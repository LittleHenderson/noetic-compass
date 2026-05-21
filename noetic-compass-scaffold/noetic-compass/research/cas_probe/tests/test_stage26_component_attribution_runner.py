from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage26_component_attribution.py"


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


def test_component_scope_matches_preregistration() -> None:
    stage26 = _load_module("stage26_runner_scope")

    components = stage26._all_components()
    heads = [component for component in components if component.kind == "head"]
    mlps = [component for component in components if component.kind == "mlp"]

    assert len(components) == 78
    assert len(heads) == 72
    assert len(mlps) == 6
    assert components[0].name == "L0H0"
    assert components[-1].name == "L5MLP"


def test_component_name_round_trips() -> None:
    stage26 = _load_module("stage26_runner_names")

    assert stage26._component_from_name("L3H7") == stage26.Component("head", 3, 7)
    assert stage26._component_from_name("L4MLP") == stage26.Component("mlp", 4, None)


def test_random_summary_uses_plus_one_empirical_p() -> None:
    stage26 = _load_module("stage26_runner_random")

    result = stage26._summarize_vs_random(0.5, [0.1, 0.2, 0.6])

    assert result["actual"] == 0.5
    assert result["n_random"] == 3
    assert result["empirical_p_random_ge_actual"] == 0.5


def test_top_set_control_ranks_selected_against_random_sets() -> None:
    stage26 = _load_module("stage26_runner_topset")
    scores = {f"c{i}": float(i) for i in range(10)}

    result = stage26._top_set_random_control(scores, ["c8", "c9"], 20, 123)

    assert result["actual"] == 8.5
    assert result["n_random"] == 20
    assert 0.0 < result["empirical_p_random_ge_actual"] <= 1.0


def test_class_drop_summary_orders_largest_drops_first() -> None:
    stage26 = _load_module("stage26_runner_class_drop")
    y = np.array([0, 0, 1, 1])
    baseline = np.array([0, 0, 1, 1])
    ablated = np.array([1, 1, 1, 0])

    result = stage26._class_drop_summary(y, baseline, ablated)

    assert result["top_class_drops"][0]["foundation"] == "F1T"
    assert result["top_class_drops"][0]["drop"] == 1.0
    assert result["n_positive_drop_classes"] == 2


def test_status_boundaries() -> None:
    stage26 = _load_module("stage26_runner_status")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "capture_contract": {"finite_components": True},
        "alignment_enrichment": {"random_control": {"empirical_p_random_ge_actual": 0.01}},
        "targeted_ablation_drop": {
            "targeted_drop": 0.1,
            "random_control": {"empirical_p_random_ge_actual": 0.01},
        },
        "sanity_controls": {"noop_acc_delta": 0.0, "noop_acc_delta_slack": 0.01},
        "class_specificity": {"max_class_drop": 0.2},
    }

    assert stage26._status_from_gates(report) == "PASS_BOUNDED_COMPONENT_ATTRIBUTION"
    report["artifact_contract"]["formal_gate_valid"] = False
    assert stage26._status_from_gates(report) == "STAGE26_COMPONENT_ATTRIBUTION_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"
