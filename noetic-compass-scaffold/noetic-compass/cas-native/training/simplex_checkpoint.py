"""Checkpoint save/load for the simplex MVP trainer.

Per user 2026-05-11. Minimal but complete: model state, optimizer state,
config, tokenizer/BPE paths or hashes, global step, RNG seeds, ablation
mode, loss weights. Default-off — only activates when
``--save-checkpoints-at`` is set on the trainer CLI.

This is offline-built diagnostic infrastructure: a checkpoint persisted
during a future run can be loaded into a separate diagnostic process
(teacher-forced eval, per-token greedy trace, decode-time ablation)
without re-training.

Checkpoint layout (single .pt file via torch.save):
{
    "schema_version": "simplex_mvp_ckpt.v1",
    "step": int,
    "config": asdict(SimplexTrainConfig),
    "model_state_dict": dict (tied weight stored ONCE),
    "optimizer_state_dict": dict,
    "rng_state": {
        "torch": torch.get_rng_state() bytes,
        "torch_cuda": torch.cuda.get_rng_state_all() bytes if cuda,
        "python_random": tuple-state from random.getstate(),
        "numpy": numpy.random.get_state() if numpy available,
    },
    "tokenizer_info": {
        "tokenizer_path": str,
        "tokenizer_sha256": str (optional),
        "english_bpe_path": str,
        "english_bpe_sha256": str (optional),
        "vocab_size": int,
    },
    "ablation_mode": str,
    "loss_weights_active": dict,
    "loss_history_tail": list of last K step dicts,  # K=20 by default
    "saved_at_utc": ISO timestamp,
    "torch_version": str,
    "cuda_version": str,
}
"""
from __future__ import annotations

import hashlib
import json
import os
import random as _random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import torch


SCHEMA_VERSION = "simplex_mvp_ckpt.v1"
_DEFAULT_HISTORY_TAIL = 20


def _file_sha256(path: str) -> Optional[str]:
    """Hex SHA-256 of a file path, or None if path doesn't exist."""
    if not path or not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _collect_rng_state() -> dict[str, Any]:
    """Snapshot torch + python random RNG states. NumPy optional."""
    state: dict[str, Any] = {
        "torch": torch.get_rng_state(),
        "python_random": _random.getstate(),
    }
    if torch.cuda.is_available():
        try:
            state["torch_cuda"] = torch.cuda.get_rng_state_all()
        except Exception:
            state["torch_cuda"] = None
    try:
        import numpy as _np
        state["numpy"] = _np.random.get_state()
    except Exception:
        state["numpy"] = None
    return state


def _restore_rng_state(state: dict[str, Any]) -> None:
    """Restore RNG state from a checkpoint dict's ``rng_state`` field."""
    if state.get("torch") is not None:
        torch.set_rng_state(state["torch"])
    if state.get("python_random") is not None:
        _random.setstate(state["python_random"])
    if state.get("torch_cuda") is not None and torch.cuda.is_available():
        try:
            torch.cuda.set_rng_state_all(state["torch_cuda"])
        except Exception:
            pass
    if state.get("numpy") is not None:
        try:
            import numpy as _np
            _np.random.set_state(state["numpy"])
        except Exception:
            pass


def save_checkpoint(
    output_path: str,
    *,
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    step: int,
    cfg: Any,
    tokenizer_info: dict[str, Any],
    loss_history_tail: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Save a checkpoint to ``output_path``. Returns the manifest dict.

    Raises if the destination directory doesn't exist (caller's responsibility
    to mkdir the run dir).
    """
    out = Path(output_path)
    if not out.parent.exists():
        raise FileNotFoundError(
            f"Parent dir does not exist: {out.parent}. "
            "Create the run dir before calling save_checkpoint."
        )

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "step": int(step),
        "config": asdict(cfg) if hasattr(cfg, "__dataclass_fields__") else dict(cfg),
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "rng_state": _collect_rng_state(),
        "tokenizer_info": dict(tokenizer_info),
        "ablation_mode": getattr(cfg, "ablation", "full"),
        "loss_weights_active": dict(getattr(cfg, "loss_weights", {})),
        "loss_history_tail": list(loss_history_tail or [])[-_DEFAULT_HISTORY_TAIL:],
        "saved_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "torch_version": torch.__version__,
        "cuda_version": getattr(torch.version, "cuda", None),
    }
    if extra:
        payload["extra"] = dict(extra)
    torch.save(payload, str(out))

    # Side-car JSON manifest for human inspection (small subset, no tensors)
    manifest = {
        "schema_version": payload["schema_version"],
        "step": payload["step"],
        "saved_at_utc": payload["saved_at_utc"],
        "torch_version": payload["torch_version"],
        "cuda_version": payload["cuda_version"],
        "tokenizer_info": payload["tokenizer_info"],
        "ablation_mode": payload["ablation_mode"],
        "loss_weights_active": payload["loss_weights_active"],
        "config": payload["config"],
        "loss_history_tail_count": len(payload["loss_history_tail"]),
        "checkpoint_size_bytes": out.stat().st_size,
    }
    manifest_path = out.with_suffix(out.suffix + ".manifest.json")
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return manifest


def load_checkpoint(
    checkpoint_path: str,
    *,
    model: torch.nn.Module,
    optimizer: Optional[torch.optim.Optimizer] = None,
    map_location: str = "cpu",
    strict: bool = True,
    restore_rng: bool = True,
) -> dict[str, Any]:
    """Load a checkpoint into the given model + optional optimizer.

    Args:
        checkpoint_path: path to a ``.pt`` produced by ``save_checkpoint``.
        model: target model (must match the saved architecture).
        optimizer: optional — if provided, optimizer state is restored too.
        map_location: passed to ``torch.load``. Default "cpu" so the load
            doesn't pin to a specific GPU; the caller moves the model after.
        strict: passed to ``model.load_state_dict``. False allows aux-head
            mismatches (matches v1e Phase C pattern).
        restore_rng: whether to restore the saved RNG state.

    Returns:
        The full payload dict (sans tensors that already got loaded).
    """
    p = Path(checkpoint_path)
    if not p.exists():
        raise FileNotFoundError(f"checkpoint not found: {p}")
    payload = torch.load(str(p), map_location=map_location, weights_only=False)

    schema = payload.get("schema_version")
    if schema != SCHEMA_VERSION:
        raise ValueError(
            f"checkpoint schema mismatch: expected {SCHEMA_VERSION}, got {schema!r}"
        )

    model.load_state_dict(payload["model_state_dict"], strict=strict)
    if optimizer is not None and payload.get("optimizer_state_dict") is not None:
        optimizer.load_state_dict(payload["optimizer_state_dict"])
    if restore_rng and payload.get("rng_state") is not None:
        _restore_rng_state(payload["rng_state"])
    return payload


def build_tokenizer_info(
    tokenizer_path: str,
    english_bpe_path: str,
    *,
    tokenizer: Any,
) -> dict[str, Any]:
    """Build the ``tokenizer_info`` dict for ``save_checkpoint``.

    Hashes both files (if they exist on disk) so the loader can verify
    integrity / detect a tokenizer swap.
    """
    return {
        "tokenizer_path": str(tokenizer_path or ""),
        "tokenizer_sha256": _file_sha256(tokenizer_path) if tokenizer_path else None,
        "english_bpe_path": str(english_bpe_path or ""),
        "english_bpe_sha256": _file_sha256(english_bpe_path) if english_bpe_path else None,
        "vocab_size": int(getattr(tokenizer, "vocab_size", 0)),
    }
