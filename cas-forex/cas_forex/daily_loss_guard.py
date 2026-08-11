"""Deterministic daily realized-loss gate for new trading exposure.

The AI Operator may autonomously enter and manage trades inside the owner's
authority envelope. A configured daily loss cap is one boundary of that
envelope: once reconciled broker history reaches the cap, entries and scale-ins
stop for the UTC trading day while risk-reducing management remains available.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence


REPORT_KIND = "cas_forex_daily_realized_loss_gate"


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def effective_daily_loss_cap_usd(
    *,
    config: Any = None,
    control_values: Optional[Mapping[str, Any]] = None,
) -> tuple[float, str]:
    """Return the active owner-fenced cap and the source that supplied it.

    Zero disables the cap. The control authority is preferred because its value
    has already been clamped inside the owner's envelope; static config is only
    a compatibility fallback for runtimes without that authority surface.
    """

    if isinstance(control_values, Mapping) and "daily_loss_cap_usd" in control_values:
        value = _number(control_values.get("daily_loss_cap_usd"))
        return max(0.0, float(value or 0.0)), "supplied_control_values"

    try:
        from cas_forex.ai_control_authority import get_authority

        value = _number(get_authority().control.get("daily_loss_cap_usd"))
        if value is not None:
            return max(0.0, value), "ai_control_authority"
    except Exception:
        pass

    for name in ("daily_loss_cap_usd", "max_daily_loss_usd"):
        try:
            value = _number(getattr(config, name))
        except Exception:
            value = None
        if value is not None:
            return max(0.0, value), f"config.{name}"
    return 0.0, "disabled_default"


def evaluate_daily_realized_loss(
    account_context: Mapping[str, Any] | None,
    *,
    config: Any = None,
    control_values: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Evaluate whether a new entry or scale-in may create exposure."""

    context = dict(account_context or {})
    cap, cap_source = effective_daily_loss_cap_usd(
        config=config,
        control_values=control_values,
    )
    realized = _number(context.get("realized_today_usd"))
    reconciliation = (
        dict(context.get("account_growth_reconciliation") or {})
        if isinstance(context.get("account_growth_reconciliation"), Mapping)
        else {}
    )
    period_stale = reconciliation.get("period_current") is False
    if period_stale:
        realized = None

    base = {
        "report_kind": REPORT_KIND,
        "cap_usd": round(cap, 2),
        "cap_source": cap_source,
        "realized_today_usd": round(realized, 2) if realized is not None else None,
        "account_growth_reconciliation": reconciliation,
        "blocking_cap": "daily_loss_cap_usd",
        "position_management_allowed": True,
        "risk_reducing_close_allowed": True,
        "take_profit_and_stop_management_allowed": True,
    }
    if cap <= 0:
        return {
            **base,
            "status": "DISABLED",
            "block_new_exposure": False,
            "remaining_loss_budget_usd": None,
            "detail": "Daily realized-loss cap is disabled.",
        }

    if realized is None:
        return {
            **base,
            "status": (
                "DAILY_REALIZED_LOSS_UTC_PERIOD_STALE"
                if period_stale
                else "DAILY_REALIZED_LOSS_TRUTH_UNAVAILABLE"
            ),
            "block_new_exposure": True,
            "remaining_loss_budget_usd": None,
            "detail": (
                "New exposure blocked because the reconciled broker loss ledger is "
                "from a previous UTC day and must refresh before today's loss budget "
                "can be evaluated."
                if period_stale
                else (
                    "New exposure blocked because the daily realized-loss cap is active "
                    "but reconciled broker realized P&L for today is unavailable."
                )
            ),
        }

    remaining = round(max(0.0, cap + realized), 2)
    if realized <= -cap + 1e-9:
        return {
            **base,
            "status": "DAILY_REALIZED_LOSS_CAP_REACHED",
            "block_new_exposure": True,
            "remaining_loss_budget_usd": 0.0,
            "detail": (
                f"New exposure blocked: realized P&L today is ${realized:,.2f}, "
                f"at or below the -${cap:,.2f} daily loss boundary. Existing-position "
                "protection, take-profit, partial-close, and full-close actions remain allowed."
            ),
        }

    return {
        **base,
        "status": "WITHIN_DAILY_REALIZED_LOSS_CAP",
        "block_new_exposure": False,
        "remaining_loss_budget_usd": remaining,
        "detail": (
            f"Realized P&L today is ${realized:,.2f}; the configured daily loss "
            f"boundary is -${cap:,.2f}."
        ),
    }


def evaluate_bridge_daily_realized_loss(
    bridge: Any,
    *,
    config: Any = None,
    control_values: Optional[Mapping[str, Any]] = None,
    positions: Optional[Sequence[Mapping[str, Any]]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Build reconciled broker account context and evaluate the daily cap."""

    cap, _ = effective_daily_loss_cap_usd(
        config=config,
        control_values=control_values,
    )
    if cap <= 0:
        return evaluate_daily_realized_loss(
            {},
            config=config,
            control_values=control_values,
        )

    from cas_forex.operator_account_context import build_operator_account_context

    context = build_operator_account_context(
        bridge,
        positions=positions,
        account_snapshot=account_snapshot,
    )
    report = evaluate_daily_realized_loss(
        context,
        config=config,
        control_values=control_values,
    )
    return {
        **report,
        "account_context_hash_input": {
            "login": context.get("login"),
            "server": context.get("server"),
            "balance": context.get("balance"),
            "realized_today_usd": context.get("realized_today_usd"),
            "growth_event_hash": (
                (context.get("account_growth_reconciliation") or {}).get("event_hash")
                if isinstance(context.get("account_growth_reconciliation"), Mapping)
                else None
            ),
        },
    }


__all__ = [
    "REPORT_KIND",
    "effective_daily_loss_cap_usd",
    "evaluate_bridge_daily_realized_loss",
    "evaluate_daily_realized_loss",
]
