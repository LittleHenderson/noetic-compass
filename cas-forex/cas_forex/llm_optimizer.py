"""Guarded LLM optimizer contracts for CAS FOREX.

The optimizer may suggest experiments, but CAS Harness/PCBA boundaries keep the
suggestions in a research queue. It cannot authorize deposits, withdrawals,
broker execution, or profit claims.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from cas_forex.pcba_prompt_injection import (
    evaluate_pcba_prompt_injection,
    extract_prompt_injection_surfaces,
)
from cas_forex.strategy_ledger import LEDGER_PATH, load_strategy_lead_ledger


CLAIM_BOUNDARY = "Research proposal only. Live trading remains NOT LICENSED."


class OptimizerVerdict(str, Enum):
    RESEARCH_QUEUE = "RESEARCH_QUEUE"
    FLAG_FOR_HUMAN_REVIEW = "FLAG_FOR_HUMAN_REVIEW"
    REJECT = "REJECT"


@dataclass
class OptimizerProposal:
    proposal_id: str
    model_id: str
    lead_id: str
    objective: str
    proposed_changes: Dict[str, Any]
    evidence_refs: List[str]
    simulator_requests: List[Dict[str, Any]] = field(default_factory=list)
    condition_contexts: List[str] = field(default_factory=list)
    risk_notes: List[str] = field(default_factory=list)
    claim_boundary: str = CLAIM_BOUNDARY


@dataclass
class OptimizerReview:
    verdict: OptimizerVerdict
    reasons: List[str]
    claim_ceiling: str
    can_create_broker_accept: bool = False
    can_unlock_live_trading: bool = False

    @property
    def passed_research_gate(self) -> bool:
        return self.verdict == OptimizerVerdict.RESEARCH_QUEUE


class CASPCBAOptimizerGuard:
    """Evidence and safety gate for LLM-generated optimization proposals."""

    def __init__(self, ledger_path: Path = LEDGER_PATH):
        self.ledger_path = ledger_path

    def review(self, proposal: OptimizerProposal) -> OptimizerReview:
        reject_reasons: List[str] = []
        review_reasons: List[str] = []
        normalized_text = _normalized_proposal_text(proposal)

        detected_injection, patterns = evaluate_pcba_prompt_injection(normalized_text)
        if detected_injection:
            reject_reasons.append(f"PCBA prompt-injection surface detected: {', '.join(patterns)}")

        forbidden = _matched_patterns(normalized_text, FORBIDDEN_LIVE_ACTION_PATTERNS)
        if forbidden:
            reject_reasons.append(f"Proposal tries to cross live/payment/broker authority: {', '.join(forbidden)}")

        promises = _matched_patterns(normalized_text, PROFIT_PROMISE_PATTERNS)
        if promises:
            reject_reasons.append(f"Proposal uses guaranteed-profit language: {', '.join(promises)}")

        if "NOT LICENSED" not in proposal.claim_boundary:
            review_reasons.append("Proposal does not preserve the NOT LICENSED claim boundary.")

        if not proposal.evidence_refs:
            review_reasons.append("Proposal has no evidence_refs; hallucination guard requires source evidence.")

        if not proposal.condition_contexts:
            review_reasons.append("Proposal has no condition_contexts; optimizer must cite tested conditions.")

        if not proposal.proposed_changes:
            review_reasons.append("Proposal contains no concrete proposed_changes.")

        lead_lookup = self._lead_lookup()
        lead = lead_lookup.get(proposal.lead_id)
        if lead is None:
            review_reasons.append(f"Unknown strategy lead_id {proposal.lead_id!r}; possible drift from ledger memory.")
        elif lead.get("status") != "ACTIVE_RESEARCH_LEAD":
            review_reasons.append(
                f"Strategy lead {proposal.lead_id!r} is {lead.get('status')}; human review required before reuse."
            )

        if reject_reasons:
            return OptimizerReview(
                verdict=OptimizerVerdict.REJECT,
                reasons=reject_reasons + review_reasons,
                claim_ceiling="NOT LICENSED",
            )
        if review_reasons:
            return OptimizerReview(
                verdict=OptimizerVerdict.FLAG_FOR_HUMAN_REVIEW,
                reasons=review_reasons,
                claim_ceiling="FLAG_FOR_HUMAN_REVIEW",
            )
        return OptimizerReview(
            verdict=OptimizerVerdict.RESEARCH_QUEUE,
            reasons=["Proposal is bounded to research optimization and tied to ledger/evidence/conditions."],
            claim_ceiling="OPEN",
        )

    def _lead_lookup(self) -> Dict[str, Mapping[str, Any]]:
        ledger = load_strategy_lead_ledger(self.ledger_path)
        return {str(lead["lead_id"]): lead for lead in ledger["leads"]}


FORBIDDEN_LIVE_ACTION_PATTERNS = (
    r"\blive[_ -]?mode\s*=\s*true\b",
    r"\b(can|should|will)\s+create\s+broker\s+accept\b",
    r"\bcreate\s+broker\s+accept\b",
    r"\bunlock\s+live\s+trading\b",
    r"\bplace\s+(a\s+)?(live\s+)?trade\b",
    r"\bexecute\s+(a\s+)?(live\s+)?(market|limit|broker)?\s*order\b",
    r"\bsend\s+(a\s+)?(market|limit|broker)\s+order\b",
    r"\bauto\s*deposit\b",
    r"\bwithdraw(al)?\b",
    r"\bdeposit\s+(winnings|profits|funds|money)\b",
    r"\btransfer\s+(winnings|profits|funds|money)\b",
    r"\bbank\s+account\b",
    r"\bdebit\s+card\b",
    r"\bcredit\s+card\b",
)

PROFIT_PROMISE_PATTERNS = (
    r"\bguarantee[sd]?\s+(profit|return|income|win|winning)\b",
    r"\brisk[- ]?free\s+(profit|return|income|trade)\b",
    r"\bsure\s+thing\b",
    r"\bwill\s+make\s+\$?\d",
    r"\bguaranteed\s+\$?\d",
)


def _normalized_proposal_text(proposal: OptimizerProposal) -> str:
    raw_text = " ".join(_flatten_text(proposal))
    surfaces = extract_prompt_injection_surfaces(raw_text)
    return " ".join(surfaces.values()).lower()


def _flatten_text(value: Any) -> Iterable[str]:
    if isinstance(value, OptimizerProposal):
        yield from _flatten_text(value.__dict__)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from _flatten_text(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _flatten_text(item)
    elif value is not None:
        yield str(value)


def _matched_patterns(text: str, patterns: Sequence[str]) -> List[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE)]
