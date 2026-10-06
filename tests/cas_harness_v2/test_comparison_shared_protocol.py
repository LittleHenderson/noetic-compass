from __future__ import annotations

import ast
from dataclasses import replace
import inspect
import json

import pytest

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes, thaw_json
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.comparison_adapters import BehavioralCaseInput
from cas_harness_v2.comparison_model_protocol import (
    BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
    BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
    CLOSED_WEIGHT,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
    OPEN_WEIGHT,
    build_comparison_model_configuration_body,
    build_comparison_model_identity,
    build_comparison_model_weight_identity_body,
)
from cas_harness_v2.comparison_shared_protocol import (
    ADVERSARIAL_PRESENT,
    AUTHORIZATION_BOUNDARY_MEDIA_TYPE,
    BEHAVIORAL_COMPARISON_CASE_SCHEMA,
    BEHAVIORAL_PROMPT_MEDIA_TYPE,
    CASE_ROLES,
    CLEAN_ABSENT,
    CLEAN_CONTROLS_MEDIA_TYPE,
    CLEAN_NULL_ABSENT,
    CLOSED,
    DETERMINISTIC_TEMPERATURE_POLICY,
    DETERMINISTIC_TEMPERATURE_VALUE,
    FROZEN_COMPARISON_ROSTER_MEDIA_TYPE,
    FROZEN_COMPARISON_ROSTER_SCHEMA,
    INDEPENDENT_EVALUATOR_MEDIA_TYPE,
    INSTRUCTION_EQUIVALENCE_MEDIA_TYPE,
    OPEN,
    OUTPUT_SCHEMA_MEDIA_TYPE,
    PROMPT_INJECTION_TAXONOMY_MEDIA_TYPE,
    PROMPT_SOURCE_MAP_MEDIA_TYPE,
    PROVIDER_TIMESTAMP_RECORDING_REQUIRED,
    SEMANTIC_TASK_MEDIA_TYPE,
    SHARED_COMPARISON_PROTOCOL_SCHEMA,
    SYSTEM_INSTRUCTION_MEDIA_TYPE,
    TIME_POLICY_MEDIA_TYPE,
    TOOL_DEFINITIONS_MEDIA_TYPE,
    BehavioralComparisonCaseArtifact,
    FrozenComparisonRosterArtifact,
    SharedComparisonProtocolArtifact,
    build_behavioral_comparison_case,
    build_frozen_comparison_roster,
    build_shared_comparison_protocol,
    load_behavioral_comparison_case,
    load_frozen_comparison_roster,
    load_shared_comparison_protocol,
    replay_behavioral_comparison_case,
    replay_frozen_comparison_roster,
    replay_shared_comparison_protocol,
)
import cas_harness_v2.comparison_shared_protocol as shared_module


def _ref(artifact_id: str, media_type: str, *, body: bytes | None = None) -> ArtifactRef:
    raw = body if body is not None else canonical_json_bytes({"artifact_id": artifact_id})
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=media_type,
    )


