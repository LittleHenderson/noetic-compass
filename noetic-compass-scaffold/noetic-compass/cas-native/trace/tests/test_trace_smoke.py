"""Smoke tests for cas_native.trace (Mode 7 Network Tracer).

These tests exercise the v0 stub end-to-end:

  * trace_prediction returns a fully-shaped MechanisticTrace.
  * Per-token attribution sums to 1.0 per head.
  * Capacity allocation sums to 1.0.
  * Empty input is handled gracefully.
  * Markdown rendering is non-empty and contains all the expected sections.
  * JSON rendering is serializable with stdlib json.

No torch, no checkpoint, no model. The stub path is the path under test.
"""

from __future__ import annotations

import json
import math

import pytest

from cas_native.trace import (
    SCHEMA_VERSION,
    MechanisticTrace,
    render_trace_json,
    render_trace_markdown,
    trace_prediction,
)
from cas_native.trace.activations import HEAD_NAMES, head_logit_widths
from cas_native.trace.attribution import is_normalized
from cas_native.trace.mechanistic import (
    _AUTHORITY_LABELS,
    _DOMAIN_LABELS,
    _DRIVE_LABELS,
    _EXPRESSION_FAMILY_LABELS,
    _META_RELATION_LABELS,
    _REGISTER_LABELS,
    _REGISTER_MODE_LABELS,
    _TRANSITION_KIND_LABELS,
    _TURN_TYPE_LABELS,
)
from cas_native.trace.network_summary import (
    build_head_agreement_matrix,
    flagged_disagreements,
    summarize_activations,
)


# -- Smoke 1: trace_prediction returns the expected shape -----------------


