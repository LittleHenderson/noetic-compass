"""Ablation probe tests — the live worker's first causal proof.

Two layers of coverage, neither of which downloads Pythia weights:

1. Demo mode (no real weights): ``stream_fake_trace`` / ``stream_trace`` must
   emit a schema-valid ``ablation_effect`` event flagged ``is_real_model=False``
   with EVERY numeric delta left ``None``. Demo mode must never fabricate a
   causal number.

2. Real measurement on a tiny hand-built ``nn.Module`` whose ``.mlp`` modules
   genuinely fire the forward hook. ``run_real_ablation_effect`` runs the real
   hook + delta-measurement code path (the same one Pythia-160M would use) and
   must return ``is_real_model=True`` with real, finite measured deltas. The
   module is constructed so zeroing the target unit demonstrably moves the
   next-token logits — a real causal effect, no download required.

The trigger contract (ablation requested via the ``ablation_target`` field OR a
``"causal_ablation"`` probe; absent → no ablation event) is covered too, to lock
in backward compatibility with existing demo traces.
"""

from __future__ import annotations

import asyncio
import math
from typing import Any

import pytest

from app.runtime import event_stream, model_loader
from app.runtime.ablation_probe import (
    ablation_requested,
    demo_ablation_control,
    demo_ablation_effect,
    resolve_ablation_target,
    run_real_ablation_control,
    run_real_ablation_effect,
)
from app.runtime.model_loader import LoadedModel
from app.schemas.requests import AblationTargetRequest, CreateSessionRequest


# ---------------------------------------------------------------------------
# Trigger contract — backward-compatible request gating.
# ---------------------------------------------------------------------------


def test_ablation_not_requested_by_default():
    req = CreateSessionRequest(prompt="hi", max_new_tokens=2)
    assert ablation_requested(req) is False


def test_ablation_requested_via_probe():
    req = CreateSessionRequest(
        prompt="hi", max_new_tokens=2, probes=["causal_ablation"]
    )
    assert ablation_requested(req) is True
    target = resolve_ablation_target(req)
    # Bare probe with no explicit target defaults to a real, fixed unit.
    assert target.layer == 0
    assert target.unit == 0
    assert target.mode == "zero"


def test_ablation_requested_via_target_field():
    req = CreateSessionRequest(
        prompt="hi",
        max_new_tokens=2,
        ablation_target=AblationTargetRequest(layer=1, unit=5, mode="mean"),
    )
    assert ablation_requested(req) is True
    target = resolve_ablation_target(req)
    assert (target.layer, target.unit, target.mode) == (1, 5, "mean")


# ---------------------------------------------------------------------------
# Demo mode — schema-valid, explicitly NOT a real measurement.
# ---------------------------------------------------------------------------


def test_demo_ablation_effect_has_no_numbers():
    event = demo_ablation_effect(AblationTargetRequest(layer=0, unit=0, mode="zero"))
    assert event.type == "ablation_effect"
    assert event.is_real_model is False
    # Every measured field MUST be None in demo mode — no fabricated numbers.
    assert event.baseline_top_token is None
    assert event.ablated_top_token is None
    assert event.baseline_top_token_id is None
    assert event.ablated_top_token_id is None
    assert event.logit_delta is None
    assert event.confidence_delta is None
    assert event.top_token_changed is None


def test_demo_ablation_control_has_no_numbers():
    event = demo_ablation_control(AblationTargetRequest(layer=0, unit=0, mode="zero"))
    assert event.type == "ablation_control_effect"
    assert event.is_real_model is False
    # Every measured field MUST be None/zero in demo mode — no fabricated numbers.
    assert event.n_controls == 0
    assert event.control_units is None
    assert event.target_abs_logit_delta is None
    assert event.control_mean_abs_logit_delta is None
    assert event.control_max_abs_logit_delta is None
    assert event.margin_over_control_max is None
    assert event.selectivity_passed is None
    assert event.seed is None


async def _drain(req: CreateSessionRequest) -> list[Any]:
    out: list[Any] = []
    async for event in event_stream.stream_trace(req):
        out.append(event)
    return out


