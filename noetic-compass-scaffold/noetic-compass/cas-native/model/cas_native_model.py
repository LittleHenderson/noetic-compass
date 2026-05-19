"""
CASNativeModel: Full model assembly combining all CAS-Native components
into a complete transformer-based architecture.

Architecture:
  - Token embedding + positional encoding
  - CognitiveStateEmbedding branch (parallel to main pathway)
  - N transformer layers, each with:
    - DomainDescentAttention (replaces standard attention)
    - FractalAttentionHead (additional multi-scale heads)
    - PrerequisiteGateLayer after attention
    - FFN + LayerNorm
  - CognitiveToposReasoner output head
  - LM head (nn.Linear -> vocab_size)

Forward returns dict: logits, cognitive_state, rpm_satisfaction,
inversion_flags, topos_truth_values

CAS-Native v2 forward-path integration (Wave 7B Task 1, ADR-01):
  - Forward accepts an optional per-example per-position register-activation
    tensor shaped ``(batch, 40, 4)`` bool over the 4 Phenomenological
    Registers {T, A, f, E} when ``v2_components["register_embedding"]`` is
    present. For each position, the activation mask selects which of the
    ``register_film`` transforms are applied to that slot of the 40-dim
    pre-simplex logit vector. Multiple active registers at the same position
    are composed by sequential multiplicative application (equivalent to the
    closed-form gamma/beta composition in the ADR-01 docstring).

  - Register-unspecified positions (all-zero row) apply NO modulation —
    identity FiLM. This preserves v7.4 byte-equivalence under the common
    "no register labels" case and is the fallback when register activations
    are not provided at all.
"""

import math
from dataclasses import dataclass
from typing import Any, Optional

import torch
import torch.nn as nn

from .embedding import (
    CognitiveStateEmbedding,
    CognitiveStateEmbeddingWithRegister,
    NUM_COGNITIVE_STATES,
)
from .domain_descent import DomainDescentAttention
from .rpm_gate import PrerequisiteGateLayer
from .fractal_attention import FractalAttentionHead
from .register_film import NUM_REGISTERS
from .topos_reasoner import CognitiveToposReasoner
from .composition import GenerativeHead
from .lacunarity_gate import LacunarityGate
from .lacunarity_head import LacunarityHead


@dataclass
class CASNativeConfig:
    """Configuration for the CAS-Native model."""

    d_model: int = 512
    n_layers: int = 6
    n_heads: int = 8
    vocab_size: int = 32000
    max_seq_len: int = 2048
    fractal_depth: int = 3
    num_ethical_propositions: int = 7
    dropout: float = 0.1
    rpm_threshold: float = 0.5
    num_ifs_maps: int = 4
    causal_lm: bool = False


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding."""

    def __init__(self, d_model: int, max_seq_len: int = 2048, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_seq_len, d_model)
        position = torch.arange(0, max_seq_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_seq_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Add positional encoding to input embeddings."""
        x = x + self.pe[:, : x.size(1), :]
        return self.dropout(x)


