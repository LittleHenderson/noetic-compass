from __future__ import annotations

from dataclasses import replace
import socket
import subprocess
import urllib.request

import pytest

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes, thaw_json
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.comparison_execution_boundary import (
    BLOCKED_MISSING_EXACT_EXTERNAL_AUTHORIZATION,
    REQUIRED_MISSING_FIELDS,
    ZERO_SPEND,
    build_blocked_comparison_execution_boundary,
    build_zero_comparison_spend_record,
    load_blocked_comparison_execution_boundary,
    load_zero_comparison_spend_record,
    replay_blocked_comparison_execution_boundary,
    replay_zero_comparison_spend_record,
)
from cas_harness_v2.comparison_model_protocol import (
    BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
    CLOSED_WEIGHT,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
    OPEN_WEIGHT,
    build_comparison_model_configuration_body,
    build_comparison_model_identity,
    build_comparison_model_weight_identity_body,
)
from cas_harness_v2.comparison_shared_protocol import (
    AUTHORIZATION_BOUNDARY_MEDIA_TYPE,
    BEHAVIORAL_PROMPT_MEDIA_TYPE,
    CASE_ROLES,
    CLEAN_CONTROLS_MEDIA_TYPE,
    DETERMINISTIC_TEMPERATURE_POLICY,
    DETERMINISTIC_TEMPERATURE_VALUE,
    INDEPENDENT_EVALUATOR_MEDIA_TYPE,
    INSTRUCTION_EQUIVALENCE_MEDIA_TYPE,
    OUTPUT_SCHEMA_MEDIA_TYPE,
    PROMPT_INJECTION_TAXONOMY_MEDIA_TYPE,
    PROMPT_SOURCE_MAP_MEDIA_TYPE,
    PROVIDER_TIMESTAMP_RECORDING_REQUIRED,
    SEMANTIC_TASK_MEDIA_TYPE,
    SYSTEM_INSTRUCTION_MEDIA_TYPE,
    TIME_POLICY_MEDIA_TYPE,
    TOOL_DEFINITIONS_MEDIA_TYPE,
    build_behavioral_comparison_case,
    build_frozen_comparison_roster,
    build_shared_comparison_protocol,
)


def ref(artifact_id: str, media_type: str, body: bytes | None = None) -> ArtifactRef:
    raw = body or canonical_json_bytes({"artifact_id": artifact_id})
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=media_type,
    )


