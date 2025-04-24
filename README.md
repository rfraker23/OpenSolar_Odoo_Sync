# OpenSolar → Django → Odoo Sync Integration

This Django-based integration pulls data from the OpenSolar API into your local Django models, then pushes contacts and projects (with proposals, pricing, system size, and system components) into Odoo via its JSON-RPC interface.

---

## Contents

1. [Requirements](#requirements)  
2. [Installation & Configuration](#installation--configuration)  
3. [Environment Variables](#environment-variables)  
4. [Django Setup](#django-setup)  
5. [Usage](#usage)  
   - Management Commands  
   - HTTP “sync_all” Endpoint  
6. [Scheduling](#scheduling)  
7. [Logging & Troubleshooting](#logging--troubleshooting)  
8. [FAQ](#faq)  

---

## Requirements

- Python 3.11+  
- Django 5.2+  
- Pip (for dependencies)  
- Windows Task Scheduler (or cron on Linux/macOS)  
- Odoo 17 (or compatible) with the following custom fields:

  - **Contacts** (`res.partner`):  
    - `x_studio_opensolar_external_id` (Integer)  
  - **Projects** (`x_projects`):  
    - `x_name`  
    - `x_studio_partner_id`  
    - `x_studio_opensolar_external_id`  
    - `x_studio_open_solar_proposal`  
    - `x_studio_value`  
    - `x_studio_change_order_price`  
    - `x_studio_system_size_kw_1`  
    - _Plus component lines for modules, inverters, batteries…_  

---

## Installation & Configuration

```bash
# 1) Clone repo
git clone https://github.com/rfraker23/my-django-project
cd my-django-project

# 2) Create & activate virtualenv
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Apply migrations
python manage.py migrate
