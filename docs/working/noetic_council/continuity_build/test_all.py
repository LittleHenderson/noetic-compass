"""test_all.py -- one runnable test file for the continuity build. No pytest needed.

WHAT THIS FILE DOES
-------------------
It proves every rule the owning instruction names, with explicit cases and explicit
numbers, and prints one PASS or FAIL line per case plus a total. Run it with:

    python -B test_all.py

It covers:
  * a seam that fires (head changed AND step at or above the threshold);
  * a seam that does NOT fire because only the step was big (head unchanged);
  * a seam that does NOT fire because only the head changed (step below the threshold);
  * the inclusive boundary (a step exactly equal to the threshold fires);
  * proof that station crossings inside one thought are never seams, at any threshold;
  * a non-simplex input refused as NOT_ON_OPEN_SIMPLEX;
  * interpolation across a seam refused as NO_INTERPOLATION_ACROSS_SEAM;
  * two heads held as CO_PRESENT and never averaged;
  * the shuffled-injection control producing zero CREATED, and raising when it does not;
  * the full disengage ladder, the disengage-without-reason refusal, and the terminal
    behaviour;
  * the frozen threshold table's sha256, and that no threshold was invented;
  * that README.md states the claim ceiling and lists every UNDECIDED IN DESIGN line.

WHAT THIS FILE DOES NOT DO
--------------------------
  * It does NOT prove that anything was thought, carried, or understood. Every case here is
    a mechanism check. The claim ceiling is on every line of this build for that reason.
  * It does NOT run a brain, a faculty, a language parser, a renderer, or the Recursive
    Possibility Atlas -- none of those are in this build.
  * It does NOT use pytest, numpy, torch, any network, or any cloud service. Standard
    library only, and it runs in well under a second on this machine.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. NOT THE BRAIN FEATURE. THE ATLAS LINK IS NOT BUILT.
"""

from __future__ import annotations

import json
import math
import os
import platform
import re
import sys

BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

import continuity
import disengage
import provenance
import seams
import stations

CLAIM_CEILING = "MECHANISM ONLY. NOT THE BRAIN FEATURE. THE ATLAS LINK IS NOT BUILT."

#: The cases, in the order they run.
CASES = []


def case(function):
    """Register one test case."""
    CASES.append(function)
    return function


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
#: Points of the open 40-state simplex, built the LM-T2 way (floor 1/400 per state).
#: These are TEST POINTS, not measured station points: no tracker is built here.
P_UNIFORM = stations.base_point()                  # every state 0.025
P_STATE0 = stations.base_point({0: 1.0})           # mass crowded onto state 0
P_STATE1 = stations.base_point({1: 1.0})           # mass crowded onto state 1
P_NEAR_STATE0 = stations.base_point({0: 1.0, 5: 0.0001})  # a hair away from P_STATE0

#: A TEST threshold, supplied by hand so the rule can be exercised. It is NOT a calibrated
#: station threshold: the frozen table has none, which is the point of case
#: ``no_invented_thresholds``.
TEST_SEAM_THRESHOLD = 0.5


def record(head, register, point, station="S1", tick=0, thought="T1"):
    """A bare record with the three fields the seam rule reads."""
    return {
        "thought_id": thought,
        "station": station,
        "tick": tick,
        "head_omega": head,
        "leading_register": register,
        "point": point,
    }


def expect_refusal(callable_, code, label="refusal"):
    """Call something that must refuse, and check the refusal's code."""
    try:
        callable_()
    except Exception as exc:  # noqa: BLE001 - the point is to inspect any refusal
        got = getattr(exc, "code", None)
        if got != code:
            raise AssertionError(
                f"expected {label} {code}, got {type(exc).__name__} with code {got!r}: {exc}"
            ) from exc
        return exc
    raise AssertionError(f"expected {label} {code}, but nothing was raised")


def ascii_safe(text):
    """Make a message printable on any console code page."""
    return str(text).encode("ascii", "backslashreplace").decode("ascii")


# --------------------------------------------------------------------------- #
# 1. The station model and the frozen table
# --------------------------------------------------------------------------- #
@case
def station_kinds_are_the_seven_station_md_names():
    kinds = stations.STATION_KINDS
    assert len(kinds) == 7, f"expected 7 station kinds, found {len(kinds)}"
    expected = {
        "THOUGHT_HEAD": "S0",
        "CJT_TRIGGER": "S1",
        "CJT_BIAS": "S2",
        "CJT_ARRIVAL": "S3",
        "OPERATING_POINT": "S4",
        "RPM_LINK": "S5",
        "NEXT_STAGE": "S6",
    }
    for kind, ordinal in expected.items():
        assert kind in kinds, f"station kind {kind} is missing"
        assert kinds[kind]["ordinal"] == ordinal, f"{kind} should sit at {ordinal}"
    for ordinal in stations.STATION_ORDINALS:
        assert stations.kind_of(ordinal) in kinds, f"{ordinal} maps to no kind"
    assert stations.kind_of("S3") == "CJT_ARRIVAL"
    expect_refusal(lambda: stations.kind_of("S7"), "UNKNOWN_STATION", "station refusal")


