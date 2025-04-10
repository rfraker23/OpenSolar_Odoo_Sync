from django.contrib import admin
from .models import OpenSolarProject, OpenSolarCustomer

@admin.register(OpenSolarProject)
class OpenSolarProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'external_id', 'status', 'customer', 'created_at')
    search_fields = ('name', 'external_id')

@admin.register(OpenSolarCustomer)
class OpenSolarCustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone')
    search_fields = ('name', 'email')
