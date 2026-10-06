"""Additive model-binding selection.

These tests pin the property that makes the second binding safe: selecting no
model must behave exactly like the historical pythia-only loader, and an
unrecognized selection must fail closed rather than fall back to a model the
caller did not ask for.
"""

from __future__ import annotations

import pytest

from app.runtime import model_loader


def test_unset_selection_is_the_pythia_pin(monkeypatch) -> None:
    monkeypatch.delenv(model_loader.ACTIVE_MODEL_ENV, raising=False)
    binding = model_loader.active_model_binding()
    assert binding.key == model_loader.PYTHIA_160M_BINDING_KEY
    assert binding.model_id == model_loader.PYTHIA_160M_MODEL_ID
    assert binding.revision == model_loader.PYTHIA_160M_REVISION
    assert binding.weights_filename == model_loader.PYTHIA_160M_WEIGHTS_FILENAME
    assert binding.weights_sha256 == model_loader.PYTHIA_160M_WEIGHTS_SHA256
    assert binding.weights_bytes == model_loader.PYTHIA_160M_WEIGHTS_BYTES
    assert binding.arch is model_loader._PYTHIA_ARCH


def test_blank_selection_is_the_pythia_pin(monkeypatch) -> None:
    monkeypatch.setenv(model_loader.ACTIVE_MODEL_ENV, "   ")
    assert (
        model_loader.active_model_binding().key
        == model_loader.PYTHIA_160M_BINDING_KEY
    )


def test_pythia_bootstrap_manifest_is_the_historical_object(monkeypatch) -> None:
    """Existing receipts must stay byte-identical, not merely equivalent."""

    monkeypatch.delenv(model_loader.ACTIVE_MODEL_ENV, raising=False)
    assert model_loader.bootstrap_manifest() is model_loader.PYTHIA_160M_MANIFEST


def test_binding_is_rebuilt_per_call_so_pins_stay_substitutable(monkeypatch) -> None:
    """An import-time snapshot would silently ignore a substituted pin.

    The fail-closed identity tests substitute these constants at runtime. If a
    binding captured them at import, those tests would assert nothing.
    """

    monkeypatch.delenv(model_loader.ACTIVE_MODEL_ENV, raising=False)
    monkeypatch.setattr(model_loader, "PYTHIA_160M_WEIGHTS_SHA256", "0" * 64)
    assert model_loader.active_model_binding().weights_sha256 == "0" * 64


def test_qwen_selection_reports_its_own_pinned_identity(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV, model_loader.QWEN_05B_INSTRUCT_BINDING_KEY
    )
    binding = model_loader.active_model_binding()
    assert binding.model_id == "Qwen/Qwen2.5-0.5B-Instruct"
    assert binding.revision == "7ae557604adf67be50417f59c2c2f167def9a775"
    assert binding.weights_bytes == 988_097_824
    assert binding.arch.n_layers == 24
    assert binding.arch.hidden_size == 896
    assert binding.arch.mlp_intermediate_dim == 4864
    assert binding.arch.n_heads == 14


def test_qwen_selection_is_case_insensitive(monkeypatch) -> None:
    monkeypatch.setenv(model_loader.ACTIVE_MODEL_ENV, "QWEN2.5-0.5B-Instruct")
    assert (
        model_loader.active_model_binding().model_id == "Qwen/Qwen2.5-0.5B-Instruct"
    )


def test_qwen_bootstrap_manifest_does_not_claim_a_real_load(monkeypatch) -> None:
    monkeypatch.setenv(
        model_loader.ACTIVE_MODEL_ENV, model_loader.QWEN_05B_INSTRUCT_BINDING_KEY
    )
    manifest = model_loader.bootstrap_manifest()
    assert manifest.model_id == "Qwen/Qwen2.5-0.5B-Instruct"
    assert manifest.tokenizer_id == "Qwen/Qwen2.5-0.5B-Instruct"
    assert manifest.model_arch.mlp_intermediate_dim == 4864
    assert manifest.is_real_model is False
    assert manifest.execution_kind == "demo_schema_only"
    assert manifest.model_identity_status == "DEMO_OR_UNLOADED"


def test_unknown_selection_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv(model_loader.ACTIVE_MODEL_ENV, "gpt-4")
    with pytest.raises(RuntimeError, match="is not a pinned model binding"):
        model_loader.active_model_binding()


def test_pinned_pythia_identity_is_unchanged_by_the_addition() -> None:
    """The second binding must not relax the original pin."""

    assert model_loader.PYTHIA_160M_MODEL_ID == "EleutherAI/pythia-160m"
    assert (
        model_loader.PYTHIA_160M_REVISION
        == "50f5173d932e8e61f858120bcb800b97af589f46"
    )
    assert model_loader.PYTHIA_160M_WEIGHTS_BYTES == 374_998_696
    assert model_loader.DEFAULT_MODEL_KEY == model_loader.PYTHIA_160M_BINDING_KEY
