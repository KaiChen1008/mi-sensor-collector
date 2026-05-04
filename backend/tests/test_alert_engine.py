"""Unit tests for the alert rule evaluation engine."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.alert_rule import AlertLog, AlertRule
from app.models.reading import Reading
from app.models.sensor import Sensor
from app.services.alert_engine import OPERATORS, _metric_value, evaluate_rules


def make_sensor(id=1, name="Room"):
    s = Sensor()
    s.id = id
    s.name = name
    s.location = "Bedroom"
    s.is_active = True
    return s


def make_reading(sensor_id=1, temperature=25.0, humidity=65.0, battery=80):
    r = Reading()
    r.id = 1
    r.sensor_id = sensor_id
    r.temperature = temperature
    r.humidity = humidity
    r.battery = battery
    r.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
    return r


def make_rule(
    metric="humidity",
    operator=">",
    threshold=60.0,
    channel="email",
    target="test@example.com",
    cooldown=30,
    sensor_id=None,
    last_triggered_at=None,
):
    rule = AlertRule()
    rule.id = 1
    rule.name = "Test Rule"
    rule.sensor_id = sensor_id
    rule.metric = metric
    rule.operator = operator
    rule.threshold = threshold
    rule.channel = channel
    rule.channel_target = target
    rule.cooldown_minutes = cooldown
    rule.last_triggered_at = last_triggered_at
    rule.is_active = True
    return rule


class TestMetricValue:
    def test_temperature(self):
        r = make_reading(temperature=22.5)
        assert _metric_value(r, "temperature") == 22.5

    def test_humidity(self):
        r = make_reading(humidity=70.0)
        assert _metric_value(r, "humidity") == 70.0

    def test_battery(self):
        r = make_reading(battery=45)
        assert _metric_value(r, "battery") == 45

    def test_unknown_metric(self):
        assert _metric_value(make_reading(), "pressure") is None


class TestOperators:
    @pytest.mark.parametrize(
        "op,a,b,expected",
        [
            (">", 61, 60, True),
            (">", 60, 60, False),
            ("<", 59, 60, True),
            (">=", 60, 60, True),
            ("<=", 60, 60, True),
            ("==", 60, 60, True),
            ("!=", 59, 60, True),
            ("!=", 60, 60, False),
        ],
    )
    def test_comparison(self, op, a, b, expected):
        fn = OPERATORS[op]
        assert fn(a, b) == expected


class TestEvaluateRules:
    async def _run_evaluate(self, rules, reading, sensor):
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = rules
        db.execute = AsyncMock(return_value=result_mock)
        db.add = MagicMock()
        db.commit = AsyncMock()

        with patch("app.services.alert_engine.NOTIFIERS", {"email": AsyncMock(send=AsyncMock())}):
            await evaluate_rules(db, reading, sensor)

        return db

    @pytest.mark.asyncio
    async def test_triggers_when_condition_met(self):
        rule = make_rule(metric="humidity", operator=">", threshold=60.0)
        reading = make_reading(humidity=65.0)
        sensor = make_sensor()

        db = await self._run_evaluate([rule], reading, sensor)
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_does_not_trigger_when_condition_not_met(self):
        rule = make_rule(metric="humidity", operator=">", threshold=60.0)
        reading = make_reading(humidity=55.0)
        sensor = make_sensor()

        db = await self._run_evaluate([rule], reading, sensor)
        # commit is only called if alert fires
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_respects_cooldown(self):
        recent = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
        rule = make_rule(
            metric="humidity", operator=">", threshold=60.0, cooldown=30, last_triggered_at=recent
        )
        reading = make_reading(humidity=80.0)
        sensor = make_sensor()

        db = await self._run_evaluate([rule], reading, sensor)
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_fires_after_cooldown_expires(self):
        old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=60)
        rule = make_rule(
            metric="humidity", operator=">", threshold=60.0, cooldown=30, last_triggered_at=old
        )
        reading = make_reading(humidity=80.0)
        sensor = make_sensor()

        db = await self._run_evaluate([rule], reading, sensor)
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_temperature_rule(self):
        rule = make_rule(metric="temperature", operator=">=", threshold=30.0)
        reading = make_reading(temperature=30.0)
        sensor = make_sensor()

        db = await self._run_evaluate([rule], reading, sensor)
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_battery_low_rule(self):
        rule = make_rule(metric="battery", operator="<", threshold=20)
        reading = make_reading(battery=15)
        sensor = make_sensor()

        db = await self._run_evaluate([rule], reading, sensor)
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_notification_failure_still_logs(self):
        rule = make_rule()
        reading = make_reading(humidity=80.0)
        sensor = make_sensor()

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [rule]
        db.execute = AsyncMock(return_value=result_mock)
        db.add = MagicMock()
        db.commit = AsyncMock()

        broken_notifier = AsyncMock()
        broken_notifier.send = AsyncMock(side_effect=RuntimeError("SMTP down"))

        with patch("app.services.alert_engine.NOTIFIERS", {"email": broken_notifier}):
            await evaluate_rules(db, reading, sensor)

        # Log row should still be added even on send failure
        db.add.assert_called_once()
        logged: AlertLog = db.add.call_args[0][0]
        assert logged.notification_sent is False
        assert "SMTP down" in logged.error_message
