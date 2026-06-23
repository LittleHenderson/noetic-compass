"""Run the CAS Forex adaptive paper-compounding review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cas_forex.adaptive_compounding import (
    AdaptiveCompoundingConfig,
    append_adaptive_compounding_review,
    review_adaptive_compounding,
    write_adaptive_compounding_status,
)
from cas_forex.paper_decision import summarize_paper_route_decisions
from cas_forex.paper_proof import build_index_tsmom_126_paper_proof_plan
from cas_forex.time_utils import utc_now


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lead-id", default="index_tsmom_126_d1", choices=["index_tsmom_126_d1"])
    parser.add_argument("--paper-output-dir", default="evidence_runs/index_tsmom_126_paper_proof")
    parser.add_argument("--output-dir", default="evidence_runs/index_tsmom_126_paper_proof")
    parser.add_argument("--decision-json", help="Optional explicit paper decision JSON file.")
    parser.add_argument("--positions-json", help="Optional active paper positions JSON list.")
    parser.add_argument("--condition-tally-json", help="Optional condition tally JSON file.")
    parser.add_argument("--mt-history-summary-json", help="Optional MT history import report JSON file.")
    parser.add_argument("--account-equity", type=float, default=5_000.0)
    parser.add_argument("--max-basket-positions", type=int, default=15)
    parser.add_argument("--base-lot", type=float, default=0.01)
    parser.add_argument("--min-compound-profit-r", type=float, default=0.5)
    parser.add_argument("--min-add-confidence", type=float, default=0.55)
    args = parser.parse_args()

    plan = build_index_tsmom_126_paper_proof_plan()
    latest_decision = _load_latest_decision(plan, args)
    positions = _load_json(args.positions_json, default=[])
    condition_tally = _load_json(args.condition_tally_json, default=None)
    mt_history = _load_json(args.mt_history_summary_json, default=None)
    cfg = AdaptiveCompoundingConfig(
        max_basket_positions=args.max_basket_positions,
        base_lot=args.base_lot,
        min_compound_profit_r=args.min_compound_profit_r,
        min_add_confidence=args.min_add_confidence,
    )
    review = review_adaptive_compounding(
        plan,
        latest_decision,
        active_positions=positions,
        condition_tally=condition_tally,
        imported_history_summary=mt_history,
        account_equity=args.account_equity,
        config=cfg,
    )
    receipt = append_adaptive_compounding_review(review, args.output_dir)
    status_path = write_adaptive_compounding_status(plan, args.output_dir)
    print(json.dumps({"status_path": str(status_path), **receipt}, indent=2))
    return 0


def _load_latest_decision(plan: Any, args: argparse.Namespace) -> Dict[str, Any]:
    if args.decision_json:
        payload = _load_json(args.decision_json, default={})
        if not isinstance(payload, dict):
            raise ValueError("--decision-json must contain a JSON object.")
        return payload
    summary = summarize_paper_route_decisions(plan, args.paper_output_dir)
    latest = summary.get("latest_decision")
    if isinstance(latest, dict):
        return latest
    return {
        "decision_id": f"{plan.plan_id}-{utc_now().date().isoformat()}-paper-decision",
        "plan_id": plan.plan_id,
        "lead_id": plan.lead_id,
        "strategy_setting": plan.strategy_setting,
        "date": utc_now().date().isoformat(),
        "timeframe": plan.timeframe,
        "route_action": "NO_TRADE",
        "event_context": "normal",
        "symbol_decisions": [],
        "notes": ["No latest paper route decision was found."],
    }


def _load_json(path: str | None, *, default: Any) -> Any:
    if not path:
        return default
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())

