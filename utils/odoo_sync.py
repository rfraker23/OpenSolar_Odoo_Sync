import os
import xmlrpc.client
from decouple import Config, RepositoryEnv

# Load .env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
env_config = Config(RepositoryEnv(env_path))

# Odoo credentials
ODOO_URL = env_config("ODOO_URL")
ODOO_DB = env_config("ODOO_DB")
ODOO_USERNAME = env_config("ODOO_API_USERNAME")
ODOO_PASSWORD = env_config("ODOO_API_TOKEN")

# Connect to Odoo
common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
if not uid:
    raise Exception("❌ Odoo authentication failed.")

models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")


def sync_opensolar_payload_to_odoo(payload):
    """
    Sync a single OpenSolar project payload into Odoo:
    - Create/find contact
    - Create project
    - Store external_id as integer (only numeric part)
    """

    # === Step 1: Validate and sanitize input ===
    contact_name = payload.get("customer_name")
    email = payload.get("email")
    phone = payload.get("phone", "")
    external_id_raw = payload.get("external_id")
    project_name = payload.get("project_name", "OpenSolar Project")

    if not contact_name or not email or not external_id_raw:
        raise ValueError("❌ Missing required fields: customer_name, email, or external_id.")

    # === Step 2: Convert external_id to integer (digits only) ===
    try:
        external_id = int(''.join(filter(str.isdigit, external_id_raw)))
    except Exception as e:
        raise ValueError(f"❌ Could not convert external_id '{external_id_raw}' to integer: {e}")

    print(f"🔁 Syncing Contact: {contact_name} ({email}) | OpenSolar ID: {external_id}")

    # === Step 3: Find or create contact ===
    partner_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'res.partner', 'search',
        [[['email', '=', email]]],
        {'limit': 1}
    )

    if partner_ids:
        partner_id = partner_ids[0]
        print(f"ℹ️  Found existing contact ID: {partner_id}")
    else:
        partner_id = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'create',
            [{
                'name': contact_name,
                'email': email,
                'phone': phone,
                'x_studio_opensolar_external_id': external_id  # Integer field on contact
            }]
        )
        print(f"✅ Created new contact ID: {partner_id}")

    # === Step 4: Create linked project ===
    print(f"🛠 Creating project: {project_name}")
    project_id = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'x_projects', 'create',
        [{
            'x_name': project_name,
            'x_studio_partner_id': partner_id,
            'x_studio_opensolar_id': external_id  # Integer field on project
        }]
    )
    print(f"✅ Project created with ID: {project_id}")

    return {"contact_id": partner_id, "project_id": project_id}
