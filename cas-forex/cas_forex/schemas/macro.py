"""Macro-event schemas for forex blackout and shock handling."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MacroEventType(str, Enum):
    NFP = "NFP"
    CPI = "CPI"
    FOMC = "FOMC"
    GDP = "GDP"
    UNEMPLOYMENT = "UNEMPLOYMENT"
    CENTRAL_BANK_SPEECH = "CENTRAL_BANK_SPEECH"
    RATE_DECISION = "RATE_DECISION"


class MacroImpact(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MacroReleaseStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    RELEASED = "RELEASED"
    REVISED = "REVISED"
    CANCELLED = "CANCELLED"


class MacroEventState(BaseModel):
    """One scheduled or released macro event that can affect forex trading."""

    event_id: str
    event_type: MacroEventType
    currency: str = Field(default="USD", min_length=3, max_length=3)
    scheduled_at_utc: datetime
    source: str = "static-2026-seed"
    expected: Optional[float] = None
    actual: Optional[float] = None
    previous: Optional[float] = None
    impact: MacroImpact = MacroImpact.HIGH
    blackout_before_minutes: int = Field(default=15, ge=0)
    blackout_after_minutes: int = Field(default=15, ge=0)
    shock_threshold: Optional[float] = None
    release_status: MacroReleaseStatus = MacroReleaseStatus.SCHEDULED

    @property
    def surprise_abs(self) -> Optional[float]:
        if self.actual is None or self.expected is None:
            return None
        return self.actual - self.expected

    @property
    def surprise_pct(self) -> Optional[float]:
        if self.actual is None or self.expected in (None, 0):
            return None
        return (self.actual - self.expected) / abs(self.expected) * 100.0

    @property
    def shock_active(self) -> bool:
        if self.shock_threshold is None or self.surprise_abs is None:
            return False
        return abs(self.surprise_abs) >= self.shock_threshold
