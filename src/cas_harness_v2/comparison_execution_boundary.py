"""Canonical blocked-execution and zero-spend records for model comparison.

The only buildable execution state in this module is blocked.  No positive
authorization, provider adapter, model call, network operation, or spending
implementation is installed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from ._strict_json import (
    canonical_json_bytes,
    freeze_json,
    load_json_object,
    sha256_bytes,
    thaw_json,
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
from .comparison_model_protocol import NON_AUTHORITY, STRUCTURE_ONLY
from .comparison_shared_protocol import (
    FrozenComparisonRosterArtifact,
    SharedComparisonProtocolArtifact,
    replay_frozen_comparison_roster,
    replay_shared_comparison_protocol,
)


COMPARISON_EXECUTION_BOUNDARY_SCHEMA = (
    "cas_harness_v2.comparison_execution_boundary.v1"
)
COMPARISON_ZERO_SPEND_RECORD_SCHEMA = (
    "cas_harness_v2.comparison_zero_spend_record.v1"
)
COMPARISON_EXECUTION_BOUNDARY_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-execution-boundary-v1+json"
)
COMPARISON_ZERO_SPEND_RECORD_MEDIA_TYPE = (
    "application/vnd.cas-harness.comparison-zero-spend-record-v1+json"
)

BLOCKED_MISSING_EXACT_EXTERNAL_AUTHORIZATION = (
    "BLOCKED_MISSING_EXACT_EXTERNAL_AUTHORIZATION"
)
NOT_EXECUTED = "NOT_EXECUTED"
ZERO_SPEND = "ZERO_SPEND"
REQUIRED_MISSING_FIELDS = (
    "EXACT_OPEN_MODEL_AND_IMMUTABLE_REVISION",
    "EXACT_CLOSED_MODEL_AND_IMMUTABLE_REVISION",
    "PROVIDER_PERMISSIONS",
    "EXACT_MAX_SPEND",
    "AUTHORIZATION_WINDOW_START_UTC",
    "AUTHORIZATION_WINDOW_EXPIRY_UTC",
    "AUTHENTICATED_ONE_USE_NONCE",
    "DURABLE_NONCE_CONSUMPTION_LEDGER",
    "TRUSTED_CURRENT_TIME",
)

_STATUS = MappingProxyType(
    {
        "scope": STRUCTURE_ONLY,
        "authority": NON_AUTHORITY,
        "execution": NOT_EXECUTED,
        "authorization": BLOCKED_MISSING_EXACT_EXTERNAL_AUTHORIZATION,
    }
)
_ZERO_ACTIVITY = MappingProxyType(
    {
        "provider_calls": 0,
        "model_calls": 0,
        "gpu_allocations": 0,
        "runpod_runs": 0,
        "network_calls": 0,
        "spend_microusd": 0,
    }
)


class ComparisonExecutionBoundaryValidationError(SchemaValidationError):
    """A blocked execution or zero-spend carrier violated its closed schema."""


@dataclass(frozen=True, slots=True)
class BlockedComparisonExecutionBoundaryArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    boundary_id: str
    program_id: str
    protocol_ref: ArtifactRef
    roster_ref: ArtifactRef
    open_identity_ref: ArtifactRef
    closed_identity_ref: ArtifactRef
    open_configuration_ref: ArtifactRef
    closed_configuration_ref: ArtifactRef
    evaluation_count: int
    missing_fields: tuple[str, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.boundary_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=COMPARISON_EXECUTION_BOUNDARY_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class ZeroComparisonSpendRecordArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    spend_record_id: str
    boundary_ref: ArtifactRef
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.spend_record_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=COMPARISON_ZERO_SPEND_RECORD_MEDIA_TYPE,
        )


def _require_ref(value: Any, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise ComparisonExecutionBoundaryValidationError(
            f"{path} must be an exact ArtifactRef"
        )
    try:
        ArtifactRef(
            artifact_id=value.artifact_id,
            sha256=value.sha256,
            byte_length=value.byte_length,
            media_type=value.media_type,
        )
    except (TypeError, ValueError, SchemaValidationError) as exc:
        raise ComparisonExecutionBoundaryValidationError(
            f"{path} is a forged ArtifactRef: {exc}"
        ) from exc
    return value


def _ref_value(value: ArtifactRef) -> dict[str, Any]:
    value = _require_ref(value, "artifact_ref")
    return {
        "artifact_id": value.artifact_id,
        "sha256": value.sha256,
        "byte_length": value.byte_length,
        "media_type": value.media_type,
    }


def _canonical(raw: bytes | bytearray | memoryview, path: str) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
    except (TypeError, ValueError) as exc:
        raise ComparisonExecutionBoundaryValidationError(f"{path}: {exc}") from exc
    if snapshot != canonical_json_bytes(value):
        raise ComparisonExecutionBoundaryValidationError(
            f"{path} must use canonical JSON"
        )
    return snapshot, value


def _require_frozen(value: Any, path: str) -> None:
    if type(value) is MappingProxyType:
        for key, child in value.items():
            if type(key) is not str:
                raise ComparisonExecutionBoundaryValidationError(
                    f"{path} has a non-string key"
                )
            _require_frozen(child, f"{path}.{key}")
        return
    if type(value) is tuple:
        for index, child in enumerate(value):
            _require_frozen(child, f"{path}[{index}]")
        return
    if type(value) not in (str, int, bool) and value is not None:
        raise ComparisonExecutionBoundaryValidationError(
            f"{path} is not recursively frozen"
        )


def _require_distinct_refs(
    references: tuple[ArtifactRef, ...], *, owner_id: str, path: str
) -> tuple[ArtifactRef, ...]:
    ids: set[str] = set()
    content: set[tuple[str, int]] = set()
    for index, reference in enumerate(references):
        reference = _require_ref(reference, f"{path}[{index}]")
        if reference.artifact_id == owner_id or reference.artifact_id in ids:
            raise ComparisonExecutionBoundaryValidationError(
                f"{path} reuses or collides with an artifact_id"
            )
        content_key = (reference.sha256, reference.byte_length)
        if content_key in content:
            raise ComparisonExecutionBoundaryValidationError(
                f"{path} reuses content under another role"
            )
        ids.add(reference.artifact_id)
        content.add(content_key)
    return references


def _validated_dependencies(
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
) -> tuple[SharedComparisonProtocolArtifact, FrozenComparisonRosterArtifact]:
    protocol = replay_shared_comparison_protocol(protocol)
    roster = replay_frozen_comparison_roster(roster)
    if roster.protocol.artifact_ref != protocol.artifact_ref:
        raise ComparisonExecutionBoundaryValidationError(
            "roster differs from the exact shared protocol"
        )
    return protocol, roster


def _boundary_value(
    *,
    boundary_id: str,
    program_id: str,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
) -> dict[str, Any]:
    return {
        "schema": COMPARISON_EXECUTION_BOUNDARY_SCHEMA,
        "boundary_id": boundary_id,
        "program_id": program_id,
        "protocol_ref": _ref_value(protocol.artifact_ref),
        "roster_ref": _ref_value(roster.artifact_ref),
        "models": {
            "open_identity_ref": _ref_value(protocol.open_identity.artifact_ref),
            "closed_identity_ref": _ref_value(protocol.closed_identity.artifact_ref),
            "open_configuration_ref": _ref_value(protocol.open_configuration_ref),
            "closed_configuration_ref": _ref_value(protocol.closed_configuration_ref),
        },
        "execution_limits": {
            "evaluations": len(roster.cases),
            "attempts_per_case": 1,
            "retries": 0,
            "replacements": 0,
            "current_generation_calls": 0,
            "current_interventions": 0,
        },
        "external_authorization": {
            "state": BLOCKED_MISSING_EXACT_EXTERNAL_AUTHORIZATION,
            "missing_fields": list(REQUIRED_MISSING_FIELDS),
            "window_start_utc": None,
            "window_expiry_utc": None,
            "max_spend_microusd": None,
            "nonce": None,
            "consumed_at": None,
        },
        "activity": dict(_ZERO_ACTIVITY),
        "status": dict(_STATUS),
    }


def build_blocked_comparison_execution_boundary(
    *,
    boundary_id: str,
    program_id: str,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
) -> BlockedComparisonExecutionBoundaryArtifact:
    """Build the only installed execution state: blocked before any call."""

    protocol, roster = _validated_dependencies(protocol, roster)
    boundary_id = expect_machine_id(boundary_id, "boundary_id")
    program_id = expect_machine_id(program_id, "program_id")
    if "stagec" in program_id.casefold() or "c-cal" in program_id.casefold():
        raise ComparisonExecutionBoundaryValidationError(
            "comparison execution cannot reuse the current Stage C program or phase"
        )
    raw = canonical_json_bytes(
        _boundary_value(
            boundary_id=boundary_id,
            program_id=program_id,
            protocol=protocol,
            roster=roster,
        )
    )
    return load_blocked_comparison_execution_boundary(
        raw,
        boundary_ref=ArtifactRef(
            artifact_id=boundary_id,
            sha256=sha256_bytes(raw),
            byte_length=len(raw),
            media_type=COMPARISON_EXECUTION_BOUNDARY_MEDIA_TYPE,
        ),
        protocol=protocol,
        roster=roster,
    )


def load_blocked_comparison_execution_boundary(
    raw: bytes | bytearray | memoryview,
    *,
    boundary_ref: ArtifactRef,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
) -> BlockedComparisonExecutionBoundaryArtifact:
    protocol, roster = _validated_dependencies(protocol, roster)
    boundary_ref = _require_ref(boundary_ref, "boundary_ref")
    if boundary_ref.media_type != COMPARISON_EXECUTION_BOUNDARY_MEDIA_TYPE:
        raise ComparisonExecutionBoundaryValidationError(
            "boundary_ref media type changed"
        )
    snapshot, value = _canonical(raw, "execution boundary")
    if not boundary_ref.verify_bytes(snapshot):
        raise ComparisonExecutionBoundaryValidationError(
            "execution boundary bytes differ from boundary_ref"
        )
    expect_keys(
        value,
        required={
            "schema",
            "boundary_id",
            "program_id",
            "protocol_ref",
            "roster_ref",
            "models",
            "execution_limits",
            "external_authorization",
            "activity",
            "status",
        },
        path="$",
    )
    if value["schema"] != COMPARISON_EXECUTION_BOUNDARY_SCHEMA:
        raise ComparisonExecutionBoundaryValidationError("boundary schema changed")
    boundary_id = expect_machine_id(value["boundary_id"], "$.boundary_id")
    program_id = expect_machine_id(value["program_id"], "$.program_id")
    if boundary_id != boundary_ref.artifact_id:
        raise ComparisonExecutionBoundaryValidationError("boundary identity changed")
    if "stagec" in program_id.casefold() or "c-cal" in program_id.casefold():
        raise ComparisonExecutionBoundaryValidationError(
            "comparison boundary collides with Stage C"
        )
    if (
        parse_artifact_ref(value["protocol_ref"], "$.protocol_ref")
        != protocol.artifact_ref
        or parse_artifact_ref(value["roster_ref"], "$.roster_ref")
        != roster.artifact_ref
    ):
        raise ComparisonExecutionBoundaryValidationError(
            "protocol or roster binding changed"
        )
    models = expect_object(value["models"], "$.models")
    expect_keys(
        models,
        required={
            "open_identity_ref",
            "closed_identity_ref",
            "open_configuration_ref",
            "closed_configuration_ref",
        },
        path="$.models",
    )
    model_refs = (
        protocol.open_identity.artifact_ref,
        protocol.closed_identity.artifact_ref,
        protocol.open_configuration_ref,
        protocol.closed_configuration_ref,
    )
    if tuple(
        parse_artifact_ref(models[name], f"$.models.{name}")
        for name in (
            "open_identity_ref",
            "closed_identity_ref",
            "open_configuration_ref",
            "closed_configuration_ref",
        )
    ) != model_refs:
        raise ComparisonExecutionBoundaryValidationError("model binding changed")
    limits = expect_object(value["execution_limits"], "$.execution_limits")
    expected_limits = {
        "evaluations": len(roster.cases),
        "attempts_per_case": 1,
        "retries": 0,
        "replacements": 0,
        "current_generation_calls": 0,
        "current_interventions": 0,
    }
    if limits != expected_limits or any(type(item) is not int for item in limits.values()):
        raise ComparisonExecutionBoundaryValidationError("execution limits changed")
    authorization = expect_object(
        value["external_authorization"], "$.external_authorization"
    )
    expect_keys(
        authorization,
        required={
            "state",
            "missing_fields",
            "window_start_utc",
            "window_expiry_utc",
            "max_spend_microusd",
            "nonce",
            "consumed_at",
        },
        path="$.external_authorization",
    )
    missing = expect_list(
        authorization["missing_fields"], "$.external_authorization.missing_fields"
    )
    if (
        authorization["state"] != BLOCKED_MISSING_EXACT_EXTERNAL_AUTHORIZATION
        or tuple(missing) != REQUIRED_MISSING_FIELDS
        or any(type(item) is not str for item in missing)
        or any(
            authorization[name] is not None
            for name in (
                "window_start_utc",
                "window_expiry_utc",
                "max_spend_microusd",
                "nonce",
                "consumed_at",
            )
        )
    ):
        raise ComparisonExecutionBoundaryValidationError(
            "external authorization must remain explicitly blocked"
        )
    activity = expect_object(value["activity"], "$.activity")
    status = expect_object(value["status"], "$.status")
    if (
        activity != _ZERO_ACTIVITY
        or any(type(item) is not int for item in activity.values())
        or status != _STATUS
        or any(type(item) is not str for item in status.values())
    ):
        raise ComparisonExecutionBoundaryValidationError(
            "activity or status made an execution claim"
        )
    refs = _require_distinct_refs(
        (protocol.artifact_ref, roster.artifact_ref, *model_refs),
        owner_id=boundary_id,
        path="artifact_refs",
    )
    return BlockedComparisonExecutionBoundaryArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        boundary_id=boundary_id,
        program_id=program_id,
        protocol_ref=protocol.artifact_ref,
        roster_ref=roster.artifact_ref,
        open_identity_ref=model_refs[0],
        closed_identity_ref=model_refs[1],
        open_configuration_ref=model_refs[2],
        closed_configuration_ref=model_refs[3],
        evaluation_count=len(roster.cases),
        missing_fields=REQUIRED_MISSING_FIELDS,
        payload=freeze_json(value),
        artifact_refs=refs,
    )


def replay_blocked_comparison_execution_boundary(
    artifact: BlockedComparisonExecutionBoundaryArtifact,
    *,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
) -> BlockedComparisonExecutionBoundaryArtifact:
    if type(artifact) is not BlockedComparisonExecutionBoundaryArtifact:
        raise ComparisonExecutionBoundaryValidationError(
            "artifact must be an exact blocked execution artifact"
        )
    if type(artifact.raw_bytes) is not bytes:
        raise ComparisonExecutionBoundaryValidationError("raw bytes changed type")
    if type(artifact.sha256) is not str or artifact.sha256 != sha256_bytes(
        artifact.raw_bytes
    ):
        raise ComparisonExecutionBoundaryValidationError("sha256 changed")
    if type(artifact.byte_length) is not int or artifact.byte_length != len(
        artifact.raw_bytes
    ):
        raise ComparisonExecutionBoundaryValidationError("byte_length changed")
    for name in (
        "protocol_ref",
        "roster_ref",
        "open_identity_ref",
        "closed_identity_ref",
        "open_configuration_ref",
        "closed_configuration_ref",
    ):
        _require_ref(getattr(artifact, name), f"artifact.{name}")
    if (
        type(artifact.missing_fields) is not tuple
        or artifact.missing_fields != REQUIRED_MISSING_FIELDS
        or any(type(item) is not str for item in artifact.missing_fields)
        or type(artifact.artifact_refs) is not tuple
    ):
        raise ComparisonExecutionBoundaryValidationError(
            "blocked projection tuple fields changed"
        )
    for index, reference in enumerate(artifact.artifact_refs):
        _require_ref(reference, f"artifact.artifact_refs[{index}]")
    _require_frozen(artifact.payload, "artifact.payload")
    if canonical_json_bytes(thaw_json(artifact.payload)) != artifact.raw_bytes:
        raise ComparisonExecutionBoundaryValidationError("payload differs from raw bytes")
    replayed = load_blocked_comparison_execution_boundary(
        artifact.raw_bytes,
        boundary_ref=artifact.artifact_ref,
        protocol=protocol,
        roster=roster,
    )
    if (
        type(artifact.boundary_id) is not str
        or type(artifact.program_id) is not str
        or type(artifact.evaluation_count) is not int
        or replayed != artifact
    ):
        raise ComparisonExecutionBoundaryValidationError(
            "blocked execution artifact differs from fresh replay"
        )
    return replayed


def _spend_value(
    *, spend_record_id: str, boundary_ref: ArtifactRef
) -> dict[str, Any]:
    return {
        "schema": COMPARISON_ZERO_SPEND_RECORD_SCHEMA,
        "spend_record_id": spend_record_id,
        "execution_boundary_ref": _ref_value(boundary_ref),
        "activity": dict(_ZERO_ACTIVITY),
        "provider_receipt_ref": None,
        "status": {
            "execution": NOT_EXECUTED,
            "spend": ZERO_SPEND,
            "scope": STRUCTURE_ONLY,
            "authority": NON_AUTHORITY,
        },
    }


def build_zero_comparison_spend_record(
    *,
    spend_record_id: str,
    boundary: BlockedComparisonExecutionBoundaryArtifact,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
) -> ZeroComparisonSpendRecordArtifact:
    boundary = replay_blocked_comparison_execution_boundary(
        boundary, protocol=protocol, roster=roster
    )
    spend_record_id = expect_machine_id(spend_record_id, "spend_record_id")
    raw = canonical_json_bytes(
        _spend_value(
            spend_record_id=spend_record_id,
            boundary_ref=boundary.artifact_ref,
        )
    )
    return load_zero_comparison_spend_record(
        raw,
        spend_ref=ArtifactRef(
            artifact_id=spend_record_id,
            sha256=sha256_bytes(raw),
            byte_length=len(raw),
            media_type=COMPARISON_ZERO_SPEND_RECORD_MEDIA_TYPE,
        ),
        boundary=boundary,
        protocol=protocol,
        roster=roster,
    )


def load_zero_comparison_spend_record(
    raw: bytes | bytearray | memoryview,
    *,
    spend_ref: ArtifactRef,
    boundary: BlockedComparisonExecutionBoundaryArtifact,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
) -> ZeroComparisonSpendRecordArtifact:
    boundary = replay_blocked_comparison_execution_boundary(
        boundary, protocol=protocol, roster=roster
    )
    spend_ref = _require_ref(spend_ref, "spend_ref")
    if spend_ref.media_type != COMPARISON_ZERO_SPEND_RECORD_MEDIA_TYPE:
        raise ComparisonExecutionBoundaryValidationError("spend media type changed")
    snapshot, value = _canonical(raw, "zero spend record")
    if not spend_ref.verify_bytes(snapshot):
        raise ComparisonExecutionBoundaryValidationError(
            "zero spend bytes differ from spend_ref"
        )
    expect_keys(
        value,
        required={
            "schema",
            "spend_record_id",
            "execution_boundary_ref",
            "activity",
            "provider_receipt_ref",
            "status",
        },
        path="$",
    )
    spend_record_id = expect_machine_id(value["spend_record_id"], "$.spend_record_id")
    expected_status = {
        "execution": NOT_EXECUTED,
        "spend": ZERO_SPEND,
        "scope": STRUCTURE_ONLY,
        "authority": NON_AUTHORITY,
    }
    activity = expect_object(value["activity"], "$.activity")
    status = expect_object(value["status"], "$.status")
    if (
        value["schema"] != COMPARISON_ZERO_SPEND_RECORD_SCHEMA
        or spend_record_id != spend_ref.artifact_id
        or parse_artifact_ref(
            value["execution_boundary_ref"], "$.execution_boundary_ref"
        )
        != boundary.artifact_ref
        or activity != _ZERO_ACTIVITY
        or any(type(item) is not int for item in activity.values())
        or value["provider_receipt_ref"] is not None
        or status != expected_status
        or any(type(item) is not str for item in status.values())
    ):
        raise ComparisonExecutionBoundaryValidationError(
            "zero-spend record made a nonzero or executed claim"
        )
    refs = _require_distinct_refs(
        (boundary.artifact_ref,),
        owner_id=spend_record_id,
        path="artifact_refs",
    )
    return ZeroComparisonSpendRecordArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        spend_record_id=spend_record_id,
        boundary_ref=boundary.artifact_ref,
        payload=freeze_json(value),
        artifact_refs=refs,
    )


def replay_zero_comparison_spend_record(
    artifact: ZeroComparisonSpendRecordArtifact,
    *,
    boundary: BlockedComparisonExecutionBoundaryArtifact,
    protocol: SharedComparisonProtocolArtifact,
    roster: FrozenComparisonRosterArtifact,
) -> ZeroComparisonSpendRecordArtifact:
    if type(artifact) is not ZeroComparisonSpendRecordArtifact:
        raise ComparisonExecutionBoundaryValidationError(
            "artifact must be an exact zero-spend artifact"
        )
    if type(artifact.raw_bytes) is not bytes:
        raise ComparisonExecutionBoundaryValidationError("raw bytes changed type")
    if type(artifact.sha256) is not str or artifact.sha256 != sha256_bytes(
        artifact.raw_bytes
    ):
        raise ComparisonExecutionBoundaryValidationError("sha256 changed")
    if type(artifact.byte_length) is not int or artifact.byte_length != len(
        artifact.raw_bytes
    ):
        raise ComparisonExecutionBoundaryValidationError("byte_length changed")
    _require_ref(artifact.boundary_ref, "artifact.boundary_ref")
    if type(artifact.artifact_refs) is not tuple:
        raise ComparisonExecutionBoundaryValidationError("artifact_refs changed type")
    for index, reference in enumerate(artifact.artifact_refs):
        _require_ref(reference, f"artifact.artifact_refs[{index}]")
    _require_frozen(artifact.payload, "artifact.payload")
    if canonical_json_bytes(thaw_json(artifact.payload)) != artifact.raw_bytes:
        raise ComparisonExecutionBoundaryValidationError("payload differs from raw bytes")
    replayed = load_zero_comparison_spend_record(
        artifact.raw_bytes,
        spend_ref=artifact.artifact_ref,
        boundary=boundary,
        protocol=protocol,
        roster=roster,
    )
    if (
        type(artifact.spend_record_id) is not str
        or replayed != artifact
    ):
        raise ComparisonExecutionBoundaryValidationError(
            "zero-spend artifact differs from fresh replay"
        )
    return replayed


__all__ = (
    "COMPARISON_EXECUTION_BOUNDARY_SCHEMA",
    "COMPARISON_ZERO_SPEND_RECORD_SCHEMA",
    "COMPARISON_EXECUTION_BOUNDARY_MEDIA_TYPE",
    "COMPARISON_ZERO_SPEND_RECORD_MEDIA_TYPE",
    "BLOCKED_MISSING_EXACT_EXTERNAL_AUTHORIZATION",
    "NOT_EXECUTED",
    "ZERO_SPEND",
    "REQUIRED_MISSING_FIELDS",
    "ComparisonExecutionBoundaryValidationError",
    "BlockedComparisonExecutionBoundaryArtifact",
    "ZeroComparisonSpendRecordArtifact",
    "build_blocked_comparison_execution_boundary",
    "load_blocked_comparison_execution_boundary",
    "replay_blocked_comparison_execution_boundary",
    "build_zero_comparison_spend_record",
    "load_zero_comparison_spend_record",
    "replay_zero_comparison_spend_record",
)
