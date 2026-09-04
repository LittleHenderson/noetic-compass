from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest
import torch


CASFORMER_ROOT = Path(__file__).resolve().parents[2] / "CASFORMER_v0_1"
sys.path.insert(0, str(CASFORMER_ROOT))

from casformer import CASformerConfig

from cas_cjt.checkpoint import (
    checkpoint_entry_digests,
    diff_checkpoint_artifacts,
    encode_module_checkpoint,
)
from cas_cjt.control import RouteSettings
from cas_cjt.contracts import (
    ContractSchemaError,
    canonical_digest,
    canonical_json,
    validate_contract,
)
from cas_cjt.memory import MemoryError as CJTMemoryError
from cas_cjt.network import CJTNodeSpec, TopologyEdge
from cas_cjt.network_coordinator import NetworkBatchRejected
from cas_cjt.persistence import PersistenceError, SQLiteAtomicStore
from cas_cjt.repair import repair_outcome_from_dict
from cas_cjt.runtime import NeuralCJTRuntime, RuntimeContractError
from cas_cjt.state import make_cause
from cas_cjt.types import MANDATORY_TICK_ORDER, RepairStatus, VerifierDisposition


LABELS = ("L0", "L1", "L2", "L3")
SPECS = tuple(CJTNodeSpec(name, "^6") for name in ("A", "B", "C", "R"))
EDGES = (
    TopologyEdge("A", "B"),
    TopologyEdge("B", "C"),
    TopologyEdge("C", "R"),
    TopologyEdge("R", "C"),
)


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


def _input() -> torch.Tensor:
    return torch.tensor([[[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]])


def _objective(names: tuple[str, ...]):
    def loss(model: torch.nn.Module) -> torch.Tensor:
        parameters = dict(model.named_parameters())
        return sum(((parameters[name] - 0.125) ** 2).mean() for name in names)

    def score(model: torch.nn.Module) -> dict[str, float]:
        return {
            "target_loss": float(loss(model).detach().item()),
            "retention_loss": 0.0,
        }

    return loss, score


def _subprocess_restore(database: Path) -> dict[str, object]:
    code = """
import json, sys
from casformer import CASformerConfig
from cas_cjt import CJTNodeSpec, TopologyEdge, NeuralCJTRuntime
cfg=CASformerConfig(d_model=4,num_heads=2,num_relations=4,num_layers=1,dropout=0.0,attention_dropout=0.0,initial_cutoff=0.01,initial_saturation=100.0)
specs=tuple(CJTNodeSpec(x,'^6') for x in ('A','B','C','R'))
edges=(TopologyEdge('A','B'),TopologyEdge('B','C'),TopologyEdge('C','R'),TopologyEdge('R','C'))
runtime=NeuralCJTRuntime.open(sys.argv[1],config=cfg,node_specs=specs,topology=edges,labels=('L0','L1','L2','L3'))
print(json.dumps({'state_digest':runtime.state.state_digest,'model_digest':runtime.state.model_digest,'state_version':runtime.state.state_version,'integrity':True},sort_keys=True))
runtime.close()
"""
    environment = dict(os.environ)
    package_root = str(Path(__file__).resolve().parents[1])
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(CASFORMER_ROOT), package_root, environment.get("PYTHONPATH", ""))
    )
    completed = subprocess.run(
        [sys.executable, "-c", code, str(database)],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
    )
    return json.loads(completed.stdout)


