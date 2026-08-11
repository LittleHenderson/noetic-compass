from __future__ import annotations

import copy
from dataclasses import dataclass, replace
import pickle
import socket
import subprocess
import urllib.request

import pytest

import cas_harness_v2.comparison_adapters as adapter_module
import cas_harness_v2.comparison_model_protocol as protocol_module
from cas_harness_v2._strict_json import sha256_bytes
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.comparison_adapters import (
    BEHAVIORAL_ADAPTER_AUTHORITY,
    BEHAVIORAL_ADAPTER_STATUS,
    BEHAVIORAL_REPLAY_MODE,
    BehavioralAdapterBinding,
    BehavioralAdapterUnavailableError,
    BehavioralCaseInput,
    ReplayBehavioralAdapter,
    UnavailableBehavioralAdapter,
    build_replay_behavioral_adapter,
    build_unavailable_behavioral_adapter,
    observe_behavioral_case,
)
from cas_harness_v2.comparison_model_protocol import (
    ACTIVATION_CAPTURE,
    BEHAVIOR_GENERATION,
    BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
    BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
    CLOSED_WEIGHT,
    COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    HIDDEN_STATE_OBSERVATION,
    LOGPROB_OBSERVATION,
    NON_AUTHORITY,
    OBSERVED,
    REPLAY,
    RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
    RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
    STEERING_INTERVENTION,
    STRUCTURE_ONLY,
    SUPPORTED_WITH_EVIDENCE,
    TOOL_CALL_OBSERVATION,
    UNAVAILABLE,
    UNAVAILABLE_BY_ACCESS_MODEL,
    build_behavioral_observation,
    build_comparison_capability_evidence_body,
    build_comparison_model_configuration_body,
    build_comparison_model_capabilities,
    build_comparison_model_identity,
)


def ref(
    artifact_id: str,
    body: bytes,
    media_type: str = "application/octet-stream",
) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(body),
        byte_length=len(body),
        media_type=media_type,
    )


@dataclass(frozen=True)
class Fixture:
    identity: object
    capabilities: object
    configuration_ref: ArtifactRef
    configuration_bytes: bytes
    protocol_ref: ArtifactRef
    cases: tuple[BehavioralCaseInput, ...]
    observations: tuple[object, ...]

    def replay_adapter(self) -> ReplayBehavioralAdapter:
        return build_replay_behavioral_adapter(
            identity=self.identity,
            capabilities=self.capabilities,
            configuration_ref=self.configuration_ref,
            protocol_ref=self.protocol_ref,
            ordered_cases=self.cases,
            observations=self.observations,
        )

    def unavailable_adapter(self) -> UnavailableBehavioralAdapter:
        return build_unavailable_behavioral_adapter(
            identity=self.identity,
            capabilities=self.capabilities,
            configuration_ref=self.configuration_ref,
            protocol_ref=self.protocol_ref,
            reason="REPLAY_FIXTURE_UNAVAILABLE",
        )


