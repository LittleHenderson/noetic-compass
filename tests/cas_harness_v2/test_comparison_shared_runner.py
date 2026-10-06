from __future__ import annotations

import ast
from dataclasses import dataclass, replace
import inspect
import socket
import subprocess
import urllib.request

import pytest

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes, thaw_json
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.comparison_adapters import (
    BehavioralCaseInput,
    ReplayBehavioralAdapter,
    build_replay_behavioral_adapter,
    build_unavailable_behavioral_adapter,
)
from cas_harness_v2.comparison_model_protocol import (
    ACTIVATION_CAPTURE,
    BEHAVIOR_GENERATION,
    CLOSED_WEIGHT,
    COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
    HIDDEN_STATE_OBSERVATION,
    LOGPROB_OBSERVATION,
    OBSERVED,
    OPEN_WEIGHT,
    RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
    RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
    STEERING_INTERVENTION,
    SUPPORTED_WITH_EVIDENCE,
    TOOL_CALL_OBSERVATION,
    UNAVAILABLE_BY_ACCESS_MODEL,
    UNKNOWN_UNVERIFIED,
    build_behavioral_observation,
    build_comparison_capability_evidence_body,
    build_comparison_model_capabilities,
    build_comparison_model_configuration_body,
    build_comparison_model_identity,
    build_comparison_model_weight_identity_body,
)
from cas_harness_v2.comparison_shared_protocol import (
    AUTHORIZATION_BOUNDARY_MEDIA_TYPE,
    BEHAVIORAL_PROMPT_MEDIA_TYPE,
    CASE_ROLES,
    CLEAN_CONTROLS_MEDIA_TYPE,
    CLOSED,
    DETERMINISTIC_TEMPERATURE_POLICY,
    DETERMINISTIC_TEMPERATURE_VALUE,
    INDEPENDENT_EVALUATOR_MEDIA_TYPE,
    INSTRUCTION_EQUIVALENCE_MEDIA_TYPE,
    OPEN,
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
from cas_harness_v2.comparison_shared_runner import (
    SHARED_BEHAVIORAL_REPLAY_MEDIA_TYPE,
    SHARED_BEHAVIORAL_REPLAY_SCHEMA,
    SharedBehavioralReplayArtifact,
    SharedBehavioralReplayFailure,
    build_shared_behavioral_replay_artifact,
    load_shared_behavioral_replay_artifact,
    replay_shared_behavioral_replay_artifact,
    run_shared_behavioral_replay,
)
import cas_harness_v2.comparison_shared_runner as runner_module


def _ref(artifact_id: str, media_type: str, *, body: bytes | None = None) -> ArtifactRef:
    raw = body if body is not None else canonical_json_bytes({"artifact_id": artifact_id})
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=media_type,
    )


def _capabilities(
    *,
    prefix: str,
    identity,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
) -> object:
    closed = identity.access_kind == CLOSED_WEIGHT
    statuses = {
        BEHAVIOR_GENERATION: SUPPORTED_WITH_EVIDENCE,
        TOOL_CALL_OBSERVATION: SUPPORTED_WITH_EVIDENCE,
        LOGPROB_OBSERVATION: (
            UNAVAILABLE_BY_ACCESS_MODEL if closed else UNKNOWN_UNVERIFIED
        ),
        HIDDEN_STATE_OBSERVATION: (
            UNAVAILABLE_BY_ACCESS_MODEL if closed else UNKNOWN_UNVERIFIED
        ),
        ACTIVATION_CAPTURE: (
            UNAVAILABLE_BY_ACCESS_MODEL if closed else UNKNOWN_UNVERIFIED
        ),
        STEERING_INTERVENTION: (
            UNAVAILABLE_BY_ACCESS_MODEL if closed else UNKNOWN_UNVERIFIED
        ),
    }
    evidence_ids = {
        BEHAVIOR_GENERATION: f"{prefix}-behavior-evidence",
        TOOL_CALL_OBSERVATION: f"{prefix}-tool-evidence",
    }
    evidence_bytes = {
        name: (
            build_comparison_capability_evidence_body(
                evidence_id=evidence_ids[name],
                capability_name=name,
                identity=identity,
                configuration_ref=configuration_ref,
            )
            if name in evidence_ids
            else None
        )
        for name in statuses
    }
    evidence_refs = {
        name: (
            _ref(
                evidence_ids[name],
                COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
                body=evidence_bytes[name],
            )
            if name in evidence_ids
            else None
        )
        for name in statuses
    }
    return build_comparison_model_capabilities(
        capabilities_id=f"{prefix}-capabilities",
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_statuses=statuses,
        capability_evidence_refs=evidence_refs,
        capability_evidence_bytes=evidence_bytes,
    )


