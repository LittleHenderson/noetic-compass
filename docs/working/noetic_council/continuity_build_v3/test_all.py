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

It also covers the REAL atlas (rebound in continuity_build_v3). Every case in that section runs
against the CAS-RPU Recursive Possibility Atlas copied read-only into ``real_atlas/`` from branch
``codex/helm-rpa-recorded-run-20260922`` at commit
``eb9985566bd11a89f485d627186ef0efa7177f02``; no stand-in atlas is imported, built or present:

  * the six copied files still hash to the recorded sha256, and the classes this build uses are
    the real model's own objects, not copies of them;
  * a snapshot with a duplicate node id is refused by the real model, and a node's
    ``region_digest`` changes when its members change;
  * a link naming a node the snapshot does not hold is refused, and so is an empty snapshot;
  * a ``contains_part`` cycle, and a link from a node to itself, are refused;
  * a crossing between two different sorts with no declaration is refused, and the declaration
    is inside the crossing's digest;
  * a Crossing is accepted only when the real link really joins those two real nodes, and its
    relation is a real ``LinkType`` with both real region digests on it;
  * ``is_cjt`` is True for a Crossing and False for an AtlasNode, an AtlasLink and a dict;
  * S0 binds to a real atlas node, and a missing node is refused;
  * a path across three real nodes gives an ordered digest list and 0 sort pollution;
  * **S0 anchors on a real ``AtlasNode.region_digest()``**, recomputed with the real model's own
    hasher and required to match;
  * **glue-back is decided by the real ``compatibility()`` and ``certify_overlap()``**, proved by
    substituting both real functions and watching the adapter's answer follow them;
  * **a refused glue-back is surfaced** as a typed refusal carrying the real model's words;
  * **the stand-in is gone**: the file is absent, no module imports it, and an object that
    imitates it is refused by S0.

WHAT THIS FILE DOES NOT DO
--------------------------
  * It does NOT prove that anything was thought, carried, or understood. Every case here is
    a mechanism check. The claim ceiling is on every line of this build for that reason.
  * It does NOT prove that language crossed the atlas. No case here uses language at all:
    a node's fields are short data strings, nothing is parsed or rendered, and the
    one claim the design labels NOT LICENSED stays unclaimed.
  * It does NOT run a brain, a faculty, a language parser, or a renderer -- none of those
    are in this build.
  * It does NOT use pytest, numpy, torch, any network, or any cloud service. Standard
    library plus the real model's own dependencies only, and it runs in well under a second
    on this machine.

CLAIM CEILING (verbatim from the owning instruction):
    MECHANISM ONLY. THE ATLAS IS A MINIMAL OBJECT, NOT HELM VISION ABILITY 6 AT FULL SCOPE. NO LANGUAGE PASSED ACROSS IT.
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

import atlas_adapter
import continuity
import crossings
import disengage
import provenance
import seams
import stations

CLAIM_CEILING = (
    "MECHANISM ONLY. THE ATLAS IS A MINIMAL OBJECT, NOT HELM VISION ABILITY 6 AT FULL "
    "SCOPE. NO LANGUAGE PASSED ACROSS IT."
)

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
# 7. The REAL Recursive Possibility Atlas, and the CJT crossing
# --------------------------------------------------------------------------- #
# Everything in this section runs against the real atlas model copied into
# ``real_atlas/`` -- the CAS-RPU model from branch codex/helm-rpa-recorded-run-20260922 at
# commit eb9985566bd11a89f485d627186ef0efa7177f02. No stand-in atlas is imported or built
# here, and no atlas class is defined in this build.
from real_atlas.canonical import digest as real_digest

AtlasContext = atlas_adapter.AtlasContext
AtlasLink = atlas_adapter.AtlasLink
AtlasNode = atlas_adapter.AtlasNode
AtlasSnapshot = atlas_adapter.AtlasSnapshot
LinkType = atlas_adapter.LinkType
NodeKind = atlas_adapter.NodeKind
NodeStatus = atlas_adapter.NodeStatus

#: One real context, shared by every node built here, so a crossing is not refused for a
#: context mismatch that has nothing to do with the rule under test.
REAL_CONTEXT = AtlasContext(
    context_id="ctx-circuit",
    model_version="cas-rpa/0.1",
    observation_id="obs-1",
    observation_time="2026-10-16T00:00:00Z",
    record_version=1,
)


