"""Adversarial tests for revision-pinned live-model identity."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from pydantic import ValidationError

from app.runtime import model_loader
from app.schemas.manifest import ModelManifest


class _FakeModel:
    def __init__(
        self,
        revision: str,
        *,
        hidden_size: int = 768,
        cuda_move_error: Exception | None = None,
    ) -> None:
        self.config = SimpleNamespace(
            _commit_hash=revision,
            hidden_size=hidden_size,
            intermediate_size=3072,
            num_hidden_layers=12,
            num_attention_heads=12,
        )
        self.eval_called = False
        self.cuda_move_error = cuda_move_error
        self.to_calls: list[str] = []
        self._parameter = SimpleNamespace(
            device=SimpleNamespace(type="cpu"),
            dtype="torch.float32",
        )

    def eval(self) -> None:
        self.eval_called = True

    def to(self, device: str) -> "_FakeModel":
        self.to_calls.append(device)
        if self.cuda_move_error is not None:
            raise self.cuda_move_error
        self._parameter.device = SimpleNamespace(type=device)
        return self

    def parameters(self):
        return iter((self._parameter,))


def _install_fake_runtime(
    monkeypatch,
    model: _FakeModel,
    tmp_path: Path,
    *,
    cuda_available: bool = False,
    cuda_bfloat16_supported: bool = True,
) -> list[tuple[str, str, dict]]:
    calls: list[tuple[str, str, dict]] = []
    artifact_bytes = {
        "config.json": b'{"model_type":"gpt_neox"}',
        model_loader.PYTHIA_160M_WEIGHTS_FILENAME: b"typed-pythia-weights-fixture",
        "special_tokens_map.json": b"{}",
        "tokenizer.json": b'{"version":"1.0"}',
        "tokenizer_config.json": b"{}",
    }
    artifact_paths: dict[str, Path] = {}
    artifact_pins: dict[str, tuple[str, int]] = {}
    for filename, content in artifact_bytes.items():
        path = tmp_path / filename
        path.write_bytes(content)
        artifact_paths[filename] = path
        artifact_pins[filename] = (hashlib.sha256(content).hexdigest(), len(content))
    weights_bytes = artifact_bytes[model_loader.PYTHIA_160M_WEIGHTS_FILENAME]
    monkeypatch.setattr(model_loader, "PYTHIA_160M_ARTIFACTS", artifact_pins)
    monkeypatch.setattr(
        model_loader,
        "PYTHIA_160M_WEIGHTS_SHA256",
        hashlib.sha256(weights_bytes).hexdigest(),
    )
    monkeypatch.setattr(
        model_loader,
        "PYTHIA_160M_WEIGHTS_BYTES",
        len(weights_bytes),
    )

    class _TokenizerFactory:
        @staticmethod
        def from_pretrained(model_id: str, **kwargs):
            calls.append(("tokenizer", model_id, kwargs))
            return object()

    class _ModelFactory:
        @staticmethod
        def from_pretrained(model_id: str, **kwargs):
            calls.append(("model", model_id, kwargs))
            model._parameter.dtype = kwargs["dtype"]
            return model

    torch_module = ModuleType("torch")
    torch_module.__version__ = "2.13.0+cu126"
    torch_module.cuda = SimpleNamespace(is_available=lambda: cuda_available)

    def _is_bf16_supported(*, including_emulation=True):
        calls.append(
            ("bfloat16_support", str(including_emulation), {"hardware_only": True})
        )
        return cuda_bfloat16_supported

    torch_module.cuda.is_bf16_supported = _is_bf16_supported
    torch_module.cuda.current_device = lambda: 0
    torch_module.cuda.get_device_name = lambda _index: "Synthetic Gate5 GPU"
    torch_module.cuda.get_device_capability = lambda _index: (9, 0)
    torch_module.version = SimpleNamespace(cuda="12.6")
    torch_module.float16 = "torch.float16"
    torch_module.bfloat16 = "torch.bfloat16"
    torch_module.float32 = "torch.float32"
    transformers_module = ModuleType("transformers")
    transformers_module.AutoTokenizer = _TokenizerFactory
    transformers_module.AutoModelForCausalLM = _ModelFactory
    huggingface_hub_module = ModuleType("huggingface_hub")

    def _hf_hub_download(**kwargs):
        calls.append(("artifact", kwargs["repo_id"], kwargs))
        return str(artifact_paths[kwargs["filename"]])

    huggingface_hub_module.hf_hub_download = _hf_hub_download
    monkeypatch.setattr(
        model_loader,
        "_validate_runtime_canary",
        lambda _torch, _model, _tokenizer, *, device: calls.append(
            ("canary", device, {})
        ),
    )
    monkeypatch.setattr(model_loader, "_read_cuda_driver_version", lambda: 12060)
    monkeypatch.setitem(sys.modules, "torch", torch_module)
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)
    monkeypatch.setitem(sys.modules, "huggingface_hub", huggingface_hub_module)
    return calls


def test_warm_load_pins_revision_and_recomputes_weights_identity(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    model = _FakeModel(model_loader.PYTHIA_160M_REVISION)
    calls = _install_fake_runtime(monkeypatch, model, tmp_path)
    model_loader.reset_for_test()
    try:
        loaded = model_loader.warm_load()
    finally:
        model_loader.reset_for_test()

    assert loaded.is_real is True
    assert model.eval_called is True
    assert loaded.manifest.execution_kind == "real_model_weights"
    assert (
        loaded.manifest.intervention_hook_contract.coordinate_space
        == "mlp_intermediate_post_activation"
    )
    assert loaded.manifest.requested_revision == model_loader.PYTHIA_160M_REVISION
    assert loaded.manifest.resolved_revision == model_loader.PYTHIA_160M_REVISION
    assert loaded.manifest.revision_verified is True
    assert loaded.manifest.weights_filename == model_loader.PYTHIA_160M_WEIGHTS_FILENAME
    assert loaded.manifest.weights_sha256 == model_loader.PYTHIA_160M_WEIGHTS_SHA256
    assert loaded.manifest.weights_bytes == model_loader.PYTHIA_160M_WEIGHTS_BYTES
    assert loaded.manifest.weights_hash_verified is True
    assert (
        loaded.manifest.model_identity_status
        == "PINNED_REVISION_AND_WEIGHTS_SHA256"
    )
    loader_calls = [call for call in calls if call[0] in {"tokenizer", "model"}]
    assert [call[2]["revision"] for call in loader_calls] == [
        model_loader.PYTHIA_160M_REVISION,
        model_loader.PYTHIA_160M_REVISION,
    ]
    model_call = next(call for call in calls if call[0] == "model")
    tokenizer_call = next(call for call in calls if call[0] == "tokenizer")
    assert model_call[2]["use_safetensors"] is True
    assert model_call[2]["dtype"] == "torch.float32"
    assert model_call[2]["attn_implementation"] == "eager"
    assert tokenizer_call[2]["local_files_only"] is True
    assert model_call[2]["local_files_only"] is True
    artifact_calls = [call for call in calls if call[0] == "artifact"]
    expected_artifacts = list(model_loader.PYTHIA_160M_ARTIFACTS)
    assert [call[2]["filename"] for call in artifact_calls[:5]] == expected_artifacts
    assert [call[2]["filename"] for call in artifact_calls[5:]] == expected_artifacts
    assert all(call[2]["local_files_only"] is True for call in artifact_calls)
    artifact_positions = [
        index for index, call in enumerate(calls) if call[0] == "artifact"
    ]
    canary_position = calls.index(("canary", "cpu", {}))
    assert max(artifact_positions[:5]) < calls.index(tokenizer_call)
    assert canary_position < min(artifact_positions[5:])
    assert loaded.manifest.runtime_execution is not None
    assert loaded.manifest.runtime_execution.device == "cpu"
    assert loaded.manifest.runtime_execution.dtype == "torch.float32"


def test_cuda_load_uses_bfloat16_eager_attention_and_moves_to_cuda(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    monkeypatch.setenv(model_loader.WORKER_PROFILE_ENV, model_loader.PRODUCTION_PROFILE)
    monkeypatch.setenv(model_loader.TORCH_NATIVE_JIT_DISABLE_ENV, "1")
    monkeypatch.setattr(model_loader, "_validate_production_model_cache", lambda: None)
    model = _FakeModel(model_loader.PYTHIA_160M_REVISION)
    calls = _install_fake_runtime(
        monkeypatch,
        model,
        tmp_path,
        cuda_available=True,
    )
    model_loader.reset_for_test()
    try:
        loaded = model_loader.warm_load()
    finally:
        model_loader.reset_for_test()

    assert loaded.is_real is True
    model_call = next(call for call in calls if call[0] == "model")
    assert model_call[2]["dtype"] == "torch.bfloat16"
    assert model_call[2]["attn_implementation"] == "eager"
    assert model.to_calls == ["cuda"]
    canary_position = calls.index(("canary", "cuda", {}))
    final_artifact_position = max(
        index for index, call in enumerate(calls) if call[0] == "artifact"
    )
    assert canary_position < final_artifact_position
    assert loaded.manifest.runtime_execution is not None
    assert loaded.manifest.runtime_execution.device == "cuda"
    assert loaded.manifest.runtime_execution.dtype == "torch.bfloat16"
    assert loaded.manifest.runtime_execution.torch_native_jit_disabled is True
    assert loaded.manifest.runtime_execution.cuda_bfloat16_supported is True
    assert loaded.manifest.runtime_execution.cuda_driver_version == 12060
    support_calls = [call for call in calls if call[0] == "bfloat16_support"]
    assert len(support_calls) == 2
    assert all(call[1] == "False" for call in support_calls)


def test_cuda_load_fails_closed_when_native_bfloat16_is_unsupported(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    model = _FakeModel(model_loader.PYTHIA_160M_REVISION)
    calls = _install_fake_runtime(
        monkeypatch,
        model,
        tmp_path,
        cuda_available=True,
        cuda_bfloat16_supported=False,
    )
    model_loader.reset_for_test()
    try:
        with pytest.raises(RuntimeError, match="native BF16 support"):
            model_loader.warm_load()
    finally:
        model_loader.reset_for_test()

    assert not any(call[0] == "model" for call in calls)


def test_runtime_canary_failure_fails_closed_to_startup_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    model = _FakeModel(model_loader.PYTHIA_160M_REVISION)
    _install_fake_runtime(monkeypatch, model, tmp_path)
    monkeypatch.setattr(
        model_loader,
        "_validate_runtime_canary",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("synthetic nonfinite runtime canary")
        ),
    )
    model_loader.reset_for_test()
    try:
        with pytest.raises(RuntimeError, match="synthetic nonfinite runtime canary"):
            model_loader.warm_load()
    finally:
        model_loader.reset_for_test()


def test_artifact_identity_change_during_load_fails_closed(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    model = _FakeModel(model_loader.PYTHIA_160M_REVISION)
    _install_fake_runtime(monkeypatch, model, tmp_path)
    validate = model_loader._validated_model_artifacts
    validations = 0

    def _changed_after_load(download):
        nonlocal validations
        observed = validate(download)
        validations += 1
        if validations == 2:
            changed = dict(observed)
            digest, byte_count = changed["config.json"]
            changed["config.json"] = ("0" * len(digest), byte_count)
            return changed
        return observed

    monkeypatch.setattr(model_loader, "_validated_model_artifacts", _changed_after_load)
    model_loader.reset_for_test()
    try:
        with pytest.raises(RuntimeError, match="changed during model loading"):
            model_loader.warm_load()
    finally:
        model_loader.reset_for_test()


def test_cuda_move_failure_fails_closed_to_startup_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    model = _FakeModel(
        model_loader.PYTHIA_160M_REVISION,
        cuda_move_error=RuntimeError("synthetic CUDA transfer failure"),
    )
    _install_fake_runtime(
        monkeypatch,
        model,
        tmp_path,
        cuda_available=True,
    )
    model_loader.reset_for_test()
    try:
        with pytest.raises(RuntimeError, match="synthetic CUDA transfer failure"):
            model_loader.warm_load()
    finally:
        model_loader.reset_for_test()
    assert model.to_calls == ["cuda"]


def test_revision_mismatch_fails_closed_to_startup_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    model = _FakeModel("0" * 40)
    _install_fake_runtime(monkeypatch, model, tmp_path)
    model_loader.reset_for_test()
    try:
        with pytest.raises(RuntimeError, match="does not match"):
            model_loader.warm_load()
    finally:
        model_loader.reset_for_test()


def test_architecture_mismatch_fails_closed_to_startup_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    model = _FakeModel(model_loader.PYTHIA_160M_REVISION, hidden_size=769)
    _install_fake_runtime(monkeypatch, model, tmp_path)
    model_loader.reset_for_test()
    try:
        with pytest.raises(RuntimeError, match="architecture mismatch"):
            model_loader.warm_load()
    finally:
        model_loader.reset_for_test()


def test_weights_digest_mismatch_fails_closed_to_startup_error(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    model = _FakeModel(model_loader.PYTHIA_160M_REVISION)
    _install_fake_runtime(monkeypatch, model, tmp_path)
    monkeypatch.setattr(model_loader, "PYTHIA_160M_WEIGHTS_SHA256", "0" * 64)
    model_loader.reset_for_test()
    try:
        with pytest.raises(RuntimeError, match="model.safetensors SHA-256 does not match"):
            model_loader.warm_load()
    finally:
        model_loader.reset_for_test()


def test_manifest_rejects_real_model_claim_without_revision_attestation() -> None:
    payload = model_loader.PYTHIA_160M_MANIFEST.model_dump()
    payload["is_real_model"] = True
    with pytest.raises(ValidationError, match="verified weights SHA-256"):
        ModelManifest.model_validate(payload)


def test_manifest_rejects_forged_verified_weights_metadata() -> None:
    payload = model_loader.PYTHIA_160M_MANIFEST.model_dump()
    payload.update(
        {
            "resolved_revision": model_loader.PYTHIA_160M_REVISION,
            "revision_verified": True,
            "weights_filename": model_loader.PYTHIA_160M_WEIGHTS_FILENAME,
            "weights_sha256": "not-a-digest",
            "weights_bytes": 1,
            "weights_hash_verified": True,
            "model_identity_status": "PINNED_REVISION_AND_WEIGHTS_SHA256",
            "runtime_execution": {
                "profile": "development",
                "device": "cpu",
                "dtype": "torch.float32",
                "torch_version": "2.13.0+cu126",
            },
        }
    )
    with pytest.raises(ValidationError, match="full lowercase SHA-256"):
        ModelManifest.model_validate(payload)


def test_typed_fixture_cannot_claim_real_model_execution() -> None:
    payload = model_loader.PYTHIA_160M_MANIFEST.model_dump()
    payload.update(
        {
            "is_real_model": True,
            "execution_kind": "typed_test_fixture",
            "resolved_revision": model_loader.PYTHIA_160M_REVISION,
            "revision_verified": True,
            "weights_filename": model_loader.PYTHIA_160M_WEIGHTS_FILENAME,
            "weights_sha256": model_loader.PYTHIA_160M_WEIGHTS_SHA256,
            "weights_bytes": model_loader.PYTHIA_160M_WEIGHTS_BYTES,
            "weights_hash_verified": True,
            "model_identity_status": "PINNED_REVISION_AND_WEIGHTS_SHA256",
            "runtime_execution": {
                "profile": "development",
                "device": "cpu",
                "dtype": "torch.float32",
                "torch_version": "2.13.0+cu126",
            },
        }
    )
    with pytest.raises(ValidationError, match="real_model_weights execution provenance"):
        ModelManifest.model_validate(payload)


def test_loaded_model_property_rejects_forged_model_copy() -> None:
    # model_copy(update=...) is intentionally not trusted: Pydantic documents
    # that update data is not validated.  The runtime property must still fail.
    forged = model_loader.PYTHIA_160M_MANIFEST.model_copy(
        update={"is_real_model": True}
    )
    loaded = model_loader.LoadedModel(
        manifest=forged,
        model=object(),
        tokenizer=object(),
    )
    assert loaded.is_real is False


def test_production_profile_requires_cuda(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    monkeypatch.setenv(model_loader.WORKER_PROFILE_ENV, model_loader.PRODUCTION_PROFILE)
    monkeypatch.setenv(model_loader.TORCH_NATIVE_JIT_DISABLE_ENV, "1")
    model = _FakeModel(model_loader.PYTHIA_160M_REVISION)
    _install_fake_runtime(monkeypatch, model, tmp_path, cuda_available=False)
    monkeypatch.setattr(model_loader, "_validate_production_model_cache", lambda: None)
    model_loader.reset_for_test()
    try:
        with pytest.raises(RuntimeError, match="requires an available CUDA device"):
            model_loader.warm_load()
    finally:
        model_loader.reset_for_test()


def test_production_profile_requires_native_jit_disabled(
    monkeypatch,
) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    monkeypatch.setenv(model_loader.WORKER_PROFILE_ENV, model_loader.PRODUCTION_PROFILE)
    monkeypatch.delenv(model_loader.TORCH_NATIVE_JIT_DISABLE_ENV, raising=False)
    monkeypatch.setattr(model_loader, "_validate_production_model_cache", lambda: None)
    model_loader.reset_for_test()
    try:
        with pytest.raises(RuntimeError, match="TORCH_DISABLE_NATIVE_JIT=1"):
            model_loader.warm_load()
    finally:
        model_loader.reset_for_test()


def test_production_profile_forbids_demo(monkeypatch) -> None:
    monkeypatch.setenv("LIVE_TRACE_DEMO_MODE", "1")
    monkeypatch.setenv(model_loader.WORKER_PROFILE_ENV, model_loader.PRODUCTION_PROFILE)
    model_loader.reset_for_test()
    try:
        with pytest.raises(RuntimeError, match="forbids demo mode"):
            model_loader.warm_load()
    finally:
        model_loader.reset_for_test()


def test_production_profile_rejects_redirected_or_writable_model_cache(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HF_HOME", str(tmp_path / "redirected"))
    with pytest.raises(RuntimeError, match="image-bound Hugging Face cache"):
        model_loader._validate_production_model_cache()

    monkeypatch.setattr(model_loader, "PRODUCTION_HF_HOME", str(tmp_path))
    monkeypatch.setenv("HF_HOME", str(tmp_path))
    monkeypatch.setattr(model_loader.os, "access", lambda *_args: True)
    with pytest.raises(RuntimeError, match="must be non-writable"):
        model_loader._validate_production_model_cache()

    monkeypatch.setattr(model_loader.os, "access", lambda *_args: False)
    model_loader._validate_production_model_cache()
