from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass, replace
import json
from pathlib import Path
import sys

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
from cas_harness_v2._validation import ArtifactRef, SchemaValidationError  # noqa: E402
from cas_harness_v2.diagnostic_preregistration import (  # noqa: E402
    load_diagnostic_preregistration,
)
from cas_harness_v2.diagnostic_study_protocol import (  # noqa: E402
    build_diagnostic_split_inventory,
    build_diagnostic_study_plan,
    build_diagnostic_study_request,
)
from cas_harness_v2.diagnostic_execution_protocol import (  # noqa: E402
    DIAGNOSTIC_CHILD_EXECUTION_BINDING_MEDIA_TYPE,
    DIAGNOSTIC_CHILD_EXECUTION_BINDING_SCHEMA,
    DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_MEDIA_TYPE,
    DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA,
    DIAGNOSTIC_INVOCATION_CERTAINTIES,
    DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
    DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
    DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE,
    DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA,
    DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_MEDIA_TYPE,
    DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_SCHEMA,
    DIAGNOSTIC_TERMINAL_STATUSES,
    DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE,
    DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA,
    DiagnosticChildExecutionBindingArtifact,
    DiagnosticChildTerminalReceiptV2Artifact,
    DiagnosticStageCExecutionContractArtifact,
    DiagnosticWorkerAuthorizationV2Artifact,
    build_diagnostic_child_execution_binding,
    build_diagnostic_child_terminal_receipt_v2,
    build_diagnostic_stagec_execution_contract,
    build_diagnostic_worker_authorization_v2,
    load_diagnostic_child_execution_binding,
    load_diagnostic_child_terminal_receipt_v2,
    load_diagnostic_stagec_execution_contract,
    load_diagnostic_worker_authorization_v2,
    replay_diagnostic_execution_family,
    validate_diagnostic_execution_batch_uniqueness,
)
from test_diagnostic_study_protocol import (  # noqa: E402
    base_value,
    make_capture_requests,
    make_chain,
)


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


ARTIFACT_IDS = {
    "authorization": "diag-auth-001",
    "authorization_projection": "diag-auth-projection-001",
    "capture_index": "diag-capture-index-001",
    "input_ids": "diag-input-ids-001",
    "attention_mask": "diag-attention-mask-001",
    "target_vector": "diag-target-vector-001",
    "wrong_layer_vector": "diag-wrong-vector-001",
    "archive_admission": "diag-archive-admission-001",
    "child_output": "diag-child-output-001",
    "terminal_receipt": "diag-terminal-001",
}


@dataclass(frozen=True)
class Fixture:
    chain: object
    plan: object
    request: object
    contract: DiagnosticStageCExecutionContractArtifact
    binding: DiagnosticChildExecutionBindingArtifact
    authorization: DiagnosticWorkerAuthorizationV2Artifact
    admission_ref: ArtifactRef
    admission_raw: bytes
    output_ref: ArtifactRef
    output_raw: bytes


