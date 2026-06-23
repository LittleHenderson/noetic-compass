"""MT4/MT5 account-history import helpers for CAS Forex.

The importer is intentionally read-only. It turns exported CSV/HTML statement
data into normalized research evidence that the adaptive paper manager can
compare against current conditions.
"""

from __future__ import annotations

import csv
import hashlib
import html.parser
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from cas_forex.schemas.forecast import Direction


MT_HISTORY_IMPORT_CLAIM_BOUNDARY = (
    "Imported MT4/MT5 history is research evidence only. It does not create "
    "broker ACCEPT, live trading permission, or payment-transfer permission."
)


@dataclass(frozen=True)
class ImportedTrade:
    ticket: str
    symbol: str
    direction: str
    lots: float
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    open_price: Optional[float] = None
    close_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    profit: float = 0.0
    commission: float = 0.0
    swap: float = 0.0
    source_row: Dict[str, Any] | None = None


def import_mt_history(path: str | Path) -> Dict[str, Any]:
    source = Path(path)
    text = source.read_text(encoding="utf-8", errors="ignore")
    trades = parse_mt_history_text(text, source_name=source.name)
    return summarize_imported_history(trades, source_name=str(source), source_sha256=_sha256_text(text))


def parse_mt_history_text(text: str, *, source_name: str = "inline") -> List[ImportedTrade]:
    if "<table" in text.lower() or "<tr" in text.lower():
        rows = _parse_html_rows(text)
    else:
        rows = _parse_delimited_rows(text)
    trades = [_trade_from_row(row) for row in rows]
    return [trade for trade in trades if trade is not None]


def summarize_imported_history(
    trades: Sequence[ImportedTrade],
    *,
    source_name: str,
    source_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    closed = [trade for trade in trades if trade.profit or trade.close_price is not None]
    gross_profit = sum(max(trade.profit, 0.0) for trade in closed)
    gross_loss = abs(sum(min(trade.profit, 0.0) for trade in closed))
    by_symbol = {
        symbol: _summarize_trade_group(group)
        for symbol, group in _group_by_symbol(closed).items()
    }
    bursts = _summarize_bursts(closed)
    payload = {
        "source_name": source_name,
        "source_sha256": source_sha256,
        "platform_guess": _platform_guess(source_name),
        "trade_count": len(trades),
        "closed_trade_count": len(closed),
        "winning_trades": sum(1 for trade in closed if trade.profit > 0),
        "losing_trades": sum(1 for trade in closed if trade.profit < 0),
        "net_profit": round(sum(trade.profit for trade in closed), 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0),
        "win_rate": round(sum(1 for trade in closed if trade.profit > 0) / len(closed), 4) if closed else 0.0,
        "symbols": sorted(by_symbol),
        "by_symbol": by_symbol,
        "bursts": bursts,
        "trades": [asdict(trade) for trade in trades],
        "claim_boundary": MT_HISTORY_IMPORT_CLAIM_BOUNDARY,
        "deployment_status": "NOT LICENSED",
        "broker_accept_status": "NOT LICENSED",
        "payment_transfer_status": "NOT LICENSED",
    }
    return payload


def write_mt_history_import_report(report: Mapping[str, Any], output_dir: str | Path) -> Path:
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source = str(report.get("source_name", "mt-history")).replace("\\", "/").split("/")[-1]
    safe_source = re.sub(r"[^A-Za-z0-9_.-]+", "-", source).strip("-") or "mt-history"
    path = out_dir / f"{safe_source}-import-report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def _trade_from_row(row: Mapping[str, Any]) -> Optional[ImportedTrade]:
    normalized = {_norm_key(key): value for key, value in row.items()}
    trade_type = _first_text(normalized, "type", "direction", "side")
    direction = _direction(trade_type)
    if direction is None:
        return None
    symbol = _normalize_symbol(_first_text(normalized, "symbol", "item", "instrument"))
    if not symbol:
        return None
    lots = _first_number(normalized, "lots", "lot", "size", "volume")
    if lots is None or lots <= 0:
        return None
    open_price = _first_number(normalized, "openprice", "entryprice", "priceopen", "price")
    close_price = _first_number(normalized, "closeprice", "exitprice", "priceclose")
    profit = _first_number(normalized, "profit", "pl", "pnl") or 0.0
    return ImportedTrade(
        ticket=_first_text(normalized, "ticket", "order", "deal", "position", "id") or "",
        symbol=symbol,
        direction=direction,
        lots=lots,
        open_time=_first_text(normalized, "opentime", "time", "open"),
        close_time=_first_text(normalized, "closetime", "close"),
        open_price=open_price,
        close_price=close_price,
        stop_loss=_first_number(normalized, "sl", "s/l", "stoploss"),
        take_profit=_first_number(normalized, "tp", "t/p", "takeprofit"),
        profit=profit,
        commission=_first_number(normalized, "commission") or 0.0,
        swap=_first_number(normalized, "swap") or 0.0,
        source_row=dict(row),
    )


def _parse_delimited_rows(text: str) -> List[Dict[str, Any]]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    return [dict(row) for row in reader if any(str(value).strip() for value in row.values())]


def _parse_html_rows(text: str) -> List[Dict[str, Any]]:
    parser = _TableParser()
    parser.feed(text)
    rows = parser.rows
    if not rows:
        return []
    header_index = _find_header_index(rows)
    if header_index is None:
        return []
    headers = rows[header_index]
    parsed: List[Dict[str, Any]] = []
    for cells in rows[header_index + 1 :]:
        if len(cells) < 2:
            continue
        if len(cells) < len(headers):
            cells = [*cells, *([""] * (len(headers) - len(cells)))]
        parsed.append({headers[idx]: cells[idx] for idx in range(min(len(headers), len(cells)))})
    return parsed


class _TableParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: List[List[str]] = []
        self._current_row: Optional[List[str]] = None
        self._current_cell: Optional[List[str]] = None
        self._in_cell = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag.lower() == "tr":
            self._current_row = []
        elif tag.lower() in {"td", "th"} and self._current_row is not None:
            self._current_cell = []
            self._in_cell = True

    def handle_data(self, data: str) -> None:
        if self._in_cell and self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"td", "th"} and self._current_row is not None and self._current_cell is not None:
            self._current_row.append(" ".join("".join(self._current_cell).split()))
            self._current_cell = None
            self._in_cell = False
        elif tag.lower() == "tr" and self._current_row is not None:
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = None


