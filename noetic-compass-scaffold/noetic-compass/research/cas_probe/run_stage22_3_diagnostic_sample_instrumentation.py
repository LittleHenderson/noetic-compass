"""Stage 22.3 diagnostic sample instrumentation.

This runner adds the Stage 22.2 diagnostic contract to the row samples that
actually contain enough runtime data in the locked Stage 19B report. It does
not claim full-population attribution: Stage 19B suppressed rows mostly retain
only ``index`` and ``reason``, so the full verifier must be rerun with per-row
diagnostic emission before RPM/lacunarity/inversion can be measured across all
examples.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from stage22_2_diagnostic_instrumentation_spec import required_field_names

_HERE = Path(__file__).resolve().parent
_REGISTERS = ("T", "A", "f", "E")


def _resolve(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = _HERE / candidate
    return candidate


def _load_json(path: str) -> dict[str, Any]:
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _recompose(drive_label: str | None, register_label: str | None) -> str | None:
    if not drive_label or not register_label:
        return None
    if drive_label.startswith("F") and register_label in _REGISTERS:
        return f"{drive_label}{register_label}"
    return None


def _vote_profile(votes: dict[str, str] | None) -> dict[str, Any]:
    if not votes:
        return {
            "vote_count": 0,
            "unique_labels": 0,
            "max_vote_share": 0.0,
            "conflict_count": 0,
            "labels": [],
        }
    counts = Counter(votes.values())
    max_count = counts.most_common(1)[0][1]
    return {
        "vote_count": len(votes),
        "unique_labels": len(counts),
        "max_vote_share": max_count / len(votes),
        "conflict_count": len(votes) - max_count,
        "labels": sorted(counts),
    }


def _vote_lacunarity(profile: dict[str, Any]) -> float:
    if profile["vote_count"] == 0:
        return 0.0
    # Proxy only: conflict concentration over the three readout positions.
    return float(profile["conflict_count"] / profile["vote_count"])


def _decision_from_score(score: float) -> str:
    if score >= 0.85:
        return "allow"
    if score >= 0.65:
        return "caveat"
    if score >= 0.45:
        return "constrain"
    return "suppress"


def _lacunarity_decision(lacunarity: float) -> str:
    if lacunarity <= 0.0:
        return "allow"
    if lacunarity <= 0.34:
        return "caveat"
    if lacunarity <= 0.67:
        return "constrain"
    return "suppress"


def _instrument_accepted_row(model_key: str, row: dict[str, Any]) -> dict[str, Any]:
    foundation_votes = row.get("foundation_votes") or row.get("votes") or {}
    drive_votes = row.get("drive_votes") or {}
    register_votes = row.get("register_votes") or {}
    recomposed = _recompose(row.get("drive_prediction"), row.get("register_prediction"))
    prediction = row.get("prediction")
    factor_consistent = recomposed == prediction if recomposed is not None else None
    rpm_satisfaction = 1.0 if factor_consistent is True else 0.0 if factor_consistent is False else 0.5

    foundation_profile = _vote_profile(foundation_votes)
    drive_profile = _vote_profile(drive_votes)
    register_profile = _vote_profile(register_votes)
    foundation_lacunarity = _vote_lacunarity(foundation_profile)
    drive_lacunarity = _vote_lacunarity(drive_profile)
    register_lacunarity = _vote_lacunarity(register_profile)
    max_lacunarity = max(foundation_lacunarity, drive_lacunarity, register_lacunarity)

    rpm_decision = _decision_from_score(rpm_satisfaction)
    lac_decision = _lacunarity_decision(max_lacunarity)

    # No true inversion scan exists in the locked Stage 19B rows. Keep the
    # required field present with a non-attribution marker and do not score it.
    inversion_axis_scores: list[float | None] = [None] * 7
    inversion_gate_decision = "not_evaluated"

    gate_decisions = {
        "rpm_gate": {
            "decision": rpm_decision,
            "source": "drive_register_recomposition_runtime_proxy",
            "attribution_status": "proxy_measurable",
        },
        "lacunarity_gate": {
            "decision": lac_decision,
            "source": "readout_vote_lacunarity_proxy_not_neural_lacunarity_head",
            "attribution_status": "proxy_measurable",
        },
        "inversion_scan_gate": {
            "decision": inversion_gate_decision,
            "source": "not_recorded_in_locked_stage19b_rows",
            "attribution_status": "not_measurable",
        },
    }

    return {
        "model_key": model_key,
        "index": row.get("index"),
        "sample_id": row.get("sample_id"),
        "prediction": prediction,
        "confidence_tier": row.get("confidence_tier"),
        "rpm_satisfaction": rpm_satisfaction,
        "rpm_gate_decision": rpm_decision,
        "lacunarity_scores": {
            "foundation_vote_lacunarity": foundation_lacunarity,
            "drive_vote_lacunarity": drive_lacunarity,
            "register_vote_lacunarity": register_lacunarity,
            "max_vote_lacunarity": max_lacunarity,
            "source": "vote_distribution_proxy",
        },
        "gap_map_summary": {
            "foundation": foundation_profile,
            "drive": drive_profile,
            "register": register_profile,
            "source": "readout_vote_profiles",
        },
        "lacunarity_gate_decision": lac_decision,
        "inversion_axis_scores": inversion_axis_scores,
        "inversion_flag_count": None,
        "inversion_gate_decision": inversion_gate_decision,
        "gate_decisions": gate_decisions,
        "instrumentation_status": {
            "rpm_gate": "proxy_measurable_from_factor_recomposition",
            "lacunarity_gate": "proxy_measurable_from_readout_votes",
            "inversion_scan_gate": "not_measurable_from_locked_artifact",
            "full_attribution_ready": False,
        },
    }


def build_report() -> dict[str, Any]:
    stage19b = _load_json("stage19b_cross_arch_foundation_verification_stack_20260519.json")
    instrumented_rows: list[dict[str, Any]] = []
    suppressed_rows_seen = 0
    suppressed_rows_with_votes = 0
    for model_key, model in stage19b["models"].items():
        for row in model.get("accepted_examples_sample", []):
            instrumented_rows.append(_instrument_accepted_row(model_key, row))
        for row in model.get("suppressed_examples_sample", []):
            suppressed_rows_seen += 1
            if any(key in row for key in ("foundation_votes", "votes", "drive_votes", "register_votes")):
                suppressed_rows_with_votes += 1

    required = set(required_field_names())
    rows_with_required_fields = sum(
        1 for row in instrumented_rows if required.issubset(row)
    )
    inversion_ready_rows = sum(
        1
        for row in instrumented_rows
        if row["instrumentation_status"]["inversion_scan_gate"] != "not_measurable_from_locked_artifact"
    )
    return {
        "status": "STAGE22_3_SAMPLE_INSTRUMENTATION_PARTIAL",
        "schema_version": "stage22_3_diagnostic_sample_instrumentation_v1",
        "source": "stage19b_cross_arch_foundation_verification_stack_20260519.json",
        "instrumented_row_count": len(instrumented_rows),
        "rows_with_required_field_names_present": rows_with_required_fields,
        "suppressed_sample_rows_seen": suppressed_rows_seen,
        "suppressed_sample_rows_with_votes": suppressed_rows_with_votes,
        "inversion_ready_rows": inversion_ready_rows,
        "instrumented_rows": instrumented_rows,
        "boundary": (
            "This sample instrumentation proves the row contract shape for accepted "
            "Stage 19B sample rows. RPM and lacunarity are vote/factor proxies, not "
            "fresh neural RPM/lacunarity diagnostics. Inversion remains unmeasured. "
            "Full attribution requires rerunning the verifier with per-row diagnostics "
            "for both accepted and suppressed rows."
        ),
        "next_runner_requirements": {
            "emit_all_test_rows": True,
            "include_suppressed_row_votes": True,
            "compute_true_inversion_axis_scores": True,
            "compute_neural_or_deterministic_lacunarity_scores": True,
            "compute_rpm_satisfaction_without_gold_labels": True,
        },
    }


def _write_markdown(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 22.3 Diagnostic Sample Instrumentation",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Headline",
        "",
        f"- Instrumented accepted sample rows: `{report['instrumented_row_count']}`",
        f"- Rows with Stage 22.2 required field names present: `{report['rows_with_required_field_names_present']}`",
        f"- Suppressed sample rows seen: `{report['suppressed_sample_rows_seen']}`",
        f"- Suppressed sample rows with votes: `{report['suppressed_sample_rows_with_votes']}`",
        f"- Inversion-ready rows: `{report['inversion_ready_rows']}`",
        "",
        "## Boundary",
        "",
        report["boundary"],
        "",
        "## Next Runner Requirements",
        "",
    ]
    for key, value in report["next_runner_requirements"].items():
        lines.append(f"- `{key}`: `{str(value).lower()}`")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-json",
        default="stage22_3_diagnostic_sample_instrumentation_20260519.json",
    )
    parser.add_argument(
        "--out-md",
        default="STAGE22_3_DIAGNOSTIC_SAMPLE_INSTRUMENTATION_20260519.md",
    )
    args = parser.parse_args(argv)
    report = build_report()
    _resolve(args.out_json).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_markdown(report, _resolve(args.out_md))
    print(
        json.dumps(
            {
                "status": report["status"],
                "instrumented_row_count": report["instrumented_row_count"],
                "suppressed_sample_rows_with_votes": report["suppressed_sample_rows_with_votes"],
                "inversion_ready_rows": report["inversion_ready_rows"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

