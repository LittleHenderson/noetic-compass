"""Shared paraphrase templates and slot-extraction logic.

The training-time augmentation set and the evaluation-time invariance test
must use **disjoint** template sets so a model trained on augmentation
templates is still being evaluated on held-out surface forms. Without that
separation, paraphrase-eval accuracy after augmented training would mostly
measure memorization of the augmentation templates, not surface-form
generalization.

Both ``evaluate_paraphrase_invariance.py`` and ``paraphrase_augmentation.py``
import their template sets from this module, and a property test
(``test_paraphrase_templates.py::test_train_eval_template_sets_are_disjoint``)
guards the disjointness invariant.
"""

from __future__ import annotations

import copy
from typing import Any


# Eval-time paraphrase templates. These are the canonical Session-43 set;
# moving them here is a structural refactor only — same surface strings.
EVAL_PARAPHRASE_TEMPLATES: tuple[str, ...] = (
    "Map this recoverable CAS slot reading into notation, then explain it briefly: {slots}.",
    "Please reconstruct the exact CAS expression from these stated slots: {slots}.",
    "As a CAS notation check, translate this slot list into the formal expression: {slots}.",
    "Given this recoverable structure, return the CAS notation and a concise explanation: {slots}.",
)


# Training-time augmentation templates. Disjoint from the eval set by
# construction — see test_train_eval_template_sets_are_disjoint. Each
# template carries the same conceptual ask ("convert slots to CAS notation")
# but with surface forms the eval will not test on, so the model is forced
# to learn what they have in common (the slot block) rather than memorize
# any one frame.
TRAINING_PARAPHRASE_TEMPLATES: tuple[str, ...] = (
    "Convert these CAS slots into formal notation: {slots}",
    "From the slot reading {slots}, write the CAS expression.",
    "What is the CAS notation for: {slots}?",
    "Render this as CAS notation: {slots}.",
    "Translate the following slot description to CAS notation: {slots}",
    "Given {slots}, what does the CAS expression look like?",
    "Output the CAS expression that matches: {slots}",
    "Encode the following into CAS form: {slots}.",
)


# Suffixes that can appear at the end of canonical Level 3 prompts and need
# to be stripped before re-templating, so the slot block is a clean payload.
KNOWN_SUFFIXES: tuple[str, ...] = (
    ". What notation should I use?",
    ". What is the precise notation?",
    ".",
)


def extract_recoverable_slots(prompt: str) -> str:
    """Extract the formal slot reading from a recoverable Level 3 prompt.

    Looks for the ``families:`` marker. Records that lack the marker
    (e.g., free-form prompts) round-trip the entire prompt unchanged so
    template wrapping still produces well-formed records.
    """

    marker = "families:"
    start = prompt.find(marker)
    if start < 0:
        return prompt.strip()
    slots = prompt[start:].strip()
    for suffix in KNOWN_SUFFIXES:
        if slots.endswith(suffix):
            slots = slots[: -len(suffix)].strip()
            break
    return slots


def apply_template(
    record: dict[str, Any],
    template: str,
    *,
    paraphrase_index: int,
    paraphrase_source: str,
) -> dict[str, Any]:
    """Return a deep copy of ``record`` with a templated prompt.

    Preserves all CAS target fields (``cas_expression``, ``bucket``,
    ``source_level2_id``, etc.) so the augmented record reuses the
    canonical's labels without modification. Modified fields:

      - ``user_prompt`` — re-templated with the slot block.
      - ``id`` — suffixed with ``::para{paraphrase_index}``.
      - ``base_id`` — set to the canonical record's ``id``.
      - ``paraphrase_index`` and ``paraphrase_source`` recorded for audit.
    """

    slots = extract_recoverable_slots(str(record.get("user_prompt") or ""))
    out = copy.deepcopy(record)
    out["base_id"] = record.get("id")
    out["paraphrase_index"] = paraphrase_index
    out["id"] = f"{record.get('id')}::para{paraphrase_index}"
    out["user_prompt"] = template.format(slots=slots)
    out["paraphrase_source"] = paraphrase_source
    return out


__all__ = [
    "EVAL_PARAPHRASE_TEMPLATES",
    "TRAINING_PARAPHRASE_TEMPLATES",
    "KNOWN_SUFFIXES",
    "extract_recoverable_slots",
    "apply_template",
]
