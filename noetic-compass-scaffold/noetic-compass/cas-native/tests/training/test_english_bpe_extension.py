"""Tests for the English BPE tokenizer extension.

These tests cover both the BPE training entry point and the composed
``ExtendedHybridCASTokenizer``. The training corpus is a small synthetic
JSONL written to ``tmp_path`` so the suite runs in <2 seconds and does not
depend on the parallel SDG agent's output.

Test coverage targets are listed in
``docs/working/native_nl_tokenizer_extension_spec_2026_05_04.md`` §6.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cas_native.training.english_bpe_extension import (
    ARTIFACT_SCHEMA_VERSION,
    DEFAULT_VOCAB_VERSION,
    BPEArtifact,
    ExtendedHybridCASTokenizer,
    extend_hybrid_tokenizer,
    load_english_bpe_artifact,
    tokenize_with_provenance,
    train_english_bpe,
)
from cas_native.training.tokenizer import HybridCASTokenizer


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

MINI_CORPUS_LINES = [
    {
        "prompt": "The mind is drawn to the idea like a moth to a flame.",
        "reply": "This colloquialism maps to ^2 Positive in CAS: an Idea the Mind has an affinity for.",
    },
    {
        "prompt": "She can't stomach what they did to him.",
        "reply": "That's ^3 Negative — visceral aversion, not analytical critique.",
    },
    {
        "prompt": "It just popped into my head out of nowhere.",
        "reply": "Below/Effect — ^9 — an Idea brought to Mind by an Above/Cause trigger.",
    },
    {
        "prompt": "Practice makes perfect.",
        "reply": "Rhythm: ^7. The rate and pattern a Mind is exposed to an Idea.",
    },
    {
        "prompt": "We are the sum of our experiences.",
        "reply": "^5 Female — a Mind impregnated with an Idea.",
    },
    {
        "prompt": "Unpacking an idea, breaking it down.",
        "reply": "^6 Male — an Idea impregnated with another Idea.",
    },
    {
        "prompt": "Made an impression. Struck a chord.",
        "reply": "^4 Vibration — the degree to which an Idea resonates with the Mind.",
    },
    {
        "prompt": "One thing reminded me of another.",
        "reply": "^8 Above/Cause — associative triggering, not deductive reasoning.",
    },
    {
        "prompt": "Paying attention. Making up your mind.",
        "reply": "^1 Mind — various degrees of awareness that processes Ideas.",
    },
    {
        "prompt": "It's all in your head.",
        "reply": "^0 Idea — all things in and outside the Mind.",
    },
]


def _write_corpus(path: Path, lines: list[dict[str, str]]) -> Path:
    """Write a JSONL corpus to ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    return path


@pytest.fixture
def mini_corpus(tmp_path: Path) -> Path:
    return _write_corpus(tmp_path / "mini_corpus.jsonl", MINI_CORPUS_LINES)


@pytest.fixture
def trained_artifact(mini_corpus: Path, tmp_path: Path) -> dict:
    return train_english_bpe(
        mini_corpus,
        vocab_size=400,
        min_frequency=2,
        output_path=tmp_path / "bpe.json",
    )


@pytest.fixture
def extended_tokenizer(trained_artifact: dict, tmp_path: Path) -> ExtendedHybridCASTokenizer:
    base = HybridCASTokenizer.from_texts(["seed"])
    artifact = load_english_bpe_artifact(tmp_path / "bpe.json")
    return ExtendedHybridCASTokenizer(base=base, artifact=artifact)


# ---------------------------------------------------------------------------
# 1. BPE trains deterministically on a fixed mini-corpus
# ---------------------------------------------------------------------------

