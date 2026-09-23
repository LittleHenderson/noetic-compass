"""D-1 acceptance tests A1-A6 (Claude, independent checker) of checker version 2 (builder: Codex).

The pass conditions are the ones fixed in `_handoffs/HELM_NEXT_PHASE_20260923/D1_CHECKER_V2_SPEC_AND_ACCEPTANCE.md`
section 3 BEFORE the build existed, plus the coverage Codex's handoff asked for
(`records/helm_peer_handoff_20260923/README.md`, "For D-1, include"), plus the fixes from Claude's own pre-launch
review (2026-09-23; see ../hset1a/BUILD_SPEC_v0_1.md section 6a and this folder's README). The verdict is emitted by
this program from measured values; nothing is decided in prose. Every test is wrapped: an unexpected error is recorded
as that test's FAILURE, and the result file is rewritten after every test, so no measured value is lost.

  A1  the five frozen files' LF sha256 equal the ORIGINAL anchors (Helm 2.0 source 20208c92, in --anchors); the frozen
      checker profile digest equals the historical anchor AND the original tree's (--frozen-profile-json, required);
      every imported module really comes from --v2-root
  A2  all 564 registry records: v2's accepted-answer sets equal the frozen checker's (witnesses and coverage reported);
      all 564 slot plans: slots_v2 output byte-identical to slots; all 6,768 saved predictions of the two historical
      studies: v2's `correct` equals the frozen checker's
  A3  5- and 6-node cases against Claude's independent oracle (brute-force canonical form + degree-refined
      backtracking): all 105 degree-colliding 5-node classes vs their partners; same-shape same-domain exclusion;
      NO_MATCH; full correspondence mapping sets; the answer cap pinned from both sides (EXACTLY 64 analogy answers
      accepted; 120 correspondence maps refused, never truncated); the node bound pinned from above (any 7-node world
      in scope is refused, never turned into NO_MATCH); random 6-node isomorphs and same-degree decoys; and the new
      slot-compiler path on 5- and 6-node correspondence packets (all n!+1 candidates offered, every accepted answer
      among them; the frozen compiler refuses them)
  A4  v2's checker and slot profiles have their own schemas and digests; MAX_ISOMORPHISM_NODES == 6;
      MAX_ADMISSIBLE_ANSWERS == 64; the S3 rule strings equal the frozen profile's; no v2 name contains "frozen"
  A5  one 5-node world in a bank no longer breaks analogy (frozen refuses); a public with 65 BANK worlds is refused by
      v2 itself with the exact bank-limit reason; a 64-world bank plus a separate focus is accepted; the frozen
      64-world training bank with a 5-node focus is refused by frozen and answered correctly by v2
  A6  1,000 five-node analogy questions, each on a 64-WORLD bank, single process, timed on this machine; maximum and
      total permutations checked; budget 600 s (Codex WORK_PLAN.md); every answer checked against the oracle
  X   (extra) v2 on every HSET-1A Stage 1 packet (reach, parts, edge_account at 3-5 nodes) equals the frozen gold.
      Sealed packets are reported as counts only, and v2 code runs there with its output captured and discarded.

Non-neural. Run inside the v2 package tree:

    python -B d1_acceptance_run.py --v2-root <CNCM root at the v2 commit> --anchors anchors.json \
        --frozen-profile-json profiles.json --hset-public HSET1A_CELLS_PUBLIC.json \
        --hset-sealed HSET1A_SEALED_TEST_NEW_5.json --out D1_ACCEPTANCE_RESULT.json
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import concurrent.futures.process
import contextlib
import hashlib
import io
import itertools
import json
import math
import multiprocessing
import os
import pathlib
import platform
import random
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
HSET_DIR = HERE.parent / "hset1a"
FROZEN_FILES = ("checker.py", "answers.py", "slots.py", "source.py", "pointer_inputs.py")
TT = "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/"
FROZEN_CHECKER_PROFILE_ANCHOR = "2c95354e62994fb8a0c0ab56254d1527f5f4d2c79ea5ecbed5679de730bd8a81"
S3_RULE_KEYS = ("graph_matching", "analogy_domain_rule", "tie_rule", "max_admissible_answers", "rules",
                "declaration_references", "graph_order", "process_order", "role_semantics")
STUDIES = {"helm1_certified": ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")],
           "helm2_experimental": ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]}
PHASES = ("course_p00", "course_p10")
A6_QUESTIONS, A6_BANK, A6_BUDGET_SECONDS = 1000, 64, 600.0
POOL_TOTAL_SECONDS = 2400


def lf_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _paths(v2_root):
    sys.dont_write_bytecode = True
    for p in (str(HERE), str(HSET_DIR), str(pathlib.Path(v2_root) / "research" / "CAS_META_2_COMPOSITION")):
        if p not in sys.path:
            sys.path.insert(0, p)


def run_pool(fn, tasks, *, processes, init_args, chunksize):
    """Map fn over tasks in spawned worker processes. A dead worker or a failed start-up raises BrokenProcessPool
    (never an endless restart), and the whole map is bounded by POOL_TOTAL_SECONDS. Attempt 1 on AWS failed here:
    on Python 3.14 `multiprocessing.Pool.imap_unordered` returns a plain generator with no `.next(timeout)`."""
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=processes, mp_context=multiprocessing.get_context("spawn"),
                                                      initializer=_init, initargs=init_args)
    rows = []
    try:
        for row in executor.map(fn, tasks, chunksize=chunksize, timeout=POOL_TOTAL_SECONDS):
            rows.append(row)
    except (concurrent.futures.process.BrokenProcessPool, TimeoutError) as error:
        executor.shutdown(wait=False, cancel_futures=True)
        raise RuntimeError("POOL_FAILED: %s after %d of %d" % (type(error).__name__, len(rows), len(tasks)))
    executor.shutdown(wait=True)
    return rows


# ============================================================================ workers
_S = {}


def _init(v2_root, want_material):
    _paths(v2_root)
    import hset_worlds as hw
    from cas_meta2.typed_teaching import (answers, checker, checker_v2, course, pointer_contract, slots, slots_v2,
                                          source)
    _, families = hw.vocabulary(source)
    _S.update(hw=hw, answers=answers, checker=checker, v2=checker_v2, course=course, slots=slots, slots_v2=slots_v2,
              source=source, bank=source.freeze_bank(families))
    if want_material:
        _S["material"] = pointer_contract.load_material(pathlib.Path(v2_root))[0]


def _a2_task(task):
    record_id, predictions = task
    hw, course, checker, v2 = _S["hw"], _S["course"], _S["checker"], _S["v2"]
    try:
        packet = course.model_packet(_S["material"], record_id)
        public, query = packet["source"], packet["record"]["query"]
        a, b = checker.derive_target(public, query), v2.derive_target(public, query)
        row = {"record_id": record_id, "kind": query["kind"],
               "answers_equal": hw.canon(a["admissible_answers"]) == hw.canon(b["admissible_answers"]),
               "witnesses_equal": hw.canon(a["witnesses"]) == hw.canon(b["witnesses"]),
               "coverage_equal": hw.canon(a["coverage"]) == hw.canon(b["coverage"]),
               "plan_bytes_equal": hw.canon(_S["slots"].compile_slots(packet)) == hw.canon(_S["slots_v2"].compile_slots(packet)),
               "predictions": len(predictions), "check_mismatches": []}
        for tag, answer in predictions:
            x = checker.check_answer(public, query, answer)["correct"]
            y = v2.check_answer(public, query, answer)["correct"]
            if x != y:
                row["check_mismatches"].append(tag)
        return row
    except Exception as error:  # noqa: BLE001
        return {"record_id": record_id, "error": "%s: %s" % (type(error).__name__, str(error)[:300])}


def _x_task(item):
    hw = _S["hw"]
    sink = io.StringIO()
    try:
        # v2 is builder-written code; whatever it prints on a sealed packet must not reach the public log.
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            packet, _, _ = hw.packet_from_item(_S["source"], _S["answers"], _S["course"], _S["bank"], item)
            if packet["record"]["record_id"] != item["evaluation"]["record_id"]:
                return {"item_id": item["item_id"], "error": "RECORD_ID_NOT_REPRODUCED"}
            target = _S["v2"].derive_target(packet["source"], packet["record"]["query"])
        values = [a["value"] for a in target["admissible_answers"]]
        return {"item_id": item["item_id"], "equal": len(values) == 1 and hw.canon(values[0]) == hw.canon(item["evaluation"]["gold"])}
    except Exception as error:  # noqa: BLE001
        return {"item_id": item["item_id"], "error": "%s: %s" % (type(error).__name__, str(error)[:300])}


# ============================================================================ worlds for A3/A5/A6
class Worlds:
    def __init__(self, hw, source, vocab, rng):
        self.hw, self.source, self.vocab, self.rng = hw, source, vocab, rng

    def make(self, n, edges, domain, relabel=True):
        """A world of shape (n, edges) in `domain`: random trained labels, random node order, whole = a root."""
        v = self.vocab[domain]
        labels = self.rng.sample(v["labels"], n)
        perm = list(range(n))
        if relabel:
            self.rng.shuffle(perm)
        e = [[perm[a], perm[b]] for a, b in edges]
        whole = self.rng.choice(self.hw.roots(n, [tuple(x) for x in e]))
        p2, p3 = self.rng.sample([x for x in range(n) if x != whole], 2)
        spec = {"labels": labels, "edges": e, "primary": [whole, p2, p3],
                "declarations": {"domain": domain, "kind": self.rng.choice(v["kinds"]), "setting": v["setting"],
                                 "function": v["function_template"] % {"whole": labels[whole], "child": labels[p2]}}}
        return self.hw.world_from_spec(self.source, spec)


def public_of(source, bank_worlds, focus):
    worlds = {w["world_id"]: w for w in bank_worlds}
    worlds[focus["world_id"]] = focus
    return {"focus_world_id": focus["world_id"], "worlds": [worlds[k] for k in sorted(worlds)],
            "bank": source._bank_record(bank_worlds)}


def oracle_graph(world):
    refs = sorted(node["ref"] for node in world["nodes"])
    index = {r: i for i, r in enumerate(refs)}
    return (len(refs), tuple(sorted((index[e["source"]], index[e["target"]]) for e in world["contains"]))), refs


def oracle_mappings(oracle, left, right):
    """All isomorphisms left -> right as sets of (source_ref, target_ref), by M2; existence cross-checked by M1."""
    (gl, rl), (gr, rr) = oracle_graph(left), oracle_graph(right)
    found = oracle.all_isomorphisms_m2(gl, gr)
    assert bool(found) == oracle.iso_m1(gl, gr), "ORACLE_METHODS_DISAGREE"
    return {frozenset((rl[a], rr[b]) for a, b in m.items()) for m in found}


def oracle_analogy(oracle, focus, bank_worlds):
    g, _ = oracle_graph(focus)
    hits = set()
    for w in bank_worlds:
        if w["declarations"]["domain"] == focus["declarations"]["domain"]:
            continue
        if oracle.is_isomorphic(g, oracle_graph(w)[0]):         # raises if the two methods disagree
            hits.add(w["world_id"])
    return hits or {None}


def analogy_query(answers, public, focus):
    return answers.compile_query(public, kind="analogy", focus_world_id=focus["world_id"])


def v2_analogy_set(v2, answers, public, focus):
    target = v2.derive_target(public, analogy_query(answers, public, focus))
    return {a["value"]["world_id"] for a in target["admissible_answers"]}, target


def correspondence_query(answers, public, focus, other):
    return answers.compile_query(public, kind="correspondence", arguments={"target_world_id": other["world_id"]},
                                 focus_world_id=focus["world_id"])


def as_mapping_set(target):
    out = set()
    for a in target["admissible_answers"]:
        value = a["value"]
        out.add("NO_MATCH" if value["status"] == "NO_MATCH" else frozenset((p["source"], p["target"]) for p in value["pairs"]))
    return out


def v2_correspondence_set(v2, answers, public, focus, other):
    return as_mapping_set(v2.derive_target(public, correspondence_query(answers, public, focus, other)))


def refusal(fn):
    """Run fn; return None if it returned, else the exception's exact text (its reason code)."""
    try:
        fn()
        return None
    except ValueError as error:                   # SemanticCheckError, AnswerContractError and source's ValueError
        return str(error)


