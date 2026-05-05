"""Tests for the generation-trace surface.

Verifies:

* ``capture_generation_trace`` populates every TokenStep field surfaced via
  the wrapper.
* Nearest-neighbor lookup returns up to K training record IDs in order.
* Live CAS-grounding score is computed when a classifier + classify_fn are
  provided.
* Hooks register and clean up; two consecutive captures don't leak.
* GenerationTraceCapture is JSON-serializable end-to-end.
* Capture identity fields ``trace_id``, ``model_checkpoint_id``,
  ``schema_version``, ``created_at`` are populated.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import torch
import torch.nn as nn

from cas_native.trace.generation_trace import (
    GenerationTrace,
    GenerationTraceCapture,
    ModelGenerationTrace,
    NearestNeighborIndex,
    TokenStep,
    capture_generation_trace,
    live_cas_grounding_score,
    trace_to_dict,
)


# ---------------------------------------------------------------------------
# Test fixtures: a stub generative model that mimics the model agent's
# `generate(..., with_trace=True) -> (ids, GenerationTrace)` contract.
# ---------------------------------------------------------------------------


def _make_token_step(
    *,
    position: int,
    token_id: int,
    n_layers: int = 4,
    cas_prefix_len: int = 3,
) -> TokenStep:
    """Build a TokenStep using whichever field set the imported class exposes."""
    return TokenStep(
        position=position,
        token_id=token_id,
        token_str=f"tok{position}",
        attn_to_cas_prefix=tuple([1.0 if i == 0 else 0.0 for i in range(cas_prefix_len)]),
        attn_to_prior_tokens=tuple([0.5] * (position + 1)),
        layer_activation_l2=tuple([0.1 * (i + 1) for i in range(n_layers)]),
        selected_via="argmax",
    )


class _StubGenerativeModel(nn.Module):
    """Stub model returning a deterministic (ids, trace) pair.

    Mirrors the contract the model agent's NLGenerationHead.generate exposes
    when called with ``with_trace=True``. We additionally count how many
    times ``generate`` was invoked so the leak test can assert no residual
    state survives across calls.
    """

    def __init__(self) -> None:
        super().__init__()
        self.fc = nn.Linear(4, 4)
        self.calls = 0

    def generate(
        self,
        cas_prefix_ids,
        prompt_ids,
        max_new_tokens: int = 3,
        with_trace: bool = True,
        **_kwargs,
    ):
        self.calls += 1
        captured = {}

        def _hook(_mod, _in, out):
            captured["fc_out"] = out.detach()

        h = self.fc.register_forward_hook(_hook)
        try:
            x = torch.randn(1, 4)
            _ = self.fc(x)
        finally:
            h.remove()

        token_ids = list(range(int(max_new_tokens)))
        steps = [
            _make_token_step(position=i, token_id=int(i)) for i in range(int(max_new_tokens))
        ]
        trace = ModelGenerationTrace(
            output_id="model-side-output",
            model_code_version="v0.0.0-stub",
            model_weights_sha="stub-sha",
            cas_conditioning_repr="stub-cas",
            created_at="2026-05-04T00:00:00Z",
            tokens=steps,
        )
        return token_ids, trace


# ---------------------------------------------------------------------------
# 1. capture_generation_trace populates all TokenStep fields
# ---------------------------------------------------------------------------


def test_generation_trace_populates_all_token_step_fields():
    model = _StubGenerativeModel()
    capture = capture_generation_trace(
        model=model,
        cas_prefix_ids=[1, 2, 3],
        prompt_ids=[10, 11],
        bottleneck_z=[0.5, 0.5, 0.0, 0.0],
        generate_kwargs={
            "cas_prefix_ids": [1, 2, 3],
            "prompt_ids": [10, 11],
            "max_new_tokens": 4,
        },
        model_checkpoint_id="ckpt-1",
    )
    assert len(capture.token_steps) == 4
    for step in capture.token_steps:
        assert isinstance(step.position, int)
        assert isinstance(step.token_id, int)
        # Both real and skeleton classes use these fields.
        assert step.attn_to_cas_prefix, "attn_to_cas_prefix must be populated"
        assert step.layer_activation_l2, "layer_activation_l2 must be populated"
        assert step.selected_via in {"argmax", "topp", "temp"}


# ---------------------------------------------------------------------------
# 2. Nearest-neighbor lookup returns K training record IDs
# ---------------------------------------------------------------------------


def test_nearest_neighbor_returns_top_k():
    idx = NearestNeighborIndex.from_records(
        [
            {"id": "rec-A", "z": [1.0, 0.0, 0.0, 0.0], "cas_expression": "^3^P|A"},
            {"id": "rec-B", "z": [0.0, 1.0, 0.0, 0.0], "cas_expression": "^2^C|f"},
            {"id": "rec-C", "z": [0.5, 0.5, 0.0, 0.0], "cas_expression": "^4^E|T"},
            {"id": "rec-D", "z": [-1.0, 0.0, 0.0, 0.0], "cas_expression": "^5^O|E"},
        ],
        checkpoint_id="ckpt-nn",
    )
    nbrs = idx.topk([1.0, 0.0, 0.0, 0.0], k=3)
    assert len(nbrs) == 3
    # rec-A is identical -> highest similarity.
    assert nbrs[0][0] == "rec-A"

    model = _StubGenerativeModel()
    capture = capture_generation_trace(
        model=model,
        cas_prefix_ids=[],
        prompt_ids=[1],
        bottleneck_z=[1.0, 0.0, 0.0, 0.0],
        generate_kwargs={"cas_prefix_ids": [], "prompt_ids": [1], "max_new_tokens": 2},
        training_index_path=idx,
        top_k_neighbors=2,
        model_checkpoint_id="ckpt-1",
    )
    assert len(capture.nearest_neighbors) == 2
    assert capture.nearest_neighbors[0][0] == "rec-A"


# ---------------------------------------------------------------------------
# 3. Live CAS-grounding score computed
# ---------------------------------------------------------------------------


def test_live_cas_grounding_score_computed():
    def classify_fn(_clf, _text):
        return {"noetic": 3, "domain": "P", "drive": "F2", "registers": ["A"]}

    grounding = live_cas_grounding_score(
        classifier=nn.Linear(2, 2),
        reply_text="some reply",
        conditioning_cas={"noetic": 3, "domain": "P", "drive": "F2", "registers": ["A"]},
        classify_fn=classify_fn,
    )
    assert grounding["ran"] is True
    assert grounding["all_match"] is True

    def classify_fn_wrong(_clf, _text):
        return {"noetic": 7, "domain": "P", "drive": "F2", "registers": ["A"]}

    g_wrong = live_cas_grounding_score(
        classifier=nn.Linear(2, 2),
        reply_text="some reply",
        conditioning_cas={"noetic": 3, "domain": "P", "drive": "F2", "registers": ["A"]},
        classify_fn=classify_fn_wrong,
    )
    assert g_wrong["matches_per_axis"]["noetic"] is False


# ---------------------------------------------------------------------------
# 4. Hooks register + cleanup (no leaks across consecutive captures)
# ---------------------------------------------------------------------------


def test_hooks_register_and_cleanup_no_leaks():
    model = _StubGenerativeModel()
    pre_hook_count = len(model.fc._forward_hooks)
    capture_a = capture_generation_trace(
        model=model,
        cas_prefix_ids=[1],
        prompt_ids=[2],
        bottleneck_z=[0.1, 0.2, 0.3, 0.4],
        generate_kwargs={"cas_prefix_ids": [1], "prompt_ids": [2], "max_new_tokens": 1},
        model_checkpoint_id="ckpt-leak-1",
    )
    mid_hook_count = len(model.fc._forward_hooks)
    capture_b = capture_generation_trace(
        model=model,
        cas_prefix_ids=[1],
        prompt_ids=[2],
        bottleneck_z=[0.1, 0.2, 0.3, 0.4],
        generate_kwargs={"cas_prefix_ids": [1], "prompt_ids": [2], "max_new_tokens": 1},
        model_checkpoint_id="ckpt-leak-2",
    )
    post_hook_count = len(model.fc._forward_hooks)
    assert pre_hook_count == mid_hook_count == post_hook_count, (
        f"hook leak: pre={pre_hook_count} mid={mid_hook_count} post={post_hook_count}"
    )
    assert model.calls == 2
    assert capture_a.trace_id != capture_b.trace_id


# ---------------------------------------------------------------------------
# 5. GenerationTraceCapture JSON-serializable end-to-end
# ---------------------------------------------------------------------------


def test_trace_is_json_serializable():
    model = _StubGenerativeModel()
    capture = capture_generation_trace(
        model=model,
        cas_prefix_ids=[1, 2],
        prompt_ids=[3, 4],
        bottleneck_z=[0.1, 0.2, 0.3, 0.4],
        generate_kwargs={
            "cas_prefix_ids": [1, 2],
            "prompt_ids": [3, 4],
            "max_new_tokens": 2,
        },
        model_checkpoint_id="ckpt-json",
    )
    payload = trace_to_dict(capture)
    serialized = json.dumps(payload, sort_keys=True)
    parsed = json.loads(serialized)
    assert parsed["model_checkpoint_id"] == "ckpt-json"
    assert parsed["schema_version"].startswith("generation_trace_capture.")
    assert len(parsed["token_steps"]) == 2
    # The model trace is preserved verbatim under model_trace.
    assert parsed["model_trace"]["output_id"] == "model-side-output"


# ---------------------------------------------------------------------------
# 6. Capture identity fields are populated
# ---------------------------------------------------------------------------


def test_trace_identity_fields_populated():
    model = _StubGenerativeModel()
    capture = capture_generation_trace(
        model=model,
        cas_prefix_ids=[1],
        prompt_ids=[2],
        bottleneck_z=[0.0, 0.0, 0.0, 0.0],
        generate_kwargs={"cas_prefix_ids": [1], "prompt_ids": [2], "max_new_tokens": 1},
        model_checkpoint_id="ckpt-id",
    )
    assert isinstance(capture, GenerationTraceCapture)
    assert capture.trace_id, "trace_id must be assigned"
    assert capture.model_checkpoint_id == "ckpt-id"
    assert capture.created_at, "created_at must be stamped"
    assert capture.schema_version == "generation_trace_capture.v1"


# ---------------------------------------------------------------------------
# 7. NearestNeighborIndex round-trips through JSON
# ---------------------------------------------------------------------------


def test_nearest_neighbor_index_round_trip(tmp_path):
    idx = NearestNeighborIndex.from_records(
        [
            {"id": "r1", "z": [1.0, 0.0], "cas_expression": "^1^P"},
            {"id": "r2", "z": [0.0, 1.0], "cas_expression": "^2^C"},
        ],
        checkpoint_id="ckpt-rt",
    )
    path = tmp_path / "index.json"
    idx.to_json(path)
    loaded = NearestNeighborIndex.from_json(path)
    assert loaded.checkpoint_id == "ckpt-rt"
    assert loaded.dim == 2
    assert loaded.record_ids == ["r1", "r2"]


# ---------------------------------------------------------------------------
# 8. GenerationTrace alias points to the capture wrapper
# ---------------------------------------------------------------------------


def test_generation_trace_alias_is_capture_wrapper():
    """Importing ``GenerationTrace`` from this module yields the wrapper."""
    assert GenerationTrace is GenerationTraceCapture
