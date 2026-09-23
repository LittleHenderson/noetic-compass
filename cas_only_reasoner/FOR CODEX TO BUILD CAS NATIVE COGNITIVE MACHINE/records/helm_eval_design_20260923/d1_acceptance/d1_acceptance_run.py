"""D-1 acceptance tests A1-A6 (Claude, independent checker) of checker version 2 (builder: Codex).

The pass conditions are the ones fixed in `_handoffs/HELM_NEXT_PHASE_20260923/D1_CHECKER_V2_SPEC_AND_ACCEPTANCE.md`
section 3 BEFORE the build existed, plus the coverage Codex's handoff asked for
(`records/helm_peer_handoff_20260923/README.md`, "For D-1, include"). The verdict is emitted by this program from the
measured values; nothing is decided in prose.

  A1  the five frozen files' LF sha256 equal the ORIGINAL anchors (Helm 2.0 source 20208c92, passed in --anchors),
      and the frozen checker's profile digest equals the historical anchor recorded in the Helm receipts
  A2  all 564 registry records: v2's accepted-answer sets equal the frozen checker's (witnesses and coverage reported);
      all 564 slot plans: slots_v2 output is byte-identical to slots; all 6,768 saved predictions of the two historical
      studies: v2's `correct` equals the frozen checker's
  A3  5- and 6-node cases against Claude's independent oracle (two methods: brute-force canonical form, degree-refined
      backtracking): every one of the 105 degree-colliding 5-node classes vs its partners, same-shape same-domain
      exclusion, NO_MATCH, full correspondence mapping sets, automorphism-rich shapes at or below the 64-answer cap,
      and shapes above the cap (must be refused, never truncated); plus random 6-node isomorphs and decoys
  A4  v2's checker and slot profile schemas and digests differ from the frozen ones; no v2 name contains "frozen"
  A5  one 5-node world in a bank no longer breaks analogy (the frozen checker refuses it); a bank of 65 worlds is still
      refused; the frozen 64-world training bank with a 5-node focus is answered by v2 and refused by the frozen checker
  A6  1,000 five-node analogy questions, each on a 64-WORLD bank, single process, timed on this machine; maximum and
      total permutations checked; budget 600 s (Codex WORK_PLAN.md). Every answer is also checked against the oracle
  X   (extra) v2 on every HSET-1A Stage 1 packet (reach, parts, edge_account at 3-5 nodes): same answer as the frozen gold

Non-neural. Run inside the v2 package tree:

    python -B d1_acceptance_run.py --v2-root <CNCM root at the v2 commit> --anchors anchors.json \
        --hset-public HSET1A_CELLS_PUBLIC.json --hset-sealed HSET1A_SEALED_TEST_NEW_5.json --out D1_ACCEPTANCE_RESULT.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import multiprocessing
import os
import pathlib
import platform
import random
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
HSET_DIR = HERE.parent / "hset1a"
FROZEN_FILES = ("checker.py", "answers.py", "slots.py", "source.py", "pointer_inputs.py")
TT = "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/"
FROZEN_CHECKER_PROFILE_ANCHOR = "2c95354e62994fb8a0c0ab56254d1527f5f4d2c79ea5ecbed5679de730bd8a81"
STUDIES = {"helm1_certified": ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")],
           "helm2_experimental": ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]}
PHASES = ("course_p00", "course_p10")
A6_QUESTIONS, A6_BANK, A6_BUDGET_SECONDS = 1000, 64, 600.0


def lf_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _paths(v2_root):
    sys.dont_write_bytecode = True
    for p in (str(HERE), str(HSET_DIR), str(pathlib.Path(v2_root) / "research" / "CAS_META_2_COMPOSITION")):
        if p not in sys.path:
            sys.path.insert(0, p)


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
    try:
        packet, _, _ = hw.packet_from_item(_S["source"], _S["answers"], _S["course"], _S["bank"], item)
        if packet["record"]["record_id"] != item["evaluation"]["record_id"]:
            return {"item_id": item["item_id"], "error": "RECORD_ID_NOT_REPRODUCED"}
        target = _S["v2"].derive_target(packet["source"], packet["record"]["query"])
        values = [a["value"] for a in target["admissible_answers"]]
        return {"item_id": item["item_id"], "equal": len(values) == 1 and hw.canon(values[0]) == hw.canon(item["evaluation"]["gold"])}
    except Exception as error:  # noqa: BLE001
        return {"item_id": item["item_id"], "error": "%s: %s" % (type(error).__name__, str(error)[:300])}


# ============================================================================ world construction for A3/A5/A6
class Worlds:
    def __init__(self, hw, source, vocab, rng):
        self.hw, self.source, self.vocab, self.rng = hw, source, vocab, rng

    def make(self, n, edges, domain, relabel=True):
        """A world of shape (n, edges) in `domain`: random labels from the trained vocabulary, random node order."""
        v = self.vocab[domain]
        labels = self.rng.sample(v["labels"], n)
        perm = list(range(n))
        if relabel:
            self.rng.shuffle(perm)                         # structural node i becomes world node perm[i]
        e = [[perm[a], perm[b]] for a, b in edges]
        roots = self.hw.roots(n, [tuple(x) for x in e])
        whole = self.rng.choice(roots)
        others = [x for x in range(n) if x != whole]
        p2, p3 = self.rng.sample(others, 2)
        spec = {"labels": labels, "edges": e, "primary": [whole, p2, p3],
                "declarations": {"domain": domain, "kind": self.rng.choice(v["kinds"]), "setting": v["setting"],
                                 "function": v["function_template"] % {"whole": labels[whole], "child": labels[p2]}}}
        world = self.hw.world_from_spec(self.source, spec)
        refs = self.hw.node_refs(world, spec)
        graph = (n, frozenset((refs.index(a_ref), refs.index(b_ref)) for a_ref, b_ref in
                              ((edge["source"], edge["target"]) for edge in world["contains"])))
        return world, refs, graph


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
    """All isomorphisms left -> right as sets of (source_ref, target_ref), by M2, with the count checked by M1."""
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
        h, _ = oracle_graph(w)
        if oracle.is_isomorphic(g, h):                          # raises if the two methods disagree
            hits.add(w["world_id"])
    return hits or {None}


def v2_analogy_set(v2, answers, public, focus):
    query = answers.compile_query(public, kind="analogy", focus_world_id=focus["world_id"])
    target = v2.derive_target(public, query)
    return {a["value"]["world_id"] for a in target["admissible_answers"]}, target


def v2_correspondence_set(v2, answers, public, focus, other):
    query = answers.compile_query(public, kind="correspondence", arguments={"target_world_id": other["world_id"]},
                                  focus_world_id=focus["world_id"])
    target = v2.derive_target(public, query)
    out = set()
    for a in target["admissible_answers"]:
        value = a["value"]
        out.add("NO_MATCH" if value["status"] == "NO_MATCH" else frozenset((p["source"], p["target"]) for p in value["pairs"]))
    return out


def random_dag(rng, n, hw, oracle):
    while True:
        order = list(range(n))
        rng.shuffle(order)
        pairs = [(order[i], order[j]) for i in range(n) for j in range(i + 1, n)]
        edges = tuple(sorted(p for p in pairs if rng.random() < 0.4))
        if edges and oracle._weakly_connected(n, edges):
            return edges


# ============================================================================ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2-root", required=True)
    ap.add_argument("--anchors", required=True, help="JSON: LF sha256 of the five frozen files at the original source commit")
    ap.add_argument("--frozen-profile-json", default=None, help="JSON from the ORIGINAL tree: checker and slot profile digests")
    ap.add_argument("--hset-public", default=None)
    ap.add_argument("--hset-sealed", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--processes", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--quick", action="store_true", help="smoke only: tiny A2/A3/A6")
    args = ap.parse_args()
    t0 = time.monotonic()
    v2_root = pathlib.Path(args.v2_root).resolve()
    _paths(v2_root)
    import hset_worlds as hw
    import oracle_isomorphism as oracle
    from cas_meta2.typed_teaching import answers, checker, checker_v2 as v2, slots, slots_v2, source
    anchors = json.loads(pathlib.Path(args.anchors).read_text(encoding="utf-8"))
    result = {"schema": "claude.d1-acceptance/0.1", "v2_root": str(v2_root), "anchors": anchors,
              "machine": {"python": platform.python_version(), "platform": platform.platform(), "cpus": os.cpu_count(),
                          "cpu_model": next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), None)
                          if pathlib.Path("/proc/cpuinfo").is_file() else platform.processor()},
              "v2_files_sha256_lf": {n: lf_sha(v2_root / TT / n) for n in ("checker_v2.py", "answers_v2.py", "slots_v2.py")}}
    verdict = {}

    # ---------------------------------------------------------------- A1
    got = {n: lf_sha(v2_root / TT / n) for n in FROZEN_FILES}
    frozen_profile = checker.checker_profile()["profile_digest"]
    a1 = {"files_sha256_lf": got, "files_equal_anchor": {n: got[n] == anchors["frozen_files_sha256_lf"][n] for n in FROZEN_FILES},
          "frozen_checker_profile_digest": frozen_profile,
          "profile_equals_historical_anchor": frozen_profile == FROZEN_CHECKER_PROFILE_ANCHOR}
    if args.frozen_profile_json:
        original = json.loads(pathlib.Path(args.frozen_profile_json).read_text(encoding="utf-8"))
        a1["original_tree_profiles"] = original
        a1["checker_profile_equals_original_tree"] = original["checker_profile_digest"] == frozen_profile
        a1["slot_profile_equals_original_tree"] = original["slot_profile_digest"] == slots.profile()["profile_digest"]
    verdict["A1"] = all(a1["files_equal_anchor"].values()) and a1["profile_equals_historical_anchor"] and \
        a1.get("checker_profile_equals_original_tree", True) and a1.get("slot_profile_equals_original_tree", True)
    result["A1"] = a1
    print("A1", verdict["A1"], flush=True)

    # ---------------------------------------------------------------- A4
    v2p, sp, s2p = v2.checker_profile(), slots.profile(), slots_v2.profile()
    names = ["checker_v2", "answers_v2", "slots_v2", v2.PROFILE_SCHEMA, slots_v2.PROFILE_SCHEMA, slots_v2.PLAN_SCHEMA,
             v2p["schema"], s2p["schema"]]
    a4 = {"v2_checker_schema": v2p["schema"], "frozen_checker_schema": checker.checker_profile()["schema"],
          "v2_checker_digest": v2p["profile_digest"], "frozen_checker_digest": frozen_profile,
          "v2_slot_schema": s2p["schema"], "frozen_slot_schema": sp["schema"],
          "v2_slot_digest": s2p["profile_digest"], "frozen_slot_digest": sp["profile_digest"],
          "v2_max_isomorphism_nodes": v2.MAX_ISOMORPHISM_NODES, "names_checked": names,
          "no_name_contains_frozen": not any("frozen" in x.lower() for x in names)}
    verdict["A4"] = (a4["v2_checker_schema"] != a4["frozen_checker_schema"] and a4["v2_checker_digest"] != frozen_profile
                     and a4["v2_slot_schema"] != a4["frozen_slot_schema"] and a4["v2_slot_digest"] != a4["frozen_slot_digest"]
                     and a4["no_name_contains_frozen"])
    result["A4"] = a4
    print("A4", verdict["A4"], flush=True)

    ctx = multiprocessing.get_context("spawn")
    # ---------------------------------------------------------------- A2
    t = time.monotonic()
    by_record = collections.defaultdict(list)
    files = {}
    for study, receipts in STUDIES.items():
        for receipt in receipts:
            for ph in PHASES:
                path = v2_root / "records/typed_pointer_001" / receipt / "collected/results/artifacts" / ("%s_predictions.json" % ph)
                files["%s/%s" % (receipt, ph)] = hashlib.sha256(path.read_bytes()).hexdigest()
                for k, p in enumerate(json.loads(path.read_text(encoding="utf-8"))["predictions"]):
                    by_record[p["record_id"]].append(("%s/%s/%s/%d" % (study, receipt, ph, k), p["answer"]))
    from cas_meta2.typed_teaching import pointer_contract
    registry = [row["record_id"] for row in pointer_contract.load_material(v2_root)[0]["registry"]]
    tasks = [(rid, by_record.get(rid, [])) for rid in registry]
    if args.quick:
        tasks = tasks[:24]
    with ctx.Pool(args.processes, initializer=_init, initargs=(str(v2_root), True)) as pool:
        rows = list(pool.imap_unordered(_a2_task, tasks, chunksize=4))
    errors = [r for r in rows if "error" in r]
    ok = [r for r in rows if "error" not in r]
    a2 = {"prediction_files_sha256": files, "records": len(rows), "registry_records": len(registry), "errors": errors[:10],
          "error_count": len(errors),
          "answer_set_mismatches": [r["record_id"] for r in ok if not r["answers_equal"]],
          "witness_differences": sum(1 for r in ok if not r["witnesses_equal"]),
          "coverage_differences": sum(1 for r in ok if not r["coverage_equal"]),
          "plan_byte_mismatches": [r["record_id"] for r in ok if not r["plan_bytes_equal"]],
          "predictions_compared": sum(r["predictions"] for r in ok),
          "prediction_mismatches": [m for r in ok for m in r["check_mismatches"]],
          "records_without_predictions": [rid for rid in registry if rid not in by_record],
          "seconds": round(time.monotonic() - t, 1)}
    expected_predictions = sum(len(v) for v in by_record.values())
    a2["predictions_in_files"] = expected_predictions
    verdict["A2"] = (not args.quick and a2["error_count"] == 0 and len(registry) == 564 and a2["records"] == 564
                     and not a2["answer_set_mismatches"] and not a2["plan_byte_mismatches"]
                     and a2["predictions_compared"] == expected_predictions == 6768 and not a2["prediction_mismatches"])
    result["A2"] = a2
    print("A2", verdict["A2"], "(%.0f s)" % a2["seconds"], flush=True)

    # ---------------------------------------------------------------- A3 / A5 / A6 need worlds
    vocab, families = hw.vocabulary(source)
    rng = random.Random(20260923)
    W = Worlds(hw, source, vocab, rng)
    D = hw.TRAINING_DOMAINS
    classes5 = oracle.dag_classes(5)
    groups = oracle.degree_collisions(classes5)
    a3 = {"analogy_questions": 0, "correspondence_questions": 0, "mismatches": [], "cap_cases": [], "refusals": []}

    def record(tag, ok, detail=None):
        if not ok:
            a3["mismatches"].append([tag, detail])

    t = time.monotonic()
    group_list = sorted(groups.values())
    if args.quick:
        group_list = group_list[:3]
    colliding_classes = 0
    for gi, members in enumerate(group_list):
        for xi, (n, edges) in enumerate(members):
            colliding_classes += 1
            d0, d1, d2, d3 = rng.sample(D, 4)
            focus, _, _ = W.make(n, edges, d0)
            iso_other, _, _ = W.make(n, edges, d1)
            iso_same, _, _ = W.make(n, edges, d0)
            partners = [W.make(m, e, d2)[0] for j, (m, e) in enumerate(members) if j != xi]
            extra = [W.make(5, classes5[rng.randrange(len(classes5))][1], d3)[0] for _ in range(2)]
            bank_worlds = [iso_other, iso_same] + partners + extra
            public = public_of(source, bank_worlds, focus)
            got_set, _ = v2_analogy_set(v2, answers, public, focus)
            want = oracle_analogy(oracle, focus, bank_worlds)
            a3["analogy_questions"] += 1
            record("colliding g%d x%d analogy" % (gi, xi), got_set == want, [sorted(map(str, got_set)), sorted(map(str, want))])
            record("colliding g%d x%d same-domain isomorph excluded" % (gi, xi), iso_same["world_id"] not in got_set)
            for other in [iso_other, iso_same] + partners:
                got_c = v2_correspondence_set(v2, answers, public, focus, other)
                want_c = oracle_mappings(oracle, focus, other) or {"NO_MATCH"}
                a3["correspondence_questions"] += 1
                record("colliding g%d x%d correspondence" % (gi, xi), got_c == want_c, [len(got_c), len(want_c)])
            # NO_MATCH analogy: only the same-domain isomorph and non-isomorphic partners are in the bank
            nm_bank = [iso_same] + partners
            nm_public = public_of(source, nm_bank, focus)
            got_nm, _ = v2_analogy_set(v2, answers, nm_public, focus)
            a3["analogy_questions"] += 1
            record("colliding g%d x%d NO_MATCH analogy" % (gi, xi), got_nm == {None} == oracle_analogy(oracle, focus, nm_bank))
    a3["colliding_classes_tested"] = colliding_classes
    a3["colliding_groups_tested"] = len(group_list)

    # automorphism-rich shapes: at or below the cap, and above it
    rich = {"star5_24": (5, [(0, i) for i in range(1, 5)]), "sink5_24": (5, [(i, 4) for i in range(4)]),
            "k24_6_48": (6, [(a, b) for a in (0, 1) for b in (2, 3, 4, 5)]), "k33_6_36": (6, [(a, b) for a in (0, 1, 2) for b in (3, 4, 5)]),
            "star6_120": (6, [(0, i) for i in range(1, 6)]), "sink6_120": (6, [(i, 5) for i in range(5)])}
    for name, (n, edges) in rich.items():
        d0, d1 = rng.sample(D, 2)
        focus, _, _ = W.make(n, edges, d0)
        other, _, _ = W.make(n, edges, d1)
        public = public_of(source, [other], focus)
        want = oracle_mappings(oracle, focus, other)
        entry = {"shape": name, "oracle_mappings": len(want)}
        try:
            got = v2_correspondence_set(v2, answers, public, focus, other)
            entry.update(v2_answers=len(got), equal=got == want)
            ok = len(want) <= 64 and got == want
        except v2.SemanticCheckError as error:
            entry.update(v2_refused=str(error))
            ok = len(want) > 64 and str(error) == "TYPED_CHECKER_TARGET_SET_BOUND"
        entry["pass"] = ok
        a3["cap_cases"].append(entry)
        record("cap %s" % name, ok, entry)
    a3["cap_cases_at_or_below_64"] = sum(1 for e in a3["cap_cases"] if e["oracle_mappings"] <= 64)
    a3["cap_cases_above_64"] = sum(1 for e in a3["cap_cases"] if e["oracle_mappings"] > 64)

    # random 6-node isomorphs and same-degree decoys
    six = [random_dag(rng, 6, hw, oracle) for _ in range(40 if args.quick else 400)]
    by_degree = collections.defaultdict(list)
    for e in six:
        by_degree[oracle.degree_multiset(6, e)].append(e)
    six_questions = 0
    for i, e in enumerate(six[: (10 if args.quick else 150)]):
        d0, d1, d2 = rng.sample(D, 3)
        focus, _, _ = W.make(6, e, d0)
        iso, _, _ = W.make(6, e, d1)
        decoys = [x for x in by_degree[oracle.degree_multiset(6, e)] if not oracle.is_isomorphic((6, x), (6, e))][:2]
        decoy_worlds = [W.make(6, x, d2)[0] for x in decoys]
        bank_worlds = [iso] + decoy_worlds
        public = public_of(source, bank_worlds, focus)
        got_set, _ = v2_analogy_set(v2, answers, public, focus)
        record("six %d analogy" % i, got_set == oracle_analogy(oracle, focus, bank_worlds))
        for other in [iso] + decoy_worlds:
            want = oracle_mappings(oracle, focus, other) or {"NO_MATCH"}
            try:
                got = v2_correspondence_set(v2, answers, public, focus, other)
                record("six %d correspondence" % i, len(want) <= 64 and got == want, [len(got), len(want)])
            except v2.SemanticCheckError as error:
                record("six %d correspondence refusal" % i, len(want) > 64 and str(error) == "TYPED_CHECKER_TARGET_SET_BOUND",
                       [str(error), len(want)])
                a3["refusals"].append(len(want))
            six_questions += 1
    a3["six_node_correspondence_questions"] = six_questions
    a3["six_node_decoys_found"] = sum(1 for e in six[:150] if any(not oracle.is_isomorphic((6, x), (6, e))
                                                                    for x in by_degree[oracle.degree_multiset(6, e)]))
    a3["seconds"] = round(time.monotonic() - t, 1)
    verdict["A3"] = (not args.quick and not a3["mismatches"] and a3["colliding_classes_tested"] == 105
                     and a3["cap_cases_at_or_below_64"] >= 1 and a3["cap_cases_above_64"] >= 1)
    result["A3"] = a3
    print("A3", verdict["A3"], "mismatches", len(a3["mismatches"]), "(%.0f s)" % a3["seconds"], flush=True)

    # ---------------------------------------------------------------- A5
    a5 = {}
    fours = [s for s in oracle.dag_classes(4)]
    d0, d1 = rng.sample(D, 2)
    focus4, _, _ = W.make(4, fours[0][1], d0)
    bank_mixed = [W.make(4, s[1], d1)[0] for s in fours[:4]] + [W.make(5, classes5[0][1], d1)[0]]
    public = public_of(source, bank_mixed, focus4)
    query = answers.compile_query(public, kind="analogy", focus_world_id=focus4["world_id"])
    try:
        checker.derive_target(public, query)
        a5["frozen_on_bank_with_5_node_world"] = "ANSWERED"
    except checker.SemanticCheckError as error:
        a5["frozen_on_bank_with_5_node_world"] = "REFUSED:" + str(error)
    got_set, _ = v2_analogy_set(v2, answers, public, focus4)
    a5["v2_on_bank_with_5_node_world_equals_oracle"] = got_set == oracle_analogy(oracle, focus4, bank_mixed)
    big_bank = [W.make(5, classes5[rng.randrange(len(classes5))][1], rng.choice(D))[0] for _ in range(65)]
    focus5, _, _ = W.make(5, classes5[1][1], d0)
    try:
        public = public_of(source, big_bank, focus5)
        v2.derive_target(public, answers.compile_query(public, kind="analogy", focus_world_id=focus5["world_id"]))
        a5["v2_on_65_world_bank"] = "ANSWERED"
    except Exception as error:  # noqa: BLE001 -- the refusal may come from the source or query layer
        a5["v2_on_65_world_bank"] = "REFUSED:%s:%s" % (type(error).__name__, str(error))
    training_bank = source.freeze_bank(families)
    public = public_of(source, training_bank["worlds"], focus5)
    query = answers.compile_query(public, kind="analogy", focus_world_id=focus5["world_id"])
    try:
        checker.derive_target(public, query)
        a5["frozen_on_training_bank_with_5_node_focus"] = "ANSWERED"
    except checker.SemanticCheckError as error:
        a5["frozen_on_training_bank_with_5_node_focus"] = "REFUSED:" + str(error)
    got_set, _ = v2_analogy_set(v2, answers, public, focus5)
    a5["v2_on_training_bank_with_5_node_focus"] = sorted(map(str, got_set))
    a5["v2_on_training_bank_equals_oracle"] = got_set == oracle_analogy(oracle, focus5, training_bank["worlds"])
    verdict["A5"] = (a5["frozen_on_bank_with_5_node_world"] == "REFUSED:TYPED_CHECKER_ISOMORPHISM_BOUND"
                     and a5["v2_on_bank_with_5_node_world_equals_oracle"] and a5["v2_on_65_world_bank"].startswith("REFUSED")
                     and a5["frozen_on_training_bank_with_5_node_focus"] == "REFUSED:TYPED_CHECKER_ISOMORPHISM_BOUND"
                     and a5["v2_on_training_bank_equals_oracle"])
    result["A5"] = a5
    print("A5", verdict["A5"], flush=True)

    # ---------------------------------------------------------------- A6
    pool_worlds = [W.make(5, classes5[rng.randrange(len(classes5))][1], rng.choice(D))[0] for _ in range(1500)]
    count = 20 if args.quick else A6_QUESTIONS
    questions = []
    for _ in range(count):
        chosen = rng.sample(range(len(pool_worlds)), A6_BANK + 1)
        bank_worlds = [pool_worlds[i] for i in chosen[1:]]
        focus = pool_worlds[chosen[0]]
        public = public_of(source, bank_worlds, focus)
        questions.append((public, answers.compile_query(public, kind="analogy", focus_world_id=focus["world_id"]), focus, bank_worlds))
    t = time.monotonic()
    targets = [v2.derive_target(public, query) for public, query, _, _ in questions]
    timed = time.monotonic() - t
    perms = [sum(d["permutations_checked"] for d in tg["coverage"]["decisions"]) for tg in targets]
    oracle_ok = sum(1 for tg, (_, _, focus, bw) in zip(targets, questions)
                    if {a["value"]["world_id"] for a in tg["admissible_answers"]} == oracle_analogy(oracle, focus, bw))
    six_pool = [W.make(6, random_dag(rng, 6, hw, oracle), rng.choice(D))[0] for _ in range(300)]
    six_q = []
    for _ in range(10 if args.quick else 100):
        chosen = rng.sample(range(len(six_pool)), A6_BANK + 1)
        bw = [six_pool[i] for i in chosen[1:]]
        public = public_of(source, bw, six_pool[chosen[0]])
        six_q.append((public, answers.compile_query(public, kind="analogy", focus_world_id=six_pool[chosen[0]]["world_id"])))
    t = time.monotonic()
    six_targets = [v2.derive_target(p, q) for p, q in six_q]
    six_timed = time.monotonic() - t
    a6 = {"questions": count, "bank_worlds_per_question": A6_BANK, "nodes": 5, "single_process_seconds": round(timed, 3),
          "budget_seconds": A6_BUDGET_SECONDS, "max_permutations_per_question": max(perms), "total_permutations": sum(perms),
          "answers_equal_oracle": oracle_ok, "device": result["machine"],
          "six_node_questions": len(six_q), "six_node_seconds": round(six_timed, 3),
          "six_node_max_permutations_per_question": max(sum(d["permutations_checked"] for d in tg["coverage"]["decisions"]) for tg in six_targets),
          "builder_benchmark_for_comparison": "Codex: 1,000 questions, 3 worlds per bank, 23.554114344 s on t3.large (README)"}
    verdict["A6"] = (not args.quick and timed <= A6_BUDGET_SECONDS and oracle_ok == count)
    result["A6"] = a6
    print("A6", verdict["A6"], "%.1f s" % timed, flush=True)

    # ---------------------------------------------------------------- X: v2 on every HSET-1A packet
    items, sealed_ids = [], set()
    for path, secret in ((args.hset_public, False), (args.hset_sealed, True)):
        if path:
            rows = [i for i in json.loads(pathlib.Path(path).read_text(encoding="utf-8"))["items"] if i.get("evaluation")]
            items += rows
            if secret:
                sealed_ids |= {i["item_id"] for i in rows}
    if args.quick:
        items = items[:40]
    if items:
        t = time.monotonic()
        with ctx.Pool(args.processes, initializer=_init, initargs=(str(v2_root), False)) as pool:
            xs = list(pool.imap_unordered(_x_task, items, chunksize=16))
        # Custody: a sealed item id carries a fingerprint of a secret shape, so sealed rows are reported as counts only.
        result["X_hset1a_crosscheck"] = {
            "packets": len(xs), "equal": sum(1 for r in xs if r.get("equal")),
            "sealed_packets": sum(1 for r in xs if r["item_id"] in sealed_ids),
            "sealed_equal": sum(1 for r in xs if r["item_id"] in sealed_ids and r.get("equal")),
            "public_errors": [r for r in xs if "error" in r and r["item_id"] not in sealed_ids][:10],
            "sealed_error_count": sum(1 for r in xs if "error" in r and r["item_id"] in sealed_ids),
            "sealed_error_messages": sorted({r["error"].split(":")[0] for r in xs if "error" in r and r["item_id"] in sealed_ids}),
            "seconds": round(time.monotonic() - t, 1)}
        print("X", result["X_hset1a_crosscheck"]["equal"], "/", len(xs), flush=True)

    result["verdict"] = verdict
    result["acceptance"] = ("ACCEPTED" if all(verdict.get(k) for k in ("A1", "A2", "A3", "A4", "A5", "A6"))
                            else "NOT_ACCEPTED")
    result["seconds"] = round(time.monotonic() - t0, 1)
    with open(args.out, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, indent=1, sort_keys=True, default=str))
    print(json.dumps({"acceptance": result["acceptance"], "verdict": verdict, "seconds": result["seconds"]}), flush=True)
    return 0 if result["acceptance"] == "ACCEPTED" else 3


if __name__ == "__main__":
    sys.exit(main())
