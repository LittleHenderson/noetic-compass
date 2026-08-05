"""Conservative executable kernel for the Gate 1 typed TKS v8 prototype.

This package is intentionally independent of the production CAS notation
compiler.  It models only finite objects and total finite-function arrows,
which is enough to make the source/target discipline and the corrected
deterministic-lift result executable.
"""

from .category import (
    CompositionTypeError,
    Endomap,
    FiniteArrow,
    FiniteObject,
    SemigroupoidPath,
    ValidationError,
    compose,
    identity,
)
from .deterministic_lift import DeterministicLift
from .normal_forms import (
    ClosureLimitExceeded,
    Generator,
    NormalFormCatalog,
    TypedWord,
    UnreachableDenotationError,
)

__all__ = [
    "ClosureLimitExceeded",
    "CompositionTypeError",
    "DeterministicLift",
    "Endomap",
    "FiniteArrow",
    "FiniteObject",
    "Generator",
    "NormalFormCatalog",
    "SemigroupoidPath",
    "TypedWord",
    "UnreachableDenotationError",
    "ValidationError",
    "compose",
    "identity",
]
