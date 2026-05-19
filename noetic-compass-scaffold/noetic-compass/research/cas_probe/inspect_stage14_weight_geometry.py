"""Inspect Stage 14 CAS probe subspace against Pythia-2.8B weight geometry."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import (
    _FOUNDATION_LABELS,
    _fit_readout,
    _labels_for_task,
    _load_jsonl,
    _projection_basis_from_probe,
    _split_indices,
)
from evaluate_stage6_role_bound_full import _sha256_of_file


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-2.8b"
_SEED = 14019


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _load_weights(allow_download: bool) -> tuple[np.ndarray, np.ndarray, Any, dict[str, Any]]:
    import torch
    import transformers as transformers_pkg
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=not allow_download, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=not allow_download)
    output = model.get_output_embeddings()
    input_emb = model.get_input_embeddings()
    if output is None or input_emb is None:
        raise RuntimeError("model did not expose both input and output embeddings")
    output_w = output.weight.detach().to(dtype=torch.float32, device="cpu").numpy()
    input_w = input_emb.weight.detach().to(dtype=torch.float32, device="cpu").numpy()
    meta = {
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "hidden_dim": int(output_w.shape[1]),
        "vocab_size": int(output_w.shape[0]),
        "transformers": getattr(transformers_pkg, "__version__", "unknown"),
        "torch": getattr(torch, "__version__", "unknown"),
    }
    return output_w, input_w, tokenizer, meta


def _random_basis(rng: np.random.Generator, rank: int, hidden_dim: int) -> np.ndarray:
    raw = rng.standard_normal((hidden_dim, rank))
    q, _ = np.linalg.qr(raw)
    return q[:, :rank].T


def _summarize(actual: float, random_values: np.ndarray) -> dict[str, Any]:
    values = np.asarray(random_values, dtype=np.float64)
    return {
        "actual": float(actual),
        "random_mean": float(values.mean()),
        "random_std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
        "random_p05": float(np.quantile(values, 0.05)),
        "random_p50": float(np.quantile(values, 0.50)),
        "random_p95": float(np.quantile(values, 0.95)),
        "actual_over_random_mean": float(actual / values.mean()) if values.mean() else math.inf,
        "empirical_p_random_ge_actual": float((1 + np.sum(values >= actual)) / (len(values) + 1)),
        "actual_percentile_vs_random": float(np.mean(values <= actual)),
        "n_random": int(len(values)),
    }


def _energy_fraction(basis_rows: np.ndarray, gram: np.ndarray) -> float:
    return float(np.trace(basis_rows @ gram @ basis_rows.T) / np.trace(gram))


def _logit_lens_fraction(X: np.ndarray, basis_rows: np.ndarray, gram: np.ndarray) -> float:
    projection = basis_rows.T @ basis_rows
    Xp = X @ projection
    numerator = np.einsum("ij,jk,ik->i", Xp, gram, Xp, optimize=True)
    denominator = np.einsum("ij,jk,ik->i", X, gram, X, optimize=True)
    valid = denominator > 1e-12
    if not np.any(valid):
        return 0.0
    return float(np.mean(numerator[valid] / denominator[valid]))


def _top_tokens_for_probe_rows(coef_raw: np.ndarray, output_w: np.ndarray, tokenizer: Any, top_k: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for i, label in enumerate(_FOUNDATION_LABELS):
        direction = coef_raw[i]
        norm = float(np.linalg.norm(direction))
        if norm <= 1e-12:
            scores = np.zeros((output_w.shape[0],), dtype=np.float64)
        else:
            scores = output_w @ (direction / norm)
        top_pos = np.argsort(scores)[-top_k:][::-1]
        top_neg = np.argsort(scores)[:top_k]
        out[label] = {
            "positive": [
                {"token_id": int(idx), "token": tokenizer.decode([int(idx)]), "score": float(scores[int(idx)])}
                for idx in top_pos
            ],
            "negative": [
                {"token_id": int(idx), "token": tokenizer.decode([int(idx)]), "score": float(scores[int(idx)])}
                for idx in top_neg
            ],
        }
    return out


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 14 Weight Geometry / Alignment Inspection",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Plain English",
        "",
        "Weights do not fire. This report inspects whether the trained CAS Foundation probe subspace is geometrically aligned with Pythia-2.8B's static input/output token-weight matrices.",
        "",
        "## Probe",
        "",
        f"- Selected layer: `{report['selected_layer_position']}`",
        f"- Probe rank: `{report['probe']['rank']}`",
        f"- Test accuracy: `{report['probe']['test_acc']:.4f}`",
        "",
        "## Alignment",
        "",
        "| Check | Actual | Random mean | Random p95 | p(random >= actual) |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in ("output_weight_energy_fraction", "input_weight_energy_fraction", "output_logit_lens_energy_fraction"):
        row = report["alignment"][name]
        lines.append(
            f"| `{name}` | {row['actual']:.6f} | {row['random_mean']:.6f} | "
            f"{row['random_p95']:.6f} | {row['empirical_p_random_ge_actual']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            report["interpretation"],
            "",
            "## Boundary",
            "",
            "This is weight-geometry evidence only. It does not prove exact causal neurons, hidden-state steering, or raw-symbol understanding.",
            "",
        ]
    )
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage14_pythia28b_activations_20260518.npz")
    parser.add_argument("--selected-layer", type=int, default=14)
    parser.add_argument("--n-random", type=int, default=100)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--out-report", default="stage14_weight_geometry_alignment_20260519.json")
    parser.add_argument("--out-md", default="STAGE14_WEIGHT_GEOMETRY_ALIGNMENT_20260519.md")
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args(argv)

    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    out_report = _resolve(args.out_report)
    out_md = _resolve(args.out_md)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    split = _split_indices(rows_by_id, sample_ids)
    layer_positions = [int(x) for x in data["layer_positions"].tolist()]
    if int(args.selected_layer) not in layer_positions:
        raise SystemExit(f"selected layer {args.selected_layer} not in activation layer positions {layer_positions}")
    layer_index = layer_positions.index(int(args.selected_layer))
    X = np.asarray(data["X_focus"][:, layer_index, :], dtype=np.float64)
    y = _labels_for_task(rows_by_id, sample_ids, "interaction")
    fitted = _fit_readout(X, y, split["train"], split["val"], split["test"], _FOUNDATION_LABELS)
    basis = _projection_basis_from_probe(fitted["scaler"], fitted["clf"])
    basis_rows = np.asarray(basis["basis_rows"], dtype=np.float64)
    sigma_safe = np.where(fitted["scaler"].scale_ == 0, 1e-8, fitted["scaler"].scale_)
    coef_raw = fitted["clf"].coef_ / sigma_safe[None, :]

    output_w, input_w, tokenizer, model_meta = _load_weights(bool(args.allow_download))
    output_gram = output_w.T @ output_w
    input_gram = input_w.T @ input_w
    rng = np.random.default_rng(_SEED)
    random_bases = [_random_basis(rng, int(basis["rank"]), int(output_w.shape[1])) for _ in range(int(args.n_random))]

    output_actual = _energy_fraction(basis_rows, output_gram)
    input_actual = _energy_fraction(basis_rows, input_gram)
    logit_actual = _logit_lens_fraction(X[split["test"]], basis_rows, output_gram)
    output_random = np.array([_energy_fraction(b, output_gram) for b in random_bases])
    input_random = np.array([_energy_fraction(b, input_gram) for b in random_bases])
    logit_random = np.array([_logit_lens_fraction(X[split["test"]], b, output_gram) for b in random_bases])

    output_summary = _summarize(output_actual, output_random)
    logit_summary = _summarize(logit_actual, logit_random)
    if (
        output_summary["empirical_p_random_ge_actual"] < 0.05
        or logit_summary["empirical_p_random_ge_actual"] < 0.05
    ):
        status = "CAS_SUBSPACE_WEIGHT_ALIGNMENT_ABOVE_RANDOM_ON_SOME_CHECK"
        interpretation = (
            "At least one weight-geometry check is above random same-rank controls. This supports a bounded "
            "alignment-inspection claim, not generation control."
        )
    else:
        status = "CAS_SUBSPACE_WEIGHT_ALIGNMENT_NEAR_RANDOM"
        interpretation = (
            "The CAS readout subspace is not unusually aligned with static token-weight geometry under these "
            "checks. This is compatible with the eta-to-epsilon result because that mechanism works through "
            "readable prefix attention, not raw hidden-state steering."
        )

    report = {
        "schema_version": "stage14_weight_geometry_alignment.v1",
        "status": status,
        "model": model_meta,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": _sha256_of_file(activations_path),
        "selected_layer_position": int(args.selected_layer),
        "selected_layer_array_index": int(layer_index),
        "probe": {
            "rank": int(basis["rank"]),
            "train_acc": float(fitted["train"]["acc"]),
            "val_acc": float(fitted["val"]["acc"]),
            "test_acc": float(fitted["test"]["acc"]),
            "singular_values": basis["singular_values"],
        },
        "alignment": {
            "output_weight_energy_fraction": output_summary,
            "input_weight_energy_fraction": _summarize(input_actual, input_random),
            "output_logit_lens_energy_fraction": logit_summary,
        },
        "top_tokens_by_probe_direction": _top_tokens_for_probe_rows(coef_raw, output_w, tokenizer, int(args.top_k)),
        "interpretation": interpretation,
        "boundary": (
            "Static weight geometry inspection only. Weights do not fire; activations change per input."
        ),
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_md(report, out_md)
    print(json.dumps({"status": status, "output_alignment": output_summary, "logit_alignment": logit_summary}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
