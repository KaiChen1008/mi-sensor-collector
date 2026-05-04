from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Metric = Literal["temperature", "humidity", "battery"]
Operator = Literal[">", "<", ">=", "<=", "==", "!="]
Channel = Literal["email", "telegram", "line"]


class AlertRuleBase(BaseModel):
    name: str
    sensor_id: int | None = None
    metric: Metric
    operator: Operator
    threshold: float
    channel: Channel
    channel_target: str
    cooldown_minutes: int = 30


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    sensor_id: int | None = None
    metric: Metric | None = None
    operator: Operator | None = None
    threshold: float | None = None
    channel: Channel | None = None
    channel_target: str | None = None
    cooldown_minutes: int | None = None
    is_active: bool | None = None


class AlertRuleOut(AlertRuleBase):
    id: int
    is_active: bool
    last_triggered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertLogOut(BaseModel):
    id: int
    rule_id: int
    sensor_id: int
    reading_id: int
    metric_value: float
    triggered_at: datetime
    notification_sent: bool
    error_message: str | None

    model_config = {"from_attributes": True}
