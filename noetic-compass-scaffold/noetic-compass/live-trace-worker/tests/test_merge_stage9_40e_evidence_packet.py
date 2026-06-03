from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "merge_stage9_40e_evidence_packet.py"
)
SPEC = importlib.util.spec_from_file_location("merge_stage9_40e_evidence_packet", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
merge_stage9_40e_evidence_packet = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(merge_stage9_40e_evidence_packet)


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _readout_fixture() -> dict:
    return {
        "schema_version": "cas_harness_40_element_probe_eval.v1",
        "status": "packet_ready_evaluation_completed",
        "created_at": "2026-05-27T00:00:00+00:00",
        "trace_id": "trace-stage9-40e",
        "run_id": "run-stage9-40e",
        "model_id": "EleutherAI/gpt-neox-20b",
        "model_family": "gpt_neox",
        "parameter_scale": "20B",
        "dataset": "D:/archive/gpt_neox_20b_stage9_original_40e_layers_0_43.npz",
        "metadata_path": "D:/archive/gpt_neox_20b_stage9_original_40e_layers_0_43.metadata.json",
        "best_layer": {"layer": 2, "test_acc": 0.95625, "test_macro_f1": 0.95},
        "controls": {
            "confirmed_text_baseline_report": {"test_acc": 0.4924107142857143},
            "text_hash_baseline": {"test_acc": 0.5},
            "shuffled_label_hidden_best_layer": {"mean_test_acc": 0.02619419642857143},
            "compact_gloss_v0": {"status": "blocked_text_only", "text_only_acc": 1.0},
        },
        "artifacts": [
            {
                "artifact_id": "activation_dataset_npz",
                "artifact_type": "40e_activation_dataset_npz",
                "content_sha256": "a" * 64,
                "byte_count": 123,
                "storage_uri": "D:/archive/dataset.npz",
            }
        ],
        "provenance": {
            "source_pr": 102,
            "method_label": "S9-40E-ORIGINAL-BASELINE-READOUT",
        },
        "hashes": {"weights_sha": "b" * 64},
    }


def test_readout_only_packet_is_review_flag_and_never_final_verdict(tmp_path):
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())

    packet = merge_stage9_40e_evidence_packet.build_packet(
        readout_report=readout,
        generated_at=datetime(2026, 5, 27, tzinfo=UTC),
    )

    assert packet["schema_version"] == "cas_harness_stage9_40e_evidence_packet.v1"
    assert packet["trace_id"] == "trace-stage9-40e"
    assert packet["run_id"] == "run-stage9-40e"
    assert packet["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert packet["verdict"] not in {"ACCEPT", "SUPPRESS"}
    assert packet["tier_statuses"] == {
        "model": "present",
        "readout": "present",
        "baseline": "present",
        "causal": "missing",
        "control": "missing",
        "output_bridge": "missing",
        "verifier": "missing",
    }
    assert packet["causal_proof"]["blocking_reason"] == (
        "subspace_ablation report was not supplied"
    )
    assert packet["control_proof"]["blocking_reason"] == (
        "cover_discovery report was not supplied"
    )
    assert packet["output_bridge_proof"]["blocking_reason"] == (
        "output_bridge report was not supplied"
    )


def test_packet_includes_exact_corrected_baseline_fields(tmp_path):
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())

    packet = merge_stage9_40e_evidence_packet.build_packet(readout_report=readout)
    baseline = packet["baseline_proof"]

    assert baseline["method_label"] == "S9-40E-ORIGINAL-BASELINE-READOUT"
    assert baseline["hidden_probe_test_acc"] == 0.95625
    assert baseline["hidden_probe_test_acc_pct"] == 95.625
    assert baseline["confirmed_text_test_acc"] == 0.4924107142857143
    assert baseline["confirmed_text_test_acc_pct"] == 49.241071
    assert baseline["text_hash_test_acc"] == 0.5
    assert baseline["text_hash_test_acc_pct"] == 50.0
    assert baseline["shuffled_label_hidden_mean_test_acc"] == 0.02619419642857143
    assert baseline["shuffled_label_hidden_mean_test_acc_pct"] == 2.619
    assert baseline["compact_gloss_v0"]["status"] == "blocked_text_only"
    assert baseline["compact_gloss_v0"]["text_only_acc_pct"] == 100.0
    assert set(baseline["source_field_checks"].values()) == {
        "matches_corrected_baseline"
    }


