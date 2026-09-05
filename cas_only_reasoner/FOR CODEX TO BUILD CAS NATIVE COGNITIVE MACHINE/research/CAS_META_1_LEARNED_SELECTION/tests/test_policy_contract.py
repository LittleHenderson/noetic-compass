"""Non-neural contract checks only: never construct or execute a model locally."""

import ast
from copy import deepcopy
from pathlib import Path

import pytest

from cas_meta1.policy import (PolicyConfig, PolicyContractError, PublicTokenizer,
                             require_cuda, validate_public)


ROOT = Path(__file__).resolve().parents[1]


def sample_public():
    return {"problem": "Inspect the amber record.", "observations": [
        {"slot": slot, "tag": tag, "values": [float(slot)] * 8}
        for slot, tag in enumerate(("amber", "blue", "copper"))]}


def test_tokenizer_is_train_only_and_does_not_mutate_public():
    public = sample_public()
    original = deepcopy(public)
    tokenizer = PublicTokenizer.fit_train([public])
    unseen = deepcopy(public)
    unseen["problem"] = "unseentransferword"
    before = tokenizer.digest
    encoded = tokenizer.encode_public(unseen)
    assert 1 in encoded["ids"]
    assert "unseentransferword" not in tokenizer.vocabulary
    assert before == tokenizer.digest
    assert public == original
    assert tokenizer.to_dict()["fit_split"] == "train_only"


@pytest.mark.parametrize("key", ["id", "target", "provenance", "gold", "expected", "procedure", "binding"])
def test_selector_rejects_extra_fields(key):
    public = sample_public()
    public[key] = "hidden"
    with pytest.raises(PolicyContractError, match="PUBLIC_INPUT_FIELDS_INVALID"):
        validate_public(public)


def test_full_task_is_not_a_permitted_selector_input():
    task = {"id": "x", "public": sample_public(), "target": {"procedure": 0, "binding": 0}}
    with pytest.raises(PolicyContractError):
        PublicTokenizer.fit_train([task])


def test_observations_are_bound_by_public_slot_not_list_order():
    public = sample_public()
    tokenizer = PublicTokenizer.fit_train([public])
    changed = deepcopy(public)
    changed["observations"].reverse()
    assert tokenizer.encode_public(public) == tokenizer.encode_public(changed)


def test_numeric_values_reach_shared_input_features():
    public = sample_public()
    tokenizer = PublicTokenizer.fit_train([public])
    changed = deepcopy(public)
    changed["observations"][1]["values"][0] = 4.25
    first, second = tokenizer.encode_public(public), tokenizer.encode_public(changed)
    assert first["ids"] == second["ids"]
    assert first["values"] != second["values"]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), True, "1"])
def test_bad_numeric_public_rejected(bad):
    public = sample_public()
    public["observations"][0]["values"][0] = bad
    with pytest.raises(PolicyContractError, match="PUBLIC_VALUES_INVALID"):
        validate_public(public)


def test_public_slot_coverage_rejects_duplicates():
    public = sample_public()
    public["observations"][2]["slot"] = 1
    with pytest.raises(PolicyContractError, match="PUBLIC_SLOT_COVERAGE_INVALID"):
        validate_public(public)


def test_no_silent_token_truncation():
    public = sample_public()
    tokenizer = PublicTokenizer.fit_train([public])
    public["problem"] = "word " * 200
    with pytest.raises(PolicyContractError, match="NO_SILENT_TRUNCATION"):
        tokenizer.encode_public(public)


def test_cpu_guard_fails_before_cuda_probe(monkeypatch):
    def forbidden():
        raise AssertionError("CPU request must fail before even probing CUDA")
    monkeypatch.setattr("cas_meta1.policy.torch.cuda.is_available", forbidden)
    with pytest.raises(RuntimeError, match="NO_CPU_FALLBACK"):
        require_cuda("cpu")


def test_missing_cuda_guard_no_forward(monkeypatch):
    monkeypatch.setattr("cas_meta1.policy.torch.cuda.is_available", lambda: False)
    with pytest.raises(RuntimeError, match="CUDA_UNAVAILABLE"):
        require_cuda("cuda")


def test_fixed_architecture_defaults_and_static_source_parse():
    config = PolicyConfig()
    config.validate()
    assert (config.d_model, config.heads, config.layers) == (32, 4, 2)
    assert config.max_parameter_mismatch_fraction == 0.01
    for name in ("policy.py", "train.py"):
        ast.parse((ROOT / "cas_meta1" / name).read_text(encoding="utf-8"))


def test_test_gold_read_is_after_sealed_predictions_static():
    tree = ast.parse((ROOT / "cas_meta1" / "train.py").read_text(encoding="utf-8"))
    run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run")
    statements = list(ast.walk(run))
    reads = [node for node in statements if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == "test_tasks" for target in node.targets)]
    seals = [node for node in statements if isinstance(node, ast.Constant) and node.value == "predictions_seal.json"]
    cuda_gates = [node for node in statements if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name) and node.func.id == "require_cuda"]
    builders = [node for node in statements if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name) and node.func.id == "build_matched_policies"]
    assert len(reads) == 1 and len(seals) == 1 and reads[0].lineno > seals[0].lineno
    assert min(node.lineno for node in cuda_gates) < min(node.lineno for node in builders)


def test_parameter_matching_has_no_padding_parameter_escape():
    source = (ROOT / "cas_meta1" / "policy.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    matching = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build_matched_policies")
    assert "ff_width" in source
    assert not any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr in ("Parameter", "register_parameter") for node in ast.walk(matching))
