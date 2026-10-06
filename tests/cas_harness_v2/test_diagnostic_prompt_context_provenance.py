from __future__ import annotations

from dataclasses import dataclass, replace
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cas_harness_v2._strict_json import (  # noqa: E402
    canonical_json_bytes,
    sha256_bytes,
)
from cas_harness_v2._validation import ArtifactRef  # noqa: E402
from cas_harness_v2.diagnostic_prompt_context_provenance import (  # noqa: E402
    COMPOSED,
    LITERAL,
    RETRIEVAL,
    SOURCE,
    STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
    STAGEC_PROMPT_CONTEXT_NODE_SCHEMA,
    STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE,
    STAGEC_PROMPT_CONTEXT_PROVENANCE_SCHEMA,
    STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    SYSTEM,
    USER,
    UTF8_CONCAT,
    StageCPromptContextNodeArtifact,
    StageCPromptContextProvenanceArtifact,
    StageCPromptContextProvenanceError,
    StageCPromptContextProvenanceIntegrityError,
    build_stagec_prompt_concat_node,
    build_stagec_prompt_context_provenance,
    build_stagec_prompt_source_node,
    load_stagec_prompt_context_node,
    load_stagec_prompt_context_provenance,
    replay_stagec_prompt_context_node_projection,
    replay_stagec_prompt_context_provenance_projection,
    resolve_stagec_prompt_context,
)
from cas_harness_v2.diagnostic_study_protocol import (  # noqa: E402
    ADVERSARIAL_PRESENT,
    STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    STAGEC_CAPTURE_REQUEST_SCHEMA,
    StageCCaptureRequestArtifact,
    load_stagec_capture_request,
)


def ref(
    artifact_id: str,
    raw: bytes,
    media_type: str = "application/octet-stream",
) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=artifact_id,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        media_type=media_type,
    )


def ref_value(reference: ArtifactRef) -> dict[str, object]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def mutate(raw: bytes, change) -> bytes:
    value = json.loads(raw)
    change(value)
    return canonical_json_bytes(value)


def make_request(
    *,
    prompt: str = "System policy.\nRetrieved note.\nUser question.",
    artifact_id: str = "stagec-capture-request-001-1",
    case_id: str = "stagec-case-001-1",
) -> StageCCaptureRequestArtifact:
    raw = canonical_json_bytes(
        {
            "schema_version": STAGEC_CAPTURE_REQUEST_SCHEMA,
            "study_id": "stagec-diagnostic-study-001",
            "case_id": case_id,
            "split_id": "stagec-calibration",
            "base_intent_group_id": "intent-group-001",
            "frozen_variant": ADVERSARIAL_PRESENT,
            "frozen_label": ADVERSARIAL_PRESENT,
            "invocation_id": f"stagec-invocation-{case_id[-5:]}",
            "prompt": prompt,
        }
    )
    return load_stagec_capture_request(
        ref(artifact_id, raw, STAGEC_CAPTURE_REQUEST_MEDIA_TYPE),
        raw,
    )


@dataclass(frozen=True)
class ContextFixture:
    request: StageCCaptureRequestArtifact
    nodes: tuple[StageCPromptContextNodeArtifact, ...]
    sources: tuple[tuple[ArtifactRef, bytes], ...]
    provenance: StageCPromptContextProvenanceArtifact


def make_context() -> ContextFixture:
    request = make_request()
    bodies = (
        b"System policy.\n",
        b"Retrieved note.\n",
        b"User question.",
    )
    source_refs = tuple(
        ref(
            f"stagec-prompt-source-{index}",
            body,
            STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
        )
        for index, body in enumerate(bodies, start=1)
    )
    source_nodes = tuple(
        build_stagec_prompt_source_node(
            node_id=f"stagec-prompt-node-{index}",
            declared_origin=origin,
            source_artifact=source_ref,
            source_body=body,
        )
        for index, (origin, source_ref, body) in enumerate(
            zip((SYSTEM, RETRIEVAL, USER), source_refs, bodies),
            start=1,
        )
    )
    root = build_stagec_prompt_concat_node(
        node_id="stagec-prompt-node-root",
        parent_nodes=source_nodes,
        parent_bodies=bodies,
    )
    nodes = (*source_nodes, root)
    sources = tuple(zip(source_refs, bodies))
    provenance = build_stagec_prompt_context_provenance(
        provenance_id="stagec-prompt-context-001-1",
        created_at="2026-08-09T08:00:00Z",
        capture_request=request,
        ordered_nodes=nodes,
        source_bodies=sources,
        root_node=root.artifact_ref,
    )
    return ContextFixture(request, nodes, sources, provenance)


