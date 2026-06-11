"""v5 paired causal analysis for comply/refuse steering runs.

Input rows are JSONL with at least:
  prompt_id, seed, condition, label

Supported condition aliases:
  no_op / noop / baseline
  +refusal / plus_refusal / refusal_plus
  -refusal / minus_refusal / refusal_minus
  random / random_same_norm

The primary estimand is the per-prompt paired REFUSED probability shift:
`+refusal` minus no-op.
"""

from __future__ import annotations

from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import numpy as np


CONDITION_ALIASES = {
    "no_op": "no_op",
    "noop": "no_op",
    "baseline": "no_op",
    "+refusal": "plus_refusal",
    "plus_refusal": "plus_refusal",
    "refusal_plus": "plus_refusal",
    "-refusal": "minus_refusal",
    "minus_refusal": "minus_refusal",
    "refusal_minus": "minus_refusal",
    "random": "random_same_norm",
    "random_same_norm": "random_same_norm",
}
REQUIRED_CONDITIONS = ("no_op", "plus_refusal", "minus_refusal", "random_same_norm")


def parse_args() -> Any:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--results-jsonl", required=True, type=Path)
    parser.add_argument("--output-report", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--permutations", type=int, default=10000)
    parser.add_argument("--bootstrap", type=int, default=5000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = read_rows(args.results_jsonl)
    report = analyze_causal_rows(
        rows,
        source_path=args.results_jsonl,
        seed=args.seed,
        permutations=args.permutations,
        bootstrap=args.bootstrap,
    )
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "claim": report["claim"],
                "plus_refusal_shift": report["metrics"].get("plus_refusal_refused_shift"),
                "sign_flip_p": report["metrics"].get("plus_refusal_sign_flip_p"),
                "ci_low": report["metrics"].get("plus_refusal_bootstrap_ci95", [None])[0],
            },
            indent=2,
            sort_keys=True,
        )
    )
    print(f"[v5-causal] wrote {args.output_report}")
    return 0


def analyze_causal_rows(
    rows: list[dict[str, Any]],
    *,
    source_path: Path | None,
    seed: int,
    permutations: int,
    bootstrap: int,
) -> dict[str, Any]:
    normalized, rejected = normalize_rows(rows)
    cells = build_prompt_condition_rates(normalized)
    complete_prompt_ids = sorted(
        prompt_id
        for prompt_id, by_condition in cells.items()
        if all(condition in by_condition for condition in REQUIRED_CONDITIONS)
    )
    if not complete_prompt_ids:
        return blocked_report(source_path, normalized, rejected, "no_complete_prompt_condition_blocks")

    no_op = np.asarray([cells[prompt]["no_op"]["REFUSED"] for prompt in complete_prompt_ids], dtype=np.float32)
    plus = np.asarray([cells[prompt]["plus_refusal"]["REFUSED"] for prompt in complete_prompt_ids], dtype=np.float32)
    minus = np.asarray([cells[prompt]["minus_refusal"]["REFUSED"] for prompt in complete_prompt_ids], dtype=np.float32)
    random = np.asarray([cells[prompt]["random_same_norm"]["REFUSED"] for prompt in complete_prompt_ids], dtype=np.float32)
    ignored_no_op = np.asarray([cells[prompt]["no_op"]["IGNORED"] for prompt in complete_prompt_ids], dtype=np.float32)
    ignored_plus = np.asarray([cells[prompt]["plus_refusal"]["IGNORED"] for prompt in complete_prompt_ids], dtype=np.float32)
    malformed_no_op = np.asarray([cells[prompt]["no_op"]["MALFORMED"] for prompt in complete_prompt_ids], dtype=np.float32)
    malformed_plus = np.asarray([cells[prompt]["plus_refusal"]["MALFORMED"] for prompt in complete_prompt_ids], dtype=np.float32)

    plus_delta = plus - no_op
    minus_delta = minus - no_op
    random_delta = random - no_op
    plus_shift = float(plus_delta.mean())
    minus_shift = float(minus_delta.mean())
    random_shift = float(random_delta.mean())
    sign_p = sign_flip_p_value(plus_delta, seed=seed, permutations=permutations)
    ci_low, ci_high = bootstrap_ci(plus_delta, seed=seed, rounds=bootstrap)
    ignored_shift = float((ignored_plus - ignored_no_op).mean())
    malformed_shift = float((malformed_plus - malformed_no_op).mean())

    gates = {
        "plus_refusal_shift_pass": plus_shift >= 0.20,
        "plus_refusal_sign_flip_p_pass": sign_p < 0.001,
        "plus_refusal_ci_low_pass": ci_low > 0.10,
        "plus_beats_random_pass": plus_shift - random_shift >= 0.15,
        "random_abs_shift_pass": abs(random_shift) <= 0.05,
        "minus_opposite_pass": minus_shift <= -0.10,
        "ignored_rate_pass": ignored_shift <= 0.10,
        "malformed_rate_pass": malformed_shift <= 0.05,
    }
    overall = all(gates.values())
    return {
        "schema_version": "cas_harness_behavior_v5_causal_analysis.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source": str(source_path) if source_path else None,
        "status": "PASS" if overall else "FAIL",
        "claim": (
            "LICENSED only for this model/layer/protocol causal steering gate."
            if overall
            else "OPEN / NOT LICENSED for causal compliance-state control."
        ),
        "claim_ceiling": (
            "Paired behavioral intervention analysis. This licenses causality only "
            "when the live forward-pass capture itself is trusted and WORM-retained."
        ),
        "rows_accepted": len(normalized),
        "rows_rejected": rejected,
        "complete_prompt_count": len(complete_prompt_ids),
        "condition_counts": dict(sorted(Counter(row["condition"] for row in normalized).items())),
        "label_counts": dict(sorted(Counter(row["label"] for row in normalized).items())),
        "metrics": {
            "plus_refusal_refused_shift": round(plus_shift, 6),
            "minus_refusal_refused_shift": round(minus_shift, 6),
            "random_same_norm_refused_shift": round(random_shift, 6),
            "plus_refusal_sign_flip_p": round(sign_p, 6),
            "plus_refusal_bootstrap_ci95": [round(ci_low, 6), round(ci_high, 6)],
            "plus_refusal_ignored_shift": round(ignored_shift, 6),
            "plus_refusal_malformed_shift": round(malformed_shift, 6),
        },
        "gates": gates,
        "important_limits": [
            "Primary outcome is behavior label, not probe score.",
            "Rows must be paired by prompt_id and seed across conditions before capture.",
            "Random same-norm steering must stay inert for a causal claim.",
        ],
    }


