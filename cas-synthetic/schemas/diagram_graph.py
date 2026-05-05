"""Canonical-identity utilities for CAS compiler diagram dicts.

A compiler diagram has the shape produced by the notation compiler's
``build_diagram`` / ``CompilationArtifact.diagram()`` API::

    {
        "kind": "cas_diagram",
        "schema_version": "1.0",
        "layouts": [...],
        "nodes": [
            {"id": "state:P3", "kind": "state", "label": "P3",
             "role": "cognitive_state", ...},
            ...
        ],
        "edges": [
            {"id": "edge:1", "source": "state:P3", "target": "state:C3",
             "kind": "dependency", "directed": True, ...},
            ...
        ],
        "containers": [
            {"id": "container:Noetics", "kind": "noetic_cluster",
             "label": "Noetics", "contains": [...], ...},
            ...
        ],
    }

All four exported functions are pure — they do not mutate the input dicts and
carry no side-effects.  ``diagram_diff.py`` imports and reuses them; do not
inline equivalent logic there.
"""

from __future__ import annotations

import hashlib
import json
import re


# ---------------------------------------------------------------------------
# Axis extraction
# ---------------------------------------------------------------------------

def _parse_state_label(label: str) -> dict:
    """Parse a state-node label such as ``P3``, ``P3_F5``, ``P3_F5|A``.

    Returns a dict with keys ``domain``, ``noetic``, ``drive``, ``register``
    (any value may be ``None`` when absent from the label).  Returns an empty
    dict when the label does not match the expected state format.
    """
    m = re.match(r"^([PCEO])(\d)(?:_F(\d))?(?:[|](\S+))?$", label)
    if not m:
        return {}
    return {
        "domain": m.group(1),
        "noetic": int(m.group(2)),
        "drive": int(m.group(3)) if m.group(3) is not None else None,
        "register": m.group(4),
    }


def _parse_noetic_label(label: str) -> dict:
    """Parse a noetic-node label such as ``CO-3``."""
    m = re.match(r"^CO-(\d)$", label)
    if not m:
        return {}
    return {"noetic": int(m.group(1))}


def _parse_drive_label(label: str) -> dict:
    """Parse a drive-node label such as ``F3`` or ``F3^P``."""
    m = re.match(r"^F(\d)", label)
    if not m:
        return {}
    return {"drive": int(m.group(1))}


def extract_node_axes(node: dict) -> dict:
    """Extract CAS axis values (noetic, domain, drive, register) from a node.

    Checks for explicit metadata fields first (forward-compatible with diagram
    formats that carry axis data directly).  Falls back to label parsing for
    the three node kinds whose labels encode axes: ``state``, ``noetic``, and
    ``drive``.

    Returns a dict; any axis absent from the node is omitted entirely (not set
    to ``None``).  An empty dict means no parseable axis information is present.
    """
    # Explicit metadata takes priority (forward-compat with richer diagrams).
    axes: dict = {}
    for axis in ("noetic", "domain", "drive", "register"):
        if axis in node:
            axes[axis] = node[axis]
    if axes:
        return axes

    # Label-based fallback.
    kind = node.get("kind", "")
    label = node.get("label", "")
    if kind == "state":
        return {k: v for k, v in _parse_state_label(label).items() if v is not None}
    if kind == "noetic":
        return {k: v for k, v in _parse_noetic_label(label).items() if v is not None}
    if kind == "drive":
        return {k: v for k, v in _parse_drive_label(label).items() if v is not None}
    return {}


# ---------------------------------------------------------------------------
# Canonical key functions (exported, reused by diagram_diff.py)
# ---------------------------------------------------------------------------

def canonical_node_key(node: dict) -> str:
    """Stable identity key for a diagram node.

    Identity is ``(kind, role, label)`` packed as a colon-separated string.
    The ``id`` field is deliberately excluded: auto-generated IDs may differ
    across compiler runs for the same logical node.  Visual attributes such as
    ``color`` are also excluded — they do not affect structural identity.
    """
    kind = node.get("kind") or ""
    role = node.get("role") or ""
    label = node.get("label") or ""
    return f"{kind}:{role}:{label}"


