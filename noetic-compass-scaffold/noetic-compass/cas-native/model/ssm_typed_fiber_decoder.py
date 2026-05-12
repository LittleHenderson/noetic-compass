"""SsmTypedFiberDecoder — SSM/S6-style decoder mirroring TypedFiberDecoder's API.

Candidate D per user 2026-05-12 (`docs/working/simplex_mvp_candidate_d_design_2026_05_12.md`).

This decoder replaces the transformer self-attention with a selective
state-space (S6-style) block while preserving the rest of the
TypedFiberDecoder architecture verbatim (cross-attention to simplex
stream, cross-attention to source stream, FFN, lm/slot/copy/phrase-bias
heads). The output dictionary keys and shapes are bit-for-bit identical
to TypedFiberDecoder so it plugs into the existing trainer + collator +
sample_decoder + evaluation pipelines without other changes.

Naming: This is **SSM/S6-style**, NOT canonical Mamba. The selective scan
is implemented as a Python loop (O(L) sequential, not the parallel scan
of the official Mamba CUDA kernel). The discretization is simplified
(exp(dt * A) for A, dt * B for B; not the bilinear/zoh discretization
canonical Mamba uses). State init is zeros (no contextual init). For CPU
smoke and 1000-step pod runs this is acceptable; if D validates, the
optimized mamba-ssm CUDA path is the optimization target.

Per user 2026-05-12 constraint: do not call this canonical Mamba unless
the implementation is faithful enough to justify the name.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
from torch import nn
import torch.nn.functional as F

from cas_native.model.typed_fiber_decoder import (
    SLOT_TYPES, SLOT_TYPE_TO_ID, NUM_SLOT_TYPES, COPY_ALLOWED_SLOT_IDS,
    _CrossAttention, _FFN, TypedFiberDecoderConfig,
)


@dataclass
class SsmTypedFiberDecoderConfig:
    """Hyperparameters for the SSM/S6-style decoder.

    Mirrors TypedFiberDecoderConfig and adds S6-specific fields
    (d_state, d_conv, expand). When converting from a transformer config
    use ``from_transformer_config``.
    """
    vocab_size_english: int = 50_000
    d_model: int = 384
    n_heads: int = 6           # used for cross-attention to source/simplex
    ffn_dim: int = 1536
    n_layers: int = 6
    dropout: float = 0.1
    max_decode_len: int = 256
    num_slot_types: int = NUM_SLOT_TYPES
    num_states: int = 40
    num_noetics: int = 10
    n_phrases_per_k: int = 8
    pad_token_id: int = 0
    tie_lm_head: bool = True
    # S6-specific
    d_state: int = 16          # SSM hidden-state dimension per channel
    d_conv: int = 4            # local conv kernel width
    expand: int = 2            # inner-dimension expansion factor

    @classmethod
    def from_transformer_config(
        cls,
        tcfg: TypedFiberDecoderConfig,
        *,
        d_state: int = 16,
        d_conv: int = 4,
        expand: int = 2,
    ) -> "SsmTypedFiberDecoderConfig":
        """Construct an SSM config matching an existing transformer config
        on every shared field. Used by the trainer when ``--decoder-arch ssm``
        is set so the rest of the pipeline (vocab, d_model, etc.) stays
        identical."""
        return cls(
            vocab_size_english=tcfg.vocab_size_english,
            d_model=tcfg.d_model,
            n_heads=tcfg.n_heads,
            ffn_dim=tcfg.ffn_dim,
            n_layers=tcfg.n_layers,
            dropout=tcfg.dropout,
            max_decode_len=tcfg.max_decode_len,
            num_slot_types=tcfg.num_slot_types,
            num_states=tcfg.num_states,
            num_noetics=tcfg.num_noetics,
            n_phrases_per_k=tcfg.n_phrases_per_k,
            pad_token_id=tcfg.pad_token_id,
            tie_lm_head=tcfg.tie_lm_head,
            d_state=d_state,
            d_conv=d_conv,
            expand=expand,
        )


class _SsmS6Block(nn.Module):
    """Selective state-space block, S6-style, pure PyTorch.

    Replaces transformer self-attention. Causal by construction (no
    explicit mask needed — the selective scan is sequential).

    NOT canonical Mamba:
      - Scan is a Python for-loop (sequential); canonical Mamba uses a
        parallel scan via custom CUDA kernel.
      - Discretization is simplified (exp(dt*A), dt*B) rather than the
        bilinear/ZOH discretization Mamba uses.
      - No SSM-specific initialization tricks (e.g. HiPPO matrix).

    What this block does provide:
      - Selectivity: dt, B, C are functions of input (the load-bearing
        property that distinguishes S6 from earlier S4).
      - Local context via depthwise causal Conv1d.
      - Gated residual via z stream (SiLU(z) * y).
    """

    def __init__(self, cfg: SsmTypedFiberDecoderConfig):
        super().__init__()
        self.d_model = cfg.d_model
        self.d_state = cfg.d_state
        self.d_inner = cfg.d_model * cfg.expand
        self.d_conv = cfg.d_conv

        # Input projection: d_model -> 2 * d_inner (x stream + z gate stream)
        self.in_proj = nn.Linear(cfg.d_model, 2 * self.d_inner, bias=False)

        # Depthwise causal conv1d on x stream
        self.conv1d = nn.Conv1d(
            in_channels=self.d_inner, out_channels=self.d_inner,
            kernel_size=self.d_conv, groups=self.d_inner,
            padding=self.d_conv - 1, bias=True,
        )

        # Selectivity: project input to (dt, B, C). dt is per-channel
        # (d_inner), B and C are state-shaped (d_state each).
        self.x_proj = nn.Linear(
            self.d_inner, self.d_inner + 2 * self.d_state, bias=False,
        )
        # Δt projection: small learnable bias so initial dt ~ 1/100
        self.dt_proj = nn.Linear(self.d_inner, self.d_inner, bias=True)
        with torch.no_grad():
            # Initialize dt_proj bias so initial Δt ≈ exp(-4) ≈ 0.018,
            # a small step that lets the scan accumulate gradually
            # before learning. Bias init scheme matches simplified
            # discretization assumptions.
            self.dt_proj.bias.fill_(-4.0)
            # Small weight init so dt starts dominated by the bias
            nn.init.uniform_(self.dt_proj.weight, -0.001, 0.001)

        # State matrix A: log-parametrized for stability, init A_k = k+1.
        # Stored as log so we can exponentiate to ensure positivity, then
        # negate for negative-real spectrum (decay).
        A = torch.arange(1, cfg.d_state + 1, dtype=torch.float32)
        A = A.unsqueeze(0).expand(self.d_inner, -1).contiguous()
        self.A_log = nn.Parameter(torch.log(A))                  # (d_inner, d_state)

        # D residual (skip-around-scan) — initialize to 1 so the block
        # has a useful identity-pass at init.
        self.D = nn.Parameter(torch.ones(self.d_inner))

        # Output projection back to d_model
        self.out_proj = nn.Linear(self.d_inner, cfg.d_model, bias=False)

        # Pre-norm
        self.norm = nn.LayerNorm(cfg.d_model)

        self.dropout = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Causal SSM step over the sequence.

        Args:
            x: (B, L, d_model) decoder hidden state up to current step.
        Returns:
            (B, L, d_model) updated hidden state (residual added).
        """
        B, L, _ = x.shape
        residual = x
        h = self.norm(x)

        # Input projection
        xz = self.in_proj(h)                                  # (B, L, 2*d_inner)
        x_in, z = xz.chunk(2, dim=-1)                         # each (B, L, d_inner)

        # Depthwise causal conv: (B, L, C) -> (B, C, L) -> conv -> trim -> (B, L, C)
        x_conv_in = x_in.transpose(1, 2)                       # (B, d_inner, L)
        x_conv = self.conv1d(x_conv_in)
        # Conv with left-pad of d_conv-1 produces (B, d_inner, L + d_conv - 1).
        # Trim to keep first L positions (causal).
        x_conv = x_conv[:, :, :L]                              # (B, d_inner, L)
        x_conv = x_conv.transpose(1, 2)                        # (B, L, d_inner)
        x_conv = F.silu(x_conv)

        # Project to dt, B_param, C_param
        x_dbl = self.x_proj(x_conv)                            # (B, L, d_inner + 2*d_state)
        dt_raw = x_dbl[..., : self.d_inner]                    # (B, L, d_inner)
        B_param = x_dbl[..., self.d_inner : self.d_inner + self.d_state]   # (B, L, d_state)
        C_param = x_dbl[..., self.d_inner + self.d_state :]                # (B, L, d_state)
        dt = F.softplus(self.dt_proj(dt_raw))                  # (B, L, d_inner), > 0

        # Continuous-time A (negative for stability) — (d_inner, d_state)
        A = -torch.exp(self.A_log)

        # Selective scan (sequential — Python loop over L).
        state = torch.zeros(B, self.d_inner, self.d_state,
                             device=x.device, dtype=x_conv.dtype)
        ys = []
        for t in range(L):
            dt_t = dt[:, t, :]                                 # (B, d_inner)
            x_t = x_conv[:, t, :]                              # (B, d_inner)
            B_t = B_param[:, t, :]                             # (B, d_state)
            C_t = C_param[:, t, :]                             # (B, d_state)

            # Discretize A per-step: A_disc = exp(dt * A)
            A_disc = torch.exp(dt_t.unsqueeze(-1) * A.unsqueeze(0))  # (B, d_inner, d_state)
            # Discretize B per-step: B_disc = dt * B (broadcast across d_inner)
            B_disc = dt_t.unsqueeze(-1) * B_t.unsqueeze(1)     # (B, d_inner, d_state)

            # State update: state = A_disc * state + B_disc * x_t
            state = A_disc * state + B_disc * x_t.unsqueeze(-1)
            # Output: y = sum_k(C_k * state_{ik})
            y_t = (state * C_t.unsqueeze(1)).sum(dim=-1)       # (B, d_inner)
            # D residual (skip around scan)
            y_t = y_t + self.D * x_t
            ys.append(y_t)

        y = torch.stack(ys, dim=1)                             # (B, L, d_inner)

        # Gate
        y = y * F.silu(z)

        # Output projection + residual
        out = self.out_proj(y)
        return residual + self.dropout(out)


