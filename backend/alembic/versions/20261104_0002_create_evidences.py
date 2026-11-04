"""Create evidences table.

Revision ID: 20261104_0002
Revises: 20261104_0001
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261104_0002"
down_revision: str | None = "20261104_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evidences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=80), nullable=False),
        sa.Column("mime_type", sa.String(length=80), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("step_label", sa.String(length=200), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("lab_id", "sha256", name="uq_evidences_lab_sha256"),
        sa.UniqueConstraint("stored_filename", name="uq_evidences_stored_filename"),
    )
    op.create_index("ix_evidences_lab_id", "evidences", ["lab_id"])


def downgrade() -> None:
    op.drop_index("ix_evidences_lab_id", table_name="evidences")
    op.drop_table("evidences")