def test_packet_preserves_input_hashes_and_provenance(tmp_path):
    readout_payload = _readout_fixture()
    readout = _write_json(tmp_path / "readout.json", readout_payload)

    packet = merge_stage9_40e_evidence_packet.build_packet(readout_report=readout)
    source_report = packet["readout_proof"]["source_report"]

    assert source_report["content_sha256"] == hashlib.sha256(readout.read_bytes()).hexdigest()
    assert packet["readout_proof"]["source_fields"]["artifacts"] == readout_payload["artifacts"]
    assert packet["readout_proof"]["source_fields"]["hashes"] == readout_payload["hashes"]
    assert packet["readout_proof"]["source_fields"]["provenance"] == readout_payload["provenance"]
    assert packet["model_proof"]["model_weight_hash"] == "b" * 64
    assert packet["provenance"]["input_count"] == 1


def test_optional_reports_upgrade_tier_statuses_without_final_verdict(tmp_path):
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())
    ablation = _write_json(
        tmp_path / "ablation.json",
        {
            "schema_version": "stage9_40e_ablation.v0",
            "status": "completed",
            "method_label": "subspace-ablation-fixture",
            "run_id": "ablation-run",
            "primary_result": {
                "layer": 2,
                "original_accuracy": 0.95625,
                "ablated_accuracy": 0.6689732142857143,
                "true_disruption": 0.2872767857142857,
                "chance_baseline_accuracy": 0.025,
                "random_same_rank_mean_disruption": 0.0006808035714286175,
                "random_same_rank_max_disruption": 0.002678571428571419,
                "guard_status": "passed",
            },
            "artifacts": [{"artifact_id": "ablation", "content_sha256": "c" * 64}],
            "provenance": {"worker": "fixture"},
        },
    )
    cover = _write_json(
        tmp_path / "cover.json",
        {
            "schema_version": "stage9_40e_cover.v0",
            "status": "candidate_cover_discovery_completed",
            "method_label": "cover-discovery-fixture",
            "run_id": "cover-run",
            "selected_layer": 2,
            "top_k": 8,
            "cover_map": {f"^{i}|P": {"true_cover": [f"L2N{i}"]} for i in range(40)},
            "true_cover_per_class": {f"^{i}|P": [f"L2N{i}"] for i in range(40)},
            "caveat": "candidate covers need matched ablation validation",
            "hashes": {"cover_sha": "d" * 64},
        },
    )
    bridge = _write_json(
        tmp_path / "bridge.json",
        {
            "schema_version": "stage9_40e_bridge.v0",
            "status": "PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS",
            "method_label": "bridge-fixture",
            "run_id": "bridge-run",
            "n_cases": 80,
            "per_element": 2,
            "readout_layer": 2,
            "readout_mode": "logistic_linear_probe",
            "probe_prediction": {
                "selected_element_accuracy": 0.975,
                "selected_operator_accuracy": 0.975,
                "selected_domain_accuracy": 1.0,
                "all_test_element_accuracy": 0.952679,
            },
            "key_comparisons": {
                "probe_readable_delta_vs_none": 1.41205,
                "probe_readable_minus_partner_readable_margin": 2.881239,
                "gold_readable_delta_vs_none": 1.497513,
                "probe_raw_delta_vs_none": 0.013817,
            },
            "bridge_gates": {
                "probe_readable": {"passed": True},
                "gold_readable": {"passed": True},
            },
            "provenance": {"bridge": "fixture"},
        },
    )

    packet = merge_stage9_40e_evidence_packet.build_packet(
        readout_report=readout,
        ablation_report=ablation,
        cover_report=cover,
        bridge_report=bridge,
    )

    assert packet["tier_statuses"]["causal"] == "present"
    assert packet["tier_statuses"]["control"] == "present"
    assert packet["tier_statuses"]["output_bridge"] == "present"
    assert packet["tier_statuses"]["verifier"] == "missing"
    # Candidate-only cover discovery records the control tier as evidence but is
    # NOT verified, so the strict-verified proof-chip gate stays blocked.
    assert packet["verification"]["proof_chip_gate"] == "blocked"
    control_chip = next(
        chip
        for chip in packet["verification"]["proof_chips"]
        if chip["id"] == "control_proof"
    )
    assert control_chip["status"] == "present"
    assert packet["verification"]["explicit_verifier_decision"] is None
    assert packet["causal_proof"]["source_fields"]["provenance"] == {"worker": "fixture"}
    assert packet["control_proof"]["source_fields"]["hashes"] == {"cover_sha": "d" * 64}
    causal_primary = packet["causal_proof"]["summary"]["primary_result"]
    assert causal_primary["original_accuracy_pct"] == 95.625
    assert causal_primary["ablated_accuracy_pct"] == 66.897321
    assert causal_primary["true_disruption_pp"] == 28.727679
    assert causal_primary["random_same_rank_max_disruption_pp"] == 0.267857
    assert causal_primary["guard_status"] == "passed"
    assert packet["control_proof"]["summary"]["class_count"] == 40
    assert packet["control_proof"]["summary"]["selected_layer"] == 2
    assert packet["control_proof"]["summary"]["top_k"] == 8
    assert packet["output_bridge_proof"]["summary"]["run_id"] == "bridge-run"
    assert packet["output_bridge_proof"]["summary"]["n_cases"] == 80
    assert packet["output_bridge_proof"]["summary"]["probe_readable_gate_passed"] is True
    assert packet["output_bridge_proof"]["summary"]["key_comparisons"][
        "probe_readable_delta_vs_none"
    ] == 1.41205
    assert packet["output_bridge_proof"]["summary"]["probe_prediction"][
        "selected_element_accuracy"
    ] == 0.975
    assert packet["provenance"]["input_count"] == 4
    assert packet["verdict"] == "FLAG_FOR_HUMAN_REVIEW"


