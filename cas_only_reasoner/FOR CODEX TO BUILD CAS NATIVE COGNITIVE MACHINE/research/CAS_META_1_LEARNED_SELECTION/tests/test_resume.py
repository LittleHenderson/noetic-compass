"""Recovery contracts only: JSON/bytes and fake CUDA setup, no neural work."""
import ast
import copy
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest

from cas_meta1 import resume
from cas_meta1.execution import ExecutionInfrastructureError


@pytest.fixture
def original(monkeypatch):
    training = Path("/byte_only_original")
    archive = resume.ROOT/"records"/"aws_run_001"/"cloud_artifacts.zip"
    with zipfile.ZipFile(archive) as source:
        saved = {Path(name).name: source.read(name) for name in source.namelist()
                 if name.startswith("cloud_job/training/") and len(Path(name).parts) == 3}
    read, hashed = resume.read, resume.file_hash
    monkeypatch.setattr(resume, "read", lambda path: json.loads(saved[Path(path).name])
                        if Path(path).parent == training else read(path))
    monkeypatch.setattr(resume, "file_hash", lambda path: resume.sha256(saved[Path(path).name]).hexdigest()
                        if Path(path).parent == training else hashed(path))
    return training, saved


def test_original_saved_predictions_checkpoints_and_data_match_without_loading_models(original):
    tasks, publics, predictions, checkpoints = resume.validate_inputs(original[0], resume.ROOT/"data")
    assert len(tasks) == len(publics) == 72
    assert len(resume.work_items(predictions)) == 72
    assert sum(len(item["actions"]) for item in resume.work_items(predictions)) == 360
    assert checkpoints["cas"]["selected"]["epoch"] == 28
    assert checkpoints["generic"]["selected"]["epoch"] == 55


@pytest.mark.parametrize("name", ["predictions.json", "cas_best.pt", "generic_best.pt"])
def test_changed_prediction_or_checkpoint_bytes_fail(original, name):
    training, saved = original
    saved[name] += b" "
    with pytest.raises(ValueError, match="CHANGED"):
        resume.validate_inputs(training, resume.ROOT/"data")


def test_gold_custody_timestamp_cannot_move_before_seal(original):
    training, saved = original
    opening = json.loads(saved["test_gold_opening_receipt.json"])
    opening["opened_utc"] = "2020-01-01T00:00:00+00:00"
    saved["test_gold_opening_receipt.json"] = json.dumps(opening).encode()
    with pytest.raises(ValueError, match="GOLD_OPENED_BEFORE"):
        resume.validate_inputs(training, resume.ROOT/"data")


def test_setup_is_once_per_process_and_never_calls_real_cuda(monkeypatch):
    import sys
    import cas_meta1.policy
    calls = []
    fake = SimpleNamespace(set_num_threads=lambda n:calls.append(("threads", n)),
        set_num_interop_threads=lambda n:calls.append(("interop", n)),
        use_deterministic_algorithms=lambda value:calls.append(("deterministic", value)),
        backends=SimpleNamespace(cudnn=SimpleNamespace(benchmark=True, allow_tf32=True),
                                cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=True))))
    monkeypatch.setitem(sys.modules, "torch", fake)
    monkeypatch.setattr(cas_meta1.policy, "require_cuda", lambda device:"fake_cuda")
    monkeypatch.setattr(resume, "_CUDA_CONTEXT", None)
    assert resume.setup_cuda() == resume.setup_cuda() == (fake, "fake_cuda")
    assert calls.count(("interop", 1)) == 1
    assert fake.backends.cuda.matmul.allow_tf32 is False


@pytest.mark.parametrize("kind", ["OutOfMemoryError", "OSError", "RuntimeError", "ValueError"])
def test_returned_runtime_failures_never_become_model_errors(kind):
    with pytest.raises(ExecutionInfrastructureError, match="VALID_ACTION_EXECUTION_FAILED"):
        resume.require_healthy_execution({"status":"REJECTED", "failure":{"type":kind}})


def test_evidence_io_failure_aborts_but_wrong_answer_remains_in_denominator():
    with pytest.raises(ExecutionInfrastructureError, match="DURABLE_VERIFICATION"):
        resume.require_healthy_execution({"status":"EXECUTED"}, {"reasons":["INVALID_DURABLE_EVIDENCE:OperationalError"]})
    resume.require_healthy_execution({"status":"EXECUTED"}, {"success":False,"reasons":["PROCEDURE_CORRECT","OUTPUT_CORRECT"]})


def completed_fixture():
    predictions = {"arms": {arm:[{"procedure":0,"binding":0} for _ in range(72)] for arm in resume.ARMS}}
    completed = [{"case_index":i, "arms":{arm:{"case_index":i,"action":copy.deepcopy(predictions["arms"][arm][i]),
        "verification":{"success":i == 0},"execution_status":"EXECUTED","reserved_policy_units":72,
        "execution_timing":{"wall_seconds":1}} for arm in resume.ARMS}} for i in range(72)]
    return predictions, completed


def test_recount_keeps_all_five_denominators_and_does_not_select_successes():
    predictions, completed = completed_fixture()
    metrics, _ = resume.recount(list(reversed(completed)), predictions)
    assert all(row["total"] == 72 and row["success"] == 1 for row in metrics.values())
    with pytest.raises(ValueError, match="MISSING_OR_DUPLICATE"):
        resume.recount(completed[:-1], predictions)
    completed[-1] = completed[0]
    with pytest.raises(ValueError, match="MISSING_OR_DUPLICATE"):
        resume.recount(completed, predictions)


def test_recount_rejects_action_changed_after_seal():
    predictions, completed = completed_fixture()
    completed[0]["arms"]["cas_trained"]["action"]["binding"] = 1
    with pytest.raises(ValueError, match="DIFFER_FROM_ORIGINAL_SEAL"):
        resume.recount(completed, predictions)


def test_recovery_has_no_selector_forward_training_or_optimizer_calls():
    source = Path(resume.__file__).read_text(encoding="utf-8")
    parsed = ast.parse(source)
    names = {node.func.attr for node in ast.walk(parsed) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not names & {"backward", "step", "predict", "forward", "load_state_dict", "fit"}
    assert 'get_context("spawn")' in source
    assert "stop_pool(pool)" in source
    assert "profile_call(run" in source


def test_in_memory_path_rebinding_preserves_original_record():
    original = {"output_dir":"/old", "native_database":"/old/native.db", "sha256":"unchanged"}
    updated = resume.rebound_result(original, resume.ROOT/"records"/"example")
    assert original["output_dir"] == "/old" and updated["sha256"] == "unchanged"
    with pytest.raises(ValueError, match="OUTSIDE_PILOT"):
        resume.rebound_result(original, resume.ROOT.parent)


def test_failed_worker_pool_cancels_and_stops_every_process():
    events = []
    process = SimpleNamespace(is_alive=lambda:True, terminate=lambda:events.append("terminate"),
                              kill=lambda:events.append("kill"), join=lambda timeout:events.append("join"))
    pool = SimpleNamespace(_processes={1:process, 2:process},
                           shutdown=lambda **kwargs:events.append(kwargs))
    resume.stop_pool(pool)
    assert events[0] == {"wait":False, "cancel_futures":True}
    assert events.count("terminate") == events.count("kill") == events.count("join") == 2
