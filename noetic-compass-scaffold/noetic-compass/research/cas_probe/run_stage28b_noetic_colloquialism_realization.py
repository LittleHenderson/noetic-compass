"""Stage 28B Noetic colloquialism realization probe.

This runner tests whether canonical natural-language Noetic colloquialisms
produce hidden states that the Stage 9 collapsed Noetic probe can read. It is
not static W_U sonar: Pythia processes the phrase through a normal forward pass,
then the locked layer-5 readout scores the phrase token activation.

Boundary: this is single-Noetic phrase realization evidence on Pythia-160M. It
does not prove Noetic clusters, exact neurons, complete circuits, raw CAS-symbol
understanding, or free-form generation control.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

import evaluate_stage6_role_bound_full as stage6
from capture_stage6_role_bound_activations import _find_token_for_char
from evaluate_stage7_factor_check import _fit_readout
from evaluate_stage9_elements_pilot import _load_rows
from run_stage28a_noetic_involution_sonar import _artifact_contract, _noetic_labels_for_rows
from stage28b_noetic_colloquialism_realization_spec import (
    stage28b_claim_boundary,
    stage28b_colloquialism_fixture,
)


_HERE = Path(__file__).resolve().parent
_MODEL_NAME = "EleutherAI/pythia-160m"
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


def _sha256_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _carrier_text(phrase: str) -> str:
    return f'The speaker says "{phrase}". The quoted phrase is the focus.'


def _fixture_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(stage28b_colloquialism_fixture()):
        phrase = str(row["phrase"])
        text = _carrier_text(phrase)
        start = text.index(phrase)
        rows.append(
            {
                "row_id": f"stage28b_{idx:03d}",
                "noetic": row["noetic"],
                "noetic_name": row["name"],
                "target_index": _LABEL_TO_INDEX[row["noetic"]],
                "phrase": phrase,
                "english": text,
                "phrase_start": int(start),
                "phrase_end": int(start + len(phrase)),
            }
        )
    return rows


def _token_indices_overlapping_span(offsets: list[tuple[int, int]], start: int, end: int) -> list[int]:
    out: list[int] = []
    for idx, (left, right) in enumerate(offsets):
        if right <= left:
            continue
        if left < end and right > start:
            out.append(idx)
    return out


def _fit_stage9_noetic_probe(input_path: Path, activations_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = _load_rows(input_path)
    rows_by_id = {str(row["sample_id"]): row for row in rows}
    data = np.load(activations_path, allow_pickle=False)
    sample_ids = [str(x) for x in data["sample_ids"].tolist()]
    splits = stage6._split_indices(rows_by_id, sample_ids)
    X = np.asarray(data[_READOUT_KEY][:, _LAYER, :], dtype=np.float64)
    y = _noetic_labels_for_rows(rows_by_id, sample_ids)
    fitted = _fit_readout(X, y, splits["train"], splits["val"], splits["test"], _NOETIC_LABELS)
    probe_meta = {
        "train_acc": float(fitted["train"]["acc"]),
        "val_acc": float(fitted["val"]["acc"]),
        "test_acc": float(fitted["test"]["acc"]),
        "n_train": int(len(splits["train"])),
        "n_val": int(len(splits["val"])),
        "n_test": int(len(splits["test"])),
    }
    return fitted, probe_meta


def _load_model_and_tokenizer(allow_download: bool, device: str) -> tuple[Any, Any, Any, dict[str, Any]]:
    import torch
    import transformers as transformers_pkg
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=not allow_download, use_fast=True)
    if not getattr(tokenizer, "is_fast", False):
        raise RuntimeError("Stage 28B requires a fast tokenizer with offset mapping")
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
    meta = {
        "model_name": _MODEL_NAME,
        "model_source": getattr(model.config, "_name_or_path", _MODEL_NAME),
        "model_revision": getattr(model.config, "_commit_hash", None) or "unknown",
        "hidden_dim": int(model.config.hidden_size),
        "n_layer_positions": int(model.config.num_hidden_layers) + 1,
        "device": str(actual_device),
        "transformers": getattr(transformers_pkg, "__version__", "unknown"),
        "torch": getattr(torch, "__version__", "unknown"),
    }
    return model, tokenizer, actual_device, meta


def _capture_phrase_vectors(
    fixture_rows: list[dict[str, Any]],
    model: Any,
    tokenizer: Any,
    device: Any,
    *,
    max_length: int,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    import torch

    vectors: list[np.ndarray] = []
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
                focus_idx = _find_token_for_char(offsets, int(row["phrase_start"]))
                token_indices = [focus_idx]
            focus_idx = int(token_indices[0])
            token_id = int(encoded["input_ids"][0, focus_idx].item())
            encoded = encoded.to(device)
            outputs = model(**encoded)
            vec = outputs.hidden_states[_LAYER][0, focus_idx, :].detach().cpu().float().numpy()
            vectors.append(vec)
            audit_rows.append(
                {
                    **row,
                    "focus_token_index": focus_idx,
                    "phrase_token_indices": [int(x) for x in token_indices],
                    "focus_token_id": token_id,
                    "focus_token_text": tokenizer.decode([token_id]),
                    "sequence_length": int(encoded["attention_mask"][0].sum().item()),
                }
            )
    return np.asarray(vectors, dtype=np.float64), audit_rows


def _binomial_upper_tail(k: int, n: int, p: float) -> float:
    if not (0.0 <= p <= 1.0):
        raise ValueError(f"p must be in [0,1], got {p}")
    return float(math.fsum(math.comb(n, i) * (p**i) * ((1.0 - p) ** (n - i)) for i in range(k, n + 1)))


def _score_colloquialisms(fitted: dict[str, Any], X: np.ndarray, fixture_rows: list[dict[str, Any]]) -> dict[str, Any]:
    scaled = fitted["scaler"].transform(np.asarray(X, dtype=np.float64))
    probs = np.asarray(fitted["clf"].predict_proba(scaled), dtype=np.float64)
    pred = np.argmax(probs, axis=1)
    targets = np.asarray([int(row["target_index"]) for row in fixture_rows], dtype=np.int64)
    top2 = np.argsort(probs, axis=1)[:, -2:]
    target_probs = probs[np.arange(len(targets)), targets]
    exact = pred == targets
    top2_hits = np.asarray([target in row for target, row in zip(targets, top2)], dtype=bool)
    partner_margins: list[float] = []
    partner_rows: list[dict[str, Any]] = []
    row_reports: list[dict[str, Any]] = []
    for i, row in enumerate(fixture_rows):
        target = int(targets[i])
        predicted = int(pred[i])
        partner = _INVOLUTION_PARTNER.get(target)
        partner_margin = None
        if partner is not None:
            partner_margin = float(probs[i, target] - probs[i, partner])
            partner_margins.append(partner_margin)
            partner_rows.append(
                {
                    "row_id": row["row_id"],
                    "target": _NOETIC_LABELS[target],
                    "partner": _NOETIC_LABELS[partner],
                    "target_minus_partner_probability": partner_margin,
                    "target_beats_partner": bool(partner_margin > 0.0),
                }
            )
        row_reports.append(
            {
                "row_id": row["row_id"],
                "phrase": row["phrase"],
                "target": _NOETIC_LABELS[target],
                "target_name": _NOETIC_NAMES[target],
                "predicted": _NOETIC_LABELS[predicted],
                "predicted_name": _NOETIC_NAMES[predicted],
                "exact": bool(exact[i]),
                "top2": bool(top2_hits[i]),
                "target_probability": float(target_probs[i]),
                "predicted_probability": float(probs[i, predicted]),
                "partner_margin": partner_margin,
            }
        )
    per_noetic: list[dict[str, Any]] = []
    for idx, label in enumerate(_NOETIC_LABELS):
        mask = targets == idx
        if not np.any(mask):
            continue
        per_noetic.append(
            {
                "noetic": label,
                "name": _NOETIC_NAMES[idx],
                "n": int(np.sum(mask)),
                "exact_accuracy": float(np.mean(exact[mask])),
                "top2_accuracy": float(np.mean(top2_hits[mask])),
                "mean_target_probability": float(np.mean(target_probs[mask])),
                "predicted_counts": {
                    _NOETIC_LABELS[pred_idx]: int(np.sum(pred[mask] == pred_idx))
                    for pred_idx in range(len(_NOETIC_LABELS))
                    if int(np.sum(pred[mask] == pred_idx)) > 0
                },
            }
        )
    return {
        "n_rows": int(len(targets)),
        "exact_correct": int(np.sum(exact)),
        "exact_accuracy": float(np.mean(exact)),
        "top2_correct": int(np.sum(top2_hits)),
        "top2_accuracy": float(np.mean(top2_hits)),
        "mean_target_probability": float(np.mean(target_probs)),
        "median_target_probability": float(np.median(target_probs)),
        "target_probability_lift_over_chance": float(np.mean(target_probs) - (1.0 / len(_NOETIC_LABELS))),
        "exact_binomial_p_vs_chance": _binomial_upper_tail(int(np.sum(exact)), int(len(targets)), 1.0 / len(_NOETIC_LABELS)),
        "involution_partner_rows": partner_rows,
        "involution_partner_n": int(len(partner_margins)),
        "involution_partner_positive": int(np.sum(np.asarray(partner_margins) > 0.0)) if partner_margins else 0,
        "involution_partner_positive_share": float(np.mean(np.asarray(partner_margins) > 0.0)) if partner_margins else 0.0,
        "mean_involution_target_minus_partner_probability": float(np.mean(partner_margins)) if partner_margins else 0.0,
        "per_noetic": per_noetic,
        "row_reports": row_reports,
    }


def _status_from_gates(report: dict[str, Any]) -> str:
    gates = report["gates"]
    metrics = report["colloquialism_metrics"]
    if not report["artifact_contract"]["formal_gate_valid"]:
        return "STAGE28B_NOETIC_COLLOQUIALISM_DIAGNOSTIC_ONLY_ARTIFACT_MISMATCH"
    if report["probe"]["test_acc"] < gates["min_probe_test_acc"]:
        return "NULL_NOETIC_COLLOQUIALISM_REALIZATION_PROBE_FLOOR_NOT_MET"
    acc_ok = metrics["exact_accuracy"] >= gates["min_exact_accuracy"] and metrics["exact_binomial_p_vs_chance"] < gates["max_exact_binomial_p"]
    lift_ok = metrics["mean_target_probability"] >= gates["min_mean_target_probability"]
    top2_ok = metrics["top2_accuracy"] >= gates["min_top2_accuracy"]
    partner_ok = metrics["involution_partner_positive_share"] >= gates["min_involution_partner_positive_share"]
    if acc_ok and lift_ok and top2_ok and partner_ok:
        return "PASS_BOUNDED_NOETIC_COLLOQUIALISM_REALIZATION"
    if not acc_ok and not lift_ok:
        return "NULL_NOETIC_COLLOQUIALISM_REALIZATION_NOT_ESTABLISHED"
    return "GREY_NOETIC_COLLOQUIALISM_REALIZATION_PARTIAL"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    input_path = _resolve(args.input)
    activations_path = _resolve(args.activations)
    activation_manifest_path = _resolve(args.activation_manifest)
    prereg_path = _resolve(args.preregistration)
    if not activations_path.exists():
        raise FileNotFoundError(f"Stage 28B requires the Stage 9 activation artifact: {activations_path}")
    activations_sha256 = _sha256_of_file(activations_path)
    artifact_contract = _artifact_contract(activations_sha256, activation_manifest_path)
    fitted, probe_meta = _fit_stage9_noetic_probe(input_path, activations_path)
    fixture_rows = _fixture_rows()
    model, tokenizer, device, model_meta = _load_model_and_tokenizer(bool(args.allow_download), str(args.device))
    X, audit_rows = _capture_phrase_vectors(fixture_rows, model, tokenizer, device, max_length=int(args.max_length))
    metrics = _score_colloquialisms(fitted, X, audit_rows)
    report: dict[str, Any] = {
        "schema_version": "stage28b_noetic_colloquialism_realization.v1",
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
        "locked_probe_readout": {"readout_key": _READOUT_KEY, "readout_name": _READOUT_NAME, "layer": _LAYER},
        "runtime_readout": {
            "name": "phrase_first_token",
            "layer": _LAYER,
            "definition": "first tokenizer token overlapping the quoted colloquial phrase span",
        },
        "noetic_labels": list(_NOETIC_LABELS),
        "noetic_names": list(_NOETIC_NAMES),
        "probe": probe_meta,
        "fixture_rows": audit_rows,
        "colloquialism_metrics": metrics,
        "gates": {
            "min_probe_test_acc": float(args.min_probe_test_acc),
            "min_exact_accuracy": float(args.min_exact_accuracy),
            "max_exact_binomial_p": float(args.max_exact_binomial_p),
            "min_mean_target_probability": float(args.min_mean_target_probability),
            "min_top2_accuracy": float(args.min_top2_accuracy),
            "min_involution_partner_positive_share": float(args.min_involution_partner_positive_share),
        },
        "claim_boundary": stage28b_claim_boundary(),
        "plain_english_read": (
            "This report tests the colloquialism route: natural-language Noetic phrases are processed by Pythia, "
            "then the existing Stage 9 Noetic probe reads the resulting layer-5 phrase-token hidden state."
        ),
        "boundary": (
            "Stage 28B is a single-Noetic colloquial phrase realization probe on Pythia-160M. It does not prove "
            "Noetic clusters, exact neurons, complete circuits, raw CAS-symbol understanding, free-form generation "
            "control, or cross-model generality."
        ),
    }
    report["status"] = _status_from_gates(report)
    return report


def _write_md(report: dict[str, Any], out_md: Path) -> None:
    metrics = report["colloquialism_metrics"]
    lines = [
        "# Stage 28B Noetic Colloquialism Realization",
        "",
        f"**Status:** `{report['status']}`",
        "",
        "## Plain English",
        "",
        report["plain_english_read"],
        "",
        "## Probe And Fixture",
        "",
        f"- Model: `{report['model']['model_name']}`",
        f"- Runtime device: `{report['model']['device']}`",
        f"- Locked probe readout: `{report['locked_probe_readout']['readout_key']}` layer `{report['locked_probe_readout']['layer']}`",
        f"- Runtime readout: `{report['runtime_readout']['name']}` layer `{report['runtime_readout']['layer']}`",
        f"- Noetic probe test accuracy: `{report['probe']['test_acc']:.4f}`",
        f"- Artifact contract: `{report['artifact_contract']['status']}`",
        f"- Fixture rows: `{metrics['n_rows']}`",
        "",
        "## Metrics",
        "",
        f"- Exact accuracy: `{metrics['exact_accuracy']:.4f}` ({metrics['exact_correct']} / {metrics['n_rows']})",
        f"- Exact-binomial p vs 10-way chance: `{metrics['exact_binomial_p_vs_chance']:.6g}`",
        f"- Top-2 accuracy: `{metrics['top2_accuracy']:.4f}` ({metrics['top2_correct']} / {metrics['n_rows']})",
        f"- Mean target probability: `{metrics['mean_target_probability']:.4f}`",
        f"- Target probability lift over chance: `{metrics['target_probability_lift_over_chance']:.4f}`",
        f"- Involution target > partner share: `{metrics['involution_partner_positive_share']:.4f}` "
        f"({metrics['involution_partner_positive']} / {metrics['involution_partner_n']})",
        f"- Mean target-partner probability margin: `{metrics['mean_involution_target_minus_partner_probability']:.4f}`",
        "",
        "## Per-Noetic Readout",
        "",
        "| Noetic | Name | Exact | Top-2 | Mean target probability | Predicted counts |",
        "|---|---|---:|---:|---:|---|",
    ]
    for row in metrics["per_noetic"]:
        lines.append(
            f"| `{row['noetic']}` | {row['name']} | {row['exact_accuracy']:.3f} | "
            f"{row['top2_accuracy']:.3f} | {row['mean_target_probability']:.3f} | `{row['predicted_counts']}` |"
        )
    lines.extend(
        [
            "",
            "## Row Audit",
            "",
            "| Target | Phrase | Predicted | Exact | Target probability | Focus token |",
            "|---|---|---|---|---:|---|",
        ]
    )
    focus_by_id = {row["row_id"]: row for row in report["fixture_rows"]}
    for row in metrics["row_reports"]:
        focus = focus_by_id[row["row_id"]]["focus_token_text"].replace("\n", "\\n")
        lines.append(
            f"| `{row['target']}` | {row['phrase']} | `{row['predicted']}` | `{row['exact']}` | "
            f"{row['target_probability']:.3f} | `{focus}` |"
        )
    lines.extend(["", "## Boundary", "", report["boundary"], ""])
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="stage9_elements_pilot_20260517.jsonl")
    parser.add_argument("--activations", default="stage9_elements_pilot_activations_20260517.npz")
    parser.add_argument("--activation-manifest", default="stage24b_40_element_cpu_recap_prereg_20260521.json")
    parser.add_argument("--preregistration", default="stage28b_noetic_colloquialism_prereg_20260521.json")
    parser.add_argument("--out-report", default="stage28b_noetic_colloquialism_realization_20260521.json")
    parser.add_argument("--out-md", default="STAGE28B_NOETIC_COLLOQUIALISM_REALIZATION_20260521.md")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--min-probe-test-acc", type=float, default=0.50)
    parser.add_argument("--min-exact-accuracy", type=float, default=0.45)
    parser.add_argument("--max-exact-binomial-p", type=float, default=0.05)
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
                "probe_test_acc": report["probe"]["test_acc"],
                "exact_accuracy": report["colloquialism_metrics"]["exact_accuracy"],
                "exact_binomial_p": report["colloquialism_metrics"]["exact_binomial_p_vs_chance"],
                "top2_accuracy": report["colloquialism_metrics"]["top2_accuracy"],
                "mean_target_probability": report["colloquialism_metrics"]["mean_target_probability"],
                "involution_positive_share": report["colloquialism_metrics"]["involution_partner_positive_share"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
