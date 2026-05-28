"""Verifier decision gate for merged CAS Harness fleet packets.

The fleet executor proves that distributed worker receipts exist. This module
is the next gate: it may pass through an explicit packet-level verifier
decision, or it returns a conservative human-review decision when the merged
packet has receipts but no verifier proof chips. It never promotes fleet
completion into ACCEPT by itself.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from api.services.cas_harness_distributed_audits import get_distributed_audit
from api.services.cas_harness_fleet_executor import get_fleet_run
from api.services.cas_harness_verifier_decision_adapter import VerifierDecision


FleetVerifierProofChipGate = Literal["passed", "blocked", "unavailable"]


class FleetVerifierStateError(ValueError):
    """Raised when a fleet run is not ready for verifier review."""


@dataclass(frozen=True)
class FleetVerifierDecisionRecord:
    audit_id: str
    merged_packet_trace_id: str
    verdict: Literal["ACCEPT", "SUPPRESS", "FLAG_FOR_HUMAN_REVIEW"]
    confidence: float | None
    source: str
    reason: str
    decision_scope: str
    coverage: dict[str, Any]
    proof_chip_gate: FleetVerifierProofChipGate
    blockers: list[str]
    next_actions: list[str]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_merged_fleet_packet(
    audit_id: str,
    *,
    explicit_packet_decision: VerifierDecision | None = None,
    packet_load_error: str | None = None,
) -> FleetVerifierDecisionRecord | None:
    """Return the verifier-owned decision for a merged fleet packet.

    ``explicit_packet_decision`` must come from the Evidence Packet verifier
    adapter. When it is absent, a complete fleet merge still routes to
    ``FLAG_FOR_HUMAN_REVIEW`` with null confidence.
    """

    run = get_fleet_run(audit_id)
    if run is None:
        return None
    if not run.merged_packet_trace_id:
        raise FleetVerifierStateError("Merge fleet evidence before verifier review.")

    distributed = get_distributed_audit(audit_id)
    coverage = {
        "basis": "fleet_worker_fragments",
        "total_jobs": len(run.jobs),
        "completed_fragments": sum(1 for job in run.jobs if job.status == "completed"),
        "failed_jobs": sum(1 for job in run.jobs if job.status == "failed"),
        "missing_output_jobs": sum(1 for job in run.jobs if job.missing_outputs),
        "distributed_merge_status": distributed.merge_status if distributed else None,
    }

    if explicit_packet_decision is not None:
        return FleetVerifierDecisionRecord(
            audit_id=audit_id,
            merged_packet_trace_id=run.merged_packet_trace_id,
            verdict=explicit_packet_decision.verdict,
            confidence=explicit_packet_decision.confidence,
            source=explicit_packet_decision.source,
            reason=explicit_packet_decision.reason,
            decision_scope=explicit_packet_decision.decision_scope
            or "distributed_fleet_merged_packet",
            coverage=explicit_packet_decision.coverage or coverage,
            proof_chip_gate="passed",
            blockers=[],
            next_actions=[
                "Attach this verifier-owned decision to the merged Evidence Packet.",
                "Expose the Evidence Packet trace for reviewer drill-down.",
            ],
            created_at=_utc_now(),
        )

    blockers = [
        "Merged distributed packet has worker receipts but no explicit proof-chip verifier decision.",
    ]
    if packet_load_error:
        blockers.append(f"Evidence Packet verifier payload was not loadable: {packet_load_error}.")
    failed_jobs = sum(1 for job in run.jobs if job.status == "failed")
    if failed_jobs:
        blockers.append(f"{failed_jobs} fleet job(s) failed.")
    missing_jobs = [job.job_id for job in run.jobs if job.missing_outputs]
    if missing_jobs:
        blockers.append(f"{len(missing_jobs)} fleet job(s) reported missing outputs.")

    return FleetVerifierDecisionRecord(
        audit_id=audit_id,
        merged_packet_trace_id=run.merged_packet_trace_id,
        verdict="FLAG_FOR_HUMAN_REVIEW",
        confidence=None,
        source="fleet_packet_verifier",
        reason=(
            "Fleet receipts are merged, but ACCEPT/SUPPRESS requires an explicit "
            "verifier decision over the merged Evidence Packet."
        ),
        decision_scope="distributed_fleet_merged_packet",
        coverage=coverage,
        proof_chip_gate="unavailable" if not packet_load_error else "blocked",
        blockers=blockers,
        next_actions=[
            "Attach Stage 19/20/21 verifier output or packet-level explicit_verifier_decision.",
            "Keep the public verdict at FLAG FOR HUMAN REVIEW until proof chips pass.",
        ],
        created_at=_utc_now(),
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