@dataclass(frozen=True)
class Fixture:
    protocol: object
    roster: object
    open_capabilities: object
    closed_capabilities: object
    open_cases: tuple[BehavioralCaseInput, ...]
    closed_cases: tuple[BehavioralCaseInput, ...]
    open_observations: tuple[object, ...]
    closed_observations: tuple[object, ...]

    def adapters(self) -> tuple[ReplayBehavioralAdapter, ReplayBehavioralAdapter]:
        return (
            build_replay_behavioral_adapter(
                identity=self.protocol.open_identity,
                capabilities=self.open_capabilities,
                configuration_ref=self.protocol.open_configuration_ref,
                protocol_ref=self.protocol.artifact_ref,
                ordered_cases=self.open_cases,
                observations=self.open_observations,
            ),
            build_replay_behavioral_adapter(
                identity=self.protocol.closed_identity,
                capabilities=self.closed_capabilities,
                configuration_ref=self.protocol.closed_configuration_ref,
                protocol_ref=self.protocol.artifact_ref,
                ordered_cases=self.closed_cases,
                observations=self.closed_observations,
            ),
        )

    def run(self) -> SharedBehavioralReplayArtifact:
        open_adapter, closed_adapter = self.adapters()
        return run_shared_behavioral_replay(
            replay_id="shared-replay-001",
            protocol=self.protocol,
            roster=self.roster,
            open_capabilities=self.open_capabilities,
            closed_capabilities=self.closed_capabilities,
            open_adapter=open_adapter,
            closed_adapter=closed_adapter,
            open_cases=self.open_cases,
            closed_cases=self.closed_cases,
        )


