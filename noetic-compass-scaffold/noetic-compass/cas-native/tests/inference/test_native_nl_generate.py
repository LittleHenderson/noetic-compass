"""Tests for ``generate_reply`` — autoregressive sampling helper."""

from __future__ import annotations

import pytest
import torch

from cas_native.inference.native_nl_generate import (
    DEFAULT_REGISTER_TO_ID,
    GenerateConfig,
    generate_reply,
)
from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel
from cas_native.model.nl_generation_head import (
    NLGenerationHead,
    NLGenerationHeadConfig,
)
from cas_native.training.tokenizer import HybridCASTokenizer


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _make_tokenizer() -> HybridCASTokenizer:
    """Tiny frozen tokenizer with enough English fragments to round-trip."""
    tok = HybridCASTokenizer()
    for w in [
        "hello", "world", "today", "the", "feel", "I", "drawn",
        "to", "this", "idea", "and", "it", "speaks", "me", "back",
    ]:
        tok.fit_text(w)
    tok.freeze()
    return tok


def _make_model_with_head(tokenizer: HybridCASTokenizer) -> CASNativeModel:
    """Tiny CASNativeModel + NLGenerationHead at d_model=32 for CPU smoke."""
    d_model = 32
    enc_cfg = CASNativeConfig(
        d_model=d_model,
        n_layers=1,
        n_heads=4,
        vocab_size=tokenizer.vocab_size,
        max_seq_len=128,
        fractal_depth=1,
        num_ifs_maps=1,
    )
    encoder = CASNativeModel(enc_cfg)
    head_cfg = NLGenerationHeadConfig(
        vocab_size=tokenizer.vocab_size,
        d_model=d_model,
        n_heads=4,
        n_layers=1,
        ffn_dim=64,
        bottleneck_dim=16,
        soft_prefix_length=2,
        max_len=128,
    )
    head = NLGenerationHead(head_cfg)
    encoder.attach_nl_gen_head(head)
    return encoder


# ---------------------------------------------------------------------------
# 1. Basic invocation — end-to-end with random-init weights
# ---------------------------------------------------------------------------

def test_generate_reply_basic_smoke():
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    out = generate_reply(
        model=model,
        tokenizer=tok,
        prompt_text="hello world",
        register="T",
        max_new_tokens=15,
        sampling="greedy",
    )
    assert isinstance(out["reply_text"], str)
    assert isinstance(out["token_ids"], list)
    assert 1 <= out["n_steps"] <= 15
    assert out["prompt_text"] == "hello world"
    assert out["config"]["sampling"] == "greedy"
    assert out["config"]["register"] == "T"
    assert out["config"]["register_id"] == 0  # T -> 0
    assert out["trace"] is None  # return_trace=False default


# ---------------------------------------------------------------------------
# 2. Greedy is deterministic — same seed should produce same output
# ---------------------------------------------------------------------------

def test_greedy_sampling_is_deterministic():
    tok = _make_tokenizer()
    torch.manual_seed(123)
    model_a = _make_model_with_head(tok)
    torch.manual_seed(123)
    model_b = _make_model_with_head(tok)

    a = generate_reply(
        model=model_a, tokenizer=tok, prompt_text="hello",
        max_new_tokens=10, sampling="greedy",
    )
    b = generate_reply(
        model=model_b, tokenizer=tok, prompt_text="hello",
        max_new_tokens=10, sampling="greedy",
    )
    # Two identically-initialized models produce identical greedy outputs
    assert a["token_ids"] == b["token_ids"]


# ---------------------------------------------------------------------------
# 3. Disallowed tokens never appear in output
# ---------------------------------------------------------------------------

def test_disallowed_tokens_never_in_output():
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    out = generate_reply(
        model=model, tokenizer=tok, prompt_text="hello world",
        max_new_tokens=20, sampling="greedy",
    )
    # PAD, UNK, BOS must not appear in the output
    assert tok.PAD_ID not in out["token_ids"]
    assert tok.UNK_ID not in out["token_ids"]
    assert tok.BOS_ID not in out["token_ids"]


# ---------------------------------------------------------------------------
# 4. EOS terminates generation; stopped_on_eos flag set correctly
# ---------------------------------------------------------------------------

def _bias_lm_head_toward(model, vocab_size: int, target_id: int, magnitude: float = 10.0) -> None:
    """Replace lm_head with a biased Linear that forces target_id as
    argmax regardless of input. NLGenerationHead's lm_head is bias=False
    by default; we swap in a bias=True Linear for these tests."""
    import torch.nn as nn
    in_features = model.nl_gen_head.lm_head.in_features
    new_head = nn.Linear(in_features, vocab_size, bias=True)
    with torch.no_grad():
        nn.init.zeros_(new_head.weight)
        nn.init.zeros_(new_head.bias)
        new_head.bias[target_id] = float(magnitude)
    model.nl_gen_head.lm_head = new_head


