from django.contrib import admin
from apps.api.models import (
    OpenSolarProject,
    OpenSolarCustomer,
    OpenSolarProposal,
    OpenSolarModule,
    OpenSolarInverter,
    OpenSolarBattery,
)

class OpenSolarProposalInline(admin.TabularInline):
    model = OpenSolarProposal
    extra = 0

@admin.register(OpenSolarProject)
class OpenSolarProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'external_id', 'status', 'customer', 'created_at', 'price_including_tax')  # Display only 'price_including_tax'
    search_fields = ('name', 'external_id')
    list_per_page = 50  # Set the number of records per page here (adjust as needed)
    exclude = ('price', 'price_excluding_tax')  # Exclude 'price' and 'price_excluding_tax' from the form

@admin.register(OpenSolarCustomer)
class OpenSolarCustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone')
    search_fields = ('name', 'email')

@admin.register(OpenSolarModule)
class OpenSolarModuleAdmin(admin.ModelAdmin):
    list_display = ('code', 'manufacturer_name', 'quantity', 'get_project')
    search_fields = ('code', 'manufacturer_name', 'project__name')

    def get_project(self, obj):
        return obj.project.name
    get_project.short_description = 'Project'

@admin.register(OpenSolarInverter)
class OpenSolarInverterAdmin(admin.ModelAdmin):
    list_display = ('code', 'manufacturer_name', 'quantity', 'get_project')
    search_fields = ('code', 'manufacturer_name', 'project__name')

    def get_project(self, obj):
        return obj.project.name
    get_project.short_description = 'Project'

@admin.register(OpenSolarBattery)
class OpenSolarBatteryAdmin(admin.ModelAdmin):
    list_display = ('code', 'manufacturer_name', 'quantity', 'get_project')
    search_fields = ('code', 'manufacturer_name', 'project__name')

    def get_project(self, obj):
        return obj.project.name
    get_project.short_description = 'Project'
