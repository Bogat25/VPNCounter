@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Run scripts\setup.ps1 first, then launch VPN Counter again.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m vpn_counter