@case
def frozen_table_digest_and_read_only():
    digest = stations.verify_frozen()
    assert digest == stations.STATION_KINDS_SHA256
    assert re.fullmatch(r"[0-9a-f]{64}", digest), f"{digest!r} is not a sha256"
    # canonical JSON is stable across calls, so the digest cannot drift
    assert stations.canonical_table_json() == stations.canonical_table_json()
    assert json.loads(stations.canonical_table_json())  # it parses, so it is real JSON
    # the exposed table really is read-only
    os_error = None
    try:
        stations.STATION_KINDS["CJT_BIAS"]["seam_threshold"] = 0.5
    except TypeError as exc:
        os_error = exc
    assert os_error is not None, "the frozen table accepted a write; it is not frozen"
    assert stations.STATION_KINDS["CJT_BIAS"]["seam_threshold"] is None


@case
def no_invented_thresholds():
    for ordinal in stations.STATION_ORDINALS:
        record_ = stations.station_record(ordinal)
        assert record_["seam_threshold"] is None, f"{ordinal} invented a seam threshold"
        assert record_["tone_threshold"] is None, f"{ordinal} invented a tone threshold"
        assert record_["drift_threshold"] is None, f"{ordinal} invented a drift threshold"
        assert record_["threshold_status"] == "THRESHOLD_UNDECIDED", (
            f"{ordinal} is not marked THRESHOLD_UNDECIDED"
        )
        assert stations.threshold_of(ordinal, "seam") is None
    dialogue = stations.DIALOGUE_THRESHOLDS_NOT_REUSED
    assert dialogue["seam"] == 0.841069956
    assert dialogue["tone"] == 1.227592661
    assert dialogue["drift"] == 0.984979914
    assert dialogue["licensed_for_station_kinds"] is False, (
        "the dialogue thresholds must not be licensed for station kinds"
    )


# --------------------------------------------------------------------------- #
# 2. The seam rule
# --------------------------------------------------------------------------- #
@case
def seam_fires_when_head_changes_and_step_is_large():
    before = record("Omega_a", None, P_UNIFORM, station="S1", tick=0)
    after = record("Omega_b", None, P_STATE0, station="S1", tick=1)
    step = seams.step_size(P_UNIFORM, P_STATE0)
    assert step > TEST_SEAM_THRESHOLD, f"the test step {step} must be a big one"
    fired, reason = seams.is_seam(before, after, TEST_SEAM_THRESHOLD)
    code, detail = seams.decode_reason(reason)
    assert fired is True, f"the seam should have fired; reason was {reason}"
    assert code == seams.SEAM_HEAD_CHANGED_AND_STEP_AT_OR_ABOVE_THRESHOLD, code
    assert "step" in detail and "threshold" in detail


@case
def seam_boundary_is_inclusive():
    before = record("Omega_a", None, P_UNIFORM)
    after = record("Omega_b", None, P_STATE0)
    step = seams.step_size(P_UNIFORM, P_STATE0)
    fired, reason = seams.is_seam(before, after, step)  # exactly equal
    assert fired is True, f"a step exactly at the threshold must fire; {reason}"
    fired_above, _ = seams.is_seam(before, after, step * (1 + 1e-9))
    assert fired_above is False, "a step just under the threshold must not fire"


@case
def no_seam_when_only_the_step_is_large():
    before = record("Omega_a", None, P_UNIFORM)
    after = record("Omega_a", None, P_STATE0)  # the SAME head
    step = seams.step_size(P_UNIFORM, P_STATE0)
    assert step > TEST_SEAM_THRESHOLD
    fired, reason = seams.is_seam(before, after, TEST_SEAM_THRESHOLD)
    code, detail = seams.decode_reason(reason)
    assert fired is False, "a large step alone is not a seam"
    assert code == seams.NO_SEAM_HEAD_UNCHANGED, code
    assert "unchanged" in detail


@case
def no_seam_when_only_the_head_changes():
    before = record("Omega_a", None, P_STATE0)
    after = record("Omega_b", None, P_NEAR_STATE0)
    step = seams.step_size(P_STATE0, P_NEAR_STATE0)
    assert step < TEST_SEAM_THRESHOLD, f"the test step {step} must be a small one"
    fired, reason = seams.is_seam(before, after, TEST_SEAM_THRESHOLD)
    code, detail = seams.decode_reason(reason)
    assert fired is False, "a head change alone is not a seam"
    assert code == seams.NO_SEAM_STEP_BELOW_THRESHOLD, code
    assert "only the head changed" in detail


