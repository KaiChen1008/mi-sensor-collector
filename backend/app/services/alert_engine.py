import logging
import operator as op
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_rule import AlertRule, AlertLog
from app.models.reading import Reading
from app.models.sensor import Sensor
from app.services.notifiers import NOTIFIERS

logger = logging.getLogger(__name__)

OPERATORS = {
    ">": op.gt,
    "<": op.lt,
    ">=": op.ge,
    "<=": op.le,
    "==": op.eq,
    "!=": op.ne,
}


def _metric_value(reading: Reading, metric: str) -> float | None:
    return {"temperature": reading.temperature, "humidity": reading.humidity, "battery": reading.battery}.get(metric)


async def evaluate_rules(db: AsyncSession, reading: Reading, sensor: Sensor) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    result = await db.execute(
        select(AlertRule).where(
            AlertRule.is_active == True,
            (AlertRule.sensor_id == sensor.id) | (AlertRule.sensor_id == None),
        )
    )
    rules = result.scalars().all()

    for rule in rules:
        value = _metric_value(reading, rule.metric)
        if value is None:
            continue

        compare = OPERATORS.get(rule.operator)
        if compare is None or not compare(value, rule.threshold):
            continue

        # Respect cooldown window
        if rule.last_triggered_at:
            elapsed = now - rule.last_triggered_at
            if elapsed < timedelta(minutes=rule.cooldown_minutes):
                continue

        await _fire_alert(db, rule, reading, sensor, value, now)


async def _fire_alert(
    db: AsyncSession,
    rule: AlertRule,
    reading: Reading,
    sensor: Sensor,
    value: float,
    now: datetime,
) -> None:
    metric_labels = {"temperature": "Temperature", "humidity": "Humidity", "battery": "Battery"}
    unit = {"temperature": "°C", "humidity": "%", "battery": "%"}.get(rule.metric, "")

    subject = f"[Mi Sensor Alert] {rule.name}"
    body = (
        f"Sensor: {sensor.name} ({sensor.location or 'no location'})\n"
        f"Rule: {rule.name}\n"
        f"Condition: {metric_labels.get(rule.metric, rule.metric)} {rule.operator} {rule.threshold}{unit}\n"
        f"Current value: {value}{unit}\n"
        f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )

    error_msg = None
    sent = False
    notifier = NOTIFIERS.get(rule.channel)

    try:
        if notifier:
            await notifier.send(rule.channel_target, subject, body)
            sent = True
            logger.info("Alert sent via %s for rule %d (sensor %s)", rule.channel, rule.id, sensor.name)
        else:
            raise RuntimeError(f"Unknown channel: {rule.channel}")
    except Exception as exc:
        error_msg = str(exc)
        logger.error("Failed to send alert for rule %d: %s", rule.id, exc)

    log = AlertLog(
        rule_id=rule.id,
        sensor_id=sensor.id,
        reading_id=reading.id,
        metric_value=value,
        triggered_at=now,
        notification_sent=sent,
        error_message=error_msg,
    )
    db.add(log)

    rule.last_triggered_at = now
    await db.commit()
