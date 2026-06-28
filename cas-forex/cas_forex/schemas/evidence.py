"""ForexEvidencePacket schema - complete audit trail for a trade."""

import hashlib
import json
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from cas_forex.time_utils import utc_now


class PacketStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    SUPPRESSED = "SUPPRESSED"
    FLAG_FOR_HUMAN_REVIEW = "FLAG_FOR_HUMAN_REVIEW"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    CLOSED_WIN = "CLOSED_WIN"
    CLOSED_LOSS = "CLOSED_LOSS"
    CANCELLED = "CANCELLED"
    LIVE_LOCKED = "LIVE_LOCKED"
    WRITE_FAILED = "WRITE_FAILED"


class ForexEvidencePacket(BaseModel):
    """Complete audit trail from market snapshot through final outcome.

    Generated for every proposed, accepted, suppressed, executed, and closed
    trade. Follows CAS Harness Evidence Packet discipline:
    - Immutable after finalization.
    - Hash-covered for integrity.
    - Verdict follows claim-status discipline (ACCEPT/SUPPRESS/FLAG_FOR_HUMAN_REVIEW).
    """

    packet_id: str = Field(
        ...,
        description="Unique Evidence Packet identifier (UUID).",
    )
    trace_id: str = Field(
        ...,
        description="Trace identifier linking this packet to its trade lifecycle.",
    )
    status: PacketStatus = Field(
        default=PacketStatus.PROPOSED,
        description="Current state of this trade in the lifecycle.",
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        description="UTC timestamp when the packet was first created.",
    )
    finalized_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp when the packet was finalized (immutable).",
    )

    # Core artifacts
    proposal: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Serialized ForecastProposal that started this trade.",
    )
    market_snapshot: Optional[Dict[str, Any]] = Field(
        default=None,
        description="MarketSnapshot at the time of proposal evaluation.",
    )
    cas_decision: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Serialized CASDecision from the verifier.",
    )
    risk_assessment: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Serialized RiskAssessment.",
    )
    order_request: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Serialized BrokerOrderRequest sent to MetaTrader.",
    )
    order_outcome: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Serialized OrderOutcome from broker execution.",
    )
    close_outcome: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Trade close result: profit/loss in account currency and pips.",
    )
    sweep_transaction: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Serialized SweepTransaction if profit was swept.",
    )

    # Meta
    profit_loss_account: Optional[float] = Field(
        default=None,
        description="Realized profit/loss in account currency.",
    )
    profit_loss_pips: Optional[float] = Field(
        default=None,
        description="Realized profit/loss in pips.",
    )
    holding_duration_seconds: Optional[float] = Field(
        default=None,
        description="How long the position was held.",
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Human or automated notes added during the trade lifecycle.",
    )
    cjt_diagnostics: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Optional evidence-only CJT diagnostics. These may explain, suppress, "
            "flag, or lock, but cannot authorize ACCEPT."
        ),
    )
    pcba_diagnostics: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Optional evidence-only PCBA diagnostics. These may explain, suppress, "
            "flag, or lock, but cannot authorize ACCEPT."
        ),
    )

    # Integrity
    packet_hash_sha256: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of the packet content (computed before this field is set).",
    )

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the packet, excluding the hash field itself."""
        data = self.model_dump(exclude={"packet_hash_sha256"})
        canonical = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def finalize(self) -> None:
        """Finalize the packet: set finalized_at then compute hash."""
        self.finalized_at = utc_now()
        self.packet_hash_sha256 = self.compute_hash()

    def verify_hash(self) -> bool:
        """Verify that the stored hash matches recomputed hash."""
        if self.packet_hash_sha256 is None:
            return False
        return self.compute_hash() == self.packet_hash_sha256


class EvidenceReceipt(BaseModel):
    """Receipt for an append-only local evidence-chain record."""

    packet_id: str
    trace_id: str
    run_id: str
    event_seq: int
    packet_hash: str
    record_hash: str
    previous_record_hash: Optional[str] = None
    store_uri: str
    created_at: datetime = Field(default_factory=utc_now)
    worm_retained: bool = False
    anchor_scheme: str = "local-jsonl-hash-chain"


class PostTradeObservation(BaseModel):
    """A broker/post-trade observation recorded after order placement."""

    trace_id: str
    broker_ticket: Optional[int] = None
    symbol: str
    status: str
    floating_profit: float = 0.0
    realized_profit: Optional[float] = None
    profit_pips: Optional[float] = None
    slippage_pips: Optional[float] = None
    margin_level_pct: Optional[float] = None
    mismatch_detected: bool = False
    lock_reason: Optional[str] = None
    observed_at: datetime = Field(default_factory=utc_now)
    evidence: Dict[str, Any] = Field(default_factory=dict)


class BacktestEvidenceReport(BaseModel):
    """Summary artifact for a verified comparative backtest run."""

    report_id: str
    run_id: str
    symbols: List[str] = Field(default_factory=list)
    variants: List[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
    packet_count: int = 0
    chain_verified: bool = False
    metrics_by_symbol: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    variant_metrics: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    passed: bool = False
    failure_reasons: List[str] = Field(default_factory=list)


class PaperTradingSessionReport(BaseModel):
    """Summary artifact for a 30-trading-day paper proof run."""

    report_id: str
    session_id: str
    required_trading_days: int = 30
    completed_trading_days: int = 0
    symbols: List[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
    packet_count: int = 0
    chain_verified: bool = False
    live_mode_used: bool = False
    open_positions_reconciled: bool = False
    live_locks: List[str] = Field(default_factory=list)
    daily_summaries: List[Dict[str, Any]] = Field(default_factory=list)
    broker_verified_days: int = 0
    net_pnl_usd: float = 0.0
    max_drawdown_pct: float = 0.0
    days_with_trades: int = 0
    min_trade_days_required: int = 0
    profit_passed: bool = False
    profit_thresholds: Dict[str, Any] = Field(default_factory=dict)
    passed: bool = False
    failure_reasons: List[str] = Field(default_factory=list)
