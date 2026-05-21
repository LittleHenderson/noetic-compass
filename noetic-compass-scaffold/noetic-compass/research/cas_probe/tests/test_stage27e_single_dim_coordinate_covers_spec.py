from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27e_single_dim_coordinate_covers_spec.py"


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


def test_stage27e_payload_validates_cleanly() -> None:
    stage27e = _load_module("stage27e_spec_payload")

    payload = stage27e.stage27e_payload()

    assert payload["stage"] == "27E"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["slices_per_head"] == payload["required_inputs"]["head_dim"]
    assert payload["required_inputs"]["stage27d_status"] == "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS"


def test_stage27e_claim_boundary_forbids_neuron_overclaim() -> None:
    stage27e = _load_module("stage27e_spec_boundary")

    boundary = stage27e.stage27e_claim_boundary()

    assert "not literal neurons" in boundary["scope_boundary"]
    assert "exact neurons" in boundary["forbidden_claims"]
    assert "MLP-neuron" in boundary["forbidden_claims"]
