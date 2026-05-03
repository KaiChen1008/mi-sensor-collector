import asyncio
import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.api import alert_rules, readings, sensors
from app.config import settings
from app.database import init_db
from app.services import ble_scanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# --------------------------------------------------------------------------- #
#  WebSocket connection manager                                                 #
# --------------------------------------------------------------------------- #

class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.remove(ws)

    async def broadcast(self, payload: dict) -> None:
        message = json.dumps(payload)
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.remove(ws)


manager = ConnectionManager()


# --------------------------------------------------------------------------- #
#  App lifespan                                                                 #
# --------------------------------------------------------------------------- #

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    scanner = ble_scanner.BLEScanner()
    ble_scanner._scanner_instance = scanner
    ble_scanner.register_broadcast(manager.broadcast)
    await scanner.start()

    yield

    await scanner.stop()


app = FastAPI(title="Mi Sensor Monitor", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sensors.router, prefix="/api/sensors", tags=["sensors"])
app.include_router(readings.router, prefix="/api/readings", tags=["readings"])
app.include_router(alert_rules.router, prefix="/api/alert-rules", tags=["alert-rules"])


@app.get("/health")
async def health():
    return {"status": "ok", "simulate": settings.simulate_sensors}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep alive; client may send pings
    except WebSocketDisconnect:
        manager.disconnect(ws)