def test_valid_verifier_report_can_emit_accept_when_proof_chips_pass(tmp_path):
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())
    ablation = _write_json(
        tmp_path / "ablation.json",
        {
            "status": "completed",
            "primary_result": {
                "layer": 2,
                "original_accuracy": 0.95625,
                "ablated_accuracy": 0.6689732142857143,
                "true_disruption": 0.2872767857142857,
                "chance_baseline_accuracy": 0.025,
                "random_same_rank_mean_disruption": 0.0006808035714286175,
                "random_same_rank_max_disruption": 0.002678571428571419,
                "guard_status": "passed",
            },
        },
    )
    cover = _write_json(
        tmp_path / "cover.json",
        {
            # A "verified" control chip requires the cover report to declare that
            # matched-ablation validation actually ran and passed -- not merely
            # that 40 candidate cover classes exist.
            "status": "matched_ablation_validated",
            "selected_layer": 2,
            "top_k": 8,
            "cover_map": {f"^{i}|P": {"true_cover": [f"L2N{i}"]} for i in range(40)},
        },
    )
    bridge = _write_json(
        tmp_path / "bridge.json",
        {
            "status": "PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS",
            "n_cases": 80,
            "probe_prediction": {"selected_element_accuracy": 0.975},
            "key_comparisons": {"probe_readable_delta_vs_none": 1.41205},
            "bridge_gates": {"probe_readable": {"passed": True}},
        },
    )
    verifier = _write_json(
        tmp_path / "verifier.json",
        {
            "schema_version": "cas_harness_stage9_40e_verifier_decision.v1",
            "verdict": "ACCEPT",
            "confidence": 0.91,
            "source": "stage19_stage20_verifier_fixture",
            "reason": "All fixture gates pass.",
        },
    )

    packet = merge_stage9_40e_evidence_packet.build_packet(
        readout_report=readout,
        ablation_report=ablation,
        cover_report=cover,
        bridge_report=bridge,
        verifier_report=verifier,
    )

    assert packet["tier_statuses"]["verifier"] == "present"
    assert packet["verification"]["proof_chip_gate"] == "passed"
    assert packet["verification"]["explicit_verifier_decision"]["verdict"] == "ACCEPT"
    assert packet["verification"]["explicit_verifier_decision"]["confidence"] == 0.91
    assert packet["verdict"] == "ACCEPT"
    chips = {chip["id"]: chip["status"] for chip in packet["verification"]["proof_chips"]}
    assert chips["cas_readout"] == "verified"
    assert chips["causal_proof"] == "verified"
    assert chips["control_proof"] == "verified"
    assert chips["output_proof"] == "verified"


