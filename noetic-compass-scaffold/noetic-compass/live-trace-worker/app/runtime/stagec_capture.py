"""Fail-closed STRUCTURE_ONLY Stage C Qwen W0 capture candidate.

The seam is intentionally not wired into a worker route.  It consumes exact
canonical request and non-authorizing projection bytes plus an authenticated,
one-use process-local runtime permit, requires the loader's exact
``LoadedModel`` carrier, performs one direct prefill call, and returns a
self-replaying in-memory evidence bundle.  It does not itself authorize a real
execution, revalidate model files, retain evidence durably, generate tokens,
perform an intervention, or make a scientific/product claim.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from hashlib import sha256
import json
import re
import threading
from types import MappingProxyType
from typing import Any, Mapping, Sequence
import weakref

import numpy as np
import torch
from torch.nn.modules import module as torch_module_hooks
from torch.utils.hooks import RemovableHandle

from . import model_loader, stagec_runtime_activation


STAGEC_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
STAGEC_MODEL_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
STAGEC_WEIGHTS_SHA256 = (
    "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe"
)
STAGEC_WEIGHTS_BYTES = 988_097_824
STAGEC_MODEL_CONFIG_SHA256 = (
    "18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45"
)
STAGEC_MODEL_CONFIG_BYTES = 659
STAGEC_TOKENIZER_JSON_SHA256 = (
    "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"
)
STAGEC_TOKENIZER_JSON_BYTES = 7_031_645
STAGEC_TOKENIZER_CONFIG_SHA256 = (
    "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583"
)
STAGEC_TOKENIZER_CONFIG_BYTES = 7_305

STAGEC_LAYER_COUNT = 24
STAGEC_HIDDEN_WIDTH = 896
STAGEC_VECTOR_WIDTH = 4_864
STAGEC_VOCAB_SIZE = 151_936
STAGEC_MAX_SEQUENCE_LENGTH = 32_768
STAGEC_TARGET_LAYER = 18
STAGEC_WRONG_LAYER = 0
STAGEC_CAPTURE_LAYERS = (STAGEC_WRONG_LAYER, STAGEC_TARGET_LAYER)
STAGEC_TARGET_MODULE_PATH = "model.layers[18].mlp.down_proj"
STAGEC_WRONG_LAYER_MODULE_PATH = "model.layers[0].mlp.down_proj"
STAGEC_WORKER_VERSION = "stageb-real-qwen2.5-0.5b-instruct"

REQUEST_SCHEMA = "cas_harness.stagec.capture_request.v1"
AUTHORIZATION_SCHEMA = "cas_harness.stagec.authorization_projection.v1"
CAPTURE_INDEX_SCHEMA = "cas_harness.stagec.capture_index.v1"
REQUEST_MEDIA_TYPE = "application/vnd.cas-harness.stagec-capture-request+json"
AUTHORIZATION_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-authorization-projection+json"
)
CAPTURE_INDEX_MEDIA_TYPE = "application/vnd.cas-harness.stagec-capture-index+json"
RAW_ARRAY_MEDIA_TYPE = "application/vnd.cas-harness.ndarray.raw"
RAW_ARRAY_FORMAT = "RAW C-ORDER ARRAY BYTES / NO HEADER / NO PICKLE"
RAW_ARRAY_LAYOUT = "C_CONTIGUOUS"
STRUCTURE_ONLY_SCOPE = "STRUCTURE_ONLY"
NON_AUTHORITY_STATUS = "NON_AUTHORITY / DOES_NOT_AUTHORIZE_MODEL_EXECUTION"
LOADER_IDENTITY_STATUS = (
    "LOADER_CARRIER_VERIFIED / MODEL_FILES_NOT_REVALIDATED_AT_CAPTURE"
)
IN_MEMORY_LOCATION = "IN_MEMORY"
NOT_DURABLY_RETAINED = "NOT_DURABLY_RETAINED"
NOT_ATTESTED = "NOT_ATTESTED"

_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,255}$")
_ALLOWED_SPLITS = {
    "stagec-calibration",
    "stagec-confirmatory",
    "stagec-heldout",
}
_ALLOWED_LABELS = {
    "ADVERSARIAL_PRESENT",
    "CLEAN_ABSENT",
    "CLEAN_NULL_ABSENT",
}
_KNOWN_QWEN_CHAT_CONTROL_TOKENS = {
    "<|endoftext|>",
    "<|im_start|>",
    "<|im_end|>",
}
_MAX_SIGNED_INT64 = (1 << 63) - 1
_LOCAL_HOOK_REGISTRIES = (
    "_forward_pre_hooks",
    "_forward_hooks",
    "_forward_pre_hooks_with_kwargs",
    "_forward_hooks_with_kwargs",
    "_forward_hooks_always_called",
)
_GLOBAL_HOOK_REGISTRIES = (
    "_global_forward_pre_hooks",
    "_global_forward_hooks",
    "_global_forward_hooks_with_kwargs",
    "_global_forward_hooks_always_called",
)


class StageCCaptureError(RuntimeError):
    """An exact capture or replay precondition was not established."""


class _StageCRuntimeBindingError(StageCCaptureError):
    """A deterministic local/envelope binding rejection before model access."""


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest().upper()


def _require_text(value: Any, *, field_name: str, identifier: bool = False) -> str:
    if type(value) is not str or not value:
        raise StageCCaptureError(f"{field_name} must be a non-empty exact string")
    if identifier and _IDENTIFIER_RE.fullmatch(value) is None:
        raise StageCCaptureError(f"{field_name} is not a bounded machine identifier")
    return value


def _require_int(
    value: Any,
    *,
    field_name: str,
    minimum: int = 0,
    maximum: int = _MAX_SIGNED_INT64,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise StageCCaptureError(
            f"{field_name} must be an exact integer in [{minimum}, {maximum}]"
        )
    return value


def _require_sha256(value: Any, *, field_name: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise StageCCaptureError(f"{field_name} must be canonical uppercase SHA-256")
    return value


def _require_exact_keys(value: Any, expected: set[str], *, field_name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise StageCCaptureError(f"{field_name} must be an exact JSON object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise StageCCaptureError(
            f"{field_name} keys drifted; missing={missing!r}, extra={extra!r}"
        )
    return value


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return text.encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise StageCCaptureError("value is not canonical strict UTF-8 JSON") from exc


def _stagec_capture_profile_payload() -> dict[str, Any]:
    """Return the exact local contract whose digest must be runtime-bound."""

    return {
        "schema_version": "cas_harness.stagec.qwen_w0_worker_capture_profile.v1",
        "model": {
            "model_id": STAGEC_MODEL_ID,
            "model_revision": STAGEC_MODEL_REVISION,
            "model_config_sha256": STAGEC_MODEL_CONFIG_SHA256.upper(),
            "weights_sha256": STAGEC_WEIGHTS_SHA256.upper(),
            "tokenizer_json_sha256": STAGEC_TOKENIZER_JSON_SHA256.upper(),
            "tokenizer_config_sha256": STAGEC_TOKENIZER_CONFIG_SHA256.upper(),
        },
        "prompt": {
            "message_count": 1,
            "message_role": "user",
            "chat_template_application_count": 1,
            "add_generation_prompt": True,
            "tokenizer_padding": False,
            "tokenizer_truncation": False,
            "observation_position": "FINAL_UNPADDED_PROMPT_TOKEN",
        },
        "forward": {
            "direct_prefill_call_count": 1,
            "pre_row_model_forward_count": 0,
            "startup_canary_count": 0,
            "generate_call_count": 0,
            "intervention_count": 0,
            "use_cache": False,
            "output_attentions": False,
            "output_hidden_states": False,
            "return_dict": True,
            "inference_mode": True,
        },
        "capture": {
            "hook_kind": "FORWARD_PRE_HOOK_INPUT",
            "registration_order": list(STAGEC_CAPTURE_LAYERS),
            "firing_order": list(STAGEC_CAPTURE_LAYERS),
            "cleanup_order": list(reversed(STAGEC_CAPTURE_LAYERS)),
            "wrong_layer": STAGEC_WRONG_LAYER,
            "wrong_layer_module_path": STAGEC_WRONG_LAYER_MODULE_PATH,
            "target_layer": STAGEC_TARGET_LAYER,
            "target_module_path": STAGEC_TARGET_MODULE_PATH,
            "vector_width": STAGEC_VECTOR_WIDTH,
            "retained_dtype": "torch.float32",
            "retained_device": "cpu",
        },
        "scope": {
            "capture_only": True,
            "detector_scoring": False,
            "outcome_access_before_model_call": False,
            "generation": False,
            "intervention": False,
            "steering": False,
        },
    }


STAGEC_CAPTURE_PROFILE_SHA256 = _sha256_bytes(
    _canonical_json_bytes(_stagec_capture_profile_payload())
)


def _strict_json_object(raw_bytes: Any, *, field_name: str) -> dict[str, Any]:
    if type(raw_bytes) is not bytes or not raw_bytes:
        raise StageCCaptureError(f"{field_name} must be non-empty immutable bytes")
    try:
        text = raw_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise StageCCaptureError(f"{field_name} is not strict UTF-8") from exc
    if text.startswith("\ufeff"):
        raise StageCCaptureError(f"{field_name} must not contain a UTF-8 BOM")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise StageCCaptureError(
                    f"{field_name} contains duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise StageCCaptureError(f"{field_name} contains non-finite JSON value {value}")

    try:
        decoded = json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except StageCCaptureError:
        raise
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise StageCCaptureError(f"{field_name} is not valid JSON") from exc
    if type(decoded) is not dict:
        raise StageCCaptureError(f"{field_name} must decode to one JSON object")
    if _canonical_json_bytes(decoded) != raw_bytes:
        raise StageCCaptureError(f"{field_name} bytes are not the exact canonical encoding")
    return decoded


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    """Exact content reference for a JSON, text, model, or tokenizer artifact."""

    artifact_id: str
    sha256: str
    byte_length: int
    media_type: str

    def __post_init__(self) -> None:
        _require_text(self.artifact_id, field_name="artifact_id", identifier=True)
        _require_sha256(self.sha256, field_name=f"{self.artifact_id}.sha256")
        _require_int(self.byte_length, field_name=f"{self.artifact_id}.byte_length", minimum=1)
        _require_text(self.media_type, field_name=f"{self.artifact_id}.media_type")

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "byte_length": self.byte_length,
            "media_type": self.media_type,
            "sha256": self.sha256,
        }

    @classmethod
    def from_payload(cls, value: Any, *, field_name: str) -> "ArtifactIdentity":
        payload = _require_exact_keys(
            value,
            {"artifact_id", "byte_length", "media_type", "sha256"},
            field_name=field_name,
        )
        try:
            return cls(**payload)
        except TypeError as exc:
            raise StageCCaptureError(f"{field_name} is not an exact artifact ref") from exc


@dataclass(frozen=True, slots=True)
class CanonicalJsonArtifact:
    """Immutable exact bytes plus their content reference."""

    ref: ArtifactIdentity
    raw_bytes: bytes

    def __post_init__(self) -> None:
        if type(self.ref) is not ArtifactIdentity:
            raise StageCCaptureError("JSON artifact ref must be an exact ArtifactIdentity")
        if type(self.raw_bytes) is not bytes:
            raise StageCCaptureError("JSON artifact payload must be immutable bytes")
        if len(self.raw_bytes) != self.ref.byte_length:
            raise StageCCaptureError("JSON artifact byte length does not match its ref")
        if _sha256_bytes(self.raw_bytes) != self.ref.sha256:
            raise StageCCaptureError("JSON artifact digest does not match its ref")


def _json_artifact(
    *, artifact_id: str, media_type: str, payload: Mapping[str, Any]
) -> CanonicalJsonArtifact:
    raw_bytes = _canonical_json_bytes(dict(payload))
    return CanonicalJsonArtifact(
        ref=ArtifactIdentity(
            artifact_id=artifact_id,
            sha256=_sha256_bytes(raw_bytes),
            byte_length=len(raw_bytes),
            media_type=media_type,
        ),
        raw_bytes=raw_bytes,
    )


def _load_json_artifact(
    artifact: Any,
    *,
    media_type: str,
    field_name: str,
) -> dict[str, Any]:
    if type(artifact) is not CanonicalJsonArtifact:
        raise StageCCaptureError(f"{field_name} must be an exact CanonicalJsonArtifact")
    if type(artifact.ref) is not ArtifactIdentity:
        raise StageCCaptureError(f"{field_name} ref must be an exact ArtifactIdentity")
    if type(artifact.raw_bytes) is not bytes:
        raise StageCCaptureError(f"{field_name} payload must be immutable bytes")
    validated_ref = ArtifactIdentity.from_payload(
        artifact.ref.to_payload(), field_name=f"{field_name}.ref"
    )
    if validated_ref != artifact.ref:
        raise StageCCaptureError(f"{field_name} ref value drifted")
    if artifact.ref.media_type != media_type:
        raise StageCCaptureError(f"{field_name} has the wrong exact media type")
    if len(artifact.raw_bytes) != artifact.ref.byte_length:
        raise StageCCaptureError(f"{field_name} byte length drifted")
    if _sha256_bytes(artifact.raw_bytes) != artifact.ref.sha256:
        raise StageCCaptureError(f"{field_name} digest drifted")
    return _strict_json_object(artifact.raw_bytes, field_name=field_name)


def _validate_association_values(payload: Mapping[str, Any]) -> None:
    for key in (
        "study_id",
        "case_id",
        "split_id",
        "base_intent_group_id",
        "frozen_variant",
        "frozen_label",
        "invocation_id",
    ):
        _require_text(payload[key], field_name=key, identifier=True)
    if payload["split_id"] not in _ALLOWED_SPLITS:
        raise StageCCaptureError("split_id is not a frozen Stage C split")
    if payload["frozen_variant"] not in _ALLOWED_LABELS:
        raise StageCCaptureError("frozen_variant is not a frozen Stage C variant")
    if payload["frozen_label"] not in _ALLOWED_LABELS:
        raise StageCCaptureError("frozen_label is not a Stage C label")
    if payload["frozen_variant"] != payload["frozen_label"]:
        raise StageCCaptureError("frozen_variant does not map exactly to frozen_label")


_REQUEST_KEYS = {
    "schema_version",
    "study_id",
    "case_id",
    "split_id",
    "base_intent_group_id",
    "frozen_variant",
    "frozen_label",
    "invocation_id",
    "prompt",
}


def _validate_request_payload(value: Any) -> dict[str, Any]:
    payload = _require_exact_keys(value, _REQUEST_KEYS, field_name="request")
    if payload["schema_version"] != REQUEST_SCHEMA:
        raise StageCCaptureError("request schema version drifted")
    _validate_association_values(payload)
    _require_text(payload["prompt"], field_name="prompt")
    try:
        payload["prompt"].encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StageCCaptureError("prompt is not strict UTF-8") from exc
    return payload


def build_stagec_request_artifact(
    *,
    artifact_id: str,
    study_id: str,
    case_id: str,
    split_id: str,
    base_intent_group_id: str,
    frozen_variant: str,
    frozen_label: str,
    invocation_id: str,
    prompt: str,
) -> CanonicalJsonArtifact:
    payload = {
        "schema_version": REQUEST_SCHEMA,
        "study_id": study_id,
        "case_id": case_id,
        "split_id": split_id,
        "base_intent_group_id": base_intent_group_id,
        "frozen_variant": frozen_variant,
        "frozen_label": frozen_label,
        "invocation_id": invocation_id,
        "prompt": prompt,
    }
    _validate_request_payload(payload)
    return _json_artifact(
        artifact_id=artifact_id,
        media_type=REQUEST_MEDIA_TYPE,
        payload=payload,
    )


_AUTHORIZATION_KEYS = {
    "schema_version",
    "scope",
    "authority_status",
    "request_sha256",
    "plan_id",
    "study_id",
    "case_id",
    "invocation_id",
}


def _validate_authorization_payload(
    value: Any,
    *,
    request: Mapping[str, Any],
    request_ref: ArtifactIdentity,
) -> dict[str, Any]:
    payload = _require_exact_keys(
        value, _AUTHORIZATION_KEYS, field_name="authorization_projection"
    )
    if payload["schema_version"] != AUTHORIZATION_SCHEMA:
        raise StageCCaptureError("authorization projection schema version drifted")
    if payload["scope"] != STRUCTURE_ONLY_SCOPE:
        raise StageCCaptureError("authorization projection is not STRUCTURE_ONLY")
    if payload["authority_status"] != NON_AUTHORITY_STATUS:
        raise StageCCaptureError("authorization projection lost literal non-authority")
    _require_sha256(payload["request_sha256"], field_name="authorization.request_sha256")
    _require_text(payload["plan_id"], field_name="plan_id", identifier=True)
    if payload["request_sha256"] != request_ref.sha256:
        raise StageCCaptureError("authorization projection binds a different request")
    for key in ("study_id", "case_id", "invocation_id"):
        _require_text(payload[key], field_name=f"authorization.{key}", identifier=True)
        if payload[key] != request[key]:
            raise StageCCaptureError(f"authorization projection {key} drifted")
    return payload


def build_stagec_authorization_projection_artifact(
    *,
    artifact_id: str,
    request_artifact: CanonicalJsonArtifact,
    plan_id: str,
) -> CanonicalJsonArtifact:
    request = _validate_request_payload(
        _load_json_artifact(
            request_artifact,
            media_type=REQUEST_MEDIA_TYPE,
            field_name="request_artifact",
        )
    )
    payload = {
        "schema_version": AUTHORIZATION_SCHEMA,
        "scope": STRUCTURE_ONLY_SCOPE,
        "authority_status": NON_AUTHORITY_STATUS,
        "request_sha256": request_artifact.ref.sha256,
        "plan_id": plan_id,
        "study_id": request["study_id"],
        "case_id": request["case_id"],
        "invocation_id": request["invocation_id"],
    }
    _validate_authorization_payload(
        payload,
        request=request,
        request_ref=request_artifact.ref,
    )
    return _json_artifact(
        artifact_id=artifact_id,
        media_type=AUTHORIZATION_MEDIA_TYPE,
        payload=payload,
    )


@dataclass(frozen=True, slots=True)
class CaptureArtifactIds:
    """Prospectively unique IDs for every capture-created/reference artifact."""

    capture_index: str
    model_config: str
    model_weights: str
    tokenizer_json: str
    tokenizer_config: str
    chat_template: str
    input_ids: str
    attention_mask: str
    target_vector: str
    wrong_layer_vector: str

    def __post_init__(self) -> None:
        values = tuple(getattr(self, name) for name in self.__slots__)
        for index, value in enumerate(values):
            _require_text(
                value,
                field_name=f"capture_artifact_ids[{index}]",
                identifier=True,
            )
        if len(set(values)) != len(values):
            raise StageCCaptureError("capture artifact IDs must be globally unique")


@dataclass(frozen=True, slots=True)
class RawArrayArtifactRef:
    artifact_id: str
    sha256: str
    byte_length: int
    media_type: str
    format: str
    dtype: str
    byte_order: str
    shape: tuple[int, ...]
    layout: str
    role: str
    layer_index: int | None
    module_path: str | None
    retention_location: str
    durability_status: str

    def __post_init__(self) -> None:
        _require_text(self.artifact_id, field_name="array.artifact_id", identifier=True)
        _require_sha256(self.sha256, field_name=f"{self.artifact_id}.sha256")
        _require_int(self.byte_length, field_name=f"{self.artifact_id}.byte_length", minimum=1)
        if self.media_type != RAW_ARRAY_MEDIA_TYPE or self.format != RAW_ARRAY_FORMAT:
            raise StageCCaptureError("raw array media type/format drifted")
        if self.dtype not in {"<i8", "<f4"} or self.byte_order != "little":
            raise StageCCaptureError("raw array dtype/byte order drifted")
        if (
            type(self.shape) is not tuple
            or not self.shape
            or any(type(item) is not int or item < 1 for item in self.shape)
        ):
            raise StageCCaptureError("raw array shape is invalid")
        if self.layout != RAW_ARRAY_LAYOUT:
            raise StageCCaptureError("raw array layout drifted")
        if self.retention_location != IN_MEMORY_LOCATION:
            raise StageCCaptureError("raw array must be labeled IN_MEMORY")
        if self.durability_status != NOT_DURABLY_RETAINED:
            raise StageCCaptureError("raw array must be labeled NOT_DURABLY_RETAINED")
        _require_text(self.role, field_name="array.role")
        if self.layer_index is not None and type(self.layer_index) is not int:
            raise StageCCaptureError("raw array layer_index must be int or null")
        if self.module_path is not None and type(self.module_path) is not str:
            raise StageCCaptureError("raw array module_path must be string or null")
        item_size = 8 if self.dtype == "<i8" else 4
        expected = item_size
        for dimension in self.shape:
            expected *= dimension
        if self.byte_length != expected:
            raise StageCCaptureError("raw array length does not match dtype and shape")

    def to_payload(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "byte_length": self.byte_length,
            "byte_order": self.byte_order,
            "dtype": self.dtype,
            "durability_status": self.durability_status,
            "format": self.format,
            "layer_index": self.layer_index,
            "layout": self.layout,
            "media_type": self.media_type,
            "module_path": self.module_path,
            "retention_location": self.retention_location,
            "role": self.role,
            "sha256": self.sha256,
            "shape": list(self.shape),
        }

    @classmethod
    def from_payload(cls, value: Any, *, field_name: str) -> "RawArrayArtifactRef":
        payload = _require_exact_keys(
            value,
            {
                "artifact_id", "byte_length", "byte_order", "dtype",
                "durability_status", "format", "layer_index", "layout",
                "media_type", "module_path", "retention_location", "role",
                "sha256", "shape",
            },
            field_name=field_name,
        )
        if type(payload["shape"]) is not list:
            raise StageCCaptureError(f"{field_name}.shape must be a JSON array")
        values = dict(payload)
        values["shape"] = tuple(payload["shape"])
        try:
            return cls(**values)
        except TypeError as exc:
            raise StageCCaptureError(f"{field_name} is not an exact array ref") from exc


@dataclass(frozen=True, slots=True)
class RawArrayArtifact:
    ref: RawArrayArtifactRef
    raw_bytes: bytes

    def __post_init__(self) -> None:
        if type(self.ref) is not RawArrayArtifactRef:
            raise StageCCaptureError("raw array ref has the wrong exact type")
        if type(self.raw_bytes) is not bytes:
            raise StageCCaptureError("raw array payload must be immutable bytes")
        if len(self.raw_bytes) != self.ref.byte_length:
            raise StageCCaptureError("raw array payload length drifted")
        if _sha256_bytes(self.raw_bytes) != self.ref.sha256:
            raise StageCCaptureError("raw array payload digest drifted")


def _raw_array_artifact(
    *,
    artifact_id: str,
    tensor: torch.Tensor,
    dtype: str,
    role: str,
    layer_index: int | None,
    module_path: str | None,
) -> RawArrayArtifact:
    if dtype == "<i8":
        array = np.asarray(
            tensor.detach().to(device="cpu", dtype=torch.int64).contiguous().numpy(),
            dtype=np.dtype("<i8"),
            order="C",
        )
    elif dtype == "<f4":
        array = np.asarray(
            tensor.detach().to(device="cpu", dtype=torch.float32).contiguous().numpy(),
            dtype=np.dtype("<f4"),
            order="C",
        )
    else:  # pragma: no cover - private callers fix the two admitted dtypes
        raise StageCCaptureError("unsupported raw array dtype")
    raw_bytes = array.tobytes(order="C")
    return RawArrayArtifact(
        ref=RawArrayArtifactRef(
            artifact_id=artifact_id,
            sha256=_sha256_bytes(raw_bytes),
            byte_length=len(raw_bytes),
            media_type=RAW_ARRAY_MEDIA_TYPE,
            format=RAW_ARRAY_FORMAT,
            dtype=dtype,
            byte_order="little",
            shape=tuple(int(item) for item in array.shape),
            layout=RAW_ARRAY_LAYOUT,
            role=role,
            layer_index=layer_index,
            module_path=module_path,
            retention_location=IN_MEMORY_LOCATION,
            durability_status=NOT_DURABLY_RETAINED,
        ),
        raw_bytes=raw_bytes,
    )


def _verify_exact_qwen_binding(binding: Any) -> model_loader.ModelBinding:
    if type(binding) is not model_loader.ModelBinding:
        raise StageCCaptureError("selected model binding has the wrong exact type")
    actual = {
        "key": binding.key,
        "model_id": binding.model_id,
        "revision": binding.revision,
        "weights_filename": binding.weights_filename,
        "weights_sha256": binding.weights_sha256,
        "weights_bytes": binding.weights_bytes,
        "family": binding.arch.family,
        "layers": binding.arch.n_layers,
        "hidden": binding.arch.hidden_size,
        "intermediate": binding.arch.mlp_intermediate_dim,
        "worker_version": binding.worker_version,
        "stack": binding.probe_layer_stack_path,
        "projection": binding.probe_projection_path,
        "intervention": binding.stage27f_intervention_supported,
        "cover": binding.stage27f_cover_library_supported,
        "ablation": binding.single_unit_causal_ablation_supported,
    }
    expected = {
        "key": model_loader.QWEN_05B_INSTRUCT_BINDING_KEY,
        "model_id": STAGEC_MODEL_ID,
        "revision": STAGEC_MODEL_REVISION,
        "weights_filename": "model.safetensors",
        "weights_sha256": STAGEC_WEIGHTS_SHA256,
        "weights_bytes": STAGEC_WEIGHTS_BYTES,
        "family": "qwen2",
        "layers": STAGEC_LAYER_COUNT,
        "hidden": STAGEC_HIDDEN_WIDTH,
        "intermediate": STAGEC_VECTOR_WIDTH,
        "worker_version": STAGEC_WORKER_VERSION,
        "stack": ("model", "layers"),
        "projection": ("mlp", "down_proj"),
        "intervention": False,
        "cover": False,
        "ablation": False,
    }
    if actual != expected:
        raise StageCCaptureError("selected model is not the exact Stage C Qwen binding")
    exact_typed_fields = {
        "key": str,
        "model_id": str,
        "revision": str,
        "weights_filename": str,
        "weights_sha256": str,
        "weights_bytes": int,
        "worker_version": str,
        "probe_layer_stack_path": tuple,
        "probe_projection_path": tuple,
        "stage27f_intervention_supported": bool,
        "stage27f_cover_library_supported": bool,
        "single_unit_causal_ablation_supported": bool,
    }
    for name, expected_type in exact_typed_fields.items():
        if type(getattr(binding, name)) is not expected_type:
            raise StageCCaptureError(f"selected Qwen binding type drifted: {name}")
    arch = binding.arch
    if type(arch) is not model_loader.ModelArch:
        raise StageCCaptureError("selected Qwen architecture has the wrong exact type")
    exact_arch = {
        "family": (str, "qwen2"),
        "n_layers": (int, 24),
        "hidden_size": (int, 896),
        "mlp_intermediate_dim": (int, 4_864),
        "n_heads": (int, 14),
        "total_params": (int, 494_032_768),
        "validated": (bool, True),
    }
    for name, (expected_type, expected_value) in exact_arch.items():
        observed = getattr(arch, name, None)
        if type(observed) is not expected_type or observed != expected_value:
            raise StageCCaptureError(f"selected Qwen architecture drifted: {name}")
    pins = {
        "config.json": (STAGEC_MODEL_CONFIG_SHA256, STAGEC_MODEL_CONFIG_BYTES),
        "generation_config.json": (
            "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6",
            242,
        ),
        "merges.txt": (
            "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3",
            1_671_839,
        ),
        "model.safetensors": (STAGEC_WEIGHTS_SHA256, STAGEC_WEIGHTS_BYTES),
        "tokenizer.json": (STAGEC_TOKENIZER_JSON_SHA256, STAGEC_TOKENIZER_JSON_BYTES),
        "tokenizer_config.json": (
            STAGEC_TOKENIZER_CONFIG_SHA256,
            STAGEC_TOKENIZER_CONFIG_BYTES,
        ),
        "vocab.json": (
            "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
            2_776_833,
        ),
    }
    if type(binding.artifacts) is not MappingProxyType or set(binding.artifacts) != set(pins):
        raise StageCCaptureError("selected Qwen artifact manifest drifted")
    for name, expected_pin in pins.items():
        observed_pin = binding.artifacts[name]
        if (
            type(observed_pin) is not tuple
            or len(observed_pin) != 2
            or type(observed_pin[0]) is not str
            or type(observed_pin[1]) is not int
            or observed_pin != expected_pin
        ):
            raise StageCCaptureError(
                f"selected Qwen artifact manifest drifted at {name}"
            )
    return binding


def _verify_model_config(model: Any) -> None:
    config = getattr(model, "config", None)
    expected = {
        "model_type": "qwen2",
        "num_hidden_layers": STAGEC_LAYER_COUNT,
        "hidden_size": STAGEC_HIDDEN_WIDTH,
        "intermediate_size": STAGEC_VECTOR_WIDTH,
        "_commit_hash": STAGEC_MODEL_REVISION,
        "vocab_size": STAGEC_VOCAB_SIZE,
        "max_position_embeddings": STAGEC_MAX_SEQUENCE_LENGTH,
    }
    if config is None:
        raise StageCCaptureError("loaded model exposes no Qwen config")
    for name, expected_value in expected.items():
        observed = getattr(config, name, None)
        if type(observed) is not type(expected_value) or observed != expected_value:
            raise StageCCaptureError(f"model config identity drifted at {name}")


def _verify_loaded_carrier(
    loaded: Any,
) -> tuple[model_loader.ModelBinding, Any, Any, bytes, str]:
    binding = _verify_exact_qwen_binding(model_loader.active_model_binding())
    if type(loaded) is not model_loader.LoadedModel:
        raise StageCCaptureError("loaded must be the exact model_loader.LoadedModel carrier")
    try:
        is_real = loaded.is_real
    except Exception as exc:
        raise StageCCaptureError("LoadedModel.is_real verification failed") from exc
    if is_real is not True:
        raise StageCCaptureError("LoadedModel.is_real is not exact true")
    manifest = loaded.manifest
    expected_manifest_type = type(model_loader.bootstrap_manifest(binding))
    if type(manifest) is not expected_manifest_type:
        raise StageCCaptureError("LoadedModel manifest has the wrong exact type")
    exact_manifest_fields = {
        "model_id": STAGEC_MODEL_ID,
        "tokenizer_id": STAGEC_MODEL_ID,
        "requested_revision": STAGEC_MODEL_REVISION,
        "resolved_revision": STAGEC_MODEL_REVISION,
        "revision_verified": True,
        "weights_filename": "model.safetensors",
        "weights_sha256": STAGEC_WEIGHTS_SHA256,
        "weights_bytes": STAGEC_WEIGHTS_BYTES,
        "weights_hash_verified": True,
        "model_identity_status": "PINNED_REVISION_AND_WEIGHTS_SHA256",
        "is_real_model": True,
        "execution_kind": "real_model_weights",
        "worker_version": STAGEC_WORKER_VERSION,
    }
    for name, expected_value in exact_manifest_fields.items():
        observed = getattr(manifest, name, None)
        if type(observed) is not type(expected_value) or observed != expected_value:
            raise StageCCaptureError(f"LoadedModel manifest identity drifted at {name}")
    if type(manifest.model_arch) is not model_loader.ModelArch:
        raise StageCCaptureError("LoadedModel manifest architecture has the wrong exact type")
    expected_hooks = [
        "residual_stream",
        "mlp_intermediate_post_activation",
        "attention_pattern",
        "logits",
    ]
    if type(manifest.supported_hooks) is not list or manifest.supported_hooks != expected_hooks:
        raise StageCCaptureError("LoadedModel manifest supported-hook identity drifted")
    observation_contract = manifest.intervention_hook_contract
    expected_observation_contract = {
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
    if (
        type(observation_contract) is not model_loader.ObservationOnlyHookContract
        or observation_contract.model_dump(mode="json")
        != expected_observation_contract
    ):
        raise StageCCaptureError(
            "LoadedModel manifest observation-only hook contract drifted"
        )
    if type(manifest.runtime_execution) is not model_loader.RuntimeExecutionEvidence:
        raise StageCCaptureError(
            "LoadedModel manifest runtime evidence has the wrong exact type"
        )
    if loaded.load_error is not None:
        raise StageCCaptureError("LoadedModel carrier records a load error")
    model = loaded.model
    tokenizer = loaded.tokenizer
    if not isinstance(model, torch.nn.Module):
        raise StageCCaptureError("LoadedModel.model is not a torch module")
    if getattr(model, "training", None) is not False:
        raise StageCCaptureError("Stage C model must already be in evaluation mode")
    _verify_model_config(model)
    if getattr(tokenizer, "name_or_path", None) != STAGEC_MODEL_ID:
        raise StageCCaptureError("LoadedModel tokenizer identity is not pinned Qwen")
    chat_template = getattr(tokenizer, "chat_template", None)
    if type(chat_template) is not str or not chat_template.strip():
        raise StageCCaptureError("LoadedModel tokenizer exposes no chat template")
    try:
        template_bytes = chat_template.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StageCCaptureError("chat template is not strict UTF-8") from exc
    manifest_bytes = _canonical_json_bytes(manifest.model_dump(mode="json"))
    return binding, model, tokenizer, template_bytes, _sha256_bytes(manifest_bytes)


def _plain_prompt_bytes(tokenizer: Any, prompt: Any) -> bytes:
    _require_text(prompt, field_name="request.prompt")
    try:
        raw = prompt.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StageCCaptureError("request prompt is not strict UTF-8") from exc
    special_tokens = set(_KNOWN_QWEN_CHAT_CONTROL_TOKENS)
    runtime_special = getattr(tokenizer, "all_special_tokens", ())
    if isinstance(runtime_special, (tuple, list, set, frozenset)):
        special_tokens.update(
            item for item in runtime_special if type(item) is str and item
        )
    if any(token in prompt for token in special_tokens):
        raise StageCCaptureError("request prompt contains a literal chat control token")
    return raw


def _render_and_tokenize(tokenizer: Any, prompt: str) -> tuple[str, Mapping[str, Any]]:
    apply_template = getattr(tokenizer, "apply_chat_template", None)
    if not callable(apply_template):
        raise StageCCaptureError("pinned tokenizer cannot apply its chat template")
    try:
        rendered = apply_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
    except Exception as exc:
        raise StageCCaptureError("chat-template rendering failed") from exc
    if type(rendered) is not str or not rendered or rendered == prompt:
        raise StageCCaptureError("chat-template rendering returned invalid text")
    try:
        rendered.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StageCCaptureError("rendered chat template is not strict UTF-8") from exc
    if not callable(tokenizer):
        raise StageCCaptureError("pinned tokenizer is not callable")
    try:
        encoded = tokenizer(
            rendered,
            add_special_tokens=False,
            truncation=False,
            return_attention_mask=True,
            return_tensors="pt",
        )
    except Exception as exc:
        raise StageCCaptureError("rendered-text tokenization failed") from exc
    if not isinstance(encoded, Mapping):
        raise StageCCaptureError("rendered-text tokenizer returned no mapping")
    return rendered, encoded


def _integer_input_tensor(value: Any, *, field_name: str) -> torch.Tensor:
    if type(value) is not torch.Tensor:
        raise StageCCaptureError(f"{field_name} must be an exact torch.Tensor")
    if value.ndim != 2 or int(value.shape[0]) != 1 or int(value.shape[1]) < 1:
        raise StageCCaptureError(f"{field_name} must have shape [1, sequence_length]")
    if value.dtype == torch.bool or torch.is_floating_point(value) or value.is_complex():
        raise StageCCaptureError(f"{field_name} must contain integer values")
    return value.detach().to(device="cpu", dtype=torch.int64).contiguous().clone()


def _marker_has_content(value: Any) -> bool:
    if value is None:
        return False
    if type(value) is torch.Tensor:
        return value.numel() > 0 and bool(torch.any(value != 0).item())
    if isinstance(value, (tuple, list, Mapping, str, bytes)):
        return len(value) > 0
    if type(value) is int:
        return value != 0
    return True


def _verify_no_truncation_markers(encoded: Mapping[str, Any]) -> None:
    if _marker_has_content(encoded.get("overflowing_tokens")):
        raise StageCCaptureError("tokenizer reported overflowing prompt tokens")
    if _marker_has_content(encoded.get("num_truncated_tokens")):
        raise StageCCaptureError("tokenizer reported truncated prompt tokens")


def _model_device(model: torch.nn.Module) -> torch.device:
    declared = getattr(model, "device", None)
    if declared is not None and torch.device(declared).type != "meta":
        return torch.device(declared)
    try:
        first = next(model.parameters())
    except StopIteration:
        return torch.device("cpu")
    device = torch.device(first.device)
    if device.type == "meta":
        raise StageCCaptureError("meta device cannot execute Stage C capture")
    return device


def _tensor_value_sha256(tensor: Any) -> str:
    if not isinstance(tensor, torch.Tensor):
        raise StageCCaptureError("endpoint value digest input is not a tensor")
    try:
        byte_view = tensor.detach().to(device="cpu").contiguous().view(torch.uint8)
        return _sha256_bytes(byte_view.numpy().tobytes(order="C"))
    except Exception as exc:
        raise StageCCaptureError("cannot compute endpoint tensor value digest") from exc


def _tensor_endpoint_signature(tensor: torch.Tensor) -> tuple[Any, ...]:
    return (
        id(tensor),
        tuple(int(item) for item in tensor.shape),
        tuple(int(item) for item in tensor.stride()),
        str(tensor.dtype),
        str(tensor.device),
        bool(tensor.requires_grad),
        _tensor_value_sha256(tensor),
    )


def _model_endpoint_snapshot(model: torch.nn.Module) -> tuple[tuple[Any, ...], ...]:
    rows: list[tuple[Any, ...]] = []
    try:
        parameters = tuple(model.named_parameters())
        buffers = tuple(model.named_buffers())
    except Exception as exc:
        raise StageCCaptureError("cannot enumerate model endpoint tensors") from exc
    for kind, values in (("parameter", parameters), ("buffer", buffers)):
        for name, tensor in values:
            if type(name) is not str or not isinstance(tensor, torch.Tensor):
                raise StageCCaptureError("model endpoint tensor enumeration drifted")
            rows.append((kind, name, *_tensor_endpoint_signature(tensor)))
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class _HookRegistryState:
    owner: Any = field(compare=False, repr=False)
    registry_name: str
    registry: OrderedDict[Any, Any] | None = field(compare=False, repr=False)
    entries: tuple[tuple[Any, Any], ...] = field(compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class _HookRegistrySnapshot:
    local_rows: tuple[tuple[Any, ...], ...]
    global_rows: tuple[tuple[Any, ...], ...]
    local_states: tuple[_HookRegistryState, ...] = field(compare=False, repr=False)
    global_states: tuple[_HookRegistryState, ...] = field(compare=False, repr=False)

    @property
    def digest(self) -> str:
        return _sha256_bytes(_canonical_json_bytes([self.local_rows, self.global_rows]))


def _registry_entries(value: Any, *, field_name: str) -> tuple[tuple[Any, ...], ...]:
    if value is None:
        return ()
    if type(value) is not OrderedDict:
        raise StageCCaptureError(f"{field_name} is not an exact OrderedDict registry")
    return tuple((repr(key), id(item)) for key, item in value.items())


def _hook_registry_snapshot(model: torch.nn.Module) -> _HookRegistrySnapshot:
    try:
        modules = tuple(model.named_modules())
    except Exception as exc:
        raise StageCCaptureError("cannot enumerate modules for hook audit") from exc
    local_rows: list[tuple[Any, ...]] = []
    local_states: list[_HookRegistryState] = []
    for name, module in modules:
        if type(name) is not str or not isinstance(module, torch.nn.Module):
            raise StageCCaptureError("module hook registry enumeration drifted")
        for registry_name in _LOCAL_HOOK_REGISTRIES:
            registry = getattr(module, registry_name, None)
            local_rows.append(
                (
                    name,
                    id(module),
                    registry_name,
                    id(registry) if registry is not None else None,
                    _registry_entries(
                        registry,
                        field_name=f"{name or '<root>'}.{registry_name}",
                    ),
                )
            )
            local_states.append(
                _HookRegistryState(
                    owner=module,
                    registry_name=registry_name,
                    registry=registry,
                    entries=() if registry is None else tuple(registry.items()),
                )
            )
    global_rows: list[tuple[Any, ...]] = []
    global_states: list[_HookRegistryState] = []
    for registry_name in _GLOBAL_HOOK_REGISTRIES:
        registry = getattr(torch_module_hooks, registry_name, None)
        global_rows.append(
            (
                registry_name,
                id(registry) if registry is not None else None,
                _registry_entries(registry, field_name=registry_name),
            )
        )
        global_states.append(
            _HookRegistryState(
                owner=torch_module_hooks,
                registry_name=registry_name,
                registry=registry,
                entries=() if registry is None else tuple(registry.items()),
            )
        )
    return _HookRegistrySnapshot(
        tuple(local_rows),
        tuple(global_rows),
        tuple(local_states),
        tuple(global_states),
    )


def _reject_existing_hooks(snapshot: _HookRegistrySnapshot) -> None:
    if any(row[-1] for row in snapshot.local_rows):
        raise StageCCaptureError("pre-existing local forward/pre-hook forbids capture")
    if any(row[-1] for row in snapshot.global_rows):
        raise StageCCaptureError("pre-existing global forward/pre-hook forbids capture")


def _remove_hook_identity_everywhere(model: torch.nn.Module, hook: Any) -> None:
    """Best-effort fallback for our own hook after a handle anomaly."""

    for module in model.modules():
        for registry_name in _LOCAL_HOOK_REGISTRIES:
            registry = getattr(module, registry_name, None)
            if not isinstance(registry, Mapping):
                continue
            for key, value in tuple(registry.items()):
                if value is hook:
                    try:
                        del registry[key]
                    except Exception:
                        pass
                    for companion_name in (
                        "_forward_pre_hooks_with_kwargs",
                        "_forward_hooks_with_kwargs",
                        "_forward_hooks_always_called",
                    ):
                        companion = getattr(module, companion_name, None)
                        if isinstance(companion, Mapping):
                            try:
                                companion.pop(key, None)
                            except Exception:
                                pass


def _restore_hook_registries_exactly(
    model: torch.nn.Module,
    baseline: _HookRegistrySnapshot,
) -> list[str]:
    """Restore every snapshotted registry object and ordered entry identity."""

    anomalies: list[str] = []
    baseline_module_ids = {id(state.owner) for state in baseline.local_states}
    try:
        current_modules = tuple(model.modules())
    except Exception as exc:
        anomalies.append(f"cannot enumerate modules during registry restoration: {exc}")
        current_modules = ()
    for module in current_modules:
        if id(module) in baseline_module_ids:
            continue
        for registry_name in _LOCAL_HOOK_REGISTRIES:
            introduced = getattr(module, registry_name, None)
            if type(introduced) is OrderedDict:
                try:
                    introduced.clear()
                except Exception as exc:
                    anomalies.append(
                        f"cannot clear introduced module registry {registry_name}: {exc}"
                    )

    for state in (*baseline.local_states, *baseline.global_states):
        current = getattr(state.owner, state.registry_name, None)
        if current is not state.registry:
            if type(current) is OrderedDict:
                try:
                    current.clear()
                except Exception as exc:
                    anomalies.append(
                        f"cannot clear replacement registry {state.registry_name}: {exc}"
                    )
            try:
                setattr(state.owner, state.registry_name, state.registry)
            except Exception as exc:
                anomalies.append(
                    f"cannot restore registry object {state.registry_name}: {exc}"
                )
                continue
        if state.registry is not None:
            try:
                state.registry.clear()
                state.registry.update(state.entries)
            except Exception as exc:
                anomalies.append(
                    f"cannot restore registry entries {state.registry_name}: {exc}"
                )
    return anomalies


def _verify_registered_hooks(
    *,
    model: torch.nn.Module,
    projections: Mapping[int, torch.nn.Module],
    hook_functions: Mapping[int, Any],
    handles: Mapping[int, RemovableHandle],
    baseline: _HookRegistrySnapshot,
) -> None:
    current = _hook_registry_snapshot(model)
    if current.global_rows != baseline.global_rows:
        raise StageCCaptureError("global hook registry changed during registration")
    if len(current.local_rows) != len(baseline.local_rows):
        raise StageCCaptureError("module topology changed during hook registration")
    expected_entries = {
        (id(projections[layer]), "_forward_pre_hooks"): (
            (repr(handles[layer].id), id(hook_functions[layer])),
        )
        for layer in STAGEC_CAPTURE_LAYERS
    }
    for before, after in zip(baseline.local_rows, current.local_rows, strict=True):
        if before[:4] != after[:4]:
            raise StageCCaptureError(
                "local hook registry topology/identity changed during registration"
            )
        expected = expected_entries.get((after[1], after[2]), ())
        if after[-1] != expected:
            raise StageCCaptureError("forward-pre-hook registration anomaly")


def _freeze_json(value: Any) -> Any:
    if type(value) is dict:
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    return value


@dataclass(frozen=True, slots=True, init=False)
class StageCCaptureIndex:
    """Decoded, strictly validated view of canonical capture-index bytes."""

    payload: Mapping[str, Any]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StageCCaptureError("capture index construction requires the strict loader")

    def to_payload(self) -> dict[str, Any]:
        return _thaw_json(self.payload)

    @property
    def telemetry(self) -> Mapping[str, Any]:
        return self.payload["telemetry"]

    @property
    def association(self) -> Mapping[str, Any]:
        return self.payload["association"]


_INDEX_KEYS = {
    "schema_version",
    "scope",
    "retention",
    "association",
    "identity",
    "prompt",
    "tokens",
    "activations",
    "logits",
    "hooks",
    "endpoint_checks",
    "telemetry",
}


def _validate_index_payload(payload: dict[str, Any]) -> None:
    _require_exact_keys(payload, _INDEX_KEYS, field_name="capture_index")
    if payload["schema_version"] != CAPTURE_INDEX_SCHEMA:
        raise StageCCaptureError("capture index schema version drifted")
    if payload["scope"] != STRUCTURE_ONLY_SCOPE:
        raise StageCCaptureError("capture index scope drifted")
    retention = _require_exact_keys(
        payload["retention"], {"location", "durability_status"}, field_name="retention"
    )
    if retention != {
        "location": IN_MEMORY_LOCATION,
        "durability_status": NOT_DURABLY_RETAINED,
    }:
        raise StageCCaptureError("capture index overclaims durable retention")

    association = _require_exact_keys(
        payload["association"],
        {
            "study_id", "case_id", "split_id", "base_intent_group_id",
            "frozen_variant", "frozen_label", "invocation_id", "plan_id",
            "request_artifact", "authorization_projection_artifact",
        },
        field_name="capture_index.association",
    )
    _validate_association_values(association)
    _require_text(association["plan_id"], field_name="plan_id", identifier=True)
    request_ref = ArtifactIdentity.from_payload(
        association["request_artifact"], field_name="association.request_artifact"
    )
    authorization_ref = ArtifactIdentity.from_payload(
        association["authorization_projection_artifact"],
        field_name="association.authorization_projection_artifact",
    )
    if request_ref.media_type != REQUEST_MEDIA_TYPE:
        raise StageCCaptureError("capture index request media type drifted")
    if authorization_ref.media_type != AUTHORIZATION_MEDIA_TYPE:
        raise StageCCaptureError("capture index authorization media type drifted")

    identity = _require_exact_keys(
        payload["identity"],
        {
            "status", "model_id", "tokenizer_id", "revision", "manifest_sha256",
            "model_config_artifact", "model_weights_artifact",
            "tokenizer_json_artifact", "tokenizer_config_artifact",
            "chat_template_artifact",
        },
        field_name="capture_index.identity",
    )
    if identity["status"] != LOADER_IDENTITY_STATUS:
        raise StageCCaptureError("capture identity status overclaims file revalidation")
    if (
        identity["model_id"] != STAGEC_MODEL_ID
        or identity["tokenizer_id"] != STAGEC_MODEL_ID
        or identity["revision"] != STAGEC_MODEL_REVISION
    ):
        raise StageCCaptureError("capture index Qwen identity drifted")
    _require_sha256(identity["manifest_sha256"], field_name="identity.manifest_sha256")
    identity_refs = {
        name: ArtifactIdentity.from_payload(identity[name], field_name=f"identity.{name}")
        for name in (
            "model_config_artifact", "model_weights_artifact",
            "tokenizer_json_artifact", "tokenizer_config_artifact",
            "chat_template_artifact",
        )
    }
    expected_pins = {
        "model_config_artifact": (STAGEC_MODEL_CONFIG_SHA256, STAGEC_MODEL_CONFIG_BYTES, "application/json"),
        "model_weights_artifact": (STAGEC_WEIGHTS_SHA256, STAGEC_WEIGHTS_BYTES, "application/vnd.safetensors"),
        "tokenizer_json_artifact": (STAGEC_TOKENIZER_JSON_SHA256, STAGEC_TOKENIZER_JSON_BYTES, "application/json"),
        "tokenizer_config_artifact": (STAGEC_TOKENIZER_CONFIG_SHA256, STAGEC_TOKENIZER_CONFIG_BYTES, "application/json"),
    }
    for name, expected in expected_pins.items():
        ref = identity_refs[name]
        if (ref.sha256.lower(), ref.byte_length, ref.media_type) != expected:
            raise StageCCaptureError(f"capture index identity pin drifted: {name}")
    if identity_refs["chat_template_artifact"].media_type != "text/plain;charset=utf-8":
        raise StageCCaptureError("chat template artifact media type drifted")

    prompt = _require_exact_keys(
        payload["prompt"],
        {
            "raw_utf8_sha256", "raw_utf8_byte_length",
            "rendered_utf8_sha256", "rendered_utf8_byte_length",
            "chat_template_application_count",
        },
        field_name="capture_index.prompt",
    )
    for name in ("raw_utf8_sha256", "rendered_utf8_sha256"):
        _require_sha256(prompt[name], field_name=f"prompt.{name}")
    for name in ("raw_utf8_byte_length", "rendered_utf8_byte_length"):
        _require_int(prompt[name], field_name=f"prompt.{name}", minimum=1)
    _require_int(
        prompt["chat_template_application_count"],
        field_name="prompt.chat_template_application_count",
        minimum=1,
        maximum=1,
    )
    if prompt["chat_template_application_count"] != 1:
        raise StageCCaptureError("chat template application count is not exactly one")

    tokens = _require_exact_keys(
        payload["tokens"],
        {
            "input_ids_artifact", "attention_mask_artifact", "sequence_length",
            "final_prompt_token_index", "final_prompt_token_id",
            "truncation_enabled", "truncation_occurred",
        },
        field_name="capture_index.tokens",
    )
    input_ref = RawArrayArtifactRef.from_payload(
        tokens["input_ids_artifact"], field_name="tokens.input_ids_artifact"
    )
    mask_ref = RawArrayArtifactRef.from_payload(
        tokens["attention_mask_artifact"], field_name="tokens.attention_mask_artifact"
    )
    sequence_length = _require_int(
        tokens["sequence_length"],
        field_name="tokens.sequence_length",
        minimum=1,
        maximum=STAGEC_MAX_SEQUENCE_LENGTH,
    )
    final_index = _require_int(
        tokens["final_prompt_token_index"],
        field_name="tokens.final_prompt_token_index",
        maximum=STAGEC_MAX_SEQUENCE_LENGTH - 1,
    )
    _require_int(
        tokens["final_prompt_token_id"],
        field_name="tokens.final_prompt_token_id",
        maximum=STAGEC_VOCAB_SIZE - 1,
    )
    if final_index != sequence_length - 1:
        raise StageCCaptureError("final prompt token index does not bind sequence end")
    if type(tokens["truncation_enabled"]) is not bool or type(tokens["truncation_occurred"]) is not bool:
        raise StageCCaptureError("truncation fields must be exact booleans")
    if tokens["truncation_enabled"] or tokens["truncation_occurred"]:
        raise StageCCaptureError("capture index claims truncation")
    expected_token_refs = (
        (input_ref, "input_ids", "<i8"),
        (mask_ref, "attention_mask", "<i8"),
    )
    for ref, role, dtype in expected_token_refs:
        if (
            ref.role != role
            or ref.dtype != dtype
            or ref.shape != (1, sequence_length)
            or ref.layer_index is not None
            or ref.module_path is not None
        ):
            raise StageCCaptureError(f"{role} array role/geometry drifted")

    activations = _require_exact_keys(
        payload["activations"], {"target", "wrong_layer"}, field_name="activations"
    )
    activation_specs = {
        "target": (STAGEC_TARGET_LAYER, STAGEC_TARGET_MODULE_PATH, "target_final_token_activation"),
        "wrong_layer": (STAGEC_WRONG_LAYER, STAGEC_WRONG_LAYER_MODULE_PATH, "wrong_layer_final_token_activation"),
    }
    activation_refs: dict[str, RawArrayArtifactRef] = {}
    for name, (layer, module_path, role) in activation_specs.items():
        item = _require_exact_keys(
            activations[name],
            {
                "array_artifact", "layer_index", "module_path",
                "source_dtype", "source_device", "source_autocast_enabled",
            },
            field_name=f"activations.{name}",
        )
        ref = RawArrayArtifactRef.from_payload(
            item["array_artifact"], field_name=f"activations.{name}.array_artifact"
        )
        activation_refs[name] = ref
        _require_int(
            item["layer_index"],
            field_name=f"activations.{name}.layer_index",
            maximum=STAGEC_LAYER_COUNT - 1,
        )
        if (
            item["layer_index"] != layer
            or item["module_path"] != module_path
            or ref.layer_index != layer
            or ref.module_path != module_path
            or ref.role != role
            or ref.dtype != "<f4"
            or ref.shape != (STAGEC_VECTOR_WIDTH,)
        ):
            raise StageCCaptureError(f"{name} activation role/layer/module drifted")
        _require_text(item["source_dtype"], field_name=f"activations.{name}.source_dtype")
        _require_text(item["source_device"], field_name=f"activations.{name}.source_device")
        if type(item["source_autocast_enabled"]) is not bool:
            raise StageCCaptureError("activation autocast field must be an exact boolean")

    logits = _require_exact_keys(
        payload["logits"],
        {"shape", "dtype", "device", "all_finite", "value_sha256"},
        field_name="logits",
    )
    if (
        type(logits["shape"]) is not list
        or len(logits["shape"]) != 3
        or any(type(item) is not int for item in logits["shape"])
        or logits["shape"] != [1, sequence_length, STAGEC_VOCAB_SIZE]
    ):
        raise StageCCaptureError("causal-LM logits shape drifted")
    _require_text(logits["dtype"], field_name="logits.dtype")
    _require_text(logits["device"], field_name="logits.device")
    if logits["all_finite"] is not True:
        raise StageCCaptureError("causal-LM logits are not finite")
    _require_sha256(logits["value_sha256"], field_name="logits.value_sha256")

    hooks = _require_exact_keys(
        payload["hooks"],
        {
            "registration_order", "firing_order", "cleanup_order",
            "wrong_layer_hook_count", "target_hook_count",
            "registries_before_sha256", "registries_after_sha256",
            "registry_status", "hook_return_status",
        },
        field_name="hooks",
    )
    for name in ("registration_order", "firing_order", "cleanup_order"):
        order = hooks[name]
        if type(order) is not list or any(type(item) is not int for item in order):
            raise StageCCaptureError(f"hook {name} must contain exact integers")
    if hooks["registration_order"] != [0, 18] or hooks["firing_order"] != [0, 18]:
        raise StageCCaptureError("hook registration/firing order drifted")
    if hooks["cleanup_order"] != [18, 0]:
        raise StageCCaptureError("hook cleanup order drifted")
    for name in ("wrong_layer_hook_count", "target_hook_count"):
        _require_int(
            hooks[name], field_name=f"hooks.{name}", minimum=1, maximum=1
        )
    if hooks["wrong_layer_hook_count"] != 1 or hooks["target_hook_count"] != 1:
        raise StageCCaptureError("hook cardinality drifted")
    for name in ("registries_before_sha256", "registries_after_sha256"):
        _require_sha256(hooks[name], field_name=f"hooks.{name}")
    if hooks["registries_before_sha256"] != hooks["registries_after_sha256"]:
        raise StageCCaptureError("hook registry digests do not prove exact cleanup")
    if hooks["registry_status"] != "LOCAL_AND_GLOBAL_FORWARD_PRE_HOOK_REGISTRIES_EXACTLY_RESTORED":
        raise StageCCaptureError("hook registry status drifted")
    if hooks["hook_return_status"] != "OBSERVATION_HOOKS_RETURNED_NONE":
        raise StageCCaptureError("hook return status drifted")

    endpoint = _require_exact_keys(
        payload["endpoint_checks"],
        {"input_tensors", "model_tensors", "output_logits"},
        field_name="endpoint_checks",
    )
    expected_endpoint = {
        "input_tensors": "METADATA_AND_VALUE_DIGEST_UNCHANGED_AT_CALL_ENDPOINTS",
        "model_tensors": "METADATA_AND_VALUE_DIGEST_UNCHANGED_AT_CALL_ENDPOINTS",
        "output_logits": "METADATA_FINITE_VALUE_DIGEST_OBSERVED_AT_RETURN",
    }
    if endpoint != expected_endpoint:
        raise StageCCaptureError("endpoint check wording/status drifted")

    telemetry = _require_exact_keys(
        payload["telemetry"],
        {
            "direct_capture_model_call_count", "direct_generate_api_call_count",
            "total_model_forward_count", "total_generation_count",
            "total_intervention_count", "startup_canary_count",
        },
        field_name="telemetry",
    )
    _require_int(
        telemetry["direct_capture_model_call_count"],
        field_name="telemetry.direct_capture_model_call_count",
        minimum=1,
        maximum=1,
    )
    _require_int(
        telemetry["direct_generate_api_call_count"],
        field_name="telemetry.direct_generate_api_call_count",
        maximum=0,
    )
    if telemetry["direct_capture_model_call_count"] != 1:
        raise StageCCaptureError("direct capture model-call count drifted")
    if telemetry["direct_generate_api_call_count"] != 0:
        raise StageCCaptureError("direct generate API-call count drifted")
    for name in (
        "total_model_forward_count", "total_generation_count",
        "total_intervention_count", "startup_canary_count",
    ):
        if telemetry[name] != NOT_ATTESTED:
            raise StageCCaptureError(f"{name} must remain NOT_ATTESTED")

    refs = [request_ref, authorization_ref, *identity_refs.values(), input_ref, mask_ref, *activation_refs.values()]
    ids = [ref.artifact_id for ref in refs]
    if len(ids) != len(set(ids)):
        raise StageCCaptureError("capture index artifact IDs are not globally unique")


def load_stagec_capture_index(artifact: Any) -> StageCCaptureIndex:
    payload = _load_json_artifact(
        artifact,
        media_type=CAPTURE_INDEX_MEDIA_TYPE,
        field_name="capture_index_artifact",
    )
    _validate_index_payload(payload)
    nested_ids = {
        payload["association"]["request_artifact"]["artifact_id"],
        payload["association"]["authorization_projection_artifact"]["artifact_id"],
        payload["tokens"]["input_ids_artifact"]["artifact_id"],
        payload["tokens"]["attention_mask_artifact"]["artifact_id"],
        payload["activations"]["target"]["array_artifact"]["artifact_id"],
        payload["activations"]["wrong_layer"]["array_artifact"]["artifact_id"],
        *(
            payload["identity"][name]["artifact_id"]
            for name in (
                "model_config_artifact",
                "model_weights_artifact",
                "tokenizer_json_artifact",
                "tokenizer_config_artifact",
                "chat_template_artifact",
            )
        ),
    }
    if artifact.ref.artifact_id in nested_ids:
        raise StageCCaptureError("capture index artifact ID overlaps a referenced artifact")
    index = object.__new__(StageCCaptureIndex)
    object.__setattr__(index, "payload", _freeze_json(payload))
    return index


def _decode_array(artifact: Any, *, expected_ref: RawArrayArtifactRef, field_name: str) -> np.ndarray:
    if type(artifact) is not RawArrayArtifact:
        raise StageCCaptureError(f"{field_name} must be an exact RawArrayArtifact")
    if type(artifact.ref) is not RawArrayArtifactRef:
        raise StageCCaptureError(f"{field_name} ref must be an exact RawArrayArtifactRef")
    if type(artifact.raw_bytes) is not bytes:
        raise StageCCaptureError(f"{field_name} payload must be immutable bytes")
    validated_ref = RawArrayArtifactRef.from_payload(
        artifact.ref.to_payload(), field_name=f"{field_name}.ref"
    )
    if validated_ref != artifact.ref:
        raise StageCCaptureError(f"{field_name} ref value drifted")
    if artifact.ref != expected_ref:
        raise StageCCaptureError(f"{field_name} does not bind its exact index role")
    if len(artifact.raw_bytes) != expected_ref.byte_length:
        raise StageCCaptureError(f"{field_name} byte length drifted")
    if _sha256_bytes(artifact.raw_bytes) != expected_ref.sha256:
        raise StageCCaptureError(f"{field_name} digest drifted")
    try:
        return np.frombuffer(artifact.raw_bytes, dtype=np.dtype(expected_ref.dtype)).reshape(expected_ref.shape)
    except (TypeError, ValueError) as exc:
        raise StageCCaptureError(f"{field_name} cannot be decoded exactly") from exc


@dataclass(frozen=True, slots=True, init=False, weakref_slot=True)
class StageCCaptureResult:
    """Self-contained in-memory bundle created only by the capture seam.

    Result replay additionally requires this process's capture-seam registration.
    Artifact replay proves byte/ref/semantic consistency only; promotion still
    requires a trusted external index ref/anchor.
    """

    index_artifact: CanonicalJsonArtifact
    request_artifact: CanonicalJsonArtifact
    authorization_projection_artifact: CanonicalJsonArtifact
    input_ids: RawArrayArtifact
    attention_mask: RawArrayArtifact
    target_vector: RawArrayArtifact
    wrong_layer_vector: RawArrayArtifact
    index: StageCCaptureIndex = field(init=False, repr=False)

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise StageCCaptureError(
            "direct StageCCaptureResult construction is forbidden; "
            "replay cannot confer provenance without an external anchor"
        )


_CAPTURE_RESULT_REGISTRY_LOCK = threading.Lock()
_CAPTURE_RESULT_REGISTRY: dict[
    int,
    tuple[weakref.ReferenceType[StageCCaptureResult], str],
] = {}


def _capture_result_seal(result: StageCCaptureResult) -> str:
    """Digest all immutable artifact fields, excluding the decoded index cache."""

    sealed: dict[str, Any] = {}
    for name, expected_type in (
        ("index_artifact", CanonicalJsonArtifact),
        ("request_artifact", CanonicalJsonArtifact),
        ("authorization_projection_artifact", CanonicalJsonArtifact),
        ("input_ids", RawArrayArtifact),
        ("attention_mask", RawArrayArtifact),
        ("target_vector", RawArrayArtifact),
        ("wrong_layer_vector", RawArrayArtifact),
    ):
        try:
            artifact = getattr(result, name)
        except AttributeError as exc:
            raise StageCCaptureError("capture result is structurally incomplete") from exc
        if type(artifact) is not expected_type:
            raise StageCCaptureError(f"capture result {name} has the wrong exact type")
        expected_ref_type = (
            ArtifactIdentity
            if expected_type is CanonicalJsonArtifact
            else RawArrayArtifactRef
        )
        if type(artifact.ref) is not expected_ref_type:
            raise StageCCaptureError(
                f"capture result {name} ref has the wrong exact type"
            )
        if type(artifact.raw_bytes) is not bytes:
            raise StageCCaptureError(
                f"capture result {name} payload must be immutable bytes"
            )
        sealed[name] = {
            "ref": artifact.ref.to_payload(),
            "raw_byte_length": len(artifact.raw_bytes),
            "raw_sha256": _sha256_bytes(artifact.raw_bytes),
        }
    return _sha256_bytes(_canonical_json_bytes(sealed))


def _register_capture_result(result: StageCCaptureResult) -> None:
    result_id = id(result)
    seal = _capture_result_seal(result)

    def discard(reference: weakref.ReferenceType[StageCCaptureResult]) -> None:
        with _CAPTURE_RESULT_REGISTRY_LOCK:
            current = _CAPTURE_RESULT_REGISTRY.get(result_id)
            if current is not None and current[0] is reference:
                _CAPTURE_RESULT_REGISTRY.pop(result_id, None)

    reference = weakref.ref(result, discard)
    with _CAPTURE_RESULT_REGISTRY_LOCK:
        _CAPTURE_RESULT_REGISTRY[result_id] = (reference, seal)


def _require_registered_capture_result(result: StageCCaptureResult) -> None:
    with _CAPTURE_RESULT_REGISTRY_LOCK:
        registered = _CAPTURE_RESULT_REGISTRY.get(id(result))
    if registered is None or registered[0]() is not result:
        raise StageCCaptureError(
            "capture result is not registered as capture-created in this process; "
            "artifact replay requires a trusted external index ref/anchor"
        )
    if _capture_result_seal(result) != registered[1]:
        raise StageCCaptureError("capture-created result artifact fields drifted after capture")


def replay_stagec_capture_artifacts(
    *,
    index_artifact: CanonicalJsonArtifact,
    request_artifact: CanonicalJsonArtifact,
    authorization_projection_artifact: CanonicalJsonArtifact,
    input_ids: RawArrayArtifact,
    attention_mask: RawArrayArtifact,
    target_vector: RawArrayArtifact,
    wrong_layer_vector: RawArrayArtifact,
) -> StageCCaptureIndex:
    """Replay exact artifacts without conferring capture provenance.

    A successful replay proves canonical byte/ref/semantic consistency only.
    A trusted external capture-index ref or durable anchor remains required.
    """

    authorization_artifact = authorization_projection_artifact
    array_artifacts = {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "target": target_vector,
        "wrong_layer": wrong_layer_vector,
    }
    index = load_stagec_capture_index(index_artifact)
    payload = index.to_payload()
    request = _validate_request_payload(
        _load_json_artifact(
            request_artifact,
            media_type=REQUEST_MEDIA_TYPE,
            field_name="request_artifact",
        )
    )
    authorization = _validate_authorization_payload(
        _load_json_artifact(
            authorization_artifact,
            media_type=AUTHORIZATION_MEDIA_TYPE,
            field_name="authorization_projection_artifact",
        ),
        request=request,
        request_ref=request_artifact.ref,
    )
    association = payload["association"]
    if association["request_artifact"] != request_artifact.ref.to_payload():
        raise StageCCaptureError("capture index binds a different request artifact")
    if association["authorization_projection_artifact"] != authorization_artifact.ref.to_payload():
        raise StageCCaptureError("capture index binds a different authorization projection")
    for name in (
        "study_id", "case_id", "split_id", "base_intent_group_id",
        "frozen_variant", "frozen_label", "invocation_id",
    ):
        if association[name] != request[name]:
            raise StageCCaptureError(f"capture index/request association drifted at {name}")
    if association["plan_id"] != authorization["plan_id"]:
        raise StageCCaptureError("capture index authorization plan drifted")
    prompt_bytes = request["prompt"].encode("utf-8", errors="strict")
    if (
        payload["prompt"]["raw_utf8_sha256"] != _sha256_bytes(prompt_bytes)
        or payload["prompt"]["raw_utf8_byte_length"] != len(prompt_bytes)
    ):
        raise StageCCaptureError("capture prompt digest/length does not derive from request bytes")

    token_payload = payload["tokens"]
    input_ref = RawArrayArtifactRef.from_payload(
        token_payload["input_ids_artifact"], field_name="tokens.input_ids_artifact"
    )
    mask_ref = RawArrayArtifactRef.from_payload(
        token_payload["attention_mask_artifact"], field_name="tokens.attention_mask_artifact"
    )
    activation_payload = payload["activations"]
    target_ref = RawArrayArtifactRef.from_payload(
        activation_payload["target"]["array_artifact"], field_name="activations.target.array_artifact"
    )
    wrong_ref = RawArrayArtifactRef.from_payload(
        activation_payload["wrong_layer"]["array_artifact"], field_name="activations.wrong_layer.array_artifact"
    )
    arrays = {
        "input_ids": _decode_array(array_artifacts["input_ids"], expected_ref=input_ref, field_name="input_ids"),
        "attention_mask": _decode_array(array_artifacts["attention_mask"], expected_ref=mask_ref, field_name="attention_mask"),
        "target": _decode_array(array_artifacts["target"], expected_ref=target_ref, field_name="target_vector"),
        "wrong_layer": _decode_array(array_artifacts["wrong_layer"], expected_ref=wrong_ref, field_name="wrong_layer_vector"),
    }
    input_ids = arrays["input_ids"]
    attention_mask = arrays["attention_mask"]
    if np.any(input_ids < 0) or np.any(input_ids >= STAGEC_VOCAB_SIZE):
        raise StageCCaptureError("replayed input_ids contain an out-of-range token")
    if not np.all(attention_mask == 1):
        raise StageCCaptureError("replayed attention_mask is not all ones")
    final_index = token_payload["final_prompt_token_index"]
    if int(input_ids[0, final_index]) != token_payload["final_prompt_token_id"]:
        raise StageCCaptureError("replayed final prompt token does not match the index")
    for name in ("target", "wrong_layer"):
        vector = arrays[name]
        if vector.shape != (STAGEC_VECTOR_WIDTH,) or not np.isfinite(vector).all():
            raise StageCCaptureError(f"replayed {name} vector is nonfinite or wrong width")

    all_ids = [
        index_artifact.ref.artifact_id,
        request_artifact.ref.artifact_id,
        authorization_artifact.ref.artifact_id,
        *(artifact.ref.artifact_id for artifact in array_artifacts.values()),
        *(
            payload["identity"][name]["artifact_id"]
            for name in (
                "model_config_artifact", "model_weights_artifact",
                "tokenizer_json_artifact", "tokenizer_config_artifact",
                "chat_template_artifact",
            )
        ),
    ]
    if len(all_ids) != len(set(all_ids)):
        raise StageCCaptureError("result artifact IDs are not globally unique")
    return index


def replay_stagec_capture_result(result: Any) -> StageCCaptureIndex:
    """Replay a result emitted and still registered by this capture process."""

    if type(result) is not StageCCaptureResult:
        raise StageCCaptureError("capture replay requires exact StageCCaptureResult")
    _require_registered_capture_result(result)
    try:
        cached_index = result.index
    except AttributeError as exc:
        raise StageCCaptureError("capture result decoded index cache is missing") from exc
    if type(cached_index) is not StageCCaptureIndex:
        raise StageCCaptureError("capture result decoded index cache has the wrong exact type")
    replayed = replay_stagec_capture_artifacts(
        index_artifact=result.index_artifact,
        request_artifact=result.request_artifact,
        authorization_projection_artifact=result.authorization_projection_artifact,
        input_ids=result.input_ids,
        attention_mask=result.attention_mask,
        target_vector=result.target_vector,
        wrong_layer_vector=result.wrong_layer_vector,
    )
    if cached_index.to_payload() != replayed.to_payload():
        raise StageCCaptureError("capture result decoded index cache drifted from exact bytes")
    return replayed


def _artifact_ref(artifact_id: str, sha_value: str, byte_length: int, media_type: str) -> ArtifactIdentity:
    return ArtifactIdentity(
        artifact_id=artifact_id,
        sha256=sha_value.upper(),
        byte_length=byte_length,
        media_type=media_type,
    )


class _StageCCaptureRuntimeEntry:
    """Factory-only one-use entry from the public gate to capture mechanics."""

    __slots__ = ()

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "_StageCCaptureRuntimeEntry":
        raise TypeError("Stage C capture runtime entries are factory-only")


@dataclass(slots=True)
class _StageCCaptureRuntimeRecord:
    entry: _StageCCaptureRuntimeEntry
    runtime_activation_envelope: (
        stagec_runtime_activation.StageCRuntimeActivationEnvelope
    )
    model_call_permit: stagec_runtime_activation.StageCModelCallPermit
    request_artifact: CanonicalJsonArtifact
    authorization_projection_artifact: CanonicalJsonArtifact
    artifact_ids: CaptureArtifactIds
    runtime_activation_sha256: str
    runtime_payload_sha256: str
    request_snapshot: tuple[Any, ...]
    authorization_snapshot: tuple[Any, ...]
    artifact_ids_snapshot: tuple[str, ...]
    phase: str = "ISSUED"
    redemption_attempted: bool = False
    model_call_redeemed: bool = False


_STAGEC_CAPTURE_RUNTIME_ENTRY_LOCK = threading.RLock()
_STAGEC_CAPTURE_RUNTIME_ENTRIES: dict[int, _StageCCaptureRuntimeRecord] = {}
_STAGEC_CAPTURE_BOUND_PERMITS: dict[
    int, stagec_runtime_activation.StageCModelCallPermit
] = {}


def _runtime_artifact_snapshot(artifact: CanonicalJsonArtifact) -> tuple[Any, ...]:
    return (
        artifact.ref.artifact_id,
        artifact.ref.sha256,
        artifact.ref.byte_length,
        artifact.ref.media_type,
        artifact.raw_bytes,
    )


def _runtime_artifact_ids_snapshot(
    artifact_ids: CaptureArtifactIds,
) -> tuple[str, ...]:
    return tuple(
        getattr(artifact_ids, name)
        for name in stagec_runtime_activation.STAGEC_CAPTURE_ARTIFACT_ID_FIELDS
    )


def _detach_runtime_json_artifact(
    artifact: Any,
    *,
    field_name: str,
) -> CanonicalJsonArtifact:
    """Build an exact private carrier without retaining caller-owned objects."""

    if type(artifact) is not CanonicalJsonArtifact:
        raise StageCCaptureError(
            f"{field_name} must be an exact CanonicalJsonArtifact"
        )
    try:
        original_ref = artifact.ref
        before = _runtime_artifact_snapshot(artifact)
        artifact_id, digest, byte_length, media_type, raw_bytes = before
        detached = CanonicalJsonArtifact(
            ref=ArtifactIdentity(
                artifact_id=artifact_id,
                sha256=digest,
                byte_length=byte_length,
                media_type=media_type,
            ),
            raw_bytes=raw_bytes,
        )
        if (
            artifact.ref is not original_ref
            or _runtime_artifact_snapshot(artifact) != before
        ):
            raise StageCCaptureError(
                f"{field_name} changed while its exact snapshot was taken"
            )
    except StageCCaptureError:
        raise
    except Exception as exc:
        raise StageCCaptureError(
            f"{field_name} cannot be detached as one exact artifact"
        ) from exc
    return detached


def _detach_runtime_artifact_ids(
    artifact_ids: Any,
) -> CaptureArtifactIds:
    if type(artifact_ids) is not CaptureArtifactIds:
        raise StageCCaptureError("artifact_ids must be exact CaptureArtifactIds")
    if tuple(artifact_ids.__slots__) != (
        stagec_runtime_activation.STAGEC_CAPTURE_ARTIFACT_ID_FIELDS
    ):
        raise _StageCRuntimeBindingError(
            "runtime/capture artifact-ID field order drifted"
        )
    try:
        before = _runtime_artifact_ids_snapshot(artifact_ids)
        detached = CaptureArtifactIds(
            **dict(
                zip(
                    stagec_runtime_activation.STAGEC_CAPTURE_ARTIFACT_ID_FIELDS,
                    before,
                    strict=True,
                )
            )
        )
        if _runtime_artifact_ids_snapshot(artifact_ids) != before:
            raise StageCCaptureError(
                "artifact_ids changed while their exact snapshot was taken"
            )
    except StageCCaptureError:
        raise
    except Exception as exc:
        raise StageCCaptureError(
            "artifact_ids cannot be detached as exact values"
        ) from exc
    return detached


def _detach_runtime_envelope(
    envelope: Any,
) -> stagec_runtime_activation.StageCRuntimeActivationEnvelope:
    if type(envelope) is not stagec_runtime_activation.StageCRuntimeActivationEnvelope:
        raise _StageCRuntimeBindingError(
            "runtime activation envelope has the wrong exact type"
        )
    try:
        raw_bytes = envelope.raw_bytes
        digest = envelope.sha256
        detached = stagec_runtime_activation.StageCRuntimeActivationEnvelope(
            raw_bytes=raw_bytes,
            sha256=digest,
        )
        stagec_runtime_activation.replay_stagec_runtime_activation_envelope(
            detached
        )
        if envelope.raw_bytes != raw_bytes or envelope.sha256 != digest:
            raise _StageCRuntimeBindingError(
                "runtime activation envelope changed while snapshotted"
            )
    except _StageCRuntimeBindingError:
        raise
    except Exception as exc:
        raise _StageCRuntimeBindingError(
            "runtime activation envelope cannot be detached exactly"
        ) from exc
    return detached


def _new_stagec_capture_runtime_entry(
    *,
    runtime_activation_envelope: (
        stagec_runtime_activation.StageCRuntimeActivationEnvelope
    ),
    model_call_permit: stagec_runtime_activation.StageCModelCallPermit,
    request_artifact: CanonicalJsonArtifact,
    authorization_projection_artifact: CanonicalJsonArtifact,
    artifact_ids: CaptureArtifactIds,
) -> _StageCCaptureRuntimeEntry:
    """Validate and snapshot one exact row; return only an opaque entry."""

    # This remains the first operation even for a direct call to this private
    # factory.  Wrong/reused permits never trigger request parsing or loading.
    stagec_runtime_activation.validate_stagec_model_call_permit(
        permit=model_call_permit,
        runtime_activation_envelope=runtime_activation_envelope,
    )
    terminal_envelope = runtime_activation_envelope
    try:
        exact_envelope = _detach_runtime_envelope(runtime_activation_envelope)
        terminal_envelope = exact_envelope
        exact_request_artifact = _detach_runtime_json_artifact(
            request_artifact,
            field_name="request_artifact",
        )
        exact_authorization_artifact = _detach_runtime_json_artifact(
            authorization_projection_artifact,
            field_name="authorization_projection_artifact",
        )
        exact_artifact_ids = _detach_runtime_artifact_ids(artifact_ids)
        runtime_payload = (
            stagec_runtime_activation.replay_stagec_runtime_activation_envelope(
                exact_envelope
            )
        )
        _validate_runtime_activation_capture_binding(
            runtime_activation_payload=runtime_payload,
            request_artifact=exact_request_artifact,
            authorization_projection_artifact=exact_authorization_artifact,
            artifact_ids=exact_artifact_ids,
        )
    except BaseException as primary_error:
        try:
            stagec_runtime_activation.invalidate_stagec_model_call_permit(
                permit=model_call_permit,
                runtime_activation_envelope=terminal_envelope,
                disposition=(
                    stagec_runtime_activation.StageCModelCallInvalidationDisposition.REJECTED
                ),
            )
        except BaseException as terminalization_error:
            raise StageCCaptureError(
                "runtime-entry binding failure could not be durably rejected"
            ) from terminalization_error
        raise primary_error

    entry = object.__new__(_StageCCaptureRuntimeEntry)
    record = _StageCCaptureRuntimeRecord(
        entry=entry,
        runtime_activation_envelope=exact_envelope,
        model_call_permit=model_call_permit,
        request_artifact=exact_request_artifact,
        authorization_projection_artifact=exact_authorization_artifact,
        artifact_ids=exact_artifact_ids,
        runtime_activation_sha256=exact_envelope.sha256,
        runtime_payload_sha256=_sha256_bytes(
            _canonical_json_bytes(runtime_payload)
        ),
        request_snapshot=_runtime_artifact_snapshot(exact_request_artifact),
        authorization_snapshot=_runtime_artifact_snapshot(
            exact_authorization_artifact
        ),
        artifact_ids_snapshot=_runtime_artifact_ids_snapshot(exact_artifact_ids),
    )
    with _STAGEC_CAPTURE_RUNTIME_ENTRY_LOCK:
        retained_permit = _STAGEC_CAPTURE_BOUND_PERMITS.get(id(model_call_permit))
        if retained_permit is not None:
            raise _StageCRuntimeBindingError(
                "model-call permit is already bound to a capture runtime entry"
            )
        _STAGEC_CAPTURE_BOUND_PERMITS[id(model_call_permit)] = model_call_permit
        _STAGEC_CAPTURE_RUNTIME_ENTRIES[id(entry)] = record
    return entry


def _require_stagec_capture_runtime_inputs_locked(
    entry: Any,
    *,
    phase: str,
) -> tuple[
    stagec_runtime_activation.StageCRuntimeActivationEnvelope,
    CanonicalJsonArtifact,
    CanonicalJsonArtifact,
    CaptureArtifactIds,
]:
    if type(entry) is not _StageCCaptureRuntimeEntry:
        raise _StageCRuntimeBindingError(
            "capture mechanics received no sealed runtime entry"
        )
    record = _STAGEC_CAPTURE_RUNTIME_ENTRIES.get(id(entry))
    try:
        if (
            record is None
            or record.entry is not entry
            or record.phase != phase
            or type(record.runtime_activation_envelope)
            is not stagec_runtime_activation.StageCRuntimeActivationEnvelope
            or record.runtime_activation_sha256
            != record.runtime_activation_envelope.sha256
            or type(record.request_artifact) is not CanonicalJsonArtifact
            or type(record.authorization_projection_artifact)
            is not CanonicalJsonArtifact
            or type(record.artifact_ids) is not CaptureArtifactIds
            or record.request_snapshot
            != _runtime_artifact_snapshot(record.request_artifact)
            or record.authorization_snapshot
            != _runtime_artifact_snapshot(
                record.authorization_projection_artifact
            )
            or record.artifact_ids_snapshot
            != _runtime_artifact_ids_snapshot(record.artifact_ids)
        ):
            raise _StageCRuntimeBindingError(
                "capture runtime entry private snapshots drifted"
            )
        runtime_payload = (
            stagec_runtime_activation.replay_stagec_runtime_activation_envelope(
                record.runtime_activation_envelope
            )
        )
        if record.runtime_payload_sha256 != _sha256_bytes(
            _canonical_json_bytes(runtime_payload)
        ):
            raise _StageCRuntimeBindingError(
                "capture runtime entry payload snapshot drifted"
            )
    except _StageCRuntimeBindingError:
        raise
    except Exception as exc:
        raise _StageCRuntimeBindingError(
            "capture runtime entry private snapshots cannot be replayed"
        ) from exc
    return (
        record.runtime_activation_envelope,
        record.request_artifact,
        record.authorization_projection_artifact,
        record.artifact_ids,
    )


def _stagec_capture_runtime_inputs(
    entry: Any,
    *,
    phase: str,
) -> tuple[
    stagec_runtime_activation.StageCRuntimeActivationEnvelope,
    CanonicalJsonArtifact,
    CanonicalJsonArtifact,
    CaptureArtifactIds,
]:
    with _STAGEC_CAPTURE_RUNTIME_ENTRY_LOCK:
        return _require_stagec_capture_runtime_inputs_locked(entry, phase=phase)


def _consume_stagec_capture_runtime_entry(
    entry: Any,
    *,
    runtime_activation_payload: dict[str, Any],
    request_artifact: CanonicalJsonArtifact,
    authorization_projection_artifact: CanonicalJsonArtifact,
    artifact_ids: CaptureArtifactIds,
) -> tuple[
    dict[str, Any],
    CanonicalJsonArtifact,
    CanonicalJsonArtifact,
    CaptureArtifactIds,
]:
    with _STAGEC_CAPTURE_RUNTIME_ENTRY_LOCK:
        (
            runtime_envelope,
            exact_request_artifact,
            exact_authorization_artifact,
            exact_artifact_ids,
        ) = _require_stagec_capture_runtime_inputs_locked(entry, phase="ISSUED")
        record = _STAGEC_CAPTURE_RUNTIME_ENTRIES[id(entry)]
        try:
            supplied_payload_sha256 = _sha256_bytes(
                _canonical_json_bytes(runtime_activation_payload)
            )
            supplied_request_snapshot = _runtime_artifact_snapshot(
                request_artifact
            )
            supplied_authorization_snapshot = _runtime_artifact_snapshot(
                authorization_projection_artifact
            )
            supplied_artifact_ids_snapshot = _runtime_artifact_ids_snapshot(
                artifact_ids
            )
        except Exception as exc:
            raise _StageCRuntimeBindingError(
                "capture runtime entry inputs cannot be snapshotted"
            ) from exc
        if (
            record.runtime_payload_sha256 != supplied_payload_sha256
            or record.request_snapshot != supplied_request_snapshot
            or record.authorization_snapshot != supplied_authorization_snapshot
            or record.artifact_ids_snapshot != supplied_artifact_ids_snapshot
        ):
            raise _StageCRuntimeBindingError(
                "capture runtime entry binding is invalid, substituted, or consumed"
            )
        record.phase = "CONSUMED"
        exact_payload = (
            stagec_runtime_activation.replay_stagec_runtime_activation_envelope(
                runtime_envelope
            )
        )
        _require_stagec_capture_runtime_inputs_locked(entry, phase="CONSUMED")
    return (
        exact_payload,
        exact_request_artifact,
        exact_authorization_artifact,
        exact_artifact_ids,
    )


def _stagec_capture_runtime_status(
    entry: _StageCCaptureRuntimeEntry | None,
) -> tuple[bool, bool]:
    if entry is None:
        return False, False
    with _STAGEC_CAPTURE_RUNTIME_ENTRY_LOCK:
        record = _STAGEC_CAPTURE_RUNTIME_ENTRIES.get(id(entry))
        if record is None or record.entry is not entry:
            # Missing state after issuance is ambiguous.  Treat it as if model
            # redemption may have started so no caller can reopen the claim.
            return True, False
        return record.redemption_attempted, record.model_call_redeemed


def _discard_stagec_capture_runtime_entry(
    entry: _StageCCaptureRuntimeEntry | None,
) -> None:
    if entry is None:
        return
    with _STAGEC_CAPTURE_RUNTIME_ENTRY_LOCK:
        retained = _STAGEC_CAPTURE_RUNTIME_ENTRIES.get(id(entry))
        if retained is not None and retained.entry is entry:
            del _STAGEC_CAPTURE_RUNTIME_ENTRIES[id(entry)]


def _validate_runtime_activation_capture_binding(
    *,
    runtime_activation_payload: dict[str, Any],
    request_artifact: CanonicalJsonArtifact,
    authorization_projection_artifact: CanonicalJsonArtifact,
    artifact_ids: CaptureArtifactIds,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind the authenticated row envelope to exact local capture inputs."""

    request = _validate_request_payload(
        _load_json_artifact(
            request_artifact,
            media_type=REQUEST_MEDIA_TYPE,
            field_name="request_artifact",
        )
    )
    authorization = _validate_authorization_payload(
        _load_json_artifact(
            authorization_projection_artifact,
            media_type=AUTHORIZATION_MEDIA_TYPE,
            field_name="authorization_projection_artifact",
        ),
        request=request,
        request_ref=request_artifact.ref,
    )
    if type(artifact_ids) is not CaptureArtifactIds:
        raise StageCCaptureError("artifact_ids must be exact CaptureArtifactIds")
    if tuple(artifact_ids.__slots__) != (
        stagec_runtime_activation.STAGEC_CAPTURE_ARTIFACT_ID_FIELDS
    ):
        raise _StageCRuntimeBindingError(
            "runtime/capture artifact-ID field order drifted"
        )
    all_prospective_ids = (
        request_artifact.ref.artifact_id,
        authorization_projection_artifact.ref.artifact_id,
        *(getattr(artifact_ids, name) for name in artifact_ids.__slots__),
    )
    if len(all_prospective_ids) != len(set(all_prospective_ids)):
        raise _StageCRuntimeBindingError(
            "request/auth/capture artifact IDs are not globally unique"
        )

    if runtime_activation_payload["request_artifact_identity"] != (
        request_artifact.ref.to_payload()
    ):
        raise _StageCRuntimeBindingError(
            "runtime activation binds a different request artifact"
        )
    if runtime_activation_payload[
        "authorization_projection_artifact_identity"
    ] != authorization_projection_artifact.ref.to_payload():
        raise _StageCRuntimeBindingError(
            "runtime activation binds a different authorization projection"
        )
    expected_capture_ids = {
        name: getattr(artifact_ids, name)
        for name in stagec_runtime_activation.STAGEC_CAPTURE_ARTIFACT_ID_FIELDS
    }
    if runtime_activation_payload["capture_artifact_ids"] != expected_capture_ids:
        raise _StageCRuntimeBindingError(
            "runtime activation capture artifact IDs drifted"
        )
    if runtime_activation_payload["attempt"]["case_id"] != request["case_id"]:
        raise _StageCRuntimeBindingError("runtime activation binds a different case")

    model_identity = runtime_activation_payload["model_identity"]
    expected_model_identity = {
        "model_id": STAGEC_MODEL_ID,
        "model_revision": STAGEC_MODEL_REVISION,
        "model_config_sha256": STAGEC_MODEL_CONFIG_SHA256.upper(),
        "weights_sha256": STAGEC_WEIGHTS_SHA256.upper(),
        "tokenizer_json_sha256": STAGEC_TOKENIZER_JSON_SHA256.upper(),
        "tokenizer_config_sha256": STAGEC_TOKENIZER_CONFIG_SHA256.upper(),
    }
    for field_name, expected in expected_model_identity.items():
        if model_identity[field_name] != expected:
            raise _StageCRuntimeBindingError(
                f"runtime activation model identity drifted: {field_name}"
            )
    if model_identity["capture_profile_sha256"] != STAGEC_CAPTURE_PROFILE_SHA256:
        raise _StageCRuntimeBindingError(
            "runtime activation model identity drifted: capture_profile_sha256"
        )
    return request, authorization


