"""ExpressionProposerHead: learned head that proposes structured CAS v7.7
expressions from model hidden states (ADR-07).

Closes the gradient-flow gap identified by Codex 5.4 in the Wave 7B panel
review. The existing ``_compute_rule_four_loss`` in ``training/trainer.py``
is not gradient-bearing w.r.t. model weights: it builds expression operands
from ground-truth **labels** (not model outputs) and wraps the Rust-returned
Python floats in a fresh ``torch.tensor(..., requires_grad=False)``. As a
result, ``rule_four_loss`` appears in the total-loss scalar but its
backward pass touches no model parameters.

ADR-07 closes that gap with a learned expression proposer that emits a
structured expression proposal per example. The proposer's parameters are
the actual training signal — its outputs are compared to derived label
distributions (Option A — score-based), and the resulting cross-entropy +
smooth-L1 loss is gradient-bearing to every component upstream of the
proposer's input (hidden states). The Rust validator remains authoritative
at inference / evaluation; at training it is NOT on the gradient path.

Design choice — Option A (score-based) over Option B (REINFORCE-lite):

* Option A: proposer outputs scored directly against label distributions
  (noetic CE, domain CE, per-operand register CE, operand-count smooth L1,
  named-emergent binary CE). Gradient path: hidden_states → proposer
  logits → loss → backward. Simpler, lower variance, closes the gap.
* Option B: proposer output discretized via Gumbel-softmax ST, fed to Rust,
  distance used as negative reward. More principled but higher variance
  and requires Rust at every training step. Deferred to v2 of ADR-07.

Option A was chosen for v1 because it closes the wiring gap with the
minimum viable architectural surface; Option B remains available as an
upgrade path if Rust-validated distance turns out to carry signal
orthogonal to the score-based CE.

Proposer head structure:

* Input: pooled hidden states of shape ``(B, d_model)``. The proposer
  accepts either pooled (2-D) or per-position (3-D, ``(B, seq_len, d_model)``)
  tensors — 3-D inputs are mean-pooled over the sequence axis.
* Five parameter heads:
  - ``noetic_logits`` — (B, 10) over the 10 Noetics (CO-0 … CO-9)
  - ``domain_logits`` — (B, 4) over the 4 Domains (P, C, E, O)
  - ``register_logits_per_operand`` — (B, max_operands, 4) over the 4 Registers
    (T, A, f, E) per operand slot
  - ``operand_count_logits`` — (B, 5) over {0, 1, 2, 3, 4} operand counts
    (count 1 is trivially valid → no Rule 4 signal, but remains in the
    distribution for proposer coverage)
  - ``named_emergent_logits`` — (B, 2) binary "is an emergent result named"
* Shared low-rank backbone: ``d_model → bottleneck → five parallel heads``.
  Bottleneck dim keeps the parameter budget near the ADR-07 target.

Parameter budget target (v1): ~20-50K per ADR-07 Implementation Notes.
Actual count at ``d_model=128, bottleneck=32, max_operands=4``:
    backbone:    128 * 32 + 32                      =  4,128
    noetic:       32 * 10 + 10                      =    330
    domain:       32 *  4 +  4                      =    132
    register:     32 * (4 * 4) + (4 * 4)            =    528
    op_count:     32 *  5 +  5                      =    165
    named_emg:    32 *  2 +  2                      =     66
    ------------------------------------------------------
    TOTAL                                            ≈  5,349

At ``d_model=512`` the backbone scales to 16,416, total ≈ 17,637.
The larger ~50K figure in the ADR is the upper bound at d_model=512
with a 64-dim bottleneck and max_operands=5 (full head sweep).

Training / inference modes:

* Training (``mode="training"``): Gumbel-softmax discretization on the
  per-operand register logits for downstream Option-B compatibility. The
  **loss** in v1 uses the raw logits (not the Gumbel samples), so the
  discretization is a decorative no-op at training time — preserved so
  Option B can flip the switch without re-plumbing the head.
* Inference (``mode="inference"``): argmax on every head; emits a
  structured proposal suitable for Rust validation.

Backward compatibility: the proposer is gated by
``V2ComponentFlags.use_expression_proposer`` (default False). When False,
the proposer is never instantiated, no loss is added, and model behaviour
is byte-equivalent to the pre-ADR-07 Wave 7B state.

Reference: ``docs/architecture/cas_native_v2_adrs.md`` ADR-07.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

from .register_film import NUM_REGISTERS


__all__ = [
    "ExpressionProposerHead",
    "ExpressionProposal",
    "NUM_NOETICS",
    "NUM_DOMAINS",
    "DEFAULT_MAX_OPERANDS",
    "DEFAULT_BOTTLENECK_DIM",
    "OPERAND_COUNT_BUCKETS",
]


# Public constants -----------------------------------------------------------
NUM_NOETICS: int = 10
NUM_DOMAINS: int = 4
DEFAULT_MAX_OPERANDS: int = 4
DEFAULT_BOTTLENECK_DIM: int = 32

# Operand-count buckets. Index i corresponds to count == i, so argmax
# directly yields the predicted operand count. Count 0 == "no expression
# proposed", count 1 == trivially valid (single operand, no Rule 4 signal).
OPERAND_COUNT_BUCKETS: tuple[int, ...] = (0, 1, 2, 3, 4)


@dataclass(frozen=True)
class ExpressionProposal:
    """Discretized output of the ExpressionProposerHead.

    Produced at inference (mode="inference") via argmax on every head.
    Fields align 1:1 with the Rust bridge's ``StructuralPattern`` /
    ``rule_four_distance_batch`` input shape, so a downstream caller can
    pass the proposal straight to the validator with no conversion.

    Attributes:
        noetic: integer in ``[0, 10)`` — the single Noetic the proposal
            asserts across every operand.
        domain: integer in ``[0, 4)`` — the Domain the proposal asserts
            across every operand (0=P, 1=C, 2=E, 3=O).
        registers_per_operand: tuple of register indices, one per operand,
            each in ``[0, 4)``. Length == ``operand_count``.
        operand_count: integer in ``OPERAND_COUNT_BUCKETS``.
        has_named_emergent: whether the proposal names an emergent result.
            Rule 4 admits ``× (multi-register)`` only when this is True OR
            the register set contains at most one register.
    """

    noetic: int
    domain: int
    registers_per_operand: tuple[int, ...]
    operand_count: int
    has_named_emergent: bool


class ExpressionProposerHead(nn.Module):
    """Learned expression proposer — Option A (score-based) variant.

    Consumes hidden states from the CAS-Native model and emits five
    parallel logit heads describing a CAS v7.7 structural expression. The
    heads are trained against label-derived target distributions, giving
    the Rule 4 training path a real gradient-bearing signal.

    Args:
        d_model: input hidden dim (expected to match
            ``CASNativeConfig.d_model``).
        bottleneck_dim: width of the shared bottleneck between hidden
            state and the five parallel heads. Default 32.
        max_operands: number of per-operand register slots the head
            predicts over. Default 4 (the v7.7 maximum for Rule 4).
        num_noetics: size of the noetic head output. Default 10.
        num_domains: size of the domain head output. Default 4.
        num_registers: size of the per-operand register head. Default
            ``NUM_REGISTERS`` (= 4).
        operand_count_buckets: tuple of operand counts the head
            discretizes over. Default ``OPERAND_COUNT_BUCKETS`` (0..4).

    Shape:
        hidden_states: ``(B, d_model)`` or ``(B, seq_len, d_model)`` —
            3-D inputs are mean-pooled over the sequence axis.

    Returns from forward:
        dict with keys:
          - noetic_logits: ``(B, num_noetics)``
          - domain_logits: ``(B, num_domains)``
          - register_logits: ``(B, max_operands, num_registers)``
          - operand_count_logits: ``(B, len(operand_count_buckets))``
          - named_emergent_logits: ``(B, 2)``

    Parameter budget: see module docstring. At defaults (d_model=128,
    bottleneck=32, max_operands=4) ≈ 5.3K; at d_model=512 ≈ 17.6K. Actual
    parameter count is exposed as ``self.parameter_count``.
    """

    def __init__(
        self,
        d_model: int,
        bottleneck_dim: int = DEFAULT_BOTTLENECK_DIM,
        max_operands: int = DEFAULT_MAX_OPERANDS,
        num_noetics: int = NUM_NOETICS,
        num_domains: int = NUM_DOMAINS,
        num_registers: int = NUM_REGISTERS,
        operand_count_buckets: tuple[int, ...] = OPERAND_COUNT_BUCKETS,
    ) -> None:
        super().__init__()

        if d_model <= 0:
            raise ValueError(f"d_model must be > 0, got {d_model}")
        if bottleneck_dim <= 0:
            raise ValueError(
                f"bottleneck_dim must be > 0, got {bottleneck_dim}"
            )
        if max_operands <= 0:
            raise ValueError(f"max_operands must be > 0, got {max_operands}")
        if not operand_count_buckets:
            raise ValueError("operand_count_buckets must be non-empty")

        self.d_model = d_model
        self.bottleneck_dim = bottleneck_dim
        self.max_operands = max_operands
        self.num_noetics = num_noetics
        self.num_domains = num_domains
        self.num_registers = num_registers
        self.operand_count_buckets = tuple(operand_count_buckets)

        # Shared low-rank backbone: d_model -> bottleneck -> GELU.
        self.backbone = nn.Sequential(
            nn.Linear(d_model, bottleneck_dim),
            nn.GELU(),
        )

        # Five parallel heads.
        self.noetic_head = nn.Linear(bottleneck_dim, num_noetics)
        self.domain_head = nn.Linear(bottleneck_dim, num_domains)
        # Per-operand register head emits max_operands * num_registers
        # logits, reshaped to (B, max_operands, num_registers).
        self.register_head = nn.Linear(
            bottleneck_dim, max_operands * num_registers
        )
        self.operand_count_head = nn.Linear(
            bottleneck_dim, len(self.operand_count_buckets)
        )
        # Binary: is a named Ω_* emergent result present?
        self.named_emergent_head = nn.Linear(bottleneck_dim, 2)

    # ---------------------------------------------------------------- utils

    @property
    def parameter_count(self) -> int:
        """Total trainable parameter count of this head."""
        return sum(p.numel() for p in self.parameters())

    # --------------------------------------------------------------- forward

    def _pool(self, hidden_states: torch.Tensor) -> torch.Tensor:
        """Mean-pool 3-D hidden states; pass 2-D through unchanged."""
        if hidden_states.dim() == 3:
            return hidden_states.mean(dim=1)
        if hidden_states.dim() == 2:
            return hidden_states
        raise ValueError(
            "ExpressionProposerHead expects hidden_states with 2 or 3 "
            f"dimensions; got {hidden_states.dim()} "
            f"(shape={tuple(hidden_states.shape)})."
        )

    def forward(
        self,
        hidden_states: torch.Tensor,
        *,
        mode: str = "training",
        tau: float = 1.0,
    ) -> dict[str, torch.Tensor]:
        """Emit the five-head logit dict.

        Args:
            hidden_states: ``(B, d_model)`` or ``(B, seq_len, d_model)``.
            mode: ``"training"`` or ``"inference"``. Only affects whether
                Gumbel-softmax samples are attached to the return dict — the
                logits themselves are mode-invariant.
            tau: Gumbel-softmax temperature. Only consulted when
                ``mode == "training"``. The trainer wires this to the same
                annealed tau used by ADR-04's ``DifferentiableStoichiometry``.

        Returns:
            dict with:
                - ``noetic_logits`` (B, num_noetics)
                - ``domain_logits`` (B, num_domains)
                - ``register_logits`` (B, max_operands, num_registers)
                - ``operand_count_logits`` (B, |operand_count_buckets|)
                - ``named_emergent_logits`` (B, 2)
                - (training-mode only) ``register_gumbel`` (B, max_operands,
                  num_registers): Gumbel-softmax ST sample — present for
                  forward-compat with Option B (ADR-07 Consequences §3);
                  the v1 loss does not consume it.
        """
        if mode not in {"training", "inference"}:
            raise ValueError(
                f"mode must be 'training' or 'inference', got {mode!r}"
            )

        pooled = self._pool(hidden_states)  # (B, d_model)
        bottleneck = self.backbone(pooled)  # (B, bottleneck_dim)

        noetic_logits = self.noetic_head(bottleneck)          # (B, N)
        domain_logits = self.domain_head(bottleneck)          # (B, D)
        register_flat = self.register_head(bottleneck)        # (B, M*R)
        register_logits = register_flat.reshape(
            -1, self.max_operands, self.num_registers
        )                                                     # (B, M, R)
        operand_count_logits = self.operand_count_head(bottleneck)
        named_emergent_logits = self.named_emergent_head(bottleneck)

        out: dict[str, torch.Tensor] = {
            "noetic_logits": noetic_logits,
            "domain_logits": domain_logits,
            "register_logits": register_logits,
            "operand_count_logits": operand_count_logits,
            "named_emergent_logits": named_emergent_logits,
        }

        if mode == "training":
            # Differentiable register-sample carried alongside logits for
            # Option B compatibility. Straight-through Gumbel-softmax so
            # the forward uses one-hot but the backward pass uses the
            # soft distribution. Not consumed by v1 Option-A loss.
            out["register_gumbel"] = F.gumbel_softmax(
                register_logits, tau=max(float(tau), 1e-3), hard=True, dim=-1
            )

        return out

    # ------------------------------------------------------------- inference

    def propose(
        self,
        hidden_states: torch.Tensor,
    ) -> list[ExpressionProposal]:
        """Argmax proposal (inference-mode convenience).

        Returns one ``ExpressionProposal`` per example in the batch.
        """
        out = self.forward(hidden_states, mode="inference")

        noetic = out["noetic_logits"].argmax(dim=-1)          # (B,)
        domain = out["domain_logits"].argmax(dim=-1)          # (B,)
        registers = out["register_logits"].argmax(dim=-1)     # (B, M)
        op_count_idx = out["operand_count_logits"].argmax(dim=-1)  # (B,)
        named = out["named_emergent_logits"].argmax(dim=-1)   # (B,)

        proposals: list[ExpressionProposal] = []
        for i in range(noetic.shape[0]):
            count_bucket = int(op_count_idx[i].item())
            count = self.operand_count_buckets[count_bucket]
            regs_row = registers[i].tolist()[:count]
            proposals.append(
                ExpressionProposal(
                    noetic=int(noetic[i].item()),
                    domain=int(domain[i].item()),
                    registers_per_operand=tuple(int(r) for r in regs_row),
                    operand_count=int(count),
                    has_named_emergent=bool(named[i].item()),
                )
            )
        return proposals
