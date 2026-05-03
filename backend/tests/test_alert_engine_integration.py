"""Integration tests for alert engine rule scoping and AlertLog creation.

Unit tests in test_alert_engine.py mock the DB, so they cannot verify the SQL
WHERE clause that scopes rules to sensors.  These tests use a real in-memory
SQLite DB to cover that gap.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.models.alert_rule import AlertLog, AlertRule
from app.models.reading import Reading
from app.models.sensor import Sensor
from app.services.alert_engine import evaluate_rules


# ── helpers ──────────────────────────────────────────────────────────────────

async def _sensor(db, name="Room", addr="AA:01"):
    s = Sensor(name=name, ble_address=addr)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _reading(db, sensor_id, humidity=65.0, temperature=25.0):
    r = Reading(
        sensor_id=sensor_id,
        temperature=temperature,
        humidity=humidity,
        battery=80,
        timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


async def _rule(db, sensor_id=None, threshold=60.0, is_active=True):
    rule = AlertRule(
        name="Test Rule",
        sensor_id=sensor_id,
        metric="humidity",
        operator=">",
        threshold=threshold,
        channel="email",
        channel_target="a@b.com",
        cooldown_minutes=0,
        is_active=is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def _run(db, sensor, reading, notifier=None):
    if notifier is None:
        notifier = AsyncMock()
        notifier.send = AsyncMock()
    with patch("app.services.alert_engine.NOTIFIERS", {"email": notifier}):
        await evaluate_rules(db, reading, sensor)
    return notifier


# ── tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestRuleScoping:
    async def test_global_rule_fires_for_any_sensor(self, db_session):
        sensor = await _sensor(db_session, addr="S1:01")
        await _rule(db_session, sensor_id=None)
        reading = await _reading(db_session, sensor.id, humidity=70.0)

        notifier = await _run(db_session, sensor, reading)
        notifier.send.assert_called_once()

    async def test_sensor_scoped_rule_fires_for_matching_sensor(self, db_session):
        sensor = await _sensor(db_session, addr="S1:02")
        await _rule(db_session, sensor_id=sensor.id)
        reading = await _reading(db_session, sensor.id, humidity=70.0)

        notifier = await _run(db_session, sensor, reading)
        notifier.send.assert_called_once()

    async def test_sensor_scoped_rule_skipped_for_different_sensor(self, db_session):
        s1 = await _sensor(db_session, name="S1", addr="S1:03")
        s2 = await _sensor(db_session, name="S2", addr="S1:04")
        await _rule(db_session, sensor_id=s1.id)   # scoped to s1
        reading = await _reading(db_session, s2.id, humidity=70.0)  # from s2

        notifier = await _run(db_session, s2, reading)
        notifier.send.assert_not_called()

    async def test_inactive_rule_not_evaluated(self, db_session):
        sensor = await _sensor(db_session, addr="S1:05")
        await _rule(db_session, sensor_id=None, is_active=False)
        reading = await _reading(db_session, sensor.id, humidity=80.0)

        notifier = await _run(db_session, sensor, reading)
        notifier.send.assert_not_called()

    async def test_only_matching_scoped_rule_fires_among_multiple(self, db_session):
        s1 = await _sensor(db_session, name="S1", addr="S1:06")
        s2 = await _sensor(db_session, name="S2", addr="S1:07")
        await _rule(db_session, sensor_id=s1.id)   # should fire
        await _rule(db_session, sensor_id=s2.id)   # should not fire
        reading = await _reading(db_session, s1.id, humidity=70.0)

        notifier = await _run(db_session, s1, reading)
        notifier.send.assert_called_once()


@pytest.mark.asyncio
class TestAlertLogContent:
    async def test_log_records_correct_ids_and_value(self, db_session):
        sensor = await _sensor(db_session, addr="S2:01")
        rule = await _rule(db_session, sensor_id=None)
        reading = await _reading(db_session, sensor.id, humidity=70.0)

        await _run(db_session, sensor, reading)

        result = await db_session.execute(select(AlertLog))
        logs = result.scalars().all()
        assert len(logs) == 1
        log = logs[0]
        assert log.sensor_id == sensor.id
        assert log.rule_id == rule.id
        assert log.reading_id == reading.id
        assert log.metric_value == pytest.approx(70.0)
        assert log.notification_sent is True
        assert log.error_message is None

    async def test_failed_send_writes_log_with_error(self, db_session):
        sensor = await _sensor(db_session, addr="S2:02")
        await _rule(db_session, sensor_id=None)
        reading = await _reading(db_session, sensor.id, humidity=70.0)

        broken = AsyncMock()
        broken.send = AsyncMock(side_effect=RuntimeError("timeout"))
        await _run(db_session, sensor, reading, notifier=broken)

        result = await db_session.execute(select(AlertLog))
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].notification_sent is False
        assert "timeout" in logs[0].error_message

    async def test_each_triggering_sensor_creates_separate_log(self, db_session):
        s1 = await _sensor(db_session, name="S1", addr="S2:03")
        s2 = await _sensor(db_session, name="S2", addr="S2:04")
        await _rule(db_session, sensor_id=None)  # global
        r1 = await _reading(db_session, s1.id, humidity=70.0)
        r2 = await _reading(db_session, s2.id, humidity=70.0)

        notifier = AsyncMock()
        notifier.send = AsyncMock()
        await _run(db_session, s1, r1, notifier=notifier)
        await _run(db_session, s2, r2, notifier=notifier)

        result = await db_session.execute(select(AlertLog))
        logs = result.scalars().all()
        assert len(logs) == 2
        sensor_ids = {log.sensor_id for log in logs}
        assert sensor_ids == {s1.id, s2.id}


@pytest.mark.asyncio
class TestAlertLogsAPI:
    """Verify GET /api/alert-rules/logs via the HTTP client once a rule fires."""

    async def test_logs_populated_after_rule_fires(self, client, db_session):
        sensor = await _sensor(db_session, addr="S3:01")
        rule = await _rule(db_session, sensor_id=None)
        reading = await _reading(db_session, sensor.id, humidity=70.0)

        notifier = AsyncMock()
        notifier.send = AsyncMock()
        with patch("app.services.alert_engine.NOTIFIERS", {"email": notifier}):
            await evaluate_rules(db_session, reading, sensor)

        resp = await client.get("/api/alert-rules/logs")
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 1
        assert logs[0]["rule_id"] == rule.id
        assert logs[0]["sensor_id"] == sensor.id
        assert logs[0]["notification_sent"] is True

    async def test_logs_filtered_by_rule_id(self, client, db_session):
        sensor = await _sensor(db_session, addr="S3:02")
        rule1 = await _rule(db_session, sensor_id=None)
        rule2 = await _rule(db_session, sensor_id=None)
        r1 = await _reading(db_session, sensor.id, humidity=70.0)
        r2 = await _reading(db_session, sensor.id, humidity=70.0)

        notifier = AsyncMock()
        notifier.send = AsyncMock()
        with patch("app.services.alert_engine.NOTIFIERS", {"email": notifier}):
            await evaluate_rules(db_session, r1, sensor)
            await evaluate_rules(db_session, r2, sensor)

        resp = await client.get("/api/alert-rules/logs", params={"rule_id": rule1.id})
        assert resp.status_code == 200
        logs = resp.json()
        assert all(log["rule_id"] == rule1.id for log in logs)
