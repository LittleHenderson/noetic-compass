"""Pure boundary checks for the CUDA-only v9 trainer.

These tests never import a tensor library or run the experiment. They exercise
only admission, configuration, reporting, and output-boundary behavior.
"""
from copy import deepcopy
import builtins
import platform

import pytest

from cas_meta2.condition_skill_v9 import train


FORBIDDEN = {"torch", "numpy", "sqlite3", "boto3", "botocore", "casformer", "cas_cjt"}


def test_import_is_neural_and_provider_free():
    assert not FORBIDDEN.intersection(__import__("sys").modules)
    assert train.CLAIMS == {
        "native_runtime_created": False,
        "native_admission": "NOT_DONE",
        "accepted_artifacts_replaced": False,
        "persistent_bias_reset": False,
        "historical_C7_repaired": False,
        "restart_or_resume_proved": False,
        "CAS_advantage_claimed": False,
        "new_noetic_semantics": False,
        "provider_identity_proved_by_execution_guard": False,
    }


def test_default_config_is_fresh_and_exact():
    first = train.validate_config()
    second = train.validate_config({})
    assert first == second == train.DEFAULT_CONFIG
    assert first is not train.DEFAULT_CONFIG and second is not first
    first["epochs"] = 1
    assert train.DEFAULT_CONFIG["epochs"] == 100


@pytest.mark.parametrize("config,reason", [
    ({"epochs": 99}, "FIXED_CONFIG_REQUIRED:epochs"),
    ({"epochs": True}, "FIXED_CONFIG_REQUIRED:epochs"),
    ({"learning_rate": 0.0030, "extra": 1}, "UNKNOWN_CONFIG_FIELD"),
    ([], "CONFIG_OBJECT_REQUIRED"),
    ("", "CONFIG_OBJECT_REQUIRED"),
])
def test_config_rejects_tuning_or_wrong_types(config, reason):
    with pytest.raises(ValueError, match=reason):
        train.validate_config(config)


def test_execution_guard_fail_closed_off_linux_or_without_flag(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    with pytest.raises(ValueError, match="LINUX_WORKER_REQUIRED"):
        train.execution_guard()

    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.delenv("CAS_META2_RUN_CONDITION_SKILL_V9", raising=False)
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", "cas-meta2-20260907123456-abcdef12")
    with pytest.raises(ValueError, match="EXPLICIT_CONDITION_SKILL_ENABLE_REQUIRED"):
        train.execution_guard()


@pytest.mark.parametrize("job", ["", "cas-meta2-1-deadbeef", "cas-meta2-20260907123456-ABCDEFGH",
                                  "cas-meta2-20260907123456-deadbeeg", "other-20260907123456-deadbeef"])
def test_execution_guard_rejects_malformed_job_labels(monkeypatch, job):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setenv("CAS_META2_RUN_CONDITION_SKILL_V9", "1")
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", job)
    with pytest.raises(ValueError, match="EXPLICIT_AWS_JOB_LABEL_REQUIRED"):
        train.execution_guard()


def test_execution_guard_is_not_provider_attestation(monkeypatch):
    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setenv("CAS_META2_RUN_CONDITION_SKILL_V9", "1")
    job = "cas-meta2-20260907123456-abcdef12"
    monkeypatch.setenv("CAS_META2_AWS_JOB_ID", job)
    assert train.execution_guard() == {
        "job_label": job,
        "provider_identity_proved": False,
        "identity_evidence_required": "independent outer provider launch receipt",
    }


def score_row(task, target, prediction, loss=1.0):
    return {"task_id": task, "target": target, "prediction": prediction,
            "negative_log_likelihood": loss}


def test_summarize_counts_classes_bits_and_no_effect():
    rows = [score_row("a", 0, 0, 0.1), score_row("b", 1, -1, 0.2),
            score_row("c", 2, 3, 0.3), score_row("d", 3, 3, 0.4)]
    result = train.summarize(rows)
    assert result["cases"] == 4 and result["correct"] == 2
    assert result["accuracy"] == result["macro_accuracy"] == 0.5
    assert result["class_counts"] == [1, 1, 1, 1]
    assert result["confusion"] == [[1, 0, 0, 0, 0], [0, 0, 0, 0, 1],
                                    [0, 0, 0, 1, 0], [0, 0, 0, 1, 0]]
    assert result["no_effect_count"] == 1
    assert result["bit_accuracy"] == [0.75, 0.5]
    assert result["error_task_ids"] == ["b", "c"]


def test_summarize_refuses_empty_missing_class_and_bad_values():
    with pytest.raises(ValueError, match="EMPTY_SCORE_ROWS"):
        train.summarize([])
    with pytest.raises(ValueError, match="MACRO_REQUIRES_ALL_FOUR_CLASSES"):
        train.summarize([score_row("a", 0, 0)])
    rows = [score_row(str(i), i, i) for i in range(4)]
    for key, value in (("target", True), ("target", 4), ("prediction", -2), ("prediction", 4)):
        broken = deepcopy(rows)
        broken[0][key] = value
        with pytest.raises(ValueError, match="SCORE_CLASS_RANGE"):
            train.summarize(broken)


@pytest.fixture
def scoped_output(monkeypatch, tmp_path):
    monkeypatch.setattr(train, "ROOT", tmp_path)
    parent = tmp_path / "records"
    parent.mkdir()
    return parent / "run"


def test_writer_is_scoped_fresh_flat_and_bounded(scoped_output):
    output = scoped_output
    writer = train._Writer(output, 1024 * 1024 + 32)
    assert output.is_dir() and writer.used == 0
    item = writer.write("a.bin", b"abc")
    assert item["bytes"] == 3 and (output / "a.bin").read_bytes() == b"abc"
    with pytest.raises(ValueError, match="NEW_FLAT_OUTPUT_REQUIRED"):
        writer.write("a.bin", b"again")
    with pytest.raises(ValueError, match="NEW_FLAT_OUTPUT_REQUIRED"):
        writer.write("../escape.bin", b"x")
    with pytest.raises(ValueError, match="OUTPUT_BYTES_REQUIRED"):
        writer.write("text.bin", "x")
    with pytest.raises(ValueError, match="OUTPUT_BYTE_LIMIT"):
        writer.write("too-large.bin", b"x" * 30)
    assert writer.write("result.json", b"x" * 29, final=True)["bytes"] == 29


def test_writer_refuses_existing_or_out_of_scope_paths(scoped_output):
    scoped_output.mkdir()
    with pytest.raises(ValueError, match="FRESH_SCOPED_OUTPUT_DIRECTORY_REQUIRED"):
        train._Writer(scoped_output, 1024 * 1024 + 1)
    outside = train.ROOT / "outside-condition-run"
    with pytest.raises(ValueError, match="FRESH_SCOPED_OUTPUT_DIRECTORY_REQUIRED"):
        train._Writer(outside, 1024 * 1024 + 1)


def test_run_checks_guard_before_neural_import_or_output(monkeypatch, scoped_output):
    output = scoped_output
    imported = []
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        imported.append(name)
        if name.split(".")[0] in FORBIDDEN:
            raise AssertionError("HEAVY_IMPORT_BEFORE_GUARD:" + name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    with pytest.raises(ValueError, match="LINUX_WORKER_REQUIRED"):
        train.run(output, "unused")
    assert not output.exists()
    assert not FORBIDDEN.intersection(name.split(".")[0] for name in imported)
