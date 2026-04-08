"""
CASDataset and data pipeline for CAS-Native training.

Loads prompt-response-score triples from JSON files and prepares them
for PyTorch DataLoader consumption.

Features:
  - Load from JSON files (validation/baseline_results.json format)
  - Simple whitespace tokenizer (or HuggingFace tokenizer if available)
  - CAS scores attached as training labels
  - Train/val/test split (80/10/10)
  - Collate function for batching variable-length sequences
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

        return {
            "input_ids": input_ids,
            "targets": targets,
            "attention_mask": attention_mask,
            "cas_scores": cas_scores,
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

    return {
        "input_ids": torch.stack(padded_input_ids),
        "targets": torch.stack(padded_targets),
        "attention_mask": torch.stack(padded_masks),
        "cas_scores": cas_scores_list,
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
