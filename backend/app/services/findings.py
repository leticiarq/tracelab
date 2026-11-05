from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.evidence import Evidence
from app.models.finding import CVSSAssessment, Finding
from app.models.lab import Lab
from app.schemas.finding import CVSSAssessmentInput, FindingCreate, FindingReorder, FindingUpdate
from app.services.errors import InvalidRelationError, NotFoundError
from app.services.slug import slugify


def _lab_or_404(db: Session, lab_id: int) -> Lab:
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise NotFoundError("Lab not found")
    return lab


def _slug(db: Session, lab_id: int, title: str, exclude_id: int | None = None) -> str:
    base = slugify(title, fallback="finding")
    candidate = base
    suffix = 2
    while True:
        query = select(Finding.id).where(Finding.lab_id == lab_id, Finding.slug == candidate)
        if exclude_id is not None:
            query = query.where(Finding.id != exclude_id)
        if db.scalar(query) is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


def list_findings(db: Session, lab_id: int) -> list[Finding]:
    _lab_or_404(db, lab_id)
    return list(
        db.scalars(
            select(Finding)
            .options(selectinload(Finding.cvss_assessment))
            .where(Finding.lab_id == lab_id)
            .order_by(Finding.display_order, Finding.id)
        )
    )


def get_finding(db: Session, lab_id: int, finding_id: int) -> Finding:
    finding = db.scalar(
        select(Finding)
        .options(selectinload(Finding.cvss_assessment), selectinload(Finding.evidences))
        .where(Finding.id == finding_id, Finding.lab_id == lab_id)
    )
    if finding is None:
        raise NotFoundError("Finding not found")
    finding.evidences.sort(key=lambda item: (item.display_order, item.id))
    return finding


def create_finding(db: Session, lab_id: int, data: FindingCreate) -> Finding:
    _lab_or_404(db, lab_id)
    order = db.scalar(
        select(func.coalesce(func.max(Finding.display_order), -1)).where(Finding.lab_id == lab_id)
    )
    finding = Finding(
        **data.model_dump(),
        lab_id=lab_id,
        slug=_slug(db, lab_id, data.title),
        display_order=int(order) + 1,
    )
    db.add(finding)
    db.commit()
    return get_finding(db, lab_id, finding.id)


def update_finding(db: Session, lab_id: int, finding_id: int, data: FindingUpdate) -> Finding:
    finding = get_finding(db, lab_id, finding_id)
    changes = data.model_dump(exclude_unset=True)
    if "title" in changes:
        finding.slug = _slug(db, lab_id, changes["title"], exclude_id=finding.id)
    for field, value in changes.items():
        if isinstance(value, str):
            value = value.strip()
        if field in {"category", "cwe_id"} and not value:
            value = None
        setattr(finding, field, value)
    finding.updated_at = datetime.now(timezone.utc)
    db.commit()
    return get_finding(db, lab_id, finding_id)


def delete_finding(db: Session, lab_id: int, finding_id: int) -> None:
    finding = get_finding(db, lab_id, finding_id)
    # Explicitly disassociate before deletion so evidence files and metadata survive on every DB.
    for evidence in finding.evidences:
        evidence.finding_id = None
    db.delete(finding)
    db.commit()
    remaining = list_findings(db, lab_id)
    for order, item in enumerate(remaining):
        item.display_order = order
    db.commit()


def reorder_findings(db: Session, lab_id: int, data: FindingReorder) -> list[Finding]:
    current = list_findings(db, lab_id)
    if set(data.finding_ids) != {item.id for item in current}:
        raise InvalidRelationError("finding_ids must contain every finding from the laboratory")
    by_id = {item.id: item for item in current}
    for order, finding_id in enumerate(data.finding_ids):
        by_id[finding_id].display_order = order
    db.commit()
    return [by_id[finding_id] for finding_id in data.finding_ids]


def list_finding_evidences(db: Session, lab_id: int, finding_id: int) -> list[Evidence]:
    get_finding(db, lab_id, finding_id)
    return list(
        db.scalars(
            select(Evidence)
            .where(Evidence.lab_id == lab_id, Evidence.finding_id == finding_id)
            .order_by(Evidence.display_order, Evidence.id)
        )
    )


def save_cvss(
    db: Session, lab_id: int, finding_id: int, data: CVSSAssessmentInput
) -> CVSSAssessment:
    finding = get_finding(db, lab_id, finding_id)
    assessment = finding.cvss_assessment
    if assessment is None:
        assessment = CVSSAssessment(finding_id=finding.id, **data.model_dump())
        db.add(assessment)
    else:
        for field, value in data.model_dump().items():
            setattr(assessment, field, value)
        assessment.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assessment)
    return assessment


def delete_cvss(db: Session, lab_id: int, finding_id: int) -> None:
    finding = get_finding(db, lab_id, finding_id)
    if finding.cvss_assessment is None:
        raise NotFoundError("CVSS assessment not found")
    db.delete(finding.cvss_assessment)
    db.commit()
