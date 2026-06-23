"""Review condition-tally buckets against owner-control promotion policy."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.owner_control import (
    OwnerControlMode,
    PromotionThresholds,
    candidate_from_tally_bucket,
    count_condition_lab_simulator_wins,
    review_owner_promotion,
)
from cas_forex.time_utils import utc_now


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _load_buckets(path: Path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    tally = payload.get("tally", payload)
    buckets = tally.get("buckets")
    if not isinstance(buckets, list):
        raise ValueError(f"No tally buckets found in {path}")
    return buckets


def _load_condition_lab_cells(paths: list[str]) -> dict[str, list[dict[str, Any]]]:
    cells_by_path: dict[str, list[dict[str, Any]]] = {}
    for raw_path in paths:
        path = Path(raw_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        cells = payload.get("cells")
        if not isinstance(cells, list):
            raise ValueError(f"No Condition Lab cells found in {path}")
        cells_by_path[str(path)] = cells
    return cells_by_path


def _simulator_wins_for_setting(
    cells_by_path: dict[str, list[dict[str, Any]]],
    *,
    setting: str,
    min_return_pct: float,
    max_drawdown_pct: float,
    min_trades: float,
) -> int:
    return sum(
        count_condition_lab_simulator_wins(
            cells,
            setting=setting,
            min_return_pct=min_return_pct,
            max_drawdown_pct=max_drawdown_pct,
            min_trades=min_trades,
        )
        for cells in cells_by_path.values()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tally_report", help="Condition tally JSON report.")
    parser.add_argument("--lead-id", default="range_scalper_filtered_fx_d1")
    parser.add_argument("--settings", nargs="*", default=None,
                        help="Optional routed setting names to review from the tally.")
    parser.add_argument("--owner-mode", choices=[mode.value for mode in OwnerControlMode], default="NOTIFY_ONLY")
    parser.add_argument("--simulator-wins", type=int, default=0)
    parser.add_argument("--condition-lab-reports", nargs="*", default=[],
                        help="Optional Condition Lab JSON reports used to count simulator wins by bucket setting.")
    parser.add_argument("--sim-min-return", type=float, default=0.0)
    parser.add_argument("--sim-max-drawdown", type=float, default=20.0)
    parser.add_argument("--sim-min-trades", type=float, default=1.0)
    parser.add_argument("--paper-days", type=int, default=0)
    parser.add_argument("--paper-passed", action="store_true")
    parser.add_argument("--max-paper-trades", type=int, default=1)
    parser.add_argument("--min-simulator-wins", type=int, default=10)
    parser.add_argument("--min-walk-forward-windows", type=int, default=10)
    parser.add_argument("--min-positive-rate", type=float, default=0.60)
    parser.add_argument("--min-mean-return", type=float, default=0.50)
    parser.add_argument("--max-drawdown", type=float, default=5.0)
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--min-paper-days", type=int, default=30)
    parser.add_argument("--output-dir", default="evidence_runs/owner_promotion_review")
    args = parser.parse_args()

    thresholds = PromotionThresholds(
        min_simulator_wins=args.min_simulator_wins,
        min_walk_forward_windows=args.min_walk_forward_windows,
        min_positive_routed_window_rate=args.min_positive_rate,
        min_mean_return_pct=args.min_mean_return,
        max_drawdown_pct=args.max_drawdown,
        min_trades=args.min_trades,
        min_paper_days=args.min_paper_days,
    )
    tally_path = Path(args.tally_report)
    buckets = _load_buckets(tally_path)
    condition_lab_cells = _load_condition_lab_cells(args.condition_lab_reports)
    reviews = []
    wanted_settings = set(args.settings or [])
    for bucket in buckets:
        axes = bucket.get("axes", {})
        if axes.get("route_action") != "ROUTE":
            continue
        setting = str(axes.get("setting") or "")
        if wanted_settings and setting not in wanted_settings:
            continue
        simulator_wins = args.simulator_wins
        simulator_wins += _simulator_wins_for_setting(
            condition_lab_cells,
            setting=setting,
            min_return_pct=args.sim_min_return,
            max_drawdown_pct=args.sim_max_drawdown,
            min_trades=args.sim_min_trades,
        )
        evidence_refs = [str(tally_path)] + list(condition_lab_cells)
        candidate = candidate_from_tally_bucket(
            bucket,
            lead_id=args.lead_id,
            source=" + ".join(evidence_refs),
            simulator_wins=simulator_wins,
            paper_days=args.paper_days,
            paper_passed=args.paper_passed,
            evidence_refs=evidence_refs,
        )
        decision = review_owner_promotion(
            candidate,
            owner_mode=OwnerControlMode(args.owner_mode),
            thresholds=thresholds,
            max_paper_trades=args.max_paper_trades,
        )
        reviews.append({
            "bucket_key": bucket.get("key"),
            "candidate": _jsonable(asdict(candidate)),
            "decision": _jsonable(asdict(decision)),
        })

    run_id = f"owner-promotion-review-{utc_now().strftime('%Y%m%d%H%M%S')}"
    output = {
        "run_id": run_id,
        "generated_at": utc_now().isoformat(),
        "tally_report": str(tally_path),
        "settings_filter": sorted(wanted_settings),
        "condition_lab_reports": list(condition_lab_cells),
        "simulator_win_filters": {
            "min_return_pct": args.sim_min_return,
            "max_drawdown_pct": args.sim_max_drawdown,
            "min_trades": args.sim_min_trades,
        },
        "owner_mode": args.owner_mode,
        "thresholds": _jsonable(asdict(thresholds)),
        "reviews": reviews,
        "claim_boundary": "Owner control review is research/paper-only. Live trading remains NOT LICENSED.",
    }
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}-report.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("=" * 118)
    print("CAS FOREX OWNER PROMOTION REVIEW")
    print("=" * 118)
    print(f"reviews={len(reviews)} owner_mode={args.owner_mode}")
    for review in reviews:
        decision = review["decision"]
        print(f"{review['bucket_key']} -> {decision['verdict']} | {decision['reasons']}")
    print(f"\nreport written: {out_path}")
    print("NOTE: research/paper-only. Live trading remains NOT LICENSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
