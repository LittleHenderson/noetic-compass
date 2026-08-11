"""Provider-neutral, replay-only universal probe contract.

This module records exact configuration discovery, generated semantic probe
manifests, replay-fixture validation, and a bounded zero-call canary plan.  It
does not import a model loader, execute model code, inspect a live graph,
register a hook, touch a filesystem or network, or grant execution or license
authority.  A future live backend needs a different, separately authorized
contract.
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
    ACTIVATION_CAPTURE,
    CLOSED_WEIGHT,
    COMPARISON_MODEL_CAPABILITIES_MEDIA_TYPE,
    COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
    COMPARISON_MODEL_IDENTITY_MEDIA_TYPE,
    HIDDEN_STATE_OBSERVATION,
    NON_AUTHORITY,
    OPEN_WEIGHT,
    REPLAY,
    STRUCTURE_ONLY,
    SUPPORTED_WITH_EVIDENCE,
    UNAVAILABLE_BY_ACCESS_MODEL,
    UNAVAILABLE_IN_REPLAY,
    ComparisonModelCapabilitiesArtifact,
    ComparisonModelIdentityArtifact,
    replay_comparison_model_capabilities,
    replay_comparison_model_identity,
)


ARCHITECTURE_DISCOVERY_EVIDENCE_SCHEMA = (
    "cas_harness_v2.architecture_discovery_evidence.v1"
)
ARCHITECTURE_DISCOVERY_RECEIPT_SCHEMA = (
    "cas_harness_v2.architecture_discovery_receipt.v1"
)
GENERATED_PROBE_ADAPTER_MANIFEST_SCHEMA = (
    "cas_harness_v2.generated_probe_adapter_manifest.v1"
)
PROBE_VALIDATION_EVIDENCE_SCHEMA = "cas_harness_v2.probe_validation_evidence.v1"
PROBE_VALIDATION_RECEIPT_SCHEMA = "cas_harness_v2.probe_validation_receipt.v1"
UNIVERSAL_PROBE_CANARY_PLAN_SCHEMA = "cas_harness_v2.universal_probe_canary_plan.v1"

ARCHITECTURE_DISCOVERY_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.architecture-discovery-evidence-v1+json"
)
ARCHITECTURE_DISCOVERY_RECEIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.architecture-discovery-receipt-v1+json"
)
GENERATED_PROBE_ADAPTER_MANIFEST_MEDIA_TYPE = (
    "application/vnd.cas-harness.generated-probe-adapter-manifest-v1+json"
)
PROBE_VALIDATION_EVIDENCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.probe-validation-evidence-v1+json"
)
PROBE_VALIDATION_RECEIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.probe-validation-receipt-v1+json"
)
UNIVERSAL_PROBE_CANARY_PLAN_MEDIA_TYPE = (
    "application/vnd.cas-harness.universal-probe-canary-plan-v1+json"
)

DENSE_DECODER = "DENSE_DECODER"
ENCODER_DECODER = "ENCODER_DECODER"
MIXTURE_OF_EXPERTS = "MIXTURE_OF_EXPERTS"
SSM_RECURRENT = "SSM_RECURRENT"
MULTIMODAL = "MULTIMODAL"
ARCHITECTURE_FAMILIES = (
    DENSE_DECODER,
    ENCODER_DECODER,
    MIXTURE_OF_EXPERTS,
    SSM_RECURRENT,
    MULTIMODAL,
)

CONFIG_STRUCTURE_RECORDED = "CONFIG_STRUCTURE_RECORDED"
AMBIGUOUS_CONFIG_STRUCTURE = "AMBIGUOUS_CONFIG_STRUCTURE"
DISCOVERY_UNAVAILABLE_BY_ACCESS_MODEL = "UNAVAILABLE_BY_ACCESS_MODEL"
DISCOVERY_UNAVAILABLE_IN_REPLAY = "UNAVAILABLE_IN_REPLAY"
DISCOVERY_UNAVAILABLE_NOT_IMPLEMENTED = "UNAVAILABLE_NOT_IMPLEMENTED"
DISCOVERY_STATES = (
    CONFIG_STRUCTURE_RECORDED,
    AMBIGUOUS_CONFIG_STRUCTURE,
    DISCOVERY_UNAVAILABLE_BY_ACCESS_MODEL,
    DISCOVERY_UNAVAILABLE_IN_REPLAY,
    DISCOVERY_UNAVAILABLE_NOT_IMPLEMENTED,
)

RESIDUAL = "RESIDUAL"
ATTENTION = "ATTENTION"
MLP = "MLP"
ROUTER = "ROUTER"
EXPERT = "EXPERT"
RECURRENT = "RECURRENT"
MULTIMODAL_SITE = "MULTIMODAL"
SEMANTIC_PROBE_SITES = (
    RESIDUAL,
    ATTENTION,
    MLP,
    ROUTER,
    EXPERT,
    RECURRENT,
    MULTIMODAL_SITE,
)

RESIDUAL_STREAM = "RESIDUAL_STREAM"
ATTENTION_OUTPUT = "ATTENTION_OUTPUT"
MLP_OUTPUT = "MLP_OUTPUT"
ROUTER_LOGITS = "ROUTER_LOGITS"
EXPERT_OUTPUT = "EXPERT_OUTPUT"
RECURRENT_STATE = "RECURRENT_STATE"
MULTIMODAL_FUSION = "MULTIMODAL_FUSION"
SEMANTIC_PROJECTIONS = (
    RESIDUAL_STREAM,
    ATTENTION_OUTPUT,
    MLP_OUTPUT,
    ROUTER_LOGITS,
    EXPERT_OUTPUT,
    RECURRENT_STATE,
    MULTIMODAL_FUSION,
)

PRE = "PRE"
POST = "POST"
HOOK_LOCATIONS = (PRE, POST)
ALL_TOKENS = "ALL_TOKENS"
LAST_TOKEN = "LAST_TOKEN"
SELECTED_TOKEN = "SELECTED_TOKEN"
NO_TOKEN_AXIS = "NO_TOKEN_AXIS"
TOKEN_SCOPES = (ALL_TOKENS, LAST_TOKEN, SELECTED_TOKEN, NO_TOKEN_AXIS)

FLOAT16 = "FLOAT16"
BFLOAT16 = "BFLOAT16"
FLOAT32 = "FLOAT32"
INT8 = "INT8"
INT4 = "INT4"
DTYPES = (FLOAT16, BFLOAT16, FLOAT32, INT8, INT4)
NO_QUANTIZATION = "NONE"
QUANTIZED_INT8 = "INT8"
QUANTIZED_INT4 = "INT4"
QUANTIZED_NF4 = "NF4"
QUANTIZATIONS = (
    NO_QUANTIZATION,
    QUANTIZED_INT8,
    QUANTIZED_INT4,
    QUANTIZED_NF4,
)

IDENTITY_TRANSFORM = "IDENTITY"
SELECT_TOKEN_TRANSFORM = "SELECT_TOKEN"
SELECT_HEAD_TRANSFORM = "SELECT_HEAD"
ROUTER_LOGITS_TRANSFORM = "ROUTER_LOGITS"
SELECT_EXPERT_TRANSFORM = "SELECT_EXPERT"
RECURRENT_STATE_TRANSFORM = "RECURRENT_STATE"
MULTIMODAL_FUSION_TRANSFORM = "MULTIMODAL_FUSION"
TRANSFORMS = (
    IDENTITY_TRANSFORM,
    SELECT_TOKEN_TRANSFORM,
    SELECT_HEAD_TRANSFORM,
    ROUTER_LOGITS_TRANSFORM,
    SELECT_EXPERT_TRANSFORM,
    RECURRENT_STATE_TRANSFORM,
    MULTIMODAL_FUSION_TRANSFORM,
)

REPLAY_FIXTURE_MATCH = "REPLAY_FIXTURE_MATCH"
AMBIGUOUS_VALIDATION = "AMBIGUOUS"
VALIDATION_UNAVAILABLE_NOT_IMPLEMENTED = "UNAVAILABLE_NOT_IMPLEMENTED"
VALIDATION_STATES = (
    REPLAY_FIXTURE_MATCH,
    AMBIGUOUS_VALIDATION,
    VALIDATION_UNAVAILABLE_NOT_IMPLEMENTED,
)

UNMEASURED = "UNMEASURED"
CAPABILITY_UNAVAILABLE_BY_ACCESS_MODEL = "UNAVAILABLE_BY_ACCESS_MODEL"
CAPABILITY_UNAVAILABLE_IN_REPLAY = "UNAVAILABLE_IN_REPLAY"
MODEL_PROBE_CAPABILITY_STATES = (
    UNMEASURED,
    CAPABILITY_UNAVAILABLE_BY_ACCESS_MODEL,
    CAPABILITY_UNAVAILABLE_IN_REPLAY,
)

NOT_LICENSED = "NOT_LICENSED"
NOT_EXECUTED = "NOT_EXECUTED"
REPLAY_ONLY = "REPLAY_ONLY"
UNAVAILABLE_BACKEND = "UNAVAILABLE"

_STATUS = {
    "scope": STRUCTURE_ONLY,
    "authority": NON_AUTHORITY,
    "license": NOT_LICENSED,
}
_BOUNDARY = {
    "execution": NOT_EXECUTED,
    "live_loader_calls": 0,
    "model_calls": 0,
    "provider_calls": 0,
    "network_calls": 0,
    "filesystem_calls": 0,
    "hook_registrations": 0,
    "torch_calls": 0,
    "spend_microusd": 0,
    "remote_code": "FORBIDDEN",
    "execution_authority": "NOT_GRANTED",
}
_CANARY_CHECKS = (
    "NONEMPTY_CAPTURE",
    "SENTINEL_ROUNDTRIP",
    "EXACT_SHAPE_DTYPE_QUANTIZATION",
    "ZERO_CONTROL_NO_EFFECT",
    "SHAM_CONTROL_NO_EFFECT",
)
_SITE_PROJECTION = {
    RESIDUAL: RESIDUAL_STREAM,
    ATTENTION: ATTENTION_OUTPUT,
    MLP: MLP_OUTPUT,
    ROUTER: ROUTER_LOGITS,
    EXPERT: EXPERT_OUTPUT,
    RECURRENT: RECURRENT_STATE,
    MULTIMODAL_SITE: MULTIMODAL_FUSION,
}
_SITE_TRANSFORMS = {
    RESIDUAL: {IDENTITY_TRANSFORM, SELECT_TOKEN_TRANSFORM},
    ATTENTION: {SELECT_HEAD_TRANSFORM, SELECT_TOKEN_TRANSFORM},
    MLP: {IDENTITY_TRANSFORM, SELECT_TOKEN_TRANSFORM},
    ROUTER: {ROUTER_LOGITS_TRANSFORM},
    EXPERT: {SELECT_EXPERT_TRANSFORM},
    RECURRENT: {RECURRENT_STATE_TRANSFORM},
    MULTIMODAL_SITE: {MULTIMODAL_FUSION_TRANSFORM},
}
_FAMILY_REQUIRED_SITES = {
    DENSE_DECODER: {RESIDUAL, ATTENTION, MLP},
    ENCODER_DECODER: {RESIDUAL, ATTENTION, MLP},
    MIXTURE_OF_EXPERTS: {RESIDUAL, ATTENTION, MLP, ROUTER, EXPERT},
    SSM_RECURRENT: {RESIDUAL, RECURRENT},
    MULTIMODAL: {RESIDUAL, ATTENTION, MLP, MULTIMODAL_SITE},
}
_FAMILY_CONFIG_TOKENS = {
    DENSE_DECODER: {
        "hidden_size", "num_hidden_layers", "num_attention_heads", "intermediate_size"
    },
    ENCODER_DECODER: {
        "encoder_layers", "decoder_layers", "d_model",
        "encoder_attention_heads", "decoder_attention_heads",
    },
    MIXTURE_OF_EXPERTS: {
        "hidden_size", "num_hidden_layers", "num_experts", "num_experts_per_tok"
    },
    SSM_RECURRENT: {"hidden_size", "num_hidden_layers", "state_size", "conv_kernel"},
    MULTIMODAL: {
        "hidden_size", "vision_hidden_size", "text_hidden_size", "projector_type"
    },
}
_FORBIDDEN_INFERENCE_TOKENS = {
    "model_name", "model_id", "model_type", "parameter_count", "parameters",
    "num_parameters", "parameter_size", "size_label",
}
_NATIVE_PATH_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+))*$"
)
_ADAPTER_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*-v[1-9][0-9]*(?:\.[0-9]+){0,2}$")


class UniversalProbeContractValidationError(SchemaValidationError):
    """One exact universal-probe contract value failed closed."""


class UniversalProbeBackendUnavailableError(RuntimeError):
    """The universal-probe backend is deliberately unavailable."""


@dataclass(frozen=True, slots=True)
class ProbeSiteSpec:
    site_id: str
    semantic_site: str
    semantic_projection: str
    native_path: str
    hook_location: str
    layer_index: int
    token_scope: str
    head_index: int | None
    expert_index: int | None
    owning_rank: int
    shape: tuple[int, ...]
    dtype: str
    quantization: str
    transform: str
    adapter_version: str

    def __post_init__(self) -> None:
        _validate_site(self, "ProbeSiteSpec")


@dataclass(frozen=True, slots=True)
class ProbeValidationResult:
    site_id: str
    validation_state: str
    observed_native_path: str | None
    observed_semantic_projection: str | None
    observed_hook_location: str | None
    observed_layer_index: int | None
    observed_token_scope: str | None
    observed_head_index: int | None
    observed_expert_index: int | None
    observed_owning_rank: int | None
    observed_shape: tuple[int, ...] | None
    observed_dtype: str | None
    observed_quantization: str | None
    observed_transform: str | None
    hook_registration_count: int
    nonempty_capture: bool
    sentinel_roundtrip: bool
    zero_control_unchanged: bool
    sham_control_unchanged: bool
    evidence_ref: ArtifactRef | None
    evidence_bytes: bytes | None
    ambiguity_reason: str | None


@dataclass(frozen=True, slots=True)
class ArchitectureDiscoveryReceiptArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    discovery_id: str
    identity_ref: ArtifactRef
    capabilities_ref: ArtifactRef
    configuration_ref: ArtifactRef
    configuration_bytes: bytes
    discovery_state: str
    architecture_family: str | None
    candidate_families: tuple[str, ...]
    observed_config_paths: tuple[str, ...]
    evidence_ref: ArtifactRef
    evidence_bytes: bytes
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.discovery_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=ARCHITECTURE_DISCOVERY_RECEIPT_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class GeneratedProbeAdapterManifestArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    manifest_id: str
    identity_ref: ArtifactRef
    capabilities_ref: ArtifactRef
    configuration_ref: ArtifactRef
    discovery_ref: ArtifactRef
    architecture_family: str
    adapter_version: str
    sites: tuple[ProbeSiteSpec, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.manifest_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=GENERATED_PROBE_ADAPTER_MANIFEST_MEDIA_TYPE,
        )

    def site(self, site_id: str) -> ProbeSiteSpec:
        site_id = expect_machine_id(site_id, "site_id")
        matches = tuple(item for item in self.sites if item.site_id == site_id)
        if len(matches) != 1:
            raise UniversalProbeContractValidationError(
                "site_id must resolve exactly one generated probe site"
            )
        return matches[0]


@dataclass(frozen=True, slots=True)
class ProbeValidationReceiptArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    validation_id: str
    identity_ref: ArtifactRef
    capabilities_ref: ArtifactRef
    configuration_ref: ArtifactRef
    discovery_ref: ArtifactRef
    manifest_ref: ArtifactRef
    model_capability_state: str
    results: tuple[ProbeValidationResult, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.validation_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=PROBE_VALIDATION_RECEIPT_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class UniversalProbeCanaryPlanArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    plan_id: str
    identity_ref: ArtifactRef
    capabilities_ref: ArtifactRef
    configuration_ref: ArtifactRef
    discovery_ref: ArtifactRef
    manifest_ref: ArtifactRef
    max_canaries: int
    checks: tuple[str, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.plan_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=UNIVERSAL_PROBE_CANARY_PLAN_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class UniversalProbeReplayRequest:
    identity_ref: ArtifactRef
    capabilities_ref: ArtifactRef
    configuration_ref: ArtifactRef
    discovery_ref: ArtifactRef
    manifest_ref: ArtifactRef
    validation_ref: ArtifactRef
    canary_plan_ref: ArtifactRef

    def __post_init__(self) -> None:
        refs = (
            self.identity_ref, self.capabilities_ref, self.configuration_ref,
            self.discovery_ref, self.manifest_ref, self.validation_ref,
            self.canary_plan_ref,
        )
        for index, reference in enumerate(refs):
            _require_ref(reference, f"UniversalProbeReplayRequest[{index}]")
        _require_media(self.identity_ref, COMPARISON_MODEL_IDENTITY_MEDIA_TYPE, "identity_ref")
        _require_media(
            self.capabilities_ref, COMPARISON_MODEL_CAPABILITIES_MEDIA_TYPE,
            "capabilities_ref",
        )
        _require_media(
            self.configuration_ref, COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
            "configuration_ref",
        )
        _require_media(
            self.discovery_ref, ARCHITECTURE_DISCOVERY_RECEIPT_MEDIA_TYPE,
            "discovery_ref",
        )
        _require_media(
            self.manifest_ref, GENERATED_PROBE_ADAPTER_MANIFEST_MEDIA_TYPE,
            "manifest_ref",
        )
        _require_media(
            self.validation_ref, PROBE_VALIDATION_RECEIPT_MEDIA_TYPE,
            "validation_ref",
        )
        _require_media(
            self.canary_plan_ref, UNIVERSAL_PROBE_CANARY_PLAN_MEDIA_TYPE,
            "canary_plan_ref",
        )
        _unique_ref_closure(refs, "UniversalProbeReplayRequest")


def _ref_value(reference: ArtifactRef) -> dict[str, Any]:
    reference = _require_ref(reference, "artifact_ref")
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _require_ref(value: Any, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise UniversalProbeContractValidationError(
            f"{path} must be an exact ArtifactRef"
        )
    try:
        ArtifactRef(
            artifact_id=value.artifact_id,
            sha256=value.sha256,
            byte_length=value.byte_length,
            media_type=value.media_type,
        )
    except (AttributeError, TypeError, ValueError, SchemaValidationError) as exc:
        raise UniversalProbeContractValidationError(
            f"{path} is a forged ArtifactRef: {exc}"
        ) from exc
    return value


def _require_media(reference: ArtifactRef, expected: str, path: str) -> None:
    if reference.media_type != expected:
        raise UniversalProbeContractValidationError(
            f"{path} must use media type {expected}"
        )


def _canonical_object(raw: Any, path: str) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
        if canonical_json_bytes(value) != snapshot:
            raise UniversalProbeContractValidationError(
                f"{path} must be canonical JSON"
            )
        return snapshot, value
    except UniversalProbeContractValidationError:
        raise
    except (TypeError, ValueError) as exc:
        raise UniversalProbeContractValidationError(f"{path}: {exc}") from exc


def _require_status_boundary(value: dict[str, Any]) -> None:
    status = expect_object(value["status"], "$.status")
    expect_keys(status, required=_STATUS, path="$.status")
    if any(
        type(status[name]) is not type(expected) or status[name] != expected
        for name, expected in _STATUS.items()
    ):
        raise UniversalProbeContractValidationError(
            "probe artifacts remain STRUCTURE_ONLY/NON_AUTHORITY/NOT_LICENSED"
        )
    boundary = expect_object(value["boundary"], "$.boundary")
    expect_keys(boundary, required=_BOUNDARY, path="$.boundary")
    if any(
        type(boundary[name]) is not type(expected) or boundary[name] != expected
        for name, expected in _BOUNDARY.items()
    ):
        raise UniversalProbeContractValidationError(
            "probe artifacts must retain the exact zero-call boundary"
        )


def _model_binding(identity: ComparisonModelIdentityArtifact) -> dict[str, Any]:
    return {
        "identity_ref": _ref_value(identity.artifact_ref),
        "access_kind": identity.access_kind,
        "provider": identity.provider,
        "model_id": identity.model_id,
        "revision": identity.revision,
    }


def _require_model_binding(value: Any, identity: ComparisonModelIdentityArtifact, path: str) -> None:
    binding = expect_object(value, path)
    expect_keys(
        binding,
        required={"identity_ref", "access_kind", "provider", "model_id", "revision"},
        path=path,
    )
    if binding != _model_binding(identity):
        raise UniversalProbeContractValidationError(
            f"{path} differs from the exact model/revision/access binding"
        )


def _validate_model(
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> tuple[ComparisonModelIdentityArtifact, ComparisonModelCapabilitiesArtifact]:
    identity = replay_comparison_model_identity(identity)
    capabilities = replay_comparison_model_capabilities(capabilities, identity=identity)
    if capabilities.identity_ref != identity.artifact_ref:
        raise UniversalProbeContractValidationError(
            "capabilities differ from the exact model identity"
        )
    if (
        capabilities.access_kind != identity.access_kind
        or capabilities.provider != identity.provider
        or capabilities.model_id != identity.model_id
        or capabilities.revision != identity.revision
    ):
        raise UniversalProbeContractValidationError(
            "capabilities differ from the exact provider/model/revision/access binding"
        )
    if identity.access_kind == CLOSED_WEIGHT:
        for name in (HIDDEN_STATE_OBSERVATION, ACTIVATION_CAPTURE):
            if capabilities.capability(name).status != UNAVAILABLE_BY_ACCESS_MODEL:
                raise UniversalProbeContractValidationError(
                    "closed-weight mechanistic capabilities must be UNAVAILABLE_BY_ACCESS_MODEL"
                )
    if identity.access_kind == REPLAY:
        for name in (HIDDEN_STATE_OBSERVATION, ACTIVATION_CAPTURE):
            if capabilities.capability(name).status != UNAVAILABLE_IN_REPLAY:
                raise UniversalProbeContractValidationError(
                    "replay mechanistic capabilities must be UNAVAILABLE_IN_REPLAY"
                )
    return identity, capabilities


def _validate_configuration(
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
) -> tuple[ArtifactRef, bytes]:
    configuration_ref = _require_ref(configuration_ref, "configuration_ref")
    _require_media(
        configuration_ref, COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        "configuration_ref",
    )
    if configuration_ref != capabilities.configuration_ref:
        raise UniversalProbeContractValidationError(
            "configuration reference differs from the exact capability binding"
        )
    if type(configuration_bytes) is not bytes or not configuration_ref.verify_bytes(
        configuration_bytes
    ):
        raise UniversalProbeContractValidationError(
            "configuration bytes differ from the exact configuration reference"
        )
    if configuration_bytes != capabilities.configuration_bytes:
        raise UniversalProbeContractValidationError(
            "configuration bytes differ from the replayed capability binding"
        )
    return configuration_ref, configuration_bytes


def _validate_native_path(value: Any, path: str) -> str:
    result = expect_string(value, path, maximum=512)
    if not _NATIVE_PATH_RE.fullmatch(result):
        raise UniversalProbeContractValidationError(
            f"{path} must be a static dotted native module path"
        )
    if any(part.startswith("__") or part.endswith("__") for part in result.split(".")):
        raise UniversalProbeContractValidationError(
            f"{path} must not request dynamic or executable lookup"
        )
    return result


def _validate_adapter_version(value: Any, path: str) -> str:
    result = expect_string(value, path, maximum=128)
    if not _ADAPTER_VERSION_RE.fullmatch(result):
        raise UniversalProbeContractValidationError(
            f"{path} must be an immutable numbered adapter version"
        )
    return result


def _validate_shape(value: Any, path: str) -> tuple[int, ...]:
    if type(value) is not tuple or not 2 <= len(value) <= 8:
        raise UniversalProbeContractValidationError(
            f"{path} must be an exact rank-2 through rank-8 tuple"
        )
    result = tuple(expect_int(item, f"{path}[{i}]", minimum=1) for i, item in enumerate(value))
    return result


def _validate_site(site: Any, path: str) -> ProbeSiteSpec:
    if type(site) is not ProbeSiteSpec:
        raise UniversalProbeContractValidationError(
            f"{path} must be an exact ProbeSiteSpec"
        )
    expect_machine_id(site.site_id, f"{path}.site_id")
    semantic = expect_enum(
        site.semantic_site, set(SEMANTIC_PROBE_SITES), f"{path}.semantic_site"
    )
    projection = expect_enum(
        site.semantic_projection, set(SEMANTIC_PROJECTIONS),
        f"{path}.semantic_projection",
    )
    if projection != _SITE_PROJECTION[semantic]:
        raise UniversalProbeContractValidationError(
            f"{path} cannot substitute a whole block or a different semantic projection"
        )
    _validate_native_path(site.native_path, f"{path}.native_path")
    expect_enum(site.hook_location, set(HOOK_LOCATIONS), f"{path}.hook_location")
    expect_int(site.layer_index, f"{path}.layer_index", minimum=0, maximum=1_000_000)
    expect_enum(site.token_scope, set(TOKEN_SCOPES), f"{path}.token_scope")
    if site.head_index is not None:
        expect_int(site.head_index, f"{path}.head_index", minimum=0, maximum=1_000_000)
    if site.expert_index is not None:
        expect_int(site.expert_index, f"{path}.expert_index", minimum=0, maximum=1_000_000)
    if semantic == ATTENTION:
        if site.head_index is None or site.expert_index is not None:
            raise UniversalProbeContractValidationError(
                f"{path} attention sites require one exact head and no expert"
            )
    elif semantic == EXPERT:
        if site.expert_index is None or site.head_index is not None:
            raise UniversalProbeContractValidationError(
                f"{path} expert sites require one exact expert and no head"
            )
    elif site.head_index is not None or site.expert_index is not None:
        raise UniversalProbeContractValidationError(
            f"{path} head/expert indices are forbidden for this semantic site"
        )
    expect_int(site.owning_rank, f"{path}.owning_rank", minimum=0, maximum=1_000_000)
    _validate_shape(site.shape, f"{path}.shape")
    dtype = expect_enum(site.dtype, set(DTYPES), f"{path}.dtype")
    quantization = expect_enum(
        site.quantization, set(QUANTIZATIONS), f"{path}.quantization"
    )
    if quantization == NO_QUANTIZATION and dtype not in {FLOAT16, BFLOAT16, FLOAT32}:
        raise UniversalProbeContractValidationError(
            f"{path} unquantized probes require a floating dtype"
        )
    if quantization == QUANTIZED_INT8 and dtype != INT8:
        raise UniversalProbeContractValidationError(
            f"{path} INT8 quantization requires INT8 dtype"
        )
    if quantization in {QUANTIZED_INT4, QUANTIZED_NF4} and dtype != INT4:
        raise UniversalProbeContractValidationError(
            f"{path} four-bit quantization requires INT4 dtype"
        )
    transform = expect_enum(site.transform, set(TRANSFORMS), f"{path}.transform")
    if transform not in _SITE_TRANSFORMS[semantic]:
        raise UniversalProbeContractValidationError(
            f"{path} transform changes the requested semantic site"
        )
    _validate_adapter_version(site.adapter_version, f"{path}.adapter_version")
    return site


def _site_value(site: ProbeSiteSpec) -> dict[str, Any]:
    _validate_site(site, "site")
    return {
        "site_id": site.site_id,
        "semantic_site": site.semantic_site,
        "semantic_projection": site.semantic_projection,
        "native_path": site.native_path,
        "hook_location": site.hook_location,
        "layer_index": site.layer_index,
        "token_scope": site.token_scope,
        "head_index": site.head_index,
        "expert_index": site.expert_index,
        "owning_rank": site.owning_rank,
        "shape": list(site.shape),
        "dtype": site.dtype,
        "quantization": site.quantization,
        "transform": site.transform,
        "adapter_version": site.adapter_version,
    }


def _parse_site(value: Any, path: str) -> ProbeSiteSpec:
    row = expect_object(value, path)
    expect_keys(
        row,
        required={
            "site_id", "semantic_site", "semantic_projection", "native_path",
            "hook_location", "layer_index", "token_scope", "head_index",
            "expert_index", "owning_rank", "shape", "dtype", "quantization",
            "transform", "adapter_version",
        },
        path=path,
    )
    shape = expect_list(row["shape"], f"{path}.shape")
    return ProbeSiteSpec(
        site_id=expect_machine_id(row["site_id"], f"{path}.site_id"),
        semantic_site=expect_enum(
            row["semantic_site"], set(SEMANTIC_PROBE_SITES), f"{path}.semantic_site"
        ),
        semantic_projection=expect_enum(
            row["semantic_projection"], set(SEMANTIC_PROJECTIONS),
            f"{path}.semantic_projection",
        ),
        native_path=_validate_native_path(row["native_path"], f"{path}.native_path"),
        hook_location=expect_enum(
            row["hook_location"], set(HOOK_LOCATIONS), f"{path}.hook_location"
        ),
        layer_index=expect_int(row["layer_index"], f"{path}.layer_index"),
        token_scope=expect_enum(
            row["token_scope"], set(TOKEN_SCOPES), f"{path}.token_scope"
        ),
        head_index=(
            None if row["head_index"] is None
            else expect_int(row["head_index"], f"{path}.head_index")
        ),
        expert_index=(
            None if row["expert_index"] is None
            else expect_int(row["expert_index"], f"{path}.expert_index")
        ),
        owning_rank=expect_int(row["owning_rank"], f"{path}.owning_rank"),
        shape=tuple(expect_int(item, f"{path}.shape[{i}]", minimum=1) for i, item in enumerate(shape)),
        dtype=expect_enum(row["dtype"], set(DTYPES), f"{path}.dtype"),
        quantization=expect_enum(
            row["quantization"], set(QUANTIZATIONS), f"{path}.quantization"
        ),
        transform=expect_enum(row["transform"], set(TRANSFORMS), f"{path}.transform"),
        adapter_version=_validate_adapter_version(
            row["adapter_version"], f"{path}.adapter_version"
        ),
    )


def _unique_ref_closure(
    refs: tuple[ArtifactRef, ...], path: str
) -> tuple[ArtifactRef, ...]:
    by_id: dict[str, ArtifactRef] = {}
    by_content: dict[tuple[str, int], ArtifactRef] = {}
    ordered: list[ArtifactRef] = []
    for index, reference in enumerate(refs):
        reference = _require_ref(reference, f"{path}[{index}]")
        prior = by_id.get(reference.artifact_id)
        if prior is not None:
            if prior != reference:
                raise UniversalProbeContractValidationError(
                    f"{path} aliases one artifact ID to different content"
                )
            continue
        content_key = (reference.sha256, reference.byte_length)
        prior_content = by_content.get(content_key)
        if prior_content is not None:
            raise UniversalProbeContractValidationError(
                f"{path} aliases one content identity under different IDs"
            )
        by_id[reference.artifact_id] = reference
        by_content[content_key] = reference
        ordered.append(reference)
    return tuple(ordered)


def _owner_closure(owner_id: str, refs: tuple[ArtifactRef, ...], path: str) -> tuple[ArtifactRef, ...]:
    closure = _unique_ref_closure(refs, path)
    if owner_id in {item.artifact_id for item in closure}:
        raise UniversalProbeContractValidationError(
            f"{path} collides with its owner artifact ID"
        )
    return closure


def _require_frozen_json(value: Any, path: str) -> None:
    if type(value) is MappingProxyType:
        for key, child in value.items():
            if type(key) is not str:
                raise UniversalProbeContractValidationError(
                    f"{path} has a non-string key"
                )
            _require_frozen_json(child, f"{path}.{key}")
        return
    if type(value) is tuple:
        for index, child in enumerate(value):
            _require_frozen_json(child, f"{path}[{index}]")
        return
    if type(value) in (str, int, bool) or value is None:
        return
    raise UniversalProbeContractValidationError(
        f"{path} must be recursively frozen canonical JSON"
    )


def _artifact_storage(value: Any, exact_type: type[Any], path: str) -> None:
    if type(value) is not exact_type:
        raise UniversalProbeContractValidationError(
            f"{path} must be an exact {exact_type.__name__}"
        )
    missing = object()
    if (
        type(getattr(value, "raw_bytes", missing)) is not bytes
        or type(getattr(value, "sha256", missing)) is not str
        or type(getattr(value, "byte_length", missing)) is not int
        or type(getattr(value, "payload", missing)) is not MappingProxyType
        or type(getattr(value, "artifact_refs", missing)) is not tuple
    ):
        raise UniversalProbeContractValidationError(
            f"{path} storage projections must remain exact immutable values"
        )
    _require_frozen_json(value.payload, f"{path}.payload")
    for index, reference in enumerate(value.artifact_refs):
        _require_ref(reference, f"{path}.artifact_refs[{index}]")


def _capability_state(identity: ComparisonModelIdentityArtifact) -> str:
    if identity.access_kind == CLOSED_WEIGHT:
        return CAPABILITY_UNAVAILABLE_BY_ACCESS_MODEL
    if identity.access_kind == REPLAY:
        return CAPABILITY_UNAVAILABLE_IN_REPLAY
    return UNMEASURED


def _ordered_families(values: tuple[str, ...], path: str) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise UniversalProbeContractValidationError(f"{path} must be an exact tuple")
    result = tuple(
        expect_enum(item, set(ARCHITECTURE_FAMILIES), f"{path}[{index}]")
        for index, item in enumerate(values)
    )
    expected = tuple(item for item in ARCHITECTURE_FAMILIES if item in set(result))
    if len(result) != len(set(result)) or result != expected:
        raise UniversalProbeContractValidationError(
            f"{path} must be unique and use the fixed architecture-family order"
        )
    return result


def _config_paths(values: tuple[str, ...], path: str) -> tuple[str, ...]:
    if type(values) is not tuple:
        raise UniversalProbeContractValidationError(f"{path} must be an exact tuple")
    result: list[str] = []
    for index, value in enumerate(values):
        item = _validate_native_path(value, f"{path}[{index}]")
        tokens = tuple(part.lower() for part in item.split("."))
        if any(token in _FORBIDDEN_INFERENCE_TOKENS for token in tokens):
            raise UniversalProbeContractValidationError(
                f"{path} cannot infer architecture from a model name, type, size, or parameter count"
            )
        result.append(item)
    materialized = tuple(result)
    if materialized != tuple(sorted(set(materialized))):
        raise UniversalProbeContractValidationError(
            f"{path} must be unique and lexically ordered"
        )
    return materialized


def _validate_discovery_state(
    *,
    discovery_state: str,
    architecture_family: str | None,
    candidate_families: tuple[str, ...],
    observed_config_paths: tuple[str, ...],
) -> tuple[str, str | None, tuple[str, ...], tuple[str, ...]]:
    state = expect_enum(discovery_state, set(DISCOVERY_STATES), "discovery_state")
    candidates = _ordered_families(candidate_families, "candidate_families")
    paths = _config_paths(observed_config_paths, "observed_config_paths")
    if architecture_family is not None:
        family = expect_enum(
            architecture_family, set(ARCHITECTURE_FAMILIES), "architecture_family"
        )
    else:
        family = None
    if state == CONFIG_STRUCTURE_RECORDED:
        if family is None or candidates or not paths:
            raise UniversalProbeContractValidationError(
                "recorded config structure requires one family, paths, and no candidates"
            )
        terminal_tokens = {item.rsplit(".", 1)[-1].lower() for item in paths}
        missing = _FAMILY_CONFIG_TOKENS[family] - terminal_tokens
        if missing:
            raise UniversalProbeContractValidationError(
                "recorded config structure lacks required structural fields: "
                f"{sorted(missing)}"
            )
    elif state == AMBIGUOUS_CONFIG_STRUCTURE:
        if family is not None or len(candidates) < 2 or not paths:
            raise UniversalProbeContractValidationError(
                "ambiguous config structure requires at least two ordered candidates and paths"
            )
    elif family is not None or candidates or paths:
        raise UniversalProbeContractValidationError(
            "unavailable config discovery cannot claim a family, candidates, or observed paths"
        )
    return state, family, candidates, paths


def build_architecture_discovery_evidence_body(
    *,
    evidence_id: str,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    discovery_state: str,
    architecture_family: str | None,
    candidate_families: tuple[str, ...],
    observed_config_paths: tuple[str, ...],
) -> bytes:
    """Build config-only discovery evidence with no model-name inference field."""

    identity = replay_comparison_model_identity(identity)
    configuration_ref = _require_ref(configuration_ref, "configuration_ref")
    _require_media(
        configuration_ref, COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        "configuration_ref",
    )
    state, family, candidates, paths = _validate_discovery_state(
        discovery_state=discovery_state,
        architecture_family=architecture_family,
        candidate_families=candidate_families,
        observed_config_paths=observed_config_paths,
    )
    return canonical_json_bytes(
        {
            "schema": ARCHITECTURE_DISCOVERY_EVIDENCE_SCHEMA,
            "evidence_id": expect_machine_id(evidence_id, "evidence_id"),
            "model_identity": _model_binding(identity),
            "configuration_ref": _ref_value(configuration_ref),
            "discovery_basis": "CONFIGURATION_ARTIFACT_ONLY",
            "discovery_state": state,
            "architecture_family": family,
            "candidate_families": list(candidates),
            "observed_config_paths": list(paths),
            "status": dict(_STATUS),
            "boundary": dict(_BOUNDARY),
        }
    )


def _validate_discovery_evidence(
    raw: Any,
    evidence_ref: ArtifactRef,
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    discovery_state: str,
    architecture_family: str | None,
    candidate_families: tuple[str, ...],
    observed_config_paths: tuple[str, ...],
) -> bytes:
    evidence_ref = _require_ref(evidence_ref, "evidence_ref")
    _require_media(
        evidence_ref, ARCHITECTURE_DISCOVERY_EVIDENCE_MEDIA_TYPE, "evidence_ref"
    )
    if type(raw) is not bytes or not evidence_ref.verify_bytes(raw):
        raise UniversalProbeContractValidationError(
            "discovery evidence bytes differ from the exact evidence reference"
        )
    snapshot, value = _canonical_object(raw, "architecture discovery evidence")
    expect_keys(
        value,
        required={
            "schema", "evidence_id", "model_identity", "configuration_ref",
            "discovery_basis", "discovery_state", "architecture_family",
            "candidate_families", "observed_config_paths", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != ARCHITECTURE_DISCOVERY_EVIDENCE_SCHEMA:
        raise UniversalProbeContractValidationError("discovery evidence schema drifted")
    if expect_machine_id(value["evidence_id"], "$.evidence_id") != evidence_ref.artifact_id:
        raise UniversalProbeContractValidationError(
            "discovery evidence ID differs from its reference"
        )
    _require_model_binding(value["model_identity"], identity, "$.model_identity")
    if parse_artifact_ref(value["configuration_ref"], "$.configuration_ref") != configuration_ref:
        raise UniversalProbeContractValidationError(
            "discovery evidence differs from the exact configuration"
        )
    if value["discovery_basis"] != "CONFIGURATION_ARTIFACT_ONLY":
        raise UniversalProbeContractValidationError(
            "architecture discovery evidence must remain config-only"
        )
    raw_candidates = expect_list(
        value["candidate_families"], "$.candidate_families", nonempty=False
    )
    raw_paths = expect_list(
        value["observed_config_paths"], "$.observed_config_paths", nonempty=False
    )
    parsed = _validate_discovery_state(
        discovery_state=value["discovery_state"],
        architecture_family=value["architecture_family"],
        candidate_families=tuple(raw_candidates),
        observed_config_paths=tuple(raw_paths),
    )
    if parsed != (
        discovery_state, architecture_family, candidate_families, observed_config_paths
    ):
        raise UniversalProbeContractValidationError(
            "discovery evidence differs from the caller-bound discovery state"
        )
    _require_status_boundary(value)
    return snapshot


def _discovery_value(
    *,
    discovery_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    discovery_state: str,
    architecture_family: str | None,
    candidate_families: tuple[str, ...],
    observed_config_paths: tuple[str, ...],
    evidence_ref: ArtifactRef,
) -> dict[str, Any]:
    return {
        "schema": ARCHITECTURE_DISCOVERY_RECEIPT_SCHEMA,
        "discovery_id": discovery_id,
        "model_identity": _model_binding(identity),
        "capabilities_ref": _ref_value(capabilities.artifact_ref),
        "configuration_ref": _ref_value(configuration_ref),
        "discovery_method": "CONFIG_ONLY_NO_CODE_EXECUTION",
        "discovery_state": discovery_state,
        "architecture_family": architecture_family,
        "candidate_families": list(candidate_families),
        "observed_config_paths": list(observed_config_paths),
        "evidence_ref": _ref_value(evidence_ref),
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_architecture_discovery_receipt(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    evidence_bytes: bytes,
) -> ArchitectureDiscoveryReceiptArtifact:
    identity, capabilities = _validate_model(identity, capabilities)
    configuration_ref, configuration_bytes = _validate_configuration(
        capabilities, configuration_ref, configuration_bytes
    )
    snapshot, value = _canonical_object(raw, "architecture discovery receipt")
    expect_keys(
        value,
        required={
            "schema", "discovery_id", "model_identity", "capabilities_ref",
            "configuration_ref", "discovery_method", "discovery_state",
            "architecture_family", "candidate_families", "observed_config_paths",
            "evidence_ref", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != ARCHITECTURE_DISCOVERY_RECEIPT_SCHEMA:
        raise UniversalProbeContractValidationError("discovery receipt schema drifted")
    discovery_id = expect_machine_id(value["discovery_id"], "$.discovery_id")
    _require_model_binding(value["model_identity"], identity, "$.model_identity")
    if parse_artifact_ref(value["capabilities_ref"], "$.capabilities_ref") != capabilities.artifact_ref:
        raise UniversalProbeContractValidationError(
            "discovery receipt differs from exact capabilities"
        )
    if parse_artifact_ref(value["configuration_ref"], "$.configuration_ref") != configuration_ref:
        raise UniversalProbeContractValidationError(
            "discovery receipt differs from exact configuration"
        )
    if value["discovery_method"] != "CONFIG_ONLY_NO_CODE_EXECUTION":
        raise UniversalProbeContractValidationError(
            "discovery receipt must remain config-only without code execution"
        )
    candidates_value = expect_list(
        value["candidate_families"], "$.candidate_families", nonempty=False
    )
    paths_value = expect_list(
        value["observed_config_paths"], "$.observed_config_paths", nonempty=False
    )
    state, family, candidates, paths = _validate_discovery_state(
        discovery_state=value["discovery_state"],
        architecture_family=value["architecture_family"],
        candidate_families=tuple(candidates_value),
        observed_config_paths=tuple(paths_value),
    )
    evidence_ref = parse_artifact_ref(value["evidence_ref"], "$.evidence_ref")
    evidence_bytes = _validate_discovery_evidence(
        evidence_bytes,
        evidence_ref,
        identity=identity,
        configuration_ref=configuration_ref,
        discovery_state=state,
        architecture_family=family,
        candidate_families=candidates,
        observed_config_paths=paths,
    )
    _require_status_boundary(value)
    refs = _owner_closure(
        discovery_id,
        (
            identity.artifact_ref, *identity.artifact_refs,
            capabilities.artifact_ref, *capabilities.artifact_refs,
            configuration_ref, evidence_ref,
        ),
        "discovery artifact closure",
    )
    return ArchitectureDiscoveryReceiptArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        discovery_id=discovery_id,
        identity_ref=identity.artifact_ref,
        capabilities_ref=capabilities.artifact_ref,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        discovery_state=state,
        architecture_family=family,
        candidate_families=candidates,
        observed_config_paths=paths,
        evidence_ref=evidence_ref,
        evidence_bytes=evidence_bytes,
        payload=freeze_json(value),
        artifact_refs=refs,
    )


def build_architecture_discovery_receipt(
    *,
    discovery_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    discovery_state: str,
    architecture_family: str | None,
    candidate_families: tuple[str, ...],
    observed_config_paths: tuple[str, ...],
    evidence_ref: ArtifactRef,
    evidence_bytes: bytes,
) -> ArchitectureDiscoveryReceiptArtifact:
    """Build one exact config-only architecture discovery receipt."""

    discovery_id = expect_machine_id(discovery_id, "discovery_id")
    identity, capabilities = _validate_model(identity, capabilities)
    configuration_ref, configuration_bytes = _validate_configuration(
        capabilities, configuration_ref, configuration_bytes
    )
    state, family, candidates, paths = _validate_discovery_state(
        discovery_state=discovery_state,
        architecture_family=architecture_family,
        candidate_families=candidate_families,
        observed_config_paths=observed_config_paths,
    )
    _validate_discovery_evidence(
        evidence_bytes,
        evidence_ref,
        identity=identity,
        configuration_ref=configuration_ref,
        discovery_state=state,
        architecture_family=family,
        candidate_families=candidates,
        observed_config_paths=paths,
    )
    raw = canonical_json_bytes(
        _discovery_value(
            discovery_id=discovery_id,
            identity=identity,
            capabilities=capabilities,
            configuration_ref=configuration_ref,
            discovery_state=state,
            architecture_family=family,
            candidate_families=candidates,
            observed_config_paths=paths,
            evidence_ref=evidence_ref,
        )
    )
    return _load_architecture_discovery_receipt(
        raw,
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        evidence_bytes=evidence_bytes,
    )


def load_architecture_discovery_receipt(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    evidence_bytes: bytes,
) -> ArchitectureDiscoveryReceiptArtifact:
    return _load_architecture_discovery_receipt(
        raw,
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        configuration_bytes=configuration_bytes,
        evidence_bytes=evidence_bytes,
    )


def replay_architecture_discovery_receipt(
    receipt: ArchitectureDiscoveryReceiptArtifact,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> ArchitectureDiscoveryReceiptArtifact:
    _artifact_storage(receipt, ArchitectureDiscoveryReceiptArtifact, "receipt")
    replayed = _load_architecture_discovery_receipt(
        receipt.raw_bytes,
        identity=identity,
        capabilities=capabilities,
        configuration_ref=receipt.configuration_ref,
        configuration_bytes=receipt.configuration_bytes,
        evidence_bytes=receipt.evidence_bytes,
    )
    if replayed != receipt:
        raise UniversalProbeContractValidationError(
            "architecture discovery receipt differs from exact-byte replay"
        )
    return replayed


def _validate_discovery_dependency(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
) -> ArchitectureDiscoveryReceiptArtifact:
    replayed = replay_architecture_discovery_receipt(
        discovery, identity=identity, capabilities=capabilities
    )
    if (
        replayed.identity_ref != identity.artifact_ref
        or replayed.capabilities_ref != capabilities.artifact_ref
        or replayed.configuration_ref != capabilities.configuration_ref
    ):
        raise UniversalProbeContractValidationError(
            "architecture discovery differs from exact model/configuration/capabilities"
        )
    return replayed


def _validate_manifest_sites(
    *,
    sites: tuple[ProbeSiteSpec, ...],
    architecture_family: str,
    adapter_version: str,
) -> tuple[ProbeSiteSpec, ...]:
    if type(sites) is not tuple or not sites or len(sites) > 512:
        raise UniversalProbeContractValidationError(
            "sites must be a non-empty exact tuple with at most 512 entries"
        )
    family = expect_enum(
        architecture_family, set(ARCHITECTURE_FAMILIES), "architecture_family"
    )
    version = _validate_adapter_version(adapter_version, "adapter_version")
    allowed_sites = _FAMILY_REQUIRED_SITES[family]
    site_ids: set[str] = set()
    hook_signatures: set[tuple[Any, ...]] = set()
    semantics: set[str] = set()
    validated: list[ProbeSiteSpec] = []
    for index, site in enumerate(sites):
        site = _validate_site(site, f"sites[{index}]")
        if site.adapter_version != version:
            raise UniversalProbeContractValidationError(
                "every probe site must use the exact manifest adapter version"
            )
        if site.semantic_site not in allowed_sites:
            raise UniversalProbeContractValidationError(
                "probe site is incompatible with the config-recorded architecture family"
            )
        if site.site_id in site_ids:
            raise UniversalProbeContractValidationError(
                "generated adapter manifest contains a duplicate site_id"
            )
        signature = (
            site.native_path,
            site.hook_location,
            site.layer_index,
            site.token_scope,
            site.head_index,
            site.expert_index,
            site.owning_rank,
        )
        if signature in hook_signatures:
            raise UniversalProbeContractValidationError(
                "generated adapter manifest contains a duplicate hook"
            )
        site_ids.add(site.site_id)
        hook_signatures.add(signature)
        semantics.add(site.semantic_site)
        validated.append(site)
    missing = allowed_sites - semantics
    if missing:
        raise UniversalProbeContractValidationError(
            "generated adapter manifest is missing required semantic projections: "
            f"{sorted(missing)}"
        )
    return tuple(validated)


def _manifest_value(
    *,
    manifest_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    adapter_version: str,
    sites: tuple[ProbeSiteSpec, ...],
) -> dict[str, Any]:
    return {
        "schema": GENERATED_PROBE_ADAPTER_MANIFEST_SCHEMA,
        "manifest_id": manifest_id,
        "model_identity": _model_binding(identity),
        "capabilities_ref": _ref_value(capabilities.artifact_ref),
        "configuration_ref": _ref_value(capabilities.configuration_ref),
        "discovery_ref": _ref_value(discovery.artifact_ref),
        "architecture_family": discovery.architecture_family,
        "adapter_version": adapter_version,
        "generation_basis": "CONFIG_ONLY_STATIC_PATH_MANIFEST",
        "remote_code_policy": "REJECT",
        "remote_code_required": False,
        "sites": [_site_value(site) for site in sites],
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_generated_probe_adapter_manifest(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
) -> GeneratedProbeAdapterManifestArtifact:
    identity, capabilities = _validate_model(identity, capabilities)
    discovery = _validate_discovery_dependency(
        identity=identity, capabilities=capabilities, discovery=discovery
    )
    if identity.access_kind != OPEN_WEIGHT:
        raise UniversalProbeContractValidationError(
            "generated mechanistic probe manifests are available only for OPEN_WEIGHT"
        )
    for capability_name in (HIDDEN_STATE_OBSERVATION, ACTIVATION_CAPTURE):
        if capabilities.capability(capability_name).status != SUPPORTED_WITH_EVIDENCE:
            raise UniversalProbeContractValidationError(
                "generated probe manifests require measured capability evidence"
            )
    if (
        discovery.discovery_state != CONFIG_STRUCTURE_RECORDED
        or discovery.architecture_family is None
    ):
        raise UniversalProbeContractValidationError(
            "generated adapter manifests require one unambiguous config structure"
        )
    snapshot, value = _canonical_object(raw, "generated probe adapter manifest")
    expect_keys(
        value,
        required={
            "schema", "manifest_id", "model_identity", "capabilities_ref",
            "configuration_ref", "discovery_ref", "architecture_family",
            "adapter_version", "generation_basis", "remote_code_policy",
            "remote_code_required", "sites", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != GENERATED_PROBE_ADAPTER_MANIFEST_SCHEMA:
        raise UniversalProbeContractValidationError("probe adapter manifest schema drifted")
    manifest_id = expect_machine_id(value["manifest_id"], "$.manifest_id")
    _require_model_binding(value["model_identity"], identity, "$.model_identity")
    if parse_artifact_ref(value["capabilities_ref"], "$.capabilities_ref") != capabilities.artifact_ref:
        raise UniversalProbeContractValidationError(
            "probe manifest differs from exact model capabilities"
        )
    if parse_artifact_ref(value["configuration_ref"], "$.configuration_ref") != capabilities.configuration_ref:
        raise UniversalProbeContractValidationError(
            "probe manifest differs from exact model configuration"
        )
    if parse_artifact_ref(value["discovery_ref"], "$.discovery_ref") != discovery.artifact_ref:
        raise UniversalProbeContractValidationError(
            "probe manifest differs from config-only discovery"
        )
    family = expect_enum(
        value["architecture_family"], set(ARCHITECTURE_FAMILIES),
        "$.architecture_family",
    )
    if family != discovery.architecture_family:
        raise UniversalProbeContractValidationError(
            "probe manifest architecture family differs from discovery"
        )
    adapter_version = _validate_adapter_version(
        value["adapter_version"], "$.adapter_version"
    )
    if value["generation_basis"] != "CONFIG_ONLY_STATIC_PATH_MANIFEST":
        raise UniversalProbeContractValidationError(
            "probe manifest generation basis must remain config-only"
        )
    if value["remote_code_policy"] != "REJECT" or expect_bool(
        value["remote_code_required"], "$.remote_code_required"
    ):
        raise UniversalProbeContractValidationError(
            "probe manifest must reject remote code"
        )
    raw_sites = expect_list(value["sites"], "$.sites")
    sites = _validate_manifest_sites(
        sites=tuple(_parse_site(item, f"$.sites[{index}]") for index, item in enumerate(raw_sites)),
        architecture_family=family,
        adapter_version=adapter_version,
    )
    _require_status_boundary(value)
    refs = _owner_closure(
        manifest_id,
        (
            identity.artifact_ref, *identity.artifact_refs,
            capabilities.artifact_ref, *capabilities.artifact_refs,
            discovery.artifact_ref, *discovery.artifact_refs,
        ),
        "manifest artifact closure",
    )
    return GeneratedProbeAdapterManifestArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        manifest_id=manifest_id,
        identity_ref=identity.artifact_ref,
        capabilities_ref=capabilities.artifact_ref,
        configuration_ref=capabilities.configuration_ref,
        discovery_ref=discovery.artifact_ref,
        architecture_family=family,
        adapter_version=adapter_version,
        sites=sites,
        payload=freeze_json(value),
        artifact_refs=refs,
    )


def build_generated_probe_adapter_manifest(
    *,
    manifest_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    adapter_version: str,
    sites: tuple[ProbeSiteSpec, ...],
    remote_code_required: bool,
) -> GeneratedProbeAdapterManifestArtifact:
    """Generate a static, non-executing probe adapter manifest."""

    if type(remote_code_required) is not bool or remote_code_required:
        raise UniversalProbeContractValidationError(
            "remote-code-required adapter generation is forbidden"
        )
    manifest_id = expect_machine_id(manifest_id, "manifest_id")
    identity, capabilities = _validate_model(identity, capabilities)
    discovery = _validate_discovery_dependency(
        identity=identity, capabilities=capabilities, discovery=discovery
    )
    if discovery.architecture_family is None:
        raise UniversalProbeContractValidationError(
            "adapter generation requires an unambiguous architecture family"
        )
    adapter_version = _validate_adapter_version(adapter_version, "adapter_version")
    sites = _validate_manifest_sites(
        sites=sites,
        architecture_family=discovery.architecture_family,
        adapter_version=adapter_version,
    )
    raw = canonical_json_bytes(
        _manifest_value(
            manifest_id=manifest_id,
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            adapter_version=adapter_version,
            sites=sites,
        )
    )
    return _load_generated_probe_adapter_manifest(
        raw,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
    )


def load_generated_probe_adapter_manifest(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
) -> GeneratedProbeAdapterManifestArtifact:
    return _load_generated_probe_adapter_manifest(
        raw, identity=identity, capabilities=capabilities, discovery=discovery
    )


def replay_generated_probe_adapter_manifest(
    manifest: GeneratedProbeAdapterManifestArtifact,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
) -> GeneratedProbeAdapterManifestArtifact:
    _artifact_storage(
        manifest, GeneratedProbeAdapterManifestArtifact, "manifest"
    )
    if type(manifest.sites) is not tuple or any(
        type(item) is not ProbeSiteSpec for item in manifest.sites
    ):
        raise UniversalProbeContractValidationError(
            "manifest site projections must remain exact immutable types"
        )
    replayed = _load_generated_probe_adapter_manifest(
        manifest.raw_bytes,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
    )
    if replayed != manifest:
        raise UniversalProbeContractValidationError(
            "generated probe manifest differs from exact-byte replay"
        )
    return replayed


def probe_capability_state(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
) -> str:
    """Return only an evidence-safe state; this contract never infers support."""

    identity, _ = _validate_model(identity, capabilities)
    return _capability_state(identity)


def build_probe_validation_evidence_body(
    *,
    evidence_id: str,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    manifest_ref: ArtifactRef,
    site: ProbeSiteSpec,
) -> bytes:
    """Build exact replay-fixture evidence without claiming model support."""

    identity = replay_comparison_model_identity(identity)
    configuration_ref = _require_ref(configuration_ref, "configuration_ref")
    _require_media(
        configuration_ref, COMPARISON_MODEL_CONFIGURATION_MEDIA_TYPE,
        "configuration_ref",
    )
    manifest_ref = _require_ref(manifest_ref, "manifest_ref")
    _require_media(
        manifest_ref, GENERATED_PROBE_ADAPTER_MANIFEST_MEDIA_TYPE, "manifest_ref"
    )
    site = _validate_site(site, "site")
    return canonical_json_bytes(
        {
            "schema": PROBE_VALIDATION_EVIDENCE_SCHEMA,
            "evidence_id": expect_machine_id(evidence_id, "evidence_id"),
            "model_identity": _model_binding(identity),
            "configuration_ref": _ref_value(configuration_ref),
            "manifest_ref": _ref_value(manifest_ref),
            "validation_basis": "REPLAY_FIXTURE_ONLY",
            "observed_site": _site_value(site),
            "hook_registration_count": 1,
            "nonempty_capture": True,
            "sentinel_roundtrip": True,
            "zero_control_unchanged": True,
            "sham_control_unchanged": True,
            "model_capability_claim": UNMEASURED,
            "status": dict(_STATUS),
            "boundary": dict(_BOUNDARY),
        }
    )


def _validate_probe_evidence(
    raw: Any,
    evidence_ref: ArtifactRef,
    *,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    manifest_ref: ArtifactRef,
    site: ProbeSiteSpec,
) -> bytes:
    evidence_ref = _require_ref(evidence_ref, "probe evidence_ref")
    _require_media(
        evidence_ref, PROBE_VALIDATION_EVIDENCE_MEDIA_TYPE, "probe evidence_ref"
    )
    if type(raw) is not bytes or not evidence_ref.verify_bytes(raw):
        raise UniversalProbeContractValidationError(
            "probe validation evidence differs from its exact reference"
        )
    snapshot, value = _canonical_object(raw, "probe validation evidence")
    expect_keys(
        value,
        required={
            "schema", "evidence_id", "model_identity", "configuration_ref",
            "manifest_ref", "validation_basis", "observed_site",
            "hook_registration_count", "nonempty_capture", "sentinel_roundtrip",
            "zero_control_unchanged", "sham_control_unchanged",
            "model_capability_claim", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != PROBE_VALIDATION_EVIDENCE_SCHEMA:
        raise UniversalProbeContractValidationError("probe evidence schema drifted")
    if expect_machine_id(value["evidence_id"], "$.evidence_id") != evidence_ref.artifact_id:
        raise UniversalProbeContractValidationError(
            "probe evidence ID differs from its reference"
        )
    _require_model_binding(value["model_identity"], identity, "$.model_identity")
    if parse_artifact_ref(value["configuration_ref"], "$.configuration_ref") != configuration_ref:
        raise UniversalProbeContractValidationError(
            "probe evidence differs from the exact configuration"
        )
    if parse_artifact_ref(value["manifest_ref"], "$.manifest_ref") != manifest_ref:
        raise UniversalProbeContractValidationError(
            "probe evidence differs from the generated manifest"
        )
    if value["validation_basis"] != "REPLAY_FIXTURE_ONLY":
        raise UniversalProbeContractValidationError(
            "probe evidence must remain a replay fixture"
        )
    parsed_site = _parse_site(value["observed_site"], "$.observed_site")
    if parsed_site != site:
        raise UniversalProbeContractValidationError(
            "probe evidence shape, dtype, rank, path, or semantic projection drifted"
        )
    if expect_int(
        value["hook_registration_count"], "$.hook_registration_count", minimum=0
    ) != 1:
        raise UniversalProbeContractValidationError(
            "probe evidence requires exactly one hook registration"
        )
    for field in (
        "nonempty_capture", "sentinel_roundtrip", "zero_control_unchanged",
        "sham_control_unchanged",
    ):
        if not expect_bool(value[field], f"$.{field}"):
            raise UniversalProbeContractValidationError(
                "probe fixture evidence failed a required validation control"
            )
    if value["model_capability_claim"] != UNMEASURED:
        raise UniversalProbeContractValidationError(
            "replay fixtures cannot claim measured model capability"
        )
    _require_status_boundary(value)
    return snapshot


def _result_observation_tuple(result: ProbeValidationResult) -> tuple[Any, ...]:
    return (
        result.observed_native_path,
        result.observed_semantic_projection,
        result.observed_hook_location,
        result.observed_layer_index,
        result.observed_token_scope,
        result.observed_head_index,
        result.observed_expert_index,
        result.observed_owning_rank,
        result.observed_shape,
        result.observed_dtype,
        result.observed_quantization,
        result.observed_transform,
    )


def _site_observation_tuple(site: ProbeSiteSpec) -> tuple[Any, ...]:
    return (
        site.native_path,
        site.semantic_projection,
        site.hook_location,
        site.layer_index,
        site.token_scope,
        site.head_index,
        site.expert_index,
        site.owning_rank,
        site.shape,
        site.dtype,
        site.quantization,
        site.transform,
    )


def _validate_result(
    result: Any,
    *,
    site: ProbeSiteSpec,
    identity: ComparisonModelIdentityArtifact,
    configuration_ref: ArtifactRef,
    manifest_ref: ArtifactRef,
    path: str,
) -> ProbeValidationResult:
    if type(result) is not ProbeValidationResult:
        raise UniversalProbeContractValidationError(
            f"{path} must be an exact ProbeValidationResult"
        )
    if expect_machine_id(result.site_id, f"{path}.site_id") != site.site_id:
        raise UniversalProbeContractValidationError(
            f"{path} differs from the ordered manifest site"
        )
    state = expect_enum(
        result.validation_state, set(VALIDATION_STATES),
        f"{path}.validation_state",
    )
    expect_int(
        result.hook_registration_count, f"{path}.hook_registration_count",
        minimum=0, maximum=1,
    )
    for field in (
        result.nonempty_capture,
        result.sentinel_roundtrip,
        result.zero_control_unchanged,
        result.sham_control_unchanged,
    ):
        if type(field) is not bool:
            raise UniversalProbeContractValidationError(
                f"{path} validation controls must be exact booleans"
            )
    if state == REPLAY_FIXTURE_MATCH:
        if _result_observation_tuple(result) != _site_observation_tuple(site):
            raise UniversalProbeContractValidationError(
                f"{path} shape, dtype, rank, path, or semantic projection is wrong"
            )
        if (
            result.hook_registration_count != 1
            or not result.nonempty_capture
            or not result.sentinel_roundtrip
            or not result.zero_control_unchanged
            or not result.sham_control_unchanged
            or result.ambiguity_reason is not None
        ):
            raise UniversalProbeContractValidationError(
                f"{path} replay fixture did not pass every exact control"
            )
        if result.evidence_ref is None or result.evidence_bytes is None:
            raise UniversalProbeContractValidationError(
                f"{path} replay fixture match requires exact evidence"
            )
        evidence_bytes = _validate_probe_evidence(
            result.evidence_bytes,
            result.evidence_ref,
            identity=identity,
            configuration_ref=configuration_ref,
            manifest_ref=manifest_ref,
            site=site,
        )
        if evidence_bytes != result.evidence_bytes:
            raise UniversalProbeContractValidationError(
                f"{path} evidence bytes were not exact immutable bytes"
            )
    else:
        if any(item is not None for item in _result_observation_tuple(result)):
            raise UniversalProbeContractValidationError(
                f"{path} ambiguous/unavailable state cannot claim an observation"
            )
        if (
            result.hook_registration_count != 0
            or result.nonempty_capture
            or result.sentinel_roundtrip
            or result.zero_control_unchanged
            or result.sham_control_unchanged
            or result.evidence_ref is not None
            or result.evidence_bytes is not None
        ):
            raise UniversalProbeContractValidationError(
                f"{path} ambiguous/unavailable state cannot claim validation evidence"
            )
        expect_string(result.ambiguity_reason, f"{path}.ambiguity_reason", maximum=512)
    return result


def _result_value(result: ProbeValidationResult) -> dict[str, Any]:
    return {
        "site_id": result.site_id,
        "validation_state": result.validation_state,
        "observed_native_path": result.observed_native_path,
        "observed_semantic_projection": result.observed_semantic_projection,
        "observed_hook_location": result.observed_hook_location,
        "observed_layer_index": result.observed_layer_index,
        "observed_token_scope": result.observed_token_scope,
        "observed_head_index": result.observed_head_index,
        "observed_expert_index": result.observed_expert_index,
        "observed_owning_rank": result.observed_owning_rank,
        "observed_shape": (
            None if result.observed_shape is None else list(result.observed_shape)
        ),
        "observed_dtype": result.observed_dtype,
        "observed_quantization": result.observed_quantization,
        "observed_transform": result.observed_transform,
        "hook_registration_count": result.hook_registration_count,
        "nonempty_capture": result.nonempty_capture,
        "sentinel_roundtrip": result.sentinel_roundtrip,
        "zero_control_unchanged": result.zero_control_unchanged,
        "sham_control_unchanged": result.sham_control_unchanged,
        "evidence_ref": (
            None if result.evidence_ref is None else _ref_value(result.evidence_ref)
        ),
        "ambiguity_reason": result.ambiguity_reason,
    }


def _parse_result(
    value: Any,
    *,
    evidence_bytes: bytes | None,
    path: str,
) -> ProbeValidationResult:
    row = expect_object(value, path)
    required = {
        "site_id", "validation_state", "observed_native_path",
        "observed_semantic_projection", "observed_hook_location",
        "observed_layer_index", "observed_token_scope", "observed_head_index",
        "observed_expert_index", "observed_owning_rank", "observed_shape",
        "observed_dtype", "observed_quantization", "observed_transform",
        "hook_registration_count", "nonempty_capture", "sentinel_roundtrip",
        "zero_control_unchanged", "sham_control_unchanged", "evidence_ref",
        "ambiguity_reason",
    }
    expect_keys(row, required=required, path=path)
    shape_value = row["observed_shape"]
    shape = None
    if shape_value is not None:
        shape_rows = expect_list(shape_value, f"{path}.observed_shape")
        shape = tuple(
            expect_int(item, f"{path}.observed_shape[{index}]", minimum=1)
            for index, item in enumerate(shape_rows)
        )
    return ProbeValidationResult(
        site_id=expect_machine_id(row["site_id"], f"{path}.site_id"),
        validation_state=expect_enum(
            row["validation_state"], set(VALIDATION_STATES),
            f"{path}.validation_state",
        ),
        observed_native_path=(
            None if row["observed_native_path"] is None
            else _validate_native_path(row["observed_native_path"], f"{path}.observed_native_path")
        ),
        observed_semantic_projection=(
            None if row["observed_semantic_projection"] is None
            else expect_enum(
                row["observed_semantic_projection"], set(SEMANTIC_PROJECTIONS),
                f"{path}.observed_semantic_projection",
            )
        ),
        observed_hook_location=(
            None if row["observed_hook_location"] is None
            else expect_enum(
                row["observed_hook_location"], set(HOOK_LOCATIONS),
                f"{path}.observed_hook_location",
            )
        ),
        observed_layer_index=(
            None if row["observed_layer_index"] is None
            else expect_int(row["observed_layer_index"], f"{path}.observed_layer_index")
        ),
        observed_token_scope=(
            None if row["observed_token_scope"] is None
            else expect_enum(
                row["observed_token_scope"], set(TOKEN_SCOPES),
                f"{path}.observed_token_scope",
            )
        ),
        observed_head_index=(
            None if row["observed_head_index"] is None
            else expect_int(row["observed_head_index"], f"{path}.observed_head_index")
        ),
        observed_expert_index=(
            None if row["observed_expert_index"] is None
            else expect_int(row["observed_expert_index"], f"{path}.observed_expert_index")
        ),
        observed_owning_rank=(
            None if row["observed_owning_rank"] is None
            else expect_int(row["observed_owning_rank"], f"{path}.observed_owning_rank")
        ),
        observed_shape=shape,
        observed_dtype=(
            None if row["observed_dtype"] is None
            else expect_enum(row["observed_dtype"], set(DTYPES), f"{path}.observed_dtype")
        ),
        observed_quantization=(
            None if row["observed_quantization"] is None
            else expect_enum(
                row["observed_quantization"], set(QUANTIZATIONS),
                f"{path}.observed_quantization",
            )
        ),
        observed_transform=(
            None if row["observed_transform"] is None
            else expect_enum(row["observed_transform"], set(TRANSFORMS), f"{path}.observed_transform")
        ),
        hook_registration_count=expect_int(
            row["hook_registration_count"], f"{path}.hook_registration_count",
            maximum=1,
        ),
        nonempty_capture=expect_bool(row["nonempty_capture"], f"{path}.nonempty_capture"),
        sentinel_roundtrip=expect_bool(row["sentinel_roundtrip"], f"{path}.sentinel_roundtrip"),
        zero_control_unchanged=expect_bool(
            row["zero_control_unchanged"], f"{path}.zero_control_unchanged"
        ),
        sham_control_unchanged=expect_bool(
            row["sham_control_unchanged"], f"{path}.sham_control_unchanged"
        ),
        evidence_ref=(
            None if row["evidence_ref"] is None
            else parse_artifact_ref(row["evidence_ref"], f"{path}.evidence_ref")
        ),
        evidence_bytes=evidence_bytes,
        ambiguity_reason=(
            None if row["ambiguity_reason"] is None
            else expect_string(row["ambiguity_reason"], f"{path}.ambiguity_reason", maximum=512)
        ),
    )


def _validation_value(
    *,
    validation_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    results: tuple[ProbeValidationResult, ...],
) -> dict[str, Any]:
    return {
        "schema": PROBE_VALIDATION_RECEIPT_SCHEMA,
        "validation_id": validation_id,
        "model_identity": _model_binding(identity),
        "capabilities_ref": _ref_value(capabilities.artifact_ref),
        "configuration_ref": _ref_value(capabilities.configuration_ref),
        "discovery_ref": _ref_value(discovery.artifact_ref),
        "manifest_ref": _ref_value(manifest.artifact_ref),
        "validation_mode": "REPLAY_FIXTURES_ONLY",
        "model_probe_capability_state": _capability_state(identity),
        "results": [_result_value(item) for item in results],
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_probe_validation_receipt(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    evidence_bytes_by_site: Mapping[str, bytes | None],
) -> ProbeValidationReceiptArtifact:
    identity, capabilities = _validate_model(identity, capabilities)
    discovery = _validate_discovery_dependency(
        identity=identity, capabilities=capabilities, discovery=discovery
    )
    manifest = replay_generated_probe_adapter_manifest(
        manifest,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
    )
    if type(evidence_bytes_by_site) is not dict:
        raise UniversalProbeContractValidationError(
            "evidence_bytes_by_site must be an exact dict"
        )
    if set(evidence_bytes_by_site) != {site.site_id for site in manifest.sites}:
        raise UniversalProbeContractValidationError(
            "validation evidence byte map must contain every manifest site exactly once"
        )
    snapshot, value = _canonical_object(raw, "probe validation receipt")
    expect_keys(
        value,
        required={
            "schema", "validation_id", "model_identity", "capabilities_ref",
            "configuration_ref", "discovery_ref", "manifest_ref",
            "validation_mode", "model_probe_capability_state", "results",
            "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != PROBE_VALIDATION_RECEIPT_SCHEMA:
        raise UniversalProbeContractValidationError("validation receipt schema drifted")
    validation_id = expect_machine_id(value["validation_id"], "$.validation_id")
    _require_model_binding(value["model_identity"], identity, "$.model_identity")
    exact_refs = (
        ("capabilities_ref", capabilities.artifact_ref),
        ("configuration_ref", capabilities.configuration_ref),
        ("discovery_ref", discovery.artifact_ref),
        ("manifest_ref", manifest.artifact_ref),
    )
    for field, expected in exact_refs:
        if parse_artifact_ref(value[field], f"$.{field}") != expected:
            raise UniversalProbeContractValidationError(
                f"validation receipt {field} differs from its exact dependency"
            )
    if value["validation_mode"] != "REPLAY_FIXTURES_ONLY":
        raise UniversalProbeContractValidationError(
            "validation receipt must remain replay-fixture only"
        )
    model_state = expect_enum(
        value["model_probe_capability_state"], set(MODEL_PROBE_CAPABILITY_STATES),
        "$.model_probe_capability_state",
    )
    if model_state != _capability_state(identity):
        raise UniversalProbeContractValidationError(
            "validation receipt inferred model capability without measured evidence"
        )
    raw_results = expect_list(value["results"], "$.results")
    if len(raw_results) != len(manifest.sites):
        raise UniversalProbeContractValidationError(
            "validation receipt must contain every manifest site exactly once"
        )
    results: list[ProbeValidationResult] = []
    for index, (raw_result, site) in enumerate(
        zip(raw_results, manifest.sites, strict=True)
    ):
        result = _parse_result(
            raw_result,
            evidence_bytes=evidence_bytes_by_site[site.site_id],
            path=f"$.results[{index}]",
        )
        results.append(
            _validate_result(
                result,
                site=site,
                identity=identity,
                configuration_ref=capabilities.configuration_ref,
                manifest_ref=manifest.artifact_ref,
                path=f"$.results[{index}]",
            )
        )
    _require_status_boundary(value)
    evidence_refs = tuple(
        item.evidence_ref for item in results if item.evidence_ref is not None
    )
    refs = _owner_closure(
        validation_id,
        (
            identity.artifact_ref, *identity.artifact_refs,
            capabilities.artifact_ref, *capabilities.artifact_refs,
            discovery.artifact_ref, *discovery.artifact_refs,
            manifest.artifact_ref, *manifest.artifact_refs,
            *evidence_refs,
        ),
        "validation artifact closure",
    )
    return ProbeValidationReceiptArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        validation_id=validation_id,
        identity_ref=identity.artifact_ref,
        capabilities_ref=capabilities.artifact_ref,
        configuration_ref=capabilities.configuration_ref,
        discovery_ref=discovery.artifact_ref,
        manifest_ref=manifest.artifact_ref,
        model_capability_state=model_state,
        results=tuple(results),
        payload=freeze_json(value),
        artifact_refs=refs,
    )


def build_probe_validation_receipt(
    *,
    validation_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    results: tuple[ProbeValidationResult, ...],
) -> ProbeValidationReceiptArtifact:
    """Build a replay-fixture validation receipt without a support claim."""

    validation_id = expect_machine_id(validation_id, "validation_id")
    identity, capabilities = _validate_model(identity, capabilities)
    discovery = _validate_discovery_dependency(
        identity=identity, capabilities=capabilities, discovery=discovery
    )
    manifest = replay_generated_probe_adapter_manifest(
        manifest,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
    )
    if type(results) is not tuple or len(results) != len(manifest.sites):
        raise UniversalProbeContractValidationError(
            "results must be an exact tuple covering every manifest site"
        )
    validated = tuple(
        _validate_result(
            result,
            site=site,
            identity=identity,
            configuration_ref=capabilities.configuration_ref,
            manifest_ref=manifest.artifact_ref,
            path=f"results[{index}]",
        )
        for index, (result, site) in enumerate(zip(results, manifest.sites, strict=True))
    )
    raw = canonical_json_bytes(
        _validation_value(
            validation_id=validation_id,
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            manifest=manifest,
            results=validated,
        )
    )
    return _load_probe_validation_receipt(
        raw,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        evidence_bytes_by_site={
            item.site_id: item.evidence_bytes for item in validated
        },
    )


def load_probe_validation_receipt(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    evidence_bytes_by_site: Mapping[str, bytes | None],
) -> ProbeValidationReceiptArtifact:
    return _load_probe_validation_receipt(
        raw,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        evidence_bytes_by_site=evidence_bytes_by_site,
    )


def replay_probe_validation_receipt(
    receipt: ProbeValidationReceiptArtifact,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
) -> ProbeValidationReceiptArtifact:
    _artifact_storage(receipt, ProbeValidationReceiptArtifact, "validation receipt")
    if type(receipt.results) is not tuple or any(
        type(item) is not ProbeValidationResult for item in receipt.results
    ):
        raise UniversalProbeContractValidationError(
            "validation result projections must remain exact immutable types"
        )
    replayed = _load_probe_validation_receipt(
        receipt.raw_bytes,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        evidence_bytes_by_site={
            item.site_id: item.evidence_bytes for item in receipt.results
        },
    )
    if replayed != receipt:
        raise UniversalProbeContractValidationError(
            "probe validation receipt differs from exact-byte replay"
        )
    return replayed


def _canary_value(
    *,
    plan_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    max_canaries: int,
) -> dict[str, Any]:
    return {
        "schema": UNIVERSAL_PROBE_CANARY_PLAN_SCHEMA,
        "plan_id": plan_id,
        "model_identity": _model_binding(identity),
        "capabilities_ref": _ref_value(capabilities.artifact_ref),
        "configuration_ref": _ref_value(capabilities.configuration_ref),
        "discovery_ref": _ref_value(discovery.artifact_ref),
        "manifest_ref": _ref_value(manifest.artifact_ref),
        "checks": list(_CANARY_CHECKS),
        "max_canaries": max_canaries,
        "attempts_per_canary": 1,
        "executed_canaries": 0,
        "execution_state": NOT_EXECUTED,
        "replacement": "FORBIDDEN",
        "retry": "FORBIDDEN",
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def _load_universal_probe_canary_plan(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
) -> UniversalProbeCanaryPlanArtifact:
    identity, capabilities = _validate_model(identity, capabilities)
    discovery = _validate_discovery_dependency(
        identity=identity, capabilities=capabilities, discovery=discovery
    )
    manifest = replay_generated_probe_adapter_manifest(
        manifest,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
    )
    snapshot, value = _canonical_object(raw, "universal probe canary plan")
    expect_keys(
        value,
        required={
            "schema", "plan_id", "model_identity", "capabilities_ref",
            "configuration_ref", "discovery_ref", "manifest_ref", "checks",
            "max_canaries", "attempts_per_canary", "executed_canaries",
            "execution_state", "replacement", "retry", "status", "boundary",
        },
        path="$",
    )
    if value["schema"] != UNIVERSAL_PROBE_CANARY_PLAN_SCHEMA:
        raise UniversalProbeContractValidationError("canary plan schema drifted")
    plan_id = expect_machine_id(value["plan_id"], "$.plan_id")
    _require_model_binding(value["model_identity"], identity, "$.model_identity")
    exact_refs = (
        ("capabilities_ref", capabilities.artifact_ref),
        ("configuration_ref", capabilities.configuration_ref),
        ("discovery_ref", discovery.artifact_ref),
        ("manifest_ref", manifest.artifact_ref),
    )
    for field, expected in exact_refs:
        if parse_artifact_ref(value[field], f"$.{field}") != expected:
            raise UniversalProbeContractValidationError(
                f"canary plan {field} differs from its exact dependency"
            )
    checks_value = expect_list(value["checks"], "$.checks")
    checks = tuple(expect_string(item, f"$.checks[{index}]", maximum=128) for index, item in enumerate(checks_value))
    if checks != _CANARY_CHECKS:
        raise UniversalProbeContractValidationError(
            "canary plan must retain every fixed validation check in order"
        )
    max_canaries = expect_int(
        value["max_canaries"], "$.max_canaries", minimum=1,
        maximum=min(64, len(manifest.sites) * 5),
    )
    if expect_int(value["attempts_per_canary"], "$.attempts_per_canary", minimum=1, maximum=1) != 1:
        raise UniversalProbeContractValidationError(
            "canary plan allows exactly one attempt per canary"
        )
    if expect_int(value["executed_canaries"], "$.executed_canaries", maximum=0) != 0:
        raise UniversalProbeContractValidationError(
            "structure-only canary plans cannot record execution"
        )
    if value["execution_state"] != NOT_EXECUTED:
        raise UniversalProbeContractValidationError(
            "structure-only canary plan execution state must be NOT_EXECUTED"
        )
    if value["replacement"] != "FORBIDDEN" or value["retry"] != "FORBIDDEN":
        raise UniversalProbeContractValidationError(
            "canary replacement and retry must remain forbidden"
        )
    _require_status_boundary(value)
    refs = _owner_closure(
        plan_id,
        (
            identity.artifact_ref, *identity.artifact_refs,
            capabilities.artifact_ref, *capabilities.artifact_refs,
            discovery.artifact_ref, *discovery.artifact_refs,
            manifest.artifact_ref, *manifest.artifact_refs,
        ),
        "canary plan artifact closure",
    )
    return UniversalProbeCanaryPlanArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        plan_id=plan_id,
        identity_ref=identity.artifact_ref,
        capabilities_ref=capabilities.artifact_ref,
        configuration_ref=capabilities.configuration_ref,
        discovery_ref=discovery.artifact_ref,
        manifest_ref=manifest.artifact_ref,
        max_canaries=max_canaries,
        checks=checks,
        payload=freeze_json(value),
        artifact_refs=refs,
    )


def build_universal_probe_canary_plan(
    *,
    plan_id: str,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    max_canaries: int,
) -> UniversalProbeCanaryPlanArtifact:
    """Build a bounded preregistered plan with all execution counters at zero."""

    plan_id = expect_machine_id(plan_id, "plan_id")
    identity, capabilities = _validate_model(identity, capabilities)
    discovery = _validate_discovery_dependency(
        identity=identity, capabilities=capabilities, discovery=discovery
    )
    manifest = replay_generated_probe_adapter_manifest(
        manifest,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
    )
    max_canaries = expect_int(
        max_canaries, "max_canaries", minimum=1,
        maximum=min(64, len(manifest.sites) * 5),
    )
    raw = canonical_json_bytes(
        _canary_value(
            plan_id=plan_id,
            identity=identity,
            capabilities=capabilities,
            discovery=discovery,
            manifest=manifest,
            max_canaries=max_canaries,
        )
    )
    return _load_universal_probe_canary_plan(
        raw,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
    )


def load_universal_probe_canary_plan(
    raw: Any,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
) -> UniversalProbeCanaryPlanArtifact:
    return _load_universal_probe_canary_plan(
        raw,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
    )


def replay_universal_probe_canary_plan(
    plan: UniversalProbeCanaryPlanArtifact,
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
) -> UniversalProbeCanaryPlanArtifact:
    _artifact_storage(plan, UniversalProbeCanaryPlanArtifact, "canary plan")
    if type(plan.checks) is not tuple:
        raise UniversalProbeContractValidationError(
            "canary plan checks must remain an exact immutable tuple"
        )
    replayed = _load_universal_probe_canary_plan(
        plan.raw_bytes,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
    )
    if replayed != plan:
        raise UniversalProbeContractValidationError(
            "universal probe canary plan differs from exact-byte replay"
        )
    return replayed


@dataclass(slots=True)
class _ReplayBackendSeal:
    identity: ComparisonModelIdentityArtifact
    capabilities: ComparisonModelCapabilitiesArtifact
    discovery: ArchitectureDiscoveryReceiptArtifact
    manifest: GeneratedProbeAdapterManifestArtifact
    validation: ProbeValidationReceiptArtifact
    plan: UniversalProbeCanaryPlanArtifact
    request: UniversalProbeReplayRequest
    bundle_signature: tuple[Any, ...]
    consumed: bool
    lock: threading.RLock


@dataclass(frozen=True, slots=True)
class _UnavailableBackendSeal:
    identity: ComparisonModelIdentityArtifact
    capabilities: ComparisonModelCapabilitiesArtifact
    configuration_ref: ArtifactRef
    bundle_signature: tuple[Any, ...]
    reason: str


_BACKEND_SEALS_LOCK = threading.RLock()
_REPLAY_BACKEND_SEALS: WeakKeyDictionary[Any, _ReplayBackendSeal] = WeakKeyDictionary()
_UNAVAILABLE_BACKEND_SEALS: WeakKeyDictionary[Any, _UnavailableBackendSeal] = WeakKeyDictionary()


def _factory_only(name: str) -> NoReturn:
    raise TypeError(f"{name} is factory-only")


def _not_copyable(name: str) -> NoReturn:
    raise TypeError(f"{name} cannot be copied, replaced, or pickled")


class ReplayUniversalProbeBackend:
    """Process-sealed, single-use replay of one preloaded validation receipt."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: Any, **kwargs: Any) -> ReplayUniversalProbeBackend:
        del args, kwargs
        _factory_only("ReplayUniversalProbeBackend")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("ReplayUniversalProbeBackend cannot be subclassed")

    def __copy__(self) -> NoReturn:
        _not_copyable("ReplayUniversalProbeBackend")

    def __deepcopy__(self, memo: Any) -> NoReturn:
        del memo
        _not_copyable("ReplayUniversalProbeBackend")

    def __reduce__(self) -> NoReturn:
        _not_copyable("ReplayUniversalProbeBackend")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _not_copyable("ReplayUniversalProbeBackend")

    def __replace__(self, **changes: Any) -> NoReturn:
        del changes
        _not_copyable("ReplayUniversalProbeBackend")

    @property
    def mode(self) -> str:
        _require_replay_backend_seal(self)
        return REPLAY_ONLY

    @property
    def status(self) -> str:
        _require_replay_backend_seal(self)
        return STRUCTURE_ONLY

    @property
    def authority(self) -> str:
        _require_replay_backend_seal(self)
        return NON_AUTHORITY

    @property
    def consumed(self) -> bool:
        seal = _require_replay_backend_seal(self)
        with seal.lock:
            return seal.consumed

    def replay(self, request: UniversalProbeReplayRequest) -> ProbeValidationReceiptArtifact:
        seal = _require_replay_backend_seal(self)
        with seal.lock:
            if seal.consumed:
                raise UniversalProbeContractValidationError(
                    "universal probe validation replay was already consumed exactly once"
                )
            _verify_replay_backend_seal(seal)
            if type(request) is not UniversalProbeReplayRequest or request is not seal.request:
                raise UniversalProbeContractValidationError(
                    "universal probe replay requires the exact sealed request object"
                )
            detached = replay_probe_validation_receipt(
                seal.validation,
                identity=seal.identity,
                capabilities=seal.capabilities,
                discovery=seal.discovery,
                manifest=seal.manifest,
            )
            if detached is seal.validation:
                raise UniversalProbeContractValidationError(
                    "universal probe replay did not detach its return value"
                )
            seal.consumed = True
            return detached


