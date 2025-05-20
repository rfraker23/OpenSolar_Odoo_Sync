# OpenSolar Odoo Sync

A Django-based synchronization tool that integrates [OpenSolar](https://www.opensolar.com/) project, customer, and proposal data with an Odoo ERP system.

## Features

- Syncs OpenSolar projects, customers, proposals, and detailed system data into Odoo.
- Stores data in Django models for further processing, reporting, or integration.
- Can be run as a management command or automated for scheduled syncs.

## Requirements

- Python 3.10+
- Django 4.x or 5.x
- Access to OpenSolar API credentials (token, org_id)
- Access to Odoo with API/RPC enabled

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/rfraker23/OpenSolar_Odoo_Sync.git
   cd OpenSolar_Odoo_Sync
Create and activate a virtual environment:

bash
Copy
Edit
python -m venv venv
# On Windows
venv\Scripts\activate
# On Mac/Linux
source venv/bin/activate
Install dependencies:

bash
Copy
Edit
pip install -r requirements.txt
Set environment variables:
Create a .env file in the root directory with the following (replace with your actual tokens):

ini
Copy
Edit
OPENSOLAR_API_TOKEN=your_opensolar_api_token
OPENSOLAR_ORG_ID=your_opensolar_org_id
# Optionally add your Odoo credentials/settings here
Usage
Apply Django migrations:

bash
Copy
Edit
python manage.py migrate
Run the sync command:

bash
Copy
Edit
python manage.py sync_opensolar
This will fetch data from OpenSolar and update your local Django database models.

You can automate this via cron or task scheduler for regular syncs.

Project Structure
bash
Copy
Edit
"OpenSolar_Odoo_Sync/
├── apps/
│   └── api/                # Main Django app for OpenSolar/Odoo integration
│       ├── management/
│       │   └── commands/
│       │       └── sync_opensolar.py
│       ├── migrations/
│       ├── models.py
│       ├── ...
├── opensolar_sync/         # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── scripts/                # Helper scripts
├── tests/                  # Test files
├── requirements.txt
├── .env
├── .gitignore
└── manage.py
Contributing
Pull requests, bug reports, and feature requests are welcome. Please open an issue to discuss your proposal."

Author
Fraker — GitHub Profile

