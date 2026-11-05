"""create findings, optional CVSS assessments, and evidence associations

Revision ID: 20261104_0008
Revises: 20261104_0007

Legacy vulnerability columns intentionally remain on labs. The backfill copies them into one
finding only when at least one technical field contains non-whitespace content. Existing reports
and evidence files are not changed; evidence remains general until reviewed by the user.
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20261104_0008"
down_revision: str | None = "20261104_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lab_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False),
        sa.Column("category", sa.String(120)),
        sa.Column("cwe_id", sa.String(20)),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("technical_details", sa.Text(), nullable=False),
        sa.Column("reproduction_steps", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("mitigation", sa.Text(), nullable=False),
        sa.Column("status", sa.String(13), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["lab_id"], ["labs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("lab_id", "slug", name="uq_findings_lab_slug"),
    )
    op.create_index("ix_findings_lab_id", "findings", ["lab_id"])
    op.create_index("ix_findings_status", "findings", ["status"])
    op.create_table(
        "cvss_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("finding_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(10), nullable=False),
        sa.Column("vector", sa.String(255), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("finding_id"),
    )
    op.create_index("ix_cvss_assessments_finding_id", "cvss_assessments", ["finding_id"], unique=True)
    with op.batch_alter_table("evidences") as batch_op:
        batch_op.add_column(sa.Column("finding_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_evidences_finding_id", "findings", ["finding_id"], ["id"], ondelete="SET NULL")
        batch_op.create_index("ix_evidences_finding_id", ["finding_id"])

    connection = op.get_bind()
    labs = sa.table(
        "labs",
        sa.column("id", sa.Integer), sa.column("category_id", sa.Integer),
        sa.column("vulnerability_description", sa.Text), sa.column("resolution_steps", sa.Text),
        sa.column("impact", sa.Text), sa.column("mitigation", sa.Text),
        sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime),
    )
    categories = sa.table("categories", sa.column("id", sa.Integer), sa.column("name", sa.String))
    findings = sa.table(
        "findings", sa.column("lab_id", sa.Integer), sa.column("title", sa.String),
        sa.column("slug", sa.String), sa.column("category", sa.String), sa.column("cwe_id", sa.String),
        sa.column("description", sa.Text), sa.column("technical_details", sa.Text),
        sa.column("reproduction_steps", sa.Text), sa.column("impact", sa.Text),
        sa.column("mitigation", sa.Text), sa.column("status", sa.String),
        sa.column("display_order", sa.Integer), sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    rows = connection.execute(
        sa.select(labs, categories.c.name.label("category_name")).select_from(
            labs.outerjoin(categories, labs.c.category_id == categories.c.id)
        )
    ).mappings()
    for row in rows:
        technical = [row["vulnerability_description"], row["resolution_steps"], row["impact"], row["mitigation"]]
        if not any(value and value.strip() for value in technical):
            continue
        connection.execute(findings.insert().values(
            lab_id=row["id"], title="Vulnerabilidade documentada", slug="vulnerabilidade-documentada",
            category=row["category_name"], cwe_id=None,
            description=row["vulnerability_description"] or "", technical_details="",
            reproduction_steps=row["resolution_steps"] or "", impact=row["impact"] or "",
            mitigation=row["mitigation"] or "", status="confirmed", display_order=0,
            created_at=row["created_at"], updated_at=row["updated_at"],
        ))


def downgrade() -> None:
    with op.batch_alter_table("evidences") as batch_op:
        batch_op.drop_index("ix_evidences_finding_id")
        batch_op.drop_constraint("fk_evidences_finding_id", type_="foreignkey")
        batch_op.drop_column("finding_id")
    op.drop_index("ix_cvss_assessments_finding_id", table_name="cvss_assessments")
    op.drop_table("cvss_assessments")
    op.drop_index("ix_findings_status", table_name="findings")
    op.drop_index("ix_findings_lab_id", table_name="findings")
    op.drop_table("findings")
