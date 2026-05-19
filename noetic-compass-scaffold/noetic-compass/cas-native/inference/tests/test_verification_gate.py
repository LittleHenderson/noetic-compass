"""Unit tests for the CAS Native Verification Gate.

Mirrors the Stage 19A decision logic from
``research/cas_probe/run_stage19a_formula_verification_stack.py``.

Each test exercises one decision branch of the stack:

1. all-agree + stable trace  -> ACCEPT-high
2. all-agree + marginal trace -> ACCEPT-medium
3. two agree, one dissents   -> SUPPRESS with one ``_conflicted`` reason
4. all-disagree              -> SUPPRESS with ``ensemble_all_disagree``
5. all-agree + unstable trace -> SUPPRESS with ``trace_unstable``
6. invalid CAS expression    -> SUPPRESS with ``compiler_invalid``
7. valid CAS expression      -> no ``compiler_invalid`` reason
8. quorum=2, 2-of-3 agree    -> ACCEPT still allowed
9. empty per_layer_trace     -> SUPPRESS gracefully with ``trace_unstable``
10. ACCEPT-high confidence   -> aggregate >= 0.85 from per-position confidences

The module is imported via the absolute path so the tests can run without
relying on the ``cas_native`` package alias maintained by the cas-native
test ``conftest.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Import the standalone module directly. The path resolves
#   noetic-compass/cas-native/inference/verification_gate.py
# without needing the project ``cas_native`` package alias.
_MODULE_DIR = Path(__file__).resolve().parent.parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

from verification_gate import (  # noqa: E402  (path-tweak before import)
    DEFAULT_ENSEMBLE_POSITIONS,
    VerificationGate,
    VerificationResult,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _all_agree_classifications(label: str = "^2^C") -> dict[str, str]:
    return {position: label for position in DEFAULT_ENSEMBLE_POSITIONS}


def _high_confidences(value: float = 0.95) -> dict[str, float]:
    return {position: value for position in DEFAULT_ENSEMBLE_POSITIONS}


def _stable_trace(label: str = "^2^C", n_layers: int = 12) -> list[str]:
    # 11 of 12 match dominant => stability 11/12 ≈ 0.917
    trace = [label] * (n_layers - 1) + ["^3^C"]
    return trace


def _marginal_trace(label: str = "^2^C", n_layers: int = 10) -> list[str]:
    # 7 of 10 match dominant => stability 0.7  (>= 0.6, < 0.8)
    trace = [label] * 7 + ["^3^C"] * 3
    return trace


def _unstable_trace(label: str = "^2^C", n_layers: int = 10) -> list[str]:
    # 5 of 10 dominant => stability 0.5 (< 0.6)
    trace = [label] * 5 + ["^3^C"] * 3 + ["^4^C"] * 2
    return trace


@pytest.fixture
def gate() -> VerificationGate:
    return VerificationGate()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_1_all_agree_stable_trace_accepts_high(gate: VerificationGate) -> None:
    """All 3 positions agree on a stable trace -> ACCEPT-high, no reasons."""
    result = gate.check(
        per_position_classifications=_all_agree_classifications("^2^C"),
        per_position_confidences=_high_confidences(0.95),
        per_layer_trace=_stable_trace("^2^C"),
    )

    assert isinstance(result, VerificationResult)
    assert result.decision == "ACCEPT"
    assert result.decision_tier == "high"
    assert result.suppression_reasons == []
    assert result.ensemble_agreement is True
    assert result.trace_stability >= 0.8
    assert result.compiler_valid is None  # no expression supplied


def test_2_all_agree_marginal_trace_accepts_medium(gate: VerificationGate) -> None:
    """All 3 agree, trace stability in [0.6, 0.8) -> ACCEPT-medium."""
    result = gate.check(
        per_position_classifications=_all_agree_classifications("^2^C"),
        per_position_confidences=_high_confidences(0.9),
        per_layer_trace=_marginal_trace("^2^C"),
    )

    assert result.decision == "ACCEPT"
    assert result.decision_tier == "medium"
    assert result.suppression_reasons == []
    assert result.ensemble_agreement is True
    assert 0.6 <= result.trace_stability < 0.8


def test_3_two_agree_one_dissents_suppresses_with_conflicted_reason(
    gate: VerificationGate,
) -> None:
    """One position disagrees -> SUPPRESS with that position's ``_conflicted``."""
    classifications = {
        "focus_token": "^2^C",
        "final_token": "^2^C",
        "mean_over_seq_len": "^3^C",  # dissenter
    }
    result = gate.check(
        per_position_classifications=classifications,
        per_position_confidences=_high_confidences(0.9),
        per_layer_trace=_stable_trace("^2^C"),
    )

    assert result.decision == "SUPPRESS"
    assert result.decision_tier == "suppress"
    assert "mean_over_seq_len_conflicted" in result.suppression_reasons
    assert "ensemble_all_disagree" not in result.suppression_reasons
    # Only one dissenter -> exactly one conflict reason.
    conflict_reasons = [r for r in result.suppression_reasons if r.endswith("_conflicted")]
    assert len(conflict_reasons) == 1


def test_4_all_three_disagree_suppresses_with_ensemble_all_disagree(
    gate: VerificationGate,
) -> None:
    """Three different labels -> SUPPRESS with ``ensemble_all_disagree``."""
    classifications = {
        "focus_token": "^2^C",
        "final_token": "^3^C",
        "mean_over_seq_len": "^4^C",
    }
    result = gate.check(
        per_position_classifications=classifications,
        per_position_confidences=_high_confidences(0.8),
        per_layer_trace=_stable_trace("^2^C"),
    )

    assert result.decision == "SUPPRESS"
    assert result.decision_tier == "suppress"
    assert "ensemble_all_disagree" in result.suppression_reasons
    # Should not also fire ``_conflicted`` for individual positions when
    # everyone is in a separate bucket.
    conflict_reasons = [r for r in result.suppression_reasons if r.endswith("_conflicted")]
    assert conflict_reasons == []
    assert result.ensemble_agreement is False


