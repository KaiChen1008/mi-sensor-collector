# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend (run from `backend/`)
```bash
# First-time setup
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

# Start with real BLE sensors (uvicorn with reload=True)
.venv/bin/python run.py

# Start with simulated data (no BLE hardware needed)
SIMULATE_SENSORS=true .venv/bin/python run.py

# API docs available at http://localhost:8000/docs
```

### Frontend (run from `frontend/`)
```bash
npm install       # first-time setup
npm run dev       # dev server on :3000 with HMR
npm run build     # production build to dist/
```

### Tests (run from `backend/`)
```bash
.venv/bin/pytest           # all 73 tests
.venv/bin/pytest -v        # verbose
.venv/bin/pytest tests/test_alert_engine.py        # single file
.venv/bin/pytest tests/test_api_sensors.py -k create   # single test
```
Tests use an in-memory SQLite database and mock all BLE and external HTTP calls.
`SIMULATE_SENSORS=true` is set automatically in `conftest.py`.

### HomeKit bridge (run from `backend/`)
```bash
python -m app.services.homekit_bridge     # starts on port 51826
HOMEKIT_PORT=51826 python -m app.services.homekit_bridge
```
On first run, a QR code and 8-digit PIN are printed. Open **Home app → + → Add Accessory** and scan the QR code (or enter the PIN). HAP pairing state is persisted to `data/homekit/state.json`.

### Start all three together (from repo root)
```bash
./start-dev.sh                          # backend + frontend
SIMULATE=true ./start-dev.sh            # with simulated sensor data
HOMEKIT=true ./start-dev.sh             # also start HomeKit bridge
SIMULATE=true HOMEKIT=true ./start-dev.sh
```

The Vite dev server proxies `/api` and `/ws` to `localhost:8000`, so the frontend always talks to the backend through the same origin.

## Architecture

### Data flow
```
BLEScanner (asyncio task)
  └─► read_sensor_ble() / _simulate_reading()
        └─► Reading persisted to SQLite
              └─► evaluate_rules() → fire_alert() → Notifier.send()
              └─► _broadcast() → WebSocket → frontend Dashboard
```

### Backend (`backend/app/`)

**Entry point**: `main.py` — FastAPI app with a `lifespan` context that initialises the DB, creates `BLEScanner`, registers the WebSocket broadcast function, and wires the three API routers.

**BLE loop** (`services/ble_scanner.py`): `BLEScanner` runs as a persistent `asyncio.Task`. Every `SCAN_INTERVAL_SECONDS` it fetches all active sensors from the DB and calls `read_sensor_ble()` (or the simulator) for each. The module-level `_scanner_instance` and `_ws_broadcast_fn` globals let the API routes trigger manual reads and the WebSocket layer receive push events without circular imports.

**Alert engine** (`services/alert_engine.py`): called synchronously after each reading is committed. Fetches all active `AlertRule` rows whose `sensor_id` matches or is NULL (= all sensors), checks the comparison operator and cooldown window, then dispatches to the appropriate `Notifier` and writes an `AlertLog` row.

**Notifiers** (`services/notifiers/`): `base.py` defines the `BaseNotifier` ABC (`send(target, subject, body)`). The `NOTIFIERS` dict in `__init__.py` is the registry — add a new channel by subclassing `BaseNotifier` and registering it there.

**Config** (`config.py`): Pydantic `BaseSettings` reads from `.env` (copy from `.env.example`). Key variables: `APP_HOST`/`APP_PORT` (default `0.0.0.0:8000`), `SCAN_INTERVAL_SECONDS` (default `60`), `SIMULATE_SENSORS`, `HOMEKIT_PORT` (default `51826`), `API_BASE_URL` (default `http://localhost:8000`), plus SMTP/Telegram/LINE credentials. The `simulate_sensors` flag is the main toggle for development without hardware.

**Database** (`database.py`): SQLAlchemy 2.0 async with `aiosqlite`. The `data/sensors.db` file is created automatically on startup. `init_db()` runs `metadata.create_all` — no migration tooling is set up; schema changes require dropping and recreating the DB.

**Models**: `AlertRule.sensor_id = NULL` means the rule applies to every sensor. `AlertLog` is append-only; it records both successful sends and failures (with `error_message`).

**HomeKit bridge** (`services/homekit_bridge.py`): a standalone process that runs a HAP (HomeKit Accessory Protocol) server using `HAP-python`. It polls `/api/readings/latest` every `POLL_INTERVAL_SECONDS` and pushes updates to HomeKit characteristics. Each sensor is represented as a `Bridge` child accessory with `TemperatureSensor`, `HumiditySensor`, and `BatteryService` services. The bridge is intentionally decoupled from the SQLAlchemy session — it only speaks to the REST API over HTTP, so it can run on a different machine. HAP state (cryptographic keys and pairing info) lives in `data/homekit/state.json`.

### Frontend (`frontend/src/`)

**Routing**: React Router with four pages — Dashboard, SensorsPage, AlertRulesPage, HistoryPage.

**Real-time**: `useWebSocket` hook (auto-reconnects every 3 s, pings every 20 s). The Dashboard page subscribes and merges incoming `{type: "reading", ...}` frames into local state, keyed by `sensor_id`.

**API layer**: all HTTP calls are in `api/client.js` (thin axios wrappers). Components never call axios directly.

**Styling**: Tailwind CSS. Shared utility classes (`input`, `label`, `btn-primary`, `btn-secondary`, `btn-danger`, `btn-xs`) are defined in `index.css` under `@layer components`.

## Key constraints

- **HomeKit bridge is a separate process**: it must be started independently of the FastAPI server. Pairing info is lost if `data/homekit/` is deleted — you'll need to re-pair in the Home app (remove the accessory first).
- **HAP-python uses its own asyncio loop**: do not embed the bridge inside the FastAPI lifespan — it will deadlock.

- **macOS BLE addresses are UUIDs**, not MAC addresses. `bleak` returns a UUID string on macOS; the `ble_address` column stores whichever format the OS provides.
- **No DB migrations**: dropping `data/sensors.db` is the current reset strategy for schema changes.
- **LINE Notify `channel_target`** is the user's personal access token (not a channel name) — each recipient needs their own token.
- **Telegram `channel_target`** is the numeric chat ID, not the username.
