"""Cashflow-adjusted realized growth from authoritative MT5 deal history."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from cas_forex.time_utils import ensure_utc, utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_PATH = REPO_ROOT / "runtime" / "mt5-account-growth.json"
REPORT_KIND = "cas_forex_mt5_account_growth"
SCHEMA = "cas_forex_mt5_account_growth.v1"
DEFAULT_HISTORY_DAYS = 36_500
DEFAULT_REFRESH_SECONDS = 21_600

# MetaTrader5 5.0.5735 DEAL_TYPE constants, read from the locally installed
# package. Unknown future types fail the reconciliation closed.
DEAL_TYPE_LABELS = {
    0: "BUY",
    1: "SELL",
    2: "BALANCE",
    3: "CREDIT",
    4: "CHARGE",
    5: "CORRECTION",
    6: "BONUS",
    7: "COMMISSION",
    8: "COMMISSION_DAILY",
    9: "COMMISSION_MONTHLY",
    10: "COMMISSION_AGENT_DAILY",
    11: "COMMISSION_AGENT_MONTHLY",
    12: "INTEREST",
    13: "BUY_CANCELED",
    14: "SELL_CANCELED",
}
TRADE_TYPES = {0, 1}
CAPITAL_FLOW_TYPES = {2, 3, 6}
ACCOUNT_COST_TYPES = {4, 7, 8, 9, 10, 11, 12}
CORRECTION_TYPES = {5, 13, 14}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [dict(row) for row in value if isinstance(row, Mapping)]


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _money(value: float) -> float:
    return round(float(value), 2)


def _deal_effect(row: Mapping[str, Any]) -> float:
    return sum(
        _number(row.get(key)) or 0.0
        for key in ("profit", "commission", "swap", "fee")
    )


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return ensure_utc(value)
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return ensure_utc(datetime.fromisoformat(text))
    except ValueError:
        return None


def _deal_time(row: Mapping[str, Any]) -> datetime | None:
    parsed = _parse_datetime(row.get("time_iso"))
    if parsed is not None:
        return parsed
    seconds = _number(row.get("time"))
    if seconds is None:
        return None
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _latest_deal_fingerprint(rows: Sequence[Mapping[str, Any]]) -> str | None:
    normalized = sorted(
        _rows(rows),
        key=lambda row: (
            _number(row.get("time")) or 0.0,
            _number(row.get("time_msc")) or 0.0,
            str(row.get("ticket") or ""),
        ),
    )
    return _hash(normalized[-1]) if normalized else None


def account_identity_hash(login: Any, server: Any) -> str | None:
    if login in (None, "") or server in (None, ""):
        return None
    return _hash({"login": login, "server": server})


def classify_mt5_account_growth_snapshot(
    growth_snapshot: Mapping[str, Any] | None,
    *,
    login: Any,
    server: Any,
    current_balance: Any,
    observed_at: datetime | str | None = None,
) -> dict[str, Any]:
    """Classify exact versus pending growth truth for one broker account."""

    growth = _mapping(growth_snapshot)
    account = _mapping(growth.get("account"))
    baseline = _mapping(growth.get("baseline"))
    reconciliation = _mapping(growth.get("reconciliation"))
    period = _mapping(growth.get("period"))
    reference_at = _parse_datetime(observed_at) or ensure_utc(utc_now())
    current_utc_day = reference_at.date().isoformat()
    current_utc_month = reference_at.strftime("%Y-%m")
    generated_at = _parse_datetime(growth.get("generated_at"))
    period_utc_day = str(period.get("utc_day") or "").strip() or (
        generated_at.date().isoformat() if generated_at is not None else None
    )
    period_utc_month = str(period.get("utc_month") or "").strip() or (
        generated_at.strftime("%Y-%m") if generated_at is not None else None
    )
    selected_hash = account_identity_hash(login, server)
    account_matches = bool(
        selected_hash
        and selected_hash == str(account.get("account_id_hash") or "").strip()
    )
    saved_balance = _number(account.get("current_balance_account_currency"))
    selected_balance = _number(current_balance)
    balance_matches = bool(
        account_matches
        and saved_balance is not None
        and selected_balance is not None
        and abs(saved_balance - selected_balance) <= 0.005
    )
    source_reconciled = bool(
        account_matches
        and growth.get("status") == "RECONCILED_CASHFLOW_ADJUSTED_GROWTH"
        and baseline.get("status")
        == "RECONCILED_CASHFLOW_ADJUSTED_ACCOUNT_HISTORY"
        and reconciliation.get("ledger_ties_to_current_balance") is True
        and reconciliation.get("growth_components_tie") is True
    )
    period_current = bool(period_utc_day and period_utc_day == current_utc_day)
    month_current = bool(
        period_utc_month and period_utc_month == current_utc_month
    )
    pending_delta = (
        round(selected_balance - saved_balance, 2)
        if source_reconciled
        and not balance_matches
        and selected_balance is not None
        and saved_balance is not None
        else None
    )
    exact = bool(source_reconciled and balance_matches and period_current)
    return {
        "account_matches": account_matches,
        "balance_matches": balance_matches,
        "source_reconciled": source_reconciled,
        "period_current": period_current,
        "month_current": month_current,
        "reconciled": exact,
        "last_reconciled_available": source_reconciled,
        "pending_balance_delta_account_currency": pending_delta,
        "saved_balance_account_currency": saved_balance,
        "current_balance_account_currency": selected_balance,
        "period_utc_day": period_utc_day,
        "current_utc_day": current_utc_day,
        "period_utc_month": period_utc_month,
        "current_utc_month": current_utc_month,
        "status": (
            "EXACT_RECONCILED_CURRENT_BALANCE"
            if exact
            else "PENDING_BROKER_HISTORY_RECONCILIATION"
            if source_reconciled and not balance_matches
            else "STALE_PERIOD_RECONCILIATION"
            if source_reconciled and not period_current
            else "UNAVAILABLE"
        ),
    }


def _effective_full_history_days(
    existing: Mapping[str, Any],
    *,
    now: datetime,
    requested_days: int,
    same_account: bool,
) -> tuple[int, str]:
    """Bound repeat queries to the lifetime proven by the prior full ledger."""

    requested = max(int(requested_days), 1)
    history = _mapping(existing.get("history"))
    first_event_at = _parse_datetime(history.get("first_event_at"))
    reusable_baseline = bool(
        same_account
        and existing.get("status") == "RECONCILED_CASHFLOW_ADJUSTED_GROWTH"
        and first_event_at is not None
        and first_event_at <= now
    )
    if not reusable_baseline:
        return requested, "FULL_CONFIGURED_HISTORY"

    account_age_days = max((now - first_event_at).total_seconds(), 0.0) / 86_400.0
    bounded = max(int(math.ceil(account_age_days)) + 2, 2)
    return min(requested, bounded), "BOUNDED_FROM_RECONCILED_FIRST_EVENT"


def build_mt5_account_growth_report(
    history_report: Mapping[str, Any],
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Reconcile current balance to capital flows and realized account effects."""

    history = _mapping(history_report)
    terminal = _mapping(history.get("terminal_snapshot"))
    account = _mapping(terminal.get("account"))
    query = _mapping(history.get("query"))
    raw_deals = sorted(
        _rows(history.get("raw_deals")),
        key=lambda row: (
            _number(row.get("time")) or 0.0,
            _number(row.get("time_msc")) or 0.0,
            str(row.get("ticket") or ""),
        ),
    )
    closed_rows = _rows(history.get("history_records"))
    now = ensure_utc(generated_at or utc_now())
    current_balance = _number(account.get("balance"))
    account_hash = str(account.get("account_id_hash") or "").strip() or None

    event_rows: list[dict[str, Any]] = []
    unknown_types: set[int | str] = set()
    for row in raw_deals:
        deal_type = _integer(row.get("type"))
        label = DEAL_TYPE_LABELS.get(deal_type) if deal_type is not None else None
        if label is None:
            unknown_types.add(deal_type if deal_type is not None else str(row.get("type")))
        effect = _deal_effect(row)
        timestamp = _deal_time(row)
        if deal_type in TRADE_TYPES:
            bucket = "TRADING"
        elif deal_type in CAPITAL_FLOW_TYPES:
            bucket = "CAPITAL_FLOW"
        elif deal_type in ACCOUNT_COST_TYPES:
            bucket = "ACCOUNT_COST_OR_INTEREST"
        elif deal_type in CORRECTION_TYPES:
            bucket = "BROKER_CORRECTION"
        else:
            bucket = "UNKNOWN"
        event_rows.append(
            {
                "type": deal_type,
                "type_label": label or "UNKNOWN",
                "bucket": bucket,
                "effect": effect,
                "timestamp": timestamp,
                "profit": _number(row.get("profit")) or 0.0,
                "commission": _number(row.get("commission")) or 0.0,
                "swap": _number(row.get("swap")) or 0.0,
                "fee": _number(row.get("fee")) or 0.0,
            }
        )

    capital_rows = [row for row in event_rows if row["bucket"] == "CAPITAL_FLOW"]
    noncapital_rows = [row for row in event_rows if row["bucket"] != "CAPITAL_FLOW"]
    trade_rows = [row for row in event_rows if row["bucket"] == "TRADING"]
    cost_rows = [
        row for row in event_rows if row["bucket"] == "ACCOUNT_COST_OR_INTEREST"
    ]
    correction_rows = [
        row for row in event_rows if row["bucket"] == "BROKER_CORRECTION"
    ]

    net_capital_flow = sum(float(row["effect"]) for row in capital_rows)
    ledger_balance = sum(float(row["effect"]) for row in event_rows)
    noncapital_effect = sum(float(row["effect"]) for row in noncapital_rows)
    trade_effect = sum(float(row["effect"]) for row in trade_rows)
    account_cost_effect = sum(float(row["effect"]) for row in cost_rows)
    correction_effect = sum(float(row["effect"]) for row in correction_rows)
    closed_position_net = sum(_number(row.get("profit")) or 0.0 for row in closed_rows)
    balance_residual = (
        float(current_balance) - ledger_balance if current_balance is not None else None
    )
    cashflow_adjusted_growth = (
        float(current_balance) - net_capital_flow if current_balance is not None else None
    )
    growth_reconciliation_residual = (
        float(cashflow_adjusted_growth) - noncapital_effect
        if cashflow_adjusted_growth is not None
        else None
    )

    balance_deposits = sum(
        max(float(row["effect"]), 0.0)
        for row in capital_rows
        if row["type"] == 2
    )
    balance_withdrawals = sum(
        abs(min(float(row["effect"]), 0.0))
        for row in capital_rows
        if row["type"] == 2
    )
    credit_net = sum(
        float(row["effect"]) for row in capital_rows if row["type"] == 3
    )
    bonus_net = sum(
        float(row["effect"]) for row in capital_rows if row["type"] == 6
    )

    timestamps = [row["timestamp"] for row in event_rows if row["timestamp"] is not None]
    first_event_at = min(timestamps) if timestamps else None
    last_event_at = max(timestamps) if timestamps else None
    query_start = _parse_datetime(query.get("start"))
    query_end = _parse_datetime(query.get("end"))
    first_effective_row = next(
        (row for row in event_rows if abs(float(row["effect"])) > 0.0000001),
        None,
    )
    opening_capital_event = bool(
        first_effective_row
        and first_effective_row["bucket"] == "CAPITAL_FLOW"
        and float(first_effective_row["effect"]) > 0.0
    )
    query_precedes_first_event = bool(
        query_start is not None
        and first_event_at is not None
        and query_start <= first_event_at - timedelta(days=1)
    )
    ledger_ties = bool(
        balance_residual is not None and abs(float(balance_residual)) <= 0.011
    )
    growth_ties = bool(
        growth_reconciliation_residual is not None
        and abs(float(growth_reconciliation_residual)) <= 0.011
    )

    if not raw_deals or current_balance is None or account_hash is None:
        status = "ACCOUNT_HISTORY_UNAVAILABLE"
        baseline_status = "UNAVAILABLE_NO_RECONCILED_CASHFLOW_BASELINE"
    elif unknown_types:
        status = "PARTIAL_ACCOUNT_HISTORY_UNKNOWN_DEAL_TYPES"
        baseline_status = "UNAVAILABLE_UNKNOWN_MT5_DEAL_TYPES"
    elif not opening_capital_event or not query_precedes_first_event:
        status = "PARTIAL_ACCOUNT_HISTORY_NO_OPENING_CAPITAL"
        baseline_status = "UNAVAILABLE_NO_OPENING_CAPITAL_EVENT"
    elif not ledger_ties or not growth_ties:
        status = "ACCOUNT_LEDGER_DOES_NOT_TIE_TO_BALANCE"
        baseline_status = "UNAVAILABLE_ACCOUNT_LEDGER_RECONCILIATION_FAILED"
    else:
        status = "RECONCILED_CASHFLOW_ADJUSTED_GROWTH"
        baseline_status = "RECONCILED_CASHFLOW_ADJUSTED_ACCOUNT_HISTORY"

    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_month = start_today.replace(day=1)
    latest_deal_fingerprint = _latest_deal_fingerprint(raw_deals)

    def period_effect(start: datetime) -> float:
        return sum(
            float(row["effect"])
            for row in noncapital_rows
            if row["timestamp"] is not None and row["timestamp"] >= start
        )

    deal_counts: dict[str, int] = {}
    for row in event_rows:
        label = str(row["type_label"])
        deal_counts[label] = deal_counts.get(label, 0) + 1

    result = {
        "report_kind": REPORT_KIND,
        "schema": SCHEMA,
        "status": status,
        "generated_at": now.isoformat(),
        "period": {
            "timezone": "UTC",
            "utc_day": start_today.date().isoformat(),
            "utc_month": start_month.strftime("%Y-%m"),
            "day_start": start_today.isoformat(),
            "month_start": start_month.isoformat(),
        },
        "account": {
            "account_id_hash": account_hash,
            "server": account.get("server"),
            "currency": account.get("currency") or "USD",
            "account_mode": history.get("account_mode") or query.get("account_mode"),
            "current_balance_account_currency": (
                _money(current_balance) if current_balance is not None else None
            ),
            "current_equity_account_currency": _number(account.get("equity")),
        },
        "baseline": {
            "status": baseline_status,
            "current_balance_is_profit": False,
            "opening_capital_event_present": opening_capital_event,
            "query_precedes_first_event": query_precedes_first_event,
            "net_external_capital_flow_account_currency": _money(net_capital_flow),
            "balance_deposits_account_currency": _money(balance_deposits),
            "balance_withdrawals_account_currency": _money(balance_withdrawals),
            "credit_net_account_currency": _money(credit_net),
            "bonus_net_account_currency": _money(bonus_net),
        },
        "realized_growth": {
            "cashflow_adjusted_all_time_account_currency": (
                _money(cashflow_adjusted_growth)
                if cashflow_adjusted_growth is not None
                else None
            ),
            "today_account_currency": _money(period_effect(start_today)),
            "month_account_currency": _money(period_effect(start_month)),
            "growth_pct_on_net_external_capital": (
                round((float(cashflow_adjusted_growth) / net_capital_flow) * 100.0, 4)
                if cashflow_adjusted_growth is not None and net_capital_flow > 0
                else None
            ),
            "closed_position_net_pnl_account_currency": _money(closed_position_net),
            "trade_effect_not_in_closed_position_rows_account_currency": _money(
                trade_effect - closed_position_net
            ),
        },
        "components": {
            "trade_gross_profit_account_currency": _money(
                sum(float(row["profit"]) for row in trade_rows)
            ),
            "trade_commission_account_currency": _money(
                sum(float(row["commission"]) for row in trade_rows)
            ),
            "trade_swap_account_currency": _money(
                sum(float(row["swap"]) for row in trade_rows)
            ),
            "trade_fee_account_currency": _money(
                sum(float(row["fee"]) for row in trade_rows)
            ),
            "trade_net_effect_account_currency": _money(trade_effect),
            "account_cost_or_interest_effect_account_currency": _money(
                account_cost_effect
            ),
            "broker_correction_effect_account_currency": _money(correction_effect),
            "all_noncapital_effect_account_currency": _money(noncapital_effect),
        },
        "reconciliation": {
            "ledger_balance_account_currency": _money(ledger_balance),
            "current_balance_account_currency": (
                _money(current_balance) if current_balance is not None else None
            ),
            "balance_residual_account_currency": (
                _money(balance_residual) if balance_residual is not None else None
            ),
            "cashflow_adjusted_growth_residual_account_currency": (
                _money(growth_reconciliation_residual)
                if growth_reconciliation_residual is not None
                else None
            ),
            "ledger_ties_to_current_balance": ledger_ties,
            "growth_components_tie": growth_ties,
            "unknown_deal_types": sorted(str(value) for value in unknown_types),
        },
        "history": {
            "query_start": query_start.isoformat() if query_start else None,
            "query_end": query_end.isoformat() if query_end else None,
            "history_days_back": query.get("days_back"),
            "raw_deal_count": len(raw_deals),
            "closed_position_count": len(closed_rows),
            "first_event_at": first_event_at.isoformat() if first_event_at else None,
            "last_event_at": last_event_at.isoformat() if last_event_at else None,
            "latest_deal_fingerprint": latest_deal_fingerprint,
            "deal_type_counts": deal_counts,
            "raw_deals_sha256": history.get("raw_deals_sha256") or _hash(raw_deals),
            "deal_type_map_source": "MetaTrader5 5.0.5735 DEAL_TYPE constants 0-14",
        },
        "period_realized_status": (
            "RECONCILED_MT5_ACCOUNT_HISTORY"
            if status == "RECONCILED_CASHFLOW_ADJUSTED_GROWTH"
            else "UNAVAILABLE_NO_PERIOD_RECONCILIATION"
        ),
        "claim_boundary": (
            "This read-only ledger measures cashflow-adjusted realized account growth. "
            "Deposits, withdrawals, credit, and bonus flows are not trading profit. "
            "Open P&L remains separate and unrealized. The report cannot place orders, "
            "move money, authorize live trading, or promise future profit."
        ),
    }
    result["event_hash"] = _hash(result)
    return result


