@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (echo Run provision.bat first. & exit /b 1)
.venv\Scripts\python.exe -B -m server
exit /b %errorlevel%
