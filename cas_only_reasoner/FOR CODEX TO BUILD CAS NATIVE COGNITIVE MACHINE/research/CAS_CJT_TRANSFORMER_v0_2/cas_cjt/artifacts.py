"""Content-addressed binary artifacts for the Neural CJT runtime.

Authoritative JSON stores only immutable artifact references.  Tensor and model
bytes live in the same durable SQLite transaction as the state version that
starts referring to them.  A digest binds the artifact kind, media type,
encoding, metadata, and exact payload bytes.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from typing import Any, Mapping

import torch
from torch import Tensor


ARTIFACT_ENCODING = "raw-contiguous-v1"


class ArtifactError(ValueError):
    """An artifact or its reference failed a closed integrity check."""


def _json_primitive(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ArtifactError("artifact metadata cannot contain non-finite floats")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ArtifactError("artifact metadata mapping keys must be strings")
        return {key: _json_primitive(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_json_primitive(item) for item in value]
    raise ArtifactError(f"unsupported artifact metadata value: {type(value).__name__}")


def canonical_json(value: Any) -> str:
    return json.dumps(
        _json_primitive(value),
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _bound_digest(
    *,
    kind: str,
    media_type: str,
    encoding: str,
    metadata: Mapping[str, Any],
    payload: bytes,
) -> str:
    header = canonical_json(
        {
            "encoding": encoding,
            "kind": kind,
            "media_type": media_type,
            "metadata": metadata,
            "payload_byte_length": len(payload),
        }
    ).encode("ascii")
    return sha256(header + b"\n" + payload).hexdigest()


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    """An immutable binary artifact and its content-derived identity."""

    artifact_id: str
    sha256: str
    kind: str
    media_type: str
    encoding: str
    metadata_json: str
    payload: bytes

    @property
    def byte_length(self) -> int:
        return len(self.payload)

    @property
    def metadata(self) -> dict[str, Any]:
        try:
            value = json.loads(self.metadata_json)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ArtifactError("artifact metadata is not canonical JSON") from exc
        if not isinstance(value, dict):
            raise ArtifactError("artifact metadata must be an object")
        if canonical_json(value) != self.metadata_json:
            raise ArtifactError("artifact metadata is not canonically encoded")
        return value

    def verify(self) -> None:
        if not isinstance(self.payload, bytes):
            raise ArtifactError("artifact payload must be immutable bytes")
        if not all(
            isinstance(value, str) and value
            for value in (self.artifact_id, self.kind, self.media_type, self.encoding)
        ):
            raise ArtifactError("artifact identity fields must be nonempty strings")
        metadata = self.metadata
        expected = _bound_digest(
            kind=self.kind,
            media_type=self.media_type,
            encoding=self.encoding,
            metadata=metadata,
            payload=self.payload,
        )
        if self.sha256 != expected:
            raise ArtifactError("artifact digest mismatch")
        if self.artifact_id != f"artifact-{expected[:24]}":
            raise ArtifactError("artifact_id is not content-derived")

    def public_descriptor(self) -> dict[str, Any]:
        """Return a reference that never includes private tensor/model bytes."""

        self.verify()
        return {
            "artifact_id": self.artifact_id,
            "sha256": self.sha256,
            "kind": self.kind,
            "media_type": self.media_type,
            "encoding": self.encoding,
            "byte_length": self.byte_length,
            "metadata": self.metadata,
            "redacted": True,
        }


def make_artifact(
    payload: bytes | bytearray | memoryview,
    *,
    kind: str,
    media_type: str = "application/octet-stream",
    encoding: str = "opaque-v1",
    metadata: Mapping[str, Any] | None = None,
) -> StoredArtifact:
    """Create a content-addressed immutable artifact."""

    if not all(isinstance(value, str) and value for value in (kind, media_type, encoding)):
        raise ArtifactError("artifact kind, media_type, and encoding must be nonempty strings")
    body = bytes(payload)
    normalized_metadata = _json_primitive({} if metadata is None else metadata)
    assert isinstance(normalized_metadata, dict)
    metadata_json = canonical_json(normalized_metadata)
    digest = _bound_digest(
        kind=kind,
        media_type=media_type,
        encoding=encoding,
        metadata=normalized_metadata,
        payload=body,
    )
    artifact = StoredArtifact(
        artifact_id=f"artifact-{digest[:24]}",
        sha256=digest,
        kind=kind,
        media_type=media_type,
        encoding=encoding,
        metadata_json=metadata_json,
        payload=body,
    )
    artifact.verify()
    return artifact


_DTYPE_TO_NAME: dict[torch.dtype, str] = {
    torch.bool: "bool",
    torch.uint8: "uint8",
    torch.int8: "int8",
    torch.int16: "int16",
    torch.int32: "int32",
    torch.int64: "int64",
    torch.float16: "float16",
    torch.bfloat16: "bfloat16",
    torch.float32: "float32",
    torch.float64: "float64",
}
_NAME_TO_DTYPE = {name: dtype for dtype, name in _DTYPE_TO_NAME.items()}


def encode_tensor(
    value: Tensor,
    *,
    kind: str = "tensor",
    allow_nonfinite: bool = False,
) -> tuple[dict[str, Any], StoredArtifact]:
    """Encode a tensor as deterministic contiguous CPU bytes.

    The returned mapping matches the public ``TensorArtifactRef`` field names.
    The exact bytes are never included in that mapping.
    """

    if not isinstance(value, Tensor):
        raise ArtifactError("value must be a torch.Tensor")
    if value.dtype not in _DTYPE_TO_NAME:
        raise ArtifactError(f"unsupported tensor dtype: {value.dtype}")
    detached = value.detach().to(device="cpu").contiguous()
    if detached.numel() == 0:
        # TensorArtifactRef.byte_length is deliberately positive.  Keeping the
        # codec on the same side of that frozen contract avoids references
        # which can be stored but cannot be represented by the public type.
        raise ArtifactError("empty tensors are not valid authoritative artifacts")
    if detached.is_floating_point() and not allow_nonfinite:
        if not bool(torch.isfinite(detached).all().item()):
            raise ArtifactError("authoritative tensor artifacts must be finite")
    shape = [int(size) for size in detached.shape]
    payload = detached.view(torch.uint8).reshape(-1).numpy().tobytes(order="C")
    dtype_name = _DTYPE_TO_NAME[detached.dtype]
    metadata = {
        "dtype": dtype_name,
        "numel": int(detached.numel()),
        "shape": shape,
    }
    artifact = make_artifact(
        payload,
        kind=kind,
        media_type="application/vnd.cas.tensor",
        encoding=ARTIFACT_ENCODING,
        metadata=metadata,
    )
    reference = {
        "artifact_id": artifact.artifact_id,
        "sha256": artifact.sha256,
        "dtype": dtype_name,
        "shape": shape,
        "encoding": ARTIFACT_ENCODING,
        "byte_length": artifact.byte_length,
    }
    return reference, artifact


def _reference_mapping(reference: Any) -> dict[str, Any]:
    required = ("artifact_id", "sha256", "dtype", "shape", "encoding", "byte_length")
    if isinstance(reference, Mapping):
        mapped = dict(reference)
        if all(field in mapped for field in required):
            return {field: mapped[field] for field in required}
        return mapped
    to_dict = getattr(reference, "to_dict", None)
    if callable(to_dict):
        value = to_dict()
        if isinstance(value, Mapping):
            mapped = dict(value)
            if all(field in mapped for field in required):
                return {field: mapped[field] for field in required}
            return mapped
    if all(hasattr(reference, field) for field in required):
        return {field: getattr(reference, field) for field in required}
    raise ArtifactError("tensor reference must be a mapping or TensorArtifactRef-like object")


def decode_tensor(reference: Any, artifact: StoredArtifact) -> Tensor:
    """Verify and decode one tensor artifact without pickle execution."""

    artifact.verify()
    ref = _reference_mapping(reference)
    required = {"artifact_id", "sha256", "dtype", "shape", "encoding", "byte_length"}
    if set(ref) != required:
        raise ArtifactError("tensor reference fields do not match the frozen contract")
    if ref["artifact_id"] != artifact.artifact_id or ref["sha256"] != artifact.sha256:
        raise ArtifactError("tensor reference does not bind the supplied artifact")
    if ref["encoding"] != ARTIFACT_ENCODING or artifact.encoding != ARTIFACT_ENCODING:
        raise ArtifactError("unsupported tensor encoding")
    if ref["byte_length"] != artifact.byte_length:
        raise ArtifactError("tensor byte length mismatch")
    dtype = _NAME_TO_DTYPE.get(ref["dtype"])
    shape = ref["shape"]
    if dtype is None or not isinstance(shape, (tuple, list)) or any(
        not isinstance(size, int) or isinstance(size, bool) or size < 0 for size in shape
    ):
        raise ArtifactError("tensor dtype or shape is invalid")
    shape = list(shape)
    metadata = artifact.metadata
    if metadata != {
        "dtype": ref["dtype"],
        "numel": math.prod(shape),
        "shape": shape,
    }:
        raise ArtifactError("tensor metadata/reference mismatch")
    element_size = torch.empty((), dtype=dtype).element_size()
    expected_length = math.prod(shape) * element_size
    if expected_length != artifact.byte_length:
        raise ArtifactError("tensor payload length does not match dtype and shape")
    if expected_length == 0:
        return torch.empty(tuple(shape), dtype=dtype)
    # bytearray gives PyTorch writable owned input; clone detaches from it.
    tensor = torch.frombuffer(bytearray(artifact.payload), dtype=dtype).clone()
    return tensor.reshape(tuple(shape))


def make_model_artifact(
    payload: bytes | bytearray | memoryview,
    *,
    format_name: str,
    metadata: Mapping[str, Any] | None = None,
) -> StoredArtifact:
    """Create an opaque model/checkpoint artifact.

    Loading policy belongs to the model runtime.  This module never unpickles a
    model artifact.
    """

    if not isinstance(format_name, str) or not format_name:
        raise ArtifactError("format_name must be a nonempty string")
    combined_metadata = {"format": format_name, **({} if metadata is None else dict(metadata))}
    return make_artifact(
        payload,
        kind="model",
        media_type="application/vnd.cas.model",
        encoding="opaque-model-v1",
        metadata=combined_metadata,
    )


__all__ = [
    "ARTIFACT_ENCODING",
    "ArtifactError",
    "StoredArtifact",
    "canonical_json",
    "decode_tensor",
    "encode_tensor",
    "make_artifact",
    "make_model_artifact",
]