def real_node(
    node_id,
    *,
    kind=NodeKind.IDEA_CONTEXT,
    status=NodeStatus.OBSERVED,
    members=None,
    fields=(("board_1", "copied into memory"),),
    idea_id="idea-main",
):
    """One real ``AtlasNode``. Members and fields are chosen sorted, as the real model asks."""
    return AtlasNode(
        node_id=node_id,
        idea_id=idea_id,
        label=node_id,
        context=REAL_CONTEXT,
        status=status,
        kind=kind,
        members=members,
        fields=fields,
    )


def real_link(link_id, source_id, target_id, relation=LinkType.CONTAINS_PART):
    """One real ``AtlasLink``, with the field the relation type requires and no other."""
    if relation is LinkType.CONTAINS_PART:
        return AtlasLink(
            link_id=link_id,
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            projection="the part this node names",
        )
    return AtlasLink(
        link_id=link_id, source_id=source_id, target_id=target_id, relation=relation
    )


def circuit_snapshot():
    """The test circuit as a REAL ``AtlasSnapshot``: four nodes, two links, one present state.

    The node statuses differ on purpose. ``S1-trigger`` is observed and
    ``S0-possibilities`` is hypothetical, so a crossing between them is a crossing between
    two sorts and must be declared. The member sets overlap by one route, so the real
    model's own ``certify_overlap`` can certify them.
    """
    state = real_node(
        "state-now",
        kind=NodeKind.STATE,
        status=NodeStatus.OBSERVED,
        fields=(("board_1", "copied into memory"), ("board_2", "not copied")),
    )
    s0 = real_node(
        "S0-possibilities",
        kind=NodeKind.REGION,
        status=NodeStatus.HYPOTHETICAL,
        members=("route-alt", "route-narrowed", "route-single"),
    )
    s1 = real_node(
        "S1-trigger",
        kind=NodeKind.REGION,
        status=NodeStatus.OBSERVED,
        members=("route-alt", "route-single", "route-third"),
    )
    s3 = real_node(
        "S3-arrival",
        kind=NodeKind.IDEA_CONTEXT,
        status=NodeStatus.HYPOTHETICAL,
        members=("route-fourth", "route-single", "route-third"),
    )
    links = (
        real_link("link-s0-s1", "S0-possibilities", "S1-trigger"),
        real_link("link-s1-s3", "S1-trigger", "S3-arrival"),
    )
    return AtlasSnapshot(
        nodes=(state, s0, s1, s3),
        links=links,
        current_state_id="state-now",
        focus_node_id="S0-possibilities",
    )


def expect_real_refusal(callable_, fragment, label="real-model refusal"):
    """Call something that must be refused by the REAL model, and check its own words."""
    from real_atlas.model import ContractError

    try:
        callable_()
    except ContractError as refusal:
        assert fragment in str(refusal), f"{label}: expected {fragment!r}, got {str(refusal)!r}"
        return refusal
    raise AssertionError(f"expected {label} mentioning {fragment!r}, but nothing was raised")


REPORT_SNAPSHOT = circuit_snapshot()
REPORT_SNAPSHOT_DIGEST = REPORT_SNAPSHOT.snapshot_digest


@case
def real_atlas_is_the_model_from_the_commit_and_its_files_are_unchanged():
    # the six copied files still hash to what the provenance record says
    hashes = atlas_adapter.verify_real_model()
    assert len(hashes) == 6, hashes
    assert hashes["rpa_model.py"] == atlas_adapter.REAL_MODEL_SHA256["rpa_model.py"]
    assert atlas_adapter.REAL_MODEL_COMMIT == "eb9985566bd11a89f485d627186ef0efa7177f02"
    assert atlas_adapter.REAL_MODEL_BRANCH == "codex/helm-rpa-recorded-run-20260922"
    # the classes used by this build are the REAL model's own objects, not a copy of them
    for name in ("AtlasContext", "AtlasNode", "AtlasLink", "AtlasSnapshot", "LinkType",
                 "NodeKind", "NodeStatus", "validate_profile40", "certify_overlap",
                 "compatibility"):
        obj = getattr(atlas_adapter, name)
        module = getattr(obj, "__module__", None)
        assert module == "real_atlas.rpa_model", f"{name} comes from {module}, not the real model"
    # the bounds are read from the real file, not remembered here
    assert atlas_adapter.ATLAS_MAX_NODES == 512, atlas_adapter.ATLAS_MAX_NODES
    assert atlas_adapter.ATLAS_MAX_BYTES == 8 * 1024 * 1024, atlas_adapter.ATLAS_MAX_BYTES
    assert atlas_adapter.ATLAS_MAX_EXPANSION_DEPTH == 32
    # the real model's own forty-coordinate gate is reachable and refuses a short profile
    expect_real_refusal(
        lambda: atlas_adapter.validate_profile40(("1/2", "1/2"), None),
        "forty coordinates",
        "profile refusal",
    )


