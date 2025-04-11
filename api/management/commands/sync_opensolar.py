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
                project_id = proj["id"]

                # Fetch full project details to get share_link and proposals
                full_proj_resp = requests.get(f"{base_url}/projects/{project_id}/", headers=headers)
                full_proj_resp.raise_for_status()
                full_proj_data = full_proj_resp.json()
                share_link = full_proj_data.get("share_link")

                # Customer Sync
                contact = (proj.get("contacts_data") or [{}])[0]
                customer = None
                if contact.get("id"):
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
                    print(f"⚠️ No customer data found for project {proj.get('title')}")

                # Project Sync
                project_obj, _ = OpenSolarProject.objects.update_or_create(
                    external_id=proj["id"],
                    defaults={
                        "name": proj.get("title", ""),
                        "status": str(proj.get("stage", "")),
                        "customer": customer,
                        "created_at": proj.get("created_date"),
                        "project_type": "Residential" if proj.get("is_residential") else "Commercial",
                        "share_link": share_link,
                    },
                )

                # Proposals (if embedded)
                proposals = full_proj_data.get("proposals", [])
                for proposal in proposals:
                    proposal_obj, _ = OpenSolarProposal.objects.update_or_create(
                        external_id=proposal.get("id"),
                        defaults={
                            "project": project_obj,
                            "title": proposal.get("title", "Untitled"),
                            "pdf_url": proposal.get("pdf_url"),
                            "created_at": proposal.get("created_at"),
                            "system_size_kw": proposal.get("kw_stc"),
                            "system_output_kwh": proposal.get("output_annual_kwh"),
                            "price": proposal.get("price_excluding_tax"),
                            "battery_size_kwh": proposal.get("battery_total_kwh"),
                        }
                    )
                    print(f"📄 Synced proposal for: {project_obj.name}")

                # Fetch System Details
                system_resp = requests.get(f"{base_url}/projects/{proj['id']}/systems/details/", headers=headers)
                system_resp.raise_for_status()
                system_data = system_resp.json()
                systems = system_data.get("systems", [])

                if systems:
                    system = systems[0]
                    project_obj.system_size_kw = system.get("kw_stc")
                    project_obj.price = system.get("basicPriceOverride")
                    project_obj.battery_size_kwh = system.get("battery_total_kwh")
                    project_obj.system_output_kwh = system.get("output_annual_kwh")
                    project_obj.save()

                    # Clear old related items
                    project_obj.modules.all().delete()
                    project_obj.inverters.all().delete()
                    project_obj.batteries.all().delete()

                    for module in system.get("modules", []):
                        OpenSolarModule.objects.create(
                            project=project_obj,
                            manufacturer_name=module["manufacturer_name"],
                            code=module["code"],
                            quantity=module["quantity"],
                        )

                    for inverter in system.get("inverters", []):
                        OpenSolarInverter.objects.create(
                            project=project_obj,
                            manufacturer_name=inverter["manufacturer_name"],
                            code=inverter["code"],
                            quantity=inverter["quantity"],
                        )

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
