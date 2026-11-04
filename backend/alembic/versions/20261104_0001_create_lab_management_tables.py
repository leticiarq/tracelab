"""Create platform, category, and lab tables.

Revision ID: 20261104_0001
Revises:
Create Date: 2026-11-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261104_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platforms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("website_url", sa.String(length=2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["platform_id"], ["platforms.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_categories_platform_id", "categories", ["platform_id"])
    op.create_table(
        "labs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("platform_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("difficulty", sa.String(length=50), nullable=True),
        sa.Column(
            "status",
            sa.Enum("todo", "in_progress", "solved", "documented", name="labstatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("vulnerability_description", sa.Text(), nullable=True),
        sa.Column("impact", sa.Text(), nullable=True),
        sa.Column("mitigation", sa.Text(), nullable=True),
        sa.Column("learnings", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["platform_id"], ["platforms.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_labs_category_id", "labs", ["category_id"])
    op.create_index("ix_labs_platform_id", "labs", ["platform_id"])
    op.create_index("ix_labs_status", "labs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_labs_status", table_name="labs")
    op.drop_index("ix_labs_platform_id", table_name="labs")
    op.drop_index("ix_labs_category_id", table_name="labs")
    op.drop_table("labs")
    op.drop_index("ix_categories_platform_id", table_name="categories")
    op.drop_table("categories")
    op.drop_table("platforms")