@pytest.fixture(scope="module")
def fx() -> Fixture:
    capture_requests = make_capture_requests()
    inventory = build_diagnostic_split_inventory(
        inventory_id="stagec-calibration-inventory-exec-v2",
        capture_requests=capture_requests,
    )
    base = load_diagnostic_preregistration(canonical_json_bytes(base_value(inventory)))
    chain = make_chain(base)
    plan = build_diagnostic_study_plan(
        chain=chain,
        inventory=inventory,
        plan_id="stagec-diagnostic-plan-exec-v2",
        created_at="2026-08-08T08:30:00Z",
    )
    request = build_diagnostic_study_request(
        chain=chain,
        plan=plan,
        case_id=plan.cases[0].case_id,
        created_at="2026-08-08T08:40:00Z",
    )
    contract = build_diagnostic_stagec_execution_contract(
        chain=chain,
        plan=plan,
        contract_id="diagnostic-stagec-execution-contract-001",
        created_at="2026-08-08T08:35:00Z",
    )
    binding = build_diagnostic_child_execution_binding(
        chain=chain,
        plan=plan,
        study_request=request,
        execution_contract=contract,
        binding_id="diagnostic-child-binding-001",
        created_at="2026-08-08T08:45:00Z",
        run_nonce=bytes(range(32)),
        assigned_worker_id="diagnostic-worker-001",
        archive_root="C:/cas-harness/stagec/diag-child-001",
        artifact_ids=ARTIFACT_IDS,
    )
    authorization = build_diagnostic_worker_authorization_v2(
        chain=chain,
        plan=plan,
        study_request=request,
        execution_contract=contract,
        binding=binding,
        issued_at="2026-08-08T08:50:00Z",
        expires_at="2026-08-08T11:00:00Z",
    )
    context = authorization.payload["execution_context"]
    manifest_raw = canonical_json_bytes({"fake_only_external_factory_obligation": True})
    manifest_ref = ref(
        "stagec-local-archive-" + "a" * 64,
        manifest_raw,
        context["artifact_expectations"]["archive"]["media_type"],
    )
    admission_raw = canonical_json_bytes(
        {
            "schema_version": DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
            "admission_id": ARTIFACT_IDS["archive_admission"],
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
        ARTIFACT_IDS["archive_admission"],
        admission_raw,
        DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
    )
    output_raw = canonical_json_bytes(
        {
            "schema_version": DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA,
            "output_id": ARTIFACT_IDS["child_output"],
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
        ARTIFACT_IDS["child_output"],
        output_raw,
        DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE,
    )
    return Fixture(
        chain=chain,
        plan=plan,
        request=request,
        contract=contract,
        binding=binding,
        authorization=authorization,
        admission_ref=admission_ref,
        admission_raw=admission_raw,
        output_ref=output_ref,
        output_raw=output_raw,
    )


def error(category: str = "EXECUTION_FAILED") -> dict[str, object]:
    return {
        "code": "DIAGNOSTIC_CHILD_TERMINAL",
        "category": category,
        "message": "Bounded fake-only terminal observation.",
        "retryable": False,
    }


def completed(fx: Fixture) -> DiagnosticChildTerminalReceiptV2Artifact:
    return build_diagnostic_child_terminal_receipt_v2(
        chain=fx.chain,
        plan=fx.plan,
        study_request=fx.request,
        execution_contract=fx.contract,
        binding=fx.binding,
        authorization=fx.authorization,
        terminal_at="2026-08-08T09:06:00Z",
        terminal_status="COMPLETED",
        terminal_phase="COMPLETE",
        invocation_certainty="EXACTLY_ONE",
        worker_started_at="2026-08-08T09:05:00Z",
        produced_artifacts={
            "archive_admission": (fx.admission_ref, fx.admission_raw),
            "child_output": (fx.output_ref, fx.output_raw),
        },
        error=None,
    )


def test_public_family_is_distinct_canonical_and_non_authoritative(fx: Fixture) -> None:
    assert len(
        {
            DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_SCHEMA,
            DIAGNOSTIC_CHILD_EXECUTION_BINDING_SCHEMA,
            DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA,
            DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA,
        }
    ) == 4
    assert len(
        {
            DIAGNOSTIC_STAGEC_EXECUTION_CONTRACT_MEDIA_TYPE,
            DIAGNOSTIC_CHILD_EXECUTION_BINDING_MEDIA_TYPE,
            DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE,
            DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_MEDIA_TYPE,
        }
    ) == 4
    for carrier in (fx.contract, fx.binding, fx.authorization):
        assert carrier.payload["authority"]["scope"] == "STRUCTURE_ONLY"
        assert carrier.payload["authority"]["execution_authority"] == "NOT_GRANTED_BY_CARRIER"
        assert carrier.payload["authority"]["evidence_packet_v2"] == "FORBIDDEN"
    assert DIAGNOSTIC_TERMINAL_STATUSES == (
        "COMPLETED", "FAILED", "INDETERMINATE", "REJECTED", "EXPIRED"
    )
    assert DIAGNOSTIC_INVOCATION_CERTAINTIES == (
        "EXACTLY_ZERO", "EXACTLY_ONE", "INDETERMINATE_ZERO_OR_ONE"
    )


def test_contract_binding_and_authorization_exact_replay(fx: Fixture) -> None:
    contract = load_diagnostic_stagec_execution_contract(
        fx.contract.raw_bytes, chain=fx.chain, plan=fx.plan
    )
    binding = load_diagnostic_child_execution_binding(
        fx.binding.raw_bytes,
        chain=fx.chain,
        plan=fx.plan,
        study_request=fx.request,
        execution_contract=contract,
    )
    authorization = load_diagnostic_worker_authorization_v2(
        fx.authorization.raw_bytes,
        chain=fx.chain,
        plan=fx.plan,
        study_request=fx.request,
        execution_contract=contract,
        binding=binding,
    )
    assert (contract, binding, authorization) == (fx.contract, fx.binding, fx.authorization)
    assert binding.attempt_ordinal == authorization.attempt_ordinal == 1
    assert binding.run_nonce_b64url == authorization.run_nonce_b64url
    assert binding.payload["execution_context"]["attempt_binding"]["retry_policy"] == {
        "attempt_ordinal": 1,
        "durable_enforcement": "EXTERNAL_REQUIRED_NOT_PROVIDED",
        "maximum_attempts": 1,
        "replacement": "FORBIDDEN",
        "retry": "FORBIDDEN",
        "retry_count": 0,
    }
    assert binding.payload["execution_context"] == authorization.payload["execution_context"]
    assert binding.execution_context_sha256 == authorization.execution_context_sha256
    assert binding.case_execution_ordinal == 1


def test_completed_terminal_and_whole_family_replay(fx: Fixture) -> None:
    terminal = completed(fx)
    assert terminal.terminal_status == "COMPLETED"
    assert terminal.invocation_certainty == "EXACTLY_ONE"
    assert terminal.produced_artifact_refs == (fx.admission_ref, fx.output_ref)
    assert terminal.payload["execution_context"] == fx.authorization.payload["execution_context"]
    assert terminal.payload["terminal"]["packet_v2"] == "FORBIDDEN"
    assert terminal.payload["terminal"]["archive_manifest"]["artifact_id"] == (
        "stagec-local-archive-" + "a" * 64
    )
    replayed = replay_diagnostic_execution_family(
        chain=fx.chain,
        plan=fx.plan,
        study_request=fx.request,
        execution_contract=fx.contract,
        binding=fx.binding,
        authorization=fx.authorization,
        terminal_receipt=terminal,
        produced_artifact_bodies={
            "archive_admission": fx.admission_raw,
            "child_output": fx.output_raw,
        },
    )
    assert replayed == (fx.contract, fx.binding, fx.authorization, terminal)


@pytest.mark.parametrize(
    ("status", "phase", "certainty", "started", "terminal_at", "produced", "category"),
    [
        ("FAILED", "PRE_MODEL", "EXACTLY_ZERO", "2026-08-08T09:05:00Z", "2026-08-08T09:06:00Z", {}, "EXECUTION_FAILED"),
        ("FAILED", "OUTPUT", "EXACTLY_ONE", "2026-08-08T09:05:00Z", "2026-08-08T09:06:00Z", "admission", "OUTPUT_FAILED"),
        ("INDETERMINATE", "DISPATCH_OR_EXECUTION", "INDETERMINATE_ZERO_OR_ONE", "2026-08-08T09:05:00Z", "2026-08-08T11:05:00Z", {}, "EXECUTION_INDETERMINATE"),
        ("REJECTED", "PRE_ADMISSION", "EXACTLY_ZERO", None, "2026-08-08T08:55:00Z", {}, "AUTHORIZATION_REJECTED"),
        ("EXPIRED", "AUTHORIZATION_EXPIRED", "EXACTLY_ZERO", None, "2026-08-08T11:00:00Z", {}, "AUTHORIZATION_EXPIRED"),
    ],
)
def test_all_adverse_terminal_branches(
    fx: Fixture, status, phase, certainty, started, terminal_at, produced, category
) -> None:
    artifacts = (
        {"archive_admission": (fx.admission_ref, fx.admission_raw)}
        if produced == "admission"
        else {}
    )
    terminal = build_diagnostic_child_terminal_receipt_v2(
        chain=fx.chain,
        plan=fx.plan,
        study_request=fx.request,
        execution_contract=fx.contract,
        binding=fx.binding,
        authorization=fx.authorization,
        terminal_at=terminal_at,
        terminal_status=status,
        terminal_phase=phase,
        invocation_certainty=certainty,
        worker_started_at=started,
        produced_artifacts=artifacts,
        error=error(category),
    )
    assert terminal.terminal_status == status
    assert terminal.payload["terminal"]["retry_count"] == 0
    assert terminal.payload["terminal"]["retryable"] is False
    assert terminal.payload["terminal"]["replacement"] == "FORBIDDEN"
    if status != "COMPLETED":
        assert terminal.payload["terminal"]["row_disposition"].endswith(
            "QUARANTINED_NO_REPLACEMENT"
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(extra="forbidden"),
        lambda value: value["model_contract"].update(model_id="other/model"),
        lambda value: value["capture_contract"].update(target_layer=17),
        lambda value: value["authority"].update(execution_authority="GRANTED"),
        lambda value: value["boundary"].update(execution="PERFORMED"),
        lambda value: value["execution_identity_artifacts"].clear(),
    ],
)
def test_contract_rejects_semantic_and_authority_mutations(fx: Fixture, change) -> None:
    with pytest.raises((SchemaValidationError, ValueError)):
        load_diagnostic_stagec_execution_contract(
            mutate(fx.contract.raw_bytes, change), chain=fx.chain, plan=fx.plan
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(extra="forbidden"),
        lambda value: value["execution_context"]["case_binding"].update(case_id="other-case"),
        lambda value: value["execution_context"]["case_binding"].update(case_execution_ordinal=2),
        lambda value: value["execution_context"]["attempt_binding"]["retry_policy"].update(maximum_attempts=2),
        lambda value: value["execution_context"]["attempt_binding"]["retry_policy"].update(retry="ALLOWED"),
        lambda value: value["execution_context"]["artifact_expectations"]["archive"].update(absolute_root="C:/other"),
        lambda value: value["execution_context"]["artifact_expectations"]["archive"]["ordered_member_roles"].reverse(),
        lambda value: value["authority"].update(authentication="PROVIDED"),
        lambda value: value["boundary"].update(execution="PERFORMED"),
    ],
)
def test_binding_rejects_case_attempt_archive_and_authority_mutations(
    fx: Fixture, change
) -> None:
    with pytest.raises((SchemaValidationError, ValueError, KeyError)):
        load_diagnostic_child_execution_binding(
            mutate(fx.binding.raw_bytes, change),
            chain=fx.chain,
            plan=fx.plan,
            study_request=fx.request,
            execution_contract=fx.contract,
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(authorization_id="wrong-auth"),
        lambda value: value.update(not_before="2026-08-08T09:01:00Z"),
        lambda value: value["execution_context"]["case_binding"].update(case_id="other-case"),
        lambda value: value.update(execution_context_sha256="0" * 64),
        lambda value: value["execution_context"]["attempt_binding"]["run_nonce"].update(value_b64url="A" * 43),
        lambda value: value["authority"].update(durable_one_use="PROVIDED"),
    ],
)
def test_authorization_rejects_context_nonce_window_and_authority_mutations(
    fx: Fixture, change
) -> None:
    with pytest.raises((SchemaValidationError, ValueError)):
        load_diagnostic_worker_authorization_v2(
            mutate(fx.authorization.raw_bytes, change),
            chain=fx.chain,
            plan=fx.plan,
            study_request=fx.request,
            execution_contract=fx.contract,
            binding=fx.binding,
        )