def dependencies():
    weight_bytes = build_comparison_model_weight_identity_body(
        provider="open.fixture",
        model_id="open.fixture/model-a",
        revision="v1.2.3",
    )
    open_identity = build_comparison_model_identity(
        identity_id="open-identity-a",
        access_kind=OPEN_WEIGHT,
        provider="open.fixture",
        model_id="open.fixture/model-a",
        revision="v1.2.3",
        weight_artifact_ref=ref(
            "open-weight-a",
            COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
            weight_bytes,
        ),
        weight_artifact_bytes=weight_bytes,
    )
    closed_identity = build_comparison_model_identity(
        identity_id="closed-identity-b",
        access_kind=CLOSED_WEIGHT,
        provider="closed.fixture",
        model_id="closed.fixture/model-b",
        revision="2026-08-01",
        weight_artifact_ref=None,
    )
    open_config_bytes = build_comparison_model_configuration_body(
        configuration_id="open-config-a", identity=open_identity
    )
    closed_config_bytes = build_comparison_model_configuration_body(
        configuration_id="closed-config-b", identity=closed_identity
    )
    protocol = build_shared_comparison_protocol(
        protocol_id="shared-protocol-boundary-001",
        open_identity=open_identity,
        open_configuration_ref=ref(
            "open-config-a",
            COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
            open_config_bytes,
        ),
        open_configuration_bytes=open_config_bytes,
        open_system_instruction_ref=ref(
            "open-system", SYSTEM_INSTRUCTION_MEDIA_TYPE
        ),
        open_temperature_policy=DETERMINISTIC_TEMPERATURE_POLICY,
        open_temperature_value=DETERMINISTIC_TEMPERATURE_VALUE,
        open_max_output_tokens=256,
        open_provider_timestamp_recording=PROVIDER_TIMESTAMP_RECORDING_REQUIRED,
        closed_identity=closed_identity,
        closed_configuration_ref=ref(
            "closed-config-b",
            COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
            closed_config_bytes,
        ),
        closed_configuration_bytes=closed_config_bytes,
        closed_system_instruction_ref=ref(
            "closed-system", SYSTEM_INSTRUCTION_MEDIA_TYPE
        ),
        closed_temperature_policy=DETERMINISTIC_TEMPERATURE_POLICY,
        closed_temperature_value=DETERMINISTIC_TEMPERATURE_VALUE,
        closed_max_output_tokens=256,
        closed_provider_timestamp_recording=PROVIDER_TIMESTAMP_RECORDING_REQUIRED,
        semantic_task_ref=ref("semantic-task", SEMANTIC_TASK_MEDIA_TYPE),
        injection_taxonomy_ref=ref(
            "injection-taxonomy", PROMPT_INJECTION_TAXONOMY_MEDIA_TYPE
        ),
        clean_controls_ref=ref("clean-controls", CLEAN_CONTROLS_MEDIA_TYPE),
        tool_definitions_ref=ref("tools", TOOL_DEFINITIONS_MEDIA_TYPE),
        authorization_boundary_ref=ref(
            "authorization-boundary", AUTHORIZATION_BOUNDARY_MEDIA_TYPE
        ),
        output_schema_ref=ref("output-schema", OUTPUT_SCHEMA_MEDIA_TYPE),
        instruction_equivalence_ref=ref(
            "instruction-equivalence", INSTRUCTION_EQUIVALENCE_MEDIA_TYPE
        ),
        independent_evaluator_ref=ref(
            "independent-evaluator", INDEPENDENT_EVALUATOR_MEDIA_TYPE
        ),
        time_policy_ref=ref("time-policy", TIME_POLICY_MEDIA_TYPE),
    )
    cases = tuple(
        build_behavioral_comparison_case(
            case_id=f"case-01-{index}",
            group_id="group-01",
            role=role,
            protocol=protocol,
            prompt_ref=ref(
                f"prompt-01-{index}", BEHAVIORAL_PROMPT_MEDIA_TYPE
            ),
            prompt_source_map_ref=ref(
                f"source-map-01-{index}", PROMPT_SOURCE_MAP_MEDIA_TYPE
            ),
        )
        for index, role in enumerate(CASE_ROLES, start=1)
    )
    roster = build_frozen_comparison_roster(
        roster_id="comparison-roster-boundary-001",
        protocol=protocol,
        cases=cases,
    )
    return protocol, roster


def artifacts():
    protocol, roster = dependencies()
    boundary = build_blocked_comparison_execution_boundary(
        boundary_id="comparison-boundary-001",
        program_id="open-closed-comparison-v1",
        protocol=protocol,
        roster=roster,
    )
    spend = build_zero_comparison_spend_record(
        spend_record_id="comparison-spend-zero-001",
        boundary=boundary,
        protocol=protocol,
        roster=roster,
    )
    return protocol, roster, boundary, spend


def test_blocked_boundary_and_zero_spend_are_exact_and_replayable() -> None:
    protocol, roster, boundary, spend = artifacts()
    assert boundary.evaluation_count == 3
    assert boundary.missing_fields == REQUIRED_MISSING_FIELDS
    assert boundary.payload["external_authorization"]["state"] == (
        BLOCKED_MISSING_EXACT_EXTERNAL_AUTHORIZATION
    )
    assert boundary.payload["activity"] == {
        "provider_calls": 0,
        "model_calls": 0,
        "gpu_allocations": 0,
        "runpod_runs": 0,
        "network_calls": 0,
        "spend_microusd": 0,
    }
    assert spend.payload["status"]["spend"] == ZERO_SPEND
    assert replay_blocked_comparison_execution_boundary(
        boundary, protocol=protocol, roster=roster
    ) == boundary
    assert replay_zero_comparison_spend_record(
        spend,
        boundary=boundary,
        protocol=protocol,
        roster=roster,
    ) == spend


@pytest.mark.parametrize(
    "program_id",
    (
        "stagec-calibration",
        "stagec-calibration-comparison",
        "gate5-stagec-qwen-prompt-injection-v0.1",
        "comparison-c-cal-v1",
    ),
)
def test_boundary_cannot_reuse_stagec(program_id: str) -> None:
    protocol, roster = dependencies()
    with pytest.raises(SchemaValidationError, match="Stage C"):
        build_blocked_comparison_execution_boundary(
            boundary_id="comparison-boundary-stagec",
            program_id=program_id,
            protocol=protocol,
            roster=roster,
        )


