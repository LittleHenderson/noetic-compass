"""
CognitiveStateEmbedding: Projects token embeddings onto the 40-dimensional
open probability simplex.

The target space is S_I = Delta_39 = { p in R^40 : pk > 0 for all k, sum(pk) = 1 }
(CORRECTION 4: open probability simplex, NOT discrete 40-element set).

The 40 dimensions correspond to the 10 Cognitive Operators x 4 Processing Domains:
  P0-P9 (Principled), C0-C9 (Cognitive), E0-E9 (Evaluative), O0-O9 (Operational)

CognitiveStateEmbeddingWithRegister augments the base projection with
Phenomenological Register (CAS v7.5) integration. Under ADR-08 Option E, a
single shared :class:`RegisterLatent` module parameterizes BOTH the 40-dim
simplex FiLM surface and the d_model hidden-state FiLM surface via learned
output heads on a per-register latent vector ``z_R``. See
``docs/architecture/cas_native_v2_adrs.md`` ADR-08 for the design decision.

For backward compatibility with call sites that read ``gamma``/``beta``
tensors directly off the former ``RegisterFiLM`` attribute (e.g. the
forward-path sequential FiLM composition in ``cas_native_model.py``), thin
view objects ``register_film`` and ``register_film_dmodel`` are exposed as
properties. They read their gamma/beta tensors by calling the latent
module's ``compute_gamma_beta_*`` methods each access — always in sync
with the shared latent.
"""

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from .register_film import (
    DEFAULT_LATENT_DIM_R,
    DEFAULT_SCALE_40,
    DEFAULT_SCALE_D,
    DEFAULT_SCALE_WARMUP_STEPS,
    NUM_REGISTERS,
    RegisterLatent,
)


# Number of cognitive states: 10 operators x 4 domains
NUM_COGNITIVE_STATES = 40

# Epsilon floor to ensure strict positivity on the open simplex
SIMPLEX_EPS = 1e-8


