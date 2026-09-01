"""tier_c_j_necessity.py -- does changing J ever change the correct answer?
(Owner ruling after C1: one CPU-only, $0 test before any further spend.)

WHY THIS INSTRUMENT EXISTS. The frozen symbolic solver in pathb_core.solve()
never consults R -- it is hand-written over clause classes and argument
slots. So "run the solver under J variants" is not directly executable, and
a naive reading ("perturb J, see if the GOLD changes") is degenerate: the
gold would not change under perturbations of M or C either, because the gold
does not read R at all.

The non-degenerate question is IDENTIFIABILITY:

    Does J carry information that an R-driven reasoner needs, over and above
    M, C, and the surface, in order to reach the correct answer?

So this module builds an R-DRIVEN solver -- one that computes the answer FROM
the table -- and then varies J underneath it. Three properties make the test
fair rather than rigged:

  1. VALIDITY GATE. Under the full frozen R the R-driven solver must
     reproduce pathb_core.solve()'s gold on 100% of records. If it does not,
     the instrument is broken and the test is void.
  2. J IS GIVEN EVERY CHANCE. The solver consults J at the one decision
     point where J could legitimately bind -- assigning which named
     operation class is the SELECTOR and which is the FINAL step -- and it
     is asked FIRST, before M's asymmetry is consulted. If J is ever
     informative, this design finds it.
  3. THE REDUNDANT-VS-USELESS DISTINCTION. A supplementary pass symmetrizes
     M (destroying the asymmetry that currently fixes the order) and asks
     whether J alone can still recover the correct order. That separates
     "J is useless" from "J is redundant given M" -- different findings.

Entity typing is by surface pool membership (MINDS / IDEAS / PARTS), the
same observable typing used to build R_EMPIRICAL. No hardcoded solver rule
is imported into the R-driven path.

Runs on train + the C1 val half ONLY. The C2_STRUCTURE_EVAL half is not
read. Development-only, non-claim-bearing. CPU, $0.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "cjt_gate1a_static_neural_v1"))

import pathb_core as pc  # noqa: E402
import tier_c_structure as ts  # noqa: E402
from tier_c_c1_split import c1_side  # noqa: E402

PRIMARY = ("QB_REL", "QB_COMP", "QB_INT")

# Which operation classes each question frame NAMES on the surface. This is
# read off the question templates in pathb_core.Q_FRAMES, not invented:
#   QB_REL   "which idea {v2} the mind that {v3} {x}?"        -> ^2, ^3
#   QB_COMP  "which idea was {v8} for the mind that {x} {v2}?"-> ^8, ^2
#   QB_INT   "which part belonged to both {i1} and the idea
#             that {v2} {m}?"  (+ "which part" implies ^6)    -> ^2, ^6
NAMED_CLASSES = {"QB_REL": ("^2", "^3"), "QB_COMP": ("^8", "^2"),
                 "QB_INT": ("^2", "^6")}


def pool_type(split):
    t = {}
    for e in pc.MINDS[split]:
        t[e] = "MIND"
    for e in pc.IDEAS[split]:
        t[e] = "IDEA"
    for e in pc.PARTS[split]:
        t[e] = "PART"
    return t


def flat_args(op):
    out = []
    for a in op[1]:
        if isinstance(a, list):
            out.extend(a)
        else:
            out.append(a)
    return out


# ---- the R-driven solver ---------------------------------------------------
def order_from_J(R, ca, cb):
    """J's OWN answer to 'which class is the selector?', asked FIRST.
    Registered rule, derived only from J's declared content: a class that
    HAS a dual is an involution member and plays the selecting role; a
    dual-less class is terminal. If both have duals, the NEGATIVE-signed one
    selects (aversion narrows, affinity delivers). Returns an ordered pair,
    or None when J cannot decide."""
    J = R["J"]
    da, db = J["dual_present"][ca], J["dual_present"][cb]
    if da != db:
        return (ca, cb) if da else (cb, ca)
    if da and db:
        sa, sb = J["sign"][ca], J["sign"][cb]
        if sa == "NEG" and sb != "NEG":
            return (ca, cb)
        if sb == "NEG" and sa != "NEG":
            return (cb, ca)
    return None


def order_from_M(R, ca, cb):
    """M's answer: the ordered pair that is a DERIVED composition."""
    ab = ts.m_of(R, ca, cb) == 1
    ba = ts.m_of(R, cb, ca) == 1
    if ab and not ba:
        return (ca, cb)
    if ba and not ab:
        return (cb, ca)
    return None


