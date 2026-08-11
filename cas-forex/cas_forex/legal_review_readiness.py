"""Legal review readiness for CAS Forex.

This diagnostic separates draft disclosure coverage from counsel-reviewed
public-launch readiness. It is intentionally read-only and does not infer legal
approval from the presence of draft documents.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_KIND = "cas_forex_legal_review_readiness"

DISCLOSURE_DRAFT = Path("docs/legal/CAS_FOREX_DISCLOSURE_DRAFT.md")
TERMS_DRAFT = Path("docs/legal/CAS_FOREX_TERMS_OF_SERVICE_DRAFT.md")
PRIVACY_DRAFT = Path("docs/legal/CAS_FOREX_PRIVACY_POLICY_DRAFT.md")
AUTOMATED_TRADING_DISCLOSURE_DRAFT = Path(
    "docs/legal/CAS_FOREX_AUTOMATED_TRADING_DISCLOSURE_DRAFT.md"
)
AI_LIMITATIONS_DISCLOSURE_DRAFT = Path(
    "docs/legal/CAS_FOREX_AI_LIMITATIONS_DISCLOSURE_DRAFT.md"
)
BROKER_CONNECTIVITY_DISCLOSURE_DRAFT = Path(
    "docs/legal/CAS_FOREX_BROKER_CONNECTIVITY_DISCLOSURE_DRAFT.md"
)
LEGAL_REVIEW_CHECKLIST = Path("docs/legal/CAS_FOREX_LEGAL_REVIEW_CHECKLIST.md")
COUNSEL_REVIEW_RECORD = Path("docs/legal/CAS_FOREX_COUNSEL_REVIEW_RECORD.md")
AUTONOMOUS_EXECUTION_CORRECTION = Path(
    "docs/working/cas_forex_autonomous_execution_correction_2026-07-09.yaml"
)

REQUIRED_DRAFTS = (
    DISCLOSURE_DRAFT,
    TERMS_DRAFT,
    PRIVACY_DRAFT,
    AUTOMATED_TRADING_DISCLOSURE_DRAFT,
    AI_LIMITATIONS_DISCLOSURE_DRAFT,
    BROKER_CONNECTIVITY_DISCLOSURE_DRAFT,
)
CHECKLIST_TERMS = (
    "public launch",
    "counsel",
    "jurisdiction",
    "automated trading",
    "autonomous execution",
    "retail forex",
    "privacy",
    "broker",
    "money movement",
    "risk disclosure",
)
COUNSEL_RECORD_SCOPE_TERMS = (
    "terms",
    "risk",
    "privacy",
    "automated",
    "autonomous",
    "broker",
    "money movement",
)

CLAIM_BOUNDARY = (
    "Legal review readiness is a read-only product/compliance diagnostic. It "
    "does not provide legal advice, create an attorney-client relationship, "
    "approve public launch, authorize live trading, place orders, close "
    "positions, move money, or promise returns."
)


def build_legal_review_readiness(root: Path | str | None = None) -> dict[str, Any]:
    base = Path(root) if root is not None else REPO_ROOT
    counsel = _counsel_record_assessment(base)
    checks = [
        _draft_package_check(base),
        _checklist_check(base),
        counsel,
        _public_launch_check(counsel),
    ]
    attention = [check for check in checks if check["status"] != "OK"]
    counsel_accepted = counsel["status"] == "OK"
    return {
        "report_kind": REPORT_KIND,
        "status": "OK" if not attention else "ATTENTION",
        "launch_legal_status": "READY_FOR_PUBLIC_LAUNCH_LEGAL" if counsel_accepted else "BLOCK_PUBLIC_LAUNCH",
        "counsel_review_accepted": counsel_accepted,
        "ok_count": sum(1 for check in checks if check["status"] == "OK"),
        "attention_count": len(attention),
        "checks": checks,
        "required_documents": {
            "drafts": [path.as_posix() for path in REQUIRED_DRAFTS],
            "checklist": LEGAL_REVIEW_CHECKLIST.as_posix(),
            "counsel_review_record": COUNSEL_REVIEW_RECORD.as_posix(),
        },
        "counsel_review_handoff": _counsel_review_handoff(
            base=base,
            counsel_accepted=counsel_accepted,
            attention=attention,
        ),
        "counsel_review_record_path": COUNSEL_REVIEW_RECORD.as_posix(),
        "top_attention_items": [check["detail"] for check in attention][:6],
        "next_action": (
            "Counsel-reviewed launch record is present with accepted markers."
            if counsel_accepted
            else "Complete qualified legal/compliance review and add an accepted counsel review record before public launch."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }


def _counsel_review_handoff(
    *,
    base: Path,
    counsel_accepted: bool,
    attention: list[dict[str, Any]],
) -> dict[str, Any]:
    documents = [
        DISCLOSURE_DRAFT,
        TERMS_DRAFT,
        PRIVACY_DRAFT,
        AUTOMATED_TRADING_DISCLOSURE_DRAFT,
        AI_LIMITATIONS_DISCLOSURE_DRAFT,
        BROKER_CONNECTIVITY_DISCLOSURE_DRAFT,
        LEGAL_REVIEW_CHECKLIST,
        AUTONOMOUS_EXECUTION_CORRECTION,
        COUNSEL_REVIEW_RECORD,
    ]
    attention_keys = [
        str(check.get("key") or "")
        for check in attention
        if str(check.get("key") or "").strip()
    ]
    return {
        "status": "READY_FOR_RECORD_REVIEW" if counsel_accepted else "COUNSEL_REVIEW_REQUIRED",
        "launch_legal_status": "READY_FOR_PUBLIC_LAUNCH_LEGAL" if counsel_accepted else "BLOCK_PUBLIC_LAUNCH",
        "package_documents": [
            {
                "path": path.as_posix(),
                "present": (base / path).exists(),
                "line_count": _line_count(base / path),
            }
            for path in documents
        ],
        "required_record_fields": [
            "counsel_review_status: accepted",
            "reviewed_by",
            "review_date",
            "scope",
            "qualified_counsel_confirmed: yes",
            "review_artifact_path",
            "review_artifact_sha256",
        ],
        "required_scope_terms": list(COUNSEL_RECORD_SCOPE_TERMS),
        "attention_keys": attention_keys,
        "setup_steps": [
            "Give qualified counsel the draft disclosure, Terms, Privacy Policy, legal review checklist, and current product/spec evidence.",
            "Ask counsel to review public launch, automated trading, autonomous execution, retail forex, broker connectivity, AI limitations, data/privacy, and money-movement surfaces.",
            "Save the final review artifact path and SHA-256, then record the accepted counsel review in Settings > Legal Review Readiness.",
            "Do not treat draft docs, UI copy, or this handoff as public-launch approval without the accepted counsel record.",
        ],
        "record_template": [
            "counsel_review_status: accepted",
            "reviewed_by: <qualified counsel name or firm>",
            "review_date: <yyyy-mm-dd>",
            "scope: Terms, risk disclosure, privacy, automated trading, AI limitations, autonomous execution, broker connectivity, money movement, retail forex, public launch",
            "qualified_counsel_confirmed: yes",
            "review_artifact_path: <local or external final review artifact path>",
            "review_artifact_sha256: <64-character sha256>",
        ],
        "claim_boundary": (
            "This handoff is a read-only legal-review checklist. It does not "
            "provide legal advice, create an attorney-client relationship, "
            "approve public launch, authorize live trading, place orders, move "
            "money, or promise returns."
        ),
    }


def _draft_package_check(base: Path) -> dict[str, Any]:
    evidence = [
        {
            "path": path.as_posix(),
            "present": (base / path).exists(),
            "line_count": _line_count(base / path),
        }
        for path in REQUIRED_DRAFTS
    ]
    missing = [row["path"] for row in evidence if not row["present"]]
    return {
        "key": "draft_disclosure_package",
        "label": "Draft Disclosure Package",
        "status": "OK" if not missing else "MISSING",
        "detail": (
            "Draft risk, Terms, and Privacy documents are present."
            if not missing
            else "Draft risk, Terms, and Privacy documents are incomplete."
        ),
        "evidence": evidence,
        "missing_paths": missing,
        "missing_terms": [],
        "next_action": (
            "Keep draft disclosures synchronized with product behavior."
            if not missing
            else "Add the missing draft legal/disclosure documents."
        ),
    }


def _checklist_check(base: Path) -> dict[str, Any]:
    text = _read_text(base / LEGAL_REVIEW_CHECKLIST).lower()
    missing_terms = [term for term in CHECKLIST_TERMS if term not in text]
    present = bool(text)
    return {
        "key": "legal_review_checklist",
        "label": "Legal Review Checklist",
        "status": "OK" if present and not missing_terms else "MISSING",
        "detail": (
            "Legal review checklist covers public launch, counsel, retail forex, automated trading, broker, risk, and privacy scope."
            if present and not missing_terms
            else "Legal review checklist is missing or does not cover the required review scope."
        ),
        "evidence": [{"term": term, "present": term not in missing_terms} for term in CHECKLIST_TERMS],
        "missing_paths": [] if present else [LEGAL_REVIEW_CHECKLIST.as_posix()],
        "missing_terms": missing_terms,
        "next_action": (
            "Use the checklist as launch-review intake; it is not approval."
            if present and not missing_terms
            else "Add or update the legal review checklist."
        ),
    }


def _counsel_record_assessment(base: Path) -> dict[str, Any]:
    path = base / COUNSEL_REVIEW_RECORD
    text = _read_text(path)
    lowered = text.lower()
    status_value = _field_value(text, "counsel_review_status").lower()
    reviewed_by = _field_value(text, "reviewed_by")
    review_date = _field_value(text, "review_date")
    scope = _field_value(text, "scope").lower()
    review_artifact_path = _field_value(text, "review_artifact_path")
    review_artifact_sha256 = _field_value(text, "review_artifact_sha256").lower()
    qualified_counsel_confirmed = _field_value(text, "qualified_counsel_confirmed").lower()
    missing_terms: list[str] = []
    if status_value != "accepted":
        missing_terms.append("counsel_review_status: accepted")
    if not _meaningful_field(reviewed_by):
        missing_terms.append("reviewed_by")
    if not _meaningful_field(review_date):
        missing_terms.append("review_date")
    if qualified_counsel_confirmed not in {"yes", "true", "1", "confirmed", "accepted"}:
        missing_terms.append("qualified_counsel_confirmed: yes")
    if not _meaningful_field(review_artifact_path):
        missing_terms.append("review_artifact_path")
    if not _looks_sha256(review_artifact_sha256):
        missing_terms.append("review_artifact_sha256")
    for term in COUNSEL_RECORD_SCOPE_TERMS:
        if term not in scope and term not in lowered:
            missing_terms.append(f"scope:{term}")
    present = path.exists()
    accepted = present and not missing_terms
    return {
        "key": "counsel_review_record",
        "label": "Counsel Review Record",
        "status": "OK" if accepted else "MISSING",
        "detail": (
            "Counsel review record contains accepted status, reviewer, date, and required scope markers."
            if accepted
            else "Counsel review record is absent or incomplete; drafts are not public-launch approval."
        ),
        "evidence": [
            {"term": "counsel_review_status: accepted", "present": status_value == "accepted"},
            {"term": "reviewed_by", "present": _meaningful_field(reviewed_by)},
            {"term": "review_date", "present": _meaningful_field(review_date)},
            {"term": "qualified_counsel_confirmed: yes", "present": qualified_counsel_confirmed in {"yes", "true", "1", "confirmed", "accepted"}},
            {"term": "review_artifact_path", "present": _meaningful_field(review_artifact_path)},
            {"term": "review_artifact_sha256", "present": _looks_sha256(review_artifact_sha256)},
            *[
                {"term": f"scope:{term}", "present": term in scope or term in lowered}
                for term in COUNSEL_RECORD_SCOPE_TERMS
            ],
        ],
        "missing_paths": [] if present else [COUNSEL_REVIEW_RECORD.as_posix()],
        "missing_terms": missing_terms,
        "next_action": "Have qualified counsel complete the final review record before public launch.",
    }


def _public_launch_check(counsel: dict[str, Any]) -> dict[str, Any]:
    accepted = counsel["status"] == "OK"
    return {
        "key": "public_launch_legal_status",
        "label": "Public Launch Legal Status",
        "status": "OK" if accepted else "ATTENTION",
        "detail": (
            "Public-launch legal readiness has an accepted counsel review record."
            if accepted
            else "Public launch, hosted paid access, or advising others for compensation remains blocked pending counsel review."
        ),
        "evidence": [{"term": "accepted_counsel_review_record", "present": accepted}],
        "missing_paths": [] if accepted else [COUNSEL_REVIEW_RECORD.as_posix()],
        "missing_terms": [] if accepted else ["accepted_counsel_review_record"],
        "next_action": (
            "Keep the counsel record current if product behavior, jurisdictions, data handling, broker flows, or money movement change."
            if accepted
            else "Do not treat draft docs or UI disclosures as final legal approval."
        ),
    }


def _field_value(text: str, field: str) -> str:
    prefix = f"{field}:"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(prefix):
            return stripped.split(":", 1)[1].strip()
    return ""


def _meaningful_field(value: str) -> bool:
    normalized = value.strip().lower()
    return bool(normalized) and normalized not in {"tbd", "todo", "pending", "none", "n/a"}


def _looks_sha256(value: str) -> bool:
    return bool(value) and len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def _line_count(path: Path) -> int:
    text = _read_text(path)
    return 0 if not text else len(text.splitlines())


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


__all__ = ["REPORT_KIND", "build_legal_review_readiness"]
