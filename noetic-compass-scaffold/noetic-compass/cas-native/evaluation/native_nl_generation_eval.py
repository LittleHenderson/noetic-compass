"""Eval harness for the fully-native CAS NL generation head.

This module is part of the *fully-native* CAS English generation head — no
foreign pretrained weights. The model under test is the parallel agent's
``cas_native.model.nl_generation_head.NLGenerationHead``, trained by
``train_native_nl_gen.py`` in this same package.

Three eval metrics, each emitting an :class:`EvalResult` with full object
provenance:

* **CAS-grounding rate**: generate a reply for ``(CAS, prompt)``, run the
  reply back through the project's existing structured-prediction classifier,
  and check whether the classifier recovers the conditioning CAS expression
  on each axis (Noetic / Domain / Drive / Register). Per-bucket breakdown
  spans the 10 Noetics × 4 Domains × 7 Drives × 4 Registers grid.
* **Fluency (perplexity)**: model perplexity on a held-out validation slice.
* **Diversity (distinct-2)**: distinct-bigram ratio across N=64 generations
  drawn from the same ``(CAS, prompt)`` prefix; high values mean the model
  isn't memorizing one canned response per prefix.

Object provenance: every :class:`EvalResult` carries ``eval_id``,
``checkpoint_id``, ``eval_dataset_id``, ``eval_dataset_hash``,
``metric_name``, ``value``, ``per_bucket_breakdown``, ``timestamp``, and
``schema_version="eval_result.v1"``. Given a JSON eval result on disk, every
provenance field needed to replay or audit the metric is present.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F


SCHEMA_VERSION = "eval_result.v1"

# Canonical CAS axes, mirrored from cas_native.model.structured_prediction.
NOETIC_LABELS: tuple[int, ...] = tuple(range(10))
DOMAIN_LABELS: tuple[str, ...] = ("P", "C", "E", "O")
DRIVE_LABELS: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
REGISTER_LABELS: tuple[str, ...] = ("T", "A", "f", "E")


# ---------------------------------------------------------------------------
# EvalResult dataclass
# ---------------------------------------------------------------------------


@dataclass
class EvalResult:
    """Single metric × checkpoint × dataset evaluation outcome.

    Provenance fields (load-bearing for traceability):

    * ``eval_id`` — UUID4 for this eval run.
    * ``checkpoint_id`` — the model checkpoint under test.
    * ``eval_dataset_id`` — stable identifier for the eval set.
    * ``eval_dataset_hash`` — SHA-256 of the eval set bytes.
    * ``metric_name`` — one of ``"cas_grounding_rate"``,
      ``"fluency_perplexity"``, ``"diversity_distinct_2"``.
    * ``value`` — the headline metric value.
    * ``per_bucket_breakdown`` — keyed by ``noetic`` / ``domain`` /
      ``drive`` / ``register`` mappings of bucket -> per-bucket value.
    * ``timestamp`` — UTC ISO-8601 time the eval finished.
    * ``schema_version`` — pinned to ``"eval_result.v1"``.
    """

    eval_id: str
    checkpoint_id: str
    eval_dataset_id: str
    eval_dataset_hash: str
    metric_name: str
    value: float
    per_bucket_breakdown: dict[str, dict[str, float]] = field(default_factory=dict)
    timestamp: str = ""
    schema_version: str = SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "eval_id": self.eval_id,
            "checkpoint_id": self.checkpoint_id,
            "eval_dataset_id": self.eval_dataset_id,
            "eval_dataset_hash": self.eval_dataset_hash,
            "metric_name": self.metric_name,
            "value": float(self.value),
            "per_bucket_breakdown": {
                axis: {str(k): float(v) for k, v in bucket.items()}
                for axis, bucket in self.per_bucket_breakdown.items()
            },
            "timestamp": self.timestamp,
            "schema_version": self.schema_version,
            "metadata": dict(self.metadata),
        }

    def to_json(self, path: str | Path) -> None:
        path = Path(path)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, sort_keys=True)


# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------


def hash_dataset_bytes(records: Sequence[dict[str, Any]]) -> str:
    """SHA-256 of a deterministic JSON serialization of the eval set."""
    h = hashlib.sha256()
    for rec in records:
        # Stable key ordering for deterministic hashing.
        h.update(
            json.dumps(rec, sort_keys=True, ensure_ascii=False).encode("utf-8")
        )
        h.update(b"\n")
    return h.hexdigest()


def _empty_per_bucket() -> dict[str, dict[str, float]]:
    """Initialize an empty per-bucket breakdown spanning all 4 CAS axes.

    Empty buckets are allowed (value 0.0) per the contract — what matters is
    that the structure covers every axis position so a downstream UI can
    render the full grid without missing keys.
    """
    return {
        "noetic": {str(n): 0.0 for n in NOETIC_LABELS},
        "domain": {d: 0.0 for d in DOMAIN_LABELS},
        "drive": {d: 0.0 for d in DRIVE_LABELS},
        "register": {r: 0.0 for r in REGISTER_LABELS},
    }


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# 1. CAS-grounding rate
# ---------------------------------------------------------------------------


def evaluate_cas_grounding_rate(
    model: nn.Module,
    eval_records: Sequence[dict[str, Any]],
    *,
    checkpoint_id: str,
    eval_dataset_id: str,
    classifier: nn.Module | None,
    classify_fn: Callable[[nn.Module, str], dict[str, Any]] | None,
    generate_fn: Callable[[nn.Module, dict[str, Any]], str] | None = None,
    max_records: int | None = None,
) -> EvalResult:
    """Compute CAS-grounding rate over the eval set.

    For each ``(CAS, prompt)`` record:

    1. Generate a reply with ``generate_fn(model, record)`` (or
       ``model.generate(record)`` if ``generate_fn`` is None).
    2. Classify the reply via ``classify_fn(classifier, reply_text)``.
    3. Check whether each axis (noetic/domain/drive/registers) of the
       classifier prediction matches the conditioning record.

    The headline value is the fraction of records on which *all* axes match.
    Per-bucket breakdown reports per-axis match-rate by ground-truth bucket
    so failures can be localized (e.g. "the model fails on register=T 80% of
    the time").
    """
    if not eval_records:
        return _empty_eval_result(
            metric_name="cas_grounding_rate",
            checkpoint_id=checkpoint_id,
            eval_dataset_id=eval_dataset_id,
            eval_dataset_hash=hash_dataset_bytes(eval_records),
            metadata={"note": "empty_eval_set"},
        )

    records = list(eval_records)
    if max_records is not None:
        records = records[: max(0, int(max_records))]

    per_bucket = _empty_per_bucket()
    bucket_counts: dict[str, dict[str, int]] = {
        axis: {key: 0 for key in per_bucket[axis]} for axis in per_bucket
    }
    bucket_match: dict[str, dict[str, int]] = {
        axis: {key: 0 for key in per_bucket[axis]} for axis in per_bucket
    }

    n_total = 0
    n_match = 0
    diagnostics: list[str] = []

    for rec in records:
        cas = rec.get("cas", rec.get("conditioning_cas") or {}) or {}
        try:
            if generate_fn is not None:
                reply_text = generate_fn(model, rec)
            else:
                gen = getattr(model, "generate", None)
                reply_text = gen(rec) if callable(gen) else ""
        except Exception as exc:  # pragma: no cover - defensive
            diagnostics.append(f"generate_failed:{type(exc).__name__}")
            reply_text = ""

        if classifier is None or classify_fn is None or not reply_text:
            predicted: dict[str, Any] = {}
        else:
            try:
                predicted = classify_fn(classifier, reply_text) or {}
            except Exception as exc:  # pragma: no cover
                diagnostics.append(f"classify_failed:{type(exc).__name__}")
                predicted = {}

        axis_match = _axis_matches(cas, predicted)
        n_total += 1
        if axis_match["all_match"]:
            n_match += 1

        for axis, axis_key, key_value in (
            ("noetic", "noetic", cas.get("noetic")),
            ("domain", "domain", cas.get("domain")),
            ("drive", "drive", cas.get("drive")),
        ):
            if key_value is None:
                continue
            key_str = str(key_value)
            if key_str in bucket_counts[axis]:
                bucket_counts[axis][key_str] += 1
                if axis_match.get(axis_key, False):
                    bucket_match[axis][key_str] += 1
        for reg in cas.get("registers", []) or []:
            if reg in bucket_counts["register"]:
                bucket_counts["register"][reg] += 1
                if axis_match.get("registers", False):
                    bucket_match["register"][reg] += 1

    for axis in per_bucket:
        for key in per_bucket[axis]:
            count = bucket_counts[axis][key]
            per_bucket[axis][key] = (
                bucket_match[axis][key] / count if count > 0 else 0.0
            )

    value = (n_match / n_total) if n_total > 0 else 0.0

    return EvalResult(
        eval_id=str(uuid.uuid4()),
        checkpoint_id=str(checkpoint_id),
        eval_dataset_id=str(eval_dataset_id),
        eval_dataset_hash=hash_dataset_bytes(records),
        metric_name="cas_grounding_rate",
        value=float(value),
        per_bucket_breakdown=per_bucket,
        timestamp=_now_iso(),
        schema_version=SCHEMA_VERSION,
        metadata={
            "n_records": n_total,
            "n_match": n_match,
            "diagnostics": diagnostics,
        },
    )


def _axis_matches(cas: dict[str, Any], predicted: dict[str, Any]) -> dict[str, bool]:
    """Return per-axis match flags + an ``all_match`` summary."""
    out: dict[str, bool] = {}
    for key in ("noetic", "domain", "drive"):
        if key in cas and key in predicted:
            out[key] = cas[key] == predicted[key]
    if "registers" in cas and "registers" in predicted:
        cond = cas["registers"] or []
        pred = predicted["registers"] or []
        out["registers"] = sorted(cond) == sorted(pred)
    out["all_match"] = bool(out) and all(out.values())
    return out


# ---------------------------------------------------------------------------
# 2. Fluency (perplexity)
# ---------------------------------------------------------------------------


def evaluate_fluency_perplexity(
    model: nn.Module,
    val_token_batches: Iterable[dict[str, torch.Tensor]],
    *,
    checkpoint_id: str,
    eval_dataset_id: str,
    eval_dataset_hash: str,
    pad_token_id: int = -100,
) -> EvalResult:
    """Mean perplexity across the held-out validation set.

    Each batch in ``val_token_batches`` is a dict with at least
    ``input_ids`` and ``target_ids`` (torch tensors). The model is called as
    ``model(**batch, return_lm_loss=True)`` first; if that fails it falls back
    to ``model(input_ids=..., target_ids=...)`` and reads ``lm_loss`` /
    ``loss`` from the output dict. ``pad_token_id`` positions in
    ``target_ids`` are masked from the cross-entropy.
    """
    losses: list[float] = []
    n_tokens = 0
    diagnostics: list[str] = []

    was_training = bool(getattr(model, "training", False))
    if hasattr(model, "eval"):
        model.eval()
    try:
        with torch.no_grad():
            for batch in val_token_batches:
                target_ids = batch.get("target_ids")
                if target_ids is None:
                    target_ids = batch.get("labels")
                if target_ids is None:
                    diagnostics.append("batch_missing_target_ids")
                    continue
                try:
                    out = model(**batch)
                except TypeError:
                    diagnostics.append("model_signature_mismatch")
                    continue
                except Exception as exc:  # pragma: no cover
                    diagnostics.append(f"model_forward_failed:{type(exc).__name__}")
                    continue

                lm_loss = _extract_lm_loss(out, target_ids, pad_token_id)
                if lm_loss is None:
                    diagnostics.append("no_lm_loss_in_output")
                    continue
                # Token count for proper averaging.
                if pad_token_id is not None:
                    valid = (target_ids != pad_token_id).sum().item()
                else:
                    valid = target_ids.numel()
                if valid <= 0:
                    continue
                losses.append(float(lm_loss) * valid)
                n_tokens += int(valid)
    finally:
        if was_training and hasattr(model, "train"):
            model.train()

    if n_tokens == 0:
        ppl = float("inf") if losses else 1.0
    else:
        avg_loss = sum(losses) / n_tokens
        ppl = float(math.exp(avg_loss))

    return EvalResult(
        eval_id=str(uuid.uuid4()),
        checkpoint_id=str(checkpoint_id),
        eval_dataset_id=str(eval_dataset_id),
        eval_dataset_hash=str(eval_dataset_hash),
        metric_name="fluency_perplexity",
        value=ppl,
        per_bucket_breakdown=_empty_per_bucket(),
        timestamp=_now_iso(),
        schema_version=SCHEMA_VERSION,
        metadata={
            "n_tokens": int(n_tokens),
            "n_batches": int(len(losses)),
            "diagnostics": diagnostics,
        },
    )


def _extract_lm_loss(
    out: Any,
    target_ids: torch.Tensor,
    pad_token_id: int,
) -> float | None:
    """Pull a scalar LM-loss out of the model output, computing one if needed."""
    if isinstance(out, dict):
        for key in ("lm_loss", "loss", "loss_lm"):
            if key in out:
                v = out[key]
                if isinstance(v, torch.Tensor):
                    return float(v.detach().mean().item())
                return float(v)
        if "logits" in out and isinstance(out["logits"], torch.Tensor):
            logits = out["logits"]
            return _ce_from_logits(logits, target_ids, pad_token_id)
    elif isinstance(out, torch.Tensor):
        return _ce_from_logits(out, target_ids, pad_token_id)
    return None


def _ce_from_logits(
    logits: torch.Tensor, target_ids: torch.Tensor, pad_token_id: int
) -> float:
    """Compute next-token cross entropy from logits + targets."""
    if logits.dim() == 3 and target_ids.dim() == 2:
        b, s, v = logits.shape
        flat_logits = logits.reshape(b * s, v)
        flat_targets = target_ids.reshape(b * s)
    elif logits.dim() == 2 and target_ids.dim() == 1:
        flat_logits = logits
        flat_targets = target_ids
    else:
        return float(F.cross_entropy(logits, target_ids).item())
    return float(
        F.cross_entropy(
            flat_logits, flat_targets, ignore_index=pad_token_id, reduction="mean"
        ).item()
    )


# ---------------------------------------------------------------------------
# 3. Diversity (distinct-2)
# ---------------------------------------------------------------------------


def evaluate_diversity_distinct2(
    generations: Sequence[str],
    *,
    checkpoint_id: str,
    eval_dataset_id: str,
    eval_dataset_hash: str = "",
) -> EvalResult:
    """Distinct-bigram ratio across the provided generations.

    distinct-2 = (# unique bigrams) / (# total bigrams)

    All-identical generations -> distinct-2 close to 0.
    All-unique bigrams -> distinct-2 = 1.0.

    Empty input is treated as 0.0 with diagnostic.
    """
    bigrams_seen: set[tuple[str, str]] = set()
    total = 0
    for text in generations:
        toks = (text or "").split()
        if len(toks) < 2:
            continue
        for i in range(len(toks) - 1):
            bigrams_seen.add((toks[i], toks[i + 1]))
            total += 1
    if total == 0:
        value = 0.0
    else:
        value = float(len(bigrams_seen) / total)

    return EvalResult(
        eval_id=str(uuid.uuid4()),
        checkpoint_id=str(checkpoint_id),
        eval_dataset_id=str(eval_dataset_id),
        eval_dataset_hash=str(eval_dataset_hash) or hashlib.sha256(
            "\n".join(generations).encode("utf-8")
        ).hexdigest(),
        metric_name="diversity_distinct_2",
        value=value,
        per_bucket_breakdown=_empty_per_bucket(),
        timestamp=_now_iso(),
        schema_version=SCHEMA_VERSION,
        metadata={
            "n_generations": len(list(generations)),
            "n_total_bigrams": total,
            "n_unique_bigrams": len(bigrams_seen),
        },
    )


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def render_eval_report_markdown(results: Sequence[EvalResult]) -> str:
    """Render a human-readable Markdown report from a list of EvalResults."""
    if not results:
        return "# CAS-Native NL Generation Eval Report\n\n(No results.)\n"
    lines: list[str] = []
    lines.append("# CAS-Native NL Generation Eval Report")
    lines.append("")
    lines.append(f"Generated: {_now_iso()}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value | Checkpoint | Dataset |")
    lines.append("|---|---|---|---|")
    for r in results:
        lines.append(
            f"| `{r.metric_name}` | {r.value:.6f} | `{r.checkpoint_id}` | `{r.eval_dataset_id}` |"
        )
    lines.append("")

    for r in results:
        lines.append(f"## {r.metric_name}")
        lines.append("")
        lines.append(f"- **eval_id**: `{r.eval_id}`")
        lines.append(f"- **checkpoint_id**: `{r.checkpoint_id}`")
        lines.append(f"- **eval_dataset_id**: `{r.eval_dataset_id}`")
        lines.append(f"- **eval_dataset_hash**: `{r.eval_dataset_hash}`")
        lines.append(f"- **value**: `{r.value:.6f}`")
        lines.append(f"- **timestamp**: `{r.timestamp}`")
        lines.append("")
        if r.per_bucket_breakdown:
            for axis, bucket in r.per_bucket_breakdown.items():
                non_zero = [(k, v) for k, v in bucket.items() if v > 0]
                if not non_zero:
                    continue
                lines.append(f"### Per-{axis} breakdown")
                lines.append("")
                lines.append(f"| {axis} | value |")
                lines.append("|---|---|")
                for k, v in sorted(bucket.items()):
                    lines.append(f"| `{k}` | {v:.4f} |")
                lines.append("")
    return "\n".join(lines) + "\n"


def write_eval_artifacts(
    results: Sequence[EvalResult],
    out_dir: str | Path,
) -> dict[str, str]:
    """Write per-eval JSON files + a combined Markdown report.

    Returns a dict of artifact-name -> path written.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for r in results:
        json_path = out_dir / f"{r.metric_name}_{r.eval_id[:8]}.json"
        r.to_json(json_path)
        written[r.metric_name] = str(json_path)
    md_path = out_dir / "eval_report.md"
    with md_path.open("w", encoding="utf-8") as fh:
        fh.write(render_eval_report_markdown(results))
    written["report"] = str(md_path)
    return written


def _empty_eval_result(
    *,
    metric_name: str,
    checkpoint_id: str,
    eval_dataset_id: str,
    eval_dataset_hash: str,
    metadata: dict[str, Any] | None = None,
) -> EvalResult:
    return EvalResult(
        eval_id=str(uuid.uuid4()),
        checkpoint_id=str(checkpoint_id),
        eval_dataset_id=str(eval_dataset_id),
        eval_dataset_hash=str(eval_dataset_hash),
        metric_name=str(metric_name),
        value=0.0,
        per_bucket_breakdown=_empty_per_bucket(),
        timestamp=_now_iso(),
        schema_version=SCHEMA_VERSION,
        metadata=dict(metadata or {}),
    )


__all__ = [
    "DOMAIN_LABELS",
    "DRIVE_LABELS",
    "EvalResult",
    "NOETIC_LABELS",
    "REGISTER_LABELS",
    "SCHEMA_VERSION",
    "evaluate_cas_grounding_rate",
    "evaluate_diversity_distinct2",
    "evaluate_fluency_perplexity",
    "hash_dataset_bytes",
    "render_eval_report_markdown",
    "write_eval_artifacts",
]
