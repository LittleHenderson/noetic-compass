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
from cas_harness_v2.diagnostic_prompt_context_inventory import (  # noqa: E402
    STAGEC_PROMPT_CONTEXT_INVENTORY_MEDIA_TYPE,
    STAGEC_PROMPT_CONTEXT_INVENTORY_SCHEMA,
    StageCPromptContextInventoryArtifact,
    StageCPromptContextInventoryError,
    StageCPromptContextInventoryIntegrityError,
    StageCPromptContextReplayBundle,
    build_stagec_prompt_context_inventory,
    load_stagec_prompt_context_inventory,
    replay_stagec_prompt_context_inventory_projection,
)
from cas_harness_v2.diagnostic_prompt_context_provenance import (  # noqa: E402
    STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
    STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE,
    STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
    USER,
    build_stagec_prompt_context_provenance,
    build_stagec_prompt_concat_node,
    build_stagec_prompt_source_node,
)
from cas_harness_v2.diagnostic_study_protocol import (  # noqa: E402
    DIAGNOSTIC_CASE_COUNT,
    DIAGNOSTIC_GROUP_COUNT,
    DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE,
    DIAGNOSTIC_VARIANT_ROLES,
    STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    STAGEC_CAPTURE_REQUEST_SCHEMA,
    DiagnosticSplitInventoryArtifact,
    StageCCaptureRequestArtifact,
    build_diagnostic_split_inventory,
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


def mutate(raw: bytes, change) -> bytes:
    value = json.loads(raw)
    change(value)
    return canonical_json_bytes(value)


def make_capture_request(
    *,
    group: int,
    variant_number: int,
    variant: str,
    prompt: str | None = None,
) -> StageCCaptureRequestArtifact:
    prompt = prompt or f"Frozen shared prompt for group {group}."
    raw = canonical_json_bytes(
        {
            "schema_version": STAGEC_CAPTURE_REQUEST_SCHEMA,
            "study_id": "stagec-diagnostic-study-001",
            "case_id": f"stagec-case-{group:03d}-{variant_number}",
            "split_id": "stagec-calibration",
            "base_intent_group_id": f"intent-group-{group:03d}",
            "frozen_variant": variant,
            "frozen_label": variant,
            "invocation_id": f"stagec-invocation-{group:03d}-{variant_number}",
            "prompt": prompt,
        }
    )
    reference = ref(
        f"stagec-capture-request-{group:03d}-{variant_number}",
        raw,
        STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    )
    return load_stagec_capture_request(reference, raw)


@dataclass(frozen=True)
class InventoryFixture:
    split: DiagnosticSplitInventoryArtifact
    bundles: tuple[StageCPromptContextReplayBundle, ...]
    aggregate: StageCPromptContextInventoryArtifact


def make_inventory_fixture() -> InventoryFixture:
    requests = tuple(
        make_capture_request(
            group=group,
            variant_number=variant_number,
            variant=variant,
        )
        for group in range(1, DIAGNOSTIC_GROUP_COUNT + 1)
        for variant_number, variant in enumerate(DIAGNOSTIC_VARIANT_ROLES, start=1)
    )
    split = build_diagnostic_split_inventory(
        inventory_id="stagec-diagnostic-split-inventory-001",
        capture_requests=requests,
    )
    group_nodes = {}
    group_sources = {}
    for group in range(1, DIAGNOSTIC_GROUP_COUNT + 1):
        body = f"Frozen shared prompt for group {group}.".encode("utf-8")
        source_ref = ref(
            f"stagec-prompt-source-{group:03d}",
            body,
            STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
        )
        node = build_stagec_prompt_source_node(
            node_id=f"stagec-prompt-node-{group:03d}",
            declared_origin=USER,
            source_artifact=source_ref,
            source_body=body,
        )
        group_sources[group] = (source_ref, body)
        group_nodes[group] = node
    bundles = []
    for ordinal, request in enumerate(requests, start=1):
        group = ((ordinal - 1) // len(DIAGNOSTIC_VARIANT_ROLES)) + 1
        node = group_nodes[group]
        source = group_sources[group]
        provenance = build_stagec_prompt_context_provenance(
            provenance_id=f"stagec-prompt-context-{ordinal:03d}",
            created_at="2026-08-09T09:00:00Z",
            capture_request=request,
            ordered_nodes=(node,),
            source_bodies=(source,),
            root_node=node.artifact_ref,
        )
        bundles.append(
            StageCPromptContextReplayBundle(
                provenance=provenance,
                ordered_nodes=(node,),
                source_bodies=(source,),
            )
        )
    frozen_bundles = tuple(bundles)
    aggregate = build_stagec_prompt_context_inventory(
        inventory_id="stagec-prompt-context-inventory-001",
        created_at="2026-08-09T09:01:00Z",
        split_inventory=split,
        replay_bundles=frozen_bundles,
    )
    return InventoryFixture(split, frozen_bundles, aggregate)


@pytest.fixture(scope="module")
def inventory() -> InventoryFixture:
    return make_inventory_fixture()


def test_exact_480_row_roundtrip_and_shared_dependency_reuse(
    inventory: InventoryFixture,
) -> None:
    assert len(inventory.aggregate.rows) == DIAGNOSTIC_CASE_COUNT
    assert len(inventory.aggregate.ordered_node_artifacts) == DIAGNOSTIC_GROUP_COUNT
    assert len(inventory.aggregate.ordered_source_artifacts) == DIAGNOSTIC_GROUP_COUNT
    assert inventory.aggregate.rows[0].execution_ordinal == 1
    assert inventory.aggregate.rows[-1].execution_ordinal == DIAGNOSTIC_CASE_COUNT
    assert inventory.aggregate.rows[0].capture_request == (
        inventory.split.capture_requests[0].artifact_ref
    )
    loaded = load_stagec_prompt_context_inventory(
        inventory.aggregate.raw_bytes,
        split_inventory=inventory.split,
        replay_bundles=inventory.bundles,
    )
    assert loaded == inventory.aggregate
    assert loaded.payload["study_binding"] == {
        "study_id": inventory.split.study_id,
        "split_id": inventory.split.split_id,
        "group_count": DIAGNOSTIC_GROUP_COUNT,
        "case_count": DIAGNOSTIC_CASE_COUNT,
        "ordered_case_inventory_sha256": (
            inventory.split.ordered_case_inventory_sha256
        ),
    }
    assert loaded.payload["authority"]["corpus_freeze"] == "NOT_ESTABLISHED"
    assert loaded.payload["authority"]["execution_authority"] == "NOT_GRANTED"
    assert loaded.payload["boundary"]["existing_schema_changes"] == (
        "NONE_ADDITIVE_COMPANION_ONLY"
    )


@pytest.mark.parametrize("count_delta", [-1, 1])
def test_exact_480_bundle_count_is_required(
    inventory: InventoryFixture,
    count_delta: int,
) -> None:
    bundles = (
        inventory.bundles[:-1]
        if count_delta < 0
        else (*inventory.bundles, inventory.bundles[-1])
    )
    with pytest.raises(StageCPromptContextInventoryError, match="exactly 480"):
        load_stagec_prompt_context_inventory(
            inventory.aggregate.raw_bytes,
            split_inventory=inventory.split,
            replay_bundles=bundles,
        )


def test_reordered_duplicated_and_cross_request_bundles_fail_closed(
    inventory: InventoryFixture,
) -> None:
    mutations = (
        (inventory.bundles[1], inventory.bundles[0], *inventory.bundles[2:]),
        (inventory.bundles[0], inventory.bundles[0], *inventory.bundles[2:]),
        (*inventory.bundles[:-2], inventory.bundles[-1], inventory.bundles[-2]),
    )
    for bundles in mutations:
        with pytest.raises(StageCPromptContextInventoryError, match="row"):
            load_stagec_prompt_context_inventory(
                inventory.aggregate.raw_bytes,
                split_inventory=inventory.split,
                replay_bundles=bundles,
            )


def test_missing_and_mutated_graph_dependencies_fail_closed(
    inventory: InventoryFixture,
) -> None:
    first = inventory.bundles[0]
    missing = replace(first, source_bodies=())
    forged_node = replace(first.ordered_nodes[0], declared_origin="SYSTEM")
    mutated = replace(first, ordered_nodes=(forged_node,))
    for bundle in (missing, mutated):
        bundles = (bundle, *inventory.bundles[1:])
        with pytest.raises(StageCPromptContextInventoryError, match="row 1"):
            load_stagec_prompt_context_inventory(
                inventory.aggregate.raw_bytes,
                split_inventory=inventory.split,
                replay_bundles=bundles,
            )


def _replacement_bundle(
    inventory: InventoryFixture,
    *,
    row_index: int,
    source_id: str,
    node_id: str,
) -> StageCPromptContextReplayBundle:
    request = inventory.split.capture_requests[row_index]
    body = request.prompt.encode("utf-8")
    source_ref = ref(source_id, body, STAGEC_PROMPT_SOURCE_MEDIA_TYPE)
    node = build_stagec_prompt_source_node(
        node_id=node_id,
        declared_origin=USER,
        source_artifact=source_ref,
        source_body=body,
    )
    provenance = build_stagec_prompt_context_provenance(
        provenance_id=f"stagec-prompt-context-replacement-{row_index}",
        created_at="2026-08-09T09:02:00Z",
        capture_request=request,
        ordered_nodes=(node,),
        source_bodies=((source_ref, body),),
        root_node=node.artifact_ref,
    )
    return StageCPromptContextReplayBundle(
        provenance=provenance,
        ordered_nodes=(node,),
        source_bodies=((source_ref, body),),
    )


def test_cross_row_dependency_clones_and_id_conflicts_fail_closed(
    inventory: InventoryFixture,
) -> None:
    clone = _replacement_bundle(
        inventory,
        row_index=1,
        source_id="stagec-prompt-source-cloned-content",
        node_id="stagec-prompt-node-cloned-content",
    )
    conflict = _replacement_bundle(
        inventory,
        row_index=3,
        source_id=inventory.bundles[0].source_bodies[0][0].artifact_id,
        node_id="stagec-prompt-node-conflicting-id",
    )
    for index, bundle in ((1, clone), (3, conflict)):
        bundles = list(inventory.bundles)
        bundles[index] = bundle
        with pytest.raises(
            StageCPromptContextInventoryError,
            match="cloned|conflicting",
        ):
            build_stagec_prompt_context_inventory(
                inventory_id="stagec-prompt-context-inventory-forged",
                created_at="2026-08-09T09:03:00Z",
                split_inventory=inventory.split,
                replay_bundles=tuple(bundles),
            )


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.__setitem__("schema_version", "wrong.schema"),
        lambda value: value["authority"].__setitem__(
            "execution_authority", "GRANTED"
        ),
        lambda value: value["authority"].__setitem__(
            "corpus_freeze", "ESTABLISHED"
        ),
        lambda value: value["boundary"].__setitem__(
            "runtime_admission", "PERFORMED"
        ),
        lambda value: value.__setitem__(
            "ordered_contexts_sha256", "0" * 64
        ),
        lambda value: value.__setitem__(
            "dependency_closure_sha256", "0" * 64
        ),
        lambda value: value.__setitem__("dependency_artifact_count", 1),
        lambda value: value["ordered_contexts"].__setitem__(
            0, value["ordered_contexts"][1]
        ),
        lambda value: value.__setitem__(
            "ordered_unique_node_artifacts_sha256", "0" * 64
        ),
        lambda value: value["study_binding"].__setitem__("case_count", 479),
    ],
)
def test_aggregate_document_tampering_fails_closed(
    inventory: InventoryFixture,
    change,
) -> None:
    raw = mutate(inventory.aggregate.raw_bytes, change)
    with pytest.raises(StageCPromptContextInventoryError):
        load_stagec_prompt_context_inventory(
            raw,
            split_inventory=inventory.split,
            replay_bundles=inventory.bundles,
        )


