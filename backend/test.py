"""
米家溫濕度計 2 (LYWSD03MMC) — macOS BLE Reader
Usage: python mijia_reader.py
"""

import asyncio
import struct

from bleak import BleakClient, BleakScanner

# GATT characteristic for temperature + humidity + battery
TEMP_CHAR_UUID = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6"
SENSOR_NAME = "LYWSD03MMC"


def parse_data(data: bytearray) -> dict:
    temp_raw = struct.unpack_from("<H", data, 0)[0]
    humidity = data[2]
    batt_mv = struct.unpack_from("<H", data, 3)[0]
    batt_pct = min(int((batt_mv - 2100) / (3100 - 2100) * 100), 100)
    return {
        "temperature": round(temp_raw / 100.0, 2),
        "humidity": humidity,
        "battery_mv": batt_mv,
        "battery_pct": max(batt_pct, 0),
    }


async def scan_for_sensors(timeout: float = 10.0) -> list[tuple[str, str]]:
    """Scan BLE devices, return list of (name, uuid) for LYWSD03MMC sensors."""
    print(f"[scan] Scanning for {timeout}s ...")
    devices = await BleakScanner.discover(timeout=timeout)

    sensors = []
    print(f"\n{'Name':<35} {'UUID'}")
    print("-" * 75)
    for d in devices:
        name = d.name or "(unknown)"
        marker = "  <-- SENSOR" if SENSOR_NAME in name else ""
        print(f"{name:<35} {d.address}{marker}")
        if marker:
            sensors.append((name, d.address))

    return sensors


async def read_sensor(uuid: str, retries: int = 3) -> dict | None:
    """Connect to a sensor UUID and read one measurement."""
    for attempt in range(1, retries + 1):
        try:
            async with BleakClient(uuid, timeout=15.0) as client:
                data = await client.read_gatt_char(TEMP_CHAR_UUID)
                return parse_data(data)
        except Exception as e:
            print(f"  [attempt {attempt}/{retries}] {e}")
            if attempt < retries:
                await asyncio.sleep(2)
    return None


async def main():
    sensors = await scan_for_sensors()

    if not sensors:
        print("\n[!] No LYWSD03MMC sensors found.")
        print("    Make sure the sensor is nearby and Bluetooth is enabled.")
        return

    print(f"\n[found] {len(sensors)} sensor(s). Reading data ...\n")

    for name, uuid in sensors:
        print(f"  Sensor : {name}")
        print(f"  UUID   : {uuid}")
        result = await read_sensor(uuid)
        if result:
            print(f"  Temp   : {result['temperature']} °C")
            print(f"  Hum    : {result['humidity']} %")
            print(f"  Batt   : {result['battery_mv']} mV  (~{result['battery_pct']}%)")
        else:
            print("  [!] Failed to read data after retries.")
        print()


if __name__ == "__main__":
    asyncio.run(main())
