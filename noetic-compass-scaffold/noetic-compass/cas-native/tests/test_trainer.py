"""Semantic tests for CASTrainer supervision behavior."""

import pytest
import torch
from torch.utils.data import DataLoader

from cas_native.model.cas_native_model import CASNativeModel, CASNativeConfig
from cas_native.training.data_pipeline import CASDataset, cas_collate_fn
from cas_native.training.trainer import CASTrainer


@pytest.fixture
def trainer():
    config = CASNativeConfig(
        d_model=32,
        n_layers=1,
        n_heads=4,
        vocab_size=128,
        max_seq_len=32,
        fractal_depth=1,
        num_ethical_propositions=3,
    )
    model = CASNativeModel(config)
    dataset = CASDataset(
        [{"prompt": "p", "response": "r", "scores": {"operator_scores": [1] * 10}}],
        max_length=16,
    )
    loader = DataLoader(dataset, batch_size=1, collate_fn=cas_collate_fn)
    return CASTrainer(model, loader, loader, config={"max_steps": 1})


class TestCASTrainer:

    def test_target_cognitive_state_uses_cas_labels(self, trainer):
        """Different CAS labels should produce different target simplex states."""
        seq_len = 4
        target_a = trainer._generate_target_cognitive_state(
            [{"operator_scores": [10, 1, 1, 1, 1, 1, 1, 1, 1, 1]}],
            seq_len=seq_len,
        )
        target_b = trainer._generate_target_cognitive_state(
            [{"operator_scores": [1, 10, 1, 1, 1, 1, 1, 1, 1, 1]}],
            seq_len=seq_len,
        )

        assert target_a.shape == (1, seq_len, 40)
        assert target_b.shape == (1, seq_len, 40)
        assert not torch.allclose(target_a, target_b)
        assert torch.allclose(target_a.sum(dim=-1), torch.ones_like(target_a.sum(dim=-1)))

    def test_target_cognitive_state_falls_back_to_uniform_without_labels(self, trainer):
        """Missing structured labels should still produce a valid uniform simplex target."""
        target = trainer._generate_target_cognitive_state([{}], seq_len=3)
        expected = torch.ones(1, 3, 40, device=trainer.device) / 40.0
        assert torch.allclose(target, expected)
