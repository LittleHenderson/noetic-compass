from __future__ import annotations

import builtins
from dataclasses import FrozenInstanceError
import gc
import inspect
import json
from pathlib import Path
import socket
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cas_harness_v2._strict_json import canonical_json_bytes  # noqa: E402
from cas_harness_v2._validation import ArtifactRef  # noqa: E402
from cas_harness_v2.diagnostic_stagec_historical_source_inventory import (  # noqa: E402
    HISTORICAL_W0_RAW_ROW_COUNT,
    HISTORICAL_W0_SOURCE_BYTE_LENGTH,
    HISTORICAL_W0_SOURCE_SCHEMA,
    HISTORICAL_W0_SOURCE_SHA256,
)
from cas_harness_v2.diagnostic_stagec_prerequisite_admission import (  # noqa: E402
    CORPUS_ADJUDICATION_MEDIA_TYPE,
    CORPUS_ROWS_MEDIA_TYPE,
    CORPUS_SPLIT_ASSIGNMENT_MEDIA_TYPE,
    CORPUS_SURFACE_BUNDLE_MEDIA_TYPE,
)
import cas_harness_v2.diagnostic_stagec_corpus_authoring_scaffold as sut  # noqa: E402
from cas_harness_v2.diagnostic_stagec_corpus_authoring_scaffold import (  # noqa: E402
    CONFIRMATORY,
    DIAGNOSTIC_CALIBRATION,
    HELD_OUT_REPLICATION,
    STAGEC_AUTHORING_CARRIERS,
    STAGEC_AUTHORING_GROUP_COUNT,
    STAGEC_AUTHORING_REVIEW_SLOTS,
    STAGEC_AUTHORING_ROW_COUNT,
    STAGEC_AUTHORING_SPLIT_GROUP_COUNTS,
    STAGEC_AUTHORING_VARIANT_COUNT,
    STAGEC_CORPUS_AUTHORING_SCAFFOLD_ID,
    STAGEC_CORPUS_AUTHORING_SCAFFOLD_MEDIA_TYPE,
    STAGEC_CORPUS_AUTHORING_SCAFFOLD_SCHEMA,
    StageCCorpusAuthoringScaffoldArtifact,
    StageCCorpusAuthoringScaffoldError,
    StageCCorpusDraftGroupInput,
    StageCCorpusDraftReviewInput,
    StageCCorpusDraftRowInput,
    build_stagec_corpus_authoring_scaffold,
    derive_stagec_corpus_authoring_subject_sha256,
    load_stagec_corpus_authoring_scaffold,
)
from cas_harness_v2.diagnostic_study_protocol import (  # noqa: E402
    ADVERSARIAL_PRESENT,
    CLEAN_ABSENT,
    CLEAN_NULL_ABSENT,
    DIAGNOSTIC_VARIANT_ROLES,
)


FROZEN_EMPTY_SHA256 = (
    "50303F23895C2403F9CEB54917E5D5CBECBE8FE5B26DFE342A7F6409D0EEB438"
)
FROZEN_EMPTY_BYTE_LENGTH = 318_956


def _group(
    ordinal: int,
    *,
    base_intent: str | None = None,
    template_family: str | None = None,
    prompt_prefix: str | None = None,
    row_order: tuple[str, ...] = DIAGNOSTIC_VARIANT_ROLES,
    carriers: tuple[str, ...] | None = None,
) -> StageCCorpusDraftGroupInput:
    prompt_prefix = prompt_prefix or f"New Stage C synthetic prompt {ordinal:03d}"
    carriers = carriers or tuple(
        STAGEC_AUTHORING_CARRIERS[(ordinal + index) % 4]
        for index in range(3)
    )
    return StageCCorpusDraftGroupInput(
        group_ordinal=ordinal,
        base_intent_utf8=(
            base_intent or f"New Stage C synthetic base intent {ordinal:03d}."
        ),
        taxonomy=f"taxonomy-{ordinal % 5}",
        payload_family=f"payload-family-{ordinal % 7}",
        template_family=template_family or f"template-family-{ordinal:03d}",
        rows=tuple(
            StageCCorpusDraftRowInput(
                variant_role=variant,
                prompt_utf8=f"{prompt_prefix} {variant}.",
                carrier=carriers[index],
            )
            for index, variant in enumerate(row_order)
        ),
    )


def _review(
    ordinal: int,
    variant: str,
    slot: str,
    *,
    reviewer_id: str | None = None,
    decision: str = "APPROVE_DRAFT",
) -> StageCCorpusDraftReviewInput:
    return StageCCorpusDraftReviewInput(
        group_ordinal=ordinal,
        variant_role=variant,
        review_slot=slot,
        reviewer_id=reviewer_id or f"reviewer-{slot.lower()}",
        decision=decision,
        rationale_code="structural-review-recorded",
    )


def _full_inputs() -> tuple[
    tuple[StageCCorpusDraftGroupInput, ...],
    tuple[StageCCorpusDraftReviewInput, ...],
]:
    groups = tuple(_group(ordinal) for ordinal in range(1, 321))
    reviews = tuple(
        _review(ordinal, variant, slot)
        for ordinal in range(1, 321)
        for variant in DIAGNOSTIC_VARIANT_ROLES
        for slot in STAGEC_AUTHORING_REVIEW_SLOTS
    )
    return groups, reviews


def _mutate(raw: bytes, change) -> bytes:
    value = json.loads(raw)
    change(value)
    return canonical_json_bytes(value)


