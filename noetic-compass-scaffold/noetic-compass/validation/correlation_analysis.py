#!/usr/bin/env python3
"""Correlation analysis between CAS machine scores and human labels.

Computes:
- Pearson correlation per Cognitive Operator (machine vs human)
- Inter-rater reliability (Cohen's kappa) if multiple raters exist
- Test-retest reliability from reproducibility data
- Summary report with 95% confidence intervals

Usage:
    python validation/correlation_analysis.py
    python validation/correlation_analysis.py --baseline validation/baseline_results.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

OPERATOR_NAMES = [
    "CO-0 Identity", "CO-1 Reflection", "CO-2 Abstraction",
    "CO-3 Concretization", "CO-4 Integration", "CO-5 Differentiation",
    "CO-6 Unification", "CO-7 Transformation", "CO-8 Expansion",
    "CO-9 Contraction",
]

DOMAIN_NAMES = ["Principled", "Cognitive", "Evaluative", "Operational"]


def pearson_r(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Compute Pearson correlation and p-value approximation.

    Returns (r, p_value). Uses t-distribution approximation for p.
    """
    n = len(xs)
    if n < 3:
        return 0.0, 1.0

    mx = sum(xs) / n
    my = sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs) / (n - 1)) if n > 1 else 0
    sy = math.sqrt(sum((y - my) ** 2 for y in ys) / (n - 1)) if n > 1 else 0

    if sx == 0 or sy == 0:
        return 0.0, 1.0

    r = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / ((n - 1) * sx * sy)
    r = max(-1.0, min(1.0, r))

    # t-statistic approximation for p-value
    if abs(r) >= 1.0:
        p = 0.0
    else:
        t_stat = r * math.sqrt((n - 2) / (1 - r * r))
        # Rough two-tailed p-value via normal approximation for large n
        p = 2 * (1 - _norm_cdf(abs(t_stat)))

    return r, p


def _norm_cdf(x: float) -> float:
    """Standard normal CDF approximation (Abramowitz & Stegun)."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def confidence_interval_r(r: float, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Fisher z-transform 95% CI for Pearson r."""
    if n < 4:
        return -1.0, 1.0
    z = 0.5 * math.log((1 + r) / max(1e-10, 1 - r))
    se = 1 / math.sqrt(n - 3)
    z_crit = 1.96  # 95% CI
    lo = math.tanh(z - z_crit * se)
    hi = math.tanh(z + z_crit * se)
    return lo, hi


