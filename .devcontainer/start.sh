#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Self-heal older Codespaces where postCreate dependency installation did not finish.
if [[ ! -x ".venv/bin/python" ]] || ! .venv/bin/python -c 'import uvicorn' >/dev/null 2>&1; then
  echo "Preparing isolated Python environment and installing backend requirements..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r backend/requirements.txt
fi

STATE_DIR="$HOME/.goflow"
KEY_FILE="$STATE_DIR/codespaces-api-key"
mkdir -p "$STATE_DIR"
chmod 700 "$STATE_DIR"
if [[ ! -s "$KEY_FILE" ]]; then
  .venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))' > "$KEY_FILE"
  chmod 600 "$KEY_FILE"
fi
export GOFLOW_API_KEY="$(cat "$KEY_FILE")"
export GOFLOW_DATA_DIR="${CODESPACE_VOLUMES:-$STATE_DIR}/data"
mkdir -p "$GOFLOW_DATA_DIR"

if ! pgrep -f '[u]vicorn main:app.*--port 8000' >/dev/null 2>&1; then
  (cd backend && nohup "$OLDPWD/.venv/bin/python" -m uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/goflow-api.log 2>&1 &)
fi
if ! pgrep -f '[p]ython -m http.server 3000' >/dev/null 2>&1; then
  nohup .venv/bin/python -m http.server 3000 --bind 0.0.0.0 > /tmp/goflow-web.log 2>&1 &
fi

cat <<EOF
goflow.ai services starting:
  Creator Studio: port 3000
  API:             port 8000
  API key:         $GOFLOW_API_KEY

Set Backend API URL to the forwarded HTTPS URL for port 8000
(the URL ending in -8000.app.github.dev), then enter the API key above.
Retrieve the key later with: cat "$KEY_FILE"
Logs: /tmp/goflow-api.log and /tmp/goflow-web.log
EOF
