"""Live-order dry-run audit for CAS Forex.

This module rehearses a proposed live order against the same live-money checks
used at dispatch, but it never constructs or calls a broker bridge. It is the
owner-facing "would this be allowed if I pressed live?" report between paper
proof and a tiny controlled live pilot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from cas_forex import edge_authorization, execution_guard, live_pilot, runtime_gates
from cas_forex.account_ledger import stable_ledger_id
from cas_forex.compounding_governor import decide as decide_compound
from cas_forex.order_dispatch import TradeIntent, attach_pre_trade_estimate_to_intent
from cas_forex.pre_execution_risk_gate import decision_to_payload
from cas_forex.pre_trade_money import build_pre_trade_money_estimate
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AUDIT_PATH = REPO_ROOT / "runtime" / "live-order-dry-run-audit.jsonl"
DEFAULT_COMPOUND_ADD_AUDIT_PATH = REPO_ROOT / "runtime" / "compound-add-order-dry-run-audit.jsonl"

REPORT_KIND = "cas_forex_live_order_dry_run"
COMPOUND_ADD_REPORT_KIND = "cas_forex_compound_add_order_dry_run"
STATUS_PASS = "DRY_RUN_PASS"
STATUS_BLOCKED = "DRY_RUN_BLOCKED"

CLAIM_BOUNDARY = (
    "Live-order dry run evaluates a proposed order against live-trading, edge "
    "PASS, small-pilot, and risk gates without calling any broker bridge. It "
    "does not place orders, close positions, create broker ACCEPT, deposit, "
    "withdraw, move bank/card money, automate payouts, or authorize live trading."
)

COMPOUND_ADD_CLAIM_BOUNDARY = (
    "Compound-add dry run rehearses a pyramid add order for an already profitable "
    "broker-truth position. It checks parent-position context, CAS lacunarity/RPM/CJT "
    "context, a fresh add-edge PASS, small-pilot limits, and pre-execution risk "
    "without calling any broker bridge. It does not place add orders, close "
    "positions, create broker ACCEPT, create owner ACCEPT, authorize live trading, "
    "deposit, withdraw, move bank/card money, automate payouts, or register edge tokens."
)


@dataclass(frozen=True)
class LiveOrderDryRunRequest:
    order_id: str
    decision_ref: str
    symbol: str
    direction: str
    volume: float
    stop_loss: float
    take_profit: float
    price: float = 0.0
    expected_loss_usd: Optional[float] = None
    comment: str = "CAS_FOREX_DRY_RUN"
    strategy_id: Optional[str] = None

    def to_intent(self) -> TradeIntent:
        return TradeIntent(
            order_id=self.order_id,
            decision_ref=self.decision_ref,
            symbol=self.symbol,
            direction=self.direction,
            volume=float(self.volume),
            stop_loss=float(self.stop_loss),
            take_profit=float(self.take_profit),
            price=float(self.price),
            comment=self.comment,
            strategy_id=self.strategy_id,
            ai_action="LIVE_DRY_RUN",
            expected_loss_usd=self.expected_loss_usd,
        )


@dataclass(frozen=True)
class CompoundAddDryRunRequest:
    parent_order_id: str
    parent_decision_ref: str
    symbol: str
    direction: str
    add_order_id: str
    add_decision_ref: str
    add_volume: float
    price: float
    stop_loss: float
    take_profit: float
    position_entry: float
    position_stop_loss: float
    current_price: float
    current_units: int = 1
    max_units: int = 4
    broker_ticket: Optional[str] = None
    broker_grade_market_truth: bool = False
    cas_feature_map: Optional[Mapping[str, Any]] = None
    expected_loss_usd: Optional[float] = None
    comment: str = "CAS_FOREX_ADD_DRY_RUN"

    def to_live_order_request(self) -> LiveOrderDryRunRequest:
        return LiveOrderDryRunRequest(
            order_id=self.add_order_id,
            decision_ref=self.add_decision_ref,
            symbol=self.symbol,
            direction=self.direction,
            volume=float(self.add_volume),
            stop_loss=float(self.stop_loss),
            take_profit=float(self.take_profit),
            price=float(self.price),
            expected_loss_usd=self.expected_loss_usd,
            comment=self.comment,
            strategy_id="waste-compound",
        )


class LiveOrderDryRunAuditLog:
    def __init__(self, path: Path | str = DEFAULT_AUDIT_PATH) -> None:
        self.path = Path(path)

    def append(self, report: Mapping[str, Any]) -> dict[str, Any]:
        is_compound_add = report.get("report_kind") == COMPOUND_ADD_REPORT_KIND
        audit_prefix = "compound-add-order-dry-run" if is_compound_add else "live-order-dry-run"
        record = {
            "audit_id": stable_ledger_id(
                audit_prefix,
                str(report.get("order_id") or ""),
                str(report.get("decision_ref") or ""),
                utc_now().isoformat(),
            ),
            "action": "COMPOUND_ADD_ORDER_DRY_RUN" if is_compound_add else "LIVE_ORDER_DRY_RUN",
            "timestamp": utc_now().isoformat(),
            "status": report.get("status"),
            "order_id": report.get("order_id"),
            "decision_ref": report.get("decision_ref"),
            "payload": dict(report),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
        return record

    def latest(self) -> Optional[dict[str, Any]]:
        if not self.path.exists():
            return None
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return None
        try:
            return json.loads(lines[-1])
        except json.JSONDecodeError:
            return None


def build_live_order_dry_run(
    request: LiveOrderDryRunRequest,
    *,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
    bridge: Any = None,
    audit: Optional[LiveOrderDryRunAuditLog] = None,
) -> dict[str, Any]:
    """Evaluate a proposed live order without touching a broker bridge."""

    checks: list[dict[str, Any]] = []
    blocking_reasons: list[str] = []
    intent = request.to_intent()
    order = None
    proposed_intent = intent.proposed_intent()
    pre_trade_estimate = build_pre_trade_money_estimate(
        symbol=request.symbol,
        direction=request.direction,
        lots=request.volume,
        price=request.price,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        proposed_intent=proposed_intent,
        account_snapshot=account_snapshot,
        bridge=bridge,
        config=config,
    )
    proposed_intent = attach_pre_trade_estimate_to_intent(proposed_intent, pre_trade_estimate)
    estimate_ready = str(pre_trade_estimate.get("status") or "").upper() == "ESTIMATED"
    checks.append(
        _check(
            "pre_trade_money_estimate",
            estimate_ready,
            "Fresh stop-risk and margin estimate is available."
            if estimate_ready
            else "Complete stop-risk and margin evidence is unavailable.",
            pre_trade_estimate,
        )
    )
    if not estimate_ready:
        blocking_reasons.append("pre_trade_money_estimate: complete stop-risk and margin evidence is unavailable")

    try:
        order = intent.to_order()
        checks.append(_check("order_schema", True, "Order geometry is broker-schema valid.", order.model_dump(mode="json")))
    except Exception as exc:
        checks.append(_check("order_schema", False, f"Order rejected before live dry-run: {exc}", None))
        blocking_reasons.append(f"order_schema: {exc}")

    live_gate = runtime_gates.evaluate_live_trading(config, require_dry_run_review=False).to_dict()
    live_ok = bool(live_gate.get("authorized", False))
    checks.append(
        _check(
            "live_trading_gate",
            live_ok,
            "Live-trading gate is authorized." if live_ok else "Live-trading gate is not authorized.",
            live_gate,
        )
    )
    if not live_ok:
        blocking_reasons.extend(f"live_trading_gate: {item}" for item in live_gate.get("missing_requirements", []))

    if order is not None:
        try:
            edge_authorization.require(
                order,
                is_real=True,
                config=config,
                volume=request.volume,
                order_type=getattr(order, "order_type", None),
                price=getattr(order, "price", None),
                proposed_intent=proposed_intent,
            )
            checks.append(_check("edge_pass_token", True, "Fresh matching edge PASS is registered.", None))
        except Exception as exc:
            checks.append(_check("edge_pass_token", False, str(exc), None))
            blocking_reasons.append(f"edge_pass_token: {exc}")

        try:
            pilot = live_pilot.require_live_pilot_intent(proposed_intent, live_telemetry=live_telemetry)
            checks.append(_check("small_live_pilot", True, "Proposed order is inside the accepted live-pilot envelope.", pilot))
        except Exception as exc:
            checks.append(_check("small_live_pilot", False, str(exc), None))
            blocking_reasons.append(f"small_live_pilot: {exc}")

    risk_decision = execution_guard.evaluate(
        proposed_intent,
        config=config,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        equity_peak=equity_peak,
    )
    risk_payload = decision_to_payload(risk_decision)
    checks.append(
        _check(
            "pre_execution_risk_gate",
            bool(risk_decision.accepted),
            risk_decision.plain_english_reason,
            risk_payload,
        )
    )
    if not risk_decision.accepted:
        blocking_reasons.extend(f"pre_execution_risk_gate: {cap}" for cap in risk_decision.blocking_caps)

    status = STATUS_PASS if order is not None and not blocking_reasons else STATUS_BLOCKED
    report = {
        "report_kind": REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "would_reach_broker_if_executed": status == STATUS_PASS,
        "broker_touched": False,
        "order_id": request.order_id,
        "decision_ref": request.decision_ref,
        "proposed_intent": proposed_intent,
        "pre_trade_estimate": pre_trade_estimate,
        "order_request": order.model_dump(mode="json") if order is not None else None,
        "checks": checks,
        "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
        "next_action": (
            "All dry-run gates passed; owner can decide whether to proceed through the real dispatch confirmation path."
            if status == STATUS_PASS
            else "Resolve the listed blockers; this dry run never touched a broker bridge."
        ),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    if audit is not None:
        report["audit"] = audit.append(report)
    return report


def build_compound_add_order_dry_run(
    request: CompoundAddDryRunRequest,
    *,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
    bridge: Any = None,
    audit: Optional[LiveOrderDryRunAuditLog] = None,
) -> dict[str, Any]:
    """Evaluate a pyramid/add order without touching a broker bridge."""

    context_checks = _compound_context_checks(request)
    blocking_reasons = [
        f"{check['check_id']}: {check['detail']}"
        for check in context_checks
        if not bool(check.get("passed", False))
    ]

    base = build_live_order_dry_run(
        request.to_live_order_request(),
        config=config,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        equity_peak=equity_peak,
        bridge=bridge,
        audit=None,
    )
    base_checks = list(base.get("checks") or [])
    blocking_reasons.extend(str(item) for item in base.get("blocking_reasons", []) or [])

    compound_decision = _compound_add_decision(request)
    if compound_decision.action != "ADD":
        blocking_reasons.append(f"compound_decision: {compound_decision.reason}")

    status = (
        STATUS_PASS
        if base.get("status") == STATUS_PASS
        and compound_decision.action == "ADD"
        and not blocking_reasons
        else STATUS_BLOCKED
    )
    report = {
        "report_kind": COMPOUND_ADD_REPORT_KIND,
        "generated_at": utc_now().isoformat(),
        "status": status,
        "would_reach_broker_if_executed": status == STATUS_PASS,
        "broker_touched": False,
        "order_id": request.add_order_id,
        "decision_ref": request.add_decision_ref,
        "parent_order_id": request.parent_order_id,
        "parent_decision_ref": request.parent_decision_ref,
        "broker_ticket": request.broker_ticket,
        "proposed_intent": base.get("proposed_intent"),
        "order_request": base.get("order_request"),
        "compound_context": {
            "symbol": request.symbol,
            "direction": request.direction,
            "current_units": int(request.current_units),
            "max_units": int(request.max_units),
            "add_units": 1,
            "floating_r": _floating_r(
                direction=request.direction,
                entry=float(request.position_entry),
                stop_loss=float(request.position_stop_loss),
                current_price=float(request.current_price),
            ),
            "broker_grade_market_truth": bool(request.broker_grade_market_truth),
            "cas_feature_map": _safe_json(request.cas_feature_map or {}),
            "compound_decision": _safe_json(compound_decision),
        },
        "checks": context_checks + base_checks + [
            _check(
                "compound_governor_add_decision",
                compound_decision.action == "ADD",
                compound_decision.reason,
                _safe_json(compound_decision),
            )
        ],
        "base_live_order_dry_run": base,
        "blocking_reasons": list(dict.fromkeys(blocking_reasons)),
        "next_action": (
            "Compound-add dry run passed; owner can review this exact add fingerprint before any gated add dispatch."
            if status == STATUS_PASS
            else "Resolve the listed compound-add blockers; this dry run never touched a broker bridge."
        ),
        "claim_boundary": COMPOUND_ADD_CLAIM_BOUNDARY,
    }
    if audit is not None:
        report["audit"] = audit.append(report)
    return report


def _compound_context_checks(request: CompoundAddDryRunRequest) -> list[dict[str, Any]]:
    cas_map = dict(request.cas_feature_map or {})
    floating_r = _floating_r(
        direction=request.direction,
        entry=float(request.position_entry),
        stop_loss=float(request.position_stop_loss),
        current_price=float(request.current_price),
    )
    headroom = int(request.max_units) - int(request.current_units)
    return [
        _check(
            "parent_position_reference",
            bool(request.parent_order_id or request.broker_ticket),
            "Parent broker position/order reference is present."
            if bool(request.parent_order_id or request.broker_ticket)
            else "Missing parent broker position/order reference.",
            {
                "parent_order_id": request.parent_order_id,
                "broker_ticket": request.broker_ticket,
                "parent_decision_ref": request.parent_decision_ref,
            },
        ),
        _check(
            "broker_truth_position",
            bool(request.broker_grade_market_truth),
            "Parent position context is broker-grade market truth."
            if request.broker_grade_market_truth
            else "Broker-grade parent position truth is required before compounding.",
            {"broker_grade_market_truth": bool(request.broker_grade_market_truth)},
        ),
        _check(
            "profitable_position_r",
            floating_r is not None and floating_r > 0.0,
            f"Parent position is profitable at {floating_r:.2f}R."
            if floating_r is not None and floating_r > 0.0
            else (
                f"Parent position is not yet profitable ({floating_r:.2f}R)."
                if floating_r is not None
                else "Cannot compute parent position R."
            ),
            {"floating_r": floating_r},
        ),
        _check(
            "cas_feature_map_present",
            bool(cas_map),
            "CAS lacunarity/RPM/CJT feature map is present."
            if cas_map
            else "CAS lacunarity/RPM/CJT feature map is required before compounding.",
            _safe_json(cas_map),
        ),
        _check(
            "cas_rpm_route",
            str(cas_map.get("selected_rpm_action") or "").upper() == "ROUTE",
            "CAS RPM selected ROUTE for this profile."
            if str(cas_map.get("selected_rpm_action") or "").upper() == "ROUTE"
            else "CAS RPM did not select ROUTE for this profile.",
            {"selected_rpm_action": cas_map.get("selected_rpm_action")},
        ),
        _check(
            "cas_non_lacuna",
            not _bool_value(cas_map.get("selected_is_lacuna"), default=True),
            "Selected CAS cell is non-lacuna."
            if not _bool_value(cas_map.get("selected_is_lacuna"), default=True)
            else "Selected CAS cell is a lacuna.",
            {"selected_is_lacuna": cas_map.get("selected_is_lacuna")},
        ),
        _check(
            "cas_cjt_active",
            str(cas_map.get("selected_cjt_region") or "").lower() == "active",
            "Selected CJT region is active."
            if str(cas_map.get("selected_cjt_region") or "").lower() == "active"
            else "Selected CJT region is not active.",
            {"selected_cjt_region": cas_map.get("selected_cjt_region")},
        ),
        _check(
            "compound_unit_headroom",
            int(request.current_units) >= 0 and headroom >= 1,
            f"Compound headroom is available ({request.current_units}->{request.max_units})."
            if headroom >= 1
            else "No compound unit headroom is available.",
            {"current_units": request.current_units, "max_units": request.max_units, "headroom": headroom},
        ),
    ]


def _compound_add_decision(request: CompoundAddDryRunRequest) -> Any:
    cas_map = dict(request.cas_feature_map or {})
    floating_r = _floating_r(
        direction=request.direction,
        entry=float(request.position_entry),
        stop_loss=float(request.position_stop_loss),
        current_price=float(request.current_price),
    )
    return decide_compound(
        position={
            "symbol": request.symbol,
            "direction": request.direction,
            "parent_order_id": request.parent_order_id,
            "broker_ticket": request.broker_ticket,
        },
        cell_reliability=float(cas_map.get("cell_reliability") or 0.0),
        cascade_confidence=float(cas_map.get("cascade_confidence") or cas_map.get("cell_reliability") or 0.0),
        cjt_region=str(cas_map.get("selected_cjt_region") or "unknown"),
        floating_r=float(floating_r or 0.0),
        max_units=int(request.max_units),
        current_units=int(request.current_units),
        fresh_edge_pass=edge_authorization.is_required(request.add_decision_ref),
    )


def _check(check_id: str, passed: bool, detail: str, evidence: Any) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "passed": bool(passed),
        "status": "PASS" if passed else "BLOCKED",
        "detail": detail,
        "evidence": evidence,
    }


def request_from_mapping(payload: Mapping[str, Any]) -> LiveOrderDryRunRequest:
    """Build the dataclass request from an API/test mapping."""
    return LiveOrderDryRunRequest(
        order_id=str(payload.get("order_id") or ""),
        decision_ref=str(payload.get("decision_ref") or payload.get("order_id") or ""),
        symbol=str(payload.get("symbol") or "").upper(),
        direction=str(payload.get("direction") or "").upper(),
        volume=float(payload.get("volume", payload.get("lots", 0.0)) or 0.0),
        stop_loss=float(payload.get("stop_loss", payload.get("sl", 0.0)) or 0.0),
        take_profit=float(payload.get("take_profit", payload.get("tp", 0.0)) or 0.0),
        price=float(payload.get("price", 0.0) or 0.0),
        expected_loss_usd=(
            None
            if payload.get("expected_loss_usd") is None
            else float(payload.get("expected_loss_usd") or 0.0)
        ),
        comment=str(payload.get("comment") or "CAS_FOREX_DRY_RUN")[:27],
    )


def compound_add_request_from_mapping(payload: Mapping[str, Any]) -> CompoundAddDryRunRequest:
    """Build a compound-add dry-run request from an API/test mapping."""
    parent = payload.get("parent_position") if isinstance(payload.get("parent_position"), Mapping) else {}
    cas_map = payload.get("cas_feature_map")
    if cas_map is None and isinstance(parent, Mapping):
        cas_map = parent.get("cas_feature_map")
    return CompoundAddDryRunRequest(
        parent_order_id=str(payload.get("parent_order_id") or parent.get("order_id") or ""),
        parent_decision_ref=str(payload.get("parent_decision_ref") or parent.get("decision_ref") or ""),
        broker_ticket=(
            None
            if (payload.get("broker_ticket") or parent.get("broker_ticket")) is None
            else str(payload.get("broker_ticket") or parent.get("broker_ticket"))
        ),
        symbol=str(payload.get("symbol") or parent.get("symbol") or "").upper(),
        direction=str(payload.get("direction") or parent.get("direction") or "").upper(),
        add_order_id=str(payload.get("add_order_id") or payload.get("order_id") or ""),
        add_decision_ref=str(payload.get("add_decision_ref") or payload.get("decision_ref") or payload.get("add_order_id") or payload.get("order_id") or ""),
        add_volume=float(payload.get("add_volume", payload.get("volume", payload.get("lots", 0.0))) or 0.0),
        price=float(payload.get("price", payload.get("current_price", parent.get("current_price", 0.0))) or 0.0),
        stop_loss=float(payload.get("stop_loss", payload.get("sl", parent.get("stop_loss", 0.0))) or 0.0),
        take_profit=float(payload.get("take_profit", payload.get("tp", parent.get("take_profit", 0.0))) or 0.0),
        position_entry=float(payload.get("position_entry", parent.get("entry", parent.get("entry_price", 0.0))) or 0.0),
        position_stop_loss=float(payload.get("position_stop_loss", parent.get("stop_loss", 0.0)) or 0.0),
        current_price=float(payload.get("current_price", parent.get("current_price", payload.get("price", 0.0))) or 0.0),
        current_units=int(payload.get("current_units", parent.get("current_units", 1)) or 1),
        max_units=int(payload.get("max_units", parent.get("max_units", 4)) or 4),
        broker_grade_market_truth=bool(payload.get("broker_grade_market_truth", parent.get("broker_grade_market_truth", False))),
        cas_feature_map=dict(cas_map or {}) if isinstance(cas_map, Mapping) else {},
        expected_loss_usd=(
            None
            if payload.get("expected_loss_usd") is None
            else float(payload.get("expected_loss_usd") or 0.0)
        ),
        comment=str(payload.get("comment") or "CAS_FOREX_ADD_DRY_RUN")[:27],
    )


def _floating_r(*, direction: str, entry: float, stop_loss: float, current_price: float) -> Optional[float]:
    risk = abs(float(entry) - float(stop_loss))
    if risk <= 0:
        return None
    side = str(direction or "").upper()
    if side == "LONG":
        return (float(current_price) - float(entry)) / risk
    if side == "SHORT":
        return (float(entry) - float(current_price)) / risk
    return None


def _bool_value(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _safe_json(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "__dataclass_fields__"):
        return {key: _safe_json(getattr(value, key)) for key in value.__dataclass_fields__}
    if isinstance(value, Mapping):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_json(item) for item in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