def random_dag(rng, n, oracle):
    while True:
        order = list(range(n))
        rng.shuffle(order)
        pairs = [(order[i], order[j]) for i in range(n) for j in range(i + 1, n)]
        edges = tuple(sorted(p for p in pairs if rng.random() < 0.4))
        if edges and oracle._weakly_connected(n, edges):
            return edges


# ============================================================================ tests
def test_a1(ctx):
    checker, v2, slots, slots_v2, anchors, root = ctx["checker"], ctx["v2"], ctx["slots"], ctx["slots_v2"], ctx["anchors"], ctx["v2_root"]
    got = {n: lf_sha(root / TT / n) for n in FROZEN_FILES}
    frozen_profile = checker.checker_profile()["profile_digest"]
    original = json.loads(pathlib.Path(ctx["args"].frozen_profile_json).read_text(encoding="utf-8"))
    modules = {m.__name__: str(pathlib.Path(m.__file__).resolve()) for m in (checker, v2, slots, slots_v2, ctx["answers"], ctx["source"])}
    detail = {"files_sha256_lf": got, "files_equal_anchor": {n: got[n] == anchors["frozen_files_sha256_lf"][n] for n in FROZEN_FILES},
              "frozen_checker_profile_digest": frozen_profile,
              "profile_equals_historical_anchor": frozen_profile == FROZEN_CHECKER_PROFILE_ANCHOR,
              "original_tree_profiles": original,
              "checker_profile_equals_original_tree": original["checker_profile_digest"] == frozen_profile,
              "slot_profile_equals_original_tree": original["slot_profile_digest"] == slots.profile()["profile_digest"],
              "imported_module_files": modules,
              "all_modules_from_v2_root": all(pathlib.Path(p).is_relative_to(root.resolve()) for p in modules.values())}
    ok = (all(detail["files_equal_anchor"].values()) and detail["profile_equals_historical_anchor"]
          and detail["checker_profile_equals_original_tree"] and detail["slot_profile_equals_original_tree"]
          and detail["all_modules_from_v2_root"])
    return ok, detail


