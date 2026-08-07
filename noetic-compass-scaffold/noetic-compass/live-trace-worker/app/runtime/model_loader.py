"""Fail-closed loader for the exact Pythia-160M artifact set.

The production profile accepts only the image-bound, non-writable model cache,
requires CUDA, validates the exact repository revision and every admitted
artifact before and after loading, and executes a geometry/numerics canary.
Any unrequested import or load failure raises. Explicit demo mode remains
available only outside the production profile.
"""

from __future__ import annotations

import logging
import ctypes
import hashlib
import os
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..schemas.manifest import ModelArch, ModelManifest, RuntimeExecutionEvidence

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
PYTHIA_160M_ARTIFACTS: dict[str, tuple[str, int]] = {
    "config.json": (
        "76eb275107220e450d31258f792a2efcbee109d8b62ae0088260057dec06362f",
        569,
    ),
    PYTHIA_160M_WEIGHTS_FILENAME: (
        PYTHIA_160M_WEIGHTS_SHA256,
        PYTHIA_160M_WEIGHTS_BYTES,
    ),
    "special_tokens_map.json": (
        "6f50ab5a5a509a1c309d6171f339b196a900dc9c99ad0408ff23bb615fdae7ad",
        99,
    ),
    "tokenizer.json": (
        "c24618a1b3e6a38167beff1c72cffd126c3a66254347304b50547d12c5f25624",
        2_113_710,
    ),
    "tokenizer_config.json": (
        "70e38394e494931c6f773ba41e19460dd4436526b852207367f04341b4066d3f",
        396,
    ),
}
_COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
WORKER_PROFILE_ENV = "ATLAS_WORKER_PROFILE"
TORCH_NATIVE_JIT_DISABLE_ENV = "TORCH_DISABLE_NATIVE_JIT"
DEVELOPMENT_PROFILE = "development"
PRODUCTION_PROFILE = "production"
PRODUCTION_HF_HOME = "/worker/.cache/huggingface"

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
            and isinstance(
                self.manifest.runtime_execution,
                RuntimeExecutionEvidence,
            )
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


def _worker_profile() -> str:
    profile = os.environ.get(WORKER_PROFILE_ENV, DEVELOPMENT_PROFILE).strip().lower()
    if profile not in {DEVELOPMENT_PROFILE, PRODUCTION_PROFILE}:
        raise RuntimeError(
            f"{WORKER_PROFILE_ENV} must be {DEVELOPMENT_PROFILE!r} or "
            f"{PRODUCTION_PROFILE!r}"
        )
    return profile


def _is_production_profile() -> bool:
    return _worker_profile() == PRODUCTION_PROFILE


def _validate_production_model_cache() -> None:
    """Require production model bytes to remain in the frozen image cache."""

    configured_home = os.environ.get("HF_HOME")
    if configured_home != PRODUCTION_HF_HOME:
        raise RuntimeError(
            "production worker profile requires the image-bound Hugging Face cache"
        )
    cache_root = Path(configured_home)
    if not cache_root.is_dir() or cache_root.is_symlink():
        raise RuntimeError(
            "production Hugging Face cache must be a real image directory"
        )
    if os.access(cache_root, os.W_OK):
        raise RuntimeError("production Hugging Face cache must be non-writable")


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


