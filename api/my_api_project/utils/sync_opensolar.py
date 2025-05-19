from utils.odoo_sync import sync_opensolar_payload_to_odoo

def get_mock_opensolar_projects():
    """TEMP: Replace this later with real OpenSolar API data."""
    return [
        {
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
    ]

def run_sync():
    print("🚀 Starting OpenSolar → Odoo sync...")

    projects = get_mock_opensolar_projects()
    success_count = 0
    failure_count = 0

    for project in projects:
        try:
            result = sync_opensolar_payload_to_odoo(project)
            print(f"✅ Synced Project ID: {result['project_id']}")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to sync project: {e}")
            failure_count += 1

    print(f"\n✅ Finished sync: {success_count} success, {failure_count} failed")
