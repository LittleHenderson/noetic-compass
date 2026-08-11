"""Capture a no-touch proof that one winning outlier cannot authorize press size."""

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

from cas_forex.time_utils import utc_now
from cas_forex.waste_direction_outcome_binding import build_waste_learning_outcomes


DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "runtime" / "redteam-operator-outlier-edge-robustness-latest.json"
)
DEFAULT_LEARNING_PATH = REPO_ROOT / "runtime" / "mt5-demo-learning-sync.json"


def _current_operator_learning() -> dict[str, Any]:
    try:
        payload = json.loads(DEFAULT_LEARNING_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return build_waste_learning_outcomes()
    return dict(payload) if isinstance(payload, Mapping) else build_waste_learning_outcomes()


def _compact_group(value: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "symbol",
        "observed_symbols",
        "timeframe",
        "direction",
        "profile",
        "trades",
        "wins",
        "losses",
        "win_rate",
        "net_pnl",
        "after_cost_expectancy",
        "after_cost_expectancy_r",
        "after_cost_expectancy_per_1_lot_usd",
        "profit_factor",
        "largest_positive_outcome_pnl",
        "largest_positive_outcome_r",
        "largest_win_share_of_gross_profit",
        "leave_one_best_out_removed_broker_ticket",
        "leave_one_best_out_trades",
        "leave_one_best_out_net_pnl",
        "leave_one_best_out_after_cost_expectancy",
        "leave_one_best_out_after_cost_expectancy_r",
        "leave_one_best_out_after_cost_expectancy_per_1_lot_usd",
        "leave_one_best_out_growth_positive_after_costs",
        "recent_window_trade_count",
        "recent_window_net_pnl",
        "recent_window_after_cost_expectancy_r",
        "recent_consecutive_losses",
        "sample_ready",
        "growth_positive_after_costs",
        "growth_robust_to_single_best_outcome",
        "outlier_dependency_status",
        "press_size_supported_by_robust_outcomes",
        "outcome_ready_for_promotion",
        "last_close_time",
    )
    return {key: value.get(key) for key in keys}


def _focus_group(groups: list[dict[str, Any]]) -> dict[str, Any]:
    preferred = next(
        (
            row
            for row in groups
            if str(row.get("symbol") or "").upper() == "NAS100"
            and str(row.get("timeframe") or "").upper() == "M15"
            and str(row.get("direction") or "").upper() == "SHORT"
        ),
        None,
    )
    return preferred or max(groups, key=lambda row: int(row.get("trades") or 0))


def build_report(*, learning: Mapping[str, Any] | None = None) -> dict[str, Any]:
    source = dict(learning) if learning is not None else _current_operator_learning()
    groups = [
        dict(row)
        for row in (
            source.get("group_stats")
            or source.get("learning_group_stats")
            or []
        )
        if isinstance(row, Mapping)
    ]
    sample_ready = [row for row in groups if row.get("sample_ready") is True]
    robust_positive = [
        row
        for row in sample_ready
        if row.get("growth_robust_to_single_best_outcome") is True
        and row.get("press_size_supported_by_robust_outcomes") is True
    ]
    outlier_dependent = [
        row
        for row in sample_ready
        if row.get("outlier_dependency_status")
        == "POSITIVE_DEPENDS_ON_SINGLE_BEST_OUTCOME"
    ]
    focus = _focus_group(outlier_dependent) if outlier_dependent else {}
    checks = {
        "sample_ready_positive_group_found": bool(focus)
        and focus.get("sample_ready") is True
        and focus.get("growth_positive_after_costs") is True,
        "single_best_outcome_dependency_detected": bool(focus)
        and focus.get("growth_robust_to_single_best_outcome") is False
        and focus.get("outlier_dependency_status")
        == "POSITIVE_DEPENDS_ON_SINGLE_BEST_OUTCOME",
        "leave_best_out_growth_is_not_positive": bool(focus)
        and focus.get("leave_one_best_out_growth_positive_after_costs") is False
        and float(focus.get("leave_one_best_out_net_pnl") or 0.0) <= 0.0,
        "press_size_is_not_supported": bool(focus)
        and focus.get("press_size_supported_by_robust_outcomes") is False,
        "promotion_is_not_ready": bool(focus)
        and focus.get("outcome_ready_for_promotion") is False,
    }
    passed = bool(checks) and all(checks.values())
    report: dict[str, Any] = {
        "report_kind": "cas_forex_operator_outlier_edge_robustness_redteam",
        "generated_at": utc_now().isoformat(),
        "status": (
            "PASS_NO_TOUCH_OUTLIER_EDGE_ROBUSTNESS"
            if passed
            else "FAIL_REVIEW_REQUIRED"
        ),
        "source_learning_generated_at": source.get("generated_at"),
        "source_learning_grouping_basis": source.get("grouping_basis")
        or source.get("learning_grouping_basis"),
        "source_learning_ranking_basis": source.get("ranking_basis")
        or source.get("learning_ranking_basis"),
        "source_learning_overall": source.get("overall")
        or source.get("learning_overall")
        or {},
        "group_count": len(groups),
        "sample_ready_group_count": len(sample_ready),
        "robust_positive_sample_ready_group_count": len(robust_positive),
        "outlier_dependent_sample_ready_group_count": len(outlier_dependent),
        "nonpositive_sample_ready_group_count": len(sample_ready)
        - len(robust_positive)
        - len(outlier_dependent),
        "focus_group": _compact_group(focus),
        "robust_positive_groups": [_compact_group(row) for row in robust_positive],
        "outlier_dependent_groups": [
            _compact_group(row) for row in outlier_dependent
        ],
        "invariant_checks": checks,
        "operator_policy_effect": {
            "paper_learning_remains_autonomous": True,
            "minimum_probe_or_standard_may_remain_available_inside_risk_gates": True,
            "press_edge_or_max_requires_robust_positive_outcomes": True,
            "single_best_outcome_cannot_promote_behavior": True,
        },
        "read_only": True,
        "dry_run": True,
        "broker_touched": False,
        "order_send_called": False,
        "position_modified": False,
        "money_moved": False,
        "live_authority_changed": False,
        "claim_boundary": (
            "This report recomputes PAPER/DEMO outcome statistics without broker or "
            "money effects. It proves that current classification prevents one best "
            "trade from authorizing PRESS_EDGE, MAX, or promotion. It does not prove "
            "durable edge, future profit, external live readiness, or provider-backed "
            "money movement. External live money remains CURRENTLY NOT LICENSED."
        ),
    }
    report["event_hash"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args()
    report = build_report()
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(f"{target.suffix}.tmp")
    temp.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    temp.replace(target)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS_NO_TOUCH_OUTLIER_EDGE_ROBUSTNESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
