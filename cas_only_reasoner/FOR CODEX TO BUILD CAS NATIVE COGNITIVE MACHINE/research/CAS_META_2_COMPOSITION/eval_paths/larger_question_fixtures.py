"""Public 5- and 6-node fixtures for the larger-question path (v0.1): build, write, check and load.

PLAIN SUMMARY. These are small, hand-designed, PUBLIC integration fixtures. They exist to prove that questions of
every kind can travel read -> forward -> decode -> grade without an error. They are NOT an evaluation set, they
carry no claim about Helm, and their shapes must be kept out of any sealed TEST (their canonical forms are
listed in the file so a custodian can exclude them).

HOW THEY ARE BUILT. The same public construction as the HSET builders (`hset_worlds.world_from_spec` and
`build_packet`, read from the integration branch; no salt, no TEST material):
* every world goes through the frozen `source._facts` and `source._world`, so it passes the frozen validator;
* words come only from the four TRAINING domains: each domain's setting, its kinds, its function template and
  its `declaration_labels` (labels that already occur inside a trained function text);
* packets are shaped exactly like `course.model_packet`: 0 supports, the course's cue for the kind.

THREE KINDS OF BANK.
* `MAIN`: 10 hand-made worlds of 4, 5 and 6 nodes. The focus is a bank member, as in the course.
* `FROZEN_TRAINING`: the frozen 64-world training bank (`source.freeze_bank(source.training_families())`, the
  course's own bank, `course.py:156-163`) with a new 5- or 6-node focus added OUTSIDE the bank, as in HSET
  (65 worlds, aliases W0..W64). It is rebuilt on load, never stored, and pinned by its bank digest.
* `REFUSE_SEVEN` and `REFUSE_DEGREE`: small banks that carry a 7-node world or a node of degree 5. Every packet
  there must be refused.

EXPECTED ANSWERS ARE COMPUTED WITHOUT THE CHECKER. `expected_values` come from the plain-graph code below
(brute-force isomorphism, the two reach rules re-implemented over node ranks). The torch-free test compares them
with checker v2's admissible answers, so a slip in either one fails the test.

    python -B larger_question_fixtures.py --write    # (re)write fixtures/larger_question_fixtures_v0_1.json
    python -B larger_question_fixtures.py --check    # rebuild in memory; exit 1 unless byte-identical
"""
from __future__ import annotations

import argparse
import ast
import collections
from copy import deepcopy
from hashlib import sha256
import itertools
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from cas_meta2.typed_teaching import answers, course, focal, source  # noqa: E402

SCHEMA = "claude.helm-larger-question-fixtures/0.1"
FIXTURE_PATH = HERE / "fixtures" / "larger_question_fixtures_v0_1.json"
TRAINING_DOMAINS = ("mechanical", "grammatical", "procedural", "container")
REACH_FIRST = "first_direct_constituent_lexical_v1"
REACH_BFS = "bfs_immediate_predecessor_lexical_v1"
# The frozen training bank's digest, measured from `source.freeze_bank(source.training_families())` on
# 2026-09-23 and checked on every load, so a changed corpus can never silently become a different bank. The same
# value appears in committed Helm records (for example `records/rpa_recorded_helm_20260922/selected_records.json`).
FROZEN_TRAINING_BANK_DIGEST = "0f563762a70e67513ca3e6996d988afd4421dd90fe63e1a04942a31a79e9c388"
PURPOSE = ("PUBLIC_INTEGRATION_FIXTURES_NOT_AN_EVALUATION_SET: read -> forward -> decode -> grade plumbing for "
           "5- and 6-node questions, plus refusal of 7-node and degree-5 questions. No claim about Helm.")

