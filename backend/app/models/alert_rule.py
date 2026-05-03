from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    # null sensor_id means the rule applies to ALL sensors
    sensor_id: Mapped[int | None] = mapped_column(
        ForeignKey("sensors.id"), nullable=True, index=True
    )
    metric: Mapped[str] = mapped_column(String(50))      # temperature | humidity | battery
    operator: Mapped[str] = mapped_column(String(10))    # > | < | >= | <= | == | !=
    threshold: Mapped[float] = mapped_column(Float)
    channel: Mapped[str] = mapped_column(String(50))     # email | telegram | line
    channel_target: Mapped[str] = mapped_column(String(500))
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    sensor: Mapped[Optional["Sensor"]] = relationship(
        back_populates="alert_rules", foreign_keys=[sensor_id]
    )


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("alert_rules.id"), index=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id"))
    reading_id: Mapped[int] = mapped_column(ForeignKey("readings.id"))
    metric_value: Mapped[float] = mapped_column(Float)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    rule: Mapped["AlertRule"] = relationship("AlertRule")
    sensor: Mapped["Sensor"] = relationship("Sensor")
    reading: Mapped["Reading"] = relationship("Reading")
