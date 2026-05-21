from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27h_prefix_neuron_steering.py"


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


def test_load_status_contract_checks_expected_status() -> None:
    stage27h = _load_module("stage27h_runner_contract")
    path = ROOT / ".tmp_stage27h_status_contract.json"
    try:
        path.write_text(json.dumps({"status": "PASS_OK"}), encoding="utf-8")
        contract = stage27h._load_status_contract(path, "PASS_OK")
    finally:
        path.unlink(missing_ok=True)

    assert contract["formal_gate_valid"] is True
    assert contract["source_status"] == "PASS_OK"


def test_model_layers_supports_gpt_neox_wrapper() -> None:
    stage27h = _load_module("stage27h_runner_layers")

    class Wrapper:
        pass

    model = Wrapper()
    model.gpt_neox = Wrapper()
    model.gpt_neox.layers = ["layer0"]

    assert stage27h._model_layers(model) == ["layer0"]


def test_score_continuation_with_hook_changes_logits() -> None:
    stage27h = _load_module("stage27h_runner_hook")

    class DummyTokenizer:
        def encode(self, text: str, add_special_tokens: bool = False):
            del add_special_tokens
            return [0] if text == "p" else [1]

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

    class Body(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.layers = torch.nn.ModuleList([Layer()])

    class DummyModel(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.gpt_neox = Body()

        def forward(self, input_ids: torch.Tensor, use_cache: bool = False):
            del use_cache
            hidden = torch.ones((1, input_ids.shape[1], 2), dtype=torch.float32, device=input_ids.device)
            hidden = self.gpt_neox.layers[0].mlp(hidden)
            logits = torch.zeros((1, input_ids.shape[1], 2), dtype=torch.float32, device=input_ids.device)
            logits[:, :, 1] = hidden[:, :, 1]
            return type("Out", (), {"logits": logits})()

    base = stage27h._score_continuation(DummyModel(), DummyTokenizer(), "p", "c", torch.device("cpu"))
    scaled = stage27h._score_continuation(
        DummyModel(),
        DummyTokenizer(),
        "p",
        "c",
        torch.device("cpu"),
        neurons=[stage27h.MLPNeuron(0, 1)],
        scale=2.0,
    )

    assert scaled["mean_logprob"] > base["mean_logprob"]


def test_status_boundaries() -> None:
    stage27h = _load_module("stage27h_runner_status")
    report = {
        "source_contracts": {
            "stage7_prefix": {"formal_gate_valid": True},
            "stage27g": {"formal_gate_valid": True},
        },
        "stage27f_contract": {"formal_gate_valid": True},
        "gates": {
            "min_prefix_delta_vs_none": 0.1,
            "min_random_win_share": 0.6,
            "max_sign_test_p": 0.05,
            "min_positive_effect_share": 0.55,
        },
        "evaluation": {
            "effects": {
                "prefix_delta_vs_none": {"mean": 0.2},
                "prefix_target_amplification_increment": {"mean": 1.0, "positive_share": 0.9},
                "random_prefix_target_amplification_mean_increment": {"mean": 0.1},
                "prefix_target_flip_reduction": {"mean": 2.0, "positive_share": 0.9},
                "random_prefix_target_flip_mean_reduction": {"mean": 0.2},
            },
            "paired_controls": {
                "prefix_target_amplification_vs_random_mean": {"win_share": 0.7, "sign_test_p": 0.01},
                "prefix_target_flip_vs_random_mean": {"win_share": 0.8, "sign_test_p": 0.001},
            },
        },
    }

    assert stage27h._status_from_gates(report) == "PASS_BOUNDED_PREFIX_PLUS_NEURON_STEERING"
    report["evaluation"]["paired_controls"]["prefix_target_flip_vs_random_mean"]["win_share"] = 0.4
    assert stage27h._status_from_gates(report) == "GREY_PREFIX_PLUS_NEURON_STEERING_PARTIAL"
    report["evaluation"]["paired_controls"]["prefix_target_amplification_vs_random_mean"]["win_share"] = 0.4
    report["evaluation"]["effects"]["prefix_target_amplification_increment"]["mean"] = -1.0
    assert stage27h._status_from_gates(report) == "NULL_PREFIX_PLUS_NEURON_STEERING_NOT_ESTABLISHED"
    report["source_contracts"]["stage7_prefix"]["formal_gate_valid"] = False
    assert (
        stage27h._status_from_gates(report)
        == "STAGE27H_PREFIX_NEURON_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    )