def test_a4(ctx):
    checker, v2, slots, slots_v2 = ctx["checker"], ctx["v2"], ctx["slots"], ctx["slots_v2"]
    fp, v2p, sp, s2p = checker.checker_profile(), v2.checker_profile(), slots.profile(), slots_v2.profile()
    names = ["checker_v2", "answers_v2", "slots_v2", v2.PROFILE_SCHEMA, slots_v2.PROFILE_SCHEMA, slots_v2.PLAN_SCHEMA,
             v2p["schema"], s2p["schema"]]
    detail = {"v2_checker_schema": v2p["schema"], "frozen_checker_schema": fp["schema"],
              "v2_checker_digest": v2p["profile_digest"], "frozen_checker_digest": fp["profile_digest"],
              "v2_slot_schema": s2p["schema"], "frozen_slot_schema": sp["schema"],
              "v2_slot_digest": s2p["profile_digest"], "frozen_slot_digest": sp["profile_digest"],
              "v2_max_isomorphism_nodes": v2.MAX_ISOMORPHISM_NODES, "v2_max_admissible_answers": v2.MAX_ADMISSIBLE_ANSWERS,
              "v2_profile_declares": {"max_isomorphism_nodes": v2p["max_isomorphism_nodes"],
                                      "max_admissible_answers": v2p["max_admissible_answers"]},
              "s3_rule_strings_equal_frozen": {k: v2p.get(k) == fp.get(k) for k in S3_RULE_KEYS},
              "names_checked": names, "no_name_contains_frozen": not any("frozen" in x.lower() for x in names),
              "shared_with_frozen_by_design": {"TARGET_SCHEMA": v2.TARGET_SCHEMA == checker.TARGET_SCHEMA,
                                               "CHECK_SCHEMA": v2.CHECK_SCHEMA == checker.CHECK_SCHEMA,
                                               "DECISION_SCHEMA": slots_v2.DECISION_SCHEMA == slots.DECISION_SCHEMA,
                                               "note": "the spec (S1) requires a distinct PROFILE; a v2 target or check is told "
                                                       "apart by the profile digest it carries"}}
    ok = (detail["v2_checker_schema"] != detail["frozen_checker_schema"] and detail["v2_checker_digest"] != detail["frozen_checker_digest"]
          and detail["v2_slot_schema"] != detail["frozen_slot_schema"] and detail["v2_slot_digest"] != detail["frozen_slot_digest"]
          and v2.MAX_ISOMORPHISM_NODES == 6 and v2.MAX_ADMISSIBLE_ANSWERS == 64
          and v2p["max_isomorphism_nodes"] == 6 and v2p["max_admissible_answers"] == 64
          and all(detail["s3_rule_strings_equal_frozen"].values()) and detail["no_name_contains_frozen"])
    return ok, detail


