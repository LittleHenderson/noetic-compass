"""MarketSnapshot schema - current market state at the time of a proposal."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from cas_forex.schemas.forecast import SUPPORTED_SYMBOLS
from cas_forex.time_utils import utc_now


class MarketSnapshot(BaseModel):
    """A point-in-time snapshot of market conditions for a symbol.

    Captured when a ForecastProposal is evaluated so the CAS Verifier gates
    have consistent input.
    """

    symbol: str = Field(..., description="Forex pair symbol.")
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp of this snapshot.",
    )
    bid: float = Field(..., description="Current bid price.", gt=0)
    ask: float = Field(..., description="Current ask price.", gt=0)
    spread: float = Field(
        default=0.0,
        description="Current spread in pips (ask - bid).",
    )
    volume_1m: Optional[int] = Field(
        default=None,
        description="Tick volume in last 1 minute.",
    )
    # OHLCV for the current candle
    open: Optional[float] = Field(default=None, description="Current candle open.", gt=0)
    high: Optional[float] = Field(default=None, description="Current candle high.", gt=0)
    low: Optional[float] = Field(default=None, description="Current candle low.", gt=0)
    close: Optional[float] = Field(
        default=None, description="Current candle close (latest price).", gt=0
    )
    timeframe: str = Field(
        default="M5",
        description="Timeframe of the OHLCV data (M1, M5, M15, H1, D1).",
    )
    # Session info
    session: str = Field(
        default="UNKNOWN",
        description="Current trading session: ASIAN, LONDON, NEW_YORK, OVERLAP, UNKNOWN.",
    )
    is_market_open: bool = Field(
        default=True,
        description="Whether the underlying market is open for trading.",
    )

    @field_validator("symbol")
    @classmethod
    def symbol_must_be_supported(cls, v: str) -> str:
        if v not in SUPPORTED_SYMBOLS:
            raise ValueError(
                f"Unsupported symbol '{v}'. Supported: {sorted(SUPPORTED_SYMBOLS)}"
            )
        return v

    @property
    def mid(self) -> float:
        """Mid price (average of bid and ask)."""
        return (self.bid + self.ask) / 2.0
