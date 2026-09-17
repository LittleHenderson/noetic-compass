"""Tests for the 7-axis inversion scanner and the state-index authority.

Subject under test: ``cncm/inversions.py``, plus the index mapping it reads from
``cncm/noetica.py``.

The load-bearing distinction these tests defend: an axis with a **frozen** limit is judged,
and an axis without one is **measured but not judged**. ``exceeds_frozen_limit`` must be
``None`` — not ``False`` — in the second case, because collapsing the two would turn an
undecided threshold into a silent pass. And the compound axis must not be reachable from an
unfrozen reading.

Plain pytest functions, no fixtures, no numeric runtime, no clock.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from cncm import inversions as inv
from cncm import noetica as n
from cncm import simplex as s
from cncm.model import CANONICAL_DRIVES


def uniform_state() -> s.CognitiveStateVector:
    return s.from_weights([1.0] * s.NUM_STATES)


def state_concentrated_on(label: str, weight: float = 1.0) -> s.CognitiveStateVector:
    weights = [1e-9] * s.NUM_STATES
    weights[n.index_of(label)] = weight
    return s.from_weights(weights)


def dials(*values) -> inv.DialProfile:
    return inv.DialProfile(dials=tuple(values))


def drive_profile(**overrides) -> inv.DriveProfile:
    values = {drive: float(index) for index, drive in enumerate(CANONICAL_DRIVES)}
    values.update(overrides)
    return inv.DriveProfile(values=values)


def subdrive_profile(factor: float = 1.0) -> inv.SubDriveProfile:
    return inv.SubDriveProfile(
        values={
            (drive, tier): factor * index
            for index, drive in enumerate(CANONICAL_DRIVES)
            for tier in inv.DOMAIN_TIERS
        }
    )


# --------------------------------------------------------------------------- #
# Frozen structure.
# --------------------------------------------------------------------------- #


def test_the_seven_axes_are_named_and_their_limits_declared():
    profile = inv.axis_profile()
    assert [row["axis"] for row in profile["axes"]] == ["N", "W", "F", "E", "S", "A", "P"]
    limits = {row["axis"]: row["limit"] for row in profile["axes"]}
    assert limits["N"] == "frozen"
    assert limits["A"] == "frozen at 0"
    assert limits["P"] == "frozen: more than one axis"
    for axis in ("W", "F", "E", "S"):
        assert limits[axis] == "NOT_FROZEN"


def test_the_frozen_structures_match_the_instructions():
    assert inv.INVOLUTION_PAIRS == ((2, 3), (5, 6), (8, 9))
    assert inv.SELF_DUAL_NOETICS == (0, 1, 4, 7)
    assert inv.DRIVE_PAIRS == (("F1", "F7"), ("F2", "F6"), ("F3", "F5"))
    assert inv.SELF_DUAL_DRIVE == "F4"
    assert inv.DOMAIN_TIERS == ("P", "C", "E", "O")
    assert (inv.MIN_DIAL, inv.MAX_DIAL) == (3, 9)
    assert inv.MAX_INVOLUTION_DIAL_DIVERGENCE == 4
    assert inv.axis_profile()["stealth"] == "ABSENT_FROM_THE_INSTRUCTIONS"


def test_the_dial_range_is_non_overridable():
    for bad in (2, 0, 10, 99, -3):
        with pytest.raises(inv.DialOutOfRange):
            dials(3, 4, 5, 6, 7, 8, 9, 3, 4, bad)
    for bad in (5.0, True, "5", None):
        with pytest.raises(inv.InversionError):
            dials(3, 4, 5, 6, 7, 8, 9, 3, 4, bad)
    with pytest.raises(inv.InversionError):
        inv.DialProfile(dials=(3, 4, 5))
    assert dials(3, 3, 3, 3, 3, 3, 3, 3, 3, 3).dials[0] == 3


# --------------------------------------------------------------------------- #
# Axis N — judged on dials, measured on the state vector.
# --------------------------------------------------------------------------- #


def test_axis_n_measures_the_worst_frozen_pair_divergence():
    profile = dials(3, 4, 5, 9, 7, 8, 9, 3, 4, 5)
    measurement = inv.involution_axis(profile)
    assert measurement.detail["pair_divergences"] == {"^2-^3": 4, "^5-^6": 1, "^8-^9": 1}
    assert measurement.measurement == 4.0
    assert measurement.frozen_limit == 4.0


def test_axis_n_judges_at_the_frozen_boundary():
    """``> 4`` fails; exactly 4 does not. The boundary is the instruction's, not a choice."""
    at_limit = inv.involution_axis(dials(3, 4, 5, 9, 7, 8, 9, 3, 4, 5))
    assert at_limit.measurement == 4.0
    assert at_limit.exceeds_frozen_limit is False

    over = inv.involution_axis(dials(3, 4, 3, 9, 7, 8, 9, 3, 4, 5))
    assert over.measurement == 6.0
    assert over.exceeds_frozen_limit is True


