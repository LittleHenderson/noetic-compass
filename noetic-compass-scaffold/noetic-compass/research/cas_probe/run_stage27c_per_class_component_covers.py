"""Stage 27C per-class component covers for the Stage 7 Foundation readout.

Stage 26/27A proved a global six-head family is causally load-bearing and
sufficient for the Foundation readout. Stage 27C tests whether class-local
three-head subcovers inside that family improve held-out hard-partner
Foundation margins over same-size global and random subset controls.

Boundary: this is readout-local component cover evidence, not exact neurons,
complete circuits, token sonar, raw-symbol understanding, or generation
control.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import (
    _FOUNDATION_LABELS,
    _fit_readout,
    _labels_for_task,
    _load_jsonl,
    _split_indices,
)
from run_stage26_component_attribution import Component, _artifact_contract, _component_from_name, _encode_row
from run_stage27_component_path_patching import (
    _forward_vec_and_cache_heads,
    _forward_vec_with_head_patches,
    _load_model_and_tokenizer,
)
from run_stage27b_component_guided_contrast_sonar import _load_component_contract, _pair_kind, _partner_label


_HERE = Path(__file__).resolve().parent
_SEED = 27030
_READOUT_KEY = "X_focus"
_READOUT_NAME = "focus_token"
_LAYER = 6
_DEFAULT_SELECTED_COMPONENTS = ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")
_EXPECTED_STAGE26_STATUS = "PASS_BOUNDED_COMPONENT_ATTRIBUTION"
_EXPECTED_STAGE27A_STATUS = "PASS_BOUNDED_COMPONENT_PATH_PATCHING"
_EXPECTED_STAGE27B_STATUS = "GREY_COMPONENT_GUIDED_CONTRAST_SONAR_PARTIAL"
_LABEL_TO_INDEX = {label: idx for idx, label in enumerate(_FOUNDATION_LABELS)}


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _binomial_upper_tail(k: int, n: int, p: float = 0.5) -> float:
    return float(math.fsum(math.comb(n, i) * (p**i) * ((1.0 - p) ** (n - i)) for i in range(k, n + 1)))


def _balanced_indices(split_indices: Any, y: np.ndarray, *, rows_per_class: int) -> list[int]:
    out: list[int] = []
    split = [int(i) for i in list(split_indices)]
    for class_idx in range(len(_FOUNDATION_LABELS)):
        rows = [idx for idx in split if int(y[idx]) == class_idx]
        if len(rows) < rows_per_class:
            raise ValueError(
                f"class {_FOUNDATION_LABELS[class_idx]} has only {len(rows)} rows; need {rows_per_class}"
            )
        out.extend(rows[:rows_per_class])
    return out


def _probe_logits(fitted: dict[str, Any], vector: np.ndarray) -> np.ndarray:
    X = np.asarray([vector], dtype=np.float64)
    logits = fitted["clf"].decision_function(fitted["scaler"].transform(X))
    logits = np.asarray(logits, dtype=np.float64)
    if logits.ndim == 2:
        return logits[0]
    return logits


def _probe_margin(fitted: dict[str, Any], vector: np.ndarray, target_idx: int, partner_idx: int) -> float:
    logits = _probe_logits(fitted, vector)
    return float(logits[int(target_idx)] - logits[int(partner_idx)])


def _sample_random_subcovers(
    selected_names: list[str],
    *,
    cover_size: int,
    n_random: int,
    seed: int,
) -> list[list[str]]:
    rng = np.random.default_rng(seed)
    out: list[list[str]] = []
    for _ in range(n_random):
        out.append([str(name) for name in rng.choice(selected_names, size=cover_size, replace=False).tolist()])
    return out


def _component_names(components: list[Component]) -> list[str]:
    return [component.name for component in components]


def _learn_per_class_covers(
    learn_rows: list[dict[str, Any]],
    learn_y: np.ndarray,
    fitted: dict[str, Any],
    model: Any,
    tokenizer: Any,
    device: Any,
    selected_components: list[Component],
    *,
    cover_size: int,
) -> dict[str, Any]:
    selected_names = _component_names(selected_components)
    selected_layers = {component.layer for component in selected_components}
    lift_values: dict[str, dict[str, list[float]]] = {
        label: {name: [] for name in selected_names} for label in _FOUNDATION_LABELS
    }
    for row, target_idx_raw in zip(learn_rows, learn_y):
        target_idx = int(target_idx_raw)
        target_label = _FOUNDATION_LABELS[target_idx]
        partner_label = _partner_label(row)
        partner_idx = _LABEL_TO_INDEX[partner_label]
        encoded, focus_idx = _encode_row(row, tokenizer, device)
        _clean_vec, clean_cache = _forward_vec_and_cache_heads(encoded, focus_idx, model, selected_layers)
        ablated_vec = _forward_vec_with_head_patches(
            encoded,
            focus_idx,
            model,
            ablate_components=selected_components,
            patch_components=[],
            clean_cache=clean_cache,
        )
        ablated_margin = _probe_margin(fitted, ablated_vec, target_idx, partner_idx)
        for component in selected_components:
            patched_vec = _forward_vec_with_head_patches(
                encoded,
                focus_idx,
                model,
                ablate_components=selected_components,
                patch_components=[component],
                clean_cache=clean_cache,
            )
            patched_margin = _probe_margin(fitted, patched_vec, target_idx, partner_idx)
            lift_values[target_label][component.name].append(float(patched_margin - ablated_margin))

    covers: dict[str, list[str]] = {}
    class_scores: dict[str, list[dict[str, Any]]] = {}
    for label in _FOUNDATION_LABELS:
        rows: list[dict[str, Any]] = []
        for name in selected_names:
            values = lift_values[label][name]
            rows.append(
                {
                    "component": name,
                    "mean_lift": float(np.mean(values)) if values else 0.0,
                    "n": int(len(values)),
                }
            )
        rows.sort(key=lambda item: item["mean_lift"], reverse=True)
        covers[label] = [str(item["component"]) for item in rows[:cover_size]]
        class_scores[label] = rows
    return {"covers": covers, "class_component_scores": class_scores}


def _margin_summary(values: list[float]) -> dict[str, Any]:
    arr = np.asarray(values, dtype=np.float64)
    if arr.size == 0:
        return {"n": 0, "mean": 0.0, "median": 0.0, "positive_share": 0.0}
    return {
        "n": int(arr.size),
        "mean": float(arr.mean()),
        "median": float(np.median(arr)),
        "positive_share": float(np.mean(arr > 0.0)),
    }


def _paired_summary(left: list[float], right: list[float]) -> dict[str, Any]:
    left_arr = np.asarray(left, dtype=np.float64)
    right_arr = np.asarray(right, dtype=np.float64)
    if left_arr.shape != right_arr.shape:
        raise ValueError("paired arrays must have identical shapes")
    diff = left_arr - right_arr
    wins = int(np.sum(diff > 0.0))
    return {
        "n": int(diff.size),
        "mean_delta": float(diff.mean()) if diff.size else 0.0,
        "median_delta": float(np.median(diff)) if diff.size else 0.0,
        "wins": wins,
        "win_share": float(wins / diff.size) if diff.size else 0.0,
        "sign_test_p": _binomial_upper_tail(wins, int(diff.size), 0.5) if diff.size else 1.0,
    }


def _evaluate_covers(
    eval_rows: list[dict[str, Any]],
    eval_y: np.ndarray,
    fitted: dict[str, Any],
    model: Any,
    tokenizer: Any,
    device: Any,
    selected_components: list[Component],
    class_covers: dict[str, list[str]],
    random_subcovers: list[list[str]],
    *,
    global_prefix_size: int,
) -> dict[str, Any]:
    selected_layers = {component.layer for component in selected_components}
    selected_by_name = {component.name: component for component in selected_components}
    global_prefix = _component_names(selected_components)[:global_prefix_size]
    row_reports: list[dict[str, Any]] = []
    ablated_margins: list[float] = []
    class_margins: list[float] = []
    prefix_margins: list[float] = []
    full_global_margins: list[float] = []
    random_mean_margins: list[float] = []

    for row, target_idx_raw in zip(eval_rows, eval_y):
        target_idx = int(target_idx_raw)
        target_label = _FOUNDATION_LABELS[target_idx]
        partner_label = _partner_label(row)
        partner_idx = _LABEL_TO_INDEX[partner_label]
        encoded, focus_idx = _encode_row(row, tokenizer, device)
        _clean_vec, clean_cache = _forward_vec_and_cache_heads(encoded, focus_idx, model, selected_layers)
        ablated_vec = _forward_vec_with_head_patches(
            encoded,
            focus_idx,
            model,
            ablate_components=selected_components,
            patch_components=[],
            clean_cache=clean_cache,
        )
        class_cover_names = class_covers[target_label]
        class_components = [selected_by_name[name] for name in class_cover_names]
        prefix_components = [selected_by_name[name] for name in global_prefix]
        class_vec = _forward_vec_with_head_patches(
            encoded,
            focus_idx,
            model,
            ablate_components=selected_components,
            patch_components=class_components,
            clean_cache=clean_cache,
        )
        prefix_vec = _forward_vec_with_head_patches(
            encoded,
            focus_idx,
            model,
            ablate_components=selected_components,
            patch_components=prefix_components,
            clean_cache=clean_cache,
        )
        full_vec = _forward_vec_with_head_patches(
            encoded,
            focus_idx,
            model,
            ablate_components=selected_components,
            patch_components=selected_components,
            clean_cache=clean_cache,
        )
        random_margins: list[float] = []
        for names in random_subcovers:
            components = [selected_by_name[name] for name in names]
            vec = _forward_vec_with_head_patches(
                encoded,
                focus_idx,
                model,
                ablate_components=selected_components,
                patch_components=components,
                clean_cache=clean_cache,
            )
            random_margins.append(_probe_margin(fitted, vec, target_idx, partner_idx))

        ablated_margin = _probe_margin(fitted, ablated_vec, target_idx, partner_idx)
        class_margin = _probe_margin(fitted, class_vec, target_idx, partner_idx)
        prefix_margin = _probe_margin(fitted, prefix_vec, target_idx, partner_idx)
        full_margin = _probe_margin(fitted, full_vec, target_idx, partner_idx)
        random_mean = float(np.mean(random_margins)) if random_margins else 0.0
        ablated_margins.append(ablated_margin)
        class_margins.append(class_margin)
        prefix_margins.append(prefix_margin)
        full_global_margins.append(full_margin)
        random_mean_margins.append(random_mean)
        row_reports.append(
            {
                "sample_id": row["sample_id"],
                "target": target_label,
                "partner": partner_label,
                "pair_kind": _pair_kind(target_label, partner_label),
                "class_cover": class_cover_names,
                "ablated_margin": float(ablated_margin),
                "class_cover_margin": float(class_margin),
                "global_prefix_margin": float(prefix_margin),
                "full_global_margin": float(full_margin),
                "random_subset_mean_margin": random_mean,
                "class_minus_global_prefix": float(class_margin - prefix_margin),
                "class_minus_random_mean": float(class_margin - random_mean),
            }
        )

    by_pair_kind: dict[str, Any] = {}
    for pair_kind in sorted({str(row["pair_kind"]) for row in row_reports}):
        subset = [row for row in row_reports if row["pair_kind"] == pair_kind]
        by_pair_kind[pair_kind] = {
            "n": int(len(subset)),
            "class_cover": _margin_summary([float(row["class_cover_margin"]) for row in subset]),
            "class_vs_global_prefix": _paired_summary(
                [float(row["class_cover_margin"]) for row in subset],
                [float(row["global_prefix_margin"]) for row in subset],
            ),
            "class_vs_random_mean": _paired_summary(
                [float(row["class_cover_margin"]) for row in subset],
                [float(row["random_subset_mean_margin"]) for row in subset],
            ),
        }

    full_gain = np.asarray(full_global_margins, dtype=np.float64) - np.asarray(ablated_margins, dtype=np.float64)
    class_gain = np.asarray(class_margins, dtype=np.float64) - np.asarray(ablated_margins, dtype=np.float64)
    valid = np.abs(full_gain) > 1e-8
    ceiling_fraction = float(np.mean(class_gain[valid] / full_gain[valid])) if np.any(valid) else 0.0
    return {
        "row_reports": row_reports,
        "margins": {
            "ablated": _margin_summary(ablated_margins),
            "class_cover": _margin_summary(class_margins),
            "global_prefix": _margin_summary(prefix_margins),
            "full_global": _margin_summary(full_global_margins),
            "random_subset_mean": _margin_summary(random_mean_margins),
        },
        "paired_controls": {
            "class_vs_global_prefix": _paired_summary(class_margins, prefix_margins),
            "class_vs_random_subset_mean": _paired_summary(class_margins, random_mean_margins),
        },
        "full_global_ceiling": {
            "mean_class_gain_fraction_of_full_global_gain": ceiling_fraction,
            "mean_full_global_minus_class_margin": float(np.mean(np.asarray(full_global_margins) - np.asarray(class_margins))),
        },
        "pair_kind_breakdown": by_pair_kind,
    }


def _load_stage27b_contract(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    return {
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
        "source_status": str(report.get("status")),
        "formal_gate_valid": bool(report.get("status") == _EXPECTED_STAGE27B_STATUS),
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    if not report["artifact_contract"]["formal_gate_valid"] or not report["component_path_contract"]["formal_gate_valid"]:
        return "STAGE27C_PER_CLASS_COVERS_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    if not report["split_contract"]["learn_eval_disjoint"]:
        return "NULL_PER_CLASS_COMPONENT_COVERS_SPLIT_INVALID"
    metrics = report["evaluation"]
    class_summary = metrics["margins"]["class_cover"]
    global_pair = metrics["paired_controls"]["class_vs_global_prefix"]
    random_pair = metrics["paired_controls"]["class_vs_random_subset_mean"]
    mean_ok = class_summary["mean"] > metrics["margins"]["global_prefix"]["mean"]
    global_ok = global_pair["win_share"] >= report["gates"]["min_control_win_share"] and global_pair["sign_test_p"] < report["gates"]["max_sign_test_p"]
    random_ok = random_pair["win_share"] >= report["gates"]["min_control_win_share"] and random_pair["sign_test_p"] < report["gates"]["max_sign_test_p"]
    positive_ok = class_summary["positive_share"] >= report["gates"]["min_positive_margin_share"]
    if mean_ok and global_ok and random_ok and positive_ok:
        return "PASS_BOUNDED_PER_CLASS_COMPONENT_COVERS"
    if mean_ok or global_ok or random_ok:
        return "GREY_PER_CLASS_COMPONENT_COVERS_PARTIAL"
    return "NULL_PER_CLASS_COMPONENT_COVERS_NOT_ESTABLISHED"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    manifest_path = _resolve(args.activation_manifest)
    stage26_path = _resolve(args.stage26_report)
    stage27a_path = _resolve(args.stage27a_report)
    stage27b_path = _resolve(args.stage27b_report)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = _split_indices(rows_by_id, sample_ids)
    X = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    y = _labels_for_task(rows_by_id, sample_ids, "interaction")
    fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _FOUNDATION_LABELS)
    component_contract = _load_component_contract(stage26_path, stage27a_path, len(_DEFAULT_SELECTED_COMPONENTS))
    stage27b_contract = _load_stage27b_contract(stage27b_path)
    selected_names = list(component_contract["expected_selected_components"])
    selected_components = [_component_from_name(name) for name in selected_names]
    for component in selected_components:
        if component.kind != "head":
            raise SystemExit(f"Stage 27C only supports selected attention heads; got {component.name}")

    learn_indices = _balanced_indices(splits["train"], y, rows_per_class=int(args.learn_rows_per_class))
    eval_indices = _balanced_indices(splits["test"], y, rows_per_class=int(args.eval_rows_per_class))
    learn_ids = [sample_ids[idx] for idx in learn_indices]
    eval_ids = [sample_ids[idx] for idx in eval_indices]
    learn_rows = [rows_by_id[sid] for sid in learn_ids]
    eval_rows = [rows_by_id[sid] for sid in eval_ids]
    learn_y = y[learn_indices]
    eval_y = y[eval_indices]
    model, tokenizer, device = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    learned = _learn_per_class_covers(
        learn_rows,
        learn_y,
        fitted,
        model,
        tokenizer,
        device,
        selected_components,
        cover_size=int(args.cover_size),
    )
    random_subcovers = _sample_random_subcovers(
        selected_names,
        cover_size=int(args.cover_size),
        n_random=int(args.n_random_subcovers),
        seed=int(args.seed),
    )
    evaluation = _evaluate_covers(
        eval_rows,
        eval_y,
        fitted,
        model,
        tokenizer,
        device,
        selected_components,
        learned["covers"],
        random_subcovers,
        global_prefix_size=int(args.cover_size),
    )
    activations_sha = _sha256_of_file(activations_path)
    report: dict[str, Any] = {
        "schema_version": "stage27c_per_class_component_covers.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": activations_sha,
        "activation_manifest_file": manifest_path.name,
        "artifact_contract": _artifact_contract(activations_sha, manifest_path),
        "component_path_contract": component_contract,
        "stage27b_context": stage27b_contract,
        "locked_readout": {"readout_key": _READOUT_KEY, "readout_name": _READOUT_NAME, "layer": _LAYER},
        "device": str(device),
        "elapsed_seconds": float(time.perf_counter() - started),
        "probe": {
            "raw_train_acc": float(fitted["train"]["acc"]),
            "raw_val_acc": float(fitted["val"]["acc"]),
            "raw_test_acc": float(fitted["test"]["acc"]),
        },
        "split_contract": {
            "learn_split": "train",
            "eval_split": "test",
            "learn_rows_per_class": int(args.learn_rows_per_class),
            "eval_rows_per_class": int(args.eval_rows_per_class),
            "learn_rows": int(len(learn_rows)),
            "eval_rows": int(len(eval_rows)),
            "learn_eval_disjoint": bool(set(learn_ids).isdisjoint(set(eval_ids))),
        },
        "selected_components": selected_names,
        "cover_size": int(args.cover_size),
        "per_class_covers": learned["covers"],
        "per_class_component_scores": learned["class_component_scores"],
        "random_subcovers": random_subcovers,
        "evaluation": evaluation,
        "gates": {
            "min_control_win_share": float(args.min_control_win_share),
            "max_sign_test_p": float(args.max_sign_test_p),
            "min_positive_margin_share": float(args.min_positive_margin_share),
        },
        "boundary": (
            "Stage 27C is bounded to Pythia-160M Stage 7 Foundation probe-logit margins inside the Stage 26/27A "
            "validated six-head component family. It does not test Noetic/40-Element covers, token sonar, exact neurons, "
            "complete circuits, raw CAS-symbol understanding, or generation control."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    eval_block = report["evaluation"]
    global_pair = eval_block["paired_controls"]["class_vs_global_prefix"]
    random_pair = eval_block["paired_controls"]["class_vs_random_subset_mean"]
    lines = [
        "# Stage 27C Per-Class Component Covers",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 artifact: `{report['artifact_contract']['status']}`",
        f"- Stage 26 source status: `{report['component_path_contract']['stage26_status']}`",
        f"- Stage 27A source status: `{report['component_path_contract']['stage27a_status']}`",
        f"- Stage 27B context status: `{report['stage27b_context']['source_status']}`",
        f"- Learn/eval disjoint: `{report['split_contract']['learn_eval_disjoint']}`",
        "",
        "## Evaluation",
        "",
        f"- Learn rows: `{report['split_contract']['learn_rows']}` ({report['split_contract']['learn_rows_per_class']} per class)",
        f"- Eval rows: `{report['split_contract']['eval_rows']}` ({report['split_contract']['eval_rows_per_class']} per class)",
        f"- Class-cover mean margin: `{eval_block['margins']['class_cover']['mean']:.6f}`",
        f"- Global-prefix mean margin: `{eval_block['margins']['global_prefix']['mean']:.6f}`",
        f"- Random-subset mean margin: `{eval_block['margins']['random_subset_mean']['mean']:.6f}`",
        f"- Full-global mean margin: `{eval_block['margins']['full_global']['mean']:.6f}`",
        f"- Class-cover positive margin share: `{eval_block['margins']['class_cover']['positive_share']:.4f}`",
        "",
        "## Paired Controls",
        "",
        f"- Class > global-prefix: `{global_pair['wins']} / {global_pair['n']}` "
        f"(share `{global_pair['win_share']:.4f}`, p `{global_pair['sign_test_p']:.6g}`, mean delta `{global_pair['mean_delta']:.6f}`)",
        f"- Class > random-subset mean: `{random_pair['wins']} / {random_pair['n']}` "
        f"(share `{random_pair['win_share']:.4f}`, p `{random_pair['sign_test_p']:.6g}`, mean delta `{random_pair['mean_delta']:.6f}`)",
        f"- Mean class gain fraction of full-global gain: `{eval_block['full_global_ceiling']['mean_class_gain_fraction_of_full_global_gain']:.6f}`",
        "",
        "## Pair-Kind Breakdown",
        "",
        "| Pair kind | n | Class mean | Class > prefix share | Class > random share |",
        "|---|---:|---:|---:|---:|",
    ]
    for kind, row in eval_block["pair_kind_breakdown"].items():
        lines.append(
            f"| `{kind}` | {row['n']} | {row['class_cover']['mean']:.6f} | "
            f"{row['class_vs_global_prefix']['win_share']:.4f} | {row['class_vs_random_mean']['win_share']:.4f} |"
        )
    lines.extend(["", "## Example Per-Class Covers", ""])
    for label in list(report["per_class_covers"])[:12]:
        lines.append(f"- `{label}`: {', '.join(f'`{name}`' for name in report['per_class_covers'][label])}")
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage7_foundation_pilot_activations_manifest_20260517.json")
    parser.add_argument("--stage26-report", default="stage26_component_attribution_20260521.json")
    parser.add_argument("--stage27a-report", default="stage27_component_path_patching_20260521.json")
    parser.add_argument("--stage27b-report", default="stage27b_component_guided_contrast_sonar_20260521.json")
    parser.add_argument("--out-report", default="stage27c_per_class_component_covers_20260521.json")
    parser.add_argument("--out-md", default="STAGE27C_PER_CLASS_COMPONENT_COVERS_20260521.md")
    parser.add_argument("--learn-rows-per-class", type=int, default=4)
    parser.add_argument("--eval-rows-per-class", type=int, default=4)
    parser.add_argument("--cover-size", type=int, default=3)
    parser.add_argument("--n-random-subcovers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=_SEED)
    parser.add_argument("--min-control-win-share", type=float, default=0.60)
    parser.add_argument("--max-sign-test-p", type=float, default=0.05)
    parser.add_argument("--min-positive-margin-share", type=float, default=0.55)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
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
                "class_mean_margin": report["evaluation"]["margins"]["class_cover"]["mean"],
                "global_prefix_mean_margin": report["evaluation"]["margins"]["global_prefix"]["mean"],
                "class_vs_global_prefix": report["evaluation"]["paired_controls"]["class_vs_global_prefix"],
                "class_vs_random_subset_mean": report["evaluation"]["paired_controls"]["class_vs_random_subset_mean"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
