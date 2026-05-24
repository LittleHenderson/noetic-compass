"""GET /health — RunPod health-checks + the API proxy preflight.

M2: surfaces whether real weights are loaded so the API proxy can
fail-fast (HTTP 503) if a caller asks for LIVE mode but the worker is
still in demo mode after warm_load.

``/health/realmode`` is a *cheap* probe used by the operator-facing
verification script (``scripts/verify_atlas_live.py``). It deliberately
does NOT trigger a model load — it only reports whether warm_load has
already populated the singleton with real weights, and whether the
``LIVE_TRACE_DEMO_MODE`` env var is forcing demo mode. The point is to
answer the "is this RunPod actually in real-model mode?" question without
paying any load cost.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..runtime import get_loaded_model
from ..runtime import model_loader

router = APIRouter()


@router.get("/health")
def health() -> dict:
    loaded = get_loaded_model()
    return {
        "status": "ok",
        "worker_version": loaded.manifest.worker_version,
        "model_id": loaded.manifest.model_id,
        "is_real_model": loaded.manifest.is_real_model,
        "model_loaded": loaded.is_real,
        "load_error": loaded.load_error,
    }


@router.get("/health/realmode")
def health_realmode() -> dict:
    """Cheap real-mode probe — does NOT trigger a model load.

    ``is_real_model`` reflects whether the worker is configured to run on
    real Pythia-160M weights. It is ``False`` exactly when the
    ``LIVE_TRACE_DEMO_MODE`` env var is set (the worker's fake-runtime
    switch).

    ``fake_runtime_env`` mirrors the env-var state so operators can tell
    whether ``is_real_model=False`` is caused by the env-var override (vs
    a load failure surfaced via ``/health``).

    ``model_loaded`` is ``True`` only when warm_load has already run AND
    populated the singleton with real weights. It is intentionally a
    *probe*: this endpoint never calls ``warm_load`` or
    ``get_loaded_model`` because either would trigger a model load on a
    cold worker, which defeats the "cheap check" purpose.
    """
    fake_runtime = model_loader._is_demo_mode_forced()
    is_real_model = not fake_runtime
    # Probe the singleton without forcing a load. _LOADED is None on cold
    # workers — that's the answer; do NOT call warm_load() here.
    loaded = model_loader._LOADED
    model_loaded = bool(loaded is not None and loaded.is_real)
    worker_version = (
        loaded.manifest.worker_version
        if loaded is not None
        else model_loader.PYTHIA_160M_MANIFEST.worker_version
    )
    return {
        "is_real_model": is_real_model,
        "fake_runtime_env": fake_runtime,
        "model_id": model_loader.PYTHIA_160M_MODEL_ID,
        "model_loaded": model_loaded,
        "worker_version": worker_version,
    }
