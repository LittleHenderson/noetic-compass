"""Owner command broker: preview → typed CONFIRM → receipt.

The invariant: nothing is applied without a matching typed confirmation, a
blocked preview never applies, and every applied change writes a receipt. Each
command runs the SAME gated function the UI uses (asserted by observing the real
state change through the authority / risk_control / owner_auth).
"""

from __future__ import annotations

import pytest

from cas_forex import live_enable_control, owner_auth, owner_command_broker, risk_control
from cas_forex.ai_control_authority import AiControlAuthority, set_authority_for_tests


@pytest.fixture(autouse=True)
def _isolated(tmp_path):
    set_authority_for_tests(AiControlAuthority(tmp_path / "authority.json"))
    owner_auth.set_auth_path_for_tests(tmp_path / "owner-auth.json")
    owner_command_broker.set_receipts_path_for_tests(tmp_path / "receipts.jsonl")
    live_enable_control.set_live_enable_override_store_for_tests(tmp_path / "live-enable.json")
    risk_control.set_risk_control_override_store_for_tests(tmp_path / "risk-control-overrides.json")
    risk_control.set_risk_control_audit_path_for_tests(tmp_path / "risk-control-audit.jsonl")
    risk_control.clear_risk_control_overrides()
    live_enable_control.clear_live_enable_overrides()
    yield
    set_authority_for_tests(None)
    owner_auth.set_auth_path_for_tests(None)
    owner_command_broker.set_receipts_path_for_tests(None)
    risk_control.set_risk_control_audit_path_for_tests(None)
    risk_control.clear_risk_control_overrides()
    risk_control.set_risk_control_override_store_for_tests(risk_control.DEFAULT_OVERRIDE_PATH)
    live_enable_control.clear_live_enable_overrides()
    live_enable_control.set_live_enable_override_store_for_tests(None)


def test_catalog_lists_the_settings_commands():
    names = {c["name"] for c in owner_command_broker.catalog()}
    assert {"set_ai_dial", "set_risk_cap", "set_lan_mode"} <= names


def test_preview_shows_current_and_proposed():
    prev = owner_command_broker.preview("set_ai_dial", {"lever": "edge_threshold", "value": 0.7})
    assert prev["ready"] is True
    assert prev["proposed"] == 0.7
    assert prev["confirm_phrase"] == "CONFIRM"
    assert prev["current"] is not None
    assert any("Posture impact" in effect for effect in prev["effects"])
    assert any("edge gate" in effect for effect in prev["effects"])
    assert prev["contract_rows"][0]["field"] == "edge_threshold"
    assert prev["binding"]["runtime_path"] == "ai_control_authority.control_surface.values.edge_threshold"


def test_loosened_ai_dial_preview_requires_journal_reason():
    prev = owner_command_broker.preview("set_ai_dial", {"lever": "max_risk_pct_per_trade", "value": 1.25})
    assert prev["ready"] is False
    assert prev["journal_required"] is True
    assert prev["journal_prompt"]
    assert any("reason must be at least" in blocker for blocker in prev["blockers"])

    ready = owner_command_broker.preview(
        "set_ai_dial",
        {
            "lever": "max_risk_pct_per_trade",
            "value": 1.25,
            "journal_reason": "paper-only widen with rollback condition and capped account impact",
        },
    )
    assert ready["ready"] is True
    assert ready["journal_required"] is True


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


def test_execute_loosened_ai_dial_requires_real_journal_reason():
    from cas_forex.ai_control_authority import get_authority

    before = get_authority().control.get("max_risk_pct_per_trade")
    blocked = owner_command_broker.execute(
        "set_ai_dial",
        {"lever": "max_risk_pct_per_trade", "value": 1.25},
        confirmation="CONFIRM",
    )
    assert blocked["ok"] is False
    assert blocked["applied"] is False
    assert blocked["reason"] == "blocked"
    assert get_authority().control.get("max_risk_pct_per_trade") == before

    applied = owner_command_broker.execute(
        "set_ai_dial",
        {
            "lever": "max_risk_pct_per_trade",
            "value": 1.25,
            "journal_reason": "paper-only widen with rollback condition and capped account impact",
        },
        confirmation="CONFIRM",
    )
    assert applied["ok"] is True
    assert applied["applied"] is True
    assert float(get_authority().control.get("max_risk_pct_per_trade")) == 1.25


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
    audit = risk_control.recent_risk_control_audit()
    assert audit[0]["source"] == "owner_command_broker.set_risk_cap"
    assert audit[0]["changes"][0]["key"] == "max_loss_cap_usd"

    # null / "unlimited" removes the cap.
    prev = owner_command_broker.preview("set_risk_cap", {"cap": "max_loss_cap_usd", "value": "unlimited"})
    assert prev["ready"] is False
    assert any("reason must be" in blocker for blocker in prev["blockers"])
    prev = owner_command_broker.preview(
        "set_risk_cap",
        {
            "cap": "max_loss_cap_usd",
            "value": "unlimited",
            "journal_reason": "paper loss-cap removal test with rollback",
        },
    )
    assert prev["ready"] is True
    assert prev["proposed"] == "UNLIMITED"
    r2 = owner_command_broker.execute(
        "set_risk_cap",
        {
            "cap": "max_loss_cap_usd",
            "value": None,
            "journal_reason": "paper loss-cap removal test with rollback",
        },
        confirmation="CONFIRM",
    )
    assert r2["ok"] is True
    assert resolve_risk_control().max_loss_cap_usd is None


