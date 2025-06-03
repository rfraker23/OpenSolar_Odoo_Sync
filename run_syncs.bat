chcp 65001
@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM Batch file to run three Python scripts sequentially
REM ─────────────────────────────────────────────────────────────────────────────

REM If needed, set the full path to your Python executable.
REM Otherwise, leave as just "python" if Python is already on your PATH.
SET "PYTHON_EXE=C:\Users\seadmin\venv\Scripts\python.exe"


REM ──────────────── Run script OpenSola ────────────────
"%PYTHON_EXE%" "C:\Users\seadmin\OpenSolarOdooAPI\apps\api\management\commands\sync_opensolar.py"
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: script1.py exited with code %ERRORLEVEL%.
    echo Aborting batch.
    exit /b %ERRORLEVEL%
)

REM ──────────────── Run script Odoo Contacts ────────────────
"%PYTHON_EXE%" "C:\Users\seadmin\OpenSolarOdooAPI\apps\api\management\commands\sync_contacts_to_odoo.py"
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: script2.py exited with code %ERRORLEVEL%.
    echo Aborting batch.
    exit /b %ERRORLEVEL%
)

REM ──────────────── Run script Odoo Projects ────────────────
"%PYTHON_EXE%" "C:\Users\seadmin\OpenSolarOdooAPI\apps\api\management\commands\sync_projects_to_odoo.py"
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: script3.py exited with code %ERRORLEVEL%.
    echo Aborting batch.
    exit /b %ERRORLEVEL%
)

echo.
echo All three scripts completed successfully.
pause
