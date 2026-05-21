"""Stage 28A Noetic involution sonar.

This diagnostic collapses the Stage 9 original-TKS 40 Element fixture into a
10-way Noetic readout and tests whether formal involution pairs (^2/^3,
^5/^6, ^8/^9) are opposed in Pythia-160M output-embedding token space.

Boundary: this is static token-signature attribution over Noetic classes. It
does not prove exact neurons, complete circuits, Noetic clusters, hard-partner
40-Element resolution, raw CAS-symbol understanding, or free-form generation
control.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

import evaluate_stage6_role_bound_full as stage6
from evaluate_stage7_factor_check import _fit_readout
from evaluate_stage9_elements_pilot import _load_rows
from run_stage24a_token_level_cas_sonar import (
    _center_unit_columns,
    _is_readable_token,
    _probe_raw_directions,
    _ranked_tokens,
    _score_token_space,
    _summarize_random,
)


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
_SEED = 28010
_READOUT_KEY = "X_focus"
_READOUT_NAME = "focus_token"
_LAYER = 5
_NOETIC_LABELS = ("^1", "^2", "^3", "^4", "^5", "^6", "^7", "^8", "^9", "^0")
_NOETIC_NAMES = (
    "Mind",
    "Positive",
    "Negative",
    "Vibration",
    "Female",
    "Male",
    "Rhythm",
    "Above/Cause",
    "Below/Effect",
    "Idea",
)
_INVOLUTION_PAIRS = ((1, 2), (4, 5), (7, 8))


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
    contract_source = "output_sha256"
    if expected is None and isinstance(manifest.get("replacement_artifact_contract"), dict):
        expected = manifest["replacement_artifact_contract"].get("output_sha256")
        contract_source = "replacement_artifact_contract.output_sha256"
    matched = bool(expected == activations_sha256)
    return {
        "status": "LOCKED_ARTIFACT_MATCH" if matched else "LOCAL_RECAPTURE_HASH_MISMATCH",
        "expected_activation_sha256": expected,
        "actual_activation_sha256": activations_sha256,
        "contract_source": contract_source,
        "formal_gate_valid": matched,
    }


def _noetic_index(row: dict[str, Any]) -> int:
    value = int(row["element_noetic_tks"])
    if value == 10:
        return 9
    return value - 1


def _noetic_labels_for_rows(rows_by_id: dict[str, dict[str, Any]], sample_ids: list[str]) -> np.ndarray:
    return np.asarray([_noetic_index(rows_by_id[str(sample_id)]) for sample_id in sample_ids], dtype=np.int64)


def _non_involution_pairs() -> list[tuple[int, int]]:
    involution = {tuple(sorted(pair)) for pair in _INVOLUTION_PAIRS}
    return [pair for pair in combinations(range(len(_NOETIC_LABELS)), 2) if tuple(sorted(pair)) not in involution]


def _cosine_by_pair(normalized_scores_by_class: np.ndarray, pairs: list[tuple[int, int]]) -> list[float]:
    return [float(np.dot(normalized_scores_by_class[i], normalized_scores_by_class[j])) for i, j in pairs]


def _opposition_metrics(scores_by_token: np.ndarray) -> dict[str, Any]:
    normalized = _center_unit_columns(scores_by_token.T)
    involution_values = _cosine_by_pair(normalized, list(_INVOLUTION_PAIRS))
    non_involution_values = _cosine_by_pair(normalized, _non_involution_pairs())
    all_values = _cosine_by_pair(normalized, list(combinations(range(len(_NOETIC_LABELS)), 2)))
    median = float(np.median(all_values))
    pair_rows = []
    below_median = 0
    for left_idx, right_idx in _INVOLUTION_PAIRS:
        cosine = float(np.dot(normalized[left_idx], normalized[right_idx]))
        below = bool(cosine < median)
        below_median += int(below)
        pair_rows.append(
            {
                "left": _NOETIC_LABELS[left_idx],
                "right": _NOETIC_LABELS[right_idx],
                "left_name": _NOETIC_NAMES[left_idx],
                "right_name": _NOETIC_NAMES[right_idx],
                "cosine": cosine,
                "opposition": float(-cosine),
                "below_global_pairwise_median": below,
            }
        )
    involution_mean = float(np.mean(involution_values))
    non_involution_mean = float(np.mean(non_involution_values))
    return {
        "involution_mean_cosine": involution_mean,
        "non_involution_mean_cosine": non_involution_mean,
        "non_involution_minus_involution_cosine": float(non_involution_mean - involution_mean),
        "involution_mean_opposition": float(-involution_mean),
        "non_involution_mean_opposition": float(-non_involution_mean),
        "global_pairwise_median_cosine": median,
        "involution_pairs_below_median": int(below_median),
        "involution_pair_rows": pair_rows,
    }


def _random_direction_metrics(output_w: np.ndarray, *, n_random: int, seed: int) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    hidden_dim = int(output_w.shape[1])
    out = []
    for _ in range(n_random):
        directions = rng.standard_normal((len(_NOETIC_LABELS), hidden_dim))
        scores = _score_token_space(directions, output_w)
        out.append(_opposition_metrics(scores))
    return out


def _top_tokens(scores_by_token: np.ndarray, tokenizer: Any, top_k: int, *, readable_only: bool) -> dict[str, Any]:
    out: dict[str, Any] = {}
    scores_by_class = np.asarray(scores_by_token, dtype=np.float64).T
    for class_idx, label in enumerate(_NOETIC_LABELS):
        scores = scores_by_class[class_idx]
        out[label] = {
            "name": _NOETIC_NAMES[class_idx],
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
                        {"noetic": label, "polarity": polarity, "token": item["token"], "token_id": item["token_id"]}
                    )
    return {
        "total_top_tokens": int(total),
        "readable_top_tokens": int(readable),
        "readable_rate": float(readable / total) if total else 0.0,
        "unreadable_examples": unreadable_examples,
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


def _status_from_gates(report: dict[str, Any]) -> str:
    if not report["artifact_contract"]["formal_gate_valid"]:
        return "STAGE28A_NOETIC_INVOLUTION_SONAR_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"
    if report["probe"]["test_acc"] < float(report["gates"]["min_probe_test_acc"]):
        return "NULL_NOETIC_INVOLUTION_SONAR_PROBE_FLOOR_NOT_MET"
    if report["top_token_readability"]["readable_rate"] < float(report["gates"]["min_readable_rate"]):
        return "NULL_NOETIC_INVOLUTION_SONAR_ARTIFACT_DOMINATED"
    margin_ok = report["opposition_metrics"]["non_involution_minus_involution_cosine"] > 0.0
    control_ok = (
        report["random_control_summary"]["non_involution_minus_involution_cosine"]["empirical_p_random_ge_actual"]
        < float(report["gates"]["max_control_p"])
    )
    rank_ok = report["opposition_metrics"]["involution_pairs_below_median"] >= int(report["gates"]["min_pairs_below_median"])
    if margin_ok and control_ok and rank_ok:
        return "PASS_BOUNDED_NOETIC_INVOLUTION_SONAR"
    if not margin_ok and not rank_ok:
        return "NULL_NOETIC_INVOLUTION_SONAR_NOT_ESTABLISHED"
    return "GREY_NOETIC_INVOLUTION_SONAR_PARTIAL"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    activation_manifest_path = _resolve(args.activation_manifest)
    if not activations_path.exists():
        raise FileNotFoundError(
            f"Stage 28A requires the Stage 9 activation artifact: {activations_path}. "
            "Recapture or pull the artifact before running sonar."
        )
    activations_sha256 = _sha256_of_file(activations_path)
    artifact_contract = _artifact_contract(activations_sha256, activation_manifest_path)
    rows = _load_rows(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = stage6._split_indices(rows_by_id, sample_ids)
    X = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    y = _noetic_labels_for_rows(rows_by_id, sample_ids)
    fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _NOETIC_LABELS)
    directions = _probe_raw_directions(fitted["scaler"], fitted["clf"])
    output_w, tokenizer, model_meta = _load_output_embeddings(bool(args.allow_download))
    if int(output_w.shape[1]) != int(directions.shape[1]):
        raise ValueError(f"direction dim {directions.shape[1]} != output embedding dim {output_w.shape[1]}")
    scores_by_token = _score_token_space(directions, output_w)
    opposition = _opposition_metrics(scores_by_token)
    random_metrics = _random_direction_metrics(output_w, n_random=int(args.n_random), seed=int(args.seed))
    random_control_summary = {
        "non_involution_minus_involution_cosine": _summarize_random(
            opposition["non_involution_minus_involution_cosine"],
            [row["non_involution_minus_involution_cosine"] for row in random_metrics],
        )
    }
    raw_top_tokens = _top_tokens(scores_by_token, tokenizer, int(args.top_k), readable_only=False)
    readability = _top_token_readability(raw_top_tokens)
    report: dict[str, Any] = {
        "schema_version": "stage28a_noetic_involution_sonar.v1",
        "status": "PENDING_STATUS_COMPUTED_BELOW",
        "model": model_meta,
        "input_file": input_path.name,
        "input_sha256": _sha256_of_file(input_path),
        "activations_file": activations_path.name,
        "activations_sha256": activations_sha256,
        "activation_manifest_file": activation_manifest_path.name,
        "artifact_contract": artifact_contract,
        "locked_readout": {"readout_key": _READOUT_KEY, "readout_name": _READOUT_NAME, "layer": _LAYER},
        "noetic_labels": list(_NOETIC_LABELS),
        "noetic_names": list(_NOETIC_NAMES),
        "involution_pairs": [
            [_NOETIC_LABELS[left], _NOETIC_LABELS[right]] for left, right in _INVOLUTION_PAIRS
        ],
        "probe": {
            "train_acc": float(fitted["train"]["acc"]),
            "val_acc": float(fitted["val"]["acc"]),
            "test_acc": float(fitted["test"]["acc"]),
        },
        "opposition_metrics": opposition,
        "random_control_summary": random_control_summary,
        "top_token_readability": readability,
        "top_tokens_by_noetic": raw_top_tokens,
        "readable_top_tokens_by_noetic": _top_tokens(scores_by_token, tokenizer, int(args.top_k), readable_only=True),
        "gates": {
            "min_probe_test_acc": float(args.min_probe_test_acc),
            "min_readable_rate": float(args.min_readable_rate),
            "max_control_p": float(args.max_control_p),
            "min_pairs_below_median": int(args.min_pairs_below_median),
        },
        "plain_english_read": (
            "This report tests whether formal Noetic involution pairs produce opposed token signatures "
            "when the Stage 9 40-Element fixture is collapsed to a 10-way Noetic readout."
        ),
        "boundary": (
            "Stage 28A is static output-embedding sonar over collapsed Noetic readout directions. "
            "It does not prove exact neurons, complete circuits, Noetic clusters, 40-Element hard-partner "
            "resolution, raw CAS-symbol understanding, free-form generation control, or cross-model generality."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    control = report["random_control_summary"]["non_involution_minus_involution_cosine"]
    lines = [
        "# Stage 28A Noetic Involution Sonar",
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
        f"- Noetic probe test accuracy: `{report['probe']['test_acc']:.4f}`",
        f"- Artifact contract: `{report['artifact_contract']['status']}`",
        "",
        "## Involution Opposition",
        "",
        f"- Involution mean cosine: `{report['opposition_metrics']['involution_mean_cosine']:.6f}`",
        f"- Non-involution mean cosine: `{report['opposition_metrics']['non_involution_mean_cosine']:.6f}`",
        f"- Opposition margin (non-involution - involution): `{report['opposition_metrics']['non_involution_minus_involution_cosine']:.6f}`",
        f"- p(random >= actual): `{control['empirical_p_random_ge_actual']:.4f}`",
        f"- Involution pairs below global median: `{report['opposition_metrics']['involution_pairs_below_median']} / 3`",
        "",
        "| Pair | Cosine | Opposition | Below median |",
        "|---|---:|---:|---|",
    ]
    for row in report["opposition_metrics"]["involution_pair_rows"]:
        lines.append(
            f"| `{row['left']}` / `{row['right']}` | {row['cosine']:.6f} | "
            f"{row['opposition']:.6f} | `{row['below_global_pairwise_median']}` |"
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
    for label in report["noetic_labels"]:
        tokens = ", ".join(
            item["token"].replace("\n", "\\n")
            for item in report["readable_top_tokens_by_noetic"][label]["positive"][:5]
        )
        lines.append(f"- `{label}` {report['readable_top_tokens_by_noetic'][label]['name']}: {tokens}")
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage9_elements_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage9_elements_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage24b_40_element_cpu_recap_prereg_20260521.json")
    parser.add_argument("--out-report", default="stage28a_noetic_involution_sonar_20260521.json")
    parser.add_argument("--out-md", default="STAGE28A_NOETIC_INVOLUTION_SONAR_20260521.md")
    parser.add_argument("--top-k", type=int, default=12)
    parser.add_argument("--n-random", type=int, default=100)
    parser.add_argument("--seed", type=int, default=_SEED)
    parser.add_argument("--min-probe-test-acc", type=float, default=0.50)
    parser.add_argument("--min-readable-rate", type=float, default=0.50)
    parser.add_argument("--max-control-p", type=float, default=0.05)
    parser.add_argument("--min-pairs-below-median", type=int, default=2)
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
                "opposition_margin": report["opposition_metrics"]["non_involution_minus_involution_cosine"],
                "control_p": report["random_control_summary"]["non_involution_minus_involution_cosine"][
                    "empirical_p_random_ge_actual"
                ],
                "pairs_below_median": report["opposition_metrics"]["involution_pairs_below_median"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
