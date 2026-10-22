"""Exact parameter counts by formula (no torch), and each block's job (Capacity Rules v0.1).

The GPU host asserts these numbers against torch's own count before any training (kit/run_ctt.py preflight and
ctt_train/train.py). The laptop never imports torch.
"""
from __future__ import annotations

from typing import Dict, List

CONFIGS: Dict[str, Dict[str, int]] = {
    "A4_9p6M": {"d_model": 256, "enc_layers": 4, "dec_layers": 4, "heads": 4, "ff": 1024},
    "A5_2p5M": {"d_model": 128, "enc_layers": 3, "dec_layers": 3, "heads": 4, "ff": 512},
}


def attn(d: int) -> int:            # torch.nn.MultiheadAttention: in_proj (3d x d + 3d) + out_proj (d x d + d)
    return 4 * d * d + 4 * d


def ffn(d: int, ff: int) -> int:     # linear1 (d x ff + ff) + linear2 (ff x d + d)
    return d * ff + ff + ff * d + d


def layernorm(d: int) -> int:
    return 2 * d


def blocks(vocab_size: int, cfg: Dict[str, int]) -> List[Dict[str, object]]:
    d, ff = cfg["d_model"], cfg["ff"]
    enc_layer = attn(d) + ffn(d, ff) + 2 * layernorm(d)
    dec_layer = 2 * attn(d) + ffn(d, ff) + 3 * layernorm(d)
    return [
        {"block": "shared embedding, tied input/output (vocab x d)", "count": vocab_size * d,
         "job": "one vector per English piece and per CAS token; CAS states are factored (^n, ^D, Fk, |R), so the "
                "40 states cost 14 vectors"},
        {"block": "output bias (vocab)", "count": vocab_size,
         "job": "base rate of each output token before the context is read"},
        {"block": "encoder: %d layers (self-attention + feed-forward + 2 layer norms)" % cfg["enc_layers"],
         "count": cfg["enc_layers"] * enc_layer,
         "job": "read the English, the slot tags and the dialogue records"},
        {"block": "encoder final layer norm", "count": layernorm(d), "job": "scale the encoder's output"},
        {"block": "decoder: %d layers (self-attention + cross-attention + feed-forward + 3 layer norms)"
                  % cfg["dec_layers"], "count": cfg["dec_layers"] * dec_layer,
         "job": "write the CAS record one token at a time, looking back at the sentence"},
        {"block": "decoder final layer norm", "count": layernorm(d), "job": "scale the decoder's output"},
        {"block": "copy (pointer) head: bilinear copy attention (d x d)", "count": d * d,
         "job": "point at a slot tag of the user's own sentence instead of inventing a number or a name"},
        {"block": "copy gate (2d + 1)", "count": 2 * d + 1,
         "job": "decide, per output step, between writing a CAS token and pointing at a slot"},
        {"block": "positions", "count": 0, "job": "fixed sinusoids; no parameters, so no input-length table "
                                                   "to run out of (gate H-LEN)"},
    ]


def total(vocab_size: int, cfg: Dict[str, int]) -> int:
    return sum(int(b["count"]) for b in blocks(vocab_size, cfg))