def test_noncanonical_duplicate_bom_and_mutable_input_rules(fx: Fixture) -> None:
    noncanonical = json.dumps(json.loads(fx.binding.raw_bytes), indent=2).encode()
    duplicate = b'{"binding_id":"duplicate",' + fx.binding.raw_bytes[1:]
    for raw in (noncanonical, b"\xef\xbb\xbf" + fx.binding.raw_bytes, duplicate):
        with pytest.raises(ValueError):
            load_diagnostic_child_execution_binding(
                raw,
                chain=fx.chain,
                plan=fx.plan,
                study_request=fx.request,
                execution_contract=fx.contract,
            )
    mutable = bytearray(fx.authorization.raw_bytes)
    loaded = load_diagnostic_worker_authorization_v2(
        mutable,
        chain=fx.chain,
        plan=fx.plan,
        study_request=fx.request,
        execution_contract=fx.contract,
        binding=fx.binding,
    )
    mutable[:] = b"{}"
    assert loaded.raw_bytes == fx.authorization.raw_bytes


@pytest.mark.parametrize(
    ("status", "phase", "certainty", "started", "produced", "err"),
    [
        ("COMPLETED", "COMPLETE", "EXACTLY_ZERO", "2026-08-08T09:05:00Z", "both", None),
        ("COMPLETED", "COMPLETE", "EXACTLY_ONE", "2026-08-08T09:05:00Z", "none", None),
        ("COMPLETED", "COMPLETE", "EXACTLY_ONE", "2026-08-08T09:05:00Z", "both", error()),
        ("FAILED", "PRE_MODEL", "EXACTLY_ONE", "2026-08-08T09:05:00Z", "none", error()),
        ("FAILED", "OUTPUT", "EXACTLY_ONE", "2026-08-08T09:05:00Z", "both", error("OUTPUT_FAILED")),
        ("INDETERMINATE", "DISPATCH_OR_EXECUTION", "EXACTLY_ONE", "2026-08-08T09:05:00Z", "none", error("EXECUTION_INDETERMINATE")),
        ("REJECTED", "PRE_ADMISSION", "EXACTLY_ZERO", "2026-08-08T09:05:00Z", "none", error("AUTHORIZATION_REJECTED")),
        ("EXPIRED", "AUTHORIZATION_EXPIRED", "EXACTLY_ZERO", None, "admission", error("AUTHORIZATION_EXPIRED")),
    ],
)
def test_terminal_union_rejects_cross_branch_shapes(
    fx: Fixture, status, phase, certainty, started, produced, err
) -> None:
    artifacts = {
        "both": {
            "archive_admission": (fx.admission_ref, fx.admission_raw),
            "child_output": (fx.output_ref, fx.output_raw),
        },
        "admission": {"archive_admission": (fx.admission_ref, fx.admission_raw)},
        "none": {},
    }[produced]
    with pytest.raises(SchemaValidationError):
        build_diagnostic_child_terminal_receipt_v2(
            chain=fx.chain,
            plan=fx.plan,
            study_request=fx.request,
            execution_contract=fx.contract,
            binding=fx.binding,
            authorization=fx.authorization,
            terminal_at="2026-08-08T09:06:00Z",
            terminal_status=status,
            terminal_phase=phase,
            invocation_certainty=certainty,
            worker_started_at=started,
            produced_artifacts=artifacts,
            error=err,
        )


