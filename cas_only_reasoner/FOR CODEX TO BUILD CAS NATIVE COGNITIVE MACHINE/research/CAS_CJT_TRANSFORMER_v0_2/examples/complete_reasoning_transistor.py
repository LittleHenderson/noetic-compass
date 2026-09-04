"""Run the complete four-CJT v0.2 research acceptance scenario."""

from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

import torch

from casformer import CASformerConfig
from cas_cjt import (
    CJTNodeSpec,
    NetworkBatchRejected,
    NeuralCJTRuntime,
    TopologyEdge,
    diff_checkpoint_artifacts,
)


LABELS = ("L0", "L1", "L2", "L3")
SPECS = tuple(CJTNodeSpec(name, "^6") for name in ("A", "B", "C", "R"))
EDGES = (
    TopologyEdge("A", "B"),
    TopologyEdge("B", "C"),
    TopologyEdge("C", "R"),
    TopologyEdge("R", "C"),
)


def config() -> CASformerConfig:
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


def input_tensor() -> torch.Tensor:
    return torch.tensor([[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]])


def objective(names: tuple[str, ...]):
    def loss(model: torch.nn.Module) -> torch.Tensor:
        parameters = dict(model.named_parameters())
        return sum(((parameters[name] - 0.125) ** 2).mean() for name in names)

    def score(model: torch.nn.Module) -> dict[str, float]:
        return {
            "target_loss": float(loss(model).detach().item()),
            "retention_loss": 0.0,
        }

    return loss, score


