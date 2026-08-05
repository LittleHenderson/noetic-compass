"""Real-mode dispatch test — exercises stream_real_trace + stream_trace's
real-vs-fake dispatcher without needing actual Pythia weights.

We mock the LoadedModel singleton so ``is_real`` reports True, and we
inject a stub pythia_runner.run_pythia that yields synthetic token dicts.
The point of these tests is the dispatcher + event ordering + Error
fallback — not the real model forward (that's verified by hand via
M2_ACCEPTANCE.md on a RunPod box).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.runtime import event_stream, model_loader
from app.runtime.model_loader import LoadedModel
from app.schemas.manifest import ModelManifest
from app.schemas.requests import CreateSessionRequest


def _real_manifest() -> ModelManifest:
    return model_loader.PYTHIA_160M_MANIFEST.model_copy(
        update={
            "is_real_model": True,
            "execution_kind": "real_model_weights",
            "resolved_revision": model_loader.PYTHIA_160M_REVISION,
            "revision_verified": True,
            "weights_filename": model_loader.PYTHIA_160M_WEIGHTS_FILENAME,
            "weights_sha256": model_loader.PYTHIA_160M_WEIGHTS_SHA256,
            "weights_bytes": model_loader.PYTHIA_160M_WEIGHTS_BYTES,
            "weights_hash_verified": True,
            "model_identity_status": "PINNED_REVISION_AND_WEIGHTS_SHA256",
        }
    )


def _force_real_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a singleton claiming a real model is loaded."""
    loaded = LoadedModel(
        manifest=_real_manifest(),
        model=object(),  # truthy placeholder so is_real is True
        tokenizer=object(),
    )
    monkeypatch.setattr(model_loader, "_LOADED", loaded)


async def _drain(req: CreateSessionRequest) -> list[Any]:
    out: list[Any] = []
    async for event in event_stream.stream_trace(req):
        out.append(event)
    return out


def test_real_mode_dispatch_uses_pythia_runner(monkeypatch: pytest.MonkeyPatch):
    _force_real_loaded(monkeypatch)

    # Stub the real runner so we don't need actual weights.
    async def _fake_run_pythia(req, model, tokenizer, n_layers):  # noqa: ARG001
        for i in range(4):
            yield {
                "token_index": i,
                "token": f" t{i}",
                "top_activated_neurons": [{"layer": 0, "index": i, "activation": 0.4}],
                "mode7_attribution": [
                    {"from_token_index": None, "to_token_index": 0, "weight": 1.0}
                    if i == 0
                    else {"from_token_index": 0, "to_token_index": i, "weight": 0.5}
                ],
                "confidence": 0.42,
            }

    from app.runtime import pythia_runner

    monkeypatch.setattr(pythia_runner, "run_pythia", _fake_run_pythia)

    req = CreateSessionRequest(prompt="hello world", max_new_tokens=4)
    events = asyncio.run(_drain(req))

    # First event must be the manifest; first manifest must claim is_real_model.
    assert events[0].type == "manifest"
    assert events[0].manifest.is_real_model is True
    # Knob-resolution echo (new; carries what the worker actually used).
    assert events[1].type == "knob_resolution"
    # Then neuron_covers.
    assert events[2].type == "neuron_covers"
    # Token events, then complete.
    token_events = [e for e in events if e.type == "token"]
    assert len(token_events) == 4
    assert token_events[0].token == " t0"
    assert events[-1].type == "complete"
    assert events[-1].total_tokens == 4


def test_real_mode_emits_error_on_runner_failure(monkeypatch: pytest.MonkeyPatch):
    _force_real_loaded(monkeypatch)

    async def _broken_run_pythia(req, model, tokenizer, n_layers):  # noqa: ARG001
        # Async generators must yield at least once before raising for the
        # error to land inside the consumer's try/except. We yield one
        # token then raise.
        yield {
            "token_index": 0,
            "token": " ok",
            "top_activated_neurons": [],
            "mode7_attribution": [],
            "confidence": None,
        }
        raise RuntimeError("boom — simulated GPU OOM")

    from app.runtime import pythia_runner

    monkeypatch.setattr(pythia_runner, "run_pythia", _broken_run_pythia)

    req = CreateSessionRequest(prompt="anything")
    events = asyncio.run(_drain(req))

    types = [e.type for e in events]
    # manifest, covers, one token, then error — NO complete event.
    assert types[0] == "manifest"
    assert "error" in types
    assert "complete" not in types
    err = next(e for e in events if e.type == "error")
    assert "boom" in err.message
    assert err.retryable is True


def test_demo_dispatch_when_no_real_model(client):
    """Without forcing a real load, the dispatcher must pick the fake stream."""
    r = client.post(
        "/sessions/dump",
        json={"prompt": "no real model here", "seed": 1, "max_new_tokens": 3},
    )
    assert r.status_code == 200
    events = r.json()["events"]
    # Manifest still flows, but is_real_model is False (demo mode).
    assert events[0]["type"] == "manifest"
    assert events[0]["manifest"]["is_real_model"] is False
    # Three token events + complete.
    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) == 3
    assert events[-1]["type"] == "complete"