def _mapping_proxy_backing(value) -> dict:
    dictionaries = [item for item in gc.get_referents(value) if type(item) is dict]
    assert len(dictionaries) == 1
    return dictionaries[0]


def _scalar_paths(value, path=()):
    if type(value) is dict:
        for key, item in value.items():
            yield from _scalar_paths(item, (*path, key))
    elif type(value) is list:
        for index, item in enumerate(value):
            yield from _scalar_paths(item, (*path, index))
    elif type(value) in (int, bool):
        yield path, value


def _replace_path(value, path, replacement) -> None:
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement


def _reachable_mutable_payload_backings(value) -> tuple[object, ...]:
    found: list[object] = []
    seen: set[int] = set()

    def visit(node) -> None:
        identity = id(node)
        if identity in seen:
            return
        seen.add(identity)
        for referent in gc.get_referents(node):
            if type(referent) is type:
                continue
            if type(referent) in (dict, list, set, bytearray):
                found.append(referent)
            elif isinstance(referent, tuple):
                visit(referent)

    visit(value)
    return tuple(found)


def _authority_forgery() -> tuple[bytes, dict, object, tuple[int, ...]]:
    baseline = build_stagec_corpus_authoring_scaffold()
    value = json.loads(baseline.raw_bytes)
    value["classification"]["lifecycle"] = "FROZEN"
    value["classification"]["authority"] = "AUTHORITY"
    value["classification"]["admission"] = "ADMITTED"
    value["progress"]["status"] = "FROZEN"
    value["progress"]["admitted_group_count"] = 320
    value["progress"]["admitted_row_count"] = 960
    value["draft_inventory"]["counts_status"] = "FROZEN"
    value["draft_inventory"]["contingency_table_status"] = "ESTABLISHED"
    value["boundary"]["stagec_corpus"] = "FROZEN"
    value["boundary"]["stagec_corpus_freeze"] = "FROZEN"
    value["boundary"]["double_adjudication_authority"] = "ESTABLISHED"
    value["boundary"]["admitted_group_count"] = 320
    value["boundary"]["admitted_row_count"] = 960
    value["boundary"]["execution_authority"] = "GRANTED"
    raw = canonical_json_bytes(value)
    payload = sut._immutable_json_value(value)
    counts = (0, 0, 0, 0, 0, 320, 960)
    return raw, value, payload, counts


def _slot_forgery(
    raw: bytes,
    payload: object,
    counts: tuple[int, ...],
) -> StageCCorpusAuthoringScaffoldArtifact:
    forged = object.__new__(StageCCorpusAuthoringScaffoldArtifact)
    for name, value in (
        ("raw_bytes", raw),
        ("sha256", sut.sha256_bytes(raw)),
        ("byte_length", len(raw)),
        ("scaffold_id", STAGEC_CORPUS_AUTHORING_SCAFFOLD_ID),
        ("authored_group_count", counts[0]),
        ("authored_row_count", counts[1]),
        ("recorded_review_count", counts[2]),
        ("two_review_row_count", counts[3]),
        ("two_review_approve_row_count", counts[4]),
        ("admitted_group_count", counts[5]),
        ("admitted_row_count", counts[6]),
        ("payload", payload),
    ):
        object.__setattr__(forged, name, value)
    return forged


def test_empty_scaffold_has_frozen_deterministic_identity_and_exact_slots() -> None:
    artifact = build_stagec_corpus_authoring_scaffold()
    assert artifact.scaffold_id == STAGEC_CORPUS_AUTHORING_SCAFFOLD_ID
    assert artifact.sha256 == FROZEN_EMPTY_SHA256
    assert artifact.byte_length == FROZEN_EMPTY_BYTE_LENGTH
    assert artifact.raw_bytes == canonical_json_bytes(json.loads(artifact.raw_bytes))
    assert artifact.artifact_ref.media_type == STAGEC_CORPUS_AUTHORING_SCAFFOLD_MEDIA_TYPE
    assert artifact.artifact_ref.verify_bytes(artifact.raw_bytes)
    assert len(artifact.payload["groups"]) == STAGEC_AUTHORING_GROUP_COUNT
    assert sum(len(group["rows"]) for group in artifact.payload["groups"]) == 960
    assert artifact.payload["recorded_reviews"] == ()
    assert build_stagec_corpus_authoring_scaffold() == artifact


def test_scaffold_contract_is_exact_320_by_3_and_whole_group_160_80_80() -> None:
    payload = build_stagec_corpus_authoring_scaffold().payload
    assert payload["schema_version"] == STAGEC_CORPUS_AUTHORING_SCAFFOLD_SCHEMA
    assert payload["contract"]["required_group_count"] == 320
    assert payload["contract"]["required_row_count"] == 960
    assert payload["contract"]["variant_count"] == 3
    assert payload["contract"]["variant_roles"] == DIAGNOSTIC_VARIANT_ROLES
    assert payload["contract"]["group_assignment"] == (
        "DISJOINT_WHOLE_BASE_INTENT_GROUPS"
    )
    assert dict(payload["contract"]["split_group_counts"]) == {
        DIAGNOSTIC_CALIBRATION: 160,
        CONFIRMATORY: 80,
        HELD_OUT_REPLICATION: 80,
    }
    split_counts: dict[str, int] = {}
    row_ordinals: list[int] = []
    case_ids: list[str] = []
    for group in payload["groups"]:
        split_counts[group["split_role"]] = split_counts.get(group["split_role"], 0) + 1
        assert tuple(row["variant_role"] for row in group["rows"]) == (
            ADVERSARIAL_PRESENT,
            CLEAN_ABSENT,
            CLEAN_NULL_ABSENT,
        )
        row_ordinals.extend(row["row_ordinal"] for row in group["rows"])
        case_ids.extend(row["case_id"] for row in group["rows"])
    assert split_counts == dict(STAGEC_AUTHORING_SPLIT_GROUP_COUNTS)
    assert row_ordinals == list(range(1, 961))
    assert len(case_ids) == len(set(case_ids)) == 960


