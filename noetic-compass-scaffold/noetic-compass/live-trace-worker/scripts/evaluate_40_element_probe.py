#!/usr/bin/env python3
r"""Evaluate the 40-Element (10 Noetics x 4 Domains) readout on a captured
open-weight probe dataset.

Replicates the Pythia-160M 40-Element closure target (89.8% readout, +39.7pp
over text baseline; CAS_HARNESS_SPEC_SHEET_v1_5_20260519) on a different
substrate, using only labels already present in the captured dataset.

The 40-Element label is constructed at runtime as `operator|domain` from the
existing `labels_operator` (10 Noetics: ^0..^9) and `labels_domain`
(4 Domains: P/C/E/O) arrays. No new capture is needed.

Usage on RunPod (canonical dataset location):

    python evaluate_40_element_probe.py \
      --dataset /workspace/cas-harness-large-eval/data/gpt_neox_20b_augmented_400_layers_0_43.npz \
      --metadata /workspace/cas-harness-large-eval/data/gpt_neox_20b_augmented_400_layers_0_43.metadata.json \
      --output /workspace/cas-harness-large-eval/results/gpt_neox_20b_40_element_probe_eval_report.json

Usage locally (against the archived copy):

    python evaluate_40_element_probe.py ^
      --dataset D:\tksCAS-archive\gpt_neox_20b_probe_dataset_eval_20260526\gpt_neox_20b_augmented_400_layers_0_43.npz ^
      --metadata D:\tksCAS-archive\gpt_neox_20b_probe_dataset_eval_20260526\gpt_neox_20b_augmented_400_layers_0_43.metadata.json ^
      --output .\gpt_neox_20b_40_element_probe_eval_report.json

Output schema matches the existing per-axis probe eval reports for direct
comparison: best_layer, per_layer, controls (majority, shuffled-label,
text-hash), populated cell count, and an explicit Pythia-160M comparator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


SCHEMA_VERSION = "cas_harness_40_element_probe_eval.v1"
EXPECTED_OPERATORS = tuple(f"^{i}" for i in range(10))
EXPECTED_DOMAINS = ("P", "C", "E", "O")
EXPECTED_40E_CELLS = tuple(
    f"{operator}|{domain}"
    for operator in EXPECTED_OPERATORS
    for domain in EXPECTED_DOMAINS
)
DEFAULT_MIN_SAMPLES_PER_CELL = 10
REQUIRED_NPZ_KEYS = ("features", "layers", "labels_domain", "labels_operator", "prompts")


def _strip_framing_tags(prompt: str) -> str:
    """Strip leading [bracket framing] tags so paraphrase siblings share a base."""
    s = str(prompt)
    while s.startswith("[") and "]" in s:
        s = s.split("]", 1)[1].lstrip()
    return s


def _get_path_value(item: dict, path: str | None):
    if not path:
        return None
    current = item
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _load_scenario_meta(path: Path | None) -> dict[str, dict]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    scenarios = payload.get("scenarios", payload) if isinstance(payload, dict) else payload
    if not isinstance(scenarios, list):
        raise SystemExit("--scenario-path must be a list or contain a scenarios list")
    out: dict[str, dict] = {}
    for index, item in enumerate(scenarios):
        if not isinstance(item, dict):
            continue
        scenario_id = str(item.get("id") or item.get("scenario_id") or f"scenario-{index + 1:04d}")
        out[scenario_id] = item
    return out


def _fixed_split_from_scenarios(
    *,
    scenario_ids: np.ndarray,
    scenario_meta: dict[str, dict],
    split_key: str,
    test_split: str,
) -> tuple[np.ndarray, np.ndarray]:
    train_idx: list[int] = []
    test_idx: list[int] = []
    missing: list[str] = []
    for index, scenario_id in enumerate(scenario_ids.tolist()):
        item = scenario_meta.get(str(scenario_id))
        if item is None:
            missing.append(str(scenario_id))
            continue
        split = str(_get_path_value(item, split_key) or "")
        if split == test_split:
            test_idx.append(index)
        elif split:
            train_idx.append(index)
    if missing:
        raise SystemExit(f"--scenario-path is missing {len(missing)} dataset scenario_ids, e.g. {missing[:5]}")
    if not train_idx or not test_idx:
        raise SystemExit(
            f"--split-key {split_key!r} with --test-split {test_split!r} did not produce train/test rows"
        )
    return np.asarray(train_idx, dtype=int), np.asarray(test_idx, dtype=int)


def _groups_for_rows(
    *,
    prompts: np.ndarray,
    scenario_ids: np.ndarray,
    scenario_meta: dict[str, dict],
    group_key: str | None,
) -> np.ndarray:
    groups: list[str] = []
    for prompt, scenario_id in zip(prompts.tolist(), scenario_ids.tolist()):
        item = scenario_meta.get(str(scenario_id))
        value = _get_path_value(item, group_key) if item is not None and group_key else None
        groups.append(str(value or _strip_framing_tags(str(prompt))))
    return np.asarray(groups)


def _load_confirmed_text_baseline(path: Path | None) -> dict | None:
    if path is None:
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    baseline = report.get("text_baseline") or {}
    gate = report.get("claim_gate") or {}
    return {
        "source_report": str(path),
        "axis": report.get("axis"),
        "model": baseline.get("model"),
        "test_acc": baseline.get("test_accuracy"),
        "test_macro_f1": baseline.get("test_macro_f1"),
        "cas_beats_text_claim_allowed": gate.get("cas_beats_text_claim_allowed"),
        "status": gate.get("status"),
        "target_text_baseline_ceiling": gate.get("target_text_baseline_ceiling"),
    }


def _cell_sort_key(cell: str) -> tuple[int, int, str]:
    operator, _, domain = cell.partition("|")
    try:
        operator_idx = int(operator.removeprefix("^"))
    except ValueError:
        operator_idx = 99
    try:
        domain_idx = EXPECTED_DOMAINS.index(domain)
    except ValueError:
        domain_idx = 99
    return operator_idx, domain_idx, cell


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_descriptor(artifact_id: str, artifact_type: str, path: Path) -> dict:
    stat = path.stat()
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "content_sha256": _sha256_file(path),
        "byte_count": int(stat.st_size),
        "storage_uri": str(path),
        "redaction_class": "internal_eval_artifact",
        "created_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }


def build_40e_readiness_gate(
    class_distribution: dict[str, int],
    *,
    min_samples_per_cell: int = DEFAULT_MIN_SAMPLES_PER_CELL,
) -> dict:
    expected_cells = set(EXPECTED_40E_CELLS)
    observed_cells = set(class_distribution)
    missing_cells = sorted(expected_cells - observed_cells, key=_cell_sort_key)
    unexpected_cells = sorted(observed_cells - expected_cells, key=_cell_sort_key)
    sparse_cells = {
        cell: int(class_distribution[cell])
        for cell in sorted(expected_cells & observed_cells, key=_cell_sort_key)
        if int(class_distribution[cell]) < min_samples_per_cell
    }

    blocking_reasons: list[str] = []
    if missing_cells:
        blocking_reasons.append(f"{len(missing_cells)} expected 40E cells are absent")
    if sparse_cells:
        blocking_reasons.append(
            f"{len(sparse_cells)} populated cells have fewer than "
            f"{min_samples_per_cell} samples"
        )
    if unexpected_cells:
        blocking_reasons.append(
            f"{len(unexpected_cells)} labels are outside the canonical ^0..^9 x P/C/E/O grid"
        )

    packet_ready = not blocking_reasons
    return {
        "status": "packet_ready" if packet_ready else "blocked_missing_balanced_40e_artifact",
        "packet_ready": packet_ready,
        "axis": "40_element_operator_x_domain",
        "expected_cells": len(EXPECTED_40E_CELLS),
        "populated_expected_cells": len(expected_cells & observed_cells),
        "min_samples_per_cell_required": int(min_samples_per_cell),
        "missing_cells": missing_cells,
        "sparse_cells": sparse_cells,
        "unexpected_cells": unexpected_cells,
        "blocking_reasons": blocking_reasons,
        "required_artifact": {
            "name": "balanced_40_element_activation_dataset",
            "description": (
                "A source-derived TKS40 activation dataset with every canonical "
                "^0..^9 x P/C/E/O cell populated at or above the configured "
                "minimum sample count."
            ),
            "required_npz_keys": list(REQUIRED_NPZ_KEYS),
            "feature_shape": "[N_scenarios, N_layers, hidden_dim]",
            "labels": ["labels_operator", "labels_domain"],
            "how_to_supply": (
                "Capture or copy the balanced 40E .npz plus its metadata JSON, then run "
                "this evaluator with --dataset PATH --metadata PATH --output PATH. "
                "Use --require-balanced-40e to make packet assembly fail fast when "
                "the artifact is incomplete."
            ),
        },
    }


def _build_linear_probe(C: float, max_iter: int):
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=C,
            max_iter=max_iter,
            class_weight="balanced",
            solver="lbfgs",
            n_jobs=-1,
        ),
    )


def _fit_linear_probe(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    C: float,
    max_iter: int,
) -> tuple[float, float]:
    """Fit StandardScaler + balanced logistic regression; return (acc, macro_f1)."""
    clf = _build_linear_probe(C, max_iter)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    acc = float(accuracy_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    return acc, f1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scenario-path", type=Path)
    parser.add_argument("--split-key")
    parser.add_argument("--test-split", default="test")
    parser.add_argument("--group-key")
    parser.add_argument("--confirmed-text-baseline-report", type=Path)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--shuffled-trials", type=int, default=20)
    parser.add_argument("--probe-C", type=float, default=0.1)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--min-samples-per-cell", type=int, default=DEFAULT_MIN_SAMPLES_PER_CELL)
    parser.add_argument(
        "--require-balanced-40e",
        action="store_true",
        help=(
            "Exit before probe training unless all 40 canonical cells have at least "
            "--min-samples-per-cell samples. Writes a guard report to --output."
        ),
    )
    args = parser.parse_args()

    print(f"loading dataset: {args.dataset}")
    data = np.load(args.dataset, allow_pickle=True)
    required_keys = set(REQUIRED_NPZ_KEYS)
    missing = required_keys - set(data.files)
    if missing:
        raise SystemExit(
            f"dataset missing required keys for 40-Element relabel: {sorted(missing)}. "
            "This script requires 'features', 'layers', 'labels_domain', 'labels_operator', 'prompts'."
        )

    features = data["features"]
    layers = data["layers"]
    labels_domain = data["labels_domain"]
    labels_operator = data["labels_operator"]
    prompts = data["prompts"]
    scenario_ids = data["scenario_ids"] if "scenario_ids" in data.files else np.asarray(
        [f"scenario-{index + 1:04d}" for index in range(len(prompts))]
    )

    if features.ndim != 3:
        raise SystemExit(f"features must be [N, num_layers, hidden_dim]; got {features.shape}")
    n_samples, n_layers, hidden_dim = features.shape
    print(f"shape: N={n_samples}, layers={n_layers}, hidden_dim={hidden_dim}")

    # --- Construct 40-Element label = operator | domain ------------------
    forty_element = np.array(
        [f"{op}|{dom}" for op, dom in zip(labels_operator, labels_domain)]
    )
    unique_classes = sorted(set(forty_element.tolist()))
    class_distribution = {c: int((forty_element == c).sum()) for c in unique_classes}
    populated_cells = len(unique_classes)
    print(f"40-Element classes populated: {populated_cells}/40")
    sparse_cells = sum(1 for c in class_distribution.values() if c < args.min_samples_per_cell)
    print(f"  cells with <{args.min_samples_per_cell} samples: {sparse_cells}")

    readiness_gate = build_40e_readiness_gate(
        class_distribution,
        min_samples_per_cell=args.min_samples_per_cell,
    )
    if readiness_gate["blocking_reasons"]:
        print("40E packet readiness: BLOCKED")
        for reason in readiness_gate["blocking_reasons"]:
            print(f"  - {reason}")
    else:
        print("40E packet readiness: packet_ready")

    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    artifacts = [
        _artifact_descriptor(
            "activation_dataset_npz",
            "40e_activation_dataset_npz",
            args.dataset,
        ),
        _artifact_descriptor("metadata_json", "40e_capture_metadata_json", args.metadata),
    ]
    method_contract = {
        "readout": "StandardScaler + LogisticRegression",
        "class_weight": "balanced",
        "solver": "lbfgs",
        "probe_C": float(args.probe_C),
        "probe_max_iter": int(args.probe_max_iter),
        "split": "not evaluated in guard-only mode",
        "split_key": args.split_key,
        "test_split": args.test_split,
        "group_key": args.group_key,
        "seed": int(args.seed),
        "shuffled_trials": int(args.shuffled_trials),
        "min_samples_per_cell": int(args.min_samples_per_cell),
    }

    if args.require_balanced_40e and not readiness_gate["packet_ready"]:
        report = {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked_missing_balanced_40e_artifact",
            "created_at": datetime.now(UTC).isoformat(),
            "dataset": str(args.dataset),
            "metadata_path": str(args.metadata),
            "model_id": metadata.get("model_id"),
            "n_samples": int(n_samples),
            "n_layers": int(n_layers),
            "hidden_dim": int(hidden_dim),
            "axis": "40_element_operator_x_domain",
            "populated_cells": populated_cells,
            "total_cells": 40,
            "class_distribution": class_distribution,
            "readiness_gate": readiness_gate,
            "artifacts": artifacts,
            "method_contract": method_contract,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nwrote guard report: {args.output}")
        return 2

    # --- Group-aware split by base-prompt --------------------------------
    scenario_meta = _load_scenario_meta(args.scenario_path)
    base_groups = _groups_for_rows(
        prompts=prompts,
        scenario_ids=scenario_ids,
        scenario_meta=scenario_meta,
        group_key=args.group_key,
    )
    n_unique_groups = len(set(base_groups.tolist()))
    print(f"base-prompt groups: {n_unique_groups}")

    if args.scenario_path and args.split_key:
        train_idx, test_idx = _fixed_split_from_scenarios(
            scenario_ids=scenario_ids,
            scenario_meta=scenario_meta,
            split_key=args.split_key,
            test_split=args.test_split,
        )
        split_kind = f"fixed split by {args.split_key}; test_split={args.test_split}"
    else:
        gss = GroupShuffleSplit(n_splits=1, test_size=args.test_size, random_state=args.seed)
        train_idx, test_idx = next(gss.split(features, forty_element, groups=base_groups))
        split_kind = "GroupShuffleSplit by base-prompt (strips leading [...] framing tags)"
    method_contract["split"] = split_kind
    train_groups = set(base_groups[train_idx].tolist())
    test_groups = set(base_groups[test_idx].tolist())
    group_overlap = sorted(train_groups & test_groups)
    print(f"train={len(train_idx)}, test={len(test_idx)} ({split_kind})")
    print(f"train/test group overlap={len(group_overlap)}")

    y_train = forty_element[train_idx]
    y_test = forty_element[test_idx]

    # --- Per-layer hidden-state linear probe -----------------------------
    print("training per-layer probes...")
    per_layer_results = []
    for li in range(n_layers):
        X = features[:, li, :].astype(np.float32)
        X_train_l, X_test_l = X[train_idx], X[test_idx]
        try:
            acc, f1 = _fit_linear_probe(
                X_train_l, y_train, X_test_l, y_test, args.probe_C, args.probe_max_iter
            )
        except Exception as exc:
            print(f"  layer {int(layers[li])}: probe failed -> {exc}")
            acc, f1 = 0.0, 0.0
        per_layer_results.append(
            {
                "layer": int(layers[li]),
                "test_acc": acc,
                "test_macro_f1": f1,
            }
        )
        print(f"  layer {int(layers[li]):3d}: acc={acc*100:5.2f}%  macro_f1={f1*100:5.2f}%")

    best = max(per_layer_results, key=lambda r: r["test_acc"])
    best_layer_idx = per_layer_results.index(best)
    print(f"\nbest layer: {best['layer']} (acc={best['test_acc']*100:.2f}%)")

    # --- Control 1: majority class ---------------------------------------
    test_class_counts = {c: int((y_test == c).sum()) for c in unique_classes}
    most_common_in_train = max(class_distribution, key=class_distribution.get)
    majority_test_acc = float((y_test == most_common_in_train).mean())

    # --- Control 2: shuffled-label hidden-state probe (best layer) -------
    print(f"\nrunning {args.shuffled_trials} shuffled-label trials on best layer...")
    X_best = features[:, best_layer_idx, :].astype(np.float32)
    X_train_b, X_test_b = X_best[train_idx], X_best[test_idx]
    rng = np.random.default_rng(args.seed)
    shuffled_accs: list[float] = []
    for t in range(args.shuffled_trials):
        y_train_perm = rng.permutation(y_train)
        try:
            acc_s, _ = _fit_linear_probe(
                X_train_b, y_train_perm, X_test_b, y_test, args.probe_C, args.probe_max_iter
            )
        except Exception:
            acc_s = 0.0
        shuffled_accs.append(acc_s)
        print(f"  trial {t+1:2d}: acc={acc_s*100:.2f}%")
    shuffled_mean = float(np.mean(shuffled_accs))
    shuffled_std = float(np.std(shuffled_accs))
    shuffled_max = float(np.max(shuffled_accs))
    print(f"shuffled mean={shuffled_mean*100:.2f}% std={shuffled_std*100:.2f} max={shuffled_max*100:.2f}%")

    # --- Control 3: text-hash baseline (canonical English surface) -------
    print("\ntraining text-hash baseline...")
    vec = HashingVectorizer(n_features=2**14, ngram_range=(1, 2), alternate_sign=False)
    text_train_X = vec.transform([str(p) for p in prompts[train_idx]])
    text_test_X = vec.transform([str(p) for p in prompts[test_idx]])
    text_clf = LogisticRegression(
        C=1.0,
        max_iter=args.probe_max_iter,
        class_weight="balanced",
        solver="lbfgs",
        n_jobs=-1,
    )
    text_clf.fit(text_train_X, y_train)
    text_pred = text_clf.predict(text_test_X)
    text_acc = float(accuracy_score(y_test, text_pred))
    text_f1 = float(f1_score(y_test, text_pred, average="macro", zero_division=0))
    print(f"text-hash: acc={text_acc*100:.2f}%  macro_f1={text_f1*100:.2f}%")
    confirmed_text_baseline = _load_confirmed_text_baseline(args.confirmed_text_baseline_report)

    # --- Composite report -----------------------------------------------
    label_drop_minus_random_mean = best["test_acc"] - shuffled_mean

    report = {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "packet_ready_evaluation_completed"
            if readiness_gate["packet_ready"]
            else "diagnostic_completed_not_packet_ready"
        ),
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(args.dataset),
        "metadata_path": str(args.metadata),
        "model_id": metadata.get("model_id"),
        "artifacts": artifacts,
        "method_contract": method_contract,
        "n_samples": int(n_samples),
        "n_layers": int(n_layers),
        "hidden_dim": int(hidden_dim),
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "n_base_prompt_groups": int(n_unique_groups),
        "split": split_kind,
        "train_test_group_overlap_count": len(group_overlap),
        "train_test_group_overlap_examples": group_overlap[:10],
        "test_size": float(args.test_size),
        "axis": "40_element_operator_x_domain",
        "populated_cells": populated_cells,
        "total_cells": 40,
        "sparse_cells_lt_min_samples": sparse_cells,
        "class_distribution": class_distribution,
        "test_class_distribution": test_class_counts,
        "readiness_gate": readiness_gate,
        "best_layer": best,
        "per_layer": per_layer_results,
        "controls": {
            "majority_class_test_acc": majority_test_acc,
            "majority_class_label": most_common_in_train,
            "shuffled_label_hidden_best_layer": {
                "mean_test_acc": shuffled_mean,
                "std_test_acc": shuffled_std,
                "max_test_acc": shuffled_max,
                "trials": args.shuffled_trials,
                "all_trials": shuffled_accs,
            },
            "text_hash_baseline": {
                "test_acc": text_acc,
                "test_macro_f1": text_f1,
                "description": "HashingVectorizer(1-2 ngrams, 2^14 features) + LogisticRegression on prompt text",
            },
            "confirmed_text_baseline_report": confirmed_text_baseline,
        },
        "result_summary": {
            "hidden_probe_test_acc": best["test_acc"],
            "hidden_probe_minus_shuffled_mean_pp": label_drop_minus_random_mean * 100,
            "hidden_probe_exceeds_shuffled_max": best["test_acc"] > shuffled_max,
            "hidden_probe_beats_majority": best["test_acc"] > majority_test_acc,
            "hidden_probe_beats_text_baseline": best["test_acc"] > text_acc,
            "hidden_probe_beats_confirmed_text_baseline": (
                bool(best["test_acc"] > float(confirmed_text_baseline["test_acc"]))
                if confirmed_text_baseline and confirmed_text_baseline.get("test_acc") is not None
                else None
            ),
            "interpretation": (
                "Pythia-160M closure target on 40-Element: 89.8% readout, +39.7pp "
                "over text baseline. This run replicates the readout protocol on a "
                "different substrate using the dataset's operator + domain labels. "
                "When --confirmed-text-baseline-report is supplied, the result summary "
                "states whether hidden readout beats the exact-fixture text baseline."
            ),
        },
        "pythia_160m_comparator": {
            "axis": "40-Element (10 Noetics x 4 Domains)",
            "readout_test_acc": 0.898,
            "text_baseline_gap_pp": 39.7,
            "source": "CAS_HARNESS_SPEC_SHEET_v1_5_20260519_409e9efe",
        },
        "important_limit": (
            f"Dataset has {populated_cells}/40 cells populated, with {sparse_cells} "
            f"cells under the configured minimum of {args.min_samples_per_cell} samples. "
            "Sparse cells make probe claims undertrained. "
            f"{split_kind} was used; train/test group overlap is {len(group_overlap)}. "
            "Text-hash baseline measures whether prompt surface forms (which carry "
            "canonical CAS colloquialisms) encode the label. Canonical TKS English is "
            "valid framework language, but a high text-only score blocks the specific "
            "CAS-beats-surface-text claim until the fixture passes the baseline ceiling. "
            "Methodology minimum is 10 samples per cell; headline closure can be "
            "rerun with --min-samples-per-cell 25 for the stricter ~1000-scenario "
            "packet threshold."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(f"\nwrote report: {args.output}")

    # --- Headline summary printed last ----------------------------------
    print()
    print("=" * 64)
    print("40-ELEMENT READOUT HEADLINE")
    print("=" * 64)
    print(f"  Hidden probe (best layer={best['layer']:>3d}):  {best['test_acc']*100:6.2f}%")
    print(f"  Majority baseline:                {majority_test_acc*100:6.2f}%")
    print(f"  Shuffled-label control (mean):    {shuffled_mean*100:6.2f}%   (max {shuffled_max*100:.2f}, std {shuffled_std*100:.2f})")
    print(f"  Text-hash baseline:               {text_acc*100:6.2f}%")
    print(f"  Pythia-160M comparator:           {89.80:6.2f}%   (spec sheet v1.5)")
    print()
    print(f"  Probe above shuffled max:         {report['result_summary']['hidden_probe_exceeds_shuffled_max']}")
    print(f"  Probe above majority:             {report['result_summary']['hidden_probe_beats_majority']}")
    print(f"  Probe above text baseline:        {report['result_summary']['hidden_probe_beats_text_baseline']}")
    print(f"  Probe minus shuffled mean:        {label_drop_minus_random_mean*100:+6.2f} pp")
    print("=" * 64)

    return 0


if __name__ == "__main__":
    sys.exit(main())
