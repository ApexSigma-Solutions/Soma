@echo off
REM Load .env file and start InGress
cd /d "%~dp0\.."
for /f "tokens=*" %%a in (.env) do (
    echo %%a | findstr /v "^#" | findstr "=" >nul
    if not errorlevel 1 set %%a
)
cd InGress
python -m soma_ingress.main
