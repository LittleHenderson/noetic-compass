"""CAS Forex Auditor – compiler-validated, 5-gate pipeline producing CASDecision.

Gate order:
  0. CAS COMPILER  — validates trade as CAS expression (valid? admissible? descent_ok?)
  1. RISK           — hard locks (daily DD >2%, weekly >5%)
  2. MACRO          — blackout windows (NFP, FOMC, CPI)
  3. MARKET         — spread, session, ATR volatility
  4. EXECUTION      — duplicate, slippage, stop distance

Gate 0 is new: uses the real CAS compiler (api/notation/compiler.py, 5,814 lines)
to verify that the trade setup expressed in CAS notation is valid, admissible,
and respects domain descent (P→C→E→O). This replaces hand-written CAS checks.
"""

import uuid
from datetime import datetime
from typing import Optional

from cas_forex.compiler_bridge import (
    CASCompilerBridge,
    market_to_cas_relation,
    market_to_cas_state,
    get_bridge,
)
from cas_forex.schemas.decision import CASDecision, GateResult, GateStatus, Verdict
from cas_forex.schemas.forecast_harness import ForecastHarnessReport, ForecastHarnessVerdict
from cas_forex.schemas.forecast import ForecastProposal
from cas_forex.schemas.live_lock import LiveLockReason
from cas_forex.schemas.market import MarketSnapshot
from cas_forex.schemas.order import BrokerOrderRequest, OrderType
from cas_forex.schemas.risk import RiskAssessment
from cas_forex.verifier.live_lock import LiveLockController
from cas_forex.verifier.market_gate import MarketGate
from cas_forex.verifier.macro_gate import MacroGate
from cas_forex.verifier.risk_gate import RiskGate
from cas_forex.verifier.execution_gate import ExecutionGate
from cas_forex.time_utils import utc_now


