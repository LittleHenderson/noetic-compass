"""
CognitiveStateEmbedding: Projects token embeddings onto the 40-dimensional
open probability simplex.

The target space is S_I = Delta_39 = { p in R^40 : pk > 0 for all k, sum(pk) = 1 }
(CORRECTION 4: open probability simplex, NOT discrete 40-element set).

The 40 dimensions correspond to the 10 Cognitive Operators x 4 Processing Domains:
  P0-P9 (Principled), C0-C9 (Cognitive), E0-E9 (Evaluative), O0-O9 (Operational)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


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