def test_the_state_vector_reading_of_axis_n_is_measured_but_not_judged():
    measurement = inv.involution_mass_axis(uniform_state())
    assert measurement.frozen_limit is None
    assert measurement.exceeds_frozen_limit is None
    assert measurement.detail["reading"] == "state vector, not dials"


def test_the_state_vector_reading_reports_a_real_imbalance():
    measurement = inv.involution_mass_axis(state_concentrated_on("C2"))
    assert measurement.measurement > 0.9
    assert measurement.exceeds_frozen_limit is None


# --------------------------------------------------------------------------- #
# Axis W — measured only.
# --------------------------------------------------------------------------- #


def test_axis_w_counts_strict_adjacent_tier_inversions():
    flat = inv.domain_precedence_axis(uniform_state())
    assert flat.measurement == 0.0
    assert flat.detail["domain_mass"]["P"] == pytest.approx(0.25, rel=1e-12)


def test_axis_w_does_not_treat_equal_tiers_as_an_inversion():
    """Equal mass in adjacent tiers is not an inversion; only strictly more is."""
    measurement = inv.domain_precedence_axis(uniform_state())
    assert measurement.measurement == 0.0
    assert measurement.detail["inversions"] == []


def test_axis_w_flags_a_real_inversion_and_has_no_limit():
    measurement = inv.domain_precedence_axis(state_concentrated_on("O3"))
    assert measurement.measurement >= 1.0
    assert measurement.frozen_limit is None
    assert measurement.exceeds_frozen_limit is None
    assert any(row["lower"] == "O" for row in measurement.detail["inversions"])


# --------------------------------------------------------------------------- #
# Axis F — measured only.
# --------------------------------------------------------------------------- #


def test_axis_f_measures_drive_pair_gaps_without_a_limit():
    measurement = inv.drive_pair_axis(drive_profile())
    assert measurement.detail["pair_gaps"] == {"F1-F7": 6.0, "F2-F6": 4.0, "F3-F5": 2.0}
    assert measurement.measurement == 6.0
    assert measurement.frozen_limit is None
    assert measurement.exceeds_frozen_limit is None


def test_the_drive_profile_needs_exactly_the_seven_canonical_drives():
    with pytest.raises(inv.InversionError):
        inv.DriveProfile(values={"F1": 1.0})
    with pytest.raises(inv.InversionError):
        inv.DriveProfile(values={**{d: 1.0 for d in CANONICAL_DRIVES}, "F8": 1.0})
    with pytest.raises(inv.InversionError):
        inv.DriveProfile(values={**{d: 1.0 for d in CANONICAL_DRIVES}, "F1": float("nan")})


# --------------------------------------------------------------------------- #
# Axis E — Correction 4's entropy, measured only.
# --------------------------------------------------------------------------- #