def test_a2(ctx):
    args, root = ctx["args"], ctx["v2_root"]
    by_record, files = collections.defaultdict(list), {}
    for study, receipts in STUDIES.items():
        for receipt in receipts:
            for ph in PHASES:
                path = root / "records/typed_pointer_001" / receipt / "collected/results/artifacts" / ("%s_predictions.json" % ph)
                files["%s/%s" % (receipt, ph)] = hashlib.sha256(path.read_bytes()).hexdigest()
                for k, p in enumerate(json.loads(path.read_text(encoding="utf-8"))["predictions"]):
                    by_record[p["record_id"]].append(("%s/%s/%s/%d" % (study, receipt, ph, k), p["answer"]))
    from cas_meta2.typed_teaching import pointer_contract
    registry = [row["record_id"] for row in pointer_contract.load_material(root)[0]["registry"]]
    tasks = [(rid, by_record.get(rid, [])) for rid in registry]
    if args.quick:
        tasks = tasks[:24]
    rows = run_pool(_a2_task, tasks, processes=args.processes, init_args=(str(root), True), chunksize=4)
    errors = [r for r in rows if "error" in r]
    ok_rows = [r for r in rows if "error" not in r]
    expected = sum(len(v) for v in by_record.values())
    detail = {"prediction_files_sha256": files,
              "prediction_files_equal_launch_anchor": {k: files[k] == ctx["anchors"]["prediction_files_sha256"].get(
                  "records/typed_pointer_001/%s/collected/results/artifacts/%s_predictions.json" % tuple(k.split("/"))) for k in files},
              "records": len(rows), "registry_records": len(registry), "errors": errors[:10], "error_count": len(errors),
              "answer_set_mismatches": [r["record_id"] for r in ok_rows if not r["answers_equal"]],
              "witness_differences": sum(1 for r in ok_rows if not r["witnesses_equal"]),
              "coverage_differences": sum(1 for r in ok_rows if not r["coverage_equal"]),
              "plan_byte_mismatches": [r["record_id"] for r in ok_rows if not r["plan_bytes_equal"]],
              "predictions_in_files": expected, "predictions_compared": sum(r["predictions"] for r in ok_rows),
              "prediction_mismatches": [m for r in ok_rows for m in r["check_mismatches"]],
              "records_without_predictions": [rid for rid in registry if rid not in by_record]}
    ok = (not args.quick and detail["error_count"] == 0 and len(registry) == 564 and detail["records"] == 564
          and not detail["answer_set_mismatches"] and not detail["plan_byte_mismatches"]
          and detail["predictions_compared"] == expected == 6768 and not detail["prediction_mismatches"]
          and all(detail["prediction_files_equal_launch_anchor"].values()))
    return ok, detail


