"""Side-effect-free behavioral replay boundaries for model comparisons.

This module deliberately provides no live/provider adapter.  A replay adapter
can only return canonical observations supplied to its factory, in the exact
frozen case order, once.  The unavailable adapter always stops before it
examines a case or changes local state.
"""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Any, NoReturn
from weakref import WeakKeyDictionary

from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_int,
    expect_machine_id,
    expect_string,
)
from .comparison_model_protocol import (
    ACTIVATION_CAPTURE,
    BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
    BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
    CLOSED_WEIGHT,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    HIDDEN_STATE_OBSERVATION,
    NON_AUTHORITY,
    OBSERVED,
    REPLAY,
    STEERING_INTERVENTION,
    STRUCTURE_ONLY,
    UNAVAILABLE_BY_ACCESS_MODEL,
    UNAVAILABLE,
    BehavioralObservationArtifact,
    ComparisonModelCapabilitiesArtifact,
    ComparisonModelIdentityArtifact,
    replay_behavioral_observation,
    replay_comparison_model_capabilities,
    replay_comparison_model_identity,
)


BEHAVIORAL_ADAPTER_STATUS = STRUCTURE_ONLY
BEHAVIORAL_ADAPTER_AUTHORITY = NON_AUTHORITY
BEHAVIORAL_REPLAY_MODE = REPLAY


class BehavioralAdapterError(RuntimeError):
    """Base error for the non-live behavioral adapter boundary."""


class BehavioralAdapterUnavailableError(BehavioralAdapterError):
    """No behavioral adapter is available at this boundary."""


@dataclass(frozen=True, slots=True)
class BehavioralCaseInput:
    """One label-free, artifact-bound input in an ordered behavioral roster.

    A ground-truth label, prediction, detector result, or hidden-state carrier
    has no field in this type.  The adapter sees only the case identity and the
    exact configuration/protocol references required to replay its observation.
    """

    execution_ordinal: int
    case_id: str
    case_ref: ArtifactRef
    configuration_ref: ArtifactRef
    protocol_ref: ArtifactRef

    def __post_init__(self) -> None:
        expect_int(
            self.execution_ordinal,
            "BehavioralCaseInput.execution_ordinal",
            minimum=1,
        )
        expect_machine_id(self.case_id, "BehavioralCaseInput.case_id")
        _require_ref(self.case_ref, "BehavioralCaseInput.case_ref")
        _require_ref_media(
            self.case_ref,
            BEHAVIORAL_COMPARISON_CASE_MEDIA_TYPE,
            "BehavioralCaseInput.case_ref",
        )
        _require_ref(
            self.configuration_ref,
            "BehavioralCaseInput.configuration_ref",
        )
        _require_ref_media(
            self.configuration_ref,
            COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
            "BehavioralCaseInput.configuration_ref",
        )
        _require_ref(self.protocol_ref, "BehavioralCaseInput.protocol_ref")
        _require_ref_media(
            self.protocol_ref,
            BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
            "BehavioralCaseInput.protocol_ref",
        )
        _require_distinct_refs(
            (
                ("case_ref", self.case_ref),
                ("configuration_ref", self.configuration_ref),
                ("protocol_ref", self.protocol_ref),
            ),
            path="BehavioralCaseInput",
        )


@dataclass(frozen=True, slots=True)
class _ReplayRowSeal:
    case_input: BehavioralCaseInput
    case_signature: tuple[Any, ...]
    observation: BehavioralObservationArtifact
    observation_signature: tuple[Any, ...]


@dataclass(slots=True)
class _ReplayAdapterSeal:
    identity: ComparisonModelIdentityArtifact
    identity_signature: tuple[Any, ...]
    capabilities: ComparisonModelCapabilitiesArtifact
    capabilities_signature: tuple[Any, ...]
    configuration_ref: ArtifactRef
    protocol_ref: ArtifactRef
    rows: tuple[_ReplayRowSeal, ...]
    artifact_closure_signature: tuple[tuple[Any, ...], ...]
    cursor: int
    lock: threading.RLock


@dataclass(frozen=True, slots=True)
class _UnavailableAdapterSeal:
    identity: ComparisonModelIdentityArtifact
    identity_signature: tuple[Any, ...]
    capabilities: ComparisonModelCapabilitiesArtifact
    capabilities_signature: tuple[Any, ...]
    configuration_ref: ArtifactRef
    protocol_ref: ArtifactRef
    artifact_closure_signature: tuple[tuple[Any, ...], ...]
    reason: str


