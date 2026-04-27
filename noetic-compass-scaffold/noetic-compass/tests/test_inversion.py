"""Tests for the Sprint 3 CAS inversion engine (`api/notation/inversion.py`).

Covers:

- N axis (Operator / Noetic involution): pair flips, self-duals unchanged,
  recipe-form preservation.
- W axis (Domain precedence): P↔O, C↔E.
- F axis (Drive pair): F2↔F6, F3↔F5, drive inside compound state.
- P axis (Compound): N + W + F applied together.
- Deferred axes E / S / A raise DeferredAxisError.
- Round-trip property: applying the same axis twice returns the original.
"""

from __future__ import annotations

import pytest

from api.notation.compiler import compile_expression
from api.notation.inversion import (
    AXIS_DESCRIPTIONS,
    DEFERRED_AXES,
    IMPLEMENTED_AXES,
    DeferredAxisError,
    UnknownAxisError,
    invert_expression,
)


# ---------------------------------------------------------------------------
# N axis
# ---------------------------------------------------------------------------


def test_n_axis_flips_co2_to_co3_state():
    result = invert_expression("^2^P", "N")
    assert result.valid, result.error
    assert result.inverted == "^3^P"
    assert result.axis == "N"


def test_n_axis_flips_co5_to_co6_in_cognitive_domain():
    result = invert_expression("^5^C", "N")
    assert result.valid, result.error
    assert result.inverted == "^6^C"


def test_n_axis_self_dual_co4_unchanged():
    """CO-4 (Vibration) is a structural self-dual — N must leave it alone."""
    result = invert_expression("^4^E", "N")
    assert result.valid, result.error
    assert result.inverted == "^4^E"


def test_n_axis_self_duals_co0_co1_co7_unchanged():
    for src in ("^0^P", "^1^C", "^7^O"):
        result = invert_expression(src, "N")
        assert result.valid, result.error
        assert result.inverted == src


def test_n_axis_handles_long_co_form():
    """The long-form ``CO-N`` surface must invert identically to ``^N``."""
    result = invert_expression("CO-2^C_{F2}", "N")
    assert result.valid, result.error
    assert result.inverted == "CO-3^C_{F2}"


def test_n_axis_inside_recipe_inverts_each_prerequisite():
    src = "Theta(Omega_x) = 0.6*CO-2^P + 0.4*CO-8^C -> Omega_x"
    result = invert_expression(src, "N")
    assert result.valid, result.error
    # CO-2 -> CO-3, CO-8 -> CO-9. Theta/Omega tokens are untouched.
    assert "CO-3^P" in result.inverted
    assert "CO-9^C" in result.inverted
    assert "CO-2" not in result.inverted
    assert "CO-8" not in result.inverted


# ---------------------------------------------------------------------------
# W axis (Domain precedence)
# ---------------------------------------------------------------------------


def test_w_axis_flips_principled_to_operational():
    result = invert_expression("^2^P", "W")
    assert result.valid, result.error
    assert result.inverted == "^2^O"


def test_w_axis_flips_cognitive_to_evaluative():
    result = invert_expression("^5^C", "W")
    assert result.valid, result.error
    assert result.inverted == "^5^E"


def test_w_axis_double_application_is_identity():
    src = "^2^P_{F2}"
    once = invert_expression(src, "W")
    twice = invert_expression(once.inverted, "W")
    assert twice.valid
    assert twice.inverted == src


# ---------------------------------------------------------------------------
# F axis (Drive pair)
# ---------------------------------------------------------------------------


def test_f_axis_drive_membership_assertion():
    """``F2 ∈ Drives`` should invert to ``F6 ∈ Drives``."""
    src = "F2 ∈ Drives"
    result = invert_expression(src, "F")
    assert result.valid, result.error
    assert "F6" in result.inverted
    assert "F2" not in result.inverted


def test_f_axis_inside_compound_state():
    result = invert_expression("^3^P_{F3}", "F")
    assert result.valid, result.error
    # F3 ↔ F5 under the inversion-pair rule
    assert result.inverted == "^3^P_{F5}"


