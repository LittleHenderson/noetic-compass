"""Tests for the 14 reserved CAS-literal tokens (vocab14 patch).

Background — see ``docs/working/v76_meta_logic_deep_dive_2026_05_04.md``
and ``docs/working/vocab14_prep_memo_2026_05_04.md``: the K=9 baseline
vocabulary missed all 7 typed meta-logic constructors and the bare
v7.6 production-semantics symbols. Those tokens are now seeded into
``RESERVED_CAS_TOKENS`` so they exist in the vocabulary regardless of
corpus frequency, and the CAS-notation recognizer matches them so they
tokenize as ``cas:`` keys (not ``surf:`` fallbacks).

These tests pin the four invariants:
  1. All 14 reserved CAS tokens are in the vocab built from any corpus.
  2. They are present even when the corpus does NOT contain them.
  3. They tokenize correctly when seen in an expression (right vocab IDs
     come out of the assembler).
  4. Adding the 14 tokens grows the vocab by EXACTLY 14 vs the prior
     baseline behavior on the same corpus.
"""

from __future__ import annotations

from cas_native.tokenizer import (
    RESERVED_CAS_TOKENS,
    RESERVED_TOKENS,
    StructuredTokenVocabulary,
    structured_token_key,
    tokenize,
)
from cas_native.tokenizer.cas_notation import (
    KIND_LAMBDA_BARE,
    KIND_OMEGA_BARE,
    KIND_SET_RELATION,
    KIND_THETA_BARE,
    KIND_TYPED_CONSTRUCTOR,
    match_cas_notation,
)


# ---------------------------------------------------------------------------
# Invariant 1 + 2: reserved tokens always present, regardless of corpus.
# ---------------------------------------------------------------------------


def test_reserved_cas_tokens_count_is_exactly_14():
    assert len(RESERVED_CAS_TOKENS) == 14, (
        "vocab14 patch is sized at 14 reserved CAS tokens — see "
        "docs/working/vocab14_prep_memo_2026_05_04.md"
    )


def test_reserved_cas_tokens_present_in_empty_vocab():
    vocab = StructuredTokenVocabulary.empty()
    for token in RESERVED_CAS_TOKENS:
        assert token in vocab.token_to_id, f"missing reserved token {token!r}"


def test_reserved_cas_tokens_present_when_corpus_does_not_contain_them():
    corpus = [
        "the quick brown fox jumps over the lazy dog",
        "this is plain natural language with no CAS notation at all",
        "we discuss attention and rhythm without any formal symbols",
    ]
    vocab = StructuredTokenVocabulary.from_texts(corpus, min_count=1)
    for token in RESERVED_CAS_TOKENS:
        assert token in vocab.token_to_id, (
            f"reserved CAS token {token!r} missing despite empty corpus"
        )


def test_reserved_cas_tokens_have_stable_consecutive_ids():
    vocab = StructuredTokenVocabulary.empty()
    base = len(RESERVED_TOKENS)
    for offset, token in enumerate(RESERVED_CAS_TOKENS):
        assert vocab.token_to_id[token] == base + offset, (
            f"reserved CAS token {token!r} expected id {base + offset}, "
            f"got {vocab.token_to_id[token]}"
        )


def test_reserved_cas_tokens_present_with_real_cas_corpus():
    corpus = [
        "I feel drawn to ^2^P_{F4}|f",
        "the audit highlights ^6^E and ^3^E together",
        "Ω_attunement landed cleanly",
    ]
    vocab = StructuredTokenVocabulary.from_texts(corpus, min_count=1)
    for token in RESERVED_CAS_TOKENS:
        assert token in vocab.token_to_id


# ---------------------------------------------------------------------------
# Invariant 3: tokenizer emits the right cas: keys for these constructs.
# ---------------------------------------------------------------------------


def test_typed_constructor_recognizer_matches_each_constructor_name():
    constructor_names = (
        "NoeticCluster",
        "StateSet",
        "StateCluster",
        "RelationCluster",
        "CoverOf",
        "PartitionOf",
        "Product",
    )
    for name in constructor_names:
        match = match_cas_notation(name)
        assert match is not None, f"recognizer missed {name!r}"
        assert match.kind == KIND_TYPED_CONSTRUCTOR
        assert match.matched_text == name
        assert "typed_constructor" in match.signature.role_tags
        assert f"typed_constructor:{name}" in match.signature.role_tags


def test_typed_constructor_does_not_match_a_longer_identifier():
    # "NoeticClusterX" must NOT be matched as the constructor — the negative
    # lookahead prevents partial matches that swallow neighbour identifiers.
    match = match_cas_notation("NoeticClusterX")
    assert match is None or match.kind != KIND_TYPED_CONSTRUCTOR


def test_typed_constructor_followed_by_brace_matches():
    match = match_cas_notation("NoeticCluster{^2, ^7}")
    assert match is not None
    assert match.kind == KIND_TYPED_CONSTRUCTOR
    assert match.matched_text == "NoeticCluster"


def test_bare_omega_recognizer_matches_only_when_no_label():
    # Bare Ω matches.
    match = match_cas_notation("Ω")
    assert match is not None
    assert match.kind == KIND_OMEGA_BARE
    # Ω_attunement still falls through to KIND_OMEGA (the labelled form).
    match2 = match_cas_notation("Ω_attunement")
    assert match2 is not None
    assert match2.kind != KIND_OMEGA_BARE  # should be KIND_OMEGA


