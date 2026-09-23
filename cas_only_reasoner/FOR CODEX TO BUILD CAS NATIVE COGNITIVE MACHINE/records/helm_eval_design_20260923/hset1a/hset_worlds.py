"""Shared helpers for the HSET evaluation sets (Claude, evaluation designer and sealed-test custodian).

What this module does, in plain words:
  * reads the TRAINED vocabulary (the four training domains' settings, kinds, node labels and function
    templates) from the same pinned literals `source.training_families()` reads, and nothing from the
    development or held-out domains;
  * builds a world from a small structural spec (node labels in structural order, edges between structural
    node numbers, declarations, the three primary nodes) through the frozen `source._facts` / `source._world`,
    so every world passes the frozen source validator by construction;
  * builds a closed model packet exactly as `course.model_packet` shapes one (0 supports), over the frozen
    64-world training bank plus the new focus world (65 worlds, the frozen union limit);
  * computes structural facts on plain graphs (node numbers 0..n-1): automorphisms, roots, reachability,
    shortest distance, and the frozen reach rules re-implemented over an explicit node ranking.

It never imports the checker. Gold answers come from the frozen checker in the callers, and the callers
cross-check them against the re-implementation here, so a slip in either one fails the build.

A graph is (n, edges) with edges a sorted tuple of (a, b) pairs over 0..n-1. The rank of a node is the position
of its label in sorted(labels), which is exactly the `/n<i>` index `source._world` assigns.
"""
from __future__ import annotations

import ast
import collections
import hashlib
import itertools
import json
from copy import deepcopy

TRAINING_DOMAINS = ("mechanical", "grammatical", "procedural", "container")
REACH_FIRST = "first_direct_constituent_lexical_v1"
REACH_BFS = "bfs_immediate_predecessor_lexical_v1"


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha(value):
    return hashlib.sha256(canon(value).encode("utf-8")).hexdigest()


def keyed_int(material, *parts):
    """A deterministic 256-bit integer from a secret or public seed string plus identifying parts."""
    return int(hashlib.sha256(("|".join([material] + [str(p) for p in parts])).encode("utf-8")).hexdigest(), 16)


# ----------------------------------------------------------------------------- trained vocabulary
def vocabulary(source):
    """Per training domain: the one setting, the 16 kinds, every node label, and the function template.

    Only the training domains' entries of `_FUNCTION` are evaluated (the same key-by-key literal reading
    `source.training_families` uses), and every training family's own function string is re-derived from the
    template as a proof that the template is the one training used.
    """
    families = source.training_families()
    constants = {}
    for node in ast.parse(source.CORPUS_PATH.read_bytes(), str(source.CORPUS_PATH)).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            constants[node.targets[0].id] = node.value
    table = constants["_FUNCTION"]
    templates = {}
    for key, value in zip(table.keys, table.values):
        domain = ast.literal_eval(key)
        if domain in TRAINING_DOMAINS:
            templates[domain] = ast.literal_eval(value)
    result = {}
    for domain in TRAINING_DOMAINS:
        rows = [f for f in families if f["domain"] == domain]
        assert len(rows) == 16, domain
        settings = sorted({f["setting"] for f in rows})
        assert len(settings) == 1, domain
        for f in rows:
            assert templates[domain] % {"whole": f["labels"][0], "child": f["labels"][1]} == f["function"], f["family_id"]
        result[domain] = {"setting": settings[0], "kinds": sorted({f["kind"] for f in rows}),
                          "labels": sorted({label for f in rows for label in f["labels"]}),
                          "function_template": templates[domain]}
    return result, families


# ----------------------------------------------------------------------------- plain graphs
def children(edges, v):
    return [b for a, b in edges if a == v]


def roots(n, edges):
    targets = {b for _, b in edges}
    return [v for v in range(n) if v not in targets]


def automorphisms(n, edges):
    edge_set = set(edges)
    return [p for p in itertools.permutations(range(n)) if {(p[a], p[b]) for a, b in edges} == edge_set]


def reachable(edges, start):
    """Nodes reachable from `start` by one or more edges (start itself only if on a cycle, never here)."""
    out = collections.defaultdict(list)
    for a, b in edges:
        out[a].append(b)
    seen, stack = set(), [start]
    while stack:
        x = stack.pop()
        for y in out[x]:
            if y not in seen:
                seen.add(y)
                stack.append(y)
    return seen


def distance(edges, start, goal):
    out = collections.defaultdict(list)
    for a, b in edges:
        out[a].append(b)
    frontier, seen, d = [start], {start}, 0
    while frontier:
        if goal in frontier:
            return d
        nxt = []
        for x in frontier:
            for y in out[x]:
                if y not in seen:
                    seen.add(y)
                    nxt.append(y)
        frontier, d = nxt, d + 1
    return None