def test_axis_e_is_zero_at_the_uniform_point():
    measurement = inv.entropy_deficit_axis(uniform_state())
    assert measurement.measurement == pytest.approx(0.0, abs=1e-12)
    assert measurement.detail["entropy_nats"] == pytest.approx(math.log(40), rel=1e-12)


def test_axis_e_rises_as_the_state_concentrates():
    wide = inv.entropy_deficit_axis(s.from_weights([2.0] + [1.0] * 39))
    narrow = inv.entropy_deficit_axis(s.from_weights([1000.0] + [1.0] * 39))
    assert 0.0 < wide.measurement < narrow.measurement < 1.0
    assert narrow.frozen_limit is None
    assert narrow.exceeds_frozen_limit is None


def test_axis_e_matches_correction_four_and_stays_finite():
    """The open simplex guarantees every component is positive, so entropy is always defined."""
    for weights in ([1.0] * 40, [1e-12] * 40, [1e6] + [1e-6] * 39):
        state = s.from_weights(weights)
        measurement = inv.entropy_deficit_axis(state)
        assert measurement.measurement == pytest.approx(1.0 - state.uniformity(), rel=1e-12)
        assert math.isfinite(measurement.measurement)


# --------------------------------------------------------------------------- #
# Axis S — measured only.
# --------------------------------------------------------------------------- #


def test_axis_s_is_zero_when_every_drive_agrees_across_domains():
    measurement = inv.subdrive_variance_axis(subdrive_profile())
    assert measurement.measurement == pytest.approx(0.0, abs=1e-12)


def test_axis_s_reports_the_population_variance():
    values = {
        (drive, tier): ({**{"P": 0.0, "C": 0.0, "E": 0.0, "O": 4.0}}[tier])
        for drive in CANONICAL_DRIVES
        for tier in inv.DOMAIN_TIERS
    }
    measurement = inv.subdrive_variance_axis(inv.SubDriveProfile(values=values))
    # values 0,0,0,4 -> mean 1, variance (1+1+1+9)/4 = 3
    assert measurement.measurement == pytest.approx(3.0, rel=1e-12)
    assert measurement.frozen_limit is None


def test_the_subdrive_profile_needs_twenty_eight_values():
    with pytest.raises(inv.InversionError):
        inv.SubDriveProfile(values={("F1", "P"): 1.0})
    with pytest.raises(inv.InversionError):
        inv.SubDriveProfile(
            values={
                (drive, tier): 1.0
                for drive in CANONICAL_DRIVES
                for tier in (*inv.DOMAIN_TIERS, "X")
            }
        )


# --------------------------------------------------------------------------- #
# Axis A — judged, because the chain is frozen at zero violations.
# --------------------------------------------------------------------------- #


def test_axis_a_is_clean_on_a_correctly_ordered_chain():
    measurement = inv.pathway_chain_axis({"A0", "D1", "W1", "P1"})
    assert measurement.measurement == 0.0
    assert measurement.frozen_limit == 0.0
    assert measurement.exceeds_frozen_limit is False


def test_axis_a_reports_each_node_admitted_before_its_prerequisites():
    measurement = inv.pathway_chain_axis({"A0", "D1", "P1"})
    assert measurement.measurement == 1.0
    assert measurement.exceeds_frozen_limit is True
    assert measurement.detail["violations"] == [
        {"node": "P1", "unsatisfied_prerequisites": ["W1"]}
    ]


def test_axis_a_counts_every_violation_and_refuses_unknown_nodes():
    measurement = inv.pathway_chain_axis({"D1", "W2"})
    assert measurement.measurement == 2.0
    assert sorted(row["node"] for row in measurement.detail["violations"]) == ["D1", "W2"]
    with pytest.raises(inv.InversionError):
        inv.pathway_chain_axis({"Z9"})


# --------------------------------------------------------------------------- #
# The report.
# --------------------------------------------------------------------------- #