def load_mt5_account_growth(
    state_path: Path | str = DEFAULT_STATE_PATH,
) -> dict[str, Any]:
    path = Path(state_path)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def refresh_mt5_account_growth_if_due(
    *,
    mt5_module: Any,
    mt5_path: Path | str | None,
    current_history_report: Mapping[str, Any],
    state_path: Path | str = DEFAULT_STATE_PATH,
    account_mode: str = "demo",
    confirm_live_history: bool = False,
    history_days_back: int = DEFAULT_HISTORY_DAYS,
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS,
    force: bool = False,
    history_builder: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Refresh the compact full-history growth ledger when account state changes."""

    now = ensure_utc(utc_now())
    current = _mapping(current_history_report)
    current_query = _mapping(current.get("query"))
    current_account = _mapping(_mapping(current.get("terminal_snapshot")).get("account"))
    account_hash = str(current_account.get("account_id_hash") or "").strip() or None
    current_balance = _number(current_account.get("balance"))
    current_latest_deal_fingerprint = _latest_deal_fingerprint(
        _rows(current.get("raw_deals"))
    )
    existing = load_mt5_account_growth(state_path)
    existing_account = _mapping(existing.get("account"))
    existing_history = _mapping(existing.get("history"))
    existing_period = _mapping(existing.get("period"))
    existing_generated = _parse_datetime(existing.get("generated_at"))
    age_seconds = (
        (now - existing_generated).total_seconds()
        if existing_generated is not None
        else None
    )
    current_utc_day = now.date().isoformat()
    existing_utc_day = str(existing_period.get("utc_day") or "").strip()
    if not existing_utc_day and existing_generated is not None:
        existing_utc_day = existing_generated.date().isoformat()
    period_current = existing_utc_day == current_utc_day
    same_account = bool(
        account_hash
        and account_hash == str(existing_account.get("account_id_hash") or "")
    )
    existing_balance = _number(existing_account.get("current_balance_account_currency"))
    same_balance = bool(
        current_balance is not None
        and existing_balance is not None
        and abs(current_balance - existing_balance) <= 0.005
    )
    existing_latest_deal_fingerprint = str(
        existing_history.get("latest_deal_fingerprint") or ""
    ).strip() or None
    existing_last_event_at = _parse_datetime(existing_history.get("last_event_at"))
    current_query_start = _parse_datetime(current_query.get("start"))
    if current_latest_deal_fingerprint is not None:
        recent_history_consistent = bool(
            existing_latest_deal_fingerprint
            and current_latest_deal_fingerprint == existing_latest_deal_fingerprint
        )
    elif existing_latest_deal_fingerprint is None:
        recent_history_consistent = bool(
            existing_history.get("raw_deal_count") == 0
        )
    else:
        recent_history_consistent = bool(
            existing_last_event_at is not None
            and current_query_start is not None
            and existing_last_event_at < current_query_start
        )
    if (
        not force
        and existing
        and same_account
        and same_balance
        and period_current
        and recent_history_consistent
        and age_seconds is not None
        and 0 <= age_seconds < max(int(refresh_seconds), 1)
    ):
        return {
            **existing,
            "refresh_status": "CACHED_ACCOUNT_BALANCE_UNCHANGED",
            "refresh_reason": "CACHE_PERIOD_AND_RECENT_DEAL_IDENTITY_CURRENT",
            "snapshot_age_seconds": round(age_seconds, 3),
            "snapshot_period_current": True,
            "recent_history_consistent": True,
        }

    if force:
        refresh_reason = "FORCED"
    elif not existing:
        refresh_reason = "NO_EXISTING_SNAPSHOT"
    elif not same_account:
        refresh_reason = "ACCOUNT_CHANGED"
    elif not same_balance:
        refresh_reason = "BALANCE_CHANGED"
    elif not period_current:
        refresh_reason = "UTC_DAY_ROLLOVER"
    elif not recent_history_consistent:
        refresh_reason = "RECENT_DEAL_FINGERPRINT_CHANGED"
    else:
        refresh_reason = "PERIODIC_REFRESH_DUE"

    effective_history_days, history_window_status = _effective_full_history_days(
        existing,
        now=now,
        requested_days=history_days_back,
        same_account=same_account,
    )

    if history_builder is None:
        from cas_forex.mt5_deal_history_ingest import (
            build_mt5_deal_history_ingest_report,
        )

        history_builder = build_mt5_deal_history_ingest_report
    full_history = history_builder(
        mt5_path=mt5_path,
        mt5_module=mt5_module,
        account_mode=account_mode,
        confirm_live_history=confirm_live_history,
        days_back=effective_history_days,
        run_terminal_history_ingest=False,
        write_report=False,
    )
    report = build_mt5_account_growth_report(full_history)
    report["refresh_status"] = "FULL_HISTORY_REFRESHED"
    report["refresh_reason"] = refresh_reason
    report["snapshot_age_seconds"] = 0.0
    report["snapshot_period_current"] = True
    report["recent_history_consistent"] = True
    report["refresh_history_window_status"] = history_window_status
    report["refresh_requested_history_days"] = max(int(history_days_back), 1)
    report["refresh_effective_history_days"] = effective_history_days
    _write_state(state_path, report)
    return report


def _write_state(path: Path | str, payload: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(f"{target.suffix}.tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(target)


__all__ = [
    "DEFAULT_HISTORY_DAYS",
    "DEFAULT_REFRESH_SECONDS",
    "DEFAULT_STATE_PATH",
    "DEAL_TYPE_LABELS",
    "REPORT_KIND",
    "SCHEMA",
    "account_identity_hash",
    "build_mt5_account_growth_report",
    "classify_mt5_account_growth_snapshot",
    "load_mt5_account_growth",
    "refresh_mt5_account_growth_if_due",
]
