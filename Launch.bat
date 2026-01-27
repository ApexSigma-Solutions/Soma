@echo off
:: OmegaKG Launcher
:: Detaches the Master Ecosystem Script and exits.
:: The script itself handles the service startup and opening the browser.

cd /d "%~dp0"

echo Starting OmegaKG Ecosystem in the background...
start "" powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File "start_ecosystem.ps1" -Persistent

echo.
echo ============================================================
echo OmegaKG Core is starting.
echo The dashboard (http://localhost:6001) will open automatically
echo once the services are initialized.
echo ============================================================
echo.

timeout /t 5 >nul
exit
