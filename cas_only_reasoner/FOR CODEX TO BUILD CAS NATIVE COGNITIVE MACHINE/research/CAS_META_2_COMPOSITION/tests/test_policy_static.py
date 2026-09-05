"""Source-contract tests only: never import torch or construct a model."""

import ast
from pathlib import Path
import pytest

pytestmark = pytest.mark.not_gpu


POLICY = Path(__file__).resolve().parents[1] / "cas_meta2" / "policy.py"
TREE = ast.parse(POLICY.read_text(encoding="utf-8"))


def function(name):
    return next(node for node in ast.walk(TREE)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)


def called_names(node):
    return {item.func.id for item in ast.walk(node)
            if isinstance(item, ast.Call) and isinstance(item.func, ast.Name)}


def test_every_model_constructor_guards_cuda_before_initialization():
    classes = [node for node in TREE.body if isinstance(node, ast.ClassDef)
               and node.name in ("_ProgramGenerator", "CASProgramGenerator", "GenericProgramGenerator")]
    assert len(classes) == 3
    for cls in classes:
        constructor = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "__init__")
        first = constructor.body[0]
        assert isinstance(first, ast.Assign)
        assert isinstance(first.value, ast.Call)
        assert first.value.func.id == "require_cuda"


def test_tensor_entry_points_require_cuda():
    for name in ("encode_batch", "encode_targets", "build_matched_policies", "predict_public"):
        assert "require_cuda" in called_names(function(name))


def test_prediction_has_no_gold_or_program_catalog_input():
    node = function("predict_public")
    assert [value.arg for value in node.args.args] == ["model", "tokenizer", "publics"]
    forbidden = {"encode_targets", "action_to_ids", "reference_task", "verify_task", "rule_select", "compile_program"}
    assert not called_names(node).intersection(forbidden)
    assert "ids_to_action" in called_names(node)
    assert "encode_batch" in called_names(node)


def test_decoder_is_causal_and_program_token_based():
    text = ast.get_source_segment(POLICY.read_text(encoding="utf-8"), function("decode"))
    assert "tgt_mask=causal" in text
    assert "torch.triu" in text and "diagonal=1" in text
    assert "binding_query" in text and "binding_key" in text
    assert "procedure_logits" not in POLICY.read_text(encoding="utf-8")


def test_no_cpu_fallback_and_no_program_length_truncation():
    text = POLICY.read_text(encoding="utf-8")
    assert "NO_CPU_FALLBACK" in text
    assert "NO_SILENT_TRUNCATION" in text
    assert "GENERATION_LENGTH_EXHAUSTED" in text
    assert ".cpu()" not in text


def test_encoder_matching_uses_real_feedforward_dimensions():
    text = ast.get_source_segment(POLICY.read_text(encoding="utf-8"), function("build_matched_policies"))
    assert "slope = config.layers * (2 * config.d_model + 1)" in text
    assert "ACTIVE_PARAMETER_MATCH_FAILED" in text
    assert "nn.Parameter(" not in text


def test_initial_gate_range_scales_without_changing_drive_or_current():
    text = POLICY.read_text(encoding="utf-8")
    assert "cas_initial_saturation_per_max_token: float = 2.0" in text
    assert "config.cas_initial_saturation_per_max_token" in text
    assert "* config.max_length" in text
    assert "initial_saturation=4.0" not in text
    inputs = ast.get_source_segment(text, function("_encoder_inputs"))
    assert "controls.drive" not in inputs
    assert "total_current" not in inputs
    assert "frozen_candidate_parameter_names" in text


def test_four_gpu_tests_cover_real_default_batch_and_absolute_flow():
    gpu_path = POLICY.parents[1] / "tests" / "test_policy_gpu.py"
    source = gpu_path.read_text(encoding="utf-8")
    gpu_tree = ast.parse(source)
    assert sum(isinstance(node, ast.FunctionDef) and node.name.startswith("test_") for node in gpu_tree.body) == 4
    assert "default_longest_training_batch16" in source
    assert "reverse=True)[:16]" in source
    assert "default_tokenizer, PolicyConfig()" in source
    assert "active_fraction >= 0.95" in source
    assert "total_current_halved" in source and "relative_attention_unchanged" in source