def test_historical_w0_is_only_fixed_aggregate_context_and_never_imported() -> None:
    artifact = build_stagec_corpus_authoring_scaffold()
    assert tuple(inspect.signature(build_stagec_corpus_authoring_scaffold).parameters) == (
        "authored_groups",
        "reviews",
    )
    assert artifact.payload["historical_w0_boundary"] == {
        "schema_version": HISTORICAL_W0_SOURCE_SCHEMA,
        "sha256": HISTORICAL_W0_SOURCE_SHA256,
        "byte_length": HISTORICAL_W0_SOURCE_BYTE_LENGTH,
        "historical_raw_row_count": HISTORICAL_W0_RAW_ROW_COUNT,
        "role": "AGGREGATE_GAP_CONTEXT_ONLY",
        "prompt_body_access": "NOT_PERFORMED",
        "prompt_overlap_check": "NOT_PERFORMED",
        "row_import_count": 0,
        "stagec_evidence_row_count": 0,
        "evidence_relabeling": "FORBIDDEN",
    }
    assert artifact.payload["classification"]["content_status"] == "SYNTHETIC"
    assert artifact.payload["classification"]["evidence_relabeling"] == "FORBIDDEN"


def test_one_authored_group_and_structural_reviews_bind_exact_content() -> None:
    group = _group(1)
    reviews = (
        _review(1, ADVERSARIAL_PRESENT, "B", decision="REVISE_DRAFT"),
        _review(1, CLEAN_ABSENT, "A"),
        _review(1, ADVERSARIAL_PRESENT, "A"),
    )
    artifact = build_stagec_corpus_authoring_scaffold(
        authored_groups=(group,), reviews=reviews
    )
    progress = artifact.payload["progress"]
    assert progress["authored_group_count"] == 1
    assert progress["authored_row_count"] == 3
    assert progress["recorded_review_count"] == 3
    assert progress["unreviewed_row_count"] == 958
    assert progress["single_review_row_count"] == 1
    assert progress["two_review_row_count"] == 1
    assert progress["two_review_agreement_row_count"] == 0
    assert progress["two_review_disagreement_row_count"] == 1
    subject_sha256 = derive_stagec_corpus_authoring_subject_sha256(
        group, group.rows[0]
    )
    first_row = artifact.payload["groups"][0]["rows"][0]
    assert first_row["authoring_subject_sha256"] == subject_sha256
    assert artifact.payload["recorded_reviews"][0] == (
        1,
        "A",
        "reviewer-a",
        "APPROVE_DRAFT",
        "structural-review-recorded",
        subject_sha256,
    )
    assert artifact.payload["recorded_reviews"][1][1] == "B"
    assert artifact.payload["recorded_reviews"][1][5] == subject_sha256
    assert artifact.payload["groups"][1]["authoring"]["status"] == "PENDING"


def test_input_order_does_not_change_canonical_group_or_review_order() -> None:
    groups = (_group(240), _group(1), _group(161))
    reviews = (
        _review(161, CLEAN_NULL_ABSENT, "B"),
        _review(1, ADVERSARIAL_PRESENT, "A"),
        _review(161, CLEAN_NULL_ABSENT, "A"),
    )
    left = build_stagec_corpus_authoring_scaffold(
        authored_groups=groups, reviews=reviews
    )
    right = build_stagec_corpus_authoring_scaffold(
        authored_groups=tuple(reversed(groups)), reviews=tuple(reversed(reviews))
    )
    assert left == right


def test_full_320_by_3_and_two_review_draft_still_admits_zero() -> None:
    groups, reviews = _full_inputs()
    artifact = build_stagec_corpus_authoring_scaffold(
        authored_groups=groups, reviews=reviews
    )
    progress = artifact.payload["progress"]
    assert artifact.authored_group_count == 320
    assert artifact.authored_row_count == 960
    assert artifact.recorded_review_count == 1_920
    assert artifact.two_review_row_count == 960
    assert artifact.two_review_approve_row_count == 960
    assert progress["pending_group_count"] == 0
    assert progress["pending_row_count"] == 0
    assert progress["two_review_disagreement_row_count"] == 0
    assert artifact.admitted_group_count == 0
    assert artifact.admitted_row_count == 0
    assert progress["admitted_group_count"] == 0
    assert progress["admitted_row_count"] == 0
    assert artifact.payload["boundary"] == {
        "stagec_corpus": "DRAFT",
        "stagec_corpus_freeze": "NOT_ESTABLISHED",
        "double_adjudication_authority": "NOT_ESTABLISHED",
        "reviewer_identity_authentication": "NOT_PROVIDED",
        "admitted_group_count": 0,
        "admitted_row_count": 0,
        "execution_authority": "NOT_GRANTED",
        "scientific_conclusion": "NOT_ESTABLISHED",
        "license": "NOT LICENSED",
        "disclosure": "HELD",
    }
    assert artifact.payload["draft_inventory"]["carrier_row_counts"] == {
        carrier: 240 for carrier in STAGEC_AUTHORING_CARRIERS
    }
    assert artifact.byte_length < 2_000_000
    assert load_stagec_corpus_authoring_scaffold(artifact.raw_bytes) == artifact


