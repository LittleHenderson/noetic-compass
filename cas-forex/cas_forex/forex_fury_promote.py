"""Promote Forex Fury replay candidates into the strategy_leads research lane.

This module is Step 4-5 of the Forex Fury activation recipe. It binds a
replay candidate (already CAS-derived from owner-supplied set evidence) to
a strategy_leads.json entry once the underlying .set file is sha256-verified
against the import manifest.

Hard boundary: promotions land in the paper research lane only. The
``status`` field is hard-coded to ``"PROMOTED_PAPER_LANE"`` — there is no
code path here that produces ``"PROMOTED_LIVE"``. Live promotion remains an
operator-driven license flip handled outside this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Optional


CLAIM_BOUNDARY = (
    "Forex Fury promotions land in the paper research lane only. This module "
    "never writes PROMOTED_LIVE; live-money execution remains operator-driven "
    "and gated by the broker-license flip."
)

PAPER_LANE_STATUS = "PROMOTED_PAPER_LANE"


@dataclass(frozen=True)
class SetIntegrityVerification:
    """Result of comparing an on-disk .set file's sha256 to the manifest."""

    profile_id: str
    expected_sha256: str
    actual_sha256: Optional[str]
    verified: bool
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "expected_sha256": self.expected_sha256,
            "actual_sha256": self.actual_sha256,
            "verified": self.verified,
            "error_message": self.error_message,
        }


@dataclass(frozen=True)
class ForexFuryPromotionResult:
    """Outcome of a single promote_candidate call."""

    candidate_id: str
    profile_id: Optional[str]
    promoted_at_iso: Optional[str]
    lead_path: Optional[str]
    integrity: Optional[SetIntegrityVerification]
    accepted: bool
    rejection_reason: Optional[str] = None
    lead_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "profile_id": self.profile_id,
            "promoted_at_iso": self.promoted_at_iso,
            "lead_path": self.lead_path,
            "integrity": self.integrity.to_dict() if self.integrity is not None else None,
            "accepted": self.accepted,
            "rejection_reason": self.rejection_reason,
            "lead_id": self.lead_id,
        }


def verify_set_integrity(
    *,
    profile_id: str,
    relative_source_path: str,
    expected_sha256: str,
    repo_root: Path,
) -> SetIntegrityVerification:
    """Pure-ish verifier: read the .set at repo_root / relative_source_path and
    compare its sha256 to expected_sha256. Never raises."""

    if not relative_source_path:
        return SetIntegrityVerification(
            profile_id=profile_id,
            expected_sha256=expected_sha256,
            actual_sha256=None,
            verified=False,
            error_message="set file path is empty",
        )
    target = (Path(repo_root) / relative_source_path).resolve()
    if not target.exists() or not target.is_file():
        return SetIntegrityVerification(
            profile_id=profile_id,
            expected_sha256=expected_sha256,
            actual_sha256=None,
            verified=False,
            error_message=f"set file missing at {relative_source_path}",
        )
    try:
        actual = _file_sha256(target)
    except OSError as exc:
        return SetIntegrityVerification(
            profile_id=profile_id,
            expected_sha256=expected_sha256,
            actual_sha256=None,
            verified=False,
            error_message=f"could not read set file: {exc}",
        )
    if not expected_sha256:
        return SetIntegrityVerification(
            profile_id=profile_id,
            expected_sha256=expected_sha256,
            actual_sha256=actual,
            verified=False,
            error_message="expected sha256 was empty in manifest",
        )
    if actual.lower() != expected_sha256.lower():
        return SetIntegrityVerification(
            profile_id=profile_id,
            expected_sha256=expected_sha256,
            actual_sha256=actual,
            verified=False,
            error_message="sha256 mismatch against manifest",
        )
    return SetIntegrityVerification(
        profile_id=profile_id,
        expected_sha256=expected_sha256,
        actual_sha256=actual,
        verified=True,
        error_message=None,
    )


