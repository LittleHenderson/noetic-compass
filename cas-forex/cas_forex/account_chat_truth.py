"""Grounded owner-chat projection for the active execution account.

The Operator and cockpit Assistant share this formatter so account identity,
open P&L accounting, realized growth, and secondary simulator evidence cannot
drift into two contradictory chat stories.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from typing import Any


REPORT_KIND = "cas_forex_active_account_chat_truth"


def asks_active_account_truth(message: str) -> bool:
    """Return True for current-account questions that should bypass free-form AI."""

    low = " ".join(str(message or "").lower().split())
    if not low:
        return False

    direct_markers = (
        "active account",
        "my account",
        "our account",
        "account balance",
        "account status",
        "how is the account",
        "current balance",
        "current equity",
        "current p&l",
        "current pnl",
        "floating p&l",
        "floating pnl",
        "realized growth",
        "cashflow-adjusted",
        "cashflow adjusted",
        "how much have we made",
        "how much have we lost",
    )
    if any(marker in low for marker in direct_markers):
        return True

    account_metric = any(
        marker in low
        for marker in (
            "balance",
            "equity",
            "open p&l",
            "open pnl",
            "realized p&l",
            "realized pnl",
            "account profit",
            "account loss",
        )
    )
    current_cue = any(
        marker in low
        for marker in (
            "current",
            "right now",
            "today",
            "this month",
            "what is",
            "what's",
            "whats",
            "why hasn't",
            "why hasnt",
            "not changed",
            "not moving",
        )
    )
    return account_metric and current_cue


def project_active_account_chat_truth(
    report: Mapping[str, Any] | None,
    *,
    simulator_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project the minimum decision-relevant account facts used by both chats."""

    source = report if isinstance(report, Mapping) else {}
    account = _mapping(source.get("account"))
    exposure = _mapping(source.get("open_exposure"))
    snapshot = _mapping(source.get("snapshot"))
    growth = _mapping(source.get("growth_measurement"))
    reconciliation = _mapping(growth.get("account_growth_reconciliation"))
    last_reconciled = _mapping(growth.get("last_reconciled_growth"))
    decomposition = _mapping(growth.get("open_pnl_decomposition"))
    if not decomposition:
        decomposition = {
            "price_pnl_usd": account.get("position_price_pnl_usd"),
            "swap_or_carry_usd": account.get("open_swap_usd"),
            "commission_usd": account.get("open_commission_usd"),
            "account_net_open_pnl_usd": account.get("floating_pnl_usd"),
            "unattributed_open_pnl_usd": account.get("unattributed_open_pnl_usd"),
        }
    secondary = _mapping(source.get("secondary_simulator"))
    secondary_account = _mapping(secondary.get("account"))
    performance = simulator_evidence if isinstance(simulator_evidence, Mapping) else {}

    projection: dict[str, Any] = {
        "report_kind": REPORT_KIND,
        "status": source.get("status") or "ACTIVE_ACCOUNT_TRUTH_UNAVAILABLE",
        "objective_account_established": bool(source.get("objective_account_established")),
        "authoritative_account_source": source.get("authoritative_account_source"),
        "account": {
            key: account.get(key)
            for key in (
                "login",
                "server",
                "currency",
                "is_demo",
                "mode",
                "balance_usd",
                "equity_usd",
                "floating_pnl_usd",
                "position_price_pnl_usd",
                "open_swap_usd",
                "open_commission_usd",
                "unattributed_open_pnl_usd",
                "margin_used_usd",
                "free_margin_usd",
            )
        },
        "open_exposure": {
            key: exposure.get(key)
            for key in (
                "open_position_count",
                "open_lots",
                "protected_position_count",
                "unprotected_position_count",
                "entry_to_stop_risk_usd",
                "entry_to_stop_risk_pct_equity",
            )
        },
        "snapshot": {
            key: snapshot.get(key)
            for key in (
                "observed_at",
                "age_seconds",
                "fresh",
                "cached",
                "terminal_connected",
                "algo_order_send_ready",
            )
        },
        "growth_measurement": {
            "balance_baseline_status": growth.get("balance_baseline_status"),
            "cashflow_adjusted_realized_growth_usd": growth.get(
                "cashflow_adjusted_realized_growth_usd"
            ),
            "realized_today_usd": growth.get("realized_today_usd"),
            "realized_month_usd": growth.get("realized_month_usd"),
            "net_external_capital_flow_usd": growth.get("net_external_capital_flow_usd"),
            "current_balance_is_profit": growth.get("current_balance_is_profit"),
            "account_growth_reconciled": bool(reconciliation.get("reconciled")),
            "account_growth_truth_status": reconciliation.get("truth_status"),
            "last_reconciled_growth": {
                key: last_reconciled.get(key)
                for key in (
                    "available",
                    "classification",
                    "generated_at",
                    "event_hash",
                    "reconciled_balance_usd",
                    "current_balance_usd",
                    "pending_balance_delta_usd",
                    "cashflow_adjusted_realized_growth_usd",
                    "realized_today_usd",
                    "realized_month_usd",
                    "net_external_capital_flow_usd",
                    "period_utc_day",
                    "current_utc_day",
                )
            },
            "open_pnl_decomposition": {
                key: decomposition.get(key)
                for key in (
                    "price_pnl_usd",
                    "swap_or_carry_usd",
                    "commission_usd",
                    "account_net_open_pnl_usd",
                    "unattributed_open_pnl_usd",
                )
            },
        },
        "secondary_evidence": {
            "authoritative_for_active_account": False,
            "simulator_ledger_balance_usd": secondary_account.get("balance_usd"),
            "simulator_ledger_scope": secondary.get("scope"),
            "performance_evidence_balance_usd": performance.get("honest_paper_balance_usd"),
            "performance_evidence_net_pnl_usd": performance.get(
                "balance_growth_net_pnl_usd"
            ),
            "performance_evidence_scope": performance.get("scope"),
        },
        "claim_boundary": (
            "This is current read-only account truth for conversation. It does not send "
            "an order, change a dial, move money, or combine secondary simulator/replay "
            "evidence with the active MT5 account."
        ),
    }
    canonical = json.dumps(projection, sort_keys=True, separators=(",", ":"), default=str)
    projection["evidence_fingerprint"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return projection


def compose_active_account_chat_reply(projection: Mapping[str, Any] | None) -> str:
    """Render one exact, plain-English account answer from the shared projection."""

    truth = projection if isinstance(projection, Mapping) else {}
    account = _mapping(truth.get("account"))
    exposure = _mapping(truth.get("open_exposure"))
    snapshot = _mapping(truth.get("snapshot"))
    growth = _mapping(truth.get("growth_measurement"))
    decomposition = _mapping(growth.get("open_pnl_decomposition"))
    last_reconciled = _mapping(growth.get("last_reconciled_growth"))
    secondary = _mapping(truth.get("secondary_evidence"))

    if not truth.get("objective_account_established") or not account.get("login"):
        return (
            "The active execution-account truth is unavailable right now, so I will not "
            "guess a balance, P&L, or position count. No order ran, no dial changed, and "
            "no money moved from this chat."
        )

    account_kind = "MT5 demo" if account.get("is_demo") else "MT5 live"
    reply = [
        (
            f"Current active execution account: {account_kind} #{account.get('login')} on "
            f"{account.get('server') or 'unknown server'}. Balance {_money(account.get('balance_usd'))}; "
            f"equity {_money(account.get('equity_usd'))}; "
            f"open positions {_count(exposure.get('open_position_count'))}."
        ),
        (
            "Net open P&L after reported costs "
            f"{_money(decomposition.get('account_net_open_pnl_usd'), signed=True)} = "
            f"price P&L {_money(decomposition.get('price_pnl_usd'), signed=True)} + "
            f"swap/carry {_money(decomposition.get('swap_or_carry_usd'), signed=True)} + "
            f"commission {_money(decomposition.get('commission_usd'), signed=True)} + "
            f"unattributed residual {_money(decomposition.get('unattributed_open_pnl_usd'), signed=True)}."
        ),
        _growth_reply(growth, last_reconciled),
        (
            "Secondary evidence stays separate: simulator ledger balance "
            f"{_money(secondary.get('simulator_ledger_balance_usd'))}; replay/performance "
            f"balance {_money(secondary.get('performance_evidence_balance_usd'))} with net P&L "
            f"{_money(secondary.get('performance_evidence_net_pnl_usd'), signed=True)}. "
            "Neither is added to the active MT5 account."
        ),
        (
            f"Snapshot observed {snapshot.get('observed_at') or 'at an unavailable time'}; "
            f"age {_seconds(snapshot.get('age_seconds'))}; fresh={bool(snapshot.get('fresh'))}."
        ),
        "This chat placed no order, changed no dial, and moved no money.",
    ]
    return " ".join(reply)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _money(value: Any, *, signed: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "unavailable"
    if number < 0:
        return f"-${abs(number):,.2f}"
    prefix = "+" if signed and number > 0 else ""
    return f"{prefix}${number:,.2f}"


def _count(value: Any) -> str:
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "unavailable"


def _seconds(value: Any) -> str:
    try:
        return f"{float(value):.1f}s"
    except (TypeError, ValueError):
        return "unavailable"


def _growth_reply(
    growth: Mapping[str, Any],
    last_reconciled: Mapping[str, Any],
) -> str:
    if growth.get("account_growth_reconciled"):
        return (
            "Cashflow-adjusted realized growth: "
            f"all time {_money(growth.get('cashflow_adjusted_realized_growth_usd'), signed=True)}, "
            f"today {_money(growth.get('realized_today_usd'), signed=True)}, "
            f"this month {_money(growth.get('realized_month_usd'), signed=True)}. "
            f"External capital {_money(growth.get('net_external_capital_flow_usd'))} is excluded from profit; "
            "the current balance itself is not labeled profit."
        )
    if last_reconciled.get("available"):
        return (
            "Broker-history refresh pending. Last reconciled at "
            f"{last_reconciled.get('generated_at') or 'an unavailable time'}: "
            "cashflow-adjusted realized growth all time "
            f"{_money(last_reconciled.get('cashflow_adjusted_realized_growth_usd'), signed=True)}, "
            f"today {_money(last_reconciled.get('realized_today_usd'), signed=True)}, "
            f"this month {_money(last_reconciled.get('realized_month_usd'), signed=True)}; "
            f"external capital {_money(last_reconciled.get('net_external_capital_flow_usd'))}. "
            "The current broker balance differs from that reconciled snapshot by "
            f"{_money(last_reconciled.get('pending_balance_delta_usd'), signed=True)}. "
            "That delta is pending broker-history classification and is not being "
            "guessed as trading profit, loss, deposit, or withdrawal."
        )
    return (
        "Cashflow-adjusted realized growth is unavailable because no matching "
        "broker-history baseline currently reconciles to this account. The current "
        "balance itself is not labeled profit."
    )


__all__ = [
    "REPORT_KIND",
    "asks_active_account_truth",
    "compose_active_account_chat_reply",
    "project_active_account_chat_truth",
]
