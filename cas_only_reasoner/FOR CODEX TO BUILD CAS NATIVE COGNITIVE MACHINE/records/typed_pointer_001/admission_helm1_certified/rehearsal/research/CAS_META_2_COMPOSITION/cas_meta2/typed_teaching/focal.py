"""Bounded, source-grounded role recognition, not free-language semantics.

An excerpt is one or more controlled clauses: a fixed readable prefix followed
by canonical JSON. The prefix and payload shape are public grammatical cues.
This task can therefore be solved as controlled-language classification; it
does not measure unrestricted semantic recognition. Every asserted claim must
also agree with the supplied public source. False or unknown claims refuse.

``render_excerpt`` is authoring: a template chooses a positive example, never a
learner menu. ``derive_roles`` does not call that renderer, read its template,
consult an event face, inspect provenance, or access a private answer. Only the
explicit focal text is classified; background source and worked supports are
not additional focal clauses. A complete static account supports roles 5 and
6 under this declared convention. No process, interaction, authorship or wider
world truth is inferred from containment or presentation order.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json

from . import answers, source


GRAMMAR_SCHEMA = "cas.typed-teaching-focal-grammar/0.1"
RULE_ID = "focal_excerpt_roles_v1"
MAX_CLAUSES = 16
MAX_ISOMORPHISM_STATES = 100000
PREFIXES = {
    "definition": "Declared whole: ",
    "context": "Declared surroundings: ",
    "analogy": "Different domains, same containment pattern: ",
    "correspondence": "Exact node correspondence: ",
    "parts": "Direct constituent inventory: ",
    "account": "Complete static containment account: ",
    "reference": "Source reference: ",
}
_FIELDS = {
    "definition": {"whole", "kind_ref", "function_ref"},
    "context": {"world_id", "setting_ref", "participants"},
    "analogy": {"source_world_id", "target_world_id"},
    "correspondence": {"source_world_id", "target_world_id", "pairs"},
    "parts": {"world_id", "whole", "nodes"},
    "account": {"world_id", "edges"},
    "reference": {"world_id"},
}
_ROLES = {"definition": [1], "context": [2], "analogy": [3],
          "correspondence": [4], "parts": [5], "account": [5, 6], "reference": []}


class FocalContractError(ValueError):
    """An excerpt is outside the grammar or makes an unsupported claim."""


def _require(condition, reason):
    if not condition:
        raise FocalContractError(reason)


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise FocalContractError("FOCAL_CANONICAL_JSON") from exc


def grammar_profile():
    """The published classification convention, not a learned model profile."""
    return {"schema": GRAMMAR_SCHEMA, "rule": RULE_ID,
            "syntax": "READABLE_PREFIX_PLUS_CANONICAL_JSON_ONE_CLAUSE_PER_LF_LINE",
            "clauses": [{"name": name, "prefix": PREFIXES[name],
                         "fields": sorted(_FIELDS[name]), "roles": list(_ROLES[name])}
                        for name in PREFIXES],
            "max_excerpt_bytes": answers.MAX_EXCERPT_BYTES, "max_clauses": MAX_CLAUSES,
            "max_isomorphism_search_states": MAX_ISOMORPHISM_STATES,
            "scope": "EXPLICIT_FOCAL_CLAUSES_ONLY_NOT_BACKGROUND_OR_WORKED_SUPPORTS",
            "claim_authority": "EXACT_CALLER_SUPPLIED_SOURCE_NOT_WORLD_TRUTH",
            "recognition_scope": "CONTROLLED_GRAMMAR_NOT_UNRESTRICTED_NATURAL_LANGUAGE",
            "static_account_roles": [5, 6], "process_order_inferred": False,
            "interaction_facts_inferred": False,
            "candidate_menu": "ALL_SIX_ROLES_INDEPENDENT_OF_TARGET"}


def _closed(value, fields, reason):
    _require(type(value) is dict and set(value) == set(fields), reason)


def _member(value, values, reason):
    _require(type(value) is str and value in values, reason)


def _nodes(world):
    return sorted(node["ref"] for node in world["nodes"])


def _edges(world):
    return {(edge["source"], edge["target"]) for edge in world["contains"]}


def _pair_rows(edges):
    return [{"source": a, "target": b} for a, b in sorted(edges)]


def _bijection(left, right):
    """First lexical exact directed-graph bijection, with a hard search bound.

    Used only for source authoring and private claim checking, never inference.
    Degree filtering and partial-edge tests do not certify a match; the final
    mapped edge set must equal the entire target edge set.
    """
    left_nodes, right_nodes = _nodes(left), _nodes(right)
    le, re = _edges(left), _edges(right)
    if len(left_nodes) != len(right_nodes) or len(le) != len(re):
        return None
    def signature(node, edges):
        return (sum(a == node for a, _ in edges), sum(b == node for _, b in edges))
    choices = {a: [b for b in right_nodes if signature(a, le) == signature(b, re)]
               for a in left_nodes}
    mapping, used = {}, set()
    states = 0
    def visit(position):
        nonlocal states
        states += 1
        _require(states <= MAX_ISOMORPHISM_STATES, "FOCAL_ISOMORPHISM_SEARCH_BOUND")
        if position == len(left_nodes):
            return dict(mapping) if {(mapping[a], mapping[b]) for a, b in le} == re else None
        a = left_nodes[position]
        for b in choices[a]:
            if b in used or any(((a, x) in le) != ((b, y) in re)
                               or ((x, a) in le) != ((y, b) in re)
                               for x, y in mapping.items()):
                continue
            mapping[a] = b
            used.add(b)
            result = visit(position + 1)
            if result is not None:
                return result
            del mapping[a]
            used.remove(b)
        return None
    return visit(0)


def _parse(excerpt):
    _require(type(excerpt) is str and bool(excerpt), "FOCAL_TEXT")
    try:
        size = len(excerpt.encode("utf-8"))
    except UnicodeError as exc:
        raise FocalContractError("FOCAL_UTF8") from exc
    _require(size <= answers.MAX_EXCERPT_BYTES, "FOCAL_BYTE_BOUND")
    lines = excerpt.split("\n")
    _require(1 <= len(lines) <= MAX_CLAUSES and all(lines), "FOCAL_CLAUSE_BOUND")
    result = []
    def object_pairs(pairs):
        value = {}
        for key, child in pairs:
            _require(key not in value, "FOCAL_DUPLICATE_KEY")
            value[key] = child
        return value
    def constant(_value):
        raise FocalContractError("FOCAL_NONFINITE")
    for line in lines:
        names = [name for name, prefix in PREFIXES.items() if line.startswith(prefix)]
        _require(len(names) == 1, "FOCAL_UNKNOWN_CLAUSE")
        name = names[0]
        raw = line[len(PREFIXES[name]):]
        try:
            payload = json.loads(raw, object_pairs_hook=object_pairs, parse_constant=constant)
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise FocalContractError("FOCAL_JSON") from exc
        _require(_canonical(payload).decode("utf-8") == raw, "FOCAL_NONCANONICAL")
        _closed(payload, _FIELDS[name], "FOCAL_CLAUSE_FIELDS")
        result.append((name, payload, line))
    return result


def _checked_pairs(value, left_nodes, right_nodes, reason):
    _require(type(value) is list, reason)
    result = []
    for pair in value:
        _closed(pair, {"source", "target"}, reason)
        _member(pair["source"], left_nodes, reason)
        _member(pair["target"], right_nodes, reason)
        result.append((pair["source"], pair["target"]))
    _require(result == sorted(set(result)), reason)
    return result


def _checked_set(value, candidates, reason):
    _require(type(value) is list and all(type(item) is str for item in value), reason)
    _require(value == sorted(set(value)) and all(item in candidates for item in value), reason)


def _check_clause(name, payload, focus, worlds, bank_ids):
    """Validate asserted content independently of the renderer's template."""
    world = worlds[focus]
    nodes = _nodes(world)
    if name == "definition":
        _require(payload["whole"] == world["declared_whole"]
                 and payload["kind_ref"] == answers.declaration_ref(focus, "kind")
                 and payload["function_ref"] == answers.declaration_ref(focus, "function"),
                 "FOCAL_FALSE_DEFINITION")
        return [payload["whole"], payload["kind_ref"], payload["function_ref"]]
    if name in ("analogy", "correspondence"):
        _require(payload["source_world_id"] == focus, "FOCAL_COMPARISON_FOCUS")
        target = payload["target_world_id"]
        _member(target, bank_ids, "FOCAL_COMPARISON_PUBLIC_BANK")
        _require(target != focus, "FOCAL_COMPARISON_DISTINCT_WORLDS")
        other = worlds[target]
        if name == "analogy":
            _require(world["declarations"]["domain"] != other["declarations"]["domain"],
                     "FOCAL_FALSE_DIFFERENT_DOMAINS")
            _require(_bijection(world, other) is not None, "FOCAL_FALSE_SAME_PATTERN")
            return [focus, target]
        pairs = _checked_pairs(payload["pairs"], nodes, _nodes(other), "FOCAL_MAPPING_PAIRS")
        _require([a for a, _ in pairs] == nodes
                 and sorted(b for _, b in pairs) == _nodes(other), "FOCAL_NOT_BIJECTION")
        mapping = dict(pairs)
        _require({(mapping[a], mapping[b]) for a, b in _edges(world)} == _edges(other),
                 "FOCAL_FALSE_MAPPING")
        return [focus, target] + [ref for pair in pairs for ref in pair]
    _require(payload["world_id"] == focus, "FOCAL_CLAUSE_FOCUS")
    if name == "context":
        _require(payload["setting_ref"] == answers.declaration_ref(focus, "setting"),
                 "FOCAL_FALSE_SETTING")
        _checked_set(payload["participants"], nodes, "FOCAL_PARTICIPANT_SET")
        _require(payload["participants"] == sorted(world["declarations"]["participants"]),
                 "FOCAL_FALSE_PARTICIPANTS")
        return [payload["setting_ref"]] + payload["participants"]
    if name == "parts":
        _member(payload["whole"], nodes, "FOCAL_PARTS_WHOLE")
        _checked_set(payload["nodes"], nodes, "FOCAL_PART_SET")
        _require(payload["nodes"] == sorted(b for a, b in _edges(world) if a == payload["whole"]),
                 "FOCAL_FALSE_PARTS")
        return [payload["whole"]] + payload["nodes"]
    if name == "account":
        pairs = _checked_pairs(payload["edges"], nodes, nodes, "FOCAL_ACCOUNT_EDGES")
        _require(set(pairs) == _edges(world), "FOCAL_FALSE_COMPLETE_ACCOUNT")
        return [focus] + [ref for pair in pairs for ref in pair]
    _require(name == "reference", "FOCAL_UNKNOWN_CLAUSE")
    return [focus]


