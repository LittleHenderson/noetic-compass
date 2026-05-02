"""Per-eval token-source provenance summary.

Reports how many tokens at eval time carry signal-bearing CAS structure
(``LEXICON`` or ``CAS_NOTATION``) vs fall to neutral fallback. The signal
fraction upper-bounds what the encoder can learn from per-token
``cas_signature`` features alone — a low signal fraction with high
all-heads-exact strongly suggests the model is relying on something
other than per-token CAS structure (e.g., template memorization).

Used by:

  - ``cas-native/training/train_structured_prediction.py`` — every eval
    pass attaches a provenance block to its manifest.
  - ``cas-native/training/diagnose_lexicon_coverage.py`` — standalone
    coverage diagnostic against canonical + paraphrase eval sets.

Both consumers compute provenance from the same `summarize_token_provenance`
function so manifest blocks and standalone reports are directly comparable.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Sequence

from .structured_token import StructuredToken


SOURCE_LABELS: tuple[str, ...] = ("LEXICON", "CAS_NOTATION", "LEARNED", "FALLBACK")
SIGNAL_BEARING_LABELS: frozenset[str] = frozenset({"LEXICON", "CAS_NOTATION"})


def summarize_token_provenance(
    token_sequences: Sequence[Sequence[StructuredToken]],
    records: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate per-token sources into overall + per-bucket breakdown.

    ``records`` is optional. When supplied it must have the same length as
    ``token_sequences`` — element ``records[i]`` is the source record for
    ``token_sequences[i]``. Per-bucket grouping uses ``record["bucket"]``;
    records without a bucket field are grouped under ``"unknown"``.

    Without ``records`` all sequences are grouped under ``"unknown"`` and
    only the overall numbers are meaningful.
    """

    if records is not None and len(records) != len(token_sequences):
        raise ValueError(
            f"records length {len(records)} does not match "
            f"token_sequences length {len(token_sequences)}"
        )

    overall: Counter[str] = Counter()
    total_tokens = 0
    total_signal = 0
    by_bucket: dict[str, dict[str, Any]] = defaultdict(_new_bucket_acc)

    for idx, sequence in enumerate(token_sequences):
        bucket = "unknown"
        if records is not None:
            bucket = str(records[idx].get("bucket") or "unknown")
        seq_total = 0
        seq_signal = 0
        for token in sequence:
            label = token.source.name
            overall[label] += 1
            seq_total += 1
            if label in SIGNAL_BEARING_LABELS:
                seq_signal += 1
            by_bucket[bucket]["by_source"][label] += 1
        total_tokens += seq_total
        total_signal += seq_signal
        by_bucket[bucket]["n_records"] += 1
        by_bucket[bucket]["total_tokens"] += seq_total
        by_bucket[bucket]["total_signal"] += seq_signal

    return {
        "n_records": len(token_sequences),
        "total_tokens": total_tokens,
        "total_signal_bearing": total_signal,
        "overall_signal_fraction": _frac(total_signal, total_tokens),
        "by_source": {label: int(overall.get(label, 0)) for label in SOURCE_LABELS},
        "by_source_fraction": {
            label: _frac(overall.get(label, 0), total_tokens) for label in SOURCE_LABELS
        },
        "by_bucket": {
            bucket: {
                "n_records": data["n_records"],
                "total_tokens": data["total_tokens"],
                "total_signal_bearing": data["total_signal"],
                "signal_fraction": _frac(data["total_signal"], data["total_tokens"]),
                "by_source": {
                    label: int(data["by_source"].get(label, 0))
                    for label in SOURCE_LABELS
                },
                "by_source_fraction": {
                    label: _frac(data["by_source"].get(label, 0), data["total_tokens"])
                    for label in SOURCE_LABELS
                },
            }
            for bucket, data in sorted(by_bucket.items())
        },
    }


def _new_bucket_acc() -> dict[str, Any]:
    return {
        "n_records": 0,
        "total_tokens": 0,
        "total_signal": 0,
        "by_source": Counter(),
    }


def _frac(num: int, denom: int) -> float:
    return num / denom if denom else 0.0


__all__ = [
    "SOURCE_LABELS",
    "SIGNAL_BEARING_LABELS",
    "summarize_token_provenance",
]
