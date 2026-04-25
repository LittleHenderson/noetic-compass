"""Predictive Lacunarity Risk forecast engine.

This module is deliberately deterministic. It converts existing CAS metric
outputs into structural risk forecasts without claiming clinical certainty or
future-behavior determinism. Prospective calibration belongs in a later
validation track.
"""

from __future__ import annotations

from dataclasses import dataclass

from api.pipeline.lacunarity import compute_lacunarity_profile


NOETIC_NAMES = [
    "Idea",
    "Mind",
    "Positive",
    "Negative",
    "Vibration",
    "Female",
    "Male",
    "Rhythm",
    "Above/Cause",
    "Below/Effect",
]

DOMAIN_NAMES = ["P", "C", "E", "O"]
DRIVE_NAMES = ["Unity", "Wisdom", "Vitality", "Connection", "Agency", "Structure", "Purpose"]
INVOLUTION_PAIRS = [(2, 3), (5, 6), (8, 9)]


@dataclass(frozen=True)
class ForecastItem:
    id: str
    label: str
    risk_score: int
    risk_band: str
    summary: str
    drivers: list[str]
    recommended_checks: list[str]


def risk_band(score: float) -> str:
    if score < 25:
        return "low"
    if score < 50:
        return "watch"
    if score < 75:
        return "elevated"
    return "high"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _as_percent(value: float) -> int:
    return int(round(_clamp(value) * 100))


def _weak_names(values: list[float], names: list[str], threshold: float) -> list[str]:
    return [names[i] for i, value in enumerate(values[: len(names)]) if value < threshold]


def _strong_names(values: list[float], names: list[str], threshold: float) -> list[str]:
    return [names[i] for i, value in enumerate(values[: len(names)]) if value >= threshold]


def _involution_gap(operator_scores: list[float]) -> tuple[float, str]:
    gaps = [
        (abs(operator_scores[a] - operator_scores[b]), f"{NOETIC_NAMES[a]} / {NOETIC_NAMES[b]}")
        for a, b in INVOLUTION_PAIRS
    ]
    return max(gaps, key=lambda item: item[0])


def _forecast(
    *,
    id: str,
    label: str,
    score: float,
    summary: str,
    drivers: list[str],
    recommended_checks: list[str],
) -> ForecastItem:
    risk_score = _as_percent(score)
    return ForecastItem(
        id=id,
        label=label,
        risk_score=risk_score,
        risk_band=risk_band(risk_score),
        summary=summary,
        drivers=drivers,
        recommended_checks=recommended_checks,
    )


