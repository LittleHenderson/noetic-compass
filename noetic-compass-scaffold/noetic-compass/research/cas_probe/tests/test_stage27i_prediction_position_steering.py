from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import torch


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27i_prediction_position_steering.py"


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
    stage27i = _load_module("stage27i_runner_positions")

    assert stage27i._prediction_positions(2, 3) == (1, 2, 3)


def test_score_continuation_localizes_hook_to_prediction_position() -> None:
    stage27i = _load_module("stage27i_runner_hook")

    class DummyTokenizer:
        def encode(self, text: str, add_special_tokens: bool = False):
            del add_special_tokens
            if text == "p":
                return [0, 0]
            return [1]

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

        def forward(self, input_ids: torch.Tensor, use_cache: bool = False, output_hidden_states: bool = False):
            del use_cache
            hidden = torch.ones((1, input_ids.shape[1], 2), dtype=torch.float32, device=input_ids.device)
            hidden[:, 0, 1] = 10.0
            hidden = self.gpt_neox.layers[0].mlp(hidden)
            logits = torch.zeros((1, input_ids.shape[1], 2), dtype=torch.float32, device=input_ids.device)
            logits[:, :, 1] = hidden[:, :, 1]
            if output_hidden_states:
                return type("Out", (), {"logits": logits, "hidden_states": [hidden, hidden]})()
            return type("Out", (), {"logits": logits})()

    base = stage27i._score_continuation_position_localized(
        DummyModel(), DummyTokenizer(), "p", "c", torch.device("cpu")
    )
    scaled = stage27i._score_continuation_position_localized(
        DummyModel(),
        DummyTokenizer(),
        "p",
        "c",
        torch.device("cpu"),
        neurons=[stage27i.MLPNeuron(0, 1)],
        scale=2.0,
    )

    assert scaled["prediction_positions"] == [1]
    assert scaled["mean_logprob"] > base["mean_logprob"]


def test_status_boundaries() -> None:
    stage27i = _load_module("stage27i_runner_status")
    report = {
        "source_contracts": {
            "stage7_artifact": {"formal_gate_valid": True},
            "stage7_prefix": {"formal_gate_valid": True},
            "stage27g": {"formal_gate_valid": True},
            "stage27h": {"formal_gate_valid": True},
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
                "position_localized_target_amplification_increment": {"mean": 1.0, "positive_share": 0.9},
                "random_position_localized_target_amplification_mean_increment": {"mean": 0.1},
                "position_localized_target_flip_reduction": {"mean": 2.0, "positive_share": 0.9},
                "random_position_localized_target_flip_mean_reduction": {"mean": 0.2},
            },
            "paired_controls": {
                "position_localized_target_amplification_vs_random_mean": {
                    "win_share": 0.7,
                    "sign_test_p": 0.01,
                },
                "position_localized_target_flip_vs_random_mean": {"win_share": 0.8, "sign_test_p": 0.001},
            },
        },
    }

    assert stage27i._status_from_gates(report) == "PASS_BOUNDED_PREDICTION_POSITION_NEURON_STEERING"
    report["evaluation"]["paired_controls"]["position_localized_target_flip_vs_random_mean"]["win_share"] = 0.4
    assert stage27i._status_from_gates(report) == "GREY_PREDICTION_POSITION_NEURON_STEERING_PARTIAL"
    report["evaluation"]["paired_controls"]["position_localized_target_amplification_vs_random_mean"]["win_share"] = 0.4
    report["evaluation"]["effects"]["position_localized_target_amplification_increment"]["mean"] = -1.0
    assert stage27i._status_from_gates(report) == "NULL_PREDICTION_POSITION_NEURON_STEERING_NOT_ESTABLISHED"
    report["source_contracts"]["stage7_artifact"]["formal_gate_valid"] = False
    assert (
        stage27i._status_from_gates(report)
        == "STAGE27I_PREDICTION_POSITION_STEERING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    )


def test_downstream_trace_summarizes_layer_delta(monkeypatch) -> None:
    stage27i = _load_module("stage27i_runner_trace")

    rows = [
        {
            "sample_id": "s1",
            "english": "A is the focused role.",
            "foundation_drive": 1,
            "foundation_register": "T",
            "foundation_label": "F1T",
        }
    ]
    fitted = {6: object()}
    monkeypatch.setattr(stage27i, "_partner_drive", lambda _row: 2)
    monkeypatch.setattr(stage27i, "_prediction_trace_vectors", lambda *args, **kwargs: {6: np.asarray([1.0, 0.0])} if kwargs.get("neurons") is None else {6: np.asarray([3.0, 0.0])})
    monkeypatch.setattr(stage27i, "_probe_margin", lambda _fit, vec, _target, _partner: float(vec[0]))

    trace = stage27i._downstream_survival_trace(
        rows,
        object(),
        object(),
        object(),
        {"F1T": ["L5N1"]},
        fitted,
        trace_layers=(6,),
        amplification_scale=2.0,
    )

    assert trace["layers"]["6"]["delta"]["mean"] == 2.0
