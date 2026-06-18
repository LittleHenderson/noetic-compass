"""ProfitSweepPolicy and SweepTransaction schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from cas_forex.time_utils import utc_now


class SweepMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    MANUAL = "MANUAL"
    AUTO = "AUTO"


class SweepStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class TransferBoundary(str, Enum):
    INTERNAL_LEDGER_ONLY = "INTERNAL_LEDGER_ONLY"
    MANUAL_BANK_TRANSFER = "MANUAL_BANK_TRANSFER"
    PROVIDER_API = "PROVIDER_API"


class ProfitSweepPolicy(BaseModel):
    """Configuration for automated profit sweeping.

    Controls when and how realized profits are transferred from the trading
    account to savings/reinvestment.
    """

    policy_id: str = Field(
        default="default",
        description="Policy identifier.",
    )
    mode: SweepMode = Field(
        default=SweepMode.DRY_RUN,
        description="DRY_RUN (simulate only), MANUAL (approve each), AUTO (automatic).",
    )
    # Thresholds
    min_profit_threshold: float = Field(
        default=50.0,
        description="Minimum cumulative realized profit before sweep is allowed.",
        ge=0,
    )
    min_trading_balance: float = Field(
        default=500.0,
        description="Minimum balance to retain in trading account after sweep.",
        gt=0,
    )
    # Allocation (must sum to 100)
    reinvest_pct: float = Field(
        default=50.0,
        description="Percentage of profit to reinvest in trading account.",
        ge=0.0,
        le=100.0,
    )
    savings_pct: float = Field(
        default=40.0,
        description="Percentage of profit to transfer to savings.",
        ge=0.0,
        le=100.0,
    )
    tax_reserve_pct: float = Field(
        default=10.0,
        description="Percentage of profit to reserve for taxes.",
        ge=0.0,
        le=100.0,
    )
    # Safety
    block_during_drawdown: bool = Field(
        default=True,
        description="Block sweeps when account is in drawdown.",
    )
    block_during_open_risk: bool = Field(
        default=True,
        description="Block sweeps when open risk exceeds threshold.",
    )
    max_sweep_frequency_minutes: int = Field(
        default=1440,
        description="Minimum minutes between sweeps (default: 24 hours).",
        ge=60,
    )
    last_sweep_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the last executed sweep.",
    )
    transfer_boundary: TransferBoundary = Field(
        default=TransferBoundary.INTERNAL_LEDGER_ONLY,
        description="How far sweep execution may go outside the local ledger.",
    )
    destination_allowlisted: bool = Field(
        default=False,
        description="Whether the destination account has been explicitly allowlisted.",
    )
    require_human_confirmation: bool = Field(
        default=True,
        description="Whether a human must confirm provider/API transfer execution.",
    )
    max_sweep_percent: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="Maximum percentage of current balance removable in one sweep.",
    )
    created_at: datetime = Field(
        default_factory=utc_now,
    )

    @property
    def allocation_sum(self) -> float:
        return self.reinvest_pct + self.savings_pct + self.tax_reserve_pct


class SweepTransaction(BaseModel):
    """Record of a single profit sweep execution."""

    sweep_id: str = Field(
        ...,
        description="Unique sweep transaction identifier.",
    )
    policy_ref: str = Field(
        default="default",
        description="Reference to the ProfitSweepPolicy used.",
    )
    status: SweepStatus = Field(
        default=SweepStatus.PENDING,
        description="Execution status.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp of this sweep.",
    )
    # Amounts
    total_profit: float = Field(
        ...,
        description="Total realized profit available for sweep.",
        ge=0,
    )
    reinvest_amount: float = Field(
        default=0.0,
        description="Amount retained in trading account.",
        ge=0,
    )
    savings_amount: float = Field(
        default=0.0,
        description="Amount transferred to savings.",
        ge=0,
    )
    tax_reserve_amount: float = Field(
        default=0.0,
        description="Amount reserved for taxes.",
        ge=0,
    )
    # Account state
    balance_before: float = Field(
        ...,
        description="Trading account balance before sweep.",
    )
    balance_after: float = Field(
        default=0.0,
        description="Trading account balance after sweep.",
    )
    # Integrity
    block_reason: Optional[str] = Field(
        default=None,
        description="Reason if sweep was BLOCKED.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if sweep FAILED.",
    )
    transfer_boundary: TransferBoundary = Field(
        default=TransferBoundary.INTERNAL_LEDGER_ONLY,
        description="Transfer boundary used for this sweep.",
    )
    idempotency_key: Optional[str] = Field(default=None)
    receipt_hash: Optional[str] = Field(default=None)
    destination_allowlisted: bool = Field(default=False)
    live_lock_triggered: bool = Field(default=False)
