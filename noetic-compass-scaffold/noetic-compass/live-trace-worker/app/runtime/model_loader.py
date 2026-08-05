"""Model loader — loads real Pythia-160M weights when torch + transformers are
available, falls back to demo mode otherwise.

M2 change vs M1: instead of returning a static manifest, this module also
owns the live torch.nn.Module + tokenizer. The FastAPI app's startup hook
calls ``warm_load`` once at boot, then ``get_loaded_model()`` returns the
warm singleton for every subsequent request.

The two modes:

* **real** — torch + transformers import successfully, EleutherAI/pythia-160m
  weights load into memory. ``manifest.is_real_model = True`` and
  ``manifest.execution_kind = "real_model_weights"``.
  pythia_runner.run_pythia drives generation through these weights.

* **demo** — either torch is missing (CI / local dev), or
  ``LIVE_TRACE_DEMO_MODE=1`` is set, or the explicit load failed.
  ``manifest.is_real_model = False`` and
  ``manifest.execution_kind = "demo_schema_only"``. event_stream falls back
  to the schema-valid fake stream from M1.

User-visible contract: the cockpit's "Live · actual weights" badge MUST
only show when ``manifest.is_real_model = True``.
"""

from __future__ import annotations

import logging
import hashlib
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
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
# Exact Hugging Face repository commit present in the controlled local cache.
# A symbolic branch such as ``main`` is deliberately not accepted for a real
# Harness run because it can resolve to different bytes over time.
PYTHIA_160M_REVISION = "50f5173d932e8e61f858120bcb800b97af589f46"
PYTHIA_160M_WEIGHTS_FILENAME = "model.safetensors"
PYTHIA_160M_WEIGHTS_SHA256 = (
    "29d2e457a664e41c12c735f20a36dc0956a665f614a54ce5db21a32e75965270"
)
PYTHIA_160M_WEIGHTS_BYTES = 374_998_696
_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# Initial demo-mode manifest. real_load() returns a copy with
# is_real_model = True. Treat this as the worker's bootstrap default — it
# is what /manifest returns before warm_load runs (or if warm_load fails).
PYTHIA_160M_MANIFEST = ModelManifest(
    model_id=PYTHIA_160M_MODEL_ID,
    tokenizer_id=PYTHIA_160M_MODEL_ID,
    model_arch=_PYTHIA_ARCH,
    supported_hooks=[
        "residual_stream",
        "mlp_intermediate_post_activation",
        "attention_pattern",
        "logits",
    ],
    execution_kind="demo_schema_only",
    worker_version="m2-real-pythia",
    requested_revision=PYTHIA_160M_REVISION,
    resolved_revision=None,
    revision_verified=False,
    weights_filename=None,
    weights_sha256=None,
    weights_bytes=None,
    weights_hash_verified=False,
    model_identity_status="DEMO_OR_UNLOADED",
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
        return bool(
            self.manifest.is_real_model
            and self.manifest.execution_kind == "real_model_weights"
            and self.manifest.revision_verified
            and self.manifest.resolved_revision == PYTHIA_160M_REVISION
            and self.manifest.weights_hash_verified
            and self.manifest.weights_filename == PYTHIA_160M_WEIGHTS_FILENAME
            and self.manifest.weights_sha256 == PYTHIA_160M_WEIGHTS_SHA256
            and self.manifest.weights_bytes == PYTHIA_160M_WEIGHTS_BYTES
            and self.manifest.model_identity_status
            == "PINNED_REVISION_AND_WEIGHTS_SHA256"
            and self.model is not None
            and self.tokenizer is not None
            and self.load_error is None
        )


_LOADED: LoadedModel | None = None
_LOAD_LOCK = threading.Lock()


def _is_demo_mode_forced() -> bool:
    """env LIVE_TRACE_DEMO_MODE=1 forces the demo stream even if torch is fine.

    Used for local dev where you don't want the worker to download Pythia
    weights, and for cheap integration tests on CI runners.
    """
    return os.environ.get("LIVE_TRACE_DEMO_MODE", "0").strip().lower() in {"1", "true", "yes"}


def _validated_resolved_revision(model: Any) -> str:
    """Return the exact resolved commit or reject the load as non-attestable.

    Passing ``revision=...`` prevents branch drift.  We additionally require
    transformers to report the same commit on the loaded configuration so the
    emitted manifest is an observation, not merely a copy of requested input.
    This is revision attestation only; it is not a full weights digest.
    """

    requested = PYTHIA_160M_REVISION
    if not _COMMIT_SHA_RE.fullmatch(requested):
        raise RuntimeError("configured Pythia revision is not a full lowercase commit SHA")
    config = getattr(model, "config", None)
    resolved = getattr(config, "_commit_hash", None)
    if not isinstance(resolved, str) or not _COMMIT_SHA_RE.fullmatch(resolved):
        raise RuntimeError("loaded model did not report an exact resolved revision commit")
    if resolved != requested:
        raise RuntimeError("loaded model revision does not match the pinned requested revision")

    expected = {
        "hidden_size": _PYTHIA_ARCH.hidden_size,
        "intermediate_size": _PYTHIA_ARCH.mlp_intermediate_dim,
        "num_hidden_layers": _PYTHIA_ARCH.n_layers,
        "num_attention_heads": _PYTHIA_ARCH.n_heads,
    }
    for field_name, expected_value in expected.items():
        observed = getattr(config, field_name, None)
        if observed != expected_value:
            raise RuntimeError(
                f"loaded model architecture mismatch for {field_name}: "
                f"expected {expected_value}, observed {observed!r}"
            )
    return resolved


def _stream_file_sha256(path: Path) -> tuple[str, int]:
    """Hash a regular file while independently counting every byte read."""

    if not path.is_file():
        raise RuntimeError("resolved Pythia weights artifact is not a regular file")
    digest = hashlib.sha256()
    byte_count = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            byte_count += len(chunk)
    return digest.hexdigest(), byte_count


def _validated_weights_artifact(hf_hub_download: Any) -> tuple[str, str, int]:
    """Resolve and recompute the exact pinned Pythia safetensors artifact.

    ``local_files_only=True`` makes this an attestation of bytes already used by
    the pinned loader, not a second mutable network resolution.  The digest is
    a file-identity statement; it is not by itself a trust-root signature or a
    scientific-result attestation.
    """

    raw_path = hf_hub_download(
        repo_id=PYTHIA_160M_MODEL_ID,
        filename=PYTHIA_160M_WEIGHTS_FILENAME,
        revision=PYTHIA_160M_REVISION,
        local_files_only=True,
    )
    if not isinstance(raw_path, (str, os.PathLike)):
        raise RuntimeError("Hugging Face did not return a filesystem weights path")
    path = Path(raw_path)
    if path.name != PYTHIA_160M_WEIGHTS_FILENAME:
        raise RuntimeError("resolved Pythia weights filename does not match the pin")
    digest, byte_count = _stream_file_sha256(path)
    if digest != PYTHIA_160M_WEIGHTS_SHA256:
        raise RuntimeError("resolved Pythia weights SHA-256 does not match the pin")
    if byte_count != PYTHIA_160M_WEIGHTS_BYTES:
        raise RuntimeError("resolved Pythia weights byte length does not match the pin")
    return path.name, digest, byte_count


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
            from huggingface_hub import hf_hub_download

            logger.info(
                "warm_load: loading %s at pinned revision %s",
                PYTHIA_160M_MODEL_ID,
                PYTHIA_160M_REVISION,
            )
            tokenizer = AutoTokenizer.from_pretrained(
                PYTHIA_160M_MODEL_ID,
                revision=PYTHIA_160M_REVISION,
            )
            model = AutoModelForCausalLM.from_pretrained(
                PYTHIA_160M_MODEL_ID,
                revision=PYTHIA_160M_REVISION,
                use_safetensors=True,
                output_hidden_states=True,
                output_attentions=True,
            )
            model.eval()
            resolved_revision = _validated_resolved_revision(model)
            weights_filename, weights_sha256, weights_bytes = (
                _validated_weights_artifact(hf_hub_download)
            )
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

            real_manifest = ModelManifest.model_validate(
                {
                    **PYTHIA_160M_MANIFEST.model_dump(),
                    "is_real_model": True,
                    "execution_kind": "real_model_weights",
                    "resolved_revision": resolved_revision,
                    "revision_verified": True,
                    "weights_filename": weights_filename,
                    "weights_sha256": weights_sha256,
                    "weights_bytes": weights_bytes,
                    "weights_hash_verified": True,
                    "model_identity_status": (
                        "PINNED_REVISION_AND_WEIGHTS_SHA256"
                    ),
                },
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