@pytest.fixture
def fx() -> Fixture:
    weight_body = build_comparison_model_weight_identity_body(
        provider="open.provider",
        model_id="open.provider/model-a",
        revision="v1.2.3",
    )
    weight_ref = _ref(
        "runner-open-weight",
        COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
        body=weight_body,
    )
    open_identity = build_comparison_model_identity(
        identity_id="runner-open-identity",
        access_kind=OPEN_WEIGHT,
        provider="open.provider",
        model_id="open.provider/model-a",
        revision="v1.2.3",
        weight_artifact_ref=weight_ref,
        weight_artifact_bytes=weight_body,
    )
    closed_identity = build_comparison_model_identity(
        identity_id="runner-closed-identity",
        access_kind=CLOSED_WEIGHT,
        provider="closed.provider",
        model_id="closed.provider/model-b",
        revision="2026-08-01",
        weight_artifact_ref=None,
    )
    open_config_bytes = build_comparison_model_configuration_body(
        configuration_id="runner-open-config", identity=open_identity
    )
    closed_config_bytes = build_comparison_model_configuration_body(
        configuration_id="runner-closed-config", identity=closed_identity
    )
    open_config_ref = _ref(
        "runner-open-config",
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        body=open_config_bytes,
    )
    closed_config_ref = _ref(
        "runner-closed-config",
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        body=closed_config_bytes,
    )
    protocol = build_shared_comparison_protocol(
        protocol_id="runner-shared-protocol",
        open_identity=open_identity,
        open_configuration_ref=open_config_ref,
        open_configuration_bytes=open_config_bytes,
        open_system_instruction_ref=_ref(
            "runner-open-system", SYSTEM_INSTRUCTION_MEDIA_TYPE
        ),
        open_temperature_policy=DETERMINISTIC_TEMPERATURE_POLICY,
        open_temperature_value=DETERMINISTIC_TEMPERATURE_VALUE,
        open_max_output_tokens=512,
        open_provider_timestamp_recording=PROVIDER_TIMESTAMP_RECORDING_REQUIRED,
        closed_identity=closed_identity,
        closed_configuration_ref=closed_config_ref,
        closed_configuration_bytes=closed_config_bytes,
        closed_system_instruction_ref=_ref(
            "runner-closed-system", SYSTEM_INSTRUCTION_MEDIA_TYPE
        ),
        closed_temperature_policy=DETERMINISTIC_TEMPERATURE_POLICY,
        closed_temperature_value=DETERMINISTIC_TEMPERATURE_VALUE,
        closed_max_output_tokens=512,
        closed_provider_timestamp_recording=PROVIDER_TIMESTAMP_RECORDING_REQUIRED,
        semantic_task_ref=_ref("runner-semantic", SEMANTIC_TASK_MEDIA_TYPE),
        injection_taxonomy_ref=_ref(
            "runner-taxonomy", PROMPT_INJECTION_TAXONOMY_MEDIA_TYPE
        ),
        clean_controls_ref=_ref("runner-controls", CLEAN_CONTROLS_MEDIA_TYPE),
        tool_definitions_ref=_ref("runner-tools", TOOL_DEFINITIONS_MEDIA_TYPE),
        authorization_boundary_ref=_ref(
            "runner-auth-boundary", AUTHORIZATION_BOUNDARY_MEDIA_TYPE
        ),
        output_schema_ref=_ref("runner-output-schema", OUTPUT_SCHEMA_MEDIA_TYPE),
        instruction_equivalence_ref=_ref(
            "runner-instruction-equivalence", INSTRUCTION_EQUIVALENCE_MEDIA_TYPE
        ),
        independent_evaluator_ref=_ref(
            "runner-independent-evaluator", INDEPENDENT_EVALUATOR_MEDIA_TYPE
        ),
        time_policy_ref=_ref("runner-time-policy", TIME_POLICY_MEDIA_TYPE),
    )
    case_artifacts = tuple(
        build_behavioral_comparison_case(
            case_id=f"runner-case-{group_ordinal:02d}-{role_ordinal}",
            group_id=f"runner-group-{group_ordinal:02d}",
            role=role,
            protocol=protocol,
            prompt_ref=_ref(
                f"runner-prompt-{group_ordinal:02d}-{role_ordinal}",
                BEHAVIORAL_PROMPT_MEDIA_TYPE,
            ),
            prompt_source_map_ref=_ref(
                f"runner-source-map-{group_ordinal:02d}-{role_ordinal}",
                PROMPT_SOURCE_MAP_MEDIA_TYPE,
            ),
        )
        for group_ordinal in (1, 2)
        for role_ordinal, role in enumerate(CASE_ROLES, start=1)
    )
    roster = build_frozen_comparison_roster(
        roster_id="runner-roster", protocol=protocol, cases=case_artifacts
    )
    open_capabilities = _capabilities(
        prefix="runner-open",
        identity=open_identity,
        configuration_ref=open_config_ref,
        configuration_bytes=open_config_bytes,
    )
    closed_capabilities = _capabilities(
        prefix="runner-closed",
        identity=closed_identity,
        configuration_ref=closed_config_ref,
        configuration_bytes=closed_config_bytes,
    )
    open_cases = roster.adapter_cases(OPEN)
    closed_cases = roster.adapter_cases(CLOSED)

    def observations(role: str, cases: tuple[BehavioralCaseInput, ...]) -> tuple[object, ...]:
        if role == OPEN:
            identity = open_identity
            configuration_ref = open_config_ref
            configuration_bytes = open_config_bytes
        else:
            identity = closed_identity
            configuration_ref = closed_config_ref
            configuration_bytes = closed_config_bytes
        return tuple(
            build_behavioral_observation(
                observation_id=f"runner-{role.lower()}-observation-{case.execution_ordinal:03d}",
                identity=identity,
                configuration_ref=configuration_ref,
                configuration_bytes=configuration_bytes,
                protocol_ref=protocol.artifact_ref,
                case_id=case.case_id,
                case_ref=case.case_ref,
                observation_status=OBSERVED,
                raw_response_ref=_ref(
                    f"runner-{role.lower()}-response-{case.execution_ordinal:03d}",
                    RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
                ),
                raw_tool_calls_ref=_ref(
                    f"runner-{role.lower()}-tools-{case.execution_ordinal:03d}",
                    RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
                ),
                unavailable_reason=None,
            )
            for case in cases
        )

    return Fixture(
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        open_cases=open_cases,
        closed_cases=closed_cases,
        open_observations=observations(OPEN, open_cases),
        closed_observations=observations(CLOSED, closed_cases),
    )