@case
def real_atlas_refuses_a_duplicate_node_id_and_a_changed_region():
    first = real_node("n1", members=("r1", "r2"))
    same = real_node("n1", members=("r1", "r2"))
    assert same.region_digest == first.region_digest, "an equal node must hash equally"
    assert re.fullmatch(r"[0-9a-f]{64}", first.region_digest), first.region_digest
    # the same node id with different members is a DIFFERENT region view, and a snapshot
    # that held both would carry two nodes under one id: the real model refuses that
    other = real_node("n1", members=("r1", "r3"))
    assert other.region_digest != first.region_digest, "members are inside the region digest"
    state = real_node("state-now", kind=NodeKind.STATE, status=NodeStatus.OBSERVED)
    expect_real_refusal(
        lambda: AtlasSnapshot(
            nodes=(state, first, other),
            links=(),
            current_state_id="state-now",
            focus_node_id="n1",
        ),
        "duplicate atlas node ID",
        "duplicate refusal",
    )
    # a fifth sort of node is not a sort of node: the real model's two fields are typed
    expect_real_refusal(
        lambda: real_node("n2", kind="possibility"),
        "typed",
        "node-kind refusal",
    )
    # a node with a fake status word is refused by the real type check too
    expect_real_refusal(
        lambda: AtlasNode(
            node_id="n3",
            idea_id="idea-main",
            label="n3",
            context=REAL_CONTEXT,
            status="GUESS",
        ),
        "typed",
        "node-status refusal",
    )


@case
def real_atlas_refuses_a_link_to_a_missing_node():
    first = real_node("n1")
    state = real_node("state-now", kind=NodeKind.STATE, status=NodeStatus.OBSERVED)
    dangling = real_link("link-dangling", "n1", "n-absent")
    expect_real_refusal(
        lambda: AtlasSnapshot(
            nodes=(state, first),
            links=(dangling,),
            current_state_id="state-now",
            focus_node_id="n1",
        ),
        "atlas link endpoint missing",
        "link refusal",
    )
    # a snapshot needs its present state, and that state must be a supplied observed record
    hidden = real_node("n1", kind=NodeKind.REGION, status=NodeStatus.HYPOTHETICAL)
    expect_real_refusal(
        lambda: AtlasSnapshot(
            nodes=(state, hidden),
            links=(),
            current_state_id="n1",
            focus_node_id="n1",
        ),
        "observed/verified state record",
        "current-state refusal",
    )
    # an empty atlas is not an atlas
    expect_real_refusal(
        lambda: AtlasSnapshot(
            nodes=(), links=(), current_state_id="state-now", focus_node_id="state-now"
        ),
        "atlas node bound/type invalid",
        "empty-snapshot refusal",
    )


@case
def real_atlas_refuses_a_contains_part_cycle():
    a = real_node("n-a")
    b = real_node("n-b")
    state = real_node("state-now", kind=NodeKind.STATE, status=NodeStatus.OBSERVED)
    cycle = (real_link("link-ab", "n-a", "n-b"), real_link("link-ba", "n-b", "n-a"))
    expect_real_refusal(
        lambda: AtlasSnapshot(
            nodes=(state, a, b),
            links=cycle,
            current_state_id="state-now",
            focus_node_id="n-a",
        ),
        "contains_part cycle is prohibited",
        "cycle refusal",
    )
    # a link from a node to itself closes the same circle and is refused the same way
    loop = (real_link("link-aa", "n-a", "n-a"),)
    expect_real_refusal(
        lambda: AtlasSnapshot(
            nodes=(state, a, b),
            links=loop,
            current_state_id="state-now",
            focus_node_id="n-a",
        ),
        "contains_part cycle is prohibited",
        "self-link refusal",
    )
    # the report snapshot holds no undeclared sort crossing's worth of trouble, and its
    # digest is the same on every run
    assert REPORT_SNAPSHOT.snapshot_digest == REPORT_SNAPSHOT_DIGEST
    assert REPORT_SNAPSHOT.focus_node_id == "S0-possibilities"
    assert REPORT_SNAPSHOT.current_state_id == "state-now"


