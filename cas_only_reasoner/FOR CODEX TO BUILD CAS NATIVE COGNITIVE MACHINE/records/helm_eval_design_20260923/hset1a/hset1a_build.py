"""HSET-1A Stage 1 cell builder (Claude: evaluation designer and sealed-test custodian).

Implements `EVALUATION_DESIGN_v0_2.md` section 1 with the implementation choices fixed in `BUILD_SPEC_v0_1.md`
(read that first). Non-neural: no model is loaded, nothing is trained, no forward pass. It builds:

  splits  FAMILIAR_RELABELLED (the 6 bank shapes)   NEW_SHAPE_4 (3 new 3-node + 19 new 4-node shapes)
          DEV_NEW_5 (60 of the 267 5-node shapes)   TEST_NEW_5 (60 more, SECRET)
  cells   REACH_FIRST_DIRECT  REACH_BFS  PARTS  EDGE_ACCOUNT

and, for every cell: the clusters, 2 presentations per cluster, the frozen checker's gold answer for every
packet, every registered no-learning comparator scored by the frozen checker, the measured bar, the effective n
(clusters) and the power of the exact cluster sign test at stated effect sizes.

Every packet is also run through the frozen packet validator, the frozen slot compiler and Helm's own frozen
input reader (`pointer_inputs.read_packet`, pure Python), so a cell Helm cannot read fails the build.

    python -B hset1a_build.py --package-root <CNCM root at 20208c92> --salt-file <sealed salt> \
        --out-public DIR --out-sealed DIR [--processes 8] [--limit-shapes K]

Custody: TEST_NEW_5 items, answers and per-cluster results go ONLY to --out-sealed. The public outputs carry
aggregate TEST numbers and digests, never TEST worlds, record ids or answers.
"""
from __future__ import annotations

import argparse
import collections
import functools
import hashlib
import json
import math
import multiprocessing
import os
import pathlib
import platform
import random
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ORACLE_DIR = HERE.parent / "d1_acceptance"
PUBLIC_SEED = "HSET-1A-public-instances-v0.1"
FROZEN_CHECKER_PROFILE_ANCHOR = "2c95354e62994fb8a0c0ab56254d1527f5f4d2c79ea5ecbed5679de730bd8a81"
SPLITS = ("FAMILIAR_RELABELLED", "NEW_SHAPE_4", "DEV_NEW_5", "TEST_NEW_5")
SECRET_SPLITS = ("TEST_NEW_5",)
CELLS = ("REACH_FIRST_DIRECT", "REACH_BFS", "PARTS", "EDGE_ACCOUNT")
DEV_TEST_EACH = 60
MIN_CLUSTERS = 10
ALPHA = 0.01
COMPARATORS = {
    "reach": ("CONSTANT_ABSENT", "CONSTANT_DIRECT", "ONE_HOP", "LOWEST_RANK_CHILD", "RANK_LAST_CHILD",
              "TWO_HOP_FIRST_CHILD", "PARTICIPANT_2", "DEGREE_RULE"),
    "parts": ("CONSTANT_EMPTY", "ONE_HOP", "PARTICIPANTS_2_3", "ALL_OTHERS", "DESCENDANTS"),
    "edge_account": ("ONE_HOP_ALL_EDGES", "STAR_FROM_DECLARED_WHOLE", "RANK_CHAIN", "PARTICIPANT_CHAIN"),
}
FLAGS = ("GOLD_VIA_IS_PARTICIPANT_2", "GOLD_VIA_IS_LOWEST_RANK_CHILD", "GOLD_VIA_IS_RANK_LAST_CHILD")


def lf_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _paths(package_root):
    sys.dont_write_bytecode = True
    for p in (str(ORACLE_DIR), str(HERE), str(pathlib.Path(package_root) / "research" / "CAS_META_2_COMPOSITION")):
        if p not in sys.path:
            sys.path.insert(0, p)


# ============================================================================ worker (one per process)
_W = {}


def _init(package_root):
    _paths(package_root)
    import hset_worlds as hw
    from cas_meta2.typed_teaching import answers, checker, course, pointer_inputs, slots, source
    _, families = hw.vocabulary(source)
    _W.update(hw=hw, source=source, answers=answers, course=course, checker=checker, slots=slots,
              pointer_inputs=pointer_inputs, bank=source.freeze_bank(families))


