"""Per-prediction mechanistic trace data model and renderers.

This is the public face of Mode 7. A consumer calls::

    trace = trace_prediction(model, input_text)
    md = render_trace_markdown(trace)
    payload = render_trace_json(trace)

and gets back a fully-shaped trace usable for audit logs, dashboards, and
regulator-facing reports. See ``docs/working/mode_7_network_tracer_spec_2026_05_04.md``
for the full spec.

Pure stdlib + cas_native; no torch import at module load time. The torch path
lives in ``activations.py`` and is gated behind ``model is not None``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from cas_native.trace.activations import (
    DEFAULT_BOTTLENECK_DIM,
    DEFAULT_D_MODEL,
    HEAD_NAMES,
    ActivationCapture,
    compute_with_hooks,
    head_logit_widths,
)
from cas_native.trace.attribution import (
    attribution_sums,
    compute_bottleneck_top_k,
    compute_capacity_allocation,
    compute_per_head_confidence,
    compute_per_token_attribution,
    is_normalized,
)
from cas_native.trace.network_summary import (
    ActivationSummary,
    build_head_agreement_matrix,
    flagged_disagreements,
    summarize_activations,
)

SCHEMA_VERSION: str = "mechanistic_trace.v1"

# Label tables — duplicated from structured_prediction.py to keep the trace
# package decoupled from torch. Kept in sync via the smoke test
# ``test_label_tables_match_structured_prediction_head``.
_TURN_TYPE_LABELS: tuple[str, ...] = (
    "OPEN", "ACK", "MIRROR", "CLARIFY", "EMPATHIZE", "ANSWER",
    "PLAN", "REFUSE", "REFUSE_CLAIM", "REPAIR", "CLOSE",
)
_EXPRESSION_FAMILY_LABELS: tuple[str, ...] = (
    "state", "register_state", "production", "rule_four", "omega", "meta_logic",
)
_TRANSITION_KIND_LABELS: tuple[str, ...] = (
    "state", "relation", "membership", "subset", "cluster_update",
    "rpm_gate", "production", "omega_bind", "inversion_check",
    "meta_logic_move", "surface_act", "ask_clarify", "repair",
)
_DOMAIN_LABELS: tuple[str, ...] = ("P", "C", "E", "O")
_DRIVE_LABELS: tuple[str, ...] = ("F1", "F2", "F3", "F4", "F5", "F6", "F7")
_REGISTER_LABELS: tuple[str, ...] = ("T", "A", "f", "E")
_REGISTER_MODE_LABELS: tuple[str, ...] = (
    "none", "single", "set_spec", "co_presence", "integration",
)
_META_RELATION_LABELS: tuple[str, ...] = (
    "membership", "subset", "product", "cover", "partition",
    "pullback", "authority", "evidence", "trace_nesting",
)
_AUTHORITY_LABELS: tuple[str, ...] = ("none", "admitted", "blocked")


@dataclass(frozen=True)
class MechanisticTrace:
    """A per-prediction mechanistic trace.

    See spec §2.1 for field-by-field semantics.
    """

    prediction: dict
    per_token_attribution: dict[str, list[float]]
    per_head_confidence: dict[str, float]
    head_agreement_matrix: dict[tuple[str, str], float]
    bottleneck_top_k: list[tuple[int, float]]
    capacity_allocation: dict[str, float]
    metadata: dict = field(default_factory=dict)

    def required_fields_present(self) -> bool:
        """Sanity-check that all six analytic fields plus metadata are populated.

        ``per_token_attribution`` and ``capacity_allocation`` are required to
        cover all 12 head names. Returns False on any missing key.
        """
        for name in HEAD_NAMES:
            if name not in self.per_token_attribution:
                return False
            if name not in self.per_head_confidence:
                return False
            if name not in self.capacity_allocation:
                return False
        if not isinstance(self.bottleneck_top_k, list):
            return False
        if not isinstance(self.head_agreement_matrix, dict):
            return False
        if "schema_version" not in self.metadata:
            return False
        return True

    def diagnostics(self) -> list[str]:
        return list(self.metadata.get("diagnostics") or [])

    def is_stub(self) -> bool:
        return any(d.startswith("stub_") for d in self.diagnostics())


def trace_prediction(
    model: Any | None,
    input_text: str,
    *,
    capture_level: str = "full",
    top_k: int = 8,
    tokenizer: Callable[[str], list[str]] | None = None,
    bottleneck_dim: int = DEFAULT_BOTTLENECK_DIM,
    d_model: int = DEFAULT_D_MODEL,
    head_weights: dict[str, list[list[float]]] | None = None,
    decode_prediction: Callable[[ActivationCapture], dict] | None = None,
) -> MechanisticTrace:
    """Run the model, capture activations, compute a mechanistic trace.

    Args:
        model: a structured-prediction-bearing nn.Module, OR None for the v0
            stub path. The stub generates deterministic activations from
            ``input_text`` so smoke tests don't need a checkpoint.
        input_text: the user input string.
        capture_level: ``"summary" | "full" | "raw"``. See spec §3.
        top_k: number of top bottleneck dims to surface.
        tokenizer: callable ``str -> list[str]``. If None, a whitespace
            tokenizer is used. Empty input returns empty attribution lists.
        bottleneck_dim: width of the post-backbone bottleneck.
        d_model: width of the pre-backbone hidden state.
        head_weights: optional ``{head_name: weight_matrix}`` for the capacity
            calculation. If None, mock weights are generated.
        decode_prediction: callable ``ActivationCapture -> dict``. If None, the
            12-key prediction is decoded by argmax/threshold over the captured
            per-head logits using the canonical label tables.

    Returns:
        A populated ``MechanisticTrace``.

    Raises:
        ValueError: on unknown ``capture_level``.
    """
    if capture_level not in {"summary", "full", "raw"}:
        raise ValueError(
            f"unknown capture_level {capture_level!r}; "
            f"expected one of 'summary', 'full', 'raw'"
        )

    t_start = time.perf_counter()

    if tokenizer is None:
        tokenizer = _whitespace_tokenizer
    tokens = tokenizer(input_text) if input_text else []

    t_capture_start = time.perf_counter()
    capture = compute_with_hooks(
        model,
        input_text,
        bottleneck_dim=bottleneck_dim,
        d_model=d_model,
    )
    t_capture_end = time.perf_counter()

    if decode_prediction is not None:
        prediction = decode_prediction(capture)
    else:
        prediction = _decode_prediction_from_logits(capture)

    t_attr_start = time.perf_counter()
    if capture_level == "summary":
        per_token = {name: [] for name in HEAD_NAMES}
    else:
        per_token = compute_per_token_attribution(
            capture,
            tokens=tokens,
            method="rollout",
        )
    t_attr_end = time.perf_counter()

    per_head_confidence = compute_per_head_confidence(capture)
    capacity_allocation = compute_capacity_allocation(
        capture,
        head_weights=head_weights,
    )
    bottleneck_top_k = compute_bottleneck_top_k(capture, top_k=top_k)
    agreement_matrix = build_head_agreement_matrix(prediction)

    diagnostics: list[str] = []
    diagnostics.extend(capture.diagnostics)
    if not tokens:
        if "empty_input" not in diagnostics:
            diagnostics.append("empty_input")
    if capture_level != "summary" and per_token and tokens:
        all_uniform = all(
            len(set(round(v, 9) for v in values)) <= 1
            for values in per_token.values()
            if values
        )
        if all_uniform:
            diagnostics.append("stub_attribution_uniform")

    t_end = time.perf_counter()

    metadata: dict = {
        "schema_version": SCHEMA_VERSION,
        "model_id": _model_id(model),
        "input_text": input_text,
        "token_count": len(tokens),
        "tokens": list(tokens),
        "capture_level": capture_level,
        "timing": {
            "forward_ms": round((t_capture_end - t_capture_start) * 1000.0, 4),
            "attribution_ms": round((t_attr_end - t_attr_start) * 1000.0, 4),
            "total_ms": round((t_end - t_start) * 1000.0, 4),
        },
        "hook_status": dict(capture.hook_status),
        "diagnostics": diagnostics,
    }

    if capture_level == "raw":
        metadata["raw_activations"] = {
            "pre_bottleneck": list(capture.pre_bottleneck),
            "post_bottleneck": list(capture.post_bottleneck),
            "per_head_logits": {
                name: list(values)
                for name, values in capture.per_head_logits.items()
            },
        }

    summary = summarize_activations(
        capture,
        per_head_confidence=per_head_confidence,
        capacity_allocation=capacity_allocation,
    )
    metadata["activation_summary"] = _summary_to_dict(summary)
    metadata["disagreements"] = [
        {"a": a, "b": b, "score": score}
        for a, b, score in flagged_disagreements(agreement_matrix)
    ]

    return MechanisticTrace(
        prediction=prediction,
        per_token_attribution=per_token,
        per_head_confidence=per_head_confidence,
        head_agreement_matrix=agreement_matrix,
        bottleneck_top_k=bottleneck_top_k,
        capacity_allocation=capacity_allocation,
        metadata=metadata,
    )


def render_trace_markdown(trace: MechanisticTrace) -> str:
    """Human-readable markdown rendering for the audit log / report.

    Sections:
      - Prediction summary
      - Activation summary
      - Per-head confidence
      - Capacity allocation
      - Bottleneck top-K
      - Per-token attribution heatmap (compact)
      - Head agreement disagreements
      - Diagnostics
    """
    lines: list[str] = []
    lines.append("# Mechanistic Trace")
    lines.append("")
    md_meta = trace.metadata or {}
    lines.append(
        f"- Schema: `{md_meta.get('schema_version', 'unknown')}`"
    )
    lines.append(
        f"- Model: `{md_meta.get('model_id', 'unknown')}`"
    )
    lines.append(
        f"- Capture level: `{md_meta.get('capture_level', 'unknown')}`"
    )
    timing = md_meta.get("timing") or {}
    lines.append(
        f"- Timing: forward={timing.get('forward_ms', 0):.2f}ms "
        f"attribution={timing.get('attribution_ms', 0):.2f}ms "
        f"total={timing.get('total_ms', 0):.2f}ms"
    )
    lines.append("")

    lines.append("## Prediction")
    lines.append("")
    pred = trace.prediction or {}
    if pred:
        for key in (
            "turn_type", "expression_family", "transition_kind",
            "noetic", "domain", "drive", "registers", "register_mode",
            "authority", "has_omega", "has_meta_logic",
        ):
            if key in pred:
                lines.append(f"- **{key}**: `{pred[key]!r}`")
    else:
        lines.append("_no prediction_")
    lines.append("")

    lines.append("## Activation Summary")
    lines.append("")
    summary = md_meta.get("activation_summary") or {}
    if summary:
        lines.append(f"_{summary.get('headline', '')}_")
        lines.append("")
        lines.append(f"- Bottleneck L2 norm: `{summary.get('bottleneck_norm', 0):.3f}`")
        lines.append(
            f"- Active dims: `{summary.get('bottleneck_active_dims', 0)}` "
            f"(sparsity {summary.get('bottleneck_sparsity', 0):.2f})"
        )
        lines.append(
            f"- Most confident head: `{summary.get('most_confident_head', 'n/a')}`"
        )
        lines.append(
            f"- Least confident head: `{summary.get('least_confident_head', 'n/a')}`"
        )
        lines.append(
            f"- Capacity-dominant head: `{summary.get('most_capacity_head', 'n/a')}` "
            f"(share {summary.get('capacity_dominance', 0):.2f})"
        )
    lines.append("")

    lines.append("## Per-Head Confidence")
    lines.append("")
    lines.append("| head | confidence |")
    lines.append("|---|---|")
    for name in HEAD_NAMES:
        c = trace.per_head_confidence.get(name, 0.0)
        bar = _confidence_bar(c)
        lines.append(f"| `{name}` | `{c:.3f}` {bar} |")
    lines.append("")

    lines.append("## Capacity Allocation")
    lines.append("")
    lines.append("| head | capacity share |")
    lines.append("|---|---|")
    for name in HEAD_NAMES:
        share = trace.capacity_allocation.get(name, 0.0)
        bar = _share_bar(share)
        lines.append(f"| `{name}` | `{share:.3f}` {bar} |")
    lines.append("")

    lines.append("## Bottleneck Top-K")
    lines.append("")
    if trace.bottleneck_top_k:
        lines.append("| dim | activation |")
        lines.append("|---|---|")
        for dim, act in trace.bottleneck_top_k:
            sign = "+" if act >= 0 else "-"
            lines.append(f"| `{dim}` | `{sign}{abs(act):.3f}` |")
    else:
        lines.append("_no bottleneck activations captured_")
    lines.append("")

    lines.append("## Per-Token Attribution")
    lines.append("")
    tokens = md_meta.get("tokens") or []
    if tokens and any(trace.per_token_attribution.values()):
        header_cells = ["head"] + [f"`{tok}`" for tok in tokens]
        lines.append("| " + " | ".join(header_cells) + " |")
        lines.append("|" + "|".join(["---"] * len(header_cells)) + "|")
        for name in HEAD_NAMES:
            row = trace.per_token_attribution.get(name) or []
            cells = [f"`{name}`"] + [f"{v:.2f}" for v in row]
            if len(cells) - 1 < len(tokens):
                cells.extend(["-"] * (len(tokens) - (len(cells) - 1)))
            lines.append("| " + " | ".join(cells) + " |")
    else:
        lines.append("_no per-token attribution available_")
    lines.append("")

    lines.append("## Head Disagreements")
    lines.append("")
    disagreements = md_meta.get("disagreements") or []
    if disagreements:
        lines.append("| head A | head B | agreement |")
        lines.append("|---|---|---|")
        for entry in disagreements:
            a = entry.get("a", "")
            b = entry.get("b", "")
            score = entry.get("score", 0.0)
            lines.append(f"| `{a}` | `{b}` | `{score:.2f}` |")
    else:
        lines.append("_no head disagreements flagged_")
    lines.append("")

    lines.append("## Diagnostics")
    lines.append("")
    diagnostics = md_meta.get("diagnostics") or []
    if diagnostics:
        for d in diagnostics:
            lines.append(f"- `{d}`")
    else:
        lines.append("_clean: no diagnostics_")
    lines.append("")

    return "\n".join(lines)


def render_trace_json(trace: MechanisticTrace) -> dict:
    """JSON-serializable dict for the dashboard / API consumer.

    Note: the head_agreement_matrix is rendered as a list of
    ``{a, b, score}`` records (tuples don't serialize cleanly). Only the
    canonical (a < b) ordering is emitted; consumers can mirror.
    """
    pairs: list[dict] = []
    seen: set[frozenset[str]] = set()
    for (a, b), score in trace.head_agreement_matrix.items():
        if a == b:
            continue
        key = frozenset({a, b})
        if key in seen:
            continue
        seen.add(key)
        first, second = sorted([a, b])
        pairs.append({"a": first, "b": second, "score": float(score)})
    pairs.sort(key=lambda d: (d["a"], d["b"]))

    top_k_records = [
        {"dim": int(dim), "activation": float(act)}
        for dim, act in trace.bottleneck_top_k
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "prediction": dict(trace.prediction),
        "per_token_attribution": {
            name: [float(v) for v in values]
            for name, values in trace.per_token_attribution.items()
        },
        "per_head_confidence": {
            name: float(v) for name, v in trace.per_head_confidence.items()
        },
        "head_agreement_matrix": pairs,
        "bottleneck_top_k": top_k_records,
        "capacity_allocation": {
            name: float(v) for name, v in trace.capacity_allocation.items()
        },
        "metadata": _scrub_for_json(trace.metadata),
    }


def _decode_prediction_from_logits(capture: ActivationCapture) -> dict:
    logits = capture.per_head_logits

    def _argmax_label(name: str, labels: tuple[str, ...]) -> str:
        values = logits.get(name) or []
        if not values:
            return labels[0]
        idx = max(range(len(values)), key=lambda i: values[i])
        if idx < len(labels):
            return labels[idx]
        return labels[0]

    def _argmax_int(name: str, n: int) -> int:
        values = logits.get(name) or []
        if not values:
            return 0
        idx = max(range(min(len(values), n)), key=lambda i: values[i])
        return idx

    def _multilabel(name: str, labels: tuple[str, ...]) -> tuple[str, ...]:
        values = logits.get(name) or []
        active = [labels[i] for i, v in enumerate(values) if i < len(labels) and v > 0.0]
        if not active and values:
            top = max(range(len(values)), key=lambda i: values[i])
            if top < len(labels):
                active = [labels[top]]
        return tuple(active)

    def _bool(name: str) -> bool:
        values = logits.get(name) or []
        if len(values) < 2:
            return False
        return values[1] > values[0]

    return {
        "turn_type": _argmax_label("turn_type", _TURN_TYPE_LABELS),
        "expression_family": _argmax_label(
            "expression_family", _EXPRESSION_FAMILY_LABELS
        ),
        "transition_kind": _argmax_label(
            "transition_kind", _TRANSITION_KIND_LABELS
        ),
        "noetic": _argmax_int("noetic", 10),
        "domain": _argmax_label("domain", _DOMAIN_LABELS),
        "drive": _argmax_label("drive", _DRIVE_LABELS),
        "registers": list(_multilabel("register", _REGISTER_LABELS)),
        "register_mode": _argmax_label(
            "register_mode", _REGISTER_MODE_LABELS
        ),
        "meta_relations": list(_multilabel("meta_relation", _META_RELATION_LABELS)),
        "authority": _argmax_label("authority", _AUTHORITY_LABELS),
        "has_omega": _bool("omega"),
        "has_meta_logic": _bool("meta_logic"),
    }


def _whitespace_tokenizer(text: str) -> list[str]:
    if not text:
        return []
    return [t for t in text.split() if t]


def _model_id(model: Any | None) -> str:
    if model is None:
        return "stub-v0"
    name = getattr(model, "name", None) or type(model).__name__
    return f"{name}@{id(model):x}"


def _confidence_bar(value: float, *, width: int = 10) -> str:
    filled = max(0, min(width, int(round(value * width))))
    return "`" + ("#" * filled) + ("." * (width - filled)) + "`"


def _share_bar(value: float, *, width: int = 10) -> str:
    return _confidence_bar(value, width=width)


def _summary_to_dict(summary: ActivationSummary) -> dict:
    return {
        "bottleneck_norm": summary.bottleneck_norm,
        "bottleneck_active_dims": summary.bottleneck_active_dims,
        "bottleneck_sparsity": summary.bottleneck_sparsity,
        "most_confident_head": summary.most_confident_head,
        "least_confident_head": summary.least_confident_head,
        "confidence_gap": summary.confidence_gap,
        "most_capacity_head": summary.most_capacity_head,
        "capacity_dominance": summary.capacity_dominance,
        "headline": summary.headline,
    }


def _scrub_for_json(obj: Any) -> Any:
    """Recursively convert dataclasses / tuples to JSON-friendly Python."""
    if isinstance(obj, dict):
        return {str(k): _scrub_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_scrub_for_json(v) for v in obj]
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (int, float, str)) or obj is None:
        return obj
    return repr(obj)
