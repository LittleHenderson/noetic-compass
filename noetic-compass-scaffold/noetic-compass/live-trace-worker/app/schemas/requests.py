"""Request bodies accepted by the worker."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AblationTargetRequest(BaseModel):
    """A single-target causal ablation/intervention request.

    When present on a ``CreateSessionRequest`` (or when ``"causal_ablation"``
    appears in ``probes``), the real-Pythia runner runs the forward pass once
    normally and once with the target MLP-output unit ablated, then emits one
    ``AblationEffectEvent`` carrying the measured logit/confidence deltas.

    ``mode``:
      * ``"zero"``    — set the target unit's last-token MLP-output to 0.
      * ``"mean"``    — patch the target unit to the running per-position mean
        of the same unit across the prompt positions (mean-ablation).

    This is the FIRST causal proof the live worker can produce. It is
    intentionally a single-target probe; matched controls are a separate,
    later slice and are NOT produced here.
    """

    layer: int = Field(..., ge=0, description="Transformer block index to hook.")
    unit: int = Field(
        ...,
        ge=0,
        description="Index into the layer's MLP-output (intermediate) dimension.",
    )
    mode: Literal["zero", "mean"] = Field(
        default="zero",
        description="Ablation style: hard-zero or mean-patch the target unit.",
    )


class CreateSessionRequest(BaseModel):
    """Body for POST /sessions on the worker.

    The API proxy translates the user's auth/license context into a server-side
    call to this endpoint. The worker is therefore stateless w.r.t. user
    identity — it only knows about sessions and prompts.
    """

    prompt: str = Field(..., min_length=1, max_length=4096)
    model_id: str = Field(default="EleutherAI/pythia-160m")
    max_new_tokens: int = Field(default=24, ge=1, le=128)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    seed: int | None = Field(
        default=None,
        description="Optional seed for reproducibility. None = nondeterministic.",
    )
    # Probe selection. UI exposes this via the methods panel; api proxies it
    # down. Empty list = run the full default probe pipeline.
    probes: list[Literal[
        "active_trace",
        "blindspot_covers",
        # Legacy alias accepted so older deployed UI builds still work.
        "blindspots_f1",
        "mode7_attribution",
        "confidence_margin",
        # Causal single-target ablation. When present, the runner also expects
        # ``ablation_target`` to be set (a bare "causal_ablation" probe with no
        # target defaults to layer 0 / unit 0). Backward-compatible: absent =>
        # no ablation runs, exactly as before.
        "causal_ablation",
    ]] = Field(default_factory=list)
    ablation_target: AblationTargetRequest | None = Field(
        default=None,
        description=(
            "Optional single-target causal ablation. When set (or when "
            "'causal_ablation' is in probes), the real runner emits one "
            "AblationEffectEvent with measured logit/confidence deltas. "
            "None => no ablation (backward-compatible default)."
        ),
    )
    method_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Live testing-module controls forwarded by Atlas Viewer.",
    )


class CreateSessionResponse(BaseModel):
    session_id: str
    events_url: str = Field(
        description="Relative SSE URL the caller subscribes to for events. The API "
        "proxy translates this into a public /api/atlas/live/session/{id}/events URL.",
    )
