"""Model manifest — what the worker reports about the model it's hosting.

This is the contract the API + UI use to know what hooks / layers / heads are
available for a session. Mirrors the structure the atlas-viewer ReplayTrace
fixture uses for its model_arch field so the UI doesn't need a separate
adapter when switching between REPLAY and LIVE.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SupportedHook = Literal[
    "residual_stream",
    "mlp_pre_activation",
    "mlp_post_activation",
    "attention_pattern",
    "attention_head_output",
    "logits",
]


class ModelArch(BaseModel):
    """Bare architecture facts. Used by the UI to lay out the 3D scene."""

    family: str = Field(..., description="Model family, e.g. 'pythia'.")
    n_layers: int = Field(..., ge=1)
    hidden_size: int = Field(..., ge=1)
    mlp_intermediate_dim: int = Field(..., ge=1)
    n_heads: int = Field(..., ge=1)
    total_params: int = Field(..., ge=1)
    validated: bool = Field(default=True)


class ModelManifest(BaseModel):
    """Full per-session manifest emitted before the first trace event.

    Surfaced in the cockpit's provenance badge + the help overlay's data
    provenance section so the user can see *which* model is running and
    *which* probes are available for the current session.
    """

    model_id: str = Field(..., description="HF model id, e.g. 'EleutherAI/pythia-160m'.")
    model_arch: ModelArch
    tokenizer_id: str = Field(..., description="Tokenizer model id (often equal to model_id).")
    supported_hooks: list[SupportedHook] = Field(
        default_factory=lambda: ["residual_stream", "mlp_post_activation", "attention_pattern", "logits"],
    )
    worker_version: str = Field(default="m1-scaffold", description="Worker code version tag.")
    is_real_model: bool = Field(
        default=False,
        description=(
            "False until milestone 2 swaps the fake event_stream for the real Pythia "
            "runner. UI surfaces this in the LIVE-mode badge so demos don't accidentally "
            "claim live-model status while still streaming fakes."
        ),
    )