class _SsmDecoderBlock(nn.Module):
    """SSM decoder block: SSM/S6 -> cross-attn(simplex) -> cross-attn(src) -> FFN.

    Same shape semantics as TypedFiberDecoder's _DecoderBlock — only the
    self-attention is replaced with the SSM block. The final block exposes
    copy scores from cross-attn(src) for the pointer-copy distribution.
    """

    def __init__(self, cfg: SsmTypedFiberDecoderConfig, has_copy: bool = False):
        super().__init__()
        # SSM block subsumes its own pre-norm + residual internally
        self.ssm = _SsmS6Block(cfg)
        # Cross-attentions reuse the transformer decoder's class for an
        # apples-to-apples comparison on the cross-attention side. We build
        # a transformer config that matches the SSM config's d_model/n_heads/etc.
        tcfg = TypedFiberDecoderConfig(
            vocab_size_english=cfg.vocab_size_english,
            d_model=cfg.d_model, n_heads=cfg.n_heads, ffn_dim=cfg.ffn_dim,
            n_layers=cfg.n_layers, dropout=cfg.dropout,
            max_decode_len=cfg.max_decode_len, num_slot_types=cfg.num_slot_types,
            num_states=cfg.num_states, num_noetics=cfg.num_noetics,
            n_phrases_per_k=cfg.n_phrases_per_k, pad_token_id=cfg.pad_token_id,
            tie_lm_head=cfg.tie_lm_head,
        )
        self.norm_cross_simplex = nn.LayerNorm(cfg.d_model)
        self.cross_simplex = _CrossAttention(tcfg, kv_dim=cfg.d_model)
        self.norm_cross_src = nn.LayerNorm(cfg.d_model)
        self.cross_src = _CrossAttention(tcfg, kv_dim=cfg.d_model)
        self.norm_ffn = nn.LayerNorm(cfg.d_model)
        self.ffn = _FFN(tcfg)
        self.dropout = nn.Dropout(cfg.dropout)
        self.has_copy = has_copy

    def forward(
        self,
        x: torch.Tensor,
        simplex_kv: torch.Tensor,
        src_kv: torch.Tensor,
        src_mask: Optional[torch.Tensor],
    ) -> tuple[torch.Tensor, Optional[torch.Tensor]]:
        # SSM self-mixing (causal by construction)
        x = self.ssm(x)
        # Cross-attention to simplex stream
        out_simplex, _ = self.cross_simplex(
            self.norm_cross_simplex(x), simplex_kv, kv_mask=src_mask,
        )
        x = x + self.dropout(out_simplex)
        # Cross-attention to source (with copy scores on final block)
        out_src, copy_scores = self.cross_src(
            self.norm_cross_src(x), src_kv, kv_mask=src_mask,
            return_scores=self.has_copy,
        )
        x = x + self.dropout(out_src)
        # FFN
        x = x + self.ffn(self.norm_ffn(x))
        return x, copy_scores