def test_set_risk_cap_live_armed_loosen_uses_strong_phrase():
    from cas_forex.risk_control import RISK_LOOSEN_CONFIRM_PHRASE, resolve_risk_control

    live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
    owner_command_broker.execute("set_risk_cap", {"cap": "max_total_exposure_lots", "value": 0.5}, confirmation="CONFIRM")

    prev = owner_command_broker.preview("set_risk_cap", {"cap": "max_total_exposure_lots", "value": None})
    assert prev["ready"] is False
    assert any("reason must be" in blocker for blocker in prev["blockers"])

    prev = owner_command_broker.preview(
        "set_risk_cap",
        {
            "cap": "max_total_exposure_lots",
            "value": None,
            "journal_reason": "live exposure cap removal test with rollback",
        },
    )
    assert prev["ready"] is True
    assert prev["confirm_phrase"] == RISK_LOOSEN_CONFIRM_PHRASE

    plain = owner_command_broker.execute(
        "set_risk_cap",
        {
            "cap": "max_total_exposure_lots",
            "value": None,
            "journal_reason": "live exposure cap removal test with rollback",
        },
        confirmation="CONFIRM",
    )
    assert plain["ok"] is False and plain["applied"] is False
    assert resolve_risk_control().max_total_exposure_lots == 0.5

    strong = owner_command_broker.execute(
        "set_risk_cap",
        {
            "cap": "max_total_exposure_lots",
            "value": None,
            "journal_reason": "live exposure cap removal test with rollback",
        },
        confirmation=RISK_LOOSEN_CONFIRM_PHRASE,
    )
    assert strong["ok"] is True and strong["applied"] is True
    assert resolve_risk_control().max_total_exposure_lots is None


def test_owner_command_repeated_risk_loosening_hits_cooldown():
    from cas_forex.risk_control import RISK_LOOSEN_CONFIRM_PHRASE, resolve_risk_control

    live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
    owner_command_broker.execute("set_risk_cap", {"cap": "max_total_exposure_lots", "value": 0.5}, confirmation="CONFIRM")
    first = owner_command_broker.execute(
        "set_risk_cap",
        {
            "cap": "max_total_exposure_lots",
            "value": None,
            "journal_reason": "first live loosening cooldown seed",
        },
        confirmation=RISK_LOOSEN_CONFIRM_PHRASE,
    )
    assert first["ok"] is True

    prev = owner_command_broker.preview(
        "set_risk_cap",
        {
            "cap": "max_concurrent_trades",
            "value": None,
            "journal_reason": "second live loosening should hit cooldown",
        },
    )
    assert prev["ready"] is False
    assert any("cooldown" in blocker.lower() for blocker in prev["blockers"])

    second = owner_command_broker.execute(
        "set_risk_cap",
        {
            "cap": "max_concurrent_trades",
            "value": None,
            "journal_reason": "second live loosening should hit cooldown",
        },
        confirmation=RISK_LOOSEN_CONFIRM_PHRASE,
    )
    assert second["ok"] is False
    assert second["applied"] is False
    assert resolve_risk_control().max_concurrent_trades is not None


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


# --- arm_live_switch ---------------------------------------------------------

def test_arm_live_switch_needs_switch_specific_confirmation():
    prev = owner_command_broker.preview("arm_live_switch", {"switch": "owner_enable_live_trading", "enabled": True})
    assert prev["ready"] is True
    assert prev["confirm_phrase"] == "ARM owner_enable_live_trading"
    # A plain "CONFIRM" is NOT enough for a live switch.
    res = owner_command_broker.execute("arm_live_switch", {"switch": "owner_enable_live_trading", "enabled": True}, confirmation="CONFIRM")
    assert res["ok"] is False and res["applied"] is False
    assert res["need_confirmation"] == "ARM owner_enable_live_trading"


