#!/usr/bin/env python3
"""Merge Stage 9 40E proof reports into a review-only Evidence Packet.

This scaffold intentionally does not emit ACCEPT or SUPPRESS. It preserves the
corrected Stage 9 original 40E readout and records which downstream proof tiers
are still missing until ablation, cover, bridge, and verifier artifacts exist.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "cas_harness_stage9_40e_evidence_packet.v1"
METHOD_LABEL = "S9-40E-ORIGINAL-BASELINE-READOUT"
DEFAULT_READOUT_REPORT = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "working"
    / "gpt_neox_20b_stage9_original_40e_probe_eval_report_20260527.json"
)
DEFAULT_OUTPUT_JSON = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "working"
    / "gpt_neox_20b_stage9_original_40e_evidence_packet_20260527.json"
)
DEFAULT_OUTPUT_MARKDOWN = DEFAULT_OUTPUT_JSON.with_suffix(".md")

CORRECTED_BASELINE = {
    "hidden_probe_test_acc": 0.95625,
    "hidden_probe_test_acc_pct": 95.625,
    "confirmed_text_test_acc": 0.4924107142857143,
    "confirmed_text_test_acc_pct": 49.241071,
    "text_hash_test_acc": 0.5,
    "text_hash_test_acc_pct": 50.0,
    "shuffled_label_hidden_mean_test_acc": 0.02619419642857143,
    "shuffled_label_hidden_mean_test_acc_pct": 2.619,
    "compact_gloss_v0_text_only_acc": 1.0,
    "compact_gloss_v0_text_only_acc_pct": 100.0,
}

REVIEW_VERDICT = "FLAG_FOR_HUMAN_REVIEW"
INPUT_COPY_KEYS = (
    "schema_version",
    "status",
    "created_at",
    "model_id",
    "model_name",
    "model_family",
    "model_scale",
    "parameter_scale",
    "dataset",
    "metadata_path",
    "method_label",
    "method_contract",
    "run_id",
    "trace_id",
    "artifacts",
    "hashes",
    "provenance",
)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"required report does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"report is not valid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"report must be a JSON object: {path}")
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _report_artifact(path: Path, artifact_id: str, artifact_type: str) -> dict[str, Any]:
    stat = path.stat()
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "content_sha256": _sha256_file(path),
        "byte_count": int(stat.st_size),
        "storage_uri": str(path),
        "redaction_class": "stage9_40e_internal_report",
        "created_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }


def _copy_known_fields(report: dict[str, Any]) -> dict[str, Any]:
    return {key: report[key] for key in INPUT_COPY_KEYS if key in report}


def _nested_get(report: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = report
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _first_present(report: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> Any:
    for path in paths:
        value = _nested_get(report, path)
        if value is not None:
            return value
    return None


def _numeric_close(left: Any, right: float, tolerance: float = 1e-9) -> bool | None:
    if left is None:
        return None
    try:
        return abs(float(left) - right) <= tolerance
    except (TypeError, ValueError):
        return False


def _observed_baseline_fields(readout: dict[str, Any]) -> dict[str, Any]:
    """Pull known metric locations without requiring one exact report schema."""
    return {
        "hidden_probe_test_acc": _first_present(
            readout,
            (
                ("corrected_baseline", "hidden_probe_test_acc"),
                ("baseline", "hidden_probe_test_acc"),
                ("baseline_proof", "hidden_probe_test_acc"),
                ("result_summary", "hidden_probe_test_acc"),
                ("best_layer", "test_acc"),
            ),
        ),
        "confirmed_text_test_acc": _first_present(
            readout,
            (
                ("corrected_baseline", "confirmed_text_test_acc"),
                ("baseline", "confirmed_text_test_acc"),
                ("baseline_proof", "confirmed_text_test_acc"),
                ("controls", "confirmed_text_baseline_report", "test_acc"),
                ("controls", "confirmed_text", "test_acc"),
                ("controls", "confirmed_text_baseline", "test_acc"),
                ("controls", "confirmed_text_test_acc"),
            ),
        ),
        "text_hash_test_acc": _first_present(
            readout,
            (
                ("corrected_baseline", "text_hash_test_acc"),
                ("baseline", "text_hash_test_acc"),
                ("baseline_proof", "text_hash_test_acc"),
                ("controls", "text_hash_baseline", "test_acc"),
                ("controls", "text_hash_centroid", "test_acc"),
                ("controls", "text_hash", "test_acc"),
                ("controls", "text_hash_test_acc"),
            ),
        ),
        "shuffled_label_hidden_mean_test_acc": _first_present(
            readout,
            (
                ("corrected_baseline", "shuffled_label_hidden_mean_test_acc"),
                ("baseline", "shuffled_label_hidden_mean_test_acc"),
                ("baseline_proof", "shuffled_label_hidden_mean_test_acc"),
                ("controls", "shuffled_label_hidden_best_layer", "mean_test_acc"),
                ("controls", "shuffled_label_hidden", "mean_test_acc"),
                ("controls", "shuffled_label_mean_test_acc"),
            ),
        ),
        "compact_gloss_v0_text_only_acc": _first_present(
            readout,
            (
                ("corrected_baseline", "compact_gloss_v0_text_only_acc"),
                ("baseline", "compact_gloss_v0_text_only_acc"),
                ("baseline_proof", "compact_gloss_v0_text_only_acc"),
                ("controls", "compact_gloss_v0", "text_only_acc"),
                ("compact_gloss_v0", "text_only_acc"),
            ),
        ),
        "compact_gloss_v0_status": _first_present(
            readout,
            (
                ("corrected_baseline", "compact_gloss_v0_status"),
                ("baseline", "compact_gloss_v0_status"),
                ("baseline_proof", "compact_gloss_v0_status"),
                ("controls", "compact_gloss_v0", "status"),
                ("compact_gloss_v0", "status"),
            ),
        ),
    }


def _baseline_checks(observed: dict[str, Any]) -> dict[str, str]:
    checks: dict[str, str] = {}
    for key in (
        "hidden_probe_test_acc",
        "confirmed_text_test_acc",
        "text_hash_test_acc",
        "shuffled_label_hidden_mean_test_acc",
        "compact_gloss_v0_text_only_acc",
    ):
        expected = CORRECTED_BASELINE[key]
        result = _numeric_close(observed.get(key), expected)
        if result is True:
            checks[key] = "matches_corrected_baseline"
        elif result is False:
            checks[key] = "differs_from_corrected_baseline"
        else:
            checks[key] = "not_present_in_source_report"

    status = observed.get("compact_gloss_v0_status")
    if status is None:
        checks["compact_gloss_v0_status"] = "not_present_in_source_report"
    elif str(status).lower() in {"blocked", "blocked_text_only", "text_only_blocked"}:
        checks["compact_gloss_v0_status"] = "matches_corrected_baseline"
    else:
        checks["compact_gloss_v0_status"] = "differs_from_corrected_baseline"
    return checks


def _extract_trace_id(readout: dict[str, Any]) -> str:
    explicit = _first_present(
        readout,
        (
            ("trace_id",),
            ("run", "trace_id"),
            ("provenance", "trace_id"),
            ("metadata", "trace_id"),
        ),
    )
    if explicit:
        return str(explicit)
    return "stage9-40e-original-baseline-readout-20260527"


def _extract_run_id(readout: dict[str, Any]) -> str:
    explicit = _first_present(
        readout,
        (
            ("run_id",),
            ("run", "run_id"),
            ("provenance", "run_id"),
            ("metadata", "run_id"),
        ),
    )
    if explicit:
        return str(explicit)
    return "gpt-neox-20b-stage9-original-40e-20260527"


def _extract_model_proof(readout: dict[str, Any], readout_artifact: dict[str, Any]) -> dict[str, Any]:
    model_id = _first_present(
        readout,
        (
            ("model_id",),
            ("model", "model_id"),
            ("model_subject", "model_id"),
            ("provenance", "model_id"),
        ),
    )
    model_weight_hash = _first_present(
        readout,
        (
            ("model_weight_hash",),
            ("hashes", "model_weight_hash"),
            ("hashes", "weights_sha"),
            ("model_subject", "model_weight_hash"),
            ("provenance", "model_weight_hash"),
        ),
    )
    return {
        "status": "present",
        "model_id": model_id or "EleutherAI/gpt-neox-20b",
        "model_family": _first_present(
            readout,
            (
                ("model_family",),
                ("model", "model_family"),
                ("model_subject", "model_family"),
            ),
        )
        or "gpt_neox",
        "parameter_scale": _first_present(
            readout,
            (
                ("parameter_scale",),
                ("model_scale",),
                ("model", "parameter_scale"),
                ("model_subject", "parameter_scale"),
            ),
        )
        or "20B",
        "model_weight_hash": model_weight_hash,
        "source_report": readout_artifact,
        "input_provenance": readout.get("provenance"),
    }


def _make_readout_proof(
    readout: dict[str, Any],
    readout_artifact: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "present",
        "method_label": METHOD_LABEL,
        "source_report": readout_artifact,
        "source_fields": _copy_known_fields(readout),
        "best_layer": readout.get("best_layer"),
        "controls": readout.get("controls"),
        "result_summary": readout.get("result_summary"),
        "readiness_gate": readout.get("readiness_gate"),
        "baseline_note": (
            "PR #102 corrected the Stage 9 original 40E readout baseline. "
            "This merger preserves that corrected baseline and does not promote "
            "the packet to ACCEPT or SUPPRESS."
        ),
    }


def _make_baseline_proof(readout: dict[str, Any]) -> dict[str, Any]:
    observed = _observed_baseline_fields(readout)
    return {
        "status": "present",
        "method_label": METHOD_LABEL,
        **CORRECTED_BASELINE,
        "compact_gloss_v0": {
            "status": "blocked_text_only",
            "text_only_acc": CORRECTED_BASELINE["compact_gloss_v0_text_only_acc"],
            "text_only_acc_pct": CORRECTED_BASELINE["compact_gloss_v0_text_only_acc_pct"],
            "note": "compact-gloss v0 is blocked because it is 100% text-only.",
        },
        "observed_source_fields": observed,
        "source_field_checks": _baseline_checks(observed),
        "source": "PR #102 corrected 20B Stage 9 original 40E readout",
    }


def _pct(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value) * 100.0, 6)
    except (TypeError, ValueError):
        return None


def _make_report_summary(tier_name: str, report: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": report.get("status"),
        "method_label": report.get("method_label"),
        "run_id": report.get("run_id"),
        "trace_id": report.get("trace_id"),
    }

    if tier_name == "subspace_ablation":
        primary = report.get("primary_result")
        if isinstance(primary, dict):
            summary["primary_result"] = {
                "layer": primary.get("layer"),
                "original_accuracy": primary.get("original_accuracy"),
                "original_accuracy_pct": _pct(primary.get("original_accuracy")),
                "ablated_accuracy": primary.get("ablated_accuracy"),
                "ablated_accuracy_pct": _pct(primary.get("ablated_accuracy")),
                "true_disruption": primary.get("true_disruption"),
                "true_disruption_pp": _pct(primary.get("true_disruption")),
                "chance_baseline_accuracy": primary.get("chance_baseline_accuracy"),
                "chance_baseline_accuracy_pct": _pct(
                    primary.get("chance_baseline_accuracy")
                ),
                "random_same_rank_mean_disruption": primary.get(
                    "random_same_rank_mean_disruption"
                ),
                "random_same_rank_mean_disruption_pp": _pct(
                    primary.get("random_same_rank_mean_disruption")
                ),
                "random_same_rank_max_disruption": primary.get(
                    "random_same_rank_max_disruption"
                ),
                "random_same_rank_max_disruption_pp": _pct(
                    primary.get("random_same_rank_max_disruption")
                ),
                "guard_status": primary.get("guard_status"),
            }

    if tier_name == "cover_discovery":
        cover_map = report.get("cover_map")
        true_cover_per_class = report.get("true_cover_per_class")
        matched_controls = report.get("matched_controls")
        if isinstance(cover_map, dict):
            summary["class_count"] = len(cover_map)
        elif isinstance(true_cover_per_class, dict):
            summary["class_count"] = len(true_cover_per_class)
        summary["selected_layer"] = report.get("selected_layer")
        summary["top_k"] = report.get("top_k")
        if isinstance(true_cover_per_class, dict):
            summary["true_cover_classes"] = len(true_cover_per_class)
        if isinstance(matched_controls, dict):
            summary["matched_controls"] = {
                "random_same_size_classes": len(
                    matched_controls.get("random_same_size") or {}
                )
                if isinstance(matched_controls.get("random_same_size"), dict)
                else None,
                "wrong_class_reference_classes": len(
                    matched_controls.get("wrong_class_references") or {}
                )
                if isinstance(matched_controls.get("wrong_class_references"), dict)
                else None,
            }
        if "caveat" in report:
            summary["caveat"] = report["caveat"]

    if tier_name == "output_bridge":
        key_comparisons = report.get("key_comparisons")
        bridge_gates = report.get("bridge_gates")
        probe_prediction = report.get("probe_prediction")
        if isinstance(key_comparisons, dict):
            summary["key_comparisons"] = key_comparisons
        if isinstance(bridge_gates, dict):
            summary["bridge_gates"] = bridge_gates
            summary["probe_readable_gate_passed"] = bool(
                bridge_gates.get("probe_readable", {}).get("passed")
            )
            summary["gold_readable_gate_passed"] = bool(
                bridge_gates.get("gold_readable", {}).get("passed")
            )
        if isinstance(probe_prediction, dict):
            summary["probe_prediction"] = {
                "selected_element_accuracy": probe_prediction.get(
                    "selected_element_accuracy"
                ),
                "selected_operator_accuracy": probe_prediction.get(
                    "selected_operator_accuracy"
                ),
                "selected_domain_accuracy": probe_prediction.get(
                    "selected_domain_accuracy"
                ),
                "all_test_element_accuracy": probe_prediction.get(
                    "all_test_element_accuracy"
                ),
            }
        for key in ("n_cases", "per_element", "readout_layer", "readout_mode"):
            if key in report:
                summary[key] = report[key]
        if "implication" in report:
            summary["implication"] = report["implication"]

    return summary


def _make_optional_proof(
    *,
    tier_name: str,
    report_path: Path | None,
    artifact_id: str,
    artifact_type: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if report_path is None:
        return (
            {
                "status": "missing",
                "tier": tier_name,
                "required_for_final_verdict": True,
                "source_report": None,
                "blocking_reason": f"{tier_name} report was not supplied",
            },
            None,
        )

    report = _load_json(report_path)
    artifact = _report_artifact(report_path, artifact_id, artifact_type)
    return (
        {
            "status": "present",
            "tier": tier_name,
            "required_for_final_verdict": True,
            "source_report": artifact,
            "source_fields": _copy_known_fields(report),
            "summary": _make_report_summary(tier_name, report),
        },
        artifact,
    )


def _verdict_rationale(tier_statuses: dict[str, str]) -> str:
    missing = [
        tier
        for tier, status in tier_statuses.items()
        if tier in {"causal", "control", "output_bridge", "verifier"} and status != "present"
    ]
    if missing:
        return (
            "Merged packet is review-only because required proof tiers are missing: "
            + ", ".join(missing)
            + "."
        )
    return (
        "All merger-side proof tiers are present, but this scaffold still requires "
        "an attached verifier decision before any final ACCEPT or SUPPRESS verdict."
    )


def build_packet(
    *,
    readout_report: Path,
    ablation_report: Path | None = None,
    cover_report: Path | None = None,
    bridge_report: Path | None = None,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    readout = _load_json(readout_report)
    generated = generated_at or datetime.now(UTC)
    readout_artifact = _report_artifact(
        readout_report,
        "stage9_40e_readout_report",
        "stage9_40e_original_baseline_readout_report",
    )
    causal_proof, causal_artifact = _make_optional_proof(
        tier_name="subspace_ablation",
        report_path=ablation_report,
        artifact_id="stage9_40e_subspace_ablation_report",
        artifact_type="stage9_40e_subspace_ablation_report",
    )
    control_proof, control_artifact = _make_optional_proof(
        tier_name="cover_discovery",
        report_path=cover_report,
        artifact_id="stage9_40e_cover_discovery_report",
        artifact_type="stage9_40e_cover_discovery_report",
    )
    output_bridge_proof, bridge_artifact = _make_optional_proof(
        tier_name="output_bridge",
        report_path=bridge_report,
        artifact_id="stage9_40e_bridge_report",
        artifact_type="stage9_40e_bridge_report",
    )

    tier_statuses = {
        "model": "present",
        "readout": "present",
        "baseline": "present",
        "causal": causal_proof["status"],
        "control": control_proof["status"],
        "output_bridge": output_bridge_proof["status"],
        "verifier": "missing",
    }
    input_artifacts = [
        artifact
        for artifact in (readout_artifact, causal_artifact, control_artifact, bridge_artifact)
        if artifact is not None
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "trace_id": _extract_trace_id(readout),
        "run_id": _extract_run_id(readout),
        "generated_at": generated.isoformat(),
        "method_label": METHOD_LABEL,
        "model_proof": _extract_model_proof(readout, readout_artifact),
        "readout_proof": _make_readout_proof(readout, readout_artifact),
        "baseline_proof": _make_baseline_proof(readout),
        "causal_proof": causal_proof,
        "control_proof": control_proof,
        "output_bridge_proof": output_bridge_proof,
        "tier_statuses": tier_statuses,
        "verifier": {
            "status": "missing",
            "required_for_final_verdict": True,
            "blocking_reason": "No verifier decision layer is attached to this packet.",
        },
        "verdict": REVIEW_VERDICT,
        "verdict_rationale": _verdict_rationale(tier_statuses),
        "caveats": [
            "This Stage 9 40E merger scaffold is not an ACCEPT verdict.",
            "This Stage 9 40E merger scaffold is not a SUPPRESS verdict.",
            (
                "Final ACCEPT/SUPPRESS requires present causal, control, and "
                "output/bridge proof tiers plus an attached verifier decision."
            ),
            (
                "Readout-only packets preserve the corrected PR #102 baseline "
                "but remain flagged for human review."
            ),
        ],
        "provenance": {
            "input_artifacts": input_artifacts,
            "input_count": len(input_artifacts),
            "readout_report": str(readout_report),
            "ablation_report": str(ablation_report) if ablation_report else None,
            "cover_report": str(cover_report) if cover_report else None,
            "bridge_report": str(bridge_report) if bridge_report else None,
        },
    }


def render_markdown(packet: dict[str, Any]) -> str:
    baseline = packet["baseline_proof"]
    tiers = packet["tier_statuses"]
    caveats = "\n".join(f"- {caveat}" for caveat in packet["caveats"])
    causal_primary = (
        packet.get("causal_proof", {})
        .get("summary", {})
        .get("primary_result")
    )
    if causal_primary:
        causal_rows = f"""
