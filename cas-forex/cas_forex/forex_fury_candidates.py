"""Replay/backtest candidates derived from imported Forex Fury set files."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from cas_forex.forex_fury_sets import (
    DEFAULT_OUTPUT_DIR as DEFAULT_SET_IMPORT_DIR,
    ForexFuryImportError,
    load_latest_forex_fury_set_import_report,
)
from cas_forex.instruments import SUPPORTED_SYMBOLS


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "forex_fury_replay_candidates"
CLAIM_BOUNDARY = (
    "Forex Fury replay candidates are CAS research/backtest queue inputs only. "
    "They translate owner-supplied set/report evidence into replay jobs without "
    "executing EA binaries, placing orders, creating broker ACCEPT, depositing, "
    "withdrawing, moving bank/card funds, or automating payouts."
)


class ForexFuryCandidateError(ValueError):
    """Raised when Forex Fury replay candidates cannot be built or loaded."""


def build_forex_fury_replay_candidates(
    set_import_report: Optional[Mapping[str, Any]] = None,
    *,
    min_profit_factor: float = 1.2,
    max_equity_drawdown_pct: float = 70.0,
    max_candidates: int = 24,
) -> Dict[str, Any]:
    """Build ranked CAS replay/backtest candidates from a set-import report."""

    source_report = dict(set_import_report or load_latest_forex_fury_set_import_report(DEFAULT_SET_IMPORT_DIR))
    _validate_source_report(source_report)
    records = [record for record in source_report.get("set_records", []) if isinstance(record, dict)]
    candidates = [
        candidate
        for record in records
        if (candidate := _candidate_from_record(record, source_report))
        and _passes_candidate_floor(candidate, min_profit_factor, max_equity_drawdown_pct)
    ]
    candidates = sorted(candidates, key=_candidate_sort_key, reverse=True)[:max_candidates]
    for rank, candidate in enumerate(candidates, start=1):
        candidate["rank"] = rank

    payload = {
        "report_kind": "cas_forex_forex_fury_replay_candidates",
        "created_at": datetime.now(UTC).isoformat(),
        "source_report_path": source_report.get("report_path"),
        "source_report_sha256": _file_sha256(source_report.get("report_path")),
        "source_set_count": len(records),
        "claim_boundary": CLAIM_BOUNDARY,
        "selection_thresholds": {
            "min_profit_factor": min_profit_factor,
            "max_equity_drawdown_pct": max_equity_drawdown_pct,
            "max_candidates": max_candidates,
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
        "summary": _summarize_candidates(candidates, records),
        "next_actions": [
            "Run condition-lab real-data and synthetic sweeps for the supported imported symbols/timeframes.",
            "Compare high-profit-factor profiles against CAS buckets before adding compounding rules.",
            "Use MT4 paper/demo mailbox receipts to prove any imported-style profile through CAS, not vendor tester output alone.",
            "Keep unsupported or broker-specific symbols visible until an instrument spec and broker symbol mapping are added.",
        ],
    }
    validate_forex_fury_replay_candidate_report(payload)
    return payload


def write_forex_fury_replay_candidate_report(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    min_profit_factor: float = 1.2,
    max_equity_drawdown_pct: float = 70.0,
    max_candidates: int = 24,
) -> Dict[str, Path]:
    """Write JSON and Markdown replay-candidate reports."""

    report = build_forex_fury_replay_candidates(
        min_profit_factor=min_profit_factor,
        max_equity_drawdown_pct=max_equity_drawdown_pct,
        max_candidates=max_candidates,
    )
    target_dir = output_dir.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"forex-fury-replay-candidates-{stamp}-report.json"
    md_path = target_dir / f"forex-fury-replay-candidates-{stamp}-report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_forex_fury_replay_candidates_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def load_latest_forex_fury_replay_candidate_report(report_dir: Path = DEFAULT_OUTPUT_DIR) -> Dict[str, Any]:
    """Load the newest generated Forex Fury replay-candidate report."""

    files = sorted(report_dir.glob("forex-fury-replay-candidates-*-report.json"))
    if not files:
        raise ForexFuryCandidateError(f"No Forex Fury replay-candidate reports found in {report_dir}")
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    validate_forex_fury_replay_candidate_report(payload)
    payload["report_path"] = str(files[-1])
    return payload


def validate_forex_fury_replay_candidate_report(payload: Mapping[str, Any]) -> None:
    required = {"report_kind", "created_at", "claim_boundary", "summary", "candidate_count", "candidates"}
    missing = required.difference(payload)
    if missing:
        raise ForexFuryCandidateError(f"Forex Fury replay-candidate report missing fields: {sorted(missing)}")
    if payload.get("report_kind") != "cas_forex_forex_fury_replay_candidates":
        raise ForexFuryCandidateError("unexpected Forex Fury replay-candidate report_kind")
    if "without executing EA binaries" not in str(payload.get("claim_boundary", "")):
        raise ForexFuryCandidateError("Forex Fury replay-candidate claim boundary must preserve execution limit")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise ForexFuryCandidateError("Forex Fury replay-candidate report requires a candidate list")


def render_forex_fury_replay_candidates_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# CAS Forex Forex Fury Replay Candidates",
        "",
        f"Created: `{report.get('created_at')}`",
        "",
        f"Source report: `{report.get('source_report_path')}`",
        "",
        f"Boundary: {report.get('claim_boundary')}",
        "",
        "## Summary",
        "",
        f"- Candidate count: `{report.get('candidate_count')}`",
        f"- Supported candidates: `{summary.get('supported_candidate_count')}`",
        f"- Symbols: `{summary.get('symbols')}`",
        f"- Timeframes: `{summary.get('timeframes')}`",
        f"- Families: `{summary.get('families')}`",
        f"- Platforms: `{summary.get('platforms')}`",
        "",
        "## Top Candidates",
        "",
    ]
    for candidate in report.get("candidates", [])[:10]:
        lines.append(
            "- "
            f"`#{candidate.get('rank')}` `{candidate.get('candidate_id')}` "
            f"{candidate.get('cas_symbol')} {candidate.get('timeframe')} "
            f"{candidate.get('trade_window')} score `{candidate.get('score')}` "
            f"PF `{candidate.get('evidence', {}).get('profit_factor')}`"
        )
    lines.extend(["", "## Next Actions", ""])
    for action in report.get("next_actions") or []:
        lines.append(f"- {action}")
    return "\n".join(lines) + "\n"


def _candidate_from_record(record: Mapping[str, Any], source_report: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    symbol = _normalize_symbol(record.get("symbol"))
    timeframe = str(record.get("timeframe") or "").upper()
    if not symbol or not timeframe:
        return None

    derived = record.get("derived") or {}
    report = record.get("tester_report") or {}
    metrics = report.get("metrics") or {}
    profit_factor = _as_float(metrics.get("profit_factor"))
    drawdown = _as_float(metrics.get("equity_drawdown_relative_pct"))
    trades = _as_int(metrics.get("total_trades"))
    net_profit = _as_float(metrics.get("total_net_profit"))
    max_orders = _as_int(derived.get("max_orders"))
    score = _candidate_score(profit_factor, drawdown, trades, net_profit, derived)
    candidate_id = _candidate_id(record, symbol, timeframe)
    symbol_supported = symbol in SUPPORTED_SYMBOLS
    return {
        "candidate_id": candidate_id,
        "source_profile_id": record.get("profile_id"),
        "source_set_path": record.get("relative_source_path"),
        "source_set_sha256": record.get("source_sha256"),
        "source_report_path": report.get("relative_report_path"),
        "source_import_report_path": source_report.get("report_path"),
        "platform": record.get("platform"),
        "family": record.get("family"),
        "variant": record.get("variant"),
        "raw_symbol": record.get("symbol"),
        "cas_symbol": symbol,
        "symbol_supported": symbol_supported,
        "symbol_status": "CAS_SUPPORTED" if symbol_supported else "NEEDS_INSTRUMENT_SPEC",
        "timeframe": timeframe,
        "trade_window": record.get("trade_window"),
        "trade_window_hours": derived.get("trade_window_hours") or record.get("trade_window_hours"),
        "active_days": record.get("active_days") or [],
        "execution_profile": {
            "max_orders": max_orders,
            "max_trades_per_day": _as_int(derived.get("max_trades_per_day")),
            "uses_grid": bool(derived.get("uses_grid")),
            "uses_close_by_money": bool(derived.get("uses_close_by_money")),
            "close_money_trigger": _as_float(derived.get("close_money_trigger")),
            "uses_trailing_stop": bool(derived.get("uses_trailing_stop")),
            "uses_hidden_sltp": bool(derived.get("uses_hidden_sltp")),
            "uses_dynamic_retrace": bool(derived.get("uses_dynamic_retrace")),
            "uses_cost_averaging": bool(derived.get("uses_cost_averaging")),
            "one_set_trade_per_day": bool(derived.get("one_set_trade_per_day")),
            "only_range_trading": bool(derived.get("only_range_trading")),
        },
        "risk_shape": {
            "lot_size": _as_float(derived.get("lot_size")),
            "stop_loss": _as_float(derived.get("stop_loss")),
            "take_profit": _as_float(derived.get("take_profit")),
            "tp_sl_ratio": _as_float(derived.get("tp_sl_ratio")),
            "grid_level_distance_min": _as_float(derived.get("grid_level_distance_min")),
            "grid_level_distance_max": _as_float(derived.get("grid_level_distance_max")),
            "grid_volume_multiplier_max": _as_float(derived.get("grid_volume_multiplier_max")),
        },
        "evidence": {
            "profit_factor": profit_factor,
            "equity_drawdown_relative_pct": drawdown,
            "total_net_profit": net_profit,
            "total_trades": trades,
            "history_quality": report.get("history_quality"),
        },
        "score": score,
        "readiness": "READY_FOR_CAS_REPLAY" if symbol_supported else "WAITING_FOR_INSTRUMENT_SPEC",
        "replay_job": _replay_job_spec(candidate_id, symbol, timeframe, record, max_orders),
        "recommended_commands": _recommended_commands(symbol, timeframe),
        "notes": _candidate_notes(record, symbol_supported),
    }


def _replay_job_spec(
    candidate_id: str,
    symbol: str,
    timeframe: str,
    record: Mapping[str, Any],
    max_orders: Optional[int],
) -> Dict[str, Any]:
    return {
        "job_id": f"{candidate_id}-condition-lab",
        "job_kind": "FOREX_FURY_DERIVED_CONDITION_REPLAY",
        "source": "forex_fury_set_import",
        "status": "READY_FOR_REPLAY",
        "symbols": [symbol],
        "timeframes": [timeframe],
        "families_to_compare": _families_for_record(record),
        "owner_control_inputs": {
            "max_open_positions": max_orders,
            "trade_window": record.get("trade_window"),
            "allow_grid_policy_test": bool((record.get("derived") or {}).get("uses_grid")),
            "allow_money_close_policy_test": bool((record.get("derived") or {}).get("uses_close_by_money")),
        },
    }


def _recommended_commands(symbol: str, timeframe: str) -> List[str]:
    return [
        (
            "python scripts/run_condition_lab.py --source both "
            f"--symbols {symbol} --timeframes {timeframe} "
            "--families range_scalper meanrev breakout tsmom "
            "--output-dir evidence_runs/forex_fury_condition_replay"
        ),
        (
            "python scripts/run_walk_forward_condition_lab.py "
            f"--symbols {symbol} --timeframes {timeframe} "
            "--families range_scalper meanrev breakout tsmom "
            "--output-dir evidence_runs/forex_fury_walk_forward_replay"
        ),
    ]


def _families_for_record(record: Mapping[str, Any]) -> List[str]:
    family = str(record.get("family") or "").lower()
    if family == "scalping":
        return ["range_scalper", "meanrev", "breakout"]
    if family == "swing":
        return ["tsmom", "pullback", "breakout"]
    return ["range_scalper", "meanrev", "tsmom"]


def _passes_candidate_floor(
    candidate: Mapping[str, Any],
    min_profit_factor: float,
    max_equity_drawdown_pct: float,
) -> bool:
    evidence = candidate.get("evidence") or {}
    profit_factor = _as_float(evidence.get("profit_factor"))
    drawdown = _as_float(evidence.get("equity_drawdown_relative_pct"))
    if profit_factor is None and drawdown is None:
        return False
    if profit_factor is not None and profit_factor < min_profit_factor:
        return False
    if drawdown is not None and drawdown > max_equity_drawdown_pct:
        return False
    return True


def _candidate_score(
    profit_factor: Optional[float],
    drawdown: Optional[float],
    trades: Optional[int],
    net_profit: Optional[float],
    derived: Mapping[str, Any],
) -> float:
    score = 0.0
    if profit_factor is not None:
        score += min(profit_factor, 20.0) * 12.0
    if drawdown is not None:
        score += max(0.0, 70.0 - drawdown) * 1.4
    if trades is not None:
        score += min(trades, 500) / 20.0
    if net_profit is not None and net_profit > 0:
        score += min(net_profit, 25_000.0) / 1_000.0
    if derived.get("uses_grid"):
        score += 5.0
    if derived.get("uses_close_by_money"):
        score += 3.0
    if _as_int(derived.get("max_orders")) and int(derived.get("max_orders")) > 1:
        score += 4.0
    return round(score, 4)


def _candidate_sort_key(candidate: Mapping[str, Any]) -> tuple[float, int, float]:
    evidence = candidate.get("evidence") or {}
    supported_bonus = 1 if candidate.get("symbol_supported") else 0
    drawdown = _as_float(evidence.get("equity_drawdown_relative_pct"))
    return (float(candidate.get("score") or 0.0), supported_bonus, -(drawdown or 999999.0))


def _summarize_candidates(candidates: List[Dict[str, Any]], records: List[Mapping[str, Any]]) -> Dict[str, Any]:
    supported = [candidate for candidate in candidates if candidate.get("symbol_supported")]
    return {
        "source_set_count": len(records),
        "candidate_count": len(candidates),
        "supported_candidate_count": len(supported),
        "waiting_for_instrument_spec_count": len(candidates) - len(supported),
        "symbols": sorted({candidate["cas_symbol"] for candidate in candidates}),
        "timeframes": sorted({candidate["timeframe"] for candidate in candidates}),
        "families": _count_by(candidates, "family"),
        "platforms": _count_by(candidates, "platform"),
        "ready_for_replay_ids": [candidate["candidate_id"] for candidate in supported[:10]],
        "top_candidate_id": candidates[0]["candidate_id"] if candidates else None,
        "top_candidate_score": candidates[0]["score"] if candidates else None,
    }


def _candidate_notes(record: Mapping[str, Any], symbol_supported: bool) -> List[str]:
    notes = [
        "Candidate was derived from owner-supplied Forex Fury set/report evidence.",
        "Run through CAS replay and walk-forward before using it for adaptive compounding policy.",
    ]
    if not symbol_supported:
        notes.append("CAS needs an instrument spec before this symbol can run through the normal market/backtest path.")
    if bool((record.get("derived") or {}).get("uses_grid")):
        notes.append("Grid behavior must be tested as an explicit CAS policy, not copied blindly from the EA.")
    return notes


def _normalize_symbol(symbol: object) -> Optional[str]:
    raw = str(symbol or "").strip().upper().replace("_", "")
    if not raw:
        return None
    aliases = {
        "EURUSD": "EUR/USD",
        "GBPUSD": "GBP/USD",
        "USDJPY": "USD/JPY",
        "AUDUSD": "AUD/USD",
        "USDCAD": "USD/CAD",
        "AUDCAD": "AUD/CAD",
        "GBPAUD": "GBP/AUD",
        "XAUUSD": "XAU/USD",
        "SPX500": "SPX500",
    }
    if raw in aliases:
        return aliases[raw]
    if "/" in raw:
        return raw
    match = re.fullmatch(r"([A-Z]{3})([A-Z]{3})", raw)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return raw


def _candidate_id(record: Mapping[str, Any], symbol: str, timeframe: str) -> str:
    parts = [
        str(record.get("profile_id") or ""),
        symbol,
        timeframe,
        str(record.get("trade_window") or ""),
    ]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:10]
    slug = re.sub(r"[^a-z0-9]+", "-", f"{symbol}-{timeframe}-{record.get('family')}".lower()).strip("-")
    return f"ff-replay-{slug}-{digest}"


def _count_by(rows: List[Mapping[str, Any]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "UNKNOWN")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _validate_source_report(report: Mapping[str, Any]) -> None:
    if report.get("report_kind") != "cas_forex_forex_fury_set_import":
        raise ForexFuryCandidateError("source report must be a Forex Fury set-import report")
    try:
        records = report["set_records"]
    except KeyError as exc:
        raise ForexFuryCandidateError("source report missing set_records") from exc
    if not isinstance(records, list) or not records:
        raise ForexFuryCandidateError("source report has no set records")


def _file_sha256(path_value: object) -> Optional[str]:
    if not path_value:
        return None
    path = Path(str(path_value))
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _as_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
