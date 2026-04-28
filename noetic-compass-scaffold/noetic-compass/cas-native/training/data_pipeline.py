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
  - CAS-aware frozen tokenizer for symbolic CAS + prose
  - CAS scores attached as training labels
  - Train/val/test split (80/10/10)
  - Collate function for batching variable-length sequences
  - Inversion engine augmentation for training data expansion
  - CAS ontology validation (open simplex, score ranges)

Wave 8A Agent 36 — compiler-sourced Phenomenological Register activations.
When an example carries a ``cas_expression`` string field, the dataset
compiles the expression via ``api.notation.compile_expression`` and uses
``extract_register_activations`` on the parsed AST to produce a
``list[RegisterActivation]`` per example. Examples without a
``cas_expression`` but with ``register_labels`` fall back to building
equivalent ``RegisterActivation`` records from the raw label dicts so the
trainer path is uniform. The ``register_activations_batch`` field in the
collated batch is the single source of truth the trainer consumes; the
original ``register_labels`` list is retained for backward compatibility
with earlier callers that bypass the compiler.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import torch
from torch.utils.data import Dataset, DataLoader, random_split

from cas_native.training.level3_conversation_ingest import (
    conversation_text as _conversation_text,
    domain_targets_as_list as _domain_targets_as_list,
    score_payload as _score_payload,
)
from cas_native.training.tokenizer import (
    HybridCASTokenizer,
    SimpleTokenizer,
    TokenizerLike,
    build_tokenizer_from_records,
    tokenizer_from_loader,
)

# The notation compiler lives in the sibling `api/notation/` package.
# Conftest / scaffold setup places `noetic-compass/` on sys.path so this
# import resolves without editable installs. Import-time failure is caught
# and the compiler-sourced path silently degrades to the label-only fallback
# so callers that never set a `cas_expression` field continue to work.
try:
    from cas_native.model.meta_logic_constructs import (
        classify_expression,
        construct_tokens,
    )
except Exception:  # pragma: no cover - import alias unavailable in script mode
    classify_expression = None  # type: ignore[assignment]
    construct_tokens = None  # type: ignore[assignment]

try:
    from api.notation import (
        RegisterActivation,
        VALID_REGISTERS,
        compile_expression,
        extract_register_activations,
    )

    _COMPILER_AVAILABLE = True
except Exception:  # pragma: no cover - defensive; compiler is expected to import
    RegisterActivation = None  # type: ignore[assignment]
    VALID_REGISTERS = ("T", "A", "f", "E")
    compile_expression = None  # type: ignore[assignment]
    extract_register_activations = None  # type: ignore[assignment]
    _COMPILER_AVAILABLE = False


def build_register_activations_from_labels(
    register_labels: list[dict[str, Any]],
    omega_labels: Optional[list[dict[str, Any]]] = None,
) -> list[Any]:
    """Fallback path: construct ``list[RegisterActivation]`` from raw label dicts.

    Matches the same emit order and field semantics as
    ``api.notation.extract_register_activations`` so trainer code is
    agnostic to whether the activations originated from a compiled CAS
    expression or from a hand-authored ``register_labels`` list.

    Emission order per position (deterministic by sorted position):
      1. One :class:`RegisterActivation` per (position, register) pair in
         ``register_labels`` (single-register single-element frozenset,
         ``is_register_set=False``, ``emergent_name`` attached from the
         matching ``omega_labels`` entry if any).
      2. One trailing :class:`RegisterActivation` per position that has a
         matching ``omega_labels`` entry AND at least 2 distinct registers
         at that position, carrying the union frozenset and the omega name
         (mirrors the trailing emergent record emitted by the compiler for
         a named ``= ^n^D|Ω_name`` assignment).

    Returns an empty list if the compiler is unavailable at import time and
    the `RegisterActivation` type has not been loaded — in that case the
    trainer's legacy fallback path handles the batch via raw label dicts.
    """
    if not _COMPILER_AVAILABLE or RegisterActivation is None:
        return []

    # Per-position collection of registers in source order.
    per_position: dict[int, list[str]] = {}
    for entry in register_labels or []:
        pos = entry.get("position")
        reg = entry.get("register")
        if pos is None or reg is None:
            continue
        try:
            pos_int = int(pos)
        except (TypeError, ValueError):
            continue
        if reg not in VALID_REGISTERS:
            continue
        per_position.setdefault(pos_int, []).append(reg)

    # Map omega names by position for emergent_name attachment.
    omega_by_position: dict[int, str] = {}
    for entry in omega_labels or []:
        pos = entry.get("position")
        name = entry.get("omega_name")
        if pos is None or name is None:
            continue
        try:
            pos_int = int(pos)
        except (TypeError, ValueError):
            continue
        omega_by_position[pos_int] = str(name)

    out: list[Any] = []
    # Sort positions for deterministic output ordering across Python runs.
    for pos_int in sorted(per_position.keys()):
        regs = per_position[pos_int]
        emergent_name = omega_by_position.get(pos_int)
        for reg in regs:
            out.append(
                RegisterActivation(
                    position=pos_int,
                    registers_active=frozenset((reg,)),
                    is_register_set=False,
                    emergent_name=emergent_name,
                )
            )
        # Trailing emergent record when the fallback is reconstructing a
        # named emergent-result assignment with >= 2 co-active registers.
        if emergent_name is not None and len(set(regs)) >= 2:
            out.append(
                RegisterActivation(
                    position=pos_int,
                    registers_active=frozenset(regs),
                    is_register_set=False,
                    emergent_name=emergent_name,
                )
            )
    return out


