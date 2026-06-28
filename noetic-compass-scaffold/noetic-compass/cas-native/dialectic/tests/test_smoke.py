"""Smoke test: end-to-end orchestrator on the K=9 baseline checkpoint.

Asserts plumbing correctness only. Priming is stubbed at this scaffold
stage, so we do NOT assert specific output Noetic / Domain / Drive /
Register values. We DO assert:

  - the predictor loads
  - the orchestrator runs without raising
  - every rotation produces an attractor with a score
  - top-K selection returns at least one attractor
  - final_expression is a non-empty string
  - rotation_trace is a non-empty list of strings
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Path / package shim (mirrors conftest.py for tests run via the sibling
# package layout)
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve()
_PACKAGE_ROOT = _HERE.parent.parent.parent  # cas-native/
_PROJECT_ROOT = _PACKAGE_ROOT.parent          # noetic-compass/

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

if "cas_native" not in sys.modules:
    package = types.ModuleType("cas_native")
    package.__file__ = str(_PACKAGE_ROOT / "__init__.py")
    package.__path__ = [str(_PACKAGE_ROOT)]
    sys.modules["cas_native"] = package


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_RUN_DIR = (
    _PACKAGE_ROOT
    / "training"
    / "runs"
    / "structured-token-recoverable-paraphrase-v77fix-20epoch-gpu-20260502-1045"
)


def _import_predictor():
    """Lazy import: predict_cas pulls in torch which is heavy."""
    from cas_native.inference.predict_cas import load_predictor
    return load_predictor


def _diverse_demo_prompts():
    """Pick three prompts spanning v74_baseline, v75_register, v76_production."""
    from cas_native.inference.demo_prompts import DEMO_PROMPTS

    by_bucket: dict[str, list[dict]] = {}
    for entry in DEMO_PROMPTS:
        by_bucket.setdefault(entry["bucket"], []).append(entry)

    chosen: list[dict] = []
    for bucket in ("v74_baseline", "v75_register", "v76_production"):
        if bucket in by_bucket:
            chosen.append(by_bucket[bucket][0])
    # Fall back to any first three if buckets missing.
    if len(chosen) < 3:
        for entry in DEMO_PROMPTS:
            if entry not in chosen:
                chosen.append(entry)
            if len(chosen) >= 3:
                break
    return chosen[:3]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def predictor():
    if not DEFAULT_RUN_DIR.exists():
        pytest.skip(f"baseline checkpoint dir not found: {DEFAULT_RUN_DIR}")
    load_predictor = _import_predictor()
    return load_predictor(DEFAULT_RUN_DIR)


@pytest.fixture(scope="module")
def orchestrator(predictor):
    from cas_native.dialectic import DialecticOrchestrator
    return DialecticOrchestrator(predictor, max_rotations=2, top_k=1)


# ---------------------------------------------------------------------------
# Smoke tests
# ---------------------------------------------------------------------------

def test_imports_only():
    """Module surface imports cleanly without torch already loaded."""
    from cas_native.dialectic import (
        Attractor,
        AttractorScore,
        AxisPriming,
        CASInstance,
        DialecticOrchestrator,
        DialecticResponse,
        ROTATION_DOMAIN,
        ROTATION_DRIVE_INVERSION,
        ROTATION_NOETIC_INVOLUTION,
        ROTATION_REGISTER_INVERSION,
        score_attractor,
        select_rotations,
        select_top_attractors,
    )

    # Sanity: rotation libraries non-empty.
    assert ROTATION_NOETIC_INVOLUTION
    assert ROTATION_DOMAIN
    assert ROTATION_DRIVE_INVERSION
    assert ROTATION_REGISTER_INVERSION


def test_axis_priming_validation():
    from cas_native.dialectic import AxisPriming

    # Valid configs.
    AxisPriming()
    AxisPriming(noetic_bias=0)
    AxisPriming(noetic_bias=9, domain_bias="P", drive_bias="F4", register_bias="T")

    # Invalid: out-of-range Noetic.
    with pytest.raises(ValueError):
        AxisPriming(noetic_bias=10)

    # Invalid: bad domain.
    with pytest.raises(ValueError):
        AxisPriming(domain_bias="X")

    # Invalid: bad drive.
    with pytest.raises(ValueError):
        AxisPriming(drive_bias="F8")

    # Invalid: bad register.
    with pytest.raises(ValueError):
        AxisPriming(register_bias="X")

    # Invalid: bad temperature.
    with pytest.raises(ValueError):
        AxisPriming(temperature=0.0)


def test_select_rotations_returns_pairs():
    from cas_native.dialectic import AxisPriming, select_rotations

    rotations = select_rotations("just a query", k=3)
    assert len(rotations) == 3
    for pair in rotations:
        assert isinstance(pair, tuple) and len(pair) == 2
        assert isinstance(pair[0], AxisPriming)
        assert isinstance(pair[1], AxisPriming)


def test_orchestrator_smoke_diverse_prompts(orchestrator):
    prompts = _diverse_demo_prompts()
    assert len(prompts) >= 1, "expected at least one demo prompt"

    sample_for_print = None

    for entry in prompts:
        prompt_text = entry["prompt"]
        response = orchestrator.respond(prompt_text)

        # Plumbing-correctness assertions.
        assert response is not None
        assert isinstance(response.attractors_evaluated, list)
        assert isinstance(response.scores, list)
        assert len(response.attractors_evaluated) == len(response.scores), (
            "attractor / score lists should be parallel"
        )
        assert len(response.attractors_evaluated) >= 1, (
            f"expected >= 1 attractor for prompt {prompt_text!r}, "
            f"got {len(response.attractors_evaluated)}"
        )
        assert response.chosen_idx >= 0, (
            f"top-K selection failed for prompt {prompt_text!r}"
        )
        assert isinstance(response.final_expression, str)
        assert response.final_expression, (
            "final_expression must be non-empty"
        )
        assert isinstance(response.rotation_trace, list)
        assert response.rotation_trace, "rotation_trace must be non-empty"
        assert all(isinstance(line, str) for line in response.rotation_trace)
        assert response.elapsed_ms > 0

        for attractor in response.attractors_evaluated:
            assert attractor.integration_kind in (
                "co_presence", "integration", "set_spec", "fallback"
            )
            assert isinstance(attractor.integrated_expression, str)

        for score in response.scores:
            assert 0.0 <= score.substance <= 1.0
            assert 0.0 <= score.relevance <= 1.0
            assert 0.0 <= score.admissibility <= 1.0
            assert 0.0 <= score.invariant_balance <= 1.0
            assert 0.0 <= score.composite <= 1.0

        if sample_for_print is None:
            sample_for_print = (prompt_text, response)

    if sample_for_print is not None:
        prompt_text, response = sample_for_print
        # Print one full sample for human inspection. pytest -s will surface this.
        print()
        print("=" * 72)
        print(f"Sample DialecticResponse for: {prompt_text!r}")
        print("=" * 72)
        print(f"final_expression: {response.final_expression}")
        print(f"final_english:    {response.final_english}")
        print("rotation_trace:")
        for line in response.rotation_trace:
            print(f"  {line}")
        print(f"elapsed_ms: {response.elapsed_ms:.1f}")
        print("=" * 72)


def test_orchestrator_handles_empty_query(orchestrator):
    """Empty queries should not raise; should produce some attractor or
    a clean empty-trace response."""
    response = orchestrator.respond("")
    # Either we get rotations + attractors with something rendered, or
    # we get a clean no-op trace. Both are valid; we just must not raise.
    assert response is not None
    assert isinstance(response.rotation_trace, list)
    assert response.rotation_trace, "even on empty query, trace should explain rotations"
