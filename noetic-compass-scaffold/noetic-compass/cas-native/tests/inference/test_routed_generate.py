"""Tests for the unified routed_generate entry point.

These tests exercise the orchestration logic without loading a real
checkpoint. ``generate_reply`` is monkeypatched so we can assert that
``routed_generate`` correctly:
  - calls route_by_compilability on the source
  - selects the task-aware token budget
  - constructs the prompt via build_prompt_from_routing
  - passes use_cas_prefix=True by default (the B-4 fix)
  - threads stopped_on_eos into postprocess
  - assembles a RoutedGenerationResult that exposes the expected fields
"""

from __future__ import annotations

import pytest

from cas_native.inference import routed_generate as rg_module
from cas_native.inference.routed_generate import (
    RoutedGenerationResult,
    routed_generate,
)


def _make_fake_generate_reply(
    *, reply_text: str = "default reply", n_steps: int = 5,
    stopped_on_eos: bool = True,
):
    """Build a stubbed generate_reply that records how it was called."""
    captured: dict[str, object] = {}

    def fake(*, model, tokenizer, prompt_text, cas_expression, register,
             max_new_tokens, sampling, temperature, top_p, use_cas_prefix,
             device, seed_decoder_text=None, prepend_cas_prefix_token_id=None):
        captured["prompt_text"] = prompt_text
        captured["cas_expression"] = cas_expression
        captured["max_new_tokens"] = max_new_tokens
        captured["use_cas_prefix"] = use_cas_prefix
        captured["sampling"] = sampling
        captured["register"] = register
        captured["seed_decoder_text"] = seed_decoder_text
        captured["prepend_cas_prefix_token_id"] = prepend_cas_prefix_token_id
        return {
            "reply_text": reply_text,
            "stopped_on_eos": stopped_on_eos,
            "n_steps": n_steps,
            "seed_token_count": 0,
            "config": {"sampling": sampling, "temperature": temperature, "top_p": top_p},
            "token_ids": [],
        }

    return fake, captured


# ---------------------------------------------------------------------------
# Routing → prompt → generation → postprocess composition
# ---------------------------------------------------------------------------

def test_routes_valid_cas_to_cas_to_english_and_uses_describe_wrapper(monkeypatch):
    fake, captured = _make_fake_generate_reply(
        reply_text="A practiced rhythm in cognitive thinking.",
    )
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    result = routed_generate(
        model=None, tokenizer=None,
        source_cas="^7^C_{F2}|T",
        sampling="greedy",
    )

    assert isinstance(result, RoutedGenerationResult)
    assert result.task_type == "cas_to_english"
    assert result.routing.compiled is True
    assert "Describe the following CAS expression" in captured["prompt_text"]
    assert "^7^C_{F2}|T" in captured["prompt_text"]


def test_routes_invalid_cas_to_explanation_with_error_class(monkeypatch):
    fake, captured = _make_fake_generate_reply(
        reply_text="The expression sets up a starting point and tries to hand off to a destination that was never defined.",
    )
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    invalid = "let X = ^0^P; X -> Y"  # Y undefined
    result = routed_generate(
        model=None, tokenizer=None, source_cas=invalid, sampling="greedy",
    )

    assert result.task_type == "invalid_to_explanation"
    assert result.routing.compiled is False
    assert "Explain in plain English why" in captured["prompt_text"]
    assert "Invalid CAS expression (error class:" in captured["prompt_text"]


# ---------------------------------------------------------------------------
# Task-aware max_new_tokens budgets
# ---------------------------------------------------------------------------

def test_default_budget_for_cas_to_english_is_150(monkeypatch):
    fake, captured = _make_fake_generate_reply()
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    routed_generate(
        model=None, tokenizer=None,
        source_cas="^4^P|A",  # valid → cas_to_english
        sampling="greedy",
    )
    assert captured["max_new_tokens"] == 150


