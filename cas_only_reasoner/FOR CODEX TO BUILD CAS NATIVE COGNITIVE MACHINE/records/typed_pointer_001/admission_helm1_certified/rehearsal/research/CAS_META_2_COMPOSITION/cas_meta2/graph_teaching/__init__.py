"""Graph-first teaching candidate: explicit structure of ideas.

Four pieces (owner-corrected): nodes, node contents, connectors, and
intersection/commonality. Branches and connectors are the same — an item's
available choices are exactly its outgoing connectors.

Modules:
- ``graph``: the structure (nodes, contents, named connectors) and its
  validation invariants (no stored derived connectors, no answer edges).
- ``reference``: the deterministic checker that computes every answer from
  the stored graph.
- ``lessons``: binding and whole-part lesson families, exercise generation,
  CAS/generic framings, and the sealed-split dataset builder.
"""
from .graph import Graph, Node, Relation
from . import reference
from . import lessons

__all__ = ["Graph", "Node", "Relation", "reference", "lessons"]
