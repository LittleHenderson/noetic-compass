"""Replay-only distributed probe ownership and reconstruction contract.

The contract binds exact model, configuration, universal probe, topology,
rank, shard, fragment, checkpoint, and reconstruction identities.  It has no
distributed framework, model loader, GPU, filesystem, provider, network, or
spend path.  All capability remains unmeasured and not licensed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
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
    expect_string,
    parse_artifact_ref,
)
from .comparison_model_protocol import (
    COMPARISON_MODEL_CAPABILITIES_MEDIA_TYPE,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    COMPARISON_MODEL_IDENTITY_MEDIA_TYPE,
    NON_AUTHORITY,
    STRUCTURE_ONLY,
    ComparisonModelCapabilitiesArtifact,
    ComparisonModelIdentityArtifact,
    replay_comparison_model_capabilities,
    replay_comparison_model_identity,
)
from .universal_probe_contract import (
    ARCHITECTURE_DISCOVERY_RECEIPT_MEDIA_TYPE,
    GENERATED_PROBE_ADAPTER_MANIFEST_MEDIA_TYPE,
    UNIVERSAL_PROBE_CANARY_PLAN_MEDIA_TYPE,
    ArchitectureDiscoveryReceiptArtifact,
    GeneratedProbeAdapterManifestArtifact,
    UniversalProbeCanaryPlanArtifact,
    replay_architecture_discovery_receipt,
    replay_generated_probe_adapter_manifest,
    replay_universal_probe_canary_plan,
)


DISTRIBUTED_RUNTIME_IDENTITY_SCHEMA = (
    "cas_harness_v2.distributed_runtime_identity.v1"
)
NO_FULL_COPY_PROOF_SCHEMA = "cas_harness_v2.no_full_copy_proof.v1"
DISTRIBUTED_PROBE_PLAN_SCHEMA = "cas_harness_v2.distributed_probe_plan.v1"
DISTRIBUTED_PROBE_FRAGMENT_SCHEMA = "cas_harness_v2.distributed_probe_fragment.v1"
INDEPENDENT_RECONSTRUCTION_EVIDENCE_SCHEMA = (
    "cas_harness_v2.independent_reconstruction_evidence.v1"
)
INDEPENDENT_RECONSTRUCTION_RECEIPT_SCHEMA = (
    "cas_harness_v2.independent_reconstruction_receipt.v1"
)

DISTRIBUTED_RUNTIME_IDENTITY_MEDIA_TYPE = (
    "application/vnd.cas-harness.distributed-runtime-identity-v1+json"
)
NO_FULL_COPY_PROOF_MEDIA_TYPE = (
    "application/vnd.cas-harness.no-full-copy-proof-v1+json"
)
DISTRIBUTED_MODEL_SHARD_MEDIA_TYPE = (
    "application/vnd.cas-harness.distributed-model-shard-v1+octets"
)
DISTRIBUTED_PROBE_PLAN_MEDIA_TYPE = (
    "application/vnd.cas-harness.distributed-probe-plan-v1+json"
)
DISTRIBUTED_FRAGMENT_CONTENT_MEDIA_TYPE = (
    "application/vnd.cas-harness.distributed-fragment-content-v1+octets"
)
DISTRIBUTED_PROBE_FRAGMENT_MEDIA_TYPE = (
    "application/vnd.cas-harness.distributed-probe-fragment-v1+json"
)
INDEPENDENT_RECONSTRUCTION_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.independent-reconstruction-evidence-v1+json"
)
INDEPENDENT_RECONSTRUCTION_RECEIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.independent-reconstruction-receipt-v1+json"
)
DISTRIBUTED_RECONSTRUCTED_OUTPUT_MEDIA_TYPE = (
    "application/vnd.cas-harness.distributed-reconstructed-output-v1+octets"
)

TENSOR_PARALLEL = "TENSOR_PARALLEL"
PIPELINE_PARALLEL = "PIPELINE_PARALLEL"
EXPERT_PARALLEL = "EXPERT_PARALLEL"
TOPOLOGY_TYPES = (TENSOR_PARALLEL, PIPELINE_PARALLEL, EXPERT_PARALLEL)

COORDINATOR = "COORDINATOR"
WORKER = "WORKER"
INDEPENDENT_RECONSTRUCTOR = "INDEPENDENT_RECONSTRUCTOR"
RUNTIME_ROLES = (COORDINATOR, WORKER, INDEPENDENT_RECONSTRUCTOR)

COMPLETED = "COMPLETED"
RANK_FAILED = "RANK_FAILED"
RANK_OOM = "RANK_OOM"
RANK_OUTCOME_STATUSES = (COMPLETED, RANK_FAILED, RANK_OOM)

UNMEASURED = "UNMEASURED"
NOT_LICENSED = "NOT_LICENSED"
NOT_EXECUTED = "NOT_EXECUTED"
REPLAY_ONLY = "REPLAY_ONLY"
UNAVAILABLE = "UNAVAILABLE"
FRAGMENT_OBJECT_VERSION = "distributed-fragment-v1"

_STATUS = {
    "scope": STRUCTURE_ONLY,
    "authority": NON_AUTHORITY,
    "license": NOT_LICENSED,
    "capability": UNMEASURED,
}
_BOUNDARY = {
    "execution": NOT_EXECUTED,
    "distributed_framework_calls": 0,
    "model_calls": 0,
    "provider_calls": 0,
    "network_calls": 0,
    "filesystem_calls": 0,
    "gpu_calls": 0,
    "spend_microusd": 0,
    "executed_attempts": 0,
    "execution_authority": "NOT_GRANTED",
}
_VERSION_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*-v[1-9][0-9]*(?:\.[0-9]+){0,2}$"
)


class DistributedProbeContractValidationError(SchemaValidationError):
    """An exact distributed probe contract value failed closed."""


class DistributedProbeBackendUnavailableError(RuntimeError):
    """The distributed probe backend is deliberately unavailable."""


@dataclass(frozen=True, slots=True)
class ParameterRange:
    start: int
    stop: int

    def __post_init__(self) -> None:
        start = expect_int(self.start, "ParameterRange.start", minimum=0)
        stop = expect_int(self.stop, "ParameterRange.stop", minimum=1)
        if stop <= start:
            raise DistributedProbeContractValidationError(
                "ParameterRange.stop must be greater than start"
            )

    @property
    def width(self) -> int:
        return self.stop - self.start


@dataclass(frozen=True, slots=True)
class DistributedRankSpec:
    rank: int
    parameter_ranges: tuple[ParameterRange, ...]
    owned_site_ids: tuple[str, ...]
    model_shard_ref: ArtifactRef
    model_shard_bytes: bytes
    no_full_copy_proof_ref: ArtifactRef
    no_full_copy_proof_bytes: bytes
    worker_runtime_ref: ArtifactRef
    worker_runtime_bytes: bytes

    def __post_init__(self) -> None:
        expect_int(self.rank, "DistributedRankSpec.rank", minimum=0)
        if type(self.parameter_ranges) is not tuple or not self.parameter_ranges:
            raise DistributedProbeContractValidationError(
                "DistributedRankSpec.parameter_ranges must be a non-empty exact tuple"
            )
        for index, item in enumerate(self.parameter_ranges):
            if type(item) is not ParameterRange:
                raise DistributedProbeContractValidationError(
                    f"DistributedRankSpec.parameter_ranges[{index}] must be exact"
                )
        if type(self.owned_site_ids) is not tuple or not self.owned_site_ids:
            raise DistributedProbeContractValidationError(
                "DistributedRankSpec.owned_site_ids must be a non-empty exact tuple"
            )
        for index, site_id in enumerate(self.owned_site_ids):
            expect_machine_id(site_id, f"DistributedRankSpec.owned_site_ids[{index}]")
        for path, reference, expected_media in (
            (
                "DistributedRankSpec.model_shard_ref",
                self.model_shard_ref,
                DISTRIBUTED_MODEL_SHARD_MEDIA_TYPE,
            ),
            (
                "DistributedRankSpec.no_full_copy_proof_ref",
                self.no_full_copy_proof_ref,
                NO_FULL_COPY_PROOF_MEDIA_TYPE,
            ),
            (
                "DistributedRankSpec.worker_runtime_ref",
                self.worker_runtime_ref,
                DISTRIBUTED_RUNTIME_IDENTITY_MEDIA_TYPE,
            ),
        ):
            _require_ref(reference, path)
            _require_media(reference, expected_media, path)
        for path, raw, reference in (
            (
                "DistributedRankSpec.model_shard_bytes",
                self.model_shard_bytes,
                self.model_shard_ref,
            ),
            (
                "DistributedRankSpec.no_full_copy_proof_bytes",
                self.no_full_copy_proof_bytes,
                self.no_full_copy_proof_ref,
            ),
            (
                "DistributedRankSpec.worker_runtime_bytes",
                self.worker_runtime_bytes,
                self.worker_runtime_ref,
            ),
        ):
            if type(raw) is not bytes or not reference.verify_bytes(raw):
                raise DistributedProbeContractValidationError(
                    f"{path} differs from its exact artifact reference"
                )


@dataclass(frozen=True, slots=True)
class FragmentSlot:
    merge_ordinal: int
    checkpoint_ordinal: int
    rank: int
    site_id: str
    case_id: str

    def __post_init__(self) -> None:
        merge = expect_int(self.merge_ordinal, "FragmentSlot.merge_ordinal", minimum=1)
        checkpoint = expect_int(
            self.checkpoint_ordinal, "FragmentSlot.checkpoint_ordinal", minimum=1
        )
        if checkpoint != merge:
            raise DistributedProbeContractValidationError(
                "checkpoint ordinal must equal the immutable merge ordinal"
            )
        expect_int(self.rank, "FragmentSlot.rank", minimum=0)
        expect_machine_id(self.site_id, "FragmentSlot.site_id")
        expect_machine_id(self.case_id, "FragmentSlot.case_id")


@dataclass(frozen=True, slots=True)
class DistributedRankOutcome:
    rank: int
    status: str
    attempt_number: int
    resumed: bool
    replaced: bool
    final_checkpoint_ordinal: int

    def __post_init__(self) -> None:
        expect_int(self.rank, "DistributedRankOutcome.rank", minimum=0)
        expect_enum(
            self.status, set(RANK_OUTCOME_STATUSES), "DistributedRankOutcome.status"
        )
        expect_int(
            self.attempt_number,
            "DistributedRankOutcome.attempt_number",
            minimum=1,
            maximum=1,
        )
        if type(self.resumed) is not bool or type(self.replaced) is not bool:
            raise DistributedProbeContractValidationError(
                "rank resume/replacement flags must be exact booleans"
            )
        expect_int(
            self.final_checkpoint_ordinal,
            "DistributedRankOutcome.final_checkpoint_ordinal",
            minimum=1,
        )


@dataclass(frozen=True, slots=True)
class DistributedProbePlanArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    plan_id: str
    identity_ref: ArtifactRef
    capabilities_ref: ArtifactRef
    configuration_ref: ArtifactRef
    configuration_bytes: bytes
    discovery_ref: ArtifactRef
    manifest_ref: ArtifactRef
    canary_plan_ref: ArtifactRef
    topology_id: str
    topology_type: str
    total_parameter_units: int
    world_size: int
    coordinator_runtime_ref: ArtifactRef
    coordinator_runtime_bytes: bytes
    ranks: tuple[DistributedRankSpec, ...]
    case_ids: tuple[str, ...]
    fragment_slots: tuple[FragmentSlot, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.plan_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DISTRIBUTED_PROBE_PLAN_MEDIA_TYPE,
        )

    def slot(self, merge_ordinal: int) -> FragmentSlot:
        merge_ordinal = expect_int(merge_ordinal, "merge_ordinal", minimum=1)
        if merge_ordinal > len(self.fragment_slots):
            raise DistributedProbeContractValidationError(
                "merge ordinal is outside the frozen fragment schedule"
            )
        return self.fragment_slots[merge_ordinal - 1]


@dataclass(frozen=True, slots=True)
class DistributedProbeFragmentArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    fragment_id: str
    object_version: str
    plan_ref: ArtifactRef
    merge_ordinal: int
    checkpoint_ordinal: int
    rank: int
    site_id: str
    case_id: str
    attempt_number: int
    content_ref: ArtifactRef
    content_bytes: bytes
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.fragment_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=DISTRIBUTED_PROBE_FRAGMENT_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class IndependentReconstructionReceiptArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    receipt_id: str
    plan_ref: ArtifactRef
    fragment_refs: tuple[ArtifactRef, ...]
    rank_outcomes: tuple[DistributedRankOutcome, ...]
    reconstructed_output_ref: ArtifactRef
    reconstructed_output_bytes: bytes
    independent_runtime_ref: ArtifactRef
    independent_runtime_bytes: bytes
    independent_evidence_ref: ArtifactRef
    independent_evidence_bytes: bytes
    capability_state: str
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.receipt_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=INDEPENDENT_RECONSTRUCTION_RECEIPT_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class DistributedProbeReplayRequest:
    plan_ref: ArtifactRef
    reconstruction_receipt_ref: ArtifactRef

    def __post_init__(self) -> None:
        _require_ref(self.plan_ref, "DistributedProbeReplayRequest.plan_ref")
        _require_media(
            self.plan_ref,
            DISTRIBUTED_PROBE_PLAN_MEDIA_TYPE,
            "DistributedProbeReplayRequest.plan_ref",
        )
        _require_ref(
            self.reconstruction_receipt_ref,
            "DistributedProbeReplayRequest.reconstruction_receipt_ref",
        )
        _require_media(
            self.reconstruction_receipt_ref,
            INDEPENDENT_RECONSTRUCTION_RECEIPT_MEDIA_TYPE,
            "DistributedProbeReplayRequest.reconstruction_receipt_ref",
        )
        _unique_ref_closure(
            (self.plan_ref, self.reconstruction_receipt_ref),
            "DistributedProbeReplayRequest",
        )


def _require_ref(value: Any, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise DistributedProbeContractValidationError(
            f"{path} must be an exact ArtifactRef"
        )
    return value


def _require_media(reference: ArtifactRef, expected: str, path: str) -> None:
    if reference.media_type != expected:
        raise DistributedProbeContractValidationError(
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


def _canonical_object(raw: Any, path: str) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise DistributedProbeContractValidationError(
                f"{path} must use exact canonical JSON bytes"
            )
        return snapshot, value
    except DistributedProbeContractValidationError:
        raise
    except (TypeError, ValueError) as exc:
        raise DistributedProbeContractValidationError(f"{path}: {exc}") from exc


def _require_status_boundary(value: dict[str, Any]) -> None:
    status = expect_object(value["status"], "$.status")
    expect_keys(status, required=_STATUS, path="$.status")
    if status != _STATUS:
        raise DistributedProbeContractValidationError(
            "distributed artifacts remain STRUCTURE_ONLY/NON_AUTHORITY/NOT_LICENSED/UNMEASURED"
        )
    boundary = expect_object(value["boundary"], "$.boundary")
    expect_keys(boundary, required=_BOUNDARY, path="$.boundary")
    if boundary != _BOUNDARY:
        raise DistributedProbeContractValidationError(
            "distributed artifacts must retain the exact zero-call boundary"
        )


def _model_binding(identity: ComparisonModelIdentityArtifact) -> dict[str, Any]:
    return {
        "identity_ref": _ref_value(identity.artifact_ref),
        "access_kind": identity.access_kind,
        "provider": identity.provider,
        "model_id": identity.model_id,
        "revision": identity.revision,
    }


def _require_model_binding(
    value: Any, identity: ComparisonModelIdentityArtifact, path: str
) -> None:
    binding = expect_object(value, path)
    expect_keys(
        binding,
        required={"identity_ref", "access_kind", "provider", "model_id", "revision"},
        path=path,
    )
    if binding != _model_binding(identity):
        raise DistributedProbeContractValidationError(
            f"{path} differs from the exact model/revision/access binding"
        )


def _immutable_version(value: Any, path: str) -> str:
    result = expect_string(value, path, maximum=128)
    if not _VERSION_RE.fullmatch(result):
        raise DistributedProbeContractValidationError(
            f"{path} must be an immutable numbered version"
        )
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
            if prior != reference:
                raise DistributedProbeContractValidationError(
                    f"{path} aliases one artifact ID to different content"
                )
            continue
        content_key = (reference.sha256, reference.byte_length)
        prior_content = by_content.get(content_key)
        if prior_content is not None:
            raise DistributedProbeContractValidationError(
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
    if owner_id in {reference.artifact_id for reference in closure}:
        raise DistributedProbeContractValidationError(
            f"{path} collides with its owner artifact ID"
        )
    return closure


def _artifact_storage(value: Any, expected: type[Any], path: str) -> None:
    if type(value) is not expected:
        raise DistributedProbeContractValidationError(
            f"{path} must be an exact {expected.__name__}"
        )
    missing = object()
    if (
        type(getattr(value, "raw_bytes", missing)) is not bytes
        or type(getattr(value, "sha256", missing)) is not str
        or type(getattr(value, "byte_length", missing)) is not int
        or type(getattr(value, "payload", missing)) is not MappingProxyType
        or type(getattr(value, "artifact_refs", missing)) is not tuple
    ):
        raise DistributedProbeContractValidationError(
            f"{path} storage projections must remain exact immutable values"
        )


def _validate_universal_dependencies(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
) -> tuple[
    ComparisonModelIdentityArtifact,
    ComparisonModelCapabilitiesArtifact,
    ArchitectureDiscoveryReceiptArtifact,
    GeneratedProbeAdapterManifestArtifact,
    UniversalProbeCanaryPlanArtifact,
]:
    identity = replay_comparison_model_identity(identity)
    capabilities = replay_comparison_model_capabilities(
        capabilities, identity=identity
    )
    if (
        capabilities.identity_ref != identity.artifact_ref
        or capabilities.provider != identity.provider
        or capabilities.model_id != identity.model_id
        or capabilities.revision != identity.revision
        or capabilities.access_kind != identity.access_kind
    ):
        raise DistributedProbeContractValidationError(
            "distributed plan model capabilities differ from exact model identity"
        )
    discovery = replay_architecture_discovery_receipt(
        discovery, identity=identity, capabilities=capabilities
    )
    manifest = replay_generated_probe_adapter_manifest(
        manifest,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
    )
    canary_plan = replay_universal_probe_canary_plan(
        canary_plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
    )
    if (
        discovery.identity_ref != identity.artifact_ref
        or discovery.capabilities_ref != capabilities.artifact_ref
        or discovery.configuration_ref != capabilities.configuration_ref
        or manifest.identity_ref != identity.artifact_ref
        or manifest.capabilities_ref != capabilities.artifact_ref
        or manifest.configuration_ref != capabilities.configuration_ref
        or manifest.discovery_ref != discovery.artifact_ref
        or canary_plan.identity_ref != identity.artifact_ref
        or canary_plan.capabilities_ref != capabilities.artifact_ref
        or canary_plan.configuration_ref != capabilities.configuration_ref
        or canary_plan.discovery_ref != discovery.artifact_ref
        or canary_plan.manifest_ref != manifest.artifact_ref
    ):
        raise DistributedProbeContractValidationError(
            "distributed plan differs from exact universal probe dependencies"
        )
    return identity, capabilities, discovery, manifest, canary_plan


def _range_value(value: ParameterRange) -> dict[str, int]:
    if type(value) is not ParameterRange:
        raise DistributedProbeContractValidationError(
            "parameter range must be an exact ParameterRange"
        )
    return {"start": value.start, "stop": value.stop}


def _parse_range(value: Any, path: str) -> ParameterRange:
    row = expect_object(value, path)
    expect_keys(row, required={"start", "stop"}, path=path)
    return ParameterRange(
        start=expect_int(row["start"], f"{path}.start"),
        stop=expect_int(row["stop"], f"{path}.stop", minimum=1),
    )


def _validate_ranges(
    ranges: tuple[ParameterRange, ...], path: str
) -> tuple[ParameterRange, ...]:
    if type(ranges) is not tuple or not ranges:
        raise DistributedProbeContractValidationError(
            f"{path} must be a non-empty exact tuple"
        )
    result: list[ParameterRange] = []
    last_stop: int | None = None
    for index, value in enumerate(ranges):
        if type(value) is not ParameterRange:
            raise DistributedProbeContractValidationError(
                f"{path}[{index}] must be an exact ParameterRange"
            )
        if last_stop is not None and value.start < last_stop:
            raise DistributedProbeContractValidationError(
                f"{path} contains overlapping or out-of-order ranges"
            )
        last_stop = value.stop
        result.append(value)
    return tuple(result)


def build_distributed_runtime_identity_body(
    *,
    runtime_id: str,
    role: str,
    rank: int | None,
    implementation: str,
    version: str,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    topology_id: str,
    topology_type: str,
    world_size: int,
) -> bytes:
    """Build a typed coordinator, worker, or independent runtime identity."""

    identity = replay_comparison_model_identity(identity)
    role = expect_enum(role, set(RUNTIME_ROLES), "role")
    world_size = expect_int(world_size, "world_size", minimum=2, maximum=4096)
    if role == WORKER:
        rank = expect_int(rank, "rank", minimum=0, maximum=world_size - 1)
    elif rank is not None:
        raise DistributedProbeContractValidationError(
            "coordinator and independent reconstructor runtime identities have no rank"
        )
    configuration_ref = _require_ref(configuration_ref, "configuration_ref")
    _require_media(
        configuration_ref,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        "configuration_ref",
    )
    topology_type = expect_enum(
        topology_type, set(TOPOLOGY_TYPES), "topology_type"
    )
    return canonical_json_bytes(
        {
            "schema": DISTRIBUTED_RUNTIME_IDENTITY_SCHEMA,
            "runtime_id": expect_machine_id(runtime_id, "runtime_id"),
            "role": role,
            "rank": rank,
            "implementation": expect_machine_id(implementation, "implementation"),
            "version": _immutable_version(version, "version"),
            "model_identity": _model_binding(identity),
            "configuration_ref": _ref_value(configuration_ref),
            "topology_id": expect_machine_id(topology_id, "topology_id"),
            "topology_type": topology_type,
            "world_size": world_size,
            "runtime_scope": "IDENTITY_ONLY_NO_EXECUTION",
            "status": dict(_STATUS),
            "boundary": dict(_BOUNDARY),
        }
    )


def _validate_runtime_identity_body(
    raw: Any,
    reference: ArtifactRef,
    *,
    role: str,
    rank: int | None,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    topology_id: str,
    topology_type: str,
    world_size: int,
    path: str,
) -> bytes:
    reference = _require_ref(reference, f"{path}.reference")
    _require_media(
        reference, DISTRIBUTED_RUNTIME_IDENTITY_MEDIA_TYPE, f"{path}.reference"
    )
    if type(raw) is not bytes or not reference.verify_bytes(raw):
        raise DistributedProbeContractValidationError(
            f"{path} bytes differ from the exact runtime identity reference"
        )
    snapshot, value = _canonical_object(raw, path)
    expect_keys(
        value,
        required={
            "schema", "runtime_id", "role", "rank", "implementation", "version",
            "model_identity", "configuration_ref", "topology_id", "topology_type",
            "world_size", "runtime_scope", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != DISTRIBUTED_RUNTIME_IDENTITY_SCHEMA:
        raise DistributedProbeContractValidationError(f"{path} schema drifted")
    if expect_machine_id(value["runtime_id"], "$.runtime_id") != reference.artifact_id:
        raise DistributedProbeContractValidationError(
            f"{path} runtime ID differs from its artifact reference"
        )
    if expect_enum(value["role"], set(RUNTIME_ROLES), "$.role") != role:
        raise DistributedProbeContractValidationError(f"{path} role drifted")
    parsed_rank = value["rank"]
    if parsed_rank is not None:
        parsed_rank = expect_int(parsed_rank, "$.rank")
    if parsed_rank != rank:
        raise DistributedProbeContractValidationError(f"{path} rank drifted")
    expect_machine_id(value["implementation"], "$.implementation")
    _immutable_version(value["version"], "$.version")
    _require_model_binding(value["model_identity"], identity, "$.model_identity")
    if parse_artifact_ref(value["configuration_ref"], "$.configuration_ref") != configuration_ref:
        raise DistributedProbeContractValidationError(
            f"{path} configuration binding drifted"
        )
    if expect_machine_id(value["topology_id"], "$.topology_id") != topology_id:
        raise DistributedProbeContractValidationError(f"{path} topology ID drifted")
    if expect_enum(value["topology_type"], set(TOPOLOGY_TYPES), "$.topology_type") != topology_type:
        raise DistributedProbeContractValidationError(f"{path} topology type drifted")
    if expect_int(value["world_size"], "$.world_size", minimum=2) != world_size:
        raise DistributedProbeContractValidationError(f"{path} world size drifted")
    if value["runtime_scope"] != "IDENTITY_ONLY_NO_EXECUTION":
        raise DistributedProbeContractValidationError(
            f"{path} cannot claim runtime execution"
        )
    _require_status_boundary(value)
    return snapshot


def build_no_full_copy_proof_body(
    *,
    proof_id: str,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    topology_id: str,
    topology_type: str,
    world_size: int,
    rank: int,
    total_parameter_units: int,
    parameter_ranges: tuple[ParameterRange, ...],
    model_shard_ref: ArtifactRef,
) -> bytes:
    """Build structural evidence that one rank owns less than the full model."""

    identity = replay_comparison_model_identity(identity)
    configuration_ref = _require_ref(configuration_ref, "configuration_ref")
    _require_media(
        configuration_ref,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        "configuration_ref",
    )
    topology_type = expect_enum(
        topology_type, set(TOPOLOGY_TYPES), "topology_type"
    )
    world_size = expect_int(world_size, "world_size", minimum=2, maximum=4096)
    rank = expect_int(rank, "rank", minimum=0, maximum=world_size - 1)
    total = expect_int(
        total_parameter_units, "total_parameter_units", minimum=2
    )
    ranges = _validate_ranges(parameter_ranges, "parameter_ranges")
    if any(item.stop > total for item in ranges):
        raise DistributedProbeContractValidationError(
            "parameter range exceeds total model parameter units"
        )
    owned = sum(item.width for item in ranges)
    if owned >= total:
        raise DistributedProbeContractValidationError(
            "a distributed rank cannot own a full model copy"
        )
    model_shard_ref = _require_ref(model_shard_ref, "model_shard_ref")
    _require_media(
        model_shard_ref, DISTRIBUTED_MODEL_SHARD_MEDIA_TYPE, "model_shard_ref"
    )
    return canonical_json_bytes(
        {
            "schema": NO_FULL_COPY_PROOF_SCHEMA,
            "proof_id": expect_machine_id(proof_id, "proof_id"),
            "model_identity": _model_binding(identity),
            "configuration_ref": _ref_value(configuration_ref),
            "topology_id": expect_machine_id(topology_id, "topology_id"),
            "topology_type": topology_type,
            "world_size": world_size,
            "rank": rank,
            "total_parameter_units": total,
            "parameter_ranges": [_range_value(item) for item in ranges],
            "owned_parameter_units": owned,
            "model_shard_ref": _ref_value(model_shard_ref),
            "full_model_copy": False,
            "proof_scope": "STRUCTURAL_DECLARATION_ONLY",
            "status": dict(_STATUS),
            "boundary": dict(_BOUNDARY),
        }
    )


def _validate_no_full_copy_proof(
    raw: Any,
    reference: ArtifactRef,
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    topology_id: str,
    topology_type: str,
    world_size: int,
    rank: int,
    total_parameter_units: int,
    parameter_ranges: tuple[ParameterRange, ...],
    model_shard_ref: ArtifactRef,
    path: str,
) -> bytes:
    reference = _require_ref(reference, f"{path}.reference")
    _require_media(reference, NO_FULL_COPY_PROOF_MEDIA_TYPE, f"{path}.reference")
    if type(raw) is not bytes or not reference.verify_bytes(raw):
        raise DistributedProbeContractValidationError(
            f"{path} bytes differ from the exact proof reference"
        )
    snapshot, value = _canonical_object(raw, path)
    expect_keys(
        value,
        required={
            "schema", "proof_id", "model_identity", "configuration_ref",
            "topology_id", "topology_type", "world_size", "rank",
            "total_parameter_units", "parameter_ranges", "owned_parameter_units",
            "model_shard_ref", "full_model_copy", "proof_scope", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != NO_FULL_COPY_PROOF_SCHEMA:
        raise DistributedProbeContractValidationError(f"{path} schema drifted")
    if expect_machine_id(value["proof_id"], "$.proof_id") != reference.artifact_id:
        raise DistributedProbeContractValidationError(
            f"{path} proof ID differs from its reference"
        )
    _require_model_binding(value["model_identity"], identity, "$.model_identity")
    if parse_artifact_ref(value["configuration_ref"], "$.configuration_ref") != configuration_ref:
        raise DistributedProbeContractValidationError(f"{path} configuration drifted")
    if expect_machine_id(value["topology_id"], "$.topology_id") != topology_id:
        raise DistributedProbeContractValidationError(f"{path} topology ID drifted")
    if expect_enum(value["topology_type"], set(TOPOLOGY_TYPES), "$.topology_type") != topology_type:
        raise DistributedProbeContractValidationError(f"{path} topology type drifted")
    if expect_int(value["world_size"], "$.world_size", minimum=2) != world_size:
        raise DistributedProbeContractValidationError(f"{path} world size drifted")
    if expect_int(value["rank"], "$.rank") != rank:
        raise DistributedProbeContractValidationError(f"{path} rank drifted")
    if expect_int(value["total_parameter_units"], "$.total_parameter_units", minimum=2) != total_parameter_units:
        raise DistributedProbeContractValidationError(f"{path} total units drifted")
    raw_ranges = expect_list(value["parameter_ranges"], "$.parameter_ranges")
    parsed_ranges = _validate_ranges(
        tuple(_parse_range(item, f"$.parameter_ranges[{index}]") for index, item in enumerate(raw_ranges)),
        "$.parameter_ranges",
    )
    if parsed_ranges != parameter_ranges:
        raise DistributedProbeContractValidationError(f"{path} ownership ranges drifted")
    owned = sum(item.width for item in parsed_ranges)
    if expect_int(value["owned_parameter_units"], "$.owned_parameter_units", minimum=1) != owned:
        raise DistributedProbeContractValidationError(f"{path} owned-unit count drifted")
    if owned >= total_parameter_units:
        raise DistributedProbeContractValidationError(
            "a distributed rank cannot own a full model copy"
        )
    if parse_artifact_ref(value["model_shard_ref"], "$.model_shard_ref") != model_shard_ref:
        raise DistributedProbeContractValidationError(f"{path} model shard drifted")
    if expect_bool(value["full_model_copy"], "$.full_model_copy"):
        raise DistributedProbeContractValidationError(f"{path} claims a full model copy")
    if value["proof_scope"] != "STRUCTURAL_DECLARATION_ONLY":
        raise DistributedProbeContractValidationError(
            f"{path} proof scope exceeds structural evidence"
        )
    _require_status_boundary(value)
    return snapshot


def _validate_case_ids(value: tuple[str, ...]) -> tuple[str, ...]:
    if type(value) is not tuple or not value or len(value) > 128:
        raise DistributedProbeContractValidationError(
            "case_ids must be a non-empty exact tuple with at most 128 entries"
        )
    result = tuple(
        expect_machine_id(item, f"case_ids[{index}]")
        for index, item in enumerate(value)
    )
    if len(result) != len(set(result)):
        raise DistributedProbeContractValidationError("case_ids contain duplicates")
    return result


def _validate_rank_specs(
    *,
    rank_specs: tuple[DistributedRankSpec, ...],
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    manifest: GeneratedProbeAdapterManifestArtifact,
    topology_id: str,
    topology_type: str,
    world_size: int,
    total_parameter_units: int,
) -> tuple[DistributedRankSpec, ...]:
    if type(rank_specs) is not tuple or len(rank_specs) != world_size:
        raise DistributedProbeContractValidationError(
            "rank_specs must be an exact tuple matching world_size"
        )
    expected_ranks = tuple(range(world_size))
    if tuple(spec.rank for spec in rank_specs) != expected_ranks:
        raise DistributedProbeContractValidationError(
            "rank_specs must be contiguous, unique, zero-based, and rank ordered"
        )
    site_owner = {site.site_id: site.owning_rank for site in manifest.sites}
    if any(rank < 0 or rank >= world_size for rank in site_owner.values()):
        raise DistributedProbeContractValidationError(
            "universal probe site owning rank is outside distributed world_size"
        )
    expected_sites_by_rank = {
        rank: tuple(
            site.site_id for site in manifest.sites if site.owning_rank == rank
        )
        for rank in expected_ranks
    }
    if any(not sites for sites in expected_sites_by_rank.values()):
        raise DistributedProbeContractValidationError(
            "every distributed rank must own at least one universal probe site"
        )
    flat_ranges: list[tuple[int, int, int]] = []
    validated: list[DistributedRankSpec] = []
    for spec in rank_specs:
        if type(spec) is not DistributedRankSpec:
            raise DistributedProbeContractValidationError(
                "rank_specs must contain exact DistributedRankSpec values"
            )
        ranges = _validate_ranges(
            spec.parameter_ranges, f"rank_specs[{spec.rank}].parameter_ranges"
        )
        if any(item.stop > total_parameter_units for item in ranges):
            raise DistributedProbeContractValidationError(
                "rank parameter range exceeds total model parameter units"
            )
        if sum(item.width for item in ranges) >= total_parameter_units:
            raise DistributedProbeContractValidationError(
                "a distributed rank owns a full model copy"
            )
        for item in ranges:
            flat_ranges.append((item.start, item.stop, spec.rank))
        if spec.owned_site_ids != expected_sites_by_rank[spec.rank]:
            raise DistributedProbeContractValidationError(
                "rank owned probe sites differ from exact universal owning ranks"
            )
        if type(spec.model_shard_bytes) is not bytes or not spec.model_shard_ref.verify_bytes(
            spec.model_shard_bytes
        ):
            raise DistributedProbeContractValidationError(
                "rank model shard bytes differ from their exact hash/length reference"
            )
        _validate_no_full_copy_proof(
            spec.no_full_copy_proof_bytes,
            spec.no_full_copy_proof_ref,
            identity=identity,
            configuration_ref=configuration_ref,
            topology_id=topology_id,
            topology_type=topology_type,
            world_size=world_size,
            rank=spec.rank,
            total_parameter_units=total_parameter_units,
            parameter_ranges=ranges,
            model_shard_ref=spec.model_shard_ref,
            path=f"rank_specs[{spec.rank}].no_full_copy_proof",
        )
        _validate_runtime_identity_body(
            spec.worker_runtime_bytes,
            spec.worker_runtime_ref,
            role=WORKER,
            rank=spec.rank,
            identity=identity,
            configuration_ref=configuration_ref,
            topology_id=topology_id,
            topology_type=topology_type,
            world_size=world_size,
            path=f"rank_specs[{spec.rank}].worker_runtime",
        )
        validated.append(spec)
    ordered_ranges = sorted(flat_ranges)
    cursor = 0
    for start, stop, _rank in ordered_ranges:
        if start != cursor:
            condition = "overlap" if start < cursor else "gap"
            raise DistributedProbeContractValidationError(
                f"global parameter ownership has a range {condition}"
            )
        cursor = stop
    if cursor != total_parameter_units:
        raise DistributedProbeContractValidationError(
            "global parameter ownership has a terminal range gap"
        )
    return tuple(validated)


def _build_fragment_slots(
    *,
    case_ids: tuple[str, ...],
    manifest: GeneratedProbeAdapterManifestArtifact,
) -> tuple[FragmentSlot, ...]:
    slots: list[FragmentSlot] = []
    ordinal = 1
    for case_id in case_ids:
        for site in manifest.sites:
            slots.append(
                FragmentSlot(
                    merge_ordinal=ordinal,
                    checkpoint_ordinal=ordinal,
                    rank=site.owning_rank,
                    site_id=site.site_id,
                    case_id=case_id,
                )
            )
            ordinal += 1
    if len(slots) > 4096:
        raise DistributedProbeContractValidationError(
            "distributed fragment schedule exceeds 4096 slots"
        )
    return tuple(slots)


def _rank_value(spec: DistributedRankSpec) -> dict[str, Any]:
    return {
        "rank": spec.rank,
        "parameter_ranges": [_range_value(item) for item in spec.parameter_ranges],
        "owned_site_ids": list(spec.owned_site_ids),
        "model_shard_ref": _ref_value(spec.model_shard_ref),
        "no_full_copy_proof_ref": _ref_value(spec.no_full_copy_proof_ref),
        "worker_runtime_ref": _ref_value(spec.worker_runtime_ref),
        "attempt_limit": 1,
        "retry": "FORBIDDEN",
        "replacement": "FORBIDDEN",
        "resume": "FORBIDDEN",
    }


def _slot_value(slot: FragmentSlot) -> dict[str, Any]:
    return {
        "merge_ordinal": slot.merge_ordinal,
        "checkpoint_ordinal": slot.checkpoint_ordinal,
        "rank": slot.rank,
        "site_id": slot.site_id,
        "case_id": slot.case_id,
    }


def _plan_value(
    *,
    plan_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    topology_id: str,
    topology_type: str,
    total_parameter_units: int,
    world_size: int,
    coordinator_runtime_ref: ArtifactRef,
    ranks: tuple[DistributedRankSpec, ...],
    case_ids: tuple[str, ...],
    fragment_slots: tuple[FragmentSlot, ...],
) -> dict[str, Any]:
    return {
        "schema": DISTRIBUTED_PROBE_PLAN_SCHEMA,
        "plan_id": plan_id,
        "model_identity": _model_binding(identity),
        "capabilities_ref": _ref_value(capabilities.artifact_ref),
        "configuration_ref": _ref_value(capabilities.configuration_ref),
        "discovery_ref": _ref_value(discovery.artifact_ref),
        "manifest_ref": _ref_value(manifest.artifact_ref),
        "canary_plan_ref": _ref_value(canary_plan.artifact_ref),
        "topology_id": topology_id,
        "topology_type": topology_type,
        "total_parameter_units": total_parameter_units,
        "world_size": world_size,
        "coordinator_runtime_ref": _ref_value(coordinator_runtime_ref),
        "ranks": [_rank_value(spec) for spec in ranks],
        "case_ids": list(case_ids),
        "fragment_slots": [_slot_value(slot) for slot in fragment_slots],
        "checkpoint_policy": "ONE_IMMUTABLE_CHECKPOINT_PER_MERGE_SLOT",
        "merge_policy": "EXACT_FROZEN_SLOT_ORDER",
        "attempt_limit": 1,
        "retry": "FORBIDDEN",
        "replacement": "FORBIDDEN",
        "resume": "FORBIDDEN",
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_distributed_probe_plan(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    coordinator_runtime_bytes: bytes,
    rank_specs: tuple[DistributedRankSpec, ...],
) -> DistributedProbePlanArtifact:
    identity, capabilities, discovery, manifest, canary_plan = (
        _validate_universal_dependencies(
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            manifest=manifest,
            canary_plan=canary_plan,
        )
    )
    snapshot, value = _canonical_object(raw, "distributed probe plan")
    expect_keys(
        value,
        required={
            "schema", "plan_id", "model_identity", "capabilities_ref",
            "configuration_ref", "discovery_ref", "manifest_ref",
            "canary_plan_ref", "topology_id", "topology_type",
            "total_parameter_units", "world_size", "coordinator_runtime_ref",
            "ranks", "case_ids", "fragment_slots", "checkpoint_policy",
            "merge_policy", "attempt_limit", "retry", "replacement", "resume",
            "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != DISTRIBUTED_PROBE_PLAN_SCHEMA:
        raise DistributedProbeContractValidationError("distributed plan schema drifted")
    plan_id = expect_machine_id(value["plan_id"], "$.plan_id")
    _require_model_binding(value["model_identity"], identity, "$.model_identity")
    expected_refs = (
        ("capabilities_ref", capabilities.artifact_ref),
        ("configuration_ref", capabilities.configuration_ref),
        ("discovery_ref", discovery.artifact_ref),
        ("manifest_ref", manifest.artifact_ref),
        ("canary_plan_ref", canary_plan.artifact_ref),
    )
    for field, expected in expected_refs:
        if parse_artifact_ref(value[field], f"$.{field}") != expected:
            raise DistributedProbeContractValidationError(
                f"distributed plan {field} differs from its exact dependency"
            )
    topology_id = expect_machine_id(value["topology_id"], "$.topology_id")
    topology_type = expect_enum(
        value["topology_type"], set(TOPOLOGY_TYPES), "$.topology_type"
    )
    total = expect_int(
        value["total_parameter_units"], "$.total_parameter_units", minimum=2
    )
    world_size = expect_int(
        value["world_size"], "$.world_size", minimum=2, maximum=4096
    )
    coordinator_runtime_ref = parse_artifact_ref(
        value["coordinator_runtime_ref"], "$.coordinator_runtime_ref"
    )
    _validate_runtime_identity_body(
        coordinator_runtime_bytes,
        coordinator_runtime_ref,
        role=COORDINATOR,
        rank=None,
        identity=identity,
        configuration_ref=capabilities.configuration_ref,
        topology_id=topology_id,
        topology_type=topology_type,
        world_size=world_size,
        path="coordinator_runtime",
    )
    ranks = _validate_rank_specs(
        rank_specs=rank_specs,
        identity=identity,
        configuration_ref=capabilities.configuration_ref,
        manifest=manifest,
        topology_id=topology_id,
        topology_type=topology_type,
        world_size=world_size,
        total_parameter_units=total,
    )
    raw_ranks = expect_list(value["ranks"], "$.ranks")
    if len(raw_ranks) != world_size:
        raise DistributedProbeContractValidationError(
            "distributed plan rank rows differ from world_size"
        )
    for index, (raw_rank, spec) in enumerate(zip(raw_ranks, ranks, strict=True)):
        row = expect_object(raw_rank, f"$.ranks[{index}]")
        expected_row = _rank_value(spec)
        expect_keys(row, required=expected_row, path=f"$.ranks[{index}]")
        if row != expected_row:
            raise DistributedProbeContractValidationError(
                "distributed plan rank projection differs from exact caller-bound rank"
            )
    raw_cases = expect_list(value["case_ids"], "$.case_ids")
    case_ids = _validate_case_ids(tuple(raw_cases))
    slots = _build_fragment_slots(case_ids=case_ids, manifest=manifest)
    raw_slots = expect_list(value["fragment_slots"], "$.fragment_slots")
    if len(raw_slots) != len(slots):
        raise DistributedProbeContractValidationError(
            "distributed plan fragment schedule is missing or duplicated"
        )
    for index, (raw_slot, slot) in enumerate(zip(raw_slots, slots, strict=True)):
        row = expect_object(raw_slot, f"$.fragment_slots[{index}]")
        expected_row = _slot_value(slot)
        expect_keys(row, required=expected_row, path=f"$.fragment_slots[{index}]")
        if row != expected_row:
            raise DistributedProbeContractValidationError(
                "distributed plan checkpoint or merge order drifted"
            )
    if (
        value["checkpoint_policy"] != "ONE_IMMUTABLE_CHECKPOINT_PER_MERGE_SLOT"
        or value["merge_policy"] != "EXACT_FROZEN_SLOT_ORDER"
    ):
        raise DistributedProbeContractValidationError(
            "distributed checkpoint or merge policy drifted"
        )
    if expect_int(value["attempt_limit"], "$.attempt_limit", minimum=1, maximum=1) != 1:
        raise DistributedProbeContractValidationError(
            "distributed plan permits exactly one attempt"
        )
    if any(value[field] != "FORBIDDEN" for field in ("retry", "replacement", "resume")):
        raise DistributedProbeContractValidationError(
            "distributed retry, replacement, and resume must remain forbidden"
        )
    _require_status_boundary(value)
    dependency_refs: list[ArtifactRef] = [
        identity.artifact_ref, *identity.artifact_refs,
        capabilities.artifact_ref, *capabilities.artifact_refs,
        discovery.artifact_ref, *discovery.artifact_refs,
        manifest.artifact_ref, *manifest.artifact_refs,
        canary_plan.artifact_ref, *canary_plan.artifact_refs,
        coordinator_runtime_ref,
    ]
    for spec in ranks:
        dependency_refs.extend(
            (
                spec.model_shard_ref,
                spec.no_full_copy_proof_ref,
                spec.worker_runtime_ref,
            )
        )
    refs = _owner_closure(
        plan_id, tuple(dependency_refs), "distributed plan artifact closure"
    )
    return DistributedProbePlanArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        plan_id=plan_id,
        identity_ref=identity.artifact_ref,
        capabilities_ref=capabilities.artifact_ref,
        configuration_ref=capabilities.configuration_ref,
        configuration_bytes=capabilities.configuration_bytes,
        discovery_ref=discovery.artifact_ref,
        manifest_ref=manifest.artifact_ref,
        canary_plan_ref=canary_plan.artifact_ref,
        topology_id=topology_id,
        topology_type=topology_type,
        total_parameter_units=total,
        world_size=world_size,
        coordinator_runtime_ref=coordinator_runtime_ref,
        coordinator_runtime_bytes=coordinator_runtime_bytes,
        ranks=ranks,
        case_ids=case_ids,
        fragment_slots=slots,
        payload=freeze_json(value),
        artifact_refs=refs,
    )


def build_distributed_probe_plan(
    *,
    plan_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    topology_id: str,
    topology_type: str,
    total_parameter_units: int,
    world_size: int,
    coordinator_runtime_ref: ArtifactRef,
    coordinator_runtime_bytes: bytes,
    rank_specs: tuple[DistributedRankSpec, ...],
    case_ids: tuple[str, ...],
) -> DistributedProbePlanArtifact:
    """Build a zero-call exact distributed ownership and fragment schedule."""

    plan_id = expect_machine_id(plan_id, "plan_id")
    topology_id = expect_machine_id(topology_id, "topology_id")
    topology_type = expect_enum(
        topology_type, set(TOPOLOGY_TYPES), "topology_type"
    )
    total = expect_int(total_parameter_units, "total_parameter_units", minimum=2)
    world_size = expect_int(world_size, "world_size", minimum=2, maximum=4096)
    identity, capabilities, discovery, manifest, canary_plan = (
        _validate_universal_dependencies(
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            manifest=manifest,
            canary_plan=canary_plan,
        )
    )
    coordinator_runtime_ref = _require_ref(
        coordinator_runtime_ref, "coordinator_runtime_ref"
    )
    _validate_runtime_identity_body(
        coordinator_runtime_bytes,
        coordinator_runtime_ref,
        role=COORDINATOR,
        rank=None,
        identity=identity,
        configuration_ref=capabilities.configuration_ref,
        topology_id=topology_id,
        topology_type=topology_type,
        world_size=world_size,
        path="coordinator_runtime",
    )
    ranks = _validate_rank_specs(
        rank_specs=rank_specs,
        identity=identity,
        configuration_ref=capabilities.configuration_ref,
        manifest=manifest,
        topology_id=topology_id,
        topology_type=topology_type,
        world_size=world_size,
        total_parameter_units=total,
    )
    case_ids = _validate_case_ids(case_ids)
    slots = _build_fragment_slots(case_ids=case_ids, manifest=manifest)
    raw = canonical_json_bytes(
        _plan_value(
            plan_id=plan_id,
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            manifest=manifest,
            canary_plan=canary_plan,
            topology_id=topology_id,
            topology_type=topology_type,
            total_parameter_units=total,
            world_size=world_size,
            coordinator_runtime_ref=coordinator_runtime_ref,
            ranks=ranks,
            case_ids=case_ids,
            fragment_slots=slots,
        )
    )
    return _load_distributed_probe_plan(
        raw,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        coordinator_runtime_bytes=coordinator_runtime_bytes,
        rank_specs=ranks,
    )


def load_distributed_probe_plan(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    coordinator_runtime_bytes: bytes,
    rank_specs: tuple[DistributedRankSpec, ...],
) -> DistributedProbePlanArtifact:
    return _load_distributed_probe_plan(
        raw,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        coordinator_runtime_bytes=coordinator_runtime_bytes,
        rank_specs=rank_specs,
    )


def replay_distributed_probe_plan(
    plan: DistributedProbePlanArtifact,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
) -> DistributedProbePlanArtifact:
    _artifact_storage(plan, DistributedProbePlanArtifact, "distributed plan")
    if (
        type(plan.ranks) is not tuple
        or any(type(item) is not DistributedRankSpec for item in plan.ranks)
        or type(plan.case_ids) is not tuple
        or type(plan.fragment_slots) is not tuple
        or any(type(item) is not FragmentSlot for item in plan.fragment_slots)
    ):
        raise DistributedProbeContractValidationError(
            "distributed plan projections must remain exact immutable types"
        )
    replayed = _load_distributed_probe_plan(
        plan.raw_bytes,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        coordinator_runtime_bytes=plan.coordinator_runtime_bytes,
        rank_specs=plan.ranks,
    )
    if replayed != plan:
        raise DistributedProbeContractValidationError(
            "distributed probe plan differs from exact-byte replay"
        )
    return replayed


def _validate_plan_dependency(
    *,
    plan: DistributedProbePlanArtifact,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
) -> DistributedProbePlanArtifact:
    replayed = replay_distributed_probe_plan(
        plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
    )
    if (
        replayed.identity_ref != identity.artifact_ref
        or replayed.capabilities_ref != capabilities.artifact_ref
        or replayed.configuration_ref != capabilities.configuration_ref
        or replayed.discovery_ref != discovery.artifact_ref
        or replayed.manifest_ref != manifest.artifact_ref
        or replayed.canary_plan_ref != canary_plan.artifact_ref
    ):
        raise DistributedProbeContractValidationError(
            "distributed plan differs from exact model and universal probe dependencies"
        )
    return replayed


def _fragment_value(
    *,
    fragment_id: str,
    object_version: str,
    plan: DistributedProbePlanArtifact,
    slot: FragmentSlot,
    content_ref: ArtifactRef,
) -> dict[str, Any]:
    return {
        "schema": DISTRIBUTED_PROBE_FRAGMENT_SCHEMA,
        "fragment_id": fragment_id,
        "object_version": object_version,
        "plan_ref": _ref_value(plan.artifact_ref),
        "merge_ordinal": slot.merge_ordinal,
        "checkpoint_ordinal": slot.checkpoint_ordinal,
        "rank": slot.rank,
        "site_id": slot.site_id,
        "case_id": slot.case_id,
        "attempt_number": 1,
        "content_ref": _ref_value(content_ref),
        "retry": "FORBIDDEN",
        "replacement": "FORBIDDEN",
        "resume": "FORBIDDEN",
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_distributed_probe_fragment(
    raw: Any,
    *,
    plan: DistributedProbePlanArtifact,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    content_bytes: bytes,
) -> DistributedProbeFragmentArtifact:
    identity, capabilities, discovery, manifest, canary_plan = (
        _validate_universal_dependencies(
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            manifest=manifest,
            canary_plan=canary_plan,
        )
    )
    plan = _validate_plan_dependency(
        plan=plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
    )
    snapshot, value = _canonical_object(raw, "distributed probe fragment")
    expect_keys(
        value,
        required={
            "schema", "fragment_id", "object_version", "plan_ref",
            "merge_ordinal", "checkpoint_ordinal", "rank", "site_id", "case_id",
            "attempt_number", "content_ref", "retry", "replacement", "resume",
            "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != DISTRIBUTED_PROBE_FRAGMENT_SCHEMA:
        raise DistributedProbeContractValidationError("fragment schema drifted")
    fragment_id = expect_machine_id(value["fragment_id"], "$.fragment_id")
    object_version = _immutable_version(value["object_version"], "$.object_version")
    if object_version != FRAGMENT_OBJECT_VERSION:
        raise DistributedProbeContractValidationError(
            "fragment object version differs from the frozen version"
        )
    if parse_artifact_ref(value["plan_ref"], "$.plan_ref") != plan.artifact_ref:
        raise DistributedProbeContractValidationError(
            "fragment is stale or bound to a different distributed plan"
        )
    merge_ordinal = expect_int(value["merge_ordinal"], "$.merge_ordinal", minimum=1)
    if merge_ordinal > len(plan.fragment_slots):
        raise DistributedProbeContractValidationError(
            "fragment merge ordinal is outside the frozen schedule"
        )
    expected_slot = plan.slot(merge_ordinal)
    supplied_slot = FragmentSlot(
        merge_ordinal=merge_ordinal,
        checkpoint_ordinal=expect_int(
            value["checkpoint_ordinal"], "$.checkpoint_ordinal", minimum=1
        ),
        rank=expect_int(value["rank"], "$.rank"),
        site_id=expect_machine_id(value["site_id"], "$.site_id"),
        case_id=expect_machine_id(value["case_id"], "$.case_id"),
    )
    if supplied_slot != expected_slot:
        if supplied_slot.rank != expected_slot.rank:
            raise DistributedProbeContractValidationError(
                "non-owning rank attempted to capture a probe tensor"
            )
        raise DistributedProbeContractValidationError(
            "fragment site, case, checkpoint, or merge slot drifted"
        )
    if expect_int(value["attempt_number"], "$.attempt_number", minimum=1, maximum=1) != 1:
        raise DistributedProbeContractValidationError(
            "fragment attempt number must remain exactly one"
        )
    content_ref = parse_artifact_ref(value["content_ref"], "$.content_ref")
    _require_media(
        content_ref, DISTRIBUTED_FRAGMENT_CONTENT_MEDIA_TYPE, "$.content_ref"
    )
    if type(content_bytes) is not bytes or not content_ref.verify_bytes(content_bytes):
        raise DistributedProbeContractValidationError(
            "fragment content hash or byte length disagrees with its exact reference"
        )
    if any(value[field] != "FORBIDDEN" for field in ("retry", "replacement", "resume")):
        raise DistributedProbeContractValidationError(
            "fragment retry, replacement, and resume must remain forbidden"
        )
    _require_status_boundary(value)
    refs = _owner_closure(
        fragment_id,
        (plan.artifact_ref, *plan.artifact_refs, content_ref),
        "fragment artifact closure",
    )
    return DistributedProbeFragmentArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        fragment_id=fragment_id,
        object_version=object_version,
        plan_ref=plan.artifact_ref,
        merge_ordinal=supplied_slot.merge_ordinal,
        checkpoint_ordinal=supplied_slot.checkpoint_ordinal,
        rank=supplied_slot.rank,
        site_id=supplied_slot.site_id,
        case_id=supplied_slot.case_id,
        attempt_number=1,
        content_ref=content_ref,
        content_bytes=content_bytes,
        payload=freeze_json(value),
        artifact_refs=refs,
    )


def build_distributed_probe_fragment(
    *,
    fragment_id: str,
    object_version: str,
    plan: DistributedProbePlanArtifact,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    merge_ordinal: int,
    checkpoint_ordinal: int,
    rank: int,
    site_id: str,
    case_id: str,
    attempt_number: int,
    content_ref: ArtifactRef,
    content_bytes: bytes,
) -> DistributedProbeFragmentArtifact:
    """Build one preloaded fragment for one exact rank/site/case slot."""

    fragment_id = expect_machine_id(fragment_id, "fragment_id")
    object_version = _immutable_version(object_version, "object_version")
    if object_version != FRAGMENT_OBJECT_VERSION:
        raise DistributedProbeContractValidationError(
            "fragment object version differs from the frozen version"
        )
    if expect_int(attempt_number, "attempt_number", minimum=1, maximum=1) != 1:
        raise DistributedProbeContractValidationError(
            "fragment attempt number must remain exactly one"
        )
    slot = FragmentSlot(
        merge_ordinal=merge_ordinal,
        checkpoint_ordinal=checkpoint_ordinal,
        rank=rank,
        site_id=site_id,
        case_id=case_id,
    )
    plan = _validate_plan_dependency(
        plan=plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
    )
    if slot != plan.slot(slot.merge_ordinal):
        if slot.rank != plan.slot(slot.merge_ordinal).rank:
            raise DistributedProbeContractValidationError(
                "non-owning rank attempted to capture a probe tensor"
            )
        raise DistributedProbeContractValidationError(
            "fragment differs from the frozen site/case/checkpoint/merge slot"
        )
    content_ref = _require_ref(content_ref, "content_ref")
    _require_media(
        content_ref, DISTRIBUTED_FRAGMENT_CONTENT_MEDIA_TYPE, "content_ref"
    )
    if type(content_bytes) is not bytes or not content_ref.verify_bytes(content_bytes):
        raise DistributedProbeContractValidationError(
            "fragment content hash or byte length disagrees with its reference"
        )
    raw = canonical_json_bytes(
        _fragment_value(
            fragment_id=fragment_id,
            object_version=object_version,
            plan=plan,
            slot=slot,
            content_ref=content_ref,
        )
    )
    return _load_distributed_probe_fragment(
        raw,
        plan=plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        content_bytes=content_bytes,
    )


def load_distributed_probe_fragment(
    raw: Any,
    *,
    plan: DistributedProbePlanArtifact,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    content_bytes: bytes,
) -> DistributedProbeFragmentArtifact:
    return _load_distributed_probe_fragment(
        raw,
        plan=plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        content_bytes=content_bytes,
    )


def replay_distributed_probe_fragment(
    fragment: DistributedProbeFragmentArtifact,
    *,
    plan: DistributedProbePlanArtifact,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
) -> DistributedProbeFragmentArtifact:
    _artifact_storage(fragment, DistributedProbeFragmentArtifact, "fragment")
    replayed = _load_distributed_probe_fragment(
        fragment.raw_bytes,
        plan=plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        content_bytes=fragment.content_bytes,
    )
    if replayed != fragment:
        raise DistributedProbeContractValidationError(
            "distributed fragment differs from exact-byte replay"
        )
    return replayed


def _validate_fragments(
    *,
    fragments: tuple[DistributedProbeFragmentArtifact, ...],
    plan: DistributedProbePlanArtifact,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
) -> tuple[DistributedProbeFragmentArtifact, ...]:
    if type(fragments) is not tuple or len(fragments) != len(plan.fragment_slots):
        raise DistributedProbeContractValidationError(
            "fragments must be an exact tuple covering every frozen slot"
        )
    validated: list[DistributedProbeFragmentArtifact] = []
    fragment_ids: set[str] = set()
    for index, (fragment, slot) in enumerate(
        zip(fragments, plan.fragment_slots, strict=True), start=1
    ):
        replayed = replay_distributed_probe_fragment(
            fragment,
            plan=plan,
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            manifest=manifest,
            canary_plan=canary_plan,
        )
        if replayed.merge_ordinal != index or (
            replayed.merge_ordinal,
            replayed.checkpoint_ordinal,
            replayed.rank,
            replayed.site_id,
            replayed.case_id,
        ) != (
            slot.merge_ordinal,
            slot.checkpoint_ordinal,
            slot.rank,
            slot.site_id,
            slot.case_id,
        ):
            raise DistributedProbeContractValidationError(
                "fragment is missing, stale, duplicated, conflicting, or out of merge order"
            )
        if replayed.fragment_id in fragment_ids:
            raise DistributedProbeContractValidationError(
                "distributed reconstruction contains a duplicate fragment object"
            )
        fragment_ids.add(replayed.fragment_id)
        validated.append(replayed)
    all_refs: list[ArtifactRef] = []
    for fragment in validated:
        all_refs.extend(
            (fragment.artifact_ref, *fragment.artifact_refs)
        )
    _unique_ref_closure(tuple(all_refs), "distributed fragment closure")
    return tuple(validated)


def _outcome_value(outcome: DistributedRankOutcome) -> dict[str, Any]:
    return {
        "rank": outcome.rank,
        "status": outcome.status,
        "attempt_number": outcome.attempt_number,
        "resumed": outcome.resumed,
        "replaced": outcome.replaced,
        "final_checkpoint_ordinal": outcome.final_checkpoint_ordinal,
    }


def _parse_outcome(value: Any, path: str) -> DistributedRankOutcome:
    row = expect_object(value, path)
    expect_keys(
        row,
        required={
            "rank", "status", "attempt_number", "resumed", "replaced",
            "final_checkpoint_ordinal",
        },
        path=path,
    )
    return DistributedRankOutcome(
        rank=expect_int(row["rank"], f"{path}.rank"),
        status=expect_enum(
            row["status"], set(RANK_OUTCOME_STATUSES), f"{path}.status"
        ),
        attempt_number=expect_int(
            row["attempt_number"], f"{path}.attempt_number", minimum=1, maximum=1
        ),
        resumed=expect_bool(row["resumed"], f"{path}.resumed"),
        replaced=expect_bool(row["replaced"], f"{path}.replaced"),
        final_checkpoint_ordinal=expect_int(
            row["final_checkpoint_ordinal"],
            f"{path}.final_checkpoint_ordinal",
            minimum=1,
        ),
    )


def _validate_rank_outcomes(
    outcomes: tuple[DistributedRankOutcome, ...],
    plan: DistributedProbePlanArtifact,
) -> tuple[DistributedRankOutcome, ...]:
    if type(outcomes) is not tuple or len(outcomes) != plan.world_size:
        raise DistributedProbeContractValidationError(
            "rank outcomes must be an exact tuple matching world_size"
        )
    if tuple(item.rank for item in outcomes) != tuple(range(plan.world_size)):
        raise DistributedProbeContractValidationError(
            "rank outcomes must be unique, contiguous, zero-based, and rank ordered"
        )
    expected_final = {
        rank: max(
            slot.checkpoint_ordinal
            for slot in plan.fragment_slots
            if slot.rank == rank
        )
        for rank in range(plan.world_size)
    }
    validated: list[DistributedRankOutcome] = []
    for outcome in outcomes:
        if type(outcome) is not DistributedRankOutcome:
            raise DistributedProbeContractValidationError(
                "rank outcomes must contain exact DistributedRankOutcome values"
            )
        if outcome.status == RANK_FAILED:
            raise DistributedProbeContractValidationError(
                f"distributed rank {outcome.rank} failed"
            )
        if outcome.status == RANK_OOM:
            raise DistributedProbeContractValidationError(
                f"distributed rank {outcome.rank} reported OOM"
            )
        if outcome.status != COMPLETED:
            raise DistributedProbeContractValidationError(
                "every distributed rank must complete"
            )
        if outcome.attempt_number != 1:
            raise DistributedProbeContractValidationError(
                "every distributed rank permits exactly one attempt"
            )
        if outcome.resumed or outcome.replaced:
            raise DistributedProbeContractValidationError(
                "resume cannot imply retry, replacement, or another attempt"
            )
        if outcome.final_checkpoint_ordinal != expected_final[outcome.rank]:
            raise DistributedProbeContractValidationError(
                "rank final checkpoint is missing, stale, or beyond its frozen slots"
            )
        validated.append(outcome)
    return tuple(validated)


def build_independent_reconstruction_evidence_body(
    *,
    evidence_id: str,
    receipt_id: str,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    plan_ref: ArtifactRef,
    fragment_refs: tuple[ArtifactRef, ...],
    reconstructed_output_ref: ArtifactRef,
    independent_runtime_ref: ArtifactRef,
) -> bytes:
    """Build typed evidence for a separate in-memory byte reconstruction."""

    identity = replay_comparison_model_identity(identity)
    configuration_ref = _require_ref(configuration_ref, "configuration_ref")
    _require_media(
        configuration_ref,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        "configuration_ref",
    )
    plan_ref = _require_ref(plan_ref, "plan_ref")
    _require_media(plan_ref, DISTRIBUTED_PROBE_PLAN_MEDIA_TYPE, "plan_ref")
    if type(fragment_refs) is not tuple or not fragment_refs:
        raise DistributedProbeContractValidationError(
            "fragment_refs must be a non-empty exact tuple"
        )
    for index, reference in enumerate(fragment_refs):
        _require_ref(reference, f"fragment_refs[{index}]")
        _require_media(
            reference,
            DISTRIBUTED_PROBE_FRAGMENT_MEDIA_TYPE,
            f"fragment_refs[{index}]",
        )
    _unique_ref_closure(fragment_refs, "fragment_refs")
    reconstructed_output_ref = _require_ref(
        reconstructed_output_ref, "reconstructed_output_ref"
    )
    _require_media(
        reconstructed_output_ref,
        DISTRIBUTED_RECONSTRUCTED_OUTPUT_MEDIA_TYPE,
        "reconstructed_output_ref",
    )
    independent_runtime_ref = _require_ref(
        independent_runtime_ref, "independent_runtime_ref"
    )
    _require_media(
        independent_runtime_ref,
        DISTRIBUTED_RUNTIME_IDENTITY_MEDIA_TYPE,
        "independent_runtime_ref",
    )
    return canonical_json_bytes(
        {
            "schema": INDEPENDENT_RECONSTRUCTION_EVIDENCE_SCHEMA,
            "evidence_id": expect_machine_id(evidence_id, "evidence_id"),
            "receipt_id": expect_machine_id(receipt_id, "receipt_id"),
            "model_identity": _model_binding(identity),
            "configuration_ref": _ref_value(configuration_ref),
            "plan_ref": _ref_value(plan_ref),
            "ordered_fragment_refs": [_ref_value(item) for item in fragment_refs],
            "reconstructed_output_ref": _ref_value(reconstructed_output_ref),
            "independent_runtime_ref": _ref_value(independent_runtime_ref),
            "algorithm": "BYTE_CONCAT_IN_FROZEN_MERGE_ORDER_V1",
            "independence": "SEPARATE_RUNTIME_IDENTITY_REPLAY",
            "model_capability_claim": UNMEASURED,
            "status": dict(_STATUS),
            "boundary": dict(_BOUNDARY),
        }
    )


def _validate_independent_evidence(
    raw: Any,
    reference: ArtifactRef,
    *,
    receipt_id: str,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    plan_ref: ArtifactRef,
    fragment_refs: tuple[ArtifactRef, ...],
    reconstructed_output_ref: ArtifactRef,
    independent_runtime_ref: ArtifactRef,
) -> bytes:
    reference = _require_ref(reference, "independent_evidence_ref")
    _require_media(
        reference,
        INDEPENDENT_RECONSTRUCTION_EVIDENCE_MEDIA_TYPE,
        "independent_evidence_ref",
    )
    if type(raw) is not bytes or not reference.verify_bytes(raw):
        raise DistributedProbeContractValidationError(
            "independent reconstruction evidence hash or length disagrees"
        )
    snapshot, value = _canonical_object(raw, "independent reconstruction evidence")
    expect_keys(
        value,
        required={
            "schema", "evidence_id", "receipt_id", "model_identity",
            "configuration_ref", "plan_ref", "ordered_fragment_refs",
            "reconstructed_output_ref", "independent_runtime_ref", "algorithm",
            "independence", "model_capability_claim", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != INDEPENDENT_RECONSTRUCTION_EVIDENCE_SCHEMA:
        raise DistributedProbeContractValidationError(
            "independent reconstruction evidence schema drifted"
        )
    if expect_machine_id(value["evidence_id"], "$.evidence_id") != reference.artifact_id:
        raise DistributedProbeContractValidationError(
            "independent evidence ID differs from its reference"
        )
    if expect_machine_id(value["receipt_id"], "$.receipt_id") != receipt_id:
        raise DistributedProbeContractValidationError(
            "independent evidence receipt ID drifted"
        )
    _require_model_binding(value["model_identity"], identity, "$.model_identity")
    if parse_artifact_ref(value["configuration_ref"], "$.configuration_ref") != configuration_ref:
        raise DistributedProbeContractValidationError(
            "independent evidence configuration drifted"
        )
    if parse_artifact_ref(value["plan_ref"], "$.plan_ref") != plan_ref:
        raise DistributedProbeContractValidationError(
            "independent evidence distributed plan drifted"
        )
    raw_fragment_refs = expect_list(
        value["ordered_fragment_refs"], "$.ordered_fragment_refs"
    )
    parsed_fragment_refs = tuple(
        parse_artifact_ref(item, f"$.ordered_fragment_refs[{index}]")
        for index, item in enumerate(raw_fragment_refs)
    )
    if parsed_fragment_refs != fragment_refs:
        raise DistributedProbeContractValidationError(
            "independent evidence fragment order drifted"
        )
    if parse_artifact_ref(value["reconstructed_output_ref"], "$.reconstructed_output_ref") != reconstructed_output_ref:
        raise DistributedProbeContractValidationError(
            "independent evidence output hash or length drifted"
        )
    if parse_artifact_ref(value["independent_runtime_ref"], "$.independent_runtime_ref") != independent_runtime_ref:
        raise DistributedProbeContractValidationError(
            "independent evidence runtime identity drifted"
        )
    if (
        value["algorithm"] != "BYTE_CONCAT_IN_FROZEN_MERGE_ORDER_V1"
        or value["independence"] != "SEPARATE_RUNTIME_IDENTITY_REPLAY"
        or value["model_capability_claim"] != UNMEASURED
    ):
        raise DistributedProbeContractValidationError(
            "independent reconstruction scope or capability claim drifted"
        )
    _require_status_boundary(value)
    return snapshot


def _fragment_receipt_value(
    fragment: DistributedProbeFragmentArtifact,
) -> dict[str, Any]:
    return {
        "fragment_ref": _ref_value(fragment.artifact_ref),
        "object_version": fragment.object_version,
        "merge_ordinal": fragment.merge_ordinal,
        "checkpoint_ordinal": fragment.checkpoint_ordinal,
        "rank": fragment.rank,
        "site_id": fragment.site_id,
        "case_id": fragment.case_id,
        "attempt_number": fragment.attempt_number,
        "content_ref": _ref_value(fragment.content_ref),
    }


def _receipt_value(
    *,
    receipt_id: str,
    identity: ComparisonModelIdentityArtifact,
    plan: DistributedProbePlanArtifact,
    fragments: tuple[DistributedProbeFragmentArtifact, ...],
    outcomes: tuple[DistributedRankOutcome, ...],
    reconstructed_output_ref: ArtifactRef,
    independent_runtime_ref: ArtifactRef,
    independent_evidence_ref: ArtifactRef,
) -> dict[str, Any]:
    return {
        "schema": INDEPENDENT_RECONSTRUCTION_RECEIPT_SCHEMA,
        "receipt_id": receipt_id,
        "model_identity": _model_binding(identity),
        "configuration_ref": _ref_value(plan.configuration_ref),
        "plan_ref": _ref_value(plan.artifact_ref),
        "fragments": [_fragment_receipt_value(item) for item in fragments],
        "rank_outcomes": [_outcome_value(item) for item in outcomes],
        "reconstructed_output_ref": _ref_value(reconstructed_output_ref),
        "independent_runtime_ref": _ref_value(independent_runtime_ref),
        "independent_evidence_ref": _ref_value(independent_evidence_ref),
        "reconstruction_algorithm": "BYTE_CONCAT_IN_FROZEN_MERGE_ORDER_V1",
        "reconstruction_result": "EXACT_HASH_AND_LENGTH_MATCH",
        "capability_state": UNMEASURED,
        "attempt_limit": 1,
        "retry": "FORBIDDEN",
        "replacement": "FORBIDDEN",
        "resume": "FORBIDDEN",
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_independent_reconstruction_receipt(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    plan: DistributedProbePlanArtifact,
    fragments: tuple[DistributedProbeFragmentArtifact, ...],
    rank_outcomes: tuple[DistributedRankOutcome, ...],
    reconstructed_output_bytes: bytes,
    independent_runtime_bytes: bytes,
    independent_evidence_bytes: bytes,
) -> IndependentReconstructionReceiptArtifact:
    identity, capabilities, discovery, manifest, canary_plan = (
        _validate_universal_dependencies(
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            manifest=manifest,
            canary_plan=canary_plan,
        )
    )
    plan = _validate_plan_dependency(
        plan=plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
    )
    fragments = _validate_fragments(
        fragments=fragments,
        plan=plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
    )
    rank_outcomes = _validate_rank_outcomes(rank_outcomes, plan)
    snapshot, value = _canonical_object(raw, "independent reconstruction receipt")
    expect_keys(
        value,
        required={
            "schema", "receipt_id", "model_identity", "configuration_ref",
            "plan_ref", "fragments", "rank_outcomes", "reconstructed_output_ref",
            "independent_runtime_ref", "independent_evidence_ref",
            "reconstruction_algorithm", "reconstruction_result", "capability_state",
            "attempt_limit", "retry", "replacement", "resume", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != INDEPENDENT_RECONSTRUCTION_RECEIPT_SCHEMA:
        raise DistributedProbeContractValidationError(
            "independent reconstruction receipt schema drifted"
        )
    receipt_id = expect_machine_id(value["receipt_id"], "$.receipt_id")
    _require_model_binding(value["model_identity"], identity, "$.model_identity")
    if parse_artifact_ref(value["configuration_ref"], "$.configuration_ref") != plan.configuration_ref:
        raise DistributedProbeContractValidationError(
            "reconstruction receipt configuration drifted"
        )
    if parse_artifact_ref(value["plan_ref"], "$.plan_ref") != plan.artifact_ref:
        raise DistributedProbeContractValidationError(
            "reconstruction receipt is stale or bound to another plan"
        )
    raw_fragments = expect_list(value["fragments"], "$.fragments")
    if len(raw_fragments) != len(fragments):
        raise DistributedProbeContractValidationError(
            "reconstruction receipt has a missing or duplicate fragment"
        )
    for index, (raw_fragment, fragment) in enumerate(
        zip(raw_fragments, fragments, strict=True)
    ):
        row = expect_object(raw_fragment, f"$.fragments[{index}]")
        expected_row = _fragment_receipt_value(fragment)
        expect_keys(row, required=expected_row, path=f"$.fragments[{index}]")
        if row != expected_row:
            raise DistributedProbeContractValidationError(
                "reconstruction fragment is stale, conflicting, corrupted, or out of merge order"
            )
    raw_outcomes = expect_list(value["rank_outcomes"], "$.rank_outcomes")
    parsed_outcomes = tuple(
        _parse_outcome(item, f"$.rank_outcomes[{index}]")
        for index, item in enumerate(raw_outcomes)
    )
    if _validate_rank_outcomes(parsed_outcomes, plan) != rank_outcomes:
        raise DistributedProbeContractValidationError(
            "reconstruction rank outcomes differ from caller-bound outcomes"
        )
    reconstructed_output_ref = parse_artifact_ref(
        value["reconstructed_output_ref"], "$.reconstructed_output_ref"
    )
    _require_media(
        reconstructed_output_ref,
        DISTRIBUTED_RECONSTRUCTED_OUTPUT_MEDIA_TYPE,
        "$.reconstructed_output_ref",
    )
    expected_output = b"".join(fragment.content_bytes for fragment in fragments)
    if (
        type(reconstructed_output_bytes) is not bytes
        or reconstructed_output_bytes != expected_output
        or not reconstructed_output_ref.verify_bytes(reconstructed_output_bytes)
    ):
        raise DistributedProbeContractValidationError(
            "independent reconstruction hash or byte length disagrees with exact merge bytes"
        )
    independent_runtime_ref = parse_artifact_ref(
        value["independent_runtime_ref"], "$.independent_runtime_ref"
    )
    _validate_runtime_identity_body(
        independent_runtime_bytes,
        independent_runtime_ref,
        role=INDEPENDENT_RECONSTRUCTOR,
        rank=None,
        identity=identity,
        configuration_ref=plan.configuration_ref,
        topology_id=plan.topology_id,
        topology_type=plan.topology_type,
        world_size=plan.world_size,
        path="independent_runtime",
    )
    independent_evidence_ref = parse_artifact_ref(
        value["independent_evidence_ref"], "$.independent_evidence_ref"
    )
    fragment_refs = tuple(fragment.artifact_ref for fragment in fragments)
    independent_evidence_bytes = _validate_independent_evidence(
        independent_evidence_bytes,
        independent_evidence_ref,
        receipt_id=receipt_id,
        identity=identity,
        configuration_ref=plan.configuration_ref,
        plan_ref=plan.artifact_ref,
        fragment_refs=fragment_refs,
        reconstructed_output_ref=reconstructed_output_ref,
        independent_runtime_ref=independent_runtime_ref,
    )
    if (
        value["reconstruction_algorithm"]
        != "BYTE_CONCAT_IN_FROZEN_MERGE_ORDER_V1"
        or value["reconstruction_result"] != "EXACT_HASH_AND_LENGTH_MATCH"
        or value["capability_state"] != UNMEASURED
    ):
        raise DistributedProbeContractValidationError(
            "reconstruction result cannot promote unmeasured distributed capability"
        )
    if expect_int(value["attempt_limit"], "$.attempt_limit", minimum=1, maximum=1) != 1:
        raise DistributedProbeContractValidationError(
            "reconstruction permits exactly one attempt"
        )
    if any(value[field] != "FORBIDDEN" for field in ("retry", "replacement", "resume")):
        raise DistributedProbeContractValidationError(
            "reconstruction retry, replacement, and resume must remain forbidden"
        )
    _require_status_boundary(value)
    dependency_refs: list[ArtifactRef] = [
        plan.artifact_ref,
        *plan.artifact_refs,
        reconstructed_output_ref,
        independent_runtime_ref,
        independent_evidence_ref,
    ]
    for fragment in fragments:
        dependency_refs.extend((fragment.artifact_ref, *fragment.artifact_refs))
    refs = _owner_closure(
        receipt_id,
        tuple(dependency_refs),
        "independent reconstruction artifact closure",
    )
    return IndependentReconstructionReceiptArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        receipt_id=receipt_id,
        plan_ref=plan.artifact_ref,
        fragment_refs=fragment_refs,
        rank_outcomes=rank_outcomes,
        reconstructed_output_ref=reconstructed_output_ref,
        reconstructed_output_bytes=reconstructed_output_bytes,
        independent_runtime_ref=independent_runtime_ref,
        independent_runtime_bytes=independent_runtime_bytes,
        independent_evidence_ref=independent_evidence_ref,
        independent_evidence_bytes=independent_evidence_bytes,
        capability_state=UNMEASURED,
        payload=freeze_json(value),
        artifact_refs=refs,
    )


def build_independent_reconstruction_receipt(
    *,
    receipt_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    plan: DistributedProbePlanArtifact,
    fragments: tuple[DistributedProbeFragmentArtifact, ...],
    rank_outcomes: tuple[DistributedRankOutcome, ...],
    reconstructed_output_ref: ArtifactRef,
    reconstructed_output_bytes: bytes,
    independent_runtime_ref: ArtifactRef,
    independent_runtime_bytes: bytes,
    independent_evidence_ref: ArtifactRef,
    independent_evidence_bytes: bytes,
) -> IndependentReconstructionReceiptArtifact:
    """Mechanically verify every fragment and seal an independent replay receipt."""

    receipt_id = expect_machine_id(receipt_id, "receipt_id")
    plan = _validate_plan_dependency(
        plan=plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
    )
    fragments = _validate_fragments(
        fragments=fragments,
        plan=plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
    )
    outcomes = _validate_rank_outcomes(rank_outcomes, plan)
    reconstructed_output_ref = _require_ref(
        reconstructed_output_ref, "reconstructed_output_ref"
    )
    _require_media(
        reconstructed_output_ref,
        DISTRIBUTED_RECONSTRUCTED_OUTPUT_MEDIA_TYPE,
        "reconstructed_output_ref",
    )
    expected_output = b"".join(fragment.content_bytes for fragment in fragments)
    if (
        type(reconstructed_output_bytes) is not bytes
        or reconstructed_output_bytes != expected_output
        or not reconstructed_output_ref.verify_bytes(reconstructed_output_bytes)
    ):
        raise DistributedProbeContractValidationError(
            "independent reconstruction hash or byte length disagrees with exact merge bytes"
        )
    _validate_runtime_identity_body(
        independent_runtime_bytes,
        independent_runtime_ref,
        role=INDEPENDENT_RECONSTRUCTOR,
        rank=None,
        identity=identity,
        configuration_ref=plan.configuration_ref,
        topology_id=plan.topology_id,
        topology_type=plan.topology_type,
        world_size=plan.world_size,
        path="independent_runtime",
    )
    fragment_refs = tuple(fragment.artifact_ref for fragment in fragments)
    _validate_independent_evidence(
        independent_evidence_bytes,
        independent_evidence_ref,
        receipt_id=receipt_id,
        identity=identity,
        configuration_ref=plan.configuration_ref,
        plan_ref=plan.artifact_ref,
        fragment_refs=fragment_refs,
        reconstructed_output_ref=reconstructed_output_ref,
        independent_runtime_ref=independent_runtime_ref,
    )
    raw = canonical_json_bytes(
        _receipt_value(
            receipt_id=receipt_id,
            identity=identity,
            plan=plan,
            fragments=fragments,
            outcomes=outcomes,
            reconstructed_output_ref=reconstructed_output_ref,
            independent_runtime_ref=independent_runtime_ref,
            independent_evidence_ref=independent_evidence_ref,
        )
    )
    return _load_independent_reconstruction_receipt(
        raw,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        plan=plan,
        fragments=fragments,
        rank_outcomes=outcomes,
        reconstructed_output_bytes=reconstructed_output_bytes,
        independent_runtime_bytes=independent_runtime_bytes,
        independent_evidence_bytes=independent_evidence_bytes,
    )


def load_independent_reconstruction_receipt(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    plan: DistributedProbePlanArtifact,
    fragments: tuple[DistributedProbeFragmentArtifact, ...],
    rank_outcomes: tuple[DistributedRankOutcome, ...],
    reconstructed_output_bytes: bytes,
    independent_runtime_bytes: bytes,
    independent_evidence_bytes: bytes,
) -> IndependentReconstructionReceiptArtifact:
    return _load_independent_reconstruction_receipt(
        raw,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        plan=plan,
        fragments=fragments,
        rank_outcomes=rank_outcomes,
        reconstructed_output_bytes=reconstructed_output_bytes,
        independent_runtime_bytes=independent_runtime_bytes,
        independent_evidence_bytes=independent_evidence_bytes,
    )


def replay_independent_reconstruction_receipt(
    receipt: IndependentReconstructionReceiptArtifact,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    plan: DistributedProbePlanArtifact,
    fragments: tuple[DistributedProbeFragmentArtifact, ...],
) -> IndependentReconstructionReceiptArtifact:
    _artifact_storage(
        receipt, IndependentReconstructionReceiptArtifact, "reconstruction receipt"
    )
    if (
        type(receipt.fragment_refs) is not tuple
        or type(receipt.rank_outcomes) is not tuple
        or any(type(item) is not DistributedRankOutcome for item in receipt.rank_outcomes)
    ):
        raise DistributedProbeContractValidationError(
            "reconstruction receipt projections must remain exact immutable values"
        )
    replayed = _load_independent_reconstruction_receipt(
        receipt.raw_bytes,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        plan=plan,
        fragments=fragments,
        rank_outcomes=receipt.rank_outcomes,
        reconstructed_output_bytes=receipt.reconstructed_output_bytes,
        independent_runtime_bytes=receipt.independent_runtime_bytes,
        independent_evidence_bytes=receipt.independent_evidence_bytes,
    )
    if replayed != receipt:
        raise DistributedProbeContractValidationError(
            "independent reconstruction receipt differs from exact-byte replay"
        )
    return replayed


@dataclass(slots=True)
class _ReplayBackendSeal:
    identity: ComparisonModelIdentityArtifact
    capabilities: ComparisonModelCapabilitiesArtifact
    discovery: ArchitectureDiscoveryReceiptArtifact
    manifest: GeneratedProbeAdapterManifestArtifact
    canary_plan: UniversalProbeCanaryPlanArtifact
    plan: DistributedProbePlanArtifact
    fragments: tuple[DistributedProbeFragmentArtifact, ...]
    receipt: IndependentReconstructionReceiptArtifact
    request: DistributedProbeReplayRequest
    signature: tuple[Any, ...]
    consumed: bool
    lock: threading.RLock


@dataclass(frozen=True, slots=True)
class _UnavailableBackendSeal:
    identity: ComparisonModelIdentityArtifact
    capabilities: ComparisonModelCapabilitiesArtifact
    configuration_ref: ArtifactRef
    signature: tuple[Any, ...]
    reason: str


_BACKEND_LOCK = threading.RLock()
_REPLAY_BACKENDS: WeakKeyDictionary[Any, _ReplayBackendSeal] = WeakKeyDictionary()
_UNAVAILABLE_BACKENDS: WeakKeyDictionary[Any, _UnavailableBackendSeal] = WeakKeyDictionary()


def _factory_only(name: str) -> NoReturn:
    raise TypeError(f"{name} is factory-only")


def _not_copyable(name: str) -> NoReturn:
    raise TypeError(f"{name} cannot be copied, replaced, or pickled")


class ReplayDistributedProbeBackend:
    """Process-sealed, single-use replay of exact reconstruction artifacts."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: Any, **kwargs: Any) -> ReplayDistributedProbeBackend:
        del args, kwargs
        _factory_only("ReplayDistributedProbeBackend")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("ReplayDistributedProbeBackend cannot be subclassed")

    def __copy__(self) -> NoReturn:
        _not_copyable("ReplayDistributedProbeBackend")

    def __deepcopy__(self, memo: Any) -> NoReturn:
        del memo
        _not_copyable("ReplayDistributedProbeBackend")

    def __reduce__(self) -> NoReturn:
        _not_copyable("ReplayDistributedProbeBackend")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _not_copyable("ReplayDistributedProbeBackend")

    def __replace__(self, **changes: Any) -> NoReturn:
        del changes
        _not_copyable("ReplayDistributedProbeBackend")

    @property
    def mode(self) -> str:
        _require_replay_backend(self)
        return REPLAY_ONLY

    @property
    def status(self) -> str:
        _require_replay_backend(self)
        return STRUCTURE_ONLY

    @property
    def authority(self) -> str:
        _require_replay_backend(self)
        return NON_AUTHORITY

    @property
    def consumed(self) -> bool:
        seal = _require_replay_backend(self)
        with seal.lock:
            return seal.consumed

    def reconstruct(
        self, request: DistributedProbeReplayRequest
    ) -> IndependentReconstructionReceiptArtifact:
        seal = _require_replay_backend(self)
        with seal.lock:
            if seal.consumed:
                raise DistributedProbeContractValidationError(
                    "distributed reconstruction replay was already consumed exactly once"
                )
            _verify_replay_backend(seal)
            if type(request) is not DistributedProbeReplayRequest or request is not seal.request:
                raise DistributedProbeContractValidationError(
                    "distributed replay requires the exact sealed request object"
                )
            detached = replay_independent_reconstruction_receipt(
                seal.receipt,
                identity=seal.identity,
                capabilities=seal.capabilities,
                discovery=seal.discovery,
                manifest=seal.manifest,
                canary_plan=seal.canary_plan,
                plan=seal.plan,
                fragments=seal.fragments,
            )
            if detached is seal.receipt:
                raise DistributedProbeContractValidationError(
                    "distributed reconstruction replay did not detach its return value"
                )
            seal.consumed = True
            return detached


