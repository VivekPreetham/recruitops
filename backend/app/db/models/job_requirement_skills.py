import enum
import uuid

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class RequirementSkillLevel(str, enum.Enum):
    required = "required"
    preferred = "preferred"


class JobRequirementSkill(UUIDPKMixin, TimestampMixin, Base):
    """Links a confirmed JD version to the same skill catalog resumes use."""

    __tablename__ = "job_requirement_skills"
    __table_args__ = (
        UniqueConstraint(
            "job_requirements_id",
            "skill_id",
            name="uq_job_requirement_skills_req_skill",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    job_requirements_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_requirements.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), index=True, nullable=False
    )
    level: Mapped[RequirementSkillLevel] = mapped_column(
        Enum(RequirementSkillLevel, name="requirement_skill_level"), nullable=False
    )
