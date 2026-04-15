"""
LacunarityGate: Real-time self-correction during inference.

When cognitive activation concentrates too heavily in too few slots,
this gate nudges activation toward neglected slots. Operates between
DomainDescentAttention and the output heads.

This is inference-time self-correction. The model catches itself
when its thinking gets too narrow.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class LacunarityGate(nn.Module):
    """Self-correcting gate that reduces extreme cognitive concentration.

    Computes lacunarity (Var/Mean^2) on the slot activation vector.
    When lacunarity exceeds the threshold, applies a learned correction
    that boosts neglected slots and dampens over-concentrated ones.
    Re-normalizes to maintain the open simplex constraint (all > 0, sum = 1).

    Args:
        num_slots: Number of cognitive state slots (default 40).
        threshold: Lacunarity threshold above which correction activates.
        correction_strength: How strongly to apply the correction.
    """

    def __init__(
        self,
        num_slots: int = 40,
        threshold: float = 2.0,
        correction_strength: float = 0.3,
    ):
        super().__init__()
        self.num_slots = num_slots
        self.threshold = threshold
        self.strength = correction_strength
        self.rebalance = nn.Linear(num_slots, num_slots)
        self.gate = nn.Linear(num_slots, 1)

    def forward(
        self, slot_activations: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Apply lacunarity-aware self-correction.

        Args:
            slot_activations: (batch, ..., num_slots) on the simplex

        Returns:
            (corrected_activations, lacunarity_scores)
            corrected stays on the open simplex
            lacunarity_scores is (batch,) or (batch, seq) scalar per sample
        """
        # Flatten to (batch, num_slots) if needed
        orig_shape = slot_activations.shape
        flat = slot_activations.reshape(-1, self.num_slots)

        # Compute lacunarity: Var / Mean^2
        mean = flat.mean(dim=-1, keepdim=True)
        var = ((flat - mean) ** 2).mean(dim=-1, keepdim=True)
        lacunarity = var / (mean ** 2 + 1e-8)

        # Determine correction strength per sample
        needs_correction = (lacunarity > self.threshold).float()
        gate_strength = torch.sigmoid(self.gate(flat))

        # Correction: learned rebalancing
        correction = self.rebalance(flat)
        corrected = flat + self.strength * needs_correction * gate_strength * correction

        # Re-normalize to open simplex via softmax with temperature
        corrected = F.softmax(corrected / 0.1, dim=-1)
        corrected = corrected.clamp(min=1e-6)
        corrected = corrected / corrected.sum(dim=-1, keepdim=True)

        # Reshape back
        corrected = corrected.reshape(orig_shape)
        lacunarity_out = lacunarity.squeeze(-1).reshape(orig_shape[:-1]) if len(orig_shape) > 2 else lacunarity.squeeze(-1)

        return corrected, lacunarity_out
