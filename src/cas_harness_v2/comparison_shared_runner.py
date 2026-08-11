"""Replay-only runner for one frozen open-versus-closed comparison roster.

The runner consumes only exact public :class:`ReplayBehavioralAdapter`
instances.  It has no live/provider adapter, performs no external I/O, spends
nothing, and produces no verdict or composite metric.  A returned artifact is
only a canonical association of two complete local replay streams.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ._strict_json import (
    canonical_json_bytes,
    freeze_json,
    load_json_object,
    mapping_proxy_backing_dict,
    sha256_bytes,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    parse_artifact_ref,
)
from .comparison_adapters import (
    BEHAVIORAL_ADAPTER_AUTHORITY,
    BEHAVIORAL_ADAPTER_STATUS,
    BEHAVIORAL_REPLAY_MODE,
    BehavioralAdapterBinding,
    BehavioralCaseInput,
    ReplayBehavioralAdapter,
)
from .comparison_model_protocol import (
    NON_AUTHORITY,
    OBSERVED,
    STRUCTURE_ONLY,
    BehavioralObservationArtifact,
    ComparisonModelCapabilitiesArtifact,
    ComparisonModelIdentityArtifact,
    replay_behavioral_observation,
    replay_comparison_model_capabilities,
)
from .comparison_shared_protocol import (
    CLOSED,
    OPEN,
    FrozenComparisonRosterArtifact,
    SharedComparisonProtocolArtifact,
    replay_frozen_comparison_roster,
    replay_shared_comparison_protocol,
)


SHARED_BEHAVIORAL_REPLAY_SCHEMA = "cas_harness_v2.shared_behavioral_replay.v1"
SHARED_BEHAVIORAL_REPLAY_MEDIA_TYPE = (
    "application/vnd.cas-harness.shared-behavioral-replay-v1+json"
)

__all__ = (
    "SHARED_BEHAVIORAL_REPLAY_SCHEMA",
    "SHARED_BEHAVIORAL_REPLAY_MEDIA_TYPE",
    "SharedBehavioralReplayValidationError",
    "SharedBehavioralReplayFailure",
    "SharedBehavioralReplayPair",
    "SharedBehavioralReplayArtifact",
    "build_shared_behavioral_replay_artifact",
    "load_shared_behavioral_replay_artifact",
    "replay_shared_behavioral_replay_artifact",
    "run_shared_behavioral_replay",
)

_STATUS = MappingProxyType({"scope": STRUCTURE_ONLY, "authority": NON_AUTHORITY})
_BOUNDARY = MappingProxyType({
    "local_replay": "PERFORMED",
    "live_execution": "NOT_PERFORMED",
    "execution_authority": "NOT_GRANTED",
    "provider_calls": 0,
    "model_calls": 0,
    "network_calls": 0,
    "filesystem_calls": 0,
    "spend_actions": 0,
})


class SharedBehavioralReplayValidationError(SchemaValidationError):
    """Raised when a shared replay artifact violates its closed schema."""


class SharedBehavioralReplayFailure(RuntimeError):
    """A deterministic local replay failure that produced no artifact."""


@dataclass(frozen=True, slots=True)
class SharedBehavioralReplayPair:
    execution_ordinal: int
    case_id: str
    case_ref: ArtifactRef
    open_observation: BehavioralObservationArtifact
    closed_observation: BehavioralObservationArtifact


@dataclass(frozen=True, slots=True)
class SharedBehavioralReplayArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    replay_id: str
    protocol: SharedComparisonProtocolArtifact
    roster: FrozenComparisonRosterArtifact
    open_capabilities: ComparisonModelCapabilitiesArtifact
    closed_capabilities: ComparisonModelCapabilitiesArtifact
    pairs: tuple[SharedBehavioralReplayPair, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.replay_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=SHARED_BEHAVIORAL_REPLAY_MEDIA_TYPE,
        )


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    reference = _require_ref(reference, "artifact_ref")
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _require_ref(value: Any, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise SharedBehavioralReplayValidationError(
            f"{path} must be an exact ArtifactRef"
        )
    if (
        type(value.artifact_id) is not str
        or type(value.sha256) is not str
        or type(value.byte_length) is not int
        or type(value.media_type) is not str
    ):
        raise SharedBehavioralReplayValidationError(
            f"{path} fields must use exact immutable scalar types"
        )
    return value


def _canonical_object(raw: Any, path: str) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise SharedBehavioralReplayValidationError(
                f"{path} must use exact canonical JSON bytes"
            )
        return snapshot, value
    except SharedBehavioralReplayValidationError:
        raise
    except (TypeError, ValueError) as exc:
        raise SharedBehavioralReplayValidationError(f"{path}: {exc}") from exc


def _require_frozen_json(value: Any, path: str) -> None:
    if type(value) is MappingProxyType:
        backing = mapping_proxy_backing_dict(value)
        if backing is None:
            raise SharedBehavioralReplayValidationError(
                f"{path} mapping proxy must wrap an exact dict"
            )
        for key, child in backing.items():
            if type(key) is not str:
                raise SharedBehavioralReplayValidationError(
                    f"{path} keys must be exact strings"
                )
            _require_frozen_json(child, f"{path}.{key}")
        return
    if type(value) is tuple:
        for index, child in enumerate(value):
            _require_frozen_json(child, f"{path}[{index}]")
        return
    if type(value) in (str, int, bool) or value is None:
        return
    raise SharedBehavioralReplayValidationError(
        f"{path} must be recursively frozen canonical JSON"
    )


def _require_status_and_boundary(value: dict[str, Any]) -> None:
    status = expect_object(value["status"], "$.status")
    expect_keys(status, required=_STATUS, path="$.status")
    if status != _STATUS:
        raise SharedBehavioralReplayValidationError(
            "shared replay status must remain STRUCTURE_ONLY/NON_AUTHORITY"
        )
    boundary = expect_object(value["boundary"], "$.boundary")
    expect_keys(boundary, required=_BOUNDARY, path="$.boundary")
    if boundary != _BOUNDARY:
        raise SharedBehavioralReplayValidationError(
            "shared replay boundary cannot claim external calls, spend, or authority"
        )


def _unique_ref_closure(
    references: tuple[ArtifactRef, ...], path: str
) -> tuple[ArtifactRef, ...]:
    by_id: dict[str, ArtifactRef] = {}
    by_content: dict[tuple[str, int], ArtifactRef] = {}
    ordered: list[ArtifactRef] = []
    for index, reference in enumerate(references):
        reference = _require_ref(reference, f"{path}[{index}]")
        prior = by_id.get(reference.artifact_id)
        if prior is not None:
            if prior != reference:
                raise SharedBehavioralReplayValidationError(
                    f"{path} reuses one artifact identity for different content"
                )
            continue
        content = (reference.sha256, reference.byte_length)
        if content in by_content:
            raise SharedBehavioralReplayValidationError(
                f"{path} duplicates one content identity under different artifact IDs"
            )
        by_id[reference.artifact_id] = reference
        by_content[content] = reference
        ordered.append(reference)
    return tuple(ordered)


def _require_distinct_role_refs(
    references: tuple[ArtifactRef, ...], *, path: str
) -> None:
    if len(_unique_ref_closure(references, path)) != len(references):
        raise SharedBehavioralReplayValidationError(
            f"{path} cannot reuse one artifact across distinct replay roles"
        )


def _validate_capabilities(
    capabilities: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    role: str,
) -> ComparisonModelCapabilitiesArtifact:
    if type(capabilities) is not ComparisonModelCapabilitiesArtifact:
        raise SharedBehavioralReplayValidationError(
            f"{role} capabilities must have the exact artifact type"
        )
    try:
        replayed = replay_comparison_model_capabilities(
            capabilities,
            identity=identity,
        )
    except Exception as exc:
        raise SharedBehavioralReplayValidationError(
            f"{role} capabilities fail exact replay: {exc}"
        ) from exc
    if replayed != capabilities:
        raise SharedBehavioralReplayValidationError(
            f"{role} capabilities differ from exact replay"
        )
    if (
        capabilities.identity_ref != identity.artifact_ref
        or capabilities.configuration_ref != configuration_ref
        or capabilities.access_kind != identity.access_kind
        or capabilities.provider != identity.provider
        or capabilities.model_id != identity.model_id
        or capabilities.revision != identity.revision
    ):
        raise SharedBehavioralReplayValidationError(
            f"{role} capabilities differ from the exact model/configuration binding"
        )
    return replayed


def _validate_observation(
    observation: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    protocol_ref: ArtifactRef,
    case_input: BehavioralCaseInput,
    role: str,
) -> BehavioralObservationArtifact:
    if type(observation) is not BehavioralObservationArtifact:
        raise SharedBehavioralReplayValidationError(
            f"{role} observation must have the exact artifact type"
        )
    try:
        replayed = replay_behavioral_observation(
            observation,
            identity=identity,
            configuration_ref=configuration_ref,
            protocol_ref=protocol_ref,
            case_id=case_input.case_id,
            case_ref=case_input.case_ref,
        )
    except Exception as exc:
        raise SharedBehavioralReplayValidationError(
            f"{role} observation fails exact bound replay: {exc}"
        ) from exc
    if replayed != observation or replayed.observation_status != OBSERVED:
        raise SharedBehavioralReplayValidationError(
            f"{role} observation must be exact OBSERVED replay evidence"
        )
    return replayed


def _validate_cases(
    supplied: Any,
    *,
    expected: tuple[BehavioralCaseInput, ...],
    role: str,
) -> tuple[BehavioralCaseInput, ...]:
    if type(supplied) is not tuple or len(supplied) != len(expected):
        raise SharedBehavioralReplayValidationError(
            f"{role} cases must be the complete exact roster"
        )
    seen_ids: set[str] = set()
    seen_refs: set[ArtifactRef] = set()
    for ordinal, (actual, projected) in enumerate(
        zip(supplied, expected, strict=True), start=1
    ):
        if type(actual) is not BehavioralCaseInput:
            raise SharedBehavioralReplayValidationError(
                f"{role} cases must contain exact BehavioralCaseInput values"
            )
        if actual != projected or actual.execution_ordinal != ordinal:
            raise SharedBehavioralReplayValidationError(
                f"{role} case is missing, duplicated, substituted, or out of order"
            )
        if actual.case_id in seen_ids or actual.case_ref in seen_refs:
            raise SharedBehavioralReplayValidationError(
                f"{role} cases contain duplicate identifiers or references"
            )
        seen_ids.add(actual.case_id)
        seen_refs.add(actual.case_ref)
    return supplied


def _validate_replay_inputs(
    *,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    open_observations: tuple[BehavioralObservationArtifact, ...],
    closed_observations: tuple[BehavioralObservationArtifact, ...],
) -> tuple[
    SharedComparisonProtocolArtifact,
    FrozenComparisonRosterArtifact,
    ComparisonModelCapabilitiesArtifact,
    ComparisonModelCapabilitiesArtifact,
    tuple[SharedBehavioralReplayPair, ...],
    tuple[ArtifactRef, ...],
]:
    protocol = replay_shared_comparison_protocol(protocol)
    roster = replay_frozen_comparison_roster(roster)
    if roster.protocol != protocol:
        raise SharedBehavioralReplayValidationError(
            "roster differs from the exact shared protocol"
        )
    open_capabilities = _validate_capabilities(
        open_capabilities,
        identity=protocol.open_identity,
        configuration_ref=protocol.open_configuration_ref,
        role=OPEN,
    )
    closed_capabilities = _validate_capabilities(
        closed_capabilities,
        identity=protocol.closed_identity,
        configuration_ref=protocol.closed_configuration_ref,
        role=CLOSED,
    )
    if type(open_observations) is not tuple or type(closed_observations) is not tuple:
        raise SharedBehavioralReplayValidationError(
            "OPEN and CLOSED observations must be exact tuples"
        )
    case_count = len(roster.cases)
    if (
        case_count == 0
        or len(open_observations) != case_count
        or len(closed_observations) != case_count
    ):
        raise SharedBehavioralReplayValidationError(
            "OPEN and CLOSED observations must match the complete roster count"
        )
    open_cases = roster.adapter_cases(OPEN)
    closed_cases = roster.adapter_cases(CLOSED)
    pairs: list[SharedBehavioralReplayPair] = []
    role_refs: list[ArtifactRef] = [
        open_capabilities.artifact_ref,
        closed_capabilities.artifact_ref,
    ]
    role_refs.extend(
        capability.evidence_ref
        for capabilities in (open_capabilities, closed_capabilities)
        for capability in capabilities.capabilities
        if capability.evidence_ref is not None
    )
    for ordinal, (case, open_observation, closed_observation) in enumerate(
        zip(roster.cases, open_observations, closed_observations, strict=True),
        start=1,
    ):
        open_observation = _validate_observation(
            open_observation,
            identity=protocol.open_identity,
            configuration_ref=protocol.open_configuration_ref,
            protocol_ref=protocol.artifact_ref,
            case_input=open_cases[ordinal - 1],
            role=OPEN,
        )
        closed_observation = _validate_observation(
            closed_observation,
            identity=protocol.closed_identity,
            configuration_ref=protocol.closed_configuration_ref,
            protocol_ref=protocol.artifact_ref,
            case_input=closed_cases[ordinal - 1],
            role=CLOSED,
        )
        pair = SharedBehavioralReplayPair(
            execution_ordinal=ordinal,
            case_id=case.case_id,
            case_ref=case.artifact_ref,
            open_observation=open_observation,
            closed_observation=closed_observation,
        )
        pairs.append(pair)
        for observation in (open_observation, closed_observation):
            role_refs.append(observation.artifact_ref)
            if observation.raw_response_ref is not None:
                role_refs.append(observation.raw_response_ref)
            if observation.raw_tool_calls_ref is not None:
                role_refs.append(observation.raw_tool_calls_ref)
    _require_distinct_role_refs(tuple(role_refs), path="shared replay result roles")
    dependencies = _unique_ref_closure(
        (
            protocol.artifact_ref,
            *protocol.artifact_refs,
            roster.artifact_ref,
            *roster.artifact_refs,
            open_capabilities.artifact_ref,
            *open_capabilities.artifact_refs,
            closed_capabilities.artifact_ref,
            *closed_capabilities.artifact_refs,
            *(
                reference
                for pair in pairs
                for observation in (
                    pair.open_observation,
                    pair.closed_observation,
                )
                for reference in (
                    observation.artifact_ref,
                    *observation.artifact_refs,
                )
            ),
        ),
        "shared replay artifact closure",
    )
    return (
        protocol,
        roster,
        open_capabilities,
        closed_capabilities,
        tuple(pairs),
        dependencies,
    )


def _observation_value(
    observation: BehavioralObservationArtifact,
) -> dict[str, Any]:
    return {
        "observation_ref": _artifact_ref_value(observation.artifact_ref),
        "raw_response_ref": (
            None
            if observation.raw_response_ref is None
            else _artifact_ref_value(observation.raw_response_ref)
        ),
        "raw_tool_calls_ref": (
            None
            if observation.raw_tool_calls_ref is None
            else _artifact_ref_value(observation.raw_tool_calls_ref)
        ),
    }


def _artifact_value(
    *,
    replay_id: str,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    pairs: tuple[SharedBehavioralReplayPair, ...],
) -> dict[str, Any]:
    return {
        "schema": SHARED_BEHAVIORAL_REPLAY_SCHEMA,
        "replay_id": replay_id,
        "protocol_ref": _artifact_ref_value(protocol.artifact_ref),
        "roster_ref": _artifact_ref_value(roster.artifact_ref),
        "models": [
            {
                "role": OPEN,
                "identity_ref": _artifact_ref_value(protocol.open_identity.artifact_ref),
                "capabilities_ref": _artifact_ref_value(
                    open_capabilities.artifact_ref
                ),
                "configuration_ref": _artifact_ref_value(
                    protocol.open_configuration_ref
                ),
            },
            {
                "role": CLOSED,
                "identity_ref": _artifact_ref_value(
                    protocol.closed_identity.artifact_ref
                ),
                "capabilities_ref": _artifact_ref_value(
                    closed_capabilities.artifact_ref
                ),
                "configuration_ref": _artifact_ref_value(
                    protocol.closed_configuration_ref
                ),
            },
        ],
        "pairs": [
            {
                "execution_ordinal": pair.execution_ordinal,
                "case_id": pair.case_id,
                "case_ref": _artifact_ref_value(pair.case_ref),
                "open_observation": _observation_value(pair.open_observation),
                "closed_observation": _observation_value(pair.closed_observation),
            }
            for pair in pairs
        ],
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _validate_body_shape(value: dict[str, Any]) -> None:
    expect_keys(
        value,
        required={
            "schema", "replay_id", "protocol_ref", "roster_ref", "models", "pairs",
            "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != SHARED_BEHAVIORAL_REPLAY_SCHEMA:
        raise SharedBehavioralReplayValidationError("shared replay schema drifted")
    expect_machine_id(value["replay_id"], "$.replay_id")
    parse_artifact_ref(value["protocol_ref"], "$.protocol_ref")
    parse_artifact_ref(value["roster_ref"], "$.roster_ref")
    models = expect_list(value["models"], "$.models")
    if len(models) != 2:
        raise SharedBehavioralReplayValidationError(
            "$.models must contain exactly OPEN then CLOSED"
        )
    for index, model in enumerate(models):
        model = expect_object(model, f"$.models[{index}]")
        expect_keys(
            model,
            required={"role", "identity_ref", "capabilities_ref", "configuration_ref"},
            path=f"$.models[{index}]",
        )
        for name in ("identity_ref", "capabilities_ref", "configuration_ref"):
            parse_artifact_ref(model[name], f"$.models[{index}].{name}")
    pairs = expect_list(value["pairs"], "$.pairs")
    for index, pair in enumerate(pairs):
        pair = expect_object(pair, f"$.pairs[{index}]")
        expect_keys(
            pair,
            required={
                "execution_ordinal", "case_id", "case_ref", "open_observation",
                "closed_observation",
            },
            path=f"$.pairs[{index}]",
        )
        expect_int(pair["execution_ordinal"], f"$.pairs[{index}].execution_ordinal", minimum=1)
        expect_machine_id(pair["case_id"], f"$.pairs[{index}].case_id")
        parse_artifact_ref(pair["case_ref"], f"$.pairs[{index}].case_ref")
        for role in ("open_observation", "closed_observation"):
            observation = expect_object(pair[role], f"$.pairs[{index}].{role}")
            expect_keys(
                observation,
                required={"observation_ref", "raw_response_ref", "raw_tool_calls_ref"},
                path=f"$.pairs[{index}].{role}",
            )
            parse_artifact_ref(
                observation["observation_ref"],
                f"$.pairs[{index}].{role}.observation_ref",
            )
            for name in ("raw_response_ref", "raw_tool_calls_ref"):
                if observation[name] is not None:
                    parse_artifact_ref(
                        observation[name], f"$.pairs[{index}].{role}.{name}"
                    )
    _require_status_and_boundary(value)


def _load_shared_behavioral_replay_artifact(
    raw: Any,
    *,
    replay_ref: ArtifactRef,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    open_observations: tuple[BehavioralObservationArtifact, ...],
    closed_observations: tuple[BehavioralObservationArtifact, ...],
) -> SharedBehavioralReplayArtifact:
    snapshot, value = _canonical_object(raw, "shared behavioral replay")
    replay_ref = _require_ref(replay_ref, "replay_ref")
    if replay_ref.media_type != SHARED_BEHAVIORAL_REPLAY_MEDIA_TYPE:
        raise SharedBehavioralReplayValidationError(
            "replay_ref uses the wrong shared replay media type"
        )
    if not replay_ref.verify_bytes(snapshot):
        raise SharedBehavioralReplayValidationError(
            "shared replay bytes differ from the exact replay reference"
        )
    _validate_body_shape(value)
    replay_id = expect_machine_id(value["replay_id"], "$.replay_id")
    if replay_id != replay_ref.artifact_id:
        raise SharedBehavioralReplayValidationError(
            "replay_id differs from the exact replay reference"
        )
    (
        protocol,
        roster,
        open_capabilities,
        closed_capabilities,
        pairs,
        dependencies,
    ) = _validate_replay_inputs(
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        open_observations=open_observations,
        closed_observations=closed_observations,
    )
    expected = _artifact_value(
        replay_id=replay_id,
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        pairs=pairs,
    )
    if value != expected:
        raise SharedBehavioralReplayValidationError(
            "shared replay differs from its exact caller-bound projection"
        )
    _unique_ref_closure((replay_ref, *dependencies), "shared replay owner closure")
    return SharedBehavioralReplayArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        replay_id=replay_id,
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        pairs=pairs,
        payload=freeze_json(value),
        artifact_refs=dependencies,
    )


def build_shared_behavioral_replay_artifact(
    *,
    replay_id: str,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    open_observations: tuple[BehavioralObservationArtifact, ...],
    closed_observations: tuple[BehavioralObservationArtifact, ...],
) -> SharedBehavioralReplayArtifact:
    """Build a canonical association of two complete local replay streams."""

    replay_id = expect_machine_id(replay_id, "replay_id")
    (
        protocol,
        roster,
        open_capabilities,
        closed_capabilities,
        pairs,
        _,
    ) = _validate_replay_inputs(
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        open_observations=open_observations,
        closed_observations=closed_observations,
    )
    raw = canonical_json_bytes(
        _artifact_value(
            replay_id=replay_id,
            protocol=protocol,
            roster=roster,
            open_capabilities=open_capabilities,
            closed_capabilities=closed_capabilities,
            pairs=pairs,
        )
    )
    replay_ref = ArtifactRef(
        artifact_id=replay_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=SHARED_BEHAVIORAL_REPLAY_MEDIA_TYPE,
    )
    return _load_shared_behavioral_replay_artifact(
        raw,
        replay_ref=replay_ref,
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        open_observations=open_observations,
        closed_observations=closed_observations,
    )


def load_shared_behavioral_replay_artifact(
    raw: bytes | bytearray | memoryview,
    *,
    replay_ref: ArtifactRef,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    open_observations: tuple[BehavioralObservationArtifact, ...],
    closed_observations: tuple[BehavioralObservationArtifact, ...],
) -> SharedBehavioralReplayArtifact:
    """Load canonical replay bytes against every exact caller dependency."""

    return _load_shared_behavioral_replay_artifact(
        raw,
        replay_ref=replay_ref,
        protocol=protocol,
        roster=roster,
        open_capabilities=open_capabilities,
        closed_capabilities=closed_capabilities,
        open_observations=open_observations,
        closed_observations=closed_observations,
    )


def replay_shared_behavioral_replay_artifact(
    artifact: SharedBehavioralReplayArtifact,
) -> SharedBehavioralReplayArtifact:
    """Freshly replay one immutable shared behavioral replay projection."""

    if type(artifact) is not SharedBehavioralReplayArtifact:
        raise SharedBehavioralReplayValidationError(
            "artifact must be an exact SharedBehavioralReplayArtifact"
        )
    if (
        type(artifact.raw_bytes) is not bytes
        or type(artifact.sha256) is not str
        or type(artifact.byte_length) is not int
        or type(artifact.replay_id) is not str
        or type(artifact.pairs) is not tuple
        or type(artifact.artifact_refs) is not tuple
    ):
        raise SharedBehavioralReplayValidationError(
            "shared replay projections must use exact immutable types"
        )
    _require_frozen_json(artifact.payload, "artifact.payload")
    for index, pair in enumerate(artifact.pairs):
        if (
            type(pair) is not SharedBehavioralReplayPair
            or type(pair.execution_ordinal) is not int
            or type(pair.case_id) is not str
        ):
            raise SharedBehavioralReplayValidationError(
                f"artifact.pairs[{index}] uses a forged projection type"
            )
    for index, reference in enumerate(artifact.artifact_refs):
        _require_ref(reference, f"artifact.artifact_refs[{index}]")
    replayed = _load_shared_behavioral_replay_artifact(
        artifact.raw_bytes,
        replay_ref=artifact.artifact_ref,
        protocol=artifact.protocol,
        roster=artifact.roster,
        open_capabilities=artifact.open_capabilities,
        closed_capabilities=artifact.closed_capabilities,
        open_observations=tuple(
            pair.open_observation for pair in artifact.pairs
        ),
        closed_observations=tuple(
            pair.closed_observation for pair in artifact.pairs
        ),
    )
    if replayed != artifact:
        raise SharedBehavioralReplayValidationError(
            "shared replay differs from fresh exact-byte replay"
        )
    return replayed


def _validate_public_adapter(
    adapter: Any,
    *,
    cases: tuple[BehavioralCaseInput, ...],
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    protocol_ref: ArtifactRef,
    role: str,
) -> ReplayBehavioralAdapter:
    if type(adapter) is not ReplayBehavioralAdapter:
        raise SharedBehavioralReplayValidationError(
            f"{role} adapter must be an exact public ReplayBehavioralAdapter"
        )
    try:
        if (
            adapter.adapter_mode != BEHAVIORAL_REPLAY_MODE
            or adapter.status != BEHAVIORAL_ADAPTER_STATUS
            or adapter.authority != BEHAVIORAL_ADAPTER_AUTHORITY
        ):
            raise SharedBehavioralReplayValidationError(
                f"{role} adapter crossed the replay-only non-authority boundary"
            )
        binding = adapter.binding
        expected_binding = BehavioralAdapterBinding(
            identity_ref=identity.artifact_ref,
            capabilities_ref=capabilities.artifact_ref,
            configuration_ref=configuration_ref,
            protocol_ref=protocol_ref,
        )
        if type(binding) is not BehavioralAdapterBinding or binding != expected_binding:
            raise SharedBehavioralReplayValidationError(
                f"{role} adapter differs from the exact identity, capabilities, "
                "configuration, or protocol binding"
            )
        if (
            adapter.case_count != len(cases)
            or adapter.consumed_case_count != 0
            or adapter.complete
        ):
            raise SharedBehavioralReplayValidationError(
                f"{role} adapter must be untouched and match the complete roster"
            )
    except SharedBehavioralReplayValidationError:
        raise
    except Exception as exc:
        raise SharedBehavioralReplayValidationError(
            f"{role} adapter public replay state is invalid: {exc}"
        ) from exc
    return adapter


def run_shared_behavioral_replay(
    *,
    replay_id: str,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
    open_capabilities: ComparisonModelCapabilitiesArtifact,
    closed_capabilities: ComparisonModelCapabilitiesArtifact,
    open_adapter: ReplayBehavioralAdapter,
    closed_adapter: ReplayBehavioralAdapter,
    open_cases: tuple[BehavioralCaseInput, ...],
    closed_cases: tuple[BehavioralCaseInput, ...],
) -> SharedBehavioralReplayArtifact:
    """Consume two complete public replay adapters and bind their exact rows.

    The OPEN adapter is consumed first, followed by the CLOSED adapter.  If
    either public replay fails, this function raises a deterministic local
    failure and constructs no artifact.  The earlier adapter may remain locally
    consumed; no external action or authority follows from that state.
    """

    replay_id = expect_machine_id(replay_id, "replay_id")
    protocol = replay_shared_comparison_protocol(protocol)
    roster = replay_frozen_comparison_roster(roster)
    if roster.protocol != protocol:
        raise SharedBehavioralReplayValidationError(
            "roster differs from the exact shared protocol"
        )
    open_cases = _validate_cases(
        open_cases,
        expected=roster.adapter_cases(OPEN),
        role=OPEN,
    )
    closed_cases = _validate_cases(
        closed_cases,
        expected=roster.adapter_cases(CLOSED),
        role=CLOSED,
    )
    if tuple(
        (case.execution_ordinal, case.case_id, case.case_ref, case.protocol_ref)
        for case in open_cases
    ) != tuple(
        (case.execution_ordinal, case.case_id, case.case_ref, case.protocol_ref)
        for case in closed_cases
    ):
        raise SharedBehavioralReplayValidationError(
            "OPEN and CLOSED adapters must use the same label-free case sequence"
        )
    open_capabilities = _validate_capabilities(
        open_capabilities,
        identity=protocol.open_identity,
        configuration_ref=protocol.open_configuration_ref,
        role=OPEN,
    )
    closed_capabilities = _validate_capabilities(
        closed_capabilities,
        identity=protocol.closed_identity,
        configuration_ref=protocol.closed_configuration_ref,
        role=CLOSED,
    )
    known_references = _unique_ref_closure(
        (
            protocol.artifact_ref,
            *protocol.artifact_refs,
            roster.artifact_ref,
            *roster.artifact_refs,
            open_capabilities.artifact_ref,
            *open_capabilities.artifact_refs,
            closed_capabilities.artifact_ref,
            *closed_capabilities.artifact_refs,
        ),
        "shared runner preflight closure",
    )
    if replay_id in {reference.artifact_id for reference in known_references}:
        raise SharedBehavioralReplayValidationError(
            "replay_id collides with a frozen dependency artifact identity"
        )
    if open_adapter is closed_adapter:
        raise SharedBehavioralReplayValidationError(
            "OPEN and CLOSED must use two distinct replay adapters"
        )
    open_adapter = _validate_public_adapter(
        open_adapter,
        cases=open_cases,
        identity=protocol.open_identity,
        capabilities=open_capabilities,
        configuration_ref=protocol.open_configuration_ref,
        protocol_ref=protocol.artifact_ref,
        role=OPEN,
    )
    closed_adapter = _validate_public_adapter(
        closed_adapter,
        cases=closed_cases,
        identity=protocol.closed_identity,
        capabilities=closed_capabilities,
        configuration_ref=protocol.closed_configuration_ref,
        protocol_ref=protocol.artifact_ref,
        role=CLOSED,
    )
    try:
        open_observations = open_adapter.replay_all(open_cases)
    except Exception as exc:
        raise SharedBehavioralReplayFailure(
            "LOCAL_REPLAY_FAILURE:OPEN:NO_ARTIFACT"
        ) from exc
    try:
        closed_observations = closed_adapter.replay_all(closed_cases)
    except Exception as exc:
        raise SharedBehavioralReplayFailure(
            "LOCAL_REPLAY_FAILURE:CLOSED:NO_ARTIFACT"
        ) from exc
    try:
        open_adapter.require_complete()
        closed_adapter.require_complete()
        return build_shared_behavioral_replay_artifact(
            replay_id=replay_id,
            protocol=protocol,
            roster=roster,
            open_capabilities=open_capabilities,
            closed_capabilities=closed_capabilities,
            open_observations=open_observations,
            closed_observations=closed_observations,
        )
    except Exception as exc:
        raise SharedBehavioralReplayFailure(
            "LOCAL_REPLAY_FAILURE:VALIDATION:NO_ARTIFACT"
        ) from exc
