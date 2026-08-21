"""Event stream -- milestone 1 emits a fake but schema-valid trace.

Per the locked plan: prove the interface end-to-end first. Real Pythia
forward lands in milestone 2 (pythia_runner.run_pythia).

The fake stream:
  1. Emits ModelManifest (so the UI knows what model it would have hit).
  2. Emits NeuronCoversEvent (so the Blindspots overlay has something to
     paint).
  3. Tokenises the prompt very crudely (whitespace split), then emits a
     TokenEvent per token with deterministic-looking activations + Mode 7
     arcs derived from a seeded RNG so demos are reproducible.
  4. Emits CompleteEvent.
"""

from __future__ import annotations

import asyncio
import random
from typing import AsyncIterator

from ..schemas.events import (
    AttentionSummary,
    CompleteEvent,
    CoverConfidence,
    LiveTraceEvent,
    ManifestEvent,
    MethodRuntimeStatusEvent,
    Mode7Edge,
    NeuronActivation,
    NeuronCoversEvent,
    RpmGateCheckTrace,
    TokenEvent,
    VerificationStackTrace,
)
from ..schemas.methods import method_runtime_statuses
from ..schemas.requests import CreateSessionRequest
from .cover_library import CoverLibraryPayload, LEGACY_F1_COVER_DEMO
from .cover_library import load_default_cover_payload
from .model_loader import get_manifest
from .probe_runner import RuntimeProbeConfig, resolve_probes, resolve_runtime_config


def _fake_neurons(
    rng: random.Random,
    config: RuntimeProbeConfig,
) -> list[NeuronActivation]:
    """Top-k activated neurons for a token -- k random hits across layers."""
    out: list[NeuronActivation] = []
    layers = config.foundation_layer_range or tuple(range(12))
    for _ in range(config.foundation_top_k):
        layer = layers[rng.randrange(len(layers))]
        index = rng.randint(0, 3071)
        activation = rng.uniform(0.30, 0.95)
        out.append(NeuronActivation(layer=layer, index=index, activation=activation))
    return out


def _fake_mode7(rng: random.Random, current: int) -> list[Mode7Edge]:
    """Mode 7 attribution -- current token points back to up to 3 earlier ones."""
    if current == 0:
        return [Mode7Edge(from_token_index=None, to_token_index=0, weight=1.0)]
    n_edges = min(current, 3)
    targets = rng.sample(range(current), n_edges)
    return [
        Mode7Edge(
            from_token_index=t,
            to_token_index=current,
            weight=round(rng.uniform(0.25, 0.95), 3),
        )
        for t in targets
    ]


def _tokenise(prompt: str) -> list[str]:
    """Whitespace tokeniser -- milestone-1 stand-in for the real BPE.

    Real tokenisation arrives with milestone 2 when the actual tokenizer
    is loaded by model_loader. For schema validation + UI rendering this
    is sufficient (UI just gets strings).
    """
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


def _fake_foundation_probe(rng: random.Random) -> list[float]:
    scores = [rng.uniform(0.05, 0.95) for _ in range(7)]
    total = sum(scores) or 1.0
    return [round(score / total, 4) for score in scores]


def _fake_rpm_trace(rng: random.Random, config: RuntimeProbeConfig) -> RpmGateCheckTrace:
    score = round(rng.uniform(0.2, 0.9), 3)
    attention = None
    if config.rpm_emit_attention:
        attention = [
            AttentionSummary(
                layer=layer,
                head=idx,
                weight=round(rng.uniform(0.25, 0.95), 3),
            )
            for idx, layer in enumerate(config.foundation_layer_range[:3])
        ]
    return RpmGateCheckTrace(
        strictness_threshold=config.rpm_strictness_threshold,
        score=score,
        passed=score >= config.rpm_strictness_threshold,
        attention_summary=attention,
    )


def _fake_verification_trace(
    confidence: float,
    config: RuntimeProbeConfig,
) -> VerificationStackTrace:
    threshold_by_mode = {
        "HIGH_PRECISION": 0.9,
        "BALANCED": 0.65,
        "MAX_COVERAGE_TRIAGE": 0.4,
    }
    threshold = threshold_by_mode.get(config.verification_mode, 0.65)
    return VerificationStackTrace(
        mode=config.verification_mode,
        verdict="ACCEPT" if confidence >= threshold else "SUPPRESS",
        margin=round(abs(confidence - threshold), 3),
    )


def _label_layer(label: str) -> int | None:
    if not label.startswith("L") or "N" not in label:
        return None
    layer_text = label[1 : label.index("N")]
    try:
        return int(layer_text)
    except ValueError:
        return None


