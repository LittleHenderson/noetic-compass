"""Capture read-only proof that an untradeable PASS cannot starve later lanes."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_forex.ai_control_authority import get_authority
from cas_forex.config import config
from cas_forex.live_candle_route_policy import _scan_candidate_block_reason
from cas_forex.time_utils import utc_now
from cas_forex.waste_market_data import build_waste_market_state_scan


DEFAULT_OUTPUT_PATH = REPO_ROOT / "runtime" / "redteam-entry-candidate-actionability-latest.json"
DEFAULT_EMISSION_PATH = REPO_ROOT / "runtime" / "live-candle-route-emissions.json"


def build_report(*, timeframe: str = "H1") -> dict[str, Any]:
    authority = get_authority()
    symbols = list(authority.control.get("symbols") or [])
    threshold = float(authority.control.get("edge_threshold") or 0.65)
    state = build_waste_market_state_scan(
        authority=authority,
        timeframe=str(timeframe or "H1").upper(),
        bars=300,
        max_pairs=200,
        max_scan_candidates=max(12, len(symbols)),
        allowed_symbols=symbols,
        threshold=threshold,
        candidate_block_reason=lambda candidate_state, candidate_edge: (
            _scan_candidate_block_reason(
                candidate_state,
                candidate_edge,
                emission_state_path=DEFAULT_EMISSION_PATH,
                config=config,
            )
        ),
    )
    scan = state.get("waste_market_scan")
    scan = dict(scan) if isinstance(scan, Mapping) else {}
    attempts = [
        dict(row)
        for row in (scan.get("attempts") or [])
        if isinstance(row, Mapping)
    ]
    blocked_passes = [
        row
        for row in attempts
        if str(row.get("edge_status") or "") == "PASS"
        and row.get("candidate_actionable") is False
    ]
    first_blocked_index = next(
        (
            index
            for index, row in enumerate(attempts)
            if row in blocked_passes
        ),
        -1,
    )
    later_lane_observed = first_blocked_index >= 0 and len(attempts) > first_blocked_index + 1
    selected_actionable = scan.get("selected_candidate_actionable") is True
    status = (
        "ACTIONABILITY_STARVATION_BYPASS_OBSERVED"
        if blocked_passes and later_lane_observed and selected_actionable
        else "NO_BLOCKED_PASS_OBSERVED"
    )
    report: dict[str, Any] = {
        "report_kind": "cas_forex_entry_candidate_actionability_redteam",
        "generated_at": utc_now().isoformat(),
        "status": status,
        "timeframe": str(timeframe or "H1").upper(),
        "symbol_count": len(symbols),
        "attempt_count": len(attempts),
        "blocked_pass_count": len(blocked_passes),
        "blocked_passes": [
            {
                "symbol": row.get("symbol"),
                "direction": row.get("candidate_direction"),
                "edge_status": row.get("edge_status"),
                "measured_win_prob": row.get("measured_win_prob"),
                "candidate_block_reason": row.get("candidate_block_reason"),
            }
            for row in blocked_passes
        ],
        "later_lane_observed_after_first_blocked_pass": later_lane_observed,
        "selected_symbol": scan.get("selected_symbol"),
        "selected_edge_status": scan.get("selected_edge_status"),
        "selected_candidate_actionable": selected_actionable,
        "selected_candidate_block_reason": scan.get("selected_candidate_block_reason"),
        "scan_status": scan.get("status"),
        "attempts": attempts,
        "broker_execution_touched": bool(scan.get("broker_execution_touched", False)),
        "order_send_called": False,
        "money_moved": bool(scan.get("money_moved", False)),
        "claim_boundary": (
            "This report exercises the read-only market-state selector only. It proves that "
            "a PASS with closed, stale, missing, unusable, future-dated, or already-emitted "
            "action-time evidence cannot terminate exploration of later lanes. It does not "
            "approve or dispatch an order, register an edge authorization, move money, prove "
            "future profitability, or authorize live trading."
        ),
    }
    report["event_hash"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()
    report = build_report(timeframe=args.timeframe)
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(f"{target.suffix}.tmp")
    temp.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    temp.replace(target)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
