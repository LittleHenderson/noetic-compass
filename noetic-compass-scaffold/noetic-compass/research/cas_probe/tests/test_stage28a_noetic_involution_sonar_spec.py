from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage28a_noetic_involution_sonar_spec.py"


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


def test_stage28a_payload_validates() -> None:
    stage28a = _load_module("stage28a_spec_valid")

    payload = stage28a.stage28a_payload()

    assert payload["status"] == "PREREGISTERED_NO_GPU"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["locked_readout"]["layer"] == 5
    assert payload["claim_boundary"]["pass_status"] == "PASS_BOUNDED_NOETIC_INVOLUTION_SONAR"


def test_stage28a_locks_involution_pairs_and_forbidden_claims() -> None:
    stage28a = _load_module("stage28a_spec_pairs")
    payload = stage28a.stage28a_payload()

    assert tuple(tuple(x) for x in payload["required_inputs"]["involution_pairs"]) == (
        ("^2", "^3"),
        ("^5", "^6"),
        ("^8", "^9"),
    )
    forbidden = payload["claim_boundary"]["forbidden_claims"]
    assert "Noetic clusters" in forbidden
    assert "free-form generation control" in forbidden


def test_stage28a_validation_rejects_wrong_layer() -> None:
    stage28a = _load_module("stage28a_spec_invalid")
    payload = stage28a.stage28a_payload()
    payload["required_inputs"]["locked_readout"]["layer"] = 6

    errors = stage28a.validate_stage28a_payload(payload)

    assert "required_inputs" in errors