def _filter_cover_payload(
    payload: CoverLibraryPayload,
    config: RuntimeProbeConfig,
) -> NeuronCoversEvent:
    if not config.is_active("blindspot_detection"):
        return NeuronCoversEvent()

    if config.blindspot_scope == "one_drive":
        class_keys = [f"{config.blindspot_drive}{register}" for register in ("A", "T", "f", "E")]
    else:
        class_keys = list(payload.per_class_neuron_covers)

    layer_filter = set(config.blindspot_layer_range)
    covers: dict[str, list[str]] = {}
    evidence = {}
    for class_key in class_keys:
        labels = payload.per_class_neuron_covers.get(class_key, [])
        used_layer_fallback = False
        if layer_filter:
            labels = [
                label
                for label in labels
                if (layer := _label_layer(label)) is not None and layer in layer_filter
            ]
        if not labels and layer_filter:
            labels = [
                label
                for label in LEGACY_F1_COVER_DEMO.get(class_key, [])
                if (layer := _label_layer(label)) is not None and layer in layer_filter
            ]
            used_layer_fallback = bool(labels)
        if not labels:
            continue
        covers[class_key] = labels
        row_evidence = payload.cover_evidence.get(class_key)
        if row_evidence is not None:
            if used_layer_fallback:
                fallback_confidence = CoverConfidence(
                    status="unavailable",
                    reason=(
                        "no Stage 27F row evidence for requested layer-filtered "
                        "cover; cover-level confidence requires targeted_drop and "
                        "clean_margin for the emitted cover"
                    ),
                    provenance={
                        "source_stage": "Stage 27F",
                        "confidence_scope": "cover-level",
                        "target": class_key,
                        "requested_layers": sorted(layer_filter),
                    },
                )
                evidence[class_key] = row_evidence.model_copy(
                    update={
                        "neuron_cover": labels,
                        "clean_margin": None,
                        "targeted_drop": None,
                        "confidence": fallback_confidence,
                    }
                )
            else:
                evidence[class_key] = row_evidence.model_copy(update={"neuron_cover": labels})
    return NeuronCoversEvent(
        per_class_neuron_covers=covers,
        cover_evidence=evidence,
    )


async def stream_fake_trace(req: CreateSessionRequest) -> AsyncIterator[LiveTraceEvent]:
    """Emit a fake-but-schema-valid trace for the given request.

    Milestone 2 swaps the per-token block here for a real pythia_runner call;
    everything else (manifest, covers, completion) stays.
    """
    manifest = get_manifest(req.model_id)
    yield ManifestEvent(manifest=manifest)

    _ = resolve_probes(req.probes)  # Reserved for milestone 2.
    runtime_config = resolve_runtime_config(
        req.method_configs,
        n_layers=manifest.model_arch.n_layers,
    )

    cover_payload = load_default_cover_payload()
    yield _filter_cover_payload(cover_payload, runtime_config)
    yield MethodRuntimeStatusEvent(methods=method_runtime_statuses(req.method_configs))

    seed = req.seed if req.seed is not None else 1234
    rng = random.Random(seed)
    tokens = _tokenise(req.prompt)
    max_new = min(req.max_new_tokens, 24)
    for i in range(max_new):
        # Cycle through the prompt's own tokens -- milestone-1 stand-in. The
        # real runner will produce continuations from Pythia.
        tok = tokens[i % len(tokens)]
        confidence = round(rng.uniform(0.55, 0.95), 3)
        yield TokenEvent(
            token_index=i,
            token=tok,
            top_activated_neurons=(
                _fake_neurons(rng, runtime_config)
                if runtime_config.is_active("foundation_probe")
                else []
            ),
            mode7_attribution=_fake_mode7(rng, i),
            confidence=confidence,
            foundation_probe=(
                _fake_foundation_probe(rng)
                if runtime_config.is_active("foundation_probe")
                else None
            ),
            rpm_gate_check=(
                _fake_rpm_trace(rng, runtime_config)
                if runtime_config.is_active("rpm_gate_check")
                else None
            ),
            verification_stack=(
                _fake_verification_trace(confidence, runtime_config)
                if runtime_config.is_active("verification_stack")
                else None
            ),
        )
        # Small wait keeps SSE clients from getting one giant flush.
        await asyncio.sleep(0.04)

    yield CompleteEvent(total_tokens=max_new)


# ---------------------------------------------------------------------------
# Milestone 2: the REAL live route.
#
# stream_real_trace replaces the fabricated per-token block of
# stream_fake_trace with values MEASURED from a real forward pass through the
# attested open-weight engine (the same load_open_weight_runtime /
# capture_greedy_trajectory path validated in the detector work). Every field
# that stream_fake_trace drew from an RNG is now either a real measurement or
# an explicit absence -- never a fabricated number:
#
#   token                 -> the real generated token id, decoded
#   confidence            -> softmax(pre_selection_logits[step]).max()  (real)
#   top_activated_neurons -> top-k by |mlp_states[step]|, real (layer,index)
#   mode7_attribution     -> []   (attention is not captured; not fabricated)
#   foundation_probe      -> None (CAS probe not measured here; not fabricated)
#   rpm_gate_check        -> None (not measured here; not fabricated)
#   verification_stack    -> None (not measured here; not fabricated)
#
# The manifest / covers / method-status preamble and the CompleteEvent are
# identical to the fake stream, so the UI contract is unchanged.
# ---------------------------------------------------------------------------