@case
def station_crossings_inside_one_thought_are_never_seams():
    path = continuity.ContinuityPath(
        "T-continuity", "Omega_a", leading_register="|A", seam_threshold=0.1
    )
    path.add_crossing("S0", 0, point=P_UNIFORM)
    path.add_crossing("S1", 1, point=P_STATE0)
    path.add_crossing("S2", 2, point=P_UNIFORM)
    path.add_crossing("S3", 3, point=P_STATE1)
    # every neighbouring step really is a big one
    for first, second in zip(path.crossings, path.crossings[1:]):
        assert seams.step_size(first.point, second.point) > 0.1
    checks = path.seam_checks()
    assert len(checks) == 3, f"expected 3 checks, got {len(checks)}"
    for check in checks:
        assert check.fired is False, f"{check.from_station}->{check.to_station} fired"
        assert check.code == seams.NO_SEAM_HEAD_UNCHANGED, check.code
    assert path.seams() == (), "station crossings inside one thought can never be seams"
    # and the same holds with the lowest threshold there is
    zero = continuity.ContinuityPath("T-continuity-2", "Omega_a", seam_threshold=0.0)
    zero.add_crossing("S0", 0, point=P_UNIFORM)
    zero.add_crossing("S1", 1, point=P_STATE0)
    zero.add_crossing("S2", 2, point=P_UNIFORM)
    assert zero.seams() == (), "even at threshold 0 no station crossing is a seam"
    assert zero.summary()["seams"] == 0


@case
def seam_rule_refuses_without_a_threshold():
    before = record("Omega_a", None, P_UNIFORM)
    after = record("Omega_b", None, P_STATE0)
    expect_refusal(
        lambda: seams.is_seam(before, after, None),
        "SEAM_THRESHOLD_UNDECIDED",
        "threshold refusal",
    )
    expect_refusal(
        lambda: seams.is_seam(before, after, -1.0),
        "INVALID_THRESHOLD",
        "threshold refusal",
    )
    path = continuity.ContinuityPath("T-no-threshold", "Omega_a")
    path.add_crossing("S0", 0, point=P_UNIFORM)
    path.add_crossing("S1", 1, point=P_STATE0)
    expect_refusal(lambda: path.seams(), "SEAM_THRESHOLD_UNDECIDED", "path refusal")
    summary = path.summary()
    assert summary["seams"] is None, "an uncomputable seam count must not be reported as 0"
    assert summary["seams_status"] == "THRESHOLD_UNDECIDED"


@case
def head_change_inside_one_thought_is_refused():
    path = continuity.ContinuityPath("T-head", "Omega_a")
    path.add_crossing("S0", 0, point=P_UNIFORM)
    expect_refusal(
        lambda: path.add_crossing("S1", 1, point=P_STATE0, head_omega="Omega_b"),
        "HEAD_CHANGE_INSIDE_ONE_THOUGHT",
        "path refusal",
    )
    assert len(path.crossings) == 1, "the refused crossing must not be added"
    # a new head is a new thought with its own anchor
    other = continuity.ContinuityPath("T-head-2", "Omega_b")
    other.add_crossing("S0", 0, point=P_STATE0)
    held = seams.hold_together(path.anchor(), other.anchor())
    assert held.label == "CO_PRESENT"
    assert held.points[0] != held.points[1]


# --------------------------------------------------------------------------- #
# 3. The open simplex, the step size, and the refusal to interpolate
# --------------------------------------------------------------------------- #
@case
def not_on_open_simplex_refused():
    bad_sum = tuple(1.1 / seams.POINT_DIMENSION for _ in range(seams.POINT_DIMENSION))
    zero_entry = list(P_UNIFORM)
    zero_entry[3] = 0.0
    zero_entry[0] += P_UNIFORM[3]
    negative = list(P_UNIFORM)
    negative[3] = -0.001
    negative[0] += P_UNIFORM[3] + 0.001
    wrong_length = tuple(0.2 for _ in range(5))
    cases = {
        "sums to 1.1": bad_sum,
        "a zero entry": tuple(zero_entry),
        "a negative entry": tuple(negative),
        "five states instead of forty": wrong_length,
    }
    for label, bad in cases.items():
        error = expect_refusal(
            lambda bad=bad: seams.step_size(bad, P_UNIFORM),
            "NOT_ON_OPEN_SIMPLEX",
            f"simplex refusal ({label})",
        )
        assert error.detail, f"{label} was refused with no detail"
    # a good point passes, and the distance is a real number in [0, pi]
    good = seams.step_size(P_UNIFORM, P_STATE0)
    assert 0.0 < good <= math.pi, f"{good} is not a distance"
    with_bad_numbers = list(P_UNIFORM)
    with_bad_numbers[0] = float("nan")
    expect_refusal(
        lambda: seams.step_size(tuple(with_bad_numbers), P_UNIFORM),
        "NOT_ON_OPEN_SIMPLEX",
        "simplex refusal (NaN)",
    )


@case
def interpolation_across_a_seam_refused():
    error = expect_refusal(
        lambda: seams.never_interpolate(P_UNIFORM, P_STATE0),
        "NO_INTERPOLATION_ACROSS_SEAM",
        "interpolation refusal",
    )
    assert "never averaged" in error.detail, "the refusal must say what it refuses"
    assert not hasattr(seams, "interpolate"), "there must be no interpolator in this build"
    assert not hasattr(seams, "midpoint"), "there must be no midpoint function either"