def test_authoring_media_type_cannot_pose_as_an_admission_dependency() -> None:
    assert STAGEC_CORPUS_AUTHORING_SCAFFOLD_MEDIA_TYPE not in {
        CORPUS_ROWS_MEDIA_TYPE,
        CORPUS_ADJUDICATION_MEDIA_TYPE,
        CORPUS_SPLIT_ASSIGNMENT_MEDIA_TYPE,
        CORPUS_SURFACE_BUNDLE_MEDIA_TYPE,
    }
    payload = build_stagec_corpus_authoring_scaffold().payload
    assert payload["classification"] == {
        "lifecycle": "DRAFT",
        "content_status": "SYNTHETIC",
        "authority": "NON_AUTHORITY",
        "scope": "AUTHORING_WORKSHEET_ONLY",
        "admission": "NOT_ESTABLISHED",
        "evidence_relabeling": "FORBIDDEN",
    }


def test_authority_inspection_maps_are_recursively_immutable() -> None:
    with pytest.raises(TypeError):
        sut._CLASSIFICATION["authority"] = "GRANTED"
    with pytest.raises(TypeError):
        sut._HISTORICAL_W0_BOUNDARY["row_import_count"] = 960
    with pytest.raises(TypeError):
        sut._CONTRACT["required_row_count"] = 1
    with pytest.raises(TypeError):
        sut._CONTRACT["split_group_counts"][DIAGNOSTIC_CALIBRATION] = 1
    with pytest.raises(TypeError):
        sut._CONTRACT["variant_roles"][0] = "FORGED"
    with pytest.raises(TypeError):
        sut._DRAFT_LEAKAGE_CONTROLS["semantic_equivalence_review"] = "PASS"
    with pytest.raises(TypeError):
        sut._BOUNDARY["admitted_row_count"] = 960


def test_authority_backing_mutation_and_global_rebinding_cannot_promote_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = _group(1)
    reviews = (
        _review(1, ADVERSARIAL_PRESENT, "A"),
        _review(1, ADVERSARIAL_PRESENT, "B"),
    )
    baseline = build_stagec_corpus_authoring_scaffold(
        authored_groups=(group,), reviews=reviews
    )

    classification = _mapping_proxy_backing(sut._CLASSIFICATION)
    historical = _mapping_proxy_backing(sut._HISTORICAL_W0_BOUNDARY)
    contract = _mapping_proxy_backing(sut._CONTRACT)
    split_counts = _mapping_proxy_backing(contract["split_group_counts"])
    leakage = _mapping_proxy_backing(sut._DRAFT_LEAKAGE_CONTROLS)
    boundary = _mapping_proxy_backing(sut._BOUNDARY)
    monkeypatch.setitem(classification, "authority", "GRANTED")
    monkeypatch.setitem(classification, "admission", "ADMITTED")
    monkeypatch.setitem(historical, "row_import_count", 2_560)
    monkeypatch.setitem(historical, "stagec_evidence_row_count", 960)
    monkeypatch.setitem(contract, "required_row_count", 1)
    monkeypatch.setitem(contract, "variant_roles", ("FORGED",))
    monkeypatch.setitem(split_counts, DIAGNOSTIC_CALIBRATION, 1)
    monkeypatch.setitem(leakage, "semantic_equivalence_review", "PASS")
    monkeypatch.setitem(boundary, "stagec_corpus_freeze", "FROZEN")
    monkeypatch.setitem(boundary, "admitted_row_count", 960)
    monkeypatch.setitem(boundary, "execution_authority", "GRANTED")

    forged_mapping = {"authority": "GRANTED", "admitted_row_count": 960}
    for name in (
        "_CLASSIFICATION",
        "_HISTORICAL_W0_BOUNDARY",
        "_CONTRACT",
        "_DRAFT_LEAKAGE_CONTROLS",
        "_BOUNDARY",
        "_VARIANT_SLUGS",
    ):
        monkeypatch.setattr(sut, name, forged_mapping)
    for name in (
        "_CLASSIFICATION_ITEMS",
        "_HISTORICAL_W0_BOUNDARY_ITEMS",
        "_CONTRACT_SCALAR_ITEMS",
        "_CONTRACT_VARIANT_ROLES",
        "_CONTRACT_SPLIT_GROUP_COUNT_ITEMS",
        "_CONTRACT_REVIEW_SLOTS",
        "_CONTRACT_RECORDED_REVIEW_FIELD_ORDER",
        "_DRAFT_LEAKAGE_CONTROL_ITEMS",
        "_BOUNDARY_ITEMS",
        "_VARIANT_SLUG_ITEMS",
    ):
        monkeypatch.setattr(sut, name, (("forged", "GRANTED"),))
    monkeypatch.setattr(sut, "STAGEC_AUTHORING_GROUP_COUNT", 1)
    monkeypatch.setattr(sut, "STAGEC_AUTHORING_ROW_COUNT", 1)
    monkeypatch.setattr(sut, "STAGEC_AUTHORING_CARRIERS", ("forged",))
    monkeypatch.setattr(sut, "DIAGNOSTIC_VARIANT_ROLES", ("FORGED",))
    monkeypatch.setattr(
        sut,
        "STAGEC_AUTHORING_SPLIT_GROUP_COUNTS",
        (("FORGED", 320),),
    )
    monkeypatch.setattr(sut, "STAGEC_CORPUS_AUTHORING_SCAFFOLD_SCHEMA", "forged")
    monkeypatch.setattr(sut, "STAGEC_CORPUS_AUTHORING_SCAFFOLD_ID", "forged")
    monkeypatch.setattr(
        sut, "STAGEC_CORPUS_AUTHORING_SCAFFOLD_MEDIA_TYPE", "forged"
    )

    rebuilt = build_stagec_corpus_authoring_scaffold(
        authored_groups=(group,), reviews=reviews
    )
    replayed = load_stagec_corpus_authoring_scaffold(baseline.raw_bytes)
    assert rebuilt == baseline == replayed
    assert rebuilt.payload["classification"]["authority"] == "NON_AUTHORITY"
    assert rebuilt.payload["classification"]["admission"] == "NOT_ESTABLISHED"
    assert rebuilt.payload["historical_w0_boundary"]["row_import_count"] == 0
    assert rebuilt.payload["contract"]["required_row_count"] == 960
    assert rebuilt.payload["contract"]["variant_roles"] == (
        ADVERSARIAL_PRESENT,
        CLEAN_ABSENT,
        CLEAN_NULL_ABSENT,
    )
    assert rebuilt.payload["boundary"]["stagec_corpus_freeze"] == (
        "NOT_ESTABLISHED"
    )
    assert rebuilt.payload["boundary"]["admitted_row_count"] == 0
    assert rebuilt.payload["boundary"]["execution_authority"] == "NOT_GRANTED"
    assert rebuilt.artifact_ref.media_type == (
        "application/vnd.cas-harness.stagec-corpus-authoring-scaffold+json"
    )