def test_f_axis_self_dual_f4_unchanged():
    result = invert_expression("^2^C_{F4}", "F")
    assert result.valid, result.error
    assert result.inverted == "^2^C_{F4}"


def test_f_axis_does_not_perturb_co_or_domain_tokens():
    """Drive flip must leave CO-N and ^D tokens alone."""
    src = "CO-2^P_{F2}"
    result = invert_expression(src, "F")
    assert result.valid, result.error
    # CO-2 unchanged, ^P unchanged, F2 -> F6
    assert result.inverted == "CO-2^P_{F6}"


# ---------------------------------------------------------------------------
# P axis (Compound: N + W + F)
# ---------------------------------------------------------------------------


def test_p_axis_applies_n_w_and_f_together():
    result = invert_expression("^2^P_{F2}", "P")
    assert result.valid, result.error
    # CO-2 -> CO-3, P -> O, F2 -> F6 -- all three axes in one shot.
    assert result.inverted == "^3^O_{F6}"


def test_p_axis_preserves_self_duals_on_each_axis():
    # CO-4 self-dual under N, F4 self-dual under F. Only W flips.
    result = invert_expression("^4^C_{F4}", "P")
    assert result.valid, result.error
    assert result.inverted == "^4^E_{F4}"


# ---------------------------------------------------------------------------
# Deferred axes (E, S, A)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("axis", ["E", "S", "A"])
def test_deferred_axes_raise_deferred_axis_error(axis: str):
    with pytest.raises(DeferredAxisError) as excinfo:
        invert_expression("^2^P", axis)
    assert excinfo.value.axis == axis
    # Description carried through so the API layer can surface it.
    assert excinfo.value.description == AXIS_DESCRIPTIONS[axis]


@pytest.mark.parametrize("axis", ["E", "S", "A"])
def test_deferred_axes_listed_in_module_constants(axis: str):
    assert axis in DEFERRED_AXES
    assert axis not in IMPLEMENTED_AXES


def test_unknown_axis_raises_unknown_axis_error():
    with pytest.raises(UnknownAxisError):
        invert_expression("^2^P", "Z")


# ---------------------------------------------------------------------------
# Round-trip / involution property
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "axis,src",
    [
        ("N", "^2^P_{F2}"),
        ("N", "CO-5^C_{F4}"),
        ("N", "Theta(Omega_x) = 0.6*CO-2^P + 0.4*CO-8^C -> Omega_x"),
        ("W", "^3^C_{F1}"),
        ("W", "^7^E"),
        ("F", "^2^P_{F3}"),
        ("F", "CO-1^O_{F2}"),
        ("P", "^2^P_{F2}"),
        ("P", "^4^C_{F4}"),
    ],
)
def test_axis_double_application_is_identity(axis: str, src: str):
    """Each implemented axis is an involution: applying it twice returns
    the original (and the result is still compiler-valid)."""
    once = invert_expression(src, axis)
    assert once.valid, once.error
    twice = invert_expression(once.inverted, axis)
    assert twice.valid, twice.error
    assert twice.inverted == src


# ---------------------------------------------------------------------------
# Compiler validity of inverted output
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "axis,src",
    [
        ("N", "^2^P_{F2}"),
        ("W", "^5^C"),
        ("F", "^3^P_{F3}"),
        ("P", "^2^P_{F2}"),
    ],
)
def test_inverted_output_compiles_via_public_api(axis: str, src: str):
    """The inverted CAS string must round-trip cleanly through the public
    ``compile_expression`` (we cannot rely on InversionResult.valid alone
    in case of internal divergence between the two code paths)."""
    result = invert_expression(src, axis)
    assert result.valid, result.error
    artifact = compile_expression(result.inverted)
    assert artifact.valid is True, artifact.error
    assert artifact.ast is not None


# ---------------------------------------------------------------------------
# Documented axis catalogue
# ---------------------------------------------------------------------------


def test_axis_descriptions_cover_all_seven_axes():
    expected = {"N", "W", "F", "E", "S", "A", "P"}
    assert set(AXIS_DESCRIPTIONS) == expected
