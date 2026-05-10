"""Vocab expansion + warm-start for v1c → v1c+task-tokens transition.

When a v1 checkpoint (vocab=38683) is loaded into a model built with
the v1c tokenizer (vocab=38685), every embedding/lm_head tensor in
the state dict has the old shape ``(38683, d_model)`` while the
model expects ``(38685, d_model)``. ``load_state_dict`` would fail.

This module provides ``expand_state_dict_for_vocab_extension`` that:
  - copies rows 0..N_old-1 verbatim (preserves all v1 learning),
  - warm-starts new rows from semantic anchor IDs (per the Option C
    design doc: ``[TASK_EXPR]`` → ``[VALID]``, ``[TASK_EXPLAIN]`` →
    ``[INVALID]``),
  - returns a new state dict ready for ``load_state_dict(strict=True)``,
  - logs the source/destination IDs for every warm-start so the run
    manifest can record them.

This module is pure-python on top of torch tensors. No model or
tokenizer construction. Callable in tests with synthetic tensors so
the warm-start logic is verifiable without a real checkpoint.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import torch


@dataclass(frozen=True)
class WarmStartCopy:
    """One row-copy operation applied during vocab expansion."""
    source_id: int
    source_token: str | None  # human-readable label, optional
    target_id: int
    target_token: str | None  # human-readable label, optional


@dataclass
class VocabExpansionLog:
    """Audit-friendly summary of an expansion pass."""
    old_vocab: int
    new_vocab: int
    expanded_keys: list[str] = field(default_factory=list)
    skipped_keys: list[str] = field(default_factory=list)
    warm_starts: list[WarmStartCopy] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "old_vocab": self.old_vocab,
            "new_vocab": self.new_vocab,
            "expanded_keys": list(self.expanded_keys),
            "skipped_keys": list(self.skipped_keys),
            "warm_starts": [
                {
                    "source_id": w.source_id,
                    "source_token": w.source_token,
                    "target_id": w.target_id,
                    "target_token": w.target_token,
                }
                for w in self.warm_starts
            ],
        }


def expand_state_dict_for_vocab_extension(
    *,
    state_dict: dict[str, torch.Tensor],
    old_vocab: int,
    new_vocab: int,
    warm_starts: list[WarmStartCopy],
) -> tuple[dict[str, torch.Tensor], VocabExpansionLog]:
    """Resize every (old_vocab, *)-shaped weight tensor to
    (new_vocab, *) and copy warm-start anchor rows into the new
    positions.

    Returns ``(new_state_dict, log)``. Tensors that don't match the
    expected old_vocab in their first dim are passed through
    unchanged.

    Warm-start rows that fall in [old_vocab, new_vocab) are written
    by copying ``state_dict[key][source_id, :]`` into the new
    position. Rows outside that range raise ValueError so callers
    don't accidentally overwrite pre-trained rows.
    """
    if new_vocab < old_vocab:
        raise ValueError(
            f"new_vocab ({new_vocab}) must be >= old_vocab ({old_vocab})"
        )
    if new_vocab == old_vocab and warm_starts:
        raise ValueError(
            "warm_starts supplied but new_vocab == old_vocab; nothing to expand"
        )
    for ws in warm_starts:
        if not (old_vocab <= ws.target_id < new_vocab):
            raise ValueError(
                f"warm_start target_id {ws.target_id} not in expansion "
                f"range [{old_vocab}, {new_vocab})"
            )
        if not (0 <= ws.source_id < old_vocab):
            raise ValueError(
                f"warm_start source_id {ws.source_id} not in old vocab "
                f"range [0, {old_vocab})"
            )

    log = VocabExpansionLog(old_vocab=old_vocab, new_vocab=new_vocab)
    out: dict[str, torch.Tensor] = {}

    no_op = (new_vocab == old_vocab)
    for key, tensor in state_dict.items():
        if not isinstance(tensor, torch.Tensor):
            out[key] = tensor
            log.skipped_keys.append(key)
            continue
        if tensor.dim() == 0 or tensor.shape[0] != old_vocab or no_op:
            out[key] = tensor
            log.skipped_keys.append(key)
            continue
        # Allocate the expanded tensor.
        new_shape = (new_vocab,) + tuple(tensor.shape[1:])
        new_tensor = torch.zeros(
            new_shape, dtype=tensor.dtype, device=tensor.device,
        )
        # Copy old rows verbatim.
        new_tensor[:old_vocab] = tensor
        # Apply warm-start copies.
        for ws in warm_starts:
            new_tensor[ws.target_id] = tensor[ws.source_id]
        out[key] = new_tensor
        log.expanded_keys.append(key)

    # Record warm-starts on the log only once (independent of which
    # key they applied to).
    log.warm_starts.extend(warm_starts)
    return out, log


__all__ = [
    "VocabExpansionLog",
    "WarmStartCopy",
    "expand_state_dict_for_vocab_extension",
]
