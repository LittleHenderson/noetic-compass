"""Tests for the native CAS-Native English generation head.

These tests enforce both behavioral correctness and the architectural rule
that NO foreign pretrained models are used: the module docstring is scanned
for the literal string "NO foreign pretrained" and ``_VERSION`` must be a
semver-shaped string.
"""

from __future__ import annotations

import re

import pytest
import torch

from cas_native.model import nl_generation_head as nlg_mod
from cas_native.model.nl_generation_head import (
    GenerationTrace,
    NLGenerationHead,
    NLGenerationHeadConfig,
    TokenStep,
    _VERSION,
)
from cas_native.model.cas_native_model import CASNativeConfig, CASNativeModel


SMALL_CFG_KW = dict(
    vocab_size=128,
    d_model=32,
    n_heads=4,
    n_layers=2,
    ffn_dim=64,
    dropout=0.0,
    bottleneck_dim=16,
    soft_prefix_length=2,
    max_len=64,
)


def _make_head(**overrides) -> NLGenerationHead:
    kw = {**SMALL_CFG_KW, **overrides}
    return NLGenerationHead(NLGenerationHeadConfig(**kw))


# ---------------------------------------------------------------------------
# Architectural-rule tests
# ---------------------------------------------------------------------------


def test_module_docstring_no_foreign_pretrained():
    """Architectural rule: the module docstring must explicitly state that
    no foreign pretrained models are used. Caught by static substring scan.
    """
    docstring = nlg_mod.__doc__ or ""
    assert "NO foreign pretrained" in docstring, (
        "Module docstring must contain the literal string "
        '"NO foreign pretrained" — this is a load-bearing architectural '
        "guarantee."
    )


def test_version_constant_is_semver_shaped():
    """``_VERSION`` must follow ``vMAJOR.MINOR.PATCH`` semver shape."""
    assert isinstance(_VERSION, str)
    assert re.match(r"^v\d+\.\d+\.\d+$", _VERSION), (
        f"_VERSION must be semver-shaped (e.g. 'v0.1.0'), got {_VERSION!r}"
    )


def test_config_dataclass_is_frozen():
    """Frozen so the ``code_version`` declaration cannot drift from the
    module-level constant after construction."""
    cfg = NLGenerationHeadConfig(**SMALL_CFG_KW)
    with pytest.raises(Exception):
        # frozen dataclass raises FrozenInstanceError on attribute assignment.
        cfg.d_model = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Forward / backward
# ---------------------------------------------------------------------------


def test_forward_shape_basic():
    """Logits shape: (B, L, V) — CAS prefix is stripped from the output."""
    head = _make_head()
    b, l, k, s_enc = 2, 10, 3, 5
    decoder_ids = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, l))
    bottleneck = torch.randn(b, SMALL_CFG_KW["bottleneck_dim"])
    cas_prefix = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, k))
    encoder_out = torch.randn(b, s_enc, SMALL_CFG_KW["d_model"])
    domain_mask = torch.ones(b, s_enc, dtype=torch.bool)

    logits = head(
        decoder_ids,
        bottleneck,
        cas_prefix_ids=cas_prefix,
        encoder_outputs=encoder_out,
        domain_mask=domain_mask,
    )
    assert logits.shape == (b, l, SMALL_CFG_KW["vocab_size"])


def test_backward_pass_flows_gradients():
    """Backward pass produces non-zero gradients on the in-path parameters
    (every parameter touched by the forward without optional conditioning).

    Parameters that are NOT touched by this minimal forward (the legacy
    RegisterFiLM gamma/beta when ``register_id is None``) are excluded —
    that's expected behavior, not a bug.
    """
    head = _make_head()
    head.train()
    b, l = 2, 8
    decoder_ids = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, l))
    bottleneck = torch.randn(b, SMALL_CFG_KW["bottleneck_dim"])
    logits = head(decoder_ids, bottleneck)
    loss = logits.sum()
    loss.backward()

    # The lm_head, soft_prefix_proj, token_embedding, every decoder layer,
    # and final_norm are all in-path under the minimal forward.
    in_path = [
        ("lm_head.weight", head.lm_head.weight),
        ("soft_prefix_proj.weight", head.soft_prefix_proj.weight),
        ("token_embedding.weight", head.token_embedding.weight),
        ("final_norm.weight", head.final_norm.weight),
    ]
    for name, p in in_path:
        assert p.grad is not None, f"{name} has no grad"
        assert p.grad.abs().sum().item() > 0.0, f"{name} grad is zero"


def test_soft_prefix_projection_shape():
    """The bottleneck soft-prefix has correct learned shape.

    The projection maps (B, bottleneck_dim) -> (B, K, d_model).
    """
    head = _make_head()
    bottleneck = torch.randn(3, SMALL_CFG_KW["bottleneck_dim"])
    soft = head._build_soft_prefix(bottleneck)
    assert soft.shape == (
        3,
        SMALL_CFG_KW["soft_prefix_length"],
        SMALL_CFG_KW["d_model"],
    )