class CognitiveStateEmbedding(nn.Module):
    """Projects token embeddings onto the 40-dimensional open probability simplex.

    Input:  (batch, seq, d_model) token embeddings
    Output: (batch, seq, 40) vectors on the open simplex (all entries > 0, sum = 1)
    """

    def __init__(self, d_model: int, num_states: int = NUM_COGNITIVE_STATES, eps: float = SIMPLEX_EPS):
        super().__init__()
        self.d_model = d_model
        self.num_states = num_states
        self.eps = eps

        # Two-layer projection: d_model -> hidden -> num_states
        self.projection = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Linear(d_model // 2, num_states),
        )

    def _project_to_open_simplex(self, logits: torch.Tensor) -> torch.Tensor:
        """Project logits onto the open probability simplex.

        Uses softmax + epsilon floor + renormalization to guarantee:
          - All entries strictly positive (pk > eps > 0)
          - Sum of entries = 1.0
        """
        # Softmax gives us the closed simplex (entries >= 0, sum = 1)
        probs = F.softmax(logits, dim=-1)

        # Epsilon floor: ensure all entries are strictly positive
        probs = probs + self.eps

        # Renormalize so they sum to exactly 1.0
        probs = probs / probs.sum(dim=-1, keepdim=True)

        return probs

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Token embeddings of shape (batch, seq, d_model)

        Returns:
            Cognitive state vectors of shape (batch, seq, 40) on the open simplex
        """
        logits = self.projection(x)
        return self._project_to_open_simplex(logits)

    @staticmethod
    def validate(tensor: torch.Tensor, tol: float = 1e-5) -> bool:
        """Validate that a tensor lies on the open probability simplex.

        Checks:
          1. All entries are strictly positive (> 0)
          2. Last dimension sums to 1.0 within tolerance

        Args:
            tensor: Tensor to validate, last dim should be size 40
            tol: Tolerance for sum-to-one check

        Returns:
            True if valid, False otherwise

        Raises:
            ValueError: If tensor has wrong last dimension
        """
        if tensor.shape[-1] != NUM_COGNITIVE_STATES:
            raise ValueError(
                f"Expected last dimension {NUM_COGNITIVE_STATES}, got {tensor.shape[-1]}"
            )

        # Check strict positivity
        if not (tensor > 0).all():
            return False

        # Check sum-to-one constraint
        sums = tensor.sum(dim=-1)
        if not torch.allclose(sums, torch.ones_like(sums), atol=tol):
            return False

        return True


# ---------------------------------------------------------------------------
# Latent-backed FiLM view (Option E, ADR-08)
# ---------------------------------------------------------------------------


class _LatentFiLMView:
    """Thin proxy exposing (d_model, num_registers, gamma, beta, apply_register).

    Backed by a :class:`RegisterLatent` module's output-head computation. Used
    to keep call sites that historically read the old ``register_film.gamma``
    / ``.beta`` tensors working without modification. The gamma/beta tensors
    are computed on each access from the shared latent; they always reflect
    the current W + z_R state.

    This is NOT an ``nn.Module`` — it doesn't own parameters. The underlying
    parameters live on the :class:`RegisterLatent` that this view wraps.
    """

    __slots__ = ("_latent", "_surface", "d_model", "num_registers")

    def __init__(self, latent: RegisterLatent, surface: str) -> None:
        if surface not in ("s40", "sd"):
            raise ValueError(f"surface must be 's40' or 'sd', got {surface!r}")
        self._latent = latent
        self._surface = surface
        self.num_registers = latent.num_registers
        if surface == "s40":
            # d_model attribute retained for structural compatibility with
            # tests that expect the 40-dim FiLM to report d_model=40.
            self.d_model = latent.num_states
        else:
            self.d_model = latent.d_model

    @property
    def gamma(self) -> torch.Tensor:
        """Current gamma tensor, shape ``(num_registers, d_model)``."""
        if self._surface == "s40":
            g, _ = self._latent.compute_gamma_beta_40()
        else:
            g, _ = self._latent.compute_gamma_beta_d()
        return g

    @property
    def beta(self) -> torch.Tensor:
        """Current beta tensor, shape ``(num_registers, d_model)``."""
        if self._surface == "s40":
            _, b = self._latent.compute_gamma_beta_40()
        else:
            _, b = self._latent.compute_gamma_beta_d()
        return b

    def apply_register(
        self,
        state: torch.Tensor,
        register_idx: Optional[int],
    ) -> torch.Tensor:
        """Delegate to the latent module's apply_register_* variant."""
        if self._surface == "s40":
            return self._latent.apply_register_40(state, register_idx)
        return self._latent.apply_register_d(state, register_idx)


