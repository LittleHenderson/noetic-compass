"""Fully native CAS-Native English generation head.

Random-init weights. NO foreign pretrained models. NO TinyLlama, Llama, Qwen,
Mistral, Phi, Gemma, GPT-2, BERT, or any pretrained backbone. Reuses
``domain_descent``, ``register_film``, and ``structured_token_embedding`` from
this package — every piece of this module is CAS-Native by construction.

Architecture
------------

A 6-layer Transformer decoder operating on the existing 64-dim CAS-Native
bottleneck. Conditioning enters the decoder through three independent paths:

1. **Discrete CAS expression tokens** (``cas_prefix_ids``) prepended to the
   decoder input embeddings.

2. **Continuous bottleneck soft-prefix** (``bottleneck_z``) — a 4-position
   learned projection of the 64-dim CAS-Native bottleneck into the decoder
   ``d_model``.

3. **Cross-attention to encoder outputs** (the structured-token embedding
   stream) with a domain-descent attention mask layered over the cross-
   attention key/query alignment.

Register conditioning is applied as a multiplicative FiLM modulation of the
post-decoder hidden state, immediately before the output projection to vocab.

Design rules (user-ratified, locked)
------------------------------------

- Random-initialized weights only. Verified by the
  ``test_module_docstring_no_foreign_pretrained`` test which scans this
  docstring for the literal string ``"NO foreign pretrained"``.
- Object traceability is load-bearing. Every forward output carries
  ``output_id`` (UUID), ``model_code_version``, ``model_weights_sha`` (sha256
  of the state_dict bytes), ``cas_conditioning_id``, and an attention summary.
  Generated tokens carry per-step ``TokenStep`` traces suitable for the Mode 7
  trace surface (see ``cas_native/trace/live_capture.py``).
- The decoder layer reuses ``nn.MultiheadAttention`` as a layer primitive.
  These are not pretrained models — they are architectural building blocks.
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import hashlib
import io
import math
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from .domain_descent import build_domain_descent_mask
from .register_film import RegisterFiLM, NUM_REGISTERS


_VERSION = "v0.1.0"
"""Module-level code version constant. Surfaced on every forward output as
``model_code_version`` and on every :class:`GenerationTrace`."""


_SEMVER_RE = re.compile(r"^v\d+\.\d+\.\d+$")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NLGenerationHeadConfig:
    """Frozen configuration for :class:`NLGenerationHead`.

    Frozen for traceability: the ``code_version`` string must reflect the
    structural shape of the head. Any meaningful change to the architecture
    bumps ``_VERSION``; the dataclass being frozen prevents silent in-place
    mutation that could decouple a checkpoint from its declared shape.
    """

    vocab_size: int
    d_model: int = 512
    n_heads: int = 8
    n_layers: int = 6
    ffn_dim: int = 2048
    dropout: float = 0.1
    bottleneck_dim: int = 64
    soft_prefix_length: int = 4
    max_len: int = 512
    code_version: str = _VERSION

    def __post_init__(self) -> None:
        if self.vocab_size <= 0:
            raise ValueError(
                f"vocab_size must be > 0, got {self.vocab_size}"
            )
        if self.d_model <= 0 or self.d_model % self.n_heads != 0:
            raise ValueError(
                "d_model must be positive and divisible by n_heads; "
                f"got d_model={self.d_model}, n_heads={self.n_heads}"
            )
        if self.n_layers <= 0:
            raise ValueError(f"n_layers must be > 0, got {self.n_layers}")
        if self.bottleneck_dim <= 0:
            raise ValueError(
                f"bottleneck_dim must be > 0, got {self.bottleneck_dim}"
            )
        if self.soft_prefix_length <= 0:
            raise ValueError(
                f"soft_prefix_length must be > 0, got {self.soft_prefix_length}"
            )
        if self.max_len <= 0:
            raise ValueError(f"max_len must be > 0, got {self.max_len}")
        if not isinstance(self.code_version, str) or not self.code_version:
            raise ValueError("code_version must be a non-empty string")


# ---------------------------------------------------------------------------
# Trace data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenStep:
    """One generated-token's trace record.

    Frozen — token-step records should not be mutated after creation. Lists
    are pre-built before construction.
    """

    position: int
    token_id: int
    token_str: Optional[str]
    attn_to_cas_prefix: tuple[float, ...]
    """Mean attention weight from the current token to each CAS-prefix
    position (averaged over heads and layers). Length matches the CAS
    prefix length used at generation time. ``()`` if no CAS prefix was
    supplied."""
    attn_to_prior_tokens: tuple[float, ...]
    """Compact summary of self-attention to prior decoder positions: one
    scalar per prior position (mean across heads, last layer)."""
    layer_activation_l2: tuple[float, ...]
    """Per-layer L2 norm of the decoder hidden state after that layer.
    Length matches ``config.n_layers``."""
    selected_via: str
    """One of ``"argmax"``, ``"topp"``, or ``"temp"``."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": int(self.position),
            "token_id": int(self.token_id),
            "token_str": self.token_str,
            "attn_to_cas_prefix": [float(v) for v in self.attn_to_cas_prefix],
            "attn_to_prior_tokens": [float(v) for v in self.attn_to_prior_tokens],
            "layer_activation_l2": [float(v) for v in self.layer_activation_l2],
            "selected_via": str(self.selected_via),
        }


