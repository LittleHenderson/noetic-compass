"""Bounded next-tick prerequisite and repair mechanics."""

from __future__ import annotations

from dataclasses import replace
from typing import Mapping, Sequence

from .contracts import canonical_digest, verify_declared_digest
from .state import ZERO_DIGEST, content_id, make_cause
from .types import (
    BiasState,
    CandidateEffect,
    CauseKind,
    CausePacket,
    ReadinessAxisName,
    RepairFrame,
    RepairOutcome,
    RepairStatus,
    SemanticOutcome,
    VerifierDisposition,
    VerifierReceipt,
)


class RepairError(ValueError):
    """A repair request violated timing, depth, branch, cycle, or budget law."""


class RepairDepthExhausted(RepairError):
    pass


class RepairBranchExhausted(RepairError):
    pass


class RepairBudgetExhausted(RepairError):
    pass


class RepairCycleDetected(RepairError):
    pass


def _seal_frame(frame: RepairFrame) -> RepairFrame:
    return replace(
        frame,
        frame_digest=canonical_digest(frame.to_dict(), omit_keys=("frame_digest",)),
    )


def open_repair(
    *,
    cause: CausePacket,
    candidate: CandidateEffect,
    receipt: VerifierReceipt,
    bias: BiasState,
    prerequisite_axis: ReadinessAxisName | None = None,
    parent_depth: int = 0,
    branch_count: int = 1,
    max_depth: int = 3,
    max_branches: int = 2,
    budget_units: int = 4,
    consumed_units: int = 1,
    active_cycle_keys: Sequence[str] = (),
) -> tuple[RepairFrame, CausePacket]:
    """Open a suspended parent and a typed subgoal that starts at ``t+1``."""

    if receipt.disposition is not VerifierDisposition.REPAIR or not receipt.repair_required:
        raise RepairError("only an independent REPAIR receipt can open a repair frame")
    if (
        receipt.cause_id != cause.cause_id
        or receipt.candidate_effect_id != candidate.candidate_effect_id
        or receipt.candidate_effect_digest != candidate.candidate_digest
        or receipt.bias_id != bias.bias_id
        or receipt.bias_version != bias.version
        or receipt.bias_digest != bias.state_digest
    ):
        raise RepairError("repair receipt does not bind the suspended transition")
    depth = parent_depth + 1
    if depth > max_depth:
        raise RepairDepthExhausted("REPAIR_DEPTH_EXHAUSTED")
    if branch_count > max_branches:
        raise RepairBranchExhausted("REPAIR_BRANCH_EXHAUSTED")
    if consumed_units > budget_units:
        raise RepairBudgetExhausted("REPAIR_BUDGET_EXHAUSTED")
    axis = prerequisite_axis or bias.rpm.readiness.first_unmet or ReadinessAxisName.WISDOM
    cycle_key = canonical_digest(
        {
            "parent_cause_id": cause.cause_id,
            "producer_cjt_id": candidate.producer_cjt_id,
            "operation_id": candidate.operation_id,
            "axis": axis.value,
        }
    )
    if cycle_key in set(active_cycle_keys):
        raise RepairCycleDetected("REPAIR_CYCLE")
    opened_tick = cause.tick
    subgoal_identity = {
        "parent_cause_id": cause.cause_id,
        "candidate_effect_id": candidate.candidate_effect_id,
        "receipt_id": receipt.receipt_id,
        "axis": axis.value,
        "eligible_tick": opened_tick + 1,
        "cycle_key": cycle_key,
    }
    repair_id = content_id("repair", subgoal_identity)
    subgoal = make_cause(
        tick=opened_tick + 1,
        cause_kind=CauseKind.RPM_SUBGOAL,
        content={
            "repair_id": repair_id,
            "blocked_axis": axis.value,
            "parent_cause_id": cause.cause_id,
            "rejected_candidate_effect_id": candidate.candidate_effect_id,
            "reason_codes": list(receipt.reason_codes),
        },
        goal_context={
            "kind": "PREREQUISITE_REPAIR",
            "return_address": f"cjt:{bias.cjt_id}:cause:{cause.cause_id}",
        },
        source="prototype:rpm-controller",
        provenance=(
            f"verifier-receipt:{receipt.receipt_id}",
            f"suspended-bias:{bias.state_digest}",
        ),
        candidate_operation_ids=("^6",),
        originating_cjt_id=candidate.producer_cjt_id,
        content_ref=candidate.content_ref,
    )
    frame = RepairFrame(
        repair_id=repair_id,
        opened_tick=opened_tick,
        eligible_tick=opened_tick + 1,
        parent_cause_id=cause.cause_id,
        rejected_candidate_effect_id=candidate.candidate_effect_id,
        verifier_receipt_id=receipt.receipt_id,
        suspended_bias_id=bias.bias_id,
        suspended_bias_version=bias.version,
        prerequisite_axis=axis,
        subgoal_cause_id=subgoal.cause_id,
        return_address=f"cjt:{bias.cjt_id}:cause:{cause.cause_id}",
        depth=depth,
        max_depth=max_depth,
        branch_count=branch_count,
        max_branches=max_branches,
        budget_units=budget_units,
        consumed_units=consumed_units,
        cycle_key=cycle_key,
        status=RepairStatus.OPEN,
        result_effect_id=None,
        frame_digest=ZERO_DIGEST,
    )
    return _seal_frame(frame), subgoal


