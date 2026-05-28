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
    decision_scope: str | None = None
    coverage: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


def verifier_decision_from_packet(packet: Mapping[str, Any]) -> VerifierDecision | None:
    """Return a public verdict from a locked Stage 21 packet, if explicit."""

    if packet.get("schema_version") == "cas_harness_stage9_40e_evidence_packet.v1":
        return _stage9_40e_decision(packet)

    if packet.get("schema_version") != "cas_harness_evidence_packet_v1":
        return None

    s7_decision = _s7_f28_balanced_bridge_decision(packet)
    if s7_decision is not None:
        return s7_decision

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


def _stage9_40e_decision(packet: Mapping[str, Any]) -> VerifierDecision | None:
    """Pass through a Stage 9 40E packet only when its own verifier is explicit.

    Stage 9 packets are validation artifacts. They may surface ACCEPT/SUPPRESS
    only after the packet merger has attached a verifier decision and all six
    proof chips are pass-ready.
    """

    verification = _mapping_or_empty(packet.get("verification"))
    decision = _mapping_or_empty(verification.get("explicit_verifier_decision"))
    verdict = decision.get("verdict")
    confidence = _confidence_or_none(decision.get("confidence"))
    if verdict not in {"ACCEPT", "SUPPRESS", "FLAG_FOR_HUMAN_REVIEW"}:
        return None
    if confidence is None:
        return None
    if not _stage9_proof_chips_pass_ready(verification.get("proof_chips")):
        return None
    if packet.get("verdict") != verdict:
        return None

    source = decision.get("source")
    reason = decision.get("reason")
    coverage = decision.get("coverage")
    return VerifierDecision(
        verdict=verdict,
        confidence=confidence,
        source=(
            source
            if isinstance(source, str) and source.strip()
            else "stage9_40e_verifier_decision"
        ),
        reason=(
            reason
            if isinstance(reason, str) and reason.strip()
            else (
                "Stage 9 40E packet has pass-ready proof chips and an explicit "
                "verifier decision."
            )
        ),
        decision_scope=_string_or_none(decision.get("decision_scope")),
        coverage=dict(coverage) if isinstance(coverage, Mapping) else None,
    )


def _stage9_proof_chips_pass_ready(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    required = {
        "model_proof",
        "cas_readout",
        "causal_proof",
        "control_proof",
        "output_proof",
        "packet_proof",
    }
    strict_verified = {
        "cas_readout",
        "causal_proof",
        "control_proof",
        "output_proof",
    }
    by_id: dict[str, str] = {}
    for row in value:
        if not isinstance(row, Mapping):
            continue
        chip_id = row.get("id")
        status = row.get("status")
        if isinstance(chip_id, str) and isinstance(status, str):
            by_id[chip_id] = status
    if not required.issubset(by_id):
        return False
    if any(by_id[chip_id] not in {"verified", "present"} for chip_id in required):
        return False
    return all(by_id[chip_id] == "verified" for chip_id in strict_verified)


def _s7_f28_balanced_bridge_decision(packet: Mapping[str, Any]) -> VerifierDecision | None:
    """Pass through the S7-F28 packet's conservative human-review decision.

    This method packet is a large-model validation artifact, not a Stage 21
    production row. It is allowed to return only FLAG_FOR_HUMAN_REVIEW. The
    adapter must never upgrade an S7 packet to ACCEPT/SUPPRESS.
    """

    provenance = _mapping_or_empty(packet.get("provenance"))
    if provenance.get("method_label") != "S7-F28-BALANCED-BRIDGE":
        return None

    verification = _mapping_or_empty(packet.get("verification"))
    decision = _mapping_or_empty(verification.get("explicit_verifier_decision"))
    if decision.get("verdict") != "FLAG_FOR_HUMAN_REVIEW":
        return None
    confidence = _confidence_or_none(decision.get("confidence"))
    if confidence is None:
        return None

    proof_chips = verification.get("proof_chips")
    if not _proof_chips_pass_ready(proof_chips):
        return None

    source = decision.get("source")
    reason = decision.get("reason")
    return VerifierDecision(
        verdict="FLAG_FOR_HUMAN_REVIEW",
        confidence=confidence,
        source=source if isinstance(source, str) and source.strip() else "S7-F28-BALANCED-BRIDGE",
        reason=(
            reason
            if isinstance(reason, str) and reason.strip()
            else (
                "S7-F28 packet assembled all evidence layers, but production "
                "ACCEPT/SUPPRESS requires the Stage 19/20/21 verifier."
            )
        ),
    )


def _proof_chips_pass_ready(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    required = {
        "model_proof",
        "cas_readout",
        "causal_proof",
        "control_proof",
        "output_proof",
        "packet_proof",
    }
    by_id: dict[str, str] = {}
    for row in value:
        if not isinstance(row, Mapping):
            continue
        chip_id = row.get("id")
        status = row.get("status")
        if isinstance(chip_id, str) and isinstance(status, str):
            by_id[chip_id] = status
    return required.issubset(by_id) and all(
        by_id[chip_id] in {"verified", "present"} for chip_id in required
    )


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


def _string_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
