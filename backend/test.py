import asyncio

from bleak import BleakScanner

SENSOR_NAME = "LYWSD03MMC"


async def scan_sensors():
    # 掃描 10 秒，找出所有 BLE 裝置
    print("Scanning for BLE devices (10s)...")
    devices = await BleakScanner.discover(timeout=10.0)

    sensors = []
    for d in devices:
        name = d.name or ""
        print(f"  {name:<30} {d.address}")
        if SENSOR_NAME in name:
            sensors.append(d)

    print(f"\nFound {len(sensors)} sensor(s):")
    for s in sensors:
        print(f"  >> {s.name}  UUID: {s.address}")

    return sensors


asyncio.run(scan_sensors())
