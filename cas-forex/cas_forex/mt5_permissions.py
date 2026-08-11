"""MT5 terminal/account trade-permission interpretation.

These helpers do not authorize CAS Forex live trading. They only explain whether
the local MetaTrader terminal/account appears able to accept an ``order_send``
call before CAS risk and owner-live gates are considered.
"""

from __future__ import annotations

from typing import Any


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def build_mt5_permission_state(
    terminal: Any,
    account: Any,
    *,
    is_demo: bool | None = None,
) -> dict[str, Any]:
    """Return an owner-facing MT5 permission summary from terminal/account info."""

    terminal_connected = _bool_or_none(getattr(terminal, "connected", None)) if terminal is not None else None
    terminal_trade_allowed = _bool_or_none(getattr(terminal, "trade_allowed", None)) if terminal is not None else None
    terminal_tradeapi_disabled = (
        _bool_or_none(getattr(terminal, "tradeapi_disabled", None)) if terminal is not None else None
    )
    account_trade_allowed = _bool_or_none(getattr(account, "trade_allowed", None)) if account is not None else None
    account_trade_expert = _bool_or_none(getattr(account, "trade_expert", None)) if account is not None else None
    account_trade_mode = getattr(account, "trade_mode", None) if account is not None else None

    blockers: list[str] = []
    if terminal is None:
        blockers.append("MT5 terminal_info is unavailable.")
    elif terminal_connected is False:
        blockers.append("MT5 terminal is disconnected.")
    if account is None:
        blockers.append("MT5 account_info is unavailable.")
    if terminal_trade_allowed is False:
        blockers.append("MT5 Algo Trading is off in the terminal.")
    if terminal_tradeapi_disabled is True:
        blockers.append("MT5 Python trade API is disabled by the terminal.")
    if account_trade_allowed is False:
        blockers.append("The connected MT5 account reports trade_allowed=false.")
    if account_trade_expert is False:
        blockers.append("The connected MT5 account reports trade_expert=false.")

    can_submit = (
        not blockers
        and terminal_connected is not False
        and terminal_trade_allowed is True
        and terminal_tradeapi_disabled is not True
        and account_trade_allowed is not False
        and account_trade_expert is not False
    )

    if blockers:
        if terminal is None:
            status = "TERMINAL_INFO_UNAVAILABLE"
        elif terminal_connected is False:
            status = "TERMINAL_DISCONNECTED"
        elif account is None:
            status = "ACCOUNT_INFO_UNAVAILABLE"
        elif terminal_trade_allowed is False:
            status = "TERMINAL_ALGO_DISABLED"
        elif terminal_tradeapi_disabled is True:
            status = "MT5_TRADE_API_DISABLED"
        elif account_trade_allowed is False:
            status = "ACCOUNT_TRADE_DISABLED"
        elif account_trade_expert is False:
            status = "ACCOUNT_EXPERT_DISABLED"
        else:
            status = "ORDER_SEND_BLOCKED"
    elif can_submit:
        status = "ORDER_SEND_READY_AT_TERMINAL"
    else:
        status = "PERMISSION_UNKNOWN"

    if status == "ORDER_SEND_READY_AT_TERMINAL":
        if is_demo is True:
            plain = (
                "MT5 terminal permissions look order-send ready for demo/paper. "
                "CAS risk controls still apply before any dispatch."
            )
        elif is_demo is False:
            plain = (
                "MT5 terminal permissions look order-send ready for real-money order_send. "
                "CAS owner live-authority gates and risk controls still apply."
            )
        else:
            plain = "MT5 terminal permissions look order-send ready. CAS gates still apply."
    elif blockers:
        plain = "MT5 order_send is blocked before CAS can submit: " + " ".join(blockers)
    else:
        plain = (
            "CAS can read the MT5 account, but one or more MT5 permission fields are unavailable. "
            "Confirm Algo Trading and account trading permissions before expecting order_send."
        )

    return {
        "report_kind": "cas_forex_mt5_permission_state",
        "status": status,
        "permission_label": "MT5 ORDER_SEND READY" if can_submit else (
            "MT5 PERMISSION UNKNOWN" if not blockers else "MT5 ORDER_SEND BLOCKED"
        ),
        "can_submit_order_send": can_submit,
        "terminal_connected": terminal_connected,
        "terminal_trade_allowed": terminal_trade_allowed,
        "terminal_algo_trading_enabled": terminal_trade_allowed,
        "terminal_tradeapi_disabled": terminal_tradeapi_disabled,
        "account_trade_allowed": account_trade_allowed,
        "account_expert_trading_allowed": account_trade_expert,
        "account_trade_mode": account_trade_mode,
        "blockers": blockers,
        "plain_english": plain,
    }


def mt5_order_send_block_reason(permission_state: dict[str, Any]) -> str | None:
    """Return a concise rejection reason for explicit MT5 permission blockers."""

    blockers = [str(item).strip() for item in permission_state.get("blockers", []) if str(item).strip()]
    if not blockers:
        return None
    return "MT5 order_send blocked before broker request: " + "; ".join(blockers)
