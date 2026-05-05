"""Per-token generation trace surface for the fully-native CAS NL generation head.

This module extends the Mode 7 patterns established in ``live_capture.py`` to
the *generative* path. While ``live_capture.py`` traces a single forward pass
of the structured-prediction classifier, this module traces an autoregressive
``NLGenerationHead.generate(...)`` call and bundles its result with the extra
provenance + retrieval surfaces required for a load-bearing trace artifact:

* The model agent's :class:`cas_native.model.nl_generation_head.GenerationTrace`
  carries the per-token decoder trace (token steps, attention summaries,
  per-layer activation L2 norms, the model code version + weights SHA,
  ``cas_conditioning_repr`` for the CAS prefix the model conditioned on).
* This module's :class:`GenerationTraceCapture` wraps that with the
  trace-side provenance fields the eval/training pipeline relies on:
  ``trace_id``, ``model_checkpoint_id``, ``created_at``, the nearest-neighbor
  lookup against training data, and the live CAS-grounding score.

Object traceability is load-bearing:

* Every captured trace carries ``trace_id``, ``schema_version``,
  ``model_checkpoint_id``, and ``created_at``. Given a trace artifact, the
  reader knows *which* checkpoint produced it.
* Hooks installed by either the model agent's ``generate`` or this module
  are removed via ``try/finally``; two consecutive captures must not leak
  hook handles. This is verified by
  ``test_no_leaks_across_two_consecutive_captures``.

Public surface:

* :class:`GenerationTraceCapture` — wrapper bundling the model's trace plus
  trace-side provenance. Re-exported as ``GenerationTrace`` so callers using
  ``from cas_native.trace.generation_trace import GenerationTrace`` see the
  trace package's authoritative wrapper.
* :class:`TokenStep` — re-export of the model agent's ``TokenStep`` so
  callers can construct steps for tests without importing the model module.
* :func:`capture_generation_trace` — main entrypoint.
* :class:`NearestNeighborIndex` — minimal cosine-similarity index over the
  bottleneck embedding space, JSON-loadable.
* :func:`live_cas_grounding_score` — runs the generated reply back through
  the project's structured-prediction classifier and returns whether the
  classifier recovers the conditioning CAS expression.

Imports from the parallel agent's scope:

* ``cas_native.model.nl_generation_head.NLGenerationHead``
* ``cas_native.model.nl_generation_head.GenerationTrace`` (model's class)
* ``cas_native.model.nl_generation_head.TokenStep``

If those imports fail (parallel agent not yet shipped), this module falls
back to local skeletons so downstream tests still construct a valid trace.
"""

from __future__ import annotations

import json
import math
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import torch
import torch.nn as nn


# ---------------------------------------------------------------------------
# Soft-import the model agent's contract types. Fall back to skeletons if the
# parallel agent has not yet shipped them.
# ---------------------------------------------------------------------------

try:  # pragma: no cover - covered indirectly by both branches
    from cas_native.model.nl_generation_head import (  # type: ignore[import-not-found]
        GenerationTrace as _ModelGenerationTrace,
        TokenStep as _ModelTokenStep,
    )
    _MODEL_TYPES_AVAILABLE = True
except Exception:  # pragma: no cover
    _MODEL_TYPES_AVAILABLE = False

    @dataclass(frozen=True)
    class _ModelTokenStep:  # type: ignore[no-redef]
        """Skeleton TokenStep used until the model agent ships the real one.

        The real class is owned by ``cas_native.model.nl_generation_head``.
        This skeleton matches the documented contract (token id, str, attention
        summaries, per-layer activation L2 norms, sampling mode) so downstream
        code can be written and tested before the model agent's class is on
        disk.
        """

        position: int = 0
        token_id: int = 0
        token_str: str | None = None
        attn_to_cas_prefix: tuple[float, ...] = ()
        attn_to_prior_tokens: tuple[float, ...] = ()
        layer_activation_l2: tuple[float, ...] = ()
        selected_via: str = "argmax"

        def to_dict(self) -> dict[str, Any]:
            return {
                "position": int(self.position),
                "token_id": int(self.token_id),
                "token_str": self.token_str,
                "attn_to_cas_prefix": [float(v) for v in self.attn_to_cas_prefix],
                "attn_to_prior_tokens": [float(v) for v in self.attn_to_prior_tokens],
                "layer_activation_l2": [float(v) for v in self.layer_activation_l2],
                "selected_via": str(self.selected_via),
            }

    @dataclass
    class _ModelGenerationTrace:  # type: ignore[no-redef]
        """Skeleton GenerationTrace used until the model agent ships the real one."""

        output_id: str = ""
        model_code_version: str = ""
        model_weights_sha: str = ""
        cas_conditioning_repr: str = ""
        created_at: str = ""
        tokens: list[_ModelTokenStep] = field(default_factory=list)
        schema_version: str = "generation_trace.v1"

        def to_dict(self) -> dict[str, Any]:
            return {
                "schema_version": self.schema_version,
                "output_id": self.output_id,
                "model_code_version": self.model_code_version,
                "model_weights_sha": self.model_weights_sha,
                "cas_conditioning_repr": self.cas_conditioning_repr,
                "created_at": self.created_at,
                "tokens": [t.to_dict() for t in self.tokens],
            }


