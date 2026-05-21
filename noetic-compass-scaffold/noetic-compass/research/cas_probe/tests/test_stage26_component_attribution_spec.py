from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage26_component_attribution_spec.py"


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SPEC)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_stage26_is_preregistered_no_gpu_and_locked_to_stage7() -> None:
    stage26 = _load_module("stage26_spec_locked")
    payload = stage26.stage26_payload()

    assert payload["status"] == "PREREGISTERED_NO_GPU"
    assert payload["required_inputs"]["model"] == "EleutherAI/pythia-160m"
    assert payload["required_inputs"]["locked_readout"] == {"name": "focus_token", "key": "X_focus", "layer": 6}
    assert payload["required_inputs"]["n_foundation_classes"] == 28
    assert payload["validation"] == {}


def test_stage26_component_scope_is_head_and_mlp_block_level() -> None:
    stage26 = _load_module("stage26_spec_scope")
    scope = stage26.stage26_payload()["component_scope"]

    assert scope["attention_heads"]["layers"] == [0, 1, 2, 3, 4, 5]
    assert scope["attention_heads"]["heads_per_layer"] == 12
    assert scope["attention_heads"]["total_heads"] == 72
    assert scope["mlp_blocks"]["total_blocks"] == 6
    assert "deferred" in scope["mlp_blocks"]["neuron_level"]


def test_stage26_gates_include_alignment_ablation_and_specificity() -> None:
    stage26 = _load_module("stage26_spec_gates")
    gates = {gate["name"]: gate for gate in stage26.stage26_payload()["gates"]}

    assert gates["alignment_enrichment"]["kind"] == "primary"
    assert gates["targeted_ablation_drop"]["kind"] == "causal"
    assert gates["class_specificity"]["kind"] == "causal"
    assert "random" in gates["sanity_controls"]["criterion"]


def test_stage26_claim_boundary_forbids_exact_neurons_and_generation_control() -> None:
    stage26 = _load_module("stage26_spec_boundary")
    boundary = stage26.stage26_payload()["claim_boundary"]

    assert boundary["pass_status"] == "PASS_BOUNDED_COMPONENT_ATTRIBUTION"
    assert boundary["null_status"] == "NULL_COMPONENT_ATTRIBUTION_NOT_ESTABLISHED"
    assert "exact neurons" in boundary["forbidden_claims"]
    assert "free-form generation control" in boundary["forbidden_claims"]