@pytest.fixture
def fx() -> Fixture:
    identity = build_comparison_model_identity(
        identity_id="closed-fixture-model",
        access_kind=CLOSED_WEIGHT,
        provider="fixture-provider",
        model_id="fixture/closed-model",
        revision="fixture-revision-001",
        weight_artifact_ref=None,
    )
    capability_statuses = {
        BEHAVIOR_GENERATION: SUPPORTED_WITH_EVIDENCE,
        TOOL_CALL_OBSERVATION: SUPPORTED_WITH_EVIDENCE,
        LOGPROB_OBSERVATION: UNAVAILABLE_BY_ACCESS_MODEL,
        HIDDEN_STATE_OBSERVATION: UNAVAILABLE_BY_ACCESS_MODEL,
        ACTIVATION_CAPTURE: UNAVAILABLE_BY_ACCESS_MODEL,
        STEERING_INTERVENTION: UNAVAILABLE_BY_ACCESS_MODEL,
    }
    configuration_bytes = build_comparison_model_configuration_body(
        configuration_id="behavior-config",
        identity=identity,
    )
    configuration_ref = ref(
        "behavior-config",
        configuration_bytes,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    )
    capability_evidence_bytes = {
        name: (
            build_comparison_capability_evidence_body(
                evidence_id=artifact_id,
                capability_name=name,
                identity=identity,
                configuration_ref=configuration_ref,
            )
            if artifact_id is not None
            else None
        )
        for name, artifact_id in {
            BEHAVIOR_GENERATION: "cap-behavior",
            TOOL_CALL_OBSERVATION: "cap-tools",
            LOGPROB_OBSERVATION: None,
            HIDDEN_STATE_OBSERVATION: None,
            ACTIVATION_CAPTURE: None,
            STEERING_INTERVENTION: None,
        }.items()
    }
    capability_evidence_refs = {
        BEHAVIOR_GENERATION: ref(
            "cap-behavior",
            capability_evidence_bytes[BEHAVIOR_GENERATION],
            COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
        ),
        TOOL_CALL_OBSERVATION: ref(
            "cap-tools",
            capability_evidence_bytes[TOOL_CALL_OBSERVATION],
            COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
        ),
        LOGPROB_OBSERVATION: None,
        HIDDEN_STATE_OBSERVATION: None,
        ACTIVATION_CAPTURE: None,
        STEERING_INTERVENTION: None,
    }
    capabilities = build_comparison_model_capabilities(
        capabilities_id="closed-fixture-capabilities",
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_statuses=capability_statuses,
        capability_evidence_refs=capability_evidence_refs,
        capability_evidence_bytes=capability_evidence_bytes,
    )
    protocol_ref = ref(
        "behavior-protocol",
        b"frozen behavior protocol",
        BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
    )
    cases = tuple(
        BehavioralCaseInput(
            execution_ordinal=index,
            case_id=f"behavior-case-{index:03d}",
            case_ref=ref(
                f"behavior-case-ref-{index:03d}",
                f"case {index}".encode(),
                BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
            ),
            configuration_ref=configuration_ref,
            protocol_ref=protocol_ref,
        )
        for index in (1, 2)
    )
    observations = tuple(
        build_behavioral_observation(
            observation_id=f"behavior-observation-{case.execution_ordinal:03d}",
            identity=identity,
            configuration_ref=configuration_ref,
            configuration_bytes=configuration_bytes,
            protocol_ref=protocol_ref,
            case_id=case.case_id,
            case_ref=case.case_ref,
            observation_status=OBSERVED,
            raw_response_ref=ref(
                f"raw-response-{case.execution_ordinal:03d}",
                f"response {case.execution_ordinal}".encode(),
                RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
            ),
            raw_tool_calls_ref=ref(
                f"raw-tool-calls-{case.execution_ordinal:03d}",
                f"tool calls {case.execution_ordinal}".encode(),
                RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
            ),
            unavailable_reason=None,
        )
        for case in cases
    )
    return Fixture(
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        protocol_ref=protocol_ref,
        cases=cases,
        observations=observations,
    )


def test_label_free_case_and_non_authority_metadata(fx: Fixture) -> None:
    case = fx.cases[0]
    assert case.execution_ordinal == 1
    for forbidden in (
        "label",
        "binary_label",
        "ground_truth",
        "prediction",
        "hidden_state",
        "activation",
    ):
        assert not hasattr(case, forbidden)

    adapter = fx.replay_adapter()
    assert adapter.adapter_mode == BEHAVIORAL_REPLAY_MODE == REPLAY
    assert adapter.status == BEHAVIORAL_ADAPTER_STATUS == STRUCTURE_ONLY
    assert adapter.authority == BEHAVIORAL_ADAPTER_AUTHORITY == NON_AUTHORITY
    assert adapter.case_count == 2
    assert adapter.consumed_case_count == 0
    assert adapter.complete is False


def test_binding_is_exact_fresh_detached_and_mutation_safe(fx: Fixture) -> None:
    adapter = fx.replay_adapter()
    first = adapter.binding
    second = adapter.binding
    assert type(first) is BehavioralAdapterBinding
    assert first == second
    assert first is not second
    assert first.identity_ref == fx.identity.artifact_ref
    assert first.capabilities_ref == fx.capabilities.artifact_ref
    assert first.configuration_ref == fx.configuration_ref
    assert first.protocol_ref == fx.protocol_ref
    assert first.identity_ref is not second.identity_ref
    assert first.capabilities_ref is not second.capabilities_ref
    assert first.configuration_ref is not fx.configuration_ref
    assert first.protocol_ref is not fx.protocol_ref

    object.__setattr__(first.configuration_ref, "artifact_id", "mutated-copy")
    fresh = adapter.binding
    assert fresh.configuration_ref == fx.configuration_ref
    assert adapter.replay_all(fx.cases) == fx.observations


