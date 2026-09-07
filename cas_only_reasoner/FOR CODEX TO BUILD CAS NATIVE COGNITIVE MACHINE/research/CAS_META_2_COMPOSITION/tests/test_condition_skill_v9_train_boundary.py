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


def sliced_row(task, target, prediction, equality=0, unit_margin=0):
    return {**score_row(task, target, prediction),
            "equality_conditions": equality, "unit_margin_conditions": unit_margin}


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
    assert result["first_wrong_bit"] == {"bit_1_count": 1, "bit_2_count": 1, "none_count": 2,
                                         "bit_1_fraction": 0.25, "bit_2_fraction": 0.25}
    assert "equality_slice" not in result and "unit_margin_slice" not in result


def test_summarize_first_wrong_bit_uses_bit_order_and_no_effect():
    # NO_EFFECT is wrong on both bits, so bit 1 is reported first.
    rows = [score_row("ok", 0, 0), score_row("bit1", 1, 3), score_row("bit2", 2, 3),
            score_row("dead", 3, -1)]
    result = train.summarize(rows)
    assert result["first_wrong_bit"] == {"bit_1_count": 2, "bit_2_count": 1, "none_count": 1,
                                         "bit_1_fraction": 0.5, "bit_2_fraction": 0.25}


def test_summarize_emits_margin_slices_when_rows_carry_them():
    rows = [sliced_row("eq-ok", 0, 0, equality=1), sliced_row("eq-bad", 1, 0, equality=2),
            sliced_row("unit-ok", 2, 2, unit_margin=1), sliced_row("unit-bad", 3, 2, unit_margin=1)]
    result = train.summarize(rows)
    assert result["equality_slice"] == {"cases": 2, "correct": 1, "accuracy": 0.5}
    assert result["unit_margin_slice"] == {"cases": 2, "correct": 1, "accuracy": 0.5}


def test_summarize_rejects_bad_margin_fields():
    rows = [sliced_row(str(i), i, i) for i in range(4)]
    for key, value in (("equality_conditions", 3), ("unit_margin_conditions", -1),
                       ("equality_conditions", "1")):
        broken = deepcopy(rows)
        broken[0][key] = value
        with pytest.raises(ValueError, match="SCORE_MARGIN_RANGE"):
            train.summarize(broken)


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


def passing_report():
    metrics = {}
    for family in train.FAMILIES:
        metrics[family + ".untrained"] = {
            split: {"accuracy": 0.2, "bit_accuracy": [0.5, 0.5]} for split in train.TEST_SPLITS}
        metrics[family + ".trained"] = {
            split: {"accuracy": 0.6, "bit_accuracy": [0.8, 0.8]} for split in train.TEST_SPLITS}
    controls = {}
    for family in train.FAMILIES:
        controls[family + ".trained"] = {
            split + "." + control: {"joint_accuracy": 1.0}
            for split in train.TEST_SPLITS for control in train.CONTROL_NAMES}
    return {
        "status": "COMPLETED_OFFLINE_CANDIDATE_EXPERIMENT",
        "selection_sealed": True, "test_targets_parsed": True,
        "source_before": {"baseline": {}, "installed_wheels": {}, "candidate_sources": {}},
        "source_after": {"baseline": {}, "installed_wheels": {}, "candidate_sources": {}},
        "baselines": {split: {"cases": 384, "constant_correct": 96, "oracle_correct": 384}
                      for split in ("validation", "test_instances", "test_direction_pair")},
        "metrics": metrics, "controls": controls,
        "training_steps": {"cas": 2400, "generic_attention": 2400},
    }


def provider_attestation():
    return {**train.PROVIDER_ATTESTATION_KEYS, "job": "cas-meta2-20260907123456-abcdef12"}


def test_adjudication_vocabulary_is_frozen():
    assert train.ADJUDICATION["status_vocabulary"] == ["PASS", "FAIL", "EVIDENCE_INCOMPLETE"]
    assert train.ADJUDICATION["claim_scope"] == "offline_candidate_learning_only_no_native_admission"


def test_adjudicator_without_provider_attestation_is_evidence_incomplete():
    verdict = train.adjudicate(passing_report())
    assert verdict["status"] == "EVIDENCE_INCOMPLETE"
    gate = verdict["gates"]["provider_attestation"]
    assert gate["passed"] is False and gate["actual"] is None


