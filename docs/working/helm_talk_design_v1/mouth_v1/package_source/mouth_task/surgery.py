"""mouth_task/surgery.py -- one new row for [M] in the CUBE TRAIN weights (A-TALK-4 W2). GPU host only (torch).

The shared embedding (vocab x d, tied input/output) and the output bias (vocab) each gain one row at the END, for the
new token [M]; its starting values are the mean of the three direction rows [A], [N], [B] (ids 5, 6, 7), so the new
direction starts where the old directions sit. Every other parameter is copied unchanged. The parameter count is the
frozen formula at the new vocabulary size: +d (the row) +1 (the bias) per copy.
"""
from __future__ import annotations

from typing import Dict

DIRECTION_ROWS = (5, 6, 7)


def add_m_row(state: Dict[str, "object"], old_vocab_size: int) -> Dict[str, "object"]:
    import torch
    emb, bias = state["emb.weight"], state["out_bias"]
    if emb.shape[0] != old_vocab_size or bias.shape[0] != old_vocab_size:
        raise ValueError("weights were not saved at the base vocabulary size")
    rows = list(DIRECTION_ROWS)
    new = dict(state)
    new["emb.weight"] = torch.cat([emb, emb[rows].mean(dim=0, keepdim=True)], dim=0)
    new["out_bias"] = torch.cat([bias, bias[rows].mean().reshape(1)], dim=0)
    return new
