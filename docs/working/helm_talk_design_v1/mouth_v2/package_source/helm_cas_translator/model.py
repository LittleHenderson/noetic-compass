"""The CAS-token translator network (torch). Imported ONLY on the GPU host, never on the laptop.

Encoder-decoder transformer trained from scratch: one shared embedding table (tied input/output), fixed sinusoid
positions (no parameters), and a copy (pointer) head that moves probability onto the slot tags of the input so the
model points at the user's own amounts and words instead of inventing them. Every block's job:
PARAMETER_JOBS_CTT.md (param_count.blocks). The exact count is asserted against param_count.total() before training.

GPU_REQUIRED: require_cuda() raises unless CUDA is present. There is no CPU fallback for training or scoring.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F

from . import param_count
from .vocab import EOS, PAD


class GPURequired(RuntimeError):
    """Raised when CUDA is not available: the run fails closed (GPU_REQUIRED), never falls back to the CPU."""


def require_cuda() -> torch.device:
    if not torch.cuda.is_available():
        raise GPURequired("GPU_REQUIRED: CUDA is not available; neural work never runs on the CPU")
    return torch.device("cuda")


def sinusoid(length: int, d: int, device) -> torch.Tensor:
    pos = torch.arange(length, device=device, dtype=torch.float32).unsqueeze(1)
    div = torch.exp(torch.arange(0, d, 2, device=device, dtype=torch.float32) * (-math.log(10000.0) / d))
    pe = torch.zeros(length, d, device=device)
    pe[:, 0::2] = torch.sin(pos * div)
    pe[:, 1::2] = torch.cos(pos * div)
    return pe


class CTTModel(nn.Module):
    def __init__(self, vocab_size: int, d_model: int, enc_layers: int, dec_layers: int, heads: int, ff: int,
                 dropout: float = 0.1):
        super().__init__()
        self.vocab_size, self.d = vocab_size, d_model
        self.emb = nn.Embedding(vocab_size, d_model)
        self.out_bias = nn.Parameter(torch.zeros(vocab_size))
        enc = nn.TransformerEncoderLayer(d_model, heads, ff, dropout, batch_first=True, norm_first=True)
        self.encoder = nn.TransformerEncoder(enc, enc_layers, norm=nn.LayerNorm(d_model),
                                             enable_nested_tensor=False)
        dec = nn.TransformerDecoderLayer(d_model, heads, ff, dropout, batch_first=True, norm_first=True)
        self.decoder = nn.TransformerDecoder(dec, dec_layers, norm=nn.LayerNorm(d_model))
        self.copy_w = nn.Linear(d_model, d_model, bias=False)
        self.gate = nn.Linear(2 * d_model, 1)
        nn.init.normal_(self.emb.weight, mean=0.0, std=d_model ** -0.5)

    @classmethod
    def from_config(cls, vocab_size: int, cfg: Dict[str, int], dropout: float = 0.1) -> "CTTModel":
        return cls(vocab_size, cfg["d_model"], cfg["enc_layers"], cfg["dec_layers"], cfg["heads"], cfg["ff"],
                   dropout)

    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def encode(self, src: torch.Tensor):
        pad = src.eq(PAD)
        x = self.emb(src) * math.sqrt(self.d) + sinusoid(src.size(1), self.d, src.device)
        return self.encoder(x, src_key_padding_mask=pad), pad

    def decode_logp(self, src: torch.Tensor, mem: torch.Tensor, src_pad: torch.Tensor, tgt_in: torch.Tensor
                    ) -> torch.Tensor:
        """Log-probabilities (B, T, V) of the next token at every target position."""
        lt = tgt_in.size(1)
        y = self.emb(tgt_in) * math.sqrt(self.d) + sinusoid(lt, self.d, tgt_in.device)
        causal = torch.triu(torch.ones(lt, lt, device=tgt_in.device, dtype=torch.bool), diagonal=1)
        h = self.decoder(y, mem, tgt_mask=causal, tgt_key_padding_mask=tgt_in.eq(PAD),
                         memory_key_padding_mask=src_pad)
        logits = h @ self.emb.weight.t() + self.out_bias
        p_vocab = F.softmax(logits, dim=-1)
        scores = torch.bmm(self.copy_w(h), mem.transpose(1, 2)) / math.sqrt(self.d)
        scores = scores.masked_fill(src_pad.unsqueeze(1), float("-inf"))
        attn = F.softmax(scores, dim=-1)
        ctx = torch.bmm(attn, mem)
        g = torch.sigmoid(self.gate(torch.cat([h, ctx], dim=-1)))
        p_copy = torch.zeros_like(p_vocab).scatter_add_(2, src.unsqueeze(1).expand(-1, lt, -1), attn)
        p = (1.0 - g) * p_vocab + g * p_copy
        return torch.log(p.clamp_min(1e-12))

    def forward(self, src: torch.Tensor, tgt_in: torch.Tensor) -> torch.Tensor:
        mem, pad = self.encode(src)
        return self.decode_logp(src, mem, pad, tgt_in)


def pad_batch(seqs: Sequence[Sequence[int]], device) -> torch.Tensor:
    n = max(len(s) for s in seqs)
    out = torch.full((len(seqs), n), PAD, dtype=torch.long)
    for i, s in enumerate(seqs):
        out[i, :len(s)] = torch.tensor(list(s), dtype=torch.long)
    return out.to(device)


@torch.no_grad()
def greedy_locked(model: CTTModel, srcs: List[List[int]], automata: List[object], tok_of_id: List[str],
                  id_of_tok: Dict[str, int], device, max_len: int = 128) -> List[Dict[str, object]]:
    """Grammar-locked greedy decoding. automata[i] has allowed() -> set of token strings and step(tok).
    Returns per row: {"tokens": [...], "complete": bool, "steps": n}. A row that hits max_len without [EOS] is
    marked incomplete (the checker refuses it)."""
    model.eval()
    src = pad_batch(srcs, device)
    mem, src_pad = model.encode(src)
    b = len(srcs)
    tgt = torch.full((b, 1), 1, dtype=torch.long, device=device)          # [BOS]
    done = [False] * b
    out_tokens: List[List[str]] = [[] for _ in range(b)]
    mask_cache: Dict[frozenset, torch.Tensor] = {}
    for _step in range(max_len):
        logp = model.decode_logp(src, mem, src_pad, tgt)[:, -1, :]
        nxt = torch.full((b,), PAD, dtype=torch.long, device=device)
        for i in range(b):
            if done[i]:
                continue
            allowed = automata[i].allowed()
            if not allowed:
                done[i] = True
                continue
            m = mask_cache.get(allowed)
            if m is None:
                m = torch.full((model.vocab_size,), float("-inf"), device=device)
                m[torch.tensor([id_of_tok[t] for t in allowed], device=device)] = 0.0
                mask_cache[allowed] = m
            k = int(torch.argmax(logp[i] + m).item())
            tok = tok_of_id[k]
            automata[i].step(tok)
            nxt[i] = k
            if tok == "[EOS]":
                done[i] = True
            else:
                out_tokens[i].append(tok)
        tgt = torch.cat([tgt, nxt.unsqueeze(1)], dim=1)
        if all(done):
            break
    return [{"tokens": out_tokens[i], "complete": bool(getattr(automata[i], "ended", False)),
             "steps": len(out_tokens[i])} for i in range(b)]


def assert_parameter_count(model: CTTModel, vocab_size: int, cfg: Dict[str, int]) -> int:
    want = param_count.total(vocab_size, cfg)
    got = model.n_parameters()
    if got != want:
        raise AssertionError("parameter count %d != formula %d" % (got, want))
    return got
