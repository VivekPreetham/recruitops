import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.errors import NotFoundError
from app.db.models import JobStatus, User, UserRole
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.jobs import JobCreate, JobUpdate, JobOut
from app.services import jobs as job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])

STAFF = (UserRole.recruiter, UserRole.admin)


@router.post("", response_model=JobOut, status_code=201)
def create_job(
    body: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return job_service.create_job(db, user, body)


@router.get("", response_model=Page[JobOut])
def list_jobs(
    status: JobStatus | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == UserRole.candidate:
        status = JobStatus.open
    items, total = job_service.list_jobs(db, user, status=status, page=page, size=size)
    return Page(items=items, total=total, page=page, size=size)


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = job_service.get_job(db, user, job_id)
    if user.role == UserRole.candidate and job.status != JobStatus.open:
        raise NotFoundError("Job not found")
    return job



@router.patch("/{job_id}", response_model=JobOut)
def update_job(
    job_id: uuid.UUID,
    body: JobUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return job_service.update_job(db, user, job_id, body)