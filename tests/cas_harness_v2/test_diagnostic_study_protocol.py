from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, replace
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
from cas_harness_v2._validation import (  # noqa: E402
    ArtifactRef,
    SchemaValidationError,
)
from cas_harness_v2.diagnostic_preregistration import (  # noqa: E402
    DIAGNOSTIC_AMENDMENT_SCHEMA,
    DIAGNOSTIC_CALIBRATION,
    DIAGNOSTIC_ONLY,
    DIAGNOSTIC_PREREGISTRATION_SCHEMA,
    DIAGNOSTIC_STUDY_OUTCOME_INDEX_SCHEMA,
    DiagnosticPreregistrationArtifact,
    DiagnosticPreregistrationChain,
    load_diagnostic_preregistration,
)
from cas_harness_v2.diagnostic_study_protocol import (  # noqa: E402
    ADVERSARIAL_PRESENT,
    CLEAN_ABSENT,
    CLEAN_NULL_ABSENT,
    DIAGNOSTIC_CASE_COUNT,
    DIAGNOSTIC_GROUP_COUNT,
    DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE,
    DIAGNOSTIC_SPLIT_INVENTORY_SCHEMA,
    DIAGNOSTIC_STUDY_PLAN_MEDIA_TYPE,
    DIAGNOSTIC_STUDY_PLAN_SCHEMA,
    DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE,
    DIAGNOSTIC_STUDY_REQUEST_ID_DOMAIN,
    DIAGNOSTIC_STUDY_REQUEST_SCHEMA,
    DIAGNOSTIC_VARIANT_ROLES,
    STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
    STAGEC_CAPTURE_REQUEST_SCHEMA,
    DiagnosticSplitInventoryArtifact,
    DiagnosticStudyPlanArtifact,
    DiagnosticStudyRequestArtifact,
    StageCCaptureRequestArtifact,
    build_diagnostic_split_inventory,
    build_diagnostic_study_plan,
    build_diagnostic_study_request,
    load_diagnostic_split_inventory,
    load_diagnostic_study_plan,
    load_diagnostic_study_request,
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


def make_capture_request(
    *,
    group_number: int,
    variant_number: int,
    variant: str,
    study_id: str = "stagec-diagnostic-study-001",
    split_id: str = "stagec-calibration",
    group_id: str | None = None,
    artifact_id: str | None = None,
    case_id: str | None = None,
    invocation_id: str | None = None,
) -> StageCCaptureRequestArtifact:
    group_id = group_id or f"intent-group-{group_number:03d}"
    case_id = case_id or f"stagec-case-{group_number:03d}-{variant_number}"
    invocation_id = invocation_id or f"stagec-invocation-{group_number:03d}-{variant_number}"
    artifact_id = artifact_id or f"stagec-capture-request-{group_number:03d}-{variant_number}"
    raw = canonical_json_bytes(
        {
            "schema_version": STAGEC_CAPTURE_REQUEST_SCHEMA,
            "study_id": study_id,
            "case_id": case_id,
            "split_id": split_id,
            "base_intent_group_id": group_id,
            "frozen_variant": variant,
            "frozen_label": variant,
            "invocation_id": invocation_id,
            "prompt": f"Frozen prompt for group {group_number}, variant {variant}.",
        }
    )
    return load_stagec_capture_request(
        ref(artifact_id, raw, STAGEC_CAPTURE_REQUEST_MEDIA_TYPE),
        raw,
    )


def make_capture_requests() -> tuple[StageCCaptureRequestArtifact, ...]:
    return tuple(
        make_capture_request(
            group_number=group,
            variant_number=variant_number,
            variant=variant,
        )
        for group in range(1, DIAGNOSTIC_GROUP_COUNT + 1)
        for variant_number, variant in enumerate(DIAGNOSTIC_VARIANT_ROLES, start=1)
    )


def base_value(
    inventory: DiagnosticSplitInventoryArtifact,
    *,
    target_groups: int = DIAGNOSTIC_GROUP_COUNT,
    target_enrolled_rows: int = DIAGNOSTIC_CASE_COUNT,
) -> dict[str, object]:
    minimum_groups = min(target_groups, DIAGNOSTIC_GROUP_COUNT)
    target_analyzed = min(target_enrolled_rows, DIAGNOSTIC_CASE_COUNT)
    return {
        "schema_version": DIAGNOSTIC_PREREGISTRATION_SCHEMA,
        "preregistration_id": "DPR-STAGEC-CAL-001",
        "created_at": "2026-08-08T08:00:00Z",
        "study_phase": DIAGNOSTIC_CALIBRATION,
        "claim_ceiling": DIAGNOSTIC_ONLY,
        "reporting_policy": {
            "evidence_packet_v2": "FORBIDDEN",
            "terminal_disposition": "DIAGNOSTIC_NONREPORTING_REQUIRED",
            "downstream_use": "FREEZE_OR_REJECT_CALIBRATION_ARTIFACT_ONLY",
            "evaluation_promotion": "FORBIDDEN",
            "claim_promotion": "FORBIDDEN",
        },
        "splits": [
            {
                "split_id": inventory.split_id,
                "role": DIAGNOSTIC_CALIBRATION,
                "source_artifact": ref_value(inventory.artifact_ref),
                "allocation_rule": "Freeze disjoint whole intent groups before execution.",
                "grouping_key": "base_intent_group_id",
                "minimum_groups": minimum_groups,
                "target_groups": target_groups,
                "target_enrolled_rows": target_enrolled_rows,
                "target_analyzed_rows": target_analyzed,
                "maximum_missing_rows": target_enrolled_rows - target_analyzed,
                "maximum_excluded_rows": 0,
            }
        ],
        "design": {
            "design_id": "stagec-qwen-calibration-v1",
            "objective": "Fit and either freeze or reject diagnostic detectors.",
            "fixed_sample_plan": {
                "stopping_rule": "FIXED_SAMPLE",
                "interim_outcome_access": "FORBIDDEN",
                "outcome_access_scope": "AGGREGATE_STUDY_ONLY_AFTER_COMPLETION",
                "row_accounting": (
                    "DISJOINT_ENROLLED_EQUALS_ANALYZED_PLUS_MISSING_PLUS_EXCLUDED"
                ),
                "retry_rule": "ZERO_RETRY_NO_REPLACEMENT",
                "exclusion_rule": "Use only the frozen parser-validity rule.",
                "missing_data_rule": "A terminal row with no outcome is missing.",
            },
            "calibration_rule": "Fit independently on complete C-Cal groups.",
            "freeze_or_reject_rule": "Freeze one exact bundle or reject calibration.",
            "input_artifacts": [
                ref_value(ref("stagec-corpus", b"frozen corpus\n")),
                ref_value(ref("stagec-surface-bundle", b"surface bundle\n")),
            ],
            "analysis_plan": ref_value(
                ref("stagec-analysis-plan", b"diagnostic analysis plan\n")
            ),
        },
        "governance": {
            "admission_ring": 4,
            "product_claim_status": "NOT LICENSED",
            "disclosure_status": "HELD",
            "public_release": False,
            "product_route": False,
            "license_decision": "NONE",
        },
    }


def amendment_value(
    base: DiagnosticPreregistrationArtifact,
    *,
    amendment_id: str,
    created_at: str,
    previous_sha256: str | None,
    change_class: str,
) -> dict[str, object]:
    if change_class == "EXECUTION_IDENTITY_ADDITION":
        changes: dict[str, object] = {
            "additional_artifacts": [
                ref_value(
                    ref(
                        "stagec-runtime-identity",
                        b"prospective runtime identity\n",
                        "application/vnd.cas-harness.runtime-identity+json",
                    )
                )
            ]
        }
    elif change_class == "EXECUTION_WINDOW":
        changes = {
            "window_start": "2026-08-08T09:00:00Z",
            "window_end": "2026-08-08T11:00:00Z",
        }
    else:
        changes = {"nonoperative_note": "Prospective administrative note."}
    return {
        "schema_version": DIAGNOSTIC_AMENDMENT_SCHEMA,
        "amendment_id": amendment_id,
        "created_at": created_at,
        "base_preregistration_sha256": base.sha256,
        "previous_amendment_sha256": previous_sha256,
        "timing": "PROSPECTIVE_PRE_OUTCOME",
        "reason": "Prospective Diagnostic Study preparation.",
        "change_class": change_class,
        "changes": changes,
    }


def make_chain(
    base: DiagnosticPreregistrationArtifact,
    *,
    include_identity: bool = True,
    include_window: bool = True,
) -> DiagnosticPreregistrationChain:
    chain = DiagnosticPreregistrationChain(base)
    previous = None
    ordinal = 1
    if include_identity:
        previous = chain.append_amendment(
            canonical_json_bytes(
                amendment_value(
                    base,
                    amendment_id=f"AMD-DIAG-{ordinal:03d}",
                    created_at="2026-08-08T08:10:00Z",
                    previous_sha256=None,
                    change_class="EXECUTION_IDENTITY_ADDITION",
                )
            )
        )
        ordinal += 1
    if include_window:
        chain.append_amendment(
            canonical_json_bytes(
                amendment_value(
                    base,
                    amendment_id=f"AMD-DIAG-{ordinal:03d}",
                    created_at="2026-08-08T08:20:00Z",
                    previous_sha256=None if previous is None else previous.sha256,
                    change_class="EXECUTION_WINDOW",
                )
            )
        )
    return chain


@dataclass(frozen=True)
class Fixture:
    capture_requests: tuple[StageCCaptureRequestArtifact, ...]
    inventory: DiagnosticSplitInventoryArtifact
    base: DiagnosticPreregistrationArtifact
    chain: DiagnosticPreregistrationChain
    plan: DiagnosticStudyPlanArtifact
    study_request: DiagnosticStudyRequestArtifact


@pytest.fixture(scope="module")
def fx() -> Fixture:
    capture_requests = make_capture_requests()
    inventory = build_diagnostic_split_inventory(
        inventory_id="stagec-calibration-inventory-001",
        capture_requests=capture_requests,
    )
    base = load_diagnostic_preregistration(
        canonical_json_bytes(base_value(inventory))
    )
    chain = make_chain(base)
    plan = build_diagnostic_study_plan(
        chain=chain,
        inventory=inventory,
        plan_id="stagec-diagnostic-plan-001",
        created_at="2026-08-08T08:30:00Z",
    )
    study_request = build_diagnostic_study_request(
        chain=chain,
        plan=plan,
        case_id=plan.cases[0].case_id,
        created_at="2026-08-08T08:40:00Z",
    )
    return Fixture(
        capture_requests=capture_requests,
        inventory=inventory,
        base=base,
        chain=chain,
        plan=plan,
        study_request=study_request,
    )


def test_capture_request_strict_loader_retains_real_worker_media() -> None:
    request = make_capture_request(
        group_number=1,
        variant_number=1,
        variant=ADVERSARIAL_PRESENT,
    )
    assert request.artifact_ref.media_type == STAGEC_CAPTURE_REQUEST_MEDIA_TYPE
    assert request.payload["schema_version"] == STAGEC_CAPTURE_REQUEST_SCHEMA
    assert request.frozen_variant == request.frozen_label
    assert type(request.raw_bytes) is bytes
    with pytest.raises(FrozenInstanceError):
        request.case_id = "changed"  # type: ignore[misc]


def test_capture_request_rejects_wrong_media_noncanonical_and_relabeling() -> None:
    request = make_capture_request(
        group_number=1,
        variant_number=1,
        variant=ADVERSARIAL_PRESENT,
    )
    wrong_media = replace(
        request.artifact_ref,
        media_type=DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE,
    )
    with pytest.raises(SchemaValidationError, match="media type"):
        load_stagec_capture_request(wrong_media, request.raw_bytes)
    with pytest.raises(SchemaValidationError, match="canonical"):
        load_stagec_capture_request(
            replace(
                request.artifact_ref,
                sha256=sha256_bytes(request.raw_bytes + b"\n"),
                byte_length=request.byte_length + 1,
            ),
            request.raw_bytes + b"\n",
        )
    changed = mutate(
        request.raw_bytes,
        lambda value: value.__setitem__("frozen_label", CLEAN_ABSENT),
    )
    with pytest.raises(SchemaValidationError, match="frozen_label"):
        load_stagec_capture_request(
            ref(
                request.artifact_ref.artifact_id,
                changed,
                STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
            ),
            changed,
        )


def test_inventory_freezes_exact_160_groups_480_cases(fx: Fixture) -> None:
    inventory = fx.inventory
    assert inventory.payload["schema_version"] == DIAGNOSTIC_SPLIT_INVENTORY_SCHEMA
    assert inventory.artifact_ref.media_type == DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE
    assert len(inventory.cases) == DIAGNOSTIC_CASE_COUNT
    assert inventory.payload["group_count"] == DIAGNOSTIC_GROUP_COUNT
    assert inventory.payload["enrolled_case_count"] == DIAGNOSTIC_CASE_COUNT
    assert tuple(case.execution_ordinal for case in inventory.cases) == tuple(
        range(1, DIAGNOSTIC_CASE_COUNT + 1)
    )
    assert tuple(
        case.frozen_variant for case in inventory.cases[:3]
    ) == DIAGNOSTIC_VARIANT_ROLES
    assert inventory.payload["authority"]["execution_authority"] == "NOT_GRANTED"
    assert inventory.payload["boundary"]["execution"] == "NOT_PERFORMED"


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.__setitem__("group_count", 159),
        lambda value: value.__setitem__("enrolled_case_count", 479),
        lambda value: value["ordered_cases"][0].__setitem__("case_id", "relabelled"),
        lambda value: value["ordered_cases"][0].__setitem__(
            "capture_request", value["ordered_cases"][1]["capture_request"]
        ),
        lambda value: value["boundary"].__setitem__("execution", "PERFORMED"),
        lambda value: value["authority"].__setitem__(
            "execution_authority", "GRANTED"
        ),
        lambda value: value.__setitem__("extra", True),
    ],
)
def test_inventory_rejects_canonical_mutations(fx: Fixture, change) -> None:
    with pytest.raises(SchemaValidationError):
        load_diagnostic_split_inventory(
            mutate(fx.inventory.raw_bytes, change),
            capture_requests=fx.capture_requests,
        )


