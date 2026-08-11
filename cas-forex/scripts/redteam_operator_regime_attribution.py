"""Capture a no-touch proof that mixed regimes cannot masquerade as one edge."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_forex.time_utils import utc_now
from cas_forex.waste_direction_outcome_binding import (
    STATUS_COLLECTING,
    STATUS_READY,
    build_waste_direction_outcome_binding,
)


DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "runtime" / "redteam-operator-regime-attribution-latest.json"
)


def _cycle(index: int, regime: str | None) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "symbol": "NAS100",
        "timeframe": "H1",
        "direction": "LONG",
        "decision_ref": f"regime-decision-{index}",
        "directional_hypothesis": {
            "direction": "LONG",
            "profile": "regime-redteam",
        },
    }
    if regime is not None:
        candidate["regime"] = regime
    return {
        "cycle_id": f"regime-cycle-{index}",
        "generated_at": f"2026-07-14T12:{index:02d}:00+00:00",
        "decision": "EXECUTE",
        "candidate": candidate,
        "edge": {"status": "PASS", "has_edge_token": True},
        "execute_result": {
            "status": "EXECUTED",
            "broker_ticket": f"regime-ticket-{index}",
        },
    }


def _attempt(index: int) -> dict[str, Any]:
    return {
        "attempt_id": f"regime-attempt-{index}",
        "status": "ATTEMPT_RECORDED",
        "mode": "PAPER",
        "order_id": f"waste-regime-decision-{index}",
        "decision_ref": f"regime-decision-{index}",
        "symbol": "NAS100",
        "direction": "LONG",
        "volume": 0.01,
        "executed": True,
        "result_finalized": True,
        "pre_trade_estimate": {
            "entry_price": 100.0,
            "stop_loss": 99.0,
            "lots": 0.01,
            "risk_at_stop_usd": 1.0,
            "unit_value_source": "broker.trade_tick_value/trade_tick_size",
            "broker_unit_value_per_lot_usd": 100.0,
            "broker_contract_constraints": {
                "tick_size": 0.01,
                "tick_value": 1.0,
                "tick_value_loss": 1.0,
            },
        },
        "outcome": {
            "broker_ticket": f"regime-ticket-{index}",
            "broker_mode": "PAPER_MT5",
        },
    }


def _history(count: int) -> dict[str, Any]:
    return {
        "report_kind": "cas_forex_mt5_deal_history_ingest_report",
        "ingest_status": "MT5_DEAL_HISTORY_JOINED_TO_MEMORY",
        "account_mode": "demo",
        "history_records": [
            {
                "broker_ticket": f"regime-ticket-{index}",
                "ticket": f"regime-ticket-{index}",
                "symbol": "NAS100",
                "direction": "buy",
                "broker_mode": "PAPER_MT5",
                "profit": 10.0,
                "gross_profit": 11.0,
                "commission": -1.0,
                "swap": 0.0,
                "open_time": f"2026-07-14T12:{index:02d}:00+00:00",
                "close_time": f"2026-07-14T13:{index:02d}:00+00:00",
            }
            for index in range(1, count + 1)
        ],
    }


def _scenario(regimes: Sequence[str | None]) -> dict[str, Any]:
    count = len(regimes)
    report = build_waste_direction_outcome_binding(
        cycles=[_cycle(index, regime) for index, regime in enumerate(regimes, 1)],
        attempts=[_attempt(index) for index in range(1, count + 1)],
        history_report=_history(count),
        min_bound_outcomes_for_promotion=5,
    )
    group = dict((report.get("group_stats") or [{}])[0])
    return {
        "status": report.get("status"),
        "outcome_ready_for_promotion": report.get("outcome_ready_for_promotion"),
        "pooled_profit_cannot_promote_across_regimes": report.get(
            "pooled_profit_cannot_promote_across_regimes"
        ),
        "regime_attributed_bound_count": report.get(
            "regime_attributed_bound_count"
        ),
        "unknown_regime_bound_count": report.get("unknown_regime_bound_count"),
        "pooled_group": {
            key: group.get(key)
            for key in (
                "trades",
                "net_pnl",
                "sample_ready",
                "growth_robust_to_single_best_outcome",
                "regime_count",
                "known_regime_trade_count",
                "unknown_regime_trade_count",
                "regime_outcome_ready_for_promotion",
                "press_size_supported_by_robust_outcomes",
                "outcome_ready_for_promotion",
            )
        },
        "regime_breakdown": group.get("regime_breakdown") or [],
    }


def build_report() -> dict[str, Any]:
    mixed = _scenario(["trend", "trend", "trend", "range", "range", "range"])
    unknown = _scenario([None, None, None, None, None])
    independently_ready = _scenario(
        ["trend", "trend", "trend", "trend", "trend", "range"]
    )
    checks = {
        "mixed_pooled_group_is_sample_ready_and_profitable": (
            mixed["pooled_group"]["sample_ready"] is True
            and float(mixed["pooled_group"]["net_pnl"] or 0.0) > 0.0
        ),
        "mixed_regimes_do_not_authorize_press_or_promotion": (
            mixed["status"] == STATUS_COLLECTING
            and mixed["outcome_ready_for_promotion"] is False
            and mixed["pooled_group"]["press_size_supported_by_robust_outcomes"]
            is False
        ),
        "unknown_regime_history_cannot_promote": (
            unknown["status"] == STATUS_COLLECTING
            and unknown["outcome_ready_for_promotion"] is False
            and int(unknown["unknown_regime_bound_count"] or 0) == 5
        ),
        "independently_ready_regime_can_promote": (
            independently_ready["status"] == STATUS_READY
            and independently_ready["outcome_ready_for_promotion"] is True
            and independently_ready["pooled_group"][
                "regime_outcome_ready_for_promotion"
            ]
            is True
        ),
    }
    passed = all(checks.values())
    report: dict[str, Any] = {
        "report_kind": "cas_forex_operator_regime_attribution_redteam",
        "generated_at": utc_now().isoformat(),
        "status": (
            "PASS_NO_TOUCH_REGIME_ATTRIBUTION"
            if passed
            else "FAIL_REVIEW_REQUIRED"
        ),
        "invariant_checks": checks,
        "mixed_regime_scenario": mixed,
        "unknown_regime_scenario": unknown,
        "independently_ready_regime_scenario": independently_ready,
        "read_only": True,
        "dry_run": True,
        "broker_touched": False,
        "order_send_called": False,
        "position_modified": False,
        "money_moved": False,
        "live_authority_changed": False,
        "claim_boundary": (
            "This synthetic PAPER/DEMO outcome-binding proof exercises regime "
            "attribution without broker or money effects. It proves mixed or "
            "UNKNOWN regimes cannot authorize press sizing or promotion. It does "
            "not prove durable edge, future profit, external live readiness, or "
            "provider-backed money movement. External live money remains CURRENTLY "
            "NOT LICENSED."
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
    temporary = target.with_suffix(f"{target.suffix}.tmp")
    temporary.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(target)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS_NO_TOUCH_REGIME_ATTRIBUTION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