class CognitiveStateEmbeddingWithRegister(nn.Module):
    """CognitiveStateEmbedding + Phenomenological Register (CAS v7.5 / ADR-08).

    Under ADR-08 Option E, the register parameterization is a single shared
    :class:`RegisterLatent` module. It provides two FiLM surfaces:

    - 40-dim simplex surface — consumed via ``apply_register_40`` when the
      pre-simplex logits are modulated per-register (v7.5 path).
    - d_model surface — consumed via ``apply_register_d`` by downstream
      v7.7 binding heads (ADR-02 EmergentRegisterBindingHead) that need
      register-modulated hidden states at the transformer's native width.

    Both FiLM surfaces are projections of a single per-register latent
    vector ``z_R`` — register identity cannot drift between them.

    Register-neutral mode (``register_idx=None``) is byte-for-byte identical
    to the base CognitiveStateEmbedding forward, preserving CAS v7.4
    backward compatibility (ADR-01 invariant under ADR-08 refactor).

    Backward-compat attribute access
    --------------------------------
    ``register_film`` and ``register_film_dmodel`` are exposed as ``_LatentFiLMView``
    proxies — they look like a ``RegisterFiLM`` (``.gamma``, ``.beta``,
    ``.d_model``, ``.num_registers``, ``.apply_register``) but read through
    to the shared :class:`RegisterLatent`. This lets the legacy forward-path
    FiLM composition in ``cas_native_model.py`` continue to work without
    change.

    Args:
        d_model: Dim of input token embeddings. Also the width of the
            d_model FiLM surface used by downstream binding heads.
        num_states: Size of the cognitive state simplex (default 40).
        eps: Epsilon floor for strict positivity on the open simplex.
        register_dim: Deprecated — retained for signature compatibility;
            the 40-dim simplex FiLM surface is always sized at ``num_states``.
        num_registers: Number of Phenomenological Registers (default 4).
        latent_dim_r / scale_40 / scale_d / scale_warmup_steps:
            ADR-08 Option E hyperparameters (forwarded to RegisterLatent).
    """

    def __init__(
        self,
        d_model: int,
        num_states: int = NUM_COGNITIVE_STATES,
        eps: float = SIMPLEX_EPS,
        register_dim: Optional[int] = None,
        num_registers: int = NUM_REGISTERS,
        latent_dim_r: int = DEFAULT_LATENT_DIM_R,
        scale_40: float = DEFAULT_SCALE_40,
        scale_d: float = DEFAULT_SCALE_D,
        scale_warmup_steps: int = DEFAULT_SCALE_WARMUP_STEPS,
    ) -> None:
        super().__init__()

        # Base embedding — preserved verbatim (no behavioral change in
        # register-neutral mode).
        self.base = CognitiveStateEmbedding(
            d_model=d_model, num_states=num_states, eps=eps
        )

        # Option E (ADR-08): single shared latent module with dual FiLM heads.
        self.register_latent = RegisterLatent(
            d_model=d_model,
            num_states=num_states,
            num_registers=num_registers,
            latent_dim_r=latent_dim_r,
            scale_40=scale_40,
            scale_d=scale_d,
            scale_warmup_steps=scale_warmup_steps,
        )

        # ``register_dim`` retained only for signature compatibility.
        self.register_dim = register_dim if register_dim is not None else num_states

    # ------------------------------------------------------------------ views

    @property
    def register_film(self) -> _LatentFiLMView:
        """Legacy-compatible view of the 40-dim simplex FiLM surface.

        Under ADR-08 Option E this is a thin proxy over ``register_latent``;
        ``gamma`` and ``beta`` are computed on access from the shared
        per-register latent vector ``z_R``.
        """
        return _LatentFiLMView(self.register_latent, "s40")

    @property
    def register_film_dmodel(self) -> _LatentFiLMView:
        """Legacy-compatible view of the d_model FiLM surface.

        Under ADR-08 Option E this is a thin proxy over ``register_latent``;
        both FiLM surfaces derive from the same latent, preventing the
        semantic drift the two-module Wave 7A design permitted.
        """
        return _LatentFiLMView(self.register_latent, "sd")

    # --------------------------------------------------------------- passthru

    @property
    def d_model(self) -> int:
        return self.base.d_model

    @property
    def num_states(self) -> int:
        return self.base.num_states

    @property
    def eps(self) -> float:
        return self.base.eps

    # ------------------------------------------------------------------ fwd

    def forward(
        self,
        x: torch.Tensor,
        register_idx: Optional[int] = None,
    ) -> torch.Tensor:
        """
        Args:
            x: Token embeddings of shape (batch, seq, d_model).
            register_idx: Optional register index in [0, num_registers):
                0=T, 1=A, 2=f, 3=E. None = register-neutral (v7.4 behavior).

        Returns:
            Cognitive state vectors of shape (batch, seq, num_states) on the
            open probability simplex.
        """
        # Project to 40-dim logits via the base projection.
        logits = self.base.projection(x)

        # FiLM modulate on the 40-dim simplex surface (no-op when None).
        logits = self.register_latent.apply_register_40(logits, register_idx)

        # Re-project to the open simplex (shared implementation with base).
        return self.base._project_to_open_simplex(logits)

    @staticmethod
    def validate(tensor: torch.Tensor, tol: float = 1e-5) -> bool:
        """Delegate to CognitiveStateEmbedding.validate (identical contract)."""
        return CognitiveStateEmbedding.validate(tensor, tol=tol)
