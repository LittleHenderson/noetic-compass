"""
RegisterFiLM: Feature-wise Linear Modulation for Phenomenological Register
integration (CAS v7.5 / ADR-01).

The Phenomenological Register specifies the operational character (T, A, f, E)
of a cognitive state without changing what the operation IS. This module
implements the register as a per-register affine modulation (FiLM, Perez et al.
2018) applied to the base cognitive state vector:

    state_output[R] = gamma[R] * state + beta[R]

Register index mapping (per CAS v7.5 Clarification 8; lowercase `f` for
Affective is authoritative):

    0 = T  (Transcendent)
    1 = A  (Analytical)
    2 = f  (Affective)
    3 = E  (Embodied)

Involution pair structure (enforced SOFTLY via InvolutionConstraintLoss in
loss.py, NOT hard architectural enforcement):

    T <-> E   (idx 0 <-> 3)
    A <-> f   (idx 1 <-> 2)

At initialization (gamma = 1, beta = 0) the modulation is the identity
transformation: apply_register(state, R) == state for all R. A register_idx of
None skips the modulation entirely, preserving full CAS v7.4 backward
compatibility with no computation cost and no parameter touch.

Parameter budget: 4 registers x 2 (gamma, beta) x d_model = 1,024 params at
d_model = 128 (ADR-01 default).

Reference: docs/architecture/cas_native_v2_adrs.md (ADR-01).
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
#   gamma[a] * gamma[b] = 1  (multiplicative inverse)
#   beta[a] + beta[b] = 0    (additive inverse)
INVOLUTION_REGISTER_PAIRS: list[tuple[int, int]] = [
    (REGISTER_INDEX["T"], REGISTER_INDEX["E"]),  # T <-> E
    (REGISTER_INDEX["A"], REGISTER_INDEX["f"]),  # A <-> f
]

# ADR-01 default register embedding dimension
DEFAULT_REGISTER_DIM = 128


class RegisterFiLM(nn.Module):
    """Feature-wise Linear Modulation parameterized by Phenomenological Register.

    Applies an affine per-register transform to a base cognitive state vector:

        state_output = gamma[register_idx] * state + beta[register_idx]

    gamma is identity-initialized (ones) and beta is zero-initialized so that,
    at training start, the modulation is exactly the identity map. A
    register_idx of None short-circuits the call and returns the input tensor
    unchanged, preserving CAS v7.4 register-neutral semantics.

    Args:
        d_model: Dimensionality of the base state vector. Default 128 per ADR-01.
        num_registers: Number of registers. Default 4 (T, A, f, E).

    Shape:
        state: (..., d_model)
        output: (..., d_model) — same shape as state.

    Parameter count: num_registers * 2 * d_model
        (default 4 * 2 * 128 = 1,024 per ADR-01).
    """

    def __init__(
        self,
        d_model: int = DEFAULT_REGISTER_DIM,
        num_registers: int = NUM_REGISTERS,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.num_registers = num_registers

        # Identity initialization: gamma = 1, beta = 0 -> register-neutral
        # at start of training (ADR-01 Decision section).
        self.gamma = nn.Parameter(torch.ones(num_registers, d_model))
        self.beta = nn.Parameter(torch.zeros(num_registers, d_model))

    def apply_register(
        self,
        state: torch.Tensor,
        register_idx: Optional[int],
    ) -> torch.Tensor:
        """Apply per-register FiLM modulation to a state tensor.

        Args:
            state: Input tensor of shape (..., d_model).
            register_idx: Integer index in [0, num_registers) selecting T/A/f/E,
                or None for register-neutral (v7.4 backward-compat) — skips
                modulation and returns `state` unchanged.

        Returns:
            Modulated tensor of the same shape as `state`, or `state` itself
            when register_idx is None.

        Raises:
            IndexError: If register_idx is out of range.
            ValueError: If state's last dim does not equal d_model.
        """
        # v7.4 backward-compat fast path: no computation, no parameter touch.
        if register_idx is None:
            return state

        if not isinstance(register_idx, int):
            # Accept 0-d tensor or numpy-like; normalize to int.
            register_idx = int(register_idx)

        if register_idx < 0 or register_idx >= self.num_registers:
            raise IndexError(
                f"register_idx {register_idx} out of range "
                f"[0, {self.num_registers})"
            )

        if state.shape[-1] != self.d_model:
            raise ValueError(
                f"Expected last dimension {self.d_model}, got {state.shape[-1]}"
            )

        # Broadcast gamma[register_idx], beta[register_idx] over leading dims.
        return self.gamma[register_idx] * state + self.beta[register_idx]

    def forward(
        self,
        state: torch.Tensor,
        register_idx: Optional[int] = None,
    ) -> torch.Tensor:
        """Alias for apply_register; register_idx defaults to None (neutral)."""
        return self.apply_register(state, register_idx)

    def num_parameters(self) -> int:
        """Return the total learned parameter count.

        Expected: num_registers * 2 * d_model (default 1,024 per ADR-01).
        """
        return sum(p.numel() for p in self.parameters())
