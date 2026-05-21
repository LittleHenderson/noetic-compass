from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27j_output_side_component_attribution_spec.py"


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


def test_stage27j_payload_validates_cleanly() -> None:
    stage27j = _load_module("stage27j_spec_payload")

    payload = stage27j.stage27j_payload()

    assert payload["status"] == "PREREGISTERED_GPU_RECOMMENDED"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["stage27i_status"] == "NULL_PREDICTION_POSITION_NEURON_STEERING_NOT_ESTABLISHED"
    assert payload["required_inputs"]["intervention_positions"] == "continuation_prediction_positions_only"


def test_stage27j_validation_rejects_wrong_source_status() -> None:
    stage27j = _load_module("stage27j_spec_validation")
    payload = stage27j.stage27j_payload()
    payload["required_inputs"]["stage27i_status"] = "PASS_WRONG"

    errors = stage27j.validate_stage27j_payload(payload)

    assert "required_inputs" in errors

