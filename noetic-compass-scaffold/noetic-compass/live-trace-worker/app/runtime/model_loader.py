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
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from ..schemas.manifest import (
    ModelArch,
    ModelManifest,
    ObservationOnlyHookContract,
    RuntimeExecutionEvidence,
)

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
# --- Stage B additive second pinned model ------------------------------
#
# pythia-160m is a base model and does not reliably follow instructions, so a
# joined Stage B run cannot exercise a realistic instruction request with it.
# The binding below ADDS a pinned instruction-tuned model. It does not replace,
# relax, or retire the pythia pin: every PYTHIA_160M_* constant above remains
# the exact default, and a worker that sets no environment variable behaves
# identically to before this addition.
#
# Selecting a model creates no detection, steering, scientific, product,
# licensing, or disclosure claim.

QWEN_05B_INSTRUCT_MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
QWEN_05B_INSTRUCT_REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
QWEN_05B_INSTRUCT_WEIGHTS_FILENAME = "model.safetensors"
QWEN_05B_INSTRUCT_WEIGHTS_SHA256 = (
    "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe"
)
QWEN_05B_INSTRUCT_WEIGHTS_BYTES = 988_097_824
QWEN_05B_INSTRUCT_ARTIFACTS: dict[str, tuple[str, int]] = {
    "config.json": (
        "18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45",
        659,
    ),
    "generation_config.json": (
        "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6",
        242,
    ),
    "merges.txt": (
        "599bab54075088774b1733fde865d5bd747cbcc7a547c5bc12610e874e26f5e3",
        1_671_839,
    ),
    QWEN_05B_INSTRUCT_WEIGHTS_FILENAME: (
        QWEN_05B_INSTRUCT_WEIGHTS_SHA256,
        QWEN_05B_INSTRUCT_WEIGHTS_BYTES,
    ),
    "tokenizer.json": (
        "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539",
        7_031_645,
    ),
    "tokenizer_config.json": (
        "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583",
        7_305,
    ),
    "vocab.json": (
        "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
        2_776_833,
    ),
}
# Geometry read from the pinned config.json; total_params measured by summing
# parameter element counts on the loaded model inside the frozen image.
_QWEN_05B_INSTRUCT_ARCH = ModelArch(
    family="qwen2",
    n_layers=24,
    hidden_size=896,
    mlp_intermediate_dim=4864,
    n_heads=14,
    total_params=494_032_768,
    validated=True,
)


@dataclass(frozen=True)
class ModelBinding:
    """One exactly pinned model identity plus its declared architecture."""

    key: str
    model_id: str
    revision: str
    weights_filename: str
    weights_sha256: str
    weights_bytes: int
    artifacts: Mapping[str, tuple[str, int]]
    arch: ModelArch
    worker_version: str
    probe_layer_stack_path: tuple[str, ...]
    probe_projection_path: tuple[str, ...]
    stage27f_intervention_supported: bool
    stage27f_cover_library_supported: bool
    single_unit_causal_ablation_supported: bool

    @property
    def probe_layer_stack_attr(self) -> str:
        return ".".join(self.probe_layer_stack_path)

    @property
    def probe_projection_attr(self) -> str:
        return ".".join(self.probe_projection_path)


PYTHIA_160M_BINDING_KEY = "pythia-160m"
QWEN_05B_INSTRUCT_BINDING_KEY = "qwen2.5-0.5b-instruct"
MODEL_BINDING_KEYS = (PYTHIA_160M_BINDING_KEY, QWEN_05B_INSTRUCT_BINDING_KEY)
ACTIVE_MODEL_ENV = "ATLAS_WORKER_MODEL"
DEFAULT_MODEL_KEY = PYTHIA_160M_BINDING_KEY