class UnavailableUniversalProbeBackend:
    """A process-sealed backend that fails before inspecting caller input."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: Any, **kwargs: Any) -> UnavailableUniversalProbeBackend:
        del args, kwargs
        _factory_only("UnavailableUniversalProbeBackend")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        del cls, kwargs
        raise TypeError("UnavailableUniversalProbeBackend cannot be subclassed")

    def __copy__(self) -> NoReturn:
        _not_copyable("UnavailableUniversalProbeBackend")

    def __deepcopy__(self, memo: Any) -> NoReturn:
        del memo
        _not_copyable("UnavailableUniversalProbeBackend")

    def __reduce__(self) -> NoReturn:
        _not_copyable("UnavailableUniversalProbeBackend")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _not_copyable("UnavailableUniversalProbeBackend")

    def __replace__(self, **changes: Any) -> NoReturn:
        del changes
        _not_copyable("UnavailableUniversalProbeBackend")

    @property
    def mode(self) -> str:
        _require_unavailable_backend_seal(self)
        return UNAVAILABLE_BACKEND

    @property
    def status(self) -> str:
        _require_unavailable_backend_seal(self)
        return STRUCTURE_ONLY

    @property
    def authority(self) -> str:
        _require_unavailable_backend_seal(self)
        return NON_AUTHORITY

    def replay(self, request: object) -> NoReturn:
        del request
        seal = _require_unavailable_backend_seal(self)
        raise UniversalProbeBackendUnavailableError(seal.reason)


def _bundle_signature(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact | None = None,
    manifest: GeneratedProbeAdapterManifestArtifact | None = None,
    validation: ProbeValidationReceiptArtifact | None = None,
    plan: UniversalProbeCanaryPlanArtifact | None = None,
) -> tuple[Any, ...]:
    values: list[Any] = [
        identity.artifact_ref,
        identity.raw_bytes,
        capabilities.artifact_ref,
        capabilities.raw_bytes,
        capabilities.configuration_ref,
        capabilities.configuration_bytes,
    ]
    for artifact in (discovery, manifest, validation, plan):
        if artifact is not None:
            values.extend((artifact.artifact_ref, artifact.raw_bytes, artifact.artifact_refs))
    return tuple(values)


def _request_for(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    validation: ProbeValidationReceiptArtifact,
    plan: UniversalProbeCanaryPlanArtifact,
) -> UniversalProbeReplayRequest:
    return UniversalProbeReplayRequest(
        identity_ref=identity.artifact_ref,
        capabilities_ref=capabilities.artifact_ref,
        configuration_ref=capabilities.configuration_ref,
        discovery_ref=discovery.artifact_ref,
        manifest_ref=manifest.artifact_ref,
        validation_ref=validation.artifact_ref,
        canary_plan_ref=plan.artifact_ref,
    )


def _validate_bundle(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    validation: ProbeValidationReceiptArtifact,
    plan: UniversalProbeCanaryPlanArtifact,
) -> tuple[
    ComparisonModelIdentityArtifact,
    ComparisonModelCapabilitiesArtifact,
    ArchitectureDiscoveryReceiptArtifact,
    GeneratedProbeAdapterManifestArtifact,
    ProbeValidationReceiptArtifact,
    UniversalProbeCanaryPlanArtifact,
]:
    identity, capabilities = _validate_model(identity, capabilities)
    discovery = _validate_discovery_dependency(
        identity=identity, capabilities=capabilities, discovery=discovery
    )
    manifest = replay_generated_probe_adapter_manifest(
        manifest,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
    )
    validation = replay_probe_validation_receipt(
        validation,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
    )
    plan = replay_universal_probe_canary_plan(
        plan,
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
    )
    if (
        validation.manifest_ref != manifest.artifact_ref
        or plan.manifest_ref != manifest.artifact_ref
        or validation.discovery_ref != discovery.artifact_ref
        or plan.discovery_ref != discovery.artifact_ref
    ):
        raise UniversalProbeContractValidationError(
            "universal probe bundle dependencies are not exact"
        )
    closure = (
        identity.artifact_ref, *identity.artifact_refs,
        capabilities.artifact_ref, *capabilities.artifact_refs,
        discovery.artifact_ref, *discovery.artifact_refs,
        manifest.artifact_ref, *manifest.artifact_refs,
        validation.artifact_ref, *validation.artifact_refs,
        plan.artifact_ref, *plan.artifact_refs,
    )
    _unique_ref_closure(closure, "universal probe bundle closure")
    return identity, capabilities, discovery, manifest, validation, plan


def build_replay_universal_probe_backend(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    discovery: ArchitectureDiscoveryReceiptArtifact,
    manifest: GeneratedProbeAdapterManifestArtifact,
    validation: ProbeValidationReceiptArtifact,
    plan: UniversalProbeCanaryPlanArtifact,
) -> tuple[ReplayUniversalProbeBackend, UniversalProbeReplayRequest]:
    """Seal one single-use replay bundle and its exact request object."""

    identity, capabilities, discovery, manifest, validation, plan = _validate_bundle(
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        validation=validation,
        plan=plan,
    )
    request = _request_for(
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        validation=validation,
        plan=plan,
    )
    signature = _bundle_signature(
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        validation=validation,
        plan=plan,
    )
    backend = object.__new__(ReplayUniversalProbeBackend)
    seal = _ReplayBackendSeal(
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        validation=validation,
        plan=plan,
        request=request,
        bundle_signature=signature,
        consumed=False,
        lock=threading.RLock(),
    )
    with _BACKEND_SEALS_LOCK:
        _REPLAY_BACKEND_SEALS[backend] = seal
    return backend, request


def build_unavailable_universal_probe_backend(
    *,
    identity: ComparisonModelIdentityArtifact,
    capabilities: ComparisonModelCapabilitiesArtifact,
    configuration_ref: ArtifactRef,
    configuration_bytes: bytes,
    reason: str,
) -> UnavailableUniversalProbeBackend:
    """Bind a fail-closed backend to one exact model/configuration."""

    identity, capabilities = _validate_model(identity, capabilities)
    configuration_ref, _ = _validate_configuration(
        capabilities, configuration_ref, configuration_bytes
    )
    reason = expect_string(reason, "reason", maximum=512)
    signature = _bundle_signature(identity=identity, capabilities=capabilities)
    backend = object.__new__(UnavailableUniversalProbeBackend)
    seal = _UnavailableBackendSeal(
        identity=identity,
        capabilities=capabilities,
        configuration_ref=configuration_ref,
        bundle_signature=signature,
        reason=reason,
    )
    with _BACKEND_SEALS_LOCK:
        _UNAVAILABLE_BACKEND_SEALS[backend] = seal
    return backend


def _require_replay_backend_seal(backend: object) -> _ReplayBackendSeal:
    if type(backend) is not ReplayUniversalProbeBackend:
        raise UniversalProbeContractValidationError(
            "replay backend has a substituted exact type"
        )
    with _BACKEND_SEALS_LOCK:
        seal = _REPLAY_BACKEND_SEALS.get(backend)
    if seal is None:
        raise UniversalProbeContractValidationError(
            "replay backend is not an exact process-sealed factory result"
        )
    return seal


def _require_unavailable_backend_seal(backend: object) -> _UnavailableBackendSeal:
    if type(backend) is not UnavailableUniversalProbeBackend:
        raise UniversalProbeContractValidationError(
            "unavailable backend has a substituted exact type"
        )
    with _BACKEND_SEALS_LOCK:
        seal = _UNAVAILABLE_BACKEND_SEALS.get(backend)
    if seal is None:
        raise UniversalProbeContractValidationError(
            "unavailable backend is not an exact process-sealed factory result"
        )
    current = _bundle_signature(
        identity=seal.identity, capabilities=seal.capabilities
    )
    if current != seal.bundle_signature:
        raise UniversalProbeContractValidationError(
            "unavailable backend model binding was mutated"
        )
    return seal


def _verify_replay_backend_seal(seal: _ReplayBackendSeal) -> None:
    bundle = _validate_bundle(
        identity=seal.identity,
        capabilities=seal.capabilities,
        discovery=seal.discovery,
        manifest=seal.manifest,
        validation=seal.validation,
        plan=seal.plan,
    )
    identity, capabilities, discovery, manifest, validation, plan = bundle
    current = _bundle_signature(
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        validation=validation,
        plan=plan,
    )
    if current != seal.bundle_signature or _request_for(
        identity=identity,
        capabilities=capabilities,
        discovery=discovery,
        manifest=manifest,
        validation=validation,
        plan=plan,
    ) != seal.request:
        raise UniversalProbeContractValidationError(
            "sealed universal probe replay bundle was mutated"
        )


def replay_universal_probe_validation(
    backend: object,
    request: object,
) -> ProbeValidationReceiptArtifact:
    """Dispatch only to the exact replay or unavailable built-in backend."""

    if type(backend) is ReplayUniversalProbeBackend:
        if type(request) is not UniversalProbeReplayRequest:
            raise UniversalProbeContractValidationError(
                "replay backend requires an exact UniversalProbeReplayRequest"
            )
        return backend.replay(request)
    if type(backend) is UnavailableUniversalProbeBackend:
        return backend.replay(request)
    raise UniversalProbeContractValidationError(
        "arbitrary, live, model, provider, or network probe backends are not installed"
    )


__all__ = (
    "ARCHITECTURE_DISCOVERY_EVIDENCE_SCHEMA",
    "ARCHITECTURE_DISCOVERY_RECEIPT_SCHEMA",
    "GENERATED_PROBE_ADAPTER_MANIFEST_SCHEMA",
    "PROBE_VALIDATION_EVIDENCE_SCHEMA",
    "PROBE_VALIDATION_RECEIPT_SCHEMA",
    "UNIVERSAL_PROBE_CANARY_PLAN_SCHEMA",
    "ARCHITECTURE_DISCOVERY_EVIDENCE_MEDIA_TYPE",
    "ARCHITECTURE_DISCOVERY_RECEIPT_MEDIA_TYPE",
    "GENERATED_PROBE_ADAPTER_MANIFEST_MEDIA_TYPE",
    "PROBE_VALIDATION_EVIDENCE_MEDIA_TYPE",
    "PROBE_VALIDATION_RECEIPT_MEDIA_TYPE",
    "UNIVERSAL_PROBE_CANARY_PLAN_MEDIA_TYPE",
    "DENSE_DECODER",
    "ENCODER_DECODER",
    "MIXTURE_OF_EXPERTS",
    "SSM_RECURRENT",
    "MULTIMODAL",
    "ARCHITECTURE_FAMILIES",
    "CONFIG_STRUCTURE_RECORDED",
    "AMBIGUOUS_CONFIG_STRUCTURE",
    "DISCOVERY_UNAVAILABLE_BY_ACCESS_MODEL",
    "DISCOVERY_UNAVAILABLE_IN_REPLAY",
    "DISCOVERY_UNAVAILABLE_NOT_IMPLEMENTED",
    "DISCOVERY_STATES",
    "RESIDUAL",
    "ATTENTION",
    "MLP",
    "ROUTER",
    "EXPERT",
    "RECURRENT",
    "MULTIMODAL_SITE",
    "SEMANTIC_PROBE_SITES",
    "RESIDUAL_STREAM",
    "ATTENTION_OUTPUT",
    "MLP_OUTPUT",
    "ROUTER_LOGITS",
    "EXPERT_OUTPUT",
    "RECURRENT_STATE",
    "MULTIMODAL_FUSION",
    "SEMANTIC_PROJECTIONS",
    "PRE",
    "POST",
    "HOOK_LOCATIONS",
    "ALL_TOKENS",
    "LAST_TOKEN",
    "SELECTED_TOKEN",
    "NO_TOKEN_AXIS",
    "TOKEN_SCOPES",
    "FLOAT16",
    "BFLOAT16",
    "FLOAT32",
    "INT8",
    "INT4",
    "DTYPES",
    "NO_QUANTIZATION",
    "QUANTIZED_INT8",
    "QUANTIZED_INT4",
    "QUANTIZED_NF4",
    "QUANTIZATIONS",
    "IDENTITY_TRANSFORM",
    "SELECT_TOKEN_TRANSFORM",
    "SELECT_HEAD_TRANSFORM",
    "ROUTER_LOGITS_TRANSFORM",
    "SELECT_EXPERT_TRANSFORM",
    "RECURRENT_STATE_TRANSFORM",
    "MULTIMODAL_FUSION_TRANSFORM",
    "TRANSFORMS",
    "REPLAY_FIXTURE_MATCH",
    "AMBIGUOUS_VALIDATION",
    "VALIDATION_UNAVAILABLE_NOT_IMPLEMENTED",
    "VALIDATION_STATES",
    "UNMEASURED",
    "CAPABILITY_UNAVAILABLE_BY_ACCESS_MODEL",
    "CAPABILITY_UNAVAILABLE_IN_REPLAY",
    "MODEL_PROBE_CAPABILITY_STATES",
    "NOT_LICENSED",
    "NOT_EXECUTED",
    "REPLAY_ONLY",
    "UNAVAILABLE_BACKEND",
    "UniversalProbeContractValidationError",
    "UniversalProbeBackendUnavailableError",
    "ProbeSiteSpec",
    "ProbeValidationResult",
    "ArchitectureDiscoveryReceiptArtifact",
    "GeneratedProbeAdapterManifestArtifact",
    "ProbeValidationReceiptArtifact",
    "UniversalProbeCanaryPlanArtifact",
    "UniversalProbeReplayRequest",
    "build_architecture_discovery_evidence_body",
    "build_architecture_discovery_receipt",
    "load_architecture_discovery_receipt",
    "replay_architecture_discovery_receipt",
    "build_generated_probe_adapter_manifest",
    "load_generated_probe_adapter_manifest",
    "replay_generated_probe_adapter_manifest",
    "probe_capability_state",
    "build_probe_validation_evidence_body",
    "build_probe_validation_receipt",
    "load_probe_validation_receipt",
    "replay_probe_validation_receipt",
    "build_universal_probe_canary_plan",
    "load_universal_probe_canary_plan",
    "replay_universal_probe_canary_plan",
    "ReplayUniversalProbeBackend",
    "UnavailableUniversalProbeBackend",
    "build_replay_universal_probe_backend",
    "build_unavailable_universal_probe_backend",
    "replay_universal_probe_validation",
)
