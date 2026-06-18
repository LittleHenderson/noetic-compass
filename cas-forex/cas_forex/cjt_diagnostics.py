"""A-1: CJT diagnostic mapper.

Converts existing CAS Forex conditions (forecast disagreement, weak edge,
single-model overconfidence, macro shock, drawdown, broker mismatch, beta
drift) into evidence-only ``CjtCircuitDiagnostic`` sidecars.

Claim boundary: every diagnostic produced here can only *explain*, ``SUPPRESS``,
``FLAG_FOR_HUMAN_REVIEW``, or contribute to ``LIVE_LOCKED``. There is no path to
``ACCEPT`` — the schema (``CjtClaimCeiling`` has no ACCEPT value, and
``CjtCircuitDiagnostic`` blocks ``can_create_broker_accept``) enforces this.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from cas_forex.schemas.cjt import (
    CjtCircuitDiagnostic,
    CjtClaimCeiling,
    CjtDiagnosticKind,
    CjtObservation,
    CjtRegion,
)

# Which claim ceiling each diagnostic kind is allowed to express. None of these
# is ACCEPT; this table is the single place the routing policy lives.
_CEILING_BY_KIND: dict[CjtDiagnosticKind, CjtClaimCeiling] = {
    CjtDiagnosticKind.FORECAST_DISAGREEMENT: CjtClaimCeiling.FLAG_FOR_HUMAN_REVIEW,
    CjtDiagnosticKind.WEAK_EDGE: CjtClaimCeiling.SUPPRESS,
    CjtDiagnosticKind.SINGLE_MODEL_OVERCONFIDENCE: CjtClaimCeiling.FLAG_FOR_HUMAN_REVIEW,
    CjtDiagnosticKind.MACRO_SHOCK: CjtClaimCeiling.LIVE_LOCKED,
    CjtDiagnosticKind.DRAWDOWN_OVERLOAD: CjtClaimCeiling.LIVE_LOCKED,
    CjtDiagnosticKind.BROKER_MISMATCH: CjtClaimCeiling.FLAG_FOR_HUMAN_REVIEW,
    CjtDiagnosticKind.BETA_DRIFT: CjtClaimCeiling.FLAG_FOR_HUMAN_REVIEW,
    CjtDiagnosticKind.GENERAL: CjtClaimCeiling.OPEN,
}


def build_observation(
    trace_id: str,
    kind: CjtDiagnosticKind,
    *,
    cause_ref: str,
    bias_ref: str,
    effect_ref: str,
    region: CjtRegion,
    beta_estimate: Optional[float] = None,
    beta_source: str = "heuristic",
    confidence: float = 0.0,
    evidence_refs: Optional[list[str]] = None,
    evidence: Optional[Mapping[str, Any]] = None,
    notes: Optional[list[str]] = None,
    index: int = 0,
) -> CjtObservation:
    """Build a single traceable cause/bias/effect observation."""

    return CjtObservation(
        observation_id=f"{trace_id}:obs:{kind.value}:{index}",
        cause_ref=cause_ref,
        bias_ref=bias_ref,
        effect_ref=effect_ref,
        region=region,
        beta_estimate=beta_estimate,
        beta_source=beta_source,
        confidence=max(0.0, min(1.0, confidence)),
        claim_ceiling=_CEILING_BY_KIND.get(kind, CjtClaimCeiling.OPEN),
        evidence_refs=list(evidence_refs or []),
        evidence=dict(evidence or {}),
        notes=list(notes or []),
    )


def build_cjt_diagnostic(
    trace_id: str,
    kind: CjtDiagnosticKind,
    observations: list[CjtObservation],
    *,
    overall_region: CjtRegion = CjtRegion.UNKNOWN,
    evidence: Optional[Mapping[str, Any]] = None,
) -> CjtCircuitDiagnostic:
    """Assemble a claim-bounded circuit diagnostic from observations."""

    ceiling = _CEILING_BY_KIND.get(kind, CjtClaimCeiling.OPEN)
    return CjtCircuitDiagnostic(
        diagnostic_id=f"{trace_id}:cjt:{kind.value}",
        kind=kind,
        trace_id=trace_id,
        observations=observations,
        overall_region=overall_region,
        claim_ceiling=ceiling,
        # can_unlock_live_trading / can_create_broker_accept stay False; the
        # schema validator raises if either is flipped on.
        evidence=dict(evidence or {}),
    )


# ---- Condition-specific mappers ----


def forecast_disagreement_diagnostic(
    trace_id: str,
    *,
    model_a_ref: str,
    model_b_ref: str,
    divergence: float,
    bias_ref: str = "system_constitution",
) -> CjtCircuitDiagnostic:
    """Two models disagree → differential-pair imbalance."""

    obs = build_observation(
        trace_id,
        CjtDiagnosticKind.FORECAST_DISAGREEMENT,
        cause_ref=f"{model_a_ref} vs {model_b_ref}",
        bias_ref=bias_ref,
        effect_ref="differential_imbalance",
        region=CjtRegion.ACTIVE,
        beta_estimate=divergence,
        beta_source="forecast_divergence",
        confidence=min(1.0, divergence),
        notes=["Differential-pair imbalance: models disagree under shared bias."],
        evidence={"divergence": divergence},
    )
    return build_cjt_diagnostic(
        trace_id, CjtDiagnosticKind.FORECAST_DISAGREEMENT, [obs],
        overall_region=CjtRegion.ACTIVE,
    )


def weak_edge_diagnostic(
    trace_id: str,
    *,
    edge_strength: float,
    threshold: float,
    cause_ref: str = "forecast_signal",
    bias_ref: str = "baseline_controls",
) -> CjtCircuitDiagnostic:
    """Edge below baseline → cutoff (signal did not conduct into a trade)."""

    obs = build_observation(
        trace_id,
        CjtDiagnosticKind.WEAK_EDGE,
        cause_ref=cause_ref,
        bias_ref=bias_ref,
        effect_ref="no_trade",
        region=CjtRegion.CUTOFF,
        beta_estimate=0.0,
        beta_source="edge_vs_threshold",
        confidence=1.0 if edge_strength < threshold else 0.0,
        notes=[
            f"Cutoff: edge {edge_strength:g} below baseline threshold {threshold:g}; "
            "forecast did not conduct."
        ],
        evidence={"edge_strength": edge_strength, "threshold": threshold},
    )
    return build_cjt_diagnostic(
        trace_id, CjtDiagnosticKind.WEAK_EDGE, [obs], overall_region=CjtRegion.CUTOFF,
    )


def single_model_overconfidence_diagnostic(
    trace_id: str,
    *,
    model_ref: str,
    confidence: float,
    support_count: int,
    bias_ref: str = "single_model_bias",
) -> CjtCircuitDiagnostic:
    """One model very confident with thin support → high gain, low support."""

    beta = round(confidence * 20.0, 3)  # high gain proxy
    obs = build_observation(
        trace_id,
        CjtDiagnosticKind.SINGLE_MODEL_OVERCONFIDENCE,
        cause_ref=model_ref,
        bias_ref=bias_ref,
        effect_ref="overweighted_signal",
        region=CjtRegion.SATURATION if confidence >= 0.95 else CjtRegion.ACTIVE,
        beta_estimate=beta,
        beta_source="confidence_proxy",
        confidence=confidence,
        notes=[
            f"High gain (β≈{beta:g}) from one model with only {support_count} "
            "supporting signal(s)."
        ],
        evidence={"confidence": confidence, "support_count": support_count},
    )
    region = CjtRegion.SATURATION if confidence >= 0.95 else CjtRegion.ACTIVE
    return build_cjt_diagnostic(
        trace_id, CjtDiagnosticKind.SINGLE_MODEL_OVERCONFIDENCE, [obs],
        overall_region=region,
    )


def macro_shock_diagnostic(
    trace_id: str,
    *,
    event_ref: str,
    severity: float,
    bias_ref: str = "macro_context",
) -> CjtCircuitDiagnostic:
    """Macro shock → saturation/breakdown warning, route to LIVE_LOCKED."""

    region = CjtRegion.BREAKDOWN if severity >= 0.8 else CjtRegion.SATURATION
    obs = build_observation(
        trace_id,
        CjtDiagnosticKind.MACRO_SHOCK,
        cause_ref=event_ref,
        bias_ref=bias_ref,
        effect_ref="trading_lock",
        region=region,
        beta_estimate=severity,
        beta_source="macro_severity",
        confidence=severity,
        notes=[f"Macro shock severity {severity:g} → {region.value}."],
        evidence={"severity": severity},
    )
    return build_cjt_diagnostic(
        trace_id, CjtDiagnosticKind.MACRO_SHOCK, [obs], overall_region=region,
    )


def drawdown_overload_diagnostic(
    trace_id: str,
    *,
    drawdown_pct: float,
    limit_pct: float,
    bias_ref: str = "risk_budget",
) -> CjtCircuitDiagnostic:
    """Drawdown breach → power-management overload, route to LIVE_LOCKED."""

    obs = build_observation(
        trace_id,
        CjtDiagnosticKind.DRAWDOWN_OVERLOAD,
        cause_ref="cumulative_loss",
        bias_ref=bias_ref,
        effect_ref="brownout_lock",
        region=CjtRegion.BREAKDOWN,
        beta_estimate=None,
        beta_source="drawdown_vs_limit",
        confidence=1.0 if drawdown_pct >= limit_pct else 0.0,
        notes=[
            f"Power overload: drawdown {drawdown_pct:g}% vs limit {limit_pct:g}% "
            "→ brownout lock."
        ],
        evidence={"drawdown_pct": drawdown_pct, "limit_pct": limit_pct},
    )
    return build_cjt_diagnostic(
        trace_id, CjtDiagnosticKind.DRAWDOWN_OVERLOAD, [obs],
        overall_region=CjtRegion.BREAKDOWN,
    )


def broker_mismatch_diagnostic(
    trace_id: str,
    *,
    detail: str,
    bias_ref: str = "broker_link",
) -> CjtCircuitDiagnostic:
    """Broker disconnect / fill mismatch → circuit fault, flag for review."""

    obs = build_observation(
        trace_id,
        CjtDiagnosticKind.BROKER_MISMATCH,
        cause_ref="broker_event",
        bias_ref=bias_ref,
        effect_ref="circuit_fault",
        region=CjtRegion.BREAKDOWN,
        beta_source="broker_observation",
        confidence=1.0,
        notes=[f"Circuit fault: {detail}."],
        evidence={"detail": detail},
    )
    return build_cjt_diagnostic(
        trace_id, CjtDiagnosticKind.BROKER_MISMATCH, [obs],
        overall_region=CjtRegion.BREAKDOWN,
    )


def beta_drift_diagnostic(
    trace_id: str,
    *,
    prior_beta: float,
    current_beta: float,
    bias_ref: str = "harvester_history",
) -> CjtCircuitDiagnostic:
    """Edge that used to amplify profit now amplifies losses → beta drift."""

    obs = build_observation(
        trace_id,
        CjtDiagnosticKind.BETA_DRIFT,
        cause_ref="repeated_loss_signature",
        bias_ref=bias_ref,
        effect_ref="gain_recalibration_needed",
        region=CjtRegion.ACTIVE,
        beta_estimate=current_beta,
        beta_source="harvester_trend",
        confidence=min(1.0, abs(current_beta - prior_beta)),
        notes=[
            f"Beta drift: gain moved {prior_beta:g} → {current_beta:g} on the "
            "same path."
        ],
        evidence={"prior_beta": prior_beta, "current_beta": current_beta},
    )
    return build_cjt_diagnostic(
        trace_id, CjtDiagnosticKind.BETA_DRIFT, [obs], overall_region=CjtRegion.ACTIVE,
    )


def diagnostics_from_conditions(
    trace_id: str,
    conditions: Mapping[str, Any],
) -> list[CjtCircuitDiagnostic]:
    """Map a normalized conditions dict into a list of CJT diagnostics.

    Recognized keys (all optional):
      - ``forecast_disagreement``: {model_a_ref, model_b_ref, divergence}
      - ``weak_edge``: {edge_strength, threshold}
      - ``single_model_overconfidence``: {model_ref, confidence, support_count}
      - ``macro_shock``: {event_ref, severity}
      - ``drawdown_overload``: {drawdown_pct, limit_pct}
      - ``broker_mismatch``: {detail}
      - ``beta_drift``: {prior_beta, current_beta}
    """

    out: list[CjtCircuitDiagnostic] = []
    if "forecast_disagreement" in conditions:
        out.append(forecast_disagreement_diagnostic(trace_id, **conditions["forecast_disagreement"]))
    if "weak_edge" in conditions:
        out.append(weak_edge_diagnostic(trace_id, **conditions["weak_edge"]))
    if "single_model_overconfidence" in conditions:
        out.append(single_model_overconfidence_diagnostic(trace_id, **conditions["single_model_overconfidence"]))
    if "macro_shock" in conditions:
        out.append(macro_shock_diagnostic(trace_id, **conditions["macro_shock"]))
    if "drawdown_overload" in conditions:
        out.append(drawdown_overload_diagnostic(trace_id, **conditions["drawdown_overload"]))
    if "broker_mismatch" in conditions:
        out.append(broker_mismatch_diagnostic(trace_id, **conditions["broker_mismatch"]))
    if "beta_drift" in conditions:
        out.append(beta_drift_diagnostic(trace_id, **conditions["beta_drift"]))
    return out
