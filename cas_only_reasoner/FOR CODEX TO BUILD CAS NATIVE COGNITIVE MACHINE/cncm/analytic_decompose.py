"""Closed-form initialisation of the registered ``^6`` decompose block.

This module is the executable form of
``records/encoder_capacity_001/ARCHITECTURE_CHANGE_SPEC_v0.2_ANALYTIC_DECOMPOSE_INIT.md``.
It contains the arithmetic; it does not contain a run, a device, or a schedule.

The registered module
---------------------
The registered ``^6`` operation is ``cas_cjt.neural._DecomposeTransform``:

    left.weight   (64,  64)
    right.weight  (64,  64)
    merge.weight  (64, 128)

    forward(x) = merge @ concat( tanh(left @ x), tanh(right @ x) )

The construction
----------------
Setting ``left = I``, ``right = 0`` and ``merge = [T | 0]`` gives, for every input ``x``,

    forward(x) = [T | 0] @ [ tanh(x) ; tanh(0) ] = T @ tanh(x)

as an identity, not an approximation: the right branch contributes ``tanh(0) = 0`` and the
right half of ``merge`` is zero. So the registered module can implement any ``x |-> T·tanh(x)``
exactly, with no new parameter, no shape change, no scope change and no contract change.

Realising a free readout through the frozen one
-----------------------------------------------
The learner's readout is frozen: ``logits_c = r_c · (T φ)`` for frozen unit rows ``r_c``.
With ``R`` the matrix whose row ``c`` is ``r_c`` and ``W`` a free-readout weight matrix
(column ``c`` = the class-``c`` weight vector), the choice

    T = R⁻¹ Wᵀ        (equivalently Tᵀ = W (Rᵀ)⁻¹)

gives ``r_c · (T φ) = (Tᵀ r_c) · φ = W_c · φ`` for every class, so the frozen readout
computes exactly the free-readout score vector. The construction is available exactly when
``R`` is invertible; :func:`decompose_from_free_readout` refuses rather than approximating.

Grounding
---------
- The registered shapes and the forward-pass identity:
  ``records/encoder_capacity_001/REACHABLE_SOLUTION_RESULT.md``, measured.
- The free readout's accuracy on the real encoded slot: 63.65% (5-fold CV), reproduced from
  ``measure_real_slot_encoding.py`` by ``measure_reachable_solution.py``.
- The reachable class's accuracy: 63.83%, with 100.00% argmax agreement through the frozen
  readout rows and max |RᵀR⁻ᵀ − I| = 2.798e-14.

Pure standard library. No torch, no device, no gradient, no wall-clock input. Nothing here
trains and nothing here authorises a run.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence

from .canonical import digest

#: Width of the registered core vector, from ``cas_cjt`` config ``d_model``.
D_MODEL = 64

#: The registered parameter names and shapes, verbatim from
#: ``cas_meta2/typed_teaching/learner.py`` :data:`PARAMETER_SHAPES`.
REGISTERED_PARAMETER_SHAPES = {
    "left.weight": (D_MODEL, D_MODEL),
    "right.weight": (D_MODEL, D_MODEL),
    "merge.weight": (D_MODEL, 2 * D_MODEL),
}

SCHEMA_VERSION = "cncm.analytic-decompose/0.1"

#: Ridge penalty used throughout the recorded measurements. Kept as a named constant so a
#: caller cannot silently change it and still claim to reproduce them.
DEFAULT_RIDGE_LAMBDA = 1.0


class AnalyticDecomposeError(ValueError):
    """The construction was asked for something it cannot supply exactly."""


def _matrix(value: Iterable[Iterable[float]], rows: int, cols: int, name: str) -> tuple:
    if isinstance(value, (str, bytes)):
        raise AnalyticDecomposeError(f"{name} must be a sequence of rows")
    out = []
    for index, row in enumerate(value):
        if isinstance(row, (str, bytes)):
            raise AnalyticDecomposeError(f"{name} row {index} must be a sequence")
        entries = tuple(row)
        if len(entries) != cols:
            raise AnalyticDecomposeError(
                f"{name} row {index} has {len(entries)} entries, expected {cols}"
            )
        converted = []
        for position, entry in enumerate(entries):
            if isinstance(entry, bool) or not isinstance(entry, (int, float)):
                raise AnalyticDecomposeError(f"{name}[{index}][{position}] is not a number")
            number = float(entry)
            if not math.isfinite(number):
                raise AnalyticDecomposeError(f"{name}[{index}][{position}] is not finite")
            converted.append(number)
        out.append(tuple(converted))
    if len(out) != rows:
        raise AnalyticDecomposeError(f"{name} has {len(out)} rows, expected {rows}")
    return tuple(out)


def _vector(value: Iterable[float], length: int, name: str) -> tuple:
    if isinstance(value, (str, bytes)):
        raise AnalyticDecomposeError(f"{name} must be a sequence of numbers")
    entries = tuple(value)
    if len(entries) != length:
        raise AnalyticDecomposeError(f"{name} has {len(entries)} entries, expected {length}")
    out = []
    for index, entry in enumerate(entries):
        if isinstance(entry, bool) or not isinstance(entry, (int, float)):
            raise AnalyticDecomposeError(f"{name}[{index}] is not a number")
        number = float(entry)
        if not math.isfinite(number):
            raise AnalyticDecomposeError(f"{name}[{index}] is not finite")
        out.append(number)
    return tuple(out)


# --------------------------------------------------------------------------- #
# Small dense linear algebra. Sizes here are 64 x 64; nothing larger is needed.
# --------------------------------------------------------------------------- #


def transpose(matrix: Sequence[Sequence[float]]) -> tuple:
    if not matrix:
        return ()
    return tuple(tuple(row) for row in zip(*matrix))


def matmul(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> tuple:
    if not left or not right:
        raise AnalyticDecomposeError("matmul needs two non-empty matrices")
    if len(left[0]) != len(right):
        raise AnalyticDecomposeError(
            f"matmul shape mismatch: {len(left)}x{len(left[0])} by "
            f"{len(right)}x{len(right[0])}"
        )
    right_t = transpose(right)
    return tuple(
        tuple(math.fsum(a * b for a, b in zip(row, column)) for column in right_t)
        for row in left
    )


def matvec(matrix: Sequence[Sequence[float]], vector: Sequence[float]) -> tuple:
    if len(matrix[0]) != len(vector):
        raise AnalyticDecomposeError("matvec shape mismatch")
    return tuple(math.fsum(a * b for a, b in zip(row, vector)) for row in matrix)


def solve(matrix: Sequence[Sequence[float]], rhs: Sequence[Sequence[float]]) -> tuple | None:
    """Return ``matrix⁻¹ @ rhs`` by Gauss-Jordan with partial pivoting, or ``None``.

    ``None`` means the system is singular at the working precision. Callers here treat that
    as a refusal, never as a reason to fall back on an approximation.
    """
    n = len(matrix)
    if n == 0 or len(matrix[0]) != n:
        raise AnalyticDecomposeError("solve needs a square matrix")
    if len(rhs) != n:
        raise AnalyticDecomposeError("solve rhs row count must match the matrix order")
    width = len(rhs[0])
    work = [
        list(matrix[i]) + list(rhs[i])
        for i in range(n)
    ]
    for column in range(n):
        pivot = max(range(column, n), key=lambda r: abs(work[r][column]))
        if abs(work[pivot][column]) < 1e-12:
            return None
        work[column], work[pivot] = work[pivot], work[column]
        value = work[column][column]
        work[column] = [entry / value for entry in work[column]]
        for row in range(n):
            if row != column and work[row][column]:
                factor = work[row][column]
                work[row] = [
                    a - factor * b for a, b in zip(work[row], work[column])
                ]
    return tuple(tuple(row[n:n + width]) for row in work)


def inverse_diagnostics(matrix: Sequence[Sequence[float]]) -> dict:
    """Measure ``R`` rather than assume it. Reports the residual of ``R R⁻¹ − I``.

    The recorded measurement of the registered readout gave max |Rᵀ R⁻ᵀ − I| = 2.798e-14.
    A caller that wants to claim the construction is available must be able to reproduce
    something of that order, so this returns the number instead of a boolean.
    """
    n = len(matrix)
    unit = tuple(tuple(1.0 if i == j else 0.0 for j in range(n)) for i in range(n))
    result = solve(matrix, unit)
    if result is None:
        return {"invertible": False, "residual": None, "order": n}
    product = matmul(matrix, result)
    residual = max(
        abs(product[i][j] - (1.0 if i == j else 0.0))
        for i in range(n)
        for j in range(n)
    )
    return {"invertible": True, "residual": residual, "order": n}


# --------------------------------------------------------------------------- #
# The registered module, as plain arithmetic.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DecomposeParameters:
    """The three registered ``^6`` matrices, in the registered shapes."""

    left: tuple
    right: tuple
    merge: tuple

    def shapes(self) -> dict:
        return {
            "left.weight": (len(self.left), len(self.left[0])),
            "right.weight": (len(self.right), len(self.right[0])),
            "merge.weight": (len(self.merge), len(self.merge[0])),
        }

    def matches_registered_shapes(self) -> bool:
        return self.shapes() == REGISTERED_PARAMETER_SHAPES

    def digest(self) -> str:
        return digest(
            {
                "schema": SCHEMA_VERSION,
                "left.weight": [list(row) for row in self.left],
                "right.weight": [list(row) for row in self.right],
                "merge.weight": [list(row) for row in self.merge],
            }
        )

    def forward(self, value: Sequence[float]) -> tuple:
        """``merge @ concat(tanh(left @ x), tanh(right @ x))``, exactly as registered."""
        vector = _vector(value, D_MODEL, "value")
        left_out = tuple(math.tanh(entry) for entry in matvec(self.left, vector))
        right_out = tuple(math.tanh(entry) for entry in matvec(self.right, vector))
        return matvec(self.merge, left_out + right_out)

    def parameter_dict(self) -> dict:
        return {
            "left.weight": self.left,
            "right.weight": self.right,
            "merge.weight": self.merge,
        }


def identity_parameters() -> DecomposeParameters:
    """``left = I``, ``right = 0``, ``merge = [I | 0]``: the identity in the linear regime.

    Included as the reference point for the identity checks. ``forward(x)`` here is
    ``tanh(x)``, not ``x``, which is the whole reason the construction has to be stated as a
    statement about ``tanh(x)`` and not about ``x``.
    """
    unit = tuple(tuple(1.0 if i == j else 0.0 for j in range(D_MODEL)) for i in range(D_MODEL))
    zero = tuple(tuple(0.0 for _ in range(D_MODEL)) for _ in range(D_MODEL))
    merge = tuple(
        tuple(1.0 if i == j else 0.0 for j in range(2 * D_MODEL)) for i in range(D_MODEL)
    )
    return DecomposeParameters(left=unit, right=zero, merge=merge)


def parameters_for_map(T: Sequence[Sequence[float]]) -> DecomposeParameters:
    """Wrap an arbitrary ``64 x 64`` map ``T`` as registered ``^6`` parameters.

    Returns parameters satisfying ``forward(x) == T @ tanh(x)`` for every finite ``x``.
    """
    matrix = _matrix(T, D_MODEL, D_MODEL, "T")
    left = tuple(
        tuple(1.0 if i == j else 0.0 for j in range(D_MODEL)) for i in range(D_MODEL)
    )
    right = tuple(tuple(0.0 for _ in range(D_MODEL)) for _ in range(D_MODEL))
    merge = tuple(
        tuple(matrix[i][j] if j < D_MODEL else 0.0 for j in range(2 * D_MODEL))
        for i in range(D_MODEL)
    )
    return DecomposeParameters(left=left, right=right, merge=merge)


def ridge_weights(
    features: Sequence[Sequence[float]],
    targets: Sequence[int],
    *,
    nclass: int = D_MODEL,
    lam: float = DEFAULT_RIDGE_LAMBDA,
) -> tuple:
    """Closed-form ridge: ``W = (XᵀX + lam I)⁻¹ Xᵀ Y`` with one-hot ``Y``.

    Returns a ``d x nclass`` matrix. Raises when the normal equations are singular.
    """
    if not features:
        raise AnalyticDecomposeError("ridge needs at least one row")
    width = len(features[0])
    rows = [_vector(row, width, "features row") for row in features]
    if len(targets) != len(rows):
        raise AnalyticDecomposeError("targets length must match the feature row count")
    for index, target in enumerate(targets):
        if isinstance(target, bool) or not isinstance(target, int):
            raise AnalyticDecomposeError(f"target {index} is not an integer class")
        if not 0 <= target < nclass:
            raise AnalyticDecomposeError(f"target {index} = {target} is outside 0..{nclass - 1}")
    if not math.isfinite(lam) or lam < 0.0:
        raise AnalyticDecomposeError("ridge penalty must be finite and non-negative")

    gram = [[0.0] * width for _ in range(width)]
    for i in range(width):
        for j in range(i, width):
            total = math.fsum(row[i] * row[j] for row in rows)
            gram[i][j] = total
            gram[j][i] = total
    for i in range(width):
        gram[i][i] += lam
    cross = [[0.0] * nclass for _ in range(width)]
    for row, target in zip(rows, targets):
        for i in range(width):
            cross[i][target] += row[i]
    result = solve(gram, cross)
    if result is None:
        raise AnalyticDecomposeError("ridge normal equations are singular")
    return result


def decompose_from_free_readout(
    free_weights: Sequence[Sequence[float]],
    readout_rows: Sequence[Sequence[float]],
    *,
    core_width: int = D_MODEL,
    nclass: int = D_MODEL,
) -> DecomposeParameters:
    """Build registered ``^6`` parameters that make the frozen readout act as ``free_weights``.

    ``free_weights`` is ``d x nclass`` with column ``c`` the free-readout weight vector for
    class ``c``. ``readout_rows`` is ``nclass x d`` with row ``c`` the frozen readout row for
    class ``c``. The returned parameters satisfy, for every input ``x`` and every class ``c``,

        readout_rows[c] · forward(x)  ==  free_weights[:, c] · tanh(x)

    exactly, provided ``readout_rows`` is invertible. Refuses otherwise.
    """
    if core_width != D_MODEL:
        raise AnalyticDecomposeError(f"registered core width is {D_MODEL}, not {core_width}")
    W = _matrix(free_weights, core_width, nclass, "free_weights")
    R = _matrix(readout_rows, nclass, core_width, "readout_rows")
    if nclass != core_width:
        raise AnalyticDecomposeError(
            "the frozen readout must supply one row per class and the same number as the "
            "core width for the inverse to be square"
        )
    # T = R^-1 W^T, solved directly rather than by forming an explicit inverse.
    T = solve(R, transpose(W))
    if T is None:
        raise AnalyticDecomposeError(
            "the frozen readout rows are singular; the construction is unavailable and no "
            "approximation is substituted"
        )
    return parameters_for_map(T)


def free_readout_scores(
    free_weights: Sequence[Sequence[float]], value: Sequence[float]
) -> tuple:
    """Class scores of a free readout: index ``c`` is ``W[:, c] · value``.

    ``ridge_weights`` returns ``W`` in the ``d x nclass`` orientation with **column** ``c``
    the class-``c`` weight vector, so the score vector is ``Wᵀ value``, not ``W value``.
    The frozen readout is built the other way round — row ``c`` is ``r_c`` — so
    :func:`frozen_readout_scores` uses ``R value``. Both return a length-``nclass`` vector
    indexed by class; the two orientations are the one place this module can silently
    disagree with itself, so both are stated here.
    """
    W = _matrix(free_weights, len(free_weights), len(free_weights[0]), "free_weights")
    vector = _vector(value, len(W), "value")
    return matvec(transpose(W), vector)


def frozen_readout_scores(
    readout_rows: Sequence[Sequence[float]],
    parameters: DecomposeParameters,
    value: Sequence[float],
) -> tuple:
    """Class scores through the frozen readout: index ``c`` is ``r_c · forward(value)``."""
    R = _matrix(readout_rows, len(readout_rows), D_MODEL, "readout_rows")
    return matvec(R, parameters.forward(value))


def tanh_vector(value: Sequence[float]) -> tuple:
    """Elementwise ``tanh``. The module's linear regime is linear in ``tanh(x)``, not in
    ``x``, and conflating the two is the easiest way to get this construction wrong."""
    vector = _vector(value, D_MODEL, "value")
    return tuple(math.tanh(entry) for entry in vector)


def realisation_agreement(
    free_weights: Sequence[Sequence[float]],
    readout_rows: Sequence[Sequence[float]],
    values: Sequence[Sequence[float]],
) -> float:
    """Fraction of inputs where the frozen readout's argmax equals the free readout's.

    ``values`` are **module inputs** ``x``. Both sides are compared on the same feature:
    the free readout is applied to ``tanh(x)``, because that is what the constructed
    parameters feed it, and the frozen readout is applied to ``forward(x)``. Comparing the
    free readout on ``x`` against the frozen readout on ``forward(x)`` would compare
    ``Wᵀ x`` with ``Wᵀ tanh(x)`` and fail for a reason that has nothing to do with the
    construction.

    This is the check that the construction is exact rather than close. The recorded
    measurement over 564 real encoded slots is 1.0.
    """
    W = _matrix(free_weights, len(free_weights), len(free_weights[0]), "free_weights")
    R = _matrix(readout_rows, len(readout_rows), D_MODEL, "readout_rows")
    parameters = decompose_from_free_readout(W, R)
    nclass = len(W[0])
    Wt = transpose(W)
    agree = 0
    for value in values:
        free = matvec(Wt, tanh_vector(value))
        through = matvec(R, parameters.forward(value))
        if max(range(nclass), key=lambda c: free[c]) == max(
            range(nclass), key=lambda c: through[c]
        ):
            agree += 1
    return agree / len(values)


def realisation_score_residual(
    free_weights: Sequence[Sequence[float]],
    readout_rows: Sequence[Sequence[float]],
    values: Sequence[Sequence[float]],
) -> float:
    """Max ``|free_c − through_c|`` over classes and inputs — the exact statement.

    ``values`` are **module inputs** ``x``. The construction's claim is an identity at the
    score level: for every class ``c`` and every finite input ``x``,

        readout_rows[c] · forward(x)  ==  free_weights[:, c] · tanh(x)

    and both sides are evaluated that way here. This returns the largest violation of it,
    and is expected to be of order 1e-14.

    :func:`realisation_agreement` reports the argmax-level consequence, which is what a
    scored answer depends on. The two are not interchangeable: when two class scores differ
    by less than floating-point noise — which happens when a class received no training rows
    and its column is numerically zero — the argmax is decided by that noise and can differ
    even though the identity holds. The score residual is the stronger check.
    """
    W = _matrix(free_weights, len(free_weights), len(free_weights[0]), "free_weights")
    R = _matrix(readout_rows, len(readout_rows), D_MODEL, "readout_rows")
    parameters = decompose_from_free_readout(W, R)
    Wt = transpose(W)
    worst = 0.0
    for value in values:
        free = matvec(Wt, tanh_vector(value))
        through = matvec(R, parameters.forward(value))
        worst = max(worst, max(abs(a - b) for a, b in zip(free, through)))
    return worst


def identity_residual(
    parameters: DecomposeParameters, values: Sequence[Sequence[float]]
) -> float:
    """Max ``‖forward(x) − T·tanh(x)‖`` over ``values``, where ``T`` is read back out.

    Zero to floating-point precision for parameters produced by :func:`parameters_for_map`,
    which is what makes the construction an identity rather than an approximation.
    """
    left = parameters.left
    # Recover T from the parameters without assuming they were built by parameters_for_map:
    # forward(x) = merge @ [tanh(left x); tanh(right x)], so T is only well-defined when the
    # right branch is the zero map. Refuse to invent one otherwise.
    zero_right = all(entry == 0.0 for row in parameters.right for entry in row)
    if not zero_right:
        raise AnalyticDecomposeError(
            "the right branch is not the zero map, so no single T describes this module"
        )
    recovered = tuple(tuple(row[j] for j in range(D_MODEL)) for row in parameters.merge)
    worst = 0.0
    for value in values:
        vector = _vector(value, D_MODEL, "value")
        target = matvec(recovered, tuple(math.tanh(entry) for entry in vector))
        actual = parameters.forward(vector)
        worst = max(
            worst,
            math.sqrt(math.fsum((a - b) * (a - b) for a, b in zip(target, actual))),
        )
    return worst


def shuffled_label_control(
    features: Sequence[Sequence[float]],
    targets: Sequence[int],
    *,
    seed: int,
    nclass: int = D_MODEL,
    lam: float = DEFAULT_RIDGE_LAMBDA,
) -> tuple:
    """The arm-C null: fit the same solve against permuted labels.

    A deterministic Fisher-Yates permutation from a caller-supplied seed, so a control is
    reproducible without importing a random module. This exists because a solve that is
    applied with zero updates *is* the model, so a good score is not interpretable without
    knowing what a wrong solve scores.
    """
    rows = list(targets)
    state = seed & 0xFFFFFFFF
    for index in range(len(rows) - 1, 0, -1):
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        swap = state % (index + 1)
        rows[index], rows[swap] = rows[swap], rows[index]
    return ridge_weights(features, rows, nclass=nclass, lam=lam)


def scope_declaration() -> dict:
    """What this construction does and does not touch, for an evidence record."""
    return {
        "schema": SCHEMA_VERSION,
        "operation": "cas.cjt.operation.^6.decompose/0.2",
        "role": "operation:^6",
        "changes": "the initial values of the three registered parameter matrices only",
        "unchanged": [
            "registered parameter names",
            "registered parameter shapes",
            "registered plasticity scope",
            "registered update ceiling (max_updates <= 176)",
            "frozen encoder",
            "frozen readout rows",
            "the loss",
            "the curriculum",
        ],
        "new_parameters": 0,
        "requires_gpu_for_the_solve": False,
        "requires_owner_record_to_run": True,
        "spec": (
            "records/encoder_capacity_001/"
            "ARCHITECTURE_CHANGE_SPEC_v0.2_ANALYTIC_DECOMPOSE_INIT.md"
        ),
    }


__all__ = [
    "AnalyticDecomposeError",
    "DEFAULT_RIDGE_LAMBDA",
    "D_MODEL",
    "DecomposeParameters",
    "REGISTERED_PARAMETER_SHAPES",
    "SCHEMA_VERSION",
    "decompose_from_free_readout",
    "free_readout_scores",
    "frozen_readout_scores",
    "identity_parameters",
    "identity_residual",
    "inverse_diagnostics",
    "matmul",
    "matvec",
    "parameters_for_map",
    "realisation_agreement",
    "realisation_score_residual",
    "ridge_weights",
    "scope_declaration",
    "shuffled_label_control",
    "solve",
    "tanh_vector",
    "transpose",
]
