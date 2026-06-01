"""Single-target causal ablation probe — the live worker's FIRST causal proof.

The live trace + neuron-cover pipeline is *observational*: it reports which
units activate, but activation is not causation. This module adds the first
*interventional* signal: it runs the model's forward pass once normally and
once with a single target MLP-output unit ablated (hard-zeroed or mean-patched
via a forward hook), then reports the measured change in the next-token
distribution.

Honesty contract (this product's entire value is honest, traceable audits):

* ``run_real_ablation_effect`` only runs on actually loaded weights and returns
  an ``AblationEffectEvent`` with ``is_real_model = True`` and REAL measured
  deltas.
* ``demo_ablation_effect`` returns a schema-valid event with
  ``is_real_model = False`` and ALL numeric deltas set to ``None`` — a demo
  event reports "no causal measurement was taken", it never fabricates a
  number and dresses it up as real.

The runner (``api/services/cas_harness_live_worker_runner.py``) flips its
``causal_proof`` chip to ``present`` ONLY when it sees an ``ablation_effect``
event with ``is_real_model = True``. Matched controls remain a separate, later
slice and are NOT produced here.

Reuses the same Pythia layer-location + last-token MLP-output convention as
``probe_runner.capture_probes`` (hook on ``model.gpt_neox.layers[i].mlp``,
operate on the final-prompt-token position, batch = 1).
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Iterator

from ..schemas.events import AblationEffectEvent
from ..schemas.requests import AblationTargetRequest, CreateSessionRequest
from .probe_runner import _get_pythia_layers, _softmax_margin

logger = logging.getLogger(__name__)


def ablation_requested(req: CreateSessionRequest) -> bool:
    """True when this session asked for a causal ablation probe.

    Triggered by either an explicit ``ablation_target`` or a
    ``"causal_ablation"`` entry in ``probes``. Backward-compatible: a request
    with neither runs exactly as before (no ablation event emitted).
    """
    if req.ablation_target is not None:
        return True
    return "causal_ablation" in (req.probes or [])


def resolve_ablation_target(req: CreateSessionRequest) -> AblationTargetRequest:
    """Resolve the target unit for this session.

    Explicit ``ablation_target`` wins. A bare ``"causal_ablation"`` probe with
    no target defaults to layer 0 / unit 0 so the path is exercisable without
    the caller having to pick a unit, while still being a real, single-target
    ablation.
    """
    if req.ablation_target is not None:
        return req.ablation_target
    return AblationTargetRequest(layer=0, unit=0, mode="zero")


# ---------------------------------------------------------------------------
# Real ablation — measured on loaded weights.
# ---------------------------------------------------------------------------


@contextmanager
def _ablate_mlp_unit(
    model: Any,
    n_layers: int,
    target: AblationTargetRequest,
) -> Iterator[None]:
    """Hook the target layer's MLP and ablate one last-token output unit.

    ``mode == "zero"`` sets the unit to 0 at the final-prompt-token position.
    ``mode == "mean"`` replaces it with the mean of the same unit across all
    prompt positions (a mean-patch). Other positions are left untouched — only
    the predicting position's logits matter for the next-token effect.

    Always removes the hook on exit, even on exception, so no intervention
    leaks into a later forward pass.
    """
    layers = _get_pythia_layers(model)
    handles: list[Any] = []
    if layers is None or not (0 <= target.layer < min(n_layers, len(layers))):
        logger.warning(
            "ablation: target layer %d out of range (n_layers=%d) — no-op hook",
            target.layer,
            n_layers,
        )
        yield
        return

    mlp = getattr(layers[target.layer], "mlp", None)
    if mlp is None:
        logger.warning("ablation: layer %d has no .mlp — no-op hook", target.layer)
        yield
        return

    def _hook(_module: Any, _inputs: Any, output: Any) -> Any:
        try:
            if output is None:
                return None
            width = int(output.shape[-1])
            unit = int(target.unit)
            if not (0 <= unit < width):
                return output
            modified = output.clone()
            if target.mode == "mean":
                # Mean of the unit across all positions in this (batch=1) pass.
                patch = modified[0, :, unit].mean()
                modified[0, -1, unit] = patch
            else:
                modified[0, -1, unit] = modified[0, -1, unit] * 0.0
            return modified
        except Exception:  # pragma: no cover — defensive; keep forward alive
            logger.exception("ablation hook failed at layer %d", target.layer)
            return output

    handles.append(mlp.register_forward_hook(_hook))
    try:
        yield
    finally:
        for handle in handles:
            try:
                handle.remove()
            except Exception:  # pragma: no cover — defensive cleanup
                logger.exception("ablation: hook removal failed")


def _last_token_logits(model: Any, input_ids: Any) -> Any:
    outputs = model(input_ids, output_hidden_states=False, output_attentions=False)
    return outputs.logits[0, -1]


def run_real_ablation_effect(
    req: CreateSessionRequest,
    model: Any,
    tokenizer: Any,
    n_layers: int,
    target: AblationTargetRequest,
) -> AblationEffectEvent:
    """Measure a single-target ablation effect on loaded weights.

    Runs the prompt forward once normally and once with the target unit
    ablated, then reports the measured deltas. The model is NOT mutated: the
    hook is attached only for the ablated pass and removed afterwards.
    """
    import torch

    device = next(model.parameters()).device
    input_ids = tokenizer(req.prompt, return_tensors="pt").input_ids.to(device)

    with torch.no_grad():
        baseline_logits = _last_token_logits(model, input_ids)
        baseline_vec = baseline_logits.float().detach().cpu().tolist()
        baseline_id = int(torch.argmax(baseline_logits).item())

        with _ablate_mlp_unit(model, n_layers, target):
            ablated_logits = _last_token_logits(model, input_ids)
        ablated_vec = ablated_logits.float().detach().cpu().tolist()
        ablated_id = int(torch.argmax(ablated_logits).item())

    baseline_conf = _softmax_margin(baseline_vec)
    ablated_conf = _softmax_margin(ablated_vec)
    # logit_delta tracks the baseline-top token's own logit: how much did
    # ablating the unit move the token the model would otherwise have picked?
    logit_delta = float(ablated_vec[baseline_id] - baseline_vec[baseline_id])
    confidence_delta: float | None = None
    if baseline_conf is not None and ablated_conf is not None:
        confidence_delta = round(float(ablated_conf - baseline_conf), 4)

    return AblationEffectEvent(
        target={"layer": int(target.layer), "unit": int(target.unit)},
        mode=target.mode,
        is_real_model=True,
        baseline_top_token=tokenizer.decode([baseline_id]),
        ablated_top_token=tokenizer.decode([ablated_id]),
        baseline_top_token_id=baseline_id,
        ablated_top_token_id=ablated_id,
        logit_delta=round(logit_delta, 4),
        confidence_delta=confidence_delta,
        top_token_changed=bool(baseline_id != ablated_id),
        detail=(
            f"Measured single-target ablation ({target.mode}) of "
            f"layer {target.layer} unit {target.unit} on loaded weights."
        ),
    )


# ---------------------------------------------------------------------------
# Demo ablation — schema-valid, explicitly NOT a real measurement.
# ---------------------------------------------------------------------------


def demo_ablation_effect(target: AblationTargetRequest) -> AblationEffectEvent:
    """Schema-valid ablation event for demo mode — no real measurement.

    Deliberately leaves every numeric delta ``None`` and flags
    ``is_real_model = False``. Demo mode must never present synthetic numbers
    as a real causal measurement; it reports honestly that no real ablation
    ran because weights are not loaded.
    """
    return AblationEffectEvent(
        target={"layer": int(target.layer), "unit": int(target.unit)},
        mode=target.mode,
        is_real_model=False,
        baseline_top_token=None,
        ablated_top_token=None,
        baseline_top_token_id=None,
        ablated_top_token_id=None,
        logit_delta=None,
        confidence_delta=None,
        top_token_changed=None,
        detail=(
            "Demo mode: no real weights loaded, so no causal ablation was "
            "measured. This event is a schema-valid placeholder — it carries "
            "no measured deltas and must not be read as a real causal proof."
        ),
    )
