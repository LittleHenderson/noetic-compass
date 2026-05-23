"""Model loader — stub at milestone 1.

At milestone 2 this will load Pythia-160M weights into a torch.nn.Module and
attach the probe hooks. For now it just returns a fixed manifest so the rest
of the stack has something to render.
"""

from __future__ import annotations

from ..schemas.manifest import ModelArch, ModelManifest

# Static manifest for the only model we plan to support at v0.1.
# Numbers match the offline ReplayTrace fixture so the UI sees no change
# when toggling between REPLAY and LIVE during milestone 1 demos.
PYTHIA_160M_MANIFEST = ModelManifest(
    model_id="EleutherAI/pythia-160m",
    tokenizer_id="EleutherAI/pythia-160m",
    model_arch=ModelArch(
        family="pythia",
        n_layers=12,
        hidden_size=768,
        mlp_intermediate_dim=3072,
        n_heads=12,
        total_params=162_000_000,
        validated=True,
    ),
    supported_hooks=[
        "residual_stream",
        "mlp_post_activation",
        "attention_pattern",
        "logits",
    ],
    worker_version="m1-scaffold",
    is_real_model=False,
)


def get_manifest(model_id: str) -> ModelManifest:
    """Return the manifest for a model. Raises ValueError for unknown IDs."""
    if model_id == "EleutherAI/pythia-160m":
        return PYTHIA_160M_MANIFEST
    raise ValueError(
        f"model_id={model_id!r} not supported at milestone 1. "
        "Only EleutherAI/pythia-160m is wired."
    )
