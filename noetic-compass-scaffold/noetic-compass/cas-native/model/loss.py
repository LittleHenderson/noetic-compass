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
import torch.nn.functional as F

from .composition import composition_loss as _composition_loss
from .register_film import (
    INVOLUTION_REGISTER_PAIRS,
    REGISTER_INDEX,
    RegisterFiLM,
    RegisterLatent,
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
        source: Union[RegisterFiLM, RegisterLatent, tuple[torch.Tensor, torch.Tensor]],
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Normalize the loss input to a (gamma, beta) tensor pair.

        Accepts the legacy ``RegisterFiLM`` (direct parameter access), the
        ADR-08 ``RegisterLatent`` (reads the 40-dim simplex FiLM surface via
        ``compute_gamma_beta_40``), or an explicit tensor tuple.
        """
        if isinstance(source, RegisterFiLM):
            return source.gamma, source.beta
        if isinstance(source, RegisterLatent):
            # Default surface is the 40-dim simplex FiLM; callers wanting
            # the d_model surface should pass the tuple directly via
            # ``source.compute_gamma_beta_d()``.
            return source.compute_gamma_beta_40()
        if isinstance(source, tuple) and len(source) == 2:
            return source[0], source[1]
        raise TypeError(
            "InvolutionConstraintLoss expects a RegisterFiLM / RegisterLatent "
            "instance or a (gamma, beta) tensor tuple; got "
            "{type!r}".format(type=type(source))
        )

    def involution_loss(
        self,
        source: Union[RegisterFiLM, RegisterLatent, tuple[torch.Tensor, torch.Tensor]],
    ) -> torch.Tensor:
        """Compute the soft involution constraint loss.

        Args:
            source: A RegisterFiLM module, a RegisterLatent module (reads
                the 40-dim simplex FiLM surface), or a (gamma, beta) tensor
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
        source: Union[RegisterFiLM, RegisterLatent, tuple[torch.Tensor, torch.Tensor]],
    ) -> torch.Tensor:
        return self.involution_loss(source)


