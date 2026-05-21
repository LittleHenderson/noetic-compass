"""Stage 28D Noetic cluster colloquialism realization.

This runner tests compound Noetic phrases as multi-label clusters. It scores
whether the two target Noetics are jointly elevated over hard replacement
controls in row-standardized probe-logit space. This avoids the wrong
single-label exact-accuracy target used for Stages 28B/C.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from run_stage28a_noetic_involution_sonar import _artifact_contract
from run_stage28b_noetic_colloquialism_realization import (
    _LAYER,
    _NOETIC_LABELS,
    _NOETIC_NAMES,
    _binomial_upper_tail,
    _carrier_text,
    _load_model_and_tokenizer,
    _sha256_of_file,
)
from run_stage28c_noetic_phrase_level_realization import (
    _capture_phrase_vector_bundle,
    _fit_stage9_noetic_probe_for_key,
)
from stage28d_noetic_cluster_realization_spec import stage28d_claim_boundary, stage28d_cluster_fixture


_HERE = Path(__file__).resolve().parent
_READOUTS = {
    "phrase_mean": {"stage9_key": "X_mean", "stage9_name": "mean_over_seq_len"},
    "phrase_last": {"stage9_key": "X_final", "stage9_name": "final_token"},
}
_LABEL_TO_INDEX = {label: idx for idx, label in enumerate(_NOETIC_LABELS)}
_INVOLUTION_PARTNER = {
    _LABEL_TO_INDEX["^2"]: _LABEL_TO_INDEX["^3"],
    _LABEL_TO_INDEX["^3"]: _LABEL_TO_INDEX["^2"],
    _LABEL_TO_INDEX["^5"]: _LABEL_TO_INDEX["^6"],
    _LABEL_TO_INDEX["^6"]: _LABEL_TO_INDEX["^5"],
    _LABEL_TO_INDEX["^8"]: _LABEL_TO_INDEX["^9"],
    _LABEL_TO_INDEX["^9"]: _LABEL_TO_INDEX["^8"],
}


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _cluster_fixture_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(stage28d_cluster_fixture()):
        phrase = str(row["phrase"])
        text = _carrier_text(phrase)
        start = text.index(phrase)
        targets = tuple(str(item) for item in row["targets"])
        rows.append(
            {
                "row_id": f"stage28d_{idx:03d}",
                "cluster": row["cluster"],
                "targets": list(targets),
                "target_indices": [_LABEL_TO_INDEX[label] for label in targets],
                "phrase": phrase,
                "english": text,
                "phrase_start": int(start),
                "phrase_end": int(start + len(phrase)),
            }
        )
    return rows


def _fallback_control_index(label_idx: int, target_set: set[int]) -> int:
    for offset in (4, 5, 3, 6, 2, 7, 1, 8, 9):
        candidate = (label_idx + offset) % len(_NOETIC_LABELS)
        if candidate not in target_set:
            return candidate
    raise ValueError("could not construct fallback control index")


def _replacement_control_pairs(target_indices: list[int]) -> list[tuple[int, int]]:
    if len(target_indices) != 2:
        raise ValueError("Stage 28D clusters must have exactly two target indices")
    target_set = set(int(x) for x in target_indices)
    pairs: list[tuple[int, int]] = []
    for pos, target in enumerate(target_indices):
        other = int(target_indices[1 - pos])
        replacement = _INVOLUTION_PARTNER.get(int(target))
        if replacement is None or replacement in target_set:
            replacement = _fallback_control_index(int(target), target_set)
        pair = (other, replacement)
        if pair[0] == pair[1]:
            pair = (other, _fallback_control_index(replacement, target_set | {other}))
        pairs.append(pair)
    return pairs


def _row_zscore(logits: np.ndarray) -> np.ndarray:
    row = np.asarray(logits, dtype=np.float64)
    std = float(row.std())
    if std <= 1e-12:
        return np.zeros_like(row, dtype=np.float64)
    return (row - float(row.mean())) / std


def _pair_score(row_scores: np.ndarray, pair: tuple[int, int] | list[int]) -> float:
    return float(np.mean(row_scores[list(pair)]))


def _decision_logits(fitted: dict[str, Any], X: np.ndarray) -> np.ndarray:
    scaled = fitted["scaler"].transform(np.asarray(X, dtype=np.float64))
    logits = fitted["clf"].decision_function(scaled)
    logits = np.asarray(logits, dtype=np.float64)
    if logits.ndim == 1:
        logits = logits.reshape(-1, 1)
    return logits


def _score_cluster_readout(fitted: dict[str, Any], X: np.ndarray, fixture_rows: list[dict[str, Any]]) -> dict[str, Any]:
    logits = _decision_logits(fitted, X)
    row_reports: list[dict[str, Any]] = []
    margins: list[float] = []
    target_scores: list[float] = []
    control_scores: list[float] = []
    top4_counts: list[int] = []
    both_top4: list[bool] = []
    for i, row in enumerate(fixture_rows):
        target_indices = [int(x) for x in row["target_indices"]]
        z = _row_zscore(logits[i])
        replacement_pairs = _replacement_control_pairs(target_indices)
        target_score = _pair_score(z, target_indices)
        control_pair_scores = [_pair_score(z, pair) for pair in replacement_pairs]
        hard_control_score = float(max(control_pair_scores))
        margin = float(target_score - hard_control_score)
        top4 = np.argsort(z)[-4:][::-1].tolist()
        target_top4_count = int(sum(idx in top4 for idx in target_indices))
        row_reports.append(
            {
                "row_id": row["row_id"],
                "cluster": row["cluster"],
                "phrase": row["phrase"],
                "targets": row["targets"],
                "target_indices": target_indices,
                "target_pair_z": target_score,
                "replacement_pairs": [
                    [_NOETIC_LABELS[left], _NOETIC_LABELS[right]] for left, right in replacement_pairs
                ],
                "replacement_pair_z": control_pair_scores,
                "hard_control_z": hard_control_score,
                "target_minus_hard_control_z": margin,
                "positive_margin": bool(margin > 0.0),
                "top4_labels": [_NOETIC_LABELS[idx] for idx in top4],
                "target_labels_in_top4": target_top4_count,
                "both_targets_in_top4": bool(target_top4_count == 2),
            }
        )
        margins.append(margin)
        target_scores.append(target_score)
        control_scores.append(hard_control_score)
        top4_counts.append(target_top4_count)
        both_top4.append(target_top4_count == 2)

    positive_count = int(np.sum(np.asarray(margins) > 0.0))
    per_cluster: list[dict[str, Any]] = []
    clusters = sorted({str(row["cluster"]) for row in fixture_rows})
    for cluster in clusters:
        indices = [idx for idx, row in enumerate(row_reports) if row["cluster"] == cluster]
        cluster_margins = np.asarray([margins[idx] for idx in indices], dtype=np.float64)
        cluster_top4 = np.asarray([top4_counts[idx] for idx in indices], dtype=np.float64)
        per_cluster.append(
            {
                "cluster": cluster,
                "n": int(len(indices)),
                "targets": row_reports[indices[0]]["targets"],
                "mean_margin": float(cluster_margins.mean()),
                "positive_share": float(np.mean(cluster_margins > 0.0)),
                "mean_target_labels_in_top4": float(cluster_top4.mean()),
            }
        )
    return {
        "n_rows": int(len(fixture_rows)),
        "mean_target_pair_z": float(np.mean(target_scores)),
        "mean_hard_control_z": float(np.mean(control_scores)),
        "mean_target_minus_hard_control_z": float(np.mean(margins)),
        "median_target_minus_hard_control_z": float(np.median(margins)),
        "positive_margin_count": positive_count,
        "positive_margin_share": float(positive_count / len(margins)) if margins else 0.0,
        "sign_test_p_vs_half": _binomial_upper_tail(positive_count, len(margins), 0.5) if margins else 1.0,
        "mean_target_labels_in_top4": float(np.mean(top4_counts)) if top4_counts else 0.0,
        "both_targets_in_top4_share": float(np.mean(both_top4)) if both_top4 else 0.0,
        "per_cluster": per_cluster,
        "row_reports": row_reports,
    }


def _candidate_pass(metrics: dict[str, Any], probe: dict[str, Any], gates: dict[str, float]) -> bool:
    return bool(
        probe["test_acc"] >= gates["min_probe_test_acc"]
        and metrics["mean_target_minus_hard_control_z"] > 0.0
        and metrics["positive_margin_count"] >= gates["min_positive_rows"]
        and metrics["sign_test_p_vs_half"] < gates["max_sign_test_p"]
        and metrics["mean_target_labels_in_top4"] >= gates["min_mean_target_labels_in_top4"]
    )


def _status_from_gates(report: dict[str, Any]) -> str:
    if not report["artifact_contract"]["formal_gate_valid"]:
        return "STAGE28D_NOETIC_CLUSTER_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"
    eligible = [row for row in report["readout_results"].values() if row["eligible_probe_floor"]]
    if not eligible:
        return "NULL_NOETIC_CLUSTER_REALIZATION_PROBE_FLOOR_NOT_MET"
    if any(row["passes_all_primary_gates"] for row in eligible):
        return "PASS_BOUNDED_NOETIC_CLUSTER_REALIZATION"
    for row in eligible:
        metrics = row["metrics"]
        if metrics["mean_target_minus_hard_control_z"] > 0.0 and metrics["positive_margin_share"] >= 0.60:
            return "GREY_NOETIC_CLUSTER_REALIZATION_PARTIAL"
    return "NULL_NOETIC_CLUSTER_REALIZATION_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    activation_manifest_path = _resolve(args.activation_manifest)
    prereg_path = _resolve(args.preregistration)
    activations_sha256 = _sha256_of_file(activations_path)
    artifact_contract = _artifact_contract(activations_sha256, activation_manifest_path)
    fixture_rows = _cluster_fixture_rows()
    fitted_by_key: dict[str, dict[str, Any]] = {}
    probes_by_key: dict[str, dict[str, Any]] = {}
    for spec in _READOUTS.values():
        key = spec["stage9_key"]
        fitted, probe_meta = _fit_stage9_noetic_probe_for_key(input_path, activations_path, key)
        fitted_by_key[key] = fitted
        probes_by_key[key] = probe_meta

    model, tokenizer, device, model_meta = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    vector_bundle, audit_rows = _capture_phrase_vector_bundle(fixture_rows, model, tokenizer, device, max_length=int(args.max_length))
    gates = {
        "min_probe_test_acc": float(args.min_probe_test_acc),
        "min_positive_rows": int(args.min_positive_rows),
        "max_sign_test_p": float(args.max_sign_test_p),
        "min_mean_target_labels_in_top4": float(args.min_mean_target_labels_in_top4),
    }
    readout_results: dict[str, Any] = {}
    for name, spec in _READOUTS.items():
        key = spec["stage9_key"]
        metrics = _score_cluster_readout(fitted_by_key[key], vector_bundle[name], audit_rows)
        probe = probes_by_key[key]
        readout_results[name] = {
            "runtime_readout": name,
            "stage9_readout_key": key,
            "stage9_readout_name": spec["stage9_name"],
            "eligible_probe_floor": bool(probe["test_acc"] >= gates["min_probe_test_acc"]),
            "passes_all_primary_gates": _candidate_pass(metrics, probe, gates),
            "probe": probe,
            "metrics": metrics,
        }
    report: dict[str, Any] = {
        "schema_version": "stage28d_noetic_cluster_realization.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "model": model_meta,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": activations_sha256,
        "activation_manifest_file": activation_manifest_path.name,
        "artifact_contract": artifact_contract,
        "preregistration_file": prereg_path.name,
        "preregistration_sha256": _sha256_of_file(prereg_path) if prereg_path.exists() else None,
        "layer": _LAYER,
        "fixture_rows": audit_rows,
        "readout_results": readout_results,
        "noetic_labels": list(_NOETIC_LABELS),
        "noetic_names": list(_NOETIC_NAMES),
        "gates": gates,
        "claim_boundary": stage28d_claim_boundary(),
        "plain_english_read": (
            "This report tests compound Noetic colloquialisms as multi-label clusters by asking whether "
            "their two target Noetics are jointly elevated over hard replacement controls."
        ),
        "boundary": (
            "Stage 28D tests multi-label two-Noetic clusters on Pythia-160M using existing Stage 9 probes. "
            "It does not train a cluster classifier, test full formulas/equations, prove exact neurons, or establish generation control."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 28D Noetic Cluster Realization",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Plain English",
        "",
        report["plain_english_read"],
        "",
        "## Artifact",
        "",
        f"- Model: `{report['model']['model_name']}`",
        f"- Runtime device: `{report['model']['device']}`",
        f"- Layer: `{report['layer']}`",
        f"- Artifact contract: `{report['artifact_contract']['status']}`",
        f"- Fixture rows: `{len(report['fixture_rows'])}`",
        "",
        "## Readout Results",
        "",
        "| Runtime readout | Stage 9 probe | Probe test acc | Mean margin | Positive rows | Sign p | Mean targets in top4 | Both targets top4 | Pass gates |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for name, row in report["readout_results"].items():
        metrics = row["metrics"]
        lines.append(
            f"| `{name}` | `{row['stage9_readout_key']}` | {row['probe']['test_acc']:.4f} | "
            f"{metrics['mean_target_minus_hard_control_z']:.4f} | "
            f"{metrics['positive_margin_count']} / {metrics['n_rows']} | "
            f"{metrics['sign_test_p_vs_half']:.6g} | "
            f"{metrics['mean_target_labels_in_top4']:.4f} | "
            f"{metrics['both_targets_in_top4_share']:.4f} | `{row['passes_all_primary_gates']}` |"
        )
    lines.extend(["", "## Per-Cluster Margins", ""])
    for name, row in report["readout_results"].items():
        lines.extend(
            [
                f"### {name}",
                "",
                "| Cluster | Targets | Mean margin | Positive share | Mean targets in top4 |",
                "|---|---|---:|---:|---:|",
            ]
        )
        for item in row["metrics"]["per_cluster"]:
            lines.append(
                f"| `{item['cluster']}` | `{', '.join(item['targets'])}` | {item['mean_margin']:.4f} | "
                f"{item['positive_share']:.3f} | {item['mean_target_labels_in_top4']:.3f} |"
            )
        lines.append("")
    lines.extend(["## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage9_elements_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage9_elements_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage24b_40_element_cpu_recap_prereg_20260521.json")
    parser.add_argument("--preregistration", default="stage28d_noetic_cluster_prereg_20260521.json")
    parser.add_argument("--out-report", default="stage28d_noetic_cluster_realization_20260521.json")
    parser.add_argument("--out-md", default="STAGE28D_NOETIC_CLUSTER_REALIZATION_20260521.md")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--max-length", type=int, default=112)
    parser.add_argument("--min-probe-test-acc", type=float, default=0.50)
    parser.add_argument("--min-positive-rows", type=int, default=18)
    parser.add_argument("--max-sign-test-p", type=float, default=0.025)
    parser.add_argument("--min-mean-target-labels-in-top4", type=float, default=0.90)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args(argv)

    report = build_report(args)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    print(
        json.dumps(
            {
                "status": report["status"],
                "readouts": {
                    name: {
                        "probe_test_acc": row["probe"]["test_acc"],
                        "mean_margin": row["metrics"]["mean_target_minus_hard_control_z"],
                        "positive_rows": row["metrics"]["positive_margin_count"],
                        "sign_p": row["metrics"]["sign_test_p_vs_half"],
                        "mean_targets_in_top4": row["metrics"]["mean_target_labels_in_top4"],
                        "passes_all_primary_gates": row["passes_all_primary_gates"],
                    }
                    for name, row in report["readout_results"].items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
