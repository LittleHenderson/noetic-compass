"""Profit Sweep — automated profit distribution engine.

Follows the forex plan specification:
  - Only sweeps realized closed-trade profit
  - Blocks during drawdown recovery or open-risk overload
  - Auto-sweep transfers only after threshold, reserve, and minimum-balance checks
  - Supports: DRY_RUN (simulate), MANUAL (approve each), AUTO (automatic)
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from cas_forex.schemas.evidence import ForexEvidencePacket, PacketStatus
from cas_forex.schemas.live_lock import LiveLockReason
from cas_forex.schemas.sweep import (
    ProfitSweepPolicy,
    SweepTransaction,
    SweepMode,
    SweepStatus,
    TransferBoundary,
)
from cas_forex.time_utils import ensure_utc, utc_now


class ProfitSweeper:
    """Manages profit distribution according to sweep policy."""

    def __init__(self, policy: Optional[ProfitSweepPolicy] = None, live_lock_controller=None):
        self.policy = policy or ProfitSweepPolicy()
        self.live_lock_controller = live_lock_controller
        self._sweep_history: List[SweepTransaction] = []
        self._cumulative_profit: float = 0.0
        self._last_sweep_at: Optional[datetime] = None

    def check_sweep_eligibility(
        self,
        current_balance: float,
        current_equity: float,
        open_risk_lots: float,
    ) -> Tuple[bool, str]:
        """Check if a sweep is currently allowed.

        Returns (eligible, reason).
        """
        # Block during drawdown
        if self.policy.block_during_drawdown:
            drawdown_pct = (current_balance - current_equity) / current_balance * 100
            if drawdown_pct > 1.0:
                return False, f"Account in drawdown ({drawdown_pct:.1f}%)"

        # Block during open risk
        if self.policy.block_during_open_risk and open_risk_lots > 0.2:
            return False, f"Open risk {open_risk_lots:.2f} lots exceeds threshold"

        # Minimum balance check
        if current_balance < self.policy.min_trading_balance:
            return False, f"Balance {current_balance:.0f} below minimum {self.policy.min_trading_balance:.0f}"

        # Frequency check
        if self._last_sweep_at:
            minutes_since = (utc_now() - ensure_utc(self._last_sweep_at)).total_seconds() / 60
            if minutes_since < self.policy.max_sweep_frequency_minutes:
                return False, (
                    f"Last sweep was {minutes_since:.0f} min ago "
                    f"(min interval: {self.policy.max_sweep_frequency_minutes} min)"
                )

        return True, "Eligible"

    def execute_sweep(
        self,
        account_balance: float,
        realized_profit: float,
        open_risk_lots: float = 0.0,
        idempotency_key: Optional[str] = None,
        receipt_hash: Optional[str] = None,
    ) -> Optional[SweepTransaction]:
        """Execute a profit sweep if eligible and policy allows.

        Args:
            account_balance: Current account balance
            realized_profit: Realized profit available to sweep
            open_risk_lots: Currently open position risk in lots

        Returns SweepTransaction or None if blocked.
        """
        # DRY_RUN: simulate but don't execute
        if self.policy.mode == SweepMode.DRY_RUN:
            return self._build_sweep(
                account_balance, realized_profit, SweepStatus.PENDING,
                block_reason="DRY_RUN mode — sweep simulated only"
            )

        if self.live_lock_controller is not None and self.live_lock_controller.is_locked():
            return self._build_sweep(
                account_balance, realized_profit, SweepStatus.BLOCKED,
                block_reason="LIVE_LOCKED active; sweep blocked",
            )

        # Eligibility check
        eligible, reason = self.check_sweep_eligibility(
            account_balance, account_balance, open_risk_lots
        )
        if not eligible:
            return self._build_sweep(
                account_balance, realized_profit, SweepStatus.BLOCKED,
                block_reason=reason,
            )

        # Minimum profit threshold
        if realized_profit < self.policy.min_profit_threshold:
            return self._build_sweep(
                account_balance, realized_profit, SweepStatus.BLOCKED,
                block_reason=(
                    f"Profit {realized_profit:.0f} below threshold "
                    f"{self.policy.min_profit_threshold:.0f}"
                ),
            )

        # Calculate distribution
        reinvest = round(realized_profit * self.policy.reinvest_pct / 100, 2)
        savings = round(realized_profit * self.policy.savings_pct / 100, 2)
        tax_reserve = round(realized_profit * self.policy.tax_reserve_pct / 100, 2)
        removable_amount = savings + tax_reserve
        max_removable = round(account_balance * self.policy.max_sweep_percent / 100, 2)
        if removable_amount > max_removable:
            return self._build_sweep(
                account_balance, realized_profit, SweepStatus.BLOCKED,
                block_reason=(
                    f"Sweep amount {removable_amount:.0f} exceeds "
                    f"max removable {max_removable:.0f}"
                ),
            )

        # Post-sweep balance
        balance_after = account_balance - savings - tax_reserve
        if balance_after < self.policy.min_trading_balance:
            return self._build_sweep(
                account_balance, realized_profit, SweepStatus.BLOCKED,
                block_reason=(
                    f"Post-sweep balance {balance_after:.0f} below "
                    f"minimum {self.policy.min_trading_balance:.0f}"
                ),
            )

        # MANUAL mode: require approval
        if self.policy.mode == SweepMode.MANUAL:
            return self._build_sweep(
                account_balance, realized_profit, SweepStatus.PENDING,
                block_reason="MANUAL mode — awaiting approval",
            )

        # AUTO provider transfers are still NOT LICENSED unless the caller
        # supplies a provider boundary, receipt, idempotency, and allowlist proof.
        if self.policy.transfer_boundary != TransferBoundary.PROVIDER_API:
            return self._build_sweep(
                account_balance, realized_profit, SweepStatus.BLOCKED,
                block_reason="AUTO provider transfer is NOT LICENSED",
            )

        if not self.policy.destination_allowlisted:
            tx = self._build_sweep(
                account_balance, realized_profit, SweepStatus.FAILED,
                block_reason="Destination not allowlisted",
                live_lock_triggered=True,
            )
            self._lock_sweep_failure(tx)
            return tx

        if not idempotency_key or not receipt_hash:
            tx = self._build_sweep(
                account_balance, realized_profit, SweepStatus.FAILED,
                block_reason="Provider transfer missing idempotency key or receipt",
                live_lock_triggered=True,
            )
            self._lock_sweep_failure(tx)
            return tx

        if self.policy.require_human_confirmation:
            return self._build_sweep(
                account_balance, realized_profit, SweepStatus.BLOCKED,
                block_reason="Human confirmation required before provider transfer",
            )

        # Provider API path records the post-provider receipt only; the transfer
        # implementation itself must live behind a licensed provider integration.
        tx = SweepTransaction(
            sweep_id=f"sweep-{len(self._sweep_history):04d}",
            policy_ref=self.policy.policy_id,
            status=SweepStatus.EXECUTED,
            total_profit=round(realized_profit, 2),
            reinvest_amount=reinvest,
            savings_amount=savings,
            tax_reserve_amount=tax_reserve,
            balance_before=account_balance,
            balance_after=balance_after,
            transfer_boundary=self.policy.transfer_boundary,
            idempotency_key=idempotency_key,
            receipt_hash=receipt_hash,
            destination_allowlisted=self.policy.destination_allowlisted,
        )
        self._sweep_history.append(tx)
        self._cumulative_profit += realized_profit
        self._last_sweep_at = utc_now()
        self.policy.last_sweep_at = self._last_sweep_at
        return tx

    def _build_sweep(
        self,
        balance: float,
        profit: float,
        status: SweepStatus,
        block_reason: str = "",
        live_lock_triggered: bool = False,
    ) -> SweepTransaction:
        return SweepTransaction(
            sweep_id=f"sweep-{len(self._sweep_history):04d}",
            policy_ref=self.policy.policy_id,
            status=status,
            total_profit=round(profit, 2),
            balance_before=balance,
            balance_after=balance,
            block_reason=block_reason,
            transfer_boundary=self.policy.transfer_boundary,
            destination_allowlisted=self.policy.destination_allowlisted,
            live_lock_triggered=live_lock_triggered,
        )

    def _lock_sweep_failure(self, tx: SweepTransaction) -> None:
        if not tx.live_lock_triggered or self.live_lock_controller is None:
            return
        self.live_lock_controller.lock(
            [LiveLockReason.SAVINGS_TRANSFER_FAILURE],
            details=tx.model_dump(mode="json"),
        )

    @property
    def total_swept(self) -> float:
        return sum(t.savings_amount for t in self._sweep_history
                   if t.status == SweepStatus.EXECUTED)

    @property
    def history(self) -> List[SweepTransaction]:
        return list(self._sweep_history)

    def summary(self) -> dict:
        executed = [t for t in self._sweep_history if t.status == SweepStatus.EXECUTED]
        return {
            "mode": self.policy.mode.value,
            "total_sweeps": len(executed),
            "total_swept": round(self.total_swept, 2),
            "cumulative_profit": round(self._cumulative_profit, 2),
            "allocation": {
                "reinvest_pct": self.policy.reinvest_pct,
                "savings_pct": self.policy.savings_pct,
                "tax_reserve_pct": self.policy.tax_reserve_pct,
            },
        }