class ProposerRuleFourLoss(nn.Module):
    """Score-based loss for the learned ExpressionProposerHead (ADR-07).

    Closes the gradient-flow gap identified by Codex 5.4: the legacy
    ``_compute_rule_four_loss`` in ``training/trainer.py`` built expression
    operands from labels (not model outputs) and wrapped the Rust-returned
    distances in a fresh ``torch.tensor`` with ``requires_grad=False``. The
    legacy loss was therefore a metric, not a training signal.

    This loss consumes the five parallel logit heads emitted by
    ``ExpressionProposerHead.forward`` and compares each to a
    label-derived target. Because the logits are produced by a linear
    projection of ``hidden_states``, the loss is gradient-bearing to every
    component upstream of the proposer input (token embedding, transformer
    layers, final norm).

    Components:

        L_noetic       — cross-entropy on noetic_logits         (B, 10)
        L_domain       — cross-entropy on domain_logits         (B,  4)
        L_register     — cross-entropy on register_logits       (B, M, 4)
                         masked by operand-slot presence
        L_count        — smooth-L1 on soft-argmax of operand_count_logits
                         vs target count
        L_named_emg    — cross-entropy on named_emergent_logits (B,  2)

        L = w_n * L_noetic + w_d * L_domain
          + w_r * L_register + w_c * L_count
          + w_e * L_named_emg

    Default component weights (all 1.0) are passed through from the
    trainer's ``V2Hyperparameters.lambda_proposer_*`` fields, and the
    outer ``lambda_proposer_rule_four`` applies in the trainer's loss
    aggregation (see ``_compute_proposer_rule_four_loss``).

    All five components are per-example-masked: examples missing a given
    label stream contribute zero to that component but still contribute to
    the others when their labels are present. ``None`` is returned only
    when NO example in the batch has any proposer-trainable label.

    Args:
        lambda_noetic: weight on the Noetic CE head (default 1.0).
        lambda_domain: weight on the Domain CE head (default 1.0).
        lambda_register: weight on the per-operand Register CE head
            (default 1.0).
        lambda_count: weight on the operand-count smooth-L1 head
            (default 0.5, lower than CE heads — count carries less
            per-batch signal than per-operand registers).
        lambda_named_emergent: weight on the named-emergent CE head
            (default 1.0).
    """

    def __init__(
        self,
        lambda_noetic: float = 1.0,
        lambda_domain: float = 1.0,
        lambda_register: float = 1.0,
        lambda_count: float = 0.5,
        lambda_named_emergent: float = 1.0,
    ) -> None:
        super().__init__()
        self.lambda_noetic = float(lambda_noetic)
        self.lambda_domain = float(lambda_domain)
        self.lambda_register = float(lambda_register)
        self.lambda_count = float(lambda_count)
        self.lambda_named_emergent = float(lambda_named_emergent)

    def forward(
        self,
        proposer_out: dict[str, torch.Tensor],
        *,
        noetic_targets: Optional[torch.Tensor] = None,
        domain_targets: Optional[torch.Tensor] = None,
        register_targets: Optional[torch.Tensor] = None,
        register_target_mask: Optional[torch.Tensor] = None,
        operand_count_targets: Optional[torch.Tensor] = None,
        named_emergent_targets: Optional[torch.Tensor] = None,
    ) -> Optional[torch.Tensor]:
        """Compute the weighted sum of the five components.

        Each ``*_targets`` argument is an index tensor (LongTensor) or
        ``None`` when the label is absent for every example. When
        ``register_targets`` is present, ``register_target_mask`` MUST be
        supplied — a ``(B, M)`` bool mask marking which operand slots
        carry a register label (shorter expressions have unmasked tails
        that are excluded from the CE).

        Returns:
            Scalar loss tensor, or ``None`` when every component's target
            is ``None``.
        """
        components: list[torch.Tensor] = []

        # Noetic CE.
        if noetic_targets is not None and noetic_targets.numel() > 0:
            noetic_logits = proposer_out["noetic_logits"]
            # Per-example selection: noetic_targets has shape (K,) where
            # K <= B. Caller supplies the matched subset via indexing.
            ce = F.cross_entropy(noetic_logits, noetic_targets)
            components.append(self.lambda_noetic * ce)

        # Domain CE.
        if domain_targets is not None and domain_targets.numel() > 0:
            domain_logits = proposer_out["domain_logits"]
            ce = F.cross_entropy(domain_logits, domain_targets)
            components.append(self.lambda_domain * ce)

        # Per-operand Register CE — operand-slot masked.
        if (
            register_targets is not None
            and register_targets.numel() > 0
            and register_target_mask is not None
        ):
            register_logits = proposer_out["register_logits"]  # (B, M, R)
            B, M, R = register_logits.shape
            # Flatten (B, M, R) to (B*M, R) and (B, M) mask to (B*M,).
            flat_logits = register_logits.reshape(B * M, R)
            flat_targets = register_targets.reshape(B * M)
            flat_mask = register_target_mask.reshape(B * M)
            if flat_mask.any():
                masked_logits = flat_logits[flat_mask]
                masked_targets = flat_targets[flat_mask]
                ce = F.cross_entropy(masked_logits, masked_targets)
                components.append(self.lambda_register * ce)

        # Operand-count smooth-L1 on the soft-argmax of the logits.
        #
        # Cross-entropy would work too, but the count axis is ordinal
        # (a proposal of 3 operands is closer to 4 than to 0), so smooth-L1
        # on the soft-argmax respects the ordering while remaining fully
        # differentiable.
        if (
            operand_count_targets is not None
            and operand_count_targets.numel() > 0
        ):
            count_logits = proposer_out["operand_count_logits"]  # (B, K)
            K = count_logits.shape[-1]
            probs = F.softmax(count_logits, dim=-1)
            bucket_idx = torch.arange(
                K, device=count_logits.device, dtype=count_logits.dtype
            )
            soft_argmax = (probs * bucket_idx.unsqueeze(0)).sum(dim=-1)
            target_f = operand_count_targets.to(count_logits.dtype)
            sl1 = F.smooth_l1_loss(soft_argmax, target_f)
            components.append(self.lambda_count * sl1)

        # Named-emergent binary CE.
        if (
            named_emergent_targets is not None
            and named_emergent_targets.numel() > 0
        ):
            named_logits = proposer_out["named_emergent_logits"]  # (B, 2)
            ce = F.cross_entropy(named_logits, named_emergent_targets)
            components.append(self.lambda_named_emergent * ce)

        if not components:
            return None

        return torch.stack(components).sum()


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


