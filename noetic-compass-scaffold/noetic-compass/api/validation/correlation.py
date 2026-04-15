"""Correlation computation for human validation study.

Computes:
- Pearson r per operator (human vs machine scores)
- Approximate two-tailed p-values via t-distribution
- 95% confidence intervals via Fisher z-transform
- Cohen's kappa for inter-rater reliability
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
import json
from statistics import mean

OPERATOR_NAMES = [
    "CO-0 Identity", "CO-1 Reflection", "CO-2 Abstraction",
    "CO-3 Concretization", "CO-4 Integration", "CO-5 Differentiation",
    "CO-6 Unification", "CO-7 Transformation", "CO-8 Expansion",
    "CO-9 Contraction",
]
DOMAIN_NAMES = ["Principled", "Cognitive", "Evaluative", "Operational"]

# Weak correlation threshold — operators below this are flagged for recalibration
WEAK_THRESHOLD = 0.4
STRONG_THRESHOLD = 0.7


def _clip_prompt(text: str, limit: int = 180) -> str:
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else f"{compact[:limit - 3]}..."


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via erf (Abramowitz & Stegun)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def pearson_r(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Compute Pearson correlation and approximate two-tailed p-value.

    Returns ``(r, p_value)``. If there are fewer than 3 paired observations
    or either series has zero variance, returns ``(0.0, 1.0)``.
    """
    n = len(xs)
    if n < 3:
        return 0.0, 1.0

    mx = sum(xs) / n
    my = sum(ys) / n
    sx_sq = sum((x - mx) ** 2 for x in xs)
    sy_sq = sum((y - my) ** 2 for y in ys)

    if sx_sq == 0 or sy_sq == 0:
        return 0.0, 1.0

    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    r = numerator / math.sqrt(sx_sq * sy_sq)
    r = max(-1.0, min(1.0, r))

    # Two-tailed p-value via t-distribution → normal approximation
    if abs(r) >= 1.0:
        return r, 0.0
    t_stat = r * math.sqrt((n - 2) / (1 - r * r))
    p = 2 * (1 - _norm_cdf(abs(t_stat)))
    return r, p


