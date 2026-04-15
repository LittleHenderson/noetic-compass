"""
LacunarityHead: Metacognitive output head for gap awareness.

Reports the model's own cognitive gap profile alongside its main output.
Produces:
- 5 lacunarity scores (state, fractal, domain, drive, rpm)
- 40-element gap map (probability each slot is a gap)
- 4 domain confidence scores (P, C, E, O)

This is output-time metacognition. The model warns you about its own
blind spots BEFORE you check.
"""

import torch
import torch.nn as nn


class LacunarityHead(nn.Module):
    """Metacognitive head that reports cognitive gap awareness.

    Args:
        d_model: Hidden dimension of the model.
        num_slots: Number of cognitive state slots (default 40).
        num_domains: Number of processing domains (default 4).
    """

    def __init__(self, d_model: int, num_slots: int = 40, num_domains: int = 4):
        super().__init__()

        # Predicts 5 lacunarity dimension scores
        self.lacunarity_predictor = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Linear(d_model // 2, 5),
        )

        # Predicts per-slot gap probability (is this slot a blind spot?)
        self.gap_detector = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.ReLU(),
            nn.Linear(d_model // 2, num_slots),
            nn.Sigmoid(),
        )

        # Predicts per-domain confidence (how confident is the model in each domain?)
        self.confidence_estimator = nn.Sequential(
            nn.Linear(d_model, d_model // 4),
            nn.ReLU(),
            nn.Linear(d_model // 4, num_domains),
            nn.Sigmoid(),
        )

    def forward(self, state: torch.Tensor) -> dict[str, torch.Tensor]:
        """Produce metacognitive lacunarity report.

        Args:
            state: Hidden state (batch, seq, d_model) or (batch, d_model)

        Returns:
            Dict with 'lacunarity' (batch, 5), 'gap_map' (batch, 40),
            'domain_confidence' (batch, 4)
        """
        # Pool across sequence if needed
        pooled = state.mean(dim=-2) if state.dim() > 2 else state

        lacunarity_scores = self.lacunarity_predictor(pooled)
        gap_map = self.gap_detector(pooled)
        domain_confidence = self.confidence_estimator(pooled)

        return {
            "lacunarity": lacunarity_scores,
            "gap_map": gap_map,
            "domain_confidence": domain_confidence,
        }
