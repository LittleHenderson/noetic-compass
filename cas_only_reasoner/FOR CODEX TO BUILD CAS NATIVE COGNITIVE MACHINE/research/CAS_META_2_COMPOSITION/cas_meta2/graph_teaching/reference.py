"""Deterministic reference checker for the graph-first teaching candidate.

Every answer is computed from the stored graph (nodes, contents, connectors).
The derived connectors ``shares`` and ``produced_by`` are computed here and
NEVER stored in a learner graph. The checker refuses ambiguity: exactly one
correct selection or an explicit error.
"""
from __future__ import annotations

from .graph import Graph, require


def field_value(graph, node_id, field):
    return graph.node(node_id).field(field)


def objects_with_field(graph, field, value):
    return sorted(node.identifier for node in graph.nodes
                  if node.kind == "object"
                  and any(name == field and item == value for name, item in node.fields))


def direct_parts(graph, idea_id):
    """Constituent ideas directly inside ``idea_id`` (``contains`` connectors)."""
    return sorted(relation.target for relation in graph.outgoing(idea_id)
                  if relation.kind == "contains")


def transitive_parts(graph, idea_id):
    """All constituent ideas reachable through ``contains`` connectors."""
    seen, frontier = set(), [idea_id]
    while frontier:
        current = frontier.pop()
        for part in direct_parts(graph, current):
            if part not in seen:
                seen.add(part)
                frontier.append(part)
    return sorted(seen)


def shared_parts(graph, a, b):
    """Constituent ideas directly common to ``a`` and ``b`` (derived ``shares``).

    Direct level only, matching the lesson example: bicycle and cart share the
    constituent idea ``wheel``; the parts INSIDE wheel are reached through
    wheel and belong to the REACHED_VIA lesson. If one idea is itself a direct
    constituent of the other, that constituent is the shared idea.
    """
    require(a != b, "SHARED_PARTS_DISTINCT_REQUIRED")
    shared = set(direct_parts(graph, a)) & set(direct_parts(graph, b))
    if b in direct_parts(graph, a):
        shared.add(b)
    if a in direct_parts(graph, b):
        shared.add(a)
    return sorted(shared)


def reach_kind(graph, part_id, idea_id):
    """'direct', 'via:<constituent>' or 'absent' for part relative to idea."""
    require(idea_id != part_id, "REACH_DISTINCT_REQUIRED")
    if part_id in direct_parts(graph, idea_id):
        return "direct"
    for constituent in direct_parts(graph, idea_id):
        if part_id in transitive_parts(graph, constituent):
            return "via:" + constituent
    return "absent"


def requirements(graph, request_id):
    """Ordered (field, value) requirements named by the request's connectors."""
    pairs = []
    for relation in graph.outgoing(request_id):
        if relation.kind == "requires":
            requirement = graph.node(relation.target)
            pairs.append((requirement.field("property"), requirement.field("value")))
    return sorted(pairs)


def matching_objects(graph, field, value):
    return objects_with_field(graph, field, value)


def select_object(graph, request_id):
    """Exactly one object must satisfy every requirement of the request."""
    all_requirements = requirements(graph, request_id)
    require(all_requirements, "SELECT_REQUIREMENTS_REQUIRED")
    candidates = None
    for field, value in all_requirements:
        matches = set(objects_with_field(graph, field, value))
        candidates = matches if candidates is None else (candidates & matches)
    require(len(candidates) == 1, "SELECT_NOT_UNIQUE")
    return sorted(candidates)[0]


def relation_kind_between(graph, source_id, target_id):
    """The named kind of a stored connector from source to target."""
    kinds = sorted(relation.kind for relation in graph.outgoing(source_id)
                   if relation.target == target_id)
    require(len(kinds) == 1, "RELATION_NOT_UNIQUE")
    return kinds[0]


def common_fields(graph, a, b):
    """(field, value) pairs present in both nodes (derived commonality)."""
    fields_a = dict(graph.node(a).fields)
    fields_b = dict(graph.node(b).fields)
    return sorted((name, value) for name, value in fields_a.items()
                  if name in fields_b and fields_b[name] == value)


def derivation_for(operation, graph, arguments):
    """Recorded reference derivation: which connectors determined the answer."""
    if operation == "LIST_PARTS":
        return {"method": "direct_parts", "used_relations": ["contains"]}
    if operation == "FIND_SHARED_PART":
        return {"method": "shared_parts", "used_relations": ["contains"],
                "derived_relation": "shares"}
    if operation == "REACHED_VIA":
        return {"method": "reach_kind", "used_relations": ["contains"]}
    if operation in ("FOLLOW_ONE_HOP", "FOLLOW_TWO_HOPS", "CHANGE_REQUEST"):
        return {"method": "select_object",
                "used_relations": ["requires", "has_color", "has_shape", "has_value"]}
    if operation == "READ_VALUE":
        return {"method": "field_value", "used_relations": ["has_value"]}
    if operation == "CONTAINING_NODE":
        return {"method": "objects_with_field", "used_relations": ["has_color",
                                                                   "has_shape", "has_value"]}
    if operation == "IDENTIFY_CONNECTION":
        return {"method": "relation_kind_between",
                "used_relations": ["has_color", "has_shape", "has_value"]}
    raise ValueError("UNKNOWN_OPERATION:" + operation)
