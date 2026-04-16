from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.attendance import AttendanceStatus


class AttendanceBase(BaseModel):
    user_id: int
    date: date
    status: AttendanceStatus
    notes: str | None = Field(default=None, max_length=1000)
    image_path: str | None = Field(default=None, max_length=255)


class AttendanceCreate(AttendanceBase):
    pass


class AttendanceUpdate(BaseModel):
    status: AttendanceStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)


class AttendanceOut(AttendanceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
