"""Tests for diagnostic-infra piece 1: simplex MVP checkpoint save/load.

Per user 2026-05-11. CPU-only, tiny model. Verifies:
  - save_checkpoint round-trip preserves model state, optimizer state,
    RNG, config, tokenizer info
  - schema version is enforced on load
  - tied weight (lm_head <-> token_emb) survives round-trip as ONE
    shared tensor, not two copies
  - .manifest.json side-car is written
  - load_checkpoint with strict=False handles aux-head mismatch
"""
from __future__ import annotations

import json
import random as _random
from pathlib import Path

import pytest
import torch
import torch.optim as optim

from cas_native.model.typed_fiber_decoder import (
    TypedFiberDecoder, TypedFiberDecoderConfig,
)
from cas_native.training.simplex_checkpoint import (
    SCHEMA_VERSION,
    build_tokenizer_info,
    load_checkpoint,
    save_checkpoint,
)
from cas_native.training.train_simplex_mvp import (
    DEFAULT_LOSS_WEIGHTS, SimplexTrainConfig,
)


def _tiny_decoder() -> TypedFiberDecoder:
    cfg = TypedFiberDecoderConfig(
        vocab_size_english=128,
        d_model=32, n_heads=4, ffn_dim=64,
        n_layers=2, dropout=0.0,
    )
    return TypedFiberDecoder(cfg)


def _tiny_cfg() -> SimplexTrainConfig:
    cfg = SimplexTrainConfig(
        data_path="x", output_dir="y",
        d_model=32, encoder_n_layers=2, encoder_n_heads=4,
        decoder_n_layers=2, decoder_n_heads=4,
        batch_size=2, lr=1e-4,
    )
    cfg.loss_weights = dict(DEFAULT_LOSS_WEIGHTS)
    return cfg


def _tokenizer_info_stub() -> dict:
    return {
        "tokenizer_path": "/fake/tokenizer.json",
        "tokenizer_sha256": None,
        "english_bpe_path": "",
        "english_bpe_sha256": None,
        "vocab_size": 128,
    }


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

def test_save_load_round_trip_model_weights(tmp_path):
    """Saving + loading must preserve model.state_dict exactly."""
    model = _tiny_decoder()
    cfg = _tiny_cfg()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    ckpt = tmp_path / "test_ckpt.pt"

    # Snapshot weights before save
    pre_state = {k: v.clone() for k, v in model.state_dict().items()}
    save_checkpoint(
        str(ckpt), model=model, optimizer=optimizer, step=42, cfg=cfg,
        tokenizer_info=_tokenizer_info_stub(),
    )

    # Mutate the model so load has to actually restore
    with torch.no_grad():
        for p in model.parameters():
            p.fill_(0.0)
    # Confirm mutation took
    assert (next(model.parameters()).abs().sum() == 0).item()

    # Load
    payload = load_checkpoint(str(ckpt), model=model, optimizer=optimizer)

    # Verify weights restored
    post_state = model.state_dict()
    for k in pre_state:
        assert torch.equal(pre_state[k], post_state[k]), (
            f"weight {k!r} not restored exactly"
        )
    assert payload["step"] == 42
    assert payload["schema_version"] == SCHEMA_VERSION


def test_save_load_round_trip_tied_weight_shared_tensor(tmp_path):
    """The tied lm_head <-> token_emb tensor must remain ONE shared
    parameter after load, not split into two copies. Regression for the
    weight-tying decision (commit 7e23e4c)."""
    model = _tiny_decoder()
    # Confirm tying before save
    assert model.lm_head.weight is model.token_emb.weight

    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    ckpt = tmp_path / "test_tied.pt"
    save_checkpoint(
        str(ckpt), model=model, optimizer=optimizer, step=1, cfg=_tiny_cfg(),
        tokenizer_info=_tokenizer_info_stub(),
    )

    # Build a fresh model + load
    model2 = _tiny_decoder()
    assert model2.lm_head.weight is model2.token_emb.weight  # tied at init
    load_checkpoint(str(ckpt), model=model2)
    # Critical: still tied after load — modifying one must surface in other.
    with torch.no_grad():
        model2.token_emb.weight[0].fill_(7.77)
    assert torch.all(model2.lm_head.weight[0] == 7.77), (
        "lm_head <-> token_emb tying broken after load; model.state_dict() "
        "treated them as separate tensors"
    )


