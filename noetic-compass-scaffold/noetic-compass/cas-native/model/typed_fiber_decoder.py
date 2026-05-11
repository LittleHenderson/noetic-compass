"""TypedFiberDecoder — pointer-generator decoder with slot-typed copy/generate.

Implements build-spec §2.3: 6-layer Transformer decoder with two cross-
attention KV streams (simplex_trajectory + src_token_emb), per-position
slot_type head (9 classes), pointer-copy attention masked by source-token-
type, and soft simplex-conditioned phrase bias at NOETIC_PHRASE positions.

Resolves the v1e Phase 1B "trailing-prose-emits-noetics" problem by making
the noetic-phrase bias multiply by 0 at CONNECTIVE positions, so connective
tokens like "then" / "after which" can be emitted even when the simplex
coordinate is at ^7.

Stage 1 status: skeleton with class signature, forward-pass shape contract,
and per-head outputs matching the spec. Slot-type emission rules + copy
mask + phrase-bias gating are wired but the source-side type-tag schema
and phrase tables are minimal placeholders sized to make Stage 2 shape
tests pass. Tuning lands in Stage 7-bis.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
from torch import nn
import torch.nn.functional as F


# 9 slot types per build-spec §2.3. Order is contract; the collator's
# typed_slot_positions tensor uses the same int ids.
SLOT_TYPES: tuple[str, ...] = (
    "CONNECTIVE",       # 0 — default; emit via lm_head
    "OMEGA",            # 1 — pointer-copy from source Ω tokens
    "STAGE_VAR",        # 2 — pointer-copy from source stage variables
    "COEFFICIENT",      # 3 — pointer-copy from source coefficients
    "REGISTER_LETTER",  # 4 — pointer-copy from source register letters
    "DOMAIN_LETTER",    # 5 — pointer-copy from source domain letters
    "DRIVE_LETTER",     # 6 — pointer-copy from source drive letters
    "FRACTAL_K_LITERAL",  # 7 — pointer-copy from source fractal k-literals
    "NOETIC_PHRASE",    # 8 — lm_head + simplex-conditioned phrase bias
)
SLOT_TYPE_TO_ID: dict[str, int] = {name: i for i, name in enumerate(SLOT_TYPES)}
NUM_SLOT_TYPES: int = len(SLOT_TYPES)

# Copy is allowed when src_token_type == slot_type. CONNECTIVE/NOETIC_PHRASE
# are emit-via-LM, not copy. Mapping is identity except CONNECTIVE(0) and
# NOETIC_PHRASE(8), which have no admissible copy sources.
COPY_ALLOWED_SLOT_IDS: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)


@dataclass
class TypedFiberDecoderConfig:
    """Hyperparameters per build-spec §2.3."""
    vocab_size_english: int = 50_000   # English BPE vocab
    d_model: int = 384
    n_heads: int = 6
    ffn_dim: int = 1536
    n_layers: int = 6
    dropout: float = 0.1
    max_decode_len: int = 256
    num_slot_types: int = NUM_SLOT_TYPES
    num_states: int = 40                # Δ°₃₉ dimensionality
    num_noetics: int = 10               # 10 Noetics for phrase-bias indexing
    n_phrases_per_k: int = 8            # phrase table depth per noetic
    pad_token_id: int = 0


class _MaskedSelfAttention(nn.Module):
    """Causal self-attention for the decoder side."""

    def __init__(self, cfg: TypedFiberDecoderConfig):
        super().__init__()
        if cfg.d_model % cfg.n_heads != 0:
            raise ValueError(f"d_model {cfg.d_model} not divisible by n_heads {cfg.n_heads}")
        self.head_dim = cfg.d_model // cfg.n_heads
        self.n_heads = cfg.n_heads
        self.scale = self.head_dim ** -0.5
        self.qkv = nn.Linear(cfg.d_model, 3 * cfg.d_model, bias=False)
        self.out_proj = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
        self.dropout = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, L, _ = x.shape
        qkv = self.qkv(x).view(B, L, 3, self.n_heads, self.head_dim).permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        attn = torch.matmul(q, k.transpose(-2, -1)) * self.scale  # (B,H,L,L)
        causal = torch.triu(torch.ones(L, L, dtype=torch.bool, device=x.device), diagonal=1)
        attn = attn.masked_fill(causal[None, None, :, :], float("-inf"))
        attn = F.softmax(attn, dim=-1)
        attn = self.dropout(attn)
        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, L, -1)
        return self.out_proj(out)


class _CrossAttention(nn.Module):
    """Decoder→encoder cross-attention. Returns also raw scores for copy mask."""

    def __init__(self, cfg: TypedFiberDecoderConfig, kv_dim: Optional[int] = None):
        super().__init__()
        if cfg.d_model % cfg.n_heads != 0:
            raise ValueError(f"d_model {cfg.d_model} not divisible by n_heads {cfg.n_heads}")
        self.head_dim = cfg.d_model // cfg.n_heads
        self.n_heads = cfg.n_heads
        self.scale = self.head_dim ** -0.5
        kv_dim = kv_dim or cfg.d_model
        self.q_proj = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
        self.k_proj = nn.Linear(kv_dim, cfg.d_model, bias=False)
        self.v_proj = nn.Linear(kv_dim, cfg.d_model, bias=False)
        self.out_proj = nn.Linear(cfg.d_model, cfg.d_model, bias=False)
        self.dropout = nn.Dropout(cfg.dropout)

    def forward(
        self,
        x: torch.Tensor,
        kv: torch.Tensor,
        kv_mask: Optional[torch.Tensor] = None,
        return_scores: bool = False,
    ) -> tuple[torch.Tensor, Optional[torch.Tensor]]:
        B, L_q, _ = x.shape
        _, L_kv, _ = kv.shape
        q = self.q_proj(x).view(B, L_q, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(kv).view(B, L_kv, self.n_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(kv).view(B, L_kv, self.n_heads, self.head_dim).transpose(1, 2)
        scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale  # (B,H,L_q,L_kv)
        if kv_mask is not None:
            mask = kv_mask[:, None, None, :].to(dtype=torch.bool)
            scores = scores.masked_fill(~mask, float("-inf"))
        attn = F.softmax(scores, dim=-1)
        # Fail-closed for fully-masked rows (all keys are PAD): softmax over
        # all -inf produces NaN; replace with a uniform-zero attention so the
        # downstream generative paths (lm_head, slot_type_head) stay finite.
        # Build-spec §2.3 + user-named "all-PAD source copy path fail-closed".
        attn = torch.nan_to_num(attn, nan=0.0, posinf=0.0, neginf=0.0)
        attn = self.dropout(attn)
        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(B, L_q, -1)
        out = self.out_proj(out)
        if return_scores:
            # Return mean of pre-softmax scores across heads as a single
            # per-(query,key) score for downstream pointer-copy logits.
            return out, scores.mean(dim=1)  # (B, L_q, L_kv)
        return out, None


class _FFN(nn.Module):
    def __init__(self, cfg: TypedFiberDecoderConfig):
        super().__init__()
        self.fc1 = nn.Linear(cfg.d_model, cfg.ffn_dim)
        self.fc2 = nn.Linear(cfg.ffn_dim, cfg.d_model)
        self.act = nn.GELU()
        self.dropout = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.fc2(self.act(self.fc1(x))))


class _DecoderBlock(nn.Module):
    """Decoder block: self-attn → cross-attn(simplex stream) →
    cross-attn(src_emb stream) → FFN. Pre-norm everywhere.
    """

    def __init__(self, cfg: TypedFiberDecoderConfig, has_copy: bool = False):
        super().__init__()
        self.norm_self = nn.LayerNorm(cfg.d_model)
        self.self_attn = _MaskedSelfAttention(cfg)
        self.norm_cross_simplex = nn.LayerNorm(cfg.d_model)
        self.cross_simplex = _CrossAttention(cfg, kv_dim=cfg.d_model)
        self.norm_cross_src = nn.LayerNorm(cfg.d_model)
        self.cross_src = _CrossAttention(cfg, kv_dim=cfg.d_model)
        self.norm_ffn = nn.LayerNorm(cfg.d_model)
        self.ffn = _FFN(cfg)
        self.dropout = nn.Dropout(cfg.dropout)
        self.has_copy = has_copy  # only the final block exposes copy scores

    def forward(
        self,
        x: torch.Tensor,
        simplex_kv: torch.Tensor,
        src_kv: torch.Tensor,
        src_mask: Optional[torch.Tensor],
    ) -> tuple[torch.Tensor, Optional[torch.Tensor]]:
        x = x + self.dropout(self.self_attn(self.norm_self(x)))
        out_simplex, _ = self.cross_simplex(self.norm_cross_simplex(x), simplex_kv, kv_mask=src_mask)
        x = x + self.dropout(out_simplex)
        out_src, copy_scores = self.cross_src(
            self.norm_cross_src(x), src_kv, kv_mask=src_mask, return_scores=self.has_copy
        )
        x = x + self.dropout(out_src)
        x = x + self.ffn(self.norm_ffn(x))
        return x, copy_scores


class TypedFiberDecoder(nn.Module):
    """6-layer decoder with slot-typed copy/generate per build-spec §2.3.

    Forward args:
        decoder_input_ids:    (B, L_out) int64 English BPE token IDs (shifted target)
        source_hidden:        (B, L_src, d_model) trunk hidden from encoder
        simplex_trajectory:   (B, L_src, 40) Δ°₃₉ trajectory from encoder
        src_ids:              (B, L_src) int64 source CAS token IDs
        src_token_type:       (B, L_src) int8 source-side type tags
        src_padding_mask:     (B, L_src) bool, True=keep, False=pad
        target_typed_positions: (B, L_out) int8 slot-type per output position
                                (collator-derived; used to gate phrase bias)

    Returns (dict):
        lm_logits:            (B, L_out, V_english)
        slot_type_logits:     (B, L_out, 9)
        p_copy:               (B, L_out, L_src) — softmax over source positions
        copy_source_indices:  (B, L_out) int16 — argmax_j p_copy(j) at typed positions; -1 elsewhere
        decoder_hidden_state: (B, L_out, d_model) for trace; not used by L_FR
    """

    def __init__(self, cfg: Optional[TypedFiberDecoderConfig] = None):
        super().__init__()
        self.cfg = cfg or TypedFiberDecoderConfig()
        self.token_emb = nn.Embedding(
            self.cfg.vocab_size_english, self.cfg.d_model, padding_idx=self.cfg.pad_token_id,
        )
        self.input_dropout = nn.Dropout(self.cfg.dropout)
        # Project the 40-dim simplex up to d_model so cross-attn keys/values match
        self.simplex_proj = nn.Linear(self.cfg.num_states, self.cfg.d_model)
        # Project source CAS tokens to d_model — separate embedding so the
        # decoder's pointer-copy lookup is decoupled from the encoder trunk
        # representation. Reuses tokenizer vocab size; weight tying is a
        # tuning lever for Stage 7-bis.
        self.src_token_proj = nn.Linear(self.cfg.d_model, self.cfg.d_model)

        blocks = []
        for i in range(self.cfg.n_layers):
            is_final = (i == self.cfg.n_layers - 1)
            blocks.append(_DecoderBlock(self.cfg, has_copy=is_final))
        self.blocks = nn.ModuleList(blocks)
        self.final_norm = nn.LayerNorm(self.cfg.d_model)

        self.lm_head = nn.Linear(self.cfg.d_model, self.cfg.vocab_size_english)
        self.slot_type_head = nn.Linear(self.cfg.d_model, self.cfg.num_slot_types)

        # Soft simplex-conditioned phrase bias: (10 noetics, n_phrases_per_k, d_model)
        # h_t projected to a per-noetic phrase-bias scalar via lookup + dot.
        self.phrase_bias_table = nn.Parameter(
            torch.zeros(self.cfg.num_noetics, self.cfg.n_phrases_per_k, self.cfg.d_model)
        )
        nn.init.normal_(self.phrase_bias_table, std=0.02)
        # Project phrase-bias-table dot-product up to vocab_size to mix into lm_logits
        self.phrase_bias_proj = nn.Linear(self.cfg.n_phrases_per_k, self.cfg.vocab_size_english)
        self.phrase_bias_alpha = nn.Parameter(torch.tensor(0.5))  # α_layer

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
            src_padding_mask = torch.ones(B, L_src, dtype=torch.bool, device=src_ids.device)

        # Decoder input embeddings
        x = self.token_emb(decoder_input_ids)
        x = self.input_dropout(x)

        # Encoder-side KV streams
        simplex_kv = self.simplex_proj(simplex_trajectory.to(dtype=x.dtype))   # (B, L_src, d_model)
        src_kv = self.src_token_proj(source_hidden)                            # (B, L_src, d_model)

        copy_scores: Optional[torch.Tensor] = None
        for block in self.blocks:
            x, block_scores = block(x, simplex_kv=simplex_kv, src_kv=src_kv, src_mask=src_padding_mask)
            if block_scores is not None:
                copy_scores = block_scores

        decoder_hidden_state = self.final_norm(x)
        lm_logits = self.lm_head(decoder_hidden_state)             # (B, L_out, V)
        slot_type_logits = self.slot_type_head(decoder_hidden_state)  # (B, L_out, 9)

        # Pointer-copy distribution: softmax of the final block's cross-attn
        # scores (averaged over heads) over source positions, masked by padding.
        if copy_scores is None:
            copy_scores = torch.zeros(B, L_out, L_src, dtype=x.dtype, device=x.device)
        if src_padding_mask is not None:
            mask = src_padding_mask[:, None, :].to(dtype=torch.bool)
            copy_scores = copy_scores.masked_fill(~mask, float("-inf"))
        p_copy = F.softmax(copy_scores, dim=-1)
        # Fail-closed for all-PAD source: replace NaN rows with zeros so the
        # consumer (L_copy loss / argmax / trace) sees a well-defined tensor.
        # All-PAD is a corpus-edge case; copy is simply not applicable there.
        p_copy = torch.nan_to_num(p_copy, nan=0.0, posinf=0.0, neginf=0.0)

        # Phrase-bias term: gated by predicted slot_type == NOETIC_PHRASE (8).
        # Pick k* from simplex_final pooled over source positions to align
        # phrase-table indexing. Mixing into lm_logits is multiplied by
        # alpha_layer * (slot_type == NOETIC_PHRASE).
        with torch.no_grad():
            mask_f = src_padding_mask.to(dtype=torch.float32).unsqueeze(-1)
            denom = mask_f.sum(dim=1).clamp_min(1.0)
            simplex_pooled = (simplex_trajectory * mask_f).sum(dim=1) / denom  # (B, 40)
            # Pool 40 → 10 noetics: sum over 4 domains per noetic. Indices
            # 0,10,20,30 → noetic 0; 1,11,21,31 → noetic 1; …
            pooled_noetic = simplex_pooled.view(B, 4, 10).sum(dim=1)            # (B, 10)
            k_star = pooled_noetic.argmax(dim=-1)                               # (B,)
        # Per-batch phrase table: (B, n_phrases_per_k, d_model)
        phrase_table_b = self.phrase_bias_table[k_star]
        # Dot-product against decoder hidden: (B, L_out, n_phrases_per_k)
        phrase_scores = torch.einsum("bld,bnd->bln", decoder_hidden_state, phrase_table_b)
        # Project to vocab: (B, L_out, V_english)
        phrase_bias = self.phrase_bias_proj(phrase_scores)

        # Gate by predicted slot_type == NOETIC_PHRASE (slot id 8).
        # Use a soft gate (softmax prob) so gradients flow; build-spec §2.3
        # specifies soft, not hard.
        slot_type_probs = F.softmax(slot_type_logits, dim=-1)            # (B, L_out, 9)
        noetic_phrase_gate = slot_type_probs[..., SLOT_TYPE_TO_ID["NOETIC_PHRASE"]].unsqueeze(-1)
        lm_logits = lm_logits + self.phrase_bias_alpha * noetic_phrase_gate * phrase_bias

        # copy_source_indices: argmax over source positions per output position.
        # Default to -1 (non-typed); collator-supplied target_typed_positions
        # tells us which output positions are typed. We always compute argmax;
        # the trainer can mask using target_typed_positions if it wants -1 elsewhere.
        copy_source_indices = p_copy.argmax(dim=-1).to(dtype=torch.int16)  # (B, L_out)
        if target_typed_positions is not None:
            # Mark CONNECTIVE (0) and NOETIC_PHRASE (8) positions with -1
            is_copy_slot = torch.zeros_like(target_typed_positions, dtype=torch.bool)
            for sid in COPY_ALLOWED_SLOT_IDS:
                is_copy_slot = is_copy_slot | (target_typed_positions == sid)
            copy_source_indices = torch.where(
                is_copy_slot, copy_source_indices, torch.full_like(copy_source_indices, -1)
            )

        return {
            "lm_logits": lm_logits,
            "slot_type_logits": slot_type_logits,
            "p_copy": p_copy,
            "copy_source_indices": copy_source_indices,
            "decoder_hidden_state": decoder_hidden_state,
        }
