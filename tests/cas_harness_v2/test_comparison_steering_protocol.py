from __future__ import annotations

import copy
from dataclasses import dataclass, replace
import pickle
import socket
import subprocess
import urllib.request

import pytest

import cas_harness_v2.comparison_steering_protocol as steering_module
from cas_harness_v2._strict_json import sha256_bytes, thaw_json
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError
from cas_harness_v2.comparison_model_protocol import (
    ACTIVATION_CAPTURE,
    BEHAVIOR_GENERATION,
    CAPABILITY_NAMES,
    CLOSED_WEIGHT,
    COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
    HIDDEN_STATE_OBSERVATION,
    LOGPROB_OBSERVATION,
    OPEN_WEIGHT,
    STEERING_INTERVENTION,
    SUPPORTED_WITH_EVIDENCE,
    TOOL_CALL_OBSERVATION,
    UNAVAILABLE_BY_ACCESS_MODEL,
    UNAVAILABLE_NOT_IMPLEMENTED,
    UNKNOWN_UNVERIFIED,
    build_comparison_capability_evidence_body,
    build_comparison_model_capabilities,
    build_comparison_model_configuration_body,
    build_comparison_model_identity,
    build_comparison_model_weight_identity_body,
)
from cas_harness_v2.comparison_steering_protocol import (
    ACTIVATION_CHANGED,
    ACTIVATION_COORDINATE_MEDIA_TYPE,
    BACKEND_UNAVAILABLE,
    BLACK_BOX_CONTROL_NAMES,
    BLACK_BOX_CONTROL_SPEC_MEDIA_TYPE,
    BLACK_BOX_POLICY_CONTROL,
    FROZEN_COMPARISON_ROSTER_MEDIA_TYPE,
    STEERING_CONTROL_NAMES,
    STEERING_CONTROL_SPEC_MEDIA_TYPE,
    STEERING_DIRECTION_MEDIA_TYPE,
    SteeringBackendUnavailableError,
    UnavailableSteeringBackend,
    build_activation_coordinate_body,
    build_black_box_control_spec_body,
    build_black_box_policy_control,
    build_steering_control_spec_body,
    build_steering_direction_body,
    build_steering_protocol,
    build_unavailable_steering_backend,
    load_steering_protocol,
    replay_black_box_policy_control,
    replay_steering_protocol,
)


def ref(artifact_id: str, body: bytes, media_type: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(body),
        byte_length=len(body),
        media_type=media_type,
    )


def model_fixture(
    access_kind: str,
    suffix: str,
    *,
    steering_supported: bool = True,
    behavior_supported: bool = True,
):
    provider = f"fixture-provider-{suffix}"
    model_id = f"fixture/model-{suffix}"
    revision = f"fixture-revision-2026-08-{suffix}"
    if access_kind == OPEN_WEIGHT:
        weight_bytes = build_comparison_model_weight_identity_body(
            provider=provider,
            model_id=model_id,
            revision=revision,
        )
        weight_ref = ref(
            f"weight-{suffix}",
            weight_bytes,
            COMPARISON_MODEL_WEIGHT_IDENTITY_MEDIA_TYPE,
        )
    else:
        weight_bytes = None
        weight_ref = None
    identity = build_comparison_model_identity(
        identity_id=f"identity-{suffix}",
        access_kind=access_kind,
        provider=provider,
        model_id=model_id,
        revision=revision,
        weight_artifact_ref=weight_ref,
        weight_artifact_bytes=weight_bytes,
    )
    configuration_bytes = build_comparison_model_configuration_body(
        configuration_id=f"configuration-{suffix}",
        identity=identity,
    )
    configuration_ref = ref(
        f"configuration-{suffix}",
        configuration_bytes,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    )
    if access_kind == OPEN_WEIGHT:
        supported = {
            TOOL_CALL_OBSERVATION,
            HIDDEN_STATE_OBSERVATION,
            ACTIVATION_CAPTURE,
        }
        if behavior_supported:
            supported.add(BEHAVIOR_GENERATION)
        if steering_supported:
            supported.add(STEERING_INTERVENTION)
        statuses = {
            name: (
                SUPPORTED_WITH_EVIDENCE
                if name in supported
                else UNAVAILABLE_NOT_IMPLEMENTED
            )
            for name in CAPABILITY_NAMES
        }
    else:
        statuses = {
            BEHAVIOR_GENERATION: SUPPORTED_WITH_EVIDENCE,
            TOOL_CALL_OBSERVATION: SUPPORTED_WITH_EVIDENCE,
            LOGPROB_OBSERVATION: UNKNOWN_UNVERIFIED,
            HIDDEN_STATE_OBSERVATION: UNAVAILABLE_BY_ACCESS_MODEL,
            ACTIVATION_CAPTURE: UNAVAILABLE_BY_ACCESS_MODEL,
            STEERING_INTERVENTION: UNAVAILABLE_BY_ACCESS_MODEL,
        }
    evidence_bytes: dict[str, bytes | None] = {}
    evidence_refs: dict[str, ArtifactRef | None] = {}
    for name in CAPABILITY_NAMES:
        if statuses[name] == SUPPORTED_WITH_EVIDENCE:
            body = build_comparison_capability_evidence_body(
                evidence_id=f"capability-{suffix}-{name.lower()}",
                capability_name=name,
                identity=identity,
                configuration_ref=configuration_ref,
            )
            evidence_bytes[name] = body
            evidence_refs[name] = ref(
                f"capability-{suffix}-{name.lower()}",
                body,
                COMPARISON_CAPABILITY_EVIDENCE_MEDIA_TYPE,
            )
        else:
            evidence_bytes[name] = None
            evidence_refs[name] = None
    capabilities = build_comparison_model_capabilities(
        capabilities_id=f"capabilities-{suffix}",
        identity=identity,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        capability_statuses=statuses,
        capability_evidence_refs=evidence_refs,
        capability_evidence_bytes=evidence_bytes,
    )
    return identity, capabilities