def repair_frame_from_dict(value: Mapping[str, object]) -> RepairFrame:
    """Rebuild a persisted frame and verify its declared digest."""

    frame = RepairFrame(
        repair_id=str(value["repair_id"]),
        opened_tick=int(value["opened_tick"]),
        eligible_tick=int(value["eligible_tick"]),
        parent_cause_id=str(value["parent_cause_id"]),
        rejected_candidate_effect_id=str(value["rejected_candidate_effect_id"]),
        verifier_receipt_id=str(value["verifier_receipt_id"]),
        suspended_bias_id=str(value["suspended_bias_id"]),
        suspended_bias_version=int(value["suspended_bias_version"]),
        prerequisite_axis=str(value["prerequisite_axis"]),
        subgoal_cause_id=str(value["subgoal_cause_id"]),
        return_address=str(value["return_address"]),
        depth=int(value["depth"]),
        max_depth=int(value["max_depth"]),
        branch_count=int(value["branch_count"]),
        max_branches=int(value["max_branches"]),
        budget_units=int(value["budget_units"]),
        consumed_units=int(value["consumed_units"]),
        cycle_key=str(value["cycle_key"]),
        status=str(value["status"]),
        result_effect_id=(
            None if value.get("result_effect_id") is None else str(value["result_effect_id"])
        ),
        frame_digest=str(value["frame_digest"]),
    )
    if not verify_declared_digest(frame, "frame_digest"):
        raise RepairError("persisted RepairFrame digest mismatch")
    return frame