def _protocol_inputs() -> dict[str, object]:
    weight_body = build_comparison_model_weight_identity_body(
        provider="open.provider",
        model_id="open.provider/model-a",
        revision="v1.2.3",
    )
    weight_ref = _ref(
        "open-weight-a",
        COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
        body=weight_body,
    )
    open_identity = build_comparison_model_identity(
        identity_id="open-identity-a",
        access_kind=OPEN_WEIGHT,
        provider="open.provider",
        model_id="open.provider/model-a",
        revision="v1.2.3",
        weight_artifact_ref=weight_ref,
        weight_artifact_bytes=weight_body,
    )
    closed_identity = build_comparison_model_identity(
        identity_id="closed-identity-b",
        access_kind=CLOSED_WEIGHT,
        provider="closed.provider",
        model_id="closed.provider/model-b",
        revision="2026-08-01",
        weight_artifact_ref=None,
    )
    open_config_body = build_comparison_model_configuration_body(
        configuration_id="open-config-a", identity=open_identity
    )
    closed_config_body = build_comparison_model_configuration_body(
        configuration_id="closed-config-b", identity=closed_identity
    )
    return {
        "protocol_id": "shared-protocol-001",
        "open_identity": open_identity,
        "open_configuration_ref": _ref(
            "open-config-a",
            COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
            body=open_config_body,
        ),
        "open_configuration_bytes": open_config_body,
        "open_system_instruction_ref": _ref(
            "open-system-a", SYSTEM_INSTRUCTION_MEDIA_TYPE
        ),
        "open_temperature_policy": DETERMINISTIC_TEMPERATURE_POLICY,
        "open_temperature_value": DETERMINISTIC_TEMPERATURE_VALUE,
        "open_max_output_tokens": 512,
        "open_provider_timestamp_recording": PROVIDER_TIMESTAMP_RECORDING_REQUIRED,
        "closed_identity": closed_identity,
        "closed_configuration_ref": _ref(
            "closed-config-b",
            COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
            body=closed_config_body,
        ),
        "closed_configuration_bytes": closed_config_body,
        "closed_system_instruction_ref": _ref(
            "closed-system-b", SYSTEM_INSTRUCTION_MEDIA_TYPE
        ),
        "closed_temperature_policy": DETERMINISTIC_TEMPERATURE_POLICY,
        "closed_temperature_value": DETERMINISTIC_TEMPERATURE_VALUE,
        "closed_max_output_tokens": 512,
        "closed_provider_timestamp_recording": PROVIDER_TIMESTAMP_RECORDING_REQUIRED,
        "semantic_task_ref": _ref("semantic-task", SEMANTIC_TASK_MEDIA_TYPE),
        "injection_taxonomy_ref": _ref(
            "injection-taxonomy", PROMPT_INJECTION_TAXONOMY_MEDIA_TYPE
        ),
        "clean_controls_ref": _ref("clean-controls", CLEAN_CONTROLS_MEDIA_TYPE),
        "tool_definitions_ref": _ref("tool-definitions", TOOL_DEFINITIONS_MEDIA_TYPE),
        "authorization_boundary_ref": _ref(
            "authorization-boundary", AUTHORIZATION_BOUNDARY_MEDIA_TYPE
        ),
        "output_schema_ref": _ref("output-schema", OUTPUT_SCHEMA_MEDIA_TYPE),
        "instruction_equivalence_ref": _ref(
            "instruction-equivalence", INSTRUCTION_EQUIVALENCE_MEDIA_TYPE
        ),
        "independent_evaluator_ref": _ref(
            "independent-evaluator", INDEPENDENT_EVALUATOR_MEDIA_TYPE
        ),
        "time_policy_ref": _ref("time-policy", TIME_POLICY_MEDIA_TYPE),
    }


def _protocol() -> tuple[SharedComparisonProtocolArtifact, dict[str, object]]:
    inputs = _protocol_inputs()
    return build_shared_comparison_protocol(**inputs), inputs


def _load_protocol(
    protocol: SharedComparisonProtocolArtifact,
    inputs: dict[str, object],
    *,
    raw: bytes | None = None,
    protocol_ref: ArtifactRef | None = None,
) -> SharedComparisonProtocolArtifact:
    kwargs = dict(inputs)
    kwargs.pop("protocol_id")
    return load_shared_comparison_protocol(
        protocol.raw_bytes if raw is None else raw,
        protocol_ref=protocol.artifact_ref if protocol_ref is None else protocol_ref,
        **kwargs,
    )


