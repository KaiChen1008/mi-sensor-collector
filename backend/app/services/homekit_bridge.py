"""
Apple HomeKit bridge for Mi sensor readings.

Implements a HAP (HomeKit Accessory Protocol) accessory server that
exposes each registered sensor as a HomeKit TemperatureSensor +
HumiditySensor service pair. Once paired, sensors appear natively in
the Home app and Siri on iPhone, iPad, and Mac.

Usage
-----
Run as a standalone process alongside the main FastAPI server:

    python -m app.services.homekit_bridge

Setup (first run)
-----------------
1. Start the bridge. It will print a QR code and pairing PIN to stdout.
2. Open the Home app → "+" → "Add Accessory" → "I Don't Have a Code"
   → scan the QR code, or enter the PIN manually when asked.
3. Approve the "Unsupported Accessory" warning (it's fine).

Persistence
-----------
HAP state (keys, pairing info) is stored in `data/homekit/`. Deleting
this directory forces a re-pair on next start.

Architecture note
-----------------
The bridge polls the REST API (`/api/readings/latest`) every
POLL_INTERVAL_SECONDS rather than connecting to the database directly.
This keeps it decoupled from the SQLAlchemy session and means it works
even if the main server and bridge run on different machines.
"""

import asyncio
import logging
import os
import signal

import httpx
from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
HAP_STATE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "homekit")
HAP_STATE_FILE = os.path.join(HAP_STATE_DIR, "state.json")
HAP_PORT = int(os.environ.get("HOMEKIT_PORT", "51826"))


class MiTemperatureHumiditySensor(Accessory):
    """
    A single HomeKit accessory combining a TemperatureSensor service and a
    HumiditySensor service — matching what the physical LYWSD03MMC exposes.
    """

    category = 10  # HAP category: Sensor

    def __init__(self, driver, sensor_id: int, sensor_name: str, sensor_location: str):
        super().__init__(driver, sensor_name)
        self.sensor_id = sensor_id

        # TemperatureSensor service
        temp_service = self.driver.loader.get_service("TemperatureSensor")
        self.temp_char = temp_service.get_characteristic("CurrentTemperature")
        self.add_service(temp_service)

        # HumiditySensor service
        hum_service = self.driver.loader.get_service("HumiditySensor")
        self.hum_char = hum_service.get_characteristic("CurrentRelativeHumidity")
        self.add_service(hum_service)

        # BatteryService (shows battery level in Home app)
        batt_service = self.driver.loader.get_service("BatteryService")
        self.batt_level_char = batt_service.get_characteristic("BatteryLevel")
        self.batt_status_char = batt_service.get_characteristic("StatusLowBattery")
        self.add_service(batt_service)

        info = self.get_service("AccessoryInformation")
        info.get_characteristic("Manufacturer").set_value("Xiaomi")
        info.get_characteristic("Model").set_value("LYWSD03MMC")
        if sensor_location:
            info.get_characteristic("SerialNumber").set_value(sensor_location)

    def update(self, temperature: float, humidity: float, battery: int) -> None:
        self.temp_char.set_value(round(temperature, 1))
        self.hum_char.set_value(round(humidity, 1))
        self.batt_level_char.set_value(battery)
        self.batt_status_char.set_value(1 if battery < 20 else 0)


# --------------------------------------------------------------------------- #
#  Polling loop                                                                 #
# --------------------------------------------------------------------------- #


async def _poll_loop(accessories: dict[int, MiTemperatureHumiditySensor]) -> None:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as http:
        while True:
            try:
                resp = await http.get("/api/readings/latest")
                resp.raise_for_status()
                for entry in resp.json():
                    acc = accessories.get(entry["sensor_id"])
                    if acc and entry["temperature"] is not None:
                        acc.update(
                            temperature=entry["temperature"],
                            humidity=entry["humidity"],
                            battery=entry.get("battery") or 100,
                        )
                        logger.debug(
                            "HomeKit updated sensor %d: %.1f°C %.0f%%",
                            entry["sensor_id"],
                            entry["temperature"],
                            entry["humidity"],
                        )
            except Exception as exc:
                logger.warning("HomeKit poll failed: %s", exc)

            await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _fetch_sensors() -> list[dict]:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=10) as http:
        resp = await http.get("/api/sensors")
        resp.raise_for_status()
        return [s for s in resp.json() if s["is_active"]]


# --------------------------------------------------------------------------- #
#  Entry point                                                                  #
# --------------------------------------------------------------------------- #


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    os.makedirs(HAP_STATE_DIR, exist_ok=True)

    # Fetch registered sensors synchronously before starting the driver
    sensors = asyncio.run(_fetch_sensors())
    if not sensors:
        logger.warning(
            "No active sensors found in the API. Add sensors first, then restart the bridge."
        )

    driver = AccessoryDriver(port=HAP_PORT, persist_file=HAP_STATE_FILE)

    bridge = Bridge(driver, "Mi Sensor Bridge")

    accessories: dict[int, MiTemperatureHumiditySensor] = {}
    for s in sensors:
        acc = MiTemperatureHumiditySensor(
            driver,
            sensor_id=s["id"],
            sensor_name=s["name"],
            sensor_location=s.get("location", ""),
        )
        bridge.add_accessory(acc)
        accessories[s["id"]] = acc
        logger.info("HomeKit: registered sensor '%s' (id=%d)", s["name"], s["id"])

    driver.add_job(asyncio.ensure_future, _poll_loop(accessories))

    driver.set_accessory(bridge)

    signal.signal(signal.SIGTERM, driver.signal_handler)

    logger.info(
        "HomeKit bridge starting on port %d — pair via Home app or use the QR code above.",
        HAP_PORT,
    )
    driver.start()


if __name__ == "__main__":
    run()
