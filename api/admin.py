from django.contrib import admin
from .models import (
    OpenSolarProject,
    OpenSolarCustomer,
    OpenSolarProposal,
    OpenSolarModule,
    OpenSolarInverter,
    OpenSolarBattery
)

@admin.register(OpenSolarProject)
class OpenSolarProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'external_id', 'status', 'customer', 'created_at')
    search_fields = ('name', 'external_id')


@admin.register(OpenSolarCustomer)
class OpenSolarCustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone')
    search_fields = ('name', 'email')


@admin.register(OpenSolarProposal)
class OpenSolarProposalAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'system_size_kw', 'price', 'pdf_url')
    search_fields = ('title', 'project__name')


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
