from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage28d_noetic_cluster_realization_spec.py"


def _load_module(name: str):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, SPEC)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_stage28d_payload_validates() -> None:
    stage28d = _load_module("stage28d_spec_valid")

    payload = stage28d.stage28d_payload()

    assert payload["status"] == "PREREGISTERED_LOCAL_FORWARD_PASS"
    assert payload["validation"] == {}
    assert payload["claim_boundary"]["pass_status"] == "PASS_BOUNDED_NOETIC_CLUSTER_REALIZATION"


def test_stage28d_fixture_is_balanced_multilabel_and_natural_language() -> None:
    stage28d = _load_module("stage28d_spec_fixture")
    payload = stage28d.stage28d_payload()

    counts: dict[str, int] = {}
    for row in payload["cluster_fixture"]:
        counts[row["cluster"]] = counts.get(row["cluster"], 0) + 1
        assert len(row["targets"]) == 2
        assert "^" not in row["phrase"]
        assert "|" not in row["phrase"]

    assert len(payload["cluster_fixture"]) == 24
    assert len(counts) == 8
    assert set(counts.values()) == {3}


def test_stage28d_locks_phrase_level_candidates_and_corrected_gate() -> None:
    stage28d = _load_module("stage28d_spec_gates")
    payload = stage28d.stage28d_payload()
    inputs = payload["required_inputs"]
    candidates = {row["runtime_name"]: row["stage9_key"] for row in inputs["primary_phrase_level_readouts"]}
    gates = {gate["name"]: gate["criterion"] for gate in payload["gates"]}

    assert candidates == {"phrase_mean": "X_mean", "phrase_last": "X_final"}
    assert "18/24" in gates["corrected_sign_test"]
    assert "p<0.025" in gates["corrected_sign_test"]


def test_stage28d_validation_rejects_single_label_cluster() -> None:
    stage28d = _load_module("stage28d_spec_invalid")
    payload = stage28d.stage28d_payload()
    payload["cluster_fixture"][0]["targets"] = ("^2",)

    errors = stage28d.validate_stage28d_payload(payload)

    assert "cluster_fixture" in errors
