"""
PrerequisiteGateLayer: Differentiable gate implementing the RPM
(Realization-Prerequisite Monad) chain A0 -> D -> W -> P.

CORRECTION 2: RPM is Section-Retraction, NOT Adjunction.
  epsilon_I . eta_I = id_I  (realization after embedding = identity)
  BUT: eta_I . epsilon_I != id_R(I)  (re-embedding after realization may lose info)

This means:
  - Forward (eta): embeds input into prerequisite space
  - Backward (epsilon): separate retraction path, NOT the inverse of eta
  - Satisfaction is ONE-DIRECTIONAL: we cache forward results
  - The gate attenuates (soft-blocks) signals that fail prerequisites

The 4 sequential gates correspond to the RPM chain:
  A0 (Pure Desire) -> D (Drive) -> W (Wisdom) -> P (Proficiency)
"""

import torch
import torch.nn as nn


class SoftGate(nn.Module):
    """A single differentiable soft gate.

    Computes a satisfaction score in [0, 1] via sigmoid, then element-wise
    multiplies the input. Below-threshold signals are attenuated, not
    hard-blocked, preserving gradient flow.
    """

    def __init__(self, d_model: int, threshold: float = 0.5):
        super().__init__()
        self.gate_proj = nn.Linear(d_model, d_model)
        self.threshold = threshold

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: Input tensor of shape (..., d_model)

        Returns:
            Tuple of (gated_output, satisfaction_scores)
            - gated_output: x * gate_score, shape (..., d_model)
            - satisfaction_scores: sigmoid outputs in [0, 1], shape (..., d_model)
        """
        satisfaction = torch.sigmoid(self.gate_proj(x))
        gated = x * satisfaction
        return gated, satisfaction


class PrerequisiteGateLayer(nn.Module):
    """Differentiable RPM prerequisite gate with section-retraction semantics.

    Implements the chain A0 -> Drive -> Wisdom -> Proficiency where each
    stage gates the next. Uses separate forward (eta) and retraction (epsilon)
    paths to enforce one-directional prerequisite satisfaction.

    The forward path (eta) embeds and computes satisfaction.
    The retraction path (epsilon) is a separate linear mapping that does NOT
    invert eta, implementing CORRECTION 2.
    """

    def __init__(self, d_model: int, threshold: float = 0.5):
        super().__init__()
        self.d_model = d_model
        self.threshold = threshold

        # 4 sequential soft gates: A0, Drive, Wisdom, Proficiency
        self.gate_a0 = SoftGate(d_model, threshold)
        self.gate_drive = SoftGate(d_model, threshold)
        self.gate_wisdom = SoftGate(d_model, threshold)
        self.gate_proficiency = SoftGate(d_model, threshold)

        # Forward embedding path (eta): embeds into prerequisite space
        self.eta = nn.Linear(d_model, d_model)

        # Retraction path (epsilon): separate, non-inverse of eta
        # epsilon . eta = id (section-retraction property)
        # BUT eta . epsilon != id (information loss possible)
        self.epsilon = nn.Linear(d_model, d_model)

        # Cache for forward satisfaction scores (CORRECTION 2)
        self._cached_satisfaction: dict[str, torch.Tensor] = {}

    def _clear_cache(self) -> None:
        """Clear cached satisfaction scores."""
        self._cached_satisfaction.clear()

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        """
        Args:
            x: Input tensor of shape (batch, seq, d_model)

        Returns:
            Tuple of (output, satisfaction_dict)
            - output: Gated output, shape (batch, seq, d_model)
            - satisfaction_dict: Dict mapping gate names to satisfaction tensors
        """
        self._clear_cache()

        # Forward embedding (eta)
        embedded = self.eta(x)

        # Sequential gating: A0 -> Drive -> Wisdom -> Proficiency
        out_a0, sat_a0 = self.gate_a0(embedded)
        out_drive, sat_drive = self.gate_drive(out_a0)
        out_wisdom, sat_wisdom = self.gate_wisdom(out_drive)
        out_prof, sat_prof = self.gate_proficiency(out_wisdom)

        # Cache satisfaction scores (one-directional, forward only)
        self._cached_satisfaction = {
            "a0": sat_a0.detach(),
            "drive": sat_drive.detach(),
            "wisdom": sat_wisdom.detach(),
            "proficiency": sat_prof.detach(),
        }

        # Retraction (epsilon): project back from prerequisite space
        # Note: epsilon is NOT the inverse of eta (CORRECTION 2)
        output = self.epsilon(out_prof)

        satisfaction_dict = {
            "a0": sat_a0,
            "drive": sat_drive,
            "wisdom": sat_wisdom,
            "proficiency": sat_prof,
        }

        return output, satisfaction_dict

    def get_mean_satisfaction(self) -> torch.Tensor:
        """Get the mean satisfaction across all gates from the last forward pass.

        Returns:
            Scalar tensor with the mean satisfaction score.
        """
        if not self._cached_satisfaction:
            return torch.tensor(0.0)

        all_sats = torch.stack([s.mean() for s in self._cached_satisfaction.values()])
        return all_sats.mean()
