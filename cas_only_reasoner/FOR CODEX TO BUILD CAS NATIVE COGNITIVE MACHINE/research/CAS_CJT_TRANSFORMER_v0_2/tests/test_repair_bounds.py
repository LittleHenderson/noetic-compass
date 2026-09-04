from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import pytest
import torch


CASFORMER_ROOT = Path(__file__).resolve().parents[2] / "CASFORMER_v0_1"
sys.path.insert(0, str(CASFORMER_ROOT))

from casformer import CASformerConfig

from cas_cjt.contracts import ContractSchemaError, canonical_digest, validate_contract
from cas_cjt.network import CJTNodeSpec, TopologyEdge
from cas_cjt.repair import (
    RepairBranchExhausted,
    RepairBudgetExhausted,
    RepairCycleDetected,
    RepairDepthExhausted,
    open_repair,
    repair_frame_from_dict,
)
from cas_cjt.runtime import NeuralCJTRuntime
from cas_cjt.types import ContractTypeError, RepairStatus, VerifierDisposition


def _fixture(tmp_path: Path):
    config = CASformerConfig(
        d_model=4,
        num_heads=2,
        num_relations=4,
        num_layers=1,
        initial_cutoff=0.01,
        initial_saturation=100.0,
    )
    runtime = NeuralCJTRuntime.create(
        tmp_path / "repair.db",
        config=config,
        node_specs=tuple(CJTNodeSpec(name, "^6") for name in ("A", "B", "C")),
        topology=(TopologyEdge("A", "B"), TopologyEdge("B", "A")),
        seed=7,
        labels=("L0", "L1", "L2", "L3"),
    )
    cause, artifact = runtime.make_input_cause(
        torch.tensor([[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]]),
        tick=1,
        content={"task": "repair bounds"},
        goal_context={"goal": "fail safely"},
    )
    prepared = runtime._prepare_inference(
        cause=cause,
        cjt_id="A",
        expected_symbol="L0",
        opposite_symbol="L1",
        settings=None,
        supplied_artifacts=(artifact,),
        resume_repair_id=None,
        write_memory=False,
    )
    assert prepared.verifier_receipt.disposition is VerifierDisposition.REPAIR
    return runtime, prepared, cause


def _open(prepared, cause, **changes):
    return open_repair(
        cause=cause,
        candidate=prepared.candidate_effect,
        receipt=prepared.verifier_receipt,
        bias=prepared.bias,
        **changes,
    )


def test_repair_has_exact_next_tick_and_sealed_return(tmp_path: Path) -> None:
    runtime, prepared, cause = _fixture(tmp_path)
    frame, subgoal = _open(prepared, cause)
    assert subgoal.tick == cause.tick + 1 == frame.eligible_tick
    assert subgoal.cause_id == frame.subgoal_cause_id
    assert frame.return_address in subgoal.goal_context["return_address"]
    assert repair_frame_from_dict(frame.to_dict()) == frame
    assert frame.status is RepairStatus.OPEN
    assert frame.result_effect_id is None
    with pytest.raises(ContractTypeError, match="immutable OPEN"):
        replace(frame, status=RepairStatus.ACTIVE)
    with pytest.raises(ContractTypeError, match="immutable OPEN"):
        replace(frame, result_effect_id="effect-forged")
    forged = frame.to_dict()
    forged["status"] = "ACTIVE"
    forged["frame_digest"] = canonical_digest(
        forged, omit_keys=("frame_digest",)
    )
    with pytest.raises(ContractSchemaError):
        validate_contract(forged)
    runtime.close()


@pytest.mark.parametrize(
    ("changes", "error"),
    (
        ({"parent_depth": 3, "max_depth": 3}, RepairDepthExhausted),
        ({"branch_count": 3, "max_branches": 2}, RepairBranchExhausted),
        ({"budget_units": 0, "consumed_units": 1}, RepairBudgetExhausted),
    ),
)
def test_repair_depth_branch_and_budget_limits_fail_closed(
    tmp_path: Path, changes: dict[str, int], error: type[Exception]
) -> None:
    runtime, prepared, cause = _fixture(tmp_path)
    with pytest.raises(error):
        _open(prepared, cause, **changes)
    runtime.close()


def test_repair_cycle_key_cannot_reopen(tmp_path: Path) -> None:
    runtime, prepared, cause = _fixture(tmp_path)
    frame, _ = _open(prepared, cause)
    with pytest.raises(RepairCycleDetected, match="REPAIR_CYCLE"):
        _open(prepared, cause, active_cycle_keys=(frame.cycle_key,))
    runtime.close()
