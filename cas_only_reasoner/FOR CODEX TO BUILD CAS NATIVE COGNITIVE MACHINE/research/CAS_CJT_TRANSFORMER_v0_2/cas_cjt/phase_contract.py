"""Required evidence fields for each of the eleven CJT tick phases."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .types import MANDATORY_TICK_ORDER, PhaseRecord, TickPhase


class PhaseContractError(ValueError):
    """A phase record is ordered correctly but lacks required evidence."""


REQUIRED_PHASE_FIELDS: Mapping[TickPhase, Mapping[str, tuple[str, ...]]] = {
    TickPhase.READ: {
        "inputs": ("cause_id", "state_digest", "model_digest"),
        "outputs": ("bias_ids", "bias_digests", "memory_read_refs"),
        "diagnostics": (),
    },
    TickPhase.CANDIDATE: {
        "inputs": ("candidate_operation_ids",),
        "outputs": ("candidate_cjt_ids", "operation_contract_ids"),
        "diagnostics": (),
    },
    TickPhase.READINESS: {
        "inputs": ("profile_ids",),
        "outputs": ("desire", "wisdom", "power", "hard_open"),
        "diagnostics": (),
    },
    TickPhase.ROUTE: {
        "inputs": (
            "control_cjt_id",
            "topology_mask",
            "permission_mask",
            "quarantine_mask",
            "budget_mask",
            "readiness_hard_mask",
            "route_settings",
            "native_compute",
            "compute_policy",
            "control_binding_manifest",
        ),
        "outputs": (
            "compute_plan",
            "effective_path_mask",
            "conducting_query_mask",
            "current_microunits",
            "total_current_microunits",
            "flow_allocation_ppm",
        ),
        "diagnostics": (),
    },
    TickPhase.EXECUTE: {
        "inputs": ("scheduled_cjt_ids", "operation_ids"),
        "outputs": ("executed_cjt_ids", "compute_units_used"),
        "diagnostics": (),
    },
    TickPhase.OBSERVE: {
        "inputs": ("executed_cjt_ids",),
        "outputs": (
            "candidate_effect_ids",
            "operating_regions",
            "artifact_ids",
            "compute_observations",
        ),
        "diagnostics": (
            "control_binding_digest",
            "declared_beta_microunits",
            "live_beta_by_head_microunits",
        ),
    },
    TickPhase.VERIFY: {
        "inputs": ("candidate_effect_ids", "evidence_ids"),
        "outputs": ("verifier_receipt_ids", "semantic_outcomes", "dispositions"),
        "diagnostics": (),
    },
    TickPhase.DIAGNOSE: {
        "inputs": ("operating_regions", "semantic_outcomes"),
        "outputs": ("reason_codes", "repair_required"),
        "diagnostics": (),
    },
    TickPhase.EMIT: {
        "inputs": ("verifier_receipt_ids",),
        "outputs": (
            "state_intent_ids",
            "model_intent_ids",
            "memory_intent_ids",
            "repair_ids",
            "repair_outcome_ids",
            "publication_requested",
        ),
        "diagnostics": (),
    },
    TickPhase.COMMIT: {
        "inputs": ("pre_state_digest", "pre_model_digest"),
        "outputs": ("proposed_post_state_digest", "proposed_post_model_digest"),
        "diagnostics": (),
    },
    TickPhase.TRACE: {
        "inputs": ("previous_trace_digest",),
        "outputs": ("seal_requested", "phase_count"),
        "diagnostics": (),
    },
}


def validate_phase_contract(
    records: Sequence[PhaseRecord],
    *,
    cause_id: str | None = None,
    pre_state_digest: str | None = None,
    pre_model_digest: str | None = None,
) -> None:
    """Reject ordered-but-empty or cross-bound phase records."""

    phases = tuple(record.phase for record in records)
    if phases != MANDATORY_TICK_ORDER:
        raise PhaseContractError("phase records do not follow the mandatory order")
    if len({record.tick for record in records}) != 1:
        raise PhaseContractError("phase records do not share one logical tick")
    for record in records:
        contract = REQUIRED_PHASE_FIELDS[record.phase]
        for section, keys in contract.items():
            value = getattr(record, section)
            missing = [key for key in keys if key not in value]
            extra = [key for key in value if key not in keys]
            if missing or extra:
                raise PhaseContractError(
                    f"{record.phase.value}.{section} keys are not exact; "
                    f"missing={','.join(missing)} extra={','.join(extra)}"
                )
    by_phase = {record.phase: record for record in records}
    read = by_phase[TickPhase.READ]
    commit = by_phase[TickPhase.COMMIT]
    if cause_id is not None and read.inputs["cause_id"] != cause_id:
        raise PhaseContractError("READ Cause does not bind the batch Cause")
    if pre_state_digest is not None and (
        read.inputs["state_digest"] != pre_state_digest
        or commit.inputs["pre_state_digest"] != pre_state_digest
    ):
        raise PhaseContractError("READ/COMMIT do not bind the durable state head")
    if pre_model_digest is not None and (
        read.inputs["model_digest"] != pre_model_digest
        or commit.inputs["pre_model_digest"] != pre_model_digest
    ):
        raise PhaseContractError("READ/COMMIT do not bind the durable model head")
    if by_phase[TickPhase.TRACE].outputs["phase_count"] != len(MANDATORY_TICK_ORDER):
        raise PhaseContractError("TRACE phase_count is incorrect")
    if by_phase[TickPhase.TRACE].outputs["seal_requested"] is not True:
        raise PhaseContractError("TRACE must request a seal")
    for record in records:
        expected_compute = (
            record.outputs["compute_units_used"]
            if record.phase is TickPhase.EXECUTE
            else 0
        )
        if record.compute_units != expected_compute:
            raise PhaseContractError(
                f"{record.phase.value}.compute_units is not exact"
            )


__all__ = [
    "PhaseContractError",
    "REQUIRED_PHASE_FIELDS",
    "validate_phase_contract",
]