def promote_candidate(
    *,
    candidate_id: str,
    replay_candidates: Mapping[str, Any],
    repo_root: Path,
    leads_path: Path,
    now: Optional[datetime] = None,
) -> ForexFuryPromotionResult:
    """Promote a candidate into strategy_leads.json under the paper research lane.

    Choice on idempotency: APPEND. Promoting the same candidate twice produces
    two distinct lead entries (distinct ``lead_id`` derived from
    ``candidate_id`` + ``promoted_at_iso``). The leads file is research-lane
    history; we preserve the audit trail of every promotion attempt rather
    than silently merge. Callers wanting dedupe can pre-check via the
    promotion-status API.
    """

    now = now or datetime.now(UTC)
    promoted_at_iso = now.replace(microsecond=0).isoformat()

    candidate = _find_candidate(replay_candidates, candidate_id)
    if candidate is None:
        return ForexFuryPromotionResult(
            candidate_id=candidate_id,
            profile_id=None,
            promoted_at_iso=None,
            lead_path=None,
            integrity=None,
            accepted=False,
            rejection_reason="candidate not found",
        )

    profile_id = str(candidate.get("source_profile_id") or "")
    relative_path = str(candidate.get("source_set_path") or "")
    expected_sha = str(candidate.get("source_set_sha256") or "")

    integrity = verify_set_integrity(
        profile_id=profile_id,
        relative_source_path=relative_path,
        expected_sha256=expected_sha,
        repo_root=repo_root,
    )
    if not integrity.verified:
        if integrity.error_message and "missing" in integrity.error_message:
            reason = "set file missing"
        else:
            reason = "sha256 mismatch"
        return ForexFuryPromotionResult(
            candidate_id=candidate_id,
            profile_id=profile_id or None,
            promoted_at_iso=None,
            lead_path=None,
            integrity=integrity,
            accepted=False,
            rejection_reason=reason,
        )

    lead_id = _deterministic_lead_id(candidate_id, promoted_at_iso)
    evidence = candidate.get("evidence") or {}
    lead_entry: dict[str, Any] = {
        "lead_id": lead_id,
        "candidate_id": candidate_id,
        "family": candidate.get("family"),
        "symbol": candidate.get("cas_symbol"),
        "timeframe": candidate.get("timeframe"),
        "source_profile_id": profile_id or None,
        "source_set_path": relative_path,
        "source_sha256": expected_sha,
        "evidence_ref": {
            "profit_factor": evidence.get("profit_factor"),
            "equity_drawdown_relative_pct": evidence.get("equity_drawdown_relative_pct"),
            "total_trades": evidence.get("total_trades"),
            "walk_forward_grade": evidence.get("walk_forward_grade"),
        },
        "promoted_at_iso": promoted_at_iso,
        "status": PAPER_LANE_STATUS,
        "claim_boundary": CLAIM_BOUNDARY,
    }

    _append_lead_atomic(leads_path, lead_entry)

    return ForexFuryPromotionResult(
        candidate_id=candidate_id,
        profile_id=profile_id or None,
        promoted_at_iso=promoted_at_iso,
        lead_path=str(leads_path),
        integrity=integrity,
        accepted=True,
        rejection_reason=None,
        lead_id=lead_id,
    )


def find_promoted_lead(leads_path: Path, candidate_id: str) -> Optional[dict[str, Any]]:
    """Return the most recent paper-lane lead entry for candidate_id, or None."""

    if not leads_path.exists():
        return None
    try:
        document = json.loads(leads_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    leads = document.get("leads")
    if not isinstance(leads, list):
        return None
    matches = [
        entry
        for entry in leads
        if isinstance(entry, dict) and entry.get("candidate_id") == candidate_id
    ]
    if not matches:
        return None
    # Most recent by promoted_at_iso when present; otherwise last in list.
    matches.sort(key=lambda e: str(e.get("promoted_at_iso") or ""))
    return matches[-1]


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_candidate(
    replay_candidates: Mapping[str, Any], candidate_id: str
) -> Optional[Mapping[str, Any]]:
    if not isinstance(replay_candidates, Mapping):
        return None
    candidates = replay_candidates.get("candidates")
    if not isinstance(candidates, list):
        return None
    for entry in candidates:
        if isinstance(entry, Mapping) and entry.get("candidate_id") == candidate_id:
            return entry
    return None


def _deterministic_lead_id(candidate_id: str, promoted_at_iso: str) -> str:
    digest = hashlib.sha256(f"{candidate_id}|{promoted_at_iso}".encode("utf-8")).hexdigest()
    return f"ff-lead-{digest[:12]}"


def _append_lead_atomic(leads_path: Path, lead_entry: Mapping[str, Any]) -> None:
    """Read-modify-write strategy_leads.json atomically.

    A new file is initialized with the v1 schema envelope if missing. The
    write goes through a tempfile in the same directory plus ``os.replace``
    so a crash mid-write cannot leave a half-written leads file.
    """

    leads_path = Path(leads_path)
    leads_path.parent.mkdir(parents=True, exist_ok=True)

    if leads_path.exists():
        try:
            document = json.loads(leads_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                f"strategy_leads file at {leads_path} is unreadable: {exc}"
            ) from exc
        if not isinstance(document, dict):
            raise RuntimeError(
                f"strategy_leads file at {leads_path} must contain a JSON object"
            )
    else:
        document = {
            "schema_version": "cas-forex-strategy-leads.v1",
            "claim_boundary": CLAIM_BOUNDARY,
            "leads": [],
        }

    leads = document.get("leads")
    if not isinstance(leads, list):
        document["leads"] = []
        leads = document["leads"]
    leads.append(dict(lead_entry))
    document["updated_at"] = lead_entry.get("promoted_at_iso") or document.get("updated_at")

    payload = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False)

    fd, tmp_path = tempfile.mkstemp(
        prefix=".strategy_leads.",
        suffix=".tmp",
        dir=str(leads_path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp_path, leads_path)
    except Exception:
        # Best-effort cleanup; if replace already moved tmp_path, unlink will
        # raise FileNotFoundError which we ignore.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
