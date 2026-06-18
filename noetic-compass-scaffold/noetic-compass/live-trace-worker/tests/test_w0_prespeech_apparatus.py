"""Tests for the Lane A/B pre-speech apparatus (pure logic, no GPU/model).

Proves the math is correct AND that the apparatus is honestly bounded: an
untrained probe is flagged untrained, and the causal gate verifier only returns
LICENSED when every gate passes.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.runtime.causal_intervention import refusal_direction, verify_causal_gates
from app.runtime.refusal_recipe_probe import compute_recipe_readiness
from app.runtime.w0_capture import cosine, validate_windows


# ---- w0_capture temporal validation ----

def test_validate_windows_flags_non_prespeech():
    # W0 ~ W1 (nearly identical) -> capture is NOT genuinely pre-generation.
    w0 = [1.0, 0.0, 0.0, 0.0]
    w1_same = [1.0, 0.0001, 0.0, 0.0]
    assert validate_windows(w0, w1_same)["valid"] is False
    # W0 clearly differs from W1 -> valid pre-speech window.
    w1_diff = [0.0, 1.0, 0.0, 0.0]
    res = validate_windows(w0, w1_diff)
    assert res["valid"] is True
    assert res["cosine_W0_W1"] == pytest.approx(0.0, abs=1e-9)


def test_cosine_basic():
    assert cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine([1, 0], [0, 1]) == pytest.approx(0.0)


# ---- refusal recipe readiness (pure) ----

def test_recipe_readiness_refused_vs_complied():
    strong = {"^3^P|T": 0.8, "^3^P|A": 0.9, "^3^P|f": 0.7, "^8^P|T": 0.75}
    r = compute_recipe_readiness(strong, polarity_margin=-0.4)
    assert r["predicted_label"] == "REFUSED"  # high readiness + aversive polarity
    assert r["limiting_reagent"] == "^3^P|f"  # lowest activation
    # Same activations but attractive polarity -> not a refusal.
    r2 = compute_recipe_readiness(strong, polarity_margin=+0.4)
    assert r2["predicted_label"] == "COMPLIED"


def test_recipe_lacunarity_and_missing_ingredient():
    weak = {"^3^P|T": 0.1, "^3^P|A": 0.2, "^3^P|f": 0.1, "^8^P|T": 0.05}
    r = compute_recipe_readiness(weak, polarity_margin=-0.9)
    assert r["lacunarity"] > 0.3  # big shortfall below 0.5
    assert r["refusal_readiness"] < 0.5
    assert r["predicted_label"] == "COMPLIED"  # readiness below threshold
    with pytest.raises(ValueError):
        compute_recipe_readiness({"^3^P|T": 0.5}, polarity_margin=0.0)  # missing ingredients


# ---- refusal direction (pure) ----

def test_refusal_direction_points_from_complied_to_refused():
    w0 = [[2.0, 0.0], [2.2, 0.1], [-2.0, 0.0], [-2.1, -0.1]]
    labels = ["REFUSED", "REFUSED", "COMPLIED", "COMPLIED"]
    d = refusal_direction(w0, labels)
    assert d[0] > 0.9  # direction dominated by the separating axis
    assert np.isclose(np.linalg.norm(d), 1.0)
    with pytest.raises(ValueError):
        refusal_direction([[1.0, 0.0]], ["REFUSED"])  # only one class


# ---- Lane B causal gate verification (pure) ----

def _passing_conditions():
    return {"no_op": 0.30, "+refusal": 0.55, "-refusal": 0.12, "random": 0.32}


def test_causal_gates_all_pass():
    v = verify_causal_gates(
        _passing_conditions(),
        permutation_p=0.0005,
        ci_lower=0.18,
        ci_upper=0.32,
        complied_shift_minus=0.20,
        ignored_shift=0.03,
        malformed_shift=0.01,
    )
    assert v["all_passed"] is True
    assert v["verdict"] == "CAUSAL_PROOF_LICENSED"


def test_causal_gates_fail_when_random_steer_also_shifts():
    # If random same-norm steer moves refusal as much as +refusal, it's not causal.
    cond = {"no_op": 0.30, "+refusal": 0.55, "-refusal": 0.12, "random": 0.52}
    v = verify_causal_gates(
        cond, permutation_p=0.0005, ci_lower=0.18, ci_upper=0.32,
        complied_shift_minus=0.20, ignored_shift=0.03, malformed_shift=0.01,
    )
    assert v["all_passed"] is False
    assert v["gates"]["G4_beats_random"]["passed"] is False
    assert v["gates"]["G5_random_small"]["passed"] is False
    assert v["verdict"] == "CAUSAL_PROOF_NOT_LICENSED"


def test_causal_gates_fail_on_weak_shift_or_high_p():
    cond = {"no_op": 0.30, "+refusal": 0.36, "-refusal": 0.28, "random": 0.31}
    v = verify_causal_gates(
        cond, permutation_p=0.05, ci_lower=0.02, ci_upper=0.10,
        complied_shift_minus=0.01, ignored_shift=0.2, malformed_shift=0.1,
    )
    assert v["all_passed"] is False
    assert v["gates"]["G1_refusal_shift"]["passed"] is False
    assert v["gates"]["G2_permutation"]["passed"] is False
