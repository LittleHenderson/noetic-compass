"""build_s7_h.py -- CJT-DEV-P1-S7Delta.1: REGISTER the hard WordNet
primary-lexname control as S7-H (owner ruling, adopt-with-modifications).
Non-claim-bearing development artifact.

The original hard partition FAILED its preregistered Cramer's-V <= 0.35 gate
(S7_PILOT_CONSTRUCTION_FAILED, commit 19d9e843 -- preserved, not rewritten).
The owner's exact permutation analysis then showed the GATE was miscalibrated
for n=16: under the exact uniformly-random balanced four-way partition null
(16!/(4!)^4 = 63,063,000 labelled partitions),
    P(V >= 0.353553) = 0.9000405
    P(V <= 0.35)     = 0.0999595
i.e. the old threshold admitted only ~10% of genuinely random balanced
partitions, and the attainable-V lattice jumps 0.288675 -> 0.353553 with 0.35
sitting in the empty gap. The observed V=0.353553 (chi2=6) is therefore fully
compatible with independence. Ruling: the procedural failure stands; the
"no honest semantic control can exist" interpretation is RETIRED; the honest
primary-lexname partition is REGISTERED as the hard control S7-H.

This script does NOT re-derive the partition (avoiding drift): it reads the
frozen assignment out of S7_PILOT_BUILD_RECEIPT.json, re-verifies every
statistic from scratch (balance, chi2, V, !=S3, not-a-permutation-of-S3), and
attaches the exact-null calibration (independently re-verified by full
63,063,000-partition enumeration in this session).

Writes S7_H_WN1.json + S7_H_BUILD_RECEIPT.json.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

CAS_ORDER = ("^2", "^3", "^6", "^8")
VERBS = ["drawn", "pulled", "felt", "captured",
         "withdrew", "repelled", "recoiled", "backed",
         "broke", "lay", "split", "made",
         "brought", "thought", "reminded", "summoned"]
CAS = {v: (i // 4) for i, v in enumerate(VERBS)}

# exact-null constants (owner's enumeration, INDEPENDENTLY RE-VERIFIED this
# session over all 63,063,000 balanced labelled partitions)
EXACT_NULL = {
    "space": "all 16!/(4!)^4 = 63,063,000 balanced labelled 4-way partitions",
    "P_V_ge_0p353553": 0.9000405,
    "P_V_le_0p35": 0.0999595,
    "P_bestperm_argmax_le_8_of_16": 0.81205,
    "P_bestperm_argmax_le_9_of_16": 0.94555,
    "attainable_V_near_threshold": [0.288675, 0.353553, 0.408248],
    "verification": "re-enumerated independently in-session; all five values "
                    "matched the owner's ruling exactly",
}


def main():
    src = json.loads((HERE / "S7_PILOT_BUILD_RECEIPT.json").read_text("utf-8"))
    pr = src["pre_declared_primary_rule"]
    assign = pr["assignment_verb_to_classindex"]
    assert set(assign) == set(VERBS), "assignment vocabulary mismatch"

    # ---- re-verify every statistic from the raw assignment ----
    sizes = [sum(1 for v in VERBS if assign[v] == k) for k in range(4)]
    balanced = sizes == [4, 4, 4, 4]
    T = [[0] * 4 for _ in range(4)]                    # S7H rows x CAS cols
    for v in VERBS:
        T[assign[v]][CAS[v]] += 1
    chi2 = sum((T[i][j] - 1.0) ** 2 for i in range(4) for j in range(4))
    V = math.sqrt(chi2 / (16 * 3))
    equals_S3 = all(assign[v] == CAS[v] for v in VERBS)
    is_perm = any(all(assign[v] == pi[CAS[v]] for v in VERBS)
                  for pi in itertools.permutations(range(4)))
    # permutation-invariant hard agreement (for the record)
    a_star = max(sum(1 for v in VERBS if assign[v] == pi[CAS[v]])
                 for pi in itertools.permutations(range(4)))

    ok = (balanced and abs(chi2 - pr["chi2"]) < 1e-9
          and abs(V - pr["cramers_v"]) < 1e-6 and not equals_S3 and not is_perm)

    table = {
        "table_id": "S7_H_WN1",
        "control_name": "Hard WordNet Primary-Lexname Control",
        "non_claim_bearing": True,
        "profile_semantics": "EXCLUSIVE_LEXICAL_CATEGORY",
        "authority": "RESOURCE_DERIVED_CONTROL",
        "cas_class_order": CAS_ORDER,
        "verb_to_class": {v: int(assign[v]) for v in sorted(assign)},
        "construction": pr["name"],
        "provenance": {**src["wordnet"],
                       "frozen_in": "S7_PILOT_BUILD_RECEIPT.json (commit 19d9e843)",
                       "registered_under": "CJT-DEV-P1-S7Delta.1"},
    }
    table_text = json.dumps(table, indent=2, sort_keys=True) + "\n"
    table_sha = hashlib.sha256(table_text.encode("utf-8")).hexdigest()

    receipt = {
        "receipt_id": "S7_H_BUILD_RECEIPT",
        "pilot": "CJT-DEV-P1",
        "amendment": "CJT-DEV-P1-S7Delta.1",
        "non_claim_bearing": True,
        "verdict": "S7_H_REGISTERED" if ok else "S7_H_VERIFICATION_FAILED",
        "s7_h_table_sha256": table_sha,
        "preserves": {
            "hard_partition_verdict": "S7_PILOT_CONSTRUCTION_FAILED",
            "interpretation_amendment": {
                "SUPPORTED": "the original hard-partition protocol failed its "
                             "preregistered V<=0.35 gate",
                "NOT_SUPPORTED": "that no honest independent semantic control "
                                 "can exist for these verbs",
                "retired_language": "'missed by only 0.0036' -- replaced by the "
                                    "frozen exact-null statement below"},
        },
        "frozen_replacement_statement":
            "The hard WordNet partition produced chi-square=6 and V=0.353553. "
            "Under the exact uniformly random balanced four-way permutation "
            "null: P(V >= observed) = 0.9000405 and P(V <= 0.35) = 0.0999595. "
            "The old threshold admitted only about 10% of random balanced "
            "partitions and was miscalibrated for n=16.",
        "verified_statistics": {
            "class_sizes": sizes, "balanced": balanced,
            "chi2": chi2, "cramers_v": round(V, 6),
            "equals_S3": equals_S3, "is_permutation_of_S3": is_perm,
            "best_permutation_argmax_agreement_of_16": a_star,
            "contingency_S7H_rows_x_CAS_cols": T},
        "exact_null_calibration": EXACT_NULL,
        "compatibility_conclusion":
            "V=0.353553 gives NO evidence against the random-balanced null "
            "(p=0.90). This does not prove WordNet and CAS are independent; it "
            "means the observed association is fully compatible with an "
            "independent balanced partition. S7-H is registered as a valid "
            "hard control.",
    }

    (HERE / "S7_H_WN1.json").write_text(table_text, encoding="utf-8")
    (HERE / "S7_H_BUILD_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"VERDICT: {receipt['verdict']}")
    print(f"  sizes={sizes} chi2={chi2} V={V:.6f} equals_S3={equals_S3} "
          f"perm={is_perm} A*={a_star}/16")
    print(f"  table sha256 {table_sha[:16]}...")
    return 0 if ok else 4


if __name__ == "__main__":
    raise SystemExit(main())
