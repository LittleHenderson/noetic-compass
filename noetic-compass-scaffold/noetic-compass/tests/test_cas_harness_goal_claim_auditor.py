from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from api.services.cas_harness_goal_claim_auditor import (
    DEFAULT_HIDDEN_INJECTION_SURFACE_SCREEN,
    DEFAULT_W0_DATA_READINESS_MANIFEST,
    DEFAULT_W0_FULL_CONTROL_REPORT,
    HIDDEN_INJECTION_REQUIRED_GATES,
    HIDDEN_INJECTION_W0_REPORT_SCHEMA_VERSION,
    W0_REPORT_SCHEMA_VERSION,
    W0_REQUIRED_GATES,
    audit_active_goal_claims,
)


ROOT = Path(__file__).resolve().parents[1]


def test_active_goal_auditor_reflects_current_scoped_w0_license_boundary():
    audit = audit_active_goal_claims(ROOT)
    rows = {row["claim_id"]: row for row in audit["claims"]}
    w0 = rows["internal_w0_prompt_injection_detection"]

    assert audit["schema_version"] == "cas_harness_active_goal_claim_audit.v0"
    assert audit["goal_complete"] is False
    assert audit["summary"]["claims_total"] == 6
    assert audit["summary"]["claims_licensed"] == 1
    assert set(audit["summary"]["unlicensed_claim_ids"]) == set(rows) - {
        "internal_w0_prompt_injection_detection"
    }
    assert w0["claim_status"] == "LICENSED"
    assert w0["license_status"] == "LICENSED"
    assert w0["evidence_status"] == "present"
    assert w0["failing_gates"] == []
    assert {
        row["license_status"]
        for claim_id, row in rows.items()
        if claim_id != "internal_w0_prompt_injection_detection"
    } == {"NOT LICENSED"}
    assert {
        row["claim_status"]
        for claim_id, row in rows.items()
        if claim_id != "internal_w0_prompt_injection_detection"
    } == {"OPEN"}

    assert w0["observed_metrics"]["existing_w0_report_count"] > 1
    assert w0["observed_metrics"]["passing_w0_report_count"] == 0
    assert (
        w0["observed_metrics"]["next_hidden_injection_surface_screen"]["status"]
        == "READY_FOR_W0_CAPTURE"
    )
    assert (
        w0["observed_metrics"]["next_hidden_injection_surface_screen"][
            "text_hash_balanced_accuracy"
        ]
        == 0.503125
    )
    assert w0["observed_metrics"]["existing_hidden_injection_w0_report_count"] >= 1
    assert w0["observed_metrics"]["passing_hidden_injection_w0_report_count"] == 1
    assert (
        w0["observed_metrics"]["best_hidden_injection_w0_candidate"][
            "license_eligible"
        ]
        is True
    )
    assert (
        w0["observed_metrics"]["best_hidden_injection_w0_candidate"][
            "hidden_balanced_accuracy"
        ]
        == 0.896875
    )
    assert (
        w0["observed_metrics"]["best_hidden_injection_w0_candidate"][
            "hidden_minus_text_balanced_accuracy"
        ]
        == 0.39375
    )
    assert (
        w0["observed_metrics"]["best_hidden_injection_w0_candidate"][
            "within_payload_permutation_p"
        ]
        == 0.000999
    )
    assert (
        w0["observed_metrics"]["best_existing_w0_candidate"]["license_eligible"] is False
    )
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