@pytest.fixture(scope="module")
def context() -> ContextFixture:
    return make_context()


def test_exact_roundtrip_recomputes_ordered_multi_origin_graph(
    context: ContextFixture,
) -> None:
    resolved = resolve_stagec_prompt_context(
        ordered_nodes=context.nodes,
        source_bodies=context.sources,
        root_node=context.nodes[-1].artifact_ref,
    )
    assert resolved.root_body == context.request.prompt.encode("utf-8")
    assert resolved.maximum_depth == 2
    assert tuple(node.declared_origin for node in resolved.ordered_nodes) == (
        SYSTEM,
        RETRIEVAL,
        USER,
        COMPOSED,
    )
    assert tuple(node.operation for node in resolved.ordered_nodes) == (
        SOURCE,
        SOURCE,
        SOURCE,
        UTF8_CONCAT,
    )
    loaded = load_stagec_prompt_context_provenance(
        context.provenance.raw_bytes,
        capture_request=context.request,
        ordered_nodes=context.nodes,
        source_bodies=context.sources,
    )
    assert loaded == context.provenance
    assert loaded.payload["authority"]["rendered_channel"] == "USER_CONTENT"
    assert loaded.payload["authority"]["actual_message_count"] == 1
    assert loaded.payload["authority"]["execution_authority"] == "NOT_GRANTED"
    assert loaded.payload["authority"]["scientific_conclusion"] == (
        "NOT_ESTABLISHED"
    )
    assert loaded.payload["boundary"]["worker_rendering_change"] == (
        "NONE_SINGLE_USER_MESSAGE_RETAINED"
    )


def test_single_source_root_is_supported_without_role_coercion() -> None:
    request = make_request(prompt="Exact user content.")
    body = request.prompt.encode("utf-8")
    source_ref = ref(
        "stagec-prompt-source-single",
        body,
        STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    )
    node = build_stagec_prompt_source_node(
        node_id="stagec-prompt-node-single",
        declared_origin=SYSTEM,
        source_artifact=source_ref,
        source_body=body,
    )
    artifact = build_stagec_prompt_context_provenance(
        provenance_id="stagec-prompt-context-single",
        created_at="2026-08-09T08:01:00Z",
        capture_request=request,
        ordered_nodes=(node,),
        source_bodies=((source_ref, body),),
        root_node=node.artifact_ref,
    )
    assert artifact.payload["authority"]["rendered_channel"] == "USER_CONTENT"
    assert node.declared_origin == SYSTEM


@pytest.mark.parametrize(
    "raw",
    [b"\xef\xbb\xbftext", b"bad\x00text", b"\xff"],
)
def test_source_body_rejects_bom_nul_and_invalid_utf8(raw: bytes) -> None:
    source_ref = ref("stagec-prompt-source-invalid", raw, STAGEC_PROMPT_SOURCE_MEDIA_TYPE)
    with pytest.raises(StageCPromptContextProvenanceError):
        build_stagec_prompt_source_node(
            node_id="stagec-prompt-node-invalid",
            declared_origin=USER,
            source_artifact=source_ref,
            source_body=raw,
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.__setitem__("schema_version", "wrong.schema"),
        lambda value: value.__setitem__("operation", "NORMALIZE"),
        lambda value: value.__setitem__("declared_origin", "UNKNOWN"),
        lambda value: value["output"].__setitem__("media_type", "text/plain"),
        lambda value: value["boundary"].__setitem__("execution", "AUTHORIZED"),
    ],
)
def test_node_document_tampering_fails_closed(
    context: ContextFixture,
    change,
) -> None:
    raw = mutate(context.nodes[0].raw_bytes, change)
    reference = ref(
        context.nodes[0].node_id,
        raw,
        STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
    )
    with pytest.raises(StageCPromptContextProvenanceError):
        load_stagec_prompt_context_node(reference, raw)


