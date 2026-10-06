"""Disabled J-Space vector JVP/VJP shadow contract.

This module verifies caller-supplied source bodies before import and binds a
replay-only vector numerical protocol.  It provides no import, autograd,
model, provider, network, filesystem, or execution path and issues no verdict.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
import re
import threading
from types import MappingProxyType
from typing import Any, NoReturn
from weakref import WeakKeyDictionary

from ._strict_json import canonical_json_bytes, freeze_json, load_json_object, sha256_bytes
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_bool,
    expect_enum,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    parse_artifact_ref,
)


JSPACE_REGISTERED_COMPONENT_SCHEMA = "cas_harness_v2.jspace_registered_component.v1"
JSPACE_VECTOR_SCHEMA = "cas_harness_v2.jspace_vector.v1"
JSPACE_SOURCE_BUNDLE_MANIFEST_SCHEMA = "cas_harness_v2.jspace_source_bundle_manifest.v1"
JSPACE_SHADOW_PROTOCOL_SCHEMA = "cas_harness_v2.jspace_shadow_protocol.v1"

JSPACE_REGISTERED_COMPONENT_MEDIA_TYPE = (
    "application/vnd.cas-harness.jspace-registered-component-v1+json"
)
JSPACE_VECTOR_MEDIA_TYPE = "application/vnd.cas-harness.jspace-vector-v1+json"
JSPACE_SOURCE_BUNDLE_MANIFEST_MEDIA_TYPE = (
    "application/vnd.cas-harness.jspace-source-bundle-manifest-v1+json"
)
JSPACE_SHADOW_PROTOCOL_MEDIA_TYPE = (
    "application/vnd.cas-harness.jspace-shadow-protocol-v1+json"
)

CORRESPONDENCE_BASIS = "CORRESPONDENCE_BASIS"
OUTPUT_FUNCTIONAL = "OUTPUT_FUNCTIONAL"
TANGENT_IDENTITY = "TANGENT_IDENTITY"
ADJOINT_IDENTITY = "ADJOINT_IDENTITY"
SOURCE_IDENTITY = "SOURCE_IDENTITY"
AUTOGRAD_IDENTITY = "AUTOGRAD_IDENTITY"
BACKEND_IDENTITY = "BACKEND_IDENTITY"
COMPONENT_ROLES = (
    CORRESPONDENCE_BASIS,
    OUTPUT_FUNCTIONAL,
    TANGENT_IDENTITY,
    ADJOINT_IDENTITY,
    SOURCE_IDENTITY,
    AUTOGRAD_IDENTITY,
    BACKEND_IDENTITY,
)

TANGENT_VECTOR = "TANGENT_VECTOR"
ADJOINT_VECTOR = "ADJOINT_VECTOR"
JVP_VECTOR = "JVP_VECTOR"
VJP_VECTOR = "VJP_VECTOR"
VECTOR_ROLES = (TANGENT_VECTOR, ADJOINT_VECTOR, JVP_VECTOR, VJP_VECTOR)

FLOAT16 = "FLOAT16"
BFLOAT16 = "BFLOAT16"
FLOAT32 = "FLOAT32"
FLOAT64 = "FLOAT64"
DTYPES = (FLOAT16, BFLOAT16, FLOAT32, FLOAT64)

TARGET = "TARGET"
MATCHED_CONTROL = "MATCHED_CONTROL"
KNOWN_FAULT = "KNOWN_FAULT"
ROW_KINDS = (TARGET, MATCHED_CONTROL, KNOWN_FAULT)

NO_FAULT = "NONE"
WRONG_TANGENT = "WRONG_TANGENT"
WRONG_ADJOINT = "WRONG_ADJOINT"
DETACHED_GRAPH = "DETACHED_GRAPH"
RANK_LOSS = "RANK_LOSS"
DTYPE_DRIFT = "DTYPE_DRIFT"
ZERO_DENOMINATOR_SCALAR_PROJECTION = "ZERO_DENOMINATOR_SCALAR_PROJECTION"
ARTIFACT_CORRUPTION = "ARTIFACT_CORRUPTION"
KNOWN_FAULT_KINDS = (
    WRONG_TANGENT,
    WRONG_ADJOINT,
    DETACHED_GRAPH,
    RANK_LOSS,
    DTYPE_DRIFT,
    ZERO_DENOMINATOR_SCALAR_PROJECTION,
    ARTIFACT_CORRUPTION,
)
FAULT_KINDS = (NO_FAULT, *KNOWN_FAULT_KINDS)

VECTOR_OUTPUT = "VECTOR_OUTPUT"
SCALAR_PROJECTION = "SCALAR_PROJECTION"
OUTPUT_PROJECTIONS = (VECTOR_OUTPUT, SCALAR_PROJECTION)
VECTOR_DENOMINATOR = "VECTOR_MAX_ABS"
ABSOLUTE_ONLY_ZERO_DENOMINATOR = "ABSOLUTE_ONLY_ZERO_DENOMINATOR"

SHADOW = "SHADOW"
NONE = "NONE"
NOT_LICENSED = "NOT_LICENSED"
NON_AUTHORITY = "NON_AUTHORITY"
REPLAY_ONLY = "REPLAY_ONLY"
UNAVAILABLE = "UNAVAILABLE"
NOT_EXECUTED = "NOT_EXECUTED"
NO_VERDICT = "NO_VERDICT"

_STATUS = MappingProxyType({
    "mode": SHADOW,
    "intervention": NONE,
    "license": NOT_LICENSED,
    "authority": NON_AUTHORITY,
    "verdict": NO_VERDICT,
})
_BOUNDARY = MappingProxyType({
    "execution": NOT_EXECUTED,
    "canary_count": 0,
    "import_calls": 0,
    "torch_calls": 0,
    "autograd_calls": 0,
    "model_calls": 0,
    "provider_calls": 0,
    "network_calls": 0,
    "filesystem_calls": 0,
    "dose_executions": 0,
    "execution_authority": "NOT_GRANTED",
})
_COMPONENT_SEMANTICS = MappingProxyType({
    CORRESPONDENCE_BASIS: "REGISTERED_CORRESPONDENCE_BASIS",
    OUTPUT_FUNCTIONAL: "EXACT_VECTOR_OUTPUT_FUNCTIONAL",
    TANGENT_IDENTITY: "REGISTERED_VECTOR_TANGENT_IDENTITY",
    ADJOINT_IDENTITY: "REGISTERED_VECTOR_ADJOINT_IDENTITY",
    SOURCE_IDENTITY: "EXACT_SOURCE_IDENTITY",
    AUTOGRAD_IDENTITY: "EXACT_AUTOGRAD_IDENTITY",
    BACKEND_IDENTITY: "EXACT_BACKEND_IDENTITY",
})
_STAGEC_NAMESPACE_RE = re.compile(r"[^a-z0-9]+")


class JSpaceShadowContractValidationError(SchemaValidationError):
    """A J-Space shadow carrier failed closed."""


class JSpaceShadowBackendUnavailableError(RuntimeError):
    """The J-Space shadow backend is deliberately unavailable."""


@dataclass(frozen=True, slots=True)
class JSpaceSourceMember:
    role: str
    artifact_ref: ArtifactRef
    body_bytes: bytes

    def __post_init__(self) -> None:
        expect_enum(self.role, set(COMPONENT_ROLES), "JSpaceSourceMember.role")
        _require_ref(self.artifact_ref, "JSpaceSourceMember.artifact_ref")
        _require_media(
            self.artifact_ref,
            JSPACE_REGISTERED_COMPONENT_MEDIA_TYPE,
            "JSpaceSourceMember.artifact_ref",
        )
        if type(self.body_bytes) is not bytes or not self.artifact_ref.verify_bytes(
            self.body_bytes
        ):
            raise JSpaceShadowContractValidationError(
                "JSpaceSourceMember body differs from its exact hash/length reference"
            )


@dataclass(frozen=True, slots=True)
class JSpaceVectorBinding:
    role: str
    artifact_ref: ArtifactRef
    body_bytes: bytes

    def __post_init__(self) -> None:
        expect_enum(self.role, set(VECTOR_ROLES), "JSpaceVectorBinding.role")
        _require_ref(self.artifact_ref, "JSpaceVectorBinding.artifact_ref")
        _require_media(
            self.artifact_ref,
            JSPACE_VECTOR_MEDIA_TYPE,
            "JSpaceVectorBinding.artifact_ref",
        )
        if type(self.body_bytes) is not bytes or not self.artifact_ref.verify_bytes(
            self.body_bytes
        ):
            raise JSpaceShadowContractValidationError(
                "JSpaceVectorBinding body differs from its exact hash/length reference"
            )


@dataclass(frozen=True, slots=True)
class JSpaceShadowRow:
    row_id: str
    row_kind: str
    fault_kind: str
    tangent_identity_matches: bool
    adjoint_identity_matches: bool
    graph_connected: bool
    expected_rank: int
    observed_rank: int
    expected_shape: tuple[int, ...]
    observed_shape: tuple[int, ...]
    expected_dtype: str
    observed_dtype: str
    all_finite: bool
    output_projection: str
    artifact_integrity: bool
    expected_vector: tuple[int, ...]
    observed_vector: tuple[int, ...]
    expected_vjp_vector: tuple[int, ...]
    observed_vjp_vector: tuple[int, ...]
    denominator_units: int
    vector_bindings: tuple[JSpaceVectorBinding, ...]


@dataclass(frozen=True, slots=True)
class JSpaceSourceBundleManifestArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    bundle_id: str
    members: tuple[JSpaceSourceMember, ...]
    dimension: int
    rank: int
    shape: tuple[int, ...]
    dtype: str
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def payload(self) -> Mapping[str, Any]:
        _, value = _canonical_object(self.raw_bytes, "source bundle raw_bytes")
        return freeze_json(value)

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.bundle_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=JSPACE_SOURCE_BUNDLE_MANIFEST_MEDIA_TYPE,
        )

    def member(self, role: str) -> JSpaceSourceMember:
        role = expect_enum(role, set(COMPONENT_ROLES), "role")
        if type(self.members) is not tuple or any(
            type(item) is not JSpaceSourceMember for item in self.members
        ):
            raise JSpaceShadowContractValidationError(
                "component members must remain exact JSpaceSourceMember values"
            )
        for index, item in enumerate(self.members):
            expect_enum(
                item.role,
                set(COMPONENT_ROLES),
                f"component members[{index}].role",
            )
        matches = tuple(item for item in self.members if item.role == role)
        if len(matches) != 1:
            raise JSpaceShadowContractValidationError(
                "component role must resolve exactly one source member"
            )
        return matches[0]


@dataclass(frozen=True, slots=True)
class JSpaceShadowProtocolArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    protocol_id: str
    source_bundle_ref: ArtifactRef
    component_refs: tuple[ArtifactRef, ...]
    dimension: int
    rank: int
    shape: tuple[int, ...]
    dtype: str
    absolute_tolerance_units: int
    relative_tolerance_ppm: int
    dose_schedule_units: tuple[int, ...]
    rows: tuple[JSpaceShadowRow, ...]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def payload(self) -> Mapping[str, Any]:
        _, value = _canonical_object(self.raw_bytes, "shadow protocol raw_bytes")
        return freeze_json(value)

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.protocol_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=JSPACE_SHADOW_PROTOCOL_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class JSpaceShadowReplayRequest:
    source_bundle_ref: ArtifactRef
    protocol_ref: ArtifactRef

    def __post_init__(self) -> None:
        _require_ref(self.source_bundle_ref, "source_bundle_ref")
        _require_media(
            self.source_bundle_ref,
            JSPACE_SOURCE_BUNDLE_MANIFEST_MEDIA_TYPE,
            "source_bundle_ref",
        )
        _require_ref(self.protocol_ref, "protocol_ref")
        _require_media(
            self.protocol_ref, JSPACE_SHADOW_PROTOCOL_MEDIA_TYPE, "protocol_ref"
        )
        _unique_ref_closure(
            (self.source_bundle_ref, self.protocol_ref), "JSpaceShadowReplayRequest"
        )


def _reject_stagec(value: str, path: str) -> str:
    if type(value) is not str:
        raise JSpaceShadowContractValidationError(f"{path} must be an exact string")
    normalized = _STAGEC_NAMESPACE_RE.sub("", value.casefold())
    if "stagec" in normalized or "ccal" in normalized:
        raise JSpaceShadowContractValidationError(
            f"{path} must not contain any Stage C identity or phase"
        )
    return value


def _machine_id(value: Any, path: str) -> str:
    result = expect_machine_id(value, path)
    return _reject_stagec(result, path)


def _require_ref(value: Any, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise JSpaceShadowContractValidationError(
            f"{path} must be an exact ArtifactRef"
        )
    if (
        type(value.artifact_id) is not str
        or type(value.sha256) is not str
        or type(value.byte_length) is not int
        or type(value.media_type) is not str
    ):
        raise JSpaceShadowContractValidationError(
            f"{path} must retain exact ArtifactRef scalar types"
        )
    _reject_stagec(value.artifact_id, f"{path}.artifact_id")
    try:
        reconstructed = ArtifactRef(
            artifact_id=value.artifact_id,
            sha256=value.sha256,
            byte_length=value.byte_length,
            media_type=value.media_type,
        )
    except (TypeError, ValueError, SchemaValidationError) as exc:
        raise JSpaceShadowContractValidationError(
            f"{path} cannot reconstruct an exact ArtifactRef: {exc}"
        ) from exc
    if not _exact_equal(reconstructed, value):
        raise JSpaceShadowContractValidationError(
            f"{path} differs from exact ArtifactRef reconstruction"
        )
    return value


def _require_media(reference: ArtifactRef, expected: str, path: str) -> None:
    if reference.media_type != expected:
        raise JSpaceShadowContractValidationError(
            f"{path} must use media type {expected}"
        )


def _ref_value(reference: ArtifactRef) -> dict[str, Any]:
    reference = _require_ref(reference, "artifact_ref")
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _parse_exact_ref(value: Any, path: str) -> ArtifactRef:
    try:
        return _require_ref(parse_artifact_ref(value, path), path)
    except JSpaceShadowContractValidationError:
        raise
    except (TypeError, ValueError, SchemaValidationError) as exc:
        raise JSpaceShadowContractValidationError(
            f"{path} is not an exact reconstructable ArtifactRef: {exc}"
        ) from exc


def _exact_equal(left: Any, right: Any) -> bool:
    """Compare immutable projections without Python's bool/int coercions."""

    if type(left) is not type(right):
        return False
    if is_dataclass(left) and not isinstance(left, type):
        return all(
            _exact_equal(getattr(left, field.name), getattr(right, field.name))
            for field in fields(left)
        )
    if type(left) in {dict, MappingProxyType}:
        if (
            any(type(key) is not str for key in left)
            or any(type(key) is not str for key in right)
            or set(left.keys()) != set(right.keys())
        ):
            return False
        return all(_exact_equal(left[key], right[key]) for key in left)
    if type(left) is tuple:
        return len(left) == len(right) and all(
            _exact_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _canonical_object(raw: Any, path: str) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise JSpaceShadowContractValidationError(
                f"{path} must use exact canonical JSON bytes"
            )
        return snapshot, value
    except JSpaceShadowContractValidationError:
        raise
    except (TypeError, ValueError) as exc:
        raise JSpaceShadowContractValidationError(f"{path}: {exc}") from exc


def _require_status_boundary(value: dict[str, Any]) -> None:
    status = expect_object(value["status"], "$.status")
    expect_keys(status, required=_STATUS, path="$.status")
    if not _exact_equal(status, dict(_STATUS)):
        raise JSpaceShadowContractValidationError(
            "J-Space status must remain SHADOW/NONE/NOT_LICENSED/NON_AUTHORITY/NO_VERDICT"
        )
    boundary = expect_object(value["boundary"], "$.boundary")
    expect_keys(boundary, required=_BOUNDARY, path="$.boundary")
    if not _exact_equal(boundary, dict(_BOUNDARY)):
        raise JSpaceShadowContractValidationError(
            "J-Space boundary must retain zero execution and canary_count=0"
        )


def _shape(value: tuple[int, ...], path: str) -> tuple[int, ...]:
    if type(value) is not tuple or not value or len(value) > 8:
        raise JSpaceShadowContractValidationError(
            f"{path} must be an exact rank-1 through rank-8 tuple"
        )
    return tuple(
        expect_int(item, f"{path}[{index}]", minimum=1)
        for index, item in enumerate(value)
    )


def _shape_dimension(shape: tuple[int, ...]) -> int:
    result = 1
    for item in shape:
        result *= item
    return result


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
            if not _exact_equal(prior, reference):
                raise JSpaceShadowContractValidationError(
                    f"{path} aliases one artifact ID to different content"
                )
            continue
        content_key = (reference.sha256, reference.byte_length)
        if content_key in by_content:
            raise JSpaceShadowContractValidationError(
                f"{path} aliases one content identity under different artifact IDs"
            )
        by_id[reference.artifact_id] = reference
        by_content[content_key] = reference
        ordered.append(reference)
    return tuple(ordered)


def _owner_closure(
    owner_id: str, references: tuple[ArtifactRef, ...], path: str
) -> tuple[ArtifactRef, ...]:
    closure = _unique_ref_closure(references, path)
    if owner_id in {item.artifact_id for item in closure}:
        raise JSpaceShadowContractValidationError(
            f"{path} collides with its owner artifact ID"
        )
    return closure


def _artifact_storage(value: Any, expected: type[Any], path: str) -> None:
    if type(value) is not expected:
        raise JSpaceShadowContractValidationError(
            f"{path} must be an exact {expected.__name__}"
        )
    missing = object()
    if (
        type(getattr(value, "raw_bytes", missing)) is not bytes
        or type(getattr(value, "sha256", missing)) is not str
        or type(getattr(value, "byte_length", missing)) is not int
        or type(getattr(value, "artifact_refs", missing)) is not tuple
    ):
        raise JSpaceShadowContractValidationError(
            f"{path} storage projections must remain exact immutable values"
        )
    if value.sha256 != sha256_bytes(value.raw_bytes) or value.byte_length != len(
        value.raw_bytes
    ):
        raise JSpaceShadowContractValidationError(
            f"{path} raw byte hash/length projections drifted"
        )
    for index, reference in enumerate(value.artifact_refs):
        _require_ref(reference, f"{path}.artifact_refs[{index}]")
    if expected is JSpaceSourceBundleManifestArtifact:
        _machine_id(value.bundle_id, f"{path}.bundle_id")
        if type(value.members) is not tuple or any(
            type(item) is not JSpaceSourceMember for item in value.members
        ):
            raise JSpaceShadowContractValidationError(
                f"{path}.members must remain exact immutable members"
            )
        expect_int(value.dimension, f"{path}.dimension", minimum=1)
        expect_int(value.rank, f"{path}.rank", minimum=1, maximum=8)
        _shape(value.shape, f"{path}.shape")
        if type(value.dtype) is not str:
            raise JSpaceShadowContractValidationError(
                f"{path}.dtype must remain an exact string"
            )
        expect_enum(value.dtype, set(DTYPES), f"{path}.dtype")
    elif expected is JSpaceShadowProtocolArtifact:
        _machine_id(value.protocol_id, f"{path}.protocol_id")
        _require_ref(value.source_bundle_ref, f"{path}.source_bundle_ref")
        if type(value.component_refs) is not tuple:
            raise JSpaceShadowContractValidationError(
                f"{path}.component_refs must remain an exact tuple"
            )
        for index, reference in enumerate(value.component_refs):
            _require_ref(reference, f"{path}.component_refs[{index}]")
        expect_int(value.dimension, f"{path}.dimension", minimum=1)
        expect_int(value.rank, f"{path}.rank", minimum=1, maximum=8)
        _shape(value.shape, f"{path}.shape")
        if type(value.dtype) is not str:
            raise JSpaceShadowContractValidationError(
                f"{path}.dtype must remain an exact string"
            )
        expect_enum(value.dtype, set(DTYPES), f"{path}.dtype")
        expect_int(
            value.absolute_tolerance_units,
            f"{path}.absolute_tolerance_units",
            minimum=0,
            maximum=2**31 - 1,
        )
        expect_int(
            value.relative_tolerance_ppm,
            f"{path}.relative_tolerance_ppm",
            minimum=0,
            maximum=1_000_000,
        )
        _dose_schedule(value.dose_schedule_units)
        if type(value.rows) is not tuple or any(
            type(item) is not JSpaceShadowRow for item in value.rows
        ):
            raise JSpaceShadowContractValidationError(
                f"{path}.rows must remain exact immutable rows"
            )


def build_jspace_registered_component_body(
    *,
    component_id: str,
    role: str,
    dimension: int,
    rank: int,
    shape: tuple[int, ...],
    dtype: str,
) -> bytes:
    """Build one exact registered source/basis/functional/vector identity body."""

    component_id = _machine_id(component_id, "component_id")
    role = expect_enum(role, set(COMPONENT_ROLES), "role")
    shape = _shape(shape, "shape")
    rank = expect_int(rank, "rank", minimum=1, maximum=8)
    if rank != len(shape):
        raise JSpaceShadowContractValidationError("rank must equal shape rank")
    dimension = expect_int(dimension, "dimension", minimum=1)
    if dimension != _shape_dimension(shape):
        raise JSpaceShadowContractValidationError(
            "dimension must equal the exact shape element count"
        )
    dtype = expect_enum(dtype, set(DTYPES), "dtype")
    return canonical_json_bytes(
        {
            "schema": JSPACE_REGISTERED_COMPONENT_SCHEMA,
            "component_id": component_id,
            "role": role,
            "semantic": _COMPONENT_SEMANTICS[role],
            "dimension": dimension,
            "rank": rank,
            "shape": list(shape),
            "dtype": dtype,
            "finite_required": True,
            "registration": "EXACT_BODY_REGISTERED",
            "status": dict(_STATUS),
            "boundary": dict(_BOUNDARY),
        }
    )


def build_jspace_vector_body(
    *,
    vector_id: str,
    row_id: str,
    role: str,
    dimension: int,
    dtype: str,
    registered_values: tuple[int, ...],
    observed_values: tuple[int, ...],
) -> bytes:
    """Build one exact, non-executable tangent, adjoint, JVP, or VJP body."""

    vector_id = _machine_id(vector_id, "vector_id")
    row_id = _machine_id(row_id, "row_id")
    if vector_id == row_id:
        raise JSpaceShadowContractValidationError(
            "vector_id must not collide with its row owner"
        )
    role = expect_enum(role, set(VECTOR_ROLES), "role")
    dimension = expect_int(dimension, "dimension", minimum=1)
    dtype = expect_enum(dtype, set(DTYPES), "dtype")
    registered = _vector(registered_values, dimension, "registered_values")
    observed = _vector(observed_values, dimension, "observed_values")
    return canonical_json_bytes(
        {
            "schema": JSPACE_VECTOR_SCHEMA,
            "vector_id": vector_id,
            "row_id": row_id,
            "role": role,
            "dimension": dimension,
            "dtype": dtype,
            "registered_values": list(registered),
            "observed_values": list(observed),
            "finite_required": True,
            "representation": "EXACT_INTEGER_VECTOR_UNITS",
            "status": dict(_STATUS),
            "boundary": dict(_BOUNDARY),
        }
    )


def _validate_vector_binding(
    binding: Any,
    *,
    row_id: str,
    role: str,
    dimension: int,
    dtype: str,
    path: str,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if type(binding) is not JSpaceVectorBinding:
        raise JSpaceShadowContractValidationError(
            f"{path} must be an exact JSpaceVectorBinding"
        )
    if binding.role != role:
        raise JSpaceShadowContractValidationError(
            f"{path} must retain exact vector role order"
        )
    reference = _require_ref(binding.artifact_ref, f"{path}.artifact_ref")
    _require_media(reference, JSPACE_VECTOR_MEDIA_TYPE, f"{path}.artifact_ref")
    if type(binding.body_bytes) is not bytes:
        raise JSpaceShadowContractValidationError(
            f"{path}.body_bytes must be exact immutable bytes"
        )
    snapshot, value = _canonical_object(binding.body_bytes, f"{path}.body")
    if not reference.verify_bytes(snapshot):
        raise JSpaceShadowContractValidationError(
            f"{path} body differs from its exact hash/length reference"
        )
    expect_keys(
        value,
        required={
            "schema", "vector_id", "row_id", "role", "dimension", "dtype",
            "registered_values", "observed_values", "finite_required",
            "representation", "status", "boundary",
        },
        path=f"{path}.body",
    )
    if value["schema"] != JSPACE_VECTOR_SCHEMA:
        raise JSpaceShadowContractValidationError(f"{path} vector schema drifted")
    if _machine_id(value["vector_id"], f"{path}.body.vector_id") != reference.artifact_id:
        raise JSpaceShadowContractValidationError(
            f"{path} vector ID differs from its exact ArtifactRef"
        )
    if _machine_id(value["row_id"], f"{path}.body.row_id") != row_id:
        raise JSpaceShadowContractValidationError(
            f"{path} vector body is bound to a different row"
        )
    if value["vector_id"] == row_id:
        raise JSpaceShadowContractValidationError(
            f"{path} vector ID collides with its row owner"
        )
    if expect_enum(value["role"], set(VECTOR_ROLES), f"{path}.body.role") != role:
        raise JSpaceShadowContractValidationError(
            f"{path} vector body role drifted"
        )
    if expect_int(value["dimension"], f"{path}.body.dimension", minimum=1) != dimension:
        raise JSpaceShadowContractValidationError(
            f"{path} vector body dimension drifted"
        )
    if expect_enum(value["dtype"], set(DTYPES), f"{path}.body.dtype") != dtype:
        raise JSpaceShadowContractValidationError(f"{path} vector body dtype drifted")
    registered = _vector(
        tuple(expect_list(value["registered_values"], f"{path}.body.registered_values")),
        dimension,
        f"{path}.body.registered_values",
    )
    observed = _vector(
        tuple(expect_list(value["observed_values"], f"{path}.body.observed_values")),
        dimension,
        f"{path}.body.observed_values",
    )
    if not expect_bool(value["finite_required"], f"{path}.body.finite_required"):
        raise JSpaceShadowContractValidationError(
            f"{path} vector body must require finite values"
        )
    if value["representation"] != "EXACT_INTEGER_VECTOR_UNITS":
        raise JSpaceShadowContractValidationError(
            f"{path} vector representation drifted"
        )
    _require_status_boundary(value)
    return registered, observed


def _validate_vector_bindings(
    bindings: tuple[JSpaceVectorBinding, ...],
    *,
    row_id: str,
    dimension: int,
    dtype: str,
    path: str,
) -> dict[str, tuple[tuple[int, ...], tuple[int, ...]]]:
    if type(bindings) is not tuple or len(bindings) != len(VECTOR_ROLES):
        raise JSpaceShadowContractValidationError(
            f"{path} must contain four exact vector bindings"
        )
    if any(type(item) is not JSpaceVectorBinding for item in bindings):
        raise JSpaceShadowContractValidationError(
            f"{path} must contain exact JSpaceVectorBinding values"
        )
    for index, item in enumerate(bindings):
        expect_enum(item.role, set(VECTOR_ROLES), f"{path}[{index}].role")
    if tuple(item.role for item in bindings) != VECTOR_ROLES:
        raise JSpaceShadowContractValidationError(
            f"{path} must order tangent, adjoint, JVP, then VJP"
        )
    values = {
        role: _validate_vector_binding(
            binding,
            row_id=row_id,
            role=role,
            dimension=dimension,
            dtype=dtype,
            path=f"{path}[{index}]",
        )
        for index, (role, binding) in enumerate(zip(VECTOR_ROLES, bindings, strict=True))
    }
    refs = tuple(binding.artifact_ref for binding in bindings)
    if len(_unique_ref_closure(refs, path)) != len(refs):
        raise JSpaceShadowContractValidationError(
            f"{path} must use four distinct vector artifacts"
        )
    return values


def _validate_component_body(
    member: JSpaceSourceMember,
) -> tuple[bytes, int, int, tuple[int, ...], str]:
    if type(member) is not JSpaceSourceMember:
        raise JSpaceShadowContractValidationError(
            "source bundle members must be exact JSpaceSourceMember values"
        )
    expect_enum(member.role, set(COMPONENT_ROLES), "source bundle member role")
    _require_ref(member.artifact_ref, "source bundle member artifact_ref")
    _require_media(
        member.artifact_ref,
        JSPACE_REGISTERED_COMPONENT_MEDIA_TYPE,
        "source bundle member artifact_ref",
    )
    if type(member.body_bytes) is not bytes:
        raise JSpaceShadowContractValidationError(
            "source bundle member body must remain exact bytes"
        )
    snapshot, value = _canonical_object(
        member.body_bytes, f"component[{member.role}]"
    )
    if not member.artifact_ref.verify_bytes(snapshot):
        raise JSpaceShadowContractValidationError(
            "component body hash or byte length disagrees before import"
        )
    expect_keys(
        value,
        required={
            "schema", "component_id", "role", "semantic", "dimension", "rank",
            "shape", "dtype", "finite_required", "registration", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != JSPACE_REGISTERED_COMPONENT_SCHEMA:
        raise JSpaceShadowContractValidationError("component schema drifted")
    if _machine_id(value["component_id"], "$.component_id") != member.artifact_ref.artifact_id:
        raise JSpaceShadowContractValidationError(
            "component ID differs from its exact artifact reference"
        )
    if expect_enum(value["role"], set(COMPONENT_ROLES), "$.role") != member.role:
        raise JSpaceShadowContractValidationError("component role drifted")
    if value["semantic"] != _COMPONENT_SEMANTICS[member.role]:
        raise JSpaceShadowContractValidationError("component semantic binding drifted")
    raw_shape = expect_list(value["shape"], "$.shape")
    shape = _shape(tuple(raw_shape), "$.shape")
    rank = expect_int(value["rank"], "$.rank", minimum=1, maximum=8)
    dimension = expect_int(value["dimension"], "$.dimension", minimum=1)
    if rank != len(shape) or dimension != _shape_dimension(shape):
        raise JSpaceShadowContractValidationError(
            "component dimension/rank/shape binding drifted"
        )
    dtype = expect_enum(value["dtype"], set(DTYPES), "$.dtype")
    if not expect_bool(value["finite_required"], "$.finite_required"):
        raise JSpaceShadowContractValidationError("component must require finite vectors")
    if value["registration"] != "EXACT_BODY_REGISTERED":
        raise JSpaceShadowContractValidationError("component is not exactly registered")
    _require_status_boundary(value)
    return snapshot, dimension, rank, shape, dtype


def _validate_members(
    members: tuple[JSpaceSourceMember, ...],
) -> tuple[tuple[JSpaceSourceMember, ...], int, int, tuple[int, ...], str]:
    if type(members) is not tuple or len(members) != len(COMPONENT_ROLES):
        raise JSpaceShadowContractValidationError(
            "source bundle must contain every fixed component role exactly once"
        )
    if any(type(item) is not JSpaceSourceMember for item in members):
        raise JSpaceShadowContractValidationError(
            "source bundle members must be exact JSpaceSourceMember values"
        )
    for index, item in enumerate(members):
        expect_enum(
            item.role,
            set(COMPONENT_ROLES),
            f"source bundle members[{index}].role",
        )
    if tuple(item.role for item in members) != COMPONENT_ROLES:
        raise JSpaceShadowContractValidationError(
            "source bundle components must use the exact fixed role order"
        )
    geometry: tuple[int, int, tuple[int, ...], str] | None = None
    validated: list[JSpaceSourceMember] = []
    for member in members:
        _snapshot, dimension, rank, shape, dtype = _validate_component_body(member)
        current = (dimension, rank, shape, dtype)
        if geometry is None:
            geometry = current
        elif not _exact_equal(current, geometry):
            raise JSpaceShadowContractValidationError(
                "source, basis, functional, vector, autograd, and backend geometry drifted"
            )
        validated.append(member)
    assert geometry is not None
    _unique_ref_closure(
        tuple(item.artifact_ref for item in validated), "source bundle components"
    )
    return tuple(validated), *geometry


def _manifest_value(
    *,
    bundle_id: str,
    members: tuple[JSpaceSourceMember, ...],
    dimension: int,
    rank: int,
    shape: tuple[int, ...],
    dtype: str,
) -> dict[str, Any]:
    return {
        "schema": JSPACE_SOURCE_BUNDLE_MANIFEST_SCHEMA,
        "bundle_id": bundle_id,
        "members": [
            {"role": item.role, "artifact_ref": _ref_value(item.artifact_ref)}
            for item in members
        ],
        "dimension": dimension,
        "rank": rank,
        "shape": list(shape),
        "dtype": dtype,
        "verification_order": "VERIFY_EVERY_BODY_BEFORE_IMPORT",
        "all_bodies_verified": True,
        "import_state": "NOT_IMPORTED",
        "import_authority": "NONE",
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_jspace_source_bundle_manifest(
    raw: Any,
    *,
    members: tuple[JSpaceSourceMember, ...],
) -> JSpaceSourceBundleManifestArtifact:
    members, dimension, rank, shape, dtype = _validate_members(members)
    snapshot, value = _canonical_object(raw, "J-Space source bundle manifest")
    expect_keys(
        value,
        required={
            "schema", "bundle_id", "members", "dimension", "rank", "shape",
            "dtype", "verification_order", "all_bodies_verified", "import_state",
            "import_authority", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != JSPACE_SOURCE_BUNDLE_MANIFEST_SCHEMA:
        raise JSpaceShadowContractValidationError("source bundle schema drifted")
    bundle_id = _machine_id(value["bundle_id"], "$.bundle_id")
    raw_members = expect_list(value["members"], "$.members")
    if len(raw_members) != len(members):
        raise JSpaceShadowContractValidationError(
            "source bundle manifest is missing or duplicating a component"
        )
    for index, (raw_member, member) in enumerate(
        zip(raw_members, members, strict=True)
    ):
        row = expect_object(raw_member, f"$.members[{index}]")
        expect_keys(row, required={"role", "artifact_ref"}, path=f"$.members[{index}]")
        if (
            expect_enum(row["role"], set(COMPONENT_ROLES), f"$.members[{index}].role")
            != member.role
            or not _exact_equal(
                _parse_exact_ref(
                    row["artifact_ref"], f"$.members[{index}].artifact_ref"
                ),
                member.artifact_ref,
            )
        ):
            raise JSpaceShadowContractValidationError(
                "source bundle component role or exact body reference drifted"
            )
    raw_shape = expect_list(value["shape"], "$.shape")
    if (
        expect_int(value["dimension"], "$.dimension", minimum=1) != dimension
        or expect_int(value["rank"], "$.rank", minimum=1) != rank
        or _shape(tuple(raw_shape), "$.shape") != shape
        or expect_enum(value["dtype"], set(DTYPES), "$.dtype") != dtype
    ):
        raise JSpaceShadowContractValidationError(
            "source bundle dimension/rank/shape/dtype projection drifted"
        )
    if (
        value["verification_order"] != "VERIFY_EVERY_BODY_BEFORE_IMPORT"
        or not expect_bool(value["all_bodies_verified"], "$.all_bodies_verified")
        or value["import_state"] != "NOT_IMPORTED"
        or value["import_authority"] != "NONE"
    ):
        raise JSpaceShadowContractValidationError(
            "source bodies must verify before import and remain NOT_IMPORTED"
        )
    _require_status_boundary(value)
    refs = _owner_closure(
        bundle_id,
        tuple(item.artifact_ref for item in members),
        "source bundle artifact closure",
    )
    return JSpaceSourceBundleManifestArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        bundle_id=bundle_id,
        members=members,
        dimension=dimension,
        rank=rank,
        shape=shape,
        dtype=dtype,
        artifact_refs=refs,
    )


def build_jspace_source_bundle_manifest(
    *,
    bundle_id: str,
    members: tuple[JSpaceSourceMember, ...],
) -> JSpaceSourceBundleManifestArtifact:
    """Verify every exact component body and build a NOT_IMPORTED manifest."""

    bundle_id = _machine_id(bundle_id, "bundle_id")
    members, dimension, rank, shape, dtype = _validate_members(members)
    raw = canonical_json_bytes(
        _manifest_value(
            bundle_id=bundle_id,
            members=members,
            dimension=dimension,
            rank=rank,
            shape=shape,
            dtype=dtype,
        )
    )
    return _load_jspace_source_bundle_manifest(raw, members=members)


def load_jspace_source_bundle_manifest(
    raw: Any,
    *,
    members: tuple[JSpaceSourceMember, ...],
) -> JSpaceSourceBundleManifestArtifact:
    return _load_jspace_source_bundle_manifest(raw, members=members)


def replay_jspace_source_bundle_manifest(
    manifest: JSpaceSourceBundleManifestArtifact,
) -> JSpaceSourceBundleManifestArtifact:
    _artifact_storage(
        manifest, JSpaceSourceBundleManifestArtifact, "source bundle manifest"
    )
    if type(manifest.members) is not tuple or any(
        type(item) is not JSpaceSourceMember for item in manifest.members
    ):
        raise JSpaceShadowContractValidationError(
            "source bundle member projections must remain exact immutable types"
        )
    replayed = _load_jspace_source_bundle_manifest(
        manifest.raw_bytes, members=manifest.members
    )
    if not _exact_equal(replayed, manifest):
        raise JSpaceShadowContractValidationError(
            "source bundle manifest differs from exact-byte replay"
        )
    return replayed


def _vector(value: tuple[int, ...], dimension: int, path: str) -> tuple[int, ...]:
    if type(value) is not tuple or len(value) != dimension:
        raise JSpaceShadowContractValidationError(
            f"{path} must be an exact integer tuple matching dimension"
        )
    return tuple(
        expect_int(item, f"{path}[{index}]", minimum=-(2**31), maximum=2**31 - 1)
        for index, item in enumerate(value)
    )


def _row_defects(row: JSpaceShadowRow) -> set[str]:
    defects: set[str] = set()
    if not row.tangent_identity_matches:
        defects.add(WRONG_TANGENT)
    if not row.adjoint_identity_matches:
        defects.add(WRONG_ADJOINT)
    if not row.graph_connected:
        defects.add(DETACHED_GRAPH)
    if row.observed_rank != row.expected_rank or row.observed_shape != row.expected_shape:
        defects.add(RANK_LOSS)
    if row.observed_dtype != row.expected_dtype:
        defects.add(DTYPE_DRIFT)
    if row.output_projection == SCALAR_PROJECTION and row.denominator_units == 0:
        defects.add(ZERO_DENOMINATOR_SCALAR_PROJECTION)
    if not row.artifact_integrity:
        defects.add(ARTIFACT_CORRUPTION)
    return defects


def _validate_row(
    row: Any,
    *,
    dimension: int,
    rank: int,
    shape: tuple[int, ...],
    dtype: str,
    absolute_tolerance_units: int,
    relative_tolerance_ppm: int,
    path: str,
) -> JSpaceShadowRow:
    if type(row) is not JSpaceShadowRow:
        raise JSpaceShadowContractValidationError(
            f"{path} must be an exact JSpaceShadowRow"
        )
    _machine_id(row.row_id, f"{path}.row_id")
    kind = expect_enum(row.row_kind, set(ROW_KINDS), f"{path}.row_kind")
    fault = expect_enum(row.fault_kind, set(FAULT_KINDS), f"{path}.fault_kind")
    for field in (
        row.tangent_identity_matches,
        row.adjoint_identity_matches,
        row.graph_connected,
        row.all_finite,
        row.artifact_integrity,
    ):
        if type(field) is not bool:
            raise JSpaceShadowContractValidationError(
                f"{path} identity/graph/finite/integrity flags must be exact booleans"
            )
    expected_rank = expect_int(
        row.expected_rank, f"{path}.expected_rank", minimum=1, maximum=8
    )
    observed_rank = expect_int(
        row.observed_rank, f"{path}.observed_rank", minimum=0, maximum=8
    )
    expected_shape = _shape(row.expected_shape, f"{path}.expected_shape")
    if type(row.observed_shape) is not tuple or len(row.observed_shape) != observed_rank:
        raise JSpaceShadowContractValidationError(
            f"{path}.observed_shape must exactly match observed rank"
        )
    observed_shape = tuple(
        expect_int(item, f"{path}.observed_shape[{index}]", minimum=1)
        for index, item in enumerate(row.observed_shape)
    )
    expected_dtype = expect_enum(
        row.expected_dtype, set(DTYPES), f"{path}.expected_dtype"
    )
    observed_dtype = expect_enum(
        row.observed_dtype, set(DTYPES), f"{path}.observed_dtype"
    )
    projection = expect_enum(
        row.output_projection,
        set(OUTPUT_PROJECTIONS),
        f"{path}.output_projection",
    )
    expected_vector = _vector(row.expected_vector, dimension, f"{path}.expected_vector")
    observed_vector = _vector(row.observed_vector, dimension, f"{path}.observed_vector")
    expected_vjp_vector = _vector(
        row.expected_vjp_vector, dimension, f"{path}.expected_vjp_vector"
    )
    observed_vjp_vector = _vector(
        row.observed_vjp_vector, dimension, f"{path}.observed_vjp_vector"
    )
    vector_values = _validate_vector_bindings(
        row.vector_bindings,
        row_id=row.row_id,
        dimension=dimension,
        dtype=expected_dtype,
        path=f"{path}.vector_bindings",
    )
    tangent_registered, tangent_observed = vector_values[TANGENT_VECTOR]
    adjoint_registered, adjoint_observed = vector_values[ADJOINT_VECTOR]
    jvp_registered, jvp_observed = vector_values[JVP_VECTOR]
    vjp_registered, vjp_observed = vector_values[VJP_VECTOR]
    if row.tangent_identity_matches is not (
        tangent_registered == tangent_observed
    ):
        raise JSpaceShadowContractValidationError(
            f"{path} tangent identity flag differs from exact tangent vectors"
        )
    if row.adjoint_identity_matches is not (
        adjoint_registered == adjoint_observed
    ):
        raise JSpaceShadowContractValidationError(
            f"{path} adjoint identity flag differs from exact adjoint vectors"
        )
    if jvp_registered != expected_vector or jvp_observed != observed_vector:
        raise JSpaceShadowContractValidationError(
            f"{path} JVP body differs from exact row JVP vectors"
        )
    if (
        vjp_registered != expected_vjp_vector
        or vjp_observed != observed_vjp_vector
    ):
        raise JSpaceShadowContractValidationError(
            f"{path} VJP body differs from exact row VJP vectors"
        )
    denominator = expect_int(
        row.denominator_units, f"{path}.denominator_units", minimum=0
    )
    computed_denominator = max(
        *(abs(item) for item in expected_vector),
        *(abs(item) for item in expected_vjp_vector),
    )
    if denominator != computed_denominator:
        raise JSpaceShadowContractValidationError(
            f"{path} denominator must equal vector max-absolute magnitude"
        )
    maximum_error = max(
        *(
            abs(observed - expected)
            for observed, expected in zip(
                observed_vector, expected_vector, strict=True
            )
        ),
        *(
            abs(observed - expected)
            for observed, expected in zip(
                observed_vjp_vector, expected_vjp_vector, strict=True
            )
        ),
    )
    relative_allowance = (
        0
        if denominator == 0
        else (relative_tolerance_ppm * denominator + 999_999) // 1_000_000
    )
    if maximum_error > absolute_tolerance_units + relative_allowance:
        raise JSpaceShadowContractValidationError(
            f"{path} replay fixture exceeds explicit integer tolerances"
        )
    if (
        expected_rank != rank
        or expected_shape != shape
        or expected_dtype != dtype
    ):
        raise JSpaceShadowContractValidationError(
            f"{path} expected rank/shape/dtype differs from registered source bundle"
        )
    defects = _row_defects(row)
    if kind in {TARGET, MATCHED_CONTROL}:
        if fault != NO_FAULT or defects:
            raise JSpaceShadowContractValidationError(
                f"{path} target/control rows cannot contain a known fault"
            )
        if not row.all_finite or projection != VECTOR_OUTPUT:
            raise JSpaceShadowContractValidationError(
                f"{path} target/control rows require finite vector output"
            )
    else:
        if fault == NO_FAULT or defects != {fault}:
            raise JSpaceShadowContractValidationError(
                f"{path} known-fault row must contain exactly its declared defect"
            )
        if fault == RANK_LOSS and not (
            observed_rank == rank - 1 and len(observed_shape) == observed_rank
        ):
            raise JSpaceShadowContractValidationError(
                f"{path} rank-loss fixture must lose exactly one rank"
            )
        if fault == ZERO_DENOMINATOR_SCALAR_PROJECTION and not (
            denominator == 0
            and all(item == 0 for item in expected_vector)
            and all(item == 0 for item in expected_vjp_vector)
            and projection == SCALAR_PROJECTION
        ):
            raise JSpaceShadowContractValidationError(
                f"{path} scalar-projection fault requires an exact zero denominator"
            )
        if fault != ARTIFACT_CORRUPTION and not row.artifact_integrity:
            raise JSpaceShadowContractValidationError(
                f"{path} non-corruption fault must retain artifact integrity"
            )
        if fault not in {DETACHED_GRAPH} and not row.graph_connected:
            raise JSpaceShadowContractValidationError(
                f"{path} non-detached fault must retain graph connection"
            )
        if not row.all_finite:
            raise JSpaceShadowContractValidationError(
                f"{path} known-fault fixture must remain finite"
            )
    return row


def _validate_rows(
    rows: tuple[JSpaceShadowRow, ...],
    *,
    dimension: int,
    rank: int,
    shape: tuple[int, ...],
    dtype: str,
    absolute_tolerance_units: int,
    relative_tolerance_ppm: int,
) -> tuple[JSpaceShadowRow, ...]:
    if type(rows) is not tuple or len(rows) < 9 or len(rows) > 512:
        raise JSpaceShadowContractValidationError(
            "rows require target, matched control, and seven known-fault fixtures"
        )
    validated = tuple(
        _validate_row(
            row,
            dimension=dimension,
            rank=rank,
            shape=shape,
            dtype=dtype,
            absolute_tolerance_units=absolute_tolerance_units,
            relative_tolerance_ppm=relative_tolerance_ppm,
            path=f"rows[{index}]",
        )
        for index, row in enumerate(rows)
    )
    ids = tuple(row.row_id for row in validated)
    if len(ids) != len(set(ids)):
        raise JSpaceShadowContractValidationError("shadow rows contain duplicate IDs")
    vector_refs = tuple(
        binding.artifact_ref
        for row in validated
        for binding in row.vector_bindings
    )
    if len(_unique_ref_closure(vector_refs, "shadow vector artifact closure")) != len(
        vector_refs
    ):
        raise JSpaceShadowContractValidationError(
            "every shadow row must use four distinct vector artifacts"
        )
    target_rows = tuple(row for row in validated if row.row_kind == TARGET)
    controls = tuple(row for row in validated if row.row_kind == MATCHED_CONTROL)
    faults = tuple(row for row in validated if row.row_kind == KNOWN_FAULT)
    if not target_rows or not controls:
        raise JSpaceShadowContractValidationError(
            "shadow protocol requires target and matched-control rows"
        )
    if tuple(row.fault_kind for row in faults) != KNOWN_FAULT_KINDS:
        raise JSpaceShadowContractValidationError(
            "shadow protocol requires every known fault exactly once in fixed order"
        )
    if validated != (*target_rows, *controls, *faults):
        raise JSpaceShadowContractValidationError(
            "shadow rows must order targets, matched controls, then known faults"
        )
    return validated


def _binding_value(binding: JSpaceVectorBinding) -> dict[str, Any]:
    if type(binding) is not JSpaceVectorBinding:
        raise JSpaceShadowContractValidationError(
            "row vector bindings must remain exact JSpaceVectorBinding values"
        )
    _require_ref(binding.artifact_ref, "row.vector_binding.artifact_ref")
    if type(binding.body_bytes) is not bytes:
        raise JSpaceShadowContractValidationError(
            "row vector binding body must remain exact bytes"
        )
    return {
        "role": binding.role,
        "artifact_ref": _ref_value(binding.artifact_ref),
        "body_hex": binding.body_bytes.hex(),
    }


def _parse_binding(value: Any, path: str) -> JSpaceVectorBinding:
    item = expect_object(value, path)
    expect_keys(
        item, required={"role", "artifact_ref", "body_hex"}, path=path
    )
    role = expect_enum(item["role"], set(VECTOR_ROLES), f"{path}.role")
    reference = _parse_exact_ref(item["artifact_ref"], f"{path}.artifact_ref")
    body_hex = item["body_hex"]
    if (
        type(body_hex) is not str
        or not body_hex
        or len(body_hex) % 2
        or re.fullmatch(r"[0-9a-f]+", body_hex) is None
    ):
        raise JSpaceShadowContractValidationError(
            f"{path}.body_hex must be nonblank canonical lowercase hex"
        )
    body = bytes.fromhex(body_hex)
    if body.hex() != body_hex:
        raise JSpaceShadowContractValidationError(
            f"{path}.body_hex is not an exact byte encoding"
        )
    return JSpaceVectorBinding(role=role, artifact_ref=reference, body_bytes=body)


def _row_value(row: JSpaceShadowRow) -> dict[str, Any]:
    return {
        "row_id": row.row_id,
        "row_kind": row.row_kind,
        "fault_kind": row.fault_kind,
        "tangent_identity_matches": row.tangent_identity_matches,
        "adjoint_identity_matches": row.adjoint_identity_matches,
        "graph_connected": row.graph_connected,
        "expected_rank": row.expected_rank,
        "observed_rank": row.observed_rank,
        "expected_shape": list(row.expected_shape),
        "observed_shape": list(row.observed_shape),
        "expected_dtype": row.expected_dtype,
        "observed_dtype": row.observed_dtype,
        "all_finite": row.all_finite,
        "output_projection": row.output_projection,
        "artifact_integrity": row.artifact_integrity,
        "expected_vector": list(row.expected_vector),
        "observed_vector": list(row.observed_vector),
        "expected_vjp_vector": list(row.expected_vjp_vector),
        "observed_vjp_vector": list(row.observed_vjp_vector),
        "denominator_units": row.denominator_units,
        "vector_bindings": [_binding_value(item) for item in row.vector_bindings],
    }


def _parse_row(value: Any, path: str) -> JSpaceShadowRow:
    row = expect_object(value, path)
    required = {
        "row_id", "row_kind", "fault_kind", "tangent_identity_matches",
        "adjoint_identity_matches", "graph_connected", "expected_rank",
        "observed_rank", "expected_shape", "observed_shape", "expected_dtype",
        "observed_dtype", "all_finite", "output_projection", "artifact_integrity",
        "expected_vector", "observed_vector", "expected_vjp_vector",
        "observed_vjp_vector", "denominator_units", "vector_bindings",
    }
    expect_keys(row, required=required, path=path)
    return JSpaceShadowRow(
        row_id=_machine_id(row["row_id"], f"{path}.row_id"),
        row_kind=expect_enum(row["row_kind"], set(ROW_KINDS), f"{path}.row_kind"),
        fault_kind=expect_enum(row["fault_kind"], set(FAULT_KINDS), f"{path}.fault_kind"),
        tangent_identity_matches=expect_bool(
            row["tangent_identity_matches"], f"{path}.tangent_identity_matches"
        ),
        adjoint_identity_matches=expect_bool(
            row["adjoint_identity_matches"], f"{path}.adjoint_identity_matches"
        ),
        graph_connected=expect_bool(row["graph_connected"], f"{path}.graph_connected"),
        expected_rank=expect_int(row["expected_rank"], f"{path}.expected_rank"),
        observed_rank=expect_int(row["observed_rank"], f"{path}.observed_rank"),
        expected_shape=tuple(expect_list(row["expected_shape"], f"{path}.expected_shape")),
        observed_shape=tuple(expect_list(row["observed_shape"], f"{path}.observed_shape", nonempty=False)),
        expected_dtype=expect_enum(row["expected_dtype"], set(DTYPES), f"{path}.expected_dtype"),
        observed_dtype=expect_enum(row["observed_dtype"], set(DTYPES), f"{path}.observed_dtype"),
        all_finite=expect_bool(row["all_finite"], f"{path}.all_finite"),
        output_projection=expect_enum(
            row["output_projection"], set(OUTPUT_PROJECTIONS), f"{path}.output_projection"
        ),
        artifact_integrity=expect_bool(row["artifact_integrity"], f"{path}.artifact_integrity"),
        expected_vector=tuple(expect_list(row["expected_vector"], f"{path}.expected_vector")),
        observed_vector=tuple(expect_list(row["observed_vector"], f"{path}.observed_vector")),
        expected_vjp_vector=tuple(
            expect_list(row["expected_vjp_vector"], f"{path}.expected_vjp_vector")
        ),
        observed_vjp_vector=tuple(
            expect_list(row["observed_vjp_vector"], f"{path}.observed_vjp_vector")
        ),
        denominator_units=expect_int(row["denominator_units"], f"{path}.denominator_units"),
        vector_bindings=tuple(
            _parse_binding(item, f"{path}.vector_bindings[{index}]")
            for index, item in enumerate(
                expect_list(row["vector_bindings"], f"{path}.vector_bindings")
            )
        ),
    )


def _dose_schedule(value: tuple[int, ...]) -> tuple[int, ...]:
    if type(value) is not tuple:
        raise JSpaceShadowContractValidationError(
            "dose_schedule_units must be an exact tuple"
        )
    if not value:
        return ()
    doses = tuple(
        expect_int(item, f"dose_schedule_units[{index}]", minimum=0)
        for index, item in enumerate(value)
    )
    if len(doses) < 2 or doses[0] != 0 or any(
        later <= earlier for earlier, later in zip(doses, doses[1:])
    ):
        raise JSpaceShadowContractValidationError(
            "bound dose schedule must start at zero and increase strictly"
        )
    return doses


def _protocol_value(
    *,
    protocol_id: str,
    source_bundle: JSpaceSourceBundleManifestArtifact,
    absolute_tolerance_units: int,
    relative_tolerance_ppm: int,
    dose_schedule_units: tuple[int, ...],
    rows: tuple[JSpaceShadowRow, ...],
) -> dict[str, Any]:
    return {
        "schema": JSPACE_SHADOW_PROTOCOL_SCHEMA,
        "protocol_id": protocol_id,
        "phase": SHADOW,
        "intervention": NONE,
        "source_bundle_ref": _ref_value(source_bundle.artifact_ref),
        "component_refs": {
            role: _ref_value(source_bundle.member(role).artifact_ref)
            for role in COMPONENT_ROLES
        },
        "dimension": source_bundle.dimension,
        "rank": source_bundle.rank,
        "shape": list(source_bundle.shape),
        "dtype": source_bundle.dtype,
        "finite_required": True,
        "output_functional": "EXACT_VECTOR_OUTPUT",
        "tangent_identity": "EXACT_REGISTERED_VECTOR",
        "adjoint_identity": "EXACT_REGISTERED_VECTOR",
        "denominator": VECTOR_DENOMINATOR,
        "zero_denominator_policy": ABSOLUTE_ONLY_ZERO_DENOMINATOR,
        "absolute_tolerance_units": absolute_tolerance_units,
        "relative_tolerance_ppm": relative_tolerance_ppm,
        "dose_schedule_units": list(dose_schedule_units),
        "dose_execution": NONE,
        "rows": [_row_value(row) for row in rows],
        "result_scope": "FIXTURE_CONTRACT_ONLY_NO_VERDICT",
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_jspace_shadow_protocol(
    raw: Any,
    *,
    source_bundle: JSpaceSourceBundleManifestArtifact,
) -> JSpaceShadowProtocolArtifact:
    source_bundle = replay_jspace_source_bundle_manifest(source_bundle)
    snapshot, value = _canonical_object(raw, "J-Space shadow protocol")
    expect_keys(
        value,
        required={
            "schema", "protocol_id", "phase", "intervention", "source_bundle_ref",
            "component_refs", "dimension", "rank", "shape", "dtype",
            "finite_required", "output_functional", "tangent_identity",
            "adjoint_identity", "denominator", "zero_denominator_policy",
            "absolute_tolerance_units", "relative_tolerance_ppm",
            "dose_schedule_units", "dose_execution", "rows", "result_scope",
            "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != JSPACE_SHADOW_PROTOCOL_SCHEMA:
        raise JSpaceShadowContractValidationError("shadow protocol schema drifted")
    protocol_id = _machine_id(value["protocol_id"], "$.protocol_id")
    if value["phase"] != SHADOW or value["intervention"] != NONE:
        raise JSpaceShadowContractValidationError(
            "J-Space protocol phase/intervention must remain SHADOW/NONE"
        )
    if not _exact_equal(
        _parse_exact_ref(value["source_bundle_ref"], "$.source_bundle_ref"),
        source_bundle.artifact_ref,
    ):
        raise JSpaceShadowContractValidationError(
            "shadow protocol source bundle reference drifted"
        )
    component_map = expect_object(value["component_refs"], "$.component_refs")
    expect_keys(component_map, required=COMPONENT_ROLES, path="$.component_refs")
    component_refs: list[ArtifactRef] = []
    for role in COMPONENT_ROLES:
        parsed = _parse_exact_ref(component_map[role], f"$.component_refs.{role}")
        expected = source_bundle.member(role).artifact_ref
        if not _exact_equal(parsed, expected):
            raise JSpaceShadowContractValidationError(
                "shadow protocol registered component identity drifted"
            )
        component_refs.append(parsed)
    raw_shape = expect_list(value["shape"], "$.shape")
    if (
        expect_int(value["dimension"], "$.dimension", minimum=1)
        != source_bundle.dimension
        or expect_int(value["rank"], "$.rank", minimum=1) != source_bundle.rank
        or _shape(tuple(raw_shape), "$.shape") != source_bundle.shape
        or expect_enum(value["dtype"], set(DTYPES), "$.dtype")
        != source_bundle.dtype
        or not expect_bool(value["finite_required"], "$.finite_required")
    ):
        raise JSpaceShadowContractValidationError(
            "shadow protocol dimension/rank/shape/dtype/finite binding drifted"
        )
    if (
        value["output_functional"] != "EXACT_VECTOR_OUTPUT"
        or value["tangent_identity"] != "EXACT_REGISTERED_VECTOR"
        or value["adjoint_identity"] != "EXACT_REGISTERED_VECTOR"
        or value["denominator"] != VECTOR_DENOMINATOR
        or value["zero_denominator_policy"]
        != ABSOLUTE_ONLY_ZERO_DENOMINATOR
    ):
        raise JSpaceShadowContractValidationError(
            "vector functional, tangent, adjoint, or zero-denominator policy drifted"
        )
    absolute = expect_int(
        value["absolute_tolerance_units"],
        "$.absolute_tolerance_units",
        minimum=0,
        maximum=2**31 - 1,
    )
    relative = expect_int(
        value["relative_tolerance_ppm"],
        "$.relative_tolerance_ppm",
        minimum=0,
        maximum=1_000_000,
    )
    if absolute == 0 and relative == 0:
        raise JSpaceShadowContractValidationError(
            "at least one explicit integer tolerance must be nonzero"
        )
    raw_doses = expect_list(
        value["dose_schedule_units"], "$.dose_schedule_units", nonempty=False
    )
    doses = _dose_schedule(tuple(raw_doses))
    if value["dose_execution"] != NONE:
        raise JSpaceShadowContractValidationError(
            "dose schedule may bind but cannot execute"
        )
    raw_rows = expect_list(value["rows"], "$.rows")
    rows = _validate_rows(
        tuple(_parse_row(item, f"$.rows[{index}]") for index, item in enumerate(raw_rows)),
        dimension=source_bundle.dimension,
        rank=source_bundle.rank,
        shape=source_bundle.shape,
        dtype=source_bundle.dtype,
        absolute_tolerance_units=absolute,
        relative_tolerance_ppm=relative,
    )
    if value["result_scope"] != "FIXTURE_CONTRACT_ONLY_NO_VERDICT":
        raise JSpaceShadowContractValidationError(
            "J-Space shadow protocol cannot grant a verdict"
        )
    _require_status_boundary(value)
    refs = _owner_closure(
        protocol_id,
        (
            source_bundle.artifact_ref,
            *source_bundle.artifact_refs,
            *component_refs,
            *(
                binding.artifact_ref
                for row in rows
                for binding in row.vector_bindings
            ),
        ),
        "shadow protocol artifact closure",
    )
    return JSpaceShadowProtocolArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        protocol_id=protocol_id,
        source_bundle_ref=source_bundle.artifact_ref,
        component_refs=tuple(component_refs),
        dimension=source_bundle.dimension,
        rank=source_bundle.rank,
        shape=source_bundle.shape,
        dtype=source_bundle.dtype,
        absolute_tolerance_units=absolute,
        relative_tolerance_ppm=relative,
        dose_schedule_units=doses,
        rows=rows,
        artifact_refs=refs,
    )


def build_jspace_shadow_protocol(
    *,
    protocol_id: str,
    source_bundle: JSpaceSourceBundleManifestArtifact,
    absolute_tolerance_units: int,
    relative_tolerance_ppm: int,
    dose_schedule_units: tuple[int, ...],
    rows: tuple[JSpaceShadowRow, ...],
    phase: str,
    intervention: str,
) -> JSpaceShadowProtocolArtifact:
    """Build a disabled vector JVP/VJP fixture contract with no verdict."""

    protocol_id = _machine_id(protocol_id, "protocol_id")
    if type(phase) is not str or type(intervention) is not str:
        raise JSpaceShadowContractValidationError(
            "phase and intervention must be exact strings"
        )
    _reject_stagec(phase, "phase")
    if phase != SHADOW or intervention != NONE:
        raise JSpaceShadowContractValidationError(
            "J-Space protocol requires exact SHADOW phase and NONE intervention"
        )
    source_bundle = replay_jspace_source_bundle_manifest(source_bundle)
    absolute = expect_int(
        absolute_tolerance_units,
        "absolute_tolerance_units",
        minimum=0,
        maximum=2**31 - 1,
    )
    relative = expect_int(
        relative_tolerance_ppm,
        "relative_tolerance_ppm",
        minimum=0,
        maximum=1_000_000,
    )
    if absolute == 0 and relative == 0:
        raise JSpaceShadowContractValidationError(
            "at least one explicit integer tolerance must be nonzero"
        )
    doses = _dose_schedule(dose_schedule_units)
    rows = _validate_rows(
        rows,
        dimension=source_bundle.dimension,
        rank=source_bundle.rank,
        shape=source_bundle.shape,
        dtype=source_bundle.dtype,
        absolute_tolerance_units=absolute,
        relative_tolerance_ppm=relative,
    )
    raw = canonical_json_bytes(
        _protocol_value(
            protocol_id=protocol_id,
            source_bundle=source_bundle,
            absolute_tolerance_units=absolute,
            relative_tolerance_ppm=relative,
            dose_schedule_units=doses,
            rows=rows,
        )
    )
    return _load_jspace_shadow_protocol(raw, source_bundle=source_bundle)


def load_jspace_shadow_protocol(
    raw: Any,
    *,
    source_bundle: JSpaceSourceBundleManifestArtifact,
) -> JSpaceShadowProtocolArtifact:
    return _load_jspace_shadow_protocol(raw, source_bundle=source_bundle)


def replay_jspace_shadow_protocol(
    protocol: JSpaceShadowProtocolArtifact,
    *,
    source_bundle: JSpaceSourceBundleManifestArtifact,
) -> JSpaceShadowProtocolArtifact:
    _artifact_storage(protocol, JSpaceShadowProtocolArtifact, "shadow protocol")
    if type(protocol.rows) is not tuple or any(
        type(item) is not JSpaceShadowRow for item in protocol.rows
    ):
        raise JSpaceShadowContractValidationError(
            "shadow row projections must remain exact immutable types"
        )
    replayed = _load_jspace_shadow_protocol(
        protocol.raw_bytes, source_bundle=source_bundle
    )
    if not _exact_equal(replayed, protocol):
        raise JSpaceShadowContractValidationError(
            "J-Space shadow protocol differs from exact-byte replay"
        )
    return replayed


@dataclass(slots=True)
class _ReplaySeal:
    source_bundle: JSpaceSourceBundleManifestArtifact
    protocol: JSpaceShadowProtocolArtifact
    request: JSpaceShadowReplayRequest
    signature: tuple[Any, ...]
    consumed: bool
    lock: threading.RLock


@dataclass(frozen=True, slots=True)
class _UnavailableSeal:
    source_bundle: JSpaceSourceBundleManifestArtifact
    signature: tuple[Any, ...]
    reason: str


_SEAL_LOCK = threading.RLock()
_REPLAY_SEALS: WeakKeyDictionary[Any, _ReplaySeal] = WeakKeyDictionary()
_UNAVAILABLE_SEALS: WeakKeyDictionary[Any, _UnavailableSeal] = WeakKeyDictionary()


def _factory_only(name: str) -> NoReturn:
    raise TypeError(f"{name} is factory-only")


def _not_copyable(name: str) -> NoReturn:
    raise TypeError(f"{name} cannot be copied, replaced, or pickled")


class ReplayJSpaceShadowBackend:
    """Process-sealed, single-use replay of one disabled shadow protocol."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: Any, **kwargs: Any) -> ReplayJSpaceShadowBackend:
        del args, kwargs
        _factory_only("ReplayJSpaceShadowBackend")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("ReplayJSpaceShadowBackend cannot be subclassed")

    def __copy__(self) -> NoReturn:
        _not_copyable("ReplayJSpaceShadowBackend")

    def __deepcopy__(self, memo: Any) -> NoReturn:
        del memo
        _not_copyable("ReplayJSpaceShadowBackend")

    def __reduce__(self) -> NoReturn:
        _not_copyable("ReplayJSpaceShadowBackend")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _not_copyable("ReplayJSpaceShadowBackend")

    def __replace__(self, **changes: Any) -> NoReturn:
        del changes
        _not_copyable("ReplayJSpaceShadowBackend")

    @property
    def mode(self) -> str:
        _require_replay_seal(self)
        return REPLAY_ONLY

    @property
    def phase(self) -> str:
        _require_replay_seal(self)
        return SHADOW

    @property
    def intervention(self) -> str:
        _require_replay_seal(self)
        return NONE

    @property
    def canary_count(self) -> int:
        _require_replay_seal(self)
        return 0

    def replay(self, request: JSpaceShadowReplayRequest) -> JSpaceShadowProtocolArtifact:
        seal = _require_replay_seal(self)
        with seal.lock:
            if seal.consumed:
                raise JSpaceShadowContractValidationError(
                    "J-Space shadow replay was already consumed exactly once"
                )
            _verify_replay_seal(seal)
            if type(request) is not JSpaceShadowReplayRequest or request is not seal.request:
                raise JSpaceShadowContractValidationError(
                    "J-Space replay requires the exact sealed request object"
                )
            detached = replay_jspace_shadow_protocol(
                seal.protocol, source_bundle=seal.source_bundle
            )
            if detached is seal.protocol:
                raise JSpaceShadowContractValidationError(
                    "J-Space shadow replay did not detach its return value"
                )
            seal.consumed = True
            return detached


class UnavailableJSpaceShadowBackend:
    """A sealed unavailable backend that ignores caller input before failure."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: Any, **kwargs: Any) -> UnavailableJSpaceShadowBackend:
        del args, kwargs
        _factory_only("UnavailableJSpaceShadowBackend")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("UnavailableJSpaceShadowBackend cannot be subclassed")

    def __copy__(self) -> NoReturn:
        _not_copyable("UnavailableJSpaceShadowBackend")

    def __deepcopy__(self, memo: Any) -> NoReturn:
        del memo
        _not_copyable("UnavailableJSpaceShadowBackend")

    def __reduce__(self) -> NoReturn:
        _not_copyable("UnavailableJSpaceShadowBackend")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _not_copyable("UnavailableJSpaceShadowBackend")

    def __replace__(self, **changes: Any) -> NoReturn:
        del changes
        _not_copyable("UnavailableJSpaceShadowBackend")

    @property
    def mode(self) -> str:
        _require_unavailable_seal(self)
        return UNAVAILABLE

    @property
    def phase(self) -> str:
        _require_unavailable_seal(self)
        return SHADOW

    @property
    def intervention(self) -> str:
        _require_unavailable_seal(self)
        return NONE

    @property
    def canary_count(self) -> int:
        _require_unavailable_seal(self)
        return 0

    def replay(self, request: object) -> NoReturn:
        del request
        seal = _require_unavailable_seal(self)
        raise JSpaceShadowBackendUnavailableError(seal.reason)


def _bundle_signature(bundle: JSpaceSourceBundleManifestArtifact) -> tuple[Any, ...]:
    return (
        bundle.artifact_ref,
        bundle.raw_bytes,
        bundle.artifact_refs,
        tuple(
            (member.role, member.artifact_ref, member.body_bytes)
            for member in bundle.members
        ),
    )


def _replay_signature(
    bundle: JSpaceSourceBundleManifestArtifact,
    protocol: JSpaceShadowProtocolArtifact,
) -> tuple[Any, ...]:
    return (
        *_bundle_signature(bundle),
        protocol.artifact_ref,
        protocol.raw_bytes,
        protocol.artifact_refs,
        protocol.rows,
    )


def build_replay_jspace_shadow_backend(
    *,
    source_bundle: JSpaceSourceBundleManifestArtifact,
    protocol: JSpaceShadowProtocolArtifact,
) -> tuple[ReplayJSpaceShadowBackend, JSpaceShadowReplayRequest]:
    """Seal one exact disabled protocol for single-use replay."""

    source_bundle = replay_jspace_source_bundle_manifest(source_bundle)
    protocol = replay_jspace_shadow_protocol(
        protocol, source_bundle=source_bundle
    )
    request = JSpaceShadowReplayRequest(
        source_bundle_ref=source_bundle.artifact_ref,
        protocol_ref=protocol.artifact_ref,
    )
    backend = object.__new__(ReplayJSpaceShadowBackend)
    seal = _ReplaySeal(
        source_bundle=source_bundle,
        protocol=protocol,
        request=request,
        signature=_replay_signature(source_bundle, protocol),
        consumed=False,
        lock=threading.RLock(),
    )
    with _SEAL_LOCK:
        _REPLAY_SEALS[backend] = seal
    return backend, request


def build_unavailable_jspace_shadow_backend(
    *,
    source_bundle: JSpaceSourceBundleManifestArtifact,
    reason: str,
) -> UnavailableJSpaceShadowBackend:
    """Build a source-bound backend that can only report unavailability."""

    source_bundle = replay_jspace_source_bundle_manifest(source_bundle)
    if type(reason) is not str or not reason.strip() or len(reason) > 512:
        raise JSpaceShadowContractValidationError(
            "reason must be a nonblank exact string of at most 512 characters"
        )
    backend = object.__new__(UnavailableJSpaceShadowBackend)
    seal = _UnavailableSeal(
        source_bundle=source_bundle,
        signature=_bundle_signature(source_bundle),
        reason=reason,
    )
    with _SEAL_LOCK:
        _UNAVAILABLE_SEALS[backend] = seal
    return backend


def _require_replay_seal(backend: object) -> _ReplaySeal:
    if type(backend) is not ReplayJSpaceShadowBackend:
        raise JSpaceShadowContractValidationError(
            "replay backend has a substituted exact type"
        )
    with _SEAL_LOCK:
        seal = _REPLAY_SEALS.get(backend)
    if seal is None:
        raise JSpaceShadowContractValidationError(
            "replay backend is not an exact process-sealed factory result"
        )
    return seal


def _require_unavailable_seal(backend: object) -> _UnavailableSeal:
    if type(backend) is not UnavailableJSpaceShadowBackend:
        raise JSpaceShadowContractValidationError(
            "unavailable backend has a substituted exact type"
        )
    with _SEAL_LOCK:
        seal = _UNAVAILABLE_SEALS.get(backend)
    if seal is None:
        raise JSpaceShadowContractValidationError(
            "unavailable backend is not an exact process-sealed factory result"
        )
    replayed = replay_jspace_source_bundle_manifest(seal.source_bundle)
    if not _exact_equal(_bundle_signature(replayed), seal.signature):
        raise JSpaceShadowContractValidationError(
            "sealed unavailable J-Space source bundle was mutated"
        )
    return seal


def _verify_replay_seal(seal: _ReplaySeal) -> None:
    bundle = replay_jspace_source_bundle_manifest(seal.source_bundle)
    protocol = replay_jspace_shadow_protocol(
        seal.protocol, source_bundle=bundle
    )
    current = _replay_signature(bundle, protocol)
    expected_request = JSpaceShadowReplayRequest(
        source_bundle_ref=bundle.artifact_ref,
        protocol_ref=protocol.artifact_ref,
    )
    if not _exact_equal(current, seal.signature) or not _exact_equal(
        expected_request, seal.request
    ):
        raise JSpaceShadowContractValidationError(
            "sealed J-Space replay bundle was mutated"
        )


def replay_jspace_shadow(
    backend: object,
    request: object,
) -> JSpaceShadowProtocolArtifact:
    """Dispatch only to exact replay or unavailable built-in backends."""

    if type(backend) is ReplayJSpaceShadowBackend:
        if type(request) is not JSpaceShadowReplayRequest:
            raise JSpaceShadowContractValidationError(
                "replay backend requires an exact JSpaceShadowReplayRequest"
            )
        return backend.replay(request)
    if type(backend) is UnavailableJSpaceShadowBackend:
        return backend.replay(request)
    raise JSpaceShadowContractValidationError(
        "arbitrary, live, torch, autograd, model, provider, network, or filesystem backends are not installed"
    )


__all__ = (
    "JSPACE_REGISTERED_COMPONENT_SCHEMA",
    "JSPACE_VECTOR_SCHEMA",
    "JSPACE_SOURCE_BUNDLE_MANIFEST_SCHEMA",
    "JSPACE_SHADOW_PROTOCOL_SCHEMA",
    "JSPACE_REGISTERED_COMPONENT_MEDIA_TYPE",
    "JSPACE_VECTOR_MEDIA_TYPE",
    "JSPACE_SOURCE_BUNDLE_MANIFEST_MEDIA_TYPE",
    "JSPACE_SHADOW_PROTOCOL_MEDIA_TYPE",
    "CORRESPONDENCE_BASIS",
    "OUTPUT_FUNCTIONAL",
    "TANGENT_IDENTITY",
    "ADJOINT_IDENTITY",
    "SOURCE_IDENTITY",
    "AUTOGRAD_IDENTITY",
    "BACKEND_IDENTITY",
    "COMPONENT_ROLES",
    "TANGENT_VECTOR",
    "ADJOINT_VECTOR",
    "JVP_VECTOR",
    "VJP_VECTOR",
    "VECTOR_ROLES",
    "FLOAT16",
    "BFLOAT16",
    "FLOAT32",
    "FLOAT64",
    "DTYPES",
    "TARGET",
    "MATCHED_CONTROL",
    "KNOWN_FAULT",
    "ROW_KINDS",
    "NO_FAULT",
    "WRONG_TANGENT",
    "WRONG_ADJOINT",
    "DETACHED_GRAPH",
    "RANK_LOSS",
    "DTYPE_DRIFT",
    "ZERO_DENOMINATOR_SCALAR_PROJECTION",
    "ARTIFACT_CORRUPTION",
    "KNOWN_FAULT_KINDS",
    "FAULT_KINDS",
    "VECTOR_OUTPUT",
    "SCALAR_PROJECTION",
    "OUTPUT_PROJECTIONS",
    "VECTOR_DENOMINATOR",
    "ABSOLUTE_ONLY_ZERO_DENOMINATOR",
    "SHADOW",
    "NONE",
    "NOT_LICENSED",
    "NON_AUTHORITY",
    "REPLAY_ONLY",
    "UNAVAILABLE",
    "NOT_EXECUTED",
    "NO_VERDICT",
    "JSpaceShadowContractValidationError",
    "JSpaceShadowBackendUnavailableError",
    "JSpaceSourceMember",
    "JSpaceVectorBinding",
    "JSpaceShadowRow",
    "JSpaceSourceBundleManifestArtifact",
    "JSpaceShadowProtocolArtifact",
    "JSpaceShadowReplayRequest",
    "build_jspace_registered_component_body",
    "build_jspace_vector_body",
    "build_jspace_source_bundle_manifest",
    "load_jspace_source_bundle_manifest",
    "replay_jspace_source_bundle_manifest",
    "build_jspace_shadow_protocol",
    "load_jspace_shadow_protocol",
    "replay_jspace_shadow_protocol",
    "ReplayJSpaceShadowBackend",
    "UnavailableJSpaceShadowBackend",
    "build_replay_jspace_shadow_backend",
    "build_unavailable_jspace_shadow_backend",
    "replay_jspace_shadow",
)
