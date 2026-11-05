"""archive obsolete ai report assistant storage without data loss

Revision ID: 20261104_0006
Revises: 20261104_0005
"""
from collections.abc import Sequence
from alembic import op

revision: str = "20261104_0006"
down_revision: str | None = "20261104_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("ai_report_versions", "legacy_ai_report_versions")


def downgrade() -> None:
    op.rename_table("legacy_ai_report_versions", "ai_report_versions")
