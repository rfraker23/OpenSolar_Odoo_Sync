# models.py (update OpenSolarProposal)
from django.db import models

class OpenSolarCustomer(models.Model):
    external_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    zip_code = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.name

class OpenSolarProject(models.Model):
    external_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=100, null=True, blank=True)
    customer = models.ForeignKey('OpenSolarCustomer', on_delete=models.CASCADE, related_name='projects', null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    project_type = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name

class OpenSolarProposal(models.Model):
    external_id = models.CharField(max_length=100, unique=True)
    project = models.ForeignKey(OpenSolarProject, on_delete=models.CASCADE, related_name='proposals')
    title = models.CharField(max_length=255)
    pdf_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    # System details from proposal
    system_size_kw = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    system_output_kwh = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    battery_size_kwh = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.project.name}"

# admin.py
from django.contrib import admin
from .models import OpenSolarProject, OpenSolarCustomer, OpenSolarProposal

@admin.register(OpenSolarProposal)
class OpenSolarProposalAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'system_size_kw', 'price', 'pdf_url')
    search_fields = ('title', 'project__name')

# sync_opensolar.py additions (example usage)
def fetch_proposals_for_project(org_id, project_id, headers):
    url = f"https://api.opensolar.com/api/orgs/{org_id}/projects/{project_id}/proposals/"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Error fetching proposals for project {project_id}: {e}")
        return []

# Example placeholder for your project sync loop:
def sync_proposals_for_project(project_obj, org_id, headers):
    proposals = fetch_proposals_for_project(org_id, project_obj.external_id, headers)
    for prop in proposals:
        OpenSolarProposal.objects.update_or_create(
            external_id=prop["id"],
            defaults={
                "project": project_obj,
                "title": prop.get("title", "Untitled"),
                "pdf_url": prop.get("pdf_url"),
                "created_at": prop.get("created_at"),
                "system_size_kw": prop.get("kw_stc"),
                "system_output_kwh": prop.get("output_annual_kwh"),
                "price": prop.get("price_excluding_tax"),
                "battery_size_kwh": prop.get("battery_total_kwh"),
            }
        )
