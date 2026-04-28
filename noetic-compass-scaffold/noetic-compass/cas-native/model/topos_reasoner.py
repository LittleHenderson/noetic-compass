"""
CognitiveToposReasoner: neural 3-valued proposition scorer.

What is explicit here:
  - Outputs are normalized over three labels: true / false / undetermined.
  - "Undetermined" is treated as a first-class output rather than an error.

What is not implemented here:
  - No actual sheaf, Grothendieck-topology, or internal-logic machinery is
    constructed in this module.
  - The "counit" path is naming guidance only; it is a learned linear layer,
    not a categorical proof object.

This module is therefore a neural proxy for 3-valued assessment, not a literal
implementation of a topos' internal logic.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


# Truth value indices
TRUTH_TRUE = 0
TRUTH_FALSE = 1
TRUTH_UNDETERMINED = 2
NUM_TRUTH_VALUES = 3

TOPOS_PROPOSITION_LABELS = (
    "typed_membership",
    "typed_subset",
    "finite_union",
    "finite_intersection",
    "finite_relative_complement",
    "pullback_as_finite_meet",
    "cover_or_partition",
)


class CognitiveToposReasoner(nn.Module):
    """Neural 3-valued proposition classifier.

    The probabilistic 3-valued output is explicit. Any stronger "topos"
    interpretation should be treated as an external modeling claim rather than
    something proven by this module alone.
    """

    def __init__(
        self,
        d_model: int,
        num_propositions: int = 7,
        proposition_labels: tuple[str, ...] | None = None,
    ):
        super().__init__()
        self.d_model = d_model
        self.num_propositions = num_propositions
        self.proposition_labels = (
            tuple(proposition_labels)
            if proposition_labels is not None
            else TOPOS_PROPOSITION_LABELS[:num_propositions]
        )

        # Project from model dimension to proposition representations
        self.proposition_proj = nn.Linear(d_model, num_propositions * d_model)

        # Per-proposition truth-value classifier
        # Each proposition gets its own classifier to allow independent reasoning
        self.truth_classifiers = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model, d_model // 4),
                nn.GELU(),
                nn.Linear(d_model // 4, NUM_TRUTH_VALUES),
            )
            for _ in range(num_propositions)
        ])

        # Counit path (epsilon): toward the covered object (CORRECTION 3)
        # Maps from the enriched representation back toward concrete truth values
        self.counit = nn.Linear(d_model, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Input tensor of shape (batch, seq, d_model) or (batch, d_model)

        Returns:
            Truth value probabilities of shape (batch, num_propositions, 3)
            where the 3 values represent P(true), P(false), P(undetermined)
        """
        # If sequence dimension exists, pool across it
        if x.dim() == 3:
            x = x.mean(dim=1)  # (batch, d_model)

        # Apply counit: project toward the covered object (CORRECTION 3)
        x = self.counit(x)

        # Project to proposition space
        batch = x.shape[0]
        prop_repr = self.proposition_proj(x)  # (batch, num_propositions * d_model)
        prop_repr = prop_repr.view(batch, self.num_propositions, self.d_model)

        # Classify each proposition into truth values
        truth_logits = []
        for i, classifier in enumerate(self.truth_classifiers):
            logits_i = classifier(prop_repr[:, i, :])  # (batch, 3)
            truth_logits.append(logits_i)

        # Stack: (batch, num_propositions, 3)
        truth_logits = torch.stack(truth_logits, dim=1)

        # Softmax over truth values to get valid probability distribution
        truth_probs = F.softmax(truth_logits, dim=-1)

        return truth_probs