def test_complete_four_cjt_reasoning_transistor(tmp_path: Path) -> None:
    """One scenario proves all fifteen first-prototype acceptance behaviors."""

    database = tmp_path / "complete-cjt.db"
    runtime = NeuralCJTRuntime.create(
        database,
        config=_config(),
        node_specs=SPECS,
        topology=EDGES,
        seed=7,
        labels=LABELS,
    )
    original_state = runtime.state
    original_artifact = runtime.store.load_artifact(
        original_state.model_artifact_ref.artifact_id
    )

    # Freeze an exact pre-learning neural result without committing it.  The
    # same Cause is replayed after learning and a process restart below.
    proof_cause, proof_artifact = runtime.make_input_cause(
        _input(),
        tick=6,
        content={"task": "repeat after durable learning"},
        goal_context={"goal": "behavioral proof"},
    )
    before_learning = runtime._prepare_inference(
        cause=proof_cause,
        cjt_id="C",
        expected_symbol="L0",
        opposite_symbol=None,
        settings=None,
        supplied_artifacts=(proof_artifact,),
        resume_repair_id=None,
        write_memory=False,
    )
    before_candidate_digest = before_learning.candidate_effect.content_ref.sha256
    before_binding = dict(before_learning.materialized.binding_manifest)
    assert before_binding["model_digest"] == original_state.model_digest
    assert before_binding["bias_digest"] == original_state.by_cjt_id["C"].state_digest
    assert before_binding["recurrent_bias_digest"] is None
    assert not bool((before_learning.materialized.bias_tensor != 0).any().item())

    cause_a, cause_artifact = runtime.make_input_cause(
        _input(),
        tick=1,
        content={"task": "four-CJT demonstration"},
        goal_context={"goal": "verified decomposition chain"},
    )
    result_a = runtime.inference_tick(
        cause=cause_a,
        cjt_id="A",
        expected_symbol="L1",
        supplied_artifacts=(cause_artifact,),
    )
    assert result_a.accepted
    assert result_a.commit_receipt.published_effect_ids

    cause_b = runtime.cause_from_effect(
        result_a.commit_receipt.published_effect_ids[0],
        tick=2,
        candidate_operation_ids=("^6",),
        goal_context={"goal": "verified decomposition chain"},
    )
    assert cause_b.parent_effect_id == result_a.commit_receipt.published_effect_ids[0]
    assert runtime.network.select_candidates(cause_b) == ("B",)
    result_b = runtime.inference_tick(
        cause=cause_b,
        cjt_id="B",
        expected_symbol="L3",
    )
    assert result_b.accepted

    cause_c = runtime.cause_from_effect(
        result_b.commit_receipt.published_effect_ids[0],
        tick=3,
        candidate_operation_ids=("^6",),
        goal_context={"goal": "verified decomposition chain"},
    )
    result_c = runtime.inference_tick(
        cause=cause_c,
        cjt_id="C",
        expected_symbol="L0",
        opposite_symbol="L2",
    )
    assert result_c.verifier_receipt.disposition is VerifierDisposition.REPAIR
    assert result_c.repair_frame is not None
    assert result_c.repair_subgoal is not None
    assert result_c.repair_frame.opened_tick == 3
    assert result_c.repair_frame.eligible_tick == 4
    assert result_c.repair_subgoal.tick == 4
    assert result_c.repair_subgoal.cause_id == result_c.repair_frame.subgoal_cause_id

    result_repair = runtime.inference_tick(
        cause=result_c.repair_subgoal,
        cjt_id="R",
        expected_symbol="L1",
    )
    assert result_repair.accepted
    repair_effect_id = result_repair.commit_receipt.published_effect_ids[0]
    resumed_cause = runtime.cause_from_effect(
        repair_effect_id,
        tick=5,
        candidate_operation_ids=("^6",),
        goal_context={"goal": "verified decomposition chain"},
    )
    assert runtime.network.select_candidates(resumed_cause) == ("C",)

    allowed_c = runtime.network.parameter_names_for_node("C")
    loss_c, score_c = _objective(allowed_c)
    learning = runtime.learning_tick(
        cause=resumed_cause,
        cjt_id="C",
        expected_symbol="L2",
        loss_fn=loss_c,
        score_fn=score_c,
        regression_passed=True,
        resume_repair_id=result_c.repair_frame.repair_id,
    )
    assert learning.pre_model_digest != learning.post_model_digest
    assert learning.learning_proposal.qualification.qualified
    assert not learning.bias_after.rpm.open_repair_ids
    assert result_c.repair_frame.repair_id in learning.bias_after.rpm.repair_history
    assert learning.inference is not None
    outcome = learning.inference.repair_outcome
    assert outcome is not None
    assert outcome.status is RepairStatus.RETURNED
    assert outcome.repair_id == result_c.repair_frame.repair_id
    assert outcome.frame_digest == result_c.repair_frame.frame_digest
    assert outcome.result_effect_id == repair_effect_id
    assert outcome.resumed_cause_id == resumed_cause.cause_id
    assert outcome.resumed_candidate_effect_id == learning.inference.candidate_effect.candidate_effect_id
    assert outcome.verifier_receipt_id == learning.inference.verifier_receipt.receipt_id
    assert outcome.target_bias_id == learning.bias_before.bias_id
    assert outcome.target_bias_version == learning.bias_before.version
    assert outcome.target_bias_digest == learning.bias_before.state_digest
    retained_frame = runtime.store.immutable_document(
        "repair_frames", result_c.repair_frame.repair_id
    )
    assert retained_frame["status"] == RepairStatus.OPEN.value
    assert retained_frame["result_effect_id"] is None
    retained_outcome = repair_outcome_from_dict(
        runtime.store.immutable_document("repair_outcomes", outcome.outcome_id)
    )
    assert retained_outcome == outcome
    repair_transition = runtime.store.reconstruct_transition(
        learning.commit_receipt.trace_id
    )
    assert repair_transition["repair_outcomes"] == [outcome.to_dict()]
    assert repair_transition["trace"]["repair_outcome_ids"] == [outcome.outcome_id]
    emit = next(
        item
        for item in repair_transition["trace"]["phases"]
        if item["phase"] == "EMIT"
    )
    assert emit["outputs"]["repair_outcome_ids"] == [outcome.outcome_id]
    assert all(
        bias.theta.model_digest == learning.post_model_digest
        and bias.theta.model_version == 1
        for bias in runtime.state.biases
    )

    learned_artifact = runtime.store.load_artifact(
        runtime.state.model_artifact_ref.artifact_id
    )
    changed = diff_checkpoint_artifacts(
        original_state.model_artifact_ref,
        original_artifact,
        runtime.state.model_artifact_ref,
        learned_artifact,
    )
    assert changed == learning.learning_proposal.changed_parameter_names
    assert changed and all("cells.node_0002.operations" in name for name in changed)
    before_entries = checkpoint_entry_digests(
        original_state.model_artifact_ref, original_artifact
    )
    after_entries = checkpoint_entry_digests(
        runtime.state.model_artifact_ref, learned_artifact
    )
    assert all(
        before_entries[name] == after_entries[name]
        for name in before_entries
        if name not in changed
    )

    durable_state = runtime.state
    runtime.close()
    restored = _subprocess_restore(database)
    assert restored == {
        "integrity": True,
        "model_digest": durable_state.model_digest,
        "state_digest": durable_state.state_digest,
        "state_version": 5,
    }

    runtime = NeuralCJTRuntime.open(
        database,
        config=_config(),
        node_specs=SPECS,
        topology=EDGES,
        labels=LABELS,
    )
    later_cause, later_artifact = runtime.make_input_cause(
        _input(),
        tick=6,
        content={"task": "repeat after durable learning"},
        goal_context={"goal": "behavioral proof"},
    )
    assert later_cause == proof_cause
    assert later_artifact.sha256 == proof_artifact.sha256
    later = runtime.inference_tick(
        cause=later_cause,
        cjt_id="C",
        expected_symbol="L0",
        supplied_artifacts=(later_artifact,),
    )
    assert later.accepted
    assert bool((later.materialized.bias_tensor != 0).any().item())
    assert (
        later.materialized.binding_manifest["recurrent_bias_digest"]
        == durable_state.by_cjt_id["C"].memory.recurrent_state_ref.sha256
    )
    assert later.materialized.binding_manifest["model_digest"] == durable_state.model_digest
    assert later.materialized.binding_manifest["model_digest"] != before_binding["model_digest"]
    assert later.materialized.binding_manifest["bias_digest"] != before_binding["bias_digest"]
    assert later.candidate_effect.content_ref.sha256 != before_candidate_digest

    # An attempted C-learning update that changes A's bytes is rejected.  The
    # active state, model bytes, Effects, and trace head remain unchanged while
    # a separate non-authoritative rejection audit is appended.
    before_bad_head = runtime.store.head
    before_bad_model = encode_module_checkpoint(runtime.network).artifact.payload
    before_bad_effects = tuple(
        item["published_effect_id"]
        for trace in runtime.store.trace_events()
        for item in runtime.store.documents_for_receipt(
            "published_effects", trace["commit_receipt_id"]
        )
    )
    bad_cause, bad_artifact = runtime.make_input_cause(
        _input(),
        tick=7,
        content={"task": "attempt cross-CJT update"},
        goal_context={"goal": "must fail closed"},
    )
    wrong_scope = runtime.network.parameter_names_for_node("A")
    bad_loss, bad_score = _objective(wrong_scope)
    with pytest.raises(NetworkBatchRejected, match="CHECKPOINT_PARAMETER_SCOPE_ESCAPE"):
        runtime.learning_tick(
            cause=bad_cause,
            cjt_id="C",
            expected_symbol="L0",
            loss_fn=bad_loss,
            score_fn=bad_score,
            supplied_artifacts=(bad_artifact,),
            allowed_parameter_names=wrong_scope,
            regression_passed=True,
        )
    assert runtime.store.head == before_bad_head
    assert encode_module_checkpoint(runtime.network).artifact.payload == before_bad_model
    after_bad_effects = tuple(
        item["published_effect_id"]
        for trace in runtime.store.trace_events()
        for item in runtime.store.documents_for_receipt(
            "published_effects", trace["commit_receipt_id"]
        )
    )
    assert after_bad_effects == before_bad_effects
    rejection = runtime.store.rejection_audits()[-1]
    assert rejection["pre_state_digest"] == rejection["post_state_digest"]
    assert rejection["pre_model_digest"] == rejection["post_model_digest"]
    assert rejection["reason_codes"] == ["CHECKPOINT_PARAMETER_SCOPE_ESCAPE"]
    assert rejection["atomic_rollback"] is True

    traces = runtime.store.trace_events()
    assert [trace["tick"] for trace in traces] == [1, 2, 3, 4, 5, 6]
    assert all(
        tuple(record["phase"] for record in trace["phases"])
        == tuple(phase.value for phase in MANDATORY_TICK_ORDER)
        for trace in traces
    )
    for trace in traces:
        assert validate_contract(trace) == trace
        rebuilt = runtime.store.reconstruct_transition(trace["trace_id"])
        assert rebuilt["trace"] == trace
        assert rebuilt["causes"]
        assert rebuilt["candidate_effects"]
        assert rebuilt["verifier_receipts"]
        assert rebuilt["transition_batches"]
        assert rebuilt["artifacts"]
    with pytest.raises(ContractSchemaError):
        validate_contract({**traces[0], "undeclared_trace_field": True})
    assert runtime.store.verify_integrity()
    runtime.close()

    tampered_outcome_database = tmp_path / "tampered-outcome.db"
    shutil.copy2(database, tampered_outcome_database)
    connection = sqlite3.connect(tampered_outcome_database)
    for (trigger_name,) in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'repair_outcomes'"
    ).fetchall():
        connection.execute(f'DROP TRIGGER "{trigger_name}"')
    connection.execute(
        "UPDATE repair_outcomes SET payload_json = payload_json || 'x'"
    )
    connection.commit()
    connection.close()
    tampered_outcome = SQLiteAtomicStore(tampered_outcome_database)
    assert tampered_outcome.verify_integrity() is False
    tampered_outcome.close()

    tampered_frame_database = tmp_path / "tampered-frame.db"
    shutil.copy2(database, tampered_frame_database)
    connection = sqlite3.connect(tampered_frame_database)
    frame_row = connection.execute(
        "SELECT record_id, commit_receipt_id, payload_json FROM repair_frames LIMIT 1"
    ).fetchone()
    frame_payload = json.loads(frame_row[2])
    frame_payload["cycle_key"] = "f" * 64
    frame_payload["frame_digest"] = canonical_digest(
        frame_payload, omit_keys=("frame_digest",)
    )
    frame_json = canonical_json(frame_payload)
    frame_checksum = hashlib.sha256(frame_json.encode("ascii")).hexdigest()
    for (trigger_name,) in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'repair_frames'"
    ).fetchall():
        connection.execute(f'DROP TRIGGER "{trigger_name}"')
    connection.execute(
        "UPDATE repair_frames SET payload_sha256 = ?, payload_json = ? "
        "WHERE record_id = ?",
        (frame_checksum, frame_json, frame_row[0]),
    )
    owner_trace_id = connection.execute(
        "SELECT te.trace_id FROM commit_receipts cr "
        "JOIN trace_events te ON te.trace_digest = cr.trace_digest "
        "WHERE cr.receipt_id = ?",
        (frame_row[1],),
    ).fetchone()[0]
    connection.commit()
    connection.close()
    tampered_frame = SQLiteAtomicStore(tampered_frame_database)
    with pytest.raises(PersistenceError, match="repair frame evidence"):
        tampered_frame.reconstruct_transition(owner_trace_id)
    assert tampered_frame.verify_integrity() is False
    tampered_frame.close()

    tampered_database = tmp_path / "tampered.db"
    shutil.copy2(database, tampered_database)
    connection = sqlite3.connect(tampered_database)
    for (trigger_name,) in connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'trigger' AND tbl_name = 'trace_events'"
    ).fetchall():
        connection.execute(f'DROP TRIGGER "{trigger_name}"')
    connection.execute(
        "UPDATE trace_events SET payload_json = payload_json || 'x' WHERE sequence = 1"
    )
    connection.commit()
    connection.close()
    tampered = SQLiteAtomicStore(tampered_database)
    assert tampered.verify_integrity() is False
    tampered.close()


