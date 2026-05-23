"""Request bodies accepted by the worker."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


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
        "blindspots_f1",
        "mode7_attribution",
        "confidence_margin",
    ]] = Field(default_factory=list)
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