## Causal Proof

| Metric | Value |
| --- | ---: |
| Original hidden readout | {causal_primary["original_accuracy_pct"]:.6g}% |
| After learned-subspace ablation | {causal_primary["ablated_accuracy_pct"]:.6g}% |
| True disruption | {causal_primary["true_disruption_pp"]:.6g} pp |
| Random same-rank mean disruption | {causal_primary["random_same_rank_mean_disruption_pp"]:.6g} pp |
| Random same-rank max disruption | {causal_primary["random_same_rank_max_disruption_pp"]:.6g} pp |
| Chance baseline | {causal_primary["chance_baseline_accuracy_pct"]:.6g}% |
| Guard status | {causal_primary["guard_status"]} |
"""
    else:
        causal_rows = ""
    control_summary = packet.get("control_proof", {}).get("summary", {})
    if control_summary.get("class_count") is not None:
        control_rows = f"""
## Control / Cover Proof

| Metric | Value |
| --- | ---: |
| Candidate classes | {control_summary["class_count"]} |
| Selected layer | {control_summary.get("selected_layer")} |
| Top-k neurons per class | {control_summary.get("top_k")} |
| Caveat | {control_summary.get("caveat", "candidate cover discovery")} |
"""
    else:
        control_rows = ""
    bridge_summary = packet.get("output_bridge_proof", {}).get("summary", {})
    bridge_key = bridge_summary.get("key_comparisons", {})
    bridge_pred = bridge_summary.get("probe_prediction", {})
    if bridge_key:
        bridge_rows = f"""
