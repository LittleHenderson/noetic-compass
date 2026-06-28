"""Forex Fury set/report importer for CAS Forex strategy study.

The importer reads owner-supplied MetaTrader `.set` files and tester reports.
It never executes compiled EA binaries.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = Path.home() / "Downloads" / "Forex-Fury-CORE-1.4NEW-SETS (1)"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "forex_fury_set_import"
CLAIM_BOUNDARY = (
    "Forex Fury set import is local strategy-study evidence only. It reads set/report files "
    "and fingerprints compiled EA binaries without executing them. It does not place orders, "
    "create broker ACCEPT, deposit, withdraw, move bank/card funds, or automate payouts."
)

KEY_PARAMETERS = (
    "InpTradeDirection",
    "InpLotSizeMode",
    "Lot_Size",
    "InpLotSizeEquityP",
    "InpLotSizeMoney",
    "InpUseHiddenSLTP",
    "InpSLMode",
    "Stop_Loss",
    "InpTPMode",
    "Take_Profit",
    "InpTPRatio",
    "MaxOrders",
    "InpReverseStrategy",
    "InpOneSetTradePerDay",
    "InpMaxTradesPerDay",
    "InpOnlyRangeTrading",
    "InpCoolOffTimeAfterLoss",
    "MaxSpread",
    "Max_Slippage",
    "Magic_Number",
    "InpUseGrid",
    "InpGridLevelsDistanceMultiplier",
    "InpGridVolumeMultiplier",
    "InpFilterTradesByHeikenAshi",
    "InpFilterTradesByStochastic",
    "InpCloseAllByMoney",
    "InpTriggerAmount",
    "InpCloseByDonchianChannels",
    "InpDonchianChannelsPeriod",
    "InpUseDynamicRetrace",
    "InpRetraceTrigger",
    "InpRetraceExit",
    "InpUseCostAveraging",
    "InpCAMinDistance",
    "InpUseTrailingStop",
    "InpTrailingStart",
    "InpTrailingStep",
    "InpTrailingStop",
    "StartTradingTime",
    "EndTradingTime",
    "TradeOnMonday",
    "TradeOnTuesday",
    "TradeOnWednesday",
    "TradeOnThursday",
    "TradeOnFriday",
    "InpCloseAtTime1",
    "InpCloseTime1Day",
    "InpCloseTime1Time",
    "InpCloseOnlyTradesInProfit",
    "InpMarginCallLevel",
    "InpStopOutLevel",
)

REPORT_LABELS = {
    "Expert",
    "Symbol",
    "Period",
    "Company",
    "Currency",
    "Initial Deposit",
    "Leverage",
    "History Quality",
    "Bars",
    "Ticks",
    "Symbols",
    "Total Net Profit",
    "Gross Profit",
    "Gross Loss",
    "Balance Drawdown Absolute",
    "Balance Drawdown Maximal",
    "Balance Drawdown Relative",
    "Equity Drawdown Absolute",
    "Equity Drawdown Maximal",
    "Equity Drawdown Relative",
    "Profit Factor",
    "Expected Payoff",
    "Margin Level",
    "Recovery Factor",
    "Sharpe Ratio",
    "Z-Score",
    "Total Trades",
    "Total Deals",
    "Profit Trades (% of total)",
    "Loss Trades (% of total)",
    "Largest profit trade",
    "Largest loss trade",
}


class ForexFuryImportError(ValueError):
    """Raised when a Forex Fury set/report import cannot be built."""


def build_forex_fury_set_import(source_dir: Path = DEFAULT_SOURCE_DIR) -> Dict[str, Any]:
    """Build a normalized report from a Forex Fury package directory."""

    source_root = source_dir.expanduser().resolve()
    if not source_root.exists():
        raise ForexFuryImportError(f"Forex Fury source directory does not exist: {source_root}")
    if not source_root.is_dir():
        raise ForexFuryImportError(f"Forex Fury source path is not a directory: {source_root}")

    set_paths = sorted(source_root.rglob("*.set"))
    html_paths = sorted(path for path in source_root.rglob("*") if path.is_file() and path.suffix.lower() in {".html", ".htm"})
    binary_paths = sorted(
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".ex4", ".ex5", ".dll", ".exe"}
    )
    file_counts = Counter(path.suffix.lower() or "<no_ext>" for path in source_root.rglob("*") if path.is_file())

    records = [_parse_set_record(path, source_root) for path in set_paths]
    for record in records:
        report_path = _find_report_for_set(Path(record["source_path"]))
        if report_path:
            record["tester_report"] = _parse_tester_report(report_path, source_root)
        else:
            record["tester_report"] = None

    payload: Dict[str, Any] = {
        "report_kind": "cas_forex_forex_fury_set_import",
        "created_at": datetime.now(UTC).isoformat(),
        "source_family": "Forex Fury CORE 2026",
        "source_dir": str(source_root),
        "claim_boundary": CLAIM_BOUNDARY,
        "source_limitations": [
            "Compiled EA files are fingerprinted only; they are not executed or decompiled.",
            "MetaTrader tester reports are vendor/local backtest artifacts and are not live CAS broker receipts.",
            "Set-file parameters are strategy inputs, not proof that CAS Forex should trade live immediately.",
        ],
        "file_counts": dict(sorted(file_counts.items())),
        "compiled_binaries": [_fingerprint_binary(path, source_root) for path in binary_paths],
        "set_records": records,
        "summary": _summarize_records(records, html_paths, binary_paths),
        "cas_improvement_targets": _build_improvement_targets(records),
    }
    return payload


def write_forex_fury_set_import_report(
    source_dir: Path = DEFAULT_SOURCE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Dict[str, Path]:
    """Write JSON and Markdown reports for a Forex Fury package import."""

    report = build_forex_fury_set_import(source_dir)
    target_dir = output_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"forex-fury-set-import-{stamp}-report.json"
    md_path = target_dir / f"forex-fury-set-import-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_forex_fury_set_import_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_forex_fury_set_import_report(report_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    """Load the newest generated Forex Fury set-import report."""

    files = sorted(report_dir.glob("forex-fury-set-import-*-report.json"))
    if not files:
        raise ForexFuryImportError(f"No Forex Fury set-import reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    validate_forex_fury_set_import_report(payload)
    payload["report_path"] = str(files[-1])
    return payload


def validate_forex_fury_set_import_report(payload: Mapping[str, Any]) -> None:
    required = {"report_kind", "created_at", "source_family", "claim_boundary", "summary", "set_records"}
    missing = required.difference(payload)
    if missing:
        raise ForexFuryImportError(f"Forex Fury set-import report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != "cas_forex_forex_fury_set_import":
        raise ForexFuryImportError("unexpected Forex Fury set-import report_kind")
    if "does not place orders" not in str(payload.get("claim_boundary", "")):
        raise ForexFuryImportError("Forex Fury set-import claim boundary must preserve order-execution limit")
    records = payload.get("set_records")
    if not isinstance(records, list) or not records:
        raise ForexFuryImportError("Forex Fury set-import report requires at least one set record")


def render_forex_fury_set_import_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Forex Fury Set Import",
        "",
        f"Created: `{report.get('created_at')}`",
        "",
        f"Source: `{report.get('source_dir')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Set files: `{summary.get('set_count')}`",
        f"- Tester reports attached: `{summary.get('tester_report_count')}`",
        f"- Platforms: `{summary.get('platform_counts')}`",
        f"- Families: `{summary.get('family_counts')}`",
        f"- Symbols: `{summary.get('symbol_counts')}`",
        f"- Timeframes: `{summary.get('timeframe_counts')}`",
        f"- Unique trade windows: `{summary.get('trade_windows')}`",
        f"- Grid-enabled sets: `{summary.get('grid_enabled_count')}`",
        f"- Close-by-money sets: `{summary.get('close_by_money_count')}`",
        f"- Compiled binaries fingerprinted: `{summary.get('compiled_binary_count')}`",
        "",
        "## Best Report Signals",
        "",
    ]
    for key in ("best_profit_factor", "lowest_equity_drawdown_pct", "highest_net_profit"):
        item = summary.get(key) or {}
        lines.append(f"- {key}: `{item.get('profile_id')}` / `{item.get('value')}`")
    lines.extend(["", "## CAS Improvement Targets", ""])
    for target in report.get("cas_improvement_targets") or []:
        lines.append(f"- {target}")
    return "\n".join(lines) + "\n"


def _parse_set_record(path: Path, source_root: Path) -> Dict[str, Any]:
    parameters, optimization = _parse_set_parameters(path)
    core = {key: parameters[key] for key in KEY_PARAMETERS if key in parameters}
    start = _normalize_time(_as_str(core.get("StartTradingTime")))
    end = _normalize_time(_as_str(core.get("EndTradingTime")))
    stop_loss = _as_float(core.get("Stop_Loss"))
    take_profit = _as_float(core.get("Take_Profit"))
    max_orders = _as_int(core.get("MaxOrders"))
    grid_levels = _as_float_list(core.get("InpGridLevelsDistanceMultiplier"))
    grid_volume = _as_float_list(core.get("InpGridVolumeMultiplier"))
    active_days = [
        day
        for day, key in (
            ("Monday", "TradeOnMonday"),
            ("Tuesday", "TradeOnTuesday"),
            ("Wednesday", "TradeOnWednesday"),
            ("Thursday", "TradeOnThursday"),
            ("Friday", "TradeOnFriday"),
        )
        if core.get(key) is True
    ]

    profile_id = _profile_id(path, source_root)
    return {
        "profile_id": profile_id,
        "source_path": str(path),
        "relative_source_path": str(path.relative_to(source_root)),
        "source_sha256": _sha256(path),
        "platform": _detect_platform(path),
        "family": _detect_family(path),
        "variant": _detect_variant(path),
        "symbol": _detect_symbol(path),
        "timeframe": _detect_timeframe(path),
        "trade_window": f"{start}-{end}" if start and end else None,
        "trade_window_hours": _window_hours(start, end),
        "active_days": active_days,
        "core_parameters": core,
        "derived": {
            "lot_size": _as_float(core.get("Lot_Size")),
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "tp_sl_ratio": round(take_profit / stop_loss, 6) if stop_loss and take_profit else None,
            "max_orders": max_orders,
            "max_trades_per_day": _as_int(core.get("InpMaxTradesPerDay")),
            "max_spread": _as_float(core.get("MaxSpread")),
            "uses_grid": bool(core.get("InpUseGrid")),
            "grid_level_distance_min": min(grid_levels) if grid_levels else None,
            "grid_level_distance_max": max(grid_levels) if grid_levels else None,
            "grid_volume_multiplier_max": max(grid_volume) if grid_volume else None,
            "uses_close_by_money": bool(core.get("InpCloseAllByMoney")),
            "close_money_trigger": _as_float(core.get("InpTriggerAmount")),
            "uses_hidden_sltp": bool(core.get("InpUseHiddenSLTP")),
            "uses_dynamic_retrace": bool(core.get("InpUseDynamicRetrace")),
            "uses_cost_averaging": bool(core.get("InpUseCostAveraging")),
            "uses_trailing_stop": bool(core.get("InpUseTrailingStop")),
            "uses_stochastic_filter": bool(core.get("InpFilterTradesByStochastic")),
            "uses_heiken_ashi_filter": bool(core.get("InpFilterTradesByHeikenAshi")),
            "one_set_trade_per_day": bool(core.get("InpOneSetTradePerDay")),
            "only_range_trading": bool(core.get("InpOnlyRangeTrading")),
        },
        "optimization": optimization,
    }


def _parse_set_parameters(path: Path) -> tuple[Dict[str, Any], Dict[str, Any]]:
    parameters: Dict[str, Any] = {}
    ranges: Dict[str, Dict[str, Any]] = {}
    optimized_fields: List[str] = []
    for raw_line in _read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = _coerce_value(raw_value.strip())
        match = re.match(r"^(?P<base>.+),(?P<suffix>[123F])$", key)
        if match:
            base = match.group("base")
            suffix = match.group("suffix")
            ranges.setdefault(base, {})[suffix] = value
            if suffix == "F" and bool(value):
                optimized_fields.append(base)
            continue
        parameters[key] = value
    return parameters, {"ranges": ranges, "optimized_fields": sorted(set(optimized_fields))}


def _parse_tester_report(path: Path, source_root: Path) -> Dict[str, Any]:
    text = _read_text(path)
    label_values = _extract_report_label_values(text)
    metrics = {
        "total_net_profit": _first_number(label_values.get("Total Net Profit")),
        "gross_profit": _first_number(label_values.get("Gross Profit")),
        "gross_loss": _first_number(label_values.get("Gross Loss")),
        "profit_factor": _first_number(label_values.get("Profit Factor")),
        "expected_payoff": _first_number(label_values.get("Expected Payoff")),
        "recovery_factor": _first_number(label_values.get("Recovery Factor")),
        "sharpe_ratio": _first_number(label_values.get("Sharpe Ratio")),
        "total_trades": _as_int(_first_number(label_values.get("Total Trades"))),
        "total_deals": _as_int(_first_number(label_values.get("Total Deals"))),
        "profit_trades_pct": _percent_number(label_values.get("Profit Trades (% of total)")),
        "loss_trades_pct": _percent_number(label_values.get("Loss Trades (% of total)")),
        "balance_drawdown_maximal": _first_number(label_values.get("Balance Drawdown Maximal")),
        "balance_drawdown_maximal_pct": _percent_number(label_values.get("Balance Drawdown Maximal")),
        "balance_drawdown_relative_pct": _percent_number(label_values.get("Balance Drawdown Relative")),
        "equity_drawdown_maximal": _first_number(label_values.get("Equity Drawdown Maximal")),
        "equity_drawdown_maximal_pct": _percent_number(label_values.get("Equity Drawdown Maximal")),
        "equity_drawdown_relative_pct": _percent_number(label_values.get("Equity Drawdown Relative")),
        "initial_deposit": _first_number(label_values.get("Initial Deposit")),
        "bars": _as_int(_first_number(label_values.get("Bars"))),
        "ticks": _as_int(_first_number(label_values.get("Ticks"))),
    }
    return {
        "report_path": str(path),
        "relative_report_path": str(path.relative_to(source_root)),
        "report_sha256": _sha256(path),
        "expert": label_values.get("Expert"),
        "symbol": label_values.get("Symbol"),
        "period": label_values.get("Period"),
        "company": label_values.get("Company"),
        "currency": label_values.get("Currency"),
        "leverage": label_values.get("Leverage"),
        "history_quality": label_values.get("History Quality"),
        "raw_fields": label_values,
        "metrics": metrics,
    }


def _extract_report_label_values(text: str) -> Dict[str, str]:
    cells = []
    for match in re.finditer(r"<td\b[^>]*>(.*?)</td>", text, flags=re.IGNORECASE | re.DOTALL):
        cell = re.sub(r"<[^>]+>", "", match.group(1))
        cell = html.unescape(re.sub(r"\s+", " ", cell)).strip()
        if cell:
            cells.append(cell)
    values: Dict[str, str] = {}
    for idx, cell in enumerate(cells):
        if not cell.endswith(":"):
            continue
        label = cell[:-1].strip()
        if label not in REPORT_LABELS:
            continue
        for candidate in cells[idx + 1 : idx + 4]:
            if candidate and not candidate.endswith(":"):
                values[label] = candidate
                break
    return values


def _find_report_for_set(set_path: Path) -> Optional[Path]:
    candidates: List[Path] = []
    candidates.extend(sorted(set_path.parent.glob("*.html")))
    candidates.extend(sorted((set_path.parent / "ReportTester").glob("*.html")))
    return candidates[0] if candidates else None


def _summarize_records(records: List[Dict[str, Any]], html_paths: List[Path], binary_paths: List[Path]) -> Dict[str, Any]:
    platform_counts = Counter(record.get("platform") for record in records)
    family_counts = Counter(record.get("family") for record in records)
    symbol_counts = Counter(record.get("symbol") for record in records if record.get("symbol"))
    timeframe_counts = Counter(record.get("timeframe") for record in records if record.get("timeframe"))
    report_records = [record for record in records if record.get("tester_report")]
    ranked = _rank_report_records(report_records)
    return {
        "set_count": len(records),
        "html_report_file_count": len(html_paths),
        "tester_report_count": len(report_records),
        "compiled_binary_count": len(binary_paths),
        "platform_counts": dict(sorted(platform_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "symbol_counts": dict(sorted(symbol_counts.items())),
        "timeframe_counts": dict(sorted(timeframe_counts.items())),
        "trade_windows": sorted({record["trade_window"] for record in records if record.get("trade_window")}),
        "max_orders_values": sorted({record["derived"]["max_orders"] for record in records if record["derived"].get("max_orders") is not None}),
        "grid_enabled_count": sum(bool(record["derived"].get("uses_grid")) for record in records),
        "close_by_money_count": sum(bool(record["derived"].get("uses_close_by_money")) for record in records),
        "hidden_sltp_count": sum(bool(record["derived"].get("uses_hidden_sltp")) for record in records),
        "trailing_stop_count": sum(bool(record["derived"].get("uses_trailing_stop")) for record in records),
        "dynamic_retrace_count": sum(bool(record["derived"].get("uses_dynamic_retrace")) for record in records),
        "cost_averaging_count": sum(bool(record["derived"].get("uses_cost_averaging")) for record in records),
        "stochastic_filter_count": sum(bool(record["derived"].get("uses_stochastic_filter")) for record in records),
        "one_set_trade_per_day_count": sum(bool(record["derived"].get("one_set_trade_per_day")) for record in records),
        "best_profit_factor": _best_metric(report_records, "profit_factor", highest=True),
        "lowest_equity_drawdown_pct": _best_metric(report_records, "equity_drawdown_relative_pct", highest=False),
        "highest_net_profit": _best_metric(report_records, "total_net_profit", highest=True),
        "top_report_profiles": ranked[:10],
    }


def _rank_report_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def score(record: Dict[str, Any]) -> tuple[float, float, float]:
        metrics = ((record.get("tester_report") or {}).get("metrics") or {})
        return (
            float(metrics.get("profit_factor") or 0.0),
            -float(metrics.get("equity_drawdown_relative_pct") or 999999.0),
            float(metrics.get("total_net_profit") or 0.0),
        )

    ranked = sorted(records, key=score, reverse=True)
    return [_metric_snapshot(record) for record in ranked]


def _best_metric(records: List[Dict[str, Any]], metric: str, *, highest: bool) -> Optional[Dict[str, Any]]:
    rows = []
    for record in records:
        value = (((record.get("tester_report") or {}).get("metrics") or {}).get(metric))
        if value is not None:
            rows.append((float(value), record))
    if not rows:
        return None
    value, record = max(rows, key=lambda item: item[0]) if highest else min(rows, key=lambda item: item[0])
    return {**_metric_snapshot(record), "metric": metric, "value": value}


def _metric_snapshot(record: Mapping[str, Any]) -> Dict[str, Any]:
    report = record.get("tester_report") or {}
    metrics = report.get("metrics") or {}
    return {
        "profile_id": record.get("profile_id"),
        "platform": record.get("platform"),
        "family": record.get("family"),
        "variant": record.get("variant"),
        "symbol": record.get("symbol"),
        "timeframe": record.get("timeframe"),
        "trade_window": record.get("trade_window"),
        "profit_factor": metrics.get("profit_factor"),
        "total_net_profit": metrics.get("total_net_profit"),
        "equity_drawdown_relative_pct": metrics.get("equity_drawdown_relative_pct"),
        "total_trades": metrics.get("total_trades"),
        "history_quality": report.get("history_quality"),
    }


def _build_improvement_targets(records: List[Dict[str, Any]]) -> List[str]:
    windows = sorted({record["trade_window"] for record in records if record.get("trade_window")})
    symbols = sorted({record["symbol"] for record in records if record.get("symbol")})
    grid_count = sum(bool(record["derived"].get("uses_grid")) for record in records)
    close_money_count = sum(bool(record["derived"].get("uses_close_by_money")) for record in records)
    return [
        "Add CAS Forex strategy-profile ingestion for MT4/MT5 set files so owner-supplied recipes become replayable evidence.",
        f"Build a session-window optimizer using observed Forex Fury windows: {', '.join(windows)}.",
        f"Extend CAS symbol/timeframe candidate coverage using observed package targets: {', '.join(symbols)}.",
        f"Model grid/compounding as a controlled policy surface; {grid_count} imported sets enable grid behavior.",
        f"Add money-close and dynamic exit review; {close_money_count} imported sets use close-all-by-money triggers.",
        "Compare fast-grid vs regular-grid behavior before allowing CAS to compound winning positions.",
        "Prioritize MT4 bridge hardening because the package includes MT4 sets plus a compiled MT4 EA binary.",
        "Keep every imported set as research input until CAS has its own broker receipts, market replay, and owner-authorized runtime checks.",
    ]


def _fingerprint_binary(path: Path, source_root: Path) -> Dict[str, Any]:
    return {
        "path": str(path),
        "relative_path": str(path.relative_to(source_root)),
        "extension": path.suffix.lower(),
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "handling": "fingerprinted_only_not_executed",
    }


def _profile_id(path: Path, source_root: Path) -> str:
    rel = path.relative_to(source_root)
    raw = "|".join(part for part in rel.parts if part.lower() not in {"set files", "reporttester"})
    digest = hashlib.sha256(str(rel).encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return f"ff-{slug[:70]}-{digest}"


def _detect_platform(path: Path) -> str:
    parts = {part.upper() for part in path.parts}
    if "MT4" in parts:
        return "MT4"
    if "MT5" in parts:
        return "MT5"
    return "UNKNOWN"


def _detect_family(path: Path) -> str:
    text = str(path).lower()
    if "scalping" in text:
        return "scalping"
    if "swing" in text:
        return "swing"
    if "old set" in text or "all m15" in text:
        return "classic_m15"
    return "unknown"


def _detect_variant(path: Path) -> str:
    text = str(path).lower()
    if "fast" in text:
        return "fast"
    if "regular" in text:
        return "regular"
    if "aggressive" in text and "high risk" in text:
        return "aggressive_high_risk"
    if "aggressive" in text and "low frequency" in text:
        return "aggressive_low_frequency"
    if "default" in text or "low risk" in text:
        return "default_low_risk"
    return "standard"


def _detect_symbol(path: Path) -> Optional[str]:
    text = str(path).upper()
    matches = re.findall(r"(?<![A-Z0-9])(_?SPX500|[A-Z]{6})(?![A-Z0-9])", text)
    if not matches:
        return None
    return matches[-1].lstrip("_")


def _detect_timeframe(path: Path) -> Optional[str]:
    text = str(path).upper()
    matches = re.findall(r"(?<![A-Z0-9])(M1|M5|M15|M30|H1|H4|D1)(?![A-Z0-9])", text)
    return matches[-1] if matches else None


def _coerce_value(value: str) -> Any:
    if value == "(null)":
        return None
    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if "," in value:
        parts = [part.strip() for part in value.split(",")]
        numbers = [_try_float(part) for part in parts]
        if all(number is not None for number in numbers):
            return numbers
    number = _try_float(value)
    if number is not None:
        return int(number) if number.is_integer() and "." not in value else number
    return value


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _first_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    match = re.search(r"-?\d[\d\s]*\.?\d*", str(value))
    if not match:
        return None
    return float(match.group(0).replace(" ", ""))


def _percent_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    match = re.search(r"(-?\d[\d\s]*\.?\d*)\s*%", str(value))
    if not match:
        return None
    return float(match.group(1).replace(" ", ""))


def _try_float(value: str) -> Optional[float]:
    try:
        return float(value.replace(" ", ""))
    except ValueError:
        return None


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return _try_float(str(value))


def _as_int(value: Any) -> Optional[int]:
    number = _as_float(value)
    return int(number) if number is not None else None


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _as_float_list(value: Any) -> List[float]:
    if isinstance(value, list):
        return [float(item) for item in value if isinstance(item, (int, float))]
    if isinstance(value, (int, float)):
        return [float(value)]
    return []


def _window_hours(start: Optional[str], end: Optional[str]) -> Optional[float]:
    if not start or not end:
        return None
    start_seconds = _time_seconds(start)
    end_seconds = _time_seconds(end)
    if start_seconds is None or end_seconds is None:
        return None
    if end_seconds < start_seconds:
        end_seconds += 24 * 60 * 60
    return round((end_seconds - start_seconds) / 3600.0, 4)


def _time_seconds(value: str) -> Optional[int]:
    match = re.match(r"^(\d{1,2}):(\d{2}):(\d{2})$", value)
    if not match:
        return None
    hours, minutes, seconds = (int(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def _normalize_time(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    match = re.match(r"^(\d{1,2}):(\d{2}):(\d{2})$", value)
    if not match:
        return value
    hours, minutes, seconds = (int(part) for part in match.groups())
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
