"""Diagram serialization utilities for the CAS diagram-loop lever.

``compile_to_graph`` converts a CAS expression string into a graph object
suitable for use as a prior in the diagram-loop model path.
``serialize_diagram_for_batch`` prepares a list of such graphs for batched
model inference.

These functions are the ONLY sanctioned entry points for building graph priors
in the eval and training paths.  The honest eval invariant requires that every
call to ``compile_to_graph`` receives a model-predicted CAS expression string,
never a ground-truth ``cas_expression`` field from an eval record.

IMPLEMENTATION NOTE: this is a minimal stub.  The real implementation will
replace the stub dicts with proper graph tensor structures once the
diagram-loop model architecture is finalised.  The stub is correct with
respect to the empty-graph contract: ``compile_to_graph("")`` and
``compile_to_graph`` on any invalid expression both return ``None`` (treated
as an empty graph downstream, producing zero-attention behaviour).
"""

from __future__ import annotations

import re
from typing import Any


# Minimal graph dict schema.  Fields are placeholders; the real impl will
# replace them with DGL / PyG tensors or similar.
_EMPTY_GRAPH: dict[str, Any] = {"nodes": [], "edges": [], "expression": ""}

# Loose CAS expression pattern — any string with at least one ^ operator token.
_CAS_PATTERN = re.compile(r"\^[0-9]")


def compile_to_graph(cas_expression: str) -> dict[str, Any] | None:
    """Compile a CAS expression string into a minimal graph dict.

    Returns ``None`` for empty or syntactically trivial strings, which callers
    treat as an empty / zero-attention graph.  Never raises on bad input.

    Args:
        cas_expression: A model-predicted CAS expression string.  This must
            NOT be the ground-truth ``cas_expression`` from an eval record.

    Returns:
        A graph dict with ``nodes``, ``edges``, and ``expression`` keys, or
        ``None`` if the input is empty / un-parseable.
    """
    if not cas_expression or not isinstance(cas_expression, str):
        return None
    stripped = cas_expression.strip()
    if not stripped or not _CAS_PATTERN.search(stripped):
        return None
    return {
        "nodes": _extract_nodes(stripped),
        "edges": [],
        "expression": stripped,
    }


def serialize_diagram_for_batch(
    graphs: list[dict[str, Any] | None],
    *,
    device: str = "cpu",
) -> dict[str, Any] | None:
    """Prepare a list of graph dicts for batched model inference.

    Returns ``None`` when all graphs are ``None`` (zero-attention fallback).
    Otherwise returns a minimal batch dict with an ``expressions`` list and a
    ``valid_mask`` boolean list indicating which positions have real graphs.

    Args:
        graphs: One graph per record in the batch.  ``None`` entries are
            treated as zero-attention positions.
        device: Target device string (ignored by this stub; included for
            interface compatibility with the real implementation).
    """
    if not graphs:
        return None
    valid_mask = [g is not None for g in graphs]
    if not any(valid_mask):
        return None
    return {
        "expressions": [
            (g["expression"] if g is not None else "") for g in graphs
        ],
        "valid_mask": valid_mask,
        "device": device,
    }


def _extract_nodes(expression: str) -> list[str]:
    """Extract operator tokens from a CAS expression for stub node list."""
    return _CAS_PATTERN.findall(expression)


__all__ = ["compile_to_graph", "serialize_diagram_for_batch"]
