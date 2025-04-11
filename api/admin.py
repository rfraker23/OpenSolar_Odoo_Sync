from django.contrib import admin
from django.utils.html import format_html
from .models import (
    OpenSolarProject,
    OpenSolarCustomer,
    OpenSolarProposal,
    OpenSolarModule,
    OpenSolarInverter,
    OpenSolarBattery
)
class OpenSolarProposalInline(admin.TabularInline):
    model = OpenSolarProposal
    extra = 0

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
    list_display = (
        'title',
        'project',
        'system_size_kw',
        'price',
        'online_link',  # ⬅️ new field
        'pdf_url'
    )
    search_fields = ('title', 'project__name')

    def online_link(self, obj):
        if obj.online_url:
            return format_html('<a href="{}" target="_blank">View Proposal</a>', obj.online_url)
        return "-"
    online_link.short_description = "Online Proposal"

    

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
