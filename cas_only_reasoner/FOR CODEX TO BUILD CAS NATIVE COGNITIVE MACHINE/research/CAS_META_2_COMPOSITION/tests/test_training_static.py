"""Pure data and source checks; no Torch import or model execution."""

import ast
from copy import deepcopy
from pathlib import Path
import subprocess
import sys

import pytest

from cas_meta2.campaign import (
    ARMS, MAX_OUTPUT_BYTES, MAX_WALL_SECONDS, WORKERS,
    _smoke_tasks, admission_error, aggregate_cases,
)
from cas_meta2.curriculum import generate_dataset, parse_problem
from cas_meta2.ir import validate_program

pytestmark = pytest.mark.not_gpu
ROOT = Path(__file__).resolve().parents[1]
TRAIN_TEXT = (ROOT / "cas_meta2" / "train.py").read_text(encoding="utf-8")
CAMPAIGN_TEXT = (ROOT / "cas_meta2" / "campaign.py").read_text(encoding="utf-8")
TRAIN = ast.parse(TRAIN_TEXT)
CAMPAIGN = ast.parse(CAMPAIGN_TEXT)


def function(tree, name):
    return next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)


def test_campaign_import_does_not_import_torch():
    script = ("import sys;sys.path.insert(0," + repr(str(ROOT))
              + ");import cas_meta2.campaign;assert 'torch' not in sys.modules")
    subprocess.run([sys.executable, "-B", "-c", script], check=True)


def test_training_source_does_not_parse_held_out_private_file():
    for node in ast.walk(TRAIN):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("read_json", "loads", "load"):
            source = ast.get_source_segment(TRAIN_TEXT, node)
            assert "test_private.json" not in source
    assert 'file_hash(data / name)' in TRAIN_TEXT
    assert '"test_private_labels_loaded": False' in TRAIN_TEXT


def test_private_opening_occurs_after_seal_validation():
    node = function(CAMPAIGN, "evaluate_sealed")
    source = ast.get_source_segment(CAMPAIGN_TEXT, node)
    assert source.index("PREDICTION_SEAL_INVALID") < source.index('tasks = _read(data / "test_private.json")')
    assert source.index("SEALED_CASE_ARM_COVERAGE_INVALID") < source.index('tasks = _read(data / "test_private.json")')
    assert "TEST_GOLD_OPENING_TIME_NOT_AFTER_SEAL" in source
    assert "TEST_PUBLIC_PRIVATE_BINDING_MISMATCH" in source


def test_dataset_construction_uses_a_separate_process():
    source = ast.get_source_segment(CAMPAIGN_TEXT, function(CAMPAIGN, "_construct_data"))
    assert "subprocess.run(" in source and "capture_output=True" in source
    assert "write_dataset(sys.argv[1]" in source


def test_training_uses_identical_paired_batches_and_optimizer_conditions():
    source = ast.get_source_segment(TRAIN_TEXT, function(TRAIN, "train_and_seal"))
    assert "for family, model in models.items():" in source
    assert 'logits = model(public_batch, target["decoder_input_ids"])' in source
    assert "torch.optim.AdamW(model.parameters(), lr=config.learning_rate" in source
    assert "MATCHED_OPTIMIZER_STEPS_DIFFER" in source
    assert "DISCONNECTED_TRAINABLE_PARAMETERS" in source
    assert "TRAINING_GRADIENT_NONFINITE" in source
    assert "BOUNDED_TRAINING_ALLOCATION_REACHED" in source


def test_validation_selection_never_uses_test_outcome():
    source = ast.get_source_segment(TRAIN_TEXT, function(TRAIN, "train_and_seal"))
    assert 'validation["token_cross_entropy"] < best["validation"]["token_cross_entropy"]' in source
    assert "verify_task(" not in source and "reference_task(" not in source
    assert "test_tasks" not in source


def test_checkpoint_loading_requires_digest_and_cuda():
    source = ast.get_source_segment(TRAIN_TEXT, function(TRAIN, "_load_checkpoint"))
    assert "require_cuda(device)" in source
    assert "CANDIDATE_CHECKPOINT_DIGEST_MISMATCH" in source
    assert "map_location=device, weights_only=True" in source
    assert "CHECKPOINT_ACTION_VOCABULARY_MISMATCH" in source


def test_all_five_arms_sealed_before_native_evaluation():
    assert ARMS == ("cas_untrained", "cas_trained", "generic_untrained", "generic_trained", "rule")
    source = ast.get_source_segment(TRAIN_TEXT, function(TRAIN, "train_and_seal"))
    assert source.index("for arm in ARMS:") < source.index('prediction_path = output / "predictions.jsonl"')
    assert "os.fsync(stream.fileno())" in source
    assert '"prediction_count": len(test_public) * len(ARMS)' in source


def test_worker_spawn_deadline_and_no_retry():
    source = ast.get_source_segment(CAMPAIGN_TEXT, function(CAMPAIGN, "evaluate_sealed"))
    assert 'multiprocessing.get_context("spawn")' in source
    assert "ProcessPoolExecutor(max_workers=WORKERS" in source
    assert "process.terminate()" in source and "process.kill()" in source
    assert "cancel_futures=True" in source
    assert '"automatic_retry": False' in source
    assert WORKERS == 8 and MAX_WALL_SECONDS == 6600
    assert MAX_OUTPUT_BYTES == 2 * 1024 * 1024 * 1024