@dataclass(frozen=True)
class Fixture:
    open_identity: object
    open_capabilities: object
    closed_identity: object
    closed_capabilities: object
    protocol_ref: ArtifactRef
    roster_ref: ArtifactRef
    direction_ref: ArtifactRef
    direction_bytes: bytes
    coordinate_ref: ArtifactRef
    coordinate_bytes: bytes
    steering_controls: dict[str, ArtifactRef]
    steering_control_bytes: dict[str, bytes]
    black_box_controls: dict[str, ArtifactRef]
    black_box_control_bytes: dict[str, bytes]

    def steering(self, **changes):
        values = {
            "steering_id": "steering-plan-001",
            "phase_id": "comparison-steering-shadow-001",
            "identity": self.open_identity,
            "capabilities": self.open_capabilities,
            "shared_protocol_ref": self.protocol_ref,
            "roster_ref": self.roster_ref,
            "direction_ref": self.direction_ref,
            "direction_bytes": self.direction_bytes,
            "coordinate_ref": self.coordinate_ref,
            "coordinate_bytes": self.coordinate_bytes,
            "target_layer_id": "decoder-layer-18",
            "activation_tensor_name": "residual-post",
            "activation_width": 4096,
            "coordinate_start": 100,
            "coordinate_count": 64,
            "dose_ticks": (0, 100_000, 250_000),
            "control_spec_refs": self.steering_controls,
            "control_spec_bytes": self.steering_control_bytes,
        }
        values.update(changes)
        return build_steering_protocol(**values)


