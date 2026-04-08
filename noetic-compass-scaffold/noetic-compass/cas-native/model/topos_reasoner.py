"""
CognitiveToposReasoner: Implements intuitionistic reasoning with a three-valued
subobject classifier Omega = {true, false, undetermined}.

CORRECTION 3: Noetic Coverage uses COUNIT not UNIT.
  Noe-Cov-3 uses epsilon_I: R(I) -> I (toward target), NOT eta_I: I -> R(I).
  Covering morphisms point TOWARD the covered object.

In intuitionistic logic:
  - The law of excluded middle does NOT hold: p OR NOT p is not always true
  - "undetermined" is a valid truth value, NOT an error
  - This models genuine ethical uncertainty in CAS assessments

The subobject classifier Omega has three truth values:
  0 = true, 1 = false, 2 = undetermined

For each ethical proposition, the reasoner outputs a probability distribution
over these three values.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


# Truth value indices
TRUTH_TRUE = 0
TRUTH_FALSE = 1
TRUTH_UNDETERMINED = 2
NUM_TRUTH_VALUES = 3


class CognitiveToposReasoner(nn.Module):
    """Intuitionistic logic reasoner with three-valued subobject classifier.

    For each of num_propositions ethical propositions, produces a probability
    distribution over {true, false, undetermined}.

    Architecture:
      - Linear projection from d_model to proposition space
      - Per-proposition classification into 3 truth values
      - Softmax ensures valid probability distribution

    The covering morphisms point toward the covered object (CORRECTION 3),
    meaning the reasoner's output represents the degree to which evidence
    supports each truth value for a given proposition.
    """

    def __init__(self, d_model: int, num_propositions: int = 7):
        super().__init__()
        self.d_model = d_model
        self.num_propositions = num_propositions

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
