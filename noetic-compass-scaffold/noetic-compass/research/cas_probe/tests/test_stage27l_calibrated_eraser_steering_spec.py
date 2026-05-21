from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27l_calibrated_eraser_steering_spec.py"


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


def test_stage27l_payload_validates_cleanly() -> None:
    stage27l = _load_module("stage27l_spec_payload")

    payload = stage27l.stage27l_payload()

    assert payload["status"] == "PREREGISTERED_GPU_RECOMMENDED"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["stage27k_status"] == "GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL"
    assert payload["required_inputs"]["evaluation_rows"] == "Stage 27J held-out eval split"


def test_stage27l_validation_rejects_bad_scale_grid() -> None:
    stage27l = _load_module("stage27l_spec_validation")
    payload = stage27l.stage27l_payload()
    payload["required_inputs"]["eraser_scale_grid"] = [-0.1, 0.5]

    errors = stage27l.validate_stage27l_payload(payload)

    assert "required_inputs" in errors