def _comparators(kind, world, query):
    """Every registered no-learning rule, read off the packet's own focus world (refs, contains, flags)."""
    nodes = sorted(n["ref"] for n in world["nodes"])                      # sorted refs = rank order
    rank = {ref: i for i, ref in enumerate(nodes)}
    edges = {(e["source"], e["target"]) for e in world["contains"]}
    participants = world["declarations"]["participants"]
    p2, p3 = participants[1], participants[2]
    whole = query["arguments"].get("whole", world["declared_whole"])
    kids = sorted((b for a, b in edges if a == whole), key=rank.get)
    out = {}
    if kind == "reach":
        part = query["arguments"]["part"]
        A, D = {"state": "ABSENT", "via": None}, {"state": "DIRECT", "via": None}
        via = lambda ref: {"state": "VIA", "via": ref}                    # noqa: E731
        direct = part in kids
        indeg = collections.Counter(b for _, b in edges)
        outdeg = collections.Counter(a for a, _ in edges)
        two = [c for c in kids if (c, part) in edges]
        out["CONSTANT_ABSENT"], out["CONSTANT_DIRECT"] = A, D
        out["ONE_HOP"] = D if direct else A
        out["LOWEST_RANK_CHILD"] = D if direct else (via(kids[0]) if kids else A)
        out["RANK_LAST_CHILD"] = D if direct else (via(kids[-1]) if kids else A)
        out["TWO_HOP_FIRST_CHILD"] = D if direct else (via(two[0]) if two else A)
        out["PARTICIPANT_2"] = D if direct else (via(p2) if kids else A)
        out["DEGREE_RULE"] = (D if direct else A if indeg[part] == 0 else
                              via(max(kids, key=lambda c: (outdeg[c], -rank[c]))) if kids else A)
    elif kind == "parts":
        reach, stack = set(), [whole]
        while stack:
            x = stack.pop()
            for a, b in edges:
                if a == x and b not in reach:
                    reach.add(b)
                    stack.append(b)
        out["CONSTANT_EMPTY"] = {"nodes": []}
        out["ONE_HOP"] = {"nodes": sorted(kids)}
        out["PARTICIPANTS_2_3"] = {"nodes": sorted({p2, p3})}
        out["ALL_OTHERS"] = {"nodes": sorted(set(nodes) - {whole})}
        out["DESCENDANTS"] = {"nodes": sorted(reach)}
    else:
        rows = lambda pairs: {"edges": [{"source": a, "target": b} for a, b in sorted(set(pairs))]}  # noqa: E731
        out["ONE_HOP_ALL_EDGES"] = rows(edges)
        out["STAR_FROM_DECLARED_WHOLE"] = rows((world["declared_whole"], x) for x in nodes if x != world["declared_whole"])
        out["RANK_CHAIN"] = rows((nodes[i], nodes[i + 1]) for i in range(len(nodes) - 1))
        out["PARTICIPANT_CHAIN"] = rows([(participants[0], p2), (p2, p3)])
    assert tuple(out) == COMPARATORS[kind], (kind, tuple(out))
    return out, {"kids": kids, "p2": p2}


def _independent_gold(hw, item, refs):
    spec = item["world"]
    n, edges = len(spec["labels"]), [tuple(e) for e in spec["edges"]]
    if item["kind"] == "reach":
        state, via = hw.reach_gold(n, edges, item["whole"], item["part"], hw.ranks(spec), item["rule"])
        return {"state": state, "via": None if via is None else refs[via]}
    if item["kind"] == "parts":
        return {"nodes": sorted(refs[b] for a, b in edges if a == item["whole"])}
    return {"edges": [{"source": a, "target": b} for a, b in sorted((refs[a], refs[b]) for a, b in edges)]}


def _evaluate(item):
    try:
        return _evaluate_inner(item)
    except Exception as error:  # noqa: BLE001 -- reported per item; any error fails the build
        return {"item_id": item["item_id"], "error": "%s: %s" % (type(error).__name__, str(error)[:300])}


