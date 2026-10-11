import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Job, JobStatus

def get_by_id(db: Session, org_id: uuid.UUID, job_id: uuid.UUID) -> Job | None:
    return db.scalar(select(Job).where(Job.id == job_id, Job.organization_id == org_id))

def list_page(
    db: Session,
    org_id: uuid.UUID,
    *,
    status: JobStatus | None,
    page: int,
    size: int,
) -> tuple[list[Job], int]:
    base = select(Job).where(Job.organization_id == org_id)
    if status is not None:
        base = base.where(Job.status == status)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(
        base.order_by(Job.created_at.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return list(items), total