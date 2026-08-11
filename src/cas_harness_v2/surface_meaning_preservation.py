"""Per-cell Surface Gate and Meaning Preservation evidence contracts.

The artifacts in this module are structure-only replay records.  They do not
execute a model, score text, call an evaluator, authorize an intervention, or
emit an aggregate PASS.  Each result stays visible at cell and axis level.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from ._strict_json import (
    canonical_json_bytes,
    freeze_json,
    load_json_object,
    mapping_proxy_backing_dict,
    sha256_bytes,
    thaw_json,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_enum,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    parse_artifact_ref,
)


SEMANTIC_GATE_PROFILE_SCHEMA = "cas_harness_v2.semantic_gate_profile.v1"
SURFACE_GATE_RECEIPT_SCHEMA = "cas_harness_v2.surface_gate_receipt.v1"
MEANING_PRESERVATION_RECEIPT_SCHEMA = (
    "cas_harness_v2.meaning_preservation_receipt.v1"
)
SEMANTIC_GATE_PROFILE_MEDIA_TYPE = (
    "application/vnd.cas-harness.semantic-gate-profile-v1+json"
)
SURFACE_GATE_RECEIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.surface-gate-receipt-v1+json"
)
MEANING_PRESERVATION_RECEIPT_MEDIA_TYPE = (
    "application/vnd.cas-harness.meaning-preservation-receipt-v1+json"
)

TEXT_OVERLAP = "TEXT_OVERLAP"
CHARACTER_OVERLAP = "CHARACTER_OVERLAP"
TOKEN_OVERLAP = "TOKEN_OVERLAP"
EMBEDDING_OVERLAP = "EMBEDDING_OVERLAP"
PROVENANCE = "PROVENANCE"
LENGTH = "LENGTH"
TAXONOMY = "TAXONOMY"
CARRIER = "CARRIER"
PAYLOAD_FAMILY = "PAYLOAD_FAMILY"
SURFACE_AXES = (
    TEXT_OVERLAP,
    CHARACTER_OVERLAP,
    TOKEN_OVERLAP,
    EMBEDDING_OVERLAP,
    PROVENANCE,
    LENGTH,
    TAXONOMY,
    CARRIER,
    PAYLOAD_FAMILY,
)

USER = "USER"
SYSTEM = "SYSTEM"
TOOL = "TOOL"
RETRIEVED = "RETRIEVED"
EXTERNAL = "EXTERNAL"
SOURCE_KINDS = (USER, SYSTEM, TOOL, RETRIEVED, EXTERNAL)

MEANING_BEARING = "MEANING_BEARING"
VOCABULARY_DEPENDENT = "VOCABULARY_DEPENDENT"
CELL_DISPOSITIONS = (MEANING_BEARING, VOCABULARY_DEPENDENT)

STRUCTURE_ONLY = "STRUCTURE_ONLY"
NON_AUTHORITY = "NON_AUTHORITY"
NOT_LICENSED = "NOT_LICENSED"
REPLAY_ONLY = "REPLAY_ONLY"
PER_CELL_ONLY = "PER_CELL_ONLY / NO AGGREGATE PASS"

_STATUS = MappingProxyType({
    "scope": STRUCTURE_ONLY,
    "authority": NON_AUTHORITY,
    "license": NOT_LICENSED,
    "execution": REPLAY_ONLY,
    "claim_scope": PER_CELL_ONLY,
})
_BOUNDARY = MappingProxyType({
    "model_calls": 0,
    "provider_calls": 0,
    "network_calls": 0,
    "filesystem_writes": 0,
    "interventions": 0,
    "aggregate_verdict": None,
    "execution_authority": "NOT_GRANTED",
})
_OVERLAP_AXES = (
    TEXT_OVERLAP,
    CHARACTER_OVERLAP,
    TOKEN_OVERLAP,
    EMBEDDING_OVERLAP,
)


class SurfaceMeaningValidationError(SchemaValidationError):
    """A semantic gate carrier violated its closed schema."""


@dataclass(frozen=True, slots=True)
class SurfaceGateCellInput:
    execution_ordinal: int
    cell_id: str
    prompt_ref: ArtifactRef
    prompt_source_map_ref: ArtifactRef
    source_kind: str
    attack_category: str
    disposition: str
    text_overlap_ppm: int
    character_overlap_ppm: int
    token_overlap_ppm: int
    embedding_overlap_ppm: int
    length_ratio_ppm: int
    provenance_preserved: bool
    taxonomy_preserved: bool
    carrier_preserved: bool
    payload_family_preserved: bool

    def __post_init__(self) -> None:
        expect_int(self.execution_ordinal, "execution_ordinal", minimum=1)
        expect_machine_id(self.cell_id, "cell_id")
        _require_ref(self.prompt_ref, "prompt_ref")
        _require_ref(self.prompt_source_map_ref, "prompt_source_map_ref")
        if self.prompt_ref.artifact_id == self.prompt_source_map_ref.artifact_id:
            raise SurfaceMeaningValidationError("cell roles reuse an artifact identity")
        if _content_key(self.prompt_ref) == _content_key(self.prompt_source_map_ref):
            raise SurfaceMeaningValidationError("cell roles reuse artifact content")
        expect_enum(self.source_kind, set(SOURCE_KINDS), "source_kind")
        expect_machine_id(self.attack_category, "attack_category")
        expect_enum(self.disposition, set(CELL_DISPOSITIONS), "disposition")
        for name in (
            "text_overlap_ppm",
            "character_overlap_ppm",
            "token_overlap_ppm",
            "embedding_overlap_ppm",
        ):
            expect_int(getattr(self, name), name, minimum=0, maximum=1_000_000)
        expect_int(
            self.length_ratio_ppm,
            "length_ratio_ppm",
            minimum=1,
            maximum=10_000_000,
        )
        for name in (
            "provenance_preserved",
            "taxonomy_preserved",
            "carrier_preserved",
            "payload_family_preserved",
        ):
            if type(getattr(self, name)) is not bool:
                raise SurfaceMeaningValidationError(f"{name} must be an exact bool")


@dataclass(frozen=True, slots=True)
class MeaningPreservationCellInput:
    execution_ordinal: int
    cell_id: str
    surface_cell_id: str
    paraphrase_ref: ArtifactRef
    paraphrase_provenance_ref: ArtifactRef
    task_preserved: bool
    label_blinded: bool
    independent_evaluator_score_ppm: int
    vocabulary_dependence_ppm: int
    rater_scores_ppm: tuple[int, ...]

    def __post_init__(self) -> None:
        expect_int(self.execution_ordinal, "execution_ordinal", minimum=1)
        expect_machine_id(self.cell_id, "cell_id")
        expect_machine_id(self.surface_cell_id, "surface_cell_id")
        _require_ref(self.paraphrase_ref, "paraphrase_ref")
        _require_ref(self.paraphrase_provenance_ref, "paraphrase_provenance_ref")
        if self.paraphrase_ref.artifact_id == self.paraphrase_provenance_ref.artifact_id:
            raise SurfaceMeaningValidationError("meaning cell roles reuse an identity")
        if _content_key(self.paraphrase_ref) == _content_key(
            self.paraphrase_provenance_ref
        ):
            raise SurfaceMeaningValidationError("meaning cell roles reuse content")
        if type(self.task_preserved) is not bool or type(self.label_blinded) is not bool:
            raise SurfaceMeaningValidationError(
                "task_preserved and label_blinded must be exact bools"
            )
        expect_int(
            self.independent_evaluator_score_ppm,
            "independent_evaluator_score_ppm",
            minimum=0,
            maximum=1_000_000,
        )
        expect_int(
            self.vocabulary_dependence_ppm,
            "vocabulary_dependence_ppm",
            minimum=0,
            maximum=1_000_000,
        )
        if type(self.rater_scores_ppm) is not tuple or not self.rater_scores_ppm:
            raise SurfaceMeaningValidationError(
                "rater_scores_ppm must be a nonempty exact tuple"
            )
        for index, score in enumerate(self.rater_scores_ppm):
            expect_int(
                score,
                f"rater_scores_ppm[{index}]",
                minimum=0,
                maximum=1_000_000,
            )


@dataclass(frozen=True, slots=True)
class SemanticGateProfileArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    profile_id: str
    definition_ref: ArtifactRef
    crosswalk_ref: ArtifactRef
    rubric_ref: ArtifactRef
    power_plan_ref: ArtifactRef
    blind_assignment_ref: ArtifactRef
    independent_evaluator_ref: ArtifactRef
    rater_refs: tuple[ArtifactRef, ...]
    max_surface_overlap_ppm: Mapping[str, int]
    min_length_ratio_ppm: int
    max_length_ratio_ppm: int
    min_meaning_score_ppm: int
    max_vocabulary_dependence_ppm: int
    max_rater_spread_ppm: int
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.profile_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=SEMANTIC_GATE_PROFILE_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class SurfaceGateReceiptArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    receipt_id: str
    profile: SemanticGateProfileArtifact
    protocol_ref: ArtifactRef
    roster_ref: ArtifactRef
    cells: tuple[SurfaceGateCellInput, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.receipt_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=SURFACE_GATE_RECEIPT_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class MeaningPreservationReceiptArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    receipt_id: str
    profile: SemanticGateProfileArtifact
    surface_gate: SurfaceGateReceiptArtifact
    cells: tuple[MeaningPreservationCellInput, ...]
    payload: Mapping[str, Any]
    artifact_refs: tuple[ArtifactRef, ...]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.receipt_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=MEANING_PRESERVATION_RECEIPT_MEDIA_TYPE,
        )


def _require_ref(value: Any, path: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise SurfaceMeaningValidationError(f"{path} must be an exact ArtifactRef")
    try:
        checked = ArtifactRef(
            artifact_id=value.artifact_id,
            sha256=value.sha256,
            byte_length=value.byte_length,
            media_type=value.media_type,
        )
    except (TypeError, ValueError, SchemaValidationError) as exc:
        raise SurfaceMeaningValidationError(f"{path} is forged: {exc}") from exc
    if checked != value:
        raise SurfaceMeaningValidationError(f"{path} changed during validation")
    return value


def _content_key(value: ArtifactRef) -> tuple[str, int]:
    return value.sha256, value.byte_length


def _ref_value(value: ArtifactRef) -> dict[str, Any]:
    value = _require_ref(value, "artifact_ref")
    return {
        "artifact_id": value.artifact_id,
        "sha256": value.sha256,
        "byte_length": value.byte_length,
        "media_type": value.media_type,
    }


def _canonical(raw: Any, path: str) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, value = load_json_object(raw)
    except (TypeError, ValueError) as exc:
        raise SurfaceMeaningValidationError(f"{path}: {exc}") from exc
    if snapshot != canonical_json_bytes(value):
        raise SurfaceMeaningValidationError(f"{path} must use canonical JSON")
    return snapshot, value


def _require_frozen(value: Any, path: str) -> None:
    if type(value) is MappingProxyType:
        backing = mapping_proxy_backing_dict(value)
        if backing is None:
            raise SurfaceMeaningValidationError(
                f"{path} mapping proxy must wrap an exact dict"
            )
        for key, child in backing.items():
            if type(key) is not str:
                raise SurfaceMeaningValidationError(f"{path} has a non-string key")
            _require_frozen(child, f"{path}.{key}")
        return
    if type(value) is tuple:
        for index, child in enumerate(value):
            _require_frozen(child, f"{path}[{index}]")
        return
    if type(value) not in (str, int, bool) and value is not None:
        raise SurfaceMeaningValidationError(f"{path} is not recursively frozen")


def _unique_refs(
    references: tuple[ArtifactRef, ...], *, owner_id: str, path: str
) -> tuple[ArtifactRef, ...]:
    by_id: dict[str, ArtifactRef] = {}
    by_content: dict[tuple[str, int], ArtifactRef] = {}
    ordered: list[ArtifactRef] = []
    for index, reference in enumerate(references):
        reference = _require_ref(reference, f"{path}[{index}]")
        if reference.artifact_id == owner_id:
            raise SurfaceMeaningValidationError(f"{path} collides with owner identity")
        prior = by_id.get(reference.artifact_id)
        if prior is not None:
            detail = (
                "maps one identity to different bytes"
                if prior != reference
                else "reuses one artifact identity across roles"
            )
            raise SurfaceMeaningValidationError(f"{path} {detail}")
        key = _content_key(reference)
        prior_content = by_content.get(key)
        if prior_content is not None and prior_content.artifact_id != reference.artifact_id:
            raise SurfaceMeaningValidationError(
                f"{path} reuses content under another identity"
            )
        by_id[reference.artifact_id] = reference
        by_content[key] = reference
        ordered.append(reference)
    return tuple(ordered)


def _require_status(value: dict[str, Any]) -> None:
    status = expect_object(value["status"], "$.status")
    boundary = expect_object(value["boundary"], "$.boundary")
    expect_keys(status, required=_STATUS, path="$.status")
    expect_keys(boundary, required=_BOUNDARY, path="$.boundary")
    for key, expected in _STATUS.items():
        if type(status[key]) is not type(expected) or status[key] != expected:
            raise SurfaceMeaningValidationError("semantic gate status changed")
    for key, expected in _BOUNDARY.items():
        if type(boundary[key]) is not type(expected) or boundary[key] != expected:
            raise SurfaceMeaningValidationError("semantic gate boundary changed")


def _profile_value(
    *,
    profile_id: str,
    definition_ref: ArtifactRef,
    crosswalk_ref: ArtifactRef,
    rubric_ref: ArtifactRef,
    power_plan_ref: ArtifactRef,
    blind_assignment_ref: ArtifactRef,
    independent_evaluator_ref: ArtifactRef,
    rater_refs: tuple[ArtifactRef, ...],
    max_surface_overlap_ppm: Mapping[str, int],
    min_length_ratio_ppm: int,
    max_length_ratio_ppm: int,
    min_meaning_score_ppm: int,
    max_vocabulary_dependence_ppm: int,
    max_rater_spread_ppm: int,
) -> dict[str, Any]:
    return {
        "schema": SEMANTIC_GATE_PROFILE_SCHEMA,
        "profile_id": profile_id,
        "definitions": {
            "definition_ref": _ref_value(definition_ref),
            "crosswalk_ref": _ref_value(crosswalk_ref),
            "rubric_ref": _ref_value(rubric_ref),
            "power_plan_ref": _ref_value(power_plan_ref),
            "blind_assignment_ref": _ref_value(blind_assignment_ref),
            "independent_evaluator_ref": _ref_value(independent_evaluator_ref),
            "rater_refs": [_ref_value(ref) for ref in rater_refs],
        },
        "thresholds": {
            "max_surface_overlap_ppm": dict(max_surface_overlap_ppm),
            "min_length_ratio_ppm": min_length_ratio_ppm,
            "max_length_ratio_ppm": max_length_ratio_ppm,
            "min_meaning_score_ppm": min_meaning_score_ppm,
            "max_vocabulary_dependence_ppm": max_vocabulary_dependence_ppm,
            "max_rater_spread_ppm": max_rater_spread_ppm,
        },
        "status": dict(_STATUS),
        "boundary": dict(_BOUNDARY),
    }


def build_semantic_gate_profile(
    *,
    profile_id: str,
    definition_ref: ArtifactRef,
    crosswalk_ref: ArtifactRef,
    rubric_ref: ArtifactRef,
    power_plan_ref: ArtifactRef,
    blind_assignment_ref: ArtifactRef,
    independent_evaluator_ref: ArtifactRef,
    rater_refs: tuple[ArtifactRef, ...],
    max_surface_overlap_ppm: Mapping[str, int],
    min_length_ratio_ppm: int,
    max_length_ratio_ppm: int,
    min_meaning_score_ppm: int,
    max_vocabulary_dependence_ppm: int,
    max_rater_spread_ppm: int,
) -> SemanticGateProfileArtifact:
    profile_id = expect_machine_id(profile_id, "profile_id")
    value = _profile_value(
        profile_id=profile_id,
        definition_ref=definition_ref,
        crosswalk_ref=crosswalk_ref,
        rubric_ref=rubric_ref,
        power_plan_ref=power_plan_ref,
        blind_assignment_ref=blind_assignment_ref,
        independent_evaluator_ref=independent_evaluator_ref,
        rater_refs=rater_refs,
        max_surface_overlap_ppm=max_surface_overlap_ppm,
        min_length_ratio_ppm=min_length_ratio_ppm,
        max_length_ratio_ppm=max_length_ratio_ppm,
        min_meaning_score_ppm=min_meaning_score_ppm,
        max_vocabulary_dependence_ppm=max_vocabulary_dependence_ppm,
        max_rater_spread_ppm=max_rater_spread_ppm,
    )
    raw = canonical_json_bytes(value)
    return load_semantic_gate_profile(
        raw,
        profile_ref=ArtifactRef(
            artifact_id=profile_id,
            sha256=sha256_bytes(raw),
            byte_length=len(raw),
            media_type=SEMANTIC_GATE_PROFILE_MEDIA_TYPE,
        ),
        definition_ref=definition_ref,
        crosswalk_ref=crosswalk_ref,
        rubric_ref=rubric_ref,
        power_plan_ref=power_plan_ref,
        blind_assignment_ref=blind_assignment_ref,
        independent_evaluator_ref=independent_evaluator_ref,
        rater_refs=rater_refs,
    )


def load_semantic_gate_profile(
    raw: Any,
    *,
    profile_ref: ArtifactRef,
    definition_ref: ArtifactRef,
    crosswalk_ref: ArtifactRef,
    rubric_ref: ArtifactRef,
    power_plan_ref: ArtifactRef,
    blind_assignment_ref: ArtifactRef,
    independent_evaluator_ref: ArtifactRef,
    rater_refs: tuple[ArtifactRef, ...],
) -> SemanticGateProfileArtifact:
    snapshot, value = _canonical(raw, "semantic gate profile")
    profile_ref = _require_ref(profile_ref, "profile_ref")
    if profile_ref.media_type != SEMANTIC_GATE_PROFILE_MEDIA_TYPE or not profile_ref.verify_bytes(snapshot):
        raise SurfaceMeaningValidationError("profile_ref does not bind profile bytes")
    expect_keys(
        value,
        required={"schema", "profile_id", "definitions", "thresholds", "status", "boundary"},
        path="$",
    )
    profile_id = expect_machine_id(value["profile_id"], "$.profile_id")
    if value["schema"] != SEMANTIC_GATE_PROFILE_SCHEMA or profile_id != profile_ref.artifact_id:
        raise SurfaceMeaningValidationError("profile schema or identity changed")
    if type(rater_refs) is not tuple or len(rater_refs) < 2:
        raise SurfaceMeaningValidationError("at least two exact independent raters are required")
    refs = (
        definition_ref,
        crosswalk_ref,
        rubric_ref,
        power_plan_ref,
        blind_assignment_ref,
        independent_evaluator_ref,
        *rater_refs,
    )
    closure = _unique_refs(refs, owner_id=profile_id, path="profile artifact closure")
    definitions = expect_object(value["definitions"], "$.definitions")
    expect_keys(
        definitions,
        required={
            "definition_ref", "crosswalk_ref", "rubric_ref", "power_plan_ref",
            "blind_assignment_ref", "independent_evaluator_ref", "rater_refs",
        },
        path="$.definitions",
    )
    parsed = (
        parse_artifact_ref(definitions["definition_ref"], "$.definitions.definition_ref"),
        parse_artifact_ref(definitions["crosswalk_ref"], "$.definitions.crosswalk_ref"),
        parse_artifact_ref(definitions["rubric_ref"], "$.definitions.rubric_ref"),
        parse_artifact_ref(definitions["power_plan_ref"], "$.definitions.power_plan_ref"),
        parse_artifact_ref(definitions["blind_assignment_ref"], "$.definitions.blind_assignment_ref"),
        parse_artifact_ref(definitions["independent_evaluator_ref"], "$.definitions.independent_evaluator_ref"),
        *(parse_artifact_ref(item, "$.definitions.rater_refs[]") for item in expect_list(definitions["rater_refs"], "$.definitions.rater_refs")),
    )
    if parsed != refs:
        raise SurfaceMeaningValidationError("profile definition or rater binding changed")
    thresholds = expect_object(value["thresholds"], "$.thresholds")
    expect_keys(
        thresholds,
        required={
            "max_surface_overlap_ppm", "min_length_ratio_ppm", "max_length_ratio_ppm",
            "min_meaning_score_ppm", "max_vocabulary_dependence_ppm", "max_rater_spread_ppm",
        },
        path="$.thresholds",
    )
    overlap = expect_object(thresholds["max_surface_overlap_ppm"], "$.thresholds.max_surface_overlap_ppm")
    expect_keys(overlap, required=set(_OVERLAP_AXES), path="$.thresholds.max_surface_overlap_ppm")
    checked_overlap = {
        axis: expect_int(overlap[axis], f"$.thresholds.max_surface_overlap_ppm.{axis}", minimum=0, maximum=1_000_000)
        for axis in _OVERLAP_AXES
    }
    min_length = expect_int(thresholds["min_length_ratio_ppm"], "$.thresholds.min_length_ratio_ppm", minimum=1, maximum=10_000_000)
    max_length = expect_int(thresholds["max_length_ratio_ppm"], "$.thresholds.max_length_ratio_ppm", minimum=1, maximum=10_000_000)
    if min_length > max_length:
        raise SurfaceMeaningValidationError("length ratio bounds are reversed")
    min_meaning = expect_int(thresholds["min_meaning_score_ppm"], "$.thresholds.min_meaning_score_ppm", minimum=0, maximum=1_000_000)
    max_vocab = expect_int(thresholds["max_vocabulary_dependence_ppm"], "$.thresholds.max_vocabulary_dependence_ppm", minimum=0, maximum=1_000_000)
    max_spread = expect_int(thresholds["max_rater_spread_ppm"], "$.thresholds.max_rater_spread_ppm", minimum=0, maximum=1_000_000)
    _require_status(value)
    return SemanticGateProfileArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        profile_id=profile_id,
        definition_ref=refs[0], crosswalk_ref=refs[1], rubric_ref=refs[2],
        power_plan_ref=refs[3], blind_assignment_ref=refs[4], independent_evaluator_ref=refs[5],
        rater_refs=tuple(rater_refs), max_surface_overlap_ppm=MappingProxyType(checked_overlap),
        min_length_ratio_ppm=min_length, max_length_ratio_ppm=max_length,
        min_meaning_score_ppm=min_meaning, max_vocabulary_dependence_ppm=max_vocab,
        max_rater_spread_ppm=max_spread, payload=freeze_json(value), artifact_refs=closure,
    )


def replay_semantic_gate_profile(artifact: SemanticGateProfileArtifact) -> SemanticGateProfileArtifact:
    _require_artifact_storage(artifact, SemanticGateProfileArtifact, "profile")
    if (
        type(artifact.profile_id) is not str
        or type(artifact.rater_refs) is not tuple
        or type(artifact.max_surface_overlap_ppm) is not MappingProxyType
        or set(artifact.max_surface_overlap_ppm) != set(_OVERLAP_AXES)
    ):
        raise SurfaceMeaningValidationError("profile projections changed type or shape")
    for axis in _OVERLAP_AXES:
        expect_int(
            artifact.max_surface_overlap_ppm[axis],
            f"profile.max_surface_overlap_ppm.{axis}",
            minimum=0,
            maximum=1_000_000,
        )
    for name, maximum in (
        ("min_length_ratio_ppm", 10_000_000),
        ("max_length_ratio_ppm", 10_000_000),
        ("min_meaning_score_ppm", 1_000_000),
        ("max_vocabulary_dependence_ppm", 1_000_000),
        ("max_rater_spread_ppm", 1_000_000),
    ):
        expect_int(getattr(artifact, name), f"profile.{name}", minimum=0, maximum=maximum)
    for name in (
        "definition_ref", "crosswalk_ref", "rubric_ref", "power_plan_ref",
        "blind_assignment_ref", "independent_evaluator_ref",
    ):
        _require_ref(getattr(artifact, name), f"profile.{name}")
    for index, reference in enumerate(artifact.rater_refs):
        _require_ref(reference, f"profile.rater_refs[{index}]")
    replayed = load_semantic_gate_profile(
        artifact.raw_bytes, profile_ref=artifact.artifact_ref,
        definition_ref=artifact.definition_ref, crosswalk_ref=artifact.crosswalk_ref,
        rubric_ref=artifact.rubric_ref, power_plan_ref=artifact.power_plan_ref,
        blind_assignment_ref=artifact.blind_assignment_ref,
        independent_evaluator_ref=artifact.independent_evaluator_ref,
        rater_refs=artifact.rater_refs,
    )
    if replayed != artifact:
        raise SurfaceMeaningValidationError("profile differs from exact replay")
    return replayed


def _surface_cell_value(cell: SurfaceGateCellInput, profile: SemanticGateProfileArtifact) -> dict[str, Any]:
    scores = {
        TEXT_OVERLAP: cell.text_overlap_ppm,
        CHARACTER_OVERLAP: cell.character_overlap_ppm,
        TOKEN_OVERLAP: cell.token_overlap_ppm,
        EMBEDDING_OVERLAP: cell.embedding_overlap_ppm,
    }
    passed = {axis: scores[axis] <= profile.max_surface_overlap_ppm[axis] for axis in _OVERLAP_AXES}
    passed.update(
        {
            PROVENANCE: cell.provenance_preserved,
            LENGTH: profile.min_length_ratio_ppm <= cell.length_ratio_ppm <= profile.max_length_ratio_ppm,
            TAXONOMY: cell.taxonomy_preserved,
            CARRIER: cell.carrier_preserved,
            PAYLOAD_FAMILY: cell.payload_family_preserved,
        }
    )
    return {
        "execution_ordinal": cell.execution_ordinal,
        "cell_id": cell.cell_id,
        "prompt_ref": _ref_value(cell.prompt_ref),
        "prompt_source_map_ref": _ref_value(cell.prompt_source_map_ref),
        "source_kind": cell.source_kind,
        "attack_category": cell.attack_category,
        "disposition": cell.disposition,
        "measurements": {
            "text_overlap_ppm": cell.text_overlap_ppm,
            "character_overlap_ppm": cell.character_overlap_ppm,
            "token_overlap_ppm": cell.token_overlap_ppm,
            "embedding_overlap_ppm": cell.embedding_overlap_ppm,
            "length_ratio_ppm": cell.length_ratio_ppm,
            "provenance_preserved": cell.provenance_preserved,
            "taxonomy_preserved": cell.taxonomy_preserved,
            "carrier_preserved": cell.carrier_preserved,
            "payload_family_preserved": cell.payload_family_preserved,
        },
        "axis_pass": {axis: passed[axis] for axis in SURFACE_AXES},
        "failed_axes": [axis for axis in SURFACE_AXES if not passed[axis]],
        "surface_eligible": all(passed.values()),
    }


def _validate_surface_cells(cells: Any, profile: SemanticGateProfileArtifact) -> tuple[SurfaceGateCellInput, ...]:
    if type(cells) is not tuple or not cells:
        raise SurfaceMeaningValidationError("surface cells must be a nonempty exact tuple")
    seen: set[str] = set()
    result: list[SurfaceGateCellInput] = []
    for index, cell in enumerate(cells, start=1):
        if type(cell) is not SurfaceGateCellInput:
            raise SurfaceMeaningValidationError("surface cell type changed")
        cell.__post_init__()
        if cell.execution_ordinal != index or cell.cell_id in seen:
            raise SurfaceMeaningValidationError("surface cells must be unique and contiguous")
        seen.add(cell.cell_id)
        result.append(cell)
    return tuple(result)


def build_surface_gate_receipt(
    *, receipt_id: str, profile: SemanticGateProfileArtifact, protocol_ref: ArtifactRef,
    roster_ref: ArtifactRef, cells: tuple[SurfaceGateCellInput, ...]
) -> SurfaceGateReceiptArtifact:
    receipt_id = expect_machine_id(receipt_id, "receipt_id")
    profile = replay_semantic_gate_profile(profile)
    checked = _validate_surface_cells(cells, profile)
    value = {
        "schema": SURFACE_GATE_RECEIPT_SCHEMA, "receipt_id": receipt_id,
        "profile_ref": _ref_value(profile.artifact_ref), "protocol_ref": _ref_value(protocol_ref),
        "roster_ref": _ref_value(roster_ref),
        "cells": [_surface_cell_value(cell, profile) for cell in checked],
        "status": dict(_STATUS), "boundary": dict(_BOUNDARY),
    }
    raw = canonical_json_bytes(value)
    return load_surface_gate_receipt(
        raw,
        receipt_ref=ArtifactRef(receipt_id, sha256_bytes(raw), len(raw), SURFACE_GATE_RECEIPT_MEDIA_TYPE),
        profile=profile, protocol_ref=protocol_ref, roster_ref=roster_ref, cells=checked,
    )


def load_surface_gate_receipt(
    raw: Any, *, receipt_ref: ArtifactRef, profile: SemanticGateProfileArtifact,
    protocol_ref: ArtifactRef, roster_ref: ArtifactRef, cells: tuple[SurfaceGateCellInput, ...]
) -> SurfaceGateReceiptArtifact:
    snapshot, value = _canonical(raw, "surface gate receipt")
    profile = replay_semantic_gate_profile(profile)
    receipt_ref = _require_ref(receipt_ref, "receipt_ref")
    protocol_ref = _require_ref(protocol_ref, "protocol_ref")
    roster_ref = _require_ref(roster_ref, "roster_ref")
    if receipt_ref.media_type != SURFACE_GATE_RECEIPT_MEDIA_TYPE or not receipt_ref.verify_bytes(snapshot):
        raise SurfaceMeaningValidationError("surface receipt reference changed")
    expect_keys(value, required={"schema", "receipt_id", "profile_ref", "protocol_ref", "roster_ref", "cells", "status", "boundary"}, path="$")
    receipt_id = expect_machine_id(value["receipt_id"], "$.receipt_id")
    checked = _validate_surface_cells(cells, profile)
    expected = {
        "schema": SURFACE_GATE_RECEIPT_SCHEMA, "receipt_id": receipt_id,
        "profile_ref": _ref_value(profile.artifact_ref), "protocol_ref": _ref_value(protocol_ref),
        "roster_ref": _ref_value(roster_ref), "cells": [_surface_cell_value(cell, profile) for cell in checked],
        "status": dict(_STATUS), "boundary": dict(_BOUNDARY),
    }
    if receipt_id != receipt_ref.artifact_id or value != expected:
        raise SurfaceMeaningValidationError("surface receipt differs from exact caller-bound projection")
    _require_status(value)
    refs = _unique_refs(
        (profile.artifact_ref, *profile.artifact_refs, protocol_ref, roster_ref, *(ref for cell in checked for ref in (cell.prompt_ref, cell.prompt_source_map_ref))),
        owner_id=receipt_id, path="surface receipt artifact closure",
    )
    return SurfaceGateReceiptArtifact(snapshot, sha256_bytes(snapshot), len(snapshot), receipt_id, profile, protocol_ref, roster_ref, checked, freeze_json(value), refs)


def replay_surface_gate_receipt(artifact: SurfaceGateReceiptArtifact) -> SurfaceGateReceiptArtifact:
    _require_artifact_storage(artifact, SurfaceGateReceiptArtifact, "surface receipt")
    replayed = load_surface_gate_receipt(
        artifact.raw_bytes, receipt_ref=artifact.artifact_ref, profile=artifact.profile,
        protocol_ref=artifact.protocol_ref, roster_ref=artifact.roster_ref, cells=artifact.cells,
    )
    if replayed != artifact:
        raise SurfaceMeaningValidationError("surface receipt differs from exact replay")
    return replayed


def _meaning_cell_value(cell: MeaningPreservationCellInput, surface_cell: SurfaceGateCellInput, profile: SemanticGateProfileArtifact) -> dict[str, Any]:
    spread = max(cell.rater_scores_ppm) - min(cell.rater_scores_ppm)
    rater_floor = min(cell.rater_scores_ppm)
    surface_value = _surface_cell_value(surface_cell, profile)
    meaning_pass = (
        cell.task_preserved and cell.label_blinded
        and cell.independent_evaluator_score_ppm >= profile.min_meaning_score_ppm
        and rater_floor >= profile.min_meaning_score_ppm
        and cell.vocabulary_dependence_ppm <= profile.max_vocabulary_dependence_ppm
        and spread <= profile.max_rater_spread_ppm
    )
    return {
        "execution_ordinal": cell.execution_ordinal, "cell_id": cell.cell_id,
        "surface_cell_id": cell.surface_cell_id,
        "paraphrase_ref": _ref_value(cell.paraphrase_ref),
        "paraphrase_provenance_ref": _ref_value(cell.paraphrase_provenance_ref),
        "task_preserved": cell.task_preserved, "label_blinded": cell.label_blinded,
        "independent_evaluator_score_ppm": cell.independent_evaluator_score_ppm,
        "vocabulary_dependence_ppm": cell.vocabulary_dependence_ppm,
        "rater_scores_ppm": list(cell.rater_scores_ppm), "rater_spread_ppm": spread,
        "meaning_preserved": meaning_pass,
        "surface_eligible": surface_value["surface_eligible"],
        "eligible_for_narrow_claim": meaning_pass and surface_value["surface_eligible"],
    }


def _validate_meaning_cells(
    cells: Any, surface_gate: SurfaceGateReceiptArtifact, profile: SemanticGateProfileArtifact
) -> tuple[MeaningPreservationCellInput, ...]:
    if type(cells) is not tuple or len(cells) != len(surface_gate.cells):
        raise SurfaceMeaningValidationError("meaning cells must match the surface roster exactly")
    seen: set[str] = set()
    result: list[MeaningPreservationCellInput] = []
    for index, (cell, surface_cell) in enumerate(zip(cells, surface_gate.cells), start=1):
        if type(cell) is not MeaningPreservationCellInput:
            raise SurfaceMeaningValidationError("meaning cell type changed")
        cell.__post_init__()
        if (
            cell.execution_ordinal != index or cell.surface_cell_id != surface_cell.cell_id
            or cell.cell_id in seen or len(cell.rater_scores_ppm) != len(profile.rater_refs)
        ):
            raise SurfaceMeaningValidationError("meaning cells are mixed, duplicated, or misbound")
        seen.add(cell.cell_id)
        result.append(cell)
    return tuple(result)


def build_meaning_preservation_receipt(
    *, receipt_id: str, profile: SemanticGateProfileArtifact,
    surface_gate: SurfaceGateReceiptArtifact, cells: tuple[MeaningPreservationCellInput, ...]
) -> MeaningPreservationReceiptArtifact:
    receipt_id = expect_machine_id(receipt_id, "receipt_id")
    profile = replay_semantic_gate_profile(profile)
    surface_gate = replay_surface_gate_receipt(surface_gate)
    if surface_gate.profile.artifact_ref != profile.artifact_ref:
        raise SurfaceMeaningValidationError("meaning profile differs from surface profile")
    checked = _validate_meaning_cells(cells, surface_gate, profile)
    value = {
        "schema": MEANING_PRESERVATION_RECEIPT_SCHEMA, "receipt_id": receipt_id,
        "profile_ref": _ref_value(profile.artifact_ref), "surface_gate_ref": _ref_value(surface_gate.artifact_ref),
        "cells": [_meaning_cell_value(cell, surface_cell, profile) for cell, surface_cell in zip(checked, surface_gate.cells)],
        "status": dict(_STATUS), "boundary": dict(_BOUNDARY),
    }
    raw = canonical_json_bytes(value)
    return load_meaning_preservation_receipt(
        raw,
        receipt_ref=ArtifactRef(receipt_id, sha256_bytes(raw), len(raw), MEANING_PRESERVATION_RECEIPT_MEDIA_TYPE),
        profile=profile, surface_gate=surface_gate, cells=checked,
    )


def load_meaning_preservation_receipt(
    raw: Any, *, receipt_ref: ArtifactRef, profile: SemanticGateProfileArtifact,
    surface_gate: SurfaceGateReceiptArtifact, cells: tuple[MeaningPreservationCellInput, ...]
) -> MeaningPreservationReceiptArtifact:
    snapshot, value = _canonical(raw, "meaning preservation receipt")
    profile = replay_semantic_gate_profile(profile)
    surface_gate = replay_surface_gate_receipt(surface_gate)
    if surface_gate.profile.artifact_ref != profile.artifact_ref:
        raise SurfaceMeaningValidationError(
            "meaning profile differs from the exact surface profile"
        )
    receipt_ref = _require_ref(receipt_ref, "receipt_ref")
    if receipt_ref.media_type != MEANING_PRESERVATION_RECEIPT_MEDIA_TYPE or not receipt_ref.verify_bytes(snapshot):
        raise SurfaceMeaningValidationError("meaning receipt reference changed")
    expect_keys(value, required={"schema", "receipt_id", "profile_ref", "surface_gate_ref", "cells", "status", "boundary"}, path="$")
    receipt_id = expect_machine_id(value["receipt_id"], "$.receipt_id")
    checked = _validate_meaning_cells(cells, surface_gate, profile)
    expected = {
        "schema": MEANING_PRESERVATION_RECEIPT_SCHEMA, "receipt_id": receipt_id,
        "profile_ref": _ref_value(profile.artifact_ref), "surface_gate_ref": _ref_value(surface_gate.artifact_ref),
        "cells": [_meaning_cell_value(cell, surface_cell, profile) for cell, surface_cell in zip(checked, surface_gate.cells)],
        "status": dict(_STATUS), "boundary": dict(_BOUNDARY),
    }
    if receipt_id != receipt_ref.artifact_id or value != expected:
        raise SurfaceMeaningValidationError("meaning receipt differs from exact caller-bound projection")
    _require_status(value)
    refs = _unique_refs(
        (surface_gate.artifact_ref, *surface_gate.artifact_refs, *(ref for cell in checked for ref in (cell.paraphrase_ref, cell.paraphrase_provenance_ref))),
        owner_id=receipt_id, path="meaning receipt artifact closure",
    )
    return MeaningPreservationReceiptArtifact(snapshot, sha256_bytes(snapshot), len(snapshot), receipt_id, profile, surface_gate, checked, freeze_json(value), refs)


def replay_meaning_preservation_receipt(artifact: MeaningPreservationReceiptArtifact) -> MeaningPreservationReceiptArtifact:
    _require_artifact_storage(artifact, MeaningPreservationReceiptArtifact, "meaning receipt")
    replayed = load_meaning_preservation_receipt(
        artifact.raw_bytes, receipt_ref=artifact.artifact_ref, profile=artifact.profile,
        surface_gate=artifact.surface_gate, cells=artifact.cells,
    )
    if replayed != artifact:
        raise SurfaceMeaningValidationError("meaning receipt differs from exact replay")
    return replayed


def _require_artifact_storage(value: Any, expected: type[Any], path: str) -> None:
    if type(value) is not expected:
        raise SurfaceMeaningValidationError(f"{path} must have exact type {expected.__name__}")
    if (
        type(value.raw_bytes) is not bytes or type(value.sha256) is not str
        or type(value.byte_length) is not int or type(value.artifact_refs) is not tuple
        or value.sha256 != sha256_bytes(value.raw_bytes) or value.byte_length != len(value.raw_bytes)
    ):
        raise SurfaceMeaningValidationError(f"{path} storage projections changed")
    _require_frozen(value.payload, f"{path}.payload")
    if canonical_json_bytes(thaw_json(value.payload)) != value.raw_bytes:
        raise SurfaceMeaningValidationError(f"{path} payload differs from raw bytes")
    for index, reference in enumerate(value.artifact_refs):
        _require_ref(reference, f"{path}.artifact_refs[{index}]")


__all__ = (
    "SEMANTIC_GATE_PROFILE_SCHEMA", "SURFACE_GATE_RECEIPT_SCHEMA",
    "MEANING_PRESERVATION_RECEIPT_SCHEMA", "SEMANTIC_GATE_PROFILE_MEDIA_TYPE",
    "SURFACE_GATE_RECEIPT_MEDIA_TYPE", "MEANING_PRESERVATION_RECEIPT_MEDIA_TYPE",
    "TEXT_OVERLAP", "CHARACTER_OVERLAP", "TOKEN_OVERLAP", "EMBEDDING_OVERLAP",
    "PROVENANCE", "LENGTH", "TAXONOMY", "CARRIER", "PAYLOAD_FAMILY", "SURFACE_AXES",
    "USER", "SYSTEM", "TOOL", "RETRIEVED", "EXTERNAL", "SOURCE_KINDS",
    "MEANING_BEARING", "VOCABULARY_DEPENDENT", "CELL_DISPOSITIONS",
    "STRUCTURE_ONLY", "NON_AUTHORITY", "NOT_LICENSED", "REPLAY_ONLY", "PER_CELL_ONLY",
    "SurfaceMeaningValidationError", "SurfaceGateCellInput", "MeaningPreservationCellInput",
    "SemanticGateProfileArtifact", "SurfaceGateReceiptArtifact", "MeaningPreservationReceiptArtifact",
    "build_semantic_gate_profile", "load_semantic_gate_profile", "replay_semantic_gate_profile",
    "build_surface_gate_receipt", "load_surface_gate_receipt", "replay_surface_gate_receipt",
    "build_meaning_preservation_receipt", "load_meaning_preservation_receipt",
    "replay_meaning_preservation_receipt",
)
