"""Backbone hidden-state adapter for CAS Transformer structured prediction.

Step 10 replaces the temporary hashed prompt features with pooled hidden states
from ``CASNativeModel``. This module is intentionally narrow: it tokenizes the
user prompt, runs the CAS-Native backbone, and feeds the pooled hidden state into
``StructuredPredictionHead``. The compiler/ingest layer still owns the labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import torch
import torch.nn as nn

from cas_native.model import CASNativeModel, StructuredPredictionHead
from cas_native.training.tokenizer import HybridCASTokenizer


@dataclass(frozen=True)
class BackboneBatch:
    """Tokenized prompt batch for CAS-Native backbone encoding."""

    input_ids: torch.Tensor
    attention_mask: torch.Tensor


def records_to_backbone_batch(
    records: Iterable[dict[str, Any]],
    tokenizer: HybridCASTokenizer,
    *,
    max_length: int = 256,
    device: torch.device | str | None = None,
) -> BackboneBatch:
    """Tokenize record prompts and build ``input_ids`` + ``attention_mask``."""

    encoded = [
        tokenizer.encode(str(record.get("user_prompt") or ""), max_length=max_length)
        for record in records
    ]
    if not encoded:
        raise ValueError("records must be non-empty")
    seq_len = max(len(row) for row in encoded)
    pad_id = tokenizer.pad_id()
    dev = torch.device(device) if device is not None else None
    input_ids = torch.full(
        (len(encoded), seq_len),
        pad_id,
        dtype=torch.long,
        device=dev,
    )
    attention_mask = torch.zeros(
        (len(encoded), seq_len),
        dtype=torch.long,
        device=dev,
    )
    for i, row in enumerate(encoded):
        values = torch.tensor(row, dtype=torch.long, device=dev)
        input_ids[i, : len(row)] = values
        attention_mask[i, : len(row)] = 1
    return BackboneBatch(input_ids=input_ids, attention_mask=attention_mask)


def pooled_backbone_hidden_states(
    backbone: CASNativeModel,
    batch: BackboneBatch,
    *,
    register_activations: torch.Tensor | None = None,
) -> torch.Tensor:
    """Return pooled CAS-Native hidden states for a tokenized prompt batch."""

    output = backbone(
        batch.input_ids,
        attention_mask=batch.attention_mask,
        register_activations=register_activations,
    )
    pooled = output.get("pooled_hidden_state")
    if pooled is None:
        raise KeyError("CASNativeModel output is missing 'pooled_hidden_state'")
    return pooled


class CASBackboneStructuredPredictor(nn.Module):
    """Compose CAS-Native backbone encoding with ``StructuredPredictionHead``."""

    def __init__(
        self,
        backbone: CASNativeModel,
        head: StructuredPredictionHead | None = None,
        *,
        freeze_backbone: bool = False,
    ) -> None:
        super().__init__()
        self.backbone = backbone
        self.head = head or StructuredPredictionHead(d_model=backbone.config.d_model)
        self.freeze_backbone = freeze_backbone
        if freeze_backbone:
            for param in self.backbone.parameters():
                param.requires_grad_(False)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        register_activations: torch.Tensor | None = None,
    ) -> dict[str, torch.Tensor]:
        if self.freeze_backbone:
            with torch.no_grad():
                backbone_output = self.backbone(
                    input_ids,
                    attention_mask=attention_mask,
                    register_activations=register_activations,
                )
                pooled = backbone_output["pooled_hidden_state"]
        else:
            backbone_output = self.backbone(
                input_ids,
                attention_mask=attention_mask,
                register_activations=register_activations,
            )
            pooled = backbone_output["pooled_hidden_state"]

        head_output = self.head(pooled)
        return {
            **head_output,
            "pooled_hidden_state": pooled,
        }
