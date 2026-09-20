"""Small training-fit mode for the teaching campaign's binding task.

Re-exports the mode entry points. Importing this package never imports a real
tensor library; the real torch module is only reached inside ``mode.import_torch``
and the real launch path.
"""

from .mode import (
    BINDING_SLOTS,
    CASES_PER_SLOT,
    DEFAULT_MAX_OPTIMIZER_STEPS,
    DEFAULT_MAX_WALL_SECONDS,
    FAMILIES,
    SCHEMA,
    TOTAL_CASES,
    BOUNDARY,
    BindingFitLearner,
    build_balanced_cases,
    build_records,
    import_torch,
    launch,
    run_fit,
    short_public,
    validate_balanced_cases,
    validate_budget,
    validate_records,
)

__all__ = [
    "BINDING_SLOTS",
    "CASES_PER_SLOT",
    "DEFAULT_MAX_OPTIMIZER_STEPS",
    "DEFAULT_MAX_WALL_SECONDS",
    "FAMILIES",
    "SCHEMA",
    "TOTAL_CASES",
    "BOUNDARY",
    "BindingFitLearner",
    "build_balanced_cases",
    "build_records",
    "import_torch",
    "launch",
    "run_fit",
    "short_public",
    "validate_balanced_cases",
    "validate_budget",
    "validate_records",
]
