"""Replay entry-learning and fresh-position churn defects without broker effects."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_forex.ai_operator_position_edge import (
    PROMPT_VERSION as POSITION_PROMPT_VERSION,
    review_management_actions_with_operator,
)
from cas_forex.ai_operator_trade_edge import (
    _candidate_group_context,
    _context_group_stats,
)
from cas_forex.time_utils import utc_now


DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "runtime" / "redteam-operator-learning-and-fresh-close-latest.json"
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _load_jsonl_ticket(path: Path, ticket: str) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if ticket not in line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, Mapping):
                    latest = dict(payload)
    except OSError:
        return {}
    return latest


def _find_attempt_by_ticket(payload: Mapping[str, Any], ticket: str) -> dict[str, Any]:
    attempts = payload.get("attempts")
    if not isinstance(attempts, Mapping):
        return {}
    for raw in attempts.values():
        if not isinstance(raw, Mapping):
            continue
        if ticket in json.dumps(raw, sort_keys=True, default=str):
            return dict(raw)
    return {}


def _find_bound_outcome(payload: Mapping[str, Any], ticket: str) -> dict[str, Any]:
    for raw in payload.get("bound_outcomes") or []:
        if not isinstance(raw, Mapping):
            continue
        if str(raw.get("broker_ticket") or "") == ticket:
            return dict(raw)
    return {}


class _CloseNowProvider:
    def generate(self, prompt: str, system: str | None = None, **_kwargs: Any) -> dict[str, Any]:
        payload = json.loads(prompt)
        group = payload["position_action_candidates"][0]
        action = group["actions"][0]
        return {
            "ok": True,
            "text": json.dumps(
                {
                    "position_decisions": [
                        {
                            "position_key": group["position_key"],
                            "decision": "SELECT",
                            "action_ref": action["action_ref"],
                            "selected_intent": action["intent"],
                            "growth_case": "ACCOUNT_RISK_REDUCTION",
                            "conviction": "HIGH",
                            "reason": (
                                "The small opening loss creates account pressure, so close now."
                            ),
                        }
                    ],
                    "summary": "Close the fresh position to reduce account pressure.",
                }
            ),
            "provider": "redteam-contract-provider",
            "provider_label": "Red-team contract provider",
            "paid": False,
            "failover": False,
            "error": None,
        }


class _NoTouchBridge:
    def __init__(self) -> None:
        self.broker_calls = 0

    def will_execute_real_order(self) -> bool:
        return False

    def is_demo_account(self) -> bool:
        return True

    def get_account_info(self) -> dict[str, float]:
        return {
            "balance": 45_043.18,
            "equity": 45_042.96,
            "margin": 8.01,
            "margin_free": 45_034.95,
            "profit": -0.22,
            "leverage": 500,
        }

    def modify_position(self, *_args: Any, **_kwargs: Any) -> None:
        self.broker_calls += 1
        raise AssertionError("Position-edge review must never call the broker")


def _group_evidence_replay() -> dict[str, Any]:
    strategy = "live_candle_broker-candle_h1"
    candidate = {
        "intent_id": "intent-spx-h1-redteam",
        "symbol": "SPX500",
        "timeframe": "H1",
        "direction": "LONG",
        "strategy": strategy,
    }
    recent_losses = [
        {
            "binding_id": f"loss-{index}",
            "broker_ticket": f"ticket-{index}",
            "symbol": "SPX500",
            "timeframe": "H1",
            "direction": "LONG",
            "strategy_id": strategy,
            "profile": strategy,
            "net_pnl": value,
            "net_pnl_per_1_lot_usd": value * 100.0,
            "admission_stop_risk_usd": 20.0,
            "realized_after_cost_r_multiple": value / 20.0,
            "close_time": f"2026-07-13T2{index}:00:00+00:00",
        }
        for index, value in enumerate((-0.06, -0.48, -0.83))
    ]
    broker_exact = {
        "symbol": "SPX500",
        "timeframe": "H1",
        "direction": "LONG",
        "profile": strategy,
        "trades": 4,
        "wins": 1,
        "losses": 3,
        "sample_ready": True,
        "net_pnl": 1.47,
        "after_cost_expectancy": 0.3675,
        "after_cost_expectancy_r": 0.0132,
        "risk_normalized_trade_count": 4,
        "risk_normalized_evidence_complete": True,
        "after_cost_expectancy_per_1_lot_usd": 36.75,
    }
    combined_wrong_profile = {**broker_exact, "profile": "range_fade"}
    legacy = _candidate_group_context(
        [candidate],
        recent_losses,
        group_stats=[combined_wrong_profile],
    )[candidate["intent_id"]]
    merged_stats = _context_group_stats(
        {
            "combined_paper_learning": {"group_stats": [combined_wrong_profile]},
            "broker_verified_mt5_demo": {"group_stats": [broker_exact]},
        }
    )
    corrected = _candidate_group_context(
        [candidate],
        recent_losses,
        group_stats=merged_stats,
    )[candidate["intent_id"]]
    return {
        "defect": "combined group table replaced broker-verified exact group evidence",
        "legacy_selection": {
            "exact_group_source": legacy.get("exact_group_source"),
            "growth_evidence_state": legacy.get("growth_evidence_state"),
            "trades": (legacy.get("exact_group") or {}).get("trades"),
            "net_pnl": (legacy.get("exact_group") or {}).get("net_pnl"),
            "after_cost_expectancy_r": (legacy.get("exact_group") or {}).get(
                "after_cost_expectancy_r"
            ),
        },
        "corrected_selection": {
            "merged_group_count": len(merged_stats),
            "exact_group_source": corrected.get("exact_group_source"),
            "growth_evidence_state": corrected.get("growth_evidence_state"),
            "trades": (corrected.get("exact_group") or {}).get("trades"),
            "net_pnl": (corrected.get("exact_group") or {}).get("net_pnl"),
            "after_cost_expectancy_r": (corrected.get("exact_group") or {}).get(
                "after_cost_expectancy_r"
            ),
        },
        "pass": (
            legacy.get("growth_evidence_state")
            == "EXACT_GROUP_NON_POSITIVE_AND_SPARSE"
            and corrected.get("growth_evidence_state")
            == "EXACT_GROUP_POSITIVE_SAMPLE_READY"
            and (corrected.get("exact_group") or {}).get("net_pnl") == 1.47
        ),
    }


def _fresh_close_replay() -> dict[str, Any]:
    ticket = 45945223
    action = {
        "action_id": f"ai-hedge-management:broker:{ticket}:close_full",
        "intent": "close_full",
        "broker_ticket": ticket,
        "position_id": f"broker:{ticket}",
        "symbol": "XAUUSD",
        "side": "SHORT",
        "timeframe": "H1",
        "strategy": "live_candle_index-tsmom-126-d1_h1",
        "broker_method": "close_position",
        "open_price": 4003.05,
        "current_price": 4003.27,
        "previous_stop_loss": 4028.24,
        "original_stop_loss": 4028.24,
        "stop_loss": None,
        "previous_take_profit": 3964.45,
        "take_profit": None,
        "original_volume": 0.01,
        "volume": None,
        "r_multiple": -0.0087,
        "r_multiple_basis": "ORIGINAL_ENTRY_STOP_FROM_ORDER_RECEIPT",
        "floating_pnl_usd": -0.22,
        "position_price_pnl_usd": -0.22,
        "swap_usd": 0.0,
        "commission_usd": 0.0,
        "net_open_pnl_after_reported_costs_usd": -0.22,
        "open_pnl_basis": "PRICE_PLUS_REPORTED_SWAP_AND_COMMISSION",
        "opened_at_iso": "2026-07-13T22:12:46+00:00",
        "age_days": 24.0 / 86_400.0,
        "urgency": "LOW",
        "risk_effect": "exposure_reducing_full_close",
        "reason": "Close only if current evidence invalidates the hold thesis.",
        "operator_discretionary_option": True,
        "operator_selection_required": True,
        "option_origin": "AI_OPERATOR_DISCRETIONARY_POSITION_REVIEW",
        "decision_parameters": {
            "close_basis": "RISK_REDUCTION_REQUIRES_THESIS_REVIEW",
            "thesis_invalidation_evidence_supplied": False,
        },
        "evidence_refs": ["position.r_multiple"],
    }
    snapshot = {
        "status": "FRESH",
        "bridge_executes_real_orders": False,
        "management_policy": {"take_profit_reward_risk": 1.5394},
        "position_risk": {"status": "WITHIN_CAP"},
        "quote_attempts": [
            {
                "symbol": "XAUUSD",
                "usable": True,
                "quote_source": "redteam_snapshot",
                "age_seconds": 0.1,
            }
        ],
        "positions": [
            {
                "broker_ticket": ticket,
                "row_id": f"broker:{ticket}",
                "symbol": "XAUUSD",
                "side": "SHORT",
                "timeframe": "H1",
                "strategy": "live_candle_index-tsmom-126-d1_h1",
                "lot_size": 0.01,
                "open_price": 4003.05,
                "current_price": 4003.27,
                "stop_loss": 4028.24,
                "take_profit": 3964.45,
                "floating_pnl_usd": -0.22,
                "net_open_pnl_after_reported_costs_usd": -0.22,
            }
        ],
    }
    decision_context = {
        "status": "REALIZED_OUTCOMES_AVAILABLE",
        "recent_outcomes": [],
        "group_stats": [],
    }
    config = SimpleNamespace(
        live_mode=False,
        ai_operator_position_edge_enabled=True,
        ai_operator_position_edge_timeout_seconds=12,
        ai_operator_position_edge_review_interval_seconds=60,
        ai_control_values={"trailing_stop_enabled": 1, "trailing_lock_fraction": 0.5},
    )
    bridge = _NoTouchBridge()
    with TemporaryDirectory(prefix="cas-forex-redteam-position-v14-") as temp_dir:
        selected, report = review_management_actions_with_operator(
            [action],
            position_snapshot=snapshot,
            bridge=bridge,
            config=config,
            provider=_CloseNowProvider(),
            enabled=True,
            decision_context=decision_context,
            audit_path=Path(temp_dir) / "audit.jsonl",
            latest_path=Path(temp_dir) / "latest.json",
        )
    return {
        "defect": "fresh protected position closed on initial spread as generic account risk",
        "prompt_version": report.get("prompt_version"),
        "attempted_model_choice": "close_full",
        "position_age_seconds": 24.0,
        "current_r": -0.0087,
        "adverse_r_threshold": -0.10,
        "minimum_observation_seconds": 900.0,
        "deterministic_thesis_invalidation": False,
        "selected_action_count": len(selected),
        "decision_status": report.get("status"),
        "model_error": report.get("model_error"),
        "broker_calls": bridge.broker_calls,
        "broker_touched": bool(report.get("broker_touched")),
        "money_moved": bool(report.get("money_moved")),
        "pass": (
            POSITION_PROMPT_VERSION == "ai_operator_position_edge.v14"
            and report.get("status")
            == "MODEL_UNAVAILABLE_PAPER_DISCRETIONARY_STAND_DOWN"
            and not selected
            and bridge.broker_calls == 0
            and "initial spread or a tiny opening loss is not thesis invalidation"
            in str(report.get("model_error") or "")
        ),
    }


def _natural_runtime_evidence() -> dict[str, Any]:
    ticket = "45945223"
    trade = _load_json(REPO_ROOT / "runtime" / "ai-operator-trade-edge-latest.json")
    attempts = _load_json(REPO_ROOT / "runtime" / "order-attempts.json")
    learning = _load_json(REPO_ROOT / "runtime" / "mt5-demo-learning-sync.json")
    natural_v14 = _load_json(
        REPO_ROOT / "runtime" / "operator-position-v14-natural-receipt-latest.json"
    )
    starvation = _load_json(
        REPO_ROOT / "runtime" / "redteam-entry-candidate-actionability-latest.json"
    )
    attempt = _find_attempt_by_ticket(attempts, ticket)
    management = _load_jsonl_ticket(
        REPO_ROOT / "runtime" / "ai-hedge-management-execution-audit.jsonl",
        ticket,
    )
    bound = _find_bound_outcome(learning, ticket)
    trade_decisions = [
        dict(row) for row in trade.get("decisions") or [] if isinstance(row, Mapping)
    ]
    management_action = management.get("selected_action")
    management_action = (
        dict(management_action) if isinstance(management_action, Mapping) else {}
    )
    result = attempt.get("result") if isinstance(attempt.get("result"), Mapping) else {}
    money_impact = (
        result.get("money_impact") if isinstance(result.get("money_impact"), Mapping) else {}
    )
    growth = learning.get("account_growth")
    growth = dict(growth) if isinstance(growth, Mapping) else {}
    account = growth.get("account") if isinstance(growth.get("account"), Mapping) else {}
    overall = learning.get("learning_overall")
    overall = dict(overall) if isinstance(overall, Mapping) else {}
    return {
        "candidate_actionability_scan": {
            "status": starvation.get("status"),
            "attempt_count": starvation.get("attempt_count"),
            "blocked_pass_count": starvation.get("blocked_pass_count"),
            "later_lane_observed_after_blocked_pass": starvation.get(
                "later_lane_observed_after_first_blocked_pass"
            ),
            "broker_execution_touched": starvation.get("broker_execution_touched"),
            "event_hash": starvation.get("event_hash"),
        },
        "natural_entry_decision": {
            "prompt_version": trade.get("prompt_version"),
            "status": trade.get("status"),
            "operator_approved_count": trade.get("operator_approved_count"),
            "provider_label": trade.get("provider_label"),
            "decision": trade_decisions[0] if trade_decisions else {},
            "event_hash": trade.get("event_hash"),
        },
        "natural_demo_order": {
            "attempt_id": attempt.get("attempt_id"),
            "decision_ref": attempt.get("decision_ref"),
            "symbol": attempt.get("symbol"),
            "direction": attempt.get("direction"),
            "volume": attempt.get("volume"),
            "result_status": attempt.get("result_status"),
            "broker_bridge_touched": money_impact.get("broker_bridge_touched"),
            "external_broker_terminal": money_impact.get("external_broker_terminal"),
            "is_demo_account": money_impact.get("is_demo_account"),
            "live_money_broker": money_impact.get("live_money_broker"),
            "ticket": ticket,
        },
        "legacy_immediate_close": {
            "ticket": ticket,
            "prompt_version": management_action.get("operator_prompt_version"),
            "operator_event_hash": management.get("operator_position_edge_event_hash"),
            "decision": {
                "action_ref": management_action.get("operator_action_ref"),
                "intent": management_action.get("intent"),
                "growth_case": management_action.get("operator_growth_case"),
                "reason": management_action.get("operator_reason"),
            },
            "management_status": management.get("status"),
            "broker_method_called": management.get("broker_method_called"),
            "broker_touched": management.get("broker_touched"),
            "terminal_receipt_status": management.get("terminal_receipt_status"),
            "bound_outcome_net_pnl": bound.get("net_pnl"),
            "bound_outcome_close_time": bound.get("close_time"),
            "bound_outcome_close_reason": bound.get("close_reason"),
        },
        "natural_v14_position_management": {
            "status": natural_v14.get("status"),
            "prompt_version": (
                (natural_v14.get("operator_decision") or {}).get("prompt_version")
                if isinstance(natural_v14.get("operator_decision"), Mapping)
                else None
            ),
            "operator_event_hash": (
                (natural_v14.get("operator_decision") or {}).get("event_hash")
                if isinstance(natural_v14.get("operator_decision"), Mapping)
                else None
            ),
            "execution_count": len(natural_v14.get("executions") or []),
            "cycle_net_pnl": natural_v14.get("cycle_net_pnl"),
            "capture_controls": natural_v14.get("capture_controls"),
            "event_hash": natural_v14.get("event_hash"),
        },
        "account_and_learning_truth": {
            "current_demo_balance": account.get("current_balance_account_currency"),
            "current_demo_equity": account.get("current_equity_account_currency"),
            "bound_trade_count": learning.get("bound_trade_count"),
            "bound_outcome_net_pnl": overall.get("net_pnl"),
            "bound_outcome_after_cost_expectancy_r": overall.get(
                "after_cost_expectancy_r"
            ),
            "cashflow_adjusted_all_time_growth": (
                (growth.get("realized_growth") or {}).get(
                    "cashflow_adjusted_all_time_account_currency"
                )
                if isinstance(growth.get("realized_growth"), Mapping)
                else None
            ),
            "durable_positive_edge_proven": False,
        },
    }


def build_report() -> dict[str, Any]:
    group_replay = _group_evidence_replay()
    fresh_close_replay = _fresh_close_replay()
    natural = _natural_runtime_evidence()
    report: dict[str, Any] = {
        "report_kind": "cas_forex_operator_learning_and_fresh_close_redteam",
        "generated_at": utc_now().isoformat(),
        "status": (
            "PASS_NO_TOUCH_REPLAY"
            if group_replay.get("pass") and fresh_close_replay.get("pass")
            else "FAIL_REVIEW_REQUIRED"
        ),
        "group_evidence_replacement_replay": group_replay,
        "fresh_position_close_replay": fresh_close_replay,
        "natural_runtime_evidence": natural,
        "redteam_broker_touched": False,
        "redteam_order_send_called": False,
        "redteam_money_moved": False,
        "claim_boundary": (
            "The replay sections use synthetic decision evidence and a no-touch bridge. "
            "They prove current selection and validation behavior, not future profitability. "
            "The natural-runtime section quotes prior MT5 demo receipts already present in "
            "the audit ledger; this script does not place, close, or modify any trade, move "
            "money, enable live trading, or authorize live money. Live money remains "
            "CURRENTLY NOT LICENSED."
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
    return 0 if report["status"] == "PASS_NO_TOUCH_REPLAY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
