# Mi Sensor Monitor

Monitor **Xiaomi Mi Temperature & Humidity Monitor 2 (LYWSD03MMC)** sensors over Bluetooth LE, visualise live data in a web UI, receive push alerts via Email, Telegram, or LINE, and integrate with **Apple Home** (HomeKit).

## Features

- Live dashboard with real-time temperature, humidity, and battery readings via WebSocket
- Historical charts with selectable time ranges (2 h → 7 d)
- Flexible alert rules: any metric × any comparison operator × per-sensor or global scope
- Per-rule cooldown to avoid notification spam
- Three notification channels: Email (SMTP), Telegram Bot, LINE Notify
- "Test notification" button to verify credentials without waiting for a real trigger
- BLE device scanner in the UI — click a discovered device to auto-fill its address
- Simulate mode for development without physical sensors
- **Apple HomeKit bridge** — sensors appear natively in the Home app, Siri, and automations

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+ · FastAPI · SQLAlchemy 2 (async) · SQLite · bleak |
| HomeKit | HAP-python (HomeKit Accessory Protocol bridge) |
| Frontend | React 18 · Vite · Tailwind CSS · Recharts |
| Notifications | aiosmtplib (email) · httpx (Telegram / LINE) |

## Quick start

### 1. Clone and configure

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — fill in SMTP / Telegram / LINE credentials as needed
```

### 2. Docker (recommended)

```bash
# Set SIMULATE_SENSORS=true in backend/.env (BLE is unavailable inside Docker on macOS/Windows)
docker compose up
```

Frontend → http://localhost:8001  
Backend API docs → http://localhost:8002/docs

With the optional HomeKit bridge:
```bash
docker compose --profile homekit up
```

### 3. Run locally (simulated data — no BLE hardware required)

```bash
SIMULATE=true ./start-dev.sh
```

### 4. Run locally with real sensors

```bash
./start-dev.sh
```

macOS will prompt for Bluetooth permission on first run.

## Make commands

A `Makefile` is included at the repo root for convenience:

```bash
make install       # install backend (uv) + frontend (npm) dependencies
make dev           # start backend + frontend
make dev-sim       # start with simulated sensor data
make dev-full      # simulated data + HomeKit bridge
make scan          # discover nearby BLE devices and list them (10s), then exit
make scan-sim      # same but with simulated data (no hardware needed)
make test          # run all 93 backend tests
make lint          # ruff check
make check         # format + lint + test
make clean         # remove Python cache + test artifacts
make clean-db      # delete SQLite database (recreated on startup)
make clean-all     # full clean including node_modules
```

Run `make` or `make help` to see all available commands.

## Manual setup (without Docker)

### Backend

```bash
cd backend
uv sync
SIMULATE_SENSORS=true uv run python run.py   # or omit SIMULATE_SENSORS for real BLE
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Configuration (`.env`)

| Variable | Default | Description |
|---|---|---|
| `SCAN_INTERVAL_SECONDS` | `60` | How often to poll each sensor |
| `SIMULATE_SENSORS` | `false` | Generate random readings instead of BLE |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` | — | Email credentials |
| `TELEGRAM_BOT_TOKEN` | — | From @BotFather |
| `LINE_NOTIFY_TOKEN` | — | Personal token from notify-bot.line.me |

## Adding sensors

1. Open the **Sensors** page and click **Scan BLE** to discover nearby devices.
2. Click a discovered `LYWSD03MMC` row to pre-fill its BLE address.
3. Give it a name and optional location, then save.

> **macOS note**: `bleak` returns a UUID string instead of a MAC address on macOS — this is expected. Copy the UUID from the scan result.

## Alert rule setup

Go to **Alert Rules** → **New Rule**:

| Field | Notes |
|---|---|
| Sensor | Leave blank to apply to all sensors |
| Metric | `temperature`, `humidity`, or `battery` |
| Operator | `>`, `<`, `>=`, `<=`, `==`, `!=` |
| Threshold | Numeric value (°C or %) |
| Channel | `email`, `telegram`, or `line` |
| Channel target | Email address · Telegram chat ID · LINE Notify token |
| Cooldown | Minimum minutes between repeat alerts for this rule |

Use the **Test** button to send a sample notification before going live.

### Getting a Telegram chat ID

1. Create a bot via [@BotFather](https://t.me/botfather) → copy the token into `TELEGRAM_BOT_TOKEN`.
2. Send any message to your new bot.
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` → find `"chat":{"id": ...}`.
4. Paste that number as the **Channel target** in your alert rule.

### Getting a LINE Notify token

Visit [notify-bot.line.me/my](https://notify-bot.line.me/my/), log in, and generate a personal access token. Paste it as the **Channel target** — no bot setup required.

## Apple HomeKit integration

Each sensor is exposed to HomeKit as an accessory containing three services:
**TemperatureSensor**, **HumiditySensor**, and **BatteryService** (including low-battery
status). Once paired, you can:

- View readings directly in the **Home app** on iPhone, iPad, or Mac
- Ask **Siri** "What's the temperature in the bedroom?"
- Build **Automations** ("If humidity > 70% turn on the fan")
- View historical graphs in the Home app

### Pairing steps

1. Make sure the main backend is running (the bridge reads from its API).
2. Start the HomeKit bridge:
   ```bash
   cd backend
   uv run python -m app.services.homekit_bridge
   ```
3. A QR code and an 8-digit PIN are printed to the terminal.
4. Open **Home app** → **+** → **Add Accessory**.
5. Scan the QR code, or tap **"I Don't Have a Code or Cannot Scan"** and enter the PIN.
6. Confirm the "Unsupported Accessory" prompt — this is normal for third-party HAP bridges.

Pairing info is stored in `backend/data/homekit/state.json`. If you delete this directory
you must remove the accessory in the Home app and re-pair.

### Start everything at once
```bash
# Docker
docker compose --profile homekit up

# Local
HOMEKIT=true ./start-dev.sh
# or with simulated data:
SIMULATE=true HOMEKIT=true ./start-dev.sh
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `HOMEKIT_PORT` | `51826` | UDP/TCP port for HAP protocol |
| `API_BASE_URL` | `http://localhost:8002` | Where the HomeKit bridge fetches readings from |

## Project layout

```
mi-sensor-collector/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app + WebSocket manager
│   │   ├── config.py          # Pydantic settings (reads .env)
│   │   ├── database.py        # SQLAlchemy async engine + session
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic request/response types
│   │   ├── api/               # REST route handlers
│   │   └── services/
│   │       ├── ble_scanner.py     # BLE polling loop + simulator + standalone CLI
│   │       ├── alert_engine.py    # Rule evaluation + cooldown logic
│   │       ├── homekit_bridge.py  # Apple HomeKit HAP bridge (standalone process)
│   │       └── notifiers/         # Email / Telegram / LINE senders
│   ├── data/                  # SQLite database + HomeKit state (auto-created; bind-mounted in Docker)
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/client.js      # All HTTP calls (axios)
│   │   ├── hooks/useWebSocket.js
│   │   ├── components/        # SensorCard, SensorChart, AlertRule*
│   │   └── pages/             # Dashboard, SensorsPage, AlertRulesPage, HistoryPage
│   ├── Dockerfile             # Multi-stage: Node build → nginx
│   └── nginx.conf             # Serves static files + proxies /api and /ws to backend
├── docs/                      # Architecture guide (GitHub Pages)
├── docker-compose.yml         # backend + frontend; homekit via --profile homekit
├── Makefile                   # dev / test / lint / scan / clean targets
└── start-dev.sh               # Local dev: backend + frontend (+ optional HomeKit bridge)
```