@pytest.mark.parametrize("mutation", ("nested_digest", "shared_model"))
def test_persistence_rejects_resealed_malformed_network_biases(
    tmp_path: Path, mutation: str
) -> None:
    runtime = NeuralCJTRuntime.create(
        tmp_path / f"nested-bias-{mutation}.db",
        config=_config(),
        node_specs=SPECS,
        topology=EDGES,
        seed=7,
        labels=LABELS,
    )
    store = runtime.store
    old_digest = store.head.state_digest
    row = store._connection.execute(  # noqa: SLF001 - adversarial row mutation
        "SELECT payload_json FROM state_versions WHERE state_digest = ?",
        (old_digest,),
    ).fetchone()
    payload = json.loads(row["payload_json"])
    if mutation == "nested_digest":
        payload["biases"][0]["state_digest"] = "f" * 64
    else:
        payload["biases"][0]["theta"]["model_version"] = 7
        payload["biases"][0]["state_digest"] = canonical_digest(
            payload["biases"][0], omit_keys=("state_digest",)
        )
    payload["state_digest"] = canonical_digest(
        payload, omit_keys=("state_digest",)
    )
    new_digest = payload["state_digest"]
    payload_json = canonical_json(payload)
    checksum = hashlib.sha256(payload_json.encode("ascii")).hexdigest()
    store._connection.execute("PRAGMA foreign_keys = OFF")  # noqa: SLF001
    store._connection.execute(  # noqa: SLF001
        "DROP TRIGGER state_versions_immutable_update"
    )
    store._connection.execute(  # noqa: SLF001
        "UPDATE state_versions SET state_digest = ?, payload_sha256 = ?, "
        "payload_json = ? WHERE state_digest = ?",
        (new_digest, checksum, payload_json, old_digest),
    )
    store._connection.execute(  # noqa: SLF001
        "UPDATE active_head SET state_digest = ? WHERE singleton = 1",
        (new_digest,),
    )
    with pytest.raises(PersistenceError, match="Bias|network model head"):
        store.load_state(new_digest)
    assert store.verify_integrity() is False
    runtime.close()


