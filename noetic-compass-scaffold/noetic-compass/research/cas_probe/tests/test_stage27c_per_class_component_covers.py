from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27c_per_class_component_covers.py"


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


def test_balanced_indices_selects_requested_rows_per_class() -> None:
    stage27c = _load_module("stage27c_runner_balanced")
    y = np.asarray([0, 1, 0, 1, 0, 1], dtype=np.int64)
    original_labels = stage27c._FOUNDATION_LABELS
    try:
        stage27c._FOUNDATION_LABELS = ("A", "B")
        rows = stage27c._balanced_indices([0, 1, 2, 3, 4, 5], y, rows_per_class=2)
    finally:
        stage27c._FOUNDATION_LABELS = original_labels

    assert rows == [0, 2, 1, 3]


def test_paired_summary_uses_exact_sign_test() -> None:
    stage27c = _load_module("stage27c_runner_paired")

    summary = stage27c._paired_summary([2, 3, 4, 1], [1, 1, 2, 2])

    assert summary["wins"] == 3
    assert summary["win_share"] == 0.75
    assert summary["sign_test_p"] == 0.3125


def test_random_subcovers_are_same_size_and_from_selected() -> None:
    stage27c = _load_module("stage27c_runner_random")
    selected = ["A", "B", "C", "D"]

    covers = stage27c._sample_random_subcovers(selected, cover_size=2, n_random=5, seed=1)

    assert len(covers) == 5
    assert all(len(cover) == 2 for cover in covers)
    assert all(set(cover) <= set(selected) for cover in covers)


def test_learn_per_class_covers_selects_top_component_scores_without_model() -> None:
    stage27c = _load_module("stage27c_runner_learn_shape")
    original_labels = stage27c._FOUNDATION_LABELS
    try:
        stage27c._FOUNDATION_LABELS = ("F1T", "F2T")
        selected = [stage27c.Component("head", 0, 0), stage27c.Component("head", 0, 1)]
        # Exercise the final cover construction logic by monkeypatching the expensive
        # forward helpers to deterministic vectors.
        def fake_encode(_row, _tokenizer, _device):
            return object(), 0

        def fake_cache(_encoded, _focus_idx, _model, _layers):
            return np.asarray([0.0]), {}

        def fake_patch(_encoded, _focus_idx, _model, *, ablate_components, patch_components, clean_cache):
            if not patch_components:
                return np.asarray([0.0])
            return np.asarray([1.0 if patch_components[0].head == 1 else 0.5])

        class DummyScaler:
            def transform(self, X):
                return X

        class DummyClf:
            def decision_function(self, X):
                arr = np.asarray(X)
                return np.column_stack([arr[:, 0], np.zeros(arr.shape[0])])

        old_encode = stage27c._encode_row
        old_cache = stage27c._forward_vec_and_cache_heads
        old_patch = stage27c._forward_vec_with_head_patches
        old_partner = stage27c._partner_label
        old_label_index = stage27c._LABEL_TO_INDEX
        stage27c._encode_row = fake_encode
        stage27c._forward_vec_and_cache_heads = fake_cache
        stage27c._forward_vec_with_head_patches = fake_patch
        stage27c._partner_label = lambda _row: "F2T"
        stage27c._LABEL_TO_INDEX = {"F1T": 0, "F2T": 1}
        learned = stage27c._learn_per_class_covers(
            [{"sample_id": "x"}],
            np.asarray([0]),
            {"scaler": DummyScaler(), "clf": DummyClf()},
            None,
            None,
            None,
            selected,
            cover_size=1,
        )
    finally:
        stage27c._FOUNDATION_LABELS = original_labels
        stage27c._encode_row = old_encode
        stage27c._forward_vec_and_cache_heads = old_cache
        stage27c._forward_vec_with_head_patches = old_patch
        stage27c._partner_label = old_partner
        stage27c._LABEL_TO_INDEX = old_label_index

    assert learned["covers"]["F1T"] == ["L0H1"]


def test_status_boundaries() -> None:
    stage27c = _load_module("stage27c_runner_status")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "component_path_contract": {"formal_gate_valid": True},
        "split_contract": {"learn_eval_disjoint": True},
        "gates": {
            "min_control_win_share": 0.6,
            "max_sign_test_p": 0.05,
            "min_positive_margin_share": 0.55,
        },
        "evaluation": {
            "margins": {
                "class_cover": {"mean": 0.2, "positive_share": 0.7},
                "global_prefix": {"mean": 0.1},
            },
            "paired_controls": {
                "class_vs_global_prefix": {"win_share": 0.7, "sign_test_p": 0.01},
                "class_vs_random_subset_mean": {"win_share": 0.7, "sign_test_p": 0.01},
            },
        },
    }

    assert stage27c._status_from_gates(report) == "PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS"
    report["evaluation"]["paired_controls"]["class_vs_random_subset_mean"]["sign_test_p"] = 0.9
    assert stage27c._status_from_gates(report) == "GREY_PER_CLASS_COMPONENT_COVERS_PARTIAL"
    report["evaluation"]["margins"]["class_cover"]["mean"] = -0.1
    report["evaluation"]["paired_controls"]["class_vs_global_prefix"]["sign_test_p"] = 0.9
    assert stage27c._status_from_gates(report) == "NULL_PER_CLASS_COMPONENT_COVERS_NOT_ESTABLISHED"
    report["artifact_contract"]["formal_gate_valid"] = False
    assert stage27c._status_from_gates(report) == "STAGE27C_PER_CLASS_COVERS_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