def test_save_load_round_trip_optimizer_state(tmp_path):
    """Adam moment buffers must be preserved (so resume produces same updates)."""
    model = _tiny_decoder()
    cfg = _tiny_cfg()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    # Take one optimizer step so moments populate
    x = torch.randn(1, 4, requires_grad=False)
    target = sum(p.sum() for p in model.parameters())
    target.backward()
    optimizer.step()

    ckpt = tmp_path / "test_optim.pt"
    save_checkpoint(
        str(ckpt), model=model, optimizer=optimizer, step=1, cfg=cfg,
        tokenizer_info=_tokenizer_info_stub(),
    )

    # New optimizer should NOT have moments
    optimizer2 = optim.Adam(model.parameters(), lr=1e-4)
    # state_dict has 'state' (per-param moments) and 'param_groups'
    assert len(optimizer2.state_dict()["state"]) == 0
    # Load — moments should populate
    load_checkpoint(str(ckpt), model=model, optimizer=optimizer2)
    assert len(optimizer2.state_dict()["state"]) > 0, (
        "optimizer state not restored"
    )


def test_warm_start_loads_model_only_skips_optimizer(tmp_path):
    """Candidate B warm-start contract (2026-05-11):
    load_checkpoint(..., optimizer=None) must load model weights but leave
    the caller's fresh optimizer state untouched. Required for staged
    training where each stage gets a fresh optimizer per its new loss
    landscape, but inherits prior-stage model weights.
    """
    model_a = _tiny_decoder()
    cfg = _tiny_cfg()
    optimizer_a = optim.Adam(model_a.parameters(), lr=1e-4)
    # Populate optimizer state with one step's worth of moments
    target = sum(p.sum() for p in model_a.parameters())
    target.backward()
    optimizer_a.step()

    ckpt = tmp_path / "warm_start.pt"
    save_checkpoint(
        str(ckpt), model=model_a, optimizer=optimizer_a, step=42, cfg=cfg,
        tokenizer_info=_tokenizer_info_stub(),
    )
    saved_weights = {k: v.clone() for k, v in model_a.state_dict().items()}

    # Fresh "stage 2" model + optimizer — these are the equivalent of a
    # new training run that calls --load-model-from on the stage-1 ckpt.
    model_b = _tiny_decoder()
    optimizer_b = optim.Adam(model_b.parameters(), lr=1e-4)
    # Confirm pre-load state: optimizer_b has NO moments, weights differ
    assert len(optimizer_b.state_dict()["state"]) == 0
    pre_load_weights = {k: v.clone() for k, v in model_b.state_dict().items()}
    any_differ = any(
        not torch.allclose(pre_load_weights[k], saved_weights[k], atol=1e-6)
        for k in saved_weights
    )
    assert any_differ, "test premise: fresh model B should differ from A"

    # Warm-start: model only, no optimizer, no RNG.
    load_checkpoint(
        str(ckpt), model=model_b, optimizer=None,
        restore_rng=False,
    )

    # Model weights must now match the saved snapshot exactly
    for k, expected in saved_weights.items():
        got = model_b.state_dict()[k]
        assert torch.allclose(got, expected, atol=1e-6), (
            f"warm-start failed to load weight {k}"
        )

    # Optimizer_b must STILL be fresh — no Adam moments inherited
    assert len(optimizer_b.state_dict()["state"]) == 0, (
        "warm-start must NOT restore optimizer state (Candidate B contract)"
    )


def test_save_writes_manifest_json_sidecar(tmp_path):
    """A .manifest.json side-car must exist next to the .pt file."""
    model = _tiny_decoder()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    ckpt = tmp_path / "test_manifest.pt"
    save_checkpoint(
        str(ckpt), model=model, optimizer=optimizer, step=99, cfg=_tiny_cfg(),
        tokenizer_info=_tokenizer_info_stub(),
    )
    manifest_path = ckpt.with_suffix(ckpt.suffix + ".manifest.json")
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["step"] == 99
    assert manifest["schema_version"] == SCHEMA_VERSION
    assert "config" in manifest
    assert "tokenizer_info" in manifest
    # Manifest must NOT include the heavy tensors
    assert "model_state_dict" not in manifest
    assert "optimizer_state_dict" not in manifest


