import hashlib
import os
from pathlib import Path, PurePath
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.evidence import Evidence
from app.models.finding import Finding
from app.models.lab import Lab
from app.schemas.evidence import EvidenceReorder, EvidenceUpdate
from app.services.errors import ConflictError, NotFoundError, ServiceError

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".txt", ".http"}
STORED_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "text/plain": ".txt",
    "message/http": ".http",
}


class InvalidEvidenceError(ServiceError):
    status_code = 422


class EvidenceTooLargeError(ServiceError):
    status_code = 413


def _lab_or_404(db: Session, lab_id: int) -> Lab:
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise NotFoundError("Lab not found")
    return lab


def _safe_original_filename(filename: str | None) -> tuple[str, str]:
    if not filename or len(filename) > 255 or "\x00" in filename:
        raise InvalidEvidenceError("Invalid filename")
    if filename != PurePath(filename).name or "/" in filename or "\\" in filename:
        raise InvalidEvidenceError("Filename must not contain a path")
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise InvalidEvidenceError("Unsupported file extension")
    return filename, extension


def _detect_content_type(content: bytes, extension: str) -> str:
    if (
        len(content) >= 33
        and content.startswith(b"\x89PNG\r\n\x1a\n")
        and content[12:16] == b"IHDR"
        and b"IEND" in content[-16:]
    ):
        detected = "image/png"
        valid_extensions = {".png"}
    elif content.startswith(b"\xff\xd8\xff") and content.endswith(b"\xff\xd9"):
        detected = "image/jpeg"
        valid_extensions = {".jpg", ".jpeg"}
    elif (
        len(content) >= 20
        and content[:4] == b"RIFF"
        and content[8:12] == b"WEBP"
        and int.from_bytes(content[4:8], "little") + 8 <= len(content)
    ):
        detected = "image/webp"
        valid_extensions = {".webp"}
    else:
        if extension not in {".txt", ".http"}:
            raise InvalidEvidenceError("File content does not match its image extension")
        if b"\x00" in content:
            raise InvalidEvidenceError("Text evidence contains binary data")
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise InvalidEvidenceError("Text evidence must be valid UTF-8") from exc
        if any(ord(character) < 9 or 13 < ord(character) < 32 for character in text):
            raise InvalidEvidenceError("Text evidence contains unsupported control characters")
        return "message/http" if extension == ".http" else "text/plain"
    if extension not in valid_extensions:
        raise InvalidEvidenceError("File content does not match its extension")
    return detected


def _storage_root() -> Path:
    root = Path(settings.evidence_storage_path).expanduser().resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    return root


def evidence_path(evidence: Evidence) -> Path:
    root = _storage_root()
    candidate = (root / evidence.stored_filename).resolve()
    if candidate.parent != root or candidate.name != evidence.stored_filename:
        raise NotFoundError("Evidence file not found")
    if not candidate.is_file():
        raise NotFoundError("Evidence file not found")
    return candidate


def list_evidences(db: Session, lab_id: int) -> list[Evidence]:
    _lab_or_404(db, lab_id)
    return list(
        db.scalars(
            select(Evidence)
            .where(Evidence.lab_id == lab_id)
            .order_by(Evidence.display_order, Evidence.id)
        )
    )


