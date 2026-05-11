"""SimplexEncoder — Δ°₃₉ source-CAS encoder for the simplex MVP rebuild.

Implements build-spec §2.1: 4-layer pre-norm Transformer trunk with RoPE +
bidirectional self-attention, then a 2-layer logit-space mirror-descent tail
that produces a per-source-token point on the open probability simplex Δ°₃₉.

Stage 1 status: skeleton. Class signature, forward-pass shape contract, and
output keys match the spec exactly. Internal trunk/tail computations are
implemented at the level required for shape + invariant tests; tuning,
RoPE-vs-sinusoidal A/B, and FFN dim/dropout sweeps land in Stage 7-bis.

References:
- ``docs/working/simplex_mvp_build_spec_2026_05_11.md`` §2.1
- ``docs/working/simplex_mvp_execution_plan_2026_05_11.md`` §Stage 1
- Mirror-descent rationale: logit-space updates keep ∂p/∂z bounded by 1 in
  operator norm even when p_k → ε, so Fisher-Rao's 1/p_k blow-up at the
  boundary is contained.
- Open-simplex projection reuses the existing
  ``embedding.CognitiveStateEmbedding._project_to_open_simplex`` pattern
  (softmax + ε-floor + renorm) so Specialist B's loss can reuse the existing
  simplex-validity asserts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
from torch import nn
import torch.nn.functional as F


NUM_COGNITIVE_STATES: int = 40
SIMPLEX_EPS: float = 1e-6  # B's clamp floor; matches build-spec §2.1


@dataclass
class SimplexEncoderConfig:
    """Hyperparameters per build-spec §2.1."""
    vocab_size: int = 38685            # v1c VALIDTOK tokenizer
    d_model: int = 384
    n_heads: int = 6
    ffn_dim: int = 1536
    n_layers: int = 4
    dropout: float = 0.1
    max_source_len: int = 256
    tail_hidden: int = 256             # MLP[(d_model + 40) -> 256 -> 40]
    tail_layers: int = 2               # 2-layer mirror-descent recurrence
    num_states: int = NUM_COGNITIVE_STATES
    eps: float = SIMPLEX_EPS
    pad_token_id: int = 0


class _RotaryPositionalEmbedding(nn.Module):
    """RoPE applied to query/key. Build-spec §2.1 specifies RoPE, NOT sinusoidal.

    Implementation note: precomputes cos/sin tables on first forward at the
    given sequence length; bigger sequences trigger a recompute.
    """

    def __init__(self, head_dim: int, max_seq_len: int = 256, base: float = 10_000.0):
        super().__init__()
        if head_dim % 2 != 0:
            raise ValueError(f"RoPE requires even head_dim; got {head_dim}")
        self.head_dim = head_dim
        self.base = base
        self.max_seq_len = max_seq_len
        cos, sin = self._build_tables(max_seq_len)
        self.register_buffer("cos_cached", cos, persistent=False)
        self.register_buffer("sin_cached", sin, persistent=False)

    def _build_tables(self, seq_len: int) -> tuple[torch.Tensor, torch.Tensor]:
        inv_freq = 1.0 / (self.base ** (torch.arange(0, self.head_dim, 2).float() / self.head_dim))
        t = torch.arange(seq_len).float()
        freqs = torch.einsum("i,j->ij", t, inv_freq)  # (seq_len, head_dim/2)
        emb = torch.cat([freqs, freqs], dim=-1)        # (seq_len, head_dim)
        return emb.cos(), emb.sin()

    def _maybe_extend(self, seq_len: int, device: torch.device, dtype: torch.dtype) -> None:
        if seq_len <= self.max_seq_len:
            return
        cos, sin = self._build_tables(seq_len)
        self.cos_cached = cos.to(device=device, dtype=dtype)
        self.sin_cached = sin.to(device=device, dtype=dtype)
        self.max_seq_len = seq_len

    @staticmethod
    def _rotate_half(x: torch.Tensor) -> torch.Tensor:
        x1, x2 = x.chunk(2, dim=-1)
        return torch.cat([-x2, x1], dim=-1)

    def forward(self, q: torch.Tensor, k: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # q, k: (B, n_heads, L, head_dim)
        seq_len = q.shape[-2]
        self._maybe_extend(seq_len, q.device, q.dtype)
        cos = self.cos_cached[:seq_len].to(dtype=q.dtype, device=q.device)
        sin = self.sin_cached[:seq_len].to(dtype=q.dtype, device=q.device)
        # Broadcast over batch and head dims: (1, 1, L, head_dim)
        cos = cos.unsqueeze(0).unsqueeze(0)
        sin = sin.unsqueeze(0).unsqueeze(0)
        q_rot = (q * cos) + (self._rotate_half(q) * sin)
        k_rot = (k * cos) + (self._rotate_half(k) * sin)
        return q_rot, k_rot


class _BidirectionalSelfAttention(nn.Module):
    """Multi-head bidirectional self-attention with RoPE on Q/K."""

    def __init__(self, cfg: SimplexEncoderConfig):
        super().__init__()
        if cfg.d_model % cfg.n_heads != 0:
            raise ValueError(
                f"d_model {cfg.d_model} must be divisible by n_heads {cfg.n_heads}"
            )
        self.head_dim = cfg.d_model // cfg.n_heads
        self.n_heads = cfg.n_heads
        self.scale = self.head_dim ** -0.5
        self.qkv = nn.Linear(cfg.d_model, 3 * cfg.d_model, bias=False)
        self.out_proj = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
        self.dropout = nn.Dropout(cfg.dropout)
        self.rope = _RotaryPositionalEmbedding(self.head_dim, max_seq_len=cfg.max_source_len)

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        B, L, _ = x.shape
        qkv = self.qkv(x).view(B, L, 3, self.n_heads, self.head_dim)
        qkv = qkv.permute(2, 0, 3, 1, 4)  # (3, B, n_heads, L, head_dim)
        q, k, v = qkv[0], qkv[1], qkv[2]
        q, k = self.rope(q, k)

        attn_logits = torch.matmul(q, k.transpose(-2, -1)) * self.scale  # (B, H, L, L)
        if attention_mask is not None:
            # attention_mask: (B, L) — True=keep, False=pad. Mask keys.
            key_mask = attention_mask[:, None, None, :].to(dtype=torch.bool)
            attn_logits = attn_logits.masked_fill(~key_mask, float("-inf"))
        attn = F.softmax(attn_logits, dim=-1)
        attn = self.dropout(attn)
        out = torch.matmul(attn, v)                       # (B, H, L, head_dim)
        out = out.transpose(1, 2).contiguous().view(B, L, -1)
        return self.out_proj(out)


class _FFN(nn.Module):
    def __init__(self, cfg: SimplexEncoderConfig):
        super().__init__()
        self.fc1 = nn.Linear(cfg.d_model, cfg.ffn_dim)
        self.fc2 = nn.Linear(cfg.ffn_dim, cfg.d_model)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.fc2(self.act(self.fc1(x))))


class _PreNormTransformerBlock(nn.Module):
    """Pre-norm (LayerNorm at sublayer input) Transformer block."""

    def __init__(self, cfg: SimplexEncoderConfig):
        super().__init__()
        self.attn_norm = nn.LayerNorm(cfg.d_model)
        self.attn = _BidirectionalSelfAttention(cfg)
        self.ffn_norm = nn.LayerNorm(cfg.d_model)
        self.ffn = _FFN(cfg)
        self.dropout = nn.Dropout(cfg.dropout)

    def forward(
        self,
        x: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        x = x + self.dropout(self.attn(self.attn_norm(x), attention_mask=attention_mask))
        x = x + self.ffn(self.ffn_norm(x))
        return x


class _MirrorDescentTail(nn.Module):
    """Logit-space mirror-descent recurrence producing simplex_trajectory.

    z_0 = 0 in R^40 (uniform pre-softmax).
    For each source position t:
        z_{t+1} = z_t + g_theta(h_t, z_t)
    g_theta = MLP[(d_model + 40) -> 256 -> 40] with GELU + LN.

    Layered ``tail_layers`` times. The recurrence is sequential over source
    positions; layers compound the same recurrence so the model can apply
    several mirror-descent corrections per position before projecting.
    """

    def __init__(self, cfg: SimplexEncoderConfig):
        super().__init__()
        self.num_states = cfg.num_states
        self.tail_layers = cfg.tail_layers
        self.eps = cfg.eps

        layers = []
        for _ in range(cfg.tail_layers):
            layers.append(
                nn.Sequential(
                    nn.LayerNorm(cfg.d_model + cfg.num_states),
                    nn.Linear(cfg.d_model + cfg.num_states, cfg.tail_hidden),
                    nn.GELU(),
                    nn.Linear(cfg.tail_hidden, cfg.num_states),
                )
            )
        self.layers = nn.ModuleList(layers)

    def _project_to_open_simplex(self, logits: torch.Tensor) -> torch.Tensor:
        """Softmax + ε-floor + renorm to land in Δ°₃₉."""
        probs = F.softmax(logits, dim=-1)
        probs = probs + self.eps
        probs = probs / probs.sum(dim=-1, keepdim=True)
        return probs

    def forward(self, source_hidden: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Apply mirror-descent recurrence pooled by-position.

        Returns:
            simplex_trajectory: (B, L_src, 40) strict positive, row-stochastic
            floor_violations:   (B, L_src) int count of clamped/eps-hit steps
        """
        B, L, _ = source_hidden.shape
        # Initialize z at uniform (zero logits => uniform after softmax)
        z = torch.zeros(B, L, self.num_states, dtype=source_hidden.dtype, device=source_hidden.device)
        for layer in self.layers:
            z_in = torch.cat([source_hidden, z], dim=-1)
            g = layer(z_in)
            z = z + g
        p = self._project_to_open_simplex(z)
        # Floor-violations telemetry: count positions where any p_k <= 2*eps
        floor_violations = (p <= 2 * self.eps).any(dim=-1).to(dtype=torch.int32)
        return p, floor_violations


