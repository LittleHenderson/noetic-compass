"""Capture a no-touch proof of current Operator sizing and compound-slot policy."""

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
from cas_forex.broker.mt5_bridge import MT5Bridge
from cas_forex.config import config
from cas_forex.operator_sizing import build_operator_sizing_plan
from cas_forex.time_utils import utc_now


DEFAULT_OUTPUT = REPO_ROOT / "runtime" / "redteam-operator-sizing-compound-slot-latest.json"


class _ReadOnlyPositionOverlay:
    """Expose synthetic policy-probe positions while delegating broker reads."""

    def __init__(
        self,
        bridge: MT5Bridge,
        positions: list[Mapping[str, Any]] | None = None,
    ) -> None:
        self._bridge = bridge
        self._mt5 = bridge._mt5
        self._positions = [dict(row) for row in positions or []]

    def get_account_info(self) -> dict[str, Any]:
        return dict(self._bridge.get_account_info() or {})

    def get_open_positions(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._positions]

    def get_open_positions_all(self) -> list[dict[str, Any]]:
        return self.get_open_positions()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_complete_natural_geometry() -> tuple[dict[str, Any], dict[str, Any]]:
    learning = _read_json(REPO_ROOT / "runtime" / "mt5-demo-learning-sync.json")
    attempts = _read_json(REPO_ROOT / "runtime" / "order-attempts.json").get("attempts") or {}
    candidates: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for row in learning.get("bound_outcomes") or []:
        if not isinstance(row, Mapping) or not row.get("admission_risk_evidence_complete"):
            continue
        attempt = attempts.get(str(row.get("attempt_id") or ""))
        if not isinstance(attempt, Mapping):
            continue
        provenance = attempt.get("execution_provenance") or {}
        shape = provenance.get("order_shape") or {}
        if not all(shape.get(key) is not None for key in ("symbol", "direction", "stop_loss", "take_profit")):
            continue
        entry = (provenance.get("pre_trade_estimate") or {}).get("entry_price")
        if entry is None:
            entry = (row.get("admission_risk_contract") or {}).get("entry_price")
        if entry is None:
            continue
        candidates.append((str(row.get("close_time") or ""), dict(row), dict(attempt)))
    if not candidates:
        raise RuntimeError("No complete natural MT5 demo geometry is available for the sizing probe.")
    _, outcome, attempt = max(candidates, key=lambda item: item[0])
    return outcome, attempt