async def upload_evidences(db: Session, lab_id: int, files: list[UploadFile]) -> list[Evidence]:
    _lab_or_404(db, lab_id)
    if not files:
        raise InvalidEvidenceError("Select at least one file")
    if len(files) > settings.evidence_max_files_per_upload:
        raise InvalidEvidenceError(
            f"A maximum of {settings.evidence_max_files_per_upload} files can be uploaded at once"
        )
    current_count = db.scalar(
        select(func.count()).select_from(Evidence).where(Evidence.lab_id == lab_id)
    ) or 0
    if current_count + len(files) > settings.evidence_max_files_per_lab:
        raise InvalidEvidenceError(
            f"A laboratory can contain at most {settings.evidence_max_files_per_lab} evidences"
        )

    prepared: list[tuple[str, bytes, str, str]] = []
    hashes: set[str] = set()
    for upload in files:
        original_filename, extension = _safe_original_filename(upload.filename)
        content = await upload.read(settings.evidence_max_file_size + 1)
        await upload.close()
        if len(content) > settings.evidence_max_file_size:
            raise EvidenceTooLargeError(
                f"{original_filename} exceeds the {settings.evidence_max_file_size}-byte limit"
            )
        if not content:
            raise InvalidEvidenceError(f"{original_filename} is empty")
        mime_type = _detect_content_type(content, extension)
        digest = hashlib.sha256(content).hexdigest()
        if digest in hashes or db.scalar(
            select(Evidence.id).where(Evidence.lab_id == lab_id, Evidence.sha256 == digest)
        ):
            raise ConflictError(f"Duplicate evidence: {original_filename}")
        hashes.add(digest)
        prepared.append((original_filename, content, mime_type, digest))

    root = _storage_root()
    created_paths: list[Path] = []
    evidences: list[Evidence] = []
    try:
        for offset, (original_filename, content, mime_type, digest) in enumerate(prepared):
            stored_filename = f"{uuid4().hex}{STORED_EXTENSIONS[mime_type]}"
            path = root / stored_filename
            with path.open("xb") as stream:
                os.chmod(path, 0o600)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            created_paths.append(path)
            evidence = Evidence(
                lab_id=lab_id,
                original_filename=original_filename,
                stored_filename=stored_filename,
                mime_type=mime_type,
                file_size=len(content),
                sha256=digest,
                description=Path(original_filename).stem,
                display_order=current_count + offset,
            )
            db.add(evidence)
            evidences.append(evidence)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise ConflictError("Duplicate evidence") from exc
    except Exception:
        db.rollback()
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise
    for evidence in evidences:
        db.refresh(evidence)
    return evidences


def get_evidence(db: Session, lab_id: int, evidence_id: int) -> Evidence:
    evidence = db.scalar(
        select(Evidence).where(Evidence.id == evidence_id, Evidence.lab_id == lab_id)
    )
    if evidence is None:
        raise NotFoundError("Evidence not found")
    return evidence


def update_evidence(
    db: Session, lab_id: int, evidence_id: int, data: EvidenceUpdate
) -> Evidence:
    evidence = get_evidence(db, lab_id, evidence_id)
    changes = data.model_dump(exclude_unset=True)
    if "finding_id" in changes and changes["finding_id"] is not None:
        finding = db.scalar(
            select(Finding).where(
                Finding.id == changes["finding_id"], Finding.lab_id == lab_id
            )
        )
        if finding is None:
            raise InvalidEvidenceError("Evidence can only be associated with a finding from this laboratory")
    for field, value in changes.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(evidence, field, value or ("" if field == "description" else None))
    db.commit()
    db.refresh(evidence)
    return evidence


def reorder_evidences(db: Session, lab_id: int, data: EvidenceReorder) -> list[Evidence]:
    current = list(db.scalars(select(Evidence).where(Evidence.lab_id == lab_id)))
    if not current:
        _lab_or_404(db, lab_id)
    if set(data.evidence_ids) != {item.id for item in current}:
        raise InvalidEvidenceError("evidence_ids must contain every evidence from the laboratory")
    by_id = {item.id: item for item in current}
    for order, evidence_id in enumerate(data.evidence_ids):
        by_id[evidence_id].display_order = order
    db.commit()
    return [by_id[evidence_id] for evidence_id in data.evidence_ids]


def delete_evidence(db: Session, lab_id: int, evidence_id: int) -> None:
    evidence = get_evidence(db, lab_id, evidence_id)
    path = evidence_path(evidence)
    db.delete(evidence)
    db.commit()
    path.unlink(missing_ok=True)
    remaining = list_evidences(db, lab_id)
    for order, item in enumerate(remaining):
        item.display_order = order
    db.commit()


def lab_evidence_paths(db: Session, lab_id: int) -> list[Path]:
    paths: list[Path] = []
    for evidence in list_evidences(db, lab_id):
        try:
            paths.append(evidence_path(evidence))
        except NotFoundError:
            pass
    return paths
