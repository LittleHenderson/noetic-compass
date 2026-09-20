"""Target-independent public questions and typed answer syntax.

This module never checks graph truth, solves a task, reads a teacher sidecar or
runs a learner. Incorrect but well-formed answers must pass syntax validation.
Reference inventories include every public possibility of the requested type.
The new contract is not compatible with the legacy three-choice worker.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from itertools import permutations
import json

from . import source

QUERY_SCHEMA = "cas.typed-teaching-query/0.1"
ANSWER_SCHEMA = "cas.typed-teaching-answer/0.1"
SPACE_SCHEMA = "cas.typed-teaching-answer-space/0.1"
MAX_EXCERPT_BYTES = 16384
MAX_ANSWER_BYTES = 32768
MAX_PERMUTATION_NODES = 4
ROLE_IDS = (1, 2, 3, 4, 5, 6)
RULES = {
    "role_set": ("focal_excerpt_roles_v1",),
    "definition": ("declared_kind_and_function_v1",),
    "context": ("declared_setting_and_participants_v1",),
    "analogy": ("cross_domain_full_graph_isomorphism_v1",),
    "correspondence": ("full_directed_graph_bijection_v1",),
    "parts": ("direct_contains_v1",),
    "edge_account": ("complete_edge_set_lexical_serialization_v1",),
    "reach": ("first_direct_constituent_lexical_v1",
              "bfs_immediate_predecessor_lexical_v1"),
}
_ARGUMENTS = {
    "role_set": {"focal_excerpt"}, "definition": set(), "context": set(),
    "analogy": set(), "correspondence": {"target_world_id"},
    "parts": {"whole"}, "edge_account": set(), "reach": {"whole", "part"},
}
_QUERY_FIELDS = {"schema", "source_digest", "focus_world_id", "kind", "rule",
                 "arguments", "query_id"}


class AnswerContractError(ValueError):
    """A public query or answer is malformed, not necessarily false."""


def _require(condition, reason):
    if not condition:
        raise AnswerContractError(reason)


def _closed(value, fields, reason):
    _require(type(value) is dict and set(value) == set(fields), reason)


def _json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise AnswerContractError("TYPED_NOT_CANONICAL_JSON") from exc


def _digest(value):
    return sha256(_json(value)).hexdigest()


def _worlds(public):
    source.validate_public(public)
    return {world["world_id"]: world for world in public["worlds"]}


def _nodes(world):
    return [node["ref"] for node in world["nodes"]]


def _query_body(public, *, kind, rule, arguments, focus_world_id):
    worlds = _worlds(public)
    _require(type(kind) is str and kind in RULES, "TYPED_KIND")
    if rule is None:
        _require(len(RULES[kind]) == 1, "TYPED_EXPLICIT_REACH_RULE_REQUIRED")
        rule = RULES[kind][0]
    _require(type(rule) is str and rule in RULES[kind], "TYPED_RULE")
    focus = public["focus_world_id"] if focus_world_id is None else focus_world_id
    _require(type(focus) is str and focus in worlds, "TYPED_FOCUS_WORLD")
    arguments = {} if arguments is None else arguments
    _closed(arguments, _ARGUMENTS[kind], "TYPED_ARGUMENT_FIELDS")
    if kind == "role_set":
        excerpt = arguments["focal_excerpt"]
        _require(type(excerpt) is str and excerpt.strip(), "TYPED_FOCAL_EXCERPT")
        try:
            excerpt_bytes = excerpt.encode("utf-8")
        except UnicodeError as exc:
            raise AnswerContractError("TYPED_EXCERPT_ENCODING") from exc
        _require(len(excerpt_bytes) <= MAX_EXCERPT_BYTES, "TYPED_EXCERPT_BOUND")
    if kind == "correspondence":
        target = arguments["target_world_id"]
        _require(type(target) is str and target in public["bank"]["world_ids"],
                 "TYPED_TARGET_NOT_IN_PUBLIC_BANK")
    for field in ("whole", "part"):
        if field in arguments:
            _require(type(arguments[field]) is str and arguments[field] in _nodes(worlds[focus]),
                     "TYPED_ARGUMENT_NODE_SCOPE")
    if kind == "reach":
        _require(arguments["whole"] != arguments["part"], "TYPED_REACH_DISTINCT_NODES")
    return {"schema": QUERY_SCHEMA, "source_digest": source.public_digest(public),
            "focus_world_id": focus, "kind": kind, "rule": rule,
            "arguments": deepcopy(arguments)}


def compile_query(public, *, kind, rule=None, arguments=None, focus_world_id=None):
    """Bind only public source, request and rule; no target/face/negative input."""
    body = _query_body(public, kind=kind, rule=rule, arguments=arguments,
                       focus_world_id=focus_world_id)
    return {**body, "query_id": "typed-query-" + _digest(body)}


def validate_query(public, query):
    _closed(query, _QUERY_FIELDS, "TYPED_QUERY_FIELDS")
    expected = compile_query(public, kind=query["kind"], rule=query["rule"],
                             arguments=query["arguments"],
                             focus_world_id=query["focus_world_id"])
    _require(_json(query) == _json(expected), "TYPED_QUERY_BINDING")
    return deepcopy(expected)


def declaration_ref(world_id, field):
    """Uniform public reference, not a teacher-selected declaration."""
    _require(type(world_id) is str and bool(world_id), "TYPED_DECLARATION_WORLD")
    _require(field in ("kind", "function", "setting"), "TYPED_DECLARATION_FIELD")
    return world_id + "/decl/" + field


def answer_space(public, query):
    """All syntactic choices; excludes no answer because of graph correctness.

    Edges are all node pairs, including self-pairs, not the declared contains
    subset. Analogy includes the entire frozen bank, not matching graphs only.
    """
    validate_query(public, query)
    worlds = _worlds(public)
    nodes = _nodes(worlds[query["focus_world_id"]])
    kind = query["kind"]
    inventory = {}
    if kind == "role_set":
        inventory = {"role_ids": list(ROLE_IDS),
                     "statuses": ["INSUFFICIENT", "UNIQUE", "AMBIGUOUS"]}
    elif kind == "definition":
        inventory = {"whole_refs": nodes,
                     "kind_refs": [declaration_ref(w, "kind") for w in sorted(worlds)],
                     "function_refs": [declaration_ref(w, "function") for w in sorted(worlds)]}
    elif kind == "context":
        inventory = {"setting_refs": [declaration_ref(w, "setting") for w in sorted(worlds)],
                     "participant_refs": nodes}
    elif kind == "analogy":
        inventory = {"world_ids": list(public["bank"]["world_ids"]), "no_match_allowed": True}
    elif kind == "correspondence":
        inventory = {"source_nodes": nodes,
                     "target_nodes": _nodes(worlds[query["arguments"]["target_world_id"]]),
                     "no_match_allowed": True}
    elif kind == "parts":
        inventory = {"node_refs": nodes}
    elif kind == "edge_account":
        inventory = {"edge_pairs": [[a, b] for a in nodes for b in nodes],
                     "order": "LEXICAL_REFERENCE_PAIR_SERIALIZATION_NOT_PROCESS"}
    elif kind == "reach":
        inventory = {"states": ["ABSENT", "DIRECT", "VIA"], "via_refs": nodes}
    return {"schema": SPACE_SCHEMA, "query_id": query["query_id"],
            "kind": kind, "inventory": inventory,
            "semantic_correctness_checked": False}


def _member(value, candidates, reason):
    _require(type(value) is str and value in candidates, reason)


def _set(value, candidates, reason):
    _require(type(value) is list and all(type(item) is str for item in value), reason)
    _require(value == sorted(set(value)) and all(item in candidates for item in value), reason)


def _payload(space, value):
    kind, inv = space["kind"], space["inventory"]
    if kind == "role_set":
        _closed(value, {"roles", "status"}, "TYPED_ROLE_FIELDS")
        roles = value["roles"]
        _require(type(roles) is list and all(type(r) is int and r in ROLE_IDS for r in roles)
                 and roles == sorted(set(roles)), "TYPED_ROLE_SET")
        status = "INSUFFICIENT" if not roles else "UNIQUE" if len(roles) == 1 else "AMBIGUOUS"
        _require(value["status"] == status, "TYPED_ROLE_STATUS")
    elif kind == "definition":
        _closed(value, {"whole", "kind_ref", "function_ref"}, "TYPED_DEFINITION_FIELDS")
        for field, candidates in (("whole", "whole_refs"), ("kind_ref", "kind_refs"),
                                  ("function_ref", "function_refs")):
            _member(value[field], inv[candidates], "TYPED_DEFINITION_REFERENCE")
    elif kind == "context":
        _closed(value, {"setting_ref", "participants"}, "TYPED_CONTEXT_FIELDS")
        _member(value["setting_ref"], inv["setting_refs"], "TYPED_CONTEXT_SETTING")
        _set(value["participants"], inv["participant_refs"], "TYPED_CONTEXT_PARTICIPANTS")
    elif kind == "analogy":
        _closed(value, {"world_id"}, "TYPED_ANALOGY_FIELDS")
        if value["world_id"] is not None:
            _member(value["world_id"], inv["world_ids"], "TYPED_ANALOGY_WORLD")
    elif kind == "correspondence":
        _closed(value, {"status", "pairs"}, "TYPED_CORRESPONDENCE_FIELDS")
        _require(type(value["status"]) is str and value["status"] in ("MAPPING", "NO_MATCH"),
                 "TYPED_CORRESPONDENCE_STATUS")
        pairs = value["pairs"]
        _require(type(pairs) is list, "TYPED_CORRESPONDENCE_PAIRS")
        if value["status"] == "NO_MATCH":
            _require(pairs == [], "TYPED_NO_MATCH_PAIRS")
        else:
            for pair in pairs:
                _closed(pair, {"source", "target"}, "TYPED_MAPPING_PAIR_FIELDS")
                _member(pair["source"], inv["source_nodes"], "TYPED_MAPPING_SOURCE")
                _member(pair["target"], inv["target_nodes"], "TYPED_MAPPING_TARGET")
            _require([p["source"] for p in pairs] == sorted(inv["source_nodes"]),
                     "TYPED_MAPPING_SOURCE_COVERAGE")
            _require(sorted(p["target"] for p in pairs) == sorted(inv["target_nodes"]),
                     "TYPED_MAPPING_BIJECTION")
    elif kind == "parts":
        _closed(value, {"nodes"}, "TYPED_PARTS_FIELDS")
        _set(value["nodes"], inv["node_refs"], "TYPED_PARTS_NODES")
    elif kind == "edge_account":
        _closed(value, {"edges"}, "TYPED_EDGE_FIELDS")
        _require(type(value["edges"]) is list, "TYPED_EDGE_LIST")
        pairs = []
        for pair in value["edges"]:
            _closed(pair, {"source", "target"}, "TYPED_EDGE_PAIR_FIELDS")
            candidate = [pair["source"], pair["target"]]
            _require(all(type(v) is str for v in candidate)
                     and candidate in inv["edge_pairs"], "TYPED_EDGE_REFERENCE")
            pairs.append(tuple(candidate))
        _require(pairs == sorted(set(pairs)), "TYPED_EDGE_CANONICAL_SET")
    elif kind == "reach":
        _closed(value, {"state", "via"}, "TYPED_REACH_FIELDS")
        _require(type(value["state"]) is str and value["state"] in inv["states"], "TYPED_REACH_STATE")
        if value["state"] == "VIA":
            _member(value["via"], inv["via_refs"], "TYPED_REACH_VIA")
        else:
            _require(value["via"] is None, "TYPED_REACH_NON_VIA")


def make_answer(public, query, payload):
    """Wrap caller prediction; syntactic admission only."""
    space = answer_space(public, query)
    _require(len(_json(payload)) <= MAX_ANSWER_BYTES, "TYPED_ANSWER_BOUND")
    _payload(space, payload)
    result = {"schema": ANSWER_SCHEMA, "query_id": query["query_id"],
              "kind": query["kind"], "value": deepcopy(payload)}
    _require(len(_json(result)) <= MAX_ANSWER_BYTES, "TYPED_ANSWER_BOUND")
    return result


def validate_answer(public, query, answer):
    _closed(answer, {"schema", "query_id", "kind", "value"}, "TYPED_ANSWER_FIELDS")
    expected = make_answer(public, query, answer["value"])
    _require(_json(answer) == _json(expected), "TYPED_ANSWER_BINDING")
    return deepcopy(expected)


def encode_answer(public, query, answer):
    return _json(validate_answer(public, query, answer))


def decode_answer(public, query, raw):
    """Reject noncanonical bytes, duplicates and unknown fields; never repair."""
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_ANSWER_BYTES, "TYPED_WIRE_BOUND")
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            _require(key not in result, "TYPED_DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=object_pairs)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise AnswerContractError("TYPED_WIRE_JSON") from exc
    result = validate_answer(public, query, value)
    _require(_json(result) == raw, "TYPED_WIRE_NONCANONICAL")
    return result


def correspondence_candidates(public, query, *, max_nodes=MAX_PERMUTATION_NODES):
    """Bounded grammar-only candidates; includes wrong mappings and NO_MATCH.

    The only selection inputs are public scoped node inventories and a ceiling
    no larger than four. No graph edges or teacher labels enter permutation
    generation. Ten-node syntax admission does not admit 10! numerical work.
    """
    _require(type(max_nodes) is int and 1 <= max_nodes <= MAX_PERMUTATION_NODES,
             "TYPED_PERMUTATION_LIMIT")
    space = answer_space(public, query)
    _require(query["kind"] == "correspondence", "TYPED_CANDIDATES_KIND")
    inv = space["inventory"]
    left, right = sorted(inv["source_nodes"]), sorted(inv["target_nodes"])
    _require(max(len(left), len(right)) <= max_nodes, "TYPED_PERMUTATION_BOUND")
    candidates = [{"status": "NO_MATCH", "pairs": []}]
    if len(left) == len(right):
        candidates += [{"status": "MAPPING",
                        "pairs": [{"source": a, "target": b} for a, b in zip(left, row)]}
                       for row in permutations(right)]
    return candidates
