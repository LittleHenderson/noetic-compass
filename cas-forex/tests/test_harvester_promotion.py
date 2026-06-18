"""Tests for harvester promotion state machine."""

import hmac
import hashlib

import pytest

from cas_forex.harvester import PromotionController
from cas_forex.schemas.promotion import AnchorReceipt, PromotionState, StrategyChangeProposal


def _proposal():
    return StrategyChangeProposal(
        change_id="harvest-0001",
        change_type="gate",
        current_value=2.0,
        proposed_value=1.5,
        rationale="high lacunarity losses",
        expected_impact="would suppress losing trades",
    )


def test_no_direct_promote_without_anchor(tmp_path):
    controller = PromotionController(anchor_path=tmp_path / "anchors.jsonl")
    with pytest.raises(ValueError, match="Promotion requires ANCHORED"):
        controller.promote_next_session(_proposal(), next_session_id="session-2")


def test_paper_gate_requires_backtest_pass(tmp_path):
    controller = PromotionController(anchor_path=tmp_path / "anchors.jsonl")
    with pytest.raises(ValueError, match="BACKTEST_PASSED"):
        controller.run_paper_gate(_proposal(), {"total_trades": 5})


def test_backtest_failure_blocks_paper(tmp_path):
    controller = PromotionController(anchor_path=tmp_path / "anchors.jsonl")
    proposal = controller.run_backtest_gate(
        _proposal(),
        {"total_trades": 0, "profit_factor": 1.0, "max_drawdown_pct": 0},
    )
    assert proposal.state == PromotionState.BACKTEST_FAILED
    with pytest.raises(ValueError, match="BACKTEST_PASSED"):
        controller.run_paper_gate(proposal, {"total_trades": 5})


def test_full_promotion_flow_is_next_session_only(tmp_path):
    controller = PromotionController(
        anchor_path=tmp_path / "anchors.jsonl",
        active_session_id="session-1",
    )
    proposal = controller.run_backtest_gate(
        _proposal(),
        {"total_trades": 10, "profit_factor": 1.2, "max_drawdown_pct": 2.0},
    )
    proposal = controller.run_paper_gate(
        proposal,
        {"total_trades": 10, "profit_factor": 1.1, "max_drawdown_pct": 1.0},
    )
    signature = controller.payload_hash(proposal)
    proposal = controller.approve_change(proposal, "wakil", signature)
    proposal = controller.anchor_change(proposal)
    assert proposal.human_approval.signed_payload_hash == proposal.anchor.payload_hash
    assert proposal.anchor.worm_retained is False

    with pytest.raises(ValueError, match="future session"):
        controller.promote_next_session(proposal, "session-1")

    path = controller.promote_next_session(
        proposal,
        "session-2",
        ruleset_dir=tmp_path / "rulesets",
    )

    assert proposal.state == PromotionState.PROMOTED_NEXT_SESSION
    assert proposal.mid_session_apply_allowed is False
    assert path is not None and path.exists()


def test_forged_anchored_state_cannot_promote(tmp_path):
    controller = PromotionController(anchor_path=tmp_path / "anchors.jsonl")
    proposal = _proposal()
    proposal.state = PromotionState.ANCHORED

    with pytest.raises(ValueError, match="human approval receipt"):
        controller.promote_next_session(proposal, "session-2")


def test_missing_anchor_log_blocks_promotion(tmp_path):
    controller = PromotionController(anchor_path=tmp_path / "anchors.jsonl")
    proposal = controller.run_backtest_gate(
        _proposal(),
        {"total_trades": 10, "profit_factor": 1.2, "max_drawdown_pct": 2.0},
    )
    proposal = controller.run_paper_gate(
        proposal,
        {"total_trades": 10, "profit_factor": 1.1, "max_drawdown_pct": 1.0},
    )
    proposal = controller.approve_change(proposal, "wakil", controller.payload_hash(proposal))
    proposal = controller.anchor_change(proposal)
    controller.anchor_path.unlink()

    with pytest.raises(ValueError, match="Anchored record not found"):
        controller.promote_next_session(proposal, "session-2")


def test_anchor_payload_mismatch_blocks_promotion(tmp_path):
    controller = PromotionController(anchor_path=tmp_path / "anchors.jsonl")
    proposal = controller.run_backtest_gate(
        _proposal(),
        {"total_trades": 10, "profit_factor": 1.2, "max_drawdown_pct": 2.0},
    )
    proposal = controller.run_paper_gate(
        proposal,
        {"total_trades": 10, "profit_factor": 1.1, "max_drawdown_pct": 1.0},
    )
    proposal = controller.approve_change(proposal, "wakil", controller.payload_hash(proposal))
    proposal = controller.anchor_change(proposal)
    proposal.anchor = AnchorReceipt(
        anchor_uri=proposal.anchor.anchor_uri,
        payload_hash="bad",
        previous_anchor_hash=proposal.anchor.previous_anchor_hash,
        record_hash=proposal.anchor.record_hash,
    )

    with pytest.raises(ValueError, match="Anchor payload hash does not match"):
        controller.promote_next_session(proposal, "session-2")


def test_human_approval_rejects_bad_signature(tmp_path):
    controller = PromotionController(anchor_path=tmp_path / "anchors.jsonl")
    proposal = controller.run_backtest_gate(
        _proposal(),
        {"total_trades": 10, "profit_factor": 1.2, "max_drawdown_pct": 2.0},
    )
    proposal = controller.run_paper_gate(
        proposal,
        {"total_trades": 10, "profit_factor": 1.1, "max_drawdown_pct": 1.0},
    )

    with pytest.raises(ValueError, match="Invalid human approval signature"):
        controller.approve_change(proposal, "wakil", "bad-signature")
    assert proposal.state == PromotionState.HUMAN_REJECTED


def test_human_approval_accepts_hmac_signature(tmp_path):
    controller = PromotionController(anchor_path=tmp_path / "anchors.jsonl")
    proposal = controller.run_backtest_gate(
        _proposal(),
        {"total_trades": 10, "profit_factor": 1.2, "max_drawdown_pct": 2.0},
    )
    proposal = controller.run_paper_gate(
        proposal,
        {"total_trades": 10, "profit_factor": 1.1, "max_drawdown_pct": 1.0},
    )
    payload_hash = controller.payload_hash(proposal)
    signature = hmac.new(
        b"secret",
        payload_hash.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    controller.approve_change(proposal, "wakil", signature, secret="secret")

    assert proposal.state == PromotionState.HUMAN_APPROVED


def test_anchor_log_detects_tamper(tmp_path):
    controller = PromotionController(anchor_path=tmp_path / "anchors.jsonl")
    proposal = controller.run_backtest_gate(
        _proposal(),
        {"total_trades": 10, "profit_factor": 1.2, "max_drawdown_pct": 2.0},
    )
    proposal = controller.run_paper_gate(
        proposal,
        {"total_trades": 10, "profit_factor": 1.1, "max_drawdown_pct": 1.0},
    )
    proposal = controller.approve_change(proposal, "wakil", controller.payload_hash(proposal))
    controller.anchor_change(proposal)

    assert controller.verify_anchor_log()
    controller.anchor_path.write_text(
        controller.anchor_path.read_text(encoding="utf-8").replace(
            proposal.change_id,
            "tampered",
        ),
        encoding="utf-8",
    )
    assert not controller.verify_anchor_log()
