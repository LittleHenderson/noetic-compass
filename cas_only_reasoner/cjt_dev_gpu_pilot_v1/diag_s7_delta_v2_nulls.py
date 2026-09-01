"""diag_s7_delta_v2_nulls.py -- POST-VERDICT DIAGNOSTIC (not a gate, run AFTER
S7_DELTA_V2_CONSTRUCTION_FAILED was recorded): the owner-literal entropy-matched
null from ruling CJT-DEV-P1-S7Delta.1 correction 3.

The builder's PRIMARY null shuffles which balanced CAS labeling pairs with the
observed rows. This second null instead randomizes the 4 values WITHIN each
observed row (each row's entropy preserved EXACTLY; column masses preserved in
expectation by symmetry) with the CAS pairing fixed -- the "entropy- and
marginal-matched random simplex" reading of the ruling. Frozen seed + draws.

Purpose: show the anti-copy failure is robust to the choice of null, so the
verdict cannot be attributed to a null-construction artifact.

Result recorded 2026-08-31 (observed A_hard*=11/16, A_soft*=0.5239):
    row-value-permutation null: A_hard* p95=9.0    p=0.00688
                                A_soft* p95=0.4515 p=0.00121
    (primary shuffle null:      A_hard* p95=10.0   p=0.01090
                                A_soft* p95=0.4532 p=0.00160)
Both nulls and the structural bound (A_hard* <= 9/16) agree: FAILED.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEED = 20260831
DRAWS = 200_000

VERBS = ["drawn", "pulled", "felt", "captured",
         "withdrew", "repelled", "recoiled", "backed",
         "broke", "lay", "split", "made",
         "brought", "thought", "reminded", "summoned"]
CAS = {v: (i // 4) for i, v in enumerate(VERBS)}


def main():
    t = json.loads((HERE / "S7_DELTA_WN1_V2.json").read_text("utf-8"))
    bal = np.array([t["verb_to_profile"][v] for v in VERBS])
    cas = np.array([CAS[v] for v in VERBS])
    perms = list(itertools.permutations(range(4)))

    def astar(M):
        hard = M.argmax(axis=1)
        bh, bs = -1, -1.0
        for pi in perms:
            mapped = np.array([pi[c] for c in cas])
            bh = max(bh, int((hard == mapped).sum()))
            bs = max(bs, float(M[np.arange(16), mapped].mean()))
        return bh, bs

    oh, osoft = astar(bal)
    rng = np.random.default_rng(SEED)
    nh = np.empty(DRAWS, dtype=np.int16)
    ns = np.empty(DRAWS)
    for d in range(DRAWS):
        M = np.take_along_axis(bal, np.argsort(rng.random((16, 4)), axis=1),
                               axis=1)
        h, s = astar(M)
        nh[d] = h
        ns[d] = s
    print(f"observed A_hard*={oh}/16  A_soft*={osoft:.4f}")
    print(f"row-value-permutation null: A_hard* p95={np.percentile(nh, 95)} "
          f"p={float((nh >= oh).mean()):.5f}")
    print(f"                            A_soft* p95={np.percentile(ns, 95):.4f} "
          f"p={float((ns >= osoft).mean()):.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