@case
def crossing_between_two_sorts_undeclared_is_refused():
    snapshot = circuit_snapshot()
    link = [item for item in snapshot.links if item.link_id == "link-s0-s1"][0]
    # S0-possibilities is hypothetical+region and S1-trigger is observed+region: two sorts
    expect_refusal(
        lambda: crossings.cross(snapshot, "S0-possibilities", link, "S1-trigger"),
        "CROSS_SORT_UNDECLARED",
        "sort refusal",
    )
    declared = crossings.cross(
        snapshot, "S0-possibilities", link, "S1-trigger", thought_id="T-1", tick=1, declared=True
    )
    assert declared.declared is True
    assert declared.joins_different_sorts is True
    # the declaration is inside the crossing's digest, so the two records differ
    undeclared_record = atlas_adapter.CrossingRecord(
        from_node=declared.from_node, link=declared.link, to_node=declared.to_node,
        tick=1, thought_id="T-1", declared=False,
    )
    assert undeclared_record.digest != declared.digest, "the declaration is part of the digest"
    # a node whose kind and status both match is one sort, and needs no declaration
    same = real_node("n-same-sort", kind=NodeKind.REGION, status=NodeStatus.HYPOTHETICAL)
    assert atlas_adapter.sorts_differ(declared.from_node, same) is False
    assert atlas_adapter.sort_of(declared.from_node) == ("region", "hypothetical")


@case
def crossing_requires_the_link_to_connect_those_two_nodes():
    snapshot = circuit_snapshot()
    nodes = snapshot.node_map()
    node_a, node_b, node_s3 = nodes["S0-possibilities"], nodes["S1-trigger"], nodes["S3-arrival"]
    link_ab = [item for item in snapshot.links if item.link_id == "link-s0-s1"][0]
    link_b3 = [item for item in snapshot.links if item.link_id == "link-s1-s3"][0]
    good = crossings.cross(
        snapshot, "S0-possibilities", link_ab, "S1-trigger", thought_id="T-1", tick=1, declared=True
    )
    assert crossings.is_cjt(good) is True
    assert good.from_node_id == "S0-possibilities" and good.to_node_id == "S1-trigger"
    assert good.from_digest == node_a.region_digest and good.to_digest == node_b.region_digest
    assert good.tick == 1 and good.thought_id == "T-1"
    assert re.fullmatch(r"[0-9a-f]{64}", good.digest), good.digest
    # the link cannot be crossed backwards, and no other link can be substituted
    expect_refusal(
        lambda: crossings.cross(snapshot, "S1-trigger", link_ab, "S0-possibilities"),
        "LINK_FROM_MISMATCH",
        "crossing refusal",
    )
    expect_refusal(
        lambda: crossings.cross(snapshot, "S0-possibilities", link_b3, "S1-trigger"),
        "LINK_FROM_MISMATCH",
        "crossing refusal",
    )
    expect_refusal(
        lambda: crossings.cross(snapshot, "S0-possibilities", link_ab, "S3-arrival"),
        "LINK_TO_MISMATCH",
        "crossing refusal",
    )
    # a real AtlasLink naming two real nodes but not held by the snapshot is refused
    unheld = real_link("link-unheld", "S0-possibilities", "S3-arrival")
    expect_refusal(
        lambda: crossings.cross(snapshot, "S0-possibilities", unheld, "S3-arrival"),
        "LINK_NOT_IN_SNAPSHOT",
        "crossing refusal",
    )
    # a missing endpoint is refused, and is not repaired into a crossing
    expect_refusal(
        lambda: crossings.cross(snapshot, "n-absent", link_ab, "S1-trigger"),
        "MISSING_END_NODE",
        "crossing refusal",
    )
    # an object that is not the real snapshot is refused rather than duck-typed
    class StandIn:
        node_map = staticmethod(lambda: {})
        links = ()

    expect_refusal(
        lambda: crossings.cross(StandIn(), "S0-possibilities", link_ab, "S1-trigger"),
        "BAD_SNAPSHOT",
        "crossing refusal",
    )
    # the tick is part of the crossing: the same link at another tick is another crossing
    later = crossings.cross(
        snapshot, "S0-possibilities", link_ab, "S1-trigger", thought_id="T-1", tick=2, declared=True
    )
    assert later.digest != good.digest
    assert node_s3.region_digest != node_b.region_digest


@case
def crossing_record_carries_the_real_link_type_and_both_region_digests():
    snapshot = circuit_snapshot()
    nodes = snapshot.node_map()
    link = [item for item in snapshot.links if item.link_id == "link-s0-s1"][0]
    record = crossings.cross(
        snapshot, "S0-possibilities", link, "S1-trigger", thought_id="T-1", tick=4, declared=True
    )
    # the relation is the REAL LinkType, not a string this build invented
    assert type(record.relation) is LinkType, type(record.relation)
    assert record.relation is LinkType.CONTAINS_PART
    assert record.as_dict()["relation"] == "contains_part"
    # the two digests ARE the real region digests, recomputed from the real node's own fields
    for node in (nodes["S0-possibilities"], nodes["S1-trigger"]):
        recomputed = real_digest(
            {"node_id": node.node_id, "context": node.context.to_dict(), "members": node.members}
        )
        assert recomputed == node.region_digest, "the real model's region digest did not recompute"
    assert record.from_digest == nodes["S0-possibilities"].region_digest
    assert record.to_digest == nodes["S1-trigger"].region_digest
    # the crossing is not its link, and its digest is over the real pieces
    assert record.digest != link.link_id
    assert record.digest == real_digest(
        {
            "from_region_digest": record.from_digest,
            "link": link.to_dict(),
            "to_region_digest": record.to_digest,
            "tick": 4,
            "thought_id": "T-1",
            "declared": True,
        }
    )
    assert record.as_dict()["from_sort"] == ("region", "hypothetical")
    assert record.as_dict()["to_sort"] == ("region", "observed")


