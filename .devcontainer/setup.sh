#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y --no-install-recommends ffmpeg python3-venv

# Use an isolated project environment; system Python may be externally managed.
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements.txt

echo
echo "goflow.ai Codespaces environment is ready."
echo "Python: $(.venv/bin/python --version)"
echo "Uvicorn: $(.venv/bin/python -m uvicorn --version)"
echo "FFmpeg: $(ffmpeg -version | head -n 1)"
