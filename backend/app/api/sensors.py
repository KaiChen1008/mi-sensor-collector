from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.sensor import Sensor
from app.schemas.sensor import DiscoveredDevice, SensorCreate, SensorOut, SensorUpdate
from app.services import ble_scanner

router = APIRouter()


@router.get("", response_model=list[SensorOut])
async def list_sensors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Sensor).order_by(Sensor.created_at))
    return result.scalars().all()


@router.post("", response_model=SensorOut, status_code=status.HTTP_201_CREATED)
async def create_sensor(body: SensorCreate, db: AsyncSession = Depends(get_db)):
    sensor = Sensor(**body.model_dump())
    db.add(sensor)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A sensor with this BLE address already exists")
    await db.refresh(sensor)
    return sensor


@router.get("/scan", response_model=list[DiscoveredDevice])
async def scan_ble_devices():
    if settings.simulate_sensors:
        return [
            DiscoveredDevice(name="LYWSD03MMC", address="AA:BB:CC:DD:EE:01", rssi=-65),
            DiscoveredDevice(name="LYWSD03MMC", address="AA:BB:CC:DD:EE:02", rssi=-72),
        ]
    try:
        devices = await ble_scanner.discover_devices(timeout=10.0)
        return devices
    except Exception as exc:
        ble_unavailable = "No such file or directory" in str(exc) or "dbus" in str(exc).lower()
        detail = (
            "BLE hardware is not accessible. Set SIMULATE_SENSORS=true to use simulated data."
            if ble_unavailable
            else f"BLE scan failed: {exc}"
        )
        raise HTTPException(status_code=503, detail=detail)


@router.get("/{sensor_id}", response_model=SensorOut)
async def get_sensor(sensor_id: int, db: AsyncSession = Depends(get_db)):
    sensor = await db.get(Sensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor


@router.patch("/{sensor_id}", response_model=SensorOut)
async def update_sensor(sensor_id: int, body: SensorUpdate, db: AsyncSession = Depends(get_db)):
    sensor = await db.get(Sensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(sensor, field, value)
    await db.commit()
    await db.refresh(sensor)
    return sensor


@router.delete("/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sensor(sensor_id: int, db: AsyncSession = Depends(get_db)):
    sensor = await db.get(Sensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    await db.delete(sensor)
    await db.commit()


@router.post("/{sensor_id}/read", response_model=dict)
async def trigger_read(sensor_id: int, db: AsyncSession = Depends(get_db)):
    """Manually trigger an immediate BLE read for the given sensor."""
    sensor = await db.get(Sensor, sensor_id)
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    if not sensor.is_active:
        raise HTTPException(status_code=400, detail="Sensor is inactive")

    scanner_instance = ble_scanner._scanner_instance
    if scanner_instance is None:
        raise HTTPException(status_code=503, detail="Scanner not running")

    import asyncio

    asyncio.create_task(scanner_instance._read_and_store(sensor))
    return {"status": "read triggered"}
