"""compare_s7_to_cas.py -- CJT-DEV-P1.2 independent comparator. Runs ONLY
after wordnet_profile_builder.py has sealed S7_DELTA_WN1_V3.json. This is the
only program that may read both the WordNet control and the CAS mapping.

ADMISSION LAW (owner ruling S7Delta.2 / P1.2 -- MAGNITUDE, not significance):
    exact WordNet source hash present and matched      (builder receipt)
    every row finite, nonnegative, sums to 1           (builder receipt)
    anti-uniform gates pass                            (builder receipt)
    factor-stability gate passes                       (builder receipt)
    NOT equal to S3 under any of the 24 column permutations
    A_soft* < 0.75    (equivalently D_copy = 1 - A_soft* > 0.25)
    A_hard* < 14/16
Failure of a magnitude condition is named CONTROL_INSUFFICIENTLY_DISTINCT --
NOT copying or misconduct (an independently constructed semantic control can
be close to CAS without wrongdoing).

The random-label nulls are DESCRIPTIVE ONLY (never gates), correctly named
CONDITIONAL_BALANCED_PERMUTATION_MONTE_CARLO (200,000 draws, frozen seed, with
Monte Carlo standard errors) -- they report that WordNet's factors align with
CAS more than shuffled labels, which is EXPECTED for two semantic descriptions
of verbs selected to instantiate the CAS operations. Also verifies the V3
profiles equal the frozen v2 profiles byte-for-byte (reuse law).

Writes S7_DELTA_V3_COMPARATOR_RECEIPT.json.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MC_SEED = 20260831
MC_DRAWS = 200_000
A_SOFT_MAX = 0.75                       # magnitude gate (D_copy > 0.25)
A_HARD_MAX_OF_16 = 14                   # magnitude gate (A_hard* < 14/16)

VERBS = ["drawn", "pulled", "felt", "captured",
         "withdrew", "repelled", "recoiled", "backed",
         "broke", "lay", "split", "made",
         "brought", "thought", "reminded", "summoned"]
CAS = {v: (i // 4) for i, v in enumerate(VERBS)}
CAS_ORDER = ("^2", "^3", "^6", "^8")


def main():
    table = json.loads((HERE / "S7_DELTA_WN1_V3.json").read_text("utf-8"))
    builder = json.loads(
        (HERE / "S7_DELTA_V3_BUILDER_RECEIPT.json").read_text("utf-8"))
    v2 = json.loads((HERE / "S7_DELTA_WN1_V2.json").read_text("utf-8"))

    # byte-frozen reuse law
    reuse_ok = all(table["verb_to_profile"][v] == v2["verb_to_profile"][v]
                   for v in VERBS)
    builder_ok = builder["builder_pass"] is True \
        and builder["builder_gates"]["wordnet_pin_matched"] is True

    bal = np.array([table["verb_to_profile"][v] for v in VERBS])
    cas_idx = [CAS[v] for v in VERBS]
    C = np.zeros((16, 4))
    for i, v in enumerate(VERBS):
        C[i, CAS[v]] = 1.0

    perms = list(itertools.permutations(range(4)))
    equals_S3 = bool(np.allclose(bal, C, atol=1e-6))
    perm_equals_S3 = any(np.allclose(bal[:, list(pi)], C, atol=1e-6)
                         for pi in perms)

    hard = bal.argmax(axis=1)
    A_hard, A_soft = -1, -1.0
    for pi in perms:
        mapped = np.array([pi[c] for c in cas_idx])
        A_hard = max(A_hard, int((hard == mapped).sum()))
        A_soft = max(A_soft, float(bal[np.arange(16), mapped].mean()))
    D_copy = 1.0 - A_soft

    gate_soft = A_soft < A_SOFT_MAX
    gate_hard = A_hard < A_HARD_MAX_OF_16

    # descriptive Monte Carlo nulls (NOT gates)
    rng = np.random.default_rng(MC_SEED)
    labels = np.array(cas_idx)
    nh = np.empty(MC_DRAWS, dtype=np.int16)
    ns = np.empty(MC_DRAWS)
    for d in range(MC_DRAWS):
        lab = rng.permutation(labels)
        bh, bs = -1, -1.0
        for pi in perms:
            mapped = np.array([pi[c] for c in lab])
            bh = max(bh, int((hard == mapped).sum()))
            bs = max(bs, float(bal[np.arange(16), mapped].mean()))
        nh[d] = bh
        ns[d] = bs
    p_hard = float((nh >= A_hard).mean())
    p_soft = float((ns >= A_soft).mean())
    se = lambda p: math.sqrt(max(p * (1 - p), 1e-12) / MC_DRAWS)

    # per-row aligned CAS mass under the best soft permutation (reporting)
    best_pi = max(perms, key=lambda pi: float(
        bal[np.arange(16), np.array([pi[c] for c in cas_idx])].mean()))
    aligned = {v: round(float(bal[i, best_pi[CAS[v]]]), 6)
               for i, v in enumerate(VERBS)}

    admitted = all([builder_ok, reuse_ok, not equals_S3, not perm_equals_S3,
                    gate_soft, gate_hard])
    verdict = "S7_DELTA_V3_ADMITTED" if admitted else \
        ("CONTROL_INSUFFICIENTLY_DISTINCT"
         if (builder_ok and reuse_ok and not equals_S3 and not perm_equals_S3)
         else "S7_DELTA_V3_PRECONDITION_FAILED")

    receipt = {
        "receipt_id": "S7_DELTA_V3_COMPARATOR_RECEIPT",
        "amendment": "CJT-DEV-P1.2 / S7Delta.2",
        "non_claim_bearing": True,
        "verdict": verdict,
        "admission_gates": {
            "builder_pass_and_wordnet_pin": builder_ok,
            "v3_profiles_equal_frozen_v2_byte_for_byte": reuse_ok,
            "equals_S3": equals_S3,
            "permutation_equals_S3": perm_equals_S3,
            "A_soft_star": round(A_soft, 6),
            "A_soft_gate_lt_0p75": gate_soft,
            "D_copy": round(D_copy, 6),
            "A_hard_star_of_16": int(A_hard),
            "A_hard_gate_lt_14_of_16": gate_hard},
        "descriptive_association_diagnostics": {
            "law": ("DESCRIPTIVE ONLY -- never admission gates. Association "
                    "with CAS is expected for two semantic descriptions of "
                    "verbs selected to instantiate the CAS operations; "
                    "association is not copying."),
            "null_name": "CONDITIONAL_BALANCED_PERMUTATION_MONTE_CARLO",
            "draws": MC_DRAWS, "seed": MC_SEED,
            "A_hard_null_p95": float(np.percentile(nh, 95)),
            "A_hard_p_value": round(p_hard, 6),
            "A_hard_p_value_mc_se": round(se(p_hard), 6),
            "A_soft_null_p95": round(float(np.percentile(ns, 95)), 6),
            "A_soft_p_value": round(p_soft, 6),
            "A_soft_p_value_mc_se": round(se(p_soft), 6)},
        "per_verb_aligned_cas_mass_under_best_soft_permutation": aligned,
        "best_soft_permutation_factor_for_each_cas_class": {
            CAS_ORDER[c]: f"WN-F{best_pi[c]}" for c in range(4)},
        "history": {
            "v2_verdict_preserved": "S7_DELTA_V2_CONSTRUCTION_FAILED "
                                    "(7b6f2560, under its own frozen "
                                    "significance gates)",
            "hard_verdict_preserved": "S7_PILOT_CONSTRUCTION_FAILED "
                                      "(19d9e843)"},
        "s7_delta_v3_table_sha256": hashlib.sha256(
            (HERE / "S7_DELTA_WN1_V3.json").read_bytes()).hexdigest()}
    (HERE / "S7_DELTA_V3_COMPARATOR_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    print(f"VERDICT: {verdict}")
    print(f"  A_soft*={A_soft:.6f} (<0.75: {gate_soft})  D_copy={D_copy:.6f}")
    print(f"  A_hard*={A_hard}/16 (<14: {gate_hard})")
    print(f"  equals_S3={equals_S3} perm_equals_S3={perm_equals_S3} "
          f"reuse_ok={reuse_ok} builder_ok={builder_ok}")
    print(f"  descriptive MC: p_hard={p_hard:.5f}±{se(p_hard):.5f} "
          f"p_soft={p_soft:.5f}±{se(p_soft):.5f}")
    return 0 if admitted else 4


if __name__ == "__main__":
    raise SystemExit(main())
