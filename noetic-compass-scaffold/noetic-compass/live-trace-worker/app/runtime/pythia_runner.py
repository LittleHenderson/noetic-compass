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
from typing import Any, AsyncIterator

from ..schemas.requests import CreateSessionRequest
from .cover_library import coords_for_drive
from .probe_runner import EraserIntervention, capture_probes, resolve_probes, summarise

logger = logging.getLogger(__name__)


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

    device = next(model.parameters()).device
    input_ids = tokenizer(req.prompt, return_tensors="pt").input_ids.to(device)
    prompt_len = int(input_ids.shape[1])

    # Apply seed for the (optional) sampling path.
    if req.seed is not None:
        torch.manual_seed(int(req.seed))

    max_new = min(req.max_new_tokens, 24)
    requested_probes = _requested_probes(req)
    knobs = _knobs(req)
    foundation_layers = _layer_filter(knobs.get("foundation_probe", {}).get("layer_range"))
    top_k = _positive_int(knobs.get("foundation_probe", {}).get("top_k"), default=8)
    rpm_threshold = _float_knob(
        knobs.get("rpm_gate_check", {}).get("strictness_threshold"),
        default=0.0,
    )
    intervention = _eraser_intervention(req)

    with torch.no_grad():
        for new_idx in range(max_new):
            with capture_probes(model, n_layers, intervention=intervention) as state:
                outputs = model(
                    input_ids,
                    output_hidden_states=False,
                    output_attentions=True,
                )

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
            }

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


def _knobs(req: CreateSessionRequest) -> dict[str, dict[str, Any]]:
    raw = req.method_config.get("knobs", {}) if req.method_config else {}
    return raw if isinstance(raw, dict) else {}


def _requested_probes(req: CreateSessionRequest) -> set[str]:
    if req.method_config and "enabled_methods" in req.method_config and not req.probes:
        return set()
    return set(resolve_probes(req.probes))


def _enabled_methods(req: CreateSessionRequest) -> set[str]:
    raw = req.method_config.get("enabled_methods", []) if req.method_config else []
    if not isinstance(raw, list):
        return set()
    return {str(item) for item in raw}


def _layer_filter(raw: Any) -> set[int] | None:
    if not isinstance(raw, list) or not raw:
        return None
    out: set[int] = set()
    for item in raw:
        try:
            out.add(int(item))
        except (TypeError, ValueError):
            continue
    return out or None


def _positive_int(raw: Any, default: int) -> int:
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _float_knob(raw: Any, default: float) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _eraser_intervention(req: CreateSessionRequest) -> EraserIntervention | None:
    if "drive_local_eraser" not in _enabled_methods(req):
        return None
    knobs = _knobs(req).get("drive_local_eraser", {})
    drive = str(knobs.get("drive") or "F1")
    gain = _float_knob(knobs.get("gain"), default=1.0)
    coords = tuple((coord.layer, coord.index) for coord in coords_for_drive(drive))
    if not coords:
        return None
    return EraserIntervention(coords=coords, gain=gain)
