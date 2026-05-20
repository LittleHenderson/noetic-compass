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
_PROFILE_KEYS = ("foundation", "drive", "register")
_PROFILE_SCHEMA_KEYS = ("vote_count", "conflict_count")
_PRE_PROFILE_STAGES = {"foundation_ensemble"}
_PRE_TRACE_STAGES = {
    "foundation_ensemble",
    "drive_ensemble",
    "register_ensemble",
    "factor_consistency",
}


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
        state = str(trace.get("state") if isinstance(trace, dict) else trace).lower()
        if state in {"uncertain", "conflicted"}:
            risky += 1
        elif state not in {"stable", "drifting", "uncertain", "conflicted"}:
            raise ValueError("unknown_trace_state")
    return _clamp01(risky / len(trace_states))


def _rpm_risk(row: dict[str, Any]) -> float:
    value = row.get("rpm_satisfaction")
    if value is None:
        raise ValueError("missing_rpm_satisfaction")
    return _clamp01(1.0 - float(value))


def _not_available(reason: str) -> dict[str, Any]:
    return {
        "axis_order": list(INVERSION_AXES),
        "axis_scores": [None] * len(INVERSION_AXES),
        "flagged_axes": [],
        "flag_count": None,
        "max_axis_score": None,
        "decision": "not_available",
        "attribution_status": "not_available",
        "source": "stage22_6_runtime_structural_proxy_scanner",
        "reason": reason,
        "boundary": (
            "Inversion proxy scanning requires gap_map_summary with foundation, "
            "drive, register, trace_states, and rpm_satisfaction. Missing runtime "
            "inputs are explicit not_available, not silent zero-risk rows."
        ),
    }


def _is_unreached_row(row: dict[str, Any], stages: set[str]) -> bool:
    return str(row.get("stage") or "") in stages and bool(row.get("reason"))


def _validate_gap(row: dict[str, Any], gap: Any) -> str | None:
    if not isinstance(gap, dict):
        return "missing_gap_map_summary"
    for key in _PROFILE_KEYS:
        profile = gap.get(key)
        if not isinstance(profile, dict):
            return f"missing_{key}_profile"
        missing_profile_keys = [schema_key for schema_key in _PROFILE_SCHEMA_KEYS if schema_key not in profile]
        if missing_profile_keys:
            return f"malformed_{key}_profile"
        vote_count = int(profile.get("vote_count", 0) or 0)
        if vote_count <= 0 and not _is_unreached_row(row, _PRE_PROFILE_STAGES):
            return f"empty_{key}_profile"
    trace_states = gap.get("trace_states")
    if not isinstance(trace_states, dict):
        return "missing_trace_states"
    if not trace_states and not _is_unreached_row(row, _PRE_TRACE_STAGES):
        return "empty_trace_states"
    return None


def scan_inversion_from_diagnostic_row(row: dict[str, Any]) -> dict[str, Any]:
    """Compute seven deterministic inversion-risk proxy scores for one row."""
    gap = row.get("gap_map_summary")
    invalid_reason = _validate_gap(row, gap)
    if invalid_reason is not None:
        return _not_available(invalid_reason)
    if row.get("rpm_satisfaction") is None:
        return _not_available("missing_rpm_satisfaction")
    foundation_profile = gap.get("foundation") or {}
    drive_profile = gap.get("drive") or {}
    register_profile = gap.get("register") or {}
    trace_states = gap.get("trace_states") or {}

    try:
        n_risk = _profile_lac(foundation_profile)
        w_risk = _trace_risk(trace_states)
        f_risk = _profile_lac(drive_profile)
        e_risk = max(w_risk, _clamp01((n_risk + f_risk) / 2.0))
        s_risk = _profile_lac(register_profile)
        a_risk = _rpm_risk(row)
    except ValueError as exc:
        return _not_available(str(exc))
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
