from __future__ import annotations

from pathlib import Path
import importlib.util
import sys


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27d_within_head_slice_covers_spec.py"


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


def test_stage27d_payload_validates_cleanly() -> None:
    stage27d = _load_module("stage27d_spec_payload")

    payload = stage27d.stage27d_payload()

    assert payload["stage"] == "27D"
    assert payload["validation"] == {}
    assert payload["required_inputs"]["stage27c_status"] == "PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS"
    assert payload["required_inputs"]["slice_cover_size"] < (
        payload["required_inputs"]["source_cover_size"] * payload["required_inputs"]["slices_per_head"]
    )


def test_stage27d_claim_boundary_forbids_overclaims() -> None:
    stage27d = _load_module("stage27d_spec_boundary")

    forbidden = stage27d.stage27d_claim_boundary()["forbidden_claims"]

    assert "exact neurons" in forbidden
    assert "MLP-neuron" in forbidden
    assert "free-form generation control" in forbidden
    assert "Noetic/40-Element" in forbidden
