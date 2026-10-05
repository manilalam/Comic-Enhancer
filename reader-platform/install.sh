#!/usr/bin/env bash
# Installs everything from the "dependencies" folder. No internet needed.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f dependencies/postgres16.tar ]; then
  echo "Loading PostgreSQL image..."
  docker load -i dependencies/postgres16.tar
fi

if [ ! -d backend/.venv ]; then
  echo "Creating virtual environment in backend/.venv ..."
  python3 -m venv backend/.venv
fi

echo "Installing Python packages from dependencies/python ..."
backend/.venv/bin/python -m pip install --no-index --find-links dependencies/python -r backend/requirements.txt

[ -f backend/.env ] || cp backend/.env.example backend/.env

echo
echo "Done. Next: run 'docker compose up -d', then follow 'Run it' in README.md from step 3."
