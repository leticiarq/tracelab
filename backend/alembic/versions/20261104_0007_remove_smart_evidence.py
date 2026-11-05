"""archive obsolete smart evidence storage without data loss

Revision ID: 20261104_0007
Revises: 20261104_0006
"""
from collections.abc import Sequence
from alembic import op

revision: str = "20261104_0007"
down_revision: str | None = "20261104_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("smart_evidence_analyses", "legacy_smart_evidence_analyses")


def downgrade() -> None:
    op.rename_table("legacy_smart_evidence_analyses", "smart_evidence_analyses")
