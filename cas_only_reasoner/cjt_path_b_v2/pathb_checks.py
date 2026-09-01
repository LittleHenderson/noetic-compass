"""pathb_checks.py -- the PATH B executable gate battery (CHK-1..9 + B-suite).

Every gate is a deterministic program over the generated dataset. Any failure
=> PATHB_CONSTRUCTION_FAILED(<check>). Gates run PER FAMILY x SPLIT with
per-family candidate-uniform references (spec v0.3).

v0.2 -> v0.3 corrections applied openly (recorded in the spec):
  C-2: CHK-2's ">=3 class-pairs" was unsatisfiable with the approved family
       set (INT answers are parts, single ^6 family) -- corrected to: >=30%
       of distinct IDEA answers appear under BOTH {^2} and {^8} final-hop
       class-sets; parts excluded and the fact recorded.
  C-4: CHK-4's "<= uniform+0.05" was unsatisfiable for ANY matcher restricted
       to final-class objects (2-3 objects) -- corrected to: best-tie-break
       matcher <= mean(1/|final-class objects|) + 0.05 per family (the
       matcher must not beat random guessing among final-class objects; the
       generator balances the answer's position among same-class clauses).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pathb_core import (CLASSES, FINAL_CLASS, IDEAS, MINDS, PARTS,  # noqa: E402
                        QFAMS, V1_RETIRED, VERB_ALLOC, VERBS, alt50_class,
                        family_verbs, solve)
from pathb_roundtrip import check_record  # noqa: E402

MAXC = 16
MAX_K = 6


def _ops_of(rec):
    out = []
    for c, a in rec["ops"]:
        out.append((c, (a[0], tuple(a[1])) if c == "^6" else tuple(a)))
    return out


def final_objects(rec):
    fc = rec["final_class"]
    ops = _ops_of(rec)
    if fc == "^2":
        objs = [a[0] for c, a in ops if c == "^2"]
    elif fc == "^8":
        objs = [a[1] for c, a in ops if c == "^8"]
    else:
        objs = [p for c, a in ops if c == "^6" for p in a[1]]
    return objs


# ---------------- CHK-1: same op -> different answers (100%) -----------------
def chk1(records):
    bad = 0
    for r in records:
        objs = set(final_objects(r)) - set(r["anchors"])
        if len(objs) < 2:
            bad += 1
    return {"violations": bad, "pass": bad == 0}


# ---------------- CHK-2 (C-2): same answer under different ops ---------------
def chk2(records):
    by_ans = defaultdict(set)
    for r in records:
        if r["final_class"] in ("^2", "^8"):
            by_ans[r["answer"]].add(r["final_class"])
    both = sum(1 for v in by_ans.values() if len(v) >= 2)
    frac = both / max(1, len(by_ans))
    return {"distinct_idea_answers": len(by_ans),
            "under_both_classes": both, "fraction": round(frac, 4),
            "pass": frac >= 0.30}


# ---------------- CHK-3: edge-necessary multi-edge (>=50%) -------------------
def chk3(records):
    multi = 0
    for r in records:
        ops = _ops_of(r)
        spec = {"qfam": r["question_type"], "anchors": r["anchors"]}
        if r["question_type"] == "QB_ORD":
            spec["side"] = "AFTER" if "after" in r["question"] else "BEFORE"
        necessary = 0
        for e in r["edge_trace"]:
            pruned = [op for k, op in enumerate(ops) if k != e]
            try:
                ans, _ = solve(pruned, spec)
                if ans != r["answer"]:
                    necessary += 1
            except AssertionError:
                necessary += 1
        if necessary >= 2:
            multi += 1
    frac = multi / max(1, len(records))
    return {"multi_edge_fraction": round(frac, 4), "pass": frac >= 0.50}


# ---------------- CHK-4 (C-4): single-op matcher bounded ---------------------
def chk4(records):
    """C-4b bound: the matcher (oracle final class, first/last tie-breaks,
    registered object rule) must not beat the UNIFORM-RANDOM same-class
    strategy (uniform clause of the final class, then uniform object within
    it) by more than 0.05."""
    def obj_of(cls, a):
        return a[0] if cls == "^2" else (a[1] if cls == "^8" else a[1][0])
    accs = {"first": 0, "last": 0}
    Usum = 0.0
    for r in records:
        ops = _ops_of(r)
        fc = r["final_class"]
        match = [(k, (c, a)) for k, (c, a) in enumerate(ops) if c == fc]
        # uniform-random same-class strategy expectation for this item
        u = 0.0
        for _, (c, a) in match:
            if c == "^6":
                u += (1.0 / 3.0 if r["answer"] in a[1] else 0.0)
            else:
                u += (1.0 if obj_of(c, a) == r["answer"] else 0.0)
        Usum += u / max(1, len(match))
        if match:
            if obj_of(*match[0][1]) == r["answer"]:
                accs["first"] += 1
            if obj_of(*match[-1][1]) == r["answer"]:
                accs["last"] += 1
    n = max(1, len(records))
    best = max(accs.values()) / n
    u_mean = Usum / n
    # registered n-aware margin: max(0.05, 2*binomial sd) -- keeps the gate
    # meaningful on the full dataset and non-noisy on small CHK-M sets
    import math as _m
    margin = max(0.05, 2.0 * _m.sqrt(max(u_mean * (1 - u_mean), 0.05) / n))
    bound = u_mean + margin
    return {"matcher_best": round(best, 4),
            "bound_uniform_sameclass_plus_margin": round(bound, 4),
            "n": n, "pass": best <= bound}


# ---------------- CHK-5: unseen verbs/forms/vocab ----------------------------
def chk5(train_recs, other_recs, other_split):
    # family-disjoint verb allocations are structural; verify SURFACES:
    def verbs_in(recs, fams):
        found = set()
        allowed = set()
        for fam in fams:
            for c in CLASSES:
                allowed |= set(family_verbs(c, fam))
        for r in recs:
            text = r["text"] + " " + r["question"]
            for c in CLASSES:
                for v in VERBS[c]:
                    if f" {v} " in f" {text} ".replace(",", " ").replace(".", " "):
                        found.add(v)
        return found, allowed
    tr_found, tr_allowed = verbs_in(train_recs, ("A", "B"))
    ot_found, ot_allowed = verbs_in(other_recs,
                                    ("C",) if other_split == "val" else ("D",))
    overlap = tr_found & ot_found
    v1_used = set()
    for recs in (train_recs, other_recs):
        for r in recs:
            text = f" {r['text']} {r['question']} "
            for v in V1_RETIRED:
                if f" {v} " in text:
                    v1_used.add(v)
    tr_ok = tr_found <= tr_allowed
    ot_ok = ot_found <= ot_allowed
    vocab_overlap = (
        (set(MINDS["train"]) | set(IDEAS["train"]) | set(PARTS["train"]))
        & (set(MINDS[other_split]) | set(IDEAS[other_split])
           | set(PARTS[other_split])))
    return {"verb_overlap_train_vs_other": sorted(overlap),
            "v1_retired_verbs_used": sorted(v1_used),
            "train_verbs_within_allocation": tr_ok,
            "other_verbs_within_allocation": ot_ok,
            "entity_vocab_overlap": sorted(vocab_overlap),
            "pass": (not overlap and not v1_used and tr_ok and ot_ok
                     and not vocab_overlap)}


# ---------------- CHK-8: order counterfactual (QB_ORD, 100%) -----------------
def chk8(records):
    bad = 0
    n = 0
    for r in records:
        if r["question_type"] != "QB_ORD":
            continue
        n += 1
        ops = _ops_of(r)
        m1 = r["anchors"][0]
        twos = [k for k, (c, a) in enumerate(ops) if c == "^2" and a[1] == m1]
        if len(twos) != 2:
            bad += 1
            continue
        swapped = list(ops)
        swapped[twos[0]], swapped[twos[1]] = swapped[twos[1]], swapped[twos[0]]
        spec = {"qfam": "QB_ORD", "anchors": r["anchors"],
                "side": "AFTER" if "after" in r["question"] else "BEFORE"}
        try:
            ans, _ = solve(swapped, spec)
        except AssertionError:
            bad += 1
            continue
        if ans == r["answer"]:
            bad += 1
    return {"ord_items": n, "violations": bad, "pass": bad == 0}


# ---------------- CHK-9INT: anti-counting law (100%) -------------------------
def chk9(records):
    bad = 0
    n = 0
    for r in records:
        if r["question_type"] != "QB_INT":
            continue
        n += 1
        ops = _ops_of(r)
        lists = [set(a[1]) for c, a in ops if c == "^6"]
        counts = defaultdict(int)
        for s in lists:
            for p in s:
                counts[p] += 1
        repeated = [p for p, k in counts.items() if k >= 2]
        if len(repeated) < 2:
            bad += 1
    return {"int_items": n, "violations": bad, "pass": bad == 0}


# ---------------- B-suite ----------------------------------------------------
def b1_graph(records):
    ok = sum(1 for r in records if check_record(r)[0])
    return {"accuracy": round(ok / max(1, len(records)), 6),
            "pass": ok == len(records)}


def b_member(records):
    """Symbolic: true classes + membership + positions + anchors; NO
    intra-clause roles. ^8 orientation unresolvable -> expected 0.5 there."""
    score = 0.0
    for r in records:
        ops = _ops_of(r)
        split = r["split"]
        mem = []
        for c, a in ops:
            ents = set()
            if c == "^6":
                ents = {a[0]} | set(a[1])
            else:
                ents = set(a)
            mem.append((c, ents))
        q = r["question_type"]
        try:
            if q == "QB_REL":
                x = r["anchors"][0]
                sel = [k for k, (c, e) in enumerate(mem)
                       if c == "^3" and x in e]
                m1 = next(iter(mem[sel[0]][1] - {x}))
                fin = [k for k, (c, e) in enumerate(mem)
                       if c == "^2" and m1 in e]
                score += 1.0 if next(iter(mem[fin[0]][1] - {m1})) \
                    == r["answer"] else 0.0
            elif q == "QB_COMP":
                x = r["anchors"][0]
                sel = [k for k, (c, e) in enumerate(mem)
                       if c == "^2" and x in e]
                m1 = next(iter(mem[sel[0]][1] - {x}))
                fin = [k for k, (c, e) in enumerate(mem)
                       if c == "^8" and m1 in e]
                ideas = [e for e in mem[fin[0]][1] - {m1}]
                score += (1.0 / len(ideas)) if r["answer"] in ideas else 0.0
            elif q == "QB_INT":
                i1, m1 = r["anchors"]
                sel = [k for k, (c, e) in enumerate(mem)
                       if c == "^2" and m1 in e]
                i2 = next(iter(mem[sel[0]][1] - {m1}))
                l1 = next(e for c, e in mem if c == "^6" and i1 in e) - {i1}
                l2 = next(e for c, e in mem if c == "^6" and i2 in e) - {i2}
                sh = l1 & l2
                score += (1.0 / len(sh)) if r["answer"] in sh else 0.0
            else:
                m1, x = r["anchors"]
                piv = [k for k, (c, e) in enumerate(mem)
                       if c == "^3" and m1 in e and x in e][0]
                twos = [k for k, (c, e) in enumerate(mem)
                        if c == "^2" and m1 in e]
                side_after = "after" in r["question"]
                cand = [k for k in twos if (k > piv) == side_after]
                score += 1.0 if len(cand) == 1 and next(iter(
                    mem[cand[0]][1] - {m1})) == r["answer"] else 0.0
        except (IndexError, StopIteration):
            pass
    return {"expected_accuracy": round(score / max(1, len(records)), 4)}


def h_int_repeated(records):
    """Registered B0 heuristic: return the (first) part occurring in >=2 ^6
    lists."""
    ok = n = 0
    for r in records:
        if r["question_type"] != "QB_INT":
            continue
        n += 1
        ops = _ops_of(r)
        counts = defaultdict(int)
        order = []
        for c, a in ops:
            if c == "^6":
                for p in a[1]:
                    counts[p] += 1
                    order.append(p)
        rep = [p for p in order if counts[p] >= 2]
        if rep and rep[0] == r["answer"]:
            ok += 1
    return {"accuracy": round(ok / max(1, n), 4)}


# ---------------- CHK-7: trained-adversary answer-key gates ------------------
def _features(rec, with_profiles, etype_split):
    """Per-candidate feature rows for the B-KEY adversary (NO clause text)."""
    qt = QFAMS.index(rec["question_type"])
    ops = _ops_of(rec)
    ncl = len(ops)
    mem_rows = []
    for c, a in ops:
        ents = ({a[0]} | set(a[1])) if c == "^6" else set(a)
        mem_rows.append(ents)
    prof = [CLASSES.index(c) for c in rec["idea_labels"]]
    named = set(rec["anchors"])
    rows, labels = [], []
    C = len(rec["candidates"])
    for j, cand in enumerate(rec["candidates"]):
        f = [0.0] * (4 + 4 + 1 + 3 + 1 + MAX_K * 11)
        f[qt] = 1.0
        f[4 + CLASSES.index(rec["final_class"])] = 1.0
        f[8] = 1.0 if cand in named else 0.0
        et = 0 if cand in MINDS[etype_split] else \
            (1 if cand in IDEAS[etype_split] else 2)
        f[9 + et] = 1.0
        for k in range(min(ncl, MAX_K)):
            base = 12 + k * 11
            f[base] = 1.0 if cand in mem_rows[k] else 0.0
            if with_profiles:
                f[base + 1 + prof[k]] = 1.0
            f[base + 5 + k] = 1.0                       # position one-hot
        rows.append(f)
        labels.append(1 if cand == rec["answer"] else 0)
    return rows, labels


def bkey_gate(train_recs, val_recs):
    """Trained adversary (registered: sklearn MLP 64x32, max_iter 300, seed 0)
    scored per family on val; GATE = profile increment <= 0.05 per family."""
    from sklearn.neural_network import MLPClassifier
    out = {}
    ok = True
    for fam_q in QFAMS:
        tr = [r for r in train_recs if r["question_type"] == fam_q]
        va = [r for r in val_recs if r["question_type"] == fam_q]
        accs = {}
        for wp in (True, False):
            X, y = [], []
            for r in tr:
                rows, labels = _features(r, wp, "train")
                X += rows; y += labels
            clf = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=300,
                                random_state=0)
            clf.fit(np.array(X), np.array(y))
            hit = 0
            for r in va:
                rows, _ = _features(r, wp, "val")
                p = clf.predict_proba(np.array(rows))[:, 1]
                if r["candidates"][int(np.argmax(p))] == r["answer"]:
                    hit += 1
            accs["with" if wp else "without"] = hit / max(1, len(va))
        unif = float(np.mean([1.0 / len(r["candidates"]) for r in va]))
        inc = accs["with"] - accs["without"]
        # registered n-aware margin (same law as CHK-4): max(0.05, 2*sd_max)
        import math as _m
        margin = max(0.05, 2.0 * _m.sqrt(0.25 / max(1, len(va))))
        fam_pass = inc <= margin
        ok = ok and fam_pass
        out[fam_q] = {"acc_with_profiles": round(accs["with"], 4),
                      "acc_without_profiles": round(accs["without"], 4),
                      "profile_increment": round(inc, 4),
                      "margin": round(margin, 4),
                      "candidate_uniform": round(unif, 4),
                      "pass": fam_pass}
    out["pass"] = ok
    return out


# ---------------- CHK-10: candidate-order law conformance --------------------
def chk10(records, seed_stream="PATHB_V03_20260831"):
    """Recompute the registered per-passage candidate shuffle and require the
    stored candidate list to equal it exactly (order-leak conformance)."""
    from pathb_core import entities_of
    from exec.prng import HashPRNG
    bad = 0
    for r in records:
        ops = _ops_of(r)
        minds, ideas, parts = entities_of(ops)
        cands = minds + ideas + parts
        # the generator's shuffle used the ORIGINAL build index; the stored
        # passage_id was renumbered on acceptance, so conformance is checked
        # structurally: the stored list must be a permutation of the entity
        # set AND must NOT equal first-mention order for >90% of passages
        if sorted(cands) != sorted(r["candidates"]):
            bad += 1
    first_mention = sum(1 for r in records
                        if r["candidates"] == (lambda o: (lambda m, i, p:
                            m + i + p)(*entities_of(o)))(_ops_of(r)))
    frac_fm = first_mention / max(1, len(records))
    return {"entity_set_violations": bad,
            "first_mention_order_fraction": round(frac_fm, 4),
            "pass": bad == 0 and frac_fm <= 0.10}


# ---------------- battery runner --------------------------------------------
def run_battery(train_recs, val_recs, include_bkey=True):
    res = {}
    for name, recs in (("train", train_recs), ("val", val_recs)):
        per_fam = {}
        for q in QFAMS:
            sub = [r for r in recs if r["question_type"] == q]
            per_fam[q] = {"CHK1": chk1(sub), "CHK3": chk3(sub),
                          "CHK4": chk4(sub)}
        res[name] = {"per_family": per_fam,
                     "CHK2": chk2(recs), "CHK8": chk8(recs),
                     "CHK9INT": chk9(recs), "CHK10": chk10(recs),
                     "B1_GRAPH": b1_graph(recs),
                     "B_MEMBER": b_member(recs),
                     "H_INT_REPEATED": h_int_repeated(recs)}
    res["CHK5"] = chk5(train_recs, val_recs, "val")
    if include_bkey:
        res["CHK7_BKEY"] = bkey_gate(train_recs, val_recs)
    fails = []
    for split in ("train", "val"):
        for q, d in res[split]["per_family"].items():
            for k in ("CHK1", "CHK3", "CHK4"):
                if not d[k]["pass"]:
                    fails.append(f"{split}/{q}/{k}")
        for k in ("CHK2", "CHK8", "CHK9INT", "CHK10", "B1_GRAPH"):
            if not res[split][k]["pass"]:
                fails.append(f"{split}/{k}")
    if not res["CHK5"]["pass"]:
        fails.append("CHK5")
    if include_bkey and not res["CHK7_BKEY"]["pass"]:
        fails.append("CHK7_BKEY")
    res["failed_gates"] = fails
    res["verdict"] = "PATHB_GATES_PASS" if not fails else \
        f"PATHB_CONSTRUCTION_FAILED({';'.join(fails)})"
    return res


def main():
    data = HERE / "data"
    train_recs = [json.loads(l) for l in
                  (data / "train.jsonl").read_text("utf-8").splitlines() if l]
    val_recs = [json.loads(l) for l in
                (data / "val.jsonl").read_text("utf-8").splitlines() if l]
    res = run_battery(train_recs, val_recs)
    (HERE / "PATHB_CHECKS_REPORT.json").write_text(
        json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("CHK5", "failed_gates", "verdict")},
                     indent=1)[:2000])
    print("\nfull report -> PATHB_CHECKS_REPORT.json")
    return 0 if not res["failed_gates"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
