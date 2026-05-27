from __future__ import annotations

import json
from pathlib import Path

import pytest

from api.services.cas_harness_evidence_bridge import normalize_evidence_packet_for_audit
from api.services.cas_harness_verdict_runner import run_evidence_gated_verdict
from scripts.merge_s7_f28_balanced_bridge_evidence_packet import (
    METHOD_LABEL,
    MergeConfig,
    build_evidence_packet,
    render_markdown,
)


def test_merger_builds_packet_with_six_pass_ready_proof_chips(tmp_path: Path):
    config = _write_fixture_set(tmp_path)

    packet = build_evidence_packet(config)

    assert packet["schema_version"] == "cas_harness_evidence_packet_v1"
    assert packet["trace_id"] == "trace-fixture"
    assert packet["input"]["method_label"] == METHOD_LABEL
    assert packet["model"]["name"] == "EleutherAI/gpt-neox-20b"
    assert packet["readout"]["heldout_accuracy"] == 0.868622
    assert packet["readout"]["lacunarity"] == 0.006715
    assert packet["ablation"]["label_specific_cover_ablation"]["drop_from_clean"] == 0.124424
    assert packet["matched_controls"]["activation_controls"]["label_drop_exceeds_random_max"] is True
    assert packet["output"]["probe_readable"]["delta_vs_none_mean"] == 0.596413
    assert packet["verification"]["trace_diagnostics"]["numeric_trace_class"] == "Amplifying"

    chips = {chip["id"]: chip for chip in packet["verification"]["proof_chips"]}
    assert set(chips) == {
        "model_proof",
        "cas_readout",
        "causal_proof",
        "control_proof",
        "output_proof",
        "packet_proof",
    }
    assert chips["model_proof"]["status"] == "present"
    assert chips["cas_readout"]["status"] == "verified"
    assert chips["causal_proof"]["status"] == "verified"
    assert chips["control_proof"]["status"] == "verified"
    assert chips["output_proof"]["status"] == "verified"
    assert chips["packet_proof"]["status"] == "present"

    normalized = normalize_evidence_packet_for_audit(packet)
    normalized_chips = {chip.id: chip for chip in normalized.chips}
    assert normalized_chips["model_proof"].status == "present"
    assert normalized_chips["cas_readout"].status == "present"
    assert normalized_chips["causal_proof"].status == "verified"
    assert normalized_chips["control_proof"].status == "verified"
    assert normalized_chips["output_proof"].status == "present"
    assert normalized_chips["packet_proof"].status == "present"


