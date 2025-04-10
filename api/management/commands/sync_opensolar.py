from django.core.management.base import BaseCommand
from api.models import OpenSolarProject, OpenSolarCustomer, OpenSolarProposal
import requests
from decouple import config


def fetch_all_proposals_from_webhooks(org_id, headers):
    url = f"https://api.opensolar.com/api/orgs/{org_id}/webhook_process_logs/"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print("🧪 Full webhook log data:", response.json())
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Error fetching webhook proposals: {e}")
        return []



def sync_all_proposals(org_id, headers):
    proposals = fetch_all_proposals_from_webhooks(org_id, headers)
    print(f"📦 Webhook proposals fetched: {len(proposals)}")

    for entry in proposals:
        payload = entry.get("payload", {})
        if not payload or "id" not in payload:
            continue

        project_id = payload.get("project")
        try:
            project = OpenSolarProject.objects.get(external_id=project_id)
        except OpenSolarProject.DoesNotExist:
            print(f"⚠ Skipping proposal {payload.get('id')} — project {project_id} not found")
            continue

        OpenSolarProposal.objects.update_or_create(
            external_id=payload["id"],
            defaults={
                "project": project,
                "title": payload.get("title", "Untitled"),
                "pdf_url": payload.get("pdf_url"),
                "created_at": payload.get("created_at"),
                "system_size_kw": payload.get("kw_stc"),
                "system_output_kwh": payload.get("output_annual_kwh"),
                "price": payload.get("price_excluding_tax"),
                "battery_size_kwh": payload.get("battery_total_kwh"),
            }
        )
        print(f"✅ Synced proposal: {payload.get('title', 'Untitled')}")


class Command(BaseCommand):
    help = 'Syncs project and customer data from OpenSolar API'

    def handle(self, *args, **kwargs):
        token = config("OPENSOLAR_API_TOKEN")
        org_id = config("OPENSOLAR_ORG_ID")

        base_url = f"https://api.opensolar.com/api/orgs/{org_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.get(f"{base_url}/projects/", headers=headers)
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

                project_obj, _ = OpenSolarProject.objects.update_or_create(
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

            # ✅ NEW: Sync proposals from webhook logs
            sync_all_proposals(org_id, headers)

            self.stdout.write(self.style.SUCCESS(f"✅ Synced {len(projects)} projects from OpenSolar."))

        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"❌ API error: {str(e)}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Sync failed: {str(e)}"))