def _find_header_index(rows: Sequence[Sequence[str]]) -> Optional[int]:
    for idx, row in enumerate(rows):
        normalized = {_norm_key(cell) for cell in row}
        if {"type", "size", "price"} & normalized and ("symbol" in normalized or "item" in normalized):
            return idx
        if {"ticket", "symbol", "type"} <= normalized:
            return idx
    return None


def _summarize_trade_group(trades: Sequence[ImportedTrade]) -> Dict[str, Any]:
    gross_profit = sum(max(trade.profit, 0.0) for trade in trades)
    gross_loss = abs(sum(min(trade.profit, 0.0) for trade in trades))
    wins = sum(1 for trade in trades if trade.profit > 0)
    losses = sum(1 for trade in trades if trade.profit < 0)
    return {
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(trades), 4) if trades else 0.0,
        "net_profit": round(sum(trade.profit for trade in trades), 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0),
        "average_profit": round(sum(trade.profit for trade in trades) / len(trades), 2) if trades else 0.0,
        "max_lots": round(max((trade.lots for trade in trades), default=0.0), 4),
        "directions": sorted({trade.direction for trade in trades}),
    }


def _summarize_bursts(trades: Sequence[ImportedTrade]) -> Dict[str, Any]:
    buckets: Dict[str, int] = {}
    for trade in trades:
        key = f"{trade.symbol}|{trade.direction}|{trade.open_time or 'unknown'}"
        buckets[key] = buckets.get(key, 0) + 1
    burst_sizes = list(buckets.values())
    return {
        "multi_trade_bursts": sum(1 for size in burst_sizes if size > 1),
        "max_orders_same_timestamp": max(burst_sizes, default=0),
        "burst_keys": sorted(key for key, size in buckets.items() if size > 1)[:25],
    }


def _group_by_symbol(trades: Sequence[ImportedTrade]) -> Dict[str, List[ImportedTrade]]:
    groups: Dict[str, List[ImportedTrade]] = {}
    for trade in trades:
        groups.setdefault(trade.symbol, []).append(trade)
    return groups


def _direction(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = value.strip().lower()
    if raw in {"buy", "long"}:
        return Direction.LONG.value
    if raw in {"sell", "short"}:
        return Direction.SHORT.value
    return None


def _normalize_symbol(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    raw = value.strip().upper().replace("/", "").replace(".", "")
    mapping = {
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY",
        "AUDUSD": "AUD/USD",
        "USDCAD": "USD/CAD",
        "XAUUSD": "XAU/USD",
        "NAS100": "NAS100",
        "US30": "US30",
    }
    return mapping.get(raw, value.strip().upper())


def _first_text(row: Mapping[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = row.get(_norm_key(key))
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _first_number(row: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = row.get(_norm_key(key))
        number = _parse_number(value)
        if number is not None:
            return number
    return None


def _parse_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    raw = raw.replace(" ", "").replace(",", "")
    if raw in {"-", "--"}:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _norm_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9/]+", "", str(key).strip().lower())


def _platform_guess(source_name: str) -> str:
    lowered = source_name.lower()
    if "mt5" in lowered or "metatrader5" in lowered:
        return "MT5"
    if "mt4" in lowered or "metatrader4" in lowered:
        return "MT4"
    return "MT4_OR_MT5"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()

