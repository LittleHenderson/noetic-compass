"""Mechanism checks for fixed-weight calls, shared reservations, and restart."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path

import pytest
import torch

from cas_cjt import validate_contract
from cas_cjt.checkpoint import encode_module_checkpoint
from cas_meta.compiler import compile_program
from cas_meta.executor import Executor, Limits, MetaRuntimeError
from cas_meta.fixture import create_native, initial_input, open_native, run_reference


PROGRAM_PATH = Path(__file__).resolve().parents[1] / "programs" / "fixed_chain.json"


@pytest.fixture
def source():
    return json.loads(PROGRAM_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def program(source):
    return compile_program(source)


@pytest.fixture
def native(tmp_path):
    runtime = create_native(tmp_path / "native.db")
    try:
        yield runtime
    finally:
        runtime.close()


def _executor(native, program, **kwargs):
    cause, artifact = initial_input(native)
    return Executor(native, program, cause, artifacts=(artifact,), **kwargs)


def _advance_to_trace_count(executor, count):
    for _ in range(30):
        if len(executor.native.store.trace_events()) == count:
            return
        assert not executor.done
        executor.step()
    raise AssertionError("fixture did not reach the requested native boundary")


def _projection(runtime):
    """Compare native meaning and state, without requiring meta/trace hashes."""
    projected = []
    for trace in runtime.store.trace_events():
        validate_contract(trace)
        receipt_id = trace["commit_receipt_id"]
        projected.append({
            "tick": trace["tick"],
            "pre_state": runtime.store.load_state(trace["pre_state_digest"]),
            "post_state": runtime.store.load_state(trace["post_state_digest"]),
            "compute_plan": trace["compute_plan"],
            "compute_observations": trace["compute_observations"],
            **{
                table: runtime.store.documents_for_receipt(table, receipt_id)
                for table in (
                    "causes", "candidate_effects", "verifier_receipts",
                    "published_effects", "repair_frames", "repair_outcomes",
                    "state_intents", "model_intents", "memory_intents",
                )
            },
        })
    return projected


def test_full_fixed_weight_execution_matches_public_native_reference(native, program, tmp_path):
    reference = create_native(tmp_path / "reference.db")
    try:
        reference_results = run_reference(reference)
        executor = _executor(native, program)
        effect_id = executor.run()
        assert executor.done and not executor.frames
        assert effect_id == reference_results[-1].published_effect["published_effect_id"]
        assert _projection(native) == _projection(reference)
        assert native.state == reference.state
        assert len(native.store.trace_events()) == 5
        assert sum(len(t["published_effect_ids"]) for t in native.store.trace_events()) == 4
        assert executor.spent == 360
        assert native.store.verify_integrity()
    finally:
        reference.close()


def test_real_nested_frames_suspend_and_return_to_the_exact_caller(native, program):
    executor = _executor(native, program)
    _advance_to_trace_count(executor, 3)
    frames = executor.frames
    assert [f["procedure"] for f in frames] == ["main", "worker", "repair_c"]
    main, worker, repair = frames
    assert [f["pc"] for f in frames] == [1, 1, 0]
    assert len({f["call_id"] for f in frames}) == 3
    assert repair["parent_id"] == worker["call_id"]
    assert worker["parent_id"] == main["call_id"]
    assert repair["return_pc"] == worker["pc"] == worker["waiting"]["pc"]
    assert worker["waiting"]["child_id"] == repair["call_id"]
    assert main["waiting"]["child_id"] == worker["call_id"]
    assert frames[0]["spent"] == 216
    assert frames[1]["spent"] == 144
    assert frames[2]["spent"] == 0
    assert frames[2]["allowance"] == frames[1]["allowance"] - frames[1]["spent"]

    # Public snapshots cannot mutate the live suspended caller or meta events.
    frames[1]["waiting"]["child_id"] = "changed-detached-copy"
    events = executor.events
    events[0]["kind"] = "CHANGED_DETACHED_COPY"
    assert executor.frames[1]["waiting"]["child_id"] == repair["call_id"]
    assert executor.events[0]["kind"] == "ENTER"

    executor.step()  # R commits, while the caller remains suspended.
    assert len(native.store.trace_events()) == 4
    assert executor.frames[1]["pc"] == worker["pc"]
    assert executor.frames[1]["waiting"]["child_id"] == repair["call_id"]
    executor.step()  # Child return is a meta event, not another native tick.
    assert len(native.store.trace_events()) == 4
    assert len(executor.frames) == 2
    resumed = executor.frames[-1]
    assert resumed["call_id"] == worker["call_id"]
    assert resumed["pc"] == worker["pc"]
    assert resumed["waiting"] is None
    assert resumed["resume_repair_id"] == worker["waiting"]["repair_id"]
    returned = [e for e in executor.events if e["kind"] == "RETURN"][-1]
    assert returned["call_id"] == repair["call_id"]
    assert returned["parent_id"] == worker["call_id"]
    assert returned["return_pc"] == worker["pc"]
    executor.run()
    assert not native.state.by_cjt_id["C"].rpm.open_repair_ids
    assert [e["cjt_id"] for e in executor.events if e["kind"] == "NATIVE"] == [
        "A", "B", "C", "R", "C"
    ]


def test_restart_after_durable_repair_preserves_caller_budget_and_reference(program, tmp_path):
    path = tmp_path / "restart.db"
    runtime = create_native(path)
    executor = _executor(runtime, program)
    _advance_to_trace_count(executor, 4)
    frames = executor.frames
    assert frames[-1]["procedure"] == "repair_c"
    assert frames[-1]["pc"] == 1
    assert frames[-2]["waiting"] is not None
    checkpoint = tmp_path / "checkpoint.json"
    receipt = executor.checkpoint(checkpoint)
    head = runtime.store.head
    model = runtime.state.model_digest
    state = runtime.state
    events = executor.events
    spent = executor.spent
    runtime.close()
    reopened = open_native(path)
    reference = create_native(tmp_path / "restart-reference.db")
    try:
        restored = Executor.restore(
            reopened, program, checkpoint, expected_digest=receipt,
            chain_id="fixed-chain", limits=Limits(),
        )
        assert reopened.store.head == head
        assert reopened.state == state
        assert restored.frames == frames and restored.events == events
        assert restored.spent == spent == 288
        restored.run()
        run_reference(reference)
        assert _projection(reopened) == _projection(reference)
        assert reopened.state == reference.state
        assert reopened.state.model_digest == model
        assert len(reopened.store.trace_events()) == 5
        assert [e["cjt_id"] for e in restored.events if e["kind"] == "NATIVE"].count("R") == 1
        assert restored.spent == 360
    finally:
        reopened.close()
        reference.close()


def test_child_allowance_cannot_exceed_remaining_parent(native, program):
    executor = _executor(native, program, limits=Limits(budget=300))
    executor.step()
    head = native.store.head
    with pytest.raises(MetaRuntimeError, match="CHILD_ALLOWANCE_EXCEEDED"):
        executor.step()
    assert native.store.head == head
    assert len(native.store.trace_events()) == 1
    assert executor.spent == 72


def test_child_budget_exhaustion_prevents_neural_tick_without_refund(native, source):
    source["procedures"]["main"]["body"]["steps"][1]["allowance"] = 100
    executor = _executor(native, compile_program(source))
    _advance_to_trace_count(executor, 2)
    before = native.store.head
    with pytest.raises(MetaRuntimeError, match="SHARED_BUDGET_EXHAUSTED"):
        executor.step()
    assert native.store.head == before
    assert len(native.store.trace_events()) == 2
    assert executor.spent == 144
    with pytest.raises(MetaRuntimeError, match="EXECUTOR_HALTED"):
        executor.step()


def test_rejected_c_stays_charged_when_repair_cannot_fit_child_allowance(native, source):
    source["procedures"]["main"]["body"]["steps"][1]["allowance"] = 200
    executor = _executor(native, compile_program(source), limits=Limits(budget=300))
    _advance_to_trace_count(executor, 3)
    assert executor.spent == 216
    assert executor.frames[-1]["allowance"] == 56
    rejected_trace = native.store.trace_events()[-1]
    assert rejected_trace["published_effect_ids"] == []
    assert native.state.by_cjt_id["C"].rpm.open_repair_ids
    before = native.store.head
    with pytest.raises(MetaRuntimeError, match="SHARED_BUDGET_EXHAUSTED"):
        executor.step()
    assert native.store.head == before
    assert executor.spent == 216
    assert len([e for e in executor.events if e["kind"] == "CHARGE"]) == 3
    assert native.store.verify_integrity()


def test_scope_is_denied_before_any_native_tick(native, program):
    before = native.store.head
    with pytest.raises(MetaRuntimeError, match="CJT_SCOPE_DENIED"):
        _executor(native, program, permitted_cjts=("A", "B", "C"))
    assert native.store.head == before
    assert not native.store.trace_events()


def test_fixed_parameters_and_only_executing_cjt_bias_change(native, program):
    executor = _executor(native, program)
    original = {name: tensor.detach().clone() for name, tensor in native.network.named_parameters()}
    model = native.state.model_digest
    changed = []
    while not executor.done:
        before = native.state
        count = len(native.store.trace_events())
        executor.step()
        after = native.state
        if len(native.store.trace_events()) > count:
            event = [e for e in executor.events if e["kind"] == "NATIVE"][-1]
            names = [name for name, bias in before.by_cjt_id.items() if bias != after.by_cjt_id[name]]
            assert names == [event["cjt_id"]]
            changed.extend(names)
        else:
            assert after == before
        assert after.model_digest == model
    assert changed == ["A", "B", "C", "R", "C"]
    assert all(torch.equal(original[name], tensor) for name, tensor in native.network.named_parameters())
    assert encode_module_checkpoint(native.network).model_digest == model


def test_live_model_modification_is_rejected_before_execution(native, program):
    executor = _executor(native, program)
    before = native.store.head
    with torch.no_grad():
        next(native.network.parameters()).add_(0.125)
    with pytest.raises(MetaRuntimeError, match="MODEL_CHANGED"):
        executor.step()
    assert native.store.head == before
    assert not native.store.trace_events()


def test_native_head_changed_by_another_owner_is_rejected(native, program):
    executor = _executor(native, program)
    cause, artifact = initial_input(native)
    native.inference_tick(cause=cause, cjt_id="A", expected_symbol="L1", supplied_artifacts=(artifact,))
    head = native.store.head
    with pytest.raises(MetaRuntimeError, match="NATIVE_HEAD_MISMATCH"):
        executor.step()
    assert native.store.head == head
    assert len(native.store.trace_events()) == 1
    assert executor.spent == 0


@pytest.mark.parametrize("change", ["program", "chain", "limits", "scope", "checkpoint"])
def test_restart_rejects_changed_identity_or_receipt(native, program, source, tmp_path, change):
    executor = _executor(native, program)
    executor.step()
    path = tmp_path / "bound-checkpoint.json"
    receipt = executor.checkpoint(path)
    arguments = {"expected_digest": receipt, "chain_id": "fixed-chain", "limits": Limits()}
    selected_program = program
    code = "RUNTIME_BINDING_MISMATCH"
    if change == "program":
        altered = deepcopy(source)
        altered["procedures"]["main"]["body"]["steps"][1]["allowance"] = 399
        selected_program = compile_program(altered)
    elif change == "chain":
        arguments["chain_id"] = "different-chain"
    elif change == "limits":
        arguments["limits"] = Limits(budget=513)
    elif change == "scope":
        arguments["permitted_cjts"] = ("A", "B", "C")
        code = "CJT_SCOPE_DENIED"
    else:
        path.write_bytes(path.read_bytes() + b"\n")
        code = "CHECKPOINT_RECEIPT_MISMATCH"
    head = native.store.head
    with pytest.raises(MetaRuntimeError, match=code):
        Executor.restore(native, selected_program, path, **arguments)
    assert native.store.head == head


@pytest.mark.parametrize("field", ["parent_id", "return_pc"])
def test_wrong_active_child_caller_or_return_address_fails_closed(native, program, field):
    executor = _executor(native, program)
    executor.step()
    executor.step()
    assert len(executor.frames) == 2
    head = native.store.head
    # Deliberate internal corruption tests an invariant, not a Python sandbox.
    setattr(executor._frames[-1], field, "wrong-caller" if field == "parent_id" else 999)
    with pytest.raises(MetaRuntimeError, match="CALLER_MISMATCH"):
        executor.step()
    assert native.store.head == head
    assert len(native.store.trace_events()) == 1


def test_depth_limit_preserves_prior_durable_steps_and_charges(native, program):
    executor = _executor(native, program, limits=Limits(max_depth=2))
    _advance_to_trace_count(executor, 2)
    with pytest.raises(MetaRuntimeError, match="CALL_DEPTH_EXCEEDED"):
        executor.step()
    assert len(native.store.trace_events()) == 3
    assert executor.spent == 216
    assert native.state.by_cjt_id["C"].rpm.open_repair_ids
    assert native.store.verify_integrity()


def test_meta_step_limit_stops_before_further_native_work(native, program):
    executor = _executor(native, program, limits=Limits(max_steps=2))
    executor.step()
    executor.step()
    before = asdict(native.store.head)
    with pytest.raises(MetaRuntimeError, match="META_STEP_LIMIT"):
        executor.step()
    assert asdict(native.store.head) == before
    assert len(native.store.trace_events()) == 1
    assert executor.spent == 72


@pytest.mark.parametrize("change", ["model", "head"])
def test_completed_executor_rechecks_model_and_head_before_returning_result(native, change):
    one_step = compile_program({
        "version": "cas-meta/0.1", "entry": "main", "procedures": {
            "main": {
                "input_type": "IDEA", "output_type": "EFFECT", "allowed_cjts": ["A"],
                "body": {"kind": "run", "cjt": "A", "operation": "^6", "expected": "L1"},
            }
        }
    })
    executor = _executor(native, one_step)
    effect_id = executor.run()
    assert executor.done
    assert executor.run() == effect_id  # Unchanged completed state is repeatable.
    if change == "model":
        with torch.no_grad():
            next(native.network.parameters()).add_(0.125)
        code = "MODEL_CHANGED"
    else:
        next_cause = native.cause_from_effect(
            effect_id, tick=native.store.next_tick(), candidate_operation_ids=("^6",),
            goal_context={"goal": "verified four-CJT chain"},
        )
        native.inference_tick(cause=next_cause, cjt_id="B", expected_symbol="L3")
        code = "NATIVE_HEAD_MISMATCH"
    head = native.store.head
    with pytest.raises(MetaRuntimeError, match=code):
        executor.run()
    with pytest.raises(MetaRuntimeError, match=code):
        executor.validate_evidence()
    assert native.store.head == head
    assert executor.spent == 72


def test_independent_invocations_have_unique_call_ids_even_with_same_chain(native, program):
    first = _executor(native, program, chain_id="shared-chain-label")
    second = _executor(native, program, chain_id="shared-chain-label")
    first_frame, second_frame = first.frames[0], second.frames[0]
    assert first.chain_id == second.chain_id
    assert first_frame["procedure"] == second_frame["procedure"]
    assert first_frame["path"] == second_frame["path"]
    assert first_frame["call_id"] != second_frame["call_id"]
    assert not native.store.trace_events()


def test_oversized_checkpoint_cannot_replace_previous_valid_checkpoint(native, program, tmp_path, monkeypatch):
    import cas_meta.executor as executor_module

    executor = _executor(native, program)
    executor.step()
    path = tmp_path / "preserved-checkpoint.json"
    receipt = executor.checkpoint(path)
    original_bytes = path.read_bytes()
    serializer = executor_module.canonical_json

    def oversized_checkpoint(value):
        encoded = serializer(value)
        if isinstance(value, dict) and value.get("schema") == "cas-meta-checkpoint/0.1":
            return encoded + " " * (16 * 1024 * 1024)
        return encoded

    # Test the write-size guard, without changing native or frame state.
    monkeypatch.setattr(executor_module, "canonical_json", oversized_checkpoint)
    with pytest.raises(MetaRuntimeError, match="CHECKPOINT_TOO_LARGE"):
        executor.checkpoint(path)
    assert path.read_bytes() == original_bytes
    assert not list(tmp_path.glob(".meta-checkpoint-*"))
    restored = Executor.restore(
        native, program, path, expected_digest=receipt, chain_id="fixed-chain", limits=Limits()
    )
    assert restored.frames == executor.frames


def test_restart_rejects_stale_checkpoint_without_undoing_durable_b(program, tmp_path):
    database = tmp_path / "stale-checkpoint.db"
    runtime = create_native(database)
    try:
        executor = _executor(runtime, program)
        executor.step()  # A is durable; the checkpoint is valid for this head.
        checkpoint = tmp_path / "after-a.json"
        receipt = executor.checkpoint(checkpoint)
        checkpoint_head = runtime.store.head
        _advance_to_trace_count(executor, 2)  # Enter worker, then commit B.
        durable_head = runtime.store.head
        durable_state = runtime.state
        published_b = runtime.store.trace_events()[-1]["published_effect_ids"]
        assert published_b and durable_head != checkpoint_head
        assert durable_state.by_cjt_id["B"].memory.recurrent_state_ref is not None
    finally:
        runtime.close()

    reopened = open_native(database)
    try:
        with pytest.raises(MetaRuntimeError, match="NATIVE_HEAD_MISMATCH"):
            Executor.restore(
                reopened, program, checkpoint, expected_digest=receipt,
                chain_id="fixed-chain", limits=Limits(),
            )
        assert reopened.store.head == durable_head
        assert reopened.state == durable_state
        assert len(reopened.store.trace_events()) == 2
        assert reopened.store.trace_events()[-1]["published_effect_ids"] == published_b
        assert reopened.store.immutable_document("published_effects", published_b[0])
        assert reopened.store.verify_integrity()
    finally:
        reopened.close()