def test_bpe_trains_deterministically_on_mini_corpus(mini_corpus: Path, tmp_path: Path):
    a = train_english_bpe(
        mini_corpus,
        vocab_size=400,
        min_frequency=2,
        output_path=tmp_path / "a.json",
    )
    b = train_english_bpe(
        mini_corpus,
        vocab_size=400,
        min_frequency=2,
        output_path=tmp_path / "b.json",
    )
    # Merge sequence must be identical.
    assert a["merges"] == b["merges"]
    # Hash of the merge list — anchor for a fixed-corpus contract.
    merges_hash = hashlib.sha256(
        json.dumps(a["merges"], ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    # Both runs produce the same merges hash.
    merges_hash_b = hashlib.sha256(
        json.dumps(b["merges"], ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert merges_hash == merges_hash_b


# ---------------------------------------------------------------------------
# 2. Vocab cap is enforced
# ---------------------------------------------------------------------------

def test_bpe_respects_vocab_size_cap(mini_corpus: Path, tmp_path: Path):
    artifact = train_english_bpe(
        mini_corpus,
        vocab_size=300,
        min_frequency=1,  # admit even rare merges
        output_path=tmp_path / "small.json",
    )
    assert artifact["english_vocab_size"] <= 300
    # Total = bytes (256) + specials (4) + merges
    assert (
        artifact["english_vocab_size"]
        == 256 + 4 + artifact["bpe_merge_count"]
    )


# ---------------------------------------------------------------------------
# 3. CAS reserved tokens preserved at low IDs
# ---------------------------------------------------------------------------

def test_cas_reserved_tokens_preserve_low_ids(extended_tokenizer: ExtendedHybridCASTokenizer):
    base = extended_tokenizer.base
    n_cas = extended_tokenizer.cas_reserved_token_count
    # Every base ID survives unchanged in the extended tokenizer.
    for tok, idx in base.word2id.items():
        assert idx < n_cas
        assert extended_tokenizer._composed_id_to_token[idx] == tok  # noqa: SLF001
    # Specific load-bearing CAS tokens.
    for tok in ["^0", "^9", "^P", "|A", "Θ", "Ω", "∪", "∩"]:
        if tok in base.word2id:
            base_id = base.word2id[tok]
            assert base_id < n_cas
            assert extended_tokenizer._id_for_token(tok) == base_id  # noqa: SLF001


# ---------------------------------------------------------------------------
# 4. Roundtrip identity for ASCII
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "The mind is drawn to the idea.",
        "She can't stomach it.",
        "Practice makes perfect.",
        "We are the sum of our experiences.",
        "It just popped into my head.",
    ],
)
def test_roundtrip_identity_for_ascii(extended_tokenizer: ExtendedHybridCASTokenizer, text: str):
    ids = extended_tokenizer.encode(text, max_length=512, add_special=False)
    decoded = extended_tokenizer.decode(ids)
    assert decoded == text


# ---------------------------------------------------------------------------
# 5. Roundtrip handles multi-byte UTF-8
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "Resonance — ^4 — felt like a chord.",
        "Café résumé naïve",
        "面 — multi-byte: 你好 世界",
        "Mathematical: π ≈ 3.14, ∫ from 0 to ∞",
    ],
)
def test_roundtrip_handles_multibyte_utf8(
    extended_tokenizer: ExtendedHybridCASTokenizer, text: str
):
    ids = extended_tokenizer.encode(text, max_length=512, add_special=False)
    decoded = extended_tokenizer.decode(ids)
    assert decoded == text


# ---------------------------------------------------------------------------
# 6. Same corpus produces same merge order
# ---------------------------------------------------------------------------

def test_same_corpus_produces_same_merges(mini_corpus: Path, tmp_path: Path):
    a = train_english_bpe(mini_corpus, vocab_size=400, min_frequency=2)
    b = train_english_bpe(mini_corpus, vocab_size=400, min_frequency=2)
    assert a["merges"] == b["merges"]
    assert a["bpe_merge_count"] == b["bpe_merge_count"]


# ---------------------------------------------------------------------------
# 7. Different corpus -> different merges
# ---------------------------------------------------------------------------

def test_different_corpus_produces_different_merges(mini_corpus: Path, tmp_path: Path):
    a = train_english_bpe(mini_corpus, vocab_size=400, min_frequency=2)
    other_corpus = _write_corpus(
        tmp_path / "other.jsonl",
        [
            {"prompt": "QQQQ XXXXX YYYYYYY ZZZZZZZ", "reply": "QQQQ XXXXX YYYYYYY"},
            {"prompt": "AAAA BBBB CCCC DDDD EEEE", "reply": "AAAA BBBB CCCC DDDD"},
        ],
    )
    b = train_english_bpe(other_corpus, vocab_size=400, min_frequency=2)
    assert a["merges"] != b["merges"]
    assert a["trained_from_corpus_hash"] != b["trained_from_corpus_hash"]


# ---------------------------------------------------------------------------
# 8. vocab_version + trained_from_corpus_hash populated
# ---------------------------------------------------------------------------

