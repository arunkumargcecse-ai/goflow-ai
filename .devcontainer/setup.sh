#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update
sudo apt-get install -y --no-install-recommends ffmpeg
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

echo
echo "goflow.ai Codespaces environment is ready."
echo "FFmpeg: $(ffmpeg -version | head -n 1)"
