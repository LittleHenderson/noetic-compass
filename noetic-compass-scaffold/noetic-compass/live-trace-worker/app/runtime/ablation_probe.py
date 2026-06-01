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

from ..schemas.events import AblationControlEffectEvent, AblationEffectEvent
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
# Matched-control selectivity — the live worker's FIRST control proof.
#
# The single-target ablation tells us the chosen unit moves the next-token
# distribution. It does NOT tell us whether that move is *selective* — maybe
# ablating any sibling unit moves it just as much. This runner answers that by
# ablating the target AND a set of random same-layer control units, scoring
# each by the same metric (change in the baseline-top token's logit), and
# reporting whether the target beat every control. This is the single-unit
# forward-pass analog of the offline Stage-9 'beat random same-rank controls'
# guard; it is NOT the 40-Element subspace control (a separate, later proof).
# ---------------------------------------------------------------------------


def _capture_target_mlp_width(
    model: Any,
    n_layers: int,
    target: AblationTargetRequest,
    input_ids: Any,
) -> tuple[Any, int | None]:
    """Run one baseline forward, capturing the target MLP's output width.

    Returns ``(baseline_last_token_logits, width)``. ``width`` is ``None`` when
    the target layer / MLP is out of range, which signals the caller that no
    real control could be sampled (so no control proof is claimed).
    """
    layers = _get_pythia_layers(model)
    captured: dict[str, int] = {}
    handle: Any = None
    if layers is not None and 0 <= target.layer < min(n_layers, len(layers)):
        mlp = getattr(layers[target.layer], "mlp", None)
        if mlp is not None:

            def _capture(_module: Any, _inputs: Any, output: Any) -> Any:
                try:
                    if output is not None:
                        captured["width"] = int(output.shape[-1])
                except Exception:  # pragma: no cover — defensive
                    logger.exception("ablation control: width capture failed")
                return output

            handle = mlp.register_forward_hook(_capture)
    try:
        logits = _last_token_logits(model, input_ids)
    finally:
        if handle is not None:
            try:
                handle.remove()
            except Exception:  # pragma: no cover — defensive cleanup
                logger.exception("ablation control: width hook removal failed")
    return logits, captured.get("width")


def run_real_ablation_control(
    req: CreateSessionRequest,
    model: Any,
    tokenizer: Any,
    n_layers: int,
    target: AblationTargetRequest,
    n_controls: int = 8,
    seed: int = 42,
) -> AblationControlEffectEvent:
    """Measure single-unit ablation selectivity vs random same-layer controls.

    Ablates the target unit and up to ``n_controls`` random OTHER units in the
    SAME layer (same mode), each scored by the change in the baseline-top
    token's logit. Reports whether the target moved that token strictly more
    than every control. The model is NOT mutated: each hook is attached only
    for its own ablated forward pass and removed afterwards.

    Honesty: ``is_real_model`` is True ONLY when at least one control unit was
    actually ablated on real weights. If the target layer is out of range or no
    sibling unit can be sampled, this returns an ``is_real_model = False`` event
    with no numeric deltas — the matched control did not run, so no control
    proof is claimed.
    """
    import numpy as np
    import torch

    device = next(model.parameters()).device
    input_ids = tokenizer(req.prompt, return_tensors="pt").input_ids.to(device)

    with torch.no_grad():
        baseline_logits, width = _capture_target_mlp_width(
            model, n_layers, target, input_ids
        )
        baseline_vec = baseline_logits.float().detach().cpu()
        baseline_id = int(torch.argmax(baseline_logits).item())
        baseline_top_logit = float(baseline_vec[baseline_id].item())

        if width is None or width <= 1:
            return demo_ablation_control(
                target,
                detail=(
                    "No matched control ran: target layer "
                    f"{target.layer} unit {target.unit} is out of range or its "
                    "layer has no spare units to sample as controls, so no real "
                    "control proof is claimed."
                ),
            )

        # Real target effect (identical metric to run_real_ablation_effect).
        with _ablate_mlp_unit(model, n_layers, target):
            target_logits = _last_token_logits(model, input_ids)
        target_logit = float(target_logits.float().detach().cpu()[baseline_id].item())
        target_abs = abs(target_logit - baseline_top_logit)

        # Sample random control units in the same layer, excluding the target.
        rng = np.random.default_rng(seed)
        candidates = [u for u in range(int(width)) if u != int(target.unit)]
        k = min(int(n_controls), len(candidates))
        control_units = sorted(
            int(u) for u in rng.choice(candidates, size=k, replace=False)
        )

        control_abs_deltas: list[float] = []
        for unit in control_units:
            control_target = AblationTargetRequest(
                layer=int(target.layer), unit=int(unit), mode=target.mode
            )
            with _ablate_mlp_unit(model, n_layers, control_target):
                control_logits = _last_token_logits(model, input_ids)
            control_logit = float(
                control_logits.float().detach().cpu()[baseline_id].item()
            )
            control_abs_deltas.append(abs(control_logit - baseline_top_logit))

    control_mean_abs = float(sum(control_abs_deltas) / len(control_abs_deltas))
    control_max_abs = float(max(control_abs_deltas))
    margin = float(target_abs - control_max_abs)
    selectivity_passed = bool(target_abs > control_max_abs)

    return AblationControlEffectEvent(
        target={"layer": int(target.layer), "unit": int(target.unit)},
        mode=target.mode,
        is_real_model=True,
        n_controls=len(control_units),
        control_units=control_units,
        target_abs_logit_delta=round(target_abs, 4),
        control_mean_abs_logit_delta=round(control_mean_abs, 4),
        control_max_abs_logit_delta=round(control_max_abs, 4),
        margin_over_control_max=round(margin, 4),
        selectivity_passed=selectivity_passed,
        seed=int(seed),
        detail=(
            f"Single-unit selectivity control ({target.mode}) for layer "
            f"{target.layer} unit {target.unit}: target |logit delta| "
            f"{target_abs:.4f} vs {len(control_units)} random same-layer "
            f"controls (max {control_max_abs:.4f}). Single-unit next-token "
            "control, NOT the 40-Element subspace control."
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


def demo_ablation_control(
    target: AblationTargetRequest,
    detail: str | None = None,
) -> AblationControlEffectEvent:
    """Schema-valid matched-control event for demo mode — no real measurement.

    Mirrors ``demo_ablation_effect``: every numeric field is ``None`` and
    ``is_real_model`` is ``False``. Demo mode (or a real run where no sibling
    control unit could be sampled) must never present synthetic numbers as a
    real matched control; it reports honestly that no control ran.
    """
    return AblationControlEffectEvent(
        target={"layer": int(target.layer), "unit": int(target.unit)},
        mode=target.mode,
        is_real_model=False,
        n_controls=0,
        control_units=None,
        target_abs_logit_delta=None,
        control_mean_abs_logit_delta=None,
        control_max_abs_logit_delta=None,
        margin_over_control_max=None,
        selectivity_passed=None,
        seed=None,
        detail=detail
        or (
            "Demo mode: no real weights loaded, so no matched-control ablation "
            "was measured. This event is a schema-valid placeholder — it carries "
            "no measured deltas and must not be read as a real control proof."
        ),
    )