def derive_roles(public, query):
    """Derive only from validated focal clauses and public facts.

    Witnesses are private checker evidence. A learner receives the original
    excerpt, never these derived roles or the renderer's template selector.
    This function must not be used by an inference-time decoder or repairer.
    """
    validated = answers.validate_query(public, query)
    _require(validated["kind"] == "role_set" and validated["rule"] == RULE_ID,
             "FOCAL_ROLE_QUERY_REQUIRED")
    worlds = {world["world_id"]: world for world in public["worlds"]}
    focus = validated["focus_world_id"]
    clauses = _parse(validated["arguments"]["focal_excerpt"])
    roles, witnesses = set(), []
    for index, (name, payload, line) in enumerate(clauses):
        refs = _check_clause(name, payload, focus, worlds, public["bank"]["world_ids"])
        clause_roles = list(_ROLES[name])
        roles.update(clause_roles)
        witnesses.append({"clause_index": index, "rule": GRAMMAR_SCHEMA + "/" + name,
                          "clause_sha256": sha256(line.encode("utf-8")).hexdigest(),
                          "source_digest": validated["source_digest"],
                          "roles": clause_roles, "public_refs": sorted(set(refs)),
                          "authority": "EXACT_CALLER_SUPPLIED_SOURCE_NOT_WORLD_TRUTH"})
    result = sorted(roles)
    return {"roles": result,
            "status": "INSUFFICIENT" if not result else "UNIQUE" if len(result) == 1 else "AMBIGUOUS",
            "witnesses": witnesses}


