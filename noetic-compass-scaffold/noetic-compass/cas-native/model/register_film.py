"""
RegisterLatent + RegisterFiLM: Phenomenological Register parameterization
for CAS v7.5 integration, under the Option E architecture (ADR-08).

This module hosts TWO primary classes:

1. ``RegisterLatent`` (Option E, ADR-08) — the authoritative register
   parameterization. A single per-register latent vector ``z_R`` feeds four
   zero-initialized linear output heads, producing (gamma_40, beta_40,
   gamma_d, beta_d) FiLM tensors via tanh-saturated scaled readouts:

       gamma = 1 + s * tanh(W * z_R)
       beta  = s * tanh(W * z_R)

   Register identity is a single source of truth (the latent ``z_R``); both
   FiLM surfaces (40-dim cognitive simplex + d_model hidden state) are
   projections of that same semantic source. This closes the semantic-drift
   gap between the two independent FiLM modules shipped in Wave 7A.

2. ``RegisterFiLM`` (legacy shim, preserved) — now a thin wrapper exposing
   an ``nn.Parameter`` ``gamma``/``beta`` API over a fixed (num_registers,
   d_model) pair. Used only in tests that assert RegisterFiLM-specific
   attribute shapes; the model + embedding + trainer path consumes
   ``RegisterLatent`` exclusively.

Register index mapping (per CAS v7.5 Clarification 8; lowercase ``f`` for
Affective is authoritative):

    0 = T  (Transcendent)
    1 = A  (Analytical)
    2 = f  (Affective)
    3 = E  (Embodied)

Involution pair structure:

    T <-> E   (idx 0 <-> 3)
    A <-> f   (idx 1 <-> 2)

Enforced via ADR-08 ``LatentInvolutionLoss`` (latent-level + output-surface
terms) in ``cas-native/model/loss.py``.

References
----------
- docs/architecture/cas_native_v2_adrs.md (ADR-01 historical, ADR-08 current)
- docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md (Clarification 8)
"""

from __future__ import annotations

from typing import Optional

import torch
import torch.nn as nn


# Number of Phenomenological Registers: T, A, f, E
NUM_REGISTERS = 4

# Register index map (lowercase `f` preserved per Clarification 8)
REGISTER_INDEX = {
    "T": 0,  # Transcendent
    "A": 1,  # Analytical
    "f": 2,  # Affective (lowercase per authoritative Clarification 8)
    "E": 3,  # Embodied
}

# Inverse map: idx -> symbol
REGISTER_SYMBOL = {v: k for k, v in REGISTER_INDEX.items()}

# Involution pairs (idx_a, idx_b) — soft-constrained in loss:
#   latent-level:  z_a + z_b = 0     (additive inverse in latent space)
#   surface-level: gamma_a * gamma_b = 1, beta_a + beta_b = 0
INVOLUTION_REGISTER_PAIRS: list[tuple[int, int]] = [
    (REGISTER_INDEX["T"], REGISTER_INDEX["E"]),  # T <-> E
    (REGISTER_INDEX["A"], REGISTER_INDEX["f"]),  # A <-> f
]

# Default register embedding dimension (historical ADR-01 d_model).
DEFAULT_REGISTER_DIM = 128

# Cognitive-state simplex width (10 Noetics x 4 Domains).
DEFAULT_NUM_STATES = 40

# ADR-08 Option E hyperparameter defaults.
DEFAULT_LATENT_DIM_R = 16
DEFAULT_SCALE_40 = 0.05
DEFAULT_SCALE_D = 0.02
DEFAULT_SCALE_WARMUP_STEPS = 1000


# ---------------------------------------------------------------------------
# RegisterLatent — Option E (ADR-08). Authoritative register parameterization.
# ---------------------------------------------------------------------------


