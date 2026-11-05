import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.lab import Lab
from app.models.report import Report
from app.services.errors import ConflictError, NotFoundError, ServiceError
from app.services.evidences import evidence_path

IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
SENSITIVE_PATTERNS = {
    "possível chave privada": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    "possível senha": re.compile(r"\b(?:password|passwd|senha)\s*[:=]\s*\S+", re.I),
    "possível token ou segredo": re.compile(r"\b(?:api[_-]?key|token|secret)\s*[:=]\s*[A-Za-z0-9_./+\-=]{8,}", re.I),
}
ACTIVE_HTML_PATTERN = re.compile(
    r"<\s*/?\s*(?:script|iframe|object|embed|img|svg|style|link|meta|form|input|video|audio|source)\b",
    re.I,
)


class InvalidReportError(ServiceError):
    status_code = 422


class ExportTooLargeError(ServiceError):
    status_code = 413


def _lab(db: Session, lab_id: int) -> Lab:
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise NotFoundError("Lab not found")
    return lab


def _evidences(db: Session, lab_id: int) -> list[Evidence]:
    return list(
        db.scalars(
            select(Evidence)
            .where(Evidence.lab_id == lab_id)
            .order_by(Evidence.display_order, Evidence.id)
        )
    )


def _findings(db: Session, lab_id: int) -> list[Finding]:
    return list(
        db.scalars(
            select(Finding)
            .options(selectinload(Finding.cvss_assessment))
            .where(Finding.lab_id == lab_id)
            .order_by(Finding.display_order, Finding.id)
        )
    )


def evidence_export_name(evidence: Evidence, position: int) -> str:
    extension = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp", "text/plain": ".txt", "message/http": ".http"}[evidence.mime_type]
    prefix = "image" if evidence.mime_type in IMAGE_TYPES else "evidence"
    return f"{prefix}-{position:02d}{extension}"


def _escape_inline(value: str) -> str:
    single_line = " ".join(value.splitlines())
    escaped = single_line.replace("\\", "\\\\")
    for character in "`*_{}[]<>()#+-.!|":
        escaped = escaped.replace(character, f"\\{character}")
    return escaped


def _section(number: int, title: str, content: str | None) -> str | None:
    if not content or not content.strip():
        return None
    return f"## {number}. {title}\n\n{content}"


def incomplete_fields(lab: Lab, findings: list[Finding], evidences: list[Evidence]) -> list[str]:
    fields = {"Objetivo": lab.objective, "Aprendizados": lab.learnings}
    if not findings and any((lab.vulnerability_description, lab.resolution_steps, lab.impact, lab.mitigation)):
        fields.update({
            "Vulnerabilidade": lab.vulnerability_description,
            "Etapas da resolução": lab.resolution_steps,
            "Impacto": lab.impact,
            "Mitigação": lab.mitigation,
        })
    missing = [label for label, value in fields.items() if not value or not value.strip()]
    for finding in findings:
        for label, value in (
            ("Descrição", finding.description),
            ("Reprodução", finding.reproduction_steps),
            ("Impacto", finding.impact),
            ("Mitigação", finding.mitigation),
        ):
            if not value.strip():
                missing.append(f"{finding.title}: {label}")
    return missing


def sensitive_warnings(markdown: str) -> list[str]:
    return [label for label, pattern in SENSITIVE_PATTERNS.items() if pattern.search(markdown)]


def _evidence_markdown(evidences: list[Evidence], all_evidences: list[Evidence]) -> str:
    positions = {item.id: position for position, item in enumerate(all_evidences, 1)}
    lines: list[str] = []
    for evidence in evidences:
        name = evidence_export_name(evidence, positions[evidence.id])
        caption = evidence.description.strip() or evidence.original_filename
        if evidence.step_label:
            lines.append(f"### {_escape_inline(evidence.step_label)}")
        if evidence.mime_type in IMAGE_TYPES:
            lines.append(f"![{_escape_inline(caption)}](evidence/{name})")
        else:
            lines.append(f"[{_escape_inline(caption)}](evidence/{name})")
        lines.append(f"_{_escape_inline(caption)}_")
    return "\n\n".join(lines)