@case
def hold_together_is_co_present_and_not_averaged():
    held = seams.hold_together(P_UNIFORM, P_STATE0)
    assert held.label == "CO_PRESENT", held.label
    assert held.operator == "+", held.operator
    assert held.points[0] == P_UNIFORM
    assert held.points[1] == P_STATE0
    assert held.as_dict()["averaged"] is False
    assert held.distance == seams.step_size(P_UNIFORM, P_STATE0)
    # the record is not an average: a real midpoint would be a third, different point
    midpoint = tuple((a + b) / 2.0 for a, b in zip(P_UNIFORM, P_STATE0))
    assert seams.step_size(midpoint, P_UNIFORM) > 1e-6, "the hold must not be a blend"
    assert seams.step_size(midpoint, P_STATE0) > 1e-6


@case
def step_size_agrees_with_the_stable_form():
    pairs = [
        (P_UNIFORM, P_UNIFORM),
        (P_UNIFORM, P_STATE0),
        (P_STATE0, P_NEAR_STATE0),
        (P_UNIFORM, P_STATE1),
        (P_STATE0, P_STATE1),
    ]
    for left, right in pairs:
        direct = seams.step_size(left, right)
        stable = seams.step_size_stable(left, right)
        assert abs(direct - stable) < 1e-9, f"{direct} vs {stable} disagree"
        assert 0.0 <= direct <= math.pi
        assert abs(seams.step_size(left, right) - seams.step_size(right, left)) < 1e-12, (
            "the distance must be symmetric"
        )
    assert seams.step_size(P_UNIFORM, P_UNIFORM) <= 1e-9, "a point to itself is zero distance"


# --------------------------------------------------------------------------- #
# 4. The path builder
# --------------------------------------------------------------------------- #
@case
def points_and_form_gaps_are_counted():
    path = continuity.ContinuityPath("T-points", "Omega_a", seam_threshold=0.5)
    path.add_crossing("S0", 0, point=P_UNIFORM)
    path.add_crossing("S1", 1, point=P_STATE0)
    gap = path.add_crossing("S4", 2)  # S4 has no CCE form at all (TAP_AND_INJECT.md:49)
    path.add_crossing("S5", 3, point=P_UNIFORM)
    assert gap.form_gap is True and gap.point is None
    assert len(path.points()) == 3, f"expected 3 points, got {len(path.points())}"
    assert path.form_gaps == 1, f"expected 1 FORM gap, got {path.form_gaps}"
    summary = path.summary()
    assert summary["crossings"] == 4
    assert summary["points"] == 3
    assert summary["form_gaps"] == 1
    assert summary["seams"] == 0
    assert summary["nested_depth_max"] == 0
    assert [point.station for point in path.points()] == ["S0", "S1", "S5"]


@case
def anchor_and_displacement():
    path = continuity.ContinuityPath("T-anchor", "Omega_a", seam_threshold=0.5)
    path.add_crossing("S0", 0, point=P_UNIFORM)
    path.add_crossing("S1", 1, point=P_STATE0)
    path.add_crossing("S2", 2, point=P_NEAR_STATE0)
    assert path.anchor() == P_UNIFORM, "the anchor is the S0 point"
    assert path.displacement("S0") <= 1e-9, "the anchor's displacement from itself is zero"
    assert abs(path.displacement("S1") - seams.step_size(P_UNIFORM, P_STATE0)) < 1e-12
    assert abs(path.displacement("S2") - seams.step_size(P_UNIFORM, P_NEAR_STATE0)) < 1e-12
    assert path.displacement(1) == path.displacement("S1"), "index and station must agree"
    # a path with no S0 crossing has no anchor
    no_anchor = continuity.ContinuityPath("T-no-s0", "Omega_a")
    no_anchor.add_crossing("S1", 0, point=P_UNIFORM)
    expect_refusal(lambda: no_anchor.anchor(), "NO_S0_CROSSING", "anchor refusal")


@case
def displacement_refuses_a_station_with_no_point():
    path = continuity.ContinuityPath("T-gap-displacement", "Omega_a", seam_threshold=0.5)
    path.add_crossing("S0", 0, point=P_UNIFORM)
    path.add_crossing("S4", 1)  # no point: a FORM gap at S4
    expect_refusal(
        lambda: path.displacement("S4"), "NO_POINT_AT_STATION", "displacement refusal"
    )
    # the head itself can be a FORM gap, and then there is no anchor to measure from
    headless = continuity.ContinuityPath("T-headless", "Omega_a")
    headless.add_crossing("S0", 0)  # the order shape has no CCE form
    expect_refusal(lambda: headless.anchor(), "ANCHOR_HAS_NO_POINT", "anchor refusal")
    assert headless.form_gaps == 1
    assert headless.points() == ()


