#api/management/commands/sync_opensolar.py

import time
import json
import traceback
import requests
from decouple import config
from django.core.management.base import BaseCommand
from apps.api.models import (
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
        PAGE_SIZE      = 20             # Number of projects per request
        page           = 1              # Start from the first page
        last_get       = 0.0            # timestamp of last GET request
        GET_DELAY      = 1.0            # Delay between GET requests to respect rate limits
        total_synced   = 0              # Track the total number of projects synced

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
                    params={"limit": PAGE_SIZE, "page": page},
                )
                resp.raise_for_status()
                last_get = time.time()
                data = resp.json()
                # throttle and fetch page
                throttle(last_get, GET_DELAY)
                try:
                    resp = requests.get(
                        f"{base}/projects/",
                        headers=headers,
                        params={"limit": PAGE_SIZE, "page": page},
                    )
                    resp.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    # skip this page on 500
                    print(f"⚠️  Server error on page {page}: {e}. Skipping.")
                    page += 1
                    continue
                last_get = time.time()
                data = resp.json()
                
                print(f"Fetched data from page {page}: {data}")

                if isinstance(data, list):
                    projects = data
                elif isinstance(data, dict) and 'projects' in data:
                    projects = data['projects']
                else:
                    print(f"Unexpected response format: {data}")
                    break

                # ─── normalize projects list ─────────────────────────────────────────────
                if isinstance(data, dict) and "projects" in data:
                    projects = data["projects"]
                elif isinstance(data, list):
                    projects = data
                else:
                    print(f"Unexpected response format on page {page}: {data}")
                    break

                print(f"Fetched {len(projects)} projects from page {page}")
                if not projects:
                    print("No more projects to fetch.")
                    break

                for proj in projects:
                    pid = proj["id"]

                    # — fetch full project —
                    throttle(last_get, GET_DELAY)
                    full = requests.get(f"{base}/projects/{pid}/", headers=headers)
                    full.raise_for_status()
                    last_get = time.time()
                    full_data = full.json()
                    share_link = full_data.get("share_link", "")

                    # — upsert customer —
                    contact = (proj.get("contacts_data") or [{}])[0]
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
                        customer = None
                                  

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
                    
                     # ─── CLEAR ALL OLD PARTS ────────────────────────────────────────────
                    project_obj.modules.all().delete()
                    project_obj.inverters.all().delete()
                    project_obj.batteries.all().delete()

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
                                "price":              prop.get("price_including_tax"),
                                "battery_size_kwh":   prop.get("battery_total_kwh"),
                            }
                        )

                    # — fetch & sync detailed systems payload —
                    throttle(last_get, GET_DELAY)
                    systems_resp = requests.get(
                        f"{base}/systems/",
                        headers=headers,
                        params={"project": pid, "fieldset": "list", "page": 1, "limit": 1},
                    )
                    systems_resp.raise_for_status()
                    last_get = time.time()
                    systems_data = systems_resp.json()

                    print(f"Fetched system details for project {pid}: {systems_data}")

                    if systems_data:
                        for system in systems_data:
                            # — update price —
                            price_including_tax = system.get("price_including_tax")
                            if price_including_tax is not None:
                                project_obj.price_including_tax = price_including_tax
                                print(f"✅ Price updated for project {project_obj.name}: {price_including_tax}")
                            else:
                                print(f"⚠️ No price in system, checking proposals for {project_obj.name}")
                                for prop in full_data.get("proposals", []):
                                    pft = prop.get("price_including_tax")
                                    if pft:
                                        project_obj.price_including_tax = pft
                                        print(f"✅ Price updated for project {project_obj.name} from proposal: {pft}")
                                        break
                                    
                         # ← NEW: pull in system size, annual output and battery kWh
                            project_obj.system_size_kw    = system.get("kw_stc")
                            project_obj.system_output_kwh = system.get("output_annual_kwh")
                            project_obj.battery_size_kwh  = system.get("battery_total_kwh")
                            print(f"✅ System size for {project_obj.name}: {project_obj.system_size_kw} kW")            
                            project_obj.save()

                        # Process modules, inverters, and batteries
                        total_mod_qty = 0
                        for m in system.get("modules", []):
                            module_qty = m.get("quantity", 0)
                            total_mod_qty += module_qty
                            # Check if module already exists for the project
                            existing_module = OpenSolarModule.objects.filter(
                                project=project_obj,
                                code=m.get("code")
                            ).first()
                            if not existing_module:
                                OpenSolarModule.objects.create(
                                    project=project_obj,
                                    manufacturer_name=m.get("manufacturer_name", ""),
                                    code=m.get("code", ""),
                                    quantity=module_qty,
                                )

                       # ─── Process inverters (with microinverter override) ─────────────────
                        for inv in system.get("inverters", []):
                            # 1) start with whatever the system list payload gave you
                            qty = inv.get("quantity", 0) or 0

                            # 2) pull the real activation ID
                            activation_id = inv.get("inverter_activation_id")
                            self.stdout.write(f"🔍 Checking inverter activation ID: {activation_id}")

                            if activation_id:
                                throttle(last_get, GET_DELAY)
                                inv_resp = requests.get(
                                    f"{base}/component_inverter_activations/{activation_id}/",
                                    headers=headers
                                )
                                inv_resp.raise_for_status()
                                last_get = time.time()
                                inv_detail = inv_resp.json()
                                self.stdout.write(f"  👉 activation detail: {inv_detail}")

                                # 3) the payload’s "data" field is itself a JSON-encoded string
                                data_blob = inv_detail.get("data")
                                if data_blob:
                                    parsed = json.loads(data_blob)
                                    self.stdout.write(f"     parsed.data → microinverter = {parsed.get('microinverter')}")
                                    if str(parsed.get("microinverter","")).upper() == "Y":
                                        qty = total_mod_qty
                                        self.stdout.write(f"✅ Microinverter override: setting qty to {qty}")

                            # 4) finally, save or update the inverter record
                            OpenSolarInverter.objects.create(
                                project=project_obj,
                                manufacturer_name=inv.get("manufacturer_name",""),
                                code=inv.get("code",""),
                                quantity=qty,
                            )

                            # — process batteries —
                            for b in system.get("batteries", []):
                                if not OpenSolarBattery.objects.filter(project=project_obj, code=b.get("code")).exists():
                                    OpenSolarBattery.objects.create(
                                        project=project_obj,
                                        manufacturer_name=b.get("manufacturer_name", ""),
                                        code=b.get("code", ""),
                                        quantity=b.get("quantity", 0),
                                    )

                            print(f"✅ Synced system for {project_obj.name}")
                            total_synced += 1

                            if not projects:
                                print("No more projects to fetch.")
                                break
                            page += 1


            self.stdout.write(self.style.SUCCESS(
                f"✅ Synced {total_synced} OpenSolar projects (paged in {PAGE_SIZE} chunks)."
            ))

        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"❌ API Request Error: {e}"))
            traceback.print_exc()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ General Sync Error: {e}"))
            traceback.print_exc()
