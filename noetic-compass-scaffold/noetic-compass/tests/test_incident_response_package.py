from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts import validate_incident_response_package as validator


ROOT = Path(__file__).resolve().parents[1]
CONTROL_PATH = ROOT / validator.CONTROL_PATH
RECORD_PATH = ROOT / validator.RECORD_DIR / "IR-2026-07-13-001.json"
MARKDOWN_PATH = RECORD_PATH.with_suffix(".md")


def _control() -> dict:
    return json.loads(CONTROL_PATH.read_text(encoding="utf-8"))


def _record() -> dict:
    return json.loads(RECORD_PATH.read_text(encoding="utf-8"))


def test_checked_in_incident_response_package_passes() -> None:
    assert validator.validate_package(ROOT) == []


def test_record_rejects_raw_secret_field() -> None:
    record = _record()
    record["credential_value"] = "not-a-real-secret-value"

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("prohibited raw-secret field" in error for error in errors)


def test_record_rejects_credential_shape_in_text() -> None:
    record = _record()
    record["claim_boundary"]["notes"] = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz"

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("possible bearer credential" in error for error in errors)


def test_record_requires_exact_known_rotation_and_recovery_facts() -> None:
    record = _record()
    events = {event["id"]: event for event in record["observed_events"]}
    events["worker_token_rotation"]["old_credential_removed"] = False
    events["blueprint_sync_hook_rotation"]["rotation_pending"] = False
    events["aws_production_iam_key"]["credential_state"] = "valid"
    events["runpod_mfa"]["personal_action_required"] = False

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("worker token rotation" in error for error in errors)
    assert any("Blueprint sync-hook rotation" in error for error in errors)
    assert any("AWS production IAM key" in error for error in errors)
    assert any("RunPod MFA" in error for error in errors)


def test_record_cannot_promote_open_worm_or_production_readiness() -> None:
    record = copy.deepcopy(_record())
    record["claim_boundary"]["production_readiness_status"] = "ACCEPT"
    record["evidence_handling"]["worm_status"] = "ACCEPT"

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("production_readiness_status must remain OPEN" in error for error in errors)
    assert any("WORM status must remain OPEN" in error for error in errors)


def test_record_requires_every_provider_and_response_phase() -> None:
    record = _record()
    del record["systems"]["Vercel"]
    record["response_checklist"] = record["response_checklist"][:-1]

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("systems must exactly match the immutable scope" in error for error in errors)
    assert any("response checklist must cover" in error for error in errors)


def test_incident_state_is_categorically_open_only() -> None:
    for forbidden_status in ("MONITORING", "CLOSED"):
        record = _record()
        record["status"] = forbidden_status

        errors = validator.validate_incident_record(record, _control(), source="memory")

        assert any("incident status must remain OPEN" in error for error in errors)


def test_completed_claims_are_disabled_until_separate_chronology_verifier() -> None:
    record = _record()
    record["observed_events"][0]["status"] = "complete"
    record["response_checklist"][0]["status"] = "complete"
    record["open_actions"][0]["status"] = "COMPLETE"
    record["notification_decision"]["status"] = "complete"
    record["tabletop"]["exercise_status"] = "complete"

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("completed event claims require" in error for error in errors)
    assert any("complete/not_applicable claims require" in error for error in errors)
    assert any("COMPLETE requires" in error for error in errors)
    assert any("notification_decision must remain pending" in error for error in errors)
    assert any("tabletop must remain participant_run_pending" in error for error in errors)


def test_original_incident_system_event_and_action_scope_is_immutable() -> None:
    record = _record()
    record["systems"]["AWS"].pop()
    record["observed_events"].pop()
    record["observed_events"].append(
        {
            "id": "replacement_event",
            "provider": "AWS/Render",
            "status": "blocked",
            "secret_material_recorded": False,
        }
    )
    record["open_actions"][0]["action"] = "A narrower replacement action."
    record["open_actions"].pop()

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("systems must exactly match the immutable scope" in error for error in errors)
    assert any("observed event IDs must exactly match the immutable scope" in error for error in errors)
    assert any("action text and owner must match the immutable scope" in error for error in errors)
    assert any("exactly match the seven immutable actions" in error for error in errors)


def test_event_provider_binding_cannot_be_rewritten() -> None:
    record = _record()
    record["observed_events"][0]["provider"] = "SelfAttestedProvider"

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("provider must remain pinned" in error for error in errors)


def test_unregistered_incident_has_no_mutable_default_scope() -> None:
    record = _record()
    record["incident_id"] = "IR-2026-07-14-999"

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("has no pinned immutable scope" in error for error in errors)


def test_assigned_control_roles_require_separation_of_duties() -> None:
    record = _record()
    record["roles"]["incident_commander"] = "Alex Example"
    record["roles"]["security_forensics_lead"] = "alex example"

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("assigned role identities must be distinct" in error for error in errors)


def test_typed_or_untracked_local_evidence_cannot_attest_to_closure() -> None:
    record = _record()
    record["observed_events"][0]["evidence_references"] = [
        {
            "artifact_type": "provider_event",
            "path": "docs/working/incident_response/evidence/self-attested.json",
            "sha256": "a" * 64,
        }
    ]

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("typed/local evidence artifacts are disabled" in error for error in errors)

    record = _record()
    record["observed_events"][0]["evidence_references"] = [
        "docs/working/incident_response/evidence/self-attested.json"
    ]

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("cannot cite local or temporary artifact paths" in error for error in errors)


def test_incident_record_cannot_mint_accept_in_any_nested_field() -> None:
    record = _record()
    record["claim_boundary"]["notes"] = "customer-production ACCEPT"

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("customer-production ACCEPT is prohibited" in error for error in errors)


def test_unknown_closure_or_receipt_fields_are_rejected() -> None:
    record = _record()
    record["closure_approvals"] = {"incident_commander": "self-attested"}

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("OPEN-only incident fields must match the pinned schema" in error for error in errors)


def test_terminal_state_scalar_cannot_hide_inside_an_existing_object() -> None:
    record = _record()
    record["severity"]["review_status"] = "CLOSED"

    errors = validator.validate_incident_record(record, _control(), source="memory")

    assert any("terminal state 'CLOSED' is prohibited" in error for error in errors)


def test_markdown_twin_rejects_accept_and_status_contradictions() -> None:
    record = _record()
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8")
    markdown = markdown.replace(
        "| Customer-production readiness | `OPEN` |",
        "| Customer-production readiness | `ACCEPT` |",
    ).replace("| Status | `OPEN` |", "| Status | `CLOSED` |")

    errors = validator._validate_markdown_twin(record, markdown, source="memory.md")

    assert any("ACCEPT is prohibited" in error for error in errors)
    assert any("Markdown record status must be exactly OPEN" in error for error in errors)
    assert any("Markdown customer-production readiness must be exactly OPEN" in error for error in errors)
    assert any("Markdown contradicts the OPEN-only JSON status" in error for error in errors)


def test_markdown_action_register_must_match_json() -> None:
    record = _record()
    markdown = MARKDOWN_PATH.read_text(encoding="utf-8").replace(
        "| IR-ACT-001 | Assign roles, on-call contacts, cadence and closure approver | Incident Commander | `[SET]` | Named primary/backup/contact for every required role | `OPEN` |",
        "| IR-ACT-001 | Assign roles, on-call contacts, cadence and closure approver | Incident Commander | `[SET]` | Named primary/backup/contact for every required role | `BLOCKED` |",
    )

    errors = validator._validate_markdown_twin(record, markdown, source="memory.md")

    assert any("Markdown action statuses must exactly match" in error for error in errors)
