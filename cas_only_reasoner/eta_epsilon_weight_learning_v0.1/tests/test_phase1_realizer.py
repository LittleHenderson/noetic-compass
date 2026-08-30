"""Phase 1 permanent tests. The only claim these license: the software
implements a local regularized right-inverse on synthetic matrices under
declared rank conditions. No model, no Transformer claim."""
import numpy as np

import realizer_core as rc


def test_formal_and_empirical_map_names_are_separate():
    assert rc.map_namespaces_are_disjoint()
    assert "eta" in rc.FORMAL_MAP_NAMES and "eta_hat" in rc.EMPIRICAL_MAP_NAMES
    assert "eta" not in rc.EMPIRICAL_MAP_NAMES


def test_map_domains_and_codomains_compose():
    # eta_hat: target(R^k) -> param(R^m); epsilon_hat: param(R^m) -> target(R^k)
    assert rc.composes("target_Rk", "param_Rm", "param_Rm", "target_Rk")
    # a mismatched pair must NOT compose
    assert not rc.composes("target_Rk", "param_Rm", "target_Rk", "param_Rm")


def test_exact_right_inverse_when_full_row_rank():
    rng = np.random.default_rng(0)
    J = rng.standard_normal((3, 7))            # full row rank, k<m
    eta, label, meta = rc.right_inverse(J, lam=0.0)
    assert label == "EXACT_RIGHT_INVERSE"
    assert meta["full_row_rank"] is True
    assert np.allclose(J @ eta, np.eye(3), atol=1e-9)


def test_rank_deficiency_is_reported():
    J = np.array([[1.0, 2.0, 3.0], [2.0, 4.0, 6.0]])   # row 2 = 2*row 1
    rank, _s = rc.numerical_rank(J)
    assert rank == 1
    out = rc.predict_intervention(J, np.array([1.0, 0.0]), lam=1e-6)
    # target [1,0] is largely outside the 1-D reachable subspace
    assert out["reachable_fraction"] < 0.99
    assert out["status"] == "TARGET_PARTIALLY_UNREACHABLE"


def test_damped_inverse_not_labeled_exact():
    rng = np.random.default_rng(1)
    J = rng.standard_normal((3, 7))
    _eta, label, _m = rc.right_inverse(J, lam=0.1)
    assert label == "LOCAL_DAMPED_REALIZER"
    # J @ eta_damped is NOT an exact idempotent projector
    eta, _l, _mm = rc.right_inverse(J, lam=0.1)
    assert not rc.is_idempotent(J @ eta)


def test_projection_is_idempotent_only_when_conditions_hold():
    rng = np.random.default_rng(2)
    J = rng.standard_normal((3, 7))
    Jp = rc.moore_penrose(J)
    # exact Moore-Penrose projectors ARE idempotent
    assert rc.is_idempotent(J @ Jp)     # target-space reachable projector
    assert rc.is_idempotent(Jp @ J)     # source-space visible projector
    # full row rank -> J J+ == I_k
    assert np.allclose(J @ Jp, np.eye(3), atol=1e-9)
    # damped operator is not idempotent
    eta, _l, _m = rc.right_inverse(J, lam=0.25)
    assert not rc.is_idempotent(J @ eta)


def test_zero_target_produces_zero_intervention():
    rng = np.random.default_rng(3)
    J = rng.standard_normal((3, 7))
    out = rc.predict_intervention(J, np.zeros(3), lam=0.0)
    assert np.allclose(out["delta_c"], 0.0, atol=1e-12)


def test_sign_reversal_reverses_intervention():
    rng = np.random.default_rng(4)
    J = rng.standard_normal((3, 7))
    d = rng.standard_normal(3)
    a = rc.predict_intervention(J, d, lam=0.05)["delta_c"]
    b = rc.predict_intervention(J, -d, lam=0.05)["delta_c"]
    assert np.allclose(a, -b, atol=1e-9)


def test_deterministic_svd_and_solver():
    rng = np.random.default_rng(5)
    J = rng.standard_normal((4, 9))
    d = rng.standard_normal(4)
    o1 = rc.predict_intervention(J, d, lam=0.1)
    o2 = rc.predict_intervention(J, d, lam=0.1)
    assert np.array_equal(o1["delta_c"], o2["delta_c"])
    assert o1["meta"]["singular_values"] == o2["meta"]["singular_values"]
    assert o1["reachable_fraction"] == o2["reachable_fraction"]
