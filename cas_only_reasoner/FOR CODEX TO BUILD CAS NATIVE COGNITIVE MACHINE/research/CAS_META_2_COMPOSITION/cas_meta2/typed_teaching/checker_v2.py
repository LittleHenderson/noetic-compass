"""Stage 2 private bounded semantics over validated typed-teaching public facts.

Additive version of checker.py: only the profile schema and graph bound change.
Historical checker.py remains the original entry point.

Inference builders must not call this module. It accepts no legacy family,
archetype, teacher target or model. A receipt establishes a deterministic answer
under supplied declarations, not authenticated source custody or world truth.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from hashlib import sha256
from itertools import permutations
import json

from . import answers, focal, source

TARGET_SCHEMA = "cas.typed-teaching-private-target/0.1"
CHECK_SCHEMA = "cas.typed-teaching-private-check/0.1"
PROFILE_SCHEMA = "cas.typed-teaching-semantic-profile/0.2"
MAX_ISOMORPHISM_NODES = 6
MAX_ADMISSIBLE_ANSWERS = 64
MAX_TARGET_BYTES = 512 * 1024
BOUNDARY = (
    "Private deterministic semantics of supplied public declarations; no source "
    "authentication, outside-world truth, learner inference or learning claim."
)


class SemanticCheckError(ValueError):
    """Malformed binding or unsupported checker scope; never a guessed target."""


def _require(condition, reason):
    if not condition:
        raise SemanticCheckError(reason)


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise SemanticCheckError("TYPED_CHECKER_JSON") from exc


def _digest(value):
    return sha256(_canonical(value)).hexdigest()


def checker_profile():
    """Versioned rule declaration, not an attestation of loaded code bytes."""
    body = {
        "schema": PROFILE_SCHEMA,
        "rules": {kind: list(rules) for kind, rules in answers.RULES.items()},
        "role_semantics": "EXACT_CONTROLLED_FOCAL_CLAUSES_NOT_FREE_LANGUAGE",
        "focal_grammar": focal.grammar_profile(),
        "declaration_references": "FOCUS_WORLD_DECLARATION_IDENTITY",
        "graph_matching": "UNROOTED_EXACT_DIRECTED_GRAPH_BIJECTION",
        "analogy_domain_rule": "DISTINCT_DECLARED_DOMAIN_STRINGS",
        "tie_rule": "ALL_VALID_ANSWERS_RETAINED_CANONICAL_BYTE_ORDER",
        "graph_order": "SORTED_SCOPED_NODE_REFERENCES",
        "process_order": "NOT_INFERRED_FROM_CONTAINS_OR_SERIALIZATION",
        "max_isomorphism_nodes": MAX_ISOMORPHISM_NODES,
        "max_bank_worlds": source.MAX_BANK_WORLDS,
        "max_admissible_answers": MAX_ADMISSIBLE_ANSWERS,
        "max_target_bytes": MAX_TARGET_BYTES,
        "identity_evidence": "VERSIONED_RULE_PROFILE_NOT_CODE_AUTHENTICATION",
    }
    return {**body, "profile_digest": _digest(body)}


def _nodes(world):
    return sorted(node["ref"] for node in world["nodes"])


def _edges(world):
    return frozenset((edge["source"], edge["target"]) for edge in world["contains"])


def _edge_rows(edges):
    return [{"source": a, "target": b} for a, b in sorted(edges)]


def _adjacency(world):
    result = {node: [] for node in _nodes(world)}
    for left, right in sorted(_edges(world)):
        result[left].append(right)
    return result


def _bounded_graphs(worlds):
    _require(all(len(world["nodes"]) <= MAX_ISOMORPHISM_NODES for world in worlds),
             "TYPED_CHECKER_ISOMORPHISM_BOUND")


def _isomorphisms(left, right):
    """Enumerate every mapping; node labels, root choice and archetypes do not vote."""
    _bounded_graphs((left, right))
    lhs, rhs = _nodes(left), _nodes(right)
    ledges, redges = _edges(left), _edges(right)
    if len(lhs) != len(rhs):
        return [], {"reason": "NODE_COUNT_MISMATCH", "permutations_checked": 0}
    if len(ledges) != len(redges):
        return [], {"reason": "EDGE_COUNT_MISMATCH", "permutations_checked": 0}
    matches, checked = [], 0
    for order in permutations(rhs):
        checked += 1
        mapping = dict(zip(lhs, order))
        if frozenset((mapping[a], mapping[b]) for a, b in ledges) == redges:
            matches.append([{"source": a, "target": mapping[a]} for a in lhs])
    return matches, {"reason": "MATCHES" if matches else "NO_EDGE_PRESERVING_BIJECTION",
                     "permutations_checked": checked}


def _bfs(adjacency, start, goal):
    """First shortest path under sorted-reference neighbour order, plus closure."""
    queue, seen = deque([[start]]), {start}
    while queue:
        path = queue.popleft()
        if path[-1] == goal:
            return path, sorted(seen)
        for child in adjacency[path[-1]]:
            if child not in seen:
                seen.add(child)
                queue.append(path + [child])
    return None, sorted(seen)


def _reach(world, query):
    whole, part = query["arguments"]["whole"], query["arguments"]["part"]
    adjacency = _adjacency(world)
    if part in adjacency[whole]:
        return {"state": "DIRECT", "via": None}, {
            "path": [whole, part], "selection": "DIRECT_EDGE_TAKES_PRECEDENCE"}
    if query["rule"] == "first_direct_constituent_lexical_v1":
        for first in adjacency[whole]:
            suffix, _ = _bfs(adjacency, first, part)
            if suffix is not None:
                return {"state": "VIA", "via": first}, {
                    "path": [whole] + suffix,
                    "selection": "LEXICAL_FIRST_DIRECT_CONSTITUENT_WITH_A_PATH"}
        _, visited = _bfs(adjacency, whole, part)
    else:
        _require(query["rule"] == "bfs_immediate_predecessor_lexical_v1",
                 "TYPED_CHECKER_REACH_RULE")
        path, visited = _bfs(adjacency, whole, part)
        if path is not None:
            return {"state": "VIA", "via": path[-2]}, {
                "path": path, "selection": "LEXICAL_BFS_FIRST_PATH_IMMEDIATE_PREDECESSOR"}
    return {"state": "ABSENT", "via": None}, {
        "reachable_nodes_including_start": visited,
        "inventory_scope": world["inventory_scope"],
        "selection": "NO_PATH_IN_COMPLETE_SUPPLIED_SNAPSHOT"}


def _derive_values(public, query):
    worlds = {world["world_id"]: world for world in public["worlds"]}
    focus = worlds[query["focus_world_id"]]
    kind = query["kind"]
    values, witnesses, coverage = [], [], {}
    if kind == "role_set":
        derived = focal.derive_roles(public, query)
        values.append({"roles": derived["roles"], "status": derived["status"]})
        witnesses.append({"focal_clauses": derived["witnesses"],
                          "role_rule": "ALL_AND_ONLY_SOURCE_GROUNDED_FOCAL_ROLES"})
        coverage = {"clauses_checked": len(derived["witnesses"]),
                    "focal_grammar_schema": focal.GRAMMAR_SCHEMA,
                    "background_and_worked_supports_are_focal": False}
    elif kind == "definition":
        value = {"whole": focus["declared_whole"],
                 "kind_ref": answers.declaration_ref(focus["world_id"], "kind"),
                 "function_ref": answers.declaration_ref(focus["world_id"], "function")}
        values.append(value)
        witnesses.append({"whole": value["whole"],
                          "kind": focus["declarations"]["kind"],
                          "function": focus["declarations"]["function"],
                          "reference_rule": "FOCUS_WORLD_DECLARATION_IDENTITY"})
    elif kind == "context":
        values.append({"setting_ref": answers.declaration_ref(focus["world_id"], "setting"),
                       "participants": sorted(focus["declarations"]["participants"])})
        witnesses.append({"setting": focus["declarations"]["setting"],
                          "participants_basis": focus["declarations"]["participants_basis"],
                          "reference_rule": "FOCUS_WORLD_DECLARATION_IDENTITY"})
    elif kind == "parts":
        whole = query["arguments"]["whole"]
        edges = [(a, b) for a, b in _edges(focus) if a == whole]
        values.append({"nodes": sorted(b for _, b in edges)})
        witnesses.append({"whole": whole, "direct_edges": _edge_rows(edges),
                          "inventory_scope": focus["inventory_scope"]})
    elif kind == "edge_account":
        value = {"edges": _edge_rows(_edges(focus))}
        values.append(value)
        witnesses.append({"declared_edge_count": len(value["edges"]),
                          "order": "LEXICAL_REFERENCE_PAIR_SERIALIZATION_NOT_PROCESS",
                          "inventory_scope": focus["inventory_scope"]})
    elif kind == "reach":
        value, witness = _reach(focus, query)
        values.append(value)
        witnesses.append(witness)
    elif kind == "correspondence":
        other = worlds[query["arguments"]["target_world_id"]]
        matches, audit = _isomorphisms(focus, other)
        coverage = {"source_world_id": focus["world_id"], "target_world_id": other["world_id"],
                    "matching_bijections": len(matches), **audit}
        if matches:
            for pairs in matches:
                values.append({"status": "MAPPING", "pairs": pairs})
                witnesses.append({"mapping": pairs,
                                  "mapped_source_edges_equal_all_target_edges": True})
        else:
            values.append({"status": "NO_MATCH", "pairs": []})
            witnesses.append({"exhaustive_bounded_comparison": deepcopy(coverage)})
    elif kind == "analogy":
        bank = [worlds[key] for key in public["bank"]["world_ids"]]
        # Check the entire requested oracle scope before rejecting any candidate.
        # Unsupported graphs cannot quietly become NO_MATCH, even in one domain.
        _bounded_graphs([focus] + bank)
        decisions = []
        for other in bank:
            row = {"world_id": other["world_id"]}
            if other["declarations"]["domain"] == focus["declarations"]["domain"]:
                decisions.append({**row, "reason": "SAME_DECLARED_DOMAIN",
                                  "permutations_checked": 0, "matching_bijections": 0})
                continue
            matches, audit = _isomorphisms(focus, other)
            decisions.append({**row, **audit, "matching_bijections": len(matches)})
            if matches:
                values.append({"world_id": other["world_id"]})
                witnesses.append({"source_domain": focus["declarations"]["domain"],
                                  "target_domain": other["declarations"]["domain"],
                                  "mapping": matches[0], "matching_bijections": len(matches),
                                  "mapped_source_edges_equal_all_target_edges": True})
        coverage = {"bank_digest": public["bank"]["bank_digest"],
                    "worlds_checked": len(bank), "decisions": decisions}
        if not values:
            values.append({"world_id": None})
            witnesses.append({"exhaustive_bounded_bank_comparison": True})
    else:
        raise SemanticCheckError("TYPED_CHECKER_KIND_UNSUPPORTED")
    return values, witnesses, coverage


def derive_target(public, query):
    """Derive a private complete admissible set from a copied public snapshot."""
    snapshot = source.validate_public(public)
    request = answers.validate_query(snapshot, query)
    values, witnesses, coverage = _derive_values(snapshot, request)
    _require(0 < len(values) <= MAX_ADMISSIBLE_ANSWERS and len(values) == len(witnesses),
             "TYPED_CHECKER_TARGET_SET_BOUND")
    rows = []
    for value, witness in zip(values, witnesses):
        answer = answers.make_answer(snapshot, request, value)
        rows.append((answer, {"answer_digest": _digest(answer), "evidence": witness}))
    rows.sort(key=lambda row: _canonical(row[0]))
    _require(len({_canonical(row[0]) for row in rows}) == len(rows),
             "TYPED_CHECKER_DUPLICATE_TARGET")
    profile = checker_profile()
    body = {"schema": TARGET_SCHEMA, "query_id": request["query_id"],
            "source_digest": request["source_digest"], "kind": request["kind"],
            "rule": request["rule"], "checker_profile": profile,
            "checker_profile_digest": profile["profile_digest"],
            "admissible_answers": [row[0] for row in rows],
            "witnesses": [row[1] for row in rows], "coverage": coverage,
            "boundary": BOUNDARY}
    _require(len(_canonical(body)) <= MAX_TARGET_BYTES, "TYPED_CHECKER_TARGET_BYTES")
    result = {**body, "target_digest": _digest(body)}
    _require(len(_canonical(result)) <= MAX_TARGET_BYTES, "TYPED_CHECKER_TARGET_BYTES")
    return deepcopy(result)


def validate_target(public, query, target):
    """Independently rederive; a resealed private assertion is not evidence."""
    _require(type(target) is dict and len(_canonical(target)) <= MAX_TARGET_BYTES,
             "TYPED_CHECKER_TARGET_SHAPE")
    expected = derive_target(public, query)
    _require(set(target) == set(expected) and _canonical(target) == _canonical(expected),
             "TYPED_CHECKER_TARGET_BINDING")
    return deepcopy(expected)


def check_answer(public, query, answer):
    """Validate predicted syntax before any semantic work; do not trust targets."""
    snapshot = source.validate_public(public)
    request = answers.validate_query(snapshot, query)
    prediction = answers.validate_answer(snapshot, request, answer)
    target = derive_target(snapshot, request)
    matched = [w for a, w in zip(target["admissible_answers"], target["witnesses"])
               if _canonical(a) == _canonical(prediction)]
    body = {"schema": CHECK_SCHEMA, "query_id": request["query_id"],
            "source_digest": request["source_digest"], "kind": request["kind"],
            "rule": request["rule"], "answer_digest": _digest(prediction),
            "target_digest": target["target_digest"],
            "checker_profile_digest": target["checker_profile_digest"],
            "correct": bool(matched), "admissible_answer_count": len(target["admissible_answers"]),
            "witnesses": matched, "boundary": BOUNDARY}
    return deepcopy({**body, "check_digest": _digest(body)})
