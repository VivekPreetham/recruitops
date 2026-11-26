import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class Skill(UUIDPKMixin, TimestampMixin, Base):
    """Global canonical skill. Aliases map messy resume/JD strings onto one row."""

    __tablename__ = "skills"

    canonical_name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)


class SkillAlias(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "skill_aliases"

    alias: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), index=True, nullable=False
    )