def test_merger_keeps_verdict_to_human_review_not_accept(tmp_path: Path):
    config = _write_fixture_set(tmp_path)

    packet = build_evidence_packet(config)
    decision = packet["verification"]["explicit_verifier_decision"]

    assert decision["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert decision["confidence"] == 0.803571
    assert packet["verification"]["evidence_gate_confidence"]["formula"] == (
        "min(balanced_logistic_heldout_accuracy, "
        "probe_readable_positive_fraction, causal_control_pass, trace_gate_pass)"
    )

    result = run_evidence_gated_verdict(
        evidence_packet_trace_id=packet["trace_id"],
        proof_chips=packet["verification"]["proof_chips"],
        explicit_verifier_decision=decision,
    )
    assert result.status == "COMPLETE"
    assert result.verdict == "FLAG_FOR_HUMAN_REVIEW"
    assert result.confidence == 0.803571


def test_confidence_drops_to_zero_when_trace_gate_fails(tmp_path: Path):
    config = _write_fixture_set(tmp_path)
    trace = json.loads(config.trace_diagnostics_report.read_text(encoding="utf-8"))
    trace["status"] = "TRACE_DIAGNOSTICS_REVIEW"
    config.trace_diagnostics_report.write_text(json.dumps(trace), encoding="utf-8")

    packet = build_evidence_packet(config)

    assert packet["verification"]["evidence_gate_confidence"]["score"] == 0.0
    assert packet["verification"]["explicit_verifier_decision"]["verdict"] == "FLAG_FOR_HUMAN_REVIEW"


def test_merger_hashes_every_source_artifact(tmp_path: Path):
    config = _write_fixture_set(tmp_path)

    packet = build_evidence_packet(config)

    artifact_hashes = packet["hashes"]["artifact_sha256"]
    assert set(artifact_hashes) == {
        "ablation_report",
        "bridge_report",
        "eval_report",
        "scenario_path",
        "trace_diagnostics_report",
    }
    assert all(len(value) == 64 for value in artifact_hashes.values())
    assert len(packet["hashes"]["packet_content_sha256"]) == 64


def test_merger_refuses_missing_required_artifacts(tmp_path: Path):
    config = _write_fixture_set(tmp_path)
    config.bridge_report.unlink()

    with pytest.raises(FileNotFoundError, match="bridge_report"):
        build_evidence_packet(config)


def test_markdown_summary_names_method_and_verdict(tmp_path: Path):
    config = _write_fixture_set(tmp_path)
    packet = build_evidence_packet(config)

    rendered = render_markdown(packet)

    assert "S7-F28 Balanced Bridge Evidence Packet" in rendered
    assert "`S7-F28-BALANCED-BRIDGE`" in rendered
    assert "`FLAG_FOR_HUMAN_REVIEW`" in rendered
    assert "0.596413" in rendered


def _write_fixture_set(tmp_path: Path) -> MergeConfig:
    scenario_path = tmp_path / "scenarios.json"
    eval_report = tmp_path / "eval.json"
    ablation_report = tmp_path / "ablation.json"
    bridge_report = tmp_path / "bridge.json"
    trace_report = tmp_path / "trace.json"

    _write_json(
        scenario_path,
        {
            "scenarios": [
                {
                    "id": "row-001",
                    "expected_cas_axes": {"foundation": "F1|T"},
                    "metadata": {"split": "train"},
                },
                {
                    "id": "row-002",
                    "expected_cas_axes": {"foundation": "F2|A"},
                    "metadata": {"split": "test"},
                },
            ]
        },
    )
    _write_json(
        eval_report,
        {
            "axes": {
                "foundation": {
                    "best_layer": {"layer": 40, "test_acc": 0.510369},
                    "controls": {
                        "majority_class_test_acc": 0.035714,
                        "shuffled_label_hidden_centroid_mean_test_acc": 0.034044,
                        "text_hash_centroid": {"test_acc": 0.422811},
                    },
                }
            }
        },
    )
    _write_json(
        ablation_report,
        {
            "ablation_mode": "activation_level_train_mean_replacement",
            "important_limit": "captured-vector ablation, not live hook steering",
            "axes": {
                "foundation": {
                    "best_layer": 40,
                    "clean": {"acc": 0.510369, "macro_f1": 0.510863},
                    "label_specific_cover_ablation": {
                        "acc": 0.385945,
                        "drop_from_clean": 0.124424,
                    },
                    "label_random_same_size_controls": {
                        "max_drop_from_clean": 0.003457,
                        "mean_drop_from_clean": 0.000749,
                        "trials": 20,
                    },
                    "wrong_cover_control": {"acc": 0.509217, "drop_from_clean": 0.001152},
                    "result_summary": {
                        "label_drop_exceeds_random_max": True,
                        "label_drop_minus_random_mean": 0.123675,
                    },
                }
            },
        },
    )
    _write_json(
        bridge_report,
        {
            "schema_version": "cas_harness_open_weight_eta_epsilon_bridge.v1",
            "status": "PROBE_PREDICTED_ETA_EPSILON_BRIDGE_PASS",
            "model_id": "EleutherAI/gpt-neox-20b",
            "model_revision": None,
            "model_info": {
                "architectures": ["GPTNeoXForCausalLM"],
                "model_type": "gpt_neox",
                "parameter_count": 20554567680,
                "num_hidden_layers": 44,
                "hidden_size": 6144,
                "torch_dtype": "torch.float16",
                "device_map": "auto",
            },
            "n_cases": 112,
            "readout_mode": "logistic_linear_probe",
            "readout_layer": 40,
            "probe_prediction": {
                "all_test_foundation_accuracy": 0.868622,
                "selected_foundation_accuracy": 0.857143,
                "selected_drive_accuracy": 0.9375,
            },
            "bridge_gates": {
                "probe_readable": {
                    "checks": {
                        "delta_positive_sign_p": {"value": 3e-11},
                    },
                }
            },
            "conditions": {
                "probe_readable": {
                    "delta_positive_count": 90,
                    "delta_positive_sign_p": 3e-11,
                    "delta_vs_none": {"mean": 0.596413},
                },
                "gold_readable": {
                    "delta_positive_count": 93,
                    "delta_positive_sign_p": 0.0,
                    "delta_vs_none": {"mean": 0.660065},
                },
                "probe_raw": {"delta_vs_none": {"mean": 0.002524}},
                "gold_raw": {"delta_vs_none": {"mean": 0.002186}},
                "partner_readable": {"delta_vs_none": {"mean": -0.648503}},
            },
            "key_comparisons": {
                "probe_readable_minus_partner_readable_margin": 1.244917,
                "probe_raw_delta_vs_none": 0.002524,
                "gold_raw_delta_vs_none": 0.002186,
            },
            "important_limit": "Likelihood bridge, not final verdict.",
        },
    )
    _write_json(
        trace_report,
        {
            "schema_version": "cas_harness_open_weight_trace_diagnostics.v1",
            "status": "TRACE_DIAGNOSTICS_PASS",
            "probe_readout": {
                "kind": "balanced_logistic_linear_probe",
                "C": 0.1,
                "class_weight": "balanced",
                "standardized": True,
            },
            "layer_scan": {
                "best_layer": 40,
                "best_test_acc": 0.868622,
                "best_test_macro_f1": 0.869944,
            },
            "lacunarity_gate": {
                "score": 0.006715,
                "threshold": 0.05,
                "passed": True,
                "drive_lacunarity": 0.002752,
                "register_lacunarity": 0.001283,
            },
            "fractal_preflight": {
                "class": "Amplifying",
                "classifier_kind": "numeric_trace_proxy",
                "important_limit": "not discrete cas-engine orbit",
            },
        },
    )

    return MergeConfig(
        scenario_path=scenario_path,
        eval_report=eval_report,
        ablation_report=ablation_report,
        bridge_report=bridge_report,
        trace_diagnostics_report=trace_report,
        output=tmp_path / "packet.json",
        output_md=tmp_path / "packet.md",
        trace_id="trace-fixture",
    )


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")