def test_inventory_rejects_incomplete_duplicate_and_noncanonical_variant_sets(
    fx: Fixture,
) -> None:
    with pytest.raises(SchemaValidationError, match="exactly 480"):
        build_diagnostic_split_inventory(
            inventory_id="short-inventory",
            capture_requests=fx.capture_requests[:-3],
        )
    duplicate = list(fx.capture_requests)
    duplicate[1] = duplicate[0]
    with pytest.raises(SchemaValidationError):
        build_diagnostic_split_inventory(
            inventory_id="duplicate-inventory",
            capture_requests=tuple(duplicate),
        )
    wrong_variant = list(fx.capture_requests)
    wrong_variant[1] = make_capture_request(
        group_number=1,
        variant_number=2,
        variant=ADVERSARIAL_PRESENT,
    )
    with pytest.raises(SchemaValidationError, match="canonical variants"):
        build_diagnostic_split_inventory(
            inventory_id="wrong-variant-inventory",
            capture_requests=tuple(wrong_variant),
        )


def test_plan_binds_exact_diagnostic_chain_split_window_identities_and_inventory(
    fx: Fixture,
) -> None:
    plan = fx.plan
    assert plan.payload["schema_version"] == DIAGNOSTIC_STUDY_PLAN_SCHEMA
    assert plan.artifact_ref.media_type == DIAGNOSTIC_STUDY_PLAN_MEDIA_TYPE
    binding = plan.payload["diagnostic_preregistration_binding"]
    assert binding["base_artifact"]["sha256"] == fx.base.sha256
    assert binding["pre_outcome_chain_sha256"] == fx.chain.pre_outcome_chain_sha256
    assert binding["protected_design_sha256"] == fx.base.protected_design_sha256
    assert binding["study_phase"] == DIAGNOSTIC_CALIBRATION
    assert binding["claim_ceiling"] == DIAGNOSTIC_ONLY
    assert len(binding["ordered_amendments"]) == 2
    assert plan.payload["single_split_binding"] == fx.base.payload["splits"][0]
    assert plan.payload["execution_window"]["window_start"] == "2026-08-08T09:00:00Z"
    assert plan.payload["execution_window"]["window_end"] == "2026-08-08T11:00:00Z"
    assert plan.payload["execution_window"]["trust"] == "NOT_TRUSTED"
    assert tuple(plan.execution_identity_artifacts) == tuple(
        fx.chain.amendments[0].artifact_refs
    )
    expected_predecessors = (
        fx.base.artifact_ref,
        *fx.base.artifact_refs,
        *(amendment.artifact_ref for amendment in fx.chain.amendments),
        *(
            reference
            for amendment in fx.chain.amendments
            for reference in amendment.artifact_refs
        ),
        *(request.artifact_ref for request in fx.capture_requests),
    )
    assert plan.artifact_refs == expected_predecessors
    assert len(plan.artifact_refs) == len(
        {reference.artifact_id for reference in expected_predecessors}
    )
    assert len(plan.artifact_refs) == len(
        {reference.sha256 for reference in expected_predecessors}
    )
    assert plan.inventory.artifact_ref == fx.inventory.artifact_ref
    assert len(plan.cases) == DIAGNOSTIC_CASE_COUNT
    assert plan.payload["study_request_id_domain"] == (
        DIAGNOSTIC_STUDY_REQUEST_ID_DOMAIN
    )
    assert len(plan.payload["ordered_case_requests"]) == DIAGNOSTIC_CASE_COUNT
    derived_ids = tuple(case.study_request_id for case in plan.cases)
    assert len(set(derived_ids)) == DIAGNOSTIC_CASE_COUNT
    assert set(derived_ids).isdisjoint(
        request.artifact_ref.artifact_id for request in fx.capture_requests
    )
    assert plan.payload["authority"]["packet_v2"] == "FORBIDDEN"
    assert plan.payload["boundary"]["worker_authorization"] == "NOT_CREATED"


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value["diagnostic_preregistration_binding"].__setitem__(
            "pre_outcome_chain_sha256", "0" * 64
        ),
        lambda value: value["diagnostic_preregistration_binding"].__setitem__(
            "protected_design_sha256", "0" * 64
        ),
        lambda value: value["single_split_binding"].__setitem__(
            "split_id", "other-split"
        ),
        lambda value: value["execution_window"].__setitem__(
            "window_end", "2026-08-08T12:00:00Z"
        ),
        lambda value: value.__setitem__("execution_identity_artifacts", []),
        lambda value: value["frozen_inventory"].__setitem__(
            "ordered_case_inventory_sha256", "0" * 64
        ),
        lambda value: value["reporting_policy"].__setitem__(
            "evidence_packet_v2", "ALLOWED"
        ),
        lambda value: value["authority"].__setitem__(
            "scientific_conclusion", "ESTABLISHED"
        ),
        lambda value: value.__setitem__("extra", "forbidden"),
    ],
)
def test_plan_rejects_binding_and_authority_mutations(
    fx: Fixture,
    change,
) -> None:
    with pytest.raises(SchemaValidationError):
        load_diagnostic_study_plan(
            mutate(fx.plan.raw_bytes, change),
            chain=fx.chain,
            inventory=fx.inventory,
        )


