from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import sys
import threading

import pytest

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes
from cas_harness_v2._validation import ArtifactRef
from cas_harness_v2.diagnostic_execution_protocol import (
    build_diagnostic_child_execution_binding,
    build_diagnostic_stagec_execution_contract,
    build_diagnostic_worker_authorization_v2,
)
from cas_harness_v2.diagnostic_lifecycle import (
    build_diagnostic_shared_plan_replay_context,
    derive_diagnostic_attempt_subject_sha256,
)
from cas_harness_v2.diagnostic_phase_coordinator import (
    DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE,
    build_diagnostic_phase_registration,
    build_diagnostic_phase_store_binding,
)
from cas_harness_v2.diagnostic_preregistration import (
    DIAGNOSTIC_AMENDMENT_SCHEMA,
    DiagnosticPreregistrationChain,
)
from cas_harness_v2.diagnostic_stagec_prerequisite_external_intake import (
    load_stagec_external_prerequisite_binding,
    load_stagec_external_prerequisite_snapshot,
)
import cas_harness_v2.diagnostic_stagec_prerequisite_external_intake as external_intake
from cas_harness_v2.diagnostic_study_protocol import build_diagnostic_study_plan
import cas_harness_v2.diagnostic_stagec_prerequisite_admission as admission
import cas_harness_v2.diagnostic_stagec_runtime_activation as sut
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from test_diagnostic_execution_protocol import ARTIFACT_IDS  # noqa: E402
from test_diagnostic_stagec_prerequisite_admission import (  # noqa: E402
    build_fx,
)


TENANT = "tenant-stagec-runtime"
CONTROL_WORKER = "stagec-control-worker-001"
ROW_WORKER = "stagec-row-worker-001"
PHASE_TIME = "2026-08-09T10:01:00Z"
CLAIM_TIME = "2026-08-09T10:05:00Z"


