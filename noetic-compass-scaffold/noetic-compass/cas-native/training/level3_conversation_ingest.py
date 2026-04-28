"""Torch-free helpers for ingesting Level 3 conversational SDG records."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


DOMAIN_TARGET_ORDER = ("P", "C", "E", "O")


def conversation_text(item: dict[str, Any], primary: str, fallback: str) -> str:
    """Read either legacy training text or Level 3 conversational text."""
    value = item.get(primary)
    if value is None:
        value = item.get(fallback)
    if value is None:
        value = item.get("text" if primary == "prompt" else "output")
    return str(value) if value is not None else ""


def domain_targets_as_list(value: Any) -> list[float] | None:
    """Normalize domain target mappings/lists to P,C,E,O list order."""
    if isinstance(value, dict):
        try:
            return [float(value[key]) for key in DOMAIN_TARGET_ORDER]
        except (KeyError, TypeError, ValueError):
            return None
    if isinstance(value, list):
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return None
    return None


def score_payload(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy and Level 3 soft labels into trainer score keys.

    Precedence when a record carries both legacy and Level 3 fields:

    - ``operator_scores`` and ``domain_scores`` are **overwritten** by
      ``soft_operator_targets`` and ``soft_domain_targets`` respectively.
      Level 3 soft targets are the richer signal (probability distributions
      vs one-hot), so they win when both are present.
    - ``domain_averages`` is preserved via ``setdefault``: an existing legacy
      value stays put; the soft-target list is only used to fill the slot
      when ``domain_averages`` is absent. This asymmetry is intentional so
      callers that already populated ``domain_averages`` (e.g. legacy
      pipeline outputs) aren't silently overridden.
    """
    scores = item.get("scores")
    cas_scores = dict(scores) if isinstance(scores, dict) else {}

    if "operator_scores" in item:
        cas_scores["operator_scores"] = item["operator_scores"]
    if "soft_operator_targets" in item:
        cas_scores["operator_scores"] = item["soft_operator_targets"]

    if "domain_scores" in item:
        cas_scores["domain_scores"] = item["domain_scores"]
    if "domain_averages" in item:
        cas_scores["domain_averages"] = item["domain_averages"]
    if "soft_domain_targets" in item:
        domain_targets = domain_targets_as_list(item["soft_domain_targets"])
        if domain_targets is not None:
            cas_scores["domain_scores"] = domain_targets
            cas_scores.setdefault("domain_averages", domain_targets)

    if "nccs" in item:
        cas_scores["nccs"] = item["nccs"]
    return cas_scores


def level3_ingestion_errors(item: dict[str, Any]) -> list[str]:
    """Return training-ingestion errors for one Level 3 record."""
    errors: list[str] = []
    if not conversation_text(item, "prompt", "user_prompt").strip():
        errors.append("missing prompt/user_prompt text")
    if not conversation_text(item, "response", "assistant_response").strip():
        errors.append("missing response/assistant_response text")
    if not str(item.get("cas_expression", "")).strip():
        errors.append("missing cas_expression")

    scores = score_payload(item)
    operator_scores = scores.get("operator_scores")
    if not isinstance(operator_scores, list) or len(operator_scores) != 10:
        errors.append("operator_scores/soft_operator_targets must be a length-10 list")
    domain_scores = scores.get("domain_scores")
    if not isinstance(domain_scores, list) or len(domain_scores) != 4:
        errors.append("domain_scores/soft_domain_targets must be a length-4 list")
    return errors


def summarize_level3_ingestion(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarize whether records are ready for CAS-Native data loading."""
    total = 0
    invalid = 0
    bucket_counts: Counter[str] = Counter()
    first_errors: list[dict[str, Any]] = []
    for index, item in enumerate(records):
        total += 1
        bucket_counts[str(item.get("bucket", "unknown"))] += 1
        errors = level3_ingestion_errors(item)
        if errors:
            invalid += 1
            if len(first_errors) < 10:
                first_errors.append(
                    {
                        "index": index,
                        "id": item.get("id"),
                        "errors": errors,
                    }
                )

    return {
        "total": total,
        "valid": total - invalid,
        "invalid": invalid,
        "bucket_counts": dict(bucket_counts),
        "first_errors": first_errors,
    }
