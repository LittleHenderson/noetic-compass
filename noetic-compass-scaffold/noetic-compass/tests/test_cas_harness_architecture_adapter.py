"""Unit tests for the frontier architecture-adapter gate (frontier run-gate 6).

These exercise the honesty contract at the service layer, mirroring the
provenance gate's declared-vs-verified split:

* A missing declaration, a model_type with no probe adapter, or an
  unrecognizable architecture class is ``ARCHITECTURE_ADAPTER_UNSUPPORTED`` and
  the frontier validator raises (callers turn that into HTTP 422).
* A declared architecture whose ``model_type`` (or an inferred architecture
  class) resolves to one of the worker's four hookable decoder stacks is
  ``ARCHITECTURE_ADAPTER_AVAILABLE`` -- enough to create a run, never a verdict.
* ``ARCHITECTURE_ADAPTER_VERIFIED`` is reserved for the probe worker, the only
  place the real model is loaded and its layer stack actually located, so it is
  never produced at this service tier.

The registry is anchored to what the worker can actually do: it mirrors the four
hardcoded attribute paths in ``locate_transformer_layers``. An architecture
mapping to none of them is refused because the worker would raise rather than
capture activations.
"""

from __future__ import annotations

import pytest

from api.services.cas_harness_architecture_adapter import (
    SUPPORTED_LAYER_STACK_PATHS,
    ModelArchitectureDeclaration,
    find_adapter_for_model_type,
    normalize_model_type,
    summarize_architecture_adapter,
    supported_model_types,
    validate_frontier_architecture,
)


# ---------------------------------------------------------------------------
# No declaration / unresolvable -> UNSUPPORTED
# ---------------------------------------------------------------------------


def test_missing_declaration_is_unsupported():
    summary = summarize_architecture_adapter(declaration=None)

    assert summary.status == "ARCHITECTURE_ADAPTER_UNSUPPORTED"
    assert summary.adapter_available is False
    assert summary.accepted is False
    assert summary.resolved_model_type is None
    assert summary.reasons  # an honest reason is always attached


def test_declaration_with_neither_model_type_nor_class_is_unsupported():
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration()
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_UNSUPPORTED"
    assert summary.resolved_model_type is None
    assert summary.adapter_available is False


def test_unknown_model_type_is_unsupported():
    # mamba is a state-space model: the worker cannot locate a transformer
    # decoder stack at any of its four hardcoded paths, so it would raise.
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(model_type="mamba")
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_UNSUPPORTED"
    assert summary.resolved_model_type == "mamba"
    assert summary.adapter_family is None
    assert summary.adapter_available is False
    # The honest notice cites the actual mechanism (the four hookable stacks).
    assert "model.layers" in summary.notice


def test_unknown_architecture_class_is_unsupported():
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(
            architectures=("MambaForCausalLM",)
        )
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_UNSUPPORTED"
    assert summary.resolved_model_type is None


# ---------------------------------------------------------------------------
# Supported model_types -> AVAILABLE (never VERIFIED at this tier)
# ---------------------------------------------------------------------------


def test_llama_resolves_to_llama_like_adapter_available():
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(model_type="llama")
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert summary.accepted is True
    assert summary.resolved_model_type == "llama"
    assert summary.adapter_family == "llama_like"
    assert summary.layer_stack_attr == "model.layers"
    assert summary.hook_submodule == "mlp"
    assert summary.adapter_available is True
    # A declared-only architecture is structurally supported, NOT empirically
    # validated -- a frontier run is EXPERIMENTAL_NOT_VALIDATED by definition.
    assert summary.adapter_validation == "structurally_supported"
    # Never claim VERIFIED at the service tier.
    assert summary.status != "ARCHITECTURE_ADAPTER_VERIFIED"


def test_qwen2_resolves_to_llama_like_adapter_available():
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(model_type="qwen2")
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert summary.adapter_family == "llama_like"
    assert summary.resolved_model_type == "qwen2"


def test_gpt_neox_is_empirically_validated_reference_family():
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(model_type="gpt_neox")
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert summary.adapter_family == "gpt_neox"
    assert summary.layer_stack_attr == "gpt_neox.layers"
    # GPT-NeoX / Pythia is the family the readout was reproduced end-to-end on.
    assert summary.adapter_validation == "empirically_validated"


def test_gpt2_resolves_to_gpt2_like_transformer_h_stack():
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(model_type="gpt2")
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert summary.adapter_family == "gpt2_like"
    assert summary.layer_stack_attr == "transformer.h"