def _cases(
    protocol: SharedComparisonProtocolArtifact, *, groups: int = 2
) -> tuple[BehavioralComparisonCaseArtifact, ...]:
    result: list[BehavioralComparisonCaseArtifact] = []
    for group_ordinal in range(1, groups + 1):
        for role_ordinal, role in enumerate(CASE_ROLES, start=1):
            case_id = f"case-{group_ordinal:02d}-{role_ordinal}"
            result.append(
                build_behavioral_comparison_case(
                    case_id=case_id,
                    group_id=f"group-{group_ordinal:02d}",
                    role=role,
                    protocol=protocol,
                    prompt_ref=_ref(
                        f"prompt-{group_ordinal:02d}-{role_ordinal}",
                        BEHAVIORAL_PROMPT_MEDIA_TYPE,
                    ),
                    prompt_source_map_ref=_ref(
                        f"source-map-{group_ordinal:02d}-{role_ordinal}",
                        PROMPT_SOURCE_MAP_MEDIA_TYPE,
                    ),
                )
            )
    return tuple(result)


def _mutated_ref(reference: ArtifactRef, raw: bytes) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=reference.artifact_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=reference.media_type,
    )


def test_shared_protocol_is_canonical_exact_and_replayable() -> None:
    protocol, inputs = _protocol()
    assert protocol.raw_bytes == canonical_json_bytes(thaw_json(protocol.payload))
    assert protocol.payload["schema"] == SHARED_COMPARISON_PROTOCOL_SCHEMA
    assert protocol.payload["status"] == {
        "scope": "STRUCTURE_ONLY",
        "authority": "NON_AUTHORITY",
    }
    assert protocol.payload["boundary"] == {
        "execution": "NOT_PERFORMED",
        "live_model_call": "NOT_PERFORMED",
        "provider_call": "NOT_PERFORMED",
        "network_io": "NOT_PERFORMED",
        "filesystem_io": "NOT_PERFORMED",
        "execution_authority": "NOT_GRANTED",
        "outcome": "NOT_ESTABLISHED",
    }
    assert replay_shared_comparison_protocol(protocol) == protocol
    assert _load_protocol(protocol, inputs) == protocol
    assert protocol.artifact_ref.media_type == BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE
    assert len({item.artifact_id for item in protocol.artifact_refs}) == len(
        protocol.artifact_refs
    )


def test_protocol_binds_fixed_model_order_and_all_common_roles() -> None:
    protocol, _ = _protocol()
    models = protocol.payload["models"]
    assert tuple(model["role"] for model in models) == (OPEN, CLOSED)
    assert tuple(model["access_kind"] for model in models) == (
        OPEN_WEIGHT,
        CLOSED_WEIGHT,
    )
    assert all(
        model["temperature_policy"] == DETERMINISTIC_TEMPERATURE_POLICY
        and model["temperature_value"] == DETERMINISTIC_TEMPERATURE_VALUE
        and model["provider_timestamp_recording"]
        == PROVIDER_TIMESTAMP_RECORDING_REQUIRED
        for model in models
    )
    assert set(protocol.payload["common_evidence"]) == {
        "semantic_task_ref",
        "injection_taxonomy_ref",
        "clean_controls_ref",
        "tool_definitions_ref",
        "authorization_boundary_ref",
        "output_schema_ref",
        "instruction_equivalence_ref",
        "independent_evaluator_ref",
        "time_policy_ref",
    }


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("open_temperature_policy", "PROVIDER_DEFAULT", "deterministic"),
        ("closed_temperature_value", "1", "deterministic"),
        ("closed_max_output_tokens", 513, "equal max output"),
        ("open_provider_timestamp_recording", "OPTIONAL", "timestamp recording"),
    ],
)
def test_protocol_rejects_nondeterminism_token_drift_and_missing_timestamps(
    field: str, value: object, match: str
) -> None:
    inputs = _protocol_inputs()
    inputs[field] = value
    with pytest.raises(SchemaValidationError, match=match):
        build_shared_comparison_protocol(**inputs)


