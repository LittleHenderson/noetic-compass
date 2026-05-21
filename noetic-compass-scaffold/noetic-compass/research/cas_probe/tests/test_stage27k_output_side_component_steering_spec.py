from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27k_output_side_component_steering_spec.py"


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


def test_stage27k_payload_validates_cleanly() -> None:
    stage27k = _load_module("stage27k_spec_payload")

    payload = stage27k.stage27k_payload()

    assert payload["status"] == "PREREGISTERED_GPU_RECOMMENDED"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["stage27j_status"] == "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION"
    assert payload["required_inputs"]["intervention_rows"] == "Stage 27J held-out eval split only"


def test_stage27k_validation_rejects_wrong_scale() -> None:
    stage27k = _load_module("stage27k_spec_validation")
    payload = stage27k.stage27k_payload()
    payload["required_inputs"]["carrier_scale"] = 1.0

    errors = stage27k.validate_stage27k_payload(payload)

    assert "required_inputs" in errors