def test_candidate_only_cover_blocks_accept_and_keeps_control_chip_present(tmp_path):
    """A candidate-only cover discovery is recorded evidence, not a verified
    control. Even with an attached verifier ACCEPT, the packet must stay
    human-review because control_proof is "present", not "verified". This pins
    the honest behavior for the Pythia-160M Stage 9 40E packet, whose cover
    report status is ``candidate_cover_discovery_completed``.
    """
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())
    ablation = _write_json(
        tmp_path / "ablation.json",
        {
            "status": "completed",
            "primary_result": {
                "true_disruption": 0.2872767857142857,
                "random_same_rank_max_disruption": 0.002678571428571419,
                "guard_status": "passed",
            },
        },
    )
    cover = _write_json(
        tmp_path / "cover.json",
        {
            "status": "candidate_cover_discovery_completed",
            "selected_layer": 2,
            "top_k": 8,
            "cover_map": {f"^{i}|P": {"true_cover": [f"L2N{i}"]} for i in range(40)},
            "caveat": "candidate covers need matched ablation validation",
        },
    )
    bridge = _write_json(
        tmp_path / "bridge.json",
        {
            "status": "PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS",
            "n_cases": 80,
            "probe_prediction": {"selected_element_accuracy": 0.975},
            "key_comparisons": {"probe_readable_delta_vs_none": 1.41205},
            "bridge_gates": {"probe_readable": {"passed": True}},
        },
    )
    verifier = _write_json(
        tmp_path / "verifier.json",
        {
            "verdict": "ACCEPT",
            "confidence": 0.95,
            "reason": "Candidate-only control must not produce ACCEPT.",
        },
    )

    packet = merge_stage9_40e_evidence_packet.build_packet(
        readout_report=readout,
        ablation_report=ablation,
        cover_report=cover,
        bridge_report=bridge,
        verifier_report=verifier,
    )

    chips = {chip["id"]: chip["status"] for chip in packet["verification"]["proof_chips"]}
    assert chips["control_proof"] == "present"
    assert chips["cas_readout"] == "verified"
    assert chips["causal_proof"] == "verified"
    assert chips["output_proof"] == "verified"
    assert packet["verification"]["proof_chip_gate"] == "blocked"
    assert packet["verdict"] == "FLAG_FOR_HUMAN_REVIEW"


def test_explicit_accept_is_blocked_when_required_proof_chip_fails(tmp_path):
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())
    verifier = _write_json(
        tmp_path / "verifier.json",
        {
            "verdict": "ACCEPT",
            "confidence": 0.91,
            "reason": "This must not override missing proof.",
        },
    )

    packet = merge_stage9_40e_evidence_packet.build_packet(
        readout_report=readout,
        verifier_report=verifier,
    )

    assert packet["tier_statuses"]["verifier"] == "present"
    assert packet["verification"]["proof_chip_gate"] == "blocked"
    assert packet["verification"]["explicit_verifier_decision"]["verdict"] == "ACCEPT"
    assert packet["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert "required proof tiers are missing" in packet["verdict_rationale"]


def test_invalid_verifier_report_fails_closed(tmp_path):
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())
    verifier = _write_json(
        tmp_path / "verifier.json",
        {"verdict": "ACCEPT", "confidence": "0.91"},
    )

    packet = merge_stage9_40e_evidence_packet.build_packet(
        readout_report=readout,
        verifier_report=verifier,
    )

    assert packet["tier_statuses"]["verifier"] == "failed"
    assert packet["verification"]["explicit_verifier_decision"] is None
    assert packet["verdict"] == "FLAG_FOR_HUMAN_REVIEW"


def test_valid_verifier_report_can_emit_suppress_when_proof_chips_pass(tmp_path):
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())
    ablation = _write_json(
        tmp_path / "ablation.json",
        {
            "primary_result": {
                "true_disruption": 0.2,
                "random_same_rank_max_disruption": 0.01,
                "guard_status": "passed",
            },
        },
    )
    cover = _write_json(
        tmp_path / "cover.json",
        {
            "status": "matched_ablation_validated",
            "cover_map": {f"^{i}|P": {"true_cover": [f"L2N{i}"]} for i in range(40)},
        },
    )
    bridge = _write_json(
        tmp_path / "bridge.json",
        {
            "bridge_gates": {"probe_readable": {"passed": True}},
            "key_comparisons": {"probe_readable_delta_vs_none": 1.0},
        },
    )
    verifier = _write_json(
        tmp_path / "verifier.json",
        {
            "explicit_verifier_decision": {
                "verdict": "SUPPRESS",
                "confidence": 0.87,
                "source": "stage20_generation_readiness",
                "reason": "Verifier found a blocking condition.",
            }
        },
    )

    packet = merge_stage9_40e_evidence_packet.build_packet(
        readout_report=readout,
        ablation_report=ablation,
        cover_report=cover,
        bridge_report=bridge,
        verifier_report=verifier,
    )

    assert packet["verdict"] == "SUPPRESS"
    assert packet["verification"]["explicit_verifier_decision"]["source"] == (
        "stage20_generation_readiness"
    )