@case
def nested_depth_cap():
    path = continuity.ContinuityPath("T-depth", "Omega_a", seam_threshold=0.5)
    path.add_crossing("S0", 0, point=P_UNIFORM)
    path.add_crossing("S1", 1, point=P_STATE0, depth=5)
    assert path.summary()["nested_depth_max"] == 5
    expect_refusal(
        lambda: path.add_crossing("S1", 2, point=P_STATE0, depth=6),
        "DEPTH_CAP",
        "depth refusal",
    )
    assert len(path.crossings) == 2, "the refused crossing must not be added"


@case
def same_station_twice_needs_an_index():
    path = continuity.ContinuityPath("T-twice", "Omega_a", seam_threshold=0.5)
    path.add_crossing("S0", 0, point=P_UNIFORM)
    path.add_crossing("S1", 1, point=P_STATE0)          # the outer CJT
    path.add_crossing("S1", 2, point=P_NEAR_STATE0)     # a nested level, same station code
    expect_refusal(
        lambda: path.displacement("S1"), "STATION_OCCURS_MORE_THAN_ONCE", "displacement refusal"
    )
    assert abs(path.displacement(1) - seams.step_size(P_UNIFORM, P_STATE0)) < 1e-12
    assert abs(path.displacement(2) - seams.step_size(P_UNIFORM, P_NEAR_STATE0)) < 1e-12


@case
def drift_is_reported_with_its_clarify():
    # a threshold pair supplied by hand: seam above the steps, drift below the displacement
    path = continuity.ContinuityPath(
        "T-drift", "Omega_a", seam_threshold=3.0, drift_threshold=1.0
    )
    path.add_crossing("S0", 0, point=P_UNIFORM)
    path.add_crossing("S1", 1, point=P_STATE0)
    records = path.drift_checks()
    assert len(records) == 1, f"expected 1 drift reading, got {len(records)}"
    reading = records[0]
    assert reading.displacement >= 1.0
    assert reading.drifting is True, f"drift should be flagged; reason was {reading.reason}"
    assert reading.clarify is not None and "Are we still on" in reading.clarify
    assert "Omega_a" in reading.clarify
    # with a seam threshold below the step, the movement is a seam-sized step, not drift
    no_drift = continuity.ContinuityPath(
        "T-drift-2", "Omega_a", seam_threshold=0.5, drift_threshold=1.0
    )
    no_drift.add_crossing("S0", 0, point=P_UNIFORM)
    no_drift.add_crossing("S1", 1, point=P_STATE0)
    assert no_drift.drift_checks()[0].drifting is False
    assert no_drift.drift_checks()[0].clarify is None


@case
def drift_refuses_without_a_threshold():
    path = continuity.ContinuityPath("T-drift-3", "Omega_a", seam_threshold=0.5)
    path.add_crossing("S0", 0, point=P_UNIFORM)
    path.add_crossing("S1", 1, point=P_STATE0)
    expect_refusal(
        lambda: path.drift_checks(), "DRIFT_THRESHOLD_UNDECIDED", "drift refusal"
    )


# --------------------------------------------------------------------------- #
# 5. Provenance: FOLLOWED, CREATED, ATTEMPTED
# --------------------------------------------------------------------------- #
FACULTY_WRITER = {"kind": "FACULTY", "phi": "Phi<8:9:6:0>"}
INJECTION_WRITER = {"kind": "INJECTION", "turn": 12}


def pointer(next_station, written_tick=None, writer=None, control=None, pointer_id=None):
    """A next-station pointer record, with only the fields this build reads."""
    out = {"next_station": next_station}
    if written_tick is not None:
        out["written_tick"] = written_tick
    if writer is not None:
        out["writer"] = writer
    if control is not None:
        out["control"] = control
    if pointer_id is not None:
        out["pointer_id"] = pointer_id
    return out


def entry(thought, station, tick, next_pointer):
    """One entry of the append-only path record."""
    return {
        "thought_id": thought,
        "station": station,
        "tick": tick,
        "next_pointer": next_pointer,
    }


@case
def provenance_followed():
    earlier = entry("T-9", "S1", 1, pointer("S2"))
    crossing = entry("T-9", "S1", 5, pointer("S2"))
    word, reason = provenance.classify(crossing, [earlier], {})
    code, detail = provenance.decode_reason(reason)
    assert word == provenance.FOLLOWED, f"expected FOLLOWED, got {word}: {reason}"
    assert code == provenance.POINTER_EXISTED_BEFORE_TICK, code
    assert "before this tick" in detail, detail
    # a record at the SAME tick is not an earlier record
    same_tick = entry("T-9", "S1", 5, pointer("S2"))
    expect_refusal(
        lambda: provenance.classify(crossing, [same_tick], {}),
        "PROVENANCE_UNDECIDABLE",
        "provenance refusal",
    )


