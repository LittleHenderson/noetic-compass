"""Tests for grammar-constrained CAS inference sampling."""

import pytest

from api.notation import compile_expression
from cas_native.inference.constrained_sampling import (
    BUCKETS,
    CandidateTrieConstraint,
    build_candidate_expressions,
    build_dataset_candidate_expressions,
)
from cas_native.training.tokenizer import HybridCASTokenizer


def test_candidate_banks_are_nonempty_and_compiler_valid():
    for bucket in BUCKETS:
        expressions = build_candidate_expressions(bucket, 50)

        assert expressions, bucket
        for expr in expressions[:10]:
            assert compile_expression(expr).valid, (bucket, expr)


def test_dataset_candidate_bank_filters_by_bucket_and_compile_validity():
    records = [
        {"_meta": {"bucket": "v75_register"}, "cas_expression": "^2^P_{F2}|A"},
        {"_meta": {"bucket": "v75_register"}, "cas_expression": "^2^P_{F2}|A"},
        {"_meta": {"bucket": "v75_register"}, "cas_expression": "^2, ^3}"},
        {"_meta": {"bucket": "meta_logic"}, "cas_expression": "^2 ∈ Noetics"},
    ]

    candidates = build_dataset_candidate_expressions(
        records,
        "v75_register",
        max_candidates=10,
        include_builtin=False,
    )

    assert candidates == ("^2^P_{F2}|A",)


def test_trie_constraint_allows_only_candidate_prefixes_and_terminal_eos():
    expr = build_candidate_expressions("v76_production", 10)[0]
    tokenizer = HybridCASTokenizer.from_texts([expr])
    constraint = CandidateTrieConstraint(tokenizer, "v76_production", candidates=[expr])
    token_ids = tokenizer.encode(expr, add_special=False)

    for idx, token_id in enumerate(token_ids):
        decision = constraint.decision(token_ids[:idx])
        assert decision.valid_prefix
        assert token_id in decision.allowed_token_ids
        assert not decision.allow_eos

    terminal = constraint.decision(token_ids)
    assert terminal.valid_prefix
    assert terminal.allow_eos

    bad_prefix = [tokenizer.word2id[","]]
    dead = constraint.decision(bad_prefix)
    assert not dead.valid_prefix
    assert dead.state == "dead_end"
    assert not dead.allowed_token_ids


def test_constraint_detects_compatible_and_incompatible_primers():
    expr = "(^3^P_{F2}|A × ^3^P_{F2}|f) = ^3^P|Ω_refusal"
    tokenizer = HybridCASTokenizer.from_texts([expr, "^N^D_{F"])
    constraint = CandidateTrieConstraint(tokenizer, "v77_omega", candidates=[expr])

    assert constraint.is_compatible_primer("(")
    assert constraint.is_compatible_primer("(^3^P_{F2}|A × ")
    assert not constraint.is_compatible_primer("^N^D_{F")


def test_sample_token_applies_allowed_ids_before_top_p():
    torch = pytest.importorskip("torch")
    pytest.importorskip("torch.nn")
    from cas_native.inference.generate_samples import sample_token

    expr = build_candidate_expressions("meta_logic", 10)[0]
    tokenizer = HybridCASTokenizer.from_texts([expr])
    constraint = CandidateTrieConstraint(tokenizer, "meta_logic", candidates=[expr])
    first_id = next(iter(constraint.decision([]).allowed_token_ids))
    comma_id = tokenizer.word2id[","]

    logits = torch.full((tokenizer.vocab_size,), -100.0)
    logits[comma_id] = 100.0
    logits[first_id] = -50.0

    chosen = sample_token(
        logits,
        temperature=1.0,
        top_p=0.9,
        tokenizer=tokenizer,
        allowed_token_ids={first_id},
    )

    assert chosen == first_id
