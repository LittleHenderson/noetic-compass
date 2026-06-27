"""Unit tests for cas_forex.forex_fury_promote."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from cas_forex.forex_fury_promote import (
    PAPER_LANE_STATUS,
    ForexFuryPromotionResult,
    SetIntegrityVerification,
    find_promoted_lead,
    promote_candidate,
    verify_set_integrity,
)


SET_CONTENT = b"ForexFury|profile=demo|tp=10|sl=5|window=04:00-05:00\n"
SET_SHA256 = hashlib.sha256(SET_CONTENT).hexdigest()


def _write_set_file(repo_root: Path, relative: str, content: bytes = SET_CONTENT) -> Path:
    target = repo_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return target


def _candidate(
    candidate_id: str = "ff-replay-eur-usd-m5-scalping-abc1234567",
    relative_set: str = "sets/demo/EURUSD-M5.set",
    sha256: str = SET_SHA256,
    family: str = "scalping",
    symbol: str = "EUR/USD",
    timeframe: str = "M5",
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "source_profile_id": "ff-demo-profile-1",
        "source_set_path": relative_set,
        "source_set_sha256": sha256,
        "family": family,
        "cas_symbol": symbol,
        "timeframe": timeframe,
        "evidence": {
            "profit_factor": 1.85,
            "equity_drawdown_relative_pct": 12.5,
            "total_trades": 240,
            "walk_forward_grade": "WALK_FORWARD_LEAD",
        },
    }


# ---------------------------------------------------------------------------
# verify_set_integrity
# ---------------------------------------------------------------------------


def test_verify_set_integrity_matches(tmp_path: Path) -> None:
    _write_set_file(tmp_path, "sets/demo.set")
    result = verify_set_integrity(
        profile_id="p1",
        relative_source_path="sets/demo.set",
        expected_sha256=SET_SHA256,
        repo_root=tmp_path,
    )
    assert isinstance(result, SetIntegrityVerification)
    assert result.verified is True
    assert result.actual_sha256 == SET_SHA256
    assert result.error_message is None


def test_verify_set_integrity_mismatch(tmp_path: Path) -> None:
    _write_set_file(tmp_path, "sets/demo.set")
    result = verify_set_integrity(
        profile_id="p1",
        relative_source_path="sets/demo.set",
        expected_sha256="0" * 64,
        repo_root=tmp_path,
    )
    assert result.verified is False
    assert result.actual_sha256 == SET_SHA256
    assert "mismatch" in (result.error_message or "")


def test_verify_set_integrity_missing_file(tmp_path: Path) -> None:
    result = verify_set_integrity(
        profile_id="p1",
        relative_source_path="sets/nope.set",
        expected_sha256=SET_SHA256,
        repo_root=tmp_path,
    )
    assert result.verified is False
    assert result.actual_sha256 is None
    assert result.error_message is not None
    assert "set file missing" in result.error_message


# ---------------------------------------------------------------------------
# promote_candidate
# ---------------------------------------------------------------------------


def test_promote_unknown_candidate_rejected(tmp_path: Path) -> None:
    leads_path = tmp_path / "strategy_leads.json"
    result = promote_candidate(
        candidate_id="ff-replay-does-not-exist",
        replay_candidates={"candidates": [_candidate()]},
        repo_root=tmp_path,
        leads_path=leads_path,
    )
    assert isinstance(result, ForexFuryPromotionResult)
    assert result.accepted is False
    assert result.rejection_reason == "candidate not found"
    assert not leads_path.exists()


def test_promote_integrity_failure_does_not_write_leads(tmp_path: Path) -> None:
    leads_path = tmp_path / "strategy_leads.json"
    # No .set file on disk => integrity fails => leads must not be touched.
    cand = _candidate()
    result = promote_candidate(
        candidate_id=cand["candidate_id"],
        replay_candidates={"candidates": [cand]},
        repo_root=tmp_path,
        leads_path=leads_path,
    )
    assert result.accepted is False
    assert result.rejection_reason == "set file missing"
    assert result.integrity is not None
    assert result.integrity.verified is False
    assert not leads_path.exists()


def test_promote_allow_unverified_writes_flagged_lead(tmp_path: Path) -> None:
    leads_path = tmp_path / "strategy_leads.json"
    # No .set file on disk => integrity fails, but the owner override promotes
    # anyway, and the lead is flagged so it can never be mistaken for verified.
    cand = _candidate()
    result = promote_candidate(
        candidate_id=cand["candidate_id"],
        replay_candidates={"candidates": [cand]},
        repo_root=tmp_path,
        leads_path=leads_path,
        allow_unverified=True,
    )
    assert result.accepted is True
    assert result.lead_id is not None
    assert result.integrity is not None and result.integrity.verified is False

    entry = json.loads(leads_path.read_text(encoding="utf-8"))["leads"][0]
    assert entry["integrity_verified"] is False
    assert entry["integrity_override"] is True
    assert entry["status"] == "PROMOTED_PAPER_LANE"


def test_promote_success_writes_lead_entry(tmp_path: Path) -> None:
    _write_set_file(tmp_path, "sets/demo.set")
    cand = _candidate(relative_set="sets/demo.set")
    leads_path = tmp_path / "strategy_leads.json"

    result = promote_candidate(
        candidate_id=cand["candidate_id"],
        replay_candidates={"candidates": [cand]},
        repo_root=tmp_path,
        leads_path=leads_path,
        now=datetime(2026, 6, 24, 12, 0, 0, tzinfo=UTC),
    )

    assert result.accepted is True
    assert result.lead_path == str(leads_path)
    assert result.lead_id is not None
    assert result.integrity is not None and result.integrity.verified

    document = json.loads(leads_path.read_text(encoding="utf-8"))
    assert document["schema_version"] == "cas-forex-strategy-leads.v1"
    assert len(document["leads"]) == 1
    entry = document["leads"][0]
    assert entry["candidate_id"] == cand["candidate_id"]
    assert entry["symbol"] == "EUR/USD"
    assert entry["timeframe"] == "M5"
    assert entry["family"] == "scalping"
    assert entry["source_sha256"] == SET_SHA256
    assert entry["evidence_ref"]["profit_factor"] == 1.85


def test_promoted_lead_status_is_paper_lane_never_live(tmp_path: Path) -> None:
    _write_set_file(tmp_path, "sets/demo.set")
    cand = _candidate(relative_set="sets/demo.set")
    leads_path = tmp_path / "strategy_leads.json"

    promote_candidate(
        candidate_id=cand["candidate_id"],
        replay_candidates={"candidates": [cand]},
        repo_root=tmp_path,
        leads_path=leads_path,
    )

    document = json.loads(leads_path.read_text(encoding="utf-8"))
    entry = document["leads"][0]
    assert entry["status"] == PAPER_LANE_STATUS
    assert entry["status"] == "PROMOTED_PAPER_LANE"
    assert "LIVE" not in entry["status"]


def test_promote_same_candidate_twice_appends_distinct_lead_ids(tmp_path: Path) -> None:
    """Documented choice: APPEND, not dedupe. Two attempts produce two entries
    with distinct lead_ids, and both are integrity-verified."""

    _write_set_file(tmp_path, "sets/demo.set")
    cand = _candidate(relative_set="sets/demo.set")
    leads_path = tmp_path / "strategy_leads.json"

    r1 = promote_candidate(
        candidate_id=cand["candidate_id"],
        replay_candidates={"candidates": [cand]},
        repo_root=tmp_path,
        leads_path=leads_path,
        now=datetime(2026, 6, 24, 12, 0, 0, tzinfo=UTC),
    )
    r2 = promote_candidate(
        candidate_id=cand["candidate_id"],
        replay_candidates={"candidates": [cand]},
        repo_root=tmp_path,
        leads_path=leads_path,
        now=datetime(2026, 6, 24, 13, 0, 0, tzinfo=UTC),
    )

    assert r1.accepted and r2.accepted
    assert r1.lead_id != r2.lead_id

    document = json.loads(leads_path.read_text(encoding="utf-8"))
    assert len(document["leads"]) == 2
    for entry in document["leads"]:
        assert entry["status"] == PAPER_LANE_STATUS
        assert entry["source_sha256"] == SET_SHA256


def test_promote_atomic_write_on_io_error_leaves_file_untouched(tmp_path: Path) -> None:
    """When os.replace fails mid-write, the leads file content must not change
    and no temp file should remain in the directory."""

    _write_set_file(tmp_path, "sets/demo.set")
    leads_path = tmp_path / "strategy_leads.json"
    pre_existing = {
        "schema_version": "cas-forex-strategy-leads.v1",
        "leads": [
            {"lead_id": "pre-existing-lead", "candidate_id": "other", "status": PAPER_LANE_STATUS}
        ],
    }
    leads_path.write_text(json.dumps(pre_existing, indent=2), encoding="utf-8")
    original_bytes = leads_path.read_bytes()

    cand = _candidate(relative_set="sets/demo.set")

    def _boom(src: str, dst: str) -> None:
        raise OSError("simulated disk failure")

    with patch("cas_forex.forex_fury_promote.os.replace", side_effect=_boom):
        with pytest.raises(OSError):
            promote_candidate(
                candidate_id=cand["candidate_id"],
                replay_candidates={"candidates": [cand]},
                repo_root=tmp_path,
                leads_path=leads_path,
            )

    # File contents must be byte-identical to pre-call state.
    assert leads_path.read_bytes() == original_bytes
    # No tempfile leftovers in the leads directory.
    leftovers = [
        p for p in leads_path.parent.iterdir()
        if p.name.startswith(".strategy_leads.") and p.name.endswith(".tmp")
    ]
    assert leftovers == []


# ---------------------------------------------------------------------------
# find_promoted_lead helper coverage (supports the route's GET endpoint)
# ---------------------------------------------------------------------------


def test_find_promoted_lead_returns_latest_match(tmp_path: Path) -> None:
    _write_set_file(tmp_path, "sets/demo.set")
    cand = _candidate(relative_set="sets/demo.set")
    leads_path = tmp_path / "strategy_leads.json"

    promote_candidate(
        candidate_id=cand["candidate_id"],
        replay_candidates={"candidates": [cand]},
        repo_root=tmp_path,
        leads_path=leads_path,
        now=datetime(2026, 6, 24, 12, 0, 0, tzinfo=UTC),
    )
    r2 = promote_candidate(
        candidate_id=cand["candidate_id"],
        replay_candidates={"candidates": [cand]},
        repo_root=tmp_path,
        leads_path=leads_path,
        now=datetime(2026, 6, 24, 13, 0, 0, tzinfo=UTC),
    )

    found = find_promoted_lead(leads_path, cand["candidate_id"])
    assert found is not None
    assert found["lead_id"] == r2.lead_id
    assert find_promoted_lead(leads_path, "no-such-candidate") is None
