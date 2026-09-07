"""Pure self-tests for the automatic test-point layer.

Known-valid and deliberately-invalid synthetic fixtures are run through each
checker, asserting the layer distinguishes them and names the first observed
failed check. No dataset partition is read; all fixtures are synthetic bytes
under tmp_path. No forbidden library is imported.
"""
import builtins
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from tools.condition_skill_v9_test_points import (
    DATASET_MANIFEST_RELPATH,
    DATASET_MANIFEST_SHA256,
    FAMILIES,
    FILES,
    NOT_REACHED,
    STAGES,
    TEST_SPLITS,
    development_scorecard,
    identity_report,
    transition_report,
)


def _write_tree(tmp_path, manifest_bytes=b"synthetic-dataset-manifest\n"):
    """Build a synthetic source tree holding every FILES entry plus a manifest.

    Returns (root, expected) where expected maps research-relative path to the
    sha256 of the bytes just written.
    """
    root = Path(tmp_path)
    expected = {}
    for name in FILES:
        data = ("content:" + name).encode("utf-8")
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        expected[name] = hashlib.sha256(data).hexdigest()
    manifest_path = root / DATASET_MANIFEST_RELPATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest_bytes)
    expected[DATASET_MANIFEST_RELPATH] = hashlib.sha256(manifest_bytes).hexdigest()
    return root, expected


# --------------------------------------------------------------------------- #
# identity_report
# --------------------------------------------------------------------------- #

def test_identity_all_ok(tmp_path):
    root, expected = _write_tree(tmp_path)
    report = identity_report(source_root=root, expected_hashes=expected)
    assert report["status"] == "IDENTITY_OK"
    assert set(report["files"]) == set(FILES)
    assert all(entry["status"] == "OK" for entry in report["files"].values())
    assert report["dataset_manifest"]["status"] == "OK"
    assert report["dataset_manifest"]["actual_sha256"] == expected[DATASET_MANIFEST_RELPATH]


def test_identity_tampered_file_is_mismatch(tmp_path):
    root, expected = _write_tree(tmp_path)
    target = FILES[1]
    (root / target).write_bytes(b"tampered bytes")
    report = identity_report(source_root=root, expected_hashes=expected)
    assert report["files"][target]["status"] == "MISMATCH"
    assert report["files"][target]["actual_sha256"] != report["files"][target]["expected_sha256"]
    assert report["status"] == "IDENTITY_MISMATCH"


def test_identity_missing_file_is_incomplete(tmp_path):
    root, expected = _write_tree(tmp_path)
    target = FILES[2]
    (root / target).unlink()
    report = identity_report(source_root=root, expected_hashes=expected)
    assert report["files"][target]["status"] == "MISSING"
    assert report["files"][target]["actual_sha256"] is None
    assert report["status"] == "IDENTITY_INCOMPLETE"


def test_identity_not_reached_semantics(tmp_path):
    root, expected = _write_tree(tmp_path)
    target = FILES[3]
    del expected[target]  # no frozen expectation for this file -> check unreachable
    report = identity_report(source_root=root, expected_hashes=expected)
    entry = report["files"][target]
    assert entry["status"] == "NOT_REACHED"
    assert entry["status"] not in ("FAILED", "MISMATCH", "MISSING")
    assert entry["expected_sha256"] is None
    assert entry["actual_sha256"] is not None  # the file exists; we can still hash it
    assert report["status"] == "IDENTITY_INCOMPLETE"


def test_identity_default_manifest_expects_frozen_constant(tmp_path):
    root, _ = _write_tree(tmp_path)
    # No expected_hashes and no publication packet: the manifest expectation
    # must be the frozen constant, so the synthetic manifest is a MISMATCH.
    report = identity_report(source_root=root)
    assert report["dataset_manifest"]["expected_sha256"] == DATASET_MANIFEST_SHA256
    assert report["dataset_manifest"]["actual_sha256"] != DATASET_MANIFEST_SHA256
    assert report["dataset_manifest"]["status"] == "MISMATCH"


# --------------------------------------------------------------------------- #
# transition_report
# --------------------------------------------------------------------------- #

TRANSITION_KEYS = {
    "operation", "tick", "actual_candidate_output",
    "required_output_for_this_fixture", "verifier_outcome",
    "attempt_occurred", "accepted_result", "next_tick_reached",
    "repair_open", "outer_caller_restored", "first_observed_failed_check",
}


