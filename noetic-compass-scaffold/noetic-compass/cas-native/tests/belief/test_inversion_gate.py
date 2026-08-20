"""Tests for the 7-axis inversion scan."""

from __future__ import annotations

import pytest

from cas_native.belief import (
    ALL_AXES,
    PLACEHOLDER_AXES,
    run_inversion_scan,
)
from cas_native.belief.inversion_gate import (
    _extract_domains,
    axis_a_check,
    axis_e_check,
    axis_f_check,
    axis_n_check,
    axis_p_check,
    axis_s_check,
    axis_w_check,
)


# ---------------------------------------------------------------------------
# Per-axis primitives
# ---------------------------------------------------------------------------


def test_axis_n_clean_for_self_dual():
    out = axis_n_check("^4^P")
    assert out["clean"] is True


def test_axis_n_flags_2_and_3_without_integrator():
    out = axis_n_check("^2^P ^3^P")
    assert out["clean"] is False
    assert (2, 3) in out["flagged_pairs"]


def test_axis_n_clean_when_integrator_present():
    out = axis_n_check("^2^P + ^3^P")
    assert out["clean"] is True


def test_axis_n_flags_when_contradiction_history_nonempty():
    out = axis_n_check("^4^P", contradiction_count=1)
    assert out["clean"] is False
    assert "contradiction" in out["reason"].lower()


def test_axis_w_clean_when_only_one_domain():
    out = axis_w_check("^4^P")
    assert out["clean"] is True


def test_axis_w_clean_for_descending_p_then_o():
    out = axis_w_check("^4^P + ^2^O")
    assert out["clean"] is True


def test_axis_w_flags_for_ascending_o_then_p():
    out = axis_w_check("^4^O + ^2^P")
    assert out["clean"] is False
    assert "precedence" in out["reason"].lower()


def test_axis_w_clean_for_p_c_e_descent():
    out = axis_w_check("^4^P -> ^4^C -> ^4^E")
    assert out["clean"] is True


# ---------------------------------------------------------------------------
# Regression: _DOMAIN_RE must match inside DRIVE-TAGGED literals.
#
# `_DOMAIN_RE` used to end in `\b`. `_` is a word character, so in the shapes
# this project actually emits (`^8^E_{F5} -> ^6^C_{F5}`) there is no word
# boundary between `E` and `_`, `_extract_domains` returned `[]`, and axis W
# could NEVER fire on a drive-tagged expression. These tests pin the fix.
# ---------------------------------------------------------------------------


def test_extract_domains_sees_through_a_drive_tag():
    # Before the fix this returned [].
    assert _extract_domains("^8^E_{F5} -> ^6^C_{F5}") == ["E", "C"]


def test_extract_domains_sees_through_a_register_tag():
    assert _extract_domains("^3^P|A + ^3^P|f") == ["P", "P"]


def test_extract_domains_ignores_a_domain_letter_inside_a_longer_token():
    # `^Ex` is not a domain marker; the lookahead must still reject it.
    assert _extract_domains("^Extra") == []


@pytest.mark.parametrize("suffix", ["é", "١", "\u0301"])
def test_extract_domains_rejects_unicode_letter_number_or_mark_suffix(suffix):
    assert _extract_domains(f"^P{suffix}") == []


def test_axis_w_flags_drive_tagged_precedence_violation():
    # E (rank 2) followed by C (rank 1) is a genuine domain-precedence
    # violation. Before the fix this returned clean=True with domains=[].
    out = axis_w_check("^8^E_{F5} -> ^6^C_{F5}")
    assert out["clean"] is False
    assert out["domains"] == ["E", "C"]
    assert "precedence" in out["reason"].lower()


def test_axis_w_clean_on_valid_drive_tagged_descent():
    out = axis_w_check("^8^C_{F5} -> ^6^E_{F5}")
    assert out["clean"] is True
    assert out["domains"] == ["C", "E"]


def test_run_inversion_scan_axis_w_fires_on_drive_tagged_violation():
    scan = run_inversion_scan("^8^E_{F5} -> ^6^C_{F5}", rpm_satisfied=True)
    assert scan.axes["W"]["clean"] is False
    assert scan.clean is False


def test_run_inversion_scan_axis_w_stays_clean_on_valid_drive_tagged_descent():
    scan = run_inversion_scan("^8^C_{F5} -> ^6^E_{F5}", rpm_satisfied=True)
    assert scan.axes["W"]["clean"] is True
    assert scan.clean is True


def test_axis_f_clean_for_self_dual():
    out = axis_f_check("^4^P_{F4}")
    assert out["clean"] is True


def test_axis_f_flags_f1_f7_without_integrator():
    out = axis_f_check("F1 F7")
    assert out["clean"] is False


def test_axis_f_clean_with_integrator():
    out = axis_f_check("F1 + F7")
    assert out["clean"] is True


def test_axis_e_is_placeholder():
    out = axis_e_check()
    assert out["clean"] is True
    assert out.get("placeholder") is True


def test_axis_s_is_placeholder():
    out = axis_s_check()
    assert out["clean"] is True
    assert out.get("placeholder") is True


def test_axis_a_uses_rpm_satisfied():
    assert axis_a_check(rpm_satisfied=True)["clean"] is True
    assert axis_a_check(rpm_satisfied=False)["clean"] is False


def test_axis_p_clean_when_zero_other_failures():
    others = {
        "N": {"clean": True},
        "W": {"clean": True},
        "F": {"clean": True},
        "A": {"clean": True},
    }
    assert axis_p_check(others)["clean"] is True


def test_axis_p_clean_when_one_other_failure():
    others = {
        "N": {"clean": False},
        "W": {"clean": True},
        "F": {"clean": True},
        "A": {"clean": True},
    }
    out = axis_p_check(others)
    assert out["clean"] is True


def test_axis_p_flags_when_two_or_more_failures():
    others = {
        "N": {"clean": False},
        "W": {"clean": False},
        "F": {"clean": True},
        "A": {"clean": True},
    }
    out = axis_p_check(others)
    assert out["clean"] is False
    assert "compound" in out["reason"].lower()


# ---------------------------------------------------------------------------
# Top-level scan
# ---------------------------------------------------------------------------


def test_top_level_clean_expression_passes():
    scan = run_inversion_scan("^4^P", history=[], rpm_satisfied=True)
    assert scan.clean is True
    for axis in ALL_AXES:
        assert axis in scan.axes


def test_top_level_unsatisfied_rpm_fails_axis_a():
    scan = run_inversion_scan("^4^P", history=[], rpm_satisfied=False)
    assert scan.clean is False
    assert scan.axes["A"]["clean"] is False


def test_top_level_w_violation_unsatisfied_rpm_compound_fires():
    # W will fail (O before P) AND A fails -> P should fire.
    scan = run_inversion_scan(
        "^4^O + ^2^P", history=[], rpm_satisfied=False
    )
    assert scan.clean is False
    assert scan.axes["W"]["clean"] is False
    assert scan.axes["A"]["clean"] is False
    assert scan.axes["P"]["clean"] is False


def test_placeholder_axes_never_block_clean():
    scan = run_inversion_scan("^4^P", history=[], rpm_satisfied=True)
    for axis in PLACEHOLDER_AXES:
        assert scan.axes[axis]["clean"] is True
        assert scan.axes[axis].get("placeholder") is True
    assert scan.clean is True
