from django.urls import path
from .views import hello_world, sync_odoo_projects  # Import both views

urlpatterns = [
    path('hello/', hello_world),  # This handles the 'GET /hello/'
    path('sync/odoo/', sync_odoo_projects),  # This handles the POST for syncing with Odoo
]