def _write_json(tmp_path, value, name="analysis.json"):
    path = tmp_path / name
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_transition_valid_case_exact_keys(tmp_path):
    analysis = {
        "core_analysis": {
            "stages": [
                {"cjt_id": "C", "tick": 7, "attempted": True, "accepted": True,
                 "returned": True, "committed": True, "expected_symbol": "L2",
                 "proposal_observation": {"reported_decoded_content": {
                     "operation_id": "^6", "symbol": "L2", "effect_kind": "DECOMPOSITION_SIGNAL"}}},
                {"cjt_id": "R", "tick": 8, "attempted": True, "accepted": False,
                 "returned": False, "committed": False, "expected_symbol": "L1"},
            ],
            "R_rpm_after": {"open_repair_ids": []},
            "checks": [{"check": "core_schema", "ok": True}],
            "core_failures": [],
        },
        "outer_caller_restored": True,
    }
    result = transition_report(_write_json(tmp_path, analysis))
    assert set(result.keys()) == TRANSITION_KEYS
    assert result["operation"] == "^6"
    assert result["tick"] == 7
    assert result["actual_candidate_output"] == "L2"
    assert result["required_output_for_this_fixture"] == "L2"
    assert result["verifier_outcome"] == "ACCEPTED"
    assert result["attempt_occurred"] is True
    assert result["accepted_result"] == "L2"
    assert result["next_tick_reached"] is True
    assert result["repair_open"] is False
    assert result["outer_caller_restored"] is True
    assert result["first_observed_failed_check"] is None


def test_transition_next_tick_absent(tmp_path):
    analysis = {
        "core_analysis": {
            "stages": [
                {"cjt_id": "C", "tick": 7, "attempted": True, "accepted": False,
                 "returned": False, "committed": False, "expected_symbol": "L2",
                 "proposal_observation": {"reported_decoded_content": {
                     "operation_id": "^6", "symbol": "L0"}}},
            ],
            "R_rpm_after": {"open_repair_ids": ["repair-abc"]},
            "checks": [],
            "core_failures": [{"type": "RuntimeContractError", "message": "refused"}],
        },
    }
    result = transition_report(_write_json(tmp_path, analysis))
    assert result["next_tick_reached"] is False
    assert result["accepted_result"] is None
    assert result["outer_caller_restored"] is None  # key absent -> explicit None
    assert result["repair_open"] is True
    assert result["verifier_outcome"] == "REFUSED"
    # "not reached" is never reported as "failed".
    assert all(value != "failed" and value != "FAILED" for value in result.values())


def test_transition_wrong_output_names_first_failed_check(tmp_path):
    analysis = {
        "core_analysis": {
            "stages": [
                {"cjt_id": "C", "tick": 7, "attempted": True, "accepted": False,
                 "returned": False, "committed": False, "expected_symbol": "L2",
                 "proposal_observation": {"reported_decoded_content": {
                     "operation_id": "^6", "symbol": "L0"}}},
            ],
            "checks": [
                {"check": "core_schema", "ok": True},
                {"check": "output_symbol_matches_required", "ok": False},
            ],
            "R_rpm_after": {"open_repair_ids": []},
            "core_failures": [],
        },
        "outer_caller_restored": False,
    }
    result = transition_report(_write_json(tmp_path, analysis))
    assert result["actual_candidate_output"] == "L0"
    assert result["required_output_for_this_fixture"] == "L2"
    assert result["first_observed_failed_check"] == "output_symbol_matches_required"


# --------------------------------------------------------------------------- #
# development_scorecard
# --------------------------------------------------------------------------- #

def _summary(accuracy, bit0, bit1, no_effect=0, eq_acc=None, um_acc=None,
             first_wrong=None):
    summary = {
        "cases": 384, "accuracy": accuracy, "bit_accuracy": [bit0, bit1],
        "first_wrong_bit": first_wrong or {"bit_1_count": 1, "bit_2_count": 2,
                                           "none_count": 381, "bit_1_fraction": 1 / 384,
                                           "bit_2_fraction": 2 / 384},
        "no_effect_count": no_effect,
    }
    if eq_acc is not None:
        summary["equality_slice"] = {"cases": 44, "correct": 0, "accuracy": eq_acc}
    if um_acc is not None:
        summary["unit_margin_slice"] = {"cases": 105, "correct": 0, "accuracy": um_acc}
    return summary


def _training_result(metrics):
    return {"schema": "cas-meta2-condition-skill-training/9",
            "status": "COMPLETED_OFFLINE_CANDIDATE_EXPERIMENT", "metrics": metrics}