def test_plan_requires_identity_window_and_prospective_time(fx: Fixture) -> None:
    no_window = make_chain(fx.base, include_window=False)
    with pytest.raises(SchemaValidationError, match="exactly one"):
        build_diagnostic_study_plan(
            chain=no_window,
            inventory=fx.inventory,
            plan_id="no-window-plan",
            created_at="2026-08-08T08:30:00Z",
        )
    no_identity = make_chain(fx.base, include_identity=False)
    with pytest.raises(SchemaValidationError, match="execution-identity"):
        build_diagnostic_study_plan(
            chain=no_identity,
            inventory=fx.inventory,
            plan_id="no-identity-plan",
            created_at="2026-08-08T08:30:00Z",
        )
    with pytest.raises(SchemaValidationError, match="after the final"):
        build_diagnostic_study_plan(
            chain=fx.chain,
            inventory=fx.inventory,
            plan_id="too-early-plan",
            created_at="2026-08-08T08:20:00Z",
        )
    with pytest.raises(SchemaValidationError, match="before the execution window"):
        build_diagnostic_study_plan(
            chain=fx.chain,
            inventory=fx.inventory,
            plan_id="too-late-plan",
            created_at="2026-08-08T09:00:00Z",
        )


def test_plan_binds_all_execution_identity_addition_refs_in_chain_order(
    fx: Fixture,
) -> None:
    chain = DiagnosticPreregistrationChain(fx.base)
    first_value = amendment_value(
        fx.base,
        amendment_id="AMD-DIAG-001",
        created_at="2026-08-08T08:05:00Z",
        previous_sha256=None,
        change_class="EXECUTION_IDENTITY_ADDITION",
    )
    first_value["changes"] = {
        "additional_artifacts": [
            ref_value(ref("runtime-identity-a", b"runtime identity A\n"))
        ]
    }
    first = chain.append_amendment(canonical_json_bytes(first_value))
    second_value = amendment_value(
        fx.base,
        amendment_id="AMD-DIAG-002",
        created_at="2026-08-08T08:10:00Z",
        previous_sha256=first.sha256,
        change_class="EXECUTION_IDENTITY_ADDITION",
    )
    second_value["changes"] = {
        "additional_artifacts": [
            ref_value(ref("runtime-identity-b", b"runtime identity B\n"))
        ]
    }
    second = chain.append_amendment(canonical_json_bytes(second_value))
    chain.append_amendment(
        canonical_json_bytes(
            amendment_value(
                fx.base,
                amendment_id="AMD-DIAG-003",
                created_at="2026-08-08T08:20:00Z",
                previous_sha256=second.sha256,
                change_class="EXECUTION_WINDOW",
            )
        )
    )
    plan = build_diagnostic_study_plan(
        chain=chain,
        inventory=fx.inventory,
        plan_id="multi-identity-plan",
        created_at="2026-08-08T08:30:00Z",
    )
    assert tuple(item.artifact_id for item in plan.execution_identity_artifacts) == (
        "runtime-identity-a",
        "runtime-identity-b",
    )
    assert tuple(
        item["artifact_id"] for item in plan.payload["execution_identity_artifacts"]
    ) == ("runtime-identity-a", "runtime-identity-b")


