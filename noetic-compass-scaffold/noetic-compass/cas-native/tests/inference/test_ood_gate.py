"""Tests for the OOD routing gate (Step C of the v0 relevance-failure plan).

The K=9 classifier already detects out-of-distribution input. The gate's job
is to consult that detection and STOP shipping a CAS classification + native
generation when the detector says the input is out-of-distribution. Without
the gate, casual prompts like "what up?" / "this shit is wack" / "Bro I don't
know" produced confidently-wrong CAS classifications during the
2026-05-07 human-relevance audit
(``docs/working/path_B4_human_relevance_failure_2026_05_07.md``).

These tests assert:

* The four canonical failure prompts no longer route to ``CAS_PIPELINE``.
* A clean CAS prompt with high confidence DOES route to ``CAS_PIPELINE``.
* A CAS-detected prompt below the gate's confidence threshold routes to
  ``NEED_CONTEXT`` rather than ship a low-confidence classification.
* ``chat.py`` actually calls the gate from ``_predict_and_show`` (source-grep
  pin so future edits don't silently regress the routing).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cas_native.inference.ood_gate import (
    GateResult,
    OODGate,
    RouteDecision,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_OOD_NOTE = (
    "no CAS signal detected in free-form input; predicting on the "
    "raw text. The K=9 baseline tends to collapse to its prior on "
    "out-of-distribution colloquial English (documented modality "
    "limitation)."
)


def _ood_k9_result(**extra: object) -> dict[str, object]:
    """K=9 result shape that mimics the OOD-detected branch in chat.py.

    The detector wrote the sentinel into ``notes``; per-head confidences may
    or may not be present. The gate must trigger on the sentinel regardless
    of confidence.
    """
    base: dict[str, object] = {
        "notes": [_OOD_NOTE],
        "noetic": 2,
        "domain": "E",
        "drive": "F5",
        "registers": ["E"],
        # Confidences are typical-looking; the gate must NOT use them to
        # override the OOD-sentinel verdict.
        "noetic_confidence": 0.71,
        "domain_confidence": 0.65,
        "drive_confidence": 0.58,
    }
    base.update(extra)
    return base


def _confident_cas_k9_result(confidence: float = 0.85) -> dict[str, object]:
    """K=9 result for a clean, in-distribution CAS prompt with high confidence."""
    return {
        # No notes field, no OOD sentinel anywhere.
        "noetic": 3,
        "domain": "P",
        "drive": "F2",
        "registers": ["A"],
        "noetic_confidence": confidence,
        "domain_confidence": confidence,
        "drive_confidence": confidence,
        "register_confidence": confidence,
    }


def _chat_source() -> str:
    """Return chat.py source for source-grep tests."""
    repo_root = Path(__file__).resolve().parents[3]
    chat_path = repo_root / "cas-native" / "inference" / "chat.py"
    assert chat_path.exists(), f"chat.py not found at {chat_path}"
    return chat_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Required spec tests — the four canonical prompts must NOT ship CAS
# ---------------------------------------------------------------------------


def test_what_up_does_not_route_to_cas_pipeline():
    gate = OODGate()
    result = gate.route("what up?", _ood_k9_result())
    assert isinstance(result, GateResult)
    assert result.decision is not RouteDecision.CAS_PIPELINE
    # "what up?" is short + casual -> conversational fallback.
    assert result.decision is RouteDecision.CONVERSATIONAL_FALLBACK
    assert result.canned_response  # canned plain-English reply present
    assert "CAS" not in (result.canned_response or "") or "CAS structure" in (
        result.canned_response or ""
    )


def test_this_shit_is_wack_does_not_route_to_cas_pipeline():
    gate = OODGate()
    # The audit prompt verbatim was "This shit is wack as fuck."
    result = gate.route(
        "This shit is wack as fuck.", _ood_k9_result()
    )
    assert result.decision is not RouteDecision.CAS_PIPELINE
    # 6 words, multiple casual hits -> conversational fallback.
    assert result.decision is RouteDecision.CONVERSATIONAL_FALLBACK
    assert result.canned_response


def test_bro_i_dont_know_does_not_route_to_cas_pipeline():
    gate = OODGate()
    result = gate.route("Bro I don't know", _ood_k9_result())
    assert result.decision is not RouteDecision.CAS_PIPELINE
    assert result.decision is RouteDecision.CONVERSATIONAL_FALLBACK
    assert result.canned_response


# ---------------------------------------------------------------------------
# Required spec tests — valid CAS prompt regression + low-confidence branch
# ---------------------------------------------------------------------------


def test_valid_cas_prompt_routes_to_pipeline():
    """Regression: a confident, in-distribution CAS prompt must still flow."""
    gate = OODGate()
    prompt = (
        "I keep practicing the same scale every morning before I do anything else."
    )
    result = gate.route(prompt, _confident_cas_k9_result(confidence=0.85))
    assert result.decision is RouteDecision.CAS_PIPELINE
    assert result.canned_response is None


def test_low_confidence_routes_to_need_context():
    """K=9 ran (no OOD sentinel) but confidence is too low -> NEED_CONTEXT."""
    gate = OODGate(confidence_threshold=0.4)
    prompt = (
        "I noticed something unusual in my response to that situation today."
    )
    # All head confidences are below threshold.
    low_conf = {
        "noetic": 1,
        "domain": "C",
        "drive": "F4",
        "noetic_confidence": 0.21,
        "domain_confidence": 0.18,
        "drive_confidence": 0.30,
        "register_confidence": 0.25,
    }
    result = gate.route(prompt, low_conf)
    assert result.decision is RouteDecision.NEED_CONTEXT
    assert result.canned_response


# ---------------------------------------------------------------------------
# Source-grep wiring pins on chat.py
# ---------------------------------------------------------------------------


def test_chat_imports_ood_gate():
    """chat.py must import the gate; otherwise routing won't fire."""
    src = _chat_source()
    assert "from cas_native.inference.ood_gate import" in src, (
        "chat.py must import the OOD gate module"
    )
    assert "OODGate" in src
    assert "RouteDecision" in src


