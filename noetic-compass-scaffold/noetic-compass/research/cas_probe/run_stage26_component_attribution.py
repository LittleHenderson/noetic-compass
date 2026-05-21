"""Stage 26 head/MLP component attribution for CAS Harness.

This runner localizes the Stage 7 Foundation readout signal across Pythia-160M
attention heads and MLP blocks. It ranks components by projection onto the
locked Stage 7 Foundation readout subspace, then ablates the top-ranked
components and compares against same-count random component ablations.

Boundary: component attribution is not exact-neuron or circuit discovery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from capture_stage6_role_bound_activations import _find_focus_char_index, _find_token_for_char
from evaluate_stage7_factor_check import (
    _FOUNDATION_LABELS,
    _fit_readout,
    _labels_for_task,
    _load_jsonl,
    _metrics,
    _projection_basis_from_probe,
    _split_indices,
)


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 26026
_READOUT_KEY = "X_focus"
_LAYER = 6
_COMPONENT_LAYERS = tuple(range(6))


@dataclass(frozen=True)
class Component:
    kind: str
    layer: int
    head: int | None = None

    @property
    def name(self) -> str:
        if self.kind == "head":
            return f"L{self.layer}H{self.head}"
        return f"L{self.layer}MLP"


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


def _artifact_contract(activations_sha256: str, manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        return {
            "status": "MANIFEST_MISSING",
            "expected_activation_sha256": None,
            "actual_activation_sha256": activations_sha256,
            "formal_gate_valid": False,
        }
    with manifest_path.open(encoding="utf-8") as fh:
        manifest = json.load(fh)
    expected = manifest.get("output_sha256")
    matched = bool(expected == activations_sha256)
    return {
        "status": "LOCKED_ARTIFACT_MATCH" if matched else "LOCAL_RECAPTURE_HASH_MISMATCH",
        "expected_activation_sha256": expected,
        "actual_activation_sha256": activations_sha256,
        "formal_gate_valid": matched,
    }


def _all_components() -> list[Component]:
    out: list[Component] = []
    for layer in _COMPONENT_LAYERS:
        out.extend(Component("head", layer, head) for head in range(12))
        out.append(Component("mlp", layer, None))
    return out


def _component_from_name(name: str) -> Component:
    if "MLP" in name:
        layer = int(name[1:name.index("MLP")])
        return Component("mlp", layer, None)
    layer_s, head_s = name.split("H", 1)
    return Component("head", int(layer_s[1:]), int(head_s))


def _summarize_vs_random(actual: float, random_values: list[float]) -> dict[str, Any]:
    values = np.asarray(random_values, dtype=np.float64)
    if values.size == 0:
        return {"actual": float(actual), "empirical_p_random_ge_actual": 1.0, "n_random": 0}
    return {
        "actual": float(actual),
        "random_mean": float(values.mean()),
        "random_p95": float(np.quantile(values, 0.95)),
        "empirical_p_random_ge_actual": float((1 + np.sum(values >= actual)) / (values.size + 1)),
        "n_random": int(values.size),
    }


def _top_set_random_control(scores: dict[str, float], selected: list[str], n_random: int, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    names = list(scores)
    k = len(selected)
    actual = float(np.mean([scores[name] for name in selected])) if selected else 0.0
    values: list[float] = []
    for _ in range(n_random):
        sample = rng.choice(names, size=k, replace=False).tolist()
        values.append(float(np.mean([scores[name] for name in sample])))
    return _summarize_vs_random(actual, values)


def _class_drop_summary(y_true: np.ndarray, baseline_pred: np.ndarray, ablated_pred: np.ndarray) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for class_idx, label in enumerate(_FOUNDATION_LABELS):
        mask = y_true == class_idx
        if not np.any(mask):
            continue
        base_acc = float(np.mean(baseline_pred[mask] == y_true[mask]))
        ablated_acc = float(np.mean(ablated_pred[mask] == y_true[mask]))
        rows.append(
            {
                "foundation": label,
                "n": int(np.sum(mask)),
                "baseline_acc": base_acc,
                "ablated_acc": ablated_acc,
                "drop": float(base_acc - ablated_acc),
            }
        )
    rows.sort(key=lambda row: row["drop"], reverse=True)
    positive = [row["drop"] for row in rows if row["drop"] > 0]
    return {
        "top_class_drops": rows[:10],
        "max_class_drop": float(rows[0]["drop"]) if rows else 0.0,
        "mean_positive_class_drop": float(np.mean(positive)) if positive else 0.0,
        "n_positive_drop_classes": int(len(positive)),
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    if not report["artifact_contract"]["formal_gate_valid"]:
        return "STAGE26_COMPONENT_ATTRIBUTION_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"
    if not report["capture_contract"]["finite_components"]:
        return "NULL_COMPONENT_ATTRIBUTION_NOT_ESTABLISHED"
    align_ok = report["alignment_enrichment"]["random_control"]["empirical_p_random_ge_actual"] < 0.05
    ablate_ok = report["targeted_ablation_drop"]["random_control"]["empirical_p_random_ge_actual"] < 0.05
    sanity_ok = abs(report["sanity_controls"]["noop_acc_delta"]) <= float(report["sanity_controls"]["noop_acc_delta_slack"])
    class_specific = report["class_specificity"]["max_class_drop"] > max(0.0, report["targeted_ablation_drop"]["targeted_drop"])
    if align_ok and ablate_ok and sanity_ok and class_specific:
        return "PASS_BOUNDED_COMPONENT_ATTRIBUTION"
    if not align_ok and not ablate_ok:
        return "NULL_COMPONENT_ATTRIBUTION_NOT_ESTABLISHED"
    return "GREY_COMPONENT_ATTRIBUTION_UNDERPOWERED_OR_DIFFUSE"


def _load_model_and_tokenizer(allow_download: bool, device: str) -> tuple[Any, Any, Any]:
    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=not allow_download, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModel.from_pretrained(
        _MODEL_NAME,
        output_hidden_states=True,
        local_files_only=not allow_download,
    )
    actual_device = torch.device(device if device == "cuda" and torch.cuda.is_available() else "cpu")
    model.eval()
    model.to(actual_device)
    return model, tokenizer, actual_device


def _encode_row(row: dict[str, Any], tokenizer: Any, device: Any) -> tuple[Any, int]:
    text = str(row["english"])
    focus = str(row["focus_span"])
    focus_char_index = _find_focus_char_index(text, focus)
    encoded = tokenizer(
        text,
        return_tensors="pt",
        return_offsets_mapping=True,
        truncation=True,
        max_length=256,
    )
    offsets = [(int(a), int(b)) for a, b in encoded.pop("offset_mapping")[0].tolist()]
    focus_idx = _find_token_for_char(offsets, focus_char_index)
    return encoded.to(device), int(focus_idx)


def _probe_projection_score(vector: Any, projection: Any) -> float:
    import torch

    v = vector.float()
    denom = torch.linalg.vector_norm(v).clamp_min(1e-8)
    projected = v @ projection
    return float((torch.linalg.vector_norm(projected) / denom).detach().cpu())


def _capture_component_scores(
    rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    projection: Any,
    *,
    limit: int,
) -> dict[str, Any]:
    import torch

    components = _all_components()
    score_sum = {component.name: 0.0 for component in components}
    count = {component.name: 0 for component in components}
    finite = True
    focus_holder = {"idx": 0}
    handles = []
    head_dim = int(model.config.hidden_size // model.config.num_attention_heads)

    def make_attn_hook(layer_idx: int):
        dense = model.layers[layer_idx].attention.dense
        weight = dense.weight.detach()

        def hook(_module: Any, inputs: tuple[Any, ...]) -> None:
            x = inputs[0][0, focus_holder["idx"], :]
            for head in range(int(model.config.num_attention_heads)):
                start = head * head_dim
                stop = start + head_dim
                contrib = x[start:stop] @ weight[:, start:stop].T
                name = Component("head", layer_idx, head).name
                score_sum[name] += _probe_projection_score(contrib, projection)
                count[name] += 1

        return hook

    def make_mlp_hook(layer_idx: int):
        def hook(_module: Any, _inputs: tuple[Any, ...], output: Any) -> None:
            nonlocal finite
            vec = output[0, focus_holder["idx"], :]
            if not torch.isfinite(vec).all():
                finite = False
            name = Component("mlp", layer_idx, None).name
            score_sum[name] += _probe_projection_score(vec, projection)
            count[name] += 1

        return hook

    for layer_idx in _COMPONENT_LAYERS:
        handles.append(model.layers[layer_idx].attention.dense.register_forward_pre_hook(make_attn_hook(layer_idx)))
        handles.append(model.layers[layer_idx].mlp.register_forward_hook(make_mlp_hook(layer_idx)))
    try:
        selected_rows = rows if limit <= 0 else rows[:limit]
        with torch.no_grad():
            for row in selected_rows:
                encoded, focus_idx = _encode_row(row, tokenizer, device)
                focus_holder["idx"] = focus_idx
                model(**encoded)
    finally:
        for handle in handles:
            handle.remove()
    mean_scores = {
        name: float(score_sum[name] / max(count[name], 1))
        for name in score_sum
    }
    return {
        "scores": mean_scores,
        "counts": count,
        "finite_components": bool(finite and all(count[name] > 0 for name in count)),
        "n_rows": int(len(rows if limit <= 0 else rows[:limit])),
    }


def _predict_forward_subset(
    rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    fitted: dict[str, Any],
    *,
    components_to_ablate: list[Component] | None = None,
) -> np.ndarray:
    import torch

    components_to_ablate = components_to_ablate or []
    head_targets: dict[int, set[int]] = {}
    mlp_targets: set[int] = set()
    for component in components_to_ablate:
        if component.kind == "head" and component.head is not None:
            head_targets.setdefault(component.layer, set()).add(component.head)
        elif component.kind == "mlp":
            mlp_targets.add(component.layer)

    handles = []
    head_dim = int(model.config.hidden_size // model.config.num_attention_heads)

    def make_attn_ablate_hook(layer_idx: int):
        targets = set(head_targets.get(layer_idx, set()))

        def hook(_module: Any, inputs: tuple[Any, ...]) -> tuple[Any, ...]:
            if not targets:
                return inputs
            x = inputs[0].clone()
            for head in targets:
                start = head * head_dim
                stop = start + head_dim
                x[:, :, start:stop] = 0
            return (x,)

        return hook

    def make_mlp_ablate_hook(layer_idx: int):
        def hook(_module: Any, _inputs: tuple[Any, ...], output: Any) -> Any:
            if layer_idx not in mlp_targets:
                return output
            return output * 0

        return hook

    for layer_idx in _COMPONENT_LAYERS:
        if layer_idx in head_targets:
            handles.append(model.layers[layer_idx].attention.dense.register_forward_pre_hook(make_attn_ablate_hook(layer_idx)))
        if layer_idx in mlp_targets:
            handles.append(model.layers[layer_idx].mlp.register_forward_hook(make_mlp_ablate_hook(layer_idx)))
    X_focus: list[np.ndarray] = []
    try:
        with torch.no_grad():
            for row in rows:
                encoded, focus_idx = _encode_row(row, tokenizer, device)
                outputs = model(**encoded)
                vec = outputs.hidden_states[_LAYER][0, focus_idx, :].detach().cpu().float().numpy()
                X_focus.append(vec)
    finally:
        for handle in handles:
            handle.remove()
    X = np.asarray(X_focus, dtype=np.float64)
    return fitted["clf"].predict(fitted["scaler"].transform(X))


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    import torch

    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    manifest_path = _resolve(args.activation_manifest)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = _split_indices(rows_by_id, sample_ids)
    X = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    y = _labels_for_task(rows_by_id, sample_ids, "interaction")
    fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _FOUNDATION_LABELS)
    basis = _projection_basis_from_probe(fitted["scaler"], fitted["clf"])
    projection = torch.tensor(basis["projection"], dtype=torch.float32)
    model, tokenizer, device = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    projection = projection.to(device)

    capture_rows = rows if int(args.capture_limit) <= 0 else rows[: int(args.capture_limit)]
    capture = _capture_component_scores(
        capture_rows,
        model,
        tokenizer,
        device,
        projection,
        limit=0,
    )
    score_map = capture["scores"]
    ordered_components = sorted(score_map, key=lambda name: score_map[name], reverse=True)
    selected_names = ordered_components[: int(args.top_k_components)]
    selected_components = [_component_from_name(name) for name in selected_names]
    alignment_control = _top_set_random_control(
        score_map,
        selected_names,
        int(args.n_random),
        int(args.seed) + 1,
    )

    eval_ids = splits["test"]
    if int(args.eval_limit) > 0:
        eval_ids = eval_ids[: int(args.eval_limit)]
    rows_by_id_ordered = {sid: rows_by_id[sid] for sid in rows_by_id}
    eval_sample_ids = [sample_ids[int(i)] for i in eval_ids]
    eval_rows = [rows_by_id_ordered[sid] for sid in eval_sample_ids]
    y_eval = y[eval_ids]
    baseline_pred = _predict_forward_subset(eval_rows, model, tokenizer, device, fitted)
    targeted_pred = _predict_forward_subset(
        eval_rows,
        model,
        tokenizer,
        device,
        fitted,
        components_to_ablate=selected_components,
    )
    baseline_metrics = _metrics(y_eval, baseline_pred, _FOUNDATION_LABELS)
    targeted_metrics = _metrics(y_eval, targeted_pred, _FOUNDATION_LABELS)
    targeted_drop = float(baseline_metrics["acc"] - targeted_metrics["acc"])

    rng = np.random.default_rng(int(args.seed) + 2)
    all_components = _all_components()
    random_drops: list[float] = []
    for _ in range(int(args.n_random)):
        sampled = rng.choice(len(all_components), size=len(selected_components), replace=False).astype(int).tolist()
        random_components = [all_components[i] for i in sampled]
        random_pred = _predict_forward_subset(
            eval_rows,
            model,
            tokenizer,
            device,
            fitted,
            components_to_ablate=random_components,
        )
        random_metrics = _metrics(y_eval, random_pred, _FOUNDATION_LABELS)
        random_drops.append(float(baseline_metrics["acc"] - random_metrics["acc"]))
    ablation_control = _summarize_vs_random(targeted_drop, random_drops)
    noop_pred = _predict_forward_subset(eval_rows, model, tokenizer, device, fitted)
    noop_metrics = _metrics(y_eval, noop_pred, _FOUNDATION_LABELS)
    class_specificity = _class_drop_summary(y_eval, baseline_pred, targeted_pred)

    report: dict[str, Any] = {
        "schema_version": "stage26_component_attribution.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "activation_manifest_file": manifest_path.name,
        "artifact_contract": _artifact_contract(_sha256_of_file(activations_path), manifest_path),
        "locked_readout": {"readout_key": _READOUT_KEY, "readout_name": "focus_token", "layer": _LAYER},
        "device": str(device),
        "elapsed_seconds": float(time.perf_counter() - started),
        "probe": {
            "raw_train_acc": float(fitted["train"]["acc"]),
            "raw_val_acc": float(fitted["val"]["acc"]),
            "raw_test_acc": float(fitted["test"]["acc"]),
            "basis_rank": int(basis["rank"]),
        },
        "capture_contract": {
            "n_rows": int(capture["n_rows"]),
            "n_components": int(len(score_map)),
            "finite_components": bool(capture["finite_components"]),
            "component_counts_min": int(min(capture["counts"].values())),
            "component_counts_max": int(max(capture["counts"].values())),
        },
        "component_ranking": [
            {"component": name, "projection_score": float(score_map[name])}
            for name in ordered_components
        ],
        "alignment_enrichment": {
            "selected_components": selected_names,
            "selected_mean_projection_score": float(np.mean([score_map[name] for name in selected_names])),
            "random_control": alignment_control,
        },
        "targeted_ablation_drop": {
            "eval_rows": int(len(eval_rows)),
            "baseline_acc": float(baseline_metrics["acc"]),
            "targeted_ablated_acc": float(targeted_metrics["acc"]),
            "targeted_drop": targeted_drop,
            "random_control": ablation_control,
        },
        "class_specificity": class_specificity,
        "sanity_controls": {
            "noop_acc": float(noop_metrics["acc"]),
            "noop_acc_delta": float(baseline_metrics["acc"] - noop_metrics["acc"]),
            "noop_acc_delta_slack": float(args.noop_slack),
        },
        "boundary": (
            "Stage 26 is bounded component attribution over attention heads and MLP blocks. "
            "It does not identify exact neurons, complete circuits, raw CAS-symbol understanding, "
            "an internal CAS compiler, free-form generation control, or cross-model component generality."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 26 Component Attribution",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Artifact Contract",
        "",
        f"- Contract: `{report['artifact_contract']['status']}`",
        f"- Formal gate valid: `{report['artifact_contract']['formal_gate_valid']}`",
        "",
        "## Capture",
        "",
        f"- Rows: `{report['capture_contract']['n_rows']}`",
        f"- Components: `{report['capture_contract']['n_components']}`",
        f"- Finite components: `{report['capture_contract']['finite_components']}`",
        "",
        "## Alignment",
        "",
        f"- Selected mean projection score: `{report['alignment_enrichment']['selected_mean_projection_score']:.6f}`",
        f"- p(random >= actual): `{report['alignment_enrichment']['random_control']['empirical_p_random_ge_actual']:.4f}`",
        "",
        "## Ablation",
        "",
        f"- Eval rows: `{report['targeted_ablation_drop']['eval_rows']}`",
        f"- Baseline acc: `{report['targeted_ablation_drop']['baseline_acc']:.4f}`",
        f"- Targeted ablated acc: `{report['targeted_ablation_drop']['targeted_ablated_acc']:.4f}`",
        f"- Targeted drop: `{report['targeted_ablation_drop']['targeted_drop']:.4f}`",
        f"- p(random >= actual): `{report['targeted_ablation_drop']['random_control']['empirical_p_random_ge_actual']:.4f}`",
        "",
        "## Top Components",
        "",
    ]
    for row in report["component_ranking"][:20]:
        lines.append(f"- `{row['component']}`: `{row['projection_score']:.6f}`")
    lines.extend(["", "## Class Specificity", ""])
    for row in report["class_specificity"]["top_class_drops"][:10]:
        lines.append(
            f"- `{row['foundation']}` n={row['n']} baseline={row['baseline_acc']:.3f} "
            f"ablated={row['ablated_acc']:.3f} drop={row['drop']:.3f}"
        )
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage7_foundation_pilot_activations_manifest_20260517.json")
    parser.add_argument("--out-report", default="stage26_component_attribution_20260521.json")
    parser.add_argument("--out-md", default="STAGE26_COMPONENT_ATTRIBUTION_20260521.md")
    parser.add_argument("--capture-limit", type=int, default=0)
    parser.add_argument("--eval-limit", type=int, default=512)
    parser.add_argument("--top-k-components", type=int, default=6)
    parser.add_argument("--n-random", type=int, default=30)
    parser.add_argument("--seed", type=int, default=_SEED)
    parser.add_argument("--noop-slack", type=float, default=0.01)
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
                "alignment_p": report["alignment_enrichment"]["random_control"]["empirical_p_random_ge_actual"],
                "targeted_drop": report["targeted_ablation_drop"]["targeted_drop"],
                "ablation_p": report["targeted_ablation_drop"]["random_control"]["empirical_p_random_ge_actual"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
