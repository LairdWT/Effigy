@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -B -m tools.provision %*
) else (
  python -B -m tools.provision %*
)
exit /b %errorlevel%