def test_artifact_provenance_fields_populated(trained_artifact: dict):
    required_fields = [
        "schema_version",
        "vocab_version",
        "trained_from_corpus_hash",
        "trained_from_corpus_path",
        "trained_at_timestamp",
        "bpe_merge_count",
        "english_vocab_size",
        "target_vocab_size",
        "min_frequency",
        "n_records_trained_on",
    ]
    for field in required_fields:
        assert field in trained_artifact, f"missing provenance field: {field}"
    assert trained_artifact["schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert trained_artifact["vocab_version"] == DEFAULT_VOCAB_VERSION
    assert len(trained_artifact["trained_from_corpus_hash"]) == 64  # SHA-256 hex
    assert isinstance(trained_artifact["bpe_merge_count"], int)
    assert isinstance(trained_artifact["english_vocab_size"], int)
    assert trained_artifact["bpe_merge_count"] >= 0


# ---------------------------------------------------------------------------
# 9. Tokenization output carries vocab_version
# ---------------------------------------------------------------------------

def test_tokenize_with_provenance_stamps_vocab_version(
    extended_tokenizer: ExtendedHybridCASTokenizer,
):
    out = tokenize_with_provenance("Practice makes perfect.", extended_tokenizer)
    assert "vocab_version" in out
    assert out["vocab_version"] == extended_tokenizer.vocab_version
    assert out["vocab_version"] == DEFAULT_VOCAB_VERSION
    assert "encoded_at" in out
    assert "tokens" in out
    assert "ids" in out
    assert isinstance(out["tokens"], list)
    assert isinstance(out["ids"], list)
    assert len(out["ids"]) > 0


def test_tokenize_with_provenance_works_on_base_hybrid_tokenizer():
    base = HybridCASTokenizer.from_texts(["seed text"])
    out = tokenize_with_provenance("seed text", base)
    assert out["vocab_version"] == HybridCASTokenizer.VERSION


# ---------------------------------------------------------------------------
# 10. Extended tokenizer keeps CAS-only callers working
# ---------------------------------------------------------------------------

def test_extended_tokenizer_keeps_cas_only_callers_working(
    extended_tokenizer: ExtendedHybridCASTokenizer,
):
    """Every CAS-mixed expression that round-tripped through the base
    hybrid tokenizer must still round-trip through the extended tokenizer.
    """
    cas_expressions = [
        "^2^P_{F2}|A",
        "Θ(Ω_safe_judgment) = 0.40·^3^P_{F2}|A → Ω_safe_judgment",
        "Product(Noetics, Domains)",
        "(^3^P|A × ^3^P|f) = ^3^P|Ω_unified",
    ]
    for expr in cas_expressions:
        ids = extended_tokenizer.encode(expr, add_special=False)
        decoded = extended_tokenizer.decode(ids)
        assert decoded == expr, f"roundtrip failed for {expr!r}: got {decoded!r}"


# ---------------------------------------------------------------------------
# 11. Min-frequency enforced (rare merges dropped)
# ---------------------------------------------------------------------------

def test_min_frequency_drops_rare_merges(tmp_path: Path):
    """A corpus with many singletons should produce few merges if
    min_frequency=2.
    """
    # Each line has a unique made-up word — every adjacent byte pair has count 1.
    unique_words_corpus = _write_corpus(
        tmp_path / "unique.jsonl",
        [
            {"prompt": f"qzx{i}qrm{i}", "reply": f"abj{i}znw{i}"}
            for i in range(20)
        ],
    )
    # With min_frequency=2, only pairs that recur across records get merged.
    a = train_english_bpe(
        unique_words_corpus,
        vocab_size=1000,
        min_frequency=2,
        output_path=tmp_path / "a.json",
    )
    # With min_frequency=1, every pair of any frequency can be merged, so
    # we should get strictly more merges.
    b = train_english_bpe(
        unique_words_corpus,
        vocab_size=1000,
        min_frequency=1,
        output_path=tmp_path / "b.json",
    )
    assert a["bpe_merge_count"] < b["bpe_merge_count"]


# ---------------------------------------------------------------------------
# 12. Vocab cap enforced (won't exceed vocab_size)
# ---------------------------------------------------------------------------

def test_vocab_cap_strict(mini_corpus: Path, tmp_path: Path):
    cap = 280
    artifact = train_english_bpe(
        mini_corpus,
        vocab_size=cap,
        min_frequency=1,
        output_path=tmp_path / "cap.json",
    )
    assert artifact["english_vocab_size"] <= cap


# ---------------------------------------------------------------------------
# 13. Corpus modification changes the hash
# ---------------------------------------------------------------------------

def test_corpus_hash_detects_modification(mini_corpus: Path, tmp_path: Path):
    a = train_english_bpe(mini_corpus, vocab_size=400, min_frequency=2)
    # Modify the corpus by one record.
    with open(mini_corpus, "a", encoding="utf-8") as fh:
        fh.write(
            json.dumps({"prompt": "extra line", "reply": "another extra line"}) + "\n"
        )
    b = train_english_bpe(mini_corpus, vocab_size=400, min_frequency=2)
    assert a["trained_from_corpus_hash"] != b["trained_from_corpus_hash"]


# ---------------------------------------------------------------------------
# 14. End-to-end: train, save, load, compose, encode/decode
# ---------------------------------------------------------------------------

def test_end_to_end_train_save_load_compose(mini_corpus: Path, tmp_path: Path):
    artifact_path = tmp_path / "e2e_bpe.json"
    train_english_bpe(
        mini_corpus,
        vocab_size=500,
        min_frequency=2,
        output_path=artifact_path,
    )
    base = HybridCASTokenizer.from_texts(["seed"])
    base_path = tmp_path / "base.json"
    base.save(base_path)

    extended = extend_hybrid_tokenizer(base_path, artifact_path)
    assert isinstance(extended, ExtendedHybridCASTokenizer)
    assert extended.cas_reserved_token_count > 0
    assert extended.english_vocab_size > 256  # at least the byte alphabet

    text = "The mind is drawn to ^2 Positive — an Idea the Mind has an affinity for."
    ids = extended.encode(text, add_special=False)
    decoded = extended.decode(ids)
    assert decoded == text


# ---------------------------------------------------------------------------
# 15. Empty / missing corpus errors cleanly
# ---------------------------------------------------------------------------

def test_missing_corpus_raises_filenotfound(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        train_english_bpe(tmp_path / "does_not_exist.jsonl", vocab_size=400)


def test_empty_corpus_raises_value_error(tmp_path: Path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        train_english_bpe(empty, vocab_size=400)


def test_too_small_vocab_size_raises(mini_corpus: Path):
    with pytest.raises(ValueError):
        # Below the byte-alphabet floor (256 + 4 specials = 260).
        train_english_bpe(mini_corpus, vocab_size=10)


# ---------------------------------------------------------------------------
# 16. Artifact reload roundtrip
# ---------------------------------------------------------------------------

def test_artifact_save_load_roundtrip(mini_corpus: Path, tmp_path: Path):
    out = tmp_path / "saved.json"
    payload = train_english_bpe(
        mini_corpus,
        vocab_size=400,
        min_frequency=2,
        output_path=out,
    )
    loaded = load_english_bpe_artifact(out)
    assert isinstance(loaded, BPEArtifact)
    assert loaded.bpe_merge_count == payload["bpe_merge_count"]
    assert loaded.trained_from_corpus_hash == payload["trained_from_corpus_hash"]
    assert loaded.merges == [tuple(p) for p in payload["merges"]]


# ---------------------------------------------------------------------------
# 17. Composed tokenizer metadata reports both layers
# ---------------------------------------------------------------------------

def test_composed_tokenizer_metadata_reports_both_layers(
    extended_tokenizer: ExtendedHybridCASTokenizer,
):
    meta = extended_tokenizer.metadata()
    assert meta["extension_type"] == "english_bpe"
    assert meta["vocab_version"] == DEFAULT_VOCAB_VERSION
    assert meta["cas_reserved_token_count"] == extended_tokenizer.cas_reserved_token_count
    assert meta["english_vocab_size"] == extended_tokenizer.english_vocab_size
    assert meta["extended_vocab_size"] == extended_tokenizer.vocab_size
    assert "trained_from_corpus_hash" in meta
    assert "trained_at_timestamp" in meta


# ---------------------------------------------------------------------------
# 18. Backward compatibility — base hybrid tokenizer untouched
# ---------------------------------------------------------------------------

def test_backward_compat_base_hybrid_unchanged_after_extension(mini_corpus: Path, tmp_path: Path):
    """The extension is non-destructive: the base hybrid tokenizer must
    continue to encode/decode as it always has, including when wrapped.
    """
    base_before = HybridCASTokenizer.from_texts(["seed"])
    word2id_before = dict(base_before.word2id)
    vocab_size_before = base_before.vocab_size

    artifact = train_english_bpe(
        mini_corpus,
        vocab_size=400,
        min_frequency=2,
    )
    art_obj = BPEArtifact.from_dict(artifact)
    extended = ExtendedHybridCASTokenizer(base=base_before, artifact=art_obj)

    # Wrapping doesn't mutate the base.
    assert base_before.word2id == word2id_before
    assert base_before.vocab_size == vocab_size_before

    # The base still works on its own.
    base_ids = base_before.encode("^3^P|A", add_special=False)
    assert base_before.UNK_ID not in base_ids
    assert base_before.decode(base_ids) == "^3^P|A"

    # And the extended tokenizer has the same vocab partition relationships.
    assert extended.cas_reserved_token_count == vocab_size_before