def test_protocol_rejects_wrong_access_kind_and_same_model() -> None:
    inputs = _protocol_inputs()
    inputs["open_identity"] = inputs["closed_identity"]
    with pytest.raises(SchemaValidationError, match="OPEN_WEIGHT"):
        build_shared_comparison_protocol(**inputs)

    inputs = _protocol_inputs()
    open_identity = inputs["open_identity"]
    same_model_closed = build_comparison_model_identity(
        identity_id="closed-copy-of-open-model",
        access_kind=CLOSED_WEIGHT,
        provider=open_identity.provider,
        model_id=open_identity.model_id,
        revision="v2.0.0",
        weight_artifact_ref=None,
    )
    body = build_comparison_model_configuration_body(
        configuration_id="closed-copy-config", identity=same_model_closed
    )
    inputs.update(
        closed_identity=same_model_closed,
        closed_configuration_ref=_ref(
            "closed-copy-config", COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE, body=body
        ),
        closed_configuration_bytes=body,
    )
    with pytest.raises(SchemaValidationError, match="two different models"):
        build_shared_comparison_protocol(**inputs)


def test_protocol_rejects_configuration_system_and_provider_substitution() -> None:
    protocol, inputs = _protocol()
    forged = dict(inputs)
    forged["open_configuration_bytes"] = inputs["closed_configuration_bytes"]
    with pytest.raises(SchemaValidationError, match="caller bytes"):
        build_shared_comparison_protocol(**forged)

    payload = thaw_json(protocol.payload)
    payload["models"][0]["system_instruction_ref"] = payload["models"][1][
        "system_instruction_ref"
    ]
    raw = canonical_json_bytes(payload)
    with pytest.raises(SchemaValidationError, match="exact model binding"):
        _load_protocol(
            protocol,
            inputs,
            raw=raw,
            protocol_ref=_mutated_ref(protocol.artifact_ref, raw),
        )

    payload = thaw_json(protocol.payload)
    payload["models"][0]["provider"] = "substituted.provider"
    raw = canonical_json_bytes(payload)
    with pytest.raises(SchemaValidationError, match="exact model binding"):
        _load_protocol(
            protocol,
            inputs,
            raw=raw,
            protocol_ref=_mutated_ref(protocol.artifact_ref, raw),
        )


def test_protocol_rejects_role_aliases_and_global_content_aliases() -> None:
    inputs = _protocol_inputs()
    inputs["closed_system_instruction_ref"] = inputs["open_system_instruction_ref"]
    with pytest.raises(SchemaValidationError, match="distinct roles"):
        build_shared_comparison_protocol(**inputs)

    inputs = _protocol_inputs()
    semantic = inputs["semantic_task_ref"]
    inputs["time_policy_ref"] = ArtifactRef(
        artifact_id="different-time-id",
        sha256=semantic.sha256,
        byte_length=semantic.byte_length,
        media_type=TIME_POLICY_MEDIA_TYPE,
    )
    with pytest.raises(SchemaValidationError, match="content identity"):
        build_shared_comparison_protocol(**inputs)


def test_protocol_rejects_noncanonical_extra_float_and_mutable_payload() -> None:
    protocol, inputs = _protocol()
    noncanonical = b" " + protocol.raw_bytes
    with pytest.raises(SchemaValidationError, match="canonical JSON"):
        _load_protocol(
            protocol,
            inputs,
            raw=noncanonical,
            protocol_ref=_mutated_ref(protocol.artifact_ref, noncanonical),
        )
    payload = thaw_json(protocol.payload)
    payload["extra"] = "forbidden"
    raw = canonical_json_bytes(payload)
    with pytest.raises(SchemaValidationError, match="forbidden extra"):
        _load_protocol(
            protocol,
            inputs,
            raw=raw,
            protocol_ref=_mutated_ref(protocol.artifact_ref, raw),
        )
    float_raw = protocol.raw_bytes.replace(
        b'"temperature_value":"0"', b'"temperature_value":0.0', 1
    )
    with pytest.raises(SchemaValidationError, match="floating-point"):
        _load_protocol(
            protocol,
            inputs,
            raw=float_raw,
            protocol_ref=_mutated_ref(protocol.artifact_ref, float_raw),
        )
    with pytest.raises(SchemaValidationError, match="recursively frozen"):
        replay_shared_comparison_protocol(
            replace(protocol, payload=thaw_json(protocol.payload))
        )


