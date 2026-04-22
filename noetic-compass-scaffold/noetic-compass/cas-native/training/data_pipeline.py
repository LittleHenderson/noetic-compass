"""
CASDataset and data pipeline for CAS-Native training.

5-stage pipeline:
  Stage 1: Load labeled assessments (baseline JSON + optional PostgreSQL)
  Stage 2: Augment using the inversion engine (7x expansion)
  Stage 3: Validate all data against CAS ontology (open simplex, valid ranges)
  Stage 4: Split into train/val/test (80/10/10)
  Stage 5: Tokenize and prepare for PyTorch DataLoader

Features:
  - Load from JSON files (validation/baseline_results.json format)
  - Simple whitespace tokenizer (or HuggingFace tokenizer if available)
  - CAS scores attached as training labels
  - Train/val/test split (80/10/10)
  - Collate function for batching variable-length sequences
  - Inversion engine augmentation for training data expansion
  - CAS ontology validation (open simplex, score ranges)
"""

import json
from pathlib import Path
from typing import Any, Optional

import torch
from torch.utils.data import Dataset, DataLoader, random_split


class SimpleTokenizer:
    """Simple whitespace tokenizer for when HuggingFace is not available.

    Maps words to integer IDs. Includes special tokens:
      0 = [PAD], 1 = [UNK], 2 = [BOS], 3 = [EOS]
    """

    PAD_ID = 0
    UNK_ID = 1
    BOS_ID = 2
    EOS_ID = 3

    def __init__(self, vocab_size: int = 32000):
        self.vocab_size = vocab_size
        self.word2id: dict[str, int] = {
            "[PAD]": self.PAD_ID,
            "[UNK]": self.UNK_ID,
            "[BOS]": self.BOS_ID,
            "[EOS]": self.EOS_ID,
        }
        self._next_id = 4

    def _get_or_add(self, word: str) -> int:
        """Get word ID, adding it to vocabulary if new."""
        if word not in self.word2id:
            if self._next_id < self.vocab_size:
                self.word2id[word] = self._next_id
                self._next_id += 1
            else:
                return self.UNK_ID
        return self.word2id[word]

    def encode(self, text: str, max_length: int = 512) -> list[int]:
        """Tokenize text into a list of integer IDs."""
        words = text.lower().split()
        ids = [self.BOS_ID]
        for w in words[: max_length - 2]:
            ids.append(self._get_or_add(w))
        ids.append(self.EOS_ID)
        return ids

    def pad_id(self) -> int:
        return self.PAD_ID


class CASDataset(Dataset):
    """Dataset for CAS-Native training.

    Each item contains:
      - input_ids: Tokenized prompt (as tensor)
      - targets: Tokenized response shifted by 1 (as tensor)
      - cas_scores: Dict of CAS scores (operators, domains, drives, etc.)
      - attention_mask: Binary mask (1 for real tokens, 0 for padding)
    """

    def __init__(
        self,
        data: list[dict[str, Any]],
        tokenizer: Optional[SimpleTokenizer] = None,
        max_length: int = 512,
    ):
        self.data = data
        self.tokenizer = tokenizer or SimpleTokenizer()
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        item = self.data[idx]

        # Get prompt and response text
        prompt = item.get("prompt", item.get("text", ""))
        response = item.get("response", item.get("output", ""))

        # Tokenize: combine prompt + response
        combined = f"{prompt} {response}".strip()
        if not combined:
            combined = "empty"
        token_ids = self.tokenizer.encode(combined, max_length=self.max_length)

        # Input: all tokens except last; Target: all tokens except first
        input_ids = torch.tensor(token_ids[:-1], dtype=torch.long)
        targets = torch.tensor(token_ids[1:], dtype=torch.long)

        # Attention mask (all real tokens)
        attention_mask = torch.ones(len(input_ids), dtype=torch.long)

        # CAS scores (if available)
        cas_scores = {}
        if "scores" in item:
            cas_scores = item["scores"]
        elif "operator_scores" in item:
            cas_scores["operator_scores"] = item["operator_scores"]
        if "domain_scores" in item:
            cas_scores["domain_scores"] = item["domain_scores"]
        if "nccs" in item:
            cas_scores["nccs"] = item["nccs"]

        # v2 label streams (ADR-01 / ADR-02 / ADR-04). All optional; absent
        # fields default to empty list / None so per-example masking applies.
        register_labels = item.get("register_labels", [])
        omega_labels = item.get("omega_labels", [])
        production_target = item.get("production_target", None)

        return {
            "input_ids": input_ids,
            "targets": targets,
            "attention_mask": attention_mask,
            "cas_scores": cas_scores,
            "register_labels": register_labels,
            "omega_labels": omega_labels,
            "production_target": production_target,
        }


