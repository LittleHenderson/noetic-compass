"""tier_c_controls.py -- Tier C matched relational control pool (G-C0-5).

Generates, BEFORE any neural result, >= 1000 structurally matched, pairwise
non-isomorphic candidate relation structures, none isomorphic to R_CAS
(owner ruling section 4). Hard-matched statistics: tensor dimensions,
defined-cell count, diagonal-defined count, row/column degree multisets,
result-class frequencies, mediator frequencies, dual-pair count, sign
multiset, dual-present count, M-rank, walk-count vector (lengths 2-4),
automorphism-group size (= 1).

R-RANDOM (classification: RELATIONAL_MISINFORMATION_CONTROL -- it is wrong
relational information, NOT the CAS-specificity control) is the pool entry
with the smallest SHA-256 of its canonical form: a frozen selection law,
blind to any neural result.

Also freezes the R-CORRUPTED50 builder (C2 misinformation-dose arm): a
hash-keyed map corrupting each cell's typed content with probability 1/2 --
registered now so the table cannot be tuned later.

Development-only, non-claim-bearing. CPU.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "cjt_gate1a_static_neural_v1"
sys.path.insert(0, str(PKG))
from exec.prng import HashPRNG  # noqa: E402

import tier_c_structure as ts  # noqa: E402

CLASSES = ts.CLASSES
POOL_TARGET = 1000


# ---- assembly of one candidate structure ------------------------------------
def assemble(mask_cells, rt_assign, mt_assign, dual_pair, sign_orient):
    """mask_cells: ordered tuple of 4 (a,b) defined cells; rt/mt_assign:
    tuples of types aligned with mask_cells; dual_pair: frozenset of 2
    classes; sign_orient: (pos_class, neg_class) within the dual pair."""
    cells = {}
    defined = dict(zip(mask_cells, zip(rt_assign, mt_assign)))
    for a in CLASSES:
        for b in CLASSES:
            key = f"{a}|{b}"
            if (a, b) in defined:
                rt, mt = defined[(a, b)]
                cells[key] = {"M": 1, "status": "CONTROL",
                              "result_type": rt, "mediator_type": mt,
                              "source_rule": "CONTROL_POOL_GENERATED",
                              "derivation": "matched control; no CAS content"}
            else:
                cells[key] = {"M": 0, "status": "UNDEFINED",
                              "result_type": "UNDEFINED",
                              "mediator_type": "UNDEFINED",
                              "source_rule": "CONTROL_POOL_GENERATED",
                              "derivation": "undefined cell"}
    pos, neg = sign_orient
    return {"structure_id": "R_CONTROL", "non_claim_bearing": True,
            "classes": list(CLASSES), "cells": cells,
            "J": {"pair": {f"{a}|{b}":
                           ("SAME" if a == b else
                            "DUAL" if frozenset({a, b}) == dual_pair
                            else "UNDEFINED")
                           for a in CLASSES for b in CLASSES},
                  "sign": {c: ("POS" if c == pos else
                               "NEG" if c == neg else "NEUTRAL")
                           for c in CLASSES},
                  "dual_present": {c: c in dual_pair for c in CLASSES},
                  "source_rule": "CONTROL_POOL_GENERATED"}}


# ---- pool generation --------------------------------------------------------
def _mask_candidates(target_stats):
    """All defined-cell 0/1 masks matching the M-plane statistics of
    R_CAS (cell count taken from the stats, never hardcoded)."""
    out = []
    for cells in itertools.combinations(
            [(a, b) for a in CLASSES for b in CLASSES],
            target_stats["n_defined"]):
        rows = sorted(sum(1 for (a, _) in cells if a == c) for c in CLASSES)
        cols = sorted(sum(1 for (_, b) in cells if b == c) for c in CLASSES)
        diag = sum(1 for (a, b) in cells if a == b)
        if rows != target_stats["row_degree_multiset"]:
            continue
        if cols != target_stats["col_degree_multiset"]:
            continue
        if diag != target_stats["diag_defined"]:
            continue
        m = [[0] * 4 for _ in range(4)]
        for (a, b) in cells:
            m[ts.CIDX[a]][ts.CIDX[b]] = 1
        if ts._rank01([[float(v) for v in r] for r in m]) != \
                target_stats["m_rank"]:
            continue
        walks, p = [], m
        for _ in (2, 3, 4):
            p = ts._mat_mul(p, m)
            walks.append(sum(sum(r) for r in p))
        if walks != target_stats["walk_counts_2_3_4"]:
            continue
        out.append(cells)
    return out


def _multiset_perms(items):
    return sorted(set(itertools.permutations(items)))


# ---- fast tuple encoding (permutation action = index remap) -----------------
def encode(struct):
    """Compact hashable code of the full typed structure: 16 cell tuples
    (M, rt_idx, mt_idx, jp_idx) row-major + 4 class tuples (sign, dual)."""
    cellc = tuple(
        (ts.cell(struct, a, b)["M"],
         ts.RESULT_TYPES.index(ts.cell(struct, a, b)["result_type"]),
         ts.MEDIATOR_TYPES.index(ts.cell(struct, a, b)["mediator_type"]),
         ts.J_PAIR_TYPES.index(struct["J"]["pair"][f"{a}|{b}"]))
        for a in CLASSES for b in CLASSES)
    classc = tuple(
        (ts.SIGN_TYPES.index(struct["J"]["sign"][c]),
         int(struct["J"]["dual_present"][c])) for c in CLASSES)
    return (cellc, classc)


def _encode_parts(cells4, rt, mt, dual_pair, orient):
    """encode() without assembling a structure dict (fast path)."""
    defined = {(ts.CIDX[a], ts.CIDX[b]): (ts.RESULT_TYPES.index(r),
                                          ts.MEDIATOR_TYPES.index(m))
               for (a, b), r, m in zip(cells4, rt, mt)}
    dp = {ts.CIDX[c] for c in dual_pair}
    pos, neg = ts.CIDX[orient[0]], ts.CIDX[orient[1]]
    cellc = []
    for i in range(4):
        for j in range(4):
            m_bit = 1 if (i, j) in defined else 0
            r_i, m_i = defined.get((i, j), (3, 3))     # 3 = UNDEFINED
            jp = 0 if i == j else (1 if {i, j} == dp else 2)
            cellc.append((m_bit, r_i, m_i, jp))
    classc = tuple((0 if i == pos else 1 if i == neg else 2,
                    1 if i in dp else 0) for i in range(4))
    return (tuple(cellc), classc)


def _permute_code(code, perm):
    """Code of the consistently renamed structure: new (i,j) = old
    (inv[i], inv[j]); new class i = old class inv[i]."""
    cellc, classc = code
    inv = [0] * 4
    for i, p in enumerate(perm):
        inv[p] = i
    new_cells = tuple(cellc[inv[i] * 4 + inv[j]]
                      for i in range(4) for j in range(4))
    new_class = tuple(classc[inv[i]] for i in range(4))
    return (new_cells, new_class)


_PERMS = list(itertools.permutations(range(4)))


def canonical_code(code):
    return min(_permute_code(code, p) for p in _PERMS)


def automorphism_count(code):
    return sum(1 for p in _PERMS if _permute_code(code, p) == code)


def build_pool(r_cas, inject=None):
    """The frozen matched control pool. inject: optional extra candidate
    (cells4, rt, mt, dual_pair, orient) tuples prepended BEFORE filtering
    (used only by mutation M17)."""
    stats = ts.structure_stats(r_cas)
    cas_canon = canonical_code(encode(r_cas))
    rt_opts = _multiset_perms(stats["result_type_multiset"])
    mt_opts = _multiset_perms(stats["mediator_type_multiset"])
    duals = [frozenset(p) for p in itertools.combinations(CLASSES, 2)]
    masks = _mask_candidates(stats)
    pool, seen = [], set()
    rejected = {"isomorphic_to_cas": 0, "nontrivial_automorphism": 0,
                "duplicate_class": 0}
    candidates = list(inject) if inject else []
    for cells in masks:
        for rt in rt_opts:
            for mt in mt_opts:
                for dp in duals:
                    a, b = sorted(dp)
                    for orient in ((a, b), (b, a)):
                        candidates.append((cells, rt, mt, dp, orient))
    for parts in candidates:
        code = _encode_parts(*parts)
        if automorphism_count(code) != 1:
            rejected["nontrivial_automorphism"] += 1
            continue
        canon = canonical_code(code)
        if canon == cas_canon:
            rejected["isomorphic_to_cas"] += 1
            continue
        if canon in seen:
            rejected["duplicate_class"] += 1
            continue
        seen.add(canon)
        pool.append({"canonical_sha256": hashlib.sha256(
            json.dumps(canon).encode()).hexdigest(), "parts": parts})
    pool.sort(key=lambda e: e["canonical_sha256"])
    r_random = None
    if pool:
        r_random = assemble(*pool[0]["parts"])
        r_random["structure_id"] = "R_RANDOM_v1"
    return {"pool_id": "TIER_C_CONTROL_POOL_v1", "non_claim_bearing": True,
            "target": POOL_TARGET, "pool_size": len(pool),
            "sufficient": len(pool) >= POOL_TARGET,
            "matched_stats": stats, "mask_candidates": len(masks),
            "candidates_enumerated": len(candidates),
            "rejected": rejected,
            "r_random_selection_law": "pool entry with the smallest SHA-256 "
                                      "of its canonical CODE (the fast "
                                      "tuple encoding's lexicographic "
                                      "minimum over the 24 renamings -- "
                                      "equivalent as an isomorphism "
                                      "invariant to ts.canonical_form's "
                                      "phi-table form but a different "
                                      "byte serialization); frozen, blind "
                                      "to any neural result. The law pins "
                                      "the ISOMORPHISM CLASS; the labelled "
                                      "representative consumed by training "
                                      "is that class's first-enumerated "
                                      "assembly (deterministic enumeration "
                                      "order, disclosed here).",
            "r_random_canonical_sha256":
                pool[0]["canonical_sha256"] if pool else None,
            "r_random_classification": "RELATIONAL_MISINFORMATION_CONTROL",
            "pool_shas": [e["canonical_sha256"] for e in pool]}, r_random, \
        pool


# ---- R-CORRUPTED50 (C2 misinformation-dose arm; law frozen now) -------------
def build_r_corrupted50(r_cas):
    """Hash-keyed 50% CELL-TRANSPLANT corruption of R_CAS (v2 law, fixing
    two C0-review-confirmed defects of v1: v1 always flipped M so the
    corrupted table had ~3x the defined-cell density -- wrongness
    confounded with density -- and v1 never touched the J sign/dual
    planes, leaving 8/20 phi dims faithful CAS content).

    v2 law, per plane, all HashPRNG-frozen:
      * cells: for each ordered cell, with p=1/2 replace its full typed
        content (M, result_type, mediator_type) by the content of a
        uniformly drawn DIFFERENT R_CAS cell. Replacement content is
        always a legal cell vector, and the expected defined-cell density
        is preserved (each corrupted cell draws M=1 with the table's own
        marginal 4/16 = 1/4).
      * J.pair: with p=1/2 per entry, replace by another J_PAIR_TYPE.
      * J.sign: with p=1/2 per class, replace by another sign.
      * J.dual_present: with p=1/2 per class, flip.
    Never called a half-dose: this is the WRONGNESS axis, separated from
    the attenuation axis by owner ruling."""
    src = json.loads(json.dumps(r_cas))
    src["structure_id"] = "R_CORRUPTED50_v2"
    all_cells = [f"{a}|{b}" for a in CLASSES for b in CLASSES]
    donor_pool = {k: dict(r_cas["cells"][k]) for k in all_cells}
    n_cells = 0
    for a in CLASSES:
        for b in CLASSES:
            key = f"{a}|{b}"
            r = HashPRNG(f"TIERC_CORRUPT50V2|CELL|{key}")
            if r.randbelow(2) == 0:
                continue
            n_cells += 1
            donors = [k for k in all_cells if k != key]
            donor = donor_pool[donors[r.randbelow(len(donors))]]
            c = src["cells"][key]
            c["M"] = donor["M"]
            c["result_type"] = donor["result_type"]
            c["mediator_type"] = donor["mediator_type"]
            c["status"] = "CORRUPTED"
            c["source_rule"] = "TIERC_CORRUPT50V2_CELL_TRANSPLANT"
    n_jp = n_sign = n_dual = 0
    for a in CLASSES:
        for b in CLASSES:
            key = f"{a}|{b}"
            r = HashPRNG(f"TIERC_CORRUPT50V2|JPAIR|{key}")
            if r.randbelow(2) == 1:
                n_jp += 1
                jp = src["J"]["pair"][key]
                others = [t for t in ts.J_PAIR_TYPES if t != jp]
                src["J"]["pair"][key] = others[r.randbelow(len(others))]
    for cclass in CLASSES:
        r = HashPRNG(f"TIERC_CORRUPT50V2|SIGN|{cclass}")
        if r.randbelow(2) == 1:
            n_sign += 1
            sg = src["J"]["sign"][cclass]
            others = [t for t in ts.SIGN_TYPES if t != sg]
            src["J"]["sign"][cclass] = others[r.randbelow(len(others))]
        r = HashPRNG(f"TIERC_CORRUPT50V2|DUAL|{cclass}")
        if r.randbelow(2) == 1:
            n_dual += 1
            src["J"]["dual_present"][cclass] = \
                not src["J"]["dual_present"][cclass]
    src["corruption_counts"] = {"cells_of_16": n_cells,
                                "j_pair_of_16": n_jp,
                                "sign_of_4": n_sign, "dual_of_4": n_dual}
    src["defined_cell_density"] = sum(
        c["M"] for c in src["cells"].values())
    return src