@pytest.mark.parametrize("role", CASE_ROLES)
def test_behavioral_case_is_typed_canonical_and_replayable(role: str) -> None:
    protocol, _ = _protocol()
    case = build_behavioral_comparison_case(
        case_id=f"case-{role.lower()}",
        group_id="group-01",
        role=role,
        protocol=protocol,
        prompt_ref=_ref(f"prompt-{role.lower()}", BEHAVIORAL_PROMPT_MEDIA_TYPE),
        prompt_source_map_ref=_ref(
            f"source-{role.lower()}", PROMPT_SOURCE_MAP_MEDIA_TYPE
        ),
    )
    assert case.payload["schema"] == BEHAVIORAL_COMPARISON_CASE_SCHEMA
    assert case.payload["role"] == role
    assert case.artifact_ref.media_type == BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE
    assert replay_behavioral_comparison_case(case, protocol=protocol) == case
    assert (
        load_behavioral_comparison_case(
            case.raw_bytes,
            case_ref=case.artifact_ref,
            case_id=case.case_id,
            group_id=case.group_id,
            role=case.role,
            protocol=protocol,
            prompt_ref=case.prompt_ref,
            prompt_source_map_ref=case.prompt_source_map_ref,
        )
        == case
    )


def test_behavioral_case_rejects_bad_role_media_alias_and_body_drift() -> None:
    protocol, _ = _protocol()
    kwargs = {
        "case_id": "case-bad",
        "group_id": "group-01",
        "role": "UNKNOWN_ROLE",
        "protocol": protocol,
        "prompt_ref": _ref("prompt-bad", BEHAVIORAL_PROMPT_MEDIA_TYPE),
        "prompt_source_map_ref": _ref("source-bad", PROMPT_SOURCE_MAP_MEDIA_TYPE),
    }
    with pytest.raises(SchemaValidationError, match="must be one of"):
        build_behavioral_comparison_case(**kwargs)

    kwargs["role"] = ADVERSARIAL_PRESENT
    kwargs["prompt_ref"] = _ref("prompt-wrong-media", "text/plain")
    with pytest.raises(SchemaValidationError, match="media_type"):
        build_behavioral_comparison_case(**kwargs)

    kwargs["prompt_ref"] = _ref("same-role-id", BEHAVIORAL_PROMPT_MEDIA_TYPE)
    same = kwargs["prompt_ref"]
    kwargs["prompt_source_map_ref"] = ArtifactRef(
        artifact_id=same.artifact_id,
        sha256=same.sha256,
        byte_length=same.byte_length,
        media_type=PROMPT_SOURCE_MAP_MEDIA_TYPE,
    )
    with pytest.raises(SchemaValidationError, match="different content|distinct roles"):
        build_behavioral_comparison_case(**kwargs)

    case = _cases(protocol, groups=1)[0]
    payload = thaw_json(case.payload)
    payload["group_id"] = "substituted-group"
    raw = canonical_json_bytes(payload)
    with pytest.raises(SchemaValidationError, match="caller-bound projection"):
        load_behavioral_comparison_case(
            raw,
            case_ref=_mutated_ref(case.artifact_ref, raw),
            case_id=case.case_id,
            group_id=case.group_id,
            role=case.role,
            protocol=protocol,
            prompt_ref=case.prompt_ref,
            prompt_source_map_ref=case.prompt_source_map_ref,
        )


