@echo off
REM Run ONCE with internet. Saves every dependency into the "dependencies" folder.
cd /d "%~dp0"
if not exist dependencies\python mkdir dependencies\python

echo Downloading Python packages...
python -m pip download -r backend\requirements.txt -d dependencies\python
if errorlevel 1 goto :error

where docker >nul 2>nul
if errorlevel 1 (
  echo Docker not found, skipping the PostgreSQL image.
) else (
  echo Downloading PostgreSQL image, about 400 MB...
  docker pull postgres:16
  if errorlevel 1 goto :error
  docker save -o dependencies\postgres16.tar postgres:16
  if errorlevel 1 goto :error
)

echo.
echo Done. Every dependency is in the dependencies folder.
goto :eof

:error
echo Something failed. Check the message above.
exit /b 1