def test_scan_needs_at_least_one_input():
    with pytest.raises(inv.InversionError):
        inv.scan()


def test_the_report_separates_judged_axes_from_measured_ones():
    report = inv.scan(dials=dials(3, 4, 5, 6, 7, 8, 9, 3, 4, 5), state=uniform_state())
    assert [axis.value for axis in report.frozen_axes] == ["N"]
    assert [axis.value for axis in report.unfrozen_axes] == ["W", "E"]
    assert len(report.all_readings(inv.Axis.NOETIC_INVOLUTION)) == 2
    # the measured-only reading of N is listed, not hidden behind the judged one
    assert any(row.startswith("N:") for row in report.unfrozen_readings)
    assert report.compound is False


def test_the_compound_axis_needs_more_than_one_frozen_exceedance():
    single = inv.scan(dials=dials(3, 4, 3, 9, 7, 8, 9, 3, 4, 5))
    assert [axis.value for axis in single.axes_exceeding_frozen_limits] == ["N"]
    assert single.compound is False

    double = inv.scan(
        dials=dials(3, 4, 3, 9, 7, 8, 9, 3, 4, 5), satisfied={"A0", "D1", "P1"}
    )
    assert sorted(axis.value for axis in double.axes_exceeding_frozen_limits) == ["A", "N"]
    assert double.compound is True


def test_an_unfrozen_reading_can_never_produce_a_compound_finding():
    """Extreme values on every measured-only axis must not manufacture a compound result."""
    extreme = s.from_weights([1e9] + [1e-9] * 39)
    report = inv.scan(
        state=extreme,
        drives=drive_profile(F7=1000.0),
        subdrives=inv.SubDriveProfile(
            values={
                (drive, tier): (0.0 if tier == "P" else 1000.0)
                for drive in CANONICAL_DRIVES
                for tier in inv.DOMAIN_TIERS
            }
        ),
    )
    assert report.axes_exceeding_frozen_limits == ()
    assert report.compound is False
    assert report.axis(inv.Axis.ENTROPY_DEFICIT).measurement > 0.5
    assert report.axis(inv.Axis.ENTROPY_DEFICIT).exceeds_frozen_limit is None


def test_the_report_refuses_to_produce_an_nccs_component():
    report = inv.scan(dials=dials(3, 4, 5, 6, 7, 8, 9, 3, 4, 5))
    text = report.nccs_inversion_resistance
    assert text.startswith("NOT_PRODUCED")
    assert "will not grant scoring authority" in text
    assert "score" not in report.as_dict() or "nccs_inversion_resistance" in report.as_dict()
    assert "nccs" not in {key.lower() for key in report.as_dict() if key != "nccs_inversion_resistance"}


def test_the_report_is_canonically_identifiable():
    first = inv.scan(dials=dials(3, 4, 5, 6, 7, 8, 9, 3, 4, 5), state=uniform_state())
    second = inv.scan(dials=dials(3, 4, 5, 6, 7, 8, 9, 3, 4, 5), state=uniform_state())
    assert first.digest() == second.digest()
    # move a dial that belongs to a frozen pair, so a measured quantity actually changes
    other = inv.scan(dials=dials(3, 4, 3, 6, 7, 8, 9, 3, 4, 5), state=uniform_state())
    assert other.digest() != first.digest()


def test_a_self_dual_dial_does_not_move_the_involution_reading():
    """Only pairs are measured on axis ``N``, so a self-dual dial is correctly irrelevant.

    This is a property of the measurement, not an oversight: the axis is named for involution
    imbalance, and a self-dual Noetic has no partner to be imbalanced with.
    """
    baseline = inv.scan(dials=dials(3, 4, 5, 6, 7, 8, 9, 3, 4, 5), state=uniform_state())
    changed_self_dual = inv.scan(
        dials=dials(9, 4, 5, 6, 7, 8, 9, 3, 4, 5), state=uniform_state()
    )
    assert changed_self_dual.axis(inv.Axis.NOETIC_INVOLUTION).measurement == 1.0
    assert (
        changed_self_dual.axis(inv.Axis.NOETIC_INVOLUTION).measurement
        == baseline.axis(inv.Axis.NOETIC_INVOLUTION).measurement
    )
    assert changed_self_dual.digest() == baseline.digest()


