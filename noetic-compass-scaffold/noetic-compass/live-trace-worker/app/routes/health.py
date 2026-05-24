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

    ``is_real_model`` is the load-bearing assertion: real Pythia-160M
    weights are loaded *right now*. It requires three conditions
    simultaneously, all probed cheaply:

      1. ``fake_runtime_env`` is False (LIVE_TRACE_DEMO_MODE not forced).
      2. ``model_loaded`` is True (warm_load has populated the singleton
         with real weights — not None, not a sentinel).
      3. ``load_error`` is null (no prior load failure recorded).

    A cold worker (env unset, no warm_load yet) reports ``is_real_model:
    False`` because the model is not actually loaded. The point of this
    endpoint is to answer the operator question "is this RunPod serving
    real weights right now?" — merely "not forced to demo" is not enough.

    ``fake_runtime_env`` mirrors the env-var state separately so operators
    can distinguish a forced-demo failure mode from a cold-worker or
    load-error failure mode.

    This endpoint never calls ``warm_load`` or ``get_loaded_model``
    because either would trigger a model load on a cold worker, which
    defeats the "cheap check" purpose.
    """
    fake_runtime = model_loader._is_demo_mode_forced()
    # Probe the singleton without forcing a load. _LOADED is None on cold
    # workers — that's the answer; do NOT call warm_load() here.
    loaded = model_loader._LOADED
    model_loaded = bool(loaded is not None and loaded.is_real)
    load_error = loaded.load_error if loaded is not None else None
    # Real-mode requires ALL three: demo env not forced, weights actually
    # loaded, no prior load error.
    is_real_model = (not fake_runtime) and model_loaded and load_error is None
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
        "load_error": load_error,
        "worker_version": worker_version,
    }
