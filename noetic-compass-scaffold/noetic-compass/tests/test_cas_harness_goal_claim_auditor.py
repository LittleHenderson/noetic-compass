from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from api.services.cas_harness_goal_claim_auditor import (
    BEHAVIOR_V5_CAUSAL_REPORT_SCHEMA_VERSION,
    BEHAVIOR_V5_CAUSAL_REQUIRED_GATES,
    BEHAVIOR_V5_PRESPEECH_REPORT_SCHEMA_VERSION,
    BEHAVIOR_V5_PRESPEECH_REQUIRED_GATES,
    DEFAULT_HALLUCINATION_SURFACE_SCREEN,
    DEFAULT_HIDDEN_INJECTION_SURFACE_SCREEN,
    DEFAULT_W0_DATA_READINESS_MANIFEST,
    DEFAULT_W0_FULL_CONTROL_REPORT,
    HALLUCINATION_PRESPEECH_REPORT_SCHEMA_VERSION,
    HALLUCINATION_PRESPEECH_REQUIRED_GATES,
    HIDDEN_INJECTION_REQUIRED_GATES,
    HIDDEN_INJECTION_W0_REPORT_SCHEMA_VERSION,
    W0_REPORT_SCHEMA_VERSION,
    W0_REQUIRED_GATES,
    audit_active_goal_claims,
)


ROOT = Path(__file__).resolve().parents[1]


def test_char_text_margin_is_a_required_hidden_injection_gate():
    # 2026-06-18 re-audit: a character-level surface control must be beaten before
    # any hidden-state report can be licensed. This gate is permanent.
    assert "char_text_margin_pass" in HIDDEN_INJECTION_REQUIRED_GATES


def test_char_text_margin_is_a_required_v6_prompt_risk_gate():
    # Prompt-level chain-break W0 reports must beat character n-gram surface text
    # too. The hidden/encoded withdrawal showed that word text alone is not enough.
    assert "risk_char_text_margin_pass" in W0_REQUIRED_GATES


def test_active_goal_auditor_reflects_withdrawn_w0_license_boundary():
    # 2026-06-18: the scoped hidden-injection W0 license was WITHDRAWN on re-audit
    # because a character-level text control (~0.93) beats the hidden readout
    # (0.897). The committed report does not satisfy the char_text_margin_pass
    # gate, so internal_w0 must be OPEN / NOT LICENSED and all six claims unlicensed.
    audit = audit_active_goal_claims(ROOT)
    rows = {row["claim_id"]: row for row in audit["claims"]}
    w0 = rows["internal_w0_prompt_injection_detection"]

    assert audit["schema_version"] == "cas_harness_active_goal_claim_audit.v0"
    assert audit["goal_complete"] is False
    assert audit["summary"]["claims_total"] == 6
    assert audit["summary"]["claims_licensed"] == 0
    assert set(audit["summary"]["unlicensed_claim_ids"]) == set(rows)

    assert w0["claim_status"] == "OPEN"
    assert w0["license_status"] == "NOT LICENSED"

    # No hidden-injection report is license-eligible under the 15-gate battery.
    best_hidden = w0["observed_metrics"].get("best_hidden_injection_w0_candidate")
    if best_hidden is not None:
        assert best_hidden.get("license_eligible") is not True

    assert {row["license_status"] for row in rows.values()} == {"NOT LICENSED"}
    assert {row["claim_status"] for row in rows.values()} == {"OPEN"}
    assert "OPEN / NOT LICENSED" in audit["claim_ceiling"]


