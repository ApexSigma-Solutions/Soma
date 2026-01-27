@echo off
REM Omega Full Stack Launcher - Batch Script
REM This script runs cleanup_before_start.ps1 followed by start_full_stack.ps1
REM The script is idempotent - running it multiple times will safely restart services

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set CLEANUP_SCRIPT=%SCRIPT_DIR%cleanup_before_start.ps1
set START_SCRIPT=%SCRIPT_DIR%start_full_stack.ps1

echo ========================================
echo Omega Full Stack Launcher
echo ========================================
echo.

REM Check if PowerShell is available
where powershell >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: PowerShell is not available on this system.
    pause
    exit /b 1
)

REM Check if scripts exist
if not exist "%CLEANUP_SCRIPT%" (
    echo ERROR: Cleanup script not found at %CLEANUP_SCRIPT%
    pause
    exit /b 1
)

if not exist "%START_SCRIPT%" (
    echo ERROR: Start script not found at %START_SCRIPT%
    pause
    exit /b 1
)

echo [1/2] Running cleanup script...
powershell -ExecutionPolicy Bypass -File "%CLEANUP_SCRIPT%"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Cleanup script failed with error code %ERRORLEVEL%
    pause
    exit /b 1
)
echo Cleanup completed successfully.
echo.

echo [2/2] Starting full stack...
powershell -ExecutionPolicy Bypass -File "%START_SCRIPT%" -SkipCleanup
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Start script failed with error code %ERRORLEVEL%
    pause
    exit /b 1
)

echo.
echo ========================================
echo Omega full stack started successfully!
echo ========================================
pause