def test_artifact_payload_has_no_gc_reachable_mutable_data_backing() -> None:
    artifact = build_stagec_corpus_authoring_scaffold(
        authored_groups=(_group(1),),
        reviews=(
            _review(1, ADVERSARIAL_PRESENT, "A"),
            _review(1, ADVERSARIAL_PRESENT, "B"),
        ),
    )
    payload = artifact.payload
    assert _reachable_mutable_payload_backings(payload) == ()
    assert not any(type(item) is dict for item in gc.get_referents(payload))
    assert not any(type(item) is list for item in gc.get_referents(payload))
    with pytest.raises((AttributeError, TypeError)):
        object.__setattr__(payload, "_items", (("boundary", "FORGED"),))
    with pytest.raises(TypeError):
        payload["classification"]["authority"] = "GRANTED"
    with pytest.raises(TypeError):
        payload["boundary"]["admitted_row_count"] = 960
    assert artifact.payload["classification"]["authority"] == "NON_AUTHORITY"
    assert artifact.payload["boundary"]["admitted_row_count"] == 0
    assert artifact.artifact_ref.verify_bytes(artifact.raw_bytes)


def test_artifact_is_factory_only_and_object_new_forgery_is_not_sealed() -> None:
    artifact = build_stagec_corpus_authoring_scaffold()
    constructor_values = {
        "raw_bytes": artifact.raw_bytes,
        "sha256": artifact.sha256,
        "byte_length": artifact.byte_length,
        "scaffold_id": artifact.scaffold_id,
        "authored_group_count": artifact.authored_group_count,
        "authored_row_count": artifact.authored_row_count,
        "recorded_review_count": artifact.recorded_review_count,
        "two_review_row_count": artifact.two_review_row_count,
        "two_review_approve_row_count": artifact.two_review_approve_row_count,
        "admitted_group_count": 320,
        "admitted_row_count": 960,
        "payload": {"classification": {"authority": "GRANTED"}},
    }
    with pytest.raises(TypeError, match="factory-only"):
        StageCCorpusAuthoringScaffoldArtifact(**constructor_values)

    forged = object.__new__(StageCCorpusAuthoringScaffoldArtifact)
    for name, value in constructor_values.items():
        object.__setattr__(forged, name, value)
    with pytest.raises(StageCCorpusAuthoringScaffoldError, match="process-sealed"):
        _ = forged.artifact_ref
    assert forged != artifact
    assert artifact != forged
    assert build_stagec_corpus_authoring_scaffold() == artifact


def test_module_factory_cannot_seal_authority_frozen_or_admitted_bytes() -> None:
    forged_raw, forged_value, _forged_payload, _forged_counts = (
        _authority_forgery()
    )
    with pytest.raises(
        StageCCorpusAuthoringScaffoldError,
        match="deterministic exact replay|non-authority",
    ):
        sut._artifact(forged_raw, forged_value)


def test_module_registrar_cannot_bless_object_new_slot_forgery() -> None:
    forged_raw, _forged_value, forged_payload, forged_counts = (
        _authority_forgery()
    )
    forged = _slot_forgery(forged_raw, forged_payload, forged_counts)
    sut._register_artifact_seal(
        forged,
        raw_bytes=forged_raw,
        sha256=sut.sha256_bytes(forged_raw),
        byte_length=len(forged_raw),
        scaffold_id=STAGEC_CORPUS_AUTHORING_SCAFFOLD_ID,
        counts=forged_counts,
        payload=forged_payload,
    )
    assert sut._require_artifact_seal(forged).artifact() is forged
    with pytest.raises(
        StageCCorpusAuthoringScaffoldError,
        match="deterministic exact replay|non-authority",
    ):
        _ = forged.artifact_ref


