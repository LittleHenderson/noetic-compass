from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27d_within_head_slice_covers.py"


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


def test_make_slices_for_component_partitions_head_dim() -> None:
    stage27d = _load_module("stage27d_runner_slices")

    slices = stage27d._make_slices_for_component(stage27d.Component("head", 5, 3), head_dim=64, slices_per_head=8)

    assert [head_slice.name for head_slice in slices[:2]] == ["L5H3S0", "L5H3S1"]
    assert slices[0].start == 0
    assert slices[0].stop == 8
    assert slices[-1].start == 56
    assert slices[-1].stop == 64


def test_random_slice_covers_are_same_size_and_from_candidates() -> None:
    stage27d = _load_module("stage27d_runner_random")

    covers = stage27d._sample_random_slice_covers(["a", "b", "c", "d"], cover_size=2, n_random=5, seed=1)

    assert len(covers) == 5
    assert all(len(cover) == 2 for cover in covers)
    assert all(set(cover) <= {"a", "b", "c", "d"} for cover in covers)


def test_status_boundaries() -> None:
    stage27d = _load_module("stage27d_runner_status")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "stage27c_contract": {"formal_gate_valid": True},
        "split_contract": {"learn_eval_disjoint": True},
        "gates": {
            "min_random_win_share": 0.6,
            "max_sign_test_p": 0.05,
            "min_positive_margin_share": 0.55,
            "min_class_head_gain_fraction": 0.25,
        },
        "evaluation": {
            "margins": {
                "slice_cover": {"mean": 2.0, "positive_share": 0.7},
                "random_slice_mean": {"mean": 1.0},
            },
            "paired_controls": {
                "slice_vs_random_slice_mean": {"win_share": 0.7, "sign_test_p": 0.01},
            },
            "class_head_ceiling": {"mean_slice_gain_fraction_of_mean_class_head_gain": 0.5},
        },
    }

    assert stage27d._status_from_gates(report) == "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS"
    report["evaluation"]["class_head_ceiling"]["mean_slice_gain_fraction_of_mean_class_head_gain"] = 0.1
    assert stage27d._status_from_gates(report) == "GREY_WITHIN_HEAD_SLICE_COVERS_PARTIAL"
    report["evaluation"]["paired_controls"]["slice_vs_random_slice_mean"]["sign_test_p"] = 0.9
    report["evaluation"]["margins"]["slice_cover"]["mean"] = 0.5
    assert stage27d._status_from_gates(report) == "NULL_WITHIN_HEAD_SLICE_COVERS_NOT_ESTABLISHED"
    report["artifact_contract"]["formal_gate_valid"] = False
    assert stage27d._status_from_gates(report) == "STAGE27D_WITHIN_HEAD_SLICE_COVERS_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"


def test_evaluate_slice_covers_reports_mean_gain_fraction() -> None:
    stage27d = _load_module("stage27d_runner_eval")
    original_labels = stage27d._FOUNDATION_LABELS
    old_label_index = stage27d._LABEL_TO_INDEX
    old_encode = stage27d._encode_row
    old_cache = stage27d._forward_vec_and_cache_heads
    old_slice_patch = stage27d._forward_vec_with_slice_patches
    old_head_patch = stage27d._forward_vec_with_head_patches
    old_probe_margin = stage27d._probe_margin
    try:
        stage27d._FOUNDATION_LABELS = ("F1T", "F1A")
        stage27d._LABEL_TO_INDEX = {"F1T": 0, "F1A": 1}
        selected = [stage27d.Component("head", 0, 0), stage27d.Component("head", 0, 1)]
        candidate = {
            "F1T": [
                stage27d.HeadSlice(layer=0, head=1, slice_index=0, start=0, stop=4),
                stage27d.HeadSlice(layer=0, head=1, slice_index=1, start=4, stop=8),
            ]
        }
        rows = [
            {"sample_id": "r1", "foundation_label": "F1T", "contrast_partner_foundation": "F1A", "head_margin": 5.0},
            {"sample_id": "r2", "foundation_label": "F1T", "contrast_partner_foundation": "F1A", "head_margin": 3.0},
        ]

        def fake_encode(row, _tokenizer, _device):
            return row, 0

        def fake_cache(_encoded, _focus_idx, _model, _layers):
            return np.asarray([0.0]), {}

        def fake_slice_patch(_encoded, _focus_idx, _model, *, ablate_components, patch_slices, clean_cache):
            del ablate_components, clean_cache
            if not patch_slices:
                return np.asarray([1.0])
            names = [head_slice.name for head_slice in patch_slices]
            if names == ["L0H1S0"]:
                return np.asarray([2.5])
            return np.asarray([1.5])

        def fake_head_patch(encoded, _focus_idx, _model, *, ablate_components, patch_components, clean_cache):
            del ablate_components, patch_components, clean_cache
            return np.asarray([encoded["head_margin"]])

        stage27d._encode_row = fake_encode
        stage27d._forward_vec_and_cache_heads = fake_cache
        stage27d._forward_vec_with_slice_patches = fake_slice_patch
        stage27d._forward_vec_with_head_patches = fake_head_patch
        stage27d._probe_margin = lambda _fitted, vector, _target_idx, _partner_idx: float(vector[0])
        result = stage27d._evaluate_slice_covers(
            rows,
            np.asarray([0, 0]),
            {},
            None,
            None,
            None,
            selected,
            {"F1T": ["L0H1"]},
            candidate,
            {"F1T": ["L0H1S0"]},
            {"F1T": [["L0H1S1"]]},
        )
    finally:
        stage27d._FOUNDATION_LABELS = original_labels
        stage27d._LABEL_TO_INDEX = old_label_index
        stage27d._encode_row = old_encode
        stage27d._forward_vec_and_cache_heads = old_cache
        stage27d._forward_vec_with_slice_patches = old_slice_patch
        stage27d._forward_vec_with_head_patches = old_head_patch
        stage27d._probe_margin = old_probe_margin

    assert result["class_head_ceiling"]["mean_slice_gain"] == 1.5
    assert result["class_head_ceiling"]["mean_class_head_gain"] == 3.0
    assert result["class_head_ceiling"]["mean_slice_gain_fraction_of_mean_class_head_gain"] == 0.5