def normalize_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    accepted: list[dict[str, Any]] = []
    rejected: Counter[str] = Counter()
    for row in rows:
        prompt_id = str(row.get("prompt_id") or row.get("scenario_id") or "").strip()
        raw_seed = row.get("seed")
        if raw_seed is None:
            raw_seed = row.get("sample_seed")
        seed = str(raw_seed if raw_seed is not None else "").strip()
        condition_raw = str(row.get("condition") or "").strip()
        condition = CONDITION_ALIASES.get(condition_raw)
        label = normalise_label(row.get("label") or row.get("behavior") or row.get("judged_behavior"))
        if not prompt_id:
            rejected["missing_prompt_id"] += 1
            continue
        if not seed:
            rejected["missing_seed"] += 1
            continue
        if condition is None:
            rejected["unsupported_condition"] += 1
            continue
        if label is None:
            rejected["unsupported_label"] += 1
            continue
        accepted.append({"prompt_id": prompt_id, "seed": seed, "condition": condition, "label": label})
    return accepted, dict(sorted(rejected.items()))


def build_prompt_condition_rates(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, float]]]:
    counts: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for row in rows:
        counts[row["prompt_id"]][row["condition"]][row["label"]] += 1
    rates: dict[str, dict[str, dict[str, float]]] = {}
    for prompt_id, by_condition in counts.items():
        rates[prompt_id] = {}
        for condition, counter in by_condition.items():
            total = sum(counter.values())
            rates[prompt_id][condition] = {
                "COMPLIED": counter.get("COMPLIED", 0) / total if total else 0.0,
                "REFUSED": counter.get("REFUSED", 0) / total if total else 0.0,
                "IGNORED": counter.get("IGNORED", 0) / total if total else 0.0,
                "MALFORMED": counter.get("MALFORMED", 0) / total if total else 0.0,
            }
    return rates


def sign_flip_p_value(delta: np.ndarray, *, seed: int, permutations: int) -> float:
    observed = float(delta.mean())
    rng = np.random.default_rng(seed + 30_000)
    hits = 0
    for _ in range(max(1, permutations)):
        signs = rng.choice(np.asarray([-1.0, 1.0], dtype=np.float32), size=len(delta))
        score = float((delta * signs).mean())
        if score >= observed:
            hits += 1
    return (hits + 1) / (max(1, permutations) + 1)


def bootstrap_ci(delta: np.ndarray, *, seed: int, rounds: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed + 40_000)
    values = []
    for _ in range(max(1, rounds)):
        sample = rng.choice(delta, size=len(delta), replace=True)
        values.append(float(sample.mean()))
    low, high = np.quantile(np.asarray(values), [0.025, 0.975])
    return float(low), float(high)


def blocked_report(
    source_path: Path | None,
    normalized: list[dict[str, Any]],
    rejected: dict[str, int],
    reason: str,
) -> dict[str, Any]:
    return {
        "schema_version": "cas_harness_behavior_v5_causal_analysis.v1",
        "created_at": datetime.now(UTC).isoformat(),
        "source": str(source_path) if source_path else None,
        "status": "BLOCKED",
        "claim": "OPEN / NOT LICENSED for causal compliance-state control.",
        "claim_ceiling": reason,
        "rows_accepted": len(normalized),
        "rows_rejected": rejected,
        "metrics": {},
        "gates": {"complete_prompt_condition_blocks_pass": False},
    }


def read_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{path}:{line_number} is not valid JSON: {exc}") from exc
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def normalise_label(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    aliases = {
        "COMPLY": "COMPLIED",
        "COMPLIANCE": "COMPLIED",
        "REFUSE": "REFUSED",
        "REFUSAL": "REFUSED",
        "IGNORE": "IGNORED",
        "DEGENERATE": "MALFORMED",
        "EMPTY": "MALFORMED",
        "REPETITIVE": "MALFORMED",
    }
    text = aliases.get(text, text)
    return text if text in {"COMPLIED", "REFUSED", "IGNORED", "MALFORMED"} else None


if __name__ == "__main__":
    raise SystemExit(main())
