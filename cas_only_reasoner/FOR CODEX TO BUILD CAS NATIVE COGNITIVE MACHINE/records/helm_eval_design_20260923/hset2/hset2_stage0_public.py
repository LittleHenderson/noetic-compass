"""HSET-2 stage 0: the PUBLIC stage. It runs first, and its outputs are committed before the sealed stage runs.

Label: CLAUDE_BUILT_CLAUDE_CHECKED (temporary takeover while Codex is away). Implements
`../EVALUATION_DESIGN_v0_4.md` section 3 with Amendment A1 D1 (the group key and the side rule, byte for byte).

What it does, in order (no salt, no sealed material, no model):
  1. PUBLIC_EXCLUDED version 1: every 5- or 6-node class in the larger-question fixture file (commit 785c9bd1,
     sha256 7f0760c7...), listed by canonical-form digest. The canonical form is the D-1 oracle's method M1
     (`oracle_isomorphism.canonical_form`: the smallest sorted edge list over all n! node orders).
  2. Every 6-node class: acyclic, weakly connected, every in-degree and out-degree at most 4 (expected 5,074).
  3. Remove PUBLIC_EXCLUDED; group the rest by degree multiset; put each whole group on the DEV or TEST side by the
     pinned rule of A1 D1.
  4. DEV_NEW_6: 60 foci from the reviewed MIX sampler (`hset1b_build.sample_class`) with the public seed
     `HSET-2-dev-shapes-v0.1`, keeping only DEV-side classes. DEV_DECOYS_6: every other DEV-side class.
  5. Write the DEV-side and TEST-side group lists with their digests.

Everything here is public by design: the side rule is public, so anyone can compute the TEST side (the forbidden
set). Which TEST-side classes become the TEST foci is decided only by the sealed stage, with the HSET-2 salt.

    python -B hset2_stage0_public.py [--fixture-file PATH] [--out DIR]      # write the committed outputs
    python -B hset2_stage0_public.py --check [--fixture-file PATH]          # recompute; exit 1 unless identical

Without --fixture-file the fixture is read from git objects at the pinned commit (`git cat-file`), never from a
working file, and its sha256 is checked either way.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import itertools
import json
import pathlib
import random
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
DESIGN_DIR = HERE.parent
HSET1A_DIR = DESIGN_DIR / "hset1a"
ORACLE_DIR = DESIGN_DIR / "d1_acceptance"
CNCM = HERE.parents[2]

LABEL = "CLAUDE_BUILT_CLAUDE_CHECKED"
FIXTURE_COMMIT = "785c9bd10f1416deb95f9c30aacb43124134fe45"
FIXTURE_REL = "research/CAS_META_2_COMPOSITION/eval_paths/fixtures/larger_question_fixtures_v0_1.json"
FIXTURE_SHA256 = "7f0760c768398c4f1ff221cbd627c2db5367100769b4e2c13b62cb0a4bc95fc3"
GROUP_SIDE_PREFIX = b"HSET-2-group-side-v0.1:"          # A1 D1, byte for byte
DEV_SIDE_BYTE_BELOW = 64                                   # A1 D1: DEV iff the first digest byte < 64
DEV_SEED = "HSET-2-dev-shapes-v0.1"                        # design s3 step 4, public
HSET1B_DEV_SEED = "HSET-1B-dev-shapes-v0.1"                # only for a printed custody diagnostic
N6 = 6
MAX_DEGREE = 4
FOCI_PER_SPLIT = 60
EXPECTED_CLASSES = {5: 267, 6: 5074}                       # 6: with every degree <= 4 (design s3; review census)
EXPECTED_PUBLIC_EXCLUDED = {5: 3, 6: 4}                    # the coordinator's count; verified, not assumed

PUBLIC_EXCLUDED_FILE = "PUBLIC_EXCLUDED_v1.json"
DEV_GROUPS_FILE = "STAGE0_DEV_SIDE_GROUPS.json"
TEST_GROUPS_FILE = "STAGE0_TEST_SIDE_GROUPS.json"
SUMMARY_FILE = "STAGE0_SUMMARY.json"


def paths():
    sys.dont_write_bytecode = True
    for p in (str(ORACLE_DIR), str(HSET1A_DIR), str(HERE)):
        if p not in sys.path:
            sys.path.insert(0, p)


def modules():
    paths()
    import hset_worlds as hw
    import hset1b_build as B
    import oracle_isomorphism as oracle
    return hw, B, oracle


# ============================================================================ keys, digests, sides
def class_key(shape):
    """The class key HSET-1A and HSET-1B use: canon([n, [[a, b], ...]]) of the oracle canonical form."""
    hw, _, _ = modules()
    n, edges = shape
    return hw.canon([n, [list(e) for e in edges]])


def key_shape(key):
    n, edges = json.loads(key)
    return n, tuple(tuple(e) for e in edges)


def class_digest(key):
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def group_key(shape):
    """A1 D1: `hset_worlds.canon([n, [[i, o], ...]])`, the sorted joint (in-degree, out-degree) pairs."""
    hw, _, _ = modules()
    n, edges = shape
    return hw.canon([n, [list(p) for p in hw.degree_multiset(n, list(edges))]])


def side_of_group(gkey):
    """A1 D1: DEV iff sha256(b"HSET-2-group-side-v0.1:" + key.encode("utf-8")).digest()[0] < 64."""
    return "DEV" if hashlib.sha256(GROUP_SIDE_PREFIX + gkey.encode("utf-8")).digest()[0] < DEV_SIDE_BYTE_BELOW else "TEST"


def list_digest(value):
    hw, _, _ = modules()
    return hw.sha(value)


def max_degree(n, edges):
    ind, outd = [0] * n, [0] * n
    for a, b in edges:
        outd[a] += 1
        ind[b] += 1
    return max(ind + outd)


# ============================================================================ enumeration
def _refined_colours(n, edges):
    """Colour refinement with canonical integer names: equal on isomorphic graphs, node for node."""
    outs, ins = [[] for _ in range(n)], [[] for _ in range(n)]
    for a, b in edges:
        outs[a].append(b)
        ins[b].append(a)
    colour = [(len(ins[v]), len(outs[v])) for v in range(n)]
    classes = len(set(colour))
    while True:
        signature = [(colour[v], tuple(sorted(colour[u] for u in outs[v])), tuple(sorted(colour[u] for u in ins[v])))
                     for v in range(n)]
        names = {s: i for i, s in enumerate(sorted(set(signature)))}
        new = [names[s] for s in signature]
        if len(names) == classes:
            return new
        colour, classes = new, len(names)


def _pre_key(n, edges):
    """A fast canonical labelling used ONLY to skip repeated work: the smallest relabelled edge list over the node
    orders that respect the refined colours. Equal keys imply isomorphic graphs (a key is a relabelled copy), and
    `enumerate_classes` fails closed if two keys ever share an oracle canonical form."""
    colour = _refined_colours(n, edges)
    groups = [sorted(v for v in range(n) if colour[v] == c) for c in sorted(set(colour))]
    best = None
    for parts in itertools.product(*(itertools.permutations(g) for g in groups)):
        order = [v for part in parts for v in part]
        position = {v: i for i, v in enumerate(order)}
        key = tuple(sorted((position[a], position[b]) for a, b in edges))
        if best is None or key < best:
            best = key
    return best


def _connected(n, edges):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in edges:
        parent[find(a)] = find(b)
    return len({find(v) for v in range(n)}) == 1


def enumerate_classes(n, max_deg=MAX_DEGREE):
    """Every weakly connected DAG on n nodes with every in/out degree <= max_deg, as oracle canonical forms.

    Every DAG has a topological numbering, so every class appears among the edge sets with edges i -> j, i < j
    (2^(n(n-1)/2) sets; 32,768 at 6 nodes). Each class is reduced to `oracle_isomorphism.canonical_form` (method M1,
    all n! orders), the same form `hset1b_build.sample_class` returns, so sampler draws and this list agree.
    """
    _, _, oracle = modules()
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    first = {}
    for mask in range(1, 1 << len(pairs)):
        edges = [pairs[b] for b in range(len(pairs)) if mask >> b & 1]
        if len(edges) < n - 1 or max_degree(n, edges) > max_deg or not _connected(n, edges):
            continue
        key = _pre_key(n, edges)
        if key not in first:
            first[key] = edges
    forms = {}
    for key, edges in first.items():
        form = oracle.canonical_form(n, edges)
        if form in forms:
            raise AssertionError("PRE_KEY_NOT_CANONICAL")
        forms[form] = key
    return sorted(forms)


# ============================================================================ PUBLIC_EXCLUDED
def read_fixture_bytes(fixture_file=None, package_root=None):
    if fixture_file is not None:
        raw = pathlib.Path(fixture_file).read_bytes()
    elif package_root is not None:
        raw = (pathlib.Path(package_root) / FIXTURE_REL).read_bytes()
    else:
        prefix = subprocess.run(["git", "-C", str(CNCM), "rev-parse", "--show-prefix"], capture_output=True,
                                check=True).stdout.decode().strip()
        raw = subprocess.run(["git", "-C", str(CNCM), "cat-file", "blob", "%s:%s%s" % (FIXTURE_COMMIT, prefix, FIXTURE_REL)],
                             capture_output=True, check=True).stdout
    if hashlib.sha256(raw).hexdigest() != FIXTURE_SHA256:
        raise SystemExit("FIXTURE_REFUSED: the fixture file is not the pinned one (sha256 %s...)" % FIXTURE_SHA256[:8])
    return raw


def public_excluded(raw):
    """Every 5- or 6-node class in the fixture file, from BOTH its shape table and every world it builds.

    Each class is recomputed with the oracle (method M1) from the shape's edges and must equal the canonical form
    the fixture file itself records; a world's node count must equal its shape's. Degree-5 shapes are kept (they
    are public too), and are marked as lying outside the 6-node universe of this test.
    """
    _, _, oracle = modules()
    data = json.loads(raw.decode("utf-8"))
    shapes = data["shapes"]
    names = collections.defaultdict(lambda: {"shapes": set(), "worlds": set()})
    for name, s in shapes.items():
        n, edges = s["nodes"], [tuple(e) for e in s["edges"]]
        form = oracle.canonical_form(n, edges)
        if [form[0], [list(e) for e in form[1]]] != s["canonical_form"]:
            raise AssertionError("FIXTURE_CANONICAL_FORM_DISAGREES:" + name)
        if n in (5, 6):
            names[class_key(form)]["shapes"].add(name)
    for wname, w in data["worlds"].items():
        s = shapes[w["shape"]]
        if len(w["labels_by_node"]) != s["nodes"]:
            raise AssertionError("FIXTURE_WORLD_SIZE:" + wname)
        if s["nodes"] in (5, 6):
            form = oracle.canonical_form(s["nodes"], [tuple(e) for e in s["edges"]])
            names[class_key(form)]["worlds"].add(wname)
    rows = []
    for key in sorted(names, key=class_digest):
        n, edges = key_shape(key)
        rows.append({"digest": class_digest(key), "canonical_form": key, "nodes": n, "edges": len(edges),
                     "max_degree": max_degree(n, edges), "inside_degree_4_universe": max_degree(n, edges) <= MAX_DEGREE,
                     "fixture_shape_names": sorted(names[key]["shapes"]),
                     "fixture_world_names": sorted(names[key]["worlds"]),
                     "degree_multiset_group_key": group_key((n, edges))})
    return rows


def public_excluded_document(raw):
    rows = public_excluded(raw)
    counts = collections.Counter(r["nodes"] for r in rows)
    doc = {"schema": "claude.hset2-public-excluded/1", "label": LABEL, "version": 1,
           "rule": ("EVALUATION_DESIGN_v0_4 s3: every 5- or 6-node class used publicly with a trained model or in any "
                    "candidate bank. Open-ended: any later public shape joins before its first use. After the HSET-2 "
                    "build (A1 D6), a new public 6-node shape must be a DEV-side class and a new public 5-node shape a "
                    "DEV_NEW_5 class; anything else is refused before use."),
           "version_1_input": {"commit": FIXTURE_COMMIT, "path": FIXTURE_REL, "sha256": FIXTURE_SHA256},
           "canonical_form": ("oracle_isomorphism.canonical_form (D-1 oracle method M1): the smallest sorted edge list "
                              "over all n! node orders; key = hset_worlds.canon([n, [[a, b], ...]])"),
           "digest": "sha256 of the key's UTF-8 bytes",
           "classes": rows, "counts_by_nodes": {str(k): counts[k] for k in sorted(counts)},
           "class_digests_digest": list_digest(sorted(r["digest"] for r in rows))}
    for n, expected in EXPECTED_PUBLIC_EXCLUDED.items():
        if counts[n] != expected:
            raise AssertionError("PUBLIC_EXCLUDED_COUNT n=%d: %d, expected %d" % (n, counts[n], expected))
    return doc


# ============================================================================ sampler
def draw_side(seed_material, label, n, count, allowed, exclude=()):
    """The reviewed MIX sampler (hset1b_build.sample_class) with rng Random(keyed_int(seed, label, n)), keeping only
    classes in `allowed` and never one in `exclude`, in draw order, without repeats. Returns (keys, draws)."""
    hw, B, oracle = modules()
    rng = random.Random(hw.keyed_int(seed_material, label, n))
    got, seen, draws = [], set(exclude), 0
    while len(got) < count:
        draws += 1
        if draws > B.MAX_DRAWS:
            raise RuntimeError("SHAPE_DRAW_LIMIT")
        key = class_key(B.sample_class(rng, n, oracle))
        if key in allowed and key not in seen:
            seen.add(key)
            got.append(key)
    return got, draws


# ============================================================================ stage 0
def compute(raw):
    """Everything stage 0 writes, as plain data. Deterministic; no salt."""
    hw, B, oracle = modules()
    t0 = time.monotonic()
    pe_doc = public_excluded_document(raw)
    excluded = {r["canonical_form"] for r in pe_doc["classes"]}
    classes6 = [class_key(s) for s in enumerate_classes(N6)]
    if len(classes6) != EXPECTED_CLASSES[N6]:
        raise AssertionError("SIX_NODE_CLASS_COUNT %d" % len(classes6))
    universe = [k for k in classes6 if k not in excluded]
    excluded_in_universe = sorted(k for k in classes6 if k in excluded)
    groups = collections.defaultdict(list)
    for k in universe:
        groups[group_key(key_shape(k))].append(k)
    side = {g: side_of_group(g) for g in groups}
    lists = {s: [{"group_key": g, "classes": sorted(groups[g])} for g in sorted(groups) if side[g] == s]
             for s in ("DEV", "TEST")}
    dev_side = {k for row in lists["DEV"] for k in row["classes"]}
    test_side = {k for row in lists["TEST"] for k in row["classes"]}
    assert not dev_side & test_side and len(dev_side) + len(test_side) == len(universe)
    dev_new_6, dev_draws = draw_side(DEV_SEED, "dev", N6, FOCI_PER_SPLIT, dev_side)
    dev_decoys_6 = sorted(dev_side - set(dev_new_6))
    group_of = {k: g for g, members in groups.items() for k in members}

    def partners_on_side(k, side_set):
        return [c for c in groups[group_of[k]] if c != k and c in side_set]
    dev_analogy = [k for k in dev_new_6 if len(partners_on_side(k, dev_side)) >= 4]
    dev_corr = [k for k in dev_new_6 if len(partners_on_side(k, dev_side)) >= 1]
    # Custody diagnostic only (printed, not acted on): where do the 40 public HSET-1B DEV_NEW_6 classes fall?
    hset1b_dev6, _ = B.draw(random.Random(hw.keyed_int(HSET1B_DEV_SEED, "dev", N6)), N6, 40, oracle, ())
    hset1b_keys = [class_key(s) for s in hset1b_dev6]

    def side_stats(rows):
        sizes = collections.Counter(len(r["classes"]) for r in rows)
        return {"groups": len(rows), "classes": sum(len(r["classes"]) for r in rows),
                "groups_with_5_or_more_classes": sum(v for s, v in sizes.items() if s >= 5),
                "groups_with_2_or_more_classes": sum(v for s, v in sizes.items() if s >= 2),
                "group_size_histogram": {str(s): sizes[s] for s in sorted(sizes)}}
    group_docs = {}
    for s in ("DEV", "TEST"):
        body = {"schema": "claude.hset2-stage0-side-groups/0.1", "label": LABEL, "side": s,
                "rule": ('group key = hset_worlds.canon([6, [[in, out], ...]]) over hset_worlds.degree_multiset; '
                         'DEV iff sha256(b"HSET-2-group-side-v0.1:" + key.encode("utf-8")).digest()[0] < 64'),
                "public_excluded_removed_first": pe_doc["class_digests_digest"],
                "group_count": len(lists[s]), "class_count": sum(len(r["classes"]) for r in lists[s]),
                "groups": lists[s]}
        body["groups_digest"] = list_digest(lists[s])
        group_docs[s] = body
    summary = {
        "schema": "claude.hset2-stage0-summary/0.1", "label": LABEL,
        "design": "EVALUATION_DESIGN_v0_4.md s3 + Amendment A1 D1 (d840ea02)",
        "public_excluded": {"file": PUBLIC_EXCLUDED_FILE, "class_digests_digest": pe_doc["class_digests_digest"],
                            "counts_by_nodes": pe_doc["counts_by_nodes"],
                            "six_node_classes_inside_the_degree_4_universe": len(excluded_in_universe)},
        "six_node_universe": {"classes_enumerated": len(classes6), "classes_after_public_excluded": len(universe),
                              "degree_groups": len(groups), "all_classes_digest": list_digest(classes6)},
        "sides": {s: side_stats(lists[s]) for s in ("DEV", "TEST")},
        "groups_digests": {s: group_docs[s]["groups_digest"] for s in ("DEV", "TEST")},
        "dev_new_6": {"seed": DEV_SEED, "rng": 'random.Random(hset_worlds.keyed_int(seed, "dev", 6))',
                      "sampler": "hset1b_build.sample_class (MIX), DEV-side classes only, no repeats",
                      "draws": dev_draws, "classes_in_draw_order": dev_new_6, "digest": list_digest(dev_new_6)},
        "dev_decoys_6": {"count": len(dev_decoys_6), "classes": dev_decoys_6, "digest": list_digest(dev_decoys_6)},
        "dev_foci_usable": {
            "analogy_at_least_4_same_group_dev_side_partners": len(dev_analogy),
            "analogy_distinct_degree_groups": len({group_of[k] for k in dev_analogy}),
            "correspondence_at_least_1_same_group_dev_side_partner": len(dev_corr),
            "correspondence_distinct_degree_groups": len({group_of[k] for k in dev_corr})},
        "custody_diagnostic_hset1b_dev_new_6": {
            "note": ("the 40 public HSET-1B DEV_NEW_6 classes (public seed HSET-1B-dev-shapes-v0.1). They are not in "
                     "PUBLIC_EXCLUDED v1 (design s3 names only the fixture file); printed so the owner can decide"),
            "on_dev_side": sum(k in dev_side for k in hset1b_keys), "on_test_side": sum(k in test_side for k in hset1b_keys),
            "in_public_excluded": sum(k in excluded for k in hset1b_keys)},
        "seconds": round(time.monotonic() - t0, 1)}
    return pe_doc, group_docs, summary


def dump_bytes(value):
    return (json.dumps(value, indent=1, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def outputs(raw):
    """{file name: exact bytes}. The summary records the sha256 of the three list files."""
    pe_doc, group_docs, summary = compute(raw)
    files = {PUBLIC_EXCLUDED_FILE: dump_bytes(pe_doc), DEV_GROUPS_FILE: dump_bytes(group_docs["DEV"]),
             TEST_GROUPS_FILE: dump_bytes(group_docs["TEST"])}
    summary = dict(summary, files_sha256={name: hashlib.sha256(b).hexdigest() for name, b in sorted(files.items())})
    seconds = summary.pop("seconds")
    files[SUMMARY_FILE] = dump_bytes(summary)
    return files, seconds


def committed_check(files, directory=HERE):
    """Names of files whose committed bytes differ (CRLF normalised to LF) from the recomputed ones."""
    bad = []
    for name, data in files.items():
        path = pathlib.Path(directory) / name
        if not path.is_file() or path.read_bytes().replace(b"\r\n", b"\n") != data:
            bad.append(name)
    return bad


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-file", default=None)
    parser.add_argument("--out", default=str(HERE))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw = read_fixture_bytes(args.fixture_file)
    files, seconds = outputs(raw)
    summary = json.loads(files[SUMMARY_FILE])
    if args.check:
        bad = committed_check(files, args.out)
        print(json.dumps({"stage0_check": "IDENTICAL" if not bad else "DIFFERS", "differs": bad, "seconds": seconds}))
        return 1 if bad else 0
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (out / name).write_bytes(data)
    print(json.dumps({k: summary[k] for k in ("public_excluded", "six_node_universe", "sides", "groups_digests",
                                              "dev_foci_usable", "custody_diagnostic_hset1b_dev_new_6")}, indent=1))
    print(json.dumps({"dev_new_6_draws": summary["dev_new_6"]["draws"], "dev_decoys_6": summary["dev_decoys_6"]["count"],
                      "files_sha256": summary["files_sha256"], "seconds": seconds}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
