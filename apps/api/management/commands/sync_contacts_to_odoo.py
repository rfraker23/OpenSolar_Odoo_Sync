from django.core.management.base import BaseCommand
from apps.api.models import OpenSolarCustomer
import requests
import json
from decouple import config

ODOO_URL = config("ODOO_URL")
ODOO_DB = config("ODOO_DB")
ODOO_USERNAME = config("ODOO_API_USERNAME")
ODOO_PASSWORD = config("ODOO_API_TOKEN")

ODOO_RPC = f"{ODOO_URL}/jsonrpc"

class Command(BaseCommand):
    help = 'Sync OpenSolar customers to Odoo as contacts'

    def handle(self, *args, **kwargs):
        try:
            uid = self.authenticate()
            customers = OpenSolarCustomer.objects.all()

            for customer in customers:
                external_id = customer.external_id
                email       = customer.email or ""
                name        = customer.name
                phone       = customer.phone or ""
                address     = customer.address or ""
                city        = customer.city or ""
                state_code  = customer.state or ""
                zip_code    = customer.zip_code or ""    # ← your Django field
                country_name= "United States"

                try:
                    country_id = self.get_country_id(uid, country_name)
                    state_id   = self.get_or_create_state_id(uid, state_code, state_code, country_id)

                    contact_data = {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "street": address,
                        "city": city,
                        "zip": zip_code,
                        "state_id": state_id,
                        "country_id": country_id,
                        "x_studio_opensolar_external_id": int(external_id)  # Syncing the external_id
                    }

                    # Dedupe by external ID OR email
                    domain = [
                        "|",
                        ["x_studio_opensolar_external_id", "=", int(external_id)],
                        ["email", "=", email if email else False]
                    ]
                    existing = self.search_contact(uid, domain)

                    if existing:
                        contact_id = existing[0]["id"]
                        # Perform update + log changes
                        self.update_contact(uid, contact_id, contact_data)
                    else:
                        # Create new
                        new_id = self.create_contact(uid, contact_data)
                        self.stdout.write(self.style.SUCCESS(
                            f"🆕 Created new contact ID {new_id} | {name}"
                        ))

                except Exception as contact_err:
                    self.stderr.write(self.style.ERROR(
                        f"❌ Failed to sync contact '{name}': {contact_err}"
                    ))

            self.stdout.write(self.style.SUCCESS(
                f"✅ Sync complete for {customers.count()} customers."
            ))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ General Sync Error: {e}"))

    def authenticate(self):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "login",
                "args": [ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD],
            },
            "id": 1,
        }
        res = requests.post(ODOO_RPC, json=payload).json()
        uid = res.get("result")
        if not uid:
            raise Exception("Authentication failed.")
        return uid

    def get_country_id(self, uid, country_name):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB, uid, ODOO_PASSWORD,
                    "res.country", "search",
                    [[["name", "=", country_name]]]
                ],
                "kwargs": {"limit": 1}
            },
            "id": 2,
        }
        res = requests.post(ODOO_RPC, json=payload).json()
        results = res.get("result", [])
        if not results:
            raise Exception(f"Country '{country_name}' not found.")
        return results[0]

    def get_or_create_state_id(self, uid, state_code, state_name, country_id):
        # Try to find the state
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB, uid, ODOO_PASSWORD,
                    "res.country.state", "search_read",
                    [[["code", "=", state_code], ["country_id", "=", country_id]]]
                ],
                "kwargs": {"fields": ["id"], "limit": 1}
            },
            "id": 3,
        }
        res = requests.post(ODOO_RPC, json=payload).json()
        states = res.get("result", [])
        if states:
            return states[0]["id"]

        # Create if missing
        create_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB, uid, ODOO_PASSWORD,
                    "res.country.state", "create",
                    [{
                        "name": state_name,
                        "code": state_code,
                        "country_id": country_id
                    }]
                ],
            },
            "id": 4,
        }
        return requests.post(ODOO_RPC, json=create_payload).json().get("result")

    def search_contact(self, uid, domain):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB, uid, ODOO_PASSWORD,
                    "res.partner", "search_read",
                    [domain]
                ],
                "kwargs": {"fields": ["id"], "limit": 1}
            },
            "id": 5,
        }
        res = requests.post(ODOO_RPC, json=payload).json()
        return res.get("result", [])

    def create_contact(self, uid, data):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB, uid, ODOO_PASSWORD,
                    "res.partner", "create", [data]
                ]
            },
            "id": 6,
        }
        return requests.post(ODOO_RPC, json=payload).json().get("result")

    def update_contact(self, uid, contact_id, new_data):
        # 1) Read current field values
        read_payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    ODOO_DB, uid, ODOO_PASSWORD,
                    "res.partner", "read", [[contact_id]]
                ],
                "kwargs": {"fields": list(new_data.keys())}
            },
            "id": 7,
        }
        existing = requests.post(ODOO_RPC, json=read_payload).json().get("result", [])[0]

        # 2) Compute diffs
        changes = {}
        for field, new_val in new_data.items():
            old_val = existing.get(field, "")
            if str(old_val) != str(new_val):
                changes[field] = {"old": old_val, "new": new_val}

        # 3) Write back only if there are changes
        if changes:
            write_payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "service": "object",
                    "method": "execute_kw",
                    "args": [
                        ODOO_DB, uid, ODOO_PASSWORD,
                        "res.partner", "write",
                        [[contact_id], new_data]
                    ]
                },
                "id": 8,
            }
            requests.post(ODOO_RPC, json=write_payload)
            self.stdout.write(self.style.WARNING(
                f"🔄 Updated contact ID {contact_id} with changes: {json.dumps(changes)}"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"✔️ No changes for contact ID {contact_id}"
            ))

        return contact_id
