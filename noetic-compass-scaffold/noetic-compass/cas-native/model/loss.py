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

from typing import Optional, Union

import torch
import torch.nn as nn

from .composition import composition_loss as _composition_loss
from .register_film import (
    INVOLUTION_REGISTER_PAIRS,
    REGISTER_INDEX,
    RegisterFiLM,
)


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


class InvolutionConstraintLoss(nn.Module):
    """Soft involution constraint on RegisterFiLM parameters (ADR-01).

    Encodes the CAS v7.5 involution relation on Phenomenological Registers —
    T <-> E and A <-> f — as a SOFT regularizer, not hard architectural
    enforcement. The constraint says involution partners are multiplicative
    inverses in gamma and additive inverses in beta, so applying one register
    then its partner returns to the unmodulated state:

        L_involution = lambda * (
            || gamma_T * gamma_E - 1 ||^2 + || beta_T + beta_E ||^2 +
            || gamma_A * gamma_f - 1 ||^2 + || beta_A + beta_f ||^2
        )

    At initialization (gamma = 1, beta = 0) every term is exactly zero:
    gamma_T * gamma_E = 1 * 1 = 1 so (gamma_T * gamma_E - 1) = 0; beta_T + beta_E
    = 0 + 0 = 0. The constraint keeps register partners near their involution
    during training, modulated by lambda (default 0.1 per ADR-01).

    Args:
        lambda_involution: Scalar weight on the constraint. Default 0.1 per
            ADR-01; tunable based on training dynamics.
        involution_pairs: Optional override for the (idx_a, idx_b) pair list.
            Defaults to the authoritative pairs T<->E, A<->f from register_film.
    """

    def __init__(
        self,
        lambda_involution: float = 0.1,
        involution_pairs: Optional[list[tuple[int, int]]] = None,
    ) -> None:
        super().__init__()
        self.lambda_involution = lambda_involution
        self.involution_pairs = (
            list(involution_pairs)
            if involution_pairs is not None
            else list(INVOLUTION_REGISTER_PAIRS)
        )

    @staticmethod
    def _extract_gamma_beta(
        source: Union[RegisterFiLM, tuple[torch.Tensor, torch.Tensor]],
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if isinstance(source, RegisterFiLM):
            return source.gamma, source.beta
        if isinstance(source, tuple) and len(source) == 2:
            return source[0], source[1]
        raise TypeError(
            "InvolutionConstraintLoss expects a RegisterFiLM instance or a "
            "(gamma, beta) tensor tuple; got {type!r}".format(type=type(source))
        )

    def involution_loss(
        self,
        source: Union[RegisterFiLM, tuple[torch.Tensor, torch.Tensor]],
    ) -> torch.Tensor:
        """Compute the soft involution constraint loss.

        Args:
            source: Either a RegisterFiLM module or a (gamma, beta) tensor
                tuple with shapes (num_registers, d_model).

        Returns:
            Scalar loss tensor: lambda * sum over pairs of
            ||gamma_a * gamma_b - 1||^2 + ||beta_a + beta_b||^2.
        """
        gamma, beta = self._extract_gamma_beta(source)

        total = torch.zeros((), device=gamma.device, dtype=gamma.dtype)
        ones = torch.ones_like(gamma[0])

        for idx_a, idx_b in self.involution_pairs:
            gamma_term = gamma[idx_a] * gamma[idx_b] - ones
            beta_term = beta[idx_a] + beta[idx_b]
            total = total + (gamma_term**2).sum() + (beta_term**2).sum()

        return self.lambda_involution * total

    def forward(
        self,
        source: Union[RegisterFiLM, tuple[torch.Tensor, torch.Tensor]],
    ) -> torch.Tensor:
        return self.involution_loss(source)


class LacunarityRegularizationLoss(nn.Module):
    """Penalizes extreme concentration in the 40-slot activation vector.

    Encourages balanced cognitive architecture development during training.
    Too high lacunarity = blind spots. Too low = no specialization.
    The target represents the ideal balance point.

    Args:
        alpha: Weight of the lacunarity penalty in the total loss.
        target_lacunarity: The ideal lacunarity level to train toward.
    """

    def __init__(self, alpha: float = 0.1, target_lacunarity: float = 0.5):
        super().__init__()
        self.alpha = alpha
        self.target = target_lacunarity

    def forward(self, slot_activations: torch.Tensor) -> torch.Tensor:
        """Compute lacunarity regularization loss.

        Args:
            slot_activations: (batch, ..., 40) on the probability simplex

        Returns:
            Scalar loss penalizing deviation from target lacunarity.
        """
        # Flatten to (batch, 40) if needed
        flat = slot_activations.reshape(-1, slot_activations.shape[-1])
        mean = flat.mean(dim=-1, keepdim=True)
        var = ((flat - mean) ** 2).mean(dim=-1)
        lacunarity = var / (mean.squeeze(-1) ** 2 + 1e-8)

        loss = self.alpha * ((lacunarity - self.target) ** 2).mean()
        return loss