def test_terminal_rejects_body_ref_context_and_retry_tampering(fx: Fixture) -> None:
    terminal = completed(fx)
    bodies = {"archive_admission": fx.admission_raw, "child_output": fx.output_raw}
    with pytest.raises(SchemaValidationError):
        load_diagnostic_child_terminal_receipt_v2(
            terminal.raw_bytes,
            chain=fx.chain,
            plan=fx.plan,
            study_request=fx.request,
            execution_contract=fx.contract,
            binding=fx.binding,
            authorization=fx.authorization,
            produced_artifact_bodies={**bodies, "child_output": b"tampered"},
        )
    for change in (
        lambda value: value["terminal"].update(retry_count=1),
        lambda value: value["terminal"].update(retryable=True),
        lambda value: value["terminal"].update(packet_v2="CREATED"),
        lambda value: value["execution_context"]["case_binding"].update(case_id="swapped"),
        lambda value: value["authority"].update(product="AUTHORIZED"),
    ):
        with pytest.raises((SchemaValidationError, ValueError)):
            load_diagnostic_child_terminal_receipt_v2(
                mutate(terminal.raw_bytes, change),
                chain=fx.chain,
                plan=fx.plan,
                study_request=fx.request,
                execution_contract=fx.contract,
                binding=fx.binding,
                authorization=fx.authorization,
                produced_artifact_bodies=bodies,
            )


