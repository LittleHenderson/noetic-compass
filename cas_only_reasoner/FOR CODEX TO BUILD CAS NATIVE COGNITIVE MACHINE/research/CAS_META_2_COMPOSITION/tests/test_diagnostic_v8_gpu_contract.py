"""Pure worker contracts only. CUDA/model/provider behavior remains unexecuted."""
import ast
from copy import deepcopy
import math
from pathlib import Path
import sys

import pytest

from cas_meta2.diagnostic_v8 import gpu


def test_module_import_does_not_import_neural_framework_or_provider():
    assert not {"torch", "casformer", "cas_cjt", "boto3", "botocore"}.intersection(
        key.split(".")[0] for key in sys.modules)


def test_laptop_refuses_before_any_plan_or_bundle_access(monkeypatch):
    monkeypatch.setattr(gpu.sys, "platform", "win32")
    with pytest.raises(ValueError, match="AWS_LINUX_EXPLICIT_ENABLE"):
        gpu.run("does-not-exist", "does-not-exist", job="x", expected_manifest_sha256="0"*64,
                plan_path="does-not-exist", expected_plan_sha256="0"*64)
    assert "torch" not in sys.modules


def test_exact_job_and_explicit_enable_required(monkeypatch):
    job = "cas-meta2-20260906120000-01234567"
    monkeypatch.setattr(gpu.sys, "platform", "linux")
    monkeypatch.delenv("CAS_META2_RUN_PREFIX_DIAGNOSTIC", raising=False)
    with pytest.raises(ValueError, match="EXPLICIT_ENABLE"):
        gpu.require_request(job)
    monkeypatch.setenv("CAS_META2_RUN_PREFIX_DIAGNOSTIC", "1")
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", job + "x")
    with pytest.raises(ValueError, match="EXACT_JOB"):
        gpu.require_request(job)
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", job)
    gpu.require_request(job)


def plan():
    return {"schema": gpu.PLAN_SCHEMA, "job": "cas-meta2-20260906120000-01234567",
            "bundle_manifest_sha256": "0"*64, "launch_enabled": True, "max_seconds": 1800,
            "batch_size": 16, "checkpoints": list(gpu.KEYS), "tasks_per_checkpoint": 120,
            "seed": 7, "source_sha": "0"*40, "instance_id": "i-" + "0"*17}


@pytest.mark.parametrize("field,value", [
    ("max_seconds", 1801), ("max_seconds", True), ("batch_size", 16.0),
    ("tasks_per_checkpoint", 120.0), ("seed", 7.0), ("launch_enabled", False),
    ("source_sha", "x"), ("instance_id", "i-x"), ("checkpoints", list(reversed(gpu.KEYS))),
])
def test_plan_scalar_bounds_fail_closed(field, value):
    value_plan = plan()
    value_plan[field] = value
    with pytest.raises(ValueError):
        gpu.plan_bounds(value_plan, plan()["job"], "0"*64)


def test_plan_geometry_pass_is_not_a_paid_launch_or_reservation():
    assert gpu.plan_bounds(plan(), plan()["job"], "0"*64) == plan()
    assert "torch" not in sys.modules


def test_raw_and_grammar_scores_have_separate_normalizers():
    score = gpu.score_choice([2.0, 0.0, 1.0], 2, [1, 2])
    assert score["raw_full_vocabulary"]["top1_token_id"] == 0
    assert score["raw_full_vocabulary"]["correct"] is False
    assert score["grammar_masked"]["top1_token_id"] == 2
    assert score["grammar_masked"]["correct"] is True
    assert score["grammar_masked"]["nll"] == pytest.approx(math.log1p(math.exp(-1)))
    assert score["raw_full_vocabulary"]["nll"] > score["grammar_masked"]["nll"]


def test_tie_break_is_lowest_token_id_and_singleton_is_explicit():
    score = gpu.score_choice([0.0, 0.0, 0.0], 2, [2, 1])
    assert score["grammar_masked"]["top1_token_id"] == 1
    singleton = gpu.score_choice([1000.0, -1000.0], 1, [1])
    assert singleton["single_option"] is True
    assert singleton["grammar_masked"]["nll"] == 0
    assert singleton["raw_full_vocabulary"]["nll"] == 2000


