"""Rotating-axis three-instance CAS dialectic orchestration scaffolding.

This package implements the plumbing for the multi-instance CAS dialog
architecture: two CAS-Native instances run an internal dialog rotating
through CAS axes (Noetic, Domain, Drive, Register involution pairs), each
rotation produces a candidate `(A x B) = Omega_axis` attractor, and a
third (or fourth) instance scores attractors and selects the load-bearing
one for user-facing output.

This is SCAFFOLDING. Real axis-priming via logits intervention,
compiler-based admissibility scoring, and a learned query->rotation
classifier are scheduled for the post-Lever-3 prototype. The interface is
defined here so they can drop in without restructuring.

Public API:
    AxisPriming      -- per-rotation hint envelope (Noetic/Domain/Drive/Register)
    CASInstance      -- predictor wrapper accepting AxisPriming
    Attractor        -- candidate Omega from an (A x B) integration
    AttractorScore   -- substance/relevance/admissibility/balance/composite
    DialecticOrchestrator -- top-level entry point
    DialecticResponse     -- full trace output

See ``README.md`` for architecture rationale and Lever 3 wiring plan.
"""

from __future__ import annotations

from .attractor import Attractor, AttractorScore, score_attractor
from .instance import AxisPriming, CASInstance
from .orchestrator import DialecticOrchestrator, DialecticResponse
from .rotator import (
    ROTATION_DOMAIN,
    ROTATION_DRIVE_INVERSION,
    ROTATION_NOETIC_INVOLUTION,
    ROTATION_REGISTER_INVERSION,
    select_rotations,
)
from .selector import select_top_attractors

__all__ = [
    "Attractor",
    "AttractorScore",
    "AxisPriming",
    "CASInstance",
    "DialecticOrchestrator",
    "DialecticResponse",
    "ROTATION_DOMAIN",
    "ROTATION_DRIVE_INVERSION",
    "ROTATION_NOETIC_INVOLUTION",
    "ROTATION_REGISTER_INVERSION",
    "score_attractor",
    "select_rotations",
    "select_top_attractors",
]