def test_behavioral_case_rejects_transitive_id_collision_and_mutable_payload() -> None:
    protocol, _ = _protocol()
    weight_ref = protocol.open_identity.weight_artifact_ref
    assert weight_ref is not None
    conflicting_prompt = _ref(weight_ref.artifact_id, BEHAVIORAL_PROMPT_MEDIA_TYPE)
    with pytest.raises(SchemaValidationError, match="different content"):
        build_behavioral_comparison_case(
            case_id="case-transitive-collision",
            group_id="group-01",
            role=ADVERSARIAL_PRESENT,
            protocol=protocol,
            prompt_ref=conflicting_prompt,
            prompt_source_map_ref=_ref("source-unique", PROMPT_SOURCE_MAP_MEDIA_TYPE),
        )
    case = _cases(protocol, groups=1)[0]
    with pytest.raises(SchemaValidationError, match="recursively frozen"):
        replay_behavioral_comparison_case(
            replace(case, payload=thaw_json(case.payload)), protocol=protocol
        )


def test_frozen_roster_is_matched_contiguous_canonical_and_replayable() -> None:
    protocol, _ = _protocol()
    cases = _cases(protocol)
    roster = build_frozen_comparison_roster(
        roster_id="roster-001", protocol=protocol, cases=cases
    )
    assert roster.payload["schema"] == FROZEN_COMPARISON_ROSTER_SCHEMA
    assert roster.artifact_ref.media_type == FROZEN_COMPARISON_ROSTER_MEDIA_TYPE
    assert tuple(group.group_ordinal for group in roster.groups) == (1, 2)
    assert tuple(group.group_id for group in roster.groups) == ("group-01", "group-02")
    assert tuple(
        row["execution_ordinal"]
        for group in roster.payload["groups"]
        for row in group["cases"]
    ) == (1, 2, 3, 4, 5, 6)
    assert replay_frozen_comparison_roster(roster) == roster
    assert (
        load_frozen_comparison_roster(
            roster.raw_bytes,
            roster_ref=roster.artifact_ref,
            protocol=protocol,
            cases=cases,
        )
        == roster
    )


def test_adapter_cases_are_ordered_label_free_and_model_specific() -> None:
    protocol, _ = _protocol()
    roster = build_frozen_comparison_roster(
        roster_id="roster-adapter", protocol=protocol, cases=_cases(protocol)
    )
    open_rows = roster.adapter_cases(OPEN)
    closed_rows = roster.adapter_cases(CLOSED)
    assert all(type(row) is BehavioralCaseInput for row in open_rows + closed_rows)
    assert tuple(row.execution_ordinal for row in open_rows) == tuple(range(1, 7))
    assert tuple(row.case_ref for row in open_rows) == tuple(
        row.case_ref for row in closed_rows
    )
    assert {row.configuration_ref for row in open_rows} == {
        protocol.open_configuration_ref
    }
    assert {row.configuration_ref for row in closed_rows} == {
        protocol.closed_configuration_ref
    }
    assert all(row.protocol_ref == protocol.artifact_ref for row in open_rows)
    assert "role" not in BehavioralCaseInput.__dataclass_fields__
    assert "label" not in BehavioralCaseInput.__dataclass_fields__
    with pytest.raises(SchemaValidationError, match="must be one of"):
        roster.adapter_cases("ADVERSARIAL_PRESENT")


@pytest.mark.parametrize(
    "transform",
    [
        lambda cases: (),
        lambda cases: cases[:-1],
        lambda cases: (cases[1], cases[0], *cases[2:]),
        lambda cases: (cases[0], cases[1], cases[2], cases[0], cases[1], cases[2]),
        lambda cases: (cases[0], cases[1], cases[3], cases[2], *cases[4:]),
    ],
)
def test_roster_rejects_empty_missing_duplicate_out_of_order_or_split_cases(
    transform,
) -> None:
    protocol, _ = _protocol()
    cases = _cases(protocol)
    with pytest.raises(SchemaValidationError):
        build_frozen_comparison_roster(
            roster_id="roster-invalid", protocol=protocol, cases=transform(cases)
        )