def test_domain_mask_affects_cross_attention():
    """Different domain masks must produce different output logits.

    Distinguishes between an all-True mask and a half-True mask under the
    same encoder stream.
    """
    head = _make_head()
    head.eval()
    torch.manual_seed(0)
    b, l, s_enc = 2, 6, 8
    decoder_ids = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, l))
    bottleneck = torch.randn(b, SMALL_CFG_KW["bottleneck_dim"])
    encoder_out = torch.randn(b, s_enc, SMALL_CFG_KW["d_model"])

    full_mask = torch.ones(b, s_enc, dtype=torch.bool)
    half_mask = torch.zeros(b, s_enc, dtype=torch.bool)
    half_mask[:, :s_enc // 2] = True

    with torch.no_grad():
        logits_full = head(
            decoder_ids, bottleneck,
            encoder_outputs=encoder_out,
            domain_mask=full_mask,
        )
        logits_half = head(
            decoder_ids, bottleneck,
            encoder_outputs=encoder_out,
            domain_mask=half_mask,
        )
    assert not torch.allclose(logits_full, logits_half, atol=1e-6)


def test_register_film_changes_output():
    """Different register IDs produce different post-decoder logits.

    With the legacy RegisterFiLM init (gamma=1, beta=0), default-init
    register effects would be the identity; we explicitly perturb gamma so
    the test covers the FiLM path being engaged.
    """
    head = _make_head()
    head.eval()
    # Perturb FiLM so the registers are functionally distinct.
    with torch.no_grad():
        head.register_film.gamma.add_(
            torch.randn_like(head.register_film.gamma) * 0.5
        )
        head.register_film.beta.add_(
            torch.randn_like(head.register_film.beta) * 0.5
        )

    b, l = 2, 4
    decoder_ids = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, l))
    bottleneck = torch.randn(b, SMALL_CFG_KW["bottleneck_dim"])

    reg0 = torch.zeros(b, dtype=torch.long)
    reg1 = torch.ones(b, dtype=torch.long)

    with torch.no_grad():
        out0 = head(decoder_ids, bottleneck, register_id=reg0)
        out1 = head(decoder_ids, bottleneck, register_id=reg1)
    assert not torch.allclose(out0, out1, atol=1e-6)


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def test_generation_respects_max_new_tokens():
    """``generate`` produces no more than ``max_new_tokens`` new tokens."""
    head = _make_head()
    b, l0 = 1, 3
    decoder_ids = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, l0))
    bottleneck = torch.randn(b, SMALL_CFG_KW["bottleneck_dim"])
    n_new = 5
    out_ids, trace = head.generate(
        decoder_ids,
        bottleneck,
        max_new_tokens=n_new,
        with_trace=False,
    )
    assert trace is None
    assert out_ids.shape[0] == b
    assert l0 <= out_ids.shape[1] <= l0 + n_new


def test_generation_with_trace_populates_token_steps():
    """``with_trace=True`` populates a GenerationTrace with one TokenStep
    per generated token."""
    head = _make_head()
    b, l0 = 1, 2
    decoder_ids = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, l0))
    bottleneck = torch.randn(b, SMALL_CFG_KW["bottleneck_dim"])
    cas_prefix = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, 2))

    out_ids, trace = head.generate(
        decoder_ids,
        bottleneck,
        cas_prefix_ids=cas_prefix,
        max_new_tokens=4,
        with_trace=True,
        temperature=0.0,  # deterministic
    )
    assert isinstance(trace, GenerationTrace)
    new_count = out_ids.shape[1] - l0
    assert len(trace.tokens) == new_count
    assert all(isinstance(t, TokenStep) for t in trace.tokens)


def test_generation_trace_has_required_fields():
    """All required GenerationTrace fields must be populated and well-typed."""
    head = _make_head()
    b, l0 = 1, 2
    decoder_ids = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, l0))
    bottleneck = torch.randn(b, SMALL_CFG_KW["bottleneck_dim"])

    _, trace = head.generate(
        decoder_ids,
        bottleneck,
        max_new_tokens=2,
        with_trace=True,
    )
    assert trace is not None
    assert trace.schema_version == "generation_trace.v1"
    assert isinstance(trace.output_id, str) and len(trace.output_id) > 0
    assert trace.model_code_version == _VERSION
    assert isinstance(trace.model_weights_sha, str)
    assert len(trace.model_weights_sha) == 64
    assert isinstance(trace.cas_conditioning_repr, str)
    assert isinstance(trace.created_at, str) and len(trace.created_at) > 0