@case
def is_cjt_true_only_for_a_crossing():
    snapshot = circuit_snapshot()
    nodes = snapshot.node_map()
    node_a, node_b = nodes["S0-possibilities"], nodes["S1-trigger"]
    link_ab = [item for item in snapshot.links if item.link_id == "link-s0-s1"][0]
    real = crossings.cross(
        snapshot, "S0-possibilities", link_ab, "S1-trigger", thought_id="T-1", tick=1, declared=True
    )
    assert crossings.is_cjt(real) is True
    # everything that is not the crossing is not the crossing
    assert crossings.is_cjt(node_a) is False, "a real atlas node is not a CJT"
    assert crossings.is_cjt(node_b) is False
    assert crossings.is_cjt(link_ab) is False, "a real atlas link is not a CJT"
    assert crossings.is_cjt(real.as_dict()) is False, "a dict of the fields is not a CJT"
    assert (
        crossings.is_cjt({"from_node": node_a, "link": link_ab, "to_node": node_b}) is False
    ), "a dict carrying the three parts is still not a CJT"
    assert crossings.is_cjt(stations.make_crossing("T-1", "S1", 0, None)) is False, (
        "a station crossing is a different record and is not a CJT"
    )
    assert crossings.is_cjt(snapshot) is False
    assert crossings.is_cjt(None) is False
    # the path accepts only a Crossing, using the same test
    path = continuity.ContinuityPath("T-1", "Omega_a")
    expect_refusal(lambda: path.add_atlas_crossing(node_a), "NOT_A_CJT", "path refusal (node)")
    expect_refusal(lambda: path.add_atlas_crossing(link_ab), "NOT_A_CJT", "path refusal (link)")
    expect_refusal(
        lambda: path.add_atlas_crossing(real.as_dict()), "NOT_A_CJT", "path refusal (dict)"
    )
    assert path.atlas_crossings == ()
    assert path.add_atlas_crossing(real) is real


@case
def s0_binds_to_a_real_atlas_node_and_refuses_a_missing_node():
    snapshot = circuit_snapshot()
    node = snapshot.node_map()["S0-possibilities"]
    position = stations.bind_s0_to_atlas(snapshot, "S0-possibilities")
    assert position.station == "S0"
    assert position.entry_id == "S0-possibilities"
    assert position.entry_digest == node.region_digest
    assert position.entry_sort == atlas_adapter.ENTRY_NODE
    assert position.atlas_digest == snapshot.snapshot_digest
    assert position.node_kind == "region" and position.node_status == "hypothetical"
    binding = position.binding
    assert binding["entry_digest"] == node.region_digest
    assert binding["node_status"] == "hypothetical"
    station_crossing = stations.make_crossing("T-1", "S0", 0, None, atlas_entry=binding)
    assert station_crossing.is_atlas_position is True
    assert station_crossing.atlas_entry["entry_id"] == "S0-possibilities"
    assert station_crossing.as_dict()["atlas_entry"]["entry_digest"] == node.region_digest
    # the binding is frozen: it cannot be edited into a different anchor
    write_error = None
    try:
        station_crossing.atlas_entry["entry_digest"] = "0" * 64
    except TypeError as exc:
        write_error = exc
    assert write_error is not None, "the atlas_entry binding accepted a write; it is not frozen"
    # a missing node is refused, and nothing is invented
    expect_refusal(
        lambda: stations.bind_s0_to_atlas(snapshot, "n-absent"),
        "ATLAS_ENTRY_NOT_FOUND",
        "binding refusal",
    )
    expect_refusal(
        lambda: stations.bind_s0_to_atlas("not an atlas", "S0-possibilities"),
        "BAD_ATLAS",
        "binding refusal",
    )
    # a binding whose digest is not a digest is not a binding
    expect_refusal(
        lambda: stations.make_crossing(
            "T-1", "S0", 0, None, atlas_entry={"entry_id": "x", "entry_digest": "not-a-digest"}
        ),
        "BAD_ATLAS_ENTRY",
        "binding refusal",
    )
    # a binding that claims the sort of entry the real model does not have is refused
    expect_refusal(
        lambda: stations.make_crossing(
            "T-1",
            "S0",
            0,
            None,
            atlas_entry={
                "entry_id": "x",
                "entry_digest": "0" * 64,
                "entry_sort": "SUB_ATLAS",
            },
        ),
        "BAD_ATLAS_ENTRY",
        "binding refusal (sub-atlas sort)",
    )