def test_default_budget_for_invalid_to_explanation_is_250(monkeypatch):
    fake, captured = _make_fake_generate_reply()
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    routed_generate(
        model=None, tokenizer=None,
        source_cas="let X = ^0^P; X -> Y",  # invalid → explanation
        sampling="greedy",
    )
    assert captured["max_new_tokens"] == 250


def test_explicit_max_new_tokens_overrides_task_default(monkeypatch):
    fake, captured = _make_fake_generate_reply()
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    routed_generate(
        model=None, tokenizer=None,
        source_cas="^4^P|A",
        max_new_tokens=80,
        sampling="greedy",
    )
    assert captured["max_new_tokens"] == 80


# ---------------------------------------------------------------------------
# Truncation flagging passes through to RoutedGenerationResult.truncated
# ---------------------------------------------------------------------------

def test_truncation_flag_propagates_when_eos_not_reached(monkeypatch):
    fake, _ = _make_fake_generate_reply(
        reply_text="This sentence will not finish because we hit the cap and",
        stopped_on_eos=False,
    )
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    result = routed_generate(
        model=None, tokenizer=None,
        source_cas="^4^P|A",
        sampling="greedy",
    )
    assert result.truncated is True
    assert result.quality_passed is False
    assert "truncated_at_max_tokens" in result.postprocess_result.quality_failures


def test_no_truncation_flag_when_eos_reached(monkeypatch):
    fake, _ = _make_fake_generate_reply(
        reply_text="When something struck a chord in a principled way.",
        stopped_on_eos=True,
    )
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    result = routed_generate(
        model=None, tokenizer=None,
        source_cas="^4^P|A",
        sampling="greedy",
    )
    assert result.truncated is False


# ---------------------------------------------------------------------------
# B-4 fix default: use_cas_prefix=True
# ---------------------------------------------------------------------------

def test_use_cas_prefix_defaults_to_true(monkeypatch):
    fake, captured = _make_fake_generate_reply()
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    routed_generate(
        model=None, tokenizer=None,
        source_cas="^4^P|A",
        sampling="greedy",
    )
    assert captured["use_cas_prefix"] is True


def test_use_cas_prefix_can_be_disabled_for_v0_checkpoints(monkeypatch):
    fake, captured = _make_fake_generate_reply()
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    routed_generate(
        model=None, tokenizer=None,
        source_cas="^4^P|A",
        sampling="greedy",
        use_cas_prefix=False,
    )
    assert captured["use_cas_prefix"] is False


# ---------------------------------------------------------------------------
# Identifier repair runs by default
# ---------------------------------------------------------------------------

def test_repair_recovers_omega_when_apply_repair_default_true(monkeypatch):
    fake, _ = _make_fake_generate_reply(
        reply_text="To produce the outcome called wrong_name, combine 1 of stuff.",
        stopped_on_eos=True,
    )
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    result = routed_generate(
        model=None, tokenizer=None,
        source_cas="Θ(Ω_decision_60) = 1*^3^P → Ω_decision_60",
        sampling="greedy",
    )
    assert result.postprocess_result.repair_applied is True
    assert "decision_60" in result.final_text
    assert "wrong_name" not in result.final_text
    # Raw still shows the hallucinated name.
    assert "wrong_name" in result.raw_text


def test_repair_can_be_disabled(monkeypatch):
    fake, _ = _make_fake_generate_reply(
        reply_text="To produce the outcome called wrong_name, combine 1 of stuff.",
        stopped_on_eos=True,
    )
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    result = routed_generate(
        model=None, tokenizer=None,
        source_cas="Θ(Ω_decision_60) = 1*^3^P → Ω_decision_60",
        apply_repair=False,
        sampling="greedy",
    )
    assert result.postprocess_result.repair_applied is False
    assert result.final_text == result.raw_text
    assert "wrong_name" in result.final_text


# ---------------------------------------------------------------------------
# Result serialization for trace logging
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Decoder-seeding for valid rpm_chain silhouette (diagnostic patch A)
# ---------------------------------------------------------------------------

