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
_SAFE_CONTEXT_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")

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
_HOOK_CONTRACT = {
    "contract_version": "harness_v2.mlp_intermediate_eraser.v2",
    "coordinate_space": "mlp_intermediate_post_activation",
    "module_path_template": "gpt_neox.layers[{layer}].mlp.dense_4h_to_h",
    "tensor_role": "forward_pre_hook.input[0]",
    "token_selection": "batch_0_last_sequence_position",
    "expected_width_source": "model_arch.mlp_intermediate_dim",
    "failure_policy": "fail_closed",
}


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
    manifest: RealWorkerManifestFacts
    claim_scope: str = "EXACT_BYTES_AND_DECLARED_MANIFEST_CONSISTENCY_ONLY"
    execution_authentication: str = "NOT_ESTABLISHED"
    image_identity: str = "NOT_ESTABLISHED"
    scientific_status: str = "NOT_ESTABLISHED"
    criteria_status: str = "OPEN"
    product_status: str = "RESEARCH_ONLY"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"


def bind_successful_real_worker_dump(
    *,
    request_raw: bytes | bytearray | memoryview,
    response_raw: bytes | bytearray | memoryview,
    expected_manifest: ExpectedRealWorkerManifest,
    allow_billing_receipt: bool = False,
) -> StrictRealWorkerDumpBinding:
    """Strict-load and bind one already-returned successful dump.

    A validation error is a definite statement about these supplied bytes. It
    is not evidence that a remote execution did not occur and does not itself
    authorize a retry.
    """

    if type(expected_manifest) is not ExpectedRealWorkerManifest:
        raise RealWorkerDumpValidationError(
            "expected_manifest must be an exact ExpectedRealWorkerManifest"
        )
    if type(allow_billing_receipt) is not bool:
        raise RealWorkerDumpValidationError(
            "allow_billing_receipt must be an exact boolean"
        )

    request_snapshot, request = _load_json_object(request_raw, "request")
    _validate_request(request, expected_manifest=expected_manifest)
    causal_requested, expected_target, expected_mode = _causal_request(request)

    response_snapshot, response = _load_json_object(response_raw, "response")
    allowed_response_keys = {"events"}
    if allow_billing_receipt:
        allowed_response_keys.add("billing_measurement_receipt")
    if set(response) != allowed_response_keys and not (
        allow_billing_receipt and set(response) == {"events"}
    ):
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

    manifest_facts, event_counts, output_text, token_count = _validate_events(
        events,
        expected_manifest=expected_manifest,
        causal_requested=causal_requested,
        expected_target=expected_target,
        expected_mode=expected_mode,
    )
    frozen_request = _freeze_json(request)
    frozen_events = tuple(_freeze_json(event) for event in events)
    frozen_billing = _freeze_json(billing) if billing is not None else None
    return StrictRealWorkerDumpBinding(
        request_raw=request_snapshot,
        request_sha256=_sha256(request_snapshot),
        request_byte_length=len(request_snapshot),
        response_raw=response_snapshot,
        response_sha256=_sha256(response_snapshot),
        response_byte_length=len(response_snapshot),
        request_payload=frozen_request,
        events=frozen_events,
        event_counts=MappingProxyType(dict(sorted(event_counts.items()))),
        token_count=token_count,
        output_text=output_text,
        causal_ablation_requested=causal_requested,
        billing_measurement_receipt=frozen_billing,
        manifest=manifest_facts,
    )


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
    causal_requested: bool,
    expected_target: tuple[int, int],
    expected_mode: str,
) -> tuple[RealWorkerManifestFacts, Counter[str], str, int]:
    for event in events:
        if type(event) is not dict:
            raise RealWorkerDumpValidationError("every event must be an object")
        if type(event.get("type")) is not str or event["type"] not in _ALLOWED_EVENT_TYPES:
            raise RealWorkerDumpValidationError("worker dump contains an unknown event type")

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

    token_events = [event for event in events if event["type"] == "token"]
    observed_indices: list[int] = []
    output_parts: list[str] = []
    for event in token_events:
        token_index = event.get("token_index")
        token = event.get("token")
        if type(token_index) is not int or token_index < 0 or type(token) is not str:
            raise RealWorkerDumpValidationError("token event has invalid critical fields")
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
        token_count=len(token_events),
        output_text=output_text,
    )
    _validate_causal_events(
        events,
        requested=causal_requested,
        expected_target=expected_target,
        expected_mode=expected_mode,
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

    hooks = manifest["supported_hooks"]
    if (
        type(hooks) is not list
        or any(type(item) is not str or item not in _SUPPORTED_HOOKS for item in hooks)
        or len(set(hooks)) != len(hooks)
    ):
        raise RealWorkerDumpValidationError("manifest supported_hooks are invalid")
    if causal_requested and not {
        "mlp_intermediate_post_activation",
        "logits",
    } <= set(hooks):
        raise RealWorkerDumpValidationError(
            "manifest lacks hooks required by the requested causal ablation"
        )
    hook_contract = manifest["intervention_hook_contract"]
    if type(hook_contract) is not dict or hook_contract != _HOOK_CONTRACT:
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
    )


