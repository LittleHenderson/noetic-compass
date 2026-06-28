#!/usr/bin/env python3
"""Run the matched-taxonomy control lane for CAS 40E / F28 readouts.

This is the runner-only implementation for the 2026-05-30 matched-taxonomy
pre-registration. It compares the original CAS labels against same-split,
same-activation matched taxonomy labels supplied by a manifest.

Manifest shape is intentionally permissive while the evidence format settles:

    {
      "schema_version": "matched_taxonomy_manifest.v1",
      "taxonomies": [
        {
          "id": "topic_40way",
          "name": "Topic 40-way",
          "role": "coherent_matched",
          "labels": ["topic_a", "..."],
          "parent_labels": ["topic_family", "..."],
          "child_labels": ["discourse_function", "..."]
        }
      ]
    }

The runner also accepts a dict under ``taxonomies`` or ``matched_taxonomies``.
Label vectors may be lists in dataset order or maps keyed by sample id when the
dataset/metadata supplies sample ids.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupShuffleSplit, StratifiedShuffleSplit
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler


SCHEMA_VERSION = "cas_harness_matched_taxonomy_control.v1"
PREREG_DOC = "docs/working/cas_harness_matched_taxonomy_control_prereg_20260530.md"
AXIS_40E = "40e"
AXIS_F28 = "f28"
DEFAULT_SHUFFLED_SEEDS = (20260530, 20260531, 20260532, 20260533, 20260534)
REQUIRED_NPZ_KEYS = ("features", "layers")
PROMPT_KEYS = ("prompts", "prompt_texts", "texts", "scenario_texts")
SAMPLE_ID_KEYS = ("sample_ids", "ids", "scenario_ids", "record_ids")


@dataclass(frozen=True)
class TaxonomySpec:
    taxonomy_id: str
    display_name: str
    role: str
    axis: str
    labels: np.ndarray
    parent_labels: np.ndarray | None
    child_labels: np.ndarray | None
    source: str
    coherent: bool
    description: str | None = None


@dataclass(frozen=True)
class LoadedDataset:
    features: np.ndarray
    layers: np.ndarray
    prompts: np.ndarray
    sample_ids: np.ndarray
    npz_keys: tuple[str, ...]


def _json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _as_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if value is None:
        return ""
    return str(value)


def _load_jsonish(path: Path) -> Any:
    if path.suffix.lower() == ".jsonl":
        records: list[Any] = []
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _progress(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[matched-taxonomy] {message}", file=sys.stderr, flush=True)


def _artifact_descriptor(artifact_id: str, artifact_type: str, path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "content_sha256": _sha256_file(path),
        "byte_count": int(stat.st_size),
        "storage_uri": str(path),
        "redaction_class": "internal_eval_artifact",
        "created_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
    }


def _build_linear_probe(C: float, max_iter: int) -> Pipeline:
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=C,
            max_iter=max_iter,
            class_weight="balanced",
            solver="lbfgs",
            n_jobs=-1,
        ),
    )


def _build_text_probe(C: float, max_iter: int) -> LogisticRegression:
    return LogisticRegression(
        C=C,
        max_iter=max_iter,
        class_weight="balanced",
        solver="lbfgs",
        n_jobs=-1,
    )


def _score_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def _strip_framing_tags(prompt: Any) -> str:
    text = _as_text(prompt)
    while text.startswith("[") and "]" in text:
        text = text.split("]", 1)[1].lstrip()
    return text


def _first_present(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in ("samples", "records", "scenarios", "items", "rows"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _record_field_vector(
    records: list[dict[str, Any]],
    *,
    field_names: tuple[str, ...],
    sample_ids: np.ndarray,
) -> np.ndarray | None:
    if not records:
        return None

    id_keys = ("sample_id", "id", "scenario_id", "record_id")
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        for id_key in id_keys:
            if id_key in record:
                by_id[_as_text(record[id_key])] = record
                break

    if by_id and all(_as_text(sample_id) in by_id for sample_id in sample_ids):
        values = []
        for sample_id in sample_ids:
            record = by_id[_as_text(sample_id)]
            values.append(_first_present(record, field_names))
        if all(value is not None for value in values):
            return np.array([_as_text(value) for value in values], dtype=object)

    if len(records) == len(sample_ids):
        values = [_first_present(record, field_names) for record in records]
        if all(value is not None for value in values):
            return np.array([_as_text(value) for value in values], dtype=object)
    return None


def _load_dataset(dataset_path: Path, metadata: Any) -> LoadedDataset:
    data = np.load(dataset_path, allow_pickle=True)
    missing = set(REQUIRED_NPZ_KEYS) - set(data.files)
    if missing:
        raise SystemExit(f"dataset missing required keys: {sorted(missing)}")

    features = np.asarray(data["features"])
    layers = np.asarray(data["layers"])
    if features.ndim != 3:
        raise SystemExit(f"features must be [N, num_layers, hidden_dim]; got {features.shape}")
    if len(layers) != features.shape[1]:
        raise SystemExit(
            f"layers length {len(layers)} does not match feature layer count {features.shape[1]}"
        )

    prompt_raw = None
    for key in PROMPT_KEYS:
        if key in data.files:
            prompt_raw = data[key]
            break
    if prompt_raw is None:
        prompt_raw = _record_field_vector(
            _extract_records(metadata),
            field_names=("prompt", "text", "scenario_text", "input"),
            sample_ids=np.array([str(i) for i in range(features.shape[0])], dtype=object),
        )
    if prompt_raw is None:
        raise SystemExit(
            "dataset must contain prompts/texts or metadata records with prompt/text fields "
            "for the text-only baseline"
        )
    prompts = np.array([_as_text(value) for value in prompt_raw], dtype=object)
    if len(prompts) != features.shape[0]:
        raise SystemExit(f"prompt count {len(prompts)} does not match sample count {features.shape[0]}")

    sample_raw = None
    for key in SAMPLE_ID_KEYS:
        if key in data.files:
            sample_raw = data[key]
            break
    if sample_raw is None:
        sample_raw = _record_field_vector(
            _extract_records(metadata),
            field_names=("sample_id", "id", "scenario_id", "record_id"),
            sample_ids=np.array([str(i) for i in range(features.shape[0])], dtype=object),
        )
    if sample_raw is None:
        sample_ids = np.array([str(i) for i in range(features.shape[0])], dtype=object)
    else:
        sample_ids = np.array([_as_text(value) for value in sample_raw], dtype=object)
    if len(sample_ids) != features.shape[0]:
        raise SystemExit(
            f"sample id count {len(sample_ids)} does not match sample count {features.shape[0]}"
        )

    return LoadedDataset(
        features=features,
        layers=layers,
        prompts=prompts,
        sample_ids=sample_ids,
        npz_keys=tuple(data.files),
    )


def _coerce_vector(
    raw: Any,
    *,
    n_samples: int,
    sample_ids: np.ndarray,
    field_name: str,
) -> np.ndarray:
    if isinstance(raw, np.ndarray):
        values = raw.tolist()
    elif isinstance(raw, list):
        values = raw
    elif isinstance(raw, tuple):
        values = list(raw)
    elif isinstance(raw, dict):
        for key in ("values", "labels", "items"):
            if key in raw:
                return _coerce_vector(
                    raw[key],
                    n_samples=n_samples,
                    sample_ids=sample_ids,
                    field_name=field_name,
                )
        missing_ids = [_as_text(sample_id) for sample_id in sample_ids if _as_text(sample_id) not in raw]
        if not missing_ids:
            return np.array([_as_text(raw[_as_text(sample_id)]) for sample_id in sample_ids], dtype=object)
        if all(str(i) in raw for i in range(n_samples)):
            return np.array([_as_text(raw[str(i)]) for i in range(n_samples)], dtype=object)
        raise SystemExit(
            f"{field_name} is a mapping but does not cover dataset sample ids; "
            f"first missing ids: {missing_ids[:5]}"
        )
    else:
        raise SystemExit(f"{field_name} must be a list or sample-id mapping")

    if values and all(isinstance(value, dict) for value in values):
        records = [value for value in values if isinstance(value, dict)]
        vector = _record_field_vector(
            records,
            field_names=("label", field_name, "class", "class_label"),
            sample_ids=sample_ids,
        )
        if vector is None:
            raise SystemExit(f"{field_name} records must provide labels in dataset order or by sample id")
        return vector

    if len(values) != n_samples:
        raise SystemExit(f"{field_name} has {len(values)} values; expected {n_samples}")
    return np.array([_as_text(value) for value in values], dtype=object)


def _vector_from_payload(
    payload: Any,
    *,
    n_samples: int,
    sample_ids: np.ndarray,
    keys: tuple[str, ...],
    field_name: str,
) -> np.ndarray | None:
    if payload is None:
        return None
    if isinstance(payload, dict):
        raw = _first_present(payload, keys)
        if raw is not None:
            return _coerce_vector(
                raw,
                n_samples=n_samples,
                sample_ids=sample_ids,
                field_name=field_name,
            )
        records = _extract_records(payload)
    elif isinstance(payload, list):
        records = _extract_records(payload)
    else:
        records = []

    if records:
        return _record_field_vector(records, field_names=keys, sample_ids=sample_ids)
    return None


def _dataset_vector(dataset_path: Path, key: str) -> np.ndarray | None:
    data = np.load(dataset_path, allow_pickle=True)
    if key not in data.files:
        return None
    return np.array([_as_text(value) for value in data[key]], dtype=object)


def _parse_factor_from_label(labels: np.ndarray) -> tuple[np.ndarray | None, np.ndarray | None]:
    delimiters = ("|", "::", "/", ":")
    parents: list[str] = []
    children: list[str] = []
    for label in labels:
        text = _as_text(label)
        delimiter = next((candidate for candidate in delimiters if candidate in text), None)
        if delimiter is None:
            return None, None
        parent, child = text.split(delimiter, 1)
        parents.append(parent)
        children.append(child)
    return np.array(parents, dtype=object), np.array(children, dtype=object)


def _build_cas_taxonomy(
    *,
    axis: str,
    dataset_path: Path,
    loaded: LoadedDataset,
    metadata: Any,
    original_labels: Any | None,
) -> TaxonomySpec:
    n_samples = loaded.features.shape[0]
    source = "activation_dataset_npz"

    if axis == AXIS_40E:
        labels = _vector_from_payload(
            original_labels,
            n_samples=n_samples,
            sample_ids=loaded.sample_ids,
            keys=("labels_40e", "labels_40_element", "forty_element", "label"),
            field_name="cas_40e_labels",
        )
        operators = None
        domains = None
        if labels is None:
            operators = _dataset_vector(dataset_path, "labels_operator")
            domains = _dataset_vector(dataset_path, "labels_domain")
            if operators is not None and domains is not None:
                labels = np.array([f"{op}|{dom}" for op, dom in zip(operators, domains)], dtype=object)
        if labels is None:
            labels = _vector_from_payload(
                metadata,
                n_samples=n_samples,
                sample_ids=loaded.sample_ids,
                keys=("labels_40e", "labels_40_element", "forty_element", "label"),
                field_name="cas_40e_labels",
            )
            source = "metadata_or_original_labels"
        if labels is None:
            raise SystemExit(
                "axis 40e requires labels_operator + labels_domain in the NPZ, "
                "or labels_40e/labels_40_element in --original-labels/--metadata"
            )
        if operators is None or domains is None:
            parents, children = _parse_factor_from_label(labels)
        else:
            parents, children = operators, domains
        return TaxonomySpec(
            taxonomy_id="cas_40e",
            display_name="CAS 40E",
            role="cas",
            axis=axis,
            labels=labels,
            parent_labels=parents,
            child_labels=children,
            source=source,
            coherent=True,
            description="Original CAS 40-Element labels",
        )

    if axis == AXIS_F28:
        labels = _vector_from_payload(
            original_labels,
            n_samples=n_samples,
            sample_ids=loaded.sample_ids,
            keys=("labels_f28", "labels_foundation", "foundation_28", "label"),
            field_name="cas_f28_labels",
        )
        drives = None
        registers = None
        if labels is None:
            drives = _dataset_vector(dataset_path, "labels_drive")
            registers = _dataset_vector(dataset_path, "labels_register")
            if drives is not None and registers is not None:
                labels = np.array([f"{drv}|{reg}" for drv, reg in zip(drives, registers)], dtype=object)
        if labels is None:
            labels = _vector_from_payload(
                metadata,
                n_samples=n_samples,
                sample_ids=loaded.sample_ids,
                keys=("labels_f28", "labels_foundation", "foundation_28", "label"),
                field_name="cas_f28_labels",
            )
            source = "metadata_or_original_labels"
        if labels is None:
            raise SystemExit(
                "axis f28 requires labels_drive + labels_register in the NPZ, "
                "or labels_f28/labels_foundation in --original-labels/--metadata"
            )
        if drives is None or registers is None:
            parents, children = _parse_factor_from_label(labels)
        else:
            parents, children = drives, registers
        return TaxonomySpec(
            taxonomy_id="cas_f28",
            display_name="CAS Foundation-28",
            role="cas",
            axis=axis,
            labels=labels,
            parent_labels=parents,
            child_labels=children,
            source=source,
            coherent=True,
            description="Original CAS Foundation-28 labels",
        )

    raise SystemExit(f"unsupported axis: {axis}")


def _normalise_role(raw: Any, taxonomy_id: str, coherent: bool) -> str:
    role = _as_text(raw).strip().lower() if raw is not None else ""
    if not role:
        role = "coherent_matched" if coherent else "matched_control"
    if "cas" in role and "scram" not in role:
        return "cas"
    if "scram" in role or "shuffle" in role or "random" in role or "scram" in taxonomy_id.lower():
        return "scrambled_control"
    if "coherent" in role:
        return "coherent_matched"
    return role


def _taxonomy_entries(manifest: Any) -> list[dict[str, Any]]:
    if not isinstance(manifest, dict):
        raise SystemExit("matched taxonomy manifest must be a JSON object")
    raw = manifest.get("taxonomies", manifest.get("matched_taxonomies", manifest.get("controls", [])))
    if isinstance(raw, dict):
        entries = []
        for taxonomy_id, value in raw.items():
            if isinstance(value, dict):
                entries.append({"id": taxonomy_id, **value})
            else:
                entries.append({"id": taxonomy_id, "labels": value})
        return entries
    if isinstance(raw, list):
        return [entry for entry in raw if isinstance(entry, dict)]
    raise SystemExit("manifest taxonomies/matched_taxonomies must be a list or object")


def _factor_vector_from_entry(
    entry: dict[str, Any],
    *,
    n_samples: int,
    sample_ids: np.ndarray,
    factor_name: str,
    direct_keys: tuple[str, ...],
) -> np.ndarray | None:
    raw = _first_present(entry, direct_keys)
    if raw is not None:
        return _coerce_vector(
            raw,
            n_samples=n_samples,
            sample_ids=sample_ids,
            field_name=f"{entry.get('id', 'taxonomy')}.{factor_name}",
        )

    nested = entry.get("nested") if isinstance(entry.get("nested"), dict) else {}
    raw = _first_present(nested, direct_keys)
    if raw is not None:
        return _coerce_vector(
            raw,
            n_samples=n_samples,
            sample_ids=sample_ids,
            field_name=f"{entry.get('id', 'taxonomy')}.{factor_name}",
        )

    factors = entry.get("factors") if isinstance(entry.get("factors"), dict) else {}
    raw = _first_present(factors, direct_keys)
    if raw is not None:
        return _coerce_vector(
            raw,
            n_samples=n_samples,
            sample_ids=sample_ids,
            field_name=f"{entry.get('id', 'taxonomy')}.{factor_name}",
        )
    return None


def _looks_like_design_only_label_space(raw: Any, *, n_samples: int) -> bool:
    """Return true when a manifest lists class names, not row-level labels."""
    if isinstance(raw, np.ndarray):
        return len(raw) != n_samples
    if isinstance(raw, (list, tuple)):
        return len(raw) != n_samples
    if isinstance(raw, dict):
        for key in ("values", "items"):
            if key in raw:
                return _looks_like_design_only_label_space(raw[key], n_samples=n_samples)
        if "labels" in raw:
            return _looks_like_design_only_label_space(raw["labels"], n_samples=n_samples)
    return False


def load_taxonomy_manifest(
    manifest: Any,
    *,
    axis: str,
    n_samples: int,
    sample_ids: np.ndarray,
) -> list[TaxonomySpec]:
    specs: list[TaxonomySpec] = []
    for index, entry in enumerate(_taxonomy_entries(manifest)):
        taxonomy_axis = _as_text(entry.get("axis", axis)).strip().lower()
        if taxonomy_axis and taxonomy_axis not in {axis, "all", "both"}:
            continue

        taxonomy_id = _as_text(entry.get("id", entry.get("taxonomy_id", f"taxonomy_{index + 1}")))
        labels_raw = _first_present(
            entry,
            ("labels", "label_vector", "class_labels", "classes", "y"),
        )
        if labels_raw is None and isinstance(entry.get("samples"), list):
            labels_raw = entry["samples"]
        if labels_raw is None:
            continue

        try:
            labels = _coerce_vector(
                labels_raw,
                n_samples=n_samples,
                sample_ids=sample_ids,
                field_name=f"{taxonomy_id}.labels",
            )
        except SystemExit:
            if _looks_like_design_only_label_space(labels_raw, n_samples=n_samples):
                continue
            raise
        parent_labels = _factor_vector_from_entry(
            entry,
            n_samples=n_samples,
            sample_ids=sample_ids,
            factor_name="parent_labels",
            direct_keys=("parent_labels", "parents", "parent", "factor_a", "drive_labels"),
        )
        child_labels = _factor_vector_from_entry(
            entry,
            n_samples=n_samples,
            sample_ids=sample_ids,
            factor_name="child_labels",
            direct_keys=("child_labels", "children", "child", "factor_b", "register_labels"),
        )
        if parent_labels is None or child_labels is None:
            parsed_parent, parsed_child = _parse_factor_from_label(labels)
            parent_labels = parent_labels if parent_labels is not None else parsed_parent
            child_labels = child_labels if child_labels is not None else parsed_child

        coherent = bool(entry.get("coherent", True))
        role = _normalise_role(
            entry.get("role", entry.get("kind", entry.get("type"))),
            taxonomy_id,
            coherent,
        )
        if role == "scrambled_control":
            coherent = False

        specs.append(
            TaxonomySpec(
                taxonomy_id=taxonomy_id,
                display_name=_as_text(entry.get("name", taxonomy_id)),
                role=role,
                axis=axis,
                labels=labels,
                parent_labels=parent_labels,
                child_labels=child_labels,
                source="matched_taxonomy_manifest",
                coherent=coherent,
                description=entry.get("description"),
            )
        )
    return specs


def _make_scrambled_taxonomy(cas: TaxonomySpec, *, seed: int) -> TaxonomySpec:
    rng = np.random.default_rng(seed)
    permutation = rng.permutation(len(cas.labels))
    labels = cas.labels[permutation]
    parent_labels = cas.parent_labels[permutation] if cas.parent_labels is not None else None
    child_labels = cas.child_labels[permutation] if cas.child_labels is not None else None
    return TaxonomySpec(
        taxonomy_id=f"scrambled_cas_seed_{seed}",
        display_name=f"Scrambled CAS labels seed {seed}",
        role="scrambled_control",
        axis=cas.axis,
        labels=np.array(labels, dtype=object),
        parent_labels=np.array(parent_labels, dtype=object) if parent_labels is not None else None,
        child_labels=np.array(child_labels, dtype=object) if child_labels is not None else None,
        source="generated_by_runner",
        coherent=False,
        description="CAS labels permuted across samples with a fixed seed",
    )


def _parse_seed_list(value: str) -> list[int]:
    if not value.strip():
        return []
    seeds: list[int] = []
    for raw in value.split(","):
        raw = raw.strip()
        if raw:
            seeds.append(int(raw))
    return seeds


def _parse_layers(value: str, layers: np.ndarray) -> list[int]:
    available = [int(layer) for layer in layers.tolist()]
    if value.strip().lower() == "all":
        return available
    selected: list[int] = []
    for raw in value.split(","):
        raw = raw.strip()
        if raw:
            selected.append(int(raw))
    missing = [layer for layer in selected if layer not in available]
    if missing:
        raise SystemExit(f"selected layer(s) not present in dataset: {missing}; available={available}")
    if not selected:
        raise SystemExit("--layers must be 'all' or a comma-separated layer list")
    return selected


def _class_distribution(labels: np.ndarray) -> dict[str, int]:
    counts = Counter(_as_text(label) for label in labels)
    return {label: int(counts[label]) for label in sorted(counts)}


def _split_indices(
    *,
    features: np.ndarray,
    labels: np.ndarray,
    prompts: np.ndarray,
    test_size: float,
    seed: int,
    split_mode: str,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    groups = np.array([_strip_framing_tags(prompt) for prompt in prompts], dtype=object)
    n_unique_groups = len(set(groups.tolist()))
    use_stratified = split_mode == "stratified" or (split_mode == "auto" and n_unique_groups == len(groups))

    if use_stratified:
        splitter = StratifiedShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
        train_idx, test_idx = next(splitter.split(features, labels))
        mode = "StratifiedShuffleSplit"
        group_key = None
    else:
        splitter = GroupShuffleSplit(n_splits=100, test_size=test_size, random_state=seed)
        all_classes = set(labels.tolist())
        best: tuple[np.ndarray, np.ndarray] | None = None
        best_score = (-1, -1, 0)
        for candidate_train, candidate_test in splitter.split(features, labels, groups=groups):
            train_classes = set(labels[candidate_train].tolist())
            test_classes = set(labels[candidate_test].tolist())
            score = (len(train_classes), len(test_classes), -abs(len(candidate_test) - test_size * len(labels)))
            if score > best_score:
                best = (candidate_train, candidate_test)
                best_score = score
            if train_classes == all_classes and len(test_classes) >= 2:
                best = (candidate_train, candidate_test)
                break
        if best is None:
            raise SystemExit("could not construct a train/test split")
        train_idx, test_idx = best
        mode = "GroupShuffleSplit"
        group_key = "base prompt after stripping leading bracket framing tags"

    split_manifest = {
        "type": mode,
        "seed": int(seed),
        "test_size": float(test_size),
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "n_base_prompt_groups": int(n_unique_groups),
        "group_key": group_key,
        "train_indices": [int(i) for i in train_idx.tolist()],
        "test_indices": [int(i) for i in test_idx.tolist()],
    }
    split_manifest["content_sha256"] = _sha256_json(split_manifest)
    return train_idx, test_idx, split_manifest


def _lacunarity(scores: np.ndarray) -> float | None:
    values = np.asarray(scores, dtype=np.float64)
    if values.size == 0:
        return None
    mean = float(np.mean(values))
    if mean <= 0.0:
        return None
    return float(np.var(values) / (mean * mean))


def _class_probability_means(
    *,
    probe: Pipeline,
    X_test: np.ndarray,
    all_classes: list[str],
) -> dict[str, float]:
    logistic = probe.named_steps["logisticregression"]
    if not hasattr(logistic, "classes_"):
        return {label: 0.0 for label in all_classes}
    classes_seen = [_as_text(label) for label in logistic.classes_]
    proba = probe.predict_proba(X_test)
    means = np.mean(proba, axis=0)
    by_class = {label: 0.0 for label in all_classes}
    for label, value in zip(classes_seen, means):
        by_class[_as_text(label)] = float(value)
    return by_class


def _factor_map(
    labels: np.ndarray,
    factors: np.ndarray | None,
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    if factors is None:
        return {}, []
    by_label: dict[str, Counter[str]] = defaultdict(Counter)
    for label, factor in zip(labels, factors):
        by_label[_as_text(label)][_as_text(factor)] += 1
    mapping: dict[str, str] = {}
    conflicts: list[dict[str, Any]] = []
    for label, counts in by_label.items():
        factor, count = counts.most_common(1)[0]
        mapping[label] = factor
        if len(counts) > 1:
            conflicts.append(
                {
                    "label": label,
                    "chosen_factor": factor,
                    "factor_counts": {key: int(value) for key, value in counts.items()},
                    "chosen_count": int(count),
                }
            )
    return mapping, conflicts


def _nested_lacunarity(
    *,
    labels: np.ndarray,
    parent_labels: np.ndarray | None,
    child_labels: np.ndarray | None,
    class_probability_means: dict[str, float],
    flat_lacunarity: float | None,
) -> dict[str, Any]:
    if parent_labels is None or child_labels is None:
        return {"status": "not_available", "reason": "taxonomy has no parent/child factor labels"}

    parent_map, parent_conflicts = _factor_map(labels, parent_labels)
    child_map, child_conflicts = _factor_map(labels, child_labels)
    if not parent_map or not child_map:
        return {"status": "not_available", "reason": "could not map joint classes to factors"}

    parent_scores: defaultdict[str, float] = defaultdict(float)
    child_scores: defaultdict[str, float] = defaultdict(float)
    for label, probability in class_probability_means.items():
        if label in parent_map:
            parent_scores[parent_map[label]] += probability
        if label in child_map:
            child_scores[child_map[label]] += probability

    parent_values = np.array([parent_scores[key] for key in sorted(parent_scores)])
    child_values = np.array([child_scores[key] for key in sorted(child_scores)])
    return {
        "status": "available",
        "parent_factor_lacunarity": _lacunarity(parent_values),
        "child_factor_lacunarity": _lacunarity(child_values),
        "joint_class_lacunarity": flat_lacunarity,
        "parent_factor_count": int(len(parent_scores)),
        "child_factor_count": int(len(child_scores)),
        "parent_factor_scores": {key: float(parent_scores[key]) for key in sorted(parent_scores)},
        "child_factor_scores": {key: float(child_scores[key]) for key in sorted(child_scores)},
        "mapping_conflicts": {
            "parent": parent_conflicts,
            "child": child_conflicts,
        },
    }


def _fit_hidden_layer(
    *,
    X: np.ndarray,
    labels: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    probe_C: float,
    probe_max_iter: int,
) -> tuple[Pipeline | None, dict[str, Any]]:
    y_train = labels[train_idx]
    y_test = labels[test_idx]
    if len(set(y_train.tolist())) < 2:
        return None, {
            "status": "failed",
            "error": "training split contains fewer than two classes",
            "accuracy": None,
            "macro_f1": None,
        }
    probe = _build_linear_probe(probe_C, probe_max_iter)
    try:
        probe.fit(X[train_idx], y_train)
        pred = probe.predict(X[test_idx])
    except Exception as exc:  # pragma: no cover - defensive report path
        return None, {
            "status": "failed",
            "error": str(exc),
            "accuracy": None,
            "macro_f1": None,
        }
    metrics = _score_predictions(y_test, pred)
    return probe, {"status": "completed", **metrics}


def _fit_text_baseline(
    *,
    prompts: np.ndarray,
    labels: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    text_C: float,
    probe_max_iter: int,
    max_features: int,
) -> dict[str, Any]:
    y_train = labels[train_idx]
    y_test = labels[test_idx]
    if len(set(y_train.tolist())) < 2:
        return {
            "status": "failed",
            "error": "training split contains fewer than two classes",
            "accuracy": None,
            "macro_f1": None,
        }
    vectorizer = CountVectorizer(max_features=max_features, ngram_range=(1, 2), lowercase=True)
    classifier = _build_text_probe(text_C, probe_max_iter)
    try:
        X_train = vectorizer.fit_transform([_as_text(value) for value in prompts[train_idx]])
        X_test = vectorizer.transform([_as_text(value) for value in prompts[test_idx]])
        classifier.fit(X_train, y_train)
        pred = classifier.predict(X_test)
    except Exception as exc:  # pragma: no cover - defensive report path
        return {
            "status": "failed",
            "error": str(exc),
            "accuracy": None,
            "macro_f1": None,
        }
    return {
        "status": "completed",
        "classifier": (
            "CountVectorizer(max_features="
            f"{max_features}, ngram_range=(1,2)) + LogisticRegression(class_weight='balanced')"
        ),
        **_score_predictions(y_test, pred),
        "vocabulary_size": int(len(vectorizer.vocabulary_)),
    }


def _shuffled_label_controls(
    *,
    X: np.ndarray,
    labels: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    seeds: list[int],
    probe_C: float,
    probe_max_iter: int,
    progress_enabled: bool = False,
    taxonomy_id: str | None = None,
) -> dict[str, Any]:
    y_train = labels[train_idx]
    y_test = labels[test_idx]
    trials: list[dict[str, Any]] = []
    label = taxonomy_id or "taxonomy"
    for seed_index, seed in enumerate(seeds, start=1):
        _progress(
            progress_enabled,
            f"control shuffled-label {label} seed {seed_index}/{len(seeds)} start seed={seed}",
        )
        rng = np.random.default_rng(seed)
        shuffled_train = rng.permutation(y_train)
        if len(set(shuffled_train.tolist())) < 2:
            trial = {
                "seed": int(seed),
                "status": "failed",
                "error": "shuffled training split contains fewer than two classes",
                "accuracy": None,
                "macro_f1": None,
            }
        else:
            probe = _build_linear_probe(probe_C, probe_max_iter)
            try:
                probe.fit(X[train_idx], shuffled_train)
                pred = probe.predict(X[test_idx])
                trial = {"seed": int(seed), "status": "completed", **_score_predictions(y_test, pred)}
            except Exception as exc:  # pragma: no cover - defensive report path
                trial = {
                    "seed": int(seed),
                    "status": "failed",
                    "error": str(exc),
                    "accuracy": None,
                    "macro_f1": None,
                }
        trials.append(trial)
        _progress(
            progress_enabled,
            (
                f"control shuffled-label {label} seed {seed_index}/{len(seeds)} "
                f"done status={trial['status']} accuracy={trial.get('accuracy')}"
            ),
        )

    accs = [float(trial["accuracy"]) for trial in trials if trial.get("accuracy") is not None]
    f1s = [float(trial["macro_f1"]) for trial in trials if trial.get("macro_f1") is not None]
    return {
        "seeds": [int(seed) for seed in seeds],
        "trials": trials,
        "mean_accuracy": float(np.mean(accs)) if accs else None,
        "max_accuracy": float(np.max(accs)) if accs else None,
        "mean_macro_f1": float(np.mean(f1s)) if f1s else None,
        "max_macro_f1": float(np.max(f1s)) if f1s else None,
    }


def _neighbor_stability(per_layer: list[dict[str, Any]], best_index: int) -> dict[str, Any]:
    if not per_layer:
        return {"status": "not_available"}
    candidates = []
    for idx in (best_index - 1, best_index + 1):
        if 0 <= idx < len(per_layer):
            value = per_layer[idx].get("accuracy")
            if value is not None:
                candidates.append(per_layer[idx])
    if not candidates:
        return {
            "status": "not_available",
            "reason": "no selected neighboring layers around best layer",
        }
    best_acc = per_layer[best_index]["accuracy"]
    neighbor_accs = [float(item["accuracy"]) for item in candidates]
    return {
        "status": "available",
        "neighbor_layers": [int(item["layer"]) for item in candidates],
        "neighbor_accuracy_mean": float(np.mean(neighbor_accs)),
        "best_minus_neighbor_mean_accuracy": float(best_acc - np.mean(neighbor_accs)),
    }


def evaluate_taxonomy(
    *,
    taxonomy: TaxonomySpec,
    loaded: LoadedDataset,
    selected_layers: list[int],
    layer_to_index: dict[int, int],
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    shuffled_seeds: list[int],
    probe_C: float,
    text_C: float,
    probe_max_iter: int,
    text_max_features: int,
    cas_class_count: int,
    progress_enabled: bool = False,
    taxonomy_index: int | None = None,
    taxonomy_total: int | None = None,
) -> dict[str, Any]:
    labels = np.array([_as_text(value) for value in taxonomy.labels], dtype=object)
    all_classes = sorted(set(labels.tolist()))
    class_distribution = _class_distribution(labels)
    test_class_distribution = _class_distribution(labels[test_idx])
    train_class_distribution = _class_distribution(labels[train_idx])
    if taxonomy_index is not None and taxonomy_total is not None:
        taxonomy_position = f"{taxonomy_index}/{taxonomy_total}"
    else:
        taxonomy_position = "?"

    _progress(
        progress_enabled,
        (
            f"taxonomy {taxonomy_position} start id={taxonomy.taxonomy_id} role={taxonomy.role} "
            f"classes={len(all_classes)} layers={len(selected_layers)} shuffled_seeds={len(shuffled_seeds)}"
        ),
    )

    _progress(progress_enabled, f"taxonomy {taxonomy.taxonomy_id} text-baseline start")
    text_baseline = _fit_text_baseline(
        prompts=loaded.prompts,
        labels=labels,
        train_idx=train_idx,
        test_idx=test_idx,
        text_C=text_C,
        probe_max_iter=probe_max_iter,
        max_features=text_max_features,
    )
    _progress(
        progress_enabled,
        (
            f"taxonomy {taxonomy.taxonomy_id} text-baseline done "
            f"status={text_baseline['status']} accuracy={text_baseline.get('accuracy')}"
        ),
    )

    per_layer: list[dict[str, Any]] = []
    for layer_index, layer in enumerate(selected_layers, start=1):
        _progress(
            progress_enabled,
            f"taxonomy {taxonomy.taxonomy_id} layer {layer_index}/{len(selected_layers)} start layer={layer}",
        )
        X = loaded.features[:, layer_to_index[layer], :].astype(np.float32)
        probe, metrics = _fit_hidden_layer(
            X=X,
            labels=labels,
            train_idx=train_idx,
            test_idx=test_idx,
            probe_C=probe_C,
            probe_max_iter=probe_max_iter,
        )
        layer_result: dict[str, Any] = {"layer": int(layer), **metrics}
        if probe is not None:
            means = _class_probability_means(
                probe=probe,
                X_test=X[test_idx],
                all_classes=all_classes,
            )
            flat = _lacunarity(np.array([means[label] for label in all_classes]))
            layer_result["flat_lacunarity"] = flat
            layer_result["class_probability_means"] = means
            layer_result["nested_lacunarity"] = _nested_lacunarity(
                labels=labels,
                parent_labels=taxonomy.parent_labels,
                child_labels=taxonomy.child_labels,
                class_probability_means=means,
                flat_lacunarity=flat,
            )
        else:
            layer_result["flat_lacunarity"] = None
            layer_result["class_probability_means"] = {}
            layer_result["nested_lacunarity"] = {
                "status": "not_available",
                "reason": "hidden probe fit failed",
            }
        per_layer.append(layer_result)
        _progress(
            progress_enabled,
            (
                f"taxonomy {taxonomy.taxonomy_id} layer {layer_index}/{len(selected_layers)} "
                f"done layer={layer} status={layer_result['status']} accuracy={layer_result.get('accuracy')}"
            ),
        )

    completed_layers = [item for item in per_layer if item.get("accuracy") is not None]
    if not completed_layers:
        best_layer = {
            "status": "failed",
            "layer": None,
            "accuracy": None,
            "macro_f1": None,
            "flat_lacunarity": None,
        }
        best_index = 0
    else:
        best_layer = max(completed_layers, key=lambda item: (float(item["accuracy"]), float(item["macro_f1"])))
        best_index = per_layer.index(best_layer)

    best_layer_id = selected_layers[best_index] if best_layer.get("layer") is None else int(best_layer["layer"])
    best_layer_X = loaded.features[:, layer_to_index[best_layer_id], :].astype(np.float32)
    _progress(
        progress_enabled,
        (
            f"taxonomy {taxonomy.taxonomy_id} control shuffled-label start "
            f"best_layer={best_layer_id} seeds={len(shuffled_seeds)}"
        ),
    )
    shuffled = _shuffled_label_controls(
        X=best_layer_X,
        labels=labels,
        train_idx=train_idx,
        test_idx=test_idx,
        seeds=shuffled_seeds,
        probe_C=probe_C,
        probe_max_iter=probe_max_iter,
        progress_enabled=progress_enabled,
        taxonomy_id=taxonomy.taxonomy_id,
    )
    _progress(
        progress_enabled,
        (
            f"taxonomy {taxonomy.taxonomy_id} control shuffled-label done "
            f"mean_accuracy={shuffled.get('mean_accuracy')} max_accuracy={shuffled.get('max_accuracy')}"
        ),
    )

    hidden_accuracy = best_layer.get("accuracy")
    hidden_f1 = best_layer.get("macro_f1")
    text_accuracy = text_baseline.get("accuracy")
    text_f1 = text_baseline.get("macro_f1")
    lift = {
        "accuracy": float(hidden_accuracy - text_accuracy)
        if hidden_accuracy is not None and text_accuracy is not None
        else None,
        "macro_f1": float(hidden_f1 - text_f1) if hidden_f1 is not None and text_f1 is not None else None,
    }

    nested_best = best_layer.get("nested_lacunarity", {"status": "not_available"})
    report = {
        "taxonomy_id": taxonomy.taxonomy_id,
        "display_name": taxonomy.display_name,
        "role": taxonomy.role,
        "axis": taxonomy.axis,
        "source": taxonomy.source,
        "coherent": bool(taxonomy.coherent),
        "description": taxonomy.description,
        "class_count": int(len(all_classes)),
        "cas_class_count": int(cas_class_count),
        "matched_cardinality_with_cas": int(len(all_classes)) == int(cas_class_count),
        "class_distribution": class_distribution,
        "train_class_distribution": train_class_distribution,
        "test_class_distribution": test_class_distribution,
        "hidden_readout": {
            "best_layer": {
                key: value
                for key, value in best_layer.items()
                if key not in {"class_probability_means", "nested_lacunarity"}
            },
            "per_layer": [
                {
                    key: value
                    for key, value in layer_result.items()
                    if key not in {"class_probability_means", "nested_lacunarity"}
                }
                for layer_result in per_layer
            ],
            "best_layer_location": best_layer.get("layer"),
            "neighbor_stability": _neighbor_stability(per_layer, best_index),
        },
        "text_baseline": text_baseline,
        "lift_over_text": lift,
        "shuffled_label_control": shuffled,
        "lacunarity": {
            "flat_best_layer": best_layer.get("flat_lacunarity"),
            "flat_per_layer": [
                {
                    "layer": int(layer_result["layer"]),
                    "flat_lacunarity": layer_result.get("flat_lacunarity"),
                }
                for layer_result in per_layer
            ],
            "nested_best_layer": nested_best,
            "nested_per_layer": [
                {
                    "layer": int(layer_result["layer"]),
                    "nested_lacunarity": layer_result.get("nested_lacunarity"),
                }
                for layer_result in per_layer
            ],
        },
    }
    _progress(
        progress_enabled,
        (
            f"taxonomy {taxonomy_position} done id={taxonomy.taxonomy_id} "
            f"best_layer={best_layer.get('layer')} best_accuracy={best_layer.get('accuracy')}"
        ),
    )
    return report


def _metric(report: dict[str, Any], path: tuple[str, ...]) -> float | None:
    current: Any = report
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    if current is None:
        return None
    try:
        return float(current)
    except (TypeError, ValueError):
        return None


def _coherent_controls(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        report
        for report in reports
        if report.get("coherent") and report.get("role") != "cas" and report.get("matched_cardinality_with_cas")
    ]


def _nested_scores(report: dict[str, Any]) -> dict[str, float | None]:
    nested = report.get("lacunarity", {}).get("nested_best_layer", {})
    if not isinstance(nested, dict) or nested.get("status") != "available":
        return {
            "parent_factor_lacunarity": None,
            "child_factor_lacunarity": None,
            "joint_class_lacunarity": None,
        }
    return {
        "parent_factor_lacunarity": _metric(nested, ("parent_factor_lacunarity",)),
        "child_factor_lacunarity": _metric(nested, ("child_factor_lacunarity",)),
        "joint_class_lacunarity": _metric(nested, ("joint_class_lacunarity",)),
    }


def _control_nested_ratio_summary(control: dict[str, Any], cas: dict[str, Any]) -> dict[str, Any]:
    control_scores = _nested_scores(control)
    cas_scores = _nested_scores(cas)
    ratios: dict[str, float | None] = {}
    for key, control_value in control_scores.items():
        cas_value = cas_scores.get(key)
        if control_value is None or cas_value is None or cas_value <= 0.0:
            ratios[key] = None
        else:
            ratios[key] = float(control_value / cas_value)

    evaluable = [value for value in ratios.values() if value is not None]
    if not evaluable:
        decision = "NOT_EVALUABLE"
    elif min(evaluable) <= 1.5 + 1e-12:
        decision = "FALSIFY"
    elif min(evaluable) + 1e-12 >= 3.0:
        decision = "PASS"
    else:
        decision = "GREY"
    return {
        "taxonomy_id": control["taxonomy_id"],
        "cas_scores": cas_scores,
        "control_scores": control_scores,
        "control_over_cas_ratios": ratios,
        "minimum_ratio": float(min(evaluable)) if evaluable else None,
        "decision": decision,
    }


def build_verdict(
    *,
    cas_report: dict[str, Any],
    taxonomy_reports: list[dict[str, Any]],
    axis: str,
    cas_lift_threshold_pp: float,
    matched_margin_pp: float,
    scrambled_margin_pp: float,
) -> dict[str, Any]:
    coherent = _coherent_controls(taxonomy_reports)
    scrambled = [report for report in taxonomy_reports if report.get("role") == "scrambled_control"]
    rules: dict[str, Any] = {}
    rationale: list[str] = []
    blocked_reasons: list[str] = []

    if not coherent:
        blocked_reasons.append(
            "missing externally supplied coherent matched taxonomy row-level labels"
        )
    rules["coherent_matched_taxonomy_presence"] = {
        "status": "present" if coherent else "missing",
        "count": len(coherent),
        "required_for_claim_b": True,
    }

    cas_hidden_acc = _metric(cas_report, ("hidden_readout", "best_layer", "accuracy"))
    cas_hidden_f1 = _metric(cas_report, ("hidden_readout", "best_layer", "macro_f1"))
    cas_text_acc = _metric(cas_report, ("text_baseline", "accuracy"))
    cas_text_f1 = _metric(cas_report, ("text_baseline", "macro_f1"))
    cas_lift_acc = _metric(cas_report, ("lift_over_text", "accuracy"))
    cas_lift_f1 = _metric(cas_report, ("lift_over_text", "macro_f1"))
    cas_flat = _metric(cas_report, ("lacunarity", "flat_best_layer"))
    cas_class_count = int(cas_report.get("class_count") or 0)
    chance = 1.0 / cas_class_count if cas_class_count else None

    gate1_pass = cas_lift_acc is not None and cas_lift_acc >= cas_lift_threshold_pp / 100.0
    rules["cas_hidden_readout_lift_over_text"] = {
        "status": "passed" if gate1_pass else "failed",
        "required_accuracy_lift_pp": float(cas_lift_threshold_pp),
        "observed_accuracy_lift_pp": cas_lift_acc * 100.0 if cas_lift_acc is not None else None,
        "observed_macro_f1_lift_pp": cas_lift_f1 * 100.0 if cas_lift_f1 is not None else None,
        "cas_hidden_accuracy": cas_hidden_acc,
        "cas_text_accuracy": cas_text_acc,
        "cas_hidden_macro_f1": cas_hidden_f1,
        "cas_text_macro_f1": cas_text_f1,
    }

    control_margins = []
    gate2_pass = bool(coherent)
    for control in coherent:
        control_acc = _metric(control, ("hidden_readout", "best_layer", "accuracy"))
        control_f1 = _metric(control, ("hidden_readout", "best_layer", "macro_f1"))
        acc_margin = cas_hidden_acc - control_acc if cas_hidden_acc is not None and control_acc is not None else None
        f1_margin = cas_hidden_f1 - control_f1 if cas_hidden_f1 is not None and control_f1 is not None else None
        control_pass = (
            (acc_margin is not None and acc_margin >= matched_margin_pp / 100.0)
            or (f1_margin is not None and f1_margin >= matched_margin_pp / 100.0)
        )
        gate2_pass = gate2_pass and control_pass
        control_margins.append(
            {
                "taxonomy_id": control["taxonomy_id"],
                "accuracy_margin_pp": acc_margin * 100.0 if acc_margin is not None else None,
                "macro_f1_margin_pp": f1_margin * 100.0 if f1_margin is not None else None,
                "passed": bool(control_pass),
            }
        )
    rules["cas_beats_coherent_matched_readout"] = {
        "status": "passed" if gate2_pass else ("not_evaluable" if not coherent else "failed"),
        "required_margin_pp": float(matched_margin_pp),
        "controls": control_margins,
    }

    coherent_flats = [
        (control, _metric(control, ("lacunarity", "flat_best_layer")))
        for control in coherent
        if _metric(control, ("lacunarity", "flat_best_layer")) is not None
    ]
    if cas_flat is None or not coherent_flats:
        gate3_pass = False
        best_control_flat = None
        best_control = None
        gate3_status = "not_evaluable"
    else:
        best_control, best_control_flat = min(coherent_flats, key=lambda item: float(item[1]))
        gate3_pass = best_control_flat > 0.0 and cas_flat <= (best_control_flat / 2.0)
        gate3_status = "passed" if gate3_pass else "failed"
    grey_exception = False
    if not gate3_pass and best_control is not None:
        control_acc = _metric(best_control, ("hidden_readout", "best_layer", "accuracy"))
        control_text = _metric(best_control, ("text_baseline", "accuracy"))
        if (
            control_acc is not None
            and cas_hidden_acc is not None
            and control_text is not None
            and cas_text_acc is not None
            and control_acc > cas_hidden_acc
            and control_text < cas_text_acc
        ):
            grey_exception = True
    rules["cas_flat_lacunarity_2x_cleaner"] = {
        "status": gate3_status,
        "cas_flat_lacunarity": cas_flat,
        "best_coherent_matched_flat_lacunarity": best_control_flat,
        "best_coherent_matched_taxonomy_id": best_control.get("taxonomy_id") if best_control else None,
        "grey_exception_matched_has_higher_readout_and_lower_text_leakage": bool(grey_exception),
    }

    if axis == AXIS_F28:
        nested_controls = [
            control
            for control in coherent
            if control.get("lacunarity", {}).get("nested_best_layer", {}).get("status") == "available"
        ]
        nested_rows = [
            _control_nested_ratio_summary(control, cas_report)
            for control in nested_controls
        ]
        if not nested_controls:
            nested_decision = "NOT_EVALUABLE"
        elif any(row["decision"] == "FALSIFY" for row in nested_rows):
            nested_decision = "FALSIFY"
        elif all(row["decision"] == "PASS" for row in nested_rows):
            nested_decision = "PASS"
        else:
            nested_decision = "GREY"
        gate4_pass = nested_decision == "PASS"
        gate4_falsify = nested_decision == "FALSIFY"
        gate4_grey = nested_decision == "GREY"
        rules["f28_nested_lacunarity_ratio_gate"] = {
            "status": nested_decision,
            "description": (
                "For Stage X.1 F28, the externally supplied coherent matched taxonomy "
                "must be at least 3x worse than CAS on every evaluable nested split. "
                "Within 1.5x falsifies; 1.5x-3x is grey."
            ),
            "pass_threshold_control_over_cas_ratio": 3.0,
            "falsify_threshold_control_over_cas_ratio": 1.5,
            "controls": nested_rows,
        }
        rules["f28_nested_lacunarity_beats_7x4_control"] = {
            "status": "superseded",
            "superseded_by": "f28_nested_lacunarity_ratio_gate",
            "reason": "Refined Stage X.1 gate uses 3x / 1.5x nested lacunarity ratios.",
        }
    else:
        gate4_pass = True
        gate4_falsify = False
        gate4_grey = False
        rules["f28_nested_lacunarity_ratio_gate"] = {
            "status": "NOT_APPLICABLE",
            "reason": "nested F28 ratio gate applies only to axis=f28",
        }
        rules["f28_nested_lacunarity_beats_7x4_control"] = {
            "status": "not_applicable",
            "reason": "nested F28 gate applies only to axis=f28",
        }

    if not scrambled or chance is None:
        gate5_pass = False
        scrambled_status = "not_evaluable"
        scrambled_rows = []
    else:
        scrambled_rows = []
        gate5_pass = True
        for control in scrambled:
            acc = _metric(control, ("hidden_readout", "best_layer", "accuracy"))
            max_shuffle = _metric(control, ("shuffled_label_control", "max_accuracy"))
            near_chance_threshold = chance + scrambled_margin_pp / 100.0
            near_chance = acc is not None and acc <= near_chance_threshold
            not_cleaner = True
            flat = _metric(control, ("lacunarity", "flat_best_layer"))
            if flat is not None and cas_flat is not None:
                not_cleaner = flat >= cas_flat
            control_pass = bool(near_chance and not_cleaner)
            gate5_pass = gate5_pass and control_pass
            scrambled_rows.append(
                {
                    "taxonomy_id": control["taxonomy_id"],
                    "accuracy": acc,
                    "chance_accuracy": chance,
                    "near_chance_threshold": near_chance_threshold,
                    "max_shuffled_accuracy": max_shuffle,
                    "flat_lacunarity": flat,
                    "not_cleaner_than_cas_flat_lacunarity": bool(not_cleaner),
                    "passed": control_pass,
                }
            )
        scrambled_status = "passed" if gate5_pass else "failed"
    rules["scrambled_cas_near_chance_no_clean_structure"] = {
        "status": scrambled_status,
        "chance_accuracy": chance,
        "near_chance_margin_pp": float(scrambled_margin_pp),
        "controls": scrambled_rows,
    }

    fail_controls: list[dict[str, Any]] = []
    for control in coherent:
        control_lift = _metric(control, ("lift_over_text", "accuracy"))
        control_flat = _metric(control, ("lacunarity", "flat_best_layer"))
        readout_matches = (
            control_lift is not None and cas_lift_acc is not None and control_lift >= cas_lift_acc
        )
        flat_matches = control_flat is not None and cas_flat is not None and control_flat <= cas_flat
        nested_matches = True
        nested_ratio_summary = None
        if axis == AXIS_F28 and control.get("lacunarity", {}).get("nested_best_layer", {}).get("status") == "available":
            nested_ratio_summary = _control_nested_ratio_summary(control, cas_report)
            nested_matches = nested_ratio_summary["decision"] == "FALSIFY"
        if readout_matches and flat_matches and nested_matches:
            fail_controls.append(
                {
                    "taxonomy_id": control["taxonomy_id"],
                    "control_lift_accuracy": control_lift,
                    "cas_lift_accuracy": cas_lift_acc,
                    "control_flat_lacunarity": control_flat,
                    "cas_flat_lacunarity": cas_flat,
                    "nested_ratio_summary": nested_ratio_summary,
                }
            )

    hard_fail = bool(fail_controls) or not gate1_pass or not gate5_pass or gate4_falsify
    all_required_pass = gate1_pass and gate2_pass and gate3_pass and gate4_pass and gate5_pass
    if blocked_reasons:
        status = "blocked"
    elif hard_fail:
        status = "falsify"
    elif all_required_pass:
        status = "pass"
    else:
        status = "grey"

    if status == "pass":
        rationale.append("CAS passed readout lift and matched-taxonomy lacunarity gates.")
    elif status == "blocked":
        rationale.extend(blocked_reasons)
    elif status == "falsify":
        if fail_controls:
            rationale.append(
                "At least one coherent matched taxonomy matched or beat CAS on lift and lacunarity."
            )
        if not gate1_pass:
            rationale.append("CAS hidden readout did not clear the pre-registered text-lift gate.")
        if not gate5_pass:
            rationale.append("Scrambled-label controls were missing or did not remain near chance.")
        if gate4_falsify:
            rationale.append(
                "The coherent matched F28 taxonomy was within 1.5x of CAS nested lacunarity."
            )
    else:
        rationale.append(
            "CAS did not fully satisfy both readout and lacunarity gates; uniqueness remains open."
        )
        if grey_exception:
            rationale.append(
                "The flat-lacunarity rule hit the pre-registered grey exception for a matched taxonomy."
            )
        if gate4_grey:
            rationale.append(
                "The coherent matched F28 taxonomy landed in the 1.5x-3x nested lacunarity grey band."
            )

    decision = "FALSIFY" if status == "falsify" else status.upper()
    return {
        "status": status,
        "decision": decision,
        "pass": status == "pass",
        "grey": status == "grey",
        "falsify": status == "falsify",
        "fail": status == "falsify",
        "blocked": status == "blocked",
        "blocked_reasons": blocked_reasons,
        "rules": rules,
        "fail_controls": fail_controls,
        "rationale": rationale,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--axis", required=True, choices=(AXIS_40E, AXIS_F28))
    parser.add_argument(
        "--original-labels",
        type=Path,
        help="Optional JSON/JSONL labels file. NPZ label arrays remain the default source.",
    )
    parser.add_argument("--layers", default="all", help="'all' or a comma-separated layer id list")
    parser.add_argument("--split-mode", choices=("auto", "group", "stratified"), default="auto")
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=20260530)
    parser.add_argument(
        "--shuffled-seeds",
        default=",".join(str(seed) for seed in DEFAULT_SHUFFLED_SEEDS),
        help=(
            "Comma-separated fixed seeds for shuffled-label controls. "
            "Default is the five pre-registered seeds; use --smoke-one-shuffled-seed "
            "for a one-seed operability run."
        ),
    )
    parser.add_argument(
        "--smoke-one-shuffled-seed",
        action="store_true",
        help=(
            "Smoke mode: use only the first shuffled-label seed. This does not change "
            "selected layers, probe settings, or the balanced logistic method."
        ),
    )
    parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Print taxonomy/layer/control progress to stderr.",
    )
    parser.add_argument("--probe-C", type=float, default=0.1)
    parser.add_argument("--text-C", type=float, default=1.0)
    parser.add_argument("--probe-max-iter", type=int, default=1000)
    parser.add_argument("--text-max-features", type=int, default=2**14)
    parser.add_argument("--cas-lift-threshold-pp", type=float, default=20.0)
    parser.add_argument("--matched-margin-pp", type=float, default=5.0)
    parser.add_argument("--scrambled-near-chance-margin-pp", type=float, default=5.0)
    parser.add_argument(
        "--add-scrambled-cas-taxonomy",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Add the preregistered scrambled-CAS taxonomy using the first shuffled seed.",
    )
    args = parser.parse_args()

    if not (0.0 < args.test_size < 1.0):
        raise SystemExit("--test-size must be between 0 and 1")

    metadata = _load_jsonish(args.metadata)
    manifest = _load_jsonish(args.manifest)
    original_labels = _load_jsonish(args.original_labels) if args.original_labels else None
    loaded = _load_dataset(args.dataset, metadata)
    selected_layers = _parse_layers(args.layers, loaded.layers)
    layer_to_index = {int(layer): index for index, layer in enumerate(loaded.layers.tolist())}
    shuffled_seeds = _parse_seed_list(args.shuffled_seeds)
    requested_shuffled_seeds = list(shuffled_seeds)
    if args.smoke_one_shuffled_seed:
        shuffled_seeds = shuffled_seeds[:1]
    if not shuffled_seeds:
        raise SystemExit("--shuffled-seeds must provide at least one seed")

    _progress(
        args.progress,
        (
            f"loaded dataset samples={loaded.features.shape[0]} layers={loaded.features.shape[1]} "
            f"hidden_dim={loaded.features.shape[2]} selected_layers={selected_layers} "
            f"shuffled_seeds={shuffled_seeds} smoke_one_shuffled_seed={args.smoke_one_shuffled_seed}"
        ),
    )

    cas_taxonomy = _build_cas_taxonomy(
        axis=args.axis,
        dataset_path=args.dataset,
        loaded=loaded,
        metadata=metadata,
        original_labels=original_labels,
    )
    taxonomies = [
        spec
        for spec in load_taxonomy_manifest(
            manifest,
            axis=args.axis,
            n_samples=loaded.features.shape[0],
            sample_ids=loaded.sample_ids,
        )
        if spec.role != "cas"
    ]
    if args.add_scrambled_cas_taxonomy and not any(spec.role == "scrambled_control" for spec in taxonomies):
        taxonomies.append(_make_scrambled_taxonomy(cas_taxonomy, seed=shuffled_seeds[0]))
    coherent_manifest_count = sum(
        1
        for spec in taxonomies
        if spec.coherent and spec.role != "scrambled_control" and spec.source == "matched_taxonomy_manifest"
    )
    scrambled_control_count = sum(1 for spec in taxonomies if spec.role == "scrambled_control")
    _progress(
        args.progress,
        (
            f"prepared taxonomies total={1 + len(taxonomies)} coherent_manifest={coherent_manifest_count} "
            f"scrambled_controls={scrambled_control_count}"
        ),
    )

    train_idx, test_idx, split_manifest = _split_indices(
        features=loaded.features,
        labels=cas_taxonomy.labels,
        prompts=loaded.prompts,
        test_size=args.test_size,
        seed=args.seed,
        split_mode=args.split_mode,
    )
    _progress(
        args.progress,
        (
            f"split ready type={split_manifest['type']} train={len(train_idx)} "
            f"test={len(test_idx)} seed={args.seed}"
        ),
    )

    cas_class_count = len(set(cas_taxonomy.labels.tolist()))
    all_specs = [cas_taxonomy, *taxonomies]
    taxonomy_reports = []
    for taxonomy_index, spec in enumerate(all_specs, start=1):
        taxonomy_reports.append(
            evaluate_taxonomy(
                taxonomy=spec,
                loaded=loaded,
                selected_layers=selected_layers,
                layer_to_index=layer_to_index,
                train_idx=train_idx,
                test_idx=test_idx,
                shuffled_seeds=shuffled_seeds,
                probe_C=args.probe_C,
                text_C=args.text_C,
                probe_max_iter=args.probe_max_iter,
                text_max_features=args.text_max_features,
                cas_class_count=cas_class_count,
                progress_enabled=args.progress,
                taxonomy_index=taxonomy_index,
                taxonomy_total=len(all_specs),
            )
        )
    cas_report = taxonomy_reports[0]
    verdict = build_verdict(
        cas_report=cas_report,
        taxonomy_reports=taxonomy_reports,
        axis=args.axis,
        cas_lift_threshold_pp=args.cas_lift_threshold_pp,
        matched_margin_pp=args.matched_margin_pp,
        scrambled_margin_pp=args.scrambled_near_chance_margin_pp,
    )

    model_provenance = metadata.get("model_provenance") if isinstance(metadata, dict) else None
    if model_provenance is None and isinstance(metadata, dict):
        model_provenance = {
            key: metadata.get(key)
            for key in ("model_id", "model_name", "model_family", "parameter_scale", "model_scale")
            if metadata.get(key) is not None
        }
    model_scope_text = json.dumps(model_provenance or {}, sort_keys=True, default=_json_default).lower()
    stage_x1_model_scope = "confirmed_20b_target" if "20b" in model_scope_text or "20 b" in model_scope_text else "not_confirmed_20b_in_metadata"

    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "created_at": datetime.now(UTC).isoformat(),
        "preregistration": {
            "document": PREREG_DOC,
            "date": "2026-05-30",
            "runner_lane_only": True,
        },
        "stage_scope": {
            "decision_stage": "Stage X.1",
            "scope": "20B-only matched-taxonomy decision gate",
            "executed_now": True,
            "model_scope_check": stage_x1_model_scope,
            "cross_architecture_extension": {
                "stage": "Stage X.2",
                "status": "conditional_not_executed",
                "condition": "Execute only after Stage X.1 returns PASS on the 20B target.",
            },
        },
        "axis": args.axis,
        "pass": verdict["pass"],
        "grey": verdict["grey"],
        "falsify": verdict["falsify"],
        "fail": verdict["fail"],
        "blocked": verdict["blocked"],
        "verdict": verdict,
        "method_contract": {
            "hidden_readout": "StandardScaler + LogisticRegression",
            "class_weight": "balanced",
            "solver": "lbfgs",
            "probe_C": float(args.probe_C),
            "text_baseline": "CountVectorizer(1-2 grams) + LogisticRegression(class_weight='balanced')",
            "text_C": float(args.text_C),
            "probe_max_iter": int(args.probe_max_iter),
            "layers": selected_layers,
            "flat_lacunarity": "Var(mean heldout class probability) / Mean^2 over taxonomy readout classes",
            "nested_lacunarity": (
                "same Var/Mean^2 after aggregating heldout class probabilities "
                "to parent and child factors when factor labels are supplied"
            ),
            "matched_alternative_label_source": (
                "externally supplied manifest labels only; the runner generates only "
                "the preregistered scrambled-CAS permutation control"
            ),
            "stage_x1_f28_nested_gate": (
                "PASS if every coherent matched F28 nested split is >=3x worse than CAS; "
                "FALSIFY if any is within 1.5x; GREY for 1.5x-3x"
            ),
        },
        "run_settings": {
            "progress_enabled": bool(args.progress),
            "smoke_settings_used": bool(args.smoke_one_shuffled_seed),
            "smoke_one_shuffled_seed": bool(args.smoke_one_shuffled_seed),
            "requested_shuffled_seed_count": int(len(requested_shuffled_seeds)),
            "selected_shuffled_seed_count": int(len(shuffled_seeds)),
            "requested_shuffled_label_seeds": [int(seed) for seed in requested_shuffled_seeds],
            "selected_shuffled_label_seeds": [int(seed) for seed in shuffled_seeds],
            "available_layers": [int(layer) for layer in loaded.layers.tolist()],
            "available_layer_count": int(len(loaded.layers)),
            "selected_layers": selected_layers,
            "selected_layer_count": int(len(selected_layers)),
            "layers_arg": args.layers,
            "method_changed_for_smoke": False,
        },
        "fixed_seeds": {
            "split_seed": int(args.seed),
            "shuffled_label_seeds": [int(seed) for seed in shuffled_seeds],
            "shuffled_label_seed_count": int(len(shuffled_seeds)),
            "scrambled_taxonomy_seed": int(shuffled_seeds[0]) if args.add_scrambled_cas_taxonomy else None,
        },
        "split_manifest": split_manifest,
        "dataset_summary": {
            "dataset": str(args.dataset),
            "metadata": str(args.metadata),
            "manifest": str(args.manifest),
            "original_labels": str(args.original_labels) if args.original_labels else None,
            "n_samples": int(loaded.features.shape[0]),
            "n_layers": int(loaded.features.shape[1]),
            "hidden_dim": int(loaded.features.shape[2]),
            "layers": [int(layer) for layer in loaded.layers.tolist()],
            "selected_layers": selected_layers,
            "selected_layer_count": int(len(selected_layers)),
            "npz_keys": list(loaded.npz_keys),
            "cas_class_count": int(cas_class_count),
            "taxonomy_count": int(len(taxonomy_reports)),
            "externally_supplied_coherent_matched_taxonomy_count": int(coherent_manifest_count),
            "scrambled_cas_taxonomy_count": int(scrambled_control_count),
        },
        "model_provenance": model_provenance,
        "artifacts": [
            _artifact_descriptor("activation_dataset_npz", "activation_dataset_npz", args.dataset),
            _artifact_descriptor("metadata_json", "metadata_json", args.metadata),
            _artifact_descriptor("matched_taxonomy_manifest_json", "matched_taxonomy_manifest_json", args.manifest),
        ]
        + (
            [_artifact_descriptor("original_labels_json", "original_labels_json", args.original_labels)]
            if args.original_labels
            else []
        ),
        "taxonomy_reports": taxonomy_reports,
        "evidence_packet_requirements": {
            "cas_taxonomy_report": "present",
            "coherent_cardinality_matched_alternative": (
                "present_externally_supplied"
                if coherent_manifest_count
                else "missing_from_manifest"
            ),
            "scrambled_cas_permutation": "present" if scrambled_control_count else "missing",
            "matched_taxonomy_reports": "present" if coherent_manifest_count else "missing",
            "text_baseline_reports": "present",
            "shuffled_label_controls": "present",
            "flat_lacunarity_table": "present",
            "nested_lacunarity_table": "present_if_factor_labels_available",
            "fixed_seed_list": "present",
            "split_manifest_hash": split_manifest["content_sha256"],
            "scenario_artifact_hashes": "manifest_and_dataset_hashes_present",
            "model_provenance": "present" if model_provenance else "not_present_in_metadata",
            "explicit_pass_grey_fail_verdict": verdict["status"],
            "explicit_pass_grey_falsify_verdict": verdict["decision"],
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )
    print(f"wrote matched-taxonomy control report: {args.output}")
    print(f"verdict: {verdict['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