def test_eos_terminates_generation():
    """Force EOS sampling by hacking logits via a tokenizer where EOS
    has overwhelming probability. We simulate this by patching the
    head's last layer to produce EOS-favoring logits."""
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    _bias_lm_head_toward(model, tok.vocab_size, tok.EOS_ID, magnitude=10.0)
    eos_id = tok.EOS_ID

    out = generate_reply(
        model=model, tokenizer=tok, prompt_text="hello",
        max_new_tokens=20, sampling="greedy",
    )
    assert out["stopped_on_eos"] is True
    # Should have stopped on first step
    assert out["n_steps"] == 1
    # EOS should be stripped from output token_ids
    assert eos_id not in out["token_ids"]


# ---------------------------------------------------------------------------
# 5. max_new_tokens caps generation when EOS doesn't fire
# ---------------------------------------------------------------------------

def _bias_lm_head_against(model, vocab_size: int, avoid_id: int) -> None:
    """Replace lm_head so a specific token is essentially never chosen
    (large negative bias). Forces generation to run to max_new_tokens."""
    import torch.nn as nn
    in_features = model.nl_gen_head.lm_head.in_features
    new_head = nn.Linear(in_features, vocab_size, bias=True)
    with torch.no_grad():
        nn.init.uniform_(new_head.weight, -0.1, 0.1)
        nn.init.zeros_(new_head.bias)
        new_head.bias[avoid_id] = -1e6
    model.nl_gen_head.lm_head = new_head


def test_max_new_tokens_caps_generation():
    """Bias lm_head AGAINST EOS so generation runs to the cap."""
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    _bias_lm_head_against(model, tok.vocab_size, tok.EOS_ID)

    cap = 8
    out = generate_reply(
        model=model, tokenizer=tok, prompt_text="hello world",
        max_new_tokens=cap, sampling="greedy",
    )
    assert out["stopped_on_eos"] is False
    assert out["n_steps"] == cap


# ---------------------------------------------------------------------------
# 6. Temperature sampling produces stochastic output
# ---------------------------------------------------------------------------

def test_temperature_sampling_is_stochastic():
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    # Bias against EOS so we get longer outputs to compare
    _bias_lm_head_against(model, tok.vocab_size, tok.EOS_ID)

    samples = []
    for seed in [1, 2, 3, 4, 5, 6, 7, 8]:
        torch.manual_seed(seed)
        out = generate_reply(
            model=model, tokenizer=tok, prompt_text="hello",
            max_new_tokens=8, sampling="temperature", temperature=1.5,
        )
        samples.append(tuple(out["token_ids"]))
    # At least 2 distinct outputs across 8 different RNG seeds.
    # If temperature sampling were deterministic, we'd get all 1.
    assert len(set(samples)) >= 2


# ---------------------------------------------------------------------------
# 7. top_p (nucleus) sampling runs and respects the cap
# ---------------------------------------------------------------------------

def test_top_p_sampling_completes_cleanly():
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    _bias_lm_head_against(model, tok.vocab_size, tok.EOS_ID)
    out = generate_reply(
        model=model, tokenizer=tok, prompt_text="hello",
        max_new_tokens=6, sampling="top_p", temperature=1.0, top_p=0.9,
    )
    assert out["n_steps"] == 6
    assert out["config"]["top_p"] == 0.9
    assert out["config"]["temperature"] == 1.0


def test_top_p_invalid_value_raises():
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    with pytest.raises(ValueError, match="top_p"):
        generate_reply(
            model=model, tokenizer=tok, prompt_text="hi",
            sampling="top_p", top_p=1.5,
        )


# ---------------------------------------------------------------------------
# 8. Register mapping — non-default register routes to its id
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("register, expected_id", [
    ("T", 0), ("A", 1), ("f", 2), ("E", 3),
])
def test_register_mapping(register, expected_id):
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    out = generate_reply(
        model=model, tokenizer=tok, prompt_text="hello",
        register=register, max_new_tokens=3, sampling="greedy",
    )
    assert out["config"]["register"] == register
    assert out["config"]["register_id"] == expected_id


def test_unknown_register_falls_back_to_zero():
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    out = generate_reply(
        model=model, tokenizer=tok, prompt_text="hello",
        register="Z", max_new_tokens=3, sampling="greedy",
    )
    assert out["config"]["register_id"] == 0


