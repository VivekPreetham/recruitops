"""resume pipeline tables

Revision ID: d4f8a1b90c21
Revises: ac35c3123ca0
Create Date: 2026-11-26 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4f8a1b90c21"
down_revision: Union[str, Sequence[str], None] = "ac35c3123ca0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "candidates",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_candidates_user_id"),
    )
    op.create_index(
        op.f("ix_candidates_organization_id"), "candidates", ["organization_id"], unique=False
    )

    op.create_table(
        "skills",
        sa.Column("canonical_name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_skills_canonical_name"), "skills", ["canonical_name"], unique=True)

    op.create_table(
        "skill_aliases",
        sa.Column("alias", sa.String(length=100), nullable=False),
        sa.Column("skill_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_skill_aliases_alias"), "skill_aliases", ["alias"], unique=True)
    op.create_index(
        op.f("ix_skill_aliases_skill_id"), "skill_aliases", ["skill_id"], unique=False
    )

    op.create_table(
        "resumes",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("mime", sa.String(length=100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("uploaded", "processing", "parsed", "failed", name="resume_status"),
            nullable=False,
        ),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index(
        op.f("ix_resumes_organization_id"), "resumes", ["organization_id"], unique=False
    )
    op.create_index(op.f("ix_resumes_candidate_id"), "resumes", ["candidate_id"], unique=False)
    op.create_index(op.f("ix_resumes_sha256"), "resumes", ["sha256"], unique=False)

    op.create_table(
        "candidate_profiles",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("candidate_id", sa.UUID(), nullable=False),
        sa.Column("resume_id", sa.UUID(), nullable=False),
        sa.Column("parsed", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("redacted_text", sa.Text(), nullable=True),
        sa.Column("total_years", sa.Numeric(5, 1), nullable=True),
        sa.Column("parser_version", sa.String(length=40), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_id"),
    )
    op.create_index(
        op.f("ix_candidate_profiles_organization_id"),
        "candidate_profiles",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_profiles_candidate_id"),
        "candidate_profiles",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        "ix_candidate_profiles_parsed",
        "candidate_profiles",
        ["parsed"],
        unique=False,
        postgresql_using="gin",
    )

    op.create_table(
        "candidate_skills",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("skill_id", sa.UUID(), nullable=False),
        sa.Column("years", sa.Numeric(5, 1), nullable=True),
        sa.Column(
            "source",
            sa.Enum("resume", "project", "cert", name="skill_source"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id", "skill_id", name="uq_candidate_skills_profile_skill"),
    )
    op.create_index(
        op.f("ix_candidate_skills_organization_id"),
        "candidate_skills",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_candidate_skills_profile_id"), "candidate_skills", ["profile_id"], unique=False
    )
    op.create_index(
        "ix_candidate_skills_skill_years",
        "candidate_skills",
        ["skill_id", "years"],
        unique=False,
    )

    op.create_table(
        "job_requirement_skills",
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("job_requirements_id", sa.UUID(), nullable=False),
        sa.Column("skill_id", sa.UUID(), nullable=False),
        sa.Column(
            "level",
            sa.Enum("required", "preferred", name="requirement_skill_level"),
            nullable=False,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["job_requirements_id"], ["job_requirements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_requirements_id", "skill_id", name="uq_job_requirement_skills_req_skill"
        ),
    )
    op.create_index(
        op.f("ix_job_requirement_skills_organization_id"),
        "job_requirement_skills",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_requirement_skills_job_requirements_id"),
        "job_requirement_skills",
        ["job_requirements_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_job_requirement_skills_skill_id"),
        "job_requirement_skills",
        ["skill_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_job_requirement_skills_skill_id"), table_name="job_requirement_skills"
    )
    op.drop_index(
        op.f("ix_job_requirement_skills_job_requirements_id"),
        table_name="job_requirement_skills",
    )
    op.drop_index(
        op.f("ix_job_requirement_skills_organization_id"),
        table_name="job_requirement_skills",
    )
    op.drop_table("job_requirement_skills")

    op.drop_index("ix_candidate_skills_skill_years", table_name="candidate_skills")
    op.drop_index(op.f("ix_candidate_skills_profile_id"), table_name="candidate_skills")
    op.drop_index(op.f("ix_candidate_skills_organization_id"), table_name="candidate_skills")
    op.drop_table("candidate_skills")

    op.drop_index("ix_candidate_profiles_parsed", table_name="candidate_profiles")
    op.drop_index(op.f("ix_candidate_profiles_candidate_id"), table_name="candidate_profiles")
    op.drop_index(
        op.f("ix_candidate_profiles_organization_id"), table_name="candidate_profiles"
    )
    op.drop_table("candidate_profiles")

    op.drop_index(op.f("ix_resumes_sha256"), table_name="resumes")
    op.drop_index(op.f("ix_resumes_candidate_id"), table_name="resumes")
    op.drop_index(op.f("ix_resumes_organization_id"), table_name="resumes")
    op.drop_table("resumes")

    op.drop_index(op.f("ix_skill_aliases_skill_id"), table_name="skill_aliases")
    op.drop_index(op.f("ix_skill_aliases_alias"), table_name="skill_aliases")
    op.drop_table("skill_aliases")

    op.drop_index(op.f("ix_skills_canonical_name"), table_name="skills")
    op.drop_table("skills")

    op.drop_index(op.f("ix_candidates_organization_id"), table_name="candidates")
    op.drop_table("candidates")

    op.execute("DROP TYPE IF EXISTS requirement_skill_level")
    op.execute("DROP TYPE IF EXISTS skill_source")
    op.execute("DROP TYPE IF EXISTS resume_status")
