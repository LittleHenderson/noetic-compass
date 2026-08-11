from types import SimpleNamespace

from cas_forex.mt5_permissions import build_mt5_permission_state, mt5_order_send_block_reason


def test_mt5_permission_state_reports_ready_demo_order_send():
    terminal = SimpleNamespace(connected=True, trade_allowed=True, tradeapi_disabled=False)
    account = SimpleNamespace(trade_allowed=True, trade_expert=True, trade_mode=0)

    state = build_mt5_permission_state(terminal, account, is_demo=True)

    assert state["status"] == "ORDER_SEND_READY_AT_TERMINAL"
    assert state["permission_label"] == "MT5 ORDER_SEND READY"
    assert state["can_submit_order_send"] is True
    assert state["blockers"] == []
    assert "demo/paper" in state["plain_english"]
    assert mt5_order_send_block_reason(state) is None


def test_mt5_permission_state_reports_explicit_algo_blocker():
    terminal = SimpleNamespace(connected=True, trade_allowed=False, tradeapi_disabled=False)
    account = SimpleNamespace(trade_allowed=True, trade_expert=True, trade_mode=0)

    state = build_mt5_permission_state(terminal, account, is_demo=True)

    assert state["status"] == "TERMINAL_ALGO_DISABLED"
    assert state["permission_label"] == "MT5 ORDER_SEND BLOCKED"
    assert state["can_submit_order_send"] is False
    assert "MT5 Algo Trading is off" in state["blockers"][0]
    assert "MT5 order_send blocked before broker request" in mt5_order_send_block_reason(state)


def test_mt5_permission_state_keeps_missing_optional_flags_unknown_not_blocked():
    terminal = SimpleNamespace(connected=True)
    account = SimpleNamespace(trade_mode=0)

    state = build_mt5_permission_state(terminal, account, is_demo=True)

    assert state["status"] == "PERMISSION_UNKNOWN"
    assert state["permission_label"] == "MT5 PERMISSION UNKNOWN"
    assert state["can_submit_order_send"] is False
    assert state["blockers"] == []
    assert mt5_order_send_block_reason(state) is None