def test_invalid_predictions_do_not_become_infrastructure_failures():
    public = {"problem": "An invalid model output must stay a model rejection.",
              "observations": [{"slot": i, "tag": tag, "values": [0.1 * (i + 1)] * 8}
                               for i, tag in enumerate(("amber", "blue", "green"))]}
    assert admission_error({"status": "REJECTED", "reason": "bad sequence"}, public)["code"] == "PREDICTED_PROGRAM_INVALID"
    assert admission_error({"program": {}, "binding": 0}, public)["code"] == "PREDICTED_PROGRAM_INVALID"
    source = ast.get_source_segment(CAMPAIGN_TEXT, function(CAMPAIGN, "_case_worker"))
    assert "if rejected is not None:" in source
    assert "ADMITTED_PROGRAM_NATIVE_FAILURE" in source
    assert "REJECTED_PROGRAM_REPORTED_CORRECT" in source


def test_smoke_is_public_parsed_deep_and_earlier_value_bound():
    data = generate_dataset(counts={"train": 8, "validation": 4, "test": 4})
    fixtures = dict(_smoke_tasks(data["splits"]["train"]))
    assert set(fixtures) == {"training_anchor", "nested_depth", "named_earlier_value"}
    for task in fixtures.values():
        assert parse_problem(task["public"]) == task["target"]
        assert admission_error(task["target"], task["public"]) is None
        assert task["provenance"]["split"] == "runtime_smoke_not_learning"
    assert validate_program(fixtures["nested_depth"]["target"]["program"])["max_call_depth"] == 3
    steps = fixtures["named_earlier_value"]["target"]["program"]["procedures"]["main"]["steps"]
    assert steps[2]["input"] == steps[0]["output"]
    assert steps[3]["input"] == steps[1]["output"]
    assert steps[3]["input"] != steps[2]["output"]


@pytest.mark.parametrize("child_return", [False, True])
def test_raw_observation_return_is_rejected_before_execution(child_return):
    public = {"problem": "Reject raw observation returns.",
              "observations": [{"slot": i, "tag": tag, "values": [0.1 * (i + 1)] * 8}
                               for i, tag in enumerate(("amber", "blue", "green"))]}
    run = {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v0"}
    procedures = {"main": {"input": "arg", "allowed_cjts": ["A"],
                           "steps": [run], "return": "arg"}}
    if child_return:
        procedures["p0"] = deepcopy(procedures["main"])
        procedures["main"] = {"input": "arg", "allowed_cjts": ["A"], "steps": [
            {"kind": "CALL", "procedure": "p0", "input": "arg", "output": "v0"},
            {"kind": "RUN", "cjt_id": "A", "input": "arg", "output": "v1"}], "return": "v1"}
    action = {"binding": 0, "program": {"schema": "cas-meta2-program/0.1",
                                       "entry": "main", "procedures": procedures}}
    rejection = admission_error(action, public)
    assert rejection["code"] == "PREDICTED_PROGRAM_INVALID"
    assert rejection["message"] == "ACCEPTED_EFFECT_RESULT_REQUIRED"


def cases():
    output = []
    for index in range(2):
        rows = {}
        for arm in ARMS:
            correct = index == 0
            rows[arm] = {
                "verification": {**{field: correct for field in (
                    "task_correct", "procedure_correct", "binding_correct", "dependency_correct",
                    "actual_output_correct", "trace_valid")},
                    "native_runs": 3 if correct else 0, "reserved_policy_units": 100 if correct else 0,
                    "repair_required": False, "repair_success": None},
                "model_rejection": not correct, "execution_status": "EXECUTED" if correct else "REJECTED",
                "wall_seconds": 0.25,
            }
        output.append({"case_index": index, "arms": rows})
    return output


def test_all_rejections_stay_in_actual_task_denominator():
    result = aggregate_cases(cases(), 2)
    for arm in ARMS:
        assert result[arm]["total"] == 2
        assert result[arm]["task_correct"] == 1
        assert result[arm]["task_accuracy"] == 0.5
        assert result[arm]["model_rejections"] == 1
        assert result[arm]["native_runs"] == 3
        assert result[arm]["repair_success"] is None
        assert result[arm]["all_cases_in_denominator"] is True


@pytest.mark.parametrize("indexes,expected", [([0], 2), ([0, 0], 2), ([0, 2], 2), ([0, 1], 3)])
def test_missing_or_duplicated_cases_cannot_report_complete(indexes, expected):
    values = cases()
    broken = [deepcopy(values[0]) for _ in indexes]
    for row, index in zip(broken, indexes, strict=True):
        row["case_index"] = index
    with pytest.raises(RuntimeError, match="COVERAGE_MISMATCH"):
        aggregate_cases(broken, expected)


def test_partial_receipt_retains_evidence_without_completion():
    source = ast.get_source_segment(CAMPAIGN_TEXT, function(CAMPAIGN, "run"))
    assert '"status": "CAS_META_2_AWS_CAMPAIGN_BLOCKED"' in source
    assert '"partial_artifacts_retained": True' in source
    assert '"evaluation_completed": False' in source
    assert "candidate_checkpoint_created" in source
    assert "torch.save(" not in CAMPAIGN_TEXT
