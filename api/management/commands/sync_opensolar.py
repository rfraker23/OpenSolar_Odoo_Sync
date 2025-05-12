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
        PAGE_SIZE      = 20             # Number of projects per request
        page           = 1              # Start from the first page
        last_get       = 0.0            # timestamp of last GET request
        GET_DELAY      = 0.6            # Delay between GET requests to respect rate limits
        last_update    = 0.0            # timestamp of last ORM update
        UPDATE_DELAY   = 1.0            # Delay between system updates to respect rate limits
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
                resp.raise_for_status()  # Raise exception for bad responses
                last_get = time.time()

                data = resp.json()

                # Debugging output to inspect the structure of the response
                print(f"Fetched data from page {page}: {data}")  # Inspect the entire response

                if isinstance(data, list):  # If the response is a list of projects
                    projects = data
                elif isinstance(data, dict) and 'projects' in data:  # If the response contains a 'projects' key
                    projects = data['projects']
                else:
                    print(f"Unexpected response format: {data}")
                    break

                print(f"Fetched {len(projects)} projects from page {page}")  # Debugging output
                if not projects:
                    print("No more projects to fetch.")
                    break

                # ─── Sync each project on this page ───────────────────────────────
                for proj in projects:
                    pid = proj["id"]

                    # — fetch full project (for share_link + proposals) —
                    throttle(last_get, GET_DELAY)
                    full = requests.get(f"{base}/projects/{pid}/", headers=headers)
                    full.raise_for_status()
                    last_get = time.time()
                    full_data = full.json()
                    share_link = full_data.get("share_link", "")

                    # — upsert customer — (using the customer's external_id)
                    contact = (proj.get("contacts_data") or [{}])[0]  # Use first contact or an empty dict
                    if contact.get("id"):
                        customer, _ = OpenSolarCustomer.objects.update_or_create(
                            external_id=contact["id"],  # Use contact ID for the customer
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
                        # Optionally, create a default customer or skip the project
                        customer = None  # Assign a default customer or handle as per your logic

                    # — upsert project header — (using the project's external_id)
                    project_obj, _ = OpenSolarProject.objects.update_or_create(
                        external_id=pid,  # Use project ID for the project
                        defaults={
                            "name":         proj.get("title", ""),
                            "status":       str(proj.get("stage", "")),
                            "customer":     customer,  # Link customer to the project
                            "created_at":   proj.get("created_date"),
                            "project_type": "Residential" if proj.get("is_residential") else "Commercial",
                            "share_link":   share_link,
                        },
                    )

                    # ─── sync proposals — (same as before)
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

                    # ─── Fetch & Sync Detailed Systems Payload ─────────────────────────────────
                    throttle(last_get, GET_DELAY)  # Delay for system details (60/min)
                    # Fetch the system details for the project
                    systems_resp = requests.get(
                        f"{base}/systems/",
                        headers=headers,
                        params={"project": pid, "fieldset": "list", "page": 1, "limit": 1}  # Fetch a single system
                    )
                    systems_resp.raise_for_status()
                    systems_data = systems_resp.json()

                    # Debugging output to inspect the system data
                    print(f"Fetched system details for project {pid}: {systems_data}")  # Debugging output

                    if systems_data:
                        for system in systems_data:
                            # First attempt: Extract the price_including_tax from system data
                            price_including_tax = system.get("price_including_tax", None)

                            if price_including_tax:
                                # If the price is available in the system, update the project price
                                project_obj.price_including_tax = price_including_tax
                                print(f"✅ Price updated for project {project_obj.name}: {price_including_tax}")
                            else:
                                # Fallback: If no price in system, check proposals
                                print(f"⚠️ No price found in system, checking proposals for project {project_obj.name}.")
                                for prop in full_data.get("proposals", []):
                                    price_from_proposal = prop.get("price_including_tax", None)
                                    if price_from_proposal:
                                        project_obj.price_including_tax = price_from_proposal
                                        print(f"✅ Price updated for project {project_obj.name} from proposal: {price_from_proposal}")
                                        break  # Stop once we find a price in the proposals

                            project_obj.save()  # Save the updated project

                            # Process modules, inverters, and batteries
                            total_mod_qty = 0
                            for m in system.get("modules", []):
                                OpenSolarModule.objects.create(
                                    project=project_obj,
                                    manufacturer_name=m.get("manufacturer_name", ""),
                                    code=m.get("code", ""),
                                    quantity=m.get("quantity", 0),
                                )

                            for inv in system.get("inverters", []):
                                OpenSolarInverter.objects.create(
                                    project=project_obj,
                                    manufacturer_name=inv.get("manufacturer_name", ""),
                                    code=inv.get("code", ""),
                                    quantity=inv.get("quantity", 0),
                                )

                            for b in system.get("batteries", []):
                                OpenSolarBattery.objects.create(
                                    project=project_obj,
                                    manufacturer_name=b.get("manufacturer_name", ""),
                                    code=b.get("code", ""),
                                    quantity=b.get("quantity", 0),
                                )

                            print(f"✅ Synced system for {project_obj.name}")

                        total_synced += 1

                # ─── Check if last page was fetched ───────────────────────
                if len(projects) < PAGE_SIZE:  # If fewer projects than the PAGE_SIZE, it’s the last page
                    print(f"Last page reached. Total projects synced: {total_synced}")
                    break
                
                page += 1  # Increment page number to fetch the next set of projects

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
