"""Promotion-gate schemas for harvester strategy changes."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from cas_forex.time_utils import utc_now


class PromotionState(str, Enum):
    PROPOSED = "PROPOSED"
    BACKTEST_PASSED = "BACKTEST_PASSED"
    BACKTEST_FAILED = "BACKTEST_FAILED"
    PAPER_PASSED = "PAPER_PASSED"
    PAPER_FAILED = "PAPER_FAILED"
    HUMAN_APPROVED = "HUMAN_APPROVED"
    HUMAN_REJECTED = "HUMAN_REJECTED"
    ANCHORED = "ANCHORED"
    PROMOTED_NEXT_SESSION = "PROMOTED_NEXT_SESSION"


class BacktestValidation(BaseModel):
    passed: bool
    metrics: Dict[str, Any] = Field(default_factory=dict)
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    completed_at: datetime = Field(default_factory=utc_now)


class PaperValidation(BaseModel):
    passed: bool
    metrics: Dict[str, Any] = Field(default_factory=dict)
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    paper_mode: bool = True
    completed_at: datetime = Field(default_factory=utc_now)


class HumanApproval(BaseModel):
    approved_by: str
    approved_at: datetime = Field(default_factory=utc_now)
    signature: str
    signed_payload_hash: str
    signature_scheme: str = "sha256-or-hmac-sha256"


class AnchorReceipt(BaseModel):
    anchor_uri: str
    payload_hash: str
    previous_anchor_hash: Optional[str] = None
    record_hash: str
    anchored_at: datetime = Field(default_factory=utc_now)
    worm_retained: bool = False
    anchor_scheme: str = "local-jsonl-hash-chain"


class StrategyChangeProposal(BaseModel):
    change_id: str
    change_type: str
    current_value: Any = None
    proposed_value: Any = None
    rationale: str = ""
    expected_impact: str = ""
    risk_level: str = "LOW"
    state: PromotionState = PromotionState.PROPOSED
    source_ruleset_hash: Optional[str] = None
    proposed_ruleset_hash: Optional[str] = None
    active_session_id_at_proposal: Optional[str] = None
    effective_session_id: Optional[str] = None
    mid_session_apply_allowed: bool = False
    backtest: Optional[BacktestValidation] = None
    paper: Optional[PaperValidation] = None
    human_approval: Optional[HumanApproval] = None
    anchor: Optional[AnchorReceipt] = None
