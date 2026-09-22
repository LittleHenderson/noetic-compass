"""CJT diagnostic and readiness schemas.

These models are evidence sidecars. They are not broker authority, live unlock
authority, or proof of compiler-enforced safety.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from cas_forex.time_utils import utc_now


class CjtRegion(str, Enum):
    """Observed operating region for a CJT-style diagnostic."""

    CUTOFF = "cutoff"
    ACTIVE = "active"
    SATURATION = "saturation"
    BREAKDOWN = "breakdown"
    UNKNOWN = "unknown"


class CjtDiagnosticKind(str, Enum):
    """Diagnostic categories that can be attached to evidence."""

    GENERAL = "general"
    FORECAST_DISAGREEMENT = "forecast_disagreement"
    WEAK_EDGE = "weak_edge"
    SINGLE_MODEL_OVERCONFIDENCE = "single_model_overconfidence"
    MACRO_SHOCK = "macro_shock"
    BROKER_MISMATCH = "broker_mismatch"
    DRAWDOWN_OVERLOAD = "drawdown_overload"
    BETA_DRIFT = "beta_drift"
    COMPILER_RESEARCH = "compiler_research"
    LIVE_TRADING_PERMISSION = "live_trading_permission"
    SAFETY_CLAIM = "safety_claim"
    PROMPT_INJECTION_PREVENTION = "prompt_injection_prevention"
    GOVERNANCE_PROOF = "governance_proof"
    BROKER_ACCEPT_CREATION = "broker_accept_creation"


class CjtClaimCeiling(str, Enum):
    """Maximum claim a CJT sidecar may support.

    There is intentionally no ACCEPT value. A CJT diagnostic can explain,
    suppress, flag, or lock. It cannot authorize broker execution.
    """

    OPEN = "OPEN"
    SUPPRESS = "SUPPRESS"
    FLAG_FOR_HUMAN_REVIEW = "FLAG_FOR_HUMAN_REVIEW"
    LIVE_LOCKED = "LIVE_LOCKED"
    NOT_LICENSED = "NOT LICENSED"


class CjtReadinessStatus(str, Enum):
    """Claim status for high-authority CJT production features."""

    OPEN = "OPEN"
    LICENSED = "LICENSED"
    NOT_LICENSED = "NOT LICENSED"


class CjtProductionFeature(str, Enum):
    """High-authority CJT features that need explicit readiness gates."""

    PRODUCTION_COMPILER_SYNTAX = "production_cjt_compiler_syntax"
    LIVE_TRADING_PERMISSION_PATH = "live_trading_permission_path"
    COMPILER_ENFORCED_SAFETY_CLAIM = "compiler_enforced_safety_claim"
    PROMPT_INJECTION_PREVENTION_CLAIM = "prompt_injection_prevention_claim"
    GOVERNANCE_REGULATORY_PROOF_CLAIM = "governance_regulatory_proof_claim"
    BROKER_ACCEPT_CREATION = "broker_accept_creation"


class CjtObservation(BaseModel):
    """A single cause/bias/effect observation."""

    observation_id: str
    cause_ref: str
    bias_ref: str
    effect_ref: str
    region: CjtRegion = CjtRegion.UNKNOWN
    beta_estimate: Optional[float] = Field(default=None, ge=0.0)
    beta_source: str = "unmeasured"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    claim_ceiling: CjtClaimCeiling = CjtClaimCeiling.OPEN
    evidence_refs: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class CjtCircuitDiagnostic(BaseModel):
    """Evidence-only CJT circuit diagnostic."""

    diagnostic_id: str
    kind: CjtDiagnosticKind = CjtDiagnosticKind.GENERAL
    trace_id: Optional[str] = None
    observations: List[CjtObservation] = Field(default_factory=list)
    overall_region: CjtRegion = CjtRegion.UNKNOWN
    claim_ceiling: CjtClaimCeiling = CjtClaimCeiling.OPEN
    can_unlock_live_trading: bool = False
    can_create_broker_accept: bool = False
    evidence: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _block_authority_escalation(self):
        if self.can_unlock_live_trading:
            raise ValueError("CJT diagnostics cannot unlock live trading")
        if self.can_create_broker_accept:
            raise ValueError("CJT diagnostics cannot create broker ACCEPT")
        return self


class CjtProductionReadinessCheck(BaseModel):
    """Readiness status for one high-authority CJT feature."""

    feature: CjtProductionFeature
    status: CjtReadinessStatus
    ready: bool = False
    claim_ceiling: CjtClaimCeiling = CjtClaimCeiling.OPEN
    required_evidence: List[str] = Field(default_factory=list)
    present_evidence: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    can_affect_live_trading: bool = False
    can_create_broker_accept: bool = False
    rationale: str = ""

    @model_validator(mode="after")
    def _enforce_claim_boundary(self):
        if self.ready and self.status != CjtReadinessStatus.LICENSED:
            raise ValueError("Ready CJT production checks must be LICENSED")
        if self.can_create_broker_accept:
            raise ValueError("CJT readiness cannot create broker ACCEPT")
        if self.feature == CjtProductionFeature.BROKER_ACCEPT_CREATION and self.ready:
            raise ValueError("CJT broker ACCEPT creation is not a licensable feature")
        return self


class CjtProductionReadinessReport(BaseModel):
    """Aggregate readiness report for CJT production-authority features."""

    report_id: str
    generated_at: datetime = Field(default_factory=utc_now)
    checks: List[CjtProductionReadinessCheck] = Field(default_factory=list)
    summary: str = ""

    @property
    def all_ready(self) -> bool:
        return bool(self.checks) and all(check.ready for check in self.checks)

    @property
    def any_live_authority(self) -> bool:
        return any(check.can_affect_live_trading for check in self.checks)

    @property
    def any_broker_accept_authority(self) -> bool:
        return any(check.can_create_broker_accept for check in self.checks)
