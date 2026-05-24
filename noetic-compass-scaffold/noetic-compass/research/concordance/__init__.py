"""Compass <-> Atlas concordance harness (M1 scaffold).

Research surface, not production. Lives outside `cas-engine/` and `api/`.

Public API:
    Scenario, CompassResult, AtlasResult, ConcordanceReport, SetReport
    call_compass, call_atlas         (M1: stubs)
    compare, run_set                  (M1: real)
    load_scenarios                    (M1: real, with fixture fallback)

See `docs/working/compass_atlas_concordance_harness_2026_05_24.md` for the
design doc.
"""

from .harness import (
    AtlasResult,
    CompassResult,
    ConcordanceReport,
    Scenario,
    SetReport,
    call_atlas,
    call_compass,
    compare,
    load_scenarios,
    run_set,
)

__all__ = [
    "AtlasResult",
    "CompassResult",
    "ConcordanceReport",
    "Scenario",
    "SetReport",
    "call_atlas",
    "call_compass",
    "compare",
    "load_scenarios",
    "run_set",
]
