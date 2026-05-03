"""Integration tests for the manual read trigger endpoint.

POST /api/sensors/{id}/read is not covered by test_api_sensors.py.
In tests the scanner is always None (set in conftest), so the 503 path
is exercised naturally without any extra mocking.
"""

import pytest


@pytest.mark.asyncio
class TestManualReadTrigger:
    async def test_trigger_nonexistent_sensor_returns_404(self, client):
        resp = await client.post("/api/sensors/999/read")
        assert resp.status_code == 404

    async def test_trigger_inactive_sensor_returns_400(self, client):
        sensor = (
            await client.post("/api/sensors", json={"name": "S", "ble_address": "TR:01"})
        ).json()
        await client.patch(f"/api/sensors/{sensor['id']}", json={"is_active": False})

        resp = await client.post(f"/api/sensors/{sensor['id']}/read")
        assert resp.status_code == 400
        assert "inactive" in resp.json()["detail"].lower()

    async def test_trigger_returns_503_when_scanner_not_running(self, client):
        # conftest sets _scanner_instance = None, so this always exercises the 503 branch
        sensor = (
            await client.post("/api/sensors", json={"name": "S", "ble_address": "TR:02"})
        ).json()

        resp = await client.post(f"/api/sensors/{sensor['id']}/read")
        assert resp.status_code == 503
        assert "Scanner not running" in resp.json()["detail"]
