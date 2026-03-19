@echo off
setlocal
cd /d %~dp0
powershell -ExecutionPolicy Bypass -File "%~dp0stop_isolated_demo.ps1"
endlocal
