"""Terminal close/history ingest for CAS Forex agent memory.

Receipt ingest tells CAS Forex that the terminal accepted a command. This
module handles the next layer: closed trade/history rows. It normalizes MT4/MT5
CSV, HTML, text, or JSON exports and joins them back to agent memory by
command id, receipt id, broker ticket, or a tight symbol/price/lot fallback.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from cas_forex.instruments import pip_multiplier
from cas_forex.mt_history_import import import_mt_history
from cas_forex.time_utils import utc_now


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = REPO_ROOT / "evidence_runs" / "terminal_history_exports"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "terminal_history_ingest"
REPORT_KIND = "cas_forex_terminal_history_ingest"
HISTORY_SCHEMA = "cas_forex_terminal_history_record.v1"
CLAIM_BOUNDARY = (
    "Terminal history ingest normalizes paper/demo MT4/MT5 close-history "
    "exports and joins them to CAS Forex memory rows. It does not by itself "
    "execute live broker orders, create broker ACCEPT, deposit, withdraw, move "
    "bank/card funds, or automate payouts."
)


class TerminalHistoryIngestError(ValueError):
    """Raised when terminal history cannot be normalized or loaded."""


def ingest_terminal_history(
    *,
    source_paths: Optional[Sequence[Path | str]] = None,
    memory_report: Optional[Mapping[str, Any]] = None,
    memory_report_dir: Optional[Path | str] = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    write_report: bool = True,
) -> Dict[str, Any]:
    """Normalize terminal history rows, join to memory, and write evidence."""

    if memory_report is None:
        try:
            from cas_forex.agent_memory import load_latest_agent_memory_report

            if memory_report_dir is None:
                memory_report = load_latest_agent_memory_report()
            else:
                memory_report = load_latest_agent_memory_report(memory_report_dir)
        except Exception:
            memory_report = None

    paths = _resolve_source_paths(source_paths)
    records: List[Dict[str, Any]] = []
    for path in paths:
        records.extend(_records_from_source(path))
    for record in records:
        validate_terminal_history_record(record)

    memory_records = list((memory_report or {}).get("memory_records") or [])
    memory_updates, unmatched_records = join_history_to_memory(records, memory_records)
    summary = _summary(records, memory_updates, unmatched_records, memory_report)
    report = {
        "report_kind": REPORT_KIND,
        "created_at": utc_now().isoformat(),
        "ingest_status": _ingest_status(records),
        "schema": HISTORY_SCHEMA,
        "source_paths": [str(path) for path in paths],
        "memory_report_path": (memory_report or {}).get("report_path")
        or ((memory_report or {}).get("artifact_paths") or {}).get("json"),
        "output_dir": str(Path(output_dir)),
        "summary": summary,
        "history_records": records,
        "memory_updates": memory_updates,
        "unmatched_history_records": unmatched_records,
        "claim_boundary": CLAIM_BOUNDARY,
        "next_action": _next_action(summary),
    }
    if write_report:
        written = write_terminal_history_ingest_report(report, output_dir=output_dir)
        report["artifact_paths"] = {key: str(path) for key, path in written.items()}
    validate_terminal_history_ingest_report(report)
    return report


def join_history_to_memory(
    history_records: Sequence[Mapping[str, Any]],
    memory_records: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return memory update packets plus unmatched history rows."""

    updates: List[Dict[str, Any]] = []
    unmatched: List[Dict[str, Any]] = []
    claimed_memory_ids: set[str] = set()
    for history in history_records:
        memory, match_method = _best_memory_match(history, memory_records, claimed_memory_ids)
        if memory is None:
            unmatched.append(dict(history))
            continue
        claimed_memory_ids.add(str(memory.get("memory_id")))
        update = _memory_update(history, memory, match_method)
        updates.append(update)
    return updates, unmatched


def write_terminal_history_ingest_report(
    report: Mapping[str, Any],
    *,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    validate_terminal_history_ingest_report(report)
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"terminal-history-ingest-{stamp}-report.json"
    md_path = target_dir / f"terminal-history-ingest-{stamp}-report.md"
    jsonl_path = target_dir / f"terminal-history-ingest-{stamp}.jsonl"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_terminal_history_ingest_markdown(report), encoding="utf-8")
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in report.get("history_records") or []:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    return {"json": json_path, "markdown": md_path, "jsonl": jsonl_path}


