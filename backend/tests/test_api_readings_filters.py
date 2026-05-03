"""Integration tests for the readings API datetime range filters (start / end).

The list_readings endpoint accepts optional `start` and `end` query params
that are not covered by test_api_readings.py.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.models.reading import Reading


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _sensor(client, addr):
    resp = await client.post("/api/sensors", json={"name": "T", "ble_address": addr})
    return resp.json()


async def _reading(db, sensor_id, temperature, dt):
    r = Reading(sensor_id=sensor_id, temperature=temperature, humidity=50.0, battery=80, timestamp=dt)
    db.add(r)
    await db.commit()
    return r


@pytest.mark.asyncio
class TestReadingsDatetimeFilters:
    async def test_start_excludes_earlier_readings(self, client, db_session):
        sensor = await _sensor(client, "F1:01")
        now = _now()
        await _reading(db_session, sensor["id"], 20.0, now - timedelta(hours=3))
        await _reading(db_session, sensor["id"], 25.0, now - timedelta(hours=1))

        start = (now - timedelta(hours=2)).isoformat()
        resp = await client.get("/api/readings", params={"sensor_id": sensor["id"], "start": start})
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["temperature"] == 25.0

    async def test_end_excludes_later_readings(self, client, db_session):
        sensor = await _sensor(client, "F1:02")
        now = _now()
        await _reading(db_session, sensor["id"], 20.0, now - timedelta(hours=3))
        await _reading(db_session, sensor["id"], 25.0, now - timedelta(hours=1))

        end = (now - timedelta(hours=2)).isoformat()
        resp = await client.get("/api/readings", params={"sensor_id": sensor["id"], "end": end})
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["temperature"] == 20.0

    async def test_start_and_end_range_returns_only_matching(self, client, db_session):
        sensor = await _sensor(client, "F1:03")
        now = _now()
        await _reading(db_session, sensor["id"], 10.0, now - timedelta(hours=5))
        await _reading(db_session, sensor["id"], 20.0, now - timedelta(hours=3))
        await _reading(db_session, sensor["id"], 30.0, now - timedelta(hours=1))

        params = {
            "sensor_id": sensor["id"],
            "start": (now - timedelta(hours=4)).isoformat(),
            "end": (now - timedelta(hours=2)).isoformat(),
        }
        resp = await client.get("/api/readings", params=params)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["temperature"] == 20.0

    async def test_start_boundary_is_inclusive(self, client, db_session):
        sensor = await _sensor(client, "F1:04")
        boundary = _now() - timedelta(hours=2)
        await _reading(db_session, sensor["id"], 20.0, boundary)

        resp = await client.get(
            "/api/readings",
            params={"sensor_id": sensor["id"], "start": boundary.isoformat()},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_end_boundary_is_inclusive(self, client, db_session):
        sensor = await _sensor(client, "F1:05")
        boundary = _now() - timedelta(hours=2)
        await _reading(db_session, sensor["id"], 20.0, boundary)

        resp = await client.get(
            "/api/readings",
            params={"sensor_id": sensor["id"], "end": boundary.isoformat()},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_no_filters_returns_all(self, client, db_session):
        sensor = await _sensor(client, "F1:06")
        now = _now()
        for i in range(3):
            await _reading(db_session, sensor["id"], float(i), now - timedelta(hours=i))

        resp = await client.get("/api/readings", params={"sensor_id": sensor["id"]})
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    async def test_start_after_all_readings_returns_empty(self, client, db_session):
        sensor = await _sensor(client, "F1:07")
        now = _now()
        await _reading(db_session, sensor["id"], 20.0, now - timedelta(hours=5))

        resp = await client.get(
            "/api/readings",
            params={"sensor_id": sensor["id"], "start": (now - timedelta(hours=1)).isoformat()},
        )
        assert resp.status_code == 200
        assert resp.json() == []