def test_active_goal_auditor_only_licenses_w0_when_all_frozen_gates_pass(tmp_path):
    report_path = tmp_path / DEFAULT_W0_FULL_CONTROL_REPORT
    manifest_path = tmp_path / DEFAULT_W0_DATA_READINESS_MANIFEST
    hidden_screen_path = tmp_path / DEFAULT_HIDDEN_INJECTION_SURFACE_SCREEN
    report_path.parent.mkdir(parents=True)
    manifest_path.parent.mkdir(parents=True)
    hidden_screen_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"status": "READY_FOR_W0_CAPTURE"}), encoding="utf-8")
    hidden_screen_path.write_text(
        json.dumps(
            {
                "status": "READY_FOR_W0_CAPTURE",
                "claim": "OPEN / NOT LICENSED for internal W0 prompt-injection detection.",
                "row_count": 640,
                "prompt_group_count": 80,
                "testable_payload_class_count": 5,
                "metrics": {"text_hash_balanced_accuracy": 0.4},
            }
        ),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(
            {
                "schema_version": W0_REPORT_SCHEMA_VERSION,
                "status": "PASS",
                "layer": 28,
                "gates": {gate: True for gate in W0_REQUIRED_GATES},
                "metrics": {
                    "risk_hidden_balanced_accuracy": 0.82,
                    "risk_text_hash_balanced_accuracy": 0.61,
                    "risk_hidden_minus_text_balanced_accuracy": 0.21,
                    "risk_l0_embedding_balanced_accuracy": 0.5,
                    "risk_payload_majority_balanced_accuracy": 0.5,
                    "risk_domain_majority_balanced_accuracy": 0.5,
                    "risk_length_balanced_accuracy": 0.48,
                    "risk_within_payload_permutation_p": 0.001,
                    "risk_per_payload_hidden_balanced_accuracy": {
                        "system_instruction_boundary": 0.78
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    audit = audit_active_goal_claims(tmp_path)
    rows = {row["claim_id"]: row for row in audit["claims"]}
    w0 = rows["internal_w0_prompt_injection_detection"]

    assert w0["claim_status"] == "LICENSED"
    assert w0["license_status"] == "LICENSED"
    assert w0["failing_gates"] == []
    assert w0["observed_metrics"]["existing_w0_report_count"] == 1
    assert w0["observed_metrics"]["passing_w0_report_count"] == 1
    assert (
        w0["observed_metrics"]["best_existing_w0_candidate"]["license_eligible"] is True
    )
    assert audit["goal_complete"] is False
    assert rows["causal_proof"]["license_status"] == "NOT LICENSED"


def test_active_goal_auditor_licenses_hidden_injection_w0_when_all_gates_pass(tmp_path):
    report_path = tmp_path / DEFAULT_W0_FULL_CONTROL_REPORT
    manifest_path = tmp_path / DEFAULT_W0_DATA_READINESS_MANIFEST
    hidden_screen_path = tmp_path / DEFAULT_HIDDEN_INJECTION_SURFACE_SCREEN
    hidden_eval_path = (
        tmp_path
        / "docs"
        / "working"
        / "hidden_prompt_injection_prespeech_eval_synthetic_pass.json"
    )
    report_path.parent.mkdir(parents=True)
    manifest_path.parent.mkdir(parents=True)
    hidden_screen_path.parent.mkdir(parents=True, exist_ok=True)
    hidden_eval_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"status": "READY_FOR_W0_CAPTURE"}), encoding="utf-8")
    report_path.write_text(
        json.dumps(
            {
                "schema_version": W0_REPORT_SCHEMA_VERSION,
                "status": "FAIL",
                "layer": 28,
                "gates": {gate: False for gate in W0_REQUIRED_GATES},
                "metrics": {},
            }
        ),
        encoding="utf-8",
    )
    hidden_screen_path.write_text(
        json.dumps(
            {
                "status": "READY_FOR_W0_CAPTURE",
                "claim": "OPEN / NOT LICENSED for internal W0 prompt-injection detection.",
                "row_count": 2560,
                "prompt_group_count": 320,
                "testable_payload_class_count": 5,
                "metrics": {"text_hash_balanced_accuracy": 0.503125},
            }
        ),
        encoding="utf-8",
    )
    hidden_eval_path.write_text(
        json.dumps(
            {
                "schema_version": HIDDEN_INJECTION_W0_REPORT_SCHEMA_VERSION,
                "status": "PASS",
                "layer": 28,
                "gates": {gate: True for gate in HIDDEN_INJECTION_REQUIRED_GATES},
                "metrics": {
                    "hidden_balanced_accuracy": 0.82,
                    "text_hash_balanced_accuracy": 0.52,
                    "hidden_minus_text_balanced_accuracy": 0.30,
                    "within_payload_permutation_p": 0.0005,
                },
            }
        ),
        encoding="utf-8",
    )

    audit = audit_active_goal_claims(tmp_path)
    rows = {row["claim_id"]: row for row in audit["claims"]}
    w0 = rows["internal_w0_prompt_injection_detection"]

    assert w0["claim_status"] == "LICENSED"
    assert w0["license_status"] == "LICENSED"
    assert w0["failing_gates"] == []
    assert w0["observed_metrics"]["existing_hidden_injection_w0_report_count"] == 1
    assert w0["observed_metrics"]["passing_hidden_injection_w0_report_count"] == 1
    assert (
        w0["observed_metrics"]["best_hidden_injection_w0_candidate"]["license_eligible"]
        is True
    )
    assert audit["goal_complete"] is False
    assert rows["live_pre_speech_interception"]["license_status"] == "NOT LICENSED"


def test_active_goal_auditor_can_license_v5_causal_without_relicensing_prompt_injection(tmp_path):
    report_path = tmp_path / DEFAULT_W0_FULL_CONTROL_REPORT
    manifest_path = tmp_path / DEFAULT_W0_DATA_READINESS_MANIFEST
    hidden_screen_path = tmp_path / DEFAULT_HIDDEN_INJECTION_SURFACE_SCREEN
    prespeech_path = tmp_path / "docs" / "working" / "v5_prespeech_pass.json"
    causal_path = tmp_path / "docs" / "working" / "v5_causal_pass.json"
    report_path.parent.mkdir(parents=True)
    manifest_path.parent.mkdir(parents=True)
    hidden_screen_path.parent.mkdir(parents=True, exist_ok=True)
    prespeech_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"status": "READY_FOR_W0_CAPTURE"}), encoding="utf-8")
    hidden_screen_path.write_text(
        json.dumps(
            {
                "status": "READY_FOR_W0_CAPTURE",
                "claim": "OPEN / NOT LICENSED for internal W0 prompt-injection detection.",
                "metrics": {},
            }
        ),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(
            {
                "schema_version": W0_REPORT_SCHEMA_VERSION,
                "status": "FAIL",
                "layer": 28,
                "gates": {gate: False for gate in W0_REQUIRED_GATES},
                "metrics": {},
            }
        ),
        encoding="utf-8",
    )
    prespeech_path.write_text(
        json.dumps(
            {
                "schema_version": BEHAVIOR_V5_PRESPEECH_REPORT_SCHEMA_VERSION,
                "status": "PASS",
                "layer": 14,
                "mixed_prompt_group_count": 40,
                "gates": {gate: True for gate in BEHAVIOR_V5_PRESPEECH_REQUIRED_GATES},
                "metrics": {
                    "hidden_balanced_accuracy": 0.81,
                    "text_hash_balanced_accuracy": 0.52,
                    "char_text_hash_balanced_accuracy": 0.51,
                    "hidden_minus_text_balanced_accuracy": 0.29,
                    "hidden_minus_char_text_balanced_accuracy": 0.30,
                    "within_payload_permutation_p": 0.0005,
                },
            }
        ),
        encoding="utf-8",
    )
    causal_path.write_text(
        json.dumps(
            {
                "schema_version": BEHAVIOR_V5_CAUSAL_REPORT_SCHEMA_VERSION,
                "status": "PASS",
                "complete_prompt_seed_block_count": 320,
                "gates": {gate: True for gate in BEHAVIOR_V5_CAUSAL_REQUIRED_GATES},
                "metrics": {
                    "plus_refusal_refused_shift": 0.24,
                    "plus_refusal_sign_flip_p": 0.0005,
                    "random_same_norm_refused_shift": 0.01,
                },
            }
        ),
        encoding="utf-8",
    )

    audit = audit_active_goal_claims(tmp_path)
    rows = {row["claim_id"]: row for row in audit["claims"]}

    assert rows["internal_w0_prompt_injection_detection"]["license_status"] == "NOT LICENSED"
    assert rows["causal_proof"]["license_status"] == "LICENSED"
    assert rows["causal_proof"]["observed_metrics"]["behavior_v5_prespeech"]["passing_report_count"] == 1
    assert rows["causal_proof"]["observed_metrics"]["behavior_v5_causal"]["passing_report_count"] == 1
    assert audit["goal_complete"] is False