def _validated_model_artifacts(
    hf_hub_download: Any,
) -> dict[str, tuple[str, int]]:
    """Resolve and recompute every artifact used by the pinned Pythia load.

    ``local_files_only=True`` makes this an attestation of bytes already used by
    the pinned loader, not a second mutable network resolution. The artifact
    set covers model configuration, weights, and tokenizer inputs. These
    digests are file-identity statements; they are not a trust-root signature
    or a scientific-result attestation.
    """

    expected_artifacts = {
        **PYTHIA_160M_ARTIFACTS,
        PYTHIA_160M_WEIGHTS_FILENAME: (
            PYTHIA_160M_WEIGHTS_SHA256,
            PYTHIA_160M_WEIGHTS_BYTES,
        ),
    }
    observed: dict[str, tuple[str, int]] = {}
    for filename, (expected_digest, expected_bytes) in expected_artifacts.items():
        raw_path = hf_hub_download(
            repo_id=PYTHIA_160M_MODEL_ID,
            filename=filename,
            revision=PYTHIA_160M_REVISION,
            local_files_only=True,
        )
        if not isinstance(raw_path, (str, os.PathLike)):
            raise RuntimeError(
                f"Hugging Face did not return a filesystem path for {filename}"
            )
        path = Path(raw_path)
        if path.name != filename:
            raise RuntimeError(f"resolved Pythia artifact filename mismatch: {filename}")
        digest, byte_count = _stream_file_sha256(path)
        if digest != expected_digest:
            raise RuntimeError(f"resolved Pythia {filename} SHA-256 does not match the pin")
        if byte_count != expected_bytes:
            raise RuntimeError(f"resolved Pythia {filename} byte length does not match the pin")
        observed[filename] = (digest, byte_count)
    return observed


def _validated_weights_artifact(hf_hub_download: Any) -> tuple[str, str, int]:
    """Compatibility wrapper returning the verified weights identity tuple."""

    observed = _validated_model_artifacts(hf_hub_download)
    digest, byte_count = observed[PYTHIA_160M_WEIGHTS_FILENAME]
    return PYTHIA_160M_WEIGHTS_FILENAME, digest, byte_count


def _validate_model_execution_layout(
    model: Any,
    *,
    expected_device: str,
    expected_dtype: str,
) -> None:
    """Require every model parameter to be materialized on one device/dtype."""

    parameters = tuple(model.parameters())
    if not parameters:
        raise RuntimeError("Pythia model exposes no materialized parameters")
    for index, parameter in enumerate(parameters):
        observed_device = str(getattr(getattr(parameter, "device", None), "type", ""))
        observed_dtype = str(getattr(parameter, "dtype", ""))
        if observed_device != expected_device:
            raise RuntimeError(
                f"Pythia parameter {index} is on {observed_device!r}, expected "
                f"{expected_device!r}"
            )
        if observed_dtype != expected_dtype:
            raise RuntimeError(
                f"Pythia parameter {index} has dtype {observed_dtype!r}, expected "
                f"{expected_dtype!r}"
            )


def _resolve_model_dtype(torch: Any, *, cuda_available: bool) -> tuple[Any, str]:
    """Choose a finite, no-JIT inference dtype for the active runtime.

    Torch 2.13's CUDA-native override path requires a runtime C compiler. The
    production worker intentionally ships no compiler, and disabling that path
    exposed non-finite Pythia logits in float16 on the bounded RTX 4070 canary.
    BF16 is finite on supported GPUs. Production fails closed when hardware
    BF16 is absent instead of silently changing the admitted CUDA substrate.
    """

    if not cuda_available:
        return torch.float32, "torch.float32"
    if not bool(torch.cuda.is_bf16_supported(including_emulation=False)):
        raise RuntimeError("production CUDA execution requires native BF16 support")
    return torch.bfloat16, "torch.bfloat16"


def _read_cuda_driver_version() -> int:
    """Read the active NVIDIA driver API version from libcuda."""

    libcuda = ctypes.CDLL("libcuda.so.1")
    if libcuda.cuInit(0) != 0:
        raise RuntimeError("CUDA driver initialization failed")
    observed = ctypes.c_int()
    if libcuda.cuDriverGetVersion(ctypes.byref(observed)) != 0 or observed.value <= 0:
        raise RuntimeError("CUDA driver version query failed")
    return int(observed.value)


