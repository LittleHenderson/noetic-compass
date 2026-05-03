"""Diagram-loop augmentation for the structured-prediction training harness.

Generates paraphrase records where the canonical CAS expression is compiled
into a typed graph and attached as ``prior_diagram``. At training time, the
ingest path routes records with ``prior_diagram`` through the GraphEncoder +
GraphTextFusion path instead of the text-only path.

This mirrors ``self_conditioning_augmentation.py`` (PR #4) in shape: the same
TRAINING_PARAPHRASE_TEMPLATES are used for surface-form variation, and the
canonical record is always included unchanged. The key difference is that the
prior carried in each augmented record is the **typed compiler graph** rather
than the CAS expression string.

Disjointness invariant: TRAINING_PARAPHRASE_TEMPLATES is disjoint from
EVAL_PARAPHRASE_TEMPLATES, same discipline as paraphrase_augmentation.py and
self_conditioning_augmentation.py.
"""

from __future__ import annotations

from typing import Any, Iterable

from .paraphrase_templates import TRAINING_PARAPHRASE_TEMPLATES, apply_template
from .diagram_serialization import compile_to_graph


DIAGRAM_LOOP_SOURCE_LABEL = "diagram_loop_augmentation"


def expand_with_diagram_loop_pairs(
    records: Iterable[dict[str, Any]],
    *,
    variants_per_record: int,
) -> list[dict[str, Any]]:
    """Expand records with diagram-loop paraphrase pairs.

    For each canonical record, generates ``variants_per_record`` paraphrase
    variants, each carrying the canonical's compiled CAS graph in the
    ``prior_diagram`` field. The canonical record itself is also included
    (unchanged, without ``prior_diagram``), so the total output length is
    ``len(records) * (1 + variants_per_record)``.

    ``variants_per_record == 0`` is a no-op pass-through — same convention as
    ``expand_with_paraphrases`` and ``expand_with_self_conditioning_pairs``.

    Each paraphrase record:
      - inherits all CAS target fields from the canonical (deepcopy via
        ``apply_template``)
      - has ``prior_diagram`` set to ``compile_to_graph(canonical_cas_expression)``
      - has its ``user_prompt`` wrapped in a training paraphrase template
      - has ``paraphrase_source`` = ``DIAGRAM_LOOP_SOURCE_LABEL``

    At training time, the training loop detects ``prior_diagram`` and routes
    the record through the GraphEncoder + GraphTextFusion path.

    Args:
        records:             iterable of canonical Level 3 records.
        variants_per_record: number of diagram-loop variants per canonical.
                             Must be >= 0.

    Returns:
        Flat list with canonical records interleaved with their variants.
    """
    if variants_per_record < 0:
        raise ValueError(
            f"variants_per_record must be non-negative, got {variants_per_record}"
        )
    expanded: list[dict[str, Any]] = []
    for record in records:
        expanded.append(record)
        if variants_per_record == 0:
            continue
        canonical_cas = str(record.get("cas_expression") or "")
        prior_diagram = compile_to_graph(canonical_cas)
        for index in range(variants_per_record):
            template = TRAINING_PARAPHRASE_TEMPLATES[
                index % len(TRAINING_PARAPHRASE_TEMPLATES)
            ]
            para = apply_template(
                record,
                template,
                paraphrase_index=index,
                paraphrase_source=DIAGRAM_LOOP_SOURCE_LABEL,
            )
            para["prior_diagram"] = prior_diagram
            expanded.append(para)
    return expanded


__all__ = [
    "DIAGRAM_LOOP_SOURCE_LABEL",
    "expand_with_diagram_loop_pairs",
]