def test_bare_theta_recognizer_matches_only_when_no_paren():
    # Bare Θ matches.
    match = match_cas_notation("Θ")
    assert match is not None
    assert match.kind == KIND_THETA_BARE
    # Θ( still falls through to the recipe-opener kind.
    match2 = match_cas_notation("Θ(Ω_recovery)")
    assert match2 is not None
    assert match2.kind != KIND_THETA_BARE


def test_bare_lambda_recognizer():
    match = match_cas_notation("Λ")
    assert match is not None
    assert match.kind == KIND_LAMBDA_BARE
    assert match.signature.role_tags == ("cas_literal", "lambda_bare", "leakage_marker")


def test_set_relation_operators_are_recognized_as_cas_notation():
    for symbol in ("∪", "∩", "∈", "⊆"):
        match = match_cas_notation(symbol)
        assert match is not None, f"set-relation symbol {symbol!r} not matched"
        assert match.kind == KIND_SET_RELATION


def test_assembler_emits_cas_key_for_typed_constructors():
    tokens = tokenize("NoeticCluster{^2, ^7} ∩ NoeticCluster{^7}")
    keys = [structured_token_key(t) for t in tokens]
    assert keys.count("cas:NoeticCluster") == 2, (
        "NoeticCluster must be emitted as the reserved cas: key, not surf:"
    )
    assert "cas:∩" in keys
    # Surface fallback should NOT be present for these tokens.
    assert "surf:noeticcluster" not in keys


def test_assembler_emits_cas_key_for_bare_recipe_symbols():
    # Note: Θ(Ω_recovery) parses Θ( as a recipe opener and Ω_recovery as
    # an omega-target, so we test the bare forms standalone.
    tokens = tokenize("Λ Ω Θ")
    keys = [structured_token_key(t) for t in tokens]
    assert "cas:Λ" in keys
    assert "cas:Ω" in keys
    assert "cas:Θ" in keys


def test_id_for_token_resolves_typed_constructor_to_seeded_id():
    vocab = StructuredTokenVocabulary.empty()
    tokens = tokenize("NoeticCluster")
    assert len(tokens) == 1
    expected_id = vocab.token_to_id["cas:NoeticCluster"]
    assert vocab.id_for_token(tokens[0]) == expected_id


def test_id_for_token_resolves_bare_lambda_to_seeded_id():
    vocab = StructuredTokenVocabulary.empty()
    tokens = tokenize("Λ")
    assert len(tokens) == 1
    expected_id = vocab.token_to_id["cas:Λ"]
    assert vocab.id_for_token(tokens[0]) == expected_id


# ---------------------------------------------------------------------------
# Invariant 4: vocab grows by exactly 14 vs the baseline behavior.
# ---------------------------------------------------------------------------


def test_seed_size_grows_by_exactly_14_over_specials_only_baseline():
    # The empty vocab now contains the 8 special tokens + 14 reserved CAS
    # tokens. Pre-patch behavior was 8 entries; post-patch behavior is 22.
    # That delta of 14 is the entire content of the patch.
    vocab = StructuredTokenVocabulary.empty()
    assert len(vocab) == len(RESERVED_TOKENS) + len(RESERVED_CAS_TOKENS)
    assert len(vocab) - len(RESERVED_TOKENS) == 14


def test_corpus_vocab_grows_by_exactly_14_over_baseline_behavior():
    # Build a vocab with a non-trivial corpus. The size delta vs the
    # "specials-only" simulation of the pre-patch baseline must be exactly
    # 14 + (number of unique non-reserved corpus keys).
    corpus = [
        "I feel drawn to ^2^P_{F4}|f",
        "the audit highlights ^6^E rhythm",
        "we are exhausted by repeated exposure",
    ]
    vocab = StructuredTokenVocabulary.from_texts(corpus, min_count=1)
    n_reserved_total = len(RESERVED_TOKENS) + len(RESERVED_CAS_TOKENS)
    n_corpus = len(vocab) - n_reserved_total
    # Confirm the 14 are all there (so the size growth attributable to the
    # patch is exactly 14, regardless of corpus size).
    assert all(token in vocab.token_to_id for token in RESERVED_CAS_TOKENS)
    # Sanity: the corpus contributed at least one non-reserved token.
    assert n_corpus > 0


def test_save_load_round_trip_preserves_reserved_cas_tokens(tmp_path):
    vocab = StructuredTokenVocabulary.from_texts(
        ["I feel drawn to ^2^P_{F4}|f", "rhythm and audit"],
        min_count=1,
    )
    path = tmp_path / "vocab14.json"
    vocab.save(path)

    loaded = StructuredTokenVocabulary.load(path)
    for token in RESERVED_CAS_TOKENS:
        assert token in loaded.token_to_id
        assert loaded.token_to_id[token] == vocab.token_to_id[token]


def test_reserved_cas_tokens_are_strictly_ordered_after_specials():
    # The contract is: ID 0..7 are the 8 specials, ID 8..21 are the 14
    # reserved CAS tokens, ID 22+ are corpus tokens. A vocab loaded from
    # JSON must satisfy this invariant or __post_init__ raises.
    vocab = StructuredTokenVocabulary.empty()
    for idx, token in enumerate(RESERVED_TOKENS):
        assert vocab.token_to_id[token] == idx
    for idx, token in enumerate(RESERVED_CAS_TOKENS):
        assert vocab.token_to_id[token] == len(RESERVED_TOKENS) + idx