## Output Bridge Proof

| Metric | Value |
| --- | ---: |
| Cases | {bridge_summary.get("n_cases")} |
| Selected element accuracy | {float(bridge_pred.get("selected_element_accuracy", 0.0)):.6g} |
| Probe-readable delta vs none | {float(bridge_key.get("probe_readable_delta_vs_none", 0.0)):.6g} |
| Probe-readable minus partner | {float(bridge_key.get("probe_readable_minus_partner_readable_margin", 0.0)):.6g} |
| Gold-readable delta vs none | {float(bridge_key.get("gold_readable_delta_vs_none", 0.0)):.6g} |
| Probe-raw delta vs none | {float(bridge_key.get("probe_raw_delta_vs_none", 0.0)):.6g} |
| Probe-readable gate | {'passed' if bridge_summary.get("probe_readable_gate_passed") else 'failed'} |
"""
    else:
        bridge_rows = ""
    return f"""# Stage 9 40E Evidence Packet

- Schema version: `{packet["schema_version"]}`
- Trace ID: `{packet["trace_id"]}`
- Run ID: `{packet["run_id"]}`
- Method: `{packet["method_label"]}`
- Verdict: `{packet["verdict"]}`

## Tier Status

| Tier | Status |
| --- | --- |
| Model proof | {tiers["model"]} |
| Readout proof | {tiers["readout"]} |
| Baseline proof | {tiers["baseline"]} |
| Causal proof | {tiers["causal"]} |
| Control proof | {tiers["control"]} |
| Output/bridge proof | {tiers["output_bridge"]} |
| Verifier | {tiers["verifier"]} |