def solve_with_R(rec, R, ptype, use_j=True, use_m=True):
    """Compute the answer FROM the table. Returns (answer, trace) or
    (None, reason). J is consulted FIRST when use_j, so if J is ever
    informative this solver uses it."""
    fam = rec["question_type"]
    ops = rec["ops"]
    ca, cb = NAMED_CLASSES[fam]
    order = None
    decided_by = None
    if use_j:
        order = order_from_J(R, ca, cb)
        decided_by = "J" if order else None
    if order is None and use_m:
        order = order_from_M(R, ca, cb)
        decided_by = "M" if order else None
    if order is None:
        return None, "ORDER_UNDETERMINED"
    c1, c2 = order
    cell = ts.cell(R, c1, c2)
    if cell["M"] != 1:
        return None, f"COMPOSITION_NOT_LICENSED:{c1}->{c2}"
    med_t = cell["mediator_type"]
    res_t = cell["result_type"]
    anchors = rec["anchors"]

    def slot_of_type(op, t):
        return [a for a in flat_args(op) if ptype.get(a) == t]

    # CLAUSE-GRAMMAR RULES (observable surface structure, NOT table content;
    # R is a relation algebra over CLASSES and legitimately says nothing
    # about which argument slot of a clause holds what):
    #  (g1) the SELECTING anchor is the anchor whose entity type differs
    #       from the composition's mediator type -- the mediator is what the
    #       two clauses share, so the anchor that picks the first clause is
    #       the other one;
    #  (g2) when several arguments carry the result type, the result is the
    #       LAST one in clause-argument order (a parser reading "A evoked B
    #       for M" sees B after A).
    sel_anchors = [a for a in anchors if ptype.get(a) != med_t]
    if not sel_anchors:
        sel_anchors = list(anchors)
    sels = [k for k, op in enumerate(ops)
            if op[0] == c1 and any(a in sel_anchors for a in flat_args(op))]
    if len(sels) != 1:
        return None, f"SELECTOR_NOT_UNIQUE:{len(sels)}"
    sel = sels[0]
    if fam == "QB_INT":
        # (^2,^6): bridge is the IDEA the mind is attracted to; then the
        # (^6,^6) diagonal join intersects that idea's parts with the
        # anchor idea's parts. result_type of (^6,^6) is PART.
        br = [a for a in slot_of_type(ops[sel], med_t) if a not in anchors]
        if len(br) != 1:
            return None, "BRIDGE_NOT_UNIQUE"
        i2 = br[0]
        join = ts.cell(R, c2, c2)
        if join["M"] != 1:
            return None, "JOIN_NOT_LICENSED"
        sets = {}
        for op in ops:
            if op[0] == c2:
                head = [a for a in flat_args(op) if ptype.get(a) == "IDEA"]
                members = [a for a in flat_args(op)
                           if ptype.get(a) == join["result_type"]]
                if head:
                    sets[head[0]] = set(members)
        i1 = [a for a in anchors if ptype.get(a) == "IDEA"]
        if len(i1) != 1 or i1[0] not in sets or i2 not in sets:
            return None, "JOIN_OPERANDS_MISSING"
        shared = sets[i1[0]] & sets[i2]
        if len(shared) != 1:
            return None, "JOIN_NOT_UNIQUE"
        return next(iter(shared)), {"order": [c1, c2],
                                    "decided_by": decided_by, "sel": sel}
    br = [a for a in slot_of_type(ops[sel], med_t) if a not in anchors] \
        or slot_of_type(ops[sel], med_t)
    if len(br) != 1:
        return None, f"BRIDGE_NOT_UNIQUE:{len(br)}"
    bridge = br[0]
    fins = [k for k, op in enumerate(ops)
            if op[0] == c2 and bridge in flat_args(op) and k != sel]
    if len(fins) != 1:
        return None, f"FINAL_NOT_UNIQUE:{len(fins)}"
    fin = fins[0]
    res = [a for a in flat_args(ops[fin])
           if ptype.get(a) == res_t and a != bridge and a not in anchors]
    if not res:
        return None, "RESULT_NOT_UNIQUE:0"
    return res[-1], {"order": [c1, c2], "decided_by": decided_by,   # (g2)
                     "sel": sel, "fin": fin,
                     "result_slot_candidates": len(res)}