def test_trace_prediction_returns_full_shape(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    assert isinstance(trace, MechanisticTrace)
    assert trace.required_fields_present(), (
        f"trace missing required fields; "
        f"per_token_attribution_keys={set(trace.per_token_attribution.keys())}, "
        f"per_head_confidence_keys={set(trace.per_head_confidence.keys())}, "
        f"capacity_allocation_keys={set(trace.capacity_allocation.keys())}, "
        f"metadata_keys={set(trace.metadata.keys())}"
    )
    assert trace.metadata["schema_version"] == SCHEMA_VERSION


def test_trace_prediction_prediction_keys(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    expected_keys = {
        "turn_type", "expression_family", "transition_kind",
        "noetic", "domain", "drive", "registers",
        "register_mode", "meta_relations", "authority",
        "has_omega", "has_meta_logic",
    }
    assert expected_keys.issubset(trace.prediction.keys()), (
        f"prediction missing keys: {expected_keys - trace.prediction.keys()}"
    )


def test_trace_prediction_label_values_in_canonical_tables(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    pred = trace.prediction
    assert pred["turn_type"] in _TURN_TYPE_LABELS
    assert pred["expression_family"] in _EXPRESSION_FAMILY_LABELS
    assert pred["transition_kind"] in _TRANSITION_KIND_LABELS
    assert 0 <= pred["noetic"] <= 9
    assert pred["domain"] in _DOMAIN_LABELS
    assert pred["drive"] in _DRIVE_LABELS
    assert pred["register_mode"] in _REGISTER_MODE_LABELS
    assert pred["authority"] in _AUTHORITY_LABELS
    for r in pred["registers"]:
        assert r in _REGISTER_LABELS
    for r in pred["meta_relations"]:
        assert r in _META_RELATION_LABELS


# -- Smoke 2: render_trace_markdown is non-empty and well-formed ----------


def test_render_trace_markdown_nonempty(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    md = render_trace_markdown(trace)
    assert isinstance(md, str)
    assert len(md) > 200
    for section in (
        "# Mechanistic Trace",
        "## Prediction",
        "## Activation Summary",
        "## Per-Head Confidence",
        "## Capacity Allocation",
        "## Bottleneck Top-K",
        "## Per-Token Attribution",
        "## Head Disagreements",
        "## Diagnostics",
    ):
        assert section in md, f"missing section: {section!r}"


def test_render_trace_markdown_lists_all_heads(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    md = render_trace_markdown(trace)
    for name in HEAD_NAMES:
        assert f"`{name}`" in md, f"head {name!r} not rendered in markdown"


# -- Smoke 3: render_trace_json is serializable ---------------------------


def test_render_trace_json_serializable(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    payload = render_trace_json(trace)
    s = json.dumps(payload)
    assert len(s) > 200
    reloaded = json.loads(s)
    assert reloaded["schema_version"] == SCHEMA_VERSION
    assert set(reloaded["per_head_confidence"].keys()) == set(HEAD_NAMES)
    assert set(reloaded["capacity_allocation"].keys()) == set(HEAD_NAMES)
    assert set(reloaded["per_token_attribution"].keys()) == set(HEAD_NAMES)


def test_render_trace_json_agreement_pairs_canonical(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    payload = render_trace_json(trace)
    seen: set[tuple[str, str]] = set()
    for entry in payload["head_agreement_matrix"]:
        a, b = entry["a"], entry["b"]
        assert a < b, f"agreement pair not canonical: ({a}, {b})"
        assert (a, b) not in seen, f"duplicate pair: ({a}, {b})"
        seen.add((a, b))
        assert 0.0 <= entry["score"] <= 1.0


# -- Smoke 4: per-token attribution sums to 1.0 per head ------------------


def test_stub_attribution_normalized(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    for head, values in trace.per_token_attribution.items():
        if not values:
            continue
        s = sum(values)
        assert math.isclose(s, 1.0, abs_tol=1e-6), (
            f"head {head!r} attribution sum={s!r} != 1.0; values={values!r}"
        )


def test_stub_attribution_token_count_matches(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    expected = trace.metadata["token_count"]
    for head, values in trace.per_token_attribution.items():
        assert len(values) == expected, (
            f"head {head!r} attribution length={len(values)} "
            f"!= token_count={expected}"
        )


# -- Smoke 5: empty input is handled gracefully ---------------------------


def test_empty_input_handled(empty_input: str) -> None:
    trace = trace_prediction(model=None, input_text=empty_input)
    assert trace.metadata["token_count"] == 0
    assert trace.metadata["tokens"] == []
    for values in trace.per_token_attribution.values():
        assert values == []
    diagnostics = trace.metadata.get("diagnostics") or []
    assert "empty_input" in diagnostics
    assert trace.required_fields_present()


def test_empty_input_renders_markdown_safely(empty_input: str) -> None:
    trace = trace_prediction(model=None, input_text=empty_input)
    md = render_trace_markdown(trace)
    assert "no per-token attribution available" in md


def test_empty_input_renders_json_safely(empty_input: str) -> None:
    trace = trace_prediction(model=None, input_text=empty_input)
    payload = render_trace_json(trace)
    json.dumps(payload)  # serializability check
    for values in payload["per_token_attribution"].values():
        assert values == []


# -- Smoke 6: capacity allocation sums to 1.0 -----------------------------


def test_capacity_allocation_normalized(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    s = sum(trace.capacity_allocation.values())
    assert math.isclose(s, 1.0, abs_tol=1e-6), (
        f"capacity allocation sum={s!r} != 1.0; "
        f"values={trace.capacity_allocation!r}"
    )


def test_capacity_allocation_all_nonneg(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    for name, share in trace.capacity_allocation.items():
        assert share >= 0.0, f"head {name!r} share={share!r} < 0"


# -- Smoke 7: head agreement matrix is symmetric, diagonal is 1.0 ---------


def test_head_agreement_matrix_symmetric(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    m = trace.head_agreement_matrix
    for (a, b), score in m.items():
        if a == b:
            continue
        assert (b, a) in m, f"missing mirror entry for ({a}, {b})"
        assert math.isclose(score, m[(b, a)], abs_tol=1e-9), (
            f"asymmetric entry: ({a},{b})={score} vs ({b},{a})={m[(b,a)]}"
        )


def test_head_agreement_matrix_diagonal_one(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    m = trace.head_agreement_matrix
    for name in HEAD_NAMES:
        assert (name, name) in m, f"diagonal entry missing for {name!r}"
        assert math.isclose(m[(name, name)], 1.0, abs_tol=1e-9)


def test_head_agreement_matrix_all_in_unit_interval(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    for (a, b), score in trace.head_agreement_matrix.items():
        assert 0.0 <= score <= 1.0, (
            f"agreement score for ({a}, {b}) out of [0,1]: {score!r}"
        )


# -- Smoke 8: bottleneck top-K is descending by |activation| --------------


def test_bottleneck_top_k_descending(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input, top_k=8)
    abs_acts = [abs(act) for _, act in trace.bottleneck_top_k]
    assert abs_acts == sorted(abs_acts, reverse=True), (
        f"bottleneck_top_k not descending: {trace.bottleneck_top_k!r}"
    )


def test_bottleneck_top_k_dim_indices_unique(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input, top_k=8)
    dims = [d for d, _ in trace.bottleneck_top_k]
    assert len(set(dims)) == len(dims)


def test_bottleneck_top_k_respects_k(sample_input: str) -> None:
    for k in (1, 4, 8, 16):
        trace = trace_prediction(model=None, input_text=sample_input, top_k=k)
        assert len(trace.bottleneck_top_k) <= k


# -- Smoke 9: capture_level=summary omits per-token attribution -----------


def test_capture_level_summary_omits_per_token(sample_input: str) -> None:
    trace = trace_prediction(
        model=None, input_text=sample_input, capture_level="summary"
    )
    for values in trace.per_token_attribution.values():
        assert values == []
    # But bottleneck top-K and capacity allocation are still populated.
    assert len(trace.bottleneck_top_k) > 0
    s = sum(trace.capacity_allocation.values())
    assert math.isclose(s, 1.0, abs_tol=1e-6)


def test_capture_level_raw_includes_raw_activations(sample_input: str) -> None:
    trace = trace_prediction(
        model=None, input_text=sample_input, capture_level="raw"
    )
    assert "raw_activations" in trace.metadata
    raw = trace.metadata["raw_activations"]
    assert "pre_bottleneck" in raw
    assert "post_bottleneck" in raw
    assert "per_head_logits" in raw
    assert len(raw["post_bottleneck"]) == 64  # default bottleneck_dim


def test_capture_level_invalid_raises() -> None:
    with pytest.raises(ValueError, match="unknown capture_level"):
        trace_prediction(model=None, input_text="x", capture_level="bogus")


# -- Determinism / reproducibility ----------------------------------------


def test_stub_capture_is_deterministic(sample_input: str) -> None:
    trace_a = trace_prediction(model=None, input_text=sample_input)
    trace_b = trace_prediction(model=None, input_text=sample_input)
    assert trace_a.prediction == trace_b.prediction
    assert trace_a.bottleneck_top_k == trace_b.bottleneck_top_k
    assert trace_a.capacity_allocation == trace_b.capacity_allocation
    assert trace_a.per_head_confidence == trace_b.per_head_confidence


def test_different_inputs_produce_different_predictions() -> None:
    a = trace_prediction(model=None, input_text="alpha bravo charlie")
    b = trace_prediction(model=None, input_text="delta echo foxtrot")
    # Not strictly required, but in practice the stub varies enough that at
    # least one of the bottleneck top-K dims should differ.
    assert a.bottleneck_top_k != b.bottleneck_top_k or a.prediction != b.prediction


# -- Per-head confidence properties ---------------------------------------


def test_per_head_confidence_in_unit_interval(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    for name, c in trace.per_head_confidence.items():
        assert 0.0 <= c <= 1.0, f"head {name!r} confidence out of [0,1]: {c!r}"


# -- Diagnostics expectations ---------------------------------------------


def test_stub_diagnostic_emitted_in_no_model_path(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    diag = trace.metadata.get("diagnostics") or []
    assert any(d.startswith("stub_") for d in diag), (
        f"expected at least one stub_* diagnostic; got {diag!r}"
    )
    assert trace.is_stub() is True


def test_normalized_helper_reports_correctly() -> None:
    assert is_normalized([0.5, 0.5]) is True
    assert is_normalized([0.6, 0.5]) is False
    assert is_normalized([]) is True


# -- Network summary direct tests -----------------------------------------


def test_summarize_activations_returns_headline(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    summary = trace.metadata["activation_summary"]
    assert isinstance(summary["headline"], str)
    assert len(summary["headline"]) > 0
    assert summary["most_confident_head"] in HEAD_NAMES
    assert summary["least_confident_head"] in HEAD_NAMES


def test_build_head_agreement_matrix_handles_empty_prediction() -> None:
    matrix = build_head_agreement_matrix({})
    # Diagonal still populated.
    for name in HEAD_NAMES:
        assert (name, name) in matrix
        assert math.isclose(matrix[(name, name)], 1.0)


def test_flagged_disagreements_filters_below_threshold() -> None:
    pred = {
        "register_mode": "single",
        "registers": ["A", "f"],          # mode=single but 2 registers -> 0.0
        "expression_family": "state",
        "has_omega": True,                 # but family != production/omega -> 0.2
        "has_meta_logic": False,
        "transition_kind": "state",
        "turn_type": "ANSWER",
        "authority": "none",
    }
    matrix = build_head_agreement_matrix(pred)
    flags = flagged_disagreements(matrix, threshold=0.5)
    pair_set = {(a, b) for a, b, _ in flags}
    canonical = {tuple(sorted(p)) for p in pair_set}
    assert ("register", "register_mode") in canonical
    assert ("expression_family", "omega") in canonical


# -- Sanity: head names match StructuredPredictionHead --------------------


def test_head_logit_widths_complete() -> None:
    widths = head_logit_widths()
    assert set(widths.keys()) == set(HEAD_NAMES)
    for name, width in widths.items():
        assert width > 0, f"head {name!r} has non-positive width {width}"


# -- Tokenizer plumbing ----------------------------------------------------


def test_custom_tokenizer_threaded_through(sample_input: str) -> None:
    calls: list[str] = []

    def tok(text: str) -> list[str]:
        calls.append(text)
        return ["A", "B", "C"]

    trace = trace_prediction(
        model=None, input_text=sample_input, tokenizer=tok
    )
    assert calls == [sample_input]
    assert trace.metadata["token_count"] == 3
    assert trace.metadata["tokens"] == ["A", "B", "C"]
    for head, values in trace.per_token_attribution.items():
        assert len(values) == 3


# -- Top-K and bottleneck-dim correctness ---------------------------------


def test_bottleneck_top_k_indices_in_range(sample_input: str) -> None:
    trace = trace_prediction(model=None, input_text=sample_input)
    for dim, _ in trace.bottleneck_top_k:
        assert 0 <= dim < 64
