from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27k_output_side_component_steering.py"


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


def test_load_stage27j_contract_extracts_covers() -> None:
    stage27k = _load_module("stage27k_runner_contract")
    path = ROOT / ".tmp_stage27k_stage27j_contract.json"
    try:
        path.write_text(
            json.dumps(
                {
                    "status": "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION",
                    "carrier_cover": ["L8H1"],
                    "eraser_cover": ["L11MLP"],
                }
            ),
            encoding="utf-8",
        )
        contract = stage27k._load_stage27j_contract(path)
    finally:
        path.unlink(missing_ok=True)

    assert contract["formal_gate_valid"] is True
    assert contract["carrier_cover"] == ["L8H1"]
    assert contract["eraser_cover"] == ["L11MLP"]


def test_component_scale_targets_groups_heads_and_mlps() -> None:
    stage27k = _load_module("stage27k_runner_targets")

    heads, mlps = stage27k._component_scale_targets(
        [
            ([stage27k.Component("head", 8, 1), stage27k.Component("mlp", 10, None)], 2.0),
            ([stage27k.Component("head", 8, 2)], 0.0),
        ]
    )

    assert heads == {8: {1: 2.0, 2: 0.0}}
    assert mlps == {10: 2.0}


def test_score_continuation_component_scaling_changes_prediction_position() -> None:
    stage27k = _load_module("stage27k_runner_hook")

    class DummyTokenizer:
        def encode(self, text: str, add_special_tokens: bool = False):
            del add_special_tokens
            return [0] if text == "p" else [1]

    class Dense(torch.nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return x

    class Attention(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.dense = Dense()

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.dense(x)

    class MLP(torch.nn.Module):
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return x

    class Layer(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.attention = Attention()
            self.mlp = MLP()

    class Body(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.layers = torch.nn.ModuleList([Layer()])

    class Config:
        hidden_size = 4
        num_attention_heads = 2

    class DummyModel(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.config = Config()
            self.gpt_neox = Body()

        def forward(self, input_ids: torch.Tensor, use_cache: bool = False):
            del use_cache
            hidden = torch.ones((1, input_ids.shape[1], 4), dtype=torch.float32, device=input_ids.device)
            hidden = self.gpt_neox.layers[0].attention(hidden)
            hidden = self.gpt_neox.layers[0].mlp(hidden)
            logits = torch.zeros((1, input_ids.shape[1], 2), dtype=torch.float32, device=input_ids.device)
            logits[:, :, 1] = hidden[:, :, 1]
            return type("Out", (), {"logits": logits})()

    base = stage27k._score_continuation_component_scaled(
        DummyModel(), DummyTokenizer(), "p", "c", torch.device("cpu")
    )
    amplified = stage27k._score_continuation_component_scaled(
        DummyModel(),
        DummyTokenizer(),
        "p",
        "c",
        torch.device("cpu"),
        component_scales=[([stage27k.Component("head", 0, 0)], 2.0)],
    )
    suppressed = stage27k._score_continuation_component_scaled(
        DummyModel(),
        DummyTokenizer(),
        "p",
        "c",
        torch.device("cpu"),
        component_scales=[([stage27k.Component("mlp", 0, None)], 0.0)],
    )

    assert amplified["prediction_positions"] == [0]
    assert amplified["mean_logprob"] > base["mean_logprob"]
    assert suppressed["mean_logprob"] < base["mean_logprob"]


def test_status_boundaries() -> None:
    stage27k = _load_module("stage27k_runner_status")
    report = {
        "source_contracts": {
            "stage7_prefix": {"formal_gate_valid": True},
            "stage27j": {"formal_gate_valid": True},
        },
        "split_contract": {"held_out_eval_only": True},
        "gates": {
            "min_random_win_share": 0.6,
            "max_sign_test_p": 0.05,
            "min_positive_effect_share": 0.55,
        },
        "evaluation": {
            "effects": {
                "combined_increment": {"mean": 1.0, "positive_share": 0.9},
                "random_combined_mean_increment": {"mean": 0.1},
                "carrier_flip_reduction": {"mean": 2.0, "positive_share": 0.9},
                "random_carrier_flip_mean_reduction": {"mean": 0.2},
            },
            "paired_controls": {
                "combined_vs_random_mean": {"win_share": 0.7, "sign_test_p": 0.01},
                "carrier_flip_vs_random_mean": {"win_share": 0.8, "sign_test_p": 0.001},
            },
        },
    }

    assert stage27k._status_from_gates(report) == "PASS_BOUNDED_OUTPUT_SIDE_COMPONENT_STEERING_WITH_POLARITY_CONTROL"
    report["evaluation"]["paired_controls"]["carrier_flip_vs_random_mean"]["win_share"] = 0.4
    assert stage27k._status_from_gates(report) == "PASS_BOUNDED_OUTPUT_SIDE_COMPONENT_STEERING"
    report["evaluation"]["paired_controls"]["combined_vs_random_mean"]["win_share"] = 0.56
    assert stage27k._status_from_gates(report) == "GREY_OUTPUT_SIDE_COMPONENT_STEERING_PARTIAL"
    report["evaluation"]["paired_controls"]["combined_vs_random_mean"]["win_share"] = 0.4
    report["evaluation"]["effects"]["combined_increment"]["mean"] = -1.0
    assert stage27k._status_from_gates(report) == "NULL_OUTPUT_SIDE_COMPONENT_STEERING_NOT_ESTABLISHED"
    report["source_contracts"]["stage7_prefix"]["formal_gate_valid"] = False
    assert (
        stage27k._status_from_gates(report)
        == "STAGE27K_OUTPUT_SIDE_COMPONENT_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    )

