"""Serialization helper for self-conditioning paraphrase records.

A self-conditioning record carries the canonical CAS expression in
``prior_cas_state`` so the model can be conditioned on its own canonical
prediction during the paraphrase forward pass. This module provides the
single serialization function that prepends the prior block to the query
prompt before tokenization.

Format:
    [PRIOR] {prior_cas_state}
    [QUERY] {user_prompt}

The ``[PRIOR]`` and ``[QUERY]`` delimiter tokens are new vocabulary entries
that appear in every self-conditioning training record. The CAS tokens in
the prior block (``^n``, ``^D``, ``|R``, ``_{Fk}``) are already handled by
the structured-token tokenizer's CAS-axis-aware path.
"""

from __future__ import annotations

from typing import Any


def serialize_prior_cas_state(record: dict[str, Any]) -> str:
    """Return the full tokenizer-input string for a self-conditioning record.

    Expects ``record['prior_cas_state']`` (the canonical CAS expression) and
    ``record['user_prompt']`` (the paraphrase query). Returns the
    ``[PRIOR] ... \\n[QUERY] ...`` formatted string that is passed to the
    tokenizer in place of the raw ``user_prompt``.

    Raises ``KeyError`` if ``prior_cas_state`` is not present in the record,
    so callers should guard with ``record.get('prior_cas_state')`` before
    calling this function.
    """

    prior = record["prior_cas_state"]
    query = str(record.get("user_prompt") or "")
    return f"[PRIOR] {prior}\n[QUERY] {query}"


__all__ = ["serialize_prior_cas_state"]
