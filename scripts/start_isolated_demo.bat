@echo off
setlocal
cd /d %~dp0
powershell -ExecutionPolicy Bypass -File "%~dp0start_isolated_demo.ps1"
endlocal