@case
def s0_anchor_is_the_real_node_region_digest():
    snapshot = circuit_snapshot()
    node = snapshot.node_map()["S0-possibilities"]
    position = stations.bind_s0_to_atlas(snapshot, "S0-possibilities")
    # the anchor is the real AtlasNode.region_digest(), and that value recomputes from the
    # node's own fields with the real model's own hasher
    recomputed = real_digest(
        {"node_id": node.node_id, "context": node.context.to_dict(), "members": node.members}
    )
    assert position.entry_digest == node.region_digest == recomputed
    assert re.fullmatch(r"[0-9a-f]{64}", position.entry_digest)
    # the anchor is not the snapshot digest and not the node's view key
    assert position.entry_digest != snapshot.snapshot_digest
    assert position.entry_digest != node.view_key[2]
    # a different member set anchors differently: members are inside the real region digest
    other = real_node(
        "S0-possibilities",
        kind=NodeKind.REGION,
        status=NodeStatus.HYPOTHETICAL,
        members=("route-alt", "route-single"),
    )
    assert other.region_digest != node.region_digest
    # the continuity anchor returns that same real digest, and nothing else
    path = continuity.ContinuityPath("T-real-anchor", "Omega_a", seam_threshold=0.5)
    path.add_crossing("S0", 0, atlas_entry=position.binding)
    anchor = path.anchor()
    assert isinstance(anchor, str), f"the anchor must be a digest here, got {type(anchor).__name__}"
    assert anchor == node.region_digest, anchor
    assert path.anchor_is_atlas_digest() is True
    assert path.summary()["anchor_is_atlas_digest"] is True
    # a digest is not a point, and no distance from it is invented
    expect_refusal(
        lambda: path.displacement("S0"), "ANCHOR_IS_ATLAS_DIGEST", "displacement refusal"
    )
    # the FORM-gap refusal no longer fires for the head: the head IS a real atlas position
    headless = continuity.ContinuityPath("T-headless-atlas", "Omega_a")
    headless.add_crossing("S0", 0, atlas_entry=position.binding)
    assert headless.anchor() == node.region_digest


@case
def glue_back_is_decided_by_the_real_compatibility():
    snapshot = circuit_snapshot()
    nodes = snapshot.node_map()
    first = nodes["S0-possibilities"]
    second = nodes["S1-trigger"]
    # what the real model says, asked directly
    report = atlas_adapter.compatibility((first, second))
    certificate = atlas_adapter.certify_overlap((first, second), "route-single")
    # what the adapter says: the same values, copied
    glue = atlas_adapter.glue_back((first, second), "route-single")
    assert glue.compatible == report.compatible is True
    assert glue.same_context == report.same_context is True
    assert glue.shared_fields == report.shared_fields, (glue.shared_fields, report.shared_fields)
    assert glue.conflicting_fields == report.conflicting_fields == ()
    assert glue.certificate_id == certificate.certificate_id
    assert glue.witness_id == certificate.witness_id == "route-single"
    assert glue.region_digests == ((first.node_id, first.region_digest), (second.node_id, second.region_digest))
    assert atlas_adapter.glue_back_ok((first, second), "route-single") is True
    # the proof that no second glue rule lives in the adapter: substitute the real
    # functions and the adapter's answer follows them, not its own opinion
    original_compatibility = atlas_adapter.compatibility
    original_overlap = atlas_adapter.certify_overlap
    try:
        atlas_adapter.compatibility = lambda views: atlas_adapter.CompatibilityReport(
            tuple(sorted(node.node_id for node in views)), True, (), ("stubbed",)
        )
        assert atlas_adapter.glue_back_ok((first, second), "route-single") is False, (
            "the adapter ignored the real compatibility() and answered on its own"
        )
        atlas_adapter.compatibility = original_compatibility
        atlas_adapter.certify_overlap = lambda views, witness=None: type(
            "NoCertificate", (), {"witness_id": None, "certificate_id": None}
        )()
        assert atlas_adapter.glue_back_ok((first, second), "route-single") is False, (
            "the adapter ignored the real certify_overlap() and answered on its own"
        )
    finally:
        atlas_adapter.compatibility = original_compatibility
        atlas_adapter.certify_overlap = original_overlap
    assert atlas_adapter.glue_back_ok((first, second), "route-single") is True
    # and the path exposes the same real answer for the nodes it visited
    link = [item for item in snapshot.links if item.link_id == "link-s0-s1"][0]
    crossing = crossings.cross(
        snapshot, "S0-possibilities", link, "S1-trigger", thought_id="T-glue", tick=1, declared=True
    )
    path = continuity.ContinuityPath("T-glue", "Omega_a", atlas_crossings=[crossing])
    assert path.atlas_glue_back_ok("route-single") is True
    expect_refusal(
        lambda: continuity.ContinuityPath("T-empty", "Omega_a").atlas_glue_back(),
        "NO_ATLAS_CROSSINGS",
        "glue refusal (no crossings)",
    )


