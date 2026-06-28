#!/usr/bin/env python3
"""Materialize row-level coherent matched-taxonomy labels.

This script turns the 2026-05-30 design manifest into runner-compatible
row-level taxonomies. It only uses explicit non-CAS control annotations or the
manifest's allowed non-CAS text fields to form candidate labels. Source CAS
labels, when present, are used only to recover splitwise quota counts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "cas_harness_matched_taxonomy_assignments.v1"
ALGORITHM_VERSION = "materialize_matched_taxonomy_assignments.py:v1"

SOURCE_AXIS_TO_RUNNER_AXIS = {
    "stage9_40e": "40e",
    "stage7_f28": "f28",
}
RUNNER_AXIS_TO_SOURCE_AXIS = {value: key for key, value in SOURCE_AXIS_TO_RUNNER_AXIS.items()}
RECORD_LIST_KEYS = ("samples", "records", "scenarios", "items", "rows")
SPLIT_TRAIN_VALUES = {"train", "training"}
SPLIT_TEST_VALUES = {"test", "heldout", "holdout", "eval", "evaluation", "dev", "validation", "val"}
SOURCE_DATASET_SHA_KEYS = (
    "source_dataset_sha256",
    "dataset_artifact_sha256",
    "activation_dataset_sha256",
    "source_activation_sha256",
)
SOURCE_40E_LABEL_KEYS = (
    "labels_40e",
    "labels_40_element",
    "forty_element_label",
    "cas_40e_label",
    "cas_label",
)
SOURCE_F28_LABEL_KEYS = (
    "labels_f28",
    "labels_foundation",
    "foundation_28",
    "f28_label",
    "cas_f28_label",
    "cas_label",
)


@dataclass(frozen=True)
class RowBase:
    row_index: int
    record: dict[str, Any]
    row_key: str
    row_key_source: str
    sample_id: str


@dataclass(frozen=True)
class Row:
    row_index: int
    record: dict[str, Any]
    row_key: str
    row_key_source: str
    sample_id: str
    split: str


@dataclass(frozen=True)
class ControlSpec:
    manifest_key: str
    control_id: str
    source_axis: str
    runner_axis: str
    seed: int
    labels: list[str]
    parent_values: list[str]
    child_values: list[str]
    label_to_parent_child: dict[str, tuple[str, str]]
    explicit_parent_field: str
    explicit_child_field: str
    candidate_text_fields: list[str]
    parent_keywords: dict[str, list[str]]
    child_keywords: dict[str, list[str]]
    parent_axis_name: str
    child_axis_name: str
    block_status: str


@dataclass(frozen=True)
class CandidateRow:
    row: Row
    candidate_labels: list[str]
    assignment_source: str
    source_text_fields_used: list[str]
    candidate_parent_values: list[str]
    candidate_child_values: list[str]
    candidate_notes: list[str]


class BlockingError(Exception):
    """Raised when a claim-bearing assignment cannot be materialized fairly."""

    def __init__(
        self,
        status: str,
        reason: str,
        *,
        control_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(reason)
        self.status = status
        self.reason = reason
        self.control_id = control_id
        self.details = details or {}


class _Edge:
    __slots__ = ("to", "rev", "cap")

    def __init__(self, to: int, rev: int, cap: int) -> None:
        self.to = to
        self.rev = rev
        self.cap = cap


class _Dinic:
    def __init__(self, size: int) -> None:
        self.graph: list[list[_Edge]] = [[] for _ in range(size)]
        self.level = [0] * size
        self.it = [0] * size

    def add_edge(self, source: int, target: int, cap: int) -> _Edge:
        forward = _Edge(target, len(self.graph[target]), cap)
        reverse = _Edge(source, len(self.graph[source]), 0)
        self.graph[source].append(forward)
        self.graph[target].append(reverse)
        return forward

    def _bfs(self, source: int, sink: int) -> bool:
        self.level = [-1] * len(self.graph)
        self.level[source] = 0
        queue: deque[int] = deque([source])
        while queue:
            node = queue.popleft()
            for edge in self.graph[node]:
                if edge.cap > 0 and self.level[edge.to] < 0:
                    self.level[edge.to] = self.level[node] + 1
                    queue.append(edge.to)
        return self.level[sink] >= 0

    def _dfs(self, node: int, sink: int, flow: int) -> int:
        if node == sink:
            return flow
        while self.it[node] < len(self.graph[node]):
            edge = self.graph[node][self.it[node]]
            if edge.cap > 0 and self.level[node] < self.level[edge.to]:
                pushed = self._dfs(edge.to, sink, min(flow, edge.cap))
                if pushed:
                    edge.cap -= pushed
                    self.graph[edge.to][edge.rev].cap += pushed
                    return pushed
            self.it[node] += 1
        return 0

    def max_flow(self, source: int, sink: int) -> int:
        total = 0
        while self._bfs(source, sink):
            self.it = [0] * len(self.graph)
            while True:
                pushed = self._dfs(source, sink, 10**9)
                if not pushed:
                    break
                total += pushed
        return total


def _json_default(value: Any) -> Any:
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


def _stable_hash_text(*parts: Any) -> str:
    text = "\0".join(_as_text(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_hash_int(*parts: Any) -> int:
    return int(_stable_hash_text(*parts), 16)


def _get_path(payload: Any, path: str) -> Any:
    if not isinstance(payload, dict):
        return None
    if path in payload:
        return payload[path]
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _first_path(payload: dict[str, Any], paths: tuple[str, ...]) -> tuple[str | None, Any]:
    for path in paths:
        value = _get_path(payload, path)
        if value is not None:
            return path, value
    return None, None


def _normalise_split(value: Any) -> str | None:
    text = _as_text(value).strip().lower()
    if text in SPLIT_TRAIN_VALUES:
        return "train"
    if text in SPLIT_TEST_VALUES:
        return "test"
    return None


def _extract_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in RECORD_LIST_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def _metadata_sample_ids(payload: Any) -> list[str] | None:
    if not isinstance(payload, dict):
        return None
    raw = _get_path(payload, "metadata.sample_ids")
    if isinstance(raw, list):
        return [_as_text(value) for value in raw]
    return None


def _discover_source_dataset_sha(payload: Any, explicit: str | None) -> str | None:
    if explicit:
        return explicit
    if isinstance(payload, dict):
        for key in SOURCE_DATASET_SHA_KEYS:
            value = _get_path(payload, key)
            if value is not None:
                return _as_text(value)
            value = _get_path(payload, f"metadata.{key}")
            if value is not None:
                return _as_text(value)
    return None


def _row_id_value(record: dict[str, Any], index: int, metadata_ids: list[str] | None) -> tuple[str | None, str | None]:
    for path in ("scenario.id", "id"):
        value = _get_path(record, path)
        if value is not None and _as_text(value):
            return _as_text(value), path
    for path in ("scenario.sample_id", "sample_id"):
        value = _get_path(record, path)
        if value is not None and _as_text(value):
            return _as_text(value), path
    if metadata_ids is not None and index < len(metadata_ids) and metadata_ids[index]:
        return metadata_ids[index], "metadata.sample_ids"
    return None, None


def _sample_id_value(record: dict[str, Any], index: int, metadata_ids: list[str] | None, row_key: str) -> str:
    for path in ("scenario.sample_id", "sample_id", "id", "scenario.id"):
        value = _get_path(record, path)
        if value is not None and _as_text(value):
            return _as_text(value)
    if metadata_ids is not None and index < len(metadata_ids) and metadata_ids[index]:
        return metadata_ids[index]
    return row_key


def _build_row_bases(
    records: list[dict[str, Any]],
    *,
    scenario_payload: Any,
    source_scenario_sha256: str,
    source_dataset_sha256: str | None,
) -> list[RowBase]:
    metadata_ids = _metadata_sample_ids(scenario_payload)
    bases: list[RowBase] = []
    fallback_sha = source_dataset_sha256 or source_scenario_sha256
    fallback_source = "sha256(dataset_artifact_sha256 + ':' + row_index)"
    if source_dataset_sha256 is None:
        fallback_source = "sha256(source_scenario_sha256 + ':' + row_index)"
    for index, record in enumerate(records):
        row_key, row_key_source = _row_id_value(record, index, metadata_ids)
        if row_key is None:
            row_key = _stable_hash_text(fallback_sha, index)
            row_key_source = fallback_source
        sample_id = _sample_id_value(record, index, metadata_ids, row_key)
        bases.append(
            RowBase(
                row_index=index,
                record=record,
                row_key=row_key,
                row_key_source=row_key_source or "unknown",
                sample_id=sample_id,
            )
        )
    return bases


def _add_split_items(
    lookup: dict[int, str],
    values: Any,
    split: str,
    *,
    id_to_index: dict[str, int],
    row_count: int,
) -> None:
    if values is None:
        return
    if isinstance(values, dict):
        values = values.get("indices", values.get("ids", values.get("sample_ids", [])))
    if not isinstance(values, list):
        return
    for value in values:
        text = _as_text(value)
        index: int | None = None
        if isinstance(value, int):
            index = value
        elif text.isdigit():
            index = int(text)
        elif text in id_to_index:
            index = id_to_index[text]
        if index is not None and 0 <= index < row_count:
            lookup[index] = split


def _split_lookup_from_object(split_payload: Any, bases: list[RowBase]) -> dict[int, str]:
    lookup: dict[int, str] = {}
    id_to_index: dict[str, int] = {}
    for row in bases:
        id_to_index.setdefault(str(row.row_index), row.row_index)
        id_to_index.setdefault(row.row_key, row.row_index)
        id_to_index.setdefault(row.sample_id, row.row_index)

    if not isinstance(split_payload, dict):
        return lookup

    for key in ("splits", "split_manifest", "split"):
        nested = split_payload.get(key)
        if isinstance(nested, dict):
            lookup.update(_split_lookup_from_object(nested, bases))

    for key in ("train_indices", "training_indices", "train_ids", "training_ids", "train"):
        _add_split_items(lookup, split_payload.get(key), "train", id_to_index=id_to_index, row_count=len(bases))
    for key in ("test_indices", "heldout_indices", "holdout_indices", "test_ids", "heldout_ids", "test"):
        _add_split_items(lookup, split_payload.get(key), "test", id_to_index=id_to_index, row_count=len(bases))

    for key, value in split_payload.items():
        split = _normalise_split(value)
        if split is not None and key in id_to_index:
            lookup[id_to_index[key]] = split
    return lookup


def _assign_splits(
    bases: list[RowBase],
    *,
    scenario_payload: Any,
    split_payload: Any | None,
) -> tuple[list[Row], dict[str, Any]]:
    rows: list[Row] = []
    missing: list[int] = []
    embedded_lookup = _split_lookup_from_object(split_payload, bases) if split_payload is not None else {}
    if not embedded_lookup:
        embedded_lookup = _split_lookup_from_object(scenario_payload, bases)

    split_indices = {"train": [], "test": []}
    for base in bases:
        split = None
        for path in ("split", "metadata.split", "scenario.split", "partition", "membership"):
            split = _normalise_split(_get_path(base.record, path))
            if split is not None:
                break
        if split is None:
            split = embedded_lookup.get(base.row_index)
        if split is None:
            missing.append(base.row_index)
            continue
        split_indices[split].append(base.row_index)
        rows.append(
            Row(
                row_index=base.row_index,
                record=base.record,
                row_key=base.row_key,
                row_key_source=base.row_key_source,
                sample_id=base.sample_id,
                split=split,
            )
        )

    split_manifest = {
        "n_train": len(split_indices["train"]),
        "n_test": len(split_indices["test"]),
        "train_indices": split_indices["train"],
        "test_indices": split_indices["test"],
        "source": "explicit_row_or_embedded_split_manifest",
    }
    split_manifest["content_sha256"] = _sha256_json(split_manifest)
    if missing:
        raise BlockingError(
            "blocked_missing_frozen_split_manifest",
            "scenario rows do not fully identify the frozen train/test split",
            details={"missing_row_indices": missing[:20], "missing_row_count": len(missing)},
        )
    if not split_indices["train"] or not split_indices["test"]:
        raise BlockingError(
            "blocked_missing_frozen_split_manifest",
            "frozen split must contain both train and test rows",
            details={"split_counts": {"train": len(split_indices["train"]), "test": len(split_indices["test"])}},
        )
    return rows, split_manifest


def _manifest_controls(manifest: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(manifest, dict) or not isinstance(manifest.get("controls"), dict):
        raise BlockingError("blocked_invalid_manifest", "manifest does not contain a controls object")
    return manifest["controls"]


def _control_aliases(control_key: str, control: dict[str, Any]) -> set[str]:
    control_id = _as_text(control.get("control_id", control_key))
    aliases = {control_key.lower(), control_id.lower()}
    if control_id.startswith("NC40") or "nc40" in control_key.lower():
        aliases.update({"nc40", "40e", "topic_frame"})
    if control_id.startswith("NC28") or "nc28" in control_key.lower():
        aliases.update({"nc28", "f28", "topic_function"})
    return aliases


def _label_for_pair(control_id: str, parent: str, child: str) -> str:
    if control_id.startswith("NC40"):
        return f"NC40_{parent}_{child}"
    if control_id.startswith("NC28"):
        return f"NC28_{parent}_{child}"
    return f"{control_id}_{parent}_{child}"


def _build_control_spec(control_key: str, control: dict[str, Any]) -> ControlSpec:
    control_id = _as_text(control.get("control_id", control_key))
    source_axis = _as_text(control.get("source_axis"))
    if source_axis not in SOURCE_AXIS_TO_RUNNER_AXIS:
        raise BlockingError(
            "blocked_invalid_manifest",
            f"control {control_id} uses unsupported source_axis={source_axis!r}",
            control_id=control_id,
        )
    mapping_rule = control.get("mapping_rule") if isinstance(control.get("mapping_rule"), dict) else {}
    keyword_rules = control.get("keyword_rules") if isinstance(control.get("keyword_rules"), dict) else {}
    explicit_fields = mapping_rule.get("explicit_field_priority")
    if not isinstance(explicit_fields, list) or len(explicit_fields) < 2:
        raise BlockingError(
            "blocked_invalid_manifest",
            f"control {control_id} is missing two explicit field paths",
            control_id=control_id,
        )

    parent_values = control.get("topic_axis")
    if not isinstance(parent_values, list):
        raise BlockingError(
            "blocked_invalid_manifest",
            f"control {control_id} is missing topic_axis",
            control_id=control_id,
        )
    child_axis_key = "frame_axis" if "frame_axis" in control else "function_axis"
    child_values = control.get(child_axis_key)
    if not isinstance(child_values, list):
        raise BlockingError(
            "blocked_invalid_manifest",
            f"control {control_id} is missing {child_axis_key}",
            control_id=control_id,
        )

    labels = control.get("labels")
    if not isinstance(labels, list):
        raise BlockingError(
            "blocked_invalid_manifest",
            f"control {control_id} is missing label space",
            control_id=control_id,
        )
    labels = [_as_text(label) for label in labels]
    expected = [_label_for_pair(control_id, _as_text(parent), _as_text(child)) for parent in parent_values for child in child_values]
    if labels != expected:
        raise BlockingError(
            "blocked_invalid_manifest",
            f"control {control_id} label order does not match topic/function cross product",
            control_id=control_id,
            details={"expected_first_labels": expected[:5], "actual_first_labels": labels[:5]},
        )

    child_keyword_key = "frames" if "frames" in keyword_rules else "functions"
    parent_keywords = keyword_rules.get("topics")
    child_keywords = keyword_rules.get(child_keyword_key)
    if not isinstance(parent_keywords, dict) or not isinstance(child_keywords, dict):
        raise BlockingError(
            "blocked_invalid_manifest",
            f"control {control_id} is missing keyword dictionaries",
            control_id=control_id,
        )

    seed = int(control.get("assignment_seed", 0))
    label_to_parent_child: dict[str, tuple[str, str]] = {}
    for parent in parent_values:
        for child in child_values:
            label_to_parent_child[_label_for_pair(control_id, _as_text(parent), _as_text(child))] = (
                _as_text(parent),
                _as_text(child),
            )

    candidate_text_fields = mapping_rule.get("candidate_text_fields")
    if not isinstance(candidate_text_fields, list):
        candidate_text_fields = []

    return ControlSpec(
        manifest_key=control_key,
        control_id=control_id,
        source_axis=source_axis,
        runner_axis=SOURCE_AXIS_TO_RUNNER_AXIS[source_axis],
        seed=seed,
        labels=labels,
        parent_values=[_as_text(value) for value in parent_values],
        child_values=[_as_text(value) for value in child_values],
        label_to_parent_child=label_to_parent_child,
        explicit_parent_field=_as_text(explicit_fields[0]),
        explicit_child_field=_as_text(explicit_fields[1]),
        candidate_text_fields=[_as_text(value) for value in candidate_text_fields],
        parent_keywords={_as_text(key): [_as_text(item) for item in value] for key, value in parent_keywords.items()},
        child_keywords={_as_text(key): [_as_text(item) for item in value] for key, value in child_keywords.items()},
        parent_axis_name=_as_text(control.get("parent_axis_name", "topic")),
        child_axis_name=_as_text(control.get("child_axis_name", "frame_or_function")),
        block_status=_as_text(mapping_rule.get("block_status", "blocked_insufficient_control_candidate_cover")),
    )


def _select_controls(
    manifest: Any,
    *,
    requested: list[str],
    axis: str | None,
) -> list[ControlSpec]:
    specs: list[ControlSpec] = []
    requested_lower = {value.lower() for value in requested}
    source_axis = RUNNER_AXIS_TO_SOURCE_AXIS.get(axis or "") if axis else None
    for control_key, control in _manifest_controls(manifest).items():
        if control_key == "scrambled_cas" or not isinstance(control, dict) or "mapping_rule" not in control:
            continue
        aliases = _control_aliases(control_key, control)
        if requested_lower and not requested_lower.intersection(aliases):
            continue
        if source_axis is not None and _as_text(control.get("source_axis")) != source_axis:
            continue
        specs.append(_build_control_spec(control_key, control))
    if not specs:
        raise BlockingError(
            "blocked_no_requested_controls",
            "no coherent non-CAS controls matched the requested control ids and axis",
            details={"requested": requested, "axis": axis},
        )
    return specs


def _value_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [_as_text(value).strip() for value in raw if _as_text(value).strip()]
    text = _as_text(raw).strip()
    if not text:
        return []
    return [text]


def _allowed_text_field_values(record: dict[str, Any], field_name: str) -> tuple[list[str], list[str]]:
    values: list[str] = []
    used_paths: list[str] = []
    for path in (field_name, f"metadata.{field_name}", f"scenario.{field_name}"):
        raw = _get_path(record, path)
        if isinstance(raw, dict):
            continue
        items = _value_list(raw)
        if items:
            values.extend(items)
            used_paths.append(path)
    return values, used_paths


def _keyword_matches(keyword: str, haystack: str) -> bool:
    needle = keyword.strip().lower()
    if not needle:
        return False
    if re.search(r"\s", needle):
        return needle in haystack
    return re.search(rf"(?<![a-z0-9_]){re.escape(needle)}(?![a-z0-9_])", haystack) is not None


def _keyword_candidates(keywords: dict[str, list[str]], text: str, value_order: list[str]) -> list[str]:
    matches: list[str] = []
    for value in value_order:
        for keyword in keywords.get(value, []):
            if _keyword_matches(keyword, text):
                matches.append(value)
                break
    return matches


def _candidate_labels_for_row(row: Row, control: ControlSpec) -> CandidateRow:
    parent_raw = _get_path(row.record, control.explicit_parent_field)
    child_raw = _get_path(row.record, control.explicit_child_field)
    if parent_raw is not None or child_raw is not None:
        parents = [value for value in _value_list(parent_raw) if value in control.parent_values]
        children = [value for value in _value_list(child_raw) if value in control.child_values]
        notes: list[str] = []
        if parent_raw is not None and not parents:
            notes.append(f"invalid explicit parent value at {control.explicit_parent_field}")
        if child_raw is not None and not children:
            notes.append(f"invalid explicit child value at {control.explicit_child_field}")
        labels = [
            _label_for_pair(control.control_id, parent, child)
            for parent in parents
            for child in children
            if _label_for_pair(control.control_id, parent, child) in control.label_to_parent_child
        ]
        return CandidateRow(
            row=row,
            candidate_labels=labels,
            assignment_source="explicit_control_semantic",
            source_text_fields_used=[],
            candidate_parent_values=parents,
            candidate_child_values=children,
            candidate_notes=notes,
        )

    text_parts: list[str] = []
    used_paths: list[str] = []
    for field_name in control.candidate_text_fields:
        values, paths = _allowed_text_field_values(row.record, field_name)
        text_parts.extend(values)
        used_paths.extend(paths)
    haystack = " ".join(text_parts).lower()
    parents = _keyword_candidates(control.parent_keywords, haystack, control.parent_values)
    children = _keyword_candidates(control.child_keywords, haystack, control.child_values)
    labels = [
        _label_for_pair(control.control_id, parent, child)
        for parent in parents
        for child in children
        if _label_for_pair(control.control_id, parent, child) in control.label_to_parent_child
    ]
    return CandidateRow(
        row=row,
        candidate_labels=labels,
        assignment_source="keyword_manifest",
        source_text_fields_used=sorted(set(used_paths)),
        candidate_parent_values=parents,
        candidate_child_values=children,
        candidate_notes=[],
    )


def _source_label_for_row(record: dict[str, Any], source_axis: str) -> str | None:
    if source_axis == "stage9_40e":
        op = _get_path(record, "labels_operator")
        dom = _get_path(record, "labels_domain")
        if op is None:
            op = _get_path(record, "metadata.labels_operator")
        if dom is None:
            dom = _get_path(record, "metadata.labels_domain")
        if op is not None and dom is not None:
            return f"{_as_text(op)}|{_as_text(dom)}"
        _, value = _first_path(record, SOURCE_40E_LABEL_KEYS)
        return _as_text(value) if value is not None and _as_text(value) else None
    if source_axis == "stage7_f28":
        drive = _get_path(record, "drive")
        register = _get_path(record, "register")
        if drive is None:
            drive = _get_path(record, "metadata.drive")
        if register is None:
            register = _get_path(record, "metadata.register")
        if drive is not None and register is not None:
            return f"{_as_text(drive)}|{_as_text(register)}"
        _, value = _first_path(record, SOURCE_F28_LABEL_KEYS)
        return _as_text(value) if value is not None and _as_text(value) else None
    return None


def _canonical_source_labels(manifest: Any, source_axis: str) -> list[str]:
    if not isinstance(manifest, dict):
        return []
    spaces = manifest.get("cas_reference_label_spaces")
    if not isinstance(spaces, dict):
        return []
    space = spaces.get(source_axis)
    if not isinstance(space, dict) or not isinstance(space.get("labels"), list):
        return []
    return [_as_text(value) for value in space["labels"]]


def _target_counts_for_split(
    split_rows: list[Row],
    *,
    control: ControlSpec,
    manifest: Any,
) -> tuple[dict[str, int], dict[str, Any]]:
    source_labels = [_source_label_for_row(row.record, control.source_axis) for row in split_rows]
    present = [label for label in source_labels if label]
    quota_source = "uniform_split_count_division"
    if present and len(present) != len(split_rows):
        raise BlockingError(
            control.block_status,
            "partial source CAS label coverage prevents honest target quota recovery",
            control_id=control.control_id,
            details={
                "split": split_rows[0].split if split_rows else None,
                "rows": len(split_rows),
                "source_labels_present": len(present),
            },
        )

    if present:
        source_counts = Counter(present)
        if len(source_counts) != len(control.labels):
            raise BlockingError(
                control.block_status,
                "source CAS class count does not match matched-control class count for this split",
                control_id=control.control_id,
                details={
                    "split": split_rows[0].split if split_rows else None,
                    "source_class_count": len(source_counts),
                    "control_class_count": len(control.labels),
                    "source_counts": dict(sorted(source_counts.items())),
                },
            )
        canonical = _canonical_source_labels(manifest, control.source_axis)
        if canonical and set(canonical) == set(source_counts):
            source_order = canonical
            quota_source = "source_cas_counts_canonical_order"
        else:
            source_order = sorted(source_counts)
            quota_source = "source_cas_counts_sorted_order"
        quotas = {label: int(source_counts[source_order[index]]) for index, label in enumerate(control.labels)}
    else:
        if len(split_rows) % len(control.labels) != 0:
            raise BlockingError(
                control.block_status,
                "source labels are absent and split rows are not divisible into uniform matched-control quotas",
                control_id=control.control_id,
                details={
                    "split": split_rows[0].split if split_rows else None,
                    "rows": len(split_rows),
                    "control_class_count": len(control.labels),
                },
            )
        per_label = len(split_rows) // len(control.labels)
        quotas = {label: per_label for label in control.labels}

    if sum(quotas.values()) != len(split_rows):
        raise BlockingError(
            control.block_status,
            "target quotas do not sum to split row count",
            control_id=control.control_id,
            details={
                "split": split_rows[0].split if split_rows else None,
                "rows": len(split_rows),
                "quota_sum": sum(quotas.values()),
            },
        )
    return quotas, {"quota_source": quota_source, "target_counts": quotas}


def _candidate_coverage(candidate_rows: list[CandidateRow], labels: list[str]) -> dict[str, int]:
    coverage = Counter()
    for candidate_row in candidate_rows:
        for label in set(candidate_row.candidate_labels):
            coverage[label] += 1
    return {label: int(coverage[label]) for label in labels}


def _sort_candidate_labels(labels: list[str], *, row: Row, seed: int) -> list[str]:
    return sorted(labels, key=lambda label: (_stable_hash_int(seed, row.row_key, label), label))


def _solve_split_assignment(
    candidate_rows: list[CandidateRow],
    quotas: dict[str, int],
    *,
    control: ControlSpec,
) -> tuple[dict[int, str], dict[str, Any]]:
    n_rows = len(candidate_rows)
    labels = list(quotas)
    source = 0
    row_offset = 1
    label_offset = row_offset + n_rows
    sink = label_offset + len(labels)
    graph = _Dinic(sink + 1)
    label_node = {label: label_offset + index for index, label in enumerate(labels)}
    row_edges: dict[int, list[tuple[str, _Edge]]] = {}

    ordered_rows = sorted(
        enumerate(candidate_rows),
        key=lambda item: (_stable_hash_int(control.seed, item[1].row.row_key), item[1].row.row_key),
    )
    for sorted_index, (original_index, candidate_row) in enumerate(ordered_rows):
        row_node = row_offset + sorted_index
        graph.add_edge(source, row_node, 1)
        row_edges[original_index] = []
        for label in _sort_candidate_labels(candidate_row.candidate_labels, row=candidate_row.row, seed=control.seed):
            if label not in label_node:
                continue
            edge = graph.add_edge(row_node, label_node[label], 1)
            row_edges[original_index].append((label, edge))

    for label, quota in quotas.items():
        graph.add_edge(label_node[label], sink, quota)

    flow = graph.max_flow(source, sink)
    assignments: dict[int, str] = {}
    assigned_counts = Counter()
    for original_index, edges in row_edges.items():
        for label, edge in edges:
            if edge.cap == 0:
                assignments[original_index] = label
                assigned_counts[label] += 1
                break

    diagnostics = {
        "requested_rows": n_rows,
        "assigned_rows": int(flow),
        "target_counts": {label: int(quotas[label]) for label in labels},
        "assigned_counts": {label: int(assigned_counts[label]) for label in labels},
        "candidate_coverage": _candidate_coverage(candidate_rows, labels),
        "unsupported_rows": [
            {
                "row_index": candidate_row.row.row_index,
                "row_key": candidate_row.row.row_key,
                "sample_id": candidate_row.row.sample_id,
                "assignment_source": candidate_row.assignment_source,
                "source_text_fields_used": candidate_row.source_text_fields_used,
                "candidate_notes": candidate_row.candidate_notes,
            }
            for candidate_row in candidate_rows
            if not candidate_row.candidate_labels
        ][:20],
    }
    if flow != n_rows:
        unsatisfied = {
            label: int(quotas[label] - assigned_counts[label])
            for label in labels
            if quotas[label] - assigned_counts[label] > 0
        }
        diagnostics["unsatisfied_target_counts"] = unsatisfied
        raise BlockingError(
            control.block_status,
            "balanced assignment cannot satisfy quotas from supported non-CAS candidates",
            control_id=control.control_id,
            details=diagnostics,
        )
    return assignments, diagnostics


def _count_by_split(row_assignments: list[dict[str, Any]], labels: list[str]) -> dict[str, dict[str, int]]:
    result = {"train": {label: 0 for label in labels}, "test": {label: 0 for label in labels}}
    for assignment in row_assignments:
        result[assignment["split"]][assignment["assigned_control_label"]] += 1
    return result


def _vector_or_map(
    row_assignments: list[dict[str, Any]],
    *,
    key: str,
    label_mode: str,
) -> list[str] | dict[str, str]:
    ordered = sorted(row_assignments, key=lambda item: int(item["row_index"]))
    if label_mode == "dataset_order":
        return [_as_text(item[key]) for item in ordered]
    return {_as_text(item["sample_id"]): _as_text(item[key]) for item in ordered}


def _materialize_control(
    rows: list[Row],
    *,
    control: ControlSpec,
    manifest: Any,
    label_mode: str,
    manifest_sha256: str,
    source_scenario_sha256: str,
    source_dataset_sha256: str | None,
    split_manifest_sha256: str,
) -> dict[str, Any]:
    all_row_assignments: list[dict[str, Any]] = []
    split_diagnostics: dict[str, Any] = {}

    for split in ("train", "test"):
        split_rows = [row for row in rows if row.split == split]
        quotas, quota_details = _target_counts_for_split(split_rows, control=control, manifest=manifest)
        candidate_rows = [_candidate_labels_for_row(row, control) for row in split_rows]
        assignments_by_position, diagnostics = _solve_split_assignment(candidate_rows, quotas, control=control)
        diagnostics.update(quota_details)
        split_diagnostics[split] = diagnostics
        for position, candidate_row in enumerate(candidate_rows):
            label = assignments_by_position[position]
            parent, child = control.label_to_parent_child[label]
            all_row_assignments.append(
                {
                    "row_key": candidate_row.row.row_key,
                    "row_key_source": candidate_row.row.row_key_source,
                    "sample_id": candidate_row.row.sample_id,
                    "row_index": candidate_row.row.row_index,
                    "split": split,
                    "assigned_control_label": label,
                    "parent_label": parent,
                    "child_label": child,
                    "candidate_labels": candidate_row.candidate_labels,
                    "candidate_parent_values": candidate_row.candidate_parent_values,
                    "candidate_child_values": candidate_row.candidate_child_values,
                    "assignment_source": candidate_row.assignment_source,
                    "source_text_fields_used": candidate_row.source_text_fields_used,
                    "candidate_notes": candidate_row.candidate_notes,
                }
            )

    all_row_assignments.sort(key=lambda item: int(item["row_index"]))
    taxonomy = {
        "id": control.control_id,
        "taxonomy_id": control.control_id,
        "name": control.control_id,
        "role": "coherent_matched",
        "coherent": True,
        "axis": control.runner_axis,
        "source_axis": control.source_axis,
        "labels": _vector_or_map(all_row_assignments, key="assigned_control_label", label_mode=label_mode),
        "parent_labels": _vector_or_map(all_row_assignments, key="parent_label", label_mode=label_mode),
        "child_labels": _vector_or_map(all_row_assignments, key="child_label", label_mode=label_mode),
        "label_space": control.labels,
        "parent_axis": control.parent_values,
        "child_axis": control.child_values,
        "parent_axis_name": control.parent_axis_name,
        "child_axis_name": control.child_axis_name,
        "assignment_contract": {
            "manifest_sha256": manifest_sha256,
            "source_scenario_sha256": source_scenario_sha256,
            "source_dataset_sha256": source_dataset_sha256,
            "split_manifest_sha256": split_manifest_sha256,
            "assignment_algorithm_version": ALGORITHM_VERSION,
            "seed": control.seed,
            "candidate_source_policy": "explicit control_semantic fields or manifest-listed non-CAS text fields only",
            "cas_fields_used_for": "splitwise target quota counts only when source labels are present",
            "blocked_status": None,
        },
        "class_counts_by_split": _count_by_split(all_row_assignments, control.labels),
        "split_diagnostics": split_diagnostics,
        "row_assignments": all_row_assignments,
    }
    taxonomy["assignment_sha256"] = _sha256_json(
        {
            "id": taxonomy["id"],
            "axis": taxonomy["axis"],
            "labels": taxonomy["labels"],
            "parent_labels": taxonomy["parent_labels"],
            "child_labels": taxonomy["child_labels"],
            "row_assignments": taxonomy["row_assignments"],
            "class_counts_by_split": taxonomy["class_counts_by_split"],
            "assignment_contract": taxonomy["assignment_contract"],
        }
    )
    return taxonomy


def materialize_assignments(
    *,
    scenarios_path: Path,
    manifest_path: Path,
    output_path: Path,
    control_ids: list[str],
    axis: str | None,
    label_mode: str,
    split_manifest_path: Path | None = None,
    source_dataset_sha256: str | None = None,
) -> int:
    scenarios = _load_jsonish(scenarios_path)
    manifest = _load_jsonish(manifest_path)
    split_payload = _load_jsonish(split_manifest_path) if split_manifest_path else None
    source_scenario_sha256 = _sha256_file(scenarios_path)
    manifest_sha256 = _sha256_file(manifest_path)
    split_manifest_file_sha = _sha256_file(split_manifest_path) if split_manifest_path else None
    source_dataset_sha256 = _discover_source_dataset_sha(scenarios, source_dataset_sha256)

    try:
        records = _extract_records(scenarios)
        if not records:
            raise BlockingError(
                "blocked_missing_source_scenario_or_activation_artifact",
                "scenario JSON does not contain a supported row list",
            )
        bases = _build_row_bases(
            records,
            scenario_payload=scenarios,
            source_scenario_sha256=source_scenario_sha256,
            source_dataset_sha256=source_dataset_sha256,
        )
        rows, split_manifest = _assign_splits(bases, scenario_payload=scenarios, split_payload=split_payload)
        if label_mode == "sample_id_map":
            sample_id_counts = Counter(row.sample_id for row in rows)
            duplicate_sample_ids = sorted(sample_id for sample_id, count in sample_id_counts.items() if count > 1)
            if duplicate_sample_ids:
                raise BlockingError(
                    "blocked_duplicate_sample_ids_for_keyed_output",
                    "sample_id_map output cannot represent duplicate sample_id rows without collapse",
                    details={
                        "duplicate_sample_ids": duplicate_sample_ids[:20],
                        "duplicate_sample_id_count": len(duplicate_sample_ids),
                    },
                )
        if split_manifest_file_sha:
            split_manifest["source_file_sha256"] = split_manifest_file_sha
            split_manifest["content_sha256"] = split_manifest_file_sha
        controls = _select_controls(manifest, requested=control_ids, axis=axis)
        taxonomies = [
            _materialize_control(
                rows,
                control=control,
                manifest=manifest,
                label_mode=label_mode,
                manifest_sha256=manifest_sha256,
                source_scenario_sha256=source_scenario_sha256,
                source_dataset_sha256=source_dataset_sha256,
                split_manifest_sha256=split_manifest["content_sha256"],
            )
            for control in controls
        ]
        status = "completed"
        blocking_reasons: list[dict[str, Any]] = []
    except BlockingError as exc:
        status = "blocked"
        taxonomies = []
        split_manifest = {}
        blocking_reasons = [
            {
                "blocked_status": exc.status,
                "control_id": exc.control_id,
                "reason": exc.reason,
                "details": exc.details,
            }
        ]

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "source_scenario": str(scenarios_path),
        "manifest": str(manifest_path),
        "manifest_sha256": manifest_sha256,
        "source_scenario_sha256": source_scenario_sha256,
        "source_dataset_sha256": source_dataset_sha256,
        "split_manifest_sha256": split_manifest.get("content_sha256"),
        "assignment_algorithm_version": ALGORITHM_VERSION,
        "label_mode": label_mode,
        "controls_requested": control_ids or ["all_coherent_non_cas"],
        "axis": axis,
        "split_manifest": split_manifest,
        "blocked": status == "blocked",
        "blocking_reasons": blocking_reasons,
        "taxonomies": taxonomies,
    }
    payload["label_assignment_sha256"] = _sha256_json(
        {
            "schema_version": payload["schema_version"],
            "status": payload["status"],
            "manifest_sha256": payload["manifest_sha256"],
            "source_scenario_sha256": payload["source_scenario_sha256"],
            "source_dataset_sha256": payload["source_dataset_sha256"],
            "split_manifest_sha256": payload["split_manifest_sha256"],
            "assignment_algorithm_version": payload["assignment_algorithm_version"],
            "label_mode": payload["label_mode"],
            "taxonomies": payload["taxonomies"],
            "blocking_reasons": payload["blocking_reasons"],
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")
    return 0 if status == "completed" else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenarios", required=True, type=Path, help="Source scenario JSON/JSONL in frozen row order")
    parser.add_argument("--manifest", required=True, type=Path, help="Matched-taxonomy design manifest JSON")
    parser.add_argument("--output", required=True, type=Path, help="Runner-compatible row-level label JSON")
    parser.add_argument(
        "--control-id",
        action="append",
        default=[],
        help="Control id/key/alias to materialize. Repeatable. Defaults to all coherent non-CAS controls.",
    )
    parser.add_argument("--axis", choices=("40e", "f28"), help="Restrict materialization to controls for one runner axis")
    parser.add_argument(
        "--label-mode",
        choices=("dataset_order", "sample_id_map"),
        default="dataset_order",
        help="Emit label vectors in dataset order or maps keyed by sample_id.",
    )
    parser.add_argument("--split-manifest", type=Path, help="Optional external frozen split manifest JSON")
    parser.add_argument(
        "--source-dataset-sha256",
        help="Optional activation dataset hash when the scenario artifact does not carry one.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return materialize_assignments(
        scenarios_path=args.scenarios,
        manifest_path=args.manifest,
        output_path=args.output,
        control_ids=args.control_id,
        axis=args.axis,
        label_mode=args.label_mode,
        split_manifest_path=args.split_manifest,
        source_dataset_sha256=args.source_dataset_sha256,
    )


if __name__ == "__main__":
    sys.exit(main())
