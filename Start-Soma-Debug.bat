@echo off
setlocal EnableDelayedExpansion

REM Soma Ecosystem Debug Launcher
REM This version shows the window and logs debug information

echo Soma Ecosystem Debug Launcher
echo ================================
echo.

REM Get the directory where this batch file is located
set "SOMA_ROOT=%~dp0"
set "SOMA_ROOT=%SOMA_ROOT:~0,-1%"

echo Script location: %SOMA_ROOT%
echo.

REM Initialize PowerShell command variable
set "PS_CMD="

REM Method 1: Check if pwsh (PowerShell 7+) is in PATH
where pwsh >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PS_CMD=pwsh"
    echo [OK] Found PowerShell 7+ (pwsh) in PATH
    goto FOUND_POWERSHELL
)

REM Method 2: Check common PowerShell 7 installation paths
if exist "C:\Program Files\PowerShell\7\pwsh.exe" (
    set "PS_CMD=C:\Program Files\PowerShell\7\pwsh.exe"
    echo [OK] Found PowerShell 7 at: C:\Program Files\PowerShell\7\
    goto FOUND_POWERSHELL
)

if exist "C:\Program Files\PowerShell\7-preview\pwsh.exe" (
    set "PS_CMD=C:\Program Files\PowerShell\7-preview\pwsh.exe"
    echo [OK] Found PowerShell 7 Preview at: C:\Program Files\PowerShell\7-preview\
    goto FOUND_POWERSHELL
)

REM Method 3: Check if Windows PowerShell 5 is in PATH
where powershell.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PS_CMD=powershell.exe"
    echo [OK] Found Windows PowerShell 5 (powershell.exe) in PATH
    echo [WARNING] PowerShell 7+ is recommended for best performance
    goto FOUND_POWERSHELL
)

REM Method 4: Check common Windows PowerShell paths
if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
    set "PS_CMD=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
    echo [OK] Found Windows PowerShell at: %SystemRoot%\System32\WindowsPowerShell\v1.0\
    echo [WARNING] PowerShell 7+ is recommended for best performance
    goto FOUND_POWERSHELL
)

REM PowerShell not found
:NOT_FOUND
echo.
echo [ERROR] Could not find PowerShell on your system.
echo.
echo Please install PowerShell 7 or later from:
echo https://github.com/PowerShell/PowerShell/releases
echo.
pause
exit /b 1

:FOUND_POWERSHELL
echo.
echo PowerShell executable: %PS_CMD%
echo.

REM Check if the PowerShell script exists
set "PS_SCRIPT=%SOMA_ROOT%\Start-SomaEcosystem.ps1"
echo Checking for script: %PS_SCRIPT%

if not exist "%PS_SCRIPT%" (
    echo [ERROR] PowerShell script not found: %PS_SCRIPT%
    echo.
    echo Current directory: %CD%
    echo Script root: %SOMA_ROOT%
    pause
    exit /b 1
)

echo [OK] Found PowerShell script
echo.

REM Create log directory
if not exist "%USERPROFILE%\.soma\logs" (
    mkdir "%USERPROFILE%\.soma\logs" 2>nul
)

REM Generate timestamp for log file
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-3 delims=: " %%a in ('time /t') do (set mytime=%%a%%b%%c)
set "LOG_FILE=%USERPROFILE%\.soma\logs\debug-startup-%mydate%-%mytime%.log"

echo Log file: %LOG_FILE%
echo.

REM Run the PowerShell script
echo Starting Soma Ecosystem...
echo ========================================
echo.

"%PS_CMD%" -ExecutionPolicy Bypass -NoProfile -File "%PS_SCRIPT%" -VerboseLogging

set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo ========================================
echo Exit code: %EXIT_CODE%
echo.

if %EXIT_CODE% NEQ 0 (
    echo [ERROR] Startup failed with exit code %EXIT_CODE%
    echo.
    echo Check the log file for details:
    echo %LOG_FILE%
)

echo.
echo Press any key to close this window...
pause >nul
exit /b %EXIT_CODE%
