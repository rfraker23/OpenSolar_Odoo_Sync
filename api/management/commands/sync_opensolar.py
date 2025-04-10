from django.core.management.base import BaseCommand
from api.models import OpenSolarProject, OpenSolarCustomer
import requests
from decouple import config


class Command(BaseCommand):
    help = 'Syncs project and customer data from OpenSolar API'

    def handle(self, *args, **kwargs):
        token = config("OPENSOLAR_API_TOKEN")
        org_id = config("OPENSOLAR_ORG_ID")

        url = f"https://api.opensolar.com/api/orgs/{org_id}/projects/"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            projects = response.json()

            for proj in projects:
                contacts = proj.get("contacts_data", [])
                contact = contacts[0] if contacts else None

                customer = None
                if contact and "id" in contact:
                    full_name = contact.get("display") or f"{contact.get('first_name', '')} {contact.get('family_name', '')}"

                    customer, _ = OpenSolarCustomer.objects.update_or_create(
                        external_id=contact["id"],
                        defaults={
                            "name": full_name.strip(),
                            "email": contact.get("email", ""),
                            "phone": contact.get("phone", ""),
                            "address": proj.get("address", ""),
                            "city": proj.get("locality", ""),
                            "state": proj.get("state", ""),
                            "zip_code": proj.get("zip", "")
                        }
                    )

                OpenSolarProject.objects.update_or_create(
                    external_id=proj["id"],
                    defaults={
                        "name": proj.get("title", ""),
                        "status": str(proj.get("stage", "")),
                        "customer": customer,
                        "created_at": proj.get("created_date"),
                        "project_type": "Residential" if proj.get("is_residential") else "Commercial"
                    }
                )

                print("✅ Saving project:", proj.get("title"), "| Stage:", proj.get("stage"))

            self.stdout.write(self.style.SUCCESS(f"✅ Synced {len(projects)} projects from OpenSolar."))

        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"❌ API error: {str(e)}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Sync failed: {str(e)}"))