@case
def a_refused_glue_back_is_surfaced():
    # the real model refuses when two regions share no member: the refusal is surfaced with
    # the real model's own words, not turned into a quiet False or a repaired answer
    left = real_node("n-left", kind=NodeKind.REGION, members=("r1", "r2"))
    right = real_node("n-right", kind=NodeKind.REGION, members=("r3", "r4"))
    refusal = expect_refusal(
        lambda: atlas_adapter.glue_back((left, right)),
        "REAL_MODEL_REFUSAL",
        "glue refusal",
    )
    assert "common witness" in refusal.detail, refusal.detail
    # the real model also refuses fewer than two views: a refusal, not a "yes" and not a "no"
    expect_refusal(
        lambda: atlas_adapter.glue_back((left,)),
        "REAL_MODEL_REFUSAL",
        "glue refusal (one node)",
    )
    # an object that is not a real AtlasNode is refused by the real model's own type check
    expect_refusal(
        lambda: atlas_adapter.glue_back((left, {"node_id": "n-fake"})),
        "REAL_MODEL_REFUSAL",
        "glue refusal (fake node)",
    )
    # a real NEGATIVE answer is reported as a report, not a refusal: conflicting field values
    # keep the members overlap, so the overlap certificate still certifies, and the fields
    # are what the real compatibility() refuses to call compatible
    same_members = ("r1", "r2")
    agree = real_node("n-agree", kind=NodeKind.REGION, members=same_members,
                      fields=(("board_1", "copied into memory"),))
    disagree = real_node("n-disagree", kind=NodeKind.REGION, members=same_members,
                         fields=(("board_1", "not copied"),))
    glue = atlas_adapter.glue_back((agree, disagree))
    direct = atlas_adapter.compatibility((agree, disagree))
    assert glue.compatible is direct.compatible is False
    assert glue.conflicting_fields == direct.conflicting_fields == ("board_1",), glue.conflicting_fields
    assert glue.certificate_id is not None, "the members still overlap, so overlap certifies"
    assert glue.ok is False, "one real verdict failing means glue-back is not ok"
    assert atlas_adapter.glue_back_ok((agree, disagree)) is False


@case
def atlas_path_across_three_nodes_and_zero_sort_pollution():
    snapshot = circuit_snapshot()
    nodes = snapshot.node_map()
    link_12 = [item for item in snapshot.links if item.link_id == "link-s0-s1"][0]
    link_23 = [item for item in snapshot.links if item.link_id == "link-s1-s3"][0]
    crossing_1 = crossings.cross(
        snapshot, "S0-possibilities", link_12, "S1-trigger",
        thought_id="T-path", tick=1, declared=True,
    )
    crossing_2 = crossings.cross(
        snapshot, "S1-trigger", link_23, "S3-arrival",
        thought_id="T-path", tick=2, declared=True,
    )
    path = continuity.ContinuityPath(
        "T-path", "Omega_a", seam_threshold=0.5, atlas_crossings=[crossing_1, crossing_2]
    )
    expected = (
        nodes["S0-possibilities"].region_digest,
        nodes["S1-trigger"].region_digest,
        nodes["S3-arrival"].region_digest,
    )
    assert path.atlas_path() == expected, path.atlas_path()
    summary = continuity.continuity_summary(path)
    assert summary["atlas_nodes_visited"] == 3, summary["atlas_nodes_visited"]
    assert summary["atlas_edges_crossed"] == 2, summary["atlas_edges_crossed"]
    assert summary["atlas_sort_pollution"] == 0, summary["atlas_sort_pollution"]
    assert summary["atlas_cross_sort_declared"] == 2, summary["atlas_cross_sort_declared"]
    assert path.atlas_sort_pollution() == 0
    assert len(path.atlas_path()) == len(set(path.atlas_path())), "three distinct nodes"
    # a crossing that does not start where the last one ended is refused
    broken = continuity.ContinuityPath("T-path", "Omega_a")
    broken.add_atlas_crossing(crossing_1)
    expect_refusal(
        lambda: broken.add_atlas_crossing(crossing_1), "ATLAS_PATH_BROKEN", "path refusal"
    )
    assert len(broken.atlas_crossings) == 1
    # a crossing of another thought is refused
    other = crossings.cross(
        snapshot, "S0-possibilities", link_12, "S1-trigger",
        thought_id="T-other", tick=3, declared=True,
    )
    expect_refusal(
        lambda: continuity.ContinuityPath("T-path", "Omega_a").add_atlas_crossing(other),
        "ATLAS_CROSSING_OTHER_THOUGHT",
        "path refusal",
    )
    # a link the real snapshot does not hold cannot be crossed, even between real nodes
    references = real_link(
        "link-same-idea", "S0-possibilities", "S3-arrival", LinkType.REFERENCES_SAME_IDEA
    )
    expect_refusal(
        lambda: crossings.cross(snapshot, "S0-possibilities", references, "S3-arrival"),
        "LINK_NOT_IN_SNAPSHOT",
        "path refusal",
    )


