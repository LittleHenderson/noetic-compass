"""Stage 22.6 deterministic inversion proxy scanner.

The scanner is deliberately runtime-only: it uses verifier diagnostics already
available in Stage 22.4 rows and never reads gold labels. The seven scores are
inversion-risk proxies in [0, 1], not a full semantic inversion theorem.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

INVERSION_AXES = ("N", "W", "F", "E", "S", "A", "P")
FLAG_THRESHOLD = 0.25


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _risk_decision(max_risk: float, flag_count: int) -> str:
    if max_risk <= 0.10 and flag_count == 0:
        return "allow"
    if max_risk <= 0.25 and flag_count <= 1:
        return "caveat"
    if max_risk <= 0.50 and flag_count <= 3:
        return "constrain"
    return "suppress"


def _profile_lac(profile: dict[str, Any]) -> float:
    vote_count = int(profile.get("vote_count", 0) or 0)
    if vote_count <= 0:
        return 0.0
    return _clamp01(float(profile.get("conflict_count", 0) or 0) / vote_count)


def _trace_risk(trace_states: dict[str, Any]) -> float:
    if not trace_states:
        return 0.0
    risky = 0
    for trace in trace_states.values():
        if str(trace).lower() in {"uncertain", "conflicted"}:
            risky += 1
        elif isinstance(trace, dict) and str(trace.get("state")) in {"uncertain", "conflicted"}:
            risky += 1
    return _clamp01(risky / len(trace_states))


def _rpm_risk(row: dict[str, Any]) -> float:
    value = row.get("rpm_satisfaction")
    if value is None:
        return 0.5
    return _clamp01(1.0 - float(value))


def scan_inversion_from_diagnostic_row(row: dict[str, Any]) -> dict[str, Any]:
    """Compute seven deterministic inversion-risk proxy scores for one row."""
    gap = row.get("gap_map_summary") or {}
    foundation_profile = gap.get("foundation") or {}
    drive_profile = gap.get("drive") or {}
    register_profile = gap.get("register") or {}
    trace_states = gap.get("trace_states") or {}

    n_risk = _profile_lac(foundation_profile)
    w_risk = _trace_risk(trace_states)
    f_risk = _profile_lac(drive_profile)
    e_risk = max(w_risk, _clamp01((n_risk + f_risk) / 2.0))
    s_risk = _profile_lac(register_profile)
    a_risk = _rpm_risk(row)
    p_risk = _clamp01(mean([n_risk, w_risk, f_risk, e_risk, s_risk, a_risk]))

    scores = [_clamp01(x) for x in (n_risk, w_risk, f_risk, e_risk, s_risk, a_risk, p_risk)]
    flags = [axis for axis, score in zip(INVERSION_AXES, scores) if score > FLAG_THRESHOLD]
    max_risk = max(scores) if scores else 0.0
    return {
        "axis_order": list(INVERSION_AXES),
        "axis_scores": scores,
        "flagged_axes": flags,
        "flag_count": len(flags),
        "max_axis_score": max_risk,
        "decision": _risk_decision(max_risk, len(flags)),
        "attribution_status": "numeric_measured",
        "source": "stage22_6_runtime_structural_proxy_scanner",
        "boundary": (
            "Scores are deterministic runtime inversion-risk proxies derived from "
            "readout disagreement, trace instability, register/drive/foundation "
            "concentration, and RPM factor recomposition. They are not gold-label "
            "correctness and not a full semantic inversion theorem."
        ),
    }
