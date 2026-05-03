#!/usr/bin/env bash
# Start backend + frontend (and optionally the HomeKit bridge) in development mode.
#
# Usage:
#   ./start-dev.sh                    → real BLE sensors
#   SIMULATE=true ./start-dev.sh      → simulated data (no BLE hardware needed)
#   HOMEKIT=true ./start-dev.sh       → also start the HomeKit bridge on :51826

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"

# Build venv if missing
if [ ! -f "$ROOT/backend/.venv/bin/python" ]; then
  echo "Creating Python venv..."
  python3 -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/pip" install -q -r "$ROOT/backend/requirements.txt"
fi

# Install frontend deps if missing
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "Installing frontend deps..."
  cd "$ROOT/frontend" && npm install
fi

SIMULATE=${SIMULATE:-false}
HOMEKIT=${HOMEKIT:-false}

echo "Starting backend on :8000 (simulate=$SIMULATE)..."
cd "$ROOT/backend"
SIMULATE_SENSORS=$SIMULATE .venv/bin/python run.py &
BACKEND_PID=$!

echo "Starting frontend on :3000..."
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

HOMEKIT_PID=""
if [ "$HOMEKIT" = "true" ]; then
  echo "Starting HomeKit bridge on :51826..."
  sleep 2  # wait for backend to be ready
  cd "$ROOT/backend"
  .venv/bin/python -m app.services.homekit_bridge &
  HOMEKIT_PID=$!
fi

trap "kill $BACKEND_PID $FRONTEND_PID ${HOMEKIT_PID} 2>/dev/null" EXIT INT TERM
wait
