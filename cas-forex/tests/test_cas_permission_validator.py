"""Tests for the CAS permission/risk validator (Stage 3 of LLM bot runtime).

The validator is pure: tests construct gate state in-memory and check the
ValidationResult. HTTP fetch is tested separately with an injected transport.
"""

from __future__ import annotations

from typing import Any, Mapping

import pytest

from cas_forex.cas_forex_bot import BotCapability
from cas_forex.cas_permission_validator import (
    DECISION_DEGRADED,
    DECISION_PASS,
    DECISION_REJECT,
    REQUIRED_GATES_BY_DANGER,
    fetch_runtime_gates,
    validate_capability,
    validate_by_key,
)


SAFE_CAP = BotCapability(
    key="s1",
    group="status",
    label="status check",
    description="reads health",
    danger_level="safe",
)

CAUTION_CAP = BotCapability(
    key="mo",
    group="mt5",
    label="MT5 demo order",
    description="sends a demo order",
    danger_level="caution",
    requires_confirm=True,
)

DANGEROUS_CAP = BotCapability(
    key="LIVE",
    group="mt5",
    label="LIVE order",
    description="would send a real-money order",
    danger_level="dangerous",
    requires_confirm=True,
)


def gates_state(*, all_open: bool = False, open_gates: tuple[str, ...] = ()) -> Mapping[str, Any]:
    """Build a `runtime_gates` response shape with selected gates open."""
    decisions: dict[str, Any] = {}
    for gate in REQUIRED_GATES_BY_DANGER["dangerous"]:
        authorized = all_open or (gate in open_gates)
        decisions[gate] = {
            "capability": gate,
            "authorized": authorized,
            "status": "AUTHORIZED" if authorized else "CURRENTLY NOT LICENSED",
            "missing_requirements": [] if authorized else [f"unlock {gate}"],
            "satisfied_requirements": [f"{gate} prereqs met"] if authorized else [],
            "next_action": "" if authorized else f"unlock {gate} via owner-control",
        }
    return {
        "report_kind": "runtime_gates",
        "decisions": decisions,
        "all_real_money_authorized": all_open,
    }


# ---------------------------------------------------------------------------
# Happy-path: safe and caution always pass when gates state is known
# ---------------------------------------------------------------------------


def test_safe_capability_always_passes():
    result = validate_capability(SAFE_CAP, gates_state())
    assert result.decision == DECISION_PASS
    assert result.blocking_gates == ()


def test_caution_capability_passes_even_when_all_money_gates_closed():
    # Caution (e.g. MT5 demo order) is not real-money — demo lane is allowed.
    result = validate_capability(CAUTION_CAP, gates_state())
    assert result.decision == DECISION_PASS
    assert result.blocking_gates == ()
    assert result.requires_confirm is True
    assert any("Stage 5" in note for note in result.advisory_notes)


def test_caution_capability_marks_broker_touching_advisory():
    result = validate_capability(CAUTION_CAP, gates_state())
    assert result.broker_touching is True
    assert any("demo lane" in note for note in result.advisory_notes)


# ---------------------------------------------------------------------------
# Dangerous capabilities require ALL real-money gates open
# ---------------------------------------------------------------------------


def test_dangerous_capability_rejected_when_all_gates_closed():
    result = validate_capability(DANGEROUS_CAP, gates_state())
    assert result.decision == DECISION_REJECT
    blocked = {b.gate for b in result.blocking_gates}
    assert blocked == set(REQUIRED_GATES_BY_DANGER["dangerous"])
    assert "[cas-validator:REJECTED]" in result.structured_message
    assert "live_trading" in result.structured_message


def test_dangerous_capability_rejected_when_one_gate_closed():
    open_gates = tuple(g for g in REQUIRED_GATES_BY_DANGER["dangerous"] if g != "broker_accept")
    result = validate_capability(DANGEROUS_CAP, gates_state(open_gates=open_gates))
    assert result.decision == DECISION_REJECT
    blocked = {b.gate for b in result.blocking_gates}
    assert blocked == {"broker_accept"}


def test_dangerous_capability_passes_when_all_gates_open():
    result = validate_capability(DANGEROUS_CAP, gates_state(all_open=True))
    assert result.decision == DECISION_PASS
    assert result.blocking_gates == ()


