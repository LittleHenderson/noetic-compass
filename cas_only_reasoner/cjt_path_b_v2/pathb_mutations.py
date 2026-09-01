"""pathb_mutations.py -- CHK-M: test the tests (owner v0.3 ruling).

Each registered mutant deliberately produces a DEFECTIVE-but-structurally-valid
dataset (in-process monkeypatching only; the working tree is never modified)
and the battery must catch it SEMANTICALLY: the target gate fails with its
registered code while the registered prerequisite gates still pass. A clean
positive reference must pass everything. Crash-only "successes" are failures
of CHK-M itself.

Owner's 7-point validity law per mutant: (1) mutated generator runs;
(2) records structurally valid; (3) prerequisite gates pass; (4) target gate
fails; (5) only the target gate catches it (no forbidden alternative failure
modes among the registered prerequisite set); (6) pristine generator passes;
(7) working tree untouched (in-process patching; verified by re-running the
clean reference AFTER all mutants).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import pathb_core as core  # noqa: E402
import pathb_checks as checks  # noqa: E402
from pathb_core import CLASSES  # noqa: E402

SMALL = 40                                    # per (family x qfam) for speed


def gen_small(mutate_record=None):
    """Small dataset via the real constructive path; mutate_record optionally
    rewrites each accepted record (post-generation defects)."""
    from pathb_core import QFAMS, SPLIT_FAMILY, build_record
    out = {}
    for split in ("train", "val"):
        recs = []
        for fam in SPLIT_FAMILY[split]:
            for qf in QFAMS:
                got = idx = 0
                while got < SMALL and idx < SMALL * 4:
                    r = build_record("MUT", split, fam, qf, idx)
                    idx += 1
                    if r is None:
                        continue
                    from generate_pathb import unique_pid
                    r["passage_id"] = unique_pid(split, fam, qf, got)
                    if mutate_record is not None:
                        r = mutate_record(r)
                    recs.append(r)
                    got += 1
        out[split] = recs
    return out["train"], out["val"]


def run(include_bkey=False):
    tr, va = gen_small()
    return checks.run_battery(tr, va, include_bkey=include_bkey)


def gates_failed(res):
    return set(res["failed_gates"])


MUTANTS = []


def mutant(mid, target, bkey=False, prereqs=("B1_GRAPH",)):
    def deco(fn):
        MUTANTS.append({"id": mid, "target": target, "setup": fn,
                        "bkey": bkey, "prereqs": prereqs})
        return fn
    return deco


# ---- M1: restore a one-operation answer shortcut (REL bijective) -----------
@mutant("M1_BIJECTIVE_REL", "CHK1")
def m1():
    orig = core.build_graph

    def patched(rng, split, qfam):
        ops, spec = orig(rng, split, qfam)
        if qfam == "QB_REL":
            # demote every non-answer ^2 edge to ^3 (final class single-object)
            out = []
            for c, a in ops:
                if c == "^2" and a[0] != spec["answer"]:
                    out.append(("^3", (a[1], a[0])))
                else:
                    out.append((c, a))
            ops = out
        return ops, spec
    core.build_graph = patched
    return lambda: setattr(core, "build_graph", orig)


# ---- M2: answers never shared across final-hop classes ----------------------
@mutant("M2_NO_XOP_OVERLAP", "CHK2")
def m2():
    orig = core.build_graph

    def patched(rng, split, qfam):
        ops, spec = orig(rng, split, qfam)
        if qfam == "QB_COMP":
            # force COMP answers into a reserved idea never used by ^2 answers
            reserved = core.IDEAS[split][-1]
            old = spec["answer"]
            rename = lambda e: reserved if e == old else e
            ops = [(c, (a[0], tuple(rename(p) for p in a[1])) if c == "^6"
                    else tuple(rename(x) for x in a)) for c, a in ops]
            spec = dict(spec, answer=reserved,
                        anchors=[rename(x) for x in spec["anchors"]])
        return ops, spec
    core.build_graph = patched
    return lambda: setattr(core, "build_graph", orig)


# ---- M3: edge trace lies (single-edge composition claim) --------------------
@mutant("M3_SINGLE_EDGE_TRACE", "CHK3")
def m3():
    def mut(rec):
        rec["edge_trace"] = rec["edge_trace"][-1:]
        return rec
    return _record_mutation(mut)


# ---- M4: reopen BOTH CHK-4 leaks (p1-slot answers + ORD extremity) ----------
@mutant("M4_MATCHER_LEAKS", "CHK4")
def m4():
    orig = core.build_graph

    def patched(rng, split, qfam):
        ops, spec = orig(rng, split, qfam)
        if qfam == "QB_INT":
            out = []
            for c, a in ops:
                if c == "^6" and spec["answer"] in a[1]:
                    ps = [spec["answer"]] + [p for p in a[1]
                                             if p != spec["answer"]]
                    out.append((c, (a[0], tuple(ps))))
                else:
                    out.append((c, a))
            ops = out
        return ops, spec
    core.build_graph = patched
    return lambda: setattr(core, "build_graph", orig)


# ---- M5: family verb allocation leak ----------------------------------------
@mutant("M5_VERB_FAMILY_LEAK", "CHK5")
def m5():
    import pathb_roundtrip as rt
    orig = dict(core.VERB_ALLOC)
    orig_pats, orig_qpats = rt._PATS, rt._QPATS
    core.VERB_ALLOC["A"] = (0, 1, 6)          # index 6 belongs to family C
    rt._PATS = {f: rt._clause_patterns(f) for f in rt.FAMILIES}
    rt._QPATS = {f: rt._q_patterns(f) for f in rt.FAMILIES}

    def restore():
        core.VERB_ALLOC.update(orig)
        rt._PATS, rt._QPATS = orig_pats, orig_qpats
    return restore


# ---- M6: train/val entity vocabulary leak -----------------------------------
@mutant("M6_VOCAB_LEAK", "CHK5")
def m6():
    orig = list(core.IDEAS["val"])
    core.IDEAS["val"][0:3] = core.IDEAS["train"][0:3]
    def restore():
        core.IDEAS["val"][:] = orig
    return restore


# ---- M7: order-independent QB_ORD answers -----------------------------------
@mutant("M7_ORDER_BLIND", "CHK8")
def m7():
    orig_graph = core.build_graph
    orig_solve = core.solve

    def patched_graph(rng, split, qfam):
        ops, spec = orig_graph(rng, split, qfam)
        if qfam == "QB_ORD":
            m1_ = spec["anchors"][0]
            objs = sorted(a[0] for c, a in ops
                          if c == "^2" and a[1] == m1_)
            spec = dict(spec, answer=objs[0])   # lexicographic, order-blind
        return ops, spec

    def patched_solve(ops, spec):
        if spec.get("qfam") == "QB_ORD":
            m1_ = spec["anchors"][0]
            twos = [k for k, (c, a) in enumerate(ops)
                    if c == "^2" and a[1] == m1_]
            assert len(twos) == 2, "ORD needs two ^2"
            objs = sorted(ops[k][1][0] for k in twos)
            k0 = next(k for k in twos if ops[k][1][0] == objs[0])
            return objs[0], [twos[0], k0]
        return orig_solve(ops, spec)
    import pathb_roundtrip as rt
    core.build_graph = patched_graph
    core.solve = patched_solve
    checks.solve = patched_solve
    rt.solve = patched_solve

    def restore():
        core.build_graph = orig_graph
        core.solve = orig_solve
        checks.solve = orig_solve
        rt.solve = orig_solve
    return restore


# ---- M8: renderer/parser template drift -------------------------------------
@mutant("M8_TEMPLATE_DRIFT", "B1_GRAPH", prereqs=("CHK8",))
def m8():
    orig = list(core.FORMS["^6"])
    core.FORMS["^6"][4] = "what {v} in two {p1}, {p2}, and {p3} was {i}."
    def restore():
        core.FORMS["^6"][:] = orig
    return restore


# ---- M9: candidate-order law broken (first-mention order) -------------------
@mutant("M9_CANDIDATE_ORDER", "CHK10")
def m9():
    def mut(rec):
        from pathb_core import entities_of
        ops = checks._ops_of(rec)
        minds, ideas, parts = entities_of(ops)
        rec["candidates"] = minds + ideas + parts
        return rec
    return _record_mutation(mut)


# ---- M10: profile channel leaks the answer index (composite key) ------------
@mutant("M10_PROFILE_ANSWER_KEY", "CHK7_BKEY", bkey=True)
def m10():
    """Composite key: the profile MARKS exactly the clauses containing the
    answer (labels[k]='^8' iff answer in clause k, else '^2'); combined with
    the membership matrix every arm receives, the answer is the candidate
    whose membership row matches the marked rows -- the canonical
    profile-completes-the-key defect."""
    def mut(rec):
        ops = checks._ops_of(rec)
        marks = []
        for c, a in ops:
            ents = ({a[0]} | set(a[1])) if c == "^6" else set(a)
            marks.append("^8" if rec["answer"] in ents else "^2")
        rec["idea_labels"] = marks
        return rec
    return _record_mutation(mut)


# ---- M11: INT anti-counting law broken (unique repeated part) ---------------
@mutant("M11_INT_COUNTING", "CHK9INT")
def m11():
    orig = core.build_graph

    def patched(rng, split, qfam):
        ops, spec = orig(rng, split, qfam)
        if qfam == "QB_INT":
            # make every ^6 list share ONLY the answer (no decoy repeats)
            pool = [p for p in core.PARTS[split]]
            used = {spec["answer"]}
            out = []
            for c, a in ops:
                if c == "^6":
                    keep = [spec["answer"]] if spec["answer"] in a[1] else []
                    fresh = []
                    for p in pool:
                        if p not in used and len(keep) + len(fresh) < 3:
                            fresh.append(p); used.add(p)
                    out.append((c, (a[0], tuple(keep + fresh))))
                else:
                    out.append((c, a))
            ops = out
        return ops, spec
    core.build_graph = patched
    return lambda: setattr(core, "build_graph", orig)


# ---- M12: duplicate passage-ids across question families --------------------
@mutant("M12_DUPLICATE_PIDS", "CHK11")
def m12():
    seen = {}

    def mut(rec):
        # renumber per (family, qfam) -- the ORIGINAL collision defect
        key = (rec["split"], rec["family"], rec["question_type"])
        k = seen.get(key, 0)
        seen[key] = k + 1
        rec["passage_id"] = f"{rec['split'][0]}{rec['family']}{k:06d}"
        return rec
    return _record_mutation(mut)


# ---- machinery --------------------------------------------------------------
_ACTIVE_RECORD_MUT = None


def _record_mutation(fn):
    global _ACTIVE_RECORD_MUT
    _ACTIVE_RECORD_MUT = fn

    def restore():
        global _ACTIVE_RECORD_MUT
        _ACTIVE_RECORD_MUT = None
    return restore


def _gen_with_active():
    return gen_small(mutate_record=_ACTIVE_RECORD_MUT)


def _bkey_small(tr, va):
    return checks.bkey_gate(tr, va)


def main():
    report = {"battery_id": "PATHB_CHK_M", "non_claim_bearing": True,
              "mutants": [], "clean_before": None, "clean_after": None,
              "clean_authority": "the FULL-dataset battery "
              "(PATHB_CHECKS_REPORT.json) is the authoritative clean CHK-7 "
              "reference; small-set CHK-7 is judged by PAIRED increment "
              "deltas only (small-n MLP instability)"}
    clean = run(include_bkey=False)
    tr0, va0 = gen_small()
    clean_bkey = _bkey_small(tr0, va0)
    report["clean_small_bkey_increments"] = {
        q: clean_bkey[q]["profile_increment"] for q in clean_bkey
        if q != "pass"}
    report["clean_before"] = {"failed_gates": clean["failed_gates"]}
    ok_all = not clean["failed_gates"]
    print(f"[clean-before] failed={clean['failed_gates']} "
          f"bkey_inc={report['clean_small_bkey_increments']}")
    for m in MUTANTS:
        restore = m["setup"]()
        try:
            tr, va = _gen_with_active()
            res = checks.run_battery(tr, va, include_bkey=False)
            failed = gates_failed(res)
            if m["bkey"]:
                mb = _bkey_small(tr, va)
                deltas = {q: mb[q]["profile_increment"]
                          - clean_bkey[q]["profile_increment"]
                          for q in mb if q != "pass"}
                margin = max(mb[q]["margin"] for q in mb if q != "pass")
                if any(d > margin for d in deltas.values()):
                    failed.add("CHK7_BKEY(paired-delta)")
                m["_deltas"] = deltas
        except SystemExit as exc:
            failed = {f"HARD_EXIT:{exc}"}
            res = None
        finally:
            restore()
        target_hit = any(m["target"] in f for f in failed)
        prereq_ok = all(not any(p in f for f in failed) for p in m["prereqs"]
                        if p != m["target"])
        crash_only = any(f.startswith("HARD_EXIT") for f in failed)
        verdict = bool(target_hit and prereq_ok and not crash_only)
        ok_all = ok_all and verdict
        row = {"id": m["id"], "target": m["target"],
               "failed_gates": sorted(failed),
               "target_caught_semantically": target_hit,
               "prerequisites_passed": prereq_ok,
               "crash_only": crash_only, "pass": verdict}
        report["mutants"].append(row)
        print(f"[{m['id']}] target={m['target']} caught={target_hit} "
              f"failed={sorted(failed)} -> {'PASS' if verdict else 'FAIL'}")
    clean2 = run(include_bkey=False)
    report["clean_after"] = {"failed_gates": clean2["failed_gates"]}
    ok_all = ok_all and not clean2["failed_gates"]
    print(f"[clean-after] failed={clean2['failed_gates']}")
    report["verdict"] = "CHK_M_PASS" if ok_all else "CHK_M_FAILED"
    (HERE / "PATHB_CHK_M_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nCHK-M VERDICT: {report['verdict']}")
    return 0 if ok_all else 4


if __name__ == "__main__":
    raise SystemExit(main())
