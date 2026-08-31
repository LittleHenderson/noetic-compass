"""emit_gate1_status.py -- the COMMITTED deterministic Gate 1 status authority.

Frozen at Gate 1A (review fix: not deferred to Gate 1B, so it cannot be written
after validation results are visible). Reads the raw per-arm results JSON and emits
exactly one status per claim under THRESHOLDS_AND_STATUS_LAW.yaml v2. Prose never
assigns status; this program does.

Input file format (produced by the Gate 1B evaluation step):
{
  "protected_passage_ids": [...1000 ids in frozen order...],
  "arms": { "S0": {"per_seed_correct": {"11": [0/1 x 1000], "23": [...], "47": [...]}},
            ..., "S7": {...} },
  "claim_a": {"probe_protected_accuracy": float,
               "shuffled_control_accuracy": float}
}

Usage: python emit_gate1_status.py <results.json>   -> prints the status JSON.
Deterministic: bootstrap uses random.Random(20260831); no wall-clock in the law.
"""
from __future__ import annotations

import json
import random
import sys

SEEDS = ("11", "23", "47")
MARGIN = 0.03
BOOT_N = 10000
BOOT_SEED = 20260831
CLAIM_A_MIN = 0.80
CLAIM_A_MARGIN = 0.15


def per_passage_scores(arm):
    vecs = [arm["per_seed_correct"][s] for s in SEEDS]
    n = len(vecs[0])
    assert all(len(v) == n for v in vecs), "seed vectors disagree in length"
    return [(vecs[0][i] + vecs[1][i] + vecs[2][i]) / 3.0 for i in range(n)]


def mean(xs):
    return sum(xs) / len(xs)


def gate(s3, ctrl):
    """One hard gate: margin + bootstrap CI + per-seed consistency."""
    a, b = per_passage_scores(s3), per_passage_scores(ctrl)
    diff = [a[i] - b[i] for i in range(len(a))]
    md = mean(diff)
    rng = random.Random(BOOT_SEED)
    n = len(diff)
    boots = []
    for _ in range(BOOT_N):
        boots.append(mean([diff[rng.randrange(n)] for _ in range(n)]))
    boots.sort()
    lo, hi = boots[int(0.025 * BOOT_N)], boots[int(0.975 * BOOT_N) - 1]
    per_seed = all(
        mean(s3["per_seed_correct"][s]) > mean(ctrl["per_seed_correct"][s])
        for s in SEEDS)
    passed = (md >= MARGIN) and (lo > 0.0) and per_seed
    return {"mean_diff": md, "ci95": [lo, hi], "per_seed_positive_3of3": per_seed,
            "margin_met": md >= MARGIN, "passed": passed}


def emit(results):
    arms = results["arms"]
    g6 = gate(arms["S3"], arms["S6"])
    g7 = gate(arms["S3"], arms["S7"])
    g4 = gate(arms["S3"], arms["S4"])
    g5 = gate(arms["S3"], arms["S5"])
    if g6["passed"] and g7["passed"]:
        b = "CLAIM_B_LICENSED"
    elif g6["passed"] and not g7["passed"]:
        b = "GENERIC_SEMANTIC_STRUCTURE_DETECTED"
    elif g7["passed"] and not g6["passed"]:
        b = "CAPACITY_EFFECT_DETECTED"
    elif ((g4["mean_diff"] >= MARGIN and g4["ci95"][0] > 0)
          or (g5["mean_diff"] >= MARGIN and g5["ci95"][0] > 0)):
        b = "SIDE_CHANNEL_ONLY"
    else:
        b = "STATIC_CAS_COUPLING_NOT_SUPPORTED"
    ca = results["claim_a"]
    a_ok = (ca["probe_protected_accuracy"] >= CLAIM_A_MIN
            and (ca["probe_protected_accuracy"] - ca["shuffled_control_accuracy"])
            >= CLAIM_A_MARGIN)
    return {
        "status_law": "GATE1_THRESHOLDS_v2",
        "claim_a_status": "CLAIM_A_LICENSED" if a_ok else "CLAIM_A_NOT_LICENSED",
        "claim_b_status": b,
        "gates": {"S3_vs_S6": g6, "S3_vs_S7": g7, "S3_vs_S4": g4, "S3_vs_S5": g5},
        "arm_means": {k: mean(per_passage_scores(v)) for k, v in sorted(arms.items())},
        "honest_ceiling_disclosures_required": True,
        "emitted_by": "tools/emit_gate1_status.py (deterministic; the only claim-status authority)",
    }


def main():
    results = json.loads(open(sys.argv[1], encoding="utf-8").read())
    print(json.dumps(emit(results), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