def _finding_section(finding: Finding, evidences: list[Evidence], all_evidences: list[Evidence], level: int) -> str:
    heading = "#" * level
    parts = [f"{heading} {_escape_inline(finding.title)}"]
    metadata = []
    if finding.category:
        metadata.append(f"- Categoria: {_escape_inline(finding.category)}")
    if finding.cwe_id:
        metadata.append(f"- CWE: {finding.cwe_id}")
    metadata.append(f"- Status: {finding.status.value}")
    parts.append("\n".join(metadata))
    for title, content in (
        ("Descrição", finding.description),
        ("Detalhes técnicos", finding.technical_details),
        ("Passos de reprodução", finding.reproduction_steps),
    ):
        if content.strip():
            parts.append(f"{heading}# {title}\n\n{content}")
    related = [item for item in evidences if item.finding_id == finding.id]
    if related:
        parts.append(f"{heading}# Evidências\n\n{_evidence_markdown(related, all_evidences)}")
    if finding.impact.strip():
        parts.append(f"{heading}# Impacto\n\n{finding.impact}")
    if finding.cvss_assessment:
        cvss = finding.cvss_assessment
        cvss_lines = [
            f"- Versão: {cvss.version}", f"- Vetor: `{cvss.vector}`",
            f"- Pontuação: {cvss.score:g}", f"- Severidade: {cvss.severity}",
        ]
        if cvss.justification.strip():
            cvss_lines.append(f"\n{cvss.justification}")
        parts.append(f"{heading}# CVSS\n\n" + "\n".join(cvss_lines))
    if finding.mitigation.strip():
        parts.append(f"{heading}# Mitigação\n\n{finding.mitigation}")
    return "\n\n".join(parts)


def build_markdown(lab: Lab, findings: list[Finding], evidences: list[Evidence]) -> str:
    general = [f"- Plataforma: {_escape_inline(lab.platform.name)}"]
    if lab.category:
        general.append(f"- Categoria: {_escape_inline(lab.category.name)}")
    if lab.difficulty:
        general.append(f"- Dificuldade: {_escape_inline(lab.difficulty)}")
    if lab.source_url:
        general.append(f"- Link original: <{lab.source_url}>")

    sections: list[str | None] = [f"# {_escape_inline(lab.title)}", "## 1. Informações gerais\n\n" + "\n".join(general)]
    sections.append(_section(2, "Objetivo", lab.objective))
    if findings:
        sections.append(_section(3, "Metodologia geral", lab.notes))
        if len(findings) > 1:
            rows = ["| Achado | Categoria | Status | CVSS |", "|---|---|---|---|"]
            for finding in findings:
                cvss = finding.cvss_assessment
                rows.append(
                    f"| {_escape_inline(finding.title)} | {_escape_inline(finding.category or '—')} | "
                    f"{finding.status.value} | {f'{cvss.score:g} · {cvss.severity}' if cvss else '—'} |"
                )
            sections.append("## 4. Resumo dos achados\n\n" + "\n".join(rows))
            sections.append("## 5. Vulnerabilidades\n\n" + "\n\n".join(
                _finding_section(item, evidences, evidences, 3) for item in findings
            ))
            next_number = 6
        else:
            sections.append("## 4. Vulnerabilidade\n\n" + _finding_section(findings[0], evidences, evidences, 3))
            next_number = 5
        general_evidence = [item for item in evidences if item.finding_id is None]
        if general_evidence:
            sections.append(_section(next_number, "Evidências gerais", _evidence_markdown(general_evidence, evidences)))
            next_number += 1
        sections.append(_section(next_number, "Conclusão e aprendizados", lab.learnings))
    else:
        methodology_parts = [value for value in (lab.resolution_steps, lab.notes) if value and value.strip()]
        sections.extend([
            _section(3, "Vulnerabilidade", lab.vulnerability_description),
            _section(4, "Metodologia e resolução", "\n\n".join(methodology_parts)),
            _section(5, "Evidências", _evidence_markdown(evidences, evidences)),
            _section(6, "Impacto", lab.impact),
            _section(7, "Mitigação", lab.mitigation),
            _section(8, "Conclusão e aprendizados", lab.learnings),
        ])
    return "\n\n".join(section for section in sections if section) + "\n"


def get_report(db: Session, lab_id: int) -> Report | None:
    _lab(db, lab_id)
    return db.scalar(select(Report).where(Report.lab_id == lab_id))


