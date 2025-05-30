chcp 65001
@echo off
cd /d C:\Users\seadmin\OpenSolarOdooAPI

C:\Users\seadmin\OpenSolarOdooAPI\venv\Scripts\python.exe manage.py sync_opensolar >> sync_opensolar.log 2>&1
C:\Users\seadmin\OpenSolarOdooAPI\venv\Scripts\python.exe manage.py sync_contacts_to_odoo >> sync_contacts_to_odoo.log 2>&1
C:\Users\seadmin\OpenSolarOdooAPI\venv\Scripts\python.exe manage.py sync_projects_to_odoo >> sync_projects_to_odoo.log 2>&1