class NullSpaceRegularizationLoss(nn.Module):
    """Pull unused Omega_* registry slots toward a null point in ER-space.

    Unused registry slots (v1 has k=2 admitted and 18 unused in a capacity-20
    table) receive minimal gradient during training — no training label ever
    lands on them — yet they still participate in cosine-similarity comparisons
    at inference. Without regularization those random-initialized embeddings
    drift into patterns that can accidentally match real Omega_* (false
    positives). This loss is the ADR-03 follow-up: pull unused embeddings
    toward a "null" point so they remain cleanly separated from admitted
    emergent registers.

    Null-point strategies (all supported; choose via ``strategy`` kwarg):

      - ``"origin"`` — pull unused embeddings toward the zero vector. Simplest,
        introduces zero additional parameters, aligns directly with "pull
        toward null" semantics. **Default**, chosen as the v1 strategy per
        ADR-03 Section 'Training signal' follow-up.
      - ``"learned_anchor"`` — pull unused embeddings toward a learned anchor
        parameter (one d_model vector). Slightly more flexible — the anchor
        can drift to the region of ER-space least occupied by admitted
        Omega_*; paid for with d_model extra parameters.
      - ``"mean_inactive"`` — pull unused embeddings toward the mean of unused
        embeddings (collective centering — softer, doesn't force any
        particular direction). No extra parameters but weaker separation
        guarantee from admitted slots.

    The v1 default ``"origin"`` rationale: the simplest well-defined target,
    no extra parameters, and alignment with "pull toward null" semantics.
    The other strategies remain available for future tuning once empirical
    evidence from training runs motivates a more sophisticated anchor.

    Formula (for ``strategy == "origin"``):

        L_null = lambda_null * (1 / unused_count) * sum_i ||registry[i]||^2

    where the sum runs over unused slot indices. When ``unused_count == 0``
    (registry fully saturated) the loss is zero.

    Args:
        strategy: Null-point strategy — one of
            ``{"origin", "learned_anchor", "mean_inactive"}``.
        lambda_null: Scalar weight on the regularizer. Default ``0.01`` —
            low weight; this is regularization only, not a primary training
            signal.
        d_model: Required only for ``strategy == "learned_anchor"`` (used to
            size the learned anchor parameter).
    """

    _VALID_STRATEGIES = ("origin", "learned_anchor", "mean_inactive")

    def __init__(
        self,
        strategy: str = "origin",
        lambda_null: float = 0.01,
        d_model: Optional[int] = None,
    ) -> None:
        super().__init__()
        if strategy not in self._VALID_STRATEGIES:
            raise ValueError(
                f"Unknown null-space strategy {strategy!r}; "
                f"expected one of {self._VALID_STRATEGIES}"
            )
        self.strategy = strategy
        self.lambda_null = float(lambda_null)

        # Only ``learned_anchor`` introduces extra parameters — keep the
        # parameter budget at zero for ``origin`` / ``mean_inactive``.
        if strategy == "learned_anchor":
            if d_model is None:
                raise ValueError(
                    "strategy='learned_anchor' requires d_model to size the "
                    "anchor parameter"
                )
            self.anchor: Optional[nn.Parameter] = nn.Parameter(torch.zeros(d_model))
        else:
            self.anchor = None

    def forward(self, unused_embeddings: torch.Tensor) -> torch.Tensor:
        """Compute the null-space regularization loss.

        Args:
            unused_embeddings: Tensor of shape ``(unused_count, d_model)``
                holding the registry rows at unused slot indices (typically
                produced by ``OmegaRegistry.unused_slot_embeddings()``).

        Returns:
            Scalar tensor ``lambda_null * mean(||embedding_i - target||^2)``.
            Zero (as a tensor) when ``unused_count == 0``.
        """
        if unused_embeddings.numel() == 0:
            return torch.zeros(
                (),
                device=unused_embeddings.device,
                dtype=unused_embeddings.dtype,
            )

        if self.strategy == "origin":
            target = torch.zeros_like(unused_embeddings)
        elif self.strategy == "learned_anchor":
            assert self.anchor is not None  # guaranteed by __init__ branch
            # Broadcast the learned anchor against every unused row.
            target = self.anchor.unsqueeze(0).expand_as(unused_embeddings)
        elif self.strategy == "mean_inactive":
            # Pull every unused row toward the mean of unused rows — a soft
            # centering; detach() keeps the mean from acting as a free moving
            # target that would trivially minimize the loss.
            mean = unused_embeddings.mean(dim=0, keepdim=True).detach()
            target = mean.expand_as(unused_embeddings)
        else:  # pragma: no cover - guarded by __init__ validation
            raise AssertionError(f"unreachable strategy {self.strategy}")

        sq_err = (unused_embeddings - target).pow(2).sum(dim=-1)  # (unused_count,)
        return self.lambda_null * sq_err.mean()


