from django.core.management.base import BaseCommand
from api.models import (
    OpenSolarProject,
    OpenSolarCustomer,
    OpenSolarModule,
    OpenSolarInverter,
    OpenSolarBattery,
)
import requests
from decouple import config
import traceback


class Command(BaseCommand):
    help = 'Sync projects, customers, and system details from OpenSolar'

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
                # Customer Sync
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
                print(f"⚠️ No customer data found for project {proj.get('title')}, skipping customer sync.")


                # Project Sync
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

                # Fetching System Details (Corrected)
                system_resp = requests.get(f"{base_url}/projects/{proj['id']}/systems/details/", headers=headers)
                system_resp.raise_for_status()
                system_data = system_resp.json()

                systems = system_data.get("systems", [])
                if systems:
                    system = systems[0]  # primary system details
                    project_obj.system_size_kw = system.get("kw_stc")
                    project_obj.price = system.get("basicPriceOverride")
                    project_obj.battery_size_kwh = system.get("battery_total_kwh")
                    project_obj.system_output_kwh = system.get("output_annual_kwh")
                    project_obj.save()

                    # Clear existing related system components
                    project_obj.modules.all().delete()
                    project_obj.inverters.all().delete()
                    project_obj.batteries.all().delete()

                    # Save Modules
                    for module in system.get("modules", []):
                        OpenSolarModule.objects.create(
                            project=project_obj,
                            manufacturer_name=module["manufacturer_name"],
                            code=module["code"],
                            quantity=module["quantity"],
                        )

                    # Save Inverters
                    for inverter in system.get("inverters", []):
                        OpenSolarInverter.objects.create(
                            project=project_obj,
                            manufacturer_name=inverter["manufacturer_name"],
                            code=inverter["code"],
                            quantity=inverter["quantity"],
                        )

                    # Save Batteries
                    for battery in system.get("batteries", []):
                        OpenSolarBattery.objects.create(
                            project=project_obj,
                            manufacturer_name=battery["manufacturer_name"],
                            code=battery["code"],
                            quantity=battery["quantity"],
                        )

                    print(f"✅ Synced system details for project: {project_obj.name}")

                else:
                    print(f"⚠️ No system data for project: {project_obj.name}")

            self.stdout.write(self.style.SUCCESS(f"✅ Successfully synced {len(projects)} projects from OpenSolar."))

        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"❌ API Request Error: {e}"))
            traceback.print_exc()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ General Sync Error: {e}"))
            traceback.print_exc()