@case
def provenance_created_admitted_and_answered():
    admitted = entry("T-9", "S2", 7, pointer("S3", written_tick=7, writer=FACULTY_WRITER))
    key = provenance.pointer_key("T-9", "S2", 7, "S3")
    word, reason = provenance.classify(admitted, [], {key: {"status": "ADMITTED"}})
    code, detail = provenance.decode_reason(reason)
    assert word == provenance.CREATED, f"expected CREATED, got {word}: {reason}"
    assert code == provenance.WRITTEN_THIS_TICK_AND_CONTINUATION_ADMITTED, code
    assert "Phi<8:9:6:0>" in detail, "the faculty's Phi word must be logged"

    answered = entry("T-9", "S5", 8, pointer("S6", written_tick=8, writer=INJECTION_WRITER))
    key2 = provenance.pointer_key("T-9", "S5", 8, "S6")
    word2, reason2 = provenance.classify(answered, [], {key2: {"status": "ANSWERED"}})
    code2, detail2 = provenance.decode_reason(reason2)
    assert word2 == provenance.CREATED, f"expected CREATED, got {word2}: {reason2}"
    assert code2 == provenance.WRITTEN_THIS_TICK_AND_CONTINUATION_ANSWERED, code2
    assert "turn 12" in detail2, "the injection's turn index must be logged"


@case
def provenance_attempted_refused_held_and_open():
    crossing = entry("T-9", "S3", 9, pointer("S4", written_tick=9, writer=FACULTY_WRITER))
    key = provenance.pointer_key("T-9", "S3", 9, "S4")
    for status, expected_code in (
        ("REFUSED", provenance.WRITTEN_THIS_TICK_CONTINUATION_REFUSED),
        ("HELD", provenance.WRITTEN_THIS_TICK_CONTINUATION_HELD),
        ("OPEN", provenance.WRITTEN_THIS_TICK_CONTINUATION_STILL_OPEN),
    ):
        word, reason = provenance.classify(crossing, [], {key: {"status": status}})
        code, _ = provenance.decode_reason(reason)
        assert word == provenance.ATTEMPTED, f"{status} should be ATTEMPTED, got {word}"
        assert code == expected_code, f"{status}: expected {expected_code}, got {code}"
    # an outcome that is not on record at all stays open at the end
    word, reason = provenance.classify(crossing, [], {})
    code, _ = provenance.decode_reason(reason)
    assert word == provenance.ATTEMPTED
    assert code == provenance.WRITTEN_THIS_TICK_CONTINUATION_STILL_OPEN
    assert provenance.WORDS == ("FOLLOWED", "CREATED", "ATTEMPTED")


@case
def provenance_refuses_a_pointer_with_no_provenance():
    no_pointer = {"thought_id": "T-9", "station": "S6", "tick": 10, "next_pointer": None}
    expect_refusal(
        lambda: provenance.classify(no_pointer, [], {}),
        "PROVENANCE_UNDECIDABLE",
        "provenance refusal",
    )
    undated = entry("T-9", "S1", 4, pointer("S2"))
    expect_refusal(
        lambda: provenance.classify(undated, [], {}),
        "PROVENANCE_UNDECIDABLE",
        "provenance refusal",
    )
    stale = entry("T-9", "S1", 4, pointer("S2", written_tick=1, writer=FACULTY_WRITER))
    expect_refusal(
        lambda: provenance.classify(stale, [], {}),
        "POINTER_NOT_IN_PATH_RECORD",
        "provenance refusal",
    )


@case
def provenance_refuses_an_unnamed_writer():
    loop_written = entry(
        "T-9", "S0", 3, pointer("S1", written_tick=3, writer={"kind": "DRIVE_LOOP_ARM"})
    )
    expect_refusal(
        lambda: provenance.classify(loop_written, [], {}),
        "PROVENANCE_UNDECIDABLE",
        "provenance refusal",
    )
    nameless_faculty = entry(
        "T-9", "S0", 3, pointer("S1", written_tick=3, writer={"kind": "FACULTY"})
    )
    expect_refusal(
        lambda: provenance.classify(nameless_faculty, [], {}),
        "BAD_POINTER",
        "provenance refusal",
    )


@case
def shuffled_control_produces_zero_created():
    crossings = [
        entry(
            "T-c",
            "S1",
            1,
            pointer("S2", written_tick=1, writer=FACULTY_WRITER, control="SHUFFLED"),
        ),
        entry(
            "T-c",
            "S2",
            2,
            pointer("S3", written_tick=2, writer=INJECTION_WRITER, control="SHUFFLED"),
        ),
        entry("T-c", "S3", 3, pointer("S4", written_tick=3, writer=FACULTY_WRITER)),
    ]
    later_outcomes = {
        provenance.pointer_key("T-c", "S1", 1, "S2"): {"status": "HELD"},
        provenance.pointer_key("T-c", "S2", 2, "S3"): {"status": "REFUSED"},
        provenance.pointer_key("T-c", "S3", 3, "S4"): {"status": "ADMITTED"},
    }
    rows = provenance.classify_all(crossings, [], later_outcomes)
    words = [row["word"] for row in rows]
    assert words == ["ATTEMPTED", "ATTEMPTED", "CREATED"], words
    created_on_control = [
        row for row in rows if row["control"] == "SHUFFLED" and row["word"] == "CREATED"
    ]
    assert created_on_control == [], "the shuffled control produced a CREATED continuation"
    checked = provenance.assert_shuffled_control(rows)
    assert checked == 2, f"expected 2 shuffled records checked, got {checked}"


