import uuid

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.models import Job, JobStatus, User
from app.db.repositories import jobs as repo
from app.schemas.jobs import JobCreate, JobUpdate


def create_job(db: Session, user: User, data: JobCreate) -> Job:
    job = Job(
        organization_id=user.organization_id,
        created_by=user.id,
        title=data.title,
        description=data.description,
    )
    db.add(job)
    db.commit()
    return job

def get_job(db: Session, user: User, job_id: uuid.UUID) -> Job:
    job = repo.get_by_id(db, user.organization_id, job_id)
    if job is None:
        raise NotFoundError("Job not found")
    return job

def list_jobs(
    db: Session,
    user: User,
    *,
    status: JobStatus | None,
    page: int,
    size: int
) -> tuple[list[Job], int]:
    return repo.list_page(db, user.organization_id, status=status, page=page, size=size)

def update_job(db: Session, user: User, job_id: uuid.UUID, data: JobUpdate) -> Job:
    job = get_job(db, user, job_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    db.commit()
    return job