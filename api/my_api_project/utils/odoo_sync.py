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
    contact_name = payload.get("customer_name")
    email = payload.get("email")
    phone = payload.get("phone", "")
    external_id_raw = payload.get("external_id")
    project_name = payload.get("project_name", "OpenSolar Project")

    if not contact_name or not email or not external_id_raw:
        raise ValueError("❌ Missing required fields: customer_name, email, or external_id.")

    # Convert external_id to integer (digits only)
    try:
        external_id = int(''.join(filter(str.isdigit, external_id_raw)))
    except Exception as e:
        raise ValueError(f"❌ Could not convert external_id '{external_id_raw}' to integer: {e}")

    print(f"🔁 Syncing Contact: {contact_name} ({email}) | OpenSolar ID: {external_id}")

    # === Extract Address Fields ===
    address = payload.get("address", {})
    street = address.get("street", "")
    street2 = address.get("street2", "")
    city = address.get("city", "")
    zip_code = address.get("zip", "")
    country_name = address.get("country")
    state_code = address.get("state")

    # Lookup country
    country_id = None
    if country_name:
        country_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.country', 'search',
            [[['name', '=', country_name]]],
            {'limit': 1}
        )
        if country_ids:
            country_id = country_ids[0]

    # Lookup state
    state_id = None
    if state_code and country_id:
        state_ids = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.country.state', 'search',
            [[['code', '=', state_code], ['country_id', '=', country_id]]],
            {'limit': 1}
        )
        if state_ids:
            state_id = state_ids[0]

    # === Find or Create Contact ===
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
        partner_data = {
            'name': contact_name,
            'email': email,
            'phone': phone,
            'x_studio_opensolar_external_id': external_id,
            'street': street,
            'street2': street2,
            'city': city,
            'zip': zip_code
        }
        if country_id:
            partner_data['country_id'] = country_id
        if state_id:
            partner_data['state_id'] = state_id

        partner_id = models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'res.partner', 'create',
            [partner_data]
        )
        print(f"✅ Created new contact ID: {partner_id}")

    # === Prevent Duplicate Project Creation ===
    existing_project_ids = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'x_projects', 'search',
        [[['x_studio_opensolar_id', '=', external_id]]],
        {'limit': 1}
    )

    if existing_project_ids:
        existing_id = existing_project_ids[0]
        print(f"⚠️  Project already exists with ID: {existing_id}")
        return {"contact_id": partner_id, "project_id": existing_id}

    # === Create Project ===
    print(f"🛠 Creating project: {project_name}")
    project_id = models.execute_kw(
        ODOO_DB, uid, ODOO_PASSWORD,
        'x_projects', 'create',
        [{
            'x_name': project_name,
            'x_studio_partner_id': partner_id,
            'x_studio_opensolar_id': external_id
        }]
    )
    print(f"✅ Project created with ID: {project_id}")
    return {"contact_id": partner_id, "project_id": project_id}
