import uuid
from datetime import UTC, datetime

from langgraph.types import Command
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.db.models import JobRequirementsRecord, User
from app.orchestration.checkpointer import get_checkpointer
from app.orchestration.graphs.job_analysis import build_job_analysis_graph
from app.schemas.job_analysis import AnalysisStatus
from app.schemas.job_requirements import JobRequirements
from app.services import jobs as job_service


def _graph():
    return build_job_analysis_graph(get_checkpointer())

def _config(job_id: uuid.UUID, version: int):
    return {"configurable": {"thread_id": f"job:{job_id}:v{version}"}}


def _latest_version(db: Session, org_id: uuid.UUID, job_id: uuid.UUID) -> int:
    latest = db.scalar(
        select(func.max(JobRequirementsRecord.version)).where(
            JobRequirementsRecord.organization_id == org_id,
            JobRequirementsRecord.job_id == job_id
        )
    )
    return latest or 0


def get_status(db: Session, user: User, job_id: uuid.UUID) -> AnalysisStatus:
    job = job_service.get_job(db, user, job_id)
    latest = _latest_version(db, user.organization_id, job.id)
    snap = _graph().get_state(_config(job.id, latest + 1))
    if snap.next:
        return AnalysisStatus(
            status="awaiting_review",
            version=latest + 1,
            draft=snap.values.get("requirements"),
        )
    if latest:
        record = db.scalar(
            select(JobRequirementsRecord).where(
                JobRequirementsRecord.organization_id == user.organization_id,
                JobRequirementsRecord.job_id == job.id,
                JobRequirementsRecord.version == latest,
            )
        )
        return AnalysisStatus(status="confirmed", version=latest, requirements=record.data)
    return AnalysisStatus(status="not_started")


def start_analysis(db: Session, user: User, job_id: uuid.UUID) -> AnalysisStatus:
    job = job_service.get_job(db, user, job_id)
    version = _latest_version(db, user.organization_id, job.id) + 1
    graph, config = _graph(), _config(job.id, version)

    if graph.get_state(config).next:
        raise ConflictError("An analysis is already awaiting review for this job")

    graph.invoke(
        {"job_id": str(job_id), "title": job.title, "description": job.description},
        config,
    )
    return get_status(db, user, job.id)


def confirm_requirements(
        db: Session, 
        user: User, 
        job_id: uuid.UUID,
        requirements: JobRequirements
    ) -> JobRequirementsRecord:
    job = job_service.get_job(db, user, job_id)
    version = _latest_version(db, user.organization_id, job.id) + 1
    graph, config = _graph(), _config(job.id, version)

    if not graph.get_state(config).next:
        raise ConflictError("No analysis is awaiting review for this job")

    graph.invoke(
        Command(
            resume={"requirements": requirements.model_dump(), "confirmed_by": str(user.id)}
        ),
        config,
    )
    confirmed = graph.get_state(config).values["confirmed"]

    record = JobRequirementsRecord(
        organization_id=user.organization_id,
        job_id=job.id,
        version=version,
        data=confirmed,
        confirmed_by=user.id,
        confirmed_at=datetime.now(UTC),
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("These requirements were already confirmed") from None
    return record
