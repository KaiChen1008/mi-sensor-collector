from datetime import datetime
from pydantic import BaseModel


class SensorBase(BaseModel):
    name: str
    ble_address: str
    location: str = ""


class SensorCreate(SensorBase):
    pass


class SensorUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    is_active: bool | None = None


class SensorOut(SensorBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DiscoveredDevice(BaseModel):
    name: str | None
    address: str
    rssi: int | None = None
