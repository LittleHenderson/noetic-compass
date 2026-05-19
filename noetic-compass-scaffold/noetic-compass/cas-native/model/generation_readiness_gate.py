"""Generation readiness policy gate for CAS-Native.

This module is intentionally not a tensor throttle. Earlier TKS valve work
showed that learned multiplicative gates can discover the shortcut of
suppressing generation entirely. The Stage 20 gate is therefore a pure
diagnostic policy layer: it reads existing CAS safety signals and returns an
auditable generation policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
import torch.nn as nn


HIGH_PRECISION = "HIGH_PRECISION"
BALANCED = "BALANCED"
MAX_COVERAGE_TRIAGE = "MAX_COVERAGE_TRIAGE"

ALLOW = "allow"
CAVEAT = "caveat"
CONSTRAIN = "constrain"
SUPPRESS = "suppress"

POLICY_VERSION = "stage20_generation_readiness_gate_v1"


_MODE_THRESHOLDS: dict[str, dict[str, float]] = {
    HIGH_PRECISION: {"caveat": 0.20, "constrain": 0.45, "suppress": 0.75},
    BALANCED: {"caveat": 0.25, "constrain": 0.55, "suppress": 0.85},
    MAX_COVERAGE_TRIAGE: {"caveat": 0.30, "constrain": 0.65, "suppress": 0.95},
}

_ACTION_SEVERITY = {
    ALLOW: 0,
    CAVEAT: 1,
    CONSTRAIN: 2,
    SUPPRESS: 3,
}


@dataclass(frozen=True)
class GenerationReadinessConfig:
    """Thresholds for the diagnostic readiness policy."""

    mode: str = BALANCED
    lacunarity_warn: float = 1.0
    lacunarity_high: float = 2.0
    gap_warn: float = 0.55
    gap_high: float = 0.75
    domain_confidence_warn: float = 0.50
    domain_confidence_low: float = 0.35
    inversion_flag_threshold: float = 0.50
    rpm_warn: float = 0.65
    rpm_low: float = 0.45


@dataclass(frozen=True)
class GenerationReadinessResult:
    """Auditable generation policy emitted by the readiness gate."""

    generation_readiness: str
    risk_score: float
    reasons: tuple[str, ...]
    recommended_mode: str
    mode: str
    evidence: dict[str, float | int | str | bool]
    policy_version: str = POLICY_VERSION

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict for Evidence Packet emission."""
        return {
            "generation_readiness": self.generation_readiness,
            "risk_score": self.risk_score,
            "reasons": list(self.reasons),
            "recommended_mode": self.recommended_mode,
            "mode": self.mode,
            "evidence": dict(self.evidence),
            "policy_version": self.policy_version,
        }


def _validate_mode(mode: str) -> str:
    if mode not in _MODE_THRESHOLDS:
        valid = ", ".join(sorted(_MODE_THRESHOLDS))
        raise ValueError(
            f"Unknown generation readiness mode {mode!r}; expected one of {valid}"
        )
    return mode


def _flatten_numbers(value: Any) -> list[float]:
    if value is None:
        return []
    if torch.is_tensor(value):
        if value.numel() == 0:
            return []
        return [
            float(v)
            for v in value.detach().to(dtype=torch.float32).reshape(-1).cpu().tolist()
        ]
    if isinstance(value, bool):
        return [1.0 if value else 0.0]
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, (list, tuple)):
        out: list[float] = []
        for item in value:
            out.extend(_flatten_numbers(item))
        return out
    return []


def _mean(value: Any, default: float = 0.0) -> float:
    items = _flatten_numbers(value)
    if not items:
        return default
    return sum(items) / len(items)


def _max(value: Any, default: float = 0.0) -> float:
    items = _flatten_numbers(value)
    if not items:
        return default
    return max(items)


def _max_or_none(value: Any) -> float | None:
    items = _flatten_numbers(value)
    if not items:
        return None
    return max(items)


def _min(value: Any, default: float = 1.0) -> float:
    items = _flatten_numbers(value)
    if not items:
        return default
    return min(items)


def _add_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _more_severe(action_a: str, action_b: str) -> str:
    if _ACTION_SEVERITY[action_a] >= _ACTION_SEVERITY[action_b]:
        return action_a
    return action_b


