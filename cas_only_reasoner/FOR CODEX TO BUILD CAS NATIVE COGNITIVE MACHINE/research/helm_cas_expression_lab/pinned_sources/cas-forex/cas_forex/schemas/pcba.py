"""PCBA-style CAS diagnostic and readiness schemas.

The PCBA models are evidence/visualization sidecars. They are not production
compiler authority, live trading authority, regulatory proof, or broker ACCEPT
authority.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator

from cas_forex.time_utils import utc_now


class PcbaComponentKind(str, Enum):
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    DIODE = "diode"
    TRANSFORMER = "transformer"
    OP_AMP = "op_amp"
    OSCILLATOR = "oscillator"
    LOGIC_GATE = "logic_gate"
    MUX = "mux"
    DEMUX = "demux"
    REGULATOR = "regulator"
    FUSE = "fuse"
    CIRCUIT_BREAKER = "circuit_breaker"
    TRACE = "trace"
    VIA = "via"
    VARACTOR = "varactor"
    RELAY = "relay"
    SCHMITT_TRIGGER = "schmitt_trigger"
    PHOTODIODE = "photodiode"
    CRYSTAL_OSCILLATOR = "crystal_oscillator"
    ADC = "adc"
    DAC = "dac"
    BRIDGE_RECTIFIER = "bridge_rectifier"


class PcbaBoardKind(str, Enum):
    COGNITIVE_SAFETY_BOARD = "cognitive_safety_board"
    COGNITIVE_OSCILLATOR_BOARD = "cognitive_oscillator_board"
    COGNITIVE_DIFFERENTIAL_AMPLIFIER_BOARD = "cognitive_differential_amplifier_board"
    COGNITIVE_MEMORY_BOARD = "cognitive_memory_board"
    COGNITIVE_POWER_MANAGEMENT_BOARD = "cognitive_power_management_board"


class PcbaClaimCeiling(str, Enum):
    """Maximum claim a PCBA diagnostic may support.

    There is intentionally no ACCEPT value.
    """

    OPEN = "OPEN"
    SUPPRESS = "SUPPRESS"
    FLAG_FOR_HUMAN_REVIEW = "FLAG_FOR_HUMAN_REVIEW"
    LIVE_LOCKED = "LIVE_LOCKED"
    NOT_LICENSED = "NOT LICENSED"


class PcbaReadinessStatus(str, Enum):
    OPEN = "OPEN"
    LICENSED = "LICENSED"
    NOT_LICENSED = "NOT LICENSED"


class PcbaProductionFeature(str, Enum):
    PRODUCTION_COMPONENT_SYNTAX = "production_pcba_component_syntax"
    LIVE_TRADING_PERMISSION_PATH = "live_trading_permission_path"
    COMPILER_ENFORCED_SAFETY_CLAIM = "compiler_enforced_safety_claim"
    PROMPT_INJECTION_PREVENTION_CLAIM = "prompt_injection_prevention_claim"
    GOVERNANCE_REGULATORY_PROOF_CLAIM = "governance_regulatory_proof_claim"
    BROKER_ACCEPT_CREATION = "broker_accept_creation"
    REFERENCE_BOARD_SAFETY_CLAIM = "reference_board_safety_claim"
    MEMORY_BOARD_COGNITIVE_MEMORY_CLAIM = "memory_board_cognitive_memory_claim"
    POWER_BOARD_BURNOUT_PREVENTION_CLAIM = "power_board_burnout_prevention_claim"


class PcbaComponentDiagnostic(BaseModel):
    diagnostic_id: str
    kind: PcbaComponentKind
    target_ref: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    cas_mapping: str = ""
    claim_ceiling: PcbaClaimCeiling = PcbaClaimCeiling.OPEN
    can_unlock_live_trading: bool = False
    can_create_broker_accept: bool = False
    evidence_refs: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _block_authority_escalation(self):
        if self.can_unlock_live_trading:
            raise ValueError("PCBA diagnostics cannot unlock live trading")
        if self.can_create_broker_accept:
            raise ValueError("PCBA diagnostics cannot create broker ACCEPT")
        return self


class PcbaBoardDiagnostic(BaseModel):
    board_id: str
    board_kind: PcbaBoardKind
    purpose: str = ""
    component_kinds: List[PcbaComponentKind] = Field(default_factory=list)
    test_points: List[str] = Field(default_factory=list)
    failure_modes: List[str] = Field(default_factory=list)
    claim_ceiling: PcbaClaimCeiling = PcbaClaimCeiling.OPEN
    can_unlock_live_trading: bool = False
    can_create_broker_accept: bool = False
    evidence: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def _block_authority_escalation(self):
        if self.can_unlock_live_trading:
            raise ValueError("PCBA boards cannot unlock live trading")
        if self.can_create_broker_accept:
            raise ValueError("PCBA boards cannot create broker ACCEPT")
        return self


class PcbaProductionReadinessCheck(BaseModel):
    feature: PcbaProductionFeature
    status: PcbaReadinessStatus
    ready: bool = False
    claim_ceiling: PcbaClaimCeiling = PcbaClaimCeiling.OPEN
    required_evidence: List[str] = Field(default_factory=list)
    present_evidence: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    can_affect_live_trading: bool = False
    can_create_broker_accept: bool = False
    rationale: str = ""

    @model_validator(mode="after")
    def _enforce_claim_boundary(self):
        if self.ready and self.status != PcbaReadinessStatus.LICENSED:
            raise ValueError("Ready PCBA production checks must be LICENSED")
        if self.can_create_broker_accept:
            raise ValueError("PCBA readiness cannot create broker ACCEPT")
        if self.feature == PcbaProductionFeature.BROKER_ACCEPT_CREATION and self.ready:
            raise ValueError("PCBA broker ACCEPT creation is not a licensable feature")
        return self


class PcbaProductionReadinessReport(BaseModel):
    report_id: str
    generated_at: datetime = Field(default_factory=utc_now)
    checks: List[PcbaProductionReadinessCheck] = Field(default_factory=list)
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