def render_excerpt(public, *, template, focus_world_id=None, comparison_world_id=None):
    """Author positive content from public facts; do not invoke a private solver.

    Template numbers select authored content only. They are not passed to the
    recognition checker or included in the resulting public excerpt. Selecting
    an example with a known structure is not selecting learner answer options.
    If no suitable public partner exists, refuse instead of inventing one.
    """
    source.validate_public(public)
    _require(type(template) is int and template in (1, 2, 3, 4, 5, 6), "FOCAL_TEMPLATE")
    worlds = {world["world_id"]: world for world in public["worlds"]}
    focus = public["focus_world_id"] if focus_world_id is None else focus_world_id
    _member(focus, worlds, "FOCAL_FOCUS")
    world = worlds[focus]
    _require(comparison_world_id is None or template in (3, 4), "FOCAL_UNUSED_COMPARISON")
    if template in (3, 4):
        candidates = public["bank"]["world_ids"]
        if comparison_world_id is not None:
            _member(comparison_world_id, candidates, "FOCAL_COMPARISON_PUBLIC_BANK")
            candidates = [comparison_world_id]
        match = None
        for target in candidates:
            if target == focus or (template == 3 and world["declarations"]["domain"]
                                    == worlds[target]["declarations"]["domain"]):
                continue
            mapping = _bijection(world, worlds[target])
            if mapping is not None:
                match = (target, mapping)
                break
        _require(match is not None, "FOCAL_NO_SUITABLE_PUBLIC_COMPARISON")
        target, mapping = match
        payload = {"source_world_id": focus, "target_world_id": target}
        name = "analogy" if template == 3 else "correspondence"
        if template == 4:
            payload["pairs"] = _pair_rows(mapping.items())
    elif template == 1:
        name, payload = "definition", {"whole": world["declared_whole"],
            "kind_ref": answers.declaration_ref(focus, "kind"),
            "function_ref": answers.declaration_ref(focus, "function")}
    elif template == 2:
        name, payload = "context", {"world_id": focus,
            "setting_ref": answers.declaration_ref(focus, "setting"),
            "participants": sorted(world["declarations"]["participants"])}
    elif template == 5:
        name, payload = "parts", {"world_id": focus, "whole": world["declared_whole"],
            "nodes": sorted(b for a, b in _edges(world) if a == world["declared_whole"])}
    else:
        name, payload = "account", {"world_id": focus, "edges": _pair_rows(_edges(world))}
    excerpt = PREFIXES[name] + _canonical(payload).decode("utf-8")
    _require(len(excerpt.encode("utf-8")) <= answers.MAX_EXCERPT_BYTES, "FOCAL_BYTE_BOUND")
    return excerpt
