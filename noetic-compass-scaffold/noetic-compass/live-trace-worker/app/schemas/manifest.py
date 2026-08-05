"""Model manifest — what the worker reports about the model it's hosting.

This is the contract the API + UI use to know what hooks / layers / heads are
available for a session. Mirrors the structure the atlas-viewer ReplayTrace
fixture uses for its model_arch field so the UI doesn't need a separate
adapter when switching between REPLAY and LIVE.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


SupportedHook = Literal[
    "residual_stream",
    "mlp_pre_activation",
    "mlp_post_activation",
    "mlp_intermediate_post_activation",
    "attention_pattern",
    "attention_head_output",
    "logits",
]

ModelExecutionKind = Literal[
    "demo_schema_only",
    "real_model_weights",
    "typed_test_fixture",
]


class InterventionHookContract(BaseModel):
    """Exact tensor semantics for Stage-27F coordinate interventions."""

    contract_version: Literal["harness_v2.mlp_intermediate_eraser.v2"] = (
        "harness_v2.mlp_intermediate_eraser.v2"
    )
    coordinate_space: Literal["mlp_intermediate_post_activation"] = (
        "mlp_intermediate_post_activation"
    )
    module_path_template: Literal[
        "gpt_neox.layers[{layer}].mlp.dense_4h_to_h"
    ] = "gpt_neox.layers[{layer}].mlp.dense_4h_to_h"
    tensor_role: Literal["forward_pre_hook.input[0]"] = "forward_pre_hook.input[0]"
    token_selection: Literal["batch_0_last_sequence_position"] = (
        "batch_0_last_sequence_position"
    )
    expected_width_source: Literal["model_arch.mlp_intermediate_dim"] = (
        "model_arch.mlp_intermediate_dim"
    )
    failure_policy: Literal["fail_closed"] = "fail_closed"

ModelIdentityStatus = Literal[
    "DEMO_OR_UNLOADED",
    "PINNED_REVISION_ONLY",
    "PINNED_REVISION_AND_WEIGHTS_SHA256",
]


class RuntimeExecutionEvidence(BaseModel):
    """Observed execution substrate for a real-model manifest."""

    profile: Literal["development", "production"]
    device: Literal["cpu", "cuda"]
    dtype: Literal["torch.float32", "torch.float16"]
    torch_version: str = Field(..., min_length=1)
    cuda_runtime_version: str | None = None
    cuda_driver_version: int | None = Field(default=None, ge=1)
    cuda_device_name: str | None = Field(default=None, min_length=1)
    cuda_device_capability: str | None = Field(default=None, min_length=3)

    @model_validator(mode="after")
    def _production_requires_observed_cuda(self) -> "RuntimeExecutionEvidence":
        if self.profile == "production":
            if self.device != "cuda" or self.dtype != "torch.float16":
                raise ValueError("production runtime evidence requires CUDA float16 execution")
            if not (
                self.cuda_runtime_version
                and self.cuda_driver_version
                and self.cuda_device_name
                and self.cuda_device_capability
            ):
                raise ValueError(
                    "production runtime evidence requires CUDA runtime, driver, device, "
                    "and capability observations"
                )
            if self.torch_version != "2.13.0+cu126":
                raise ValueError("production runtime evidence requires Torch 2.13.0+cu126")
            if self.cuda_runtime_version != "12.6":
                raise ValueError("production runtime evidence requires CUDA runtime 12.6")
            if self.cuda_driver_version < 12060:
                raise ValueError("production runtime evidence requires CUDA driver API 12.6+")
        return self


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
        default_factory=lambda: [
            "residual_stream",
            "mlp_intermediate_post_activation",
            "attention_pattern",
            "logits",
        ],
    )
    execution_kind: ModelExecutionKind = Field(
        default="demo_schema_only",
        description=(
            "Typed runtime provenance. Demo/test fixtures remain distinguishable "
            "from execution on loaded model weights."
        ),
    )
    intervention_hook_contract: InterventionHookContract = Field(
        default_factory=InterventionHookContract,
    )
    worker_version: str = Field(default="m1-scaffold", description="Worker code version tag.")
    requested_revision: str | None = Field(
        default=None,
        description="Exact model-repository commit requested from the loader.",
    )
    resolved_revision: str | None = Field(
        default=None,
        description="Commit reported by the loaded model configuration after resolution.",
    )
    revision_verified: bool = Field(
        default=False,
        description="True only when resolved_revision exactly equals requested_revision.",
    )
    weights_filename: str | None = Field(
        default=None,
        description="Exact single-file model-weights artifact verified by the loader.",
    )
    weights_sha256: str | None = Field(
        default=None,
        description="Worker-recomputed lowercase SHA-256 of weights_filename.",
    )
    weights_bytes: int | None = Field(
        default=None,
        strict=True,
        ge=1,
        description="Worker-counted byte length of weights_filename.",
    )
    weights_hash_verified: bool = Field(
        default=False,
        description=(
            "True only when the locally cached weights file matches the pinned "
            "filename, byte length, and SHA-256 constants."
        ),
    )
    model_identity_status: ModelIdentityStatus = Field(
        default="DEMO_OR_UNLOADED",
        description=(
            "Typed identity strength. PINNED_REVISION_ONLY does not establish "
            "weights-file identity; real execution requires the stronger status."
        ),
    )
    runtime_execution: RuntimeExecutionEvidence | None = Field(
        default=None,
        description=(
            "Observed device, dtype, Torch, and CUDA substrate for this loaded model."
        ),
    )
    is_real_model: bool = Field(
        default=False,
        description=(
            "False until milestone 2 swaps the fake event_stream for the real Pythia "
            "runner. UI surfaces this in the LIVE-mode badge so demos don't accidentally "
            "claim live-model status while still streaming fakes."
        ),
    )

    @model_validator(mode="after")
    def _real_model_requires_revision_attestation(self) -> "ModelManifest":
        requested = self.requested_revision
        resolved = self.resolved_revision
        exact_match = (
            isinstance(requested, str)
            and len(requested) == 40
            and all(char in "0123456789abcdef" for char in requested)
            and resolved == requested
        )
        if self.revision_verified and not exact_match:
            raise ValueError(
                "revision_verified requires equal full lowercase requested/resolved commits"
            )
        if self.model_identity_status == "PINNED_REVISION_ONLY" and not self.revision_verified:
            raise ValueError("PINNED_REVISION_ONLY requires revision_verified")
        weights_digest_is_exact = (
            isinstance(self.weights_sha256, str)
            and len(self.weights_sha256) == 64
            and all(char in "0123456789abcdef" for char in self.weights_sha256)
        )
        weights_metadata_is_complete = (
            isinstance(self.weights_filename, str)
            and bool(self.weights_filename)
            and weights_digest_is_exact
            and type(self.weights_bytes) is int
            and self.weights_bytes > 0
        )
        if self.weights_hash_verified and not weights_metadata_is_complete:
            raise ValueError(
                "weights_hash_verified requires filename, positive byte count, and "
                "a full lowercase SHA-256"
            )
        full_identity = self.model_identity_status == (
            "PINNED_REVISION_AND_WEIGHTS_SHA256"
        )
        if full_identity and not (
            self.revision_verified and self.weights_hash_verified
        ):
            raise ValueError(
                "PINNED_REVISION_AND_WEIGHTS_SHA256 requires revision and weights verification"
            )
        if self.weights_hash_verified and not full_identity:
            raise ValueError(
                "verified weights require PINNED_REVISION_AND_WEIGHTS_SHA256 status"
            )
        if self.is_real_model and not (
            self.revision_verified
            and self.weights_hash_verified
            and full_identity
            and self.runtime_execution is not None
        ):
            raise ValueError(
                "is_real_model requires an observed pinned revision, verified weights "
                "SHA-256, and runtime execution evidence"
            )
        if self.is_real_model and self.execution_kind != "real_model_weights":
            raise ValueError(
                "is_real_model requires real_model_weights execution provenance"
            )
        if self.execution_kind == "real_model_weights" and not self.is_real_model:
            raise ValueError("real_model_weights requires is_real_model")
        return self