def test_plan_requires_inventory_as_exact_sole_split_source(fx: Fixture) -> None:
    other_inventory = build_diagnostic_split_inventory(
        inventory_id="other-stagec-calibration-inventory",
        capture_requests=fx.capture_requests,
    )
    with pytest.raises(SchemaValidationError, match="sole preregistered split source"):
        build_diagnostic_study_plan(
            chain=fx.chain,
            inventory=other_inventory,
            plan_id="other-inventory-plan",
            created_at="2026-08-08T08:30:00Z",
        )


def test_regression_plan_id_cannot_reuse_transitive_base_artifact_id(
    fx: Fixture,
) -> None:
    transitive_base_ref = next(
        reference
        for reference in fx.base.artifact_refs
        if reference != fx.inventory.artifact_ref
    )
    with pytest.raises(SchemaValidationError, match="plan_id collides"):
        build_diagnostic_study_plan(
            chain=fx.chain,
            inventory=fx.inventory,
            plan_id=transitive_base_ref.artifact_id,
            created_at="2026-08-08T08:30:00Z",
        )


def test_regression_plan_rejects_base_ref_cloned_from_capture_content(
    fx: Fixture,
) -> None:
    value = base_value(fx.inventory)
    value["design"]["input_artifacts"][0] = ref_value(
        ref(
            "base-ref-cloned-from-capture",
            fx.capture_requests[0].raw_bytes,
            STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
        )
    )
    base = load_diagnostic_preregistration(canonical_json_bytes(value))
    chain = make_chain(base)
    with pytest.raises(SchemaValidationError, match=r"plan refs\.sha256"):
        build_diagnostic_study_plan(
            chain=chain,
            inventory=fx.inventory,
            plan_id="content-collision-plan",
            created_at="2026-08-08T08:30:00Z",
        )