def load_latest_terminal_history_ingest_report(report_dir: Path | str = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    files = sorted(Path(report_dir).glob("terminal-history-ingest-*-report.json"))
    if not files:
        raise TerminalHistoryIngestError(f"No terminal history ingest reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    payload["report_path"] = str(files[-1])
    validate_terminal_history_ingest_report(payload)
    return payload


def validate_terminal_history_ingest_report(payload: Mapping[str, Any]) -> None:
    required = {
        "report_kind",
        "created_at",
        "ingest_status",
        "schema",
        "summary",
        "history_records",
        "memory_updates",
        "unmatched_history_records",
        "claim_boundary",
        "next_action",
    }
    missing = required.difference(payload)
    if missing:
        raise TerminalHistoryIngestError(f"terminal history ingest report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != REPORT_KIND:
        raise TerminalHistoryIngestError("unexpected terminal history ingest report_kind")
    if payload.get("schema") != HISTORY_SCHEMA:
        raise TerminalHistoryIngestError("unexpected terminal history ingest schema")
    if "does not by itself execute live broker orders" not in str(payload.get("claim_boundary", "")):
        raise TerminalHistoryIngestError("terminal history ingest claim boundary must preserve execution boundary")
    for record in payload.get("history_records") or []:
        validate_terminal_history_record(record)


def validate_terminal_history_record(record: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "history_id",
        "source_path",
        "symbol",
        "direction",
        "lots",
        "profit_loss_account",
        "commission",
        "swap",
        "claim_boundary",
    }
    missing = required.difference(record)
    if missing:
        raise TerminalHistoryIngestError(f"terminal history record missing fields: {sorted(missing)}")
    if record.get("schema") != HISTORY_SCHEMA:
        raise TerminalHistoryIngestError("unexpected terminal history record schema")
    if "does not by itself execute live broker orders" not in str(record.get("claim_boundary", "")):
        raise TerminalHistoryIngestError("terminal history record claim boundary must preserve execution boundary")


def render_terminal_history_ingest_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Terminal History Ingest",
        "",
        f"Created: `{report.get('created_at')}`",
        f"Status: `{report.get('ingest_status')}`",
        f"Sources: `{report.get('source_paths')}`",
        f"Memory report: `{report.get('memory_report_path')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- History rows: `{summary.get('history_record_count')}`",
        f"- Memory updates: `{summary.get('memory_update_count')}`",
        f"- Unmatched rows: `{summary.get('unmatched_history_count')}`",
        f"- Closed profit rows: `{summary.get('closed_profit_count')}`",
        f"- Closed loss rows: `{summary.get('closed_loss_count')}`",
        f"- Net PnL: `{summary.get('net_profit_loss_account')}`",
        "",
        "## Memory Updates",
        "",
    ]
    for update in report.get("memory_updates") or []:
        lines.append(
            "- "
            f"`{update.get('memory_id')}` history `{update.get('history_id')}` "
            f"pnl `{update.get('profit_loss_account')}` pips `{update.get('profit_loss_pips')}` "
            f"match `{update.get('match_method')}`"
        )
    lines.extend(["", f"Next action: {report.get('next_action')}"])
    return "\n".join(lines) + "\n"


def _resolve_source_paths(source_paths: Optional[Sequence[Path | str]]) -> List[Path]:
    if source_paths:
        candidates = [Path(path) for path in source_paths]
    else:
        candidates = []
        for directory in (DEFAULT_SOURCE_DIR, REPO_ROOT / "evidence_runs" / "mt_history_import"):
            if directory.exists():
                candidates.append(directory)
    files: List[Path] = []
    for candidate in candidates:
        if candidate.is_dir():
            for pattern in ("*.json", "*.csv", "*.txt", "*.html", "*.htm"):
                files.extend(sorted(candidate.glob(pattern)))
        elif candidate.exists():
            files.append(candidate)
    return sorted(dict.fromkeys(files))


def _records_from_source(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = _json_rows(payload)
    else:
        report = import_mt_history(path)
        rows = report.get("trades") or []
    return [
        _normalize_history_row(row, source_path=path)
        for row in rows
        if isinstance(row, Mapping)
    ]


def _json_rows(payload: Any) -> List[Mapping[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, Mapping)]
    if not isinstance(payload, Mapping):
        return []
    for key in ("history_records", "trades", "deals", "orders"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, Mapping)]
    return [payload]


def _normalize_history_row(row: Mapping[str, Any], *, source_path: Path) -> Dict[str, Any]:
    normalized = {_norm_key(key): value for key, value in row.items()}
    source_row = row.get("source_row")
    if isinstance(source_row, Mapping):
        normalized = {**{_norm_key(key): value for key, value in source_row.items()}, **normalized}
    ticket = _first_text(normalized, "ticket", "order", "deal", "position", "id", "brokerticket", "broker_ticket")
    command_id = _extract_command_id(normalized)
    receipt_id = _first_text(normalized, "receiptid", "receipt_id")
    symbol = _normalize_symbol(_first_text(normalized, "symbol", "item", "instrument"))
    direction = _normalize_direction(_first_text(normalized, "direction", "side", "type"))
    lots = _first_number(normalized, "lots", "lot", "size", "volume") or 0.0
    open_price = _first_number(normalized, "openprice", "entryprice", "priceopen", "open_price")
    close_price = _first_number(normalized, "closeprice", "exitprice", "priceclose", "close_price")
    profit_loss_account = _first_number(normalized, "profitlossaccount", "profit_loss_account", "profit", "pl", "pnl", "netpnl") or 0.0
    explicit_pips = _first_number(normalized, "profitlosspips", "profit_loss_pips", "pips")
    profit_loss_pips = explicit_pips if explicit_pips is not None else _profit_pips(symbol, direction, open_price, close_price)
    record = {
        "schema": HISTORY_SCHEMA,
        "history_id": _history_id(str(source_path), ticket, command_id, symbol, open_price, close_price, profit_loss_account),
        "source_path": str(source_path),
        "source_sha256": _file_sha256(source_path),
        "ticket": ticket,
        "broker_ticket": ticket,
        "command_id": command_id,
        "receipt_id": receipt_id,
        "symbol": symbol or "UNKNOWN",
        "direction": direction or "UNKNOWN",
        "lots": lots,
        "opened_at": _first_text(normalized, "opentime", "openedat", "open_time", "time", "open"),
        "closed_at": _first_text(normalized, "closetime", "closedat", "close_time", "close"),
        "open_price": open_price,
        "close_price": close_price,
        "stop_loss": _first_number(normalized, "sl", "s/l", "stoploss", "stop_loss"),
        "take_profit": _first_number(normalized, "tp", "t/p", "takeprofit", "take_profit"),
        "profit_loss_account": round(float(profit_loss_account), 6),
        "profit_loss_pips": round(float(profit_loss_pips), 6) if profit_loss_pips is not None else None,
        "profit_loss_r": _first_number(normalized, "profitlossr", "profit_loss_r", "rmultiple"),
        "mae": _first_number(normalized, "mae", "maxadverseexcursionpips", "max_adverse_excursion_pips"),
        "mfe": _first_number(normalized, "mfe", "maxfavorableexcursionpips", "max_favorable_excursion_pips"),
        "close_reason": _first_text(normalized, "closereason", "close_reason", "reason", "comment") or "TERMINAL_HISTORY_CLOSE",
        "commission": _first_number(normalized, "commission") or 0.0,
        "swap": _first_number(normalized, "swap") or 0.0,
        "account_currency": _first_text(normalized, "currency", "accountcurrency", "account_currency") or "USD",
        "broker_mode": _first_text(normalized, "brokermode", "broker_mode") or "PAPER_MT4",
        "raw_row": dict(row),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return record


def _best_memory_match(
    history: Mapping[str, Any],
    memory_records: Sequence[Mapping[str, Any]],
    claimed_memory_ids: set[str],
) -> Tuple[Optional[Mapping[str, Any]], Optional[str]]:
    for field, method in (("command_id", "command_id"), ("receipt_id", "receipt_id"), ("broker_ticket", "broker_ticket")):
        value = history.get(field)
        if not value:
            continue
        for memory in memory_records:
            if str(memory.get("memory_id")) in claimed_memory_ids:
                continue
            if value and str(memory.get(field) or "") == str(value):
                return memory, method
    for memory in memory_records:
        if str(memory.get("memory_id")) in claimed_memory_ids:
            continue
        if _fallback_match(history, memory):
            return memory, "symbol_direction_lots_entry"
    return None, None


def _fallback_match(history: Mapping[str, Any], memory: Mapping[str, Any]) -> bool:
    if str(history.get("symbol") or "") != str(memory.get("symbol") or ""):
        return False
    if _direction_for_match(history.get("direction")) != _direction_for_match(memory.get("direction")):
        return False
    open_snapshot = memory.get("condition_snapshot_open") or {}
    if not isinstance(open_snapshot, Mapping):
        return False
    lots = _to_float(history.get("lots"))
    memory_lots = _to_float(open_snapshot.get("lot_size"))
    entry = _to_float(history.get("open_price"))
    memory_entry = _to_float(open_snapshot.get("entry_price"))
    lots_match = lots is not None and memory_lots is not None and abs(lots - memory_lots) <= 1e-6
    entry_match = entry is not None and memory_entry is not None and abs(entry - memory_entry) <= 1e-4
    return lots_match and entry_match


def _memory_update(history: Mapping[str, Any], memory: Mapping[str, Any], match_method: Optional[str]) -> Dict[str, Any]:
    profit_loss_account = _to_float(history.get("profit_loss_account")) or 0.0
    profit_loss_pips = _to_float(history.get("profit_loss_pips"))
    profit_loss_r = _to_float(history.get("profit_loss_r"))
    if profit_loss_r is None:
        profit_loss_r = _profit_r_from_memory(memory, profit_loss_pips)
    return {
        "memory_id": memory.get("memory_id"),
        "history_id": history.get("history_id"),
        "command_id": memory.get("command_id") or history.get("command_id"),
        "receipt_id": memory.get("receipt_id") or history.get("receipt_id"),
        "broker_ticket": memory.get("broker_ticket") or history.get("broker_ticket"),
        "symbol": memory.get("symbol") or history.get("symbol"),
        "timeframe": memory.get("timeframe"),
        "match_method": match_method,
        "terminal_history_status": "CLOSED_HISTORY_JOINED",
        "profit_loss_account": profit_loss_account,
        "profit_loss_pips": profit_loss_pips,
        "profit_loss_r": round(profit_loss_r, 6) if profit_loss_r is not None else None,
        "mae": history.get("mae"),
        "mfe": history.get("mfe"),
        "close_reason": history.get("close_reason"),
        "commission": history.get("commission"),
        "swap": history.get("swap"),
        "closed_at": history.get("closed_at"),
        "exit_price": history.get("close_price"),
        "outcome_label": _closed_outcome_label(profit_loss_account),
        "promotion_signal": _closed_promotion_signal(profit_loss_account),
        "demotion_flags": ["closed_trade_loss"] if profit_loss_account < 0 else [],
        "source_path": history.get("source_path"),
        "source_sha256": history.get("source_sha256"),
    }


def _summary(
    records: Sequence[Mapping[str, Any]],
    updates: Sequence[Mapping[str, Any]],
    unmatched_records: Sequence[Mapping[str, Any]],
    memory_report: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    pnl_values = [_to_float(update.get("profit_loss_account")) or 0.0 for update in updates]
    return {
        "history_record_count": len(records),
        "memory_update_count": len(updates),
        "unmatched_history_count": len(unmatched_records),
        "closed_trade_count": len(updates),
        "closed_profit_count": sum(1 for value in pnl_values if value > 0),
        "closed_loss_count": sum(1 for value in pnl_values if value < 0),
        "closed_flat_count": sum(1 for value in pnl_values if value == 0),
        "net_profit_loss_account": round(sum(pnl_values), 6),
        "total_commission": round(sum(_to_float(update.get("commission")) or 0.0 for update in updates), 6),
        "total_swap": round(sum(_to_float(update.get("swap")) or 0.0 for update in updates), 6),
        "pnl_ready_memory_count": sum(1 for update in updates if update.get("profit_loss_account") is not None),
        "mae_ready_count": sum(1 for update in updates if update.get("mae") is not None),
        "mfe_ready_count": sum(1 for update in updates if update.get("mfe") is not None),
        "source_memory_count": int(((memory_report or {}).get("summary") or {}).get("memory_record_count", 0) or 0),
        "source_pending_receipt_count": int(((memory_report or {}).get("summary") or {}).get("pending_receipt_count", 0) or 0),
    }


def _next_action(summary: Mapping[str, Any]) -> str:
    if int(summary.get("history_record_count", 0) or 0) == 0:
        return "Export MT4/MT5 account history or provide terminal history JSON/CSV so closed trades can join memory."
    if int(summary.get("unmatched_history_count", 0) or 0) > 0:
        return "Add command_id, receipt_id, broker_ticket, or CAS comment fields so unmatched terminal history rows can join memory."
    if int(summary.get("memory_update_count", 0) or 0) > 0:
        return "Rerun agent memory so closed-trade PnL fields become durable memory rows."
    return "No terminal history memory updates were produced."


def _ingest_status(records: Sequence[Mapping[str, Any]]) -> str:
    return "TERMINAL_HISTORY_INGEST_COMPLETE" if records else "TERMINAL_HISTORY_EMPTY"


def _profit_r_from_memory(memory: Mapping[str, Any], profit_loss_pips: Optional[float]) -> Optional[float]:
    if profit_loss_pips is None:
        return None
    open_snapshot = memory.get("condition_snapshot_open") or {}
    if not isinstance(open_snapshot, Mapping):
        return None
    entry = _to_float(open_snapshot.get("entry_price"))
    stop = _to_float(open_snapshot.get("stop_loss"))
    symbol = str(memory.get("symbol") or "")
    if entry is None or stop is None or not symbol:
        return None
    try:
        risk_pips = abs(entry - stop) * pip_multiplier(symbol)
    except Exception:
        return None
    if risk_pips <= 0:
        return None
    return profit_loss_pips / risk_pips


def _profit_pips(symbol: Optional[str], direction: Optional[str], open_price: Optional[float], close_price: Optional[float]) -> Optional[float]:
    if not symbol or direction not in {"LONG", "SHORT"} or open_price is None or close_price is None:
        return None
    try:
        mult = pip_multiplier(symbol)
    except Exception:
        return None
    if direction == "LONG":
        return (close_price - open_price) * mult
    return (open_price - close_price) * mult


def _closed_outcome_label(profit_loss_account: float) -> str:
    if profit_loss_account > 0:
        return "TRADE_CLOSED_PROFIT"
    if profit_loss_account < 0:
        return "TRADE_CLOSED_LOSS"
    return "TRADE_CLOSED_FLAT"


def _closed_promotion_signal(profit_loss_account: float) -> str:
    if profit_loss_account > 0:
        return "CLOSED_TRADE_PROFIT_READY_FOR_REPLAY"
    if profit_loss_account < 0:
        return "CLOSED_TRADE_LOSS_REVIEW_REQUIRED"
    return "CLOSED_TRADE_FLAT_REVIEW"


def _extract_command_id(normalized: Mapping[str, Any]) -> Optional[str]:
    direct = _first_text(normalized, "commandid", "command_id", "cascommandid", "cas_command_id")
    if direct:
        return direct
    text = " ".join(
        value
        for value in (
            _first_text(normalized, "comment", "magiccomment", "ordercomment"),
            _first_text(normalized, "note", "description"),
        )
        if value
    )
    match = re.search(r"(agent-[A-Za-z0-9_-]+-\d{14}-\d+)", text)
    return match.group(1) if match else None


def _normalize_symbol(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = str(value).strip().upper().replace("/", "").replace(".", "")
    mapping = {
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY",
        "AUDUSD": "AUD/USD",
        "USDCAD": "USD/CAD",
        "AUDCAD": "AUD/CAD",
        "GBPAUD": "GBP/AUD",
        "XAUUSD": "XAU/USD",
        "NAS100": "NAS100",
        "US30": "US30",
        "SPX500": "SPX500",
    }
    return mapping.get(raw, str(value).strip().upper())


def _normalize_direction(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = str(value).strip().lower()
    if raw in {"buy", "long"}:
        return "LONG"
    if raw in {"sell", "short"}:
        return "SHORT"
    return str(value).strip().upper()


def _direction_for_match(value: Any) -> str:
    return _normalize_direction(str(value)) or ""


def _first_text(row: Mapping[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = row.get(_norm_key(key))
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _first_number(row: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = row.get(_norm_key(key))
        number = _to_float(value)
        if number is not None:
            return number
    return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    raw = str(value).strip().replace(" ", "").replace(",", "")
    if not raw or raw in {"-", "--"}:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _norm_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9/]+", "", str(key).strip().lower())


def _history_id(*parts: object) -> str:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).hexdigest()[:16]
    return f"terminal-history-{digest}"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
