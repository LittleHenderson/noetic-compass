from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27j_output_side_component_attribution.py"


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


def test_prediction_positions_are_logit_positions() -> None:
    stage27j = _load_module("stage27j_runner_positions")

    assert stage27j._prediction_positions(2, 3) == (1, 2, 3)


def test_candidate_components_include_heads_and_mlp_blocks() -> None:
    stage27j = _load_module("stage27j_runner_components")

    components = stage27j._candidate_components((8,))

    assert len(components) == 13
    assert components[0].name == "L8H0"
    assert components[-1].name == "L8MLP"


def test_split_by_drive_is_balanced_and_disjoint() -> None:
    stage27j = _load_module("stage27j_runner_split")
    rows = [
        {"sample_id": f"d{drive}_{idx}", "foundation_drive": drive}
        for drive in range(1, 8)
        for idx in range(4)
    ]

    split = stage27j._split_by_drive(rows, 2, 2)

    assert split["learn_eval_disjoint"] is True
    assert len(split["learn_rows"]) == 14
    assert len(split["eval_rows"]) == 14


def test_random_controls_match_layer_kind_for_heads_and_kind_for_singleton_mlp() -> None:
    stage27j = _load_module("stage27j_runner_random_controls")
    candidates = stage27j._candidate_components((8, 9))

    covers = stage27j._matched_random_covers(["L8H0", "L8MLP"], candidates, n_random=4, seed=1)
    profile = stage27j._control_match_profile(["L8H0", "L8MLP"], candidates)

    assert len(covers) == 4
    for cover in covers:
        assert len(cover) == 2
        assert cover[0].startswith("L8H")
        assert cover[0] != "L8H0"
        assert "MLP" in cover[1]
        assert cover[1] != "L8MLP"
    assert profile["rows"][0]["match_level"] == "layer_kind_exact"
    assert profile["rows"][1]["match_level"] == "kind_only_singleton_layer"


def test_score_continuation_can_ablate_head_or_mlp_at_prediction_position() -> None:
    stage27j = _load_module("stage27j_runner_hook")

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

    base = stage27j._score_continuation_component_ablated(
        DummyModel(), DummyTokenizer(), "p", "c", torch.device("cpu")
    )
    head_ablated = stage27j._score_continuation_component_ablated(
        DummyModel(),
        DummyTokenizer(),
        "p",
        "c",
        torch.device("cpu"),
        components=[stage27j.Component("head", 0, 0)],
    )
    mlp_ablated = stage27j._score_continuation_component_ablated(
        DummyModel(),
        DummyTokenizer(),
        "p",
        "c",
        torch.device("cpu"),
        components=[stage27j.Component("mlp", 0, None)],
    )

    assert head_ablated["prediction_positions"] == [0]
    assert head_ablated["mean_logprob"] < base["mean_logprob"]
    assert mlp_ablated["mean_logprob"] < base["mean_logprob"]


def test_status_boundaries() -> None:
    stage27j = _load_module("stage27j_runner_status")
    report = {
        "source_contracts": {
            "stage7_prefix": {"formal_gate_valid": True},
            "stage27i": {"formal_gate_valid": True},
        },
        "split_contract": {"learn_eval_disjoint": True},
        "gates": {
            "min_random_win_share": 0.6,
            "max_sign_test_p": 0.05,
            "min_positive_effect_share": 0.55,
        },
        "evaluation": {
            "carrier_cover": {
                "drop": {"mean": 1.0, "positive_share": 0.9},
                "random_mean_drop": {"mean": 0.1},
                "drop_vs_random": {"win_share": 0.7, "sign_test_p": 0.01},
            },
            "eraser_cover": {
                "lift": {"mean": 1.0, "positive_share": 0.9},
                "random_mean_lift": {"mean": 0.1},
                "lift_vs_random": {"win_share": 0.7, "sign_test_p": 0.01},
            },
        },
    }

    assert stage27j._status_from_gates(report) == "PASS_BOUNDED_OUTPUT_SIDE_CARRIER_AND_ERASER_ATTRIBUTION"
    report["evaluation"]["eraser_cover"]["lift_vs_random"]["win_share"] = 0.4
    assert stage27j._status_from_gates(report) == "PASS_BOUNDED_OUTPUT_SIDE_COMPONENT_ATTRIBUTION"
    report["evaluation"]["carrier_cover"]["drop_vs_random"]["win_share"] = 0.56
    assert stage27j._status_from_gates(report) == "GREY_OUTPUT_SIDE_COMPONENT_ATTRIBUTION_PARTIAL"
    report["evaluation"]["carrier_cover"]["drop_vs_random"]["win_share"] = 0.4
    assert stage27j._status_from_gates(report) == "NULL_OUTPUT_SIDE_COMPONENT_ATTRIBUTION_NOT_ESTABLISHED"
    report["source_contracts"]["stage7_prefix"]["formal_gate_valid"] = False
    assert (
        stage27j._status_from_gates(report)
        == "STAGE27J_OUTPUT_SIDE_COMPONENT_ATTRIBUTION_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    )