class UnavailableDistributedProbeBackend:
    """A process-sealed backend that fails before inspecting caller input."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: Any, **kwargs: Any) -> UnavailableDistributedProbeBackend:
        del args, kwargs
        _factory_only("UnavailableDistributedProbeBackend")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("UnavailableDistributedProbeBackend cannot be subclassed")

    def __copy__(self) -> NoReturn:
        _not_copyable("UnavailableDistributedProbeBackend")

    def __deepcopy__(self, memo: Any) -> NoReturn:
        del memo
        _not_copyable("UnavailableDistributedProbeBackend")

    def __reduce__(self) -> NoReturn:
        _not_copyable("UnavailableDistributedProbeBackend")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _not_copyable("UnavailableDistributedProbeBackend")

    def __replace__(self, **changes: Any) -> NoReturn:
        del changes
        _not_copyable("UnavailableDistributedProbeBackend")

    @property
    def mode(self) -> str:
        _require_unavailable_backend(self)
        return UNAVAILABLE

    @property
    def status(self) -> str:
        _require_unavailable_backend(self)
        return STRUCTURE_ONLY

    @property
    def authority(self) -> str:
        _require_unavailable_backend(self)
        return NON_AUTHORITY

    def reconstruct(self, request: object) -> NoReturn:
        del request
        seal = _require_unavailable_backend(self)
        raise DistributedProbeBackendUnavailableError(seal.reason)


def _model_only_signature(
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> tuple[Any, ...]:
    return (
        identity.artifact_ref,
        identity.raw_bytes,
        identity.artifact_refs,
        capabilities.artifact_ref,
        capabilities.raw_bytes,
        capabilities.configuration_ref,
        capabilities.configuration_bytes,
        capabilities.artifact_refs,
    )


def _validate_model_only(
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> tuple[ComparisonModelIdentityArtifact, ComparisonModelCapabilitiesArtifact]:
    identity = replay_comparison_model_identity(identity)
    capabilities = replay_comparison_model_capabilities(
        capabilities, identity=identity
    )
    if (
        capabilities.identity_ref != identity.artifact_ref
        or capabilities.provider != identity.provider
        or capabilities.model_id != identity.model_id
        or capabilities.revision != identity.revision
        or capabilities.access_kind != identity.access_kind
    ):
        raise DistributedProbeContractValidationError(
            "distributed backend model/capability binding drifted"
        )
    return identity, capabilities


def _replay_signature(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    plan: DistributedProbePlanArtifact,
    fragments: tuple[DistributedProbeFragmentArtifact, ...],
    receipt: IndependentReconstructionReceiptArtifact,
) -> tuple[Any, ...]:
    fragment_values = tuple(
        (
            fragment.artifact_ref,
            fragment.raw_bytes,
            fragment.content_ref,
            fragment.content_bytes,
            fragment.artifact_refs,
        )
        for fragment in fragments
    )
    return (
        *_model_only_signature(identity, capabilities),
        discovery.artifact_ref,
        discovery.raw_bytes,
        manifest.artifact_ref,
        manifest.raw_bytes,
        canary_plan.artifact_ref,
        canary_plan.raw_bytes,
        plan.artifact_ref,
        plan.raw_bytes,
        plan.artifact_refs,
        fragment_values,
        receipt.artifact_ref,
        receipt.raw_bytes,
        receipt.reconstructed_output_ref,
        receipt.reconstructed_output_bytes,
        receipt.artifact_refs,
    )


def _validate_replay_bundle(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    plan: DistributedProbePlanArtifact,
    fragments: tuple[DistributedProbeFragmentArtifact, ...],
    receipt: IndependentReconstructionReceiptArtifact,
) -> tuple[
    ComparisonModelIdentityArtifact,
    ComparisonModelCapabilitiesArtifact,
    ArchitectureDiscoveryReceiptArtifact,
    GeneratedProbeAdapterManifestArtifact,
    UniversalProbeCanaryPlanArtifact,
    DistributedProbePlanArtifact,
    tuple[DistributedProbeFragmentArtifact, ...],
    IndependentReconstructionReceiptArtifact,
]:
    identity, capabilities, discovery, manifest, canary_plan = (
        _validate_universal_dependencies(
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            manifest=manifest,
            canary_plan=canary_plan,
        )
    )
    plan = _validate_plan_dependency(
        plan=plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
    )
    fragments = _validate_fragments(
        fragments=fragments,
        plan=plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
    )
    receipt = replay_independent_reconstruction_receipt(
        receipt,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        plan=plan,
        fragments=fragments,
    )
    closure: list[ArtifactRef] = [
        plan.artifact_ref, *plan.artifact_refs,
        receipt.artifact_ref, *receipt.artifact_refs,
    ]
    for fragment in fragments:
        closure.extend((fragment.artifact_ref, *fragment.artifact_refs))
    _unique_ref_closure(tuple(closure), "distributed replay bundle closure")
    return (
        identity,
        capabilities,
        discovery,
        manifest,
        canary_plan,
        plan,
        fragments,
        receipt,
    )


def build_replay_distributed_probe_backend(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    canary_plan: UniversalProbeCanaryPlanArtifact,
    plan: DistributedProbePlanArtifact,
    fragments: tuple[DistributedProbeFragmentArtifact, ...],
    receipt: IndependentReconstructionReceiptArtifact,
) -> tuple[ReplayDistributedProbeBackend, DistributedProbeReplayRequest]:
    """Seal one exact, single-use, side-effect-free reconstruction replay."""

    bundle = _validate_replay_bundle(
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        plan=plan,
        fragments=fragments,
        receipt=receipt,
    )
    (
        identity,
        capabilities,
        discovery,
        manifest,
        canary_plan,
        plan,
        fragments,
        receipt,
    ) = bundle
    request = DistributedProbeReplayRequest(
        plan_ref=plan.artifact_ref,
        reconstruction_receipt_ref=receipt.artifact_ref,
    )
    signature = _replay_signature(
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        plan=plan,
        fragments=fragments,
        receipt=receipt,
    )
    backend = object.__new__(ReplayDistributedProbeBackend)
    seal = _ReplayBackendSeal(
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        plan=plan,
        fragments=fragments,
        receipt=receipt,
        request=request,
        signature=signature,
        consumed=False,
        lock=threading.RLock(),
    )
    with _BACKEND_LOCK:
        _REPLAY_BACKENDS[backend] = seal
    return backend, request


def build_unavailable_distributed_probe_backend(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    reason: str,
) -> UnavailableDistributedProbeBackend:
    """Build a fail-closed backend bound to one exact model configuration."""

    identity, capabilities = _validate_model_only(identity, capabilities)
    configuration_ref = _require_ref(configuration_ref, "configuration_ref")
    _require_media(
        configuration_ref,
        COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        "configuration_ref",
    )
    if (
        configuration_ref != capabilities.configuration_ref
        or type(configuration_bytes) is not bytes
        or configuration_bytes != capabilities.configuration_bytes
        or not configuration_ref.verify_bytes(configuration_bytes)
    ):
        raise DistributedProbeContractValidationError(
            "unavailable backend configuration differs from exact capabilities"
        )
    reason = expect_string(reason, "reason", maximum=512)
    signature = _model_only_signature(identity, capabilities)
    backend = object.__new__(UnavailableDistributedProbeBackend)
    seal = _UnavailableBackendSeal(
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        signature=signature,
        reason=reason,
    )
    with _BACKEND_LOCK:
        _UNAVAILABLE_BACKENDS[backend] = seal
    return backend


def _require_replay_backend(backend: object) -> _ReplayBackendSeal:
    if type(backend) is not ReplayDistributedProbeBackend:
        raise DistributedProbeContractValidationError(
            "replay backend has a substituted exact type"
        )
    with _BACKEND_LOCK:
        seal = _REPLAY_BACKENDS.get(backend)
    if seal is None:
        raise DistributedProbeContractValidationError(
            "replay backend is not an exact process-sealed factory result"
        )
    return seal


def _require_unavailable_backend(backend: object) -> _UnavailableBackendSeal:
    if type(backend) is not UnavailableDistributedProbeBackend:
        raise DistributedProbeContractValidationError(
            "unavailable backend has a substituted exact type"
        )
    with _BACKEND_LOCK:
        seal = _UNAVAILABLE_BACKENDS.get(backend)
    if seal is None:
        raise DistributedProbeContractValidationError(
            "unavailable backend is not an exact process-sealed factory result"
        )
    identity, capabilities = _validate_model_only(seal.identity, seal.capabilities)
    if _model_only_signature(identity, capabilities) != seal.signature:
        raise DistributedProbeContractValidationError(
            "unavailable distributed backend model binding was mutated"
        )
    return seal


def _verify_replay_backend(seal: _ReplayBackendSeal) -> None:
    bundle = _validate_replay_bundle(
        identity=seal.identity,
        capabilities=seal.capabilities,
        discovery=seal.discovery,
        manifest=seal.manifest,
        canary_plan=seal.canary_plan,
        plan=seal.plan,
        fragments=seal.fragments,
        receipt=seal.receipt,
    )
    (
        identity,
        capabilities,
        discovery,
        manifest,
        canary_plan,
        plan,
        fragments,
        receipt,
    ) = bundle
    current = _replay_signature(
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        canary_plan=canary_plan,
        plan=plan,
        fragments=fragments,
        receipt=receipt,
    )
    expected_request = DistributedProbeReplayRequest(
        plan_ref=plan.artifact_ref,
        reconstruction_receipt_ref=receipt.artifact_ref,
    )
    if current != seal.signature or expected_request != seal.request:
        raise DistributedProbeContractValidationError(
            "sealed distributed replay bundle was mutated"
        )


def replay_distributed_reconstruction(
    backend: object,
    request: object,
) -> IndependentReconstructionReceiptArtifact:
    """Dispatch only to the exact replay or unavailable built-in backend."""

    if type(backend) is ReplayDistributedProbeBackend:
        if type(request) is not DistributedProbeReplayRequest:
            raise DistributedProbeContractValidationError(
                "replay backend requires an exact DistributedProbeReplayRequest"
            )
        return backend.reconstruct(request)
    if type(backend) is UnavailableDistributedProbeBackend:
        return backend.reconstruct(request)
    raise DistributedProbeContractValidationError(
        "arbitrary, live, framework, model, provider, GPU, or network backends are not installed"
    )


__all__ = (
    "DISTRIBUTED_RUNTIME_IDENTITY_SCHEMA",
    "NO_FULL_COPY_PROOF_SCHEMA",
    "DISTRIBUTED_PROBE_PLAN_SCHEMA",
    "DISTRIBUTED_PROBE_FRAGMENT_SCHEMA",
    "INDEPENDENT_RECONSTRUCTION_EVIDENCE_SCHEMA",
    "INDEPENDENT_RECONSTRUCTION_RECEIPT_SCHEMA",
    "DISTRIBUTED_RUNTIME_IDENTITY_MEDIA_TYPE",
    "NO_FULL_COPY_PROOF_MEDIA_TYPE",
    "DISTRIBUTED_MODEL_SHARD_MEDIA_TYPE",
    "DISTRIBUTED_PROBE_PLAN_MEDIA_TYPE",
    "DISTRIBUTED_FRAGMENT_CONTENT_MEDIA_TYPE",
    "DISTRIBUTED_PROBE_FRAGMENT_MEDIA_TYPE",
    "INDEPENDENT_RECONSTRUCTION_EVIDENCE_MEDIA_TYPE",
    "INDEPENDENT_RECONSTRUCTION_RECEIPT_MEDIA_TYPE",
    "DISTRIBUTED_RECONSTRUCTED_OUTPUT_MEDIA_TYPE",
    "TENSOR_PARALLEL",
    "PIPELINE_PARALLEL",
    "EXPERT_PARALLEL",
    "TOPOLOGY_TYPES",
    "COORDINATOR",
    "WORKER",
    "INDEPENDENT_RECONSTRUCTOR",
    "RUNTIME_ROLES",
    "COMPLETED",
    "RANK_FAILED",
    "RANK_OOM",
    "RANK_OUTCOME_STATUSES",
    "UNMEASURED",
    "NOT_LICENSED",
    "NOT_EXECUTED",
    "REPLAY_ONLY",
    "UNAVAILABLE",
    "FRAGMENT_OBJECT_VERSION",
    "DistributedProbeContractValidationError",
    "DistributedProbeBackendUnavailableError",
    "ParameterRange",
    "DistributedRankSpec",
    "FragmentSlot",
    "DistributedRankOutcome",
    "DistributedProbePlanArtifact",
    "DistributedProbeFragmentArtifact",
    "IndependentReconstructionReceiptArtifact",
    "DistributedProbeReplayRequest",
    "build_distributed_runtime_identity_body",
    "build_no_full_copy_proof_body",
    "build_distributed_probe_plan",
    "load_distributed_probe_plan",
    "replay_distributed_probe_plan",
    "build_distributed_probe_fragment",
    "load_distributed_probe_fragment",
    "replay_distributed_probe_fragment",
    "build_independent_reconstruction_evidence_body",
    "build_independent_reconstruction_receipt",
    "load_independent_reconstruction_receipt",
    "replay_independent_reconstruction_receipt",
    "ReplayDistributedProbeBackend",
    "UnavailableDistributedProbeBackend",
    "build_replay_distributed_probe_backend",
    "build_unavailable_distributed_probe_backend",
    "replay_distributed_reconstruction",
)
