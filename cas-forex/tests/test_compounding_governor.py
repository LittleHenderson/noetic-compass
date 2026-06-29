"""Tests for the compounding governor (CAS Forex AMPLIFY layer).

Proves the honest invariants:
  * ADD only when EVERY condition holds, including a FRESH edge-gate PASS;
  * ADD is BLOCKED when fresh_edge_pass is False even if everything else is green
    (re-test enforcement — the core honesty guarantee);
  * CUT on a structural breakdown (CJT region, cascade flag, or deep-negative R);
  * HOLD otherwise;
  * add_units respects max_units headroom and scales with cell_reliability.

The module is tested standalone — no other in-flight module is imported. The two
provenance helpers are exercised with lightweight stand-ins matching only the
attributes the helpers read.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from cas_forex.compounding_governor import (
    CompoundDecision,
    cascade_scalars,
    decide,
    reliability_from_lacunarity,
)


# A green baseline: every ADD precondition satisfied. Individual tests flip one
# field at a time to isolate each rule.
GREEN = dict(
    position={"symbol": "EUR/USD", "direction": "LONG", "units": 1},
    cell_reliability=0.9,
    cascade_confidence=0.8,
    cjt_region="active",
    floating_r=1.5,
    max_units=4,
    current_units=1,
)


def test_add_when_all_conditions_hold_including_fresh_pass():
    d = decide(**GREEN, fresh_edge_pass=True)
    assert isinstance(d, CompoundDecision)
    assert d.action == "ADD"
    assert d.add_units >= 1
    assert d.add_units <= GREEN["max_units"] - GREEN["current_units"]


def test_add_blocked_when_fresh_edge_pass_false_even_if_all_else_green():
    # Identical green inputs, only fresh_edge_pass flipped off -> NO ADD.
    d = decide(**GREEN, fresh_edge_pass=False)
    assert d.action == "HOLD"
    assert d.add_units == 0
    assert "fresh" in d.reason.lower() or "re-test" in d.reason.lower()


def test_add_never_inherits_parent_token():
    # The parent position carrying its own pass token must NOT authorize an add;
    # only the explicit fresh_edge_pass argument can.
    pos = {"symbol": "EUR/USD", "edge_token": "PARENT-TOKEN-123", "units": 1}
    args = {**GREEN, "position": pos}
    assert decide(**args, fresh_edge_pass=False).action == "HOLD"
    assert decide(**args, fresh_edge_pass=True).action == "ADD"


def test_cut_on_cjt_breakdown_region():
    d = decide(**{**GREEN, "cjt_region": "breakdown"}, fresh_edge_pass=True)
    assert d.action == "CUT"
    assert d.add_units == 0


def test_cut_on_cascade_breakdown_flag():
    d = decide(**GREEN, fresh_edge_pass=True, cascade_flags_breakdown=True)
    assert d.action == "CUT"
    assert d.add_units == 0


def test_cut_on_deeply_negative_floating_r():
    d = decide(**{**GREEN, "floating_r": -1.5}, fresh_edge_pass=True)
    assert d.action == "CUT"
    assert d.add_units == 0


def test_breakdown_cut_dominates_even_with_fresh_pass_and_green_scalars():
    # CUT signals must win over a would-be ADD.
    d = decide(
        **{**GREEN, "cjt_region": "breakdown"},
        fresh_edge_pass=True,
    )
    assert d.action == "CUT"


def test_hold_when_floating_r_not_positive():
    d = decide(**{**GREEN, "floating_r": 0.0}, fresh_edge_pass=True)
    assert d.action == "HOLD"
    assert d.add_units == 0


def test_hold_when_reliability_low():
    d = decide(**{**GREEN, "cell_reliability": 0.1}, fresh_edge_pass=True)
    assert d.action == "HOLD"


def test_hold_when_cascade_confidence_low():
    d = decide(**{**GREEN, "cascade_confidence": 0.1}, fresh_edge_pass=True)
    assert d.action == "HOLD"


def test_hold_when_region_not_active():
    # 'cutoff' / 'saturation' / 'unknown' are not ADD regions but also not CUT.
    for region in ("cutoff", "saturation", "unknown"):
        d = decide(**{**GREEN, "cjt_region": region}, fresh_edge_pass=True)
        assert d.action == "HOLD", region


def test_hold_when_no_headroom():
    d = decide(
        **{**GREEN, "current_units": 4, "max_units": 4},
        fresh_edge_pass=True,
    )
    assert d.action == "HOLD"
    assert d.add_units == 0


def test_add_units_respect_max_units_headroom():
    # current=2, max=4 -> headroom 2; high reliability cannot exceed headroom.
    d = decide(
        **{**GREEN, "cell_reliability": 1.0, "current_units": 2, "max_units": 4},
        fresh_edge_pass=True,
    )
    assert d.action == "ADD"
    assert d.add_units == 2  # capped at headroom


def test_add_units_scale_with_reliability():
    # With wide headroom, a lower (but still 'high') reliability adds fewer units
    # than a maximal reliability.
    base = {**GREEN, "current_units": 0, "max_units": 10}
    low = decide(**{**base, "cell_reliability": 0.6}, fresh_edge_pass=True)
    high = decide(**{**base, "cell_reliability": 1.0}, fresh_edge_pass=True)
    assert low.action == "ADD" and high.action == "ADD"
    assert low.add_units < high.add_units
    # ceil(0.6 * 10) == 6 ; ceil(1.0 * 10) == 10
    assert low.add_units == math.ceil(0.6 * 10)
    assert high.add_units == math.ceil(1.0 * 10)


def test_add_units_at_least_one_on_minimal_headroom():
    d = decide(
        **{**GREEN, "cell_reliability": 0.6, "current_units": 3, "max_units": 4},
        fresh_edge_pass=True,
    )
    assert d.action == "ADD"
    assert d.add_units == 1


# --- provenance helper tests ------------------------------------------------


def test_reliability_from_lacunarity_cellresult():
    non_gap = SimpleNamespace(is_gap=False)
    gap = SimpleNamespace(is_gap=True)
    assert reliability_from_lacunarity(non_gap) == 1.0
    assert reliability_from_lacunarity(gap) == 0.0


def test_reliability_from_lacunarity_gap_fraction():
    # All-gaps map (price-only honest default) -> zero reliability.
    assert reliability_from_lacunarity(1.0) == 0.0
    assert reliability_from_lacunarity(0.0) == 1.0
    assert reliability_from_lacunarity(0.25) == pytest.approx(0.75)


def test_cascade_scalars_reads_final_step_and_breakdown():
    fc = SimpleNamespace(confidence_curve=[0.9, 0.7, 0.4], breakdown_step=2)
    conf, flag = cascade_scalars(fc)  # final step
    assert conf == pytest.approx(0.4)
    assert flag is True  # breakdown_step 2 <= final step 3


def test_cascade_scalars_no_breakdown_before_read_step():
    fc = SimpleNamespace(confidence_curve=[0.9, 0.7, 0.4], breakdown_step=3)
    conf, flag = cascade_scalars(fc, step=2)
    assert conf == pytest.approx(0.7)
    assert flag is False  # breakdown_step 3 > read step 2


def test_cascade_scalars_empty_curve():
    fc = SimpleNamespace(confidence_curve=[], breakdown_step=None)
    conf, flag = cascade_scalars(fc)
    assert conf == 0.0
    assert flag is False
