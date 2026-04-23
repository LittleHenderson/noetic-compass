"""Validation pipeline for CAS synthetic examples.

Three stages:
  1. schema_validator  — data_format.md JSONL schema conformance
  2. rust_validator    — Rust engine batch APIs for Rule 4 / Omega / yield
  3. composite_validator — semantic coherence checks (register labels match
     registers in cas_expression, omega names admitted, prereq state ids in range, ...)
"""

from .schema_validator import (
    SchemaValidator,
    SchemaValidationError,
    validate_example_schema,
)
from .rust_validator import RustValidator, RustValidatorUnavailable
from .composite_validator import CompositeValidator, CompositeValidationReport

__all__ = [
    "SchemaValidator",
    "SchemaValidationError",
    "validate_example_schema",
    "RustValidator",
    "RustValidatorUnavailable",
    "CompositeValidator",
    "CompositeValidationReport",
]
