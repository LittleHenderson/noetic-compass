"""Self-Improving Harvester — offline strategy refinement loop.

Reads trajectory data (proposals, gate results, executions, closes, sweeps),
identifies failure patterns, and proposes strategy/config changes.

SAFETY RULES:
  1. NEVER mutate live execution rules mid-session.
  2. All changes are proposals only — human approval required.
  3. Every change must pass backtest + paper-trading before promotion.
  4. Evidence Packets track every proposal, test, and decision.

Architecture (from self-improving-harness.pdf):
  Trajectory Log → Window Review → Failure Signature Detection →
  Strategy Change Proposal → Backtest Validation → Evidence Packet →
  Human Approval Gate → Promote (or reject)
"""

import json
import hashlib
import hmac
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from cas_forex.config import config
from cas_forex.schemas.decision import GateStatus, Verdict
from cas_forex.schemas.forecast import Direction, ForecastProposal, ModelSource
from cas_forex.schemas.promotion import (
    AnchorReceipt,
    BacktestValidation,
    HumanApproval,
    PaperValidation,
    PromotionState,
    StrategyChangeProposal,
)
from cas_forex.time_utils import utc_now


class TrajectoryWindow:
    """A sliding window of N trades with aggregated statistics."""

    def __init__(self, trades: List[dict], window_size: int = 10):
        self.trades = trades[-window_size:]
        self.window_size = window_size

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.get("won", False))
        return wins / len(self.trades)

    @property
    def avg_pnl(self) -> float:
        if not self.trades:
            return 0.0
        return np.mean([t.get("pnl", 0.0) for t in self.trades])

    @property
    def suppressed_rate(self) -> float:
        total = len(self.trades) + sum(
            t.get("suppressed_count", 0) for t in self.trades
        )
        if total == 0:
            return 0.0
        suppressed = sum(t.get("suppressed_count", 0) for t in self.trades)
        return suppressed / total

    @property
    def avg_lacunarity(self) -> float:
        vals = [t.get("lacunarity", 0.0) for t in self.trades if "lacunarity" in t]
        return float(np.mean(vals)) if vals else 0.0

    @property
    def rpm_break_rate(self) -> float:
        if not self.trades:
            return 0.0
        breaks = sum(1 for t in self.trades if t.get("rpm_broken", False))
        return breaks / len(self.trades)


class FailureSignature:
    """A detected pattern in losing trades."""

    def __init__(self):
        self.name: str = ""
        self.description: str = ""
        self.count: int = 0
        self.avg_loss_pips: float = 0.0
        self.conditions: Dict[str, any] = {}
        self.suggested_fix: str = ""


class StrategyChange:
    """A proposed config rule change with evidence."""

    def __init__(self):
        self.change_id: str = ""
        self.change_type: str = ""  # "risk", "confidence", "timeframe", "gate"
        self.current_value: any = None
        self.proposed_value: any = None
        self.rationale: str = ""
        self.expected_impact: str = ""
        self.risk_level: str = "LOW"  # LOW, MEDIUM, HIGH
        self.backtest_result: Optional[dict] = None
        self.approved: bool = False
        self.state: PromotionState = PromotionState.PROPOSED

    def to_promotion_proposal(
        self,
        active_session_id: Optional[str] = None,
    ) -> StrategyChangeProposal:
        return StrategyChangeProposal(
            change_id=self.change_id,
            change_type=self.change_type,
            current_value=self.current_value,
            proposed_value=self.proposed_value,
            rationale=self.rationale,
            expected_impact=self.expected_impact,
            risk_level=self.risk_level,
            state=self.state,
            active_session_id_at_proposal=active_session_id,
        )