@case
def the_stand_in_atlas_is_gone_and_s0_refuses_it():
    import importlib.util

    # 1. the stand-in file is not in this build
    assert not os.path.exists(os.path.join(BUILD_DIR, "atlas.py")), (
        "atlas.py is still present; the stand-in was supposed to be deleted"
    )
    # 2. no module in the build imports a module named atlas
    pattern = re.compile(r"^\s*(?:import\s+atlas\b|from\s+atlas\s+import)", re.MULTILINE)
    for name in MODULE_FILES:
        with open(os.path.join(BUILD_DIR, name), encoding="utf-8") as handle:
            found = pattern.search(handle.read())
        assert found is None, f"{name} still imports the stand-in atlas: {found.group(0)}"
    # 3. a module named atlas is not importable from this build's folder
    assert importlib.util.find_spec("atlas") is None, "a module named atlas is importable"
    # 4. an object that imitates the old stand-in is not the real atlas, and S0 refuses it
    class StandIn:
        atlas_id = "atlas-test"
        depth = 0
        max_depth = 3

        def entry_digest(self, entry_id):
            return "0" * 64

        def entry_ids(self):
            return ("S0-possibilities",)

        def entry_sort(self, entry_id):
            return "NODE"

        def frozen_digest(self):
            return "0" * 64

        def summary(self):
            return {}

    expect_refusal(
        lambda: stations.bind_s0_to_atlas(StandIn(), "S0-possibilities"),
        "BAD_ATLAS",
        "stand-in refusal",
    )
    expect_refusal(
        lambda: atlas_adapter.bind_s0(StandIn(), "S0-possibilities"),
        "BAD_SNAPSHOT",
        "stand-in refusal",
    )


# --------------------------------------------------------------------------- #
# 8. The README: the claim ceiling, and every undecided line
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
    for name in MODULE_FILES:
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
MODULE_FILES = (
    "stations.py",
    "seams.py",
    "continuity.py",
    "provenance.py",
    "disengage.py",
    "atlas_adapter.py",
    "crossings.py",
)


def undecided_questions():
    """Every UNDECIDED IN DESIGN question marked in the build's seven modules."""
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
    print("continuity_build_v3 / test_all.py")
    print(f"python: {platform.python_version()}  platform: {platform.system()}")
    print(f"build folder: {BUILD_DIR}")
    print(f"frozen station-kind table sha256: {stations.STATION_KINDS_SHA256}")
    print(
        f"real atlas model: {atlas_adapter.REAL_MODEL_BRANCH} @ "
        f"{atlas_adapter.REAL_MODEL_COMMIT}"
    )
    print(f"real atlas rpa_model.py sha256: {atlas_adapter.REAL_MODEL_SHA256['rpa_model.py']}")
    print(f"real atlas snapshot sha256: {REPORT_SNAPSHOT_DIGEST}")
    print(
        "real atlas snapshot: "
        f"{len(REPORT_SNAPSHOT.nodes)} nodes, {len(REPORT_SNAPSHOT.links)} links, "
        f"present state {REPORT_SNAPSHOT.current_state_id}, "
        f"focus {REPORT_SNAPSHOT.focus_node_id}"
    )
    print("stand-in atlas.py present: " f"{os.path.exists(os.path.join(BUILD_DIR, 'atlas.py'))}")
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
