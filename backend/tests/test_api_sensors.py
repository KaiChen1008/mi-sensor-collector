"""Integration tests for the /api/sensors endpoints."""

import pytest


@pytest.mark.asyncio
class TestSensorsCRUD:
    async def test_list_empty(self, client):
        resp = await client.get("/api/sensors")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_sensor(self, client):
        payload = {"name": "Bedroom", "ble_address": "AA:BB:CC:DD:EE:01", "location": "Bedroom"}
        resp = await client.post("/api/sensors", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Bedroom"
        assert data["ble_address"] == "AA:BB:CC:DD:EE:01"
        assert data["is_active"] is True
        assert "id" in data

    async def test_list_after_create(self, client):
        await client.post("/api/sensors", json={"name": "S1", "ble_address": "AA:00"})
        await client.post("/api/sensors", json={"name": "S2", "ble_address": "AA:01"})
        resp = await client.get("/api/sensors")
        assert len(resp.json()) == 2

    async def test_duplicate_address_rejected(self, client):
        payload = {"name": "S1", "ble_address": "AA:BB:CC:DD:EE:FF"}
        await client.post("/api/sensors", json=payload)
        resp = await client.post("/api/sensors", json=payload)
        assert resp.status_code in (400, 409, 500)

    async def test_get_sensor(self, client):
        created = (
            await client.post("/api/sensors", json={"name": "S1", "ble_address": "XX:01"})
        ).json()
        resp = await client.get(f"/api/sensors/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "S1"

    async def test_get_nonexistent(self, client):
        resp = await client.get("/api/sensors/999")
        assert resp.status_code == 404

    async def test_patch_sensor(self, client):
        created = (
            await client.post("/api/sensors", json={"name": "Old", "ble_address": "YY:01"})
        ).json()
        resp = await client.patch(
            f"/api/sensors/{created['id']}", json={"name": "New", "location": "Hall"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"
        assert resp.json()["location"] == "Hall"

    async def test_patch_active_flag(self, client):
        created = (
            await client.post("/api/sensors", json={"name": "S", "ble_address": "ZZ:01"})
        ).json()
        resp = await client.patch(f"/api/sensors/{created['id']}", json={"is_active": False})
        assert resp.json()["is_active"] is False

    async def test_delete_sensor(self, client):
        created = (
            await client.post("/api/sensors", json={"name": "Del", "ble_address": "DD:01"})
        ).json()
        resp = await client.delete(f"/api/sensors/{created['id']}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/sensors/{created['id']}")
        assert resp.status_code == 404

    async def test_delete_nonexistent(self, client):
        resp = await client.delete("/api/sensors/999")
        assert resp.status_code == 404

    async def test_scan_returns_list_in_simulate_mode(self, client):
        resp = await client.get("/api/sensors/scan")
        assert resp.status_code == 200
        devices = resp.json()
        assert isinstance(devices, list)
        assert len(devices) > 0
        assert "address" in devices[0]