class Harvester:
    """Offline strategy improvement engine.

    Reads trajectory logs, identifies failure patterns, proposes changes.
    NEVER mutates live config — outputs proposals only.
    """

    def __init__(self):
        self.trajectory: List[dict] = []
        self.windows: List[TrajectoryWindow] = []
        self.signatures: List[FailureSignature] = []
        self.changes: List[StrategyChange] = []
        self.evidence_packets: List[dict] = []

    def ingest_trade(self, trade_data: dict) -> None:
        """Record a single trade trajectory entry."""
        record = {
            "timestamp": trade_data.get("timestamp", utc_now().isoformat()),
            "symbol": trade_data.get("symbol", "EUR/USD"),
            "direction": trade_data.get("direction", "UNKNOWN"),
            "entry_price": trade_data.get("entry_price", 0.0),
            "exit_price": trade_data.get("exit_price", 0.0),
            "pnl": trade_data.get("pnl", 0.0),
            "pnl_pips": trade_data.get("pnl_pips", 0.0),
            "won": trade_data.get("won", False),
            "verdict": trade_data.get("verdict", "UNKNOWN"),
            "suppressed_count": trade_data.get("suppressed_count", 0),
            "suppress_reasons": trade_data.get("suppress_reasons", []),
            "rpm_broken": trade_data.get("rpm_broken", False),
            "rpm_break_step": trade_data.get("rpm_break_step"),
            "lacunarity": trade_data.get("lacunarity", 0.0),
            "leakage_detected": trade_data.get("leakage_detected", False),
            "timeframe": trade_data.get("timeframe", "H1"),
            "confidence": trade_data.get("confidence", 0.0),
            "model": trade_data.get("model", "UNKNOWN"),
        }
        self.trajectory.append(record)

    def review_windows(self, window_size: int = 10) -> List[TrajectoryWindow]:
        """Slice trajectory into sliding windows and compute stats."""
        self.windows = []
        for i in range(0, len(self.trajectory), max(1, window_size // 2)):
            window = TrajectoryWindow(self.trajectory[i : i + window_size], window_size)
            self.windows.append(window)
        return self.windows

    def find_failure_signatures(self) -> List[FailureSignature]:
        """Analyze trajectory for common failure patterns."""
        self.signatures = []

        losses = [t for t in self.trajectory if not t["won"]]
        if not losses:
            return self.signatures

        # Signature 1: High lacunarity losers
        high_lac = [t for t in losses if t.get("lacunarity", 0) > 1.5]
        if high_lac:
            sig = FailureSignature()
            sig.name = "HIGH_LACUNARITY_LOSSES"
            sig.description = "Losing trades with lacunarity above 1.5 (gappy evidence)"
            sig.count = len(high_lac)
            sig.avg_loss_pips = float(np.mean([t["pnl_pips"] for t in high_lac]))
            sig.conditions = {"lacunarity_threshold": 1.5, "loss_count": len(high_lac)}
            sig.suggested_fix = "Lower lacunarity rejection threshold from 2.0 to 1.5"
            self.signatures.append(sig)

        # Signature 2: RPM chain breaks in losers
        rpm_losses = [t for t in losses if t.get("rpm_broken")]
        if rpm_losses:
            sig = FailureSignature()
            sig.name = "RPM_BREAK_LOSSES"
            sig.description = "Losing trades with broken prerequisite chains"
            sig.count = len(rpm_losses)
            sig.avg_loss_pips = float(np.mean([t["pnl_pips"] for t in rpm_losses]))
            steps = defaultdict(int)
            for t in rpm_losses:
                if t.get("rpm_break_step"):
                    steps[t["rpm_break_step"]] += 1
            sig.conditions = {"break_steps": dict(steps)}
            sig.suggested_fix = "Require RPM chain intact before any trade; tighten confidence floor"
            self.signatures.append(sig)

        # Signature 3: Repeated suppress reasons
        suppressed = [t for t in self.trajectory if t.get("suppress_reasons")]
        if suppressed:
            reason_counts = defaultdict(int)
            for t in suppressed:
                for reason in t.get("suppress_reasons", []):
                    reason_counts[reason] += 1
            top_reasons = sorted(reason_counts.items(), key=lambda x: -x[1])[:3]
            if top_reasons:
                sig = FailureSignature()
                sig.name = "FREQUENT_SUPPRESSION"
                sig.description = f"Most common suppress reasons: {dict(top_reasons)}"
                sig.count = len(suppressed)
                sig.conditions = {"top_reasons": dict(top_reasons)}
                sig.suggested_fix = (
                    "If 'spread' dominates: increase max_spread_pips. "
                    "If 'drawdown' dominates: lower max_position_lots."
                )
                self.signatures.append(sig)

        # Signature 4: Confidence decay (declining confidence over time)
        recent = self.trajectory[-20:]
        if len(recent) >= 10:
            first_half = [t["confidence"] for t in recent[:10]]
            second_half = [t["confidence"] for t in recent[-10:]]
            if np.mean(first_half) > np.mean(second_half) + 0.1:
                sig = FailureSignature()
                sig.name = "CONFIDENCE_DECAY"
                sig.description = "Model confidence declining over last 20 trades"
                sig.count = len(recent)
                sig.conditions = {
                    "first_half_avg": round(float(np.mean(first_half)), 3),
                    "second_half_avg": round(float(np.mean(second_half)), 3),
                }
                sig.suggested_fix = "Model may be degrading — retrain or switch model source"
                self.signatures.append(sig)

        return self.signatures

    def propose_changes(self) -> List[StrategyChange]:
        """Generate strategy change proposals from failure signatures."""
        self.changes = []

        for sig in self.signatures:
            change = StrategyChange()
            change.change_id = f"harvest-{len(self.changes):04d}"
            change.rationale = f"{sig.name}: {sig.description} ({sig.count} occurrences, avg loss {sig.avg_loss_pips:.1f} pips)"

            if sig.name == "HIGH_LACUNARITY_LOSSES":
                change.change_type = "gate"
                change.current_value = 2.0
                change.proposed_value = 1.5
                change.expected_impact = f"Would have suppressed {sig.count} losing trades"
                change.risk_level = "LOW"

            elif sig.name == "RPM_BREAK_LOSSES":
                change.change_type = "gate"
                change.current_value = "RPM check optional"
                change.proposed_value = "RPM check mandatory"
                change.expected_impact = f"Would have blocked {sig.count} RPM-broken trades"
                change.risk_level = "LOW"

            elif sig.name == "CONFIDENCE_DECAY":
                change.change_type = "model"
                change.current_value = "Auto-select ensemble"
                change.proposed_value = "Force TimeGPT primary when confidence decays"
                change.expected_impact = "Switch to stronger model during degradation"
                change.risk_level = "MEDIUM"

            self.changes.append(change)

        return self.changes

    def validate_change(self, change: StrategyChange, backtest_fn) -> StrategyChange:
        """Run a proposed change through backtest validation.

        Args:
            change: The proposed strategy change.
            backtest_fn: A callable that takes config overrides and returns BacktestResult.

        Returns change with backtest_result populated.
        """
        # Run backtest with proposed config
        try:
            result = backtest_fn(change)
            change.backtest_result = result.summary() if result else None
        except Exception as e:
            change.backtest_result = {"error": str(e)}

        return change

    def build_evidence_packet(self, change: StrategyChange) -> dict:
        """Create an evidence packet for a strategy change proposal."""
        packet = {
            "packet_id": change.change_id,
            "timestamp": utc_now().isoformat(),
            "change_type": change.change_type,
            "current_value": str(change.current_value),
            "proposed_value": str(change.proposed_value),
            "rationale": change.rationale,
            "expected_impact": change.expected_impact,
            "risk_level": change.risk_level,
            "backtest_result": change.backtest_result,
            "approval_status": "PENDING_HUMAN_REVIEW",
            "safety_rules": [
                "Never mutate live execution rules mid-session",
                "All changes require human approval",
                "Must pass backtest + paper-trading before promotion",
                "Evidence Packets track every proposal, test, and decision",
            ],
        }
        self.evidence_packets.append(packet)
        return packet

    def run_full_cycle(
        self,
        trajectory_data: List[dict],
        window_size: int = 10,
        backtest_fn=None,
    ) -> Tuple[List[FailureSignature], List[StrategyChange], List[dict]]:
        """Run a complete harvester cycle: review → find → propose → validate → packet.

        Returns: (signatures, changes, evidence_packets)
        """
        # Ingest all trades
        for trade in trajectory_data:
            self.ingest_trade(trade)

        # Review windows
        self.review_windows(window_size)

        # Find failure patterns
        self.find_failure_signatures()

        # Propose changes
        self.propose_changes()

        # Validate each change
        if backtest_fn:
            for change in self.changes:
                self.validate_change(change, backtest_fn)

        # Build evidence packets
        packets = []
        for change in self.changes:
            packets.append(self.build_evidence_packet(change))

        return self.signatures, self.changes, packets

    def summary(self) -> dict:
        """Return a human-readable summary of harvester findings."""
        return {
            "total_trades_analyzed": len(self.trajectory),
            "windows_reviewed": len(self.windows),
            "failure_signatures_found": len(self.signatures),
            "changes_proposed": len(self.changes),
            "evidence_packets_generated": len(self.evidence_packets),
            "signatures": [s.name for s in self.signatures],
            "latest_window": {
                "win_rate": self.windows[-1].win_rate if self.windows else 0,
                "avg_pnl": self.windows[-1].avg_pnl if self.windows else 0,
                "avg_lacunarity": self.windows[-1].avg_lacunarity if self.windows else 0,
            } if self.windows else None,
        }

    def build_promotion_proposals(
        self,
        active_session_id: Optional[str] = None,
    ) -> List[StrategyChangeProposal]:
        """Convert proposed strategy changes into gated promotion proposals."""
        return [
            change.to_promotion_proposal(active_session_id=active_session_id)
            for change in self.changes
        ]


class PromotionController:
    """State machine for promoting harvester proposals.

    Promotion is next-session only. This controller does not mutate live
    execution rules and refuses direct jumps around backtest, paper, approval,
    and anchoring gates.
    """

    DEFAULT_BACKTEST_THRESHOLDS = {
        "min_trades": 1,
        "max_drawdown_pct": 20.0,
        "min_profit_factor": 0.0,
    }
    DEFAULT_PAPER_THRESHOLDS = {
        "min_trades": 1,
        "max_drawdown_pct": 10.0,
        "min_profit_factor": 0.0,
    }

    def __init__(
        self,
        anchor_path: Optional[str | Path] = None,
        active_session_id: str = "active",
    ):
        self.anchor_path = Path(anchor_path or "promotion_anchors.jsonl")
        self.active_session_id = active_session_id

    def run_backtest_gate(
        self,
        proposal: StrategyChangeProposal,
        result: Any,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> StrategyChangeProposal:
        metrics = self._summary(result)
        checks = thresholds or self.DEFAULT_BACKTEST_THRESHOLDS
        passed = self._metrics_pass(metrics, checks)
        proposal.backtest = BacktestValidation(
            passed=passed,
            metrics=metrics,
            thresholds=checks,
        )
        proposal.state = (
            PromotionState.BACKTEST_PASSED
            if passed else PromotionState.BACKTEST_FAILED
        )
        return proposal

    def run_paper_gate(
        self,
        proposal: StrategyChangeProposal,
        metrics: Dict[str, Any],
        thresholds: Optional[Dict[str, Any]] = None,
        live_mode: bool = False,
    ) -> StrategyChangeProposal:
        if proposal.state != PromotionState.BACKTEST_PASSED:
            raise ValueError("Paper gate requires BACKTEST_PASSED")
        if live_mode:
            raise ValueError("Paper gate must not run in live mode")
        checks = thresholds or self.DEFAULT_PAPER_THRESHOLDS
        passed = self._metrics_pass(metrics, checks)
        proposal.paper = PaperValidation(
            passed=passed,
            metrics=metrics,
            thresholds=checks,
            paper_mode=True,
        )
        proposal.state = (
            PromotionState.PAPER_PASSED
            if passed else PromotionState.PAPER_FAILED
        )
        return proposal

    def approve_change(
        self,
        proposal: StrategyChangeProposal,
        approver_id: str,
        signature: str,
        secret: Optional[str] = None,
    ) -> StrategyChangeProposal:
        if proposal.state != PromotionState.PAPER_PASSED:
            raise ValueError("Human approval requires PAPER_PASSED")
        payload_hash = self.payload_hash(proposal)
        expected = (
            hmac.new(
                secret.encode("utf-8"),
                payload_hash.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if secret
            else payload_hash
        )
        if not hmac.compare_digest(signature, expected):
            proposal.state = PromotionState.HUMAN_REJECTED
            raise ValueError("Invalid human approval signature")

        proposal.human_approval = HumanApproval(
            approved_by=approver_id,
            signature=signature,
            signed_payload_hash=payload_hash,
        )
        proposal.state = PromotionState.HUMAN_APPROVED
        return proposal

    def anchor_change(
        self,
        proposal: StrategyChangeProposal,
    ) -> StrategyChangeProposal:
        if proposal.state != PromotionState.HUMAN_APPROVED:
            raise ValueError("Anchoring requires HUMAN_APPROVED")
        self.anchor_path.parent.mkdir(parents=True, exist_ok=True)
        previous = self._last_anchor_hash()
        payload_hash = self.payload_hash(proposal)
        if proposal.human_approval is None:
            raise ValueError("Anchoring requires human approval receipt")
        if proposal.human_approval.signed_payload_hash != payload_hash:
            raise ValueError("Human approval payload hash does not match proposal")
        record = {
            "change_id": proposal.change_id,
            "payload_hash": payload_hash,
            "previous_anchor_hash": previous,
            "anchored_at": utc_now().isoformat(),
        }
        record_hash = self._sha256(record)
        record["record_hash"] = record_hash
        with self.anchor_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
            f.flush()

        proposal.anchor = AnchorReceipt(
            anchor_uri=str(self.anchor_path),
            payload_hash=payload_hash,
            previous_anchor_hash=previous,
            record_hash=record_hash,
            worm_retained=False,
        )
        proposal.state = PromotionState.ANCHORED
        return proposal

    def promote_next_session(
        self,
        proposal: StrategyChangeProposal,
        next_session_id: str,
        ruleset_dir: Optional[str | Path] = None,
    ) -> Optional[Path]:
        if proposal.state != PromotionState.ANCHORED:
            raise ValueError("Promotion requires ANCHORED")
        self._validate_anchor_for_promotion(proposal)
        if next_session_id == self.active_session_id:
            raise ValueError("Promotion must target a future session")
        proposal.effective_session_id = next_session_id
        proposal.mid_session_apply_allowed = False
        proposal.state = PromotionState.PROMOTED_NEXT_SESSION

        if ruleset_dir is None:
            return None
        target_dir = Path(ruleset_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{proposal.change_id}_{next_session_id}.json"
        path.write_text(
            json.dumps(proposal.model_dump(mode="json"), sort_keys=True, indent=2),
            encoding="utf-8",
        )
        return path

    def verify_anchor_log(self) -> bool:
        if not self.anchor_path.exists():
            return True
        previous = None
        for line in self.anchor_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return False
            record_hash = record.get("record_hash")
            payload = dict(record)
            payload.pop("record_hash", None)
            if record.get("previous_anchor_hash") != previous:
                return False
            if self._sha256(payload) != record_hash:
                return False
            previous = record_hash
        return True

    def payload_hash(self, proposal: StrategyChangeProposal) -> str:
        # Hash only the proposal substance and validation evidence. Workflow
        # state/receipts change as the proposal moves through gates.
        payload = proposal.model_dump(
            mode="json",
            exclude={
                "state",
                "effective_session_id",
                "mid_session_apply_allowed",
                "human_approval",
                "anchor",
            },
        )
        return self._sha256(payload)

    def _validate_anchor_for_promotion(
        self,
        proposal: StrategyChangeProposal,
    ) -> None:
        if proposal.human_approval is None:
            raise ValueError("Promotion requires human approval receipt")
        if proposal.anchor is None:
            raise ValueError("Promotion requires anchor receipt")
        payload_hash = self.payload_hash(proposal)
        if proposal.human_approval.signed_payload_hash != payload_hash:
            raise ValueError("Human approval payload hash does not match proposal")
        if proposal.anchor.payload_hash != payload_hash:
            raise ValueError("Anchor payload hash does not match proposal")
        if not self.verify_anchor_log():
            raise ValueError("Anchor log does not verify")
        if not self._anchor_record_exists(proposal):
            raise ValueError("Anchored record not found in anchor log")

    def _last_anchor_hash(self) -> Optional[str]:
        if not self.anchor_path.exists():
            return None
        lines = [
            line.strip()
            for line in self.anchor_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not lines:
            return None
        try:
            return json.loads(lines[-1]).get("record_hash")
        except json.JSONDecodeError:
            return None

    def _anchor_record_exists(self, proposal: StrategyChangeProposal) -> bool:
        if not self.anchor_path.exists() or proposal.anchor is None:
            return False
        for line in self.anchor_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return False
            if (
                record.get("change_id") == proposal.change_id
                and record.get("payload_hash") == proposal.anchor.payload_hash
                and record.get("record_hash") == proposal.anchor.record_hash
            ):
                return True
        return False

    @staticmethod
    def _summary(result: Any) -> Dict[str, Any]:
        if result is None:
            return {"error": "missing backtest result"}
        if isinstance(result, dict):
            return result
        if hasattr(result, "summary"):
            return result.summary()
        return dict(result)

    @classmethod
    def _metrics_pass(cls, metrics: Dict[str, Any], thresholds: Dict[str, Any]) -> bool:
        if metrics.get("error"):
            return False
        if metrics.get("total_trades", 0) < thresholds.get("min_trades", 0):
            return False
        if metrics.get("max_drawdown_pct", 0) > thresholds.get("max_drawdown_pct", 100):
            return False
        if metrics.get("profit_factor", 0) < thresholds.get("min_profit_factor", 0):
            return False
        return True

    @staticmethod
    def _sha256(payload: Dict[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
