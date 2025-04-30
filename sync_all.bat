@echo off
REM force the Windows console into UTF-8 so emoji can be printed
chcp 65001 >nul
set PYTHONUTF8=1

set PROJECT_DIR=C:\Users\seadmin\OpenSolarOdooAPI
set PYTHON=%PROJECT_DIR%\venv\Scripts\python.exe
set MANAGE=%PROJECT_DIR%\manage.py
set LOG=%PROJECT_DIR%\sync_all.log

pushd "%PROJECT_DIR%"
echo ======================================== >> "%LOG%"
echo Starting sync at %DATE% %TIME%         >> "%LOG%"

"%PYTHON%" -X utf8 "%MANAGE%" sync_opensolar        >> "%LOG%" 2>&1
if ERRORLEVEL 1 echo sync_opensolar FAILED  >> "%LOG%"

"%PYTHON%" -X utf8 "%MANAGE%" sync_contacts_to_odoo >> "%LOG%" 2>&1
if ERRORLEVEL 1 echo sync_contacts FAILED    >> "%LOG%"

"%PYTHON%" -X utf8 "%MANAGE%" sync_projects_to_odoo >> "%LOG%" 2>&1
if ERRORLEVEL 1 echo sync_projects FAILED    >> "%LOG%"

echo Finished at %DATE% %TIME%               >> "%LOG%"
echo.                                       >> "%LOG%"
popd
