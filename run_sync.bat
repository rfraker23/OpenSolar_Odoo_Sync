@echo off
REM activate your venv
call C:\Users\seadmin\DJANGO2025\venv\Scripts\activate.bat

REM run the three management commands in sequence
python manage.py sync_opensolar
python manage.py sync_contacts_to_odoo
python manage.py sync_projects_to_odoo
