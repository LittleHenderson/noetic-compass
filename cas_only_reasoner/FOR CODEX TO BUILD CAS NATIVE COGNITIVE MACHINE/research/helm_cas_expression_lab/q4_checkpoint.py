"""Inference-only R1 checkpoint custody. Save/load neural paths are unexecuted.

Verification is deterministic. Loading is CUDA-only, weights-only, strict, and
requires the source/data identity expected OUTSIDE the checkpoint directory.
This format does not promise exact optimizer/schedule/RNG training resume.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re

SCHEMA = "helm-cas-expression-lab.q4-inference-checkpoint/0.1"
HERE = Path(__file__).resolve().parent
RUNTIME_FILES = ("learner_q4_representation.py", "learner_q4_decoder.py", "learner_q4_neural.py",
                 "learner_q4_memory.py", "q4_checkpoint.py", "q4_smoke_job.py", "q3_load.py",
                 "q3_behaviour_records.py", "reference_ops.py", "q4_runtime_metadata.py")


class CheckpointError(ValueError):
    pass


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def runtime_source_pins() -> dict[str, str]:
    return {name: digest((HERE / name).read_bytes().replace(b"\r\n", b"\n")) for name in RUNTIME_FILES}


def _strict_manifest(path):
    # Loader is the project's strict JSON implementation, not a target reader.
    from q3_load import strict_loads
    try:
        return strict_loads(path.read_text(encoding="utf-8"), path.name)
    except (OSError, UnicodeError, ValueError) as error:
        raise CheckpointError("CHECKPOINT_MANIFEST_INVALID") from error


def _verified_checkpoint_bytes(directory: Path, *, expected_identity: dict, expected_width: int,
                               expected_weights_sha256: str) -> tuple[dict, bytes]:
    """Verify bytes and externally expected identities BEFORE any torch import."""
    root = Path(directory)
    manifest = _strict_manifest(root / "manifest.json")
    required = {"schema", "purpose", "width", "identity", "weights_file", "weights_sha256", "weights_bytes"}
    if (type(manifest) is not dict or set(manifest) != required or manifest["schema"] != SCHEMA
            or manifest["purpose"] != "INFERENCE_ONLY_NO_TRAINING_RESUME"
            or type(manifest["width"]) is not int or manifest["width"] not in (64, 128)
            or manifest["width"] != expected_width or manifest["identity"] != expected_identity
            or manifest["weights_file"] != "model_state.pt"
            or type(manifest["weights_sha256"]) is not str
            or re.fullmatch(r"[0-9a-f]{64}", manifest["weights_sha256"]) is None
            or manifest["weights_sha256"] != expected_weights_sha256
            or type(manifest["weights_bytes"]) is not int or not 0 < manifest["weights_bytes"] <= 64 * 1024 * 1024):
        raise CheckpointError("CHECKPOINT_IDENTITY_MISMATCH")
    try:
        path = root / "model_state.pt"
        if path.is_symlink() or path.stat().st_size != manifest["weights_bytes"]:
            raise CheckpointError("CHECKPOINT_WEIGHTS_MISMATCH")
        with path.open("rb") as stream:
            body = stream.read(manifest["weights_bytes"] + 1)
    except OSError as error:
        raise CheckpointError("CHECKPOINT_WEIGHTS_MISSING") from error
    if len(body) != manifest["weights_bytes"] or digest(body) != manifest["weights_sha256"]:
        raise CheckpointError("CHECKPOINT_WEIGHTS_MISMATCH")
    return manifest, body


def verify_checkpoint(directory: Path, *, expected_identity: dict, expected_width: int,
                      expected_weights_sha256: str) -> dict:
    return _verified_checkpoint_bytes(directory, expected_identity=expected_identity,
                                      expected_width=expected_width,
                                      expected_weights_sha256=expected_weights_sha256)[0]


def save_checkpoint(model, directory: Path, *, identity: dict) -> dict:
    """Caller must already hold job ownership/authorization. No overwrite."""
    model._device()  # fails before serialization if the neural model is on CPU
    import torch
    root = Path(directory)
    root.mkdir(parents=False, exist_ok=False)
    path = root / "model_state.pt"
    torch.save(model.state_dict(), path)
    body = path.read_bytes()
    manifest = {"schema": SCHEMA, "purpose": "INFERENCE_ONLY_NO_TRAINING_RESUME",
                "width": model.config.width, "identity": identity,
                "weights_file": "model_state.pt", "weights_sha256": digest(body), "weights_bytes": len(body)}
    (root / "manifest.json").write_bytes(canonical(manifest) + b"\n")
    return verify_checkpoint(root, expected_identity=identity, expected_width=model.config.width,
                             expected_weights_sha256=manifest["weights_sha256"])


def load_checkpoint(directory: Path, *, expected_identity: dict, expected_weights_sha256: str, width: int, device: str):
    """Verified inference restore; no dropped tensors, fallback, or migration."""
    _, verified_bytes = _verified_checkpoint_bytes(directory, expected_identity=expected_identity, expected_width=width,
                                                   expected_weights_sha256=expected_weights_sha256)
    if expected_identity.get("source_pins") != runtime_source_pins():
        raise CheckpointError("CHECKPOINT_SOURCE_MISMATCH")
    from learner_q4_neural import NeuralConfig, build_model
    model = build_model(NeuralConfig(width), device=device)
    import torch
    state = torch.load(io.BytesIO(verified_bytes), map_location=device, weights_only=True)
    model.load_state_dict(state, strict=True)
    model.eval()
    return model