@pytest.mark.parametrize("collision_kind", ["other-study-request", "capture-request"])
def test_regression_plan_rejects_reused_or_capture_colliding_study_request_id(
    fx: Fixture,
    collision_kind: str,
) -> None:
    replacement = (
        fx.plan.cases[1].study_request_id
        if collision_kind == "other-study-request"
        else fx.capture_requests[1].artifact_ref.artifact_id
    )
    raw = mutate(
        fx.plan.raw_bytes,
        lambda value: value["ordered_case_requests"][0].__setitem__(
            "study_request_id", replacement
        ),
    )
    with pytest.raises(SchemaValidationError):
        load_diagnostic_study_plan(
            raw,
            chain=fx.chain,
            inventory=fx.inventory,
        )


@pytest.mark.parametrize(
    ("target_groups", "target_rows", "message"),
    [
        (159, DIAGNOSTIC_CASE_COUNT, "160 groups"),
        (DIAGNOSTIC_GROUP_COUNT, 479, "480 cases"),
    ],
)
def test_plan_rejects_noncanonical_preregistered_sample_size(
    fx: Fixture,
    target_groups: int,
    target_rows: int,
    message: str,
) -> None:
    base = load_diagnostic_preregistration(
        canonical_json_bytes(
            base_value(
                fx.inventory,
                target_groups=target_groups,
                target_enrolled_rows=target_rows,
            )
        )
    )
    chain = make_chain(base)
    with pytest.raises(SchemaValidationError, match=message):
        build_diagnostic_study_plan(
            chain=chain,
            inventory=fx.inventory,
            plan_id="wrong-sample-plan",
            created_at="2026-08-08T08:30:00Z",
        )