# Re-export the model agent's class names. These ARE the model agent's types
# when the parallel agent has shipped; callers that interoperate with the
# model side import these.
TokenStep = _ModelTokenStep
ModelGenerationTrace = _ModelGenerationTrace


SCHEMA_VERSION = "generation_trace_capture.v1"


# ---------------------------------------------------------------------------
# Capture wrapper — adds trace-side provenance + retrieval to the model trace.
# ---------------------------------------------------------------------------


@dataclass
class GenerationTraceCapture:
    """Captured generation trace with trace-side provenance fields.

    This is what the eval/training pipeline persists. It wraps the model's
    own :class:`cas_native.model.nl_generation_head.GenerationTrace` (which
    owns the per-token decoder trace) and adds:

    * ``trace_id`` — UUID4 for *this capture* (distinct from the model's
      ``output_id`` so re-captures of the same generation can be told apart).
    * ``model_checkpoint_id`` — the checkpoint UUID under whose weights this
      generation was produced. Pinned by the eval harness from the
      checkpoint manifest.
    * ``created_at`` — capture-side ISO-8601 timestamp.
    * ``cas_prefix_ids`` / ``prompt_ids`` — input echoes for replay.
    * ``bottleneck_z`` — the conditioning embedding used for nearest-neighbor
      lookup.
    * ``token_steps`` — flat list of :class:`TokenStep` records (the same
      list the model trace's ``tokens`` carries). Surfaced here for callers
      that prefer the trace-side field name.
    * ``nearest_neighbors`` — top-K ``(record_id, cosine_similarity)`` pairs
      from the training NN index.
    * ``live_cas_grounding`` — dict with the live grounding score, including
      ``ran``, ``matches_per_axis``, ``all_match``, ``predicted``,
      ``conditioning``.
    * ``model_trace`` — the unmodified model agent's ``GenerationTrace``,
      retained verbatim so the per-token decoder trace is auditable.
    """

    trace_id: str
    schema_version: str
    model_checkpoint_id: str
    created_at: str
    cas_prefix_ids: list[int] = field(default_factory=list)
    prompt_ids: list[int] = field(default_factory=list)
    bottleneck_z: list[float] = field(default_factory=list)
    token_steps: list[Any] = field(default_factory=list)
    nearest_neighbors: list[tuple[str, float]] = field(default_factory=list)
    live_cas_grounding: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)
    timing: dict[str, float] = field(default_factory=dict)
    model_trace: ModelGenerationTrace | None = None

    def to_dict(self) -> dict[str, Any]:
        return trace_to_dict(self)


# Convenience alias so ``from cas_native.trace.generation_trace import
# GenerationTrace`` returns the trace-side wrapper.
GenerationTrace = GenerationTraceCapture


# ---------------------------------------------------------------------------
# Nearest-neighbor index
# ---------------------------------------------------------------------------


