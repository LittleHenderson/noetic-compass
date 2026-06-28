"""GET /health — used by RunPod health checks + the API proxy preflight."""

from __future__ import annotations

from fastapi import APIRouter

from ..runtime import PYTHIA_160M_MANIFEST

router = APIRouter()

REALMODE_PASS = "REAL_PYTHIA_WEIGHTS_LOADED"
REALMODE_FAIL = "NOT_REAL_PYTHIA_WEIGHTS"


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "worker_version": PYTHIA_160M_MANIFEST.worker_version,
        "model_id": PYTHIA_160M_MANIFEST.model_id,
        "is_real_model": PYTHIA_160M_MANIFEST.is_real_model,
    }


@router.get("/health/realmode")
def health_realmode() -> dict:
    """Truthful real-weight readiness surface for API/RunPod smoke checks."""
    is_real_model = bool(PYTHIA_160M_MANIFEST.is_real_model)
    return {
        "verdict": REALMODE_PASS if is_real_model else REALMODE_FAIL,
        "is_real_model": is_real_model,
        "model_loaded": is_real_model,
        "model_id": PYTHIA_160M_MANIFEST.model_id,
        "worker_version": PYTHIA_160M_MANIFEST.worker_version,
        "load_error": None if is_real_model else "real Pythia weights are not loaded in this worker build",
    }
