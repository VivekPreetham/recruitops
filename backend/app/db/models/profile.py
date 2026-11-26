import enum
import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class SkillSource(str, enum.Enum):
    resume = "resume"
    project = "project"
    cert = "cert"


class CandidateProfile(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "candidate_profiles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    parsed: Mapped[dict] = mapped_column(JSONB, nullable=False)
    redacted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_years: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    parser_version: Mapped[str] = mapped_column(String(40), nullable=False)


class CandidateSkill(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (
        UniqueConstraint("profile_id", "skill_id", name="uq_candidate_skills_profile_skill"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id"), index=True, nullable=False
    )
    years: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    source: Mapped[SkillSource] = mapped_column(
        Enum(SkillSource, name="skill_source"), nullable=False
    )
