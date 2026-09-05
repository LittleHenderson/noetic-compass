"""AST-only native-adapter checks. No imports or execution of native.py.

These tests prove code-shape contracts only. They are not CUDA compatibility,
native execution, checkpoint retention, or observed task-correctness evidence.
"""

import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.not_gpu
PATH = Path(__file__).resolve().parents[1] / "cas_meta2" / "native.py"


@pytest.fixture(scope="module")
def tree():
    return ast.parse(PATH.read_text(encoding="utf-8"))


def function(tree, name, owner=None):
    nodes = tree.body
    if owner:
        nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == owner).body
    return next(n for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)


def calls(node, ending):
    return sorted((n for n in ast.walk(node) if isinstance(n, ast.Call)
                   and ((isinstance(n.func, ast.Attribute) and n.func.attr == ending)
                        or (isinstance(n.func, ast.Name) and n.func.id == ending))), key=lambda n: n.lineno)


def strings(node):
    return {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def source(node):
    return ast.unparse(node)


def test_static_module_does_not_import_neural_libraries_at_top_level(tree):
    for node in tree.body:
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith(("torch", "casformer", "cas_cjt")) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith(("torch", "casformer", "cas_cjt", "cas_meta1"))
    assert calls(function(tree, "_frozen"), "_frozen")


def test_static_cuda_admission_precedes_output_and_backend_construction(tree):
    run = function(tree, "_run")
    admission = calls(run, "admit_action")[0].lineno
    cuda = calls(run, "_cuda")[0].lineno
    mkdir = calls(run, "mkdir")[0].lineno
    backend = calls(run, "NativeBackend")[0].lineno
    assert admission < cuda < mkdir < backend
    init = function(tree, "__init__", "NativeBackend")
    assert calls(init, "_cuda")[0].lineno < calls(init, "create_native")[0].lineno
    assert not any(n.value == "cpu" for n in ast.walk(tree) if isinstance(n, ast.Constant))


def test_static_all_explicit_tensor_construction_uses_admitted_device(tree):
    tensors = calls(tree, "tensor")
    assert tensors
    for call in tensors:
        device = next(keyword.value for keyword in call.keywords if keyword.arg == "device")
        assert source(device) == "self.device"
    init = function(tree, "__init__", "NativeBackend")
    assert calls(init, "_gpu_forward_guards")
    requires_grad = calls(init, "requires_grad_")
    assert len(requires_grad) == 1 and isinstance(requires_grad[0].args[0], ast.Constant)
    assert requires_grad[0].args[0].value is False


def test_static_no_learning_optimizer_or_model_loading_path(tree):
    forbidden = {"learning_tick", "backward", "optimizer", "Adam", "AdamW", "SGD", "load_state_dict"}
    assert not any(calls(tree, name) for name in forbidden)
    assert calls(function(tree, "execute", "NativeBackend"), "no_grad")
    expected = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "EXPECTED" for t in n.targets))
    assert ast.literal_eval(expected) == {"A": "L1", "B": "L3", "C": "L2", "R": "L1"}


def test_static_public_execution_has_no_gold_entrypoint(tree):
    entry = function(tree, "execute_task")
    assert [a.arg for a in entry.args.args] == ["public", "action", "output_dir", "device"]
    assert "target" not in strings(entry)
    call = calls(entry, "_run")[0]
    assert next(k.value.value for k in call.keywords if k.arg == "reference") is False
    private = function(tree, "reference_task")
    assert "target" in strings(private)
    assert next(k.value.value for k in calls(private, "_run")[0].keywords if k.arg == "reference") is True


def test_static_admission_checks_observation_ambiguity_and_native_topology(tree):
    admission = function(tree, "admit_action")
    for required in ("validate_public", "validate_action", "validate_program", "check_native_topology", "pack"):
        assert calls(admission, required)
    assert {"INVALID_OR_AMBIGUOUS_OBSERVATIONS", "AMBIGUOUS_OBSERVATION_PAYLOADS",
            "ACCEPTED_EFFECT_RESULT_REQUIRED"} <= strings(admission)