def activations_for_example(item: dict[str, Any]) -> list[Any]:
    """Produce ``list[RegisterActivation]`` for a single training example.

    Preference order:
      1. If the example carries a ``cas_expression`` string, compile it via
         the notation compiler and call ``extract_register_activations`` on
         the parsed AST. This is the single source of truth whenever a CAS
         expression is available.
      2. Otherwise, fall back to building equivalent records from
         ``register_labels`` + ``omega_labels`` via
         :func:`build_register_activations_from_labels`.

    Design decision (documented for the panel): compilation happens at
    ``__getitem__`` time (per-example, lazy) rather than at collate time
    (per-batch). Rationale: (a) keeps the collate function trivially
    parallelizable and free of compiler imports; (b) DataLoader workers
    amortize the compilation cost across epochs when ``num_workers>0``;
    (c) per-example caching via ``functools.lru_cache`` on the compiled
    expression string is a trivial future optimization that does not
    change the call site. Per-batch caching would require managing a
    dataset-global cache keyed by example id, which is not justified at
    the current batch sizes.

    Returns an empty list when neither source is usable; the trainer's
    fallback path then consumes the raw ``register_labels_batch`` dicts.
    """
    if not _COMPILER_AVAILABLE:
        return []

    expr = item.get("cas_expression")
    if expr is not None and compile_expression is not None and extract_register_activations is not None:
        try:
            artifact = compile_expression(str(expr))
        except Exception:
            artifact = None
        if artifact is not None and getattr(artifact, "valid", False) and getattr(artifact, "ast", None) is not None:
            try:
                return list(extract_register_activations(artifact.ast))
            except Exception:
                # Malformed AST — fall through to the label-derived path
                # rather than crashing the training loop.
                pass

    return build_register_activations_from_labels(
        item.get("register_labels", []),
        item.get("omega_labels", []),
    )


