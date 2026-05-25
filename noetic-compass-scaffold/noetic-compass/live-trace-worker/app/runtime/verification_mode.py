"""Verification-mode verdicts for live token telemetry.

The Atlas cockpit exposes BALANCED / HIGH_PRECISION /
MAX_COVERAGE_TRIAGE as a top-level control. This module is the worker-side
source of truth for what that control does.

The score consumed here is the real runner's normalized softmax-margin when
available. If a caller explicitly passes a proxy score, the emitted telemetry
labels it as ``proxy_confidence`` so it cannot be mistaken for a calibrated
confidence metric.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal

VerificationMode = Literal["BALANCED", "HIGH_PRECISION", "MAX_COVERAGE_TRIAGE"]
VerificationVerdict = Literal["ACCEPT", "FLAG", "SUPPRESS"]
VerificationScoreSource = Literal["confidence", "proxy_confidence", "unavailable"]

DEFAULT_VERIFICATION_MODE: VerificationMode = "BALANCED"
FAIL_CLOSED_VERIFICATION_MODE: VerificationMode = "HIGH_PRECISION"


@dataclass(frozen=True)
class VerificationModeThresholds:
    accept: float
    flag: float


@dataclass(frozen=True)
class VerificationTelemetry:
    mode: VerificationMode
    verdict: VerificationVerdict
    threshold: float
    score: float | None
    score_source: VerificationScoreSource
    invalid_mode: str | None = None


THRESHOLDS: dict[VerificationMode, VerificationModeThresholds] = {
    "BALANCED": VerificationModeThresholds(accept=0.65, flag=0.45),
    "HIGH_PRECISION": VerificationModeThresholds(accept=0.85, flag=0.55),
    "MAX_COVERAGE_TRIAGE": VerificationModeThresholds(accept=0.50, flag=0.30),
}


def resolve_verification_mode(method_config: dict[str, Any] | None) -> tuple[VerificationMode, str | None]:
    """Resolve the requested verification mode from the live method config.

    Accepted locations are deliberately tolerant because deployed UI builds
    have used both a top-level key and a verification_stack knob. Unknown
    modes fail closed to HIGH_PRECISION and record the invalid raw value.
    """
    raw_mode: Any = None
    if isinstance(method_config, dict):
        knobs = method_config.get("knobs")
        if isinstance(knobs, dict):
            stack = knobs.get("verification_stack")
            if isinstance(stack, dict):
                raw_mode = stack.get("mode", stack.get("verification_mode"))
        if raw_mode is None:
            raw_mode = method_config.get("verification_mode", method_config.get("mode"))

    if raw_mode is None:
        return DEFAULT_VERIFICATION_MODE, None

    normalized = str(raw_mode).strip().upper()
    normalized = normalized.replace("-", "_").replace(" ", "_")
    if normalized in THRESHOLDS:
        return normalized, None  # type: ignore[return-value]
    return FAIL_CLOSED_VERIFICATION_MODE, str(raw_mode)


def build_verification_telemetry(
    method_config: dict[str, Any] | None,
    *,
    confidence: float | None,
    proxy_confidence: float | None = None,
) -> VerificationTelemetry:
    """Classify a token score according to the resolved verification mode."""
    mode, invalid_mode = resolve_verification_mode(method_config)
    source: VerificationScoreSource = "confidence"
    score = _usable_score(confidence)
    if score is None:
        score = _usable_score(proxy_confidence)
        source = "proxy_confidence" if score is not None else "unavailable"

    thresholds = THRESHOLDS[mode]
    if score is None:
        verdict: VerificationVerdict = "FLAG"
    elif score >= thresholds.accept:
        verdict = "ACCEPT"
    elif score >= thresholds.flag:
        verdict = "FLAG"
    else:
        verdict = "SUPPRESS"

    return VerificationTelemetry(
        mode=mode,
        verdict=verdict,
        threshold=thresholds.accept,
        score=score,
        score_source=source,
        invalid_mode=invalid_mode,
    )


def _usable_score(value: float | None) -> float | None:
    """Return an in-range score or None.

    We do not clamp out-of-range values into respectability. If upstream
    passes a malformed score, the verdict falls to FLAG with source
    unavailable rather than fabricating confidence.
    """
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(parsed):
        return None
    if not 0.0 <= parsed <= 1.0:
        return None
    return round(parsed, 3)