def capture_stagec_qwen_w0(
    *,
    request_artifact: CanonicalJsonArtifact,
    authorization_projection_artifact: CanonicalJsonArtifact,
    artifact_ids: CaptureArtifactIds,
    runtime_activation_envelope: (
        stagec_runtime_activation.StageCRuntimeActivationEnvelope
    ),
    model_call_permit: stagec_runtime_activation.StageCModelCallPermit,
) -> StageCCaptureResult:
    """Execute one exactly bound capture through the authenticated choke point."""

    # The factory's first operation validates the permit.  It also snapshots
    # every exact local input and terminalizes any deterministic substitution
    # before model loading.  It returns only this opaque one-use entry.
    runtime_entry = _new_stagec_capture_runtime_entry(
        runtime_activation_envelope=runtime_activation_envelope,
        model_call_permit=model_call_permit,
        request_artifact=request_artifact,
        authorization_projection_artifact=authorization_projection_artifact,
        artifact_ids=artifact_ids,
    )
    exact_runtime_envelope = runtime_activation_envelope
    invalidation_disposition = (
        stagec_runtime_activation.StageCModelCallInvalidationDisposition.INDETERMINATE
    )

    try:
        (
            exact_runtime_envelope,
            exact_request_artifact,
            exact_authorization_artifact,
            exact_artifact_ids,
        ) = _stagec_capture_runtime_inputs(runtime_entry, phase="ISSUED")
        runtime_payload = (
            stagec_runtime_activation.replay_stagec_runtime_activation_envelope(
                exact_runtime_envelope
            )
        )
        result = _capture_stagec_qwen_w0_after_runtime_gate(
            request_artifact=exact_request_artifact,
            authorization_projection_artifact=exact_authorization_artifact,
            artifact_ids=exact_artifact_ids,
            runtime_activation_payload=runtime_payload,
            runtime_entry=runtime_entry,
        )
        _, model_call_redeemed = _stagec_capture_runtime_status(runtime_entry)
        if not model_call_redeemed:
            raise StageCCaptureError("capture returned without redeeming its model-call permit")
        _discard_stagec_capture_runtime_entry(runtime_entry)
        return result
    except BaseException as primary_error:
        redemption_attempted, _ = _stagec_capture_runtime_status(runtime_entry)
        _discard_stagec_capture_runtime_entry(runtime_entry)
        # A redemption attempt is already terminal: either CALL_STARTED was
        # durably recorded, or the gate burned it as indeterminate.  Never
        # attempt to reopen or re-terminalize that claim.
        if not redemption_attempted:
            if isinstance(primary_error, _StageCRuntimeBindingError):
                invalidation_disposition = (
                    stagec_runtime_activation.StageCModelCallInvalidationDisposition.REJECTED
                )
            try:
                stagec_runtime_activation.invalidate_stagec_model_call_permit(
                    permit=model_call_permit,
                    runtime_activation_envelope=exact_runtime_envelope,
                    disposition=invalidation_disposition,
                )
            except BaseException as terminalization_error:
                raise StageCCaptureError(
                    "pre-model-call failure could not be durably invalidated"
                ) from terminalization_error
        raise primary_error


