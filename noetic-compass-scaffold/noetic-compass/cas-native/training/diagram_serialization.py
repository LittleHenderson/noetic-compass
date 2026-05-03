"""Diagram serialization: compiler graph → ML-friendly tensor input.

Converts a CAS expression string into the typed graph produced by the compiler
(``api/notation/compiler.py``) and then into batched tensor input suitable for
the ``GraphEncoder``.

The feature encoding is documented in
``docs/working/compiler_graph_schema_for_diagram_loop.md``:

  - Node features: 48-dim (23 node-kind one-hot + 25 CAS-axis features)
      CAS slice = 10 noetic + 4 domain + 7 drive + 4 register (multi-hot)
  - Edge features: 34-dim (33 edge-kind one-hot + 1 "other")
  - Padding: nodes padded to ``max_nodes``, edges padded to ``max_edges``
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import torch

_CAS_NATIVE_ROOT = Path(__file__).resolve().parent.parent
_PROJECT_ROOT = _CAS_NATIVE_ROOT.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Vocabulary: node kinds and edge kinds exactly as emitted by _DiagramBuilder
# ---------------------------------------------------------------------------

NODE_KINDS: tuple[str, ...] = (
    "noetic",
    "state",
    "drive",
    "domain",
    "register",
    "state_variant",
    "operator",
    "emergent",
    "coordinate",
    "tuple",
    "cardinality",
    "rpm_stage",
    "rpm",
    "production_target",
    "catalyst",
    "inhibitor",
    "state_vector",
    "yield",
    "program",
    "function",
    "module",
    "symbol",
    "subfoundation",
    # "other" is the implicit 24th bucket handled as index len(NODE_KINDS)
)

EDGE_KINDS: tuple[str, ...] = (
    "instantiates",
    "locates",
    "modulates",
    "register",
    "dependency",
    "results_from",
    "bidirectional",
    "operand",
    "fractal_step",
    "rpm_descent",
    "rpm_query",
    "emerges_as",
    "statement",
    "tuple_slot",
    "membership",
    "proper_subset",
    "subset",
    "proper_superset",
    "superset",
    "equals",
    "recipe_prerequisite",
    "catalyst",
    "inhibitor",
    "leakage",
    "activation",
    "yield_query",
    "yield_input",
    "cardinality",
    "product_axis",
    "cover_base",
    "cover_member",
    "partition_base",
    "partition_member",
    # "other" is the implicit 34th bucket handled as index len(EDGE_KINDS)
)

# Derived dims
NODE_KIND_DIM: int = len(NODE_KINDS) + 1   # +1 for "other"
CAS_FEATURE_DIM: int = 10 + 4 + 7 + 4     # noetic + domain + drive + register
NODE_FEATURE_DIM: int = NODE_KIND_DIM + CAS_FEATURE_DIM  # 24 + 25 = 49

EDGE_FEATURE_DIM: int = len(EDGE_KINDS) + 1  # +1 for "other"

_DOMAIN_INDEX = {"P": 0, "C": 1, "E": 2, "O": 3}
_DRIVE_INDEX = {"F1": 0, "F2": 1, "F3": 2, "F4": 3, "F5": 4, "F6": 5, "F7": 6}
_REGISTER_INDEX = {"T": 0, "A": 1, "f": 2, "E": 3}


def compile_to_graph(cas_expression: str) -> dict[str, Any]:
    """Parse a CAS expression string and return a flat graph dict for the encoder.

    The dict has the schema::

        {
            "nodes":         list of node attr dicts (from compiler diagram),
            "edges":         list of edge attr dicts (from compiler diagram),
            "node_features": list[list[float]] shape (n_nodes, NODE_FEATURE_DIM),
            "edge_features": list[list[float]] shape (n_edges, EDGE_FEATURE_DIM),
            "n_nodes":       int,
            "n_edges":       int,
        }

    On compile failure (invalid expression) an empty graph is returned so
    callers always get a usable dict without special-casing None.
    """
    try:
        from api.notation.compiler import compile_expression, build_diagram, empty_diagram
        result = compile_expression(cas_expression)
        if result.valid and result.ast is not None:
            diagram = build_diagram(result.ast)
        else:
            diagram = empty_diagram()
    except Exception:
        diagram = _empty_diagram_dict()

    nodes = list(diagram.get("nodes", []))
    edges = list(diagram.get("edges", []))

    node_features = [_node_feature_vector(n) for n in nodes]
    edge_features = [_edge_feature_vector(e) for e in edges]

    return {
        "nodes": nodes,
        "edges": edges,
        "node_features": node_features,
        "edge_features": edge_features,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
    }


def serialize_diagram_for_batch(
    graphs: list[dict[str, Any]],
    *,
    max_nodes: int = 32,
    max_edges: int = 128,
    device: str | torch.device | None = None,
) -> dict[str, torch.Tensor]:
    """Pack a list of graph dicts into padded batched tensors.

    Returns::

        {
            "node_features": FloatTensor (B, max_nodes, NODE_FEATURE_DIM),
            "edge_index":    LongTensor  (B, 2, max_edges),  # source/target node indices
            "edge_features": FloatTensor (B, max_edges, EDGE_FEATURE_DIM),
            "node_mask":     BoolTensor  (B, max_nodes),
            "edge_mask":     BoolTensor  (B, max_edges),
        }

    Node indices in ``edge_index`` are local (0-based within each graph).
    Out-of-range edges (after clipping to max_edges) are discarded.
    Padded positions have feature vectors of all zeros and mask=False.
    """
    batch_size = len(graphs)
    dev = torch.device(device) if device is not None else None

    node_features_batch = torch.zeros(batch_size, max_nodes, NODE_FEATURE_DIM, device=dev)
    edge_index_batch = torch.zeros(batch_size, 2, max_edges, dtype=torch.long, device=dev)
    edge_features_batch = torch.zeros(batch_size, max_edges, EDGE_FEATURE_DIM, device=dev)
    node_mask_batch = torch.zeros(batch_size, max_nodes, dtype=torch.bool, device=dev)
    edge_mask_batch = torch.zeros(batch_size, max_edges, dtype=torch.bool, device=dev)

    for b, graph in enumerate(graphs):
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        node_feats = graph.get("node_features", [])
        edge_feats = graph.get("edge_features", [])

        # Build id → local index map for edge encoding
        node_id_to_index: dict[str, int] = {
            node["id"]: i for i, node in enumerate(nodes)
        }

        n = min(len(nodes), max_nodes)
        for i in range(n):
            if i < len(node_feats):
                node_features_batch[b, i] = torch.tensor(
                    node_feats[i], dtype=torch.float32
                )
        node_mask_batch[b, :n] = True

        e_count = 0
        for j, edge in enumerate(edges):
            if e_count >= max_edges:
                break
            src_id = edge.get("source", "")
            tgt_id = edge.get("target", "")
            src_idx = node_id_to_index.get(src_id, -1)
            tgt_idx = node_id_to_index.get(tgt_id, -1)
            if src_idx < 0 or tgt_idx < 0 or src_idx >= max_nodes or tgt_idx >= max_nodes:
                continue
            edge_index_batch[b, 0, e_count] = src_idx
            edge_index_batch[b, 1, e_count] = tgt_idx
            if j < len(edge_feats):
                edge_features_batch[b, e_count] = torch.tensor(
                    edge_feats[j], dtype=torch.float32
                )
            edge_mask_batch[b, e_count] = True
            e_count += 1

    return {
        "node_features": node_features_batch,
        "edge_index": edge_index_batch,
        "edge_features": edge_features_batch,
        "node_mask": node_mask_batch,
        "edge_mask": edge_mask_batch,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _empty_diagram_dict() -> dict[str, Any]:
    return {"kind": "cas_diagram", "schema_version": "1.0",
            "layouts": [], "nodes": [], "edges": [], "containers": []}


def _node_kind_index(kind: str) -> int:
    try:
        return NODE_KINDS.index(kind)
    except ValueError:
        return len(NODE_KINDS)  # "other" bucket


def _edge_kind_index(kind: str) -> int:
    try:
        return EDGE_KINDS.index(kind)
    except ValueError:
        return len(EDGE_KINDS)  # "other" bucket


def _node_feature_vector(node: dict[str, Any]) -> list[float]:
    """Build a NODE_FEATURE_DIM float vector for one node dict."""
    vec = [0.0] * NODE_FEATURE_DIM

    # Node-kind one-hot (dims 0..NODE_KIND_DIM-1)
    vec[_node_kind_index(node.get("kind", ""))] = 1.0

    base = NODE_KIND_DIM  # = 24

    # Noetic one-hot (dims 24..33)
    operator = node.get("operator")
    if operator is not None:
        try:
            idx = int(operator)
            if 0 <= idx <= 9:
                vec[base + idx] = 1.0
        except (TypeError, ValueError):
            pass

    # Domain one-hot (dims 34..37)
    domain = node.get("domain")
    if domain is not None:
        idx = _DOMAIN_INDEX.get(str(domain))
        if idx is not None:
            vec[base + 10 + idx] = 1.0

    # Drive one-hot (dims 38..44)
    drive = node.get("drive")
    if drive is not None:
        idx = _DRIVE_INDEX.get(str(drive))
        if idx is not None:
            vec[base + 10 + 4 + idx] = 1.0

    # Register multi-hot (dims 45..48)
    register = node.get("register")
    if register is not None:
        regs = register if isinstance(register, (list, tuple)) else [register]
        for reg in regs:
            idx = _REGISTER_INDEX.get(str(reg))
            if idx is not None:
                vec[base + 10 + 4 + 7 + idx] = 1.0

    return vec


def _edge_feature_vector(edge: dict[str, Any]) -> list[float]:
    """Build an EDGE_FEATURE_DIM float vector for one edge dict."""
    vec = [0.0] * EDGE_FEATURE_DIM
    vec[_edge_kind_index(edge.get("kind", ""))] = 1.0
    return vec


__all__ = [
    "NODE_KINDS",
    "EDGE_KINDS",
    "NODE_KIND_DIM",
    "CAS_FEATURE_DIM",
    "NODE_FEATURE_DIM",
    "EDGE_FEATURE_DIM",
    "compile_to_graph",
    "serialize_diagram_for_batch",
]