def test_node_loader_rejects_noncanonical_json_and_wrong_reference(
    context: ContextFixture,
) -> None:
    noncanonical = json.dumps(
        json.loads(context.nodes[0].raw_bytes),
        indent=2,
    ).encode("utf-8")
    with pytest.raises(StageCPromptContextProvenanceError):
        load_stagec_prompt_context_node(
            ref(
                context.nodes[0].node_id,
                noncanonical,
                STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
            ),
            noncanonical,
        )
    with pytest.raises(StageCPromptContextProvenanceError):
        load_stagec_prompt_context_node(
            replace(context.nodes[0].artifact_ref, sha256="0" * 64),
            context.nodes[0].raw_bytes,
        )


def test_graph_rejects_forward_order_orphan_and_parent_reordering(
    context: ContextFixture,
) -> None:
    with pytest.raises(StageCPromptContextProvenanceError, match="cyclic|forward"):
        resolve_stagec_prompt_context(
            ordered_nodes=(context.nodes[-1], *context.nodes[:-1]),
            source_bodies=context.sources,
            root_node=context.nodes[-1].artifact_ref,
        )
    orphan_body = b"unreachable"
    orphan_ref = ref(
        "stagec-prompt-source-orphan",
        orphan_body,
        STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    )
    orphan = build_stagec_prompt_source_node(
        node_id="stagec-prompt-node-orphan",
        declared_origin=LITERAL,
        source_artifact=orphan_ref,
        source_body=orphan_body,
    )
    with pytest.raises(StageCPromptContextProvenanceError, match="orphan"):
        resolve_stagec_prompt_context(
            ordered_nodes=(*context.nodes, orphan),
            source_bodies=(*context.sources, (orphan_ref, orphan_body)),
            root_node=context.nodes[-1].artifact_ref,
        )
    reversed_root = build_stagec_prompt_concat_node(
        node_id="stagec-prompt-node-reversed",
        parent_nodes=tuple(reversed(context.nodes[:-1])),
        parent_bodies=tuple(reversed(tuple(body for _, body in context.sources))),
    )
    with pytest.raises(StageCPromptContextProvenanceError, match="root bytes"):
        build_stagec_prompt_context_provenance(
            provenance_id="stagec-prompt-context-reversed",
            created_at="2026-08-09T08:02:00Z",
            capture_request=context.request,
            ordered_nodes=(*context.nodes[:-1], reversed_root),
            source_bodies=context.sources,
            root_node=reversed_root.artifact_ref,
        )


def test_graph_requires_exact_source_inventory_and_unique_identities(
    context: ContextFixture,
) -> None:
    with pytest.raises(StageCPromptContextProvenanceError, match="exactly every SOURCE"):
        resolve_stagec_prompt_context(
            ordered_nodes=context.nodes,
            source_bodies=context.sources[:-1],
            root_node=context.nodes[-1].artifact_ref,
        )
    extra_body = b"extra source body"
    extra_ref = ref(
        "stagec-prompt-source-extra",
        extra_body,
        STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    )
    with pytest.raises(StageCPromptContextProvenanceError, match="no extras"):
        resolve_stagec_prompt_context(
            ordered_nodes=context.nodes,
            source_bodies=(*context.sources, (extra_ref, extra_body)),
            root_node=context.nodes[-1].artifact_ref,
        )
    body = b"same exact source bytes"
    first_ref = ref("stagec-source-clone-a", body, STAGEC_PROMPT_SOURCE_MEDIA_TYPE)
    second_ref = ref("stagec-source-clone-b", body, STAGEC_PROMPT_SOURCE_MEDIA_TYPE)
    first = build_stagec_prompt_source_node(
        node_id="stagec-node-clone-a",
        declared_origin=USER,
        source_artifact=first_ref,
        source_body=body,
    )
    second = build_stagec_prompt_source_node(
        node_id="stagec-node-clone-b",
        declared_origin=USER,
        source_artifact=second_ref,
        source_body=body,
    )
    with pytest.raises(StageCPromptContextProvenanceError, match="clones"):
        resolve_stagec_prompt_context(
            ordered_nodes=(first, second),
            source_bodies=((first_ref, body), (second_ref, body)),
            root_node=first.artifact_ref,
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.__setitem__("schema_version", "wrong.schema"),
        lambda value: value["authority"].__setitem__(
            "execution_authority", "GRANTED"
        ),
        lambda value: value["authority"].__setitem__(
            "scientific_conclusion", "ESTABLISHED"
        ),
        lambda value: value["boundary"].__setitem__(
            "worker_rendering_change", "MULTI_ROLE"
        ),
        lambda value: value["request_binding"].__setitem__(
            "case_id", "stagec-case-forged"
        ),
        lambda value: value.__setitem__(
            "ordered_node_closure_sha256", "0" * 64
        ),
        lambda value: value["ordered_node_closure"].reverse(),
        lambda value: value["prompt_utf8"].__setitem__("byte_length", 1),
    ],
)
def test_provenance_document_tampering_fails_closed(
    context: ContextFixture,
    change,
) -> None:
    raw = mutate(context.provenance.raw_bytes, change)
    with pytest.raises(StageCPromptContextProvenanceError):
        load_stagec_prompt_context_provenance(
            raw,
            capture_request=context.request,
            ordered_nodes=context.nodes,
            source_bodies=context.sources,
        )