def _capture_stagec_qwen_w0_after_runtime_gate(
    *,
    request_artifact: CanonicalJsonArtifact,
    authorization_projection_artifact: CanonicalJsonArtifact,
    artifact_ids: CaptureArtifactIds,
    runtime_activation_payload: dict[str, Any],
    runtime_entry: _StageCCaptureRuntimeEntry,
) -> StageCCaptureResult:
    """Run capture mechanics only after exact runtime entry validation."""

    (
        runtime_activation_payload,
        request_artifact,
        authorization_projection_artifact,
        artifact_ids,
    ) = _consume_stagec_capture_runtime_entry(
        runtime_entry,
        runtime_activation_payload=runtime_activation_payload,
        request_artifact=request_artifact,
        authorization_projection_artifact=authorization_projection_artifact,
        artifact_ids=artifact_ids,
    )
    request, authorization = _validate_runtime_activation_capture_binding(
        runtime_activation_payload=runtime_activation_payload,
        request_artifact=request_artifact,
        authorization_projection_artifact=authorization_projection_artifact,
        artifact_ids=artifact_ids,
    )

    all_prospective_ids = (
        request_artifact.ref.artifact_id,
        authorization_projection_artifact.ref.artifact_id,
        *(getattr(artifact_ids, name) for name in artifact_ids.__slots__),
    )
    if len(all_prospective_ids) != len(set(all_prospective_ids)):
        raise StageCCaptureError("request/auth/capture artifact IDs are not globally unique")

    try:
        loaded = model_loader.get_loaded_model()
    except Exception as exc:
        raise StageCCaptureError("cannot obtain the model-loader singleton carrier") from exc
    binding, model, tokenizer, template_bytes, manifest_sha = _verify_loaded_carrier(loaded)
    if runtime_activation_payload["model_identity"]["chat_template_sha256"] != (
        _sha256_bytes(template_bytes)
    ):
        raise _StageCRuntimeBindingError(
            "runtime activation chat-template digest drifted"
        )
    manifest_object = loaded.manifest
    raw_prompt = _plain_prompt_bytes(tokenizer, request["prompt"])
    rendered, encoded = _render_and_tokenize(tokenizer, request["prompt"])
    rendered_bytes = rendered.encode("utf-8", errors="strict")
    _verify_no_truncation_markers(encoded)
    input_ids_cpu = _integer_input_tensor(encoded.get("input_ids"), field_name="input_ids")
    attention_mask_cpu = _integer_input_tensor(encoded.get("attention_mask"), field_name="attention_mask")
    if tuple(input_ids_cpu.shape) != tuple(attention_mask_cpu.shape):
        raise StageCCaptureError("input_ids and attention_mask shapes differ")
    if bool(torch.any(input_ids_cpu < 0).item()) or bool(torch.any(input_ids_cpu >= STAGEC_VOCAB_SIZE).item()):
        raise StageCCaptureError("input_ids contain an out-of-range token ID")
    if not bool(torch.all(attention_mask_cpu == 1).item()):
        raise StageCCaptureError("unpadded Stage C attention_mask must be all ones")
    sequence_length = int(input_ids_cpu.shape[1])
    if sequence_length > STAGEC_MAX_SEQUENCE_LENGTH:
        raise StageCCaptureError("templated prompt exceeds the pinned model length")
    tokenizer_limit = getattr(tokenizer, "model_max_length", None)
    if type(tokenizer_limit) is int and 0 < tokenizer_limit < sequence_length:
        raise StageCCaptureError("templated prompt exceeds the tokenizer model length")
    final_index = sequence_length - 1
    final_token_id = int(input_ids_cpu[0, final_index].item())

    input_artifact = _raw_array_artifact(
        artifact_id=artifact_ids.input_ids,
        tensor=input_ids_cpu,
        dtype="<i8",
        role="input_ids",
        layer_index=None,
        module_path=None,
    )
    mask_artifact = _raw_array_artifact(
        artifact_id=artifact_ids.attention_mask,
        tensor=attention_mask_cpu,
        dtype="<i8",
        role="attention_mask",
        layer_index=None,
        module_path=None,
    )

    baseline_hooks = _hook_registry_snapshot(model)
    _reject_existing_hooks(baseline_hooks)
    try:
        layers = model_loader.resolve_probe_layer_stack(
            model,
            binding,
            expected_layers=STAGEC_LAYER_COUNT,
            require_exact_count=True,
        )
        projections = {
            layer: model_loader.resolve_probe_projection(
                layers[layer], binding, layer_index=layer
            )
            for layer in STAGEC_CAPTURE_LAYERS
        }
    except Exception as exc:
        raise StageCCaptureError("exact Qwen Stage C hook geometry is unavailable") from exc

    captures: dict[int, torch.Tensor] = {}
    sources: dict[int, dict[str, Any]] = {}
    firing_order: list[int] = []
    hook_counts = {layer: 0 for layer in STAGEC_CAPTURE_LAYERS}
    hook_functions: dict[int, Any] = {}
    handles: list[tuple[int, Any]] = []
    registered_handles: dict[int, RemovableHandle] = {}
    cleanup_order: list[int] = []
    anomalies: list[str] = []

    def make_hook(layer: int) -> Any:
        def capture_hook(_module: Any, args: tuple[Any, ...]) -> None:
            expected_ordinal = len(firing_order)
            if expected_ordinal >= 2 or STAGEC_CAPTURE_LAYERS[expected_ordinal] != layer:
                raise StageCCaptureError("Stage C hooks fired out of exact layer order")
            if type(args) is not tuple or len(args) != 1 or type(args[0]) is not torch.Tensor:
                raise StageCCaptureError("down_proj pre-hook input contract drifted")
            activation = args[0]
            expected_shape = (1, sequence_length, STAGEC_VECTOR_WIDTH)
            if tuple(int(item) for item in activation.shape) != expected_shape:
                raise StageCCaptureError("down_proj pre-hook activation geometry drifted")
            if not bool(torch.isfinite(activation).all().item()):
                raise StageCCaptureError("down_proj pre-hook activation is nonfinite")
            hook_counts[layer] += 1
            if hook_counts[layer] != 1:
                raise StageCCaptureError("Stage C hook fired more than once")
            captures[layer] = (
                activation.detach()[0, final_index, :]
                .to(device="cpu", dtype=torch.float32)
                .contiguous()
                .clone()
            )
            sources[layer] = {
                "source_dtype": str(activation.dtype),
                "source_device": str(activation.device),
                "source_autocast_enabled": bool(
                    torch.is_autocast_enabled(activation.device.type)
                ),
            }
            firing_order.append(layer)
            return None

        return capture_hook

    for layer in STAGEC_CAPTURE_LAYERS:
        hook_functions[layer] = make_hook(layer)

    device = _model_device(model)
    input_ids = input_ids_cpu.to(device=device, dtype=torch.int64).contiguous()
    attention_mask = attention_mask_cpu.to(device=device, dtype=torch.int64).contiguous()
    input_before = (_tensor_endpoint_signature(input_ids), _tensor_endpoint_signature(attention_mask))
    model_before = _model_endpoint_snapshot(model)
    direct_model_calls = 0
    output: Any = None
    primary_error: BaseException | None = None
    try:
        for layer in STAGEC_CAPTURE_LAYERS:
            handle = projections[layer].register_forward_pre_hook(hook_functions[layer])
            if handle is not None and callable(getattr(handle, "remove", None)):
                handles.append((layer, handle))
            if (
                type(handle) is not RemovableHandle
                or type(handle.id) is not int
                or not callable(getattr(handle, "remove", None))
            ):
                raise StageCCaptureError(
                    "forward-pre-hook registration anomaly: no exact RemovableHandle"
                )
            registered_handles[layer] = handle
        _verify_registered_hooks(
            model=model,
            projections=projections,
            hook_functions=hook_functions,
            handles=registered_handles,
            baseline=baseline_hooks,
        )
        with torch.inference_mode():
            with _STAGEC_CAPTURE_RUNTIME_ENTRY_LOCK:
                runtime_record = _STAGEC_CAPTURE_RUNTIME_ENTRIES.get(
                    id(runtime_entry)
                )
                if (
                    runtime_record is None
                    or runtime_record.entry is not runtime_entry
                    or runtime_record.phase != "CONSUMED"
                    or runtime_record.redemption_attempted
                ):
                    raise _StageCRuntimeBindingError(
                        "capture runtime entry cannot reach the model-call boundary"
                    )
                runtime_record.redemption_attempted = True
                runtime_envelope = runtime_record.runtime_activation_envelope
                runtime_permit = runtime_record.model_call_permit
            stagec_runtime_activation.redeem_stagec_model_call_permit(
                permit=runtime_permit,
                runtime_activation_envelope=runtime_envelope,
            )
            with _STAGEC_CAPTURE_RUNTIME_ENTRY_LOCK:
                current_record = _STAGEC_CAPTURE_RUNTIME_ENTRIES.get(
                    id(runtime_entry)
                )
                if (
                    current_record is not runtime_record
                    or current_record.entry is not runtime_entry
                    or current_record.phase != "CONSUMED"
                    or not current_record.redemption_attempted
                    or current_record.model_call_redeemed
                ):
                    raise _StageCRuntimeBindingError(
                        "capture runtime redemption acknowledgement drifted"
                    )
                current_record.model_call_redeemed = True
            direct_model_calls += 1
            output = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                use_cache=False,
                output_attentions=False,
                output_hidden_states=False,
                return_dict=True,
            )
    except BaseException as exc:
        primary_error = exc
    finally:
        for layer, handle in reversed(handles):
            try:
                handle.remove()
                cleanup_order.append(layer)
            except Exception as exc:
                anomalies.append(f"layer {layer} remove raised: {exc}")
            finally:
                hooks = getattr(projections[layer], "_forward_pre_hooks", None)
                if isinstance(hooks, Mapping) and any(
                    candidate is hook_functions[layer] for candidate in hooks.values()
                ):
                    anomalies.append(f"layer {layer} remove left its hook registered")
        for hook in hook_functions.values():
            _remove_hook_identity_everywhere(model, hook)
        try:
            observed_hooks = _hook_registry_snapshot(model)
        except Exception as exc:
            anomalies.append(f"cannot inspect hook registries before restoration: {exc}")
        else:
            if observed_hooks != baseline_hooks:
                anomalies.append(
                    "local/global hook registries did not exactly match baseline "
                    "before cleanup restoration"
                )
        anomalies.extend(_restore_hook_registries_exactly(model, baseline_hooks))
        try:
            after_hooks = _hook_registry_snapshot(model)
        except Exception as exc:
            anomalies.append(f"cannot verify hook registries after restoration: {exc}")
            after_hooks = baseline_hooks
        else:
            if after_hooks != baseline_hooks:
                anomalies.append(
                    "local/global hook registries did not exactly match baseline "
                    "after cleanup restoration"
                )
    if anomalies:
        raise StageCCaptureError("Stage C hook registration/removal anomaly: " + "; ".join(anomalies)) from primary_error
    if primary_error is not None:
        if isinstance(primary_error, StageCCaptureError):
            raise primary_error
        raise StageCCaptureError("Stage C direct prefill call failed") from primary_error
    if direct_model_calls != 1 or output is None:
        raise StageCCaptureError("Stage C direct model-call cardinality/output drifted")
    if tuple(firing_order) != STAGEC_CAPTURE_LAYERS or hook_counts != {0: 1, 18: 1}:
        raise StageCCaptureError("Stage C hook firing cardinality/order is incomplete")
    if tuple(cleanup_order) != tuple(reversed(STAGEC_CAPTURE_LAYERS)):
        raise StageCCaptureError("Stage C hook cleanup order is incomplete")
    if (_tensor_endpoint_signature(input_ids), _tensor_endpoint_signature(attention_mask)) != input_before:
        raise StageCCaptureError("input endpoint metadata/value digest changed")
    if _model_endpoint_snapshot(model) != model_before:
        raise StageCCaptureError("model endpoint metadata/value digest changed")
    if getattr(model, "training", None) is not False:
        raise StageCCaptureError("model evaluation-mode endpoint changed")
    _verify_model_config(model)
    try:
        loaded_after = model_loader.get_loaded_model()
    except Exception as exc:
        raise StageCCaptureError("cannot re-obtain the model-loader singleton carrier") from exc
    if loaded_after is not loaded:
        raise StageCCaptureError("model-loader singleton carrier identity changed")
    if loaded.model is not model or loaded.tokenizer is not tokenizer:
        raise StageCCaptureError("LoadedModel model/tokenizer carrier identity changed")
    if getattr(tokenizer, "name_or_path", None) != STAGEC_MODEL_ID:
        raise StageCCaptureError("LoadedModel tokenizer identity changed during capture")
    current_template = getattr(tokenizer, "chat_template", None)
    if type(current_template) is not str:
        raise StageCCaptureError("LoadedModel chat-template identity changed during capture")
    try:
        current_template_bytes = current_template.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise StageCCaptureError("LoadedModel chat template became invalid UTF-8") from exc
    if current_template_bytes != template_bytes:
        raise StageCCaptureError("LoadedModel chat-template bytes changed during capture")
    if loaded.manifest is not manifest_object or loaded.load_error is not None:
        raise StageCCaptureError("LoadedModel manifest/load-error carrier identity changed")
    try:
        if loaded.is_real is not True:
            raise StageCCaptureError("LoadedModel.is_real changed after capture")
        manifest_after = _canonical_json_bytes(loaded.manifest.model_dump(mode="json"))
    except StageCCaptureError:
        raise
    except Exception as exc:
        raise StageCCaptureError("LoadedModel post-capture verification failed") from exc
    if _sha256_bytes(manifest_after) != manifest_sha:
        raise StageCCaptureError("LoadedModel manifest value changed during capture")
    logits = getattr(output, "logits", None)
    if type(logits) is not torch.Tensor:
        raise StageCCaptureError("causal-LM output exposes no exact logits tensor")
    expected_logits_shape = (1, sequence_length, STAGEC_VOCAB_SIZE)
    if tuple(int(item) for item in logits.shape) != expected_logits_shape:
        raise StageCCaptureError(f"causal-LM logits shape is not {expected_logits_shape}")
    if not bool(torch.isfinite(logits).all().item()):
        raise StageCCaptureError("causal-LM logits contain nonfinite values")
    logits_digest = _tensor_value_sha256(logits)

    # Final private-snapshot check: everything below emits artifacts/results,
    # so prove the entry still owns the same detached inputs used at the call.
    (
        final_runtime_envelope,
        final_request_artifact,
        final_authorization_artifact,
        final_artifact_ids,
    ) = _stagec_capture_runtime_inputs(runtime_entry, phase="CONSUMED")
    if (
        final_runtime_envelope.sha256
        != _sha256_bytes(final_runtime_envelope.raw_bytes)
        or final_request_artifact is not request_artifact
        or final_authorization_artifact is not authorization_projection_artifact
        or final_artifact_ids is not artifact_ids
    ):
        raise _StageCRuntimeBindingError(
            "capture runtime private input identity drifted before result emission"
        )

    wrong_artifact = _raw_array_artifact(
        artifact_id=artifact_ids.wrong_layer_vector,
        tensor=captures[STAGEC_WRONG_LAYER],
        dtype="<f4",
        role="wrong_layer_final_token_activation",
        layer_index=STAGEC_WRONG_LAYER,
        module_path=STAGEC_WRONG_LAYER_MODULE_PATH,
    )
    target_artifact = _raw_array_artifact(
        artifact_id=artifact_ids.target_vector,
        tensor=captures[STAGEC_TARGET_LAYER],
        dtype="<f4",
        role="target_final_token_activation",
        layer_index=STAGEC_TARGET_LAYER,
        module_path=STAGEC_TARGET_MODULE_PATH,
    )
    model_config_ref = _artifact_ref(
        artifact_ids.model_config, STAGEC_MODEL_CONFIG_SHA256, STAGEC_MODEL_CONFIG_BYTES, "application/json"
    )
    model_weights_ref = _artifact_ref(
        artifact_ids.model_weights, STAGEC_WEIGHTS_SHA256, STAGEC_WEIGHTS_BYTES, "application/vnd.safetensors"
    )
    tokenizer_json_ref = _artifact_ref(
        artifact_ids.tokenizer_json, STAGEC_TOKENIZER_JSON_SHA256, STAGEC_TOKENIZER_JSON_BYTES, "application/json"
    )
    tokenizer_config_ref = _artifact_ref(
        artifact_ids.tokenizer_config, STAGEC_TOKENIZER_CONFIG_SHA256, STAGEC_TOKENIZER_CONFIG_BYTES, "application/json"
    )
    chat_template_ref = _artifact_ref(
        artifact_ids.chat_template, _sha256_bytes(template_bytes), len(template_bytes), "text/plain;charset=utf-8"
    )
    index_payload = {
        "schema_version": CAPTURE_INDEX_SCHEMA,
        "scope": STRUCTURE_ONLY_SCOPE,
        "retention": {
            "location": IN_MEMORY_LOCATION,
            "durability_status": NOT_DURABLY_RETAINED,
        },
        "association": {
            **{name: request[name] for name in (
                "study_id", "case_id", "split_id", "base_intent_group_id",
                "frozen_variant", "frozen_label", "invocation_id",
            )},
            "plan_id": authorization["plan_id"],
            "request_artifact": request_artifact.ref.to_payload(),
            "authorization_projection_artifact": authorization_projection_artifact.ref.to_payload(),
        },
        "identity": {
            "status": LOADER_IDENTITY_STATUS,
            "model_id": STAGEC_MODEL_ID,
            "tokenizer_id": STAGEC_MODEL_ID,
            "revision": STAGEC_MODEL_REVISION,
            "manifest_sha256": manifest_sha,
            "model_config_artifact": model_config_ref.to_payload(),
            "model_weights_artifact": model_weights_ref.to_payload(),
            "tokenizer_json_artifact": tokenizer_json_ref.to_payload(),
            "tokenizer_config_artifact": tokenizer_config_ref.to_payload(),
            "chat_template_artifact": chat_template_ref.to_payload(),
        },
        "prompt": {
            "raw_utf8_sha256": _sha256_bytes(raw_prompt),
            "raw_utf8_byte_length": len(raw_prompt),
            "rendered_utf8_sha256": _sha256_bytes(rendered_bytes),
            "rendered_utf8_byte_length": len(rendered_bytes),
            "chat_template_application_count": 1,
        },
        "tokens": {
            "input_ids_artifact": input_artifact.ref.to_payload(),
            "attention_mask_artifact": mask_artifact.ref.to_payload(),
            "sequence_length": sequence_length,
            "final_prompt_token_index": final_index,
            "final_prompt_token_id": final_token_id,
            "truncation_enabled": False,
            "truncation_occurred": False,
        },
        "activations": {
            "wrong_layer": {
                "array_artifact": wrong_artifact.ref.to_payload(),
                "layer_index": STAGEC_WRONG_LAYER,
                "module_path": STAGEC_WRONG_LAYER_MODULE_PATH,
                **sources[STAGEC_WRONG_LAYER],
            },
            "target": {
                "array_artifact": target_artifact.ref.to_payload(),
                "layer_index": STAGEC_TARGET_LAYER,
                "module_path": STAGEC_TARGET_MODULE_PATH,
                **sources[STAGEC_TARGET_LAYER],
            },
        },
        "logits": {
            "shape": list(expected_logits_shape),
            "dtype": str(logits.dtype),
            "device": str(logits.device),
            "all_finite": True,
            "value_sha256": logits_digest,
        },
        "hooks": {
            "registration_order": list(STAGEC_CAPTURE_LAYERS),
            "firing_order": firing_order,
            "cleanup_order": cleanup_order,
            "wrong_layer_hook_count": hook_counts[STAGEC_WRONG_LAYER],
            "target_hook_count": hook_counts[STAGEC_TARGET_LAYER],
            "registries_before_sha256": baseline_hooks.digest,
            "registries_after_sha256": after_hooks.digest,
            "registry_status": "LOCAL_AND_GLOBAL_FORWARD_PRE_HOOK_REGISTRIES_EXACTLY_RESTORED",
            "hook_return_status": "OBSERVATION_HOOKS_RETURNED_NONE",
        },
        "endpoint_checks": {
            "input_tensors": "METADATA_AND_VALUE_DIGEST_UNCHANGED_AT_CALL_ENDPOINTS",
            "model_tensors": "METADATA_AND_VALUE_DIGEST_UNCHANGED_AT_CALL_ENDPOINTS",
            "output_logits": "METADATA_FINITE_VALUE_DIGEST_OBSERVED_AT_RETURN",
        },
        "telemetry": {
            "direct_capture_model_call_count": 1,
            "direct_generate_api_call_count": 0,
            "total_model_forward_count": NOT_ATTESTED,
            "total_generation_count": NOT_ATTESTED,
            "total_intervention_count": NOT_ATTESTED,
            "startup_canary_count": NOT_ATTESTED,
        },
    }
    _validate_index_payload(index_payload)
    index_artifact = _json_artifact(
        artifact_id=artifact_ids.capture_index,
        media_type=CAPTURE_INDEX_MEDIA_TYPE,
        payload=index_payload,
    )
    decoded_index = replay_stagec_capture_artifacts(
        index_artifact=index_artifact,
        request_artifact=request_artifact,
        authorization_projection_artifact=authorization_projection_artifact,
        input_ids=input_artifact,
        attention_mask=mask_artifact,
        target_vector=target_artifact,
        wrong_layer_vector=wrong_artifact,
    )
    result = object.__new__(StageCCaptureResult)
    for name, value in (
        ("index_artifact", index_artifact),
        ("request_artifact", request_artifact),
        ("authorization_projection_artifact", authorization_projection_artifact),
        ("input_ids", input_artifact),
        ("attention_mask", mask_artifact),
        ("target_vector", target_artifact),
        ("wrong_layer_vector", wrong_artifact),
        ("index", decoded_index),
    ):
        object.__setattr__(result, name, value)
    _register_capture_result(result)
    replay_stagec_capture_result(result)
    return result


