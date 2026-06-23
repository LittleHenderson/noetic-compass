"""Create a condition tally from a CAS FOREX walk-forward report.

This turns route windows into a compact scoreboard by symbol, timeframe, event
context, regime, setting, return, drawdown, and trade count.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.condition_tally import tally_by_event_context, tally_walk_forward_conditions
from cas_forex.time_utils import utc_now


def load_windows(report_path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if isinstance(payload.get("windows"), list):
        return list(payload["windows"])
    if isinstance(payload.get("timeframe_reports"), dict):
        windows: List[Dict[str, Any]] = []
        for report in payload["timeframe_reports"].values():
            windows.extend(report.get("windows", []))
        return windows
    raise ValueError(f"No walk-forward windows found in {report_path}")


def _print_buckets(tally: Dict[str, Any], limit: int) -> None:
    print("\nTOP CONDITION BUCKETS")
    print("-" * 118)
    for bucket in tally["buckets"][:limit]:
        axes = ",".join(f"{key}={value}" for key, value in bucket["axes"].items())
        print(
            f"{axes} | windows={bucket['windows']} routed={bucket['routed_windows']} "
            f"positive_rate={bucket['positive_window_rate']} mean_ret={bucket['mean_return_pct']} "
            f"dd={bucket['max_drawdown_pct']} trades={bucket['trades']}"
        )
    if len(tally["buckets"]) > limit:
        print(f"... {len(tally['buckets']) - limit} more buckets in JSON report")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report_path", help="Walk-forward JSON report to tally.")
    parser.add_argument("--by-event", action="store_true", help="Group primarily by event context.")
    parser.add_argument("--axes", nargs="*", default=None,
                        help="Custom condition axes, e.g. test_event_context timeframe route_action setting.")
    parser.add_argument("--output-dir", default="evidence_runs/condition_tally")
    parser.add_argument("--limit", type=int, default=16)
    args = parser.parse_args()

    report_path = Path(args.report_path)
    windows = load_windows(report_path)
    if args.axes:
        tally = tally_walk_forward_conditions(windows, axes=args.axes)
    elif args.by_event:
        tally = tally_by_event_context(windows)
    else:
        tally = tally_walk_forward_conditions(windows)
    run_id = f"condition-tally-{utc_now().strftime('%Y%m%d%H%M%S')}"
    output = {
        "run_id": run_id,
        "generated_at": utc_now().isoformat(),
        "source_report": str(report_path),
        "by_event": bool(args.by_event),
        "tally": tally,
        "claim_boundary": "Research-only condition tally. Live trading remains NOT LICENSED.",
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}-report.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("=" * 118)
    print("CAS FOREX CONDITION TALLY")
    print("=" * 118)
    print(json.dumps(tally["summary"], indent=2))
    _print_buckets(tally, limit=args.limit)
    print(f"\nreport written: {out_path}")
    print("NOTE: research-only tally. Live trading remains NOT LICENSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
