@echo off
REM ── go to your project dir ───────────────────────────────
cd /d "C:\Users\seadmin\OpenSolarOdooAPI"

REM ── activate your virtualenv ──────────────────────────────
call venv\Scripts\activate.bat

REM ── run the three sync commands ──────────────────────────
python manage.py sync_opensolar
python manage.py sync_contacts_to_odoo
python manage.py sync_projects_to_odoo
