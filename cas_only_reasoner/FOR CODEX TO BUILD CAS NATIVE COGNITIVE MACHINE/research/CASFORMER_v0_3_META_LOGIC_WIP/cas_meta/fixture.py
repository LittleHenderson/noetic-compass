"""Fixed-weight, oracle-guided reference for the first composition experiment.

This adapts the frozen v0.2 acceptance example: its fifth learning tick becomes
an inference-only repair resumption. It makes no learning-equivalence claim.
"""

from __future__ import annotations

from pathlib import Path

import torch

from casformer import CASformerConfig
from cas_cjt import CJTNodeSpec, NeuralCJTRuntime, TopologyEdge
from cas_cjt.artifacts import StoredArtifact
from cas_cjt.control import MaterializedControl
from cas_cjt.runtime import InferenceTickResult
from cas_cjt.types import CausePacket


LABELS = ("L0", "L1", "L2", "L3")
NODE_SPECS = tuple(CJTNodeSpec(name, "^6") for name in ("A", "B", "C", "R"))
TOPOLOGY = (
    TopologyEdge("A", "B"),
    TopologyEdge("B", "C"),
    TopologyEdge("C", "R"),
    TopologyEdge("R", "C"),
)
GOAL_CONTEXT = {"goal": "verified four-CJT chain"}


def _config() -> CASformerConfig:
    return CASformerConfig(
        d_model=4,
        num_heads=2,
        num_relations=4,
        num_layers=1,
        dropout=0.0,
        attention_dropout=0.0,
        initial_cutoff=0.01,
        initial_saturation=100.0,
    )


def create_native(path: str | Path) -> NeuralCJTRuntime:
    """Create the original four-node fixture with reproducible initial weights."""
    return NeuralCJTRuntime.create(
        path,
        config=_config(),
        node_specs=NODE_SPECS,
        topology=TOPOLOGY,
        seed=7,
        labels=LABELS,
    )


def open_native(path: str | Path) -> NeuralCJTRuntime:
    """Reopen only the same configuration, topology, labels, and stored weights."""
    return NeuralCJTRuntime.open(
        path,
        config=_config(),
        node_specs=NODE_SPECS,
        topology=TOPOLOGY,
        labels=LABELS,
    )


def initial_input(runtime: NeuralCJTRuntime) -> tuple[CausePacket, StoredArtifact]:
    """Build the visible fixture input; this does not commit a native tick."""
    return runtime.make_input_cause(
        torch.tensor([[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]]),
        tick=runtime.store.next_tick(),
        content={"task": "complete reasoning transistor"},
        goal_context=GOAL_CONTEXT,
    )


def plan_charge(materialized: MaterializedControl) -> dict[str, int]:
    """Return separate summed policy ceilings, not measured neural FLOPs."""
    plan = materialized.routing.compute_plan
    plan.validate()
    return {name: int(value.sum().item()) for name, value in plan.integer_fields}


def run_reference(runtime: NeuralCJTRuntime) -> list[InferenceTickResult]:
    """Run A, B, rejected C, R, and resumed C through public native APIs.

    The caller owns the runtime and closes it. Earlier accepted native steps
    remain durable if a later step fails. No model-learning API is called.
    """
    original_model_digest = runtime.state.model_digest
    cause, artifact = initial_input(runtime)
    a = runtime.inference_tick(
        cause=cause,
        cjt_id="A",
        expected_symbol="L1",
        supplied_artifacts=(artifact,),
    )
    cause = runtime.cause_from_effect(
        a.commit_receipt.published_effect_ids[0],
        tick=runtime.store.next_tick(),
        candidate_operation_ids=("^6",),
        goal_context=GOAL_CONTEXT,
    )
    b = runtime.inference_tick(cause=cause, cjt_id="B", expected_symbol="L3")
    cause = runtime.cause_from_effect(
        b.commit_receipt.published_effect_ids[0],
        tick=runtime.store.next_tick(),
        candidate_operation_ids=("^6",),
        goal_context=GOAL_CONTEXT,
    )
    rejected = runtime.inference_tick(
        cause=cause,
        cjt_id="C",
        expected_symbol="L0",
        opposite_symbol="L2",
    )
    if rejected.repair_subgoal is None or rejected.repair_frame is None:
        raise AssertionError("fixed reference did not open its expected repair")
    repair = runtime.inference_tick(
        cause=rejected.repair_subgoal,
        cjt_id="R",
        expected_symbol="L1",
    )
    resumed_cause = runtime.cause_from_effect(
        repair.commit_receipt.published_effect_ids[0],
        tick=runtime.store.next_tick(),
        candidate_operation_ids=("^6",),
        goal_context=GOAL_CONTEXT,
    )
    resumed = runtime.inference_tick(
        cause=resumed_cause,
        cjt_id="C",
        expected_symbol="L2",
        resume_repair_id=rejected.repair_frame.repair_id,
    )
    if resumed.repair_outcome is None:
        raise AssertionError("fixed reference did not close its original repair")
    if runtime.state.model_digest != original_model_digest:
        raise AssertionError("fixed reference unexpectedly changed neural weights")
    return [a, b, rejected, repair, resumed]
