from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27f_targeted_mlp_neuron_covers.py"


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


def test_parse_coordinate_layer_and_neuron_name() -> None:
    stage27f = _load_module("stage27f_runner_parse")

    assert stage27f._parse_coordinate_layer("L5H3S12") == 5
    neuron = stage27f._neuron_from_name("L5N1482")
    assert neuron.layer == 5
    assert neuron.neuron == 1482
    assert neuron.name == "L5N1482"


def test_stage27e_contract_extracts_candidate_layers() -> None:
    stage27f = _load_module("stage27f_runner_contract")
    report = {
        "status": "PASS_BOUNDED_SINGLE_DIM_COORDINATE_COVERS",
        "artifact_contract": {"status": "LOCKED_ARTIFACT_MATCH"},
        "stage27c_contract": {"formal_gate_valid": True},
        "stage27d_contract": {"formal_gate_valid": True},
        "coordinate_resolution": {"single_coordinate": True},
        "per_class_slice_covers": {label: ["L5H3S1", "L1H6S2"] for label in stage27f._FOUNDATION_LABELS},
    }
    path = ROOT / ".tmp_stage27f_stage27e_contract.json"
    try:
        path.write_text(json.dumps(report), encoding="utf-8")
        contract = stage27f._load_stage27e_contract(path)
    finally:
        path.unlink(missing_ok=True)

    assert contract["formal_gate_valid"] is True
    assert contract["per_class_candidate_layers"]["F1T"] == [1, 5]


def test_random_neuron_covers_preserve_layer_counts() -> None:
    stage27f = _load_module("stage27f_runner_random")

    covers = stage27f._sample_random_neuron_covers(
        ["L5N1", "L5N2", "L1N3"],
        intermediate_dim=10,
        n_random=4,
        seed=1,
    )

    assert len(covers) == 4
    for cover in covers:
        layers = [stage27f._neuron_from_name(name).layer for name in cover]
        assert layers.count(5) == 2
        assert layers.count(1) == 1
        assert not {"L5N1", "L5N2", "L1N3"} & set(cover)


def test_effective_margin_direction_uses_scaler() -> None:
    stage27f = _load_module("stage27f_runner_margin")

    class DummyClf:
        coef_ = np.asarray([[2.0, 6.0], [1.0, 2.0]])

    class DummyScaler:
        scale_ = np.asarray([1.0, 2.0])

    direction = stage27f._effective_margin_direction({"clf": DummyClf(), "scaler": DummyScaler()}, 0, 1)

    assert direction.tolist() == [1.0, 2.0]


def test_status_boundaries() -> None:
    stage27f = _load_module("stage27f_runner_status")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "stage27c_contract": {"formal_gate_valid": True},
        "stage27e_contract": {"formal_gate_valid": True},
        "split_contract": {"learn_eval_disjoint": True},
        "gates": {
            "min_random_win_share": 0.6,
            "max_sign_test_p": 0.05,
            "min_positive_drop_share": 0.55,
            "max_patchback_mean_abs_error": 1e-4,
        },
        "evaluation": {
            "drops": {
                "targeted": {"mean": 1.0, "positive_share": 0.7},
                "random_mean": {"mean": 0.2},
            },
            "paired_controls": {
                "targeted_drop_vs_random_mean_drop": {"win_share": 0.7, "sign_test_p": 0.01},
            },
            "patchback_sanity": {"mean_abs_margin_error": 0.0},
        },
    }

    assert stage27f._status_from_gates(report) == "PASS_BOUNDED_TARGETED_MLP_NEURON_COVERS"
    report["evaluation"]["patchback_sanity"]["mean_abs_margin_error"] = 0.01
    assert stage27f._status_from_gates(report) == "GREY_TARGETED_MLP_NEURON_COVERS_PARTIAL"
    report["evaluation"]["drops"]["targeted"]["mean"] = -0.1
    report["evaluation"]["paired_controls"]["targeted_drop_vs_random_mean_drop"]["win_share"] = 0.4
    assert stage27f._status_from_gates(report) == "NULL_TARGETED_MLP_NEURON_COVERS_NOT_ESTABLISHED"
    report["artifact_contract"]["formal_gate_valid"] = False
    assert stage27f._status_from_gates(report) == "STAGE27F_TARGETED_MLP_NEURON_COVERS_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
