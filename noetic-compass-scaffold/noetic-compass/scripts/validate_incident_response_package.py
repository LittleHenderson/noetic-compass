#!/usr/bin/env python3
"""Validate the non-secret CAS Harness incident-response control and records."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTROL_PATH = Path("docs/runbooks/incident_response_checklist.json")
RUNBOOK_PATH = Path("docs/runbooks/incident_response.md")
POSTMORTEM_PATH = Path("docs/runbooks/incident_postmortem_template.md")
RECORD_DIR = Path("docs/working/incident_response")

EXPECTED_SEVERITIES = {"SEV-0", "SEV-1", "SEV-2", "SEV-3"}
EXPECTED_PROVIDERS = {"RunPod", "Render", "AWS", "GitHub", "Vercel"}
EXPECTED_PHASE_CONTROLS = {
    "declare_and_assign",
    "freeze_and_preserve",
    "revoke_or_rotate",
    "scope_unauthorized_use",
    "eradicate_root_cause",
    "recover_exact_sha",
    "verify_evidence_integrity",
    "notification_decision",
    "postmortem_and_actions",
}
EXPECTED_NOTIFICATION_GATES = {
    "scope_data_and_tenants",
    "identify_contracts_and_jurisdictions",
    "start_or_reject_notification_clocks",
    "approve_factual_message",
    "record_decision_and_revisit",
}
EXPECTED_ROLES = {
    "incident_commander",
    "security_forensics_lead",
    "infrastructure_lead",
    "customer_operations_lead",
    "privacy_legal_advisor",
    "communications_lead",
    "incident_recorder",
}
OPEN_ONLY_INCIDENT_ID = "IR-2026-07-13-001"
OPEN_ONLY_RECORD_FIELDS = {
    "schema_version",
    "incident_id",
    "record_type",
    "title",
    "status",
    "severity",
    "compromise_status",
    "claim_boundary",
    "time_control",
    "roles",
    "systems",
    "observed_events",
    "response_checklist",
    "notification_decision",
    "evidence_handling",
    "tabletop",
    "open_actions",
}
OPEN_ONLY_EVENT_STATUSES = {"not_started", "in_progress", "blocked"}
OPEN_ONLY_TASK_STATUSES = {"not_started", "in_progress", "blocked"}
OPEN_ONLY_ACTION_STATUSES = {"OPEN", "IN_PROGRESS", "BLOCKED"}
PINNED_SYSTEM_SCOPE = {
    "RunPod": ["pod hilj2rzs54gi06"],
    "Render": [
        "public service srv-d82ph683kofs73d210e0",
        "account canary service srv-d9akoolaeets73bp3e7g",
        "production Blueprint exs-d82lpanaqgkc7399m1g0",
        "canary Blueprint exs-d9aknt8458ps73ftpkc0",
    ],
    "AWS": [
        "cas-harness-render-production application IAM principal",
        "production S3 Evidence Packet anchor path",
    ],
    "GitHub": ["LittleHenderson/noetic-compass"],
    "Vercel": ["Noetic Compass production and preview deployments"],
}
PINNED_EVENT_PROVIDERS = {
    "worker_token_rotation": "RunPod/Render",
    "canary_deploy_hook_rotation": "Render",
    "blueprint_sync_hook_rotation": "Render",
    "aws_production_iam_key": "AWS/Render",
    "runpod_mfa": "RunPod",
}
PINNED_ACTIONS = {
    "IR-ACT-001": (
        "Assign the incident-response roles, on-call contacts, communication cadence, and closure approver.",
        "incident_commander",
    ),
    "IR-ACT-002": (
        "Export and review scoped RunPod, Render, AWS, GitHub, and Vercel audit activity; record non-secret event IDs, UTC window, digest, findings, and limitations.",
        "security_forensics_lead",
    ),
    "IR-ACT-003": (
        "Obtain and verify server-side Blueprint sync-hook rotation, then prove the prior hook can no longer initiate a sync without recording either URL.",
        "infrastructure_lead",
    ),
    "IR-ACT-004": (
        "Restore AWS administration, replace the invalid key with a least-privilege cas-harness-render-production application key, redeploy Render, and rerun STS/IAM/S3/WORM verification.",
        "infrastructure_lead",
    ),
    "IR-ACT-005": (
        "Enable RunPod MFA through the account owner's personal action and record only the enabled state and verification UTC.",
        "account_owner",
    ),
    "IR-ACT-006": (
        "Complete the customer/authority/insurer/vendor notification decision gate from scoped facts and applicable sources.",
        "privacy_legal_advisor",
    ),
    "IR-ACT-007": (
        "Run the tabletop with assigned participants and close resulting corrective actions through tested evidence.",
        "incident_commander",
    ),
}
PLACEHOLDER_IDENTITY_RE = re.compile(r"^\[(?:ASSIGN|PENDING|SET|SCHEDULE)(?::[^]]+)?]$")
ACCEPT_CLAIM_RE = re.compile(r"\bACCEPT\b")
TERMINAL_STATE_VALUES = {
    "MONITORING",
    "CLOSED",
    "COMPLETE",
    "complete",
    "not_applicable",
    "present",
}
PROHIBITED_SECRET_FIELD_NAMES = {
    "password",
    "token",
    "secret",
    "api_key",
    "access_key",
    "secret_access_key",
    "private_key",
    "session_cookie",
    "recovery_code",
    "credential_value",
    "hook_url",
    "deploy_hook_url",
    "sync_hook_url",
}
SUSPICIOUS_SECRET_PATTERNS = {
    "AWS access key identifier": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    "bearer credential": re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[A-Za-z0-9._~-]{12,}"),
    "secret assignment": re.compile(
        r"(?i)\b(?:password|token|secret|api[_-]?key|access[_-]?key)\s*[:=]\s*[A-Za-z0-9/+_.~-]{12,}"
    ),
    "credentialized URL": re.compile(
        r"(?i)https?://[^\s<>]+[?&](?:key|token|secret|signature)=[^\s<>&]{8,}"
    ),
}


def _load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: cannot load JSON: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"{path}: top-level JSON must be an object")
        return None
    return data


def _ids(items: Any, *, source: str, field: str, errors: list[str]) -> set[str]:
    if not isinstance(items, list):
        errors.append(f"{source}: {field} must be a list")
        return set()
    values: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            errors.append(f"{source}: {field}[{index}] must have a string id")
            continue
        item_id = item["id"]
        if item_id in values:
            errors.append(f"{source}: duplicate {field} id {item_id!r}")
        values.add(item_id)
    return values


def _find_prohibited_fields(value: Any, *, location: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            if key.lower() in PROHIBITED_SECRET_FIELD_NAMES:
                errors.append(f"prohibited raw-secret field {child_location}")
            errors.extend(_find_prohibited_fields(child, location=child_location))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_find_prohibited_fields(child, location=f"{location}[{index}]"))
    return errors


def _scan_text_for_secret_shapes(text: str, *, source: str) -> list[str]:
    errors: list[str] = []
    for label, pattern in SUSPICIOUS_SECRET_PATTERNS.items():
        match = pattern.search(text)
        if match:
            errors.append(f"{source}: possible {label} at character {match.start()}")
    return errors


def _find_accept_claims(value: Any, *, location: str = "$") -> list[str]:
    """Reject ACCEPT anywhere in an incident record.

    Incident handling is not the customer-production acceptance authority.  A
    separate verifier owns that verdict, so this validator deliberately has no
    positive ACCEPT representation.
    """

    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            errors.extend(_find_accept_claims(child, location=f"{location}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_find_accept_claims(child, location=f"{location}[{index}]"))
    elif isinstance(value, str) and ACCEPT_CLAIM_RE.search(value):
        errors.append(f"customer-production ACCEPT is prohibited at {location}")
    return errors


def _find_terminal_state_claims(value: Any, *, location: str = "$") -> list[str]:
    """Reject terminal state scalars anywhere in an OPEN-only record."""

    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            errors.extend(
                _find_terminal_state_claims(child, location=f"{location}.{key}")
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(
                _find_terminal_state_claims(child, location=f"{location}[{index}]")
            )
    elif isinstance(value, str) and value.strip() in TERMINAL_STATE_VALUES:
        errors.append(
            f"terminal state {value.strip()!r} is prohibited in OPEN-only mode at {location}"
        )
    return errors


def _validate_open_only_references(
    value: Any, *, source: str, location: str = "$"
) -> list[str]:
    """Keep evidence references informational while closure support is disabled.

    Object-shaped references formerly allowed an untracked local JSON file to
    attest to its own authority.  OPEN-only records may name non-secret provider
    IDs as strings, but this validator never dereferences them or treats them as
    completion evidence.
    """

    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}.{key}"
            if key.endswith("references"):
                if not isinstance(child, list) or not all(
                    isinstance(reference, str) and reference.strip() for reference in child
                ):
                    errors.append(
                        f"{source}: {child_location} must contain only non-empty informational strings; "
                        "typed/local evidence artifacts are disabled in OPEN-only mode"
                    )
                elif any(
                    reference.strip().lower().endswith(".json")
                    or "/evidence/" in reference.replace("\\", "/").lower()
                    or reference.replace("\\", "/").lower().startswith(("tmp/", "/tmp/"))
                    for reference in child
                ):
                    errors.append(
                        f"{source}: {child_location} cannot cite local or temporary artifact paths "
                        "in OPEN-only mode"
                    )
            errors.extend(
                _validate_open_only_references(
                    child, source=source, location=child_location
                )
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(
                _validate_open_only_references(
                    child, source=source, location=f"{location}[{index}]"
                )
            )
    return errors


def _validate_distinct_assigned_roles(
    roles: Any, *, source: str
) -> list[str]:
    errors: list[str] = []
    if not isinstance(roles, dict):
        return errors
    seen: dict[str, str] = {}
    for role, identity in roles.items():
        if not isinstance(identity, str) or not identity.strip():
            errors.append(f"{source}: role {role!r} must have a non-empty identity or placeholder")
            continue
        normalized = identity.strip()
        if PLACEHOLDER_IDENTITY_RE.fullmatch(normalized):
            continue
        identity_key = normalized.casefold()
        prior_role = seen.get(identity_key)
        if prior_role is not None:
            errors.append(
                f"{source}: assigned role identities must be distinct; {prior_role!r} and {role!r} "
                "cannot be the same person"
            )
        else:
            seen[identity_key] = role
    return errors


def _validate_markdown_twin(
    record: dict[str, Any], markdown: str, *, source: str
) -> list[str]:
    errors: list[str] = []
    incident_id = record.get("incident_id")
    if not isinstance(incident_id, str) or incident_id not in markdown:
        errors.append(f"{source}: incident ID does not match JSON record")
    if ACCEPT_CLAIM_RE.search(markdown):
        errors.append(
            f"{source}: customer-production ACCEPT is prohibited in incident Markdown"
        )
    if not re.search(r"(?m)^\| Status \| `OPEN` \|\s*$", markdown):
        errors.append(f"{source}: Markdown record status must be exactly OPEN")
    if not re.search(
        r"(?m)^\| Customer-production readiness \| `OPEN` \|\s*$", markdown
    ):
        errors.append(f"{source}: Markdown customer-production readiness must be exactly OPEN")
    if re.search(r"\b(?:MONITORING|CLOSED)\b", markdown):
        errors.append(f"{source}: Markdown contradicts the OPEN-only JSON status")
    action_rows = {
        action_id: status
        for action_id, status in re.findall(
            r"(?m)^\| (IR-ACT-\d{3}) \|.*\| `(OPEN|IN_PROGRESS|BLOCKED|COMPLETE)` \|\s*$",
            markdown,
        )
    }
    expected_action_statuses = {
        action.get("id"): action.get("status")
        for action in record.get("open_actions", [])
        if isinstance(action, dict) and isinstance(action.get("id"), str)
    }
    if action_rows != expected_action_statuses:
        errors.append(
            f"{source}: Markdown action statuses must exactly match the JSON action register"
        )
    return errors


def validate_control(control: dict[str, Any], *, source: str) -> list[str]:
    errors: list[str] = []
    if control.get("schema_version") != "1.0":
        errors.append(f"{source}: schema_version must be '1.0'")
    if control.get("control_id") != "cas-harness-incident-response":
        errors.append(f"{source}: unexpected control_id")
    claim_boundary = control.get("claim_boundary")
    if not isinstance(claim_boundary, dict):
        errors.append(f"{source}: claim_boundary must be an object")
    else:
        if claim_boundary.get("production_readiness_status") != "OPEN":
            errors.append(f"{source}: production readiness must remain OPEN")
        if claim_boundary.get("compromise_must_be_evidence_based") is not True:
            errors.append(f"{source}: compromise_must_be_evidence_based must be true")

    severities = _ids(control.get("severities"), source=source, field="severities", errors=errors)
    if severities != EXPECTED_SEVERITIES:
        errors.append(f"{source}: severity IDs must be {sorted(EXPECTED_SEVERITIES)}")

    roles = _ids(control.get("role_placeholders"), source=source, field="role_placeholders", errors=errors)
    if roles != EXPECTED_ROLES:
        errors.append(f"{source}: role IDs must be {sorted(EXPECTED_ROLES)}")

    phase_controls = _ids(
        control.get("phase_checklist"), source=source, field="phase_checklist", errors=errors
    )
    if phase_controls != EXPECTED_PHASE_CONTROLS:
        errors.append(f"{source}: phase control IDs must be {sorted(EXPECTED_PHASE_CONTROLS)}")

    provider_playbooks = control.get("provider_playbooks")
    if not isinstance(provider_playbooks, dict):
        errors.append(f"{source}: provider_playbooks must be an object")
    elif set(provider_playbooks) != EXPECTED_PROVIDERS:
        errors.append(f"{source}: provider playbooks must be {sorted(EXPECTED_PROVIDERS)}")
    else:
        for provider, playbook in provider_playbooks.items():
            if not isinstance(playbook, dict):
                errors.append(f"{source}: {provider} playbook must be an object")
                continue
            for phase in ("containment", "recovery"):
                steps = playbook.get(phase)
                if not isinstance(steps, list) or not steps or not all(isinstance(step, str) for step in steps):
                    errors.append(f"{source}: {provider}.{phase} must be a non-empty string list")

    notification_gates = _ids(
        control.get("notification_gates"), source=source, field="notification_gates", errors=errors
    )
    if notification_gates != EXPECTED_NOTIFICATION_GATES:
        errors.append(f"{source}: notification gate IDs must be {sorted(EXPECTED_NOTIFICATION_GATES)}")

    evidence_rules = control.get("evidence_rules")
    if not isinstance(evidence_rules, list) or len(evidence_rules) < 5:
        errors.append(f"{source}: at least five evidence rules are required")

    allowed_statuses = control.get("allowed_task_statuses")
    if not isinstance(allowed_statuses, list) or set(allowed_statuses) != {
        "not_started",
        "in_progress",
        "blocked",
        "complete",
        "not_applicable",
    }:
        errors.append(f"{source}: allowed_task_statuses does not match the runbook contract")
    return errors


def validate_incident_record(
    record: dict[str, Any], control: dict[str, Any], *, source: str
) -> list[str]:
    errors: list[str] = []
    extra_fields = set(record) - OPEN_ONLY_RECORD_FIELDS
    missing_pinned_fields = OPEN_ONLY_RECORD_FIELDS - set(record)
    if extra_fields or missing_pinned_fields:
        errors.append(
            f"{source}: OPEN-only incident fields must match the pinned schema; "
            f"extra={sorted(extra_fields)}, missing={sorted(missing_pinned_fields)}"
        )
    required_fields = control.get("required_incident_record_fields", [])
    if not isinstance(required_fields, list):
        errors.append(f"{source}: control required_incident_record_fields must be a list")
        required_fields = []
    for field in required_fields:
        if not isinstance(field, str) or field not in record:
            errors.append(f"{source}: missing required field {field!r}")

    if record.get("schema_version") != "1.0":
        errors.append(f"{source}: schema_version must be '1.0'")
    incident_id = record.get("incident_id")
    if not isinstance(incident_id, str) or not re.fullmatch(r"IR-\d{4}-\d{2}-\d{2}-\d{3}", incident_id):
        errors.append(f"{source}: incident_id must match IR-YYYY-MM-DD-NNN")
    if incident_id != OPEN_ONLY_INCIDENT_ID:
        errors.append(
            f"{source}: incident {incident_id!r} has no pinned immutable scope; "
            "register it in a reviewed validator change before use"
        )
    if record.get("record_type") != "operational_record_and_tabletop":
        errors.append(f"{source}: record_type must match the pinned incident scope")
    if record.get("title") != "CAS Harness production credential and hook control recovery":
        errors.append(f"{source}: title must match the pinned incident scope")
    time_control = record.get("time_control")
    if not isinstance(time_control, dict) or time_control.get("event_date_utc") != "2026-07-13":
        errors.append(f"{source}: event_date_utc must match the pinned incident scope")
    if record.get("status") != "OPEN":
        errors.append(
            f"{source}: incident status must remain OPEN; MONITORING/CLOSED transitions "
            "require the separate acceptance/closure verifier"
        )
    severity = record.get("severity")
    if not isinstance(severity, dict) or severity.get("current") not in EXPECTED_SEVERITIES:
        errors.append(f"{source}: severity.current must be one of {sorted(EXPECTED_SEVERITIES)}")
    if record.get("compromise_status") not in {"not_established", "suspected", "confirmed", "scoped_ruled_out"}:
        errors.append(f"{source}: invalid compromise_status")

    claim_boundary = record.get("claim_boundary")
    if not isinstance(claim_boundary, dict):
        errors.append(f"{source}: claim_boundary must be an object")
    else:
        if claim_boundary.get("no_claim_of_compromise") is not True:
            errors.append(f"{source}: no_claim_of_compromise must be true for this record")
        if claim_boundary.get("production_readiness_status") != "OPEN":
            errors.append(f"{source}: production_readiness_status must remain OPEN")

    roles = record.get("roles")
    if not isinstance(roles, dict):
        errors.append(f"{source}: roles must be an object")
    elif set(roles) != EXPECTED_ROLES:
        errors.append(f"{source}: record roles must be {sorted(EXPECTED_ROLES)}")
    errors.extend(_validate_distinct_assigned_roles(roles, source=source))

    systems = record.get("systems")
    if systems != PINNED_SYSTEM_SCOPE:
        errors.append(
            f"{source}: systems must exactly match the immutable scope for {OPEN_ONLY_INCIDENT_ID}"
        )

    observed_events = record.get("observed_events")
    event_ids = _ids(observed_events, source=source, field="observed_events", errors=errors)
    if event_ids != set(PINNED_EVENT_PROVIDERS):
        errors.append(
            f"{source}: observed event IDs must exactly match the immutable scope "
            f"{sorted(PINNED_EVENT_PROVIDERS)}"
        )
    events_by_id = {
        item["id"]: item
        for item in observed_events or []
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    worker = events_by_id.get("worker_token_rotation", {})
    if worker.get("old_credential_removed") is not True:
        errors.append(f"{source}: worker token rotation must retain old_credential_removed=true")
    canary_hook = events_by_id.get("canary_deploy_hook_rotation", {})
    if canary_hook.get("regenerated") is not True:
        errors.append(f"{source}: canary deploy hook must retain regenerated=true")
    blueprint_hook = events_by_id.get("blueprint_sync_hook_rotation", {})
    if (
        blueprint_hook.get("server_side_rotation_requested") is not True
        or blueprint_hook.get("rotation_pending") is not True
        or blueprint_hook.get("status") not in {"in_progress", "blocked"}
    ):
        errors.append(f"{source}: Blueprint sync-hook rotation must be requested and pending")
    aws_key = events_by_id.get("aws_production_iam_key", {})
    if (
        aws_key.get("credential_state") != "invalid"
        or aws_key.get("recovery_pending") is not True
        or aws_key.get("status") not in {"in_progress", "blocked"}
    ):
        errors.append(f"{source}: AWS production IAM key must be invalid with recovery pending")
    runpod_mfa = events_by_id.get("runpod_mfa", {})
    if runpod_mfa.get("personal_action_required") is not True or runpod_mfa.get("status") not in {
        "in_progress",
        "blocked",
    }:
        errors.append(f"{source}: RunPod MFA must remain a pending personal action")
    for event_id, event in events_by_id.items():
        expected_provider = PINNED_EVENT_PROVIDERS.get(event_id)
        if event.get("provider") != expected_provider:
            errors.append(
                f"{source}: {event_id} provider must remain pinned to {expected_provider!r}"
            )
        if event.get("fact_status") != "observed":
            errors.append(f"{source}: {event_id} must retain fact_status='observed'")
        if not isinstance(event.get("description"), str) or not event["description"].strip():
            errors.append(f"{source}: {event_id} must retain a substantive description")
        if event.get("status") not in OPEN_ONLY_EVENT_STATUSES:
            errors.append(
                f"{source}: {event_id} status must remain an unresolved OPEN-only state; "
                "completed event claims require the separate chronology/evidence verifier"
            )
        if event.get("secret_material_recorded") is not False:
            errors.append(f"{source}: {event_id} must explicitly set secret_material_recorded=false")

    checklist = record.get("response_checklist")
    if not isinstance(checklist, list):
        errors.append(f"{source}: response_checklist must be a list")
    else:
        checklist_ids: set[str] = set()
        for index, item in enumerate(checklist):
            if not isinstance(item, dict):
                errors.append(f"{source}: response_checklist[{index}] must be an object")
                continue
            control_id = item.get("control_id")
            if not isinstance(control_id, str):
                errors.append(f"{source}: response_checklist[{index}] lacks control_id")
                continue
            if control_id in checklist_ids:
                errors.append(f"{source}: duplicate response checklist control {control_id!r}")
            checklist_ids.add(control_id)
            if item.get("status") not in OPEN_ONLY_TASK_STATUSES:
                errors.append(
                    f"{source}: response checklist control {control_id!r} must remain unresolved; "
                    "complete/not_applicable claims require the separate chronology/evidence verifier"
                )
        if checklist_ids != EXPECTED_PHASE_CONTROLS:
            errors.append(f"{source}: response checklist must cover {sorted(EXPECTED_PHASE_CONTROLS)}")

    notification = record.get("notification_decision")
    if not isinstance(notification, dict) or notification.get("status") != "pending":
        errors.append(
            f"{source}: notification_decision must remain pending in OPEN-only mode"
        )

    tabletop = record.get("tabletop")
    if not isinstance(tabletop, dict):
        errors.append(f"{source}: tabletop must be an object")
    else:
        if tabletop.get("exercise_status") != "participant_run_pending":
            errors.append(
                f"{source}: tabletop must remain participant_run_pending in OPEN-only mode"
            )
        participants = tabletop.get("participants")
        if not isinstance(participants, list) or not participants:
            errors.append(f"{source}: tabletop participants must be a non-empty list")
        else:
            assigned_participants = [
                participant.strip()
                for participant in participants
                if isinstance(participant, str)
                and participant.strip()
                and not PLACEHOLDER_IDENTITY_RE.fullmatch(participant.strip())
            ]
            if len({participant.casefold() for participant in assigned_participants}) != len(
                assigned_participants
            ):
                errors.append(f"{source}: assigned tabletop participants must be distinct")

    evidence = record.get("evidence_handling")
    if not isinstance(evidence, dict):
        errors.append(f"{source}: evidence_handling must be an object")
    else:
        if evidence.get("raw_secret_material_present") is not False:
            errors.append(f"{source}: raw_secret_material_present must be false")
        if evidence.get("full_hook_urls_present") is not False:
            errors.append(f"{source}: full_hook_urls_present must be false")
        if evidence.get("worm_status") != "OPEN":
            errors.append(
                f"{source}: WORM status must remain OPEN; present/ACCEPT claims belong to the "
                "separate production acceptance verifier"
            )

    open_actions = record.get("open_actions")
    if not isinstance(open_actions, list) or not open_actions:
        errors.append(f"{source}: open_actions must be a non-empty list")
    else:
        action_ids: set[str] = set()
        for index, action in enumerate(open_actions):
            if not isinstance(action, dict):
                errors.append(f"{source}: open_actions[{index}] must be an object")
                continue
            action_id = action.get("id")
            if not isinstance(action_id, str) or not re.fullmatch(r"IR-ACT-\d{3}", action_id):
                errors.append(f"{source}: open_actions[{index}] has invalid id")
                continue
            if action_id in action_ids:
                errors.append(f"{source}: duplicate open action {action_id!r}")
            action_ids.add(action_id)
            if action.get("status") not in OPEN_ONLY_ACTION_STATUSES:
                errors.append(
                    f"{source}: {action_id} must remain unresolved; COMPLETE requires the "
                    "separate chronology/evidence verifier"
                )
            pinned_action = PINNED_ACTIONS.get(action_id)
            if pinned_action is not None and (
                action.get("action"), action.get("owner_role")
            ) != pinned_action:
                errors.append(
                    f"{source}: {action_id} action text and owner must match the immutable scope"
                )
        if action_ids != set(PINNED_ACTIONS):
            errors.append(
                f"{source}: open action IDs must exactly match the seven immutable actions "
                f"{sorted(PINNED_ACTIONS)}"
            )

    for field_error in _find_prohibited_fields(record):
        errors.append(f"{source}: {field_error}")
    for claim_error in _find_accept_claims(record):
        errors.append(f"{source}: {claim_error}")
    for state_error in _find_terminal_state_claims(record):
        errors.append(f"{source}: {state_error}")
    errors.extend(_validate_open_only_references(record, source=source))
    serialized = json.dumps(record, sort_keys=True)
    errors.extend(_scan_text_for_secret_shapes(serialized, source=source))
    return errors


def validate_package(repo_root: Path = REPO_ROOT) -> list[str]:
    errors: list[str] = []
    control_path = repo_root / CONTROL_PATH
    runbook_path = repo_root / RUNBOOK_PATH
    postmortem_path = repo_root / POSTMORTEM_PATH
    record_dir = repo_root / RECORD_DIR

    for path in (control_path, runbook_path, postmortem_path):
        if not path.is_file():
            errors.append(f"{path}: required file is missing")

    control = _load_json(control_path, errors) if control_path.is_file() else None
    if control is None:
        return errors
    errors.extend(validate_control(control, source=str(control_path)))

    json_records = sorted(record_dir.glob("IR-*.json")) if record_dir.is_dir() else []
    if not json_records:
        errors.append(f"{record_dir}: at least one incident record JSON file is required")
    for record_path in json_records:
        record = _load_json(record_path, errors)
        if record is None:
            continue
        errors.extend(validate_incident_record(record, control, source=str(record_path)))
        markdown_twin = record_path.with_suffix(".md")
        if not markdown_twin.is_file():
            errors.append(f"{markdown_twin}: markdown twin is missing")
        else:
            markdown = markdown_twin.read_text(encoding="utf-8")
            errors.extend(
                _validate_markdown_twin(record, markdown, source=str(markdown_twin))
            )
            errors.extend(_scan_text_for_secret_shapes(markdown, source=str(markdown_twin)))

    for doc_path in (runbook_path, postmortem_path):
        if doc_path.is_file():
            errors.extend(
                _scan_text_for_secret_shapes(doc_path.read_text(encoding="utf-8"), source=str(doc_path))
            )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate CAS Harness incident-response controls and non-secret records."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="Noetic Compass application root (defaults to the script's parent repository).",
    )
    args = parser.parse_args(argv)
    errors = validate_package(args.repo_root.resolve())
    if errors:
        print("CAS incident-response package validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("CAS incident-response package validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
