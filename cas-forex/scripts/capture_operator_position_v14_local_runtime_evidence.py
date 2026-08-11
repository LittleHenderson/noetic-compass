from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    REPO_ROOT / "runtime" / "operator-position-v14-local-natural-receipt-latest.json"
)
EXPECTED_TICKET = "45945233"
EXPECTED_INTENT = "close_full"
EXPECTED_NET_OUTCOME = 12.42


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _load_json_lines(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_record(path: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "report_kind": (payload or {}).get("report_kind"),
        "generated_at": (payload or {}).get("generated_at"),
        "event_hash": (payload or {}).get("event_hash"),
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build_evidence(
    *,
    decision: dict[str, Any],
    executions: list[dict[str, Any]],
    learning: dict[str, Any],
    growth: dict[str, Any],
    source_records: dict[str, dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    event_hash = str(decision.get("event_hash") or "")
    _require(decision.get("prompt_version") == "ai_operator_position_edge.v14", "decision is not v14")
    _require(decision.get("status") == "AI_OPERATOR_POSITION_DECIDED", "decision did not complete")
    _require(decision.get("model_ok") is True, "decision was not model-valid")
    _require(decision.get("provider") == "local-fallback", "decision was not made by the local provider")
    _require(decision.get("model_ref") == "deepseek-r1:latest", "unexpected local model")
    _require(bool(event_hash), "decision event hash is missing")
    _require(
        (decision.get("model_context_projection") or {}).get(
            "full_context_retained_in_audit"
        )
        is True,
        "full decision context was not retained",
    )
    _require(
        decision.get("model_response_normalization_count") == 0,
        "natural proof must use canonical model output",
    )

    selected = [
        row
        for row in decision.get("decisions", [])
        if isinstance(row, dict) and row.get("decision") == "SELECT"
    ]
    _require(len(selected) == 1, "expected one exact selected position action")
    decision_row = selected[0]
    _require(
        str(decision_row.get("position_key") or "").split(":", 1)[-1]
        == EXPECTED_TICKET,
        "selected ticket changed",
    )
    _require(decision_row.get("intent") == EXPECTED_INTENT, "selected intent changed")
    _require(bool(decision_row.get("action_ref")), "selected action_ref is missing")

    matching_executions = []
    for row in executions:
        selected_action = row.get("selected_action") or {}
        if (
            str(selected_action.get("broker_ticket") or "") == EXPECTED_TICKET
            and selected_action.get("operator_event_hash") == event_hash
        ):
            matching_executions.append(row)
    _require(len(matching_executions) == 1, "expected one ticket-and-event-bound execution")
    execution = matching_executions[0]
    selected_action = execution.get("selected_action") or {}
    receipt = execution.get("terminal_receipt") or {}
    _require(execution.get("status") == "EXECUTED_RECONCILED", "execution was not reconciled")
    _require(execution.get("broker_touched") is True, "execution did not touch the broker bridge")
    _require(execution.get("money_moved") is False, "execution unexpectedly moved money")
    _require(
        execution.get("per_action_owner_confirmation_required") is False,
        "execution unexpectedly required per-action confirmation",
    )
    _require(
        (execution.get("execution_guard") or {}).get("status") == "ACCEPT",
        "execution guard did not accept",
    )
    _require(execution.get("terminal_receipt_status") == "RECONCILED", "terminal receipt is not reconciled")
    _require(selected_action.get("intent") == EXPECTED_INTENT, "execution intent changed")
    _require(
        selected_action.get("operator_action_ref") == decision_row.get("action_ref"),
        "execution action_ref is not bound to the decision",
    )

    outcomes = {
        str(row.get("broker_ticket") or ""): row
        for row in learning.get("bound_outcomes", [])
        if isinstance(row, dict)
    }
    _require(learning.get("status") == "MT5_DEMO_LEARNING_BOUND", "demo learning is not bound")
    _require(learning.get("broker_order_touched") is False, "learning sync touched the broker")
    _require(learning.get("money_moved") is False, "learning sync moved money")
    _require(EXPECTED_TICKET in outcomes, "closed outcome is missing")
    outcome = outcomes[EXPECTED_TICKET]
    actual_net = float(outcome.get("net_pnl"))
    _require(
        abs(actual_net - EXPECTED_NET_OUTCOME) < 1e-9,
        "after-cost outcome changed",
    )

    account = growth.get("account") or {}
    _require(
        growth.get("status") == "RECONCILED_CASHFLOW_ADJUSTED_GROWTH",
        "account growth is not reconciled",
    )
    report: dict[str, Any] = {
        "report_kind": "cas_forex_operator_position_v14_local_natural_runtime_evidence",
        "status": "PASS_LOCAL_V14_POSITION_MANAGEMENT_RECEIPT",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "claim_boundary": (
            "This is read-only historical evidence of one natural PAPER/DEMO local-model "
            "Operator decision and broker-management effect. It proves local structured "
            "decision continuity, exact action binding, guarded MT5 demo execution, terminal "
            "reconciliation, and after-cost outcome binding for the cited ticket. It does not "
            "prove durable edge, future profit, live-money readiness, a larger-than-minimum "
            "lot, protected-winner scale-in, or provider-backed money movement."
        ),
        "operator_decision": {
            "prompt_version": decision.get("prompt_version"),
            "provider": decision.get("provider"),
            "provider_label": decision.get("provider_label"),
            "model_ref": decision.get("model_ref"),
            "model_backend": decision.get("model_backend"),
            "model_ok": decision.get("model_ok"),
            "event_hash": event_hash,
            "action_ref": decision_row.get("action_ref"),
            "intent": decision_row.get("intent"),
            "growth_case": decision_row.get("growth_case"),
            "reason": decision_row.get("reason"),
            "model_prompt_chars": decision.get("model_prompt_chars"),
            "raw_response_chars": decision.get("raw_response_chars"),
            "model_response_normalization_count": decision.get(
                "model_response_normalization_count"
            ),
            "full_context_retained_in_audit": (
                decision.get("model_context_projection") or {}
            ).get("full_context_retained_in_audit"),
        },
        "execution": {
            "ticket": EXPECTED_TICKET,
            "symbol": selected_action.get("symbol"),
            "intent": selected_action.get("intent"),
            "action_ref": selected_action.get("operator_action_ref"),
            "growth_case": selected_action.get("operator_growth_case"),
            "execution_status": execution.get("status"),
            "guard_status": (execution.get("execution_guard") or {}).get("status"),
            "broker_method": (execution.get("broker_result") or {}).get("method"),
            "broker_touched": execution.get("broker_touched"),
            "per_action_owner_confirmation_required": execution.get(
                "per_action_owner_confirmation_required"
            ),
            "terminal_receipt_status": execution.get("terminal_receipt_status"),
            "actual_remaining_volume": receipt.get("actual_remaining_volume"),
            "money_moved": execution.get("money_moved"),
        },
        "bound_outcome": {
            "ticket": EXPECTED_TICKET,
            "symbol": outcome.get("symbol"),
            "direction": outcome.get("direction"),
            "profile": outcome.get("profile"),
            "timeframe": outcome.get("timeframe"),
            "open_time": outcome.get("open_time"),
            "close_time": outcome.get("close_time"),
            "close_reason": outcome.get("close_reason"),
            "gross_profit": outcome.get("gross_profit"),
            "commission": outcome.get("commission"),
            "swap": outcome.get("swap"),
            "net_pnl": outcome.get("net_pnl"),
            "admission_stop_risk_usd": outcome.get("admission_stop_risk_usd"),
            "realized_after_cost_r_multiple": outcome.get(
                "realized_after_cost_r_multiple"
            ),
        },
        "learning": {
            "status": learning.get("status"),
            "bound_trade_count": learning.get("bound_trade_count"),
            "history_record_count": learning.get("history_record_count"),
            "broker_order_touched": learning.get("broker_order_touched"),
            "money_moved": learning.get("money_moved"),
        },
        "account_after_action": {
            "account_mode": account.get("account_mode"),
            "server": account.get("server"),
            "currency": account.get("currency"),
            "balance": account.get("current_balance_account_currency"),
            "equity": account.get("current_equity_account_currency"),
            "growth_status": growth.get("status"),
            "growth_event_hash": growth.get("event_hash"),
        },
        "capture_controls": {
            "capture_order_send_called": False,
            "capture_broker_write_called": False,
            "capture_money_moved": False,
            "historical_runtime_broker_touched": True,
            "historical_runtime_money_moved": False,
        },
        "source_records": source_records,
    }
    report["event_hash"] = _canonical_hash(report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture the natural local-model v14 position receipt without touching MT5."
    )
    parser.add_argument(
        "--decision",
        type=Path,
        default=REPO_ROOT / "runtime" / "ai-operator-position-edge-latest.json",
    )
    parser.add_argument(
        "--execution-audit",
        type=Path,
        default=REPO_ROOT / "runtime" / "ai-hedge-management-execution-audit.jsonl",
    )
    parser.add_argument(
        "--learning",
        type=Path,
        default=REPO_ROOT / "runtime" / "mt5-demo-learning-sync.json",
    )
    parser.add_argument(
        "--growth",
        type=Path,
        default=REPO_ROOT / "runtime" / "mt5-account-growth.json",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    decision = _load_json(args.decision)
    learning = _load_json(args.learning)
    growth = _load_json(args.growth)
    report = build_evidence(
        decision=decision,
        executions=_load_json_lines(args.execution_audit),
        learning=learning,
        growth=growth,
        source_records={
            "operator_position_edge": _source_record(args.decision, decision),
            "management_execution_audit": _source_record(args.execution_audit),
            "demo_learning": _source_record(args.learning, learning),
            "account_growth": _source_record(args.growth, growth),
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "event_hash": report["event_hash"],
                "output": str(args.output.resolve()),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
