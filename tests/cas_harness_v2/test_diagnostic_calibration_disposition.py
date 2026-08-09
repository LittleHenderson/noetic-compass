from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import inspect
import json
from pathlib import Path
import sqlite3
import sys
from types import MappingProxyType

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
TEST_DIR = Path(__file__).resolve().parent
for candidate in (SRC, TEST_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from cas_harness_v2._strict_json import canonical_json_bytes  # noqa: E402
from cas_harness_v2.diagnostic_calibration_disposition import (  # noqa: E402
    CALIBRATION_ANALYSIS_ELIGIBLE,
    CALIBRATION_FROZEN_NONREPORTING,
    CALIBRATION_REJECTED_NONREPORTING,
    DiagnosticCalibrationConflict,
    DiagnosticCalibrationDispositionRegistry,
    DiagnosticCalibrationIntegrityError,
    DiagnosticCalibrationValidationError,
    build_diagnostic_calibration_analysis,
    build_diagnostic_calibration_detector_bundle,
    load_diagnostic_calibration_disposition,
    replay_diagnostic_calibration_analysis_projection,
    replay_diagnostic_calibration_detector_bundle_projection,
    replay_diagnostic_calibration_disposition_projection,
)
from cas_harness_v2.diagnostic_calibration_fit import (  # noqa: E402
    DiagnosticBinary64,
    ELIGIBLE_THRESHOLD_SELECTED,
    NO_ELIGIBLE_THRESHOLD,
    TARGET_LAYER_DETECTOR,
    WRONG_LAYER_CONTROL_DETECTOR,
)
import cas_harness_v2.diagnostic_calibration_disposition as disposition_module  # noqa: E402
from test_diagnostic_calibration_fit import (  # noqa: E402,F401
    calibration_path,
    exact_fit_path,
)
from test_diagnostic_phase_coordinator import rejected_phase  # noqa: E402,F401


def mutate(raw: bytes, change) -> bytes:
    value = json.loads(raw)
    change(value)
    return canonical_json_bytes(value)


class EqualText(str):
    pass


@pytest.fixture(scope="module")
def early_disposition(rejected_phase):
    coordinator, reconciliation = rejected_phase
    registration = coordinator.registration
    first = DiagnosticCalibrationDispositionRegistry(registration=registration)
    second = DiagnosticCalibrationDispositionRegistry(registration=registration)

    def finalize(registry: DiagnosticCalibrationDispositionRegistry):
        return registry.finalize_rejection(
            finalized_at="2026-08-08T08:51:00Z",
            reconciliation=reconciliation,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        artifacts = tuple(pool.map(finalize, (first, second)))
    assert artifacts[0].raw_bytes == artifacts[1].raw_bytes
    return {
        "registration": registration,
        "reconciliation": reconciliation,
        "registry": first,
        "second_registry": second,
        "artifact": artifacts[0],
    }


@pytest.fixture(scope="module")
def eligible_disposition(exact_fit_path):
    path = exact_fit_path
    analysis = build_diagnostic_calibration_analysis(
        analysis_id="diagnostic-calibration-analysis-disposition-001",
        created_at="2026-08-08T10:04:00Z",
        rule=path["rule"],
        dataset=path["dataset"],
        transcript=path["transcript"],
        shared_plan_context=path["shared"],
        registration=path["registration"],
        reconciliation=path["reconciliation"],
        outcome_access=path["access"],
    )
    bundle = build_diagnostic_calibration_detector_bundle(
        bundle_id="diagnostic-calibration-detector-bundle-disposition-001",
        created_at="2026-08-08T10:05:00Z",
        rule=path["rule"],
        dataset=path["dataset"],
        transcript=path["transcript"],
        analysis=analysis,
        shared_plan_context=path["shared"],
        registration=path["registration"],
        reconciliation=path["reconciliation"],
        outcome_access=path["access"],
    )
    registry = DiagnosticCalibrationDispositionRegistry(
        registration=path["registration"]
    )
    artifact = registry.finalize_freeze(
        finalized_at="2026-08-08T10:06:00Z",
        rule=path["rule"],
        dataset=path["dataset"],
        transcript=path["transcript"],
        shared_plan_context=path["shared"],
        reconciliation=path["reconciliation"],
        outcome_access=path["access"],
        analysis=analysis,
        bundle=bundle,
    )
    return {**path, "analysis": analysis, "bundle": bundle, "registry": registry, "disposition": artifact}


def test_light_public_api_has_no_caller_numeric_or_promotion_inputs() -> None:
    forbidden = {
        "coefficients",
        "scores",
        "counts",
        "candidates",
        "threshold",
        "parameters",
        "packet",
        "evaluation",
        "claim",
        "product",
        "license",
        "public_release",
    }
    callables = (
        build_diagnostic_calibration_analysis,
        build_diagnostic_calibration_detector_bundle,
        DiagnosticCalibrationDispositionRegistry.finalize_freeze,
        DiagnosticCalibrationDispositionRegistry.finalize_rejection,
    )
    for callable_ in callables:
        assert forbidden.isdisjoint(inspect.signature(callable_).parameters)

    source = inspect.getsource(disposition_module)
    assert "build_diagnostic_detector_parameters" not in source
    assert "build_diagnostic_calibration_detector_result" not in source
    assert "from .evidence_packet" not in source
    assert "import EvidencePacket" not in source
    assert "NO_ELIGIBLE_THRESHOLD" in source
    assert "POST_ACCESS_NO_ELIGIBLE_THRESHOLD" in source


def test_light_disposition_loader_reason_shape_accepts_empty_only_for_freeze() -> None:
    parse = disposition_module._parse_disposition_rejection_reasons
    assert parse([], status=CALIBRATION_FROZEN_NONREPORTING) == ()
    assert parse(
        ["VALIDATED_ROW_REJECTION"],
        status=CALIBRATION_REJECTED_NONREPORTING,
    ) == ("VALIDATED_ROW_REJECTION",)
    with pytest.raises(DiagnosticCalibrationValidationError, match="must keep"):
        parse(
            ["VALIDATED_ROW_REJECTION"],
            status=CALIBRATION_FROZEN_NONREPORTING,
        )
    with pytest.raises(DiagnosticCalibrationValidationError, match="requires"):
        parse([], status=CALIBRATION_REJECTED_NONREPORTING)


def test_early_rejection_is_null_nonreporting_and_cross_instance_exact(
    early_disposition,
) -> None:
    path = early_disposition
    artifact = path["artifact"]
    assert artifact.status == CALIBRATION_REJECTED_NONREPORTING
    assert artifact.rejection_reasons == path["reconciliation"].rejection_reasons
    assert artifact.rejection_reasons == ("VALIDATED_ROW_REJECTION",)
    assert artifact.rule_ref is None
    assert artifact.dataset_ref is None
    assert artifact.fit_transcript_ref is None
    assert artifact.outcome_access_ref is None
    assert artifact.analysis_ref is None
    assert artifact.bundle_ref is None
    assert replay_diagnostic_calibration_disposition_projection(
        artifact,
        registration=path["registration"],
        reconciliation=path["reconciliation"],
    ) == artifact
    assert load_diagnostic_calibration_disposition(
        bytearray(artifact.raw_bytes),
        registration=path["registration"],
        reconciliation=path["reconciliation"],
    ) == artifact
    assert path["second_registry"].replay_retained(
        reconciliation=path["reconciliation"]
    ) == artifact


def test_early_rejection_slot_is_immutable_and_different_bytes_conflict(
    early_disposition,
) -> None:
    path = early_disposition
    with pytest.raises(DiagnosticCalibrationConflict, match="different"):
        path["second_registry"].finalize_rejection(
            finalized_at="2026-08-08T08:52:00Z",
            reconciliation=path["reconciliation"],
        )

    database_path = path["registration"].store_binding.canonical_path
    connection = sqlite3.connect(database_path, isolation_level=None)
    try:
        row = connection.execute(
            "SELECT phase_subject_sha256, status, disposition_raw FROM diagnostic_calibration_dispositions"
        ).fetchone()
        assert row is not None
        assert row[0] == path["registration"].phase_subject_sha256
        assert row[1] == CALIBRATION_REJECTED_NONREPORTING
        assert bytes(row[2]) == path["artifact"].raw_bytes
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE diagnostic_calibration_dispositions SET finalized_at='2099-01-01T00:00:00Z'"
            )
        with pytest.raises(sqlite3.IntegrityError, match="permanent"):
            connection.execute("DELETE FROM diagnostic_calibration_dispositions")
    finally:
        connection.close()


def test_extra_disposition_trigger_is_detected_fail_closed(early_disposition) -> None:
    path = early_disposition
    database_path = path["registration"].store_binding.canonical_path
    connection = sqlite3.connect(database_path, isolation_level=None)
    try:
        connection.execute(
            """
            CREATE TRIGGER diagnostic_calibration_dispositions_extra
            BEFORE INSERT ON diagnostic_calibration_dispositions
            BEGIN
                SELECT 1;
            END
            """
        )
        with pytest.raises(DiagnosticCalibrationIntegrityError, match="inventory"):
            path["registry"].replay_retained(
                reconciliation=path["reconciliation"]
            )
    finally:
        connection.execute(
            "DROP TRIGGER IF EXISTS diagnostic_calibration_dispositions_extra"
        )
        connection.close()


def test_early_disposition_projection_replacement_forgeries_fail_closed(
    early_disposition,
) -> None:
    path = early_disposition
    artifact = path["artifact"]
    for forged in (
        replace(artifact, raw_bytes=bytearray(artifact.raw_bytes)),
        replace(artifact, rejection_reasons=list(artifact.rejection_reasons)),
        replace(artifact, payload=dict(artifact.payload)),
        replace(artifact, registration_ref=artifact.reconciliation_ref),
        replace(artifact, status=CALIBRATION_FROZEN_NONREPORTING),
    ):
        with pytest.raises(DiagnosticCalibrationValidationError):
            replay_diagnostic_calibration_disposition_projection(
                forged,
                registration=path["registration"],
                reconciliation=path["reconciliation"],
            )

    backing = dict(artifact.payload)
    caller_backed = replace(artifact, payload=MappingProxyType(backing))
    replayed = replay_diagnostic_calibration_disposition_projection(
        caller_backed,
        registration=path["registration"],
        reconciliation=path["reconciliation"],
    )
    assert replayed is not caller_backed
    backing["status"] = CALIBRATION_FROZEN_NONREPORTING
    assert replayed.payload["status"] == CALIBRATION_REJECTED_NONREPORTING


def test_permanent_packet_evaluation_claim_product_public_license_locks(
    early_disposition,
) -> None:
    path = early_disposition
    artifact = path["artifact"]
    replacements = (
        ("evidence_packet_v2", "CREATED"),
        ("evaluation_execution", "AUTHORIZED"),
        ("evaluation_authority", "GRANTED"),
        ("evaluation_promotion", "ALLOWED"),
        ("claim_promotion", "ALLOWED"),
        ("product_route", "ALLOWED"),
        ("reporting", "ALLOWED"),
        ("license_status", "LICENSED"),
        ("license_granted", True),
        ("public_release", True),
    )
    for field, replacement in replacements:
        tampered = mutate(
            artifact.raw_bytes,
            lambda value, key=field, item=replacement: value["boundary"].update(
                {key: item}
            ),
        )
        with pytest.raises(DiagnosticCalibrationValidationError):
            load_diagnostic_calibration_disposition(
                tampered,
                registration=path["registration"],
                reconciliation=path["reconciliation"],
            )

    terminality = mutate(
        artifact.raw_bytes,
        lambda value: value["terminality"].update({"reporting": "ALLOWED"}),
    )
    with pytest.raises(DiagnosticCalibrationValidationError):
        load_diagnostic_calibration_disposition(
            terminality,
            registration=path["registration"],
            reconciliation=path["reconciliation"],
        )


def test_early_rejection_cannot_bind_later_or_unrecognized_inputs(
    early_disposition,
) -> None:
    path = early_disposition
    with pytest.raises(DiagnosticCalibrationValidationError, match="must keep"):
        path["registry"].finalize_rejection(
            finalized_at="2026-08-08T08:53:00Z",
            reconciliation=path["reconciliation"],
            shared_plan_context=object(),  # type: ignore[arg-type]
        )


def test_exact_locked_fit_freezes_only_dual_layer18_layer0_nonreporting(
    eligible_disposition,
) -> None:
    path = eligible_disposition
    analysis = path["analysis"]
    bundle = path["bundle"]
    disposition = path["disposition"]
    assert analysis.status == CALIBRATION_ANALYSIS_ELIGIBLE
    assert tuple(item.role for item in analysis.detector_results) == (
        TARGET_LAYER_DETECTOR,
        WRONG_LAYER_CONTROL_DETECTOR,
    )
    assert tuple(item.layer_index for item in analysis.detector_results) == (18, 0)
    assert tuple(item.selection_status for item in analysis.detector_results) == (
        ELIGIBLE_THRESHOLD_SELECTED,
        ELIGIBLE_THRESHOLD_SELECTED,
    )
    assert bundle.target_fit == path["transcript"].target_fit
    assert bundle.wrong_layer_fit == path["transcript"].wrong_layer_fit
    assert bundle.target_fit is not path["transcript"].target_fit
    assert bundle.wrong_layer_fit is not path["transcript"].wrong_layer_fit
    assert disposition.status == CALIBRATION_FROZEN_NONREPORTING
    assert disposition.rejection_reasons == ()
    assert disposition.rule_ref == path["rule"].artifact_ref
    assert disposition.dataset_ref == path["dataset"].artifact_ref
    assert disposition.fit_transcript_ref == path["transcript"].artifact_ref
    assert disposition.outcome_access_ref == path["access"].artifact_ref
    assert disposition.analysis_ref == analysis.artifact_ref
    assert disposition.bundle_ref == bundle.artifact_ref
    assert disposition.payload["boundary"]["scientific_correctness"] == "NOT_ESTABLISHED"
    assert disposition.payload["boundary"]["license_status"] == "NOT LICENSED"
    assert disposition.payload["boundary"]["public_release"] is False


def test_exact_locked_projection_guards_cover_analysis_bundle_and_terminal(
    eligible_disposition,
) -> None:
    path = eligible_disposition
    common = {
        "rule": path["rule"],
        "dataset": path["dataset"],
        "transcript": path["transcript"],
        "registration": path["registration"],
        "reconciliation": path["reconciliation"],
        "outcome_access": path["access"],
    }
    assert replay_diagnostic_calibration_analysis_projection(
        path["analysis"], **common
    ) == path["analysis"]
    assert replay_diagnostic_calibration_detector_bundle_projection(
        path["bundle"], analysis=path["analysis"], **common
    ) == path["bundle"]
    assert replay_diagnostic_calibration_disposition_projection(
        path["disposition"],
        analysis=path["analysis"],
        bundle=path["bundle"],
        **common,
    ) == path["disposition"]

    analysis_backing = dict(path["analysis"].payload)
    caller_analysis = replace(
        path["analysis"], payload=MappingProxyType(analysis_backing)
    )
    replayed_analysis = replay_diagnostic_calibration_analysis_projection(
        caller_analysis, **common
    )
    assert replayed_analysis is not caller_analysis
    analysis_backing["status"] = "CALLER_MUTATED"
    assert replayed_analysis.payload["status"] == CALIBRATION_ANALYSIS_ELIGIBLE

    bundle_backing = dict(path["bundle"].payload)
    caller_bundle = replace(
        path["bundle"], payload=MappingProxyType(bundle_backing)
    )
    replayed_bundle = replay_diagnostic_calibration_detector_bundle_projection(
        caller_bundle, analysis=path["analysis"], **common
    )
    assert replayed_bundle is not caller_bundle
    bundle_backing["status"] = "CALLER_MUTATED"
    assert replayed_bundle.payload["status"] != "CALLER_MUTATED"

    disposition_backing = dict(path["disposition"].payload)
    caller_disposition = replace(
        path["disposition"], payload=MappingProxyType(disposition_backing)
    )
    replayed_disposition = replay_diagnostic_calibration_disposition_projection(
        caller_disposition,
        analysis=path["analysis"],
        bundle=path["bundle"],
        **common,
    )
    assert replayed_disposition is not caller_disposition
    disposition_backing["status"] = CALIBRATION_REJECTED_NONREPORTING
    assert replayed_disposition.payload["status"] == CALIBRATION_FROZEN_NONREPORTING

    first_result = path["analysis"].detector_results[0]
    threshold = first_result.selected_threshold
    assert threshold is not None
    equality_equal_threshold = DiagnosticBinary64(
        hex=EqualText(threshold.hex),
        bytes_hex=EqualText(threshold.bytes_hex),
        decimal=EqualText(threshold.decimal),
    )
    threshold_forgery = replace(
        path["analysis"],
        detector_results=(
            replace(first_result, selected_threshold=equality_equal_threshold),
            path["analysis"].detector_results[1],
        ),
    )
    with pytest.raises(DiagnosticCalibrationValidationError, match="immutable text"):
        replay_diagnostic_calibration_analysis_projection(threshold_forgery, **common)

    swapped_results = replace(
        path["analysis"],
        detector_results=tuple(reversed(path["analysis"].detector_results)),
    )
    with pytest.raises(DiagnosticCalibrationValidationError):
        replay_diagnostic_calibration_analysis_projection(swapped_results, **common)

    reused_fit = replace(
        path["bundle"], wrong_layer_fit=path["bundle"].target_fit
    )
    with pytest.raises(DiagnosticCalibrationValidationError):
        replay_diagnostic_calibration_detector_bundle_projection(
            reused_fit, analysis=path["analysis"], **common
        )

    forged_terminal = replace(
        path["disposition"], bundle_ref=path["analysis"].artifact_ref
    )
    with pytest.raises(DiagnosticCalibrationValidationError):
        replay_diagnostic_calibration_disposition_projection(
            forged_terminal,
            analysis=path["analysis"],
            bundle=path["bundle"],
            **common,
        )


def test_clean_phase_cannot_take_early_rejection_or_null_bundle_path(
    eligible_disposition,
) -> None:
    path = eligible_disposition
    with pytest.raises(DiagnosticCalibrationValidationError, match="requires exact"):
        path["registry"].finalize_rejection(
            finalized_at="2026-08-08T10:07:00Z",
            reconciliation=path["reconciliation"],
        )
    assert path["transcript"].target_fit.selection_status != NO_ELIGIBLE_THRESHOLD
    assert path["transcript"].wrong_layer_fit.selection_status != NO_ELIGIBLE_THRESHOLD
