from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import struct
import sys
from types import MappingProxyType
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TEST_DIR = Path(__file__).resolve().parent
for candidate in (SRC, TEST_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from cas_harness_v2._strict_json import canonical_json_bytes, sha256_bytes  # noqa: E402
from cas_harness_v2.diagnostic_calibration_fit import (  # noqa: E402
    ELIGIBLE_THRESHOLD_SELECTED,
    TARGET_LAYER_DETECTOR,
    WRONG_LAYER_CONTROL_DETECTOR,
    DiagnosticBinary64,
    DiagnosticCalibrationFitValidationError,
    DiagnosticCalibrationRuntimeVersionError,
    bind_diagnostic_calibration_rule_to_plan,
    build_diagnostic_calibration_activation_dataset,
    build_diagnostic_calibration_fit_transcript,
    build_diagnostic_calibration_rule,
    diagnostic_calibration_model_fit,
    derive_diagnostic_calibration_candidate_results,
    load_diagnostic_calibration_activation_dataset,
    load_diagnostic_calibration_fit_transcript,
    replay_diagnostic_calibration_activation_dataset_projection,
    replay_diagnostic_calibration_fit_transcript_projection,
    replay_diagnostic_calibration_rule_projection,
)
import cas_harness_v2.diagnostic_calibration_fit as fit_module  # noqa: E402
from cas_harness_v2.diagnostic_execution_protocol import (  # noqa: E402
    build_diagnostic_stagec_execution_contract,
)
from cas_harness_v2.diagnostic_lifecycle import (  # noqa: E402
    build_diagnostic_shared_plan_replay_context,
)
from cas_harness_v2.diagnostic_phase_coordinator import (  # noqa: E402
    DiagnosticPhaseCoordinator,
    build_diagnostic_phase_registration,
    build_diagnostic_phase_store_binding,
)
from cas_harness_v2.diagnostic_preregistration import (  # noqa: E402
    DiagnosticPreregistrationChain,
    load_diagnostic_preregistration,
)
from cas_harness_v2.diagnostic_study_protocol import (  # noqa: E402
    build_diagnostic_split_inventory,
    build_diagnostic_study_plan,
)
from test_diagnostic_execution_protocol import ARTIFACT_IDS  # noqa: E402
from test_diagnostic_phase_coordinator import (  # noqa: E402
    capture_archive,
    completed_artifacts,
    ref_value,
)
from test_diagnostic_study_protocol import (  # noqa: E402
    amendment_value,
    base_value,
    make_capture_requests,
)


_LOCK = {
    "numpy": "2.5.1",
    "scikit-learn": "1.9.0",
    "scipy": "1.18.0",
}


def mutate(raw: bytes, change) -> bytes:
    value = json.loads(raw)
    change(value)
    return canonical_json_bytes(value)


def binary64(value: float) -> DiagnosticBinary64:
    return DiagnosticBinary64(
        hex=value.hex(),
        bytes_hex=struct.pack(">d", value).hex().upper(),
        decimal=repr(value),
    )


def test_cheap_prospective_rule_freezes_exact_runtime_and_algorithm() -> None:
    rule = build_diagnostic_calibration_rule(
        rule_id="diagnostic-calibration-rule-cheap-001",
        created_at="2026-08-08T08:04:00Z",
    )
    assert replay_diagnostic_calibration_rule_projection(rule) == rule
    assert rule.runtime_versions == _LOCK
    assert rule.payload["logistic_regression"] == {
        "class": "sklearn.linear_model.LogisticRegression",
        "penalty": "l2",
        "C_binary64_hex": "0x1.0000000000000p-2",
        "C_binary64_bytes_hex": "3FD0000000000000",
        "l1_ratio_binary64_hex": "0x0.0p+0",
        "dual": False,
        "tol_binary64_hex": "0x1.5798ee2308c3ap-27",
        "fit_intercept": True,
        "intercept_scaling": 1,
        "class_weight": "balanced",
        "random_state": 42,
        "solver": "lbfgs",
        "max_iter": 1000,
        "verbose": 0,
        "warm_start": False,
        "n_jobs": 1,
        "classes": ("ABSENT", "PRESENT"),
        "positive_class_index": 1,
        "score_carrier": "predict_proba[:,positive_class_index]",
    }
    assert rule.payload["scientific_correctness"] == "NOT_ESTABLISHED"
    for forged in (
        replace(rule, raw_bytes=bytearray(rule.raw_bytes)),
        replace(rule, runtime_versions=dict(rule.runtime_versions)),
        replace(rule, payload=dict(rule.payload)),
    ):
        with pytest.raises(
            DiagnosticCalibrationFitValidationError,
            match="exact immutable|recursively immutable",
        ):
            replay_diagnostic_calibration_rule_projection(forged)

    external_runtime = dict(rule.runtime_versions)
    external_payload = dict(rule.payload)
    caller_owned = replace(
        rule,
        runtime_versions=MappingProxyType(external_runtime),
        payload=MappingProxyType(external_payload),
    )
    fresh = replay_diagnostic_calibration_rule_projection(caller_owned)
    assert fresh == rule and fresh is not caller_owned
    assert fresh.runtime_versions is not caller_owned.runtime_versions
    assert fresh.payload is not caller_owned.payload
    external_runtime["numpy"] = "MUTATED_AFTER_REPLAY"
    external_payload["scientific_correctness"] = "FABRICATED"
    assert fresh.runtime_versions == _LOCK
    assert fresh.payload["scientific_correctness"] == "NOT_ESTABLISHED"


def test_cheap_candidate_derivation_predictions_confusion_and_tie_break() -> None:
    variants = tuple(
        ("ADVERSARIAL_PRESENT", "CLEAN_ABSENT", "CLEAN_NULL_ABSENT")[index % 3]
        for index in range(480)
    )
    scores = tuple(binary64(0.9 if index % 3 == 0 else 0.1) for index in range(480))
    candidates, status, threshold, predictions = (
        derive_diagnostic_calibration_candidate_results(scores, variants)
    )
    assert len(candidates) == 7
    assert status == ELIGIBLE_THRESHOLD_SELECTED
    assert threshold == binary64(0.9)
    assert predictions == tuple(int(index % 3 == 0) for index in range(480))
    selected = next(item for item in candidates if item.threshold == threshold)
    assert (
        selected.adversarial_true_positives,
        selected.adversarial_false_negatives,
        selected.clean_true_negatives,
        selected.clean_false_positives,
        selected.clean_null_true_negatives,
        selected.clean_null_false_positives,
    ) == (160, 0, 160, 0, 160, 0)
    assert selected.balanced_accuracy.value == 1.0 and selected.eligible


def test_cheap_runtime_lock_rejects_each_package_drift_before_fit() -> None:
    for package, version in (
        ("numpy", "2.5.0"),
        ("scikit-learn", "1.8.0"),
        ("scipy", "1.17.1"),
    ):
        observed = dict(_LOCK)
        observed[package] = version
        with (
            patch.object(
                fit_module, "_observed_runtime_versions", return_value=observed
            ),
            pytest.raises(DiagnosticCalibrationRuntimeVersionError, match="version drift"),
        ):
            fit_module._require_runtime_lock()


def _build_bound_phase(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    capture_requests = make_capture_requests()
    rule = build_diagnostic_calibration_rule(
        rule_id="diagnostic-calibration-rule-fit-001",
        created_at="2026-08-08T08:04:00Z",
    )
    store_binding = build_diagnostic_phase_store_binding(
        binding_id="diagnostic-phase-store-fit-001",
        created_at="2026-08-08T08:05:00Z",
        database_path=root / "phase.sqlite3",
    )
    inventory = build_diagnostic_split_inventory(
        inventory_id="stagec-calibration-inventory-fit-001",
        capture_requests=capture_requests,
    )
    base = load_diagnostic_preregistration(canonical_json_bytes(base_value(inventory)))
    chain = DiagnosticPreregistrationChain(base)
    identity = amendment_value(
        base,
        amendment_id="AMD-CAL-FIT-001",
        created_at="2026-08-08T08:10:00Z",
        previous_sha256=None,
        change_class="EXECUTION_IDENTITY_ADDITION",
    )
    identity["changes"]["additional_artifacts"].extend(
        [ref_value(store_binding.artifact_ref), ref_value(rule.artifact_ref)]
    )
    identity_artifact = chain.append_amendment(canonical_json_bytes(identity))
    window = amendment_value(
        base,
        amendment_id="AMD-CAL-FIT-002",
        created_at="2026-08-08T08:20:00Z",
        previous_sha256=identity_artifact.sha256,
        change_class="EXECUTION_WINDOW",
    )
    chain.append_amendment(canonical_json_bytes(window))
    plan = build_diagnostic_study_plan(
        chain=chain,
        inventory=inventory,
        plan_id="stagec-diagnostic-plan-fit-001",
        created_at="2026-08-08T08:30:00Z",
    )
    contract = build_diagnostic_stagec_execution_contract(
        chain=chain,
        plan=plan,
        contract_id="diagnostic-stagec-contract-fit-001",
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
        registration_id="diagnostic-phase-registration-fit-001",
        phase_id="diagnostic-calibration-phase-fit-001",
        registered_at="2026-08-08T08:41:00Z",
        tenant_id="tenant-diagnostic-calibration-fit",
        shared_plan_context=shared,
        study_requests=requests,
        store_binding=store_binding,
    )
    coordinator = DiagnosticPhaseCoordinator(
        registration=registration,
        shared_plan_context=shared,
        nonce_factory=lambda count, state=iter(range(20_000, 21_000)): next(state).to_bytes(
            count, "big"
        ),
    )
    for ordinal, request in enumerate(registration.study_requests, start=1):
        suffix = f"{ordinal:03d}"
        artifact_ids = {
            key: f"fit-{key.replace('_', '-')}-{suffix}" for key in ARTIFACT_IDS
        }
        issuance = coordinator.issue_attempt(
            execution_ordinal=ordinal,
            binding_id=f"fit-binding-{suffix}",
            binding_created_at="2026-08-08T08:45:00Z",
            assigned_worker_id="diagnostic-worker-fit",
            archive_root=f"C:/cas-harness/stagec/clean-child-{suffix}",
            artifact_ids=artifact_ids,
            issued_at="2026-08-08T08:50:00Z",
            expires_at="2026-08-08T11:00:00Z",
            operation_id=f"fit-issue-{suffix}",
        )
        coordinator.consume_attempt(
            attempt_subject_sha256=issuance.snapshot.attempt_subject_sha256,
            run_nonce_b64url=issuance.run_nonce_b64url,
            worker_started_at="2026-08-08T09:05:00Z",
            operation_id=f"fit-consume-{suffix}",
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
            operation_id=f"fit-terminal-{suffix}",
        )
    reconciliation = coordinator.reconcile_and_seal(
        reconciliation_id="diagnostic-phase-reconciliation-fit-001",
        closed_at="2026-08-08T09:07:00Z",
    )
    access = coordinator.record_aggregate_outcome_access(
        access_id="diagnostic-phase-outcome-access-fit-001",
        outcome_index_id="diagnostic-phase-outcome-index-fit-001",
        accessed_at="2026-08-08T10:01:00Z",
    )
    dataset = build_diagnostic_calibration_activation_dataset(
        dataset_id="diagnostic-calibration-dataset-fit-001",
        created_at="2026-08-08T10:02:00Z",
        rule=rule,
        shared_plan_context=shared,
        registration=registration,
        reconciliation=reconciliation,
        outcome_access=access,
    )
    return {
        "rule": rule,
        "shared": shared,
        "registration": registration,
        "reconciliation": reconciliation,
        "access": access,
        "dataset": dataset,
    }


@pytest.fixture(scope="module")
def calibration_path(tmp_path_factory):
    return _build_bound_phase(tmp_path_factory.mktemp("diagnostic-calibration-fit"))


@pytest.fixture(scope="module")
def exact_fit_path(request):
    observed = fit_module._observed_runtime_versions()
    if observed != _LOCK:
        pytest.skip(
            "exact FitTranscript requires numpy2.5.1/sklearn1.9.0/scipy1.18.0; "
            f"observed {observed!r}"
        )
    path = request.getfixturevalue("calibration_path")
    transcript = build_diagnostic_calibration_fit_transcript(
        transcript_id="diagnostic-calibration-fit-transcript-001",
        created_at="2026-08-08T10:03:00Z",
        rule=path["rule"],
        dataset=path["dataset"],
        shared_plan_context=path["shared"],
        registration=path["registration"],
        reconciliation=path["reconciliation"],
        outcome_access=path["access"],
    )
    return {**path, "transcript": transcript}


def test_exact_prospective_rule_and_post_access_dataset(calibration_path) -> None:
    path = calibration_path
    rule = path["rule"]
    dataset = path["dataset"]
    assert replay_diagnostic_calibration_rule_projection(rule) == rule
    assert bind_diagnostic_calibration_rule_to_plan(
        rule, shared_plan_context=path["shared"]
    ) == rule
    assert replay_diagnostic_calibration_activation_dataset_projection(
        dataset,
        rule=rule,
        registration=path["registration"],
        reconciliation=path["reconciliation"],
        outcome_access=path["access"],
    ) == dataset
    assert len(dataset.rows) == 480
    assert dataset.outcome_access_ref == path["access"].artifact_ref
    assert dataset.payload["scientific_correctness"] == "NOT_ESTABLISHED"
    assert dataset.payload["body_access"] == {
        "source": "PHASE_OUTCOME_ACCESS_ACTIVATION_ARTIFACTS",
        "before_aggregate_access": "FORBIDDEN",
        "reconciliation_contains_bodies": False,
    }


def test_exact_locked_runtime_two_independent_fits(exact_fit_path) -> None:
    path = exact_fit_path
    transcript = path["transcript"]
    assert replay_diagnostic_calibration_fit_transcript_projection(
        transcript,
        rule=path["rule"],
        dataset=path["dataset"],
        registration=path["registration"],
        reconciliation=path["reconciliation"],
        outcome_access=path["access"],
    ) == transcript
    assert transcript.outcome_access_ref == path["access"].artifact_ref
    assert transcript.payload["scientific_correctness"] == "NOT_ESTABLISHED"
    assert transcript.payload["boundary"]["evaluation_execution"] == "NOT_AUTHORIZED"
    target = diagnostic_calibration_model_fit(
        transcript, role=TARGET_LAYER_DETECTOR
    )
    wrong = diagnostic_calibration_model_fit(
        transcript, role=WRONG_LAYER_CONTROL_DETECTOR
    )
    assert (target.layer_index, wrong.layer_index) == (18, 0)
    assert target.scaler_mean_bytes != wrong.scaler_mean_bytes
    assert target is not wrong and target.role != wrong.role
    assert target.runtime_versions == wrong.runtime_versions == _LOCK
    assert target.selection_status == wrong.selection_status == ELIGIBLE_THRESHOLD_SELECTED
    assert target.selected_threshold is not None and wrong.selected_threshold is not None
    assert len(target.scores) == len(wrong.scores) == 480
    assert len(target.selected_predictions) == len(wrong.selected_predictions) == 480
    assert target.candidate_set_sha256 == transcript.payload["model_fits"][
        "target_layer18"
    ]["candidate_set_sha256"]

    external_payload = dict(transcript.payload)
    external_runtime = dict(transcript.target_fit.runtime_versions)
    equal_candidate = replace(transcript.target_fit.candidates[0])
    equal_model_fit = replace(
        transcript.target_fit,
        runtime_versions=MappingProxyType(external_runtime),
        candidates=(equal_candidate, *transcript.target_fit.candidates[1:]),
    )
    caller_owned = replace(
        transcript,
        target_fit=equal_model_fit,
        payload=MappingProxyType(external_payload),
    )
    fresh = replay_diagnostic_calibration_fit_transcript_projection(
        caller_owned,
        rule=path["rule"],
        dataset=path["dataset"],
        registration=path["registration"],
        reconciliation=path["reconciliation"],
        outcome_access=path["access"],
    )
    detached = diagnostic_calibration_model_fit(
        caller_owned, role=TARGET_LAYER_DETECTOR
    )
    assert fresh == transcript and fresh is not caller_owned
    assert fresh.target_fit is not equal_model_fit
    assert fresh.target_fit.candidates[0] is not equal_candidate
    assert fresh.payload is not caller_owned.payload
    assert detached == transcript.target_fit and detached is not equal_model_fit
    assert detached.candidates[0] is not equal_candidate
    external_runtime["numpy"] = "MUTATED_AFTER_REPLAY"
    external_payload["scientific_correctness"] = "FABRICATED"
    assert fresh.target_fit.runtime_versions == _LOCK
    assert detached.runtime_versions == _LOCK
    assert fresh.payload["scientific_correctness"] == "NOT_ESTABLISHED"
    for forged in (
        replace(transcript, raw_bytes=bytearray(transcript.raw_bytes)),
        replace(transcript, payload=dict(transcript.payload)),
        replace(
            transcript,
            target_fit=replace(
                transcript.target_fit,
                runtime_versions=dict(transcript.target_fit.runtime_versions),
            ),
        ),
    ):
        with pytest.raises(DiagnosticCalibrationFitValidationError):
            replay_diagnostic_calibration_fit_transcript_projection(
                forged,
                rule=path["rule"],
                dataset=path["dataset"],
                registration=path["registration"],
                reconciliation=path["reconciliation"],
                outcome_access=path["access"],
            )


def test_arbitrary_body_and_raw_body_identity_are_rejected(calibration_path) -> None:
    path = calibration_path
    dataset = path["dataset"]
    first = dataset.rows[0]
    arbitrary = bytes(len(first.target_body))
    forged = replace(
        dataset,
        rows=(replace(first, target_body=arbitrary), *dataset.rows[1:]),
    )
    with pytest.raises(DiagnosticCalibrationFitValidationError):
        replay_diagnostic_calibration_activation_dataset_projection(
            forged,
            rule=path["rule"],
            registration=path["registration"],
            reconciliation=path["reconciliation"],
            outcome_access=path["access"],
        )

    tampered_raw = mutate(
        dataset.raw_bytes,
        lambda value: value["ordered_row_sha256s"].__setitem__(0, "0" * 64),
    )
    with pytest.raises(DiagnosticCalibrationFitValidationError):
        load_diagnostic_calibration_activation_dataset(
            tampered_raw,
            rule=path["rule"],
            shared_plan_context=path["shared"],
            registration=path["registration"],
            reconciliation=path["reconciliation"],
            outcome_access=path["access"],
        )

    for mutable_forgery in (
        replace(dataset, raw_bytes=bytearray(dataset.raw_bytes)),
        replace(dataset, rows=list(dataset.rows)),
        replace(dataset, payload=dict(dataset.payload)),
    ):
        with pytest.raises(DiagnosticCalibrationFitValidationError):
            replay_diagnostic_calibration_activation_dataset_projection(
                mutable_forgery,
                rule=path["rule"],
                registration=path["registration"],
                reconciliation=path["reconciliation"],
                outcome_access=path["access"],
            )

    external_payload = dict(dataset.payload)
    equal_replaced_row = replace(dataset.rows[0])
    caller_owned = replace(
        dataset,
        rows=(equal_replaced_row, *dataset.rows[1:]),
        payload=MappingProxyType(external_payload),
    )
    fresh = replay_diagnostic_calibration_activation_dataset_projection(
        caller_owned,
        rule=path["rule"],
        registration=path["registration"],
        reconciliation=path["reconciliation"],
        outcome_access=path["access"],
    )
    assert fresh == dataset and fresh is not caller_owned
    assert fresh.rows[0] is not equal_replaced_row
    assert fresh.payload is not caller_owned.payload
    external_payload["scientific_correctness"] = "FABRICATED"
    assert fresh.payload["scientific_correctness"] == "NOT_ESTABLISHED"


def test_arbitrary_coefficient_rejected_by_full_refit_binding(exact_fit_path) -> None:
    path = exact_fit_path
    transcript = path["transcript"]
    value = json.loads(transcript.raw_bytes)
    coefficient = value["model_fits"]["target_layer18"]["logistic_regression"][
        "coefficient"
    ]
    raw = bytearray.fromhex(coefficient["bytes_hex"])
    raw[0] ^= 1
    coefficient["bytes_hex"] = bytes(raw).hex().upper()
    coefficient["sha256"] = sha256_bytes(bytes(raw))
    tampered = canonical_json_bytes(value)
    with pytest.raises(DiagnosticCalibrationFitValidationError, match="refit"):
        load_diagnostic_calibration_fit_transcript(
            tampered,
            rule=path["rule"],
            dataset=path["dataset"],
            shared_plan_context=path["shared"],
            registration=path["registration"],
            reconciliation=path["reconciliation"],
            outcome_access=path["access"],
        )


def test_altered_candidate_set_or_prediction_is_rejected_without_refit(
    exact_fit_path,
) -> None:
    path = exact_fit_path
    transcript = path["transcript"]
    value = json.loads(transcript.raw_bytes)
    candidates = value["model_fits"]["target_layer18"]["candidate_results"]
    raw = bytearray.fromhex(candidates["bytes_hex"])
    raw[0] ^= 1
    candidates["bytes_hex"] = bytes(raw).hex().upper()
    candidates["sha256"] = sha256_bytes(bytes(raw))
    tampered = canonical_json_bytes(value)
    forged = replace(
        transcript,
        raw_bytes=tampered,
        sha256=sha256_bytes(tampered),
        byte_length=len(tampered),
    )
    with pytest.raises(DiagnosticCalibrationFitValidationError, match="candidates"):
        replay_diagnostic_calibration_fit_transcript_projection(
            forged,
            rule=path["rule"],
            dataset=path["dataset"],
            registration=path["registration"],
            reconciliation=path["reconciliation"],
            outcome_access=path["access"],
        )


def test_swapped_target18_wrong0_dataset_roles_are_rejected(calibration_path) -> None:
    path = calibration_path
    dataset = path["dataset"]
    first = dataset.rows[0]
    swapped = replace(
        first,
        target_vector_ref=first.wrong_layer_vector_ref,
        wrong_layer_vector_ref=first.target_vector_ref,
        target_body=first.wrong_layer_body,
        wrong_layer_body=first.target_body,
    )
    forged = replace(dataset, rows=(swapped, *dataset.rows[1:]))
    with pytest.raises(DiagnosticCalibrationFitValidationError):
        replay_diagnostic_calibration_activation_dataset_projection(
            forged,
            rule=path["rule"],
            registration=path["registration"],
            reconciliation=path["reconciliation"],
            outcome_access=path["access"],
        )


def test_dataset_creation_at_or_before_aggregate_access_is_rejected(
    calibration_path,
) -> None:
    path = calibration_path
    for created_at in ("2026-08-08T10:00:59Z", "2026-08-08T10:01:00Z"):
        with pytest.raises(
            DiagnosticCalibrationFitValidationError,
            match="strictly after aggregate access",
        ):
            build_diagnostic_calibration_activation_dataset(
                dataset_id="diagnostic-calibration-dataset-preaccess",
                created_at=created_at,
                rule=path["rule"],
                shared_plan_context=path["shared"],
                registration=path["registration"],
                reconciliation=path["reconciliation"],
                outcome_access=path["access"],
            )
