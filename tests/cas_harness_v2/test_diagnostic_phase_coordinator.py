from __future__ import annotations

import copy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import struct
import sys
import time

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TEST_DIR = Path(__file__).resolve().parent
for candidate in (SRC, TEST_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from cas_harness_v2._strict_json import (  # noqa: E402
    canonical_json_bytes,
    canonical_sha256,
    sha256_bytes,
)
from cas_harness_v2._validation import ArtifactRef  # noqa: E402
from cas_harness_v2.diagnostic_execution_protocol import (  # noqa: E402
    DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
    DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
    DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE,
    DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA,
)
from cas_harness_v2.diagnostic_lifecycle import (  # noqa: E402
    build_diagnostic_shared_plan_replay_context,
)
from cas_harness_v2.diagnostic_preregistration import (  # noqa: E402
    DiagnosticPreregistrationChain,
    load_diagnostic_preregistration,
)
from cas_harness_v2.diagnostic_phase_coordinator import (  # noqa: E402
    DIAGNOSTIC_ACTIVATION_VECTOR_MEDIA_TYPE,
    DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE,
    PHASE_OPEN,
    PHASE_OUTCOME_ACCESSED,
    PHASE_RECONCILED_CLEAN,
    PHASE_RECONCILED_REJECTED,
    DiagnosticPhaseConflict,
    DiagnosticPhaseCoordinator,
    DiagnosticPhaseIntegrityError,
    DiagnosticPhaseValidationError,
    build_diagnostic_phase_registration,
    build_diagnostic_phase_store_binding,
    load_diagnostic_phase_registration,
    load_diagnostic_phase_store_binding,
    replay_diagnostic_phase_activation_admission_projection,
    replay_diagnostic_phase_outcome_access_projection,
    replay_diagnostic_phase_reconciliation_projection,
    replay_diagnostic_phase_registration_projection,
)
from cas_harness_v2.diagnostic_study_protocol import (  # noqa: E402
    build_diagnostic_split_inventory,
    build_diagnostic_study_plan,
)
from cas_harness_v2.stagec_outcome import (  # noqa: E402
    STAGEC_AUTHORIZATION_PROJECTION_MEDIA_TYPE,
    STAGEC_CAPTURE_INDEX_MEDIA_TYPE,
    STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE,
    STAGEC_LOCAL_CAPTURE_ARCHIVE_SCHEMA,
)
from test_diagnostic_execution_protocol import (  # noqa: E402
    ARTIFACT_IDS,
    error as terminal_error,
)
from test_diagnostic_study_protocol import (  # noqa: E402
    amendment_value,
    base_value,
    make_capture_requests,
)


TENANT = "tenant-diagnostic-phase"


def mutate(raw: bytes, change) -> bytes:
    value = json.loads(raw)
    change(value)
    return canonical_json_bytes(value)


def ref(artifact_id: str, raw: bytes, media_type: str) -> ArtifactRef:
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


def plain(value) -> object:
    return json.loads(canonical_json_bytes(value))


def _array_ref_value(
    artifact_id: str,
    raw: bytes,
    *,
    dtype: str,
    shape: list[int],
    role: str,
    layer_index: int | None = None,
    module_path: str | None = None,
) -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "byte_length": len(raw),
        "byte_order": "little",
        "dtype": dtype,
        "durability_status": "NOT_DURABLY_RETAINED",
        "format": "RAW C-ORDER ARRAY BYTES / NO HEADER / NO PICKLE",
        "layer_index": layer_index,
        "layout": "C_CONTIGUOUS",
        "media_type": DIAGNOSTIC_ACTIVATION_VECTOR_MEDIA_TYPE,
        "module_path": module_path,
        "retention_location": "IN_MEMORY",
        "role": role,
        "sha256": sha256_bytes(raw),
        "shape": shape,
    }


def _directory_identity() -> dict[str, object]:
    return {
        "device": 1,
        "file_attributes": None,
        "inode": 1,
        "mode_type": 16384,
        "reparse_tag": None,
    }


def _file_identity(byte_length: int, inode: int) -> dict[str, object]:
    return {
        "byte_length": byte_length,
        "ctime_ns": 1_000_000_000 + inode,
        "device": 1,
        "file_attributes": None,
        "inode": inode,
        "link_count": 1,
        "mode_type": 32768,
        "mtime_ns": 1_000_000_000 + inode,
        "permission_status": "READ_ONLY_PERMISSION_BITS_OBSERVED",
        "reparse_tag": None,
    }


