from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27f_targeted_mlp_neuron_covers_spec.py"


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


def test_stage27f_payload_validates_cleanly() -> None:
    stage27f = _load_module("stage27f_spec_payload")

    payload = stage27f.stage27f_payload()

    assert payload["stage"] == "27F"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["stage27e_status"] == "PASS_BOUNDED_SINGLE_DIM_COORDINATE_COVERS"
    assert payload["required_inputs"]["neuron_cover_size"] < payload["required_inputs"]["mlp_intermediate_dim"]


def test_stage27f_claim_boundary_is_neuron_but_not_circuit() -> None:
    stage27f = _load_module("stage27f_spec_boundary")

    boundary = stage27f.stage27f_claim_boundary()

    assert "MLP intermediate neurons" in boundary["scope_boundary"]
    assert "complete circuits" in boundary["forbidden_claims"]
    assert "free-form generation control" in boundary["forbidden_claims"]
