"""GET /health — RunPod health-checks + the API proxy preflight.

M2: surfaces whether real weights are loaded so the API proxy can
fail-fast (HTTP 503) if a caller asks for LIVE mode but the worker is
still in demo mode after warm_load.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..runtime import get_loaded_model
from ..runtime import model_loader

router = APIRouter()

REALMODE_PASS = "REAL_PYTHIA_WEIGHTS_LOADED"
REALMODE_FAIL = "NOT_REAL_PYTHIA_WEIGHTS"


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
    """Cheap proof surface for whether real Pythia weights are live now.

    This intentionally does not call get_loaded_model() or warm_load().
    A cold worker must report NOT_REAL_PYTHIA_WEIGHTS until startup has
    actually loaded the model singleton.
    """
    fake_runtime_env = model_loader._is_demo_mode_forced()
    loaded = model_loader._LOADED
    manifest = loaded.manifest if loaded is not None else model_loader.PYTHIA_160M_MANIFEST
    manifest_is_real_model = bool(manifest.is_real_model)
    model_loaded = bool(
        loaded is not None
        and loaded.model is not None
        and loaded.tokenizer is not None
    )
    load_error = loaded.load_error if loaded is not None else None

    is_real_model = (
        not fake_runtime_env
        and model_loaded
        and load_error is None
        and manifest_is_real_model
    )
    verdict = REALMODE_PASS if is_real_model else REALMODE_FAIL

    return {
        "verdict": verdict,
        "is_real_model": is_real_model,
        "fake_runtime_env": fake_runtime_env,
        "model_loaded": model_loaded,
        "load_error": load_error,
        "manifest_is_real_model": manifest_is_real_model,
        "model_id": model_loader.PYTHIA_160M_MODEL_ID,
        "worker_version": manifest.worker_version,
    }
