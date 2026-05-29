"""Evidence-gated CAS Harness verdict runner.

This is the first M3 production contract: it can refuse unsafe ACCEPTs from
incomplete evidence, and it can pass through an explicit verifier decision.
It does not infer ACCEPT/SUPPRESS from labels, packet existence, or UI state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping


Verdict = Literal["ACCEPT", "SUPPRESS", "FLAG_FOR_HUMAN_REVIEW"]
AuditStatus = Literal["SCAFFOLD_PENDING_RUNNER", "COMPLETE", "FAILED"]
ProofChipStatus = Literal["verified", "present", "missing", "failed", "unavailable"]

REQUIRED_PROOF_CHIPS: tuple[str, ...] = (
    "model_proof",
    "cas_readout",
    "causal_proof",
    "control_proof",
    "output_proof",
    "packet_proof",
)
PASSING_PROOF_STATUSES = {"verified", "present"}
WORM_PACKET_DETAIL_TERMS = ("worm retained", "object lock", "retention is active")


@dataclass(frozen=True)
class VerdictRunnerResult:
    status: AuditStatus
    verdict: Verdict | None
    confidence: float | None
    message: str
    missing_or_unavailable: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "message": self.message,
            "missing_or_unavailable": list(self.missing_or_unavailable),
            "failed": list(self.failed),
        }


def run_evidence_gated_verdict(
    *,
    evidence_packet_trace_id: str | None,
    proof_chips: list[Mapping[str, Any]],
    explicit_verifier_decision: Mapping[str, Any] | None = None,
) -> VerdictRunnerResult:
    """Return a verdict only when the evidence contract permits it.

    Rules:
    - No Evidence Packet means the real runner has not run.
    - Failed proof chips force human review.
    - Missing/unavailable proof chips force human review.
    - Complete proof chips are still not enough for ACCEPT/SUPPRESS unless an
      explicit verifier decision is attached.
    """

    if not evidence_packet_trace_id:
        return VerdictRunnerResult(
            status="SCAFFOLD_PENDING_RUNNER",
            verdict=None,
            confidence=None,
            message=(
                "M3 verdict runner did not execute: no Evidence Packet is attached, "
                "so no verdict or confidence was computed."
            ),
        )

    by_id = _chips_by_id(proof_chips)
    failed = tuple(
        chip_id
        for chip_id in REQUIRED_PROOF_CHIPS
        if _chip_status(by_id.get(chip_id)) == "failed"
    )
    if failed:
        return VerdictRunnerResult(
            status="COMPLETE",
            verdict="FLAG_FOR_HUMAN_REVIEW",
            confidence=None,
            failed=failed,
            message=(
                "M3 verdict runner flagged this audit for human review because "
                f"required proof chips failed: {', '.join(failed)}."
            ),
        )

    missing_or_unavailable = tuple(
        chip_id
        for chip_id in REQUIRED_PROOF_CHIPS
        if _chip_is_missing_or_unavailable(chip_id, by_id.get(chip_id))
    )
    if missing_or_unavailable:
        return VerdictRunnerResult(
            status="COMPLETE",
            verdict="FLAG_FOR_HUMAN_REVIEW",
            confidence=None,
            missing_or_unavailable=missing_or_unavailable,
            message=(
                "M3 verdict runner flagged this audit for human review because "
                "the Evidence Packet is missing required proof: "
                f"{', '.join(missing_or_unavailable)}."
            ),
        )

    decision = _parse_explicit_decision(explicit_verifier_decision)
    if decision is None:
        return VerdictRunnerResult(
            status="COMPLETE",
            verdict="FLAG_FOR_HUMAN_REVIEW",
            confidence=None,
            message=(
                "M3 evidence gate passed the required proof-chip check, but no "
                "explicit Stage 19/20/21 verifier decision is attached. The runner "
                "therefore flags for human review instead of inventing ACCEPT."
            ),
        )

    verdict, confidence = decision
    if verdict in {"ACCEPT", "SUPPRESS"} and not packet_proof_is_worm_retained(proof_chips):
        return VerdictRunnerResult(
            status="COMPLETE",
            verdict="FLAG_FOR_HUMAN_REVIEW",
            confidence=None,
            missing_or_unavailable=("packet_proof",),
            message=(
                "M3 verdict runner blocked the explicit verifier decision because "
                "final ACCEPT/SUPPRESS requires a WORM-retained Evidence Packet. "
                "Packet proof must be S3 re-read verified with active Object Lock retention."
            ),
        )
    return VerdictRunnerResult(
        status="COMPLETE",
        verdict=verdict,
        confidence=confidence,
        message=(
            "M3 verdict runner returned the explicit verifier decision from the "
            "attached evidence contract."
        ),
    )


def packet_proof_is_worm_retained(proof_chips: list[Mapping[str, Any]]) -> bool:
    chip = _chips_by_id(proof_chips).get("packet_proof")
    if _chip_status(chip) != "verified":
        return False
    detail = chip.get("detail") if isinstance(chip, Mapping) else None
    if not isinstance(detail, str):
        return False
    lowered = detail.lower()
    return all(term in lowered for term in WORM_PACKET_DETAIL_TERMS)


def _chips_by_id(proof_chips: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    by_id: dict[str, Mapping[str, Any]] = {}
    for chip in proof_chips:
        chip_id = chip.get("id")
        status = chip.get("status")
        if isinstance(chip_id, str) and status in {
            "verified",
            "present",
            "missing",
            "failed",
            "unavailable",
        }:
            by_id[chip_id] = chip
    return by_id


def _chip_status(chip: Mapping[str, Any] | None) -> ProofChipStatus | None:
    status = chip.get("status") if isinstance(chip, Mapping) else None
    if status in {"verified", "present", "missing", "failed", "unavailable"}:
        return status
    return None


def _chip_is_missing_or_unavailable(
    chip_id: str,
    chip: Mapping[str, Any] | None,
) -> bool:
    return _chip_status(chip) not in PASSING_PROOF_STATUSES


def _parse_explicit_decision(
    explicit_verifier_decision: Mapping[str, Any] | None,
) -> tuple[Verdict, float] | None:
    if explicit_verifier_decision is None:
        return None

    verdict = explicit_verifier_decision.get("verdict")
    confidence = explicit_verifier_decision.get("confidence")
    if verdict not in {"ACCEPT", "SUPPRESS", "FLAG_FOR_HUMAN_REVIEW"}:
        return None
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        return None
    confidence_float = float(confidence)
    if not 0.0 <= confidence_float <= 1.0:
        return None
    return verdict, confidence_float