@pytest.mark.parametrize(
    "path,value",
    (
        (("activity", "model_calls"), 1),
        (("activity", "model_calls"), False),
        (("activity", "spend_microusd"), 1),
        (("activity", "network_calls"), True),
        (("execution_limits", "retries"), 1),
        (("execution_limits", "attempts_per_case"), True),
        (("external_authorization", "window_start_utc"), "2026-08-11T00:00:00Z"),
        (("external_authorization", "max_spend_microusd"), 1),
        (("external_authorization", "nonce"), "forged"),
    ),
)
def test_boundary_rejects_execution_authority_and_nonzero_activity(
    path: tuple[str, str], value: object
) -> None:
    protocol, roster, boundary, _ = artifacts()
    payload = thaw_json(boundary.payload)
    payload[path[0]][path[1]] = value
    raw = canonical_json_bytes(payload)
    with pytest.raises(SchemaValidationError):
        load_blocked_comparison_execution_boundary(
            raw,
            boundary_ref=ref(
                boundary.boundary_id,
                boundary.artifact_ref.media_type,
                raw,
            ),
            protocol=protocol,
            roster=roster,
        )


def test_boundary_rejects_missing_field_and_dependency_substitution() -> None:
    protocol, roster, boundary, _ = artifacts()
    payload = thaw_json(boundary.payload)
    payload["external_authorization"]["missing_fields"].pop()
    raw = canonical_json_bytes(payload)
    with pytest.raises(SchemaValidationError, match="blocked"):
        load_blocked_comparison_execution_boundary(
            raw,
            boundary_ref=ref(boundary.boundary_id, boundary.artifact_ref.media_type, raw),
            protocol=protocol,
            roster=roster,
        )
    other_protocol, other_roster = dependencies()
    object.__setattr__(other_roster, "roster_id", "other-roster")
    with pytest.raises(SchemaValidationError):
        replay_blocked_comparison_execution_boundary(
            boundary,
            protocol=other_protocol,
            roster=other_roster,
        )


def test_spend_record_rejects_nonzero_or_provider_receipt() -> None:
    protocol, roster, boundary, spend = artifacts()
    for field, value in (("spend_microusd", 1), ("provider_calls", 1)):
        payload = thaw_json(spend.payload)
        payload["activity"][field] = value
        raw = canonical_json_bytes(payload)
        with pytest.raises(SchemaValidationError):
            load_zero_comparison_spend_record(
                raw,
                spend_ref=ref(spend.spend_record_id, spend.artifact_ref.media_type, raw),
                boundary=boundary,
                protocol=protocol,
                roster=roster,
            )
    payload = thaw_json(spend.payload)
    payload["provider_receipt_ref"] = {
        "artifact_id": "forged-provider-receipt",
        "sha256": "A" * 64,
        "byte_length": 1,
        "media_type": "application/json",
    }
    raw = canonical_json_bytes(payload)
    with pytest.raises(SchemaValidationError):
        load_zero_comparison_spend_record(
            raw,
            spend_ref=ref(spend.spend_record_id, spend.artifact_ref.media_type, raw),
            boundary=boundary,
            protocol=protocol,
            roster=roster,
        )


def test_mutable_and_forged_projections_reject() -> None:
    protocol, roster, boundary, spend = artifacts()
    with pytest.raises(SchemaValidationError, match="frozen"):
        replay_blocked_comparison_execution_boundary(
            replace(boundary, payload=thaw_json(boundary.payload)),
            protocol=protocol,
            roster=roster,
        )
    with pytest.raises(SchemaValidationError):
        replay_blocked_comparison_execution_boundary(
            replace(boundary, evaluation_count=True),
            protocol=protocol,
            roster=roster,
        )
    forged_ref = object.__new__(ArtifactRef)
    object.__setattr__(forged_ref, "artifact_id", boundary.artifact_ref.artifact_id)
    object.__setattr__(forged_ref, "sha256", boundary.artifact_ref.sha256)
    object.__setattr__(forged_ref, "byte_length", True)
    object.__setattr__(forged_ref, "media_type", boundary.artifact_ref.media_type)
    with pytest.raises(SchemaValidationError):
        replay_zero_comparison_spend_record(
            replace(spend, boundary_ref=forged_ref),
            boundary=boundary,
            protocol=protocol,
            roster=roster,
        )


def test_builds_have_no_external_side_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args, **kwargs):
        del args, kwargs
        raise AssertionError("external call attempted")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    protocol, roster, boundary, spend = artifacts()
    assert boundary.payload["status"]["execution"] == "NOT_EXECUTED"
    assert spend.payload["activity"]["spend_microusd"] == 0
    assert protocol.artifact_ref == roster.protocol.artifact_ref