def test_token_step_has_all_required_fields():
    """A TokenStep records position, token_id, attention summaries, and
    per-layer activation L2."""
    head = _make_head()
    b, l0 = 1, 2
    decoder_ids = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, l0))
    bottleneck = torch.randn(b, SMALL_CFG_KW["bottleneck_dim"])
    cas_prefix = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, 2))

    _, trace = head.generate(
        decoder_ids,
        bottleneck,
        cas_prefix_ids=cas_prefix,
        max_new_tokens=1,
        with_trace=True,
        temperature=0.0,
    )
    assert trace is not None and len(trace.tokens) == 1
    step = trace.tokens[0]
    assert step.position == 0
    assert isinstance(step.token_id, int)
    assert step.token_str is None  # no token_decoder supplied
    assert isinstance(step.attn_to_cas_prefix, tuple)
    assert isinstance(step.attn_to_prior_tokens, tuple)
    assert len(step.layer_activation_l2) == SMALL_CFG_KW["n_layers"]
    assert step.selected_via in {"argmax", "topp", "temp"}


def test_compute_weights_sha_is_deterministic():
    """Same weights -> same sha. Mutating a weight changes the sha."""
    head = _make_head()
    sha_a = head.compute_weights_sha()
    sha_b = head.compute_weights_sha()
    assert sha_a == sha_b
    with torch.no_grad():
        head.lm_head.weight.add_(0.1)
    sha_c = head.compute_weights_sha()
    assert sha_c != sha_a


def test_different_config_has_different_param_count():
    """Larger configs have strictly more parameters."""
    small = _make_head()
    bigger = _make_head(d_model=64)
    n_small = sum(p.numel() for p in small.parameters())
    n_big = sum(p.numel() for p in bigger.parameters())
    assert n_big > n_small


def test_forward_return_meta_includes_traceability_fields():
    """``return_meta=True`` returns the object-traceability surface."""
    head = _make_head()
    b, l = 1, 4
    decoder_ids = torch.randint(0, SMALL_CFG_KW["vocab_size"], (b, l))
    bottleneck = torch.randn(b, SMALL_CFG_KW["bottleneck_dim"])
    logits, meta = head(decoder_ids, bottleneck, return_meta=True)
    assert isinstance(logits, torch.Tensor)
    assert "output_id" in meta
    assert meta["model_code_version"] == _VERSION
    assert isinstance(meta["model_weights_sha"], str)
    assert len(meta["model_weights_sha"]) == 64
    assert "cas_conditioning_id" in meta
    assert "attention_summary" in meta
    summary = meta["attention_summary"]
    assert summary["n_layers"] == SMALL_CFG_KW["n_layers"]
    assert "layer_l2_means" in summary


# ---------------------------------------------------------------------------
# CASNativeModel integration
# ---------------------------------------------------------------------------


def _make_native_model(vocab_size: int = 64) -> CASNativeModel:
    cfg = CASNativeConfig(
        d_model=32,
        n_layers=2,
        n_heads=4,
        vocab_size=vocab_size,
        max_seq_len=64,
        fractal_depth=1,
        num_ethical_propositions=3,
    )
    return CASNativeModel(cfg)


def test_cas_native_model_forward_with_lm_returns_both_outputs():
    """``forward_with_lm`` produces every existing key plus ``lm_logits``."""
    cas_model = _make_native_model()
    head_cfg = NLGenerationHeadConfig(
        vocab_size=cas_model.config.vocab_size,
        d_model=32,
        n_heads=4,
        n_layers=2,
        ffn_dim=64,
        dropout=0.0,
        bottleneck_dim=16,
        soft_prefix_length=2,
        max_len=64,
    )
    cas_model.attach_nl_gen_head(NLGenerationHead(head_cfg))

    b, s, l = 2, 6, 4
    encoder_ids = torch.randint(0, cas_model.config.vocab_size, (b, s))
    decoder_ids = torch.randint(0, cas_model.config.vocab_size, (b, l))

    out = cas_model.forward_with_lm(
        encoder_ids,
        decoder_ids,
    )
    # Existing keys preserved.
    for k in ("logits", "hidden_states", "pooled_hidden_state",
              "cognitive_state", "rpm_satisfaction", "inversion_flags"):
        assert k in out
    # New key.
    assert "lm_logits" in out
    assert out["lm_logits"].shape == (b, l, cas_model.config.vocab_size)


def test_cas_native_model_forward_unchanged_without_lm_head():
    """Default forward path is unchanged — no nl_gen_head, no regression."""
    cas_model = _make_native_model()
    assert cas_model.nl_gen_head is None
    b, s = 2, 6
    encoder_ids = torch.randint(0, cas_model.config.vocab_size, (b, s))
    out = cas_model(encoder_ids)
    assert "logits" in out
    assert "lm_logits" not in out


def test_cas_native_model_forward_with_lm_raises_when_head_missing():
    """``forward_with_lm`` errors out when no head is attached."""
    cas_model = _make_native_model()
    b, s, l = 1, 4, 2
    encoder_ids = torch.randint(0, cas_model.config.vocab_size, (b, s))
    decoder_ids = torch.randint(0, cas_model.config.vocab_size, (b, l))
    with pytest.raises(RuntimeError, match="nl_gen_head"):
        cas_model.forward_with_lm(encoder_ids, decoder_ids)