# ---------------------------------------------------------------------------
# 9. CAS prefix path (--use-cas-prefix=True) wires cas_prefix_ids to head
# ---------------------------------------------------------------------------

def test_cas_prefix_path_runs_when_enabled():
    """When use_cas_prefix=True and cas_expression is provided, the head
    is called with cas_prefix_ids set. Verify by checking the run completes
    cleanly — no shape mismatches, no errors."""
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    out = generate_reply(
        model=model, tokenizer=tok,
        prompt_text="hello world",
        cas_expression="^2^E",
        use_cas_prefix=True,
        register="f",
        max_new_tokens=5, sampling="greedy",
    )
    assert out["config"]["use_cas_prefix"] is True
    assert out["cas_expression"] == "^2^E"
    assert isinstance(out["reply_text"], str)


def test_cas_prefix_default_off_does_not_pass_prefix():
    """Default use_cas_prefix=False means the head never receives
    cas_prefix_ids even if cas_expression is provided. The leakage-guard
    behavior matches the trainer's --use-cas-prefix off default."""
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    out = generate_reply(
        model=model, tokenizer=tok,
        prompt_text="hello",
        cas_expression="^2^E",
        # use_cas_prefix omitted -> default False
        max_new_tokens=3, sampling="greedy",
    )
    assert out["config"]["use_cas_prefix"] is False
    # Run completes regardless of the cas_expression value
    assert isinstance(out["reply_text"], str)


# ---------------------------------------------------------------------------
# 10. Missing nl_gen_head raises clearly
# ---------------------------------------------------------------------------

def test_no_attached_head_raises():
    tok = _make_tokenizer()
    enc_cfg = CASNativeConfig(d_model=32, n_layers=1, n_heads=4, vocab_size=tok.vocab_size)
    encoder = CASNativeModel(enc_cfg)
    # Intentionally do NOT call attach_nl_gen_head
    with pytest.raises(RuntimeError, match="nl_gen_head"):
        generate_reply(
            model=encoder, tokenizer=tok, prompt_text="hi",
            max_new_tokens=3, sampling="greedy",
        )


# ---------------------------------------------------------------------------
# 11. Invalid sampling mode raises
# ---------------------------------------------------------------------------

def test_unknown_sampling_mode_raises():
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    with pytest.raises(ValueError, match="unknown sampling"):
        generate_reply(
            model=model, tokenizer=tok, prompt_text="hi",
            sampling="bogus",
        )


def test_invalid_temperature_raises():
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    with pytest.raises(ValueError, match="temperature"):
        generate_reply(
            model=model, tokenizer=tok, prompt_text="hi",
            sampling="temperature", temperature=0.0,
        )


# ---------------------------------------------------------------------------
# 12. return_trace populates head metadata
# ---------------------------------------------------------------------------

def test_return_trace_populates_head_metadata():
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    # Bias toward EOS so generation stops fast and we hit the EOS-branch
    # of the trace-capture code.
    _bias_lm_head_toward(model, tok.vocab_size, tok.EOS_ID, magnitude=10.0)

    out = generate_reply(
        model=model, tokenizer=tok, prompt_text="hello",
        max_new_tokens=10, sampling="greedy", return_trace=True,
    )
    assert out["stopped_on_eos"] is True
    assert out["trace"] is not None
    # Head's return_meta=True populates output_id, model_code_version,
    # model_weights_sha, etc. We don't assert specific keys (those are
    # the head's contract, not ours), but the dict should be non-empty.
    assert isinstance(out["trace"], dict)
    assert len(out["trace"]) > 0


# ---------------------------------------------------------------------------
# 13. DEFAULT_REGISTER_TO_ID matches register_film NUM_REGISTERS
# ---------------------------------------------------------------------------

def test_default_register_to_id_matches_register_film():
    from cas_native.model.register_film import NUM_REGISTERS
    assert max(DEFAULT_REGISTER_TO_ID.values()) == NUM_REGISTERS - 1
    assert len(set(DEFAULT_REGISTER_TO_ID.values())) == NUM_REGISTERS


# ---------------------------------------------------------------------------
# 14. Empty prompt is handled defensively (no IndexError)
# ---------------------------------------------------------------------------

def test_empty_prompt_handled():
    tok = _make_tokenizer()
    model = _make_model_with_head(tok)
    out = generate_reply(
        model=model, tokenizer=tok, prompt_text="",
        max_new_tokens=3, sampling="greedy",
    )
    # Doesn't crash; produces a defensive single-token encoding fallback
    assert isinstance(out["reply_text"], str)
    assert out["n_steps"] >= 1
