#!/usr/bin/env bash
# Start backend + frontend (and optionally the HomeKit bridge) in development mode.
#
# Usage:
#   ./start-dev.sh                          → real BLE sensors
#   SIMULATE=true ./start-dev.sh            → simulated data (no BLE hardware needed)
#   HOMEKIT=true ./start-dev.sh             → also start the HomeKit bridge on :51826
#   SIMULATE=true HOMEKIT=true ./start-dev.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Setting up Python environment..."
uv sync --project "$ROOT/backend"

# Install frontend deps; re-run npm install if package.json is newer than node_modules
PKG="$ROOT/frontend/package.json"
NM="$ROOT/frontend/node_modules"
if [ ! -d "$NM" ] || [ "$PKG" -nt "$NM" ]; then
  echo "Installing frontend dependencies..."
  npm install --prefix "$ROOT/frontend" --silent
fi

SIMULATE=${SIMULATE:-false}
HOMEKIT=${HOMEKIT:-false}

echo "Starting backend  → http://localhost:8002  (simulate=$SIMULATE)"
cd "$ROOT/backend"
SIMULATE_SENSORS=$SIMULATE uv run python run.py &
BACKEND_PID=$!

echo "Starting frontend → http://localhost:8001"
npm run dev --prefix "$ROOT/frontend" &
FRONTEND_PID=$!

HOMEKIT_PID=""
if [ "$HOMEKIT" = "true" ]; then
  printf "Waiting for backend to be ready..."
  until curl -sf http://localhost:8002/health > /dev/null 2>&1; do
    printf "."
    sleep 1
  done
  echo " ready."
  echo "Starting HomeKit bridge → port 51826"
  uv run python -m app.services.homekit_bridge &
  HOMEKIT_PID=$!
fi

echo ""
echo "  Frontend  http://localhost:8001"
echo "  API docs  http://localhost:8002/docs"
[ "$HOMEKIT" = "true" ] && echo "  HomeKit   port 51826"
echo ""
echo "Press Ctrl+C to stop all processes."

trap 'kill "$BACKEND_PID" "$FRONTEND_PID" ${HOMEKIT_PID:+"$HOMEKIT_PID"} 2>/dev/null; exit' INT TERM EXIT
wait
