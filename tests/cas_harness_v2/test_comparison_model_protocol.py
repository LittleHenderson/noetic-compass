from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json

import pytest

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes, thaw_json
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.comparison_model_protocol import (
    ACTIVATION_CAPTURE,
    BEHAVIOR_GENERATION,
    BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
    BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
    BEHAVIORAL_OBSERVATION_MEDIA_TYPE,
    CAPABILITY_NAMES,
    CLOSED_WEIGHT,
    COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
    COMPARISON_MODEL_CAPABILITIES_MEDIA_TYPE,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    COMPARISON_MODEL_IDENTITY_MEDIA_TYPE,
    COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
    HIDDEN_STATE_OBSERVATION,
    NON_AUTHORITY,
    OBSERVED,
    OPEN_WEIGHT,
    RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
    RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
    REPLAY,
    STEERING_INTERVENTION,
    STRUCTURE_ONLY,
    SUPPORTED_WITH_EVIDENCE,
    TOOL_CALL_OBSERVATION,
    UNAVAILABLE,
    UNAVAILABLE_BY_ACCESS_MODEL,
    UNAVAILABLE_IN_REPLAY,
    UNKNOWN_UNVERIFIED,
    WEIGHT_IDENTITY_UNAVAILABLE_BY_ACCESS_MODEL,
    BehavioralObservationArtifact,
    ComparisonModelCapabilitiesArtifact,
    ComparisonModelIdentityArtifact,
    build_behavioral_observation,
    build_comparison_capability_evidence_body,
    build_comparison_model_configuration_body,
    build_comparison_model_weight_identity_body,
    build_comparison_model_capabilities,
    build_comparison_model_identity,
    load_behavioral_observation,
    load_comparison_model_capabilities,
    load_comparison_model_identity,
    replay_behavioral_observation,
    replay_comparison_model_capabilities,
    replay_comparison_model_identity,
)


def _ref(
    artifact_id: str,
    media_type: str,
    *,
    body: bytes | None = None,
) -> ArtifactRef:
    snapshot = body if body is not None else (artifact_id + "\n").encode("ascii")
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        media_type=media_type,
    )


def _canonical_mutation(raw: bytes, mutation) -> bytes:
    value = json.loads(raw)
    mutation(value)
    return canonical_json_bytes(value)


def _identity(access_kind: str = OPEN_WEIGHT) -> ComparisonModelIdentityArtifact:
    suffix = access_kind.lower().replace("_", "-")
    provider = "provider.example"
    model_id = f"provider.example/model-{suffix}"
    revision = f"revision-{suffix}-001"
    weight_body = (
        build_comparison_model_weight_identity_body(
            provider=provider, model_id=model_id, revision=revision
        )
        if access_kind == OPEN_WEIGHT
        else None
    )
    return build_comparison_model_identity(
        identity_id=f"comparison-identity-{suffix}",
        access_kind=access_kind,
        provider=provider,
        model_id=model_id,
        revision=revision,
        weight_artifact_ref=(
            _ref(
                f"weight-identity-{suffix}",
                COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
                body=weight_body,
            )
            if access_kind == OPEN_WEIGHT
            else None
        ),
        weight_artifact_bytes=weight_body,
    )


def _configuration(
    identity: ComparisonModelIdentityArtifact,
) -> tuple[ArtifactRef, bytes]:
    body = build_comparison_model_configuration_body(
        configuration_id=f"configuration-{identity.identity_id}", identity=identity
    )
    return _ref(
        f"configuration-{identity.identity_id}",
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        body=body,
    ), body


def _capability_inputs(
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
) -> tuple[
    dict[str, str], dict[str, ArtifactRef | None], dict[str, bytes | None]
]:
    access_kind = identity.access_kind
    statuses = {name: UNKNOWN_UNVERIFIED for name in CAPABILITY_NAMES}
    evidence: dict[str, ArtifactRef | None] = {name: None for name in CAPABILITY_NAMES}
    evidence_bytes: dict[str, bytes | None] = {name: None for name in CAPABILITY_NAMES}
    statuses[BEHAVIOR_GENERATION] = SUPPORTED_WITH_EVIDENCE
    body = build_comparison_capability_evidence_body(
        evidence_id=f"behavior-capability-evidence-{access_kind.lower()}",
        capability_name=BEHAVIOR_GENERATION,
        identity=identity,
        configuration_ref=configuration_ref,
    )
    evidence[BEHAVIOR_GENERATION] = _ref(
        f"behavior-capability-evidence-{access_kind.lower()}",
        COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
        body=body,
    )
    evidence_bytes[BEHAVIOR_GENERATION] = body
    if access_kind == CLOSED_WEIGHT:
        for name in (
            HIDDEN_STATE_OBSERVATION,
            ACTIVATION_CAPTURE,
            STEERING_INTERVENTION,
        ):
            statuses[name] = UNAVAILABLE_BY_ACCESS_MODEL
    if access_kind == REPLAY:
        for name in (
            HIDDEN_STATE_OBSERVATION,
            ACTIVATION_CAPTURE,
            STEERING_INTERVENTION,
        ):
            statuses[name] = UNAVAILABLE_IN_REPLAY
    return statuses, evidence, evidence_bytes


