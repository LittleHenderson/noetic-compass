"""Adapt Stage 19/20/21 CAS verifier packet fields into public verdicts.

This adapter is intentionally narrow. It only returns a decision when an
Evidence Packet carries the locked Stage 21 product schema plus the Stage 19
Verification Stack and Stage 20 Generation Readiness fields. Otherwise it
returns ``None`` so the M3 verdict runner cannot fabricate ACCEPT/SUPPRESS.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping


Verdict = Literal["ACCEPT", "SUPPRESS", "FLAG_FOR_HUMAN_REVIEW"]


@dataclass(frozen=True)
class VerifierDecision:
    verdict: Verdict
    confidence: float
    source: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verifier_decision_from_packet(packet: Mapping[str, Any]) -> VerifierDecision | None:
    """Return a public verdict from a locked Stage 21 packet, if explicit."""

    if packet.get("schema_version") != "cas_harness_evidence_packet_v1":
        return None

    if not _has_stage19_and_stage20_sources(packet):
        return None

    verification = _mapping_or_empty(packet.get("verification"))
    readiness = _mapping_or_empty(packet.get("generation_readiness"))
    action = readiness.get("generation_readiness")
    accepted = verification.get("accepted")
    if not isinstance(action, str) or not isinstance(accepted, bool):
        return None

    if action == "allow" and accepted is True:
        confidence = _accepted_accuracy(verification)
        if confidence is None:
            return None
        return VerifierDecision(
            verdict="ACCEPT",
            confidence=confidence,
            source="stage19_verification_stack+stage20_generation_readiness",
            reason="Stage 19 accepted the row and Stage 20 readiness action is allow.",
        )

    if action == "suppress" and accepted is False:
        confidence = _risk_score(readiness)
        if confidence is None:
            return None
        return VerifierDecision(
            verdict="SUPPRESS",
            confidence=confidence,
            source="stage19_verification_stack+stage20_generation_readiness",
            reason="Stage 19 rejected the row and Stage 20 readiness action is suppress.",
        )

    if action in {"caveat", "constrain"}:
        confidence = _risk_score(readiness) if accepted is False else _accepted_accuracy(verification)
        if confidence is None:
            return None
        return VerifierDecision(
            verdict="FLAG_FOR_HUMAN_REVIEW",
            confidence=confidence,
            source="stage19_verification_stack+stage20_generation_readiness",
            reason=f"Stage 20 readiness action is {action}, so the public verdict is human review.",
        )

    return None


def _has_stage19_and_stage20_sources(packet: Mapping[str, Any]) -> bool:
    provenance = _mapping_or_empty(packet.get("provenance"))
    reports = provenance.get("source_reports")
    if not isinstance(reports, list):
        return False
    names = [report for report in reports if isinstance(report, str)]
    has_stage19 = any("stage19" in name.lower() for name in names)
    has_stage20 = any("stage20" in name.lower() for name in names)
    return has_stage19 and has_stage20


def _accepted_accuracy(verification: Mapping[str, Any]) -> float | None:
    profile = _mapping_or_empty(verification.get("mode_profile"))
    value = profile.get("accepted_accuracy")
    return _confidence_or_none(value)


def _risk_score(readiness: Mapping[str, Any]) -> float | None:
    value = readiness.get("risk_score")
    return _confidence_or_none(value)


def _confidence_or_none(value: Any) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    out = float(value)
    if not 0.0 <= out <= 1.0:
        return None
    return out


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
