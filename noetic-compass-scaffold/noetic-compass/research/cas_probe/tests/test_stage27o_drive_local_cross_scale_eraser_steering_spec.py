from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27o_drive_local_cross_scale_eraser_steering_spec.py"


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


def test_stage27o_payload_validates_cleanly() -> None:
    stage27o = _load_module("stage27o_spec_payload")

    payload = stage27o.stage27o_payload()

    assert payload["status"] == "PREREGISTERED_GPU_REQUIRED"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["stage27n_status"] == "GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL"
    assert payload["required_inputs"]["selection_seed"] == 27041


def test_stage27o_validation_requires_stage27n_grey() -> None:
    stage27o = _load_module("stage27o_spec_validation")
    payload = stage27o.stage27o_payload()
    payload["required_inputs"]["stage27n_status"] = "PASS"
    payload["required_inputs"]["held_out_eval_rows"] = 112

    errors = stage27o.validate_stage27o_payload(payload)

    assert "required_inputs" in errors