def test_adjudicator_passes_complete_evidence_and_matching_attestation():
    verdict = train.adjudicate(passing_report(), provider_attestation())
    assert verdict["status"] == "PASS"
    assert all(gate["passed"] for gate in verdict["gates"].values())


def test_adjudicator_reports_baselines_denominators_and_family_rows():
    verdict = train.adjudicate(passing_report(), provider_attestation())
    definitions = verdict["metric_definitions"]
    assert definitions["joint_accuracy"]["baseline"] == 0.25
    assert definitions["bit_accuracy"]["baseline"] == 0.5
    assert definitions["bit_accuracy"]["denominator"] == (
        "all attempted rows; NO_EFFECT is wrong for both bits")
    assert verdict["families"]["cas"]["all_passed"] is True
    assert verdict["families"]["generic_attention"]["all_passed"] is True
    assert "cas_trained_test_instances_accuracy" in verdict["families"]["cas"]["gates"]
    assert verdict["initial_vs_trained"]["cas.test_instances"] == {
        "untrained_accuracy": 0.2, "trained_accuracy": 0.6, "improved": True}
    assert "combined campaign" in verdict["overall_verdict_is_conjunction"]
    assert "never erased" in verdict["overall_verdict_is_conjunction"]


def test_adjudicator_keeps_family_rows_when_campaign_fails():
    report = passing_report()
    report["metrics"]["generic_attention.trained"]["test_instances"]["accuracy"] = 0.2
    verdict = train.adjudicate(report, provider_attestation())
    assert verdict["status"] == "FAIL"
    assert verdict["families"]["cas"]["all_passed"] is True
    assert verdict["families"]["generic_attention"]["all_passed"] is False
    assert verdict["initial_vs_trained"]["cas.test_instances"]["improved"] is True


@pytest.mark.parametrize("tamper,gate_name", [
    (lambda r: r.update(status="FAILED"), "experiment_status"),
    (lambda r: r.update(selection_sealed=False), "selection_sealed"),
    (lambda r: r.update(test_targets_parsed=False), "test_targets_parsed"),
    (lambda r: r["metrics"]["cas.trained"]["test_instances"].update(accuracy=0.20),
     "cas_trained_test_instances_accuracy"),
    (lambda r: r["metrics"]["generic_attention.trained"]["test_direction_pair"].update(bit_accuracy=[0.6, 0.45]),
     "generic_attention_trained_test_direction_pair_bit1"),
    (lambda r: r["metrics"]["cas.untrained"]["test_instances"].update(accuracy=0.9),
     "cas_trained_beats_untrained_test_instances"),
    (lambda r: r["controls"]["cas.trained"]["test_instances.direction_1_reverse"].update(joint_accuracy=0.5),
     "cas_trained_test_instances_direction_1_reverse_joint"),
    (lambda r: r["baselines"]["validation"].update(constant_correct=97),
     "constant_baseline_validation"),
    (lambda r: r["baselines"]["test_direction_pair"].update(oracle_correct=383),
     "oracle_test_direction_pair"),
    (lambda r: r.update(training_steps={"cas": 2399, "generic_attention": 2400}),
     "cas_fixed_steps"),
    (lambda r: r["source_after"].update(candidate_sources={"extra": "changed"}), "source_byte_pins"),
])
def test_adjudicator_fails_each_broken_gate(tamper, gate_name):
    report = passing_report()
    tamper(report)
    verdict = train.adjudicate(report, provider_attestation())
    assert verdict["status"] == "FAIL"
    assert verdict["gates"][gate_name]["passed"] is False


def test_adjudicator_marks_missing_evidence_incomplete_not_failed():
    report = passing_report()
    report.pop("metrics")
    verdict = train.adjudicate(report, provider_attestation())
    assert verdict["status"] == "EVIDENCE_INCOMPLETE"


def test_adjudicator_rejects_mismatched_or_malformed_attestation():
    bad = {**provider_attestation(), "account": "000000000000"}
    assert train.adjudicate(passing_report(), bad)["status"] == "FAIL"
    assert train.adjudicate(passing_report(), "not-a-dict")["status"] == "FAIL"
    missing_job = {**train.PROVIDER_ATTESTATION_KEYS, "job": "wrong"}
    assert train.adjudicate(passing_report(), missing_job)["status"] == "FAIL"


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
