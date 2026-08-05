"""GET /health — RunPod health-checks + the API proxy preflight.

M2: surfaces whether real weights are loaded so the API proxy can
fail-fast (HTTP 503) if a caller asks for LIVE mode but the worker is
still in demo mode after warm_load.
"""

from __future__ import annotations

from fastapi import APIRouter

from ..runtime import model_loader

router = APIRouter()

REALMODE_PASS = "REAL_PYTHIA_WEIGHTS_LOADED"
REALMODE_FAIL = "NOT_REAL_PYTHIA_WEIGHTS"


@router.get("/health")
def health() -> dict:
    """Minimal public liveness surface; no model or failure metadata."""

    return {"status": "ok"}


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
    revision_verified = bool(manifest.revision_verified)
    model_loaded = bool(
        loaded is not None
        and loaded.model is not None
        and loaded.tokenizer is not None
    )
    load_error = loaded.load_error if loaded is not None else None
    runtime_execution = manifest.runtime_execution

    is_real_model = bool(
        not fake_runtime_env and loaded is not None and loaded.is_real
    )
    verdict = REALMODE_PASS if is_real_model else REALMODE_FAIL

    return {
        "verdict": verdict,
        "is_real_model": is_real_model,
        "fake_runtime_env": fake_runtime_env,
        "model_loaded": model_loaded,
        "load_error": "MODEL_LOAD_FAILED" if load_error else None,
        "manifest_is_real_model": manifest_is_real_model,
        "model_id": model_loader.PYTHIA_160M_MODEL_ID,
        "requested_revision": manifest.requested_revision,
        "resolved_revision": manifest.resolved_revision,
        "revision_verified": revision_verified,
        "weights_filename": manifest.weights_filename,
        "weights_sha256": manifest.weights_sha256,
        "weights_bytes": manifest.weights_bytes,
        "weights_hash_verified": manifest.weights_hash_verified,
        "model_identity_status": manifest.model_identity_status,
        "runtime_execution": (
            runtime_execution.model_dump()
            if hasattr(runtime_execution, "model_dump")
            else None
        ),
        "worker_version": manifest.worker_version,
    }
