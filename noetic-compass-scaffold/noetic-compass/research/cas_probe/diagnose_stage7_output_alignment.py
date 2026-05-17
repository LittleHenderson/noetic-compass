"""Stage 7 output-alignment diagnostics for Foundation/Drive subspaces.

This is a free diagnostic before more generation hooks. Stage 7.0-7.2
show that Pythia-160M hidden states contain a strong 28-Foundation/Drive
readout, but Stage 7.3 did not show generated-language control. This
script asks whether the trained readout subspaces are aligned with the
language model's output head at all.

It reports:

* principal-angle overlap with the full unembedding row space,
* unembedding-energy share for each task subspace vs random same-rank
  subspaces,
* top-unembedding-singular-vector overlap,
* logit-lens energy share on locked test hidden states.

Important caveat: for a full-rank unembedding matrix, "principal angles
to the full row space" is degenerate because the row space is the whole
hidden space. The useful diagnostics are therefore the energy/top-mode
and logit-lens comparisons against random controls.
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
    _LAYER,
    _READOUT_KEY,
    _TASKS,
    _fit_readout,
    _labels_for_task,
    _load_jsonl,
    _projection_basis_from_probe,
    _split_indices,
)


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 71941


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


def _load_unembedding(allow_download: bool) -> tuple[np.ndarray, dict[str, Any]]:
    import torch
    import transformers as transformers_pkg
    from transformers import AutoModelForCausalLM

    model = AutoModelForCausalLM.from_pretrained(
        _MODEL_NAME,
        local_files_only=not allow_download,
    )
    emb = model.get_output_embeddings()
    if emb is None:
        raise RuntimeError(f"{_MODEL_NAME} did not expose output embeddings")
    weight = emb.weight.detach().to(dtype=torch.float32, device="cpu").numpy()
    meta = {
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "transformers": getattr(transformers_pkg, "__version__", "unknown"),
        "torch": getattr(torch, "__version__", "unknown"),
        "vocab_size": int(weight.shape[0]),
        "hidden_dim": int(weight.shape[1]),
    }
    return weight, meta


def _orthonormal_random_basis(rng: np.random.Generator, rank: int, hidden_dim: int) -> np.ndarray:
    raw = rng.standard_normal((hidden_dim, rank))
    q, _ = np.linalg.qr(raw)
    return q[:, :rank].T


def _summarize_random(values: np.ndarray, actual: float, larger_is_more_aligned: bool = True) -> dict[str, Any]:
    values = np.asarray(values, dtype=np.float64)
    if larger_is_more_aligned:
        empirical_p = (1.0 + float(np.sum(values >= actual))) / (len(values) + 1.0)
        percentile = float(np.mean(values <= actual))
    else:
        empirical_p = (1.0 + float(np.sum(values <= actual))) / (len(values) + 1.0)
        percentile = float(np.mean(values >= actual))
    std = float(values.std(ddof=1)) if len(values) > 1 else 0.0
    return {
        "actual": float(actual),
        "random_mean": float(values.mean()),
        "random_std": std,
        "random_p05": float(np.quantile(values, 0.05)),
        "random_p50": float(np.quantile(values, 0.50)),
        "random_p95": float(np.quantile(values, 0.95)),
        "actual_over_random_mean": float(actual / values.mean()) if values.mean() != 0 else math.inf,
        "empirical_p_random_ge_actual": empirical_p if larger_is_more_aligned else None,
        "empirical_p_random_le_actual": empirical_p if not larger_is_more_aligned else None,
        "actual_percentile_vs_random": percentile,
        "n_random": int(len(values)),
    }


def _energy_fraction(basis_rows: np.ndarray, gram: np.ndarray, total_energy: float) -> float:
    # basis_rows has shape rank x hidden_dim and is orthonormal by construction.
    return float(np.trace(basis_rows @ gram @ basis_rows.T) / total_energy)


def _top_mode_overlap(basis_rows: np.ndarray, eigvecs_desc: np.ndarray, k: int) -> float:
    top = eigvecs_desc[:, :k]
    # Fraction of the task subspace contained in the top-k unembedding directions.
    return float(np.trace(basis_rows @ top @ top.T @ basis_rows.T) / basis_rows.shape[0])


def _mean_logit_lens_energy_fraction(X: np.ndarray, basis_rows: np.ndarray, gram: np.ndarray) -> float:
    projection = basis_rows.T @ basis_rows
    Xp = X @ projection
    numerator = np.einsum("ij,jk,ik->i", Xp, gram, Xp, optimize=True)
    denominator = np.einsum("ij,jk,ik->i", X, gram, X, optimize=True)
    valid = denominator > 1e-12
    if not np.any(valid):
        return 0.0
    ratios = np.zeros_like(denominator, dtype=np.float64)
    ratios[valid] = numerator[valid] / denominator[valid]
    return float(np.mean(ratios[valid]))


def _fit_task_basis(
    task: str,
    rows_by_id: dict[str, dict[str, Any]],
    sample_ids: list[str],
    X_layer: np.ndarray,
    idx_train: np.ndarray,
    idx_val: np.ndarray,
    idx_test: np.ndarray,
) -> dict[str, Any]:
    labels = _TASKS[task]
    y = _labels_for_task(rows_by_id, sample_ids, task)
    fitted = _fit_readout(X_layer, y, idx_train, idx_val, idx_test, labels)
    basis = _projection_basis_from_probe(fitted["scaler"], fitted["clf"])
    return {
        "labels": labels,
        "y": y,
        "basis_rows": np.asarray(basis["basis_rows"], dtype=np.float64),
        "rank": int(basis["rank"]),
        "singular_values": basis["singular_values"],
        "train_acc": float(fitted["train"]["acc"]),
        "val_acc": float(fitted["val"]["acc"]),
        "test_acc": float(fitted["test"]["acc"]),
    }


def _task_diagnostics(
    task: str,
    basis_rows: np.ndarray,
    X_test: np.ndarray,
    gram: np.ndarray,
    eigvecs_desc: np.ndarray,
    total_energy: float,
    n_random: int,
    rng: np.random.Generator,
) -> dict[str, Any]:
    hidden_dim = int(gram.shape[0])
    rank = int(basis_rows.shape[0])
    random_bases = [_orthonormal_random_basis(rng, rank, hidden_dim) for _ in range(n_random)]

    actual_energy = _energy_fraction(basis_rows, gram, total_energy)
    random_energy = np.array([_energy_fraction(b, gram, total_energy) for b in random_bases])

    actual_logit_lens = _mean_logit_lens_energy_fraction(X_test, basis_rows, gram)
    random_logit_lens = np.array([
        _mean_logit_lens_energy_fraction(X_test, b, gram) for b in random_bases
    ])

    top_modes: dict[str, Any] = {}
    for k in (16, 32, 64, 128, 256):
        if k > hidden_dim:
            continue
        actual = _top_mode_overlap(basis_rows, eigvecs_desc, k)
        random_values = np.array([_top_mode_overlap(b, eigvecs_desc, k) for b in random_bases])
        top_modes[f"top_{k}"] = _summarize_random(random_values, actual)

    status = "OUTPUT_ALIGNMENT_NEAR_RANDOM"
    if actual_logit_lens > float(np.quantile(random_logit_lens, 0.95)) and actual_energy > float(np.quantile(random_energy, 0.95)):
        status = "OUTPUT_ALIGNMENT_ABOVE_RANDOM"
    elif actual_logit_lens < float(np.quantile(random_logit_lens, 0.05)) and actual_energy < float(np.quantile(random_energy, 0.05)):
        status = "OUTPUT_ALIGNMENT_BELOW_RANDOM"

    return {
        "task": task,
        "rank": rank,
        "status": status,
        "unembedding_energy_fraction": _summarize_random(random_energy, actual_energy),
        "logit_lens_energy_fraction_on_locked_test": _summarize_random(random_logit_lens, actual_logit_lens),
        "top_unembedding_mode_overlap": top_modes,
    }


def _write_markdown(report: dict[str, Any], out_path: Path) -> None:
    lines: list[str] = []
    lines.append("# Stage 7 Output-Alignment Diagnostics")
    lines.append("")
    lines.append(f"**Status:** `{report['status']}`")
    lines.append("")
    lines.append("## Read")
    lines.append("")
    lines.append(report["plain_english_read"])
    lines.append("")
    lines.append("## Principal-Angle Check")
    lines.append("")
    pa = report["principal_angle_full_unembedding_rowspace"]
    lines.append(
        f"The unembedding numerical rank is `{pa['rank']}` of hidden dim `{pa['hidden_dim']}`. "
        f"Degenerate: `{pa['degenerate_full_rowspace']}`."
    )
    lines.append("")
    lines.append(pa["interpretation"])
    lines.append("")
    lines.append("## Task Diagnostics")
    lines.append("")
    lines.append("| Task | Rank | Status | Unembedding Energy | Random Mean | Logit-Lens Energy | Random Mean |")
    lines.append("|---|---:|---|---:|---:|---:|---:|")
    for task, block in report["tasks"].items():
        energy = block["alignment"]["unembedding_energy_fraction"]
        ll = block["alignment"]["logit_lens_energy_fraction_on_locked_test"]
        lines.append(
            f"| {task} | {block['rank']} | `{block['alignment']['status']}` | "
            f"{energy['actual']:.6f} | {energy['random_mean']:.6f} | "
            f"{ll['actual']:.6f} | {ll['random_mean']:.6f} |"
        )
    lines.append("")
    lines.append("## Implication")
    lines.append("")
    lines.append(report["implication"])
    lines.append("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--out-report", default="stage7_output_alignment_diagnostics_20260517.json")
    parser.add_argument("--out-md", default="STAGE7_OUTPUT_ALIGNMENT_DIAGNOSTICS_20260517.md")
    parser.add_argument("--n-random", type=int, default=200)
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--tasks", nargs="+", choices=tuple(_TASKS), default=["drive", "interaction"])
    args = parser.parse_args(argv)

    started = time.perf_counter()
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)

    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    split = _split_indices(rows_by_id, sample_ids)
    X_layer = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    X_test = X_layer[split["test"]]

    unembedding, model_meta = _load_unembedding(args.allow_download)
    unembedding = np.asarray(unembedding, dtype=np.float64)
    if unembedding.shape[1] != X_layer.shape[1]:
        raise ValueError(
            f"unembedding hidden dim {unembedding.shape[1]} != activation dim {X_layer.shape[1]}"
        )
    gram = unembedding.T @ unembedding
    total_energy = float(np.trace(gram))
    eigvals, eigvecs = np.linalg.eigh(gram)
    order = np.argsort(eigvals)[::-1]
    eigvals_desc = eigvals[order]
    eigvecs_desc = eigvecs[:, order]
    rank_tol = float(max(eigvals_desc[0] * 1e-8, 1e-12))
    unembedding_rank = int(np.sum(eigvals_desc > rank_tol))
    hidden_dim = int(unembedding.shape[1])
    degenerate = unembedding_rank >= hidden_dim

    rng = np.random.default_rng(_SEED)
    task_reports: dict[str, Any] = {}
    for task in args.tasks:
        task_basis = _fit_task_basis(
            task,
            rows_by_id,
            sample_ids,
            X_layer,
            split["train"],
            split["val"],
            split["test"],
        )
        alignment = _task_diagnostics(
            task,
            task_basis["basis_rows"],
            X_test,
            gram,
            eigvecs_desc,
            total_energy,
            args.n_random,
            rng,
        )
        task_reports[task] = {
            "rank": task_basis["rank"],
            "readout_accuracy": {
                "train": task_basis["train_acc"],
                "val": task_basis["val_acc"],
                "test": task_basis["test_acc"],
            },
            "singular_values": task_basis["singular_values"],
            "alignment": alignment,
        }

    any_above = any(block["alignment"]["status"] == "OUTPUT_ALIGNMENT_ABOVE_RANDOM" for block in task_reports.values())
    all_near_or_below = all(
        block["alignment"]["status"] in {"OUTPUT_ALIGNMENT_NEAR_RANDOM", "OUTPUT_ALIGNMENT_BELOW_RANDOM"}
        for block in task_reports.values()
    )
    if any_above:
        status = "SOME_STAGE7_SUBSPACE_OUTPUT_ALIGNMENT_ABOVE_RANDOM"
        implication = (
            "At least one Stage 7 readout subspace has output-head alignment above random same-rank controls. "
            "This does not prove generation control, but it keeps a bounded logit-margin Stage 7.4 test live."
        )
    elif all_near_or_below:
        status = "STAGE7_SUBSPACES_NOT_OUTPUT_ALIGNED_ABOVE_RANDOM"
        implication = (
            "The tested Stage 7 readout subspaces are not specially aligned with the output head by these diagnostics. "
            "That explains why subtraction at layer 6 failed to steer generation and argues against more layer-6 "
            "free-generation hooks."
        )
    else:
        status = "STAGE7_OUTPUT_ALIGNMENT_MIXED"
        implication = (
            "Output-head alignment is mixed. Treat this as diagnostic evidence only and keep any next generation test "
            "pre-registered."
        )

    principal_interpretation = (
        "Because Pythia's unembedding is numerically full-rank over the hidden dimension, principal angles to the full "
        "unembedding row space are all zero for any hidden-state subspace. The raw principal-angle test proposed in the "
        "roundtable is therefore degenerate for this model; the useful version is rank-matched energy/top-mode/logit-lens "
        "alignment against random controls."
        if degenerate
        else "The unembedding row space is not full hidden rank, so principal angles to the row space can be interpreted directly."
    )

    report = {
        "schema_version": "stage7_output_alignment_diagnostics.v1",
        "experiment": "Stage 7 output-alignment diagnostics for Foundation/Drive probe subspaces",
        "status": status,
        "plain_english_read": (
            "This diagnostic checks whether the CAS readout subspaces point toward Pythia's output head. "
            "It does not run generation and does not prove steering. It tells us whether the already-proven readout "
            "directions look like plausible output-writing directions or mostly like observer/readout directions."
        ),
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "readout": _READOUT_KEY,
        "layer": _LAYER,
        "split": {k: int(len(v)) for k, v in split.items()},
        "n_random": int(args.n_random),
        "seed": _SEED,
        "model": model_meta,
        "unembedding": {
            "shape": [int(x) for x in unembedding.shape],
            "total_frobenius_energy": total_energy,
            "top_eigenvalues": [float(x) for x in eigvals_desc[:20].tolist()],
            "rank_tol": rank_tol,
        },
        "principal_angle_full_unembedding_rowspace": {
            "rank": unembedding_rank,
            "hidden_dim": hidden_dim,
            "degenerate_full_rowspace": degenerate,
            "interpretation": principal_interpretation,
        },
        "tasks": task_reports,
        "implication": implication,
        "elapsed_seconds": time.perf_counter() - started,
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(report, out_md)

    print(f"status: {status}")
    for task, block in task_reports.items():
        energy = block["alignment"]["unembedding_energy_fraction"]
        ll = block["alignment"]["logit_lens_energy_fraction_on_locked_test"]
        print(
            f"{task}: rank={block['rank']} status={block['alignment']['status']} "
            f"energy={energy['actual']:.6f} random={energy['random_mean']:.6f} "
            f"logit_lens={ll['actual']:.6f} random={ll['random_mean']:.6f}"
        )
    print(f"report written: {out_report}")
    print(f"markdown written: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