class SsmTypedFiberDecoder(nn.Module):
    """SSM/S6-style decoder mirroring TypedFiberDecoder's API.

    Forward signature and return dict shapes are identical to
    TypedFiberDecoder — see that class's docstring for the contract.
    The architectural difference is the use of ``_SsmS6Block`` for
    autoregressive token mixing in place of masked self-attention.

    Source cross-attention is preserved (Candidate D design 2026-05-12
    decision 1: cross-attention adapter admissible because the failure
    mode under test is source-grounded copy, not source access).
    """

    def __init__(self, cfg: Optional[SsmTypedFiberDecoderConfig] = None):
        super().__init__()
        self.cfg = cfg or SsmTypedFiberDecoderConfig()

        self.token_emb = nn.Embedding(
            self.cfg.vocab_size_english, self.cfg.d_model,
            padding_idx=self.cfg.pad_token_id,
        )
        nn.init.normal_(self.token_emb.weight, mean=0.0, std=0.02)
        with torch.no_grad():
            self.token_emb.weight[self.cfg.pad_token_id].zero_()
        self.input_dropout = nn.Dropout(self.cfg.dropout)

        self.simplex_proj = nn.Linear(self.cfg.num_states, self.cfg.d_model)
        self.src_token_proj = nn.Linear(self.cfg.d_model, self.cfg.d_model)

        blocks = []
        for i in range(self.cfg.n_layers):
            is_final = (i == self.cfg.n_layers - 1)
            blocks.append(_SsmDecoderBlock(self.cfg, has_copy=is_final))
        self.blocks = nn.ModuleList(blocks)
        self.final_norm = nn.LayerNorm(self.cfg.d_model)

        self.lm_head = nn.Linear(
            self.cfg.d_model, self.cfg.vocab_size_english, bias=True,
        )
        if self.cfg.tie_lm_head:
            self.lm_head.weight = self.token_emb.weight
        self.slot_type_head = nn.Linear(
            self.cfg.d_model, self.cfg.num_slot_types,
        )

        self.phrase_bias_table = nn.Parameter(
            torch.zeros(
                self.cfg.num_noetics, self.cfg.n_phrases_per_k, self.cfg.d_model,
            )
        )
        nn.init.normal_(self.phrase_bias_table, std=0.02)
        self.phrase_bias_proj = nn.Linear(
            self.cfg.n_phrases_per_k, self.cfg.vocab_size_english,
        )
        self.phrase_bias_alpha = nn.Parameter(torch.tensor(0.5))

    def forward(
        self,
        decoder_input_ids: torch.Tensor,
        source_hidden: torch.Tensor,
        simplex_trajectory: torch.Tensor,
        src_ids: torch.Tensor,
        src_token_type: torch.Tensor,
        src_padding_mask: Optional[torch.Tensor] = None,
        target_typed_positions: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        B, L_out = decoder_input_ids.shape
        _, L_src, _ = source_hidden.shape

        if src_padding_mask is None:
            src_padding_mask = torch.ones(
                B, L_src, dtype=torch.bool, device=src_ids.device,
            )

        x = self.token_emb(decoder_input_ids)
        x = self.input_dropout(x)

        simplex_kv = self.simplex_proj(simplex_trajectory.to(dtype=x.dtype))
        src_kv = self.src_token_proj(source_hidden)

        copy_scores: Optional[torch.Tensor] = None
        for block in self.blocks:
            x, block_scores = block(
                x, simplex_kv=simplex_kv, src_kv=src_kv,
                src_mask=src_padding_mask,
            )
            if block_scores is not None:
                copy_scores = block_scores

        decoder_hidden_state = self.final_norm(x)
        lm_logits = self.lm_head(decoder_hidden_state)
        slot_type_logits = self.slot_type_head(decoder_hidden_state)

        if copy_scores is None:
            copy_scores = torch.zeros(
                B, L_out, L_src, dtype=x.dtype, device=x.device,
            )
        if src_padding_mask is not None:
            mask = src_padding_mask[:, None, :].to(dtype=torch.bool)
            copy_scores = copy_scores.masked_fill(~mask, float("-inf"))
        p_copy = F.softmax(copy_scores, dim=-1)
        p_copy = torch.nan_to_num(p_copy, nan=0.0, posinf=0.0, neginf=0.0)

        # Phrase-bias term (mirrors TypedFiberDecoder verbatim)
        with torch.no_grad():
            mask_f = src_padding_mask.to(dtype=torch.float32).unsqueeze(-1)
            denom = mask_f.sum(dim=1).clamp_min(1.0)
            simplex_pooled = (simplex_trajectory * mask_f).sum(dim=1) / denom
            pooled_noetic = simplex_pooled.view(B, 4, 10).sum(dim=1)
            k_star = pooled_noetic.argmax(dim=-1)
        phrase_table_b = self.phrase_bias_table[k_star]
        phrase_scores = torch.einsum(
            "bld,bnd->bln", decoder_hidden_state, phrase_table_b,
        )
        phrase_bias = self.phrase_bias_proj(phrase_scores)

        slot_type_probs = F.softmax(slot_type_logits, dim=-1)
        noetic_phrase_gate = slot_type_probs[
            ..., SLOT_TYPE_TO_ID["NOETIC_PHRASE"]
        ].unsqueeze(-1)
        lm_logits = (
            lm_logits + self.phrase_bias_alpha * noetic_phrase_gate * phrase_bias
        )

        copy_source_indices = p_copy.argmax(dim=-1).to(dtype=torch.int16)
        if target_typed_positions is not None:
            is_copy_slot = torch.zeros_like(target_typed_positions, dtype=torch.bool)
            for sid in COPY_ALLOWED_SLOT_IDS:
                is_copy_slot = is_copy_slot | (target_typed_positions == sid)
            copy_source_indices = torch.where(
                is_copy_slot,
                copy_source_indices,
                torch.full_like(copy_source_indices, -1),
            )

        return {
            "lm_logits": lm_logits,
            "slot_type_logits": slot_type_logits,
            "p_copy": p_copy,
            "copy_source_indices": copy_source_indices,
            "decoder_hidden_state": decoder_hidden_state,
        }