@pytest.mark.parametrize("scores,target,allowed", [
    ([float("nan"), 0], 0, [0]), ([float("inf"), 0], 0, [0]),
    ([0, 1], 0, []), ([0, 1], 0, [1]), ([0, 1], 0, [0, 0]),
    ([0, 1], True, [0, 1]), ([0, 1], 0, [0, True]), ([], 0, [0]),
])
def test_score_rejects_invalid_or_unavailable_expected_choices(scores, target, allowed):
    with pytest.raises(ValueError):
        gpu.score_choice(scores, target, allowed)


def payload_fixture():
    record = {"family": "cas", "epoch": 200, "optimizer_steps": 11200, "validation": {"tokens": 5}}
    registration = {"config": {"seed": 7}, "policy_config": {"max_length": 1024},
                    "source_sha256": {"a.py": "0"*64}, "data": {"manifest_sha256": "1"*64}}
    payload = {"schema": "cas-meta2-contrast-training/7", "family": "cas", "epoch": 200,
               "optimizer_steps": 11200, "validation": record["validation"], "training_config": registration["config"],
               "policy_config": registration["policy_config"], "source_sha256": registration["source_sha256"],
               "manifest_sha256": "1"*64, "tokenizer": {"vocabulary": ["a"]}, "action_vocabulary": ["x"],
               "accepted": False, "state_dict": {}, "optimizer_state_dict": {"state": {}, "param_groups": []}}
    return payload, record, registration


def test_all_checkpoint_metadata_bound_and_no_extra_fields():
    payload, record, registration = payload_fixture()
    gpu.checkpoint_metadata(payload, record, registration, {"vocabulary": ["a"]}, ["x"])
    for field in payload:
        altered = deepcopy(payload)
        altered[field] = None
        with pytest.raises(ValueError):
            gpu.checkpoint_metadata(altered, record, registration, {"vocabulary": ["a"]}, ["x"])
    altered = {**payload, "unregistered": True}
    with pytest.raises(ValueError):
        gpu.checkpoint_metadata(altered, record, registration, {"vocabulary": ["a"]}, ["x"])


def test_summary_keeps_zero_roles_unpaired_and_forced_choice_buckets():
    one = gpu.score_choice([0, 1], 0, [0])
    many = gpu.score_choice([0, 1], 1, [0, 1])
    rows = [{"checkpoint": "cas_initial", "cohort": "train_probe", "depth": 1,
             "decision_rows": [
                 {"reference_site": {"role": "run_input"}, "correspondence": "SITE_MISSING",
                  "preceding_tokens_differ": None, "correct_prefix": one, "self_generated_prefix": None},
                 {"reference_site": {"role": "run_input"}, "correspondence": "MATCHED",
                  "preceding_tokens_differ": False, "correct_prefix": many, "self_generated_prefix": many}]}]
    result = gpu.summarize(rows)
    assert len(result) == 6
    run = next(r for r in result if r["role"] == "run_input")
    assert run["reference_sites"] == 2
    assert run["correct_prefix"]["generated_prefix_relation"] == {"identical": 1, "different": 0, "unpaired": 1}
    assert run["correct_prefix"]["single_option"]["grammar_masked"]["attempted"] == 1
    assert run["correct_prefix"]["multiple_options"]["grammar_masked"]["attempted"] == 1
    assert run["self_generated_prefix"]["unscored_sites"] == 1
    zero = next(r for r in result if r["role"] == "call_target")
    assert zero["reference_sites"] == 0 and zero["correct_prefix"]["grammar_masked"]["mean_nll"] is None


def test_static_neural_boundary_and_no_optimizer_execution():
    tree = ast.parse(Path(gpu.__file__).read_bytes())
    top_imports = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    assert all(not (isinstance(n, ast.Import) and any(a.name == "torch" for a in n.names)) for n in top_imports)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    loads = [n for n in calls if isinstance(n.func.value, ast.Name) and n.func.value.id == "torch" and n.func.attr == "load"]
    assert len(loads) == 1
    keywords = {k.arg: k.value for k in loads[0].keywords}
    assert isinstance(keywords["weights_only"], ast.Constant) and keywords["weights_only"].value is True
    assert isinstance(keywords["map_location"], ast.Name) and keywords["map_location"].id == "device"
    assert not any(n.func.attr in ("backward", "step") for n in calls)
