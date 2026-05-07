"""Tests for the compiler-preservation scorer.

Locks in the four canonical audit-failure cases from
``docs/working/path_B4_human_relevance_failure_2026_05_07.md`` plus identity
and parse-error behavior. The scorer is deterministic: every assertion here
is on a fixed pair of strings.
"""

from __future__ import annotations

import pytest

from cas_native.evaluation.compiler_preservation_scorer import (
    PreservationResult,
    score_preservation,
)


# ---------------------------------------------------------------------------
# 1. v74_baseline -- partial loss (operand + operator drop)
# ---------------------------------------------------------------------------


def test_v74_baseline_partial_loss():
    """GT carries two operands joined by ``*``; pred drops the second
    operand and the operator.

    Five content axes (operands, operators, domains, drives, registers)
    must fail because the second state literal is gone. The remaining
    five axes (coefficients, omega targets, theta wrappers, arrows,
    meta-logic) are vacuously preserved -- both inputs have zero of each
    -- so the deterministic score is exactly 0.5. The spec floor is
    ``score <= 0.5``: anything higher would mean a content axis we
    expect to fail is actually succeeding.
    """

    gt = "^8^C_{F6} * ^5^C_{F6}"
    pred = "^8^C_{F6}"

    result = score_preservation(gt, pred)

    assert result.parse_error is None
    assert result.operands_preserved is False
    assert result.operators_preserved is False
    assert result.domains_preserved is False
    assert result.drives_preserved is False
    assert result.registers_preserved is False
    assert result.preservation_score <= 0.5


# ---------------------------------------------------------------------------
# 2. v77_omega cadence -- drives stripped, named target collapsed
# ---------------------------------------------------------------------------


def test_v77_omega_cadence_drives_and_target_lost():
    """GT: drives F2/F5/F6 present and named target ``Omega_cadence``.
    Pred: all drives stripped to None, target collapsed to bare ``Omega``.
    """

    gt = "(^7^O_{F2}|E × ^7^O_{F5}|A × ^7^O_{F6}|f) = ^7^O|Ω_cadence"
    pred = "(^7^O|A × ^7^O|f × ^7^O|E) = ^7^O|Ω"

    result = score_preservation(gt, pred)

    assert result.parse_error is None
    assert result.drives_preserved is False
    assert result.named_omega_targets_preserved is False


# ---------------------------------------------------------------------------
# 3. v77_omega presence -- domain hallucinated, drives stripped, target lost
# ---------------------------------------------------------------------------


def test_v77_omega_presence_domain_hallucinated():
    """GT: ``^1_{F3}|E`` and ``^1_{F5}|A`` -- no explicit Domain, drives
    F3/F5, named target ``Omega_presence``. Pred: hallucinated ``^P`` on
    each literal, drives dropped, target collapsed.
    """

    gt = "(^1_{F3}|E × ^1_{F5}|A) = ^1|Ω_presence"
    pred = "(^1^P|A × ^1^P|E) = ^1^P|Ω"

    result = score_preservation(gt, pred)

    assert result.parse_error is None
    assert result.domains_preserved is False
    assert result.drives_preserved is False
    assert result.named_omega_targets_preserved is False


# ---------------------------------------------------------------------------
# 4. v76_production -- catastrophic loss
# ---------------------------------------------------------------------------


def test_v76_production_catastrophic_loss():
    """GT: full Theta-wrapped recipe with three coefficients, three
    operands, an arrow, and a named omega. Pred: bare two-term sum.
    Six axes must fail and ``preservation_score`` must drop below 0.3.
    """

    gt = (
        "Θ(Ω_focused_refusal) = "
        "0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A + 1.04*^1^P_{F1}|A "
        "→ Ω_focused_refusal"
    )
    pred = "^7^P|T + ^7^P|A"

    result = score_preservation(gt, pred)

    assert result.parse_error is None
    assert result.theta_wrappers_preserved is False
    assert result.coefficients_preserved is False
    assert result.arrows_preserved is False
    assert result.named_omega_targets_preserved is False
    assert result.operands_preserved is False
    assert result.preservation_score < 0.3


# ---------------------------------------------------------------------------
# 5. Identity -- a string scored against itself returns all True / 1.0
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expr",
    [
        # Bare state literal
        "^3^P",
        # Compound state with drive + register
        "^7^P_{F7}|T",
        # Two-operand TIMES chain (v74 family)
        "^8^C_{F6} * ^5^C_{F6}",
        # v77 named-emergent assignment with full drives + register set
        "(^7^O_{F2}|E × ^7^O_{F5}|A × ^7^O_{F6}|f) = ^7^O|Ω_cadence",
        # v76 full recipe with coefficients
        (
            "Θ(Ω_focused_refusal) = "
            "0.53*^7^P_{F7}|T + 2.11*^3^P_{F2}|A + 1.04*^1^P_{F1}|A "
            "→ Ω_focused_refusal"
        ),
        # Meta-logic relation
        "CO-3 ∈ Noetics",
        # Register-set form
        "^7^O|⟨A,f,T⟩",
    ],
)
def test_identity_returns_all_true(expr: str):
    result = score_preservation(expr, expr)

    assert result.parse_error is None
    assert result.operands_preserved is True
    assert result.operators_preserved is True
    assert result.domains_preserved is True
    assert result.drives_preserved is True
    assert result.registers_preserved is True
    assert result.coefficients_preserved is True
    assert result.named_omega_targets_preserved is True
    assert result.theta_wrappers_preserved is True
    assert result.arrows_preserved is True
    assert result.meta_logic_relations_preserved is True
    assert result.preservation_score == 1.0


# ---------------------------------------------------------------------------
# 6, 7, 8. Parse-error handling
# ---------------------------------------------------------------------------


def test_both_unparseable_returns_parse_error():
    result = score_preservation("$$$ not cas $$$", "@@@ also not @@@")

    assert result.parse_error == "both_unparseable"
    assert result.operands_preserved is False
    assert result.operators_preserved is False
    assert result.domains_preserved is False
    assert result.drives_preserved is False
    assert result.registers_preserved is False
    assert result.coefficients_preserved is False
    assert result.named_omega_targets_preserved is False
    assert result.theta_wrappers_preserved is False
    assert result.arrows_preserved is False
    assert result.meta_logic_relations_preserved is False
    assert result.preservation_score == 0.0


def test_only_predicted_unparseable():
    result = score_preservation("^3^P", "$$$ garbage $$$")

    assert result.parse_error == "predicted_unparseable"
    assert result.preservation_score == 0.0
    assert all(
        getattr(result, axis) is False
        for axis in (
            "operands_preserved",
            "operators_preserved",
            "domains_preserved",
            "drives_preserved",
            "registers_preserved",
            "coefficients_preserved",
            "named_omega_targets_preserved",
            "theta_wrappers_preserved",
            "arrows_preserved",
            "meta_logic_relations_preserved",
        )
    )


def test_only_ground_truth_unparseable():
    result = score_preservation("$$$ garbage $$$", "^3^P")

    assert result.parse_error == "ground_truth_unparseable"
    assert result.preservation_score == 0.0


# ---------------------------------------------------------------------------
# Importability sanity check (per the deliverable spec)
# ---------------------------------------------------------------------------


def test_public_api_importable():
    assert callable(score_preservation)
    assert PreservationResult is not None