def test_plan_rejects_forged_carrier_and_sealed_chain(fx: Fixture) -> None:
    forged = replace(fx.inventory, study_id="other-study")
    with pytest.raises(SchemaValidationError, match="fresh exact-byte replay"):
        build_diagnostic_study_plan(
            chain=fx.chain,
            inventory=forged,
            plan_id="forged-inventory-plan",
            created_at="2026-08-08T08:30:00Z",
        )
    with pytest.raises(SchemaValidationError, match="exact DiagnosticPreregistrationChain"):
        build_diagnostic_study_plan(
            chain=object(),  # type: ignore[arg-type]
            inventory=fx.inventory,
            plan_id="legacy-adapter-plan",
            created_at="2026-08-08T08:30:00Z",
        )

    sealed = make_chain(fx.base)
    sealed.record_outcome_access(
        canonical_json_bytes(
            {
                "schema_version": DIAGNOSTIC_STUDY_OUTCOME_INDEX_SCHEMA,
                "outcome_index_id": "diagnostic-outcome-index",
                "diagnostic_preregistration": ref_value(fx.base.artifact_ref),
                "pre_outcome_chain_sha256": sealed.pre_outcome_chain_sha256,
                "timing": {
                    "execution_started_at": "2026-08-08T09:00:00Z",
                    "execution_completed_at": "2026-08-08T11:00:00Z",
                    "accessed_at": "2026-08-08T11:01:00Z",
                },
                "boundary": {
                    "scope": "STRUCTURE_ONLY",
                    "execution_authorization": "OPEN_NOT_PROVIDED",
                    "terminal_row_coordinator": "OPEN_NOT_PROVIDED",
                    "failed_row_semantics": "OPEN_NOT_PROVIDED",
                    "diagnostic_nonreporting_disposition": "OPEN_NOT_PROVIDED",
                    "retry_evidence": "NOT_ATTESTED",
                    "trusted_time": "NOT_PROVIDED",
                    "durable_one_use": "NOT_PROVIDED",
                    "worm": "NOT_PROVIDED",
                    "evidence_packet_v2": "FORBIDDEN",
                    "claim_promotion": "FORBIDDEN",
                },
            }
        )
    )
    with pytest.raises(SchemaValidationError, match="pre-outcome"):
        build_diagnostic_study_plan(
            chain=sealed,
            inventory=fx.inventory,
            plan_id="sealed-chain-plan",
            created_at="2026-08-08T08:30:00Z",
        )