def cohens_kappa(ratings_a: list[int], ratings_b: list[int], k: int = 11) -> float:
    """Cohen's kappa for ordinal ratings (0-10 scale, k=11 categories)."""
    n = len(ratings_a)
    if n == 0:
        return 0.0

    # Build confusion matrix
    matrix = [[0] * k for _ in range(k)]
    for a, b in zip(ratings_a, ratings_b):
        matrix[a][b] += 1

    # Observed agreement
    po = sum(matrix[i][i] for i in range(k)) / n

    # Expected agreement
    row_sums = [sum(matrix[i]) for i in range(k)]
    col_sums = [sum(matrix[j][i] for j in range(k)) for i in range(k)]
    pe = sum(r * c for r, c in zip(row_sums, col_sums)) / (n * n)

    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def analyze(
    baseline_path: Path,
    labels_path: Path,
    repro_path: Path | None = None,
) -> str:
    """Run full correlation analysis and return formatted report."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("CAS VALIDATION — CORRELATION ANALYSIS REPORT")
    lines.append("=" * 70)

    # Load data
    if not baseline_path.exists():
        return f"Baseline results not found: {baseline_path}"
    baseline = json.loads(baseline_path.read_text())
    machine_results = baseline.get("results", [])

    has_labels = labels_path.exists()
    labels: list[dict] = []
    if has_labels:
        labels = json.loads(labels_path.read_text())

    lines.append(f"\nMachine results: {len(machine_results)} assessments")
    lines.append(f"Human labels:    {len(labels)} ratings")

    # -- Section 1: Machine-Human Correlation --
    if labels:
        lines.append(f"\n{'-'*50}")
        lines.append("SECTION 1: MACHINE vs HUMAN CORRELATION (per CO)")
        lines.append(f"{'-'*50}")

        # Build per-item lookup: item_index -> machine scores
        machine_by_idx: dict[int, list[float]] = {}
        for item in machine_results:
            idx = item.get("index", -1)
            scores = item.get("operator_scores", [])
            if scores and idx >= 0:
                machine_by_idx[idx] = [s * 10 for s in scores]  # Scale 0-1 to 0-10

        # Match human labels to machine scores
        for co_idx in range(10):
            machine_vals: list[float] = []
            human_vals: list[float] = []
            for label in labels:
                item_idx = label.get("item_index", -1)
                if item_idx in machine_by_idx and len(label.get("operator_scores", [])) > co_idx:
                    machine_vals.append(machine_by_idx[item_idx][co_idx])
                    human_vals.append(float(label["operator_scores"][co_idx]))

            if len(machine_vals) >= 3:
                r, p = pearson_r(machine_vals, human_vals)
                lo, hi = confidence_interval_r(r, len(machine_vals))
                sig = "*" if p < 0.05 else ""
                lines.append(
                    f"  {OPERATOR_NAMES[co_idx]:25s}  r={r:+.3f}  "
                    f"95%CI=[{lo:+.3f}, {hi:+.3f}]  p={p:.4f} {sig}"
                )
            else:
                lines.append(f"  {OPERATOR_NAMES[co_idx]:25s}  (insufficient data: {len(machine_vals)} pairs)")

        # -- Section 2: Inter-Rater Reliability --
        raters = defaultdict(list)
        for label in labels:
            raters[label.get("rater", "unknown")].append(label)

        if len(raters) >= 2:
            lines.append(f"\n{'-'*50}")
            lines.append("SECTION 2: INTER-RATER RELIABILITY (Cohen's kappa)")
            lines.append(f"{'-'*50}")

            rater_names = sorted(raters.keys())
            for i, r1 in enumerate(rater_names):
                for r2 in rater_names[i + 1:]:
                    # Find overlapping items
                    items_r1 = {l["item_index"]: l for l in raters[r1] if "item_index" in l}
                    items_r2 = {l["item_index"]: l for l in raters[r2] if "item_index" in l}
                    overlap = sorted(set(items_r1) & set(items_r2))

                    if overlap:
                        lines.append(f"\n  Raters: {r1} vs {r2} ({len(overlap)} overlapping items)")
                        for co_idx in range(10):
                            a = [items_r1[idx]["operator_scores"][co_idx] for idx in overlap]
                            b = [items_r2[idx]["operator_scores"][co_idx] for idx in overlap]
                            k = cohens_kappa(a, b)
                            strength = (
                                "excellent" if k > 0.8 else "good" if k > 0.6
                                else "moderate" if k > 0.4 else "fair" if k > 0.2 else "poor"
                            )
                            lines.append(f"    {OPERATOR_NAMES[co_idx]:25s}  kappa={k:.3f} ({strength})")
        else:
            lines.append(f"\n  Inter-rater: only {len(raters)} rater(s) — need >=2 for kappa")

    else:
        lines.append("\n  No human labels found. Run human_labeling_tool.py first.")

    # -- Section 3: Test-Retest Reliability --
    lines.append(f"\n{'-'*50}")
    lines.append("SECTION 3: TEST-RETEST RELIABILITY")
    lines.append(f"{'-'*50}")

    if repro_path and repro_path.exists():
        repro = json.loads(repro_path.read_text())
        runs = repro.get("runs", [])
        if len(runs) >= 2:
            # Compare first vs last run
            first_scores = runs[0].get("operator_scores", [])
            last_scores = runs[-1].get("operator_scores", [])
            if first_scores and last_scores:
                r, p = pearson_r(first_scores, last_scores)
                lines.append(f"  Run 1 vs Run {len(runs)}: r={r:+.3f}, p={p:.4f}")
                if r > 0.99:
                    lines.append("  Deterministic mock connector: perfect test-retest (expected)")
                else:
                    lines.append(f"  Test-retest correlation: {r:.3f}")
        else:
            lines.append("  Insufficient reproducibility runs.")
    else:
        lines.append("  No reproducibility data file provided.")

    # -- Section 4: Summary Statistics --
    if machine_results:
        lines.append(f"\n{'-'*50}")
        lines.append("SECTION 4: MACHINE SCORE SUMMARY STATISTICS")
        lines.append(f"{'-'*50}")

        composites = [r.get("composite", 0) for r in machine_results if "composite" in r]
        if composites:
            avg = sum(composites) / len(composites)
            std = math.sqrt(sum((c - avg) ** 2 for c in composites) / max(1, len(composites) - 1))
            lines.append(f"  Composite: mean={avg:.1f}, std={std:.1f}, min={min(composites):.1f}, max={max(composites):.1f}")

        certs = defaultdict(int)
        for r in machine_results:
            certs[r.get("certification", "unknown")] += 1
        lines.append(f"  Certifications: {dict(certs)}")

    lines.append(f"\n{'='*70}")
    lines.append("END OF REPORT")
    lines.append(f"{'='*70}\n")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="CAS correlation analysis")
    parser.add_argument("--baseline", default="validation/baseline_results.json")
    parser.add_argument("--labels", default="validation/human_labels.json")
    parser.add_argument("--reproducibility", default=None)
    parser.add_argument("--output", default=None, help="Save report to file")
    args = parser.parse_args()

    report = analyze(
        Path(args.baseline),
        Path(args.labels),
        Path(args.reproducibility) if args.reproducibility else None,
    )

    print(report)
    if args.output:
        Path(args.output).write_text(report)
        print(f"Report saved to {args.output}")


if __name__ == "__main__":
    main()
