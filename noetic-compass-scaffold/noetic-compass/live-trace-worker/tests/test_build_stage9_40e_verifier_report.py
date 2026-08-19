from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "build_stage9_40e_verifier_report.py"
)
SPEC = importlib.util.spec_from_file_location("build_stage9_40e_verifier_report", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
build_stage9_40e_verifier_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_stage9_40e_verifier_report)


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _packet_fixture() -> dict:
    return {
        "schema_version": "cas_harness_stage9_40e_evidence_packet.v1",
        "trace_id": "trace-stage9-40e",
        "run_id": "run-stage9-40e",
        "baseline_proof": {
            "hidden_probe_test_acc": 0.95625,
            "confirmed_text_test_acc": 0.4924107142857143,
            "shuffled_label_hidden_mean_test_acc": 0.02619419642857143,
        },
        "causal_proof": {
            "status": "present",
            "summary": {
                "primary_result": {
                    "guard_status": "passed",
                    "true_disruption": 0.2872767857142857,
                    "random_same_rank_max_disruption": 0.002678571428571419,
                }
            },
        },
        "control_proof": {
            "status": "present",
            "summary": {
                "class_count": 40,
                "matched_controls": {
                    "random_same_size_classes": 40,
                    "wrong_class_reference_classes": 40,
                },
            },
        },
        "matched_taxonomy_proof": {
            "status": "matched_taxonomy_validated",
            "definition_sha256": build_stage9_40e_verifier_report.LOCKED_TKS_DEFINITION_SHA256,
            "summary": {
                "condition3_passed": True,
                "control_b_passed": True,
                "control_c_passed": True,
                "reason": "matched taxonomy controls passed",
            },
        },
        "output_bridge_proof": {
            "status": "present",
            "summary": {
                "n_cases": 80,
                "probe_readable_gate_passed": True,
                "probe_prediction": {"selected_element_accuracy": 0.975},
                "key_comparisons": {
                    "probe_readable_delta_vs_none": 1.41205,
                    "probe_readable_minus_partner_readable_margin": 2.881239,
                    "probe_raw_delta_vs_none": 0.013817,
                },
            },
        },
        "verification": {
            "proof_chip_gate": "passed",
            "proof_chips": [
                {"id": "model_proof", "status": "present"},
                {"id": "cas_readout", "status": "verified"},
                {"id": "causal_proof", "status": "verified"},
                {"id": "control_proof", "status": "verified"},
                {"id": "output_proof", "status": "verified"},
                {"id": "packet_proof", "status": "present"},
            ],
        },
    }


def test_balanced_packet_with_all_gates_passes_to_accept(tmp_path: Path):
    packet = _write_json(tmp_path / "packet.json", _packet_fixture())

    report = build_stage9_40e_verifier_report.build_report(
        packet_path=packet,
        mode="BALANCED",
        generated_at=datetime(2026, 5, 28, tzinfo=UTC),
    )

    decision = report["explicit_verifier_decision"]
    assert report["status"] == "STAGE9_40E_VERIFIER_ACCEPT"
    assert decision["verdict"] == "ACCEPT"
    assert decision["confidence"] == 0.95625
    assert decision["decision_scope"] == "stage9_40e_validation_packet"
    assert report["generation_readiness"]["generation_readiness"] == "allow"
    assert report["verification_stack"]["proof_chip_gate"] == "passed"
    assert report["verification_stack"]["gates"]["uniqueness"]["passed"] is True
    assert report["verification_stack"]["gates"]["uniqueness"]["tks_definition_locked"] is True


