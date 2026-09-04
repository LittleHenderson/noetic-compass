"""Frozen, no-float wire types for the Neural CJT research runtime.

These objects describe proposals and receipts.  They do not grant truth,
permission, proof, publication, or state-write authority.  Neural tensors live
in content-addressed artifacts; authoritative JSON carries only references.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum
import re
from types import MappingProxyType
from typing import Any, ClassVar, Mapping, Sequence


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SCHEMA_PREFIX = "cas.neural-cjt"
PPM_SCALE = 1_000_000


class ContractTypeError(ValueError):
    """Raised when a typed contract violates a local invariant."""


class CauseKind(StrEnum):
    TOKEN = "TOKEN"
    PROPOSITION = "PROPOSITION"
    IDEA = "IDEA"
    EVENT = "EVENT"
    ENTITY_RELATION = "ENTITY_RELATION"
    EFFECT = "EFFECT"
    MEMORY_RESULT = "MEMORY_RESULT"
    OBSERVATION = "OBSERVATION"
    RPM_SUBGOAL = "RPM_SUBGOAL"
    TRAINING_EXPERIENCE = "TRAINING_EXPERIENCE"


class ReadinessAxisName(StrEnum):
    DESIRE = "DESIRE"
    WISDOM = "WISDOM"
    POWER = "POWER"


class ReadinessStatus(StrEnum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    UNKNOWN = "UNKNOWN"


class OperatingRegion(StrEnum):
    UNASSESSED = "UNASSESSED"
    CUTOFF = "CUTOFF"
    ACTIVE = "ACTIVE"
    SATURATION = "SATURATION"
    BREAKDOWN = "BREAKDOWN"
    NON_OHMIC = "NON_OHMIC"
    UNSTABLE = "UNSTABLE"


class SemanticOutcome(StrEnum):
    UNASSESSED = "UNASSESSED"
    INTENDED = "INTENDED"
    OPPOSITE = "OPPOSITE"
    OFF_AXIS = "OFF_AXIS"
    UNKNOWN = "UNKNOWN"


class VerifierDisposition(StrEnum):
    ACCEPT = "ACCEPT"
    REFUSE = "REFUSE"
    ABSTAIN = "ABSTAIN"
    REPAIR = "REPAIR"
    QUARANTINE = "QUARANTINE"
    ROLLBACK = "ROLLBACK"
    HALT = "HALT"


class OntologyStatus(StrEnum):
    CANONICAL_ADMITTED = "CANONICAL_ADMITTED"
    EXPERIMENTAL_OPEN_SEMANTICS = "EXPERIMENTAL_OPEN_SEMANTICS"
    EXPERIMENTAL_CONFLICTED_SEMANTICS = "EXPERIMENTAL_CONFLICTED_SEMANTICS"
    EXPERIMENTAL_LOCAL = "EXPERIMENTAL_LOCAL"


class RepairStatus(StrEnum):
    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    RETURNED = "RETURNED"
    FAILED = "FAILED"
    EXHAUSTED = "EXHAUSTED"


class ModelUpdateKind(StrEnum):
    GRADIENT_DELTA = "GRADIENT_DELTA"
    CHECKPOINT_REPLACEMENT = "CHECKPOINT_REPLACEMENT"
    ROLLBACK = "ROLLBACK"


class MemoryKind(StrEnum):
    SHORT_TERM = "SHORT_TERM"
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    PROCEDURAL = "PROCEDURAL"
    VERIFIER_HISTORY = "VERIFIER_HISTORY"
    REPAIR_STRATEGY = "REPAIR_STRATEGY"


class CommitDisposition(StrEnum):
    COMMITTED = "COMMITTED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


class AuthorityCapability(StrEnum):
    """Proposal scopes only; none of these values grants write authority."""

    PROPOSE_STATE_UPDATE = "PROPOSE_STATE_UPDATE"
    PROPOSE_MODEL_UPDATE = "PROPOSE_MODEL_UPDATE"
    PROPOSE_MEMORY_WRITE = "PROPOSE_MEMORY_WRITE"
    REQUEST_EFFECT_PUBLICATION = "REQUEST_EFFECT_PUBLICATION"


class TickPhase(StrEnum):
    READ = "READ"
    CANDIDATE = "CANDIDATE"
    READINESS = "READINESS"
    ROUTE = "ROUTE"
    EXECUTE = "EXECUTE"
    OBSERVE = "OBSERVE"
    VERIFY = "VERIFY"
    DIAGNOSE = "DIAGNOSE"
    EMIT = "EMIT"
    COMMIT = "COMMIT"
    TRACE = "TRACE"


MANDATORY_TICK_ORDER: tuple[TickPhase, ...] = tuple(TickPhase)


def _nonempty(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractTypeError(f"{name} must be a non-empty string")
    if value != value.strip():
        raise ContractTypeError(f"{name} must not have surrounding whitespace")
    return value


def _sha256(name: str, value: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ContractTypeError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _optional_sha256(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _sha256(name, value)


def _integer(name: str, value: int, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ContractTypeError(f"{name} must be an integer >= {minimum}")
    return value


def _ppm(name: str, value: int) -> int:
    value = _integer(name, value)
    if value > PPM_SCALE:
        raise ContractTypeError(f"{name} must be <= {PPM_SCALE}")
    return value


def _strings(
    name: str,
    values: Sequence[str],
    *,
    nonempty: bool = False,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise ContractTypeError(f"{name} must be a sequence of strings")
    result = tuple(_nonempty(f"{name}[{index}]", item) for index, item in enumerate(values))
    if nonempty and not result:
        raise ContractTypeError(f"{name} must not be empty")
    if len(set(result)) != len(result):
        raise ContractTypeError(f"{name} must not contain duplicates")
    return result


def _enum_tuple(name: str, values: Sequence[Any], enum_type: type[StrEnum]) -> tuple[Any, ...]:
    if isinstance(values, (str, bytes)):
        raise ContractTypeError(f"{name} must be a sequence")
    try:
        result = tuple(enum_type(item) for item in values)
    except (TypeError, ValueError) as exc:
        raise ContractTypeError(f"{name} contains an invalid value") from exc
    if not result:
        raise ContractTypeError(f"{name} must not be empty")
    if len(set(result)) != len(result):
        raise ContractTypeError(f"{name} must not contain duplicates")
    return result


def _freeze_json(value: Any, *, path: str = "value") -> Any:
    """Deep-freeze a JSON value and reject every floating-point value."""

    if isinstance(value, float):
        raise ContractTypeError(
            f"{path} contains a float; use a scaled integer, decimal string, or tensor artifact"
        )
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str) or not key:
                raise ContractTypeError(f"{path} object keys must be non-empty strings")
            frozen[key] = _freeze_json(value[key], path=f"{path}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, path=f"{path}[{index}]") for index, item in enumerate(value))
    raise ContractTypeError(f"{path} contains unsupported JSON type {type(value).__name__}")


def _frozen_object(name: str, value: Mapping[str, Any], *, nonempty: bool = False) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractTypeError(f"{name} must be an object")
    frozen = _freeze_json(value, path=name)
    if nonempty and not frozen:
        raise ContractTypeError(f"{name} must not be empty")
    return frozen


def _jsonable(value: Any) -> Any:
    if isinstance(value, ContractModel):
        return value.to_dict()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {key: _jsonable(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise ContractTypeError(f"cannot serialize {type(value).__name__} as authoritative JSON")


class ContractModel:
    """Small common interface shared by every public wire type."""

    CONTRACT_TYPE: ClassVar[str]
    SCHEMA_VERSION: ClassVar[str]

    @property
    def contract_type(self) -> str:
        return self.CONTRACT_TYPE

    @property
    def schema_version(self) -> str:
        return self.SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        result = {
            "contract_type": self.CONTRACT_TYPE,
            "schema_version": self.SCHEMA_VERSION,
        }
        for field in fields(self):
            result[field.name] = _jsonable(getattr(self, field.name))
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class TensorArtifactRef(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "TENSOR_ARTIFACT_REF"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.tensor-artifact-ref/0.2"

    artifact_id: str
    sha256: str
    dtype: str
    shape: tuple[int, ...]
    encoding: str
    byte_length: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_id", _nonempty("artifact_id", self.artifact_id))
        object.__setattr__(self, "sha256", _sha256("sha256", self.sha256))
        object.__setattr__(self, "dtype", _nonempty("dtype", self.dtype))
        object.__setattr__(self, "encoding", _nonempty("encoding", self.encoding))
        shape = tuple(self.shape)
        for index, dimension in enumerate(shape):
            _integer(f"shape[{index}]", dimension)
        object.__setattr__(self, "shape", shape)
        _integer("byte_length", self.byte_length, minimum=1)


@dataclass(frozen=True, slots=True, kw_only=True)
class CausePacket(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "CAUSE"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.cause/0.2"

    cause_id: str
    tick: int
    cause_kind: CauseKind
    content: Mapping[str, Any]
    source: str
    provenance: tuple[str, ...]
    time_label: str
    uncertainty_ppm: int
    goal_context: Mapping[str, Any]
    entity_bindings: tuple[str, ...] = ()
    relation_bindings: tuple[str, ...] = ()
    candidate_operation_ids: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = ()
    originating_cjt_id: str | None = None
    originating_modality: str | None = None
    parent_effect_id: str | None = None
    content_ref: TensorArtifactRef | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "cause_id", _nonempty("cause_id", self.cause_id))
        _integer("tick", self.tick)
        try:
            object.__setattr__(self, "cause_kind", CauseKind(self.cause_kind))
        except (TypeError, ValueError) as exc:
            raise ContractTypeError("cause_kind is invalid") from exc
        object.__setattr__(self, "content", _frozen_object("content", self.content, nonempty=True))
        object.__setattr__(self, "source", _nonempty("source", self.source))
        object.__setattr__(self, "provenance", _strings("provenance", self.provenance, nonempty=True))
        object.__setattr__(self, "time_label", _nonempty("time_label", self.time_label))
        _ppm("uncertainty_ppm", self.uncertainty_ppm)
        object.__setattr__(
            self, "goal_context", _frozen_object("goal_context", self.goal_context, nonempty=True)
        )
        for name in ("entity_bindings", "relation_bindings", "candidate_operation_ids", "memory_refs"):
            object.__setattr__(self, name, _strings(name, getattr(self, name)))
        for name in ("originating_cjt_id", "originating_modality", "parent_effect_id"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _nonempty(name, value))
        if self.cause_kind is CauseKind.EFFECT and self.parent_effect_id is None:
            raise ContractTypeError("an EFFECT Cause requires parent_effect_id")
        if self.content_ref is not None and not isinstance(self.content_ref, TensorArtifactRef):
            raise ContractTypeError("content_ref must be a TensorArtifactRef or None")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReadinessAxis(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "READINESS_AXIS"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.readiness-axis/0.2"

    axis: ReadinessAxisName
    status: ReadinessStatus
    score_ppm: int
    threshold_ppm: int
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "axis", ReadinessAxisName(self.axis))
            object.__setattr__(self, "status", ReadinessStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise ContractTypeError("readiness axis or status is invalid") from exc
        _ppm("score_ppm", self.score_ppm)
        _ppm("threshold_ppm", self.threshold_ppm)
        object.__setattr__(self, "reason_codes", _strings("reason_codes", self.reason_codes, nonempty=True))
        object.__setattr__(self, "evidence_refs", _strings("evidence_refs", self.evidence_refs))
        object.__setattr__(self, "provenance", _strings("provenance", self.provenance, nonempty=True))
        if self.status is ReadinessStatus.SUFFICIENT and self.score_ppm < self.threshold_ppm:
            raise ContractTypeError("SUFFICIENT readiness must meet its threshold")


@dataclass(frozen=True, slots=True, kw_only=True)
class ReadinessState(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "READINESS_STATE"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.readiness-state/0.2"

    profile_id: str
    desire: ReadinessAxis
    wisdom: ReadinessAxis
    power: ReadinessAxis

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile_id", _nonempty("profile_id", self.profile_id))
        expected = (
            ("desire", self.desire, ReadinessAxisName.DESIRE),
            ("wisdom", self.wisdom, ReadinessAxisName.WISDOM),
            ("power", self.power, ReadinessAxisName.POWER),
        )
        for name, value, axis in expected:
            if not isinstance(value, ReadinessAxis) or value.axis is not axis:
                raise ContractTypeError(f"{name} must carry axis {axis.value}")

    @property
    def all_sufficient(self) -> bool:
        return all(
            axis.status is ReadinessStatus.SUFFICIENT
            for axis in (self.desire, self.wisdom, self.power)
        )

    @property
    def hard_open(self) -> bool:
        return self.all_sufficient

    @property
    def first_unmet(self) -> ReadinessAxisName | None:
        for axis in (self.desire, self.wisdom, self.power):
            if axis.status is not ReadinessStatus.SUFFICIENT:
                return axis.axis
        return None

    @property
    def readiness_ppm(self) -> int:
        if not self.all_sufficient:
            return 0
        return min(self.desire.score_ppm, self.wisdom.score_ppm, self.power.score_ppm)


@dataclass(frozen=True, slots=True, kw_only=True)
class StableSubstrate(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "BIAS_STABLE_SUBSTRATE"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.bias-stable-substrate/0.2"

    cjt_id: str
    formation_version: int
    registered_operation_id: str
    specialization_tags: tuple[str, ...]
    lineage_refs: tuple[str, ...]
    configuration_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "cjt_id", _nonempty("cjt_id", self.cjt_id))
        _integer("formation_version", self.formation_version)
        object.__setattr__(
            self, "registered_operation_id", _nonempty("registered_operation_id", self.registered_operation_id)
        )
        object.__setattr__(self, "specialization_tags", _strings("specialization_tags", self.specialization_tags))
        object.__setattr__(self, "lineage_refs", _strings("lineage_refs", self.lineage_refs))
        object.__setattr__(
            self, "configuration_digest", _sha256("configuration_digest", self.configuration_digest)
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class LocalMemory(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "BIAS_LOCAL_MEMORY"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.bias-local-memory/0.2"

    recurrent_state_ref: TensorArtifactRef | None
    recent_cause_ids: tuple[str, ...]
    recent_candidate_effect_ids: tuple[str, ...]
    verifier_receipt_ids: tuple[str, ...]
    repair_frame_ids: tuple[str, ...]
    retrieved_memory_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.recurrent_state_ref is not None and not isinstance(
            self.recurrent_state_ref, TensorArtifactRef
        ):
            raise ContractTypeError("recurrent_state_ref must be a TensorArtifactRef or None")
        for name in (
            "recent_cause_ids",
            "recent_candidate_effect_ids",
            "verifier_receipt_ids",
            "repair_frame_ids",
            "retrieved_memory_refs",
            "provenance_refs",
        ):
            object.__setattr__(self, name, _strings(name, getattr(self, name)))


@dataclass(frozen=True, slots=True, kw_only=True)
class RPMState(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "BIAS_RPM_STATE"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.bias-rpm-state/0.2"

    readiness: ReadinessState
    unmet_prerequisites: tuple[str, ...]
    open_repair_ids: tuple[str, ...]
    suspended_parent_cause_id: str | None
    return_addresses: tuple[str, ...]
    repair_history: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.readiness, ReadinessState):
            raise ContractTypeError("readiness must be a ReadinessState")
        for name in ("unmet_prerequisites", "open_repair_ids", "return_addresses", "repair_history"):
            object.__setattr__(self, name, _strings(name, getattr(self, name)))
        if self.suspended_parent_cause_id is not None:
            object.__setattr__(
                self,
                "suspended_parent_cause_id",
                _nonempty("suspended_parent_cause_id", self.suspended_parent_cause_id),
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class OperatingRecord(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "BIAS_OPERATING_RECORD"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.bias-operating-record/0.2"

    region: OperatingRegion
    stability_status: str
    response_model_status: str
    semantic_outcome: SemanticOutcome
    previous_committed_verifier_receipt_id: str | None
    last_tick: int

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "region", OperatingRegion(self.region))
            object.__setattr__(self, "semantic_outcome", SemanticOutcome(self.semantic_outcome))
        except (TypeError, ValueError) as exc:
            raise ContractTypeError("operating region or semantic outcome is invalid") from exc
        object.__setattr__(self, "stability_status", _nonempty("stability_status", self.stability_status))
        object.__setattr__(
            self, "response_model_status", _nonempty("response_model_status", self.response_model_status)
        )
        if self.previous_committed_verifier_receipt_id is not None:
            object.__setattr__(
                self,
                "previous_committed_verifier_receipt_id",
                _nonempty(
                    "previous_committed_verifier_receipt_id",
                    self.previous_committed_verifier_receipt_id,
                ),
            )
        _integer("last_tick", self.last_tick)


@dataclass(frozen=True, slots=True, kw_only=True)
class ThetaRef(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "BIAS_THETA_REF"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.bias-theta-ref/0.2"

    model_id: str
    model_version: int
    model_digest: str
    parameter_artifacts: tuple[TensorArtifactRef, ...]
    parameter_group_ids: tuple[str, ...]
    beta_microunits: int
    operating_profile_id: str
    adapter_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _nonempty("model_id", self.model_id))
        _integer("model_version", self.model_version)
        object.__setattr__(self, "model_digest", _sha256("model_digest", self.model_digest))
        artifacts = tuple(self.parameter_artifacts)
        if not artifacts or not all(isinstance(item, TensorArtifactRef) for item in artifacts):
            raise ContractTypeError("parameter_artifacts must contain TensorArtifactRef values")
        if len({item.artifact_id for item in artifacts}) != len(artifacts):
            raise ContractTypeError("parameter_artifacts must have unique artifact IDs")
        object.__setattr__(self, "parameter_artifacts", artifacts)
        object.__setattr__(
            self, "parameter_group_ids", _strings("parameter_group_ids", self.parameter_group_ids, nonempty=True)
        )
        _integer("beta_microunits", self.beta_microunits)
        object.__setattr__(
            self, "operating_profile_id", _nonempty("operating_profile_id", self.operating_profile_id)
        )
        object.__setattr__(self, "adapter_ids", _strings("adapter_ids", self.adapter_ids))


@dataclass(frozen=True, slots=True, kw_only=True)
class Governance(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "BIAS_GOVERNANCE"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.bias-governance/0.2"

    hard_permissions: tuple[str, ...]
    topology_permissions: tuple[str, ...]
    learning_permissions: tuple[str, ...]
    compute_ceiling_units: int
    quarantined: bool
    state_write_authorities: tuple[str, ...]
    memory_write_authorities: tuple[str, ...]
    effect_publication_authorities: tuple[str, ...]
    owner_restrictions: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "hard_permissions",
            "topology_permissions",
            "learning_permissions",
            "state_write_authorities",
            "memory_write_authorities",
            "effect_publication_authorities",
            "owner_restrictions",
        ):
            object.__setattr__(self, name, _strings(name, getattr(self, name)))
        _integer("compute_ceiling_units", self.compute_ceiling_units)
        if not isinstance(self.quarantined, bool):
            raise ContractTypeError("quarantined must be boolean")


@dataclass(frozen=True, slots=True, kw_only=True)
class BiasState(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "BIAS_STATE"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.bias-state/0.2"

    bias_id: str
    cjt_id: str
    version: int
    previous_digest: str | None
    stable: StableSubstrate
    memory: LocalMemory
    rpm: RPMState
    operating: OperatingRecord
    theta: ThetaRef
    governance: Governance
    state_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "bias_id", _nonempty("bias_id", self.bias_id))
        object.__setattr__(self, "cjt_id", _nonempty("cjt_id", self.cjt_id))
        _integer("version", self.version)
        object.__setattr__(
            self, "previous_digest", _optional_sha256("previous_digest", self.previous_digest)
        )
        expected_types = (
            ("stable", self.stable, StableSubstrate),
            ("memory", self.memory, LocalMemory),
            ("rpm", self.rpm, RPMState),
            ("operating", self.operating, OperatingRecord),
            ("theta", self.theta, ThetaRef),
            ("governance", self.governance, Governance),
        )
        for name, value, expected_type in expected_types:
            if not isinstance(value, expected_type):
                raise ContractTypeError(f"{name} must be {expected_type.__name__}")
        if self.stable.cjt_id != self.cjt_id:
            raise ContractTypeError("stable.cjt_id must equal BiasState.cjt_id")
        if self.version == 0 and self.previous_digest is not None:
            raise ContractTypeError("version 0 Bias cannot have previous_digest")
        if self.version > 0 and self.previous_digest is None:
            raise ContractTypeError("versioned Bias requires previous_digest")
        object.__setattr__(self, "state_digest", _sha256("state_digest", self.state_digest))


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateEffect(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "CANDIDATE_EFFECT"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.candidate-effect/0.2"

    candidate_effect_id: str
    tick: int
    parent_cause_id: str
    producer_cjt_id: str
    operation_id: str
    operation_contract_id: str
    operation_contract_digest: str
    bias_id: str
    bias_version: int
    bias_digest: str
    model_digest: str
    content: Mapping[str, Any]
    content_ref: TensorArtifactRef | None
    uncertainty_ppm: int
    provenance: tuple[str, ...]
    candidate_digest: str
    authoritative: bool = False

    def __post_init__(self) -> None:
        for name in (
            "candidate_effect_id",
            "parent_cause_id",
            "producer_cjt_id",
            "operation_id",
            "operation_contract_id",
            "bias_id",
        ):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        _integer("tick", self.tick)
        _integer("bias_version", self.bias_version)
        for name in ("operation_contract_digest", "bias_digest", "model_digest", "candidate_digest"):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        object.__setattr__(self, "content", _frozen_object("content", self.content, nonempty=True))
        if self.content_ref is not None and not isinstance(self.content_ref, TensorArtifactRef):
            raise ContractTypeError("content_ref must be a TensorArtifactRef or None")
        _ppm("uncertainty_ppm", self.uncertainty_ppm)
        object.__setattr__(self, "provenance", _strings("provenance", self.provenance, nonempty=True))
        if self.authoritative is not False:
            raise ContractTypeError("a CandidateEffect can never be authoritative")


@dataclass(frozen=True, slots=True, kw_only=True)
class PublishedEffect(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "PUBLISHED_EFFECT"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.published-effect/0.2"

    published_effect_id: str
    candidate_effect_id: str
    tick: int
    producer_cjt_id: str
    content: Mapping[str, Any]
    content_ref: TensorArtifactRef | None
    verifier_receipt_id: str
    commit_receipt_id: str
    provenance: tuple[str, ...]
    publication_digest: str
    authoritative: bool = True

    def __post_init__(self) -> None:
        for name in (
            "published_effect_id",
            "candidate_effect_id",
            "producer_cjt_id",
            "verifier_receipt_id",
            "commit_receipt_id",
        ):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        _integer("tick", self.tick)
        object.__setattr__(self, "content", _frozen_object("content", self.content, nonempty=True))
        if self.content_ref is not None and not isinstance(self.content_ref, TensorArtifactRef):
            raise ContractTypeError("content_ref must be a TensorArtifactRef or None")
        object.__setattr__(self, "provenance", _strings("provenance", self.provenance, nonempty=True))
        object.__setattr__(
            self, "publication_digest", _sha256("publication_digest", self.publication_digest)
        )
        if self.authoritative is not True:
            raise ContractTypeError("a PublishedEffect must be authoritative")


# These names are local v0.2 interpretations.  Only ^6 is presently admitted
# by the higher-precedence homebase ontology for the meaning used here.
BUILTIN_OPERATION_IDENTITIES: Mapping[str, tuple[str, OntologyStatus]] = MappingProxyType(
    {
        "^2": ("experimental_attract", OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS),
        "^3": ("experimental_avert", OntologyStatus.EXPERIMENTAL_OPEN_SEMANTICS),
        "^6": ("decompose", OntologyStatus.CANONICAL_ADMITTED),
        "^8": ("experimental_trigger", OntologyStatus.EXPERIMENTAL_CONFLICTED_SEMANTICS),
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class OperationContract(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "OPERATION_CONTRACT"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.operation-contract/0.2"

    contract_id: str
    contract_version: int
    operation_id: str
    operation_name: str
    ontology_status: OntologyStatus
    accepted_cause_kinds: tuple[CauseKind, ...]
    accepted_schema_versions: tuple[str, ...]
    permitted_evidence_ports: tuple[str, ...]
    neural_transform_id: str
    effect_schema_id: str
    memory_interface: tuple[str, ...]
    readiness_profile_id: str
    legal_actions: tuple[str, ...]
    legal_bias_paths: tuple[str, ...]
    temporal_transition_law: str
    verifier_id: str
    verifier_version: int
    verifier_digest: str
    plasticity_groups: tuple[str, ...]
    governance_requirements: tuple[str, ...]
    contract_digest: str

    def __post_init__(self) -> None:
        for name in (
            "contract_id",
            "operation_id",
            "operation_name",
            "neural_transform_id",
            "effect_schema_id",
            "readiness_profile_id",
            "temporal_transition_law",
            "verifier_id",
        ):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        _integer("contract_version", self.contract_version, minimum=1)
        _integer("verifier_version", self.verifier_version, minimum=1)
        try:
            object.__setattr__(self, "ontology_status", OntologyStatus(self.ontology_status))
        except (TypeError, ValueError) as exc:
            raise ContractTypeError("ontology_status is invalid") from exc
        object.__setattr__(
            self,
            "accepted_cause_kinds",
            _enum_tuple("accepted_cause_kinds", self.accepted_cause_kinds, CauseKind),
        )
        for name in (
            "accepted_schema_versions",
            "permitted_evidence_ports",
            "memory_interface",
            "legal_actions",
            "legal_bias_paths",
            "plasticity_groups",
            "governance_requirements",
        ):
            object.__setattr__(self, name, _strings(name, getattr(self, name), nonempty=True))
        for path in self.legal_bias_paths:
            if not path.startswith(("/memory", "/rpm", "/operating", "/theta")):
                raise ContractTypeError(f"legal Bias path is not mutable in v0.2: {path}")
        for name in ("verifier_digest", "contract_digest"):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))

        expected = BUILTIN_OPERATION_IDENTITIES.get(self.operation_id)
        if expected is not None and (self.operation_name, self.ontology_status) != expected:
            raise ContractTypeError(
                f"{self.operation_id} must be named {expected[0]!r} with status {expected[1].value}"
            )
        if self.ontology_status is OntologyStatus.CANONICAL_ADMITTED and self.operation_id != "^6":
            raise ContractTypeError("only ^6 is canonical-admitted at this authority boundary")
        if self.ontology_status is not OntologyStatus.CANONICAL_ADMITTED and not self.operation_name.startswith(
            "experimental_"
        ):
            raise ContractTypeError("noncanonical operation names must start with 'experimental_'")


@dataclass(frozen=True, slots=True, kw_only=True)
class VerifierReceipt(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "VERIFIER_RECEIPT"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.verifier-receipt/0.2"

    receipt_id: str
    tick: int
    verifier_id: str
    verifier_version: int
    verifier_digest: str
    independent: bool
    cause_id: str
    candidate_effect_id: str
    candidate_effect_digest: str
    bias_id: str
    bias_version: int
    bias_digest: str
    operation_contract_id: str
    operation_contract_digest: str
    model_digest: str
    semantic_outcome: SemanticOutcome
    disposition: VerifierDisposition
    reason_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    repair_required: bool
    receipt_digest: str

    def __post_init__(self) -> None:
        for name in (
            "receipt_id",
            "verifier_id",
            "cause_id",
            "candidate_effect_id",
            "bias_id",
            "operation_contract_id",
        ):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        _integer("tick", self.tick)
        _integer("verifier_version", self.verifier_version, minimum=1)
        _integer("bias_version", self.bias_version)
        if self.independent is not True:
            raise ContractTypeError("the candidate producer cannot self-verify")
        for name in (
            "verifier_digest",
            "candidate_effect_digest",
            "bias_digest",
            "operation_contract_digest",
            "model_digest",
            "receipt_digest",
        ):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        try:
            object.__setattr__(self, "semantic_outcome", SemanticOutcome(self.semantic_outcome))
            object.__setattr__(self, "disposition", VerifierDisposition(self.disposition))
        except (TypeError, ValueError) as exc:
            raise ContractTypeError("verifier outcome or disposition is invalid") from exc
        object.__setattr__(self, "reason_codes", _strings("reason_codes", self.reason_codes, nonempty=True))
        object.__setattr__(self, "evidence_refs", _strings("evidence_refs", self.evidence_refs))
        if not isinstance(self.repair_required, bool):
            raise ContractTypeError("repair_required must be boolean")
        if self.disposition is VerifierDisposition.ACCEPT:
            if self.semantic_outcome is not SemanticOutcome.INTENDED or self.repair_required:
                raise ContractTypeError("ACCEPT requires INTENDED and no repair")
        if self.semantic_outcome is SemanticOutcome.UNASSESSED and self.disposition is VerifierDisposition.ACCEPT:
            raise ContractTypeError("an unassessed candidate cannot be accepted")
        if self.disposition is VerifierDisposition.REPAIR and not self.repair_required:
            raise ContractTypeError("REPAIR disposition requires repair_required")


@dataclass(frozen=True, slots=True, kw_only=True)
class RepairFrame(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "REPAIR_FRAME"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.repair-frame/0.2"

    repair_id: str
    opened_tick: int
    eligible_tick: int
    parent_cause_id: str
    rejected_candidate_effect_id: str
    verifier_receipt_id: str
    suspended_bias_id: str
    suspended_bias_version: int
    prerequisite_axis: ReadinessAxisName
    subgoal_cause_id: str
    return_address: str
    depth: int
    max_depth: int
    branch_count: int
    max_branches: int
    budget_units: int
    consumed_units: int
    cycle_key: str
    status: RepairStatus
    result_effect_id: str | None
    frame_digest: str

    def __post_init__(self) -> None:
        for name in (
            "repair_id",
            "parent_cause_id",
            "rejected_candidate_effect_id",
            "verifier_receipt_id",
            "suspended_bias_id",
            "subgoal_cause_id",
            "return_address",
            "cycle_key",
        ):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        for name in (
            "opened_tick",
            "eligible_tick",
            "suspended_bias_version",
            "depth",
            "max_depth",
            "branch_count",
            "max_branches",
            "budget_units",
            "consumed_units",
        ):
            _integer(name, getattr(self, name))
        if self.eligible_tick != self.opened_tick + 1:
            raise ContractTypeError("repair must become eligible exactly on the next tick")
        if self.depth > self.max_depth:
            raise ContractTypeError("repair depth exceeds max_depth")
        if self.branch_count > self.max_branches:
            raise ContractTypeError("repair branch_count exceeds max_branches")
        if self.consumed_units > self.budget_units:
            raise ContractTypeError("repair consumed_units exceeds budget_units")
        try:
            object.__setattr__(self, "prerequisite_axis", ReadinessAxisName(self.prerequisite_axis))
            object.__setattr__(self, "status", RepairStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise ContractTypeError("repair prerequisite axis or status is invalid") from exc
        if self.status is not RepairStatus.OPEN or self.result_effect_id is not None:
            raise ContractTypeError(
                "v0.2 RepairFrame is immutable OPEN state with no result Effect"
            )
        object.__setattr__(self, "frame_digest", _sha256("frame_digest", self.frame_digest))


@dataclass(frozen=True, slots=True, kw_only=True)
class RepairOutcome(ContractModel):
    """Immutable proof that one OPEN repair was validly resumed and closed."""

    CONTRACT_TYPE: ClassVar[str] = "REPAIR_OUTCOME"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.repair-outcome/0.2"

    outcome_id: str
    repair_id: str
    tick: int
    status: RepairStatus
    frame_digest: str
    result_effect_id: str
    result_effect_digest: str
    result_effect_commit_receipt_id: str
    resumed_cause_id: str
    resumed_candidate_effect_id: str
    verifier_receipt_id: str
    target_bias_id: str
    target_bias_version: int
    target_bias_digest: str
    outcome_digest: str

    def __post_init__(self) -> None:
        for name in (
            "outcome_id",
            "repair_id",
            "result_effect_id",
            "result_effect_commit_receipt_id",
            "resumed_cause_id",
            "resumed_candidate_effect_id",
            "verifier_receipt_id",
            "target_bias_id",
        ):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        _integer("tick", self.tick)
        _integer("target_bias_version", self.target_bias_version)
        try:
            object.__setattr__(self, "status", RepairStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise ContractTypeError("repair outcome status is invalid") from exc
        if self.status is not RepairStatus.RETURNED:
            raise ContractTypeError("a repair outcome must have RETURNED status")
        for name in (
            "frame_digest",
            "result_effect_digest",
            "target_bias_digest",
            "outcome_digest",
        ):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))


@dataclass(frozen=True, slots=True, kw_only=True)
class StateUpdateIntent(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "STATE_UPDATE_INTENT"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.state-update-intent/0.2"

    intent_id: str
    tick: int
    issuer_id: str
    authority_capability: str
    target_bias_id: str
    expected_bias_version: int
    expected_bias_digest: str
    target_path: str
    replacement: Mapping[str, Any]
    verifier_receipt_id: str
    reason_codes: tuple[str, ...]
    intent_digest: str

    def __post_init__(self) -> None:
        for name in ("intent_id", "issuer_id", "authority_capability", "target_bias_id", "verifier_receipt_id"):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        _integer("tick", self.tick)
        if self.authority_capability != AuthorityCapability.PROPOSE_STATE_UPDATE.value:
            raise ContractTypeError("StateUpdateIntent requires PROPOSE_STATE_UPDATE")
        _integer("expected_bias_version", self.expected_bias_version)
        object.__setattr__(
            self, "expected_bias_digest", _sha256("expected_bias_digest", self.expected_bias_digest)
        )
        object.__setattr__(self, "target_path", _nonempty("target_path", self.target_path))
        if not self.target_path.startswith(("/memory", "/rpm", "/operating", "/theta")):
            raise ContractTypeError("target_path is protected or unknown")
        object.__setattr__(
            self, "replacement", _frozen_object("replacement", self.replacement, nonempty=True)
        )
        object.__setattr__(self, "reason_codes", _strings("reason_codes", self.reason_codes, nonempty=True))
        object.__setattr__(self, "intent_digest", _sha256("intent_digest", self.intent_digest))


@dataclass(frozen=True, slots=True, kw_only=True)
class ModelUpdateIntent(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "MODEL_UPDATE_INTENT"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.model-update-intent/0.2"

    intent_id: str
    tick: int
    issuer_id: str
    authority_capability: str
    model_id: str
    expected_model_version: int
    expected_model_digest: str
    update_kind: ModelUpdateKind
    parameter_group_ids: tuple[str, ...]
    candidate_artifact: TensorArtifactRef
    gradient_artifact: TensorArtifactRef | None
    plasticity_ppm: int
    verifier_receipt_id: str
    qualification_receipt_id: str
    reason_codes: tuple[str, ...]
    intent_digest: str

    def __post_init__(self) -> None:
        for name in (
            "intent_id",
            "issuer_id",
            "authority_capability",
            "model_id",
            "verifier_receipt_id",
            "qualification_receipt_id",
        ):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        _integer("tick", self.tick)
        if self.authority_capability != AuthorityCapability.PROPOSE_MODEL_UPDATE.value:
            raise ContractTypeError("ModelUpdateIntent requires PROPOSE_MODEL_UPDATE")
        _integer("expected_model_version", self.expected_model_version)
        object.__setattr__(
            self, "expected_model_digest", _sha256("expected_model_digest", self.expected_model_digest)
        )
        try:
            object.__setattr__(self, "update_kind", ModelUpdateKind(self.update_kind))
        except (TypeError, ValueError) as exc:
            raise ContractTypeError("update_kind is invalid") from exc
        object.__setattr__(
            self, "parameter_group_ids", _strings("parameter_group_ids", self.parameter_group_ids, nonempty=True)
        )
        if not isinstance(self.candidate_artifact, TensorArtifactRef):
            raise ContractTypeError("candidate_artifact must be a TensorArtifactRef")
        if self.gradient_artifact is not None and not isinstance(self.gradient_artifact, TensorArtifactRef):
            raise ContractTypeError("gradient_artifact must be a TensorArtifactRef or None")
        if self.update_kind is ModelUpdateKind.GRADIENT_DELTA and self.gradient_artifact is None:
            raise ContractTypeError("GRADIENT_DELTA requires gradient_artifact")
        _ppm("plasticity_ppm", self.plasticity_ppm)
        object.__setattr__(self, "reason_codes", _strings("reason_codes", self.reason_codes, nonempty=True))
        object.__setattr__(self, "intent_digest", _sha256("intent_digest", self.intent_digest))


@dataclass(frozen=True, slots=True, kw_only=True)
class MemoryWriteIntent(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "MEMORY_WRITE_INTENT"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.memory-write-intent/0.2"

    intent_id: str
    tick: int
    issuer_id: str
    authority_capability: str
    target_bias_id: str
    expected_bias_version: int
    expected_bias_digest: str
    memory_record_id: str
    memory_kind: MemoryKind
    content: Mapping[str, Any]
    content_ref: TensorArtifactRef | None
    confidence_ppm: int
    provenance: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    verifier_receipt_id: str
    intent_digest: str

    def __post_init__(self) -> None:
        for name in (
            "intent_id",
            "issuer_id",
            "authority_capability",
            "target_bias_id",
            "memory_record_id",
            "verifier_receipt_id",
        ):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        _integer("tick", self.tick)
        if self.authority_capability != AuthorityCapability.PROPOSE_MEMORY_WRITE.value:
            raise ContractTypeError("MemoryWriteIntent requires PROPOSE_MEMORY_WRITE")
        _integer("expected_bias_version", self.expected_bias_version)
        object.__setattr__(
            self, "expected_bias_digest", _sha256("expected_bias_digest", self.expected_bias_digest)
        )
        try:
            object.__setattr__(self, "memory_kind", MemoryKind(self.memory_kind))
        except (TypeError, ValueError) as exc:
            raise ContractTypeError("memory_kind is invalid") from exc
        object.__setattr__(self, "content", _frozen_object("content", self.content, nonempty=True))
        if self.content_ref is not None and not isinstance(self.content_ref, TensorArtifactRef):
            raise ContractTypeError("content_ref must be a TensorArtifactRef or None")
        _ppm("confidence_ppm", self.confidence_ppm)
        object.__setattr__(self, "provenance", _strings("provenance", self.provenance, nonempty=True))
        object.__setattr__(self, "evidence_refs", _strings("evidence_refs", self.evidence_refs, nonempty=True))
        object.__setattr__(self, "intent_digest", _sha256("intent_digest", self.intent_digest))


@dataclass(frozen=True, slots=True, kw_only=True)
class CommitReceipt(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "COMMIT_RECEIPT"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.commit-receipt/0.2"

    receipt_id: str
    tick: int
    batch_id: str
    coordinator_id: str
    authority_contract_id: str
    authorized: bool
    disposition: CommitDisposition
    pre_state_digest: str
    post_state_digest: str
    pre_model_digest: str
    post_model_digest: str
    accepted_intent_ids: tuple[str, ...]
    rejected_intent_ids: tuple[str, ...]
    published_effect_ids: tuple[str, ...]
    opened_repair_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    atomic: bool
    rollback_of_receipt_id: str | None
    persisted_snapshot_id: str | None
    trace_id: str
    receipt_digest: str

    def __post_init__(self) -> None:
        for name in ("receipt_id", "batch_id", "coordinator_id", "authority_contract_id", "trace_id"):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        _integer("tick", self.tick)
        if not isinstance(self.authorized, bool):
            raise ContractTypeError("authorized must be boolean")
        try:
            object.__setattr__(self, "disposition", CommitDisposition(self.disposition))
        except (TypeError, ValueError) as exc:
            raise ContractTypeError("commit disposition is invalid") from exc
        for name in (
            "pre_state_digest",
            "post_state_digest",
            "pre_model_digest",
            "post_model_digest",
            "receipt_digest",
        ):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        object.__setattr__(
            self, "accepted_intent_ids", _strings("accepted_intent_ids", self.accepted_intent_ids)
        )
        object.__setattr__(
            self, "rejected_intent_ids", _strings("rejected_intent_ids", self.rejected_intent_ids)
        )
        object.__setattr__(
            self, "published_effect_ids", _strings("published_effect_ids", self.published_effect_ids)
        )
        object.__setattr__(
            self, "opened_repair_ids", _strings("opened_repair_ids", self.opened_repair_ids)
        )
        if set(self.accepted_intent_ids) & set(self.rejected_intent_ids):
            raise ContractTypeError("an intent cannot be both accepted and rejected")
        object.__setattr__(self, "reason_codes", _strings("reason_codes", self.reason_codes, nonempty=True))
        if self.atomic is not True:
            raise ContractTypeError("commit receipt must assert atomic processing")
        for name in ("rollback_of_receipt_id", "persisted_snapshot_id"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _nonempty(name, value))
        if self.disposition is CommitDisposition.COMMITTED:
            committed_outputs = (
                self.accepted_intent_ids or self.published_effect_ids or self.opened_repair_ids
            )
            if not self.authorized or not committed_outputs or self.rejected_intent_ids:
                raise ContractTypeError(
                    "COMMITTED requires authorization and at least one accepted intent, published Effect, or repair"
                )
            if self.persisted_snapshot_id is None:
                raise ContractTypeError("COMMITTED requires persisted_snapshot_id")
        if self.disposition is CommitDisposition.REJECTED:
            if self.accepted_intent_ids or self.published_effect_ids or self.opened_repair_ids:
                raise ContractTypeError("REJECTED cannot publish or accept part of a batch")
            if self.pre_state_digest != self.post_state_digest:
                raise ContractTypeError("REJECTED must leave state unchanged")
            if self.pre_model_digest != self.post_model_digest:
                raise ContractTypeError("REJECTED must leave model unchanged")
        if self.disposition is CommitDisposition.ROLLED_BACK and self.rollback_of_receipt_id is None:
            raise ContractTypeError("ROLLED_BACK requires rollback_of_receipt_id")


@dataclass(frozen=True, slots=True, kw_only=True)
class PhaseRecord(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "TICK_PHASE_RECORD"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.tick-phase-record/0.2"

    phase: TickPhase
    tick: int
    inputs: Mapping[str, Any]
    outputs: Mapping[str, Any]
    diagnostics: Mapping[str, Any]
    compute_units: int

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "phase", TickPhase(self.phase))
        except (TypeError, ValueError) as exc:
            raise ContractTypeError("tick phase is invalid") from exc
        _integer("tick", self.tick)
        _integer("compute_units", self.compute_units)
        for name in ("inputs", "outputs", "diagnostics"):
            object.__setattr__(self, name, _frozen_object(name, getattr(self, name)))


@dataclass(frozen=True, slots=True, kw_only=True)
class TickTrace(ContractModel):
    CONTRACT_TYPE: ClassVar[str] = "TICK_TRACE"
    SCHEMA_VERSION: ClassVar[str] = f"{SCHEMA_PREFIX}.tick-trace/0.2"

    trace_id: str
    tick: int
    runtime_id: str
    software_digest: str
    cause_id: str
    cjt_ids: tuple[str, ...]
    pre_state_digest: str
    post_state_digest: str
    pre_model_digest: str
    post_model_digest: str
    phases: tuple[PhaseRecord, ...]
    candidate_effect_ids: tuple[str, ...]
    published_effect_ids: tuple[str, ...]
    verifier_receipt_ids: tuple[str, ...]
    commit_receipt_id: str
    memory_read_refs: tuple[str, ...]
    memory_write_refs: tuple[str, ...]
    accepted_intent_ids: tuple[str, ...]
    rejected_intent_ids: tuple[str, ...]
    previous_trace_digest: str | None
    sealed: bool
    trace_digest: str

    def __post_init__(self) -> None:
        for name in ("trace_id", "runtime_id", "cause_id", "commit_receipt_id"):
            object.__setattr__(self, name, _nonempty(name, getattr(self, name)))
        _integer("tick", self.tick)
        for name in (
            "software_digest",
            "pre_state_digest",
            "post_state_digest",
            "pre_model_digest",
            "post_model_digest",
            "trace_digest",
        ):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        object.__setattr__(
            self, "previous_trace_digest", _optional_sha256("previous_trace_digest", self.previous_trace_digest)
        )
        for name in (
            "cjt_ids",
            "candidate_effect_ids",
            "published_effect_ids",
            "verifier_receipt_ids",
            "memory_read_refs",
            "memory_write_refs",
            "accepted_intent_ids",
            "rejected_intent_ids",
        ):
            object.__setattr__(self, name, _strings(name, getattr(self, name), nonempty=name == "cjt_ids"))
        phases = tuple(self.phases)
        if not all(isinstance(item, PhaseRecord) for item in phases):
            raise ContractTypeError("phases must contain PhaseRecord values")
        if tuple(item.phase for item in phases) != MANDATORY_TICK_ORDER:
            raise ContractTypeError("phases must follow the exact mandatory 11-phase order")
        if any(item.tick != self.tick for item in phases):
            raise ContractTypeError("every phase tick must equal the trace tick")
        object.__setattr__(self, "phases", phases)
        if set(self.accepted_intent_ids) & set(self.rejected_intent_ids):
            raise ContractTypeError("trace intent dispositions overlap")
        if self.sealed is not True:
            raise ContractTypeError("TickTrace is a sealed trace type")


__all__ = [
    "PPM_SCALE",
    "MANDATORY_TICK_ORDER",
    "BUILTIN_OPERATION_IDENTITIES",
    "ContractTypeError",
    "CauseKind",
    "ReadinessAxisName",
    "ReadinessStatus",
    "OperatingRegion",
    "SemanticOutcome",
    "VerifierDisposition",
    "OntologyStatus",
    "RepairStatus",
    "ModelUpdateKind",
    "MemoryKind",
    "CommitDisposition",
    "AuthorityCapability",
    "TickPhase",
    "TensorArtifactRef",
    "CausePacket",
    "ReadinessAxis",
    "ReadinessState",
    "StableSubstrate",
    "LocalMemory",
    "RPMState",
    "OperatingRecord",
    "ThetaRef",
    "Governance",
    "BiasState",
    "CandidateEffect",
    "PublishedEffect",
    "OperationContract",
    "VerifierReceipt",
    "RepairFrame",
    "RepairOutcome",
    "StateUpdateIntent",
    "ModelUpdateIntent",
    "MemoryWriteIntent",
    "CommitReceipt",
    "PhaseRecord",
    "TickTrace",
]