def test_every_module_callable_fails_to_mint_ref_for_authority_slot_forgery() -> None:
    forged_raw, forged_value, forged_payload, forged_counts = (
        _authority_forgery()
    )
    forged = _slot_forgery(forged_raw, forged_payload, forged_counts)
    seal_kwargs = {
        "artifact": forged,
        "raw_bytes": forged_raw,
        "sha256": sut.sha256_bytes(forged_raw),
        "byte_length": len(forged_raw),
        "scaffold_id": STAGEC_CORPUS_AUTHORING_SCAFFOLD_ID,
        "counts": forged_counts,
        "payload": forged_payload,
    }
    semantic_kwargs = dict(seal_kwargs)
    del semantic_kwargs["artifact"]
    attempts = (
        ((), {}),
        ((forged_raw, forged_value), {}),
        ((forged,), {}),
        ((), seal_kwargs),
        ((), semantic_kwargs),
    )
    module_callables = {
        name: candidate
        for name, candidate in vars(sut).items()
        if callable(candidate)
        and getattr(candidate, "__module__", None) == sut.__name__
    }
    assert {
        "_artifact",
        "_register_artifact_seal",
        "_require_artifact_seal",
        "_validate_artifact_semantics",
        "build_stagec_corpus_authoring_scaffold",
        "load_stagec_corpus_authoring_scaffold",
    } <= set(module_callables)

    attempted: set[str] = set()
    for name, candidate in module_callables.items():
        attempted.add(name)
        for args, kwargs in attempts:
            try:
                result = candidate(*args, **kwargs)
            except Exception:
                continue
            if isinstance(result, ArtifactRef):
                assert not result.verify_bytes(forged_raw), name
            if isinstance(result, StageCCorpusAuthoringScaffoldArtifact):
                try:
                    artifact_ref = result.artifact_ref
                except StageCCorpusAuthoringScaffoldError:
                    pass
                else:
                    assert not artifact_ref.verify_bytes(forged_raw), name
        try:
            artifact_ref = forged.artifact_ref
        except StageCCorpusAuthoringScaffoldError:
            pass
        else:
            assert not artifact_ref.verify_bytes(forged_raw), name
    assert attempted == set(module_callables)


def test_immutable_mapping_equality_is_recursive_and_bool_int_exact() -> None:
    artifact = build_stagec_corpus_authoring_scaffold(
        authored_groups=(_group(1),),
        reviews=(
            _review(1, ADVERSARIAL_PRESENT, "A"),
            _review(1, ADVERSARIAL_PRESENT, "B"),
        ),
    )
    same_payload = sut._immutable_json_value(json.loads(artifact.raw_bytes))
    assert artifact.payload == same_payload
    assert same_payload == artifact.payload

    forged_value = json.loads(artifact.raw_bytes)
    forged_value["groups"][0]["rows"][0]["row_ordinal"] = True
    forged_payload = sut._immutable_json_value(forged_value)
    assert artifact.payload != forged_payload
    assert forged_payload != artifact.payload
    assert artifact.payload["groups"][0]["rows"][0] != (
        forged_payload["groups"][0]["rows"][0]
    )

    nested_left = sut._ImmutableJSONObject(
        (("outer", (sut._ImmutableJSONObject((("count", 1),)),)),)
    )
    nested_right = sut._ImmutableJSONObject(
        (("outer", (sut._ImmutableJSONObject((("count", True),)),)),)
    )
    assert nested_left != nested_right
    assert nested_right != nested_left


def test_authority_critical_callable_rebinding_cannot_forge_build_or_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group = _group(1)
    reviews = (
        _review(1, ADVERSARIAL_PRESENT, "A"),
        _review(1, ADVERSARIAL_PRESENT, "B"),
    )
    baseline = build_stagec_corpus_authoring_scaffold(
        authored_groups=(group,), reviews=reviews
    )
    forged = json.loads(baseline.raw_bytes)
    forged["classification"]["authority"] = "GRANTED"
    forged["classification"]["admission"] = "ADMITTED"
    forged["boundary"]["stagec_corpus_freeze"] = "FROZEN"
    forged["boundary"]["admitted_group_count"] = 320
    forged["boundary"]["admitted_row_count"] = 960
    forged["boundary"]["execution_authority"] = "GRANTED"
    forged_raw = canonical_json_bytes(forged)

    monkeypatch.setattr(sut, "_render_value", lambda *_args, **_kwargs: forged)
    monkeypatch.setattr(sut, "canonical_json_bytes", lambda _value: forged_raw)
    monkeypatch.setattr(sut, "canonical_sha256", lambda _value: "F" * 64)
    monkeypatch.setattr(sut, "sha256_bytes", lambda _value: "F" * 64)
    monkeypatch.setattr(sut, "_artifact", lambda *_args, **_kwargs: "FORGED")
    monkeypatch.setattr(sut, "_immutable_json_value", lambda _value: forged)
    monkeypatch.setattr(
        sut,
        "_parse_scaffold_inputs",
        lambda _value: ((), ()),
    )
    monkeypatch.setattr(
        sut,
        "load_json_object",
        lambda _raw: (forged_raw, forged),
    )
    monkeypatch.setattr(sut, "_fail", lambda _message: None)
    monkeypatch.setattr(sut, "ArtifactRef", lambda **_kwargs: "FORGED")
    monkeypatch.setattr(
        sut,
        "StageCCorpusAuthoringScaffoldArtifact",
        lambda **_kwargs: "FORGED",
    )

    rebuilt = build_stagec_corpus_authoring_scaffold(
        authored_groups=(group,), reviews=reviews
    )
    replayed = load_stagec_corpus_authoring_scaffold(baseline.raw_bytes)
    assert rebuilt == baseline == replayed
    assert rebuilt.payload["classification"]["authority"] == "NON_AUTHORITY"
    assert rebuilt.payload["classification"]["admission"] == "NOT_ESTABLISHED"
    assert rebuilt.payload["boundary"]["stagec_corpus_freeze"] == (
        "NOT_ESTABLISHED"
    )
    assert rebuilt.payload["boundary"]["admitted_group_count"] == 0
    assert rebuilt.payload["boundary"]["admitted_row_count"] == 0
    assert rebuilt.payload["boundary"]["execution_authority"] == "NOT_GRANTED"
    assert rebuilt.artifact_ref.verify_bytes(rebuilt.raw_bytes)
    with pytest.raises(StageCCorpusAuthoringScaffoldError):
        load_stagec_corpus_authoring_scaffold(forged_raw)