@dataclass
class NearestNeighborIndex:
    """Minimal cosine-similarity NN index over training-record bottleneck z.

    The training script writes one of these alongside each checkpoint as
    ``training_index.json``. The trace module loads it (or accepts an
    in-memory instance) and uses it during ``capture_generation_trace`` to
    surface the top-K most similar training records to the current
    generation.

    JSON shape::

        {
          "schema_version": "training_index.v1",
          "checkpoint_id": "...",
          "dim": 64,
          "records": [
            {"id": "rec-0001", "z": [0.12, ...], "cas_expression": "^3^P|A"}
          ]
        }
    """

    schema_version: str = "training_index.v1"
    checkpoint_id: str = ""
    dim: int = 0
    record_ids: list[str] = field(default_factory=list)
    record_z: list[list[float]] = field(default_factory=list)
    record_cas: list[str] = field(default_factory=list)

    @classmethod
    def from_records(
        cls,
        records: Iterable[dict[str, Any]],
        *,
        checkpoint_id: str = "",
    ) -> "NearestNeighborIndex":
        idx = cls(checkpoint_id=checkpoint_id)
        for rec in records:
            z = rec.get("z") or rec.get("bottleneck_z") or []
            z_list = [float(v) for v in z]
            if not z_list:
                continue
            if idx.dim == 0:
                idx.dim = len(z_list)
            elif len(z_list) != idx.dim:
                continue
            idx.record_ids.append(str(rec.get("id", f"rec-{len(idx.record_ids):04d}")))
            idx.record_z.append(z_list)
            idx.record_cas.append(str(rec.get("cas_expression", "")))
        return idx

    @classmethod
    def from_json(cls, path: str | Path) -> "NearestNeighborIndex":
        path = Path(path)
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        idx = cls(
            schema_version=str(payload.get("schema_version", "training_index.v1")),
            checkpoint_id=str(payload.get("checkpoint_id", "")),
            dim=int(payload.get("dim", 0)),
        )
        for rec in payload.get("records", []):
            z = [float(v) for v in rec.get("z", [])]
            if not z:
                continue
            if idx.dim == 0:
                idx.dim = len(z)
            elif len(z) != idx.dim:
                continue
            idx.record_ids.append(str(rec.get("id", f"rec-{len(idx.record_ids):04d}")))
            idx.record_z.append(z)
            idx.record_cas.append(str(rec.get("cas_expression", "")))
        return idx

    def to_json(self, path: str | Path) -> None:
        path = Path(path)
        payload = {
            "schema_version": self.schema_version,
            "checkpoint_id": self.checkpoint_id,
            "dim": self.dim,
            "records": [
                {"id": rid, "z": list(z), "cas_expression": cas}
                for rid, z, cas in zip(self.record_ids, self.record_z, self.record_cas)
            ],
        }
        with path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)

    def topk(self, query_z: list[float], k: int = 5) -> list[tuple[str, float]]:
        """Return the top-K (record_id, cosine_similarity) by descending sim."""
        if not self.record_z or not query_z:
            return []
        q_norm = math.sqrt(sum(v * v for v in query_z)) or 1.0
        scored: list[tuple[str, float]] = []
        for rid, rec_z in zip(self.record_ids, self.record_z):
            r_norm = math.sqrt(sum(v * v for v in rec_z)) or 1.0
            n = min(len(query_z), len(rec_z))
            dot = sum(query_z[i] * rec_z[i] for i in range(n))
            sim = dot / (q_norm * r_norm)
            scored.append((rid, float(sim)))
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[: max(1, int(k))]


# ---------------------------------------------------------------------------
# Live CAS-grounding score
# ---------------------------------------------------------------------------


