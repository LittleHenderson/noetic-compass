"""Capture the Operator floor-restoration-to-demo-fill evidence chain read-only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping
from urllib.error import URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cas_forex.time_utils import utc_now


OPERATOR_ACTIONS_PATH = REPO_ROOT / "runtime" / "ai-operator-actions.jsonl"
ORDER_ATTEMPTS_PATH = REPO_ROOT / "runtime" / "order-attempts-audit.jsonl"
STARVATION_REDTEAM_PATH = (
    REPO_ROOT / "runtime" / "redteam-entry-opportunity-starvation-latest.json"
)
DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "runtime" / "entry-opportunity-restoration-latest.json"
)
API_BASE = "http://127.0.0.1:8765/api/forex"


def _jsonl_rows(path: Path) -> Iterable[dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except (TypeError, ValueError):
                continue
            if isinstance(value, dict):
                yield value


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def _get_json(url: str) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=5) as response:  # noqa: S310 - fixed loopback URL
            value = json.loads(response.read().decode("utf-8"))
    except (OSError, TypeError, ValueError, URLError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def _latest_floor_adjustment() -> dict[str, Any]:
    matches = [
        row
        for row in _jsonl_rows(OPERATOR_ACTIONS_PATH)
        if str(row.get("response_contract_status") or "")
        == "EVIDENCE_BASED_DIRECTIONAL_FLOOR_ADJUSTMENT"
        and any(
            str(action.get("lever") or "") == "min_directional_confidence"
            for action in row.get("actions_applied") or []
            if isinstance(action, Mapping)
        )
    ]
    return matches[-1] if matches else {}


def _first_approved_fill_after(at: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for row in _jsonl_rows(ORDER_ATTEMPTS_PATH):
        payload = row.get("payload")
        if not isinstance(payload, Mapping):
            continue
        updated_at = str(payload.get("updated_at") or payload.get("created_at") or "")
        provenance = payload.get("execution_provenance")
        provenance = provenance if isinstance(provenance, Mapping) else {}
        operator = provenance.get("operator_decision")
        operator = operator if isinstance(operator, Mapping) else {}
        if (
            updated_at >= at
            and str(payload.get("result_status") or "") == "BROKER_EXECUTED"
            and str(operator.get("decision") or "") == "APPROVE"
        ):
            matches.append(dict(payload))
    return min(
        matches,
        key=lambda payload: str(
            payload.get("updated_at") or payload.get("created_at") or ""
        ),
        default={},
    )


def _matching_position(account: Mapping[str, Any], ticket: str) -> dict[str, Any] | None:
    for position in account.get("positions") or []:
        if isinstance(position, Mapping) and str(position.get("ticket") or "") == ticket:
            return dict(position)
    return None


def build_report() -> dict[str, Any]:
    adjustment = _latest_floor_adjustment()
    adjustment_contract = adjustment.get("entry_opportunity_response_contract")
    adjustment_contract = (
        dict(adjustment_contract)
        if isinstance(adjustment_contract, Mapping)
        else {}
    )
    action = next(
        (
            dict(item)
            for item in adjustment.get("actions_applied") or []
            if isinstance(item, Mapping)
            and str(item.get("lever") or "") == "min_directional_confidence"
        ),
        {},
    )
    adjustment_at = str(adjustment.get("at") or "")
    fill = _first_approved_fill_after(adjustment_at) if adjustment_at else {}
    provenance = fill.get("execution_provenance")
    provenance = dict(provenance) if isinstance(provenance, Mapping) else {}
    operator = provenance.get("operator_decision")
    operator = dict(operator) if isinstance(operator, Mapping) else {}
    order_shape = provenance.get("order_shape")
    order_shape = dict(order_shape) if isinstance(order_shape, Mapping) else {}
    outcome = fill.get("outcome")
    outcome = dict(outcome) if isinstance(outcome, Mapping) else {}
    result = fill.get("result")
    result = dict(result) if isinstance(result, Mapping) else {}
    trade_card = result.get("trade_explanation_card")
    trade_card = dict(trade_card) if isinstance(trade_card, Mapping) else {}
    pre_trade = trade_card.get("pre_trade_money")
    pre_trade = dict(pre_trade) if isinstance(pre_trade, Mapping) else {}
    dispatch_path = provenance.get("dispatch_path")
    dispatch_path = (
        dict(dispatch_path) if isinstance(dispatch_path, Mapping) else {}
    )
    broker_ticket = str(outcome.get("broker_ticket") or "")

    account = _get_json(f"{API_BASE}/mt5/account")
    dispatch = _get_json(f"{API_BASE}/dispatch-loop/status")
    current_position = _matching_position(account, broker_ticket) if broker_ticket else None
    redteam = _read_json(STARVATION_REDTEAM_PATH)

    proof_complete = bool(
        adjustment
        and action
        and fill
        and broker_ticket
        and str(fill.get("mode") or "") == "PAPER"
        and str(outcome.get("account_mode") or "") == "DEMO"
        and bool(outcome.get("is_demo_account"))
        and not bool(dispatch_path.get("live_money_broker"))
    )
    report: dict[str, Any] = {
        "report_kind": "cas_forex_entry_opportunity_restoration_evidence",
        "generated_at": utc_now().isoformat(),
        "status": (
            "PASS_OPERATOR_FLOOR_RESTORATION_TO_MT5_DEMO_FILL"
            if proof_complete
            else "INCOMPLETE_RESTORATION_EVIDENCE"
        ),
        "operator_floor_decision": {
            "at": adjustment_at or None,
            "provider": adjustment.get("provider"),
            "provider_label": adjustment.get("provider_label"),
            "response_contract_status": adjustment.get("response_contract_status"),
            "context_schema": (adjustment.get("context_delivery") or {}).get(
                "schema_version"
            ),
            "prior_floor": adjustment_contract.get("current_floor"),
            "strongest_observed_score": adjustment_contract.get("strongest_score"),
            "shadow_pass_score": adjustment_contract.get("shadow_pass_score"),
            "shadow_edge_status": adjustment_contract.get("shadow_edge_status"),
            "shadow_measured_win_probability": adjustment_contract.get(
                "shadow_measured_win_prob"
            ),
            "new_floor": action.get("new_value"),
            "reason": action.get("reason"),
            "source": action.get("source"),
            "deterministic_policy_used": bool(
                adjustment.get("paper_shadow_pass_policy_used")
            ),
        },
        "restored_candidate_and_operator_decision": {
            "decision_ref": fill.get("decision_ref"),
            "candidate_hash": operator.get("candidate_hash"),
            "decision": operator.get("decision"),
            "conviction": operator.get("conviction"),
            "reason": operator.get("reason"),
            "provider": operator.get("provider"),
            "provider_label": operator.get("provider_label"),
            "model_ref": operator.get("model_ref"),
            "operator_event_hash": operator.get("operator_event_hash"),
        },
        "mt5_demo_execution_receipt": {
            "attempt_id": fill.get("attempt_id"),
            "result_status": fill.get("result_status"),
            "mode": fill.get("mode"),
            "account_mode": outcome.get("account_mode"),
            "bridge": fill.get("bridge_name"),
            "broker_ticket": outcome.get("broker_ticket"),
            "server": outcome.get("server"),
            "terminal": outcome.get("terminal_name"),
            "symbol": fill.get("symbol"),
            "broker_symbol": outcome.get("broker_symbol"),
            "direction": fill.get("direction"),
            "lots": fill.get("volume"),
            "filled_price": outcome.get("filled_price"),
            "stop_loss": order_shape.get("stop_loss"),
            "take_profit": order_shape.get("take_profit"),
            "risk_at_stop_usd": pre_trade.get("risk_at_stop_usd"),
            "risk_at_stop_pct_equity": pre_trade.get("risk_at_stop_pct_equity"),
            "is_demo_account": outcome.get("is_demo_account"),
            "is_real_broker_terminal": outcome.get("is_real_broker"),
            "live_money": bool(
                dispatch_path.get("live_money_broker")
            ),
            "protective_orders_attached": bool(
                order_shape.get("stop_loss") and order_shape.get("take_profit")
            ),
            "updated_at": fill.get("updated_at"),
        },
        "current_runtime_readback": {
            "api_account_readback_available": bool(account),
            "dispatch_readback_available": bool(dispatch),
            "dispatch_running": dispatch.get("running"),
            "dispatch_lane": dispatch.get("execution_lane"),
            "dispatch_mode": dispatch.get("mode"),
            "matching_position_still_open": current_position is not None,
            "matching_position": current_position,
            "account_balance": (account.get("account") or {}).get("balance_usd"),
            "account_equity": (account.get("account") or {}).get("equity_usd"),
            "open_position_count": len(account.get("positions") or []),
        },
        "post_restoration_no_touch_redteam": {
            "status": redteam.get("status"),
            "current_directional_floor": redteam.get("current_directional_floor"),
            "current_floor_summary": redteam.get("current_floor_summary"),
            "controls_unchanged": redteam.get("controls_unchanged"),
            "authority_state_file_unchanged": redteam.get(
                "authority_state_file_unchanged"
            ),
            "broker_execution_touched": redteam.get("broker_execution_touched"),
            "order_send_called": redteam.get("order_send_called"),
            "money_moved": redteam.get("money_moved"),
            "event_hash": redteam.get("event_hash"),
        },
        "capture_side_effects": {
            "broker_touched": False,
            "order_sent": False,
            "dial_changed": False,
            "money_moved": False,
        },
        "claim_boundary": (
            "This capture only reads durable logs and loopback status endpoints. The "
            "recorded autonomous runtime, not this capture, adjusted the PAPER floor, "
            "formed a fresh candidate, obtained a new edge authorization and immediate "
            "Operator approval, passed risk and dispatch gates, and sent the MT5 demo "
            "order. One demo fill proves path continuity, not durable profitability, "
            "future returns, or external live-money readiness."
        ),
    }
    report["event_hash"] = _stable_hash(report)
    return report


def main() -> int:
    report = build_report()
    DEFAULT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = DEFAULT_OUTPUT_PATH.with_suffix(f"{DEFAULT_OUTPUT_PATH.suffix}.tmp")
    temp.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    temp.replace(DEFAULT_OUTPUT_PATH)
    print(
        json.dumps(
            {
                "status": report["status"],
                "broker_ticket": report["mt5_demo_execution_receipt"][
                    "broker_ticket"
                ],
                "live_money": report["mt5_demo_execution_receipt"]["live_money"],
                "capture_side_effects": report["capture_side_effects"],
                "event_hash": report["event_hash"],
                "output": str(DEFAULT_OUTPUT_PATH),
            },
            sort_keys=True,
        )
    )
    return 0 if report["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