def training_text_for_item(item: dict[str, Any], target_mode: str = "response") -> str:
    """Return the language-model training sequence for one record.

    ``target_mode="cas_expression"`` is the CAS-Native expression-generation
    task: natural language prompt in, canonical CAS expression out. This is
    intentionally separate from the default prose-response mode so training
    runs can choose whether they are teaching conversational explanation or
    symbolic expression generation.
    """
    prompt = _conversation_text(item, "prompt", "user_prompt")
    response = _conversation_text(item, "response", "assistant_response")
    cas_expression = str(item.get("cas_expression") or "").strip()

    if target_mode == "cas_expression" and cas_expression:
        return f"[TASK_EXPR] [PROMPT] {prompt} [RESPONSE] {cas_expression}".strip()
    if target_mode == "explain":
        source = cas_expression or prompt
        return f"[TASK_EXPLAIN] [CAS] {source} [/CAS] [RESPONSE] {response}".strip()
    if target_mode == "chat":
        return f"[TASK_CHAT] [PROMPT] {prompt} [RESPONSE] {response}".strip()

    combined = f"{prompt} {response}".strip()
    return combined or "empty"


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
        tokenizer: Optional[TokenizerLike] = None,
        max_length: int = 512,
        target_mode: str = "response",
    ):
        self.data = data
        self.tokenizer = tokenizer or SimpleTokenizer()
        self.max_length = max_length
        self.target_mode = target_mode

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        item = self.data[idx]

        # Tokenize the configured training task. CAS expression generation
        # uses `[TASK_EXPR] prompt [RESPONSE] cas_expression`; prose runs keep
        # the historical prompt+response behavior.
        combined = training_text_for_item(item, self.target_mode)
        token_ids = self.tokenizer.encode(combined, max_length=self.max_length)

        # Input: all tokens except last; Target: all tokens except first
        input_ids = torch.tensor(token_ids[:-1], dtype=torch.long)
        targets = torch.tensor(token_ids[1:], dtype=torch.long)

        # Attention mask (all real tokens)
        attention_mask = torch.ones(len(input_ids), dtype=torch.long)

        # CAS scores (if available). Level 3 conversational records use
        # soft_*_targets, which are normalized here for the trainer.
        cas_scores = _score_payload(item)

        # v2 label streams (ADR-01 / ADR-02 / ADR-04). All optional; absent
        # fields default to empty list / None so per-example masking applies.
        register_labels = item.get("register_labels", [])
        omega_labels = item.get("omega_labels", [])
        production_target = item.get("production_target", None)
        cas_expression = item.get("cas_expression")
        construct_metadata: dict[str, Any] | None = None
        if cas_expression is not None and classify_expression is not None and construct_tokens is not None:
            expr_text = str(cas_expression)
            construct_metadata = {
                "expression_kind": classify_expression(expr_text).value,
                "construct_tokens": list(construct_tokens(expr_text)),
                "cas_expression": expr_text,
            }

        # Wave 8A Agent 36: compile-time register activations. Prefers the
        # compiler output when a ``cas_expression`` string is present;
        # otherwise reconstructs equivalent records from raw labels so the
        # trainer always consumes a uniform ``list[RegisterActivation]``.
        register_activations = activations_for_example(item)

        return {
            "input_ids": input_ids,
            "targets": targets,
            "attention_mask": attention_mask,
            "cas_scores": cas_scores,
            "register_labels": register_labels,
            "omega_labels": omega_labels,
            "production_target": production_target,
            "register_activations": register_activations,
            "construct_metadata": construct_metadata,
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
    register_activations_list: list[list[Any]] = []
    construct_metadata_list = []

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
        # Wave 8A Agent 36: per-example compiler output passed through as a
        # list-of-lists so the trainer's _compute_emergent_binding_loss can
        # consume the RegisterActivation dataclasses directly without
        # reconstructing them from raw label dicts.
        register_activations_list.append(item.get("register_activations", []) or [])
        construct_metadata_list.append(item.get("construct_metadata", None))

    return {
        "input_ids": torch.stack(padded_input_ids),
        "targets": torch.stack(padded_targets),
        "attention_mask": torch.stack(padded_masks),
        "cas_scores": cas_scores_list,
        "register_labels": register_labels_list,
        "omega_labels": omega_labels_list,
        "production_target": production_targets_list,
        "register_activations_batch": register_activations_list,
        "construct_metadata": construct_metadata_list,
    }


def load_cas_data(
    json_path: str | Path,
) -> list[dict[str, Any]]:
    """Load CAS data from a JSON or JSONL file.

    Tries standard ``json.loads`` first. On a multi-document parse error
    (typical for JSONL — newline-delimited JSON), falls back to line-by-line
    parsing.

    JSON shapes supported:
      - List of records: ``[{"prompt": ..., "response": ..., "scores": ...}, ...]``
      - Dict with "results" key: ``{"results": [...]}``
      - Single record dict: ``{"prompt": ..., ...}``

    JSONL: one JSON object per line; blank lines ignored. This is the format
    the cas-synthetic Level 2 generator emits at
    ``cas-synthetic/data/level2_scaffold/level2_full_10k.jsonl``.
    """
    path = Path(json_path)
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Strip BOM and leading whitespace; bail on empty file.
    stripped = content.lstrip("﻿").lstrip()
    if not stripped:
        return []

    # First, try parsing as a single JSON document. This catches JSON arrays,
    # single-record dicts, and the {"results": [...]} shape.
    try:
        raw = json.loads(stripped)
    except json.JSONDecodeError as exc:
        # JSONL signature: the first record parsed cleanly, but extra data
        # follows. Re-parse line-by-line.
        if exc.msg == "Extra data":
            return _load_jsonl(stripped, path)
        # Anything else (e.g. malformed first record) is a real error.
        raise

    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "results" in raw:
        return raw["results"]
    if isinstance(raw, dict):
        return [raw]
    return []


def _load_jsonl(content: str, source_path: Path) -> list[dict[str, Any]]:
    """Parse JSONL content (one JSON object per non-empty line)."""
    out: list[dict[str, Any]] = []
    for line_num, line in enumerate(content.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise json.JSONDecodeError(
                f"JSONL parse error in {source_path} at line {line_num}: {exc.msg}",
                exc.doc,
                exc.pos,
            ) from exc
        if isinstance(record, dict):
            out.append(record)
    return out


def create_data_loaders(
    data: list[dict[str, Any]],
    batch_size: int = 8,
    max_length: int = 512,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
    tokenizer: Optional[TokenizerLike] = None,
    use_cas_tokenizer: bool = True,
    target_mode: str = "response",
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
        tokenizer: Optional prebuilt tokenizer. If omitted and
            ``use_cas_tokenizer`` is true, a frozen ``HybridCASTokenizer`` is
            fit once on the full dataset before split.
        use_cas_tokenizer: Build the new CAS-aware tokenizer for production
            training paths. Tests can pass ``False`` or explicit
            ``SimpleTokenizer`` for tiny-vocab compatibility.
        target_mode: LM target surface. ``response`` preserves the historical
            prompt+response task; ``cas_expression`` teaches prompt-to-CAS.

    Returns:
        Tuple of (train_loader, val_loader, test_loader)
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6, \
        f"Ratios must sum to 1.0, got {train_ratio + val_ratio + test_ratio}"

    if tokenizer is None:
        tokenizer = (
            HybridCASTokenizer.from_texts(
                training_text_for_item(item, target_mode) for item in data
            )
            if use_cas_tokenizer
            else SimpleTokenizer()
        )

    dataset = CASDataset(
        data,
        tokenizer=tokenizer,
        max_length=max_length,
        target_mode=target_mode,
    )

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
    ops = item.get("operator_scores")
    if ops is None:
        ops = item.get("soft_operator_targets", [])
    if ops:
        if len(ops) != 10:
            return False
        if not all(0.0 <= s <= 1.0 for s in ops):
            return False

    doms = item.get("domain_averages")
    if doms is None:
        doms = item.get("domain_scores")
    if doms is None:
        doms = _domain_targets_as_list(item.get("soft_domain_targets"))
    if doms is None:
        doms = []
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

    expression_kind = item.get("expression_kind")
    if expression_kind is None and "construct_metadata" in item:
        metadata = item.get("construct_metadata") or {}
        expression_kind = metadata.get("expression_kind")
    if expression_kind is not None and classify_expression is not None:
        # Validate against the shared label vocabulary without requiring a
        # compiler call in the data pipeline's cheap ontology pass.
        from cas_native.model.meta_logic_constructs import EXPRESSION_KIND_LABELS

        if str(expression_kind) not in EXPRESSION_KIND_LABELS:
            return False

    expr = item.get("cas_expression")
    if expr is not None and classify_expression is not None:
        kind = classify_expression(str(expr)).value
        if expression_kind is not None and str(expression_kind) != kind:
            return False

    return True


def run_pipeline(
    json_paths: list[str | Path],
    augment: bool = True,
    batch_size: int = 8,
    max_length: int = 512,
    seed: int = 42,
    target_mode: str = "response",
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
        target_mode=target_mode,
    )
    stats["stages"]["4_split"] = {
        "train": len(train_loader.dataset),
        "val": len(val_loader.dataset),
        "test": len(test_loader.dataset),
    }
    stats["stages"]["5_tokenize"] = {
        "max_length": max_length,
        "batch_size": batch_size,
        "target_mode": target_mode,
    }
    tokenizer = tokenizer_from_loader(train_loader)
    if isinstance(tokenizer, HybridCASTokenizer):
        stats["stages"]["5_tokenize"]["tokenizer"] = tokenizer.metadata()
        exprs = [str(item.get("cas_expression", "")) for item in valid_data if item.get("cas_expression")]
        stats["stages"]["5_tokenize"]["cas_expression_unk_rate"] = tokenizer.unk_rate(exprs)
    elif tokenizer is not None:
        stats["stages"]["5_tokenize"]["tokenizer"] = {
            "type": tokenizer.__class__.__name__,
            "vocab_size": getattr(tokenizer, "vocab_size", None),
        }
    stats["total_items"] = len(valid_data)

    return train_loader, val_loader, test_loader, stats
