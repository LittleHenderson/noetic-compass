"""pathb_core.py -- PATH B (CJT-T2) single source of truth: registered verb
inventories, clause/question templates, constructive per-family operation-graph
generation, discourse ordering, candidate-shuffle law, the frozen graph solver,
and the frozen S-ALT50 corruption map. Development-only, non-claim-bearing.

Owner rulings honored: K <= 6 (frozen MAX_IDEAS); v1's 16 verbs retired from
ALL surfaces; 10 new verbs/class allocated A:3 B:3 C:2 D:2; 6 clause forms per
class allocated A:2 B:2 C:1 D:1; per-split disjoint entity bundles; candidate
lists shuffled per-passage (seeded); four question families with explicit
uniqueness constraints; answers computed ONLY by the frozen solver.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "cjt_gate1a_static_neural_v1"
sys.path.insert(0, str(PKG))
from exec.prng import HashPRNG  # noqa: E402

CLASSES = ("^2", "^3", "^6", "^8")
FAMILIES = ("A", "B", "C", "D")
SPLIT_FAMILY = {"train": ("A", "B"), "val": ("C",), "protected": ("D",)}
K = 6

# ---- registered verb inventories (surface past forms; v1's 16 NOWHERE) ------
VERBS = {
    "^2": ["lured", "enticed", "charmed", "beckoned", "mesmerized",
           "enchanted", "tempted", "gripped", "hooked", "dazzled"],
    "^3": ["shunned", "avoided", "dodged", "spurned", "rebuffed",
           "resisted", "evaded", "snubbed", "deflected", "escaped"],
    "^6": ["divided", "fragmented", "dissolved", "crumbled", "splintered",
           "unraveled", "partitioned", "scattered", "dispersed", "branched"],
    "^8": ["evoked", "conjured", "sparked", "invoked", "awakened",
           "stirred", "kindled", "prompted", "elicited", "roused"],
}
V1_RETIRED = {"drawn", "pulled", "felt", "captured", "withdrew", "repelled",
              "recoiled", "backed", "broke", "lay", "split", "made",
              "brought", "thought", "reminded", "summoned"}
# per-class allocation A:3 B:3 C:2 D:2 (indices into VERBS[c])
VERB_ALLOC = {"A": (0, 1, 2), "B": (3, 4, 5), "C": (6, 7), "D": (8, 9)}


def family_verbs(cls, fam):
    return [VERBS[cls][i] for i in VERB_ALLOC[fam]]


# ---- registered clause forms (6 per class; A:0,1 B:2,3 C:4 D:5) -------------
FORMS = {
    "^2": ["{i} {v} {m}.",
           "{m} was {v} by {i}.",
           "it was {i} that {v} {m}.",
           "{m}, whom {i} {v}, took notice.",
           "what {v} {m} was {i}.",
           "by {i}, {m} was utterly {v}."],
    "^3": ["{m} {v} {i}.",
           "{i} was {v} by {m}.",
           "it was {i} that {m} {v}.",
           "{i}, which {m} {v}, faded away.",
           "what {m} {v} was {i}.",
           "as for {i}, {m} {v} it."],
    "^6": ["{i} {v} into {p1}, {p2}, and {p3}.",
           "{i} was {v} into {p1}, {p2}, and {p3}.",
           "it was {i} that {v} into {p1}, {p2}, and {p3}.",
           "{i}, which {v} into {p1}, {p2}, and {p3}, stood apart.",
           "what {v} into {p1}, {p2}, and {p3} was {i}.",
           "into {p1}, {p2}, and {p3} {v} {i}."],
    "^8": ["{a} {v} {b} for {m}.",
           "{b} was {v} by {a} for {m}.",
           "it was {a} that {v} {b} for {m}.",
           "for {m}, {a} {v} {b}.",
           "what {a} {v} for {m} was {b}.",
           "{b}, {v} by {a}, came to {m}."],
}
FORM_ALLOC = {"A": (0, 1), "B": (2, 3), "C": (4,), "D": (5,)}

# ---- question frames (global function words; operation verbs per family) ----
Q_FRAMES = {
    "QB_REL": "which idea {v2} the mind that {v3} {x}?",
    "QB_COMP": "which idea was {v8} for the mind that {x} {v2}?",
    "QB_INT": "which part belonged to both {i1} and the idea that {v2} {m}?",
    "QB_ORD_AFTER": "which idea {v2} {m} after {m} {v3} {x}?",
    "QB_ORD_BEFORE": "which idea {v2} {m} before {m} {v3} {x}?",
}
QFAMS = ("QB_REL", "QB_COMP", "QB_INT", "QB_ORD")
FINAL_CLASS = {"QB_REL": "^2", "QB_COMP": "^8", "QB_INT": "^6",
               "QB_ORD": "^2"}

# ---- per-split entity bundles (disjoint) ------------------------------------
MINDS = {
    "train": ["mira", "tomas", "ada", "felix", "nora", "iris", "dmitri",
              "clara", "hugo", "selin", "petra", "omar"],
    "val": ["yuki", "bram", "leila", "casper", "ines", "ravi", "greta",
            "silas"],
    "protected": ["odile", "matteo", "priya", "lars", "zora", "emil",
                  "wanda", "kofi"],
}
IDEAS = {
    "train": ["algebra", "pottery", "chess", "botany", "jazz", "sailing",
              "origami", "falconry", "geometry", "weaving", "astronomy",
              "calligraphy", "fencing", "mycology", "cartography", "juggling"],
    "val": ["archery", "topology", "glassblowing", "beekeeping", "mosaics",
            "puppetry", "linguistics", "bonsai", "surveying", "drumming"],
    "protected": ["heraldry", "meteorology", "bookbinding", "cheesemaking",
                  "acoustics", "quilting", "navigation", "taxidermy",
                  "genealogy", "smithing"],
}
PARTS = {
    "train": ["gears", "petals", "ledgers", "prisms", "anthems", "spindles",
              "runes", "beacons", "lattices", "embers", "sonatas", "atlases",
              "chisels", "banners", "orchids", "flasks", "medallions",
              "pulleys"],
    "val": ["awls", "cupolas", "tridents", "parchments", "sundials",
            "gables", "torrents", "spigots", "garlands", "crucibles",
            "pennants", "vellums"],
    "protected": ["cairns", "flutes", "girders", "lanterns", "mallets",
                  "nettles", "obelisks", "pestles", "quivers", "rudders",
                  "sextants", "tumblers"],
}


# ---- graph construction (constructive per family; K = 6) --------------------
def _pick(rng, pool, n):
    """n distinct items from pool via HashPRNG (deterministic)."""
    return rng.sample(pool, n)


def build_graph(rng, split, qfam):
    """Return (ops, question_spec). ops = ordered list of
    (cls, args_tuple); question_spec drives rendering + solver."""
    m = _pick(rng, MINDS[split], 2)
    i = _pick(rng, IDEAS[split], 5)
    p = _pick(rng, PARTS[split], 6)
    if qfam == "QB_REL":
        m1, m2 = m
        x, iA, i2, i3 = i[0], i[1], i[2], i[3]
        variant = rng.randbelow(2)
        ops = [("^3", (m1, x)), ("^2", (iA, m1)), ("^2", (i2, m2)),
               ("^6", (i3, (p[0], p[1], p[2]))), ("^8", (x, i2, m2))]
        ops.append(("^2", (i3, m2)) if variant == 0 else ("^3", (m1, i3)))
        spec = {"qfam": qfam, "anchors": [x], "sel_mind": m1, "answer": iA}
    elif qfam == "QB_COMP":
        m1, m2 = m
        x, a, b, i2 = i[0], i[1], i[2], i[3]
        ops = [("^2", (x, m1)), ("^8", (a, b, m1)), ("^2", (i2, m2)),
               ("^2", (b, m2)), ("^8", (x, i2, m2)),
               ("^6", (b, (p[0], p[1], p[2])))]
        spec = {"qfam": qfam, "anchors": [x], "sel_mind": m1, "answer": b}
    elif qfam == "QB_INT":
        m1, m2 = m
        i1, i2, i3 = i[0], i[1], i[2]
        p_sh, p_d, p3, p4, p5, p6 = p
        ops = [("^2", (i2, m1)),
               ("^6", (i1, (p_sh, p6, p_d))),
               ("^6", (i2, (p_sh, p3, p4))),
               ("^6", (i3, (p_d, p5, p3))),
               ("^2", (i1, m2)), ("^2", (i3, m2))]
        spec = {"qfam": qfam, "anchors": [i1, m1], "sel_mind": m1,
                "answer": p_sh}
    else:                                              # QB_ORD
        m1, m2 = m
        x, iA, iB, i2, i5 = i[0], i[1], i[2], i[3], i[4]
        # m2's two ^2 clauses are forced to the discourse EXTREMES (slots 0
        # and 5), so first-/last-clause matcher tie-breaks always land on a
        # distractor (CHK-4 leak fix); the ^8 gives i2 its class overlap.
        ops = [("^2", (iB, m1)), ("^3", (m1, x)), ("^2", (iA, m1)),
               ("^2", (i2, m2)), ("^8", (x, i2, m2)), ("^2", (i5, m2))]
        side = "AFTER" if rng.randbelow(2) == 0 else "BEFORE"
        spec = {"qfam": qfam, "anchors": [m1, x], "sel_mind": m1,
                "side": side, "answer": iA if side == "AFTER" else iB}
    # shuffle each ^6 part list's ORDER (sets unchanged) -- kills the
    # answer-in-slot-p1 matcher leak (CHK-4 fix)
    ops2 = []
    for c, a in ops:
        if c == "^6":
            ps = list(a[1])
            rng.shuffle(ps)
            ops2.append((c, (a[0], tuple(ps))))
        else:
            ops2.append((c, a))
    ops = ops2
    # discourse order: ORD forces m2's block to slots {0, s, 5} with the two
    # m2-^2 clauses at the extremes; m1's relative order preserved. Others
    # fully shuffled.
    order = list(range(len(ops)))
    if qfam == "QB_ORD":
        fixed = [0, 1, 2]                     # iB-^2, pivot-^3, iA-^2 (m1)
        movable = [3, 4, 5]                   # ^2(i2,m2), ^8, ^2(i5,m2)
        s_mid = 1 + rng.randbelow(4)          # ^8 slot in 1..4
        slots = [0, s_mid, 5]
        order = []
        fi = mi = 0
        for pos in range(6):
            if pos in slots:
                order.append(movable[mi]); mi += 1
            else:
                order.append(fixed[fi]); fi += 1
    else:
        rng.shuffle(order)
    ops = [ops[j] for j in order]
    return ops, spec


# ---- rendering --------------------------------------------------------------
def render_clause(rng, cls, args, fam):
    v = family_verbs(cls, fam)[rng.randbelow(len(family_verbs(cls, fam)))]
    forms = FORM_ALLOC[fam]
    f = FORMS[cls][forms[rng.randbelow(len(forms))]]
    if cls == "^2":
        i_, m_ = args
        return f.format(i=i_, m=m_, v=v)
    if cls == "^3":
        m_, i_ = args
        return f.format(m=m_, i=i_, v=v)
    if cls == "^6":
        i_, ps = args
        return f.format(i=i_, v=v, p1=ps[0], p2=ps[1], p3=ps[2])
    a_, b_, m_ = args
    return f.format(a=a_, b=b_, v=v, m=m_)


def render_question(rng, spec, fam):
    q = spec["qfam"]
    v2 = family_verbs("^2", fam)[rng.randbelow(len(VERB_ALLOC[fam]))]
    v3 = family_verbs("^3", fam)[rng.randbelow(len(VERB_ALLOC[fam]))]
    v8 = family_verbs("^8", fam)[rng.randbelow(len(VERB_ALLOC[fam]))]
    if q == "QB_REL":
        return Q_FRAMES["QB_REL"].format(v2=v2, v3=v3, x=spec["anchors"][0])
    if q == "QB_COMP":
        return Q_FRAMES["QB_COMP"].format(v8=v8, x=spec["anchors"][0], v2=v2)
    if q == "QB_INT":
        i1, m1 = spec["anchors"]
        return Q_FRAMES["QB_INT"].format(i1=i1, v2=v2, m=m1)
    m1, x = spec["anchors"]
    key = "QB_ORD_AFTER" if spec["side"] == "AFTER" else "QB_ORD_BEFORE"
    return Q_FRAMES[key].format(v2=v2, m=m1, v3=v3, x=x)


# ---- the frozen graph solver (answers + edge-usage traces) ------------------
def solve(ops, spec):
    """Answer + list of used edge indices, computed from the FORMAL graph."""
    q = spec["qfam"]
    if q == "QB_REL":
        x = spec["anchors"][0]
        sel = [k for k, (c, a) in enumerate(ops) if c == "^3" and a[1] == x]
        assert len(sel) == 1, "REL selector not unique"
        m1 = ops[sel[0]][1][0]
        fin = [k for k, (c, a) in enumerate(ops) if c == "^2" and a[1] == m1]
        assert len(fin) == 1, "REL final ^2 not unique for selected mind"
        return ops[fin[0]][1][0], [sel[0], fin[0]]
    if q == "QB_COMP":
        x = spec["anchors"][0]
        sel = [k for k, (c, a) in enumerate(ops) if c == "^2" and a[0] == x]
        assert len(sel) == 1, "COMP selector not unique"
        m1 = ops[sel[0]][1][1]
        fin = [k for k, (c, a) in enumerate(ops) if c == "^8" and a[2] == m1]
        assert len(fin) == 1, "COMP final ^8 not unique"
        return ops[fin[0]][1][1], [sel[0], fin[0]]
    if q == "QB_INT":
        i1, m1 = spec["anchors"]
        sel = [k for k, (c, a) in enumerate(ops) if c == "^2" and a[1] == m1]
        assert len(sel) == 1, "INT selector not unique"
        i2 = ops[sel[0]][1][0]
        six = {a[0]: (k, set(a[1])) for k, (c, a) in enumerate(ops)
               if c == "^6"}
        assert i1 in six and i2 in six, "INT referenced ^6 list missing"
        shared = six[i1][1] & six[i2][1]
        assert len(shared) == 1, "INT shared part not unique"
        return next(iter(shared)), [sel[0], six[i1][0], six[i2][0]]
    m1, x = spec["anchors"]
    piv = [k for k, (c, a) in enumerate(ops)
           if c == "^3" and a[0] == m1 and a[1] == x]
    assert len(piv) == 1, "ORD pivot not unique"
    twos = [k for k, (c, a) in enumerate(ops) if c == "^2" and a[1] == m1]
    assert len(twos) == 2, "ORD needs exactly two ^2 for the mind"
    if spec["side"] == "AFTER":
        cand = [k for k in twos if k > piv[0]]
    else:
        cand = [k for k in twos if k < piv[0]]
    assert len(cand) == 1, "ORD side not unique"
    return ops[cand[0]][1][0], [piv[0], cand[0]]


# ---- record assembly (with candidate-order law) -----------------------------
def entities_of(ops):
    minds, ideas, parts = [], [], []
    seen = set()

    def add(lst, e):
        if e not in seen:
            seen.add(e); lst.append(e)
    for c, a in ops:
        if c == "^2":
            add(ideas, a[0]); add(minds, a[1])
        elif c == "^3":
            add(minds, a[0]); add(ideas, a[1])
        elif c == "^6":
            add(ideas, a[0])
            for x in a[1]:
                add(parts, x)
        else:
            add(ideas, a[0]); add(ideas, a[1]); add(minds, a[2])
    return minds, ideas, parts


def build_record(seed_stream, split, fam, qfam, idx):
    """One accepted PATH B record (or None if internal constraints fail)."""
    rng = HashPRNG(f"PATHB|{seed_stream}|{split}|{fam}|{qfam}|{idx}")
    ops, spec = build_graph(rng, split, qfam)
    try:
        answer, used = solve(ops, spec)
    except AssertionError:
        return None
    assert answer == spec["answer"], "solver/spec disagreement"
    clauses = [render_clause(rng, c, a, fam) for c, a in ops]
    question = render_question(rng, spec, fam)
    minds, ideas, parts = entities_of(ops)
    cands = minds + ideas + parts
    # CANDIDATE-ORDER LAW: per-passage seeded shuffle
    crng = HashPRNG(f"PATHB_CAND|{seed_stream}|{split}|{fam}|{qfam}|{idx}")
    for a_ in range(len(cands) - 1, 0, -1):
        b_ = crng.randbelow(a_ + 1)
        cands[a_], cands[b_] = cands[b_], cands[a_]
    return {"passage_id": f"{split[0]}{fam}{idx:06d}", "split": split,
            "family": fam, "question_type": qfam,
            "clauses": [{"text": t, "op_index": k}
                        for k, t in enumerate(clauses)],
            "text": " ".join(clauses),
            "question": question, "answer": answer,
            "candidates": cands,
            "ops": [[c, list(a) if not isinstance(a[-1], tuple) else
                     [a[0], list(a[1])]] if c == "^6" else [c, list(a)]
                    for c, a in ops],
            "anchors": spec["anchors"],
            "edge_trace": used,
            "final_class": FINAL_CLASS[qfam],
            "idea_labels": [c for c, _ in ops]}


# ---- frozen S-ALT50 corruption map (dose arm; owner D1) ---------------------
def alt50_class(passage_id, clause_idx, true_cls):
    """50% exact / 50% deterministically corrupted+balanced. Frozen map."""
    r = HashPRNG(f"ALT50|{passage_id}|{clause_idx}")
    if r.randbelow(2) == 0:
        return true_cls
    others = [c for c in CLASSES if c != true_cls]
    return others[r.randbelow(3)]