def _ref_value(reference: ArtifactRef) -> dict[str, object]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _write_kit(root: Path, fx) -> None:
    bodies = {
        "detector_drc": (fx.drc.artifact_ref, fx.drc.raw_bytes),
        "frozen_corpus": (fx.corpus.artifact_ref, fx.corpus.raw_bytes),
        "trusted_storage": (fx.storage.artifact_ref, fx.storage.raw_bytes),
        "execution_authorization": (
            fx.authorization.artifact_ref,
            fx.authorization.raw_bytes,
        ),
    }
    groups = (
        (("drc_profile", "detector_ruleset", "known_fault_fixture"), fx.drc),
        (
            ("corpus_rows", "adjudication", "split_assignment", "surface_bundle"),
            fx.corpus,
        ),
        (
            (
                "object_lock_receipt",
                "readback_receipt",
                "trusted_time_receipt",
                "verifier_identity",
            ),
            fx.storage,
        ),
        (("authorization_instrument",), fx.authorization),
    )
    for names, carrier in groups:
        for name, body in zip(names, carrier.artifact_bodies, strict=True):
            bodies[name] = body
    artifacts = {}
    for index, role in enumerate(
        external_intake.STAGEC_EXTERNAL_PREREQUISITE_ROLE_ORDER, start=1
    ):
        relative_path = f"payload/{index:02d}-{role}.json"
        target = root.joinpath(*relative_path.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        reference, raw_bytes = bodies[role]
        target.write_bytes(raw_bytes)
        artifacts[role] = {
            "relative_path": relative_path,
            "artifact_ref": _ref_value(reference),
        }
    manifest = {
        "schema_version": external_intake.STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_SCHEMA,
        "target_binding_sha256": fx.context.target_binding_sha256,
        "artifacts": artifacts,
    }
    root.joinpath(
        external_intake.STAGEC_EXTERNAL_PREREQUISITE_LOCATOR_MANIFEST_FILENAME
    ).write_bytes(canonical_json_bytes(manifest))


@dataclass(frozen=True)
class RuntimeFixture:
    prerequisite: object
    external_binding: object
    shared: object
    registration: object
    target: object


@pytest.fixture(scope="module")
def runtime_fixture(tmp_path_factory) -> RuntimeFixture:
    fx = build_fx()
    kit = tmp_path_factory.mktemp("stagec-runtime-external-kit")
    _write_kit(kit, fx)
    snapshot = load_stagec_external_prerequisite_snapshot(kit, context=fx.context)
    external_binding = load_stagec_external_prerequisite_binding(
        snapshot,
        context=fx.context,
        replay_bundles=fx.bundles,
        intake_bytes=fx.intake.raw_bytes,
        admission_bytes=fx.admission.raw_bytes,
    )

    store = build_diagnostic_phase_store_binding(
        binding_id="stagec-runtime-phase-store-001",
        created_at="2026-08-09T09:08:30Z",
        database_path=tmp_path_factory.mktemp("stagec-runtime-phase-store")
        / "phase.sqlite3",
    )
    rule_raw = canonical_json_bytes(
        {
            "schema_version": "cas_harness_v2.diagnostic_calibration_rule.v1",
            "rule_id": "stagec-runtime-calibration-rule-001",
            "created_at": "2026-08-09T09:08:30Z",
            "structural_test_only": True,
        }
    )
    rule_ref = ArtifactRef(
        artifact_id="stagec-runtime-calibration-rule-001",
        sha256=sha256_bytes(rule_raw),
        byte_length=len(rule_raw),
        media_type=DIAGNOSTIC_CALIBRATION_RULE_MEDIA_TYPE,
    )
    chain = DiagnosticPreregistrationChain(fx.base)
    identity = chain.append_amendment(
        canonical_json_bytes(
            {
                "schema_version": DIAGNOSTIC_AMENDMENT_SCHEMA,
                "amendment_id": "AMD-STAGEC-RUNTIME-IDENTITY-001",
                "created_at": "2026-08-09T09:09:00Z",
                "base_preregistration_sha256": fx.base.sha256,
                "previous_amendment_sha256": None,
                "timing": "PROSPECTIVE_PRE_OUTCOME",
                "reason": "Bind the exact runtime phase store and calibration rule.",
                "change_class": "EXECUTION_IDENTITY_ADDITION",
                "changes": {
                    "additional_artifacts": [
                        _ref_value(store.artifact_ref),
                        _ref_value(rule_ref),
                    ]
                },
            }
        )
    )
    chain.append_amendment(
        canonical_json_bytes(
            {
                "schema_version": DIAGNOSTIC_AMENDMENT_SCHEMA,
                "amendment_id": "AMD-STAGEC-RUNTIME-WINDOW-001",
                "created_at": "2026-08-09T09:10:00Z",
                "base_preregistration_sha256": fx.base.sha256,
                "previous_amendment_sha256": identity.sha256,
                "timing": "PROSPECTIVE_PRE_OUTCOME",
                "reason": "Bind the exact admitted Stage C authorization window.",
                "change_class": "EXECUTION_WINDOW",
                "changes": {
                    "window_start": fx.authorization.window_start,
                    "window_end": fx.authorization.window_end,
                },
            }
        )
    )
    plan = build_diagnostic_study_plan(
        chain=chain,
        inventory=fx.split,
        plan_id="stagec-runtime-plan-001",
        created_at="2026-08-09T09:15:00Z",
    )
    contract = build_diagnostic_stagec_execution_contract(
        chain=chain,
        plan=plan,
        contract_id="stagec-runtime-execution-contract-001",
        created_at="2026-08-09T09:16:00Z",
    )
    shared = build_diagnostic_shared_plan_replay_context(
        chain=chain, plan=plan, execution_contract=contract
    )
    requests = tuple(
        shared.build_study_request(
            case_id=case.case_id,
            created_at="2026-08-09T09:17:00Z",
        )
        for case in plan.cases
    )
    registration = build_diagnostic_phase_registration(
        registration_id="stagec-runtime-phase-registration-001",
        phase_id="stagec-runtime-phase-001",
        registered_at="2026-08-09T09:18:00Z",
        tenant_id=TENANT,
        shared_plan_context=shared,
        study_requests=requests,
        store_binding=store,
    )
    target = sut.build_stagec_runtime_model_capture_target(
        prerequisite_context=fx.context,
        shared_plan_context=shared,
    )
    return RuntimeFixture(fx, external_binding, shared, registration, target)


@pytest.fixture(autouse=True)
def exact_test_seams(monkeypatch):
    monkeypatch.setattr(
        admission,
        "_utc_now",
        lambda: datetime(2026, 8, 9, 9, 30, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(sut, "_TRUSTED_BACKEND_TYPES", frozenset({TestBackend}))
    monkeypatch.setattr(
        sut, "_ACTIVATED_COORDINATOR_TYPES", frozenset({FakeCoordinator})
    )


def prepare(runtime: RuntimeFixture):
    return sut.prepare_stagec_runtime_activation(
        external_binding=runtime.external_binding,
        prerequisite_context=runtime.prerequisite.context,
        replay_bundles=runtime.prerequisite.bundles,
        shared_plan_context=runtime.shared,
        phase_registration=runtime.registration,
        model_capture_target=runtime.target,
        tenant_id=TENANT,
    )


def phase_observation(expectation, *, newly: bool = True):
    storage = sut.StageCRuntimeStorageObservation(
        authenticated_tenant_id=expectation.tenant_id,
        authenticated_worker_id=expectation.authenticated_worker_id,
        provider_id="stagec-test-provider-001",
        object_key="stagec/frozen/corpus-001.json",
        object_version_id=expectation.storage_object_version_id,
        checksum_sha256=expectation.storage_checksum_sha256,
        byte_length=expectation.storage_byte_length,
        retention_until=expectation.storage_retention_until,
        trusted_time=PHASE_TIME,
        observation_generation=1,
    )
    authorization = sut.StageCRuntimeIssuerAuthorizationObservation(
        authenticated_tenant_id=expectation.tenant_id,
        authenticated_worker_id=expectation.authenticated_worker_id,
        issuer_id="stagec-test-issuer-001",
        authorization_id=expectation.authorization_id,
        prospective_subject_sha256=expectation.prospective_subject_sha256,
        target_binding_sha256=expectation.target_binding_sha256,
        window_start=expectation.authorization_window_start,
        window_end=expectation.authorization_window_end,
        nonce_b64url=expectation.authorization_nonce_b64url,
        nonce_state_before="UNCONSUMED" if newly else "CONSUMED",
        nonce_state_after="CONSUMED",
        nonce_consumed_now=newly,
        ledger_generation=1,
        phase_id=expectation.phase_id,
        phase_subject_sha256=expectation.phase_subject_sha256,
        plan_sha256=expectation.plan_ref.sha256,
        execution_contract_sha256=expectation.execution_contract_ref.sha256,
        admission_sha256=expectation.admission_ref.sha256,
    )
    return sut.StageCRuntimePhaseActivationObservation(
        storage=storage,
        authorization=authorization,
        registration_sha256=expectation.registration_ref.sha256,
        roster_closure_sha256=expectation.roster_closure_sha256,
        model_capture_target_sha256=expectation.model_capture_target_sha256,
        control_state=sut.STAGEC_RUNTIME_ROWS_ENABLED,
    )


def claim_observation(expectation, *, newly: bool, generation: int):
    phase = SimpleNamespace(
        tenant_id=expectation.tenant_id,
        authenticated_worker_id=expectation.assigned_worker_id,
        storage_object_version_id=expectation.activation_storage_object_version_id,
        storage_checksum_sha256=expectation.activation_storage_checksum_sha256,
        storage_byte_length=expectation.activation_storage_byte_length,
        storage_retention_until=expectation.activation_storage_retention_until,
        authorization_id=expectation.stagec_authorization_id,
        prospective_subject_sha256=expectation.prospective_subject_sha256,
        target_binding_sha256=expectation.target_binding_sha256,
        authorization_window_start=expectation.stagec_authorization_window_start,
        authorization_window_end=expectation.stagec_authorization_window_end,
        authorization_nonce_b64url=expectation.stagec_authorization_nonce_b64url,
        phase_id=expectation.phase_id,
        phase_subject_sha256=expectation.phase_subject_sha256,
        plan_ref=expectation.plan_ref,
        execution_contract_ref=expectation.execution_contract_ref,
        admission_ref=expectation.admission_ref,
        registration_ref=expectation.registration_ref,
        roster_closure_sha256=expectation.roster_closure_sha256,
        model_capture_target_sha256=expectation.model_capture_target_sha256,
    )
    storage = replace(
        phase_observation(phase).storage,
        authenticated_worker_id=expectation.assigned_worker_id,
        provider_id=expectation.activation_provider_id,
        object_key=expectation.activation_storage_object_key,
        trusted_time=CLAIM_TIME,
        observation_generation=generation,
    )
    authorization = replace(
        phase_observation(phase).authorization,
        authenticated_worker_id=expectation.assigned_worker_id,
        issuer_id=expectation.activation_issuer_id,
        nonce_state_before="CONSUMED",
        nonce_consumed_now=False,
        ledger_generation=generation,
    )
    lease = sut.StageCRuntimeWorkerLeaseObservation(
        lease_id=f"stagec-row-lease-{expectation.execution_ordinal:03d}",
        authenticated_tenant_id=expectation.tenant_id,
        authenticated_worker_id=expectation.assigned_worker_id,
        provider_id=expectation.activation_provider_id,
        phase_id=expectation.phase_id,
        phase_subject_sha256=expectation.phase_subject_sha256,
        issued_at="2026-08-09T10:00:00Z",
        not_before="2026-08-09T10:00:00Z",
        expires_at="2026-08-09T10:50:00Z",
        lease_generation=generation,
        state="ACTIVE",
    )
    return sut.StageCRuntimeAttemptClaimObservation(
        storage=storage,
        authorization=authorization,
        worker_lease=lease,
        claim_id=f"stagec-row-claim-{expectation.execution_ordinal:03d}",
        claim_operation_id=expectation.claim_operation_id,
        claim_generation=generation,
        claim_state="CLAIMED",
        claimed_now=newly,
        execution_ordinal=expectation.execution_ordinal,
        study_request_sha256=expectation.study_request_ref.sha256,
        attempt_subject_sha256=expectation.attempt_subject_sha256,
        child_binding_sha256=expectation.child_binding_ref.sha256,
        worker_authorization_sha256=expectation.worker_authorization_ref.sha256,
        registration_sha256=expectation.registration_ref.sha256,
        roster_closure_sha256=expectation.roster_closure_sha256,
        model_capture_target_sha256=expectation.model_capture_target_sha256,
    )


class TestBackend(sut.StageCRuntimeActivationBackend):
    __test__ = False

    def __init__(
        self,
        *,
        phase_fault=None,
        phase_mutates_expectation=False,
        phase_raises=False,
        claim_fault=None,
        claim_mutates_expectation=False,
        claim_raises=False,
        ambiguous_fault=None,
        ambiguous_fails=False,
        invalidation_fault=None,
        invalidation_fails=False,
    ):
        self.lock = threading.RLock()
        self.phase_consumed = False
        self.claims = {}
        self.claim_operations = {}
        self.claim_generations = {}
        self.phase_calls = 0
        self.claim_calls = 0
        self.ambiguous_terminal_calls = 0
        self.invalidation_calls = 0
        self.last_phase_observation = None
        self.last_claim_observation = None
        self.phase_fault = phase_fault
        self.phase_mutates_expectation = phase_mutates_expectation
        self.phase_raises = phase_raises
        self.claim_fault = claim_fault
        self.claim_mutates_expectation = claim_mutates_expectation
        self.claim_raises = claim_raises
        self.ambiguous_fault = ambiguous_fault
        self.ambiguous_fails = ambiguous_fails
        self.invalidation_fault = invalidation_fault
        self.invalidation_fails = invalidation_fails

    def activate_phase(self, expectation):
        with self.lock:
            self.phase_calls += 1
            newly = not self.phase_consumed
            if newly:
                self.phase_consumed = True
            observation = phase_observation(expectation, newly=newly)
            if self.phase_fault is not None:
                observation = self.phase_fault(observation)
            if self.phase_mutates_expectation:
                object.__setattr__(
                    expectation,
                    "authorization_nonce_b64url",
                    "B" * 43,
                )
            if self.phase_raises:
                raise RuntimeError("injected phase backend failure")
            self.last_phase_observation = observation
            return observation

    def claim_attempt(self, expectation):
        with self.lock:
            self.claim_calls += 1
            newly = expectation.attempt_subject_sha256 not in self.claims
            if newly:
                self.claims[expectation.attempt_subject_sha256] = "CLAIMED"
                self.claim_operations[expectation.attempt_subject_sha256] = (
                    expectation.claim_operation_id
                )
            generation = self.claim_calls + 1
            if newly:
                self.claim_generations[expectation.attempt_subject_sha256] = generation
            observation = claim_observation(
                expectation, newly=newly, generation=generation
            )
            if self.claim_mutates_expectation:
                object.__setattr__(expectation, "claim_operation_id", "C" * 64)
            if self.claim_raises:
                raise RuntimeError("injected ambiguous durable claim result")
            if self.claim_fault is not None:
                observation = self.claim_fault(observation)
            self.last_claim_observation = observation
            return observation

    def terminalize_ambiguous_attempt_claim(
        self,
        expectation,
        *,
        claim_operation_id,
        invalidation_reason,
    ):
        with self.lock:
            self.ambiguous_terminal_calls += 1
            if self.ambiguous_fails:
                raise RuntimeError("injected ambiguous terminalization failure")
            subject = expectation.attempt_subject_sha256
            state = self.claims.get(subject)
            operation = self.claim_operations.get(subject)
            newly = state is None or (
                state == "CLAIMED" and operation == claim_operation_id
            )
            prior_generation = self.claim_generations.get(
                subject, expectation.activation_ledger_generation
            )
            if newly:
                self.claims[subject] = "INDETERMINATE"
                self.claim_operations[subject] = claim_operation_id
                self.claim_generations[subject] = prior_generation + 1
            observation = sut.StageCRuntimeAmbiguousClaimTerminalObservation(
                claim_operation_id=claim_operation_id,
                claim_state="INDETERMINATE" if newly else str(state),
                terminalized_now=newly,
                execution_ordinal=expectation.execution_ordinal,
                attempt_subject_sha256=subject,
                authenticated_tenant_id=expectation.tenant_id,
                authenticated_worker_id=expectation.assigned_worker_id,
                phase_id=expectation.phase_id,
                phase_subject_sha256=expectation.phase_subject_sha256,
                registration_sha256=expectation.registration_ref.sha256,
                roster_closure_sha256=expectation.roster_closure_sha256,
                model_capture_target_sha256=expectation.model_capture_target_sha256,
                invalidation_reason=invalidation_reason,
                prior_ledger_generation=prior_generation,
                ledger_generation=prior_generation + 1,
            )
            if self.ambiguous_fault is not None:
                observation = self.ambiguous_fault(observation)
            return observation

    def invalidate_attempt_claim(self, expectation):
        with self.lock:
            self.invalidation_calls += 1
            if self.invalidation_fails:
                raise RuntimeError("injected durable invalidation failure")
            state = self.claims.get(expectation.attempt_subject_sha256)
            newly = state == "CLAIMED"
            if newly:
                self.claims[expectation.attempt_subject_sha256] = "INDETERMINATE"
            observation = sut.StageCRuntimeAttemptInvalidationObservation(
                claim_id=expectation.claim_id,
                claim_generation=expectation.claim_generation,
                claim_state="INDETERMINATE" if newly else str(state),
                invalidated_now=newly,
                execution_ordinal=expectation.execution_ordinal,
                attempt_subject_sha256=expectation.attempt_subject_sha256,
                authenticated_tenant_id=expectation.tenant_id,
                authenticated_worker_id=expectation.assigned_worker_id,
                phase_id=expectation.phase_id,
                phase_subject_sha256=expectation.phase_subject_sha256,
                invalidation_reason=expectation.invalidation_reason,
                ledger_generation=expectation.claim_generation + 1,
            )
            if self.invalidation_fault is not None:
                observation = self.invalidation_fault(observation)
            return observation


class FakeCoordinator:
    def __init__(self, runtime: RuntimeFixture, issuance):
        self.registration = runtime.registration
        self.issuance = issuance
        self.consume_calls = 0
        self.issue_calls = 0
        self.reject_calls = 0
        self.transitioned_now = True
        self.raise_consume = False

    def issue_attempt(self, *, execution_ordinal, **kwargs):
        del kwargs
        self.issue_calls += 1
        assert execution_ordinal == self.issuance.snapshot.case_execution_ordinal
        return self.issuance

    def reject_preauthorization(self, *, execution_ordinal, **kwargs):
        del kwargs
        self.reject_calls += 1
        return ("REJECTED_PREAUTHORIZATION", execution_ordinal)

    def consume_attempt(self, **kwargs):
        self.consume_calls += 1
        if self.raise_consume:
            raise RuntimeError("injected local lifecycle CAS failure")
        return SimpleNamespace(
            transitioned_now=self.transitioned_now,
            binding=self.issuance.binding,
            authorization=self.issuance.authorization,
            snapshot=self.issuance.snapshot,
            kwargs=kwargs,
        )


def build_issuance(runtime: RuntimeFixture, ordinal: int = 1):
    request = runtime.registration.study_requests[ordinal - 1]
    subject = runtime.registration.ordered_subjects[ordinal - 1]
    ids = {
        key: f"runtime-{key.replace('_', '-')}-{ordinal:03d}"
        for key in ARTIFACT_IDS
    }
    binding = build_diagnostic_child_execution_binding(
        chain=runtime.shared.chain,
        plan=runtime.shared.plan,
        study_request=request,
        execution_contract=runtime.shared.execution_contract,
        binding_id=f"stagec-runtime-child-binding-{ordinal:03d}",
        created_at="2026-08-09T09:20:00Z",
        run_nonce=ordinal.to_bytes(32, "big"),
        assigned_worker_id=ROW_WORKER,
        archive_root=f"C:/cas-harness/stagec/runtime-child-{ordinal:03d}",
        artifact_ids=ids,
    )
    authorization = build_diagnostic_worker_authorization_v2(
        chain=runtime.shared.chain,
        plan=runtime.shared.plan,
        study_request=request,
        execution_contract=runtime.shared.execution_contract,
        binding=binding,
        issued_at="2026-08-09T09:21:00Z",
        expires_at="2026-08-09T10:55:00Z",
    )
    assert subject == derive_diagnostic_attempt_subject_sha256(
        plan=runtime.shared.plan, study_request=request
    )
    snapshot = SimpleNamespace(
        tenant_id=TENANT,
        attempt_subject_sha256=subject,
        case_execution_ordinal=ordinal,
    )
    return SimpleNamespace(
        snapshot=snapshot,
        binding=binding,
        authorization=authorization,
        run_nonce_b64url=binding.run_nonce_b64url,
        issued_now=True,
    )


def activated_wrapper(runtime: RuntimeFixture, *, backend=None, issuance=None):
    backend = TestBackend() if backend is None else backend
    preparation = prepare(runtime)
    activation = sut.activate_stagec_runtime_phase(
        preparation,
        backend=backend,
        authenticated_worker_id=CONTROL_WORKER,
    )
    issuance = build_issuance(runtime) if issuance is None else issuance
    coordinator = FakeCoordinator(runtime, issuance)
    wrapper = sut.ActivatedDiagnosticPhaseCoordinator(
        coordinator=coordinator,
        preparation=preparation,
        activation=activation,
    )
    issued = wrapper.issue_attempt(execution_ordinal=1)
    assert issued is issuance
    return backend, preparation, activation, coordinator, wrapper, issuance


def consume_kwargs(runtime: RuntimeFixture, issuance):
    ordinal = issuance.snapshot.case_execution_ordinal
    return {
        "execution_ordinal": ordinal,
        "study_request": runtime.registration.study_requests[ordinal - 1],
        "attempt_subject_sha256": runtime.registration.ordered_subjects[ordinal - 1],
        "child_binding": issuance.binding,
        "worker_authorization": issuance.authorization,
        "model_capture_target": runtime.target,
        "run_nonce_b64url": issuance.run_nonce_b64url,
        "worker_started_at": CLAIM_TIME,
        "operation_id": f"stagec-runtime-consume-{ordinal:03d}",
    }


def redeem_kwargs(runtime: RuntimeFixture, activation, issuance):
    values = consume_kwargs(runtime, issuance)
    values.pop("run_nonce_b64url")
    values.pop("worker_started_at")
    values.pop("operation_id")
    values["activation"] = activation
    return values


def test_preparation_fresh_replays_exact_chain_roster_target_and_preserves_statuses(
    runtime_fixture,
):
    preparation = prepare(runtime_fixture)
    assert preparation.control_state == sut.STAGEC_RUNTIME_PREPARED
    assert preparation.tenant_id == TENANT
    assert len(preparation.phase_registration.ordered_subjects) == 480
    assert preparation.model_capture_target is runtime_fixture.target
    assert sut.STAGEC_RUNTIME_GATE_5_STATUS == "OPEN / KEEP_OPEN"
    assert sut.STAGEC_RUNTIME_STAGE_C_STATUS == (
        "DESIGN_ONLY / UNAUTHORIZED / NOT_STARTED"
    )
    assert sut.STAGEC_RUNTIME_PROJECT_STATUS == "NOT LICENSED / HELD / NOT FROZEN"
    assert sut.STAGEC_RUNTIME_SERIALIZED_AUTHORITY == "NONE"
    assert "claim_stagec_runtime_attempt" not in sut.__all__
    assert not hasattr(sut, "claim_stagec_runtime_attempt")
    with pytest.raises(sut.StageCRuntimeActivationError) as canary:
        sut.require_stagec_runtime_startup_canary()
    assert canary.value.error_code == "STARTUP_CANARY_FORBIDDEN"


def test_unavailable_and_arbitrary_backend_fail_before_state_or_backend_mutation(
    runtime_fixture,
):
    preparation = prepare(runtime_fixture)
    with pytest.raises(sut.StageCRuntimeActivationError) as unavailable:
        sut.activate_stagec_runtime_phase(
            preparation,
            backend=sut.UnavailableStageCRuntimeActivationBackend(),
            authenticated_worker_id=CONTROL_WORKER,
        )
    assert unavailable.value.error_code == "BACKEND_UNAVAILABLE"
    assert preparation.control_state == sut.STAGEC_RUNTIME_PREPARED

    class ArbitraryBackend(sut.StageCRuntimeActivationBackend):
        calls = 0

        def activate_phase(self, expectation):
            self.calls += 1

    arbitrary = ArbitraryBackend()
    with pytest.raises(sut.StageCRuntimeActivationError) as rejected:
        sut.activate_stagec_runtime_phase(
            preparation,
            backend=arbitrary,
            authenticated_worker_id=CONTROL_WORKER,
        )
    assert rejected.value.error_code == "BACKEND_NOT_TRUSTED"
    assert arbitrary.calls == 0
    assert preparation.control_state == sut.STAGEC_RUNTIME_PREPARED


def test_phase_nonce_is_consumed_once_and_duplicate_activation_fails_closed(
    runtime_fixture,
):
    backend = TestBackend()
    first = prepare(runtime_fixture)
    activation = sut.activate_stagec_runtime_phase(
        first, backend=backend, authenticated_worker_id=CONTROL_WORKER
    )
    assert activation.control_state == sut.STAGEC_RUNTIME_ROWS_ENABLED
    assert backend.phase_calls == 1
    with pytest.raises(sut.StageCRuntimeActivationError) as duplicate_local:
        sut.activate_stagec_runtime_phase(
            first, backend=backend, authenticated_worker_id=CONTROL_WORKER
        )
    assert duplicate_local.value.error_code == "PHASE_ALREADY_ACTIVATED"
    assert backend.phase_calls == 1

    second = prepare(runtime_fixture)
    with pytest.raises(sut.StageCRuntimeActivationError) as duplicate_durable:
        sut.activate_stagec_runtime_phase(
            second, backend=backend, authenticated_worker_id=CONTROL_WORKER
        )
    assert duplicate_durable.value.error_code in {
        "PHASE_BINDING_MISMATCH",
        "PHASE_NONCE_NOT_NEWLY_CONSUMED",
    }
    assert second.control_state == sut.STAGEC_RUNTIME_ACTIVATION_INDETERMINATE
    assert backend.phase_calls == 2


@pytest.mark.parametrize(
    "fault",
    (
        lambda row: replace(
            row,
            storage=replace(row.storage, authenticated_tenant_id="tenant-other"),
        ),
        lambda row: replace(
            row,
            storage=replace(row.storage, object_version_id="version-other"),
        ),
        lambda row: replace(
            row,
            storage=replace(row.storage, checksum_sha256="F" * 64),
        ),
        lambda row: replace(
            row,
            storage=replace(row.storage, retention_until="2026-08-09T10:30:00Z"),
        ),
        lambda row: replace(
            row,
            storage=replace(row.storage, trusted_time="2026-08-09T11:00:00Z"),
        ),
        lambda row: replace(
            row,
            authorization=replace(row.authorization, authorization_id="auth-other"),
        ),
        lambda row: replace(
            row,
            authorization=replace(row.authorization, nonce_b64url="A" * 43),
        ),
        lambda row: replace(row, roster_closure_sha256="E" * 64),
        lambda row: replace(row, model_capture_target_sha256="D" * 64),
    ),
)
def test_phase_storage_time_auth_tenant_roster_and_target_drift_terminalize(
    runtime_fixture, fault
):
    preparation = prepare(runtime_fixture)
    backend = TestBackend(phase_fault=fault)
    with pytest.raises(sut.StageCRuntimeActivationError) as observed:
        sut.activate_stagec_runtime_phase(
            preparation, backend=backend, authenticated_worker_id=CONTROL_WORKER
        )
    assert observed.value.error_code in sut.STAGEC_RUNTIME_ACTIVATION_ERROR_CODES
    assert preparation.control_state == sut.STAGEC_RUNTIME_ACTIVATION_INDETERMINATE


def test_wrapper_requires_activation_but_allows_preauthorization_rejection(
    runtime_fixture,
):
    preparation = prepare(runtime_fixture)
    issuance = build_issuance(runtime_fixture)
    coordinator = FakeCoordinator(runtime_fixture, issuance)
    wrapper = sut.ActivatedDiagnosticPhaseCoordinator(
        coordinator=coordinator,
        preparation=preparation,
        activation=None,
    )
    assert wrapper.reject_preauthorization(execution_ordinal=1) == (
        "REJECTED_PREAUTHORIZATION",
        1,
    )
    with pytest.raises(sut.StageCRuntimeActivationError) as issue:
        wrapper.issue_attempt(execution_ordinal=1)
    assert issue.value.error_code == "PHASE_NOT_ROWS_ENABLED"


def test_exact_issue_claim_local_cas_and_single_use_redeem(runtime_fixture):
    backend, _, activation, coordinator, wrapper, issuance = activated_wrapper(
        runtime_fixture
    )
    consumed = wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
    permit = consumed.dispatch_permit
    assert consumed.mutation.transitioned_now is True
    assert permit.control_state == sut.STAGEC_RUNTIME_PERMIT_UNREDEEMED
    assert backend.claim_calls == 1
    assert coordinator.consume_calls == 1

    wrong = redeem_kwargs(runtime_fixture, activation, issuance)
    wrong["attempt_subject_sha256"] = runtime_fixture.registration.ordered_subjects[1]
    with pytest.raises(sut.StageCRuntimeActivationError) as substituted:
        sut.redeem_stagec_runtime_dispatch_permit(permit, **wrong)
    assert substituted.value.error_code == "PERMIT_BINDING_MISMATCH"
    assert permit.control_state == sut.STAGEC_RUNTIME_PERMIT_INVALIDATED
    assert backend.invalidation_calls == 1
    with pytest.raises(sut.StageCRuntimeActivationError) as invalidated_retry:
        sut.redeem_stagec_runtime_dispatch_permit(
            permit, **redeem_kwargs(runtime_fixture, activation, issuance)
        )
    assert invalidated_retry.value.error_code == "PERMIT_INVALIDATED"

    _, _, fresh_activation, _, fresh_wrapper, fresh_issuance = activated_wrapper(
        runtime_fixture
    )
    fresh_consumed = fresh_wrapper.consume_attempt(
        **consume_kwargs(runtime_fixture, fresh_issuance)
    )
    fresh_permit = fresh_consumed.dispatch_permit

    assert (
        sut.redeem_stagec_runtime_dispatch_permit(
            fresh_permit,
            **redeem_kwargs(runtime_fixture, fresh_activation, fresh_issuance),
        )
        is None
    )
    assert fresh_permit.control_state == sut.STAGEC_RUNTIME_PERMIT_REDEEMED
    with pytest.raises(sut.StageCRuntimeActivationError) as second:
        sut.redeem_stagec_runtime_dispatch_permit(
            fresh_permit,
            **redeem_kwargs(runtime_fixture, fresh_activation, fresh_issuance),
        )
    assert second.value.error_code == "PERMIT_ALREADY_REDEEMED"


def test_duplicate_consume_never_returns_a_second_permit(runtime_fixture):
    backend, _, _, coordinator, wrapper, issuance = activated_wrapper(runtime_fixture)
    first = wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
    assert first.dispatch_permit.control_state == sut.STAGEC_RUNTIME_PERMIT_UNREDEEMED
    with pytest.raises(sut.StageCRuntimeActivationError) as duplicate:
        wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
    assert duplicate.value.error_code == "ATTEMPT_ALREADY_CLAIMED"
    assert backend.claim_calls == 1
    assert coordinator.consume_calls == 1


def test_all_local_attempt_binding_substitutions_fail_before_durable_claim(
    runtime_fixture,
):
    backend, _, _, _, wrapper, issuance = activated_wrapper(runtime_fixture)
    for field in (
        "ordinal",
        "request",
        "subject",
        "binding",
        "authorization",
        "target",
        "run_nonce",
    ):
        values = consume_kwargs(runtime_fixture, issuance)
        if field == "ordinal":
            values["execution_ordinal"] = 2
        elif field == "request":
            values["study_request"] = runtime_fixture.registration.study_requests[1]
        elif field == "subject":
            values["attempt_subject_sha256"] = runtime_fixture.registration.ordered_subjects[1]
        elif field == "binding":
            values["child_binding"] = replace(issuance.binding)
        elif field == "authorization":
            values["worker_authorization"] = replace(issuance.authorization)
        elif field == "target":
            forged = object.__new__(sut.StageCRuntimeModelCaptureTarget)
            for name in (
                "model_identity_sha256",
                "capture_profile_sha256",
                "model_contract_sha256",
                "runtime_contract_sha256",
                "capture_contract_sha256",
                "target_sha256",
            ):
                object.__setattr__(forged, name, getattr(runtime_fixture.target, name))
            values["model_capture_target"] = forged
        else:
            values["run_nonce_b64url"] = "A" * 43
        with pytest.raises(sut.StageCRuntimeActivationError) as observed:
            wrapper.consume_attempt(**values)
        assert observed.value.error_code in {
            "ATTEMPT_BINDING_INVALID",
            "ATTEMPT_OUTSIDE_ROSTER",
            "MODEL_CAPTURE_TARGET_INVALID",
            "PERMIT_BINDING_MISMATCH",
        }, field
        assert backend.claim_calls == 0, field


def test_claim_storage_time_auth_worker_lease_and_roster_drift_never_release_permit(
    runtime_fixture,
):
    faults = (
        lambda row: replace(
            row, storage=replace(row.storage, object_key="other/object")
        ),
        lambda row: replace(
            row, storage=replace(row.storage, object_version_id="other-version")
        ),
        lambda row: replace(
            row, storage=replace(row.storage, trusted_time="2026-08-09T11:00:00Z")
        ),
        lambda row: replace(
            row, storage=replace(row.storage, observation_generation=1)
        ),
        lambda row: replace(
            row, authorization=replace(row.authorization, ledger_generation=1)
        ),
        lambda row: replace(
            row,
            authorization=replace(row.authorization, nonce_state_after="UNCONSUMED"),
        ),
        lambda row: replace(
            row,
            authorization=replace(row.authorization, authenticated_worker_id="worker-other"),
        ),
        lambda row: replace(
            row,
            worker_lease=replace(row.worker_lease, expires_at="2026-08-09T10:04:00Z"),
        ),
        lambda row: replace(row, claim_operation_id="C" * 64),
        lambda row: replace(row, study_request_sha256="C" * 64),
        lambda row: replace(row, claimed_now=False),
    )
    backend = TestBackend()
    backend, _, _, coordinator, wrapper, issuance = activated_wrapper(
        runtime_fixture, backend=backend
    )
    for ordinal, fault in enumerate(faults, start=1):
        if ordinal != 1:
            issuance = build_issuance(runtime_fixture, ordinal)
            coordinator.issuance = issuance
            assert wrapper.issue_attempt(execution_ordinal=ordinal) is issuance
        backend.claim_fault = fault
        with pytest.raises(sut.StageCRuntimeActivationError) as observed:
            wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
        assert observed.value.error_code in sut.STAGEC_RUNTIME_ACTIVATION_ERROR_CODES, ordinal
        assert backend.claim_calls == ordinal
        assert coordinator.consume_calls == 0
        with pytest.raises(sut.StageCRuntimeActivationError) as retry:
            wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
        assert retry.value.error_code == "ATTEMPT_CLAIM_INDETERMINATE", ordinal


def test_ambiguous_claim_exception_and_terminal_receipt_fault_are_never_retryable(
    runtime_fixture,
):
    cases = (
        (TestBackend(claim_raises=True), "BACKEND_OPERATION_FAILED"),
        (
            TestBackend(
                claim_raises=True,
                ambiguous_fault=lambda row: replace(
                    row, ledger_generation=row.prior_ledger_generation
                ),
            ),
            "AMBIGUOUS_CLAIM_TERMINAL_BINDING_MISMATCH",
        ),
    )
    for backend, expected_code in cases:
        backend, _, _, coordinator, wrapper, issuance = activated_wrapper(
            runtime_fixture, backend=backend
        )
        with pytest.raises(sut.StageCRuntimeActivationError) as ambiguous:
            wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
        assert ambiguous.value.error_code == expected_code
        subject = issuance.snapshot.attempt_subject_sha256
        assert backend.claims[subject] == "INDETERMINATE"
        assert backend.ambiguous_terminal_calls == 1
        assert coordinator.consume_calls == 0
        with pytest.raises(sut.StageCRuntimeActivationError) as retry:
            wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
        assert retry.value.error_code in {
            "ATTEMPT_ALREADY_CLAIMED",
            "ATTEMPT_CLAIM_INDETERMINATE",
        }
        assert backend.claim_calls == 1


def test_backend_expectation_mutation_never_rewrites_private_authority(
    runtime_fixture,
):
    for raises, expected_code in (
        (False, "PHASE_OBSERVATION_INVALID"),
        (True, "BACKEND_OPERATION_FAILED"),
    ):
        preparation = prepare(runtime_fixture)
        backend = TestBackend(
            phase_mutates_expectation=True,
            phase_raises=raises,
        )
        with pytest.raises(sut.StageCRuntimeActivationError) as phase:
            sut.activate_stagec_runtime_phase(
                preparation,
                backend=backend,
                authenticated_worker_id=CONTROL_WORKER,
            )
        assert phase.value.error_code == expected_code
        assert preparation.control_state == sut.STAGEC_RUNTIME_ACTIVATION_INDETERMINATE
        assert backend.phase_calls == 1

    for raises, expected_code in (
        (False, "CLAIM_OBSERVATION_INVALID"),
        (True, "BACKEND_OPERATION_FAILED"),
    ):
        backend = TestBackend(
            claim_mutates_expectation=True,
            claim_raises=raises,
        )
        backend, _, _, coordinator, wrapper, issuance = activated_wrapper(
            runtime_fixture,
            backend=backend,
        )
        with pytest.raises(sut.StageCRuntimeActivationError) as claim:
            wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
        assert claim.value.error_code == expected_code
        subject = issuance.snapshot.attempt_subject_sha256
        assert backend.claims[subject] == "INDETERMINATE"
        assert backend.ambiguous_terminal_calls == 1
        assert coordinator.consume_calls == 0
        with pytest.raises(sut.StageCRuntimeActivationError) as retry:
            wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
        assert retry.value.error_code in {
            "ATTEMPT_ALREADY_CLAIMED",
            "ATTEMPT_CLAIM_INDETERMINATE",
        }


def test_public_preparation_forgery_rejects_before_phase_backend(runtime_fixture):
    preparation = prepare(runtime_fixture)
    backend = TestBackend()
    storage = preparation.external_binding.snapshot.trusted_storage
    original = storage.object_version_id
    object.__setattr__(storage, "object_version_id", "forged-storage-version")
    try:
        with pytest.raises(sut.StageCRuntimeActivationError) as forged:
            sut.activate_stagec_runtime_phase(
                preparation,
                backend=backend,
                authenticated_worker_id=CONTROL_WORKER,
            )
        assert forged.value.error_code == "PREPARATION_INVALID"
        assert backend.phase_calls == 0
    finally:
        object.__setattr__(storage, "object_version_id", original)
    assert preparation.control_state == sut.STAGEC_RUNTIME_PREPARED


def test_backend_owned_phase_and_claim_observation_mutation_is_detached(
    runtime_fixture,
):
    backend, _, activation, _, wrapper, issuance = activated_wrapper(runtime_fixture)
    assert activation.observation is not backend.last_phase_observation
    object.__setattr__(
        backend.last_phase_observation.storage,
        "provider_id",
        "forged-retained-provider",
    )
    consumed = wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
    assert consumed.dispatch_permit.control_state == sut.STAGEC_RUNTIME_PERMIT_UNREDEEMED
    object.__setattr__(
        backend.last_claim_observation,
        "claim_id",
        "forged-retained-claim",
    )
    sut.redeem_stagec_runtime_dispatch_permit(
        consumed.dispatch_permit,
        **redeem_kwargs(runtime_fixture, activation, issuance),
    )
    assert consumed.dispatch_permit.control_state == sut.STAGEC_RUNTIME_PERMIT_REDEEMED
    assert backend.invalidation_calls == 0


def test_public_activation_or_preparation_drift_terminalizes_won_claim(
    runtime_fixture,
):
    for drift_kind in ("activation", "activation_nested", "preparation"):
        backend, preparation, activation, _, wrapper, issuance = activated_wrapper(
            runtime_fixture
        )
        consumed = wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
        permit = consumed.dispatch_permit
        if drift_kind == "activation":
            carrier = activation.observation.storage
            field = "provider_id"
            forged = "forged-public-provider"
        elif drift_kind == "activation_nested":
            carrier = activation.observation
            field = "storage"
            forged = object()
        else:
            carrier = preparation.external_binding.snapshot.trusted_storage
            field = "object_version_id"
            forged = "forged-public-version"
        original = getattr(carrier, field)
        object.__setattr__(carrier, field, forged)
        try:
            with pytest.raises(sut.StageCRuntimeActivationError) as drift:
                sut.redeem_stagec_runtime_dispatch_permit(
                    permit,
                    **redeem_kwargs(runtime_fixture, activation, issuance),
                )
            assert drift.value.error_code in {
                "PHASE_NOT_ROWS_ENABLED",
                "PREPARATION_INVALID",
            }
        finally:
            object.__setattr__(carrier, field, original)
        assert permit.control_state == sut.STAGEC_RUNTIME_PERMIT_INVALIDATED
        assert backend.invalidation_calls == 1
        assert backend.claims[issuance.snapshot.attempt_subject_sha256] == "INDETERMINATE"
        with pytest.raises(sut.StageCRuntimeActivationError) as retry:
            sut.redeem_stagec_runtime_dispatch_permit(
                permit,
                **redeem_kwargs(runtime_fixture, activation, issuance),
            )
        assert retry.value.error_code == "PERMIT_INVALIDATED"


def test_local_cas_false_durably_invalidates_claim_and_forbids_dispatch(runtime_fixture):
    backend, _, activation, coordinator, wrapper, issuance = activated_wrapper(
        runtime_fixture
    )
    coordinator.transitioned_now = False
    with pytest.raises(sut.StageCRuntimeActivationError) as local:
        wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
    assert local.value.error_code == "ATTEMPT_BINDING_INVALID"
    subject = runtime_fixture.registration.ordered_subjects[0]
    assert backend.claims[subject] == "INDETERMINATE"
    assert backend.invalidation_calls == 1
    assert backend.claim_calls == 1
    assert activation.control_state == sut.STAGEC_RUNTIME_ROWS_ENABLED


def test_invalidation_backend_fault_burns_permit_and_forbids_retry(runtime_fixture):
    backend = TestBackend(invalidation_fails=True)
    backend, _, _, coordinator, wrapper, issuance = activated_wrapper(
        runtime_fixture, backend=backend
    )
    coordinator.raise_consume = True
    with pytest.raises(sut.StageCRuntimeActivationError) as indeterminate:
        wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
    assert indeterminate.value.error_code == "CLAIM_INVALIDATION_FAILED"
    assert backend.invalidation_calls == 1
    with pytest.raises(sut.StageCRuntimeActivationError) as retry:
        wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
    assert retry.value.error_code in {
        "ATTEMPT_ALREADY_CLAIMED",
        "ATTEMPT_CLAIM_INDETERMINATE",
    }
    assert backend.claim_calls == 1


def test_explicit_mark_indeterminate_api_invalidates_unredeemed_permit(runtime_fixture):
    backend, _, activation, _, wrapper, issuance = activated_wrapper(runtime_fixture)
    consumed = wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
    permit = consumed.dispatch_permit
    wrong = redeem_kwargs(runtime_fixture, activation, issuance)
    wrong["attempt_subject_sha256"] = runtime_fixture.registration.ordered_subjects[1]
    with pytest.raises(sut.StageCRuntimeActivationError) as wrong_use:
        sut.mark_stagec_runtime_attempt_indeterminate(
            permit,
            **wrong,
            invalidation_reason="POST_CLAIM_PRE_DISPATCH_FAILURE",
        )
    assert wrong_use.value.error_code == "PERMIT_BINDING_MISMATCH"
    assert permit.control_state == sut.STAGEC_RUNTIME_PERMIT_INVALIDATED
    assert backend.invalidation_calls == 1
    with pytest.raises(sut.StageCRuntimeActivationError) as retry:
        sut.mark_stagec_runtime_attempt_indeterminate(
            permit,
            **redeem_kwargs(runtime_fixture, activation, issuance),
            invalidation_reason="POST_CLAIM_PRE_DISPATCH_FAILURE",
        )
    assert retry.value.error_code == "PERMIT_INVALIDATED"
    with pytest.raises(sut.StageCRuntimeActivationError) as dispatch:
        sut.redeem_stagec_runtime_dispatch_permit(
            permit, **redeem_kwargs(runtime_fixture, activation, issuance)
        )
    assert dispatch.value.error_code == "PERMIT_INVALIDATED"


def test_equal_generation_invalidation_is_indeterminate_and_cannot_dispatch(
    runtime_fixture,
):
    backend = TestBackend(
        invalidation_fault=lambda row: replace(
            row, ledger_generation=row.claim_generation
        )
    )
    backend, _, activation, _, wrapper, issuance = activated_wrapper(
        runtime_fixture, backend=backend
    )
    consumed = wrapper.consume_attempt(**consume_kwargs(runtime_fixture, issuance))
    permit = consumed.dispatch_permit
    with pytest.raises(sut.StageCRuntimeActivationError) as equal_generation:
        sut.mark_stagec_runtime_attempt_indeterminate(
            permit,
            **redeem_kwargs(runtime_fixture, activation, issuance),
            invalidation_reason="POST_CLAIM_PRE_DISPATCH_FAILURE",
        )
    assert equal_generation.value.error_code == "INVALIDATION_BINDING_MISMATCH"
    assert permit.control_state == sut.STAGEC_RUNTIME_PERMIT_INDETERMINATE
    with pytest.raises(sut.StageCRuntimeActivationError) as dispatch:
        sut.redeem_stagec_runtime_dispatch_permit(
            permit, **redeem_kwargs(runtime_fixture, activation, issuance)
        )
    assert dispatch.value.error_code == "PERMIT_INDETERMINATE"


def test_object_and_dataclass_forgeries_are_not_process_sealed(runtime_fixture):
    forged_preparation = object.__new__(sut.StageCRuntimePreparation)
    with pytest.raises(sut.StageCRuntimeActivationError) as prep_error:
        sut.stagec_runtime_preparation_state(forged_preparation)
    assert prep_error.value.error_code == "PREPARATION_INVALID"
    forged_permit = object.__new__(sut.StageCRuntimeDispatchPermit)
    with pytest.raises(sut.StageCRuntimeActivationError) as permit_error:
        sut.stagec_runtime_dispatch_permit_state(forged_permit)
    assert permit_error.value.error_code == "PERMIT_INVALID"
    with pytest.raises(TypeError):
        replace(runtime_fixture.target, target_sha256="F" * 64)


def test_concurrent_consume_has_exactly_one_durable_and_local_winner(runtime_fixture):
    backend, _, _, coordinator, wrapper, issuance = activated_wrapper(runtime_fixture)
    barrier = threading.Barrier(12)
    results = []
    result_lock = threading.Lock()

    def compete(index):
        barrier.wait()
        try:
            value = wrapper.consume_attempt(
                **{
                    **consume_kwargs(runtime_fixture, issuance),
                    "operation_id": f"stagec-runtime-race-{index:02d}",
                }
            )
        except sut.StageCRuntimeActivationError as exc:
            value = exc.error_code
        with result_lock:
            results.append(value)

    threads = [threading.Thread(target=compete, args=(index,)) for index in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads)
    winners = [
        item for item in results if isinstance(item, sut.ActivatedDiagnosticAttemptConsumption)
    ]
    assert len(winners) == 1
    assert results.count("ATTEMPT_ALREADY_CLAIMED") == 11
    assert backend.claim_calls == 1
    assert coordinator.consume_calls == 1
