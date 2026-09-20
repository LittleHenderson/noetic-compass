"""Graph-first teaching candidate: an explicit structure of ideas.

Owner-corrected model with FOUR pieces: nodes, node contents, connectors, and
intersection/commonality. Branches and connectors are the same: an item's
available choices are exactly its outgoing connectors (``Graph.outgoing``),
and there is no other branch data anywhere in the model.

Two further owner corrections are enforced mechanically:
- the information a connector contains IS the commonality of the two nodes it
  connects; every stored connector carries that content and validation
  recomputes it and rejects any mismatch;
- there is no limit on how many connectors or contents a node may have.

Invariants (all enforced by ``Graph.validate`` and the tests):
- node identity is separate from node contents;
- connectors carry explicit names; direction alone is not causation;
- derived connectors (``shares``, ``produced_by``) are NEVER stored — the
  reference checker computes them;
- no answer edges: nothing in the graph may mark the correct selection.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

GRAPH_SCHEMA = "cas-meta2-graph-teaching-graph/1"

STORED_KINDS = ("contains", "has_color", "has_shape", "has_value", "requires",
                "triggers")
DERIVED_KINDS = ("shares", "produced_by")
FORBIDDEN_KINDS = ("answer", "correct", "solution")


def require(condition, code):
    if not condition:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(raw):
    return sha256(raw).hexdigest()


@dataclass(frozen=True)
class Node:
    identifier: str
    kind: str
    fields: tuple  # ((field_name, value), ...)

    def field(self, name):
        for key, value in self.fields:
            if key == name:
                return value
        raise KeyError(name)


@dataclass(frozen=True)
class Relation:
    kind: str
    source: str
    target: str
    content: tuple = None  # the commonality of the two connected nodes


def commonality_of(graph, relation):
    """The information the connector contains: the commonality of its endpoints."""
    if relation.kind.startswith("has_"):
        field = relation.kind[len("has_"):]
        value = graph.node(relation.source).field(field)
        require(graph.node(relation.target).field("value") == value,
                "CONNECTOR_CONTENT_SOURCE_MISMATCH:" + relation.kind)
        return (field, value)
    if relation.kind == "contains":
        return ("constituent", relation.target)
    if relation.kind == "requires":
        requirement = graph.node(relation.target)
        return (requirement.field("property"), requirement.field("value"))
    if relation.kind == "triggers":
        return ("under_consideration", relation.target)
    raise ValueError("COMMONALITY_UNKNOWN_KIND:" + relation.kind)


@dataclass(frozen=True)
class Graph:
    nodes: tuple
    relations: tuple

    def node(self, identifier):
        for node in self.nodes:
            if node.identifier == identifier:
                return node
        raise KeyError(identifier)

    def outgoing(self, identifier):
        """The branch structure: the item's outgoing connectors, nothing else.

        There is no limit on how many connectors a node may have; every one of
        them is returned here.
        """
        return tuple(relation for relation in self.relations
                     if relation.source == identifier)

    def validate(self):
        ids = [node.identifier for node in self.nodes]
        require(len(ids) == len(set(ids)), "GRAPH_DUPLICATE_NODE")
        require(ids, "GRAPH_EMPTY")
        for node in self.nodes:
            require(type(node.identifier) is str and node.identifier,
                    "GRAPH_NODE_IDENTIFIER")
            require(type(node.kind) is str and node.kind, "GRAPH_NODE_KIND")
            for name, value in node.fields:
                require(type(name) is str and name, "GRAPH_FIELD_NAME")
                require(type(value) in (str, int, float, bool), "GRAPH_FIELD_VALUE")
        seen = set()
        for relation in self.relations:
            require(relation.source in ids and relation.target in ids,
                    "GRAPH_DANGLING_RELATION:" + relation.kind)
            require(relation.kind not in FORBIDDEN_KINDS, "GRAPH_ANSWER_EDGE_FORBIDDEN")
            require(relation.kind in STORED_KINDS,
                    "GRAPH_DERIVED_OR_UNKNOWN_RELATION_STORED:" + relation.kind)
            require(relation.content is not None, "CONNECTOR_CONTENT_REQUIRED")
            require(tuple(relation.content) == commonality_of(self, relation),
                    "CONNECTOR_CONTENT_NOT_COMMONALITY:" + relation.kind)
            key = (relation.kind, relation.source, relation.target)
            require(key not in seen, "GRAPH_DUPLICATE_RELATION:" + relation.kind)
            seen.add(key)
        return self

    def to_record(self):
        return {"schema": GRAPH_SCHEMA,
                "nodes": [{"identifier": node.identifier, "kind": node.kind,
                           "fields": [list(pair) for pair in node.fields]}
                          for node in self.nodes],
                "relations": [{"kind": relation.kind, "source": relation.source,
                               "target": relation.target,
                               "content": list(relation.content)}
                              for relation in self.relations]}

    @classmethod
    def from_record(cls, record):
        require(type(record) is dict and record.get("schema") == GRAPH_SCHEMA,
                "GRAPH_RECORD_SCHEMA")
        nodes = tuple(Node(identifier=item["identifier"], kind=item["kind"],
                           fields=tuple((name, value) for name, value in item["fields"]))
                      for item in record["nodes"])
        relations = tuple(Relation(kind=item["kind"], source=item["source"],
                                   target=item["target"],
                                   content=tuple(item["content"]))
                          for item in record["relations"])
        return cls(nodes=nodes, relations=relations).validate()

    def render(self):
        """Deterministic teaching presentation (structure only, no answers)."""
        lines = []
        for node in self.nodes:
            fields = " ".join("%s=%s" % (name, value) for name, value in node.fields)
            lines.append(("node %s kind=%s %s"
                          % (node.identifier, node.kind, fields)).rstrip())
        for relation in self.relations:
            lines.append("rel %s --%s--> %s" % (relation.source, relation.kind, relation.target))
        return "\n".join(lines) + "\n"


def digests(value):
    return digest(canonical(value))
