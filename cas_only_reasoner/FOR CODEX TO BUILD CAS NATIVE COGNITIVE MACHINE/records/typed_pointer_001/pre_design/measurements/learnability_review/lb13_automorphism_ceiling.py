"""LB13 — the decision-theoretic ceiling of the draft's correspondence head, and the exact
gradient amplification per round of the shared recurrence.

Part 1. The head scores a candidate mapping by a SUM of per-node scores, where the per-node
score has no input that depends on the target world's edge set (section 2.1 forbids derived
relations). So every permutation belonging to the automorphism group of the source world
gets an IDENTICAL total score, and the declared tie rule is "first candidate wins".
For every correspondence record this script counts the admissible mappings that lie in the
source world's automorphism group. Those are exactly the mappings the head can be made to
prefer; any admissible mapping outside that group needs an edge-dependent score component
that the declared head does not have.
"""
import sys
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path

import numpy as np

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c, checker, slots

frozen, tokenizer, devdoc = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
heldset, trainedset = set(held), set(trained)
packets = dict(c.public_packets(frozen))


def side(rid):
    return "held" if rid in heldset else "trained" if rid in trainedset else "excluded"


def autos(w):
    refs = sorted(n["ref"] for n in w["nodes"])
    edges = frozenset((e["source"], e["target"]) for e in w["contains"])
    out = []
    for order in permutations(refs):
        m = dict(zip(refs, order))
        if frozenset((m[a], m[b]) for a, b in edges) == edges:
            out.append(m)
    return out


rows = []
for rid in sorted(packets):
    p = packets[rid]
    q = p["record"]["query"]
    if q["kind"] != "correspondence":
        continue
    worlds = {w["world_id"]: w for w in p["source"]["worlds"]}
    focus = worlds[q["focus_world_id"]]
    target = worlds[q["arguments"]["target_world_id"]]
    src = sorted(n["ref"] for n in focus["nodes"])
    tgt = sorted(n["ref"] for n in target["nodes"])
    adm = {checker._canonical(a["value"]) for a in checker.derive_target(p["source"], q)["admissible_answers"]}
    aut = autos(focus)
    # all automorphisms of the source world, expressed as source->target refs by
    # order-of-appearance (a machine with no edge access cannot tell these apart)
    autosets = []
    for m in aut:
        cand = {"status": "MAPPING",
                "pairs": [{"source": a, "target": tgt[src.index(m[a])]} for a in src]}
        autosets.append(checker._canonical(cand))
    in_aut_and_valid = sum(1 for c_ in set(autosets) if c_ in adm)
    rows.append({"rid": rid, "side": side(rid), "n_admissible": len(adm), "n_aut": len(aut),
                 "automorphisms_that_are_admissible": in_aut_and_valid})

print("correspondence records %d" % len(rows))
for s in ("held", "trained", "excluded"):
    sub = [r for r in rows if r["side"] == s]
    if not sub:
        continue
    print("  %-9s records %d ; automorphisms of the source world: %s ; of the records,"
          " automorphism-group mappings that ARE admissible: %d"
          % (s, len(sub), sorted(Counter(r["n_aut"] for r in sub).items()),
             sum(1 for r in sub if r["automorphisms_that_are_admissible"] > 0)))
print()
print("records where NO admissible mapping lies in the source automorphism group")
print("(the head's tie structure cannot even land on a correct answer there):")
bad = [r for r in rows if r["automorphisms_that_are_admissible"] == 0]
print("  ", len(bad), "of", len(rows), "records;",
      dict(Counter(r["side"] for r in bad)))
print()
print("records where the admissible set is a SINGLE mapping and the source world has no")
print("non-trivial automorphism (so the head must pick exactly that permutation):")
narrow = [r for r in rows if r["n_admissible"] == 1 and r["n_aut"] == 1]
print("  ", len(narrow), "of", len(rows), ";", dict(Counter(r["side"] for r in narrow)))

# =====================================================================
# Part 2: gradient amplification per shared round, at torch-default and at
# the actual framework init, with the actual node counts.
# =====================================================================
D = 64


def mixstep(h, pars, kids, Wl, Wr, Wm, mode):
    hh = h / (np.sqrt(np.mean(h * h)) + 1e-8) if mode == "input" else h
    a = hh + pars @ hh + kids @ hh
    left, right = a @ Wl.T, a @ Wr.T
    tl, tr = np.tanh(left), np.tanh(right)
    B = np.einsum("ik,jk->ijk", (1 - tl * tl) @ Wl, Wm[:, :D]) + np.einsum("ik,jk->ijk", (1 - tr * tr) @ Wr, Wm[:, D:])
    n = h.shape[0]
    J = np.zeros((n, n, D, D))
    for i in range(n):
        J[i, i] = np.eye(D)
    hist = []
    for _ in range(8):
        hh = h / (np.sqrt(np.mean(h * h)) + 1e-8) if mode == "input" else h
        a = hh + pars @ hh + kids @ hh
        left, right = a @ Wl.T, a @ Wr.T
        tl, tr = np.tanh(left), np.tanh(right)
        B = np.einsum("ik,jk->ijk", (1 - tl * tl) @ Wl, Wm[:, :D]) + np.einsum("ik,jk->ijk", (1 - tr * tr) @ Wr, Wm[:, D:])
        Jn = np.zeros_like(J)
        for i in range(n):
            for j in range(n):
                c_ = (1.0 if i == j else 0.0) + float(pars[i, j]) + float(kids[i, j])
                if c_:
                    Jn[i, j] = c_ * B[i]
        if mode == "output":
            for i in range(n):
                r = np.sqrt(np.mean(h[i] * h[i])) + 1e-8
                u = h[i] / r
                Jn[i] = (np.eye(D) - np.outer(u, u)) / r @ Jn[i]
        J = J + Jn
        h = h + np.concatenate([tl, tr], axis=-1) @ Wm.T
        if mode == "output":
            h = h / (np.sqrt(np.mean(h * h)) + 1e-8)
        hist.append(np.linalg.norm(J.reshape(n * D, n * D), 2))
    return hist


rng = np.random.default_rng(0)
Wl = rng.uniform(-1 / np.sqrt(D), 1 / np.sqrt(D), (D, D))
Wr = rng.uniform(-1 / np.sqrt(D), 1 / np.sqrt(D), (D, D))
Wm = rng.uniform(-1 / np.sqrt(2 * D), 1 / np.sqrt(2 * D), (D, 2 * D))
print()
print("Part 2. spectral norm of d(sum h_i^K)/d(h^0) after each SHARED round, one fixed init,")
print("        node counts taken from the real material (3, 4 bank; 10 development)")
for mode in ("output", "input", "none"):
    for n, edges in ((3, [(0, 1), (1, 2)]), (4, [(0, 1), (0, 3), (1, 2), (3, 2)]),
                     (10, [(0, 1), (0, 2), (0, 3), (1, 4), (2, 5), (5, 6), (3, 7), (7, 8), (8, 9)])):
        adj = np.zeros((n, n))
        for a, b in edges:
            adj[a, b] = 1.0
        feats = rng.normal(0, 1, (n, 9))
        Win = rng.normal(0, 1 / 3, (D, 9))
        h = feats @ Win.T
        if mode == "output":
            h = h / (np.sqrt(np.mean(h * h)) + 1e-8)
        hist = mixstep(h, adj.T, adj, Wl, Wr, Wm, mode)
        print("   rms_after=%-7s nodes %2d  %s  (round-to-round factor %.4g)"
              % (mode, n, " ".join("%.4g" % v for v in hist), hist[-1] / max(hist[0], 1e-12) ** (1 / 7)))
