from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27i_prediction_position_steering_spec.py"


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


def test_stage27i_payload_validates_cleanly() -> None:
    stage27i = _load_module("stage27i_spec_payload")

    payload = stage27i.stage27i_payload()

    assert payload["stage"] == "27I"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["stage27h_status"] == "NULL_PREFIX_PLUS_NEURON_STEERING_NOT_ESTABLISHED"
    assert payload["required_inputs"]["intervention_positions"] == "continuation_prediction_positions_only"
    assert payload["required_inputs"]["downstream_trace_layers"][-1] == 12


def test_stage27i_claim_boundary_is_prediction_position_not_model_wide() -> None:
    stage27i = _load_module("stage27i_spec_boundary")

    boundary = stage27i.stage27i_claim_boundary()

    assert "prediction-position-localized likelihood steering" in boundary["scope_boundary"]
    assert "open-ended generation control" in boundary["forbidden_claims"]
    assert "model-wide control" in boundary["forbidden_claims"]
