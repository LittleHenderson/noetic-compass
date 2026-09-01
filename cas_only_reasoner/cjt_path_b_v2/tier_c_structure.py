"""tier_c_structure.py -- Tier C frozen relation algebra R = (M, C, J).

Derives R_CAS deterministically from ONLY two registered sources:
  1. the frozen solver rules in pathb_core.solve() for the three RETAINED
     primary families (QB_REL, QB_COMP, QB_INT; QB_ORD excluded -- family
     dropped, final for this dataset version);
  2. the CAS structural invariants of the canonical layer (CO-2<->CO-3
     involution; the duals of ^6 (CO-5) and ^8 (CO-9) absent from the
     operation vocabulary; ^2/^3 orientation signs from the canonical
     definitions "affinity/attracted" vs "adverse/repelled").

Every cell carries {value, status: DERIVED|UNDEFINED, source_rule,
derivation}. No continuous strengths anywhere (owner ruling section 2).

Also: the frozen typed pair encoding phi(a,b) (20 binary dims, shared by
every transform and every R-variant), the automorphism enumeration over all
24 class permutations, structural statistics for control matching, and the
R-EMPIRICAL builder (train-trace estimation, J plane carries NO information).

Development-only, non-claim-bearing.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

CLASSES = ("^2", "^3", "^6", "^8")
CIDX = {c: k for k, c in enumerate(CLASSES)}

RESULT_TYPES = ("IDEA", "PART_SET", "PART", "UNDEFINED")
MEDIATOR_TYPES = ("MIND", "IDEA", "PART", "UNDEFINED")
J_PAIR_TYPES = ("SAME", "DUAL", "UNDEFINED")
SIGN_TYPES = ("POS", "NEG", "NEUTRAL")

# ---- R_CAS derivation (typed, per-cell sourced) -----------------------------
# Solver rule IDs cite pathb_core.py solve() line ranges (frozen file).
_DERIVED_CELLS = {
    ("^3", "^2"): {
        "result_type": "IDEA", "mediator_type": "MIND",
        "source_rule": "SOLVE_QB_REL (pathb_core.py:244-251)",
        "derivation": "REL: the unique ^3(m1,x) clause selects mind m1 via "
                      "its idea-object x; the unique ^2(iA,m1) clause with "
                      "object m1 yields answer idea iA. Ordered composition "
                      "^3-then-^2 bridged by the MIND; result is an IDEA."},
    ("^2", "^8"): {
        "result_type": "IDEA", "mediator_type": "MIND",
        "source_rule": "SOLVE_QB_COMP (pathb_core.py:252-259)",
        "derivation": "COMP: the unique ^2(x,m1) clause with subject-idea x "
                      "selects mind m1 via its object slot; the unique "
                      "^8(a,b,m1) clause with mind m1 yields answer idea b. "
                      "Ordered composition ^2-then-^8 bridged by the MIND; "
                      "result is an IDEA."},
    ("^2", "^6"): {
        "result_type": "PART_SET", "mediator_type": "IDEA",
        "source_rule": "SOLVE_QB_INT step 1-2 (pathb_core.py:260-267)",
        "derivation": "INT: the unique ^2(i2,m1) clause with object m1 "
                      "yields idea i2; the ^6(i2,parts) clause headed by i2 "
                      "yields its part set. Ordered composition ^2-then-^6 "
                      "bridged by the IDEA; result is a PART_SET."},
    ("^6", "^6"): {
        "result_type": "PART", "mediator_type": "PART",
        "source_rule": "SOLVE_QB_INT step 3 (pathb_core.py:268-270)",
        "derivation": "INT join: two ^6 part sets intersect to the unique "
                      "shared PART (six[i1] & six[i2]). The join is "
                      "order-symmetric and sits on the diagonal cell."},
}

_QB_ORD_EXCLUSION = ("QB_ORD's solver rule (pathb_core.py:271-282) is "
                     "EXCLUDED: the family is dropped (final for this "
                     "dataset version, owner ruling 2026-09-01 section 7) "
                     "and its side condition is discourse order, which is "
                     "not relational-algebra content.")

_J_SOURCE = ("CAS structural invariants (canonical layer): involution pair "
             "CO-2<->CO-3; duals of ^6 (CO-5) and ^8 (CO-9) absent from the "
             "4-class operation vocabulary; signs from the canonical "
             "definitions of ^2 (affinity for / attracted toward) and ^3 "
             "(adverse to / repelled by).")

SIGN = {"^2": "POS", "^3": "NEG", "^6": "NEUTRAL", "^8": "NEUTRAL"}
DUAL_PRESENT = {"^2": True, "^3": True, "^6": False, "^8": False}
DUAL_PAIRS = frozenset({frozenset({"^2", "^3"})})


def j_pair(a, b):
    if a == b:
        return "SAME"
    if frozenset({a, b}) in DUAL_PAIRS:
        return "DUAL"
    return "UNDEFINED"


def build_r_cas():
    """The frozen R_CAS structure dict (typed, fully sourced)."""
    cells = {}
    for a in CLASSES:
        for b in CLASSES:
            key = f"{a}|{b}"
            if (a, b) in _DERIVED_CELLS:
                d = _DERIVED_CELLS[(a, b)]
                cells[key] = {"M": 1, "status": "DERIVED",
                              "result_type": d["result_type"],
                              "mediator_type": d["mediator_type"],
                              "source_rule": d["source_rule"],
                              "derivation": d["derivation"]}
            else:
                cells[key] = {"M": 0, "status": "UNDEFINED",
                              "result_type": "UNDEFINED",
                              "mediator_type": "UNDEFINED",
                              "source_rule": "NO_SOLVER_RULE",
                              "derivation": "no solver rule composes this "
                                            "ordered pair; typed UNDEFINED, "
                                            "not a silent numerical zero"}
    return {"structure_id": "R_CAS_v1", "non_claim_bearing": True,
            "classes": list(CLASSES), "cells": cells,
            "J": {"pair": {f"{a}|{b}": j_pair(a, b)
                           for a in CLASSES for b in CLASSES},
                  "sign": dict(SIGN),
                  "dual_present": {c: DUAL_PRESENT[c] for c in CLASSES},
                  "source_rule": _J_SOURCE},
            "qb_ord_exclusion": _QB_ORD_EXCLUSION,
            "derivation_sources": ["pathb_core.solve() retained families",
                                   "CAS structural invariants (canonical)"]}


# ---- generic structure accessors (work for R_CAS, controls, R_EMPIRICAL) ----
def cell(struct, a, b):
    return struct["cells"][f"{a}|{b}"]


def m_of(struct, a, b):
    return cell(struct, a, b)["M"]


def phi(struct, a, b):
    """Frozen typed pair encoding: 20 binary dims. Shared by all transforms
    and all R-variants. STRUCTURE_VIEW_MUST_CONTAIN_M: dim 0 is the M bit."""
    c = cell(struct, a, b)
    j = struct["J"]
    v = [float(c["M"])]
    v += [1.0 if c["result_type"] == t else 0.0 for t in RESULT_TYPES]
    v += [1.0 if c["mediator_type"] == t else 0.0 for t in MEDIATOR_TYPES]
    jp = j["pair"][f"{a}|{b}"]
    v += [1.0 if jp == t else 0.0 for t in J_PAIR_TYPES]
    v += [1.0 if j["sign"][a] == t else 0.0 for t in SIGN_TYPES]
    v += [1.0 if j["sign"][b] == t else 0.0 for t in SIGN_TYPES]
    v += [1.0 if j["dual_present"][a] else 0.0]
    v += [1.0 if j["dual_present"][b] else 0.0]
    assert len(v) == 20
    return v


PHI_DIM = 20


def phi_table(struct):
    """4x4 -> 20 lookup as nested lists indexed by CIDX."""
    return [[phi(struct, a, b) for b in CLASSES] for a in CLASSES]


# ---- permutation action + automorphisms -------------------------------------
def permute_structure(struct, perm):
    """perm: tuple of 4 ints, class i -> class perm[i]. Returns the
    consistently renamed structure (every class-indexed axis permuted)."""
    pmap = {CLASSES[i]: CLASSES[perm[i]] for i in range(4)}
    inv = {v: k for k, v in pmap.items()}
    cells = {}
    for a in CLASSES:
        for b in CLASSES:
            src = cell(struct, inv[a], inv[b])
            cells[f"{a}|{b}"] = dict(src)
    j = struct["J"]
    return {"structure_id": struct["structure_id"] + "|perm",
            "non_claim_bearing": True, "classes": list(CLASSES),
            "cells": cells,
            "J": {"pair": {f"{a}|{b}": j["pair"][f"{inv[a]}|{inv[b]}"]
                           for a in CLASSES for b in CLASSES},
                  "sign": {c: j["sign"][inv[c]] for c in CLASSES},
                  "dual_present": {c: j["dual_present"][inv[c]]
                                   for c in CLASSES},
                  "source_rule": j.get("source_rule", "")}}


def structures_equal(s1, s2):
    """Typed equality over every plane phi sees (M, result, mediator, J)."""
    diffs = []
    for a in CLASSES:
        for b in CLASSES:
            if phi(s1, a, b) != phi(s2, a, b):
                diffs.append(f"{a}|{b}")
    return len(diffs) == 0, diffs


def automorphism_report(struct):
    """All 24 perms; which preserve the structure. Raw violations persisted."""
    rows = []
    auts = []
    for perm in itertools.permutations(range(4)):
        ps = permute_structure(struct, perm)
        eq, diffs = structures_equal(struct, ps)
        rows.append({"perm": list(perm), "is_automorphism": eq,
                     "violated_cells": diffs})
        if eq:
            auts.append(list(perm))
    return {"automorphisms": auts, "group_size": len(auts),
            "trivial": auts == [[0, 1, 2, 3]], "per_perm": rows}


def join_cell_counterfactual(struct):
    """Registered disclosure (C0 review): M-only triviality depends on the
    (^6,^6) join cell -- a symmetric set-intersection recorded on the
    diagonal, categorically unlike the three sequential bridged cells.
    This computes the automorphism group with that cell removed, showing
    (a) the M-only justification of STRUCTURE_VIEW_MUST_CONTAIN_M weakens
    to {identity, ^6<->^8} without it, while (b) the FULL structure stays
    trivial via the C plane."""
    import copy
    cut = copy.deepcopy(struct)
    cut["cells"]["^6|^6"] = {"M": 0, "status": "UNDEFINED",
                             "result_type": "UNDEFINED",
                             "mediator_type": "UNDEFINED",
                             "source_rule": "COUNTERFACTUAL_REMOVED",
                             "derivation": "join cell removed for the "
                                           "dependency disclosure"}
    m_only = [[m_of(cut, a, b) for b in CLASSES] for a in CLASSES]
    m_auts = []
    for perm in itertools.permutations(range(4)):
        inv = [0] * 4
        for i, p in enumerate(perm):
            inv[p] = i
        if all(m_only[inv[i]][inv[j]] == m_only[i][j]
               for i in range(4) for j in range(4)):
            m_auts.append(list(perm))
    full = automorphism_report(cut)
    return {"disclosure": "M-only triviality depends on the (^6,^6) join "
                          "cell; full-R triviality is robust to its removal "
                          "via the C plane",
            "m_only_automorphisms_without_join": m_auts,
            "full_structure_automorphisms_without_join":
                full["automorphisms"],
            "full_structure_trivial_without_join": full["trivial"]}


# ---- structural statistics (for control matching) ---------------------------
def m_matrix(struct):
    return [[m_of(struct, a, b) for b in CLASSES] for a in CLASSES]


def _mat_mul(x, y):
    n = len(x)
    return [[sum(x[i][k] * y[k][j] for k in range(n)) for j in range(n)]
            for i in range(n)]


def _rank01(m):
    """Rank over the rationals via fraction-free Gaussian elimination."""
    a = [row[:] for row in m]
    n = len(a)
    rank, r = 0, 0
    for c in range(n):
        piv = next((i for i in range(r, n) if a[i][c] != 0), None)
        if piv is None:
            continue
        a[r], a[piv] = a[piv], a[r]
        for i in range(n):
            if i != r and a[i][c] != 0:
                f = a[i][c] / a[r][c]
                a[i] = [a[i][j] - f * a[r][j] for j in range(n)]
        r += 1
        rank += 1
    return rank


def structure_stats(struct):
    m = m_matrix(struct)
    defined = [(a, b) for a in CLASSES for b in CLASSES if m_of(struct, a, b)]
    rows = sorted(sum(m[i]) for i in range(4))
    cols = sorted(sum(m[i][j] for i in range(4)) for j in range(4))
    rts = sorted(cell(struct, a, b)["result_type"] for a, b in defined)
    mts = sorted(cell(struct, a, b)["mediator_type"] for a, b in defined)
    j = struct["J"]
    walks = []
    p = m
    for _ in (2, 3, 4):
        p = _mat_mul(p, m)
        walks.append(sum(sum(r) for r in p))
    return {"n_defined": len(defined),
            "diag_defined": sum(m[i][i] for i in range(4)),
            "row_degree_multiset": rows, "col_degree_multiset": cols,
            "result_type_multiset": rts, "mediator_type_multiset": mts,
            "n_dual_pairs": sum(1 for a in CLASSES for b in CLASSES
                                if a < b and j["pair"][f"{a}|{b}"] == "DUAL"),
            "sign_multiset": sorted(j["sign"].values()),
            "dual_present_count": sum(1 for c in CLASSES
                                      if j["dual_present"][c]),
            "m_rank": _rank01([[float(v) for v in r] for r in m]),
            "walk_counts_2_3_4": walks,
            "automorphism_group_size":
                automorphism_report(struct)["group_size"]}


def canonical_form(struct):
    """Canonical string: lexicographic minimum over the 24 renamings of the
    full phi table. Two structures are isomorphic iff forms are equal."""
    best = None
    for perm in itertools.permutations(range(4)):
        ps = permute_structure(struct, perm)
        s = json.dumps(phi_table(ps))
        if best is None or s < best:
            best = s
    return best


# ---- R_EMPIRICAL (train-trace estimation; J carries NO information) ---------
# Estimator law (C0 review fix -- the C plane is now GENUINELY estimated):
#  * ops arguments are flattened; a nested list argument is a syntactic
#    LIST product (observable JSON structure, no class semantics).
#  * the MEDIATOR of a composed pair is the literal shared entity between
#    the two traced clauses' arguments; its type is its membership in the
#    split's registered surface entity pools (MINDS/IDEAS/PARTS -> MIND/
#    IDEA/PART) -- an observable property of the dataset, not of the table.
#  * the RESULT of a final composition is the record's answer entity (typed
#    by pool); the result of a non-final step whose second clause carries a
#    LIST argument is that list -> PART_SET when its members are pool PARTs.
#  * ambiguity (no unique shared entity, unknown pool) fails closed.
def _flat_args(op):
    out = []
    for a in op[1]:
        if isinstance(a, list):
            out.extend(a)
        else:
            out.append(a)
    return out


def build_r_empirical(train_path):
    """M/C planes counted ONLY from train-split edge traces of the three
    retained primary families, typed by observable slot/pool structure (see
    estimator law above). The CAS composition table is never imported; the
    J plane is uninformative (all UNDEFINED / NEUTRAL / no duals)."""
    import pathb_core as pc
    pool_type = {}
    for e in pc.MINDS["train"]:
        pool_type[e] = "MIND"
    for e in pc.IDEAS["train"]:
        pool_type[e] = "IDEA"
    for e in pc.PARTS["train"]:
        pool_type[e] = "PART"
    counts = {}

    def bump(a, b, rt, mt):
        k = (a, b)
        counts.setdefault(k, {"n": 0, "result": {}, "mediator": {}})
        counts[k]["n"] += 1
        counts[k]["result"][rt] = counts[k]["result"].get(rt, 0) + 1
        counts[k]["mediator"][mt] = counts[k]["mediator"].get(mt, 0) + 1

    def pair(op1, op2, product):
        """Estimate one composed pair from the records themselves."""
        shared = set(_flat_args(op1)) & set(_flat_args(op2))
        assert len(shared) == 1, f"mediator not unique: {shared}"
        mt = pool_type[next(iter(shared))]
        if isinstance(product, list):
            assert all(pool_type[p] == "PART" for p in product)
            rt = "PART_SET"
        else:
            rt = {"MIND": "MIND", "IDEA": "IDEA",
                  "PART": "PART"}[pool_type[product]]
        bump(op1[0], op2[0], rt, mt)

    n_used = 0
    with open(train_path, encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if rec["question_type"] not in ("QB_REL", "QB_COMP", "QB_INT"):
                continue
            ops = rec["ops"]
            tr = rec["edge_trace"]
            q = rec["question_type"]
            n_used += 1
            if q in ("QB_REL", "QB_COMP"):
                pair(ops[tr[0]], ops[tr[1]], rec["answer"])
            else:                                   # QB_INT: [sel, six1, six2]
                list_arg = next(a for a in ops[tr[2]][1]
                                if isinstance(a, list))
                pair(ops[tr[0]], ops[tr[2]], list_arg)
                pair(ops[tr[1]], ops[tr[2]], rec["answer"])
    cells = {}
    for a in CLASSES:
        for b in CLASSES:
            key = f"{a}|{b}"
            if (a, b) in counts:
                c = counts[(a, b)]
                rt = max(c["result"], key=lambda k: (c["result"][k], k))
                mt = max(c["mediator"], key=lambda k: (c["mediator"][k], k))
                cells[key] = {"M": 1, "status": "DERIVED",
                              "result_type": rt, "mediator_type": mt,
                              "source_rule": "TRAIN_TRACE_COUNT "
                                             f"(n={c['n']}, "
                                             f"result_hist={c['result']}, "
                                             f"mediator_hist={c['mediator']})",
                              "derivation": "estimated from train edge "
                                            "traces; mediator = shared "
                                            "entity typed by surface pool, "
                                            "result = answer/list product "
                                            "typed by pool (estimator law); "
                                            "CAS table never imported"}
            else:
                cells[key] = {"M": 0, "status": "UNDEFINED",
                              "result_type": "UNDEFINED",
                              "mediator_type": "UNDEFINED",
                              "source_rule": "NOT_OBSERVED_IN_TRACES",
                              "derivation": "no train trace realizes this "
                                            "ordered pair"}
    return {"structure_id": "R_EMPIRICAL_v1", "non_claim_bearing": True,
            "classes": list(CLASSES), "cells": cells,
            "J": {"pair": {f"{a}|{b}": ("SAME" if a == b else "UNDEFINED")
                           for a in CLASSES for b in CLASSES},
                  "sign": {c: "NEUTRAL" for c in CLASSES},
                  "dual_present": {c: False for c in CLASSES},
                  "source_rule": "TRACE-DERIVED ONLY: duality and sign are "
                                 "not observable in edge traces; J carries "
                                 "no information by construction"},
            "n_trace_records_used": n_used}


def overlap_report(r_cas, r_emp):
    """Exact per-plane overlap between R_CAS and R_EMPIRICAL."""
    same_m, same_rt, same_mt, diff_cells = 0, 0, 0, []
    for a in CLASSES:
        for b in CLASSES:
            c1, c2 = cell(r_cas, a, b), cell(r_emp, a, b)
            same_m += int(c1["M"] == c2["M"])
            same_rt += int(c1["result_type"] == c2["result_type"])
            same_mt += int(c1["mediator_type"] == c2["mediator_type"])
            if (c1["M"], c1["result_type"], c1["mediator_type"]) != \
               (c2["M"], c2["result_type"], c2["mediator_type"]):
                diff_cells.append(f"{a}|{b}")
    j_equal = all(
        r_cas["J"]["pair"][f"{a}|{b}"] == r_emp["J"]["pair"][f"{a}|{b}"]
        for a in CLASSES for b in CLASSES) and \
        r_cas["J"]["sign"] == r_emp["J"]["sign"] and \
        r_cas["J"]["dual_present"] == r_emp["J"]["dual_present"]
    return {"m_cells_equal": same_m, "result_type_cells_equal": same_rt,
            "mediator_cells_equal": same_mt, "mc_diff_cells": diff_cells,
            "j_planes_equal": j_equal,
            "reading": "R_CAS vs R_EMPIRICAL differs exactly where the J "
                       "plane (duality/sign prior) and any non-trace-visible "
                       "C detail live -- the C2 contrast isolates that."}