def test_noncanonical_json_and_wrong_split_fail_closed(
    inventory: InventoryFixture,
) -> None:
    noncanonical = json.dumps(
        json.loads(inventory.aggregate.raw_bytes),
        indent=2,
    ).encode("utf-8")
    with pytest.raises(StageCPromptContextInventoryError, match="canonical"):
        load_stagec_prompt_context_inventory(
            noncanonical,
            split_inventory=inventory.split,
            replay_bundles=inventory.bundles,
        )
    forged_split = replace(
        inventory.split,
        cases=(
            replace(inventory.split.cases[0], execution_ordinal=True),
            *inventory.split.cases[1:],
        ),
    )
    with pytest.raises(StageCPromptContextInventoryIntegrityError):
        load_stagec_prompt_context_inventory(
            inventory.aggregate.raw_bytes,
            split_inventory=forged_split,
            replay_bundles=inventory.bundles,
        )


def test_aggregate_identifier_cannot_collide_with_dependencies(
    inventory: InventoryFixture,
) -> None:
    with pytest.raises(StageCPromptContextInventoryError, match="collides"):
        build_stagec_prompt_context_inventory(
            inventory_id=inventory.split.inventory_id,
            created_at="2026-08-09T09:04:00Z",
            split_inventory=inventory.split,
            replay_bundles=inventory.bundles,
        )


