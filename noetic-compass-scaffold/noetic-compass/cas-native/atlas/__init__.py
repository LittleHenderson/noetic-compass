"""Idea Atlas — navigable map of the Idea-substrate of a CAS prediction.

The Idea Atlas is the second of two natural visual representations of a
CAS-Native prediction (the first being the compiler-produced notation /
diagram graph at ``api/notation/compiler.py``).

Where the diagram view renders the compiled CAS expression's *typed
graph structure* (NoeticCluster, StateSet, RelationCluster, recipe
graph, RPM chain), the Idea Atlas renders the *^0 / ^5 substrate*
(per CLAUDE.md authoritative Noetic definitions): the navigable map
of Ideas the prediction lit up (positive space) and the Ideas it
explicitly did not (negative space, via involution-pair shadows).

The two views are connected through a shared ``generation_id`` —
every CAS prediction emits a UUID; both the atlas and the diagram
reference the same UUID; the dashboard uses it to highlight
corresponding elements across the toggle.

Public surface
--------------

* :class:`IdeaNode` — atomic Idea entry in the atlas.
* :class:`IdeaEdge` — relationship between two Ideas in the atlas.
* :class:`IdeaAtlas` — the full navigable atlas for one prediction.
* :class:`GenerationTrace` — 1:1 plumbing record connecting prediction
  → atlas nodes → diagram nodes via a single ``generation_id``.
* :func:`prediction_to_atlas` — derive an :class:`IdeaAtlas` from a
  CAS-Native prediction dict.
* :func:`new_generation_id` — RFC-4122 UUID4 in canonical hex form.

Status: scaffold (2026-05-04). The data model is final; rendering and
dashboard wiring are downstream work — see
``docs/working/idea_atlas_spec_2026_05_04.md``.
"""

from .idea_atlas import (
    IdeaAtlas,
    IdeaEdge,
    IdeaNode,
    new_generation_id,
)
from .prediction_to_atlas import prediction_to_atlas
from .trace_mapping import GenerationTrace

__all__ = [
    "GenerationTrace",
    "IdeaAtlas",
    "IdeaEdge",
    "IdeaNode",
    "new_generation_id",
    "prediction_to_atlas",
]
