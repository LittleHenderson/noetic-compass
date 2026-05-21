"""Stage 27A component path-patching for CAS Harness.

This runner tests whether the Stage 26 selected attention-head family is
sufficient to restore the Stage 7 Foundation readout after targeted ablation.

Boundary: path patching is head-level readout-path evidence. It is not exact
neuron discovery, complete circuit discovery, raw CAS-symbol understanding, or
free-form generation control.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import (
    _FOUNDATION_LABELS,
    _fit_readout,
    _labels_for_task,
    _load_jsonl,
    _metrics,
    _split_indices,
)
from run_stage26_component_attribution import (
    Component,
    _artifact_contract,
    _component_from_name,
    _encode_row,
    _load_model_and_tokenizer,
    _matched_component_names,
    _summarize_vs_random,
)


_HERE = Path(__file__).resolve().parent
_SEED = 27027
_READOUT_KEY = "X_focus"
_LAYER = 6
_EXPECTED_STAGE26_STATUS = "PASS_BOUNDED_COMPONENT_ATTRIBUTION"
_DEFAULT_SELECTED_COMPONENTS = ("L5H3", "L5H5", "L5H0", "L5H10", "L1H6", "L5H6")


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _head_targets(components: list[Component]) -> dict[int, set[int]]:
    targets: dict[int, set[int]] = {}
    for component in components:
        if component.kind != "head" or component.head is None:
            raise ValueError(f"Stage 27A only supports attention-head components, got {component}")
        targets.setdefault(component.layer, set()).add(component.head)
    return targets


def _matched_head_components(selected_names: list[str], rng: np.random.Generator) -> list[str]:
    raw = _matched_component_names(selected_names, rng)
    selected = set(selected_names)
    out: list[str] = []
    used: set[str] = set()
    for selected_name, candidate in zip(selected_names, raw):
        selected_component = _component_from_name(selected_name)
        if candidate not in selected and candidate not in used:
            out.append(candidate)
            used.add(candidate)
            continue
        for head in range(12):
            fallback = Component("head", selected_component.layer, head).name
            if fallback not in selected and fallback not in used:
                out.append(fallback)
                used.add(fallback)
                break
        else:
            out.append(candidate)
    return out


def _load_stage26_selection(path: Path, top_k: int) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        report = json.load(fh)
    selected = list(report.get("alignment_enrichment", {}).get("selected_components", []))[:top_k]
    return {
        "status": str(report.get("status")),
        "selected_components": selected,
        "source_file": path.name,
        "source_sha256": _sha256_of_file(path),
    }


def _forward_vec_and_cache_heads(
    encoded: Any,
    focus_idx: int,
    model: Any,
    cache_layers: set[int],
) -> tuple[np.ndarray, dict[tuple[int, int], Any]]:
    import torch

    head_dim = int(model.config.hidden_size // model.config.num_attention_heads)
    cache: dict[tuple[int, int], Any] = {}
    handles = []

    def make_hook(layer_idx: int):
        def hook(_module: Any, inputs: tuple[Any, ...]) -> None:
            x = inputs[0].detach()
            for head in range(int(model.config.num_attention_heads)):
                start = head * head_dim
                stop = start + head_dim
                cache[(layer_idx, head)] = x[:, :, start:stop].detach().clone()

        return hook

    for layer_idx in sorted(cache_layers):
        handles.append(model.layers[layer_idx].attention.dense.register_forward_pre_hook(make_hook(layer_idx)))
    try:
        with torch.no_grad():
            outputs = model(**encoded)
            vec = outputs.hidden_states[_LAYER][0, focus_idx, :].detach().cpu().float().numpy()
    finally:
        for handle in handles:
            handle.remove()
    return vec, cache


def _forward_vec_with_head_patches(
    encoded: Any,
    focus_idx: int,
    model: Any,
    *,
    ablate_components: list[Component],
    patch_components: list[Component],
    clean_cache: dict[tuple[int, int], Any],
) -> np.ndarray:
    import torch

    ablate_targets = _head_targets(ablate_components) if ablate_components else {}
    patch_targets = _head_targets(patch_components) if patch_components else {}
    hook_layers = sorted(set(ablate_targets) | set(patch_targets))
    head_dim = int(model.config.hidden_size // model.config.num_attention_heads)
    handles = []

    def make_hook(layer_idx: int):
        def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
            x = inputs[0].clone()
            for head in ablate_targets.get(layer_idx, set()):
                start = head * head_dim
                stop = start + head_dim
                x[:, :, start:stop] = 0
            for head in patch_targets.get(layer_idx, set()):
                key = (layer_idx, head)
                if key not in clean_cache:
                    raise KeyError(f"missing clean cached head slice for {key}")
                start = head * head_dim
                stop = start + head_dim
                x[:, :, start:stop] = clean_cache[key].to(device=x.device, dtype=x.dtype)
            return (x,)

        return hook

    for layer_idx in hook_layers:
        handles.append(model.layers[layer_idx].attention.dense.register_forward_pre_hook(make_hook(layer_idx)))
    try:
        with torch.no_grad():
            outputs = model(**encoded)
            return outputs.hidden_states[_LAYER][0, focus_idx, :].detach().cpu().float().numpy()
    finally:
        for handle in handles:
            handle.remove()


def _predict_from_vectors(vectors: list[np.ndarray], fitted: dict[str, Any]) -> np.ndarray:
    X = np.asarray(vectors, dtype=np.float64)
    return fitted["clf"].predict(fitted["scaler"].transform(X))


def _class_restoration_summary(
    y_true: np.ndarray,
    baseline_pred: np.ndarray,
    ablated_pred: np.ndarray,
    patched_pred: np.ndarray,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for class_idx, label in enumerate(_FOUNDATION_LABELS):
        mask = y_true == class_idx
        if not np.any(mask):
            continue
        base_acc = float(np.mean(baseline_pred[mask] == y_true[mask]))
        ablated_acc = float(np.mean(ablated_pred[mask] == y_true[mask]))
        patched_acc = float(np.mean(patched_pred[mask] == y_true[mask]))
        lost = base_acc - ablated_acc
        recovered = patched_acc - ablated_acc
        rows.append(
            {
                "foundation": label,
                "n": int(np.sum(mask)),
                "baseline_acc": base_acc,
                "ablated_acc": ablated_acc,
                "patched_acc": patched_acc,
                "lost": float(lost),
                "recovered": float(recovered),
                "recovery_fraction": float(recovered / lost) if lost > 1e-12 else 0.0,
            }
        )
    rows.sort(key=lambda row: (row["lost"], row["recovered"]), reverse=True)
    top_lost = rows[:10]
    visible = [row for row in top_lost if row["lost"] > 0 and row["recovered"] > 0]
    return {
        "top_restored_classes": top_lost,
        "n_top_lost_with_positive_restoration": int(len(visible)),
        "mean_top_lost_recovery_fraction": float(np.mean([row["recovery_fraction"] for row in visible])) if visible else 0.0,
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    if not report["artifact_contract"]["formal_gate_valid"] or not report["stage26_contract"]["formal_gate_valid"]:
        return "STAGE27_COMPONENT_PATH_PATCHING_DIAGNOSTIC_ONLY_CONTRACT_MISMATCH"
    ablation_ok = report["path_patching"]["targeted_drop"] >= float(report["gates"]["min_targeted_drop"])
    patch_ok = report["path_patching"]["recovery_fraction"] >= float(report["gates"]["min_recovery_fraction"])
    control_ok = report["matched_patch_control"]["empirical_p_random_ge_actual"] < float(report["gates"]["max_control_p"])
    sanity_ok = report["sanity_controls"]["baseline_repeat_disagreement_rate"] <= float(report["gates"]["max_repeat_disagreement_rate"])
    class_ok = report["class_restoration"]["n_top_lost_with_positive_restoration"] > 0
    if ablation_ok and patch_ok and control_ok and sanity_ok and class_ok:
        return "PASS_BOUNDED_COMPONENT_PATH_PATCHING"
    if not ablation_ok or not patch_ok:
        return "NULL_COMPONENT_PATH_PATCHING_NOT_ESTABLISHED"
    return "GREY_COMPONENT_PATH_PATCHING_PARTIAL"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    manifest_path = _resolve(args.activation_manifest)
    stage26_path = _resolve(args.stage26_report)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = _split_indices(rows_by_id, sample_ids)
    X = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    y = _labels_for_task(rows_by_id, sample_ids, "interaction")
    fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _FOUNDATION_LABELS)

    stage26 = _load_stage26_selection(stage26_path, int(args.top_k_components))
    selected_names = list(stage26["selected_components"])
    if not selected_names:
        selected_names = list(_DEFAULT_SELECTED_COMPONENTS[: int(args.top_k_components)])
    selected_components = [_component_from_name(name) for name in selected_names]
    for component in selected_components:
        if component.kind != "head":
            raise SystemExit(f"Stage 27A only supports head components; got {component.name}")

    eval_ids = splits["test"]
    if int(args.eval_limit) > 0:
        eval_ids = eval_ids[: int(args.eval_limit)]
    eval_sample_ids = [sample_ids[int(i)] for i in eval_ids]
    eval_rows = [rows_by_id[sid] for sid in eval_sample_ids]
    y_eval = y[eval_ids]

    model, tokenizer, device = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    cache_layers = {component.layer for component in selected_components}
    rng = np.random.default_rng(int(args.seed))
    random_patch_sets = [
        [_component_from_name(name) for name in _matched_head_components(selected_names, rng)]
        for _ in range(int(args.n_random))
    ]

    baseline_vectors: list[np.ndarray] = []
    repeat_vectors: list[np.ndarray] = []
    ablated_vectors: list[np.ndarray] = []
    patched_vectors: list[np.ndarray] = []
    random_patch_vectors: list[list[np.ndarray]] = [[] for _ in range(int(args.n_random))]

    for row in eval_rows:
        encoded, focus_idx = _encode_row(row, tokenizer, device)
        baseline_vec, clean_cache = _forward_vec_and_cache_heads(encoded, focus_idx, model, cache_layers)
        baseline_vectors.append(baseline_vec)
        repeat_vectors.append(
            _forward_vec_with_head_patches(
                encoded,
                focus_idx,
                model,
                ablate_components=[],
                patch_components=[],
                clean_cache=clean_cache,
            )
        )
        ablated_vectors.append(
            _forward_vec_with_head_patches(
                encoded,
                focus_idx,
                model,
                ablate_components=selected_components,
                patch_components=[],
                clean_cache=clean_cache,
            )
        )
        patched_vectors.append(
            _forward_vec_with_head_patches(
                encoded,
                focus_idx,
                model,
                ablate_components=selected_components,
                patch_components=selected_components,
                clean_cache=clean_cache,
            )
        )
        for i, random_components in enumerate(random_patch_sets):
            layers_needed = {component.layer for component in random_components}
            missing_layers = layers_needed - cache_layers
            if missing_layers:
                raise RuntimeError(f"matched control used uncached layers: {sorted(missing_layers)}")
            random_patch_vectors[i].append(
                _forward_vec_with_head_patches(
                    encoded,
                    focus_idx,
                    model,
                    ablate_components=selected_components,
                    patch_components=random_components,
                    clean_cache=clean_cache,
                )
            )

    baseline_pred = _predict_from_vectors(baseline_vectors, fitted)
    repeat_pred = _predict_from_vectors(repeat_vectors, fitted)
    ablated_pred = _predict_from_vectors(ablated_vectors, fitted)
    patched_pred = _predict_from_vectors(patched_vectors, fitted)
    random_patch_pred = [_predict_from_vectors(vectors, fitted) for vectors in random_patch_vectors]

    baseline_metrics = _metrics(y_eval, baseline_pred, _FOUNDATION_LABELS)
    repeat_metrics = _metrics(y_eval, repeat_pred, _FOUNDATION_LABELS)
    ablated_metrics = _metrics(y_eval, ablated_pred, _FOUNDATION_LABELS)
    patched_metrics = _metrics(y_eval, patched_pred, _FOUNDATION_LABELS)
    targeted_drop = float(baseline_metrics["acc"] - ablated_metrics["acc"])
    recovered = float(patched_metrics["acc"] - ablated_metrics["acc"])
    recovery_fraction = float(recovered / targeted_drop) if targeted_drop > 1e-12 else 0.0
    random_recovery_fractions: list[float] = []
    random_recoveries: list[float] = []
    for pred in random_patch_pred:
        random_acc = float(np.mean(pred == y_eval))
        random_recovery = random_acc - float(ablated_metrics["acc"])
        random_recoveries.append(float(random_recovery))
        random_recovery_fractions.append(float(random_recovery / targeted_drop) if targeted_drop > 1e-12 else 0.0)
    matched_control = _summarize_vs_random(recovery_fraction, random_recovery_fractions)
    class_restoration = _class_restoration_summary(y_eval, baseline_pred, ablated_pred, patched_pred)
    activations_sha = _sha256_of_file(activations_path)

    report: dict[str, Any] = {
        "schema_version": "stage27_component_path_patching.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": activations_sha,
        "activation_manifest_file": manifest_path.name,
        "artifact_contract": _artifact_contract(activations_sha, manifest_path),
        "stage26_contract": {
            "source_file": stage26["source_file"],
            "source_sha256": stage26["source_sha256"],
            "source_status": stage26["status"],
            "selected_components": selected_names,
            "formal_gate_valid": bool(stage26["status"] == _EXPECTED_STAGE26_STATUS and selected_names == list(_DEFAULT_SELECTED_COMPONENTS[: int(args.top_k_components)])),
        },
        "locked_readout": {"readout_key": _READOUT_KEY, "readout_name": "focus_token", "layer": _LAYER},
        "device": str(device),
        "elapsed_seconds": float(time.perf_counter() - started),
        "eval_rows": int(len(eval_rows)),
        "probe": {
            "raw_train_acc": float(fitted["train"]["acc"]),
            "raw_val_acc": float(fitted["val"]["acc"]),
            "raw_test_acc": float(fitted["test"]["acc"]),
        },
        "path_patching": {
            "selected_components": selected_names,
            "baseline_acc": float(baseline_metrics["acc"]),
            "ablated_acc": float(ablated_metrics["acc"]),
            "patched_acc": float(patched_metrics["acc"]),
            "targeted_drop": targeted_drop,
            "recovered_acc": recovered,
            "recovery_fraction": recovery_fraction,
        },
        "matched_patch_control": {
            **matched_control,
            "random_recovered_acc_mean": float(np.mean(random_recoveries)) if random_recoveries else 0.0,
            "random_patch_sets": [[component.name for component in components] for components in random_patch_sets],
        },
        "class_restoration": class_restoration,
        "sanity_controls": {
            "baseline_repeat_acc": float(repeat_metrics["acc"]),
            "baseline_repeat_disagreement_rate": float(np.mean(baseline_pred != repeat_pred)),
        },
        "gates": {
            "min_targeted_drop": float(args.min_targeted_drop),
            "min_recovery_fraction": float(args.min_recovery_fraction),
            "max_control_p": float(args.max_control_p),
            "max_repeat_disagreement_rate": float(args.max_repeat_disagreement_rate),
        },
        "boundary": (
            "Stage 27A is bounded path-patching over the Stage 26 selected Pythia-160M attention-head family. "
            "It does not identify exact neurons, complete circuits, raw CAS-symbol understanding, an internal "
            "CAS compiler, free-form generation control, or cross-model component generality."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 27A Component Path-Patching",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Contracts",
        "",
        f"- Stage 7 artifact: `{report['artifact_contract']['status']}`",
        f"- Stage 26 source status: `{report['stage26_contract']['source_status']}`",
        f"- Formal gate valid: `{report['artifact_contract']['formal_gate_valid'] and report['stage26_contract']['formal_gate_valid']}`",
        "",
        "## Path Patching",
        "",
        f"- Eval rows: `{report['eval_rows']}`",
        f"- Baseline acc: `{report['path_patching']['baseline_acc']:.4f}`",
        f"- Ablated acc: `{report['path_patching']['ablated_acc']:.4f}`",
        f"- Patched acc: `{report['path_patching']['patched_acc']:.4f}`",
        f"- Targeted drop: `{report['path_patching']['targeted_drop']:.4f}`",
        f"- Recovered acc: `{report['path_patching']['recovered_acc']:.4f}`",
        f"- Recovery fraction: `{report['path_patching']['recovery_fraction']:.4f}`",
        "",
        "## Matched Patch Control",
        "",
        f"- p(random >= actual): `{report['matched_patch_control']['empirical_p_random_ge_actual']:.4f}`",
        f"- Random mean recovery fraction: `{report['matched_patch_control']['random_mean']:.4f}`",
        f"- Random p95 recovery fraction: `{report['matched_patch_control']['random_p95']:.4f}`",
        "",
        "## Selected Components",
        "",
    ]
    for name in report["path_patching"]["selected_components"]:
        lines.append(f"- `{name}`")
    lines.extend(["", "## Top Restored Classes", ""])
    for row in report["class_restoration"]["top_restored_classes"][:10]:
        lines.append(
            f"- `{row['foundation']}` n={row['n']} baseline={row['baseline_acc']:.3f} "
            f"ablated={row['ablated_acc']:.3f} patched={row['patched_acc']:.3f} "
            f"lost={row['lost']:.3f} recovered={row['recovered']:.3f}"
        )
    lines.extend(["", "## Sanity Controls", ""])
    lines.append(f"- Baseline repeat disagreement rate: `{report['sanity_controls']['baseline_repeat_disagreement_rate']:.6f}`")
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage7_foundation_pilot_activations_manifest_20260517.json")
    parser.add_argument("--stage26-report", default="stage26_component_attribution_20260521.json")
    parser.add_argument("--out-report", default="stage27_component_path_patching_20260521.json")
    parser.add_argument("--out-md", default="STAGE27_COMPONENT_PATH_PATCHING_20260521.md")
    parser.add_argument("--eval-limit", type=int, default=512)
    parser.add_argument("--top-k-components", type=int, default=6)
    parser.add_argument("--n-random", type=int, default=30)
    parser.add_argument("--seed", type=int, default=_SEED)
    parser.add_argument("--min-targeted-drop", type=float, default=0.25)
    parser.add_argument("--min-recovery-fraction", type=float, default=0.50)
    parser.add_argument("--max-control-p", type=float, default=0.05)
    parser.add_argument("--max-repeat-disagreement-rate", type=float, default=0.0)
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
                "targeted_drop": report["path_patching"]["targeted_drop"],
                "recovery_fraction": report["path_patching"]["recovery_fraction"],
                "matched_control_p": report["matched_patch_control"]["empirical_p_random_ge_actual"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
