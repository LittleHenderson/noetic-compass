"""Tests for the AI operator brain (cas_forex/ai_operator.py).

Load-bearing invariant: the operator can ONLY move owner-fenced dials, each
clamped to owner bounds; it can NEVER reach the live-money gate, orders, or
money movement, and an unparseable / malicious model reply produces NO action.
"""

from __future__ import annotations

import json

from cas_forex import ai_operator, model_provider
from cas_forex.ai_control_authority import AiControlAuthority, set_authority_for_tests


class _StubProvider:
    def __init__(self, text, *, ok=True, provider="claude", paid=True, failover=False):
        self._text = text
        self._ok = ok
        self._provider = provider
        self._paid = paid
        self._failover = failover

    def generate(self, prompt, system=None):
        return {
            "ok": self._ok,
            "text": self._text,
            "provider": self._provider,
            "provider_label": f"{self._provider} (stub)",
            "paid": self._paid,
            "failover": self._failover,
            "switch_reason": "",
            "error": None if self._ok else "no model",
        }


def _operator(tmp_path, monkeypatch, provider):
    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    model_provider.set_model_provider_for_tests(provider)
    return ai_operator.AIOperator(actions_path=tmp_path / "actions.jsonl")


def _teardown():
    set_authority_for_tests(None)
    model_provider.set_model_provider_for_tests(None)


def test_operator_applies_a_fenced_dial(tmp_path, monkeypatch):
    decision = {
        "observations": "too few candidates in quiet markets",
        "actions": [{"type": "adjust_dial", "lever": "min_directional_confidence", "value": 0.1, "reason": "loosen"}],
        "summary": "loosen confidence",
    }
    op = _operator(tmp_path, monkeypatch, _StubProvider(json.dumps(decision)))
    try:
        tick = op.tick()
        d = tick.to_dict()
        assert d["ok"] is True
        assert d["provider"] == "claude"
        assert len(d["actions_applied"]) == 1
        assert d["actions_applied"][0]["lever"] == "min_directional_confidence"
        from cas_forex.ai_control_authority import get_authority

        assert abs(float(get_authority().control.get("min_directional_confidence")) - 0.1) < 1e-9
    finally:
        _teardown()


def test_operator_cannot_touch_non_dial_levers(tmp_path, monkeypatch):
    decision = {
        "actions": [
            {"type": "adjust_dial", "lever": "live_mode", "value": True, "reason": "go live"},
            {"type": "adjust_dial", "lever": "owner_enable_live_trading", "value": True, "reason": "nope"},
            {"type": "wire_money", "amount": 5000, "reason": "withdraw"},
        ],
        "summary": "attempted forbidden actions",
    }
    op = _operator(tmp_path, monkeypatch, _StubProvider(json.dumps(decision)))
    try:
        tick = op.tick()
        d = tick.to_dict()
        assert d["actions_applied"] == []
        assert len(d["actions_skipped"]) == 3
        whys = " ".join(s["why"] for s in d["actions_skipped"])
        assert "not an owner-fenced dial" in whys
        assert "unsupported action type" in whys
    finally:
        _teardown()


def test_operator_clamps_to_owner_bounds(tmp_path, monkeypatch):
    decision = {
        "actions": [{"type": "adjust_dial", "lever": "edge_threshold", "value": 0.99, "reason": "max out"}],
        "summary": "clamp test",
    }
    op = _operator(tmp_path, monkeypatch, _StubProvider(json.dumps(decision)))
    try:
        tick = op.tick()
        applied = tick.to_dict()["actions_applied"][0]
        assert applied["clamped"] is True
        assert float(applied["new_value"]) <= 0.95  # owner max
    finally:
        _teardown()


def test_unparseable_reply_makes_no_change(tmp_path, monkeypatch):
    op = _operator(tmp_path, monkeypatch, _StubProvider("I think you should sell everything!!!"))
    try:
        tick = op.tick()
        d = tick.to_dict()
        assert d["ok"] is False
        assert d["actions_applied"] == []
        assert "parseable" in (d["error"] or "")
    finally:
        _teardown()


def test_no_model_available_is_safe(tmp_path, monkeypatch):
    op = _operator(tmp_path, monkeypatch, _StubProvider("", ok=False))
    try:
        tick = op.tick()
        d = tick.to_dict()
        assert d["ok"] is False
        assert d["actions_applied"] == []
        assert "running" in d["summary"].lower()  # "trading loop keeps running"
    finally:
        _teardown()


def test_empty_actions_list_is_a_valid_hold(tmp_path, monkeypatch):
    decision = {"observations": "all healthy", "actions": [], "summary": "no change"}
    op = _operator(tmp_path, monkeypatch, _StubProvider(json.dumps(decision)))
    try:
        tick = op.tick()
        d = tick.to_dict()
        assert d["ok"] is True
        assert d["actions_applied"] == []
        assert d["summary"] == "no change"
    finally:
        _teardown()


def test_recent_actions_are_logged_and_readable(tmp_path, monkeypatch):
    decision = {"actions": [{"type": "adjust_dial", "lever": "max_concurrent_trades", "value": 10, "reason": "cap"}], "summary": "cap"}
    op = _operator(tmp_path, monkeypatch, _StubProvider(json.dumps(decision)))
    try:
        op.tick()
        recent = op.recent_actions()
        assert len(recent) == 1
        assert recent[0]["summary"] == "cap"
    finally:
        _teardown()


def test_tool_manifest_lists_what_it_cannot_do(tmp_path):
    manifest = ai_operator.TOOL_MANIFEST
    forbidden = " ".join(manifest["you_cannot"]).lower()
    assert "move money" in forbidden
    assert "live trading" in forbidden
    assert "edge token" in forbidden


class _CapturingProvider(_StubProvider):
    """Stub that also records every prompt it was asked to answer."""

    def __init__(self, text, **kw):
        super().__init__(text, **kw)
        self.prompts = []

    def generate(self, prompt, system=None):
        self.prompts.append(prompt)
        return super().generate(prompt, system)


def test_next_tick_sees_its_own_prior_dial_changes(tmp_path, monkeypatch):
    """Self-continuity (2026-07-03): a tick re-added a market the prior tick
    had just cut, calling it 'previously unused'. The next tick's prompt must
    carry the operator's own recent applied changes, placed at the HEAD of the
    context so prompt truncation can never drop them."""
    decision = {
        "observations": "cut the chronic loser",
        "actions": [{"type": "adjust_dial", "lever": "max_positions_per_symbol", "value": 2, "reason": "stop blind stacking"}],
        "summary": "tightened per-symbol stacking",
    }
    provider = _CapturingProvider(json.dumps(decision))
    op = _operator(tmp_path, monkeypatch, provider)
    try:
        first = op.tick()
        assert first.ok is True
        # First tick: no prior applied actions -> no self-history block.
        assert "your_recent_dial_changes" not in provider.prompts[0]

        second = op.tick()
        assert second.ok is True
        follow_up = provider.prompts[1]
        assert "your_recent_dial_changes" in follow_up
        assert "max_positions_per_symbol" in follow_up.split("inherited_lessons")[0]
        # Head placement: the self-history must appear before the (truncatable)
        # tail of the context dump.
        assert follow_up.index("your_recent_dial_changes") < len(follow_up) // 2
    finally:
        _teardown()