def test_static_effect_refs_resolve_immutable_documents_and_artifact_bytes(tree):
    effect = function(tree, "_effect_reference", "NativeBackend")
    for required in ("immutable_document", "load_artifact", "verify"):
        assert calls(effect, required)
    assert {"published_effects", "producer_cjt_id", "payload_sha256"} <= strings(effect)
    validate = function(tree, "validate_reference", "NativeBackend")
    assert calls(validate, "input_reference") and calls(validate, "_effect_reference")
    assert "reference != expected" in source(validate)
    assert {"FORGED_VALUE_REFERENCE", "UNRESOLVED_VALUE_REFERENCE"} <= strings(validate)


def test_static_source_model_head_and_scope_rechecked_at_native_boundary(tree):
    identity = function(tree, "identity", "NativeBackend")
    assert calls(identity, "_source_snapshot") and calls(identity, "_model_identity")
    assert "FROZEN_MODULE_SOURCE_CHANGED" in strings(identity)
    prepare = function(tree, "prepare", "NativeBackend")
    assert calls(prepare, "select_candidates")
    assert "NATIVE_TOPOLOGY_MISMATCH" in strings(prepare)
    execute = function(tree, "execute", "NativeBackend")
    assert {"PREPARED_PLAN_MISMATCH", "PREPARED_BOUNDARY_CHANGED", "FROZEN_RUNTIME_IDENTITY_CHANGED",
            "CROSS_CJT_BIAS_CHANGED", "UNEXPECTED_NATIVE_TICK_COUNT"} <= strings(execute)
    assert calls(execute, "head")[0].lineno < calls(execute, "inference_tick")[0].lineno


def test_static_candidate_runs_accepted_executor_and_private_path_is_independent(tree):
    execute = function(tree, "execute", "NativeBackend")
    assert calls(execute, "Executor")
    assert calls(execute, "compile_program")
    assert calls(execute, "inference_tick")
    assert {"cas-meta/0.1", "^6", "run"} <= strings(execute)
    private = function(tree, "_private_execute")
    assert not calls(private, "CompositionExecutor")
    assert not calls(private, "expand_program")
    assert calls(private, "prepare") and calls(private, "execute") and calls(private, "visit")


def test_static_receipts_bind_stored_plan_digest_and_all_five_unit_fields(tree):
    validate = function(tree, "validate_receipt", "NativeBackend")
    assert {"compute_plan", "plan_digest", "units", "receipt_id", "trace_id", "published_effect_ids",
            "route_quanta", "reasoning_step_quanta", "branch_quanta", "memory_read_quanta",
            "diagnostic_probe_quanta", "NATIVE_RECEIPT_PLAN_MISMATCH"} <= strings(validate)
    assert calls(validate, "receipt_by_id") and calls(validate, "trace_events")
    assert calls(validate, "validate_contract") and calls(validate, "digest")


def test_static_stored_examination_is_read_only_and_checks_artifact_headers(tree):
    stored = function(tree, "_stored")
    assert "?mode=ro&immutable=1" in strings(stored)
    assert calls(stored, "StoredArtifact") and calls(stored, "verify")
    assert not calls(stored, "decode_tensor")
    assert {"STORED_EVIDENCE_HASH_MISMATCH", "UNKNOWN_OR_FUTURE_EFFECT_PARENT",
            "FORGED_FINAL_EFFECT_REFERENCE", "PAYLOAD_REFERENCE_MISMATCH"} <= strings(stored)
    assert calls(stored, "close")


def test_static_correctness_checks_every_output_and_dependency_not_only_final_label(tree):
    verify = function(tree, "verify_task")
    required = {"procedure_correct", "binding_correct", "dependency_correct", "actual_output_correct", "trace_valid"}
    assert required <= strings(verify)
    assert "actual['rows'] == private['rows']" in source(verify)
    assert "actual['return_node'] == private['return_node']" in source(verify)
    assert "PRIVATE_REFERENCE_OR_FROZEN_IDENTITY_MISMATCH" in strings(verify)
    assert "PRIVATE_REFERENCE_INPUT_MISMATCH" in strings(verify)
    assert calls(verify, "all")


def test_static_close_retains_frozen_source_and_parameter_checks(tree):
    close = function(tree, "close", "NativeBackend")
    assert {"FROZEN_NATIVE_PARAMETERS_CHANGED", "FROZEN_MODULE_SOURCE_CHANGED"} <= strings(close)
    assert calls(close, "_verify_protected_identity")
    assert calls(close, "close") and calls(close, "remove")