@pytest.fixture
def fx() -> Fixture:
    open_identity, open_capabilities = model_fixture(OPEN_WEIGHT, "10")
    closed_identity, closed_capabilities = model_fixture(CLOSED_WEIGHT, "11")
    protocol_ref = ref(
        "shared-comparison-protocol-001",
        b"shared comparison protocol",
        steering_module.BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
    )
    roster_ref = ref(
        "frozen-comparison-roster-001",
        b"frozen comparison roster",
        FROZEN_COMPARISON_ROSTER_MEDIA_TYPE,
    )
    direction_bytes = build_steering_direction_body(
        direction_id="steering-direction-001",
        identity=open_identity,
        capabilities=open_capabilities,
        discovery_method="JSPACE_REGISTERED_BASIS",
    )
    direction_ref = ref(
        "steering-direction-001", direction_bytes, STEERING_DIRECTION_MEDIA_TYPE
    )
    coordinate_bytes = build_activation_coordinate_body(
        coordinate_id="activation-coordinate-001",
        identity=open_identity,
        capabilities=open_capabilities,
        target_layer_id="decoder-layer-18",
        activation_tensor_name="residual-post",
        activation_width=4096,
        coordinate_start=100,
        coordinate_count=64,
    )
    coordinate_ref = ref(
        "activation-coordinate-001",
        coordinate_bytes,
        ACTIVATION_COORDINATE_MEDIA_TYPE,
    )
    steering_control_bytes = {
        name: build_steering_control_spec_body(
            control_id=f"steering-control-{index:02d}",
            control_name=name,
            identity=open_identity,
            capabilities=open_capabilities,
        )
        for index, name in enumerate(STEERING_CONTROL_NAMES, start=1)
    }
    steering_controls = {
        name: ref(
            f"steering-control-{index:02d}",
            steering_control_bytes[name],
            STEERING_CONTROL_SPEC_MEDIA_TYPE,
        )
        for index, name in enumerate(STEERING_CONTROL_NAMES, start=1)
    }
    black_box_control_bytes = {
        name: build_black_box_control_spec_body(
            control_id=f"black-box-control-{index:02d}",
            control_name=name,
            identity=closed_identity,
            capabilities=closed_capabilities,
        )
        for index, name in enumerate(BLACK_BOX_CONTROL_NAMES, start=1)
    }
    black_box_controls = {
        name: ref(
            f"black-box-control-{index:02d}",
            black_box_control_bytes[name],
            BLACK_BOX_CONTROL_SPEC_MEDIA_TYPE,
        )
        for index, name in enumerate(BLACK_BOX_CONTROL_NAMES, start=1)
    }
    return Fixture(
        open_identity=open_identity,
        open_capabilities=open_capabilities,
        closed_identity=closed_identity,
        closed_capabilities=closed_capabilities,
        protocol_ref=protocol_ref,
        roster_ref=roster_ref,
        direction_ref=direction_ref,
        direction_bytes=direction_bytes,
        coordinate_ref=coordinate_ref,
        coordinate_bytes=coordinate_bytes,
        steering_controls=steering_controls,
        steering_control_bytes=steering_control_bytes,
        black_box_controls=black_box_controls,
        black_box_control_bytes=black_box_control_bytes,
    )


def test_disabled_steering_plan_is_exact_and_non_authoritative(fx: Fixture) -> None:
    plan = fx.steering()
    assert plan.phase_id == "comparison-steering-shadow-001"
    assert plan.dose_ticks == (0, 100_000, 250_000)
    assert plan.capabilities_ref == fx.open_capabilities.artifact_ref
    assert plan.payload["status"] == {
        "scope": "STRUCTURE_ONLY",
        "authority": "NON_AUTHORITY",
    }
    assert plan.payload["boundary"]["intervention"] == "DISABLED"
    assert plan.payload["boundary"]["canary_count"] == 0
    assert plan.payload["boundary"]["authorization"] == (
        "SEPARATE_AUTHORIZATION_REQUIRED"
    )
    replayed = replay_steering_protocol(
        plan,
        identity=fx.open_identity,
        capabilities=fx.open_capabilities,
        direction_bytes=fx.direction_bytes,
        coordinate_bytes=fx.coordinate_bytes,
        control_spec_refs=fx.steering_controls,
        control_spec_bytes=fx.steering_control_bytes,
    )
    assert replayed == plan


@pytest.mark.parametrize(
    "phase_id",
    [
        "stagec-calibration",
        "C-Cal",
        "stagec-c-cal",
        "gate5-stagec-qwen-prompt-injection-v0.1",
        "stagec-calibration-v2",
        "stagec-calibration-steering",
        "gate5-stagec-qwen-prompt-injection-v0.1-steering",
    ],
)
def test_current_stagec_cannot_activate_steering(
    fx: Fixture, phase_id: str
) -> None:
    with pytest.raises(SchemaValidationError, match="Stage C"):
        fx.steering(phase_id=phase_id)


