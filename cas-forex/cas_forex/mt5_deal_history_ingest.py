"""MT5 closed-deal history ingest for CAS Forex.

This reads closed demo/paper trade deals from the local MetaTrader5 Python API
by default, exports them in the existing terminal-history shape, and optionally
runs the generic terminal_history_ingest joiner so deal P/L can flow into CAS
memory. Live account history can be read only through the explicit
``account_mode="live"`` + ``confirm_live_history=True`` path; that path is still
read-only evidence and never places orders or moves money.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from cas_forex import mt5_connect_guard
from cas_forex.config import config
from cas_forex.market_data.connector import infer_mt5_future_server_offset_seconds
from cas_forex.terminal_history_ingest import (
    DEFAULT_OUTPUT_DIR as DEFAULT_TERMINAL_HISTORY_OUTPUT_DIR,
    DEFAULT_SOURCE_DIR as DEFAULT_TERMINAL_HISTORY_EXPORT_DIR,
    ingest_terminal_history,
)
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_MT5_DEPS = REPO_ROOT / ".mt5deps"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "mt5_deal_history_ingest"
REPORT_KIND = "cas_forex_mt5_deal_history_ingest_report"
INGEST_SCHEMA = "cas_forex_mt5_deal_history_ingest.v1"
EXPORT_SCHEMA = "cas_forex_mt5_deal_history_export.v1"
CLAIM_BOUNDARY = (
    "MT5 deal history ingest reads closed deal history through the MetaTrader5 "
    "Python API and exports it for CAS Forex memory and profit-accounting "
    "review. Demo/paper is the default lane; live account history requires an "
    "explicit live-history confirmation. It does not place live broker orders, "
    "create broker ACCEPT, deposit, withdraw, move bank/card funds, automate "
    "payouts, or override runtime gates."
)
_CLOCK_PROBE_SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US30", "NAS100", "SPX500")


class MT5DealHistoryIngestError(ValueError):
    """Raised when MT5 deal-history ingest evidence is invalid."""


def build_mt5_deal_history_ingest_report(
    *,
    mt5_path: Optional[Path | str] = None,
    start: Optional[datetime | str] = None,
    end: Optional[datetime | str] = None,
    days_back: int = 7,
    future_minutes: int = 120,
    symbol: Optional[str] = None,
    ticket: Optional[str | int] = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    export_dir: Path | str = DEFAULT_TERMINAL_HISTORY_EXPORT_DIR,
    terminal_history_output_dir: Path | str = DEFAULT_TERMINAL_HISTORY_OUTPUT_DIR,
    memory_report: Optional[Mapping[str, Any]] = None,
    memory_report_dir: Optional[Path | str] = None,
    mt5_module: Any | None = None,
    run_terminal_history_ingest: bool = True,
    write_report: bool = True,
    account_mode: str = "demo",
    confirm_live_history: bool = False,
) -> Dict[str, Any]:
    """Read MT5 deal history, export normalized rows, and write evidence."""

    mode = _normalize_account_mode(account_mode)
    _add_local_mt5_deps()
    mt5 = mt5_module or _import_mt5()
    resolved_mt5_path = str(mt5_path or config.mt5_path or "")
    # Account mode is an explicit argument throughout this read-only pipeline.
    # Do not mutate the process-global config while the autonomous dispatch
    # thread may be evaluating another order.
    query_start, query_end = _query_window(
        start=start,
        end=end,
        days_back=days_back,
        future_minutes=future_minutes,
    )
    terminal_snapshot = _terminal_snapshot(mt5=mt5, mt5_path=resolved_mt5_path or None)
    should_fetch = _should_fetch_deals(
        terminal_snapshot,
        account_mode=mode,
        confirm_live_history=confirm_live_history,
    )
    time_normalization = _mt5_server_time_normalization(
        mt5=mt5,
        symbol=symbol,
        enabled=should_fetch,
    )
    server_offset_seconds = int(time_normalization.get("server_utc_offset_seconds") or 0)
    broker_query_start = query_start + timedelta(seconds=server_offset_seconds)
    broker_query_end = query_end + timedelta(seconds=server_offset_seconds)
    raw_deals = (
        _fetch_deals(
            mt5=mt5,
            start=broker_query_start,
            end=broker_query_end,
            ticket=ticket,
            symbol=symbol,
            server_offset_seconds=server_offset_seconds,
        )
        if should_fetch
        else []
    )

    history_rows = _closed_history_rows(
        raw_deals,
        account=terminal_snapshot.get("account") if isinstance(terminal_snapshot.get("account"), Mapping) else {},
        ticket=ticket,
        broker_mode="LIVE_MT5" if mode == "live" else "PAPER_MT5",
    )
    export_path: Optional[Path] = None
    if write_report:
        export_path = write_mt5_deal_history_export(
            history_rows,
            export_dir=export_dir,
            query_start=query_start,
            query_end=query_end,
            ticket=ticket,
            account_mode=mode,
        )

    terminal_history_report: Dict[str, Any] = {}
    if run_terminal_history_ingest and export_path is not None:
        terminal_history_report = ingest_terminal_history(
            source_paths=[export_path],
            memory_report=memory_report,
            memory_report_dir=memory_report_dir,
            output_dir=terminal_history_output_dir,
        )

    summary = _summary(
        terminal_snapshot=terminal_snapshot,
        raw_deals=raw_deals,
        history_rows=history_rows,
        terminal_history_report=terminal_history_report,
        export_path=export_path,
        ticket=ticket,
        account_mode=mode,
        confirm_live_history=confirm_live_history,
        time_normalization=time_normalization,
    )
    ingest_status = _ingest_status(summary)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "ingest_status": ingest_status,
        "schema": INGEST_SCHEMA,
        "query": {
            "start": query_start.isoformat(),
            "end": query_end.isoformat(),
            "days_back": int(days_back),
            "future_minutes": int(future_minutes),
            "symbol": symbol,
            "ticket": str(ticket) if ticket is not None else None,
            "account_mode": mode,
            "confirm_live_history": bool(confirm_live_history),
            "broker_query_start": broker_query_start.isoformat(),
            "broker_query_end": broker_query_end.isoformat(),
        },
        "account_mode": mode,
        "confirm_live_history": bool(confirm_live_history),
        "mt5_path": resolved_mt5_path,
        "terminal_snapshot": terminal_snapshot,
        "history_export_path": str(export_path) if export_path is not None else None,
        "raw_deal_count": len(raw_deals),
        "raw_deals_sha256": _sha256_json(raw_deals),
        "history_records": history_rows,
        "raw_deals": raw_deals,
        "time_normalization": time_normalization,
        "terminal_history_ingest": _compact_terminal_history_report(terminal_history_report),
        "summary": summary,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(ingest_status, summary),
        "operator_commands": _operator_commands(mt5_path),
        "output_dir": str(Path(output_dir)),
    }
    if write_report:
        paths = write_mt5_deal_history_ingest_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in paths.items()}
    validate_mt5_deal_history_ingest_report(report)
    return report


def write_mt5_deal_history_ingest_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_mt5_deal_history_ingest_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"mt5-deal-history-ingest-{stamp}-report.json"
    md_path = target_dir / f"mt5-deal-history-ingest-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_mt5_deal_history_ingest_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def write_mt5_deal_history_export(
    history_rows: Sequence[Mapping[str, Any]],
    *,
    export_dir: Path | str = DEFAULT_TERMINAL_HISTORY_EXPORT_DIR,
    query_start: datetime,
    query_end: datetime,
    ticket: Optional[str | int] = None,
    account_mode: str = "demo",
) -> Path:
    target_dir = Path(export_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    suffix = f"-ticket-{ticket}" if ticket is not None else ""
    export_path = target_dir / f"mt5-deal-history{suffix}-{stamp}.json"
    payload = {
        "schema": EXPORT_SCHEMA,
        "created_at": utc_now().isoformat(),
        "source": "MetaTrader5.history_deals_get",
        "query": {
            "start": query_start.isoformat(),
            "end": query_end.isoformat(),
            "ticket": str(ticket) if ticket is not None else None,
            "account_mode": _normalize_account_mode(account_mode),
        },
        "history_records": list(history_rows),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    export_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    return export_path


def load_latest_mt5_deal_history_ingest_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("mt5-deal-history-ingest-*-report.json"))
    if not files:
        raise MT5DealHistoryIngestError(f"No MT5 deal history ingest reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_mt5_deal_history_ingest_report(payload)
    return payload


def validate_mt5_deal_history_ingest_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "ingest_status",
        "schema",
        "query",
        "terminal_snapshot",
        "raw_deal_count",
        "history_records",
        "terminal_history_ingest",
        "summary",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise MT5DealHistoryIngestError(f"MT5 deal history ingest report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise MT5DealHistoryIngestError("unexpected MT5 deal history ingest report_kind")
    if payload.get("schema") != INGEST_SCHEMA:
        raise MT5DealHistoryIngestError("unexpected MT5 deal history ingest schema")
    if "does not place live broker orders" not in str(payload.get("claim_boundary", "")):
        raise MT5DealHistoryIngestError("MT5 deal history ingest claim boundary must preserve live-order boundary")
    if not isinstance(payload.get("history_records"), list):
        raise MT5DealHistoryIngestError("history_records must be a list")


def render_mt5_deal_history_ingest_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    terminal_ingest = report.get("terminal_history_ingest") or {}
    lines = [
        "# CAS Forex MT5 Deal History Ingest",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('ingest_status')}`",
        f"Query: `{report.get('query')}`",
        f"Export: `{report.get('history_export_path')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Account mode: `{summary.get('account_mode')}`",
        f"- Live history confirmed: `{summary.get('confirm_live_history')}`",
        f"- Terminal connected: `{summary.get('terminal_connected')}`",
        f"- Demo account confirmed: `{summary.get('demo_account_confirmed')}`",
        f"- Live account confirmed: `{summary.get('live_account_confirmed')}`",
        f"- Raw MT5 deals: `{summary.get('raw_deal_count')}`",
        f"- Closed positions: `{summary.get('closed_position_count')}`",
        f"- History rows: `{summary.get('history_record_count')}`",
        f"- Memory updates: `{summary.get('memory_update_count')}`",
        f"- Unmatched history rows: `{summary.get('unmatched_history_count')}`",
        f"- Closed win/loss/flat: `{summary.get('closed_profit_count')}` / `{summary.get('closed_loss_count')}` / `{summary.get('closed_flat_count')}`",
        f"- Net closed P/L: `{summary.get('net_profit_loss_account')}`",
        f"- Total commission: `{summary.get('total_commission')}`",
        f"- Total swap: `{summary.get('total_swap')}`",
        "",
        "## Terminal History Join",
        "",
        f"- Ingest status: `{terminal_ingest.get('ingest_status')}`",
        f"- Report path: `{terminal_ingest.get('report_path')}`",
        "",
        f"Next action: {report.get('next_action')}",
    ]
    return "\n".join(lines) + "\n"


def _add_local_mt5_deps() -> None:
    if LOCAL_MT5_DEPS.exists():
        path = str(LOCAL_MT5_DEPS)
        if path not in sys.path:
            sys.path.insert(0, path)


def _import_mt5() -> Any | None:
    try:
        import MetaTrader5 as mt5  # type: ignore

        return mt5
    except ImportError:
        return None


def _query_window(
    *,
    start: Optional[datetime | str],
    end: Optional[datetime | str],
    days_back: int,
    future_minutes: int,
) -> tuple[datetime, datetime]:
    query_end = _parse_datetime(end) if end is not None else utc_now() + timedelta(minutes=max(int(future_minutes), 0))
    query_start = _parse_datetime(start) if start is not None else query_end - timedelta(days=max(int(days_back), 1))
    return query_start, query_end


def _normalize_account_mode(value: str) -> str:
    mode = str(value or "demo").strip().lower()
    if mode in {"demo", "paper", "paper_demo"}:
        return "demo"
    if mode == "live":
        return "live"
    raise MT5DealHistoryIngestError("account_mode must be 'demo' or 'live'")


def _should_fetch_deals(
    terminal_snapshot: Mapping[str, Any],
    *,
    account_mode: str,
    confirm_live_history: bool,
) -> bool:
    if account_mode == "live":
        return bool(confirm_live_history) and bool(terminal_snapshot.get("live_account_confirmed"))
    return bool(terminal_snapshot.get("demo_account_confirmed"))


def _parse_datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    raw = str(value).strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _terminal_snapshot(*, mt5: Any | None, mt5_path: Optional[Path | str]) -> Dict[str, Any]:
    if mt5 is None:
        return {
            "mt5_package_available": False,
            "initialize_ok": False,
            "terminal": {},
            "account": {},
            "demo_account_confirmed": False,
            "live_account_confirmed": False,
        }
    kwargs: Dict[str, Any] = {}
    path = str(mt5_path or config.mt5_path or "")
    if path:
        kwargs["path"] = path
    try:
        terminal = _object_to_dict(mt5.terminal_info())
        if not terminal or not bool(terminal.get("connected")):
            mt5_connect_guard.guarded_initialize(mt5, **kwargs)
            terminal = _object_to_dict(mt5.terminal_info())
        account = _object_to_dict(mt5.account_info())
        demo_confirmed = _is_demo_account(mt5, account)
        return {
            "mt5_package_available": True,
            "initialize_ok": bool(terminal),
            "terminal": _terminal_info_snapshot(terminal),
            "account": _redacted_account_snapshot(account),
            "demo_account_confirmed": demo_confirmed,
            "live_account_confirmed": bool(account) and not demo_confirmed,
        }
    except Exception as exc:
        return {
            "mt5_package_available": True,
            "initialize_ok": False,
            "error_type": type(exc).__name__,
            "message": str(exc),
            "terminal": {},
            "account": {},
            "demo_account_confirmed": False,
            "live_account_confirmed": False,
        }


def _fetch_deals(
    *,
    mt5: Any | None,
    start: datetime,
    end: datetime,
    ticket: Optional[str | int],
    symbol: Optional[str],
    server_offset_seconds: int = 0,
) -> List[Dict[str, Any]]:
    if mt5 is None:
        return []
    group = _mt5_group(symbol)
    try:
        method = getattr(mt5, "history_deals_get", None)
        if method is None:
            return []
        try:
            deals = method(start, end, group=group) or []
        except TypeError:
            deals = method(start, end) or []
    except Exception:
        return []
    snapshots = [
        _deal_snapshot(deal, server_offset_seconds=server_offset_seconds)
        for deal in deals
    ]
    if ticket is None:
        return snapshots
    wanted = str(ticket)
    return [
        deal
        for deal in snapshots
        if wanted
        in {
            str(deal.get("ticket")),
            str(deal.get("order")),
            str(deal.get("position_id")),
        }
    ]


def _mt5_server_time_normalization(
    *,
    mt5: Any | None,
    symbol: Optional[str],
    enabled: bool,
) -> Dict[str, Any]:
    """Detect broker-server-local epochs before querying deal history."""

    now = utc_now()
    if not enabled or mt5 is None:
        return {
            "status": "NOT_REQUIRED",
            "probe_symbol": None,
            "raw_tick_time": None,
            "raw_tick_time_iso": None,
            "normalized_tick_time_iso": None,
            "server_utc_offset_seconds": 0,
        }

    candidates: List[str] = []
    if symbol:
        compact = str(symbol).strip().upper().replace("/", "").replace(".", "")
        if compact:
            candidates.append(compact)
    candidates.extend(_CLOCK_PROBE_SYMBOLS)
    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            tick = mt5.symbol_info_tick(candidate)
            raw_seconds = _to_float(getattr(tick, "time", None))
        except Exception:
            continue
        if raw_seconds is None or raw_seconds <= 0:
            continue
        offset_seconds = infer_mt5_future_server_offset_seconds(
            raw_seconds,
            now_epoch=now.timestamp(),
        )
        raw_delta = raw_seconds - now.timestamp()
        if offset_seconds or abs(raw_delta) <= 300:
            normalized_seconds = raw_seconds - offset_seconds
            return {
                "status": (
                    "BROKER_SERVER_OFFSET_CORRECTED"
                    if offset_seconds
                    else "MT5_EPOCH_UTC_UNCHANGED"
                ),
                "probe_symbol": candidate,
                "raw_tick_time": raw_seconds,
                "raw_tick_time_iso": datetime.fromtimestamp(raw_seconds, tz=timezone.utc).isoformat(),
                "normalized_tick_time_iso": datetime.fromtimestamp(
                    normalized_seconds,
                    tz=timezone.utc,
                ).isoformat(),
                "server_utc_offset_seconds": int(offset_seconds),
            }

    return {
        "status": "SERVER_TIME_OFFSET_UNAVAILABLE",
        "probe_symbol": None,
        "raw_tick_time": None,
        "raw_tick_time_iso": None,
        "normalized_tick_time_iso": None,
        "server_utc_offset_seconds": 0,
    }


def _mt5_group(symbol: Optional[str]) -> str:
    if not symbol:
        return "*"
    return str(symbol).strip().upper().replace("/", "").replace(".", "")


def _closed_history_rows(
    raw_deals: Sequence[Mapping[str, Any]],
    *,
    account: Mapping[str, Any],
    ticket: Optional[str | int],
    broker_mode: str = "PAPER_MT5",
) -> List[Dict[str, Any]]:
    trade_deals = [
        dict(deal)
        for deal in raw_deals
        if _to_int(deal.get("type")) in {0, 1} and deal.get("symbol")
    ]
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for deal in trade_deals:
        key = str(deal.get("position_id") or deal.get("order") or deal.get("ticket"))
        groups[key].append(deal)

    rows: List[Dict[str, Any]] = []
    for group_key, deals in groups.items():
        deals = sorted(deals, key=lambda item: (_to_float(item.get("time")) or 0.0, _to_float(item.get("time_msc")) or 0.0, str(item.get("ticket"))))
        entry_deals = [deal for deal in deals if _is_entry_deal(deal)]
        close_deals = [deal for deal in deals if _is_close_deal(deal)]
        if not close_deals:
            continue
        open_deal = entry_deals[0] if entry_deals else deals[0]
        close_deal = close_deals[-1]
        position_id = str(open_deal.get("position_id") or close_deal.get("position_id") or group_key)
        if ticket is not None and str(ticket) != position_id and str(ticket) not in {str(deal.get("ticket")) for deal in deals} and str(ticket) not in {str(deal.get("order")) for deal in deals}:
            continue
        gross_profit = sum(_to_float(deal.get("profit")) or 0.0 for deal in deals)
        commission = sum((_to_float(deal.get("commission")) or 0.0) + (_to_float(deal.get("fee")) or 0.0) for deal in deals)
        swap = sum(_to_float(deal.get("swap")) or 0.0 for deal in deals)
        net_profit = gross_profit + commission + swap
        rows.append(
            {
                "ticket": position_id,
                "broker_ticket": position_id,
                "deal_ticket": close_deal.get("ticket"),
                "order": close_deal.get("order"),
                "position_id": position_id,
                "symbol": _display_symbol(str(open_deal.get("symbol") or close_deal.get("symbol") or "")),
                "direction": _position_direction(open_deal, close_deal),
                "lots": _to_float(open_deal.get("volume")) or _closed_volume(close_deals),
                "open_time": open_deal.get("time_iso"),
                "close_time": close_deal.get("time_iso"),
                "open_price": _to_float(open_deal.get("price")),
                "close_price": _to_float(close_deal.get("price")),
                "profit": round(net_profit, 6),
                "gross_profit": round(gross_profit, 6),
                "commission": round(commission, 6),
                "swap": round(swap, 6),
                "close_reason": _close_reason(close_deal),
                "comment": close_deal.get("comment") or open_deal.get("comment"),
                "magic": close_deal.get("magic") or open_deal.get("magic"),
                "account_currency": account.get("currency") or "USD",
                "broker_mode": broker_mode,
                "source_row": {
                    "group_key": group_key,
                    "deal_tickets": [deal.get("ticket") for deal in deals],
                    "entry_deal_ticket": open_deal.get("ticket"),
                    "close_deal_ticket": close_deal.get("ticket"),
                    "gross_profit": round(gross_profit, 6),
                    "net_profit": round(net_profit, 6),
                },
            }
        )
    return rows


def _summary(
    *,
    terminal_snapshot: Mapping[str, Any],
    raw_deals: Sequence[Mapping[str, Any]],
    history_rows: Sequence[Mapping[str, Any]],
    terminal_history_report: Mapping[str, Any],
    export_path: Optional[Path],
    ticket: Optional[str | int],
    account_mode: str,
    confirm_live_history: bool,
    time_normalization: Mapping[str, Any],
) -> Dict[str, Any]:
    terminal = terminal_snapshot.get("terminal") if isinstance(terminal_snapshot.get("terminal"), Mapping) else {}
    account = terminal_snapshot.get("account") if isinstance(terminal_snapshot.get("account"), Mapping) else {}
    history_summary = terminal_history_report.get("summary") if isinstance(terminal_history_report.get("summary"), Mapping) else {}
    pnl_values = [_to_float(row.get("profit")) or 0.0 for row in history_rows]
    return {
        "mt5_package_available": bool(terminal_snapshot.get("mt5_package_available")),
        "initialize_ok": bool(terminal_snapshot.get("initialize_ok")),
        "terminal_connected": bool(terminal.get("connected")),
        "terminal_name": terminal.get("name"),
        "terminal_trade_allowed": terminal.get("trade_allowed"),
        "server": account.get("server"),
        "account_mode": account_mode,
        "confirm_live_history": bool(confirm_live_history),
        "time_normalization_status": time_normalization.get("status"),
        "server_utc_offset_seconds": int(
            time_normalization.get("server_utc_offset_seconds") or 0
        ),
        "demo_account_confirmed": bool(terminal_snapshot.get("demo_account_confirmed")),
        "live_account_confirmed": bool(terminal_snapshot.get("live_account_confirmed")),
        "account_snapshot_present": bool(account),
        "account_balance": account.get("balance"),
        "account_equity": account.get("equity"),
        "account_currency": account.get("currency"),
        "ticket_filter": str(ticket) if ticket is not None else None,
        "raw_deal_count": len(raw_deals),
        "closed_position_count": len(history_rows),
        "history_record_count": _int_summary(history_summary, "history_record_count", len(history_rows)),
        "memory_update_count": _int_summary(history_summary, "memory_update_count", 0),
        "unmatched_history_count": _int_summary(history_summary, "unmatched_history_count", len(history_rows)),
        "closed_trade_count": _int_summary(history_summary, "closed_trade_count", len(history_rows)),
        "closed_profit_count": sum(1 for value in pnl_values if value > 0),
        "closed_loss_count": sum(1 for value in pnl_values if value < 0),
        "closed_flat_count": sum(1 for value in pnl_values if value == 0),
        "net_profit_loss_account": round(sum(pnl_values), 6),
        "total_commission": round(sum(_to_float(row.get("commission")) or 0.0 for row in history_rows), 6),
        "total_swap": round(sum(_to_float(row.get("swap")) or 0.0 for row in history_rows), 6),
        "history_export_path": str(export_path) if export_path is not None else None,
        "terminal_history_ingest_status": terminal_history_report.get("ingest_status"),
        "terminal_history_report_path": ((terminal_history_report.get("artifact_paths") or {}) or {}).get("json") or terminal_history_report.get("report_path"),
    }


def _ingest_status(summary: Mapping[str, Any]) -> str:
    if not summary.get("mt5_package_available"):
        return "MT5_DEAL_HISTORY_PACKAGE_MISSING"
    if not summary.get("terminal_connected"):
        return "MT5_DEAL_HISTORY_TERMINAL_DISCONNECTED"
    if summary.get("account_mode") == "live":
        if not summary.get("confirm_live_history"):
            return "MT5_DEAL_HISTORY_LIVE_CONFIRM_REQUIRED"
        if summary.get("demo_account_confirmed"):
            return "MT5_DEAL_HISTORY_BLOCKED_DEMO_ACCOUNT_FOR_LIVE"
        if not summary.get("live_account_confirmed"):
            return "MT5_DEAL_HISTORY_BLOCKED_LIVE_ACCOUNT_UNCONFIRMED"
        if int(summary.get("raw_deal_count") or 0) == 0:
            return "MT5_LIVE_DEAL_HISTORY_EMPTY"
        if int(summary.get("history_record_count") or 0) == 0:
            return "MT5_LIVE_DEAL_HISTORY_NO_CLOSED_POSITIONS"
        if int(summary.get("memory_update_count") or 0) > 0:
            return "MT5_LIVE_DEAL_HISTORY_JOINED_TO_MEMORY"
        return "MT5_LIVE_DEAL_HISTORY_EXPORTED_UNMATCHED"
    if not summary.get("demo_account_confirmed"):
        return "MT5_DEAL_HISTORY_BLOCKED_NON_DEMO_ACCOUNT"
    if int(summary.get("raw_deal_count") or 0) == 0:
        return "MT5_DEAL_HISTORY_EMPTY"
    if int(summary.get("history_record_count") or 0) == 0:
        return "MT5_DEAL_HISTORY_NO_CLOSED_POSITIONS"
    if int(summary.get("memory_update_count") or 0) > 0:
        return "MT5_DEAL_HISTORY_JOINED_TO_MEMORY"
    return "MT5_DEAL_HISTORY_EXPORTED_UNMATCHED"


def _int_summary(summary: Mapping[str, Any], key: str, default: int) -> int:
    value = summary.get(key)
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _next_action(status: str, summary: Mapping[str, Any]) -> str:
    if status == "MT5_DEAL_HISTORY_PACKAGE_MISSING":
        return "Install the MetaTrader5 Python package into .mt5deps, then rerun MT5 deal history ingest."
    if status == "MT5_DEAL_HISTORY_TERMINAL_DISCONNECTED":
        return "Open/log into MetaTrader 5, set CAS_FOREX_MT5_PATH if needed, then rerun MT5 deal history ingest."
    if status == "MT5_DEAL_HISTORY_BLOCKED_NON_DEMO_ACCOUNT":
        return "Log into an MT5 demo account before reading this paper/demo deal-history lane."
    if status == "MT5_DEAL_HISTORY_LIVE_CONFIRM_REQUIRED":
        return "Live account history is read-only evidence, but it still requires explicit --live-history --confirm-live-history before CAS reads live closed deals."
    if status == "MT5_DEAL_HISTORY_BLOCKED_DEMO_ACCOUNT_FOR_LIVE":
        return "The terminal is on a demo account; use the default demo history lane or log into the owner-approved live account before live-history ingest."
    if status == "MT5_DEAL_HISTORY_BLOCKED_LIVE_ACCOUNT_UNCONFIRMED":
        return "CAS could not confirm a live account snapshot. Check the terminal account/server before live-history ingest."
    if status == "MT5_LIVE_DEAL_HISTORY_EMPTY":
        return "No live MT5 deals were returned for the query window. Broaden --days-back or rerun after a live trade closes."
    if status == "MT5_LIVE_DEAL_HISTORY_NO_CLOSED_POSITIONS":
        return "Live MT5 deals were present, but no closed position groups were found. Check the query window or ticket filter."
    if status == "MT5_LIVE_DEAL_HISTORY_JOINED_TO_MEMORY":
        return "Live closed-deal history joined CAS memory. Review the verified-profit sweep cockpit before any owner-confirmed payout action."
    if status == "MT5_LIVE_DEAL_HISTORY_EXPORTED_UNMATCHED":
        return "Live closed-deal history was exported. Add/retain broker_ticket, command_id, receipt_id, or a verifier memory row so it can join strategy memory."
    if status == "MT5_DEAL_HISTORY_EMPTY":
        return "No MT5 deals were returned for the query window. Broaden --days-back or run after a demo order closes."
    if status == "MT5_DEAL_HISTORY_NO_CLOSED_POSITIONS":
        return "MT5 deals were present, but no closed position groups were found. Check the query window or ticket filter."
    if status == "MT5_DEAL_HISTORY_JOINED_TO_MEMORY":
        return "MT5 closed-deal history joined CAS memory. Rerun agent memory, strategy-dev queue, daily learning rollup, and terminal operability."
    if status == "MT5_DEAL_HISTORY_EXPORTED_UNMATCHED":
        return "MT5 closed-deal history was exported, but no CAS memory row matched it. Add/retain broker_ticket, command_id, receipt_id, or a verifier memory row, then rerun memory and strategy learning."
    return "Inspect the MT5 deal-history ingest report and rerun after resolving the first missing item."


def _operator_commands(mt5_path: Optional[Path | str]) -> Dict[str, str]:
    path = str(mt5_path or config.mt5_path or "<MT5_TERMINAL64_EXE>")
    return {
        "mt5_deal_history_ingest": f'py -3.12 scripts/run_mt5_deal_history_ingest.py --mt5-path "{path}" --days-back 7 --summary-only',
        "mt5_live_deal_history_ingest": f'py -3.12 scripts/run_mt5_deal_history_ingest.py --mt5-path "{path}" --live-history --confirm-live-history --days-back 7 --summary-only',
        "terminal_history_ingest": "py -3.12 scripts/run_terminal_history_ingest.py --summary-only",
        "agent_memory": "py -3.12 scripts/run_agent_memory.py",
        "daily_learning_rollup": "py -3.12 scripts/run_daily_learning_rollup.py --summary-only",
        "operability_refresh": "py -3.12 scripts/run_terminal_operability_verifier.py --summary-only",
    }


def _compact_terminal_history_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    if not report:
        return {}
    return {
        "report_kind": report.get("report_kind"),
        "ingest_status": report.get("ingest_status"),
        "schema": report.get("schema"),
        "summary": report.get("summary") or {},
        "artifact_paths": report.get("artifact_paths") or {},
        "report_path": report.get("report_path"),
        "next_action": report.get("next_action"),
    }


def _deal_snapshot(deal: Any, *, server_offset_seconds: int = 0) -> Dict[str, Any]:
    payload = _object_to_dict(deal)
    out: Dict[str, Any] = {}
    for key in (
        "ticket",
        "order",
        "time",
        "time_msc",
        "type",
        "entry",
        "magic",
        "position_id",
        "reason",
        "volume",
        "price",
        "commission",
        "swap",
        "profit",
        "fee",
        "symbol",
        "comment",
        "external_id",
    ):
        out[key] = payload.get(key)
    raw_time = _to_float(out.get("time"))
    raw_time_msc = _to_float(out.get("time_msc"))
    out["time_raw"] = raw_time
    out["time_msc_raw"] = raw_time_msc
    if raw_time is not None:
        out["time"] = raw_time - int(server_offset_seconds)
    if raw_time_msc is not None:
        out["time_msc"] = raw_time_msc - (int(server_offset_seconds) * 1000)
    out["time_iso_raw"] = _deal_time_iso({"time": raw_time})
    out["time_iso"] = _deal_time_iso(out)
    out["timestamp_basis"] = (
        "mt5_broker_server_epoch_normalized_to_host_utc"
        if server_offset_seconds
        else "mt5_epoch_utc"
    )
    out["mt5_server_utc_offset_seconds"] = int(server_offset_seconds)
    out["raw_sha256"] = _sha256_json(payload)
    return out


def _deal_time_iso(deal: Mapping[str, Any]) -> Optional[str]:
    seconds = _to_float(deal.get("time"))
    if seconds is None:
        return None
    try:
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _is_entry_deal(deal: Mapping[str, Any]) -> bool:
    return _to_int(deal.get("entry")) in {0}


def _is_close_deal(deal: Mapping[str, Any]) -> bool:
    entry = _to_int(deal.get("entry"))
    if entry in {1, 2, 3}:
        return True
    return (_to_float(deal.get("profit")) or 0.0) != 0.0 and not _is_entry_deal(deal)


def _position_direction(open_deal: Mapping[str, Any], close_deal: Mapping[str, Any]) -> str:
    open_type = _to_int(open_deal.get("type"))
    if open_type == 0:
        return "buy"
    if open_type == 1:
        return "sell"
    close_type = _to_int(close_deal.get("type"))
    if close_type == 1:
        return "buy"
    if close_type == 0:
        return "sell"
    return "unknown"


def _closed_volume(close_deals: Sequence[Mapping[str, Any]]) -> float:
    return round(sum(_to_float(deal.get("volume")) or 0.0 for deal in close_deals), 6)


def _close_reason(close_deal: Mapping[str, Any]) -> str:
    comment = str(close_deal.get("comment") or "").strip()
    reason = close_deal.get("reason")
    if comment:
        return f"MT5_HISTORY_CLOSE:{comment}"
    return f"MT5_HISTORY_CLOSE_REASON_{reason}" if reason is not None else "MT5_HISTORY_CLOSE"


def _display_symbol(value: str) -> str:
    raw = value.strip().upper().replace(".", "").replace("/", "")
    if len(raw) == 6 and raw.isalpha():
        return f"{raw[:3]}/{raw[3:]}"
    if raw == "XAUUSD":
        return "XAU/USD"
    return value.strip().upper()


def _terminal_info_snapshot(terminal: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "connected": bool(terminal.get("connected")),
        "name": terminal.get("name"),
        "path": terminal.get("path"),
        "data_path": terminal.get("data_path"),
        "trade_allowed": terminal.get("trade_allowed"),
        "build": terminal.get("build"),
    }


def _redacted_account_snapshot(account: Mapping[str, Any]) -> Dict[str, Any]:
    if not account:
        return {}

    def number(key: str) -> float | None:
        value = account.get(key)
        if value is None:
            return None
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return None

    return {
        "account_id_hash": _sha256_json({"login": account.get("login"), "server": account.get("server")}),
        "server": account.get("server"),
        "company": account.get("company"),
        "currency": account.get("currency"),
        "balance": number("balance"),
        "equity": number("equity"),
        "margin": number("margin"),
        "margin_free": number("margin_free"),
        "leverage": account.get("leverage"),
        "trade_mode": account.get("trade_mode"),
    }


def _is_demo_account(mt5: Any, account: Mapping[str, Any]) -> bool:
    demo_const = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
    if demo_const is not None and account.get("trade_mode") == demo_const:
        return True
    server = str(account.get("server") or "").lower()
    company = str(account.get("company") or "").lower()
    return "demo" in server or "demo" in company


def _object_to_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "_asdict"):
        return dict(value._asdict())
    data: Dict[str, Any] = {}
    for key in dir(value):
        if key.startswith("_"):
            continue
        try:
            attr = getattr(value, key)
        except Exception:
            continue
        if callable(attr):
            continue
        if isinstance(attr, (str, int, float, bool, type(None))):
            data[key] = attr
    return data


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _sha256_json(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