def test_study_request_separately_binds_envelope_and_capture_request(fx: Fixture) -> None:
    request = fx.study_request
    assert request.payload["schema_version"] == DIAGNOSTIC_STUDY_REQUEST_SCHEMA
    assert request.artifact_ref.media_type == DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE
    assert request.request_id == fx.plan.cases[0].study_request_id
    assert request.payload["request_id"] == fx.plan.cases[0].study_request_id
    assert request.capture_request.media_type == STAGEC_CAPTURE_REQUEST_MEDIA_TYPE
    assert request.capture_request != request.artifact_ref
    assert request.payload["capture_request"] == ref_value(
        fx.capture_requests[0].artifact_ref
    )
    assert request.payload["diagnostic_study_plan"] == ref_value(fx.plan.artifact_ref)
    assert request.artifact_refs == (fx.plan.artifact_ref, *fx.plan.artifact_refs)
    assert request.payload["case_binding"]["execution_ordinal"] == 1
    assert request.payload["case_binding"]["case_id"] == fx.plan.cases[0].case_id
    assert request.payload["retry_policy"] == {
        "maximum_attempts": 1,
        "retry": "FORBIDDEN",
        "replacement": "FORBIDDEN",
        "durable_enforcement": "EXTERNAL_REQUIRED_NOT_PROVIDED",
    }
    assert request.payload["boundary"]["worker_authorization"] == "NOT_CREATED"
    assert request.payload["authority"]["execution_authority"] == "NOT_GRANTED"
    assert "worker_authorization" not in request.payload


