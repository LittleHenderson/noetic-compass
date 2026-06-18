"""CASDecision schema - the output of the CAS Forex Verifier."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from cas_forex.time_utils import utc_now


class Verdict(str, Enum):
    """CAS Harness claim-status discipline applied to forex trading.

    ACCEPT: All gates passed. Route order to broker.
    SUPPRESS: One or more gates failed. Do not trade.
    FLAG_FOR_HUMAN_REVIEW: Gate result is uncertain. Requires human judgment.
    """

    ACCEPT = "ACCEPT"
    SUPPRESS = "SUPPRESS"
    FLAG_FOR_HUMAN_REVIEW = "FLAG_FOR_HUMAN_REVIEW"


class GateStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNDETERMINED = "UNDETERMINED"


class GateResult(BaseModel):
    """Result of a single CAS Verifier gate check."""

    gate_name: str = Field(
        ...,
        description="Name of the gate (market, macro, risk, execution).",
    )
    status: GateStatus = Field(
        ...,
        description="PASS, FAIL, or UNDETERMINED.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Gate confidence [0, 1].",
    )
    reason: str = Field(
        default="",
        description="Human-readable explanation of the gate result.",
    )
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured evidence supporting the gate result.",
    )
    claim_ceiling: str = Field(
        default="OPEN",
        description="Maximum claim that can be made from this gate result.",
    )


class CASDecision(BaseModel):
    """The CAS Verifier's decision on a ForecastProposal.

    This is the authoritative output after all gates have been evaluated.
    Only ACCEPT decisions should be forwarded to the broker.
    """

    decision_id: str = Field(
        ...,
        description="Unique decision identifier (UUID).",
    )
    proposal_ref: str = Field(
        ...,
        description="Reference to the ForecastProposal.proposal_id.",
    )
    symbol: str = Field(..., description="Forex pair symbol.")
    verdict: Verdict = Field(
        ...,
        description="ACCEPT, SUPPRESS, or FLAG_FOR_HUMAN_REVIEW.",
    )
    gate_results: List[GateResult] = Field(
        default_factory=list,
        description="Results from each verifier gate.",
    )
    overriding_gate: Optional[str] = Field(
        default=None,
        description="If SUPPRESS or FLAG_FOR_HUMAN_REVIEW, which gate was the primary cause.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp of this decision.",
    )
    summary: str = Field(
        default="",
        description="One-line summary for audit trail and Evidence Packet.",
    )

    @property
    def is_accepted(self) -> bool:
        return self.verdict == Verdict.ACCEPT

    @property
    def is_suppressed(self) -> bool:
        return self.verdict == Verdict.SUPPRESS

    @property
    def requires_human(self) -> bool:
        return self.verdict == Verdict.FLAG_FOR_HUMAN_REVIEW