def _evaluate_inner(item):
    hw, source, answers, course, checker = _W["hw"], _W["source"], _W["answers"], _W["course"], _W["checker"]
    packet, focus, refs = hw.packet_from_item(source, answers, course, _W["bank"], item)
    course.validate_model_packet(packet)
    plan = _W["slots"].compile_slots(packet)
    reading = _W["pointer_inputs"].read_packet(packet)
    public, query = packet["source"], packet["record"]["query"]
    rank = hw.ranks(item["world"])
    reader_ok = (reading["record_id"] == packet["record"]["record_id"] and reading["query"]["world_count"] == 1
                 and reading["focus_world"]["node_count"] == len(item["world"]["labels"])
                 and reading["query"]["whole"] == (None if item.get("whole") is None else rank[item["whole"]])
                 and reading["query"]["part"] == (None if item.get("part") is None else rank[item["part"]])
                 and all(max(d) <= 4 for d in hw.degree_multiset(len(refs), [tuple(e) for e in item["world"]["edges"]])))
    target = checker.derive_target(public, query)
    admissible = target["admissible_answers"]
    gold = admissible[0]["value"] if len(admissible) == 1 else None
    independent = _independent_gold(hw, item, refs)
    payloads, aux = _comparators(item["kind"], focus, query)
    verdicts, distinct = {}, {}
    for name, payload in payloads.items():
        key = hw.canon(payload)
        if key not in distinct:
            answer = answers.make_answer(public, query, payload)
            distinct[key] = bool(checker.check_answer(public, query, answer)["correct"])
        verdicts[name] = distinct[key]
    consistent = all(verdicts[name] == (hw.canon(payloads[name]) == hw.canon(gold)) for name in verdicts)
    flags = {}
    if item["kind"] == "reach" and gold is not None and gold["state"] == "VIA":
        flags = {"GOLD_VIA_IS_PARTICIPANT_2": gold["via"] == aux["p2"],
                 "GOLD_VIA_IS_LOWEST_RANK_CHILD": bool(aux["kids"]) and gold["via"] == aux["kids"][0],
                 "GOLD_VIA_IS_RANK_LAST_CHILD": bool(aux["kids"]) and gold["via"] == aux["kids"][-1]}
    return {"item_id": item["item_id"], "record_id": packet["record"]["record_id"], "query_id": query["query_id"],
            "source_digest": packet["record"]["source_digest"], "packet_sha256": hw.sha(packet),
            "plan_digest": plan["plan_digest"], "slot_count": len(plan["slots"]),
            "reader_ok": reader_ok, "node_rank_feature": reading["node_rank_feature"],
            "admissible_count": len(admissible), "gold": gold,
            "independent_gold_agrees": gold is not None and hw.canon(gold) == hw.canon(independent),
            "comparator_scoring_consistent": consistent, "comparators": verdicts, "flags": flags}


# ============================================================================ statistics
@functools.lru_cache(maxsize=None)
def sign_p(b, c):
    """Exact one-sided binomial P(X >= b | n = b + c, p = 1/2)."""
    n = b + c
    return sum(math.comb(n, i) for i in range(b, n + 1)) / 2 ** n if n else 1.0


def sign_pass(b, c):
    return b > c and sign_p(b, c) <= ALPHA


def power(n, q_model, q_bar):
    """P(the exact cluster sign test passes) when the model is right on a cluster with probability q_model and the
    bar with q_bar, independently per cluster (a stated assumption, printed with every number)."""
    pb, pc = q_model * (1 - q_bar), (1 - q_model) * q_bar
    pt = max(0.0, 1.0 - pb - pc)
    total = 0.0
    for b in range(n + 1):
        for c in range(0, min(b, n - b + 1)):
            if not sign_pass(b, c):
                continue
            t = n - b - c
            log_term = math.lgamma(n + 1) - math.lgamma(b + 1) - math.lgamma(c + 1) - math.lgamma(t + 1)
            if (pb == 0 and b) or (pc == 0 and c) or (pt == 0 and t):
                continue
            log_term += (b * math.log(pb) if b else 0) + (c * math.log(pc) if c else 0) + (t * math.log(pt) if t else 0)
            total += math.exp(log_term)
    return round(min(1.0, total), 6)