class CASForexAuditor:
    """Orchestrates all CAS verifier gates including compiler validation."""

    def __init__(
        self,
        market_gate=None,
        macro_gate=None,
        risk_gate=None,
        execution_gate=None,
        compiler_bridge=None,
        live_lock_controller: Optional[LiveLockController] = None,
    ):
        self.market_gate = market_gate or MarketGate()
        self.macro_gate = macro_gate or MacroGate()
        self.risk_gate = risk_gate or RiskGate()
        self.execution_gate = execution_gate or ExecutionGate()
        self.compiler = compiler_bridge or get_bridge()
        self.live_lock_controller = live_lock_controller

    def evaluate(
        self,
        proposal: ForecastProposal,
        snapshot: MarketSnapshot,
        risk: RiskAssessment,
        current_price: Optional[float] = None,
        forecast_report: Optional[ForecastHarnessReport] = None,
    ) -> CASDecision:
        decision_id = str(uuid.uuid4())
        gate_results: list[GateResult] = []

        if self.live_lock_controller and self.live_lock_controller.is_locked():
            return CASDecision(
                decision_id=decision_id,
                proposal_ref=proposal.proposal_id,
                symbol=proposal.symbol,
                verdict=Verdict.SUPPRESS,
                overriding_gate="live_lock",
                summary="LIVE_LOCKED: persistent lock active",
            )

        if forecast_report is not None:
            forecast_status = (
                GateStatus.PASS
                if forecast_report.verdict == ForecastHarnessVerdict.PASS
                else GateStatus.FAIL
            )
            gate_results.append(GateResult(
                gate_name="forecast",
                status=forecast_status,
                confidence=0.95,
                reason="Forecast harness " + forecast_report.verdict.value,
                evidence=forecast_report.model_dump(mode="json"),
                claim_ceiling="OPEN",
            ))
            if forecast_report.verdict == ForecastHarnessVerdict.LIVE_LOCKED:
                if self.live_lock_controller:
                    self.live_lock_controller.lock(
                        [LiveLockReason.MODEL_DRIFT],
                        details={"forecast_report_id": forecast_report.report_id},
                    )
                return CASDecision(
                    decision_id=decision_id,
                    proposal_ref=proposal.proposal_id,
                    symbol=proposal.symbol,
                    verdict=Verdict.SUPPRESS,
                    gate_results=gate_results,
                    overriding_gate="forecast",
                    summary="LIVE_LOCKED: forecast model drift breach",
                )
            if forecast_report.verdict != ForecastHarnessVerdict.PASS:
                return CASDecision(
                    decision_id=decision_id,
                    proposal_ref=proposal.proposal_id,
                    symbol=proposal.symbol,
                    verdict=Verdict.SUPPRESS,
                    gate_results=gate_results,
                    overriding_gate="forecast",
                    summary=f"Forecast: {', '.join(forecast_report.reason_codes)}",
                )

        # ═══════════════════════════════════════
        # GATE 0: CAS COMPILER — the authority
        # ═══════════════════════════════════════
        cas_expr = market_to_cas_relation(
            snapshot,
            proposal.direction,
            proposal.entry_price,
            proposal.stop_loss,
            proposal.take_profit,
        )
        compiler_result = self.compiler.compile_expression(cas_expr)

        if not compiler_result.valid:
            gate_results.append(GateResult(
                gate_name="cas_compiler",
                status=GateStatus.FAIL,
                confidence=0.95,
                reason=f"CAS expression failed compilation: {compiler_result.error}",
                evidence={"cas_expression": cas_expr, "compiler_error": compiler_result.error},
                claim_ceiling="OPEN",
            ))
            return CASDecision(
                decision_id=decision_id,
                proposal_ref=proposal.proposal_id,
                symbol=proposal.symbol,
                verdict=Verdict.SUPPRESS,
                gate_results=gate_results,
                overriding_gate="cas_compiler",
                summary=f"Compile failed: {compiler_result.error}",
            )

        if compiler_result.admissible is False:
            gate_results.append(GateResult(
                gate_name="cas_compiler",
                status=GateStatus.FAIL,
                confidence=0.95,
                reason="CAS expression is valid but NOT admissible — operator composition violates guard conditions",
                evidence={"cas_expression": cas_expr, "admissible": False},
                claim_ceiling="OPEN",
            ))
            return CASDecision(
                decision_id=decision_id,
                proposal_ref=proposal.proposal_id,
                symbol=proposal.symbol,
                verdict=Verdict.SUPPRESS,
                gate_results=gate_results,
                overriding_gate="cas_compiler",
                summary="Not admissible: operator guard violation",
            )

        if compiler_result.domain_descent_ok is False:
            gate_results.append(GateResult(
                gate_name="cas_compiler",
                status=GateStatus.FAIL,
                confidence=0.95,
                reason="CAS expression violates domain descent (P→C→E→O)",
                evidence={"cas_expression": cas_expr, "domain_descent_ok": False},
                claim_ceiling="OPEN",
            ))
            return CASDecision(
                decision_id=decision_id,
                proposal_ref=proposal.proposal_id,
                symbol=proposal.symbol,
                verdict=Verdict.SUPPRESS,
                gate_results=gate_results,
                overriding_gate="cas_compiler",
                summary="Domain descent violation",
            )

        # Compiler PASSES — record the CAS expression as evidence
        gate_results.append(GateResult(
            gate_name="cas_compiler",
            status=GateStatus.PASS,
            confidence=0.95,
            reason=f"CAS expression compiles: {cas_expr}",
            evidence={
                "cas_expression": cas_expr,
                "cas_state": market_to_cas_state(snapshot, proposal.direction),
                "admissible": compiler_result.admissible,
                "domain_descent_ok": compiler_result.domain_descent_ok,
                "relation": compiler_result.relation,
            },
        ))

        # Gate 1: Risk (hard locks)
        risk_result = self.risk_gate.evaluate(risk)
        gate_results.append(risk_result)
        if risk_result.status == GateStatus.FAIL:
            if risk_result.evidence.get("locks_triggered") and self.live_lock_controller:
                reasons = []
                if risk.daily_drawdown_breached:
                    reasons.append(LiveLockReason.DAILY_DRAWDOWN)
                if risk.weekly_drawdown_breached:
                    reasons.append(LiveLockReason.WEEKLY_DRAWDOWN)
                self.live_lock_controller.lock(
                    reasons or [LiveLockReason.MANUAL_OPERATOR_LOCK],
                    details=risk_result.evidence,
                )
                summary = f"LIVE_LOCKED: {risk_result.reason}"
            else:
                summary = f"Risk: {risk_result.reason}"
            return CASDecision(
                decision_id=decision_id, proposal_ref=proposal.proposal_id,
                symbol=proposal.symbol, verdict=Verdict.SUPPRESS,
                gate_results=gate_results, overriding_gate="risk",
                summary=summary,
            )

        # Gate 2: Macro
        macro_result = self.macro_gate.evaluate(snapshot.timestamp)
        gate_results.append(macro_result)
        if macro_result.status == GateStatus.FAIL:
            if "LIVE_LOCKED" in macro_result.reason and self.live_lock_controller:
                self.live_lock_controller.lock(
                    [LiveLockReason.MACRO_SHOCK],
                    details=macro_result.evidence,
                )
            return CASDecision(
                decision_id=decision_id, proposal_ref=proposal.proposal_id,
                symbol=proposal.symbol, verdict=Verdict.SUPPRESS,
                gate_results=gate_results, overriding_gate="macro",
                summary=f"Macro: {macro_result.reason}",
            )

        # Gate 3: Market
        market_result = self.market_gate.evaluate(
            snapshot, proposal.direction, proposal.entry_price,
        )
        gate_results.append(market_result)
        if market_result.status == GateStatus.FAIL:
            return CASDecision(
                decision_id=decision_id, proposal_ref=proposal.proposal_id,
                symbol=proposal.symbol, verdict=Verdict.SUPPRESS,
                gate_results=gate_results, overriding_gate="market",
                summary=f"Market: {market_result.reason}",
            )

        # Gate 4: Execution
        temp_order = self.build_order(proposal, risk, decision_ref=decision_id)
        price = current_price if current_price is not None else snapshot.mid
        exec_result = self.execution_gate.evaluate(
            temp_order, current_price=price, market_open=snapshot.is_market_open,
        )
        gate_results.append(exec_result)
        if exec_result.status == GateStatus.FAIL:
            return CASDecision(
                decision_id=decision_id, proposal_ref=proposal.proposal_id,
                symbol=proposal.symbol, verdict=Verdict.SUPPRESS,
                gate_results=gate_results, overriding_gate="execution",
                summary=f"Execution: {exec_result.reason}",
            )

        # Undetermined gates?
        undetermined = [g for g in gate_results if g.status == GateStatus.UNDETERMINED]
        if undetermined:
            return CASDecision(
                decision_id=decision_id, proposal_ref=proposal.proposal_id,
                symbol=proposal.symbol, verdict=Verdict.FLAG_FOR_HUMAN_REVIEW,
                gate_results=gate_results,
                summary=f"Uncertain: {', '.join(g.gate_name for g in undetermined)}",
            )

        # ALL 5 GATES PASSED
        return CASDecision(
            decision_id=decision_id, proposal_ref=proposal.proposal_id,
            symbol=proposal.symbol, verdict=Verdict.ACCEPT,
            gate_results=gate_results,
            summary=(
                f"ACCEPT: {proposal.symbol} {proposal.direction.value} "
                f"@ {proposal.entry_price} | CAS: {cas_expr}"
            ),
        )

    def build_order(
        self, proposal: ForecastProposal, risk: RiskAssessment,
        decision_ref: str = "",
    ) -> BrokerOrderRequest:
        return BrokerOrderRequest(
            order_id=str(uuid.uuid4()),
            decision_ref=decision_ref,
            symbol=proposal.symbol,
            order_type=OrderType.MARKET,
            direction=proposal.direction,
            volume=min(risk.proposed_position_size_lots, risk.max_position_size_lots),
            stop_loss=proposal.stop_loss,
            take_profit=proposal.take_profit,
            comment=f"CAS_{proposal.symbol.replace('/', '')}",
            magic_number=20260601,
            created_at=utc_now(),
        )