def test_roster_rejects_execution_group_case_drift_and_mutable_forgery() -> None:
    protocol, _ = _protocol()
    cases = _cases(protocol)
    roster = build_frozen_comparison_roster(
        roster_id="roster-drift", protocol=protocol, cases=cases
    )
    for mutate in (
        lambda value: value["groups"][0].__setitem__("group_ordinal", 2),
        lambda value: value["groups"][0]["cases"][0].__setitem__(
            "execution_ordinal", 9
        ),
        lambda value: value["groups"][0]["cases"][0]["case_ref"].__setitem__(
            "artifact_id", "substituted-case"
        ),
    ):
        payload = thaw_json(roster.payload)
        mutate(payload)
        raw = canonical_json_bytes(payload)
        with pytest.raises(SchemaValidationError, match="contiguous caller-bound"):
            load_frozen_comparison_roster(
                raw,
                roster_ref=_mutated_ref(roster.artifact_ref, raw),
                protocol=protocol,
                cases=cases,
            )
    with pytest.raises(SchemaValidationError, match="recursively frozen"):
        replay_frozen_comparison_roster(
            replace(roster, payload=thaw_json(roster.payload))
        )
    with pytest.raises(SchemaValidationError, match="fresh exact-byte replay"):
        replay_frozen_comparison_roster(
            replace(roster, artifact_refs=roster.artifact_refs[:-1])
        )


def test_roster_rejects_global_case_content_alias() -> None:
    protocol, _ = _protocol()
    cases = list(_cases(protocol, groups=1))
    original = cases[1]
    forged_ref = ArtifactRef(
        artifact_id="forged-case-owner",
        sha256=original.sha256,
        byte_length=original.byte_length,
        media_type=BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
    )
    with pytest.raises(SchemaValidationError, match="case_id differs"):
        load_behavioral_comparison_case(
            original.raw_bytes,
            case_ref=forged_ref,
            case_id=original.case_id,
            group_id=original.group_id,
            role=original.role,
            protocol=protocol,
            prompt_ref=original.prompt_ref,
            prompt_source_map_ref=original.prompt_source_map_ref,
        )


def test_public_exports_are_literal_unique_and_module_has_no_io_surface() -> None:
    source = inspect.getsource(shared_module)
    tree = ast.parse(source)
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
    ]
    assert len(assignments) == 1
    exported = ast.literal_eval(assignments[0].value)
    assert type(exported) is tuple
    assert len(exported) == len(set(exported))
    assert exported == shared_module.__all__
    forbidden_import_roots = {
        "asyncio", "http", "os", "pathlib", "requests", "socket", "subprocess", "urllib"
    }
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert forbidden_import_roots.isdisjoint(imported_roots)
    assert "open(" not in source
    assert "requests." not in source
    assert "subprocess." not in source


def test_schema_and_media_literals_are_exact() -> None:
    assert SHARED_COMPARISON_PROTOCOL_SCHEMA == (
        "cas_harness_v2.shared_comparison_protocol.v1"
    )
    assert BEHAVIORAL_COMPARISON_CASE_SCHEMA == (
        "cas_harness_v2.behavioral_comparison_case.v1"
    )
    assert FROZEN_COMPARISON_ROSTER_SCHEMA == (
        "cas_harness_v2.frozen_comparison_roster.v1"
    )
    assert FROZEN_COMPARISON_ROSTER_MEDIA_TYPE == (
        "application/vnd.cas-harness.frozen-comparison-roster-v1+json"
    )
    assert CASE_ROLES == (
        ADVERSARIAL_PRESENT,
        CLEAN_ABSENT,
        CLEAN_NULL_ABSENT,
    )
    assert inspect.signature(FrozenComparisonRosterArtifact.adapter_cases).return_annotation
