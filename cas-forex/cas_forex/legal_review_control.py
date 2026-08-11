"""Owner-managed counsel review record control for CAS Forex.

This module turns the counsel-review launch artifact from a hand-edited markdown
note into a structured owner workflow. It records metadata about an external
qualified counsel review, but it does not create legal approval by itself and
does not weaken the existing public-launch boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path
from typing import Any, Optional

from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORD_PATH = Path("docs") / "legal" / "CAS_FOREX_COUNSEL_REVIEW_RECORD.md"
DEFAULT_AUDIT_PATH = Path("runtime") / "legal-review-record-audit.jsonl"
REPORT_KIND = "cas_forex_legal_review_control"
RECORD_CONFIRM_PHRASE = "RECORD QUALIFIED COUNSEL REVIEW"

CLAIM_BOUNDARY = (
    "Legal review control records owner-supplied metadata about an external "
    "qualified counsel review. It does not provide legal advice, create "
    "public-launch approval by itself, authorize live trading, place orders, "
    "close positions, move money, or promise returns."
)

_LOCK = threading.RLock()
_RECORD_PATH = DEFAULT_RECORD_PATH
_AUDIT_PATH = DEFAULT_AUDIT_PATH


class LegalReviewControlError(ValueError):
    """Raised when the counsel review record cannot be written safely."""


def set_legal_review_paths_for_tests(
    record_path: Optional[Path] = None,
    audit_path: Optional[Path] = None,
) -> None:
    global _RECORD_PATH, _AUDIT_PATH
    with _LOCK:
        _RECORD_PATH = Path(record_path) if record_path is not None else DEFAULT_RECORD_PATH
        _AUDIT_PATH = Path(audit_path) if audit_path is not None else DEFAULT_AUDIT_PATH


def build_legal_review_control_report(
    root: Path | str | None = None,
) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    record = load_counsel_review_record(base)
    return {
        "report_kind": REPORT_KIND,
        "status": "OK",
        "record_path": _record_path(base).as_posix(),
        "audit_path": _audit_path(base).as_posix(),
        "required_confirm_phrase": RECORD_CONFIRM_PHRASE,
        "file_present": bool(record.get("file_present")),
        "current_record": record,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def load_counsel_review_record(root: Path | str | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    path = _record_path(base)
    text = _read_text(path)
    record_path_value = _field_value(text, "review_artifact_path")
    artifact_hash = _field_value(text, "review_artifact_sha256")
    local_artifact = _resolve_local_artifact(base, record_path_value)
    return {
        "file_present": path.exists(),
        "counsel_review_status": _field_value(text, "counsel_review_status"),
        "reviewed_by": _field_value(text, "reviewed_by"),
        "review_date": _field_value(text, "review_date"),
        "scope": _field_value(text, "scope"),
        "qualified_counsel_confirmed": _as_bool(_field_value(text, "qualified_counsel_confirmed")),
        "review_artifact_path": record_path_value,
        "review_artifact_sha256": artifact_hash,
        "matter_reference": _field_value(text, "matter_reference"),
        "jurisdictions": _field_value(text, "jurisdictions"),
        "notes": _field_value(text, "notes"),
        "recorded_via": _field_value(text, "recorded_via"),
        "recorded_at": _field_value(text, "recorded_at"),
        "artifact_path_exists_locally": bool(local_artifact and local_artifact.exists()),
        "artifact_hash_looks_valid": _looks_sha256(artifact_hash),
    }


def write_counsel_review_record(
    *,
    reviewed_by: str,
    review_date: str,
    scope: str,
    review_artifact_path: str,
    review_artifact_sha256: str = "",
    matter_reference: str = "",
    jurisdictions: str = "",
    notes: str = "",
    qualified_counsel_confirmed: bool = False,
    confirm_phrase: str = "",
    counsel_review_status: str = "accepted",
    root: Path | str | None = None,
) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    normalized_status = str(counsel_review_status or "").strip().lower()
    if normalized_status != "accepted":
        raise LegalReviewControlError("Only an accepted counsel review record may be written through this control.")
    if str(confirm_phrase or "").strip() != RECORD_CONFIRM_PHRASE:
        raise LegalReviewControlError(
            f"Typed confirmation is required before recording an accepted counsel review: {RECORD_CONFIRM_PHRASE}"
        )

    cleaned_reviewed_by = _clean_single_line(reviewed_by)
    cleaned_review_date = _clean_single_line(review_date)
    cleaned_scope = _clean_single_line(scope)
    cleaned_artifact_path = _clean_single_line(review_artifact_path)
    cleaned_matter_reference = _clean_single_line(matter_reference)
    cleaned_jurisdictions = _clean_single_line(jurisdictions)
    cleaned_notes = _clean_single_line(notes)

    if not _meaningful_field(cleaned_reviewed_by):
        raise LegalReviewControlError("reviewed_by is required.")
    if not _meaningful_field(cleaned_review_date):
        raise LegalReviewControlError("review_date is required.")
    if not _meaningful_field(cleaned_scope):
        raise LegalReviewControlError("scope is required.")
    if not qualified_counsel_confirmed:
        raise LegalReviewControlError("qualified_counsel_confirmed must be true before recording the review.")
    if not _meaningful_field(cleaned_artifact_path):
        raise LegalReviewControlError("review_artifact_path is required.")

    resolved_hash = _clean_single_line(review_artifact_sha256).lower()
    hash_source = "provided"
    if not _looks_sha256(resolved_hash):
        computed = _compute_local_artifact_sha256(base, cleaned_artifact_path)
        if computed:
            resolved_hash = computed
            hash_source = "computed_from_local_artifact"
    if not _looks_sha256(resolved_hash):
        raise LegalReviewControlError(
            "A valid review_artifact_sha256 is required unless review_artifact_path points to a readable local file."
        )

    payload = {
        "counsel_review_status": "accepted",
        "reviewed_by": cleaned_reviewed_by,
        "review_date": cleaned_review_date,
        "scope": cleaned_scope,
        "qualified_counsel_confirmed": "yes",
        "review_artifact_path": cleaned_artifact_path,
        "review_artifact_sha256": resolved_hash,
        "matter_reference": cleaned_matter_reference,
        "jurisdictions": cleaned_jurisdictions,
        "notes": cleaned_notes,
        "recorded_via": "settings_legal_review_control",
        "recorded_at": utc_now().isoformat(),
        "artifact_hash_source": hash_source,
    }

    target = _record_path(base)
    text = _render_record(payload)
    with _LOCK:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(target)
        _append_audit(
            {
                "action": "write_counsel_review_record",
                "recorded_at": payload["recorded_at"],
                "reviewed_by": cleaned_reviewed_by,
                "review_date": cleaned_review_date,
                "qualified_counsel_confirmed": True,
                "review_artifact_path": cleaned_artifact_path,
                "review_artifact_sha256": resolved_hash,
                "artifact_hash_source": hash_source,
                "record_path": target.as_posix(),
            },
            base,
        )
    return build_legal_review_control_report(base)


def reset_counsel_review_record(
    *,
    reason: str = "OWNER_RESET",
    root: Path | str | None = None,
) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    target = _record_path(base)
    with _LOCK:
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        _append_audit(
            {
                "action": "reset_counsel_review_record",
                "recorded_at": utc_now().isoformat(),
                "reason": _clean_single_line(reason) or "OWNER_RESET",
                "record_path": target.as_posix(),
            },
            base,
        )
    return build_legal_review_control_report(base)


def _render_record(payload: dict[str, str]) -> str:
    ordered_keys = (
        "counsel_review_status",
        "reviewed_by",
        "review_date",
        "scope",
        "qualified_counsel_confirmed",
        "review_artifact_path",
        "review_artifact_sha256",
        "matter_reference",
        "jurisdictions",
        "notes",
        "recorded_via",
        "recorded_at",
        "artifact_hash_source",
    )
    lines = [
        "# CAS Forex Counsel Review Record",
        "",
        "This file records owner-supplied metadata about an external qualified counsel review.",
        "It does not create public-launch legal approval by itself.",
        "",
    ]
    for key in ordered_keys:
        lines.append(f"{key}: {payload.get(key, '')}")
    lines.append("")
    return "\n".join(lines)


def _append_audit(event: dict[str, Any], base: Path) -> None:
    path = _audit_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True))
        handle.write("\n")


def _record_path(base: Path) -> Path:
    return _RECORD_PATH if _RECORD_PATH.is_absolute() else base / _RECORD_PATH


def _audit_path(base: Path) -> Path:
    return _AUDIT_PATH if _AUDIT_PATH.is_absolute() else base / _AUDIT_PATH


def _field_value(text: str, field: str) -> str:
    prefix = f"{field}:"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(prefix):
            return stripped.split(":", 1)[1].strip()
    return ""


def _clean_single_line(value: Any) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    return re.sub(r"\s+", " ", text)


def _meaningful_field(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    return bool(normalized) and normalized not in {"tbd", "todo", "pending", "none", "n/a"}


def _looks_sha256(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{64}", str(value or "").strip()))


def _as_bool(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "accepted", "confirmed"}


def _resolve_local_artifact(base: Path, artifact_path: str) -> Optional[Path]:
    text = str(artifact_path or "").strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    return base / path


def _compute_local_artifact_sha256(base: Path, artifact_path: str) -> str:
    path = _resolve_local_artifact(base, artifact_path)
    if path is None or not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


__all__ = [
    "CLAIM_BOUNDARY",
    "DEFAULT_AUDIT_PATH",
    "DEFAULT_RECORD_PATH",
    "LegalReviewControlError",
    "RECORD_CONFIRM_PHRASE",
    "REPORT_KIND",
    "build_legal_review_control_report",
    "load_counsel_review_record",
    "reset_counsel_review_record",
    "set_legal_review_paths_for_tests",
    "write_counsel_review_record",
]
