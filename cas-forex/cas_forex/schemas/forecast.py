"""ForecastProposal schema - a prediction from a forecast model."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from cas_forex.time_utils import utc_now


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class ModelSource(str, Enum):
    TIMEGPT = "TIMEGPT"
    CHRONOS = "CHRONOS"
    TECHNICAL = "TECHNICAL"
    ENSEMBLE = "ENSEMBLE"


SUPPORTED_SYMBOLS = frozenset(
    {"EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD"}
)


JPY_PAIRS = frozenset({"USD/JPY"})


def pip_multiplier(symbol: str) -> float:
    """Return the pip multiplier: 100 for JPY pairs, 10000 for others."""
    return 100.0 if symbol in JPY_PAIRS else 10000.0


class ForecastProposal(BaseModel):
    """A single trade proposal emitted by a forecast model."""

    proposal_id: str = Field(
        ...,
        description="Unique identifier for this proposal.",
        min_length=1,
    )
    symbol: str = Field(..., description="Forex pair symbol (e.g. EUR/USD).")
    direction: Direction = Field(..., description="LONG or SHORT.")
    entry_price: float = Field(
        ..., description="Proposed entry price. Must be > 0.", gt=0,
    )
    stop_loss: float = Field(
        ..., description="Stop-loss price.", gt=0,
    )
    take_profit: float = Field(
        ..., description="Take-profit price.", gt=0,
    )
    confidence: float = Field(
        ..., description="Model confidence [0, 1].", ge=0.0, le=1.0,
    )
    model_source: ModelSource = Field(
        ..., description="Which model generated this proposal.",
    )
    model_version: str = Field(default="0.1.0")
    timestamp: datetime = Field(default_factory=utc_now)
    horizon_minutes: int = Field(default=60, description="Forecast horizon.", gt=0)
    timeframe: str = Field(
        default="H1",
        description="Timeframe: M1, M5, M15, M30, H1, H4, D1, W1, MN.",
    )
    rationale: Optional[str] = Field(default=None)

    @field_validator("symbol")
    @classmethod
    def symbol_must_be_supported(cls, v: str) -> str:
        if v not in SUPPORTED_SYMBOLS:
            raise ValueError(
                f"Unsupported symbol '{v}'. Supported: {sorted(SUPPORTED_SYMBOLS)}"
            )
        return v

    @model_validator(mode="after")
    def validate_price_consistency(self):
        """Validate stop-loss/take-profit vs direction. Runs AFTER all fields set."""
        d, ep, sl, tp = self.direction, self.entry_price, self.stop_loss, self.take_profit
        if d == Direction.LONG:
            if sl >= ep:
                raise ValueError(
                    f"LONG stop_loss ({sl}) must be < entry_price ({ep})"
                )
            if tp <= ep:
                raise ValueError(
                    f"LONG take_profit ({tp}) must be > entry_price ({ep})"
                )
        else:
            if sl <= ep:
                raise ValueError(
                    f"SHORT stop_loss ({sl}) must be > entry_price ({ep})"
                )
            if tp >= ep:
                raise ValueError(
                    f"SHORT take_profit ({tp}) must be < entry_price ({ep})"
                )
        return self

    @property
    def risk_pips(self) -> float:
        """Risk in pips."""
        return abs(self.entry_price - self.stop_loss) * pip_multiplier(self.symbol)

    @property
    def reward_pips(self) -> float:
        """Reward in pips."""
        return abs(self.take_profit - self.entry_price) * pip_multiplier(self.symbol)

    @property
    def reward_risk_ratio(self) -> float:
        return self.reward_pips / max(self.risk_pips, 1e-9)
