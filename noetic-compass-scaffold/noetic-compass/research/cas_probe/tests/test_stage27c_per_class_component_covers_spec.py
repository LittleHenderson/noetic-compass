from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27c_per_class_component_covers_spec.py"


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


def test_stage27c_payload_validates() -> None:
    stage27c = _load_module("stage27c_spec_valid")

    payload = stage27c.stage27c_payload()

    assert payload["status"] == "PREREGISTERED_GPU_RECOMMENDED"
    assert payload["validation"] == {}
    assert payload["claim_boundary"]["pass_status"] == "PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS"


def test_stage27c_locks_selected_family_and_strict_subcover() -> None:
    stage27c = _load_module("stage27c_spec_components")
    payload = stage27c.stage27c_payload()
    inputs = payload["required_inputs"]

    assert tuple(inputs["global_selected_components"]) == ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")
    assert inputs["per_class_cover_size"] == 3
    assert inputs["per_class_cover_size"] < len(inputs["global_selected_components"])


def test_stage27c_locks_train_test_separation_and_controls() -> None:
    stage27c = _load_module("stage27c_spec_gates")
    payload = stage27c.stage27c_payload()
    gates = {gate["name"] for gate in payload["gates"]}

    assert "learn_eval_separation" in gates
    assert "same_size_global_control" in gates
    assert "matched_random_subset_control" in gates


def test_stage27c_validation_rejects_full_size_cover() -> None:
    stage27c = _load_module("stage27c_spec_invalid")
    payload = stage27c.stage27c_payload()
    payload["required_inputs"]["per_class_cover_size"] = 6

    errors = stage27c.validate_stage27c_payload(payload)

    assert "required_inputs" in errors
