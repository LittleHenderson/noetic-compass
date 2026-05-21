from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27n_cross_scale_calibrated_eraser_steering_spec.py"


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


def test_stage27n_payload_validates_cleanly() -> None:
    stage27n = _load_module("stage27n_spec_payload")

    payload = stage27n.stage27n_payload()

    assert payload["status"] == "PREREGISTERED_GPU_REQUIRED"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["model"] == "EleutherAI/pythia-1b"
    assert payload["required_inputs"]["held_out_eval_rows"] == 56
    assert payload["required_inputs"]["stage27m_status"] == "PASS_BOUNDED_ROBUST_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"


def test_stage27n_validation_requires_cross_scale_sources() -> None:
    stage27n = _load_module("stage27n_spec_validation")
    payload = stage27n.stage27n_payload()
    payload["required_inputs"]["stage8_cpl2_status"] = "NULL"
    payload["required_inputs"]["held_out_eval_rows"] = 112

    errors = stage27n.validate_stage27n_payload(payload)

    assert "required_inputs" in errors
