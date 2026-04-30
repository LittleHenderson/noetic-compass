"""Tests for the CAS-Native backbone structured-prediction adapter."""

from __future__ import annotations

import torch

from cas_native.model import (
    DOMAIN_LABELS,
    DRIVE_LABELS,
    EXPRESSION_FAMILY_LABELS,
    REGISTER_LABELS,
    REGISTER_MODE_LABELS,
    TRANSITION_KIND_LABELS,
    TURN_TYPE_LABELS,
    AUTHORITY_LABELS,
    META_RELATION_LABELS,
    CASNativeConfig,
    CASNativeModel,
    StructuredPredictionHead,
    structured_prediction_loss,
)
from cas_native.training.structured_backbone_adapter import (
    CASBackboneStructuredPredictor,
    pooled_backbone_hidden_states,
    records_to_backbone_batch,
)
from cas_native.training.structured_prediction_ingest import batch_targets_from_records
from cas_native.training.tokenizer import HybridCASTokenizer


def _records():
    return [
        {
            "id": "v75",
            "bucket": "v75_register",
            "cas_expression": "^2^C_{F4}|f",
            "user_prompt": "Noetic 2 in cognitive domain with drive F4 and affective register.",
        },
        {
            "id": "v76",
            "bucket": "v76_production",
            "cas_expression": (
                "\u0398(\u03a9_focus) = 0.40*^3^P_{F2}|A + "
                "0.60*^7^O_{F5}|E \u2192 \u03a9_focus"
            ),
            "user_prompt": "Recipe target Omega focus from Noetic 3 P F2 A and Noetic 7 O F5 E.",
        },
    ]


def _tokenizer(records):
    return HybridCASTokenizer.from_texts(
        [str(record["user_prompt"]) for record in records],
        freeze=True,
    )


def _backbone(vocab_size: int, d_model: int = 32) -> CASNativeModel:
    config = CASNativeConfig(
        d_model=d_model,
        n_layers=1,
        n_heads=4,
        vocab_size=vocab_size,
        max_seq_len=64,
        fractal_depth=1,
        num_ethical_propositions=3,
        dropout=0.0,
    )
    return CASNativeModel(config)


def test_records_to_backbone_batch_tokenizes_prompts_only():
    records = _records()
    tokenizer = _tokenizer(records)

    batch = records_to_backbone_batch(records, tokenizer, max_length=32)

    assert batch.input_ids.shape[0] == 2
    assert batch.attention_mask.shape == batch.input_ids.shape
    assert batch.attention_mask.sum().item() > 0


def test_backbone_exposes_pooled_hidden_states():
    records = _records()
    tokenizer = _tokenizer(records)
    batch = records_to_backbone_batch(records, tokenizer, max_length=32)
    backbone = _backbone(tokenizer.vocab_size)

    with torch.no_grad():
        pooled = pooled_backbone_hidden_states(backbone, batch)

    assert pooled.shape == (2, backbone.config.d_model)


def test_backbone_structured_predictor_output_shapes_and_loss():
    records = _records()
    tokenizer = _tokenizer(records)
    batch = records_to_backbone_batch(records, tokenizer, max_length=32)
    backbone = _backbone(tokenizer.vocab_size)
    head = StructuredPredictionHead(d_model=backbone.config.d_model, bottleneck_dim=16)
    model = CASBackboneStructuredPredictor(backbone, head)
    targets = batch_targets_from_records(records)

    outputs = model(batch.input_ids, attention_mask=batch.attention_mask)
    loss = structured_prediction_loss(outputs, targets)
    loss.backward()

    assert outputs["turn_type_logits"].shape == (2, len(TURN_TYPE_LABELS))
    assert outputs["expression_family_logits"].shape == (2, len(EXPRESSION_FAMILY_LABELS))
    assert outputs["transition_kind_logits"].shape == (2, len(TRANSITION_KIND_LABELS))
    assert outputs["domain_logits"].shape == (2, len(DOMAIN_LABELS))
    assert outputs["drive_logits"].shape == (2, len(DRIVE_LABELS))
    assert outputs["register_logits"].shape == (2, len(REGISTER_LABELS))
    assert outputs["register_mode_logits"].shape == (2, len(REGISTER_MODE_LABELS))
    assert outputs["authority_logits"].shape == (2, len(AUTHORITY_LABELS))
    assert outputs["meta_relation_logits"].shape == (2, len(META_RELATION_LABELS))
    assert outputs["pooled_hidden_state"].shape == (2, backbone.config.d_model)
    assert loss.item() > 0.0
    assert any(param.grad is not None for param in model.head.parameters())


def test_backbone_can_be_frozen_for_head_only_training():
    records = _records()
    tokenizer = _tokenizer(records)
    batch = records_to_backbone_batch(records, tokenizer, max_length=32)
    backbone = _backbone(tokenizer.vocab_size)
    model = CASBackboneStructuredPredictor(backbone, freeze_backbone=True)
    targets = batch_targets_from_records(records)

    outputs = model(batch.input_ids, attention_mask=batch.attention_mask)
    loss = structured_prediction_loss(outputs, targets)
    loss.backward()

    assert all(param.grad is None for param in model.backbone.parameters())
    assert any(param.grad is not None for param in model.head.parameters())