def test_request_and_exact_prompt_bytes_are_replayed(context: ContextFixture) -> None:
    other = make_request(
        prompt=context.request.prompt,
        artifact_id="stagec-capture-request-002-1",
        case_id="stagec-case-002-1",
    )
    with pytest.raises(StageCPromptContextProvenanceError, match="capture_request"):
        load_stagec_prompt_context_provenance(
            context.provenance.raw_bytes,
            capture_request=other,
            ordered_nodes=context.nodes,
            source_bodies=context.sources,
        )
    forged = replace(context.request, study_id="forged-study")
    with pytest.raises(StageCPromptContextProvenanceError, match="exact-byte replay"):
        load_stagec_prompt_context_provenance(
            context.provenance.raw_bytes,
            capture_request=forged,
            ordered_nodes=context.nodes,
            source_bodies=context.sources,
        )


@pytest.mark.parametrize(
    ("request_prompt", "source_body"),
    [("a\nb", b"a\r\nb"), ("caf\N{LATIN SMALL LETTER E WITH ACUTE}", "cafe\u0301".encode())],
)
def test_no_line_ending_or_unicode_normalization(
    request_prompt: str,
    source_body: bytes,
) -> None:
    request = make_request(prompt=request_prompt)
    source_ref = ref(
        "stagec-prompt-source-normalization",
        source_body,
        STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    )
    node = build_stagec_prompt_source_node(
        node_id="stagec-prompt-node-normalization",
        declared_origin=USER,
        source_artifact=source_ref,
        source_body=source_body,
    )
    with pytest.raises(StageCPromptContextProvenanceError, match="root bytes"):
        build_stagec_prompt_context_provenance(
            provenance_id="stagec-prompt-context-normalization",
            created_at="2026-08-09T08:03:00Z",
            capture_request=request,
            ordered_nodes=(node,),
            source_bodies=((source_ref, source_body),),
            root_node=node.artifact_ref,
        )


def test_dependency_identifier_collisions_fail_closed(context: ContextFixture) -> None:
    with pytest.raises(StageCPromptContextProvenanceError, match="collides"):
        build_stagec_prompt_context_provenance(
            provenance_id=context.nodes[0].node_id,
            created_at="2026-08-09T08:04:00Z",
            capture_request=context.request,
            ordered_nodes=context.nodes,
            source_bodies=context.sources,
            root_node=context.nodes[-1].artifact_ref,
        )
    collision_body = b"different collision body"
    collision_ref = ref(
        context.nodes[0].node_id,
        collision_body,
        STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    )
    collision_node = build_stagec_prompt_source_node(
        node_id="stagec-prompt-node-collision",
        declared_origin=SYSTEM,
        source_artifact=collision_ref,
        source_body=collision_body,
    )
    with pytest.raises(StageCPromptContextProvenanceError, match="globally disjoint"):
        resolve_stagec_prompt_context(
            ordered_nodes=(context.nodes[0], collision_node),
            source_bodies=(context.sources[0], (collision_ref, collision_body)),
            root_node=context.nodes[0].artifact_ref,
        )


