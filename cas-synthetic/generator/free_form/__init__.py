"""Phase 3 SDG: native free-form English generation from CAS expressions.

Public surface:

    generate_free_form(cas_expression, *, seed=None, style="neutral") -> str
    expand_record(record, *, k, seed) -> list[dict]
    parse_cas_expression(expr) -> StructuralPlan

The lexicon, parser, and surface generator live in three sibling
modules. See ``docs/working/phase3_free_form_spec_2026_05_04.md`` for
the canonical spec, motivation, anti-drift verification, and
sequencing relative to Lever 3 + demographic-tonal expansion.
"""

from __future__ import annotations

from .colloquialism_lexicon import (
    DOMAIN_FLAVOR,
    DOMAIN_NAMES,
    DRIVE_FLAVOR,
    DRIVE_NAMES,
    NOETIC_LEXICON,
    NOETIC_NAMES,
    REGISTER_FRAMES,
    REGISTER_NAMES,
)
from .compositional_rules import (
    SimpleState,
    StructuralPlan,
    parse_cas_expression,
)
from .surface_generator import (
    SACRED_FIELDS,
    expand_record,
    generate_free_form,
)

__all__ = [
    "DOMAIN_FLAVOR",
    "DOMAIN_NAMES",
    "DRIVE_FLAVOR",
    "DRIVE_NAMES",
    "NOETIC_LEXICON",
    "NOETIC_NAMES",
    "REGISTER_FRAMES",
    "REGISTER_NAMES",
    "SimpleState",
    "StructuralPlan",
    "parse_cas_expression",
    "SACRED_FIELDS",
    "expand_record",
    "generate_free_form",
]