def test_regression_request_id_cannot_reuse_transitive_plan_dependency(
    fx: Fixture,
) -> None:
    transitive_dependency = next(
        reference
        for reference in fx.plan.artifact_refs
        if reference not in {
            fx.base.artifact_ref,
            fx.inventory.artifact_ref,
            fx.capture_requests[0].artifact_ref,
        }
    )
    raw = mutate(
        fx.study_request.raw_bytes,
        lambda value: value.__setitem__(
            "request_id", transitive_dependency.artifact_id
        ),
    )
    with pytest.raises(SchemaValidationError, match="plan-frozen derived ID"):
        load_diagnostic_study_request(
            raw,
            chain=fx.chain,
            plan=fx.plan,
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value["diagnostic_study_plan"].__setitem__(
            "sha256", "0" * 64
        ),
        lambda value: value["capture_request"].__setitem__("sha256", "0" * 64),
        lambda value: value["capture_request"].__setitem__(
            "media_type", DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE
        ),
        lambda value: value["case_binding"].__setitem__("case_id", "other-case"),
        lambda value: value["case_binding"].__setitem__(
            "frozen_variant", CLEAN_ABSENT
        ),
        lambda value: value["execution_window"].__setitem__(
            "window_start", "2026-08-08T09:01:00Z"
        ),
        lambda value: value["retry_policy"].__setitem__("maximum_attempts", 2),
        lambda value: value["authority"].__setitem__(
            "execution_authority", "GRANTED"
        ),
        lambda value: value.__setitem__("worker_authorization", {}),
    ],
)
def test_study_request_rejects_rebinding_and_authority_mutations(
    fx: Fixture,
    change,
) -> None:
    with pytest.raises(SchemaValidationError):
        load_diagnostic_study_request(
            mutate(fx.study_request.raw_bytes, change),
            chain=fx.chain,
            plan=fx.plan,
        )


def test_study_request_requires_known_case_and_pre_window_time(fx: Fixture) -> None:
    with pytest.raises(SchemaValidationError, match="exactly one frozen"):
        build_diagnostic_study_request(
            chain=fx.chain,
            plan=fx.plan,
            case_id="unknown-case",
            created_at="2026-08-08T08:40:00Z",
        )
    with pytest.raises(SchemaValidationError, match="after the exact Study plan"):
        build_diagnostic_study_request(
            chain=fx.chain,
            plan=fx.plan,
            case_id=fx.plan.cases[0].case_id,
            created_at=fx.plan.created_at,
        )
    with pytest.raises(SchemaValidationError, match="before the execution window"):
        build_diagnostic_study_request(
            chain=fx.chain,
            plan=fx.plan,
            case_id=fx.plan.cases[0].case_id,
            created_at=fx.plan.execution_window_start,
        )


def test_study_request_rejects_forged_plan_and_identifier_collision(fx: Fixture) -> None:
    forged = replace(fx.plan, study_id="other-study")
    with pytest.raises(SchemaValidationError, match="fresh exact-byte replay"):
        build_diagnostic_study_request(
            chain=fx.chain,
            plan=forged,
            case_id=fx.plan.cases[0].case_id,
            created_at="2026-08-08T08:40:00Z",
        )


def test_loaders_snapshot_mutable_input_and_reject_noncanonical_plan_request(
    fx: Fixture,
) -> None:
    loaded_plan = load_diagnostic_study_plan(
        bytearray(fx.plan.raw_bytes),
        chain=fx.chain,
        inventory=fx.inventory,
    )
    loaded_request = load_diagnostic_study_request(
        bytearray(fx.study_request.raw_bytes),
        chain=fx.chain,
        plan=fx.plan,
    )
    assert type(loaded_plan.raw_bytes) is bytes
    assert type(loaded_request.raw_bytes) is bytes

    with pytest.raises(SchemaValidationError, match="canonical"):
        load_diagnostic_study_plan(
            fx.plan.raw_bytes + b"\n",
            chain=fx.chain,
            inventory=fx.inventory,
        )
    with pytest.raises(SchemaValidationError, match="canonical"):
        load_diagnostic_study_request(
            fx.study_request.raw_bytes + b"\n",
            chain=fx.chain,
            plan=fx.plan,
        )


def test_schema_constants_are_distinct_and_no_legacy_media_alias_exists() -> None:
    assert len(
        {
            DIAGNOSTIC_SPLIT_INVENTORY_SCHEMA,
            DIAGNOSTIC_STUDY_PLAN_SCHEMA,
            DIAGNOSTIC_STUDY_REQUEST_SCHEMA,
            STAGEC_CAPTURE_REQUEST_SCHEMA,
        }
    ) == 4
    assert len(
        {
            DIAGNOSTIC_SPLIT_INVENTORY_MEDIA_TYPE,
            DIAGNOSTIC_STUDY_PLAN_MEDIA_TYPE,
            DIAGNOSTIC_STUDY_REQUEST_MEDIA_TYPE,
            STAGEC_CAPTURE_REQUEST_MEDIA_TYPE,
        }
    ) == 4
    assert CLEAN_NULL_ABSENT != CLEAN_ABSENT