def test_seed_rpm_silhouette_off_by_default(monkeypatch):
    fake, captured = _make_fake_generate_reply()
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    result = routed_generate(
        model=None, tokenizer=None,
        source_cas="let stageA0_3_0234 = ^0^P; stageA0_3_0234 -> stageW3_3_0234",
        sampling="greedy",
    )
    # Default: no seeding fires even when source matches the let pattern.
    assert result.seed_decoder_text is None
    # Fake generate_reply is called without a seed text either.
    # (We don't capture seed_decoder_text in the fake, but we can assert
    # it via the result.)


def test_seed_rpm_silhouette_fires_for_valid_let_binding(monkeypatch):
    fake, captured = _make_fake_generate_reply(
        reply_text="Let stageA0_3_0234 name a foundational thought, ...",
    )
    # Need to capture the seed_decoder_text passed through.
    captured_seed: dict = {}

    def fake_with_seed(*, seed_decoder_text=None, **kwargs):
        captured_seed["seed"] = seed_decoder_text
        return fake(**kwargs)

    monkeypatch.setattr(rg_module, "generate_reply", fake_with_seed)

    cas = (
        "let stageA0_3_0234 = ^0^P; let stageD3_3_0234 = ^9^P_{F3}; "
        "stageA0_3_0234 -> stageD3_3_0234"
    )
    result = routed_generate(
        model=None, tokenizer=None,
        source_cas=cas, sampling="greedy",
        seed_rpm_silhouette=True,
    )

    assert result.routing.task_type == "cas_to_english"
    assert result.seed_decoder_text == "Let stageA0_3_0234 name "
    assert captured_seed["seed"] == "Let stageA0_3_0234 name "


def test_seed_rpm_silhouette_does_not_fire_on_non_let_cas(monkeypatch):
    fake, _ = _make_fake_generate_reply()
    captured_seed: dict = {}

    def fake_with_seed(*, seed_decoder_text=None, **kwargs):
        captured_seed["seed"] = seed_decoder_text
        return fake(**kwargs)

    monkeypatch.setattr(rg_module, "generate_reply", fake_with_seed)

    result = routed_generate(
        model=None, tokenizer=None,
        source_cas="^4^P|A",  # state literal, not a let-binding
        sampling="greedy",
        seed_rpm_silhouette=True,
    )
    # Even with the flag on, non-let sources don't get seeded.
    assert result.seed_decoder_text is None
    assert captured_seed["seed"] is None


def test_seed_rpm_silhouette_does_not_fire_on_invalid_routing(monkeypatch):
    """If the compiler routes to invalid_to_explanation, the seed must
    NOT fire — that path doesn't want a let-binding silhouette."""
    fake, _ = _make_fake_generate_reply()
    captured_seed: dict = {}

    def fake_with_seed(*, seed_decoder_text=None, **kwargs):
        captured_seed["seed"] = seed_decoder_text
        return fake(**kwargs)

    monkeypatch.setattr(rg_module, "generate_reply", fake_with_seed)

    # Invalid: undefined target var
    cas = "let X = ^0^P; X -> Y"
    result = routed_generate(
        model=None, tokenizer=None,
        source_cas=cas, sampling="greedy",
        seed_rpm_silhouette=True,
    )
    assert result.routing.task_type == "invalid_to_explanation"
    assert result.seed_decoder_text is None
    assert captured_seed["seed"] is None


