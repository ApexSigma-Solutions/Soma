@echo off
setlocal

echo Soma Ecosystem Debug Launcher
echo ================================
echo.

cd /d "%~dp0"
echo Working directory: %CD%
echo.

echo Detecting PowerShell...
echo.

if exist "C:\Program Files\PowerShell\7-preview\pwsh.exe" (
    echo Found: PowerShell 7 Preview
    set PS_CMD="C:\Program Files\PowerShell\7-preview\pwsh.exe"
    goto :run
)

if exist "C:\Program Files\PowerShell\7\pwsh.exe" (
    echo Found: PowerShell 7
    set PS_CMD="C:\Program Files\PowerShell\7\pwsh.exe"
    goto :run
)

where pwsh >nul 2>&1
if %errorlevel% == 0 (
    echo Found: PowerShell 7 in PATH
    set PS_CMD=pwsh
    goto :run
)

where powershell >nul 2>&1
if %errorlevel% == 0 (
    echo Found: Windows PowerShell 5
    set PS_CMD=powershell
    goto :run
)

echo ERROR: PowerShell not found!
pause
exit /b 1

:run
echo.
echo Starting Soma Ecosystem...
echo This will take 30-60 seconds...
echo.

if not exist "%USERPROFILE%\.soma\logs" mkdir "%USERPROFILE%\.soma\logs"

%PS_CMD% -ExecutionPolicy Bypass -File "Start-SomaEcosystem.ps1" -SkipDocker -VerboseLogging

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Startup failed with code %errorlevel%
    echo Check logs: %USERPROFILE%\.soma\logs\
    pause
    exit /b %errorlevel%
)

echo.
echo SUCCESS! Opening Cortex Dashboard...
timeout /t 2 >nul
start http://localhost:6001

echo.
echo Press any key to exit...
pause >nul
exit /b 0
