"""Label extraction for CAS Transformer structured-prediction training.

The first Step-7 target source is the held-out recoverable Level 3 dataset.
These helpers convert Level 3 records into stable class IDs and multi-hot
targets consumed by ``StructuredPredictionHead``.

Self-conditioning records carry an optional ``prior_cas_state`` field (a
serialized CAS expression string). When present, ``get_effective_prompt``
prepends a ``[PRIOR] ... \\n[QUERY] ...`` block so the tokenizer receives the
canonical CAS expression as context alongside the paraphrase query. Records
without ``prior_cas_state`` are passed through unchanged for full backward
compatibility.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

import torch

from .self_conditioning_serialization import serialize_prior_cas_state

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
)


BUCKET_TO_FAMILY = {
    "v74_baseline": "state",
    "v75_register": "register_state",
    "v76_production": "production",
    "v77_rule_four": "rule_four",
    "v77_omega": "omega",
    "meta_logic": "meta_logic",
}

FAMILY_TO_TRANSITION = {
    "state": "state",
    "register_state": "state",
    "production": "production",
    "rule_four": "relation",
    "omega": "omega_bind",
    "meta_logic": "meta_logic_move",
}

_NOETIC_RE = re.compile(r"\^([0-9])(?![0-9])")
_DOMAIN_RE = re.compile(r"\^[0-9](?![0-9])\^([PCEO])")
_DRIVE_RE = re.compile(r"_\{(F[1-7])\}")
_REGISTER_RE = re.compile(r"\|([TAfE])(?![A-Za-z])")
_REGISTER_SET_RE = re.compile(r"\|(?:<|\u27e8)([^>\u27e9]+)(?:>|\u27e9)")
_OMEGA_RE = re.compile(r"(?:Omega|[\u03a9])_[A-Za-z0-9_]+")


def labels_from_level3_record(record: dict[str, Any]) -> dict[str, Any]:
    """Extract structured-prediction labels from one Level 3 record."""

    expression = str(record.get("cas_expression", ""))
    bucket = str(record.get("bucket", ""))
    family = BUCKET_TO_FAMILY.get(bucket, _infer_family(expression))
    registers = _registers(expression)
    meta_relations = _meta_relations(expression)
    has_omega = bool(_OMEGA_RE.search(expression))
    has_meta_logic = family == "meta_logic" or any(meta_relations)
    return {
        "turn_type": _index("ANSWER", TURN_TYPE_LABELS),
        "expression_family": _index(family, EXPRESSION_FAMILY_LABELS),
        "transition_kind": _index(FAMILY_TO_TRANSITION[family], TRANSITION_KIND_LABELS),
        "noetic": _first_noetic(expression),
        "domain": _index(_first_domain(expression), DOMAIN_LABELS),
        "drive": _index(_first_drive(expression), DRIVE_LABELS),
        "registers": _multi_hot(registers, REGISTER_LABELS),
        "register_mode": _index(_register_mode(expression, registers, has_omega), REGISTER_MODE_LABELS),
        "meta_relations": _multi_hot(meta_relations, META_RELATION_LABELS),
        "authority": _index(_authority_label(expression), AUTHORITY_LABELS),
        "has_omega": int(has_omega),
        "has_meta_logic": int(has_meta_logic),
        "source_level2_id": record.get("source_level2_id"),
        "id": record.get("id"),
        "bucket": bucket,
    }


def batch_targets_from_records(
    records: Iterable[dict[str, Any]],
    *,
    device: torch.device | str | None = None,
) -> dict[str, torch.Tensor]:
    """Convert records into tensor targets for ``structured_prediction_loss``."""

    labels = [labels_from_level3_record(record) for record in records]
    if not labels:
        raise ValueError("records must be non-empty")
    dev = torch.device(device) if device is not None else None
    return {
        "turn_type": _long_tensor(labels, "turn_type", dev),
        "expression_family": _long_tensor(labels, "expression_family", dev),
        "transition_kind": _long_tensor(labels, "transition_kind", dev),
        "noetic": _long_tensor(labels, "noetic", dev),
        "domain": _long_tensor(labels, "domain", dev),
        "drive": _long_tensor(labels, "drive", dev),
        "register_mode": _long_tensor(labels, "register_mode", dev),
        "authority": _long_tensor(labels, "authority", dev),
        "has_omega": _long_tensor(labels, "has_omega", dev),
        "has_meta_logic": _long_tensor(labels, "has_meta_logic", dev),
        "registers": torch.tensor(
            [item["registers"] for item in labels],
            dtype=torch.float32,
            device=dev,
        ),
        "meta_relations": torch.tensor(
            [item["meta_relations"] for item in labels],
            dtype=torch.float32,
            device=dev,
        ),
    }


def get_effective_prompt(record: dict[str, Any]) -> str:
    """Return the tokenizer-input string for a record.

    When ``prior_cas_state`` is present and truthy, prepends the canonical CAS
    expression as a ``[PRIOR]`` block so the model can condition its content-axis
    predictions on that context. Records without ``prior_cas_state`` return their
    raw ``user_prompt`` unchanged — backward compatible with all pre-existing
    training and eval records.
    """

    if record.get("prior_cas_state"):
        return serialize_prior_cas_state(record)
    return str(record.get("user_prompt") or "")


def load_level3_jsonl(path: str | Path, limit: int | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
            if limit is not None and len(records) >= limit:
                break
    return records


def _first_noetic(expression: str) -> int:
    match = _NOETIC_RE.search(expression)
    return int(match.group(1)) if match else 0


def _first_domain(expression: str) -> str:
    match = _DOMAIN_RE.search(expression)
    return match.group(1) if match else "P"


def _first_drive(expression: str) -> str:
    match = _DRIVE_RE.search(expression)
    return match.group(1) if match else "F1"


def _registers(expression: str) -> list[str]:
    found: list[str] = []
    found.extend(match.group(1) for match in _REGISTER_RE.finditer(expression))
    for match in _REGISTER_SET_RE.finditer(expression):
        for item in match.group(1).split(","):
            value = item.strip()
            if value in REGISTER_LABELS:
                found.append(value)
    return list(dict.fromkeys(found))


def _register_mode(expression: str, registers: list[str], has_omega: bool) -> str:
    if "\u27e8" in expression or "|<" in expression:
        return "set_spec"
    if "\u00d7" in expression or re.search(r"\s+x\s+", expression):
        return "integration" if has_omega else "co_presence"
    if " + " in expression and len(registers) > 1:
        return "co_presence"
    if len(registers) == 1:
        return "single"
    if len(registers) > 1:
        return "set_spec"
    return "none"


def _meta_relations(expression: str) -> list[str]:
    relations: list[str] = []
    if any(token in expression for token in ("\u2208", " in ")):
        relations.append("membership")
    if any(token in expression for token in ("\u2282", "\u2286", "subset")):
        relations.append("subset")
    if "Product(" in expression:
        relations.append("product")
    if "CoverOf(" in expression:
        relations.append("cover")
    if "PartitionOf(" in expression:
        relations.append("partition")
    if "Pullback(" in expression:
        relations.append("pullback")
    if "TraceSet" in expression:
        relations.append("trace_nesting")
    if "EvidenceSet" in expression or "ValidatedClaimSet" in expression:
        relations.append("evidence")
    if "InstructionSet" in expression or "UserRequestSet" in expression:
        relations.append("authority")
    if any(token in expression for token in ("Cluster{", "Set{")):
        relations.append("membership")
    return list(dict.fromkeys(relations))


def _authority_label(expression: str) -> str:
    if "UserRequestSet" in expression and "SystemInstructionSet" in expression:
        return "blocked"
    if "InstructionSet" in expression or "UserRequestSet" in expression:
        return "admitted"
    return "none"


def _infer_family(expression: str) -> str:
    if "Theta(" in expression or "\u0398(" in expression:
        return "production"
    if _OMEGA_RE.search(expression):
        return "omega"
    if any(token in expression for token in ("Cluster{", "Set{", "Product(", "Pullback(", "CoverOf(", "PartitionOf(")):
        return "meta_logic"
    if _registers(expression):
        return "register_state"
    return "state"


def _index(label: str, labels: tuple[str, ...]) -> int:
    try:
        return labels.index(label)
    except ValueError as exc:
        raise ValueError(f"unknown label {label!r}; expected one of {labels}") from exc


def _multi_hot(values: list[str], labels: tuple[str, ...]) -> list[float]:
    out = [0.0] * len(labels)
    for value in values:
        if value in labels:
            out[labels.index(value)] = 1.0
    return out


def _long_tensor(labels: list[dict[str, Any]], key: str, device: torch.device | None) -> torch.Tensor:
    return torch.tensor([int(item[key]) for item in labels], dtype=torch.long, device=device)
