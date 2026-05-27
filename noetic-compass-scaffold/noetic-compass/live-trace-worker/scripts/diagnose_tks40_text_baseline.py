#!/usr/bin/env python3
"""Diagnose whether a TKS40 scenario library is too easy for text baselines.

This script is intentionally separate from the hidden-state evaluator. It uses
an interpretable CountVectorizer, not HashingVectorizer, so the report can name
the phrases that let a text-only classifier recover the 40-Element label.
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

from probe_dataset_common import load_labeled_scenarios  # noqa: E402


SCHEMA_VERSION = "cas_harness_tks40_text_baseline_diagnostic.v1"


def _strip_framing_tags(prompt: str) -> str:
    s = str(prompt)
    while s.startswith("[") and "]" in s:
        s = s.split("]", 1)[1].lstrip()
    return s


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
    test_size: float = 0.2,
    seed: int = 2026,
    top_k: int = 8,
    samples_per_label: int = 2,
) -> dict[str, Any]:
    scenarios = load_labeled_scenarios(scenario_path)
    prompts = [scenario.prompt for scenario in scenarios]
    labels = [scenario.labels["element"] for scenario in scenarios]
    label_counts = dict(sorted(Counter(labels).items()))

    groups = np.asarray([_strip_framing_tags(prompt) for prompt in prompts])
    y = np.asarray(labels)

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

    report = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "scenario_path": str(scenario_path),
        "axis": "40_element_operator_x_domain",
        "n_scenarios": len(scenarios),
        "n_classes": len(label_counts),
        "label_counts": label_counts,
        "split": {
            "kind": "GroupShuffleSplit by stripped base prompt",
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
            "cas_beats_text_claim_allowed": test_accuracy <= 0.60,
            "target_text_baseline_ceiling": 0.60,
            "actual_text_baseline": test_accuracy,
            "status": (
                "blocked_text_baseline_too_high"
                if test_accuracy > 0.60
                else "passes_text_baseline_ceiling"
            ),
            "reason": (
                "A text-only classifier can recover the TKS40 label too well. "
                "Do not claim hidden-state readout beats surface text until the "
                "scenario library is hardened and rerun."
            ),
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
            "for a CAS-beats-text claim. Hidden-state readout can still be real, but "
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
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--samples-per-label", type=int, default=2)
    args = parser.parse_args()

    report = diagnose(
        scenario_path=args.scenario,
        output_path=args.output,
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