# ------------------------------------------------------------------------------------------------ shapes
# (node count, edges over structural node numbers). Node 0 is always the declared whole, a root; node 1 is
# always a child of node 0, so the function template's "whole" and "child" are both real.
SHAPES = {
    "S4": (4, ((0, 1), (0, 2), (2, 3))),
    "S5A": (5, ((0, 1), (0, 2), (1, 3), (3, 4))),              # chain of 3 steps under one branch
    "S5B": (5, ((0, 1), (0, 2), (1, 3), (2, 4))),              # SAME degree counts as S5A, different wiring
    "S5C": (5, ((0, 1), (0, 2), (3, 2), (3, 4))),              # two roots: node 4 is not reachable from node 0
    "S6A": (6, ((0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (4, 5))),   # diamond, then a chain
    "S6B": (6, ((0, 1), (0, 3), (1, 2), (2, 3), (3, 4), (4, 5))),   # SAME degree counts as S6A, different wiring
    "S6D": (6, ((0, 1), (0, 3), (1, 2), (4, 3), (4, 5))),          # two roots: node 5 is not reachable from node 0
    "S7": (7, ((0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 6))),   # refusal only: 7 nodes
    "S6STAR": (6, ((0, 1), (0, 2), (0, 3), (0, 4), (0, 5))),        # refusal only: out-degree 5
}
SAME_DEGREE_PAIRS = (("S5A", "S5B"), ("S6A", "S6B"))

# ------------------------------------------------------------------------------------------------ worlds
# label_offset: where this world's labels start in the domain's sorted `declaration_labels` (32 per domain).
# label_order[i]: which of those labels node i receives, so node rank is not simply node number.
WORLDS = {
    "W4_C": {"shape": "S4", "domain": "container", "label_offset": 0, "label_order": [2, 0, 3, 1],
             "kind_index": 0, "primary": [0, 1, 3]},
    "W5A_M": {"shape": "S5A", "domain": "mechanical", "label_offset": 0, "label_order": [3, 0, 4, 1, 2],
              "kind_index": 1, "primary": [0, 2, 4]},
    "W5A_G": {"shape": "S5A", "domain": "grammatical", "label_offset": 5, "label_order": [0, 4, 2, 3, 1],
              "kind_index": 2, "primary": [0, 1, 3]},
    "W5B_P": {"shape": "S5B", "domain": "procedural", "label_offset": 0, "label_order": [4, 1, 0, 3, 2],
              "kind_index": 3, "primary": [0, 1, 2]},
    "W5C_C": {"shape": "S5C", "domain": "container", "label_offset": 6, "label_order": [1, 3, 0, 4, 2],
              "kind_index": 4, "primary": [0, 3, 4]},
    "W6A_M": {"shape": "S6A", "domain": "mechanical", "label_offset": 8, "label_order": [2, 5, 0, 3, 1, 4],
              "kind_index": 5, "primary": [0, 1, 5]},
    "W6A_G": {"shape": "S6A", "domain": "grammatical", "label_offset": 12, "label_order": [5, 1, 3, 0, 4, 2],
              "kind_index": 6, "primary": [0, 2, 4]},
    "W6B_P": {"shape": "S6B", "domain": "procedural", "label_offset": 6, "label_order": [1, 4, 2, 5, 0, 3],
              "kind_index": 7, "primary": [0, 3, 5]},
    "W6B_P2": {"shape": "S6B", "domain": "procedural", "label_offset": 14, "label_order": [3, 0, 5, 2, 4, 1],
               "kind_index": 8, "primary": [0, 1, 4]},
    "W6D_C": {"shape": "S6D", "domain": "container", "label_offset": 12, "label_order": [0, 2, 5, 1, 3, 4],
              "kind_index": 9, "primary": [0, 4, 5]},
    "W7_M": {"shape": "S7", "domain": "mechanical", "label_offset": 16, "label_order": [6, 0, 3, 1, 5, 2, 4],
             "kind_index": 10, "primary": [0, 1, 2]},
    "W6STAR_C": {"shape": "S6STAR", "domain": "container", "label_offset": 20, "label_order": [0, 1, 2, 3, 4, 5],
                 "kind_index": 11, "primary": [0, 1, 2]},
}
BANKS = {
    "MAIN": ("W4_C", "W5A_M", "W5A_G", "W5B_P", "W5C_C", "W6A_M", "W6A_G", "W6B_P", "W6B_P2", "W6D_C"),
    "REFUSE_SEVEN": ("W7_M", "W5A_M"),
    "REFUSE_DEGREE": ("W6STAR_C", "W6A_M"),
}
CUES = {"role_set": None, "definition": "CUBE_FACE_1", "context": "CUBE_FACE_2", "analogy": "CUBE_FACE_3",
        "correspondence": "CUBE_FACE_4", "parts": None, "edge_account": "CUBE_FACE_6"}
# id, bank, focus world, kind, rule, arguments (node numbers / world key), note.
# For `role_set` the arguments are the focal clauses: [[template, comparison world key or None], ...].
FIXTURES = (
    ("F01", "MAIN", "W5A_M", "role_set", None, {"clauses": [[3, "W5A_G"]]}, "5 nodes; one analogy clause"),
    ("F02", "MAIN", "W5A_M", "definition", None, {}, "5 nodes"),
    ("F03", "MAIN", "W5A_M", "context", None, {}, "5 nodes"),
    ("F04", "MAIN", "W5A_M", "analogy", None, {}, "5 nodes; genuine match W5A_G, same-degree decoy W5B_P in bank"),
    ("F05", "MAIN", "W5B_P", "analogy", None, {}, "5 nodes; GENUINE NO_MATCH: only same-degree decoys exist"),
    ("F06", "MAIN", "W5A_M", "correspondence", None, {"target": "W5A_G"}, "5 nodes; MAPPING"),
    ("F07", "MAIN", "W5A_M", "correspondence", None, {"target": "W5B_P"},
     "5 nodes; GENUINE NO_MATCH against a same-degree different-wiring world; 121 candidates"),
    ("F08", "MAIN", "W5A_M", "parts", None, {"whole": 0}, "5 nodes"),
    ("F09", "MAIN", "W5A_M", "edge_account", None, {}, "5 nodes"),
    ("F10", "MAIN", "W5A_M", "reach", REACH_FIRST, {"whole": 0, "part": 4}, "5 nodes; VIA, part 3 steps away"),
    ("F11", "MAIN", "W5A_M", "reach", REACH_BFS, {"whole": 0, "part": 4}, "5 nodes; VIA, the two rules differ"),
    ("F12", "MAIN", "W5C_C", "reach", REACH_FIRST, {"whole": 0, "part": 4},
     "5 nodes; GENUINE NO-PATH: the part exists under another root"),
    ("F13", "MAIN", "W5A_M", "reach", REACH_BFS, {"whole": 0, "part": 1}, "5 nodes; DIRECT"),
    ("F14", "MAIN", "W6A_M", "role_set", None, {"clauses": [[1, None], [6, None]]},
     "6 nodes; definition and account clauses"),
    ("F15", "MAIN", "W6A_M", "definition", None, {}, "6 nodes"),
    ("F16", "MAIN", "W6A_M", "context", None, {}, "6 nodes"),
    ("F17", "MAIN", "W6A_M", "analogy", None, {}, "6 nodes; genuine match W6A_G, same-degree decoys in bank"),
    ("F18", "MAIN", "W6B_P", "analogy", None, {},
     "6 nodes; GENUINE NO_MATCH: the only isomorphic world W6B_P2 shares the domain; decoys share degrees"),
    ("F19", "MAIN", "W6A_M", "correspondence", None, {"target": "W6A_G"}, "6 nodes; MAPPING, 2 valid maps"),
    ("F20", "MAIN", "W6A_M", "correspondence", None, {"target": "W6B_P"},
     "6 nodes; GENUINE NO_MATCH against a same-degree different-wiring world; 721 candidates"),
    ("F21", "MAIN", "W6A_M", "parts", None, {"whole": 0}, "6 nodes"),
    ("F22", "MAIN", "W6A_M", "edge_account", None, {}, "6 nodes"),
    ("F23", "MAIN", "W6A_M", "reach", REACH_FIRST, {"whole": 0, "part": 5},
     "6 nodes; VIA; which child is named depends on node rank (a tie by structure)"),
    ("F24", "MAIN", "W6A_M", "reach", REACH_BFS, {"whole": 0, "part": 5}, "6 nodes; VIA, 4 steps"),
    ("F25", "MAIN", "W6D_C", "reach", REACH_BFS, {"whole": 0, "part": 5},
     "6 nodes; GENUINE NO-PATH: the part exists under another root"),
    ("F26", "MAIN", "W6B_P", "reach", REACH_FIRST, {"whole": 0, "part": 3}, "6 nodes; DIRECT"),
    ("F27", "MAIN", "W6B_P", "correspondence", None, {"target": "W6B_P2"}, "6 nodes; MAPPING within one domain"),
    ("F28", "MAIN", "W4_C", "parts", None, {"whole": 0},
     "4-node focus in a bank with 5- and 6-node worlds: takes the LARGER route"),
    ("F29", "MAIN", "W5A_M", "correspondence", None, {"target": "W6A_M"},
     "5 to 6 nodes: forced NO_MATCH, 1 candidate"),
    ("F30", "MAIN", "W4_C", "correspondence", None, {"target": "W5A_M"},
     "4 to 5 nodes: forced NO_MATCH; the frozen compiler refuses it"),
    ("F31", "MAIN", "W6D_C", "reach", REACH_FIRST, {"whole": 0, "part": 2}, "6 nodes; VIA, 2 steps, one route"),
    ("H01", "FROZEN_TRAINING", "W6A_M", "definition", None, {}, "65 worlds: aliases W0..W64"),
    ("H02", "FROZEN_TRAINING", "W6A_M", "analogy", None, {},
     "65 worlds; NO_MATCH by size only (every bank world has at most 4 nodes)"),
    ("H03", "FROZEN_TRAINING", "W6A_M", "reach", REACH_BFS, {"whole": 0, "part": 5}, "65 worlds; VIA"),
    ("H04", "FROZEN_TRAINING", "W6A_M", "correspondence", None, {"target": "TRAINING_FIRST"},
     "65 worlds; forced NO_MATCH to a 4-node training world"),
    ("H05", "FROZEN_TRAINING", "W5A_M", "context", None, {}, "65 worlds; 5 nodes"),
    ("H06", "FROZEN_TRAINING", "W5C_C", "parts", None, {"whole": 3}, "65 worlds; parts of the second root"),
    ("R01", "REFUSE_SEVEN", "W7_M", "parts", None, {"whole": 0}, "REFUSE: 7-node focus"),
    ("R02", "REFUSE_SEVEN", "W5A_M", "analogy", None, {}, "REFUSE: 5-node focus, 7-node world in the bank"),
    ("R03", "REFUSE_DEGREE", "W6STAR_C", "parts", None, {"whole": 0}, "REFUSE: a node with out-degree 5"),
    ("R04", "REFUSE_DEGREE", "W6A_M", "definition", None, {}, "REFUSE: degree-5 world in the bank"),
)
EXPECTED_REFUSALS = {"R01": "WORLD_ABOVE_SIX_NODES", "R02": "WORLD_ABOVE_SIX_NODES",
                     "R03": "DEGREE_ABOVE_READER_EXACT_RANGE", "R04": "DEGREE_ABOVE_READER_EXACT_RANGE"}
ROLE_OF_TEMPLATE = {1: [1], 2: [2], 3: [3], 4: [4], 5: [5], 6: [5, 6]}


# ------------------------------------------------------------------------------------------------ vocabulary
def vocabulary():
    """Per training domain: its setting, sorted kinds, sorted declaration labels and function template."""
    families = source.training_families()
    constants = {}
    for node in ast.parse(source.CORPUS_PATH.read_bytes(), str(source.CORPUS_PATH)).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            constants[node.targets[0].id] = node.value
    table = constants["_FUNCTION"]
    templates = {ast.literal_eval(key): ast.literal_eval(value) for key, value in zip(table.keys, table.values)
                 if ast.literal_eval(key) in TRAINING_DOMAINS}
    result = {}
    for domain in TRAINING_DOMAINS:
        rows = [family for family in families if family["domain"] == domain]
        settings = sorted({family["setting"] for family in rows})
        if len(rows) != 16 or len(settings) != 1:
            raise ValueError("FIXTURE_VOCABULARY:" + domain)
        for family in rows:
            if templates[domain] % {"whole": family["labels"][0], "child": family["labels"][1]} != family["function"]:
                raise ValueError("FIXTURE_FUNCTION_TEMPLATE:" + family["family_id"])
        result[domain] = {"setting": settings[0], "kinds": sorted({family["kind"] for family in rows}),
                          "declaration_labels": sorted({family["labels"][i] for family in rows for i in (0, 1)}),
                          "function_template": templates[domain]}
    return result, families


# ------------------------------------------------------------------------------------------------ plain graphs
def degree_multiset(n, edges):
    in_degree, out_degree = [0] * n, [0] * n
    for a, b in edges:
        out_degree[a] += 1
        in_degree[b] += 1
    return sorted([list(pair) for pair in zip(in_degree, out_degree)])


def isomorphisms(left, right):
    """Every node map (tuple, left node -> right node) that carries left's edge set onto right's exactly."""
    (n, edges), (m, other) = left, right
    if n != m or len(edges) != len(other):
        return []
    target = set(other)
    return [order for order in itertools.permutations(range(m))
            if {(order[a], order[b]) for a, b in edges} == target]


def canonical_form(n, edges):
    """The lexicographically smallest sorted edge list over all n! relabellings. Two shapes are isomorphic
    exactly when their canonical forms are equal. Brute force; fine up to 7 nodes."""
    best = min(tuple(sorted((order[a], order[b]) for a, b in edges)) for order in itertools.permutations(range(n)))
    return [n, [list(edge) for edge in best]]


def colour_refinement_distinguishes(left, right):
    """Directed colour refinement (1-WL) on the disjoint union, starting from (in-degree, out-degree).

    True when the final colour counts differ. Helm's rounds pass messages along parents and children, so this
    is a NECESSARY condition for Helm to tell the two apart from structure alone; it is not sufficient.
    """
    nodes = [("L", v) for v in range(left[0])] + [("R", v) for v in range(right[0])]
    parents, children = collections.defaultdict(list), collections.defaultdict(list)
    for side, (_, edges) in (("L", left), ("R", right)):
        for a, b in edges:
            children[(side, a)].append((side, b))
            parents[(side, b)].append((side, a))
    colour = {v: (len(parents[v]), len(children[v])) for v in nodes}
    for _ in range(len(nodes)):
        signature = {v: (colour[v], tuple(sorted(colour[p] for p in parents[v])),
                         tuple(sorted(colour[c] for c in children[v]))) for v in nodes}
        palette = {sig: index for index, sig in enumerate(sorted(set(signature.values())))}
        refined = {v: palette[signature[v]] for v in nodes}
        if len(set(refined.values())) == len(set(colour.values())):
            colour = refined
            break
        colour = refined
    count = lambda side: sorted(collections.Counter(colour[v] for v in nodes if v[0] == side).items())
    return count("L") != count("R")


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
    """The two frozen reach rules over node numbers; `rank[v]` is node v's sorted-reference position."""
    adjacency = {v: sorted((b for a, b in edges if a == v), key=lambda c: rank[c]) for v in range(n)}
    if part in adjacency[whole]:
        return ("DIRECT", None)
    if rule == REACH_FIRST:
        for first in adjacency[whole]:
            if _bfs_path(adjacency, first, part) is not None:
                return ("VIA", first)
        return ("ABSENT", None)
    path = _bfs_path(adjacency, whole, part)
    return ("ABSENT", None) if path is None else ("VIA", path[-2])


def reach_rank_dependent(n, edges, whole, part, rule):
    answers_seen = {reach_gold(n, edges, whole, part, dict(enumerate(order)), rule)
                    for order in itertools.permutations(range(n))}
    return len(answers_seen) > 1


# ------------------------------------------------------------------------------------------------ construction
def _world(spec, vocab):
    n, edges = SHAPES[spec["shape"]]
    words = vocab[spec["domain"]]
    pool = words["declaration_labels"][spec["label_offset"]:spec["label_offset"] + n]
    if len(pool) != n or sorted(spec["label_order"]) != list(range(n)):
        raise ValueError("FIXTURE_LABELS")
    labels = [pool[index] for index in spec["label_order"]]
    declarations = {"domain": spec["domain"], "kind": words["kinds"][spec["kind_index"] % len(words["kinds"])],
                    "setting": words["setting"],
                    "function": words["function_template"] % {"whole": labels[0], "child": labels[1]}}
    edge_rows = sorted(({"source": labels[a], "target": labels[b]} for a, b in edges),
                       key=lambda row: (row["source"], row["target"]))
    world = source._world(source._facts(labels, edge_rows, declarations, [labels[i] for i in spec["primary"]]))
    order = sorted(labels)
    refs = [world["world_id"] + "/n%d" % order.index(label) for label in labels]
    rank = {i: order.index(label) for i, label in enumerate(labels)}
    return world, {"labels": labels, "refs": refs, "rank": rank, "n": n, "edges": edges}


def _bank(worlds):
    ordered = sorted(worlds, key=lambda world: world["world_id"])
    return source.validate_bank({"schema": source.BANK_SCHEMA, "worlds": ordered,
                                 "bank": source._bank_record(ordered)})


def frozen_training_bank():
    bank = source.freeze_bank(source.training_families())
    if bank["bank"]["bank_digest"] != FROZEN_TRAINING_BANK_DIGEST:
        raise ValueError("FIXTURE_FROZEN_TRAINING_BANK_DIGEST:" + bank["bank"]["bank_digest"])
    return bank


def _public(bank, focus_world, extra_worlds):
    worlds = {world["world_id"]: world for world in bank["worlds"]}
    for world in extra_worlds:
        if world["world_id"] in worlds:
            raise ValueError("FIXTURE_EXTRA_WORLD_IN_BANK")
        worlds[world["world_id"]] = world
    return {"focus_world_id": focus_world["world_id"], "worlds": [worlds[key] for key in sorted(worlds)],
            "bank": deepcopy(bank["bank"])}


def _packet(public, kind, rule, arguments, cue):
    query = answers.compile_query(public, kind=kind, rule=rule, arguments=arguments or None,
                                  focus_world_id=public["focus_world_id"])
    body = {"schema": course.PACKET_SCHEMA, "source_digest": source.public_digest(public),
            "source_world_id": public["focus_world_id"], "query": query, "cue": cue,
            "instruction": course.REQUESTS[kind], "role_catalog": deepcopy(course.ROLE_CATALOG), "supports": []}
    packet = {"source": public, "record": {"record_id": "typed-input-" + source.digest(body), **body}}
    return course.validate_model_packet(packet)


def packet_sha256(packet):
    return sha256(source.canonical(packet).encode()).hexdigest()


def _expected(fixture_id, kind, rule, focus_key, arguments, worlds, facts, bank_keys, public):
    """Answer VALUES computed from plain graphs only (no checker), plus design facts."""
    focus, info = worlds[focus_key], facts[focus_key]
    world_id = focus["world_id"]
    design = {}
    if kind == "definition":
        values = [{"whole": info["refs"][0], "kind_ref": answers.declaration_ref(world_id, "kind"),
                   "function_ref": answers.declaration_ref(world_id, "function")}]
    elif kind == "context":
        values = [{"setting_ref": answers.declaration_ref(world_id, "setting"),
                   "participants": sorted(info["refs"][i] for i in WORLDS[focus_key]["primary"])}]
    elif kind == "role_set":
        roles = sorted({role for template, _ in arguments["clauses"] for role in ROLE_OF_TEMPLATE[template]})
        values = [{"roles": roles, "status": "UNIQUE" if len(roles) == 1 else "AMBIGUOUS"}]
    elif kind == "parts":
        whole = arguments["whole"]
        values = [{"nodes": sorted(info["refs"][b] for a, b in info["edges"] if a == whole)}]
    elif kind == "edge_account":
        values = [{"edges": [{"source": a, "target": b}
                             for a, b in sorted((info["refs"][a], info["refs"][b]) for a, b in info["edges"])]}]
    elif kind == "reach":
        state, via = reach_gold(info["n"], info["edges"], arguments["whole"], arguments["part"], info["rank"], rule)
        values = [{"state": state, "via": None if via is None else info["refs"][via]}]
        design["rank_dependent"] = reach_rank_dependent(info["n"], info["edges"], arguments["whole"],
                                                         arguments["part"], rule)
    elif kind == "analogy":
        matches = sorted(worlds[key]["world_id"] for key in bank_keys
                         if facts[key]["domain"] != info["domain"]
                         and isomorphisms((info["n"], info["edges"]), (facts[key]["n"], facts[key]["edges"])))
        values = [{"world_id": value} for value in matches] or [{"world_id": None}]
        design["same_degree_decoys_in_bank"] = sorted(
            worlds[key]["world_id"] for key in bank_keys if key != focus_key
            and facts[key]["n"] == info["n"]
            and degree_multiset(facts[key]["n"], facts[key]["edges"]) == degree_multiset(info["n"], info["edges"])
            and not isomorphisms((info["n"], info["edges"]), (facts[key]["n"], facts[key]["edges"])))
    elif kind == "correspondence":
        target_key = arguments["target"]
        other = facts[target_key]
        maps = isomorphisms((info["n"], info["edges"]), (other["n"], other["edges"]))
        if maps:
            values = [{"status": "MAPPING", "pairs": sorted(({"source": info["refs"][i], "target": other["refs"][m[i]]}
                                                             for i in range(info["n"])), key=lambda p: p["source"])}
                      for m in maps]
        else:
            values = [{"status": "NO_MATCH", "pairs": []}]
        design["syntactic_candidates"] = 1 + (math.factorial(other["n"]) if other["n"] == info["n"] else 0)
        design["same_degree_counts"] = (other["n"] == info["n"] and degree_multiset(info["n"], info["edges"])
                                        == degree_multiset(other["n"], other["edges"]))
    else:
        raise ValueError("FIXTURE_KIND:" + kind)
    values = sorted(values, key=lambda value: source.canonical(value))
    return values, design


def build():
    """The whole fixture document, deterministically. Imports no checker."""
    vocab, _families = vocabulary()
    worlds, facts = {}, {}
    for key in sorted(WORLDS):
        worlds[key], facts[key] = _world(WORLDS[key], vocab)
        facts[key]["domain"] = WORLDS[key]["domain"]
    training = frozen_training_bank()
    training_keys = []
    for world in training["worlds"]:
        key = "TRAINING:" + world["world_id"]
        worlds[key] = world
        index = {node["ref"]: position for position, node in enumerate(sorted(world["nodes"], key=lambda n: n["ref"]))}
        refs = sorted(index)
        edges = tuple((index[edge["source"]], index[edge["target"]]) for edge in world["contains"])
        facts[key] = {"n": len(refs), "edges": edges, "refs": refs, "rank": {i: i for i in range(len(refs))},
                      "domain": world["declarations"]["domain"]}
        training_keys.append(key)
    banks = {name: _bank([worlds[key] for key in keys]) for name, keys in BANKS.items()}
    documents, packets = [], {}
    for fixture_id, bank_name, focus_key, kind, rule, arguments, note in FIXTURES:
        if bank_name == "FROZEN_TRAINING":
            bank, extra, bank_keys = training, [worlds[focus_key]], training_keys
        else:
            bank, extra, bank_keys = banks[bank_name], [], list(BANKS[bank_name])
        public = _public(bank, worlds[focus_key], extra)
        refs = facts[focus_key]["refs"]
        query_arguments = {}
        if kind == "role_set":
            clauses = []
            for template, comparison in arguments["clauses"]:
                clauses.append(focal.render_excerpt(public, template=template, focus_world_id=public["focus_world_id"],
                                                    comparison_world_id=None if comparison is None
                                                    else worlds[comparison]["world_id"]))
            query_arguments["focal_excerpt"] = "\n".join(clauses)
        for field in ("whole", "part"):
            if field in arguments:
                query_arguments[field] = refs[arguments[field]]
        if kind == "correspondence":
            target_key = training_keys[0] if arguments["target"] == "TRAINING_FIRST" else arguments["target"]
            arguments = {**arguments, "target": target_key}
            query_arguments["target_world_id"] = worlds[target_key]["world_id"]
        cue = CUES.get(kind) if kind != "reach" else (None if rule == REACH_FIRST else "CUBE_FACE_5")
        packet = _packet(public, kind, rule, query_arguments, cue)
        row = {"fixture_id": fixture_id, "bank": bank_name, "focus": focus_key,
               "focus_world_id": public["focus_world_id"],
               "extra_world_keys": [focus_key] if extra else [], "kind": kind,
               "rule": packet["record"]["query"]["rule"], "note": note, "record": packet["record"],
               "packet_sha256": packet_sha256(packet),
               "max_nodes_in_source": max(len(world["nodes"]) for world in public["worlds"]),
               "world_count_in_source": len(public["worlds"])}
        if fixture_id in EXPECTED_REFUSALS:
            row["expected_refusal"] = EXPECTED_REFUSALS[fixture_id]
        else:
            values, design = _expected(fixture_id, kind, packet["record"]["query"]["rule"], focus_key, arguments,
                                       worlds, facts, bank_keys, public)
            row["expected_values"] = values
            row["design_facts"] = design
        documents.append(row)
        packets[fixture_id] = packet
    shape_rows = {}
    for name, (n, edges) in sorted(SHAPES.items()):
        shape_rows[name] = {"nodes": n, "edges": [list(edge) for edge in edges],
                            "degree_multiset": degree_multiset(n, edges),
                            "max_degree": max(max(row) for row in degree_multiset(n, edges)),
                            "automorphisms": len(isomorphisms((n, edges), (n, edges))),
                            "canonical_form": canonical_form(n, edges)}
    pairs = []
    for left, right in SAME_DEGREE_PAIRS:
        a, b = SHAPES[left], SHAPES[right]
        pairs.append({"left": left, "right": right,
                      "degree_multisets_equal": degree_multiset(*a) == degree_multiset(*b),
                      "isomorphic": bool(isomorphisms(a, b)),
                      "colour_refinement_distinguishes": colour_refinement_distinguishes(a, b)})
    world_rows = {key: {"world_id": worlds[key]["world_id"], **deepcopy(WORLDS[key]),
                        "labels_by_node": facts[key]["labels"], "refs_by_node": facts[key]["refs"]}
                  for key in sorted(WORLDS)}
    body = {"schema": SCHEMA, "purpose": PURPOSE,
            "construction": ("Public HSET construction (hset_worlds.world_from_spec / build_packet), training-domain "
                             "words only, 0 supports; no salt, no TEST material, no model."),
            "banks": {name: banks[name] for name in sorted(banks)},
            "frozen_training_bank": {"rebuilt_on_load_by": "source.freeze_bank(source.training_families())",
                                     "bank_digest": training["bank"]["bank_digest"],
                                     "world_count": len(training["worlds"])},
            "worlds": world_rows, "shapes": shape_rows, "same_degree_pairs": pairs, "fixtures": documents}
    return {**body, "fixture_set_digest": source.digest(body)}, packets


def render(document):
    return (json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode()


def load(path=FIXTURE_PATH):
    """`(document, {fixture_id: packet})`, with every packet's identity re-checked against its sha256."""
    raw = Path(path).read_bytes()
    document = json.loads(raw)
    if document.get("schema") != SCHEMA:
        raise ValueError("FIXTURE_SCHEMA")
    body = {key: value for key, value in document.items() if key != "fixture_set_digest"}
    if source.digest(body) != document["fixture_set_digest"]:
        raise ValueError("FIXTURE_SET_DIGEST")
    training = frozen_training_bank()
    by_id = {}
    for bank in document["banks"].values():
        source.validate_bank(bank)
        for world in bank["worlds"]:
            by_id[world["world_id"]] = world
    packets = {}
    for row in document["fixtures"]:
        if row["bank"] == "FROZEN_TRAINING":
            bank = training
            extra = [by_id[document["worlds"][key]["world_id"]] for key in row["extra_world_keys"]]
        else:
            bank, extra = document["banks"][row["bank"]], []
        public = _public(bank, by_id[row["focus_world_id"]], extra)
        packet = course.validate_model_packet({"source": public, "record": deepcopy(row["record"])})
        if packet_sha256(packet) != row["packet_sha256"]:
            raise ValueError("FIXTURE_PACKET_IDENTITY:" + row["fixture_id"])
        packets[row["fixture_id"]] = packet
    return document, packets


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document, _ = build()
    raw = render(document)
    if args.write:
        FIXTURE_PATH.parent.mkdir(exist_ok=True)
        FIXTURE_PATH.write_bytes(raw)
        print("WROTE", FIXTURE_PATH.name, len(raw), sha256(raw).hexdigest(), document["fixture_set_digest"])
        return 0
    same = FIXTURE_PATH.is_file() and FIXTURE_PATH.read_bytes() == raw
    print("FIXTURES_REPRODUCE" if same else "FIXTURES_DIFFER", sha256(raw).hexdigest())
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
