@echo off
REM Activate venv (if you need to)
REM call "C:\Users\seadmin\OpenSolar Odoo API\venv\Scripts\activate.bat"
REM Run the sync_all management command
"C:\Users\seadmin\OpenSolar Odoo API\venv\Scripts\python.exe" "%~dp0manage.py" sync_all
