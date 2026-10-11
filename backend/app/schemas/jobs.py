import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.jobs import JobStatus


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, min_length=10)
    status: JobStatus | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_by: uuid.UUID
    title: str
    description: str
    status: JobStatus
    created_at: datetime