def make_repair_outcome(
    *,
    frame: RepairFrame,
    tick: int,
    result_effect: Mapping[str, object],
    resumed_cause: CausePacket,
    resumed_candidate: CandidateEffect,
    receipt: VerifierReceipt,
    target_bias: BiasState,
) -> RepairOutcome:
    """Seal proof that a retained repair Effect validly resumed its parent Bias."""

    if not verify_declared_digest(frame, "frame_digest"):
        raise RepairError("repair frame digest is invalid")
    if frame.status is not RepairStatus.OPEN:
        raise RepairError("only an immutable OPEN frame can receive a closure outcome")
    if tick != frame.eligible_tick + 1 or resumed_cause.tick != tick:
        raise RepairError("repair closure must resume on the tick after its repair Effect")
    if (
        frame.repair_id not in target_bias.rpm.open_repair_ids
        or frame.suspended_bias_id != target_bias.bias_id
        or target_bias.version <= frame.suspended_bias_version
    ):
        raise RepairError("repair closure target does not match the suspended Bias")
    result_effect_id = result_effect.get("published_effect_id")
    result_effect_digest = result_effect.get("publication_digest")
    result_commit_receipt_id = result_effect.get("commit_receipt_id")
    if (
        not isinstance(result_effect_id, str)
        or not result_effect_id
        or not isinstance(result_effect_digest, str)
        or not isinstance(result_commit_receipt_id, str)
        or not result_commit_receipt_id
        or not verify_declared_digest(result_effect, "publication_digest")
        or resumed_cause.parent_effect_id != result_effect_id
    ):
        raise RepairError("repair closure requires one retained committed Effect")
    if (
        resumed_candidate.tick != tick
        or resumed_candidate.parent_cause_id != resumed_cause.cause_id
        or receipt.tick != tick
        or receipt.cause_id != resumed_cause.cause_id
        or receipt.candidate_effect_id != resumed_candidate.candidate_effect_id
        or receipt.candidate_effect_digest != resumed_candidate.candidate_digest
        or receipt.bias_id != target_bias.bias_id
        or receipt.bias_version != target_bias.version
        or receipt.bias_digest != target_bias.state_digest
        or receipt.disposition is not VerifierDisposition.ACCEPT
        or receipt.semantic_outcome is not SemanticOutcome.INTENDED
        or receipt.repair_required
    ):
        raise RepairError("repair closure is not bound to an accepted resumed transition")
    identity = {
        "repair_id": frame.repair_id,
        "tick": tick,
        "frame_digest": frame.frame_digest,
        "result_effect_id": result_effect_id,
        "result_effect_digest": result_effect_digest,
        "result_effect_commit_receipt_id": result_commit_receipt_id,
        "resumed_cause_id": resumed_cause.cause_id,
        "resumed_candidate_effect_id": resumed_candidate.candidate_effect_id,
        "verifier_receipt_id": receipt.receipt_id,
        "target_bias_id": target_bias.bias_id,
        "target_bias_version": target_bias.version,
        "target_bias_digest": target_bias.state_digest,
    }
    draft = RepairOutcome(
        outcome_id=content_id("repair-outcome", identity),
        repair_id=frame.repair_id,
        tick=tick,
        status=RepairStatus.RETURNED,
        frame_digest=frame.frame_digest,
        result_effect_id=result_effect_id,
        result_effect_digest=result_effect_digest,
        result_effect_commit_receipt_id=result_commit_receipt_id,
        resumed_cause_id=resumed_cause.cause_id,
        resumed_candidate_effect_id=resumed_candidate.candidate_effect_id,
        verifier_receipt_id=receipt.receipt_id,
        target_bias_id=target_bias.bias_id,
        target_bias_version=target_bias.version,
        target_bias_digest=target_bias.state_digest,
        outcome_digest=ZERO_DIGEST,
    )
    return replace(
        draft,
        outcome_digest=canonical_digest(
            draft.to_dict(), omit_keys=("outcome_digest",)
        ),
    )


def repair_outcome_from_dict(value: Mapping[str, object]) -> RepairOutcome:
    """Rebuild a persisted closure outcome and verify its declared digest."""

    outcome = RepairOutcome(
        outcome_id=str(value["outcome_id"]),
        repair_id=str(value["repair_id"]),
        tick=int(value["tick"]),
        status=str(value["status"]),
        frame_digest=str(value["frame_digest"]),
        result_effect_id=str(value["result_effect_id"]),
        result_effect_digest=str(value["result_effect_digest"]),
        result_effect_commit_receipt_id=str(
            value["result_effect_commit_receipt_id"]
        ),
        resumed_cause_id=str(value["resumed_cause_id"]),
        resumed_candidate_effect_id=str(value["resumed_candidate_effect_id"]),
        verifier_receipt_id=str(value["verifier_receipt_id"]),
        target_bias_id=str(value["target_bias_id"]),
        target_bias_version=int(value["target_bias_version"]),
        target_bias_digest=str(value["target_bias_digest"]),
        outcome_digest=str(value["outcome_digest"]),
    )
    if not verify_declared_digest(outcome, "outcome_digest"):
        raise RepairError("persisted RepairOutcome digest mismatch")
    identity = {
        "repair_id": outcome.repair_id,
        "tick": outcome.tick,
        "frame_digest": outcome.frame_digest,
        "result_effect_id": outcome.result_effect_id,
        "result_effect_digest": outcome.result_effect_digest,
        "result_effect_commit_receipt_id": outcome.result_effect_commit_receipt_id,
        "resumed_cause_id": outcome.resumed_cause_id,
        "resumed_candidate_effect_id": outcome.resumed_candidate_effect_id,
        "verifier_receipt_id": outcome.verifier_receipt_id,
        "target_bias_id": outcome.target_bias_id,
        "target_bias_version": outcome.target_bias_version,
        "target_bias_digest": outcome.target_bias_digest,
    }
    if outcome.outcome_id != content_id("repair-outcome", identity):
        raise RepairError("persisted RepairOutcome identity mismatch")
    return outcome


__all__ = [
    "RepairBranchExhausted",
    "RepairBudgetExhausted",
    "RepairCycleDetected",
    "RepairDepthExhausted",
    "RepairError",
    "make_repair_outcome",
    "open_repair",
    "repair_frame_from_dict",
    "repair_outcome_from_dict",
]
