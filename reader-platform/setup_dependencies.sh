#!/usr/bin/env bash
# Run ONCE with internet. Saves every dependency into the "dependencies" folder.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p dependencies/python

echo "Downloading Python packages..."
python3 -m pip download -r backend/requirements.txt -d dependencies/python

if command -v docker >/dev/null 2>&1; then
  echo "Downloading PostgreSQL image (about 400 MB)..."
  docker pull postgres:16
  docker save -o dependencies/postgres16.tar postgres:16
else
  echo "Docker not found, skipping the PostgreSQL image."
fi

echo
echo "Done. Every dependency is in the dependencies folder."
