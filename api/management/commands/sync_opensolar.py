# api/management/commands/sync_opensolar.py

import time
import json
import traceback
import requests

from functools import wraps
from django.core.management.base import BaseCommand
from decouple import config

from api.models import (
    OpenSolarProject,
    OpenSolarCustomer,
    OpenSolarProposal,
    OpenSolarModule,
    OpenSolarInverter,
    OpenSolarBattery,
)


def rate_limiter(calls_per_minute):
    interval = 60.0 / calls_per_minute
    def decorator(fn):
        last = {"ts": 0.0}
        @wraps(fn)
        def wrapped(*args, **kwargs):
            elapsed = time.time() - last["ts"]
            if elapsed < interval:
                time.sleep(interval - elapsed)
            result = fn(*args, **kwargs)
            last["ts"] = time.time()
            return result
        return wrapped
    return decorator


class Command(BaseCommand):
    help = 'Sync projects, customers, proposals, and full system details (modules, inverters, batteries) from OpenSolar'

    def handle(self, *args, **kwargs):
        token   = config("OPENSOLAR_API_TOKEN")
        org_id  = config("OPENSOLAR_ORG_ID")
        self.base   = f"https://api.opensolar.com/api/orgs/{org_id}"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            # 1) pull down *all* projects in pages of 20
            projects = []
            page, limit = 1, 20
            while True:
                batch = self.fetch_projects(page, limit)
                if not batch:
                    break
                projects.extend(batch)
                page += 1

            self.stdout.write(f"\n🔎  {len(projects)} OpenSolar projects fetched\n")

            for proj in projects:
                pid = proj["id"]

                # 2) fetch project detail (share_link + proposals)
                full_data  = self.fetch_project_detail(pid)
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
                    self.stdout.write(f"⚠️  No customer on project #{pid} '{proj.get('title')}'")

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
                det = self.fetch_systems(pid)
                if not det:
                    self.stdout.write(f"⚠️  No detailed system info for '{project_obj.name}'")
                    continue

                # clear out old child records
                project_obj.modules.all().delete()
                project_obj.inverters.all().delete()
                project_obj.batteries.all().delete()

                # process each returned system
                for system in det:
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
                        qty = m.get("quantity", 0) or 0
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
                            quantity=b.get("quantity", 0) or 0,
                        )

                self.stdout.write(f"✅  Synced full system for '{project_obj.name}'")

            self.stdout.write(self.style.SUCCESS(f"✅  Synced {len(projects)} OpenSolar projects."))

        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"❌  API Request Error: {e}"))
            traceback.print_exc()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌  General Sync Error: {e}"))
            traceback.print_exc()

    # ─── paged / throttled fetchers ─────────────────────────────────────────

    @rate_limiter(100)   # ≤100/min for project list
    def fetch_projects(self, page, limit):
        resp = requests.get(
            f"{self.base}/projects/",
            headers=self.headers,
            params={"page": page, "limit": limit}
        )
        resp.raise_for_status()
        return resp.json()

    @rate_limiter(100)   # ≤100/min for project detail
    def fetch_project_detail(self, project_id):
        resp = requests.get(
            f"{self.base}/projects/{project_id}/",
            headers=self.headers
        )
        resp.raise_for_status()
        return resp.json()

    @rate_limiter(60)    # ≤60/min for systems/details
    def fetch_systems(self, project_id):
        params = {
            "limit_to_sold": True,
            "include_parts": "modules,inverters,batteries",
        }
        resp = requests.get(
            f"{self.base}/projects/{project_id}/systems/details/",
            headers=self.headers,
            params=params
        )
        resp.raise_for_status()
        return resp.json().get("systems", [])