def test_binding_rejects_wrong_media_and_cross_role_substitution(fx: Fixture) -> None:
    with pytest.raises(SchemaValidationError, match="media_type"):
        BehavioralAdapterBinding(
            identity_ref=fx.protocol_ref,
            capabilities_ref=fx.capabilities.artifact_ref,
            configuration_ref=fx.configuration_ref,
            protocol_ref=fx.protocol_ref,
        )
    with pytest.raises(SchemaValidationError, match="cross-role artifact reuse"):
        BehavioralAdapterBinding(
            identity_ref=fx.identity.artifact_ref,
            capabilities_ref=fx.capabilities.artifact_ref,
            configuration_ref=fx.configuration_ref,
            protocol_ref=ArtifactRef(
                artifact_id=fx.configuration_ref.artifact_id,
                sha256=fx.configuration_ref.sha256,
                byte_length=fx.configuration_ref.byte_length,
                media_type=BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
            ),
        )
    forged_ref = ref(
        "forged-binding-identity",
        b"forged binding identity",
        protocol_module.COMPARISON_MODEL_IDENTITY_MEDIA_TYPE,
    )
    object.__setattr__(forged_ref, "byte_length", True)
    with pytest.raises(SchemaValidationError, match="immutable scalar types"):
        BehavioralAdapterBinding(
            identity_ref=forged_ref,
            capabilities_ref=fx.capabilities.artifact_ref,
            configuration_ref=fx.configuration_ref,
            protocol_ref=fx.protocol_ref,
        )


def test_adapter_is_bound_to_final_protocol_module_and_capability_status() -> None:
    assert (
        adapter_module.ComparisonModelIdentityArtifact
        is protocol_module.ComparisonModelIdentityArtifact
    )
    assert (
        adapter_module.UNAVAILABLE_BY_ACCESS_MODEL
        == protocol_module.UNAVAILABLE_BY_ACCESS_MODEL
    )
    assert adapter_module.__name__.rsplit(".", 1)[0] == protocol_module.__name__.rsplit(
        ".", 1
    )[0]


def test_replay_returns_only_exact_preloaded_canonical_artifacts_once(
    fx: Fixture,
) -> None:
    adapter = fx.replay_adapter()
    first = adapter.observe(fx.cases[0])
    second_bytes = adapter.observe_bytes(fx.cases[1])
    assert first == fx.observations[0]
    assert first is not fx.observations[0]
    assert second_bytes == fx.observations[1].raw_bytes
    assert adapter.consumed_case_count == adapter.case_count == 2
    assert adapter.complete is True
    adapter.require_complete()
    with pytest.raises(SchemaValidationError, match="already consumed"):
        adapter.observe(fx.cases[0])


def test_whole_roster_replay_is_atomic_exact_and_one_use(fx: Fixture) -> None:
    adapter = fx.replay_adapter()
    substituted = replace(fx.cases[0])
    with pytest.raises(SchemaValidationError, match="missing, duplicated, substituted"):
        adapter.replay_all((substituted, fx.cases[1]))
    assert adapter.consumed_case_count == 0
    assert adapter.replay_all(fx.cases) == fx.observations
    with pytest.raises(SchemaValidationError, match="untouched"):
        adapter.replay_all(fx.cases)


def test_factory_and_returns_detach_caller_owned_observations(fx: Fixture) -> None:
    expected_first_bytes = fx.observations[0].raw_bytes
    adapter = fx.replay_adapter()

    object.__setattr__(fx.observations[0], "raw_bytes", b"caller-owned mutation")
    first = adapter.observe(fx.cases[0])
    assert first.raw_bytes == expected_first_bytes
    assert first is not fx.observations[0]

    object.__setattr__(first, "raw_bytes", b"returned-object mutation")
    object.__setattr__(
        first.raw_response_ref,
        "artifact_id",
        "returned-response-mutation",
    )
    second = adapter.observe(fx.cases[1])
    assert second == fx.observations[1]
    assert second is not fx.observations[1]
    adapter.require_complete()


def test_missing_duplicate_and_out_of_order_cases_fail_closed(fx: Fixture) -> None:
    with pytest.raises(SchemaValidationError, match="matching the full case roster"):
        build_replay_behavioral_adapter(
            identity=fx.identity,
            capabilities=fx.capabilities,
            configuration_ref=fx.configuration_ref,
            protocol_ref=fx.protocol_ref,
            ordered_cases=fx.cases,
            observations=fx.observations[:1],
        )
    duplicate_id = BehavioralCaseInput(
        execution_ordinal=2,
        case_id=fx.cases[0].case_id,
        case_ref=ref(
            "different-case-ref",
            b"different case",
            BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
        ),
        configuration_ref=fx.configuration_ref,
        protocol_ref=fx.protocol_ref,
    )
    with pytest.raises(SchemaValidationError, match="duplicate case_id"):
        build_replay_behavioral_adapter(
            identity=fx.identity,
            capabilities=fx.capabilities,
            configuration_ref=fx.configuration_ref,
            protocol_ref=fx.protocol_ref,
            ordered_cases=(fx.cases[0], duplicate_id),
            observations=fx.observations,
        )

    adapter = fx.replay_adapter()
    with pytest.raises(SchemaValidationError, match="out of order"):
        adapter.observe(fx.cases[1])
    assert adapter.consumed_case_count == 0
    replayed = adapter.observe(fx.cases[0])
    assert replayed == fx.observations[0]
    assert replayed is not fx.observations[0]