def test_dangerous_rejection_carries_next_action_hint():
    result = validate_capability(DANGEROUS_CAP, gates_state())
    blocks = {b.gate: b for b in result.blocking_gates}
    assert "unlock live_trading via owner-control" in blocks["live_trading"].next_action


# ---------------------------------------------------------------------------
# Degraded path — runtime gates unavailable
# ---------------------------------------------------------------------------


def test_degraded_when_gates_unavailable_safe_passes():
    result = validate_capability(SAFE_CAP, None)
    assert result.decision == DECISION_DEGRADED
    assert "[cas-validator:DEGRADED]" in result.structured_message


def test_degraded_when_gates_unavailable_caution_passes():
    result = validate_capability(CAUTION_CAP, None)
    assert result.decision == DECISION_DEGRADED


def test_degraded_when_gates_unavailable_dangerous_rejected():
    result = validate_capability(DANGEROUS_CAP, None)
    assert result.decision == DECISION_REJECT
    assert any("unavailable" in note for note in result.advisory_notes)
    assert "[cas-validator:REJECTED]" in result.structured_message


# ---------------------------------------------------------------------------
# Authority boundary advisory
# ---------------------------------------------------------------------------


def test_authority_boundary_advisory_attached_for_dangerous():
    open_state = gates_state(all_open=True)
    boundary = {"can_place_live_orders": False}
    result = validate_capability(DANGEROUS_CAP, open_state, authority_boundary=boundary)
    assert any("can_place_live_orders" in note for note in result.advisory_notes)


def test_authority_boundary_no_advisory_when_can_place_live_orders():
    open_state = gates_state(all_open=True)
    boundary = {"can_place_live_orders": True}
    result = validate_capability(DANGEROUS_CAP, open_state, authority_boundary=boundary)
    assert not any("can_place_live_orders" in note for note in result.advisory_notes)


# ---------------------------------------------------------------------------
# Unknown danger level treated conservatively
# ---------------------------------------------------------------------------


def test_unknown_danger_level_treated_as_caution():
    weird_cap = BotCapability(
        key="weird",
        group="system",
        label="weird",
        description="x",
        danger_level="apocalyptic",
    )
    result = validate_capability(weird_cap, gates_state())
    assert result.decision == DECISION_PASS  # treated as caution, no gates required


# ---------------------------------------------------------------------------
# Structured message shape (LLM feeds on this)
# ---------------------------------------------------------------------------


def test_pass_message_includes_capability_key_and_label():
    result = validate_capability(SAFE_CAP, gates_state())
    assert "`s1`" in result.structured_message
    assert "status check" in result.structured_message
    assert "[cas-validator:ALLOWED]" in result.structured_message


def test_reject_message_lists_each_blocking_gate():
    result = validate_capability(DANGEROUS_CAP, gates_state())
    for gate in REQUIRED_GATES_BY_DANGER["dangerous"]:
        assert f"`{gate}`" in result.structured_message


# ---------------------------------------------------------------------------
# HTTP fetch (transport injected)
# ---------------------------------------------------------------------------


def test_fetch_runtime_gates_via_transport_returns_body():
    sample = gates_state(all_open=True)

    def transport(url: str, *, timeout: int) -> dict[str, Any]:
        assert url.endswith("/api/forex/settings/runtime-gates")
        assert timeout == 5
        return dict(sample)

    result = fetch_runtime_gates("http://api.example", timeout=5, transport=transport)
    assert result is not None
    assert result["all_real_money_authorized"] is True


def test_fetch_runtime_gates_returns_none_when_transport_raises():
    def transport(url: str, *, timeout: int) -> dict[str, Any]:
        raise OSError("network down")

    result = fetch_runtime_gates("http://api.example", transport=transport)
    assert result is None


# ---------------------------------------------------------------------------
# validate_by_key convenience (uses live URL — we stub via monkeypatch)
# ---------------------------------------------------------------------------


def test_validate_by_key_unknown_capability_rejects(monkeypatch):
    result = validate_by_key("does-not-exist", api_base="http://x", capabilities=[SAFE_CAP])
    assert result.decision == DECISION_REJECT
    assert "not found" in result.structured_message


def test_validate_by_key_passes_through_fetch(monkeypatch):
    from cas_forex import cas_permission_validator as mod

    monkeypatch.setattr(mod, "fetch_runtime_gates", lambda api_base: gates_state())
    result = validate_by_key("s1", api_base="http://x", capabilities=[SAFE_CAP])
    assert result.decision == DECISION_PASS
