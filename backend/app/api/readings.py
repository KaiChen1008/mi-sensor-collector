from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.reading import Reading
from app.models.sensor import Sensor
from app.schemas.reading import LatestReading, ReadingOut

router = APIRouter()


@router.get("", response_model=list[ReadingOut])
async def list_readings(
    sensor_id: Optional[int] = Query(None),
    limit: int = Query(100, le=1000),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Reading).order_by(Reading.timestamp.desc()).limit(limit)
    if sensor_id:
        stmt = stmt.where(Reading.sensor_id == sensor_id)
    if start:
        stmt = stmt.where(Reading.timestamp >= start)
    if end:
        stmt = stmt.where(Reading.timestamp <= end)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/latest", response_model=list[LatestReading])
async def get_latest_readings(db: AsyncSession = Depends(get_db)):
    sensors_result = await db.execute(select(Sensor))
    sensors = sensors_result.scalars().all()

    output: list[LatestReading] = []
    for sensor in sensors:
        stmt = (
            select(Reading)
            .where(Reading.sensor_id == sensor.id)
            .order_by(Reading.timestamp.desc())
            .limit(1)
        )
        reading = (await db.execute(stmt)).scalar_one_or_none()
        output.append(
            LatestReading(
                sensor_id=sensor.id,
                sensor_name=sensor.name,
                sensor_location=sensor.location or "",
                temperature=reading.temperature if reading else None,
                humidity=reading.humidity if reading else None,
                battery=reading.battery if reading else None,
                timestamp=reading.timestamp if reading else None,
            )
        )
    return output
