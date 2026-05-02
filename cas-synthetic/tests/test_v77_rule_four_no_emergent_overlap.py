"""Property tests for v77_rule_four after the structural-overlap fix.

The compliant arm previously emitted `(X × Y × Z) = ^N|Ω_*` (same-Noetic
× with named emergent), which is structurally identical to v77_omega
output. These tests lock the fix: the v77_rule_four generator now emits
ONLY shapes that are distinguishable from v77_omega.
"""

from __future__ import annotations

import re

import pytest

from cas_synthetic.generator.v77_rule_four import V77RuleFourGenerator


# Match same-Noetic ×=Ω structurally (the colliding pattern, must NOT
# appear in v77_rule_four output anymore).
_OVERLAP_RE = re.compile(
    r"^\s*\(\s*(?P<lhs>[^()]+?)\s*\)\s*=\s*\^(?P<rhs_noetic>[0-9])"
    r"(?:\^[PCEO])?\s*\|\s*(?:Omega|Ω)_[A-Za-z0-9_]+\s*$"
)


def _is_same_noetic_omega_emergent(expression: str) -> bool:
    if "×" not in expression:
        return False
    m = _OVERLAP_RE.match(expression.strip())
    if not m:
        return False
    rhs_n = m.group("rhs_noetic")
    operands = [op.strip() for op in m.group("lhs").split("×")]
    if len(operands) < 2:
        return False
    operand_n_re = re.compile(r"\^([0-9])")
    for op in operands:
        nm = operand_n_re.search(op)
        if nm is None or nm.group(1) != rhs_n:
            return False
    return True


def test_compliant_arm_never_emits_same_noetic_omega_overlap():
    """No record from the compliant branch should match the v77_omega-overlap
    structural pattern. If this fails, the bucket distinction collapses again."""

    gen = V77RuleFourGenerator(seed=1234)
    samples = [gen._generate_compliant() for _ in range(80)]
    overlapping = [
        s for s in samples if _is_same_noetic_omega_emergent(s.cas_expression)
    ]
    assert overlapping == [], (
        f"v77_rule_four compliant arm emitted {len(overlapping)} records "
        f"that structurally overlap v77_omega. First example: "
        f"{overlapping[0].cas_expression!r}"
    )


def test_compliant_arm_uses_plus_copresence():
    """Post-fix the compliant arm should always be `+` co-presence."""

    gen = V77RuleFourGenerator(seed=2025)
    samples = [gen._generate_compliant() for _ in range(40)]
    for s in samples:
        # `+` co-presence has `+` and lacks `×=Ω` shape
        assert "+" in s.cas_expression, (
            f"compliant arm sample missing `+`: {s.cas_expression!r}"
        )
        assert not _is_same_noetic_omega_emergent(s.cas_expression)


def test_violation_arm_still_emits_same_noetic_no_emergent():
    """Violation arm is unchanged: same-Noetic × WITHOUT emergent.
    Distinguishable from v77_omega because no Ω_*."""

    gen = V77RuleFourGenerator(seed=42)
    sample = gen._generate_violation()
    assert "×" in sample.cas_expression
    assert "Ω" not in sample.cas_expression and "Omega" not in sample.cas_expression
    assert sample.is_valid is False


def test_full_generator_produces_no_omega_overlap_records():
    """End-to-end: across many samples, v77_rule_four never produces a record
    structurally indistinguishable from v77_omega."""

    gen = V77RuleFourGenerator(seed=99)
    samples = [gen._generate_one() for _ in range(200)]
    overlapping = [
        s for s in samples if _is_same_noetic_omega_emergent(s.cas_expression)
    ]
    assert overlapping == [], (
        f"v77_rule_four end-to-end produced {len(overlapping)} structural-"
        f"overlap records out of 200 samples"
    )