def test_scorecard_computes_rows(tmp_path):
    metrics = {
        "cas.untrained": {
            "test_instances": _summary(0.25, 0.5, 0.5, no_effect=10, eq_acc=0.30, um_acc=0.40),
            "test_direction_pair": _summary(0.25, 0.5, 0.5, no_effect=11, eq_acc=0.31, um_acc=0.41),
        },
        "cas.trained": {
            "test_instances": _summary(0.60, 0.62, 0.58, no_effect=2, eq_acc=0.70, um_acc=0.65,
                                       first_wrong={"bit_1_count": 3, "bit_2_count": 5,
                                                    "none_count": 376, "bit_1_fraction": 3 / 384,
                                                    "bit_2_fraction": 5 / 384}),
            "test_direction_pair": _summary(0.55, 0.56, 0.54, no_effect=3, eq_acc=0.60, um_acc=0.55),
        },
        "generic_attention.untrained": {
            "test_instances": _summary(0.30, 0.5, 0.5, no_effect=9),
            "test_direction_pair": _summary(0.30, 0.5, 0.5, no_effect=8),
        },
        "generic_attention.trained": {
            "test_instances": _summary(0.28, 0.49, 0.51, no_effect=6),
            "test_direction_pair": _summary(0.27, 0.52, 0.48, no_effect=5),
        },
    }
    path = _write_json(tmp_path, _training_result(metrics), name="result.json")
    card = development_scorecard(path)
    assert card["status"] == "COMPUTED"
    assert len(card["rows"]) == len(FAMILIES) * len(STAGES) * len(TEST_SPLITS)
    by_key = {(row["family"], row["stage"], row["split"]): row for row in card["rows"]}

    trained = by_key[("cas", "trained", "test_instances")]
    assert trained["joint_accuracy"] == 0.60
    assert trained["bit_accuracy"] == [0.62, 0.58]
    assert trained["first_wrong_bit_counts"] == {"bit_1_count": 3, "bit_2_count": 5,
                                                 "none_count": 376}
    assert trained["no_effect_count"] == 2
    assert trained["equality_slice_accuracy"] == 0.70
    assert trained["unit_margin_slice_accuracy"] == 0.65

    # Absent equality/unit-margin slices are NOT_REACHED, not a fake number.
    untrained = by_key[("generic_attention", "untrained", "test_instances")]
    assert untrained["equality_slice_accuracy"] == NOT_REACHED
    assert untrained["unit_margin_slice_accuracy"] == NOT_REACHED

    assert card["improvement"]["cas"]["test_instances"]["improved"] is True
    assert card["improvement"]["cas"]["test_direction_pair"]["improved"] is True
    assert card["improvement"]["generic_attention"]["test_instances"]["improved"] is False
    assert card["improvement"]["generic_attention"]["test_direction_pair"]["improved"] is False

    assert card["overall"]["improved"] == ["cas.test_instances", "cas.test_direction_pair"]
    assert card["overall"]["not_improved"] == [
        "generic_attention.test_instances", "generic_attention.test_direction_pair"]
    assert card["overall"]["not_reached"] == []


def test_scorecard_malformed_returns_error_status(tmp_path):
    path = tmp_path / "result.json"
    path.write_text("{this is not valid json", encoding="utf-8")
    card = development_scorecard(path)
    assert card["status"] == "MALFORMED"
    assert card["status"] != "COMPUTED"


def test_scorecard_wrong_schema_is_malformed(tmp_path):
    path = _write_json(tmp_path, {"schema": "some-other-schema", "metrics": {}},
                       name="result.json")
    card = development_scorecard(path)
    assert card["status"] == "MALFORMED"


def test_scorecard_no_path_is_no_run():
    card = development_scorecard()
    assert card["status"] == "NO_RUN"
    assert card["status"] != "COMPUTED"


def test_scorecard_missing_file_is_no_run(tmp_path):
    card = development_scorecard(tmp_path / "does_not_exist.json")
    assert card["status"] == "NO_RUN"


# --------------------------------------------------------------------------- #
# forbidden-import guard
# --------------------------------------------------------------------------- #

def test_module_imports_no_forbidden_libraries(monkeypatch):
    forbidden = {"torch", "numpy", "sqlite3", "boto3", "botocore",
                 "casformer", "cas_cjt", "cas_meta"}
    original = builtins.__import__
    seen = []

    def guarded(name, *args, **kwargs):
        seen.append(name)
        if name.split(".")[0] in forbidden:
            raise AssertionError("FORBIDDEN_IMPORT:" + name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    import tools.condition_skill_v9_test_points as tp
    spec = importlib.util.spec_from_file_location("isolated_test_points", Path(tp.__file__))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert not forbidden.intersection(name.split(".")[0] for name in seen)
