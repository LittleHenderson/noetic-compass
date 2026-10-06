"""Strict exact-byte binding for one successful real-worker dump.

This research-only module performs no I/O and owns no lifecycle transition. It
does not issue or consume an authorization, invoke or retry a worker, retain an
output, build an Evidence Packet, or establish authenticated execution. It
only snapshots two already-available byte carriers and proves that their JSON,
request, event sequence, and declared real-model manifest satisfy the bounded
contract below.

A caller must distinguish a definite validation failure from uncertainty after
an outbound request may have executed. The latter is represented by
``RealWorkerPostSendAmbiguousError`` and must not be converted into a retry by
this module or by a caller without a durable create-once worker protocol.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any


MAX_CARRIER_BYTES = 2_000_000
MAX_JSON_DEPTH = 40
MAX_JSON_NODES = 50_000
MAX_INTEGER_BITS = 2_048

_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_LOWER_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UPPER_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_SAFE_CONTEXT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,200}$")
_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")
_LOWER_SIGNATURE_RE = re.compile(r"^hmac-sha256:[0-9a-f]{64}$")
_COORDINATE_LABEL_RE = re.compile(r"^L([0-9]+)N([0-9]+)$")

_REQUEST_REQUIRED_KEYS = frozenset(
    {
        "prompt",
        "model_id",
        "max_new_tokens",
        "temperature",
        "probes",
        "method_config",
    }
)
_REQUEST_OPTIONAL_KEYS = frozenset(
    {"seed", "ablation_target", "billing_measurement_context"}
)
_ALLOWED_PROBES = frozenset(
    {
        "active_trace",
        "blindspot_covers",
        "blindspots_f1",
        "mode7_attribution",
        "confidence_margin",
        "causal_ablation",
    }
)
_ALLOWED_EVENT_TYPES = frozenset(
    {
        "manifest",
        "knob_resolution",
        "token",
        "neuron_covers",
        "ablation_effect",
        "ablation_control_effect",
        "word_spans",
        "error",
        "complete",
    }
)
_EVENT_PHASE = {
    "knob_resolution": 0,
    "neuron_covers": 0,
    "token": 1,
    "ablation_effect": 2,
    "ablation_control_effect": 3,
}
_EVENT_KEYS = {
    "manifest": frozenset({"type", "manifest"}),
    "knob_resolution": frozenset({"type", "resolved_knobs"}),
    "neuron_covers": frozenset({"type", "per_class_neuron_covers"}),
    "token": frozenset(
        {
            "type",
            "token_index",
            "token",
            "top_activated_neurons",
            "mode7_attribution",
            "confidence",
            "inversion_risk",
            "verification_mode",
            "verification_verdict",
            "verification_threshold",
            "verification_score",
            "verification_score_source",
            "verification_invalid_mode",
            "eraser_intervention_result",
        }
    ),
    "ablation_effect": frozenset(
        {
            "type",
            "target",
            "mode",
            "is_real_model",
            "baseline_top_token",
            "ablated_top_token",
            "baseline_top_token_id",
            "ablated_top_token_id",
            "logit_delta",
            "confidence_delta",
            "top_token_changed",
            "detail",
        }
    ),
    "ablation_control_effect": frozenset(
        {
            "type",
            "target",
            "mode",
            "is_real_model",
            "n_controls",
            "control_units",
            "target_abs_logit_delta",
            "control_mean_abs_logit_delta",
            "control_max_abs_logit_delta",
            "margin_over_control_max",
            "selectivity_passed",
            "seed",
            "detail",
        }
    ),
    "word_spans": frozenset(
        {"type", "spans", "structural_token_indices", "total_tokens_covered"}
    ),
    "error": frozenset({"type", "message", "retryable"}),
    "complete": frozenset({"type", "total_tokens"}),
}
_TOKEN_ACTIVATION_KEYS = frozenset({"layer", "index", "activation"})
_MODE7_EDGE_KEYS = frozenset({"from_token_index", "to_token_index", "weight"})
_WORD_SPAN_KEYS = frozenset({"word", "token_indices", "char_start", "char_end"})
_COVER_MEMBER_KEYS = frozenset(
    {"label", "confidence", "confidence_band", "evidence_sources"}
)
_INTERVENTION_KEYS = frozenset(
    {
        "contract_version",
        "method_id",
        "execution_kind",
        "source_kind",
        "structural_status",
        "structurally_valid",
        "coordinate_space",
        "hook_semantics",
        "token_selection",
        "requested_gain",
        "effective_gain",
        "expected_coordinate_width",
        "expected_projected_output_width",
        "hook_fired",
        "required_hook_layers",
        "hook_fired_layers",
        "observed_tensor_geometry",
        "reference_tensor_geometry",
        "stability_control_tensor_geometry",
        "requested_coordinates",
        "valid_coordinates",
        "invalid_coordinates",
        "applied_coordinates",
        "activation_changed",
        "output_changed",
        "stability_control_performed",
        "baseline_output_stable",
        "baseline_geometry_stable",
        "detail",
    }
)
_INTERVENTION_COORDINATE_KEYS = frozenset({"layer", "index", "coordinate_space"})
_INTERVENTION_GEOMETRY_KEYS = frozenset(
    {
        "layer",
        "shape",
        "rank",
        "width",
        "projected_output_width",
        "coordinate_space",
        "observation_phase",
        "hook_module_path",
        "tensor_role",
        "dtype",
        "device",
        "all_finite",
        "rng_state_sha256",
        "rng_state_after_sha256",
        "hook_call_count",
    }
)
_INTERVENTION_STATUSES = frozenset(
    {
        "REJECTED_NO_COORDINATES",
        "REJECTED_INVALID_GAIN",
        "REJECTED_WRONG_COORDINATE_SPACE",
        "REJECTED_MISSING_PREFLIGHT",
        "REJECTED_HOOK_CONTRACT",
        "REJECTED_HOOK_CARDINALITY",
        "REJECTED_NONFINITE_TENSOR",
        "REJECTED_RNG_STATE_MISMATCH",
        "REJECTED_MISSING_STABILITY_CONTROL",
        "REJECTED_UNSTABLE_BASELINE",
        "REJECTED_ALL_COORDINATES_INVALID",
        "REJECTED_PARTIALLY_INVALID_COORDINATES",
        "REJECTED_RUNTIME_GEOMETRY",
        "HOOK_NOT_FIRED",
        "ACTIVATION_UNCHANGED",
        "OUTPUT_CHANGE_UNAVAILABLE",
        "OUTPUT_UNCHANGED",
        "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED",
    }
)
_KNOWN_METHODS = frozenset(
    {
        "foundation_probe",
        "rpm_gate_check",
        "inversion_scan",
        "blindspot_detection",
        "verification_stack",
        "drive_local_eraser",
    }
)
_KNOWN_DRIVES = frozenset({f"F{index}" for index in range(1, 8)})
_VERIFICATION_THRESHOLDS = {
    "BALANCED": (0.65, 0.45),
    "HIGH_PRECISION": (0.85, 0.55),
    "MAX_COVERAGE_TRIAGE": (0.50, 0.30),
}
_BILLING_RECEIPT_KEYS = frozenset(
    {
        "schema_version",
        "key_id",
        "issuer",
        "tenant_id",
        "billing_account_id",
        "run_id",
        "worker_id",
        "provider_id",
        "model_id",
        "accelerator_type",
        "accelerator_count",
        "accelerator_milliseconds",
        "measurement_started_at",
        "measurement_ended_at",
        "issued_at",
        "nonce",
        "payload_sha256",
        "signature",
    }
)
_BILLING_RECEIPT_SCHEMA = "cas_harness_live_worker_measurement_receipt.v1"
_MAX_BILLING_RECEIPT_BYTES = 16_384
_JOINED_EXECUTION_BINDING_KEYS = frozenset(
    {
        "schema_version",
        "status",
        "authority",
        "authorization_sha256",
        "prospective_run_id",
        "invocation_id_sha256",
        "request_sha256",
        "request_byte_length",
        "events_sha256",
        "events_byte_length",
        "digest_profile",
        "binding_scope",
        "nonclaim",
    }
)
_SUPPORTED_HOOKS = frozenset(
    {
        "residual_stream",
        "mlp_pre_activation",
        "mlp_post_activation",
        "mlp_intermediate_post_activation",
        "attention_pattern",
        "attention_head_output",
        "logits",
    }
)
_MANIFEST_KEYS = frozenset(
    {
        "model_id",
        "model_arch",
        "tokenizer_id",
        "supported_hooks",
        "execution_kind",
        "intervention_hook_contract",
        "worker_version",
        "requested_revision",
        "resolved_revision",
        "revision_verified",
        "weights_filename",
        "weights_sha256",
        "weights_bytes",
        "weights_hash_verified",
        "model_identity_status",
        "runtime_execution",
        "is_real_model",
    }
)
_MODEL_ARCH_KEYS = frozenset(
    {
        "family",
        "n_layers",
        "hidden_size",
        "mlp_intermediate_dim",
        "n_heads",
        "total_params",
        "validated",
    }
)
_RUNTIME_KEYS = frozenset(
    {
        "profile",
        "device",
        "dtype",
        "torch_version",
        "torch_native_jit_disabled",
        "cuda_bfloat16_supported",
        "cuda_runtime_version",
        "cuda_driver_version",
        "cuda_device_name",
        "cuda_device_capability",
    }
)
PYTHIA_STAGE27F_HOOK_PROFILE = "PYTHIA_STAGE27F_ERASER_V2"
QWEN_OBSERVATION_ONLY_HOOK_PROFILE = "QWEN2_MLP_OBSERVATION_ONLY_V1"

_PYTHIA_HOOK_CONTRACT = {
    "contract_version": "harness_v2.mlp_intermediate_eraser.v2",
    "coordinate_space": "mlp_intermediate_post_activation",
    "module_path_template": "gpt_neox.layers[{layer}].mlp.dense_4h_to_h",
    "tensor_role": "forward_pre_hook.input[0]",
    "token_selection": "batch_0_last_sequence_position",
    "expected_width_source": "model_arch.mlp_intermediate_dim",
    "failure_policy": "fail_closed",
}
_QWEN_OBSERVATION_ONLY_HOOK_CONTRACT = {
    "contract_version": "harness_v2.qwen2_mlp_intermediate_observation_only.v1",
    "capability_status": (
        "OBSERVATION_ONLY_INTERVENTION_UNAVAILABLE_UNCALIBRATED"
    ),
    "coordinate_space": "mlp_intermediate_post_activation",
    "module_path_template": "model.layers[{layer}].mlp.down_proj",
    "tensor_role": "forward_pre_hook.input[0]",
    "token_selection": "batch_0_last_sequence_position",
    "expected_width_source": "model_arch.mlp_intermediate_dim",
    "failure_policy": "fail_closed",
    "unavailable_reason": "NO_QWEN_CALIBRATED_COORDINATE_ADAPTER",
}
_HOOK_CONTRACTS = MappingProxyType(
    {
        PYTHIA_STAGE27F_HOOK_PROFILE: _PYTHIA_HOOK_CONTRACT,
        QWEN_OBSERVATION_ONLY_HOOK_PROFILE: (
            _QWEN_OBSERVATION_ONLY_HOOK_CONTRACT
        ),
    }
)
_QWEN_OBSERVATION_ONLY_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
_QWEN_OBSERVATION_ONLY_TOKENIZER_ID = _QWEN_OBSERVATION_ONLY_MODEL_ID
_QWEN_OBSERVATION_ONLY_ARCH = MappingProxyType(
    {
        "family": "qwen2",
        "n_layers": 24,
        "hidden_size": 896,
        "mlp_intermediate_dim": 4864,
        "n_heads": 14,
        "total_params": 494_032_768,
        "validated": True,
    }
)
_QWEN_OBSERVATION_ONLY_SUPPORTED_HOOKS = (
    "residual_stream",
    "mlp_intermediate_post_activation",
    "attention_pattern",
    "logits",
)


class RealWorkerJoinError(RuntimeError):
    """Base error for the non-authoritative join boundary."""


class RealWorkerDumpValidationError(RealWorkerJoinError):
    """The supplied bytes definitely violate the strict dump contract."""

    outcome_certainty = "DEFINITE_VALIDATION_FAILURE"


class RealWorkerPostSendAmbiguousError(RealWorkerJoinError):
    """A request may have executed, but no exact terminal result is known.

    This module never raises this class itself because it never performs I/O.
    Network/executor code should use it for a post-send timeout, disconnect, or
    crash boundary and must not infer that an automatic model retry is safe.
    """

    outcome_certainty = "POST_SEND_EXECUTION_AMBIGUOUS"


class _JSONProfileError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExpectedRealWorkerManifest:
    """Explicit model artifact identity required from the worker manifest."""

    model_id: str
    revision: str
    weights_filename: str
    weights_sha256: str
    weights_bytes: int
    hook_contract_profile: str = PYTHIA_STAGE27F_HOOK_PROFILE

    def __post_init__(self) -> None:
        if not _bounded_text(self.model_id, maximum=512):
            raise ValueError("expected model_id must be bounded non-empty text")
        if _REVISION_RE.fullmatch(self.revision) is None:
            raise ValueError("expected revision must be a full lowercase commit")
        if not _bounded_text(self.weights_filename, maximum=1024):
            raise ValueError("expected weights_filename must be bounded non-empty text")
        if _LOWER_SHA256_RE.fullmatch(self.weights_sha256) is None:
            raise ValueError("expected weights_sha256 must be lowercase SHA-256")
        if type(self.weights_bytes) is not int or self.weights_bytes <= 0:
            raise ValueError("expected weights_bytes must be a positive integer")
        if (
            type(self.hook_contract_profile) is not str
            or self.hook_contract_profile not in _HOOK_CONTRACTS
        ):
            raise ValueError("expected hook_contract_profile is not supported")
        if (
            self.hook_contract_profile == QWEN_OBSERVATION_ONLY_HOOK_PROFILE
            and self.model_id != _QWEN_OBSERVATION_ONLY_MODEL_ID
        ) or (
            self.model_id == _QWEN_OBSERVATION_ONLY_MODEL_ID
            and self.hook_contract_profile != QWEN_OBSERVATION_ONLY_HOOK_PROFILE
        ):
            raise ValueError(
                "expected model_id does not match hook_contract_profile"
            )


@dataclass(frozen=True, slots=True)
class ExpectedJoinedExecutionIdentity:
    """Caller-known identity required to check the worker process binding."""

    authorization_sha256: str
    prospective_run_id: str
    invocation_id: str

    def __post_init__(self) -> None:
        if _UPPER_SHA256_RE.fullmatch(self.authorization_sha256) is None:
            raise ValueError("authorization_sha256 must be uppercase SHA-256")
        if _SAFE_CONTEXT_ID_RE.fullmatch(self.prospective_run_id) is None:
            raise ValueError("prospective_run_id must be a canonical machine identifier")
        if _SAFE_CONTEXT_ID_RE.fullmatch(self.invocation_id) is None:
            raise ValueError("invocation_id must be a canonical ASCII identifier")


@dataclass(frozen=True, slots=True)
class RealWorkerManifestFacts:
    model_id: str
    revision: str
    weights_filename: str
    weights_sha256: str
    weights_bytes: int
    worker_version: str
    torch_version: str
    cuda_runtime_version: str
    cuda_driver_version: int
    cuda_device_name: str
    cuda_device_capability: str
    supported_hooks: tuple[str, ...]
    n_layers: int
    hidden_size: int
    mlp_intermediate_dim: int
    n_heads: int
    hook_contract_profile: str
    intervention_available: bool
    legacy_cover_library_available: bool


@dataclass(frozen=True, slots=True)
class JoinedExecutionBindingFacts:
    authorization_sha256: str
    prospective_run_id: str
    invocation_id_sha256: str
    request_sha256: str
    request_byte_length: int
    events_sha256: str
    events_byte_length: int
    authority: str = "WORKER_PROCESS_OBSERVATION_ONLY"
    nonclaim: str = "NOT_A_SIGNATURE_OR_TRUSTED_EXECUTION_ATTESTATION"


@dataclass(frozen=True, slots=True)
class StrictRealWorkerRequestBinding:
    """Immutable pre-consumption result for exact worker-request bytes."""

    request_raw: bytes
    request_sha256: str
    request_byte_length: int
    request_payload: Mapping[str, Any]
    model_id: str
    hook_contract_profile: str
    causal_ablation_requested: bool
    ablation_target: tuple[int, int]
    ablation_mode: str
    claim_scope: str = "EXACT_REQUEST_BYTES_AND_EXPECTED_MODEL_CONSISTENCY_ONLY"
    execution_authentication: str = "NOT_ESTABLISHED"
    image_identity: str = "NOT_ESTABLISHED"
    scientific_status: str = "NOT_ESTABLISHED"
    criteria_status: str = "OPEN"
    product_status: str = "RESEARCH_ONLY"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"
    terminal_completion_authority: str = "NOT_AUTHORIZED"


@dataclass(frozen=True, slots=True)
class StrictRealWorkerDumpBinding:
    """Immutable mechanics-only result for one successful worker dump."""

    request_raw: bytes
    request_sha256: str
    request_byte_length: int
    response_raw: bytes
    response_sha256: str
    response_byte_length: int
    request_payload: Mapping[str, Any]
    events: tuple[Mapping[str, Any], ...]
    event_counts: Mapping[str, int]
    token_count: int
    output_text: str
    causal_ablation_requested: bool
    billing_measurement_receipt: Mapping[str, Any] | None
    joined_execution_binding: JoinedExecutionBindingFacts | None
    manifest: RealWorkerManifestFacts
    claim_scope: str = "EXACT_BYTES_AND_DECLARED_MANIFEST_CONSISTENCY_ONLY"
    execution_authentication: str = "NOT_ESTABLISHED"
    image_identity: str = "NOT_ESTABLISHED"
    scientific_status: str = "NOT_ESTABLISHED"
    criteria_status: str = "OPEN"
    product_status: str = "RESEARCH_ONLY"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"
    response_pairing_status: str = "UNBOUND_LEGACY_RESPONSE"
    billing_receipt_authentication: str = "NOT_ESTABLISHED"
    terminal_completion_authority: str = "NOT_AUTHORIZED"


def validate_real_worker_dump_request(
    *,
    request_raw: bytes | bytearray | memoryview,
    expected_manifest: ExpectedRealWorkerManifest,
) -> StrictRealWorkerRequestBinding:
    """Validate and freeze request bytes before any caller sends them.

    This function performs no I/O. Its result establishes only the exact
    request syntax and its consistency with the caller-supplied model identity;
    it does not authorize, execute, authenticate, or retry a model run.
    """

    if type(expected_manifest) is not ExpectedRealWorkerManifest:
        raise RealWorkerDumpValidationError(
            "expected_manifest must be an exact ExpectedRealWorkerManifest"
        )
    request_snapshot, request = _load_json_object(request_raw, "request")
    _validate_request(request, expected_manifest=expected_manifest)
    causal_requested, target, mode = _causal_request(request)
    return StrictRealWorkerRequestBinding(
        request_raw=request_snapshot,
        request_sha256=_sha256(request_snapshot),
        request_byte_length=len(request_snapshot),
        request_payload=_freeze_json(request),
        model_id=request["model_id"],
        hook_contract_profile=expected_manifest.hook_contract_profile,
        causal_ablation_requested=causal_requested,
        ablation_target=target,
        ablation_mode=mode,
    )


def bind_successful_real_worker_dump(
    *,
    request_raw: bytes | bytearray | memoryview,
    response_raw: bytes | bytearray | memoryview,
    expected_manifest: ExpectedRealWorkerManifest,
    expected_joined_execution: ExpectedJoinedExecutionIdentity | None = None,
    allow_billing_receipt: bool = False,
) -> StrictRealWorkerDumpBinding:
    """Strict-load and bind one already-returned successful dump.

    A validation error is a definite statement about these supplied bytes. It
    is not evidence that a remote execution did not occur and does not itself
    authorize a retry.
    """

    if type(allow_billing_receipt) is not bool:
        raise RealWorkerDumpValidationError(
            "allow_billing_receipt must be an exact boolean"
        )
    if expected_joined_execution is not None and type(
        expected_joined_execution
    ) is not ExpectedJoinedExecutionIdentity:
        raise RealWorkerDumpValidationError(
            "expected_joined_execution must use the exact joined identity type"
        )

    request_binding = validate_real_worker_dump_request(
        request_raw=request_raw,
        expected_manifest=expected_manifest,
    )

    response_snapshot, response = _load_json_object(response_raw, "response")
    allowed_response_keys = {"events"}
    billing_context = request_binding.request_payload.get(
        "billing_measurement_context"
    )
    if billing_context is not None:
        if not allow_billing_receipt:
            raise RealWorkerDumpValidationError(
                "a billing request requires explicit receipt consumption"
            )
        allowed_response_keys.add("billing_measurement_receipt")
    if expected_joined_execution is not None:
        allowed_response_keys.add("joined_execution_binding")
    if set(response) != allowed_response_keys:
        raise RealWorkerDumpValidationError(
            "response top-level keys differ from the exact dump contract"
        )
    events = response.get("events")
    if type(events) is not list or not events:
        raise RealWorkerDumpValidationError("response events must be a non-empty array")
    billing_present = "billing_measurement_receipt" in response
    billing = response.get("billing_measurement_receipt")
    if billing_present and type(billing) is not dict:
        raise RealWorkerDumpValidationError(
            "billing_measurement_receipt must be an object when present"
        )
    if billing_context is None and billing_present:
        raise RealWorkerDumpValidationError(
            "a response receipt is forbidden without request billing context"
        )
    if isinstance(billing_context, Mapping):
        _validate_billing_receipt(
            billing,
            expected_context=billing_context,
            expected_model_id=request_binding.model_id,
        )

    joined_facts = None
    if expected_joined_execution is not None:
        joined_facts = _validate_joined_execution_binding(
            response.get("joined_execution_binding"),
            expected=expected_joined_execution,
            request_binding=request_binding,
            events=events,
        )

    manifest_facts, event_counts, output_text, token_count = _validate_events(
        events,
        expected_manifest=expected_manifest,
        request_payload=request_binding.request_payload,
        causal_requested=request_binding.causal_ablation_requested,
        expected_target=request_binding.ablation_target,
        expected_mode=request_binding.ablation_mode,
    )
    frozen_events = tuple(_freeze_json(event) for event in events)
    frozen_billing = _freeze_json(billing) if billing is not None else None
    return StrictRealWorkerDumpBinding(
        request_raw=request_binding.request_raw,
        request_sha256=request_binding.request_sha256,
        request_byte_length=request_binding.request_byte_length,
        response_raw=response_snapshot,
        response_sha256=_sha256(response_snapshot),
        response_byte_length=len(response_snapshot),
        request_payload=request_binding.request_payload,
        events=frozen_events,
        event_counts=MappingProxyType(dict(sorted(event_counts.items()))),
        token_count=token_count,
        output_text=output_text,
        causal_ablation_requested=request_binding.causal_ablation_requested,
        billing_measurement_receipt=frozen_billing,
        joined_execution_binding=joined_facts,
        manifest=manifest_facts,
        response_pairing_status=(
            "WORKER_PROCESS_OBSERVED_REQUEST_EVENTS_PAIR"
            if joined_facts is not None
            else "UNBOUND_LEGACY_RESPONSE"
        ),
    )


def _validate_joined_execution_binding(
    value: object,
    *,
    expected: ExpectedJoinedExecutionIdentity,
    request_binding: StrictRealWorkerRequestBinding,
    events: list[Any],
) -> JoinedExecutionBindingFacts:
    if type(value) is not dict or set(value) != _JOINED_EXECUTION_BINDING_KEYS:
        raise RealWorkerDumpValidationError(
            "joined execution binding has invalid exact structure"
        )
    constants = {
        "schema_version": "cas_harness_live_worker.joined_execution_binding.v1",
        "status": "OBSERVED_REQUEST_AND_EVENTS_BOUND",
        "authority": "WORKER_PROCESS_OBSERVATION_ONLY",
        "digest_profile": "UTF8_SORTED_KEYS_COMPACT_JSON_ENSURE_ASCII_FALSE_V1",
        "binding_scope": "EXACT_REQUEST_BYTES_AND_CANONICAL_EVENTS_MEMBER_ONLY",
        "nonclaim": "NOT_A_SIGNATURE_OR_TRUSTED_EXECUTION_ATTESTATION",
    }
    if any(value[field] != expected_value for field, expected_value in constants.items()):
        raise RealWorkerDumpValidationError("joined execution binding contract drifted")
    invocation_sha256 = _sha256(expected.invocation_id.encode("ascii"))
    expected_identity = {
        "authorization_sha256": expected.authorization_sha256,
        "prospective_run_id": expected.prospective_run_id,
        "invocation_id_sha256": invocation_sha256,
        "request_sha256": request_binding.request_sha256,
        "request_byte_length": request_binding.request_byte_length,
    }
    if any(value[field] != expected_value for field, expected_value in expected_identity.items()):
        raise RealWorkerDumpValidationError(
            "joined execution binding differs from the exact request or caller identity"
        )
    events_raw = _canonical_json_bytes(events)
    if (
        value["events_sha256"] != _sha256(events_raw)
        or type(value["events_byte_length"]) is not int
        or value["events_byte_length"] != len(events_raw)
    ):
        raise RealWorkerDumpValidationError(
            "joined execution binding differs from the canonical events member"
        )
    return JoinedExecutionBindingFacts(
        authorization_sha256=expected.authorization_sha256,
        prospective_run_id=expected.prospective_run_id,
        invocation_id_sha256=invocation_sha256,
        request_sha256=request_binding.request_sha256,
        request_byte_length=request_binding.request_byte_length,
        events_sha256=value["events_sha256"],
        events_byte_length=value["events_byte_length"],
    )


def _validate_billing_receipt(
    value: object,
    *,
    expected_context: Mapping[str, Any],
    expected_model_id: str,
) -> None:
    if type(value) is not dict or set(value) != _BILLING_RECEIPT_KEYS:
        raise RealWorkerDumpValidationError(
            "billing measurement receipt has invalid exact structure"
        )
    if len(_canonical_json_bytes(value)) > _MAX_BILLING_RECEIPT_BYTES:
        raise RealWorkerDumpValidationError(
            "billing measurement receipt exceeds 16,384 canonical bytes"
        )
    if value["schema_version"] != _BILLING_RECEIPT_SCHEMA:
        raise RealWorkerDumpValidationError("billing receipt schema version drifted")
    for field in (
        "key_id",
        "issuer",
        "tenant_id",
        "billing_account_id",
        "run_id",
        "worker_id",
        "provider_id",
    ):
        if type(value[field]) is not str or _SAFE_CONTEXT_ID_RE.fullmatch(value[field]) is None:
            raise RealWorkerDumpValidationError(
                f"billing receipt {field} is not a canonical identifier"
            )
    if any(
        value[field] != expected_context[field]
        for field in ("tenant_id", "billing_account_id", "run_id")
    ):
        raise RealWorkerDumpValidationError(
            "billing receipt contradicts the exact request billing context"
        )
    if (
        value["model_id"] != expected_model_id
        or type(value["model_id"]) is not str
        or _MODEL_ID_RE.fullmatch(value["model_id"]) is None
        or value["accelerator_type"] != "cuda"
    ):
        raise RealWorkerDumpValidationError(
            "billing receipt model or accelerator identity drifted"
        )
    accelerator_count = value["accelerator_count"]
    accelerator_milliseconds = value["accelerator_milliseconds"]
    if (
        type(accelerator_count) is not int
        or not 1 <= accelerator_count <= 128
        or type(accelerator_milliseconds) is not int
        or accelerator_milliseconds <= 0
    ):
        raise RealWorkerDumpValidationError(
            "billing receipt accelerator measurement is invalid"
        )
    started = _canonical_utc_time(
        value["measurement_started_at"], "measurement_started_at"
    )
    ended = _canonical_utc_time(value["measurement_ended_at"], "measurement_ended_at")
    issued = _canonical_utc_time(value["issued_at"], "issued_at")
    span = ended - started
    if span <= timedelta(0) or span > timedelta(hours=1):
        raise RealWorkerDumpValidationError(
            "billing receipt measurement window is invalid"
        )
    maximum_quantity = int(span.total_seconds() * 1000) * accelerator_count
    if accelerator_milliseconds > maximum_quantity:
        raise RealWorkerDumpValidationError(
            "billing receipt quantity exceeds its measured CUDA window"
        )
    if not ended <= issued <= ended + timedelta(minutes=1):
        raise RealWorkerDumpValidationError(
            "billing receipt issuance is outside the measured window"
        )
    if type(value["nonce"]) is not str or _NONCE_RE.fullmatch(value["nonce"]) is None:
        raise RealWorkerDumpValidationError("billing receipt nonce is invalid")
    if (
        type(value["payload_sha256"]) is not str
        or _LOWER_SHA256_RE.fullmatch(value["payload_sha256"]) is None
        or type(value["signature"]) is not str
        or _LOWER_SIGNATURE_RE.fullmatch(value["signature"]) is None
    ):
        raise RealWorkerDumpValidationError(
            "billing receipt digest or signature encoding is invalid"
        )
    unsigned = dict(value)
    unsigned.pop("signature")
    claimed_payload_sha256 = unsigned.pop("payload_sha256")
    expected_payload_sha256 = hashlib.sha256(_canonical_json_bytes(unsigned)).hexdigest()
    if claimed_payload_sha256 != expected_payload_sha256:
        raise RealWorkerDumpValidationError(
            "billing receipt payload digest does not match its exact fields"
        )


def _canonical_utc_time(value: object, field: str) -> datetime:
    if type(value) is not str or not value:
        raise RealWorkerDumpValidationError(f"billing receipt {field} is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RealWorkerDumpValidationError(
            f"billing receipt {field} is invalid"
        ) from exc
    if parsed.tzinfo is None:
        raise RealWorkerDumpValidationError(
            f"billing receipt {field} lacks a UTC offset"
        )
    normalized = parsed.astimezone(UTC)
    if value != normalized.isoformat():
        raise RealWorkerDumpValidationError(
            f"billing receipt {field} is not canonical UTC ISO-8601"
        )
    return normalized


def _validate_request(
    request: dict[str, Any], *, expected_manifest: ExpectedRealWorkerManifest
) -> None:
    keys = set(request)
    if not _REQUEST_REQUIRED_KEYS <= keys or keys - (
        _REQUEST_REQUIRED_KEYS | _REQUEST_OPTIONAL_KEYS
    ):
        raise RealWorkerDumpValidationError(
            "request top-level keys differ from the closed worker contract"
        )
    prompt = request["prompt"]
    if type(prompt) is not str or not 1 <= len(prompt) <= 4096:
        raise RealWorkerDumpValidationError("request prompt has an invalid type or length")
    if request["model_id"] != expected_manifest.model_id:
        raise RealWorkerDumpValidationError("request model_id differs from expected identity")
    max_new_tokens = request["max_new_tokens"]
    if type(max_new_tokens) is not int or not 1 <= max_new_tokens <= 128:
        raise RealWorkerDumpValidationError("request max_new_tokens is invalid")
    temperature = request["temperature"]
    if not _finite_number(temperature) or not 0.0 <= temperature <= 2.0:
        raise RealWorkerDumpValidationError("request temperature is invalid")
    seed = request.get("seed")
    if seed is not None and type(seed) is not int:
        raise RealWorkerDumpValidationError("request seed must be an integer or null")
    probes = request["probes"]
    if (
        type(probes) is not list
        or any(type(item) is not str or item not in _ALLOWED_PROBES for item in probes)
        or len(set(probes)) != len(probes)
    ):
        raise RealWorkerDumpValidationError("request probes are invalid or duplicated")
    if type(request["method_config"]) is not dict:
        raise RealWorkerDumpValidationError("request method_config must be an object")
    _validate_method_config(request["method_config"])

    enabled_methods = request["method_config"].get("enabled_methods") or []
    observation_only = (
        expected_manifest.hook_contract_profile
        == QWEN_OBSERVATION_ONLY_HOOK_PROFILE
    )
    if observation_only and "drive_local_eraser" in enabled_methods:
        raise RealWorkerDumpValidationError(
            "observation-only Qwen binding forbids drive_local_eraser"
        )
    if observation_only and "blindspot_detection" in enabled_methods:
        raise RealWorkerDumpValidationError(
            "observation-only Qwen binding forbids the legacy cover library"
        )
    if observation_only and not probes:
        raise RealWorkerDumpValidationError(
            "observation-only Qwen binding requires explicit probes"
        )
    if observation_only and {"blindspot_covers", "blindspots_f1"} & set(probes):
        raise RealWorkerDumpValidationError(
            "observation-only Qwen binding forbids Pythia cover probes"
        )

    target = request.get("ablation_target")
    if target is not None:
        if type(target) is not dict or set(target) != {"layer", "unit", "mode"}:
            raise RealWorkerDumpValidationError(
                "request ablation_target must use the exact target keys"
            )
        if (
            type(target["layer"]) is not int
            or target["layer"] < 0
            or type(target["unit"]) is not int
            or target["unit"] < 0
            or target["mode"] not in {"zero", "mean"}
        ):
            raise RealWorkerDumpValidationError("request ablation_target is invalid")
    if observation_only and (
        "causal_ablation" in probes or target is not None
    ):
        raise RealWorkerDumpValidationError(
            "observation-only Qwen binding forbids causal ablation"
        )

    billing = request.get("billing_measurement_context")
    if billing is not None:
        if type(billing) is not dict or set(billing) != {
            "tenant_id",
            "billing_account_id",
            "run_id",
        }:
            raise RealWorkerDumpValidationError(
                "request billing_measurement_context has invalid keys"
            )
        if any(
            type(billing[field]) is not str
            or _SAFE_CONTEXT_ID_RE.fullmatch(billing[field]) is None
            for field in billing
        ):
            raise RealWorkerDumpValidationError(
                "request billing_measurement_context has invalid identifiers"
            )


def _validate_method_config(config: dict[str, Any]) -> None:
    if set(config) - {"enabled_methods", "verification_mode", "mode", "knobs"}:
        raise RealWorkerDumpValidationError(
            "request method_config contains an unknown top-level control"
        )
    enabled = config.get("enabled_methods")
    if enabled is not None and (
        type(enabled) is not list
        or any(type(method) is not str or method not in _KNOWN_METHODS for method in enabled)
        or len(set(enabled)) != len(enabled)
    ):
        raise RealWorkerDumpValidationError("request enabled_methods are invalid")
    for field in ("verification_mode", "mode"):
        if field in config and not _bounded_text(config[field], maximum=128):
            raise RealWorkerDumpValidationError(
                f"request method_config {field} is invalid"
            )
    knobs = config.get("knobs")
    if knobs is None:
        return
    if type(knobs) is not dict or set(knobs) - _KNOWN_METHODS:
        raise RealWorkerDumpValidationError("request method knobs are invalid")
    allowed_fields = {
        "foundation_probe": {"top_k", "layer_range"},
        "rpm_gate_check": {"strictness_threshold"},
        "inversion_scan": {"severity_threshold"},
        "blindspot_detection": {"scope", "drive"},
        "verification_stack": {"mode", "verification_mode"},
        "drive_local_eraser": {"drive", "gain"},
    }
    for method, values in knobs.items():
        if type(values) is not dict or set(values) - allowed_fields[method]:
            raise RealWorkerDumpValidationError(
                f"request {method} knobs differ from the closed worker controls"
            )
    foundation = knobs.get("foundation_probe", {})
    if "top_k" in foundation and (
        type(foundation["top_k"]) is not int
        or not 1 <= foundation["top_k"] <= 128
    ):
        raise RealWorkerDumpValidationError("request foundation top_k is invalid")
    if "layer_range" in foundation and (
        type(foundation["layer_range"]) is not list
        or len(foundation["layer_range"]) > 128
        or any(
            type(layer) is not int or layer < 0 for layer in foundation["layer_range"]
        )
    ):
        raise RealWorkerDumpValidationError("request foundation layer_range is invalid")
    for method, field in (
        ("rpm_gate_check", "strictness_threshold"),
        ("inversion_scan", "severity_threshold"),
    ):
        values = knobs.get(method, {})
        if field in values and (
            not _finite_number(values[field]) or not 0.0 <= values[field] <= 1.0
        ):
            raise RealWorkerDumpValidationError(f"request {method} threshold is invalid")
    eraser = knobs.get("drive_local_eraser", {})
    if "gain" in eraser and (
        not _finite_number(eraser["gain"]) or not 0.0 <= eraser["gain"] <= 1.0
    ):
        raise RealWorkerDumpValidationError("request eraser gain is invalid")
    for method in ("drive_local_eraser", "blindspot_detection"):
        values = knobs.get(method, {})
        for field in ("drive", "scope"):
            if field in values and not _bounded_text(values[field], maximum=64):
                raise RealWorkerDumpValidationError(
                    f"request {method} {field} is invalid"
                )
    stack = knobs.get("verification_stack", {})
    for field in ("mode", "verification_mode"):
        if field in stack and not _bounded_text(stack[field], maximum=128):
            raise RealWorkerDumpValidationError(
                f"request verification_stack {field} is invalid"
            )


def _causal_request(
    request: Mapping[str, Any],
) -> tuple[bool, tuple[int, int], str]:
    target = request.get("ablation_target")
    requested = "causal_ablation" in request["probes"] or target is not None
    if isinstance(target, Mapping):
        return requested, (int(target["layer"]), int(target["unit"])), str(target["mode"])
    return requested, (0, 0), "zero"


def _validate_events(
    events: list[Any],
    *,
    expected_manifest: ExpectedRealWorkerManifest,
    request_payload: Mapping[str, Any],
    causal_requested: bool,
    expected_target: tuple[int, int],
    expected_mode: str,
) -> tuple[RealWorkerManifestFacts, Counter[str], str, int]:
    for event in events:
        if type(event) is not dict:
            raise RealWorkerDumpValidationError("every event must be an object")
        if type(event.get("type")) is not str or event["type"] not in _ALLOWED_EVENT_TYPES:
            raise RealWorkerDumpValidationError("worker dump contains an unknown event type")
        if set(event) != _EVENT_KEYS[event["type"]]:
            raise RealWorkerDumpValidationError(
                f"{event['type']} event differs from its exact worker schema"
            )

    types = [event["type"] for event in events]
    counts: Counter[str] = Counter(types)
    if types[0] != "manifest" or counts["manifest"] != 1:
        raise RealWorkerDumpValidationError(
            "worker dump must begin with exactly one manifest event"
        )
    if counts["complete"] != 1 or types[-1] != "complete":
        raise RealWorkerDumpValidationError(
            "worker dump must end with exactly one complete event"
        )
    if counts["error"]:
        raise RealWorkerDumpValidationError(
            "a successful worker dump cannot contain an error event"
        )
    if counts["word_spans"] != 1 or types[-2] != "word_spans":
        raise RealWorkerDumpValidationError(
            "worker dump must place exactly one word_spans event before complete"
        )
    if (
        counts["knob_resolution"] != 1
        or counts["neuron_covers"] != 1
        or types[1:3] != ["knob_resolution", "neuron_covers"]
    ):
        raise RealWorkerDumpValidationError(
            "worker dump must contain one ordered knob and cover prelude"
        )

    prior_phase = 0
    for event_type in types[1:-2]:
        phase = _EVENT_PHASE.get(event_type)
        if phase is None or phase < prior_phase:
            raise RealWorkerDumpValidationError("worker event phases are out of order")
        prior_phase = phase

    manifest_event = events[0]
    if set(manifest_event) != {"type", "manifest"} or type(
        manifest_event["manifest"]
    ) is not dict:
        raise RealWorkerDumpValidationError("manifest event has invalid exact structure")
    manifest_facts = _validate_manifest(
        manifest_event["manifest"],
        expected=expected_manifest,
        causal_requested=causal_requested,
    )
    _validate_knob_resolution(
        events[1],
        request_payload=request_payload,
        legacy_cover_library_available=(
            manifest_facts.legacy_cover_library_available
        ),
    )
    _validate_neuron_covers(
        events[2],
        request_payload=request_payload,
        manifest=manifest_facts,
    )

    token_events = [event for event in events if event["type"] == "token"]
    if not token_events:
        raise RealWorkerDumpValidationError(
            "a successful real-worker dump must contain at least one token"
        )
    observed_indices: list[int] = []
    output_parts: list[str] = []
    for event in token_events:
        token_index = event.get("token_index")
        token = event.get("token")
        if type(token_index) is not int or token_index < 0 or type(token) is not str:
            raise RealWorkerDumpValidationError("token event has invalid critical fields")
        _validate_token_event(
            event,
            request_payload=request_payload,
            manifest=manifest_facts,
        )
        observed_indices.append(token_index)
        output_parts.append(token)
    if observed_indices != list(range(len(token_events))):
        raise RealWorkerDumpValidationError(
            "token indices must be unique, contiguous, ordered, and zero-based"
        )
    output_text = "".join(output_parts)

    complete = events[-1]
    if set(complete) != {"type", "total_tokens"} or type(
        complete.get("total_tokens")
    ) is not int:
        raise RealWorkerDumpValidationError("complete event has invalid exact structure")
    if complete["total_tokens"] != len(token_events):
        raise RealWorkerDumpValidationError(
            "complete total_tokens differs from the contiguous token count"
        )
    _validate_word_spans(
        events[-2],
        token_events=token_events,
    )
    _validate_causal_events(
        events,
        requested=causal_requested,
        expected_target=expected_target,
        expected_mode=expected_mode,
        manifest=manifest_facts,
    )
    return manifest_facts, counts, output_text, len(token_events)


def _validate_manifest(
    manifest: dict[str, Any],
    *,
    expected: ExpectedRealWorkerManifest,
    causal_requested: bool,
) -> RealWorkerManifestFacts:
    if set(manifest) != _MANIFEST_KEYS:
        raise RealWorkerDumpValidationError("manifest keys differ from the exact contract")
    comparisons = {
        "model_id": expected.model_id,
        "requested_revision": expected.revision,
        "resolved_revision": expected.revision,
        "weights_filename": expected.weights_filename,
        "weights_sha256": expected.weights_sha256,
        "weights_bytes": expected.weights_bytes,
        "execution_kind": "real_model_weights",
        "model_identity_status": "PINNED_REVISION_AND_WEIGHTS_SHA256",
    }
    if any(manifest[field] != value for field, value in comparisons.items()):
        raise RealWorkerDumpValidationError("manifest model artifact identity drifted")
    if any(
        manifest[field] is not True
        for field in (
            "revision_verified",
            "weights_hash_verified",
            "is_real_model",
        )
    ):
        raise RealWorkerDumpValidationError("manifest real-model verification flags are false")
    if not _bounded_text(manifest["tokenizer_id"], maximum=512) or not _bounded_text(
        manifest["worker_version"], maximum=256
    ):
        raise RealWorkerDumpValidationError("manifest tokenizer or worker version is invalid")

    arch = manifest["model_arch"]
    if type(arch) is not dict or set(arch) != _MODEL_ARCH_KEYS:
        raise RealWorkerDumpValidationError("manifest model_arch has invalid exact structure")
    if not _bounded_text(arch["family"], maximum=128) or arch["validated"] is not True:
        raise RealWorkerDumpValidationError("manifest model_arch is not validated")
    if any(
        type(arch[field]) is not int or arch[field] <= 0
        for field in (
            "n_layers",
            "hidden_size",
            "mlp_intermediate_dim",
            "n_heads",
            "total_params",
        )
    ):
        raise RealWorkerDumpValidationError("manifest model_arch dimensions are invalid")

    if expected.hook_contract_profile == QWEN_OBSERVATION_ONLY_HOOK_PROFILE:
        if manifest["tokenizer_id"] != _QWEN_OBSERVATION_ONLY_TOKENIZER_ID:
            raise RealWorkerDumpValidationError(
                "Qwen observation manifest tokenizer identity drifted"
            )
        if arch != dict(_QWEN_OBSERVATION_ONLY_ARCH):
            raise RealWorkerDumpValidationError(
                "Qwen observation manifest architecture drifted"
            )

    hooks = manifest["supported_hooks"]
    if (
        type(hooks) is not list
        or any(type(item) is not str or item not in _SUPPORTED_HOOKS for item in hooks)
        or len(set(hooks)) != len(hooks)
    ):
        raise RealWorkerDumpValidationError("manifest supported_hooks are invalid")
    if (
        expected.hook_contract_profile == QWEN_OBSERVATION_ONLY_HOOK_PROFILE
        and hooks != list(_QWEN_OBSERVATION_ONLY_SUPPORTED_HOOKS)
    ):
        raise RealWorkerDumpValidationError(
            "Qwen observation manifest supported hooks drifted"
        )
    if causal_requested and not {
        "mlp_intermediate_post_activation",
        "logits",
    } <= set(hooks):
        raise RealWorkerDumpValidationError(
            "manifest lacks hooks required by the requested causal ablation"
        )
    hook_contract = manifest["intervention_hook_contract"]
    expected_hook_contract = _HOOK_CONTRACTS[expected.hook_contract_profile]
    if type(hook_contract) is not dict or hook_contract != expected_hook_contract:
        raise RealWorkerDumpValidationError("manifest intervention hook contract drifted")

    runtime = manifest["runtime_execution"]
    if type(runtime) is not dict or set(runtime) != _RUNTIME_KEYS:
        raise RealWorkerDumpValidationError("manifest runtime evidence has invalid keys")
    required_runtime = {
        "profile": "production",
        "device": "cuda",
        "dtype": "torch.bfloat16",
        "torch_version": "2.13.0+cu126",
        "torch_native_jit_disabled": True,
        "cuda_bfloat16_supported": True,
        "cuda_runtime_version": "12.6",
    }
    if any(runtime[field] != value for field, value in required_runtime.items()):
        raise RealWorkerDumpValidationError("manifest production CUDA runtime drifted")
    driver = runtime["cuda_driver_version"]
    if type(driver) is not int or driver < 12060:
        raise RealWorkerDumpValidationError("manifest CUDA driver is below the 12.6 floor")
    for field in ("cuda_device_name", "cuda_device_capability"):
        if not _bounded_text(runtime[field], maximum=256):
            raise RealWorkerDumpValidationError("manifest CUDA device evidence is invalid")
    return RealWorkerManifestFacts(
        model_id=expected.model_id,
        revision=expected.revision,
        weights_filename=expected.weights_filename,
        weights_sha256=expected.weights_sha256,
        weights_bytes=expected.weights_bytes,
        worker_version=manifest["worker_version"],
        torch_version=runtime["torch_version"],
        cuda_runtime_version=runtime["cuda_runtime_version"],
        cuda_driver_version=driver,
        cuda_device_name=runtime["cuda_device_name"],
        cuda_device_capability=runtime["cuda_device_capability"],
        supported_hooks=tuple(hooks),
        n_layers=arch["n_layers"],
        hidden_size=arch["hidden_size"],
        mlp_intermediate_dim=arch["mlp_intermediate_dim"],
        n_heads=arch["n_heads"],
        hook_contract_profile=expected.hook_contract_profile,
        intervention_available=(
            expected.hook_contract_profile == PYTHIA_STAGE27F_HOOK_PROFILE
        ),
        legacy_cover_library_available=(
            expected.hook_contract_profile == PYTHIA_STAGE27F_HOOK_PROFILE
        ),
    )


def _validate_knob_resolution(
    event: Mapping[str, Any],
    *,
    request_payload: Mapping[str, Any],
    legacy_cover_library_available: bool,
) -> None:
    resolved = event["resolved_knobs"]
    expected = _expected_resolved_knobs(
        request_payload,
        legacy_cover_library_available=legacy_cover_library_available,
    )
    if type(resolved) is not dict or not _exact_json_equal(resolved, expected):
        raise RealWorkerDumpValidationError(
            "knob_resolution differs from the request's exact worker resolution"
        )


def _expected_resolved_knobs(
    request_payload: Mapping[str, Any],
    *,
    legacy_cover_library_available: bool = True,
) -> dict[str, dict[str, Any]]:
    config = request_payload["method_config"]
    knobs_value = config.get("knobs", {}) if isinstance(config, Mapping) else {}
    knobs = knobs_value if isinstance(knobs_value, Mapping) else {}
    enabled_value = config.get("enabled_methods", ()) if isinstance(config, Mapping) else ()
    enabled = set(enabled_value) if isinstance(enabled_value, (list, tuple)) else set()

    foundation = _mapping_or_empty(knobs.get("foundation_probe"))
    rpm = _mapping_or_empty(knobs.get("rpm_gate_check"))
    inversion = _mapping_or_empty(knobs.get("inversion_scan"))
    eraser = _mapping_or_empty(knobs.get("drive_local_eraser"))
    blindspot = _mapping_or_empty(knobs.get("blindspot_detection"))

    drive = _resolved_drive(eraser.get("drive"))
    blindspot_raw = blindspot.get("scope") or blindspot.get("drive")
    if blindspot_raw == "all_7":
        blindspot_result = {
            "scope": "all_7",
            "drive": "all_7",
            "cover_available": legacy_cover_library_available,
        }
    else:
        blindspot_drive = _resolved_drive(blindspot_raw)
        blindspot_result = {
            "scope": blindspot_drive,
            "drive": blindspot_drive,
            "cover_available": (
                legacy_cover_library_available
                and blindspot_drive in _KNOWN_DRIVES
            ),
        }
    return {
        "foundation_probe": {
            "top_k": _resolved_positive_int(foundation.get("top_k"), default=8),
            "layer_range": _resolved_layer_range(foundation.get("layer_range")),
        },
        "rpm_gate_check": {
            "strictness_threshold": _resolved_unit_float(
                rpm.get("strictness_threshold")
            )
        },
        "inversion_scan": {
            "severity_threshold": _resolved_unit_float(
                inversion.get("severity_threshold")
            ),
            "active": "inversion_scan" in enabled,
        },
        "drive_local_eraser": {
            "drive": drive,
            "gain": _resolved_nonnegative_float(eraser.get("gain"), default=1.0),
            "cover_available": (
                legacy_cover_library_available and drive in _KNOWN_DRIVES
            ),
            "active": "drive_local_eraser" in enabled,
        },
        "blindspot_detection": blindspot_result,
    }


def _mapping_or_empty(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else MappingProxyType({})


def _resolved_positive_int(value: object, *, default: int) -> int:
    try:
        parsed = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if parsed > 0 else default


def _resolved_layer_range(value: object) -> list[int]:
    if not isinstance(value, (list, tuple)):
        return []
    if len(value) == 2 and all(type(item) in (int, float) for item in value):
        low, high = int(value[0]), int(value[1])
        return list(range(max(0, low), high + 1)) if low <= high else []
    resolved: list[int] = []
    for item in value:
        try:
            parsed = int(item)
        except (TypeError, ValueError, OverflowError):
            continue
        if parsed >= 0:
            resolved.append(parsed)
    return sorted(set(resolved))


def _resolved_unit_float(value: object) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return max(0.0, min(1.0, parsed))


def _resolved_nonnegative_float(value: object, *, default: float) -> float:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return default
    return max(0.0, parsed)


def _resolved_drive(value: object) -> str:
    return value if type(value) is str and value.startswith("F") else "F1"


def _resolved_probes(request_payload: Mapping[str, Any]) -> frozenset[str]:
    probes = request_payload["probes"]
    config = request_payload["method_config"]
    if not probes:
        if isinstance(config, Mapping) and config and "enabled_methods" in config:
            return frozenset()
        return frozenset(
            {
                "active_trace",
                "blindspot_covers",
                "mode7_attribution",
                "confidence_margin",
            }
        )
    return frozenset(
        "blindspot_covers" if probe == "blindspots_f1" else probe for probe in probes
    )


def _validate_neuron_covers(
    event: Mapping[str, Any],
    *,
    request_payload: Mapping[str, Any],
    manifest: RealWorkerManifestFacts,
) -> None:
    covers = event["per_class_neuron_covers"]
    if type(covers) is not dict:
        raise RealWorkerDumpValidationError("neuron_covers payload must be an object")
    probes = _resolved_probes(request_payload)
    if not manifest.legacy_cover_library_available:
        if covers:
            raise RealWorkerDumpValidationError(
                "observation-only model emitted legacy Pythia neuron covers"
            )
        return
    if "blindspot_covers" not in probes:
        if covers:
            raise RealWorkerDumpValidationError(
                "worker emitted neuron covers when that probe was not requested"
            )
        return
    scope = _expected_resolved_knobs(request_payload)["blindspot_detection"]["scope"]
    if scope == "all_7":
        expected_classes = {
            f"F{drive}{suffix}"
            for drive in range(1, 8)
            for suffix in ("A", "T", "f", "E")
        }
    elif scope in _KNOWN_DRIVES:
        expected_classes = {f"{scope}{suffix}" for suffix in ("A", "T", "f", "E")}
    else:
        expected_classes = set()
    if set(covers) != expected_classes:
        raise RealWorkerDumpValidationError(
            "neuron cover classes differ from the resolved blindspot scope"
        )
    for class_name, members in covers.items():
        if type(members) is not list or not members:
            raise RealWorkerDumpValidationError(
                f"neuron cover {class_name} must contain calibrated members"
            )
        seen_labels: set[str] = set()
        for member in members:
            if type(member) is not dict or set(member) != _COVER_MEMBER_KEYS:
                raise RealWorkerDumpValidationError(
                    "neuron cover member differs from its exact schema"
                )
            label = member["label"]
            match = _COORDINATE_LABEL_RE.fullmatch(label) if type(label) is str else None
            if match is None:
                raise RealWorkerDumpValidationError("neuron cover label is invalid")
            layer, unit = int(match.group(1)), int(match.group(2))
            if (
                layer >= manifest.n_layers
                or unit >= manifest.mlp_intermediate_dim
                or label in seen_labels
            ):
                raise RealWorkerDumpValidationError(
                    "neuron cover coordinate is duplicated or out of range"
                )
            seen_labels.add(label)
            confidence = member["confidence"]
            if confidence is not None and (
                not _finite_number(confidence) or not 0.0 <= confidence <= 1.0
            ):
                raise RealWorkerDumpValidationError("neuron cover confidence is invalid")
            expected_band = _confidence_band(confidence)
            evidence_sources = member["evidence_sources"]
            if (
                member["confidence_band"] != expected_band
                or type(evidence_sources) is not list
                or any(
                    type(source) is not str or not _bounded_text(source, maximum=256)
                    for source in evidence_sources
                )
            ):
                raise RealWorkerDumpValidationError(
                    "neuron cover band or evidence sources are invalid"
                )


def _confidence_band(value: object) -> str:
    if not _finite_number(value):
        return "unavailable"
    if 0.80 <= value <= 0.95:
        return "high"
    if 0.60 <= value < 0.80:
        return "medium"
    if 0.40 <= value < 0.60:
        return "low"
    return "unavailable"


def _validate_token_event(
    event: Mapping[str, Any],
    *,
    request_payload: Mapping[str, Any],
    manifest: RealWorkerManifestFacts,
) -> None:
    token_index = event["token_index"]
    probes = _resolved_probes(request_payload)
    resolved = _expected_resolved_knobs(request_payload)
    activations = event["top_activated_neurons"]
    if type(activations) is not list:
        raise RealWorkerDumpValidationError("token activations must be an array")
    if "active_trace" not in probes:
        if activations:
            raise RealWorkerDumpValidationError(
                "token emitted activations without the active_trace probe"
            )
    else:
        top_k = resolved["foundation_probe"]["top_k"]
        if len(activations) != top_k:
            raise RealWorkerDumpValidationError(
                "token activation count differs from resolved foundation top_k"
            )
    layer_filter = set(resolved["foundation_probe"]["layer_range"])
    seen_activations: set[tuple[int, int]] = set()
    for activation in activations:
        if type(activation) is not dict or set(activation) != _TOKEN_ACTIVATION_KEYS:
            raise RealWorkerDumpValidationError(
                "token activation differs from its exact schema"
            )
        layer = activation["layer"]
        unit = activation["index"]
        coordinate = (layer, unit)
        if (
            type(layer) is not int
            or not 0 <= layer < manifest.n_layers
            or (layer_filter and layer not in layer_filter)
            or type(unit) is not int
            or not 0 <= unit < manifest.mlp_intermediate_dim
            or not _finite_number(activation["activation"])
            or coordinate in seen_activations
        ):
            raise RealWorkerDumpValidationError(
                "token activation is duplicated, nonfinite, or out of range"
            )
        seen_activations.add(coordinate)

    edges = event["mode7_attribution"]
    if type(edges) is not list:
        raise RealWorkerDumpValidationError("token Mode-7 attribution must be an array")
    if "mode7_attribution" not in probes and edges:
        raise RealWorkerDumpValidationError(
            "token emitted Mode-7 edges without that probe"
        )
    if "mode7_attribution" in probes and token_index == 0 and not edges:
        raise RealWorkerDumpValidationError("first token lacks its Mode-7 root edge")
    rpm_threshold = resolved["rpm_gate_check"]["strictness_threshold"]
    seen_sources: set[int | None] = set()
    for edge in edges:
        if type(edge) is not dict or set(edge) != _MODE7_EDGE_KEYS:
            raise RealWorkerDumpValidationError("Mode-7 edge differs from its exact schema")
        source = edge["from_token_index"]
        weight = edge["weight"]
        if (
            (source is not None and (type(source) is not int or not 0 <= source < token_index))
            or (source is None and token_index != 0)
            or edge["to_token_index"] != token_index
            or source in seen_sources
            or not _finite_number(weight)
            or not rpm_threshold <= weight <= 1.0
        ):
            raise RealWorkerDumpValidationError("Mode-7 edge is invalid or misbound")
        seen_sources.add(source)

    confidence = event["confidence"]
    if "confidence_margin" in probes:
        if not _finite_number(confidence) or not 0.0 <= confidence <= 1.0:
            raise RealWorkerDumpValidationError("token confidence is unavailable or invalid")
    elif confidence is not None:
        raise RealWorkerDumpValidationError(
            "token emitted confidence without the confidence probe"
        )
    inversion = event["inversion_risk"]
    inversion_knob = resolved["inversion_scan"]
    if inversion_knob["active"]:
        if (
            not _finite_number(inversion)
            or not 0.0 <= inversion <= 1.0
            or (inversion != 0.0 and inversion < inversion_knob["severity_threshold"])
        ):
            raise RealWorkerDumpValidationError("token inversion-risk telemetry is invalid")
    elif inversion is not None:
        raise RealWorkerDumpValidationError(
            "token emitted inversion risk while the method was inactive"
        )
    _validate_verification_telemetry(event, request_payload=request_payload)
    _validate_intervention_result(
        event["eraser_intervention_result"],
        resolved_eraser=resolved["drive_local_eraser"],
        manifest=manifest,
    )


def _validate_verification_telemetry(
    event: Mapping[str, Any], *, request_payload: Mapping[str, Any]
) -> None:
    fields = (
        "verification_mode",
        "verification_verdict",
        "verification_threshold",
        "verification_score",
        "verification_score_source",
        "verification_invalid_mode",
    )
    config = request_payload["method_config"]
    enabled = config.get("enabled_methods", ()) if isinstance(config, Mapping) else ()
    knobs = config.get("knobs", {}) if isinstance(config, Mapping) else {}
    requested = (
        "verification_stack" in enabled
        or (isinstance(config, Mapping) and ("verification_mode" in config or "mode" in config))
        or (isinstance(knobs, Mapping) and "verification_stack" in knobs)
    )
    if not requested:
        if any(event[field] is not None for field in fields):
            raise RealWorkerDumpValidationError(
                "token emitted verification telemetry when it was not requested"
            )
        return
    mode, invalid_mode = _resolved_verification_mode(config)
    accept, flag = _VERIFICATION_THRESHOLDS[mode]
    score = event["verification_score"]
    if score is not None and (not _finite_number(score) or not 0.0 <= score <= 1.0):
        raise RealWorkerDumpValidationError("token verification score is invalid")
    expected_verdict = (
        "FLAG"
        if score is None
        else "ACCEPT"
        if score >= accept
        else "FLAG"
        if score >= flag
        else "SUPPRESS"
    )
    source = event["verification_score_source"]
    if (
        event["verification_mode"] != mode
        or event["verification_threshold"] != accept
        or event["verification_verdict"] != expected_verdict
        or event["verification_invalid_mode"] != invalid_mode
        or source not in {"confidence", "proxy_confidence", "unavailable"}
        or (score is None) != (source == "unavailable")
    ):
        raise RealWorkerDumpValidationError(
            "token verification verdict contradicts its requested mode or score"
        )
    confidence = event["confidence"]
    if source == "confidence" and confidence is not None and score != round(confidence, 3):
        raise RealWorkerDumpValidationError(
            "token verification score differs from emitted confidence"
        )


def _resolved_verification_mode(config: Mapping[str, Any]) -> tuple[str, str | None]:
    raw_mode: object = None
    knobs = config.get("knobs")
    if isinstance(knobs, Mapping):
        stack = knobs.get("verification_stack")
        if isinstance(stack, Mapping):
            raw_mode = stack.get("mode", stack.get("verification_mode"))
    if raw_mode is None:
        raw_mode = config.get("verification_mode", config.get("mode"))
    if raw_mode is None:
        return "BALANCED", None
    normalized = str(raw_mode).strip().upper().replace("-", "_").replace(" ", "_")
    if normalized in _VERIFICATION_THRESHOLDS:
        return normalized, None
    return "HIGH_PRECISION", str(raw_mode)


def _validate_intervention_result(
    value: object,
    *,
    resolved_eraser: Mapping[str, Any],
    manifest: RealWorkerManifestFacts,
) -> None:
    if not resolved_eraser["active"]:
        if value is not None:
            raise RealWorkerDumpValidationError(
                "token emitted an intervention receipt while eraser was inactive"
            )
        return
    if type(value) is not dict or set(value) != _INTERVENTION_KEYS:
        raise RealWorkerDumpValidationError(
            "active eraser token lacks its exact intervention receipt"
        )
    constants = {
        "contract_version": "harness_v2.mlp_intermediate_eraser.v2",
        "method_id": "drive_local_eraser",
        "execution_kind": "real_model_weights",
        "source_kind": "stage27f_calibrated_cover",
        "structurally_valid": False,
        "coordinate_space": "mlp_intermediate_post_activation",
        "hook_semantics": (
            "gpt_neox.layers[{layer}].mlp.dense_4h_to_h:"
            "forward_pre_hook.input[0]"
        ),
        "token_selection": "batch_0_last_sequence_position",
        "expected_coordinate_width": manifest.mlp_intermediate_dim,
        "expected_projected_output_width": manifest.hidden_size,
    }
    if any(value[field] != expected for field, expected in constants.items()):
        raise RealWorkerDumpValidationError("intervention receipt contract drifted")
    if value["structural_status"] not in _INTERVENTION_STATUSES:
        raise RealWorkerDumpValidationError("intervention structural status is invalid")
    requested_gain = value["requested_gain"]
    effective_gain = value["effective_gain"]
    if (
        not _finite_number(requested_gain)
        or requested_gain != resolved_eraser["gain"]
        or not _finite_number(effective_gain)
        or effective_gain != min(1.0, requested_gain)
    ):
        raise RealWorkerDumpValidationError(
            "intervention gain differs from the resolved eraser request"
        )
    if any(
        type(value[field]) is not bool
        for field in ("hook_fired", "stability_control_performed")
    ) or any(
        value[field] is not None and type(value[field]) is not bool
        for field in (
            "activation_changed",
            "output_changed",
            "baseline_output_stable",
            "baseline_geometry_stable",
        )
    ):
        raise RealWorkerDumpValidationError("intervention boolean evidence is invalid")
    if not _bounded_text(value["detail"], maximum=4096):
        raise RealWorkerDumpValidationError("intervention detail is invalid")

    coordinate_lists: dict[str, list[Any]] = {}
    coordinate_sets: dict[str, set[tuple[int, int, str]]] = {}
    for field in (
        "requested_coordinates",
        "valid_coordinates",
        "invalid_coordinates",
        "applied_coordinates",
    ):
        items = value[field]
        if type(items) is not list:
            raise RealWorkerDumpValidationError("intervention coordinates must be arrays")
        coordinate_lists[field] = items
        keys: set[tuple[int, int, str]] = set()
        for item in items:
            if type(item) is not dict or set(item) != _INTERVENTION_COORDINATE_KEYS:
                raise RealWorkerDumpValidationError(
                    "intervention coordinate differs from its exact schema"
                )
            layer, unit, space = item["layer"], item["index"], item["coordinate_space"]
            key = (layer, unit, space)
            if (
                type(layer) is not int
                or type(unit) is not int
                or type(space) is not str
                or not space
                or key in keys
            ):
                raise RealWorkerDumpValidationError(
                    "intervention coordinate is invalid or duplicated"
                )
            keys.add(key)
        coordinate_sets[field] = keys
    requested = coordinate_sets["requested_coordinates"]
    valid = coordinate_sets["valid_coordinates"]
    invalid = coordinate_sets["invalid_coordinates"]
    applied = coordinate_sets["applied_coordinates"]
    if (
        valid | invalid != requested
        or valid & invalid
        or not applied <= valid
        or any(
            not 0 <= layer < manifest.n_layers
            or not 0 <= unit < manifest.mlp_intermediate_dim
            or space != "mlp_intermediate_post_activation"
            for layer, unit, space in valid | applied
        )
    ):
        raise RealWorkerDumpValidationError(
            "intervention coordinate partition or range is invalid"
        )
    required_layers = value["required_hook_layers"]
    fired_layers = value["hook_fired_layers"]
    if (
        type(required_layers) is not list
        or type(fired_layers) is not list
        or any(type(layer) is not int for layer in required_layers + fired_layers)
        or len(set(required_layers)) != len(required_layers)
        or len(set(fired_layers)) != len(fired_layers)
        or set(required_layers)
        != {layer for layer, _unit, _space in requested if layer >= 0}
        or value["hook_fired"]
        != (bool(required_layers) and set(required_layers) <= set(fired_layers))
    ):
        raise RealWorkerDumpValidationError("intervention hook-layer evidence is invalid")
    observed_geometry = _validate_geometry_list(
        value["observed_tensor_geometry"],
        expected_phase="intervention_attempt",
        manifest=manifest,
    )
    reference_geometry = _validate_geometry_list(
        value["reference_tensor_geometry"],
        expected_phase="unmodified_forward",
        manifest=manifest,
    )
    stability_geometry = _validate_geometry_list(
        value["stability_control_tensor_geometry"],
        expected_phase="unmodified_forward",
        manifest=manifest,
    )
    if value["structural_status"] == "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED":
        if not (
            value["hook_fired"]
            and value["activation_changed"] is True
            and value["output_changed"] is True
            and applied
            and not invalid
            and value["stability_control_performed"]
            and value["baseline_output_stable"] is True
            and value["baseline_geometry_stable"] is True
        ):
            raise RealWorkerDumpValidationError(
                "unattributed intervention delta lacks required structural controls"
            )
        required_set = set(required_layers)
        if (
            set(observed_geometry) != required_set
            or set(reference_geometry) != required_set
            or set(stability_geometry) != required_set
            or any(
                not observed_geometry[layer]["all_finite"]
                or observed_geometry[layer]["hook_call_count"] != 1
                or not reference_geometry[layer]["all_finite"]
                or reference_geometry[layer]["hook_call_count"] != 1
                or not stability_geometry[layer]["all_finite"]
                or stability_geometry[layer]["hook_call_count"] != 1
                or not _paired_geometry_equal(
                    reference_geometry[layer], stability_geometry[layer]
                )
                or not _paired_geometry_equal(
                    reference_geometry[layer], observed_geometry[layer]
                )
                for layer in required_set
            )
        ):
            raise RealWorkerDumpValidationError(
                "unattributed intervention delta lacks exact paired geometry"
            )
    if value["structural_status"].startswith("REJECTED_") and applied:
        raise RealWorkerDumpValidationError(
            "a rejected intervention cannot report applied coordinates"
        )


def _validate_geometry_list(
    value: object,
    *,
    expected_phase: str,
    manifest: RealWorkerManifestFacts,
) -> dict[int, dict[str, Any]]:
    if type(value) is not list:
        raise RealWorkerDumpValidationError("intervention geometry must be an array")
    seen_layers: set[int] = set()
    by_layer: dict[int, dict[str, Any]] = {}
    for geometry in value:
        if type(geometry) is not dict or set(geometry) != _INTERVENTION_GEOMETRY_KEYS:
            raise RealWorkerDumpValidationError(
                "intervention geometry differs from its exact schema"
            )
        layer = geometry["layer"]
        shape = geometry["shape"]
        if (
            type(layer) is not int
            or not 0 <= layer < manifest.n_layers
            or layer in seen_layers
            or type(shape) is not list
            or not shape
            or any(type(dimension) is not int or dimension < 1 for dimension in shape)
            or geometry["rank"] != len(shape)
            or geometry["width"] != shape[-1]
            or geometry["width"] != manifest.mlp_intermediate_dim
            or geometry["projected_output_width"] != manifest.hidden_size
            or geometry["coordinate_space"] != "mlp_intermediate_post_activation"
            or geometry["observation_phase"] != expected_phase
            or geometry["hook_module_path"]
            != f"gpt_neox.layers[{layer}].mlp.dense_4h_to_h"
            or geometry["tensor_role"] != "forward_pre_hook.input[0]"
            or not _bounded_text(geometry["dtype"], maximum=128)
            or not _bounded_text(geometry["device"], maximum=128)
            or type(geometry["all_finite"]) is not bool
            or type(geometry["hook_call_count"]) is not int
            or geometry["hook_call_count"] < 1
        ):
            raise RealWorkerDumpValidationError("intervention geometry is invalid")
        for digest_field in ("rng_state_sha256", "rng_state_after_sha256"):
            digest = geometry[digest_field]
            if digest != "UNAVAILABLE" and (
                type(digest) is not str or _LOWER_SHA256_RE.fullmatch(digest) is None
            ):
                raise RealWorkerDumpValidationError(
                    "intervention RNG identity is invalid"
                )
        seen_layers.add(layer)
        by_layer[layer] = geometry
    return by_layer


def _paired_geometry_equal(
    reference: Mapping[str, Any], observed: Mapping[str, Any]
) -> bool:
    normalized = dict(observed)
    normalized["observation_phase"] = "unmodified_forward"
    return _exact_json_equal(dict(reference), normalized)


def _validate_word_spans(
    event: dict[str, Any], *, token_events: list[dict[str, Any]]
) -> None:
    expected = _expected_word_spans(token_events)
    if not _exact_json_equal(event, expected):
        raise RealWorkerDumpValidationError(
            "word_spans differs from deterministic token-text reconstruction"
        )


def _expected_word_spans(token_events: list[dict[str, Any]]) -> dict[str, Any]:
    token_ranges: list[tuple[int, int, int, str]] = []
    cursor = 0
    for event in token_events:
        token = event["token"]
        start = cursor
        cursor += len(token)
        token_ranges.append((event["token_index"], start, cursor, token))
    output_text = "".join(item[3] for item in token_ranges)

    raw_runs: list[tuple[int, int]] = []
    index = 0
    while index < len(output_text):
        if output_text[index].isspace():
            index += 1
            continue
        start = index
        while index < len(output_text) and not output_text[index].isspace():
            index += 1
        raw_runs.append((start, index))

    structural: list[int] = []
    token_to_runs: dict[int, list[int]] = {}
    for token_index, token_start, token_end, token in token_ranges:
        if token == "" or token.isspace():
            structural.append(token_index)
            continue
        overlaps: list[int] = []
        for run_index, (run_start, run_end) in enumerate(raw_runs):
            if run_end <= token_start:
                continue
            if run_start >= token_end:
                break
            if max(token_start, run_start) < min(token_end, run_end):
                overlaps.append(run_index)
        token_to_runs[token_index] = overlaps

    parents = list(range(len(raw_runs)))

    def find(item: int) -> int:
        while parents[item] != item:
            parents[item] = parents[parents[item]]
            item = parents[item]
        return item

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parents[max(left_root, right_root)] = min(left_root, right_root)

    for overlaps in token_to_runs.values():
        for offset in range(1, len(overlaps)):
            union(overlaps[0], overlaps[offset])

    root_members: dict[int, list[int]] = {}
    for run_index in range(len(raw_runs)):
        root_members.setdefault(find(run_index), []).append(run_index)
    ordered_roots: list[int] = []
    for run_index in range(len(raw_runs)):
        root = find(run_index)
        if root not in ordered_roots:
            ordered_roots.append(root)

    span_for_run: dict[int, int] = {}
    span_specs: list[tuple[str, int, int]] = []
    for span_index, root in enumerate(ordered_roots):
        members = root_members[root]
        start = raw_runs[members[0]][0]
        end = raw_runs[members[-1]][1]
        span_specs.append((output_text[start:end], start, end))
        for run_index in members:
            span_for_run[run_index] = span_index
    token_indices: list[list[int]] = [[] for _ in span_specs]
    for token_index, _start, _end, token in token_ranges:
        if token == "" or token.isspace():
            continue
        overlaps = token_to_runs[token_index]
        if not overlaps:
            structural.append(token_index)
            continue
        token_indices[span_for_run[overlaps[0]]].append(token_index)
    spans = [
        {
            "word": word,
            "token_indices": indices,
            "char_start": start,
            "char_end": end,
        }
        for (word, start, end), indices in zip(span_specs, token_indices)
        if indices
    ]
    return {
        "type": "word_spans",
        "spans": spans,
        "structural_token_indices": structural,
        "total_tokens_covered": len(token_events),
    }


def _validate_causal_events(
    events: list[dict[str, Any]],
    *,
    requested: bool,
    expected_target: tuple[int, int],
    expected_mode: str,
    manifest: RealWorkerManifestFacts,
) -> None:
    effects = [event for event in events if event["type"] == "ablation_effect"]
    controls = [
        event for event in events if event["type"] == "ablation_control_effect"
    ]
    if not requested:
        if effects or controls:
            raise RealWorkerDumpValidationError(
                "worker emitted causal events that were not requested"
            )
        return
    if len(effects) != 1 or len(controls) != 1:
        raise RealWorkerDumpValidationError(
            "requested causal ablation requires one effect and one matched control"
        )
    if events.index(effects[0]) >= events.index(controls[0]):
        raise RealWorkerDumpValidationError(
            "causal effect must precede its matched-control event"
        )
    _validate_event_target(
        effects[0], expected_target=expected_target, expected_mode=expected_mode
    )
    _validate_event_target(
        controls[0], expected_target=expected_target, expected_mode=expected_mode
    )
    if not (
        0 <= expected_target[0] < manifest.n_layers
        and 0 <= expected_target[1] < manifest.mlp_intermediate_dim
    ):
        raise RealWorkerDumpValidationError(
            "requested causal target is outside the declared model geometry"
        )
    effect = effects[0]
    baseline_token = effect["baseline_top_token"]
    ablated_token = effect["ablated_top_token"]
    baseline_id = effect["baseline_top_token_id"]
    ablated_id = effect["ablated_top_token_id"]
    if (
        effect["is_real_model"] is not True
        or type(baseline_token) is not str
        or type(ablated_token) is not str
        or type(baseline_id) is not int
        or baseline_id < 0
        or type(ablated_id) is not int
        or ablated_id < 0
        or not _finite_number(effect["logit_delta"])
        or not _finite_number(effect["confidence_delta"])
        or not -1.0 <= effect["confidence_delta"] <= 1.0
        or type(effect["top_token_changed"]) is not bool
        or effect["top_token_changed"] != (baseline_id != ablated_id)
        or (baseline_id != ablated_id) != (baseline_token != ablated_token)
        or not _bounded_text(effect["detail"], maximum=4096)
    ):
        raise RealWorkerDumpValidationError(
            "causal effect lacks a finite real-model measurement"
        )
    control = controls[0]
    n_controls = control["n_controls"]
    units = control["control_units"]
    target_abs = control["target_abs_logit_delta"]
    control_mean = control["control_mean_abs_logit_delta"]
    control_max = control["control_max_abs_logit_delta"]
    margin = control["margin_over_control_max"]
    if (
        control["is_real_model"] is not True
        or type(n_controls) is not int
        or n_controls < 1
        or type(units) is not list
        or len(units) != n_controls
        or any(
            type(unit) is not int
            or not 0 <= unit < manifest.mlp_intermediate_dim
            or unit == expected_target[1]
            for unit in units
        )
        or units != sorted(units)
        or len(set(units)) != len(units)
        or type(control["selectivity_passed"]) is not bool
        or type(control["seed"]) is not int
        or not _bounded_text(control["detail"], maximum=4096)
        or any(
            not _finite_number(value)
            for value in (target_abs, control_mean, control_max, margin)
        )
        or min(target_abs, control_mean, control_max) < 0.0
        or control_mean > control_max + 0.0002
        or not math.isclose(
            margin,
            target_abs - control_max,
            rel_tol=0.0,
            abs_tol=0.0002,
        )
        or not math.isclose(
            target_abs,
            abs(effect["logit_delta"]),
            rel_tol=0.0,
            abs_tol=0.0002,
        )
    ):
        raise RealWorkerDumpValidationError(
            "matched control lacks a finite real-model measurement"
        )
    if abs(target_abs - control_max) > 0.0002 and control[
        "selectivity_passed"
    ] != (target_abs > control_max):
        raise RealWorkerDumpValidationError(
            "matched-control selectivity contradicts its measured deltas"
        )


def _validate_event_target(
    event: Mapping[str, Any], *, expected_target: tuple[int, int], expected_mode: str
) -> None:
    target = event.get("target")
    if (
        type(target) is not dict
        or set(target) != {"layer", "unit"}
        or type(target.get("layer")) is not int
        or type(target.get("unit")) is not int
        or (target["layer"], target["unit"]) != expected_target
        or event.get("mode") != expected_mode
    ):
        raise RealWorkerDumpValidationError(
            "causal event target differs from the exact request"
        )


def _load_json_object(
    raw: bytes | bytearray | memoryview, label: str
) -> tuple[bytes, dict[str, Any]]:
    if type(raw) not in (bytes, bytearray, memoryview):
        raise RealWorkerDumpValidationError(f"{label} carrier must be bytes-like")
    try:
        carrier_size = raw.nbytes if type(raw) is memoryview else len(raw)
    except ValueError as exc:
        raise RealWorkerDumpValidationError(
            f"{label} carrier is not readable"
        ) from exc
    if carrier_size == 0:
        raise RealWorkerDumpValidationError(f"{label} carrier is empty")
    if carrier_size > MAX_CARRIER_BYTES:
        raise RealWorkerDumpValidationError(f"{label} carrier exceeds 2,000,000 bytes")
    try:
        snapshot = bytes(raw)
    except (TypeError, ValueError) as exc:
        raise RealWorkerDumpValidationError(
            f"{label} carrier is not readable"
        ) from exc
    if len(snapshot) != carrier_size or len(snapshot) > MAX_CARRIER_BYTES:
        raise RealWorkerDumpValidationError(
            f"{label} carrier changed while it was snapshotted"
        )
    if snapshot.startswith(b"\xef\xbb\xbf"):
        raise RealWorkerDumpValidationError(f"{label} carrier contains a UTF-8 BOM")
    try:
        text = snapshot.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RealWorkerDumpValidationError(
            f"{label} carrier is not strict UTF-8"
        ) from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_float=_bounded_float,
            parse_int=_bounded_int,
            parse_constant=_reject_constant,
        )
    except _JSONProfileError as exc:
        raise RealWorkerDumpValidationError(
            f"{label} carrier violates the strict JSON profile"
        ) from exc
    except (json.JSONDecodeError, RecursionError) as exc:
        raise RealWorkerDumpValidationError(
            f"{label} carrier is not valid JSON"
        ) from exc
    if type(value) is not dict:
        raise RealWorkerDumpValidationError(
            f"{label} carrier top-level value must be an object"
        )
    try:
        _validate_tree(value)
    except _JSONProfileError as exc:
        raise RealWorkerDumpValidationError(
            f"{label} carrier violates the bounded JSON profile"
        ) from exc
    return snapshot, value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _JSONProfileError("duplicate JSON object key")
        result[key] = value
    return result


def _bounded_float(value: str) -> float:
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise _JSONProfileError("invalid JSON float") from exc
    if not math.isfinite(result):
        raise _JSONProfileError("non-finite JSON float")
    return result


def _bounded_int(value: str) -> int:
    if len(value.lstrip("-")) > 620:
        raise _JSONProfileError("JSON integer exceeds the 2048-bit bound")
    try:
        result = int(value)
    except (ValueError, OverflowError) as exc:
        raise _JSONProfileError("invalid JSON integer") from exc
    if result.bit_length() > MAX_INTEGER_BITS:
        raise _JSONProfileError("JSON integer exceeds the 2048-bit bound")
    return result


def _reject_constant(_value: str) -> None:
    raise _JSONProfileError("non-finite JSON constant")


def _validate_tree(
    value: Any, *, depth: int = 0, counter: list[int] | None = None
) -> None:
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_JSON_NODES:
        raise _JSONProfileError("JSON document exceeds the node-count bound")
    if depth > MAX_JSON_DEPTH:
        raise _JSONProfileError("JSON document exceeds the nesting-depth bound")
    if type(value) is str:
        if "\x00" in value or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise _JSONProfileError("JSON string contains forbidden Unicode")
        return
    if type(value) in (int, float, bool) or value is None:
        if type(value) is float and not math.isfinite(value):
            raise _JSONProfileError("JSON tree contains a non-finite float")
        return
    if type(value) is list:
        for item in value:
            _validate_tree(item, depth=depth + 1, counter=counter)
        return
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise _JSONProfileError("JSON object key is not a string")
            _validate_tree(key, depth=depth + 1, counter=counter)
            _validate_tree(item, depth=depth + 1, counter=counter)
        return
    raise _JSONProfileError("JSON tree contains an unsupported value")


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    if type(value) in (str, int, float, bool) or value is None:
        return value
    raise RealWorkerDumpValidationError("validated JSON could not be frozen")


def _finite_number(value: object) -> bool:
    if type(value) is int:
        return True
    return type(value) is float and math.isfinite(value)


def _bounded_text(value: object, *, maximum: int) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= maximum
    )


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RealWorkerDumpValidationError(
            "validated value cannot use the canonical JSON digest profile"
        ) from exc


def _exact_json_equal(observed: object, expected: object) -> bool:
    if type(observed) is not type(expected):
        return False
    if type(observed) is dict:
        return set(observed) == set(expected) and all(
            _exact_json_equal(observed[key], expected[key]) for key in observed
        )
    if type(observed) is list:
        return len(observed) == len(expected) and all(
            _exact_json_equal(left, right)
            for left, right in zip(observed, expected)
        )
    return observed == expected


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


__all__ = [
    "ExpectedJoinedExecutionIdentity",
    "ExpectedRealWorkerManifest",
    "JoinedExecutionBindingFacts",
    "MAX_CARRIER_BYTES",
    "PYTHIA_STAGE27F_HOOK_PROFILE",
    "QWEN_OBSERVATION_ONLY_HOOK_PROFILE",
    "RealWorkerDumpValidationError",
    "RealWorkerJoinError",
    "RealWorkerManifestFacts",
    "RealWorkerPostSendAmbiguousError",
    "StrictRealWorkerDumpBinding",
    "StrictRealWorkerRequestBinding",
    "bind_successful_real_worker_dump",
    "validate_real_worker_dump_request",
]