def _validate_word_spans(
    event: dict[str, Any], *, token_count: int, output_text: str
) -> None:
    required = {
        "type",
        "spans",
        "structural_token_indices",
        "total_tokens_covered",
    }
    if set(event) != required:
        raise RealWorkerDumpValidationError("word_spans event has invalid exact structure")
    spans = event["spans"]
    structural = event["structural_token_indices"]
    total = event["total_tokens_covered"]
    if (
        type(spans) is not list
        or type(structural) is not list
        or type(total) is not int
        or total != token_count
    ):
        raise RealWorkerDumpValidationError("word_spans token count is invalid")
    seen: set[int] = set()
    previous_end = 0
    for span in spans:
        if type(span) is not dict or not {
            "word",
            "token_indices",
            "char_start",
            "char_end",
        } <= set(span):
            raise RealWorkerDumpValidationError("word span has invalid critical fields")
        word = span["word"]
        indices = span["token_indices"]
        start = span["char_start"]
        end = span["char_end"]
        if (
            type(word) is not str
            or not word
            or type(indices) is not list
            or not indices
            or type(start) is not int
            or type(end) is not int
            or start < previous_end
            or not 0 <= start < end <= len(output_text)
            or output_text[start:end] != word
        ):
            raise RealWorkerDumpValidationError("word span text or range is invalid")
        previous_end = end
        for index in indices:
            if type(index) is not int or index < 0 or index in seen:
                raise RealWorkerDumpValidationError("word span token backing is duplicated")
            seen.add(index)
    for index in structural:
        if type(index) is not int or index < 0 or index in seen:
            raise RealWorkerDumpValidationError(
                "structural token backing is invalid or duplicated"
            )
        seen.add(index)
    if seen != set(range(token_count)):
        raise RealWorkerDumpValidationError(
            "word_spans coverage differs from the contiguous token range"
        )


def _validate_causal_events(
    events: list[dict[str, Any]],
    *,
    requested: bool,
    expected_target: tuple[int, int],
    expected_mode: str,
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
    effect = effects[0]
    if (
        effect.get("is_real_model") is not True
        or not _finite_number(effect.get("logit_delta"))
        or not _finite_number(effect.get("confidence_delta"))
        or type(effect.get("top_token_changed")) is not bool
    ):
        raise RealWorkerDumpValidationError(
            "causal effect lacks a finite real-model measurement"
        )
    control = controls[0]
    n_controls = control.get("n_controls")
    units = control.get("control_units")
    if (
        control.get("is_real_model") is not True
        or type(n_controls) is not int
        or n_controls < 1
        or type(units) is not list
        or len(units) != n_controls
        or any(type(unit) is not int or unit < 0 for unit in units)
        or len(set(units)) != len(units)
        or type(control.get("selectivity_passed")) is not bool
        or any(
            not _finite_number(control.get(field))
            for field in (
                "target_abs_logit_delta",
                "control_mean_abs_logit_delta",
                "control_max_abs_logit_delta",
                "margin_over_control_max",
            )
        )
    ):
        raise RealWorkerDumpValidationError(
            "matched control lacks a finite real-model measurement"
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


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


__all__ = [
    "ExpectedRealWorkerManifest",
    "MAX_CARRIER_BYTES",
    "RealWorkerDumpValidationError",
    "RealWorkerJoinError",
    "RealWorkerManifestFacts",
    "RealWorkerPostSendAmbiguousError",
    "StrictRealWorkerDumpBinding",
    "bind_successful_real_worker_dump",
]