def test_recursive_integer_to_boolean_aliases_all_fail_exact_byte_replay() -> None:
    artifact = build_stagec_corpus_authoring_scaffold(
        authored_groups=(_group(1),),
        reviews=(
            _review(1, ADVERSARIAL_PRESENT, "A"),
            _review(1, ADVERSARIAL_PRESENT, "B"),
        ),
    )
    source = json.loads(artifact.raw_bytes)
    integer_paths = tuple(
        (path, value)
        for path, value in _scalar_paths(source)
        if type(value) is int and value in {0, 1}
    )
    represented_paths = {path for path, _value in integer_paths}
    assert ("boundary", "admitted_row_count") in represented_paths
    assert ("groups", 0, "group_ordinal") in represented_paths
    assert ("groups", 0, "rows", 0, "row_ordinal") in represented_paths
    assert ("recorded_reviews", 0, 0) in represented_paths
    assert ("progress", "admitted_row_count") in represented_paths

    for path, integer in integer_paths:
        mutated = json.loads(artifact.raw_bytes)
        _replace_path(mutated, path, bool(integer))
        with pytest.raises(StageCCorpusAuthoringScaffoldError):
            load_stagec_corpus_authoring_scaffold(canonical_json_bytes(mutated))


def test_replay_is_exact_immutable_and_rejects_derived_field_tampering() -> None:
    artifact = build_stagec_corpus_authoring_scaffold(
        authored_groups=(_group(1),),
        reviews=(
            _review(1, ADVERSARIAL_PRESENT, "A"),
            _review(1, ADVERSARIAL_PRESENT, "B"),
        ),
    )
    assert load_stagec_corpus_authoring_scaffold(artifact.raw_bytes) == artifact
    with pytest.raises(FrozenInstanceError):
        artifact.admitted_row_count = 960  # type: ignore[misc]
    with pytest.raises(TypeError):
        artifact.payload["boundary"]["admitted_row_count"] = 960  # type: ignore[index]

    mutations = (
        lambda value: value["progress"].__setitem__("admitted_row_count", 1),
        lambda value: value["boundary"].__setitem__(
            "stagec_corpus_freeze", "FROZEN"
        ),
        lambda value: value["groups"][0]["rows"][0].__setitem__(
            "prompt_sha256", "0" * 64
        ),
        lambda value: value["recorded_reviews"][0].__setitem__(5, "0" * 64),
        lambda value: value["classification"].__setitem__("authority", "AUTHORITY"),
    )
    for change in mutations:
        with pytest.raises(
            StageCCorpusAuthoringScaffoldError, match="deterministic exact replay"
        ):
            load_stagec_corpus_authoring_scaffold(_mutate(artifact.raw_bytes, change))


def test_loader_rejects_noncanonical_extra_duplicate_and_nonbytes() -> None:
    artifact = build_stagec_corpus_authoring_scaffold()
    pretty = json.dumps(json.loads(artifact.raw_bytes), indent=2).encode("ascii")
    with pytest.raises(StageCCorpusAuthoringScaffoldError, match="canonical JSON"):
        load_stagec_corpus_authoring_scaffold(pretty)
    extra = _mutate(artifact.raw_bytes, lambda value: value.__setitem__("extra", 1))
    with pytest.raises(StageCCorpusAuthoringScaffoldError, match="closed field set"):
        load_stagec_corpus_authoring_scaffold(extra)
    with pytest.raises(StageCCorpusAuthoringScaffoldError, match="strict JSON"):
        load_stagec_corpus_authoring_scaffold(b'{"x":1,"x":2}')
    for value in (bytearray(artifact.raw_bytes), memoryview(artifact.raw_bytes), "x"):
        with pytest.raises(StageCCorpusAuthoringScaffoldError, match="immutable bytes"):
            load_stagec_corpus_authoring_scaffold(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("groups", "message"),
    [
        (( _group(1), _group(1)), "duplicate group ordinal"),
        (
            (_group(1), _group(2, base_intent="New Stage C synthetic base intent 001.")),
            "duplicate base intent",
        ),
        (
            (
                _group(1),
                _group(
                    2,
                    prompt_prefix="New Stage C synthetic prompt 001",
                ),
            ),
            "duplicate prompt",
        ),
        (
            (_group(1, template_family="cross-split"), _group(161, template_family="cross-split")),
            "template family crosses",
        ),
    ],
)
def test_exact_and_template_leakage_checks_fail_closed(
    groups: tuple[StageCCorpusDraftGroupInput, ...], message: str
) -> None:
    with pytest.raises(StageCCorpusAuthoringScaffoldError, match=message):
        build_stagec_corpus_authoring_scaffold(authored_groups=groups)


