"""Canonical graph identity scheme for CAS diagram comparison.

Provides ``canonical_graph_keys``, the graph identity primitive consumed by
the stub in ``evaluate_cross_channel_consistency.py`` and the future
``diagram_diff.py`` utility (feature/diagram-diff-utility).

Diagram format matches the output of ``build_diagram`` /
``CompilationResult.diagram`` in ``api/notation/compiler.py``:

    {
        "kind": "cas_diagram",
        "schema_version": "1.0",
        "layouts": [...],
        "nodes": [{"id": "...", "kind": "...", "label": "...", ...}, ...],
        "edges": [{"id": "...", "source": "...", "target": "...", "kind": "...", ...}, ...],
        "containers": [...],
    }
"""

from __future__ import annotations

from typing import Any


def canonical_graph_keys(diagram: dict[str, Any]) -> frozenset[str]:
    """Return a frozenset of canonical string keys representing a diagram's structural identity.

    Node key format:  ``"node:{kind}:{label}"``
    Edge key format:  ``"edge:{kind}:{src_label}:{tgt_label}"``

    Source/target labels are resolved by looking up node IDs in the nodes list,
    so the keys are stable across different serialisation runs that may assign
    different ephemeral edge IDs.

    Container nodes are intentionally excluded — they are structural groupings
    (e.g. meta-set boxes) rather than identity-bearing cognitive primitives.

    Empty diagrams (no nodes, no edges) return ``frozenset()``.  Two empty
    diagrams are therefore considered identical, which is the correct behaviour
    for comparing two failed or no-content compilations.
    """
    nodes: list[dict[str, Any]] = diagram.get("nodes", [])
    edges: list[dict[str, Any]] = diagram.get("edges", [])

    id_to_label: dict[str, str] = {
        str(node["id"]): str(node.get("label", ""))
        for node in nodes
        if "id" in node
    }

    keys: set[str] = set()
    for node in nodes:
        kind = str(node.get("kind", ""))
        label = str(node.get("label", ""))
        keys.add(f"node:{kind}:{label}")

    for edge in edges:
        kind = str(edge.get("kind", ""))
        src_id = str(edge.get("source", ""))
        tgt_id = str(edge.get("target", ""))
        src_label = id_to_label.get(src_id, src_id)
        tgt_label = id_to_label.get(tgt_id, tgt_id)
        keys.add(f"edge:{kind}:{src_label}:{tgt_label}")

    return frozenset(keys)
