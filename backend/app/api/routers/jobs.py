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
from app.schemas.job_analysis import AnalysisStatus, ConfirmRequest, JobRequirementsOut
from app.services import job_analysis as analysis_service

router = APIRouter(prefix="/jobs", tags=["jobs"])

STAFF = (UserRole.recruiter, UserRole.admin)


@router.post("", response_model=JobOut, status_code=201)
def create_job(
    body: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(*STAFF)),
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


@router.post("/{job_id}/analyze", response_model=AnalysisStatus)
def run_job_analysis(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(*STAFF)),
):
    return analysis_service.start_analysis(db, user, job_id)


@router.get("/{job_id}/analysis", response_model=AnalysisStatus)
def get_job_analysis(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(*STAFF)),
):
    return analysis_service.get_status(db, user, job_id)


@router.post(
    "/{job_id}/requirements/confirm", response_model=JobRequirementsOut, status_code=201
)
def confirm_job_requirements(
    job_id: uuid.UUID,
    body: ConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(*STAFF)),
):
    return analysis_service.confirm_requirements(db, user, job_id, body.requirements)