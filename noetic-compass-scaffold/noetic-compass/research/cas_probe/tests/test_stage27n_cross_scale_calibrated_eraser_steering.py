from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "run_stage27n_cross_scale_calibrated_eraser_steering.py"


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


def test_candidate_components_use_model_head_count() -> None:
    stage27n = _load_module("stage27n_runner_components")

    components = stage27n._candidate_components((12,), num_heads=16, num_layers=16)

    assert len(components) == 17
    assert components[0].name == "L12H0"
    assert components[15].name == "L12H15"
    assert components[-1].name == "L12MLP"


def test_candidate_components_reject_out_of_range_layer() -> None:
    stage27n = _load_module("stage27n_runner_bad_layer")

    try:
        stage27n._candidate_components((16,), num_heads=16, num_layers=16)
    except ValueError as exc:
        assert "outside" in str(exc)
    else:
        raise AssertionError("expected bad layer to raise")


def test_load_stage8_cpl2_contract_checks_pythia1b_status() -> None:
    stage27n = _load_module("stage27n_runner_stage8_contract")
    path = ROOT / ".tmp_stage27n_stage8_cpl2_contract.json"
    try:
        path.write_text(
            json.dumps(
                {
                    "status": "PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES",
                    "model_name": "EleutherAI/pythia-1b",
                    "selected_layer_position": 8,
                    "n_cases": 112,
                    "key_comparisons": {
                        "probe_readable_delta_vs_none": 0.55,
                        "probe_readable_minus_partner_readable_margin": 1.24,
                    },
                }
            ),
            encoding="utf-8",
        )
        contract = stage27n._load_stage8_cpl2_contract(path)
    finally:
        path.unlink(missing_ok=True)

    assert contract["formal_gate_valid"] is True
    assert contract["source_status"] == "PASS_CLEAN_STAGE8_PYTHIA1B_CPL2_REPLICATES"


def test_loaded_model_contract_requires_expected_revision() -> None:
    stage27n = _load_module("stage27n_runner_model_contract")

    good = stage27n._loaded_model_contract(
        {
            "model_name": "EleutherAI/pythia-1b",
            "model_revision": "f73d7dcc545c8bd326d8559c8ef84ffe92fea6b2",
            "num_hidden_layers": 16,
            "num_attention_heads": 16,
            "hidden_size": 2048,
        }
    )
    bad = stage27n._loaded_model_contract(
        {
            "model_name": "EleutherAI/pythia-1b",
            "model_revision": "unknown",
            "num_hidden_layers": 16,
            "num_attention_heads": 16,
            "hidden_size": 2048,
        }
    )

    assert good["formal_gate_valid"] is True
    assert bad["formal_gate_valid"] is False


def test_status_boundaries() -> None:
    stage27n = _load_module("stage27n_runner_status")
    report = {
        "source_contracts": {
            "stage8_cpl2": {"formal_gate_valid": True},
            "stage8_manifest": {"formal_gate_valid": True},
            "stage27m": {"formal_gate_valid": True},
        },
        "loaded_model_contract": {"formal_gate_valid": True},
        "split_contract": {
            "learn_eval_disjoint": True,
            "eval_rows": 56,
            "eval_rows_per_drive": 8,
        },
        "gates": {
            "min_random_win_share": 0.6,
            "max_sign_test_p": 0.05,
            "min_positive_effect_share": 0.55,
        },
        "evaluation": {
            "global": {
                "increment": {"mean": 1.0, "positive_share": 0.9},
                "random_mean_increment": {"mean": 0.1},
                "vs_random": {"win_share": 0.7, "sign_test_p": 0.01},
            },
            "drive_calibrated": {
                "increment": {"mean": 1.0, "positive_share": 0.9},
                "random_mean_increment": {"mean": 0.1},
                "vs_random": {"win_share": 0.8, "sign_test_p": 0.001},
            },
        },
    }

    assert stage27n._status_from_gates(report) == "PASS_BOUNDED_CROSS_SCALE_GLOBAL_AND_DRIVE_CALIBRATED_ERASER_STEERING"
    report["evaluation"]["drive_calibrated"]["vs_random"]["win_share"] = 0.4
    assert stage27n._status_from_gates(report) == "PASS_BOUNDED_CROSS_SCALE_CALIBRATED_ERASER_STEERING"
    report["evaluation"]["global"]["vs_random"]["win_share"] = 0.56
    assert stage27n._status_from_gates(report) == "GREY_CROSS_SCALE_CALIBRATED_ERASER_STEERING_PARTIAL"
    report["evaluation"]["global"]["vs_random"]["win_share"] = 0.4
    report["evaluation"]["global"]["increment"]["mean"] = -1.0
    report["evaluation"]["drive_calibrated"]["increment"]["mean"] = -1.0
    assert stage27n._status_from_gates(report) == "NULL_CROSS_SCALE_CALIBRATED_ERASER_STEERING_NOT_ESTABLISHED"
    report["loaded_model_contract"]["formal_gate_valid"] = False
    assert (
        stage27n._status_from_gates(report)
        == "STAGE27N_CROSS_SCALE_CALIBRATED_ERASER_STEERING_DIAGNOSTIC_ONLY_MODEL_MISMATCH"
    )
