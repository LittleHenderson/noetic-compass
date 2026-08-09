"""Event stream — dispatches real vs fake based on whether weights are loaded.

M1: fake-only.
M2: real Pythia takes over WHENEVER ``get_loaded_model().is_real`` is True;
fake remains the fallback for demo mode (no torch, no GPU, or
LIVE_TRACE_DEMO_MODE=1).

Cockpit invariant: manifest.is_real_model in the FIRST event tells the UI
which mode it's looking at. The UI MUST surface this in its provenance
badge — "Live · actual weights" only when is_real_model = True.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import AsyncIterator

from ..schemas.events import (
    AblationEffectEvent,
    CompleteEvent,
    ErrorEvent,
    KnobResolutionEvent,
    LiveTraceEvent,
    ManifestEvent,
    Mode7Edge,
    NeuronActivation,
    NeuronCoversEvent,
    TokenEvent,
)
from ..schemas.requests import CreateSessionRequest
from .ablation_probe import (
    ablation_requested,
    demo_ablation_control,
    demo_ablation_effect,
    resolve_ablation_target,
)
from .cover_library import cover_members_for_scope
from .knob_resolution import (
    enabled_methods as _resolve_enabled_methods,
    resolve_knobs,
)
from .model_loader import active_model_binding, get_loaded_model
from .probe_runner import demo_intervention_result, resolve_probes
from .word_spans import build_word_spans

logger = logging.getLogger(__name__)


def _selected_scope(req: CreateSessionRequest) -> str:
    """Pick which calibrated cover scope the live worker should emit."""
    resolved = resolve_knobs(req)
    bs_scope = resolved["blindspot_detection"].get("scope")
    if bs_scope == "all_7":
        return "all_7"
    if isinstance(bs_scope, str) and bs_scope.startswith("F"):
        return bs_scope
    bs_drive = resolved["blindspot_detection"]["drive"]
    if isinstance(bs_drive, str) and bs_drive.startswith("F"):
        return bs_drive
    return "F1"


def _cover_event(req: CreateSessionRequest) -> NeuronCoversEvent:
    probes = _requested_probes(req)
    if (
        "blindspot_covers" not in probes
        or not active_model_binding().stage27f_cover_library_supported
    ):
        return NeuronCoversEvent(per_class_neuron_covers={})
    return NeuronCoversEvent(
        per_class_neuron_covers=cover_members_for_scope(_selected_scope(req)),
    )


def _requested_probes(req: CreateSessionRequest) -> set[str]:
    if req.method_config and "enabled_methods" in req.method_config and not req.probes:
        return set()
    return set(resolve_probes(req.probes))


def _knob_resolution_event(req: CreateSessionRequest) -> KnobResolutionEvent:
    """Build the runtime echo of what the worker resolved from the panel."""
    return KnobResolutionEvent(resolved_knobs=resolve_knobs(req))


def _inversion_risk(
    req: CreateSessionRequest,
    confidence: float,
    activations: list[NeuronActivation],
) -> float | None:
    if "inversion_scan" not in _resolve_enabled_methods(req):
        return None
    threshold = float(resolve_knobs(req)["inversion_scan"]["severity_threshold"])
    activation_pressure = min(max((abs(a.activation) for a in activations), default=0.0), 1.0)
    confidence_pressure = 1.0 - confidence
    risk = max(0.0, min(1.0, (activation_pressure * 0.6) + (confidence_pressure * 0.4)))
    return round(risk, 3) if risk >= threshold else 0.0


# ---------------------------------------------------------------------------
# Demo-mode (M1 carry-over) — fake-but-schema-valid trace.
# Kept here both for fallback and as a sanity-check baseline.
# ---------------------------------------------------------------------------


def _fake_neurons(
    rng: random.Random,
    n_layers: int,
    top_k: int,
    layer_filter: set[int] | None,
) -> list[NeuronActivation]:
    """Generate the same knob-sensitive top-K neuron output the real runner
    would for a forward pass.

    ``top_k`` controls how many neurons are returned. ``layer_filter``
    (when non-empty) constrains which layers can contribute. The fake
    stream is the demo-mode stand-in for the real probe summariser;
    it MUST honour these knobs so demo-mode tests can prove the
    panel's knobs travel all the way through.
    """
    eligible = (
        sorted(layer_filter)
        if layer_filter
        else list(range(n_layers))
    )
    # Guard against an empty layer set so demo mode never crashes.
    if not eligible:
        eligible = list(range(n_layers))
    out: list[NeuronActivation] = []
    for _ in range(max(0, int(top_k))):
        layer = rng.choice(eligible)
        index = rng.randint(0, 3071)
        activation = rng.uniform(0.30, 0.95)
        out.append(NeuronActivation(layer=layer, index=index, activation=activation))
    return out


def _fake_mode7(
    rng: random.Random,
    current: int,
    rpm_threshold: float,
) -> list[Mode7Edge]:
    """Demo Mode 7 edges, filtered to honour the RPM strictness threshold."""
    if current == 0:
        edge = Mode7Edge(from_token_index=None, to_token_index=0, weight=1.0)
        return [edge] if edge.weight >= rpm_threshold else []
    n_edges = min(current, 3)
    targets = rng.sample(range(current), n_edges)
    edges = [
        Mode7Edge(
            from_token_index=t,
            to_token_index=current,
            weight=round(rng.uniform(0.25, 0.95), 3),
        )
        for t in targets
    ]
    if rpm_threshold > 0:
        edges = [e for e in edges if e.weight >= rpm_threshold]
    return edges


def _tokenise_whitespace(prompt: str) -> list[str]:
    pieces: list[str] = []
    cursor = 0
    for raw in prompt.split():
        idx = prompt.find(raw, cursor)
        if idx > cursor:
            pieces.append(prompt[cursor:idx] + raw)
        else:
            pieces.append(raw)
        cursor = idx + len(raw)
    if not pieces:
        return [prompt]
    return pieces


async def stream_fake_trace(req: CreateSessionRequest) -> AsyncIterator[LiveTraceEvent]:
    """Demo-mode trace — schema-valid, deterministic under seed, no real model.

    Now honours the same panel knobs the real runner does
    (foundation_probe.top_k, foundation_probe.layer_range,
    rpm_gate_check.strictness_threshold, drive_local_eraser.drive,
    blindspot_detection.scope, inversion_scan.severity_threshold).
    Tests in ``test_knob_effect.py`` rely on this — they drive the
    fake stream and assert output divergence under the same knob
    plumbing the real runner uses.
    """
    loaded = get_loaded_model()
    yield ManifestEvent(manifest=loaded.manifest)
    yield _knob_resolution_event(req)
    probes = _requested_probes(req)
    yield _cover_event(req)

    resolved = resolve_knobs(req)
    top_k = int(resolved["foundation_probe"]["top_k"])
    layer_list = resolved["foundation_probe"]["layer_range"]
    layer_filter: set[int] | None = set(layer_list) if layer_list else None
    rpm_threshold = float(resolved["rpm_gate_check"]["strictness_threshold"])
    from .pythia_runner import _eraser_intervention

    demo_intervention = _eraser_intervention(
        req,
        execution_kind="demo_schema_only",
        expected_coordinate_width=loaded.manifest.model_arch.mlp_intermediate_dim,
        expected_projected_output_width=loaded.manifest.model_arch.hidden_size,
    )
    demo_result = (
        demo_intervention_result(demo_intervention)
        if demo_intervention is not None
        else None
    )

    seed = req.seed if req.seed is not None else 1234
    rng = random.Random(seed)
    tokens = _tokenise_whitespace(req.prompt)
    max_new = min(req.max_new_tokens, 24)
    emitted_tokens: list[tuple[int, str]] = []
    for i in range(max_new):
        tok = tokens[i % len(tokens)]
        fake_neurons = _fake_neurons(
            rng,
            loaded.manifest.model_arch.n_layers,
            top_k=top_k,
            layer_filter=layer_filter,
        )
        fake_confidence = round(rng.uniform(0.55, 0.95), 3)
        yield TokenEvent(
            token_index=i,
            token=tok,
            top_activated_neurons=fake_neurons
            if "active_trace" in probes
            else [],
            mode7_attribution=_fake_mode7(rng, i, rpm_threshold)
            if "mode7_attribution" in probes
            else [],
            confidence=fake_confidence
            if "confidence_margin" in probes
            else None,
            inversion_risk=_inversion_risk(req, fake_confidence, fake_neurons),
            eraser_intervention_result=demo_result,
        )
        emitted_tokens.append((i, tok))
        await asyncio.sleep(0.04)
    if ablation_requested(req):
        # Demo mode cannot measure a real causal effect (no weights loaded),
        # so emit schema-valid events flagged is_real_model=False with no
        # numeric deltas. The runner keeps causal_proof AND control_proof
        # unavailable for these.
        demo_target = resolve_ablation_target(req)
        yield demo_ablation_effect(demo_target)
        yield demo_ablation_control(demo_target)
    yield build_word_spans(emitted_tokens)
    yield CompleteEvent(total_tokens=max_new)


# ---------------------------------------------------------------------------
# Real Pythia trace — drives event_stream off pythia_runner.run_pythia.
# ---------------------------------------------------------------------------


async def stream_real_trace(req: CreateSessionRequest) -> AsyncIterator[LiveTraceEvent]:
    """Real-model trace using the loaded Pythia + probe hooks."""
    loaded = get_loaded_model()
    if not loaded.is_real:
        # Defensive: if someone routes here when weights aren't loaded,
        # emit an error event so the UI falls back cleanly.
        yield ErrorEvent(
            message="Real Pythia runner invoked but model is not loaded.",
            retryable=False,
        )
        return

    binding = active_model_binding()
    if ablation_requested(req) and not binding.single_unit_causal_ablation_supported:
        yield ErrorEvent(
            message=(
                "Single-unit causal ablation is unavailable for the selected "
                f"model binding {binding.key!r}; no model forward was executed."
            ),
            retryable=False,
        )
        return

    yield ManifestEvent(manifest=loaded.manifest)
    yield _knob_resolution_event(req)
    yield _cover_event(req)

    # Import locally so demo mode can import this module without torch.
    from .pythia_runner import run_pythia

    n_layers = loaded.manifest.model_arch.n_layers
    emitted = 0
    emitted_tokens: list[tuple[int, str]] = []
    try:
        async for token_payload in run_pythia(req, loaded.model, loaded.tokenizer, n_layers):
            event = TokenEvent(**token_payload)
            yield event
            emitted_tokens.append((event.token_index, event.token))
            emitted += 1
    except Exception as exc:  # pragma: no cover — generation-time failures
        logger.exception("stream_real_trace: pythia_runner raised")
        yield ErrorEvent(
            message=f"Live generation failed: {exc!r}. Fall back to REPLAY.",
            retryable=True,
        )
        return

    if ablation_requested(req):
        target = resolve_ablation_target(req)
        try:
            # Import locally so demo mode never needs torch to import this module.
            from .ablation_probe import run_real_ablation_effect

            yield run_real_ablation_effect(
                req,
                loaded.model,
                loaded.tokenizer,
                n_layers,
                target,
                model_binding=binding,
            )
        except Exception:  # pragma: no cover — measurement-time failures
            # A failed measurement is NOT a real causal proof. Degrade to a
            # schema-valid demo-flagged event (is_real_model=False, no deltas)
            # so the runner keeps causal_proof unavailable rather than the
            # whole trace failing.
            logger.exception("stream_real_trace: ablation probe raised")
            yield demo_ablation_effect(target)

        # Matched-control selectivity test — flips control_proof to present
        # ONLY when a real control actually ran (see run_real_ablation_control).
        try:
            from .ablation_probe import run_real_ablation_control

            yield run_real_ablation_control(
                req,
                loaded.model,
                loaded.tokenizer,
                n_layers,
                target,
                model_binding=binding,
            )
        except Exception:  # pragma: no cover — measurement-time failures
            # A failed control measurement is NOT a real control proof. Degrade
            # to a schema-valid demo-flagged event so the runner keeps
            # control_proof unavailable rather than failing the whole trace.
            logger.exception("stream_real_trace: ablation control probe raised")
            yield demo_ablation_control(target)

    yield build_word_spans(emitted_tokens)
    yield CompleteEvent(total_tokens=emitted)


# ---------------------------------------------------------------------------
# Public entry — picks real vs fake based on whether weights are loaded.
# ---------------------------------------------------------------------------


async def stream_trace(req: CreateSessionRequest) -> AsyncIterator[LiveTraceEvent]:
    """Dispatcher: real Pythia if loaded, fake otherwise.

    Routes / tests that want to force one mode can call stream_real_trace
    or stream_fake_trace directly.
    """
    loaded = get_loaded_model()
    if loaded.is_real:
        async for event in stream_real_trace(req):
            yield event
    else:
        async for event in stream_fake_trace(req):
            yield event