_SEALS_LOCK = threading.RLock()
_REPLAY_SEALS: WeakKeyDictionary[Any, _ReplayAdapterSeal] = WeakKeyDictionary()
_UNAVAILABLE_SEALS: WeakKeyDictionary[Any, _UnavailableAdapterSeal] = (
    WeakKeyDictionary()
)


def _reject_direct_construction(name: str) -> NoReturn:
    raise TypeError(f"{name} is factory-only")


def _reject_duplication(name: str) -> NoReturn:
    raise TypeError(f"{name} cannot be copied, replaced, or pickled")


class ReplayBehavioralAdapter:
    """Process-sealed exact replay of one frozen ordered observation roster."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: Any, **kwargs: Any) -> ReplayBehavioralAdapter:
        del args, kwargs
        _reject_direct_construction("ReplayBehavioralAdapter")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("ReplayBehavioralAdapter cannot be subclassed")

    def __copy__(self) -> NoReturn:
        _reject_duplication("ReplayBehavioralAdapter")

    def __deepcopy__(self, memo: Any) -> NoReturn:
        del memo
        _reject_duplication("ReplayBehavioralAdapter")

    def __reduce__(self) -> NoReturn:
        _reject_duplication("ReplayBehavioralAdapter")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _reject_duplication("ReplayBehavioralAdapter")

    def __replace__(self, **changes: Any) -> NoReturn:
        del changes
        _reject_duplication("ReplayBehavioralAdapter")

    @property
    def adapter_mode(self) -> str:
        _require_replay_seal(self)
        return BEHAVIORAL_REPLAY_MODE

    @property
    def status(self) -> str:
        _require_replay_seal(self)
        return BEHAVIORAL_ADAPTER_STATUS

    @property
    def authority(self) -> str:
        _require_replay_seal(self)
        return BEHAVIORAL_ADAPTER_AUTHORITY

    @property
    def case_count(self) -> int:
        return len(_require_replay_seal(self).rows)

    @property
    def consumed_case_count(self) -> int:
        seal = _require_replay_seal(self)
        with seal.lock:
            return seal.cursor

    @property
    def complete(self) -> bool:
        seal = _require_replay_seal(self)
        with seal.lock:
            return seal.cursor == len(seal.rows)

    def observe(self, case_input: BehavioralCaseInput) -> BehavioralObservationArtifact:
        """Consume the next exact case and return its preloaded observation."""

        seal = _require_replay_seal(self)
        with seal.lock:
            _verify_replay_dependencies(seal)
            if seal.cursor >= len(seal.rows):
                raise SchemaValidationError(
                    "behavioral replay roster was already consumed exactly once"
                )
            row = seal.rows[seal.cursor]
            _require_exact_case(row, case_input)
            detached = _verify_observation(seal, row)
            seal.cursor += 1
            return detached

    def observe_bytes(self, case_input: BehavioralCaseInput) -> bytes:
        """Consume one case and return only its preloaded canonical bytes."""

        observation = self.observe(case_input)
        if type(observation.raw_bytes) is not bytes:
            raise SchemaValidationError(
                "behavioral observation lost its immutable canonical bytes"
            )
        return observation.raw_bytes

    def replay_all(
        self,
        ordered_cases: tuple[BehavioralCaseInput, ...],
    ) -> tuple[BehavioralObservationArtifact, ...]:
        """Atomically consume the complete exact roster once."""

        seal = _require_replay_seal(self)
        with seal.lock:
            if seal.cursor != 0:
                raise SchemaValidationError(
                    "whole-roster replay requires an untouched adapter"
                )
            if type(ordered_cases) is not tuple or len(ordered_cases) != len(
                seal.rows
            ):
                raise SchemaValidationError(
                    "whole-roster replay requires the exact frozen roster"
                )
            _verify_replay_dependencies(seal)
            detached: list[BehavioralObservationArtifact] = []
            for supplied, row in zip(ordered_cases, seal.rows, strict=True):
                _require_exact_case(row, supplied)
                detached.append(_verify_observation(seal, row))
            seal.cursor = len(seal.rows)
            return tuple(detached)

    def require_complete(self) -> None:
        """Fail closed unless every frozen row was consumed exactly once."""

        seal = _require_replay_seal(self)
        with seal.lock:
            if seal.cursor != len(seal.rows):
                raise SchemaValidationError(
                    "behavioral replay roster is not completely consumed"
                )


class UnavailableBehavioralAdapter:
    """A sealed non-adapter that fails before inspecting any case input."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: Any, **kwargs: Any) -> UnavailableBehavioralAdapter:
        del args, kwargs
        _reject_direct_construction("UnavailableBehavioralAdapter")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("UnavailableBehavioralAdapter cannot be subclassed")

    def __copy__(self) -> NoReturn:
        _reject_duplication("UnavailableBehavioralAdapter")

    def __deepcopy__(self, memo: Any) -> NoReturn:
        del memo
        _reject_duplication("UnavailableBehavioralAdapter")

    def __reduce__(self) -> NoReturn:
        _reject_duplication("UnavailableBehavioralAdapter")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _reject_duplication("UnavailableBehavioralAdapter")

    def __replace__(self, **changes: Any) -> NoReturn:
        del changes
        _reject_duplication("UnavailableBehavioralAdapter")

    @property
    def adapter_mode(self) -> str:
        _require_unavailable_seal(self)
        return UNAVAILABLE

    @property
    def status(self) -> str:
        _require_unavailable_seal(self)
        return BEHAVIORAL_ADAPTER_STATUS

    @property
    def authority(self) -> str:
        _require_unavailable_seal(self)
        return BEHAVIORAL_ADAPTER_AUTHORITY

    def observe(self, case_input: object) -> NoReturn:
        del case_input
        seal = _require_unavailable_seal(self)
        raise BehavioralAdapterUnavailableError(seal.reason)

    def observe_bytes(self, case_input: object) -> NoReturn:
        del case_input
        seal = _require_unavailable_seal(self)
        raise BehavioralAdapterUnavailableError(seal.reason)

    def replay_all(self, ordered_cases: object) -> NoReturn:
        del ordered_cases
        seal = _require_unavailable_seal(self)
        raise BehavioralAdapterUnavailableError(seal.reason)