# Bindings are built per call, never snapshotted at import. The pinned
# constants above are the single source of truth, and the fail-closed identity
# tests substitute them at runtime; an import-time snapshot would silently
# ignore that substitution and make those tests assert nothing.
def _pythia_binding() -> ModelBinding:
    return ModelBinding(
        key=PYTHIA_160M_BINDING_KEY,
        model_id=PYTHIA_160M_MODEL_ID,
        revision=PYTHIA_160M_REVISION,
        weights_filename=PYTHIA_160M_WEIGHTS_FILENAME,
        weights_sha256=PYTHIA_160M_WEIGHTS_SHA256,
        weights_bytes=PYTHIA_160M_WEIGHTS_BYTES,
        artifacts=MappingProxyType(dict(PYTHIA_160M_ARTIFACTS)),
        arch=_PYTHIA_ARCH,
        worker_version="m2-real-pythia",
        probe_layer_stack_path=("gpt_neox", "layers"),
        probe_projection_path=("mlp", "dense_4h_to_h"),
        stage27f_intervention_supported=True,
        stage27f_cover_library_supported=True,
        single_unit_causal_ablation_supported=True,
    )


def _qwen_05b_instruct_binding() -> ModelBinding:
    return ModelBinding(
        key=QWEN_05B_INSTRUCT_BINDING_KEY,
        model_id=QWEN_05B_INSTRUCT_MODEL_ID,
        revision=QWEN_05B_INSTRUCT_REVISION,
        weights_filename=QWEN_05B_INSTRUCT_WEIGHTS_FILENAME,
        weights_sha256=QWEN_05B_INSTRUCT_WEIGHTS_SHA256,
        weights_bytes=QWEN_05B_INSTRUCT_WEIGHTS_BYTES,
        artifacts=MappingProxyType(dict(QWEN_05B_INSTRUCT_ARTIFACTS)),
        arch=_QWEN_05B_INSTRUCT_ARCH,
        worker_version="stageb-real-qwen2.5-0.5b-instruct",
        probe_layer_stack_path=("model", "layers"),
        probe_projection_path=("mlp", "down_proj"),
        stage27f_intervention_supported=False,
        stage27f_cover_library_supported=False,
        single_unit_causal_ablation_supported=False,
    )


_BINDING_BUILDERS: Mapping[str, Any] = MappingProxyType(
    {
        PYTHIA_160M_BINDING_KEY: _pythia_binding,
        QWEN_05B_INSTRUCT_BINDING_KEY: _qwen_05b_instruct_binding,
    }
)


def active_model_binding() -> ModelBinding:
    """Return the selected pinned binding, defaulting to the pythia pin.

    An unset or empty environment variable selects pythia, so existing callers
    and receipts are unchanged. An unrecognized value fails closed rather than
    silently falling back, because a wrong model would silently invalidate every
    identity assertion the loader makes.
    """

    raw = os.environ.get(ACTIVE_MODEL_ENV, "").strip().lower()
    if not raw:
        return _BINDING_BUILDERS[DEFAULT_MODEL_KEY]()
    builder = _BINDING_BUILDERS.get(raw)
    if builder is None:
        raise RuntimeError(
            f"{ACTIVE_MODEL_ENV}={raw!r} is not a pinned model binding; "
            f"expected one of {sorted(_BINDING_BUILDERS)}"
        )
    return builder()


def probe_hook_module_path(binding: ModelBinding, layer: int) -> str:
    """Return the exact selected-binding projection path for one layer."""

    return (
        f"{binding.probe_layer_stack_attr}[{layer}]."
        f"{binding.probe_projection_attr}"
    )


def resolve_probe_layer_stack(
    model: Any,
    binding: ModelBinding,
    *,
    expected_layers: int,
    require_exact_count: bool = False,
) -> Any:
    """Resolve only the stack declared by the selected pinned binding.

    No cross-family fallback is permitted here. A Qwen-selected worker must not
    silently probe a coincidental ``gpt_neox.layers`` attribute, and the
    historical Pythia binding continues to resolve only ``gpt_neox.layers``.
    """

    value = model
    for attribute in binding.probe_layer_stack_path:
        value = getattr(value, attribute, None)
        if value is None:
            raise RuntimeError(
                "selected model probe stack is unavailable: expected "
                f"{binding.probe_layer_stack_attr} for {binding.key}"
            )
    try:
        observed_layers = len(value)
    except Exception as exc:
        raise RuntimeError(
            "selected model probe stack does not expose an exact layer count"
        ) from exc
    if type(expected_layers) is not int or expected_layers < 1:
        raise RuntimeError("selected model probe layer count must be a positive integer")
    if observed_layers < expected_layers or (
        require_exact_count and observed_layers != expected_layers
    ):
        comparison = "exactly" if require_exact_count else "at least"
        raise RuntimeError(
            f"selected model probe stack must expose {comparison} {expected_layers} "
            f"layers; observed {observed_layers}"
        )
    return value


