# api/management/commands/sync_opensolar.py

from django.core.management.base import BaseCommand
from api.models import (
    OpenSolarProject,
    OpenSolarCustomer,
    OpenSolarProposal,
    OpenSolarModule,
    OpenSolarInverter,
    OpenSolarBattery,
)
import requests
from decouple import config
import json
import traceback


class Command(BaseCommand):
    help = 'Sync projects, customers, proposals, and full system details (modules, inverters, batteries) from OpenSolar'

    def handle(self, *args, **kwargs):
        token   = config("OPENSOLAR_API_TOKEN")
        org_id  = config("OPENSOLAR_ORG_ID")
        base    = f"https://api.opensolar.com/api/orgs/{org_id}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        try:
            # 1) pull down all projects
            resp = requests.get(f"{base}/projects/", headers=headers)
            resp.raise_for_status()
            projects = resp.json()

            for proj in projects:
                pid = proj["id"]

                # 2) fetch project detail (for share_link + proposals)
                full = requests.get(f"{base}/projects/{pid}/", headers=headers)
                full.raise_for_status()
                full_data  = full.json()
                share_link = full_data.get("share_link", "")

                # 3) sync customer
                contact = (proj.get("contacts_data") or [{}])[0]
                customer = None
                if contact.get("id"):
                    customer, _ = OpenSolarCustomer.objects.update_or_create(
                        external_id=contact["id"],
                        defaults={
                            "name":     contact.get("display") or "No Name",
                            "email":    contact.get("email", ""),
                            "phone":    contact.get("phone", ""),
                            "address":  proj.get("address", ""),
                            "city":     proj.get("locality", ""),
                            "state":    proj.get("state", ""),
                            "zip_code": proj.get("zip", ""),
                        },
                    )
                else:
                    print(f"⚠️  No customer on {proj.get('title')}")

                # 4) upsert OpenSolarProject
                project_obj, _ = OpenSolarProject.objects.update_or_create(
                    external_id=pid,
                    defaults={
                        "name":           proj.get("title", ""),
                        "status":         str(proj.get("stage", "")),
                        "customer":       customer,
                        "created_at":     proj.get("created_date"),
                        "project_type":   "Residential" if proj.get("is_residential") else "Commercial",
                        "share_link":     share_link,
                    },
                )

                # 5) sync proposals
                for prop in full_data.get("proposals", []):
                    OpenSolarProposal.objects.update_or_create(
                        external_id=prop.get("id"),
                        defaults={
                            "project":               project_obj,
                            "title":                 prop.get("title", "Untitled"),
                            "pdf_url":               prop.get("pdf_url"),
                            "created_at":            prop.get("created_at"),
                            "system_size_kw":        prop.get("kw_stc"),
                            "system_output_kwh":     prop.get("output_annual_kwh"),
                            "price":                 prop.get("price_excluding_tax"),
                            "battery_size_kwh":      prop.get("battery_total_kwh"),
                        }
                    )

                # 6) fetch the full systems/details payload
                #    limit_to_sold=True so only sold systems,
                #    include only modules,inverters,batteries
                params = {
                    "limit_to_sold": True,
                    "include_parts": "modules,inverters,batteries",
                }
                det = requests.get(
                    f"{base}/projects/{pid}/systems/details/",
                    headers=headers,
                    params=params
                )
                det.raise_for_status()
                detail_data = det.json().get("systems", [])

                if not detail_data:
                    print(f"⚠️  No detailed system info for {project_obj.name}")
                    continue

                # clear out old child records
                project_obj.modules.all().delete()
                project_obj.inverters.all().delete()
                project_obj.batteries.all().delete()

                # process each returned system
                for system in detail_data:
                    # update summary fields once per system (last one wins)
                    if project_obj.price is None:
                        price_inc = system.get("price_including_tax")
                        if price_inc is not None:
                            project_obj.price = price_inc
                    project_obj.system_size_kw    = system.get("kw_stc")
                    project_obj.battery_size_kwh  = system.get("battery_total_kwh")
                    project_obj.system_output_kwh = system.get("output_annual_kwh")
                    project_obj.save()

                    # sync modules
                    module_qty_total = 0
                    for m in system.get("modules", []):
                        qty = m.get("quantity", 0)
                        module_qty_total += qty
                        OpenSolarModule.objects.create(
                            project=project_obj,
                            manufacturer_name=m.get("manufacturer_name", ""),
                            code=m.get("code", ""),
                            quantity=qty,
                        )

                    # sync inverters, with micro‐inverter override
                    for inv in system.get("inverters", []):
                        qty = inv.get("quantity") or 0
                        data = inv.get("data")
                        if data:
                            try:
                                dj = json.loads(data)
                                if dj.get("microinverter") == "Y":
                                    qty = module_qty_total
                            except Exception:
                                pass

                        OpenSolarInverter.objects.create(
                            project=project_obj,
                            manufacturer_name=inv.get("manufacturer_name", ""),
                            code=inv.get("code", ""),
                            quantity=qty,
                        )

                    # sync batteries
                    for b in system.get("batteries", []):
                        OpenSolarBattery.objects.create(
                            project=project_obj,
                            manufacturer_name=b.get("manufacturer_name", ""),
                            code=b.get("code", ""),
                            quantity=b.get("quantity", 0),
                        )

                print(f"✅  Synced full system for {project_obj.name}")

            self.stdout.write(self.style.SUCCESS(f"✅  Synced {len(projects)} OpenSolar projects."))

        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"❌  API Request Error: {e}"))
            traceback.print_exc()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌  General Sync Error: {e}"))
            traceback.print_exc()
