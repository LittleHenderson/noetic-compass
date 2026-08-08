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
QWEN_REALMODE_PASS = "REAL_QWEN2_5_0_5B_INSTRUCT_WEIGHTS_LOADED"
QWEN_REALMODE_FAIL = "NOT_REAL_QWEN2_5_0_5B_INSTRUCT_WEIGHTS"


def _realmode_verdict(
    binding: model_loader.ModelBinding,
    *,
    is_real_model: bool,
) -> str:
    """Return a model-specific verdict without changing Pythia's contract."""

    if binding.key == model_loader.PYTHIA_160M_BINDING_KEY:
        return REALMODE_PASS if is_real_model else REALMODE_FAIL
    if binding.key == model_loader.QWEN_05B_INSTRUCT_BINDING_KEY:
        return QWEN_REALMODE_PASS if is_real_model else QWEN_REALMODE_FAIL
    raise RuntimeError(f"no real-mode health verdict for binding {binding.key!r}")


@router.get("/health")
def health() -> dict:
    """Minimal public liveness surface; no model or failure metadata."""

    return {"status": "ok"}


@router.get("/health/realmode")
def health_realmode() -> dict:
    """Cheap proof surface for whether the selected pinned weights are live.

    This intentionally does not call get_loaded_model() or warm_load(). A cold
    worker reports the selected model's negative verdict until startup has
    actually loaded the model singleton.
    """
    binding = model_loader.active_model_binding()
    fake_runtime_env = model_loader._is_demo_mode_forced()
    loaded = model_loader._LOADED
    manifest = (
        loaded.manifest
        if loaded is not None
        else model_loader.bootstrap_manifest(binding)
    )
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
    verdict = _realmode_verdict(binding, is_real_model=is_real_model)

    return {
        "verdict": verdict,
        "is_real_model": is_real_model,
        "fake_runtime_env": fake_runtime_env,
        "model_loaded": model_loaded,
        "load_error": "MODEL_LOAD_FAILED" if load_error else None,
        "manifest_is_real_model": manifest_is_real_model,
        "model_id": manifest.model_id,
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