def test_forged_carriers_wrong_media_collisions_nonce_and_paths_rejected(fx: Fixture) -> None:
    with pytest.raises(FrozenInstanceError):
        fx.binding.binding_id = "changed"  # type: ignore[misc]
    forged = replace(fx.binding, case_id="forged-case")
    with pytest.raises(SchemaValidationError):
        build_diagnostic_worker_authorization_v2(
            chain=fx.chain,
            plan=fx.plan,
            study_request=fx.request,
            execution_contract=fx.contract,
            binding=forged,
            issued_at="2026-08-08T08:50:00Z",
            expires_at="2026-08-08T11:00:00Z",
        )
    bad_ids = dict(ARTIFACT_IDS)
    bad_ids["terminal_receipt"] = bad_ids["authorization"]
    for kwargs in (
        {"run_nonce": b"short", "archive_root": "C:/valid", "artifact_ids": ARTIFACT_IDS},
        {"run_nonce": bytes(range(32)), "archive_root": "relative/path", "artifact_ids": ARTIFACT_IDS},
        {"run_nonce": bytes(range(32)), "archive_root": "C:/parent./child", "artifact_ids": ARTIFACT_IDS},
        {"run_nonce": bytes(range(32)), "archive_root": "C:/parent /child", "artifact_ids": ARTIFACT_IDS},
        {"run_nonce": bytes(range(32)), "archive_root": "C:/parent:stream/child", "artifact_ids": ARTIFACT_IDS},
        {"run_nonce": bytes(range(32)), "archive_root": "/parent:alias/child", "artifact_ids": ARTIFACT_IDS},
        {"run_nonce": bytes(range(32)), "archive_root": "C:/valid", "artifact_ids": bad_ids},
    ):
        with pytest.raises(SchemaValidationError):
            build_diagnostic_child_execution_binding(
                chain=fx.chain,
                plan=fx.plan,
                study_request=fx.request,
                execution_contract=fx.contract,
                binding_id="another-binding",
                created_at="2026-08-08T08:46:00Z",
                assigned_worker_id="worker-002",
                **kwargs,
            )
    wrong_media = ArtifactRef(
        artifact_id=fx.admission_ref.artifact_id,
        sha256=fx.admission_ref.sha256,
        byte_length=fx.admission_ref.byte_length,
        media_type="application/json",
    )
    with pytest.raises(SchemaValidationError):
        build_diagnostic_child_terminal_receipt_v2(
            chain=fx.chain,
            plan=fx.plan,
            study_request=fx.request,
            execution_contract=fx.contract,
            binding=fx.binding,
            authorization=fx.authorization,
            terminal_at="2026-08-08T09:06:00Z",
            terminal_status="COMPLETED",
            terminal_phase="COMPLETE",
            invocation_certainty="EXACTLY_ONE",
            worker_started_at="2026-08-08T09:05:00Z",
            produced_artifacts={
                "archive_admission": (wrong_media, fx.admission_raw),
                "child_output": (fx.output_ref, fx.output_raw),
            },
            error=None,
        )


