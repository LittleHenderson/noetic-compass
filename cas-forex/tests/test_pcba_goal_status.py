"""Tests for the focused active PCBA goal status auditor."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cas_forex.pcba_authority import PcbaAuthorityReceipt, write_receipt_template
from cas_forex.pcba_goal_status import build_pcba_goal_status
from cas_forex.schemas.pcba import PcbaProductionFeature


LOCAL_EVIDENCE = {
    "pcba_grammar_spec_present": True,
    "pcba_parser_implementation_present": True,
    "pcba_component_catalog_complete": True,
    "pcba_parser_tests_pass": True,
    "pcba_invalid_form_tests_pass": True,
    "pcba_ir_roundtrip_tests_pass": True,
    "pcba_production_compiler_integration_tests_pass": True,
    "formal_pcba_safety_semantics": True,
    "negative_safety_eval_pass": True,
    "evidence_anchor_pass": True,
    "matched_prompt_injection_eval_pass": True,
    "false_positive_floor_pass": True,
    "repeatability_packet_chain_pass": True,
    "pcba_no_accept_bypass_tests_pass": True,
    "no_pcba_to_accept_route": True,
    "auditor_accept_requires_gate_passes": True,
    "broker_accept_negative_tests_pass": True,
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_receipt(tmp_path: Path, *, signed: bool) -> Path:
    artifact = tmp_path / "pcba_syntax.py"
    artifact.write_text("parser = 'reviewed'\n", encoding="utf-8")
    receipt_path = tmp_path / "receipt.json"
    receipt = write_receipt_template(
        receipt_path,
        "pcba_semantics_review_signed",
        PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX,
        artifact_refs=["pcba_syntax.py"],
        artifact_root=tmp_path,
    )
    if signed:
        payload = receipt.model_dump(mode="json")
        payload.update(
            {
                "approved": True,
                "operator_id": "owner",
                "signed_reason": "Reviewed PCBA semantics.",
                "signature": "owner-signature:pcba-semantics",
                "receipt_hash": None,
            }
        )
        receipt = PcbaAuthorityReceipt.model_validate(payload).finalize()
        receipt_path.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
    return receipt_path


def _write_simple_receipt(tmp_path: Path, key: str, feature: PcbaProductionFeature) -> Path:
    receipt = PcbaAuthorityReceipt(
        evidence_key=key,
        feature=feature,
        approved=True,
        operator_id="owner",
        signed_reason=f"Reviewed {key}.",
        signature=f"owner-signature:{key}",
    ).finalize()
    receipt_path = tmp_path / f"{key}.json"
    receipt_path.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")
    return receipt_path


def test_goal_status_current_unsigned_receipt_is_incomplete(tmp_path):
    receipt = _write_receipt(tmp_path, signed=False)

    status = build_pcba_goal_status(
        local_evidence=LOCAL_EVIDENCE,
        receipt_paths=[receipt],
        artifact_root=tmp_path,
    )

    assert status["goal_complete"] is False
    assert status["current_boundary_honest"] is True
    assert status["syntax_receipt_verified"] is False
    assert status["syntax_only_missing_receipt"] is True
    assert status["checks"]["production_pcba_component_syntax"]["status"] == "OPEN"
    assert status["checks"]["compiler_enforced_safety_claim"]["status"] == "NOT LICENSED"
    assert status["checks"]["prompt_injection_prevention_claim"]["status"] == "NOT LICENSED"


def test_goal_status_signed_receipt_closes_syntax_only(tmp_path):
    receipt = _write_receipt(tmp_path, signed=True)

    status = build_pcba_goal_status(
        local_evidence=LOCAL_EVIDENCE,
        receipt_paths=[receipt],
        artifact_root=tmp_path,
    )

    assert status["goal_complete"] is True
    assert status["syntax_receipt_verified"] is True
    assert status["syntax_gate_closed"] is True
    assert status["checks"]["production_pcba_component_syntax"]["status"] == "LICENSED"
    assert status["checks"]["compiler_enforced_safety_claim"]["status"] == "NOT LICENSED"
    assert status["checks"]["prompt_injection_prevention_claim"]["status"] == "NOT LICENSED"


def test_goal_status_all_scoped_claim_receipts_license_claims_without_live_or_accept(tmp_path):
    receipts = [
        _write_receipt(tmp_path, signed=True),
        _write_simple_receipt(
            tmp_path,
            "red_team_report_pass",
            PcbaProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM,
        ),
        _write_simple_receipt(
            tmp_path,
            "claim_review_signed",
            PcbaProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM,
        ),
        _write_simple_receipt(
            tmp_path,
            "hidden_text_control_pass",
            PcbaProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM,
        ),
        _write_simple_receipt(
            tmp_path,
            "red_team_prompt_injection_pass",
            PcbaProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM,
        ),
    ]

    status = build_pcba_goal_status(
        local_evidence=LOCAL_EVIDENCE,
        receipt_paths=receipts,
        artifact_root=tmp_path,
    )

    assert status["goal_complete"] is True
    assert status["safety_claim_licensed"] is True
    assert status["prompt_claim_licensed"] is True
    assert status["live_boundary_holds"] is True
    assert status["broker_accept_boundary_holds"] is True
    assert status["checks"]["compiler_enforced_safety_claim"]["status"] == "LICENSED"
    assert status["checks"]["prompt_injection_prevention_claim"]["status"] == "LICENSED"
    assert status["checks"]["live_trading_permission_path"]["status"] == "NOT LICENSED"
    assert status["checks"]["broker_accept_creation"]["status"] == "NOT LICENSED"


def test_goal_status_cli_writes_artifacts_and_exits_nonzero_until_signed(tmp_path):
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps({"local_evidence": LOCAL_EVIDENCE}), encoding="utf-8")
    receipt = _write_receipt(tmp_path, signed=False)
    json_out = tmp_path / "status.json"
    md_out = tmp_path / "status.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/audit_pcba_goal_status.py",
            "--local-evidence",
            str(evidence_path),
            "--receipt",
            str(receipt),
            "--artifact-root",
            str(tmp_path),
            "--json-out",
            str(json_out),
            "--md-out",
            str(md_out),
        ],
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["goal_complete"] is False
    assert payload["syntax_only_missing_receipt"] is True
    markdown = md_out.read_text(encoding="utf-8")
    assert "PCBA Goal Status" in markdown
    assert "`production_pcba_component_syntax` | `OPEN`" in markdown
