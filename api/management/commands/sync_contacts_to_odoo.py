# api/management/commands/sync_contacts_to_odoo.py
from django.core.management.base import BaseCommand
import requests
import json
from decouple import config

# Odoo API Credentials and URL
ODOO_URL = config("ODOO_URL")
ODOO_API_TOKEN = config("ODOO_API_TOKEN")
ODOO_DB = config("ODOO_DB")
ODOO_USERNAME = config("ODOO_USERNAME")

# Odoo API URL
odoo_api_url = f'{ODOO_URL}/jsonrpc'

class Command(BaseCommand):
    help = 'Sync contacts (customers) to Odoo from OpenSolar'

    def handle(self, *args, **kwargs):
        try:
            customer_data = {
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'phone': '+1234567890',
                'address': '123 Main St',
                'city': 'Los Angeles',
                'state': 'California',  # State from OpenSolar
                'country': 'United States'  # Defaulted to United States if not provided
            }

            # Assuming the function `create_or_update_contact` is defined elsewhere
            customer_id = self.create_or_update_contact(
                customer_data['name'],
                customer_data['email'],
                customer_data['phone'],
                customer_data['address'],
                customer_data['city'],
                customer_data['state'],
                customer_data['country']
            )

            self.stdout.write(self.style.SUCCESS(f"Customer created/updated with ID: {customer_id}"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error syncing contacts: {str(e)}"))

    def create_or_update_state(self, country_name, state_code, state_name):
        """Create or update a state in Odoo, ensuring uniqueness by state code and country."""
        try:
            # Fetch country by name
            country = requests.post(f'{ODOO_URL}/jsonrpc', json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "res.country",  # Odoo country model
                    "method": "search",
                    "args": [[['name', '=', country_name]]],
                },
                "id": 1
            }).json()

            if country:
                country_id = country['result'][0]['id']
                
                # Check if state exists
                state_response = requests.post(f'{ODOO_URL}/jsonrpc', json={
                    "jsonrpc": "2.0",
                    "method": "call",
                    "params": {
                        "model": "res.country.state",
                        "method": "search_read",
                        "args": [[['code', '=', state_code], ['country_id', '=', country_id]]],
                        "fields": ['id']
                    },
                    "id": 1
                }).json()

                if state_response['result']:
                    # If state exists, return state ID
                    return state_response['result'][0]['id']
                else:
                    # Create new state if not found
                    state_create_response = requests.post(f'{ODOO_URL}/jsonrpc', json={
                        "jsonrpc": "2.0",
                        "method": "call",
                        "params": {
                            "model": "res.country.state",
                            "method": "create",
                            "args": [{
                                "name": state_name,
                                "code": state_code,
                                "country_id": country_id,
                            }]
                        },
                        "id": 1
                    }).json()

                    return state_create_response['result']
            else:
                raise Exception(f"Country '{country_name}' not found in Odoo.")

        except Exception as e:
            raise Exception(f"Error creating or updating state in Odoo: {e}")

    def create_or_update_contact(self, name, email, phone, address, city, state_name, country_name="United States"):
        """Create or update a contact in Odoo with a default country of 'United States'."""
        try:
            # Create or update state first
            state_id = self.create_or_update_state(country_name, state_name, state_name)

            # Create or update contact in Odoo
            payload = {
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": "res.partner",  # Odoo model for contacts
                    "method": "create",
                    "args": [{
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "street": address,
                        "city": city,
                        "state_id": state_id,  # Use the state id we created or updated
                        "country_id": country_id,  # Use the country ID from the country model
                    }]
                },
                "id": 1
            }

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {ODOO_API_TOKEN}',
            }

            # Send the request to Odoo to create the contact
            response = requests.post(odoo_api_url, headers=headers, data=json.dumps(payload))

            if response.status_code == 200:
                return response.json()['result']  # Return the Odoo ID of the new contact
            else:
                raise Exception(f"Error creating or updating contact in Odoo: {response.text}")

        except Exception as e:
            raise Exception(f"Error creating or updating contact in Odoo: {e}")

