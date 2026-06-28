"""Stage 27F cover evidence and cover-level confidence derivation."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Mapping

from pydantic import BaseModel, Field

from ..schemas.events import CoverConfidence, CoverRowEvidence

COVER_CONFIDENCE_FORMULA = "targeted_drop / clean_margin"
MAX_REPORTABLE_COVER_CONFIDENCE = 0.95

FOUNDATION_CLASS_KEYS: tuple[str, ...] = tuple(
    f"F{drive}{register}"
    for drive in range(1, 8)
    for register in ("A", "T", "f", "E")
)
FOUNDATION_CLASS_KEY_SET = frozenset(FOUNDATION_CLASS_KEYS)

DEFAULT_STAGE27F_SNAPSHOT = (
    Path(__file__).resolve().parents[3]
    / "research"
    / "cas_probe"
    / ".tmp"
    / "stage27f_smoke.json"
)

# Legacy coordinate-only fallback. It keeps the overlay usable when the worker
# is packaged without research artifacts, but confidence stays unavailable.
LEGACY_F1_COVER_DEMO: dict[str, list[str]] = {
    "F1A": ["L3N142", "L3N518", "L5N91", "L7N2204"],
    "F1T": ["L4N336", "L6N1011", "L9N2782"],
    "F1f": ["L5N1492", "L8N87", "L11N305"],
    "F1E": ["L2N640", "L6N1872", "L10N2415"],
}


class CoverLibraryPayload(BaseModel):
    per_class_neuron_covers: dict[str, list[str]] = Field(default_factory=dict)
    cover_evidence: dict[str, CoverRowEvidence] = Field(default_factory=dict)
    source_path: str | None = None


def _as_finite_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _as_int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    out: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            continue
        out.append(item)
    return out


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _confidence_label(score: float) -> str:
    if score > 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def _unavailable(reason: str, provenance: Mapping[str, Any]) -> CoverConfidence:
    return CoverConfidence(
        status="unavailable",
        reason=reason,
        provenance=dict(provenance),
    )


def unsupported_cover_confidence(target: str) -> CoverConfidence:
    drive = target[:2] if len(target) >= 2 else target
    return CoverConfidence(
        status="unsupported",
        reason=(
            f"drive {drive} is unsupported; Stage 27F cover evidence supports "
            "F1-F7 register classes only"
        ),
        provenance={
            "source_stage": "Stage 27F",
            "confidence_scope": "cover-level",
            "supported_classes": list(FOUNDATION_CLASS_KEYS),
        },
    )


def derive_cover_confidence(
    row: Mapping[str, Any],
    provenance: Mapping[str, Any] | None = None,
) -> CoverConfidence:
    """Compute cover-level confidence only from real Stage 27F row fields."""

    prov = {
        "source_stage": "Stage 27F",
        "confidence_scope": "cover-level",
        "formula": COVER_CONFIDENCE_FORMULA,
        **dict(provenance or {}),
    }

    targeted_raw = row.get("targeted_drop")
    if targeted_raw is None:
        return _unavailable("targeted_drop missing from Stage 27F row evidence", prov)
    targeted_drop = _as_finite_float(targeted_raw)
    if targeted_drop is None or targeted_drop < 0:
        return _unavailable("targeted_drop must be a non-negative finite number", prov)

    clean_raw = row.get("clean_margin")
    if clean_raw is None:
        return _unavailable("clean_margin missing from Stage 27F row evidence", prov)
    clean_margin = _as_finite_float(clean_raw)
    if clean_margin is None or clean_margin <= 0:
        return _unavailable("clean_margin must be a positive finite number", prov)

    score = targeted_drop / clean_margin
    prov.update(
        {
            "targeted_drop": targeted_drop,
            "clean_margin": clean_margin,
            "raw_score": score,
        }
    )
    if score > MAX_REPORTABLE_COVER_CONFIDENCE:
        return _unavailable(
            "targeted_drop / clean_margin exceeds calibrated reportable range (> 0.95)",
            prov,
        )

    return CoverConfidence(
        status="real",
        score=score,
        label=_confidence_label(score),
        provenance=prov,
    )


def _snapshot_provenance(
    snapshot: Mapping[str, Any],
    source_path: Path | None,
) -> dict[str, Any]:
    artifact_contract = snapshot.get("artifact_contract")
    if not isinstance(artifact_contract, Mapping):
        artifact_contract = {}
    stage27c = snapshot.get("stage27c_contract")
    if not isinstance(stage27c, Mapping):
        stage27c = {}
    stage27e = snapshot.get("stage27e_contract")
    if not isinstance(stage27e, Mapping):
        stage27e = {}

    provenance: dict[str, Any] = {
        "source_stage": "Stage 27F",
        "confidence_scope": "cover-level",
        "formula": COVER_CONFIDENCE_FORMULA,
    }
    if source_path is not None:
        provenance["source_path"] = str(source_path)
    for out_key, raw_value in (
        ("source_schema_version", snapshot.get("schema_version")),
        ("snapshot_status", snapshot.get("status")),
        ("artifact_status", artifact_contract.get("status")),
        ("artifact_formal_gate_valid", artifact_contract.get("formal_gate_valid")),
        ("stage27c_source_status", stage27c.get("source_status")),
        ("stage27e_source_status", stage27e.get("source_status")),
    ):
        if raw_value is not None:
            provenance[out_key] = raw_value
    return provenance


def _row_reports(snapshot: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_rows = snapshot.get("row_reports")
    if raw_rows is None:
        evaluation = snapshot.get("evaluation")
        if isinstance(evaluation, Mapping):
            raw_rows = evaluation.get("row_reports")
    if not isinstance(raw_rows, list):
        return []
    return [row for row in raw_rows if isinstance(row, Mapping)]


def _row_by_target(snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    for row in _row_reports(snapshot):
        target = row.get("target")
        if not isinstance(target, str):
            continue
        rows.setdefault(target, row)
    return rows


def _covers_by_target(snapshot: Mapping[str, Any]) -> dict[str, list[str]]:
    covers = snapshot.get("per_class_neuron_covers")
    if not isinstance(covers, Mapping):
        return {}
    out: dict[str, list[str]] = {}
    for target, labels in covers.items():
        if isinstance(target, str):
            out[target] = _as_string_list(labels)
    return out


def _candidate_layers_by_target(snapshot: Mapping[str, Any]) -> dict[str, list[int]]:
    layers = snapshot.get("candidate_layers_per_class")
    if not isinstance(layers, Mapping):
        return {}
    out: dict[str, list[int]] = {}
    for target, values in layers.items():
        if isinstance(target, str):
            out[target] = _as_int_list(values)
    return out


def cover_evidence_from_row(
    row: Mapping[str, Any],
    provenance: Mapping[str, Any] | None = None,
) -> CoverRowEvidence:
    target = row.get("target")
    target_str = target if isinstance(target, str) else "unknown"
    row_provenance = dict(provenance or {})
    for key in ("sample_id", "pair_kind", "partner"):
        value = row.get(key)
        if isinstance(value, str):
            row_provenance[key] = value

    return CoverRowEvidence(
        target=target_str,
        candidate_layers=_as_int_list(row.get("candidate_layers")),
        neuron_cover=_as_string_list(row.get("neuron_cover")),
        clean_margin=_as_finite_float(row.get("clean_margin")),
        targeted_drop=_as_finite_float(row.get("targeted_drop")),
        pair_kind=row.get("pair_kind") if isinstance(row.get("pair_kind"), str) else None,
        partner=row.get("partner") if isinstance(row.get("partner"), str) else None,
        sample_id=row.get("sample_id") if isinstance(row.get("sample_id"), str) else None,
        confidence=derive_cover_confidence(row, row_provenance),
    )


def unsupported_cover_evidence(target: str) -> CoverRowEvidence:
    return CoverRowEvidence(
        target=target,
        confidence=unsupported_cover_confidence(target),
    )


def build_cover_payload_from_snapshot(
    snapshot: Mapping[str, Any],
    *,
    source_path: Path | None = None,
    requested_classes: Iterable[str] | None = None,
) -> CoverLibraryPayload:
    covers = _covers_by_target(snapshot)
    rows = _row_by_target(snapshot)
    candidate_layers = _candidate_layers_by_target(snapshot)
    base_provenance = _snapshot_provenance(snapshot, source_path)

    classes = list(requested_classes) if requested_classes is not None else [
        key for key in FOUNDATION_CLASS_KEYS if key in covers or key in rows
    ]
    evidence: dict[str, CoverRowEvidence] = {}
    for target in classes:
        if target not in FOUNDATION_CLASS_KEY_SET:
            evidence[target] = unsupported_cover_evidence(target)
            continue

        row = rows.get(target)
        if row is None:
            provenance = {
                **base_provenance,
                "target": target,
                "reason_field": "row_reports",
            }
            evidence[target] = CoverRowEvidence(
                target=target,
                candidate_layers=candidate_layers.get(target, []),
                neuron_cover=covers.get(target, []),
                confidence=_unavailable(
                    f"Stage 27F row_report missing for {target}",
                    provenance,
                ),
            )
            continue

        row_provenance = {**base_provenance, "target": target}
        row_evidence = cover_evidence_from_row(row, row_provenance)
        if not row_evidence.neuron_cover:
            row_evidence.neuron_cover = covers.get(target, [])
        if not row_evidence.candidate_layers:
            row_evidence.candidate_layers = candidate_layers.get(target, [])
        evidence[target] = row_evidence

    return CoverLibraryPayload(
        per_class_neuron_covers=covers,
        cover_evidence=evidence,
        source_path=str(source_path) if source_path is not None else None,
    )


def load_cover_payload(path: Path | str) -> CoverLibraryPayload:
    source_path = Path(path)
    with source_path.open("r", encoding="utf-8") as f:
        snapshot = json.load(f)
    if not isinstance(snapshot, Mapping):
        raise ValueError(f"Stage 27F cover snapshot must be an object: {source_path}")
    return build_cover_payload_from_snapshot(snapshot, source_path=source_path)


def _missing_snapshot_payload(path: Path) -> CoverLibraryPayload:
    reason = (
        f"Stage 27F snapshot not found at {path}; cover-level confidence "
        "requires targeted_drop and clean_margin row evidence"
    )
    evidence: dict[str, CoverRowEvidence] = {}
    for target, labels in LEGACY_F1_COVER_DEMO.items():
        evidence[target] = CoverRowEvidence(
            target=target,
            neuron_cover=labels,
            confidence=_unavailable(
                reason,
                {
                    "source_stage": "Stage 27F",
                    "confidence_scope": "cover-level",
                    "formula": COVER_CONFIDENCE_FORMULA,
                    "source_path": str(path),
                },
            ),
        )
    return CoverLibraryPayload(
        per_class_neuron_covers=LEGACY_F1_COVER_DEMO,
        cover_evidence=evidence,
        source_path=str(path),
    )


@lru_cache(maxsize=1)
def load_default_cover_payload() -> CoverLibraryPayload:
    if not DEFAULT_STAGE27F_SNAPSHOT.exists():
        return _missing_snapshot_payload(DEFAULT_STAGE27F_SNAPSHOT)
    return load_cover_payload(DEFAULT_STAGE27F_SNAPSHOT)
