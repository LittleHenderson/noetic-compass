"""Owner command broker: preview → typed CONFIRM → receipt.

The invariant: nothing is applied without a matching typed confirmation, a
blocked preview never applies, and every applied change writes a receipt. Each
command runs the SAME gated function the UI uses (asserted by observing the real
state change through the authority / risk_control / owner_auth).
"""

from __future__ import annotations

import pytest

from cas_forex import owner_auth, owner_command_broker, risk_control
from cas_forex.ai_control_authority import AiControlAuthority, set_authority_for_tests


@pytest.fixture(autouse=True)
def _isolated(tmp_path):
    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    owner_auth.set_auth_path_for_tests(tmp_path / "owner-auth.json")
    owner_command_broker.set_receipts_path_for_tests(tmp_path / "receipts.jsonl")
    risk_control.clear_risk_control_overrides()
    yield
    set_authority_for_tests(None)
    owner_auth.set_auth_path_for_tests(None)
    owner_command_broker.set_receipts_path_for_tests(None)
    risk_control.clear_risk_control_overrides()


def test_catalog_lists_the_settings_commands():
    names = {c["name"] for c in owner_command_broker.catalog()}
    assert {"set_ai_dial", "set_risk_cap", "set_lan_mode"} <= names


def test_preview_shows_current_and_proposed():
    prev = owner_command_broker.preview("set_ai_dial", {"lever": "edge_threshold", "value": 0.7})
    assert prev["ready"] is True
    assert prev["proposed"] == 0.7
    assert prev["confirm_phrase"] == "CONFIRM"
    assert prev["current"] is not None


def test_execute_requires_confirmation():
    from cas_forex.ai_control_authority import get_authority

    before = get_authority().control.get("edge_threshold")
    res = owner_command_broker.execute("set_ai_dial", {"lever": "edge_threshold", "value": 0.7}, confirmation="")
    assert res["ok"] is False
    assert res["applied"] is False
    assert res["need_confirmation"] == "CONFIRM"
    # Nothing changed without the typed CONFIRM.
    assert get_authority().control.get("edge_threshold") == before


def test_execute_with_confirm_applies_and_receipts():
    from cas_forex.ai_control_authority import get_authority

    res = owner_command_broker.execute("set_ai_dial", {"lever": "edge_threshold", "value": 0.72}, confirmation="CONFIRM")
    assert res["ok"] is True and res["applied"] is True
    assert abs(float(get_authority().control.get("edge_threshold")) - 0.72) < 1e-9
    assert res["receipt"]["command"] == "set_ai_dial"
    receipts = owner_command_broker.recent_receipts()
    assert receipts and receipts[0]["command"] == "set_ai_dial"


def test_confirmation_is_case_insensitive_and_trimmed():
    res = owner_command_broker.execute("set_lan_mode", {"enabled": True}, confirmation="  confirm ")
    assert res["ok"] is True
    assert owner_auth.lan_mode_enabled() is True


def test_unknown_dial_blocks_and_never_applies():
    prev = owner_command_broker.preview("set_ai_dial", {"lever": "nonsense", "value": 1})
    assert prev["ready"] is False
    assert prev["blockers"]
    res = owner_command_broker.execute("set_ai_dial", {"lever": "nonsense", "value": 1}, confirmation="CONFIRM")
    assert res["ok"] is False and res["applied"] is False
    assert res["reason"] == "blocked"


def test_set_risk_cap_number_and_unlimited():
    from cas_forex.risk_control import resolve_risk_control

    r1 = owner_command_broker.execute("set_risk_cap", {"cap": "max_loss_cap_usd", "value": 250}, confirmation="CONFIRM")
    assert r1["ok"] is True
    assert resolve_risk_control().max_loss_cap_usd == 250.0

    # null / "unlimited" removes the cap.
    prev = owner_command_broker.preview("set_risk_cap", {"cap": "max_loss_cap_usd", "value": "unlimited"})
    assert prev["proposed"] == "UNLIMITED"
    r2 = owner_command_broker.execute("set_risk_cap", {"cap": "max_loss_cap_usd", "value": None}, confirmation="CONFIRM")
    assert r2["ok"] is True
    assert resolve_risk_control().max_loss_cap_usd is None


def test_set_risk_cap_rejects_negative():
    prev = owner_command_broker.preview("set_risk_cap", {"cap": "max_loss_cap_usd", "value": -5})
    assert prev["ready"] is False


def test_set_lan_mode_toggles_and_receipts():
    res = owner_command_broker.execute("set_lan_mode", {"enabled": True}, confirmation="CONFIRM")
    assert res["ok"] is True
    assert owner_auth.lan_mode_enabled() is True
    assert res["result"]["before"] is False and res["result"]["after"] is True


def test_unknown_command_is_refused():
    assert owner_command_broker.preview("nope", {})["ready"] is False
    res = owner_command_broker.execute("nope", {}, confirmation="CONFIRM")
    assert res["ok"] is False and res["applied"] is False
