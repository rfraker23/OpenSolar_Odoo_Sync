from django.urls import path
from .views import hello_world, sync_odoo_projects, send_to_opensolar, test_opensolar_token  # Import views

urlpatterns = [
    path('hello/', hello_world),
    path('sync/odoo/', sync_odoo_projects),
    path('sync/opensolar/', send_to_opensolar),
    path('test-opensolar/', test_opensolar_token),  # Ensure this is included
]
