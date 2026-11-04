"""create smart evidence analyses

Revision ID: 20261104_0004
Revises: 20261104_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261104_0004"
down_revision: str | None = "20261104_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "smart_evidence_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evidence_id", sa.Integer(), nullable=False),
        sa.Column("image_sha256", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("instruction_version", sa.String(length=40), nullable=False),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("detected_tool", sa.String(length=200), nullable=True),
        sa.Column("visible_observations", sa.JSON(), nullable=False),
        sa.Column("objective_explanation", sa.Text(), nullable=False),
        sa.Column("suggested_step", sa.String(length=200), nullable=True),
        sa.Column("suggested_caption", sa.Text(), nullable=False),
        sa.Column("possible_sensitive_data", sa.JSON(), nullable=False),
        sa.Column("uncertainties", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidences.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_id"),
    )
    op.create_index(
        "ix_smart_evidence_analyses_evidence_id",
        "smart_evidence_analyses",
        ["evidence_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_smart_evidence_analyses_evidence_id", table_name="smart_evidence_analyses")
    op.drop_table("smart_evidence_analyses")
