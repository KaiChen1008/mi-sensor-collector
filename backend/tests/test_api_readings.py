"""Integration tests for the /api/readings endpoints."""

import pytest
from datetime import datetime, timezone


async def _create_sensor(client, addr="AA:BB:01"):
    resp = await client.post("/api/sensors", json={"name": "Test", "ble_address": addr})
    return resp.json()


async def _add_reading(db_session, sensor_id, temperature=22.0, humidity=55.0, battery=90):
    from app.models.reading import Reading
    r = Reading(
        sensor_id=sensor_id,
        temperature=temperature,
        humidity=humidity,
        battery=battery,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)
    return r


@pytest.mark.asyncio
class TestReadingsAPI:
    async def test_list_empty(self, client):
        resp = await client.get("/api/readings")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_latest_empty(self, client):
        resp = await client.get("/api/readings/latest")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_readings_for_sensor(self, client, db_session):
        sensor = await _create_sensor(client)
        await _add_reading(db_session, sensor["id"], temperature=24.0)
        await _add_reading(db_session, sensor["id"], temperature=25.0)

        resp = await client.get("/api/readings", params={"sensor_id": sensor["id"]})
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_limit_param(self, client, db_session):
        sensor = await _create_sensor(client, addr="AA:BB:02")
        for t in range(10):
            await _add_reading(db_session, sensor["id"], temperature=float(t))

        resp = await client.get("/api/readings", params={"sensor_id": sensor["id"], "limit": 3})
        assert len(resp.json()) == 3

    async def test_latest_returns_one_per_sensor(self, client, db_session):
        s1 = await _create_sensor(client, addr="AA:BB:03")
        s2 = await _create_sensor(client, addr="AA:BB:04")
        await _add_reading(db_session, s1["id"], temperature=21.0)
        await _add_reading(db_session, s1["id"], temperature=22.0)
        await _add_reading(db_session, s2["id"], temperature=30.0)

        resp = await client.get("/api/readings/latest")
        assert resp.status_code == 200
        results = {r["sensor_id"]: r for r in resp.json()}
        assert results[s1["id"]]["temperature"] == 22.0  # latest
        assert results[s2["id"]]["temperature"] == 30.0

    async def test_latest_no_readings_shows_none(self, client, db_session):
        await _create_sensor(client, addr="AA:BB:05")
        resp = await client.get("/api/readings/latest")
        assert resp.status_code == 200
        entry = resp.json()[0]
        assert entry["temperature"] is None
        assert entry["humidity"] is None

    async def test_filter_by_sensor_id(self, client, db_session):
        s1 = await _create_sensor(client, addr="AA:BB:06")
        s2 = await _create_sensor(client, addr="AA:BB:07")
        await _add_reading(db_session, s1["id"])
        await _add_reading(db_session, s2["id"])

        resp = await client.get("/api/readings", params={"sensor_id": s1["id"]})
        assert all(r["sensor_id"] == s1["id"] for r in resp.json())
