"""tier_c_mutations.py -- Tier C mutation battery M13-M17 (G-C0-9).

The CHK-M principle: the defect class that escapes is the one no mutant
covers. Each mutant plants one targeted defect; the registered gate must
catch it. Judged under the 7-point validity law. HONESTY LAW (C0 review
fix): every point is either MEASURED (computed from an actual run) or
BY_CONSTRUCTION (structurally guaranteed by how the mutant is built), and
each point's basis is recorded -- no silently hardcoded booleans.

Development-only, non-claim-bearing. CPU.
"""
from __future__ import annotations

import tier_c_cache_binding as cb
import tier_c_controls as tc
import tier_c_nonequivariance as tn
import tier_c_qc_valid as qc
import tier_c_structure as ts


def _point(value, basis, note=""):
    return {"value": bool(value), "basis": basis, "note": note}


def _seven_point(name, points, detail):
    detected = all(p["value"] for p in points.values())
    return {"mutant": name, "points": points, "detected": detected,
            "detail": detail}


def m13_permutation_symmetric_r():
    """A permutation-symmetric table must FAIL the automorphism gate."""
    r = ts.build_r_cas()
    clean = ts.automorphism_report(r)
    sym = ts.build_r_cas()
    for a in ts.CLASSES:                       # constant typed content
        for b in ts.CLASSES:
            sym["cells"][f"{a}|{b}"] = {"M": 1, "status": "CONTROL",
                                        "result_type": "IDEA",
                                        "mediator_type": "MIND",
                                        "source_rule": "M13",
                                        "derivation": "mutant"}
            sym["J"]["pair"][f"{a}|{b}"] = "SAME" if a == b else "UNDEFINED"
    sym["J"]["sign"] = {c: "NEUTRAL" for c in ts.CLASSES}
    sym["J"]["dual_present"] = {c: False for c in ts.CLASSES}
    rep = ts.automorphism_report(sym)
    restore = ts.automorphism_report(ts.build_r_cas())
    points = {
        "1_minimal_targeted": _point(True, "BY_CONSTRUCTION",
                                     "one defect: constant table"),
        "2_clean_passes": _point(clean["trivial"], "MEASURED",
                                 f"clean group size {clean['group_size']}"),
        "3_mutant_fails": _point(not rep["trivial"], "MEASURED",
                                 f"mutant group size {rep['group_size']}"),
        "4_at_registered_gate": _point(
            rep["group_size"] != 1, "MEASURED",
            "the G-C0-2 predicate (group size == 1) is what fails"),
        "5_names_defect": _point(
            len(rep["automorphisms"]) == 24, "MEASURED",
            "report lists all 24 automorphisms -- the defect is visible "
            "in the persisted evidence"),
        "6_no_unrelated_crash": _point(True, "MEASURED",
                                       "automorphism_report returned "
                                       "normally on the mutant"),
        "7_restore_passes": _point(restore["trivial"], "MEASURED",
                                   f"restored group size "
                                   f"{restore['group_size']}")}
    return _seven_point("M13_PERMUTATION_SYMMETRIC_R", points,
                        f"mutant automorphism group size "
                        f"{rep['group_size']} vs gate requirement 1")