def test_a3(ctx):
    hw, oracle, source, answers, course, v2, slots, slots_v2, W, rng = (
        ctx["hw"], ctx["oracle"], ctx["source"], ctx["answers"], ctx["course"], ctx["v2"], ctx["slots"], ctx["slots_v2"],
        ctx["W"], ctx["rng"])
    D, classes5, quick = hw.TRAINING_DOMAINS, ctx["classes5"], ctx["args"].quick
    d = {"analogy_questions": 0, "correspondence_questions": 0, "mismatches": [], "cap_cases": [], "bound_cases": [],
         "six_node_refusals": [], "slot_path_cases": []}

    def record(tag, ok, detail=None):
        if not ok:
            d["mismatches"].append([tag, detail])

    # (a)-(c): every degree-colliding 5-node class against its partners
    groups = sorted(oracle.degree_collisions(classes5).values())
    if quick:
        groups = groups[:3]
    tested = 0
    for gi, members in enumerate(groups):
        for xi, (n, edges) in enumerate(members):
            tested += 1
            d0, d1, d2, d3 = rng.sample(D, 4)
            focus, iso_other, iso_same = W.make(n, edges, d0), W.make(n, edges, d1), W.make(n, edges, d0)
            partners = [W.make(m, e, d2) for j, (m, e) in enumerate(members) if j != xi]
            extra = [W.make(5, classes5[rng.randrange(len(classes5))][1], d3) for _ in range(2)]
            bank = [iso_other, iso_same] + partners + extra
            public = public_of(source, bank, focus)
            got, _ = v2_analogy_set(v2, answers, public, focus)
            d["analogy_questions"] += 1
            record("colliding g%d x%d analogy" % (gi, xi), got == oracle_analogy(oracle, focus, bank))
            record("colliding g%d x%d same-domain isomorph excluded" % (gi, xi), iso_same["world_id"] not in got)
            record("colliding g%d x%d cross-domain isomorph found" % (gi, xi), iso_other["world_id"] in got)
            for other in [iso_other, iso_same] + partners:
                want = oracle_mappings(oracle, focus, other) or {"NO_MATCH"}
                d["correspondence_questions"] += 1
                record("colliding g%d x%d correspondence" % (gi, xi), v2_correspondence_set(v2, answers, public, focus, other) == want)
            nm_bank = [iso_same] + partners
            got_nm, _ = v2_analogy_set(v2, answers, public_of(source, nm_bank, focus), focus)
            d["analogy_questions"] += 1
            record("colliding g%d x%d NO_MATCH analogy" % (gi, xi), got_nm == {None} == oracle_analogy(oracle, focus, nm_bank))
    d["colliding_classes_tested"], d["colliding_groups_tested"] = tested, len(groups)

    # (d)/(e): the answer cap, pinned from both sides
    focus_shape = classes5[rng.randrange(len(classes5))][1]
    d0 = rng.choice(D)
    focus = W.make(5, focus_shape, d0)
    copies, tries = {}, 0
    while len(copies) < 64 and tries < 1000:
        tries += 1
        w = W.make(5, focus_shape, rng.choice([x for x in D if x != d0]))
        copies[w["world_id"]] = w
    bank64 = list(copies.values())
    got, target = v2_analogy_set(v2, answers, public_of(source, bank64, focus), focus)
    entry = {"case": "analogy_exactly_64_cross_domain_isomorphs", "bank_worlds": len(bank64), "v2_answers": len(got),
             "equal_oracle": got == oracle_analogy(oracle, focus, bank64)}
    entry["pass"] = len(bank64) == 64 and len(got) == 64 and entry["equal_oracle"]
    d["cap_cases"].append(entry)
    record("cap exactly 64", entry["pass"], entry)
    rich = {"star5_24": (5, [(0, i) for i in range(1, 5)]), "sink5_24": (5, [(i, 4) for i in range(4)]),
            "k24_6_48": (6, [(a, b) for a in (0, 1) for b in (2, 3, 4, 5)]), "k33_6_36": (6, [(a, b) for a in (0, 1, 2) for b in (3, 4, 5)]),
            "star6_120": (6, [(0, i) for i in range(1, 6)]), "sink6_120": (6, [(i, 5) for i in range(5)])}
    for name, (n, edges) in rich.items():
        d0, d1 = rng.sample(D, 2)
        focus, other = W.make(n, edges, d0), W.make(n, edges, d1)
        public = public_of(source, [other], focus)
        want = oracle_mappings(oracle, focus, other)
        entry = {"case": name, "oracle_mappings": len(want)}
        reason = refusal(lambda: entry.__setitem__("v2_set", v2_correspondence_set(v2, answers, public, focus, other)))
        got_set = entry.pop("v2_set", None)
        entry.update(v2_refused=reason, v2_answers=None if got_set is None else len(got_set))
        entry["pass"] = (reason is None and len(want) <= 64 and got_set == want) or \
                        (len(want) > 64 and reason == "TYPED_CHECKER_TARGET_SET_BOUND")
        d["cap_cases"].append(entry)
        record("cap %s" % name, entry["pass"], entry)

    # the node bound, pinned from above: any 7-node world in scope is refused, never quietly NO_MATCH
    seven = random_dag(rng, 7, oracle)
    d0, d1 = rng.sample(D, 2)
    f5 = W.make(5, classes5[rng.randrange(len(classes5))][1], d0)
    for name, bank, focus in (("seven_node_world_same_domain_in_bank", [W.make(7, seven, d0), W.make(5, classes5[0][1], d1)], f5),
                              ("seven_node_world_cross_domain_in_bank", [W.make(7, seven, d1), W.make(5, classes5[0][1], d1)], f5),
                              ("seven_node_focus", [W.make(5, classes5[0][1], d1)], W.make(7, seven, d0))):
        public = public_of(source, bank, focus)
        reason = refusal(lambda: v2.derive_target(public, analogy_query(answers, public, focus)))
        entry = {"case": name, "v2_refused": reason, "pass": reason == "TYPED_CHECKER_ISOMORPHISM_BOUND"}
        d["bound_cases"].append(entry)
        record("bound %s" % name, entry["pass"], entry)
    f7, t7 = W.make(7, seven, d0), W.make(7, seven, d1)
    public = public_of(source, [t7], f7)
    reason = refusal(lambda: v2.derive_target(public, correspondence_query(answers, public, f7, t7)))
    entry = {"case": "seven_node_correspondence", "v2_refused": reason, "pass": reason == "TYPED_CHECKER_ISOMORPHISM_BOUND"}
    d["bound_cases"].append(entry)
    record("bound seven correspondence", entry["pass"], entry)

    # random 6-node isomorphs and same-degree decoys
    six = [random_dag(rng, 6, oracle) for _ in range(40 if quick else 400)]
    by_degree = collections.defaultdict(list)
    for e in six:
        by_degree[oracle.degree_multiset(6, e)].append(e)
    questions = 0
    for i, e in enumerate(six[: (10 if quick else 150)]):
        d0, d1, d2 = rng.sample(D, 3)
        focus, iso = W.make(6, e, d0), W.make(6, e, d1)
        decoys = [W.make(6, x, d2) for x in by_degree[oracle.degree_multiset(6, e)] if not oracle.is_isomorphic((6, x), (6, e))][:2]
        bank = [iso] + decoys
        public = public_of(source, bank, focus)
        got, _ = v2_analogy_set(v2, answers, public, focus)
        record("six %d analogy" % i, got == oracle_analogy(oracle, focus, bank))
        for other in bank:
            want = oracle_mappings(oracle, focus, other) or {"NO_MATCH"}
            holder = {}
            reason = refusal(lambda: holder.__setitem__("s", v2_correspondence_set(v2, answers, public, focus, other)))
            if reason is None:
                record("six %d correspondence" % i, len(want) <= 64 and holder["s"] == want, [len(holder["s"]), len(want)])
            else:
                record("six %d correspondence refusal" % i, len(want) > 64 and reason == "TYPED_CHECKER_TARGET_SET_BOUND", [reason, len(want)])
                d["six_node_refusals"].append(len(want))
            questions += 1
    d["six_node_correspondence_questions"] = questions

    # the new slot-compiler path: 5- and 6-node correspondence packets
    six_shape = random_dag(rng, 6, oracle)
    while len(hw.automorphisms(6, six_shape)) > 64:                   # keep the accepted set under the cap
        six_shape = random_dag(rng, 6, oracle)
    for n, shape in ((5, classes5[rng.randrange(len(classes5))][1]), (5, (tuple((0, i) for i in range(1, 5)))),
                     (6, six_shape), (6, ((0, 1), (0, 2), (2, 3), (3, 4), (1, 5)))):
        d0, d1 = rng.sample(D, 2)
        focus, other = W.make(n, shape, d0), W.make(n, shape, d1)
        bank = {"worlds": [other], "bank": source._bank_record([other])}
        packet = hw.build_packet(source, answers, course, bank, focus, kind="correspondence", rule=None,
                                 arguments={"target_world_id": other["world_id"]}, cue="CUBE_FACE_4")
        entry = {"case": "slot_path_%d_nodes" % n}
        plan = slots_v2.compile_slots(packet)
        values = [row["value"] for row in plan["correspondence_candidates"]]
        target = v2.derive_target(packet["source"], packet["record"]["query"])
        accepted = [a["value"] for a in target["admissible_answers"]]
        entry.update(candidates=len(values), expected_candidates=math.factorial(n) + 1,
                     every_accepted_answer_offered=all(any(hw.canon(v) == hw.canon(a) for v in values) for a in accepted),
                     plan_schema=plan["schema"], frozen_compiler_refused=refusal(lambda: slots.compile_slots(packet)))
        entry["pass"] = (entry["candidates"] == entry["expected_candidates"] and entry["every_accepted_answer_offered"]
                         and plan["schema"] == slots_v2.PLAN_SCHEMA and entry["frozen_compiler_refused"] is not None)
        d["slot_path_cases"].append(entry)
        record(entry["case"], entry["pass"], entry)

    ok = (not quick and not d["mismatches"] and d["colliding_classes_tested"] == 105
          and any(c["case"] == "analogy_exactly_64_cross_domain_isomorphs" and c["pass"] for c in d["cap_cases"])
          and any(c["oracle_mappings"] > 64 and c["pass"] for c in d["cap_cases"] if "oracle_mappings" in c)
          and len(d["bound_cases"]) == 4 and all(c["pass"] for c in d["bound_cases"])
          and len(d["slot_path_cases"]) == 4 and all(c["pass"] for c in d["slot_path_cases"]))
    return ok, d


