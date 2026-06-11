"""Evaluate behavior readout only inside payload classes.

This is the honesty check for comply/refuse probes: a strong global score is
not enough if COMPLIED and REFUSED mostly come from different payload classes.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    from scripts.evaluate_probe_dataset import evaluate_axis
except ModuleNotFoundError:  # pragma: no cover - exercised by direct script execution
    from evaluate_probe_dataset import evaluate_axis


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--text-dim", type=int, default=4096)
    parser.add_argument("--cover-top-k", type=int, default=16)
    parser.add_argument("--min-class-count", type=int, default=3)
    parser.add_argument("--min-testable-payload-classes", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = evaluate_behavior_within_payload(
        dataset_path=args.dataset,
        seed=args.seed,
        text_dim=args.text_dim,
        cover_top_k=args.cover_top_k,
        min_class_count=args.min_class_count,
        min_testable_payload_classes=args.min_testable_payload_classes,
    )
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "testable_payload_classes": report["testable_payload_class_count"],
        "claim_ceiling": report["claim_ceiling"],
    }, indent=2, sort_keys=True))
    print(f"[within-payload] wrote {args.output_report}")
    return 0


def evaluate_behavior_within_payload(
    *,
    dataset_path: Path,
    seed: int,
    text_dim: int,
    cover_top_k: int,
    min_class_count: int,
    min_testable_payload_classes: int,
) -> dict[str, Any]:
    with np.load(dataset_path, allow_pickle=True) as data:
        features = data["features"].astype(np.float32)
        layers = data["layers"].astype(int)
        prompts = np.asarray(data["prompts"], dtype=object).astype(str)
        scenario_ids = np.asarray(data["scenario_ids"], dtype=str)
        behavior = np.asarray(data["labels_behavior"], dtype=str)
        payload_class = np.asarray(data["labels_payload_class"], dtype=str)

    payload_counts: dict[str, dict[str, int]] = {}
    evaluations: dict[str, Any] = {}
    skipped: dict[str, Any] = {}
    for payload in sorted(set(payload_class.tolist())):
        mask = payload_class == payload
        counts = Counter(behavior[mask].tolist())
        payload_counts[payload or ""] = dict(sorted(counts.items()))
        usable = all(counts.get(label, 0) >= min_class_count for label in ("COMPLIED", "REFUSED"))
        if not usable:
            skipped[payload or ""] = {
                "reason": f"Need COMPLIED and REFUSED each >= {min_class_count}.",
                "class_distribution": dict(sorted(counts.items())),
            }
            continue
        axis_report, _covers = evaluate_axis(
            axis="behavior",
            labels=behavior[mask],
            features=features[mask],
            layers=layers,
            prompts=prompts[mask],
            scenario_ids=scenario_ids[mask],
            seed=seed,
            text_dim=text_dim,
            cover_top_k=cover_top_k,
            min_class_count=min_class_count,
        )
        evaluations[payload or ""] = axis_report

    testable_count = len(evaluations)
    if testable_count < min_testable_payload_classes:
        status = "blocked_insufficient_within_payload_n"
        claim_ceiling = (
            "OPEN. Global behavior separation may be payload-confounded; there are "
            "not enough payload classes with both COMPLIED and REFUSED examples."
        )
    else:
        status = "evaluated_within_payload_diagnostic"
        claim_ceiling = (
            "DIAGNOSTIC ONLY. Per-payload readouts can be inspected, but causal or "
            "payload-independent claims still require matched controls and intervention."
        )

    return {
        "schema_version": "cas_harness_behavior_within_payload_eval.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": str(dataset_path),
        "status": status,
        "claim_ceiling": claim_ceiling,
        "min_class_count": int(min_class_count),
        "min_testable_payload_classes": int(min_testable_payload_classes),
        "overall_behavior_distribution": dict(sorted(Counter(behavior.tolist()).items())),
        "payload_class_distribution": payload_counts,
        "testable_payload_class_count": int(testable_count),
        "evaluations": evaluations,
        "skipped": skipped,
        "important_limit": (
            "This report controls payload class by evaluating COMPLIED-vs-REFUSED "
            "inside each payload class. It is not a live forward-pass intervention."
        ),
    }


if __name__ == "__main__":
    raise SystemExit(main())