def build_replay_behavioral_adapter(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    protocol_ref: ArtifactRef,
    ordered_cases: tuple[BehavioralCaseInput, ...],
    observations: tuple[BehavioralObservationArtifact, ...],
) -> ReplayBehavioralAdapter:
    """Seal one canonical observation per label-free ordered case."""

    identity_signature, capabilities_signature = _validate_model_dependencies(
        identity,
        capabilities,
    )
    _require_ref(configuration_ref, "configuration_ref")
    _require_ref(protocol_ref, "protocol_ref")
    _require_ref_media(
        configuration_ref,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        "configuration_ref",
    )
    _require_ref_media(
        protocol_ref,
        BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
        "protocol_ref",
    )
    _require_distinct_refs(
        (("configuration_ref", configuration_ref), ("protocol_ref", protocol_ref)),
        path="behavioral replay factory",
    )
    if type(ordered_cases) is not tuple or not ordered_cases:
        raise SchemaValidationError("ordered_cases must be a non-empty exact tuple")
    if type(observations) is not tuple or len(observations) != len(ordered_cases):
        raise SchemaValidationError(
            "observations must be an exact tuple matching the full case roster"
        )

    rows: list[_ReplayRowSeal] = []
    case_ids: set[str] = set()
    case_ref_keys: set[tuple[Any, ...]] = set()
    observation_ids: set[str] = set()
    observation_ref_keys: set[tuple[Any, ...]] = set()
    for expected_ordinal, (case_input, observation) in enumerate(
        zip(ordered_cases, observations, strict=True),
        start=1,
    ):
        if type(case_input) is not BehavioralCaseInput:
            raise SchemaValidationError(
                "ordered_cases must contain exact BehavioralCaseInput values"
            )
        if case_input.execution_ordinal != expected_ordinal:
            raise SchemaValidationError(
                "behavioral case ordinals must be contiguous and one-based"
            )
        if (
            case_input.configuration_ref != configuration_ref
            or case_input.protocol_ref != protocol_ref
        ):
            raise SchemaValidationError(
                "behavioral case differs from the adapter configuration or protocol"
            )
        if case_input.case_id in case_ids:
            raise SchemaValidationError("behavioral roster contains duplicate case_id")
        case_ref_key = _ref_signature(case_input.case_ref)
        if case_ref_key in case_ref_keys:
            raise SchemaValidationError("behavioral roster reuses a case artifact")
        case_ids.add(case_input.case_id)
        case_ref_keys.add(case_ref_key)

        observation_signature, sealed_observation = _validate_observation(
            observation,
            identity=identity,
            configuration_ref=configuration_ref,
            protocol_ref=protocol_ref,
            case_input=case_input,
        )
        if sealed_observation.observation_id in observation_ids:
            raise SchemaValidationError(
                "behavioral replay contains duplicate observation_id"
            )
        observation_ref_key = _ref_signature(sealed_observation.artifact_ref)
        if observation_ref_key in observation_ref_keys:
            raise SchemaValidationError(
                "behavioral replay reuses an observation artifact"
            )
        observation_ids.add(sealed_observation.observation_id)
        observation_ref_keys.add(observation_ref_key)
        rows.append(
            _ReplayRowSeal(
                case_input=case_input,
                case_signature=_case_signature(case_input),
                observation=sealed_observation,
                observation_signature=observation_signature,
            )
        )

    sealed_rows = tuple(rows)
    artifact_closure_signature = _build_artifact_closure_signature(
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        protocol_ref=protocol_ref,
        rows=sealed_rows,
    )
    adapter = object.__new__(ReplayBehavioralAdapter)
    seal = _ReplayAdapterSeal(
        identity=identity,
        identity_signature=identity_signature,
        capabilities=capabilities,
        capabilities_signature=capabilities_signature,
        configuration_ref=configuration_ref,
        protocol_ref=protocol_ref,
        rows=sealed_rows,
        artifact_closure_signature=artifact_closure_signature,
        cursor=0,
        lock=threading.RLock(),
    )
    with _SEALS_LOCK:
        _REPLAY_SEALS[adapter] = seal
    return adapter