__all__ = [
    "AUTHORIZATION_MEDIA_TYPE",
    "AUTHORIZATION_SCHEMA",
    "ArtifactIdentity",
    "CAPTURE_INDEX_MEDIA_TYPE",
    "CAPTURE_INDEX_SCHEMA",
    "CanonicalJsonArtifact",
    "CaptureArtifactIds",
    "IN_MEMORY_LOCATION",
    "LOADER_IDENTITY_STATUS",
    "NON_AUTHORITY_STATUS",
    "NOT_ATTESTED",
    "NOT_DURABLY_RETAINED",
    "RAW_ARRAY_FORMAT",
    "RAW_ARRAY_LAYOUT",
    "RAW_ARRAY_MEDIA_TYPE",
    "REQUEST_MEDIA_TYPE",
    "REQUEST_SCHEMA",
    "RawArrayArtifact",
    "RawArrayArtifactRef",
    "STAGEC_CAPTURE_PROFILE_SHA256",
    "STAGEC_MODEL_ID",
    "STAGEC_MODEL_REVISION",
    "STAGEC_TARGET_MODULE_PATH",
    "STAGEC_TARGET_LAYER",
    "STAGEC_TOKENIZER_CONFIG_BYTES",
    "STAGEC_TOKENIZER_CONFIG_SHA256",
    "STAGEC_TOKENIZER_JSON_BYTES",
    "STAGEC_TOKENIZER_JSON_SHA256",
    "STAGEC_VECTOR_WIDTH",
    "STAGEC_VOCAB_SIZE",
    "STAGEC_WRONG_LAYER",
    "STAGEC_WRONG_LAYER_MODULE_PATH",
    "STRUCTURE_ONLY_SCOPE",
    "StageCCaptureError",
    "StageCCaptureIndex",
    "StageCCaptureResult",
    "build_stagec_authorization_projection_artifact",
    "build_stagec_request_artifact",
    "capture_stagec_qwen_w0",
    "load_stagec_capture_index",
    "replay_stagec_capture_artifacts",
    "replay_stagec_capture_result",
]
