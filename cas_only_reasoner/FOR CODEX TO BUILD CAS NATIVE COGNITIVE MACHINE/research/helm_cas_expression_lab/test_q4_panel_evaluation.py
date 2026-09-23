"""CPU-only panel/custody/checker tests; no model construction or inference."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q4_panel_evaluation as panel


def leaf(n=0, drive=None):
    return {"node": "StateLiteral", "operator": "^" + str(n), "domain": "P", "drive": drive}


def binary(left, right, op="PLUS"):
    return {"node": "BinaryExpr", "op": op, "left": left, "right": right}


def fixture_rows():
    train, dev = [], []
    for i in range(20):
        drive = "F" + str(i // 10 + 1)
        ast = binary(leaf(), leaf(i % 10, drive))
        visible = {"record_id": "train-" + str(i), "family": "G", "mode": "reconstruction",
                   "observation": "(^0^P + ^%d^P_{%s})" % (i % 10, drive)}
        train.append((visible, {"target_ast": ast}))
        dev.append((dict(visible, record_id="dev-" + str(i), observation="(^0^P + " + visible["observation"] + ")"),
                    {"target_ast": binary(leaf(), ast)}))
    return train, dev


def test_operator_and_order_survive_structure_key():
    a = binary(leaf(), binary(leaf(), leaf()))
    b = binary(binary(leaf(), leaf()), leaf())
    assert panel.shape_key(a) != panel.shape_key(b)
    assert panel.shape_key(binary(leaf(), leaf())) != panel.shape_key(binary(leaf(), leaf(), "TIMES"))
    assert panel.shape_key(binary(leaf(1), leaf(9))) == panel.shape_key(binary(leaf(4), leaf(2)))


def test_unknown_ast_does_not_collapse_to_leaf():
    with pytest.raises(ValueError):
        panel.skeleton({"node": "MadeUp"})


@pytest.mark.parametrize("count,seed,updates", [(0, 1, 1), (10, 1, 11), (2049, 1, 5), (10, True, 3), (10, 1, -1)])
def test_exposure_schedule_refuses_unsupported_values(count, seed, updates):
    with pytest.raises(panel.PanelError):
        panel.consumed_indices(count, seed, updates)


def test_exposure_is_ordered_seeded_single_example_schedule():
    assert panel.consumed_indices(10, 20260921, 4) == [2, 5, 4, 7]


def test_build_three_distinct_panels_and_preserve_inputs():
    train, dev = fixture_rows()
    original = deepcopy((train, dev))
    panels, facts = panel.build_panels(train, dev, list(range(16)))
    assert (train, dev) == original
    assert {key: len(rows) for key, rows in panels.items()} == dict.fromkeys(panel.PANELS, 16)
    assert facts["actual_consumed_rows"] == 16
    assert panels["teaching_fit"][3]["origin"]["training_position"] == 3
    assert not panels["new_structure"][0]["matched_teaching_pool_size_depth"]
    panel.validate_panels(panels, train, list(range(16)))


@pytest.mark.parametrize("n", [0, 17, True])
def test_panel_prediction_limits(n):
    with pytest.raises(panel.PanelError):
        panel.build_panels(*fixture_rows(), list(range(16)), n)


def test_missing_new_structure_panel_is_unavailable():
    train, _ = fixture_rows()
    with pytest.raises(panel.PanelError, match="INSUFFICIENT_NEW_STRUCTURES"):
        panel.build_panels(train, train, list(range(16)))


def test_duplicate_exposure_rejected():
    with pytest.raises(panel.PanelError, match="EXPOSURE_INDICES_INVALID"):
        panel.build_panels(*fixture_rows(), [0] * 16)


def test_training_pool_is_not_the_same_as_actual_exposure():
    train, dev = fixture_rows()
    panels, _ = panel.build_panels(train, dev, list(range(16)))
    panels["teaching_fit"][0] = panel.make_row(train[19][0], train[19][1]["target_ast"], {})
    with pytest.raises(panel.PanelError, match="TEACHING_NOT_CONSUMED"):
        panel.validate_panels(panels, train, list(range(16)))


@pytest.mark.parametrize("mode", ["same_content", "same_observation", "unfamiliar_shape"])
def test_familiar_panel_rejects_wrong_split(mode):
    train, dev = fixture_rows()
    panels, _ = panel.build_panels(train, dev, list(range(16)))
    if mode == "same_content":
        panels["new_content_familiar_structure"][0] = panel.make_row(train[19][0], train[19][1]["target_ast"], {})
    elif mode == "same_observation":
        panels["new_content_familiar_structure"][0]["visible"]["observation"] = train[19][0]["observation"]
    else:
        panels["new_content_familiar_structure"][0] = panel.make_row(dev[19][0], dev[19][1]["target_ast"], {})
    with pytest.raises(panel.PanelError, match="FAMILIAR_PANEL_CONTAMINATED"):
        panel.validate_panels(panels, train, list(range(16)))


def test_new_structure_compares_complete_pool_not_only_consumed():
    train, dev = fixture_rows()
    panels, _ = panel.build_panels(train, dev, list(range(16)))
    train.append(dev[19])
    with pytest.raises(panel.PanelError, match="NEW_STRUCTURE_CONTAMINATED"):
        panel.validate_panels(panels, train, list(range(16)))


@pytest.mark.parametrize("field", ["content_sha256", "ordered_operator_shape_sha256"])
def test_mutated_row_fingerprints_fail(field):
    train, dev = fixture_rows()
    panels, _ = panel.build_panels(train, dev, list(range(16)))
    panels["teaching_fit"][0][field] = "0" * 64
    with pytest.raises(panel.PanelError, match="ROW_FINGERPRINT_MISMATCH"):
        panel.validate_panels(panels, train, list(range(16)))


def test_external_manifest_digest_checked_before_source_import():
    with pytest.raises(panel.PanelError, match="FROZEN_INPUT_MANIFEST_MISMATCH"):
        panel.validate_manifest({"schema": panel.SCHEMA}, "0" * 64)


def test_pinned_file_drift_fails_before_checkpoint_loading(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("original")
    manifest = {"schema": panel.SCHEMA, "files": [panel.file_pin(source)]}
    digest = panel.sha(panel.canonical(manifest))
    source.write_text("mutated")
    with pytest.raises(panel.PanelError, match="FROZEN_FILE_MISMATCH"):
        panel.validate_manifest(manifest, digest)


def test_historical_source_mismatch_fails_before_import(tmp_path):
    (tmp_path / "model.py").write_text("bad")
    with pytest.raises(panel.PanelError, match="HISTORICAL_SOURCE_MISMATCH"):
        panel._source_modules(tmp_path, {"model.py": "0" * 64})


@pytest.mark.parametrize("prediction,exact,structure,valid", [
    (leaf(), True, True, True), (leaf(3), False, True, True),
    (binary(leaf(), leaf()), False, False, True), (None, False, False, False),
    ({"node": "Bogus"}, False, False, False)])
def test_exact_parse_and_structure_metrics_are_separate(prediction, exact, structure, valid):
    assert panel.grade(prediction, leaf()) == {"canonical_exact": exact, "parse_valid": valid,
                                               "operator_structure_exact": structure}


def test_missing_panels_have_zero_denominator_not_invented_scores():
    row = {"panel": "new_structure", "checks": panel.grade(leaf(3), leaf())}
    summary = panel.summarize([row])
    assert summary["teaching_fit"]["n"] == 0
    assert summary["new_content_familiar_structure"]["n"] == 0
    assert summary["new_structure"] == {"n": 1, "canonical_exact": 0, "parse_valid": 1, "operator_structure_exact": 1}


def test_existing_outputs_never_overwritten(tmp_path):
    path = tmp_path / "old.json"
    panel.write_once(path, {"original": True})
    with pytest.raises(FileExistsError):
        panel.write_once(path, {"original": False})
    assert json.loads(path.read_text()) == {"original": True}


def test_supervisor_records_conflict_without_launch_or_unrelated_process_kill(tmp_path, monkeypatch):
    import q4_smoke_job
    import q4_device_capacity
    manifest = {"schema": panel.SCHEMA, "files": [], "historical_run": str(tmp_path / "old"),
                "resources": {}, "authorization": {"mode": "TEST_ONLY_NO_RUN"}}
    path = tmp_path / "manifest.json"
    panel.write_once(path, manifest)
    lock = tmp_path / "lock"
    monkeypatch.setattr(panel, "validate_manifest", lambda *args: None)
    monkeypatch.setattr(q4_smoke_job, "_device_lock_path", lambda *_: lock)
    monkeypatch.setattr(panel, "active_learning_jobs", lambda: {"matching_learning_jobs": [{"pid": 999}]})
    monkeypatch.setattr(q4_device_capacity, "check_prelaunch", lambda *_: pytest.fail("must not query or launch"))
    with pytest.raises(panel.PanelError, match="OTHER_LEARNING_JOB_ACTIVE"):
        panel.execute(path, "0" * 64, tmp_path / "run")
    assert not lock.exists()
    receipt = json.loads((tmp_path / "run/supervisor.json").read_text())
    assert receipt["status"] == "FAILED"
    assert receipt["automatic_retries"] == 0
    assert receipt["failure"]["message"] == "OTHER_LEARNING_JOB_ACTIVE"


@pytest.mark.parametrize("pwsh_present", [True, False])
def test_process_inventory_resolves_installed_shell_instead_of_assumed_path(monkeypatch, pwsh_present):
    from types import SimpleNamespace
    monkeypatch.setattr(panel.shutil, "which", lambda name: "D:/runtime/" + name + ".exe"
                        if name == "powershell" or pwsh_present else None)
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout=json.dumps([
            {"ProcessId": 7, "CommandLine": "python q4_smoke_job.py execute"},
            {"ProcessId": 8, "CommandLine": "python server.py"}]))
    monkeypatch.setattr(panel.subprocess, "run", run)
    result = panel.active_learning_jobs()
    assert calls[0][0] == "D:/runtime/" + ("pwsh" if pwsh_present else "powershell") + ".exe"
    assert result["matching_learning_jobs"] == [{"pid": 7, "entry_point": "q4_smoke_job.py"}]


def test_process_inventory_missing_shell_fails_closed(monkeypatch):
    monkeypatch.setattr(panel.shutil, "which", lambda _: None)
    with pytest.raises(panel.PanelError, match="LOCAL_JOB_INVENTORY_SHELL_UNAVAILABLE"):
        panel.active_learning_jobs()
