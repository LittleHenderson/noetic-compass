"""Lightweight prompt-candidate semantic reranker for CAS expressions.

The grammar-constrained path guarantees that every candidate is compiler-valid.
This module learns only the semantic preference layer: given a natural-language
prompt and a compiler-valid candidate expression, estimate whether that
candidate is the intended target.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import torch
from torch import nn


@dataclass(frozen=True)
class SemanticRerankerConfig:
    """Small encoder config for the contrastive prompt-candidate scorer."""

    vocab_size: int
    d_model: int = 192
    hidden_dim: int = 384
    dropout: float = 0.10


class SemanticReranker(nn.Module):
    """Mean-pooled dual encoder plus cross features.

    This is deliberately modest: it trains quickly from the existing 10K SDG
    corpus and is cheap to run over thousands of compiler-valid candidates.
    """

    def __init__(self, config: SemanticRerankerConfig):
        super().__init__()
        self.config = config
        self.embedding = nn.Embedding(config.vocab_size, config.d_model, padding_idx=0)
        self.scorer = nn.Sequential(
            nn.Linear(config.d_model * 4, config.hidden_dim),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_dim, config.hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_dim // 2, 1),
        )

    def _encode(self, ids: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        embeddings = self.embedding(ids)
        mask_f = mask.unsqueeze(-1).to(dtype=embeddings.dtype)
        summed = (embeddings * mask_f).sum(dim=1)
        counts = mask_f.sum(dim=1).clamp(min=1.0)
        return summed / counts

    def forward(
        self,
        prompt_ids: torch.Tensor,
        prompt_mask: torch.Tensor,
        candidate_ids: torch.Tensor,
        candidate_mask: torch.Tensor,
    ) -> torch.Tensor:
        prompt_vec = self._encode(prompt_ids, prompt_mask)
        candidate_vec = self._encode(candidate_ids, candidate_mask)
        features = torch.cat(
            (
                prompt_vec,
                candidate_vec,
                torch.abs(prompt_vec - candidate_vec),
                prompt_vec * candidate_vec,
            ),
            dim=-1,
        )
        return self.scorer(features).squeeze(-1)


def _trim_special(ids: list[int], *, bos_id: int = 2, eos_id: int = 3) -> list[int]:
    out = list(ids)
    if out and out[0] == bos_id:
        out = out[1:]
    if out and out[-1] == eos_id:
        out = out[:-1]
    return out


def encode_text_batch(
    tokenizer: Any,
    texts: Iterable[str],
    *,
    device: torch.device,
    max_length: int,
    add_special: bool = False,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Encode a batch of texts into padded ids and non-pad masks."""

    encoded: list[list[int]] = []
    pad_id = int(tokenizer.pad_id())
    for text in texts:
        ids = tokenizer.encode(str(text), max_length=max_length, add_special=add_special)
        if not add_special:
            ids = _trim_special(ids)
        ids = ids[:max_length]
        if not ids:
            ids = [int(getattr(tokenizer, "UNK_ID", 1))]
        encoded.append(ids)

    width = max((len(ids) for ids in encoded), default=1)
    ids_tensor = torch.full((len(encoded), width), pad_id, dtype=torch.long, device=device)
    mask_tensor = torch.zeros((len(encoded), width), dtype=torch.bool, device=device)
    for row, ids in enumerate(encoded):
        ids_tensor[row, : len(ids)] = torch.tensor(ids, dtype=torch.long, device=device)
        mask_tensor[row, : len(ids)] = True
    return ids_tensor, mask_tensor


def score_candidates(
    model: SemanticReranker,
    tokenizer: Any,
    prompt: str,
    candidates: Iterable[str],
    *,
    device: torch.device,
    batch_size: int = 256,
    max_prompt_len: int = 192,
    max_candidate_len: int = 192,
) -> list[dict[str, Any]]:
    """Return semantic scores for candidate expressions sorted descending."""

    candidate_list = [str(candidate) for candidate in candidates]
    scored: list[dict[str, Any]] = []
    model.eval()
    with torch.no_grad():
        prompt_ids, prompt_mask = encode_text_batch(
            tokenizer,
            [prompt],
            device=device,
            max_length=max_prompt_len,
            add_special=False,
        )
        for start in range(0, len(candidate_list), batch_size):
            batch = candidate_list[start : start + batch_size]
            candidate_ids, candidate_mask = encode_text_batch(
                tokenizer,
                batch,
                device=device,
                max_length=max_candidate_len,
                add_special=False,
            )
            expanded_prompt_ids = prompt_ids.expand(len(batch), -1)
            expanded_prompt_mask = prompt_mask.expand(len(batch), -1)
            scores = model(
                expanded_prompt_ids,
                expanded_prompt_mask,
                candidate_ids,
                candidate_mask,
            )
            for candidate, score in zip(batch, scores.detach().cpu().tolist()):
                scored.append({"candidate": candidate, "semantic_score": float(score)})
    scored.sort(key=lambda item: item["semantic_score"], reverse=True)
    return scored


def save_semantic_reranker(
    path: str | Path,
    model: SemanticReranker,
    *,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Persist the reranker weights and metadata."""

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "config": asdict(model.config),
        "state_dict": model.state_dict(),
        "metadata": metadata or {},
    }
    # File handles avoid PyTorchFileWriter path quirks on Windows/OneDrive.
    with open(out, "wb") as f:
        torch.save(payload, f)
    return out


def load_semantic_reranker(
    path: str | Path,
    *,
    device: torch.device,
) -> tuple[SemanticReranker, dict[str, Any]]:
    """Load a persisted semantic reranker."""

    with open(Path(path), "rb") as f:
        payload = torch.load(f, map_location=device)
    config = SemanticRerankerConfig(**payload["config"])
    model = SemanticReranker(config).to(device)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model, dict(payload.get("metadata") or {})
