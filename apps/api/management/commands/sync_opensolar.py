# api/management/commands/sync_opensolar.py
import sys
import io
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
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
import math

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

        PAGE_SIZE      = 20             # Number of projects per request
        page           = 1              # Start from the first page
        last_get       = 0.0            # timestamp of last GET request
        GET_DELAY      = 1.0            # seconds between calls
        total_synced   = 0
        total_projects = None           # Will try to grab from first page if possible

        def throttle(last_time, delay):
            """Sleep so that at least `delay` seconds has passed since last_time."""
            delta = time.time() - last_time
            if delta < delay:
                time.sleep(delay - delta)

        try:
            while True:
                throttle(last_get, GET_DELAY)
                projects_url = f"{base}/projects/"
                params = {"limit": PAGE_SIZE, "page": page}
                max_retries = 3
                backoff = GET_DELAY

                got_data = False
                for attempt in range(max_retries):
                    try:
                        resp = requests.get(projects_url, headers=headers, params=params)
                        resp.raise_for_status()
                        last_get = time.time()
                        got_data = True
                        break
                    except requests.exceptions.HTTPError as e:
                        status = getattr(resp, 'status_code', None)
                        if status == 404 or status == 500:
                            self.stdout.write(self.style.WARNING(
                                f"❌ No more pages or server error after last page (page {page}): {e}. Stopping sync."
                            ))
                            return  # Exit the command cleanly
                        else:
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ HTTP error on page {page}: {e}, retrying in {backoff}s"
                            ))
                            time.sleep(backoff)
                            backoff *= 2
                if not got_data:
                    self.stdout.write(self.style.WARNING(
                        f"❌ Max retries exceeded for page {page}. Stopping sync."
                    ))
                    return

                data = resp.json()

                # Try to grab total project count from first page
                if total_projects is None and isinstance(data, dict) and "count" in data:
                    total_projects = data["count"]
                    max_pages = math.ceil(total_projects / PAGE_SIZE)
                    self.stdout.write(self.style.NOTICE(
                        f"Total projects: {total_projects}. Expecting up to {max_pages} pages."
                    ))

                if isinstance(data, dict) and "projects" in data:
                    projects = data["projects"]
                elif isinstance(data, list):
                    projects = data
                else:
                    self.stdout.write(self.style.WARNING(
                        f"Unexpected response format: {data}"
                    ))
                    break

                if not projects:
                    self.stdout.write(self.style.SUCCESS(
                        f"✅ No more projects found (empty page {page}). Stopping sync."
                    ))
                    break

                self.stdout.write(f"Fetched {len(projects)} projects from page {page}")

                for proj in projects:
                    pid = proj["id"]

                    # — fetch full project —
                    throttle(last_get, GET_DELAY)
                    proj_url = f"{base}/projects/{pid}/"
                    for attempt in range(max_retries):
                        try:
                            full = requests.get(proj_url, headers=headers)
                            full.raise_for_status()
                            last_get = time.time()
                            break
                        except requests.exceptions.HTTPError as e:
                            status = getattr(full, 'status_code', None)
                            if status == 404 or status == 500:
                                self.stdout.write(self.style.WARNING(
                                    f"❌ No more detail or server error for project {pid}: {e}. Skipping project."
                                ))
                                continue
                            else:
                                self.stdout.write(self.style.WARNING(
                                    f"⚠️ HTTP error on project {pid}: {e}, retrying in {backoff}s"
                                ))
                                time.sleep(backoff)
                                backoff *= 2
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"❌ Max retries exceeded for project {pid}. Skipping."
                        ))
                        continue

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
                        self.stdout.write(f"⚠️ No customer on project {pid}")
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

                    # — clear old parts —
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
                    systems_url = f"{base}/systems/"
                    params = {"project": pid, "fieldset": "list", "page": 1, "limit": 1}
                    for attempt in range(max_retries):
                        try:
                            systems_resp = requests.get(systems_url, headers=headers, params=params)
                            systems_resp.raise_for_status()
                            last_get = time.time()
                            break
                        except requests.exceptions.HTTPError as e:
                            status = getattr(systems_resp, 'status_code', None)
                            if status == 404 or status == 500:
                                self.stdout.write(self.style.WARNING(
                                    f"❌ No system details or server error for project {pid}: {e}. Skipping system details."
                                ))
                                continue
                            else:
                                self.stdout.write(self.style.WARNING(
                                    f"⚠️ HTTP error on systems for project {pid}: {e}, retrying in {backoff}s"
                                ))
                                time.sleep(backoff)
                                backoff *= 2
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"❌ Max retries exceeded for systems on project {pid}. Skipping."
                        ))
                        continue

                    systems_data = systems_resp.json()
                    if not systems_data:
                        continue
                    for system in systems_data:
                        price_including_tax = system.get("price_including_tax")
                        if price_including_tax is not None:
                            project_obj.price_including_tax = price_including_tax
                        else:
                            for prop in full_data.get("proposals", []):
                                pft = prop.get("price_including_tax")
                                if pft:
                                    project_obj.price_including_tax = pft
                                    break

                        project_obj.system_size_kw    = system.get("kw_stc")
                        project_obj.system_output_kwh = system.get("output_annual_kwh")
                        project_obj.battery_size_kwh  = system.get("battery_total_kwh")
                        project_obj.save()

                        total_mod_qty = 0
                        for m in system.get("modules", []):
                            module_qty = m.get("quantity", 0)
                            total_mod_qty += module_qty
                            OpenSolarModule.objects.create(
                                project=project_obj,
                                manufacturer_name=m.get("manufacturer_name", ""),
                                code=m.get("code", ""),
                                quantity=module_qty,
                            )

                        for inv in system.get("inverters", []):
                            qty = inv.get("quantity", 0) or 0
                            activation_id = inv.get("inverter_activation_id")
                            if activation_id:
                                throttle(last_get, GET_DELAY)
                                activation_url = f"{base}/component_inverter_activations/{activation_id}/"
                                for attempt in range(max_retries):
                                    try:
                                        inv_resp = requests.get(activation_url, headers=headers)
                                        inv_resp.raise_for_status()
                                        last_get = time.time()
                                        break
                                    except requests.exceptions.HTTPError as e:
                                        status = getattr(inv_resp, 'status_code', None)
                                        if status == 404 or status == 500:
                                            self.stdout.write(self.style.WARNING(
                                                f"❌ No inverter detail or server error for activation {activation_id}: {e}. Skipping inverter."
                                            ))
                                            continue
                                        else:
                                            self.stdout.write(self.style.WARNING(
                                                f"⚠️ HTTP error on inverter activation {activation_id}: {e}, retrying in {backoff}s"
                                            ))
                                            time.sleep(backoff)
                                            backoff *= 2
                                else:
                                    self.stdout.write(self.style.WARNING(
                                        f"❌ Max retries exceeded for inverter activation {activation_id}. Skipping."
                                    ))
                                    continue

                                inv_detail = inv_resp.json()
                                data_blob = inv_detail.get("data")
                                if data_blob:
                                    parsed = json.loads(data_blob)
                                    if str(parsed.get("microinverter", "")).upper() == "Y":
                                        qty = total_mod_qty

                            OpenSolarInverter.objects.create(
                                project=project_obj,
                                manufacturer_name=inv.get("manufacturer_name", ""),
                                code=inv.get("code", ""),
                                quantity=qty,
                            )

                        for b in system.get("batteries", []):
                            if not OpenSolarBattery.objects.filter(project=project_obj, code=b.get("code")).exists():
                                OpenSolarBattery.objects.create(
                                    project=project_obj,
                                    manufacturer_name=b.get("manufacturer_name", ""),
                                    code=b.get("code", ""),
                                    quantity=b.get("quantity", 0),
                                )

                        total_synced += 1

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