def _runtime_execution_evidence(
    torch: Any,
    *,
    profile: str,
    device: str,
    dtype: str,
) -> RuntimeExecutionEvidence:
    payload: dict[str, Any] = {
        "profile": profile,
        "device": device,
        "dtype": dtype,
        "torch_version": str(getattr(torch, "__version__", "UNKNOWN")),
        "torch_native_jit_disabled": (
            os.getenv(TORCH_NATIVE_JIT_DISABLE_ENV) == "1"
        ),
    }
    if payload["torch_version"] == "UNKNOWN":
        raise RuntimeError("Torch runtime version is not observable")
    if device == "cuda":
        device_index = int(torch.cuda.current_device())
        capability = torch.cuda.get_device_capability(device_index)
        payload.update(
            {
                "cuda_runtime_version": str(torch.version.cuda),
                "cuda_driver_version": _read_cuda_driver_version(),
                "cuda_device_name": str(torch.cuda.get_device_name(device_index)),
                "cuda_device_capability": f"{int(capability[0])}.{int(capability[1])}",
                "cuda_bfloat16_supported": bool(
                    torch.cuda.is_bf16_supported(including_emulation=False)
                ),
            }
        )
    return RuntimeExecutionEvidence.model_validate(payload)


def _validate_runtime_canary(
    torch: Any,
    model: Any,
    tokenizer: Any,
    *,
    device: str,
) -> None:
    """Execute the attention/hook/numerics contract before real status."""

    architecture = PYTHIA_160M_MANIFEST.model_arch
    projection = model.gpt_neox.layers[0].mlp.dense_4h_to_h
    observed_hook_widths: list[int] = []

    def _projection_pre_hook(_module: Any, args: tuple[Any, ...]) -> None:
        if not args or not hasattr(args[0], "shape"):
            raise RuntimeError("Pythia runtime canary hook did not receive a tensor")
        activation = args[0]
        observed_hook_widths.append(int(activation.shape[-1]))
        if not bool(torch.isfinite(activation).all().item()):
            raise RuntimeError("Pythia runtime canary hook received nonfinite values")

    handle = projection.register_forward_pre_hook(_projection_pre_hook)
    try:
        encoded = tokenizer(
            "Project Coherence Gate 5 runtime canary.",
            return_tensors="pt",
        )
        inputs = {
            key: value.to(device) if hasattr(value, "to") else value
            for key, value in encoded.items()
        }
        input_ids = inputs.get("input_ids")
        if input_ids is None or not hasattr(input_ids, "shape"):
            raise RuntimeError("Pythia runtime canary tokenizer returned no input_ids")
        sequence_length = int(input_ids.shape[1])
        with torch.no_grad():
            outputs = model(
                **inputs,
                output_attentions=True,
                output_hidden_states=False,
                use_cache=False,
            )
    finally:
        handle.remove()

    attentions = tuple(outputs.attentions or ())
    if len(attentions) != architecture.n_layers:
        raise RuntimeError("Pythia runtime canary returned the wrong attention layer count")
    expected_shape = (
        1,
        architecture.n_heads,
        sequence_length,
        sequence_length,
    )
    if any(tuple(attention.shape) != expected_shape for attention in attentions):
        raise RuntimeError("Pythia runtime canary returned incompatible attention geometry")
    if observed_hook_widths != [architecture.mlp_intermediate_dim]:
        raise RuntimeError("Pythia runtime canary returned incompatible hook geometry")
    if not bool(torch.isfinite(outputs.logits).all().item()):
        raise RuntimeError("Pythia runtime canary produced nonfinite logits")
    if any(not bool(torch.isfinite(attention).all().item()) for attention in attentions):
        raise RuntimeError("Pythia runtime canary produced nonfinite attention")