def capture_archive(authorization, artifact_ids, ordinal: int, capture_request):
    context = authorization.payload["execution_context"]
    case = context["case_binding"]
    capture_request_ref = capture_request.artifact_ref
    assert ref_value(capture_request_ref) == plain(
        context["study_binding"]["stagec_capture_request"]
    )
    authorization_projection_raw = canonical_json_bytes(
        {
            "schema_version": "cas_harness.stagec.authorization_projection.v1",
            "scope": "STRUCTURE_ONLY",
            "authority_status": "NON_AUTHORITY / DOES_NOT_AUTHORIZE_MODEL_EXECUTION",
            "request_sha256": capture_request_ref.sha256,
            "plan_id": context["study_binding"]["diagnostic_study_plan"]["artifact_id"],
            "study_id": case["study_id"],
            "case_id": case["case_id"],
            "invocation_id": case["invocation_id"],
        }
    )
    authorization_projection_ref = ref(
        artifact_ids["authorization_projection"],
        authorization_projection_raw,
        STAGEC_AUTHORIZATION_PROJECTION_MEDIA_TYPE,
    )
    variant = case["frozen_variant"]
    base = {
        "ADVERSARIAL_PRESENT": 2.0,
        "CLEAN_ABSENT": -2.0,
        "CLEAN_NULL_ABSENT": -1.5,
    }[variant]
    input_ids = ordinal.to_bytes(8, "little", signed=True)
    attention_mask = (10_000 + ordinal).to_bytes(8, "little", signed=True)
    target_body = struct.pack("<f", base + ordinal / 10_000.0) * 4864
    wrong_body = struct.pack("<f", base + 0.25 + ordinal / 10_000.0) * 4864
    input_ref = _array_ref_value(
        artifact_ids["input_ids"], input_ids, dtype="<i8", shape=[1, 1], role="input_ids"
    )
    mask_ref = _array_ref_value(
        artifact_ids["attention_mask"],
        attention_mask,
        dtype="<i8",
        shape=[1, 1],
        role="attention_mask",
    )
    target_ref = _array_ref_value(
        artifact_ids["target_vector"],
        target_body,
        dtype="<f4",
        shape=[4864],
        role="target_final_token_activation",
        layer_index=18,
        module_path="model.layers[18].mlp.down_proj",
    )
    wrong_ref = _array_ref_value(
        artifact_ids["wrong_layer_vector"],
        wrong_body,
        dtype="<f4",
        shape=[4864],
        role="wrong_layer_final_token_activation",
        layer_index=0,
        module_path="model.layers[0].mlp.down_proj",
    )
    capture_index_raw = canonical_json_bytes(
        {
            "schema_version": "cas_harness.stagec.capture_index.v1",
            "scope": "STRUCTURE_ONLY",
            "retention": {
                "location": "IN_MEMORY",
                "durability_status": "NOT_DURABLY_RETAINED",
            },
            "association": {
                "study_id": case["study_id"],
                "case_id": case["case_id"],
                "split_id": case["split_id"],
                "base_intent_group_id": case["base_intent_group_id"],
                "frozen_variant": variant,
                "frozen_label": case["frozen_label"],
                "invocation_id": case["invocation_id"],
                "plan_id": context["study_binding"]["diagnostic_study_plan"]["artifact_id"],
                "request_artifact": ref_value(capture_request_ref),
                "authorization_projection_artifact": ref_value(
                    authorization_projection_ref
                ),
            },
            "identity": {},
            "prompt": {},
            "tokens": {
                "input_ids_artifact": input_ref,
                "attention_mask_artifact": mask_ref,
                "sequence_length": 1,
                "final_prompt_token_index": 0,
                "final_prompt_token_id": ordinal,
                "truncation_enabled": False,
                "truncation_occurred": False,
            },
            "activations": {
                "target": {
                    "array_artifact": target_ref,
                    "layer_index": 18,
                    "module_path": "model.layers[18].mlp.down_proj",
                    "source_dtype": "float32",
                    "source_device": "cpu",
                    "source_autocast_enabled": False,
                },
                "wrong_layer": {
                    "array_artifact": wrong_ref,
                    "layer_index": 0,
                    "module_path": "model.layers[0].mlp.down_proj",
                    "source_dtype": "float32",
                    "source_device": "cpu",
                    "source_autocast_enabled": False,
                },
            },
            "logits": {},
            "hooks": {},
            "endpoint_checks": {},
            "telemetry": {},
        }
    )
    capture_index_ref = ref(
        artifact_ids["capture_index"],
        capture_index_raw,
        STAGEC_CAPTURE_INDEX_MEDIA_TYPE,
    )
    exact_members = (
        ("request_artifact", ref_value(capture_request_ref), capture_request.raw_bytes),
        (
            "authorization_projection_artifact",
            ref_value(authorization_projection_ref),
            authorization_projection_raw,
        ),
        ("capture_index_artifact", ref_value(capture_index_ref), capture_index_raw),
        ("input_ids", input_ref, input_ids),
        ("attention_mask", mask_ref, attention_mask),
        ("target_vector", target_ref, target_body),
        ("wrong_layer_vector", wrong_ref, wrong_body),
    )
    rows = []
    member_bodies = {}
    for inode, (role, reference, body) in enumerate(exact_members, start=10):
        digest = str(reference["sha256"]).lower()
        rows.append(
            {
                "archive_copy_status": "LOCAL_FILE_COPY_RETAINED_AND_REVALIDATED",
                "file_identity": _file_identity(len(body), inode),
                "path_ancestors": [
                    {"identity": _directory_identity(), "relative_path": "."},
                    {"identity": _directory_identity(), "relative_path": "objects"},
                    {
                        "identity": _directory_identity(),
                        "relative_path": "objects/sha256",
                    },
                    {
                        "identity": _directory_identity(),
                        "relative_path": f"objects/sha256/{digest[:2]}",
                    },
                ],
                "ref": reference,
                "relative_path": f"objects/sha256/{digest[:2]}/{digest[2:]}",
                "role": role,
            }
        )
        member_bodies[role] = body
    manifest_raw = canonical_json_bytes(
        {
            "schema_version": STAGEC_LOCAL_CAPTURE_ARCHIVE_SCHEMA,
            "authority": {
                "scope": "LOCAL_SINGLE_HOST_FILE_BACKED",
                "write_mode": "CREATE_ONLY",
                "file_sync": "FILE_FSYNC_AND_REREAD_VERIFIED_AT_CREATION",
                "permission_status": "READ_ONLY_PERMISSION_BITS_OBSERVED",
                "worm_authority": "NOT_ESTABLISHED",
                "trusted_time": "NOT_ESTABLISHED",
                "external_anchor": "NOT_ESTABLISHED",
                "capture_provenance": "NOT_CONFERRED_BY_ARCHIVE_REPLAY",
                "execution_authority": "NOT_GRANTED",
                "relocatability": "SAME_ABSOLUTE_PATH_AND_FILE_IDENTITIES_ONLY",
                "membership_scope": "MANIFEST_LISTED_MEMBERS_ONLY_CLOSED_WORLD_NOT_ESTABLISHED",
            },
            "source_retention_boundary": (
                "CAPTURE-TIME IN_MEMORY / NOT_DURABLY_RETAINED LABELS PRESERVED; "
                "THIS MANIFEST BINDS A SEPARATE LOCAL FILE COPY"
            ),
            "relocatability_boundary": "SAME_ABSOLUTE_PATH_AND_FILE_IDENTITIES_ONLY",
            "manifest_membership_boundary": (
                "MANIFEST_LISTED_MEMBERS_ONLY / CLOSED_WORLD_DIRECTORY CONTENT NOT ESTABLISHED"
            ),
            "manifest_publication_boundary": (
                "THE READ_ONLY REREAD-VERIFIED MANIFEST IS THE LOCAL PUBLICATION POINT; "
                "A STOP AFTER PUBLICATION MAY LEAVE AN INTERNALLY VALID ORPHAN"
            ),
            "member_directory_fsync_status": "PERFORMED",
            "root_path": context["artifact_expectations"]["archive"]["absolute_root"],
            "root_identity": _directory_identity(),
            "association": {
                "study_id": case["study_id"],
                "case_id": case["case_id"],
                "split_id": case["split_id"],
                "base_intent_group_id": case["base_intent_group_id"],
                "frozen_variant": variant,
                "frozen_label": case["frozen_label"],
                "invocation_id": case["invocation_id"],
                "plan_id": context["study_binding"]["diagnostic_study_plan"]["artifact_id"],
            },
            "members": rows,
        }
    )
    manifest_ref = ref(
        "stagec-local-archive-"
        + sha256_bytes(canonical_json_bytes(ref_value(capture_index_ref))).lower(),
        manifest_raw,
        STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE,
    )
    return (manifest_ref, manifest_raw), member_bodies