def test_seed_rpm_silhouette_extracts_first_var_when_multiple_lets(monkeypatch):
    fake, _ = _make_fake_generate_reply()
    captured_seed: dict = {}

    def fake_with_seed(*, seed_decoder_text=None, **kwargs):
        captured_seed["seed"] = seed_decoder_text
        return fake(**kwargs)

    monkeypatch.setattr(rg_module, "generate_reply", fake_with_seed)

    # Use a CAS that compiles cleanly: P -> P descent + arrow within P.
    # CAS Domain Descent rule (P >= C >= E >= O) means C cannot descend
    # to P, so a chain that mixes domains needs to be top-down only.
    cas = (
        "let stageA0_5_0296 = ^0^P; let stageD5_5_0296 = ^7^P_{F5}; "
        "let stageW5_5_0296 = ^7^P_{F5}; stageA0_5_0296 -> stageD5_5_0296"
    )
    routed_generate(
        model=None, tokenizer=None,
        source_cas=cas, sampling="greedy",
        seed_rpm_silhouette=True,
    )
    # First let-binding wins.
    assert captured_seed["seed"] == "Let stageA0_5_0296 name "


# ---------------------------------------------------------------------------
# Option C v1c: prepend_task_token flag
# ---------------------------------------------------------------------------

class _FakeTaskTokenIds:
    valid = 38683
    invalid = 38684

    def for_task_type(self, task_type: str) -> int:
        if task_type == "cas_to_english":
            return self.valid
        if task_type == "invalid_to_explanation":
            return self.invalid
        raise ValueError(f"unknown task_type {task_type!r}")


class _FakeTaskTokenizer:
    """Minimal stub that satisfies the .task_token_ids contract for
    routed_generate. Doesn't need to encode anything because
    generate_reply is monkeypatched."""
    task_token_ids = _FakeTaskTokenIds()


def test_prepend_task_token_passes_VALID_id_for_cas_to_english(monkeypatch):
    fake, captured = _make_fake_generate_reply()
    monkeypatch.setattr(rg_module, "generate_reply", fake)
    routed_generate(
        model=None, tokenizer=_FakeTaskTokenizer(),
        source_cas="^4^P|A",  # valid -> cas_to_english
        sampling="greedy",
        prepend_task_token=True,
    )
    assert captured["prepend_cas_prefix_token_id"] == 38683


def test_prepend_task_token_passes_INVALID_id_for_invalid(monkeypatch):
    fake, captured = _make_fake_generate_reply()
    monkeypatch.setattr(rg_module, "generate_reply", fake)
    routed_generate(
        model=None, tokenizer=_FakeTaskTokenizer(),
        source_cas="let X = ^0^P; X -> Y",  # undef Y -> invalid
        sampling="greedy",
        prepend_task_token=True,
    )
    assert captured["prepend_cas_prefix_token_id"] == 38684


def test_prepend_task_token_default_false_passes_None(monkeypatch):
    fake, captured = _make_fake_generate_reply()
    monkeypatch.setattr(rg_module, "generate_reply", fake)
    routed_generate(
        model=None, tokenizer=_FakeTaskTokenizer(),
        source_cas="^4^P|A",
        sampling="greedy",
        # prepend_task_token defaults to False
    )
    assert captured["prepend_cas_prefix_token_id"] is None


def test_prepend_task_token_raises_when_tokenizer_lacks_task_token_ids(monkeypatch):
    fake, _ = _make_fake_generate_reply()
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    class _PlainTokenizer:
        pass

    with pytest.raises(RuntimeError, match="task_token_ids"):
        routed_generate(
            model=None, tokenizer=_PlainTokenizer(),
            source_cas="^4^P|A",
            sampling="greedy",
            prepend_task_token=True,
        )


def test_result_to_dict_serializes_audit_friendly(monkeypatch):
    fake, _ = _make_fake_generate_reply()
    monkeypatch.setattr(rg_module, "generate_reply", fake)

    result = routed_generate(
        model=None, tokenizer=None,
        source_cas="^4^P|A",
        sampling="greedy",
    )
    d = result.to_dict()
    assert "final_text" in d
    assert "raw_text" in d
    assert "routing" in d
    assert "prompt_used" in d
    assert "postprocess" in d
    assert "generation_metadata" in d
    assert d["routing"]["task_type"] == "cas_to_english"
    assert d["generation_metadata"]["max_new_tokens"] == 150
