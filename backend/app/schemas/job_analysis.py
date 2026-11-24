import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.job_requirements import JobRequirements

class AnalysisStatus(BaseModel):
    status: Literal["not_started", "awaiting_review", "confirmed"]
    version: int | None = None
    draft: JobRequirements | None = None         # present while awaiting_review
    requirements: JobRequirements | None = None  # present once confirmed


class ConfirmRequest(BaseModel):
    requirements: JobRequirements


class JobRequirementsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    version: int
    data: JobRequirements
    confirmed_by: uuid.UUID
    confirmed_at: datetime