def resolve_probe_projection(
    layer: Any,
    binding: ModelBinding,
    *,
    layer_index: int,
) -> Any:
    """Resolve and validate the selected layer's activated-MLP projection."""

    value = layer
    for attribute in binding.probe_projection_path:
        value = getattr(value, attribute, None)
        if value is None:
            raise RuntimeError(
                "selected model probe projection is unavailable: expected "
                f"{probe_hook_module_path(binding, layer_index)}"
            )
    if not hasattr(value, "register_forward_pre_hook"):
        raise RuntimeError(
            "selected model probe projection cannot register a forward pre-hook: "
            f"{probe_hook_module_path(binding, layer_index)}"
        )
    observed_input = getattr(value, "in_features", None)
    observed_output = getattr(value, "out_features", None)
    if (
        type(observed_input) is not int
        or observed_input != binding.arch.mlp_intermediate_dim
    ):
        raise RuntimeError(
            "selected model probe projection input width mismatch at "
            f"{probe_hook_module_path(binding, layer_index)}: expected "
            f"{binding.arch.mlp_intermediate_dim}, observed {observed_input!r}"
        )
    if (
        type(observed_output) is not int
        or observed_output != binding.arch.hidden_size
    ):
        raise RuntimeError(
            "selected model probe projection output width mismatch at "
            f"{probe_hook_module_path(binding, layer_index)}: expected "
            f"{binding.arch.hidden_size}, observed {observed_output!r}"
        )
    return value


def encode_runtime_prompt(
    tokenizer: Any,
    prompt: str,
    *,
    binding: ModelBinding,
) -> dict[str, Any]:
    """Encode one runtime prompt under the selected pinned tokenizer contract.

    Pythia retains its historical raw-tokenization call. The Qwen Instruct
    binding must use the chat template carried by the already hash-verified
    pinned ``tokenizer_config.json``; a missing template or unusable result is
    a startup/runtime error rather than a raw-prompt fallback.
    """

    if binding.key == PYTHIA_160M_BINDING_KEY:
        encoded = tokenizer(prompt, return_tensors="pt")
    elif binding.key == QWEN_05B_INSTRUCT_BINDING_KEY:
        chat_template = getattr(tokenizer, "chat_template", None)
        apply_chat_template = getattr(tokenizer, "apply_chat_template", None)
        if not isinstance(chat_template, str) or not chat_template.strip():
            raise RuntimeError("pinned Qwen tokenizer exposes no chat template")
        if not callable(apply_chat_template):
            raise RuntimeError("pinned Qwen tokenizer cannot apply its chat template")
        encoded = apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        )
    else:  # defensive: active_model_binding already rejects unknown keys
        raise RuntimeError(f"no runtime prompt encoder for binding {binding.key!r}")

    if isinstance(encoded, Mapping):
        inputs = dict(encoded)
    else:
        input_ids = getattr(encoded, "input_ids", None)
        if input_ids is None and hasattr(encoded, "shape"):
            input_ids = encoded
        inputs = {"input_ids": input_ids}
    input_ids = inputs.get("input_ids")
    shape = getattr(input_ids, "shape", None)
    if shape is None or len(shape) != 2 or int(shape[0]) != 1 or int(shape[1]) < 1:
        raise RuntimeError("runtime prompt encoder returned invalid input_ids geometry")
    return inputs


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

QWEN_05B_OBSERVATION_ONLY_HOOK_CONTRACT = ObservationOnlyHookContract()


