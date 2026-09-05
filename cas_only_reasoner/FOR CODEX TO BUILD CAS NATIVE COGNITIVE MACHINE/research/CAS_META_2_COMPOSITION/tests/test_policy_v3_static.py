"""Read source without importing a policy/model or constructing tensors."""
import ast
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).parents[1]
POLICY = ROOT / "cas_meta2" / "policy_v3.py"


def source():
    return POLICY.read_text(encoding="utf-8")


def test_frozen_policy_bytes_unchanged():
    assert sha256((ROOT / "cas_meta2" / "policy.py").read_bytes()).hexdigest() == "6d5f3cbfc455c65ef9000c5145f8f5b691668fb355339eeebd61e4aa2b8d26d0"


def test_features_import_only_pure_codec_and_frozen_lossless_tokenizer():
    tree = ast.parse((ROOT / "cas_meta2" / "features_v3.py").read_text())
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports == {"__future__", "codec", "features_v2"}
    assert {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names} == {"re"}
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert [arg.arg for arg in functions["encode_public_with_spans"].args.args] == ["public", "tokenizer"]


def test_policy_reuses_same_frozen_encoders_and_common_copy_implementation():
    tree = ast.parse(source())
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    assert [base.id for base in classes["CASProgramGenerator"].bases] == ["_LexicalCopy", "FrozenCASProgramGenerator"]
    assert [base.id for base in classes["GenericProgramGenerator"].bases] == ["_LexicalCopy", "FrozenGenericProgramGenerator"]
    for name in ("CASProgramGenerator", "GenericProgramGenerator"):
        assert {node.name for node in classes[name].body if isinstance(node, ast.FunctionDef)} == {"__init__"}


def test_no_disconnected_matching_parameters_or_cpu_fallback():
    text = source()
    assert "nn.Parameter(" not in text and ".requires_grad_(False)" not in text
    assert 'device="cpu"' not in text and '.cpu(' not in text
    assert "slope = config.layers * (2 * config.d_model + 1)" in text
    assert "parameter.copy_(original)" in text
    assert "mismatch > config.max_parameter_mismatch_fraction" in text


def test_observation_pointer_remains_in_actual_fixed_logits():
    text = source()
    assert 'self.binding_query(hidden)' in text and 'self.binding_key(torch.stack(slot_states, dim=1))' in text
    assert 'logits[:, :, list(BINDING_TOKEN_IDS)] += pointer' in text
    assert 'fixed_log_probabilities = torch.log_softmax(fixed_logits, -1)' in text


def test_copy_uses_complete_mean_spans_and_repeated_destination_aggregation():
    text = source()
    assert 'weights / weights.sum(-1, keepdim=True).clamp_min(1.0)' in text
    assert 'torch.bmm(weights, memory)' in text
    assert 'F.one_hot(safe_ids, num_classes=len(ACTION_VOCABULARY))' in text
    assert 'torch.bmm(occurrence_probabilities, destinations)' in text
    assert 'torch.where(has_occurrences, mixed, fixed_log_probabilities)' in text
    tree = ast.parse(text)
    assert not any(isinstance(node, ast.Attribute) and node.attr.startswith("scatter") for node in ast.walk(tree))


def test_generation_uses_one_grammar_for_all_models_without_problem_parser():
    tree = ast.parse(source())
    generation = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "predict_public")
    text = ast.get_source_segment(source(), generation)
    assert "GrammarState.from_ids([BOS_ID], max_length=model.config.max_action_length)" in text
    assert "state.allowed_ids()" in text and "advance_id(token_id)" in text
    assert "scores.masked_fill(~mask" in text
    assert "state.to_action()" in text
    assert "except (PolicyContractError, GrammarError)" in text
    assert not any(word in text for word in ("parse_problem", "expected_graph", "isinstance(model", "model.family", "target[", "task_id"))
    assert [arg.arg for arg in generation.args.args] == ["model", "tokenizer", "publics"]


def test_no_generation_target_encoder_or_native_executor_call():
    tree = ast.parse(source())
    generation = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "predict_public")
    names = {node.id for node in ast.walk(generation) if isinstance(node, ast.Name)}
    assert not names.intersection({"encode_targets", "action_to_ids", "NativeBackend", "verify_task", "parse_problem"})


def test_gpu_tests_guard_before_any_neural_import():
    text = (ROOT / "tests" / "test_policy_v3_gpu.py").read_text()
    assert text.index("pytest.skip(") < text.index("import torch")
    assert text.index('CAS_META2_AWS_JOB_ID') < text.index("import torch")
    assert "candidate_fixture_only" in text


def test_new_policy_explicitly_excluded_from_old_geometry_receipt():
    assert '"covered_by_frozen_v2_geometry_preflight": False' in source()


def test_rejected_token_evidence_comes_from_exact_prefix_not_batch_eos_padding():
    text = source()
    assert 'else [ACTION_TO_ID[token] for token in state.prefix]' in text
    assert 'row = ids[index].tolist()' not in text