# ============================================================================ building
def shape_facts(hw, shape):
    n, edges = shape
    aut = hw.automorphisms(n, edges)
    rts = hw.roots(n, edges)
    reach = {}
    for r in rts:
        for p in range(n):
            if p == r:
                continue
            w, q = min((s[r], s[p]) for s in aut)
            if (w, q) in reach:
                continue
            state = hw.reach_gold(n, edges, w, q, {v: v for v in range(n)}, hw.REACH_FIRST)[0]
            reach[(w, q)] = {"whole": w, "part": q, "state": state, "distance": hw.distance(edges, w, q),
                             "answers": {rule: [list(a) for a in hw.reach_answer_set(n, edges, w, q, rule)]
                                         for rule in (hw.REACH_FIRST, hw.REACH_BFS)}}
    root_reps = sorted({min(s[r] for s in aut) for r in rts})
    return {"n": n, "edges": [list(e) for e in edges], "edge_count": len(edges), "automorphisms": len(aut),
            "roots": rts, "root_reps": root_reps, "reach_clusters": [reach[k] for k in sorted(reach)],
            "via_capable": any(c["state"] == "VIA" for c in reach.values()),
            "degree_multiset": [list(d) for d in hw.degree_multiset(n, edges)]}


def split_five(hw, salt, facts5):
    strata = collections.defaultdict(list)
    for key, f in facts5.items():
        strata[(f["via_capable"], f["edge_count"])].append(key)
    total = sum(len(v) for v in strata.values())
    cap = {s: len(v) // 2 for s, v in strata.items()}
    quota = {s: min(cap[s], int(DEV_TEST_EACH * len(v) / total)) for s, v in strata.items()}
    while sum(quota.values()) < DEV_TEST_EACH:
        open_ = [s for s in strata if quota[s] < cap[s]]
        s = max(open_, key=lambda s: (DEV_TEST_EACH * len(strata[s]) / total - quota[s], repr(s)))
        quota[s] += 1
    dev, test, table = [], [], []
    for s in sorted(strata, key=repr):
        order = sorted(strata[s], key=lambda k: hw.keyed_int(salt, "split", k))
        dev += order[:quota[s]]
        test += order[quota[s]:2 * quota[s]]
        table.append({"via_capable": s[0], "edge_count": s[1], "classes": len(strata[s]), "dev": quota[s], "test": quota[s]})
    return dev, test, table


def instance_specs(hw, vocab, rng, shape, whole, part):
    """One instance, 2 presentations: same structure, domain, kind and participants; labels permuted."""
    n, edges = shape
    domain = rng.choice(hw.TRAINING_DOMAINS)
    v = vocab[domain]
    kind, label_set = rng.choice(v["kinds"]), rng.sample(v["labels"], n)
    p2, p3 = rng.sample([x for x in range(n) if x != whole], 2)
    primary = [whole, p2, p3]

    def signature(assign):
        order = sorted(assign)
        rk = {i: order.index(assign[i]) for i in range(n)}
        return (tuple(sorted((rk[a], rk[b]) for a, b in edges)), rk[whole], rk[p2], rk[p3], None if part is None else rk[part])

    first = rng.sample(label_set, n)
    for _ in range(200):
        second = rng.sample(label_set, n)
        if signature(second) != signature(first):
            break
    else:
        raise RuntimeError("NO_DISTINCT_SECOND_PRESENTATION")
    specs = []
    for assign in (first, second):
        specs.append({"labels": list(assign), "edges": [list(e) for e in edges], "primary": primary,
                      "declarations": {"domain": domain, "kind": kind, "setting": v["setting"],
                                       "function": v["function_template"] % {"whole": assign[whole], "child": assign[p2]}}})
    return specs


def build_items(hw, vocab, split, seed_material, shapes, facts):
    items, clusters = [], []
    for shape_key in shapes:
        f = facts[shape_key]
        shape = (f["n"], tuple(tuple(e) for e in f["edges"]))
        groups = [("REACH", c["whole"], c["part"], c) for c in f["reach_clusters"]]
        groups += [("PARTS", r, None, None) for r in f["root_reps"]]
        groups += [("EDGE_ACCOUNT", None, None, None)]
        for group, whole, part, reach in groups:
            cid = "%s|%s|%s|w%s|p%s" % (split, group, hw.sha(shape_key)[:16], whole, part)
            rng = random.Random(hw.keyed_int(seed_material, "instance", cid))
            w = whole if whole is not None else rng.choice(f["roots"])
            specs = instance_specs(hw, vocab, rng, shape, w, part)
            if group == "REACH":
                cells = (("REACH_FIRST_DIRECT", hw.REACH_FIRST, None), ("REACH_BFS", hw.REACH_BFS, "CUBE_FACE_5"))
            elif group == "PARTS":
                cells = (("PARTS", None, None),)
            else:
                cells = (("EDGE_ACCOUNT", None, "CUBE_FACE_6"),)
            for cell, rule, cue in cells:
                kind = {"REACH_FIRST_DIRECT": "reach", "REACH_BFS": "reach", "PARTS": "parts", "EDGE_ACCOUNT": "edge_account"}[cell]
                ccid = cid + "|" + cell
                meta = {"cluster_id": ccid, "split": split, "cell": cell, "shape_key": shape_key, "n": f["n"],
                        "edge_count": f["edge_count"], "whole": w, "part": part, "domain": specs[0]["declarations"]["domain"]}
                if reach is not None:
                    answers_rule = reach["answers"][rule]
                    meta.update(state=reach["state"], distance=reach["distance"], tie=len(answers_rule) > 1,
                                gold_options=answers_rule)
                clusters.append(meta)
                for k, spec in enumerate(specs):
                    items.append({"item_id": "%s|pres%d" % (ccid, k), "cluster_id": ccid, "split": split, "cell": cell,
                                  "presentation": k, "kind": kind, "rule": rule, "cue": cue,
                                  "whole": w if kind in ("reach", "parts") else None,
                                  "part": part if kind == "reach" else None, "world": spec})
    return items, clusters


def summarise_cell(hw, cell, clusters, rows_by_item, items_by_cluster, seed_material):
    kind = {"REACH_FIRST_DIRECT": "reach", "REACH_BFS": "reach", "PARTS": "parts", "EDGE_ACCOUNT": "edge_account"}[cell]
    names = COMPARATORS[kind]
    for c in clusters:
        rows = [rows_by_item[i["item_id"]] for i in items_by_cluster[c["cluster_id"]]]
        c["comparators"] = {name: all(r["comparators"][name] for r in rows) for name in names}
        c["presentations"] = len(rows)
    if kind == "reach":
        by_state = collections.defaultdict(list)
        for c in clusters:
            if not c["tie"]:
                by_state[c["state"]].append(c)
        k = min(len(by_state[s]) for s in ("ABSENT", "DIRECT", "VIA"))
        for s in ("ABSENT", "DIRECT", "VIA"):
            ordered = sorted(by_state[s], key=lambda c: hw.keyed_int(seed_material, "balance", c["cluster_id"]))
            for i, c in enumerate(ordered):
                c["role"] = "PRIMARY" if i < k else "SURPLUS_NON_TIE"
        for c in clusters:
            if c["tie"]:
                c["role"] = "TIE_STRATUM"
    else:
        for c in clusters:
            c["role"] = "PRIMARY"
    primary = [c for c in clusters if c["role"] == "PRIMARY"]
    n = len(primary)
    acc = {name: (sum(c["comparators"][name] for c in primary) / n if n else None) for name in names}
    bar = max(names, key=lambda name: (acc[name] if acc[name] is not None else -1, -names.index(name)))
    q_bar = acc[bar]
    summary = {"cell": cell, "kind": kind, "primary_clusters": n, "presentations_per_cluster": 2,
               "comparator_cluster_accuracy": acc, "bar": bar, "bar_cluster_accuracy": q_bar,
               "bar_right_clusters": sum(c["comparators"][bar] for c in primary)}
    if n and q_bar is not None:
        effects = sorted({round(min(1.0, q_bar + d), 6) for d in (0.10, 0.20, 0.30)} | {1.0})
        summary["power_exact_sign_test"] = {
            "assumption": "model and bar right on each cluster independently; alpha %s one-sided; no zero-loss veto" % ALPHA,
            "by_model_cluster_accuracy": {("%.4f" % q): power(n, q, q_bar) for q in effects}}
    summary["can_carry_a_claim"] = bool(n >= MIN_CLUSTERS and q_bar is not None and q_bar < 1.0)
    summary["why_not"] = (None if summary["can_carry_a_claim"] else
                          "fewer than %d clusters" % MIN_CLUSTERS if n < MIN_CLUSTERS else
                          "the bar is exact (%s answers every cluster): only input-reading fidelity can be shown" % bar)
    if kind == "reach":
        roles = collections.Counter(c["role"] for c in clusters)
        summary["clusters_by_role"] = dict(sorted(roles.items()))
        summary["primary_by_state"] = dict(sorted(collections.Counter(c["state"] for c in primary).items()))
        summary["primary_via_by_distance"] = dict(sorted(collections.Counter(
            str(c["distance"]) for c in primary if c["state"] == "VIA").items()))
        summary["primary_bar_accuracy_by_state"] = {
            s: round(sum(c["comparators"][bar] for c in primary if c["state"] == s)
                     / max(1, sum(1 for c in primary if c["state"] == s)), 6) for s in ("ABSENT", "DIRECT", "VIA")}
        nontie = [c for c in clusters if not c["tie"]]
        summary["all_non_tie_clusters"] = {
            "clusters": len(nontie), "by_state": dict(sorted(collections.Counter(c["state"] for c in nontie).items())),
            "comparator_cluster_accuracy": {name: (round(sum(c["comparators"][name] for c in nontie) / len(nontie), 6)
                                                   if nontie else None) for name in names},
            "via_by_distance": {str(d): {"clusters": sum(1 for c in nontie if c["state"] == "VIA" and c["distance"] == d),
                                         "comparator_cluster_accuracy": {name: round(
                                             sum(c["comparators"][name] for c in nontie if c["state"] == "VIA" and c["distance"] == d)
                                             / max(1, sum(1 for c in nontie if c["state"] == "VIA" and c["distance"] == d)), 6)
                                             for name in names}}
                                for d in sorted({c["distance"] for c in nontie if c["state"] == "VIA"})}}
        ties = [c for c in clusters if c["role"] == "TIE_STRATUM"]
        summary["tie_stratum"] = {"clusters": len(ties), "comparator_cluster_accuracy":
                                  {name: (round(sum(c["comparators"][name] for c in ties) / len(ties), 6) if ties else None)
                                   for name in names}}
        for scope, members in (("primary_via", [c for c in primary if c["state"] == "VIA"]),
                               ("all_via", [c for c in clusters if c["state"] == "VIA"])):
            pres = [rows_by_item[i["item_id"]] for c in members for i in items_by_cluster[c["cluster_id"]]]
            summary["flag_hit_rate_%s" % scope] = {
                "presentations": len(pres),
                **{flag: (round(sum(r["flags"][flag] for r in pres) / len(pres), 6) if pres else None) for flag in FLAGS}}
    summary["primary_domains"] = dict(sorted(collections.Counter(c["domain"] for c in primary).items()))
    summary["primary_node_counts"] = dict(sorted(collections.Counter(str(c["n"]) for c in primary).items()))
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", required=True)
    parser.add_argument("--salt-file", required=True)
    parser.add_argument("--out-public", required=True)
    parser.add_argument("--out-sealed", required=True)
    parser.add_argument("--processes", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--limit-shapes", type=int, default=0, help="smoke test only: keep K shapes per split")
    args = parser.parse_args()
    t0 = time.monotonic()
    root = pathlib.Path(args.package_root).resolve()
    _paths(root)
    import hset_worlds as hw
    import oracle_isomorphism as oracle
    from cas_meta2.typed_teaching import checker, pointer_contract, source

    salt = pathlib.Path(args.salt_file).read_text(encoding="ascii").strip()
    assert len(salt) == 64 and all(ch in "0123456789abcdef" for ch in salt), "the salt must be 64 lowercase hex characters"
    identity = {"builder_sha256_lf": lf_sha(__file__), "hset_worlds_sha256_lf": lf_sha(HERE / "hset_worlds.py"),
                "oracle_sha256_lf": lf_sha(ORACLE_DIR / "oracle_isomorphism.py"),
                "salt_sha256": hashlib.sha256(salt.encode("ascii")).hexdigest(),
                "frozen_files_sha256_lf": {name: lf_sha(root / "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching" / name)
                                           for name in ("checker.py", "answers.py", "slots.py", "source.py", "pointer_inputs.py", "course.py")},
                "frozen_checker_profile_digest": checker.checker_profile()["profile_digest"],
                "python": platform.python_version(), "platform": platform.platform(), "processes": args.processes}
    assert identity["frozen_checker_profile_digest"] == FROZEN_CHECKER_PROFILE_ANCHOR, "not the frozen checker"
    vocab, families = hw.vocabulary(source)
    bank = source.freeze_bank(families)
    course_bank = pointer_contract.load_material(root)[0]["bank"]["bank"]
    assert hw.canon(course_bank) == hw.canon(bank["bank"]), "the rebuilt bank is not the trained course's bank"
    identity["bank_digest"] = bank["bank"]["bank_digest"]
    identity["vocabulary_digest"] = hw.sha(vocab)
    identity["vocabulary_sizes"] = {d: {"kinds": len(v["kinds"]), "labels": len(v["labels"])} for d, v in vocab.items()}

    # ---- shapes
    classes = {n: oracle.dag_classes(n) for n in (3, 4, 5)}
    assert [len(classes[n]) for n in (3, 4, 5)] == [4, 24, 267], [len(classes[n]) for n in (3, 4, 5)]
    bank_shapes = set()
    for f in families:
        index = {label: i for i, label in enumerate(f["labels"])}
        bank_shapes.add(oracle.canonical_form(len(f["labels"]), [(index[b["source"]], index[b["target"]]) for b in f["branches"]]))
    assert len(bank_shapes) == 6 and all(s in classes[s[0]] for s in bank_shapes)
    key = lambda s: hw.canon([s[0], [list(e) for e in s[1]]])                       # noqa: E731
    facts = {key(s): shape_facts(hw, s) for n in (3, 4, 5) for s in classes[n]}
    familiar = sorted(key(s) for s in bank_shapes)
    new4 = sorted(key(s) for n in (3, 4) for s in classes[n] if s not in bank_shapes)
    assert len(new4) == 22
    dev5, test5, strata_table = split_five(hw, salt, {key(s): facts[key(s)] for s in classes[5]})
    assert len(dev5) == len(test5) == DEV_TEST_EACH and not set(dev5) & set(test5)
    split_shapes = {"FAMILIAR_RELABELLED": familiar, "NEW_SHAPE_4": new4, "DEV_NEW_5": dev5, "TEST_NEW_5": test5}
    if args.limit_shapes:
        split_shapes = {k: v[:args.limit_shapes] for k, v in split_shapes.items()}

    # ---- items
    items, clusters = [], []
    for split in SPLITS:
        seed = salt if split in ("DEV_NEW_5", "TEST_NEW_5") else PUBLIC_SEED
        i, c = build_items(hw, vocab, split, seed, split_shapes[split], facts)
        items += i
        clusters += c
    print("items %d, clusters %d, built in %.1f s" % (len(items), len(clusters), time.monotonic() - t0), flush=True)

    # ---- evaluate every packet (frozen validator, slot compiler, Helm's reader, frozen checker)
    ctx = multiprocessing.get_context("spawn")
    rows, t1 = [], time.monotonic()
    with ctx.Pool(args.processes, initializer=_init, initargs=(str(root),)) as pool:
        for k, row in enumerate(pool.imap_unordered(_evaluate, items, chunksize=8), 1):
            rows.append(row)
            if k % 500 == 0:
                print("  evaluated %d / %d (%.0f s)" % (k, len(items), time.monotonic() - t1), flush=True)
    rows_by_item = {r["item_id"]: r for r in rows}
    errors = [r for r in rows if "error" in r]
    problems = {
        # Custody: a sealed item's error text could name a secret world, so only its error type is kept.
        "errors": [[r["item_id"].split("|")[0], r["error"] if r["item_id"].split("|")[0] not in SECRET_SPLITS
                    else r["error"].split(":")[0]] for r in errors][:20],
        "error_count": len(errors),
        "not_exactly_one_admissible_answer": sum(1 for r in rows if "error" not in r and r["admissible_count"] != 1),
        "independent_gold_disagrees": sum(1 for r in rows if "error" not in r and not r["independent_gold_agrees"]),
        "comparator_scoring_inconsistent": sum(1 for r in rows if "error" not in r and not r["comparator_scoring_consistent"]),
        "reader_check_failed": sum(1 for r in rows if "error" not in r and not r["reader_ok"]),
        "duplicate_record_ids": len(rows) - len({r.get("record_id") for r in rows}),
    }
    build_ok = not any(v for k, v in problems.items() if k != "errors")
    items_by_cluster = collections.defaultdict(list)
    for item in items:
        items_by_cluster[item["cluster_id"]].append(item)

    # ---- cells
    summaries, cluster_tables = {}, {}
    if build_ok:
        for split in SPLITS:
            seed = salt if split in ("DEV_NEW_5", "TEST_NEW_5") else PUBLIC_SEED
            for cell in CELLS:
                members = [c for c in clusters if c["split"] == split and c["cell"] == cell]
                if not members:
                    continue
                s = summarise_cell(hw, cell, members, rows_by_item, items_by_cluster, seed)
                s["claim_role"] = ("PRIMARY_CLAIM_CANDIDATE" if split == "TEST_NEW_5" and cell.startswith("REACH")
                                   else "DEVELOPMENT_FEEDBACK" if split == "DEV_NEW_5" else "DIAGNOSTIC")
                summaries["%s/%s" % (split, cell)] = s
                cluster_tables["%s/%s" % (split, cell)] = members

    # ---- write
    pub, sealed = pathlib.Path(args.out_public), pathlib.Path(args.out_sealed)
    pub.mkdir(parents=True, exist_ok=True)
    sealed.mkdir(parents=True, exist_ok=True)

    def dump(path, value):
        data = json.dumps(value, indent=1, sort_keys=True).encode("utf-8")
        path.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def split_payload(names):
        return {"items": [dict(i, evaluation=rows_by_item.get(i["item_id"])) for i in items if i["split"] in names],
                "clusters": {k: v for k, v in cluster_tables.items() if k.split("/")[0] in names}}

    sealed_sha = dump(sealed / "HSET1A_SEALED_TEST_NEW_5.json",
                      {"schema": "claude.hset1a-sealed/0.1", "custody": "CLAUDE_ONLY_NEVER_COMMIT", "identity": identity,
                       "test_shapes": split_shapes["TEST_NEW_5"], **split_payload(SECRET_SPLITS)})
    public_names = [s for s in SPLITS if s not in SECRET_SPLITS]
    public_sha = dump(pub / "HSET1A_CELLS_PUBLIC.json",
                      {"schema": "claude.hset1a-public-cells/0.1", "identity": identity,
                       "shapes": {s: split_shapes[s] for s in public_names}, **split_payload(public_names)})
    summary = {"schema": "claude.hset1a-build-summary/0.1", "build_ok": build_ok, "problems": problems, "identity": identity,
               "counts": {"items": len(items), "clusters": len(clusters),
                          "items_by_split": dict(collections.Counter(i["split"] for i in items))},
               "five_node_strata": strata_table, "limit_shapes": args.limit_shapes,
               "test_shapes_digest": hw.sha(sorted(split_shapes["TEST_NEW_5"])),
               "dev_shapes": split_shapes["DEV_NEW_5"],
               "files": {"HSET1A_CELLS_PUBLIC.json": public_sha, "HSET1A_SEALED_TEST_NEW_5.json": sealed_sha},
               "cells": summaries, "seconds": round(time.monotonic() - t0, 1)}
    dump(pub / "HSET1A_BUILD_SUMMARY.json", summary)
    print("\n%-38s %6s %-22s %8s %9s %9s  %s" % ("cell", "n", "bar", "bar_acc", "pow+0.20", "pow@1.0", "claim?"))
    for name, s in summaries.items():
        p = s.get("power_exact_sign_test", {}).get("by_model_cluster_accuracy", {})
        plus20 = p.get("%.4f" % round(min(1.0, (s["bar_cluster_accuracy"] or 0) + 0.20), 6))
        print("%-38s %6d %-22s %8.4f %9s %9s  %s" % (name, s["primary_clusters"], s["bar"], s["bar_cluster_accuracy"] or 0,
                                                     plus20, p.get("1.0000"), "yes" if s["can_carry_a_claim"] else "NO: " + s["why_not"]))
    print(json.dumps({"build_ok": build_ok, "problems": problems, "seconds": summary["seconds"]}), flush=True)
    return 0 if build_ok else 2


if __name__ == "__main__":
    sys.exit(main())
