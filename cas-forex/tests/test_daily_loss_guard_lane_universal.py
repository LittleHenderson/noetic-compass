"""The daily-loss block must run on the PAPER/DEMO dispatch path. Pinned.

Born from the July post-mortem: the demo account lost $53,606 in a single day
(2026-07-02) because no daily loss ceiling executed on the paper lane - the
guard was designed mid-period but not enforced, and auto_halt gates live
authorization only. This suite makes the enforcement itself load-bearing: if
anyone ever reroutes demo dispatch around require_daily_realized_loss_ready,
or softens a cap-breach to a warning, these tests fail.

No behavior is changed here - these tests pin behavior that exists today
(execution_guard.guarded_place_order -> require_daily_realized_loss_ready for
every dispatch, demo included).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cas_forex import execution_guard
from cas_forex.execution_guard import ExecutionBlocked, require_daily_realized_loss_ready


class _DemoBridge:
    """A bridge shaped like the demo/paper lane: not a real-order bridge."""

    def __init__(self):
        self.calls = []

    def will_execute_real_order(self) -> bool:
        return False

    def is_demo_account(self) -> bool:
        return True

    def place_order(self, order):
        self.calls.append(order)
        return SimpleNamespace(accepted=True, order=order)


def _blocking_report(**over):
    report = {
        "report_kind": "cas_forex_daily_realized_loss_guard",
        "status": "DAILY_REALIZED_LOSS_CAP_REACHED",
        "block_new_exposure": True,
        "cap_usd": 50.0,
        "realized_today_usd": -53606.07,  # the 2026-07-02 number
        "remaining_loss_budget_usd": 0.0,
        "cap_source": "test_fixture",
        "blocking_cap": "daily_loss_cap_usd",
        "position_management_allowed": True,
        "risk_reducing_close_allowed": True,
        "take_profit_and_stop_management_allowed": True,
        "account_growth_reconciliation": {"period_current": True},
        "detail": "Test fixture: cap breached at July-2 scale.",
    }
    report.update(over)
    return report


def test_cap_breach_blocks_new_exposure_on_the_demo_lane(monkeypatch):
    """With the cap breached, require_daily_realized_loss_ready must RAISE for
    a demo bridge - not warn, not return a report and continue."""
    import cas_forex.daily_loss_guard as dlg

    monkeypatch.setattr(
        dlg, "evaluate_bridge_daily_realized_loss", lambda bridge, **k: _blocking_report()
    )
    with pytest.raises(ExecutionBlocked):
        require_daily_realized_loss_ready(bridge=_DemoBridge(), config=SimpleNamespace())


def test_stale_ledger_blocks_new_exposure_fail_closed(monkeypatch):
    """An unevaluable loss ledger (prior-UTC-day) must also block - the evasion
    named in the 2026-07-09 correction YAML."""
    import cas_forex.daily_loss_guard as dlg

    monkeypatch.setattr(
        dlg,
        "evaluate_bridge_daily_realized_loss",
        lambda bridge, **k: _blocking_report(
            status="DAILY_REALIZED_LOSS_UTC_PERIOD_STALE",
            realized_today_usd=None,
            detail="ledger from a previous UTC day",
        ),
    )
    with pytest.raises(ExecutionBlocked):
        require_daily_realized_loss_ready(bridge=_DemoBridge(), config=SimpleNamespace())


def test_guarded_place_order_consults_the_loss_guard_before_any_bridge_touch(monkeypatch):
    """The chokepoint itself: guarded_place_order must call
    require_daily_realized_loss_ready and must NOT touch the bridge when it
    raises. This is the line the July loss never had."""
    bridge = _DemoBridge()
    consulted = {"n": 0}

    def blocking_ready(**kwargs):
        consulted["n"] += 1
        raise ExecutionBlocked(
            SimpleNamespace(plain_english_reason="daily realized-loss cap reached (test)")
        )

    monkeypatch.setattr(execution_guard, "require_daily_realized_loss_ready", blocking_ready)
    with pytest.raises(ExecutionBlocked):
        execution_guard.guarded_place_order(
            bridge,
            SimpleNamespace(order_id="pin-1", decision_ref="pin-ref", symbol="NAS100"),
            config=SimpleNamespace(),
        )
    assert consulted["n"] == 1, "dispatch must consult the daily-loss guard"
    assert bridge.calls == [], "a blocked dispatch must never touch the bridge"


def test_source_pin_dispatch_path_contains_the_guard_call():
    """Belt-and-braces: the call must sit inside guarded_place_order's body so
    a refactor cannot silently drop it while the monkeypatched test above still
    passes via a renamed indirection."""
    import inspect

    body = inspect.getsource(execution_guard.guarded_place_order)
    assert "require_daily_realized_loss_ready(" in body