def test_triage_mode_flags_even_when_all_gates_pass(tmp_path: Path):
    packet = _write_json(tmp_path / "packet.json", _packet_fixture())

    report = build_stage9_40e_verifier_report.build_report(
        packet_path=packet,
        mode="MAX_COVERAGE_TRIAGE",
    )

    decision = report["explicit_verifier_decision"]
    assert decision["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert decision["confidence"] == 0.95625
    assert report["generation_readiness"]["generation_readiness"] == "caveat"
    assert report["generation_readiness"]["reasons"] == [
        "max_coverage_triage_does_not_emit_final_accept"
    ]


def test_missing_uniqueness_proof_flags_not_accept(tmp_path: Path):
    payload = _packet_fixture()
    del payload["matched_taxonomy_proof"]
    packet = _write_json(tmp_path / "packet.json", payload)

    report = build_stage9_40e_verifier_report.build_report(packet_path=packet)

    decision = report["explicit_verifier_decision"]
    assert decision["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert decision["confidence"] == 0.0
    assert report["verification_stack"]["gates"]["uniqueness"]["passed"] is None
    assert report["generation_readiness"]["reasons"] == ["uniqueness_gate_unavailable"]


def test_unbound_comparator_proof_does_not_close_uniqueness_gate(tmp_path: Path):
    payload = _packet_fixture()
    del payload["matched_taxonomy_proof"]["definition_sha256"]
    packet = _write_json(tmp_path / "packet.json", payload)

    report = build_stage9_40e_verifier_report.build_report(packet_path=packet)

    decision = report["explicit_verifier_decision"]
    uniqueness = report["verification_stack"]["gates"]["uniqueness"]
    assert decision["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert uniqueness["passed"] is None
    assert uniqueness["tks_definition_locked"] is False
    assert uniqueness["definition_sha256"] is None
    assert report["generation_readiness"]["reasons"] == ["uniqueness_gate_unavailable"]


def test_failed_uniqueness_proof_suppresses(tmp_path: Path):
    payload = _packet_fixture()
    payload["matched_taxonomy_proof"] = {
        "status": "matched_taxonomy_failed",
        "summary": {
            "condition3_passed": False,
            "control_b_passed": False,
            "control_c_passed": True,
            "reason": "wrong-class controls carried the same lift",
        },
    }
    packet = _write_json(tmp_path / "packet.json", payload)

    report = build_stage9_40e_verifier_report.build_report(packet_path=packet)

    decision = report["explicit_verifier_decision"]
    assert decision["verdict"] == "SUPPRESS"
    assert decision["confidence"] == 0.9
    assert report["verification_stack"]["gates"]["uniqueness"]["passed"] is False
    assert report["generation_readiness"]["reasons"] == ["uniqueness_gate_failed"]


def test_missing_core_verified_chip_flags_not_accept(tmp_path: Path):
    payload = _packet_fixture()
    payload["verification"]["proof_chips"][3]["status"] = "present"
    packet = _write_json(tmp_path / "packet.json", payload)

    report = build_stage9_40e_verifier_report.build_report(packet_path=packet)

    decision = report["explicit_verifier_decision"]
    assert decision["verdict"] == "FLAG_FOR_HUMAN_REVIEW"
    assert decision["confidence"] == 0.0
    assert report["verification_stack"]["proof_chip_gate"] == "blocked"


def test_failed_causal_gate_suppresses(tmp_path: Path):
    payload = _packet_fixture()
    payload["causal_proof"]["summary"]["primary_result"]["guard_status"] = "failed"
    packet = _write_json(tmp_path / "packet.json", payload)

    report = build_stage9_40e_verifier_report.build_report(packet_path=packet)

    decision = report["explicit_verifier_decision"]
    assert decision["verdict"] == "SUPPRESS"
    assert decision["confidence"] == 0.9
    assert report["generation_readiness"]["generation_readiness"] == "suppress"
    assert "causal_gate_failed" in report["generation_readiness"]["reasons"]


def test_writes_json_and_markdown_report(tmp_path: Path):
    packet = _write_json(tmp_path / "packet.json", _packet_fixture())
    out_json = tmp_path / "verifier.json"
    out_md = tmp_path / "verifier.md"
    report = build_stage9_40e_verifier_report.build_report(packet_path=packet)

    build_stage9_40e_verifier_report.write_report(report, out_json, out_md)

    written = json.loads(out_json.read_text(encoding="utf-8"))
    markdown = out_md.read_text(encoding="utf-8")
    assert written["explicit_verifier_decision"]["verdict"] == "ACCEPT"
    assert "Stage 9 40E Verifier Report" in markdown
    assert "Verdict: `ACCEPT`" in markdown
