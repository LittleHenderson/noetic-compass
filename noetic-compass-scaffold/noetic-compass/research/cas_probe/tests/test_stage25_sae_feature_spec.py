from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "stage25_sae_feature_spec.py"


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, SPEC)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_stage25_is_authorized_and_locked_to_stage7_layer6() -> None:
    stage25 = _load_module("stage25_spec_locked")
    payload = stage25.stage25_payload()

    assert payload["status"] == "AUTHORIZED_GPU_SAE_PREREGISTERED"
    assert payload["required_inputs"]["activations"] == "stage7_foundation_pilot_activations_20260517.npz"
    assert payload["required_inputs"]["activation_layer"] == 6
    assert payload["required_inputs"]["probe_labels"] == 28
    assert payload["validation"] == {}


def test_stage25_sae_config_is_overcomplete_and_bounded() -> None:
    stage25 = _load_module("stage25_spec_config")
    config = stage25.stage25_payload()["training_config"]

    assert config["input_dim"] == 768
    assert config["n_features"] == 6144
    assert config["n_features"] > config["input_dim"]
    assert config["max_steps"] == 5000
    assert config["expected_gpu_budget_usd"] == "200-500"


def test_stage25_gates_include_alignment_specificity_and_causal_drop() -> None:
    stage25 = _load_module("stage25_spec_gates")
    gates = {gate["name"]: gate for gate in stage25.stage25_payload()["gates"]}

    assert "cas_alignment" in gates
    assert "feature_specificity" in gates
    assert "causal_feature_drop" in gates
    assert gates["causal_feature_drop"]["kind"] == "causal"


def test_stage25_claim_boundary_forbids_exact_neuron_and_generation_claims() -> None:
    stage25 = _load_module("stage25_spec_boundary")
    boundary = stage25.stage25_payload()["claim_boundary"]
    forbidden = boundary["forbidden_claims"]

    assert boundary["pass_status"] == "PASS_BOUNDED_SAE_FEATURE_READOUT"
    assert boundary["null_status"] == "NULL_SAE_FEATURE_READOUT_NOT_ESTABLISHED"
    assert "exact causal neurons" in forbidden
    assert "generated-language steering" in forbidden
    assert "internal CAS compiler" in forbidden