def test_demo_stream_emits_demo_flagged_ablation_when_requested():
    """No real model loaded → dispatcher picks the fake stream, which must
    still emit a demo-flagged ablation_effect (is_real_model=False) when the
    caller asked for a causal ablation."""
    req = CreateSessionRequest(
        prompt="trace me",
        seed=7,
        max_new_tokens=3,
        probes=["active_trace", "causal_ablation"],
    )
    events = asyncio.run(_drain(req))
    ablation = [e for e in events if e.type == "ablation_effect"]
    assert len(ablation) == 1
    assert ablation[0].is_real_model is False
    assert ablation[0].logit_delta is None
    # Ablation event lands before the completion event.
    types = [e.type for e in events]
    assert types.index("ablation_effect") < types.index("complete")


def test_demo_stream_emits_demo_flagged_control_when_requested():
    """No real model loaded → the fake stream must ALSO emit a demo-flagged
    ablation_control_effect (is_real_model=False) when a causal ablation is
    requested. Demo mode never fabricates a control selectivity number."""
    req = CreateSessionRequest(
        prompt="trace me",
        seed=7,
        max_new_tokens=3,
        probes=["active_trace", "causal_ablation"],
    )
    events = asyncio.run(_drain(req))
    control = [e for e in events if e.type == "ablation_control_effect"]
    assert len(control) == 1
    assert control[0].is_real_model is False
    assert control[0].target_abs_logit_delta is None
    assert control[0].selectivity_passed is None
    # Control event lands before the completion event.
    types = [e.type for e in events]
    assert types.index("ablation_control_effect") < types.index("complete")


def test_demo_stream_omits_ablation_when_not_requested():
    """Backward compatibility: a request without any ablation trigger must
    produce NO ablation_effect event (existing demo traces are unchanged)."""
    req = CreateSessionRequest(
        prompt="trace me", seed=7, max_new_tokens=3, probes=["active_trace"]
    )
    events = asyncio.run(_drain(req))
    assert not any(e.type == "ablation_effect" for e in events)


# ---------------------------------------------------------------------------
# Real measurement on a tiny hand-built module (no Pythia download).
# ---------------------------------------------------------------------------


