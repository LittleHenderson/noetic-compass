from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27h_prefix_neuron_steering_spec.py"


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


def test_stage27h_payload_validates_cleanly() -> None:
    stage27h = _load_module("stage27h_spec_payload")

    payload = stage27h.stage27h_payload()

    assert payload["stage"] == "27H"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["stage27g_status"] == "PASS_BOUNDED_MLP_NEURON_COVER_STEERING"
    assert payload["required_inputs"]["amplification_scale"] > 1.0
    assert payload["required_inputs"]["polarity_flip_scale"] < 0.0


def test_stage27h_claim_boundary_is_likelihood_not_open_ended_generation() -> None:
    stage27h = _load_module("stage27h_spec_boundary")

    boundary = stage27h.stage27h_claim_boundary()

    assert "output-distribution likelihood steering" in boundary["scope_boundary"]
    assert "open-ended generation control" in boundary["forbidden_claims"]
    assert "model-wide control" in boundary["forbidden_claims"]