def test_access_kind_and_capability_substitution_fail_closed(fx: Fixture) -> None:
    with pytest.raises(SchemaValidationError, match="OPEN_WEIGHT"):
        fx.steering(
            identity=fx.closed_identity,
            capabilities=fx.closed_capabilities,
        )
    weak_identity, weak_capabilities = model_fixture(
        OPEN_WEIGHT, "12", steering_supported=False
    )
    with pytest.raises(SchemaValidationError, match=STEERING_INTERVENTION):
        fx.steering(identity=weak_identity, capabilities=weak_capabilities)
    no_behavior_identity, no_behavior_capabilities = model_fixture(
        OPEN_WEIGHT,
        "14",
        behavior_supported=False,
    )
    with pytest.raises(SchemaValidationError, match=BEHAVIOR_GENERATION):
        fx.steering(
            identity=no_behavior_identity,
            capabilities=no_behavior_capabilities,
        )
    with pytest.raises(SchemaValidationError, match="CLOSED_WEIGHT"):
        build_black_box_policy_control(
            control_id="wrong-access-black-box",
            identity=fx.open_identity,
            capabilities=fx.open_capabilities,
            shared_protocol_ref=fx.protocol_ref,
            roster_ref=fx.roster_ref,
            control_spec_refs=fx.black_box_controls,
            control_spec_bytes=fx.black_box_control_bytes,
        )


@pytest.mark.parametrize(
    "changes,pattern",
    [
        ({"dose_ticks": (1, 2, 3)}, "start at zero"),
        ({"dose_ticks": (0, 2, 2)}, "increase strictly"),
        ({"dose_ticks": (0, 1)}, "multiple nonzero"),
        ({"activation_width": 0}, "activation_width"),
        ({"coordinate_start": 4096}, "coordinate_start"),
        ({"coordinate_start": 4090, "coordinate_count": 7}, "coordinate_count"),
    ],
)
def test_geometry_and_dose_known_faults_reject(
    fx: Fixture, changes: dict, pattern: str
) -> None:
    with pytest.raises((SchemaValidationError, ValueError), match=pattern):
        fx.steering(**changes)


def test_every_steering_control_is_required_once_and_alias_free(fx: Fixture) -> None:
    missing = dict(fx.steering_controls)
    missing.pop(ACTIVATION_CHANGED)
    with pytest.raises(SchemaValidationError, match="every fixed control"):
        fx.steering(control_spec_refs=missing)

    wrong_order = dict(reversed(tuple(fx.steering_controls.items())))
    with pytest.raises(SchemaValidationError, match="exact order"):
        fx.steering(control_spec_refs=wrong_order)

    alias = dict(fx.steering_controls)
    first, second = STEERING_CONTROL_NAMES[:2]
    alias[second] = alias[first]
    with pytest.raises(SchemaValidationError, match="reuses artifact_id"):
        fx.steering(control_spec_refs=alias)

    swapped_refs = dict(fx.steering_controls)
    swapped_bytes = dict(fx.steering_control_bytes)
    swapped_refs[first], swapped_refs[second] = swapped_refs[second], swapped_refs[first]
    swapped_bytes[first], swapped_bytes[second] = (
        swapped_bytes[second],
        swapped_bytes[first],
    )
    with pytest.raises(SchemaValidationError, match="role or evidence"):
        fx.steering(
            control_spec_refs=swapped_refs,
            control_spec_bytes=swapped_bytes,
        )


def test_direction_and_coordinate_bodies_are_semantically_bound(fx: Fixture) -> None:
    other_direction_bytes = build_steering_direction_body(
        direction_id="steering-direction-other",
        identity=fx.open_identity,
        capabilities=fx.open_capabilities,
        discovery_method="MEAN_DIFFERENCE",
    )
    other_direction_ref = ref(
        "steering-direction-other",
        other_direction_bytes,
        STEERING_DIRECTION_MEDIA_TYPE,
    )
    plan = fx.steering(
        direction_ref=other_direction_ref,
        direction_bytes=other_direction_bytes,
    )
    assert plan.direction_ref == other_direction_ref

    wrong_coordinate_bytes = build_activation_coordinate_body(
        coordinate_id="activation-coordinate-wrong",
        identity=fx.open_identity,
        capabilities=fx.open_capabilities,
        target_layer_id="decoder-layer-17",
        activation_tensor_name="residual-post",
        activation_width=4096,
        coordinate_start=100,
        coordinate_count=64,
    )
    wrong_coordinate_ref = ref(
        "activation-coordinate-wrong",
        wrong_coordinate_bytes,
        ACTIVATION_COORDINATE_MEDIA_TYPE,
    )
    with pytest.raises(SchemaValidationError, match="geometry changed"):
        fx.steering(
            coordinate_ref=wrong_coordinate_ref,
            coordinate_bytes=wrong_coordinate_bytes,
        )