@case
def shuffled_control_raises_on_a_created():
    # a shuffled pointer whose continuation is admitted: the control MUST fail
    crossing = entry(
        "T-c", "S1", 1, pointer("S2", written_tick=1, writer=FACULTY_WRITER, control="SHUFFLED")
    )
    key = provenance.pointer_key("T-c", "S1", 1, "S2")
    rows = provenance.classify_all([crossing], [], {key: {"status": "ADMITTED"}})
    assert rows[0]["word"] == "CREATED"
    error = expect_refusal(
        lambda: provenance.assert_shuffled_control(rows),
        "SHUFFLED_CONTROL_PRODUCED_CREATED",
        "control failure",
    )
    assert "CREATED" in str(error)


@case
def shuffled_control_raises_when_empty():
    expect_refusal(
        lambda: provenance.assert_shuffled_control([]),
        "SHUFFLED_CONTROL_EMPTY",
        "control failure",
    )
    unlabelled = [{"word": "ATTEMPTED"}]
    expect_refusal(
        lambda: provenance.assert_shuffled_control(unlabelled),
        "BAD_CONTROL_RECORD",
        "control failure",
    )


# --------------------------------------------------------------------------- #
# 6. The disengage ladder
# --------------------------------------------------------------------------- #
GAP = "the batch size for the second board"


@case
def disengage_full_ladder():
    ladder = disengage.DisengageLadder(GAP)
    assert ladder.state == disengage.NOT_DECLARED
    first = ladder.step()
    assert first.step == disengage.NOT_DECLARED
    assert first.utterance is None, "the design gives no sentence for the first step"
    assert first.terminal is False
    second = ladder.step()
    assert second.step == disengage.CONFUSED
    assert second.utterance == disengage.FIXED_CANNOT_TELL
    third = ladder.step()
    assert third.step == disengage.ASK_CLARITY
    assert third.utterance == f"I need {GAP}. What is it?", third.utterance
    assert third.terminal is False
    reason = "the batch size was never supplied after it was asked for"
    fourth = ladder.step(reason=reason)
    assert fourth.step == disengage.DISENGAGE
    assert fourth.reason == reason
    assert fourth.terminal is True
    receipt = ladder.receipt
    assert len(receipt) == 4, f"expected 4 receipt entries, got {len(receipt)}"
    assert [row["step"] for row in receipt] == list(disengage.STEPS)
    assert all(row["gap"] == GAP for row in receipt), "every entry must name the gap"
    assert receipt[3]["reason"] == reason, "the disengage entry must carry the reason"
    assert ladder.steps_taken == disengage.STEPS
    assert len(ladder.utterances) == 3, "step 1 says nothing, so 3 sentences were said"


@case
def disengage_needs_a_reason():
    ladder = disengage.DisengageLadder(GAP)
    ladder.step()
    ladder.step()
    ladder.step()  # now sitting at DISENGAGE
    assert ladder.state == disengage.DISENGAGE
    for bad_reason in (None, "", "   "):
        expect_refusal(
            lambda bad_reason=bad_reason: ladder.step(reason=bad_reason),
            "DISENGAGE_NEEDS_REASON",
            "disengage refusal",
        )
        assert ladder.terminal is False, "a refused disengage must not end the turn"
        assert ladder.state == disengage.DISENGAGE, "the ladder must stay at the disengage step"
    assert len(ladder.receipt) == 3, "a refused step must not be recorded as a step"
    assert len(ladder.refusals) == 3, "the refusals must still be recorded"
    # a real reason does go through
    final = ladder.step(reason="no source names a batch size")
    assert final.terminal is True
    assert len(ladder.receipt) == 4


@case
def disengage_is_terminal():
    ladder = disengage.DisengageLadder(GAP)
    ladder.step()
    ladder.step()
    ladder.step()
    ladder.step(reason="nothing supplied it")
    before = ladder.receipt
    said = ladder.utterances
    again = ladder.step(reason="one more try")
    assert again.status == disengage.ALREADY_DISENGAGED, again.status
    assert again.terminal is True
    assert again.utterance is None, "a terminal ladder must not speak again"
    assert again.gap_value is None
    assert ladder.receipt == before, "a second call must not append to the receipt"
    assert ladder.utterances == said, "a second call must not say anything"
    assert len(ladder.receipt) == 4


@case
def disengage_never_guesses_and_names_the_gap():
    ladder = disengage.DisengageLadder(GAP)
    results = [ladder.step(), ladder.step(), ladder.step()]
    results.append(ladder.step(reason="the gap was never filled"))
    for result in results:
        assert result.gap_value is None, "no step may fill the gap"
        assert result.gap == GAP, "every step must name the gap it is about"
    assert results[2].utterance.startswith(f"I need {GAP}"), results[2].utterance
    assert results[2].utterance.endswith("What is it?"), results[2].utterance
    # a vague ask is impossible: with no gap name the ladder refuses to ask at all
    vague = disengage.DisengageLadder("   ")
    vague.step()
    vague.step()
    expect_refusal(
        lambda: vague.step(), "CLARITY_ASK_NEEDS_GAP", "clarity-ask refusal"
    )
    assert vague.state == disengage.ASK_CLARITY, (
        "it stays at the ask it cannot word; it never asks vaguely"
    )
    assert vague.terminal is False


