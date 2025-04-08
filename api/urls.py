from django.urls import path
from .views import (
    hello_world,
    sync_odoo_projects,
    send_to_opensolar,
    test_opensolar_token,
    validate_opensolar_project,
    opensolar_webhook_logs,
)

urlpatterns = [
    path('hello/', hello_world),
    path('odoo-sync/', sync_odoo_projects),
    path('send-to-opensolar/', send_to_opensolar),
    path('test-opensolar/', test_opensolar_token),
    path('validate-project/', validate_opensolar_project),
    path('opensolar-logs/', opensolar_webhook_logs),
]
