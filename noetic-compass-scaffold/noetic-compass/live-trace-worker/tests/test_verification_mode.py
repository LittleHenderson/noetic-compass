from __future__ import annotations

from app.runtime.pythia_runner import _verification_payload
from app.runtime.verification_mode import (
    build_verification_telemetry,
    resolve_verification_mode,
)
from app.schemas.events import TokenEvent
from app.schemas.requests import CreateSessionRequest


def _method_config(mode: str) -> dict:
    return {
        "enabled_methods": ["verification_stack"],
        "knobs": {"verification_stack": {"mode": mode}},
    }


def test_same_score_changes_verdict_by_mode():
    score = 0.70

    balanced = build_verification_telemetry(_method_config("BALANCED"), confidence=score)
    high_precision = build_verification_telemetry(
        _method_config("HIGH_PRECISION"),
        confidence=score,
    )
    max_coverage = build_verification_telemetry(
        _method_config("MAX_COVERAGE_TRIAGE"),
        confidence=score,
    )

    assert balanced.verdict == "ACCEPT"
    assert high_precision.verdict == "FLAG"
    assert max_coverage.verdict == "ACCEPT"
    assert high_precision.threshold > balanced.threshold > max_coverage.threshold


def test_lower_score_is_suppressed_or_flagged_by_mode():
    score = 0.40

    balanced = build_verification_telemetry(_method_config("BALANCED"), confidence=score)
    high_precision = build_verification_telemetry(
        _method_config("HIGH_PRECISION"),
        confidence=score,
    )
    max_coverage = build_verification_telemetry(
        _method_config("MAX_COVERAGE_TRIAGE"),
        confidence=score,
    )

    assert balanced.verdict == "SUPPRESS"
    assert high_precision.verdict == "SUPPRESS"
    assert max_coverage.verdict == "FLAG"


def test_invalid_mode_fails_closed_to_high_precision():
    mode, invalid = resolve_verification_mode(_method_config("anything-goes"))

    assert mode == "HIGH_PRECISION"
    assert invalid == "anything-goes"

    telemetry = build_verification_telemetry(
        _method_config("anything-goes"),
        confidence=0.70,
    )
    assert telemetry.mode == "HIGH_PRECISION"
    assert telemetry.verdict == "FLAG"
    assert telemetry.invalid_mode == "anything-goes"


def test_missing_score_flags_without_fabricating_confidence():
    telemetry = build_verification_telemetry(
        _method_config("BALANCED"),
        confidence=None,
    )

    assert telemetry.verdict == "FLAG"
    assert telemetry.score is None
    assert telemetry.score_source == "unavailable"


def test_proxy_score_is_labeled_as_proxy_not_confidence():
    telemetry = build_verification_telemetry(
        _method_config("BALANCED"),
        confidence=None,
        proxy_confidence=0.90,
    )

    assert telemetry.verdict == "ACCEPT"
    assert telemetry.score == 0.90
    assert telemetry.score_source == "proxy_confidence"


def test_malformed_score_is_unavailable_not_clamped():
    telemetry = build_verification_telemetry(
        _method_config("BALANCED"),
        confidence=1.4,
    )

    assert telemetry.verdict == "FLAG"
    assert telemetry.score is None
    assert telemetry.score_source == "unavailable"


def test_pythia_runner_payload_uses_request_mode():
    req = CreateSessionRequest(
        prompt="hello",
        max_new_tokens=1,
        method_config=_method_config("HIGH_PRECISION"),
    )

    payload = _verification_payload(req, confidence=0.70)

    assert payload == {
        "verification_mode": "HIGH_PRECISION",
        "verification_verdict": "FLAG",
        "verification_threshold": 0.85,
        "verification_score": 0.70,
        "verification_score_source": "confidence",
        "verification_invalid_mode": None,
    }


def test_pythia_runner_omits_payload_when_verification_not_requested():
    req = CreateSessionRequest(
        prompt="hello",
        max_new_tokens=1,
        method_config={"enabled_methods": [], "knobs": {}},
    )

    assert _verification_payload(req, confidence=0.70) == {}


def test_token_event_accepts_verification_telemetry_fields():
    event = TokenEvent(
        token_index=0,
        token="hello",
        confidence=None,
        verification_mode="MAX_COVERAGE_TRIAGE",
        verification_verdict="ACCEPT",
        verification_threshold=0.50,
        verification_score=0.70,
        verification_score_source="confidence",
    )

    assert event.verification_mode == "MAX_COVERAGE_TRIAGE"
    assert event.verification_verdict == "ACCEPT"