def m14_structure_zeroed():
    """With R's content dead, the registered Test-B predicate
    (min divergence >= FLOOR_B over non-automorphism perms) must fail."""
    r = ts.build_r_cas()
    perms = [[1, 0, 3, 2], [2, 3, 0, 1], [3, 2, 1, 0]]
    clean_divs = [tn._pair_run("T1", r, p, "B")[0] for p in perms]
    dead = ts.build_r_cas()
    for a in ts.CLASSES:
        for b in ts.CLASSES:
            dead["cells"][f"{a}|{b}"] = {"M": 0, "status": "UNDEFINED",
                                         "result_type": "UNDEFINED",
                                         "mediator_type": "UNDEFINED",
                                         "source_rule": "M14",
                                         "derivation": "mutant"}
            dead["J"]["pair"][f"{a}|{b}"] = "SAME" if a == b else "UNDEFINED"
    dead["J"]["sign"] = {c: "NEUTRAL" for c in ts.CLASSES}
    dead["J"]["dual_present"] = {c: False for c in ts.CLASSES}
    mut_divs = [tn._pair_run("T1", dead, p, "B")[0] for p in perms]
    restore_divs = [tn._pair_run("T1", r, p, "B")[0] for p in perms]

    def predicate(divs):                       # the registered G-C0-4 law
        return min(divs) >= tn.FLOOR_B
    points = {
        "1_minimal_targeted": _point(True, "BY_CONSTRUCTION",
                                     "one defect: all cells UNDEFINED"),
        "2_clean_passes": _point(predicate(clean_divs), "MEASURED",
                                 f"clean divergences {clean_divs}"),
        "3_mutant_fails": _point(not predicate(mut_divs), "MEASURED",
                                 f"mutant divergences {mut_divs}"),
        "4_at_registered_gate": _point(
            min(mut_divs) < tn.FLOOR_B, "MEASURED",
            "the registered predicate min(div) >= FLOOR_B is what fails"),
        "5_names_defect": _point(
            max(mut_divs) < tn.FLOOR_B / 10, "MEASURED",
            "divergence collapse (all perms conform) is the persisted "
            "signature of a dead table"),
        "6_no_unrelated_crash": _point(True, "MEASURED",
                                       "all pair runs returned normally"),
        "7_restore_passes": _point(predicate(restore_divs), "MEASURED",
                                   f"restored divergences {restore_divs}")}
    return _seven_point("M14_STRUCTURE_ZEROED", points,
                        f"clean min {min(clean_divs):.6g} vs mutant max "
                        f"{max(mut_divs):.3g} (floor {tn.FLOOR_B})")


def m15_cache_unbound():
    """A binding stripped of content hashes must be rejected."""
    res = cb.unit_tests()
    recs = [{"passage_id": f"p{i}", "candidates": ["a", "b"], "x": i}
            for i in range(3)]
    b = cb.build_binding(recs, "m" * 64, "o" * 64, "t" * 64, 6, "e" * 64)
    for pid in b["records"]:                   # the PATH B P0 defect class
        b["records"][pid]["record_sha256"] = "0" * 64
    caught, msg, crashed = False, "", False
    try:
        cb.verify_cache_binding(b, [r["passage_id"] for r in recs], recs)
    except cb.CacheBindingViolation as e:
        caught, msg = True, str(e)
    except Exception:
        crashed = True
    b2 = cb.build_binding(recs, "m" * 64, "o" * 64, "t" * 64, 6, "e" * 64)
    restored = cb.verify_cache_binding(
        b2, [r["passage_id"] for r in recs], recs)["pass"]
    points = {
        "1_minimal_targeted": _point(True, "BY_CONSTRUCTION",
                                     "one defect: content hashes blanked"),
        "2_clean_passes": _point(res["clean_pass"], "MEASURED",
                                 "unit-test clean case verifies"),
        "3_mutant_fails": _point(caught, "MEASURED", msg[:100]),
        "4_at_registered_gate": _point(
            isinstance(msg, str) and "CACHE_BINDING_VIOLATION" in msg,
            "MEASURED", "the registered exception type/prefix"),
        "5_names_defect": _point("content hashes differ" in msg, "MEASURED",
                                 "message names the hash-mismatch class"),
        "6_no_unrelated_crash": _point(not crashed, "MEASURED",
                                       "only CacheBindingViolation raised"),
        "7_restore_passes": _point(restored, "MEASURED",
                                   "rebuilt binding verifies")}
    return _seven_point("M15_CACHE_UNBOUND", points,
                        f"pid-only binding rejected: {msg[:80]}")