def test_black_box_controls_are_not_activation_steering(fx: Fixture) -> None:
    control = build_black_box_policy_control(
        control_id="closed-policy-control-001",
        identity=fx.closed_identity,
        capabilities=fx.closed_capabilities,
        shared_protocol_ref=fx.protocol_ref,
        roster_ref=fx.roster_ref,
        control_spec_refs=fx.black_box_controls,
        control_spec_bytes=fx.black_box_control_bytes,
    )
    assert control.payload["control_label"] == BLACK_BOX_POLICY_CONTROL
    assert control.payload["boundary"]["internal_activation_access"] == (
        "UNAVAILABLE_BY_ACCESS_MODEL"
    )
    assert control.payload["boundary"]["mechanism_equivalence_claim"] == (
        "FORBIDDEN"
    )
    assert "direction_ref" not in control.payload
    assert replay_black_box_policy_control(
        control,
        identity=fx.closed_identity,
        capabilities=fx.closed_capabilities,
        control_spec_refs=fx.black_box_controls,
        control_spec_bytes=fx.black_box_control_bytes,
    ) == control

    first, second = BLACK_BOX_CONTROL_NAMES[:2]
    swapped_refs = dict(fx.black_box_controls)
    swapped_bytes = dict(fx.black_box_control_bytes)
    swapped_refs[first], swapped_refs[second] = swapped_refs[second], swapped_refs[first]
    swapped_bytes[first], swapped_bytes[second] = (
        swapped_bytes[second],
        swapped_bytes[first],
    )
    with pytest.raises(SchemaValidationError, match="role or evidence"):
        build_black_box_policy_control(
            control_id="closed-policy-control-swapped",
            identity=fx.closed_identity,
            capabilities=fx.closed_capabilities,
            shared_protocol_ref=fx.protocol_ref,
            roster_ref=fx.roster_ref,
            control_spec_refs=swapped_refs,
            control_spec_bytes=swapped_bytes,
        )

    forged = replace(control, byte_length=True)
    with pytest.raises(SchemaValidationError):
        replay_black_box_policy_control(
            forged,
            identity=fx.closed_identity,
            capabilities=fx.closed_capabilities,
            control_spec_refs=fx.black_box_controls,
            control_spec_bytes=fx.black_box_control_bytes,
        )


def test_model_capability_ref_and_payload_mutation_reject(fx: Fixture) -> None:
    plan = fx.steering()
    other_identity, other_capabilities = model_fixture(OPEN_WEIGHT, "13")
    with pytest.raises(SchemaValidationError):
        replay_steering_protocol(
            plan,
            identity=other_identity,
            capabilities=other_capabilities,
            direction_bytes=fx.direction_bytes,
            coordinate_bytes=fx.coordinate_bytes,
            control_spec_refs=fx.steering_controls,
            control_spec_bytes=fx.steering_control_bytes,
        )
    mutable = replace(plan, payload=thaw_json(plan.payload))
    with pytest.raises(SchemaValidationError, match="recursively frozen"):
        replay_steering_protocol(
            mutable,
            identity=fx.open_identity,
            capabilities=fx.open_capabilities,
            direction_bytes=fx.direction_bytes,
            coordinate_bytes=fx.coordinate_bytes,
            control_spec_refs=fx.steering_controls,
            control_spec_bytes=fx.steering_control_bytes,
        )
    forged = replace(plan, raw_bytes=b"{}")
    with pytest.raises(SchemaValidationError):
        build_unavailable_steering_backend(
            steering=forged,
            identity=fx.open_identity,
            capabilities=fx.open_capabilities,
            direction_bytes=fx.direction_bytes,
            coordinate_bytes=fx.coordinate_bytes,
            control_spec_refs=fx.steering_controls,
            control_spec_bytes=fx.steering_control_bytes,
            reason="NO_AUTHORIZED_STEERING_BACKEND",
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"byte_length": True},
        {"dose_ticks": (False, 100_000, 250_000)},
        {"phase_id": "forged-shadow-phase"},
    ],
)
def test_forged_projection_types_and_unavailable_backend_reject(
    fx: Fixture, changes: dict
) -> None:
    plan = fx.steering()
    forged = replace(plan, **changes)
    with pytest.raises(SchemaValidationError):
        replay_steering_protocol(
            forged,
            identity=fx.open_identity,
            capabilities=fx.open_capabilities,
            direction_bytes=fx.direction_bytes,
            coordinate_bytes=fx.coordinate_bytes,
            control_spec_refs=fx.steering_controls,
            control_spec_bytes=fx.steering_control_bytes,
        )
    with pytest.raises(SchemaValidationError):
        build_unavailable_steering_backend(
            steering=forged,
            identity=fx.open_identity,
            capabilities=fx.open_capabilities,
            direction_bytes=fx.direction_bytes,
            coordinate_bytes=fx.coordinate_bytes,
            control_spec_refs=fx.steering_controls,
            control_spec_bytes=fx.steering_control_bytes,
            reason="NO_AUTHORIZED_STEERING_BACKEND",
        )