class SimplexEncoder(nn.Module):
    """Δ°₃₉ source-CAS encoder per build-spec §2.1.

    Inputs:
        input_ids:        (B, L_src) int64 source CAS token IDs
        attention_mask:   (B, L_src) bool, True=keep, False=pad

    Outputs (dict):
        source_hidden:           (B, L_src, d_model) per-token trunk hidden
        simplex_trajectory:      (B, L_src, 40) strict positive, row-stochastic
        simplex_final:           (B, 40) masked-mean pool over trajectory
        source_attention_mask:   (B, L_src) bool echo
        floor_violations:        (B, L_src) int telemetry for B's monitor

    Param target: ~24.5M trainable (14.9M token emb + ~9.4M trunk + ~0.1M tail).
    """

    def __init__(self, cfg: Optional[SimplexEncoderConfig] = None):
        super().__init__()
        self.cfg = cfg or SimplexEncoderConfig()
        self.token_emb = nn.Embedding(self.cfg.vocab_size, self.cfg.d_model, padding_idx=self.cfg.pad_token_id)
        self.input_dropout = nn.Dropout(self.cfg.dropout)
        self.blocks = nn.ModuleList(
            [_PreNormTransformerBlock(self.cfg) for _ in range(self.cfg.n_layers)]
        )
        self.final_norm = nn.LayerNorm(self.cfg.d_model)
        self.tail = _MirrorDescentTail(self.cfg)

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        if attention_mask is None:
            attention_mask = (input_ids != self.cfg.pad_token_id)
        else:
            attention_mask = attention_mask.to(dtype=torch.bool)

        x = self.token_emb(input_ids)
        x = self.input_dropout(x)
        for block in self.blocks:
            x = block(x, attention_mask=attention_mask)
        source_hidden = self.final_norm(x)

        # Cast to fp32 for the tail; the simplex output must be fp32
        # regardless of bf16/fp16 trunk dtype (build-spec §3 dtype contract).
        simplex_trajectory, floor_violations = self.tail(source_hidden.to(dtype=torch.float32))

        # Masked-mean pool over valid source positions
        mask_f = attention_mask.to(dtype=torch.float32).unsqueeze(-1)  # (B, L, 1)
        denom = mask_f.sum(dim=1).clamp_min(1.0)
        simplex_final = (simplex_trajectory * mask_f).sum(dim=1) / denom
        # Re-project to keep simplex_final strictly on Δ°₃₉
        simplex_final = simplex_final + self.cfg.eps
        simplex_final = simplex_final / simplex_final.sum(dim=-1, keepdim=True)

        return {
            "source_hidden": source_hidden,
            "simplex_trajectory": simplex_trajectory,
            "simplex_final": simplex_final,
            "source_attention_mask": attention_mask,
            "floor_violations": floor_violations,
        }
