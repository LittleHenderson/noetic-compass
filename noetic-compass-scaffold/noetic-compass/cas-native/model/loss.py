"""
CognitiveMetricLoss: Multi-component loss function using the Fisher-Rao
geodesic distance on the open probability simplex.

CORRECTION 4: Fisher-Rao geodesic distance:
  d(p, q) = 2 * arccos(clamp(sum(sqrt(pk * qk)), -1, 1))

Multi-component loss:
  L = L_lm + lam1*L_operator_balance + lam2*L_domain_coherence
    + lam3*L_rpm_satisfaction + lam4*L_inversion_penalty
    + lam5*L_cognitive_metric_drift

Components:
  L_operator_balance:      penalizes involution pair gaps > 4
  L_domain_coherence:      penalizes DCI (min/max domain avg) < 0.7
  L_rpm_satisfaction:      penalizes broken prerequisite chains
  L_inversion_penalty:     sum of detected inversion scores
  L_cognitive_metric_drift: Fisher-Rao distance from target alignment
"""

import torch
import torch.nn as nn

from .composition import composition_loss as _composition_loss


# Involution pairs: CO-2/CO-3, CO-5/CO-6, CO-8/CO-9
INVOLUTION_PAIRS = [(2, 3), (5, 6), (8, 9)]

# Domain indices in the 40-state vector
DOMAIN_SLICES = {
    "P": slice(0, 10),
    "C": slice(10, 20),
    "E": slice(20, 30),
    "O": slice(30, 40),
}


def fisher_rao_distance(p: torch.Tensor, q: torch.Tensor) -> torch.Tensor:
    """Compute Fisher-Rao geodesic distance on the open probability simplex.

    d(p, q) = 2 * arccos(clamp(sum(sqrt(pk * qk)), -1, 1))

    Args:
        p: Probability vectors of shape (..., K) on the open simplex
        q: Probability vectors of shape (..., K) on the open simplex

    Returns:
        Distance tensor of shape (...), one distance per vector pair
    """
    original_dtype = p.dtype

    # Compute in float64 to keep d(p, p) numerically pinned at zero.
    p_safe = torch.clamp(p.double(), min=1e-12)
    q_safe = torch.clamp(q.double(), min=1e-12)

    # Bhattacharyya coefficient: sum(sqrt(pk * qk))
    bc = (torch.sqrt(p_safe * q_safe)).sum(dim=-1)

    # Clamp for numerical stability before arccos
    bc = torch.clamp(bc, 0.0, 1.0)
    bc = torch.where(
        torch.abs(1.0 - bc) < 1e-7,
        torch.ones_like(bc),
        bc,
    )

    return (2.0 * torch.arccos(bc)).to(original_dtype)