@pytest.mark.parametrize(
    "manifest_id",
    [
        "stagec-local-archive-short",
        "stagec-local-archive-" + "A" * 64,
        "stagec-local-archive-" + "a" * 65,
        "stagec-local-archive-" + "g" * 64,
    ],
)
def test_archive_manifest_id_requires_exact_lowercase_digest(
    fx: Fixture, manifest_id: str
) -> None:
    bad_admission_raw = mutate(
        fx.admission_raw,
        lambda value: value["archive_manifest"].update(artifact_id=manifest_id),
    )
    bad_admission_ref = ref(
        ARTIFACT_IDS["archive_admission"],
        bad_admission_raw,
        DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
    )
    with pytest.raises(SchemaValidationError):
        build_diagnostic_child_terminal_receipt_v2(
            chain=fx.chain,
            plan=fx.plan,
            study_request=fx.request,
            execution_contract=fx.contract,
            binding=fx.binding,
            authorization=fx.authorization,
            terminal_at="2026-08-08T09:06:00Z",
            terminal_status="FAILED",
            terminal_phase="OUTPUT",
            invocation_certainty="EXACTLY_ONE",
            worker_started_at="2026-08-08T09:05:00Z",
            produced_artifacts={
                "archive_admission": (bad_admission_ref, bad_admission_raw)
            },
            error=error("OUTPUT_FAILED"),
        )