def build_unavailable_behavioral_adapter(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    protocol_ref: ArtifactRef,
    reason: str,
) -> UnavailableBehavioralAdapter:
    """Build a bound adapter that can only report local unavailability."""

    identity_signature, capabilities_signature = _validate_model_dependencies(
        identity,
        capabilities,
    )
    _require_ref(configuration_ref, "configuration_ref")
    _require_ref(protocol_ref, "protocol_ref")
    _require_ref_media(
        configuration_ref,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        "configuration_ref",
    )
    _require_ref_media(
        protocol_ref,
        BEHAVIORAL_COMPARISON_PROTOCOL_MEDIA_TYPE,
        "protocol_ref",
    )
    _require_distinct_refs(
        (("configuration_ref", configuration_ref), ("protocol_ref", protocol_ref)),
        path="unavailable behavioral adapter factory",
    )
    expect_string(reason, "reason", maximum=512)
    artifact_closure_signature = _build_artifact_closure_signature(
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        protocol_ref=protocol_ref,
        rows=(),
    )
    adapter = object.__new__(UnavailableBehavioralAdapter)
    seal = _UnavailableAdapterSeal(
        identity=identity,
        identity_signature=identity_signature,
        capabilities=capabilities,
        capabilities_signature=capabilities_signature,
        configuration_ref=configuration_ref,
        protocol_ref=protocol_ref,
        artifact_closure_signature=artifact_closure_signature,
        reason=reason,
    )
    with _SEALS_LOCK:
        _UNAVAILABLE_SEALS[adapter] = seal
    return adapter


def observe_behavioral_case(
    adapter: object,
    case_input: object,
) -> BehavioralObservationArtifact:
    """Dispatch only to the two exact built-in non-live adapter types."""

    if type(adapter) is ReplayBehavioralAdapter:
        if type(case_input) is not BehavioralCaseInput:
            raise SchemaValidationError(
                "replay requires an exact BehavioralCaseInput"
            )
        return adapter.observe(case_input)
    if type(adapter) is UnavailableBehavioralAdapter:
        return adapter.observe(case_input)
    raise SchemaValidationError(
        "arbitrary or live behavioral adapter types are not installed"
    )