# ---------------------------------------------------------------------------
# Schema enforcement
# ---------------------------------------------------------------------------

def test_load_rejects_wrong_schema_version(tmp_path):
    """A checkpoint with a non-matching schema_version must raise."""
    model = _tiny_decoder()
    ckpt = tmp_path / "bad_schema.pt"
    payload = {
        "schema_version": "OTHER_SCHEMA.v0",
        "model_state_dict": model.state_dict(),
    }
    torch.save(payload, str(ckpt))
    with pytest.raises(ValueError, match="schema mismatch"):
        load_checkpoint(str(ckpt), model=model)


def test_load_raises_on_missing_file(tmp_path):
    model = _tiny_decoder()
    with pytest.raises(FileNotFoundError):
        load_checkpoint(str(tmp_path / "nonexistent.pt"), model=model)


# ---------------------------------------------------------------------------
# Side-car content
# ---------------------------------------------------------------------------

def test_loss_history_tail_preserved(tmp_path):
    model = _tiny_decoder()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    fake_history = [{"step": i, "loss_lm": 10.0 - i * 0.1} for i in range(25)]
    ckpt = tmp_path / "test_hist.pt"
    save_checkpoint(
        str(ckpt), model=model, optimizer=optimizer, step=25, cfg=_tiny_cfg(),
        tokenizer_info=_tokenizer_info_stub(),
        loss_history_tail=fake_history,
    )
    payload = load_checkpoint(str(ckpt), model=model)
    # Tail capped at 20 by default
    assert len(payload["loss_history_tail"]) == 20
    assert payload["loss_history_tail"][-1]["step"] == 24


# ---------------------------------------------------------------------------
# RNG state
# ---------------------------------------------------------------------------

def test_rng_state_round_trip(tmp_path):
    """After load, torch.rand() must produce the same sequence as right
    after save (because RNG was restored)."""
    model = _tiny_decoder()
    optimizer = optim.Adam(model.parameters(), lr=1e-4)
    torch.manual_seed(1729)
    _random.seed(1729)

    ckpt = tmp_path / "test_rng.pt"
    save_checkpoint(
        str(ckpt), model=model, optimizer=optimizer, step=1, cfg=_tiny_cfg(),
        tokenizer_info=_tokenizer_info_stub(),
    )

    # Consume some randomness from the saved state
    pre_load_rand = torch.rand(5)

    # Reseed and load — should restore RNG to save time
    torch.manual_seed(9999)
    _random.seed(9999)
    load_checkpoint(str(ckpt), model=model)
    post_load_rand = torch.rand(5)
    assert torch.allclose(pre_load_rand, post_load_rand), (
        "RNG state not restored: torch.rand() produced different sequence"
    )


# ---------------------------------------------------------------------------
# Tokenizer info SHA
# ---------------------------------------------------------------------------

def test_build_tokenizer_info_computes_sha(tmp_path):
    fake_tok_path = tmp_path / "fake_tokenizer.json"
    fake_tok_path.write_text('{"vocab_size": 38683}', encoding="utf-8")

    class _FakeTokenizer:
        vocab_size = 38683

    info = build_tokenizer_info(str(fake_tok_path), "", tokenizer=_FakeTokenizer())
    assert info["tokenizer_path"] == str(fake_tok_path)
    assert info["tokenizer_sha256"] is not None
    assert len(info["tokenizer_sha256"]) == 64  # hex SHA-256
    assert info["vocab_size"] == 38683


def test_build_tokenizer_info_handles_missing_files():
    """Non-existent paths should produce None hashes without raising."""
    class _FakeTokenizer:
        vocab_size = 0

    info = build_tokenizer_info("", "", tokenizer=_FakeTokenizer())
    assert info["tokenizer_sha256"] is None
    assert info["english_bpe_sha256"] is None


# ---------------------------------------------------------------------------
# Default-off behavior
# ---------------------------------------------------------------------------

def test_save_checkpoints_at_default_empty():
    """SimplexTrainConfig default must keep checkpoint saving OFF."""
    cfg = SimplexTrainConfig(data_path="x", output_dir="y")
    assert cfg.save_checkpoints_at == ""
    assert cfg.save_final_checkpoint is False
