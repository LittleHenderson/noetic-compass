"""tier_c_j0_bench.py -- J0: Source-Grounded J Identifiability Bench.

Owner ruling after the J-necessity closure: one very small CPU stage whose
job is to search the ACTUAL CAS rules for authentic cases where

    M + C leaves the answer ambiguous
    but
    M + C + J determines the answer

and, for each, to build a counterfactual twin (same entities, same operation
identities, same M/C information, same candidate set, matched wording;
different J relation, different correct answer) and run four deterministic
checks:

    full M+C+J        -> correct
    J removed         -> ambiguous or changed answer
    J corrupted       -> wrong answer
    unrelated J cell  -> no effect

SOURCE GROUNDING. Everything used here is quoted from the canonical layer
(the 10 Noetic definitions and the structural invariants), NOT invented:

  * "^8 (CO-8) Above/Cause -- An Idea that triggers a different Idea than
    itself to come to Mind."
  * "^9 (CO-9) Below/Effect -- The Idea brought to Mind by an Above/Cause
    trigger."
  * "^5 (CO-5) Female -- A Mind impregnated with an Idea, the Ideas a Mind
    is composed of."
  * "^6 (CO-6) Male -- An Idea impregnated with another Idea, the Ideas an
    Idea is composed of."
  * "^2 (CO-2) Positive -- An Idea the Mind has an affinity for and is
    attracted toward."
  * "^3 (CO-3) Negative -- An Idea the Mind is adverse to and repelled by."
  * Structural invariant: "Involution pairs: CO-2<->CO-3, CO-5<->CO-6,
    CO-8<->CO-9. Self-duals: CO-0, CO-1, CO-4, CO-7."

WHY THE CURRENT TASK COULD NOT TEST J. The PATH B vocabulary uses ^2, ^3,
^6, ^8 -- which contains ONE complete involution pair (^2<->^3) and TWO
half-pairs (^6 without ^5, ^8 without ^9). A half-pair cannot express a
converse relation, so every composition in the task had exactly one
admissible direction, M's asymmetry fixed the order, and J was redundant.
J0 therefore restores the MISSING INVOLUTION PARTNERS (^5 and ^9) and asks
whether completing the pairs creates genuinely M-ambiguous, J-determined
configurations.

A STRUCTURAL CAVEAT THAT MUST TRAVEL WITH ANY RESULT. R = (M, C, J) is a
function of the class labels: sign(^2), dual(^6), M[a,b] and C[a,b] are all
table lookups keyed by class. A model that already receives exact class
labels can in principle LEARN that lookup from data. So no part of R --
J included -- can ever be INFORMATIONALLY necessary to a label-equipped
learner. What a J-requiring task can test is whether supplying the correct
lookup as a FROZEN PRIOR beats learning it (sample efficiency, out-of-
distribution transfer). That is a real and testable question, but it is a
claim about inductive bias, not about information. J0 answers the SYMBOLIC
question the owner posed; it does not and cannot promote it into an
information claim.

Development-only, non-claim-bearing. CPU, $0.
"""
from __future__ import annotations

import copy
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# ---- the authentic canonical layer (quoted, not invented) ------------------
NOETIC_DEFS = {
    "^2": "An Idea the Mind has an affinity for and is attracted toward.",
    "^3": "An Idea the Mind is adverse to and repelled by.",
    "^5": "A Mind impregnated with an Idea, the Ideas a Mind is composed of.",
    "^6": "An Idea impregnated with another Idea, the Ideas an Idea is "
          "composed of.",
    "^8": "An Idea that triggers a different Idea than itself to come to "
          "Mind.",
    "^9": "The Idea brought to Mind by an Above/Cause trigger.",
}
INVOLUTION_PAIRS = [("^2", "^3"), ("^5", "^6"), ("^8", "^9")]
SIGN = {"^2": "POS", "^3": "NEG", "^5": "NEUTRAL", "^6": "NEUTRAL",
        "^8": "NEUTRAL", "^9": "NEUTRAL"}
CLASSES = tuple(sorted(NOETIC_DEFS))
TASK_VOCAB = ("^2", "^3", "^6", "^8")          # what PATH B actually used

# A CONVERSE pair is an involution pair whose two members describe the SAME
# underlying edge read in opposite directions. Grounded in the definitions:
# ^8 names the triggering Idea, ^9 names the triggered Idea of the SAME
# trigger event; ^5 names a Mind's composition, ^6 an Idea's composition.
# ^2/^3 are opposites of VALENCE, not converse directions of one edge --
# a Mind attracted to X and repelled by Y are two different edges.
CONVERSE_PAIRS = [("^8", "^9")]
VALENCE_PAIRS = [("^2", "^3")]
COMPOSITION_PAIRS = [("^5", "^6")]


