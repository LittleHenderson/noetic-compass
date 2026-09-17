"""Tests for the closed-form initialisation of the registered ``^6`` decompose block.

Subject under test: ``cncm/analytic_decompose.py``.

These tests defend two claims that the architecture proposal rests on:

1. The registered module ``merge @ concat(tanh(left x), tanh(right x))`` contains the map
   ``x |-> T tanh(x)`` *exactly* for any ``T``, via ``left = I``, ``right = 0``,
   ``merge = [T | 0]``.
2. Any free-readout weight matrix ``W`` is realisable through the *frozen* readout rows
   ``R`` by ``T = R^-1 W^T``, so the frozen readout is not a constraint.

The frozen readout rows are rebuilt here from the documented algorithm
(``sha256-rademacher-float32le-64/1``, ``binding.py`` line 198) rather than imported, so the
test does not depend on ``cas_meta2`` being on the path and independently confirms the
recorded row structure.

Plain pytest functions, no fixtures, no numeric runtime, no clock.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest

from cncm import analytic_decompose as ad

D = ad.D_MODEL
ROW_ALGORITHM = "sha256-rademacher-float32le-64/1"
SEED = 20260916


def frozen_readout_rows(symbols) -> list[list[float]]:
    """Rebuild frozen rows by the algorithm recorded in ``binding.row_bytes``.

    ``bits = int.from_bytes(sha256(canonical([ROW_ALGORITHM, seed, d_model, domain]))
    .digest()[:8], "little")``; entry ``i`` is ``+0.125`` when bit ``i`` is set, else
    ``-0.125``.
    """
    rows = []
    for symbol in symbols:
        domain = ["readout", symbol]
        canonical = json.dumps(
            [ROW_ALGORITHM, SEED, D, domain],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        bits = int.from_bytes(
            hashlib.sha256(canonical.encode()).digest()[:8], "little"
        )
        rows.append([0.125 if (bits >> i) & 1 else -0.125 for i in range(D)])
    return rows


def identity(size: int) -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(size)] for i in range(size)]


@pytest.fixture(scope="module")
def readout() -> list[list[float]]:
    return frozen_readout_rows([f"W{index}" for index in range(D)])


# --------------------------------------------------------------------------- #
# Linear algebra.
# --------------------------------------------------------------------------- #


def test_transpose_and_matmul_shapes():
    a = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    assert ad.transpose(a) == ((1.0, 4.0), (2.0, 5.0), (3.0, 6.0))
    assert ad.matmul(a, identity(3)) == ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.matmul(identity(3), identity(4))


def test_matvec_matches_the_hand_product():
    matrix = [[1.0, 2.0], [3.0, 4.0]]
    assert ad.matvec(matrix, (5.0, 6.0)) == (17.0, 39.0)
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.matvec(matrix, (5.0, 6.0, 7.0))


def test_solve_inverts_a_known_system():
    matrix = [[2.0, 1.0], [1.0, 3.0]]
    rhs = [[1.0, 0.0], [0.0, 1.0]]
    result = ad.solve(matrix, rhs)
    product = ad.matmul(matrix, result)
    assert product[0][0] == pytest.approx(1.0, abs=1e-12)
    assert product[1][1] == pytest.approx(1.0, abs=1e-12)
    assert product[0][1] == pytest.approx(0.0, abs=1e-12)


def test_solve_returns_none_for_a_singular_system():
    assert ad.solve([[1.0, 2.0], [2.0, 4.0]], [[1.0], [1.0]]) is None
    assert ad.solve([[0.0]], [[1.0]]) is None


def test_solve_refuses_bad_shapes():
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.solve([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], [[1.0], [1.0]])
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.solve([[1.0, 0.0], [0.0, 1.0]], [[1.0]])


# --------------------------------------------------------------------------- #
# The real frozen readout rows.
# --------------------------------------------------------------------------- #


def test_rebuilt_readout_rows_have_the_recorded_structure(readout):
    assert len(readout) == D
    for row in readout:
        assert len(row) == D
        assert set(row) == {-0.125, 0.125}
        assert math.sqrt(math.fsum(value * value for value in row)) == pytest.approx(
            1.0, abs=1e-15
        )


def test_the_real_readout_rows_are_linearly_independent(readout):
    report = ad.inverse_diagnostics(readout)
    assert report["invertible"] is True
    assert report["order"] == D
    assert report["residual"] < 1e-12


def test_inverse_diagnostics_reports_dependence_instead_of_guessing():
    dependent = [[1.0] * 4 for _ in range(4)]
    report = ad.inverse_diagnostics(dependent)
    assert report["invertible"] is False
    assert report["residual"] is None


# --------------------------------------------------------------------------- #
# Claim 1: the registered module contains x -> T tanh(x) exactly.
# --------------------------------------------------------------------------- #


def test_parameters_carry_the_registered_shapes():
    parameters = ad.parameters_for_map(identity(D))
    assert parameters.shapes() == ad.REGISTERED_PARAMETER_SHAPES
    assert parameters.matches_registered_shapes() is True
    assert ad.REGISTERED_PARAMETER_SHAPES == {
        "left.weight": (64, 64),
        "right.weight": (64, 64),
        "merge.weight": (64, 128),
    }


def test_forward_equals_T_tanh_x_exactly():
    target = [[0.5 if i == j else 0.01 for j in range(D)] for i in range(D)]
    parameters = ad.parameters_for_map(target)
    values = [[math.sin(0.37 * (i + 1) * (j + 1)) for j in range(D)] for i in range(6)]
    assert ad.identity_residual(parameters, values) == 0.0
    for value in values:
        expected = ad.matvec(target, tuple(math.tanh(entry) for entry in value))
        assert parameters.forward(value) == expected


def test_the_right_branch_contributes_nothing():
    """Perturbing the right half of ``merge`` must not move the output."""
    target = [[0.25 if i == j else 0.0 for j in range(D)] for i in range(D)]
    parameters = ad.parameters_for_map(target)
    value = [0.1 * (index + 1) for index in range(D)]
    baseline = parameters.forward(value)
    noisy_merge = tuple(
        tuple(
            row[j] + (1e6 if j >= D else 0.0) for j in range(2 * D)
        )
        for row in parameters.merge
    )
    noisy = ad.DecomposeParameters(
        left=parameters.left, right=parameters.right, merge=noisy_merge
    )
    assert noisy.forward(value) == baseline


def test_identity_parameters_forward_is_tanh():
    parameters = ad.identity_parameters()
    value = [0.4 * math.cos(index) for index in range(D)]
    assert parameters.forward(value) == tuple(math.tanh(entry) for entry in value)


def test_identity_residual_refuses_when_the_right_branch_is_live():
    parameters = ad.identity_parameters()
    live_right = tuple(
        tuple(1.0 if i == j else 0.0 for j in range(D)) for i in range(D)
    )
    mutated = ad.DecomposeParameters(
        left=parameters.left, right=live_right, merge=parameters.merge
    )
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.identity_residual(mutated, [[0.0] * D])


def test_decompose_parameters_refuse_malformed_matrices():
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.DecomposeParameters(
            left=((1.0,),), right=((1.0,),), merge=((1.0,),)
        ).forward([0.0] * D)


def test_forward_refuses_a_non_finite_input():
    parameters = ad.identity_parameters()
    value = [0.0] * D
    value[0] = float("inf")
    with pytest.raises(ad.AnalyticDecomposeError):
        parameters.forward(value)


# --------------------------------------------------------------------------- #
# Claim 2: the frozen readout realises any free readout exactly.
# --------------------------------------------------------------------------- #


def test_score_residual_is_at_floating_point_precision(readout):
    """The identity is at the score level, and this is the number that proves it."""
    targets = [index % D for index in range(D)]
    weights = ad.ridge_weights(readout, targets, lam=1e-6)
    residual = ad.realisation_score_residual(weights, readout, readout)
    assert residual < 1e-12


def test_the_frozen_readout_reproduces_the_free_argmax(readout):
    targets = [index % D for index in range(D)]
    weights = ad.ridge_weights(readout, targets, lam=1e-6)
    assert ad.realisation_agreement(weights, readout, readout) == 1.0


def test_constructed_parameters_make_the_frozen_readout_act_as_the_free_one(readout):
    targets = [index % D for index in range(D)]
    weights = ad.ridge_weights(readout, targets, lam=1e-6)
    parameters = ad.decompose_from_free_readout(weights, readout)
    for row in readout:
        free = ad.free_readout_scores(weights, ad.tanh_vector(row))
        through = ad.frozen_readout_scores(readout, parameters, row)
        assert max(abs(a - b) for a, b in zip(free, through)) < 1e-12


def test_forgetting_the_tanh_breaks_the_identity(readout):
    """The construction is linear in ``tanh(x)``, not in ``x``.

    Comparing the free readout on the raw input against the frozen readout on
    ``forward(x)`` compares ``Wᵀ x`` with ``Wᵀ tanh(x)``. They are not equal, and this test
    pins that difference so the mistake cannot be mistaken for a construction failure.
    """
    targets = [index % D for index in range(D)]
    weights = ad.ridge_weights(readout, targets, lam=1e-6)
    parameters = ad.decompose_from_free_readout(weights, readout)
    worst = 0.0
    for row in readout:
        wrong = ad.free_readout_scores(weights, row)
        through = ad.frozen_readout_scores(readout, parameters, row)
        worst = max(worst, max(abs(a - b) for a, b in zip(wrong, through)))
    assert worst > 1e-6, "the raw-input comparison should visibly disagree"
    assert ad.tanh_vector(readout[0]) != tuple(readout[0])


def test_the_frozen_readout_agrees_even_though_tanh_moves_the_scores(readout):
    """Exactness is judged on ``tanh(x)``; the argmax survives it on this data."""
    targets = [index % D for index in range(D)]
    weights = ad.ridge_weights(readout, targets, lam=1e-6)
    assert ad.realisation_agreement(weights, readout, readout) == 1.0
    assert ad.realisation_score_residual(weights, readout, readout) < 1e-12


def test_a_singular_readout_is_refused_and_not_approximated():
    degenerate = [[1.0] * D for _ in range(D)]
    weights = ad.ridge_weights(degenerate, [index % D for index in range(D)], lam=1e-6)
    with pytest.raises(ad.AnalyticDecomposeError) as caught:
        ad.decompose_from_free_readout(weights, degenerate)
    assert "singular" in str(caught.value)
    assert "approximation" in str(caught.value)


def test_decompose_refuses_a_readout_of_the_wrong_order():
    weights = [[0.0] * 4 for _ in range(4)]
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.decompose_from_free_readout(weights, [[0.0] * 4 for _ in range(4)])
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.decompose_from_free_readout(weights, [[0.0] * D for _ in range(D)])


def test_decompose_refuses_a_core_width_other_than_the_registered_one():
    weights = [[0.0] * D for _ in range(D)]
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.decompose_from_free_readout(weights, [[0.0] * D for _ in range(D)], core_width=32)


# --------------------------------------------------------------------------- #
# Ridge.
# --------------------------------------------------------------------------- #


def test_ridge_recovers_a_well_posed_linear_system():
    rows = [[float(i == j) for j in range(D)] for i in range(D)]
    targets = [index % D for index in range(D)]
    weights = ad.ridge_weights(rows, targets, lam=1e-9)
    for row, target in zip(rows, targets):
        scores = ad.free_readout_scores(weights, row)
        assert max(range(D), key=lambda c: scores[c]) == target


def test_the_free_readout_score_is_the_column_not_the_row():
    """``ridge_weights`` returns ``d x nclass`` with column ``c`` the class-``c`` weight.

    A square well-conditioned matrix makes the two orientations visibly different, so this
    pins the convention that :func:`free_readout_scores` documents.
    """
    weights = [[1.0, 2.0], [3.0, 4.0]]
    value = (1.0, 0.0)
    # columns: c0 = (1, 3), c1 = (2, 4) -> scores (1.0, 2.0)
    assert ad.free_readout_scores([[1.0, 2.0], [3.0, 4.0]], value) == (1.0, 2.0)
    # rows would give (1.0, 3.0) instead
    assert ad.matvec(weights, value) == (1.0, 3.0)


def test_ridge_refuses_bad_targets_and_penalties():
    rows = [[1.0, 0.0], [0.0, 1.0]]
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.ridge_weights(rows, [0], nclass=2)
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.ridge_weights(rows, [0, 5], nclass=2)
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.ridge_weights(rows, [0, True], nclass=2)
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.ridge_weights(rows, [0, 1], nclass=2, lam=float("nan"))
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.ridge_weights(rows, [0, 1], nclass=2, lam=-1.0)
    with pytest.raises(ad.AnalyticDecomposeError):
        ad.ridge_weights([], [], nclass=2)


def test_shuffled_label_control_is_deterministic_and_different():
    rows = [[0.3 * math.sin(i * j + 1) for j in range(D)] for i in range(40)]
    targets = [index % D for index in range(40)]
    plain = ad.ridge_weights(rows, targets, lam=1e-3)
    first = ad.shuffled_label_control(rows, targets, seed=7, lam=1e-3)
    second = ad.shuffled_label_control(rows, targets, seed=7, lam=1e-3)
    other = ad.shuffled_label_control(rows, targets, seed=8, lam=1e-3)
    assert first == second
    assert first != plain
    assert other != first
    assert len(first) == D and len(first[0]) == D


def test_the_shuffled_control_is_near_chance_on_separable_data(readout):
    """A wrong solve must not score. This is the null the arm-C control relies on."""
    weights = ad.shuffled_label_control(readout, [index % D for index in range(D)],
                                        seed=11, lam=1e-6)
    hits = 0
    for index, row in enumerate(readout):
        scores = ad.free_readout_scores(weights, row)
        hits += 1 if max(range(D), key=lambda c: scores[c]) == index else 0
    assert hits <= 4, f"a wrong solve scored {hits}/{D}, so a right solve proves nothing"


# --------------------------------------------------------------------------- #
# Scope and purity.
# --------------------------------------------------------------------------- #


def test_scope_declaration_states_what_does_not_change():
    scope = ad.scope_declaration()
    assert scope["schema"] == ad.SCHEMA_VERSION
    assert scope["operation"] == "cas.cjt.operation.^6.decompose/0.2"
    assert scope["role"] == "operation:^6"
    assert scope["new_parameters"] == 0
    assert scope["requires_gpu_for_the_solve"] is False
    assert scope["requires_owner_record_to_run"] is True
    unchanged = set(scope["unchanged"])
    for required in (
        "registered parameter names",
        "registered parameter shapes",
        "registered plasticity scope",
        "frozen encoder",
        "frozen readout rows",
        "the loss",
    ):
        assert required in unchanged
    assert "ARCHITECTURE_CHANGE_SPEC_v0.2_ANALYTIC_DECOMPOSE_INIT.md" in scope["spec"]


def test_the_module_declares_no_numeric_runtime_import():
    source = Path(ad.__file__).read_text(encoding="utf-8")
    assert "\nimport torch" not in source
    assert "\nfrom torch" not in source
    assert "\nimport numpy" not in source
    assert "\nfrom numpy" not in source
    assert "\nimport boto3" not in source
    assert "\nimport socket" not in source


def test_the_module_reads_no_clock_and_no_randomness():
    source = Path(ad.__file__).read_text(encoding="utf-8")
    for module in ("datetime", "random", "uuid"):
        assert f"\nimport {module}" not in source
        assert f"\nfrom {module}" not in source
    assert "\ntime." not in source