def _capabilities(
    identity: ComparisonModelIdentityArtifact,
) -> ComparisonModelCapabilitiesArtifact:
    configuration_ref, configuration_bytes = _configuration(identity)
    statuses, evidence, evidence_bytes = _capability_inputs(
        identity, configuration_ref
    )
    return build_comparison_model_capabilities(
        capabilities_id=f"capabilities-{identity.access_kind.lower()}",
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_statuses=statuses,
        capability_evidence_refs=evidence,
        capability_evidence_bytes=evidence_bytes,
    )


def _capability_dependencies(
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> dict[str, object]:
    return {
        "configuration_ref": capabilities.configuration_ref,
        "configuration_bytes": capabilities.configuration_bytes,
        "capability_evidence_bytes": {
            item.name: item.evidence_bytes for item in capabilities.capabilities
        },
    }


def _observation_dependencies(
    identity: ComparisonModelIdentityArtifact,
) -> dict[str, ArtifactRef | str | bytes]:
    configuration_ref, configuration_bytes = _configuration(identity)
    return {
        "configuration_ref": configuration_ref,
        "configuration_bytes": configuration_bytes,
        "protocol_ref": _ref(
            "behavioral-protocol-001",
            BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
        ),
        "case_id": "behavioral-case-001",
        "case_ref": _ref(
            "behavioral-case-001",
            BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
        ),
    }


def _observed(
    identity: ComparisonModelIdentityArtifact,
) -> tuple[BehavioralObservationArtifact, dict[str, ArtifactRef | str]]:
    dependencies = _observation_dependencies(identity)
    observation = build_behavioral_observation(
        observation_id="behavioral-observation-001",
        identity=identity,
        **dependencies,
        observation_status=OBSERVED,
        raw_response_ref=_ref(
            "raw-behavioral-response-001",
            RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
        ),
        raw_tool_calls_ref=_ref(
            "raw-behavioral-tool-calls-001",
            RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
        ),
        unavailable_reason=None,
    )
    return observation, dependencies


def test_identity_builds_canonical_immutable_open_closed_and_replay_carriers() -> None:
    open_identity = _identity(OPEN_WEIGHT)
    closed_identity = _identity(CLOSED_WEIGHT)
    replay_identity = _identity(REPLAY)

    assert type(open_identity) is ComparisonModelIdentityArtifact
    assert open_identity.raw_bytes == canonical_json_bytes(thaw_json(open_identity.payload))
    assert open_identity.artifact_ref.media_type == COMPARISON_MODEL_IDENTITY_MEDIA_TYPE
    assert open_identity.weight_artifact_ref is not None
    assert closed_identity.weight_artifact_ref is None
    assert (
        closed_identity.weight_identity_status
        == WEIGHT_IDENTITY_UNAVAILABLE_BY_ACCESS_MODEL
    )
    assert replay_identity.weight_artifact_ref is None
    for identity in (open_identity, closed_identity, replay_identity):
        assert identity.payload["status"]["scope"] == STRUCTURE_ONLY
        assert identity.payload["status"]["authority"] == NON_AUTHORITY
        assert identity.payload["boundary"]["execution"] == "NOT_PERFORMED"
        assert replay_comparison_model_identity(identity) == identity


@pytest.mark.parametrize("access_kind", [CLOSED_WEIGHT, REPLAY])
def test_non_open_identity_cannot_claim_weight_evidence(access_kind: str) -> None:
    with pytest.raises(SchemaValidationError, match="must not claim"):
        build_comparison_model_identity(
            identity_id="comparison-identity-forged",
            access_kind=access_kind,
            provider="provider.example",
            model_id="provider.example/model",
            revision="revision-001",
            weight_artifact_ref=_ref(
                "forged-weight-ref",
                COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
            ),
            weight_artifact_bytes=b"forged",
        )


def test_open_identity_requires_exact_caller_bound_weight_evidence() -> None:
    identity = _identity(OPEN_WEIGHT)
    assert identity.weight_artifact_ref is not None
    forged_ref = replace(identity.weight_artifact_ref, byte_length=2)
    with pytest.raises(SchemaValidationError, match="caller-bound evidence"):
        load_comparison_model_identity(
            identity.raw_bytes,
            weight_artifact_ref=forged_ref,
            weight_artifact_bytes=identity.weight_artifact_bytes,
        )
    with pytest.raises(SchemaValidationError, match="requires"):
        build_comparison_model_identity(
            identity_id="comparison-identity-missing-weight",
            access_kind=OPEN_WEIGHT,
            provider="provider.example",
            model_id="provider.example/model",
            revision="revision-001",
            weight_artifact_ref=None,
            weight_artifact_bytes=None,
        )


def test_identity_loader_rejects_noncanonical_duplicate_float_bool_and_closed_schema() -> None:
    identity = _identity(OPEN_WEIGHT)
    weight_ref = identity.weight_artifact_ref
    assert weight_ref is not None

    pretty = json.dumps(json.loads(identity.raw_bytes), indent=2).encode("ascii")
    with pytest.raises(SchemaValidationError, match="canonical JSON"):
        load_comparison_model_identity(
            pretty, weight_artifact_ref=weight_ref,
            weight_artifact_bytes=identity.weight_artifact_bytes,
        )

    duplicate = identity.raw_bytes.replace(
        b'{"access_kind":', b'{"access_kind":"OPEN_WEIGHT","access_kind":', 1
    )
    with pytest.raises(SchemaValidationError, match="duplicate JSON object key"):
        load_comparison_model_identity(
            duplicate, weight_artifact_ref=weight_ref,
            weight_artifact_bytes=identity.weight_artifact_bytes,
        )

    floating = identity.raw_bytes.replace(
        str(weight_ref.byte_length).encode("ascii"), b"1.5", 1
    )
    with pytest.raises(SchemaValidationError, match="floating-point"):
        load_comparison_model_identity(
            floating, weight_artifact_ref=weight_ref,
            weight_artifact_bytes=identity.weight_artifact_bytes,
        )

    boolean_length = _canonical_mutation(
        identity.raw_bytes,
        lambda value: value["weight_identity"]["artifact_ref"].__setitem__(
            "byte_length", True
        ),
    )
    with pytest.raises(SchemaValidationError, match="exact integer"):
        load_comparison_model_identity(
            boolean_length, weight_artifact_ref=weight_ref,
            weight_artifact_bytes=identity.weight_artifact_bytes,
        )

    extra = _canonical_mutation(
        identity.raw_bytes, lambda value: value.__setitem__("hidden_state", {})
    )
    with pytest.raises(SchemaValidationError, match="forbidden extra"):
        load_comparison_model_identity(
            extra, weight_artifact_ref=weight_ref,
            weight_artifact_bytes=identity.weight_artifact_bytes,
        )

    missing = _canonical_mutation(
        identity.raw_bytes, lambda value: value.pop("revision")
    )
    with pytest.raises(SchemaValidationError, match="missing required"):
        load_comparison_model_identity(
            missing, weight_artifact_ref=weight_ref,
            weight_artifact_bytes=identity.weight_artifact_bytes,
        )


def test_identity_replay_rejects_forged_projection() -> None:
    identity = _identity(OPEN_WEIGHT)
    forged = replace(identity, model_id="provider.example/other-model")
    with pytest.raises(SchemaValidationError, match="fresh exact-byte replay"):
        replay_comparison_model_identity(forged)


@pytest.mark.parametrize("access_kind", [OPEN_WEIGHT, CLOSED_WEIGHT, REPLAY])
def test_capabilities_are_complete_canonical_and_bound_to_identity(
    access_kind: str,
) -> None:
    identity = _identity(access_kind)
    capabilities = _capabilities(identity)

    assert type(capabilities) is ComparisonModelCapabilitiesArtifact
    assert capabilities.artifact_ref.media_type == COMPARISON_MODEL_CAPABILITIES_MEDIA_TYPE
    assert capabilities.identity_ref == identity.artifact_ref
    assert tuple(item.name for item in capabilities.capabilities) == CAPABILITY_NAMES
    assert (
        capabilities.capability(BEHAVIOR_GENERATION).status
        == SUPPORTED_WITH_EVIDENCE
    )
    assert capabilities.payload["status"]["scope"] == STRUCTURE_ONLY
    assert replay_comparison_model_capabilities(
        capabilities, identity=identity
    ) == capabilities


def test_supported_capability_requires_evidence_and_other_status_forbids_it() -> None:
    identity = _identity(OPEN_WEIGHT)
    configuration_ref, configuration_bytes = _configuration(identity)
    statuses, evidence, evidence_bytes = _capability_inputs(identity, configuration_ref)
    evidence[BEHAVIOR_GENERATION] = None
    with pytest.raises(SchemaValidationError, match="exact ArtifactRef"):
        build_comparison_model_capabilities(
            capabilities_id="capabilities-no-evidence",
            identity=identity,
            configuration_ref=configuration_ref,
            configuration_bytes=configuration_bytes,
            capability_statuses=statuses,
            capability_evidence_refs=evidence,
            capability_evidence_bytes=evidence_bytes,
        )

    statuses, evidence, evidence_bytes = _capability_inputs(identity, configuration_ref)
    statuses[BEHAVIOR_GENERATION] = UNKNOWN_UNVERIFIED
    with pytest.raises(SchemaValidationError, match="only when"):
        build_comparison_model_capabilities(
            capabilities_id="capabilities-extra-evidence",
            identity=identity,
            configuration_ref=configuration_ref,
            configuration_bytes=configuration_bytes,
            capability_statuses=statuses,
            capability_evidence_refs=evidence,
            capability_evidence_bytes=evidence_bytes,
        )


def test_closed_and_replay_mechanistic_capabilities_fail_closed() -> None:
    closed_identity = _identity(CLOSED_WEIGHT)
    closed_configuration_ref, closed_configuration_bytes = _configuration(closed_identity)
    statuses, evidence, evidence_bytes = _capability_inputs(
        closed_identity, closed_configuration_ref
    )
    statuses[HIDDEN_STATE_OBSERVATION] = UNKNOWN_UNVERIFIED
    with pytest.raises(SchemaValidationError, match="UNAVAILABLE_BY_ACCESS_MODEL"):
        build_comparison_model_capabilities(
            capabilities_id="closed-capabilities-forged",
            identity=closed_identity,
            configuration_ref=closed_configuration_ref,
            configuration_bytes=closed_configuration_bytes,
            capability_statuses=statuses,
            capability_evidence_refs=evidence,
            capability_evidence_bytes=evidence_bytes,
        )

    replay_identity = _identity(REPLAY)
    replay_configuration_ref, replay_configuration_bytes = _configuration(replay_identity)
    statuses, evidence, evidence_bytes = _capability_inputs(
        replay_identity, replay_configuration_ref
    )
    statuses[STEERING_INTERVENTION] = UNKNOWN_UNVERIFIED
    with pytest.raises(SchemaValidationError, match="UNAVAILABLE_IN_REPLAY"):
        build_comparison_model_capabilities(
            capabilities_id="replay-capabilities-forged",
            identity=replay_identity,
            configuration_ref=replay_configuration_ref,
            configuration_bytes=replay_configuration_bytes,
            capability_statuses=statuses,
            capability_evidence_refs=evidence,
            capability_evidence_bytes=evidence_bytes,
        )


def test_closed_capabilities_exactly_mark_all_three_unavailable_by_access_model() -> None:
    capabilities = _capabilities(_identity(CLOSED_WEIGHT))
    for name in (
        HIDDEN_STATE_OBSERVATION,
        ACTIVATION_CAPTURE,
        STEERING_INTERVENTION,
    ):
        item = capabilities.capability(name)
        assert item.status == UNAVAILABLE_BY_ACCESS_MODEL
        assert item.evidence_ref is None


def test_capabilities_reject_cross_model_and_duplicate_capability_identities() -> None:
    open_identity = _identity(OPEN_WEIGHT)
    capabilities = _capabilities(open_identity)
    other_weight_body = build_comparison_model_weight_identity_body(
        provider="provider.example",
        model_id="provider.example/other-model",
        revision="revision-other-001",
    )
    other_identity = build_comparison_model_identity(
        identity_id="comparison-identity-other-open",
        access_kind=OPEN_WEIGHT,
        provider="provider.example",
        model_id="provider.example/other-model",
        revision="revision-other-001",
        weight_artifact_ref=_ref(
            "weight-identity-other-open",
            COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
            body=other_weight_body,
        ),
        weight_artifact_bytes=other_weight_body,
    )
    with pytest.raises(SchemaValidationError, match="caller-bound model identity"):
        load_comparison_model_capabilities(
            capabilities.raw_bytes,
            identity=other_identity,
            **_capability_dependencies(capabilities),
        )

    duplicate = _canonical_mutation(
        capabilities.raw_bytes,
        lambda value: value["capabilities"][1].__setitem__(
            "name", value["capabilities"][0]["name"]
        ),
    )
    with pytest.raises(SchemaValidationError, match="duplicate capability identity"):
        load_comparison_model_capabilities(
            duplicate, identity=open_identity, **_capability_dependencies(capabilities)
        )


def test_capability_loader_rejects_extra_missing_bool_and_projection_forgery() -> None:
    identity = _identity(OPEN_WEIGHT)
    capabilities = _capabilities(identity)
    extra = _canonical_mutation(
        capabilities.raw_bytes,
        lambda value: value["capabilities"][0].__setitem__("live", True),
    )
    with pytest.raises(SchemaValidationError, match="forbidden extra"):
        load_comparison_model_capabilities(
            extra, identity=identity, **_capability_dependencies(capabilities)
        )

    missing = _canonical_mutation(
        capabilities.raw_bytes,
        lambda value: value["capabilities"][0].pop("status"),
    )
    with pytest.raises(SchemaValidationError, match="missing required"):
        load_comparison_model_capabilities(
            missing, identity=identity, **_capability_dependencies(capabilities)
        )

    boolean_length = _canonical_mutation(
        capabilities.raw_bytes,
        lambda value: value["capabilities"][0]["evidence_ref"].__setitem__(
            "byte_length", False
        ),
    )
    with pytest.raises(SchemaValidationError, match="exact integer"):
        load_comparison_model_capabilities(
            boolean_length, identity=identity, **_capability_dependencies(capabilities)
        )

    forged = replace(capabilities, revision="revision-forged")
    with pytest.raises(SchemaValidationError, match="fresh exact-byte replay"):
        replay_comparison_model_capabilities(forged, identity=identity)


def test_observed_behavior_binds_exact_inputs_and_only_raw_behavioral_refs() -> None:
    identity = _identity(REPLAY)
    observation, dependencies = _observed(identity)
    payload = thaw_json(observation.payload)

    assert type(observation) is BehavioralObservationArtifact
    assert observation.artifact_ref.media_type == BEHAVIORAL_OBSERVATION_MEDIA_TYPE
    assert observation.identity_ref == identity.artifact_ref
    assert observation.configuration_ref == dependencies["configuration_ref"]
    assert observation.protocol_ref == dependencies["protocol_ref"]
    assert observation.case_ref == dependencies["case_ref"]
    assert observation.observation_status == OBSERVED
    assert observation.raw_response_ref is not None
    assert observation.raw_tool_calls_ref is not None
    assert observation.unavailable_reason is None
    assert payload["status"] == {
        "scope": STRUCTURE_ONLY,
        "authority": NON_AUTHORITY,
    }
    assert payload["boundary"]["live_model_call"] == "NOT_PERFORMED"
    assert "hidden_state" not in observation.raw_bytes.decode("ascii").lower()
    assert set(payload) == {
        "schema",
        "observation_id",
        "model_identity",
        "configuration_ref",
        "protocol_ref",
        "case",
        "observation_status",
        "raw_response_ref",
        "raw_tool_calls_ref",
        "unavailable_reason",
        "status",
        "boundary",
    }
    assert replay_behavioral_observation(
        observation,
        identity=identity,
        **dependencies,
    ) == observation


def test_unavailable_behavior_has_no_fabricated_raw_evidence() -> None:
    identity = _identity(CLOSED_WEIGHT)
    dependencies = _observation_dependencies(identity)
    observation = build_behavioral_observation(
        observation_id="behavioral-observation-unavailable",
        identity=identity,
        **dependencies,
        observation_status=UNAVAILABLE,
        raw_response_ref=None,
        raw_tool_calls_ref=None,
        unavailable_reason="PROVIDER_NOT_CONFIGURED",
    )
    assert observation.observation_status == UNAVAILABLE
    assert observation.raw_response_ref is None
    assert observation.raw_tool_calls_ref is None
    assert observation.unavailable_reason == "PROVIDER_NOT_CONFIGURED"

    with pytest.raises(SchemaValidationError, match="must not claim raw"):
        build_behavioral_observation(
            observation_id="behavioral-observation-false-unavailable",
            identity=identity,
            **dependencies,
            observation_status=UNAVAILABLE,
            raw_response_ref=_ref(
                "false-response", RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE
            ),
            raw_tool_calls_ref=None,
            unavailable_reason="PROVIDER_NOT_CONFIGURED",
        )


def test_observed_behavior_requires_both_raw_refs_and_no_unavailable_reason() -> None:
    identity = _identity(REPLAY)
    dependencies = _observation_dependencies(identity)
    with pytest.raises(SchemaValidationError, match="exact ArtifactRef"):
        build_behavioral_observation(
            observation_id="behavioral-observation-missing-tools",
            identity=identity,
            **dependencies,
            observation_status=OBSERVED,
            raw_response_ref=_ref(
                "raw-response-present", RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE
            ),
            raw_tool_calls_ref=None,
            unavailable_reason=None,
        )
    with pytest.raises(SchemaValidationError, match="must not carry"):
        build_behavioral_observation(
            observation_id="behavioral-observation-false-reason",
            identity=identity,
            **dependencies,
            observation_status=OBSERVED,
            raw_response_ref=_ref(
                "raw-response-reason", RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE
            ),
            raw_tool_calls_ref=_ref(
                "raw-tools-reason", RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE
            ),
            unavailable_reason="FALSE_REASON",
        )


def test_observation_loader_rejects_cross_model_config_protocol_and_case_refs() -> None:
    identity = _identity(REPLAY)
    observation, dependencies = _observed(identity)
    other_identity = build_comparison_model_identity(
        identity_id="comparison-identity-other-replay",
        access_kind=REPLAY,
        provider="provider.other",
        model_id="provider.other/model",
        revision="other-replay-revision",
        weight_artifact_ref=None,
        weight_artifact_bytes=None,
    )
    with pytest.raises(SchemaValidationError, match="caller-bound model identity"):
        load_behavioral_observation(
            observation.raw_bytes,
            identity=other_identity,
            **dependencies,
        )

    for field, replacement_ref, match in (
        (
            "configuration_ref",
            _ref("configuration-other", COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE),
            "configuration",
        ),
        (
            "protocol_ref",
            _ref("protocol-other", BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE),
            "protocol reference",
        ),
        (
            "case_ref",
            _ref("case-other", BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE),
            "case binding",
        ),
    ):
        forged_dependencies = dict(dependencies)
        forged_dependencies[field] = replacement_ref
        with pytest.raises(SchemaValidationError, match=match):
            load_behavioral_observation(
                observation.raw_bytes,
                identity=identity,
                **forged_dependencies,
            )


def test_observation_rejects_artifact_identity_and_content_aliases() -> None:
    identity = _identity(REPLAY)
    dependencies = _observation_dependencies(identity)
    configuration_ref = dependencies["configuration_ref"]
    assert type(configuration_ref) is ArtifactRef
    dependencies["case_ref"] = ArtifactRef(
        artifact_id=configuration_ref.artifact_id,
        sha256=configuration_ref.sha256,
        byte_length=configuration_ref.byte_length,
        media_type=BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
    )
    with pytest.raises(SchemaValidationError, match="artifact identity"):
        build_behavioral_observation(
            observation_id="behavioral-observation-aliased-role",
            identity=identity,
            **dependencies,
            observation_status=UNAVAILABLE,
            raw_response_ref=None,
            raw_tool_calls_ref=None,
            unavailable_reason="REPLAY_UNAVAILABLE",
        )

    dependencies = _observation_dependencies(identity)
    same_body = b"{}"
    with pytest.raises(SchemaValidationError, match="content identity"):
        build_behavioral_observation(
            observation_id="behavioral-observation-cloned-content",
            identity=identity,
            **dependencies,
            observation_status=OBSERVED,
            raw_response_ref=_ref(
                "raw-response-cloned",
                RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
                body=same_body,
            ),
            raw_tool_calls_ref=_ref(
                "raw-tools-cloned",
                RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
                body=same_body,
            ),
            unavailable_reason=None,
        )


def test_observation_loader_rejects_noncanonical_duplicate_float_bool_extra_missing() -> None:
    identity = _identity(REPLAY)
    observation, dependencies = _observed(identity)
    pretty = json.dumps(json.loads(observation.raw_bytes), indent=2).encode("ascii")
    with pytest.raises(SchemaValidationError, match="canonical JSON"):
        load_behavioral_observation(pretty, identity=identity, **dependencies)

    duplicate = observation.raw_bytes.replace(
        b'{"boundary":', b'{"boundary":{},"boundary":', 1
    )
    with pytest.raises(SchemaValidationError, match="duplicate JSON object key"):
        load_behavioral_observation(duplicate, identity=identity, **dependencies)

    floating = observation.raw_bytes.replace(b'"byte_length":24', b'"byte_length":1.5', 1)
    with pytest.raises(SchemaValidationError, match="floating-point"):
        load_behavioral_observation(floating, identity=identity, **dependencies)

    boolean_length = _canonical_mutation(
        observation.raw_bytes,
        lambda value: value["configuration_ref"].__setitem__("byte_length", True),
    )
    with pytest.raises(SchemaValidationError, match="exact integer"):
        load_behavioral_observation(
            boolean_length, identity=identity, **dependencies
        )

    extra = _canonical_mutation(
        observation.raw_bytes,
        lambda value: value.__setitem__("activation_vector", []),
    )
    with pytest.raises(SchemaValidationError, match="forbidden extra"):
        load_behavioral_observation(extra, identity=identity, **dependencies)

    missing = _canonical_mutation(
        observation.raw_bytes,
        lambda value: value.pop("raw_tool_calls_ref"),
    )
    with pytest.raises(SchemaValidationError, match="missing required"):
        load_behavioral_observation(missing, identity=identity, **dependencies)


def test_observation_replay_rejects_forged_projection() -> None:
    identity = _identity(REPLAY)
    observation, dependencies = _observed(identity)
    forged = replace(observation, revision="forged-revision")
    with pytest.raises(SchemaValidationError, match="fresh exact-byte replay"):
        replay_behavioral_observation(
            forged,
            identity=identity,
            **dependencies,
        )


def test_observation_builder_does_not_accept_hidden_state_fields() -> None:
    identity = _identity(REPLAY)
    observation, dependencies = _observed(identity)
    value = deepcopy(json.loads(observation.raw_bytes))
    value["hidden_state_ref"] = {
        "artifact_id": "forged-hidden-state",
        "sha256": "A" * 64,
        "byte_length": 1,
        "media_type": "application/octet-stream",
    }
    with pytest.raises(SchemaValidationError, match="forbidden extra"):
        load_behavioral_observation(
            canonical_json_bytes(value),
            identity=identity,
            **dependencies,
        )


@pytest.mark.parametrize(
    "revision",
    [
        "latest",
        "MAIN",
        "Master",
        "current",
        "DEFAULT",
        "Head",
        "stable",
        "NIGHTLY",
        "Rolling",
        "edge",
        "TIP",
        "trunk",
        "Develop",
        "DEV",
        "production",
        "PROD",
        "Canary",
        "snapshot",
        "BETA",
        "refs/heads/release-2026-08-10",
        "REFS/REMOTES/vendor/release-2026-08-10",
        "origin/release-2026-08-10",
        "refs/heads/main",
        "releases/Nightly",
        "branch/develop",
    ],
)
def test_identity_rejects_mutable_revision_aliases_case_insensitively(
    revision: str,
) -> None:
    with pytest.raises(SchemaValidationError, match="mutable revision alias"):
        build_comparison_model_identity(
            identity_id=f"mutable-{revision.lower()}",
            access_kind=CLOSED_WEIGHT,
            provider="provider.example",
            model_id="provider.example/model",
            revision=revision,
            weight_artifact_ref=None,
            weight_artifact_bytes=None,
        )


@pytest.mark.parametrize(
    "revision",
    [
        "2026-08-10",
        "v1.2.3",
        "release-2026-08-10",
        "provider/revisions/2026-08-10",
        "refs/tags/v1.2.3",
        "0123456789abcdef0123456789abcdef01234567",
    ],
)
def test_identity_accepts_exact_dated_versioned_or_digest_revisions(
    revision: str,
) -> None:
    identity = build_comparison_model_identity(
        identity_id=f"immutable-{sha256_bytes(revision.encode())[:16]}",
        access_kind=CLOSED_WEIGHT,
        provider="provider.example",
        model_id="provider.example/model",
        revision=revision,
        weight_artifact_ref=None,
        weight_artifact_bytes=None,
    )
    assert identity.revision == revision


def test_weight_and_configuration_bodies_reject_cross_model_reuse() -> None:
    weight_body = build_comparison_model_weight_identity_body(
        provider="provider.a", model_id="provider.a/model-a", revision="revision-a-001"
    )
    weight_ref = _ref(
        "weight-model-a", COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE, body=weight_body
    )
    identity_a = build_comparison_model_identity(
        identity_id="identity-a",
        access_kind=OPEN_WEIGHT,
        provider="provider.a",
        model_id="provider.a/model-a",
        revision="revision-a-001",
        weight_artifact_ref=weight_ref,
        weight_artifact_bytes=weight_body,
    )
    with pytest.raises(SchemaValidationError, match="exact model binding"):
        build_comparison_model_identity(
            identity_id="identity-b-forged-weight",
            access_kind=OPEN_WEIGHT,
            provider="provider.b",
            model_id="provider.b/model-b",
            revision="revision-b-001",
            weight_artifact_ref=weight_ref,
            weight_artifact_bytes=weight_body,
        )

    identity_b = _identity(REPLAY)
    dependencies = _observation_dependencies(identity_a)
    with pytest.raises(SchemaValidationError, match="caller-bound model identity"):
        build_behavioral_observation(
            observation_id="observation-cross-model-config",
            identity=identity_b,
            **dependencies,
            observation_status=UNAVAILABLE,
            raw_response_ref=None,
            raw_tool_calls_ref=None,
            unavailable_reason="REPLAY_UNAVAILABLE",
        )


def test_capability_evidence_rejects_self_wrong_media_reuse_and_transitive_ids() -> None:
    identity = _identity(OPEN_WEIGHT)
    assert identity.weight_artifact_ref is not None
    configuration_ref, configuration_bytes = _configuration(identity)
    statuses, evidence, evidence_bytes = _capability_inputs(identity, configuration_ref)

    evidence[BEHAVIOR_GENERATION] = identity.artifact_ref
    evidence_bytes[BEHAVIOR_GENERATION] = identity.raw_bytes
    with pytest.raises(SchemaValidationError, match="media_type"):
        build_comparison_model_capabilities(
            capabilities_id="caps-self-evidence",
            identity=identity,
            configuration_ref=configuration_ref,
            configuration_bytes=configuration_bytes,
            capability_statuses=statuses,
            capability_evidence_refs=evidence,
            capability_evidence_bytes=evidence_bytes,
        )

    statuses, evidence, evidence_bytes = _capability_inputs(identity, configuration_ref)
    statuses[TOOL_CALL_OBSERVATION] = SUPPORTED_WITH_EVIDENCE
    evidence[TOOL_CALL_OBSERVATION] = evidence[BEHAVIOR_GENERATION]
    evidence_bytes[TOOL_CALL_OBSERVATION] = evidence_bytes[BEHAVIOR_GENERATION]
    with pytest.raises(SchemaValidationError, match="different capability"):
        build_comparison_model_capabilities(
            capabilities_id="caps-reused-role",
            identity=identity,
            configuration_ref=configuration_ref,
            configuration_bytes=configuration_bytes,
            capability_statuses=statuses,
            capability_evidence_refs=evidence,
            capability_evidence_bytes=evidence_bytes,
        )

    statuses, evidence, evidence_bytes = _capability_inputs(identity, configuration_ref)
    transitive_id = identity.weight_artifact_ref.artifact_id
    transitive_body = build_comparison_capability_evidence_body(
        evidence_id=transitive_id,
        capability_name=BEHAVIOR_GENERATION,
        identity=identity,
        configuration_ref=configuration_ref,
    )
    evidence[BEHAVIOR_GENERATION] = _ref(
        transitive_id,
        COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
        body=transitive_body,
    )
    evidence_bytes[BEHAVIOR_GENERATION] = transitive_body
    with pytest.raises(SchemaValidationError, match="artifact identity"):
        build_comparison_model_capabilities(
            capabilities_id="caps-transitive-conflict",
            identity=identity,
            configuration_ref=configuration_ref,
            configuration_bytes=configuration_bytes,
            capability_statuses=statuses,
            capability_evidence_refs=evidence,
            capability_evidence_bytes=evidence_bytes,
        )
    with pytest.raises(SchemaValidationError, match="carrier artifact identity"):
        build_comparison_model_capabilities(
            capabilities_id=identity.weight_artifact_ref.artifact_id,
            identity=identity,
            configuration_ref=configuration_ref,
            configuration_bytes=configuration_bytes,
            capability_statuses={name: UNKNOWN_UNVERIFIED for name in CAPABILITY_NAMES},
            capability_evidence_refs={name: None for name in CAPABILITY_NAMES},
            capability_evidence_bytes={name: None for name in CAPABILITY_NAMES},
        )


def test_transitive_weight_identity_blocks_observation_owner_collision() -> None:
    identity = _identity(OPEN_WEIGHT)
    assert identity.weight_artifact_ref is not None
    dependencies = _observation_dependencies(identity)
    with pytest.raises(SchemaValidationError, match="carrier artifact identity"):
        build_behavioral_observation(
            observation_id=identity.weight_artifact_ref.artifact_id,
            identity=identity,
            **dependencies,
            observation_status=UNAVAILABLE,
            raw_response_ref=None,
            raw_tool_calls_ref=None,
            unavailable_reason="BACKEND_UNAVAILABLE",
        )


def test_replay_rejects_mutable_payloads_and_nonexact_projection_types() -> None:
    identity = _identity(REPLAY)
    with pytest.raises(SchemaValidationError, match="recursively frozen"):
        replay_comparison_model_identity(
            replace(identity, payload=thaw_json(identity.payload))
        )

    class MutableString(str):
        pass

    with pytest.raises(SchemaValidationError, match="exact immutable scalar"):
        replay_comparison_model_identity(
            replace(identity, model_id=MutableString(identity.model_id))
        )

    capabilities = _capabilities(identity)
    with pytest.raises(SchemaValidationError, match="recursively frozen"):
        replay_comparison_model_capabilities(
            replace(capabilities, payload=thaw_json(capabilities.payload)),
            identity=identity,
        )

    observation, dependencies = _observed(identity)
    with pytest.raises(SchemaValidationError, match="recursively frozen"):
        replay_behavioral_observation(
            replace(observation, payload=thaw_json(observation.payload)),
            identity=identity,
            **dependencies,
        )
