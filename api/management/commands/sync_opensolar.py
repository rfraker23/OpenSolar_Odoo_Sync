from django.core.management.base import BaseCommand
from api.models import OpenSolarProject, OpenSolarCustomer
import requests
from decouple import config


class Command(BaseCommand):
    help = 'Syncs project and customer data from OpenSolar API'

    def handle(self, *args, **kwargs):
        token = config("OPENSOLAR_API_TOKEN")
        org_id = config("OPENSOLAR_ORG_ID")  # ← This MUST come before the next line

        url = f"https://api.opensolar.com/api/orgs/{org_id}/projects/"  # Now org_id is defined

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
    }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            projects = response.json()

            for proj in projects:
                cust_data = proj.get("account", {})
                if not cust_data:
                    continue

                customer, _ = OpenSolarCustomer.objects.update_or_create(
                    external_id=cust_data["id"],
                    defaults={
                        "name": cust_data.get("name", ""),
                        "email": cust_data.get("email", ""),
                        "phone": cust_data.get("phone", ""),
                        "address": cust_data.get("address", ""),
                        "city": cust_data.get("city", ""),
                        "state": cust_data.get("state", ""),
                        "zip_code": cust_data.get("zip_code", "")
                    }
                )

                OpenSolarProject.objects.update_or_create(
                    external_id=proj["id"],
                    defaults={
                        "name": proj.get("name", ""),
                        "status": proj.get("status", ""),
                        "customer": customer,
                        "created_at": proj.get("created_at"),
                        "project_type": proj.get("type", "")
                    }
                )

            self.stdout.write(self.style.SUCCESS(f"✅ Synced {len(projects)} projects from OpenSolar."))

        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"❌ API error: {str(e)}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Sync failed: {str(e)}"))
