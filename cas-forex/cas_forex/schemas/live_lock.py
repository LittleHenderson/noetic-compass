"""Persistent LIVE_LOCKED state schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from cas_forex.time_utils import utc_now


class LiveLockReason(str, Enum):
    DAILY_DRAWDOWN = "DAILY_DRAWDOWN"
    WEEKLY_DRAWDOWN = "WEEKLY_DRAWDOWN"
    BROKER_DISCONNECT_OPEN_TRADE = "BROKER_DISCONNECT_OPEN_TRADE"
    MARGIN_ERROR = "MARGIN_ERROR"
    EXECUTION_MISMATCH = "EXECUTION_MISMATCH"
    MACRO_SHOCK = "MACRO_SHOCK"
    MODEL_DRIFT = "MODEL_DRIFT"
    EVIDENCE_WRITE_FAILURE = "EVIDENCE_WRITE_FAILURE"
    SAVINGS_TRANSFER_FAILURE = "SAVINGS_TRANSFER_FAILURE"
    MANUAL_OPERATOR_LOCK = "MANUAL_OPERATOR_LOCK"


class LiveLockState(BaseModel):
    lock_id: str
    active: bool = True
    reasons: List[LiveLockReason] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    cleared_at: Optional[datetime] = None
    evidence_refs: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    unlocked_by: Optional[str] = None
    unlock_reason: Optional[str] = None
    effective_session_id: Optional[str] = None


class UnlockReceipt(BaseModel):
    unlock_id: str
    lock_id: str
    operator_id: str
    signed_reason: str
    evidence_receipt_hash: str
    next_session_id: str
    override_open_positions: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    receipt_hash: Optional[str] = None