def _require_ref(value: object, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise SchemaValidationError(f"{path} must be an exact ArtifactRef")
    return value


def _ref_signature(value: ArtifactRef) -> tuple[str, str, int, str]:
    _require_ref(value, "artifact reference")
    return (
        value.artifact_id,
        value.sha256,
        value.byte_length,
        value.media_type,
    )


def _require_ref_media(value: ArtifactRef, expected: str, path: str) -> None:
    _require_ref(value, path)
    if value.media_type != expected:
        raise SchemaValidationError(
            f"{path}.media_type must be the exact comparison protocol media type"
        )


def _require_distinct_refs(
    values: tuple[tuple[str, ArtifactRef], ...],
    *,
    path: str,
) -> None:
    ids: set[str] = set()
    content: set[tuple[str, int]] = set()
    for role, reference in values:
        _require_ref(reference, f"{path}.{role}")
        content_key = (reference.sha256, reference.byte_length)
        if reference.artifact_id in ids or content_key in content:
            raise SchemaValidationError(f"{path} contains cross-role artifact reuse")
        ids.add(reference.artifact_id)
        content.add(content_key)


def _artifact_signature(value: object, exact_type: type[Any]) -> tuple[Any, ...]:
    if type(value) is not exact_type:
        raise SchemaValidationError(
            f"artifact must have exact type {exact_type.__name__}"
        )
    raw_bytes = getattr(value, "raw_bytes", None)
    reference = getattr(value, "artifact_ref", None)
    if type(raw_bytes) is not bytes or type(reference) is not ArtifactRef:
        raise SchemaValidationError("artifact lost immutable bytes or exact reference")
    if not reference.verify_bytes(raw_bytes):
        raise SchemaValidationError("artifact reference does not bind its exact bytes")
    return (raw_bytes, _ref_signature(reference))


def _case_signature(value: BehavioralCaseInput) -> tuple[Any, ...]:
    if type(value) is not BehavioralCaseInput:
        raise SchemaValidationError("case input has a substituted exact type")
    return (
        value.execution_ordinal,
        value.case_id,
        _ref_signature(value.case_ref),
        _ref_signature(value.configuration_ref),
        _ref_signature(value.protocol_ref),
    )


def _validate_model_dependencies(
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    identity_signature = _artifact_signature(
        identity,
        ComparisonModelIdentityArtifact,
    )
    capabilities_signature = _artifact_signature(
        capabilities,
        ComparisonModelCapabilitiesArtifact,
    )
    try:
        replayed_identity = replay_comparison_model_identity(identity)
        replayed_capabilities = replay_comparison_model_capabilities(
            capabilities,
            identity=identity,
        )
    except Exception as exc:
        raise SchemaValidationError(
            f"model comparison dependencies fail exact replay: {exc}"
        ) from exc
    if replayed_identity != identity or replayed_capabilities != capabilities:
        raise SchemaValidationError(
            "model comparison dependencies differ from canonical replay"
        )
    if identity.access_kind == CLOSED_WEIGHT:
        capability_by_name = {
            capability.name: capability.status
            for capability in capabilities.capabilities
        }
        for name in (
            HIDDEN_STATE_OBSERVATION,
            ACTIVATION_CAPTURE,
            STEERING_INTERVENTION,
        ):
            if capability_by_name.get(name) != UNAVAILABLE_BY_ACCESS_MODEL:
                raise SchemaValidationError(
                    "closed-weight behavioral adapter cannot expose hidden state, "
                    "activation capture, or steering"
                )
    return identity_signature, capabilities_signature


def _validate_observation(
    observation: BehavioralObservationArtifact,
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    protocol_ref: ArtifactRef,
    case_input: BehavioralCaseInput,
) -> tuple[tuple[Any, ...], BehavioralObservationArtifact]:
    signature = _artifact_signature(observation, BehavioralObservationArtifact)
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
        raise SchemaValidationError(
            f"behavioral observation fails exact bound replay: {exc}"
        ) from exc
    if replayed != observation:
        raise SchemaValidationError(
            "behavioral observation differs from its canonical replay"
        )
    if observation.observation_status != OBSERVED:
        raise SchemaValidationError(
            "replay adapter accepts only preloaded OBSERVED artifacts"
        )
    return signature, replayed


def _build_artifact_closure_signature(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    protocol_ref: ArtifactRef,
    rows: tuple[_ReplayRowSeal, ...],
) -> tuple[tuple[Any, ...], ...]:
    """Build one alias-free artifact-ID/content closure for the adapter."""

    role_refs: list[tuple[str, ArtifactRef]] = [
        ("identity", identity.artifact_ref),
        ("capabilities", capabilities.artifact_ref),
        ("configuration", configuration_ref),
        ("protocol", protocol_ref),
    ]
    if identity.weight_artifact_ref is not None:
        role_refs.append(("identity.weight", identity.weight_artifact_ref))
    role_refs.extend(
        (f"capability.{capability.name}", capability.evidence_ref)
        for capability in capabilities.capabilities
        if capability.evidence_ref is not None
    )
    for row in rows:
        prefix = f"case.{row.case_input.execution_ordinal}"
        role_refs.extend(
            (
                (f"{prefix}.input", row.case_input.case_ref),
                (f"{prefix}.observation", row.observation.artifact_ref),
            )
        )
        if row.observation.raw_response_ref is not None:
            role_refs.append(
                (f"{prefix}.raw_response", row.observation.raw_response_ref)
            )
        if row.observation.raw_tool_calls_ref is not None:
            role_refs.append(
                (f"{prefix}.raw_tool_calls", row.observation.raw_tool_calls_ref)
            )

    artifact_ids: dict[str, str] = {}
    content: dict[tuple[str, int], str] = {}
    closure: list[tuple[Any, ...]] = []
    for role, reference in role_refs:
        _require_ref(reference, f"artifact closure {role}")
        prior_id_role = artifact_ids.get(reference.artifact_id)
        if prior_id_role is not None:
            raise SchemaValidationError(
                "behavioral adapter artifact closure reuses artifact_id across "
                f"{prior_id_role} and {role}"
            )
        content_key = (reference.sha256, reference.byte_length)
        prior_content_role = content.get(content_key)
        if prior_content_role is not None:
            raise SchemaValidationError(
                "behavioral adapter artifact closure reuses content across "
                f"{prior_content_role} and {role}"
            )
        artifact_ids[reference.artifact_id] = role
        content[content_key] = role
        closure.append((role, *_ref_signature(reference)))
    return tuple(closure)


def _require_replay_seal(adapter: object) -> _ReplayAdapterSeal:
    if type(adapter) is not ReplayBehavioralAdapter:
        raise SchemaValidationError("replay adapter has a substituted exact type")
    with _SEALS_LOCK:
        seal = _REPLAY_SEALS.get(adapter)
    if seal is None:
        raise SchemaValidationError(
            "replay adapter is not an exact process-sealed factory result"
        )
    return seal


def _require_unavailable_seal(adapter: object) -> _UnavailableAdapterSeal:
    if type(adapter) is not UnavailableBehavioralAdapter:
        raise SchemaValidationError(
            "unavailable adapter has a substituted exact type"
        )
    with _SEALS_LOCK:
        seal = _UNAVAILABLE_SEALS.get(adapter)
    if seal is None:
        raise SchemaValidationError(
            "unavailable adapter is not an exact process-sealed factory result"
        )
    return seal


def _verify_replay_dependencies(seal: _ReplayAdapterSeal) -> None:
    identity_signature, capabilities_signature = _validate_model_dependencies(
        seal.identity,
        seal.capabilities,
    )
    if (
        identity_signature != seal.identity_signature
        or capabilities_signature != seal.capabilities_signature
    ):
        raise SchemaValidationError("sealed model comparison dependencies changed")
    current_closure = _build_artifact_closure_signature(
        identity=seal.identity,
        capabilities=seal.capabilities,
        configuration_ref=seal.configuration_ref,
        protocol_ref=seal.protocol_ref,
        rows=seal.rows,
    )
    if current_closure != seal.artifact_closure_signature:
        raise SchemaValidationError("sealed behavioral artifact closure changed")


def _require_exact_case(
    row: _ReplayRowSeal,
    supplied: object,
) -> None:
    if supplied is not row.case_input:
        raise SchemaValidationError(
            "behavioral case is missing, duplicated, substituted, or out of order"
        )
    if _case_signature(row.case_input) != row.case_signature:
        raise SchemaValidationError("sealed behavioral case input was mutated")


def _verify_observation(
    seal: _ReplayAdapterSeal,
    row: _ReplayRowSeal,
) -> BehavioralObservationArtifact:
    signature, detached = _validate_observation(
        row.observation,
        identity=seal.identity,
        configuration_ref=seal.configuration_ref,
        protocol_ref=seal.protocol_ref,
        case_input=row.case_input,
    )
    if signature != row.observation_signature:
        raise SchemaValidationError("sealed behavioral observation was mutated")
    if detached is row.observation:
        raise SchemaValidationError("behavioral replay did not detach its return value")
    return detached


__all__ = (
    "BEHAVIORAL_ADAPTER_AUTHORITY",
    "BEHAVIORAL_ADAPTER_STATUS",
    "BEHAVIORAL_REPLAY_MODE",
    "BehavioralAdapterError",
    "BehavioralAdapterUnavailableError",
    "BehavioralCaseInput",
    "ReplayBehavioralAdapter",
    "UnavailableBehavioralAdapter",
    "build_replay_behavioral_adapter",
    "build_unavailable_behavioral_adapter",
    "observe_behavioral_case",
)
