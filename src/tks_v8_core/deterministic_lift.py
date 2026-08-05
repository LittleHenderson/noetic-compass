"""Standard-basis linear lift of a typed finite function.

For ``f:X->Y``, the lift ``A_f`` sends ``e_x`` to ``e_{f(x)}``.  The exact
operator norm is ``sqrt(max_y |f^{-1}(y)|)`` (zero for an empty domain).
The implementation exposes exact integer-valued squared data wherever
possible; only :attr:`operator_norm` converts to floating point.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass
from math import sqrt
from numbers import Complex

from .category import FiniteArrow, ValidationError


@dataclass(frozen=True, slots=True)
class DeterministicLift:
    arrow: FiniteArrow

    def __post_init__(self) -> None:
        if not isinstance(self.arrow, FiniteArrow):
            raise ValidationError("a deterministic lift must wrap a FiniteArrow")

    def matrix(self) -> tuple[tuple[int, ...], ...]:
        """Return the ``|Y| x |X|`` zero-one matrix of ``A_f``."""

        return tuple(
            tuple(
                int(self.arrow.mapping[column] == row)
                for column in range(len(self.arrow.source))
            )
            for row in range(len(self.arrow.target))
        )

    def apply(self, vector: Sequence[Complex]) -> tuple[Complex, ...]:
        """Apply ``A_f`` to source coordinates."""

        if isinstance(vector, (str, bytes, bytearray, Mapping, Set)) or not isinstance(
            vector, Sequence
        ):
            raise ValidationError("source coordinates must be an ordered sequence")
        if len(vector) != len(self.arrow.source):
            raise ValidationError(
                f"expected {len(self.arrow.source)} source coordinates, got {len(vector)}"
            )
        output: list[Complex] = [0] * len(self.arrow.target)
        for source_index, value in enumerate(vector):
            output[self.arrow.mapping[source_index]] += value
        return tuple(output)

    def adjoint_apply(self, vector: Sequence[Complex]) -> tuple[Complex, ...]:
        """Apply the conjugate transpose ``A_f*`` to target coordinates."""

        if isinstance(vector, (str, bytes, bytearray, Mapping, Set)) or not isinstance(
            vector, Sequence
        ):
            raise ValidationError("target coordinates must be an ordered sequence")
        if len(vector) != len(self.arrow.target):
            raise ValidationError(
                f"expected {len(self.arrow.target)} target coordinates, got {len(vector)}"
            )
        return tuple(vector[target_index] for target_index in self.arrow.mapping)

    @property
    def fiber_sizes(self) -> tuple[int, ...]:
        sizes = [0] * len(self.arrow.target)
        for image_index in self.arrow.mapping:
            sizes[image_index] += 1
        return tuple(sizes)

    @property
    def max_fiber_size(self) -> int:
        return max(self.fiber_sizes, default=0)

    @property
    def operator_norm_squared(self) -> int:
        """The exact value ``||A_f||^2 = max_y |f^{-1}(y)|``."""

        return self.max_fiber_size

    @property
    def operator_norm(self) -> float:
        return sqrt(self.operator_norm_squared)

    def input_gram_matrix(self) -> tuple[tuple[int, ...], ...]:
        """Return ``A_f* A_f``, the input-collision Gram matrix."""

        return tuple(
            tuple(int(left_image == right_image) for right_image in self.arrow.mapping)
            for left_image in self.arrow.mapping
        )

    def output_gram_matrix(self) -> tuple[tuple[int, ...], ...]:
        """Return ``A_f A_f*``, diagonal with the output-fiber sizes."""

        sizes = self.fiber_sizes
        return tuple(
            tuple(sizes[row] if row == column else 0 for column in range(len(sizes)))
            for row in range(len(sizes))
        )

    def output_support_projector(self) -> tuple[tuple[int, ...], ...]:
        """Return the orthogonal projector onto ``im(A_f)`` in the codomain."""

        support = tuple(int(size > 0) for size in self.fiber_sizes)
        return tuple(
            tuple(support[row] if row == column else 0 for column in range(len(support)))
            for row in range(len(support))
        )

    @property
    def trace_input_gram(self) -> int:
        return len(self.arrow.source)

    @property
    def rank(self) -> int:
        return sum(size > 0 for size in self.fiber_sizes)

    @property
    def is_injective(self) -> bool:
        return all(size <= 1 for size in self.fiber_sizes)

    @property
    def is_isometry(self) -> bool:
        """Whether ``A_f* A_f`` is the identity (equivalently, ``f`` injective)."""

        return self.is_injective

    @property
    def is_partial_isometry(self) -> bool:
        """For a total standard lift, equivalently whether ``f`` is injective."""

        return self.is_injective

    @property
    def is_idempotent(self) -> bool:
        if not self.arrow.is_endomap:
            return False
        return all(self.arrow.mapping[image] == image for image in self.arrow.mapping)

    @property
    def is_orthogonal_projector(self) -> bool:
        """Whether this typed lift itself is an orthogonal projector.

        A total deterministic lift on one declared carrier is an orthogonal
        projector only for the identity map.  Non-endomaps are not operators
        on one Hilbert space and therefore return ``False``.
        """

        return self.arrow.is_endomap and self.arrow.mapping == tuple(
            range(len(self.arrow.source))
        )
