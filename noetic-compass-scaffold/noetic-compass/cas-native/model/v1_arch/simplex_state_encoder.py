"""SimplexStateEncoder — Path C-1 prototype.

Maps a token sequence into a CAS Δ°₃₉ open-simplex trajectory using
mirror-descent style multiplicative updates. NO transformer self-
attention on the encoder side.

Update rule (Path C §4.1):

    p_{t+1} = normalize_eps(p_t * exp(eta * g(x_t, p_t)))

where:
    - ``x_t`` is a token embedding,
    - ``p_t`` is the current 40-state distribution,
    - ``g(x_t, p_t)`` is a small MLP producing a 40-dim logit
      perturbation,
    - ``eta`` is a learned (or scheduled) update size,
    - ``normalize_eps`` enforces every coordinate ≥ ``simplex_floor``
      then renormalizes (CAS Correction 4 — open probability simplex
      ``S°_I = Δ°₃₉ = { p ∈ R^40 : p_k > 0, Σp_k = 1 }``).

Initialization is the uniform 1/40 distribution. The update is purely
recurrent in ``p_t``; there is no attention across tokens. Memory of
prior tokens passes through ``p_t`` itself (the simplex is the
memory) plus an optional small dialogue memory hook left as a
no-op slot for C-2/C-3 to fill.

The encoder optionally returns the per-step trace ``p_state_trace``
shaped ``(batch, seq_len, 40)`` for Mode 7 traceability — the same
trace surface a future explainer reads to walk the user from
``input -> CAS state evolution -> reply``.

Architectural rationale and constraints
---------------------------------------

- 40 atoms = 10 Noetics × 4 Domains, the patent-named primitive
  (USPTO #64/037,173). The cross-product is the unit; do NOT split
  into independent Noetic Δ°9 + Domain Δ°3 (Path C §3.1.1).
- Cognitive State is the **base manifold** in the typed-product
  decomposition; Drive (intensity vector) and Register (Bernoulli
  gates) are typed fibers that DO NOT use a simplex. C-1 ships only
  the base manifold; the encoder exposes hooks (`drive_head_input`,
  `register_head_input`) that C-2/C-3 will wire heads into.
- NO foreign pretrained models / weights anywhere
  (``feedback_no_foreign_architecture_cas_only``). Token embedding
  and the per-step update MLP are randomly-initialized from scratch.

Trace surface
-------------

For every encoded sequence the encoder records:
    p_state_init  : (batch, 40)      - the uniform start
    p_state_trace : (batch, seq, 40) - per-step distribution
    p_state_final : (batch, 40)      - last step's distribution

Each row of ``p_state_trace`` is a strictly-positive simplex vector
(every component > ``SIMPLEX_FLOOR``, sum == 1.0 within float
tolerance). This is the load-bearing object for Mode 7 (Network
Attribution / Mechanistic Trace) — every output the model produces
must walk back to its origin via this trajectory.

NO TRAINING IS RUN HERE. C-1 is code + tests only. The 5-10pp
falsification gate is measured later, after Path D corpus lands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Constants — kept local to avoid import-cycle risk against the existing
# ``cas_native.model.embedding`` module (which is consumed elsewhere).
# ---------------------------------------------------------------------------

#: Number of CAS Cognitive States — 10 Noetics × 4 Domains. Patent primitive.
NUM_COGNITIVE_STATES: int = 40

#: Open-simplex floor. Every coordinate of every emitted distribution is
#: clipped at this value before renormalization, guaranteeing
#: ``p_k > 0`` per CAS Correction 4. Chosen small enough to leave the
#: distribution near-discrete when one atom dominates, but large enough
#: that gradients near the boundary remain finite.
SIMPLEX_FLOOR: float = 1e-6


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class SimplexStateEncoderConfig:
    """Configuration for :class:`SimplexStateEncoder`.

    Attributes
    ----------
    vocab_size:
        Size of the token vocabulary. Must match the tokenizer used at
        train/inference time. Loaded from
        ``cas_hybrid_tokenizer_v2_2026_05_07.json`` for full runs.
    d_model:
        Token embedding dimension.
    num_states:
        Number of Cognitive State atoms. MUST be 40 in C-1; the parameter
        exists only to keep the smoke-test signature flexible.
    update_hidden:
        Hidden width of the per-token MLP that produces the 40-dim logit
        perturbation ``g(x_t, p_t)``.
    eta_init:
        Initial value for the learnable update-size scalar. Mirror-descent
        is sensitive to step size; we initialize small and let the
        optimizer grow it.
    eta_learnable:
        When True, ``eta`` is a learnable scalar parameter. When False,
        it is a fixed buffer (useful for fixture / smoke tests).
    simplex_floor:
        Lower clip applied to every coordinate before renormalization.
        Smaller values make the simplex closer to closed but expose the
        update to numerical issues; larger values blunt the distribution.
    return_trace:
        When True, the forward pass returns the per-step
        ``p_state_trace`` of shape ``(batch, seq_len, 40)``. Default True
        because Mode 7 requires it; flag exists for memory-constrained
        eval paths.
    use_pos_bias:
        When True, a small learnable additive bias is folded into the
        update logits as a function of token position. Default True.
        Adds a few hundred parameters; cheap.
    pad_token_id:
        Token id whose update is suppressed. The encoder still steps
        through padded positions (so trace shape is uniform across the
        batch) but the multiplicative update reduces to identity at
        those positions. Default 0 — matches HybridCASTokenizer.PAD_ID.
    """

    vocab_size: int = 1024
    d_model: int = 64
    num_states: int = NUM_COGNITIVE_STATES
    update_hidden: int = 128
    eta_init: float = 0.5
    eta_learnable: bool = True
    simplex_floor: float = SIMPLEX_FLOOR
    return_trace: bool = True
    use_pos_bias: bool = True
    pad_token_id: int = 0
    max_seq_len: int = 512


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------


class SimplexStateEncoder(nn.Module):
    """Token sequence → Δ°₃₉ open-simplex trajectory (no self-attention).

    Forward signature::

        out = encoder(input_ids, attention_mask=None)

        out["p_state_init"]  : (batch, 40)        — uniform 1/40 start
        out["p_state_trace"] : (batch, seq, 40)   — per-step trace (if
                                                      ``return_trace``)
        out["p_state_final"] : (batch, 40)        — last step's
                                                      distribution
    """

    def __init__(self, config: Optional[SimplexStateEncoderConfig] = None) -> None:
        super().__init__()
        if config is None:
            config = SimplexStateEncoderConfig()
        if config.num_states != NUM_COGNITIVE_STATES:
            # Path C §3.1.1: 40 atoms is the patent primitive. Refuse
            # silent split — caller must either keep 40 or write a
            # different module.
            raise ValueError(
                f"SimplexStateEncoder requires num_states={NUM_COGNITIVE_STATES}; "
                f"got {config.num_states}. Per Path C §3.1.1 the cross-product "
                "(Noetic × Domain) is the unit and must not be split."
            )
        self.config = config

        # ------------------------------------------------------------------
        # Token-side parameters
        # ------------------------------------------------------------------
        # Random-init from scratch — no foreign pretrained weights.
        # ``padding_idx=pad_token_id`` makes the pad embedding a frozen
        # zero vector so the update at pad positions reduces to identity
        # before the multiplicative mask we apply below.
        self.token_embedding = nn.Embedding(
            num_embeddings=config.vocab_size,
            embedding_dim=config.d_model,
            padding_idx=config.pad_token_id,
        )
        # Standard small init for the embedding.
        nn.init.normal_(self.token_embedding.weight, mean=0.0, std=0.02)
        # Re-zero pad row after the random init.
        with torch.no_grad():
            self.token_embedding.weight[config.pad_token_id].zero_()

        if config.use_pos_bias:
            # Per-position scalar bias (NOT a per-position 40-dim
            # perturbation — that would explode parameter count without
            # much benefit at this prototype stage).
            self.pos_bias = nn.Parameter(
                torch.zeros(config.max_seq_len, config.num_states)
            )
        else:
            self.register_parameter("pos_bias", None)

        # ------------------------------------------------------------------
        # Per-step update network ``g(x_t, p_t)``
        # ------------------------------------------------------------------
        # Concatenates the token embedding (d_model) with the current
        # simplex distribution (num_states) and projects through a small
        # MLP to a 40-dim logit perturbation. Two-layer GELU MLP.
        update_in = config.d_model + config.num_states
        self.update_net = nn.Sequential(
            nn.Linear(update_in, config.update_hidden),
            nn.GELU(),
            nn.Linear(config.update_hidden, config.num_states),
        )

        # Learnable (or fixed) step size η.
        eta_tensor = torch.tensor(float(config.eta_init), dtype=torch.float32)
        if config.eta_learnable:
            self.eta = nn.Parameter(eta_tensor)
        else:
            self.register_buffer("eta", eta_tensor)

        # ------------------------------------------------------------------
        # Optional hooks reserved for later phases — exposed but unused.
        # C-2 will plug a Drive intensity head into ``drive_head_input``,
        # C-3 will plug Register Bernoulli gates into
        # ``register_head_input``. C-1 leaves these as no-ops so the
        # interface is locked early.
        # ------------------------------------------------------------------
        self.drive_head_input: Optional[nn.Module] = None
        self.register_head_input: Optional[nn.Module] = None

        self._reset_update_net()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _reset_update_net(self) -> None:
        """Initialize the update MLP with small weights so the encoder
        starts close to the uniform-prior identity update.

        At init we want the perturbation network's logits to be near
        zero, so the multiplicative update ``exp(eta * g(...))`` is
        near 1.0 for every coordinate, leaving ``p_t`` close to the
        uniform start. The optimizer grows the perturbation as it learns
        which token shifts mass where.
        """
        for module in self.update_net.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight, gain=0.1)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    # ------------------------------------------------------------------
    # Open-simplex projection
    # ------------------------------------------------------------------

    def project_to_open_simplex(self, p: torch.Tensor) -> torch.Tensor:
        """Clip every coordinate to ``[simplex_floor, 1 - simplex_floor]``
        then renormalize.

        Guarantees:
            - all entries strictly positive (``p_k > simplex_floor / S``
              where S is the post-clip mass)
            - sum equals 1.0 within float tolerance

        This is the per-step ``normalize_eps`` from Path C §4.1.
        """
        floor = self.config.simplex_floor
        # Lower clip — strict positivity (CAS Correction 4).
        p = torch.clamp(p, min=floor, max=1.0 - floor)
        # Renormalize.
        p = p / p.sum(dim=-1, keepdim=True)
        return p

    def uniform_init(
        self,
        batch_size: int,
        *,
        device: torch.device,
        dtype: torch.dtype,
    ) -> torch.Tensor:
        """Return the uniform 1/40 starting distribution."""
        p = torch.full(
            (batch_size, self.config.num_states),
            1.0 / float(self.config.num_states),
            device=device,
            dtype=dtype,
        )
        return p

    # ------------------------------------------------------------------
    # Forward
    # ------------------------------------------------------------------

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        *,
        return_trace: Optional[bool] = None,
    ) -> dict[str, torch.Tensor]:
        """Encode ``input_ids`` into a CAS Δ°₃₉ trajectory.

        Args:
            input_ids: ``(batch, seq_len)`` long tensor of token ids.
            attention_mask: Optional ``(batch, seq_len)`` mask. ``1``
                for real tokens, ``0`` for padding. When provided, the
                multiplicative update at masked positions is replaced by
                identity (the simplex distribution is unchanged).
                When ``None``, all positions update.
            return_trace: Override ``config.return_trace``. When True
                the per-step ``p_state_trace`` is materialized; when
                False only the final ``p_state_final`` is returned.

        Returns:
            Dict with keys
                - ``p_state_init``  : ``(batch, 40)``
                - ``p_state_trace`` : ``(batch, seq_len, 40)`` if
                                       ``return_trace`` else absent
                - ``p_state_final`` : ``(batch, 40)``
                - ``hidden``        : ``(batch, seq_len, d_model)``
                                       token embeddings (load-bearing
                                       for Mode 7 trace).
        """
        if input_ids.dim() != 2:
            raise ValueError(
                f"input_ids must be (batch, seq_len); got shape {tuple(input_ids.shape)}."
            )
        if return_trace is None:
            return_trace = self.config.return_trace

        batch_size, seq_len = input_ids.shape
        device = input_ids.device
        dtype = self.token_embedding.weight.dtype

        # 1) Token embeddings.
        hidden = self.token_embedding(input_ids)  # (B, S, d_model)

        # 2) Per-position bias (optional). The bias is a 40-dim additive
        # perturbation indexed by position; we slice up to seq_len.
        if self.pos_bias is not None:
            if seq_len > self.pos_bias.shape[0]:
                raise ValueError(
                    f"seq_len={seq_len} exceeds configured max_seq_len="
                    f"{self.pos_bias.shape[0]}; rebuild the encoder with a "
                    "larger max_seq_len."
                )
            pos_bias = self.pos_bias[:seq_len].to(dtype=dtype, device=device)
        else:
            pos_bias = None

        # 3) Build the active mask. Float; 1.0 where the position is a
        # real token, 0.0 where padded. We DO NOT skip padded positions
        # — we step through them but the update reduces to identity by
        # multiplying the logit perturbation by zero.
        if attention_mask is None:
            active = torch.ones(batch_size, seq_len, device=device, dtype=dtype)
        else:
            active = attention_mask.to(dtype=dtype, device=device)

        # 4) Initialize p at the uniform 1/40 distribution.
        p = self.uniform_init(batch_size, device=device, dtype=dtype)
        p_state_init = p.clone()

        if return_trace:
            trace_buf = torch.empty(
                batch_size,
                seq_len,
                self.config.num_states,
                device=device,
                dtype=dtype,
            )

        # 5) Mirror-descent multiplicative loop.
        eta = self.eta.to(dtype=dtype)
        for t in range(seq_len):
            x_t = hidden[:, t, :]                      # (B, d_model)
            update_in = torch.cat([x_t, p], dim=-1)    # (B, d_model+40)
            g_t = self.update_net(update_in)           # (B, 40) — logit perturbation

            if pos_bias is not None:
                g_t = g_t + pos_bias[t].unsqueeze(0)   # broadcast over batch

            # Active mask gates the update: zero out perturbation at
            # padded positions so exp(0) = 1 -> identity update.
            mask_t = active[:, t].unsqueeze(-1)        # (B, 1)
            g_t = g_t * mask_t

            # Multiplicative update: p_{t+1} = normalize_eps(p * exp(eta * g)).
            # We work in log-space to avoid exp overflow on large
            # perturbations.
            log_p = torch.log(p)
            log_p_next = log_p + eta * g_t
            # Subtract max for numerical stability before exp.
            log_p_next = log_p_next - log_p_next.max(dim=-1, keepdim=True).values
            p = torch.exp(log_p_next)
            p = self.project_to_open_simplex(p)

            if return_trace:
                trace_buf[:, t, :] = p

        out: dict[str, torch.Tensor] = {
            "p_state_init": p_state_init,
            "p_state_final": p,
            "hidden": hidden,
        }
        if return_trace:
            out["p_state_trace"] = trace_buf
        return out

    # ------------------------------------------------------------------
    # Convenience: validate that a tensor is on the open simplex.
    # ------------------------------------------------------------------

    @staticmethod
    def is_on_open_simplex(
        p: torch.Tensor,
        *,
        sum_tol: float = 1e-4,
        positivity_eps: float = 0.0,
    ) -> bool:
        """True iff every entry > ``positivity_eps`` and rows sum to 1.

        Used by the C-1 test suite. ``positivity_eps=0.0`` checks strict
        positivity; pass a tighter floor when the test wants to assert
        the encoder's own ``simplex_floor`` is respected.
        """
        if (p <= positivity_eps).any():
            return False
        sums = p.sum(dim=-1)
        return bool(torch.all(torch.abs(sums - 1.0) < sum_tol).item())


__all__ = [
    "SimplexStateEncoder",
    "SimplexStateEncoderConfig",
    "NUM_COGNITIVE_STATES",
    "SIMPLEX_FLOOR",
]