def test_a5(ctx):
    oracle, source, answers, checker, v2, W, rng, families = (ctx["oracle"], ctx["source"], ctx["answers"], ctx["checker"],
                                                              ctx["v2"], ctx["W"], ctx["rng"], ctx["families"])
    D, classes5 = ctx["hw"].TRAINING_DOMAINS, ctx["classes5"]
    d = {}
    fours = oracle.dag_classes(4)
    d0, d1 = rng.sample(D, 2)
    focus4 = W.make(4, fours[0][1], d0)
    bank_mixed = [W.make(4, s[1], d1) for s in fours[:4]] + [W.make(5, classes5[0][1], d1)]
    public = public_of(source, bank_mixed, focus4)
    d["frozen_on_bank_with_5_node_world"] = refusal(lambda: checker.derive_target(public, analogy_query(answers, public, focus4)))
    got, _ = v2_analogy_set(v2, answers, public, focus4)
    d["v2_on_bank_with_5_node_world_equals_oracle"] = got == oracle_analogy(oracle, focus4, bank_mixed)
    # 65 BANK worlds (the focus is one of them, so the world union is 65 and only the bank limit is violated)
    distinct = {}
    while len(distinct) < 65:
        w = W.make(5, classes5[rng.randrange(len(classes5))][1], rng.choice(D))
        distinct[w["world_id"]] = w
    big = list(distinct.values())
    ok_public = public_of(source, big[1:], big[0])                      # a valid public: 64 bank worlds + focus
    query = analogy_query(answers, ok_public, big[0])
    bad_public = {"focus_world_id": big[0]["world_id"], "worlds": sorted(big, key=lambda w: w["world_id"]),
                  "bank": source._bank_record(big)}
    d["v2_on_65_bank_worlds"] = refusal(lambda: v2.derive_target(bad_public, query))
    d["v2_on_64_bank_worlds_plus_focus"] = refusal(lambda: v2.derive_target(ok_public, query))
    focus5 = W.make(5, classes5[1][1], d0)
    training = source.freeze_bank(families)
    public = public_of(source, training["worlds"], focus5)
    d["frozen_on_training_bank_with_5_node_focus"] = refusal(lambda: checker.derive_target(public, analogy_query(answers, public, focus5)))
    got, _ = v2_analogy_set(v2, answers, public, focus5)
    d["v2_on_training_bank_with_5_node_focus"] = sorted(map(str, got))
    d["v2_on_training_bank_equals_oracle"] = got == oracle_analogy(oracle, focus5, training["worlds"])
    ok = (d["frozen_on_bank_with_5_node_world"] == "TYPED_CHECKER_ISOMORPHISM_BOUND"
          and d["v2_on_bank_with_5_node_world_equals_oracle"]
          and d["v2_on_65_bank_worlds"] == "TYPED_SOURCE_PUBLIC_BANK_REFS" and d["v2_on_64_bank_worlds_plus_focus"] is None
          and d["frozen_on_training_bank_with_5_node_focus"] == "TYPED_CHECKER_ISOMORPHISM_BOUND"
          and d["v2_on_training_bank_equals_oracle"])
    return ok, d


