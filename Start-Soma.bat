@echo off
REM Soma Ecosystem Desktop Launcher
REM Double-click this file to start the entire Soma ecosystem

setlocal EnableDelayedExpansion

REM Get the directory where this batch file is located
set "SOMA_ROOT=%~dp0"
set "SOMA_ROOT=%SOMA_ROOT:~0,-1%"

REM Initialize PowerShell command variable
set "PS_CMD="

REM Method 1: Check if pwsh (PowerShell 7+) is in PATH
where pwsh >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PS_CMD=pwsh"
    echo Found PowerShell 7+ (pwsh) in PATH
    goto :FOUND_POWERSHELL
)

REM Method 2: Check common PowerShell 7 installation paths
if exist "C:\Program Files\PowerShell\7\pwsh.exe" (
    set "PS_CMD=C:\Program Files\PowerShell\7\pwsh.exe"
    echo Found PowerShell 7 at: C:\Program Files\PowerShell\7\
    goto :FOUND_POWERSHELL
)

if exist "C:\Program Files\PowerShell\7-preview\pwsh.exe" (
    set "PS_CMD=C:\Program Files\PowerShell\7-preview\pwsh.exe"
    echo Found PowerShell 7 Preview at: C:\Program Files\PowerShell\7-preview\
    goto :FOUND_POWERSHELL
)

REM Method 3: Check if Windows PowerShell 5 is in PATH
where powershell.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set "PS_CMD=powershell.exe"
    echo Found Windows PowerShell 5 (powershell.exe) in PATH
    echo WARNING: PowerShell 7+ is recommended for best performance
    goto :FOUND_POWERSHELL
)

REM Method 4: Check common Windows PowerShell paths
if exist "%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" (
    set "PS_CMD=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
    echo Found Windows PowerShell at: %SystemRoot%\System32\WindowsPowerShell\v1.0\
    echo WARNING: PowerShell 7+ is recommended for best performance
    goto :FOUND_POWERSHELL
)

REM Method 5: Check if PowerShell is available via .NET Global Tools
if exist "%USERPROFILE%\.dotnet\tools\pwsh.exe" (
    set "PS_CMD=%USERPROFILE%\.dotnet\tools\pwsh.exe"
    echo Found PowerShell 7 via .NET Global Tools
    goto :FOUND_POWERSHELL
)

REM PowerShell not found - provide helpful error message
:NOT_FOUND
echo.
echo  ================================================
echo   POWERSHELL NOT FOUND
echo  ================================================
echo.
echo  ERROR: Could not find PowerShell on your system.
echo.
echo  Please install PowerShell 7 or later from:
echo  https://github.com/PowerShell/PowerShell/releases
echo.
echo  Or install via winget:
echo  winget install Microsoft.PowerShell
echo.
echo  Or install via Microsoft Store:
echo  Search for "PowerShell" in the Microsoft Store
echo.
echo  ================================================
pause
exit /b 1

:FOUND_POWERSHELL
echo.
echo  ================================================
echo   SOMA ECOSYSTEM STARTER
echo  ================================================
echo.
echo  Using: %PS_CMD%
echo.
echo  Starting Soma Ecosystem with full pre-flight checks...
echo  This may take 30-60 seconds depending on your system.
echo.
echo  Log file will be created in: %USERPROFILE%\.soma\logs\
echo.

REM Run the PowerShell startup script with error handling
"%PS_CMD%" -ExecutionPolicy Bypass -NoProfile -File "%SOMA_ROOT%\Start-SomaEcosystem.ps1" -VerboseLogging

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ================================================
    echo   STARTUP FAILED
echo  ================================================
    echo.
    echo  Exit code: %ERRORLEVEL%
    echo.
    echo  Check the log file for details:
    echo  %USERPROFILE%\.soma\logs\
    echo.
    pause
    exit /b 1
)

exit /b 0
