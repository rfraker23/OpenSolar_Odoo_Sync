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
import traceback


class Command(BaseCommand):
    help = 'Sync projects, customers, proposals, and system details from OpenSolar'

    def handle(self, *args, **kwargs):
        token = config("OPENSOLAR_API_TOKEN")
        org_id = config("OPENSOLAR_ORG_ID")
        base_url = f"https://api.opensolar.com/api/orgs/{org_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(f"{base_url}/projects/", headers=headers)
            response.raise_for_status()
            projects = response.json()

            for proj in projects:
                contacts = proj.get("contacts_data")
                customer = None

                if contacts and contacts[0].get("id"):
                    contact = contacts[0]
                    customer, _ = OpenSolarCustomer.objects.update_or_create(
                        external_id=contact["id"],
                        defaults={
                            "name": contact.get("display") or "No Name",
                            "email": contact.get("email", ""),
                            "phone": contact.get("phone", ""),
                            "address": proj.get("address", ""),
                            "city": proj.get("locality", ""),
                            "state": proj.get("state", ""),
                            "zip_code": proj.get("zip", ""),
                        },
                    )
                else:
                    print(f"⚠️ No customer data for project: {proj.get('title')}")

                # Project sync
                project_obj, _ = OpenSolarProject.objects.update_or_create(
                    external_id=proj["id"],
                    defaults={
                        "name": proj.get("title", ""),
                        "status": str(proj.get("stage", "")),
                        "customer": customer,
                        "created_at": proj.get("created_date"),
                        "project_type": "Residential" if proj.get("is_residential") else "Commercial",
                        "share_link": proj.get("share_link"),
                    },
                )

                # Proposal sync
                OpenSolarProposal.objects.update_or_create(
                    external_id=str(proj["id"]),
                    defaults={
                        "project": project_obj,
                        "title": proj.get("title", "Untitled"),
                        "online_url": proj.get("share_link"),
                        "pdf_url": None,
                        "created_at": proj.get("created_date"),
                        "system_size_kw": None,
                        "system_output_kwh": None,
                        "price": None,
                        "battery_size_kwh": None,
                    }
                )
                print(f"📄 Synced proposal for: {project_obj.name}")

                # System sync
                try:
                    sys_resp = requests.get(f"{base_url}/projects/{proj['id']}/systems/details/", headers=headers)
                    if sys_resp.status_code == 200:
                        system_data = sys_resp.json()
                        systems = system_data.get("systems", [])
                        if systems:
                            system = systems[0]
                            project_obj.system_size_kw = system.get("kw_stc")
                            project_obj.price = system.get("basicPriceOverride")
                            project_obj.battery_size_kwh = system.get("battery_total_kwh")
                            project_obj.system_output_kwh = system.get("output_annual_kwh")
                            project_obj.save()

                            # Clear and re-sync components
                            project_obj.modules.all().delete()
                            project_obj.inverters.all().delete()
                            project_obj.batteries.all().delete()

                            for m in system.get("modules", []):
                                OpenSolarModule.objects.create(
                                    project=project_obj,
                                    manufacturer_name=m["manufacturer_name"],
                                    code=m["code"],
                                    quantity=m["quantity"]
                                )
                            for i in system.get("inverters", []):
                                OpenSolarInverter.objects.create(
                                    project=project_obj,
                                    manufacturer_name=i["manufacturer_name"],
                                    code=i["code"],
                                    quantity=i["quantity"]
                                )
                            for b in system.get("batteries", []):
                                OpenSolarBattery.objects.create(
                                    project=project_obj,
                                    manufacturer_name=b["manufacturer_name"],
                                    code=b["code"],
                                    quantity=b["quantity"]
                                )
                            print(f"✅ Synced system details for project: {project_obj.name}")
                        else:
                            print(f"⚠️ No system data for project: {project_obj.name}")
                except Exception as e:
                    print(f"❌ Error pulling system data for project {proj.get('title')}: {e}")

            self.stdout.write(self.style.SUCCESS(f"✅ Synced {len(projects)} projects from OpenSolar"))

        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"❌ API error: {e}"))
            traceback.print_exc()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ General Sync Error: {e}"))
            traceback.print_exc()