def _latest_executed_larger_operator_entry() -> dict[str, Any]:
    attempts = _read_json(REPO_ROOT / "runtime" / "order-attempts.json").get("attempts") or {}
    candidates: list[tuple[str, dict[str, Any], str]] = []
    for value in attempts.values():
        if not isinstance(value, Mapping):
            continue
        attempt = dict(value)
        provenance = dict(attempt.get("execution_provenance") or {})
        dispatch_path = dict(provenance.get("dispatch_path") or {})
        operator = dict(provenance.get("operator_decision") or {})
        sizing = dict(provenance.get("sizing") or {})
        shape = dict(provenance.get("order_shape") or {})
        config_snapshot = dict(provenance.get("config_snapshot") or {})
        broker_min_lot = float(config_snapshot.get("broker_min_lot") or 0.01)
        selected_lots = float(sizing.get("selected_lots") or shape.get("volume") or 0.0)
        if attempt.get("result_status") != "BROKER_EXECUTED":
            continue
        if operator.get("decision") != "APPROVE":
            continue
        if selected_lots <= broker_min_lot:
            continue
        if dispatch_path.get("account_mode") != "DEMO" or dispatch_path.get("live_money_broker") is True:
            continue
        if dispatch_path.get("order_executed") is not True:
            continue
        candidates.append(
            (
                str(attempt.get("updated_at") or attempt.get("created_at") or ""),
                attempt,
                str(operator.get("growth_evidence_state") or ""),
            )
        )
    if not candidates:
        return {}

    positive_sample_ready = [
        item for item in candidates if item[2] == "EXACT_GROUP_POSITIVE_SAMPLE_READY"
    ]
    _, attempt, _ = max(positive_sample_ready or candidates, key=lambda item: item[0])
    provenance = dict(attempt.get("execution_provenance") or {})
    dispatch_path = dict(provenance.get("dispatch_path") or {})
    operator = dict(provenance.get("operator_decision") or {})
    sizing = dict(provenance.get("sizing") or {})
    shape = dict(provenance.get("order_shape") or {})
    ledger_event = dict(attempt.get("ledger_event") or {})
    offered = list(sizing.get("offered_options") or [])
    broker_ticket = str(ledger_event.get("broker_ticket") or "")
    learning = _read_json(REPO_ROOT / "runtime" / "mt5-demo-learning-sync.json")
    bound_outcome = next(
        (
            dict(row)
            for row in learning.get("bound_outcomes") or []
            if isinstance(row, Mapping) and str(row.get("broker_ticket") or "") == broker_ticket
        ),
        {},
    )
    return {
        "attempt_id": attempt.get("attempt_id"),
        "broker_ticket": ledger_event.get("broker_ticket"),
        "created_at": attempt.get("created_at"),
        "symbol": shape.get("symbol"),
        "direction": shape.get("direction"),
        "selected_lots": sizing.get("selected_lots"),
        "sizing_label": sizing.get("label"),
        "sizing_ref": sizing.get("sizing_ref"),
        "sizing_plan_hash": sizing.get("sizing_plan_hash"),
        "max_executable_lots": sizing.get("max_executable_lots"),
        "limiting_source": sizing.get("limiting_source"),
        "offered_option_count": sizing.get("offered_option_count", len(offered)),
        "offered_lots": [row.get("lots") for row in offered if isinstance(row, Mapping)],
        "growth_evidence_state": operator.get("growth_evidence_state"),
        "operator_reason": operator.get("reason"),
        "operator_event_hash": operator.get("operator_event_hash"),
        "operator_provider": operator.get("provider"),
        "operator_model_ref": operator.get("model_ref"),
        "operator_prompt_version": operator.get("prompt_version"),
        "execution_status": attempt.get("result_status"),
        "realized_net_pnl": bound_outcome.get("net_pnl"),
        "realized_after_cost_r_multiple": bound_outcome.get("realized_after_cost_r_multiple"),
        "realized_outcome_bound": bool(bound_outcome),
        "external_broker_terminal": dispatch_path.get("external_broker_terminal"),
        "account_mode": dispatch_path.get("account_mode"),
        "live_money_broker": dispatch_path.get("live_money_broker"),
    }


def _compact_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": plan.get("status"),
        "purpose": plan.get("purpose"),
        "plan_version": plan.get("plan_version"),
        "plan_hash": plan.get("plan_hash"),
        "broker_min_lot": plan.get("broker_min_lot"),
        "broker_lot_step": plan.get("broker_lot_step"),
        "max_executable_lots": plan.get("max_executable_lots"),
        "limiting_source": plan.get("limiting_source"),
        "compound_slot_allowance": plan.get("compound_slot_allowance"),
        "effective_max_positions_per_symbol": plan.get("effective_max_positions_per_symbol"),
        "cap_snapshot": plan.get("cap_snapshot"),
        "portfolio_snapshot": plan.get("portfolio_snapshot"),
        "options": plan.get("options") or [],
        "blockers": plan.get("blockers") or [],
    }


