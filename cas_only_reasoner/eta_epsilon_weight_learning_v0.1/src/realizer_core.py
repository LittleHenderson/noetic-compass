"""Phase 1: synthetic local right-inverse maths. CPU only. No model.

Implements the regularized right inverse and its HONEST labels, exactly
per TYPE_CONTRACT.md. Deterministic: numpy SVD / solve only, no RNG in
the core paths.

Facts enforced here:
  - eta_lambda = J^T (J J^T + lambda I)^-1  (regularized right inverse).
  - lambda == 0 AND full row rank  ->  J @ eta = I_k exactly. Label
    EXACT_RIGHT_INVERSE.
  - lambda > 0  OR  rank deficient  ->  label LOCAL_DAMPED_REALIZER; the
    composite is NOT an exact idempotent projector.
  - J J+ is the projector onto the reachable subspace in TARGET space
    (= I_k only at full row rank). J+ J is the projector onto the visible
    subspace in SOURCE space. Both are exact idempotents for the
    Moore-Penrose inverse J+.
  - reachable_fraction = ||J J+ d|| / ||d||.
"""
from __future__ import annotations

import numpy as np

# Formal maps (exact section-retraction) vs empirical maps (hatted,
# approximate). The two namespaces are kept strictly separate.
FORMAL_MAP_NAMES = ("eta", "epsilon")
EMPIRICAL_MAP_NAMES = ("eta_hat", "epsilon_hat")


def map_namespaces_are_disjoint() -> bool:
    return set(FORMAL_MAP_NAMES).isdisjoint(EMPIRICAL_MAP_NAMES)


def composes(dom1, cod1, dom2, cod2) -> bool:
    """True iff (map1: dom1->cod1) then (map2: dom2->cod2) type-checks,
    i.e. the codomain of the first equals the domain of the second."""
    return cod1 == dom2


def numerical_rank(J, rtol: float = 1e-10):
    J = np.asarray(J, dtype=float)
    s = np.linalg.svd(J, compute_uv=False)
    if s.size == 0:
        return 0, s
    tol = rtol * s[0] * max(J.shape)
    return int(np.count_nonzero(s > tol)), s


def moore_penrose(J, rcond: float = 1e-12):
    return np.linalg.pinv(np.asarray(J, dtype=float), rcond=rcond)


def right_inverse(J, lam: float = 0.0, rtol: float = 1e-10):
    """eta = J^T (J J^T + lam I)^-1. Returns (eta, label, meta)."""
    J = np.asarray(J, dtype=float)
    k, _m = J.shape
    rank, s = numerical_rank(J, rtol)
    full_row_rank = rank == k
    A = J @ J.T + lam * np.eye(k)
    eta = J.T @ np.linalg.solve(A, np.eye(k))
    if lam == 0.0 and full_row_rank:
        label = "EXACT_RIGHT_INVERSE"
    else:
        label = "LOCAL_DAMPED_REALIZER"
    cond = float(s[0] / s[-1]) if s.size and s[-1] > 0 else float("inf")
    meta = {"rank": rank, "full_row_rank": bool(full_row_rank),
            "singular_values": s.tolist(), "condition_number": cond,
            "lambda": float(lam), "shape": list(J.shape)}
    return eta, label, meta


def reachable_fraction(J, delta_xi, rcond: float = 1e-12) -> float:
    J = np.asarray(J, dtype=float)
    d = np.asarray(delta_xi, dtype=float)
    Jp = moore_penrose(J, rcond)
    proj = J @ (Jp @ d)                 # J J+ d = reachable-subspace part
    nd = float(np.linalg.norm(d))
    return float(np.linalg.norm(proj) / nd) if nd > 0 else 0.0


def is_idempotent(P, atol: float = 1e-9) -> bool:
    P = np.asarray(P, dtype=float)
    return bool(np.allclose(P @ P, P, atol=atol))


def predict_intervention(J, delta_xi_target, lam: float = 0.0,
                         reach_floor: float = 0.50):
    """The realizer step. Returns delta_c and an honest status."""
    eta, label, meta = right_inverse(J, lam)
    d = np.asarray(delta_xi_target, dtype=float)
    delta_c = eta @ d
    rf = reachable_fraction(J, d)
    Jp = moore_penrose(J)
    reachable_component = J @ (Jp @ d)
    status = "OK" if rf >= reach_floor else "TARGET_PARTIALLY_UNREACHABLE"
    return {"delta_c": delta_c, "label": label,
            "reachable_fraction": rf, "status": status,
            "reachable_component": reachable_component, "meta": meta}