def test_zero_flow_is_audited_but_cannot_publish(tmp_path: Path) -> None:
    runtime = NeuralCJTRuntime.create(
        tmp_path / "zero-flow.db",
        config=_config(),
        node_specs=SPECS,
        topology=EDGES,
        seed=7,
        labels=LABELS,
    )
    cause, artifact = runtime.make_input_cause(
        _input(),
        tick=1,
        content={"task": "zero flow"},
        goal_context={"goal": "prove no fallback"},
    )
    before = runtime.state
    result = runtime.inference_tick(
        cause=cause,
        cjt_id="A",
        expected_symbol="NO_EFFECT",
        supplied_artifacts=(artifact,),
        settings=RouteSettings(permission_open=False),
    )
    assert result.verifier_receipt.disposition is VerifierDisposition.ABSTAIN
    assert result.verifier_receipt.reason_codes == ("ZERO_FLOW",)
    assert result.commit_receipt.published_effect_ids == ()
    assert result.bias_after == before.by_cjt_id["A"]
    assert int(
        torch.count_nonzero(
            result.materialized.routing.compute_plan.route_quanta
        ).item()
    ) == 0
    assert runtime.store.verify_integrity()
    runtime.close()


def test_poisoned_repair_resume_cause_cannot_close_open_frame(tmp_path: Path) -> None:
    runtime = NeuralCJTRuntime.create(
        tmp_path / "poisoned-resume.db",
        config=_config(),
        node_specs=SPECS,
        topology=EDGES,
        seed=7,
        labels=LABELS,
    )
    cause, artifact = runtime.make_input_cause(
        _input(),
        tick=1,
        content={"task": "open a repair"},
        goal_context={"goal": "poisoned resume must fail"},
    )
    preview = runtime._prepare_inference(
        cause=cause,
        cjt_id="C",
        expected_symbol=None,
        opposite_symbol=None,
        settings=None,
        supplied_artifacts=(artifact,),
        resume_repair_id=None,
        write_memory=False,
    )
    actual_symbol = str(preview.candidate_effect.content["symbol"])
    expected_symbol = next(label for label in LABELS if label != actual_symbol)
    opened = runtime.inference_tick(
        cause=cause,
        cjt_id="C",
        expected_symbol=expected_symbol,
        opposite_symbol=actual_symbol,
        supplied_artifacts=(artifact,),
    )
    assert opened.repair_frame is not None
    assert opened.repair_subgoal is not None

    ordinary, ordinary_artifact = runtime.make_input_cause(
        _input(),
        tick=2,
        content={"task": "attempt ordinary execution while suspended"},
        goal_context={"goal": "poisoned resume must fail"},
    )
    before_ordinary = runtime.store.head
    with pytest.raises(
        RuntimeContractError,
        match="reserved for the exact repair subgoal",
    ):
        runtime.inference_tick(
            cause=ordinary,
            cjt_id="C",
            expected_symbol="L0",
            supplied_artifacts=(ordinary_artifact,),
        )
    assert runtime.store.head == before_ordinary
    assert opened.repair_frame.repair_id in runtime.state.by_cjt_id[
        "C"
    ].rpm.open_repair_ids

    repair_control = runtime.materializer.materialize(
        state=runtime.state,
        cause=opened.repair_subgoal,
        cjt_id="R",
        settings=RouteSettings(),
    )
    repair_proposal = runtime.network.forward_node(
        "R", repair_control.cause_tensor, repair_control.control
    )
    repair_symbol = str(
        runtime.decoders["R"].decode(repair_proposal.candidate_effect)["symbol"]
    )
    repaired = runtime.inference_tick(
        cause=opened.repair_subgoal,
        cjt_id="R",
        expected_symbol=repair_symbol,
        write_memory=False,
    )
    repair_effect_id = repaired.commit_receipt.published_effect_ids[0]
    canonical = runtime.cause_from_effect(
        repair_effect_id,
        tick=3,
        candidate_operation_ids=("^6",),
        goal_context={"goal": "poisoned resume must fail"},
    )
    poisoned = make_cause(
        tick=canonical.tick,
        cause_kind=canonical.cause_kind,
        content=canonical.content,
        goal_context=canonical.goal_context,
        source="poisoned:noncanonical-resume",
        provenance=canonical.provenance,
        uncertainty_ppm=canonical.uncertainty_ppm,
        entity_bindings=canonical.entity_bindings,
        relation_bindings=canonical.relation_bindings,
        candidate_operation_ids=canonical.candidate_operation_ids,
        memory_refs=canonical.memory_refs,
        content_ref=canonical.content_ref,
        parent_effect_id=canonical.parent_effect_id,
        originating_cjt_id=canonical.originating_cjt_id,
        originating_modality=canonical.originating_modality,
    )
    before = runtime.store.head
    with pytest.raises(RuntimeContractError, match="not derived from the committed Effect"):
        runtime.inference_tick(
            cause=poisoned,
            cjt_id="C",
            expected_symbol="L0",
            resume_repair_id=opened.repair_frame.repair_id,
        )
    assert runtime.store.head == before
    assert opened.repair_frame.repair_id in runtime.state.by_cjt_id["C"].rpm.open_repair_ids
    assert runtime.store.documents_for_receipt("repair_outcomes", before.commit_receipt_id) == ()
    assert runtime.store.verify_integrity()
    runtime.close()


