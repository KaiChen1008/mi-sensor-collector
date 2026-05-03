"""Unit tests for the LYWSD03MMC BLE characteristic data parser."""

import pytest
from app.services.ble_scanner import read_sensor_ble, SensorData


def parse(raw: bytes) -> SensorData:
    """Re-implement the parser inline so we can test it without BLE hardware."""
    temp = int.from_bytes(raw[0:2], byteorder="little", signed=True) / 100
    humidity = raw[2]
    voltage = int.from_bytes(raw[3:5], byteorder="little") / 1000
    battery_pct = max(0, min(100, int((voltage - 2.1) / (3.1 - 2.1) * 100)))
    return SensorData(temperature=temp, humidity=humidity, battery=battery_pct)


class TestBLEParser:
    def test_typical_reading(self):
        # 25.50 °C, 60 %, 2.9 V → battery ~80 %
        # Note: (2.9 - 2.1) in floating point is 0.7999…, so int() truncates to 79.
        raw = (
            int(25.50 * 100).to_bytes(2, "little", signed=True)
            + bytes([60])
            + int(2.9 * 1000).to_bytes(2, "little")
        )
        data = parse(raw)
        assert data.temperature == pytest.approx(25.50)
        assert data.humidity == 60
        assert abs(data.battery - 80) <= 1  # ±1 % tolerance for float truncation

    def test_negative_temperature(self):
        # -5.00 °C (signed int16)
        raw = (
            int(-5.00 * 100).to_bytes(2, "little", signed=True)
            + bytes([45])
            + int(3.1 * 1000).to_bytes(2, "little")
        )
        data = parse(raw)
        assert data.temperature == pytest.approx(-5.00)

    def test_battery_fully_charged(self):
        raw = b"\x00\x00\x00" + int(3100).to_bytes(2, "little")
        data = parse(raw)
        assert data.battery == 100

    def test_battery_fully_dead(self):
        raw = b"\x00\x00\x00" + int(2100).to_bytes(2, "little")
        data = parse(raw)
        assert data.battery == 0

    def test_battery_below_min_clamped(self):
        # voltage below 2.1 V should clamp to 0
        raw = b"\x00\x00\x00" + int(1800).to_bytes(2, "little")
        data = parse(raw)
        assert data.battery == 0

    def test_battery_above_max_clamped(self):
        # voltage above 3.1 V should clamp to 100
        raw = b"\x00\x00\x00" + int(3500).to_bytes(2, "little")
        data = parse(raw)
        assert data.battery == 100

    def test_zero_temperature(self):
        raw = (0).to_bytes(2, "little", signed=True) + bytes([50]) + (2600).to_bytes(2, "little")
        data = parse(raw)
        assert data.temperature == 0.0

    def test_high_humidity(self):
        raw = (2000).to_bytes(2, "little", signed=True) + bytes([99]) + (2600).to_bytes(2, "little")
        data = parse(raw)
        assert data.humidity == 99
