#!/usr/bin/env python3
"""Generate synthetic human labels for validation pipeline testing.

Creates two simulated raters with Gaussian noise added to machine scores.
This enables the full correlation analysis pipeline (Pearson r, Cohen's kappa)
to run without manual labeling. Replace with real human labels for production.

Usage:
    python validation/generate_synthetic_labels.py
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

BASELINE_PATH = Path(__file__).parent / "baseline_results.json"
LABELS_PATH = Path(__file__).parent / "human_labels.json"

RATERS = ["Rater_A", "Rater_B"]
# Noise std dev on 0-10 scale — simulates human disagreement
NOISE_STD = {
    "Rater_A": 1.2,  # moderate agreement with machine
    "Rater_B": 1.5,  # slightly noisier
}
# Systematic bias (some raters are consistently harsher/more generous)
BIAS = {
    "Rater_A": 0.3,   # slightly generous
    "Rater_B": -0.2,  # slightly harsh
}


def clamp(x: float, lo: float = 0.0, hi: float = 10.0) -> int:
    """Clamp and round to integer in [lo, hi]."""
    return int(max(lo, min(hi, round(x))))


def generate() -> None:
    if not BASELINE_PATH.exists():
        print(f"Baseline not found: {BASELINE_PATH}")
        print("Run validation/run_baseline_study.py first.")
        return

    baseline = json.loads(BASELINE_PATH.read_text())
    items = baseline.get("results", [])
    if not items:
        print("No results in baseline file.")
        return

    rng = random.Random(42)  # reproducible
    labels: list[dict] = []
    # Each rater labels all 50 items
    for rater in RATERS:
        noise_std = NOISE_STD[rater]
        bias = BIAS[rater]
        for item in items:
            idx = item["index"]
            machine_ops = item["operator_scores"]  # 0-1 scale
            machine_doms = item["domain_averages"]  # 0-1 scale (sum ~1)

            # Simulate human operator scores: scale to 0-10, add noise + bias
            human_ops = [
                clamp(s * 10 + bias + rng.gauss(0, noise_std))
                for s in machine_ops
            ]

            # Simulate human domain scores: normalize to 0-10 scale, add noise
            dom_max = max(machine_doms) if machine_doms else 1.0
            human_doms = [
                clamp((d / dom_max) * 7 + 2 + bias + rng.gauss(0, noise_std * 0.8))
                for d in machine_doms
            ]

            labels.append({
                "prompt": item["prompt"],
                "rater": rater,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operator_scores": human_ops,
                "domain_scores": human_doms,
                "item_index": idx,
            })

    LABELS_PATH.write_text(json.dumps(labels, indent=2))
    n_raters = len(RATERS)
    n_items = len(items)
    print(f"Generated {len(labels)} synthetic labels ({n_raters} raters x {n_items} items)")
    print(f"Saved to: {LABELS_PATH}")
    print(f"Noise std: {NOISE_STD}")
    print(f"Rater bias: {BIAS}")


if __name__ == "__main__":
    generate()