@pytest.mark.parametrize("collision_role", ["node", "source"])
def test_capture_request_id_cannot_collide_with_graph_dependencies(
    collision_role: str,
) -> None:
    shared_id = "stagec-prompt-shared-id"
    request = make_request(
        prompt="collision prompt",
        artifact_id=shared_id,
    )
    body = request.prompt.encode("utf-8")
    source_ref = ref(
        shared_id if collision_role == "source" else "stagec-prompt-source-safe",
        body,
        STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    )
    node = build_stagec_prompt_source_node(
        node_id=(
            shared_id if collision_role == "node" else "stagec-prompt-node-safe"
        ),
        declared_origin=USER,
        source_artifact=source_ref,
        source_body=body,
    )
    with pytest.raises(StageCPromptContextProvenanceError, match="duplicate"):
        build_stagec_prompt_context_provenance(
            provenance_id="stagec-prompt-context-collision",
            created_at="2026-08-09T08:05:00Z",
            capture_request=request,
            ordered_nodes=(node,),
            source_bodies=((source_ref, body),),
            root_node=node.artifact_ref,
        )


def test_bounds_and_exact_container_types_fail_closed(
    context: ContextFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cas_harness_v2.diagnostic_prompt_context_provenance as module

    with pytest.raises(StageCPromptContextProvenanceError, match="exact tuple"):
        resolve_stagec_prompt_context(
            ordered_nodes=list(context.nodes),  # type: ignore[arg-type]
            source_bodies=context.sources,
            root_node=context.nodes[-1].artifact_ref,
        )
    monkeypatch.setattr(module, "MAX_PROMPT_CONTEXT_NODES", 3)
    with pytest.raises(StageCPromptContextProvenanceError, match="node bound"):
        resolve_stagec_prompt_context(
            ordered_nodes=context.nodes,
            source_bodies=context.sources,
            root_node=context.nodes[-1].artifact_ref,
        )


def test_projection_forgery_is_rejected_and_outputs_are_detached(
    context: ContextFixture,
) -> None:
    assert replay_stagec_prompt_context_node_projection(context.nodes[0]) == (
        context.nodes[0]
    )
    assert replay_stagec_prompt_context_provenance_projection(
        context.provenance,
        capture_request=context.request,
        ordered_nodes=context.nodes,
        source_bodies=context.sources,
    ) == context.provenance
    for forged_node in (
        replace(context.nodes[0], raw_bytes=bytearray(context.nodes[0].raw_bytes)),
        replace(context.nodes[0], payload=dict(context.nodes[0].payload)),
        replace(context.nodes[0], declared_origin=USER),
        replace(context.nodes[0], output_byte_length=True),
        replace(context.nodes[-1], parent_nodes=tuple(reversed(context.nodes[-1].parent_nodes))),
    ):
        with pytest.raises(StageCPromptContextProvenanceIntegrityError):
            replay_stagec_prompt_context_node_projection(forged_node)
    for forged_context in (
        replace(
            context.provenance,
            raw_bytes=bytearray(context.provenance.raw_bytes),
        ),
        replace(context.provenance, payload=dict(context.provenance.payload)),
        replace(context.provenance, prompt_byte_length=True),
        replace(
            context.provenance,
            ordered_node_refs=tuple(reversed(context.provenance.ordered_node_refs)),
        ),
    ):
        with pytest.raises(StageCPromptContextProvenanceIntegrityError):
            replay_stagec_prompt_context_provenance_projection(
                forged_context,
                capture_request=context.request,
                ordered_nodes=context.nodes,
                source_bodies=context.sources,
            )


def test_schema_and_media_types_are_distinct(context: ContextFixture) -> None:
    assert STAGEC_PROMPT_CONTEXT_NODE_SCHEMA != (
        STAGEC_PROMPT_CONTEXT_PROVENANCE_SCHEMA
    )
    assert STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE != (
        STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE
    )
    assert context.nodes[0].artifact_ref.media_type == (
        STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE
    )
    assert context.provenance.artifact_ref.media_type == (
        STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE
    )
