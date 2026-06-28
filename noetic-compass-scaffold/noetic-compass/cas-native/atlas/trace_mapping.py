"""1:1 trace plumbing — connect a prediction to its atlas + diagram.

A :class:`GenerationTrace` is the load-bearing record. It carries:

* A unique ``generation_id`` (shared by prediction, atlas, diagram).
* The full prediction dict.
* The rendered CAS expression.
* The atlas node ids that resulted from this prediction.
* The diagram node ids (when known) that this prediction's CAS expression
  compiled into.

The trace is what enables the dashboard's Atlas ↔ Diagram toggle to
preserve selection: when a user clicks a node in either view, the
dashboard finds the trace by ``generation_id``, looks up the
corresponding ids in the other view, and highlights them on toggle.

Storage (out of scope for the scaffold):

* In-memory: a :class:`TraceStore` keyed by ``generation_id`` is fine for
  ``cas chat`` and the demo dashboard.
* Persistent: when the dashboard backend is wired up, traces will be
  written to a key/value store (Redis or sqlite) on the same call that
  emits the prediction. The :class:`GenerationTrace` JSON shape is the
  wire format.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Mapping

from .idea_atlas import IdeaAtlas


# ---------------------------------------------------------------------------
# GenerationTrace
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GenerationTrace:
    """1:1 mapping record connecting a CAS prediction to its visualizations.

    Each user turn (or one-shot ``cas predict`` call) emits one trace.
    The trace travels with the prediction through the system:

    * The Python predictor returns ``(prediction, GenerationTrace)``.
    * ``cas chat`` and ``cas predict`` print the ``generation_id`` so the
      user can look it up in the dashboard later.
    * The dashboard fetches ``GET /trace/<generation_id>`` to get the
      atlas + diagram bundle.
    """

    generation_id: str
    timestamp_ms: int
    user_input: str
    prediction: dict[str, Any]
    cas_expression: str
    atlas_node_ids: tuple[str, ...]
    diagram_node_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.generation_id, str) or not self.generation_id:
            raise ValueError(
                "GenerationTrace.generation_id must be a non-empty string"
            )
        if not isinstance(self.timestamp_ms, int):
            raise TypeError(
                f"GenerationTrace.timestamp_ms must be int, got "
                f"{type(self.timestamp_ms).__name__}"
            )
        if not isinstance(self.user_input, str):
            raise TypeError(
                "GenerationTrace.user_input must be str, got "
                f"{type(self.user_input).__name__}"
            )
        if not isinstance(self.prediction, Mapping):
            raise TypeError(
                "GenerationTrace.prediction must be a mapping, got "
                f"{type(self.prediction).__name__}"
            )
        if not isinstance(self.cas_expression, str):
            raise TypeError(
                "GenerationTrace.cas_expression must be str, got "
                f"{type(self.cas_expression).__name__}"
            )

        if not isinstance(self.atlas_node_ids, tuple):
            object.__setattr__(self, "atlas_node_ids", tuple(self.atlas_node_ids))
        if not isinstance(self.diagram_node_ids, tuple):
            object.__setattr__(
                self, "diagram_node_ids", tuple(self.diagram_node_ids)
            )

        # Defensive copy for prediction + metadata.
        object.__setattr__(self, "prediction", dict(self.prediction))
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def has_diagram(self) -> bool:
        """True iff the trace has been merged with a compiler-diagram result."""
        return bool(self.diagram_node_ids)

    def with_diagram(self, diagram_node_ids: Iterable[str]) -> "GenerationTrace":
        """Return a copy with diagram node ids attached.

        Used when the dashboard backend compiles the CAS expression *after*
        the prediction (which is normal — the predictor emits the prediction
        first, the compiler runs second).
        """
        return replace(self, diagram_node_ids=tuple(diagram_node_ids))

    def with_metadata(self, **updates: Any) -> "GenerationTrace":
        merged = {**self.metadata, **updates}
        return replace(self, metadata=merged)

    # ---- Serialization ----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation_id": self.generation_id,
            "timestamp_ms": self.timestamp_ms,
            "user_input": self.user_input,
            "prediction": dict(self.prediction),
            "cas_expression": self.cas_expression,
            "atlas_node_ids": list(self.atlas_node_ids),
            "diagram_node_ids": list(self.diagram_node_ids),
            "metadata": dict(self.metadata),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "GenerationTrace":
        return cls(
            generation_id=data["generation_id"],
            timestamp_ms=int(data["timestamp_ms"]),
            user_input=data["user_input"],
            prediction=dict(data["prediction"]),
            cas_expression=data["cas_expression"],
            atlas_node_ids=tuple(data.get("atlas_node_ids") or ()),
            diagram_node_ids=tuple(data.get("diagram_node_ids") or ()),
            metadata=dict(data.get("metadata") or {}),
        )

    @classmethod
    def from_json(cls, text: str) -> "GenerationTrace":
        return cls.from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# Construction helpers
# ---------------------------------------------------------------------------


def trace_from_atlas(
    *,
    atlas: IdeaAtlas,
    user_input: str,
    timestamp_ms: int | None = None,
    diagram_node_ids: Iterable[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> GenerationTrace:
    """Build a :class:`GenerationTrace` directly from an :class:`IdeaAtlas`.

    Convenience constructor used at the boundary between the predictor
    (which has the prediction + atlas) and the trace store (which wants
    a single object). The atlas is the source of ``atlas_node_ids``,
    ``cas_expression``, and ``generation_id``.
    """
    if timestamp_ms is None:
        timestamp_ms = int(time.time() * 1000)

    prediction_dict = atlas.metadata.get("prediction") or {}
    # Normalize tuples → lists so round-tripping through JSON is stable.
    prediction_dict = {
        k: list(v) if isinstance(v, tuple) else v
        for k, v in dict(prediction_dict).items()
    }

    return GenerationTrace(
        generation_id=atlas.generation_id,
        timestamp_ms=timestamp_ms,
        user_input=user_input,
        prediction=prediction_dict,
        cas_expression=atlas.cas_expression,
        atlas_node_ids=tuple(n.id for n in atlas.nodes),
        diagram_node_ids=tuple(diagram_node_ids),
        metadata=dict(metadata or {}),
    )


# ---------------------------------------------------------------------------
# Diagram bridge — atlas ↔ diagram node-id correspondence
# ---------------------------------------------------------------------------


def correspond_atlas_to_diagram(
    atlas: IdeaAtlas,
    diagram_nodes: Iterable[Mapping[str, Any]],
) -> dict[str, list[str]]:
    """Build an atlas-id → diagram-id-list correspondence map.

    The compiler diagram (per ``api/notation/compiler.py`` ≈ line 5045)
    emits a graph of ``DiagramNode`` records carrying their own ids. Where
    an atlas node and a diagram node represent *the same CAS primitive*
    (same noetic / domain / drive / register), they correspond — the
    dashboard highlights both when a user clicks either.

    The match heuristic is keyed on ``(noetic, domain, drive, register)``.
    Diagram nodes that don't carry these attributes (e.g. layout-only
    container boxes) are skipped. Atlas-only nodes (involution shadows,
    Ω targets, cluster stubs) end up with no diagram-side correspondence
    and are surfaced as "atlas-only" in the dashboard tooltip.

    Parameters
    ----------
    atlas
        The :class:`IdeaAtlas` to anchor the correspondence on.
    diagram_nodes
        Iterable of ``DiagramNode``-like dicts. Each dict is expected to
        carry: ``id`` (str), and optional ``noetic``, ``domain``, ``drive``,
        ``register`` keys. Other keys are ignored.

    Returns
    -------
    dict[str, list[str]]
        Mapping of ``atlas_node_id`` → list of corresponding ``diagram_id``s.
        Empty list = no correspondence found.
    """
    diagram_by_key: dict[tuple[str, str | None, str | None, str | None], list[str]] = {}
    for diag in diagram_nodes:
        key = (
            diag.get("noetic", ""),
            diag.get("domain"),
            diag.get("drive"),
            diag.get("register"),
        )
        if not key[0]:
            continue  # diagram node has no Noetic; skip
        diagram_by_key.setdefault(key, []).append(str(diag["id"]))

    correspondence: dict[str, list[str]] = {}
    for node in atlas.nodes:
        key = (node.noetic, node.domain, node.drive, node.register)
        correspondence[node.id] = list(diagram_by_key.get(key, []))
    return correspondence


__all__ = [
    "GenerationTrace",
    "correspond_atlas_to_diagram",
    "trace_from_atlas",
]
