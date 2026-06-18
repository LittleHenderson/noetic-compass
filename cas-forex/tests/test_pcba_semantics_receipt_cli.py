"""CLI coverage for the PCBA semantics receipt closeout path."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cas_forex.pcba_authority import PcbaAuthorityReceipt, write_receipt_template
from cas_forex.schemas.pcba import PcbaProductionFeature


LOCAL_SYNTAX_EVIDENCE = {
    "local_evidence": {
        "pcba_grammar_spec_present": True,
        "pcba_parser_implementation_present": True,
        "pcba_component_catalog_complete": True,
        "pcba_parser_tests_pass": True,
        "pcba_invalid_form_tests_pass": True,
        "pcba_ir_roundtrip_tests_pass": True,
        "pcba_production_compiler_integration_tests_pass": True,
        "pcba_no_accept_bypass_tests_pass": True,
        "no_pcba_to_accept_route": True,
        "auditor_accept_requires_gate_passes": True,
        "broker_accept_negative_tests_pass": True,
        "formal_pcba_safety_semantics": True,
        "negative_safety_eval_pass": True,
        "evidence_anchor_pass": True,
        "matched_prompt_injection_eval_pass": True,
        "false_positive_floor_pass": True,
        "repeatability_packet_chain_pass": True,
    }
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_verifier(tmp_path: Path, receipt_path: Path, evidence_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/verify_pcba_semantics_receipt.py",
            "--receipt",
            str(receipt_path),
            "--local-evidence",
            str(evidence_path),
            "--artifact-root",
            str(tmp_path),
            "--out",
            str(tmp_path / "verification.json"),
        ],
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )


def _run_finalizer(tmp_path: Path, receipt_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/finalize_pcba_authority_receipt.py",
            "--receipt",
            str(receipt_path),
            "--artifact-root",
            str(tmp_path),
        ],
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )


def _run_authority_report(
    tmp_path: Path,
    receipt_path: Path,
    evidence_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/issue_pcba_authority_report.py",
            "--receipt",
            str(receipt_path),
            "--local-evidence",
            str(evidence_path),
            "--artifact-root",
            str(tmp_path),
            "--write-semantics-template",
            str(receipt_path),
            "--write-missing-templates-dir",
            str(tmp_path / "missing"),
            "--out",
            str(tmp_path / "authority.json"),
        ],
        cwd=_repo_root(),
        text=True,
        capture_output=True,
        check=False,
    )


def _write_template(tmp_path: Path) -> Path:
    artifact = tmp_path / "pcba_syntax.py"
    artifact.write_text("parser = 'reviewed'\n", encoding="utf-8")
    receipt_path = tmp_path / "pcba_semantics_review.json"
    write_receipt_template(
        receipt_path,
        "pcba_semantics_review_signed",
        PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX,
        artifact_refs=["pcba_syntax.py"],
        artifact_root=tmp_path,
    )
    return receipt_path


def _approve_receipt_without_hash(receipt_path: Path) -> None:
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    payload.update(
        {
            "approved": True,
            "operator_id": "owner",
            "signed_reason": "Reviewed PCBA production component semantics and artifact hashes.",
            "signature": "owner-signature:pcba-semantics-review",
            "receipt_hash": None,
        }
    )
    receipt_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sign_receipt(receipt_path: Path) -> None:
    _approve_receipt_without_hash(receipt_path)
    receipt = PcbaAuthorityReceipt.model_validate_json(receipt_path.read_text(encoding="utf-8")).finalize()
    receipt_path.write_text(receipt.model_dump_json(indent=2), encoding="utf-8")


def test_semantics_receipt_cli_rejects_unsigned_receipt(tmp_path):
    evidence_path = tmp_path / "local_evidence.json"
    evidence_path.write_text(json.dumps(LOCAL_SYNTAX_EVIDENCE), encoding="utf-8")
    receipt_path = _write_template(tmp_path)

    result = _run_verifier(tmp_path, receipt_path, evidence_path)

    assert result.returncode == 1
    payload = json.loads((tmp_path / "verification.json").read_text(encoding="utf-8"))
    assert payload["licensed"] is False
    assert payload["syntax_check"]["status"] == "OPEN"
    assert payload["syntax_check"]["missing_evidence"] == ["pcba_semantics_review_signed"]


def test_semantics_receipt_cli_licenses_syntax_only_after_verified_receipt(tmp_path):
    evidence_path = tmp_path / "local_evidence.json"
    evidence_path.write_text(json.dumps(LOCAL_SYNTAX_EVIDENCE), encoding="utf-8")
    receipt_path = _write_template(tmp_path)
    _sign_receipt(receipt_path)

    result = _run_verifier(tmp_path, receipt_path, evidence_path)

    assert result.returncode == 0
    payload = json.loads((tmp_path / "verification.json").read_text(encoding="utf-8"))
    assert payload["licensed"] is True
    assert payload["syntax_check"]["status"] == "LICENSED"
    assert payload["syntax_check"]["ready"] is True
    assert payload["guardrails"]["compiler_enforced_safety_claim"]["status"] == "NOT LICENSED"
    assert payload["guardrails"]["prompt_injection_prevention_claim"]["status"] == "NOT LICENSED"
    assert payload["guardrails"]["broker_accept_creation"]["status"] == "NOT LICENSED"


def test_finalize_receipt_cli_hashes_approved_receipt_for_verifier(tmp_path):
    evidence_path = tmp_path / "local_evidence.json"
    evidence_path.write_text(json.dumps(LOCAL_SYNTAX_EVIDENCE), encoding="utf-8")
    receipt_path = _write_template(tmp_path)
    _approve_receipt_without_hash(receipt_path)

    finalize = _run_finalizer(tmp_path, receipt_path)
    assert finalize.returncode == 0
    finalized = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert finalized["receipt_hash"]

    result = _run_verifier(tmp_path, receipt_path, evidence_path)
    assert result.returncode == 0


def test_finalize_receipt_cli_rejects_unsigned_receipt(tmp_path):
    receipt_path = _write_template(tmp_path)

    finalize = _run_finalizer(tmp_path, receipt_path)

    assert finalize.returncode != 0
    assert "Receipt could not be verified" in finalize.stderr or "Approved receipt requires" in finalize.stderr


def test_authority_report_does_not_overwrite_existing_signed_semantics_receipt(tmp_path):
    evidence_path = tmp_path / "local_evidence.json"
    evidence_path.write_text(json.dumps(LOCAL_SYNTAX_EVIDENCE), encoding="utf-8")
    receipt_path = _write_template(tmp_path)
    _approve_receipt_without_hash(receipt_path)
    finalize = _run_finalizer(tmp_path, receipt_path)
    assert finalize.returncode == 0
    signed_payload = json.loads(receipt_path.read_text(encoding="utf-8"))

    result = _run_authority_report(tmp_path, receipt_path, evidence_path)

    assert result.returncode == 0
    after_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert after_payload == signed_payload
    authority = json.loads((tmp_path / "authority.json").read_text(encoding="utf-8"))
    syntax = next(
        check
        for check in authority["readiness_report"]["checks"]
        if check["feature"] == "production_pcba_component_syntax"
    )
    assert syntax["status"] == "LICENSED"


def test_semantics_receipt_cli_rejects_tampered_artifact(tmp_path):
    evidence_path = tmp_path / "local_evidence.json"
    evidence_path.write_text(json.dumps(LOCAL_SYNTAX_EVIDENCE), encoding="utf-8")
    receipt_path = _write_template(tmp_path)
    _sign_receipt(receipt_path)
    (tmp_path / "pcba_syntax.py").write_text("parser = 'tampered'\n", encoding="utf-8")

    result = _run_verifier(tmp_path, receipt_path, evidence_path)

    assert result.returncode == 1
    payload = json.loads((tmp_path / "verification.json").read_text(encoding="utf-8"))
    assert payload["licensed"] is False
    assert payload["receipt_diagnostics"][0]["verified"] is False
