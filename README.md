# OpenSolar → Django → Odoo Sync

A turnkey integration that pulls your OpenSolar data into Django models, and pushes customers, projects, proposals and system‐component details into Odoo 17 via JSON-RPC. Designed to run manually, via a secure HTTP endpoint, or on a schedule (Windows Task Scheduler / Power Automate).

---

## 🔎 Features

- **Pull** OpenSolar data into Django  
  – Projects, customers, share links & proposals  
  – Full system details: modules, inverters (with micro-inverter qty override), batteries  
- **Push** into Odoo Studio custom models  
  – `res.partner` contacts  
  – `x_projects` with flattened fields  
- **De-duplication**  
  – Contacts: external ID or email  
  – Projects: external ID + customer name  
- **Change-logging** on updates  
- **Secure “full sync”** endpoint:  
  ```http
  GET /api/sync-all/?key=<SYNC_SECRET>

Scheduling
– Local: Windows Task Scheduler
– Cloud: Power Automate (hourly Flow)

📁 Repository Layout
OpenSolar_Odoo_Sync/
├── api/
│   ├── management/
│   │   └── commands/
│   │       ├── sync_opensolar.py
│   │       ├── sync_contacts_to_odoo.py
│   │       └── sync_projects_to_odoo.py
│   ├── migrations/
│   ├── models.py
│   ├── views.py
│   └── urls.py
├── my_django_project/
│   ├── settings.py
│   └── ...
├── .env.example
├── README.md
├── requirements.txt
└── manage.py

🛠️ Prerequisites
Python 3.10+

Django 5.x

An OpenSolar API token & Org ID

Odoo 17 Enterprise with Studio custom fields

(Optional) Windows machine for Task Scheduler

⚙️ Setup
Clone & install
git clone https://github.com/rfraker23/OpenSolar_Odoo_Sync.git
cd OpenSolar_Odoo_Sync
python -m venv venv
source venv/bin/activate    # macOS/Linux
# .\venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt

Env configuration
Copy .env.example → .env and fill in your credentials:
# OpenSolar
OPENSOLAR_API_TOKEN=your_opensolar_token
OPENSOLAR_ORG_ID=123456

# Odoo
ODOO_URL=https://your-odoo-host.com
ODOO_DB=your_db_name
ODOO_API_USERNAME=odoo_api_user
ODOO_API_TOKEN=odoo_api_token

# Sync endpoint protection
SYNC_SECRET=some_long_random_string

🚀 Usage
Manual
bash
Copy
Edit
# 1) Pull OpenSolar → Django
python manage.py sync_opensolar

# 2) Push contacts → Odoo
python manage.py sync_contacts_to_odoo

# 3) Push projects → Odoo
python manage.py sync_projects_to_odoo
Full-Sync Endpoint
Start your server:

bash
Copy
Edit
python manage.py runserver
Trigger:

http
Copy
Edit
GET http://127.0.0.1:8000/api/sync-all/?key=<SYNC_SECRET>
Returns JSON {"status":"ok"} on success.

⏰ Scheduling
Windows Task Scheduler
Open Task Scheduler → Create Task.

Name: “OpenSolar → Odoo Sync”.

Trigger: Daily or Hourly as desired.

Action:

Copy
Edit
manage.py sync_all
Start in:

makefile
Copy
Edit
C:\Users\seadmin\OpenSolarOdooAPI
Save & test.

Power Automate
Create an Hourly Recurrence Flow

Add an HTTP action → GET https://<your-host>/api/sync-all/?key=<SYNC_SECRET>

🔢 Odoo Studio Fields
Ensure your x_projects model has these fields:

Odoo Field	OpenSolar Data
x_name	Customer name
x_studio_partner_id	res.partner ID
x_studio_opensolar_external_id	Project external ID
x_studio_open_solar_proposal	Proposal share-link URL
x_studio_value	Proposal price
x_studio_change_order_price	Proposal price
x_studio_system_size_kw_1	System size (kW)
x_studio_module_manufacturer_name	First module manufacturer
x_studio_module_type	First module code
x_studio_module_qty	First module quantity
x_studio_inverter_manufacturer_name	First inverter manufacturer
x_studio_inverter_type	First inverter code
x_studio_inverter_qty	First inverter quantity
x_studio_battery_manufacturer_name	First battery manufacturer
x_studio_battery_type	First battery code
x_studio_battery_quantity	First battery quantity

🤝 Contributing
Fork the repo

Create a feature branch

Commit & push

Open a Pull Request

Built with :heart: by Sun Energy Partners





