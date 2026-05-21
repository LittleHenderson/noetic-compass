from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27m_robust_calibrated_eraser_steering_spec.py"


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


def test_stage27m_payload_validates_cleanly() -> None:
    stage27m = _load_module("stage27m_spec_payload")

    payload = stage27m.stage27m_payload()

    assert payload["status"] == "PREREGISTERED_GPU_RECOMMENDED"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["held_out_eval_rows"] == 245
    assert payload["required_inputs"]["stage27l_status"] == "PASS_BOUNDED_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"


def test_stage27m_validation_requires_large_eval() -> None:
    stage27m = _load_module("stage27m_spec_validation")
    payload = stage27m.stage27m_payload()
    payload["required_inputs"]["held_out_eval_rows"] = 112

    errors = stage27m.validate_stage27m_payload(payload)

    assert "required_inputs" in errors