def test_writes_json_and_markdown_packet(tmp_path):
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())
    output_json = tmp_path / "packet.json"
    output_md = tmp_path / "packet.md"
    packet = merge_stage9_40e_evidence_packet.build_packet(readout_report=readout)

    merge_stage9_40e_evidence_packet.write_packet(packet, output_json, output_md)

    written = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert written["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert "Verdict: `FLAG_FOR_HUMAN_REVIEW`" in markdown
    assert "| Causal proof | missing |" in markdown
    assert "95.625%" in markdown
    assert "49.241071%" in markdown


def test_markdown_surfaces_causal_and_cover_numbers(tmp_path):
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())
    ablation = _write_json(
        tmp_path / "ablation.json",
        {
            "schema_version": "stage9_40e_ablation.v0",
            "status": "completed",
            "method_label": "subspace-ablation-fixture",
            "primary_result": {
                "layer": 2,
                "original_accuracy": 0.95625,
                "ablated_accuracy": 0.6689732142857143,
                "true_disruption": 0.2872767857142857,
                "chance_baseline_accuracy": 0.025,
                "random_same_rank_mean_disruption": 0.0006808035714286175,
                "random_same_rank_max_disruption": 0.002678571428571419,
                "guard_status": "passed",
            },
        },
    )
    cover = _write_json(
        tmp_path / "cover.json",
        {
            "schema_version": "stage9_40e_cover.v0",
            "status": "candidate_cover_discovery_completed",
            "method_label": "cover-discovery-fixture",
            "selected_layer": 2,
            "top_k": 8,
            "cover_map": {"^0|P": {"true_cover": ["L2N1"]}},
            "caveat": "candidate cover discovery",
        },
    )

    packet = merge_stage9_40e_evidence_packet.build_packet(
        readout_report=readout,
        ablation_report=ablation,
        cover_report=cover,
    )
    markdown = merge_stage9_40e_evidence_packet.render_markdown(packet)

    assert "## Causal Proof" in markdown
    assert "| After learned-subspace ablation | 66.8973% |" in markdown
    assert "| True disruption | 28.7277 pp |" in markdown
    assert "| Random same-rank max disruption | 0.267857 pp |" in markdown
    assert "| Guard status | passed |" in markdown
    assert "## Control / Cover Proof" in markdown
    assert "| Candidate classes | 1 |" in markdown
    assert "| Top-k neurons per class | 8 |" in markdown


def test_markdown_surfaces_output_bridge_numbers(tmp_path):
    readout = _write_json(tmp_path / "readout.json", _readout_fixture())
    bridge = _write_json(
        tmp_path / "bridge.json",
        {
            "schema_version": "stage9_40e_bridge.v0",
            "status": "PROBE_PREDICTED_40E_ETA_EPSILON_BRIDGE_PASS",
            "method_label": "bridge-fixture",
            "n_cases": 80,
            "probe_prediction": {"selected_element_accuracy": 0.975},
            "key_comparisons": {
                "probe_readable_delta_vs_none": 1.41205,
                "probe_readable_minus_partner_readable_margin": 2.881239,
                "gold_readable_delta_vs_none": 1.497513,
                "probe_raw_delta_vs_none": 0.013817,
            },
            "bridge_gates": {"probe_readable": {"passed": True}},
        },
    )

    packet = merge_stage9_40e_evidence_packet.build_packet(
        readout_report=readout,
        bridge_report=bridge,
    )
    markdown = merge_stage9_40e_evidence_packet.render_markdown(packet)

    assert "## Output Bridge Proof" in markdown
    assert "| Cases | 80 |" in markdown
    assert "| Selected element accuracy | 0.975 |" in markdown
    assert "| Probe-readable delta vs none | 1.41205 |" in markdown
    assert "| Probe-readable minus partner | 2.88124 |" in markdown
    assert "| Probe-raw delta vs none | 0.013817 |" in markdown
    assert "| Probe-readable gate | passed |" in markdown
