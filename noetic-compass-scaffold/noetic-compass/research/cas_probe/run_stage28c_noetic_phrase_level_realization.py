"""Stage 28C Noetic phrase-level colloquialism realization.

This runner follows Stage 28B but changes the readout position. Instead of
using only the first token of the phrase, it tests two preregistered
phrase-level candidates: phrase_mean scored by a Stage 9 X_mean Noetic probe,
and phrase_last scored by a Stage 9 X_final Noetic probe. phrase_first/X_focus
is retained only as the Stage 28B baseline replication.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

import evaluate_stage6_role_bound_full as stage6
from capture_stage6_role_bound_activations import _find_token_for_char
from evaluate_stage7_factor_check import _fit_readout
from evaluate_stage9_elements_pilot import _load_rows
from run_stage28a_noetic_involution_sonar import _artifact_contract, _noetic_labels_for_rows
from run_stage28b_noetic_colloquialism_realization import (
    _LAYER,
    _NOETIC_LABELS,
    _NOETIC_NAMES,
    _fixture_rows,
    _load_model_and_tokenizer,
    _score_colloquialisms,
    _sha256_of_file,
    _token_indices_overlapping_span,
)
from stage28c_noetic_phrase_level_realization_spec import stage28c_claim_boundary


_HERE = Path(__file__).resolve().parent
_READOUTS = {
    "phrase_first": {"stage9_key": "X_focus", "stage9_name": "focus_token", "candidate": False},
    "phrase_mean": {"stage9_key": "X_mean", "stage9_name": "mean_over_seq_len", "candidate": True},
    "phrase_last": {"stage9_key": "X_final", "stage9_name": "final_token", "candidate": True},
}


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _fit_stage9_noetic_probe_for_key(input_path: Path, activations_path: Path, readout_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = _load_rows(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    if readout_key not in data:
        raise KeyError(f"Stage 9 artifact does not contain {readout_key}")
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = stage6._split_indices(rows_by_id, sample_ids)
    X = np.asarray(data[readout_key][:, _LAYER, :], dtype=np.float64)
    y = _noetic_labels_for_rows(rows_by_id, sample_ids)
    fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _NOETIC_LABELS)
    probe_meta = {
        "readout_key": readout_key,
        "train_acc": float(fitted["train"]["acc"]),
        "val_acc": float(fitted["val"]["acc"]),
        "test_acc": float(fitted["test"]["acc"]),
        "n_train": int(len(splits["train"])),
        "n_val": int(len(splits["val"])),
        "n_test": int(len(splits["test"])),
    }
    return fitted, probe_meta


def _phrase_vectors_from_layer(layer: Any, token_indices: list[int]) -> dict[str, np.ndarray]:
    if not token_indices:
        raise ValueError("token_indices must be non-empty")
    arr = np.asarray(layer, dtype=np.float64)
    indices = [int(idx) for idx in token_indices]
    return {
        "phrase_first": arr[indices[0]].copy(),
        "phrase_last": arr[indices[-1]].copy(),
        "phrase_mean": arr[indices].mean(axis=0),
    }


def _capture_phrase_vector_bundle(
    fixture_rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    *,
    max_length: int,
) -> tuple[dict[str, np.ndarray], list[dict[str, Any]]]:
    import torch

    vectors: dict[str, list[np.ndarray]] = {name: [] for name in _READOUTS}
    audit_rows: list[dict[str, Any]] = []
    with torch.no_grad():
        for row in fixture_rows:
            encoded = tokenizer(
                row["english"],
                return_tensors="pt",
                return_offsets_mapping=True,
                truncation=True,
                max_length=max_length,
            )
            offsets = [(int(a), int(b)) for a, b in encoded.pop("offset_mapping")[0].tolist()]
            token_indices = _token_indices_overlapping_span(offsets, int(row["phrase_start"]), int(row["phrase_end"]))
            if not token_indices:
                token_indices = [_find_token_for_char(offsets, int(row["phrase_start"]))]
            token_ids = [int(encoded["input_ids"][0, idx].item()) for idx in token_indices]
            encoded = encoded.to(device)
            outputs = model(**encoded)
            layer = outputs.hidden_states[_LAYER][0].detach().cpu().float().numpy()
            row_vectors = _phrase_vectors_from_layer(layer, token_indices)
            for name, vector in row_vectors.items():
                vectors[name].append(vector)
            audit_rows.append(
                {
                    **row,
                    "phrase_token_indices": [int(x) for x in token_indices],
                    "phrase_token_ids": token_ids,
                    "phrase_token_text": [tokenizer.decode([token_id]) for token_id in token_ids],
                    "focus_token_index": int(token_indices[0]),
                    "focus_token_text": tokenizer.decode([token_ids[0]]),
                    "last_phrase_token_index": int(token_indices[-1]),
                    "last_phrase_token_text": tokenizer.decode([token_ids[-1]]),
                    "sequence_length": int(encoded["attention_mask"][0].sum().item()),
                }
            )
    return {name: np.asarray(items, dtype=np.float64) for name, items in vectors.items()}, audit_rows


def _candidate_pass(metrics: dict[str, Any], probe: dict[str, Any], gates: dict[str, float]) -> bool:
    return bool(
        probe["test_acc"] >= gates["min_probe_test_acc"]
        and metrics["exact_accuracy"] >= gates["min_exact_accuracy"]
        and metrics["exact_binomial_p_vs_chance"] < gates["max_exact_binomial_p"]
        and metrics["mean_target_probability"] >= gates["min_mean_target_probability"]
        and metrics["top2_accuracy"] >= gates["min_top2_accuracy"]
        and metrics["involution_partner_positive_share"] >= gates["min_involution_partner_positive_share"]
    )


def _status_from_gates(report: dict[str, Any]) -> str:
    if not report["artifact_contract"]["formal_gate_valid"]:
        return "STAGE28C_NOETIC_PHRASE_LEVEL_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"
    candidates = [row for row in report["readout_results"].values() if row["is_phrase_level_candidate"]]
    eligible = [row for row in candidates if row["eligible_probe_floor"]]
    if not eligible:
        return "NULL_NOETIC_PHRASE_LEVEL_REALIZATION_PROBE_FLOOR_NOT_MET"
    if any(row["passes_all_primary_gates"] for row in eligible):
        return "PASS_BOUNDED_NOETIC_PHRASE_LEVEL_REALIZATION"
    baseline = report["readout_results"]["phrase_first"]["metrics"]
    for row in eligible:
        metrics = row["metrics"]
        if (
            metrics["exact_accuracy"] > baseline["exact_accuracy"]
            and (
                metrics["mean_target_probability"] >= report["gates"]["min_mean_target_probability"]
                or metrics["top2_accuracy"] >= report["gates"]["min_top2_accuracy"]
            )
        ):
            return "GREY_NOETIC_PHRASE_LEVEL_REALIZATION_PARTIAL"
    return "NULL_NOETIC_PHRASE_LEVEL_REALIZATION_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    activation_manifest_path = _resolve(args.activation_manifest)
    prereg_path = _resolve(args.preregistration)
    activations_sha256 = _sha256_of_file(activations_path)
    artifact_contract = _artifact_contract(activations_sha256, activation_manifest_path)

    fitted_by_key: dict[str, dict[str, Any]] = {}
    probes_by_key: dict[str, dict[str, Any]] = {}
    for spec in _READOUTS.values():
        key = spec["stage9_key"]
        if key in fitted_by_key:
            continue
        fitted, probe_meta = _fit_stage9_noetic_probe_for_key(input_path, activations_path, key)
        fitted_by_key[key] = fitted
        probes_by_key[key] = probe_meta

    fixture_rows = _fixture_rows()
    model, tokenizer, device, model_meta = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    vector_bundle, audit_rows = _capture_phrase_vector_bundle(fixture_rows, model, tokenizer, device, max_length=int(args.max_length))
    gates = {
        "min_probe_test_acc": float(args.min_probe_test_acc),
        "min_exact_accuracy": float(args.min_exact_accuracy),
        "max_exact_binomial_p": float(args.max_exact_binomial_p),
        "min_mean_target_probability": float(args.min_mean_target_probability),
        "min_top2_accuracy": float(args.min_top2_accuracy),
        "min_involution_partner_positive_share": float(args.min_involution_partner_positive_share),
    }
    readout_results: dict[str, Any] = {}
    baseline_exact = None
    for name, spec in _READOUTS.items():
        key = spec["stage9_key"]
        metrics = _score_colloquialisms(fitted_by_key[key], vector_bundle[name], audit_rows)
        if name == "phrase_first":
            baseline_exact = metrics["exact_accuracy"]
        probe = probes_by_key[key]
        readout_results[name] = {
            "runtime_readout": name,
            "stage9_readout_key": key,
            "stage9_readout_name": spec["stage9_name"],
            "is_phrase_level_candidate": bool(spec["candidate"]),
            "eligible_probe_floor": bool(probe["test_acc"] >= gates["min_probe_test_acc"]),
            "passes_all_primary_gates": _candidate_pass(metrics, probe, gates) if spec["candidate"] else False,
            "metrics": metrics,
            "probe": probe,
        }
    if baseline_exact is None:
        baseline_exact = 0.0
    for name, row in readout_results.items():
        row["metrics"]["exact_accuracy_delta_vs_phrase_first"] = float(row["metrics"]["exact_accuracy"] - baseline_exact)

    report: dict[str, Any] = {
        "schema_version": "stage28c_noetic_phrase_level_realization.v1",
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
        "readout_results": readout_results,
        "fixture_rows": audit_rows,
        "noetic_labels": list(_NOETIC_LABELS),
        "noetic_names": list(_NOETIC_NAMES),
        "gates": gates,
        "claim_boundary": stage28c_claim_boundary(),
        "plain_english_read": (
            "This report tests whether Stage 28B's null was caused by the first-token readout. "
            "phrase_mean and phrase_last are scored with matching Stage 9 probes and compared against the phrase_first baseline."
        ),
        "boundary": (
            "Stage 28C tests phrase-level readout positions for single Noetic colloquialisms on Pythia-160M. "
            "It does not test Noetic clusters, retrained colloquialism probes, full TKS formulas, exact neurons, "
            "or open-ended generation control."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 28C Noetic Phrase-Level Realization",
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
        "| Runtime readout | Stage 9 probe | Probe test acc | Exact | p vs chance | Top-2 | Mean target p | Involution share | Delta vs first | Pass gates |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for name, row in report["readout_results"].items():
        metrics = row["metrics"]
        lines.append(
            f"| `{name}` | `{row['stage9_readout_key']}` | {row['probe']['test_acc']:.4f} | "
            f"{metrics['exact_accuracy']:.4f} | {metrics['exact_binomial_p_vs_chance']:.6g} | "
            f"{metrics['top2_accuracy']:.4f} | {metrics['mean_target_probability']:.4f} | "
            f"{metrics['involution_partner_positive_share']:.4f} | "
            f"{metrics['exact_accuracy_delta_vs_phrase_first']:.4f} | `{row['passes_all_primary_gates']}` |"
        )
    lines.extend(["", "## Per-Readout Per-Noetic", ""])
    for name, row in report["readout_results"].items():
        lines.extend(
            [
                f"### {name}",
                "",
                "| Noetic | Name | Exact | Top-2 | Mean target probability | Predicted counts |",
                "|---|---|---:|---:|---:|---|",
            ]
        )
        for item in row["metrics"]["per_noetic"]:
            lines.append(
                f"| `{item['noetic']}` | {item['name']} | {item['exact_accuracy']:.3f} | "
                f"{item['top2_accuracy']:.3f} | {item['mean_target_probability']:.3f} | `{item['predicted_counts']}` |"
            )
        lines.append("")
    lines.extend(["## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage9_elements_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage9_elements_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage24b_40_element_cpu_recap_prereg_20260521.json")
    parser.add_argument("--preregistration", default="stage28c_noetic_phrase_level_prereg_20260521.json")
    parser.add_argument("--out-report", default="stage28c_noetic_phrase_level_realization_20260521.json")
    parser.add_argument("--out-md", default="STAGE28C_NOETIC_PHRASE_LEVEL_REALIZATION_20260521.md")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--min-probe-test-acc", type=float, default=0.50)
    parser.add_argument("--min-exact-accuracy", type=float, default=0.45)
    parser.add_argument("--max-exact-binomial-p", type=float, default=0.025)
    parser.add_argument("--min-mean-target-probability", type=float, default=0.15)
    parser.add_argument("--min-top2-accuracy", type=float, default=0.65)
    parser.add_argument("--min-involution-partner-positive-share", type=float, default=0.60)
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
                        "exact_accuracy": row["metrics"]["exact_accuracy"],
                        "top2_accuracy": row["metrics"]["top2_accuracy"],
                        "mean_target_probability": row["metrics"]["mean_target_probability"],
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
