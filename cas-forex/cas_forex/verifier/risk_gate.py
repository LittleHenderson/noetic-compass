"""Risk Gate – hard risk limits. Breach = SUPPRESS or LIVE_LOCKED."""
from cas_forex.schemas.decision import GateResult, GateStatus
from cas_forex.schemas.risk import RiskAssessment


class RiskGate:
    def evaluate(self, risk: RiskAssessment) -> GateResult:
        failures: list[str] = []
        locks: list[str] = []

        if risk.daily_drawdown_breached:
            locks.append(f"Daily DD {risk.daily_drawdown_pct:.2f}% >= {risk.max_daily_drawdown_pct}%")
        if risk.weekly_drawdown_breached:
            locks.append(f"Weekly DD {risk.weekly_drawdown_pct:.2f}% >= {risk.max_weekly_drawdown_pct}%")

        if risk.position_size_exceeded:
            failures.append(f"Pos size {risk.proposed_position_size_lots} > max {risk.max_position_size_lots}")
        if risk.risk_per_trade_exceeded:
            failures.append(f"Risk/trade {risk.risk_per_trade_pct:.1f}% > max {risk.max_risk_per_trade_pct:.1f}%")
        if risk.open_positions_exceeded:
            failures.append(f"Open pos {risk.open_positions_count} >= max {risk.max_open_positions}")
        if risk.exposure_exceeded:
            failures.append(f"Exposure {risk.total_exposure_lots + risk.proposed_position_size_lots:.2f} > max {risk.max_total_exposure_lots}")
        if risk.correlated_exposure_exceeded:
            failures.append(
                f"Correlated exposure {risk.correlated_exposure_lots + risk.proposed_position_size_lots:.2f} "
                f"> max {risk.max_correlated_exposure_lots:.2f}"
            )
        if risk.margin_level_pct < 200:
            failures.append(f"Margin level {risk.margin_level_pct:.0f}% < 200%")

        evidence = {
            "daily_drawdown_pct": risk.daily_drawdown_pct,
            "weekly_drawdown_pct": risk.weekly_drawdown_pct,
            "position_size_lots": risk.proposed_position_size_lots,
            "risk_per_trade_pct": risk.risk_per_trade_pct,
            "open_positions": risk.open_positions_count,
            "total_exposure_lots": risk.total_exposure_lots,
            "correlation_group": risk.correlation_group,
            "correlated_exposure_lots": risk.correlated_exposure_lots,
            "max_correlated_exposure_lots": risk.max_correlated_exposure_lots,
            "same_direction_correlation_count": risk.same_direction_correlation_count,
            "margin_level_pct": risk.margin_level_pct,
            "risk_score": risk.risk_score,
            "locks_triggered": len(locks) > 0,
            "lock_reasons": locks,
        }

        if locks:
            return GateResult(gate_name="risk", status=GateStatus.FAIL, confidence=1.0,
                              reason=f"LIVE_LOCKED: {'; '.join(locks)}",
                              evidence=evidence, claim_ceiling="OPEN")
        if failures:
            return GateResult(gate_name="risk", status=GateStatus.FAIL, confidence=1.0,
                              reason="; ".join(failures), evidence=evidence)
        return GateResult(gate_name="risk", status=GateStatus.PASS, confidence=0.95,
                          reason="Risk acceptable.", evidence=evidence)
