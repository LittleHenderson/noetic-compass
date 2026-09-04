"""Deterministic, non-pickle Neural CJT checkpoint artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import math
from typing import Any, Mapping

import torch
from torch import Tensor, nn

from .artifacts import ArtifactError, StoredArtifact, make_artifact
from .state import tensor_ref_from_mapping
from .types import TensorArtifactRef


CHECKPOINT_ENCODING = "cas-neural-cjt-state-dict-v1"

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


class CheckpointError(ValueError):
    """Checkpoint bytes or module geometry violated the frozen codec."""


@dataclass(frozen=True, slots=True)
class CheckpointBundle:
    reference: TensorArtifactRef
    artifact: StoredArtifact

    @property
    def model_digest(self) -> str:
        return self.artifact.sha256


def _tensor_bytes(value: Tensor) -> bytes:
    detached = value.detach().to(device="cpu").contiguous()
    if detached.numel() == 0:
        return b""
    return detached.view(torch.uint8).reshape(-1).numpy().tobytes(order="C")


def encode_module_checkpoint(module: nn.Module) -> CheckpointBundle:
    """Encode the exact state_dict in canonical key order without pickle."""

    if not isinstance(module, nn.Module):
        raise CheckpointError("module must be a torch.nn.Module")
    payload_parts: list[bytes] = []
    entries: list[dict[str, Any]] = []
    offset = 0
    state = module.state_dict()
    if not state:
        raise CheckpointError("a Neural CJT checkpoint cannot be empty")
    for name in sorted(state):
        value = state[name]
        if value.dtype not in _DTYPE_TO_NAME:
            raise CheckpointError(f"unsupported checkpoint dtype for {name}: {value.dtype}")
        detached = value.detach().to(device="cpu").contiguous()
        if detached.is_floating_point() and not bool(torch.isfinite(detached).all().item()):
            raise CheckpointError(f"checkpoint tensor {name} is non-finite")
        raw = _tensor_bytes(detached)
        entries.append(
            {
                "name": name,
                "dtype": _DTYPE_TO_NAME[detached.dtype],
                "shape": [int(size) for size in detached.shape],
                "offset": offset,
                "byte_length": len(raw),
            }
        )
        payload_parts.append(raw)
        offset += len(raw)
    payload = b"".join(payload_parts)
    if not payload:
        raise CheckpointError("a Neural CJT checkpoint must contain parameter bytes")
    artifact = make_artifact(
        payload,
        kind="model",
        media_type="application/vnd.cas.neural-cjt-checkpoint",
        encoding=CHECKPOINT_ENCODING,
        metadata={
            "codec": CHECKPOINT_ENCODING,
            "entry_count": len(entries),
            "entries": entries,
            "total_byte_length": len(payload),
        },
    )
    reference = tensor_ref_from_mapping(
        {
            "artifact_id": artifact.artifact_id,
            "sha256": artifact.sha256,
            "dtype": "state-dict-bundle",
            "shape": [len(payload)],
            "encoding": CHECKPOINT_ENCODING,
            "byte_length": len(payload),
        }
    )
    return CheckpointBundle(reference=reference, artifact=artifact)


def _entry_tensor(entry: Mapping[str, Any], payload: bytes) -> Tensor:
    try:
        dtype = _NAME_TO_DTYPE[str(entry["dtype"])]
        shape = tuple(int(size) for size in entry["shape"])
        offset = int(entry["offset"])
        byte_length = int(entry["byte_length"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CheckpointError("checkpoint entry metadata is malformed") from exc
    if any(size < 0 for size in shape) or offset < 0 or byte_length < 0:
        raise CheckpointError("checkpoint entry contains a negative geometry value")
    element_size = torch.empty((), dtype=dtype).element_size()
    if math.prod(shape) * element_size != byte_length:
        raise CheckpointError("checkpoint entry byte length does not match dtype and shape")
    end = offset + byte_length
    if end > len(payload):
        raise CheckpointError("checkpoint entry points outside the artifact")
    if byte_length == 0:
        return torch.empty(shape, dtype=dtype)
    return torch.frombuffer(bytearray(payload[offset:end]), dtype=dtype).clone().reshape(shape)


def verify_checkpoint(reference: TensorArtifactRef, artifact: StoredArtifact) -> bool:
    """Verify the reference, content digest, metadata, and non-overlapping layout."""

    try:
        artifact.verify()
        if (
            reference.artifact_id != artifact.artifact_id
            or reference.sha256 != artifact.sha256
            or reference.encoding != CHECKPOINT_ENCODING
            or artifact.encoding != CHECKPOINT_ENCODING
            or reference.byte_length != len(artifact.payload)
            or tuple(reference.shape) != (len(artifact.payload),)
            or reference.dtype != "state-dict-bundle"
        ):
            return False
        metadata = artifact.metadata
        if (
            metadata.get("codec") != CHECKPOINT_ENCODING
            or metadata.get("total_byte_length") != len(artifact.payload)
            or not isinstance(metadata.get("entries"), list)
            or metadata.get("entry_count") != len(metadata["entries"])
        ):
            return False
        expected_offset = 0
        names: list[str] = []
        for entry in metadata["entries"]:
            if not isinstance(entry, Mapping) or entry.get("offset") != expected_offset:
                return False
            name = entry.get("name")
            if not isinstance(name, str) or not name:
                return False
            names.append(name)
            value = _entry_tensor(entry, artifact.payload)
            if value.is_floating_point() and not bool(torch.isfinite(value).all().item()):
                return False
            expected_offset += int(entry["byte_length"])
        return (
            expected_offset == len(artifact.payload)
            and names == sorted(names)
            and len(names) == len(set(names))
        )
    except (ArtifactError, CheckpointError, KeyError, TypeError, ValueError):
        return False


def load_module_checkpoint(
    module: nn.Module,
    reference: TensorArtifactRef,
    artifact: StoredArtifact,
) -> None:
    """Load an exact compatible checkpoint after all checks pass."""

    if not verify_checkpoint(reference, artifact):
        raise CheckpointError("checkpoint reference or artifact failed verification")
    metadata = artifact.metadata
    decoded = {
        str(entry["name"]): _entry_tensor(entry, artifact.payload)
        for entry in metadata["entries"]
    }
    expected = module.state_dict()
    if set(decoded) != set(expected):
        raise CheckpointError("checkpoint keys do not match the Neural CJT module")
    for name, target in expected.items():
        candidate = decoded[name]
        if candidate.shape != target.shape or candidate.dtype != target.dtype:
            raise CheckpointError(f"checkpoint tensor {name} has incompatible geometry")
    module.load_state_dict(decoded, strict=True)


def changed_parameter_names(before: nn.Module, after: nn.Module) -> tuple[str, ...]:
    """Return exact state_dict keys whose bytes differ."""

    left = before.state_dict()
    right = after.state_dict()
    if set(left) != set(right):
        raise CheckpointError("models do not share a checkpoint layout")
    return tuple(
        name
        for name in sorted(left)
        if left[name].dtype != right[name].dtype
        or left[name].shape != right[name].shape
        or not torch.equal(left[name].detach().cpu(), right[name].detach().cpu())
    )


def checkpoint_entry_digests(
    reference: TensorArtifactRef,
    artifact: StoredArtifact,
) -> dict[str, dict[str, Any]]:
    """Expose per-state-entry byte hashes without decoding a model class."""

    if not verify_checkpoint(reference, artifact):
        raise CheckpointError("checkpoint failed verification")
    result: dict[str, dict[str, Any]] = {}
    for entry in artifact.metadata["entries"]:
        offset = int(entry["offset"])
        byte_length = int(entry["byte_length"])
        raw = artifact.payload[offset : offset + byte_length]
        result[str(entry["name"])] = {
            "dtype": str(entry["dtype"]),
            "shape": list(entry["shape"]),
            "byte_length": byte_length,
            "sha256": sha256(raw).hexdigest(),
        }
    return result


def diff_checkpoint_artifacts(
    before_reference: TensorArtifactRef,
    before_artifact: StoredArtifact,
    after_reference: TensorArtifactRef,
    after_artifact: StoredArtifact,
) -> tuple[str, ...]:
    """Independently identify exact parameter entries changed by a proposal."""

    before = checkpoint_entry_digests(before_reference, before_artifact)
    after = checkpoint_entry_digests(after_reference, after_artifact)
    if set(before) != set(after):
        raise CheckpointError("candidate checkpoint changes the state_dict key set")
    for name in before:
        if (
            before[name]["dtype"] != after[name]["dtype"]
            or before[name]["shape"] != after[name]["shape"]
            or before[name]["byte_length"] != after[name]["byte_length"]
        ):
            raise CheckpointError(f"candidate checkpoint changes geometry for {name}")
    return tuple(
        name for name in sorted(before) if before[name]["sha256"] != after[name]["sha256"]
    )


__all__ = [
    "CHECKPOINT_ENCODING",
    "CheckpointBundle",
    "CheckpointError",
    "changed_parameter_names",
    "checkpoint_entry_digests",
    "diff_checkpoint_artifacts",
    "encode_module_checkpoint",
    "load_module_checkpoint",
    "verify_checkpoint",
]
