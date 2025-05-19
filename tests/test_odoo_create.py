from utils.odoo_sync import sync_opensolar_payload_to_odoo

payload = {
    "customer_name": "Test Sync User",
    "email": "testuser@example.com",
    "phone": "123-456-7890",
    "project_name": "Test Solar Project - Sand Dunes",
    "external_id": "opensolar-test-98765",
    "address": {
        "street": "123 Solar Way",
        "street2": "Suite 200",
        "city": "Phoenix",
        "state": "AZ",
        "zip": "85001",
        "country": "United States"
    }
}

result = sync_opensolar_payload_to_odoo(payload)
print("🚀 Sync Result:", result)
