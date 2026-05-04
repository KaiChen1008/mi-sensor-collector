"""
BLE scanner for Xiaomi LYWSD03MMC (Mi Temperature & Humidity Monitor 2).

The sensor exposes temperature + humidity + battery on a single GATT characteristic.
Data layout (5 bytes):
  [0:2]  int16 little-endian  → temperature / 100  (°C)
  [2]    uint8               → humidity (%)
  [3:5]  uint16 little-endian → battery voltage / 1000 (V)
Battery % is estimated from voltage (2.1 V ≅ 0 %, 3.1 V ≅ 100 %).
"""

import sys
from pathlib import Path

if __name__ == "__main__":
    # Allow `uv run app/services/ble_scanner.py` from the backend/ directory
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.reading import Reading
from app.models.sensor import Sensor
from app.services.alert_engine import evaluate_rules

logger = logging.getLogger(__name__)

CHAR_UUID = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6"

# Set by main.py after startup so the API can trigger manual reads
_scanner_instance: "BLEScanner | None" = None


@dataclass
class SensorData:
    temperature: float
    humidity: float
    battery: int  # percent


# --------------------------------------------------------------------------- #
#  Broadcasting to WebSocket clients (registered from main.py)                 #
# --------------------------------------------------------------------------- #

_ws_broadcast_fn = None


def register_broadcast(fn) -> None:
    global _ws_broadcast_fn
    _ws_broadcast_fn = fn


async def _broadcast(payload: dict) -> None:
    if _ws_broadcast_fn:
        await _ws_broadcast_fn(payload)


# --------------------------------------------------------------------------- #
#  Low-level BLE read                                                           #
# --------------------------------------------------------------------------- #


async def read_sensor_ble(address: str) -> SensorData:
    async with BleakClient(address, timeout=15.0) as client:
        data = await client.read_gatt_char(CHAR_UUID)

    temp = int.from_bytes(data[0:2], byteorder="little", signed=True) / 100
    humidity = data[2]
    voltage = int.from_bytes(data[3:5], byteorder="little") / 1000
    battery_pct = max(0, min(100, int((voltage - 2.1) / (3.1 - 2.1) * 100)))

    return SensorData(temperature=temp, humidity=humidity, battery=battery_pct)


def _simulate_reading() -> SensorData:
    return SensorData(
        temperature=round(random.uniform(20.0, 30.0), 1),
        humidity=round(random.uniform(40.0, 80.0), 1),
        battery=random.randint(60, 100),
    )


# --------------------------------------------------------------------------- #
#  BLE discovery (used by the API to list nearby devices)                      #
# --------------------------------------------------------------------------- #


async def discover_devices(timeout: float = 30.0) -> list[dict]:
    devices = await BleakScanner.discover(timeout=timeout, return_adv=True)
    result = []
    for device, adv in devices.values():
        result.append(
            {
                "name": device.name or "Unknown",
                "address": device.address,
                "rssi": adv.rssi,
            }
        )
    return sorted(result, key=lambda d: d["rssi"] or -999, reverse=True)


# --------------------------------------------------------------------------- #
#  Background scanner loop                                                      #
# --------------------------------------------------------------------------- #


class BLEScanner:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="ble-scanner")
        logger.info(
            "BLE scanner started (interval=%ds, simulate=%s)",
            settings.scan_interval_seconds,
            settings.simulate_sensors,
        )

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._scan_all_sensors()
            except Exception as exc:
                logger.error("Scanner loop error: %s", exc)
            await asyncio.sleep(settings.scan_interval_seconds)

    async def _scan_all_sensors(self) -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Sensor).where(Sensor.is_active))
            sensors = result.scalars().all()

        logger.info("Scanning %d active sensor(s)...", len(sensors))
        for sensor in sensors:
            await self._read_and_store(sensor)

    async def _read_and_store(self, sensor: Sensor) -> None:
        try:
            if settings.simulate_sensors:
                data = _simulate_reading()
            else:
                data = await read_sensor_ble(sensor.ble_address)
        except BleakError as exc:
            logger.warning("BLE error reading %s (%s): %s", sensor.name, sensor.ble_address, exc)
            return
        except Exception as exc:
            logger.error("Unexpected error reading %s: %s", sensor.name, exc)
            return

        async with AsyncSessionLocal() as db:
            reading = Reading(
                sensor_id=sensor.id,
                temperature=data.temperature,
                humidity=data.humidity,
                battery=data.battery,
                timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.add(reading)
            await db.commit()
            await db.refresh(reading)

            await evaluate_rules(db, reading, sensor)

        await _broadcast(
            {
                "type": "reading",
                "sensor_id": sensor.id,
                "sensor_name": sensor.name,
                "sensor_location": sensor.location,
                "temperature": data.temperature,
                "humidity": data.humidity,
                "battery": data.battery,
                "timestamp": reading.timestamp.isoformat(),
            }
        )

        logger.info(
            "Reading stored — %s: %.1f°C, %.0f%%, batt %d%%",
            sensor.name,
            data.temperature,
            data.humidity,
            data.battery,
        )


if __name__ == "__main__":
    import argparse

    async def _main() -> None:
        parser = argparse.ArgumentParser(description="Discover BLE sensors and run scanner.")
        parser.add_argument(
            "--timeout",
            type=float,
            default=30.0,
            metavar="SECS",
            help="BLE discovery timeout in seconds (default: 10)",
        )
        parser.add_argument(
            "--list-only",
            action="store_true",
            help="print discovered devices and exit without reading",
        )
        args = parser.parse_args()

        if settings.simulate_sensors:
            targets = [{"name": "Simulated Sensor", "address": "SIMULATED"}]
            print("Simulate mode — skipping BLE discovery.\n")
        else:
            print(f"Scanning for nearby BLE devices ({args.timeout:.0f}s)...")
            found = await discover_devices(timeout=args.timeout)
            if not found:
                print("No BLE devices found.")
                return

            print(f"\nFound {len(found)} device(s):\n")
            print(f"  {'NAME':<35}  {'ADDRESS':<40}  {'RSSI':>5}")
            print(f"  {'-' * 35}  {'-' * 40}  {'-' * 5}")
            for d in found:
                flag = "  ← LYWSD03MMC" if "LYWSD03MMC" in (d["name"] or "") else ""
                print(f"  {d['name']:<35}  {d['address']:<40}  {d['rssi']:>5}{flag}")

            if args.list_only:
                lywsd_count = sum(1 for d in found if "LYWSD03MMC" in (d["name"] or ""))
                print(f"\n{lywsd_count} LYWSD03MMC sensor(s) out of {len(found)} device(s) found.")
                return

            lywsd = [d for d in found if "LYWSD03MMC" in (d["name"] or "")]
            if not lywsd:
                print("\nNo LYWSD03MMC sensors found.")
                return
            targets = lywsd
            n = len(lywsd)
            interval = settings.scan_interval_seconds
            print(f"\nTargeting {n} LYWSD03MMC sensor(s). Reading every {interval}s.\n")

        while True:
            for d in targets:
                try:
                    data = (
                        _simulate_reading()
                        if settings.simulate_sensors
                        else await read_sensor_ble(d["address"])
                    )
                    print(
                        f"[{d['name']}]  temp={data.temperature}°C"
                        f"  humidity={data.humidity}%  battery={data.battery}%"
                    )
                except Exception as exc:
                    print(f"[{d['name']}] error: {exc}")
            await asyncio.sleep(settings.scan_interval_seconds)

    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\nStopped.")