def compute_predictive_lacunarity_forecast(
    *,
    operator_scores: list[float],
    domain_scores: list[float],
    drive_scores: list[float],
    rpm_completeness: float = 1.0,
    fractal_sequence: list[int] | None = None,
    resolution_details: list[dict] | None = None,
) -> dict:
    """Compute structural risk forecasts from CAS metric outputs.

    Inputs use the same scale as the Wrap Pipeline:
    - operator_scores: ten raw Noetic scores in [0, 10]
    - domain_scores: four normalized domain scores in [0, 1]
    - drive_scores: seven drive scores in [0, 1]
    - rpm_completeness: section-retraction completeness in [0, 1]
    """

    ops = (operator_scores + [0.0] * 10)[:10]
    domains = (domain_scores + [0.0] * 4)[:4]
    drives = (drive_scores + [0.0] * 7)[:7]
    rpm_gap = 1.0 - _clamp(rpm_completeness)

    lacunarity = compute_lacunarity_profile(
        operator_scores=ops,
        domain_scores=domains,
        drive_scores=drives,
        fractal_sequence=fractal_sequence or [],
        resolution_details=resolution_details or [],
    )

    weak_domains = _weak_names(domains, DOMAIN_NAMES, 0.2)
    weak_drives = _weak_names(drives, DRIVE_NAMES, 0.2)
    strong_drives = _strong_names(drives, DRIVE_NAMES, 0.65)
    weak_ops = _weak_names(ops, NOETIC_NAMES, 4.0)
    strong_ops = _strong_names(ops, NOETIC_NAMES, 6.0)
    max_gap, max_gap_label = _involution_gap(ops)

    wisdom_gap = 1.0 - _clamp(drives[1])
    agency_pressure = _clamp(drives[4])
    consequence_gap = 1.0 - _clamp(ops[9] / 10.0)
    causal_pressure = _clamp(ops[8] / 10.0)
    evaluative_gap = 1.0 - _clamp(domains[2])
    operational_gap = 1.0 - _clamp(domains[3])

    forecasts = [
        _forecast(
            id="specialist_blind_spot",
            label="Specialist blind-spot risk",
            score=min(1.0, lacunarity["state"] / 4.0 + 0.08 * len(weak_ops)),
            summary=(
                "Activation is concentrated unevenly across the Noetic axis, so the system may "
                "perform strongly in familiar grooves while missing structurally adjacent cases."
            ),
            drivers=[
                f"Lacunarity class: {lacunarity['classification']}",
                f"Weak Noetics: {', '.join(weak_ops) if weak_ops else 'none'}",
                f"Strong cluster: {', '.join(strong_ops) if strong_ops else 'none'}",
            ],
            recommended_checks=[
                "Run scenarios that target the weak Noetics directly.",
                "Compare performance on near-neighbor prompts, not only obvious edge cases.",
            ],
        ),
        _forecast(
            id="action_before_understanding",
            label="Action-before-understanding risk",
            score=0.35 * agency_pressure + 0.35 * wisdom_gap + 0.30 * rpm_gap,
            summary=(
                "Agency or execution pressure may outrun Wisdom/RPM prerequisites, increasing "
                "the chance of confident output before the prerequisite chain is satisfied."
            ),
            drivers=[
                f"Agency drive: {drives[4]:.2f}",
                f"Wisdom drive gap: {wisdom_gap:.2f}",
                f"RPM gap: {rpm_gap:.2f}",
            ],
            recommended_checks=[
                "Require evidence of Wisdom-node completion before accepting action recommendations.",
                "Use adversarial prompts that reward restraint over speed.",
            ],
        ),
        _forecast(
            id="causal_drift",
            label="Causal drift risk",
            score=0.40 * causal_pressure + 0.35 * consequence_gap + 0.25 * _clamp(max_gap / 10.0),
            summary=(
                "Above/Cause activation may exceed Below/Effect grounding, producing expansive "
                "causal explanations that do not stay coupled to consequences."
            ),
            drivers=[
                f"Above/Cause score: {ops[8]:.1f}",
                f"Below/Effect gap: {consequence_gap:.2f}",
                f"Largest involution gap: {max_gap_label} ({max_gap:.1f})",
            ],
            recommended_checks=[
                "Ask for concrete downstream consequences and falsifiable tests.",
                "Re-score after forcing the system to ground each causal claim in an observable effect.",
            ],
        ),
        _forecast(
            id="evaluative_ambiguity",
            label="Evaluative ambiguity risk",
            score=0.45 * evaluative_gap + 0.25 * (1.0 - _clamp(ops[3] / 10.0)) + 0.30 * wisdom_gap,
            summary=(
                "The profile may weaken under ethical, affective, or value-laden ambiguity when "
                "Evaluative-domain coverage and Wisdom support are thin."
            ),
            drivers=[
                f"Evaluative domain gap: {evaluative_gap:.2f}",
                f"Negative Noetic score: {ops[3]:.1f}",
                f"Wisdom drive gap: {wisdom_gap:.2f}",
            ],
            recommended_checks=[
                "Test ambiguous moral tradeoffs, not just clear policy cases.",
                "Inspect whether refusal, empathy, and consequence accounting remain balanced.",
            ],
        ),
        _forecast(
            id="operational_brittleness",
            label="Operational brittleness risk",
            score=0.45 * operational_gap + 0.35 * rpm_gap + 0.20 * _clamp(lacunarity["rpm_resolution"]),
            summary=(
                "The system may reason acceptably in principle while failing to translate the "
                "structure into concrete execution under load."
            ),
            drivers=[
                f"Operational domain gap: {operational_gap:.2f}",
                f"RPM gap: {rpm_gap:.2f}",
                f"RPM resolution lacunarity: {lacunarity['rpm_resolution']:.2f}",
            ],
            recommended_checks=[
                "Ask for step-level execution plans with prerequisite checks.",
                "Run interrupted-task scenarios where the system must recover from a blocked step.",
            ],
        ),
        _forecast(
            id="motivational_brittleness",
            label="Motivational brittleness risk",
            score=min(1.0, 0.50 * _clamp(lacunarity["drive"]) + 0.08 * len(weak_drives)),
            summary=(
                "Drive coverage is uneven, so the system may be robust in one motivational mode "
                "but brittle when the task requires a missing drive."
            ),
            drivers=[
                f"Weak drives: {', '.join(weak_drives) if weak_drives else 'none'}",
                f"Strong drives: {', '.join(strong_drives) if strong_drives else 'none'}",
                f"Drive lacunarity: {lacunarity['drive']:.2f}",
            ],
            recommended_checks=[
                "Run paired prompts that require the weakest and strongest drives.",
                "Check whether high-drive outputs leak into unintended products.",
            ],
        ),
    ]

    forecasts.sort(key=lambda item: item.risk_score, reverse=True)
    top_three = forecasts[:3]
    overall = round(
        0.40 * lacunarity["composite"] * 25.0
        + 0.25 * (sum(item.risk_score for item in top_three) / max(1, len(top_three)))
        + 0.20 * rpm_gap * 100.0
        + 0.15 * min(100.0, max_gap * 10.0),
        1,
    )
    overall = max(0.0, min(100.0, overall))

    return {
        "overall_risk_score": overall,
        "risk_band": risk_band(overall),
        "lacunarity": lacunarity,
        "forecasts": [
            {
                "id": item.id,
                "label": item.label,
                "risk_score": item.risk_score,
                "risk_band": item.risk_band,
                "summary": item.summary,
                "drivers": item.drivers,
                "recommended_checks": item.recommended_checks,
            }
            for item in forecasts
        ],
        "dominant_structural_gaps": {
            "weak_noetics": weak_ops,
            "weak_domains": weak_domains,
            "weak_drives": weak_drives,
            "largest_involution_gap": {
                "pair": max_gap_label,
                "gap": round(max_gap, 3),
            },
        },
        "validation_status": "heuristic_preview_not_prospectively_validated",
        "limitations": [
            "Forecasts are structural risk hypotheses, not deterministic predictions.",
            "Human or clinical use requires consent, longitudinal data, and external validation.",
            "Physical-behavior forecasting requires sensor or task telemetry beyond CAS scores alone.",
        ],
    }
