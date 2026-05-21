from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27b_component_guided_sonar_spec.py"


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


def test_stage27b_payload_validates() -> None:
    stage27b = _load_module("stage27b_spec_valid")

    payload = stage27b.stage27b_payload()

    assert payload["status"] == "PREREGISTERED_NO_GPU"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["locked_readout"]["layer"] == 6
    assert payload["claim_boundary"]["pass_status"] == "PASS_BOUNDED_COMPONENT_GUIDED_CONTRAST_SONAR"


def test_stage27b_scope_reserves_40_element_component_claims() -> None:
    stage27b = _load_module("stage27b_spec_scope")
    payload = stage27b.stage27b_payload()

    boundary = payload["claim_boundary"]
    assert "40-Element" in boundary["scope_boundary"]
    assert "exact neurons" in boundary["forbidden_claims"]
    assert "free-form generation control" in boundary["forbidden_claims"]


def test_stage27b_validation_rejects_wrong_layer() -> None:
    stage27b = _load_module("stage27b_spec_invalid")
    payload = stage27b.stage27b_payload()
    payload["required_inputs"]["locked_readout"]["layer"] = 5

    errors = stage27b.validate_stage27b_payload(payload)

    assert "required_inputs" in errors