def test_arm_live_switch_applies_with_exact_phrase():
    res = owner_command_broker.execute(
        "arm_live_switch",
        {"switch": "personal_account_ack", "enabled": True},
        confirmation="ARM personal_account_ack",
    )
    assert res["ok"] is True and res["applied"] is True
    assert res["result"]["after"] is True
    assert live_enable_control.resolve_live_enable()["personal_account_ack"] is True


def test_arm_live_switch_unknown_switch_blocks():
    prev = owner_command_broker.preview("arm_live_switch", {"switch": "nope", "enabled": True})
    assert prev["ready"] is False


def test_disarm_real_money_turns_off_live_and_money_switches():
    live_enable_control.set_live_enable_overrides(
        live_mode=True,
        owner_enable_live_trading=True,
        live_trading_licensed=True,
        owner_enable_broker_accept=True,
        owner_enable_auto_deposit=True,
        owner_enable_bank_card_movement=True,
        owner_enable_payout_automation=True,
        personal_account_ack=True,
        payment_provider="wise",
    )
    prev = owner_command_broker.preview("disarm_real_money", {})
    assert prev["confirm_phrase"] == "DISARM REAL MONEY"
    assert prev["proposed"]["owner_enable_live_trading"] is False

    denied = owner_command_broker.execute("disarm_real_money", {}, confirmation="CONFIRM")
    assert denied["ok"] is False and denied["applied"] is False

    res = owner_command_broker.execute("disarm_real_money", {}, confirmation="DISARM REAL MONEY")
    assert res["ok"] is True and res["applied"] is True
    state = live_enable_control.resolve_live_enable()
    assert state["live_mode"] is False
    assert state["owner_enable_live_trading"] is False
    assert state["live_trading_licensed"] is False
    assert state["personal_account_ack"] is True
    auth = live_enable_control.build_authorization_report()
    assert auth["provider"]["payment_provider"] == "wise"


# --- move_money (fail-closed when the capability isn't armed) -----------------

def test_move_money_blocks_when_capability_not_armed():
    prev = owner_command_broker.preview("move_money", {"action": "withdraw", "amount_usd": 500})
    # Default: the money capability is not authorized, so this is not ready.
    assert prev["ready"] is False
    assert prev["confirm_phrase"] == "SEND $500 WITHDRAW"
    # Even with the strong phrase, an unarmed capability does not move money.
    res = owner_command_broker.execute(
        "move_money", {"action": "withdraw", "amount_usd": 500}, confirmation="SEND $500 WITHDRAW"
    )
    assert res["ok"] is False and res["applied"] is False
    assert res["reason"] == "blocked"


def test_move_money_rejects_bad_amount_and_action():
    assert owner_command_broker.preview("move_money", {"action": "withdraw", "amount_usd": 0})["ready"] is False
    assert owner_command_broker.preview("move_money", {"action": "teleport", "amount_usd": 5})["ready"] is False


# --- set_profit_target (reporting objective, never a trade quota) ------------

def test_set_profit_target_applies_daily_target():
    from cas_forex.ai_control_authority import get_authority

    prev = owner_command_broker.preview("set_profit_target", {"daily_target": 500})
    assert prev["ready"] is True
    assert any("Daily profit objective" in e for e in prev["effects"])
    assert any("never a trade quota" in e for e in prev["effects"])
    res = owner_command_broker.execute("set_profit_target", {"daily_target": 500}, confirmation="CONFIRM")
    assert res["ok"] is True and res["applied"] is True
    env = get_authority().snapshot()["owner_envelope"]
    assert float(env["daily_profit_floor_usd"]) == 500.0


def test_set_profit_target_rejects_target_above_cap():
    # Default daily cap is 3500; a 5000 target exceeds it.
    prev = owner_command_broker.preview("set_profit_target", {"daily_target": 5000})
    assert prev["ready"] is False
    assert any("cap" in b.lower() for b in prev["blockers"])


def test_set_profit_target_sets_cap_and_monthly_together():
    from cas_forex.ai_control_authority import get_authority

    res = owner_command_broker.execute(
        "set_profit_target",
        {"daily_target": 300, "daily_cap": 1500, "monthly_target": 6000},
        confirmation="CONFIRM",
    )
    assert res["ok"] is True
    env = get_authority().snapshot()["owner_envelope"]
    assert float(env["daily_profit_floor_usd"]) == 300.0
    assert float(env["daily_profit_cap_usd"]) == 1500.0
    assert float(env["monthly_profit_target_usd"]) == 6000.0


def test_set_profit_target_needs_at_least_one_field():
    assert owner_command_broker.preview("set_profit_target", {})["ready"] is False