# ---- the six registered J conditions ---------------------------------------
def j_variants(R):
    """The owner's six conditions. Only the J plane is touched; M and C are
    byte-identical across every variant."""
    out = {}
    out["1_full_M_C_J"] = copy.deepcopy(R)

    v = copy.deepcopy(R)                                   # 2. J removed
    for k in v["J"]["pair"]:
        a, b = k.split("|")
        v["J"]["pair"][k] = "SAME" if a == b else "UNDEFINED"
    v["J"]["sign"] = {c: "NEUTRAL" for c in ts.CLASSES}
    v["J"]["dual_present"] = {c: False for c in ts.CLASSES}
    out["2_J_removed"] = v

    v = copy.deepcopy(R)                                   # 3. sign flipped
    flip = {"POS": "NEG", "NEG": "POS", "NEUTRAL": "NEUTRAL"}
    v["J"]["sign"] = {c: flip[s] for c, s in v["J"]["sign"].items()}
    out["3_J_sign_flipped"] = v

    v = copy.deepcopy(R)                                   # 4. dual swapped
    for k in v["J"]["pair"]:
        a, b = k.split("|")
        if a != b:
            v["J"]["pair"][k] = "DUAL" if {a, b} == {"^6", "^8"} \
                else "UNDEFINED"
    v["J"]["dual_present"] = {c: c in ("^6", "^8") for c in ts.CLASSES}
    out["4_dual_relation_swapped"] = v

    v = copy.deepcopy(R)                                   # 5. wrong J
    for k in v["J"]["pair"]:
        a, b = k.split("|")
        if a != b:
            v["J"]["pair"][k] = "DUAL" if {a, b} == {"^2", "^6"} \
                else "UNDEFINED"
    v["J"]["dual_present"] = {c: c in ("^2", "^6") for c in ts.CLASSES}
    v["J"]["sign"] = {"^2": "NEG", "^3": "NEUTRAL", "^6": "POS",
                      "^8": "NEUTRAL"}
    out["5_wrong_J_inserted"] = v

    v = copy.deepcopy(R)                                   # 6. unrelated cell
    v["J"]["pair"]["^6|^8"] = "DUAL"                       # never queried
    out["6_unrelated_J_cell_changed"] = v
    return out


def symmetrized_M(R):
    """Destroy M's directional asymmetry on the queried pairs, so M can no
    longer fix the execution order. Used ONLY for the supplementary
    redundant-vs-useless analysis."""
    v = copy.deepcopy(R)
    for a in ts.CLASSES:
        for b in ts.CLASSES:
            if a == b:
                continue
            if ts.m_of(R, a, b) == 1 and ts.m_of(R, b, a) == 0:
                src = ts.cell(R, a, b)
                dst = v["cells"][f"{b}|{a}"]
                dst["M"] = 1
                dst["result_type"] = src["result_type"]
                dst["mediator_type"] = src["mediator_type"]
                dst["status"] = "SYMMETRIZED_FOR_ANALYSIS"
    return v


def load_records():
    """train (families A,B) + the C1 val half (family C). The
    C2_STRUCTURE_EVAL half is NOT read."""
    recs = []
    for split in ("train", "val"):
        p = HERE / "data" / f"{split}.jsonl"
        for line in p.read_text("utf-8").splitlines():
            if not line:
                continue
            r = json.loads(line)
            if r["question_type"] not in PRIMARY:
                continue
            if split == "val" and not c1_side(r["passage_id"]):
                continue          # C2 half never read
            r["_split"] = split
            recs.append(r)
    return recs


