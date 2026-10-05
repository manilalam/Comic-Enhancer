@echo off
REM Installs everything from the "dependencies" folder. No internet needed.
cd /d "%~dp0"

if exist dependencies\postgres16.tar (
  echo Loading PostgreSQL image...
  docker load -i dependencies\postgres16.tar
  if errorlevel 1 goto :error
)

if not exist backend\.venv (
  echo Creating virtual environment in backend\.venv ...
  python -m venv backend\.venv
  if errorlevel 1 goto :error
)

echo Installing Python packages from dependencies\python ...
backend\.venv\Scripts\python -m pip install --no-index --find-links dependencies\python -r backend\requirements.txt
if errorlevel 1 goto :error

if not exist backend\.env copy backend\.env.example backend\.env >nul

echo.
echo Done. Next: run "docker compose up -d", then follow "Run it" in README.md from step 3.
goto :eof

:error
echo Something failed. Check the message above.
exit /b 1
