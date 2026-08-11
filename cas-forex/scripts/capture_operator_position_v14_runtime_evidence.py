from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "runtime" / "operator-position-v14-natural-receipt-latest.json"
EXPECTED_ACTIONS = {
    "45945226": "close_full",
    "45945227": "trail_stop",
}
EXPECTED_NET_OUTCOMES = {
    "45945226": -2.27,
    "45945227": 1.00,
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_record(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "report_kind": payload.get("report_kind"),
        "generated_at": payload.get("generated_at") or payload.get("updated_at_iso"),
        "event_hash": payload.get("event_hash"),
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build_evidence(
    *,
    decision: dict[str, Any],
    cycle_state: dict[str, Any],
    learning: dict[str, Any],
    growth: dict[str, Any],
    source_records: dict[str, dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    operator_event_hash = str(decision.get("event_hash") or "")
    _require(decision.get("prompt_version") == "ai_operator_position_edge.v14", "decision is not v14")
    _require(decision.get("status") == "AI_OPERATOR_POSITION_DECIDED", "decision did not complete")
    _require(decision.get("model_ok") is True, "decision was not produced by a healthy model response")
    _require(bool(operator_event_hash), "decision event hash is missing")
    _require(decision.get("model_response_normalization_count") == 0, "natural proof must use canonical model output")

    selected_decisions = {
        str(row.get("position_key", "")).split(":", 1)[-1]: row
        for row in decision.get("decisions", [])
        if isinstance(row, dict) and row.get("decision") == "SELECT"
    }
    _require(set(selected_decisions) == set(EXPECTED_ACTIONS), "natural v14 decision ticket set changed")
    for ticket, intent in EXPECTED_ACTIONS.items():
        row = selected_decisions[ticket]
        _require(row.get("intent") == intent, f"ticket {ticket} decision intent changed")
        _require(bool(row.get("action_ref")), f"ticket {ticket} lacks an exact action_ref")

    latest_cycle = cycle_state.get("latest_cycle")
    _require(isinstance(latest_cycle, dict), "latest management cycle is missing")
    _require(latest_cycle.get("status") == "ACTIONS_EXECUTED", "management cycle did not execute")
    _require(latest_cycle.get("operator_position_edge_prompt_version") == "ai_operator_position_edge.v14", "cycle is not bound to v14")
    _require(latest_cycle.get("per_action_owner_confirmation_required") is False, "cycle unexpectedly required per-action confirmation")
    _require(latest_cycle.get("broker_touched") is True, "cycle did not touch the broker bridge")
    _require(latest_cycle.get("terminal_effect_count") == len(EXPECTED_ACTIONS), "terminal effect count changed")

    execution_rows: dict[str, dict[str, Any]] = {}
    for row in latest_cycle.get("executions", []):
        if not isinstance(row, dict):
            continue
        selected = row.get("selected_action") or {}
        ticket = str(selected.get("broker_ticket") or "")
        if ticket:
            execution_rows[ticket] = row
    _require(set(EXPECTED_ACTIONS).issubset(execution_rows), "one or more natural executions are missing")

    execution_evidence: list[dict[str, Any]] = []
    for ticket, intent in EXPECTED_ACTIONS.items():
        row = execution_rows[ticket]
        selected = row.get("selected_action") or {}
        decision_row = selected_decisions[ticket]
        _require(row.get("status") == "EXECUTED_RECONCILED", f"ticket {ticket} was not reconciled")
        _require(row.get("broker_touched") is True, f"ticket {ticket} did not touch the broker")
        _require(row.get("money_moved") is False, f"ticket {ticket} unexpectedly moved money")
        _require(row.get("operator_position_edge_event_hash") == operator_event_hash, f"ticket {ticket} event hash drifted")
        _require(selected.get("intent") == intent, f"ticket {ticket} execution intent changed")
        _require(selected.get("operator_action_ref") == decision_row.get("action_ref"), f"ticket {ticket} exact action_ref drifted")
        _require(selected.get("requires_owner_confirmation") is False, f"ticket {ticket} unexpectedly required confirmation")
        _require((row.get("execution_guard") or {}).get("status") == "ACCEPT", f"ticket {ticket} guard did not accept")
        _require(row.get("terminal_receipt_status") == "RECONCILED", f"ticket {ticket} receipt is not reconciled")
        receipt = row.get("terminal_receipt") or {}
        execution_evidence.append(
            {
                "ticket": ticket,
                "symbol": selected.get("symbol"),
                "intent": intent,
                "action_ref": decision_row.get("action_ref"),
                "growth_case": decision_row.get("growth_case"),
                "operator_reason": decision_row.get("reason"),
                "opened_at_iso": selected.get("opened_at_iso"),
                "opened_at_source": selected.get("opened_at_source"),
                "position_age_days": selected.get("age_days"),
                "r_multiple": selected.get("r_multiple"),
                "broker_method": row.get("broker_result", {}).get("method"),
                "guard_status": row.get("execution_guard", {}).get("status"),
                "execution_status": row.get("status"),
                "terminal_receipt_status": row.get("terminal_receipt_status"),
                "actual_remaining_volume": receipt.get("actual_remaining_volume"),
                "actual_stop_loss": receipt.get("actual_stop_loss"),
                "actual_take_profit": receipt.get("actual_take_profit"),
                "broker_touched": row.get("broker_touched"),
                "per_action_owner_confirmation_required": row.get("per_action_owner_confirmation_required"),
                "money_moved": row.get("money_moved"),
            }
        )

    outcomes = {
        str(row.get("broker_ticket") or ""): row
        for row in learning.get("bound_outcomes", [])
        if isinstance(row, dict)
    }
    _require(learning.get("status") == "MT5_DEMO_LEARNING_BOUND", "demo learning is not bound")
    _require(learning.get("broker_order_touched") is False, "learning sync unexpectedly touched the broker")
    _require(learning.get("money_moved") is False, "learning sync unexpectedly moved money")

    outcome_evidence: list[dict[str, Any]] = []
    for ticket, expected_net in EXPECTED_NET_OUTCOMES.items():
        _require(ticket in outcomes, f"ticket {ticket} is missing from bound outcomes")
        row = outcomes[ticket]
        actual_net = float(row.get("net_pnl"))
        _require(abs(actual_net - expected_net) < 1e-9, f"ticket {ticket} net outcome changed")
        outcome_evidence.append(
            {
                "ticket": ticket,
                "symbol": row.get("symbol"),
                "direction": row.get("direction"),
                "profile": row.get("profile"),
                "timeframe": row.get("timeframe"),
                "open_time": row.get("open_time"),
                "close_time": row.get("close_time"),
                "close_reason": row.get("close_reason"),
                "gross_profit": row.get("gross_profit"),
                "commission": row.get("commission"),
                "swap": row.get("swap"),
                "net_pnl": row.get("net_pnl"),
                "realized_after_cost_r_multiple": row.get("realized_after_cost_r_multiple"),
                "admission_risk_source": row.get("admission_risk_source"),
                "origin_source": row.get("origin_source"),
            }
        )

    account = growth.get("account") or {}
    _require(growth.get("status") == "RECONCILED_CASHFLOW_ADJUSTED_GROWTH", "account growth is not reconciled")
    report: dict[str, Any] = {
        "report_kind": "cas_forex_operator_position_v14_natural_runtime_evidence",
        "status": "PASS_NATURAL_V14_POSITION_MANAGEMENT_RECEIPT",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "claim_boundary": (
            "This is read-only historical evidence of one natural PAPER/DEMO Operator management cycle. "
            "It proves exact v14 action selection, guarded broker dispatch, terminal reconciliation, and "
            "outcome binding for the cited tickets. It does not prove durable edge, future profit, live-money "
            "readiness, a larger-than-minimum lot, protected-winner scale-in, or provider-backed money movement."
        ),
        "operator_decision": {
            "prompt_version": decision.get("prompt_version"),
            "status": decision.get("status"),
            "model_ok": decision.get("model_ok"),
            "provider_label": decision.get("provider_label"),
            "model_ref": decision.get("model_ref"),
            "model_backend": decision.get("model_backend"),
            "event_hash": operator_event_hash,
            "summary": decision.get("summary"),
            "selected_count": decision.get("operator_selected_count"),
            "stand_down_count": decision.get("operator_stand_down_count"),
            "model_response_normalization_count": decision.get("model_response_normalization_count"),
            "orders_placed": decision.get("orders_placed"),
            "broker_touched": decision.get("broker_touched"),
            "money_moved": decision.get("money_moved"),
        },
        "executions": execution_evidence,
        "bound_outcomes": outcome_evidence,
        "cycle_net_pnl": round(sum(float(row["net_pnl"]) for row in outcome_evidence), 2),
        "learning": {
            "status": learning.get("status"),
            "bound_trade_count": learning.get("bound_trade_count"),
            "history_record_count": learning.get("history_record_count"),
            "broker_order_touched": learning.get("broker_order_touched"),
            "money_moved": learning.get("money_moved"),
        },
        "account_after_cycle": {
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
    _require(report["cycle_net_pnl"] == -1.27, "combined cycle outcome changed")
    report["event_hash"] = _canonical_hash(report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture the natural v14 Operator position-management receipt without touching MT5.")
    parser.add_argument("--decision", type=Path, default=REPO_ROOT / "runtime" / "ai-operator-position-edge-latest.json")
    parser.add_argument("--cycle", type=Path, default=REPO_ROOT / "runtime" / "ai-hedge-management-cycle-state.json")
    parser.add_argument("--learning", type=Path, default=REPO_ROOT / "runtime" / "mt5-demo-learning-sync.json")
    parser.add_argument("--growth", type=Path, default=REPO_ROOT / "runtime" / "mt5-account-growth.json")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = {
        "operator_position_edge": args.decision,
        "management_cycle": args.cycle,
        "demo_learning": args.learning,
        "account_growth": args.growth,
    }
    payloads = {name: _load_json(path) for name, path in paths.items()}
    report = build_evidence(
        decision=payloads["operator_position_edge"],
        cycle_state=payloads["management_cycle"],
        learning=payloads["demo_learning"],
        growth=payloads["account_growth"],
        source_records={name: _source_record(paths[name], payloads[name]) for name in paths},
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "event_hash": report["event_hash"], "output": str(args.output.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