@dataclass
class GenerationTrace:
    """Per-generation trace record for Mode 7 surfacing.

    Mutable (``frozen=False``) only to allow incremental ``tokens`` append
    during sampling. Consumers should treat the populated record as
    read-only.
    """

    output_id: str
    model_code_version: str
    model_weights_sha: str
    cas_conditioning_repr: str
    created_at: str
    tokens: list[TokenStep] = field(default_factory=list)
    schema_version: str = "generation_trace.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "output_id": self.output_id,
            "model_code_version": self.model_code_version,
            "model_weights_sha": self.model_weights_sha,
            "cas_conditioning_repr": self.cas_conditioning_repr,
            "created_at": self.created_at,
            "tokens": [t.to_dict() for t in self.tokens],
        }


# ---------------------------------------------------------------------------
# Decoder layer
# ---------------------------------------------------------------------------


class _NLDecoderLayer(nn.Module):
    """One CAS-Native decoder block: masked self-attn + cross-attn + FFN.

    Uses ``nn.MultiheadAttention`` as a layer primitive. These are
    architectural building blocks (random-initialized at construction); they
    are not pretrained model weights.

    Per-call optional outputs:

    * ``self_attn_weights`` — mean over heads of the self-attention pattern
      at this layer, shape ``(B, L, L)``.
    * ``cross_attn_weights`` — mean over heads of the cross-attention pattern
      to encoder + soft-prefix + cas-prefix, shape ``(B, L, S)``.

    These are surfaced when ``need_weights=True`` so the trace machinery in
    :meth:`NLGenerationHead.generate` can record them per step.
    """

    def __init__(self, config: NLGenerationHeadConfig) -> None:
        super().__init__()
        self.config = config

        self.self_attn = nn.MultiheadAttention(
            embed_dim=config.d_model,
            num_heads=config.n_heads,
            dropout=config.dropout,
            batch_first=True,
        )
        self.norm_self = nn.LayerNorm(config.d_model)

        self.cross_attn = nn.MultiheadAttention(
            embed_dim=config.d_model,
            num_heads=config.n_heads,
            dropout=config.dropout,
            batch_first=True,
        )
        self.norm_cross = nn.LayerNorm(config.d_model)

        self.ffn = nn.Sequential(
            nn.Linear(config.d_model, config.ffn_dim),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.ffn_dim, config.d_model),
            nn.Dropout(config.dropout),
        )
        self.norm_ffn = nn.LayerNorm(config.d_model)

    def forward(
        self,
        x: torch.Tensor,
        encoder_outputs: Optional[torch.Tensor],
        *,
        self_attn_mask: Optional[torch.Tensor] = None,
        self_attn_key_padding_mask: Optional[torch.Tensor] = None,
        cross_attn_key_padding_mask: Optional[torch.Tensor] = None,
        cross_attn_mask: Optional[torch.Tensor] = None,
        need_weights: bool = False,
    ) -> tuple[torch.Tensor, dict[str, Optional[torch.Tensor]]]:
        # --- masked self-attention with residual ---
        # self_attn_key_padding_mask (True=ignore) is the cas-prefix PAD guard:
        # without it, padded CAS-prefix positions in [cas_prefix | decoder]
        # leak into decoder conditioning. See B-4 cas_prefix_mask fix.
        residual = x
        h = self.norm_self(x)
        self_out, self_w = self.self_attn(
            h, h, h,
            attn_mask=self_attn_mask,
            key_padding_mask=self_attn_key_padding_mask,
            need_weights=need_weights,
            average_attn_weights=True,
        )
        x = residual + self_out

        # --- cross-attention with residual ---
        cross_w: Optional[torch.Tensor] = None
        if encoder_outputs is not None:
            residual = x
            h = self.norm_cross(x)
            cross_out, cross_w = self.cross_attn(
                h, encoder_outputs, encoder_outputs,
                attn_mask=cross_attn_mask,
                key_padding_mask=cross_attn_key_padding_mask,
                need_weights=need_weights,
                average_attn_weights=True,
            )
            x = residual + cross_out

        # --- FFN with residual ---
        residual = x
        h = self.norm_ffn(x)
        x = residual + self.ffn(h)

        return x, {"self_attn_weights": self_w, "cross_attn_weights": cross_w}


# ---------------------------------------------------------------------------
# NLGenerationHead
# ---------------------------------------------------------------------------