class CASTransformerLayer(nn.Module):
    """Single transformer layer with CAS-specific components.

    Each layer contains:
      - DomainDescentAttention (domain-masked attention)
      - FractalAttentionHead (multi-scale fractal attention)
      - PrerequisiteGateLayer (RPM gating)
      - FFN + LayerNorm (standard transformer components)
    """

    def __init__(self, config: CASNativeConfig):
        super().__init__()

        # Domain descent attention (replaces standard self-attention)
        self.domain_attn = DomainDescentAttention(
            d_model=config.d_model,
            n_heads=config.n_heads,
        )
        self.norm1 = nn.LayerNorm(config.d_model)

        # Fractal attention (additional multi-scale heads)
        self.fractal_attn = FractalAttentionHead(
            d_model=config.d_model,
            n_heads=config.n_heads,
            fractal_depth=config.fractal_depth,
            num_ifs_maps=config.num_ifs_maps,
        )
        self.norm2 = nn.LayerNorm(config.d_model)

        # Fractal mixing weight (learnable blend of domain + fractal attention)
        self.fractal_gate = nn.Parameter(torch.tensor(0.5))

        # RPM prerequisite gate
        self.rpm_gate = PrerequisiteGateLayer(
            d_model=config.d_model,
            threshold=config.rpm_threshold,
        )
        self.norm3 = nn.LayerNorm(config.d_model)

        # Feed-forward network
        self.ffn = nn.Sequential(
            nn.Linear(config.d_model, config.d_model * 4),
            nn.GELU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.d_model * 4, config.d_model),
            nn.Dropout(config.dropout),
        )
        self.norm4 = nn.LayerNorm(config.d_model)

    def forward(
        self,
        x: torch.Tensor,
        cognitive_state: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        causal: bool = False,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        """
        Args:
            x: Input tensor (batch, seq, d_model)
            cognitive_state: Token-to-slot weights (batch, seq, 40)
            attention_mask: Optional padding mask (batch, seq)

        Returns:
            Tuple of (output, rpm_satisfaction_dict)
        """
        mask = None
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).to(x.dtype)

        # Domain descent attention + fractal attention (blended)
        domain_out = self.domain_attn(
            self.norm1(x),
            cognitive_state,
            attention_mask=attention_mask,
            causal=causal,
        )
        fractal_out = self.fractal_attn(
            self.norm2(x),
            attention_mask=attention_mask,
            causal=causal,
        )

        gate = torch.sigmoid(self.fractal_gate)
        attn_out = gate * domain_out + (1.0 - gate) * fractal_out
        x = x + attn_out
        if mask is not None:
            x = x * mask

        # RPM prerequisite gate
        gated, rpm_satisfaction = self.rpm_gate(self.norm3(x))
        x = x + gated
        if mask is not None:
            x = x * mask

        # Feed-forward
        x = x + self.ffn(self.norm4(x))
        if mask is not None:
            x = x * mask

        return x, rpm_satisfaction


