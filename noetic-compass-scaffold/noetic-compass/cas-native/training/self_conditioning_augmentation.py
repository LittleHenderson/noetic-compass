"""Self-conditioning augmentation for the structured-prediction training harness.

Generates paraphrase records where the canonical CAS expression is attached as
a ``prior_cas_state`` field. At tokenization time the ingest path prepends this
as a ``[PRIOR]`` block so the model can learn to anchor its content-axis
predictions on the canonical answer when it is available.

Paraphrase surface forms are drawn from ``TRAINING_PARAPHRASE_TEMPLATES``,
which is disjoint from ``EVAL_PARAPHRASE_TEMPLATES`` — the same discipline
enforced by ``paraphrase_augmentation.py``. This module does NOT merge or
duplicate the standard-paraphrase augmentation; it is a separate expansion
step layered on top.
"""

from __future__ import annotations

from typing import Any, Iterable

from .paraphrase_templates import TRAINING_PARAPHRASE_TEMPLATES, apply_template


SELF_CONDITIONING_SOURCE_LABEL = "self_conditioning_augmentation"


def expand_with_self_conditioning_pairs(
    records: Iterable[dict[str, Any]],
    *,
    variants_per_record: int,
) -> list[dict[str, Any]]:
    """Expand records with self-conditioning paraphrase pairs.

    For each canonical record, generates ``variants_per_record`` paraphrase
    variants, each carrying the canonical's ``cas_expression`` in the
    ``prior_cas_state`` field. The canonical record itself is also included
    (unchanged, without ``prior_cas_state``), so the total output length is
    ``len(records) * (1 + variants_per_record)``.

    ``variants_per_record == 0`` is a no-op pass-through — same convention as
    ``expand_with_paraphrases``.

    Each paraphrase record:
      - inherits all CAS target fields from the canonical (deepcopy via
        ``apply_template``)
      - has ``prior_cas_state`` set to the canonical's ``cas_expression``
      - has its ``user_prompt`` wrapped in a training paraphrase template
      - has ``paraphrase_source`` = ``SELF_CONDITIONING_SOURCE_LABEL``

    At tokenization time, ``get_effective_prompt`` in
    ``structured_prediction_ingest`` detects the ``prior_cas_state`` field
    and prepends the ``[PRIOR] ... \\n[QUERY] ...`` block automatically.
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
        for index in range(variants_per_record):
            template = TRAINING_PARAPHRASE_TEMPLATES[
                index % len(TRAINING_PARAPHRASE_TEMPLATES)
            ]
            para = apply_template(
                record,
                template,
                paraphrase_index=index,
                paraphrase_source=SELF_CONDITIONING_SOURCE_LABEL,
            )
            para["prior_cas_state"] = canonical_cas
            expanded.append(para)
    return expanded


__all__ = [
    "SELF_CONDITIONING_SOURCE_LABEL",
    "expand_with_self_conditioning_pairs",
]