def _build_direct(fx: Fixture, **overrides: object) -> SharedBehavioralReplayArtifact:
    kwargs = {
        "replay_id": "shared-replay-direct",
        "protocol": fx.protocol,
        "roster": fx.roster,
        "open_capabilities": fx.open_capabilities,
        "closed_capabilities": fx.closed_capabilities,
        "open_observations": fx.open_observations,
        "closed_observations": fx.closed_observations,
    }
    kwargs.update(overrides)
    return build_shared_behavioral_replay_artifact(**kwargs)


def _mutated_ref(reference: ArtifactRef, raw: bytes) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=reference.artifact_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=reference.media_type,
    )


def test_runner_consumes_both_complete_rosters_and_returns_exact_pairs(fx: Fixture) -> None:
    open_adapter, closed_adapter = fx.adapters()
    artifact = run_shared_behavioral_replay(
        replay_id="shared-replay-success",
        protocol=fx.protocol,
        roster=fx.roster,
        open_capabilities=fx.open_capabilities,
        closed_capabilities=fx.closed_capabilities,
        open_adapter=open_adapter,
        closed_adapter=closed_adapter,
        open_cases=fx.open_cases,
        closed_cases=fx.closed_cases,
    )
    assert open_adapter.complete and closed_adapter.complete
    assert open_adapter.consumed_case_count == len(fx.roster.cases)
    assert closed_adapter.consumed_case_count == len(fx.roster.cases)
    assert tuple(pair.execution_ordinal for pair in artifact.pairs) == tuple(
        range(1, len(fx.roster.cases) + 1)
    )
    assert tuple(pair.case_ref for pair in artifact.pairs) == tuple(
        case.artifact_ref for case in fx.roster.cases
    )
    assert tuple(pair.open_observation for pair in artifact.pairs) == fx.open_observations
    assert tuple(pair.closed_observation for pair in artifact.pairs) == fx.closed_observations


def test_artifact_is_canonical_replayable_non_authority_and_zero_call(fx: Fixture) -> None:
    artifact = _build_direct(fx)
    assert artifact.raw_bytes == canonical_json_bytes(thaw_json(artifact.payload))
    assert artifact.payload["schema"] == SHARED_BEHAVIORAL_REPLAY_SCHEMA
    assert artifact.artifact_ref.media_type == SHARED_BEHAVIORAL_REPLAY_MEDIA_TYPE
    assert artifact.payload["status"] == {
        "scope": "STRUCTURE_ONLY",
        "authority": "NON_AUTHORITY",
    }
    assert artifact.payload["boundary"] == {
        "local_replay": "PERFORMED",
        "live_execution": "NOT_PERFORMED",
        "execution_authority": "NOT_GRANTED",
        "provider_calls": 0,
        "model_calls": 0,
        "network_calls": 0,
        "filesystem_calls": 0,
        "spend_actions": 0,
    }
    assert replay_shared_behavioral_replay_artifact(artifact) == artifact
    assert (
        load_shared_behavioral_replay_artifact(
            artifact.raw_bytes,
            replay_ref=artifact.artifact_ref,
            protocol=fx.protocol,
            roster=fx.roster,
            open_capabilities=fx.open_capabilities,
            closed_capabilities=fx.closed_capabilities,
            open_observations=fx.open_observations,
            closed_observations=fx.closed_observations,
        )
        == artifact
    )


