"""Tests for the CAS Transformer structured-prediction head."""

from __future__ import annotations

import torch

from cas_native.model.structured_prediction import (
    AUTHORITY_LABELS,
    DOMAIN_LABELS,
    DRIVE_LABELS,
    EXPRESSION_FAMILY_LABELS,
    META_RELATION_LABELS,
    REGISTER_LABELS,
    REGISTER_MODE_LABELS,
    TRANSITION_KIND_LABELS,
    TURN_TYPE_LABELS,
    StructuredPredictionHead,
    structured_prediction_loss,
)


def test_forward_shapes_for_pooled_hidden_states():
    head = StructuredPredictionHead(d_model=32, bottleneck_dim=16)
    outputs = head(torch.randn(3, 32))

    assert outputs["turn_type_logits"].shape == (3, len(TURN_TYPE_LABELS))
    assert outputs["expression_family_logits"].shape == (
        3,
        len(EXPRESSION_FAMILY_LABELS),
    )
    assert outputs["transition_kind_logits"].shape == (
        3,
        len(TRANSITION_KIND_LABELS),
    )
    assert outputs["noetic_logits"].shape == (3, 10)
    assert outputs["domain_logits"].shape == (3, len(DOMAIN_LABELS))
    assert outputs["drive_logits"].shape == (3, len(DRIVE_LABELS))
    assert outputs["register_logits"].shape == (3, len(REGISTER_LABELS))
    assert outputs["register_mode_logits"].shape == (3, len(REGISTER_MODE_LABELS))
    assert outputs["meta_relation_logits"].shape == (3, len(META_RELATION_LABELS))
    assert outputs["authority_logits"].shape == (3, len(AUTHORITY_LABELS))
    assert outputs["omega_logits"].shape == (3, 2)
    assert outputs["meta_logic_logits"].shape == (3, 2)


def test_forward_pools_sequence_hidden_states_with_mask():
    head = StructuredPredictionHead(d_model=24, bottleneck_dim=12)
    hidden = torch.randn(2, 5, 24)
    mask = torch.tensor([[1, 1, 1, 0, 0], [1, 1, 1, 1, 1]])

    outputs = head(hidden, attention_mask=mask)

    assert outputs["turn_type_logits"].shape == (2, len(TURN_TYPE_LABELS))


def test_loss_backpropagates_through_all_heads():
    head = StructuredPredictionHead(d_model=32, bottleneck_dim=16)
    hidden = torch.randn(4, 32)
    outputs = head(hidden)
    targets = {
        "turn_type": torch.tensor([0, 1, 2, 3]),
        "expression_family": torch.tensor([0, 1, 2, 3]),
        "transition_kind": torch.tensor([0, 1, 2, 3]),
        "noetic": torch.tensor([0, 1, 2, 3]),
        "domain": torch.tensor([0, 1, 2, 3]),
        "drive": torch.tensor([0, 1, 2, 3]),
        "register_mode": torch.tensor([0, 1, 2, 3]),
        "authority": torch.tensor([0, 1, 2, 0]),
        "has_omega": torch.tensor([0, 1, 0, 1]),
        "has_meta_logic": torch.tensor([0, 0, 1, 1]),
        "registers": torch.zeros(4, len(REGISTER_LABELS)),
        "meta_relations": torch.zeros(4, len(META_RELATION_LABELS)),
    }
    targets["registers"][:, 1] = 1.0
    targets["meta_relations"][:, 2] = 1.0

    loss = structured_prediction_loss(outputs, targets)
    loss.backward()

    assert loss.item() > 0
    assert all(param.grad is not None for param in head.parameters())


def test_propose_returns_discrete_structured_predictions():
    head = StructuredPredictionHead(d_model=16, bottleneck_dim=8)
    proposals = head.propose(torch.randn(2, 16))

    assert len(proposals) == 2
    assert proposals[0].turn_type in TURN_TYPE_LABELS
    assert proposals[0].expression_family in EXPRESSION_FAMILY_LABELS
    assert proposals[0].transition_kind in TRANSITION_KIND_LABELS
    assert 0 <= proposals[0].noetic <= 9
    assert proposals[0].domain in DOMAIN_LABELS
    assert proposals[0].drive in DRIVE_LABELS
    assert proposals[0].registers