def test_a6(ctx):
    oracle, source, answers, v2, W, rng, hw = ctx["oracle"], ctx["source"], ctx["answers"], ctx["v2"], ctx["W"], ctx["rng"], ctx["hw"]
    D, classes5, quick = hw.TRAINING_DOMAINS, ctx["classes5"], ctx["args"].quick
    pool_worlds = list({w["world_id"]: w for w in (W.make(5, classes5[rng.randrange(len(classes5))][1], rng.choice(D))
                                                   for _ in range(1500))}.values())
    count = 20 if quick else A6_QUESTIONS
    questions = []
    for _ in range(count):
        chosen = rng.sample(range(len(pool_worlds)), A6_BANK + 1)
        bank, focus = [pool_worlds[i] for i in chosen[1:]], pool_worlds[chosen[0]]
        public = public_of(source, bank, focus)
        questions.append((public, analogy_query(answers, public, focus), focus, bank))
    t = time.monotonic()
    targets = [v2.derive_target(public, query) for public, query, _, _ in questions]
    timed = time.monotonic() - t
    perms = [sum(x["permutations_checked"] for x in tg["coverage"]["decisions"]) for tg in targets]
    oracle_ok = sum(1 for tg, (_, _, focus, bank) in zip(targets, questions)
                    if {a["value"]["world_id"] for a in tg["admissible_answers"]} == oracle_analogy(oracle, focus, bank))
    six_pool = list({w["world_id"]: w for w in (W.make(6, random_dag(rng, 6, oracle), rng.choice(D)) for _ in range(300))}.values())
    six_q = []
    for _ in range(10 if quick else 100):
        chosen = rng.sample(range(len(six_pool)), A6_BANK + 1)
        public = public_of(source, [six_pool[i] for i in chosen[1:]], six_pool[chosen[0]])
        six_q.append((public, analogy_query(answers, public, six_pool[chosen[0]])))
    t = time.monotonic()
    six_targets = [v2.derive_target(p, q) for p, q in six_q]
    six_timed = time.monotonic() - t
    d = {"questions": count, "bank_worlds_per_question": A6_BANK, "nodes": 5, "single_process_seconds": round(timed, 3),
         "budget_seconds": A6_BUDGET_SECONDS, "budget_source": "Codex records/helm_stage2_checker_20260923/WORK_PLAN.md",
         "max_permutations_per_question": max(perms), "total_permutations": sum(perms), "answers_equal_oracle": oracle_ok,
         "device": ctx["machine"], "six_node_questions": len(six_q), "six_node_seconds": round(six_timed, 3),
         "six_node_max_permutations_per_question": max(sum(x["permutations_checked"] for x in tg["coverage"]["decisions"]) for tg in six_targets),
         "builder_benchmark_for_comparison": "Codex: 1,000 questions, 3 worlds per bank, 23.554114344 s on t3.large (README)"}
    return (not quick and timed <= A6_BUDGET_SECONDS and oracle_ok == count), d


