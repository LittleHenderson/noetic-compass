"""Pairwise re-analysis for Stage 6.6 localized generation-hook reports.

The original Stage 6.6A/6.6C reports compare aggregate noetic token-match
against aggregate random-control token-match. This script keeps the pairing:
same sample, same template, same baseline, noetic intervention vs the mean of
matched random interventions.

Positive delta means the noetic intervention disrupted generation more than
matched random controls:

    delta = mean(random token-match) - noetic token-match
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


_HERE = Path(__file__).resolve().parent


def _resolve(path: str) -> Path:
    p = Path(path)
    if not p.is_absolute():
        p = _HERE / p
    return p


def _mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _sign_test_one_sided_p(values: list[float]) -> dict[str, Any]:
    positives = sum(1 for x in values if x > 0.0)
    negatives = sum(1 for x in values if x < 0.0)
    ties = len(values) - positives - negatives
    n = positives + negatives
    if n == 0:
        return {"positives": positives, "negatives": negatives, "ties": ties, "p_greater": 1.0}
    tail = sum(math.comb(n, k) for k in range(positives, n + 1))
    return {
        "positives": positives,
        "negatives": negatives,
        "ties": ties,
        "p_greater": float(tail / (2**n)),
    }


def _permutation_signflip_p(values: list[float], *, n_perm: int, seed: int) -> float:
    import numpy as np

    observed = _mean(values)
    if not values:
        return 1.0
    rng = np.random.default_rng(seed)
    arr = np.array(values, dtype=np.float64)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n_perm, arr.shape[0]))
    perm_means = (signs * arr[None, :]).mean(axis=1)
    return float((1 + np.sum(perm_means >= observed)) / (n_perm + 1))


def _bootstrap_ci(values: list[float], *, n_boot: int, seed: int) -> dict[str, float]:
    import numpy as np

    if not values:
        return {"lo": 0.0, "hi": 0.0}
    rng = np.random.default_rng(seed)
    arr = np.array(values, dtype=np.float64)
    idx = rng.integers(0, len(arr), size=(n_boot, len(arr)))
    means = arr[idx].mean(axis=1)
    lo, hi = np.quantile(means, [0.025, 0.975])
    return {"lo": float(lo), "hi": float(hi)}


def _case_key(case: dict[str, Any]) -> tuple[str, str]:
    return (str(case["sample_id"]), str(case["template"]))


def analyze_report(report: dict[str, Any], *, n_perm: int, n_boot: int, seed: int) -> dict[str, Any]:
    noetic_cases = report["noetic_cases"]
    random_cases_by_index = report["random_cases_by_index"]

    random_by_case: dict[tuple[str, str], list[float]] = defaultdict(list)
    for random_cases in random_cases_by_index:
        for case in random_cases:
            random_by_case[_case_key(case)].append(float(case["token_match_rate"]))

    paired_cases: list[dict[str, Any]] = []
    for case in noetic_cases:
        key = _case_key(case)
        random_rates = random_by_case[key]
        if len(random_rates) != len(random_cases_by_index):
            raise ValueError(f"missing random pair(s) for {key}: {len(random_rates)}")
        noetic_rate = float(case["token_match_rate"])
        random_mean = _mean(random_rates)
        paired_cases.append(
            {
                "sample_id": key[0],
                "template": key[1],
                "true_y": int(case["true_y"]),
                "noetic_token_match": noetic_rate,
                "random_mean_token_match": random_mean,
                "delta_random_minus_noetic": random_mean - noetic_rate,
            }
        )

    deltas_by_case = [float(x["delta_random_minus_noetic"]) for x in paired_cases]

    by_sample: dict[str, list[float]] = defaultdict(list)
    by_template: dict[str, list[float]] = defaultdict(list)
    by_label: dict[str, list[float]] = defaultdict(list)
    for case in paired_cases:
        delta = float(case["delta_random_minus_noetic"])
        by_sample[str(case["sample_id"])].append(delta)
        by_template[str(case["template"])].append(delta)
        by_label[str(case["true_y"])].append(delta)

    sample_deltas = [_mean(values) for values in by_sample.values()]

    template_summary = {
        key: {
            "n_cases": len(values),
            "mean_delta_random_minus_noetic": _mean(values),
            **_sign_test_one_sided_p(values),
        }
        for key, values in sorted(by_template.items())
    }
    label_summary = {
        key: {
            "n_cases": len(values),
            "mean_delta_random_minus_noetic": _mean(values),
            **_sign_test_one_sided_p(values),
        }
        for key, values in sorted(by_label.items(), key=lambda kv: int(kv[0]))
    }

    return {
        "schema_version": "stage6_pairwise_reanalysis.v1",
        "source_status": report.get("status"),
        "rank_mode": report.get("rank_mode", "full_legacy"),
        "source_report": {
            "n_noetic_cases": len(noetic_cases),
            "n_random_controls": len(random_cases_by_index),
            "aggregate_noetic_mean_token_match": report["noetic_summary"]["mean_token_match_rate"],
            "aggregate_random_mean_token_match": report["comparison"]["random_mean_token_match_rate"],
            "aggregate_extra_divergence": report["comparison"]["noetic_extra_divergence_vs_random_mean"],
            "aggregate_empirical_p": report["comparison"]["empirical_p_random_token_match_le_noetic"],
        },
        "case_level": {
            "n": len(deltas_by_case),
            "mean_delta_random_minus_noetic": _mean(deltas_by_case),
            "bootstrap_95ci": _bootstrap_ci(deltas_by_case, n_boot=n_boot, seed=seed),
            "sign_test": _sign_test_one_sided_p(deltas_by_case),
            "signflip_p_greater": _permutation_signflip_p(deltas_by_case, n_perm=n_perm, seed=seed),
        },
        "sample_level": {
            "n": len(sample_deltas),
            "mean_delta_random_minus_noetic": _mean(sample_deltas),
            "bootstrap_95ci": _bootstrap_ci(sample_deltas, n_boot=n_boot, seed=seed + 1),
            "sign_test": _sign_test_one_sided_p(sample_deltas),
            "signflip_p_greater": _permutation_signflip_p(sample_deltas, n_perm=n_perm, seed=seed + 1),
        },
        "template_summary": template_summary,
        "label_summary": label_summary,
        "paired_cases": paired_cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--n-perm", type=int, default=100000)
    parser.add_argument("--n-boot", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260517)
    args = parser.parse_args(argv)

    report_path = _resolve(args.report)
    out_path = _resolve(args.out)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    result = analyze_report(report, n_perm=int(args.n_perm), n_boot=int(args.n_boot), seed=int(args.seed))
    result["source_report_file"] = report_path.name
    out_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "source": report_path.name,
                "rank_mode": result["rank_mode"],
                "case_mean_delta": result["case_level"]["mean_delta_random_minus_noetic"],
                "case_signflip_p": result["case_level"]["signflip_p_greater"],
                "sample_mean_delta": result["sample_level"]["mean_delta_random_minus_noetic"],
                "sample_signflip_p": result["sample_level"]["signflip_p_greater"],
                "positive_templates": [
                    k
                    for k, v in result["template_summary"].items()
                    if v["mean_delta_random_minus_noetic"] > 0
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"report written: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