## Baseline Proof

| Metric | Corrected value |
| --- | ---: |
| Hidden readout | {baseline["hidden_probe_test_acc_pct"]:.6g}% |
| Confirmed text | {baseline["confirmed_text_test_acc_pct"]:.6f}% |
| Text-hash baseline | {baseline["text_hash_test_acc_pct"]:.6g}% |
| Shuffled-label mean | {baseline["shuffled_label_hidden_mean_test_acc_pct"]:.6g}% |
| compact-gloss v0 | blocked at {baseline["compact_gloss_v0_text_only_acc_pct"]:.6g}% text-only |

{causal_rows}{control_rows}{bridge_rows}
## Rationale

{packet["verdict_rationale"]}

## Caveats

{caveats}
"""


def write_packet(packet: dict[str, Any], output_json: Path, output_markdown: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(
        json.dumps(packet, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_markdown.write_text(render_markdown(packet), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--readout-report", type=Path, default=DEFAULT_READOUT_REPORT)
    parser.add_argument("--ablation-report", type=Path)
    parser.add_argument("--cover-report", type=Path)
    parser.add_argument("--bridge-report", type=Path)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-markdown", type=Path, default=DEFAULT_OUTPUT_MARKDOWN)
    args = parser.parse_args()

    packet = build_packet(
        readout_report=args.readout_report,
        ablation_report=args.ablation_report,
        cover_report=args.cover_report,
        bridge_report=args.bridge_report,
    )
    write_packet(packet, args.output_json, args.output_markdown)
    print(f"wrote JSON packet: {args.output_json}")
    print(f"wrote markdown packet: {args.output_markdown}")
    print(f"verdict: {packet['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