def test_global_artifact_closure_rejects_cross_role_id_and_content_aliases(
    fx: Fixture,
) -> None:
    cross_role_id = build_behavioral_observation(
        observation_id=fx.cases[1].case_ref.artifact_id,
        identity=fx.identity,
        configuration_ref=fx.configuration_ref,
        configuration_bytes=fx.configuration_bytes,
        protocol_ref=fx.protocol_ref,
        case_id=fx.cases[0].case_id,
        case_ref=fx.cases[0].case_ref,
        observation_status=OBSERVED,
        raw_response_ref=ref(
            "cross-role-id-response",
            b"cross-role id response",
            RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
        ),
        raw_tool_calls_ref=ref(
            "cross-role-id-tools",
            b"cross-role id tools",
            RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
        ),
        unavailable_reason=None,
    )
    with pytest.raises(SchemaValidationError, match="reuses artifact_id"):
        build_replay_behavioral_adapter(
            identity=fx.identity,
            capabilities=fx.capabilities,
            configuration_ref=fx.configuration_ref,
            protocol_ref=fx.protocol_ref,
            ordered_cases=fx.cases,
            observations=(cross_role_id, fx.observations[1]),
        )

    shared_response_body = b"cross-row shared raw response"
    cross_row_content = tuple(
        build_behavioral_observation(
            observation_id=f"cross-row-content-{case.execution_ordinal:03d}",
            identity=fx.identity,
            configuration_ref=fx.configuration_ref,
            configuration_bytes=fx.configuration_bytes,
            protocol_ref=fx.protocol_ref,
            case_id=case.case_id,
            case_ref=case.case_ref,
            observation_status=OBSERVED,
            raw_response_ref=ref(
                f"cross-row-response-{case.execution_ordinal:03d}",
                shared_response_body,
                RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
            ),
            raw_tool_calls_ref=ref(
                f"cross-row-tools-{case.execution_ordinal:03d}",
                f"cross-row tools {case.execution_ordinal}".encode(),
                RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
            ),
            unavailable_reason=None,
        )
        for case in fx.cases
    )
    with pytest.raises(SchemaValidationError, match="reuses content"):
        build_replay_behavioral_adapter(
            identity=fx.identity,
            capabilities=fx.capabilities,
            configuration_ref=fx.configuration_ref,
            protocol_ref=fx.protocol_ref,
            ordered_cases=fx.cases,
            observations=cross_row_content,
        )


def test_mixed_model_and_noncanonical_or_mutated_artifacts_are_rejected(
    fx: Fixture,
) -> None:
    other_identity = build_comparison_model_identity(
        identity_id="other-closed-fixture-model",
        access_kind=CLOSED_WEIGHT,
        provider="fixture-provider",
        model_id="fixture/other-closed-model",
        revision="fixture-revision-002",
        weight_artifact_ref=None,
    )
    other_configuration_bytes = build_comparison_model_configuration_body(
        configuration_id="other-behavior-config",
        identity=other_identity,
    )
    other_configuration_ref = ref(
        "other-behavior-config",
        other_configuration_bytes,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    )
    mixed = build_behavioral_observation(
        observation_id="mixed-model-observation",
        identity=other_identity,
        configuration_ref=other_configuration_ref,
        configuration_bytes=other_configuration_bytes,
        protocol_ref=fx.protocol_ref,
        case_id=fx.cases[0].case_id,
        case_ref=fx.cases[0].case_ref,
        observation_status=OBSERVED,
        raw_response_ref=ref(
            "mixed-response",
            b"mixed response",
            RAW_BEHAVIORAL_RESPONSE_MEDIA_TYPE,
        ),
        raw_tool_calls_ref=ref(
            "mixed-tools",
            b"mixed tools",
            RAW_BEHAVIORAL_TOOL_CALLS_MEDIA_TYPE,
        ),
        unavailable_reason=None,
    )
    with pytest.raises(SchemaValidationError, match="exact bound replay"):
        build_replay_behavioral_adapter(
            identity=fx.identity,
            capabilities=fx.capabilities,
            configuration_ref=fx.configuration_ref,
            protocol_ref=fx.protocol_ref,
            ordered_cases=(fx.cases[0],),
            observations=(mixed,),
        )

    forged = replace(fx.observations[0], raw_bytes=b"{}")
    with pytest.raises(SchemaValidationError, match="reference does not bind"):
        build_replay_behavioral_adapter(
            identity=fx.identity,
            capabilities=fx.capabilities,
            configuration_ref=fx.configuration_ref,
            protocol_ref=fx.protocol_ref,
            ordered_cases=(fx.cases[0],),
            observations=(forged,),
        )

    adapter = fx.replay_adapter()
    object.__setattr__(fx.cases[0], "case_id", "tampered-case")
    with pytest.raises(SchemaValidationError, match="mutated"):
        adapter.observe(fx.cases[0])
    assert adapter.consumed_case_count == 0


