from django.urls import path
from .views import hello_world, sync_odoo_projects, send_to_opensolar, test_opensolar_token  # Import all views

urlpatterns = [
    path('hello/', hello_world),  # This handles the 'GET /hello/'
    path('sync/odoo/', sync_odoo_projects),  # This handles the POST for syncing with Odoo
    path('sync/opensolar/', send_to_opensolar),  # This handles the POST for sending to OpenSolar
    path('test-opensolar/', test_opensolar_token),  # This is for testing OpenSolar token
]