def run(records, R, ptype_by_split, **kw):
    ok = bad = 0
    answers = {}
    reasons = {}
    decided = {}
    for r in records:
        a, tr = solve_with_R(r, R, ptype_by_split[r["_split"]], **kw)
        answers[r["passage_id"]] = a
        if a is None:
            bad += 1
            reasons[tr] = reasons.get(tr, 0) + 1
        else:
            ok += 1
            if isinstance(tr, dict):
                d = tr.get("decided_by")
                decided[d] = decided.get(d, 0) + 1
    return answers, {"resolved": ok, "unresolved": bad,
                     "failure_reasons": reasons, "order_decided_by": decided}


def main():
    R = json.loads((HERE / "tier_c" / "R_CAS.json").read_text("utf-8"))
    records = load_records()
    ptype = {"train": pool_type("train"), "val": pool_type("val")}
    gold = {r["passage_id"]: r["answer"] for r in records}
    n = len(records)
    per_fam_n = {f: sum(1 for r in records if r["question_type"] == f)
                 for f in PRIMARY}
    print(f"records: {n} (train + C1 val half; C2 half NOT read) {per_fam_n}")

    # ---- VALIDITY GATE ----
    base_ans, base_stats = run(records, R, ptype)
    agree = sum(1 for p, a in base_ans.items() if a == gold[p])
    valid = agree == n
    print(f"[validity] R-driven solver reproduces gold on {agree}/{n} "
          f"({agree/n:.4f}) -> {'VALID' if valid else 'INSTRUMENT_BROKEN'}")
    print(f"           order decided by: {base_stats['order_decided_by']}")
    if not valid:
        print(f"           failures: {base_stats['failure_reasons']}")

    report = {"record_id": "TIER_C_J_NECESSITY", "non_claim_bearing": True,
              "n_records": n, "per_family_n": per_fam_n,
              "data_scope": "train + C1 val half; C2_STRUCTURE_EVAL not read",
              "validity_gate": {"agreement_with_gold": agree, "n": n,
                                "valid": valid,
                                "order_decided_by":
                                    base_stats["order_decided_by"],
                                "failure_reasons":
                                    base_stats["failure_reasons"]},
              "conditions": {}, "supplementary": {}}
    if not valid:
        report["status"] = "J_NECESSITY_INSTRUMENT_BROKEN"
        (HERE / "tier_c" / "J_NECESSITY_REPORT.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        print("\nSTATUS: J_NECESSITY_INSTRUMENT_BROKEN (test void)")
        return 1

    # ---- the six conditions, under BOTH solver precedences ----
    # J-FIRST is the deliberately J-favouring instrument (J gets every
    # chance). M-FIRST is the decisive control: if a solver that consults M
    # before J is INVARIANT across every J perturbation, then no J content
    # is needed to reach the correct answer, and any change seen under
    # J-FIRST is a property of trusting J, not of the task.
    print("\n[conditions] answers CHANGED vs condition 1 (only J differs)")
    print("             J-FIRST = J-favouring instrument | "
          "M-FIRST = decisive control")
    total_changed_jfirst = 0
    total_changed_mfirst = 0
    base_m, _ = run(records, R, ptype, use_j=False)
    for name, Rv in j_variants(R).items():
        ans, st = run(records, Rv, ptype)
        changed = sum(1 for p in base_ans if ans[p] != base_ans[p])
        wrong = sum(1 for p in ans if ans[p] != gold[p])
        ans_m, st_m = run(records, Rv, ptype, use_j=False)
        changed_m = sum(1 for p in base_m if ans_m[p] != base_m[p])
        wrong_m = sum(1 for p in ans_m if ans_m[p] != gold[p])
        if name != "1_full_M_C_J":
            total_changed_jfirst += changed
            total_changed_mfirst += changed_m
        report["conditions"][name] = {
            "j_first": {"answers_changed_vs_full": changed,
                        "answers_wrong_vs_gold": wrong,
                        "resolved": st["resolved"],
                        "unresolved": st["unresolved"],
                        "order_decided_by": st["order_decided_by"],
                        "failure_reasons": st["failure_reasons"]},
            "m_first_control": {"answers_changed_vs_full": changed_m,
                                "answers_wrong_vs_gold": wrong_m,
                                "resolved": st_m["resolved"],
                                "unresolved": st_m["unresolved"]}}
        print(f"  {name:28} J-FIRST changed {changed:6d} wrong {wrong:6d} "
              f"| M-FIRST changed {changed_m:6d} wrong {wrong_m:6d}")

    # ---- supplementary: redundant or useless? ----
    print("\n[supplementary] is J merely REDUNDANT with M, or USELESS?")
    sym = symmetrized_M(R)
    # (a) M symmetrized, J available: can J alone recover the order?
    a_symJ, s_symJ = run(records, sym, ptype, use_j=True, use_m=True)
    ok_symJ = sum(1 for p, a in a_symJ.items() if a == gold[p])
    # (b) M symmetrized, J suppressed: the control
    a_sym0, s_sym0 = run(records, sym, ptype, use_j=False, use_m=True)
    ok_sym0 = sum(1 for p, a in a_sym0.items() if a == gold[p])
    # (c) full M, J suppressed: does removing J hurt when M is intact?
    a_mOnly, s_mOnly = run(records, R, ptype, use_j=False, use_m=True)
    ok_mOnly = sum(1 for p, a in a_mOnly.items() if a == gold[p])
    report["supplementary"] = {
        "M_intact_J_suppressed": {"correct": ok_mOnly, "n": n,
                                  "stats": s_mOnly},
        "M_symmetrized_J_available": {"correct": ok_symJ, "n": n,
                                      "stats": s_symJ},
        "M_symmetrized_J_suppressed": {"correct": ok_sym0, "n": n,
                                       "stats": s_sym0},
        "reading": "if M-intact/J-suppressed is already perfect, J is not "
                   "needed; if M-symmetrized/J-available is far better than "
                   "M-symmetrized/J-suppressed, J is CAPABLE of the "
                   "disambiguation job and is merely REDUNDANT given M's "
                   "asymmetry -- a different finding from J being useless"}
    print(f"  M intact,      J suppressed: {ok_mOnly}/{n}")
    print(f"  M symmetrized, J available : {ok_symJ}/{n}")
    print(f"  M symmetrized, J suppressed: {ok_sym0}/{n}")

    # ---- status law (registered) ----
    # IDENTIFIABILITY is decided by the M-FIRST control and by J-removal,
    # NOT by the J-favouring instrument. A J-first solver being damaged by a
    # WRONG J shows only that trusting J is risky when J is wrong; it does
    # not show that J carries information the task needs. J is identifiable
    # iff a solver that already has M still needs J.
    j_removal_changed = report["conditions"]["2_J_removed"][
        "j_first"]["answers_changed_vs_full"]
    identifiable = (total_changed_mfirst > 0) or (j_removal_changed > 0) \
        or (ok_mOnly < n)
    report["total_answers_changed_by_J_perturbation"] = {
        "j_first_instrument": total_changed_jfirst,
        "m_first_control": total_changed_mfirst,
        "j_removal_alone": j_removal_changed}
    report["status"] = ("TIER_C_J_IDENTIFIABLE_ON_CURRENT_TASK"
                        if identifiable
                        else "TIER_C_J_NOT_IDENTIFIABLE_ON_CURRENT_TASK")
    report["j_capable_but_redundant"] = bool(
        not identifiable and ok_symJ > ok_sym0)
    report["status_law"] = (
        "identifiable iff a solver that already has M still needs J: "
        "(M-first control changes under any J perturbation) OR (removing J "
        "changes an answer) OR (M-intact/J-suppressed is not perfect). "
        "Changes seen ONLY under the J-first instrument are excluded by "
        "construction -- they measure the cost of trusting a wrong J, not "
        "the task's need for J.")
    (HERE / "tier_c" / "J_NECESSITY_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nanswers changed by J perturbation -- J-FIRST instrument: "
          f"{total_changed_jfirst}, M-FIRST control: {total_changed_mfirst}, "
          f"J-removal alone: {j_removal_changed}")
    print(f"STATUS: {report['status']}")
    if report["j_capable_but_redundant"]:
        print("        J is CAPABLE of the ordering job (100% when M is "
              "symmetrized) but REDUNDANT: M's asymmetry already decides "
              "every case, so the task never requires J.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
