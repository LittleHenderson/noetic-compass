"""HSET-1B: Stage 1 reach cells at 6 and 7 nodes (owner decision 2026-09-23: "GO WITH YOUR RECOMMENDATION 6 AND 7 NODE").

Why: HSET-1A showed that at 5 nodes the no-learning two-hop rule is wrong on only W=2 reach clusters of TEST, so no
model could pass (HSET1A_BUILD_RESULT.md). Longer paths are common at 6 and 7 nodes.

What is reused UNCHANGED from the reviewed HSET-1A builder (hset1a_build.py, imported, not copied): world and packet
construction, the frozen-checker gold with the independent cross-check, Helm's reader check, every comparator, cluster
building, balancing, W, conditional power, alternative cuts, custody rules. What is new (BUILD_SPEC_HSET1B_v0_1.md):
  - shapes: 6- and 7-node weakly connected DAGs, every node's in- and out-degree at most 4 (Helm's reader is exact
    there), SAMPLED (the classes are too many to enumerate): DEV from a public seed, TEST from a new sealed salt, and a
    TEST class is never isomorphic to a DEV class (canonical form, checked);
  - splits DEV_NEW_6, TEST_NEW_6, DEV_NEW_7, TEST_NEW_7, each 40 shapes.
Non-neural. TEST material goes only to --out-sealed.

    python -B hset1b_build.py --package-root <CNCM root at 20208c92> --salt-file <sealed salt> \
        --out-public DIR --out-sealed DIR [--processes 8] [--limit-shapes K]
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import concurrent.futures.process
import hashlib
import json
import multiprocessing
import os
import pathlib
import platform
import random
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
NODE_COUNTS = (6, 7)
PER_SPLIT_PER_N = 40
MAX_DEGREE = 4
PUBLIC_DEV_SEED = "HSET-1B-dev-shapes-v0.1"
SPLITS = ("DEV_NEW_6", "DEV_NEW_7", "TEST_NEW_6", "TEST_NEW_7")
SECRET_SPLITS = ("TEST_NEW_6", "TEST_NEW_7")
CELLS = ("REACH_FIRST_DIRECT", "REACH_BFS", "PARTS", "EDGE_ACCOUNT")
MAX_DRAWS = 200000


def _density_edges(rng, n):
    """Generator D: a random node order, then each forward pair kept with probability 0.25, 0.35 or 0.45."""
    order = list(range(n))
    rng.shuffle(order)
    p = rng.choice((0.25, 0.35, 0.45))
    return [(order[i], order[j]) for i in range(n) for j in range(i + 1, n) if rng.random() < p]


def _tree_edges(rng, n):
    """Generator T: deeper, tree-like shapes. Nodes are placed in a random order; each new node either hangs under an
    earlier node, preferring recent ones (long paths), or, with probability 0.2, becomes a new ROOT pointing at an
    earlier node (so ABSENT questions exist). Then 0 to 2 random extra forward edges are added. NOT acyclic by construction: a new-root edge plus an extra edge
    can close a cycle, so sample_class rejects cyclic draws."""
    order = list(range(n))
    rng.shuffle(order)
    edges = set()
    for i in range(1, n):
        earlier = order[:i]
        if rng.random() < 0.2:
            edges.add((order[i], rng.choice(earlier)))                           # new root -> an earlier node
        else:
            weights = [j + 1 for j in range(i)]                                    # bias toward recent nodes: depth
            edges.add((rng.choices(earlier, weights=weights)[0], order[i]))
    position = {v: k for k, v in enumerate(order)}
    for _ in range(rng.choice((0, 1, 2))):
        a, b = rng.sample(range(n), 2)
        if position[a] > position[b]:
            a, b = b, a
        if (b, a) not in edges:
            edges.add((a, b))
    return sorted(edges)


def sample_class(rng, n, oracle):
    """One random weakly connected DAG on n nodes with every in/out degree <= 4, as its canonical form.
    Half the draws use generator D (uniform density), half generator T (deeper, tree-like)."""
    while True:
        edges = _density_edges(rng, n) if rng.random() < 0.5 else _tree_edges(rng, n)
        if not edges or not oracle._weakly_connected(n, edges) or not oracle._acyclic(n, edges):
            continue
        outd, ind = collections.Counter(a for a, _ in edges), collections.Counter(b for _, b in edges)
        if max(list(outd.values()) + list(ind.values())) > MAX_DEGREE:
            continue
        return oracle.canonical_form(n, edges)


def draw(rng, n, count, oracle, exclude):
    got, draws = [], 0
    seen = set(exclude)
    while len(got) < count:
        draws += 1
        if draws > MAX_DRAWS:
            raise RuntimeError("SHAPE_DRAW_LIMIT")
        c = sample_class(rng, n, oracle)
        if c not in seen:
            seen.add(c)
            got.append(c)
    return got, draws


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", required=True)
    parser.add_argument("--salt-file", required=True)
    parser.add_argument("--out-public", required=True)
    parser.add_argument("--out-sealed", required=True)
    parser.add_argument("--processes", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--limit-shapes", type=int, default=0, help="smoke test only")
    args = parser.parse_args()
    t0 = time.monotonic()
    root = pathlib.Path(args.package_root).resolve()
    sys.path.insert(0, str(HERE))
    import hset1a_build as A
    A._paths(root)
    import hset_worlds as hw
    import oracle_isomorphism as oracle
    from cas_meta2.typed_teaching import checker, pointer_contract, source

    salt = pathlib.Path(args.salt_file).read_text(encoding="ascii").strip()
    assert len(salt) == 64 and all(ch in "0123456789abcdef" for ch in salt)
    if args.limit_shapes and salt != "0" * 64:
        raise SystemExit("REFUSED: --limit-shapes is a smoke option and needs the all-zero throwaway salt (review finding 6)")
    identity = {"builder_sha256_lf": A.lf_sha(__file__), "hset1a_build_sha256_lf": A.lf_sha(HERE / "hset1a_build.py"),
                "hset_worlds_sha256_lf": A.lf_sha(HERE / "hset_worlds.py"), "oracle_sha256_lf": A.lf_sha(A.ORACLE_DIR / "oracle_isomorphism.py"),
                "salt_sha256": hashlib.sha256(salt.encode("ascii")).hexdigest(),
                "frozen_files_sha256_lf": {name: A.lf_sha(root / "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching" / name)
                                           for name in ("checker.py", "answers.py", "slots.py", "source.py", "pointer_inputs.py",
                                                        "course.py", "pointer_contract.py", "tokenization.py", "focal.py",
                                                        "course_plan.py", "practice_contract.py", "matched_contract.py",
                                                        "worker_contract.py", "input_frames.py")},
                "face_corpus_sha256_lf": A.lf_sha(root / "research/CAS_META_2_COMPOSITION/cas_meta2/graph_teaching/face_corpus.py"),
                "frozen_checker_profile_digest": checker.checker_profile()["profile_digest"],
                "python": platform.python_version(), "platform": platform.platform(), "processes": args.processes}
    assert identity["frozen_checker_profile_digest"] == A.FROZEN_CHECKER_PROFILE_ANCHOR
    vocab, families = hw.vocabulary(source)
    bank = source.freeze_bank(families)
    assert hw.canon(pointer_contract.load_material(root)[0]["bank"]["bank"]) == hw.canon(bank["bank"])
    identity["bank_digest"] = bank["bank"]["bank_digest"]
    identity["vocabulary_digest"] = hw.sha(vocab)
    identity["vocabulary_sizes"] = {d: {"kinds": len(v["kinds"]), "labels": len(v["labels"]),
                                        "declaration_labels": len(v["declaration_labels"])} for d, v in vocab.items()}

    # ---- shapes: DEV from a public seed, TEST from the salt, never isomorphic to DEV
    key = lambda s: hw.canon([s[0], [list(e) for e in s[1]]])              # noqa: E731
    split_shapes, draws = {}, {}
    for n in NODE_COUNTS:
        dev, d1 = draw(random.Random(hw.keyed_int(PUBLIC_DEV_SEED, "dev", n)), n, PER_SPLIT_PER_N, oracle, ())
        test, d2 = draw(random.Random(hw.keyed_int(salt, "test", n)), n, PER_SPLIT_PER_N, oracle, dev)
        assert not set(dev) & set(test)
        split_shapes["DEV_NEW_%d" % n], split_shapes["TEST_NEW_%d" % n] = [key(s) for s in dev], [key(s) for s in test]
        draws["DEV_NEW_%d" % n], draws["TEST_NEW_%d" % n] = d1, d2
    all_shapes = {k: (json.loads(k)[0], tuple(tuple(e) for e in json.loads(k)[1])) for v in split_shapes.values() for k in v}
    for k, (n, e) in all_shapes.items():                                    # the reader limit, proved
        assert max(max(d) for d in hw.degree_multiset(n, list(e))) <= MAX_DEGREE
    facts = {k: A.shape_facts(hw, s) for k, s in all_shapes.items()}
    print("shapes and facts in %.1f s" % (time.monotonic() - t0), flush=True)
    if args.limit_shapes:
        split_shapes = {k: v[:args.limit_shapes] for k, v in split_shapes.items()}

    def structural_counts(keys):
        out = {}
        for rule, cell in ((hw.REACH_FIRST, "REACH_FIRST_DIRECT"), (hw.REACH_BFS, "REACH_BFS")):
            counts = collections.Counter()
            for k in keys:
                for c in facts[k]["reach_clusters"]:
                    counts["%s/%s/d%s" % (c["state"], "tie" if len(c["answers"][rule]) > 1 else "non_tie", c["distance"])] += 1
            out[cell] = dict(sorted(counts.items()))
        return out

    structural = {s: structural_counts(v) for s, v in split_shapes.items()}

    # ---- items, evaluation (the reviewed HSET-1A code paths)
    items, clusters = [], []
    for split in SPLITS:
        seed = salt if split in SECRET_SPLITS else PUBLIC_DEV_SEED
        i, c = A.build_items(hw, vocab, split, seed, split_shapes[split], facts)
        items += i
        clusters += c
    print("items %d, clusters %d, built in %.1f s" % (len(items), len(clusters), time.monotonic() - t0), flush=True)
    A._init(str(root))
    first = A._evaluate(items[0])
    if "error" in first:
        raise SystemExit("PREFLIGHT_ITEM_FAILED: %s" % first["error"].split(":")[0])
    rows, t1 = [], time.monotonic()
    executor = concurrent.futures.ProcessPoolExecutor(max_workers=args.processes, mp_context=multiprocessing.get_context("spawn"),
                                                      initializer=A._init, initargs=(str(root),))
    try:
        for row in executor.map(A._evaluate, items, chunksize=8, timeout=A.POOL_TOTAL_SECONDS):
            rows.append(row)
            if len(rows) % 500 == 0:
                print("  evaluated %d / %d (%.0f s)" % (len(rows), len(items), time.monotonic() - t1), flush=True)
    except (concurrent.futures.process.BrokenProcessPool, TimeoutError) as error:
        executor.shutdown(wait=False, cancel_futures=True)
        raise SystemExit("POOL_FAILED: %s after %d of %d items" % (type(error).__name__, len(rows), len(items)))
    executor.shutdown(wait=True)
    rows_by_item = {r["item_id"]: r for r in rows}
    errors = [r for r in rows if "error" in r]
    problems = {
        "errors": [[r["item_id"].split("|")[0], r["error"] if r["item_id"].split("|")[0] not in SECRET_SPLITS else r["error"].split(":")[0]]
                   for r in errors][:20],
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
    summaries, cluster_tables = {}, {}
    if build_ok:
        for split in SPLITS:
            seed = salt if split in SECRET_SPLITS else PUBLIC_DEV_SEED
            for cell in CELLS:
                members = [c for c in clusters if c["split"] == split and c["cell"] == cell]
                if not members:
                    continue
                s = A.summarise_cell(hw, cell, members, rows_by_item, items_by_cluster, seed)
                s["claim_role"] = ("PRIMARY_CLAIM_CANDIDATE" if split in SECRET_SPLITS and cell.startswith("REACH")
                                   else "DEVELOPMENT_FEEDBACK" if split.startswith("DEV") else "DIAGNOSTIC")
                summaries["%s/%s" % (split, cell)] = s
                cluster_tables["%s/%s" % (split, cell)] = members

    pub, sealed = pathlib.Path(args.out_public), pathlib.Path(args.out_sealed)
    pub.mkdir(parents=True, exist_ok=True)
    sealed.mkdir(parents=True, exist_ok=True)

    def dump(path, value):
        data = json.dumps(value, indent=1, sort_keys=True).encode("utf-8")
        path.write_bytes(data)
        return hashlib.sha256(data).hexdigest()

    def payload(names):
        return {"items": [dict(i, evaluation=rows_by_item.get(i["item_id"])) for i in items if i["split"] in names],
                "clusters": {k: v for k, v in cluster_tables.items() if k.split("/")[0] in names}}

    sealed_sha = dump(sealed / "HSET1B_SEALED_TEST_NEW_67.json",
                      {"schema": "claude.hset1b-sealed/0.1", "custody": "CLAUDE_ONLY_NEVER_COMMIT", "identity": identity,
                       "test_shapes": {s: split_shapes[s] for s in SECRET_SPLITS}, **payload(SECRET_SPLITS)})
    public_names = [s for s in SPLITS if s not in SECRET_SPLITS]
    public_sha = dump(pub / "HSET1B_CELLS_PUBLIC.json",
                      {"schema": "claude.hset1b-public-cells/0.1", "identity": identity,
                       "shapes": {s: split_shapes[s] for s in public_names}, **payload(public_names)})
    summary = {"schema": "claude.hset1b-build-summary/0.1", "build_ok": build_ok, "problems": problems, "identity": identity,
               "counts": {"items": len(items), "clusters": len(clusters), "items_by_split": dict(collections.Counter(i["split"] for i in items))},
               "shape_draws": draws, "structural_reach_cluster_counts": structural, "limit_shapes": args.limit_shapes,
               "test_shapes_digest": {s: hw.sha(sorted(split_shapes[s])) for s in SECRET_SPLITS},
               "dev_shapes": {s: split_shapes[s] for s in public_names},
               "edge_count_histogram": {s: dict(sorted(collections.Counter(str(facts[k]["edge_count"]) for k in v).items()))
                                        for s, v in split_shapes.items()},
               "files": {"HSET1B_CELLS_PUBLIC.json": public_sha, "HSET1B_SEALED_TEST_NEW_67.json": sealed_sha},
               "cells": summaries, "seconds": round(time.monotonic() - t0, 1)}
    dump(pub / "HSET1B_BUILD_SUMMARY.json", summary)
    print("\n%-38s %6s %4s %-22s %8s %9s %9s  %s" % ("cell", "n", "W", "bar", "bar_acc", "pw+0.20", "pw_all_W", "claim?"))
    for name, s in summaries.items():
        pw = s.get("power_conditional_on_measured_bar", {})
        plus20 = pw.get("uniform_model_accuracy", {}).get("%.4f" % round(min(1.0, (s["bar_cluster_accuracy"] or 0) + 0.20), 4))
        print("%-38s %6d %4d %-22s %8.4f %9s %9s  %s" % (
            name, s["primary_clusters"], s["bar_wrong_clusters_W"], s["bar"], s["bar_cluster_accuracy"] or 0, plus20,
            pw.get("never_loses_where_bar_is_right_wins_fraction", {}).get("1.00"),
            "yes" if s["can_carry_a_claim"] else "NO: " + s["why_not"]))
    print(json.dumps({"build_ok": build_ok, "problems": problems, "seconds": summary["seconds"]}), flush=True)
    return 0 if build_ok else 2


if __name__ == "__main__":
    sys.exit(main())
