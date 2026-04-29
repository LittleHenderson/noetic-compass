"""Tests for grammar-constrained CAS inference sampling."""

import pytest

from api.notation import compile_expression
from cas_native.inference.constrained_sampling import (
    BUCKETS,
    CandidateTrieConstraint,
    build_candidate_expressions,
    build_dataset_candidate_expressions,
    classify_expression_family,
    expression_families,
    filter_candidates_for_prompt,
    infer_prompt_families,
    infer_prompt_required_terms,
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


def test_expression_family_classifier_covers_major_structures():
    assert classify_expression_family("\u0398(\u03a9_safe_judgment) = 0.5*^2^P_{F2}|A \u2192 \u03a9_safe_judgment") == "production"
    assert classify_expression_family("(^3^P_{F2}|A \u00d7 ^3^P_{F2}|f) = ^3^P|\u03a9_refusal") == "omega_integration"
    assert classify_expression_family("^3^P_{F2}|A + ^3^P_{F2}|f") == "register_copresence"
    assert classify_expression_family("Product(Noetics, Domains)") == "product"
    assert classify_expression_family("Coordinate{^6, P, F2, T}") == "coordinate"
    assert classify_expression_family("NoeticCluster{^2, ^7} \u2286 Noetics") == "subset"
    assert "state_cluster_literal" in expression_families("StateCluster{^2^P, ^7^O}")


def test_prompt_family_inference_for_meta_logic_examples():
    assert infer_prompt_families("Describe a typed coordinate with noetic, domain, foundation, and register axes.", "meta_logic") == ("coordinate",)
    assert infer_prompt_families("Explain how two finite StateCluster terms combine under \u222a.", "meta_logic") == ("set_union", "set_operation", "state_cluster")
    assert infer_prompt_families("Describe a finite-meet Pullback expression in this admitted CAS fragment.", "meta_logic") == ("pullback",)


def test_prompt_family_inference_does_not_match_cover_inside_discovering():
    assert infer_prompt_families(
        "A programmer discovering a security flaw is asked to give their perspective.",
        "v74_baseline",
    ) == ("v74_state", "v74_composition", "fractal", "rpm")


def test_prompt_family_filter_selects_requested_candidate_shape():
    candidates = (
        "Product(Noetics, Domains)",
        "Coordinate{^6, P, F2, T}",
        "NoeticCluster{^2, ^7} \u2286 Noetics",
        "StateCluster{^1^P, ^2^C} \u222a StateCluster{^3^O}",
    )

    filtered, diagnostics = filter_candidates_for_prompt(
        candidates,
        "Describe a typed coordinate with noetic, domain, foundation, and register axes.",
        "meta_logic",
    )

    assert filtered == ("Coordinate{^6, P, F2, T}",)
    assert diagnostics["prompt_families"] == ["coordinate"]
    assert diagnostics["pre_filter_candidate_count"] == 4
    assert diagnostics["post_filter_candidate_count"] == 1


def test_prompt_required_terms_filter_anchors_omega_name():
    candidates = (
        "(^1^E_{F3}|A \u00d7 ^1^E_{F3}|f) = ^1^E|\u03a9_clarity",
        "(^9^E_{F1}|E \u00d7 ^9^E_{F1}|f) = ^9^E|\u03a9_landing",
    )

    assert infer_prompt_required_terms("Describe a situation in which the emergent register Omega_clarity arises.") == ("omega_clarity",)
    filtered, diagnostics = filter_candidates_for_prompt(
        candidates,
        "Describe a situation in which the emergent register Omega_clarity arises.",
        "v77_omega",
    )

    assert filtered == (candidates[0],)
    assert diagnostics["prompt_required_terms"] == ["omega_clarity"]


def test_prompt_filter_falls_back_when_no_candidate_survives():
    candidates = ("Product(Noetics, Domains)",)

    filtered, diagnostics = filter_candidates_for_prompt(
        candidates,
        "Describe a typed coordinate with noetic, domain, foundation, and register axes.",
        "meta_logic",
    )

    assert filtered == candidates
    assert diagnostics["family_filter_fallback"] is True


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
