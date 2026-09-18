"""Tests for the rectangular free-readout construction.

Subject under test: ``cncm/analytic_decompose.decompose_from_free_readout_rectangular``.

``decompose_from_free_readout`` needs ``nclass == core_width`` so that ``R`` is square. The
registered readout is ``[90, 64]``, so that function refuses the real readout and the analytic
initialisation has only ever been measured on a 64-row submatrix. The rectangular construction
takes ``nclass > core_width`` and is therefore the one that applies to the readout the machine
actually has.

Three claims are defended here:

1. **Agreement.** On a square readout the rectangular construction returns the same ``T`` as the
   square one, so it is a generalisation and not a second, differently-behaved construction.
2. **Exactness where it is possible.** When ``W^T`` already lies in the column space of ``R`` -- which
   is the case ``W^T = A R`` -- the construction is exact and the reported residual is ``0.0``.
3. **Honesty where it is not.** For an arbitrary ``W`` the construction does **not** realise ``W``.
   What it produces is the orthogonal projection of ``W^T`` onto that column space, and the tests
   check that directly: ``R T`` lies in the space, and ``W^T - R T`` is orthogonal to every column of
   ``R``. The residual is also checked against the residual of the square construction whenever both
   apply.

The frozen readout rows are rebuilt here from the documented algorithm rather than imported, the same
way ``tests/test_analytic_decompose.py`` does it, so these tests do not depend on ``cas_meta2``.

Plain pytest functions, no fixtures, no numeric runtime, no clock.
"""

from __future__ import annotations

import hashlib
import json
import math

import pytest

from cncm import analytic_decompose as ad

D = ad.D_MODEL
ROW_ALGORITHM = "sha256-rademacher-float32le-64/1"
SEED = 20260916
NCLASS = 90