def run_demo(database: Path) -> dict[str, object]:
    database.parent.mkdir(parents=True, exist_ok=True)
    runtime = NeuralCJTRuntime.create(
        database,
        config=config(),
        node_specs=SPECS,
        topology=EDGES,
        seed=7,
        labels=LABELS,
    )
    initial_state = runtime.state
    initial_checkpoint = runtime.store.load_artifact(
        initial_state.model_artifact_ref.artifact_id
    )
    proof_cause, proof_artifact = runtime.make_input_cause(
        input_tensor(),
        tick=6,
        content={"task": "after restart"},
        goal_context={"goal": "behavioral proof"},
    )
    pre_learning = runtime._prepare_inference(
        cause=proof_cause,
        cjt_id="C",
        expected_symbol="L0",
        opposite_symbol=None,
        settings=None,
        supplied_artifacts=(proof_artifact,),
        resume_repair_id=None,
        write_memory=False,
    )
    pre_learning_candidate_digest = pre_learning.candidate_effect.content_ref.sha256

    cause, artifact = runtime.make_input_cause(
        input_tensor(),
        tick=1,
        content={"task": "complete reasoning transistor"},
        goal_context={"goal": "verified four-CJT chain"},
    )
    a = runtime.inference_tick(
        cause=cause,
        cjt_id="A",
        expected_symbol="L1",
        supplied_artifacts=(artifact,),
    )
    cause = runtime.cause_from_effect(
        a.commit_receipt.published_effect_ids[0],
        tick=2,
        candidate_operation_ids=("^6",),
        goal_context={"goal": "verified four-CJT chain"},
    )
    b = runtime.inference_tick(cause=cause, cjt_id="B", expected_symbol="L3")
    cause = runtime.cause_from_effect(
        b.commit_receipt.published_effect_ids[0],
        tick=3,
        candidate_operation_ids=("^6",),
        goal_context={"goal": "verified four-CJT chain"},
    )
    c_rejected = runtime.inference_tick(
        cause=cause,
        cjt_id="C",
        expected_symbol="L0",
        opposite_symbol="L2",
    )
    assert c_rejected.repair_subgoal is not None
    assert c_rejected.repair_frame is not None
    repair = runtime.inference_tick(
        cause=c_rejected.repair_subgoal,
        cjt_id="R",
        expected_symbol="L1",
    )
    resumed = runtime.cause_from_effect(
        repair.commit_receipt.published_effect_ids[0],
        tick=5,
        candidate_operation_ids=("^6",),
        goal_context={"goal": "verified four-CJT chain"},
    )
    allowed = runtime.network.parameter_names_for_node("C")
    loss, score = objective(allowed)
    learned = runtime.learning_tick(
        cause=resumed,
        cjt_id="C",
        expected_symbol="L2",
        loss_fn=loss,
        score_fn=score,
        regression_passed=True,
        resume_repair_id=c_rejected.repair_frame.repair_id,
    )
    if learned.inference is None or learned.inference.repair_outcome is None:
        raise AssertionError("resumed learning did not seal a repair outcome")
    repair_outcome_id = learned.inference.repair_outcome.outcome_id
    durable_state = runtime.state
    learned_checkpoint = runtime.store.load_artifact(
        durable_state.model_artifact_ref.artifact_id
    )
    changed = diff_checkpoint_artifacts(
        initial_state.model_artifact_ref,
        initial_checkpoint,
        durable_state.model_artifact_ref,
        learned_checkpoint,
    )
    runtime.close()

    # Reopen from durable bytes, then prove the retained recurrent Bias is read.
    runtime = NeuralCJTRuntime.open(
        database,
        config=config(),
        node_specs=SPECS,
        topology=EDGES,
        labels=LABELS,
    )
    later_cause, later_artifact = runtime.make_input_cause(
        input_tensor(),
        tick=6,
        content={"task": "after restart"},
        goal_context={"goal": "behavioral proof"},
    )
    if later_cause != proof_cause or later_artifact.sha256 != proof_artifact.sha256:
        raise AssertionError("post-restart behavioral proof did not replay the exact Cause")
    later = runtime.inference_tick(
        cause=later_cause,
        cjt_id="C",
        expected_symbol="L0",
        supplied_artifacts=(later_artifact,),
    )

    # Deliberately ask C's learning authority to change A's parameters.
    # The independent coordinator rejects it and records only an audit.
    before_invalid = runtime.store.head
    invalid_cause, invalid_artifact = runtime.make_input_cause(
        input_tensor(),
        tick=7,
        content={"task": "invalid cross-CJT learning"},
        goal_context={"goal": "prove rollback"},
    )
    wrong_names = runtime.network.parameter_names_for_node("A")
    wrong_loss, wrong_score = objective(wrong_names)
    rejected_reason = ""
    try:
        runtime.learning_tick(
            cause=invalid_cause,
            cjt_id="C",
            expected_symbol="L0",
            loss_fn=wrong_loss,
            score_fn=wrong_score,
            supplied_artifacts=(invalid_artifact,),
            allowed_parameter_names=wrong_names,
            regression_passed=True,
        )
    except NetworkBatchRejected as error:
        rejected_reason = ",".join(error.reason_codes)
    else:  # pragma: no cover - demonstration invariant
        raise AssertionError("invalid cross-CJT update unexpectedly committed")
    if runtime.store.head != before_invalid:
        raise AssertionError("rejected update changed the authoritative head")

    traces = runtime.store.trace_events()
    reconstruction = runtime.store.reconstruct_transition(
        learned.commit_receipt.trace_id
    )
    result = {
        "database": str(database.resolve()),
        "cjt_chain": ["A", "B", "C", "R", "C"],
        "accepted_effects": sum(
            len(trace["published_effect_ids"]) for trace in traces
        ),
        "repair_opened_tick": c_rejected.repair_frame.opened_tick,
        "repair_eligible_tick": c_rejected.repair_frame.eligible_tick,
        "repair_closed": not runtime.state.by_cjt_id["C"].rpm.open_repair_ids,
        "repair_outcome_id": repair_outcome_id,
        "pre_model_digest": learned.pre_model_digest,
        "post_model_digest": learned.post_model_digest,
        "changed_parameter_names": list(changed),
        "later_bias_artifact_used": later.materialized.binding_manifest[
            "recurrent_bias_artifact_id"
        ],
        "later_symbol": later.candidate_effect.content["symbol"],
        "same_input_cause_id": later_cause.cause_id,
        "pre_learning_candidate_digest": pre_learning_candidate_digest,
        "post_restart_candidate_digest": later.candidate_effect.content_ref.sha256,
        "same_input_output_changed": (
            later.candidate_effect.content_ref.sha256
            != pre_learning_candidate_digest
        ),
        "invalid_update_reason": rejected_reason,
        "invalid_update_left_head_unchanged": runtime.store.head == before_invalid,
        "trace_count": len(traces),
        "learning_transition_reconstructed": bool(
            reconstruction["candidate_effects"]
            and reconstruction["verifier_receipts"]
            and reconstruction["model_intents"]
            and reconstruction["qualification_receipts"]
        ),
        "integrity": runtime.store.verify_integrity(),
        "claim_boundary": (
            "Mechanism prototype only; no CAS learning or reasoning advantage is claimed."
        ),
    }
    runtime.close()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    database = args.database
    if database is None:
        database = Path(tempfile.mkdtemp(prefix="cas-neural-cjt-")) / "demo.db"
    import json

    print(json.dumps(run_demo(database), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