def test_artifact_preserves_every_raw_response_and_tool_reference(fx: Fixture) -> None:
    artifact = _build_direct(fx)
    for pair, open_original, closed_original in zip(
        artifact.pairs,
        fx.open_observations,
        fx.closed_observations,
        strict=True,
    ):
        assert pair.open_observation.raw_response_ref == open_original.raw_response_ref
        assert pair.open_observation.raw_tool_calls_ref == open_original.raw_tool_calls_ref
        assert pair.closed_observation.raw_response_ref == closed_original.raw_response_ref
        assert pair.closed_observation.raw_tool_calls_ref == closed_original.raw_tool_calls_ref


def test_artifact_contains_no_verdict_label_or_composite_metric(fx: Fixture) -> None:
    artifact = _build_direct(fx)
    keys: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            keys.update(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(thaw_json(artifact.payload))
    assert {"verdict", "label", "outcome", "composite_metric"}.isdisjoint(keys)


def test_runner_rejects_unavailable_arbitrary_and_reused_adapters(fx: Fixture) -> None:
    open_adapter, closed_adapter = fx.adapters()
    unavailable = build_unavailable_behavioral_adapter(
        identity=fx.protocol.open_identity,
        capabilities=fx.open_capabilities,
        configuration_ref=fx.protocol.open_configuration_ref,
        protocol_ref=fx.protocol.artifact_ref,
        reason="LOCAL_REPLAY_UNAVAILABLE",
    )
    base = {
        "replay_id": "runner-reject-adapter",
        "protocol": fx.protocol,
        "roster": fx.roster,
        "open_capabilities": fx.open_capabilities,
        "closed_capabilities": fx.closed_capabilities,
        "open_adapter": open_adapter,
        "closed_adapter": closed_adapter,
        "open_cases": fx.open_cases,
        "closed_cases": fx.closed_cases,
    }
    for candidate in (unavailable, object()):
        with pytest.raises(SchemaValidationError, match="ReplayBehavioralAdapter"):
            run_shared_behavioral_replay(**{**base, "open_adapter": candidate})
    with pytest.raises(SchemaValidationError, match="two distinct"):
        run_shared_behavioral_replay(
            **{**base, "closed_adapter": open_adapter}
        )


@pytest.mark.parametrize(
    "transform",
    [
        lambda rows: rows[:-1],
        lambda rows: (rows[0], rows[0], *rows[2:]),
        lambda rows: (rows[1], rows[0], *rows[2:]),
        lambda rows: tuple(reversed(rows)),
    ],
)
def test_runner_rejects_missing_duplicate_or_out_of_order_cases(
    fx: Fixture, transform
) -> None:
    open_adapter, closed_adapter = fx.adapters()
    with pytest.raises(SchemaValidationError, match="complete|missing|duplicated|order"):
        run_shared_behavioral_replay(
            replay_id="runner-bad-cases",
            protocol=fx.protocol,
            roster=fx.roster,
            open_capabilities=fx.open_capabilities,
            closed_capabilities=fx.closed_capabilities,
            open_adapter=open_adapter,
            closed_adapter=closed_adapter,
            open_cases=transform(fx.open_cases),
            closed_cases=fx.closed_cases,
        )


def test_runner_rejects_fresh_equal_but_not_adapter_owned_cases(fx: Fixture) -> None:
    open_adapter, closed_adapter = fx.adapters()
    fresh_open_cases = fx.roster.adapter_cases(OPEN)
    assert fresh_open_cases == fx.open_cases
    assert fresh_open_cases[0] is not fx.open_cases[0]
    with pytest.raises(
        SharedBehavioralReplayFailure,
        match="LOCAL_REPLAY_FAILURE:OPEN:NO_ARTIFACT",
    ):
        run_shared_behavioral_replay(
            replay_id="runner-fresh-cases",
            protocol=fx.protocol,
            roster=fx.roster,
            open_capabilities=fx.open_capabilities,
            closed_capabilities=fx.closed_capabilities,
            open_adapter=open_adapter,
            closed_adapter=closed_adapter,
            open_cases=fresh_open_cases,
            closed_cases=fx.closed_cases,
        )
    assert open_adapter.consumed_case_count == 0
    assert closed_adapter.consumed_case_count == 0


def test_runner_rejects_partial_and_previously_consumed_adapters(fx: Fixture) -> None:
    open_adapter, closed_adapter = fx.adapters()
    open_adapter.observe(fx.open_cases[0])
    with pytest.raises(SchemaValidationError, match="untouched"):
        run_shared_behavioral_replay(
            replay_id="runner-partial",
            protocol=fx.protocol,
            roster=fx.roster,
            open_capabilities=fx.open_capabilities,
            closed_capabilities=fx.closed_capabilities,
            open_adapter=open_adapter,
            closed_adapter=closed_adapter,
            open_cases=fx.open_cases,
            closed_cases=fx.closed_cases,
        )
    open_adapter, closed_adapter = fx.adapters()
    open_adapter.replay_all(fx.open_cases)
    with pytest.raises(SchemaValidationError, match="untouched"):
        run_shared_behavioral_replay(
            replay_id="runner-consumed",
            protocol=fx.protocol,
            roster=fx.roster,
            open_capabilities=fx.open_capabilities,
            closed_capabilities=fx.closed_capabilities,
            open_adapter=open_adapter,
            closed_adapter=closed_adapter,
            open_cases=fx.open_cases,
            closed_cases=fx.closed_cases,
        )


def test_runner_rejects_adapter_count_drift_and_owner_alias_before_consumption(
    fx: Fixture,
) -> None:
    short_open_adapter = build_replay_behavioral_adapter(
        identity=fx.protocol.open_identity,
        capabilities=fx.open_capabilities,
        configuration_ref=fx.protocol.open_configuration_ref,
        protocol_ref=fx.protocol.artifact_ref,
        ordered_cases=fx.open_cases[:3],
        observations=fx.open_observations[:3],
    )
    _, closed_adapter = fx.adapters()
    with pytest.raises(SchemaValidationError, match="complete roster"):
        run_shared_behavioral_replay(
            replay_id="runner-count-drift",
            protocol=fx.protocol,
            roster=fx.roster,
            open_capabilities=fx.open_capabilities,
            closed_capabilities=fx.closed_capabilities,
            open_adapter=short_open_adapter,
            closed_adapter=closed_adapter,
            open_cases=fx.open_cases,
            closed_cases=fx.closed_cases,
        )
    assert short_open_adapter.consumed_case_count == 0
    assert closed_adapter.consumed_case_count == 0

    open_adapter, closed_adapter = fx.adapters()
    with pytest.raises(SchemaValidationError, match="replay_id collides"):
        run_shared_behavioral_replay(
            replay_id=fx.protocol.protocol_id,
            protocol=fx.protocol,
            roster=fx.roster,
            open_capabilities=fx.open_capabilities,
            closed_capabilities=fx.closed_capabilities,
            open_adapter=open_adapter,
            closed_adapter=closed_adapter,
            open_cases=fx.open_cases,
            closed_cases=fx.closed_cases,
        )
    assert open_adapter.consumed_case_count == 0
    assert closed_adapter.consumed_case_count == 0


def test_build_rejects_cross_model_observation_mixing_and_count_drift(fx: Fixture) -> None:
    with pytest.raises(SchemaValidationError, match="OPEN observation fails"):
        _build_direct(
            fx,
            open_observations=fx.closed_observations,
            closed_observations=fx.open_observations,
        )
    with pytest.raises(SchemaValidationError, match="complete roster count"):
        _build_direct(fx, closed_observations=fx.closed_observations[:-1])


def test_build_rejects_capability_model_revision_and_configuration_substitution(
    fx: Fixture,
) -> None:
    with pytest.raises(SchemaValidationError, match="capabilities fail exact replay"):
        _build_direct(
            fx,
            open_capabilities=fx.closed_capabilities,
            closed_capabilities=fx.open_capabilities,
        )
    forged = replace(
        fx.open_capabilities,
        configuration_ref=fx.protocol.closed_configuration_ref,
    )
    with pytest.raises(SchemaValidationError, match="capabilities fail exact replay"):
        _build_direct(fx, open_capabilities=forged)


def test_runner_rejects_different_valid_capabilities_than_adapter_seal(
    fx: Fixture,
) -> None:
    alternate = _capabilities(
        prefix="runner-open-alternate",
        identity=fx.protocol.open_identity,
        configuration_ref=fx.protocol.open_configuration_ref,
        configuration_bytes=fx.protocol.open_configuration_bytes,
    )
    open_adapter, closed_adapter = fx.adapters()
    with pytest.raises(SchemaValidationError, match="exact identity, capabilities"):
        run_shared_behavioral_replay(
            replay_id="runner-capability-binding-repro",
            protocol=fx.protocol,
            roster=fx.roster,
            open_capabilities=alternate,
            closed_capabilities=fx.closed_capabilities,
            open_adapter=open_adapter,
            closed_adapter=closed_adapter,
            open_cases=fx.open_cases,
            closed_cases=fx.closed_cases,
        )
    assert open_adapter.consumed_case_count == 0
    assert closed_adapter.consumed_case_count == 0


def test_build_rejects_global_artifact_id_and_content_aliases(fx: Fixture) -> None:
    first_open = fx.open_observations[0]
    first_closed = fx.closed_observations[0]
    conflicting_raw = _ref(
        first_open.raw_response_ref.artifact_id,
        RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
        body=b"different closed response",
    )
    forged_closed = build_behavioral_observation(
        observation_id=first_closed.observation_id,
        identity=fx.protocol.closed_identity,
        configuration_ref=fx.protocol.closed_configuration_ref,
        configuration_bytes=fx.protocol.closed_configuration_bytes,
        protocol_ref=fx.protocol.artifact_ref,
        case_id=fx.closed_cases[0].case_id,
        case_ref=fx.closed_cases[0].case_ref,
        observation_status=OBSERVED,
        raw_response_ref=conflicting_raw,
        raw_tool_calls_ref=first_closed.raw_tool_calls_ref,
        unavailable_reason=None,
    )
    with pytest.raises(SchemaValidationError, match="artifact identity"):
        _build_direct(
            fx,
            closed_observations=(forged_closed, *fx.closed_observations[1:]),
        )

    aliased_raw = ArtifactRef(
        artifact_id="different-closed-response-id",
        sha256=first_open.raw_response_ref.sha256,
        byte_length=first_open.raw_response_ref.byte_length,
        media_type=RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
    )
    forged_closed = build_behavioral_observation(
        observation_id=first_closed.observation_id,
        identity=fx.protocol.closed_identity,
        configuration_ref=fx.protocol.closed_configuration_ref,
        configuration_bytes=fx.protocol.closed_configuration_bytes,
        protocol_ref=fx.protocol.artifact_ref,
        case_id=fx.closed_cases[0].case_id,
        case_ref=fx.closed_cases[0].case_ref,
        observation_status=OBSERVED,
        raw_response_ref=aliased_raw,
        raw_tool_calls_ref=first_closed.raw_tool_calls_ref,
        unavailable_reason=None,
    )
    with pytest.raises(SchemaValidationError, match="content identity"):
        _build_direct(
            fx,
            closed_observations=(forged_closed, *fx.closed_observations[1:]),
        )


def test_load_rejects_body_drift_noncanonical_bytes_and_authority_overclaim(
    fx: Fixture,
) -> None:
    artifact = _build_direct(fx)
    noncanonical = b" " + artifact.raw_bytes
    with pytest.raises(SchemaValidationError, match="canonical JSON"):
        load_shared_behavioral_replay_artifact(
            noncanonical,
            replay_ref=_mutated_ref(artifact.artifact_ref, noncanonical),
            protocol=fx.protocol,
            roster=fx.roster,
            open_capabilities=fx.open_capabilities,
            closed_capabilities=fx.closed_capabilities,
            open_observations=fx.open_observations,
            closed_observations=fx.closed_observations,
        )
    for mutate, match in (
        (
            lambda value: value["pairs"][0].__setitem__("execution_ordinal", 9),
            "caller-bound projection",
        ),
        (
            lambda value: value["models"][0].__setitem__(
                "configuration_ref", value["models"][1]["configuration_ref"]
            ),
            "caller-bound projection",
        ),
        (
            lambda value: value["boundary"].__setitem__("model_calls", 1),
            "external calls",
        ),
    ):
        payload = thaw_json(artifact.payload)
        mutate(payload)
        raw = canonical_json_bytes(payload)
        with pytest.raises(SchemaValidationError, match=match):
            load_shared_behavioral_replay_artifact(
                raw,
                replay_ref=_mutated_ref(artifact.artifact_ref, raw),
                protocol=fx.protocol,
                roster=fx.roster,
                open_capabilities=fx.open_capabilities,
                closed_capabilities=fx.closed_capabilities,
                open_observations=fx.open_observations,
                closed_observations=fx.closed_observations,
            )


def test_replay_rejects_mutable_or_forged_projections(fx: Fixture) -> None:
    artifact = _build_direct(fx)
    with pytest.raises(SchemaValidationError, match="recursively frozen"):
        replay_shared_behavioral_replay_artifact(
            replace(artifact, payload=thaw_json(artifact.payload))
        )
    with pytest.raises(SchemaValidationError, match="fresh exact-byte replay"):
        replay_shared_behavioral_replay_artifact(
            replace(artifact, artifact_refs=artifact.artifact_refs[:-1])
        )
    with pytest.raises(SchemaValidationError, match="forged projection"):
        replay_shared_behavioral_replay_artifact(
            replace(artifact, pairs=(object(), *artifact.pairs[1:]))
        )


def test_second_side_failure_returns_no_artifact_and_reports_local_failure(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    open_adapter, closed_adapter = fx.adapters()
    original = ReplayBehavioralAdapter.replay_all

    def fail_closed(self, ordered_cases):
        if self is closed_adapter:
            raise SchemaValidationError("injected local closed replay failure")
        return original(self, ordered_cases)

    monkeypatch.setattr(ReplayBehavioralAdapter, "replay_all", fail_closed)
    with pytest.raises(
        SharedBehavioralReplayFailure,
        match="LOCAL_REPLAY_FAILURE:CLOSED:NO_ARTIFACT",
    ):
        run_shared_behavioral_replay(
            replay_id="runner-closed-failure",
            protocol=fx.protocol,
            roster=fx.roster,
            open_capabilities=fx.open_capabilities,
            closed_capabilities=fx.closed_capabilities,
            open_adapter=open_adapter,
            closed_adapter=closed_adapter,
            open_cases=fx.open_cases,
            closed_cases=fx.closed_cases,
        )
    assert open_adapter.complete
    assert closed_adapter.consumed_case_count == 0


def test_success_has_no_external_call_seam(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args, **kwargs):
        del args, kwargs
        raise AssertionError("external call seam was touched")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    artifact = fx.run()
    assert type(artifact) is SharedBehavioralReplayArtifact
    assert artifact.payload["boundary"]["provider_calls"] == 0
    assert artifact.payload["boundary"]["model_calls"] == 0
    assert artifact.payload["boundary"]["network_calls"] == 0
    assert artifact.payload["boundary"]["spend_actions"] == 0


def test_public_exports_are_literal_unique_and_no_private_or_external_seam() -> None:
    source = inspect.getsource(runner_module)
    tree = ast.parse(source)
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        )
    ]
    assert len(assignments) == 1
    exports = ast.literal_eval(assignments[0].value)
    assert type(exports) is tuple
    assert len(exports) == len(set(exports))
    assert exports == runner_module.__all__
    assert "_REPLAY_SEALS" not in source
    assert "_ReplayAdapterSeal" not in source
    assert "_require_replay_seal" not in source
    forbidden_roots = {
        "asyncio", "http", "os", "pathlib", "requests", "socket", "subprocess", "urllib"
    }
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert forbidden_roots.isdisjoint(imported_roots)
    assert "open(" not in source


def test_schema_and_media_literals_are_exact() -> None:
    assert SHARED_BEHAVIORAL_REPLAY_SCHEMA == (
        "cas_harness_v2.shared_behavioral_replay.v1"
    )
    assert SHARED_BEHAVIORAL_REPLAY_MEDIA_TYPE == (
        "application/vnd.cas-harness.shared-behavioral-replay-v1+json"
    )