def test_x(ctx):
    args = ctx["args"]
    items, sealed_ids = [], set()
    for path, secret in ((args.hset_public, False), (args.hset_sealed, True)):
        if path:
            rows = [i for i in json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["items"] if i.get("evaluation")]
            items += rows
            if secret:
                sealed_ids |= {i["item_id"] for i in rows}
    if args.quick:
        items = items[:40]
    if not items:
        return None, {"skipped": "no HSET-1A files"}
    xs = run_pool(_x_task, items, processes=args.processes, init_args=(str(ctx["v2_root"]), False), chunksize=16)
    # Custody: a sealed item id carries a fingerprint of a secret shape, so sealed rows are reported as counts only.
    d = {"packets": len(xs), "equal": sum(1 for r in xs if r.get("equal")),
         "sealed_packets": sum(1 for r in xs if r["item_id"] in sealed_ids),
         "sealed_equal": sum(1 for r in xs if r["item_id"] in sealed_ids and r.get("equal")),
         "public_errors": [r for r in xs if "error" in r and r["item_id"] not in sealed_ids][:10],
         "sealed_error_count": sum(1 for r in xs if "error" in r and r["item_id"] in sealed_ids),
         "sealed_error_types": sorted({r["error"].split(":")[0] for r in xs if "error" in r and r["item_id"] in sealed_ids})}
    return d["equal"] == d["packets"], d


# ============================================================================ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2-root", required=True)
    ap.add_argument("--anchors", required=True, help="JSON: LF sha256 of the five frozen files at the original source commit")
    ap.add_argument("--frozen-profile-json", required=True, help="frozen_profiles.py output from the ORIGINAL tree")
    ap.add_argument("--hset-public", default=None)
    ap.add_argument("--hset-sealed", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--processes", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--quick", action="store_true", help="smoke only: tiny A2/A3/A6; the verdict is then never ACCEPTED")
    args = ap.parse_args()
    t0 = time.monotonic()
    v2_root = pathlib.Path(args.v2_root).resolve()
    _paths(v2_root)
    import hset_worlds as hw
    import oracle_isomorphism as oracle
    from cas_meta2.typed_teaching import answers, checker, checker_v2 as v2, course, slots, slots_v2, source
    vocab, families = hw.vocabulary(source)
    machine = {"python": platform.python_version(), "platform": platform.platform(), "cpus": os.cpu_count(),
               "cpu_model": next((line.split(":", 1)[1].strip() for line in open("/proc/cpuinfo") if line.startswith("model name")), None)
               if pathlib.Path("/proc/cpuinfo").is_file() else platform.processor()}
    ctx = {"args": args, "v2_root": v2_root, "hw": hw, "oracle": oracle, "answers": answers, "checker": checker, "v2": v2,
           "course": course, "slots": slots, "slots_v2": slots_v2, "source": source, "families": families, "machine": machine,
           "anchors": json.loads(pathlib.Path(args.anchors).read_text(encoding="utf-8")), "rng": random.Random(20260923),
           "classes5": oracle.dag_classes(5)}
    ctx["W"] = Worlds(hw, source, vocab, ctx["rng"])
    result = {"schema": "claude.d1-acceptance/0.2", "v2_root": str(v2_root), "anchors": ctx["anchors"], "machine": machine,
              "quick": args.quick, "v2_files_sha256_lf": {n: lf_sha(v2_root / TT / n) for n in ("checker_v2.py", "answers_v2.py", "slots_v2.py")},
              "verdict": {}, "seconds_per_test": {}}

    def write():
        result["seconds"] = round(time.monotonic() - t0, 1)
        with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(result, indent=1, sort_keys=True, default=str))

    for name, fn in (("A1", test_a1), ("A4", test_a4), ("A2", test_a2), ("A3", test_a3), ("A5", test_a5), ("A6", test_a6),
                     ("X_hset1a_crosscheck", test_x)):
        t = time.monotonic()
        try:
            ok, detail = fn(ctx)
        except Exception as error:  # noqa: BLE001 -- an unexpected error is that test's FAILURE, never a skipped test
            ok, detail = False, {"error": "%s: %s" % (type(error).__name__, str(error)[:500]),
                                 "traceback_tail": traceback.format_exc().splitlines()[-6:]}
        result[name] = detail
        if ok is not None:
            result["verdict"][name] = bool(ok)
        result["seconds_per_test"][name] = round(time.monotonic() - t, 1)
        print(name, ok, "(%.0f s)" % result["seconds_per_test"][name], flush=True)
        write()
    required = ("A1", "A2", "A3", "A4", "A5", "A6")
    result["acceptance"] = "ACCEPTED" if not args.quick and all(result["verdict"].get(k) for k in required) else "NOT_ACCEPTED"
    write()
    print(json.dumps({"acceptance": result["acceptance"], "verdict": result["verdict"], "seconds": result["seconds"]}), flush=True)
    return 0 if result["acceptance"] == "ACCEPTED" else 3


if __name__ == "__main__":
    sys.exit(main())
