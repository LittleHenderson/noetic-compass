"""A small, explicitly typed category of finite sets and total functions.

The module does not assign CAS or Noetic meaning to an arrow.  It supplies a
reference semantic layer in which an arrow always carries an exact source and
target and composition is rejected when those types do not match.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass, field
import hashlib
from math import factorial
from typing import Hashable


class ValidationError(ValueError):
    """Raised when a finite object, arrow, or path is malformed."""


class CompositionTypeError(TypeError):
    """Raised when categorical source and target objects do not match."""


def _ordered_tuple(values: object, field: str) -> tuple[object, ...]:
    """Reject containers whose iteration order is not part of their contract."""

    if (
        isinstance(values, (str, bytes, bytearray, Mapping, Set))
        or not isinstance(values, Sequence)
    ):
        raise ValidationError(
            f"{field} must be an ordered sequence; sets, mappings, and "
            "one-shot iterables are not accepted"
        )
    return tuple(values)


def _compact_integer_label(value: int) -> str:
    """Render a nonsemantic integer label without Python's decimal-size limit."""

    if value.bit_length() <= 256:
        return str(value)
    encoded = value.to_bytes((value.bit_length() + 7) // 8, "big")
    digest = hashlib.sha256(encoded).hexdigest()[:16]
    return f"bits={value.bit_length()},sha256={digest}"


@dataclass(frozen=True, slots=True)
class FiniteObject:
    """A named finite carrier.

    Object equality includes both ``name`` and ``elements``.  Consequently two
    carriers with the same elements but different declared object identities
    are not silently interchangeable.
    """

    name: str
    elements: tuple[Hashable, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("a finite object needs a non-blank name")
        elements = _ordered_tuple(self.elements, "finite-object elements")
        try:
            unique = set(elements)
        except TypeError as exc:
            raise ValidationError("finite-object elements must be hashable") from exc
        if len(unique) != len(elements):
            raise ValidationError("finite-object elements must be pairwise distinct")
        object.__setattr__(self, "elements", elements)

    def index(self, element: Hashable) -> int:
        """Return the standard-basis index of ``element``."""

        try:
            return self.elements.index(element)
        except ValueError as exc:
            raise ValidationError(
                f"{element!r} is not an element of object {self.name!r}"
            ) from exc

    def __len__(self) -> int:
        return len(self.elements)


@dataclass(frozen=True, slots=True)
class FiniteArrow:
    """A total function between two declared finite objects.

    ``mapping[i]`` is the target-basis index of the image of source element
    ``i``.  Arrow equality is extensional: the presentation name is excluded
    from equality and hashing.
    """

    name: str = field(compare=False)
    source: FiniteObject
    target: FiniteObject
    mapping: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError("an arrow needs a non-blank presentation name")
        if not isinstance(self.source, FiniteObject) or not isinstance(
            self.target, FiniteObject
        ):
            raise ValidationError("an arrow source and target must be FiniteObject values")
        mapping = _ordered_tuple(self.mapping, "arrow mapping")
        if len(mapping) != len(self.source):
            raise ValidationError(
                f"arrow {self.name!r} needs one image for each of the "
                f"{len(self.source)} source elements"
            )
        for image_index in mapping:
            if isinstance(image_index, bool) or not isinstance(image_index, int):
                raise ValidationError("arrow image indices must be integers")
            if not 0 <= image_index < len(self.target):
                raise ValidationError(
                    f"arrow {self.name!r} has target index {image_index}, outside "
                    f"object {self.target.name!r}"
                )
        object.__setattr__(self, "mapping", mapping)

    def __call__(self, element: Hashable) -> Hashable:
        source_index = self.source.index(element)
        return self.target.elements[self.mapping[source_index]]

    @property
    def is_endomap(self) -> bool:
        return self.source == self.target

    @property
    def denotation_key(
        self,
    ) -> tuple[FiniteObject, FiniteObject, tuple[int, ...]]:
        """A name-independent key for the denoted finite function."""

        return (self.source, self.target, self.mapping)


def identity(obj: FiniteObject, *, name: str | None = None) -> FiniteArrow:
    """Construct the identity arrow on ``obj``."""

    return FiniteArrow(
        name=name or f"id[{obj.name}]",
        source=obj,
        target=obj,
        mapping=tuple(range(len(obj))),
    )


def compose(
    after: FiniteArrow,
    before: FiniteArrow,
    *,
    name: str | None = None,
) -> FiniteArrow:
    """Return ``after ∘ before`` after checking the middle object exactly."""

    if before.target != after.source:
        raise CompositionTypeError(
            "cannot compose "
            f"{before.name}:{before.source.name}->{before.target.name} then "
            f"{after.name}:{after.source.name}->{after.target.name}"
        )
    return FiniteArrow(
        name=name or f"({after.name} o {before.name})",
        source=before.source,
        target=after.target,
        mapping=tuple(after.mapping[index] for index in before.mapping),
    )


@dataclass(frozen=True, slots=True)
class Endomap:
    """An arrow certified to lie in one endomorphism monoid ``End(X)``."""

    arrow: FiniteArrow

    def __post_init__(self) -> None:
        if not isinstance(self.arrow, FiniteArrow):
            raise ValidationError("an endomap must wrap a FiniteArrow")
        if not self.arrow.is_endomap:
            raise CompositionTypeError(
                f"{self.arrow.name!r} has type {self.arrow.source.name}->"
                f"{self.arrow.target.name}, so it is not an endomap"
            )

    @property
    def carrier(self) -> FiniteObject:
        return self.arrow.source

    def power(self, exponent: int) -> Endomap:
        """Take a monoid power of this one fixed endomap.

        This operation is deliberately absent from :class:`SemigroupoidPath`.
        It does not license powers of heterogeneous or time-varying paths.
        """

        if isinstance(exponent, bool) or not isinstance(exponent, int) or exponent < 0:
            raise ValidationError("an endomap exponent must be a non-negative integer")
        result = identity(self.carrier, name="power-accumulator")
        base = self.arrow
        remaining = exponent
        while remaining:
            if remaining & 1:
                result = compose(base, result, name="power-accumulator")
            remaining >>= 1
            if remaining:
                base = compose(base, base, name="power-square")
        return Endomap(
            FiniteArrow(
                name=f"{self.arrow.name}^({_compact_integer_label(exponent)})",
                source=self.carrier,
                target=self.carrier,
                mapping=result.mapping,
            )
        )

    def factorial_idempotent_power(self) -> Endomap:
        """Return ``f^(|X|!)``, the standard finite-map idempotent power."""

        return self.power(factorial(len(self.carrier)))

    def is_idempotent(self) -> bool:
        return compose(self.arrow, self.arrow) == self.arrow


@dataclass(frozen=True, slots=True)
class SemigroupoidPath:
    """A nonempty, typed path whose arrows need not share one carrier."""

    arrows: tuple[FiniteArrow, ...]

    def __post_init__(self) -> None:
        arrows = _ordered_tuple(self.arrows, "semigroupoid path arrows")
        if not arrows:
            raise ValidationError("a semigroupoid path is nonempty")
        if any(not isinstance(arrow, FiniteArrow) for arrow in arrows):
            raise ValidationError("every semigroupoid path member must be a FiniteArrow")
        for before, after in zip(arrows, arrows[1:]):
            if before.target != after.source:
                raise CompositionTypeError(
                    "ill-typed path segment: "
                    f"{before.name}:{before.source.name}->{before.target.name} then "
                    f"{after.name}:{after.source.name}->{after.target.name}"
                )
        object.__setattr__(self, "arrows", arrows)

    @classmethod
    def from_iterable(cls, arrows: Sequence[FiniteArrow]) -> SemigroupoidPath:
        """Build from an explicitly ordered, replayable sequence."""

        return cls(arrows)

    @property
    def source(self) -> FiniteObject:
        return self.arrows[0].source

    @property
    def target(self) -> FiniteObject:
        return self.arrows[-1].target

    def composite(self) -> FiniteArrow:
        result = self.arrows[0]
        for step, arrow in enumerate(self.arrows[1:], start=2):
            result = compose(arrow, result, name=f"path-composite[{step}]")
        return FiniteArrow(
            name=f"path-composite[{len(self.arrows)}]",
            source=result.source,
            target=result.target,
            mapping=result.mapping,
        )

    def append(self, arrow: FiniteArrow) -> SemigroupoidPath:
        return SemigroupoidPath(self.arrows + (arrow,))
