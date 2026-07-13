from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts import validate_incident_response_package as validator


ROOT = Path(__file__).resolve().parents[1]
CONTROL_PATH = ROOT / validator.CONTROL_PATH
RECORD_PATH = ROOT / validator.RECORD_DIR / "IR-2026-07-13-001.json"


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

    assert any("systems must cover" in error for error in errors)
    assert any("response checklist must cover" in error for error in errors)
