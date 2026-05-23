"""Model loader — loads real Pythia-160M weights when torch + transformers are
available, falls back to demo mode otherwise.

M2 change vs M1: instead of returning a static manifest, this module also
owns the live torch.nn.Module + tokenizer. The FastAPI app's startup hook
calls ``warm_load`` once at boot, then ``get_loaded_model()`` returns the
warm singleton for every subsequent request.

The two modes:

* **real** — torch + transformers import successfully, EleutherAI/pythia-160m
  weights load into memory. ``manifest.is_real_model = True``.
  pythia_runner.run_pythia drives generation through these weights.

* **demo** — either torch is missing (CI / local dev), or
  ``LIVE_TRACE_DEMO_MODE=1`` is set, or the explicit load failed.
  ``manifest.is_real_model = False``. event_stream falls back to the
  schema-valid fake stream from M1.

User-visible contract: the cockpit's "Live · actual weights" badge MUST
only show when ``manifest.is_real_model = True``.
"""

from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from typing import Any

from ..schemas.manifest import ModelArch, ModelManifest

logger = logging.getLogger(__name__)


# --- public manifest constants ------------------------------------------

# Architecture is fixed for Pythia-160M and matches the offline trace
# fixture. UI uses these numbers to lay out the 3D scene before any tokens
# have streamed.
_PYTHIA_ARCH = ModelArch(
    family="pythia",
    n_layers=12,
    hidden_size=768,
    mlp_intermediate_dim=3072,
    n_heads=12,
    total_params=162_000_000,
    validated=True,
)

PYTHIA_160M_MODEL_ID = "EleutherAI/pythia-160m"

# Initial demo-mode manifest. real_load() returns a copy with
# is_real_model = True. Treat this as the worker's bootstrap default — it
# is what /manifest returns before warm_load runs (or if warm_load fails).
PYTHIA_160M_MANIFEST = ModelManifest(
    model_id=PYTHIA_160M_MODEL_ID,
    tokenizer_id=PYTHIA_160M_MODEL_ID,
    model_arch=_PYTHIA_ARCH,
    supported_hooks=[
        "residual_stream",
        "mlp_post_activation",
        "attention_pattern",
        "logits",
    ],
    worker_version="m2-real-pythia",
    is_real_model=False,
)


# --- loaded-model state -------------------------------------------------


@dataclass
class LoadedModel:
    """Singleton holding the warm torch model + tokenizer + manifest.

    ``model`` and ``tokenizer`` are typed Any so the import of torch /
    transformers stays optional. Code that depends on them must guard via
    ``loaded.is_real``.
    """

    manifest: ModelManifest
    model: Any = None  # torch.nn.Module when is_real, else None
    tokenizer: Any = None  # PreTrainedTokenizer when is_real, else None
    load_error: str | None = None
    """Set to the str() of the exception if a load was attempted and failed."""

    @property
    def is_real(self) -> bool:
        return self.manifest.is_real_model and self.model is not None


_LOADED: LoadedModel | None = None
_LOAD_LOCK = threading.Lock()


def _is_demo_mode_forced() -> bool:
    """env LIVE_TRACE_DEMO_MODE=1 forces the demo stream even if torch is fine.

    Used for local dev where you don't want the worker to download Pythia
    weights, and for cheap integration tests on CI runners.
    """
    return os.environ.get("LIVE_TRACE_DEMO_MODE", "0").strip().lower() in {"1", "true", "yes"}


def warm_load() -> LoadedModel:
    """Load Pythia-160M into memory once. Idempotent + thread-safe.

    Called from the FastAPI startup hook. Subsequent calls return the
    cached LoadedModel. If torch / transformers are not importable, OR
    LIVE_TRACE_DEMO_MODE is set, OR the load raises, we return a demo
    LoadedModel with is_real_model = False and a populated load_error.
    """
    global _LOADED
    with _LOAD_LOCK:
        if _LOADED is not None:
            return _LOADED

        if _is_demo_mode_forced():
            logger.info("warm_load: LIVE_TRACE_DEMO_MODE=1 — staying in demo mode")
            _LOADED = LoadedModel(manifest=PYTHIA_160M_MANIFEST)
            return _LOADED

        try:
            # Heavy imports kept inside the try so the module is importable
            # without torch (CI, local dev) — the worker still starts and
            # just stays in demo mode.
            import torch  # noqa: F401
            from transformers import AutoModelForCausalLM, AutoTokenizer

            logger.info("warm_load: loading %s", PYTHIA_160M_MODEL_ID)
            tokenizer = AutoTokenizer.from_pretrained(PYTHIA_160M_MODEL_ID)
            model = AutoModelForCausalLM.from_pretrained(
                PYTHIA_160M_MODEL_ID,
                output_hidden_states=True,
                output_attentions=True,
            )
            model.eval()
            # If a CUDA device is visible, move there. CPU fallback is fine
            # for the M2 acceptance smoke; production lives on RunPod GPU.
            try:
                if torch.cuda.is_available():
                    model = model.to("cuda")
                    logger.info("warm_load: model moved to cuda")
                else:
                    logger.info("warm_load: cuda not available — staying on cpu")
            except Exception as cuda_exc:  # pragma: no cover — environment-dependent
                logger.warning("warm_load: cuda move failed (%s) — staying on cpu", cuda_exc)

            real_manifest = PYTHIA_160M_MANIFEST.model_copy(
                update={"is_real_model": True},
            )
            _LOADED = LoadedModel(
                manifest=real_manifest,
                model=model,
                tokenizer=tokenizer,
            )
            logger.info("warm_load: model loaded, is_real_model=True")
        except Exception as exc:  # broad — log full reason, stay demo
            logger.exception("warm_load: failed; falling back to demo mode")
            _LOADED = LoadedModel(
                manifest=PYTHIA_160M_MANIFEST,
                load_error=str(exc),
            )
        return _LOADED


def get_loaded_model() -> LoadedModel:
    """Return the warm singleton. Triggers warm_load() if it hasn't run yet.

    Routes call this to learn whether they should drive the real runner or
    the fake stream.
    """
    if _LOADED is None:
        return warm_load()
    return _LOADED


def reset_for_test() -> None:
    """Test-only: clear the cache so a fresh warm_load can run.

    Production code MUST NOT call this — it's only here so pytest can
    inject a mocked torch.
    """
    global _LOADED
    with _LOAD_LOCK:
        _LOADED = None


def get_manifest(model_id: str) -> ModelManifest:
    """Return the manifest for a model. Raises ValueError for unknown IDs.

    M2: prefers the LIVE manifest (with is_real_model from warm_load)
    over the static demo manifest if a load has happened.
    """
    if model_id != PYTHIA_160M_MODEL_ID:
        raise ValueError(
            f"model_id={model_id!r} not supported at v0.1. "
            f"Only {PYTHIA_160M_MODEL_ID} is wired."
        )
    loaded = get_loaded_model()
    return loaded.manifest