def confidence_interval(r: float, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """95% CI for Pearson r via Fisher z-transform."""
    if n < 4:
        return -1.0, 1.0
    if abs(r) >= 1.0:
        return r, r
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1 / math.sqrt(n - 3)
    z_crit = 1.96  # 95% CI
    lo = math.tanh(z - z_crit * se)
    hi = math.tanh(z + z_crit * se)
    return lo, hi


def cohens_kappa(a: list[int], b: list[int], k: int = 11) -> float:
    """Cohen's kappa for ordinal ratings on a 0-k scale (default 11 categories)."""
    n = len(a)
    if n == 0:
        return 0.0
    matrix = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        if 0 <= x < k and 0 <= y < k:
            matrix[x][y] += 1

    po = sum(matrix[i][i] for i in range(k)) / n
    row_sums = [sum(matrix[i]) for i in range(k)]
    col_sums = [sum(matrix[j][i] for j in range(k)) for i in range(k)]
    pe = sum(r * c for r, c in zip(row_sums, col_sums)) / (n * n)
    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def classify_strength(r: float) -> str:
    """Classify correlation strength: strong / moderate / weak."""
    if r >= STRONG_THRESHOLD:
        return "strong"
    if r >= WEAK_THRESHOLD:
        return "moderate"
    return "weak"


def compute_operator_correlations(
    labels: list[dict],
    machine_results: list[dict],
) -> list[dict]:
    """Compute Pearson r per CO.

    Scales machine operator scores (0-1) to 0-10 to match human scale
    before computing correlation.
    """
    # Build lookup: item_index -> machine scores (0-10 scale)
    machine_by_idx: dict[int, list[float]] = {}
    for item in machine_results:
        idx = item.get("index")
        scores = item.get("operator_scores", [])
        if idx is None or not scores:
            continue
        # Machine scores are 0-1; scale to 0-10 to match humans
        machine_by_idx[int(idx)] = [float(s) * 10.0 for s in scores]

    results: list[dict] = []
    for co_idx in range(10):
        machine_vals: list[float] = []
        human_vals: list[float] = []
        for label in labels:
            item_idx = label.get("item_index")
            if item_idx is None or int(item_idx) not in machine_by_idx:
                continue
            op_scores = label.get("operator_scores") or []
            if len(op_scores) <= co_idx:
                continue
            machine_vals.append(machine_by_idx[int(item_idx)][co_idx])
            human_vals.append(float(op_scores[co_idx]))

        r, p = pearson_r(machine_vals, human_vals)
        lo, hi = confidence_interval(r, len(machine_vals))
        human_mean = (sum(human_vals) / len(human_vals)) if human_vals else 0.0
        machine_mean = (sum(machine_vals) / len(machine_vals)) if machine_vals else 0.0

        results.append({
            "operator_index": co_idx,
            "operator_name": OPERATOR_NAMES[co_idx],
            "n_pairs": len(machine_vals),
            "human_mean": round(human_mean, 2),
            "machine_mean": round(machine_mean, 2),
            "pearson_r": round(r, 3),
            "p_value": round(p, 4),
            "ci_lower": round(lo, 3),
            "ci_upper": round(hi, 3),
            "strength": classify_strength(r),
            "scatter_points": [
                {"machine": m, "human": h}
                for m, h in zip(machine_vals, human_vals)
            ],
        })

    return results


def compute_inter_rater_kappa(labels: list[dict]) -> list[dict]:
    """Compute Cohen's kappa between every pair of raters on shared items."""
    by_rater: dict[str, dict[int, list[int]]] = defaultdict(dict)
    for label in labels:
        rater = label.get("rater", "unknown")
        idx = label.get("item_index")
        ops = label.get("operator_scores") or []
        if idx is None or not ops:
            continue
        by_rater[str(rater)][int(idx)] = [int(x) for x in ops]

    raters = sorted(by_rater.keys())
    results: list[dict] = []

    for i, r1 in enumerate(raters):
        for r2 in raters[i + 1:]:
            shared = sorted(set(by_rater[r1].keys()) & set(by_rater[r2].keys()))
            if not shared:
                continue
            per_op: list[float] = []
            for co_idx in range(10):
                a = [by_rater[r1][idx][co_idx] for idx in shared if len(by_rater[r1][idx]) > co_idx]
                b = [by_rater[r2][idx][co_idx] for idx in shared if len(by_rater[r2][idx]) > co_idx]
                if a and b:
                    per_op.append(cohens_kappa(a, b))
            avg_kappa = sum(per_op) / len(per_op) if per_op else 0.0
            # Agreement % = fraction of exact matches across all CO scores
            total = 0
            matches = 0
            for idx in shared:
                a = by_rater[r1][idx]
                b = by_rater[r2][idx]
                for x, y in zip(a, b):
                    total += 1
                    if x == y:
                        matches += 1
            agreement = (matches / total * 100) if total > 0 else 0.0

            results.append({
                "rater_a": r1,
                "rater_b": r2,
                "shared_items": len(shared),
                "cohens_kappa": round(avg_kappa, 3),
                "agreement_pct": round(agreement, 1),
            })

    return results


def generate_recommendations(operator_correlations: list[dict]) -> list[dict]:
    """Generate calibration recommendations based on correlation results."""
    recs: list[dict] = []
    for op in operator_correlations:
        name = op["operator_name"]
        r = op["pearson_r"]
        strength = op["strength"]
        n = op["n_pairs"]
        hm = op["human_mean"]
        mm = op["machine_mean"]

        if n < 10:
            recs.append({
                "operator": name,
                "severity": "info",
                "message": f"{name} has only {n} labeled items. Collect more data before drawing conclusions.",
            })
            continue

        if strength == "strong":
            recs.append({
                "operator": name,
                "severity": "ok",
                "message": f"{name} shows strong correlation (r={r}). No recalibration needed.",
            })
        elif strength == "moderate":
            recs.append({
                "operator": name,
                "severity": "warn",
                "message": f"{name} shows moderate correlation (r={r}). Review scoring rubric for edge cases.",
            })
        else:
            direction = "higher" if mm > hm else "lower"
            recs.append({
                "operator": name,
                "severity": "alert",
                "message": (
                    f"{name} shows weak correlation (r={r}). "
                    f"Machine consistently scores {direction} than humans "
                    f"(machine mean {mm}, human mean {hm}). "
                    f"Recommendation: review {name} feature extraction criteria "
                    f"and adjust the scoring rubric."
                ),
            })

    return recs


def compute_stats(labels: list[dict], machine_results: list[dict]) -> dict:
    """Compute headline statistics for the leaderboard."""
    total_labels = len(labels)
    raters = {label.get("rater", "unknown") for label in labels}

    # Items with at least 2 raters
    item_raters: dict[int, set[str]] = defaultdict(set)
    for label in labels:
        idx = label.get("item_index")
        if idx is None:
            continue
        item_raters[int(idx)].add(str(label.get("rater", "unknown")))
    multi_rated = sum(1 for rs in item_raters.values() if len(rs) >= 2)

    # Overall Pearson r (flatten all operator scores across all labels)
    machine_by_idx = {int(r.get("index", -1)): r.get("operator_scores", []) for r in machine_results}
    all_human: list[float] = []
    all_machine: list[float] = []
    for label in labels:
        idx = label.get("item_index")
        if idx is None or int(idx) not in machine_by_idx:
            continue
        m = machine_by_idx[int(idx)]
        h = label.get("operator_scores") or []
        for i in range(min(10, len(m), len(h))):
            all_machine.append(float(m[i]) * 10.0)
            all_human.append(float(h[i]))

    overall_r, overall_p = pearson_r(all_machine, all_human)

    # Overall kappa: average across rater pairs
    inter_rater = compute_inter_rater_kappa(labels)
    overall_kappa = (
        sum(ir["cohens_kappa"] for ir in inter_rater) / len(inter_rater)
        if inter_rater else 0.0
    )

    return {
        "total_labels": total_labels,
        "num_raters": len(raters),
        "items_multi_rated": multi_rated,
        "total_machine_items": len(machine_results),
        "overall_pearson_r": round(overall_r, 3),
        "overall_pearson_p": round(overall_p, 4),
        "overall_cohens_kappa": round(overall_kappa, 3),
    }


def compute_calibration_review(labels: list[dict], machine_results: list[dict]) -> dict:
    """Summarize rater bias and disagreement hot spots for calibration sessions."""
    if not labels:
        return {"raters": [], "operators": [], "items": []}

    machine_by_idx: dict[int, list[float]] = {}
    prompt_by_idx: dict[int, str] = {}
    for item in machine_results:
        idx = item.get("index")
        if idx is None:
            continue
        machine_by_idx[int(idx)] = [float(score) * 10.0 for score in item.get("operator_scores", [])[:10]]
        prompt_by_idx[int(idx)] = str(item.get("prompt", ""))

    labels_by_item: dict[int, list[dict]] = defaultdict(list)
    labels_by_rater: dict[str, list[dict]] = defaultdict(list)
    for label in labels:
        idx = label.get("item_index")
        if idx is None:
            continue
        labels_by_item[int(idx)].append(label)
        labels_by_rater[str(label.get("rater", "unknown"))].append(label)

    panel_means_by_item: dict[int, list[float]] = {}
    for idx, item_labels in labels_by_item.items():
        if not item_labels:
            continue
        panel_means_by_item[idx] = [
            mean(float(label.get("operator_scores", [0] * 10)[op_idx]) for label in item_labels)
            for op_idx in range(10)
        ]

    rater_rows: list[dict] = []
    for rater, rater_labels in sorted(labels_by_rater.items()):
        signed_panel_gaps: list[float] = []
        abs_panel_gaps: list[float] = []
        abs_machine_gaps: list[float] = []
        per_operator_signed: dict[int, list[float]] = defaultdict(list)

        for label in rater_labels:
            idx = int(label.get("item_index", -1))
            scores = [float(score) for score in label.get("operator_scores", [])[:10]]
            panel = panel_means_by_item.get(idx, [])
            machine = machine_by_idx.get(idx, [])
            for op_idx, score in enumerate(scores):
                if len(panel) > op_idx:
                    diff = score - panel[op_idx]
                    signed_panel_gaps.append(diff)
                    abs_panel_gaps.append(abs(diff))
                    per_operator_signed[op_idx].append(diff)
                if len(machine) > op_idx:
                    abs_machine_gaps.append(abs(score - machine[op_idx]))

        top_operator = None
        if per_operator_signed:
            op_idx, diffs = max(per_operator_signed.items(), key=lambda item: abs(mean(item[1])))
            top_operator = {
                "operator_index": op_idx,
                "operator_name": OPERATOR_NAMES[op_idx],
                "signed_gap": round(mean(diffs), 3),
            }

        rater_rows.append(
            {
                "rater": rater,
                "label_count": len(rater_labels),
                "item_count": len({int(label.get("item_index", -1)) for label in rater_labels}),
                "mean_panel_gap": round(mean(signed_panel_gaps), 3) if signed_panel_gaps else 0.0,
                "mean_abs_panel_gap": round(mean(abs_panel_gaps), 3) if abs_panel_gaps else 0.0,
                "mean_abs_machine_gap": round(mean(abs_machine_gaps), 3) if abs_machine_gaps else 0.0,
                "top_operator_drift": top_operator,
            }
        )

    operator_rows: list[dict] = []
    for op_idx in range(10):
        spreads: list[float] = []
        for idx, item_labels in labels_by_item.items():
            if len(item_labels) < 2:
                continue
            scores = [
                float(label.get("operator_scores", [0] * 10)[op_idx])
                for label in item_labels
                if len(label.get("operator_scores", [])) > op_idx
            ]
            if len(scores) < 2:
                continue
            spreads.append(max(scores) - min(scores))
        operator_rows.append(
            {
                "operator_index": op_idx,
                "operator_name": OPERATOR_NAMES[op_idx],
                "shared_items": len(spreads),
                "mean_spread": round(mean(spreads), 3) if spreads else 0.0,
                "max_spread": round(max(spreads), 3) if spreads else 0.0,
            }
        )

    operator_rows.sort(key=lambda row: (-row["mean_spread"], row["operator_index"]))

    item_rows: list[dict] = []
    for idx, item_labels in labels_by_item.items():
        if len(item_labels) < 2:
            continue
        operator_spreads: list[dict] = []
        for op_idx in range(10):
            scores = [
                float(label.get("operator_scores", [0] * 10)[op_idx])
                for label in item_labels
                if len(label.get("operator_scores", [])) > op_idx
            ]
            if len(scores) < 2:
                continue
            operator_spreads.append(
                {
                    "operator_index": op_idx,
                    "operator_name": OPERATOR_NAMES[op_idx],
                    "spread": round(max(scores) - min(scores), 3),
                    "panel_mean": round(mean(scores), 3),
                }
            )
        if not operator_spreads:
            continue
        operator_spreads.sort(key=lambda item: (-item["spread"], item["operator_index"]))
        machine_scores = machine_by_idx.get(idx, [])
        machine_mean = round(mean(machine_scores), 3) if machine_scores else None
        item_rows.append(
            {
                "item_index": idx,
                "prompt_excerpt": _clip_prompt(prompt_by_idx.get(idx, "")),
                "raters": sorted({str(label.get("rater", "unknown")) for label in item_labels}),
                "label_count": len(item_labels),
                "largest_operator_gap": operator_spreads[0],
                "mean_spread": round(mean(item["spread"] for item in operator_spreads), 3),
                "machine_mean": machine_mean,
                "panel_mean": round(
                    mean(
                        score
                        for label in item_labels
                        for score in [float(value) for value in label.get("operator_scores", [])[:10]]
                    ),
                    3,
                ),
            }
        )
    item_rows.sort(
        key=lambda row: (
            -(row["largest_operator_gap"]["spread"]),
            -(row["mean_spread"]),
            row["item_index"],
        )
    )

    return {
        "raters": rater_rows,
        "operators": operator_rows,
        "items": item_rows[:25],
    }


def load_labels(path: Path | str = None) -> list[dict]:
    """Load human labels from JSON file."""
    p = Path(path) if path else Path(__file__).resolve().parent.parent.parent / "validation" / "human_labels.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return data
        return []
    except (json.JSONDecodeError, OSError):
        return []


def load_machine_results(path: Path | str = None) -> list[dict]:
    """Load machine baseline results from JSON file."""
    p = Path(path) if path else Path(__file__).resolve().parent.parent.parent / "validation" / "baseline_results.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text())
        return data.get("results", []) if isinstance(data, dict) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_labels(labels: list[dict], path: Path | str = None) -> None:
    """Save human labels to JSON file."""
    p = Path(path) if path else Path(__file__).resolve().parent.parent.parent / "validation" / "human_labels.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(labels, indent=2))
