"""Stage 25 SAE feature-localization pilot for CAS Harness.

This runner trains a small overcomplete ReLU sparse autoencoder over the
locked Stage 7 Pythia-160M Foundation readout activations
(`X_focus[:, 6, :]`). It evaluates SAE feature candidates against the trained
Stage 7 Foundation probe directions and matched random feature controls.

Boundary: SAE features are feature candidates, not exact neurons.
"""

from __future__ import annotations

import argparse
import hashlib
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
    _metrics,
    _split_indices,
)


_HERE = Path(__file__).resolve().parent
_SEED = 25025
_READOUT_KEY = "X_focus"
_LAYER = 6


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
    if expected is None and isinstance(manifest.get("replacement_artifact_contract"), dict):
        expected = manifest["replacement_artifact_contract"].get("output_sha256")
    matched = bool(expected == activations_sha256)
    return {
        "status": "LOCKED_ARTIFACT_MATCH" if matched else "LOCAL_RECAPTURE_HASH_MISMATCH",
        "expected_activation_sha256": expected,
        "actual_activation_sha256": activations_sha256,
        "formal_gate_valid": matched,
    }


def _standardize_train(X: np.ndarray, idx_train: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = X[idx_train].mean(axis=0)
    std = X[idx_train].std(axis=0)
    std = np.where(std < 1e-6, 1.0, std)
    return (X - mean[None, :]) / std[None, :], mean, std


def _unit_rows(matrix: np.ndarray) -> np.ndarray:
    arr = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    return arr / np.maximum(norms, 1e-12)


def _probe_z_directions(fitted: dict[str, Any]) -> np.ndarray:
    return np.asarray(fitted["clf"].coef_, dtype=np.float64)


def _feature_alignment(decoder_features: np.ndarray, probe_directions: np.ndarray) -> dict[str, Any]:
    feature_unit = _unit_rows(decoder_features)
    probe_unit = _unit_rows(probe_directions)
    sims = feature_unit @ probe_unit.T
    abs_sims = np.abs(sims)
    best_class_idx = np.argmax(abs_sims, axis=1)
    best_abs = abs_sims[np.arange(abs_sims.shape[0]), best_class_idx]
    return {
        "similarity": sims,
        "best_class_idx": best_class_idx,
        "best_abs_alignment": best_abs,
    }


def _top_alignment_summary(alignment: dict[str, Any], top_k: int) -> dict[str, Any]:
    best_abs = np.asarray(alignment["best_abs_alignment"], dtype=np.float64)
    best_class_idx = np.asarray(alignment["best_class_idx"], dtype=np.int64)
    ordered = np.argsort(best_abs)[::-1][:top_k]
    return {
        "top_features": [
            {
                "feature": int(feature_idx),
                "foundation": _FOUNDATION_LABELS[int(best_class_idx[feature_idx])],
                "abs_alignment": float(best_abs[feature_idx]),
            }
            for feature_idx in ordered
        ],
        "top_k_mean_abs_alignment": float(np.mean(best_abs[ordered])) if ordered.size else 0.0,
        "all_feature_mean_abs_alignment": float(np.mean(best_abs)) if best_abs.size else 0.0,
    }


def _random_alignment_control(
    n_features: int,
    hidden_dim: int,
    probe_directions: np.ndarray,
    top_k: int,
    n_random: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(n_random):
        random_features = rng.standard_normal((n_features, hidden_dim))
        alignment = _feature_alignment(random_features, probe_directions)
        values.append(_top_alignment_summary(alignment, top_k)["top_k_mean_abs_alignment"])
    arr = np.asarray(values, dtype=np.float64)
    return {
        "random_mean": float(arr.mean()) if arr.size else 0.0,
        "random_p95": float(np.quantile(arr, 0.95)) if arr.size else 0.0,
        "values": [float(x) for x in values],
    }


def _summarize_vs_random(actual: float, random_values: list[float]) -> dict[str, Any]:
    arr = np.asarray(random_values, dtype=np.float64)
    if arr.size == 0:
        return {"actual": float(actual), "empirical_p_random_ge_actual": 1.0, "n_random": 0}
    return {
        "actual": float(actual),
        "random_mean": float(arr.mean()),
        "random_p95": float(np.quantile(arr, 0.95)),
        "empirical_p_random_ge_actual": float((1 + np.sum(arr >= actual)) / (arr.size + 1)),
        "n_random": int(arr.size),
    }


def _feature_specificity(feature_acts: np.ndarray, y: np.ndarray, idx_eval: np.ndarray, feature_indices: list[int]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    y_eval = y[idx_eval]
    acts_eval = feature_acts[idx_eval]
    for feature_idx in feature_indices:
        values = acts_eval[:, feature_idx]
        means = []
        for class_idx, label in enumerate(_FOUNDATION_LABELS):
            class_values = values[y_eval == class_idx]
            means.append((label, float(class_values.mean()) if class_values.size else 0.0))
        means_sorted = sorted(means, key=lambda item: item[1], reverse=True)
        top_label, top_mean = means_sorted[0]
        other_mean = float(np.mean([value for _label, value in means_sorted[1:]])) if len(means_sorted) > 1 else 0.0
        rows.append(
            {
                "feature": int(feature_idx),
                "top_foundation": top_label,
                "top_mean_activation": float(top_mean),
                "other_mean_activation": other_mean,
                "top_minus_other": float(top_mean - other_mean),
            }
        )
    return {
        "features": rows,
        "mean_top_minus_other": float(np.mean([row["top_minus_other"] for row in rows])) if rows else 0.0,
    }


def _random_specificity_control(
    feature_acts: np.ndarray,
    y: np.ndarray,
    idx_eval: np.ndarray,
    k: int,
    n_random: int,
    seed: int,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    n_features = int(feature_acts.shape[1])
    values: list[float] = []
    for _ in range(n_random):
        feature_indices = rng.choice(n_features, size=k, replace=False).astype(int).tolist()
        values.append(_feature_specificity(feature_acts, y, idx_eval, feature_indices)["mean_top_minus_other"])
    return {"values": [float(x) for x in values]}


def _predict_with_probe(raw_X: np.ndarray, fitted: dict[str, Any]) -> np.ndarray:
    return fitted["clf"].predict(fitted["scaler"].transform(raw_X))


def _status_from_gates(report: dict[str, Any]) -> str:
    if not report["artifact_contract"]["formal_gate_valid"]:
        return "STAGE25_SAE_FEATURE_READOUT_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"
    recon_ok = report["reconstruction"]["heldout_explained_variance"] >= 0.80
    sparse = report["sparsity"]
    sparsity_ok = 5 <= sparse["mean_active_features_per_row"] <= 250 and sparse["dead_feature_rate"] < 0.80
    align_ok = report["cas_alignment"]["random_control"]["empirical_p_random_ge_actual"] < 0.05
    spec_ok = report["feature_specificity"]["random_control"]["empirical_p_random_ge_actual"] < 0.05
    causal_ok = report["causal_feature_drop"]["random_control"]["empirical_p_random_ge_actual"] < 0.05
    if recon_ok and sparsity_ok and align_ok and spec_ok and causal_ok:
        return "PASS_BOUNDED_SAE_FEATURE_READOUT"
    if not recon_ok or not sparsity_ok or (not align_ok and not spec_ok):
        return "NULL_SAE_FEATURE_READOUT_NOT_ESTABLISHED"
    return "GREY_SAE_FEATURE_READOUT_UNDERPOWERED_OR_TEXT_EXPLAINED"


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 25 SAE Feature Localization Pilot",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Artifact Contract",
        "",
        f"- Contract: `{report['artifact_contract']['status']}`",
        f"- Formal gate valid: `{report['artifact_contract']['formal_gate_valid']}`",
        "",
        "## Reconstruction",
        "",
        f"- Heldout explained variance: `{report['reconstruction']['heldout_explained_variance']:.4f}`",
        f"- Heldout MSE: `{report['reconstruction']['heldout_mse']:.6f}`",
        "",
        "## Sparsity",
        "",
        f"- Mean active features per row: `{report['sparsity']['mean_active_features_per_row']:.2f}`",
        f"- Dead feature rate: `{report['sparsity']['dead_feature_rate']:.4f}`",
        "",
        "## CAS Alignment",
        "",
        f"- Top-k mean abs alignment: `{report['cas_alignment']['top_k_mean_abs_alignment']:.6f}`",
        f"- p(random >= actual): `{report['cas_alignment']['random_control']['empirical_p_random_ge_actual']:.4f}`",
        "",
        "## Feature Specificity",
        "",
        f"- Mean top-minus-other activation: `{report['feature_specificity']['mean_top_minus_other']:.6f}`",
        f"- p(random >= actual): `{report['feature_specificity']['random_control']['empirical_p_random_ge_actual']:.4f}`",
        "",
        "## Causal Feature Drop",
        "",
        f"- Reconstructed baseline acc: `{report['causal_feature_drop']['reconstructed_baseline_acc']:.4f}`",
        f"- Targeted removal acc: `{report['causal_feature_drop']['targeted_removed_acc']:.4f}`",
        f"- Targeted drop: `{report['causal_feature_drop']['targeted_drop']:.4f}`",
        f"- p(random >= actual): `{report['causal_feature_drop']['random_control']['empirical_p_random_ge_actual']:.4f}`",
        "",
        "## Top Feature Candidates",
        "",
    ]
    for item in report["cas_alignment"]["top_features"][:20]:
        lines.append(
            f"- Feature `{item['feature']}` -> `{item['foundation']}` "
            f"alignment `{item['abs_alignment']:.6f}`"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            report["boundary"],
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def _torch_train_sae(
    Z: np.ndarray,
    idx_train: np.ndarray,
    idx_eval: np.ndarray,
    args: argparse.Namespace,
) -> dict[str, Any]:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset

    torch.manual_seed(int(args.seed))
    device = torch.device(args.device if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    X_train = torch.tensor(Z[idx_train], dtype=torch.float32)
    loader = DataLoader(
        TensorDataset(X_train),
        batch_size=int(args.batch_size),
        shuffle=True,
        drop_last=False,
    )

    class SAE(nn.Module):
        def __init__(self, input_dim: int, n_features: int) -> None:
            super().__init__()
            self.encoder = nn.Linear(input_dim, n_features)
            self.decoder = nn.Linear(n_features, input_dim, bias=True)

        def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            acts = F.relu(self.encoder(x))
            recon = self.decoder(acts)
            return recon, acts

    model = SAE(int(Z.shape[1]), int(args.n_features)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=float(args.learning_rate))
    started = time.perf_counter()
    losses: list[dict[str, float]] = []
    step = 0
    while step < int(args.max_steps):
        for (batch,) in loader:
            batch = batch.to(device)
            recon, acts = model(batch)
            mse = F.mse_loss(recon, batch)
            l1 = acts.mean()
            loss = mse + float(args.l1_coefficient) * l1
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            step += 1
            if step == 1 or step % int(args.log_every) == 0 or step >= int(args.max_steps):
                losses.append({"step": int(step), "mse": float(mse.detach().cpu()), "l1": float(l1.detach().cpu())})
            if step >= int(args.max_steps):
                break

    with torch.no_grad():
        Z_tensor = torch.tensor(Z, dtype=torch.float32, device=device)
        recon, acts = model(Z_tensor)
        recon_np = recon.cpu().numpy()
        acts_np = acts.cpu().numpy()
        decoder_features = model.decoder.weight.detach().cpu().numpy().T
        checkpoint = {
            "state_dict": model.state_dict(),
            "config": {
                "input_dim": int(Z.shape[1]),
                "n_features": int(args.n_features),
                "seed": int(args.seed),
                "max_steps": int(args.max_steps),
                "l1_coefficient": float(args.l1_coefficient),
            },
        }
        checkpoint_path = _resolve(args.out_checkpoint)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(checkpoint, checkpoint_path)

    return {
        "device": str(device),
        "elapsed_seconds": float(time.perf_counter() - started),
        "losses": losses,
        "reconstruction": recon_np,
        "feature_acts": acts_np,
        "decoder_features": decoder_features,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    manifest_path = _resolve(args.activation_manifest)
    if not activations_path.exists():
        raise FileNotFoundError(f"missing Stage 25 activation artifact: {activations_path}")

    activations_sha = _sha256_of_file(activations_path)
    artifact_contract = _artifact_contract(activations_sha, manifest_path)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = _split_indices(rows_by_id, sample_ids)
    idx_train = splits["train"]
    idx_val = splits["val"]
    idx_test = splits["test"]
    X = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float32)
    y = _labels_for_task(rows_by_id, sample_ids, "interaction")
    fitted = _fit_readout(X, y, idx_train, idx_val, idx_test, _FOUNDATION_LABELS)
    Z, mean, std = _standardize_train(X, idx_train)
    train_result = _torch_train_sae(Z.astype(np.float32), idx_train, idx_val, args)
    Z_recon = np.asarray(train_result["reconstruction"], dtype=np.float64)
    acts = np.asarray(train_result["feature_acts"], dtype=np.float64)
    decoder_features = np.asarray(train_result["decoder_features"], dtype=np.float64)

    eval_idx = idx_val
    mse = float(np.mean((Z_recon[eval_idx] - Z[eval_idx]) ** 2))
    variance = float(np.var(Z[eval_idx]))
    explained = float(1.0 - mse / max(variance, 1e-12))
    active_mask = acts > float(args.active_threshold)
    active_per_row = active_mask.sum(axis=1)
    active_per_feature = active_mask.sum(axis=0)
    dead_rate = float(np.mean(active_per_feature <= 0))

    probe_dirs = _probe_z_directions(fitted)
    alignment = _feature_alignment(decoder_features, probe_dirs)
    top_summary = _top_alignment_summary(alignment, int(args.top_k_features))
    random_align = _random_alignment_control(
        int(args.n_features),
        int(X.shape[1]),
        probe_dirs,
        int(args.top_k_features),
        int(args.n_random),
        int(args.seed) + 1,
    )
    align_control = _summarize_vs_random(
        top_summary["top_k_mean_abs_alignment"],
        random_align["values"],
    )
    selected_features = [int(item["feature"]) for item in top_summary["top_features"][: int(args.top_k_features)]]
    specificity = _feature_specificity(acts, y, idx_val, selected_features)
    random_spec = _random_specificity_control(
        acts,
        y,
        idx_val,
        len(selected_features),
        int(args.n_random),
        int(args.seed) + 2,
    )
    spec_control = _summarize_vs_random(specificity["mean_top_minus_other"], random_spec["values"])

    recon_raw = Z_recon * std[None, :] + mean[None, :]
    pred_recon = _predict_with_probe(recon_raw[idx_test], fitted)
    recon_metrics = _metrics(y[idx_test], pred_recon, _FOUNDATION_LABELS)
    targeted_acts = acts.copy()
    targeted_acts[:, selected_features] = 0.0
    targeted_z = targeted_acts @ decoder_features + (Z_recon - acts @ decoder_features)
    targeted_raw = targeted_z * std[None, :] + mean[None, :]
    pred_targeted = _predict_with_probe(targeted_raw[idx_test], fitted)
    targeted_metrics = _metrics(y[idx_test], pred_targeted, _FOUNDATION_LABELS)
    targeted_drop = float(recon_metrics["acc"] - targeted_metrics["acc"])

    rng = np.random.default_rng(int(args.seed) + 3)
    random_drops: list[float] = []
    for _ in range(int(args.n_random)):
        random_features = rng.choice(int(args.n_features), size=len(selected_features), replace=False).astype(int).tolist()
        random_acts = acts.copy()
        random_acts[:, random_features] = 0.0
        random_z = random_acts @ decoder_features + (Z_recon - acts @ decoder_features)
        random_raw = random_z * std[None, :] + mean[None, :]
        pred_random = _predict_with_probe(random_raw[idx_test], fitted)
        random_acc = _metrics(y[idx_test], pred_random, _FOUNDATION_LABELS)["acc"]
        random_drops.append(float(recon_metrics["acc"] - random_acc))
    causal_control = _summarize_vs_random(targeted_drop, random_drops)

    report: dict[str, Any] = {
        "schema_version": "stage25_sae_feature_pilot.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": activations_sha,
        "activation_manifest_file": manifest_path.name,
        "artifact_contract": artifact_contract,
        "locked_readout": {"readout_key": _READOUT_KEY, "readout_name": "focus_token", "layer": _LAYER},
        "training_config": {
            "n_features": int(args.n_features),
            "max_steps": int(args.max_steps),
            "batch_size": int(args.batch_size),
            "learning_rate": float(args.learning_rate),
            "l1_coefficient": float(args.l1_coefficient),
            "seed": int(args.seed),
            "device": train_result["device"],
            "elapsed_seconds": train_result["elapsed_seconds"],
            "losses": train_result["losses"],
        },
        "probe": {
            "raw_train_acc": float(fitted["train"]["acc"]),
            "raw_val_acc": float(fitted["val"]["acc"]),
            "raw_test_acc": float(fitted["test"]["acc"]),
        },
        "reconstruction": {
            "heldout_split": "val",
            "heldout_mse": mse,
            "heldout_explained_variance": explained,
            "reconstructed_test_probe_acc": float(recon_metrics["acc"]),
        },
        "sparsity": {
            "active_threshold": float(args.active_threshold),
            "mean_active_features_per_row": float(np.mean(active_per_row)),
            "median_active_features_per_row": float(np.median(active_per_row)),
            "dead_feature_rate": dead_rate,
        },
        "cas_alignment": {
            **top_summary,
            "random_control": align_control,
        },
        "feature_specificity": {
            **specificity,
            "random_control": spec_control,
        },
        "causal_feature_drop": {
            "selected_features": selected_features,
            "reconstructed_baseline_acc": float(recon_metrics["acc"]),
            "targeted_removed_acc": float(targeted_metrics["acc"]),
            "targeted_drop": targeted_drop,
            "random_control": causal_control,
        },
        "checkpoint_file": Path(args.out_checkpoint).name,
        "checkpoint_sha256": _sha256_of_file(_resolve(args.out_checkpoint)),
        "boundary": (
            "Stage 25 trains an SAE over residual-stream readout activations and reports "
            "feature candidates. It does not identify exact causal neurons, complete circuits, "
            "raw CAS-symbol understanding, an internal CAS compiler, or free-form generation control."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage7_foundation_pilot_activations_manifest_20260517.json")
    parser.add_argument("--out-report", default="stage25_sae_feature_pilot_20260521.json")
    parser.add_argument("--out-md", default="STAGE25_SAE_FEATURE_PILOT_20260521.md")
    parser.add_argument("--out-checkpoint", default="stage25_sae_feature_pilot_20260521.pt")
    parser.add_argument("--n-features", type=int, default=6144)
    parser.add_argument("--max-steps", type=int, default=5000)
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--l1-coefficient", type=float, default=0.001)
    parser.add_argument("--active-threshold", type=float, default=1e-6)
    parser.add_argument("--top-k-features", type=int, default=28)
    parser.add_argument("--n-random", type=int, default=100)
    parser.add_argument("--seed", type=int, default=_SEED)
    parser.add_argument("--log-every", type=int, default=250)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
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
                "explained_variance": report["reconstruction"]["heldout_explained_variance"],
                "alignment_p": report["cas_alignment"]["random_control"]["empirical_p_random_ge_actual"],
                "specificity_p": report["feature_specificity"]["random_control"]["empirical_p_random_ge_actual"],
                "causal_p": report["causal_feature_drop"]["random_control"]["empirical_p_random_ge_actual"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