def test_predict_and_show_calls_ood_gate():
    """The typed-input prediction path must call OODGate.route(...)."""
    src = _chat_source()
    fn_start = src.index("def _predict_and_show(")
    # Read a generous slice — the function is ~150 lines after our edit.
    fn_body = src[fn_start: fn_start + 8000]
    assert ".route(" in fn_body, (
        "_predict_and_show must call <gate>.route(prompt, k9_result) before "
        "invoking the K=9 -> native pipeline"
    )
    assert "RouteDecision.CAS_PIPELINE" in fn_body, (
        "_predict_and_show must branch on RouteDecision.CAS_PIPELINE"
    )
    # The skip-native branch must short-circuit before native generation.
    # We assert the gate-check appears BEFORE the generate_reply call.
    gate_pos = fn_body.find(".route(")
    gen_pos = fn_body.find("generate_reply(")
    assert gate_pos != -1 and gen_pos != -1, (
        "expected both gate.route(...) and generate_reply(...) in the "
        "function body"
    )
    assert gate_pos < gen_pos, (
        "gate must be consulted BEFORE generate_reply is invoked"
    )


# ---------------------------------------------------------------------------
# Robustness coverage (small, kept tight to spec)
# ---------------------------------------------------------------------------


def test_long_non_casual_ood_prompt_routes_to_clarification():
    """Long free-form input with no casual hits but OOD-detected goes to
    CLARIFICATION rather than CONVERSATIONAL_FALLBACK."""
    gate = OODGate()
    long_prompt = (
        "Could you explain in detail the relationship between the proton's "
        "magnetic moment and the deeper foundations of quantum chromodynamics "
        "as it pertains to lattice simulations of low-energy hadron physics."
    )
    result = gate.route(long_prompt, _ood_k9_result())
    assert result.decision is RouteDecision.CLARIFICATION
    assert result.canned_response


def test_ood_sentinel_in_nested_field_still_triggers():
    """Defensive: sentinel may appear in note (singular), system_notes, etc."""
    gate = OODGate()
    for field in ("note", "ood_note", "system_notes"):
        result = gate.route(
            "yo",
            {field: _OOD_NOTE},
        )
        assert result.decision is not RouteDecision.CAS_PIPELINE, (
            f"sentinel in {field!r} must still trigger the gate"
        )


def test_threshold_is_configurable():
    gate = OODGate(confidence_threshold=0.9)
    # With threshold 0.9, even 0.85 confidence is too low.
    result = gate.route(
        "A reasonable prompt about practicing scales every morning.",
        _confident_cas_k9_result(confidence=0.85),
    )
    assert result.decision is RouteDecision.NEED_CONTEXT


def test_threshold_validation():
    with pytest.raises(ValueError):
        OODGate(confidence_threshold=-0.1)
    with pytest.raises(ValueError):
        OODGate(confidence_threshold=1.1)


def test_route_rejects_non_string_prompt():
    gate = OODGate()
    with pytest.raises(TypeError):
        gate.route(123, _ood_k9_result())  # type: ignore[arg-type]


def test_empty_prompt_falls_back_when_ood():
    gate = OODGate()
    result = gate.route("", _ood_k9_result())
    assert result.decision is RouteDecision.CONVERSATIONAL_FALLBACK


def test_no_confidence_data_does_not_block_pipeline():
    """If neither sentinel nor confidence info exists, route to pipeline.

    This preserves backward compatibility for predictors that do not yet
    expose per-head confidences in the result dict.
    """
    gate = OODGate()
    bare = {"noetic": 2, "domain": "P", "drive": "F2"}
    result = gate.route("an in-distribution-looking prompt", bare)
    assert result.decision is RouteDecision.CAS_PIPELINE
