"""Shadow-only structural monitoring rollups for CAS Harness fleets.

This module turns optional worker-submitted structural snapshots into a
claim-safe fleet summary. It is observation and review support only: no result
from this lane can mint ACCEPT/SUPPRESS or upgrade hidden-state claims.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "cas_harness_structural_monitoring.v0.shadow"
CLAIM_CEILING = (
    "Structural/fleet monitoring is shadow-only evidence review. It can record "
    "measured, derived, assigned, unavailable, or drifted signals and route "
    "anomalies to FLAG_FOR_HUMAN_REVIEW with verdict_effect none_shadow_only. "
    "It does not mint ACCEPT/SUPPRESS, certify safety, prove internal hidden-state "
    "prompt-injection or hallucination detection, prevent/removal/reversal, live "
    "pre-speech interception, autonomous remediation, or causal control."
)

_BASIS_VALUES = {"measured", "derived", "assigned", "unavailable"}
_STATUS_VALUES = {"present", "FLAG_FOR_HUMAN_REVIEW", "unavailable"}


def fleet_structural_monitoring_summary(jobs: Iterable[Any]) -> dict[str, Any]:
    """Aggregate optional structural snapshots from completed fleet jobs."""

    job_list = list(jobs)
    signals: list[dict[str, Any]] = []
    completed_jobs = [job for job in job_list if getattr(job, "status", None) == "completed"]
    missing_signal_count = 0
    review_reasons: list[str] = []

    for job in completed_jobs:
        payload = getattr(job, "evidence_packet_fragment_payload", None)
        snapshot = _extract_structural_snapshot(payload)
        if snapshot is None:
            missing_signal_count += 1
            continue
        signal = _signal_from_snapshot(job, snapshot)
        signals.append(signal)
        if signal["status"] == "FLAG_FOR_HUMAN_REVIEW":
            review_reasons.extend(signal["issues"])

    measured_count = sum(1 for signal in signals if signal["basis"] == "measured")
    derived_count = sum(1 for signal in signals if signal["basis"] == "derived")
    assigned_count = sum(1 for signal in signals if signal["basis"] == "assigned")
    unavailable_count = sum(1 for signal in signals if signal["basis"] == "unavailable")
    malformed_count = sum(1 for signal in signals if signal["malformed"])
    drifted_count = sum(1 for signal in signals if signal["drift_breach"])
    max_drift_score = _max_optional_float(signal["drift_score"] for signal in signals)

    if not signals:
        status = "unavailable"
        route = "none"
        basis = "unavailable"
    elif review_reasons:
        status = "FLAG_FOR_HUMAN_REVIEW"
        route = "FLAG_FOR_HUMAN_REVIEW"
        basis = _summary_basis(signals)
    else:
        status = "present"
        route = "none"
        basis = _summary_basis(signals)

    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "shadow",
        "status": status,
        "verdict_effect": "none_shadow_only",
        "route": route,
        "scope": "distributed_fleet",
        "basis": basis,
        "summary": {
            "total_jobs": len(job_list),
            "completed_fragments": len(completed_jobs),
            "signal_count": len(signals),
            "measured_signal_count": measured_count,
            "derived_signal_count": derived_count,
            "assigned_signal_count": assigned_count,
            "unavailable_signal_count": unavailable_count,
            "missing_signal_count": missing_signal_count,
            "malformed_signal_count": malformed_count,
            "drifted_signal_count": drifted_count,
            "max_drift_score": max_drift_score,
            "baseline_coverage_count": sum(
                1 for signal in signals if signal.get("baseline_signature_sha256")
            ),
        },
        "review_reasons": _dedupe(review_reasons),
        "signals": signals,
        "claim_ceiling": CLAIM_CEILING,
    }


def _extract_structural_snapshot(payload: Any) -> Mapping[str, Any] | None:
    if not isinstance(payload, Mapping):
        return None
    direct = payload.get("structural_monitoring")
    if isinstance(direct, Mapping):
        return direct
    telemetry = payload.get("telemetry")
    if isinstance(telemetry, Mapping):
        cjt = telemetry.get("cjt_fleet_diagnostics")
        if isinstance(cjt, Mapping):
            return cjt
    return None


def _signal_from_snapshot(job: Any, snapshot: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    mode = _clean_string(snapshot.get("mode")) or "shadow"
    if mode != "shadow":
        issues.append("structural_monitoring.mode must be shadow")

    verdict_effect = _clean_string(snapshot.get("verdict_effect")) or "none_shadow_only"
    if verdict_effect != "none_shadow_only":
        issues.append("structural monitoring cannot affect verdicts")

    basis = _clean_string(snapshot.get("basis")) or _clean_string(snapshot.get("provenance_kind"))
    if basis not in _BASIS_VALUES:
        issues.append("structural_monitoring.basis must be measured, derived, assigned, or unavailable")
        basis = "unavailable"
    elif basis == "assigned":
        issues.append("assigned-only structural mapping is not model-internal evidence")

    status = _clean_string(snapshot.get("status")) or "present"
    if status not in _STATUS_VALUES:
        issues.append("structural_monitoring.status is malformed")
        status = "FLAG_FOR_HUMAN_REVIEW"

    route = _clean_string(snapshot.get("route")) or "none"
    drift_score = _optional_float(snapshot.get("drift_score"))
    drift_threshold = _optional_float(snapshot.get("drift_threshold"))
    drift_breach = (
        drift_score is not None
        and drift_threshold is not None
        and drift_score > drift_threshold
    )
    if drift_breach:
        issues.append("structural drift_score exceeded drift_threshold")

    raw_claim_ceiling = _clean_string(snapshot.get("claim_ceiling"))
    if not raw_claim_ceiling:
        issues.append("structural_monitoring.claim_ceiling is required")

    source_status = status
    if issues or route == "FLAG_FOR_HUMAN_REVIEW" or source_status == "FLAG_FOR_HUMAN_REVIEW":
        status = "FLAG_FOR_HUMAN_REVIEW"

    signal_id = _clean_string(snapshot.get("id")) or _clean_string(snapshot.get("signal_id"))
    if not signal_id:
        signal_id = f"{getattr(job, 'assigned_worker_id', 'unknown')}:{getattr(job, 'shard_id', 'unknown')}"

    return {
        "id": signal_id,
        "job_id": getattr(job, "job_id", None),
        "worker_id": getattr(job, "assigned_worker_id", None),
        "shard_id": getattr(job, "shard_id", None),
        "layer_start": getattr(job, "layer_start", None),
        "layer_end": getattr(job, "layer_end", None),
        "status": status,
        "source_status": source_status,
        "route": "FLAG_FOR_HUMAN_REVIEW" if status == "FLAG_FOR_HUMAN_REVIEW" else "none",
        "basis": basis,
        "mode": mode,
        "verdict_effect": "none_shadow_only",
        "drift_score": drift_score,
        "drift_threshold": drift_threshold,
        "drift_breach": drift_breach,
        "baseline_trace_id": _clean_string(snapshot.get("baseline_trace_id")),
        "current_signature_sha256": _clean_string(snapshot.get("current_signature_sha256")),
        "baseline_signature_sha256": _clean_string(snapshot.get("baseline_signature_sha256")),
        "evidence_packet_fragment_ref": getattr(job, "evidence_packet_fragment_ref", None),
        "malformed": bool(issues),
        "issues": _dedupe(issues),
        "claim_ceiling": raw_claim_ceiling or CLAIM_CEILING,
    }


def _summary_basis(signals: list[dict[str, Any]]) -> str:
    bases = {signal["basis"] for signal in signals}
    if len(bases) == 1:
        return next(iter(bases))
    if "measured" in bases:
        return "mixed_measured"
    return "mixed"


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _max_optional_float(values: Iterable[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out