# ---------------------------------------------------------------------------
# ADR-08 Option E — Latent-Level Involution Loss
# ---------------------------------------------------------------------------


class LatentInvolutionLoss(nn.Module):
    """Option E involution loss over a shared :class:`RegisterLatent` module.

    Under ADR-08, register identity is a single per-register latent vector
    ``z_R``; the two FiLM surfaces (gamma_40/beta_40 and gamma_d/beta_d) are
    projections of that latent via learned linear heads. This loss enforces
    the T <-> E and A <-> f involution relation at two levels:

    * **Latent-level** (``L_inv_latent``) — asserts involution partners are
      additive inverses in latent space::

          L_inv_latent = mean((z_T + z_E)^2) + mean((z_A + z_f)^2)

      When z_T = -z_E exactly and the W heads are linear (which they are
      by construction), the gamma/beta outputs are automatically involution
      partners at both FiLM surfaces — the output-surface terms become
      redundant. Latent-level enforcement is cleaner and lower-dim than
      enforcing at both output surfaces.

    * **Output-surface** (``L_inv_output``) — enforces the involution at
      the surfaces themselves, dimension-normalized so the 40-surface and
      d_model-surface terms stay scale-comparable even when d_model changes::

          L_inv_output =
                mean((gamma_40,T * gamma_40,E - 1)^2)
              + mean((beta_40,T + beta_40,E)^2)
              + mean((gamma_40,A * gamma_40,f - 1)^2)
              + mean((beta_40,A + beta_40,f)^2)
              + mean((gamma_d,T  * gamma_d,E  - 1)^2)
              + mean((beta_d,T  + beta_d,E )^2)
              + mean((gamma_d,A  * gamma_d,f  - 1)^2)
              + mean((beta_d,A  + beta_d,f )^2)

    The aggregate is::

        L_involution_total = lambda_out * L_inv_output
                           + lambda_latent * L_inv_latent

    Defaults per ADR-08: ``lambda_out = 0.1`` (matches the legacy
    ``InvolutionConstraintLoss`` default), ``lambda_latent = 0.01``.

    At initialization: z_R ~ N(0,1) so ``z_T + z_E`` is nonzero on average,
    but the W_* matrices are zero-initialized — gamma = 1, beta = 0 exactly
    at all surfaces. So ``L_inv_output`` is zero at init while
    ``L_inv_latent`` is nonzero (a small but nonzero regularization signal
    at step 0). This is intentional: the latent-level term carries the
    primary involution pressure during training, while the output-surface
    term is a belt-and-braces redundancy that goes to zero automatically
    once the latent-level constraint is satisfied.

    Args:
        lambda_out: Scalar weight on the output-surface term. Default 0.1.
        lambda_latent: Scalar weight on the latent-level term. Default 0.01.
        involution_pairs: Optional override for the (idx_a, idx_b) pair list.
            Defaults to the authoritative pairs T<->E, A<->f from
            ``register_film.INVOLUTION_REGISTER_PAIRS``.
    """

    def __init__(
        self,
        lambda_out: float = 0.1,
        lambda_latent: float = 0.01,
        involution_pairs: Optional[list[tuple[int, int]]] = None,
    ) -> None:
        super().__init__()
        self.lambda_out = float(lambda_out)
        self.lambda_latent = float(lambda_latent)
        self.involution_pairs = (
            list(involution_pairs)
            if involution_pairs is not None
            else list(INVOLUTION_REGISTER_PAIRS)
        )

    # ---------------------------------------------------------------- latent

    def latent_term(self, latent: RegisterLatent) -> torch.Tensor:
        """Compute ``L_inv_latent = sum over pairs mean((z_a + z_b)^2)``."""
        z = latent.register_latent  # (R, latent_dim_r)
        total = torch.zeros((), device=z.device, dtype=z.dtype)
        for idx_a, idx_b in self.involution_pairs:
            total = total + ((z[idx_a] + z[idx_b]) ** 2).mean()
        return total

    # --------------------------------------------------------------- surface

    def output_surface_term(self, latent: RegisterLatent) -> torch.Tensor:
        """Compute ``L_inv_output`` across both 40-dim and d_model FiLMs.

        Uses ``.mean()`` per dimension so the 40-wide and d_model-wide
        surfaces stay scale-comparable under differing ``d_model`` values.
        """
        gamma40, beta40 = latent.compute_gamma_beta_40()
        gammad, betad = latent.compute_gamma_beta_d()

        total = torch.zeros((), device=gamma40.device, dtype=gamma40.dtype)
        for idx_a, idx_b in self.involution_pairs:
            # 40-dim simplex surface.
            g40_prod = gamma40[idx_a] * gamma40[idx_b] - 1.0
            b40_sum = beta40[idx_a] + beta40[idx_b]
            total = total + (g40_prod ** 2).mean() + (b40_sum ** 2).mean()
            # d_model surface.
            gd_prod = gammad[idx_a] * gammad[idx_b] - 1.0
            bd_sum = betad[idx_a] + betad[idx_b]
            total = total + (gd_prod ** 2).mean() + (bd_sum ** 2).mean()
        return total

    # ------------------------------------------------------------- aggregate

    def forward(
        self,
        latent: RegisterLatent,
        return_components: bool = False,
    ) -> Union[torch.Tensor, tuple[torch.Tensor, dict[str, torch.Tensor]]]:
        """Compute the aggregate latent-involution loss.

        Args:
            latent: The shared :class:`RegisterLatent` module.
            return_components: If True, also return a dict with the two
                unweighted sub-terms under keys ``"l_inv_output"`` and
                ``"l_inv_latent"`` (useful for diagnostic logging).

        Returns:
            Scalar loss ``lambda_out * L_inv_output + lambda_latent * L_inv_latent``,
            optionally paired with the components dict.
        """
        l_out = self.output_surface_term(latent)
        l_latent = self.latent_term(latent)
        total = self.lambda_out * l_out + self.lambda_latent * l_latent
        if return_components:
            return total, {
                "l_inv_output": l_out.detach(),
                "l_inv_latent": l_latent.detach(),
            }
        return total