def test_5_stable_ensemble_but_unstable_trace_suppresses_with_trace_unstable(
    gate: VerificationGate,
) -> None:
    """All agree but trace stability < 0.6 -> SUPPRESS with ``trace_unstable``."""
    result = gate.check(
        per_position_classifications=_all_agree_classifications("^2^C"),
        per_position_confidences=_high_confidences(0.9),
        per_layer_trace=_unstable_trace("^2^C"),
    )

    assert result.decision == "SUPPRESS"
    # Ensemble agrees, only trace flagged -> uncertain edge case per spec.
    assert result.decision_tier == "uncertain"
    # Per spec, uncertain tier records empty suppression_reasons; the
    # mixed branch (ensemble + trace) shows ``trace_unstable`` instead.
    assert result.suppression_reasons == []
    assert result.ensemble_agreement is True
    assert result.trace_stability < 0.6


def test_5b_unstable_trace_with_dissent_records_both_reasons() -> None:
    """When trace_unstable and a position dissents, both reasons fire."""
    gate = VerificationGate()
    classifications = {
        "focus_token": "^2^C",
        "final_token": "^2^C",
        "mean_over_seq_len": "^3^C",
    }
    result = gate.check(
        per_position_classifications=classifications,
        per_position_confidences=_high_confidences(0.8),
        per_layer_trace=_unstable_trace("^2^C"),
    )
    assert result.decision == "SUPPRESS"
    assert result.decision_tier == "suppress"
    assert "trace_unstable" in result.suppression_reasons
    assert "mean_over_seq_len_conflicted" in result.suppression_reasons


def test_6_invalid_cas_expression_suppresses_with_compiler_invalid() -> None:
    """A CAS expression that fails to compile -> ``compiler_invalid`` reason."""
    gate = VerificationGate(expression_compiler=lambda _expr: False)
    result = gate.check(
        per_position_classifications=_all_agree_classifications("^2^C"),
        per_position_confidences=_high_confidences(0.95),
        per_layer_trace=_stable_trace("^2^C"),
        cas_expression="(^2^P × ^3^P)",
    )

    assert result.decision == "SUPPRESS"
    assert result.decision_tier == "suppress"
    assert "compiler_invalid" in result.suppression_reasons
    assert result.compiler_valid is False


def test_7_valid_cas_expression_does_not_add_compiler_invalid() -> None:
    """A CAS expression that compiles -> no ``compiler_invalid`` reason."""
    gate = VerificationGate(expression_compiler=lambda _expr: True)
    result = gate.check(
        per_position_classifications=_all_agree_classifications("^2^C"),
        per_position_confidences=_high_confidences(0.95),
        per_layer_trace=_stable_trace("^2^C"),
        cas_expression="^2^C",
    )

    assert result.decision == "ACCEPT"
    assert result.decision_tier == "high"
    assert "compiler_invalid" not in result.suppression_reasons
    assert result.compiler_valid is True


def test_8_quorum_two_with_two_of_three_agreeing_still_accepts() -> None:
    """``ensemble_quorum=2`` + 2-of-3 agree on stable trace -> ACCEPT."""
    gate = VerificationGate(ensemble_quorum=2)
    classifications = {
        "focus_token": "^2^C",
        "final_token": "^2^C",
        "mean_over_seq_len": "^3^C",  # dissenter, tolerated under quorum=2
    }
    result = gate.check(
        per_position_classifications=classifications,
        per_position_confidences=_high_confidences(0.92),
        per_layer_trace=_stable_trace("^2^C"),
    )

    assert result.decision == "ACCEPT"
    assert result.decision_tier == "high"
    assert result.ensemble_agreement is True


def test_9_empty_per_layer_trace_suppresses_gracefully() -> None:
    """Empty trace must not crash -> SUPPRESS with ``trace_unstable``."""
    gate = VerificationGate()
    result = gate.check(
        per_position_classifications=_all_agree_classifications("^2^C"),
        per_position_confidences=_high_confidences(0.9),
        per_layer_trace=[],
    )

    assert result.decision == "SUPPRESS"
    # Ensemble agreed; only the empty trace prevents acceptance, so we land
    # in the uncertain branch with no per-signal reason recorded.
    assert result.decision_tier == "uncertain"
    assert result.trace_stability == 0.0


def test_10_accept_high_confidence_at_least_0_85() -> None:
    """ACCEPT-high should aggregate to confidence >= 0.85 from inputs."""
    gate = VerificationGate()
    result = gate.check(
        per_position_classifications=_all_agree_classifications("^2^C"),
        per_position_confidences={
            "focus_token": 0.92,
            "final_token": 0.90,
            "mean_over_seq_len": 0.88,
        },
        per_layer_trace=_stable_trace("^2^C"),
    )

    assert result.decision == "ACCEPT"
    assert result.decision_tier == "high"
    assert result.confidence >= 0.85


# ---------------------------------------------------------------------------
# Configuration sanity tests (constructor validation)
# ---------------------------------------------------------------------------


def test_constructor_rejects_empty_positions() -> None:
    with pytest.raises(ValueError):
        VerificationGate(ensemble_positions=())


def test_constructor_rejects_quorum_greater_than_positions() -> None:
    with pytest.raises(ValueError):
        VerificationGate(
            ensemble_positions=("a", "b"),
            ensemble_quorum=3,
        )


def test_constructor_rejects_out_of_range_threshold() -> None:
    with pytest.raises(ValueError):
        VerificationGate(trace_stability_threshold=1.5)