def degree_multiset(n, edges):
    ind, outd = [0] * n, [0] * n
    for a, b in edges:
        outd[a] += 1
        ind[b] += 1
    return tuple(sorted(zip(ind, outd)))


def _bfs_path(adjacency, start, goal):
    """The frozen checker's `_bfs`: first path found, seen-at-enqueue, neighbours in the given order."""
    queue, seen = collections.deque([[start]]), {start}
    while queue:
        path = queue.popleft()
        if path[-1] == goal:
            return path
        for child in adjacency[path[-1]]:
            if child not in seen:
                seen.add(child)
                queue.append(path + [child])
    return None


def reach_gold(n, edges, whole, part, rank, rule):
    """The frozen reach rules over plain node numbers; `rank[v]` is node v's sorted-reference position.

    Returns (state, via_node_or_None). DIRECT takes precedence under both rules.
    """
    adjacency = {v: sorted(children(edges, v), key=lambda c: rank[c]) for v in range(n)}
    if part in adjacency[whole]:
        return ("DIRECT", None)
    if rule == REACH_FIRST:
        for first in adjacency[whole]:
            if _bfs_path(adjacency, first, part) is not None:
                return ("VIA", first)
        return ("ABSENT", None)
    assert rule == REACH_BFS, rule
    path = _bfs_path(adjacency, whole, part)
    return ("ABSENT", None) if path is None else ("VIA", path[-2])


def reach_answer_set(n, edges, whole, part, rule):
    """Every gold answer the rule gives over ALL n! rankings. More than one answer = a lexical TIE case."""
    return sorted({reach_gold(n, edges, whole, part, dict(enumerate(order)), rule)
                   for order in itertools.permutations(range(n))}, key=repr)


# ----------------------------------------------------------------------------- worlds and packets
def world_from_spec(source, spec):
    """spec = {labels: [label of node 0, 1, ...], edges: [[a, b], ...] over node numbers,
               declarations: {domain, kind, setting, function}, primary: [whole, p2, p3] node numbers}."""
    labels = list(spec["labels"])
    edge_rows = sorted(({"source": labels[a], "target": labels[b]} for a, b in spec["edges"]),
                       key=lambda e: (e["source"], e["target"]))
    declarations = {k: spec["declarations"][k] for k in ("domain", "kind", "setting", "function")}
    primary = [labels[i] for i in spec["primary"]]
    return source._world(source._facts(labels, edge_rows, declarations, primary))


def node_refs(world, spec):
    """Structural node number -> this world's node ref."""
    by_label = {node["label"]: node["ref"] for node in world["nodes"]}
    return [by_label[label] for label in spec["labels"]]


def ranks(spec):
    order = sorted(spec["labels"])
    return {i: order.index(label) for i, label in enumerate(spec["labels"])}


def build_packet(source, answers, course, bank, focus, *, kind, rule, arguments, cue):
    """A closed packet shaped exactly like `course.model_packet` output, with 0 supports."""
    worlds = {w["world_id"]: w for w in bank["worlds"]}
    assert focus["world_id"] not in worlds, "a generated focus world coincides with a bank world"
    worlds[focus["world_id"]] = focus
    public = {"focus_world_id": focus["world_id"], "worlds": [worlds[k] for k in sorted(worlds)],
              "bank": deepcopy(bank["bank"])}
    query = answers.compile_query(public, kind=kind, rule=rule, arguments=arguments, focus_world_id=focus["world_id"])
    body = {"schema": course.PACKET_SCHEMA, "source_digest": source.public_digest(public),
            "source_world_id": focus["world_id"], "query": query, "cue": cue,
            "instruction": course.REQUESTS[kind], "role_catalog": deepcopy(course.ROLE_CATALOG), "supports": []}
    return {"source": public, "record": {"record_id": "typed-input-" + source.digest(body), **body}}


def packet_from_item(source, answers, course, bank, item):
    """Rebuild the exact packet of one committed item: {world: spec, kind, rule, cue, whole, part}."""
    focus = world_from_spec(source, item["world"])
    refs = node_refs(focus, item["world"])
    arguments = {}
    if item.get("whole") is not None:
        arguments["whole"] = refs[item["whole"]]
    if item.get("part") is not None:
        arguments["part"] = refs[item["part"]]
    return build_packet(source, answers, course, bank, focus, kind=item["kind"], rule=item["rule"],
                        arguments=arguments or None, cue=item["cue"]), focus, refs