def _build_fake_pythia(width: int = 8, vocab: int = 16, seq: int = 4) -> Any:
    """A minimal real nn.Module shaped like Pythia for the ablation hook.

    Layout mirrors what ``_get_pythia_layers`` + ``_ablate_mlp_unit`` expect:
    ``model.gpt_neox.layers[i].mlp`` is a real module whose forward returns a
    ``[batch, seq, width]`` tensor, so the registered forward hook genuinely
    fires and can ablate ``[0, -1, unit]``. The LM head reads the LAST-token
    MLP output, so zeroing a unit that dominates that position demonstrably
    moves the next-token logits — a real causal effect.
    """
    import torch
    from torch import nn

    class FakeMLP(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            # Identity-ish content map: each position gets a fixed activation
            # vector; the last position is dominated by unit 0 so ablating it
            # moves the argmax. Not learned — fixed so the test is determinate.
            base = torch.zeros(seq, width)
            for pos in range(seq):
                for unit in range(width):
                    base[pos, unit] = float((pos + 1) * (unit + 1)) * 0.1
            # Make unit 0 dominate the final (predicting) position.
            base[-1, 0] = 9.0
            self.register_buffer("content", base)

        def forward(self, hidden: Any) -> Any:  # noqa: D401 - torch hook target
            batch = hidden.shape[0]
            return self.content.unsqueeze(0).expand(batch, seq, width).clone()

    class FakeLayer(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.mlp = FakeMLP()

    class FakeGptNeoX(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.layers = nn.ModuleList([FakeLayer()])

    class FakeOutput:
        def __init__(self, logits: Any) -> None:
            self.logits = logits

    class FakeModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.gpt_neox = FakeGptNeoX()
            # LM head maps the last-token MLP output (width) to vocab logits.
            # Deterministic weights so unit 0 maps strongly onto token id 1.
            w = torch.zeros(vocab, width)
            w[1, 0] = 1.0  # token 1 fires iff MLP unit 0 is active
            for tok in range(vocab):
                for unit in range(width):
                    w[tok, unit] += float((tok + 1) * (unit + 1)) * 0.001
            self.register_buffer("head_w", w)
            # A real parameter so ``next(model.parameters()).device`` works.
            self._anchor = nn.Parameter(torch.zeros(1))

        def forward(
            self,
            input_ids: Any,
            output_hidden_states: bool = False,  # noqa: ARG002
            output_attentions: bool = False,  # noqa: ARG002
        ) -> Any:
            # Run the (hookable) MLP so any registered forward hook fires and
            # can ablate the last-token unit before logits are computed.
            mlp_out = self.gpt_neox.layers[0].mlp(
                torch.zeros(input_ids.shape[0], seq, width)
            )
            last = mlp_out[:, -1, :]  # [batch, width]
            logits_last = last @ self.head_w.t()  # [batch, vocab]
            # Shape logits as [batch, seq, vocab]; only the last row is read.
            logits = torch.zeros(input_ids.shape[0], seq, vocab)
            logits[:, -1, :] = logits_last
            return FakeOutput(logits)

    return FakeModel()


class _FakeTokenizer:
    """Tiny tokenizer stand-in: fixed ids + reversible single-token decode."""

    def __call__(self, prompt: str, return_tensors: str = "pt") -> Any:  # noqa: ARG002
        import torch

        class _Encoded:
            input_ids = torch.tensor([[1, 2, 3, 4]])

        return _Encoded()

    def decode(self, ids: list[int]) -> str:
        return f"<tok{int(ids[0])}>"


def test_real_ablation_measures_finite_deltas_and_flips_proof():
    """run_real_ablation_effect on a real (tiny) module must produce a REAL
    measurement: is_real_model True, finite logit_delta, and (because unit 0
    dominates the predicting position) a changed top token."""
    model = _build_fake_pythia()
    tokenizer = _FakeTokenizer()
    target = AblationTargetRequest(layer=0, unit=0, mode="zero")
    req = CreateSessionRequest(prompt="anything", max_new_tokens=1)

    event = run_real_ablation_effect(req, model, tokenizer, n_layers=1, target=target)

    assert event.type == "ablation_effect"
    assert event.is_real_model is True
    # Real measured numbers, all finite — never None on a real pass.
    assert event.logit_delta is not None
    assert math.isfinite(event.logit_delta)
    assert event.baseline_top_token_id is not None
    assert event.ablated_top_token_id is not None
    # Unit 0 drives the baseline top token; zeroing it must move the argmax.
    assert event.baseline_top_token_id == 1
    assert event.top_token_changed is True
    assert event.ablated_top_token_id != event.baseline_top_token_id
    # Zeroing the dominating unit drops that token's own logit → negative delta.
    assert event.logit_delta < 0
    assert event.target == {"layer": 0, "unit": 0}
    assert event.mode == "zero"


def test_real_ablation_mean_mode_runs_and_is_real():
    """Mean-patch mode must also yield a real measurement (is_real_model True,
    finite delta). The hook path differs (mean vs zero) but the honesty
    contract is identical."""
    model = _build_fake_pythia()
    tokenizer = _FakeTokenizer()
    target = AblationTargetRequest(layer=0, unit=0, mode="mean")
    req = CreateSessionRequest(prompt="anything", max_new_tokens=1)

    event = run_real_ablation_effect(req, model, tokenizer, n_layers=1, target=target)

    assert event.is_real_model is True
    assert event.mode == "mean"
    assert event.logit_delta is not None
    assert math.isfinite(event.logit_delta)


def test_real_stream_emits_real_ablation_event(monkeypatch: pytest.MonkeyPatch):
    """End-to-end through stream_real_trace: with a real-flagged loaded model
    and a stubbed token runner, requesting a causal ablation must yield a real
    ablation_effect event (is_real_model True) before the completion event."""

    loaded = LoadedModel(
        manifest=model_loader.PYTHIA_160M_MANIFEST.model_copy(
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
        ),
        model=_build_fake_pythia(),
        tokenizer=_FakeTokenizer(),
    )
    monkeypatch.setattr(model_loader, "_LOADED", loaded)

    async def _fake_run_pythia(req, model, tokenizer, n_layers):  # noqa: ARG001
        yield {
            "token_index": 0,
            "token": " ok",
            "top_activated_neurons": [],
            "mode7_attribution": [],
            "confidence": 0.5,
        }

    from app.runtime import pythia_runner

    monkeypatch.setattr(pythia_runner, "run_pythia", _fake_run_pythia)
    # n_layers comes from the manifest's model_arch; our fake module only has
    # one real layer, so force the manifest arch to match to keep the hook in
    # range. PYTHIA_160M_MANIFEST has 12 layers; the ablation target is layer 0
    # which is always in range, so no override is needed.

    req = CreateSessionRequest(
        prompt="trace me",
        max_new_tokens=1,
        probes=["active_trace", "causal_ablation"],
    )
    events = asyncio.run(_drain(req))

    ablation = [e for e in events if e.type == "ablation_effect"]
    assert len(ablation) == 1
    assert ablation[0].is_real_model is True
    assert ablation[0].logit_delta is not None
    types = [e.type for e in events]
    assert types.index("ablation_effect") < types.index("complete")


# ---------------------------------------------------------------------------
# Matched-control selectivity on the tiny module — the first control proof.
# ---------------------------------------------------------------------------


def test_real_ablation_control_measures_real_selectivity():
    """run_real_ablation_control on a real (tiny) module must produce a REAL
    matched-control measurement: is_real_model True, a full set of same-layer
    control units, and (because unit 0 dominates the predicting position) a
    target |logit delta| that strictly beats every random same-layer control —
    selectivity_passed True with a positive margin. No Pythia download."""
    model = _build_fake_pythia()
    tokenizer = _FakeTokenizer()
    target = AblationTargetRequest(layer=0, unit=0, mode="zero")
    req = CreateSessionRequest(prompt="anything", max_new_tokens=1)

    event = run_real_ablation_control(
        req, model, tokenizer, n_layers=1, target=target, n_controls=8, seed=42
    )

    assert event.type == "ablation_control_effect"
    assert event.is_real_model is True
    # width is 8, target unit 0 excluded → all 7 sibling units sampled.
    assert event.n_controls == 7
    assert event.control_units == [1, 2, 3, 4, 5, 6, 7]
    # Real finite deltas — never None on a real pass.
    assert event.target_abs_logit_delta is not None
    assert event.control_max_abs_logit_delta is not None
    assert math.isfinite(event.target_abs_logit_delta)
    assert math.isfinite(event.control_max_abs_logit_delta)
    # Unit 0 dominates the predicting position, so ablating it moves the
    # baseline-top token's logit far more than any sibling unit.
    assert event.target_abs_logit_delta > event.control_max_abs_logit_delta
    assert event.selectivity_passed is True
    assert event.margin_over_control_max > 0
    assert event.seed == 42
    assert event.target == {"layer": 0, "unit": 0}
    assert event.mode == "zero"


def test_real_ablation_control_out_of_range_layer_is_demo_flagged():
    """If the target layer is out of range (no real control could be sampled),
    run_real_ablation_control must degrade to a demo-flagged event — never claim
    a control proof, never fabricate selectivity numbers."""
    model = _build_fake_pythia()
    tokenizer = _FakeTokenizer()
    # Layer 5 does not exist on the 1-layer fake module → width is None.
    target = AblationTargetRequest(layer=5, unit=0, mode="zero")
    req = CreateSessionRequest(prompt="anything", max_new_tokens=1)

    event = run_real_ablation_control(
        req, model, tokenizer, n_layers=1, target=target
    )

    assert event.type == "ablation_control_effect"
    assert event.is_real_model is False
    assert event.target_abs_logit_delta is None
    assert event.selectivity_passed is None


def test_real_stream_emits_real_control_event(monkeypatch: pytest.MonkeyPatch):
    """End-to-end through stream_real_trace: with a real-flagged loaded model and
    a stubbed token runner, requesting a causal ablation must yield a real
    ablation_control_effect event (is_real_model True), ordered AFTER the
    ablation_effect and BEFORE the completion event."""

    loaded = LoadedModel(
        manifest=model_loader.PYTHIA_160M_MANIFEST.model_copy(
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
        ),
        model=_build_fake_pythia(),
        tokenizer=_FakeTokenizer(),
    )
    monkeypatch.setattr(model_loader, "_LOADED", loaded)

    async def _fake_run_pythia(req, model, tokenizer, n_layers):  # noqa: ARG001
        yield {
            "token_index": 0,
            "token": " ok",
            "top_activated_neurons": [],
            "mode7_attribution": [],
            "confidence": 0.5,
        }

    from app.runtime import pythia_runner

    monkeypatch.setattr(pythia_runner, "run_pythia", _fake_run_pythia)

    req = CreateSessionRequest(
        prompt="trace me",
        max_new_tokens=1,
        probes=["active_trace", "causal_ablation"],
    )
    events = asyncio.run(_drain(req))

    control = [e for e in events if e.type == "ablation_control_effect"]
    assert len(control) == 1
    assert control[0].is_real_model is True
    assert control[0].target_abs_logit_delta is not None
    assert control[0].selectivity_passed is True
    types = [e.type for e in events]
    # Ordering: ablation_effect → ablation_control_effect → complete.
    assert types.index("ablation_effect") < types.index("ablation_control_effect")
    assert types.index("ablation_control_effect") < types.index("complete")
