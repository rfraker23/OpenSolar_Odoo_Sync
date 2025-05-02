# api/management/commands/sync_opensolar.py

import time
import json
import traceback
import requests
from decouple import config
from django.core.management.base import BaseCommand
from api.models import (
    OpenSolarProject,
    OpenSolarCustomer,
    OpenSolarProposal,
    OpenSolarModule,
    OpenSolarInverter,
    OpenSolarBattery,
)

class Command(BaseCommand):
    help = 'Sync projects, customers, proposals, and full system details from OpenSolar'

    def handle(self, *args, **kwargs):
        token   = config("OPENSOLAR_API_TOKEN")
        org_id  = config("OPENSOLAR_ORG_ID")
        base    = f"https://api.opensolar.com/api/orgs/{org_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # ─── Pagination & Throttle Settings ──────────────────────────────────────
        PAGE_SIZE      = 50             # try bumping above the default 20
        offset         = 0
        last_get       = 0.0            # timestamp of last GET
        GET_DELAY      = 1.0            # seconds between GETs   (60/min)
        last_update    = 0.0            # timestamp of last ORM update
        UPDATE_DELAY   = 6.0            # seconds between updates (10/min)
        total_synced   = 0

        def throttle(last_time, delay):
            """
            Sleep just enough so that (now - last_time) >= delay
            """
            delta = time.time() - last_time
            if delta < delay:
                time.sleep(delay - delta)

        try:
            # ─── Loop through pages of projects ───────────────────────────────────
            while True:
                throttle(last_get, GET_DELAY)
                resp = requests.get(
                    f"{base}/projects/",
                    headers=headers,
                    params={"limit": PAGE_SIZE, "offset": offset},
                )
                resp.raise_for_status()
                last_get = time.time()

                projects = resp.json()  # assume a list
                if not projects:
                    break

                # ─── Sync each project on this page ───────────────────────────────
                for proj in projects:
                    pid = proj["id"]

                    # — fetch full project (for share_link + proposals) —
                    throttle(last_get, GET_DELAY)
                    full = requests.get(f"{base}/projects/{pid}/", headers=headers)
                    full.raise_for_status()
                    last_get  = time.time()
                    full_data = full.json()
                    share_link = full_data.get("share_link", "")

                    # — upsert customer —
                    contact = (proj.get("contacts_data") or [{}])[0]
                    customer = None
                    if contact.get("id"):
                        customer, _ = OpenSolarCustomer.objects.update_or_create(
                            external_id=contact["id"],
                            defaults={
                                "name":    contact.get("display") or "No Name",
                                "email":   contact.get("email", ""),
                                "phone":   contact.get("phone", ""),
                                "address": proj.get("address", ""),
                                "city":    proj.get("locality", ""),
                                "state":   proj.get("state", ""),
                                "zip_code": proj.get("zip", ""),
                            },
                        )
                    else:
                        print(f"⚠️ No customer on project {pid}")

                    # — upsert project header —
                    project_obj, _ = OpenSolarProject.objects.update_or_create(
                        external_id=pid,
                        defaults={
                            "name":         proj.get("title", ""),
                            "status":       str(proj.get("stage", "")),
                            "customer":     customer,
                            "created_at":   proj.get("created_date"),
                            "project_type": "Residential" if proj.get("is_residential") else "Commercial",
                            "share_link":   share_link,
                        },
                    )

                    # — sync proposals —
                    for prop in full_data.get("proposals", []):
                        OpenSolarProposal.objects.update_or_create(
                            external_id=prop.get("id"),
                            defaults={
                                "project":            project_obj,
                                "title":              prop.get("title", "Untitled"),
                                "pdf_url":            prop.get("pdf_url"),
                                "created_at":         prop.get("created_at"),
                                "system_size_kw":     prop.get("kw_stc"),
                                "system_output_kwh":  prop.get("output_annual_kwh"),
                                "price":              prop.get("price_excluding_tax"),
                                "battery_size_kwh":   prop.get("battery_total_kwh"),
                            }
                        )

                    # — fetch & sync detailed systems payload —
                    throttle(last_get, GET_DELAY)
                    det = requests.get(
                        f"{base}/projects/{pid}/systems/details/",
                        headers=headers,
                        params={
                            "limit_to_sold": True,
                            "include_parts": "modules,inverters,batteries",
                        },
                    )
                    det.raise_for_status()
                    last_get = time.time()
                    systems = det.json().get("systems", [])
                    if not systems:
                        print(f"⚠️ No detailed system info for {project_obj.name}")
                        continue

                    # clear old children
                    project_obj.modules.all().delete()
                    project_obj.inverters.all().delete()
                    project_obj.batteries.all().delete()

                    # process each system
                    for sys in systems:
                        # update summary fields once (last one wins)
                        if project_obj.price is None:
                            price_inc = sys.get("price_including_tax")
                            if price_inc is not None:
                                project_obj.price = price_inc
                        project_obj.system_size_kw    = sys.get("kw_stc")
                        project_obj.battery_size_kwh  = sys.get("battery_total_kwh")
                        project_obj.system_output_kwh = sys.get("output_annual_kwh")
                        throttle(last_update, UPDATE_DELAY)
                        project_obj.save()
                        last_update = time.time()

                        # modules
                        total_mod_qty = 0
                        for m in sys.get("modules", []):
                            qty = m.get("quantity", 0)
                            total_mod_qty += qty
                            OpenSolarModule.objects.create(
                                project=project_obj,
                                manufacturer_name=m.get("manufacturer_name",""),
                                code=m.get("code",""),
                                quantity=qty,
                            )

                        # inverters (with microinverter override)
                        for inv in sys.get("inverters", []):
                            qty = inv.get("quantity") or 0
                            data = inv.get("data")
                            if data:
                                try:
                                    dj = json.loads(data)
                                    if dj.get("microinverter") == "Y":
                                        qty = total_mod_qty
                                except json.JSONDecodeError:
                                    pass
                            OpenSolarInverter.objects.create(
                                project=project_obj,
                                manufacturer_name=inv.get("manufacturer_name",""),
                                code=inv.get("code",""),
                                quantity=qty,
                            )

                        # batteries
                        for b in sys.get("batteries", []):
                            OpenSolarBattery.objects.create(
                                project=project_obj,
                                manufacturer_name=b.get("manufacturer_name",""),
                                code=b.get("code",""),
                                quantity=b.get("quantity",0),
                            )

                    print(f"✅ Synced full system for {project_obj.name}")
                    total_synced += 1

                # ─── advance & exit if last page was partial ───────────────────────
                offset += PAGE_SIZE
                if len(projects) < PAGE_SIZE:
                    break

            # ─── final report ─────────────────────────────────────────────────────
            self.stdout.write(self.style.SUCCESS(
                f"✅ Synced {total_synced} OpenSolar projects (paged in {PAGE_SIZE} chunks)."
            ))

        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"❌ API Request Error: {e}"))
            traceback.print_exc()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ General Sync Error: {e}"))
            traceback.print_exc()