def test_dependency_bound_is_enforced(
    inventory: InventoryFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import cas_harness_v2.diagnostic_prompt_context_inventory as module

    monkeypatch.setattr(
        module,
        "MAX_PROMPT_CONTEXT_INVENTORY_DEPENDENCY_ARTIFACTS",
        1,
    )
    with pytest.raises(StageCPromptContextInventoryError, match="v1 bound"):
        load_stagec_prompt_context_inventory(
            inventory.aggregate.raw_bytes,
            split_inventory=inventory.split,
            replay_bundles=inventory.bundles,
        )


def test_compact_aggregate_supports_4321_exact_dependencies() -> None:
    requests = []
    for group in range(1, DIAGNOSTIC_GROUP_COUNT + 1):
        for variant_number, variant in enumerate(
            DIAGNOSTIC_VARIANT_ROLES,
            start=1,
        ):
            ordinal = (group - 1) * len(DIAGNOSTIC_VARIANT_ROLES) + variant_number
            prompt = f"A:{ordinal}|B:{ordinal}|C:{ordinal}"
            requests.append(
                make_capture_request(
                    group=group,
                    variant_number=variant_number,
                    variant=variant,
                    prompt=prompt,
                )
            )
    split = build_diagnostic_split_inventory(
        inventory_id="stagec-diagnostic-split-inventory-compactness",
        capture_requests=tuple(requests),
    )
    bundles = []
    for ordinal, request in enumerate(requests, start=1):
        bodies = (
            f"A:{ordinal}|".encode(),
            f"B:{ordinal}|".encode(),
            f"C:{ordinal}".encode(),
        )
        sources = tuple(
            ref(
                f"stagec-compact-source-{ordinal:03d}-{part}",
                body,
                STAGEC_PROMPT_SOURCE_MEDIA_TYPE,
            )
            for part, body in enumerate(bodies, start=1)
        )
        nodes = tuple(
            build_stagec_prompt_source_node(
                node_id=f"stagec-compact-node-{ordinal:03d}-{part}",
                declared_origin=USER,
                source_artifact=source,
                source_body=body,
            )
            for part, (source, body) in enumerate(
                zip(sources, bodies),
                start=1,
            )
        )
        root = build_stagec_prompt_concat_node(
            node_id=f"stagec-compact-root-{ordinal:03d}",
            parent_nodes=nodes,
            parent_bodies=bodies,
        )
        ordered_nodes = (*nodes, root)
        source_bodies = tuple(zip(sources, bodies))
        provenance = build_stagec_prompt_context_provenance(
            provenance_id=f"stagec-compact-context-{ordinal:03d}",
            created_at="2026-08-09T09:05:00Z",
            capture_request=request,
            ordered_nodes=ordered_nodes,
            source_bodies=source_bodies,
            root_node=root.artifact_ref,
        )
        bundles.append(
            StageCPromptContextReplayBundle(
                provenance=provenance,
                ordered_nodes=ordered_nodes,
                source_bodies=source_bodies,
            )
        )
    frozen_bundles = tuple(bundles)
    aggregate = build_stagec_prompt_context_inventory(
        inventory_id="stagec-prompt-context-inventory-compactness",
        created_at="2026-08-09T09:06:00Z",
        split_inventory=split,
        replay_bundles=frozen_bundles,
    )
    assert aggregate.dependency_artifact_count == 4_321
    assert len(aggregate.ordered_node_artifacts) == 1_920
    assert len(aggregate.ordered_source_artifacts) == 1_440
    assert len(aggregate.raw_bytes) < 2_000_000
    assert load_stagec_prompt_context_inventory(
        aggregate.raw_bytes,
        split_inventory=split,
        replay_bundles=frozen_bundles,
    ) == aggregate


def test_projection_forgery_is_rejected_and_fresh_replay_returned(
    inventory: InventoryFixture,
) -> None:
    exact = replay_stagec_prompt_context_inventory_projection(
        inventory.aggregate,
        split_inventory=inventory.split,
        replay_bundles=inventory.bundles,
    )
    assert exact == inventory.aggregate
    assert exact is not inventory.aggregate
    forged_values = (
        replace(
            inventory.aggregate,
            raw_bytes=bytearray(inventory.aggregate.raw_bytes),
        ),
        replace(inventory.aggregate, payload=dict(inventory.aggregate.payload)),
        replace(inventory.aggregate, byte_length=True),
        replace(
            inventory.aggregate,
            rows=(
                replace(inventory.aggregate.rows[0], execution_ordinal=True),
                *inventory.aggregate.rows[1:],
            ),
        ),
        replace(
            inventory.aggregate,
            ordered_node_artifacts=tuple(
                reversed(inventory.aggregate.ordered_node_artifacts)
            ),
        ),
    )
    for forged in forged_values:
        with pytest.raises(StageCPromptContextInventoryIntegrityError):
            replay_stagec_prompt_context_inventory_projection(
                forged,
                split_inventory=inventory.split,
                replay_bundles=inventory.bundles,
            )


def test_schema_and_media_types_are_distinct(inventory: InventoryFixture) -> None:
    assert STAGEC_PROMPT_CONTEXT_INVENTORY_SCHEMA != (
        inventory.bundles[0].provenance.payload["schema_version"]
    )
    assert STAGEC_PROMPT_CONTEXT_INVENTORY_MEDIA_TYPE not in {
        STAGEC_PROMPT_CONTEXT_PROVENANCE_MEDIA_TYPE,
        STAGEC_PROMPT_CONTEXT_NODE_MEDIA_TYPE,
        DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE,
    }
    assert inventory.aggregate.artifact_ref.media_type == (
        STAGEC_PROMPT_CONTEXT_INVENTORY_MEDIA_TYPE
    )