def live_cas_grounding_score(
    classifier: nn.Module | None,
    reply_text: str,
    conditioning_cas: dict[str, Any],
    *,
    classify_fn: Callable[[nn.Module, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the generated reply through the project's structured-prediction
    classifier and report whether each axis of the conditioning CAS expression
    is recovered.

    Decoupled from any specific classifier implementation: callers either
    provide a ``classify_fn`` that turns a ``(classifier, text)`` pair into a
    label dict, or pass ``classifier=None`` and let the function record a
    "skipped" diagnostic. The eval harness wires the real classifier in via
    ``classify_fn``; tests inject a stub.
    """
    if classifier is None or classify_fn is None or not reply_text:
        return {
            "ran": False,
            "matches_per_axis": {},
            "all_match": False,
            "predicted": {},
            "conditioning": dict(conditioning_cas),
        }
    try:
        predicted = classify_fn(classifier, reply_text) or {}
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "ran": False,
            "matches_per_axis": {},
            "all_match": False,
            "predicted": {},
            "conditioning": dict(conditioning_cas),
            "error": f"{type(exc).__name__}: {exc}",
        }
    matches: dict[str, bool] = {}
    for key in ("noetic", "domain", "drive", "registers"):
        if key in conditioning_cas and key in predicted:
            cond = conditioning_cas[key]
            pred = predicted[key]
            if isinstance(cond, (list, tuple, set)):
                matches[key] = sorted(cond) == sorted(pred)
            else:
                matches[key] = cond == pred
    return {
        "ran": True,
        "matches_per_axis": matches,
        "all_match": bool(matches) and all(matches.values()),
        "predicted": dict(predicted),
        "conditioning": dict(conditioning_cas),
    }


# ---------------------------------------------------------------------------
# Main capture
# ---------------------------------------------------------------------------


def _normalize_z(z: torch.Tensor | list[float] | None) -> list[float]:
    if z is None:
        return []
    if isinstance(z, torch.Tensor):
        flat = z.detach().to("cpu").flatten().tolist()
    else:
        flat = list(z)
    return [float(v) for v in flat]


def _safe_token_text(tokenizer: Any, token_id: int) -> str:
    """Best-effort conversion from token id to text; tolerates None tokenizer."""
    if tokenizer is None:
        return ""
    for method in ("decode", "id_to_token", "convert_ids_to_tokens"):
        fn = getattr(tokenizer, method, None)
        if callable(fn):
            try:
                out = fn(int(token_id))
                if isinstance(out, str):
                    return out
            except Exception:
                continue
    return ""


def capture_generation_trace(
    model: nn.Module,
    cas_prefix_ids: list[int] | torch.Tensor,
    prompt_ids: list[int] | torch.Tensor,
    bottleneck_z: list[float] | torch.Tensor | None,
    generate_kwargs: dict[str, Any],
    training_index_path: str | Path | NearestNeighborIndex | None = None,
    *,
    model_checkpoint_id: str = "",
    classifier: nn.Module | None = None,
    classify_fn: Callable[[nn.Module, str], dict[str, Any]] | None = None,
    conditioning_cas: dict[str, Any] | None = None,
    tokenizer: Any = None,
    top_k_neighbors: int = 5,
) -> GenerationTraceCapture:
    """Generate with traces and bundle the result into a
    :class:`GenerationTraceCapture`.

    The generation itself is driven by ``model.generate(**generate_kwargs,
    with_trace=True)``. The model agent's ``generate`` is contracted to
    return ``(generated_ids, GenerationTrace)`` when ``with_trace=True``.
    This function:

    1. Calls ``model.generate(...)`` to obtain the per-token decoder trace.
    2. Reads the model trace's ``tokens`` list for surfacing in the wrapper.
    3. Runs nearest-neighbor lookup against the training index.
    4. Runs live CAS-grounding via ``classify_fn`` if provided.
    5. Stamps the wrapper with ``trace_id``, ``model_checkpoint_id``,
       ``schema_version``, and ``created_at``.

    Hook safety: the model agent's ``generate`` is responsible for
    installing/removing forward hooks during sampling. This function adds a
    surrounding ``try/finally`` so any auxiliary state we introduce is
    cleaned up regardless of exceptions raised during sampling.
    """
    t_start = time.perf_counter()
    cas_ids = (
        cas_prefix_ids.tolist()
        if isinstance(cas_prefix_ids, torch.Tensor)
        else list(cas_prefix_ids)
    )
    prm_ids = (
        prompt_ids.tolist()
        if isinstance(prompt_ids, torch.Tensor)
        else list(prompt_ids)
    )
    z_list = _normalize_z(bottleneck_z)

    diagnostics: list[str] = []
    token_steps: list[Any] = []
    model_trace: ModelGenerationTrace | None = None
    generated_text = ""
    generated_ids: list[int] = []

    was_training = bool(getattr(model, "training", False))
    try:
        if hasattr(model, "eval"):
            model.eval()
        kwargs = dict(generate_kwargs)
        kwargs.setdefault("with_trace", True)

        gen_fn = getattr(model, "generate", None)
        if not callable(gen_fn):
            diagnostics.append("model_has_no_generate_method")
        else:
            try:
                with torch.no_grad():
                    out = gen_fn(**kwargs)
            except TypeError:
                diagnostics.append("generate_signature_mismatch")
                out = None

            if out is None:
                pass
            elif isinstance(out, tuple) and len(out) >= 2:
                generated_ids = _coerce_id_list(out[0])
                model_trace = out[1]
                # The model trace stores its per-token records in ``tokens``;
                # we surface the same list as ``token_steps`` on the wrapper
                # for symmetry with the spec.
                if model_trace is not None:
                    token_steps = list(getattr(model_trace, "tokens", []) or [])
                generated_text = " ".join(
                    _safe_token_text(tokenizer, tid) for tid in generated_ids
                ).strip()
            else:
                generated_ids = _coerce_id_list(out)
                generated_text = " ".join(
                    _safe_token_text(tokenizer, tid) for tid in generated_ids
                ).strip()
    finally:
        if was_training and hasattr(model, "train"):
            model.train()

    # Nearest-neighbor lookup.
    nearest: list[tuple[str, float]] = []
    if training_index_path is not None and z_list:
        if isinstance(training_index_path, NearestNeighborIndex):
            nn_index = training_index_path
        else:
            try:
                nn_index = NearestNeighborIndex.from_json(training_index_path)
            except FileNotFoundError:
                nn_index = NearestNeighborIndex()
                diagnostics.append("training_index_missing")
        nearest = nn_index.topk(z_list, k=top_k_neighbors)

    # Live CAS-grounding score.
    grounding = live_cas_grounding_score(
        classifier=classifier,
        reply_text=generated_text,
        conditioning_cas=conditioning_cas or {},
        classify_fn=classify_fn,
    )

    t_end = time.perf_counter()
    capture = GenerationTraceCapture(
        trace_id=str(uuid.uuid4()),
        schema_version=SCHEMA_VERSION,
        model_checkpoint_id=str(model_checkpoint_id),
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        cas_prefix_ids=list(cas_ids),
        prompt_ids=list(prm_ids),
        bottleneck_z=list(z_list),
        token_steps=token_steps,
        nearest_neighbors=nearest,
        live_cas_grounding=grounding,
        diagnostics=diagnostics,
        timing={"total_ms": (t_end - t_start) * 1000.0},
        model_trace=model_trace,
    )
    return capture


def _coerce_id_list(value: Any) -> list[int]:
    if isinstance(value, torch.Tensor):
        flat = value.detach().to("cpu").flatten().tolist()
        return [int(v) for v in flat]
    if isinstance(value, (list, tuple)):
        return [int(v) for v in value]
    return []


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------


def _step_to_dict(step: Any) -> dict[str, Any]:
    """Convert a TokenStep-shaped object to a JSON-friendly dict."""
    if hasattr(step, "to_dict"):
        try:
            return dict(step.to_dict())
        except Exception:
            pass
    return {
        "position": int(getattr(step, "position", 0)),
        "token_id": int(getattr(step, "token_id", 0)),
        "token_str": getattr(step, "token_str", None),
        "attn_to_cas_prefix": [
            float(v) for v in getattr(step, "attn_to_cas_prefix", []) or []
        ],
        "attn_to_prior_tokens": [
            float(v) for v in getattr(step, "attn_to_prior_tokens", []) or []
        ],
        "layer_activation_l2": [
            float(v) for v in getattr(step, "layer_activation_l2", []) or []
        ],
        "selected_via": str(getattr(step, "selected_via", "argmax")),
    }


def trace_to_dict(trace: GenerationTraceCapture) -> dict[str, Any]:
    """Convert a :class:`GenerationTraceCapture` into a JSON-friendly dict."""
    steps_out = [
        _step_to_dict(step) for step in (getattr(trace, "token_steps", []) or [])
    ]
    model_trace_dict: dict[str, Any] = {}
    mt = getattr(trace, "model_trace", None)
    if mt is not None and hasattr(mt, "to_dict"):
        try:
            model_trace_dict = dict(mt.to_dict())
        except Exception:
            model_trace_dict = {}
    return {
        "trace_id": str(getattr(trace, "trace_id", "")),
        "schema_version": str(getattr(trace, "schema_version", SCHEMA_VERSION)),
        "model_checkpoint_id": str(getattr(trace, "model_checkpoint_id", "")),
        "created_at": str(getattr(trace, "created_at", "")),
        "cas_prefix_ids": [int(v) for v in getattr(trace, "cas_prefix_ids", []) or []],
        "prompt_ids": [int(v) for v in getattr(trace, "prompt_ids", []) or []],
        "bottleneck_z": [float(v) for v in getattr(trace, "bottleneck_z", []) or []],
        "token_steps": steps_out,
        "nearest_neighbors": [
            [str(rid), float(sim)]
            for rid, sim in (getattr(trace, "nearest_neighbors", []) or [])
        ],
        "live_cas_grounding": dict(getattr(trace, "live_cas_grounding", {}) or {}),
        "diagnostics": list(getattr(trace, "diagnostics", []) or []),
        "timing": {
            k: float(v) for k, v in (getattr(trace, "timing", {}) or {}).items()
        },
        "model_trace": model_trace_dict,
    }


__all__ = [
    "GenerationTrace",
    "GenerationTraceCapture",
    "ModelGenerationTrace",
    "NearestNeighborIndex",
    "SCHEMA_VERSION",
    "TokenStep",
    "capture_generation_trace",
    "live_cas_grounding_score",
    "trace_to_dict",
]
