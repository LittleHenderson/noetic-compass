"""Training-time paraphrase augmentation.

Expands a list of canonical training records into a paraphrase-augmented
list, interleaving canonical and paraphrased forms for each base record.
Each paraphrase preserves every CAS target field; only ``user_prompt``,
``id``, ``base_id``, ``paraphrase_index``, and ``paraphrase_source`` differ.

The training templates are strictly disjoint from the eval templates
(see ``paraphrase_templates.py``); a model trained with augmentation here
is still evaluated on held-out surface forms.
"""

from __future__ import annotations

from typing import Any, Iterable

from .paraphrase_templates import (
    TRAINING_PARAPHRASE_TEMPLATES,
    apply_template,
)


PARAPHRASE_SOURCE_LABEL = "training_augmentation"


def paraphrase_train_record(
    record: dict[str, Any],
    *,
    paraphrase_index: int,
) -> dict[str, Any]:
    """Return a copy of ``record`` with a deterministic training paraphrase.

    Uses ``TRAINING_PARAPHRASE_TEMPLATES`` (disjoint from eval templates)
    indexed by ``paraphrase_index`` modulo the template count.
    """

    template = TRAINING_PARAPHRASE_TEMPLATES[
        paraphrase_index % len(TRAINING_PARAPHRASE_TEMPLATES)
    ]
    return apply_template(
        record,
        template,
        paraphrase_index=paraphrase_index,
        paraphrase_source=PARAPHRASE_SOURCE_LABEL,
    )


def expand_with_paraphrases(
    records: Iterable[dict[str, Any]],
    *,
    variants_per_record: int,
) -> list[dict[str, Any]]:
    """Expand records to (canonical + variants_per_record paraphrases) per base.

    Returns a flat list where each canonical record is followed by its
    ``variants_per_record`` paraphrases. ``variants_per_record == 0`` is
    a no-op pass-through (returns the records unchanged) so callers can
    use a single code path with a 0 default.
    """

    if variants_per_record < 0:
        raise ValueError(
            f"variants_per_record must be non-negative, got {variants_per_record}"
        )
    expanded: list[dict[str, Any]] = []
    for record in records:
        expanded.append(record)
        for index in range(variants_per_record):
            expanded.append(paraphrase_train_record(record, paraphrase_index=index))
    return expanded


__all__ = [
    "PARAPHRASE_SOURCE_LABEL",
    "paraphrase_train_record",
    "expand_with_paraphrases",
]
