"""The REAL live route (stream_real_trace) mapping, tested deterministically.

No torch and no model needed: a stub runtime returns a canned capture, so this
covers the fake->real replacement's mapping logic in CI -- real confidence from
logits, real top neurons from mlp_states, and the honest absences (no RNG) for
signals the capture does not provide.
"""

from __future__ import annotations

import asyncio

import numpy as np

from app.runtime import event_stream as ES
from app.schemas.requests import CreateSessionRequest


class _StubTokenizer:
    def decode(self, ids):
        return {10: " Paris", 11: " is", 12: " nice"}.get(int(ids[0]), f"<{int(ids[0])}>")


class _StubCapture:
    def __init__(self, arrays):
        self.arrays = arrays


class _StubRuntime:
    """Mimics a loaded runtime: exposes .tokenizer; capture is monkeypatched."""

    tokenizer = _StubTokenizer()


def _canned_capture(steps=3, layers=12, hidden=768, vocab=64):
    rng = np.random.default_rng(0)
    logits = rng.standard_normal((steps, vocab)).astype(np.float32)
    # make step 0 very peaked (high confidence) and step 1 flat (low), to check
    # confidence is really a softmax of the row, not a constant.
    logits[0, 10] = 50.0
    logits[1] = np.zeros(vocab, dtype=np.float32)
    mlp = rng.standard_normal((steps, layers, hidden)).astype(np.float32)
    mlp[0, 7, 42] = 99.0  # a clear top neuron at step 0
    return _StubCapture({
        "generated_token_ids": np.array([10, 11, 12][:steps], dtype=np.int64),
        "mlp_states": mlp,
        "pre_selection_logits": logits,
        "residual_states": rng.standard_normal((steps, layers, hidden)).astype(np.float32),
    })


def _run(req):
    async def drive():
        return [e async for e in ES.resolve_trace_stream(req)]
    return asyncio.run(drive())


def test_resolver_uses_fake_when_no_runtime_installed():
    ES.clear_real_runtime_provider()
    assert ES.real_runtime_available() is False
    events = _run(CreateSessionRequest(prompt="x", seed=1, max_new_tokens=2))
    # fake stream still works and is schema-valid
    assert events[0].type == "manifest"
    assert events[-1].type == "complete"


def test_real_route_emits_measured_values_and_honest_absences(monkeypatch):
    monkeypatch.setattr(ES, "capture_greedy_trajectory", None, raising=False)

    def fake_capture(runtime, **kwargs):
        return _canned_capture(steps=3)

    # patch the lazily-imported symbol in the engine module the real stream uses
    import app.runtime.open_weight.engine as engine
    monkeypatch.setattr(engine, "capture_greedy_trajectory", fake_capture)

    ES.set_real_runtime_provider(lambda: _StubRuntime())
    try:
        assert ES.real_runtime_available() is True
        events = _run(CreateSessionRequest(prompt="Where is Paris", seed=0, max_new_tokens=3))
    finally:
        ES.clear_real_runtime_provider()

    types = [e.type for e in events]
    assert types[0] == "manifest"
    assert types.count("token") == 3
    assert types[-1] == "complete"

    manifest_ev = events[0]
    assert manifest_ev.manifest.is_real_model is True  # real route tells the truth

    tokens = [e for e in events if e.type == "token"]
    assert tokens[0].token == " Paris"
    # confidence is a real softmax of the logit row, not a constant / RNG band
    assert tokens[0].confidence > 0.99                 # step 0 was peaked
    assert tokens[1].confidence < 0.10                 # step 1 was flat (1/vocab)
    assert len({round(t.confidence, 6) for t in tokens}) > 1
    # real top neuron from mlp_states
    top = tokens[0].top_activated_neurons[0]
    assert (top.layer, top.index) == (7, 42) and top.activation == 99.0
    # honest absences -- never fabricated
    for t in tokens:
        assert t.mode7_attribution == []
        assert t.foundation_probe is None
        assert t.rpm_gate_check is None
        assert t.verification_stack is None
