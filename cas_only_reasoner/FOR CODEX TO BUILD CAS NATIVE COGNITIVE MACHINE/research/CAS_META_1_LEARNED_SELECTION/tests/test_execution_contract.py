"""Static contracts run locally. Real native cases require an explicit GPU gate."""

import ast
from copy import deepcopy
import inspect
import json
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest

from cas_meta1 import execution as ex


def public_task():
    return {"problem": "Repair and resume the beta observation.", "observations": [
        {"slot": slot, "tag": tag,
         "values": [0.1 * (index + 1) + slot * 0.0001 for index in range(8)]}
        for slot, tag in enumerate(("alpha", "beta", "gamma"))]}


def task(procedure=2, binding=1):
    return {"id": "contract-only-example", "public": public_task(),
            "target": {"procedure": procedure, "binding": binding, "expected": {
                "workflow": list(ex.WORKFLOWS[procedure]),
                "final_symbol": ex.FINAL_SYMBOLS[procedure], "repair_required": procedure == 2}},
            "provenance": {"scope": "authored integration-test fixture"}}


@pytest.mark.parametrize("procedure", [0, 1, 2])
@pytest.mark.parametrize("binding", [0, 1, 2])
def test_pure_public_action_contract(procedure, binding):
    assert ex.validate_action(public_task(), {"procedure": procedure, "binding": binding}) is None


@pytest.mark.parametrize("bad_action", [None, [], {}, {"procedure": 0},
    {"procedure": 0, "binding": 0, "gold": 2}, {"procedure": -1, "binding": 0},
    {"procedure": 3, "binding": 0}, {"procedure": True, "binding": 0},
    {"procedure": 0, "binding": 0.0}, {"procedure": 0, "binding": float("nan")}])
def test_invalid_action_is_countable_rejection_without_neural_setup(monkeypatch, bad_action):
    def forbidden():
        raise AssertionError("invalid action reached frozen neural setup")
    monkeypatch.setattr(ex, "_frozen", forbidden)
    result = ex.execute_task(public_task(), bad_action, "unused")
    assert result["status"] == "REJECTED" and result["failure"]["code"]
    json.dumps(result, allow_nan=False)
    assert not ex.verify_task(task(), result, {})["success"]


@pytest.mark.parametrize("mutation", ["gold", "duplicate_slot", "duplicate_values", "nan", "shape"])
def test_closed_public_shape(mutation):
    value = public_task()
    if mutation == "gold":
        value["target"] = {"procedure": 2}
    elif mutation == "duplicate_slot":
        value["observations"][1]["slot"] = 0
    elif mutation == "duplicate_values":
        value["observations"][1]["values"] = list(value["observations"][0]["values"])
    elif mutation == "nan":
        value["observations"][0]["values"][0] = float("nan")
    else:
        value["observations"][0]["values"].pop()
    assert ex.validate_action(value, {"procedure": 2, "binding": 1}) is not None


def test_three_programs_compile_without_running_any_neural_module():
    from cas_meta.compiler import compile_program
    programs = [compile_program((ex.ROOT / "programs" / name).read_text(encoding="utf-8"))
                for name in ex.PROGRAM_FILES]
    assert [len(program.procedures) for program in programs] == [1, 2, 3]
    assert len({program.digest for program in programs}) == 3
    assert all(step.operation == "^6" for program in programs for proc in program.procedures
               for step in proc.steps if step.kind == "run")
    assert programs[1].by_name["main"].steps[-1].kind == "call"
    assert programs[2].by_name["worker"].steps[-1].repair == "repair_c"


def test_candidate_entry_point_has_no_gold_input_and_reference_is_direct():
    assert list(inspect.signature(ex.execute_task).parameters) == ["public", "action", "output_dir", "device"]
    tree = ast.parse(inspect.getsource(ex._direct_reference))
    used = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "inference_tick" in used
    assert not {"Executor", "compile_program", "execute_task"} & used
    assert "PROGRAM_FILES" not in inspect.getsource(ex._direct_reference)


def test_whole_network_ids_are_not_mistaken_for_the_tick_producer():
    traces = [{"cjt_ids": ["A", "B", "C", "R"],
               "candidate_effects": [{"producer_cjt_id": name}]} for name in ("A", "B")]
    assert ex._workflow(traces) == ["A", "B"]


def test_trace_valid_alone_cannot_pass_task_verification():
    result = {"status": "EXECUTED", "trace_valid": True,
              "selected_action": {"procedure": 2, "binding": 1}}
    verdict = ex.verify_task(task(), result, {"status": "REJECTED"})
    assert not verdict["success"] and not verdict["evidence_valid"]


