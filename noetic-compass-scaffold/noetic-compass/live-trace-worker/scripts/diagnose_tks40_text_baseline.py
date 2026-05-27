#!/usr/bin/env python3
"""Diagnose whether a CAS scenario library is too easy for text baselines.

This script is intentionally separate from the hidden-state evaluator. It uses
an interpretable CountVectorizer, not HashingVectorizer, so the report can name
the phrases that let a text-only classifier recover the target label.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupShuffleSplit

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from probe_dataset_common import extract_labels  # noqa: E402


SCHEMA_VERSION = "cas_harness_text_baseline_diagnostic.v2"
PROMPT_KEYS = ("prompt", "prompt_text", "text", "english")


def _strip_framing_tags(prompt: str) -> str:
    s = str(prompt)
    while s.startswith("[") and "]" in s:
        s = s.split("]", 1)[1].lstrip()
    return s


def _load_items(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        items = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                if isinstance(item, dict):
                    items.append(item)
        return items

    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("scenarios", payload) if isinstance(payload, dict) else payload
    if not isinstance(raw, list):
        raise RuntimeError("Scenario file must be a JSONL file, a list, or contain a scenarios list.")
    return [item for item in raw if isinstance(item, dict)]


def _get_path_value(item: dict[str, Any], path: str | None) -> Any:
    if not path:
        return None
    current: Any = item
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _prompt_for_item(item: dict[str, Any]) -> str:
    for key in PROMPT_KEYS:
        value = item.get(key)
        if value is not None:
            prompt = str(value).strip()
            if prompt:
                return prompt
    return ""


def _label_for_item(item: dict[str, Any], label_key: str) -> str:
    labels = extract_labels(item)
    if label_key in labels:
        return labels[label_key]
    direct = _get_path_value(item, label_key)
    if direct is not None:
        label = str(direct).strip()
        if label:
            return label
    raise KeyError(f"item has no label for {label_key!r}")


def _sample_by_label(
    prompts: list[str],
    labels: list[str],
    *,
    per_label: int,
) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = defaultdict(list)
    for prompt, label in zip(prompts, labels):
        if len(buckets[label]) < per_label:
            buckets[label].append(prompt)
    return dict(sorted(buckets.items()))


def _top_features_per_class(
    clf: LogisticRegression,
    feature_names: np.ndarray,
    classes: np.ndarray,
    *,
    top_k: int,
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for row_index, class_label in enumerate(classes):
        coefs = clf.coef_[row_index]
        top_idx = np.argsort(coefs)[-top_k:][::-1]
        out[str(class_label)] = [
            {
                "feature": str(feature_names[i]),
                "weight": float(coefs[i]),
            }
            for i in top_idx
        ]
    return out


def diagnose(
    *,
    scenario_path: Path,
    output_path: Path,
    label_key: str = "element",
    axis_name: str | None = None,
    group_key: str | None = None,
    split_key: str | None = None,
    test_split: str = "test",
    test_size: float = 0.2,
    seed: int = 2026,
    top_k: int = 8,
    samples_per_label: int = 2,
) -> dict[str, Any]:
    items = _load_items(scenario_path)
    prompts: list[str] = []
    labels: list[str] = []
    groups: list[str] = []
    splits: list[str] = []
    for index, item in enumerate(items):
        prompt = _prompt_for_item(item)
        if not prompt:
            continue
        try:
            label = _label_for_item(item, label_key)
        except KeyError:
            continue
        prompts.append(prompt)
        labels.append(label)
        group_value = _get_path_value(item, group_key) if group_key else None
        groups.append(str(group_value or _strip_framing_tags(prompt)))
        split_value = _get_path_value(item, split_key) if split_key else None
        splits.append(str(split_value or ""))

    if not prompts:
        raise RuntimeError(f"No scenarios with prompt text and {label_key!r} labels found.")

    label_counts = dict(sorted(Counter(labels).items()))
    axis = axis_name or label_key

    groups = np.asarray(groups)
    y = np.asarray(labels)

    split_kind = "GroupShuffleSplit by stripped base prompt"
    if split_key and any(splits):
        split_arr = np.asarray(splits)
        test_idx = np.flatnonzero(split_arr == test_split)
        train_idx = np.flatnonzero((split_arr != test_split) & (split_arr != ""))
        if len(train_idx) == 0 or len(test_idx) == 0:
            raise RuntimeError(
                f"Split key {split_key!r} with test split {test_split!r} did not produce train/test rows."
            )
        split_kind = f"fixed split by {split_key}; test_split={test_split}"
    else:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
        train_idx, test_idx = next(splitter.split(np.asarray(prompts), y, groups=groups))

    train_groups = set(groups[train_idx].tolist())
    test_groups = set(groups[test_idx].tolist())
    group_overlap = sorted(train_groups & test_groups)

    vectorizer = CountVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=1,
        token_pattern=r"(?u)\b[\w'-]+\b",
    )
    X_train = vectorizer.fit_transform([prompts[i] for i in train_idx])
    X_test = vectorizer.transform([prompts[i] for i in test_idx])

    clf = LogisticRegression(
        C=1.0,
        max_iter=2000,
        class_weight="balanced",
        solver="lbfgs",
    )
    clf.fit(X_train, y[train_idx])
    train_pred = clf.predict(X_train)
    test_pred = clf.predict(X_test)

    feature_names = vectorizer.get_feature_names_out()
    top_features = _top_features_per_class(
        clf,
        feature_names,
        clf.classes_,
        top_k=top_k,
    )

    repeated_template_counts = Counter(
        prompt.split(". ", 1)[0].strip() for prompt in prompts if ". " in prompt
    )
    test_accuracy = float(accuracy_score(y[test_idx], test_pred))
    test_macro_f1 = float(f1_score(y[test_idx], test_pred, average="macro", zero_division=0))
    passes_text_ceiling = test_accuracy <= 0.60
    claim_gate_reason = (
        f"The text-only classifier stayed below the ceiling for {axis}. "
        "This scenario library can be used as a meaningful text-baseline adversary."
        if passes_text_ceiling
        else (
            f"A text-only classifier can recover the {axis} label too well. "
            "Do not claim hidden-state readout beats surface text until the "
            "scenario library is hardened and rerun."
        )
    )

    report = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "scenario_path": str(scenario_path),
        "axis": axis,
        "label_key": label_key,
        "n_scenarios": len(prompts),
        "n_classes": len(label_counts),
        "label_counts": label_counts,
        "split": {
            "kind": split_kind,
            "test_size": test_size,
            "seed": seed,
            "train_count": int(len(train_idx)),
            "test_count": int(len(test_idx)),
            "unique_groups": int(len(set(groups.tolist()))),
            "train_test_group_overlap_count": len(group_overlap),
            "train_test_group_overlap_examples": group_overlap[:10],
        },
        "text_baseline": {
            "model": "CountVectorizer(1-2 grams) + LogisticRegression(class_weight='balanced')",
            "train_accuracy": float(accuracy_score(y[train_idx], train_pred)),
            "test_accuracy": test_accuracy,
            "test_macro_f1": test_macro_f1,
            "n_features": int(len(feature_names)),
        },
        "claim_gate": {
            "cas_beats_text_claim_allowed": passes_text_ceiling,
            "target_text_baseline_ceiling": 0.60,
            "actual_text_baseline": test_accuracy,
            "status": (
                "blocked_text_baseline_too_high"
                if not passes_text_ceiling
                else "passes_text_baseline_ceiling"
            ),
            "reason": claim_gate_reason,
        },
        "top_predictive_features_per_class": top_features,
        "sample_prompts_per_class": _sample_by_label(
            prompts,
            labels,
            per_label=samples_per_label,
        ),
        "template_prefix_counts": dict(repeated_template_counts.most_common(20)),
        "interpretation": (
            "If test_accuracy is near 1.0, the scenario text is too lexically separable "
            "for a CAS-beats-text claim on this axis. Hidden-state readout can still be real, but "
            "the eval set is not a meaningful text adversary."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--label-key", default="element")
    parser.add_argument("--axis-name")
    parser.add_argument("--group-key")
    parser.add_argument("--split-key")
    parser.add_argument("--test-split", default="test")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--samples-per-label", type=int, default=2)
    args = parser.parse_args()

    report = diagnose(
        scenario_path=args.scenario,
        output_path=args.output,
        label_key=args.label_key,
        axis_name=args.axis_name,
        group_key=args.group_key,
        split_key=args.split_key,
        test_split=args.test_split,
        test_size=args.test_size,
        seed=args.seed,
        top_k=args.top_k,
        samples_per_label=args.samples_per_label,
    )
    baseline = report["text_baseline"]
    split = report["split"]
    print(f"wrote {args.output}")
    print(f"text baseline test accuracy: {baseline['test_accuracy'] * 100:.2f}%")
    print(f"text baseline macro-F1: {baseline['test_macro_f1'] * 100:.2f}%")
    print(f"train/test group overlap: {split['train_test_group_overlap_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
