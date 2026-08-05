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
    def __init__(self, revision: str, *, hidden_size: int = 768) -> None:
        self.config = SimpleNamespace(
            _commit_hash=revision,
            hidden_size=hidden_size,
            intermediate_size=3072,
            num_hidden_layers=12,
            num_attention_heads=12,
        )
        self.eval_called = False

    def eval(self) -> None:
        self.eval_called = True


def _install_fake_runtime(
    monkeypatch,
    model: _FakeModel,
    tmp_path: Path,
) -> list[tuple[str, str, dict]]:
    calls: list[tuple[str, str, dict]] = []
    weights_bytes = b"typed-pythia-weights-fixture"
    weights_path = tmp_path / model_loader.PYTHIA_160M_WEIGHTS_FILENAME
    weights_path.write_bytes(weights_bytes)
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
            return model

    torch_module = ModuleType("torch")
    torch_module.cuda = SimpleNamespace(is_available=lambda: False)
    transformers_module = ModuleType("transformers")
    transformers_module.AutoTokenizer = _TokenizerFactory
    transformers_module.AutoModelForCausalLM = _ModelFactory
    huggingface_hub_module = ModuleType("huggingface_hub")

    def _hf_hub_download(**kwargs):
        calls.append(("weights", kwargs["repo_id"], kwargs))
        return str(weights_path)

    huggingface_hub_module.hf_hub_download = _hf_hub_download
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
    assert [call[2]["revision"] for call in calls[:2]] == [
        model_loader.PYTHIA_160M_REVISION,
        model_loader.PYTHIA_160M_REVISION,
    ]
    assert calls[1][2]["use_safetensors"] is True
    assert calls[2][0] == "weights"
    assert calls[2][2]["local_files_only"] is True


def test_revision_mismatch_fails_closed_to_demo(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    model = _FakeModel("0" * 40)
    _install_fake_runtime(monkeypatch, model, tmp_path)
    model_loader.reset_for_test()
    try:
        loaded = model_loader.warm_load()
    finally:
        model_loader.reset_for_test()

    assert loaded.is_real is False
    assert loaded.manifest.resolved_revision is None
    assert loaded.manifest.revision_verified is False
    assert loaded.manifest.model_identity_status == "DEMO_OR_UNLOADED"
    assert "does not match" in (loaded.load_error or "")


def test_architecture_mismatch_fails_closed_to_demo(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    model = _FakeModel(model_loader.PYTHIA_160M_REVISION, hidden_size=769)
    _install_fake_runtime(monkeypatch, model, tmp_path)
    model_loader.reset_for_test()
    try:
        loaded = model_loader.warm_load()
    finally:
        model_loader.reset_for_test()

    assert loaded.is_real is False
    assert loaded.manifest.revision_verified is False
    assert "architecture mismatch" in (loaded.load_error or "")


def test_weights_digest_mismatch_fails_closed_to_demo(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("LIVE_TRACE_DEMO_MODE", raising=False)
    model = _FakeModel(model_loader.PYTHIA_160M_REVISION)
    _install_fake_runtime(monkeypatch, model, tmp_path)
    monkeypatch.setattr(model_loader, "PYTHIA_160M_WEIGHTS_SHA256", "0" * 64)
    model_loader.reset_for_test()
    try:
        loaded = model_loader.warm_load()
    finally:
        model_loader.reset_for_test()

    assert loaded.is_real is False
    assert loaded.manifest.weights_hash_verified is False
    assert loaded.manifest.model_identity_status == "DEMO_OR_UNLOADED"
    assert "weights SHA-256 does not match" in (loaded.load_error or "")


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
