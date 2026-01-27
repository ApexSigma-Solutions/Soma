@echo off
REM =============================================================================
REM OmegaKG Capture Server Startup Script for Windows Task Scheduler
REM =============================================================================

echo ========================================
echo OmegaKG Capture Server Startup
echo ========================================
echo.

REM Change to the project directory
cd /d "D:\projects\OmegaKG\Omega_KG_stable"

REM Activate virtual environment
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found at .venv\Scripts\activate.bat
)

REM Start the capture server
echo Starting capture server...
echo Server will run on http://localhost:8765
echo Health check: http://localhost:8765/health
echo.
echo Press Ctrl+C to stop the server
echo.

python -m omega_kg.capture_server

REM If we get here, the server has stopped
echo.
echo Capture server has stopped.
pause