def warm_load() -> LoadedModel:
    """Load Pythia-160M into memory once. Idempotent + thread-safe.

    Called from the FastAPI startup hook. Subsequent calls return the
    cached LoadedModel. LIVE_TRACE_DEMO_MODE is the only path to a demo
    LoadedModel. Any unrequested load failure raises so real-mode startup
    cannot silently substitute synthetic execution.
    """
    global _LOADED
    with _LOAD_LOCK:
        if _LOADED is not None:
            return _LOADED

        profile = _worker_profile()
        if _is_demo_mode_forced():
            if profile == PRODUCTION_PROFILE:
                raise RuntimeError("production worker profile forbids demo mode")
            logger.info("warm_load: LIVE_TRACE_DEMO_MODE=1 — staying in demo mode")
            _LOADED = LoadedModel(manifest=PYTHIA_160M_MANIFEST)
            return _LOADED
        if profile == PRODUCTION_PROFILE:
            _validate_production_model_cache()
            if os.getenv(TORCH_NATIVE_JIT_DISABLE_ENV) != "1":
                raise RuntimeError(
                    "production worker requires TORCH_DISABLE_NATIVE_JIT=1 "
                    "because the runtime image intentionally has no compiler"
                )

        try:
            # Heavy imports stay local so an explicitly requested development
            # demo remains lightweight. Any unrequested failure raises.
            import torch  # noqa: F401
            from transformers import AutoModelForCausalLM, AutoTokenizer
            from huggingface_hub import hf_hub_download

            logger.info(
                "warm_load: loading %s at pinned revision %s",
                PYTHIA_160M_MODEL_ID,
                PYTHIA_160M_REVISION,
            )
            cuda_available = bool(torch.cuda.is_available())
            if profile == PRODUCTION_PROFILE and not cuda_available:
                raise RuntimeError(
                    "production worker profile requires an available CUDA device"
                )
            artifact_observations = _validated_model_artifacts(hf_hub_download)
            tokenizer = AutoTokenizer.from_pretrained(
                PYTHIA_160M_MODEL_ID,
                revision=PYTHIA_160M_REVISION,
                local_files_only=True,
            )
            load_dtype, execution_dtype = _resolve_model_dtype(
                torch,
                cuda_available=cuda_available,
            )
            model = AutoModelForCausalLM.from_pretrained(
                PYTHIA_160M_MODEL_ID,
                revision=PYTHIA_160M_REVISION,
                use_safetensors=True,
                dtype=load_dtype,
                attn_implementation="eager",
                local_files_only=True,
            )
            model.eval()
            resolved_revision = _validated_resolved_revision(model)
            weights_sha256, weights_bytes = artifact_observations[
                PYTHIA_160M_WEIGHTS_FILENAME
            ]
            weights_filename = PYTHIA_160M_WEIGHTS_FILENAME
            # Development may run the bounded CPU canary. Production requires
            # CUDA; the resolved finite dtype is preserved across the move.
            if cuda_available:
                model = model.to("cuda")
                logger.info("warm_load: model moved to cuda")
                execution_device = "cuda"
            else:
                logger.info("warm_load: cuda not available — staying on cpu")
                execution_device = "cpu"

            _validate_model_execution_layout(
                model,
                expected_device=execution_device,
                expected_dtype=execution_dtype,
            )

            _validate_runtime_canary(
                torch,
                model,
                tokenizer,
                device=execution_device,
            )
            post_load_observations = _validated_model_artifacts(hf_hub_download)
            if post_load_observations != artifact_observations:
                raise RuntimeError(
                    "Pythia artifact identity changed during model loading"
                )
            runtime_execution = _runtime_execution_evidence(
                torch,
                profile=profile,
                device=execution_device,
                dtype=execution_dtype,
            )

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
                    "runtime_execution": runtime_execution.model_dump(),
                },
            )
            _LOADED = LoadedModel(
                manifest=real_manifest,
                model=model,
                tokenizer=tokenizer,
            )
            logger.info("warm_load: model loaded, is_real_model=True")
        except Exception:  # broad boundary: real-mode startup must fail closed
            logger.exception("warm_load: failed closed; startup cannot proceed")
            _LOADED = None
            raise
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
