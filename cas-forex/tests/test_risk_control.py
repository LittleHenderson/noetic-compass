"""Tests for owner risk control — set any concurrent count / loss cap, or none."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cas_forex.execution_guard import caps_from_config, evaluate
from cas_forex.risk_control import (
    DEFAULT_OVERRIDE_PATH,
    RISK_LOOSEN_COOLDOWN_SECONDS,
    RISK_LOOSEN_CONFIRM_PHRASE,
    assess_risk_control_reset,
    assess_risk_control_update,
    build_risk_control_report,
    clear_risk_control_overrides,
    resolve_risk_control,
    set_risk_control_audit_path_for_tests,
    set_risk_control_override_store_for_tests,
    set_risk_control_overrides,
)


@pytest.fixture(autouse=True)
def _clear(tmp_path):
    set_risk_control_override_store_for_tests(tmp_path / "risk-control-overrides.json")
    clear_risk_control_overrides()
    yield
    clear_risk_control_overrides()
    set_risk_control_override_store_for_tests(DEFAULT_OVERRIDE_PATH)


def _cfg(**kw) -> SimpleNamespace:
    base = dict(
        max_open_positions=5,
        max_total_exposure_lots=0.5,
        max_weekly_drawdown_pct=5.0,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_resolve_defaults_from_config():
    rc = resolve_risk_control(_cfg())
    assert rc.max_concurrent_trades == 5
    assert rc.max_total_exposure_lots == 0.5
    assert rc.max_drawdown_pct == 5.0
    assert rc.max_loss_cap_usd is None  # no config attr -> no cap


def test_set_cap_then_unlimited():
    set_risk_control_overrides(max_concurrent_trades=50)
    assert resolve_risk_control(_cfg()).max_concurrent_trades == 50
    set_risk_control_overrides(max_concurrent_trades=None)  # unlimited
    assert resolve_risk_control(_cfg()).max_concurrent_trades is None


def test_negative_cap_rejected():
    with pytest.raises(ValueError):
        set_risk_control_overrides(max_loss_cap_usd=-1)


def test_caps_from_config_reflects_overrides():
    set_risk_control_overrides(max_concurrent_trades=42, max_total_exposure_lots=None)
    caps = caps_from_config(_cfg())
    assert caps.max_open_position_count == 42
    # Per-symbol stacking stays the AI operator's dial (default 3), held under
    # the owner's open-count cap — the owner override widens the total, not
    # blind per-symbol stacking (2026-07-03).
    assert caps.max_positions_per_symbol == 3
    assert caps.max_total_exposure_lots is None  # unlimited


def test_no_overrides_hands_the_caps_to_the_ai_dials():
    # Owner directive 2026-07-03: with no explicit owner override, the AI
    # operator's dials ARE the enforced caps (defaults 2.0 lots / 15 open /
    # 3 per symbol) — static config is only the last fallback.
    caps = caps_from_config(_cfg())
    assert caps.max_total_exposure_lots == 2.0
    assert caps.max_open_position_count == 15
    assert caps.max_positions_per_symbol == 3
    assert caps.max_drawdown_pct_from_equity_peak == 5.0
    assert caps.max_floating_loss_usd is None


def test_override_equal_to_ai_dial_is_not_mislabeled_as_effective_loosening():
    assessment = assess_risk_control_update({"max_total_exposure_lots": 2.0}, config=_cfg())
    change = assessment["changes"][0]

    assert change["owner_layer_posture"] == "loosen"
    assert change["posture"] == "unchanged"
    assert change["effective_before"] == 2.0
    assert change["effective_after"] == 2.0
    assert assessment["loosening_changes"] == []
    assert assessment["requires_journal_reason"] is False


def test_explicit_overrides_and_unlimited_survive_process_reload(tmp_path):
    store = tmp_path / "persisted-risk-overrides.json"
    set_risk_control_override_store_for_tests(store)
    set_risk_control_overrides(
        max_concurrent_trades=7,
        max_total_exposure_lots=None,
    )

    assert store.exists()
    set_risk_control_override_store_for_tests(store)  # clear memory and emulate restart

    restored = resolve_risk_control(_cfg())
    report = build_risk_control_report(_cfg())
    caps = caps_from_config(_cfg())
    assert restored.max_concurrent_trades == 7
    assert restored.max_total_exposure_lots is None
    assert report["explicit_override_keys"] == [
        "max_concurrent_trades",
        "max_total_exposure_lots",
    ]
    assert report["override_persistence"]["status"] == "PERSISTED_OWNER_OVERRIDES_ACTIVE"
    assert report["override_persistence"]["loaded_from_disk"] is True
    assert caps.max_open_position_count == 7
    assert caps.max_total_exposure_lots is None


def test_reset_removes_durable_file_and_restores_ai_precedence(tmp_path):
    store = tmp_path / "persisted-risk-overrides.json"
    set_risk_control_override_store_for_tests(store)
    set_risk_control_overrides(max_total_exposure_lots=0.25)
    assert store.exists()

    clear_risk_control_overrides()
    assert not store.exists()
    set_risk_control_override_store_for_tests(store)

    report = build_risk_control_report(_cfg())
    assert report["explicit_override_keys"] == []
    assert report["override_persistence"]["status"] == "NO_EXPLICIT_OWNER_OVERRIDES"
    assert report["effective_dispatch_caps"]["max_total_exposure_lots"] == 2.0
    assert report["effective_dispatch_caps"]["sources"]["max_total_exposure_lots"] == (
        "ai_dial_then_static_config"
    )


def test_corrupt_persistence_is_visible_and_does_not_create_explicit_caps(tmp_path):
    store = tmp_path / "corrupt-risk-overrides.json"
    store.write_text("{not-json", encoding="utf-8")
    set_risk_control_override_store_for_tests(store)

    report = build_risk_control_report(_cfg())

    assert report["explicit_override_keys"] == []
    assert report["override_persistence"]["status"] == "PERSISTENCE_LOAD_ERROR"
    assert "JSONDecodeError" in report["override_persistence"]["load_error"]


def test_failed_persistence_write_does_not_activate_new_override(monkeypatch):
    import cas_forex.risk_control as risk_control_module

    before = resolve_risk_control(_cfg()).max_total_exposure_lots
    monkeypatch.setattr(
        risk_control_module,
        "_save_overrides_snapshot",
        lambda _overrides: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    with pytest.raises(OSError, match="disk unavailable"):
        set_risk_control_overrides(max_total_exposure_lots=9.0)

    assert resolve_risk_control(_cfg()).max_total_exposure_lots == before


def test_unlimited_lets_oversized_order_pass_the_gate():
    # 5 lots on an empty book breaches the AI dial's default 2.0-lot cap...
    blocked = evaluate({"symbol": "EUR/USD", "direction": "BUY", "lots": 5.0}, config=_cfg())
    assert not blocked.accepted
    assert "max_total_exposure_lots" in blocked.blocking_caps

    # ...but with the owner removing the exposure cap, it passes.
    set_risk_control_overrides(max_total_exposure_lots=None)
    allowed = evaluate({"symbol": "EUR/USD", "direction": "BUY", "lots": 5.0}, config=_cfg())
    assert allowed.accepted


def test_higher_concurrent_cap_allows_more_positions():
    # Default cap is 5 open positions; raising it is reflected immediately.
    set_risk_control_overrides(max_concurrent_trades=100)
    caps = caps_from_config(_cfg())
    assert caps.max_open_position_count == 100


def test_assessment_marks_live_armed_loosening_for_confirmation(tmp_path):
    from cas_forex import live_enable_control

    live_enable_control.set_live_enable_override_store_for_tests(tmp_path / "live-enable.json")
    try:
        live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
        set_risk_control_overrides(max_total_exposure_lots=0.5)
        assessment = assess_risk_control_update({"max_total_exposure_lots": None}, config=_cfg())
        assert assessment["requires_confirmation"] is True
        assert assessment["requires_journal_reason"] is True
        assert assessment["journal"]["satisfied"] is False
        assert assessment["confirm_phrase"] == RISK_LOOSEN_CONFIRM_PHRASE
        assert assessment["loosening_changes"][0]["key"] == "max_total_exposure_lots"
    finally:
        live_enable_control.clear_live_enable_overrides()
        live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)


def test_assessment_allows_tightening_without_confirmation(tmp_path):
    from cas_forex import live_enable_control

    live_enable_control.set_live_enable_override_store_for_tests(tmp_path / "live-enable.json")
    try:
        live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
        set_risk_control_overrides(max_total_exposure_lots=2.0)
        assessment = assess_risk_control_update({"max_total_exposure_lots": 0.5}, config=_cfg())
        assert assessment["requires_confirmation"] is False
        assert assessment["tightening_changes"][0]["key"] == "max_total_exposure_lots"
    finally:
        live_enable_control.clear_live_enable_overrides()
        live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)


def test_reset_assessment_marks_live_armed_loosening_for_confirmation(tmp_path):
    from cas_forex import live_enable_control

    live_enable_control.set_live_enable_override_store_for_tests(tmp_path / "live-enable.json")
    try:
        live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
        set_risk_control_overrides(max_total_exposure_lots=0.25)
        assessment = assess_risk_control_reset(config=_cfg())
        assert assessment["report_kind"] == "cas_forex_risk_control_reset_assessment"
        assert assessment["requires_confirmation"] is True
        assert assessment["requires_journal_reason"] is True
        assert assessment["journal"]["satisfied"] is False
        assert assessment["confirm_phrase"] == RISK_LOOSEN_CONFIRM_PHRASE
        assert assessment["loosening_changes"][0]["key"] == "max_total_exposure_lots"
        assert assessment["loosening_changes"][0]["after"] == 0.5
    finally:
        live_enable_control.clear_live_enable_overrides()
        live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)


def test_reset_assessment_uses_effective_dispatch_posture(tmp_path):
    from cas_forex import live_enable_control

    live_enable_control.set_live_enable_override_store_for_tests(tmp_path / "live-enable.json")
    try:
        live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
        set_risk_control_overrides(max_total_exposure_lots=2.0)
        assessment = assess_risk_control_reset(config=_cfg())
        assert assessment["requires_confirmation"] is False
        exposure = next(
            row for row in assessment["changes"]
            if row["key"] == "max_total_exposure_lots"
        )
        assert exposure["owner_layer_posture"] == "tighten"
        assert exposure["posture"] == "unchanged"
        assert exposure["effective_before"] == 2.0
        assert exposure["effective_after"] == 2.0
        assert assessment["tightening_changes"] == []
    finally:
        live_enable_control.clear_live_enable_overrides()
        live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)


def test_recent_confirmed_loosening_creates_cooldown_for_next_loosening(tmp_path):
    from cas_forex import live_enable_control

    set_risk_control_audit_path_for_tests(tmp_path / "risk-control-audit.jsonl")
    live_enable_control.set_live_enable_override_store_for_tests(tmp_path / "live-enable.json")
    try:
        live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
        set_risk_control_overrides(max_total_exposure_lots=0.5)

        before = assess_risk_control_update({"max_total_exposure_lots": None}, config=_cfg())
        assert before["requires_cooldown_clear"] is False
        assert before["cooldown"]["active"] is False

        with pytest.raises(ValueError):
            set_risk_control_overrides(
                max_total_exposure_lots=None,
                audit_source="test.risk_loosen",
                audit_confirm_supplied=True,
                audit_assessment=before,
            )

        set_risk_control_overrides(
            max_total_exposure_lots=None,
            audit_source="test.risk_loosen",
            audit_confirm_supplied=True,
            audit_assessment=before,
            audit_journal_reason="paper exposure cap removal with rollback on drawdown",
        )

        after = assess_risk_control_update(
            {"max_concurrent_trades": None},
            config=_cfg(),
            journal_reason="temporary open-position cap test with rollback",
        )
        assert after["requires_confirmation"] is True
        assert after["requires_cooldown_clear"] is True
        assert after["cooldown"]["active"] is True
        assert after["cooldown"]["remaining_seconds"] <= RISK_LOOSEN_COOLDOWN_SECONDS
        assert after["cooldown"]["last_loosened_changes"][0]["key"] == "max_total_exposure_lots"

        tightening = assess_risk_control_update({"max_total_exposure_lots": 0.25}, config=_cfg())
        assert tightening["requires_cooldown_clear"] is False
    finally:
        live_enable_control.clear_live_enable_overrides()
        live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)
        set_risk_control_audit_path_for_tests(None)


def test_risk_control_report_surfaces_current_anti_impulse_status(tmp_path):
    from cas_forex import live_enable_control

    set_risk_control_audit_path_for_tests(tmp_path / "risk-control-audit.jsonl")
    live_enable_control.set_live_enable_override_store_for_tests(tmp_path / "live-enable.json")
    try:
        live_enable_control.set_live_enable_overrides(owner_enable_live_trading=True)
        set_risk_control_overrides(max_total_exposure_lots=0.5)
        first = assess_risk_control_update({"max_total_exposure_lots": None}, config=_cfg())
        set_risk_control_overrides(
            max_total_exposure_lots=None,
            audit_source="test.risk_control_report",
            audit_confirm_supplied=True,
            audit_assessment=first,
            audit_journal_reason="seed a live loosening cooldown for the report surface",
        )

        report = build_risk_control_report(_cfg())
        anti_impulse = report["anti_impulse_status"]

        assert anti_impulse["typed_confirmation_required_on_loosen"] is True
        assert anti_impulse["journal_required_on_loosen"] is True
        assert anti_impulse["would_block_new_loosening"] is True
        assert anti_impulse["cooldown"]["active"] is True
        assert anti_impulse["cooldown"]["remaining_seconds"] <= RISK_LOOSEN_COOLDOWN_SECONDS
    finally:
        live_enable_control.clear_live_enable_overrides()
        live_enable_control.set_live_enable_override_store_for_tests(live_enable_control.DEFAULT_OVERRIDE_PATH)
        set_risk_control_audit_path_for_tests(None)
