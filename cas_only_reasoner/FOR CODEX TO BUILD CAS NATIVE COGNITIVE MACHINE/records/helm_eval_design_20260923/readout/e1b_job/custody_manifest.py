"""Stage 0 of E1b: the custody manifest check (EVALUATION_DESIGN_v0_4 s8). Pure Python; no torch.

Label: CLAUDE_BUILT_CLAUDE_CHECKED; EVALUATION_NOT_INDEPENDENT_OF_THE_PROJECT.

THE RULE (s8, word for word in meaning): before any TEST reading, list every world touched by any update,
development evaluation, DEV reading, probe or smoke input, and every larger-question fixture. Check the list
against the WHOLE forbidden set (TEST_NEW_6, WITHHELD_6, TEST_NEW_5, WITHHELD_5) by two isomorphism methods, and
fail closed on any match.

THE TWO METHODS are the D-1 oracle's own (d1_acceptance/oracle_isomorphism.py, the reviewed isomorphism oracle):
  M1  canonical form: the smallest sorted edge list over every node order, turned into the same class key the
      builder uses (hset_worlds.canon([n, edges])); a match is membership in the forbidden key set;
  M2  colour refinement plus exhaustive isomorphism enumeration (`all_isomorphisms_m2`) against every forbidden
      class with the same node count, edge count and joint degree multiset.
Both must find nothing, and they must agree on every world. A disagreement stops the job too.

WHAT COUNTS AS A WORLD in a touched file (every JSON value is walked):
  * a built world: {"nodes": [{"ref": ...}, ...], "contains": [{"source": ref, "target": ref}, ...]};
  * a shape: {"nodes": <int>, "edges": [[a, b], ...]};
  * a world spec: {"labels": [...], "edges": [[a, b], ...]} (node count = number of labels);
  * a class key string exactly like "[5,[[0,1],[0,2]]]".
A world-like object that cannot be read stops the job (CUSTODY_MANIFEST_UNREADABLE): nothing is skipped silently.

EVERY KIND MUST BE DECLARED: updates, development_evaluation, dev_reading, probe, smoke, fixture. A kind with no
file is declared explicitly as NONE with a reason. A missing kind stops the job (CUSTODY_MANIFEST_INCOMPLETE).

PUBLIC OUTPUT: counts only. A matching world is itself a TEST class, so its key goes to the sealed detail only.
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import re

KINDS = ("updates", "development_evaluation", "dev_reading", "probe", "smoke", "fixture")
PASS_WORD, STOP_WORD = "CUSTODY_MANIFEST_PASS", "CUSTODY_MANIFEST_STOP"
CLASS_KEY = re.compile(r"^\[[1-9],\[(\[\d,\d\](,\[\d,\d\])*)?\]\]$")


class Unreadable(Exception):
    pass


def _built(obj):
    refs = [node.get("ref") if isinstance(node, dict) else None for node in obj["nodes"]]
    if not refs or any(not isinstance(r, str) for r in refs) or len(set(refs)) != len(refs):
        raise Unreadable("BUILT_WORLD_NODES")
    index = {r: i for i, r in enumerate(sorted(refs))}
    edges = []
    for e in obj["contains"]:
        if not isinstance(e, dict) or e.get("source") not in index or e.get("target") not in index:
            raise Unreadable("BUILT_WORLD_EDGE")
        edges.append((index[e["source"]], index[e["target"]]))
    return len(refs), edges


def _pairs(n, edges):
    out = []
    for e in edges:
        if (not isinstance(e, (list, tuple)) or len(e) != 2 or not all(isinstance(x, int) for x in e)
                or not all(0 <= x < n for x in e)):
            raise Unreadable("EDGE_LIST")
        out.append((e[0], e[1]))
    return n, out


def worlds_in(value):
    """Every world found anywhere in a parsed JSON value, as (n, sorted edge tuple)."""
    found, stack = [], [value]
    while stack:
        obj = stack.pop()
        if isinstance(obj, dict):
            if isinstance(obj.get("nodes"), list) and isinstance(obj.get("contains"), list):
                found.append(_built(obj))
            elif isinstance(obj.get("nodes"), int) and isinstance(obj.get("edges"), list):
                found.append(_pairs(obj["nodes"], obj["edges"]))
            elif isinstance(obj.get("labels"), list) and isinstance(obj.get("edges"), list):
                found.append(_pairs(len(obj["labels"]), obj["edges"]))
            stack.extend(obj.values())
        elif isinstance(obj, list):
            stack.extend(obj)
        elif isinstance(obj, str) and CLASS_KEY.match(obj):
            n, edges = json.loads(obj)
            found.append(_pairs(n, edges))
    return [(n, tuple(sorted(set(e)))) for n, e in found]


def degree_signature(n, edges):
    ind, outd = [0] * n, [0] * n
    for a, b in edges:
        outd[a] += 1
        ind[b] += 1
    return n, len(edges), tuple(sorted(zip(ind, outd)))


def parse_touched(specs):
    """specs: ["KIND=PATH", "KIND=NONE:reason", ...] -> {kind: [source rows]} (files read here, hashed)."""
    out = collections.defaultdict(list)
    for spec in specs:
        kind, _, rest = spec.partition("=")
        if kind not in KINDS or not rest:
            raise ValueError("TOUCHED_SPEC:%s" % kind)
        if rest.startswith("NONE:"):
            out[kind].append({"declared_empty": rest[5:].strip() or "no reason given"})
            continue
        raw = pathlib.Path(rest).read_bytes()
        try:
            worlds = worlds_in(json.loads(raw))
            unreadable = None
        except (ValueError, Unreadable) as error:
            worlds, unreadable = [], type(error).__name__ + ":" + str(error)[:60]
        out[kind].append({"name": pathlib.Path(rest).name, "sha256": hashlib.sha256(raw).hexdigest(),
                          "bytes": len(raw), "worlds": worlds, "unreadable": unreadable})
    return dict(out)


def check(touched, forbidden, oracle, class_key):
    """(public counts, sealed detail). `forbidden`: class keys; `oracle`: the D-1 oracle module; `class_key`:
    shape -> key (hset2_stage0_public.class_key). Fails closed; the public part never names a class."""
    reasons = []
    missing = [k for k in KINDS if not touched.get(k)]
    if missing:
        reasons.append("CUSTODY_MANIFEST_INCOMPLETE:%s" % ",".join(missing))
    bad_files = [(k, s["name"], s["unreadable"]) for k in touched for s in touched[k] if s.get("unreadable")]
    if bad_files:
        reasons.append("CUSTODY_MANIFEST_UNREADABLE:%d files" % len(bad_files))
    forbidden_set, buckets, sizes = set(forbidden), collections.defaultdict(list), collections.Counter()
    for key in forbidden:
        n, edges = json.loads(key)
        if n not in (5, 6):
            reasons.append("FORBIDDEN_SET_NOT_5_OR_6_NODES")
            break
        edges = [tuple(e) for e in edges]
        buckets[degree_signature(n, edges)].append((n, frozenset(edges)))
        sizes[str(n)] += 1
    shapes = collections.defaultdict(set)                      # (n, edges) -> kinds it came from
    for kind, sources in touched.items():
        for s in sources:
            for shape in s.get("worlds", ()):
                shapes[shape].add(kind)
    m1_hits, m2_hits = set(), set()
    for (n, edges) in shapes:
        if n in (5, 6) and class_key(oracle.canonical_form(n, list(edges))) in forbidden_set:
            m1_hits.add((n, edges))
        for other in buckets.get(degree_signature(n, edges), ()):
            if oracle.all_isomorphisms_m2((n, frozenset(edges)), other):
                m2_hits.add((n, edges))
                break
    if m1_hits or m2_hits:
        reasons.append("CUSTODY_MANIFEST_MATCH: %d touched shapes are forbidden TEST-side classes (M1 %d, M2 %d)"
                       % (len(m1_hits | m2_hits), len(m1_hits), len(m2_hits)))
    if m1_hits != m2_hits:
        reasons.append("CUSTODY_METHODS_DISAGREE:%d" % len(m1_hits ^ m2_hits))
    by_kind = {k: {"sources": [({"declared_empty": s["declared_empty"]} if "declared_empty" in s else
                                {"name": s["name"], "sha256": s["sha256"], "bytes": s["bytes"],
                                 "worlds_found": len(s["worlds"]), "unreadable": bool(s["unreadable"])})
                               for s in touched.get(k, [])],
                   "distinct_shapes": sum(1 for kinds in shapes.values() if k in kinds),
                   "matches": sum(1 for sh in (m1_hits | m2_hits) if k in shapes[sh])} for k in KINDS}
    public = {"status": PASS_WORD if not reasons else STOP_WORD, "reasons": reasons,
              "rule": "design s8: every touched world against the whole forbidden set, two isomorphism methods "
                      "(D-1 oracle M1 canonical form, M2 refinement plus enumeration), fail closed",
              "kinds": by_kind, "distinct_touched_shapes": len(shapes),
              "distinct_touched_shapes_by_node_count": dict(sorted(collections.Counter(str(n) for n, _ in shapes).items())),
              "forbidden_classes_by_node_count": dict(sorted(sizes.items())),
              "matches_m1": len(m1_hits), "matches_m2": len(m2_hits), "disagreements": len(m1_hits ^ m2_hits)}
    sealed = {"matching_touched_shapes": [{"shape": [n, [list(e) for e in edges]], "kinds": sorted(shapes[(n, edges)]),
                                           "m1": (n, edges) in m1_hits, "m2": (n, edges) in m2_hits}
                                          for n, edges in sorted(m1_hits | m2_hits)],
              "unreadable_files": bad_files}
    return public, sealed
