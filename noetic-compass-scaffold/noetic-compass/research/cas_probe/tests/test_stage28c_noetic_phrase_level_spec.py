from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage28c_noetic_phrase_level_realization_spec.py"


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


def test_stage28c_payload_validates() -> None:
    stage28c = _load_module("stage28c_spec_valid")

    payload = stage28c.stage28c_payload()

    assert payload["status"] == "PREREGISTERED_LOCAL_FORWARD_PASS"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["locked_layer"] == 5
    assert payload["claim_boundary"]["pass_status"] == "PASS_BOUNDED_NOETIC_PHRASE_LEVEL_REALIZATION"


def test_stage28c_locks_phrase_level_candidates_and_baseline() -> None:
    stage28c = _load_module("stage28c_spec_candidates")
    payload = stage28c.stage28c_payload()
    inputs = payload["required_inputs"]

    candidates = {row["runtime_name"]: row["stage9_key"] for row in inputs["primary_phrase_level_readouts"]}

    assert candidates == {"phrase_mean": "X_mean", "phrase_last": "X_final"}
    assert inputs["baseline_readout"]["runtime_name"] == "phrase_first"
    assert inputs["baseline_readout"]["stage9_key"] == "X_focus"


def test_stage28c_locks_correction_and_forbidden_claims() -> None:
    stage28c = _load_module("stage28c_spec_gates")
    payload = stage28c.stage28c_payload()
    gates = {gate["name"]: gate["criterion"] for gate in payload["gates"]}

    assert "p<0.025" in gates["corrected_exact_accuracy"]
    forbidden = payload["claim_boundary"]["forbidden_claims"]
    assert "Noetic clusters" in forbidden
    assert "retrained colloquialism classifiers" in forbidden


def test_stage28c_validation_rejects_wrong_candidate_keys() -> None:
    stage28c = _load_module("stage28c_spec_invalid")
    payload = stage28c.stage28c_payload()
    payload["required_inputs"]["primary_phrase_level_readouts"][0]["stage9_key"] = "X_focus"

    errors = stage28c.validate_stage28c_payload(payload)

    assert "required_inputs" in errors
