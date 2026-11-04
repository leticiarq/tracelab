"""create reports and resolution steps

Revision ID: 20261104_0003
Revises: 20261104_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261104_0003"
down_revision: str | None = "20261104_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("labs", sa.Column("resolution_steps", sa.Text(), nullable=True))
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lab_id", sa.Integer(), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("evidence_manifest", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lab_id"),
    )
    op.create_index("ix_reports_lab_id", "reports", ["lab_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_reports_lab_id", table_name="reports")
    op.drop_table("reports")
    op.drop_column("labs", "resolution_steps")
