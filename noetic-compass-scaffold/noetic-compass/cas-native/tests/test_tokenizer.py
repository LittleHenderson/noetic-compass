"""Tests for the CAS-aware frozen tokenizer."""

import json

import pytest

from cas_native.training.tokenizer import HybridCASTokenizer, tokenizer_from_loader


CAS_EXPRESSIONS = [
    "^2^P_{F2}|A",
    "NoeticCluster{^2, ^7} ⊆ Noetics",
    "Θ(Ω_safe_judgment) = 0.40·^3^P_{F2}|A + 0.25·^2^C_{F3}|f → Ω_safe_judgment",
    "(^3^P_{F2}|A × ^3^P_{F2}|f × ^3^P_{F2}|T) = ^3^P|Ω_unified_refusal",
    "Product(Noetics, Domains)",
    "Φ<3:8:5:2>",
]


def test_hybrid_tokenizer_preserves_cas_roundtrip():
    tokenizer = HybridCASTokenizer.from_texts(CAS_EXPRESSIONS)

    for expr in CAS_EXPRESSIONS:
        ids = tokenizer.encode(expr)
        decoded = tokenizer.decode(ids)

        assert tokenizer.UNK_ID not in ids
        assert decoded == expr


def test_hybrid_tokenizer_freeze_prevents_vocab_mutation_with_char_fallback():
    tokenizer = HybridCASTokenizer.from_texts(["Known prompt ^2^P_{F2}|A"])
    before = tokenizer.vocab_size

    ids = tokenizer.encode("UnseenWord ^7^O_{F6}|T")
    decoded = tokenizer.decode(ids)

    assert tokenizer.vocab_size == before
    assert tokenizer.UNK_ID not in ids
    assert decoded == "UnseenWord ^7^O_{F6}|T"


def test_hybrid_tokenizer_persists_id_contract():
    tokenizer = HybridCASTokenizer.from_texts(CAS_EXPRESSIONS)
    payload = tokenizer.to_dict()

    loaded = HybridCASTokenizer(
        token_to_id=payload["token_to_id"],
        frozen=payload["frozen"],
    )

    assert loaded.word2id == tokenizer.word2id
    assert loaded.metadata()["hash"] == tokenizer.metadata()["hash"]
    assert loaded.decode(loaded.encode(CAS_EXPRESSIONS[1])) == CAS_EXPRESSIONS[1]


def test_create_data_loaders_uses_frozen_cas_tokenizer():
    pytest.importorskip("torch.utils.data")
    from cas_native.training.data_pipeline import create_data_loaders

    data = [
        {
            "prompt": "Compile the expression.",
            "response": "Use ^2^P_{F2}|A.",
            "cas_expression": "^2^P_{F2}|A",
        },
        {
            "prompt": "Show a cluster.",
            "response": "Use NoeticCluster{^2, ^7} ⊆ Noetics.",
            "cas_expression": "NoeticCluster{^2, ^7} ⊆ Noetics",
        },
        {
            "prompt": "Show production.",
            "response": "Use Θ(Ω_focus) = 0.5·^1^C_{F1}|A → Ω_focus.",
            "cas_expression": "Θ(Ω_focus) = 0.5·^1^C_{F1}|A → Ω_focus",
        },
    ]

    train, _, _ = create_data_loaders(
        data,
        batch_size=1,
        train_ratio=1.0,
        val_ratio=0.0,
        test_ratio=0.0,
    )
    tokenizer = tokenizer_from_loader(train)
    before = tokenizer.vocab_size

    first_batch = next(iter(train))

    assert isinstance(tokenizer, HybridCASTokenizer)
    assert tokenizer.frozen is True
    assert tokenizer.vocab_size == before
    assert first_batch["input_ids"].max().item() < tokenizer.vocab_size


def test_run_pipeline_reports_tokenizer_gate_stats(tmp_path):
    pytest.importorskip("torch.utils.data")
    from cas_native.training.data_pipeline import run_pipeline

    records = []
    for i in range(12):
        records.append(
            {
                "prompt": f"Prompt {i}",
                "response": f"Response {i} ^{i % 10}^P_{{F1}}|A",
                "operator_scores": [0.1] * 10,
                "domain_averages": [0.25, 0.25, 0.25, 0.25],
                "cas_expression": f"^{i % 10}^P_{{F1}}|A",
            }
        )
    path = tmp_path / "data.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")

    _, _, _, stats = run_pipeline([path], augment=False, batch_size=2)

    tok_stats = stats["stages"]["5_tokenize"]["tokenizer"]
    assert tok_stats["type"] == "HybridCASTokenizer"
    assert tok_stats["vocab_size"] > 0
    assert stats["stages"]["5_tokenize"]["cas_expression_unk_rate"] == 0.0
