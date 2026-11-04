"""create ai report versions

Revision ID: 20261104_0005
Revises: 20261104_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261104_0005"
down_revision: str | None = "20261104_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_report_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lab_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=21), nullable=False),
        sa.Column("style", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column("model_name", sa.String(length=200), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("suggested_text", sa.Text(), nullable=False),
        sa.Column("ambiguities", sa.JSON(), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_report_versions_lab_id", "ai_report_versions", ["lab_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_report_versions_lab_id", table_name="ai_report_versions")
    op.drop_table("ai_report_versions")