def _position_summary(value: Any) -> dict[str, Any]:
    row = dict(value) if isinstance(value, Mapping) else {}
    return {
        "ticket": row.get("ticket") or row.get("broker_ticket"),
        "symbol": row.get("symbol"),
        "side": row.get("side") or row.get("direction") or row.get("type"),
        "volume": row.get("volume") or row.get("lots") or row.get("lot_size"),
        "open_price": row.get("open_price") or row.get("price_open"),
        "current_price": row.get("current_price") or row.get("price_current"),
        "stop_loss": row.get("stop_loss") or row.get("sl"),
        "take_profit": row.get("take_profit") or row.get("tp"),
        "profit": row.get("profit") or row.get("floating_pnl_usd"),
        "swap": row.get("swap") or row.get("swap_usd"),
    }


def build_report() -> dict[str, Any]:
    outcome, attempt = _latest_complete_natural_geometry()
    natural_larger_entry = _latest_executed_larger_operator_entry()
    provenance = dict(attempt.get("execution_provenance") or {})
    shape = dict(provenance.get("order_shape") or {})
    estimate = dict(provenance.get("pre_trade_estimate") or {})
    sizing = dict(provenance.get("sizing") or {})
    entry = estimate.get("entry_price")
    if entry is None:
        entry = (outcome.get("admission_risk_contract") or {}).get("entry_price")

    bridge = MT5Bridge(runtime_config=config)
    connected = bridge.connect()
    if not connected or not bridge.is_demo_account():
        raise RuntimeError("The no-touch sizing probe requires the connected MT5 demo account.")
    account = dict(bridge.get_account_info() or {})
    current_positions = list(bridge.get_open_positions() or [])
    authority = get_authority()
    controls = dict(authority.control.snapshot().get("values") or {})
    common = {
        "symbol": shape.get("symbol"),
        "direction": shape.get("direction"),
        "entry_price": entry,
        "stop_loss": shape.get("stop_loss"),
        "take_profit": shape.get("take_profit"),
        "seed_lots": 0.01,
        "config": config,
    }
    proposed = {
        "symbol": shape.get("symbol"),
        "direction": shape.get("direction"),
        "entry_price": entry,
        "stop_loss": shape.get("stop_loss"),
        "take_profit": shape.get("take_profit"),
        "lots": 0.01,
        "strategy_id": "redteam-read-only-sizing-proof",
    }
    current_entry = build_operator_sizing_plan(
        **common,
        bridge=bridge,
        proposed_intent=proposed,
        purpose="ENTRY",
    )
    empty_capacity_overlay = _ReadOnlyPositionOverlay(bridge)
    empty_capacity_entry = build_operator_sizing_plan(
        **common,
        bridge=empty_capacity_overlay,
        proposed_intent=proposed,
        purpose="ENTRY",
    )

    parent = {
        "ticket": "READ_ONLY_POLICY_PROBE_PARENT",
        "symbol": shape.get("symbol"),
        "side": shape.get("direction"),
        "volume": 0.01,
        "lot_size": 0.01,
    }
    overlay = _ReadOnlyPositionOverlay(bridge, [parent])
    ordinary_at_full_symbol_cap = build_operator_sizing_plan(
        **common,
        bridge=overlay,
        proposed_intent=proposed,
        purpose="ENTRY",
    )
    compound_allowance = max(0, int(controls.get("max_compound_units") or 0))
    scale_proposed = {
        **proposed,
        "is_compound_add": True,
        "parent_broker_ticket": parent["ticket"],
    }
    exact_scale_in = build_operator_sizing_plan(
        **common,
        bridge=overlay,
        proposed_intent=scale_proposed,
        purpose="SCALE_IN",
        parent_position=parent,
        compound_slot_allowance=compound_allowance,
    )

    entry_options = empty_capacity_entry.get("options") or []
    ordinary_blocked = not ordinary_at_full_symbol_cap.get("options") and any(
        "per-symbol position cap" in str(reason)
        for reason in ordinary_at_full_symbol_cap.get("blockers") or []
    )
    scale_slot_ready = bool(exact_scale_in.get("options")) and (
        exact_scale_in.get("effective_max_positions_per_symbol")
        == int(controls.get("max_positions_per_symbol") or 0) + compound_allowance
    )
    larger_choice_present = any(float(row.get("lots") or 0) > 0.01 for row in entry_options)
    natural_larger_entry_present = float(natural_larger_entry.get("selected_lots") or 0.0) > 0.01
    passed = ordinary_blocked and scale_slot_ready and larger_choice_present and natural_larger_entry_present
    report: dict[str, Any] = {
        "report_kind": "cas_forex_redteam_operator_sizing_compound_slot",
        "generated_at": utc_now().isoformat(),
        "status": "PASS_NO_TOUCH_OPERATOR_SIZING_AND_COMPOUND_SLOT" if passed else "FAIL_POLICY_PROBE",
        "source_natural_trade": {
            "attempt_id": outcome.get("attempt_id"),
            "broker_ticket": outcome.get("broker_ticket"),
            "symbol": outcome.get("symbol"),
            "direction": outcome.get("direction"),
            "entry_price": entry,
            "stop_loss": shape.get("stop_loss"),
            "take_profit": shape.get("take_profit"),
            "selected_lots": sizing.get("selected_lots"),
            "prior_max_executable_lots": sizing.get("max_executable_lots"),
            "prior_limiting_source": sizing.get("limiting_source"),
            "realized_net_pnl": outcome.get("net_pnl"),
            "realized_after_cost_r_multiple": outcome.get("realized_after_cost_r_multiple"),
        },
        "natural_larger_operator_entry": natural_larger_entry,
        "current_demo_account_read": {
            "connected": connected,
            "demo_confirmed": bridge.is_demo_account(),
            "balance": account.get("balance"),
            "equity": account.get("equity"),
            "margin": account.get("margin"),
            "free_margin": account.get("margin_free"),
            "open_position_count": len(current_positions),
            "positions": [_position_summary(row) for row in current_positions],
        },
        "current_operator_controls": {
            "max_risk_pct_per_trade": controls.get("max_risk_pct_per_trade"),
            "max_positions_per_symbol": controls.get("max_positions_per_symbol"),
            "max_compound_units": compound_allowance,
            "max_total_exposure_lots": controls.get("max_total_exposure_lots"),
        },
        "current_entry_sizing": _compact_plan(current_entry),
        "empty_symbol_capacity_sizing_policy_probe": {
            **_compact_plan(empty_capacity_entry),
            "portfolio_is_synthetic_empty_overlay": True,
            "probe_purpose": "Show the exact lot menu for the natural geometry when ordinary symbol capacity is available.",
        },
        "ordinary_entry_at_full_symbol_cap": _compact_plan(ordinary_at_full_symbol_cap),
        "authorized_scale_in_policy_probe": {
            **_compact_plan(exact_scale_in),
            "probe_parent_is_synthetic": True,
            "probe_purpose": "Verify cap composition only; this is not a trade candidate or authorization.",
        },
        "assertions": {
            "larger_than_broker_minimum_choice_present": larger_choice_present,
            "natural_operator_entry_above_broker_minimum_executed": natural_larger_entry_present,
            "natural_open_position_above_broker_minimum_observed": any(
                float(_position_summary(row).get("volume") or 0) > 0.01 for row in current_positions
            ),
            "ordinary_duplicate_entry_blocked_at_base_symbol_cap": ordinary_blocked,
            "dedicated_compound_slot_keeps_exact_scale_in_lane_available": scale_slot_ready,
            "unverified_compound_flag_cannot_reserve_slot": "covered by execution-guard and risk-gate tests",
        },
        "broker_touched": False,
        "orders_placed": False,
        "money_moved": False,
        "claim_boundary": (
            "This read-only probe revalues one naturally executed MT5 demo geometry under current controls and "
            "uses a synthetic position overlay only to test cap composition. It does not select a trade, authorize "
            "a scale-in, call order dispatch, touch the broker, move money, prove durable edge, or predict profit."
        ),
    }
    report["event_hash"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if str(report.get("status", "")).startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
