"""Unit tests for the pure strategy-development action primitives.

These tests cover the can_*/next_*/previous_* predicates plus the
``apply_action`` I/O wrapper. We exercise the wrapper against tmp_path so
no real evidence_runs/ files are touched.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cas_forex.strategy_dev_actions import (
    ALL_STAGES,
    PROMOTABLE_STAGES,
    STAGE_ORDER,
    StrategyActionResult,
    apply_action,
    can_demote,
    can_promote,
    next_stage_for_promotion,
    previous_stage_for_demotion,
)


def _make_queue(strategies: list[dict]) -> dict:
    return {"items": list(strategies)}


def _write_queue(tmp_path: Path, queue: dict) -> Path:
    path = tmp_path / "queue.json"
    path.write_text(json.dumps(queue), encoding="utf-8")
    return path


FIXED_NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Pure-predicate tests
# ---------------------------------------------------------------------------


def test_can_promote_yes_for_each_promotable_stage():
    for stage in PROMOTABLE_STAGES:
        ok, reason = can_promote({"stage": stage})
        assert ok, f"{stage} should be promotable: {reason}"
        assert reason == ""


def test_can_promote_no_for_promoted():
    ok, reason = can_promote({"stage": "PROMOTED"})
    assert not ok
    assert "already promoted" in reason


def test_can_promote_no_for_terminal_stages():
    for stage in ("REJECTED", "ARCHIVED"):
        ok, reason = can_promote({"stage": stage})
        assert not ok
        assert stage in reason


def test_can_demote_no_for_research():
    ok, reason = can_demote({"stage": "RESEARCH"})
    assert not ok
    assert "RESEARCH" in reason


def test_can_demote_yes_for_higher_stages():
    for stage in ("REPLAY", "PAPER", "REVIEW", "PROMOTED"):
        ok, reason = can_demote({"stage": stage})
        assert ok, f"{stage} should be demotable: {reason}"


def test_next_stage_for_promotion_walks_chain():
    assert next_stage_for_promotion("RESEARCH") == "REPLAY"
    assert next_stage_for_promotion("REPLAY") == "PAPER"
    assert next_stage_for_promotion("PAPER") == "REVIEW"
    assert next_stage_for_promotion("REVIEW") == "PROMOTED"
    assert next_stage_for_promotion("PROMOTED") is None
    assert next_stage_for_promotion("REJECTED") is None


def test_previous_stage_for_demotion_walks_chain():
    assert previous_stage_for_demotion("PROMOTED") == "REVIEW"
    assert previous_stage_for_demotion("REVIEW") == "PAPER"
    assert previous_stage_for_demotion("PAPER") == "REPLAY"
    assert previous_stage_for_demotion("REPLAY") == "RESEARCH"
    assert previous_stage_for_demotion("RESEARCH") is None


def test_stage_order_includes_all_stages():
    for stage in ALL_STAGES:
        assert stage in STAGE_ORDER


# ---------------------------------------------------------------------------
# apply_action I/O wrapper tests
# ---------------------------------------------------------------------------


def test_apply_action_missing_strategy_id_rejected(tmp_path: Path):
    queue = _make_queue([{"strategy_id": "abc", "stage": "RESEARCH"}])
    path = _write_queue(tmp_path, queue)
    result = apply_action(
        strategy_id="not-here",
        action="PROMOTE",
        queue=queue,
        queue_path=path,
        now=FIXED_NOW,
    )
    assert isinstance(result, StrategyActionResult)
    assert not result.accepted
    assert "not found" in (result.rejection_reason or "")


def test_apply_action_promote_walks_one_stage(tmp_path: Path):
    queue = _make_queue([{"strategy_id": "abc", "stage": "RESEARCH"}])
    path = _write_queue(tmp_path, queue)
    result = apply_action(
        strategy_id="abc",
        action="PROMOTE",
        queue=queue,
        queue_path=path,
        now=FIXED_NOW,
    )
    assert result.accepted
    assert result.previous_stage == "RESEARCH"
    assert result.next_stage == "REPLAY"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["items"][0]["stage"] == "REPLAY"


def test_apply_action_demote_walks_one_stage_back(tmp_path: Path):
    queue = _make_queue([{"strategy_id": "abc", "stage": "PAPER"}])
    path = _write_queue(tmp_path, queue)
    result = apply_action(
        strategy_id="abc",
        action="DEMOTE",
        queue=queue,
        queue_path=path,
        now=FIXED_NOW,
    )
    assert result.accepted
    assert result.previous_stage == "PAPER"
    assert result.next_stage == "REPLAY"


def test_apply_action_promote_at_promoted_terminal_rejected(tmp_path: Path):
    queue = _make_queue([{"strategy_id": "abc", "stage": "PROMOTED"}])
    path = _write_queue(tmp_path, queue)
    result = apply_action(
        strategy_id="abc",
        action="PROMOTE",
        queue=queue,
        queue_path=path,
        now=FIXED_NOW,
    )
    assert not result.accepted
    assert "already promoted" in (result.rejection_reason or "")


def test_apply_action_demote_at_research_rejected(tmp_path: Path):
    queue = _make_queue([{"strategy_id": "abc", "stage": "RESEARCH"}])
    path = _write_queue(tmp_path, queue)
    result = apply_action(
        strategy_id="abc",
        action="DEMOTE",
        queue=queue,
        queue_path=path,
        now=FIXED_NOW,
    )
    assert not result.accepted
    assert "RESEARCH" in (result.rejection_reason or "")


def test_apply_action_reject_sets_terminal(tmp_path: Path):
    queue = _make_queue([{"strategy_id": "abc", "stage": "REVIEW"}])
    path = _write_queue(tmp_path, queue)
    result = apply_action(
        strategy_id="abc",
        action="REJECT",
        queue=queue,
        queue_path=path,
        now=FIXED_NOW,
    )
    assert result.accepted
    assert result.next_stage == "REJECTED"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["items"][0]["stage"] == "REJECTED"


def test_apply_action_archive_sets_terminal(tmp_path: Path):
    queue = _make_queue([{"strategy_id": "abc", "stage": "PAPER"}])
    path = _write_queue(tmp_path, queue)
    result = apply_action(
        strategy_id="abc",
        action="ARCHIVE",
        queue=queue,
        queue_path=path,
        note="not interesting",
        now=FIXED_NOW,
    )
    assert result.accepted
    assert result.next_stage == "ARCHIVED"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["items"][0]["stage"] == "ARCHIVED"


def test_apply_action_review_does_not_change_stage(tmp_path: Path):
    queue = _make_queue([{"strategy_id": "abc", "stage": "PAPER"}])
    path = _write_queue(tmp_path, queue)
    result = apply_action(
        strategy_id="abc",
        action="REVIEW",
        queue=queue,
        queue_path=path,
        note="looks fine",
        now=FIXED_NOW,
    )
    assert result.accepted
    assert result.previous_stage == "PAPER"
    assert result.next_stage == "PAPER"
    written = json.loads(path.read_text(encoding="utf-8"))
    strat = written["items"][0]
    assert strat["stage"] == "PAPER"
    assert strat["last_reviewed_at_iso"] == FIXED_NOW.isoformat()


def test_apply_action_history_appended_not_replaced(tmp_path: Path):
    queue = _make_queue([
        {
            "strategy_id": "abc",
            "stage": "RESEARCH",
            "history": [{"action": "CREATED", "from_stage": None, "to_stage": "RESEARCH"}],
        }
    ])
    path = _write_queue(tmp_path, queue)
    result = apply_action(
        strategy_id="abc",
        action="PROMOTE",
        queue=queue,
        queue_path=path,
        note="ready for replay",
        now=FIXED_NOW,
    )
    assert result.accepted
    written = json.loads(path.read_text(encoding="utf-8"))
    history = written["items"][0]["history"]
    assert len(history) == 2
    assert history[0]["action"] == "CREATED"
    assert history[1]["action"] == "PROMOTE"
    assert history[1]["from_stage"] == "RESEARCH"
    assert history[1]["to_stage"] == "REPLAY"
    assert history[1]["note"] == "ready for replay"
    assert history[1]["actioned_at_iso"] == FIXED_NOW.isoformat()


def test_apply_action_unknown_action_rejected(tmp_path: Path):
    queue = _make_queue([{"strategy_id": "abc", "stage": "RESEARCH"}])
    path = _write_queue(tmp_path, queue)
    result = apply_action(
        strategy_id="abc",
        action="BANANA",
        queue=queue,
        queue_path=path,
        now=FIXED_NOW,
    )
    assert not result.accepted
    assert "unknown action" in (result.rejection_reason or "").lower()


def test_apply_action_atomic_write_failure_leaves_file_untouched(tmp_path: Path, monkeypatch):
    """If the atomic rewrite step raises, the original queue file must
    remain byte-identical and apply_action must propagate the exception
    (no silent partial state)."""
    queue = _make_queue([{"strategy_id": "abc", "stage": "RESEARCH"}])
    path = _write_queue(tmp_path, queue)
    original_bytes = path.read_bytes()

    import cas_forex.strategy_dev_actions as mod

    def boom(*args, **kwargs):
        raise IOError("simulated disk failure")

    monkeypatch.setattr(mod, "_atomic_write_json", boom)
    with pytest.raises(IOError):
        apply_action(
            strategy_id="abc",
            action="PROMOTE",
            queue=queue,
            queue_path=path,
            now=FIXED_NOW,
        )
    assert path.read_bytes() == original_bytes


def test_apply_action_work_items_key_also_supported(tmp_path: Path):
    """Real strategy_dev_queue reports use ``work_items``/``item_id``;
    apply_action must handle that shape too."""
    queue = {
        "work_items": [
            {"item_id": "xyz", "stage": "REPLAY"},
        ]
    }
    path = _write_queue(tmp_path, queue)
    result = apply_action(
        strategy_id="xyz",
        action="PROMOTE",
        queue=queue,
        queue_path=path,
        now=FIXED_NOW,
    )
    assert result.accepted
    assert result.next_stage == "PAPER"
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["work_items"][0]["stage"] == "PAPER"


def test_apply_action_input_queue_not_mutated_in_place(tmp_path: Path):
    """Caller's parsed queue dict must not be mutated; only the file on
    disk is rewritten."""
    queue = _make_queue([{"strategy_id": "abc", "stage": "RESEARCH"}])
    path = _write_queue(tmp_path, queue)
    snapshot_before = json.dumps(queue, sort_keys=True)
    apply_action(
        strategy_id="abc",
        action="PROMOTE",
        queue=queue,
        queue_path=path,
        now=FIXED_NOW,
    )
    snapshot_after = json.dumps(queue, sort_keys=True)
    assert snapshot_before == snapshot_after