def completed_artifacts(authorization, artifact_ids, archive_manifest):
    context = authorization.payload["execution_context"]
    manifest_ref, _manifest_raw = archive_manifest
    admission_raw = canonical_json_bytes(
        {
            "schema_version": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
            "admission_id": artifact_ids["archive_admission"],
            "authorization": ref_value(authorization.artifact_ref),
            "execution_context_sha256": authorization.execution_context_sha256,
            "case_binding": plain(context["case_binding"]),
            "archive_expectation_sha256": canonical_sha256(
                context["artifact_expectations"]["archive"]
            ),
            "archive_manifest": ref_value(manifest_ref),
            "observation": "SERIALIZED_BINDING_ONLY_FACTORY_ORIGIN_EXTERNAL_REQUIRED",
            "boundary": {
                "serialized_replay": "STRUCTURAL_BINDING_ONLY",
                "factory_origin": "EXTERNAL_REQUIRED_NOT_PROVIDED_BY_SERIALIZED_BYTES",
                "local_archive_replay": "EXTERNAL_REQUIRED_NOT_PROVIDED_BY_SERIALIZED_BYTES",
                "execution_authority": "NOT_GRANTED",
            },
            "authority": plain(authorization.payload["authority"]),
            "governance": plain(authorization.payload["governance"]),
        }
    )
    admission_ref = ref(
        artifact_ids["archive_admission"],
        admission_raw,
        DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
    )
    output_raw = canonical_json_bytes(
        {
            "schema_version": DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA,
            "output_id": artifact_ids["child_output"],
            "authorization": ref_value(authorization.artifact_ref),
            "execution_context_sha256": authorization.execution_context_sha256,
            "case_binding": plain(context["case_binding"]),
            "archive_admission": ref_value(admission_ref),
            "output_role": "DIAGNOSTIC_STAGEC_CHILD_OUTPUT",
            "boundary": {
                "serialized_replay": "STRUCTURAL_BINDING_ONLY",
                "live_archive_admission": "EXTERNAL_REQUIRED_NOT_PROVIDED_BY_SERIALIZED_BYTES",
                "scientific_assessment": "NOT_PERFORMED",
                "execution_authority": "NOT_GRANTED",
            },
            "authority": plain(authorization.payload["authority"]),
            "governance": plain(authorization.payload["governance"]),
        }
    )
    output_ref = ref(
        artifact_ids["child_output"],
        output_raw,
        DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE,
    )
    return {
        "archive_admission": (admission_ref, admission_raw),
        "child_output": (output_ref, output_raw),
    }


def bound_phase_dependencies(root: Path, *, suffix: str, tenant: str):
    started = time.perf_counter()
    root.mkdir(parents=True, exist_ok=True)
    store_binding = build_diagnostic_phase_store_binding(
        binding_id=f"diagnostic-phase-store-{suffix}",
        created_at="2026-08-08T08:05:00Z",
        database_path=root / "phase.sqlite3",
    )
    rule_raw = canonical_json_bytes(
        {
            "schema_version": "cas_harness_v2.diagnostic_calibration_rule.v1",
            "rule_id": f"diagnostic-calibration-rule-{suffix}",
            "created_at": "2026-08-08T08:04:00Z",
            "structural_test_only": True,
        }
    )
    rule_ref = ref(
        f"diagnostic-calibration-rule-{suffix}",
        rule_raw,
        DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE,
    )
    capture_requests = make_capture_requests()
    inventory = build_diagnostic_split_inventory(
        inventory_id=f"stagec-calibration-inventory-phase-{suffix}",
        capture_requests=capture_requests,
    )
    base = load_diagnostic_preregistration(canonical_json_bytes(base_value(inventory)))
    chain = DiagnosticPreregistrationChain(base)
    identity = amendment_value(
        base,
        amendment_id=f"AMD-PHASE-{suffix}-001",
        created_at="2026-08-08T08:10:00Z",
        previous_sha256=None,
        change_class="EXECUTION_IDENTITY_ADDITION",
    )
    identity["changes"]["additional_artifacts"].extend(
        [ref_value(store_binding.artifact_ref), ref_value(rule_ref)]
    )
    identity_artifact = chain.append_amendment(canonical_json_bytes(identity))
    window = amendment_value(
        base,
        amendment_id=f"AMD-PHASE-{suffix}-002",
        created_at="2026-08-08T08:20:00Z",
        previous_sha256=identity_artifact.sha256,
        change_class="EXECUTION_WINDOW",
    )
    chain.append_amendment(canonical_json_bytes(window))
    plan = build_diagnostic_study_plan(
        chain=chain,
        inventory=inventory,
        plan_id=f"stagec-diagnostic-plan-phase-{suffix}",
        created_at="2026-08-08T08:30:00Z",
    )
    from cas_harness_v2.diagnostic_execution_protocol import (
        build_diagnostic_stagec_execution_contract,
    )

    contract = build_diagnostic_stagec_execution_contract(
        chain=chain,
        plan=plan,
        contract_id=f"diagnostic-stagec-contract-phase-{suffix}",
        created_at="2026-08-08T08:35:00Z",
    )
    shared = build_diagnostic_shared_plan_replay_context(
        chain=chain,
        plan=plan,
        execution_contract=contract,
    )
    requests = tuple(
        shared.build_study_request(
            case_id=case.case_id,
            created_at="2026-08-08T08:40:00Z",
        )
        for case in shared.plan.cases
    )
    registration = build_diagnostic_phase_registration(
        registration_id=f"diagnostic-phase-registration-{suffix}",
        phase_id=f"diagnostic-calibration-phase-{suffix}",
        registered_at="2026-08-08T08:41:00Z",
        tenant_id=tenant,
        shared_plan_context=shared,
        study_requests=requests,
        store_binding=store_binding,
    )
    assert time.perf_counter() - started < 30.0
    return shared, requests, registration, store_binding, rule_ref