def test_forged_nested_artifact_ref_type_rejects(fx: Fixture) -> None:
    plan = fx.steering()
    forged_ref = object.__new__(ArtifactRef)
    object.__setattr__(forged_ref, "artifact_id", plan.direction_ref.artifact_id)
    object.__setattr__(forged_ref, "sha256", plan.direction_ref.sha256)
    object.__setattr__(forged_ref, "byte_length", True)
    object.__setattr__(forged_ref, "media_type", plan.direction_ref.media_type)
    forged = replace(plan, direction_ref=forged_ref)
    with pytest.raises(SchemaValidationError, match="forged ArtifactRef"):
        replay_steering_protocol(
            forged,
            identity=fx.open_identity,
            capabilities=fx.open_capabilities,
            direction_bytes=fx.direction_bytes,
            coordinate_bytes=fx.coordinate_bytes,
            control_spec_refs=fx.steering_controls,
            control_spec_bytes=fx.steering_control_bytes,
        )


def test_unavailable_backend_fails_before_input_or_side_effect(
    fx: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def forbidden(*args, **kwargs):
        del args, kwargs
        calls.append("side-effect")
        raise AssertionError("side effect attempted")

    class ExplosiveRequest:
        def __getattribute__(self, name):
            raise AssertionError(f"request inspected: {name}")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    backend = build_unavailable_steering_backend(
        steering=fx.steering(),
        identity=fx.open_identity,
        capabilities=fx.open_capabilities,
        direction_bytes=fx.direction_bytes,
        coordinate_bytes=fx.coordinate_bytes,
        control_spec_refs=fx.steering_controls,
        control_spec_bytes=fx.steering_control_bytes,
        reason="NO_AUTHORIZED_STEERING_BACKEND",
    )
    assert backend.status == BACKEND_UNAVAILABLE
    assert backend.canary_count == 0
    with pytest.raises(
        SteeringBackendUnavailableError,
        match="NO_AUTHORIZED_STEERING_BACKEND",
    ):
        backend.attempt(ExplosiveRequest())
    assert calls == []


def test_unavailable_backend_rejects_construction_copy_pickle_and_forgery(
    fx: Fixture,
) -> None:
    backend = build_unavailable_steering_backend(
        steering=fx.steering(),
        identity=fx.open_identity,
        capabilities=fx.open_capabilities,
        direction_bytes=fx.direction_bytes,
        coordinate_bytes=fx.coordinate_bytes,
        control_spec_refs=fx.steering_controls,
        control_spec_bytes=fx.steering_control_bytes,
        reason="UNAVAILABLE",
    )
    for operation in (
        lambda: copy.copy(backend),
        lambda: copy.deepcopy(backend),
        lambda: pickle.dumps(backend),
        lambda: copy.replace(backend),
    ):
        with pytest.raises(TypeError):
            operation()
    with pytest.raises(TypeError, match="factory-only"):
        UnavailableSteeringBackend()
    with pytest.raises(TypeError, match="cannot be subclassed"):

        class ForgedSubclass(UnavailableSteeringBackend):
            pass

    forged = object.__new__(UnavailableSteeringBackend)
    with pytest.raises(SchemaValidationError, match="factory-sealed"):
        _ = forged.status


def test_public_api_is_literal_unique_and_resolvable() -> None:
    assert type(steering_module.__all__) is tuple
    assert len(steering_module.__all__) == len(set(steering_module.__all__))
    for name in steering_module.__all__:
        assert getattr(steering_module, name) is not None