from typing import Callable, Optional

# Installed at app startup to point the live route at a loaded real runtime.
# When None, resolve_trace_stream falls back to the fake stream, so tests and
# demos with no model present keep working unchanged.
_REAL_RUNTIME_PROVIDER: Optional[Callable[[], object]] = None


def set_real_runtime_provider(provider: Callable[[], object]) -> None:
    """Install a callable returning a loaded open-weight runtime."""
    global _REAL_RUNTIME_PROVIDER
    _REAL_RUNTIME_PROVIDER = provider


def clear_real_runtime_provider() -> None:
    global _REAL_RUNTIME_PROVIDER
    _REAL_RUNTIME_PROVIDER = None


def real_runtime_available() -> bool:
    return _REAL_RUNTIME_PROVIDER is not None


def _confidence_from_logits(logit_row) -> float:
    import numpy as np

    row = np.asarray(logit_row, dtype=np.float64)
    row = row - row.max()
    probs = np.exp(row)
    probs /= probs.sum()
    return float(min(1.0, max(0.0, probs.max())))


def _real_top_neurons(mlp_step, config: RuntimeProbeConfig) -> list[NeuronActivation]:
    """Top-k neurons for this token by |activation|, measured from mlp_states.

    mlp_step is (layers, hidden). Layers are optionally restricted to the
    configured foundation range so the overlay matches the probe config.
    """
    import numpy as np

    arr = np.asarray(mlp_step, dtype=np.float64)  # (layers, hidden)
    layer_range = config.foundation_layer_range
    if layer_range:
        mask_layers = list(layer_range)
    else:
        mask_layers = list(range(arr.shape[0]))
    k = max(1, config.foundation_top_k)
    candidates: list[NeuronActivation] = []
    for layer in mask_layers:
        if layer < 0 or layer >= arr.shape[0]:
            continue
        row = arr[layer]
        idx = int(np.argmax(np.abs(row)))
        candidates.append(
            NeuronActivation(layer=int(layer), index=idx, activation=float(row[idx]))
        )
    candidates.sort(key=lambda n: abs(n.activation), reverse=True)
    return candidates[:k]


async def stream_real_trace(req: CreateSessionRequest, *, runtime) -> AsyncIterator[LiveTraceEvent]:
    """Emit a REAL, measured trace for the request through the attested engine."""
    from .open_weight.engine import capture_greedy_trajectory

    manifest = get_manifest(req.model_id)
    # This IS a real forward pass, so the manifest must say so -- the UI's
    # is_real_model flag has to tell the truth on the real route.
    manifest = manifest.model_copy(update={"is_real_model": True})
    yield ManifestEvent(manifest=manifest)

    _ = resolve_probes(req.probes)
    runtime_config = resolve_runtime_config(
        req.method_configs,
        n_layers=manifest.model_arch.n_layers,
    )
    cover_payload = load_default_cover_payload()
    yield _filter_cover_payload(cover_payload, runtime_config)
    yield MethodRuntimeStatusEvent(methods=method_runtime_statuses(req.method_configs))

    max_new = min(req.max_new_tokens, 24)
    capture = await asyncio.to_thread(
        capture_greedy_trajectory,
        runtime,
        scenario_id=f"live-{req.seed if req.seed is not None else 0}",
        prompt=req.prompt,
        max_new_tokens=max_new,
        seed=req.seed if req.seed is not None else 0,
    )
    arrays = capture.arrays
    token_ids = arrays["generated_token_ids"]
    mlp = arrays["mlp_states"]
    logits = arrays["pre_selection_logits"]
    emit_probe = runtime_config.is_active("foundation_probe")

    for i in range(len(token_ids)):
        token_text = runtime.tokenizer.decode([int(token_ids[i])])
        yield TokenEvent(
            token_index=i,
            token=token_text,
            top_activated_neurons=(_real_top_neurons(mlp[i], runtime_config) if emit_probe else []),
            mode7_attribution=[],       # real attention not captured -- not fabricated
            confidence=_confidence_from_logits(logits[i]),
            foundation_probe=None,      # CAS probe not measured here -- not fabricated
            rpm_gate_check=None,        # not measured here -- not fabricated
            verification_stack=None,    # not measured here -- not fabricated
        )
        await asyncio.sleep(0.0)

    yield CompleteEvent(total_tokens=int(len(token_ids)))


def resolve_trace_stream(req: CreateSessionRequest) -> AsyncIterator[LiveTraceEvent]:
    """The live route's entry point: real when a runtime is installed, else fake.

    This is the replacement of the fake live route: production installs a real
    runtime provider and the live endpoints emit measured traces; with no model
    present (tests, demos) it transparently falls back to the schema-valid fake
    stream, so nothing that depended on the fake route breaks.
    """
    if _REAL_RUNTIME_PROVIDER is not None:
        return stream_real_trace(req, runtime=_REAL_RUNTIME_PROVIDER())
    return stream_fake_trace(req)