def test_breakdown_fails_closed_even_when_symbol_matches(tmp_path: Path) -> None:
    runtime = NeuralCJTRuntime.create(
        tmp_path / "breakdown.db",
        config=_config(),
        node_specs=SPECS,
        topology=EDGES,
        seed=7,
        labels=LABELS,
    )
    cause, artifact = runtime.make_input_cause(
        _input(),
        tick=1,
        content={"task": "breakdown"},
        goal_context={"goal": "fail closed"},
    )
    result = runtime.inference_tick(
        cause=cause,
        cjt_id="A",
        expected_symbol="NO_EFFECT",
        supplied_artifacts=(artifact,),
        settings=RouteSettings(force_breakdown=True),
    )
    assert result.verifier_receipt.disposition is VerifierDisposition.QUARANTINE
    assert result.verifier_receipt.reason_codes == ("BREAKDOWN_REGION",)
    assert result.commit_receipt.published_effect_ids == ()
    assert runtime.store.verify_integrity()
    runtime.close()


@pytest.mark.parametrize("mismatch", ("topology", "decoder"))
def test_restart_rejects_a_different_runtime_identity(
    tmp_path: Path, mismatch: str
) -> None:
    database = tmp_path / f"restart-{mismatch}.db"
    runtime = NeuralCJTRuntime.create(
        database,
        config=_config(),
        node_specs=SPECS,
        topology=EDGES,
        seed=7,
        labels=LABELS,
    )
    runtime.close()
    topology = EDGES if mismatch == "decoder" else tuple(reversed(EDGES[:-1]))
    labels = LABELS if mismatch == "topology" else tuple(reversed(LABELS))
    with pytest.raises(RuntimeContractError, match="restart configuration"):
        NeuralCJTRuntime.open(
            database,
            config=_config(),
            node_specs=SPECS,
            topology=topology,
            labels=labels,
        )