class CognitiveMetricLoss(nn.Module):
    """Multi-component loss for CAS-Native training.

    Combines standard language modeling loss with CAS-specific losses
    that enforce cognitive architecture constraints.
    """

    def __init__(
        self,
        lambda_operator_balance: float = 1.0,
        lambda_domain_coherence: float = 1.0,
        lambda_rpm_satisfaction: float = 1.0,
        lambda_inversion_penalty: float = 1.0,
        lambda_cognitive_drift: float = 1.0,
        lambda_composition: float = 0.5,
        involution_gap_threshold: float = 4.0,
        dci_threshold: float = 0.7,
    ):
        super().__init__()
        self.lambda_operator_balance = lambda_operator_balance
        self.lambda_domain_coherence = lambda_domain_coherence
        self.lambda_rpm_satisfaction = lambda_rpm_satisfaction
        self.lambda_inversion_penalty = lambda_inversion_penalty
        self.lambda_cognitive_drift = lambda_cognitive_drift
        self.lambda_composition = lambda_composition
        self.involution_gap_threshold = involution_gap_threshold
        self.dci_threshold = dci_threshold

        # Standard LM loss
        self.lm_loss_fn = nn.CrossEntropyLoss()

    def compute_operator_balance_loss(self, cognitive_state: torch.Tensor) -> torch.Tensor:
        """Penalize involution pair (CO-2/3, CO-5/6, CO-8/9) gaps > threshold.

        The cognitive_state has 40 dims: for each domain (P/C/E/O), positions
        0-9 correspond to CO-0 through CO-9. We average across domains.
        """
        loss = torch.tensor(0.0, device=cognitive_state.device, dtype=cognitive_state.dtype)

        for co_a, co_b in INVOLUTION_PAIRS:
            # Average the operator score across all 4 domains
            # Domain d has operators at positions d*10 + operator_idx
            scores_a = torch.stack([
                cognitive_state[..., d * 10 + co_a] for d in range(4)
            ], dim=-1).mean(dim=-1)

            scores_b = torch.stack([
                cognitive_state[..., d * 10 + co_b] for d in range(4)
            ], dim=-1).mean(dim=-1)

            gap = torch.abs(scores_a - scores_b)
            # Penalize when gap exceeds threshold (scaled by 10 for significance)
            penalty = torch.relu(gap - self.involution_gap_threshold / 10.0)
            loss = loss + penalty.mean()

        return loss

    def compute_domain_coherence_loss(self, cognitive_state: torch.Tensor) -> torch.Tensor:
        """Penalize DCI (min domain avg / max domain avg) below threshold.

        DCI = weakest_domain_average / strongest_domain_average
        """
        domain_avgs = []
        for domain_name, slc in DOMAIN_SLICES.items():
            domain_avg = cognitive_state[..., slc].mean(dim=-1)
            domain_avgs.append(domain_avg)

        # Stack domain averages: (batch, ..., 4)
        domain_avgs = torch.stack(domain_avgs, dim=-1)

        # DCI = min / max (per sample)
        min_avg = domain_avgs.min(dim=-1).values
        max_avg = domain_avgs.max(dim=-1).values

        # Avoid division by zero
        dci = min_avg / (max_avg + 1e-8)

        # Penalize DCI below threshold
        penalty = torch.relu(self.dci_threshold - dci)
        return penalty.mean()

    def compute_rpm_satisfaction_loss(
        self, satisfaction_dict: dict[str, torch.Tensor]
    ) -> torch.Tensor:
        """Penalize broken prerequisite chains.

        Loss = 1 - mean(satisfaction across all gates)
        """
        if not satisfaction_dict:
            return torch.tensor(0.0)

        all_sats = []
        for name, sat in satisfaction_dict.items():
            all_sats.append(sat.mean())

        mean_sat = torch.stack(all_sats).mean()
        return 1.0 - mean_sat

    def compute_inversion_penalty(self, inversion_scores: torch.Tensor) -> torch.Tensor:
        """Sum of detected inversion scores.

        Args:
            inversion_scores: Tensor of shape (batch, 7) for the 7 inversion axes
        """
        return inversion_scores.sum(dim=-1).mean()

    def compute_cognitive_drift_loss(
        self,
        cognitive_state: torch.Tensor,
        target_state: torch.Tensor,
    ) -> torch.Tensor:
        """Fisher-Rao distance from target alignment.

        Uses the geodesic distance on the open probability simplex.
        """
        return fisher_rao_distance(cognitive_state, target_state).mean()

    @staticmethod
    def compute_composition_loss(
        predicted_op: torch.Tensor,
        op_idx_a: torch.Tensor,
        op_idx_b: torch.Tensor,
    ) -> torch.Tensor:
        """Monoid composition loss: penalizes when model's composed operator
        doesn't match (a + b) mod 10."""
        return _composition_loss(predicted_op, op_idx_a, op_idx_b)

    def forward(
        self,
        logits: torch.Tensor,
        targets: torch.Tensor,
        cognitive_state: torch.Tensor,
        target_cognitive_state: torch.Tensor,
        rpm_satisfaction: dict[str, torch.Tensor],
        inversion_scores: torch.Tensor,
    ) -> tuple[torch.Tensor, dict[str, torch.Tensor]]:
        """Compute the composite loss.

        Args:
            logits: LM logits (batch, seq, vocab)
            targets: Target token ids (batch, seq)
            cognitive_state: Predicted cognitive state (batch, seq, 40) on simplex
            target_cognitive_state: Target cognitive state (batch, seq, 40) on simplex
            rpm_satisfaction: Dict of gate satisfaction tensors
            inversion_scores: Inversion detection scores (batch, 7)

        Returns:
            Tuple of (total_loss, component_dict) where component_dict maps
            names to individual loss scalars.
        """
        # LM loss
        lm_loss = self.lm_loss_fn(
            logits.reshape(-1, logits.size(-1)),
            targets.reshape(-1),
        )

        # CAS-specific losses
        # Average cognitive state across sequence for per-sample metrics
        cog_avg = cognitive_state.mean(dim=1)  # (batch, 40)
        target_avg = target_cognitive_state.mean(dim=1)

        l_operator = self.compute_operator_balance_loss(cog_avg)
        l_domain = self.compute_domain_coherence_loss(cog_avg)
        l_rpm = self.compute_rpm_satisfaction_loss(rpm_satisfaction)
        l_inversion = self.compute_inversion_penalty(inversion_scores)
        l_drift = self.compute_cognitive_drift_loss(cog_avg, target_avg)

        # Composite loss
        total = (
            lm_loss
            + self.lambda_operator_balance * l_operator
            + self.lambda_domain_coherence * l_domain
            + self.lambda_rpm_satisfaction * l_rpm
            + self.lambda_inversion_penalty * l_inversion
            + self.lambda_cognitive_drift * l_drift
        )

        components = {
            "lm_loss": lm_loss,
            "operator_balance": l_operator,
            "domain_coherence": l_domain,
            "rpm_satisfaction": l_rpm,
            "inversion_penalty": l_inversion,
            "cognitive_drift": l_drift,
            "total": total,
        }

        return total, components
