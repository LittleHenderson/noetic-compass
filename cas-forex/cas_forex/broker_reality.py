"""Owner-reviewed broker reality gate for CAS Forex.

Broker candidates are not broker approval. Before live trading or payout
automation can be treated as ready, the owner must review the real broker facts:
withdrawal minimums, timing, KYC, withdrawal fees, currency conversion, entity /
jurisdiction, and whether the broker terms permit the intended automation.

This module records that owner review as durable evidence. It does not make
legal/regulatory claims, place orders, move money, or approve a broker on behalf
of the owner.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from cas_forex.broker_profiles import selected_broker_profile
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW_PATH = REPO_ROOT / "runtime" / "broker-reality-review.json"
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "broker-reality-audit.jsonl"

REPORT_KIND = "cas_forex_broker_reality_review"
STATUS_OPEN = "OPEN"
STATUS_ACCEPT = "ACCEPT"
DEFAULT_BROKER_ID = "hugosway"
DEFAULT_REVIEW_VALID_DAYS = 30

REQUIRED_CHECKS = (
    "withdrawal_minimum_reviewed",
    "withdrawal_timing_reviewed",
    "kyc_requirements_reviewed",
    "withdrawal_fees_reviewed",
    "currency_conversion_reviewed",
    "automation_tos_reviewed",
    "broker_entity_reviewed",
    "owner_accepts_broker_terms",
)

TEXT_FIELDS = (
    "broker_entity",
    "withdrawal_minimum",
    "withdrawal_timing",
    "kyc_requirements",
    "withdrawal_fees",
    "currency_conversion",
    "automation_tos",
    "notes",
)

CLAIM_BOUNDARY = (
    "Broker reality review is owner-recorded evidence about broker withdrawal, "
    "KYC, fee, currency, entity, and automation-term facts. It does not provide "
    "legal advice, create broker ACCEPT, place orders, deposit, withdraw, move "
    "bank/card funds, automate payouts, or authorize live trading by itself. "
    "Only the owner can mark the review ACCEPT."
)


class BrokerRealityError(ValueError):
    """Raised when a broker reality review cannot be accepted or loaded."""


def build_broker_reality_review(
    broker_id: str | None = None,
    *,
    review_path: Path | str | None = None,
) -> dict[str, Any]:
    selected = _normalize_broker_id(broker_id)
    stored = _load_review(review_path)
    if stored and _normalize_broker_id(stored.get("broker_id")) == selected:
        review = dict(stored)
    else:
        review = _empty_review(selected)
    return _finalize_review(review)


def update_broker_reality_review(
    patch: Mapping[str, Any],
    *,
    confirm_owner_accept: bool = False,
    review_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    current = build_broker_reality_review(str(patch.get("broker_id") or DEFAULT_BROKER_ID), review_path=review_path)
    review = dict(current)
    review["broker_id"] = _normalize_broker_id(patch.get("broker_id") or review.get("broker_id"))
    profile = selected_broker_profile(review["broker_id"]) or {}
    review["broker_display_name"] = profile.get("display_name") or review["broker_id"]
    review["broker_website"] = profile.get("website") or ""

    checks = dict(review.get("checks") or {})
    for key in REQUIRED_CHECKS:
        if key in patch:
            checks[key] = bool(patch[key])
    review["checks"] = checks

    for key in TEXT_FIELDS:
        if key in patch:
            review[key] = str(patch.get(key) or "").strip()
    if "source_urls" in patch:
        review["source_urls"] = _clean_sources(patch.get("source_urls"))
    if "automation_allowed_by_owner_review" in patch:
        review["automation_allowed_by_owner_review"] = bool(patch.get("automation_allowed_by_owner_review"))
    if "review_valid_days" in patch:
        review["review_valid_days"] = max(1, int(patch.get("review_valid_days") or DEFAULT_REVIEW_VALID_DAYS))

    review["updated_at"] = utc_now().isoformat()
    if confirm_owner_accept:
        _assert_accept_ready(review)
        review["owner_review_status"] = STATUS_ACCEPT
        review["owner_accepted_at"] = utc_now().isoformat()
    else:
        review["owner_review_status"] = STATUS_OPEN
        review["owner_accepted_at"] = None

    finalized = _finalize_review(review)
    _write_json(finalized, _review_path(review_path))
    _append_audit(
        {
            "action": "broker_reality_update",
            "timestamp": utc_now().isoformat(),
            "confirm_owner_accept": confirm_owner_accept,
            "broker_id": finalized["broker_id"],
            "owner_review_status": finalized["owner_review_status"],
            "missing_requirements": finalized["missing_requirements"],
        },
        _audit_path(audit_path),
    )
    return finalized


def reset_broker_reality_review(
    broker_id: str | None = None,
    *,
    review_path: Path | str | None = None,
    audit_path: Path | str | None = None,
) -> dict[str, Any]:
    review = _finalize_review(_empty_review(_normalize_broker_id(broker_id)))
    _write_json(review, _review_path(review_path))
    _append_audit(
        {
            "action": "broker_reality_reset",
            "timestamp": utc_now().isoformat(),
            "broker_id": review["broker_id"],
            "owner_review_status": review["owner_review_status"],
        },
        _audit_path(audit_path),
    )
    return review


def is_broker_reality_accepted(
    broker_id: str | None = None,
    *,
    review_path: Path | str | None = None,
) -> bool:
    review = build_broker_reality_review(broker_id, review_path=review_path)
    return bool(review.get("accepted_for_live_and_payout"))


def _empty_review(broker_id: str) -> dict[str, Any]:
    profile = selected_broker_profile(broker_id) or {}
    return {
        "report_kind": REPORT_KIND,
        "broker_id": broker_id,
        "broker_display_name": profile.get("display_name") or broker_id,
        "broker_website": profile.get("website") or "",
        "owner_review_status": STATUS_OPEN,
        "owner_accepted_at": None,
        "updated_at": None,
        "review_valid_days": DEFAULT_REVIEW_VALID_DAYS,
        "broker_entity": "",
        "withdrawal_minimum": "",
        "withdrawal_timing": "",
        "kyc_requirements": "",
        "withdrawal_fees": "",
        "currency_conversion": "",
        "automation_tos": "",
        "automation_allowed_by_owner_review": False,
        "source_urls": [],
        "notes": "",
        "checks": {key: False for key in REQUIRED_CHECKS},
    }


def _finalize_review(review: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(review)
    data["report_kind"] = REPORT_KIND
    data["broker_id"] = _normalize_broker_id(data.get("broker_id"))
    data["source_urls"] = _clean_sources(data.get("source_urls"))
    data["checks"] = {key: bool((data.get("checks") or {}).get(key, False)) for key in REQUIRED_CHECKS}
    data["review_valid_days"] = max(1, int(data.get("review_valid_days") or DEFAULT_REVIEW_VALID_DAYS))

    missing = _missing_requirements(data)
    stale = _is_stale(data)
    status = STATUS_ACCEPT if data.get("owner_review_status") == STATUS_ACCEPT and not missing and not stale else STATUS_OPEN
    data["owner_review_status"] = status
    data["accepted_for_live_and_payout"] = status == STATUS_ACCEPT
    data["missing_requirements"] = missing + (["broker reality review is stale"] if stale else [])
    data["claim_boundary"] = CLAIM_BOUNDARY
    data["next_action"] = (
        "Broker reality review is owner ACCEPT for live/payout gate purposes."
        if data["accepted_for_live_and_payout"]
        else "Review withdrawal minimums/timing, KYC, fees, currency conversion, entity, and automation terms; add sources; then owner-confirm ACCEPT."
    )
    return data


def _assert_accept_ready(review: Mapping[str, Any]) -> None:
    finalized = _finalize_review({**dict(review), "owner_review_status": STATUS_ACCEPT})
    missing = finalized.get("missing_requirements") or []
    if missing:
        raise BrokerRealityError("Cannot ACCEPT broker reality review; missing: " + "; ".join(missing))


def _missing_requirements(review: Mapping[str, Any]) -> list[str]:
    missing = [key for key, value in (review.get("checks") or {}).items() if key in REQUIRED_CHECKS and not value]
    for key in TEXT_FIELDS[:-1]:
        if not str(review.get(key) or "").strip():
            missing.append(f"{key} text")
    if not _clean_sources(review.get("source_urls")):
        missing.append("source_urls")
    if not bool(review.get("automation_allowed_by_owner_review", False)):
        missing.append("automation_allowed_by_owner_review")
    return missing


def _is_stale(review: Mapping[str, Any]) -> bool:
    accepted_at = review.get("owner_accepted_at")
    if review.get("owner_review_status") != STATUS_ACCEPT or not accepted_at:
        return False
    try:
        from datetime import datetime

        accepted = datetime.fromisoformat(str(accepted_at).replace("Z", "+00:00"))
        age_days = (utc_now() - accepted).total_seconds() / 86_400
    except Exception:
        return True
    return age_days > float(review.get("review_valid_days") or DEFAULT_REVIEW_VALID_DAYS)


def _load_review(path: Path | str | None) -> dict[str, Any] | None:
    target = _review_path(path)
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)


def _append_audit(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), sort_keys=True, default=str) + "\n")


def _review_path(path: Path | str | None) -> Path:
    return Path(path) if path is not None else Path(DEFAULT_REVIEW_PATH)


def _audit_path(path: Path | str | None) -> Path:
    return Path(path) if path is not None else Path(DEFAULT_AUDIT_PATH)


def _normalize_broker_id(value: Any) -> str:
    text = str(value or DEFAULT_BROKER_ID).strip().lower()
    return text or DEFAULT_BROKER_ID


def _clean_sources(value: Any) -> list[str]:
    if isinstance(value, str):
        items = value.replace(",", "\n").splitlines()
    elif isinstance(value, list):
        items = value
    else:
        items = []
    return [str(item).strip() for item in items if str(item).strip()]