def test_active_goal_auditor_tracks_hallucination_detection_without_licensing_prevention(tmp_path):
    report_path = tmp_path / DEFAULT_W0_FULL_CONTROL_REPORT
    manifest_path = tmp_path / DEFAULT_W0_DATA_READINESS_MANIFEST
    hidden_screen_path = tmp_path / DEFAULT_HIDDEN_INJECTION_SURFACE_SCREEN
    hallucination_screen_path = tmp_path / DEFAULT_HALLUCINATION_SURFACE_SCREEN
    hallucination_path = (
        tmp_path
        / "docs"
        / "working"
        / "hallucination_prespeech_eval_synthetic_pass.json"
    )
    report_path.parent.mkdir(parents=True)
    manifest_path.parent.mkdir(parents=True)
    hidden_screen_path.parent.mkdir(parents=True, exist_ok=True)
    hallucination_screen_path.parent.mkdir(parents=True, exist_ok=True)
    hallucination_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"status": "READY_FOR_W0_CAPTURE"}), encoding="utf-8")
    hidden_screen_path.write_text(
        json.dumps(
            {
                "status": "READY_FOR_W0_CAPTURE",
                "claim": "OPEN / NOT LICENSED for internal W0 prompt-injection detection.",
                "metrics": {},
            }
        ),
        encoding="utf-8",
    )
    hallucination_screen_path.write_text(
        json.dumps(
            {
                "schema_version": "cas_harness_grounded_factual_qa_surface_screen.v1",
                "status": "READY_FOR_W0_CAPTURE",
                "claim": "OPEN / NOT LICENSED for internal W0 hallucination-risk detection.",
                "row_count": 400,
                "prompt_group_count": 40,
                "mixed_prompt_group_count": 40,
                "testable_topic_count": 5,
                "metrics": {
                    "text_hash_balanced_accuracy": 0.5,
                    "char_text_hash_balanced_accuracy": 0.5,
                    "topic_majority_balanced_accuracy": 0.5,
                    "retrieval_condition_majority_balanced_accuracy": 0.5,
                    "retrieval_score_bucket_majority_balanced_accuracy": 0.5,
                },
            }
        ),
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(
            {
                "schema_version": W0_REPORT_SCHEMA_VERSION,
                "status": "FAIL",
                "layer": 28,
                "gates": {gate: False for gate in W0_REQUIRED_GATES},
                "metrics": {},
            }
        ),
        encoding="utf-8",
    )
    hallucination_path.write_text(
        json.dumps(
            {
                "schema_version": HALLUCINATION_PRESPEECH_REPORT_SCHEMA_VERSION,
                "status": "PASS",
                "layer": 14,
                "mixed_prompt_group_count": 40,
                "gates": {gate: True for gate in HALLUCINATION_PRESPEECH_REQUIRED_GATES},
                "metrics": {
                    "hidden_balanced_accuracy": 0.82,
                    "text_hash_balanced_accuracy": 0.52,
                    "char_text_hash_balanced_accuracy": 0.51,
                    "hidden_minus_char_text_balanced_accuracy": 0.31,
                    "hidden_minus_retrieval_condition_balanced_accuracy": 0.30,
                    "hidden_minus_retrieval_score_bucket_balanced_accuracy": 0.32,
                    "within_topic_permutation_p": 0.0005,
                },
            }
        ),
        encoding="utf-8",
    )

    audit = audit_active_goal_claims(tmp_path)
    rows = {row["claim_id"]: row for row in audit["claims"]}
    hallucination = rows["hallucination_prevention"]

    assert hallucination["license_status"] == "NOT LICENSED"
    assert hallucination["claim_status"] == "OPEN"
    detection = hallucination["observed_metrics"]["hallucination_prespeech_detection"]
    assert detection["passing_report_count"] == 1
    assert detection["best_candidate"]["license_eligible"] is True
    surface = hallucination["observed_metrics"]["next_hallucination_surface_screen"]
    assert surface["status"] == "READY_FOR_W0_CAPTURE"
    assert surface["claim"] == "OPEN / NOT LICENSED for internal W0 hallucination-risk detection."
    assert "guardrail/intervention proof" in hallucination["reason"]
    assert audit["goal_complete"] is False


def test_active_goal_auditor_cli_writes_report_and_can_fail_on_open(tmp_path):
    out_path = tmp_path / "active_goal_audit.json"
    script = ROOT / "scripts" / "audit_cas_harness_active_goal_claims.py"

    ok = subprocess.run(
        [sys.executable, str(script), "--out", str(out_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(out_path.read_text(encoding="utf-8"))

    assert payload["goal_complete"] is False
    assert "internal_w0_prompt_injection_detection" in ok.stdout

    failed = subprocess.run(
        [sys.executable, str(script), "--out", str(out_path), "--fail-on-open"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert failed.returncode == 2
    assert json.loads(out_path.read_text(encoding="utf-8"))["goal_complete"] is False