def test_mpt_resolves_to_mpt_like_blocks_stack_with_block_hook():
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(model_type="mpt")
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert summary.adapter_family == "mpt_like"
    assert summary.layer_stack_attr == "transformer.blocks"
    # MPT exposes `.ffn` not `.mlp`, so the worker's hook falls back to the block.
    assert summary.hook_submodule == "block"


# ---------------------------------------------------------------------------
# Architecture-class fallback + model_type precedence
# ---------------------------------------------------------------------------


def test_architecture_class_is_used_when_model_type_absent():
    # A caller may pass only config.json's architectures (no model_type). The
    # gate strips the ForCausalLM suffix and resolves the family.
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(
            architectures=("LlamaForCausalLM",)
        )
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert summary.resolved_model_type == "llama"
    assert summary.adapter_family == "llama_like"


def test_empty_model_type_falls_back_to_architecture_class():
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(
            model_type="", architectures=("MistralForCausalLM",)
        )
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert summary.resolved_model_type == "mistral"


def test_explicit_model_type_takes_precedence_over_architecture_class():
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(
            model_type="llama", architectures=("MambaForCausalLM",)
        )
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert summary.resolved_model_type == "llama"


def test_declared_dimensions_are_recorded_for_traceability():
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(
            model_type="llama",
            num_hidden_layers=126,
            hidden_size=16384,
            num_attention_heads=128,
        )
    )

    assert summary.declared_num_hidden_layers == 126
    assert summary.declared_hidden_size == 16384
    assert summary.declared_num_attention_heads == 128


def test_summary_to_dict_round_trips_keys():
    summary = summarize_architecture_adapter(
        declaration=ModelArchitectureDeclaration(model_type="llama")
    )
    data = summary.to_dict()

    assert data["status"] == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert data["resolved_model_type"] == "llama"
    assert data["adapter_family"] == "llama_like"
    assert data["adapter_available"] is True
    assert isinstance(data["declared_architectures"], list)
    assert isinstance(data["reasons"], list)


# ---------------------------------------------------------------------------
# Frontier validator: raises on UNSUPPORTED, returns on supported
# ---------------------------------------------------------------------------


def test_validate_frontier_architecture_raises_without_declaration():
    with pytest.raises(ValueError) as exc:
        validate_frontier_architecture(declaration=None)

    assert "unsupported model architecture" in str(exc.value)


def test_validate_frontier_architecture_raises_for_unsupported_model_type():
    with pytest.raises(ValueError) as exc:
        validate_frontier_architecture(
            declaration=ModelArchitectureDeclaration(model_type="rwkv")
        )

    assert "frontier-scale run refused" in str(exc.value)


def test_validate_frontier_architecture_returns_summary_for_supported():
    summary = validate_frontier_architecture(
        declaration=ModelArchitectureDeclaration(model_type="llama")
    )

    assert summary.status == "ARCHITECTURE_ADAPTER_AVAILABLE"
    assert summary.adapter_available is True


# ---------------------------------------------------------------------------
# Helper-function behaviour (normalization, registry lookup, coverage)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("GPTNeoX", "gpt_neox"),
        ("gptneox", "gpt_neox"),
        ("qwen", "qwen2"),
        ("DeepSeek-V2", "deepseek_v2"),
        ("Command-R", "command_r"),
        ("commandr", "command_r"),
        ("  Llama  ", "llama"),
    ],
)
def test_normalize_model_type_applies_aliases_and_separators(raw, expected):
    assert normalize_model_type(raw) == expected


def test_find_adapter_for_model_type_uses_normalization():
    # "qwen" is an alias for "qwen2", which lives in the llama_like family.
    profile = find_adapter_for_model_type("qwen")
    assert profile is not None
    assert profile.family == "llama_like"

    assert find_adapter_for_model_type("totally-made-up-arch") is None


def test_supported_model_types_covers_the_four_stacks():
    types = supported_model_types()

    # 2 (gpt_neox) + 22 (llama_like) + 6 (gpt2_like) + 1 (mpt_like) = 31.
    assert len(types) == 31
    assert len(SUPPORTED_LAYER_STACK_PATHS) == 4
    # Spot-check one representative model_type from each of the four stacks.
    for expected in ("gpt_neox", "llama", "gpt2", "mpt"):
        assert expected in types
