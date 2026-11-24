"""job_requirements

Revision ID: ac35c3123ca0
Revises: 2e5486a1c8ef
Create Date: 2026-10-13 00:22:50.493648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ac35c3123ca0'
down_revision: Union[str, Sequence[str], None] = '2e5486a1c8ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'job_requirements',
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('job_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confirmed_by', sa.UUID(), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['confirmed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id', 'version', name='uq_job_requirements_job_version'),
    )
    op.create_index(
        op.f('ix_job_requirements_job_id'), 'job_requirements', ['job_id'], unique=False
    )
    op.create_index(
        op.f('ix_job_requirements_organization_id'),
        'job_requirements',
        ['organization_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_job_requirements_organization_id'), table_name='job_requirements')
    op.drop_index(op.f('ix_job_requirements_job_id'), table_name='job_requirements')
    op.drop_table('job_requirements')