def cas_collate_fn(batch: list[dict[str, Any]]) -> dict[str, Any]:
    """Collate function that pads variable-length sequences.

    Pads input_ids, targets, and attention_mask to the maximum
    sequence length in the batch.
    """
    # Find max length in batch
    max_len = max(item["input_ids"].size(0) for item in batch)

    padded_input_ids = []
    padded_targets = []
    padded_masks = []
    cas_scores_list = []
    register_labels_list = []
    omega_labels_list = []
    production_targets_list = []

    pad_id = 0  # [PAD] token ID

    for item in batch:
        seq_len = item["input_ids"].size(0)
        pad_len = max_len - seq_len

        # Pad input_ids
        padded_input_ids.append(
            torch.cat([item["input_ids"], torch.full((pad_len,), pad_id, dtype=torch.long)])
        )

        # Pad targets (pad with -100 for ignored positions in loss)
        padded_targets.append(
            torch.cat([item["targets"], torch.full((pad_len,), -100, dtype=torch.long)])
        )

        # Pad attention mask
        padded_masks.append(
            torch.cat([item["attention_mask"], torch.zeros(pad_len, dtype=torch.long)])
        )

        cas_scores_list.append(item["cas_scores"])
        register_labels_list.append(item.get("register_labels", []))
        omega_labels_list.append(item.get("omega_labels", []))
        production_targets_list.append(item.get("production_target", None))

    return {
        "input_ids": torch.stack(padded_input_ids),
        "targets": torch.stack(padded_targets),
        "attention_mask": torch.stack(padded_masks),
        "cas_scores": cas_scores_list,
        "register_labels": register_labels_list,
        "omega_labels": omega_labels_list,
        "production_target": production_targets_list,
    }


def load_cas_data(
    json_path: str | Path,
) -> list[dict[str, Any]]:
    """Load CAS data from a JSON file.

    Supports both:
      - List of records: [{"prompt": ..., "response": ..., "scores": ...}, ...]
      - Dict with "results" key: {"results": [...]}
    """
    path = Path(json_path)
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, list):
        return raw
    elif isinstance(raw, dict) and "results" in raw:
        return raw["results"]
    elif isinstance(raw, dict):
        # Single record
        return [raw]
    return []


