"""Real Pythia-160M runner — generates one token at a time, captures probes.

Driven by event_stream.stream_real_trace. Each iteration:
  1. Tokenise the running prompt+continuation.
  2. Run a forward pass with hooks attached to capture per-layer MLP-post
     activations + attention patterns + last-token logits.
  3. Greedy-decode the next token (or sample, if temperature > 0 + seed set).
  4. Reduce the capture into a TokenProbeSummary.
  5. yield the summary + tokenizer-decoded string for this token.

This is a one-token-at-a-time loop (not model.generate) because we need
the hooks to fire on a per-token forward, AND we need to emit the SSE
event immediately so the cockpit animates as tokens arrive.

Cost note: 24-token continuation at Pythia-160M is ~24 forward passes.
At CPU that's ~5 s; at GPU (RunPod) it's well under 1 s. The cockpit's
SSE pacing keeps the UI smooth either way.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator

from ..schemas.requests import CreateSessionRequest
from ..schemas.manifest import ModelExecutionKind
from .cover_library import MLP_INTERMEDIATE_POST_ACTIVATION, coords_for_drive
from .knob_resolution import (
    enabled_methods as _resolve_enabled_methods,
    resolve_knobs,
)
from .model_loader import ModelBinding, active_model_binding, encode_runtime_prompt
from .probe_runner import (
    EraserIntervention,
    assess_baseline_stability,
    capture_probes,
    finalize_intervention_result,
    mark_unstable_baseline_without_attempt,
    restore_torch_rng_state,
    resolve_probes,
    snapshot_torch_rng_state,
    summarise,
)
from .verification_mode import build_verification_telemetry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _OutputSnapshot:
    logits: Any
    attentions: tuple[Any, ...] | None


def _snapshot_outputs(outputs: Any) -> _OutputSnapshot:
    """Clone the output evidence so a later forward cannot mutate fallback data."""
    logits = outputs.logits.detach().clone()
    raw_attentions = getattr(outputs, "attentions", None)
    attentions = (
        tuple(attention.detach().clone() for attention in raw_attentions)
        if raw_attentions
        else None
    )
    return _OutputSnapshot(logits=logits, attentions=attentions)


async def run_pythia(
    req: CreateSessionRequest,
    model: Any,
    tokenizer: Any,
    n_layers: int,
) -> AsyncIterator[dict]:
    """Real-model token stream.

    Yields one dict per emitted token:
        {
            "token_index": int,
            "token": str,
            "top_activated_neurons": [...],
            "mode7_attribution": [...],
            "confidence": float | None,
        }

    Caller wraps each dict into a TokenEvent.
    """
    import torch

    binding = active_model_binding()
    device = next(model.parameters()).device
    encoded_prompt = encode_runtime_prompt(
        tokenizer,
        req.prompt,
        binding=binding,
    )
    input_ids = encoded_prompt["input_ids"].to(device)
    prompt_len = int(input_ids.shape[1])

    # Apply seed for the (optional) sampling path.
    if req.seed is not None:
        torch.manual_seed(int(req.seed))

    max_new = min(req.max_new_tokens, 24)
    requested_probes = _requested_probes(req)
    resolved = resolve_knobs(req)
    fp_resolved = resolved["foundation_probe"]
    layer_range_list = fp_resolved["layer_range"]
    foundation_layers: set[int] | None = set(layer_range_list) if layer_range_list else None
    top_k = int(fp_resolved["top_k"])
    rpm_threshold = float(resolved["rpm_gate_check"]["strictness_threshold"])
    inversion_threshold = float(resolved["inversion_scan"]["severity_threshold"])
    inversion_active = bool(resolved["inversion_scan"]["active"])
    intervention = _eraser_intervention(
        req,
        execution_kind="real_model_weights",
        expected_coordinate_width=int(model.config.intermediate_size),
        expected_projected_output_width=int(model.config.hidden_size),
        model_binding=binding,
    )

    with torch.no_grad():
        for new_idx in range(max_new):
            intervention_result = None
            abort_after_rejected_intervention = False
            if intervention is None:
                with capture_probes(
                    model,
                    n_layers,
                    probe_binding=binding,
                ) as state:
                    outputs = model(
                        input_ids,
                        output_hidden_states=False,
                        output_attentions=True,
                    )
            else:
                # Two unmodified forwards must first prove exact local output,
                # geometry, hook-cardinality, and Torch-RNG stability. Only a
                # stable baseline is eligible for the intervention attempt.
                baseline_rng_before = snapshot_torch_rng_state()
                with capture_probes(
                    model,
                    n_layers,
                    probe_binding=binding,
                ) as baseline_state:
                    baseline_outputs_live = model(
                        input_ids,
                        output_hidden_states=False,
                        output_attentions=True,
                    )
                baseline_outputs = _snapshot_outputs(baseline_outputs_live)
                baseline_rng_after = snapshot_torch_rng_state()

                restore_torch_rng_state(baseline_rng_before)
                with capture_probes(
                    model,
                    n_layers,
                    probe_binding=binding,
                ) as stability_control_state:
                    stability_control_outputs_live = model(
                        input_ids,
                        output_hidden_states=False,
                        output_attentions=True,
                    )
                stability_control_outputs = _snapshot_outputs(
                    stability_control_outputs_live
                )
                required_layers = {
                    layer for layer, _index in intervention.coords if layer >= 0
                }
                baseline_output_stable, baseline_geometry_stable = (
                    assess_baseline_stability(
                        baseline_state,
                        baseline_outputs.logits[0, -1],
                        stability_control_state,
                        stability_control_outputs.logits[0, -1],
                        required_layers,
                    )
                )

                # A counterfactual is comparable only when it starts from the
                # exact same global Torch generators as both controls.
                restore_torch_rng_state(baseline_rng_before)
                try:
                    if (
                        baseline_output_stable is True
                        and baseline_geometry_stable is True
                    ):
                        with capture_probes(
                            model,
                            n_layers,
                            intervention=intervention,
                            reference_geometry=baseline_state.tensor_geometry,
                            probe_binding=binding,
                        ) as state:
                            outputs = model(
                                input_ids,
                                output_hidden_states=False,
                                output_attentions=True,
                            )
                    else:
                        # Create a typed fail-closed receipt without executing
                        # an intervention against an already-unstable model.
                        with capture_probes(
                            model,
                            n_layers,
                            intervention=intervention,
                            reference_geometry=baseline_state.tensor_geometry,
                            probe_binding=binding,
                        ) as state:
                            mark_unstable_baseline_without_attempt(state)
                        outputs = baseline_outputs
                except Exception:
                    restore_torch_rng_state(baseline_rng_after)
                    raise
                intervention_result = finalize_intervention_result(
                    state,
                    baseline_outputs.logits[0, -1],
                    outputs.logits[0, -1],
                    stability_control_state=stability_control_state,
                    stability_control_output=(
                        stability_control_outputs.logits[0, -1]
                    ),
                )
                if not intervention_result.structurally_valid:
                    # A rejected/failed structural receipt cannot influence
                    # generation or the emitted activation summary. Preserve
                    # its attempted-pass evidence, then fall back atomically
                    # to the paired unmodified forward result.
                    outputs = baseline_outputs
                    state = baseline_state
                    # Make rejected execution observationally atomic: sampling
                    # continues from exactly the state after one baseline run.
                    restore_torch_rng_state(baseline_rng_after)
                    abort_after_rejected_intervention = True

            # Last-token logits — used for both confidence + next-token pick.
            logits = outputs.logits[0, -1]  # [vocab]
            state.logits = logits.float().detach().cpu().tolist()

            if req.temperature > 0:
                probs = torch.softmax(logits / float(req.temperature), dim=-1)
                next_id = int(torch.multinomial(probs, num_samples=1).item())
            else:
                next_id = int(torch.argmax(logits).item())

            token_text = tokenizer.decode([next_id])

            summary = summarise(
                state,
                token_index=new_idx,
                attentions=list(outputs.attentions) if outputs.attentions else None,
                top_k=top_k,
                layer_filter=foundation_layers,
            )
            verification_payload = _verification_payload(req, summary.confidence)
            mode7_edges = summary.mode7_edges
            if rpm_threshold > 0:
                mode7_edges = [
                    edge for edge in mode7_edges if float(edge.get("weight", 0.0)) >= rpm_threshold
                ]

            yield {
                "token_index": new_idx,
                "token": token_text,
                "top_activated_neurons": summary.top_activated_neurons
                if "active_trace" in requested_probes
                else [],
                "mode7_attribution": mode7_edges
                if "mode7_attribution" in requested_probes
                else [],
                "confidence": summary.confidence
                if "confidence_margin" in requested_probes
                else None,
                "inversion_risk": _inversion_risk(summary, inversion_threshold)
                if inversion_active
                else None,
                "eraser_intervention_result": intervention_result,
                **verification_payload,
            }

            if abort_after_rejected_intervention:
                logger.warning(
                    "run_pythia: ending stream after rejected intervention to avoid "
                    "continuing from unverified mutable model state"
                )
                break

            # Append next token, continue.
            next_tensor = torch.tensor(
                [[next_id]], dtype=input_ids.dtype, device=device,
            )
            input_ids = torch.cat([input_ids, next_tensor], dim=1)

            # Stop if the model emitted an EOS token (Pythia tokenizer's
            # eos_token_id). Continuing past EOS produces nonsense.
            eos_id = getattr(tokenizer, "eos_token_id", None)
            if eos_id is not None and next_id == int(eos_id):
                logger.info("run_pythia: hit EOS at new_idx=%d", new_idx)
                break

            # Yield control so the event loop can flush the SSE write.
            await asyncio.sleep(0)

    # Touch prompt_len so static type checkers don't warn about unused vars
    # in case max_new == 0 (degenerate).
    _ = prompt_len


def _requested_probes(req: CreateSessionRequest) -> set[str]:
    if req.method_config and "enabled_methods" in req.method_config and not req.probes:
        return set()
    return set(resolve_probes(req.probes))


def _eraser_intervention(
    req: CreateSessionRequest,
    *,
    execution_kind: ModelExecutionKind = "typed_test_fixture",
    expected_coordinate_width: int = 3072,
    expected_projected_output_width: int = 768,
    model_binding: ModelBinding | None = None,
) -> EraserIntervention | None:
    """Build a typed activated-intermediate suppression request.

    Returns ``None`` only when the method is not enabled. An enabled method
    with no cover coordinates still returns a request so execution produces a
    typed fail-closed result rather than a silent no-op.
    """
    if "drive_local_eraser" not in _resolve_enabled_methods(req):
        return None
    if (
        execution_kind == "real_model_weights"
        and model_binding is not None
        and not model_binding.stage27f_intervention_supported
    ):
        raise RuntimeError(
            "drive_local_eraser coordinates are calibrated only for the pinned "
            f"Pythia binding; intervention refused for {model_binding.key}"
        )
    eraser_resolved = resolve_knobs(req)["drive_local_eraser"]
    drive = str(eraser_resolved["drive"])
    gain = float(eraser_resolved["gain"])
    cover_coords = coords_for_drive(drive)
    coords = tuple((coord.layer, coord.index) for coord in cover_coords)
    coordinate_space = (
        cover_coords[0].coordinate_space
        if cover_coords
        else MLP_INTERMEDIATE_POST_ACTIVATION
    )
    source_kind = (
        "typed_test_fixture"
        if execution_kind == "typed_test_fixture"
        else "stage27f_calibrated_cover"
    )
    return EraserIntervention(
        coords=coords,
        gain=gain,
        coordinate_space=coordinate_space,
        execution_kind=execution_kind,
        source_kind=source_kind,
        expected_coordinate_width=expected_coordinate_width,
        expected_projected_output_width=expected_projected_output_width,
    )


def _verification_payload(req: CreateSessionRequest, confidence: float | None) -> dict[str, Any]:
    """Return per-token verification telemetry when the stack is requested."""
    if not _verification_requested(req):
        return {}
    telemetry = build_verification_telemetry(
        req.method_config,
        confidence=confidence,
    )
    return {
        "verification_mode": telemetry.mode,
        "verification_verdict": telemetry.verdict,
        "verification_threshold": telemetry.threshold,
        "verification_score": telemetry.score,
        "verification_score_source": telemetry.score_source,
        "verification_invalid_mode": telemetry.invalid_mode,
    }


def _verification_requested(req: CreateSessionRequest) -> bool:
    """Detect both current and older UI shapes for the top-level mode."""
    if "verification_stack" in _resolve_enabled_methods(req):
        return True
    config = req.method_config if isinstance(req.method_config, dict) else {}
    if "verification_mode" in config or "mode" in config:
        return True
    knobs = config.get("knobs")
    return isinstance(knobs, dict) and "verification_stack" in knobs


def _inversion_risk(summary: Any, threshold: float) -> float:
    """Runtime inversion-risk side channel controlled by Inversion Scan."""
    activations = [
        abs(float(item.get("activation", 0.0)))
        for item in getattr(summary, "top_activated_neurons", [])
        if isinstance(item, dict)
    ]
    activation_pressure = min(max(activations, default=0.0), 1.0)
    confidence = getattr(summary, "confidence", None)
    confidence_pressure = 1.0 - float(confidence) if confidence is not None else 0.5
    risk = max(0.0, min(1.0, (activation_pressure * 0.6) + (confidence_pressure * 0.4)))
    return round(risk, 3) if risk >= threshold else 0.0
