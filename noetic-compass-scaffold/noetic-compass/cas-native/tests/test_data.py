"""Tests for CASDataset and data pipeline."""

import json
import tempfile
from pathlib import Path

import pytest
import torch

from cas_native.training.data_pipeline import (
    CASDataset,
    SimpleTokenizer,
    cas_collate_fn,
    create_data_loaders,
    load_cas_data,
)


@pytest.fixture
def sample_data():
    """Sample data records."""
    return [
        {
            "prompt": "What is ethical AI?",
            "response": "Ethical AI involves principles of fairness and transparency.",
            "scores": {"nccs": 78.5, "operator_scores": [7, 8, 6, 7, 8, 7, 6, 8, 7, 7]},
        },
        {
            "prompt": "Explain domain coherence.",
            "response": "Domain coherence measures balance across processing domains.",
            "scores": {"nccs": 82.1},
        },
        {
            "prompt": "What are inversions?",
            "response": "Inversions are distortions in cognitive operator behavior.",
            "scores": {"nccs": 65.0},
        },
        {
            "prompt": "Define RPM.",
            "response": "The Realization Prerequisite Monad handles capability chains.",
            "scores": {"nccs": 71.2},
        },
        {
            "prompt": "What is CAS?",
            "response": "CAS is the Cognitive Architecture System for AI assessment.",
            "scores": {"nccs": 88.0},
        },
        {
            "prompt": "Explain the open simplex.",
            "response": "The open simplex is a probability space where all entries are positive.",
            "scores": {"nccs": 75.5},
        },
        {
            "prompt": "What are cognitive operators?",
            "response": "There are 10 cognitive operators labeled CO-0 through CO-9.",
            "scores": {"nccs": 70.0},
        },
        {
            "prompt": "Define involution pairs.",
            "response": "Involution pairs are CO-2/CO-3, CO-5/CO-6, CO-8/CO-9.",
            "scores": {"nccs": 80.0},
        },
        {
            "prompt": "What is domain descent?",
            "response": "Domain descent is the P to C to E to O information flow.",
            "scores": {"nccs": 77.0},
        },
        {
            "prompt": "Explain Fisher-Rao metric.",
            "response": "Fisher-Rao is a geodesic distance on the probability simplex.",
            "scores": {"nccs": 85.0},
        },
    ]


@pytest.fixture
def sample_json_file(sample_data, tmp_path):
    """Write sample data to a JSON file."""
    path = tmp_path / "test_data.json"
    with open(path, "w") as f:
        json.dump(sample_data, f)
    return path


class TestSimpleTokenizer:

    def test_encode(self):
        tokenizer = SimpleTokenizer()
        ids = tokenizer.encode("hello world")
        assert ids[0] == SimpleTokenizer.BOS_ID
        assert ids[-1] == SimpleTokenizer.EOS_ID
        assert len(ids) == 4  # BOS + hello + world + EOS

    def test_max_length(self):
        tokenizer = SimpleTokenizer()
        text = " ".join(["word"] * 1000)
        ids = tokenizer.encode(text, max_length=10)
        assert len(ids) <= 10


class TestCASDataset:

    def test_dataset_len(self, sample_data):
        """Dataset should have expected length."""
        dataset = CASDataset(sample_data)
        assert len(dataset) == len(sample_data)

    def test_getitem_keys(self, sample_data):
        """Each item should have expected keys."""
        dataset = CASDataset(sample_data)
        item = dataset[0]
        assert "input_ids" in item
        assert "targets" in item
        assert "attention_mask" in item
        assert "cas_scores" in item

    def test_getitem_types(self, sample_data):
        """Tensors should be long type."""
        dataset = CASDataset(sample_data)
        item = dataset[0]
        assert item["input_ids"].dtype == torch.long
        assert item["targets"].dtype == torch.long

    def test_input_target_alignment(self, sample_data):
        """Targets should be input shifted by 1."""
        dataset = CASDataset(sample_data)
        item = dataset[0]
        # targets[i] = input_ids[i+1] (teacher forcing)
        assert len(item["input_ids"]) == len(item["targets"])


class TestCollate:

    def test_collate_batch(self, sample_data):
        """Collate should produce padded batch tensors."""
        dataset = CASDataset(sample_data)
        items = [dataset[i] for i in range(min(3, len(dataset)))]
        batch = cas_collate_fn(items)

        assert "input_ids" in batch
        assert "targets" in batch
        assert "attention_mask" in batch
        assert batch["input_ids"].dim() == 2  # (batch, seq)
        assert batch["input_ids"].shape[0] == len(items)

    def test_collate_padding(self, sample_data):
        """Attention mask should have 0s where padded."""
        dataset = CASDataset(sample_data)
        items = [dataset[i] for i in range(min(3, len(dataset)))]
        batch = cas_collate_fn(items)

        # Check that mask has same shape as input_ids
        assert batch["attention_mask"].shape == batch["input_ids"].shape

    def test_collate_single_item(self, sample_data):
        """Collate should work with a single item."""
        dataset = CASDataset(sample_data)
        batch = cas_collate_fn([dataset[0]])
        assert batch["input_ids"].shape[0] == 1


class TestDataLoading:

    def test_load_cas_data(self, sample_json_file):
        """Should load data from JSON file."""
        data = load_cas_data(sample_json_file)
        assert len(data) == 10

    def test_load_cas_data_missing_file(self, tmp_path):
        """Should return empty list for missing files."""
        data = load_cas_data(tmp_path / "nonexistent.json")
        assert data == []

    def test_load_cas_data_dict_format(self, tmp_path):
        """Should handle dict with 'results' key."""
        path = tmp_path / "dict_data.json"
        with open(path, "w") as f:
            json.dump({"results": [{"prompt": "test", "response": "ok"}]}, f)
        data = load_cas_data(path)
        assert len(data) == 1


class TestSplitRatios:

    def test_split_ratios(self, sample_data):
        """Train/val/test splits should sum to total dataset size."""
        train_loader, val_loader, test_loader = create_data_loaders(
            sample_data, batch_size=2, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1
        )
        total = (
            len(train_loader.dataset)
            + len(val_loader.dataset)
            + len(test_loader.dataset)
        )
        assert total == len(sample_data)

    def test_split_approximate_ratios(self, sample_data):
        """Split sizes should approximately match requested ratios."""
        n = len(sample_data)
        train_loader, val_loader, test_loader = create_data_loaders(
            sample_data, batch_size=2, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1
        )
        train_size = len(train_loader.dataset)
        # With 10 samples: 80% = 8, 10% = 1, 10% = 1
        assert train_size == int(n * 0.8)