def bootstrap_manifest(binding: ModelBinding | None = None) -> ModelManifest:
    """Return the unloaded bootstrap manifest for a pinned binding.

    The pythia binding returns the historical ``PYTHIA_160M_MANIFEST`` object
    unchanged so existing receipts and comparisons are byte-identical.
    """

    binding = binding or active_model_binding()
    if binding.key == PYTHIA_160M_BINDING_KEY:
        return PYTHIA_160M_MANIFEST
    return ModelManifest.model_validate(
        {
            **PYTHIA_160M_MANIFEST.model_dump(),
            "model_id": binding.model_id,
            "tokenizer_id": binding.model_id,
            "model_arch": binding.arch.model_dump(),
            "intervention_hook_contract": (
                QWEN_05B_OBSERVATION_ONLY_HOOK_CONTRACT.model_dump()
            ),
            "worker_version": binding.worker_version,
            "requested_revision": binding.revision,
        },
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
        return _loaded_model_is_real_for_binding(self, active_model_binding())


def _loaded_model_is_real_for_binding(
    loaded: LoadedModel,
    binding: ModelBinding,
) -> bool:
    """Validate one loaded carrier against one already-selected binding.

    The binding is supplied explicitly so a cached carrier cannot be judged
    against a different environment selection midway through validation.
    This validates the carrier metadata; callers that may execute a model must
    additionally validate the concrete family stack with
    :func:`require_pythia_runtime_model`.
    """

    if not _loaded_model_carrier_matches_binding(loaded, binding):
        return False
    return bool(
            loaded.manifest.is_real_model
            and loaded.manifest.execution_kind == "real_model_weights"
            and loaded.manifest.revision_verified
            and loaded.manifest.resolved_revision == binding.revision
            and loaded.manifest.weights_hash_verified
            and loaded.manifest.weights_filename == binding.weights_filename
            and loaded.manifest.weights_sha256 == binding.weights_sha256
            and loaded.manifest.weights_bytes == binding.weights_bytes
            and loaded.manifest.model_identity_status
            == "PINNED_REVISION_AND_WEIGHTS_SHA256"
            and isinstance(
                loaded.manifest.runtime_execution,
                RuntimeExecutionEvidence,
            )
            and loaded.model is not None
            and loaded.tokenizer is not None
            and loaded.load_error is None
        )


def _loaded_model_carrier_matches_binding(
    loaded: LoadedModel,
    binding: ModelBinding,
) -> bool:
    """Match cached carrier metadata to one exact selected binding.

    This includes demo carriers, which intentionally are not ``is_real`` but
    still must never be returned after the process selection changes to a
    different model family.
    """

    if type(loaded) is not LoadedModel or type(binding) is not ModelBinding:
        return False
    try:
        expected = bootstrap_manifest(binding)
    except Exception:
        return False
    return bool(
            loaded.manifest.model_id == expected.model_id
            and loaded.manifest.tokenizer_id == expected.tokenizer_id
            and loaded.manifest.model_arch == expected.model_arch
            and loaded.manifest.supported_hooks == expected.supported_hooks
            and loaded.manifest.intervention_hook_contract
            == expected.intervention_hook_contract
            and loaded.manifest.worker_version == expected.worker_version
            and loaded.manifest.requested_revision == binding.revision
        )


def require_pythia_runtime_model(
    model: Any,
    *,
    binding: ModelBinding,
    expected_layers: int,
) -> None:
    """Reject any non-Pythia concrete model before generic execution.

    Manifest checks alone cannot authenticate the Python object that will be
    called.  In particular, a cached Qwen object must not become eligible when
    the process environment later selects Pythia.  The exact Pythia stack is
    therefore resolved at the final generic boundary before tokenization or a
    forward pass.
    """

    if type(binding) is not ModelBinding or binding != _pythia_binding():
        raise RuntimeError(
            "generic real-model execution requires the exact pinned Pythia binding"
        )
    resolve_probe_layer_stack(
        model,
        binding,
        expected_layers=expected_layers,
        require_exact_count=(expected_layers == binding.arch.n_layers),
    )
    config = getattr(model, "config", None)
    model_type = getattr(config, "model_type", None) if config is not None else None
    if model_type is not None and model_type != "gpt_neox":
        raise RuntimeError(
            "generic real-model execution requires a concrete Pythia/GPT-NeoX model"
        )


def require_loaded_pythia_runtime(
    loaded: LoadedModel,
    *,
    binding: ModelBinding,
) -> None:
    """Cross-bind a loaded carrier, its manifest, and concrete Pythia model."""

    if not _loaded_model_is_real_for_binding(loaded, binding):
        raise RuntimeError(
            "loaded model carrier does not match the exact pinned Pythia binding"
        )
    require_pythia_runtime_model(
        loaded.model,
        binding=binding,
        # This boundary authenticates the concrete model *family* before a
        # carrier can be dispatched.  The real runner separately requires the
        # full requested layer count immediately before any forward; keeping
        # this check at one layer also permits isolated stub-runner tests.
        expected_layers=1,
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

    binding = active_model_binding()
    requested = binding.revision
    if not _COMMIT_SHA_RE.fullmatch(requested):
        raise RuntimeError("configured Pythia revision is not a full lowercase commit SHA")
    config = getattr(model, "config", None)
    resolved = getattr(config, "_commit_hash", None)
    if not isinstance(resolved, str) or not _COMMIT_SHA_RE.fullmatch(resolved):
        raise RuntimeError("loaded model did not report an exact resolved revision commit")
    if resolved != requested:
        raise RuntimeError("loaded model revision does not match the pinned requested revision")

    expected = {
        "hidden_size": binding.arch.hidden_size,
        "intermediate_size": binding.arch.mlp_intermediate_dim,
        "num_hidden_layers": binding.arch.n_layers,
        "num_attention_heads": binding.arch.n_heads,
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

    binding = active_model_binding()
    expected_artifacts = {
        **binding.artifacts,
        binding.weights_filename: (
            binding.weights_sha256,
            binding.weights_bytes,
        ),
    }
    observed: dict[str, tuple[str, int]] = {}
    for filename, (expected_digest, expected_bytes) in expected_artifacts.items():
        raw_path = hf_hub_download(
            repo_id=binding.model_id,
            filename=filename,
            revision=binding.revision,
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
    weights_filename = active_model_binding().weights_filename
    digest, byte_count = observed[weights_filename]
    return weights_filename, digest, byte_count


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

    binding = active_model_binding()
    if binding.key != PYTHIA_160M_BINDING_KEY:
        # Stage C authorization v1 fixes ``canary_count`` to zero.  Guard the
        # low-level function itself so a direct caller cannot bypass the
        # warm-load branch and execute an unpermitted Qwen forward.
        raise RuntimeError(
            "the Qwen Stage C runtime canary is forbidden by the exact "
            "zero-canary authorization scope"
        )
    architecture = binding.arch
    canary_label = "Pythia"
    require_pythia_runtime_model(
        model,
        binding=binding,
        expected_layers=architecture.n_layers,
    )
    layers = resolve_probe_layer_stack(
        model,
        binding,
        expected_layers=architecture.n_layers,
        require_exact_count=True,
    )
    projection = resolve_probe_projection(layers[0], binding, layer_index=0)
    observed_hook_widths: list[int] = []

    def _projection_pre_hook(_module: Any, args: tuple[Any, ...]) -> None:
        if not args or not hasattr(args[0], "shape"):
            raise RuntimeError(
                f"{canary_label} runtime canary hook did not receive a tensor"
            )
        activation = args[0]
        observed_hook_widths.append(int(activation.shape[-1]))
        if not bool(torch.isfinite(activation).all().item()):
            raise RuntimeError(
                f"{canary_label} runtime canary hook received nonfinite values"
            )

    handle = projection.register_forward_pre_hook(_projection_pre_hook)
    try:
        encoded = encode_runtime_prompt(
            tokenizer,
            "Project Coherence Gate 5 runtime canary.",
            binding=binding,
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
        raise RuntimeError(
            f"{canary_label} runtime canary returned the wrong attention layer count"
        )
    expected_shape = (
        1,
        architecture.n_heads,
        sequence_length,
        sequence_length,
    )
    if any(tuple(attention.shape) != expected_shape for attention in attentions):
        raise RuntimeError(
            f"{canary_label} runtime canary returned incompatible attention geometry"
        )
    if observed_hook_widths != [architecture.mlp_intermediate_dim]:
        raise RuntimeError(
            f"{canary_label} runtime canary returned incompatible hook geometry"
        )
    if not bool(torch.isfinite(outputs.logits).all().item()):
        raise RuntimeError(f"{canary_label} runtime canary produced nonfinite logits")
    if any(not bool(torch.isfinite(attention).all().item()) for attention in attentions):
        raise RuntimeError(
            f"{canary_label} runtime canary produced nonfinite attention"
        )


def _startup_runtime_canary_permitted(binding: ModelBinding) -> bool:
    """Return whether this binding's separate startup contract permits a forward.

    Stage C Qwen authorization v1 allows exactly zero canaries.  This helper is
    deliberately keyed to the closed model binding rather than an environment
    flag or caller argument, so startup configuration cannot widen that scope.
    """

    if type(binding) is not ModelBinding:
        raise RuntimeError("startup canary decision requires an exact model binding")
    return binding.key != QWEN_05B_INSTRUCT_BINDING_KEY


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
            binding = active_model_binding()
            if not _loaded_model_carrier_matches_binding(_LOADED, binding):
                raise RuntimeError(
                    "cached model carrier does not match the active pinned binding; "
                    "refusing cross-family cache reuse"
                )
            return _LOADED

        profile = _worker_profile()
        if _is_demo_mode_forced():
            if profile == PRODUCTION_PROFILE:
                raise RuntimeError("production worker profile forbids demo mode")
            logger.info("warm_load: LIVE_TRACE_DEMO_MODE=1 — staying in demo mode")
            _LOADED = LoadedModel(
                manifest=bootstrap_manifest(active_model_binding())
            )
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

            binding = active_model_binding()
            logger.info(
                "warm_load: loading %s at pinned revision %s",
                binding.model_id,
                binding.revision,
            )
            cuda_available = bool(torch.cuda.is_available())
            if profile == PRODUCTION_PROFILE and not cuda_available:
                raise RuntimeError(
                    "production worker profile requires an available CUDA device"
                )
            artifact_observations = _validated_model_artifacts(hf_hub_download)
            tokenizer = AutoTokenizer.from_pretrained(
                binding.model_id,
                revision=binding.revision,
                local_files_only=True,
            )
            load_dtype, execution_dtype = _resolve_model_dtype(
                torch,
                cuda_available=cuda_available,
            )
            model = AutoModelForCausalLM.from_pretrained(
                binding.model_id,
                revision=binding.revision,
                use_safetensors=True,
                dtype=load_dtype,
                attn_implementation="eager",
                local_files_only=True,
            )
            model.eval()
            resolved_revision = _validated_resolved_revision(model)
            weights_sha256, weights_bytes = artifact_observations[
                binding.weights_filename
            ]
            weights_filename = binding.weights_filename
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

            # The Stage C prerequisite authorization v1 fixes
            # ``canary_count`` to zero.  Loading and re-hashing the pinned Qwen
            # bytes is therefore allowed to prepare a dormant carrier, but a
            # startup forward would be an unauthorized model evaluation.  The
            # per-row capture path has a separate runtime-activation choke
            # point; it is the only place a Stage C Qwen forward may occur.
            #
            # Preserve the historical Pythia readiness canary for its separate
            # worker contract.  It must not be silently reused as Stage C
            # authority.
            if _startup_runtime_canary_permitted(binding):
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
                    **bootstrap_manifest(binding).model_dump(),
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
    # Always pass through the locked cache/binding check.  Reading ``_LOADED``
    # directly here would allow a Qwen carrier cached under one environment
    # selection to be reused after the process switches to Pythia (or vice
    # versa).
    return warm_load()


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
    active = active_model_binding()
    if model_id != active.model_id:
        raise ValueError(
            f"model_id={model_id!r} not supported at v0.1. "
            f"Only {active.model_id} is wired."
        )
    loaded = get_loaded_model()
    return loaded.manifest
