"""CAS Type Constraints for CAS-Native model validation.

Based on v6.1 Chapter 11 type system rules, adapted as validation
functions and loss regularizers for PyTorch training.

Key constraints:
- CO-0 (identity) output must equal input
- Involution pairs: CO-2(CO-3(x)) ≈ x
- Domain descent: P→C→E→O information flow
- RPM chain: Power requires Wisdom requires Desire (section-retraction)
- Fractal type: non-empty sequence, all indices 0-9
"""

from __future__ import annotations

from typing import Optional

try:
    import torch
    import torch.nn.functional as F
    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False


# --- Pure validation functions (no PyTorch required) ---

def validate_operator_output(co_index: int, input_val: float, output_val: float, tolerance: float = 0.1) -> bool:
    """Check output is valid for this Cognitive Operator.

    CO-0 (identity): output must equal input.
    Self-dual operators (CO-1, CO-4, CO-7): applying twice should approximate identity.
    """
    if co_index == 0:
        return abs(output_val - input_val) < tolerance
    return 0.0 <= output_val <= 1.0


def validate_involution_roundtrip(
    co_a: int, co_b: int, input_val: float, roundtrip_val: float, tolerance: float = 0.15
) -> bool:
    """Check involution pair roundtrip: CO-a(CO-b(x)) ≈ x.

    Involution pairs: (2,3), (5,6), (8,9).
    """
    valid_pairs = {(2, 3), (3, 2), (5, 6), (6, 5), (8, 9), (9, 8)}
    if (co_a, co_b) not in valid_pairs:
        return True  # Not an involution pair — no constraint
    return abs(roundtrip_val - input_val) < tolerance


def validate_domain_descent(
    p_output: float, c_output: float, e_output: float, o_output: float
) -> bool:
    """Verify P→C→E→O information flow constraint.

    Each domain output should be derivable from higher domains.
    O should not contain information not present in P∪C∪E.
    Heuristic: lower domains should not exceed higher domains significantly.
    """
    # P ≻ C ≻ E ≻ O: information flows downward
    # Operational should not dramatically exceed Principled
    if o_output > p_output + 0.3:
        return False
    return True


def validate_rpm_chain(desire: float, wisdom: float, power: float, threshold: float = 0.5) -> bool:
    """Verify prerequisite ordering (section-retraction, NOT monadic).

    Power > threshold requires Wisdom > threshold requires Desire > threshold.
    Forward check only — backward reconstruction NOT guaranteed (v7.4 Correction #2).
    """
    if power >= threshold and wisdom < threshold:
        return False  # Power without Wisdom
    if wisdom >= threshold and desire < threshold:
        return False  # Wisdom without Desire
    return True


def validate_fractal_type(sequence: list[int]) -> bool:
    """Check fractal is well-formed: non-empty, all indices 0-9."""
    if not sequence:
        return False
    return all(0 <= idx <= 9 for idx in sequence)


# --- PyTorch loss regularizers (require torch) ---

if _HAS_TORCH:
    def identity_constraint_loss(co0_input: torch.Tensor, co0_output: torch.Tensor) -> torch.Tensor:
        """CO-0 identity constraint: output should equal input.

        L = ||CO-0(x) - x||²
        """
        return F.mse_loss(co0_output, co0_input)

    def involution_constraint_loss(
        forward_output: torch.Tensor, backward_output: torch.Tensor, original_input: torch.Tensor
    ) -> torch.Tensor:
        """Involution roundtrip constraint: CO-a(CO-b(x)) ≈ x.

        L = ||CO-a(CO-b(x)) - x||²
        """
        return F.mse_loss(backward_output, original_input)

    def domain_descent_loss(
        p_repr: torch.Tensor, c_repr: torch.Tensor,
        e_repr: torch.Tensor, o_repr: torch.Tensor,
    ) -> torch.Tensor:
        """Domain descent constraint: information flows P→C→E→O.

        Penalizes when lower domain representations exceed higher domain norms.
        L = max(0, ||O|| - ||P|| - margin)² + max(0, ||E|| - ||C|| - margin)²
        """
        margin = 0.1
        p_norm = p_repr.norm(dim=-1)
        c_norm = c_repr.norm(dim=-1)
        e_norm = e_repr.norm(dim=-1)
        o_norm = o_repr.norm(dim=-1)

        loss_oc = torch.relu(o_norm - p_norm - margin).pow(2).mean()
        loss_ec = torch.relu(e_norm - c_norm - margin).pow(2).mean()
        return loss_oc + loss_ec

    def rpm_ordering_loss(
        desire: torch.Tensor, wisdom: torch.Tensor, power: torch.Tensor,
        threshold: float = 0.5,
    ) -> torch.Tensor:
        """RPM prerequisite ordering constraint (section-retraction).

        Penalizes power without wisdom, and wisdom without desire.
        L = max(0, power - wisdom)² + max(0, wisdom - desire)²
        Only applies when values exceed threshold.
        """
        power_without_wisdom = torch.relu(power - wisdom) * (power > threshold).float()
        wisdom_without_desire = torch.relu(wisdom - desire) * (wisdom > threshold).float()
        return (power_without_wisdom.pow(2) + wisdom_without_desire.pow(2)).mean()

    def type_constraint_loss(
        co0_input: Optional[torch.Tensor] = None,
        co0_output: Optional[torch.Tensor] = None,
        involution_input: Optional[torch.Tensor] = None,
        involution_roundtrip: Optional[torch.Tensor] = None,
        domain_reprs: Optional[tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]] = None,
        rpm_scores: Optional[tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = None,
        lambda_type: float = 0.1,
    ) -> torch.Tensor:
        """Combined type constraint regularizer.

        Aggregates all type constraints with configurable weight.
        """
        total = torch.tensor(0.0)

        if co0_input is not None and co0_output is not None:
            total = total + identity_constraint_loss(co0_input, co0_output)

        if involution_input is not None and involution_roundtrip is not None:
            total = total + involution_constraint_loss(
                involution_roundtrip, involution_roundtrip, involution_input
            )

        if domain_reprs is not None:
            total = total + domain_descent_loss(*domain_reprs)

        if rpm_scores is not None:
            total = total + rpm_ordering_loss(*rpm_scores)

        return lambda_type * total
