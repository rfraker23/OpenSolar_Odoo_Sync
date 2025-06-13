@echo off
setlocal

rem ─────────────────────────────────────────────────────────────────────────────
rem Force Python 3 to use UTF-8 for stdout/stderr
set PYTHONUTF8=1

rem ─── Find script directory and project root ─────────────────────────────────
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "BASE=%SCRIPT_DIR%\.."
pushd "%BASE%" || (
  echo [%date% %time%] ERROR: Unable to resolve project root at %BASE% >> "%BASE%\logs\batch_marker.log"
  exit /b 1
)
set "BASE=%CD%"
popd

rem ─── Prepare logs folder ───────────────────────────────────────────────────
set "LOGDIR=%BASE%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo [%date% %time%] BATCH ENTERED >> "%LOGDIR%\batch_marker.log"

rem ─── Auto-detect Python in common venv names ───────────────────────────────
set "PYTHON="
for %%V in (venv .venv env .env) do (
  if exist "%BASE%\%%V\Scripts\python.exe" set "PYTHON=%BASE%\%%V\Scripts\python.exe"
)
if not defined PYTHON (
  echo [%date% %time%] ERROR: Python executable not found in venv folders >> "%LOGDIR%\batch_marker.log"
  exit /b 1
)

rem ─── Change into project root ──────────────────────────────────────────────
pushd "%BASE%"

rem ── 1) OpenSolar sync
echo [%date% %time%] Starting sync_opensolar.py >> "%LOGDIR%\sync_opensolar.log"
"%PYTHON%" manage.py sync_opensolar >> "%LOGDIR%\sync_opensolar.log" 2>&1 || (
  echo [%date% %time%] sync_opensolar FAILED with exit code %errorlevel% >> "%LOGDIR%\sync_opensolar.log"
  popd & exit /b %errorlevel%
)

rem ── 2) Contacts sync
echo [%date% %time%] Starting sync_contacts_to_odoo.py >> "%LOGDIR%\sync_contacts_to_odoo.log"
"%PYTHON%" manage.py sync_contacts_to_odoo >> "%LOGDIR%\sync_contacts_to_odoo.log" 2>&1 || (
  echo [%date% %time%] sync_contacts_to_odoo FAILED with exit code %errorlevel% >> "%LOGDIR%\sync_contacts_to_odoo.log"
  popd & exit /b %errorlevel%
)

rem ── 3) Projects sync
echo [%date% %time%] Starting sync_projects_to_odoo.py >> "%LOGDIR%\sync_projects_to_odoo.log"
"%PYTHON%" manage.py sync_projects_to_odoo >> "%LOGDIR%\sync_projects_to_odoo.log" 2>&1 || (
  echo [%date% %time%] sync_projects_to_odoo FAILED with exit code %errorlevel% >> "%LOGDIR%\sync_projects_to_odoo.log"
  popd & exit /b %errorlevel%
)

rem ── All done
echo [%date% %time%] ALL SCRIPTS COMPLETED SUCCESSFULLY >> "%LOGDIR%\batch_marker.log"

popd
endlocal