def test_batch_uniqueness_rejects_reuse(fx: Fixture) -> None:
    terminal = completed(fx)
    validate_diagnostic_execution_batch_uniqueness(
        bindings=[fx.binding],
        authorizations=[fx.authorization],
        terminal_receipts=[terminal],
    )
    with pytest.raises(SchemaValidationError):
        validate_diagnostic_execution_batch_uniqueness(
            bindings=[fx.binding, fx.binding],
            authorizations=[fx.authorization, fx.authorization],
            terminal_receipts=[terminal, terminal],
        )


def test_batch_rejects_dataclass_projection_forgery(fx: Fixture) -> None:
    terminal = completed(fx)

    for forged_binding in (
        replace(fx.binding, run_nonce_b64url="A" * 43),
        replace(fx.binding, case_id="forged-case"),
        replace(fx.binding, case_execution_ordinal=2),
        replace(fx.binding, attempt_ordinal=2),
    ):
        with pytest.raises(SchemaValidationError):
            validate_diagnostic_execution_batch_uniqueness(
                bindings=[forged_binding],
                authorizations=[fx.authorization],
                terminal_receipts=[terminal],
            )

    for forged_authorization in (
        replace(fx.authorization, run_nonce_b64url="A" * 43),
        replace(fx.authorization, authorization_id="forged-authorization"),
        replace(fx.authorization, case_id="forged-case"),
        replace(fx.authorization, case_execution_ordinal=2),
        replace(fx.authorization, execution_context_sha256="0" * 64),
    ):
        with pytest.raises(SchemaValidationError):
            validate_diagnostic_execution_batch_uniqueness(
                bindings=[fx.binding],
                authorizations=[forged_authorization],
                terminal_receipts=[terminal],
            )

    terminal_payload_forgers = []
    for field, value in (
        ("lifecycle_terminal_state", "FAILED"),
        ("phase", "OUTPUT"),
    ):
        payload = json.loads(terminal.raw_bytes)
        payload["terminal"][field] = value
        terminal_payload_forgers.append(replace(terminal, payload=payload))
    payload = json.loads(terminal.raw_bytes)
    payload["authorization"] = None
    terminal_payload_forgers.append(replace(terminal, payload=payload))

    for forged_terminal in (
        replace(terminal, terminal_status="FAILED"),
        replace(terminal, invocation_certainty="EXACTLY_ZERO"),
        replace(terminal, produced_artifact_refs=()),
        replace(terminal, artifact_refs=terminal.artifact_refs[:-1]),
        *terminal_payload_forgers,
    ):
        with pytest.raises(SchemaValidationError):
            validate_diagnostic_execution_batch_uniqueness(
                bindings=[fx.binding],
                authorizations=[fx.authorization],
                terminal_receipts=[forged_terminal],
            )


def test_no_legacy_carrier_media_or_schema_is_accepted(fx: Fixture) -> None:
    legacy_auth = mutate(
        fx.authorization.raw_bytes,
        lambda value: value.update(schema_version="cas_harness_v2.worker_authorization.v1"),
    )
    with pytest.raises(SchemaValidationError):
        load_diagnostic_worker_authorization_v2(
            legacy_auth,
            chain=fx.chain,
            plan=fx.plan,
            study_request=fx.request,
            execution_contract=fx.contract,
            binding=fx.binding,
        )
    assert fx.authorization.artifact_ref.media_type != "application/vnd.cas-harness.worker-authorization+json"