def test_runtime_resolves_memory_and_uses_its_tensor_as_candidate_bias(
    tmp_path: Path,
) -> None:
    runtime = NeuralCJTRuntime.create(
        tmp_path / "memory-read.db",
        config=_config(),
        node_specs=SPECS,
        topology=EDGES,
        seed=7,
        labels=LABELS,
    )
    first_cause, first_artifact = runtime.make_input_cause(
        _input(),
        tick=1,
        content={"task": "write memory"},
        goal_context={"goal": "memory proof"},
    )
    first = runtime.inference_tick(
        cause=first_cause,
        cjt_id="A",
        expected_symbol="L1",
        supplied_artifacts=(first_artifact,),
    )
    memory = runtime.store.documents_for_receipt(
        "memory_records", first.commit_receipt.receipt_id
    )[0]
    memory_id = memory["memory_record_id"]
    second_cause, second_artifact = runtime.make_input_cause(
        _input(),
        tick=2,
        content={"task": "read memory"},
        goal_context={"goal": "memory proof"},
        memory_refs=(memory_id,),
    )
    second = runtime.inference_tick(
        cause=second_cause,
        cjt_id="B",
        expected_symbol=None,
        supplied_artifacts=(second_artifact,),
        write_memory=False,
    )
    assert [item["memory_record_id"] for item in second.materialized.memory_reads] == [
        memory_id
    ]
    assert bool((second.materialized.bias_tensor != 0).any().item())
    trace = runtime.store.reconstruct_transition(second.commit_receipt.trace_id)["trace"]
    assert trace["memory_read_refs"] == [memory_id]
    assert second.commit_receipt.published_effect_ids == ()

    before_missing = runtime.store.head
    missing_cause, missing_artifact = runtime.make_input_cause(
        _input(),
        tick=3,
        content={"task": "missing memory must fail"},
        goal_context={"goal": "memory proof"},
        memory_refs=("memory-does-not-exist",),
    )
    with pytest.raises(CJTMemoryError, match="was not found"):
        runtime.inference_tick(
            cause=missing_cause,
            cjt_id="B",
            expected_symbol=None,
            supplied_artifacts=(missing_artifact,),
        )
    assert runtime.store.head == before_missing
    runtime.close()


