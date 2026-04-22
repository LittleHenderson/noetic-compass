"""
CognitiveStateEmbedding: Projects token embeddings onto the 40-dimensional
open probability simplex.

The target space is S_I = Delta_39 = { p in R^40 : pk > 0 for all k, sum(pk) = 1 }
(CORRECTION 4: open probability simplex, NOT discrete 40-element set).

The 40 dimensions correspond to the 10 Cognitive Operators x 4 Processing Domains:
  P0-P9 (Principled), C0-C9 (Cognitive), E0-E9 (Evaluative), O0-O9 (Operational)
"""

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from .register_film import RegisterFiLM, DEFAULT_REGISTER_DIM, NUM_REGISTERS


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


class CognitiveStateEmbeddingWithRegister(nn.Module):
    """CognitiveStateEmbedding composed with RegisterFiLM modulation.

    This class adds Phenomenological Register (CAS v7.5) integration on top of
    the base CognitiveStateEmbedding. Two FiLM modules are maintained:

    - ``register_film`` — operates at ``register_dim`` (default = ``num_states``,
      40) on the PRE-SIMPLEX LOGITS produced by the base projection. This is
      the v7.5 path: per-register modulation of the cognitive-state
      distribution directly. The FiLM is applied to the 40-dim logit vector,
      not the intermediate d_model/2 layer.

    - ``register_film_dmodel`` — operates at the BASE ``d_model`` width and is
      the consumer surface for downstream v7.7 components (ADR-02
      EmergentRegisterBindingHead) that need register-modulated hidden states
      at the transformer's native representation width. Without this second
      FiLM the binding head could only consume 40-dim states, breaking the
      ADR-01/ADR-02 contract that `d_model` is a free parameter.

    Register-neutral mode (``register_idx=None``) is byte-for-byte identical
    to the base CognitiveStateEmbedding forward, preserving CAS v7.4 backward
    compatibility (ADR-01).

    Args:
        d_model: Dim of input token embeddings. Also the width of the
            ``register_film_dmodel`` FiLM used by downstream binding heads.
        num_states: Size of the cognitive state simplex (default 40).
        eps: Epsilon floor for strict positivity on the open simplex.
        register_dim: FiLM modulation dim for the pre-simplex logits; defaults
            to ``num_states`` because the FiLM modulates the 40-dim logits.
        num_registers: Number of Phenomenological Registers (default 4: T/A/f/E).
    """

    def __init__(
        self,
        d_model: int,
        num_states: int = NUM_COGNITIVE_STATES,
        eps: float = SIMPLEX_EPS,
        register_dim: Optional[int] = None,
        num_registers: int = NUM_REGISTERS,
    ) -> None:
        super().__init__()

        # Base embedding — preserved verbatim (no behavioral change in
        # register-neutral mode).
        self.base = CognitiveStateEmbedding(
            d_model=d_model, num_states=num_states, eps=eps
        )

        # FiLM operating on the 40-dim pre-simplex logit vector so the
        # per-register modulation affects the cognitive-state distribution
        # directly. register_dim defaults to num_states for that reason.
        self.register_dim = register_dim if register_dim is not None else num_states
        self.register_film = RegisterFiLM(
            d_model=self.register_dim,
            num_registers=num_registers,
        )
        # Additional FiLM operating at the BASE d_model width. This is what
        # downstream binding heads (ADR-02 EmergentRegisterBindingHead) consume
        # when they need register-modulated hidden states at the transformer's
        # native dimension. Keeping this separate from `register_film` above
        # preserves the v7.5 simplex-modulation semantics while making d_model
        # a free parameter end-to-end.
        self.register_film_dmodel = RegisterFiLM(
            d_model=d_model,
            num_registers=num_registers,
        )

    @property
    def d_model(self) -> int:
        return self.base.d_model

    @property
    def num_states(self) -> int:
        return self.base.num_states

    @property
    def eps(self) -> float:
        return self.base.eps

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

        # FiLM modulate (no-op when register_idx is None).
        logits = self.register_film.apply_register(logits, register_idx)

        # Re-project to the open simplex (shared implementation with base).
        return self.base._project_to_open_simplex(logits)

    @staticmethod
    def validate(tensor: torch.Tensor, tol: float = 1e-5) -> bool:
        """Delegate to CognitiveStateEmbedding.validate (identical contract)."""
        return CognitiveStateEmbedding.validate(tensor, tol=tol)
