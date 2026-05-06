"""Tests for ``save_tokenizer_artifacts`` in train_native_nl_gen.

The helper is the load-bearing fix for Codex's audit finding: the previous
inline save logic silently skipped writing tokenizer.json when the
tokenizer was an ``ExtendedHybridCASTokenizer`` (no ``save()`` attribute,
``hasattr`` returns False, the if-block was skipped without exception).
These tests pin the four branches: plain HybridCAS save, Extended via
.base, BPE artifact copy, and the raise-on-unsavable path.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cas_native.training.tokenizer import HybridCASTokenizer
from cas_native.training.train_native_nl_gen import save_tokenizer_artifacts


def _make_tokenizer() -> HybridCASTokenizer:
    tok = HybridCASTokenizer()
    for w in ["hello", "world", "today", "the", "feel"]:
        tok.fit_text(w)
    tok.freeze()
    return tok


# ---------------------------------------------------------------------------
# 1. Plain HybridCASTokenizer: save() is called directly, file lands
# ---------------------------------------------------------------------------

def test_plain_hybrid_tokenizer_saves_directly(tmp_path):
    tok = _make_tokenizer()
    prov = save_tokenizer_artifacts(tok, tmp_path)

    out = tmp_path / "tokenizer.json"
    assert out.exists()
    assert prov["tokenizer_path"] == str(out)
    assert prov["tokenizer_hash"]
    assert prov["tokenizer_kind"] == "HybridCASTokenizer"
    assert prov["vocab_size"] == tok.vocab_size

    # Round-trip
    loaded = HybridCASTokenizer.load(out)
    assert loaded.vocab_size == tok.vocab_size
    assert loaded.frozen


# ---------------------------------------------------------------------------
# 2. ExtendedHybridCASTokenizer: save reaches through to .base
# ---------------------------------------------------------------------------

def test_extended_tokenizer_saves_via_base(tmp_path):
    """The Codex-caught bug: ExtendedHybridCASTokenizer doesn't have
    save(), but does expose .base. The helper must reach through and
    save the base, not silently skip."""
    from cas_native.training.english_bpe_extension import (
        BPEArtifact,
        ExtendedHybridCASTokenizer,
        train_english_bpe,
    )

    # Build a tiny corpus and train a tiny BPE artifact for the test
    corpus_path = tmp_path / "corpus.jsonl"
    records = [
        {"prompt": "hello world today", "reply": "the world is large"},
        {"prompt": "the world feels new", "reply": "the world today"},
        {"prompt": "hello today the world", "reply": "hello hello"},
    ]
    with corpus_path.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")

    bpe_artifact_path = tmp_path / "bpe_artifact.json"
    train_english_bpe(
        corpus_path,
        vocab_size=300,
        min_frequency=1,
        output_path=bpe_artifact_path,
    )

    base = _make_tokenizer()
    extended = base.with_english_bpe(bpe_artifact_path)
    assert isinstance(extended, ExtendedHybridCASTokenizer)
    # Pre-condition Codex flagged: no save() on Extended
    assert not hasattr(extended, "save"), (
        "if Extended grows save(), the explicit-base branch in "
        "save_tokenizer_artifacts can be simplified"
    )

    out_dir = tmp_path / "out"
    prov = save_tokenizer_artifacts(
        extended,
        out_dir,
        english_bpe_path=str(bpe_artifact_path),
    )

    # tokenizer.json must exist (the base tokenizer)
    tokenizer_out = out_dir / "tokenizer.json"
    assert tokenizer_out.exists(), "Codex-caught bug: tokenizer.json was silently skipped"
    assert prov["tokenizer_path"] == str(tokenizer_out)
    assert prov["tokenizer_kind"] == "ExtendedHybridCASTokenizer"
    assert prov["vocab_size"] == extended.vocab_size

    # english_bpe.json must exist as a copy in out_dir (self-containment)
    bpe_out = out_dir / "english_bpe.json"
    assert bpe_out.exists(), "BPE artifact must be copied into checkpoint dir"
    assert prov["english_bpe_path"] == str(bpe_out)
    assert prov["english_bpe_hash"]
    assert prov["english_bpe_source_path"] == str(bpe_artifact_path)

    # The copied artifact must equal the source
    assert bpe_out.read_bytes() == bpe_artifact_path.read_bytes()

    # The base tokenizer round-trips from the saved path
    loaded_base = HybridCASTokenizer.load(tokenizer_out)
    assert loaded_base.vocab_size == base.vocab_size


# ---------------------------------------------------------------------------
# 3. Unsavable tokenizer raises clearly (silent skip is unacceptable)
# ---------------------------------------------------------------------------

class _BareTokenizer:
    """A tokenizer-shaped object with neither save() nor a .base attribute."""

    BOS_ID = 2
    EOS_ID = 3
    PAD_ID = 0
    vocab_size = 100

    def encode(self, text, max_length=512, *, add_special=False):
        return []


def test_unsavable_tokenizer_raises(tmp_path):
    """An object that exposes encode() but no save() and no .base must
    raise — silent skip would create a checkpoint that can't be loaded
    back."""
    bare = _BareTokenizer()
    with pytest.raises(RuntimeError, match="cannot be saved"):
        save_tokenizer_artifacts(bare, tmp_path)


# ---------------------------------------------------------------------------
# 4. Missing BPE source path raises FileNotFoundError before partial write
# ---------------------------------------------------------------------------

def test_missing_bpe_source_path_raises(tmp_path):
    tok = _make_tokenizer()
    fake_bpe = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError):
        save_tokenizer_artifacts(tok, tmp_path, english_bpe_path=str(fake_bpe))


# ---------------------------------------------------------------------------
# 5. No BPE path: english_bpe.json is NOT written, tokenizer.json IS
# ---------------------------------------------------------------------------

def test_no_bpe_path_only_tokenizer_written(tmp_path):
    tok = _make_tokenizer()
    prov = save_tokenizer_artifacts(tok, tmp_path)

    assert (tmp_path / "tokenizer.json").exists()
    assert not (tmp_path / "english_bpe.json").exists()
    assert "english_bpe_path" not in prov
    assert "english_bpe_hash" not in prov
