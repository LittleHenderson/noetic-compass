#!/usr/bin/env python3
"""Diagnose text-only leakage for a Stage MTC fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score


SCHEMA_VERSION = "cas_harness_mtc_fixture_text_baseline.v1"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if isinstance(payload, dict):
        for key in ("records", "scenarios", "rows", "items", "samples"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    raise SystemExit("fixture JSON does not contain records/scenarios/rows")


def _row_id(row: dict[str, Any], index: int) -> str:
    return str(row.get("sample_id") or row.get("id") or index)


def _split_masks(rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    train: list[int] = []
    test: list[int] = []
    for index, row in enumerate(rows):
        split = str(row.get("split") or row.get("metadata", {}).get("split") or "").lower()
        if split in {"train", "training"}:
            train.append(index)
        elif split in {"test", "heldout", "holdout", "eval", "validation", "val", "dev"}:
            test.append(index)
        else:
            raise SystemExit(f"row {index} has unsupported split {split!r}")
    if not train or not test:
        raise SystemExit("fixture must contain both train and test rows")
    return np.array(train, dtype=int), np.array(test, dtype=int)


def _cas_labels(rows: list[dict[str, Any]], axis: str) -> list[str]:
    labels: list[str] = []
    for row in rows:
        if axis == "40e":
            label = row.get("labels_40e")
            if not label:
                op = row.get("labels_operator") or row.get("expected_cas_axes", {}).get("operator")
                dom = row.get("labels_domain") or row.get("expected_cas_axes", {}).get("domain")
                label = f"{op}|{dom}" if op and dom else None
        else:
            label = row.get("labels_f28")
            if not label:
                drive = row.get("drive") or row.get("expected_cas_axes", {}).get("drive")
                register = row.get("register") or row.get("expected_cas_axes", {}).get("register")
                label = f"{drive}|{register}" if drive and register else None
        if not label:
            raise SystemExit(f"missing CAS label for axis {axis}")
        labels.append(str(label))
    return labels


def _assignment_labels(rows: list[dict[str, Any]], assignments: Any, axis: str) -> dict[str, list[str]]:
    if not assignments:
        return {}
    taxonomies = assignments.get("taxonomies") if isinstance(assignments, dict) else None
    if not isinstance(taxonomies, list):
        return {}

    ids = [_row_id(row, index) for index, row in enumerate(rows)]
    result: dict[str, list[str]] = {}
    for taxonomy in taxonomies:
        if not isinstance(taxonomy, dict) or taxonomy.get("axis") != axis:
            continue
        raw_labels = taxonomy.get("labels")
        if isinstance(raw_labels, list):
            if len(raw_labels) != len(rows):
                raise SystemExit(f"taxonomy {taxonomy.get('id')} label count does not match row count")
            labels = [str(value) for value in raw_labels]
        elif isinstance(raw_labels, dict):
            missing = [sample_id for sample_id in ids if sample_id not in raw_labels]
            if missing:
                raise SystemExit(
                    f"taxonomy {taxonomy.get('id')} labels missing sample ids: {missing[:5]}"
                )
            labels = [str(raw_labels[sample_id]) for sample_id in ids]
        else:
            continue
        result[str(taxonomy.get("id") or taxonomy.get("taxonomy_id") or "control")] = labels
    return result


def _score_text_baseline(
    prompts: list[str],
    labels: list[str],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    *,
    max_features: int,
    max_iter: int,
) -> dict[str, Any]:
    vectorizer = CountVectorizer(ngram_range=(1, 2), max_features=max_features)
    X_train = vectorizer.fit_transform([prompts[index] for index in train_idx])
    X_test = vectorizer.transform([prompts[index] for index in test_idx])
    y = np.array(labels, dtype=object)

    clf = LogisticRegression(
        C=1.0,
        max_iter=max_iter,
        class_weight="balanced",
        solver="lbfgs",
        n_jobs=-1,
    )
    clf.fit(X_train, y[train_idx])
    pred = clf.predict(X_test)
    acc = float(accuracy_score(y[test_idx], pred))
    macro_f1 = float(f1_score(y[test_idx], pred, average="macro", zero_division=0))
    class_count = len(set(labels))
    return {
        "class_count": class_count,
        "chance_accuracy": 1.0 / class_count if class_count else None,
        "test_accuracy": acc,
        "test_macro_f1": macro_f1,
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "vectorizer": "CountVectorizer(1-2 grams)",
        "max_features": int(max_features),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--axis", required=True, choices=("40e", "f28"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--assignments", type=Path)
    parser.add_argument("--max-features", type=int, default=2**14)
    parser.add_argument("--max-iter", type=int, default=1000)
    args = parser.parse_args()

    fixture = _load_json(args.fixture)
    rows = _records(fixture)
    assignments = _load_json(args.assignments) if args.assignments else None
    prompts = [str(row.get("prompt", "")) for row in rows]
    train_idx, test_idx = _split_masks(rows)

    label_sets = {f"cas_{args.axis}": _cas_labels(rows, args.axis)}
    label_sets.update(_assignment_labels(rows, assignments, args.axis))

    reports = {
        name: _score_text_baseline(
            prompts,
            labels,
            train_idx,
            test_idx,
            max_features=args.max_features,
            max_iter=args.max_iter,
        )
        for name, labels in label_sets.items()
    }
    max_text_acc = max(report["test_accuracy"] for report in reports.values())
    payload = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "completed",
        "axis": args.axis,
        "fixture": str(args.fixture),
        "fixture_sha256": _sha256_file(args.fixture),
        "assignments": str(args.assignments) if args.assignments else None,
        "assignments_sha256": _sha256_file(args.assignments) if args.assignments else None,
        "row_count": len(rows),
        "max_text_baseline_accuracy": max_text_acc,
        "warning": (
            "High text baseline means the prompt surface can predict at least one label set; "
            "rewrite before claim-bearing activation capture if this exceeds the preregistered ceiling."
        ),
        "label_set_reports": reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote MTC text-baseline diagnostic: {args.output}")
    for name, report in reports.items():
        print(f"{name}: {report['test_accuracy'] * 100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