class InversionDetector(nn.Module):
    """Detects inversions across the 7 CAS inversion axes.

    Axes: N (Operator), W (Domain), F (Drive), E (State),
          S (Sub-Drive), A (Pathway), P (Compound)
    """

    NUM_AXES = 7

    def __init__(self, d_model: int):
        super().__init__()
        self.detector = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Linear(d_model // 2, self.NUM_AXES),
            nn.Sigmoid(),  # Output in [0, 1] per axis
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Pooled representation (batch, d_model)

        Returns:
            Inversion scores (batch, 7) in [0, 1]
        """
        return self.detector(x)


class CASNativeModel(nn.Module):
    """Complete CAS-Native model combining all components.

    Architecture:
      - Token embedding + positional encoding
      - CognitiveStateEmbedding branch (parallel)
      - N CAS transformer layers
      - CognitiveToposReasoner output head
      - LM head
      - Inversion detector
    """

    def __init__(self, config: CASNativeConfig | None = None):
        super().__init__()
        if config is None:
            config = CASNativeConfig()
        self.config = config

        # Token embedding + positional encoding
        self.token_embedding = nn.Embedding(config.vocab_size, config.d_model)
        self.pos_encoding = PositionalEncoding(
            config.d_model, config.max_seq_len, config.dropout
        )

        # Cognitive state embedding branch (parallel to main pathway)
        self.cognitive_embedding = CognitiveStateEmbedding(config.d_model)

        # CAS transformer layers
        self.layers = nn.ModuleList([
            CASTransformerLayer(config)
            for _ in range(config.n_layers)
        ])

        # Final layer norm
        self.final_norm = nn.LayerNorm(config.d_model)

        # Output heads
        self.lm_head = nn.Linear(config.d_model, config.vocab_size, bias=False)
        self.topos_reasoner = CognitiveToposReasoner(
            config.d_model,
            config.num_ethical_propositions,
        )
        self.inversion_detector = InversionDetector(config.d_model)
        self.generative_head = GenerativeHead(config.d_model)
        self.lacunarity_gate = LacunarityGate(num_slots=40)
        self.lacunarity_head = LacunarityHead(config.d_model)

        # Optional native English NL generation head — attached lazily by the
        # trainer / harness via attach_nl_gen_head(). Default None preserves
        # backward-compat with all existing CASNativeModel callers.
        self.nl_gen_head = None  # type: ignore[assignment]
        self.generation_readiness_gate = None  # type: ignore[assignment]
        self.aux_heads = None  # type: ignore[assignment]  # v1e Phase C — attach_aux_heads()

        # Initialize weights
        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize model weights."""
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=0.02)
            elif isinstance(module, nn.LayerNorm):
                nn.init.ones_(module.weight)
                nn.init.zeros_(module.bias)

    @staticmethod
    def _masked_mean(x: torch.Tensor, attention_mask: torch.Tensor | None) -> torch.Tensor:
        """Average across sequence positions while ignoring padding."""
        if attention_mask is None:
            return x.mean(dim=1)

        weights = attention_mask.to(x.dtype).unsqueeze(-1)
        return (x * weights).sum(dim=1) / weights.sum(dim=1).clamp_min(1.0)

    # ---------------------------------------------------------------- v2
    @property
    def expression_proposer_enabled(self) -> bool:
        """True iff an ``ExpressionProposerHead`` is attached (ADR-07).

        Gated by ``V2ComponentFlags.use_expression_proposer`` — the trainer
        attaches this when the flag is True. When False the forward pass
        routes around it (byte-equivalent to the pre-ADR-07 model) and the
        ``proposer_outputs`` key is absent from the forward return dict.
        """
        v2c = getattr(self, "v2_components", None)
        if v2c is None:
            return False
        return "expression_proposer" in v2c

    @property
    def register_film_enabled(self) -> bool:
        """True iff a ``CognitiveStateEmbeddingWithRegister`` is attached.

        Gated by ``v2_components["register_embedding"]`` — the trainer
        attaches this when ``component_flags.use_register_film`` is True.
        When False the forward pass routes through the legacy v7.4 embedding
        and register activations are ignored (byte-equivalent to v7.4).
        """
        v2c = getattr(self, "v2_components", None)
        if v2c is None:
            return False
        return "register_embedding" in v2c

    def _apply_register_film_to_logits(
        self,
        logits: torch.Tensor,
        register_activations: torch.Tensor,
    ) -> torch.Tensor:
        """Apply FiLM sequentially for each register active at each position.

        The multi-register composition rule is the sequential form documented
        in ADR-01 and the embedding.py module docstring:

            apply_film(R_k, ... apply_film(R_2, apply_film(R_1, state)))

        For the affine FiLM ``γ·x + β`` this is equivalent to the closed form

            γ_total = γ_{R_1} ⊙ γ_{R_2} ⊙ ... ⊙ γ_{R_k}
            β_total = γ_{R_k} ⊙ (... (γ_{R_2} ⊙ β_{R_1} + β_{R_2}) ...) + β_{R_k}

        because affine maps compose associatively. Sequential is cleaner to
        implement so we adopt it here. When no registers are active at a
        position the row of ``register_activations`` is all-zero and FiLM
        reduces to the identity (no-op), preserving byte-equivalence.

        Under ADR-08 Option E (shared RegisterLatent), ``gamma`` and
        ``beta`` are computed ONCE from the shared latent here and reused
        across the per-register iteration — avoiding the 4x recompute that
        would follow from reading through the ``_LatentFiLMView.gamma`` /
        ``.beta`` properties inside the loop.

        Args:
            logits: (batch, 40) pre-simplex logits produced by the base
                projection.
            register_activations: (batch, 40, 4) bool tensor — True at
                ``[b, position, r]`` if register ``r`` is active at that
                cognitive-state position for example ``b``.

        Returns:
            Modulated logits of the same shape as ``logits``.
        """
        emb = self.v2_components["register_embedding"]  # type: ignore[index]
        assert isinstance(emb, CognitiveStateEmbeddingWithRegister)
        latent = emb.register_latent
        # Compute gamma/beta once from the shared Option E latent.
        gamma, beta = latent.compute_gamma_beta_40()  # (R, 40)
        num_registers = latent.num_registers

        activations = register_activations.to(dtype=logits.dtype)
        out = logits
        # Sequential multiplicative composition over the registers.
        # At positions where `activations[...,r]` is 0, the per-register
        # transform reduces to identity: (1-0)*1 + 0*gamma_r = 1 and
        # (1-0)*0 + 0*beta_r = 0, giving x -> 1*x + 0 = x.
        for r_idx in range(num_registers):
            mask = activations[..., r_idx]  # (batch, 40)
            # Effective gamma / beta for this register at each position:
            #   gamma_eff = (1 - mask) * 1 + mask * gamma_r
            #   beta_eff  = (1 - mask) * 0 + mask * beta_r
            gamma_r = gamma[r_idx]  # (40,)
            beta_r = beta[r_idx]    # (40,)
            gamma_eff = 1.0 + mask * (gamma_r.unsqueeze(0) - 1.0)
            beta_eff = mask * beta_r.unsqueeze(0)
            out = gamma_eff * out + beta_eff
        return out

    def _normalize_register_activations(
        self,
        x: torch.Tensor,
        register_activations: Optional[torch.Tensor],
    ) -> torch.Tensor:
        """Normalize ``None`` register activations to a zero-activation tensor.

        Decision G (Wave 7B integration review): when
        ``register_film_enabled=True``, the forward pass must take a SINGLE
        code path regardless of whether the caller passed
        ``register_activations=None`` or an explicit zero tensor. Previously
        the ``None`` case routed through ``self.cognitive_embedding``
        (wrapper) and the zero-tensor case routed through ``emb.base``
        (inner base) — two functionally-equivalent branches at init but
        structurally divergent (independently-initialized projection
        weights), a latent bug attractor under mixed-annotation training.

        This helper collapses the divergence: when activations are None we
        synthesize a zero-valued bool tensor of the canonical shape
        ``(batch, 40, 4)`` on the same device as ``x``. All downstream code
        then runs through the unified zero-activation path using
        ``emb.base``, which is the authoritative base projection owned by
        the v2 embedding module.

        Args:
            x: Hidden states (..., d_model). Shape is used only to derive
                the batch dimension when activations must be synthesized.
            register_activations: Optional per-position bool mask shaped
                ``(batch, 40, 4)``. If None, a zero tensor of that shape is
                returned on ``x.device``.

        Returns:
            Bool tensor shaped ``(batch, 40, 4)`` on the same device as
            ``x``. All-False when synthesized from None.
        """
        if register_activations is not None:
            return register_activations

        batch_size = x.shape[0] if x.dim() >= 1 else 1
        return torch.zeros(
            batch_size,
            NUM_COGNITIVE_STATES,
            NUM_REGISTERS,
            dtype=torch.bool,
            device=x.device,
        )

    def _compute_cognitive_state(
        self,
        x: torch.Tensor,
        register_activations: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Project hidden states to the 40-state open simplex with optional
        per-position register FiLM modulation.

        Backward compatibility invariant: when register FiLM is disabled
        entirely (``register_film_enabled=False``), this method reduces to
        ``self.cognitive_embedding(x)`` exactly — the v7.4 byte-equivalent
        path with zero register machinery engaged. This preserves the
        legacy-model guarantee tested by
        ``test_v74_byte_equivalent_when_flags_off`` and the
        register-disabled branch of
        ``test_register_neutral_matches_base_embedding_exactly``.

        When register FiLM IS enabled, a SINGLE unified code path runs
        regardless of whether ``register_activations`` is None or an
        explicit zero tensor (Decision G, Wave 7B integration review). None
        is normalized to a zero-activation tensor at the function boundary
        via ``_normalize_register_activations``, and both cases route
        through the v2 embedding's own base projection (``emb.base``) with
        FiLM applied. At init (gamma=1, beta=0) FiLM is the identity, so
        the zero-activation path is byte-equivalent to the v2 embedding's
        register-neutral forward — this is the ADR-01 byte-equivalence
        invariant guarded by
        ``test_register_neutral_matches_base_embedding_exactly``. The
        unification eliminates the former latent-bug attractor where None
        routed through ``self.cognitive_embedding`` (wrapper) and
        zero-tensor routed through ``emb.base`` (inner base) with
        independently-initialized weights.

        Args:
            x: Hidden states (..., d_model). The 40-state simplex is over
                the final axis of the output.
            register_activations: Optional per-position bool mask shaped
                ``(batch, 40, 4)`` over {T, A, f, E}. Applied only when the
                register embedding module is attached (v2 flag on). When
                None and FiLM is enabled, a zero-activation tensor is
                synthesized (identity FiLM path).

        Returns:
            Tensor on the 40-state open simplex with trailing dim 40.
        """
        # Flag-OFF path: complete bypass of register machinery (v7.4 path).
        if not self.register_film_enabled:
            return self.cognitive_embedding(x)

        # Flag-ON path: unify None and zero-activation cases via
        # normalization at the function boundary. From here on, a single
        # code path handles both.
        register_activations = self._normalize_register_activations(
            x, register_activations
        )

        emb = self.v2_components["register_embedding"]  # type: ignore[index]
        assert isinstance(emb, CognitiveStateEmbeddingWithRegister)

        # Project to 40-dim logits via the v2 embedding's own base. This is
        # the authoritative projection under the flag-ON path — NOT
        # `self.cognitive_embedding.projection`, which is a different
        # module with independently-initialized weights.
        logits = emb.base.projection(x)  # (..., 40)

        # Broadcast per-position activations across the sequence axis. The
        # activations have shape (batch, 40, 4); logits have shape
        # (batch, seq, 40). Apply the same activation mask for every
        # position in the sequence — the 40 "positions" here index the
        # cognitive-state slots, NOT sequence positions.
        if logits.dim() == 3:
            b, s, n_states = logits.shape
            # Flatten (batch, seq, 40) -> (batch*seq, 40) and broadcast
            # activations across the sequence.
            act_broadcast = register_activations.unsqueeze(1).expand(b, s, n_states, NUM_REGISTERS)
            flat_logits = logits.reshape(b * s, n_states)
            flat_acts = act_broadcast.reshape(b * s, n_states, NUM_REGISTERS)
            modulated = self._apply_register_film_to_logits(flat_logits, flat_acts)
            modulated = modulated.reshape(b, s, n_states)
        else:
            modulated = self._apply_register_film_to_logits(logits, register_activations)

        return emb.base._project_to_open_simplex(modulated)

    # ---------------------------------------------------------------- fwd

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor | None = None,
        register_activations: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        """
        Args:
            input_ids: Token IDs of shape (batch, seq)
            attention_mask: Optional mask of shape (batch, seq)
            register_activations: Optional ``(batch, 40, 4)`` bool tensor
                marking which Phenomenological Registers are active at each
                of the 40 cognitive-state positions per example. Consumed
                only when ``self.register_film_enabled`` is True (v2 ADR-01
                path). When None or when register-FiLM is off, the forward
                pass is byte-equivalent to v7.4.

        Returns:
            Dict with keys:
              - logits: LM logits (batch, seq, vocab_size)
              - hidden_states: Final hidden states (batch, seq, d_model)
              - pooled_hidden_state: Masked-mean pooled hidden state
                (batch, d_model)
              - cognitive_state: Cognitive state on simplex (batch, seq, 40)
              - rpm_satisfaction: Mean RPM satisfaction scalar
              - inversion_flags: Inversion scores (batch, 7)
              - topos_truth_values: Truth values (batch, num_propositions, 3)
        """
        # Token embedding + positional encoding
        x = self.token_embedding(input_ids)
        x = self.pos_encoding(x)

        # Apply attention mask if provided (zero out padded positions)
        if attention_mask is not None:
            x = x * attention_mask.unsqueeze(-1).float()

        # CAS transformer layers
        all_rpm_satisfaction: list[dict[str, torch.Tensor]] = []
        for layer in self.layers:
            layer_cognitive_state = self._compute_cognitive_state(
                x, register_activations=register_activations
            )
            x, rpm_sat = layer(
                x,
                layer_cognitive_state,
                attention_mask=attention_mask,
                causal=self.config.causal_lm,
            )
            all_rpm_satisfaction.append(rpm_sat)

        # Final normalization
        x = self.final_norm(x)
        if attention_mask is not None:
            x = x * attention_mask.unsqueeze(-1).float()

        # LM head
        logits = self.lm_head(x)

        # Recompute cognitive state from final hidden states
        cognitive_state = self._compute_cognitive_state(
            x, register_activations=register_activations
        )

        # Lacunarity self-correction: if activation is too concentrated, rebalance
        corrected_state, lacunarity_scores = self.lacunarity_gate(cognitive_state)

        # Pooled representation for global heads
        pooled = self._masked_mean(x, attention_mask)  # (batch, d_model)

        # Topos reasoning (intuitionistic 3-valued logic)
        topos_truth_values = self.topos_reasoner(pooled)

        # Inversion detection
        inversion_flags = self.inversion_detector(pooled)

        # Metacognitive lacunarity reporting
        lacunarity_meta = self.lacunarity_head(x)

        # Aggregate RPM satisfaction across layers
        mean_rpm = torch.tensor(0.0, device=input_ids.device)
        count = 0
        for rpm_dict in all_rpm_satisfaction:
            for name, sat in rpm_dict.items():
                mean_rpm = mean_rpm + sat.mean()
                count += 1
        if count > 0:
            mean_rpm = mean_rpm / count

        output = {
            "logits": logits,
            "hidden_states": x,
            "pooled_hidden_state": pooled,
            "cognitive_state": corrected_state,
            "raw_cognitive_state": cognitive_state,
            "rpm_satisfaction": mean_rpm,
            "inversion_flags": inversion_flags,
            "topos_truth_values": topos_truth_values,
            "lacunarity_scores": lacunarity_scores,
            "lacunarity_meta": lacunarity_meta,
        }

        # ADR-07 — learned ExpressionProposerHead. Only runs when the
        # proposer is attached (i.e. ``V2ComponentFlags.use_expression_proposer``
        # is True). The proposer consumes the pre-final-norm d_model
        # hidden states ``x`` (same tensor feeding ``lm_head`` and
        # ``topos_reasoner``), so its gradients flow through every
        # upstream transformer layer. When disabled, the key is absent
        # from the dict — preserving byte-equivalence with the pre-ADR-07
        # forward-path contract.
        if self.expression_proposer_enabled:
            proposer = self.v2_components["expression_proposer"]  # type: ignore[index]
            output["proposer_outputs"] = proposer(x, mode="training")

        return output

    # ------------------------------------------------------------------ NL gen
    def attach_nl_gen_head(self, head: nn.Module) -> None:
        """Attach a native :class:`NLGenerationHead` to this model.

        Kept as a setter rather than a constructor argument so the existing
        ``CASNativeModel.__init__`` signature stays backward-compatible. The
        trainer instantiates the head against the tokenizer agent's vocab
        size, then attaches it here.
        """
        self.nl_gen_head = head

    # ------------------------------------------------------------------ aux heads
    def attach_aux_heads(self, aux_heads: nn.Module) -> None:
        """Attach v1e Phase C auxiliary supervision heads to this model.

        The ``aux_heads`` module owns the four sub-heads (H_card, H_pos,
        H_stop, H_cluster) per
        ``docs/working/v1e_phase_c_aux_heads_design_2026_05_11.md``. Kept as
        a setter so callers that don't need aux supervision (production
        v0 inference, eval, canary) don't pay the param-count cost.

        After attachment, ``forward_with_aux()`` becomes available. Default
        ``forward()`` and ``forward_with_lm()`` are unchanged — aux heads
        only fire when explicitly invoked.
        """
        self.aux_heads = aux_heads

    # ---------------------------------------------------- generation readiness
    def attach_generation_readiness_gate(self, gate: nn.Module) -> None:
        """Attach a diagnostic generation-readiness gate.

        The gate is deliberately not called from ``forward`` or
        ``forward_with_lm``. It consumes already-produced CAS diagnostics and
        returns an auditable policy such as allow/caveat/constrain/suppress.
        This keeps Stage 20 valve behavior opt-in and prevents silent
        bottleneck or logit mutation.
        """
        self.generation_readiness_gate = gate

    def assess_generation_readiness(
        self,
        outputs: dict[str, Any],
        *,
        verification: dict[str, Any] | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        """Assess generation readiness from an existing forward output dict.

        Args:
            outputs: Dict returned by ``forward`` or ``forward_with_lm``.
            verification: Optional Verification Stack per-example decision.
            mode: Optional mode override, e.g. ``BALANCED``.

        Returns:
            JSON-serializable readiness policy.

        Raises:
            RuntimeError: If no readiness gate was attached first.
        """
        gate = getattr(self, "generation_readiness_gate", None)
        if gate is None:
            raise RuntimeError(
                "assess_generation_readiness called but no generation "
                "readiness gate is attached. Use "
                "attach_generation_readiness_gate() first."
            )

        result = gate(
            lacunarity_scores=outputs.get("lacunarity_scores"),
            lacunarity_meta=outputs.get("lacunarity_meta"),
            inversion_flags=outputs.get("inversion_flags"),
            rpm_satisfaction=outputs.get("rpm_satisfaction"),
            verification=verification,
            mode=mode,
        )
        if hasattr(result, "as_dict"):
            return result.as_dict()
        return result

    def forward_with_aux(
        self,
        input_ids: torch.Tensor,
        lm_decoder_input_ids: torch.Tensor,
        *,
        attention_mask: torch.Tensor | None = None,
        register_activations: Optional[torch.Tensor] = None,
        cas_prefix_ids: Optional[torch.Tensor] = None,
        cas_prefix_mask: Optional[torch.Tensor] = None,
        register_id: Optional[torch.Tensor] = None,
        bottleneck_z: Optional[torch.Tensor] = None,
    ) -> dict[str, torch.Tensor]:
        """Run the existing forward, the NL gen head, AND the four aux heads.

        Returns a superset of ``forward_with_lm()``'s output dict, adding:

          ``card_logits``    : ``(B, K_max + 1)`` — H_card cardinality
          ``pos_logits``     : ``(B, K_max, num_noetics)`` — H_pos per-position
          ``stop_logits``    : ``(B, L_dec, 2)`` — H_stop per-decoder-position
          ``cluster_logits`` : ``(B, C_max, num_noetics)`` — H_cluster

        The trainer uses these alongside ``lm_logits`` to compute the
        v1e Phase C multi-task loss
        (``L_total = β_lm·L_LM + α_card·L_card + α_pos·L_pos +
          α_stop·L_stop + α_cluster·L_cluster``).

        Raises:
            RuntimeError if either ``attach_nl_gen_head`` or
            ``attach_aux_heads`` was not called first.
        """
        if self.nl_gen_head is None:
            raise RuntimeError(
                "forward_with_aux called but no nl_gen_head is attached. "
                "Use attach_nl_gen_head() first."
            )
        aux = getattr(self, "aux_heads", None)
        if aux is None:
            raise RuntimeError(
                "forward_with_aux called but no aux_heads attached. "
                "Use attach_aux_heads() first."
            )

        # Run forward_with_lm in return_meta mode so we get the pre-LM-head
        # decoder hidden state for H_stop. The encoder pool comes from the
        # forward()'s "pooled_hidden_state" key (already in outputs).
        outputs = self.forward_with_lm(
            input_ids,
            lm_decoder_input_ids,
            attention_mask=attention_mask,
            register_activations=register_activations,
            cas_prefix_ids=cas_prefix_ids,
            cas_prefix_mask=cas_prefix_mask,
            register_id=register_id,
            bottleneck_z=bottleneck_z,
            return_lm_meta=True,
        )

        pooled = outputs["pooled_hidden_state"]  # (B, d_model)
        decoder_hidden = outputs["lm_meta"]["decoder_hidden_state"]  # (B, L, d_model)

        aux_out = aux(pooled=pooled, decoder_hidden=decoder_hidden)
        outputs["card_logits"] = aux_out["card_logits"]
        outputs["pos_logits"] = aux_out["pos_logits"]
        outputs["stop_logits"] = aux_out["stop_logits"]
        outputs["cluster_logits"] = aux_out["cluster_logits"]

        return outputs

    def forward_with_lm(
        self,
        input_ids: torch.Tensor,
        lm_decoder_input_ids: torch.Tensor,
        *,
        attention_mask: torch.Tensor | None = None,
        register_activations: Optional[torch.Tensor] = None,
        cas_prefix_ids: Optional[torch.Tensor] = None,
        cas_prefix_mask: Optional[torch.Tensor] = None,
        register_id: Optional[torch.Tensor] = None,
        bottleneck_z: Optional[torch.Tensor] = None,
        return_lm_meta: bool = False,
    ) -> dict[str, torch.Tensor]:
        """Run the existing forward and the attached NL generation head.

        The structured forward is unchanged — we just additionally route the
        pooled hidden state (projected to the head's bottleneck dim if
        needed) into the NL head together with the encoder stream and the
        optional CAS prefix.

        Args:
            input_ids: Encoder token IDs ``(B, S)``.
            lm_decoder_input_ids: Decoder token IDs ``(B, L)``.
            attention_mask: Optional encoder padding mask.
            register_activations: Optional ``(B, 40, 4)`` register mask for
                the structured forward (unchanged contract).
            cas_prefix_ids: Optional ``(B, K)`` CAS-expression prefix.
            cas_prefix_mask: Optional ``(B, K)`` bool tensor; True = real,
                False = PAD. Forwarded to the NL head so PAD positions in
                the cas_prefix do not leak into self-attention.
            register_id: Optional ``(B,)`` register IDs for the NL head's
                FiLM modulation.
            bottleneck_z: Optional ``(B, bottleneck_dim)`` to override the
                pooled-hidden-state-derived bottleneck. Default behavior:
                use a sliced/projected version of pooled_hidden_state.
            return_lm_meta: When True, request metadata from the NL head.

        Returns:
            Dict containing all keys from :meth:`forward` plus
            ``lm_logits`` (and optionally ``lm_meta``).
        """
        if self.nl_gen_head is None:
            raise RuntimeError(
                "forward_with_lm called but no nl_gen_head is attached. "
                "Use attach_nl_gen_head() first."
            )

        outputs = self.forward(
            input_ids,
            attention_mask=attention_mask,
            register_activations=register_activations,
        )

        head_config = self.nl_gen_head.config  # type: ignore[union-attr]
        bottleneck_dim = head_config.bottleneck_dim

        if bottleneck_z is None:
            pooled = outputs["pooled_hidden_state"]  # (B, d_model)
            if pooled.shape[-1] >= bottleneck_dim:
                bottleneck_z = pooled[..., :bottleneck_dim].contiguous()
            else:
                # Pad with zeros if d_model < bottleneck_dim (rare).
                pad = torch.zeros(
                    pooled.shape[0],
                    bottleneck_dim - pooled.shape[-1],
                    device=pooled.device,
                    dtype=pooled.dtype,
                )
                bottleneck_z = torch.cat([pooled, pad], dim=-1)

        encoder_outputs = outputs["hidden_states"]  # (B, S, d_model)

        if return_lm_meta:
            lm_logits, lm_meta = self.nl_gen_head(
                lm_decoder_input_ids,
                bottleneck_z,
                cas_prefix_ids=cas_prefix_ids,
                cas_prefix_mask=cas_prefix_mask,
                encoder_outputs=encoder_outputs,
                domain_mask=attention_mask,
                register_id=register_id,
                return_meta=True,
            )
            outputs["lm_logits"] = lm_logits
            outputs["lm_meta"] = lm_meta
        else:
            lm_logits = self.nl_gen_head(
                lm_decoder_input_ids,
                bottleneck_z,
                cas_prefix_ids=cas_prefix_ids,
                cas_prefix_mask=cas_prefix_mask,
                encoder_outputs=encoder_outputs,
                domain_mask=attention_mask,
                register_id=register_id,
                return_meta=False,
            )
            outputs["lm_logits"] = lm_logits

        return outputs