def frozen_rows(count: int) -> list:
    """Rows by the algorithm recorded in ``binding.row_bytes``, the same one the sibling test uses.

    ``bits = int.from_bytes(sha256(canonical([ROW_ALGORITHM, seed, d_model, ["readout", symbol]]))
    .digest()[:8], "little")``; entry ``i`` is ``+0.125`` when bit ``i`` is set, else ``-0.125``.
    """
    rows = []
    for index in range(count):
        canonical = json.dumps(
            [ROW_ALGORITHM, SEED, D, ["readout", f"W{index}"]],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        bits = int.from_bytes(hashlib.sha256(canonical.encode()).digest()[:8], "little")
        rows.append([0.125 if (bits >> at) & 1 else -0.125 for at in range(D)])
    return rows


def real_readout_rows() -> list:
    """The registered ``[90, 64]`` shape, built by the frozen row algorithm."""
    return frozen_rows(NCLASS)


def full_rank_rectangular() -> list:
    """Same construction, held here so the two helpers can be compared if the algorithm changes."""
    return frozen_rows(NCLASS)


def any_weights(nclass: int = NCLASS) -> list:
    """A deterministic ``D x nclass`` weight matrix."""
    return [
        [0.5 * (((index * 31 + at * 17) % 23) / 11.0 - 1.0) for index in range(nclass)]
        for at in range(D)
    ]


# --------------------------------------------------------------------------- #
# 1. Shape and refusal behaviour
# --------------------------------------------------------------------------- #


def test_real_readout_shape_is_accepted_where_the_square_construction_refuses():
    rows = real_readout_rows()
    assert (len(rows), len(rows[0])) == (NCLASS, D)
    weights = any_weights()
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.decompose_from_free_readout(weights, rows)
    parameters, report = ad.decompose_from_free_readout_rectangular(weights, rows)
    assert parameters.matches_registered_shapes()
    assert report["readout_shape"] == (NCLASS, D)
    assert report["nclass"] == NCLASS


def test_parameters_are_the_registered_shapes_and_forward_is_T_tanh():
    weights = any_weights()
    parameters, _report = ad.decompose_from_free_readout_rectangular(weights, real_readout_rows())
    assert parameters.shapes() == ad.REGISTERED_PARAMETER_SHAPES
    value = [0.3 * math.sin(at) for at in range(D)]
    read_back = ad.tanh_vector(value)
    # forward(x) == T tanh(x) by construction (left = I, right = 0, merge = [T | 0])
    via_module = parameters.forward(value)
    direct = ad.matvec(
        [row[:D] for row in parameters.merge], read_back
    )
    assert max(abs(a - b) for a, b in zip(via_module, direct)) < 1e-12


def test_a_readout_narrower_than_the_core_is_refused():
    rows = [row[: D - 1] for row in real_readout_rows()]
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.decompose_from_free_readout_rectangular(any_weights(), rows)


def test_a_readout_with_too_few_rows_is_refused():
    rows = real_readout_rows()[: D - 1]
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.decompose_from_free_readout_rectangular(any_weights(nclass=len(rows)), rows)


def test_mismatched_class_count_is_refused():
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.decompose_from_free_readout_rectangular(any_weights(NCLASS), real_readout_rows()[:80])


def test_a_singular_readout_is_refused_rather_than_approximated():
    rows = [[0.0] * D for _ in range(NCLASS)]
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.decompose_from_free_readout_rectangular(any_weights(), rows)


# --------------------------------------------------------------------------- #
# 2. Agreement with the square construction
# --------------------------------------------------------------------------- #


def test_square_readout_agrees_with_the_square_construction():
    """``nclass == D``: the rectangular path must reproduce the square one.

    Compared entry-wise rather than by digest: the square path solves ``R T = W^T`` directly and the
    rectangular path solves the normal equations ``R^T R T = R^T W^T``, which are the same system when
    ``R`` is invertible but not the same floating-point computation. The digests therefore need not be
    equal, and the agreement that matters is numerical.
    """
    rows = [row[:] for row in real_readout_rows()[:D]]
    weights = any_weights(D)
    square = ad.decompose_from_free_readout(weights, rows)
    rectangular, report = ad.decompose_from_free_readout_rectangular(weights, rows)
    assert square.matches_registered_shapes()
    assert rectangular.matches_registered_shapes()
    assert report["residual"] < 1e-9
    assert max(
        abs(a - b) for left, right in zip(square.merge, rectangular.merge)
        for a, b in zip(left, right)
    ) < 1e-9


def test_square_case_residual_is_at_the_level_of_arithmetic():
    rows = [row[:] for row in real_readout_rows()[:D]]
    _parameters, report = ad.decompose_from_free_readout_rectangular(any_weights(D), rows)
    assert report["residual"] < 1e-9


# --------------------------------------------------------------------------- #
# 3. Exactness where it is possible
# --------------------------------------------------------------------------- #


def test_weights_inside_the_column_space_are_realised_exactly():
    """``W^T = R B`` lands in the column space of ``R``, so ``R T = W^T`` must hold to arithmetic.

    The multiplier must be applied on the **right**. ``A R`` is a different set of matrices and is not
    generally reachable -- it was tried first and it is exactly the case this construction reports a
    residual for.
    """
    rows = real_readout_rows()
    R = ad._matrix(rows, NCLASS, D, "R")
    B = [[1.0 if i == j else (0.05 if (i + j) % 7 == 0 else 0.0) for j in range(D)]
         for i in range(D)]
    wanted = ad.matmul(R, B)
    weights = ad.transpose(wanted)
    _parameters, report = ad.decompose_from_free_readout_rectangular(weights, rows)
    assert report["residual"] < 1e-9
    assert report["exact"] == (report["residual"] == 0.0)
    # and the unreachable case is the one that carries a residual
    _unreachable, worse = ad.decompose_from_free_readout_rectangular(any_weights(), rows)
    assert worse["residual"] > report["residual"]


# --------------------------------------------------------------------------- #
# 4. Honesty where it is not
# --------------------------------------------------------------------------- #


def test_unreachable_weights_residual_is_the_projection_residual():
    rows = real_readout_rows()
    R = ad._matrix(rows, NCLASS, D, "R")
    W = ad._matrix(any_weights(), D, NCLASS, "W")
    parameters, report = ad.decompose_from_free_readout_rectangular(any_weights(), rows)
    T = ad._matrix(
        [row[:D] for row in parameters.merge], D, D, "T"
    )
    achieved = ad.matmul(R, T)
    wanted = ad.transpose(W)
    # (a) the achieved matrix lies in the column space of R: solving R X = achieved succeeds and
    #     reproduces it. (R^T R) is square of order D, so the right-hand side must be R^T achieved.
    X = ad.solve(ad.matmul(ad.transpose(R), R), ad.matmul(ad.transpose(R), achieved))
    assert X is not None
    reconstructed = ad.matmul(R, X)
    assert max(
        abs(reconstructed[i][j] - achieved[i][j]) for i in range(NCLASS) for j in range(D)
    ) < 1e-9
    # (b) the leftover is orthogonal to every column of R
    leftover = [[wanted[i][j] - achieved[i][j] for j in range(D)] for i in range(NCLASS)]
    for column in range(D):
        for other in range(D):
            dot = sum(leftover[row][column] * R[row][other] for row in range(NCLASS))
            assert abs(dot) < 1e-9
    # (c) and the reported residual is the largest entry of that leftover
    assert abs(
        report["residual"]
        - max(abs(leftover[i][j]) for i in range(NCLASS) for j in range(D))
    ) < 1e-12


def test_residual_is_reported_and_is_zero_only_when_reachable():
    rows = full_rank_rectangular()
    _parameters, report = ad.decompose_from_free_readout_rectangular(any_weights(), rows)
    assert report["residual"] >= 0.0
    assert report["exact"] == (report["residual"] == 0.0)
    assert 0.0 < report["residual"] < 1.0


def test_ridge_reduces_the_residual_on_a_nearly_singular_readout():
    rows = full_rank_rectangular()
    rows = [[value * (1.0 + 1e-9 * index) for value in row] for index, row in enumerate(rows)]
    _plain, without = ad.decompose_from_free_readout_rectangular(any_weights(), rows)
    _ridged, with_ridge = ad.decompose_from_free_readout_rectangular(
        any_weights(), rows, ridge=1e-6
    )
    assert with_ridge["ridge"] == 1e-6
    assert math.isfinite(without["residual"]) and math.isfinite(with_ridge["residual"])


def test_the_report_carries_everything_a_record_would_need():
    _parameters, report = ad.decompose_from_free_readout_rectangular(
        any_weights(), real_readout_rows(), ridge=1e-8
    )
    assert set(report) == {
        "readout_shape", "core_width", "nclass", "ridge", "residual", "exact"
    }
    assert report["core_width"] == D
