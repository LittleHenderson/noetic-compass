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
    validate_cas_item,
    run_pipeline,
)
from cas_native.training.augment import (
    augment_training_item,
    augment_dataset,
    _flip_operator_scores,
    _flip_domain_averages,
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


# ---- CAS Ontology Validation ----


class TestValidation:

    def test_valid_item(self):
        item = {
            "operator_scores": [0.5] * 10,
            "domain_averages": [0.25, 0.25, 0.25, 0.25],
            "composite": 65.0,
        }
        assert validate_cas_item(item) is True

    def test_invalid_operator_count(self):
        item = {"operator_scores": [0.5] * 8}
        assert validate_cas_item(item) is False

    def test_invalid_operator_range(self):
        item = {"operator_scores": [0.5] * 9 + [1.5]}
        assert validate_cas_item(item) is False

    def test_invalid_domain_zero(self):
        """Open simplex requires all pk > 0."""
        item = {"domain_averages": [0.0, 0.5, 0.3, 0.2]}
        assert validate_cas_item(item) is False

    def test_invalid_domain_sum(self):
        item = {"domain_averages": [0.5, 0.5, 0.5, 0.5]}
        assert validate_cas_item(item) is False

    def test_invalid_composite_range(self):
        item = {"composite": 150.0}
        assert validate_cas_item(item) is False

    def test_empty_item_is_valid(self):
        """Items without scores are valid (no constraints to violate)."""
        assert validate_cas_item({}) is True


# ---- Training Data Augmentation ----


class TestAugmentation:

    @pytest.fixture
    def scored_item(self):
        return {
            "index": 0,
            "prompt": "Evaluate this ethical dilemma.",
            "operator_scores": [0.7, 0.6, 0.8, 0.5, 0.9, 0.6, 0.7, 0.5, 0.65, 0.8],
            "domain_averages": [0.28, 0.22, 0.27, 0.23],
            "drive_scores": [0.7, 0.6, 0.8, 0.5, 0.7, 0.6, 0.9],
            "composite": 72.5,
        }

    def test_augment_produces_7_variants(self, scored_item):
        results = augment_training_item(scored_item)
        assert len(results) == 7

    def test_augment_tags_with_metadata(self, scored_item):
        results = augment_training_item(scored_item)
        for r in results:
            assert "augmentation" in r
            assert "inversion_axis" in r["augmentation"]
            assert "source_index" in r["augmentation"]

    def test_n_axis_swaps_scores(self):
        scores = [0.1, 0.2, 0.8, 0.3, 0.4, 0.9, 0.5, 0.6, 0.7, 0.95]
        flipped = _flip_operator_scores(scores, "N")
        # CO-2↔CO-3 swapped
        assert flipped[2] == 0.3
        assert flipped[3] == 0.8
        # CO-5↔CO-6 swapped
        assert flipped[5] == 0.5
        assert flipped[6] == 0.9

    def test_domain_averages_w_axis_swap(self):
        avgs = [0.30, 0.20, 0.25, 0.25]
        flipped = _flip_domain_averages(avgs, "W")
        # P↔O swapped, C↔E swapped, then renormalized
        total = sum(flipped)
        assert abs(total - 1.0) < 0.01
        # After swap: original[3] should be in position 0
        assert flipped[0] > flipped[1]  # O was 0.25, swapped to P

    def test_composite_dampened(self, scored_item):
        results = augment_training_item(scored_item)
        for r in results:
            assert r["composite"] < scored_item["composite"]

    def test_augment_dataset_includes_originals(self, scored_item):
        data = [scored_item]
        augmented = augment_dataset(data)
        assert len(augmented) == 8  # 1 original + 7 variants
        assert augmented[0]["prompt"] == scored_item["prompt"]


# ---- 5-Stage Pipeline ----


class TestRunPipeline:

    def test_pipeline_with_baseline(self, tmp_path):
        """Pipeline should run end-to-end with a minimal JSON file."""
        data = [
            {
                "prompt": f"Test prompt {i}",
                "response": f"Response {i}",
                "operator_scores": [0.5 + i * 0.01] * 10,
                "domain_averages": [0.25, 0.25, 0.25, 0.25],
                "composite": 60.0 + i,
            }
            for i in range(20)
        ]
        path = tmp_path / "test_baseline.json"
        path.write_text(json.dumps({"results": data}))

        train, val, test, stats = run_pipeline(
            [str(path)], augment=False, batch_size=4
        )

        assert stats["stages"]["1_load"]["items"] == 20
        assert stats["stages"]["2_augment"]["skipped"] is True
        assert stats["stages"]["3_validate"]["valid"] == 20
        total = (
            len(train.dataset) + len(val.dataset) + len(test.dataset)
        )
        assert total == 20

    def test_pipeline_with_augmentation(self, tmp_path):
        """Pipeline with augmentation should expand the dataset."""
        data = [
            {
                "index": i,
                "prompt": f"Test prompt {i}",
                "operator_scores": [0.5] * 10,
                "domain_averages": [0.25, 0.25, 0.25, 0.25],
                "composite": 65.0,
            }
            for i in range(5)
        ]
        path = tmp_path / "test_aug.json"
        path.write_text(json.dumps({"results": data}))

        _, _, _, stats = run_pipeline(
            [str(path)], augment=True, batch_size=2
        )

        assert stats["stages"]["2_augment"]["before"] == 5
        assert stats["stages"]["2_augment"]["after"] > 5
