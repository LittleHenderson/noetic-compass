from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27g_mlp_neuron_cover_steering.py"


def _load_module(name: str):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, RUNNER)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_stage27f_contract_extracts_neuron_covers() -> None:
    stage27g = _load_module("stage27g_runner_contract")
    report = {
        "status": "PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS",
        "artifact_contract": {"status": "LOCKED_ARTIFACT_MATCH"},
        "stage27c_contract": {"formal_gate_valid": True},
        "stage27e_contract": {"formal_gate_valid": True},
        "split_contract": {"learn_eval_disjoint": True},
        "mlp_intermediate_dim": 3072,
        "neuron_cover_size": 2,
        "per_class_neuron_covers": {label: ["L5N1", "L5N2"] for label in stage27g._FOUNDATION_LABELS},
    }
    path = ROOT / ".tmp_stage27g_stage27f_contract.json"
    try:
        path.write_text(json.dumps(report), encoding="utf-8")
        contract = stage27g._load_stage27f_contract(path)
    finally:
        path.unlink(missing_ok=True)

    assert contract["formal_gate_valid"] is True
    assert contract["mlp_intermediate_dim"] == 3072
    assert contract["per_class_neuron_covers"]["F1T"] == ["L5N1", "L5N2"]


def test_neuron_targets_groups_by_layer() -> None:
    stage27g = _load_module("stage27g_runner_targets")

    targets = stage27g._neuron_targets(
        [stage27g.MLPNeuron(5, 10), stage27g.MLPNeuron(5, 11), stage27g.MLPNeuron(1, 3)]
    )

    assert targets == {5: {10, 11}, 1: {3}}


def test_forward_scale_hook_changes_selected_mlp_inputs() -> None:
    stage27g = _load_module("stage27g_runner_hook")

    class Dense(torch.nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return x

    class MLP(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.dense_4h_to_h = Dense()

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.dense_4h_to_h(x)

    class Layer(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.mlp = MLP()

    class DummyModel(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.layers = torch.nn.ModuleList([Layer()])

        def forward(self, **_kwargs):
            x = torch.ones((1, 2, 4), dtype=torch.float32)
            y = self.layers[0].mlp(x)
            return type("Out", (), {"hidden_states": [y, y, y, y, y, y, y]})()

    vec = stage27g._forward_vec_with_mlp_neuron_scale(
        {"input_ids": torch.tensor([[1, 2]])},
        0,
        DummyModel(),
        neurons=[stage27g.MLPNeuron(0, 1), stage27g.MLPNeuron(0, 3)],
        scale=2.0,
    )

    assert vec.tolist() == [1.0, 2.0, 1.0, 2.0]


def test_status_boundaries() -> None:
    stage27g = _load_module("stage27g_runner_status")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "stage27f_contract": {"formal_gate_valid": True},
        "gates": {
            "min_random_win_share": 0.6,
            "max_sign_test_p": 0.05,
            "min_positive_effect_share": 0.55,
        },
        "evaluation": {
            "effects": {
                "target_amplification_delta": {"mean": 1.0, "positive_share": 0.9},
                "random_target_amplification_mean_delta": {"mean": 0.1},
                "target_flip_reduction": {"mean": 2.0, "positive_share": 0.9},
                "random_target_flip_mean_reduction": {"mean": 0.2},
            },
            "paired_controls": {
                "target_amplification_vs_random_mean": {"win_share": 0.7, "sign_test_p": 0.01},
                "target_flip_vs_random_mean": {"win_share": 0.8, "sign_test_p": 0.001},
            },
        },
    }

    assert stage27g._status_from_gates(report) == "PASS_BOUNDED_MLP_NEURON_COVER_STEERING"
    report["evaluation"]["paired_controls"]["target_flip_vs_random_mean"]["win_share"] = 0.4
    assert stage27g._status_from_gates(report) == "GREY_MLP_NEURON_COVER_STEERING_PARTIAL"
    report["evaluation"]["paired_controls"]["target_amplification_vs_random_mean"]["win_share"] = 0.4
    report["evaluation"]["effects"]["target_amplification_delta"]["mean"] = -1.0
    assert stage27g._status_from_gates(report) == "NULL_MLP_NEURON_COVER_STEERING_NOT_ESTABLISHED"
    report["artifact_contract"]["formal_gate_valid"] = False
    assert (
        stage27g._status_from_gates(report)
        == "STAGE27G_MLP_NEURON_COVER_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    )