def test_replay_path_has_zero_network_provider_model_or_spend_calls(
    fx: Fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*args, **kwargs):
        del args, kwargs
        calls.append("side-effect")
        raise AssertionError("external side effect attempted")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    adapter = fx.replay_adapter()
    assert adapter.replay_all(fx.cases) == fx.observations
    assert calls == []


def test_unavailable_fails_before_case_inspection_or_any_side_effect(
    fx: Fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def forbidden(*args, **kwargs):
        del args, kwargs
        calls.append("side-effect")
        raise AssertionError("external side effect attempted")

    class ExplosiveCase:
        def __getattribute__(self, name):
            raise AssertionError(f"unavailable adapter inspected {name}")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    adapter = fx.unavailable_adapter()
    assert adapter.adapter_mode == UNAVAILABLE
    assert adapter.status == STRUCTURE_ONLY
    assert adapter.authority == NON_AUTHORITY
    with pytest.raises(
        BehavioralAdapterUnavailableError,
        match="REPLAY_FIXTURE_UNAVAILABLE",
    ):
        adapter.observe(ExplosiveCase())
    assert calls == []


@pytest.mark.parametrize("kind", ["replay", "unavailable"])
def test_adapters_reject_copy_pickle_replace_and_forgery(
    fx: Fixture,
    kind: str,
) -> None:
    adapter = fx.replay_adapter() if kind == "replay" else fx.unavailable_adapter()
    for operation in (
        lambda: copy.copy(adapter),
        lambda: copy.deepcopy(adapter),
        lambda: pickle.dumps(adapter),
        lambda: replace(adapter),
        lambda: copy.replace(adapter),
    ):
        with pytest.raises(TypeError):
            operation()

    exact_type = type(adapter)
    forged = object.__new__(exact_type)
    with pytest.raises(SchemaValidationError, match="process-sealed"):
        forged.observe(fx.cases[0])


def test_direct_construction_subclass_and_arbitrary_live_adapter_are_rejected(
    fx: Fixture,
) -> None:
    with pytest.raises(TypeError, match="factory-only"):
        ReplayBehavioralAdapter()
    with pytest.raises(TypeError, match="factory-only"):
        UnavailableBehavioralAdapter()
    with pytest.raises(TypeError, match="cannot be subclassed"):

        class ReplaySubclass(ReplayBehavioralAdapter):
            pass

    with pytest.raises(TypeError, match="cannot be subclassed"):

        class UnavailableSubclass(UnavailableBehavioralAdapter):
            pass

    called: list[bool] = []

    class ArbitraryLiveAdapter:
        def observe(self, case):
            del case
            called.append(True)
            return fx.observations[0]

    with pytest.raises(SchemaValidationError, match="arbitrary or live"):
        observe_behavioral_case(ArbitraryLiveAdapter(), fx.cases[0])
    assert called == []


def test_closed_weight_replay_exposes_no_hidden_state_carrier(fx: Fixture) -> None:
    capability_by_name = {
        capability.name: capability.status
        for capability in fx.capabilities.capabilities
    }
    assert (
        capability_by_name[HIDDEN_STATE_OBSERVATION]
        == UNAVAILABLE_BY_ACCESS_MODEL
    )
    assert capability_by_name[ACTIVATION_CAPTURE] == UNAVAILABLE_BY_ACCESS_MODEL
    assert capability_by_name[STEERING_INTERVENTION] == UNAVAILABLE_BY_ACCESS_MODEL
    observation = fx.replay_adapter().observe(fx.cases[0])
    assert b"hidden_state" not in observation.raw_bytes
    assert b"activation" not in observation.raw_bytes
    assert not hasattr(observation, "hidden_state_ref")


def test_incomplete_replay_cannot_be_reported_complete(fx: Fixture) -> None:
    adapter = fx.replay_adapter()
    adapter.observe(fx.cases[0])
    with pytest.raises(SchemaValidationError, match="not completely consumed"):
        adapter.require_complete()