def test_bias_theta_beta_is_the_live_neural_beta(tmp_path: Path) -> None:
    config = CASformerConfig(
        d_model=4,
        num_heads=2,
        num_relations=4,
        num_layers=1,
        dropout=0.0,
        attention_dropout=0.0,
        initial_beta=0.5,
        initial_cutoff=0.01,
        initial_saturation=100.0,
    )
    runtime = NeuralCJTRuntime.create(
        tmp_path / "beta-binding.db",
        config=config,
        node_specs=SPECS,
        topology=EDGES,
        seed=7,
        labels=LABELS,
    )
    cause, artifact = runtime.make_input_cause(
        _input(),
        tick=1,
        content={"task": "beta binding"},
        goal_context={"goal": "bind declared and live beta"},
    )
    prepared = runtime._prepare_inference(
        cause=cause,
        cjt_id="A",
        expected_symbol=None,
        opposite_symbol=None,
        settings=None,
        supplied_artifacts=(artifact,),
        resume_repair_id=None,
        write_memory=False,
    )
    assert prepared.bias.theta.beta_microunits == 500_000
    assert prepared.materialized.binding_manifest["declared_beta_microunits"] == 500_000
    assert prepared.materialized.binding_manifest["live_beta_by_head_microunits"] == [
        500_000,
        500_000,
    ]
    runtime.close()
