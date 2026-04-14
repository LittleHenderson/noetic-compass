"""
CAS Generative Composition Module

Implements the monoid composition algebra at the neural level:
- COMPOSE_TABLE: the (i+j) mod 10 multiplication table
- CompositionHead: learns to compose two slot activations via monoid rules
- GenerativeHead: takes two cognitive state embeddings and produces the emergent state
- composition_loss: penalizes violations of monoid composition rules
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


# The CAS operator monoid: (i + j) mod 10, CO-0 is identity
COMPOSE_TABLE = torch.zeros(10, 10, dtype=torch.long)
for i in range(10):
    for j in range(10):
        COMPOSE_TABLE[i][j] = (i + j) % 10


class CompositionHead(nn.Module):
    """Learns to compose two cognitive operator activations via the CAS monoid.

    Takes two slot activations (from the 40-slot cognitive state) in the same
    domain and computes the monoid composition. The result is compared against
    the ground-truth composition table during training.

    Args:
        d_model: Hidden dimension of the model.
        num_operators: Number of cognitive operators (default 10).
        num_domains: Number of processing domains (default 4).
    """

    def __init__(self, d_model: int, num_operators: int = 10, num_domains: int = 4):
        super().__init__()
        self.num_operators = num_operators
        self.num_domains = num_domains

        # Project slot representations to operator logits
        self.slot_to_operator = nn.Linear(d_model, num_operators)

        # Learnable composition bias (initialized to match the monoid table)
        # This allows the model to learn deviations while being anchored to the theory
        self.compose_bias = nn.Parameter(torch.zeros(num_operators, num_operators, num_operators))
        self._init_compose_bias()

    def _init_compose_bias(self) -> None:
        """Initialize compose_bias to match the monoid table."""
        with torch.no_grad():
            for i in range(self.num_operators):
                for j in range(self.num_operators):
                    result = (i + j) % self.num_operators
                    self.compose_bias[i, j, result] = 5.0  # Strong prior toward correct composition

    def forward(
        self,
        slot_a: torch.Tensor,
        slot_b: torch.Tensor,
    ) -> torch.Tensor:
        """Compose two slot representations.

        Args:
            slot_a: Representation of first operator slot (batch, d_model)
            slot_b: Representation of second operator slot (batch, d_model)

        Returns:
            Predicted operator distribution after composition (batch, num_operators)
        """
        # Get operator distributions for each slot
        logits_a = self.slot_to_operator(slot_a)  # (batch, 10)
        logits_b = self.slot_to_operator(slot_b)  # (batch, 10)
        probs_a = F.softmax(logits_a, dim=-1)  # (batch, 10)
        probs_b = F.softmax(logits_b, dim=-1)  # (batch, 10)

        # Outer product of operator distributions
        joint = torch.einsum('bi,bj->bij', probs_a, probs_b)  # (batch, 10, 10)

        # Apply composition: sum over all (i,j) pairs weighted by compose_bias
        compose_logits = F.softmax(self.compose_bias, dim=-1)  # (10, 10, 10)
        result = torch.einsum('bij,ijk->bk', joint, compose_logits)  # (batch, 10)

        return result


class GenerativeHead(nn.Module):
    """Takes two CognitiveState embeddings and produces the emergent state.

    This head enables CAS-Native to not just classify states but COMPOSE them,
    matching the compiler's generative capability at the neural level.

    Args:
        d_model: Hidden dimension.
        num_states: Number of cognitive states (default 40 = 10 operators × 4 domains).
    """

    def __init__(self, d_model: int, num_states: int = 40):
        super().__init__()
        self.num_states = num_states

        # Combine two state embeddings
        self.merge = nn.Sequential(
            nn.Linear(d_model * 2, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model),
        )

        # Composition head for operator-level composition
        self.composition = CompositionHead(d_model)

        # Project to state distribution on the 40-simplex
        self.to_state = nn.Linear(d_model, num_states)

    def forward(
        self,
        state_a: torch.Tensor,
        state_b: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        """Compose two cognitive state embeddings.

        Args:
            state_a: First state embedding (batch, d_model)
            state_b: Second state embedding (batch, d_model)

        Returns:
            Dict with:
              - emergent_state: predicted state distribution (batch, 40)
              - operator_composition: predicted operator distribution (batch, 10)
        """
        # Merge the two states
        merged = self.merge(torch.cat([state_a, state_b], dim=-1))

        # Operator-level composition
        op_composition = self.composition(state_a, state_b)

        # Full state distribution (on the 40-simplex)
        state_logits = self.to_state(merged)
        emergent_state = F.softmax(state_logits, dim=-1)

        return {
            "emergent_state": emergent_state,
            "operator_composition": op_composition,
        }


def composition_loss(
    predicted_op: torch.Tensor,
    op_idx_a: torch.Tensor,
    op_idx_b: torch.Tensor,
) -> torch.Tensor:
    """Penalize the model when its internal representations violate monoid composition.

    Args:
        predicted_op: Predicted operator distribution (batch, 10)
        op_idx_a: Ground truth operator indices for first operand (batch,)
        op_idx_b: Ground truth operator indices for second operand (batch,)

    Returns:
        Scalar loss that is zero when the model correctly predicts (a+b) mod 10.
    """
    device = predicted_op.device
    table = COMPOSE_TABLE.to(device)

    # Ground truth: (a + b) mod 10
    target = table[op_idx_a, op_idx_b]  # (batch,)

    # Cross-entropy between predicted distribution and ground truth
    return F.cross_entropy(predicted_op, target)
