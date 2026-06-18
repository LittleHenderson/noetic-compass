"""Tests for the PCBA semantics human-review bundle."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cas_forex.pcba_semantics_review import build_pcba_semantics_review_bundle


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


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_pcba_semantics_review_bundle_is_ready_but_not_licensed():
    bundle = build_pcba_semantics_review_bundle(
        workspace_root=_workspace_root(),
        local_evidence=LOCAL_EVIDENCE,
    )

    assert bundle["ready_for_human_signature"] is True
    assert bundle["licensed"] is False
    assert all(item["exists"] for item in bundle["reviewed_artifacts"])
    assert all(item["sha256"] for item in bundle["reviewed_artifacts"])
    assert all(item["passed"] for item in bundle["parse_cases"])
    assert all(item["passed"] for item in bundle["invalid_parse_cases"])
    assert all(item["valid"] for item in bundle["compiler_pass_cases"])
    assert all(not item["valid"] for item in bundle["compiler_fail_cases"])

    assert bundle["syntax_gate"]["status"] == "OPEN"
    assert bundle["syntax_gate"]["missing_evidence"] == ["pcba_semantics_review_signed"]
    assert bundle["claim_boundaries"]["compiler_enforced_safety_claim"]["status"] == "NOT LICENSED"
    assert bundle["claim_boundaries"]["prompt_injection_prevention_claim"]["status"] == "NOT LICENSED"
    assert bundle["claim_boundaries"]["broker_accept_creation"]["status"] == "NOT LICENSED"


def test_pcba_semantics_review_bundle_script_writes_json_and_markdown(tmp_path):
    evidence_path = tmp_path / "local_evidence.json"
    evidence_path.write_text(json.dumps({"local_evidence": LOCAL_EVIDENCE}), encoding="utf-8")
    json_out = tmp_path / "bundle.json"
    md_out = tmp_path / "bundle.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_pcba_semantics_review_bundle.py",
            "--local-evidence",
            str(evidence_path),
            "--json-out",
            str(json_out),
            "--md-out",
            str(md_out),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["ready_for_human_signature"] is True
    assert payload["syntax_gate"]["status"] == "OPEN"
    text = md_out.read_text(encoding="utf-8")
    assert "PCBA Semantics Review Bundle" in text
    assert "`production_pcba_component_syntax`: `OPEN`" in text
    assert "`prompt_injection_prevention_claim`: `NOT LICENSED`" in text