class GenerationReadinessGate(nn.Module):
    """Convert CAS diagnostic signals into a generation-readiness policy.

    The gate consumes already-computed signals from CASNativeModel and the
    Verification Stack. It does not alter hidden states, bottleneck vectors,
    logits, or generated tokens. Product code can use its output to decide
    whether to emit normally, add caveats, switch to constrained decoding, or
    suppress unsupported free-form generation.
    """

    def __init__(self, config: GenerationReadinessConfig | None = None):
        super().__init__()
        self.config = config or GenerationReadinessConfig()
        _validate_mode(self.config.mode)

    def forward(
        self,
        *,
        lacunarity_scores: Any = None,
        lacunarity_meta: dict[str, Any] | None = None,
        inversion_flags: Any = None,
        rpm_satisfaction: Any = None,
        verification: dict[str, Any] | None = None,
        mode: str | None = None,
    ) -> GenerationReadinessResult:
        """Alias for :meth:`assess` so the class behaves like a module."""
        return self.assess(
            lacunarity_scores=lacunarity_scores,
            lacunarity_meta=lacunarity_meta,
            inversion_flags=inversion_flags,
            rpm_satisfaction=rpm_satisfaction,
            verification=verification,
            mode=mode,
        )

    def assess(
        self,
        *,
        lacunarity_scores: Any = None,
        lacunarity_meta: dict[str, Any] | None = None,
        inversion_flags: Any = None,
        rpm_satisfaction: Any = None,
        verification: dict[str, Any] | None = None,
        mode: str | None = None,
    ) -> GenerationReadinessResult:
        """Score readiness and return an auditable policy result."""
        active_mode = _validate_mode(mode or self.config.mode)
        lacunarity_meta = lacunarity_meta or {}
        verification = verification or {}

        risk = 0.0
        reasons: list[str] = []
        evidence: dict[str, float | int | str | bool] = {"mode": active_mode}
        forced_action: str | None = None

        accepted = verification.get("accepted")
        if accepted is False:
            _add_reason(reasons, "verification_stack_rejected")
            for reason in verification.get("suppression_reasons", []) or []:
                _add_reason(reasons, f"verification:{reason}")
            if active_mode == MAX_COVERAGE_TRIAGE:
                risk = max(risk, 0.66)
                forced_action = CONSTRAIN
            else:
                risk = max(risk, 0.90)
                forced_action = SUPPRESS
            evidence["verification_accepted"] = False
        elif accepted is True:
            evidence["verification_accepted"] = True

        decision_tier = str(verification.get("decision_tier", "")).lower()
        if decision_tier in {"medium", "diagnostic", "triage"}:
            risk += 0.25
            _add_reason(reasons, f"verification_tier_{decision_tier}")
        elif decision_tier in {"low", "conflicted", "uncertain"}:
            risk += 0.25
            _add_reason(reasons, f"verification_tier_{decision_tier}")

        lacunarity_value = _max_or_none(lacunarity_scores)
        if lacunarity_value is None:
            lacunarity_value = max(
                abs(_max(lacunarity_meta.get("lacunarity"), default=0.0)),
                abs(_min(lacunarity_meta.get("lacunarity"), default=0.0)),
            )
        evidence["max_lacunarity"] = float(lacunarity_value)
        if lacunarity_value >= self.config.lacunarity_high:
            risk += 0.35
            _add_reason(reasons, "high_lacunarity")
        elif lacunarity_value >= self.config.lacunarity_warn:
            risk += 0.15
            _add_reason(reasons, "elevated_lacunarity")

        gap_max = _max(lacunarity_meta.get("gap_map"), default=0.0)
        gap_mean = _mean(lacunarity_meta.get("gap_map"), default=0.0)
        evidence["max_gap_probability"] = gap_max
        evidence["mean_gap_probability"] = gap_mean
        if gap_max >= self.config.gap_high:
            risk += 0.30
            _add_reason(reasons, "high_gap_probability")
        elif gap_max >= self.config.gap_warn or gap_mean >= self.config.gap_warn:
            risk += 0.15
            _add_reason(reasons, "elevated_gap_probability")

        min_domain_conf = _min(lacunarity_meta.get("domain_confidence"), default=1.0)
        evidence["min_domain_confidence"] = min_domain_conf
        if min_domain_conf < self.config.domain_confidence_low:
            risk += 0.25
            _add_reason(reasons, "low_domain_confidence")
        elif min_domain_conf < self.config.domain_confidence_warn:
            risk += 0.10
            _add_reason(reasons, "reduced_domain_confidence")

        inversion_values = _flatten_numbers(inversion_flags)
        inversion_count = sum(
            1 for value in inversion_values
            if value >= self.config.inversion_flag_threshold
        )
        evidence["inversion_flag_count"] = inversion_count
        if inversion_count:
            risk += min(0.40, 0.12 * inversion_count)
            _add_reason(reasons, "inversion_flags_present")

        rpm_value = _mean(rpm_satisfaction, default=1.0)
        evidence["rpm_satisfaction"] = rpm_value
        if rpm_value < self.config.rpm_low:
            risk += 0.25
            _add_reason(reasons, "low_rpm_satisfaction")
        elif rpm_value < self.config.rpm_warn:
            risk += 0.10
            _add_reason(reasons, "reduced_rpm_satisfaction")

        risk = max(0.0, min(1.0, risk))
        thresholds = _MODE_THRESHOLDS[active_mode]
        if risk >= thresholds["suppress"]:
            action = SUPPRESS
        elif risk >= thresholds["constrain"]:
            action = CONSTRAIN
        elif risk >= thresholds["caveat"]:
            action = CAVEAT
        else:
            action = ALLOW

        if forced_action is not None:
            action = _more_severe(action, forced_action)

        recommended_mode = active_mode
        if action in {CONSTRAIN, SUPPRESS} and active_mode != HIGH_PRECISION:
            recommended_mode = HIGH_PRECISION
        elif action == CAVEAT and active_mode == MAX_COVERAGE_TRIAGE:
            recommended_mode = BALANCED

        if not reasons:
            reasons.append("all_readiness_signals_within_mode_thresholds")

        return GenerationReadinessResult(
            generation_readiness=action,
            risk_score=round(risk, 6),
            reasons=tuple(reasons),
            recommended_mode=recommended_mode,
            mode=active_mode,
            evidence=evidence,
        )