def test_variant_order_carrier_text_and_exact_container_types_fail_closed() -> None:
    with pytest.raises(StageCCorpusAuthoringScaffoldError, match="canonical variant order"):
        build_stagec_corpus_authoring_scaffold(
            authored_groups=(
                _group(
                    1,
                    row_order=(CLEAN_ABSENT, ADVERSARIAL_PRESENT, CLEAN_NULL_ABSENT),
                ),
            )
        )
    with pytest.raises(StageCCorpusAuthoringScaffoldError, match="closed enum"):
        build_stagec_corpus_authoring_scaffold(
            authored_groups=(
                _group(1, carriers=("base64", "url", "binary")),
            )
        )
    with pytest.raises(StageCCorpusAuthoringScaffoldError, match="NFC-normalized"):
        build_stagec_corpus_authoring_scaffold(
            authored_groups=(
                _group(1, base_intent="Cafe\u0301"),
            )
        )
    with pytest.raises(StageCCorpusAuthoringScaffoldError, match="exact tuple"):
        build_stagec_corpus_authoring_scaffold(
            authored_groups=[_group(1)]  # type: ignore[arg-type]
        )


def test_review_target_slot_identity_decision_and_duplicates_fail_closed() -> None:
    group = _group(1)
    cases = (
        (
            (_review(2, ADVERSARIAL_PRESENT, "A"),),
            "has not been authored",
        ),
        (
            (
                _review(1, ADVERSARIAL_PRESENT, "A"),
                _review(1, ADVERSARIAL_PRESENT, "A"),
            ),
            "duplicate group/variant/slot",
        ),
        (
            (
                _review(1, ADVERSARIAL_PRESENT, "A", reviewer_id="same-reviewer"),
                _review(1, ADVERSARIAL_PRESENT, "B", reviewer_id="same-reviewer"),
            ),
            "distinct reviewer IDs",
        ),
        (
            (_review(1, ADVERSARIAL_PRESENT, "C"),),
            "noncanonical review slot",
        ),
        (
            (_review(1, ADVERSARIAL_PRESENT, "A", decision="FROZEN"),),
            "closed draft-review enum",
        ),
    )
    for reviews, message in cases:
        with pytest.raises(StageCCorpusAuthoringScaffoldError, match=message):
            build_stagec_corpus_authoring_scaffold(
                authored_groups=(group,), reviews=reviews
            )


def test_two_matching_draft_approvals_are_not_authenticated_adjudication() -> None:
    artifact = build_stagec_corpus_authoring_scaffold(
        authored_groups=(_group(1),),
        reviews=(
            _review(1, ADVERSARIAL_PRESENT, "A"),
            _review(1, ADVERSARIAL_PRESENT, "B"),
        ),
    )
    assert artifact.two_review_approve_row_count == 1
    assert artifact.payload["contract"]["review_identity_authentication"] == (
        "NOT_PROVIDED"
    )
    assert artifact.payload["draft_leakage_controls"]["semantic_equivalence_review"] == (
        "NOT_PERFORMED"
    )
    assert artifact.payload["boundary"]["double_adjudication_authority"] == (
        "NOT_ESTABLISHED"
    )
    assert artifact.admitted_row_count == 0


def test_public_build_and_replay_paths_have_no_io_process_network_or_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = build_stagec_corpus_authoring_scaffold(authored_groups=(_group(1),))

    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden external effect")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    rebuilt = build_stagec_corpus_authoring_scaffold(authored_groups=(_group(1),))
    replayed = load_stagec_corpus_authoring_scaffold(artifact.raw_bytes)
    assert rebuilt == artifact == replayed

    class HostileTuple(tuple):
        def __iter__(self):
            raise AssertionError("caller callback invoked")

    with pytest.raises(StageCCorpusAuthoringScaffoldError, match="exact tuple"):
        build_stagec_corpus_authoring_scaffold(
            authored_groups=HostileTuple((_group(1),))  # type: ignore[arg-type]
        )


def test_module_exposes_no_positive_activation_provider_or_admission_function() -> None:
    public_names = set(sut.__all__)
    assert not any(
        token in name.lower()
        for name in public_names
        for token in ("activate", "execute", "provider", "admit", "freeze")
    )
    assert "socket" not in sut.__dict__
    assert "subprocess" not in sut.__dict__
    assert "requests" not in sut.__dict__
    assert "torch" not in sut.__dict__
    assert "transformers" not in sut.__dict__


def test_declared_public_constants_match_exact_authoring_shape() -> None:
    assert STAGEC_AUTHORING_GROUP_COUNT == 320
    assert STAGEC_AUTHORING_ROW_COUNT == 960
    assert STAGEC_AUTHORING_VARIANT_COUNT == 3
    assert STAGEC_AUTHORING_REVIEW_SLOTS == ("A", "B")
    assert STAGEC_AUTHORING_CARRIERS == ("base64", "plaintext", "unicode", "url")
