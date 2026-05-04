from datetime import datetime

from pydantic import BaseModel


class ReadingOut(BaseModel):
    id: int
    sensor_id: int
    temperature: float
    humidity: float
    battery: int | None
    timestamp: datetime

    model_config = {"from_attributes": True}


class LatestReading(BaseModel):
    sensor_id: int
    sensor_name: str
    sensor_location: str
    temperature: float | None
    humidity: float | None
    battery: int | None
    timestamp: datetime | None
