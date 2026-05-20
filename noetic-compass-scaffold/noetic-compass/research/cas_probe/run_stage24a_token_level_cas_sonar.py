"""Stage 24A: token-level CAS sonar for Pythia-160M Foundation directions.

This is the first executable Stage 24A track. It projects locked Stage 7
Foundation probe directions through Pythia-160M output embeddings to produce
model-native vocabulary signatures. It is diagnostic attribution only: top
tokens are not generation guarantees and not neuron-level causal circuits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import string
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

from evaluate_stage7_factor_check import (
    _FOUNDATION_LABELS,
    _LAYER,
    _READOUT_KEY,
    _fit_readout,
    _labels_for_task,
    _load_jsonl,
    _split_indices,
)


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 24017
_REGISTERS = ("T", "A", "f", "E")


def _resolve(path: str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = _HERE / candidate
    return candidate


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _parse_foundation(label: str) -> tuple[int, str]:
    if not label.startswith("F") or len(label) < 3:
        raise ValueError(f"bad Foundation label {label!r}")
    return int(label[1]), label[2:]


def _unit_rows(matrix: np.ndarray) -> np.ndarray:
    arr = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    return arr / np.maximum(norms, 1e-12)


def _center_unit_columns(scores: np.ndarray) -> np.ndarray:
    arr = np.asarray(scores, dtype=np.float64)
    centered = arr - arr.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(centered, axis=1, keepdims=True)
    return centered / np.maximum(norms, 1e-12)


def _probe_raw_directions(scaler: Any, clf: Any) -> np.ndarray:
    sigma_safe = np.where(scaler.scale_ == 0, 1e-8, scaler.scale_)
    return np.asarray(clf.coef_ / sigma_safe[None, :], dtype=np.float64)


def _score_token_space(directions: np.ndarray, output_w: np.ndarray) -> np.ndarray:
    return np.asarray(output_w, dtype=np.float64) @ _unit_rows(directions).T


def _is_readable_token(token: str) -> bool:
    text = token.strip()
    if len(text) < 2:
        return False
    if "�" in text or "\ufffd" in text:
        return False
    printable = set(string.printable)
    if any(ch not in printable for ch in text):
        return False
    alpha_count = sum(ch.isalpha() for ch in text)
    if alpha_count < 2:
        return False
    return True


def _ranked_tokens(
    scores: np.ndarray,
    tokenizer: Any,
    top_k: int,
    *,
    reverse: bool,
    readable_only: bool,
) -> list[dict[str, Any]]:
    ordered = np.argsort(scores)
    if reverse:
        ordered = ordered[::-1]
    out: list[dict[str, Any]] = []
    for token_id in ordered:
        token = tokenizer.decode([int(token_id)])
        if readable_only and not _is_readable_token(token):
            continue
        out.append({"token_id": int(token_id), "token": token, "score": float(scores[int(token_id)])})
        if len(out) >= top_k:
            break
    return out


def _top_tokens(
    scores_by_token: np.ndarray,
    tokenizer: Any,
    top_k: int,
    *,
    readable_only: bool = False,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    scores_by_class = np.asarray(scores_by_token, dtype=np.float64).T
    for class_idx, label in enumerate(_FOUNDATION_LABELS):
        scores = scores_by_class[class_idx]
        out[label] = {
            "positive": _ranked_tokens(scores, tokenizer, top_k, reverse=True, readable_only=readable_only),
            "negative": _ranked_tokens(scores, tokenizer, top_k, reverse=False, readable_only=readable_only),
        }
    return out


def _top_token_readability(top_tokens: dict[str, Any]) -> dict[str, Any]:
    total = 0
    readable = 0
    unreadable_examples: list[dict[str, Any]] = []
    for label, block in top_tokens.items():
        for polarity in ("positive", "negative"):
            for item in block[polarity]:
                total += 1
                ok = _is_readable_token(str(item["token"]))
                readable += int(ok)
                if not ok and len(unreadable_examples) < 12:
                    unreadable_examples.append(
                        {"foundation": label, "polarity": polarity, "token": item["token"], "token_id": item["token_id"]}
                    )
    return {
        "total_top_tokens": int(total),
        "readable_top_tokens": int(readable),
        "readable_rate": float(readable / total) if total else 0.0,
        "unreadable_examples": unreadable_examples,
    }


def _partner_pairs(rows: list[dict[str, Any]]) -> list[tuple[int, int]]:
    label_to_idx = {label: idx for idx, label in enumerate(_FOUNDATION_LABELS)}
    pairs: set[tuple[int, int]] = set()
    for row in rows:
        current = str(row.get("foundation_label"))
        current_idx = label_to_idx.get(current)
        if current_idx is None:
            continue
        for partner in row.get("hard_contrast_foundations", []):
            partner_idx = label_to_idx.get(str(partner))
            if partner_idx is None or partner_idx == current_idx:
                continue
            pairs.add(tuple(sorted((current_idx, partner_idx))))
    return sorted(pairs)


def _class_pair_sets(rows: list[dict[str, Any]]) -> dict[str, list[tuple[int, int]]]:
    same_drive: list[tuple[int, int]] = []
    same_register: list[tuple[int, int]] = []
    different_drive_register: list[tuple[int, int]] = []
    labels = list(_FOUNDATION_LABELS)
    for i, j in combinations(range(len(labels)), 2):
        drive_i, register_i = _parse_foundation(labels[i])
        drive_j, register_j = _parse_foundation(labels[j])
        if drive_i == drive_j and register_i != register_j:
            same_drive.append((i, j))
        if register_i == register_j and drive_i != drive_j:
            same_register.append((i, j))
        if drive_i != drive_j and register_i != register_j:
            different_drive_register.append((i, j))
    return {
        "same_drive": same_drive,
        "same_register": same_register,
        "different_drive_register": different_drive_register,
        "hard_partner": _partner_pairs(rows),
    }


def _mean_pair_similarity(normalized_scores_by_class: np.ndarray, pairs: list[tuple[int, int]]) -> float:
    if not pairs:
        return 0.0
    values = [
        float(np.dot(normalized_scores_by_class[i], normalized_scores_by_class[j]))
        for i, j in pairs
    ]
    return float(np.mean(values))


def _similarity_metrics(scores_by_token: np.ndarray, pair_sets: dict[str, list[tuple[int, int]]]) -> dict[str, float]:
    normalized = _center_unit_columns(scores_by_token.T)
    same_drive = _mean_pair_similarity(normalized, pair_sets["same_drive"])
    same_register = _mean_pair_similarity(normalized, pair_sets["same_register"])
    hard_partner = _mean_pair_similarity(normalized, pair_sets["hard_partner"])
    different = _mean_pair_similarity(normalized, pair_sets["different_drive_register"])
    return {
        "same_drive_mean_cosine": same_drive,
        "same_register_mean_cosine": same_register,
        "hard_partner_mean_cosine": hard_partner,
        "different_drive_register_mean_cosine": different,
        "same_drive_minus_hard_partner": float(same_drive - hard_partner),
        "same_register_minus_hard_partner": float(same_register - hard_partner),
        "same_drive_minus_different": float(same_drive - different),
        "same_register_minus_different": float(same_register - different),
    }


def _random_direction_metrics(
    output_w: np.ndarray,
    pair_sets: dict[str, list[tuple[int, int]]],
    *,
    n_random: int,
    seed: int,
) -> list[dict[str, float]]:
    rng = np.random.default_rng(seed)
    hidden_dim = int(output_w.shape[1])
    out: list[dict[str, float]] = []
    for _ in range(n_random):
        directions = rng.standard_normal((len(_FOUNDATION_LABELS), hidden_dim))
        scores = _score_token_space(directions, output_w)
        out.append(_similarity_metrics(scores, pair_sets))
    return out


def _summarize_random(actual: float, random_values: list[float]) -> dict[str, Any]:
    values = np.asarray(random_values, dtype=np.float64)
    if values.size == 0:
        return {
            "actual": float(actual),
            "random_mean": 0.0,
            "random_p95": 0.0,
            "empirical_p_random_ge_actual": 1.0,
            "n_random": 0,
        }
    return {
        "actual": float(actual),
        "random_mean": float(values.mean()),
        "random_std": float(values.std(ddof=1)) if values.size > 1 else 0.0,
        "random_p05": float(np.quantile(values, 0.05)),
        "random_p50": float(np.quantile(values, 0.50)),
        "random_p95": float(np.quantile(values, 0.95)),
        "empirical_p_random_ge_actual": float((1 + np.sum(values >= actual)) / (values.size + 1)),
        "actual_percentile_vs_random": float(np.mean(values <= actual)),
        "n_random": int(values.size),
    }


def _load_output_embeddings(allow_download: bool) -> tuple[np.ndarray, Any, dict[str, Any]]:
    import torch
    import transformers as transformers_pkg
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=not allow_download, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(_MODEL_NAME, local_files_only=not allow_download)
    output = model.get_output_embeddings()
    if output is None:
        raise RuntimeError(f"{_MODEL_NAME} did not expose output embeddings")
    output_w = output.weight.detach().to(dtype=torch.float32, device="cpu").numpy()
    meta = {
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "hidden_dim": int(output_w.shape[1]),
        "vocab_size": int(output_w.shape[0]),
        "transformers": getattr(transformers_pkg, "__version__", "unknown"),
        "torch": getattr(torch, "__version__", "unknown"),
    }
    return output_w, tokenizer, meta


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


def _status_from_controls(
    controls: dict[str, Any],
    readability: dict[str, Any],
    artifact_contract: dict[str, Any] | None = None,
) -> str:
    if artifact_contract is not None and not artifact_contract.get("formal_gate_valid", False):
        return "STAGE24A_SONAR_TOKEN_SIGNATURES_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"
    if readability["readable_rate"] < 0.50:
        return "STAGE24A_SONAR_TOKEN_SIGNATURES_NULL_ARTIFACT_DOMINATED"
    drive = controls["same_drive_minus_hard_partner"]["empirical_p_random_ge_actual"]
    register = controls["same_register_minus_hard_partner"]["empirical_p_random_ge_actual"]
    if drive < 0.05 and register < 0.05:
        return "STAGE24A_SONAR_TOKEN_SIGNATURES_PASS_BOUNDED"
    if drive > 0.50 and register > 0.50:
        return "STAGE24A_SONAR_TOKEN_SIGNATURES_NULL"
    return "STAGE24A_SONAR_TOKEN_SIGNATURES_GREY"


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    lines = [
        "# Stage 24A Token-Level CAS Sonar",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Plain English",
        "",
        report["plain_english_read"],
        "",
        "## Probe",
        "",
        f"- Model: `{report['model']['model_name']}`",
        f"- Locked readout: `{report['locked_readout']['readout_key']}` layer `{report['locked_readout']['layer']}`",
        f"- Probe test accuracy: `{report['probe']['test_acc']:.4f}`",
        f"- Artifact contract: `{report['artifact_contract']['status']}`",
        "",
        "## Pair-Similarity Controls",
        "",
        "| Metric | Actual | Random mean | Random p95 | p(random >= actual) |",
        "|---|---:|---:|---:|---:|",
    ]
    for metric, row in report["random_control_summary"].items():
        lines.append(
            f"| `{metric}` | {row['actual']:.6f} | {row['random_mean']:.6f} | "
            f"{row['random_p95']:.6f} | {row['empirical_p_random_ge_actual']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Top-Token Readability",
            "",
            f"- Readable rate: `{report['top_token_readability']['readable_rate']:.4f}`",
            f"- Readable tokens: `{report['top_token_readability']['readable_top_tokens']} / {report['top_token_readability']['total_top_tokens']}`",
            "",
            "## Example Top Tokens",
            "",
        ]
    )
    for label in list(_FOUNDATION_LABELS)[:7]:
        tokens = ", ".join(
            item["token"].replace("\n", "\\n")
            for item in report["readable_top_tokens_by_foundation"][label]["positive"][:5]
        )
        lines.append(f"- `{label}`: {tokens}")
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


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    activation_manifest_path = _resolve(args.activation_manifest)
    stage7_report_path = _resolve(args.stage7_report)

    if not activations_path.exists():
        raise FileNotFoundError(
            f"Stage 24A requires locked Stage 7 activations: {activations_path}. "
            "Recapture or pull the artifact before running sonar."
        )

    activations_sha256 = _sha256_of_file(activations_path)
    artifact_contract = _artifact_contract(activations_sha256, activation_manifest_path)
    rows = _load_jsonl(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = _split_indices(rows_by_id, sample_ids)
    X = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    y = _labels_for_task(rows_by_id, sample_ids, "interaction")
    fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _FOUNDATION_LABELS)
    directions = _probe_raw_directions(fitted["scaler"], fitted["clf"])

    output_w, tokenizer, model_meta = _load_output_embeddings(bool(args.allow_download))
    if int(output_w.shape[1]) != int(directions.shape[1]):
        raise ValueError(f"direction dim {directions.shape[1]} != output embedding dim {output_w.shape[1]}")
    scores_by_token = _score_token_space(directions, output_w)
    pair_sets = _class_pair_sets(rows)
    actual_metrics = _similarity_metrics(scores_by_token, pair_sets)
    random_metrics = _random_direction_metrics(
        output_w,
        pair_sets,
        n_random=int(args.n_random),
        seed=int(args.seed),
    )
    random_control_summary = {
        key: _summarize_random(actual_metrics[key], [row[key] for row in random_metrics])
        for key in (
            "same_drive_minus_hard_partner",
            "same_register_minus_hard_partner",
            "same_drive_minus_different",
            "same_register_minus_different",
        )
    }
    raw_top_tokens = _top_tokens(scores_by_token, tokenizer, int(args.top_k))
    readability = _top_token_readability(raw_top_tokens)
    status = _status_from_controls(random_control_summary, readability, artifact_contract)
    with stage7_report_path.open(encoding="utf-8") as fh:
        stage7_report = json.load(fh)

    report = {
        "schema_version": "stage24a_token_level_cas_sonar.v1",
        "status": status,
        "model": model_meta,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": activations_sha256,
        "activation_manifest_file": activation_manifest_path.name,
        "artifact_contract": artifact_contract,
        "stage7_report_file": stage7_report_path.name,
        "stage7_report_sha256": _sha256_of_file(stage7_report_path),
        "locked_readout": {"readout_key": _READOUT_KEY, "readout_name": "focus_token", "layer": _LAYER},
        "probe": {
            "train_acc": float(fitted["train"]["acc"]),
            "val_acc": float(fitted["val"]["acc"]),
            "test_acc": float(fitted["test"]["acc"]),
            "stage7_headline_acc": float(stage7_report["headline"]["test"]["acc"]),
        },
        "pair_set_counts": {key: int(len(value)) for key, value in pair_sets.items()},
        "pair_similarity_metrics": actual_metrics,
        "random_control_summary": random_control_summary,
        "top_token_readability": readability,
        "top_tokens_by_foundation": raw_top_tokens,
        "readable_top_tokens_by_foundation": _top_tokens(
            scores_by_token,
            tokenizer,
            int(args.top_k),
            readable_only=True,
        ),
        "plain_english_read": (
            "This report measures whether the Stage 7 Foundation probe directions have "
            "class-specific token signatures in Pythia-160M's output embedding space. "
            "It is token-level diagnostic attribution, not open-ended generation control."
        ),
        "boundary": (
            "Stage 24A sonar projects trained readout directions through static output embeddings. "
            "It does not prove exact neurons, SAE-disentangled features, raw CAS-symbol understanding, "
            "or that the model would generate the listed tokens in free-form decoding."
        ),
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage7_foundation_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage7_foundation_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage7_foundation_pilot_activations_manifest_20260517.json")
    parser.add_argument("--stage7-report", default="stage7_foundation_pilot_probe_report_20260517.json")
    parser.add_argument("--out-report", default="stage24a_token_level_cas_sonar_20260520.json")
    parser.add_argument("--out-md", default="STAGE24A_TOKEN_LEVEL_CAS_SONAR_20260520.md")
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--n-random", type=int, default=100)
    parser.add_argument("--seed", type=int, default=_SEED)
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
                "probe_test_acc": report["probe"]["test_acc"],
                "random_controls": report["random_control_summary"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