@pytest.fixture(scope="module")
def phase_dependencies(tmp_path_factory):
    return bound_phase_dependencies(
        tmp_path_factory.mktemp("phase-registration"),
        suffix="registration",
        tenant=TENANT,
    )


@pytest.fixture(scope="module")
def rejected_phase(tmp_path_factory):
    shared, _requests, registration, _binding, _rule = bound_phase_dependencies(
        tmp_path_factory.mktemp("phase-rejected"),
        suffix="rejected",
        tenant="tenant-phase-rejected",
    )
    counter = {"value": 0}

    def unique_nonce(count: int) -> bytes:
        counter["value"] += 1
        return counter["value"].to_bytes(count, "big")

    coordinator = DiagnosticPhaseCoordinator(
        registration=registration,
        shared_plan_context=shared,
        nonce_factory=unique_nonce,
    )
    population_started = time.perf_counter()
    for ordinal, request in enumerate(registration.study_requests, start=1):
        suffix = f"{ordinal:03d}"
        artifact_ids = {
            key: f"phase-{key.replace('_', '-')}-{suffix}"
            for key in ARTIFACT_IDS
        }
        coordinator.reject_preauthorization(
            execution_ordinal=ordinal,
            binding_id=f"phase-binding-{suffix}",
            binding_created_at="2026-08-08T08:45:00Z",
            assigned_worker_id="diagnostic-worker-phase",
            archive_root=f"C:/cas-harness/stagec/phase-child-{suffix}",
            artifact_ids=artifact_ids,
            terminal_at="2026-08-08T08:49:00Z",
            error=terminal_error("INPUT_REJECTED"),
            operation_id=f"phase-preauth-reject-{suffix}",
        )
    population_seconds = time.perf_counter() - population_started
    reconciliation_started = time.perf_counter()
    reconciliation = coordinator.reconcile_and_seal(
        reconciliation_id="diagnostic-phase-reconciliation-rejected-001",
        closed_at="2026-08-08T08:50:00Z",
    )
    reconciliation_seconds = time.perf_counter() - reconciliation_started
    assert population_seconds < 120.0
    assert reconciliation_seconds < 60.0
    return coordinator, reconciliation


@pytest.fixture(scope="module")
def clean_phase(tmp_path_factory):
    shared, _requests, registration, _binding, _rule = bound_phase_dependencies(
        tmp_path_factory.mktemp("phase-clean"),
        suffix="clean",
        tenant="tenant-phase-clean",
    )
    counter = {"value": 10_000}

    def unique_nonce(count: int) -> bytes:
        counter["value"] += 1
        return counter["value"].to_bytes(count, "big")

    coordinator = DiagnosticPhaseCoordinator(
        registration=registration,
        shared_plan_context=shared,
        nonce_factory=unique_nonce,
    )
    capture_requests = make_capture_requests()
    population_started = time.perf_counter()
    for ordinal, request in enumerate(registration.study_requests, start=1):
        suffix = f"{ordinal:03d}"
        artifact_ids = {
            key: f"clean-{key.replace('_', '-')}-{suffix}"
            for key in ARTIFACT_IDS
        }
        issuance = coordinator.issue_attempt(
            execution_ordinal=ordinal,
            binding_id=f"clean-binding-{suffix}",
            binding_created_at="2026-08-08T08:45:00Z",
            assigned_worker_id="diagnostic-worker-clean",
            archive_root=f"C:/cas-harness/stagec/clean-child-{suffix}",
            artifact_ids=artifact_ids,
            issued_at="2026-08-08T08:50:00Z",
            expires_at="2026-08-08T11:00:00Z",
            operation_id=f"clean-issue-{suffix}",
        )
        coordinator.consume_attempt(
            attempt_subject_sha256=issuance.snapshot.attempt_subject_sha256,
            run_nonce_b64url=issuance.run_nonce_b64url,
            worker_started_at="2026-08-08T09:05:00Z",
            operation_id=f"clean-consume-{suffix}",
        )
        archive_manifest, archive_member_bodies = capture_archive(
            issuance.authorization,
            artifact_ids,
            ordinal,
            capture_requests[ordinal - 1],
        )
        coordinator.build_and_record_terminal(
            attempt_subject_sha256=issuance.snapshot.attempt_subject_sha256,
            terminal_at="2026-08-08T09:06:00Z",
            terminal_status="COMPLETED",
            terminal_phase="COMPLETE",
            invocation_certainty="EXACTLY_ONE",
            produced_artifacts=completed_artifacts(
                issuance.authorization, artifact_ids, archive_manifest
            ),
            archive_manifest=archive_manifest,
            archive_member_bodies=archive_member_bodies,
            error=None,
            operation_id=f"clean-terminal-{suffix}",
        )
    population_seconds = time.perf_counter() - population_started
    reconciliation_started = time.perf_counter()
    reconciliation = coordinator.reconcile_and_seal(
        reconciliation_id="diagnostic-phase-reconciliation-clean-001",
        closed_at="2026-08-08T09:07:00Z",
    )
    reconciliation_seconds = time.perf_counter() - reconciliation_started
    assert population_seconds < 180.0
    assert reconciliation_seconds < 60.0
    return coordinator, reconciliation


