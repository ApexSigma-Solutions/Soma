@echo off
rem Down Ecosystem Shortcut
rem Pass any arguments to stop_ecosystem.ps1 (e.g., -Full, -AppsOnly)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_ecosystem.ps1" %*
