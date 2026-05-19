"""Wrap Pipeline adapter for the Stage 20 Generation Readiness Gate.

The Stage 20 gate (`cas-native/model/generation_readiness_gate.py`) lives in
the hyphenated ``cas-native/`` tree so it can be imported with the same
package name the CAS-Native test suite uses (``cas_native.model``). This
adapter performs the path-aliased import once at module load time and
exposes a small synchronous helper plus the canonical ALLOW/CAVEAT/
CONSTRAIN/SUPPRESS/mode constants for the Wrap Pipeline runner.

Design notes:
- The gate is **opt-in** at request and config level. When disabled the
  runner does not call into this module at all, and the cost is zero.
- The gate is a **diagnostic policy layer**. It reads already-computed CAS
  signals (lacunarity, inversion flags, RPM satisfaction) plus an
  optional Verification Stack evidence packet and returns one of
  allow / caveat / constrain / suppress. It does not modify hidden states,
  bottleneck activations, logits, or generated tokens.
- The gate is a **companion** to the Output Gate (Stage 8), not a
  replacement. The Output Gate still computes NCCS over the LLM response;
  the readiness gate produces a per-request emission policy that the
  runner applies on top of the Output Gate result.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Hyphenated-package import shim
# ---------------------------------------------------------------------------

# Resolve `cas-native/model/generation_readiness_gate.py` relative to the
# project root (this file lives at api/pipeline/readiness_gate.py).
_API_PIPELINE_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _API_PIPELINE_DIR.parent.parent
_CAS_NATIVE_DIR = _PROJECT_ROOT / "cas-native"
_GATE_PATH = _CAS_NATIVE_DIR / "model" / "generation_readiness_gate.py"


def _ensure_cas_native_package() -> None:
    """Register `cas_native` and `cas_native.model` as packages in
    ``sys.modules`` so module-level dataclasses inside the gate resolve
    their parent module correctly.

    The cas-native directory is hyphenated and therefore not directly
    importable via the standard import machinery. This shim mirrors the
    technique the cas-native test conftest uses (see
    ``cas-native/tests/conftest.py``).
    """
    if str(_PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(_PROJECT_ROOT))

    if "cas_native" not in sys.modules:
        package = types.ModuleType("cas_native")
        package.__file__ = str(_CAS_NATIVE_DIR / "__init__.py")
        package.__path__ = [str(_CAS_NATIVE_DIR)]
        sys.modules["cas_native"] = package

    if "cas_native.model" not in sys.modules:
        model_dir = _CAS_NATIVE_DIR / "model"
        model_pkg = types.ModuleType("cas_native.model")
        model_pkg.__file__ = str(model_dir / "__init__.py")
        model_pkg.__path__ = [str(model_dir)]
        sys.modules["cas_native.model"] = model_pkg


def _load_gate_module() -> Any:
    """Load only the generation_readiness_gate submodule (not the rest of
    cas_native.model, which has heavy torch deps that we don't need here)."""
    _ensure_cas_native_package()
    fq_name = "cas_native.model.generation_readiness_gate"
    if fq_name in sys.modules:
        return sys.modules[fq_name]
    if not _GATE_PATH.exists():
        raise ImportError(
            f"Stage 20 Generation Readiness Gate source not found at {_GATE_PATH}"
        )
    spec = importlib.util.spec_from_file_location(fq_name, str(_GATE_PATH))
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Could not build import spec for {fq_name} from {_GATE_PATH}"
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[fq_name] = module
    spec.loader.exec_module(module)
    return module


_gate_module = _load_gate_module()

GenerationReadinessGate = _gate_module.GenerationReadinessGate
GenerationReadinessConfig = _gate_module.GenerationReadinessConfig
GenerationReadinessResult = _gate_module.GenerationReadinessResult

ALLOW: str = _gate_module.ALLOW
CAVEAT: str = _gate_module.CAVEAT
CONSTRAIN: str = _gate_module.CONSTRAIN
SUPPRESS: str = _gate_module.SUPPRESS

HIGH_PRECISION: str = _gate_module.HIGH_PRECISION
BALANCED: str = _gate_module.BALANCED
MAX_COVERAGE_TRIAGE: str = _gate_module.MAX_COVERAGE_TRIAGE

POLICY_VERSION: str = _gate_module.POLICY_VERSION

VALID_MODES = frozenset({HIGH_PRECISION, BALANCED, MAX_COVERAGE_TRIAGE})


# ---------------------------------------------------------------------------
# Shared gate instance for the Wrap Pipeline
# ---------------------------------------------------------------------------

# A single shared gate is safe because the gate is stateless beyond its
# config thresholds. Per-request mode overrides go through the `mode=`
# kwarg on `assess(...)`, not through reinstantiation.
_default_gate: GenerationReadinessGate | None = None


def get_default_gate() -> GenerationReadinessGate:
    """Return the process-wide default gate (BALANCED thresholds)."""
    global _default_gate
    if _default_gate is None:
        _default_gate = GenerationReadinessGate(GenerationReadinessConfig(mode=BALANCED))
    return _default_gate


def resolve_mode(requested: str | None, server_default: str) -> str:
    """Resolve the active readiness mode for a request.

    Order of precedence:
      1. Per-request `verification_mode` (if non-empty and valid)
      2. Server-side default (NC_WRAP_READINESS_GATE_MODE)
      3. BALANCED (final fallback if both are invalid)
    """
    if requested and requested in VALID_MODES:
        return requested
    if server_default and server_default in VALID_MODES:
        return server_default
    return BALANCED


# ---------------------------------------------------------------------------
# Pipeline-facing assessment helper
# ---------------------------------------------------------------------------

def assess_for_wrap(
    *,
    lacunarity_profile: dict | None,
    inversion_axis_scores: list[float] | None,
    rpm_completeness: float | None,
    verification: dict | None,
    mode: str,
) -> GenerationReadinessResult:
    """Convert Wrap Pipeline signal shapes into the gate's input contract.

    The Wrap Pipeline produces a single composite lacunarity score plus a
    gap-map dict (see `api/pipeline/lacunarity.py::compute_lacunarity_profile`),
    a 7-element vector of inversion-axis resistance scores, and a scalar
    RPM completeness. The Stage 20 gate expects:

      - lacunarity_scores: numeric or sequence (max() is taken)
      - lacunarity_meta:   { lacunarity, gap_map, domain_confidence }
      - inversion_flags:   sequence of activation probabilities in [0, 1]
                           where >= 0.5 counts as a flag
      - rpm_satisfaction:  scalar or sequence in [0, 1]

    Two conversions are non-obvious and load-bearing:

      (a) The Wrap inversion-scan emits *resistance* scores: 1.0 = perfectly
          resistant, 0.0 = inverted. The Stage 20 gate counts entries
          >= inversion_flag_threshold (default 0.5) as *flags*. To preserve
          the gate's semantics we therefore pass `1.0 - resistance` so that
          a degraded axis (resistance 0.2 → flag value 0.8) counts as a
          flag while a healthy axis (resistance 0.95 → 0.05) does not.

      (b) The Wrap lacunarity composite is a single float. We pass the
          composite as `lacunarity_scores` (the gate takes max of a single
          value) and additionally surface the gap_map and a domain-
          confidence proxy via `lacunarity_meta`. Domain confidence is
          approximated as 1 - composite_lacunarity so that high-lacunarity
          profiles register as low confidence — keeping the gate
          monotonic with the Wrap signal direction.
    """
    gate = get_default_gate()

    composite_lac = 0.0
    gap_map: list[float] = []
    if lacunarity_profile:
        composite_lac = float(lacunarity_profile.get("composite", 0.0) or 0.0)
        # gap_map is a dict in the wrap profile shape; the gate only needs
        # numeric activations. We surface the lengths of the absent_* lists
        # normalised to [0, 1] so the gate's gap-probability threshold
        # carries pipeline-meaningful signal.
        gm = lacunarity_profile.get("gap_map") or {}
        if isinstance(gm, dict):
            absent_ops = len(gm.get("absent_operators") or []) / 10.0
            absent_doms = len(gm.get("absent_domains") or []) / 4.0
            absent_drvs = len(gm.get("absent_drives") or []) / 7.0
            gap_map = [absent_ops, absent_doms, absent_drvs]

    # Domain-confidence proxy: 1 - composite lacunarity, clamped to [0, 1].
    domain_confidence = max(0.0, min(1.0, 1.0 - composite_lac / 4.0))

    lac_meta = {
        "lacunarity": composite_lac,
        "gap_map": gap_map,
        "domain_confidence": [domain_confidence],
    }

    # Inversion: resistance → flag-probability (see docstring (a) above).
    inversion_flags: list[float] = []
    if inversion_axis_scores:
        inversion_flags = [
            max(0.0, min(1.0, 1.0 - float(score)))
            for score in inversion_axis_scores
        ]

    rpm_value: float
    if rpm_completeness is None:
        rpm_value = 1.0
    else:
        rpm_value = max(0.0, min(1.0, float(rpm_completeness)))

    return gate.assess(
        lacunarity_scores=composite_lac,
        lacunarity_meta=lac_meta,
        inversion_flags=inversion_flags,
        rpm_satisfaction=rpm_value,
        verification=verification or {"accepted": True},
        mode=mode,
    )


__all__ = [
    "ALLOW",
    "BALANCED",
    "CAVEAT",
    "CONSTRAIN",
    "GenerationReadinessConfig",
    "GenerationReadinessGate",
    "GenerationReadinessResult",
    "HIGH_PRECISION",
    "MAX_COVERAGE_TRIAGE",
    "POLICY_VERSION",
    "SUPPRESS",
    "VALID_MODES",
    "assess_for_wrap",
    "get_default_gate",
    "resolve_mode",
]
