@echo off
rem ─────────────────────────────────────────────────────────────────────────────
rem Force Python 3 to use UTF-8 for stdout/stderr (equivalent to -X utf8).
set PYTHONUTF8=1

rem ─────────────────────────────────────────────────────────────────────────────
rem  1) Define where logs live
rem  2) Drop a “marker” so we know the batch actually started
rem  3) Change directory to where manage.py lives
rem  4) Run each Django command via the venv’s python (UTF-8 mode guaranteed)
rem ─────────────────────────────────────────────────────────────────────────────

set "LOGDIR=C:\Users\seadmin\OpenSolarOdooAPI\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

rem ── MARKER: Did the batch even start?
echo [%date% %time%] BATCH ENTERED >> "%LOGDIR%\batch_marker.log"

rem ── Change into the Django project root (where manage.py is)
pushd "C:\Users\seadmin\OpenSolarOdooAPI"

rem ── 1) Run sync_opensolar with UTF-8 stdout/stderr
echo [%date% %time%] Starting sync_opensolar.py >> "%LOGDIR%\sync_opensolar.log"
"C:\Users\seadmin\OpenSolarOdooAPI\venv\Scripts\python.exe" manage.py sync_opensolar >> "%LOGDIR%\sync_opensolar.log" 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] sync_opensolar FAILED with exit code %errorlevel% >> "%LOGDIR%\sync_opensolar.log"
    popd
    exit /b %errorlevel%
)

rem ── 2) Run sync_contacts_to_odoo with UTF-8 stdout/stderr
echo [%date% %time%] Starting sync_contacts_to_odoo.py >> "%LOGDIR%\sync_contacts_to_odoo.log"
"C:\Users\seadmin\OpenSolarOdooAPI\venv\Scripts\python.exe" manage.py sync_contacts_to_odoo >> "%LOGDIR%\sync_contacts_to_odoo.log" 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] sync_contacts_to_odoo FAILED with exit code %errorlevel% >> "%LOGDIR%\sync_contacts_to_odoo.log"
    popd
    exit /b %errorlevel%
)

rem ── 3) Run sync_projects_to_odoo with UTF-8 stdout/stderr
echo [%date% %time%] Starting sync_projects_to_odoo.py >> "%LOGDIR%\sync_projects_to_odoo.log"
"C:\Users\seadmin\OpenSolarOdooAPI\venv\Scripts\python.exe" manage.py sync_projects_to_odoo >> "%LOGDIR%\sync_projects_to_odoo.log" 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] sync_projects_to_odoo FAILED with exit code %errorlevel% >> "%LOGDIR%\sync_projects_to_odoo.log"
    popd
    exit /b %errorlevel%
)

rem ── All done
echo [%date% %time%] ALL SCRIPTS COMPLETED SUCCESSFULLY >> "%LOGDIR%\sync_projects_to_odoo.log"

popd