# OpenSolar → Django → Odoo Integration

This project syncs OpenSolar project and customer data into Odoo 17 Enterprise using a Django-based API layer. It's designed to automate proposal syncing, customer creation, project creation, and solar component tracking (modules, batteries, inverters).

---

## 🔧 Features

- ✅ Pulls OpenSolar projects, proposals, and components into Django models  
- ✅ Pushes customers as `res.partner` records in Odoo  
- ✅ Pushes projects to a custom `x_projects` model in Odoo Studio  
- ✅ Syncs manufacturer, type/code, and quantity for:
  - Modules
  - Inverters
  - Batteries
- ✅ Logs all changes to existing records during sync  
- ✅ Prevents duplication using external IDs and customer names  
- ✅ Includes `sync_all` endpoint to trigger full sync  
- ✅ Local batch scheduling using Windows Task Scheduler  
- ✅ Remote triggering via secure `sync-all/?key=...` URL

---

## 📁 Project Structure

```text
DJANGO2025/
│
├── api/
│   ├── management/
│   │   └── commands/
│   │       ├── sync_opensolar.py
│   │       ├── sync_contacts_to_odoo.py
│   │       └── sync_projects_to_odoo.py
│   ├── models.py
│   ├── views.py
│   └── urls.py
│
├── my_django_project/
│   └── settings.py
│
├── .env               # Contains secret keys and credentials
├── README.md
└── manage.py
