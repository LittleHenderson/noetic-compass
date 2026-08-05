"""Finite-context reflector composition for the Noetic Topos 2.0 candidate.

This package is an isolated Ring-4 research artifact.  It proves and checks a
claim only for Set-valued presheaves on the sixteen-object powerset context
category.  It does not establish the corresponding product-site claim.
"""

from .finite_reflectors import (
    ACBE,
    ATOMIC,
    RPM,
    ALL_ATOMS,
    ALL_CONTEXTS,
    FinitePresheaf,
    ReflectedPresheaf,
    atomic_to_composite_section,
    composite_to_atomic_section,
    generating_family,
    generated_topology,
    normalized_support,
    run_certificate,
    symbolic_certificate,
    validate_finite_presheaf,
    verify_composition_for,
)

__all__ = [
    "ACBE",
    "ATOMIC",
    "RPM",
    "ALL_ATOMS",
    "ALL_CONTEXTS",
    "FinitePresheaf",
    "ReflectedPresheaf",
    "atomic_to_composite_section",
    "composite_to_atomic_section",
    "generating_family",
    "generated_topology",
    "normalized_support",
    "run_certificate",
    "symbolic_certificate",
    "validate_finite_presheaf",
    "verify_composition_for",
]
