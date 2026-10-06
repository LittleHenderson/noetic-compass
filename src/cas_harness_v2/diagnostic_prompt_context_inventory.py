"""Exact 480-row inventory for diagnostic Stage C prompt provenance.

The per-request provenance carrier proves how one prompt was reconstructed.
This additive aggregate proves that one fully replayed companion exists for
every row of the frozen diagnostic split, in the split's exact order.  It does
not change the request, Study, authorization, or worker schemas and grants no
execution, scientific, Packet, licensing, or product authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ._strict_json import (
    StrictJSONError,
    canonical_json_bytes,
    canonical_sha256,
    freeze_json,
    load_json_object,
    sha256_bytes,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_int,
    expect_keys,
    expect_list,
    expect_machine_id,
    expect_object,
    expect_sha256,
    expect_string,
    expect_timestamp,
    parse_artifact_ref,
)
from .diagnostic_prompt_context_provenance import (
    STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
    STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE,
    STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    StageCPromptContextNodeArtifact,
    StageCPromptContextProvenanceArtifact,
    replay_stagec_prompt_context_provenance_projection,
    resolve_stagec_prompt_context,
)
from .diagnostic_study_protocol import (
    DIAGNOSTIC_CASE_COUNT,
    DIAGNOSTIC_GROUP_COUNT,
    DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE,
    STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    DiagnosticSplitInventoryArtifact,
    DiagnosticStudyCase,
    StageCCaptureRequestArtifact,
    load_diagnostic_split_inventory,
)


STAGEC_PROMPT_CONTEXT_INVENTORY_SCHEMA = (
    "cas_harness_v2.stagec_prompt_context_inventory.v1"
)
STAGEC_PROMPT_CONTEXT_INVENTORY_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-prompt-context-inventory+json"
)
MAX_PROMPT_CONTEXT_INVENTORY_DEPENDENCY_ARTIFACTS = 5_000

_ORDERED_CONTEXTS_DOMAIN = (
    "cas_harness_v2.stagec_prompt_context_inventory_rows.v1"
)
_DEPENDENCY_CLOSURE_DOMAIN = (
    "cas_harness_v2.stagec_prompt_context_inventory_dependencies.v1"
)
_NODE_CLOSURE_DOMAIN = (
    "cas_harness_v2.stagec_prompt_context_inventory_nodes.v1"
)
_SOURCE_CLOSURE_DOMAIN = (
    "cas_harness_v2.stagec_prompt_context_inventory_sources.v1"
)

_AUTHORITY = {
    "scope": "STRUCTURE_ONLY",
    "execution_authority": "NOT_GRANTED",
    "worker_consumption": "NOT_ESTABLISHED",
    "authentication": "NOT_PROVIDED",
    "trusted_time": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "corpus_freeze": "NOT_ESTABLISHED",
    "scientific_conclusion": "NOT_ESTABLISHED",
    "detector_result": "NOT_CREATED",
    "packet_v2": "FORBIDDEN",
    "claim_promotion": "FORBIDDEN",
    "license": "NOT_GRANTED",
    "product": "NOT_AUTHORIZED",
    "disclosure": "HELD",
}

_BOUNDARY = {
    "aggregate_role": "AUDIT_ONLY_EXACT_SPLIT_ORDER_PROVENANCE_COVERAGE",
    "existing_schema_changes": "NONE_ADDITIVE_COMPANION_ONLY",
    "source_bytes": "EXTERNAL_EXACT_BYTES_REQUIRED_FOR_FULL_REPLAY",
    "node_operations": "SOURCE_AND_ORDERED_UTF8_CONCAT_ONLY",
    "declared_origins": "LABELS_ONLY_NOT_ACTUAL_CHAT_ROLES",
    "rendered_channel": "USER_CONTENT_SINGLE_MESSAGE_UNCHANGED",
    "normalization": "FORBIDDEN_RAW_UTF8_BYTES_ONLY",
    "preregistration_binding": "PROSPECTIVE_INPUT_ARTIFACT_REQUIRED",
    "preexecution_drc": "NOT_PERFORMED",
    "runtime_admission": "NOT_PERFORMED",
}

_INVENTORY_KEYS = {
    "schema_version",
    "inventory_id",
    "created_at",
    "diagnostic_split_inventory",
    "study_binding",
    "ordered_contexts",
    "ordered_contexts_sha256",
    "unique_node_artifact_count",
    "ordered_unique_node_artifacts_sha256",
    "unique_source_artifact_count",
    "ordered_unique_source_artifacts_sha256",
    "dependency_artifact_count",
    "dependency_closure_sha256",
    "authority",
    "boundary",
}

_ROW_KEYS = {
    "execution_ordinal",
    "case_id",
    "base_intent_group_id",
    "split_id",
    "frozen_variant",
    "frozen_label",
    "invocation_id",
    "capture_request",
    "prompt_context_provenance",
    "root_node",
    "ordered_node_closure_sha256",
    "prompt_utf8",
}


class StageCPromptContextInventoryError(ValueError):
    """The exact aggregate prompt-context inventory failed closed."""


class StageCPromptContextInventoryIntegrityError(
    StageCPromptContextInventoryError
):
    """Aggregate raw bytes or projected fields disagree."""


@dataclass(frozen=True, slots=True)
class StageCPromptContextReplayBundle:
    provenance: StageCPromptContextProvenanceArtifact
    ordered_nodes: tuple[StageCPromptContextNodeArtifact, ...]
    source_bodies: tuple[tuple[ArtifactRef, bytes], ...]


@dataclass(frozen=True, slots=True)
class StageCPromptContextInventoryRow:
    execution_ordinal: int
    case_id: str
    capture_request: ArtifactRef
    provenance: ArtifactRef
    root_node: ArtifactRef
    ordered_node_closure_sha256: str
    prompt_sha256: str
    prompt_byte_length: int


@dataclass(frozen=True, slots=True)
class StageCPromptContextInventoryArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    inventory_id: str
    created_at: str
    diagnostic_split_inventory: ArtifactRef
    rows: tuple[StageCPromptContextInventoryRow, ...]
    ordered_contexts_sha256: str
    ordered_node_artifacts: tuple[ArtifactRef, ...]
    ordered_source_artifacts: tuple[ArtifactRef, ...]
    dependency_artifact_count: int
    dependency_closure_sha256: str
    payload: MappingProxyType

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.inventory_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STAGEC_PROMPT_CONTEXT_INVENTORY_MEDIA_TYPE,
        )


def _ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _canonical_object(
    raw: bytes | bytearray | memoryview,
    label: str,
) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, obj = load_json_object(raw)
    except (StrictJSONError, SchemaValidationError) as exc:
        raise StageCPromptContextInventoryError(f"{label}: {exc}") from exc
    if snapshot != canonical_json_bytes(obj):
        raise StageCPromptContextInventoryError(
            f"{label} must use exact canonical JSON bytes"
        )
    return snapshot, obj


def _require_ref(
    reference: Any,
    path: str,
    *,
    media_type: str | None = None,
) -> ArtifactRef:
    if type(reference) is not ArtifactRef:
        raise StageCPromptContextInventoryError(
            f"{path} must be an exact ArtifactRef"
        )
    if media_type is not None and reference.media_type != media_type:
        raise StageCPromptContextInventoryError(
            f"{path} must retain media type {media_type!r}"
        )
    return reference


def _require_request_projection_types(
    request: StageCCaptureRequestArtifact,
    path: str,
) -> None:
    if (
        type(request) is not StageCCaptureRequestArtifact
        or type(request.raw_bytes) is not bytes
        or type(request.sha256) is not str
        or type(request.byte_length) is not int
        or type(request.artifact_ref) is not ArtifactRef
        or type(request.study_id) is not str
        or type(request.case_id) is not str
        or type(request.split_id) is not str
        or type(request.base_intent_group_id) is not str
        or type(request.frozen_variant) is not str
        or type(request.frozen_label) is not str
        or type(request.invocation_id) is not str
        or type(request.prompt) is not str
        or type(request.payload) is not MappingProxyType
    ):
        raise StageCPromptContextInventoryIntegrityError(
            f"{path} projections must use exact immutable types"
        )


def _require_case_projection_types(case: DiagnosticStudyCase, path: str) -> None:
    if (
        type(case) is not DiagnosticStudyCase
        or type(case.execution_ordinal) is not int
        or type(case.case_id) is not str
        or type(case.base_intent_group_id) is not str
        or type(case.split_id) is not str
        or type(case.frozen_variant) is not str
        or type(case.frozen_label) is not str
        or type(case.invocation_id) is not str
        or type(case.capture_request) is not ArtifactRef
    ):
        raise StageCPromptContextInventoryIntegrityError(
            f"{path} projections must use exact immutable types"
        )


def _fresh_split_inventory(
    inventory: DiagnosticSplitInventoryArtifact,
) -> DiagnosticSplitInventoryArtifact:
    if (
        type(inventory) is not DiagnosticSplitInventoryArtifact
        or type(inventory.raw_bytes) is not bytes
        or type(inventory.sha256) is not str
        or type(inventory.byte_length) is not int
        or type(inventory.inventory_id) is not str
        or type(inventory.study_id) is not str
        or type(inventory.split_id) is not str
        or type(inventory.cases) is not tuple
        or type(inventory.capture_requests) is not tuple
        or type(inventory.ordered_case_inventory_sha256) is not str
        or type(inventory.payload) is not MappingProxyType
        or type(inventory.artifact_refs) is not tuple
    ):
        raise StageCPromptContextInventoryIntegrityError(
            "diagnostic split inventory projections must use exact immutable types"
        )
    for index, case in enumerate(inventory.cases):
        _require_case_projection_types(case, f"inventory.cases[{index}]")
    for index, request in enumerate(inventory.capture_requests):
        _require_request_projection_types(
            request,
            f"inventory.capture_requests[{index}]",
        )
    if any(type(item) is not ArtifactRef for item in inventory.artifact_refs):
        raise StageCPromptContextInventoryIntegrityError(
            "diagnostic split inventory refs must be exact ArtifactRefs"
        )
    try:
        exact = load_diagnostic_split_inventory(
            inventory.raw_bytes,
            capture_requests=inventory.capture_requests,
        )
    except (SchemaValidationError, ValueError) as exc:
        raise StageCPromptContextInventoryError(
            f"diagnostic split inventory replay failed: {exc}"
        ) from exc
    if exact != inventory:
        raise StageCPromptContextInventoryIntegrityError(
            "diagnostic split inventory differs from exact-byte replay"
        )
    return exact


def _require_bundle_types(
    bundle: StageCPromptContextReplayBundle,
    index: int,
) -> None:
    if (
        type(bundle) is not StageCPromptContextReplayBundle
        or type(bundle.provenance) is not StageCPromptContextProvenanceArtifact
        or type(bundle.ordered_nodes) is not tuple
        or not bundle.ordered_nodes
        or any(
            type(item) is not StageCPromptContextNodeArtifact
            for item in bundle.ordered_nodes
        )
        or type(bundle.source_bodies) is not tuple
    ):
        raise StageCPromptContextInventoryIntegrityError(
            f"replay_bundles[{index}] must use exact immutable carrier types"
        )
    for source_index, pair in enumerate(bundle.source_bodies):
        if (
            type(pair) is not tuple
            or len(pair) != 2
            or type(pair[0]) is not ArtifactRef
            or type(pair[1]) is not bytes
        ):
            raise StageCPromptContextInventoryIntegrityError(
                "replay_bundles"
                f"[{index}].source_bodies[{source_index}] is not exact"
            )


def _row_value(
    case: DiagnosticStudyCase,
    provenance: StageCPromptContextProvenanceArtifact,
) -> dict[str, Any]:
    return {
        "execution_ordinal": case.execution_ordinal,
        "case_id": case.case_id,
        "base_intent_group_id": case.base_intent_group_id,
        "split_id": case.split_id,
        "frozen_variant": case.frozen_variant,
        "frozen_label": case.frozen_label,
        "invocation_id": case.invocation_id,
        "capture_request": _ref_value(case.capture_request),
        "prompt_context_provenance": _ref_value(provenance.artifact_ref),
        "root_node": _ref_value(provenance.root_node),
        "ordered_node_closure_sha256": (
            provenance.ordered_node_closure_sha256
        ),
        "prompt_utf8": {
            "sha256": provenance.prompt_sha256,
            "byte_length": provenance.prompt_byte_length,
            "media_type": STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
        },
    }


def _row_digest(rows: list[dict[str, Any]]) -> str:
    return _safe_canonical_sha256(
        {
            "domain": _ORDERED_CONTEXTS_DOMAIN,
            "ordered_contexts": rows,
        },
        "ordered prompt-context rows",
    )


def _dependency_digest(references: tuple[ArtifactRef, ...]) -> str:
    return _ref_closure_digest(
        references,
        domain=_DEPENDENCY_CLOSURE_DOMAIN,
        label="prompt-context dependency closure",
    )


def _ref_closure_digest(
    references: tuple[ArtifactRef, ...],
    *,
    domain: str,
    label: str,
) -> str:
    return _safe_canonical_sha256(
        {
            "domain": domain,
            "ordered_artifacts": [_ref_value(item) for item in references],
        },
        label,
    )


def _safe_canonical_sha256(value: Any, label: str) -> str:
    try:
        return canonical_sha256(value)
    except StrictJSONError as exc:
        raise StageCPromptContextInventoryError(
            f"{label} exceeds the strict canonical JSON bounds: {exc}"
        ) from exc


def _register_unique_dependency(
    reference: ArtifactRef,
    *,
    by_id: dict[str, ArtifactRef],
    by_content: dict[tuple[str, int], ArtifactRef],
    ordered: list[ArtifactRef],
) -> None:
    reference = _require_ref(reference, "dependency artifact")
    existing = by_id.get(reference.artifact_id)
    if existing is not None:
        if existing != reference:
            raise StageCPromptContextInventoryError(
                "one dependency artifact ID is bound to conflicting refs"
            )
        return
    content_key = (reference.sha256, reference.byte_length)
    content_existing = by_content.get(content_key)
    if content_existing is not None and content_existing.artifact_id != (
        reference.artifact_id
    ):
        raise StageCPromptContextInventoryError(
            "dependency content is cloned under different artifact IDs"
        )
    by_id[reference.artifact_id] = reference
    by_content[content_key] = reference
    ordered.append(reference)


@dataclass(frozen=True, slots=True)
class _ReplayedAggregate:
    split_inventory: DiagnosticSplitInventoryArtifact
    provenances: tuple[StageCPromptContextProvenanceArtifact, ...]
    rows: tuple[dict[str, Any], ...]
    node_artifacts: tuple[ArtifactRef, ...]
    source_artifacts: tuple[ArtifactRef, ...]
    dependency_artifacts: tuple[ArtifactRef, ...]


def _replay_aggregate(
    *,
    split_inventory: DiagnosticSplitInventoryArtifact,
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...],
) -> _ReplayedAggregate:
    split = _fresh_split_inventory(split_inventory)
    if type(replay_bundles) is not tuple:
        raise StageCPromptContextInventoryError(
            "replay_bundles must be an exact tuple"
        )
    if len(replay_bundles) != DIAGNOSTIC_CASE_COUNT:
        raise StageCPromptContextInventoryError(
            f"prompt-context inventory requires exactly {DIAGNOSTIC_CASE_COUNT} bundles"
        )

    provenances: list[StageCPromptContextProvenanceArtifact] = []
    rows: list[dict[str, Any]] = []
    node_refs: list[ArtifactRef] = []
    source_refs: list[ArtifactRef] = []
    node_by_id: dict[str, ArtifactRef] = {}
    node_by_content: dict[tuple[str, int], ArtifactRef] = {}
    source_by_id: dict[str, ArtifactRef] = {}
    source_by_content: dict[tuple[str, int], ArtifactRef] = {}

    for index, (case, request, bundle) in enumerate(
        zip(split.cases, split.capture_requests, replay_bundles)
    ):
        _require_bundle_types(bundle, index)
        try:
            provenance = replay_stagec_prompt_context_provenance_projection(
                bundle.provenance,
                capture_request=request,
                ordered_nodes=bundle.ordered_nodes,
                source_bodies=bundle.source_bodies,
            )
            resolved = resolve_stagec_prompt_context(
                ordered_nodes=bundle.ordered_nodes,
                source_bodies=bundle.source_bodies,
                root_node=provenance.root_node,
            )
        except ValueError as exc:
            raise StageCPromptContextInventoryError(
                f"prompt-context row {index + 1} replay failed: {exc}"
            ) from exc
        if provenance.capture_request != request.artifact_ref:
            raise StageCPromptContextInventoryError(
                f"prompt-context row {index + 1} binds the wrong capture request"
            )
        if case.execution_ordinal != index + 1:
            raise StageCPromptContextInventoryError(
                "diagnostic split execution ordinals are not exact and contiguous"
            )
        provenances.append(provenance)
        rows.append(_row_value(case, provenance))
        for node in resolved.ordered_nodes:
            _register_unique_dependency(
                node.artifact_ref,
                by_id=node_by_id,
                by_content=node_by_content,
                ordered=node_refs,
            )
        source_ref_by_id = {
            reference.artifact_id: reference
            for reference, _ in resolved.source_bodies
        }
        for node in resolved.ordered_nodes:
            if node.source_artifact is None:
                continue
            source_ref = source_ref_by_id[node.source_artifact.artifact_id]
            if source_ref != node.source_artifact:
                raise StageCPromptContextInventoryError(
                    "resolved source artifact differs from its SOURCE node"
                )
            _register_unique_dependency(
                source_ref,
                by_id=source_by_id,
                by_content=source_by_content,
                ordered=source_refs,
            )

    provenance_refs = tuple(item.artifact_ref for item in provenances)
    if len({item.artifact_id for item in provenance_refs}) != len(provenance_refs):
        raise StageCPromptContextInventoryError(
            "prompt-context provenance IDs are not unique across 480 rows"
        )
    if len(
        {(item.sha256, item.byte_length) for item in provenance_refs}
    ) != len(provenance_refs):
        raise StageCPromptContextInventoryError(
            "prompt-context provenance content is cloned across 480 rows"
        )

    dependency_order: list[ArtifactRef] = []
    dependency_by_id: dict[str, ArtifactRef] = {}
    dependency_by_content: dict[tuple[str, int], ArtifactRef] = {}
    for reference in (
        split.artifact_ref,
        *(item.artifact_ref for item in split.capture_requests),
        *provenance_refs,
        *node_refs,
        *source_refs,
    ):
        _register_unique_dependency(
            reference,
            by_id=dependency_by_id,
            by_content=dependency_by_content,
            ordered=dependency_order,
        )
    if len(dependency_order) > MAX_PROMPT_CONTEXT_INVENTORY_DEPENDENCY_ARTIFACTS:
        raise StageCPromptContextInventoryError(
            "prompt-context aggregate dependency closure exceeds its v1 bound"
        )
    return _ReplayedAggregate(
        split_inventory=split,
        provenances=tuple(provenances),
        rows=tuple(rows),
        node_artifacts=tuple(node_refs),
        source_artifacts=tuple(source_refs),
        dependency_artifacts=tuple(dependency_order),
    )


def _inventory_value(
    *,
    inventory_id: str,
    created_at: str,
    replayed: _ReplayedAggregate,
) -> dict[str, Any]:
    split = replayed.split_inventory
    rows = list(replayed.rows)
    return {
        "schema_version": STAGEC_PROMPT_CONTEXT_INVENTORY_SCHEMA,
        "inventory_id": inventory_id,
        "created_at": created_at,
        "diagnostic_split_inventory": _ref_value(split.artifact_ref),
        "study_binding": {
            "study_id": split.study_id,
            "split_id": split.split_id,
            "group_count": DIAGNOSTIC_GROUP_COUNT,
            "case_count": DIAGNOSTIC_CASE_COUNT,
            "ordered_case_inventory_sha256": (
                split.ordered_case_inventory_sha256
            ),
        },
        "ordered_contexts": rows,
        "ordered_contexts_sha256": _row_digest(rows),
        "unique_node_artifact_count": len(replayed.node_artifacts),
        "ordered_unique_node_artifacts_sha256": _ref_closure_digest(
            replayed.node_artifacts,
            domain=_NODE_CLOSURE_DOMAIN,
            label="ordered unique prompt-context nodes",
        ),
        "unique_source_artifact_count": len(replayed.source_artifacts),
        "ordered_unique_source_artifacts_sha256": _ref_closure_digest(
            replayed.source_artifacts,
            domain=_SOURCE_CLOSURE_DOMAIN,
            label="ordered unique prompt-context sources",
        ),
        "dependency_artifact_count": len(replayed.dependency_artifacts),
        "dependency_closure_sha256": _dependency_digest(
            replayed.dependency_artifacts
        ),
        "authority": dict(_AUTHORITY),
        "boundary": dict(_BOUNDARY),
    }


def _parse_row(value: Any, index: int) -> StageCPromptContextInventoryRow:
    try:
        row = expect_object(value, f"$.ordered_contexts[{index}]")
        expect_keys(row, required=_ROW_KEYS, path=f"$.ordered_contexts[{index}]")
        ordinal = expect_int(
            row["execution_ordinal"],
            f"$.ordered_contexts[{index}].execution_ordinal",
            minimum=1,
            maximum=DIAGNOSTIC_CASE_COUNT,
        )
        case_id = expect_machine_id(
            row["case_id"],
            f"$.ordered_contexts[{index}].case_id",
        )
        for key in (
            "base_intent_group_id",
            "split_id",
            "frozen_variant",
            "frozen_label",
            "invocation_id",
        ):
            expect_string(row[key], f"$.ordered_contexts[{index}].{key}")
        capture_request = parse_artifact_ref(
            row["capture_request"],
            f"$.ordered_contexts[{index}].capture_request",
        )
        provenance = parse_artifact_ref(
            row["prompt_context_provenance"],
            f"$.ordered_contexts[{index}].prompt_context_provenance",
        )
        root_node = parse_artifact_ref(
            row["root_node"],
            f"$.ordered_contexts[{index}].root_node",
        )
        node_closure_sha = expect_sha256(
            row["ordered_node_closure_sha256"],
            f"$.ordered_contexts[{index}].ordered_node_closure_sha256",
        )
        prompt = expect_object(
            row["prompt_utf8"],
            f"$.ordered_contexts[{index}].prompt_utf8",
        )
        expect_keys(
            prompt,
            required={"sha256", "byte_length", "media_type"},
            path=f"$.ordered_contexts[{index}].prompt_utf8",
        )
        prompt_sha = expect_sha256(
            prompt["sha256"],
            f"$.ordered_contexts[{index}].prompt_utf8.sha256",
        )
        prompt_length = expect_int(
            prompt["byte_length"],
            f"$.ordered_contexts[{index}].prompt_utf8.byte_length",
            minimum=1,
        )
    except SchemaValidationError as exc:
        raise StageCPromptContextInventoryError(str(exc)) from exc
    _require_ref(
        capture_request,
        "row capture request",
        media_type=STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    )
    _require_ref(
        provenance,
        "row prompt-context provenance",
        media_type=STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE,
    )
    _require_ref(
        root_node,
        "row root node",
        media_type=STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
    )
    if prompt["media_type"] != STAGEC_PROMPT_SOURCE_MEDIA_TYPE:
        raise StageCPromptContextInventoryError(
            "row prompt UTF-8 media type drifted"
        )
    return StageCPromptContextInventoryRow(
        execution_ordinal=ordinal,
        case_id=case_id,
        capture_request=capture_request,
        provenance=provenance,
        root_node=root_node,
        ordered_node_closure_sha256=node_closure_sha,
        prompt_sha256=prompt_sha,
        prompt_byte_length=prompt_length,
    )


def load_stagec_prompt_context_inventory(
    raw: bytes | bytearray | memoryview,
    *,
    split_inventory: DiagnosticSplitInventoryArtifact,
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...],
) -> StageCPromptContextInventoryArtifact:
    """Strict-load and fully replay all 480 prompt-context companions."""

    replayed = _replay_aggregate(
        split_inventory=split_inventory,
        replay_bundles=replay_bundles,
    )
    snapshot, obj = _canonical_object(raw, "Stage C prompt-context inventory")
    try:
        expect_keys(obj, required=_INVENTORY_KEYS, path="$")
        if obj["schema_version"] != STAGEC_PROMPT_CONTEXT_INVENTORY_SCHEMA:
            raise SchemaValidationError("wrong prompt-context inventory schema")
        inventory_id = expect_machine_id(obj["inventory_id"], "$.inventory_id")
        created_at = expect_timestamp(obj["created_at"], "$.created_at")
        split_ref = parse_artifact_ref(
            obj["diagnostic_split_inventory"],
            "$.diagnostic_split_inventory",
        )
        row_values = expect_list(obj["ordered_contexts"], "$.ordered_contexts")
        if len(row_values) != DIAGNOSTIC_CASE_COUNT:
            raise SchemaValidationError(
                f"$.ordered_contexts must contain {DIAGNOSTIC_CASE_COUNT} rows"
            )
        rows = tuple(_parse_row(item, index) for index, item in enumerate(row_values))
        rows_sha = expect_sha256(
            obj["ordered_contexts_sha256"],
            "$.ordered_contexts_sha256",
        )
        node_count = expect_int(
            obj["unique_node_artifact_count"],
            "$.unique_node_artifact_count",
            minimum=1,
            maximum=MAX_PROMPT_CONTEXT_INVENTORY_DEPENDENCY_ARTIFACTS,
        )
        node_sha = expect_sha256(
            obj["ordered_unique_node_artifacts_sha256"],
            "$.ordered_unique_node_artifacts_sha256",
        )
        source_count = expect_int(
            obj["unique_source_artifact_count"],
            "$.unique_source_artifact_count",
            minimum=1,
            maximum=MAX_PROMPT_CONTEXT_INVENTORY_DEPENDENCY_ARTIFACTS,
        )
        source_sha = expect_sha256(
            obj["ordered_unique_source_artifacts_sha256"],
            "$.ordered_unique_source_artifacts_sha256",
        )
        dependency_count = expect_int(
            obj["dependency_artifact_count"],
            "$.dependency_artifact_count",
            minimum=1,
            maximum=MAX_PROMPT_CONTEXT_INVENTORY_DEPENDENCY_ARTIFACTS,
        )
        dependency_sha = expect_sha256(
            obj["dependency_closure_sha256"],
            "$.dependency_closure_sha256",
        )
    except SchemaValidationError as exc:
        raise StageCPromptContextInventoryError(str(exc)) from exc
    _require_ref(
        split_ref,
        "diagnostic_split_inventory",
        media_type=DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE,
    )
    try:
        expected = _inventory_value(
            inventory_id=inventory_id,
            created_at=created_at,
            replayed=replayed,
        )
    except StrictJSONError as exc:
        raise StageCPromptContextInventoryError(
            f"prompt-context inventory replay exceeded strict bounds: {exc}"
        ) from exc
    if obj != expected:
        raise StageCPromptContextInventoryError(
            "prompt-context inventory differs from full 480-row replay"
        )
    if inventory_id in {
        item.artifact_id for item in replayed.dependency_artifacts
    }:
        raise StageCPromptContextInventoryError(
            "prompt-context inventory ID collides with its dependency closure"
        )
    if split_ref != replayed.split_inventory.artifact_ref:
        raise StageCPromptContextInventoryError(
            "prompt-context inventory binds the wrong diagnostic split"
        )
    if rows_sha != _row_digest(list(replayed.rows)):
        raise StageCPromptContextInventoryError(
            "prompt-context ordered-row digest drifted"
        )
    if (
        node_count != len(replayed.node_artifacts)
        or node_sha
        != _ref_closure_digest(
            replayed.node_artifacts,
            domain=_NODE_CLOSURE_DOMAIN,
            label="ordered unique prompt-context nodes",
        )
        or source_count != len(replayed.source_artifacts)
        or source_sha
        != _ref_closure_digest(
            replayed.source_artifacts,
            domain=_SOURCE_CLOSURE_DOMAIN,
            label="ordered unique prompt-context sources",
        )
    ):
        raise StageCPromptContextInventoryError(
            "prompt-context node or source dependency closure drifted"
        )
    if dependency_sha != _dependency_digest(replayed.dependency_artifacts):
        raise StageCPromptContextInventoryError(
            "prompt-context aggregate dependency digest drifted"
        )
    if dependency_count != len(replayed.dependency_artifacts):
        raise StageCPromptContextInventoryError(
            "prompt-context aggregate dependency count drifted"
        )
    return StageCPromptContextInventoryArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        inventory_id=inventory_id,
        created_at=created_at,
        diagnostic_split_inventory=split_ref,
        rows=rows,
        ordered_contexts_sha256=rows_sha,
        ordered_node_artifacts=replayed.node_artifacts,
        ordered_source_artifacts=replayed.source_artifacts,
        dependency_artifact_count=dependency_count,
        dependency_closure_sha256=dependency_sha,
        payload=freeze_json(obj),
    )


def build_stagec_prompt_context_inventory(
    *,
    inventory_id: str,
    created_at: str,
    split_inventory: DiagnosticSplitInventoryArtifact,
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...],
) -> StageCPromptContextInventoryArtifact:
    """Build the exact ordered 480-row aggregate and immediately replay it."""

    try:
        inventory_id = expect_machine_id(inventory_id, "inventory_id")
        created_at = expect_timestamp(created_at, "created_at")
    except SchemaValidationError as exc:
        raise StageCPromptContextInventoryError(str(exc)) from exc
    replayed = _replay_aggregate(
        split_inventory=split_inventory,
        replay_bundles=replay_bundles,
    )
    try:
        raw = canonical_json_bytes(
            _inventory_value(
                inventory_id=inventory_id,
                created_at=created_at,
                replayed=replayed,
            )
        )
    except StrictJSONError as exc:
        raise StageCPromptContextInventoryError(
            f"prompt-context inventory exceeds strict JSON bounds: {exc}"
        ) from exc
    return load_stagec_prompt_context_inventory(
        raw,
        split_inventory=replayed.split_inventory,
        replay_bundles=replay_bundles,
    )


def _require_row_projection_types(
    row: StageCPromptContextInventoryRow,
    index: int,
) -> None:
    if (
        type(row) is not StageCPromptContextInventoryRow
        or type(row.execution_ordinal) is not int
        or type(row.case_id) is not str
        or type(row.capture_request) is not ArtifactRef
        or type(row.provenance) is not ArtifactRef
        or type(row.root_node) is not ArtifactRef
        or type(row.ordered_node_closure_sha256) is not str
        or type(row.prompt_sha256) is not str
        or type(row.prompt_byte_length) is not int
    ):
        raise StageCPromptContextInventoryIntegrityError(
            f"inventory.rows[{index}] projections must use exact immutable types"
        )


def replay_stagec_prompt_context_inventory_projection(
    inventory: StageCPromptContextInventoryArtifact,
    *,
    split_inventory: DiagnosticSplitInventoryArtifact,
    replay_bundles: tuple[StageCPromptContextReplayBundle, ...],
) -> StageCPromptContextInventoryArtifact:
    """Return a fresh aggregate after rejecting projected-field forgery."""

    if (
        type(inventory) is not StageCPromptContextInventoryArtifact
        or type(inventory.raw_bytes) is not bytes
        or type(inventory.sha256) is not str
        or type(inventory.byte_length) is not int
        or type(inventory.inventory_id) is not str
        or type(inventory.created_at) is not str
        or type(inventory.diagnostic_split_inventory) is not ArtifactRef
        or type(inventory.rows) is not tuple
        or type(inventory.ordered_contexts_sha256) is not str
        or type(inventory.ordered_node_artifacts) is not tuple
        or any(
            type(item) is not ArtifactRef
            for item in inventory.ordered_node_artifacts
        )
        or type(inventory.ordered_source_artifacts) is not tuple
        or any(
            type(item) is not ArtifactRef
            for item in inventory.ordered_source_artifacts
        )
        or type(inventory.dependency_artifact_count) is not int
        or type(inventory.dependency_closure_sha256) is not str
        or type(inventory.payload) is not MappingProxyType
    ):
        raise StageCPromptContextInventoryIntegrityError(
            "aggregate projections must use exact immutable types"
        )
    for index, row in enumerate(inventory.rows):
        _require_row_projection_types(row, index)
    exact = load_stagec_prompt_context_inventory(
        inventory.raw_bytes,
        split_inventory=split_inventory,
        replay_bundles=replay_bundles,
    )
    if exact != inventory:
        raise StageCPromptContextInventoryIntegrityError(
            "aggregate dataclass differs from full exact-byte replay"
        )
    return exact


__all__ = [
    "MAX_PROMPT_CONTEXT_INVENTORY_DEPENDENCY_ARTIFACTS",
    "STAGEC_PROMPT_CONTEXT_INVENTORY_MEDIA_TYPE",
    "STAGEC_PROMPT_CONTEXT_INVENTORY_SCHEMA",
    "StageCPromptContextInventoryArtifact",
    "StageCPromptContextInventoryError",
    "StageCPromptContextInventoryIntegrityError",
    "StageCPromptContextInventoryRow",
    "StageCPromptContextReplayBundle",
    "build_stagec_prompt_context_inventory",
    "load_stagec_prompt_context_inventory",
    "replay_stagec_prompt_context_inventory_projection",
]