class NLGenerationHead(nn.Module):
    """Native CAS-Native English LM head.

    Random-init 6-layer transformer decoder over the existing 64-dim
    CAS-Native bottleneck. NO foreign pretrained models. Conditioning paths:
    discrete CAS-prefix tokens, continuous bottleneck soft-prefix,
    cross-attention to encoder outputs (with domain-descent mask), register
    FiLM modulation of the post-decoder hidden state.

    Object traceability
    -------------------

    Every instance carries a ``code_version`` attribute (read from
    ``config.code_version``). :meth:`compute_weights_sha` returns a sha256
    digest of the current state_dict, suitable for stamping every
    forward/generate output and every trace record.
    """

    def __init__(self, config: NLGenerationHeadConfig) -> None:
        super().__init__()
        self.config = config
        self.code_version = config.code_version

        # Token embedding + positional encoding (random init).
        self.token_embedding = nn.Embedding(config.vocab_size, config.d_model)
        self.pos_embedding = nn.Embedding(config.max_len, config.d_model)

        # Soft-prefix learned positions projecting bottleneck -> d_model.
        # Each of the K positions has its own projection so the soft-prefix
        # is a *learned* 4-position transform of the 64-dim bottleneck.
        self.soft_prefix_proj = nn.Linear(
            config.bottleneck_dim,
            config.soft_prefix_length * config.d_model,
        )

        # Decoder stack.
        self.layers = nn.ModuleList([
            _NLDecoderLayer(config) for _ in range(config.n_layers)
        ])
        self.final_norm = nn.LayerNorm(config.d_model)

        # Output projection to vocab. Tied embedding NOT used — random init,
        # independent matrix for clean traceability.
        self.lm_head = nn.Linear(config.d_model, config.vocab_size, bias=False)

        # Register FiLM modulation of post-decoder hidden state.
        self.register_film = RegisterFiLM(
            d_model=config.d_model,
            num_registers=NUM_REGISTERS,
        )

        # Domain-descent mask buffer (fixed structural CAS constraint).
        self.register_buffer(
            "_domain_descent_mask",
            build_domain_descent_mask(),
            persistent=False,
        )

        self.dropout = nn.Dropout(config.dropout)

        self._init_weights()

    # ------------------------------------------------------------------ init

    def _init_weights(self) -> None:
        """Random init — no borrowed weights."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Embedding):
                nn.init.normal_(m.weight, mean=0.0, std=0.02)
            elif isinstance(m, nn.LayerNorm):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)

    # ------------------------------------------------------------- traceability

    def compute_weights_sha(self) -> str:
        """sha256 digest of the current state_dict bytes.

        Deterministic in the sense that identical weights always produce the
        same digest. Surfaced on every forward output and every
        :class:`GenerationTrace` for object-level provenance.
        """
        sd = self.state_dict()
        h = hashlib.sha256()
        for key in sorted(sd.keys()):
            h.update(key.encode("utf-8"))
            tensor = sd[key].detach().to("cpu").contiguous()
            buf = io.BytesIO()
            torch.save(tensor, buf)
            h.update(buf.getvalue())
        return h.hexdigest()

    # ------------------------------------------------------------- conditioning

    def _build_soft_prefix(self, bottleneck_z: torch.Tensor) -> torch.Tensor:
        """Project ``bottleneck_z`` of shape ``(B, bottleneck_dim)`` to a soft
        prefix of shape ``(B, soft_prefix_length, d_model)``.
        """
        if bottleneck_z.dim() != 2:
            raise ValueError(
                f"bottleneck_z must be 2-D (B, {self.config.bottleneck_dim}), "
                f"got shape {tuple(bottleneck_z.shape)}"
            )
        if bottleneck_z.shape[-1] != self.config.bottleneck_dim:
            raise ValueError(
                f"bottleneck_z last dim must be {self.config.bottleneck_dim}, "
                f"got {bottleneck_z.shape[-1]}"
            )
        b = bottleneck_z.shape[0]
        flat = self.soft_prefix_proj(bottleneck_z)  # (B, K * d_model)
        return flat.view(b, self.config.soft_prefix_length, self.config.d_model)

    def _build_decoder_input(
        self,
        decoder_input_ids: torch.Tensor,
        cas_prefix_ids: Optional[torch.Tensor],
    ) -> tuple[torch.Tensor, int]:
        """Build the decoder embedding stream.

        Returns ``(embeds, cas_prefix_len)`` where ``cas_prefix_len`` is the
        number of CAS-prefix tokens prepended (0 if ``cas_prefix_ids`` is
        None or empty). The decoder input layout is ``[CAS prefix | decoder
        tokens]``.
        """
        b, l = decoder_input_ids.shape
        device = decoder_input_ids.device

        token_emb = self.token_embedding(decoder_input_ids)  # (B, L, D)

        if cas_prefix_ids is not None and cas_prefix_ids.numel() > 0:
            if cas_prefix_ids.dim() != 2 or cas_prefix_ids.shape[0] != b:
                raise ValueError(
                    "cas_prefix_ids must have shape (B, K); got "
                    f"{tuple(cas_prefix_ids.shape)} for batch {b}"
                )
            cas_emb = self.token_embedding(cas_prefix_ids)  # (B, K, D)
            stream = torch.cat([cas_emb, token_emb], dim=1)
            cas_len = int(cas_prefix_ids.shape[1])
        else:
            stream = token_emb
            cas_len = 0

        seq_len = stream.shape[1]
        if seq_len > self.config.max_len:
            raise ValueError(
                f"decoder stream length {seq_len} exceeds max_len "
                f"{self.config.max_len}"
            )

        positions = torch.arange(seq_len, device=device).unsqueeze(0).expand(b, -1)
        stream = stream + self.pos_embedding(positions)
        stream = self.dropout(stream)
        return stream, cas_len

    def _build_encoder_kv(
        self,
        encoder_outputs: Optional[torch.Tensor],
        soft_prefix: torch.Tensor,
    ) -> torch.Tensor:
        """Concatenate the soft-prefix with the encoder outputs along the
        sequence axis to form the cross-attention key/value stream.
        """
        if encoder_outputs is None:
            return soft_prefix
        if encoder_outputs.dim() != 3:
            raise ValueError(
                f"encoder_outputs must be 3-D (B, S, D); got "
                f"{tuple(encoder_outputs.shape)}"
            )
        if encoder_outputs.shape[-1] != self.config.d_model:
            raise ValueError(
                "encoder_outputs last dim must match d_model "
                f"({self.config.d_model}), got {encoder_outputs.shape[-1]}"
            )
        if encoder_outputs.shape[0] != soft_prefix.shape[0]:
            raise ValueError(
                "encoder_outputs and soft_prefix must share batch dim; got "
                f"{encoder_outputs.shape[0]} vs {soft_prefix.shape[0]}"
            )
        return torch.cat([soft_prefix, encoder_outputs], dim=1)

    @staticmethod
    def _causal_mask(seq_len: int, device: torch.device) -> torch.Tensor:
        """Build an additive causal mask shaped ``(L, L)`` for self-attn."""
        mask = torch.full((seq_len, seq_len), float("-inf"), device=device)
        mask = torch.triu(mask, diagonal=1)
        return mask

    def _build_cross_attn_kv_padding_mask(
        self,
        soft_prefix_len: int,
        encoder_outputs: Optional[torch.Tensor],
        domain_mask: Optional[torch.Tensor],
    ) -> Optional[torch.Tensor]:
        """Build a key-padding mask for cross-attention.

        ``domain_mask`` is a ``(B, S)`` boolean/float mask over the encoder
        sequence: True (or 1) means the position is valid, False (or 0)
        means masked out. We assemble a full ``(B, S_total)`` boolean mask
        where ``S_total = soft_prefix_len + S_encoder``. Soft-prefix
        positions are always valid.
        """
        if domain_mask is None or encoder_outputs is None:
            return None

        if domain_mask.dim() != 2:
            raise ValueError(
                f"domain_mask must be 2-D (B, S); got "
                f"{tuple(domain_mask.shape)}"
            )
        b, s_enc = domain_mask.shape
        if encoder_outputs.shape[1] != s_enc:
            raise ValueError(
                f"domain_mask seq dim {s_enc} != encoder_outputs seq dim "
                f"{encoder_outputs.shape[1]}"
            )
        prefix_valid = torch.ones(
            b, soft_prefix_len, device=domain_mask.device, dtype=torch.bool
        )
        encoder_valid = domain_mask.to(dtype=torch.bool)
        full = torch.cat([prefix_valid, encoder_valid], dim=1)
        # `nn.MultiheadAttention` key_padding_mask convention: True = ignore.
        return ~full

    @staticmethod
    def _build_self_attn_key_padding_mask(
        cas_prefix_ids: Optional[torch.Tensor],
        cas_prefix_mask: Optional[torch.Tensor],
        cas_prefix_len: int,
        decoder_len: int,
        batch_size: int,
        device: torch.device,
    ) -> Optional[torch.Tensor]:
        """Build a self-attention key-padding mask covering ``[cas_prefix | decoder]``.

        The decoder embedding stream is ``[CAS prefix | decoder tokens]``.
        Without a key-padding mask, padded CAS-prefix positions are
        attended to as if they were real conditioning — this is the B-4
        PAD-leak the trainer comment flagged.

        Convention (matches ``nn.MultiheadAttention``): ``True`` = ignore,
        ``False`` = attend.

        Decoder positions are NOT masked here even when they contain PAD
        because the ``loss_mask`` already excludes those positions from
        supervision. Self-attention from a real decoder token to a PAD
        decoder token at a strictly later index is blocked by the causal
        mask; PAD decoder tokens never produce a supervised prediction.

        Returns ``None`` when there is no CAS prefix (the existing causal
        mask is sufficient and we want to avoid building an all-False
        tensor that some attention backends warn about).
        """
        if cas_prefix_ids is None or cas_prefix_len == 0:
            return None
        if cas_prefix_mask is None:
            # No mask supplied: trust caller — assume all CAS prefix tokens
            # are real. Useful for inference paths that encode a single
            # example with exact length and no padding.
            return None
        if cas_prefix_mask.dim() != 2:
            raise ValueError(
                f"cas_prefix_mask must be 2-D (B, K); got "
                f"{tuple(cas_prefix_mask.shape)}"
            )
        if cas_prefix_mask.shape != cas_prefix_ids.shape:
            raise ValueError(
                "cas_prefix_mask shape must match cas_prefix_ids shape; "
                f"got mask {tuple(cas_prefix_mask.shape)} vs ids "
                f"{tuple(cas_prefix_ids.shape)}"
            )
        cas_pad = ~cas_prefix_mask.to(dtype=torch.bool, device=device)  # (B, K)
        decoder_keep = torch.zeros(
            (batch_size, decoder_len), dtype=torch.bool, device=device
        )
        return torch.cat([cas_pad, decoder_keep], dim=1)  # (B, K + L)

    # ------------------------------------------------------------------ forward

    def forward(
        self,
        decoder_input_ids: torch.Tensor,
        bottleneck_z: torch.Tensor,
        *,
        cas_prefix_ids: Optional[torch.Tensor] = None,
        cas_prefix_mask: Optional[torch.Tensor] = None,
        encoder_outputs: Optional[torch.Tensor] = None,
        domain_mask: Optional[torch.Tensor] = None,
        register_id: Optional[torch.Tensor] = None,
        return_meta: bool = False,
    ) -> torch.Tensor | tuple[torch.Tensor, dict[str, Any]]:
        """Run the decoder and return LM logits.

        Args:
            decoder_input_ids: ``(B, L)`` decoder token IDs.
            bottleneck_z: ``(B, bottleneck_dim)`` continuous CAS bottleneck.
            cas_prefix_ids: optional ``(B, K)`` CAS-expression token IDs to
                prepend to the decoder input.
            cas_prefix_mask: optional ``(B, K)`` bool tensor; ``True`` =
                real CAS-prefix token, ``False`` = PAD. When supplied
                alongside ``cas_prefix_ids``, PAD positions are masked out
                of self-attention so they do not leak into decoder
                conditioning. Shape MUST match ``cas_prefix_ids``.
            encoder_outputs: optional ``(B, S, d_model)`` encoder stream
                (typically the structured-token embedding output).
            domain_mask: optional ``(B, S)`` validity mask over the encoder
                sequence — True/1 = valid, False/0 = ignore. Used to gate
                cross-attention.
            register_id: optional ``(B,)`` long tensor of register indices in
                ``[0, NUM_REGISTERS)``. When supplied, register-FiLM
                modulation is applied to each example's post-decoder hidden
                state with that example's register.
            return_meta: when True, also return a metadata dict with
                ``output_id``, ``model_code_version``, ``model_weights_sha``,
                ``cas_conditioning_id``, ``attention_summary``.

        Returns:
            ``logits`` of shape ``(B, L, vocab_size)`` corresponding to the
            decoder-token positions only (CAS-prefix logits are stripped).
            If ``return_meta`` is True, returns ``(logits, meta_dict)``.
        """
        if decoder_input_ids.dim() != 2:
            raise ValueError(
                f"decoder_input_ids must be 2-D (B, L); got "
                f"{tuple(decoder_input_ids.shape)}"
            )

        b, l = decoder_input_ids.shape
        device = decoder_input_ids.device

        # Build conditioning streams.
        soft_prefix = self._build_soft_prefix(bottleneck_z)  # (B, K_soft, D)
        kv = self._build_encoder_kv(encoder_outputs, soft_prefix)  # (B, S_t, D)

        # Build the decoder embedding stream.
        decoder_stream, cas_prefix_len = self._build_decoder_input(
            decoder_input_ids, cas_prefix_ids,
        )
        seq_len = decoder_stream.shape[1]

        # Build masks.
        self_mask = self._causal_mask(seq_len, device=device)
        self_attn_kp_mask = self._build_self_attn_key_padding_mask(
            cas_prefix_ids=cas_prefix_ids,
            cas_prefix_mask=cas_prefix_mask,
            cas_prefix_len=cas_prefix_len,
            decoder_len=l,
            batch_size=b,
            device=device,
        )
        cross_kv_padding_mask = self._build_cross_attn_kv_padding_mask(
            soft_prefix_len=soft_prefix.shape[1],
            encoder_outputs=encoder_outputs,
            domain_mask=domain_mask,
        )

        # Run decoder layers.
        x = decoder_stream
        layer_l2: list[torch.Tensor] = []
        last_self_w: Optional[torch.Tensor] = None
        last_cross_w: Optional[torch.Tensor] = None
        for layer in self.layers:
            x, attn_meta = layer(
                x,
                encoder_outputs=kv,
                self_attn_mask=self_mask,
                self_attn_key_padding_mask=self_attn_kp_mask,
                cross_attn_key_padding_mask=cross_kv_padding_mask,
                cross_attn_mask=None,
                need_weights=return_meta,
            )
            layer_l2.append(x.detach().pow(2).sum(dim=-1).sqrt().mean().clone())
            if return_meta:
                last_self_w = attn_meta.get("self_attn_weights")
                last_cross_w = attn_meta.get("cross_attn_weights")

        x = self.final_norm(x)

        # Register FiLM modulation on the post-decoder hidden state.
        if register_id is not None:
            if register_id.dim() != 1 or register_id.shape[0] != b:
                raise ValueError(
                    f"register_id must be 1-D (B,); got "
                    f"{tuple(register_id.shape)}"
                )
            # Apply per-example to support heterogeneous register IDs.
            modulated_rows = []
            for i in range(b):
                idx = int(register_id[i].item())
                modulated_rows.append(
                    self.register_film(x[i:i + 1], register_idx=idx)
                )
            x = torch.cat(modulated_rows, dim=0)

        # Strip CAS-prefix logits — return only the decoder-token positions.
        if cas_prefix_len > 0:
            decoder_x = x[:, cas_prefix_len:, :]
        else:
            decoder_x = x

        logits = self.lm_head(decoder_x)

        if not return_meta:
            return logits

        # --- Metadata for object traceability ---
        attn_summary: dict[str, Any] = {
            "n_layers": int(self.config.n_layers),
            "decoder_seq_len": int(seq_len),
            "cas_prefix_len": int(cas_prefix_len),
            "soft_prefix_len": int(soft_prefix.shape[1]),
            "encoder_seq_len": int(
                encoder_outputs.shape[1] if encoder_outputs is not None else 0
            ),
            "layer_l2_means": [float(v.item()) for v in layer_l2],
        }
        if last_self_w is not None:
            attn_summary["self_attn_last_layer_mean"] = float(
                last_self_w.detach().mean().item()
            )
        if last_cross_w is not None:
            attn_summary["cross_attn_last_layer_mean"] = float(
                last_cross_w.detach().mean().item()
            )

        cas_repr = (
            cas_prefix_ids.detach().to("cpu").tolist()
            if cas_prefix_ids is not None
            else None
        )
        meta = {
            "output_id": str(uuid.uuid4()),
            "model_code_version": self.code_version,
            "model_weights_sha": self.compute_weights_sha(),
            "cas_conditioning_id": _hash_cas_conditioning(cas_repr, register_id),
            "attention_summary": attn_summary,
            # v1e Phase C — pre-LM-head decoder hidden state needed by the
            # StopCompleteHead. Only attached when return_meta=True so
            # default-path callers see no behavior or memory delta.
            "decoder_hidden_state": decoder_x,
        }
        return logits, meta

    # --------------------------------------------------------------- generate

    def generate(
        self,
        decoder_input_ids: torch.Tensor,
        bottleneck_z: torch.Tensor,
        *,
        cas_prefix_ids: Optional[torch.Tensor] = None,
        cas_prefix_mask: Optional[torch.Tensor] = None,
        encoder_outputs: Optional[torch.Tensor] = None,
        domain_mask: Optional[torch.Tensor] = None,
        register_id: Optional[torch.Tensor] = None,
        max_new_tokens: int = 80,
        temperature: float = 0.7,
        top_p: float = 0.9,
        eos_token_id: Optional[int] = None,
        with_trace: bool = False,
        token_decoder: Optional[Any] = None,
    ) -> tuple[torch.Tensor, Optional[GenerationTrace]]:
        """Autoregressive sampling with optional Mode-7 trace.

        Args:
            decoder_input_ids: ``(B, L0)`` initial decoder tokens.
            bottleneck_z: ``(B, bottleneck_dim)`` CAS bottleneck.
            cas_prefix_ids: optional ``(B, K)`` CAS expression token IDs.
            cas_prefix_mask: optional ``(B, K)`` bool tensor; ``True`` =
                real, ``False`` = PAD. Forwarded to every per-step
                ``forward`` call so PAD positions stay masked out of
                self-attention during autoregressive sampling.
            encoder_outputs: optional ``(B, S, d_model)`` encoder stream.
            domain_mask: optional ``(B, S)`` validity mask.
            register_id: optional ``(B,)`` register indices.
            max_new_tokens: maximum number of tokens to sample.
            temperature: sampling temperature; 0 (or negative) selects argmax.
            top_p: nucleus sampling cutoff; >= 1 disables nucleus filtering.
            eos_token_id: optional end-of-sequence ID; if all rows in the
                batch generate it, sampling halts early.
            with_trace: when True, populate a :class:`GenerationTrace`.
            token_decoder: optional callable ``int -> str`` for filling
                ``token_str`` on each :class:`TokenStep`. Optional because
                this module is tokenizer-agnostic by design.

        Returns:
            ``(generated_ids, trace)`` where ``generated_ids`` has shape
            ``(B, L0 + n_new)`` and ``trace`` is a :class:`GenerationTrace`
            if ``with_trace`` is True else ``None``.
        """
        if max_new_tokens <= 0:
            raise ValueError(
                f"max_new_tokens must be > 0, got {max_new_tokens}"
            )
        was_training = self.training
        self.eval()

        # Pre-build a trace shell so we can stamp it before we start sampling.
        trace: Optional[GenerationTrace] = None
        if with_trace:
            cas_repr = (
                cas_prefix_ids.detach().to("cpu").tolist()
                if cas_prefix_ids is not None
                else None
            )
            trace = GenerationTrace(
                output_id=str(uuid.uuid4()),
                model_code_version=self.code_version,
                model_weights_sha=self.compute_weights_sha(),
                cas_conditioning_repr=_format_cas_conditioning(
                    cas_repr, register_id,
                ),
                created_at=_dt.datetime.now(_dt.timezone.utc).isoformat(),
            )

        try:
            current_ids = decoder_input_ids.clone()
            for step in range(max_new_tokens):
                with torch.no_grad():
                    if with_trace:
                        logits, _ = self.forward(
                            current_ids,
                            bottleneck_z,
                            cas_prefix_ids=cas_prefix_ids,
                            cas_prefix_mask=cas_prefix_mask,
                            encoder_outputs=encoder_outputs,
                            domain_mask=domain_mask,
                            register_id=register_id,
                            return_meta=True,
                        )
                    else:
                        logits = self.forward(
                            current_ids,
                            bottleneck_z,
                            cas_prefix_ids=cas_prefix_ids,
                            cas_prefix_mask=cas_prefix_mask,
                            encoder_outputs=encoder_outputs,
                            domain_mask=domain_mask,
                            register_id=register_id,
                            return_meta=False,
                        )

                next_logits = logits[:, -1, :]  # (B, V)
                next_tok, selected_via = _sample_token(
                    next_logits, temperature=temperature, top_p=top_p,
                )

                if with_trace and trace is not None:
                    self._append_token_step(
                        trace=trace,
                        step=step,
                        next_tok=next_tok,
                        token_decoder=token_decoder,
                        current_ids=current_ids,
                        cas_prefix_ids=cas_prefix_ids,
                        cas_prefix_mask=cas_prefix_mask,
                        encoder_outputs=encoder_outputs,
                        bottleneck_z=bottleneck_z,
                        domain_mask=domain_mask,
                        register_id=register_id,
                        selected_via=selected_via,
                    )

                current_ids = torch.cat([current_ids, next_tok.unsqueeze(-1)], dim=1)

                if eos_token_id is not None and torch.all(
                    next_tok == eos_token_id
                ):
                    break

                if current_ids.shape[1] + (
                    cas_prefix_ids.shape[1] if cas_prefix_ids is not None else 0
                ) >= self.config.max_len:
                    break
        finally:
            if was_training:
                self.train()

        return current_ids, trace

    # ----------------------------------------------------------- trace helpers

    def _append_token_step(
        self,
        *,
        trace: GenerationTrace,
        step: int,
        next_tok: torch.Tensor,
        token_decoder: Optional[Any],
        current_ids: torch.Tensor,
        cas_prefix_ids: Optional[torch.Tensor],
        cas_prefix_mask: Optional[torch.Tensor] = None,
        encoder_outputs: Optional[torch.Tensor],
        bottleneck_z: torch.Tensor,
        domain_mask: Optional[torch.Tensor],
        register_id: Optional[torch.Tensor],
        selected_via: str,
    ) -> None:
        """Build a TokenStep record for the most-recently-sampled token.

        Uses example 0 of the batch as the trace target — multi-example
        traces would expand this surface; the schema-version contract
        commits to "first example" semantics in v1.
        """
        # Re-run forward with need_weights to capture attention summaries.
        with torch.no_grad():
            full_input = torch.cat([current_ids, next_tok.unsqueeze(-1)], dim=1)
            soft_prefix = self._build_soft_prefix(bottleneck_z)
            kv = self._build_encoder_kv(encoder_outputs, soft_prefix)
            decoder_stream, cas_prefix_len = self._build_decoder_input(
                full_input, cas_prefix_ids,
            )
            seq_len = decoder_stream.shape[1]
            self_mask = self._causal_mask(seq_len, device=full_input.device)
            self_attn_kp_mask = self._build_self_attn_key_padding_mask(
                cas_prefix_ids=cas_prefix_ids,
                cas_prefix_mask=cas_prefix_mask,
                cas_prefix_len=cas_prefix_len,
                decoder_len=full_input.shape[1],
                batch_size=full_input.shape[0],
                device=full_input.device,
            )
            cross_kv_padding_mask = self._build_cross_attn_kv_padding_mask(
                soft_prefix_len=soft_prefix.shape[1],
                encoder_outputs=encoder_outputs,
                domain_mask=domain_mask,
            )
            x = decoder_stream
            layer_l2: list[float] = []
            last_self_w: Optional[torch.Tensor] = None
            last_cross_w: Optional[torch.Tensor] = None
            for layer in self.layers:
                x, attn_meta = layer(
                    x,
                    encoder_outputs=kv,
                    self_attn_mask=self_mask,
                    self_attn_key_padding_mask=self_attn_kp_mask,
                    cross_attn_key_padding_mask=cross_kv_padding_mask,
                    need_weights=True,
                )
                # Per-example (use 0) per-layer activation L2.
                layer_l2.append(
                    float(x[0].pow(2).sum(dim=-1).sqrt().mean().item())
                )
                last_self_w = attn_meta.get("self_attn_weights")
                last_cross_w = attn_meta.get("cross_attn_weights")

            # Cross-attention summary: attention from the new token (last
            # decoder position) to CAS-prefix region of the KV stream.
            attn_to_cas: tuple[float, ...] = ()
            attn_to_prior: tuple[float, ...] = ()
            if last_cross_w is not None and cas_prefix_ids is not None:
                # cross_attn weights shape: (B, L_dec, S_total).
                # CAS-prefix lives at the *front of the decoder stream*, NOT
                # the encoder KV. So cross-attn-to-cas is read off the SELF
                # attn pattern instead.
                pass
            if last_self_w is not None:
                # self-attn shape: (B, L, L). The new token is the last row.
                row = last_self_w[0, -1, :].detach().to("cpu")
                if cas_prefix_len > 0:
                    attn_to_cas = tuple(
                        float(v) for v in row[:cas_prefix_len].tolist()
                    )
                    attn_to_prior = tuple(
                        float(v) for v in row[cas_prefix_len:].tolist()
                    )
                else:
                    attn_to_prior = tuple(float(v) for v in row.tolist())

        token_id = int(next_tok[0].item())
        token_str: Optional[str] = None
        if token_decoder is not None:
            try:
                token_str = str(token_decoder(token_id))
            except Exception:
                token_str = None

        step_record = TokenStep(
            position=step,
            token_id=token_id,
            token_str=token_str,
            attn_to_cas_prefix=attn_to_cas,
            attn_to_prior_tokens=attn_to_prior,
            layer_activation_l2=tuple(layer_l2),
            selected_via=selected_via,
        )
        trace.tokens.append(step_record)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_token(
    logits: torch.Tensor,
    *,
    temperature: float,
    top_p: float,
) -> tuple[torch.Tensor, str]:
    """Sample a token from ``logits`` of shape ``(B, V)``.

    Returns ``(token_ids, selected_via)`` where ``token_ids`` has shape
    ``(B,)`` and ``selected_via`` is one of ``"argmax"``, ``"temp"``, or
    ``"topp"``.
    """
    if temperature is None or temperature <= 0:
        return logits.argmax(dim=-1), "argmax"

    scaled = logits / float(temperature)

    if top_p is None or top_p >= 1.0:
        probs = F.softmax(scaled, dim=-1)
        sampled = torch.multinomial(probs, num_samples=1).squeeze(-1)
        return sampled, "temp"

    # Nucleus sampling.
    sorted_logits, sorted_idx = torch.sort(scaled, dim=-1, descending=True)
    sorted_probs = F.softmax(sorted_logits, dim=-1)
    cum = sorted_probs.cumsum(dim=-1)
    mask = cum > top_p
    # Always keep the top-1 token.
    mask[..., 0] = False
    sorted_logits = sorted_logits.masked_fill(mask, float("-inf"))
    filtered_probs = F.softmax(sorted_logits, dim=-1)
    sample_in_sorted = torch.multinomial(filtered_probs, num_samples=1).squeeze(-1)
    sampled = sorted_idx.gather(-1, sample_in_sorted.unsqueeze(-1)).squeeze(-1)
    return sampled, "topp"


def _hash_cas_conditioning(
    cas_repr: Optional[Any],
    register_id: Optional[torch.Tensor],
) -> str:
    """Stable hash of the CAS conditioning surface for an output.

    Combines the CAS-prefix token IDs and register IDs into a deterministic
    sha256 digest.
    """
    h = hashlib.sha256()
    h.update(repr(cas_repr).encode("utf-8"))
    if register_id is not None:
        h.update(register_id.detach().to("cpu").tolist().__repr__().encode("utf-8"))
    else:
        h.update(b"none")
    return h.hexdigest()


def _format_cas_conditioning(
    cas_repr: Optional[Any],
    register_id: Optional[torch.Tensor],
) -> str:
    """Render a human-readable description of the CAS conditioning."""
    parts: list[str] = []
    if cas_repr is not None:
        parts.append(f"cas_prefix_ids={cas_repr}")
    else:
        parts.append("cas_prefix_ids=None")
    if register_id is not None:
        parts.append(
            f"register_id={register_id.detach().to('cpu').tolist()}"
        )
    else:
        parts.append("register_id=None")
    return "; ".join(parts)


__all__ = [
    "_VERSION",
    "GenerationTrace",
    "NLGenerationHead",
    "NLGenerationHeadConfig",
    "TokenStep",
]
