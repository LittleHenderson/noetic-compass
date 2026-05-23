"""GET /health — used by RunPod health checks + the API proxy preflight."""

from __future__ import annotations

from fastapi import APIRouter

from ..runtime import PYTHIA_160M_MANIFEST

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "worker_version": PYTHIA_160M_MANIFEST.worker_version,
        "model_id": PYTHIA_160M_MANIFEST.model_id,
        "is_real_model": PYTHIA_160M_MANIFEST.is_real_model,
    }