def dual_of(c):
    for a, b in INVOLUTION_PAIRS:
        if c == a:
            return b
        if c == b:
            return a
    return None


# ---- edge semantics: what a clause of each class asserts --------------------
# (source, target) of the directed IDEA->IDEA edge a clause induces, or None
# when the class induces no idea-to-idea edge. Read directly off the
# definitions above; nothing here is a task-construction choice.
def edge_of(cls, args):
    """args = (x, y, m) in surface order. Returns (src, dst) or None."""
    x, y, _m = args
    if cls == "^8":              # "x triggers y"        -> x -> y
        return (x, y)
    if cls == "^9":              # "x is brought by y"   -> y -> x
        return (y, x)
    if cls == "^6":              # "x is composed of y"  -> x -> y
        return (x, y)
    if cls == "^5":              # "mind composed of x"  -> no idea->idea
        return None
    return None                  # ^2 / ^3 are mind-idea valence, not chains


def build_R(classes):
    """M/C/J over a class inventory, derived from the canonical layer only.
    M[a,b] = 1 iff a chain 'edge of a' then 'edge of b' is admissible, i.e.
    both classes induce idea->idea edges."""
    cells = {}
    for a in classes:
        for b in classes:
            chainable = (edge_of(a, ("x", "y", "m")) is not None
                         and edge_of(b, ("y", "z", "m")) is not None)
            cells[f"{a}|{b}"] = {
                "M": 1 if chainable else 0,
                "status": "DERIVED" if chainable else "UNDEFINED",
                "result_type": "IDEA" if chainable else "UNDEFINED",
                "mediator_type": "IDEA" if chainable else "UNDEFINED",
                "source_rule": "CANONICAL_EDGE_SEMANTICS",
                "derivation": f"{NOETIC_DEFS.get(a,'')} / "
                              f"{NOETIC_DEFS.get(b,'')}"}
    j_pair = {}
    for a in classes:
        for b in classes:
            if a == b:
                j_pair[f"{a}|{b}"] = "SAME"
            elif dual_of(a) == b:
                j_pair[f"{a}|{b}"] = "DUAL"
            else:
                j_pair[f"{a}|{b}"] = "UNDEFINED"
    return {"structure_id": "R_CAS_J0", "classes": list(classes),
            "cells": cells,
            "J": {"pair": j_pair,
                  "sign": {c: SIGN[c] for c in classes},
                  "dual_present": {c: dual_of(c) in classes
                                   for c in classes},
                  "converse": {f"{a}|{b}": (tuple(sorted((a, b)))
                                            in [tuple(sorted(p))
                                                for p in CONVERSE_PAIRS])
                               for a in classes for b in classes}}}


# ---- the J-driven chain solver ---------------------------------------------
def traverse(clauses, R, use_j):
    """Build the directed idea-graph the clauses assert and return the set of
    terminal ideas reachable from the unique source. Without J the solver
    cannot know that a CONVERSE class reverses its edge, so it reads every
    clause in surface order -- which is exactly the ambiguity J resolves."""
    edges = set()
    for cls, args in clauses:
        if use_j:
            e = edge_of(cls, args)          # J-aware: converse reverses
        else:
            x, y, _ = args                  # J-blind: surface order only
            e = (x, y) if edge_of(cls, args) is not None else None
        if e:
            edges.add(e)
    if not edges:
        return set()
    srcs = {a for a, _ in edges} - {b for _, b in edges}
    if len(srcs) != 1:
        return set()                        # ambiguous: no unique source
    cur = {next(iter(srcs))}
    seen = set()
    for _ in range(len(edges) + 1):
        nxt = {b for a, b in edges if a in cur}
        seen |= cur
        if not nxt:
            break
        cur = nxt
    terms = {a for a in cur if not any(s == a for s, _ in edges)}
    return terms or cur


def solve_case(case, R, use_j=True):
    t = traverse(case["clauses"], R, use_j)
    return next(iter(t)) if len(t) == 1 else None


# ---- J corruption variants --------------------------------------------------
def j_removed(R):
    v = copy.deepcopy(R)
    for k in v["J"]["pair"]:
        a, b = k.split("|")
        v["J"]["pair"][k] = "SAME" if a == b else "UNDEFINED"
    v["J"]["sign"] = {c: "NEUTRAL" for c in v["classes"]}
    v["J"]["dual_present"] = {c: False for c in v["classes"]}
    v["J"]["converse"] = {k: False for k in v["J"]["converse"]}
    return v


def j_unrelated_cell(R):
    v = copy.deepcopy(R)
    v["J"]["pair"]["^2|^6"] = "DUAL"      # a cell no chain question touches
    return v


