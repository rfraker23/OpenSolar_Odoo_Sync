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



