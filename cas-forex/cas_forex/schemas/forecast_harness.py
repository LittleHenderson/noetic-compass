"""Forecast-harness schemas for model evidence and drift gating."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from cas_forex.schemas.forecast import Direction
from cas_forex.time_utils import utc_now


class ForecastSignalStatus(str, Enum):
    OK = "OK"
    NO_SIGNAL = "NO_SIGNAL"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"
    WEAK_EDGE = "WEAK_EDGE"
    DRIFT_BREACH = "DRIFT_BREACH"


class ForecastHarnessVerdict(str, Enum):
    PASS = "PASS"
    SUPPRESS = "SUPPRESS"
    FLAG_FOR_HUMAN_REVIEW = "FLAG_FOR_HUMAN_REVIEW"
    LIVE_LOCKED = "LIVE_LOCKED"


class ForecastSignal(BaseModel):
    model: str
    model_version: str = "unknown"
    status: ForecastSignalStatus
    direction: Optional[Direction] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    point_forecast: Optional[float] = None
    expected_move_pips: Optional[float] = None
    interval_low: Optional[float] = None
    interval_high: Optional[float] = None
    baseline_comparison: Dict[str, float] = Field(default_factory=dict)
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)


class ForecastHarnessReport(BaseModel):
    report_id: str
    symbol: str
    generated_at: datetime = Field(default_factory=utc_now)
    signals: List[ForecastSignal] = Field(default_factory=list)
    baseline_results: Dict[str, float] = Field(default_factory=dict)
    agreement_score: float = Field(default=0.0, ge=0.0, le=1.0)
    interval_stable: bool = True
    drift_breach: bool = False
    verdict: ForecastHarnessVerdict = ForecastHarnessVerdict.SUPPRESS
    reason_codes: List[str] = Field(default_factory=list)
    cjt_diagnostics: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Optional evidence-only CJT diagnostics; never broker ACCEPT authority.",
    )
    pcba_diagnostics: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Optional evidence-only PCBA diagnostics; never broker ACCEPT authority.",
    )

    @property
    def is_pass(self) -> bool:
        return self.verdict == ForecastHarnessVerdict.PASS
