"""Wire the agent cycle's real signals into the gated order dispatch loop.

The agent cycle already produces real ``RouteIntent``s (``build_micro_scalp_intents``
+ ``build_hourly_intraday_intents``) and runs them through overseer approval
(``review_route_intents``). But the existing ``run_agent_workflow_cycle`` only
writes approved intents to an MT4 mailbox file or a separate MT5 demo verifier —
it never sends them through the live-trading + risk gate chain into a broker
bridge with a ledger record.

This module closes that gap WITHOUT touching the existing cycle: it reuses the
exact same signal builders and the exact same overseer, then routes the
*approved* intents through ``order_dispatch.dispatch_order`` — so the same gate
chain (live-trading gate if live, then pre-execution risk gate) and the same
paper broker (``SimulatedBrokerBridge`` by default) handle real agent signals
instead of hand-built ones.

Every route intent is accounted for in the report: approved intents become
gated dispatch results (executed / risk-blocked / live-gate-blocked), and
overseer-rejected intents are recorded as ``OVERSEER_REJECTED`` so the whole
path stays traceable. Paper-first: with no bridge supplied it uses
``broker.get_bridge()``, which is the paper broker until live trading is
owner-authorized. Going live is a config/flag swap; the loop is unchanged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from cas_forex.account_ledger import AccountLedgerEvent
from cas_forex.agent_state import OverseerDecision, RouteIntent
from cas_forex.order_dispatch import (
    STATUS_OVERSEER_REJECTED,
    DispatchReport,
    DispatchResult,
    build_dispatch_report,
    dispatch_order,
)
from cas_forex.schemas.order import BrokerOrderRequest
from cas_forex.time_utils import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "evidence_runs" / "agent_dispatch"

CLAIM_BOUNDARY = (
    "Agent dispatch pulls the agent cycle's real route intents, keeps only the "
    "overseer-approved ones, and runs them through the live-trading gate and "
    "pre-execution risk gate into the configured broker bridge. By default that "
    "bridge is the paper broker; a live broker is reached only after the "
    "owner-controlled live-trading gate is authorized. It does not pick or size "
    "trades and enables no real-money capability by itself."
)


@dataclass(frozen=True)
class AgentDispatchCycle:
    """A full agent dispatch cycle: signals, overseer decisions, gated dispatch."""

    report_kind: str
    generated_at: str
    route_intents: tuple[RouteIntent, ...]
    overseer_decisions: tuple[OverseerDecision, ...]
    dispatch_report: DispatchReport
    claim_boundary: str = CLAIM_BOUNDARY

    @property
    def approved_count(self) -> int:
        return sum(1 for d in self.overseer_decisions if d.approved)

    def ledger_events(self) -> tuple[AccountLedgerEvent, ...]:
        return tuple(
            r.ledger_event for r in self.dispatch_report.results if r.ledger_event is not None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": self.report_kind,
            "generated_at": self.generated_at,
            "route_intent_count": len(self.route_intents),
            "approved_intent_count": self.approved_count,
            "route_intents": [intent.to_dict() for intent in self.route_intents],
            "overseer_decisions": [
                {
                    "decision_id": d.decision_id,
                    "intent_id": d.intent_id,
                    "agent_id": d.agent_id,
                    "decision": d.decision,
                    "approved": d.approved,
                    "reasons": list(d.reasons),
                }
                for d in self.overseer_decisions
            ],
            "dispatch_report": self.dispatch_report.to_dict(),
            "claim_boundary": self.claim_boundary,
        }


def collect_route_intents(
    replay_results: Optional[Mapping[str, Any]] = None,
    replay_candidates: Optional[Mapping[str, Any]] = None,
) -> list[RouteIntent]:
    """Build the agent cycle's real route intents from the latest replay evidence.

    Mirrors the signal sources used by ``run_agent_workflow_cycle`` exactly, so
    the dispatch path consumes the same intents the rest of the desk does.
    """
    from cas_forex.forex_fury_candidates import load_latest_forex_fury_replay_candidate_report
    from cas_forex.forex_fury_replay_results import load_latest_forex_fury_replay_results_report
    from cas_forex.hourly_intraday_policy import build_hourly_intraday_intents
    from cas_forex.micro_scalp_policy import build_micro_scalp_intents

    if replay_results is None:
        replay_results = load_latest_forex_fury_replay_results_report()
    if replay_candidates is None:
        replay_candidates = load_latest_forex_fury_replay_candidate_report()

    return [
        *build_micro_scalp_intents(replay_results, replay_candidates),
        *build_hourly_intraday_intents(replay_candidates, replay_results),
    ]


def _overseer_rejected_result(intent: RouteIntent, decision: OverseerDecision) -> DispatchResult:
    direction = str(intent.direction or "").upper()
    volume = float(intent.lot_size or 0.0)
    return DispatchResult(
        order_id=str((intent.order_request or {}).get("order_id") or intent.intent_id),
        decision_ref=str((intent.order_request or {}).get("decision_ref") or intent.agent_id),
        symbol=intent.symbol,
        direction=direction,
        volume=volume,
        status=STATUS_OVERSEER_REJECTED,
        reason="; ".join(decision.reasons) or "overseer rejected route intent",
        intent_summary=f"{direction} {intent.symbol} {volume:.2f} lots",
        dispatched_to_bridge=False,
    )


def dispatch_route_intents(
    intents: Sequence[RouteIntent],
    decisions: Sequence[OverseerDecision],
    *,
    bridge: Any = None,
    config: Any = None,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
) -> DispatchReport:
    """Dispatch the overseer-approved route intents through the gated loop.

    Approved intents with an order payload are rebuilt into a
    ``BrokerOrderRequest`` and sent through ``dispatch_order`` (live + risk gate,
    then bridge). Overseer-rejected intents are recorded as ``OVERSEER_REJECTED``
    so every intent is represented in the report.
    """
    if bridge is None:
        # Honor the owner's platform choice + loosen settings.
        from cas_forex.broker_control import select_bridge

        bridge = select_bridge(config)

    # Pair intents with decisions POSITIONALLY (1:1, in order) — the same way the
    # canonical run_agent_workflow_cycle does (agent_state.py) and the order in
    # which review_route_intents emits them. This represents every intent exactly
    # once: no silent drop or misattribution even under duplicate intent_ids.
    decisions = list(decisions)
    results: list[DispatchResult] = []
    for idx, intent in enumerate(intents):
        decision = decisions[idx] if idx < len(decisions) else None
        if decision is None:
            # Fewer decisions than intents — never drop the intent silently.
            results.append(
                DispatchResult(
                    order_id=str((intent.order_request or {}).get("order_id") or intent.intent_id),
                    decision_ref=intent.agent_id,
                    symbol=intent.symbol,
                    direction=str(intent.direction or "").upper(),
                    volume=float(intent.lot_size or 0.0),
                    status=STATUS_OVERSEER_REJECTED,
                    reason="no overseer decision aligned to this intent",
                    intent_summary=f"{str(intent.direction or '').upper()} {intent.symbol}",
                    dispatched_to_bridge=False,
                )
            )
            continue
        if not decision.approved:
            results.append(_overseer_rejected_result(intent, decision))
            continue
        if not intent.order_request:
            # Approved but no order payload: nothing to dispatch. Record as a
            # pre-check rejection so it is not silently dropped.
            results.append(
                DispatchResult(
                    order_id=intent.intent_id,
                    decision_ref=intent.agent_id,
                    symbol=intent.symbol,
                    direction=str(intent.direction or "").upper(),
                    volume=float(intent.lot_size or 0.0),
                    status="REJECTED_PRECHECK",
                    reason="approved intent carries no BrokerOrderRequest payload",
                    intent_summary=f"{str(intent.direction or '').upper()} {intent.symbol}",
                    dispatched_to_bridge=False,
                )
            )
            continue

        try:
            order = BrokerOrderRequest(**dict(intent.order_request))
        except Exception as exc:
            results.append(
                DispatchResult(
                    order_id=str((intent.order_request or {}).get("order_id") or intent.intent_id),
                    decision_ref=str((intent.order_request or {}).get("decision_ref") or intent.agent_id),
                    symbol=intent.symbol,
                    direction=str(intent.direction or "").upper(),
                    volume=float(intent.lot_size or 0.0),
                    status="REJECTED_PRECHECK",
                    reason=f"order payload failed validation: {exc}",
                    intent_summary=f"{str(intent.direction or '').upper()} {intent.symbol}",
                    dispatched_to_bridge=False,
                )
            )
            continue

        results.append(
            dispatch_order(
                order,
                bridge,
                strategy_id=intent.strategy_setting,
                ai_action=intent.action,
                config=config,
                live_telemetry=live_telemetry,
                account_snapshot=account_snapshot,
                equity_peak=equity_peak,
            )
        )

    return build_dispatch_report(results, config=config)


def run_agent_dispatch_cycle(
    *,
    intents: Optional[Sequence[RouteIntent]] = None,
    replay_results: Optional[Mapping[str, Any]] = None,
    replay_candidates: Optional[Mapping[str, Any]] = None,
    bridge: Any = None,
    config: Any = None,
    event_log_path: Optional[Any] = None,
    enforce_receipt_gates: bool = True,
    live_telemetry: Optional[Mapping[str, Any]] = None,
    account_snapshot: Optional[Mapping[str, Any]] = None,
    equity_peak: Optional[float] = None,
) -> AgentDispatchCycle:
    """Run one agent dispatch cycle: real signals -> overseer -> gated dispatch.

    Pass ``intents`` to dispatch a specific set; otherwise the real signal
    builders produce them from the latest replay evidence. The overseer
    (``review_route_intents``) decides approval; only approved intents are
    dispatched through the gate chain into the (paper) broker.
    """
    from cas_forex.agent_overseer import review_route_intents

    if intents is None:
        intents = collect_route_intents(replay_results, replay_candidates)
    intents = list(intents)

    decisions = review_route_intents(
        intents,
        event_log_path=event_log_path,
        enforce_receipt_gates=enforce_receipt_gates,
    )

    report = dispatch_route_intents(
        intents,
        decisions,
        bridge=bridge,
        config=config,
        live_telemetry=live_telemetry,
        account_snapshot=account_snapshot,
        equity_peak=equity_peak,
    )

    return AgentDispatchCycle(
        report_kind="cas_forex_agent_dispatch_cycle",
        generated_at=utc_now().isoformat(),
        route_intents=tuple(intents),
        overseer_decisions=tuple(decisions),
        dispatch_report=report,
    )


def write_agent_dispatch_cycle_report(
    cycle: AgentDispatchCycle, *, output_dir: Path | str = DEFAULT_OUTPUT_DIR
) -> dict[str, Path]:
    """Persist an agent dispatch cycle as a JSON evidence artifact."""
    target_dir = Path(output_dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = utc_now().strftime("%Y%m%d%H%M%S")
    json_path = target_dir / f"agent-dispatch-cycle-{stamp}-report.json"
    json_path.write_text(
        json.dumps(cycle.to_dict(), indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return {"json": json_path}
