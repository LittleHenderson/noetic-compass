#!/usr/bin/env python3
"""Ground-truth tests for the RPM/diode asymmetric cross-ablation knockout.

Each case builds synthetic hidden states with a KNOWN geometric relationship
between a W ("prerequisite", anode) labeling and a P ("dependent", cathode)
labeling, then asserts the executor returns the correct verdict:

  containment  (P's direction lies inside span(W))  -> GREY_SUBSUMPTION_CONFOUND
  reversed     (W's direction lies inside span(P))  -> FALSIFY_REVERSED
  symmetric    (W and P share one direction)        -> FALSIFY_SYMMETRIC
  independent  (W _|_ P orthogonal directions)      -> FALSIFY_NO_DEPENDENCE

Plus the two hard gates: surface-leakage refusal and low-readout refusal, and
the standing invariant that no verdict is ever ACCEPT.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_rpm_diode_asymmetric_ablation import run_asymmetric_ablation  # noqa: E402

H = 48
M = 4.0       # signal amplitude
NOISE = 0.6


def _orthonormal(seed: int) -> np.ndarray:
    q, _ = np.linalg.qr(np.random.default_rng(seed).normal(size=(H, H)))
    return q  # columns are orthonormal directions


def _shuffle(X, yA, yB, rng):
    perm = rng.permutation(len(X))
    X, yA, yB = np.asarray(X)[perm], np.asarray(yA)[perm], np.asarray(yB)[perm]
    groups = (np.arange(len(X)) // 3).astype(str)
    return X[:, None, :], yA, yB, groups


# A regular tetrahedron on dims {0,1,2}: 4 mutually-equidistant class centers,
# separable by ANY 2 of the 3 dims (project to a plane -> 4 distinct points).
_TETRA = {"t0": (+M, +M, +M), "t1": (+M, -M, -M), "t2": (-M, +M, -M), "t3": (-M, -M, +M)}
# Coarsening of the tetra into 2 classes -> readable ONLY from span{0,1,2}.
_COARSE = {"t0": "c0", "t1": "c0", "t2": "c1", "t3": "c1"}


def _gen_tetra(seed: int, *, n_per_class: int = 90):
    """4-class tetra label `four` on dims {0,1,2}; `coarse` = a 2-class coarsening
    of it (so span(coarse) ⊂ span(four), with no coordinate collision)."""
    Q = _orthonormal(seed)
    rng = np.random.default_rng(seed + 1)
    X, four, coarse = [], [], []
    for label, (a, b, c) in _TETRA.items():
        center = a * Q[:, 0] + b * Q[:, 1] + c * Q[:, 2]
        for _ in range(n_per_class):
            X.append(center + NOISE * rng.normal(size=H))
            four.append(label); coarse.append(_COARSE[label])
    return _shuffle(X, four, coarse, rng)


def _gen_binary(seed: int, *, dim_W: int, dim_P: int, same_label: bool, n_per_combo: int = 80):
    """Two binary labels. same_label=True -> P==W on one dim (symmetric collapse).
    Else independent labels on dim_W / dim_P (disjoint -> no dependence)."""
    Q = _orthonormal(seed)
    rng = np.random.default_rng(seed + 1)
    X, yW, yP = [], [], []
    combos = [("w0", "w0")] if same_label else [("w0", "p0"), ("w0", "p1"), ("w1", "p0"), ("w1", "p1")]
    if same_label:
        combos = [("w0",), ("w1",)]
    for combo in combos:
        w = combo[0]
        for _ in range(n_per_combo):
            vec = NOISE * rng.normal(size=H)
            vec = vec + (M if w == "w0" else -M) * Q[:, dim_W]
            if same_label:
                p = w
            else:
                p = combo[1]
                vec = vec + (M if p == "p0" else -M) * Q[:, dim_P]
            X.append(vec); yW.append(w); yP.append(p)
    return _shuffle(X, yW, yP, rng)


def _run(features, yW, yP, groups, **kw):
    return run_asymmetric_ablation(
        features=features, layer_index=0, labels_W=yW, labels_P=yP, groups=groups,
        surface_screen_status="READY_FOR_W0_CAPTURE", seed=2026, **kw,
    )


# Each directional case + its expected verdict (single source of truth, so the
# tests and the __main__ pretty-printer never diverge).
def _build_directional(name: str) -> dict:
    if name == "containment":  # W = 4-class tetra; P = coarsening (P ⊂ span(W))
        f, four, coarse, g = _gen_tetra(seed=11)
        return _run(f, four, coarse, g)
    if name == "reversed":     # swap roles: P is the superset, W the coarsening
        f, four, coarse, g = _gen_tetra(seed=12)
        return _run(f, coarse, four, g)
    if name == "symmetric":    # W and P share one direction
        f, w, p, g = _gen_binary(seed=13, dim_W=0, dim_P=0, same_label=True)
        return _run(f, w, p, g)
    if name == "independent":  # orthogonal directions, independent labels
        f, w, p, g = _gen_binary(seed=14, dim_W=0, dim_P=3, same_label=False)
        return _run(f, w, p, g)
    raise ValueError(name)


_EXPECTED = {
    "containment": "GREY_SUBSUMPTION_CONFOUND",
    "reversed": "FALSIFY_REVERSED",
    "symmetric": "FALSIFY_SYMMETRIC",
    "independent": "FALSIFY_NO_DEPENDENCE",
}


def test_containment_is_grey_not_a_false_pass():
    r = _build_directional("containment")
    assert r["verdict"] == "GREY_SUBSUMPTION_CONFOUND", r["verdict"]
    assert r["leg_W_to_P_collapse"]["collapse"] is True      # P knocked out
    assert r["leg_P_to_W_survival"]["collapse"] is False     # W survives
    assert r["subsumption_control"]["containment_P_in_span_W"] >= 0.5


def test_reversed_order_is_falsified():
    assert _build_directional("reversed")["verdict"] == "FALSIFY_REVERSED"


def test_symmetric_is_falsified():
    r = _build_directional("symmetric")
    assert r["verdict"] == "FALSIFY_SYMMETRIC", r["verdict"]
    assert r["leg_W_to_P_collapse"]["collapse"] and r["leg_P_to_W_survival"]["collapse"]


def test_independent_directions_show_no_dependence():
    r = _build_directional("independent")
    assert r["verdict"] == "FALSIFY_NO_DEPENDENCE", r["verdict"]
    assert r["leg_W_to_P_collapse"]["collapse"] is False


def test_surface_screen_gate_refuses():
    f, w, p, g = _gen_binary(seed=15, dim_W=0, dim_P=3, same_label=False)
    r = run_asymmetric_ablation(features=f, layer_index=0, labels_W=w, labels_P=p,
                                groups=g, surface_screen_status="UNVERIFIED", seed=2026)
    assert r["verdict"] == "BLOCKED_SURFACE_LEAKAGE", r["verdict"]


def test_low_readout_gate_refuses():
    rng = np.random.default_rng(99)
    f = rng.normal(size=(240, 1, H))  # pure noise, no signal
    w = np.array(["w0", "w1"] * 120)
    p = np.array(["p0", "p1"] * 120)
    g = (np.arange(240) // 3).astype(str)
    r = _run(f, w, p, g)
    assert r["verdict"] == "BLOCKED_LOW_READOUT", r["verdict"]


def test_never_emits_accept():
    f, four, coarse, g = _gen_tetra(seed=11)
    r = _run(f, four, coarse, g)
    assert r["claim_ceiling"] == "FLAG_FOR_HUMAN_REVIEW"
    assert "ACCEPT" not in r["verdict"]


if __name__ == "__main__":
    print(f"{'case':28s} {'verdict':32s} {'expected':32s} W_cln P_cln  WP_dis PW_dis  contain")
    failures = 0
    for name in ("containment", "reversed", "symmetric", "independent"):
        r = _build_directional(name)
        ro = r["readout"]; wp = r["leg_W_to_P_collapse"]; pw = r["leg_P_to_W_survival"]
        ok = r["verdict"] == _EXPECTED[name]
        failures += 0 if ok else 1
        print(f"{name:28s} {r['verdict']:32s} {_EXPECTED[name]:32s} "
              f"{ro['W_clean_balanced_accuracy']:.2f}  {ro['P_clean_balanced_accuracy']:.2f}  "
              f"{wp['true_disruption']:+.3f} {pw['true_disruption']:+.3f}  "
              f"{r['subsumption_control']['containment_P_in_span_W']:.3f}  {'OK' if ok else 'FAIL'}")
    for name, fn in [("surface gate", test_surface_screen_gate_refuses),
                     ("low-readout gate", test_low_readout_gate_refuses),
                     ("never ACCEPT", test_never_emits_accept)]:
        try:
            fn(); print(f"{name:28s} OK")
        except AssertionError as e:
            failures += 1; print(f"{name:28s} FAILED: {e}")
    print(f"\n{'ALL PASS' if failures == 0 else str(failures) + ' FAILURE(S)'}")
    sys.exit(1 if failures else 0)
