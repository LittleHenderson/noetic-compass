from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage27_component_path_patching_spec.py"


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SPEC)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_stage27_is_preregistered_and_uses_stage26_family() -> None:
    stage27 = _load_module("stage27_spec_locked")
    payload = stage27.stage27_payload()

    assert payload["status"] == "PREREGISTERED_NO_GPU"
    assert payload["required_inputs"]["stage26_status"] == "PASS_BOUNDED_COMPONENT_ATTRIBUTION"
    assert payload["required_inputs"]["selected_components"] == ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")
    assert payload["validation"] == {}


def test_stage27_scope_is_attention_head_patching() -> None:
    stage27 = _load_module("stage27_spec_scope")
    scope = stage27.stage27_payload()["component_scope"]

    assert scope["primary_components"]["kind"] == "attention_head"
    assert scope["patching_unit"] == "full-sequence selected-head slice, not only focus-token slice"
    assert scope["target_probe_layer"] == 6
    assert "not primary" in scope["mlp_blocks"]


def test_stage27_gates_include_sufficiency_and_controls() -> None:
    stage27 = _load_module("stage27_spec_gates")
    gates = {gate["name"]: gate for gate in stage27.stage27_payload()["gates"]}

    assert gates["patch_restoration"]["kind"] == "causal_sufficiency"
    assert gates["matched_patch_control"]["kind"] == "causal_control"
    assert "50%" in gates["patch_restoration"]["criterion"]
    assert "p < 0.05" in gates["matched_patch_control"]["criterion"]


def test_stage27_claim_boundary_forbids_overclaims() -> None:
    stage27 = _load_module("stage27_spec_boundary")
    boundary = stage27.stage27_payload()["claim_boundary"]

    assert boundary["pass_status"] == "PASS_BOUNDED_COMPONENT_PATH_PATCHING"
    assert boundary["null_status"] == "NULL_COMPONENT_PATH_PATCHING_NOT_ESTABLISHED"
    assert "exact neurons" in boundary["forbidden_claims"]
    assert "cross-model component generality" in boundary["forbidden_claims"]
