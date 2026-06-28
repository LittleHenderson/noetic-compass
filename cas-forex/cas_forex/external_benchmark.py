"""External benchmark snapshots for CAS Forex strategy comparison.

These snapshots are reference targets from public or owner-supplied sources.
They are not CAS Forex live evidence and do not authorize broker execution.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "evidence_runs"
    / "external_benchmark"
    / "forex-fury-mt4-benchmark-20260624-report.json"
)

REQUIRED_REPORT_FIELDS = {
    "report_kind",
    "created_at",
    "source_family",
    "claim_boundary",
    "source_limitations",
    "benchmarks",
    "implementation_targets",
    "recommended_next_files",
}

REQUIRED_BENCHMARK_FIELDS = {
    "benchmark_id",
    "name",
    "url",
    "public_account_descriptor",
    "visible_symbol_focus",
    "gain_pct",
    "drawdown_pct",
    "trades",
}


class ExternalBenchmarkError(ValueError):
    """Raised when a benchmark snapshot is missing required structure."""


def load_external_benchmark_report(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load and validate the latest external benchmark snapshot."""

    report_path = path or DEFAULT_REPORT_PATH
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    validate_external_benchmark_report(payload)
    payload["report_path"] = str(report_path)
    payload["summary"] = summarize_external_benchmarks(payload)
    return payload


def validate_external_benchmark_report(payload: Mapping[str, Any]) -> None:
    missing = REQUIRED_REPORT_FIELDS.difference(payload)
    if missing:
        raise ExternalBenchmarkError(f"external benchmark report missing fields: {sorted(missing)}")

    if payload.get("report_kind") != "cas_forex_external_benchmark_snapshot":
        raise ExternalBenchmarkError("unexpected external benchmark report_kind")

    benchmarks = payload.get("benchmarks")
    if not isinstance(benchmarks, list) or not benchmarks:
        raise ExternalBenchmarkError("external benchmark report requires a non-empty benchmarks list")

    for idx, benchmark in enumerate(benchmarks):
        if not isinstance(benchmark, Mapping):
            raise ExternalBenchmarkError(f"benchmark #{idx} is not an object")
        missing_benchmark = REQUIRED_BENCHMARK_FIELDS.difference(benchmark)
        if missing_benchmark:
            raise ExternalBenchmarkError(
                f"benchmark #{idx} missing fields: {sorted(missing_benchmark)}"
            )

    claim_boundary = str(payload.get("claim_boundary", ""))
    if "does not create broker ACCEPT" not in claim_boundary:
        raise ExternalBenchmarkError("external benchmark claim boundary must preserve broker ACCEPT limit")


def summarize_external_benchmarks(payload: Mapping[str, Any]) -> Dict[str, Any]:
    benchmarks: List[Mapping[str, Any]] = list(payload.get("benchmarks") or [])
    mt4_count = sum("MetaTrader 4" in str(row.get("public_account_descriptor", "")) for row in benchmarks)
    real_count = sum(str(row.get("public_account_descriptor", "")).startswith("Real") for row in benchmarks)
    symbols = sorted({str(row.get("visible_symbol_focus")) for row in benchmarks if row.get("visible_symbol_focus")})
    best_gain = max(benchmarks, key=lambda row: float(row.get("gain_pct", 0.0)))
    lowest_drawdown = min(benchmarks, key=lambda row: float(row.get("drawdown_pct", 0.0)))
    total_trades = sum(int(row.get("trades", 0) or 0) for row in benchmarks)

    return {
        "benchmark_count": len(benchmarks),
        "real_account_count": real_count,
        "mt4_account_count": mt4_count,
        "symbols": symbols,
        "total_public_trade_count": total_trades,
        "best_gain_benchmark_id": best_gain.get("benchmark_id"),
        "best_gain_pct": best_gain.get("gain_pct"),
        "lowest_drawdown_benchmark_id": lowest_drawdown.get("benchmark_id"),
        "lowest_drawdown_pct": lowest_drawdown.get("drawdown_pct"),
        "next_build_target": "Build external benchmark ingestion, MT4 bridge, and benchmark comparison panels.",
    }