def test_a_caller_supplies_its_own_threshold_and_owns_the_decision():
    measurement = inv.involution_mass_axis(state_concentrated_on("C2"))
    assert measurement.exceeds_frozen_limit is None
    assert measurement.exceeds(0.5) is True
    # the imbalance is a ratio of two strictly positive masses, so it is strictly below 1
    assert measurement.measurement < 1.0
    assert measurement.exceeds(1.0) is False
    for bad in (True, "0.5", None, float("nan")):
        with pytest.raises(inv.InversionError):
            measurement.exceeds(bad)


def test_asking_for_an_absent_axis_is_an_error():
    report = inv.scan(dials=dials(3, 4, 5, 6, 7, 8, 9, 3, 4, 5))
    assert report.axis(inv.Axis.NOETIC_INVOLUTION).axis is inv.Axis.NOETIC_INVOLUTION
    with pytest.raises(inv.InversionError):
        report.axis(inv.Axis.SUBDRIVE_VARIANCE)
    with pytest.raises(inv.InversionError):
        report.all_readings(inv.Axis.SUBDRIVE_VARIANCE)


# --------------------------------------------------------------------------- #
# The state-index authority shared by noetica, simplex and inversions.
# --------------------------------------------------------------------------- #


def test_the_state_index_is_a_bijection_onto_the_forty_components():
    assert len(n.STATE_INDEX) == 40
    assert sorted(n.STATE_INDEX.values()) == list(range(40))
    assert n.STATE_INDEX[n.COGNITIVE_STATES[0]] == 0
    for index, label in enumerate(n.COGNITIVE_STATES):
        assert n.state_at(index) == label
        assert n.index_of(label) == index
    assert s.NUM_STATES == len(n.STATE_INDEX)


def test_the_state_index_refuses_bad_lookups():
    with pytest.raises(n.NoeticaError):
        n.state_at(40)
    with pytest.raises(n.NoeticaError):
        n.state_at(-1)
    with pytest.raises(n.NoeticaError):
        n.state_at(True)
    with pytest.raises(n.NoeticaError):
        n.index_of("Z0")


def test_the_inversion_masses_read_the_state_index_rather_than_assume_layout():
    """The one thing that could silently disagree between the two modules."""
    state = state_concentrated_on("C5")
    assert n.index_of("C5") == 15
    assert inv._domain_mass(state, "C") > 0.99
    assert inv._domain_mass(state, "P") < 0.01
    assert inv._noetic_mass(state, 5) > 0.99
    assert inv._noetic_mass(state, 4) < 0.01
    # and the counts line up with the simplex module
    assert math.fsum(inv._domain_mass(state, tier) for tier in inv.DOMAIN_TIERS) == pytest.approx(
        1.0, rel=1e-9
    )
    assert math.fsum(inv._noetic_mass(state, noetic) for noetic in range(10)) == pytest.approx(
        1.0, rel=1e-9
    )


# --------------------------------------------------------------------------- #
# Purity.
# --------------------------------------------------------------------------- #


def test_the_scanner_declares_no_numeric_runtime_or_clock():
    source = Path(inv.__file__).read_text(encoding="utf-8")
    for forbidden in ("\nimport torch", "\nfrom torch", "\nimport numpy", "\nfrom numpy"):
        assert forbidden not in source
    for module in ("datetime", "random", "time", "uuid"):
        assert f"\nimport {module}" not in source
        assert f"\nfrom {module}" not in source