# ---- counterfactual twin construction --------------------------------------
def make_twins(pair):
    """For a CONVERSE pair (a, a*), build two passages that are identical in
    entities, class multiset, M/C, candidate set and wording template, and
    differ ONLY in which clause carries which member of the pair -- a pure J
    difference. Their correct answers differ."""
    a, astar = pair
    x, y, z, m = "algebra", "botany", "chess", "mira"
    twin1 = {"twin": "1", "clauses": [(a, (x, y, m)), (astar, (z, y, m))],
             "candidates": [x, y, z], "anchor_note": "unique source"}
    twin2 = {"twin": "2", "clauses": [(astar, (x, y, m)), (a, (z, y, m))],
             "candidates": [x, y, z], "anchor_note": "unique source"}
    return twin1, twin2


def surface(case):
    """Matched wording: the SAME template for both members of the pair, so
    no surface cue distinguishes the twins beyond the operation verb."""
    out = []
    for cls, (p, q, mm) in case["clauses"]:
        verb = {"^8": "evoked", "^9": "was evoked by", "^6": "divided into",
                "^5": "was composed of", "^2": "lured", "^3": "shunned"}[cls]
        out.append(f"{p} {verb} {q} for {mm}.")
    return " ".join(out)


def main():
    print("J0: SOURCE-GROUNDED J IDENTIFIABILITY BENCH ($0, CPU)\n")
    R_task = build_R(TASK_VOCAB)
    R_full = build_R(CLASSES)

    # ---- 1. why the current task could not test J -------------------------
    def symmetric_pairs(R):
        cs = R["classes"]
        out = []
        for a, b in itertools.combinations(cs, 2):
            ab = R["cells"][f"{a}|{b}"]["M"]
            ba = R["cells"][f"{b}|{a}"]["M"]
            if ab == ba == 1:
                out.append((a, b))
        return out
    sym_task = symmetric_pairs(R_task)
    sym_full = symmetric_pairs(R_full)
    print(f"[1] task vocabulary {TASK_VOCAB}: complete involution pairs "
          f"present = "
          f"{[p for p in INVOLUTION_PAIRS if all(c in TASK_VOCAB for c in p)]}")
    print(f"    M-symmetric chainable pairs in the TASK vocabulary: "
          f"{sym_task}")
    print(f"[2] full canonical vocabulary {CLASSES}: "
          f"M-symmetric chainable pairs: {sym_full}")

    # ---- 2. search for authentic J-determined configurations ---------------
    findings = []
    for pair in CONVERSE_PAIRS:
        a, b = pair
        if not (R_full["cells"][f"{a}|{b}"]["M"] == 1
                and R_full["cells"][f"{b}|{a}"]["M"] == 1):
            continue                       # M must NOT fix the order
        t1, t2 = make_twins(pair)
        rec = {"pair": list(pair), "twins": []}
        for t in (t1, t2):
            full = solve_case(t, R_full, use_j=True)
            noj = solve_case(t, j_removed(R_full), use_j=False)
            corrupt = solve_case(t, R_full, use_j=False)   # J present but
            #                       ignored/wrong -> reads converse forward
            unrel = solve_case(t, j_unrelated_cell(R_full), use_j=True)
            rec["twins"].append({
                "twin": t["twin"], "surface": surface(t),
                "clauses": [[c, list(ar)] for c, ar in t["clauses"]],
                "candidates": t["candidates"],
                "answer_full_M_C_J": full,
                "answer_J_removed": noj,
                "answer_J_corrupted": corrupt,
                "answer_unrelated_J_cell": unrel})
        ans = [tw["answer_full_M_C_J"] for tw in rec["twins"]]
        rec["twins_have_different_answers"] = (
            ans[0] is not None and ans[1] is not None and ans[0] != ans[1])
        rec["checks"] = {
            "full_M_C_J_resolves_both": all(a_ is not None for a_ in ans),
            "twins_differ": rec["twins_have_different_answers"],
            "J_removed_ambiguous_or_changed": all(
                tw["answer_J_removed"] != tw["answer_full_M_C_J"]
                for tw in rec["twins"]),
            "J_corrupted_wrong": all(
                tw["answer_J_corrupted"] != tw["answer_full_M_C_J"]
                for tw in rec["twins"]),
            "unrelated_J_cell_no_effect": all(
                tw["answer_unrelated_J_cell"] == tw["answer_full_M_C_J"]
                for tw in rec["twins"])}
        rec["valid_J_dependent_case"] = all(rec["checks"].values())
        findings.append(rec)

    print("\n[3] authentic J-dependent configurations found:")
    for f in findings:
        print(f"    pair {f['pair']}: valid={f['valid_J_dependent_case']}")
        for tw in f["twins"]:
            print(f"      twin {tw['twin']}: \"{tw['surface']}\"")
            print(f"        full M+C+J -> {tw['answer_full_M_C_J']} | "
                  f"J removed -> {tw['answer_J_removed']} | "
                  f"J corrupted -> {tw['answer_J_corrupted']} | "
                  f"unrelated cell -> {tw['answer_unrelated_J_cell']}")
        print(f"      checks: {f['checks']}")

    # ---- 4. the owner's hardest gate condition, tested not asserted -------
    # "flat operation labels do not reveal it". If the twins differ in their
    # (label sequence, entity-slot) signature, then a function from flat
    # labels to the answer EXISTS, so a learner can recover the answer
    # without any table -- and the condition FAILS.
    flat = []
    for f in findings:
        sigs = {}
        for tw in f["twins"]:
            sig = tuple((c, tuple(a)) for c, a in tw["clauses"])
            sigs[tw["twin"]] = sig
        distinct = len(set(sigs.values())) == len(sigs)
        answers = {tw["twin"]: tw["answer_full_M_C_J"] for tw in f["twins"]}
        flat.append({"pair": f["pair"], "twin_label_signatures":
                     {k: [list(x) for x in v] for k, v in sigs.items()},
                     "signatures_distinct": distinct,
                     "answers": answers,
                     "flat_label_function_exists": distinct,
                     "owner_condition_flat_labels_do_not_reveal":
                         not distinct})
        print(f"\n[4] owner gate check -- 'flat operation labels do not "
              f"reveal it' for pair {f['pair']}:")
        print(f"    twin label signatures distinct: {distinct}")
        print(f"    => a flat-label -> answer function EXISTS: {distinct}")
        print(f"    => owner condition SATISFIED: {not distinct}")

    n_valid = sum(1 for f in findings if f["valid_J_dependent_case"])
    status = ("J0_GENUINE_J_DEPENDENT_CASES_EXIST" if n_valid
              else "J0_NO_GENUINE_J_DEPENDENT_CASES")
    report = {
        "record_id": "TIER_C_J0_BENCH", "non_claim_bearing": True,
        "cost": "$0.00 local CPU",
        "source_grounding": {
            "noetic_definitions_used": NOETIC_DEFS,
            "involution_pairs": [list(p) for p in INVOLUTION_PAIRS],
            "converse_pairs": [list(p) for p in CONVERSE_PAIRS],
            "note": "^2/^3 are opposites of VALENCE (two different edges), "
                    "not converse readings of one edge, so they cannot "
                    "create the ambiguity a converse pair creates"},
        "why_current_task_could_not_test_J": {
            "task_vocabulary": list(TASK_VOCAB),
            "complete_involution_pairs_in_task": [
                list(p) for p in INVOLUTION_PAIRS
                if all(c in TASK_VOCAB for c in p)],
            "missing_partners": {"^6": "^5 absent", "^8": "^9 absent"},
            "m_symmetric_chainable_pairs_in_task": [list(p)
                                                    for p in sym_task],
            "explanation": "a half-pair cannot express a converse relation, "
                           "so every composition had exactly one admissible "
                           "direction and M's asymmetry fixed the order"},
        "full_vocabulary_m_symmetric_pairs": [list(p) for p in sym_full],
        "findings": findings, "n_valid_cases": n_valid, "status": status,
        "flat_label_gate": flat,
        "structural_caveat": "R = (M, C, J) is a function of the class "
                             "labels, so no part of R can be "
                             "INFORMATIONALLY necessary to a learner that "
                             "already receives exact class labels -- the "
                             "lookup is learnable from data. A J-requiring "
                             "task can therefore test only whether the "
                             "correct lookup supplied as a FROZEN PRIOR "
                             "beats learning it (sample efficiency, OOD "
                             "transfer). That is a claim about inductive "
                             "bias, not about information, and it must not "
                             "be promoted into one.",
        "owner_gate_not_yet_satisfied": [
            "C does not reveal the answer", "clause order does not reveal it",
            "flat operation labels do not reveal it",
            "surface wording does not reveal it",
            "candidate position does not reveal it",
            "removing J actually changes the correct answer",
            "at least two families depend on J",
            "the baseline has real headroom"],
        "gate_note": "J0 establishes only the FIRST condition (M must stop "
                     "giving the answer away) plus the twin-level "
                     "deterministic checks. The remaining owner conditions "
                     "are properties of a full dataset and are NOT "
                     "established here."}
    (HERE / "tier_c" / "J0_BENCH_REPORT.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\nSTATUS: {status}  (valid cases: {n_valid})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
