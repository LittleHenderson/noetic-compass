from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27g_mlp_neuron_cover_steering_spec.py"


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


def test_stage27g_payload_validates_cleanly() -> None:
    stage27g = _load_module("stage27g_spec_payload")

    payload = stage27g.stage27g_payload()

    assert payload["stage"] == "27G"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["stage27f_status"] == "PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS"
    assert payload["required_inputs"]["amplification_scale"] > 1.0
    assert payload["required_inputs"]["polarity_flip_scale"] < 0.0


def test_stage27g_claim_boundary_names_readout_not_generation() -> None:
    stage27g = _load_module("stage27g_spec_boundary")

    boundary = stage27g.stage27g_claim_boundary()

    assert "MLP-neuron covers" in boundary["scope_boundary"]
    assert "free-form generation control" in boundary["forbidden_claims"]
    assert "model-wide control" in boundary["forbidden_claims"]
