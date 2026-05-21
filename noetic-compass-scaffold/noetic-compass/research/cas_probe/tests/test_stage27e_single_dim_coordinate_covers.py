from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27e_single_dim_coordinate_covers.py"


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


def test_stage27d_contract_requires_pass_and_locked_artifact() -> None:
    stage27e = _load_module("stage27e_runner_contract")
    report = {
        "status": "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS",
        "artifact_contract": {"status": "LOCKED_ARTIFACT_MATCH"},
        "stage27c_contract": {"formal_gate_valid": True},
        "slices_per_head": 8,
        "slice_cover_size": 8,
    }
    path = ROOT / ".tmp_stage27e_contract_test.json"
    try:
        path.write_text(json.dumps(report), encoding="utf-8")
        contract = stage27e._load_stage27d_contract(path)
    finally:
        path.unlink(missing_ok=True)

    assert contract["formal_gate_valid"] is True
    assert contract["source_status"] == "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS"


def test_status_requires_single_coordinate_resolution() -> None:
    stage27e = _load_module("stage27e_runner_status")
    report = {
        "artifact_contract": {"formal_gate_valid": True},
        "stage27c_contract": {"formal_gate_valid": True},
        "stage27d_contract": {"formal_gate_valid": True},
        "stage27d_style_status": "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS",
        "slices_per_head": 64,
        "head_dim": 64,
    }

    assert stage27e._status_from_stage27d_style_report(report) == "PASS_BOUNDED_SINGLE_DIM_COORDINATE_COVERS"
    report["slices_per_head"] = 8
    assert (
        stage27e._status_from_stage27d_style_report(report)
        == "STAGE27E_SINGLE_DIM_COVERS_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    )


def test_build_report_relabels_stage27d_style_report(monkeypatch) -> None:
    stage27e = _load_module("stage27e_runner_build")
    stage27d_path = ROOT / ".tmp_stage27e_build_test.json"
    stage27d_path.write_text(
        json.dumps(
            {
                "status": "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS",
                "artifact_contract": {"status": "LOCKED_ARTIFACT_MATCH"},
                "stage27c_contract": {"formal_gate_valid": True},
                "slices_per_head": 8,
                "slice_cover_size": 8,
            }
        ),
        encoding="utf-8",
    )

    def fake_build(_args):
        return {
            "schema_version": "stage27d_within_head_slice_covers.v1",
            "status": "PASS_BOUNDED_WITHIN_HEAD_SLICE_COVERS",
            "artifact_contract": {"formal_gate_valid": True},
            "stage27c_contract": {"formal_gate_valid": True},
            "head_dim": 64,
            "slices_per_head": 64,
            "slice_cover_size": 8,
            "gates": {},
            "boundary": "old",
        }

    monkeypatch.setattr(stage27e, "_build_stage27d_style_report", fake_build)
    args = SimpleNamespace(
        stage27d_report=str(stage27d_path),
        min_random_win_share=0.6,
        max_sign_test_p=0.05,
        min_positive_margin_share=0.55,
        min_class_head_gain_fraction=0.1,
    )

    try:
        report = stage27e.build_report(args)
    finally:
        stage27d_path.unlink(missing_ok=True)

    assert report["schema_version"] == "stage27e_single_dim_coordinate_covers.v1"
    assert report["status"] == "PASS_BOUNDED_SINGLE_DIM_COORDINATE_COVERS"
    assert report["coordinate_resolution"]["single_coordinate"] is True
    assert report["coordinate_cover_size"] == 8
