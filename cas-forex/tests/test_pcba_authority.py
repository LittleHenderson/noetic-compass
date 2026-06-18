"""PCBA authority licensing gate tests."""

from cas_forex.pcba_authority import (
    PcbaAuthorityReceipt,
    build_pcba_licensing_report,
    load_authority_receipts,
    merge_evidence,
    write_receipt_template,
    write_missing_receipt_templates,
)
from cas_forex.pcba_readiness import REQUIRED_EVIDENCE
from cas_forex.schemas.pcba import PcbaClaimCeiling, PcbaProductionFeature, PcbaReadinessStatus


LOCAL_PCBA_EVIDENCE = {
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
}


def _checks(report):
    return {check.feature: check for check in report.checks}


def _receipt(key, feature):
    return PcbaAuthorityReceipt(
        evidence_key=key,
        feature=feature,
        approved=True,
        operator_id="owner",
        signed_reason=f"Signed approval for {key}",
        signature=f"owner-signature:{key}",
    ).finalize()


def test_pcba_production_syntax_licenses_only_after_signed_semantics_receipt(tmp_path):
    report = build_pcba_licensing_report(LOCAL_PCBA_EVIDENCE)
    syntax = _checks(report)[PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX]
    assert syntax.status == PcbaReadinessStatus.OPEN
    assert syntax.claim_ceiling == PcbaClaimCeiling.OPEN
    assert not syntax.ready
    assert syntax.missing_evidence == ["pcba_semantics_review_signed"]

    receipt_path = tmp_path / "semantics.json"
    receipt_path.write_text(
        _receipt(
            "pcba_semantics_review_signed",
            PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX,
        ).model_dump_json(),
        encoding="utf-8",
    )
    receipt_evidence, diagnostics = load_authority_receipts([receipt_path])
    assert diagnostics[0]["verified"] is True

    licensed = build_pcba_licensing_report(merge_evidence(LOCAL_PCBA_EVIDENCE, receipt_evidence))
    syntax = _checks(licensed)[PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX]
    assert syntax.status == PcbaReadinessStatus.LICENSED
    assert syntax.claim_ceiling == PcbaClaimCeiling.OPEN
    assert syntax.ready
    assert syntax.missing_evidence == []


def test_signed_semantics_receipt_verifies_artifact_hashes(tmp_path):
    artifact = tmp_path / "pcba_syntax.py"
    artifact.write_text("parser = 'reviewed'\n", encoding="utf-8")
    receipt = write_receipt_template(
        tmp_path / "receipt.json",
        "pcba_semantics_review_signed",
        PcbaProductionFeature.PRODUCTION_COMPONENT_SYNTAX,
        artifact_refs=["pcba_syntax.py"],
        artifact_root=tmp_path,
    )
    assert receipt.artifact_hashes

    signed = receipt.model_copy(
        update={
            "approved": True,
            "operator_id": "owner",
            "signed_reason": "Reviewed PCBA semantics and artifact hash.",
            "signature": "owner-signature:pcba-semantics",
        }
    ).finalize()
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(signed.model_dump_json(), encoding="utf-8")

    evidence, diagnostics = load_authority_receipts([receipt_path], artifact_root=tmp_path)
    assert diagnostics[0]["verified"] is True
    assert evidence["pcba_semantics_review_signed"] is True

    artifact.write_text("parser = 'tampered'\n", encoding="utf-8")
    evidence, diagnostics = load_authority_receipts([receipt_path], artifact_root=tmp_path)
    assert diagnostics[0]["verified"] is False
    assert evidence["pcba_semantics_review_signed"] is False


def test_pcba_live_permission_requires_all_external_proof_receipts(tmp_path):
    receipt_paths = []
    for key in REQUIRED_EVIDENCE[PcbaProductionFeature.LIVE_TRADING_PERMISSION_PATH]:
        if key in LOCAL_PCBA_EVIDENCE:
            continue
        receipt = _receipt(key, PcbaProductionFeature.LIVE_TRADING_PERMISSION_PATH)
        path = tmp_path / f"{key}.json"
        path.write_text(receipt.model_dump_json(), encoding="utf-8")
        receipt_paths.append(path)

    receipt_evidence, _ = load_authority_receipts(receipt_paths)
    report = build_pcba_licensing_report(merge_evidence(LOCAL_PCBA_EVIDENCE, receipt_evidence))
    live = _checks(report)[PcbaProductionFeature.LIVE_TRADING_PERMISSION_PATH]

    assert live.status == PcbaReadinessStatus.LICENSED
    assert live.ready
    assert live.can_affect_live_trading
    assert not live.can_create_broker_accept


def test_pcba_claims_stay_not_licensed_until_all_required_receipts_present():
    report = build_pcba_licensing_report(LOCAL_PCBA_EVIDENCE)
    checks = _checks(report)

    for feature in [
        PcbaProductionFeature.COMPILER_ENFORCED_SAFETY_CLAIM,
        PcbaProductionFeature.PROMPT_INJECTION_PREVENTION_CLAIM,
        PcbaProductionFeature.GOVERNANCE_REGULATORY_PROOF_CLAIM,
    ]:
        assert checks[feature].status == PcbaReadinessStatus.NOT_LICENSED
        assert not checks[feature].ready
        assert checks[feature].missing_evidence


def test_pcba_broker_accept_creation_is_permanently_not_licensed_even_with_evidence():
    all_accept_evidence = {
        key: True
        for key in REQUIRED_EVIDENCE[PcbaProductionFeature.BROKER_ACCEPT_CREATION]
    }
    report = build_pcba_licensing_report(merge_evidence(LOCAL_PCBA_EVIDENCE, all_accept_evidence))
    accept = _checks(report)[PcbaProductionFeature.BROKER_ACCEPT_CREATION]

    assert accept.status == PcbaReadinessStatus.NOT_LICENSED
    assert not accept.ready
    assert accept.missing_evidence == []
    assert not accept.can_create_broker_accept


def test_missing_receipt_templates_are_written_for_external_gates(tmp_path):
    stale = tmp_path / "stale.json"
    stale.write_text("{}", encoding="utf-8")
    report = build_pcba_licensing_report(LOCAL_PCBA_EVIDENCE)
    written = write_missing_receipt_templates(report, tmp_path, clear_existing=True)

    assert written
    assert not stale.exists()
    assert any("pcba_semantics_review_signed" in path for path in written)
    assert any("thirty_trading_day_paper_proof_pass" in path for path in written)
    assert not any("pcba_parser_tests_pass" in path for path in written)


def test_missing_receipt_templates_preserve_supplied_receipt_paths_when_clearing(tmp_path):
    stale = tmp_path / "stale.json"
    stale.write_text("{}", encoding="utf-8")
    supplied = tmp_path / "compiler_enforced_safety_claim__red_team_report_pass.json"
    supplied.write_text('{"approved": true}\n', encoding="utf-8")

    report = build_pcba_licensing_report(LOCAL_PCBA_EVIDENCE)
    written = write_missing_receipt_templates(
        report,
        tmp_path,
        clear_existing=True,
        preserve_paths=[supplied],
    )

    assert supplied.exists()
    assert not stale.exists()
    assert str(supplied) not in written
