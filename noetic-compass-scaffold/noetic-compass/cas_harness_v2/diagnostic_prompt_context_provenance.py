"""Audit-only prompt-origin provenance for the diagnostic Stage C design.

The current worker receives exactly one user-message string.  This module does
not change that behavior.  It records how exact UTF-8 source bodies were joined
to make that string, while keeping declared origins distinct from actual chat
roles and from execution or scientific authority.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
    expect_enum,
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
from .diagnostic_study_protocol import (
    STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    StageCCaptureRequestArtifact,
    load_stagec_capture_request,
)


STAGEC_PROMPT_CONTEXT_NODE_SCHEMA = (
    "cas_harness_v2.stagec_prompt_context_node.v1"
)
STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-prompt-context-node+json"
)
STAGEC_PROMPT_CONTEXT_PROVENANCE_SCHEMA = (
    "cas_harness_v2.stagec_prompt_context_provenance.v1"
)
STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE = (
    "application/vnd.cas-harness.stagec-prompt-context-provenance+json"
)
STAGEC_PROMPT_SOURCE_MEDIA_TYPE = "text/plain;charset=utf-8"

SOURCE = "SOURCE"
UTF8_CONCAT = "UTF8_CONCAT"
STAGEC_PROMPT_CONTEXT_NODE_OPERATIONS = (SOURCE, UTF8_CONCAT)

SYSTEM = "SYSTEM"
DEVELOPER = "DEVELOPER"
USER = "USER"
RETRIEVAL = "RETRIEVAL"
TOOL = "TOOL"
LITERAL = "LITERAL"
COMPOSED = "COMPOSED"
STAGEC_PROMPT_DECLARED_ORIGINS = (
    SYSTEM,
    DEVELOPER,
    USER,
    RETRIEVAL,
    TOOL,
    LITERAL,
)

MAX_PROMPT_CONTEXT_NODES = 256
MAX_PROMPT_CONTEXT_DEPTH = 32
MAX_PROMPT_CONTEXT_BYTES = 1_000_000
MAX_CONCAT_PARENTS = 64

_NODE_BOUNDARY = {
    "scope": "AUDIT_ONLY_STRUCTURE_ONLY",
    "normalization": "FORBIDDEN_RAW_UTF8_BYTES_ONLY",
    "declared_origin_semantics": (
        "SOURCE_ORIGIN_LABEL_ONLY_NOT_AN_ACTUAL_CHAT_ROLE_OR_AUTHORITY"
    ),
    "execution": "NOT_PERFORMED",
    "semantic_trust": "NOT_CONFERRED",
}

_AUTHORITY = {
    "scope": "STRUCTURE_ONLY",
    "rendered_channel": "USER_CONTENT",
    "actual_message_count": 1,
    "execution_authority": "NOT_GRANTED",
    "authentication": "NOT_PROVIDED",
    "trusted_time": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "scientific_conclusion": "NOT_ESTABLISHED",
    "detector_result": "NOT_CREATED",
    "packet_v2": "FORBIDDEN",
    "claim_promotion": "FORBIDDEN",
    "license": "NOT_GRANTED",
    "product": "NOT_AUTHORIZED",
    "disclosure": "HELD",
}

_CONTEXT_BOUNDARY = {
    "request_schema_change": "NONE_COMPANION_ARTIFACT_ONLY",
    "worker_rendering_change": "NONE_SINGLE_USER_MESSAGE_RETAINED",
    "source_body_retention": "EXTERNAL_EXACT_BYTES_REQUIRED_FOR_FULL_REPLAY",
    "graph_semantics": "SOURCE_AND_ORDERED_UTF8_CONCAT_ONLY",
    "unicode_or_line_ending_normalization": "FORBIDDEN",
    "declared_origin_to_chat_role_coercion": "FORBIDDEN",
    "corpus_freeze": "NOT_ESTABLISHED",
    "preexecution_drc": "NOT_PERFORMED",
}

_NODE_KEYS = {
    "schema_version",
    "node_id",
    "operation",
    "declared_origin",
    "source_artifact",
    "ordered_parent_nodes",
    "output",
    "boundary",
}

_CONTEXT_KEYS = {
    "schema_version",
    "provenance_id",
    "created_at",
    "capture_request",
    "request_binding",
    "root_node",
    "ordered_node_closure",
    "ordered_node_closure_sha256",
    "prompt_utf8",
    "authority",
    "boundary",
}


class StageCPromptContextProvenanceError(ValueError):
    """The prompt-origin graph failed closed."""


class StageCPromptContextProvenanceIntegrityError(
    StageCPromptContextProvenanceError
):
    """Exact bytes, projections, or graph closure disagree."""


def _ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _output_value(body: bytes) -> dict[str, Any]:
    return {
        "sha256": sha256_bytes(body),
        "byte_length": len(body),
        "media_type": STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    }


def _canonical_object(
    raw: bytes | bytearray | memoryview,
    label: str,
) -> tuple[bytes, dict[str, Any]]:
    try:
        snapshot, obj = load_json_object(raw)
    except (StrictJSONError, SchemaValidationError) as exc:
        raise StageCPromptContextProvenanceError(f"{label}: {exc}") from exc
    if snapshot != canonical_json_bytes(obj):
        raise StageCPromptContextProvenanceError(
            f"{label} must use exact canonical JSON bytes"
        )
    return snapshot, obj


def _strict_utf8_body(
    raw: bytes,
    *,
    path: str,
    allow_empty: bool = False,
) -> bytes:
    if type(raw) is not bytes:
        raise StageCPromptContextProvenanceError(f"{path} must be exact bytes")
    if (not raw and not allow_empty) or len(raw) > MAX_PROMPT_CONTEXT_BYTES:
        raise StageCPromptContextProvenanceError(
            f"{path} is empty or exceeds the prompt byte bound"
        )
    if raw.startswith(b"\xef\xbb\xbf"):
        raise StageCPromptContextProvenanceError(f"{path} must not contain a UTF-8 BOM")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise StageCPromptContextProvenanceError(
            f"{path} is not strict UTF-8"
        ) from exc
    if "\x00" in text or any(0xD800 <= ord(char) <= 0xDFFF for char in text):
        raise StageCPromptContextProvenanceError(
            f"{path} contains a forbidden NUL or surrogate"
        )
    return raw


def _require_ref(reference: Any, path: str, *, media_type: str | None = None) -> ArtifactRef:
    if type(reference) is not ArtifactRef:
        raise StageCPromptContextProvenanceError(
            f"{path} must be an exact ArtifactRef"
        )
    if media_type is not None and reference.media_type != media_type:
        raise StageCPromptContextProvenanceError(
            f"{path} must retain media type {media_type!r}"
        )
    return reference


def _require_unique_refs(
    references: Sequence[ArtifactRef],
    *,
    path: str,
    content_unique: bool,
) -> None:
    ids = [item.artifact_id for item in references]
    if len(ids) != len(set(ids)):
        raise StageCPromptContextProvenanceError(
            f"{path} contains duplicate artifact identifiers"
        )
    if content_unique:
        contents = [(item.sha256, item.byte_length) for item in references]
        if len(contents) != len(set(contents)):
            raise StageCPromptContextProvenanceError(
                f"{path} clones one content identity under multiple identifiers"
            )


def _closure_digest(references: Sequence[ArtifactRef]) -> str:
    return canonical_sha256(
        {
            "domain": "cas_harness_v2.stagec_prompt_context_ordered_closure.v1",
            "ordered_node_refs": [_ref_value(item) for item in references],
        }
    )


@dataclass(frozen=True, slots=True)
class StageCPromptContextNodeArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    node_id: str
    operation: str
    declared_origin: str
    source_artifact: ArtifactRef | None
    parent_nodes: tuple[ArtifactRef, ...]
    output_sha256: str
    output_byte_length: int
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.node_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
        )


@dataclass(frozen=True, slots=True)
class ResolvedStageCPromptContext:
    ordered_nodes: tuple[StageCPromptContextNodeArtifact, ...]
    source_bodies: tuple[tuple[ArtifactRef, bytes], ...]
    output_bodies: Mapping[str, bytes]
    root_node: StageCPromptContextNodeArtifact
    root_body: bytes
    maximum_depth: int


@dataclass(frozen=True, slots=True)
class StageCPromptContextProvenanceArtifact:
    raw_bytes: bytes
    sha256: str
    byte_length: int
    provenance_id: str
    created_at: str
    capture_request: ArtifactRef
    root_node: ArtifactRef
    ordered_node_refs: tuple[ArtifactRef, ...]
    ordered_node_closure_sha256: str
    prompt_sha256: str
    prompt_byte_length: int
    payload: Mapping[str, Any]

    @property
    def artifact_ref(self) -> ArtifactRef:
        return ArtifactRef(
            artifact_id=self.provenance_id,
            sha256=self.sha256,
            byte_length=self.byte_length,
            media_type=STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE,
        )


def load_stagec_prompt_context_node(
    reference: ArtifactRef,
    raw: bytes | bytearray | memoryview,
) -> StageCPromptContextNodeArtifact:
    """Strict-load one graph node without resolving its external bodies."""

    reference = _require_ref(
        reference,
        "node reference",
        media_type=STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
    )
    snapshot, obj = _canonical_object(raw, "Stage C prompt-context node")
    if not reference.verify_bytes(snapshot):
        raise StageCPromptContextProvenanceError(
            "node reference does not bind the exact canonical bytes"
        )
    try:
        expect_keys(obj, required=_NODE_KEYS, path="$")
        if obj["schema_version"] != STAGEC_PROMPT_CONTEXT_NODE_SCHEMA:
            raise SchemaValidationError("wrong prompt-context node schema")
        node_id = expect_machine_id(obj["node_id"], "$.node_id")
        operation = expect_enum(
            obj["operation"], set(STAGEC_PROMPT_CONTEXT_NODE_OPERATIONS), "$.operation"
        )
        origin = expect_string(obj["declared_origin"], "$.declared_origin", maximum=32)
        parents_value = expect_list(
            obj["ordered_parent_nodes"],
            "$.ordered_parent_nodes",
            nonempty=False,
        )
        parents = tuple(
            parse_artifact_ref(item, f"$.ordered_parent_nodes[{index}]")
            for index, item in enumerate(parents_value)
        )
        output = expect_object(obj["output"], "$.output")
        expect_keys(
            output,
            required={"sha256", "byte_length", "media_type"},
            path="$.output",
        )
        output_sha = expect_sha256(output["sha256"], "$.output.sha256")
        output_length = expect_int(
            output["byte_length"],
            "$.output.byte_length",
            minimum=1,
            maximum=MAX_PROMPT_CONTEXT_BYTES,
        )
        output_media = expect_string(
            output["media_type"], "$.output.media_type", maximum=128
        )
    except SchemaValidationError as exc:
        raise StageCPromptContextProvenanceError(str(exc)) from exc
    if reference.artifact_id != node_id:
        raise StageCPromptContextProvenanceError(
            "node artifact ID does not equal its node_id"
        )
    if output_media != STAGEC_PROMPT_SOURCE_MEDIA_TYPE:
        raise StageCPromptContextProvenanceError("node output media type drifted")
    if obj["boundary"] != _NODE_BOUNDARY:
        raise StageCPromptContextProvenanceError("node authority boundary drifted")
    for index, parent in enumerate(parents):
        _require_ref(
            parent,
            f"ordered_parent_nodes[{index}]",
            media_type=STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
        )
    _require_unique_refs(parents, path="ordered_parent_nodes", content_unique=True)
    source_value = obj["source_artifact"]
    source: ArtifactRef | None
    if operation == SOURCE:
        if origin not in STAGEC_PROMPT_DECLARED_ORIGINS:
            raise StageCPromptContextProvenanceError(
                "SOURCE node declared_origin is outside the closed catalog"
            )
        if parents:
            raise StageCPromptContextProvenanceError(
                "SOURCE node cannot have parent nodes"
            )
        try:
            source = parse_artifact_ref(source_value, "$.source_artifact")
        except SchemaValidationError as exc:
            raise StageCPromptContextProvenanceError(str(exc)) from exc
        _require_ref(
            source,
            "source_artifact",
            media_type=STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
        )
        if (source.sha256, source.byte_length) != (output_sha, output_length):
            raise StageCPromptContextProvenanceError(
                "SOURCE output identity must exactly equal its source artifact"
            )
    else:
        if origin != COMPOSED:
            raise StageCPromptContextProvenanceError(
                "UTF8_CONCAT declared_origin must equal COMPOSED"
            )
        if source_value is not None:
            raise StageCPromptContextProvenanceError(
                "UTF8_CONCAT cannot carry a source artifact"
            )
        if len(parents) < 2 or len(parents) > MAX_CONCAT_PARENTS:
            raise StageCPromptContextProvenanceError(
                "UTF8_CONCAT parent cardinality is outside the closed bound"
            )
        source = None
    return StageCPromptContextNodeArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        node_id=node_id,
        operation=operation,
        declared_origin=origin,
        source_artifact=source,
        parent_nodes=parents,
        output_sha256=output_sha,
        output_byte_length=output_length,
        payload=freeze_json(obj),
    )


def build_stagec_prompt_source_node(
    *,
    node_id: str,
    declared_origin: str,
    source_artifact: ArtifactRef,
    source_body: bytes,
) -> StageCPromptContextNodeArtifact:
    """Build one exact source node from a separately retained UTF-8 body."""

    try:
        node_id = expect_machine_id(node_id, "node_id")
        declared_origin = expect_enum(
            declared_origin, set(STAGEC_PROMPT_DECLARED_ORIGINS), "declared_origin"
        )
    except SchemaValidationError as exc:
        raise StageCPromptContextProvenanceError(str(exc)) from exc
    source_artifact = _require_ref(
        source_artifact,
        "source_artifact",
        media_type=STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    )
    body = _strict_utf8_body(source_body, path="source_body")
    if not source_artifact.verify_bytes(body):
        raise StageCPromptContextProvenanceError(
            "source_artifact does not bind source_body"
        )
    raw = canonical_json_bytes(
        {
            "schema_version": STAGEC_PROMPT_CONTEXT_NODE_SCHEMA,
            "node_id": node_id,
            "operation": SOURCE,
            "declared_origin": declared_origin,
            "source_artifact": _ref_value(source_artifact),
            "ordered_parent_nodes": [],
            "output": _output_value(body),
            "boundary": dict(_NODE_BOUNDARY),
        }
    )
    reference = ArtifactRef(
        artifact_id=node_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
    )
    return load_stagec_prompt_context_node(reference, raw)


def build_stagec_prompt_concat_node(
    *,
    node_id: str,
    parent_nodes: tuple[StageCPromptContextNodeArtifact, ...],
    parent_bodies: tuple[bytes, ...],
) -> StageCPromptContextNodeArtifact:
    """Build one ordered raw-UTF8 concatenation node."""

    try:
        node_id = expect_machine_id(node_id, "node_id")
    except SchemaValidationError as exc:
        raise StageCPromptContextProvenanceError(str(exc)) from exc
    if type(parent_nodes) is not tuple or type(parent_bodies) is not tuple:
        raise StageCPromptContextProvenanceError(
            "parent_nodes and parent_bodies must be exact tuples"
        )
    if len(parent_nodes) != len(parent_bodies):
        raise StageCPromptContextProvenanceError(
            "parent_nodes and parent_bodies cardinality differs"
        )
    if len(parent_nodes) < 2 or len(parent_nodes) > MAX_CONCAT_PARENTS:
        raise StageCPromptContextProvenanceError(
            "UTF8_CONCAT parent cardinality is outside the closed bound"
        )
    replayed: list[StageCPromptContextNodeArtifact] = []
    bodies: list[bytes] = []
    for index, (parent, body) in enumerate(zip(parent_nodes, parent_bodies)):
        parent = replay_stagec_prompt_context_node_projection(parent)
        body = _strict_utf8_body(body, path=f"parent_bodies[{index}]")
        if (sha256_bytes(body), len(body)) != (
            parent.output_sha256,
            parent.output_byte_length,
        ):
            raise StageCPromptContextProvenanceError(
                f"parent_bodies[{index}] does not bind its parent output"
            )
        replayed.append(parent)
        bodies.append(body)
    refs = tuple(item.artifact_ref for item in replayed)
    _require_unique_refs(refs, path="parent_nodes", content_unique=True)
    output = b"".join(bodies)
    _strict_utf8_body(output, path="concatenated output")
    raw = canonical_json_bytes(
        {
            "schema_version": STAGEC_PROMPT_CONTEXT_NODE_SCHEMA,
            "node_id": node_id,
            "operation": UTF8_CONCAT,
            "declared_origin": COMPOSED,
            "source_artifact": None,
            "ordered_parent_nodes": [_ref_value(item) for item in refs],
            "output": _output_value(output),
            "boundary": dict(_NODE_BOUNDARY),
        }
    )
    reference = ArtifactRef(
        artifact_id=node_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
    )
    return load_stagec_prompt_context_node(reference, raw)


def replay_stagec_prompt_context_node_projection(
    node: StageCPromptContextNodeArtifact,
) -> StageCPromptContextNodeArtifact:
    """Return a fresh node after rejecting dataclass projection forgery."""

    if type(node) is not StageCPromptContextNodeArtifact:
        raise StageCPromptContextProvenanceIntegrityError(
            "node must be an exact StageCPromptContextNodeArtifact"
        )
    if (
        type(node.raw_bytes) is not bytes
        or type(node.sha256) is not str
        or type(node.byte_length) is not int
        or type(node.node_id) is not str
        or type(node.operation) is not str
        or type(node.declared_origin) is not str
        or (
            node.source_artifact is not None
            and type(node.source_artifact) is not ArtifactRef
        )
        or type(node.parent_nodes) is not tuple
        or any(type(item) is not ArtifactRef for item in node.parent_nodes)
        or type(node.output_sha256) is not str
        or type(node.output_byte_length) is not int
        or type(node.payload) is not MappingProxyType
    ):
        raise StageCPromptContextProvenanceIntegrityError(
            "node projections must use exact immutable types"
        )
    exact = load_stagec_prompt_context_node(node.artifact_ref, node.raw_bytes)
    if exact != node:
        raise StageCPromptContextProvenanceIntegrityError(
            "node dataclass differs from exact-byte replay"
        )
    return exact


def resolve_stagec_prompt_context(
    *,
    ordered_nodes: tuple[StageCPromptContextNodeArtifact, ...],
    source_bodies: tuple[tuple[ArtifactRef, bytes], ...],
    root_node: ArtifactRef,
) -> ResolvedStageCPromptContext:
    """Resolve and recompute one closed, topologically ordered prompt DAG."""

    if type(ordered_nodes) is not tuple or not ordered_nodes:
        raise StageCPromptContextProvenanceError(
            "ordered_nodes must be one nonempty exact tuple"
        )
    if len(ordered_nodes) > MAX_PROMPT_CONTEXT_NODES:
        raise StageCPromptContextProvenanceError("prompt graph exceeds the node bound")
    root_node = _require_ref(
        root_node,
        "root_node",
        media_type=STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
    )
    nodes = tuple(replay_stagec_prompt_context_node_projection(item) for item in ordered_nodes)
    node_refs = tuple(item.artifact_ref for item in nodes)
    _require_unique_refs(node_refs, path="ordered_nodes", content_unique=True)
    by_id = {item.node_id: item for item in nodes}
    if root_node not in node_refs:
        raise StageCPromptContextProvenanceError(
            "root_node is not one exact member of ordered_nodes"
        )
    if type(source_bodies) is not tuple:
        raise StageCPromptContextProvenanceError(
            "source_bodies must be an exact tuple"
        )
    source_map: dict[str, tuple[ArtifactRef, bytes]] = {}
    for index, pair in enumerate(source_bodies):
        if type(pair) is not tuple or len(pair) != 2:
            raise StageCPromptContextProvenanceError(
                f"source_bodies[{index}] must be an exact (ArtifactRef, bytes) tuple"
            )
        reference = _require_ref(
            pair[0],
            f"source_bodies[{index}].reference",
            media_type=STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
        )
        body = _strict_utf8_body(pair[1], path=f"source_bodies[{index}].body")
        if not reference.verify_bytes(body):
            raise StageCPromptContextProvenanceError(
                f"source_bodies[{index}] reference does not bind its body"
            )
        if reference.artifact_id in source_map:
            raise StageCPromptContextProvenanceError(
                "source_bodies contains a duplicate artifact identifier"
            )
        source_map[reference.artifact_id] = (reference, body)
    _require_unique_refs(
        tuple(item[0] for item in source_map.values()),
        path="source_bodies",
        content_unique=True,
    )
    required_sources = tuple(
        item.source_artifact for item in nodes if item.operation == SOURCE
    )
    required_ids = {item.artifact_id for item in required_sources if item is not None}
    if set(source_map) != required_ids:
        raise StageCPromptContextProvenanceError(
            "source_bodies must contain exactly every SOURCE artifact and no extras"
        )
    if set(source_map) & set(by_id):
        raise StageCPromptContextProvenanceError(
            "source and node artifact identifiers must be globally disjoint"
        )

    outputs: dict[str, bytes] = {}
    depths: dict[str, int] = {}
    seen: set[str] = set()
    for index, node in enumerate(nodes):
        if node.operation == SOURCE:
            assert node.source_artifact is not None
            reference, body = source_map[node.source_artifact.artifact_id]
            if reference != node.source_artifact:
                raise StageCPromptContextProvenanceError(
                    f"ordered_nodes[{index}] source reference drifted"
                )
            output = body
            depth = 1
        else:
            parent_ids = [item.artifact_id for item in node.parent_nodes]
            if any(parent_id not in seen for parent_id in parent_ids):
                raise StageCPromptContextProvenanceError(
                    "prompt graph is cyclic, forward-referencing, or not topologically ordered"
                )
            for parent_ref in node.parent_nodes:
                if by_id[parent_ref.artifact_id].artifact_ref != parent_ref:
                    raise StageCPromptContextProvenanceError(
                        "parent node reference differs from the exact graph member"
                    )
            output = b"".join(outputs[parent_id] for parent_id in parent_ids)
            depth = 1 + max(depths[parent_id] for parent_id in parent_ids)
        _strict_utf8_body(output, path=f"ordered_nodes[{index}].output")
        if (sha256_bytes(output), len(output)) != (
            node.output_sha256,
            node.output_byte_length,
        ):
            raise StageCPromptContextProvenanceError(
                f"ordered_nodes[{index}] output identity does not recompute"
            )
        if depth > MAX_PROMPT_CONTEXT_DEPTH:
            raise StageCPromptContextProvenanceError(
                "prompt graph exceeds the derivation-depth bound"
            )
        outputs[node.node_id] = output
        depths[node.node_id] = depth
        seen.add(node.node_id)

    reachable: set[str] = set()
    stack = [root_node.artifact_id]
    while stack:
        node_id = stack.pop()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        stack.extend(parent.artifact_id for parent in by_id[node_id].parent_nodes)
    if reachable != set(by_id):
        raise StageCPromptContextProvenanceError(
            "prompt graph contains orphan or unreachable nodes"
        )
    exact_root = by_id[root_node.artifact_id]
    return ResolvedStageCPromptContext(
        ordered_nodes=nodes,
        source_bodies=tuple(source_map.values()),
        output_bodies=MappingProxyType(dict(outputs)),
        root_node=exact_root,
        root_body=outputs[exact_root.node_id],
        maximum_depth=max(depths.values()),
    )


def _request_binding(request: StageCCaptureRequestArtifact) -> dict[str, Any]:
    return {
        "study_id": request.study_id,
        "case_id": request.case_id,
        "split_id": request.split_id,
        "base_intent_group_id": request.base_intent_group_id,
        "frozen_variant": request.frozen_variant,
        "frozen_label": request.frozen_label,
        "invocation_id": request.invocation_id,
    }


def _fresh_request(request: StageCCaptureRequestArtifact) -> StageCCaptureRequestArtifact:
    if type(request) is not StageCCaptureRequestArtifact:
        raise StageCPromptContextProvenanceError(
            "capture_request must be an exact StageCCaptureRequestArtifact"
        )
    if type(request.raw_bytes) is not bytes or type(request.payload) is not MappingProxyType:
        raise StageCPromptContextProvenanceError(
            "capture_request projections must use exact immutable types"
        )
    exact = load_stagec_capture_request(request.artifact_ref, request.raw_bytes)
    if exact != request:
        raise StageCPromptContextProvenanceError(
            "capture_request differs from exact-byte replay"
        )
    return exact


def _context_value(
    *,
    provenance_id: str,
    created_at: str,
    request: StageCCaptureRequestArtifact,
    resolved: ResolvedStageCPromptContext,
) -> dict[str, Any]:
    refs = tuple(item.artifact_ref for item in resolved.ordered_nodes)
    prompt = request.prompt.encode("utf-8", errors="strict")
    return {
        "schema_version": STAGEC_PROMPT_CONTEXT_PROVENANCE_SCHEMA,
        "provenance_id": provenance_id,
        "created_at": created_at,
        "capture_request": _ref_value(request.artifact_ref),
        "request_binding": _request_binding(request),
        "root_node": _ref_value(resolved.root_node.artifact_ref),
        "ordered_node_closure": [_ref_value(item) for item in refs],
        "ordered_node_closure_sha256": _closure_digest(refs),
        "prompt_utf8": _output_value(prompt),
        "authority": dict(_AUTHORITY),
        "boundary": dict(_CONTEXT_BOUNDARY),
    }


def load_stagec_prompt_context_provenance(
    raw: bytes | bytearray | memoryview,
    *,
    capture_request: StageCCaptureRequestArtifact,
    ordered_nodes: tuple[StageCPromptContextNodeArtifact, ...],
    source_bodies: tuple[tuple[ArtifactRef, bytes], ...],
) -> StageCPromptContextProvenanceArtifact:
    """Strict-load and fully recompute one prompt-context companion."""

    request = _fresh_request(capture_request)
    snapshot, obj = _canonical_object(raw, "Stage C prompt-context provenance")
    try:
        expect_keys(obj, required=_CONTEXT_KEYS, path="$")
        if obj["schema_version"] != STAGEC_PROMPT_CONTEXT_PROVENANCE_SCHEMA:
            raise SchemaValidationError("wrong prompt-context provenance schema")
        provenance_id = expect_machine_id(obj["provenance_id"], "$.provenance_id")
        created_at = expect_timestamp(obj["created_at"], "$.created_at")
        request_ref = parse_artifact_ref(obj["capture_request"], "$.capture_request")
        root_ref = parse_artifact_ref(obj["root_node"], "$.root_node")
        closure_values = expect_list(
            obj["ordered_node_closure"], "$.ordered_node_closure"
        )
        closure_refs = tuple(
            parse_artifact_ref(item, f"$.ordered_node_closure[{index}]")
            for index, item in enumerate(closure_values)
        )
        closure_sha = expect_sha256(
            obj["ordered_node_closure_sha256"],
            "$.ordered_node_closure_sha256",
        )
        prompt_value = expect_object(obj["prompt_utf8"], "$.prompt_utf8")
        expect_keys(
            prompt_value,
            required={"sha256", "byte_length", "media_type"},
            path="$.prompt_utf8",
        )
        prompt_sha = expect_sha256(prompt_value["sha256"], "$.prompt_utf8.sha256")
        prompt_length = expect_int(
            prompt_value["byte_length"],
            "$.prompt_utf8.byte_length",
            minimum=1,
            maximum=MAX_PROMPT_CONTEXT_BYTES,
        )
    except SchemaValidationError as exc:
        raise StageCPromptContextProvenanceError(str(exc)) from exc
    _require_ref(
        request_ref,
        "capture_request",
        media_type=STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    )
    _require_ref(
        root_ref,
        "root_node",
        media_type=STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
    )
    if request_ref != request.artifact_ref:
        raise StageCPromptContextProvenanceError(
            "provenance capture_request does not equal the exact request"
        )
    if obj["request_binding"] != _request_binding(request):
        raise StageCPromptContextProvenanceError(
            "provenance request association drifted"
        )
    if obj["authority"] != _AUTHORITY or obj["boundary"] != _CONTEXT_BOUNDARY:
        raise StageCPromptContextProvenanceError(
            "prompt-context authority or boundary drifted"
        )
    if prompt_value["media_type"] != STAGEC_PROMPT_SOURCE_MEDIA_TYPE:
        raise StageCPromptContextProvenanceError("prompt UTF-8 media type drifted")
    if len(closure_refs) > MAX_PROMPT_CONTEXT_NODES:
        raise StageCPromptContextProvenanceError("node closure exceeds the bound")
    _require_unique_refs(
        closure_refs,
        path="ordered_node_closure",
        content_unique=True,
    )
    supplied_refs = tuple(item.artifact_ref for item in ordered_nodes)
    if closure_refs != supplied_refs or closure_sha != _closure_digest(closure_refs):
        raise StageCPromptContextProvenanceError(
            "ordered node closure or its domain-separated digest drifted"
        )
    resolved = resolve_stagec_prompt_context(
        ordered_nodes=ordered_nodes,
        source_bodies=source_bodies,
        root_node=root_ref,
    )
    prompt = request.prompt.encode("utf-8", errors="strict")
    if resolved.root_body != prompt:
        raise StageCPromptContextProvenanceError(
            "resolved root bytes do not exactly equal capture_request.prompt UTF-8 bytes"
        )
    if (prompt_sha, prompt_length) != (sha256_bytes(prompt), len(prompt)):
        raise StageCPromptContextProvenanceError(
            "prompt UTF-8 identity does not match the exact capture request"
        )
    expected = _context_value(
        provenance_id=provenance_id,
        created_at=created_at,
        request=request,
        resolved=resolved,
    )
    if obj != expected:
        raise StageCPromptContextProvenanceError(
            "prompt-context provenance differs from full dependency replay"
        )
    dependency_refs = (
        request.artifact_ref,
        *(item.artifact_ref for item in resolved.ordered_nodes),
        *(item for item, _ in resolved.source_bodies),
    )
    _require_unique_refs(
        dependency_refs,
        path="prompt-context dependency closure",
        content_unique=True,
    )
    if provenance_id in {item.artifact_id for item in dependency_refs}:
        raise StageCPromptContextProvenanceError(
            "provenance identifier collides with its dependency closure"
        )
    return StageCPromptContextProvenanceArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        provenance_id=provenance_id,
        created_at=created_at,
        capture_request=request.artifact_ref,
        root_node=root_ref,
        ordered_node_refs=closure_refs,
        ordered_node_closure_sha256=closure_sha,
        prompt_sha256=prompt_sha,
        prompt_byte_length=prompt_length,
        payload=freeze_json(obj),
    )


def build_stagec_prompt_context_provenance(
    *,
    provenance_id: str,
    created_at: str,
    capture_request: StageCCaptureRequestArtifact,
    ordered_nodes: tuple[StageCPromptContextNodeArtifact, ...],
    source_bodies: tuple[tuple[ArtifactRef, bytes], ...],
    root_node: ArtifactRef,
) -> StageCPromptContextProvenanceArtifact:
    """Build the audit companion after fully resolving its exact DAG."""

    try:
        provenance_id = expect_machine_id(provenance_id, "provenance_id")
        created_at = expect_timestamp(created_at, "created_at")
    except SchemaValidationError as exc:
        raise StageCPromptContextProvenanceError(str(exc)) from exc
    request = _fresh_request(capture_request)
    resolved = resolve_stagec_prompt_context(
        ordered_nodes=ordered_nodes,
        source_bodies=source_bodies,
        root_node=root_node,
    )
    raw = canonical_json_bytes(
        _context_value(
            provenance_id=provenance_id,
            created_at=created_at,
            request=request,
            resolved=resolved,
        )
    )
    return load_stagec_prompt_context_provenance(
        raw,
        capture_request=request,
        ordered_nodes=resolved.ordered_nodes,
        source_bodies=resolved.source_bodies,
    )


def replay_stagec_prompt_context_provenance_projection(
    provenance: StageCPromptContextProvenanceArtifact,
    *,
    capture_request: StageCCaptureRequestArtifact,
    ordered_nodes: tuple[StageCPromptContextNodeArtifact, ...],
    source_bodies: tuple[tuple[ArtifactRef, bytes], ...],
) -> StageCPromptContextProvenanceArtifact:
    """Return a fresh companion after rejecting every projected-field drift."""

    if type(provenance) is not StageCPromptContextProvenanceArtifact:
        raise StageCPromptContextProvenanceIntegrityError(
            "provenance must be an exact StageCPromptContextProvenanceArtifact"
        )
    if (
        type(provenance.raw_bytes) is not bytes
        or type(provenance.sha256) is not str
        or type(provenance.byte_length) is not int
        or type(provenance.provenance_id) is not str
        or type(provenance.created_at) is not str
        or type(provenance.capture_request) is not ArtifactRef
        or type(provenance.root_node) is not ArtifactRef
        or type(provenance.ordered_node_refs) is not tuple
        or any(
            type(item) is not ArtifactRef
            for item in provenance.ordered_node_refs
        )
        or type(provenance.ordered_node_closure_sha256) is not str
        or type(provenance.prompt_sha256) is not str
        or type(provenance.prompt_byte_length) is not int
        or type(provenance.payload) is not MappingProxyType
    ):
        raise StageCPromptContextProvenanceIntegrityError(
            "provenance projections must use exact immutable types"
        )
    exact = load_stagec_prompt_context_provenance(
        provenance.raw_bytes,
        capture_request=capture_request,
        ordered_nodes=ordered_nodes,
        source_bodies=source_bodies,
    )
    if exact != provenance:
        raise StageCPromptContextProvenanceIntegrityError(
            "provenance dataclass differs from full exact-byte replay"
        )
    return exact


__all__ = [
    "COMPOSED",
    "DEVELOPER",
    "LITERAL",
    "MAX_PROMPT_CONTEXT_BYTES",
    "MAX_PROMPT_CONTEXT_DEPTH",
    "MAX_PROMPT_CONTEXT_NODES",
    "RETRIEVAL",
    "SOURCE",
    "STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE",
    "STAGEC_PROMPT_CONTEXT_NODE_OPERATIONS",
    "STAGEC_PROMPT_CONTEXT_NODE_SCHEMA",
    "STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE",
    "STAGEC_PROMPT_CONTEXT_PROVENANCE_SCHEMA",
    "STAGEC_PROMPT_DECLARED_ORIGINS",
    "STAGEC_PROMPT_SOURCE_MEDIA_TYPE",
    "SYSTEM",
    "StageCPromptContextNodeArtifact",
    "StageCPromptContextProvenanceArtifact",
    "StageCPromptContextProvenanceError",
    "StageCPromptContextProvenanceIntegrityError",
    "TOOL",
    "USER",
    "UTF8_CONCAT",
    "ResolvedStageCPromptContext",
    "build_stagec_prompt_concat_node",
    "build_stagec_prompt_context_provenance",
    "build_stagec_prompt_source_node",
    "load_stagec_prompt_context_node",
    "load_stagec_prompt_context_provenance",
    "replay_stagec_prompt_context_node_projection",
    "replay_stagec_prompt_context_provenance_projection",
    "resolve_stagec_prompt_context",
]