def create_data_loaders(
    data: list[dict[str, Any]],
    batch_size: int = 8,
    max_length: int = 512,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
) -> tuple[DataLoader, DataLoader, DataLoader]:
    """Create train/val/test DataLoaders with specified split ratios.

    Args:
        data: List of data records
        batch_size: Batch size for all loaders
        max_length: Maximum sequence length
        train_ratio: Fraction for training (default 0.8)
        val_ratio: Fraction for validation (default 0.1)
        test_ratio: Fraction for test (default 0.1)
        seed: Random seed for reproducible splits

    Returns:
        Tuple of (train_loader, val_loader, test_loader)
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        f"Ratios must sum to 1.0, got {train_ratio + val_ratio + test_ratio}"

    dataset = CASDataset(data, max_length=max_length)

    # Compute split sizes
    total = len(dataset)
    train_size = int(total * train_ratio)
    val_size = int(total * val_ratio)
    test_size = total - train_size - val_size  # Remainder goes to test

    # Split
    generator = torch.Generator().manual_seed(seed)
    train_ds, val_ds, test_ds = random_split(
        dataset, [train_size, val_size, test_size], generator=generator
    )

    # Create loaders
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True, collate_fn=cas_collate_fn
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False, collate_fn=cas_collate_fn
    )
    test_loader = DataLoader(
        test_ds, batch_size=batch_size, shuffle=False, collate_fn=cas_collate_fn
    )

    return train_loader, val_loader, test_loader


# ---- 5-Stage Pipeline ----


def validate_cas_item(item: dict[str, Any]) -> bool:
    """Stage 3: Validate a single data item against CAS ontology.

    Checks:
    - operator_scores: 10 values in [0, 1]
    - domain_averages: 4 values, all > 0, sum ≈ 1.0 (open simplex)
    - composite: in [0, 100]
    """
    ops = item.get("operator_scores", [])
    if ops:
        if len(ops) != 10:
            return False
        if not all(0.0 <= s <= 1.0 for s in ops):
            return False

    doms = item.get("domain_averages", [])
    if doms:
        if len(doms) != 4:
            return False
        if not all(d > 0 for d in doms):
            return False
        total = sum(doms)
        if abs(total - 1.0) > 0.01:
            return False

    comp = item.get("composite")
    if comp is not None:
        if not (0.0 <= comp <= 100.0):
            return False

    return True


def run_pipeline(
    json_paths: list[str | Path],
    augment: bool = True,
    batch_size: int = 8,
    max_length: int = 512,
    seed: int = 42,
) -> tuple[DataLoader, DataLoader, DataLoader, dict[str, Any]]:
    """Run the full 5-stage CAS-Native data pipeline.

    Args:
        json_paths: List of JSON file paths to load (baseline_results, etc.)
        augment: Whether to apply inversion engine augmentation (Stage 2)
        batch_size: Batch size for DataLoaders
        max_length: Maximum token sequence length
        seed: Random seed for reproducible splits

    Returns:
        Tuple of (train_loader, val_loader, test_loader, stats)
    """
    stats: dict[str, Any] = {"stages": {}}

    # Stage 1: Load
    all_data: list[dict[str, Any]] = []
    for path in json_paths:
        loaded = load_cas_data(path)
        all_data.extend(loaded)
    stats["stages"]["1_load"] = {"items": len(all_data), "sources": len(json_paths)}

    if not all_data:
        raise ValueError("No data loaded from any source")

    # Stage 2: Augment (optional)
    if augment:
        from cas_native.training.augment import augment_dataset

        pre_augment = len(all_data)
        all_data = augment_dataset(all_data)
        stats["stages"]["2_augment"] = {
            "before": pre_augment,
            "after": len(all_data),
            "multiplier": round(len(all_data) / max(pre_augment, 1), 1),
        }
    else:
        stats["stages"]["2_augment"] = {"skipped": True}

    # Stage 3: Validate
    valid_data = [item for item in all_data if validate_cas_item(item)]
    rejected = len(all_data) - len(valid_data)
    stats["stages"]["3_validate"] = {
        "valid": len(valid_data),
        "rejected": rejected,
    }

    if not valid_data:
        raise ValueError("No valid data after CAS ontology validation")

    # Stage 4 + 5: Split and tokenize (via create_data_loaders)
    train_loader, val_loader, test_loader = create_data_loaders(
        valid_data,
        batch_size=batch_size,
        max_length=max_length,
        seed=seed,
    )
    stats["stages"]["4_split"] = {
        "train": len(train_loader.dataset),
        "val": len(val_loader.dataset),
        "test": len(test_loader.dataset),
    }
    stats["stages"]["5_tokenize"] = {
        "max_length": max_length,
        "batch_size": batch_size,
    }
    stats["total_items"] = len(valid_data)

    return train_loader, val_loader, test_loader, stats
