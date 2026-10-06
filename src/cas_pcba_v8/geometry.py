"""Exact mixed-simplex validation and quarantined projector research profiles."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import math

from .arithmetic import (
    DECIMAL_CONTEXT_SHA256,
    deterministic_decimal,
    exact_decimal_add,
    exact_decimal_sum,
)
from .boundary import (
    ResearchBoundary,
    fixed_research_boundary,
    require_research_boundary,
)
from .integrity import require_safe_reference, require_sha256, sha256_payload
from .types import CANONICAL_ND_CELLS, CANONICAL_ND_LABELS, NdCell


MIXED_SIMPLEX_PROFILE = "cas-pcba-v8.mixed-simplex.v1"
PROJECTOR_VALIDATION_PROFILE = "cas-pcba-v8.projector-validation.v1"
MAX_PROJECTOR_TOLERANCE = Decimal("1E-12")
FISHER_RAO_PROFILE = "cas-pcba-v8.binary64-fisher-rao-pseudometric.v1"


class GeometryError(ValueError):
    """Raised when a geometry profile violates its declared type."""


def _finite_decimal(value: object) -> bool:
    return type(value) is Decimal and value.is_finite()


def _decimal_payload(value: Decimal) -> dict[str, str]:
    return {"type": "decimal", "value": str(value)}


@dataclass(frozen=True, slots=True)
class MixedSimplexAddress:
    """A point of the open 39-simplex in canonical P0..O9 cell order."""

    weights: tuple[Decimal, ...]
    cells: tuple[NdCell, ...] = CANONICAL_ND_CELLS
    profile_kind: str = "CANONICAL_MIXED_SIMPLEX_BASELINE"

    @deterministic_decimal
    def __post_init__(self) -> None:
        if type(self) is not MixedSimplexAddress:
            raise GeometryError("mixed-simplex subclasses are not accepted")
        object.__setattr__(self, "weights", tuple(self.weights))
        object.__setattr__(self, "cells", tuple(self.cells))
        if (
            type(self.profile_kind) is not str
            or self.profile_kind != "CANONICAL_MIXED_SIMPLEX_BASELINE"
        ):
            raise GeometryError("mixed-simplex profile_kind is fixed by its type")
        if not _canonical_cells(self.cells):
            raise GeometryError("mixed-simplex cells must use canonical P0..O9 order")
        if len(self.weights) != 40:
            raise GeometryError("a PCBA mixed-simplex address requires exactly 40 weights")
        if any(not _finite_decimal(value) or value <= 0 for value in self.weights):
            raise GeometryError(
                "every mixed-simplex weight must be finite and strictly positive"
            )
        if exact_decimal_sum(self.weights) != Decimal("1"):
            raise GeometryError("mixed-simplex weights must sum exactly to Decimal('1')")

    @classmethod
    @deterministic_decimal
    def from_positive_weights(
        cls,
        weights: tuple[Decimal, ...],
    ) -> "MixedSimplexAddress":
        if cls is not MixedSimplexAddress:
            raise GeometryError("mixed-simplex subclasses are not accepted")
        values = tuple(weights)
        if len(values) != 40:
            raise GeometryError("a PCBA mixed-simplex address requires exactly 40 weights")
        if any(not _finite_decimal(value) or value <= 0 for value in values):
            raise GeometryError("normalization requires finite strictly positive weights")
        total = exact_decimal_sum(values)
        normalized = [value / total for value in values]
        residual = exact_decimal_sum(
            (Decimal("1"), exact_decimal_sum(normalized).copy_negate())
        )
        anchor = max(range(len(values)), key=lambda index: (values[index], -index))
        normalized[anchor] = exact_decimal_add(normalized[anchor], residual)
        if normalized[anchor] <= 0:
            raise GeometryError("decimal normalization exhausted a positive coordinate")
        return cls(tuple(normalized))

    def identity_payload(self) -> dict[str, object]:
        self._revalidate()
        return {
            "profile": MIXED_SIMPLEX_PROFILE,
            "profile_kind": self.profile_kind,
            "decimal_context_sha256": DECIMAL_CONTEXT_SHA256,
            "cells": [cell.label for cell in self.cells],
            "weights": [_decimal_payload(value) for value in self.weights],
        }

    @property
    def profile_sha256(self) -> str:
        return sha256_payload(self.identity_payload())

    def _revalidate(self) -> None:
        if type(self) is not MixedSimplexAddress:
            raise GeometryError("mixed-simplex values must use the exact type")
        if (
            type(self.profile_kind) is not str
            or self.profile_kind != "CANONICAL_MIXED_SIMPLEX_BASELINE"
        ):
            raise GeometryError("mixed-simplex profile discriminator was mutated")
        if (
            type(self.cells) is not tuple
            or type(self.weights) is not tuple
            or not _canonical_cells(self.cells)
            or len(self.weights) != 40
        ):
            raise GeometryError("mixed-simplex structure was mutated")
        if any(not _finite_decimal(value) or value <= 0 for value in self.weights):
            raise GeometryError("mixed-simplex weights were mutated")
        if exact_decimal_sum(self.weights) != Decimal("1"):
            raise GeometryError("mixed-simplex exact sum was mutated")

    def weight(self, cell: NdCell) -> Decimal:
        self._revalidate()
        if type(cell) is not NdCell:
            raise GeometryError("cell lookup requires an exact NdCell")
        cell.revalidate()
        try:
            index = tuple(item.label for item in self.cells).index(cell.label)
            return self.weights[index]
        except ValueError as exc:
            raise GeometryError(f"cell {cell!r} is outside the canonical address") from exc


def _canonical_cells(cells: tuple[NdCell, ...]) -> bool:
    if len(cells) != len(CANONICAL_ND_CELLS):
        return False
    if any(type(cell) is not NdCell for cell in cells):
        return False
    try:
        labels = tuple(cell.label for cell in cells)
    except (TypeError, ValueError):
        return False
    return labels == CANONICAL_ND_LABELS


@deterministic_decimal
def fisher_rao_distance(
    left: MixedSimplexAddress,
    right: MixedSimplexAddress,
) -> Decimal:
    """Return a binary64 Fisher--Rao *pseudodistance* baseline.

    Exact Decimal profiles are converted to binary64 before ``sqrt``/``acos``.
    Distinct profiles below binary64 resolution can therefore have distance
    zero.  This is not an exact metric, proof of identity, or projector bridge.
    """

    if type(left) is not MixedSimplexAddress or type(right) is not MixedSimplexAddress:
        raise TypeError("Fisher--Rao pseudodistance accepts mixed-simplex values only")
    left._revalidate()
    right._revalidate()
    coefficient = math.fsum(
        math.sqrt(float(a) * float(b)) for a, b in zip(left.weights, right.weights)
    )
    coefficient = min(1.0, max(0.0, coefficient))
    distance = 2.0 * math.acos(coefficient)
    if abs(distance) < 1e-15:
        distance = 0.0
    return Decimal(str(distance))


fisher_rao_distance.profile = FISHER_RAO_PROFILE  # type: ignore[attr-defined]
fisher_rao_distance.is_exact_metric = False  # type: ignore[attr-defined]


@dataclass(frozen=True, slots=True)
class ProjectorProfile:
    """Optional orthogonal-projector research profile, never a PCBA address."""

    profile_id: str
    matrix: tuple[tuple[Decimal, ...], ...]
    rank: int
    tolerance: Decimal = Decimal("1E-12")
    basis_id: str = "pcba8.unspecified-basis.v1"
    source_id: str = "pcba8.unspecified-source.v1"
    validation_profile: str = PROJECTOR_VALIDATION_PROFILE
    profile_kind: str = "FRONTIER_PROJECTOR_PROFILE"
    canonical_pcba_address: bool = False
    boundary: ResearchBoundary = field(default_factory=fixed_research_boundary)
    symmetry_residual: Decimal = field(init=False)
    idempotence_residual: Decimal = field(init=False)
    trace_residual: Decimal = field(init=False)
    matrix_sha256: str = field(init=False)
    profile_sha256: str = field(init=False)

    @deterministic_decimal
    def __post_init__(self) -> None:
        if type(self) is not ProjectorProfile:
            raise GeometryError("projector-profile subclasses are not accepted")
        require_research_boundary(self.boundary)
        require_safe_reference(self.profile_id, "ProjectorProfile.profile_id")
        require_safe_reference(self.basis_id, "ProjectorProfile.basis_id")
        require_safe_reference(self.source_id, "ProjectorProfile.source_id")
        if (
            type(self.validation_profile) is not str
            or self.validation_profile != PROJECTOR_VALIDATION_PROFILE
        ):
            raise GeometryError("projector validation profile is fixed and versioned")
        if type(self.profile_kind) is not str or self.profile_kind != "FRONTIER_PROJECTOR_PROFILE":
            raise GeometryError("projector profile_kind is fixed by its type")
        if self.canonical_pcba_address is not False:
            raise GeometryError("a projector profile is never a canonical PCBA address")
        matrix = tuple(tuple(row) for row in self.matrix)
        object.__setattr__(self, "matrix", matrix)
        dimension = len(matrix)
        if dimension == 0 or any(len(row) != dimension for row in matrix):
            raise GeometryError("projector matrix must be nonempty and square")
        if type(self.rank) is not int:
            raise GeometryError("projector rank must be an integer")
        if not 0 < self.rank <= dimension:
            raise GeometryError("projector rank must lie in [1, dimension]")
        if (
            not _finite_decimal(self.tolerance)
            or self.tolerance < 0
            or self.tolerance > MAX_PROJECTOR_TOLERANCE
        ):
            raise GeometryError(
                "projector tolerance must be finite and no greater than 1E-12"
            )
        if any(not _finite_decimal(value) for row in matrix for value in row):
            raise GeometryError("projector entries must be finite Decimal values")

        symmetry, idempotence, trace_residual = _projector_residuals(
            matrix,
            self.rank,
        )
        object.__setattr__(self, "symmetry_residual", symmetry)
        object.__setattr__(self, "idempotence_residual", idempotence)
        object.__setattr__(self, "trace_residual", trace_residual)
        if symmetry > self.tolerance:
            raise GeometryError("projector matrix must be self-adjoint")
        if idempotence > self.tolerance:
            raise GeometryError("projector matrix must be idempotent")
        if trace_residual > self.tolerance:
            raise GeometryError("projector trace must agree with the declared rank")

        matrix_sha = sha256_payload(self._matrix_payload())
        object.__setattr__(self, "matrix_sha256", matrix_sha)
        profile_sha = sha256_payload(self._identity_payload(matrix_sha))
        object.__setattr__(self, "profile_sha256", profile_sha)

    def _matrix_payload(self) -> dict[str, object]:
        return {
            "profile": "cas-pcba-v8.projector-matrix.v1",
            "matrix": [
                [_decimal_payload(value) for value in row]
                for row in self.matrix
            ],
        }

    def _identity_payload(self, matrix_sha256: str) -> dict[str, object]:
        return {
            "profile": PROJECTOR_VALIDATION_PROFILE,
            "profile_id": self.profile_id,
            "profile_kind": self.profile_kind,
            "canonical_pcba_address": self.canonical_pcba_address,
            "basis_id": self.basis_id,
            "source_id": self.source_id,
            "dimension": len(self.matrix),
            "rank": self.rank,
            "tolerance": _decimal_payload(self.tolerance),
            "symmetry_residual": _decimal_payload(self.symmetry_residual),
            "idempotence_residual": _decimal_payload(self.idempotence_residual),
            "trace_residual": _decimal_payload(self.trace_residual),
            "matrix_sha256": matrix_sha256,
            "decimal_context_sha256": DECIMAL_CONTEXT_SHA256,
            "boundary": self.boundary.to_dict(),
        }

    def identity_payload(self) -> dict[str, object]:
        self.revalidate()
        return self._identity_payload(self.matrix_sha256)

    @deterministic_decimal
    def revalidate(self) -> None:
        if type(self) is not ProjectorProfile:
            raise GeometryError("projector profiles must use the exact type")
        require_research_boundary(self.boundary)
        require_safe_reference(self.profile_id, "ProjectorProfile.profile_id")
        require_safe_reference(self.basis_id, "ProjectorProfile.basis_id")
        require_safe_reference(self.source_id, "ProjectorProfile.source_id")
        if (
            type(self.validation_profile) is not str
            or self.validation_profile != PROJECTOR_VALIDATION_PROFILE
            or type(self.profile_kind) is not str
            or self.profile_kind != "FRONTIER_PROJECTOR_PROFILE"
            or self.canonical_pcba_address is not False
        ):
            raise GeometryError("projector type discriminator was mutated")
        dimension = len(self.matrix)
        if (
            type(self.matrix) is not tuple
            or any(type(row) is not tuple for row in self.matrix)
            or dimension == 0
            or any(len(row) != dimension for row in self.matrix)
        ):
            raise GeometryError("projector matrix structure was mutated")
        if (
            type(self.rank) is not int
            or not 0 < self.rank <= dimension
        ):
            raise GeometryError("projector rank was mutated")
        if (
            not _finite_decimal(self.tolerance)
            or self.tolerance < 0
            or self.tolerance > MAX_PROJECTOR_TOLERANCE
        ):
            raise GeometryError("projector tolerance exceeded its versioned bound")
        if any(not _finite_decimal(value) for row in self.matrix for value in row):
            raise GeometryError("projector matrix values were mutated")
        actual_residuals = _projector_residuals(self.matrix, self.rank)
        recorded_residuals = (
            self.symmetry_residual,
            self.idempotence_residual,
            self.trace_residual,
        )
        if any(
            not _finite_decimal(residual) or residual < 0
            for residual in recorded_residuals
        ):
            raise GeometryError("projector validation residuals were mutated")
        if actual_residuals != recorded_residuals:
            raise GeometryError("projector validation residuals are stale or tampered")
        if any(residual > self.tolerance for residual in actual_residuals):
            raise GeometryError("projector no longer satisfies its validation tolerance")
        actual_matrix_sha = sha256_payload(self._matrix_payload())
        require_sha256(self.matrix_sha256, "ProjectorProfile.matrix_sha256")
        require_sha256(self.profile_sha256, "ProjectorProfile.profile_sha256")
        if actual_matrix_sha != self.matrix_sha256:
            raise GeometryError("projector matrix identity is stale or tampered")
        actual_profile_sha = sha256_payload(self._identity_payload(actual_matrix_sha))
        if actual_profile_sha != self.profile_sha256:
            raise GeometryError("projector profile identity is stale or tampered")

    @property
    def dimension(self) -> int:
        self.revalidate()
        return len(self.matrix)


def _matrix_multiply(
    left: tuple[tuple[Decimal, ...], ...],
    right: tuple[tuple[Decimal, ...], ...],
) -> tuple[tuple[Decimal, ...], ...]:
    dimension = len(left)
    return tuple(
        tuple(
            exact_decimal_sum(
                [left[i][k] * right[k][j] for k in range(dimension)]
            )
            for j in range(dimension)
        )
        for i in range(dimension)
    )


def _projector_residuals(
    matrix: tuple[tuple[Decimal, ...], ...],
    rank: int,
) -> tuple[Decimal, Decimal, Decimal]:
    dimension = len(matrix)
    symmetry = max(
        (
            abs(matrix[i][j] - matrix[j][i])
            for i in range(dimension)
            for j in range(dimension)
        ),
        default=Decimal("0"),
    )
    square = _matrix_multiply(matrix, matrix)
    idempotence = max(
        (
            abs(square[i][j] - matrix[i][j])
            for i in range(dimension)
            for j in range(dimension)
        ),
        default=Decimal("0"),
    )
    trace = exact_decimal_sum([matrix[i][i] for i in range(dimension)])
    trace_residual = abs(trace - Decimal(rank))
    return symmetry, idempotence, trace_residual


@deterministic_decimal
def projector_overlap(left: ProjectorProfile, right: ProjectorProfile) -> Decimal:
    """Return ``tr(PQ)/rank`` for validated compatible projector profiles."""

    if type(left) is not ProjectorProfile or type(right) is not ProjectorProfile:
        raise TypeError("projector overlap accepts ProjectorProfile values only")
    left.revalidate()
    right.revalidate()
    if len(left.matrix) != len(right.matrix) or left.rank != right.rank:
        raise GeometryError("projector profiles require common dimension and rank")
    if left.basis_id != right.basis_id:
        raise GeometryError("projector overlap requires an identical declared basis")
    product = _matrix_multiply(left.matrix, right.matrix)
    trace = exact_decimal_sum(
        [product[i][i] for i in range(len(left.matrix))]
    )
    return trace / Decimal(left.rank)