def test_store_binding_replays_identity_and_observed_sqlite_pragmas(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "binding.sqlite3"
    binding = build_diagnostic_phase_store_binding(
        binding_id="diagnostic-phase-store-binding-light",
        created_at="2026-08-08T08:05:00Z",
        database_path=database_path,
    )
    assert load_diagnostic_phase_store_binding(binding.raw_bytes) == binding
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.close()
    with pytest.raises(
        DiagnosticPhaseIntegrityError, match="SQLite identity changed"
    ):
        load_diagnostic_phase_store_binding(binding.raw_bytes)

    swap_path = tmp_path / "swap.sqlite3"
    swapped = build_diagnostic_phase_store_binding(
        binding_id="diagnostic-phase-store-binding-swap",
        created_at="2026-08-08T08:05:00Z",
        database_path=swap_path,
    )
    original_path = tmp_path / "swap-original.sqlite3"
    swap_path.replace(original_path)
    sqlite3.connect(swap_path).close()
    with pytest.raises(
        DiagnosticPhaseIntegrityError, match="filesystem identity changed"
    ):
        load_diagnostic_phase_store_binding(swapped.raw_bytes)

    counterfeit_path = tmp_path / "counterfeit.sqlite3"
    counterfeit = build_diagnostic_phase_store_binding(
        binding_id="diagnostic-phase-store-binding-counterfeit",
        created_at="2026-08-08T08:05:00Z",
        database_path=counterfeit_path,
    )
    connection = sqlite3.connect(counterfeit_path)
    connection.execute("CREATE TABLE diagnostic_phases (counterfeit TEXT)")
    connection.close()
    with pytest.raises(
        DiagnosticPhaseIntegrityError, match="counterfeit or partial"
    ):
        load_diagnostic_phase_store_binding(counterfeit.raw_bytes)


def test_registration_is_exact_plan_ordered_480_by_160(phase_dependencies) -> None:
    shared, requests, registration, store_binding, _rule = phase_dependencies
    assert len(registration.study_requests[0].artifact_refs) == 491
    assert {
        row["study_request_artifact_ref_count"]
        for row in registration.payload["ordered_attempts"]
    } == {491}
    assert all(
        len(row["study_request_ordered_artifact_refs_sha256"]) == 64
        for row in registration.payload["ordered_attempts"]
    )
    assert registration.ordered_subjects == tuple(
        row["attempt_subject_sha256"]
        for row in registration.payload["ordered_attempts"]
    )
    assert len(registration.ordered_subjects) == len(set(registration.ordered_subjects)) == 480
    assert len({case.base_intent_group_id for case in shared.plan.cases}) == 160
    assert tuple(
        row["execution_ordinal"] for row in registration.payload["ordered_attempts"]
    ) == tuple(range(1, 481))
    assert tuple(
        row["frozen_variant"]
        for row in registration.payload["ordered_attempts"][:3]
    ) == ("ADVERSARIAL_PRESENT", "CLEAN_ABSENT", "CLEAN_NULL_ABSENT")
    replayed = load_diagnostic_phase_registration(
        bytearray(registration.raw_bytes),
        shared_plan_context=shared,
        study_requests=requests,
        store_binding=store_binding,
    )
    assert replayed == registration
    assert registration.payload["boundary"]["evidence_packet_v2"] == "FORBIDDEN"
    assert registration.payload["boundary"]["evaluation_execution"] == "NOT_AUTHORIZED"
    assert registration.payload["boundary"]["product_route"] == "FORBIDDEN"
    assert registration.payload["boundary"]["public_release"] is False
    with pytest.raises(
        DiagnosticPhaseValidationError, match="dataclass differs"
    ):
        replay_diagnostic_phase_registration_projection(
            replace(registration, tenant_id="forged-tenant")
        )
    for forged in (
        replace(registration, raw_bytes=bytearray(registration.raw_bytes)),
        replace(registration, payload=dict(registration.payload)),
        replace(
            registration,
            store_binding=replace(
                registration.store_binding,
                raw_bytes=bytearray(registration.store_binding.raw_bytes),
            ),
        ),
        replace(
            registration,
            store_binding=replace(
                registration.store_binding,
                payload=dict(registration.store_binding.payload),
            ),
        ),
        replace(
            registration,
            study_requests=(
                replace(registration.study_requests[0], execution_ordinal=True),
                *registration.study_requests[1:],
            ),
        ),
        replace(
            registration,
            study_requests=(
                replace(
                    registration.study_requests[0], study_id="forged-study"
                ),
                *registration.study_requests[1:],
            ),
        ),
        replace(
            registration,
            study_requests=(
                replace(
                    registration.study_requests[0],
                    artifact_refs=registration.study_requests[0].artifact_refs[:-1],
                ),
                *registration.study_requests[1:],
            ),
        ),
        replace(
            registration,
            study_requests=(
                replace(
                    registration.study_requests[0],
                    artifact_refs=(
                        registration.study_requests[0].artifact_refs[1],
                        registration.study_requests[0].artifact_refs[0],
                        *registration.study_requests[0].artifact_refs[2:],
                    ),
                ),
                *registration.study_requests[1:],
            ),
        ),
        replace(
            registration,
            study_requests=(
                replace(
                    registration.study_requests[0],
                    artifact_refs=(
                        registration.study_requests[0].artifact_refs[0],
                        *registration.study_requests[0].artifact_refs[1:-1],
                        registration.study_requests[0].artifact_refs[0],
                    ),
                ),
                *registration.study_requests[1:],
            ),
        ),
        replace(
            registration,
            study_requests=(
                replace(
                    registration.study_requests[0],
                    artifact_refs=(
                        registration.study_requests[0].artifact_ref,
                        *registration.study_requests[0].artifact_refs[1:],
                    ),
                ),
                *registration.study_requests[1:],
            ),
        ),
    ):
        with pytest.raises(
            DiagnosticPhaseValidationError,
            match=(
                "exact immutable|recursively immutable|study-request projection|"
                "artifact-ref closure"
            ),
        ):
            replay_diagnostic_phase_registration_projection(forged)
    with pytest.raises(
        DiagnosticPhaseValidationError, match="dataclass differs"
    ):
        replay_diagnostic_phase_registration_projection(
            replace(
                registration,
                store_binding=replace(
                    registration.store_binding,
                    file_inode=registration.store_binding.file_inode + 1,
                ),
            )
        )
def test_registration_rejects_479_swap_and_authority_mutation(phase_dependencies) -> None:
    shared, requests, registration, store_binding, _rule = phase_dependencies
    with pytest.raises(DiagnosticPhaseValidationError):
        build_diagnostic_phase_registration(
            registration_id="short-roster",
            phase_id="diagnostic-calibration-phase-001",
            registered_at="2026-08-08T08:41:00Z",
            tenant_id=TENANT,
            shared_plan_context=shared,
            study_requests=requests[:-1],
            store_binding=store_binding,
        )
    swapped = list(requests)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    with pytest.raises(DiagnosticPhaseValidationError):
        build_diagnostic_phase_registration(
            registration_id="swapped-roster",
            phase_id="diagnostic-calibration-phase-001",
            registered_at="2026-08-08T08:41:00Z",
            tenant_id=TENANT,
            shared_plan_context=shared,
            study_requests=swapped,
            store_binding=store_binding,
        )
    tampered = mutate(
        registration.raw_bytes,
        lambda value: value["boundary"].update(evidence_packet_v2="ALLOWED"),
    )
    with pytest.raises(DiagnosticPhaseValidationError):
        load_diagnostic_phase_registration(
            tampered,
            shared_plan_context=shared,
            study_requests=requests,
            store_binding=store_binding,
        )


def test_completed_row_derives_vectors_from_exact_seven_member_manifest(
    tmp_path: Path,
) -> None:
    shared, _requests, registration, _binding, _rule = bound_phase_dependencies(
        tmp_path / "manifest-grounding",
        suffix="manifest-grounding",
        tenant="tenant-phase-manifest-grounding",
    )
    coordinator = DiagnosticPhaseCoordinator(
        registration=registration,
        shared_plan_context=shared,
        nonce_factory=lambda count: (99).to_bytes(count, "big"),
    )
    artifact_ids = {
        key: f"manifest-grounding-{key.replace('_', '-')}" for key in ARTIFACT_IDS
    }
    issuance = coordinator.issue_attempt(
        execution_ordinal=1,
        binding_id="manifest-grounding-binding",
        binding_created_at="2026-08-08T08:45:00Z",
        assigned_worker_id="diagnostic-worker-manifest-grounding",
        archive_root="C:/cas-harness/stagec/manifest-grounding",
        artifact_ids=artifact_ids,
        issued_at="2026-08-08T08:50:00Z",
        expires_at="2026-08-08T11:00:00Z",
        operation_id="manifest-grounding-issue",
    )
    coordinator.consume_attempt(
        attempt_subject_sha256=issuance.snapshot.attempt_subject_sha256,
        run_nonce_b64url=issuance.run_nonce_b64url,
        worker_started_at="2026-08-08T09:05:00Z",
        operation_id="manifest-grounding-consume",
    )
    archive_manifest, member_bodies = capture_archive(
        issuance.authorization,
        artifact_ids,
        1,
        make_capture_requests()[0],
    )
    terminal_kwargs = {
        "attempt_subject_sha256": issuance.snapshot.attempt_subject_sha256,
        "terminal_at": "2026-08-08T09:06:00Z",
        "terminal_status": "COMPLETED",
        "terminal_phase": "COMPLETE",
        "invocation_certainty": "EXACTLY_ONE",
        "error": None,
        "operation_id": "manifest-grounding-terminal",
    }

    forged_members = dict(member_bodies)
    forged_members["target_vector"] = b"\x00" * len(
        forged_members["target_vector"]
    )
    with pytest.raises(
        DiagnosticPhaseValidationError, match="archive member target_vector bytes drifted"
    ):
        coordinator.build_and_record_terminal(
            **terminal_kwargs,
            produced_artifacts=completed_artifacts(
                issuance.authorization, artifact_ids, archive_manifest
            ),
            archive_manifest=archive_manifest,
            archive_member_bodies=forged_members,
        )

    relabeled_raw = mutate(
        archive_manifest[1],
        lambda value: value["members"][5].update(role="wrong_layer_vector"),
    )
    relabeled_manifest = (
        ref(
            archive_manifest[0].artifact_id,
            relabeled_raw,
            STAGEC_LOCAL_CAPTURE_ARCHIVE_MEDIA_TYPE,
        ),
        relabeled_raw,
    )
    with pytest.raises(
        DiagnosticPhaseValidationError, match="member role/order drifted"
    ):
        coordinator.build_and_record_terminal(
            **terminal_kwargs,
            produced_artifacts=completed_artifacts(
                issuance.authorization, artifact_ids, relabeled_manifest
            ),
            archive_manifest=relabeled_manifest,
            archive_member_bodies=member_bodies,
        )

    mutation = coordinator.build_and_record_terminal(
        **terminal_kwargs,
        produced_artifacts=completed_artifacts(
            issuance.authorization, artifact_ids, archive_manifest
        ),
        archive_manifest=archive_manifest,
        archive_member_bodies=member_bodies,
    )
    assert mutation.snapshot.state == "COMPLETED"
    assert coordinator.state == PHASE_OPEN


def test_private_sqlite_guard_contention_481_and_exact_inventory(
    phase_dependencies,
) -> None:
    shared, _requests, registration, store_binding, _rule = phase_dependencies
    database_path = Path(store_binding.canonical_path)
    coordinator = DiagnosticPhaseCoordinator(
        registration=registration,
        shared_plan_context=shared,
        nonce_factory=lambda count: bytes(range(count)),
    )
    assert not hasattr(coordinator, "lifecycle")
    assert not hasattr(coordinator, "contexts")
    assert not hasattr(coordinator, "context_for_subject")
    with pytest.raises(DiagnosticPhaseConflict):
        DiagnosticPhaseCoordinator(
            registration=registration,
            shared_plan_context=shared,
            nonce_factory=lambda count: bytes(range(count)),
        )
    with pytest.raises(DiagnosticPhaseValidationError):
        coordinator.reject_preauthorization(execution_ordinal=481)
    rogue = sqlite3.connect(database_path)
    with pytest.raises(sqlite3.IntegrityError):
        rogue.execute(
            """
            INSERT INTO diagnostic_attempts (
                tenant_id, attempt_subject_sha256, version,
                run_nonce_sha256, payload
            ) VALUES (?, ?, 1, ?, ?)
            """,
            ("rogue-tenant", "A" * 64, "B" * 64, b"{}"),
        )
    rogue.close()
    with pytest.raises(DiagnosticPhaseIntegrityError, match="full SQLite"):
        coordinator.reconcile_and_seal(
            reconciliation_id="cannot-close-empty",
            closed_at="2026-08-08T08:50:00Z",
        )
    assert coordinator.state == PHASE_OPEN

    rogue = sqlite3.connect(database_path)
    roster_insert_sql = rogue.execute(
        "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
        ("cas_diag_phase_roster_insert_guard",),
    ).fetchone()[0]
    rogue.execute("DROP TRIGGER cas_diag_phase_roster_insert_guard")
    rogue.execute(
        """
        INSERT INTO diagnostic_phase_roster (
            phase_subject_sha256, tenant_id, attempt_subject_sha256,
            execution_ordinal, case_id, study_request_sha256
        ) VALUES (?, ?, ?, 481, ?, ?)
        """,
        (
            registration.phase_subject_sha256,
            registration.tenant_id,
            "A" * 64,
            "rogue-roster-case",
            "B" * 64,
        ),
    )
    rogue.execute(roster_insert_sql)
    rogue.commit()
    with pytest.raises(
        DiagnosticPhaseIntegrityError, match="exact plan-ordered 480"
    ):
        _ = coordinator.state
    roster_delete_sql = rogue.execute(
        "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
        ("cas_diag_phase_roster_delete_guard",),
    ).fetchone()[0]
    rogue.execute("DROP TRIGGER cas_diag_phase_roster_delete_guard")
    rogue.execute(
        "DELETE FROM diagnostic_phase_roster WHERE execution_ordinal=481"
    )
    rogue.execute(roster_delete_sql)
    rogue.commit()
    assert coordinator.state == PHASE_OPEN

    phase_insert_sql = rogue.execute(
        "SELECT sql FROM sqlite_master WHERE type='trigger' AND name=?",
        ("cas_diag_phase_insert_guard",),
    ).fetchone()[0]
    rogue.execute("DROP TRIGGER cas_diag_phase_insert_guard")
    rogue.execute(
        """
        INSERT INTO diagnostic_phases (
            phase_subject_sha256, tenant_id, registration_sha256,
            registration_raw, state, created_at
        ) VALUES (?, ?, ?, ?, 'OPEN', ?)
        """,
        (
            "C" * 64,
            "rogue-phase-tenant",
            "D" * 64,
            b"{}",
            "2026-08-08T08:49:00Z",
        ),
    )
    rogue.execute(phase_insert_sql)
    rogue.commit()
    rogue.close()
    with pytest.raises(
        DiagnosticPhaseIntegrityError, match="exactly the one canonically bound phase"
    ):
        _ = coordinator.state


def test_exact_480_rejections_close_once_with_derived_accounting(rejected_phase) -> None:
    coordinator, reconciliation = rejected_phase
    assert coordinator.state == PHASE_RECONCILED_REJECTED
    assert reconciliation.status == PHASE_RECONCILED_REJECTED
    assert reconciliation.terminal_rows == 480
    assert reconciliation.completed_rows == reconciliation.analyzed_rows == 0
    assert reconciliation.missing_rows == 480
    assert reconciliation.excluded_rows == 0
    assert reconciliation.rejection_reasons == ("VALIDATED_ROW_REJECTION",)
    assert reconciliation.execution_started_at is None
    assert reconciliation.payload["accounting"]["status_counts"] == {
        "COMPLETED": 0,
        "EXPIRED": 0,
        "FAILED": 0,
        "INDETERMINATE": 0,
        "REJECTED": 480,
    }
    assert reconciliation.payload["accounting"]["model_invocation_request_count_minimum"] == 0
    assert reconciliation.payload["accounting"]["model_invocation_request_count_maximum"] == 0
    assert reconciliation.ordered_attempt_subjects == coordinator.registration.ordered_subjects
    assert replay_diagnostic_phase_reconciliation_projection(
        reconciliation, registration=coordinator.registration
    ) == reconciliation
    with pytest.raises(
        DiagnosticPhaseValidationError, match="dataclass differs"
    ):
        replay_diagnostic_phase_reconciliation_projection(
            replace(reconciliation, status=PHASE_RECONCILED_CLEAN),
            registration=coordinator.registration,
        )
    with pytest.raises(
        DiagnosticPhaseValidationError, match="exact immutable"
    ):
        replay_diagnostic_phase_reconciliation_projection(
            replace(reconciliation, raw_bytes=bytearray(reconciliation.raw_bytes)),
            registration=coordinator.registration,
        )
    with pytest.raises(
        DiagnosticPhaseValidationError, match="dataclass differs"
    ):
        replay_diagnostic_phase_reconciliation_projection(
            replace(
                reconciliation,
                ordered_terminal_row_sha256s=(
                    "0" * 64,
                    *reconciliation.ordered_terminal_row_sha256s[1:],
                ),
            ),
            registration=coordinator.registration,
        )
    with pytest.raises(DiagnosticPhaseConflict):
        coordinator.reconcile_and_seal(
            reconciliation_id="second-reconciliation-forbidden",
            closed_at="2026-08-08T08:51:00Z",
        )
    with pytest.raises(DiagnosticPhaseConflict):
        coordinator.record_aggregate_outcome_access(
            access_id="rejected-access-forbidden",
            outcome_index_id="rejected-index-forbidden",
            accessed_at="2026-08-08T10:01:00Z",
        )


def test_reconciliation_payload_is_closed_nonreporting(rejected_phase) -> None:
    _coordinator, reconciliation = rejected_phase
    boundary = reconciliation.payload["boundary"]
    assert boundary == {
        "scope": "DIAGNOSTIC_CALIBRATION_NONREPORTING_ONLY",
        "authority": "STRUCTURE_AND_ACCOUNTING_ONLY",
        "admission_ring": 4,
        "criteria_status": "OPEN",
        "product_claim_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "trusted_time": "NOT_PROVIDED",
        "durable_one_use": "NOT_ESTABLISHED",
        "phase_storage": "PRIVATE_SAME_FILE_SQLITE_CREATE_ONLY_GUARD",
        "coordinator_public_api_outcome_release": "POST_CLEAN_RECONCILIATION_ONLY",
        "out_of_band_read_prevention": "NOT_ESTABLISHED",
        "rogue_process_writes": "DETECTED_FAIL_CLOSED_NOT_PREVENTED",
        "replication": "NOT_PROVIDED",
        "worm": "NOT_PROVIDED",
        "evidence_packet_v2": "FORBIDDEN",
        "evaluation_execution": "NOT_AUTHORIZED",
        "evaluation_promotion": "FORBIDDEN",
        "claim_promotion": "FORBIDDEN",
        "product_route": "FORBIDDEN",
        "public_release": False,
    }
    assert len(reconciliation.ordered_terminal_row_sha256s) == 480
    assert len(reconciliation.ordered_activation_binding_sha256s) == 480
    assert reconciliation.payload["ordered_terminal_row_sha256s"] == (
        reconciliation.ordered_terminal_row_sha256s
    )
    assert all(item is None for item in reconciliation.activation_admission_refs)
    assert all(item is None for item in reconciliation.activation_vector_refs)


def test_clean_480_opens_exactly_one_aggregate_access(clean_phase) -> None:
    coordinator, reconciliation = clean_phase
    assert coordinator.state == PHASE_RECONCILED_CLEAN
    assert reconciliation.status == PHASE_RECONCILED_CLEAN
    assert reconciliation.terminal_rows == 480
    assert reconciliation.completed_rows == reconciliation.analyzed_rows == 480
    assert reconciliation.missing_rows == reconciliation.excluded_rows == 0
    assert reconciliation.rejection_reasons == ()
    assert reconciliation.execution_started_at == "2026-08-08T09:05:00Z"
    assert reconciliation.execution_completed_at == "2026-08-08T09:06:00Z"
    assert reconciliation.payload["accounting"]["status_counts"]["COMPLETED"] == 480
    assert reconciliation.payload["accounting"]["model_invocation_request_count_minimum"] == 480
    assert reconciliation.payload["accounting"]["model_invocation_request_count_maximum"] == 480
    assert not hasattr(reconciliation, "activation_artifacts")
    assert all(item is not None for item in reconciliation.activation_admission_refs)
    assert all(item is not None for item in reconciliation.activation_vector_refs)

    access = coordinator.record_aggregate_outcome_access(
        access_id="diagnostic-phase-outcome-access-001",
        outcome_index_id="diagnostic-phase-outcome-index-001",
        accessed_at="2026-08-08T10:01:00Z",
    )
    assert coordinator.state == PHASE_OUTCOME_ACCESSED
    assert access.reconciliation_ref == reconciliation.artifact_ref
    assert access.execution_started_at == reconciliation.execution_started_at
    assert access.study_completed_at == reconciliation.execution_completed_at
    assert access.payload["access_scope"] == (
        "AGGREGATE_STUDY_ONLY_AFTER_COMPLETE_CLEAN_RECONCILIATION"
    )
    assert access.payload["coordinator_public_api_outcome_release"] == (
        "CALIBRATION_DATASET_ONLY_AFTER_THIS_AGGREGATE_ACCESS"
    )
    assert access.payload["out_of_band_read_prevention"] == "NOT_ESTABLISHED"
    assert len(access.activation_artifacts) == 480
    assert access.activation_artifacts[0][0][0] == (
        reconciliation.activation_vector_refs[0][0]
    )
    assert coordinator.registration.study_requests[0].payload["case_binding"]["execution_ordinal"] == 1
    assert replay_diagnostic_phase_outcome_access_projection(
        access,
        registration=coordinator.registration,
        reconciliation=reconciliation,
    ) == access
    first_admission = access.activation_admissions[0]
    assert replay_diagnostic_phase_activation_admission_projection(
        first_admission
    ) == first_admission
    with pytest.raises(
        DiagnosticPhaseValidationError, match="dataclass differs"
    ):
        replay_diagnostic_phase_activation_admission_projection(
            replace(first_admission, target_vector=first_admission.wrong_layer_vector)
        )
    with pytest.raises(
        DiagnosticPhaseValidationError, match="exact immutable"
    ):
        replay_diagnostic_phase_activation_admission_projection(
            replace(first_admission, payload=dict(first_admission.payload))
        )
    with pytest.raises(
        DiagnosticPhaseValidationError, match="dataclass differs"
    ):
        replay_diagnostic_phase_outcome_access_projection(
            replace(access, access_id="forged-outcome-access"),
            registration=coordinator.registration,
            reconciliation=reconciliation,
        )
    with pytest.raises(
        DiagnosticPhaseValidationError, match="dataclass differs"
    ):
        replay_diagnostic_phase_outcome_access_projection(
            replace(
                access,
                outcome_index=replace(
                    access.outcome_index,
                    execution_started_at="2026-08-08T09:05:01Z",
                ),
            ),
            registration=coordinator.registration,
            reconciliation=reconciliation,
        )
    with pytest.raises(
        DiagnosticPhaseValidationError, match="dataclass differs"
    ):
        replay_diagnostic_phase_outcome_access_projection(
            replace(
                access,
                outcome_access_event=replace(
                    access.outcome_access_event,
                    study_outcome_index=reconciliation.artifact_ref,
                ),
            ),
            registration=coordinator.registration,
            reconciliation=reconciliation,
        )
    with pytest.raises(
        DiagnosticPhaseValidationError, match="exact immutable"
    ):
        replay_diagnostic_phase_outcome_access_projection(
            replace(access, raw_bytes=bytearray(access.raw_bytes)),
            registration=coordinator.registration,
            reconciliation=reconciliation,
        )
    assert coordinator.record_aggregate_outcome_access(
        access_id="diagnostic-phase-outcome-access-001",
        outcome_index_id="diagnostic-phase-outcome-index-001",
        accessed_at="2026-08-08T10:01:00Z",
    ) == access
    with pytest.raises(DiagnosticPhaseConflict):
        coordinator.record_aggregate_outcome_access(
            access_id="diagnostic-phase-outcome-access-002",
            outcome_index_id="diagnostic-phase-outcome-index-002",
            accessed_at="2026-08-08T10:02:00Z",
        )