def generate_report(db: Session, lab_id: int, confirm_overwrite: bool) -> Report:
    lab = _lab(db, lab_id)
    evidences = _evidences(db, lab_id)
    findings = _findings(db, lab_id)
    report = db.scalar(select(Report).where(Report.lab_id == lab_id))
    if report is not None and not confirm_overwrite:
        raise ConflictError("A report already exists; confirm regeneration before replacing it")
    markdown = build_markdown(lab, findings, evidences)
    manifest = json.dumps(
        {evidence_export_name(item, position): item.id for position, item in enumerate(evidences, 1)},
        sort_keys=True,
    )
    if report is None:
        report = Report(lab_id=lab_id, markdown=markdown, evidence_manifest=manifest)
        db.add(report)
    else:
        report.markdown = markdown
        report.evidence_manifest = manifest
        report.revision += 1
        report.generated_at = datetime.now(timezone.utc)
        report.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report


def save_report(db: Session, lab_id: int, markdown: str) -> Report:
    report = get_report(db, lab_id)
    if report is None:
        raise NotFoundError("Report not found; generate it before saving")
    report.markdown = markdown
    report.revision += 1
    report.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return report


def _validate_zip_path(path: str, root: str) -> None:
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or ".." in candidate.parts or not candidate.parts or candidate.parts[0] != root:
        raise InvalidReportError("Unsafe export path")


def export_report(db: Session, lab_id: int, evidence_ids: list[int], sensitive_reviewed: bool) -> tuple[bytes, str]:
    lab = _lab(db, lab_id)
    report = get_report(db, lab_id)
    if report is None:
        raise NotFoundError("Report not found")
    if not sensitive_reviewed:
        raise InvalidReportError("Sensitive information review must be confirmed")
    if ACTIVE_HTML_PATTERN.search(report.markdown):
        raise InvalidReportError("README contains active HTML; remove it before exporting")
    if len(set(evidence_ids)) != len(evidence_ids):
        raise InvalidReportError("Evidence selection contains duplicates")

    evidences = _evidences(db, lab_id)
    by_id = {item.id: item for item in evidences}
    if any(evidence_id not in by_id for evidence_id in evidence_ids):
        raise InvalidReportError("Export can only include evidence from this laboratory")
    try:
        manifest = {str(name): int(evidence_id) for name, evidence_id in json.loads(report.evidence_manifest).items()}
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InvalidReportError("Report evidence manifest is invalid; regenerate the report") from exc
    if any(not re.fullmatch(r"(?:image|evidence)-\d{2,}\.(?:png|jpg|webp|txt|http)", name) for name in manifest):
        raise InvalidReportError("Report evidence manifest contains an unsafe filename")
    if any(evidence_id not in manifest.values() for evidence_id in evidence_ids):
        raise InvalidReportError("Regenerate the report before exporting newly added evidence")
    selected_names = {name for name, evidence_id in manifest.items() if evidence_id in evidence_ids}
    image_targets = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", report.markdown)
    if any(not target.startswith("evidence/") for target in image_targets):
        raise InvalidReportError("README images must use exported laboratory evidence")
    evidence_targets = re.findall(r"!?\[[^\]]*\]\((evidence/[^)]+)\)", report.markdown)
    referenced: set[str] = set()
    for target in evidence_targets:
        candidate = PurePosixPath(target)
        if len(candidate.parts) != 2 or candidate.parts[0] != "evidence" or not re.fullmatch(r"[A-Za-z0-9._-]+", candidate.name):
            raise InvalidReportError("Unsafe evidence reference in README")
        referenced.add(candidate.name)
    unknown = referenced - selected_names
    if unknown:
        raise InvalidReportError("Select every evidence referenced by the README before exporting")

    root = re.sub(r"[^a-z0-9-]+", "-", lab.slug.lower()).strip("-") or "lab"
    readme_path = f"{root}/README.md"
    _validate_zip_path(readme_path, root)
    markdown_bytes = report.markdown.encode("utf-8")
    total_size = len(markdown_bytes) + sum(by_id[evidence_id].file_size for evidence_id in evidence_ids)
    if total_size > settings.report_export_max_size:
        raise ExportTooLargeError(f"Export exceeds the {settings.report_export_max_size}-byte limit")

    output = io.BytesIO()
    try:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(readme_path, markdown_bytes)
            for name, evidence_id in manifest.items():
                if evidence_id not in evidence_ids:
                    continue
                evidence = by_id[evidence_id]
                archive_path = f"{root}/evidence/{name}"
                _validate_zip_path(archive_path, root)
                archive.writestr(archive_path, evidence_path(evidence).read_bytes())
    except (OSError, zipfile.BadZipFile) as exc:
        raise ServiceError("Failed to create export") from exc
    return output.getvalue(), f"{root}.zip"