@pytest.mark.parametrize("which", ["BASELINE", "INSTALLED_WHEELS"])
@pytest.mark.parametrize("failure", [RuntimeError, OSError])
def test_protected_identity_failures_abort_instead_of_counting_as_model_error(which, failure):
    def good():
        return {"verified": True}

    def bad():
        raise failure("IDENTITY_FAILURE_FIXTURE")

    checks = (bad, good) if which == "BASELINE" else (good, bad)
    with pytest.raises(ex.ExecutionInfrastructureError,
                       match=f"FROZEN_{which}_IDENTITY_CHECK_FAILED") as caught:
        ex._verify_protected_identity(*checks)
    assert isinstance(caught.value.__cause__, failure)


def test_source_snapshot_failure_is_a_pilot_abort_without_neural_setup(monkeypatch):
    def unavailable(name):
        raise OSError("SOURCE_FILE_UNREADABLE")

    monkeypatch.setattr(ex.importlib, "import_module", unavailable)
    with pytest.raises(ex.ExecutionInfrastructureError,
                       match="FROZEN_MODULE_SOURCE_IDENTITY_UNAVAILABLE"):
        ex._source_snapshot()


def test_parameter_identity_failure_is_a_pilot_abort_without_a_model():
    def unavailable(network):
        raise RuntimeError("CHECKPOINT_UNREADABLE")

    with pytest.raises(ex.ExecutionInfrastructureError,
                       match="FROZEN_NATIVE_PARAMETER_IDENTITY_UNAVAILABLE"):
        ex._model_identity(SimpleNamespace(network=object()),
                           SimpleNamespace(encode_module_checkpoint=unavailable))


def test_frozen_executor_plan_mismatch_aborts_without_neural_execution():
    from cas_meta.executor import MetaRuntimeError
    error = MetaRuntimeError("NATIVE_PLAN_MISMATCH")
    with pytest.raises(ex.ExecutionInfrastructureError, match="^NATIVE_PLAN_MISMATCH$") as caught:
        ex._runtime_rejection(error, {"procedure": 2, "binding": 1})
    assert caught.value.__cause__ is error


def test_ordinary_runtime_error_remains_a_countable_rejection():
    result = ex._runtime_rejection(ValueError("TASK_REJECTED"), {"procedure": 2, "binding": 1})
    assert result["status"] == "REJECTED"
    assert result["failure"]["code"] == "RUNTIME_EXECUTION_REJECTED"


GPU_ONLY = pytest.mark.skipif(os.environ.get("CAS_META1_RUN_GPU_TESTS") != "1",
                              reason="AWS-only explicit GPU integration gate; no local neural probes")


@pytest.mark.gpu
@GPU_ONLY
@pytest.mark.parametrize("procedure", [0, 1, 2])
def test_gpu_authored_execution_matches_independent_reference(procedure):
    base = ex.ROOT / "runs" / "gpu-contract-tests" / uuid4().hex
    case = task(procedure)
    result = ex.execute_task(deepcopy(case["public"]), {"procedure": procedure, "binding": 1}, base / "candidate")
    reference = ex.reference_task(case, base / "reference")
    assert result["status"] == reference["status"] == "EXECUTED", (result, reference)
    assert ex.verify_task(case, result, reference)["success"]
    assert result["gpu_forward_audit"]["calls"] > 0
    assert result["gpu_forward_audit"]["device"].startswith("cuda:")
    assert result["reserved_policy_units"] == 72 * len(ex.WORKFLOWS[procedure])
    assert result["frozen_parameter_bytes_sha256_before"] == result["frozen_parameter_bytes_sha256_after"]


@pytest.mark.gpu
@GPU_ONLY
def test_gpu_wrong_binding_and_wrong_procedure_are_wrong_despite_valid_traces():
    base = ex.ROOT / "runs" / "gpu-contract-tests" / uuid4().hex
    case = task(2, 1)
    reference = ex.reference_task(case, base / "reference")
    wrong_binding = ex.execute_task(case["public"], {"procedure": 2, "binding": 0}, base / "wrong-binding")
    wrong_procedure = ex.execute_task(case["public"], {"procedure": 1, "binding": 1}, base / "wrong-procedure")
    assert wrong_binding["trace_valid"] and wrong_procedure["trace_valid"]
    assert not ex.verify_task(case, wrong_binding, reference)["binding_correct"]
    assert not ex.verify_task(case, wrong_procedure, reference)["procedure_correct"]
    assert not ex.verify_task(case, wrong_binding, reference)["success"]
    assert not ex.verify_task(case, wrong_procedure, reference)["success"]
    assert wrong_binding["input_tensor_bytes_sha256"] != reference["input_tensor_bytes_sha256"]