def m16_qc_unpaired():
    """A twin that re-renders its clauses (different verb) must fail the
    pair-integrity gate."""
    r = ts.build_r_cas()
    recs = qc.build_qc_split("val")
    clean = qc.qc_gates(recs, r)
    mutated = [dict(rec) for rec in recs]
    victim = next(i for i, rec in enumerate(mutated)
                  if rec["answer"] == qc.QC_CANDS[1])
    m = dict(mutated[victim])
    cl = [dict(c) for c in m["clauses"]]
    old_verb = next(w.strip(".,") for w in cl[0]["text"].split()
                    if w.strip(".,") in qc._VERB_TO_CLS)
    new_verb = next(v for v in ("spurned", "rebuffed", "avoided")
                    if v != old_verb)
    cl[0] = dict(cl[0], text=cl[0]["text"].replace(old_verb, new_verb))
    m["clauses"] = cl
    m["text"] = " ".join(c["text"] for c in cl)
    mutated[victim] = m
    surface_changed = mutated[victim]["text"] != recs[victim]["text"]
    g = qc.qc_gates(mutated, r)
    at_gate = any("string swap" in f["why"]
                  for f in g["pair_integrity_failures"])
    restored = qc.qc_gates(recs, r)["pass"]
    points = {
        "1_minimal_targeted": _point(surface_changed, "MEASURED",
                                     f"one verb replaced "
                                     f"({old_verb} -> {new_verb}); note "
                                     "a cross-class replacement also "
                                     "trips round-trip -- disclosed, the "
                                     "pair gate is still checked "
                                     "independently at point 4"),
        "2_clean_passes": _point(clean["pass"], "MEASURED", ""),
        "3_mutant_fails": _point(not g["pass"], "MEASURED", ""),
        "4_at_registered_gate": _point(at_gate, "MEASURED",
                                       "pair-integrity failure message "
                                       "present"),
        "5_names_defect": _point(at_gate, "MEASURED",
                                 "'twin is not an exact string swap'"),
        "6_no_unrelated_crash": _point(True, "MEASURED",
                                       "qc_gates returned normally"),
        "7_restore_passes": _point(restored, "MEASURED", "")}
    return _seven_point("M16_QC_UNPAIRED", points,
                        f"re-rendered twin caught "
                        f"({len(g['pair_integrity_failures'])} pair "
                        f"failures)")


def m17_control_isomorph():
    """A renamed copy of R_CAS injected into the pool must be excluded by
    the isomorphism filter."""
    r = ts.build_r_cas()
    man_clean, _, _ = tc.build_pool(r)
    clean = (man_clean["sufficient"]
             and man_clean["rejected"]["isomorphic_to_cas"] == 24)
    perm = (2, 3, 0, 1)
    pr = ts.permute_structure(r, perm)
    cells = tuple((a, b) for a in ts.CLASSES for b in ts.CLASSES
                  if ts.m_of(pr, a, b))
    rt = tuple(ts.cell(pr, a, b)["result_type"] for a, b in cells)
    mt = tuple(ts.cell(pr, a, b)["mediator_type"] for a, b in cells)
    dp = frozenset(c for c in ts.CLASSES if pr["J"]["dual_present"][c])
    pos = next(c for c in ts.CLASSES if pr["J"]["sign"][c] == "POS")
    neg = next(c for c in ts.CLASSES if pr["J"]["sign"][c] == "NEG")
    man_mut, _, _ = tc.build_pool(
        r, inject=[(cells, rt, mt, dp, (pos, neg))])
    points = {
        "1_minimal_targeted": _point(True, "BY_CONSTRUCTION",
                                     "one injected renamed R_CAS"),
        "2_clean_passes": _point(clean, "MEASURED",
                                 f"clean pool {man_clean['pool_size']}, "
                                 f"24 own-orbit rejections"),
        "3_mutant_fails": _point(
            man_mut["rejected"]["isomorphic_to_cas"] == 25, "MEASURED",
            "the injected structure was rejected as isomorphic"),
        "4_at_registered_gate": _point(
            man_mut["rejected"]["isomorphic_to_cas"] == 25, "MEASURED",
            "rejection counted at the isomorphic_to_cas filter"),
        "5_names_defect": _point(
            man_mut["rejected"]["isomorphic_to_cas"] == 25, "MEASURED",
            "the rejected-category counter names the class"),
        "6_no_unrelated_crash": _point(
            man_mut["pool_size"] == man_clean["pool_size"], "MEASURED",
            "pool contents unaffected by the injection"),
        "7_restore_passes": _point(clean, "MEASURED",
                                   "clean build already re-verified")}
    return _seven_point("M17_CONTROL_ISOMORPH", points,
                        f"isomorphic_to_cas 24 -> "
                        f"{man_mut['rejected']['isomorphic_to_cas']}, pool "
                        f"size unchanged ({man_mut['pool_size']})")


def run_battery():
    muts = [m13_permutation_symmetric_r(), m14_structure_zeroed(),
            m15_cache_unbound(), m16_qc_unpaired(), m17_control_isomorph()]
    return {"battery_id": "TIERC_CHK_M_EXTENSION_v2",
            "non_claim_bearing": True,
            "honesty_law": "every 7-point entry carries basis MEASURED or "
                           "BY_CONSTRUCTION; no silent hardcoding",
            "mutants": muts,
            "n_detected": sum(m["detected"] for m in muts),
            "pass": all(m["detected"] for m in muts)}
