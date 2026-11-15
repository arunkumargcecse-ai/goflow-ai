#!/usr/bin/env bash
set -euo pipefail

# A fresh per-Codespace API key is generated locally and never committed.
KEY_FILE="/tmp/goflow-codespaces-api-key"
if [[ ! -s "$KEY_FILE" ]]; then
  python -c 'import secrets; print(secrets.token_urlsafe(48))' > "$KEY_FILE"
  chmod 600 "$KEY_FILE"
fi
export GOFLOW_API_KEY="$(cat "$KEY_FILE")"
export GOFLOW_DATA_DIR="${CODESPACE_VOLUMES:-$HOME/.goflow}/data"
mkdir -p "$GOFLOW_DATA_DIR"

if ! pgrep -f "uvicorn main:app.*8000" >/dev/null 2>&1; then
  (cd backend && nohup python -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/goflow-api.log 2>&1 &)
fi
if ! pgrep -f "http.server 3000" >/dev/null 2>&1; then
  nohup python -m http.server 3000 --bind 0.0.0.0 > /tmp/goflow-web.log 2>&1 &
fi

cat <<EOF
goflow.ai services starting:
  Creator Studio: port 3000
  API:             port 8000
  API key:         $GOFLOW_API_KEY

In the Creator Studio, set Backend API URL to the forwarded HTTPS URL for port 8000
(the URL ending in -8000.app.github.dev), then enter the API key above.
Logs: /tmp/goflow-api.log and /tmp/goflow-web.log
EOF
