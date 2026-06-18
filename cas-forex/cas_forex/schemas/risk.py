"""RiskAssessment schema - pre-trade risk evaluation."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from cas_forex.time_utils import utc_now


class RiskAssessment(BaseModel):
    """Pre-trade risk evaluation computed before every order.

    The risk gate uses this to decide whether the current risk posture
    allows the proposed trade.
    """

    assessment_id: str = Field(
        ...,
        description="Unique identifier for this risk assessment.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp of this assessment.",
    )
    # Account state
    account_balance: float = Field(
        ...,
        description="Current account balance in base currency.",
        gt=0,
    )
    account_equity: float = Field(
        ...,
        description="Current account equity (balance + floating P&L).",
        gt=0,
    )
    margin_used: float = Field(
        default=0.0,
        description="Margin currently in use.",
        ge=0.0,
    )
    margin_free: float = Field(
        ...,
        description="Free margin available for new positions.",
        ge=0.0,
    )
    margin_level_pct: float = Field(
        default=100.0,
        description="Margin level as percentage (equity / margin_used * 100).",
    )
    # Drawdown
    daily_drawdown_pct: float = Field(
        default=0.0,
        description="Current daily drawdown as percentage of day-start balance.",
    )
    weekly_drawdown_pct: float = Field(
        default=0.0,
        description="Current weekly drawdown as percentage of week-start balance.",
    )
    max_daily_drawdown_pct: float = Field(
        default=2.0,
        description="Maximum allowed daily drawdown before LIVE_LOCKED.",
    )
    max_weekly_drawdown_pct: float = Field(
        default=5.0,
        description="Maximum allowed weekly drawdown before LIVE_LOCKED.",
    )
    # Position sizing
    proposed_position_size_lots: float = Field(
        ...,
        description="Proposed position size in standard lots.",
        gt=0,
    )
    max_position_size_lots: float = Field(
        default=0.1,
        description="Maximum allowed position size in lots for this risk posture.",
    )
    risk_per_trade_pct: float = Field(
        default=1.0,
        description="Risk per trade as percentage of account balance.",
        ge=0.0,
        le=100.0,
    )
    max_risk_per_trade_pct: float = Field(
        default=0.5,
        description="Maximum allowed risk per trade as percentage of balance.",
    )
    # Exposure
    open_positions_count: int = Field(
        default=0,
        description="Number of currently open positions.",
        ge=0,
    )
    max_open_positions: int = Field(
        default=5,
        description="Maximum allowed concurrent open positions.",
    )
    total_exposure_lots: float = Field(
        default=0.0,
        description="Total exposure across all open positions in lots.",
    )
    max_total_exposure_lots: float = Field(
        default=0.5,
        description="Maximum total exposure across all positions.",
    )
    # Correlation
    correlated_positions_symbols: List[str] = Field(
        default_factory=list,
        description="Symbols of open positions correlated with the proposed trade.",
    )
    correlation_group: Optional[str] = Field(
        default=None,
        description="Correlation group for the proposed symbol.",
    )
    correlated_exposure_lots: float = Field(
        default=0.0,
        description="Open same-direction correlated exposure in lots.",
    )
    max_correlated_exposure_lots: float = Field(
        default=0.2,
        description="Maximum same-direction correlated exposure in lots.",
    )
    same_direction_correlation_count: int = Field(
        default=0,
        description="Number of same-direction correlated positions.",
    )
    # Risk score
    risk_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Composite risk score [0, 1]. Higher = riskier.",
    )

    @property
    def daily_drawdown_breached(self) -> bool:
        return self.daily_drawdown_pct >= self.max_daily_drawdown_pct

    @property
    def weekly_drawdown_breached(self) -> bool:
        return self.weekly_drawdown_pct >= self.max_weekly_drawdown_pct

    @property
    def position_size_exceeded(self) -> bool:
        return self.proposed_position_size_lots > self.max_position_size_lots

    @property
    def open_positions_exceeded(self) -> bool:
        return self.open_positions_count >= self.max_open_positions

    @property
    def exposure_exceeded(self) -> bool:
        return (self.total_exposure_lots + self.proposed_position_size_lots) > self.max_total_exposure_lots

    @property
    def risk_per_trade_exceeded(self) -> bool:
        return self.risk_per_trade_pct > self.max_risk_per_trade_pct

    @property
    def correlated_exposure_exceeded(self) -> bool:
        return (
            self.correlated_exposure_lots + self.proposed_position_size_lots
        ) > self.max_correlated_exposure_lots