class RegisterLatent(nn.Module):
    """Shared-latent-with-dual-output-heads register parameterization (ADR-08).

    Single semantic source ``z_R`` per register (a ``(num_registers,
    latent_dim_r)`` learnable embedding table) read out into BOTH FiLM
    surfaces via separate learned linear heads:

        gamma_40 = 1 + s_40 * tanh(W_gamma_40 @ z_R)    shape (R, num_states)
        beta_40  =       s_40 * tanh(W_beta_40  @ z_R)  shape (R, num_states)
        gamma_d  = 1 + s_d  * tanh(W_gamma_d  @ z_R)    shape (R, d_model)
        beta_d   =       s_d  * tanh(W_beta_d   @ z_R)  shape (R, d_model)

    All four W matrices are zero-initialized, and tanh(0) = 0, so at
    initialization every FiLM is exactly the identity transform (gamma = 1,
    beta = 0). This preserves the ADR-01 byte-equivalence invariant under
    Option E without requiring any explicit ``register_idx=None``
    short-circuit at the module boundary — the identity is structural.

    Motivation (CARP Round 3 panel consensus, 4-of-5 Option E)
    ---------------------------------------------------------
    Wave 7A's design (``RegisterFiLM`` at 40-dim + ``RegisterFiLM`` at
    d_model) used two independently-learned gamma/beta pairs per register.
    Nothing architecturally forced them to represent the same register
    concept — semantic drift was possible. ADR-08 Option E closes the gap
    structurally: register identity is a single ``z_R``; both substrate
    expressions are projections of one semantic source.

    Scale-freeze mechanism
    ----------------------
    ``scale_40`` and ``scale_d`` are stored as ``nn.Parameter`` with a
    freeze flag (``_scales_frozen``). While frozen, external callers are
    responsible for NOT adding them to the optimizer's param groups; the
    :py:meth:`parameters_for_optimizer` helper filters them appropriately.
    After ``scale_warmup_steps`` training steps the scales unfreeze,
    receive gradient, and jointly adapt with the W matrices. The
    per-parameter freeze gives the W heads time to find useful directions
    before the scalar magnitudes adapt, reducing early-training
    instability.

    Parameters
    ----------
    d_model
        Width of the d_model FiLM surface (must match the transformer's
        hidden-state dimension). Default 128 per ADR-01.
    num_states
        Width of the 40-dim cognitive-state simplex FiLM surface. Default
        40 (10 Noetics x 4 Domains).
    num_registers
        Number of Phenomenological Registers. Default 4 (T, A, f, E).
    latent_dim_r
        Latent embedding dimension per register. Default 16.
    scale_40
        Initial scale on the 40-dim FiLM surface. Default 0.05.
    scale_d
        Initial scale on the d_model FiLM surface. Default 0.02.
    scale_warmup_steps
        Number of training steps during which scales remain frozen.
        Default 1000. Only an informational hint — actual freeze/unfreeze
        is driven by the caller via :py:meth:`set_scales_frozen`.

    Parameter budget (d_model=128, latent_dim_r=16, num_registers=4,
    num_states=40)::

        register_latent : 4 * 16                = 64
        W_gamma_40      : 16 * 40               = 640
        W_beta_40       : 16 * 40               = 640
        W_gamma_d       : 16 * 128              = 2048
        W_beta_d        : 16 * 128              = 2048
        scale_40        : 1
        scale_d         : 1
                                       Total   = 5,442  (~ 5,440 per ADR-08)

    At d_model=512: 5,442 - 4,096 + 16,384 = 17,730 (~ ADR-08's 17,728).
    """

    def __init__(
        self,
        d_model: int = DEFAULT_REGISTER_DIM,
        num_states: int = DEFAULT_NUM_STATES,
        num_registers: int = NUM_REGISTERS,
        latent_dim_r: int = DEFAULT_LATENT_DIM_R,
        scale_40: float = DEFAULT_SCALE_40,
        scale_d: float = DEFAULT_SCALE_D,
        scale_warmup_steps: int = DEFAULT_SCALE_WARMUP_STEPS,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.num_states = num_states
        self.num_registers = num_registers
        self.latent_dim_r = latent_dim_r
        self.scale_warmup_steps = int(scale_warmup_steps)

        # Register latent embedding table (z_R for R in {T, A, f, E}).
        self.register_latent = nn.Parameter(
            torch.randn(num_registers, latent_dim_r)
        )

        # FiLM_40 output heads (zero-initialized for step-0 identity).
        self.W_gamma_40 = nn.Linear(latent_dim_r, num_states, bias=False)
        self.W_beta_40 = nn.Linear(latent_dim_r, num_states, bias=False)
        nn.init.zeros_(self.W_gamma_40.weight)
        nn.init.zeros_(self.W_beta_40.weight)

        # FiLM_dmodel output heads (zero-initialized).
        self.W_gamma_d = nn.Linear(latent_dim_r, d_model, bias=False)
        self.W_beta_d = nn.Linear(latent_dim_r, d_model, bias=False)
        nn.init.zeros_(self.W_gamma_d.weight)
        nn.init.zeros_(self.W_beta_d.weight)

        # Register scales as Parameters so they can flow into the optimizer
        # after warmup. ``_scales_frozen=True`` is the initial state; the
        # trainer toggles this after ``scale_warmup_steps`` via
        # :py:meth:`set_scales_frozen`.
        self.scale_40 = nn.Parameter(torch.tensor(float(scale_40)))
        self.scale_d = nn.Parameter(torch.tensor(float(scale_d)))
        # ``requires_grad=False`` while frozen so autograd does not build
        # a graph edge; the corresponding optimizer param groups must
        # reflect the same choice (see parameters_for_optimizer).
        self.scale_40.requires_grad_(False)
        self.scale_d.requires_grad_(False)
        self._scales_frozen: bool = True

    # --------------------------------------------------------------- freeze

    @property
    def scales_frozen(self) -> bool:
        """True while ``scale_40`` / ``scale_d`` are not receiving grad."""
        return self._scales_frozen

    def set_scales_frozen(self, frozen: bool) -> None:
        """Freeze or unfreeze the scalar scale parameters.

        Updates ``requires_grad`` on both scale tensors; the trainer's
        optimizer param groups must be (re)built around this state to
        control which tensors receive updates.
        """
        self._scales_frozen = bool(frozen)
        self.scale_40.requires_grad_(not self._scales_frozen)
        self.scale_d.requires_grad_(not self._scales_frozen)

    def parameters_for_optimizer(self) -> list[nn.Parameter]:
        """Return the parameter list the optimizer should currently update.

        Excludes frozen scales. The caller is expected to rebuild its
        optimizer param groups when freeze state changes (see
        :py:meth:`set_scales_frozen`).
        """
        out: list[nn.Parameter] = [
            self.register_latent,
            self.W_gamma_40.weight,
            self.W_beta_40.weight,
            self.W_gamma_d.weight,
            self.W_beta_d.weight,
        ]
        if not self._scales_frozen:
            out.append(self.scale_40)
            out.append(self.scale_d)
        return out

    # --------------------------------------------------------------- compute

    def compute_gamma_beta_40(self) -> tuple[torch.Tensor, torch.Tensor]:
        """Return (gamma_40, beta_40) of shape ``(num_registers, num_states)``.

        At init (W_*_40 zero): tanh(0) = 0, so gamma_40 = 1 (all ones) and
        beta_40 = 0 (all zeros). Identity FiLM on the 40-dim simplex.
        """
        raw_g = self.W_gamma_40(self.register_latent)  # (R, num_states)
        raw_b = self.W_beta_40(self.register_latent)   # (R, num_states)
        gamma = 1.0 + self.scale_40 * torch.tanh(raw_g)
        beta = self.scale_40 * torch.tanh(raw_b)
        return gamma, beta

    def compute_gamma_beta_d(self) -> tuple[torch.Tensor, torch.Tensor]:
        """Return (gamma_d, beta_d) of shape ``(num_registers, d_model)``.

        At init (W_*_d zero): identity FiLM at d_model width.
        """
        raw_g = self.W_gamma_d(self.register_latent)  # (R, d_model)
        raw_b = self.W_beta_d(self.register_latent)   # (R, d_model)
        gamma = 1.0 + self.scale_d * torch.tanh(raw_g)
        beta = self.scale_d * torch.tanh(raw_b)
        return gamma, beta

    # --------------------------------------------------------------- apply

    def apply_register_40(
        self,
        state: torch.Tensor,
        register_idx: Optional[int],
    ) -> torch.Tensor:
        """Apply FiLM_40 to a ``(..., num_states)`` state tensor.

        When ``register_idx is None``, returns the input tensor unchanged
        (v7.4 byte-equivalent fast path).
        """
        if register_idx is None:
            return state
        if not isinstance(register_idx, int):
            register_idx = int(register_idx)
        if register_idx < 0 or register_idx >= self.num_registers:
            raise IndexError(
                f"register_idx {register_idx} out of range "
                f"[0, {self.num_registers})"
            )
        if state.shape[-1] != self.num_states:
            raise ValueError(
                f"Expected last dimension {self.num_states}, got "
                f"{state.shape[-1]}"
            )
        gamma, beta = self.compute_gamma_beta_40()
        return gamma[register_idx] * state + beta[register_idx]

    def apply_register_d(
        self,
        hidden: torch.Tensor,
        register_idx: Optional[int],
    ) -> torch.Tensor:
        """Apply FiLM_dmodel to a ``(..., d_model)`` hidden-state tensor.

        When ``register_idx is None``, returns the input unchanged.
        """
        if register_idx is None:
            return hidden
        if not isinstance(register_idx, int):
            register_idx = int(register_idx)
        if register_idx < 0 or register_idx >= self.num_registers:
            raise IndexError(
                f"register_idx {register_idx} out of range "
                f"[0, {self.num_registers})"
            )
        if hidden.shape[-1] != self.d_model:
            raise ValueError(
                f"Expected last dimension {self.d_model}, got "
                f"{hidden.shape[-1]}"
            )
        gamma, beta = self.compute_gamma_beta_d()
        return gamma[register_idx] * hidden + beta[register_idx]

    # ----------------------------------------------------------- diagnostics

    def diagnostic_metrics(self) -> dict[str, torch.Tensor]:
        """Return a dict of per-register scalar metrics for trainer logging.

        Keys (each a 1-D tensor of length ``num_registers``):

          - ``z_norm``          : ``||z_R||``           (latent magnitude)
          - ``gamma40_norm``    : ``||gamma_40,R - 1||``  (deviation from id)
          - ``beta40_norm``     : ``||beta_40,R||``
          - ``gammad_norm``     : ``||gamma_d,R - 1||``
          - ``betad_norm``      : ``||beta_d,R||``

        Plus scalar metrics:

          - ``scale_40_value``  : current ``scale_40`` (scalar)
          - ``scale_d_value``   : current ``scale_d`` (scalar)
          - ``scales_frozen``   : 1.0 if frozen, 0.0 if unfrozen
        """
        with torch.no_grad():
            gamma40, beta40 = self.compute_gamma_beta_40()
            gammad, betad = self.compute_gamma_beta_d()
            return {
                "z_norm": self.register_latent.norm(dim=-1).detach(),
                "gamma40_norm": (gamma40 - 1.0).norm(dim=-1).detach(),
                "beta40_norm": beta40.norm(dim=-1).detach(),
                "gammad_norm": (gammad - 1.0).norm(dim=-1).detach(),
                "betad_norm": betad.norm(dim=-1).detach(),
                "scale_40_value": self.scale_40.detach().clone(),
                "scale_d_value": self.scale_d.detach().clone(),
                "scales_frozen": torch.tensor(
                    1.0 if self._scales_frozen else 0.0
                ),
            }

    # -------------------------------------------------------------- count

    def num_parameters(self) -> int:
        """Return the total parameter count (both trainable and frozen)."""
        return sum(p.numel() for p in self.parameters())


# ---------------------------------------------------------------------------
# RegisterFiLM — legacy compatibility shim.
# ---------------------------------------------------------------------------


class RegisterFiLM(nn.Module):
    """Legacy FiLM module with direct (gamma, beta) parameters.

    Preserved for backward compatibility with tests that assert specific
    attribute names (``.gamma``, ``.beta``) and the ``(num_registers,
    d_model)`` shape. The model / embedding / trainer forward path uses
    :class:`RegisterLatent` instead (ADR-08 Option E).

    Applies an affine per-register transform to a base state vector::

        state_output = gamma[register_idx] * state + beta[register_idx]

    gamma is identity-initialized (ones) and beta is zero-initialized so
    that, at training start, the modulation is exactly the identity map.
    A ``register_idx of None`` short-circuits the call and returns the
    input tensor unchanged, preserving CAS v7.4 register-neutral
    semantics.

    Args:
        d_model: Dimensionality of the base state vector. Default 128.
        num_registers: Number of registers. Default 4 (T, A, f, E).
    """

    def __init__(
        self,
        d_model: int = DEFAULT_REGISTER_DIM,
        num_registers: int = NUM_REGISTERS,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.num_registers = num_registers

        self.gamma = nn.Parameter(torch.ones(num_registers, d_model))
        self.beta = nn.Parameter(torch.zeros(num_registers, d_model))

    def apply_register(
        self,
        state: torch.Tensor,
        register_idx: Optional[int],
    ) -> torch.Tensor:
        """Apply per-register FiLM modulation to a state tensor."""
        if register_idx is None:
            return state

        if not isinstance(register_idx, int):
            register_idx = int(register_idx)

        if register_idx < 0 or register_idx >= self.num_registers:
            raise IndexError(
                f"register_idx {register_idx} out of range "
                f"[0, {self.num_registers})"
            )

        if state.shape[-1] != self.d_model:
            raise ValueError(
                f"Expected last dimension {self.d_model}, got "
                f"{state.shape[-1]}"
            )

        return self.gamma[register_idx] * state + self.beta[register_idx]

    def forward(
        self,
        state: torch.Tensor,
        register_idx: Optional[int] = None,
    ) -> torch.Tensor:
        """Alias for apply_register; register_idx defaults to None (neutral)."""
        return self.apply_register(state, register_idx)

    def num_parameters(self) -> int:
        """Return the total learned parameter count."""
        return sum(p.numel() for p in self.parameters())
