"""GET /health — RunPod health-checks + the API proxy preflight.

M2: surfaces whether real weights are loaded so the API proxy can
fail-fast (HTTP 503) if a caller asks for LIVE mode but the worker is
still in demo mode after warm_load.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..runtime import get_loaded_model

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