@case
def run_ladder_disengages():
    run = disengage.run_ladder(GAP)
    assert run.outcome == disengage.OUTCOME_DISENGAGED, run.outcome
    assert run.steps == disengage.STEPS, run.steps
    assert run.terminal is True
    assert run.reason and GAP in run.reason, run.reason
    assert run.ask == f"I need {GAP}. What is it?", run.ask
    assert len(run.receipt) == 4
    as_dict = run.as_dict()
    assert as_dict["outcome"] == disengage.OUTCOME_DISENGAGED
    assert len(as_dict["receipt"]) == 4


@case
def run_ladder_info_supplied_returns_to_normal():
    run = disengage.run_ladder(GAP, info_provided=True)
    assert run.outcome == disengage.OUTCOME_RESUMED_NORMAL, run.outcome
    assert run.terminal is False, "supplying the information must not end the turn"
    assert disengage.DISENGAGE not in run.steps, run.steps
    assert run.steps == (
        disengage.NOT_DECLARED,
        disengage.CONFUSED,
        disengage.ASK_CLARITY,
    ), run.steps
    assert run.reason is None, "nothing was disengaged, so there is no disengage reason"
    assert run.ask == f"I need {GAP}. What is it?"
    assert run.receipt[-1]["step"] == disengage.ASK_CLARITY
    assert len(run.receipt) == 3


# --------------------------------------------------------------------------- #
# 7. The README: the claim ceiling, and every undecided line
# --------------------------------------------------------------------------- #
@case
def readme_states_the_claim_ceiling_and_every_undecided_line():
    readme_path = os.path.join(BUILD_DIR, "README.md")
    assert os.path.isfile(readme_path), "README.md is missing"
    with open(readme_path, encoding="utf-8") as handle:
        readme = handle.read()
    assert CLAIM_CEILING in readme, "README.md must carry the claim ceiling verbatim"
    assert "NOT LICENSED" in readme, "README.md must state the RPA claim is not licensed"
    assert "Recursive Possibility Atlas" in readme
    undecided = []
    marker = re.compile(r"#\s*UNDECIDED IN DESIGN:\s*(.+)$")
    for name in ("stations.py", "seams.py", "continuity.py", "provenance.py", "disengage.py"):
        path = os.path.join(BUILD_DIR, name)
        assert os.path.isfile(path), f"{name} is missing"
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                found = marker.search(line.rstrip("\n"))
                if found:
                    undecided.append(found.group(1).strip())
    assert undecided, "no UNDECIDED IN DESIGN line was found at all"
    assert len(undecided) >= 10, f"only {len(undecided)} undecided lines found"
    missing = [question for question in undecided if question not in readme]
    assert not missing, (
        f"README.md does not list {len(missing)} undecided line(s), first: {missing[0][:90]}"
    )


# --------------------------------------------------------------------------- #
# The runner
# --------------------------------------------------------------------------- #
MODULE_FILES = ("stations.py", "seams.py", "continuity.py", "provenance.py", "disengage.py")


def undecided_questions():
    """Every UNDECIDED IN DESIGN question marked in the five modules."""
    marker = re.compile(r"#\s*UNDECIDED IN DESIGN:\s*(.+)$")
    questions = []
    for name in MODULE_FILES:
        with open(os.path.join(BUILD_DIR, name), encoding="utf-8") as handle:
            for line in handle:
                found = marker.search(line.rstrip("\n"))
                if found:
                    questions.append(found.group(1).strip())
    return questions


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (ValueError, OSError):  # pragma: no cover - a console that refuses
                pass
    print("continuity_build / test_all.py")
    print(f"python: {platform.python_version()}  platform: {platform.system()}")
    print(f"build folder: {BUILD_DIR}")
    print(f"frozen station-kind table sha256: {stations.STATION_KINDS_SHA256}")
    print(f"claim ceiling: {CLAIM_CEILING}")
    print(f"undecided markers in the build: {len(undecided_questions())}")
    print("-" * 78)
    passed = 0
    failed = 0
    for function in CASES:
        name = function.__name__
        try:
            function()
        except Exception as exc:  # noqa: BLE001 - a test runner must catch everything
            failed += 1
            print(f"FAIL {name}: {ascii_safe(type(exc).__name__)}: {ascii_safe(exc)}")
        else:
            passed += 1
            print(f"PASS {name}")
    print("-" * 78)
    total = passed + failed
    print(f"TOTAL {total} cases: {passed} passed, {failed} failed")
    print("RESULT:", "ALL PASS" if failed == 0 else "FAILURES PRESENT")
    print(f"claim ceiling, repeated: {CLAIM_CEILING}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