def canonical_container_key(container: dict) -> str:
    """Stable identity key for a diagram container.

    Identity is ``(kind, label)`` — sufficient to distinguish containers across
    diagrams because each container kind+label pair is emitted at most once per
    compilation.
    """
    kind = container.get("kind") or ""
    label = container.get("label") or ""
    return f"{kind}:{label}"


# ---------------------------------------------------------------------------
# Internal helpers (used by canonical_graph_keys and diagram_diff.py)
# ---------------------------------------------------------------------------

def _build_id_to_canonical(nodes: list) -> dict:
    """Map each node's ``id`` string to its ``canonical_node_key``."""
    return {n.get("id", ""): canonical_node_key(n) for n in nodes}


def _canonical_edge_key(edge: dict, id_to_canonical: dict) -> str:
    """Stable identity key for an edge.

    Identity is ``(resolved_source, resolved_target, kind)``.  Source and
    target node IDs are resolved to canonical node keys so that the edge key
    remains stable across compilations.  The edge label (e.g. a coefficient
    value in a recipe) is intentionally excluded to keep structural identity
    independent of weight values; ``diagram_diff.py`` tracks weight changes
    through the axis-substitution layer.
    """
    source = id_to_canonical.get(edge.get("source", ""), edge.get("source", ""))
    target = id_to_canonical.get(edge.get("target", ""), edge.get("target", ""))
    kind = edge.get("kind") or ""
    return f"{source}|{target}|{kind}"


# ---------------------------------------------------------------------------
# Graph-level key sets
# ---------------------------------------------------------------------------

def canonical_graph_keys(diagram: dict) -> dict:
    """Return canonical key lists for all structural elements of a diagram.

    Returns::

        {
            "node_keys":      list[str],   # one entry per node
            "container_keys": list[str],   # one entry per container
            "edge_keys":      list[str],   # one entry per edge
        }

    Lists (not sets) are returned so callers can measure counts directly and
    convert to sets for set-diff operations themselves.
    """
    nodes = diagram.get("nodes") or []
    containers = diagram.get("containers") or []
    edges = diagram.get("edges") or []

    id_to_canonical = _build_id_to_canonical(nodes)

    return {
        "node_keys": [canonical_node_key(n) for n in nodes],
        "container_keys": [canonical_container_key(c) for c in containers],
        "edge_keys": [_canonical_edge_key(e, id_to_canonical) for e in edges],
    }


# ---------------------------------------------------------------------------
# Diagram summary
# ---------------------------------------------------------------------------

def diagram_summary(diagram: dict) -> dict:
    """Compact summary including structural counts and a SHA-256 graph hash.

    The graph hash is computed over a sorted, stable JSON serialisation of the
    canonical key sets, making it independent of node/edge emission order.
    Two diagrams that are structurally identical (same set of canonical keys)
    will produce the same hash even if internal IDs differ.

    Returns::

        {
            "node_count":      int,
            "container_count": int,
            "edge_count":      int,
            "layouts":         list[str],
            "graph_hash":      str,   # 64-char hex SHA-256
        }
    """
    keys = canonical_graph_keys(diagram)

    stable_payload = json.dumps(
        {
            "node_keys": sorted(keys["node_keys"]),
            "container_keys": sorted(keys["container_keys"]),
            "edge_keys": sorted(keys["edge_keys"]),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    graph_hash = hashlib.sha256(stable_payload.encode()).hexdigest()

    return {
        "node_count": len(keys["node_keys"]),
        "container_count": len(keys["container_keys"]),
        "edge_count": len(keys["edge_keys"]),
        "layouts": sorted(diagram.get("layouts") or []),
        "graph_hash": graph_hash,
    }
