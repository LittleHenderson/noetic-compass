"""Offline tests for the frozen nine-capture Pythia engineering canary.

These tests build small synthetic evidence bytes with the production tensor
shapes.  They never load a model, invoke a forward pass, contact a provider, or
exercise the execution command's CUDA lane.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from safetensors.numpy import save


WORKER_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = WORKER_ROOT.parents[2]
RUNNER_PATH = WORKER_ROOT / "scripts" / "run_open_weight_trajectory_canary_v2.py"
PREREGISTRATION_PATH = (
    REPOSITORY_ROOT / "docs" / "working" / "OPEN_WEIGHT_TRAJECTORY_CANARY_V2_PREREG.json"
)
GITHUB_SUPERVISOR_PATH = (
    REPOSITORY_ROOT
    / "tools"
    / "runpod_open_weight_canary_v2"
    / "github_stop_supervisor.py"
)
GITHUB_ARM_HELPER_PATH = (
    REPOSITORY_ROOT
    / "tools"
    / "runpod_open_weight_canary_v2"
    / "arm_github_supervisor.ps1"
)
LOCAL_WATCHDOG_PATH = (
    REPOSITORY_ROOT
    / "tools"
    / "runpod_open_weight_canary_v2"
    / "watchdog_armed.ps1"
)
GITHUB_WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "runpod-canary-stop-supervisor.yml"

SPEC = importlib.util.spec_from_file_location("open_weight_canary_v2", RUNNER_PATH)
assert SPEC is not None and SPEC.loader is not None
canary = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = canary
SPEC.loader.exec_module(canary)

SUPERVISOR_SPEC = importlib.util.spec_from_file_location(
    "github_stop_supervisor_test", GITHUB_SUPERVISOR_PATH
)
assert SUPERVISOR_SPEC is not None and SUPERVISOR_SPEC.loader is not None
github_supervisor = importlib.util.module_from_spec(SUPERVISOR_SPEC)
sys.modules[SUPERVISOR_SPEC.name] = github_supervisor
SUPERVISOR_SPEC.loader.exec_module(github_supervisor)


def test_preregistration_is_exact_self_hashed_and_inert():
    preregistration, _raw = canary.load_preregistration(PREREGISTRATION_PATH)

    assert preregistration["preregistration_sha256"] == (
        "2B6D2938D294CB0830BA401E13332AF2511204C5883CB55641BDAB0F871CB1EA"
    )
    assert preregistration["experiment"]["schedule"] == canary.expected_schedule()
    assert preregistration["launch_bindings"]["execution_authority"] == (
        canary.UNBOUND_EXECUTION_AUTHORITY
    )
    assert preregistration["launch_bindings"]["required_source_commit_sha256"] is None
    assert preregistration["launch_bindings"]["required_oci_image_digest"] == (
        "sha256:4d1721e62b56d345c83b4fd6090664be6daf9312caab5b2e76f23d8231941851"
    )


def test_github_arm_helper_uses_yaml_when_viewing_feature_ref():
    helper_text = GITHUB_ARM_HELPER_PATH.read_text(encoding="utf-8")
    assert "'workflow', 'view', $Workflow, '--repo', $Repository, '--ref', $RefName, '--yaml'" in helper_text
    assert "[string]$ProviderStartedAtUtc" in helper_text
    assert '"provider_started_at_utc=$ProviderStartedAtUtc"' in helper_text
    assert "HARD_STOP_DEADLINE_MUST_EQUAL_PROVIDER_START_PLUS_1800_SECONDS" in helper_text


def test_local_watchdog_binds_live_runpod_schema_and_exact_boundary():
    helper_text = LOCAL_WATCHDOG_PATH.read_text(encoding="utf-8")
    assert "[ValidateNotNullOrEmpty()][string]$RunStartedAtUtc" in helper_text
    assert "Convert-ProviderUtcTimestamp $RunStartedAtUtc" in helper_text
    assert "Get-OptionalProperty $machine 'gpuTypeId'" in helper_text
    assert "WATCHDOG_PROVIDER_START_TIME_MISMATCH" in helper_text
    assert "WATCHDOG_TARGET_VOLUME_NOT_ENCRYPTED" in helper_text
    assert "WATCHDOG_TARGET_VOLUME_MOUNT_MISMATCH" in helper_text
    assert "WATCHDOG_TARGET_PORTS_MISMATCH" in helper_text
    assert "WATCHDOG_TARGET_PORT_MAPPING_MISMATCH" in helper_text
    assert "WATCHDOG_TARGET_ENVIRONMENT_KEYSET_MISMATCH" in helper_text
    assert "WATCHDOG_TARGET_PUBLIC_KEY_MISMATCH" in helper_text
    assert "WATCHDOG_TARGET_CONFLICTING_GPU_ID" in helper_text
    assert "WATCHDOG_TARGET_CONFLICTING_GPU_DISPLAY_NAME" in helper_text
    assert "WATCHDOG_TARGET_INTERRUPTIBLE_TYPE_MISMATCH" in helper_text
    assert "WATCHDOG_TARGET_LOCKED_TYPE_MISMATCH" in helper_text
    assert "Read-ProviderLaunchReceipt" in helper_text
    assert "WATCHDOG_PROVIDER_LAUNCH_CREATE_RESPONSE_PROOF_MISMATCH" in helper_text
    assert "provider_launch_receipt_sha256" in helper_text
    assert "cas_external_stop_watchdog_receipt.v2" in helper_text
    assert "Get-OptionalProperty $Pod 'adjustedCostPerHr'" in helper_text
    assert "Test-IsJsonInteger $podVolumeInGb" in helper_text
    assert "Test-IsJsonInteger $containerDiskInGb" in helper_text
    assert "$target = Assert-StopTargetIdentity $emergencyPod" in helper_text
    assert "$finalTarget = Assert-StopTargetIdentity (Invoke-PodGet)" in helper_text
    assert "$failTarget = Assert-StopTargetIdentity (Invoke-PodGet)" in helper_text
    assert "Wait-ForExitedByIdentity" in helper_text
    assert "STOPPED_AFTER_WATCHDOG_FAILURE_EXITED_CONFIRMED" in helper_text
    stop_identity_body = helper_text.split(
        "function Assert-StopTargetIdentity {", 1
    )[1].split("function Assert-PreArmTargetIdentity {", 1)[0]
    assert "if ($id -ne $PodId)" in stop_identity_body
    assert "$name -ne $PodName" not in stop_identity_body
    assert "function Assert-PreArmTargetIdentity" in helper_text
    assert "WATCHDOG_PREARM_TARGET_IDENTITY_MISMATCH" in helper_text
    assert "$armIdentityProven = $false" in helper_text
    assert "$armIdentityProven = $true" in helper_text
    assert "if ($armIdentityProven -and $null -ne $script:Headers)" in helper_text
    main_body = helper_text.split("$fallbackTaskRegistered = $false", 1)[1]
    assert main_body.index("Assert-PreArmTargetIdentity") < main_body.index(
        "$armIdentityProven = $true"
    ) < main_body.index("$startedUtc = Convert-ProviderUtcTimestamp $RunStartedAtUtc")
    assert "WATCHDOG_EMERGENCY_ARMED_RECEIPT_MISSING" in helper_text
    assert "WATCHDOG_EMERGENCY_ARMED_RECEIPT_BYTES_MISMATCH" in helper_text
    assert "WATCHDOG_EMERGENCY_STALE_RESTART_MISMATCH" in helper_text
    assert "if (-not (Test-Path -LiteralPath $emergencyTerminalPath))" not in helper_text
    assert helper_text.index("$observedArmedBytes = [IO.File]::ReadAllBytes") < (
        helper_text.index("$apiKey = Read-RunPodApiKey", helper_text.index("if ($EmergencyStopOnly)"))
    )
    assert "$LocalStopLeadSeconds = 90" in helper_text
    assert "$fallbackTriggerUtc = $deadlineUtc.AddSeconds(-$LocalStopLeadSeconds)" in helper_text
    assert "[math]::Min($PollSeconds, [math]::Floor($remainingSeconds))" in helper_text
    assert "function Assert-FallbackTaskRegistration" in helper_text
    for marker in (
        "WATCHDOG_FALLBACK_TASK_ACTION_REVALIDATION_FAILED",
        "[string]$registeredTask.State -cne 'Ready'",
        "WATCHDOG_FALLBACK_TASK_TRIGGER_TIME_REVALIDATION_FAILED",
        "WATCHDOG_FALLBACK_TASK_PRINCIPAL_REVALIDATION_FAILED",
        "WATCHDOG_FALLBACK_TASK_SETTINGS_REVALIDATION_FAILED",
        "WATCHDOG_FALLBACK_TASK_NEXT_RUN_REVALIDATION_FAILED",
        "WATCHDOG_FALLBACK_TASK_RETIREMENT_FAILED",
        "WATCHDOG_FAILED_CLOSED_CONTAINMENT_CONFIRMED",
        "RETAINED_FOR_PENDING_FALLBACK",
        "RETAINED_FOR_SCHEDULED_RETRY",
        "$armedReceiptWritten = $false",
        "$armedReceiptWritten = $true",
        "elseif ($armedReceiptWritten)",
        "RETIRED_UNUSABLE_NO_ARM_RECEIPT_",
        "-RestartCount 3",
        "-RestartInterval (New-TimeSpan -Minutes 1)",
        "fail_stop_status = $failStopStatus",
        "fail_stop_http_status = $failStopHttpStatus",
        "fail_stop_terminal_status = $failStopTerminalStatus",
        "fallback_task_cleanup_status = $taskCleanupStatus",
    ):
        assert marker in helper_text


def test_unbound_execute_fails_before_runtime_or_output(tmp_path: Path, monkeypatch):
    preregistration, _raw = canary.load_preregistration(PREREGISTRATION_PATH)
    runtime_called = {"value": False}

    def forbidden_runtime_api():
        runtime_called["value"] = True
        raise AssertionError("runtime API must not be reached")

    monkeypatch.setattr(canary, "_load_runtime_api", forbidden_runtime_api)
    output = tmp_path / "must-not-exist"
    with pytest.raises(RuntimeError, match="canary is inert"):
        canary.execute_canary(
            preregistration_path=PREREGISTRATION_PATH,
            output_root=output,
            snapshot_root=tmp_path,
            model_storage_root=tmp_path,
            source_commit_sha256="1" * 40,
            oci_image_digest="sha256:" + "2" * 64,
            provider_launch_receipt_path=tmp_path / "absent-provider.json",
            watchdog_receipt_path=tmp_path / "absent.json",
            github_supervisor_receipt_path=tmp_path / "absent-github.json",
            device="cuda:0",
        )
    assert runtime_called["value"] is False
    assert not output.exists()
    assert preregistration["status"] == "FROZEN_DESIGN_ONLY_NO_EXECUTION_AUTHORITY"


def test_portable_verifier_recomputes_pass_after_bundle_move(tmp_path: Path):
    original = _build_synthetic_bundle(tmp_path / "original")
    result = canary.verify_bundle(bundle_root=original)
    assert result["status"] == canary.PASS_STATUS
    assert result["packet_eligibility"] == canary.PACKET_STATUS
    assert result["scientific_status"] == canary.SCIENTIFIC_STATUS
    assert result["external_anchor"]["status"] == canary.EXTERNAL_ANCHOR_STATUS
    assert all(
        row["status"] == "PASS" for row in result["evaluation"]["criteria"]
    )

    moved = tmp_path / "moved-copy"
    shutil.copytree(original, moved)
    moved_result = canary.verify_bundle(bundle_root=moved)
    assert moved_result == result


def test_generated_output_change_is_not_a_pass_requirement(tmp_path: Path):
    root = _build_synthetic_bundle(tmp_path / "changed-text", zero_output_changed=True)
    result = canary.verify_bundle(bundle_root=root)

    assert result["status"] == canary.PASS_STATUS
    assert result["evaluation"]["informational_observations"][
        "generated_output_change_required"
    ] is False
    assert result["evaluation"]["informational_observations"][
        "generated_output_changed_by_repeat"
    ] == [True, True, True]


def test_missing_downstream_effect_recomputes_fail(tmp_path: Path):
    root = _build_synthetic_bundle(tmp_path / "no-effect", downstream_effect=False)
    result = canary.verify_bundle(bundle_root=root)

    assert result["status"] == canary.FAIL_STATUS
    criterion = next(
        row
        for row in result["evaluation"]["criteria"]
        if row["criterion_id"] == "C10_UPSTREAM_MATCHED_AND_DOWNSTREAM_EFFECT"
    )
    assert criterion["status"] == "FAIL"


def test_duplicate_execution_nonce_recomputes_fail(tmp_path: Path):
    root = _build_synthetic_bundle(tmp_path / "duplicate-nonce", duplicate_nonce=True)
    result = canary.verify_bundle(bundle_root=root)

    assert result["status"] == canary.FAIL_STATUS
    criterion = next(
        row
        for row in result["evaluation"]["criteria"]
        if row["criterion_id"] == "C03_UNIQUE_NONCES_AND_SERIAL_CHRONOLOGY"
    )
    assert criterion["status"] == "FAIL"


def test_tensor_tamper_and_result_overwrite_fail_closed(tmp_path: Path):
    root = _build_synthetic_bundle(tmp_path / "tamper")
    preregistration, _raw = canary.load_preregistration(
        root / "preregistration.snapshot.json"
    )
    with pytest.raises(FileExistsError):
        canary._create_result_manifest(root, preregistration)

    tensor_path = root / "captures" / "01-baseline-r1" / "capture.safetensors"
    raw = bytearray(tensor_path.read_bytes())
    raw[-1] ^= 1
    tensor_path.write_bytes(raw)
    with pytest.raises(ValueError, match="evidence-file manifest"):
        canary.verify_bundle(bundle_root=root)


def test_portable_verifier_rejects_cross_mismatched_watchdog_deadline(
    tmp_path: Path,
):
    root = _build_synthetic_bundle(tmp_path / "watchdog-window")
    watchdog_path = root / "external-watchdog.receipt.json"
    watchdog = canary.strict_json_object(watchdog_path.read_bytes(), "watchdog")
    watchdog["hard_stop_deadline_utc"] = "2000-01-01T00:00:00Z"
    watchdog_raw = canary.canonical_json_bytes(watchdog)
    watchdog_path.write_bytes(watchdog_raw)

    github_path = root / "github-stop-supervisor.armed.receipt.json"
    github = canary.strict_json_object(github_path.read_bytes(), "github supervisor")
    github["hard_stop_deadline_utc"] = "2000-01-01T00:00:00Z"
    github["written_at_utc"] = "1999-12-31T23:30:00Z"
    github_raw = canary.canonical_json_bytes(github)
    github_path.write_bytes(github_raw)

    bindings_path = root / "execution-bindings.json"
    bindings = canary.strict_json_object(bindings_path.read_bytes(), "bindings")
    bindings["watchdog_receipt_sha256"] = canary.sha256_bytes(watchdog_raw)
    bindings["github_supervisor_receipt_sha256"] = canary.sha256_bytes(github_raw)
    bindings_path.write_bytes(canary.canonical_json_bytes(bindings))

    result_path = root / "canary.result.json"
    result = canary.strict_json_object(result_path.read_bytes(), "result")
    result["evidence_files"] = canary._file_manifest(
        root, exclude={"canary.result.json"}
    )
    result.pop("result_manifest_sha256")
    result["result_manifest_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(result)
    )
    result_path.write_bytes(canary.canonical_json_bytes(result))

    with pytest.raises(ValueError, match="watchdog/provider deadline mismatch"):
        canary.verify_bundle(bundle_root=root)


def test_watchdog_capture_window_rejects_capture_before_arm_time():
    capture = SimpleNamespace(
        receipt={
            "observation": {
                "execution_record": {
                    "started_utc": "2026-08-20T12:00:10Z",
                    "ended_utc": "2026-08-20T12:00:20Z",
                }
            }
        }
    )
    with pytest.raises(ValueError, match="watchdog window"):
        canary._verify_watchdog_capture_window(
            [capture],
            deadline=datetime(2026, 8, 20, 12, 30, tzinfo=timezone.utc),
            arm_written=datetime(2026, 8, 20, 12, 5, tzinfo=timezone.utc),
            maximum_wall_seconds=1800,
        )


def test_portable_verifier_rejects_github_arm_after_capture_start(tmp_path: Path):
    root = _build_synthetic_bundle(tmp_path / "github-arm-after-capture")
    github_path = root / "github-stop-supervisor.armed.receipt.json"
    github = canary.strict_json_object(github_path.read_bytes(), "github supervisor")
    github["written_at_utc"] = "2026-08-20T12:20:00Z"
    github_raw = canary.canonical_json_bytes(github)
    github_path.write_bytes(github_raw)

    bindings_path = root / "execution-bindings.json"
    bindings = canary.strict_json_object(bindings_path.read_bytes(), "bindings")
    bindings["github_supervisor_receipt_sha256"] = canary.sha256_bytes(github_raw)
    bindings_path.write_bytes(canary.canonical_json_bytes(bindings))

    result_path = root / "canary.result.json"
    result = canary.strict_json_object(result_path.read_bytes(), "result")
    result["evidence_files"] = canary._file_manifest(
        root, exclude={"canary.result.json"}
    )
    result.pop("result_manifest_sha256")
    result["result_manifest_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(result)
    )
    result_path.write_bytes(canary.canonical_json_bytes(result))

    with pytest.raises(ValueError, match="watchdog window"):
        canary.verify_bundle(bundle_root=root)


def test_execute_preflight_rejects_noncanonical_watchdog_receipt(tmp_path: Path):
    root = _build_synthetic_bundle(tmp_path / "watchdog-canonical-preflight")
    watchdog_path = root / "external-watchdog.receipt.json"
    watchdog = json.loads(watchdog_path.read_text(encoding="utf-8"))
    watchdog_path.write_text(json.dumps(watchdog, indent=2), encoding="utf-8")
    preregistration, _raw = canary.load_preregistration(
        root / "preregistration.snapshot.json"
    )
    launch = preregistration["launch_bindings"]
    provider_path = root / "provider-launch.receipt.json"
    provider = canary.strict_json_object(provider_path.read_bytes(), "provider")
    with pytest.raises(ValueError, match="not canonical JSON"):
        canary._load_watchdog_receipt(
            watchdog_path,
            source_commit_sha256=launch["required_source_commit_sha256"],
            oci_image_digest=launch["required_oci_image_digest"],
            watchdog_script_sha256=launch["required_watchdog_script_sha256"],
            provider_launch_receipt_sha256=canary.sha256_bytes(
                provider_path.read_bytes()
            ),
            expected_pod_id=provider["pod_id"],
            expected_pod_name=provider["pod_name"],
            expected_provider_started_at=provider["provider_started_at_utc"],
            expected_deadline=provider["hard_stop_deadline_utc"],
        )


def test_provider_launch_receipt_accepts_exact_create_response_proof():
    receipt = _provider_launch_receipt()
    raw = canary.canonical_json_bytes(receipt)
    observed = canary._validate_provider_launch_receipt(
        raw,
        source_commit_sha256="1" * 40,
        oci_image_digest="sha256:" + "2" * 64,
        expected_image_name="runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404",
        require_current_time=False,
    )
    assert observed["pod_id"] == "synthetic123"
    assert observed["status"] == "EXACT_CREATE_RESPONSE_STARTED_POD_OBSERVED"


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    (
        ("interruptible", True, "interruptible=false"),
        ("locked", True, "locked=false"),
        ("volumeEncrypted", False, "volumeEncrypted=true"),
        ("lastStartedAt", "2026-08-20T12:00:02Z", "timestamp mismatch"),
    ),
)
def test_provider_launch_receipt_rejects_rehashed_semantic_tamper(
    field: str, replacement: object, message: str
):
    receipt = _provider_launch_receipt()
    transaction = receipt["create_transaction"]
    transaction["response_body"][field] = replacement
    transaction["response_body_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(transaction["response_body"])
    )
    receipt.pop("receipt_sha256")
    receipt["receipt_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(receipt)
    )
    with pytest.raises(ValueError, match=message):
        canary._validate_provider_launch_receipt(
            canary.canonical_json_bytes(receipt),
            source_commit_sha256="1" * 40,
            oci_image_digest="sha256:" + "2" * 64,
            expected_image_name="runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404",
            require_current_time=False,
        )


def test_watchdog_crosslink_accepts_same_instant_powershell_utc_lexeme(
    tmp_path: Path,
):
    deadline = datetime.now(timezone.utc) + timedelta(minutes=20)
    started = deadline - timedelta(seconds=1800)
    provider_started_text = started.isoformat().replace("+00:00", "Z")
    provider_deadline_text = deadline.isoformat().replace("+00:00", "Z")

    def powershell_o(value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond:06d}0Z"

    watchdog = {
        "claim_boundary": "Self-reported external watchdog receipt; provider stop action and billing settlement require separate verification.",
        "emergency_fallback_status": "REGISTERED_AND_REVALIDATED",
        "emergency_task_name": "CAS-OpenWeight-Canary-Stop-synthetic123",
        "hard_stop_deadline_utc": powershell_o(deadline),
        "maximum_spend_usd": "0.50",
        "maximum_wall_seconds": 1800,
        "oci_image_digest": "sha256:" + "2" * 64,
        "provider": "RUNPOD",
        "provider_launch_receipt_sha256": "3" * 64,
        "provider_started_at_utc": powershell_o(started),
        "schema_version": canary.WATCHDOG_SCHEMA,
        "source_commit_sha256": "1" * 40,
        "status": "ARMED",
        "watchdog_script_sha256": "4" * 64,
        "workload_id": "synthetic123",
        "workload_name": "cas-open-weight-canary-v2-synthetic-test",
    }
    path = tmp_path / "watchdog.json"
    path.write_bytes(canary.canonical_json_bytes(watchdog))
    observed, _raw = canary._load_watchdog_receipt(
        path,
        source_commit_sha256="1" * 40,
        oci_image_digest="sha256:" + "2" * 64,
        watchdog_script_sha256="4" * 64,
        provider_launch_receipt_sha256="3" * 64,
        expected_pod_id="synthetic123",
        expected_pod_name="cas-open-weight-canary-v2-synthetic-test",
        expected_provider_started_at=provider_started_text,
        expected_deadline=provider_deadline_text,
    )
    assert observed["provider_started_at_utc"] == powershell_o(started)


def _run_powershell_provider_receipt_validation(
    tmp_path: Path, receipt: dict[str, object]
) -> subprocess.CompletedProcess[str]:
    executable = shutil.which("pwsh")
    if executable is None and sys.platform == "win32":
        candidate = Path(
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        )
        if candidate.is_file():
            executable = str(candidate)
    if executable is None:
        pytest.skip("PowerShell is unavailable")
    receipt_path = tmp_path / "provider-launch.receipt.json"
    receipt_path.write_bytes(canary.canonical_json_bytes(receipt))
    public_key = receipt["create_transaction"]["request_body"]["env"]["PUBLIC_KEY"]
    public_key_path = tmp_path / "runpod_cas.pub"
    public_key_path.write_text(public_key + "\n", encoding="utf-8", newline="\n")
    return subprocess.run(
        [
            executable,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(LOCAL_WATCHDOG_PATH),
            "-ValidateProviderLaunchReceiptOnly",
            "-PodId",
            str(receipt["pod_id"]),
            "-PodName",
            str(receipt["pod_name"]),
            "-RunStartedAtUtc",
            str(receipt["provider_started_at_utc"]),
            "-SourceCommitSha256",
            str(receipt["source_commit_sha256"]),
            "-OciImageDigest",
            str(receipt["oci_image_digest"]),
            "-ExpectedImageName",
            str(receipt["image_name"]),
            "-ObservedHourlyRate",
            "0.44",
            "-ReceiptDirectory",
            str(tmp_path / "unused-receipt-directory"),
            "-ProviderLaunchReceiptPath",
            str(receipt_path),
            "-ExpectedPublicKeyPath",
            str(public_key_path),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def test_powershell_watchdog_accepts_same_canonical_provider_receipt(tmp_path: Path):
    completed = _run_powershell_provider_receipt_validation(
        tmp_path, _provider_launch_receipt()
    )
    assert completed.returncode == 0, completed.stderr
    assert "PROVIDER_LAUNCH_RECEIPT_VALIDATION_PASS_NO_PROVIDER_CALL" in completed.stdout


def test_powershell_watchdog_rejects_rehashed_interruptible_response(
    tmp_path: Path,
):
    receipt = _provider_launch_receipt()
    transaction = receipt["create_transaction"]
    transaction["response_body"]["interruptible"] = True
    transaction["response_body_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(transaction["response_body"])
    )
    receipt.pop("receipt_sha256")
    receipt["receipt_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(receipt)
    )
    completed = _run_powershell_provider_receipt_validation(tmp_path, receipt)
    assert completed.returncode != 0
    assert "WATCHDOG_PROVIDER_LAUNCH_CREATE_RESPONSE_PROOF_MISMATCH" in (
        completed.stdout + completed.stderr
    )


def test_provider_launch_receipt_rejects_http_200_in_runner_and_watchdog(
    tmp_path: Path,
):
    receipt = _provider_launch_receipt()
    receipt["create_transaction"]["response_http_status"] = 200
    receipt.pop("receipt_sha256")
    receipt["receipt_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(receipt)
    )

    with pytest.raises(ValueError, match="HTTP status mismatch"):
        canary._validate_provider_launch_receipt(
            canary.canonical_json_bytes(receipt),
            source_commit_sha256="1" * 40,
            oci_image_digest="sha256:" + "2" * 64,
            expected_image_name=(
                "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404"
            ),
            require_current_time=False,
        )

    completed = _run_powershell_provider_receipt_validation(tmp_path, receipt)
    assert completed.returncode != 0
    assert "WATCHDOG_PROVIDER_LAUNCH_CREATE_HTTP_STATUS_MISMATCH" in (
        completed.stdout + completed.stderr
    )


def test_github_supervisor_self_test_makes_no_provider_call():
    assert github_supervisor.self_test() == 0
    assert github_supervisor.STOP_LEAD_SECONDS == 90


def test_runner_accepts_powershell_lexemes_in_github_arm_crosslink():
    value = {
        "claim_boundary": "GitHub-hosted operational stop evidence; not a RunPod signature or billing settlement record.",
        "delete_attempted": False,
        "github_repository": "LittleHenderson/noetic-compass",
        "github_run_attempt": "1",
        "github_run_id": "123",
        "github_sha": "1" * 40,
        "hard_stop_deadline_utc": "2026-08-20T12:30:00.0000000Z",
        "mode": "PRE_DEADLINE_ARM_CHECK",
        "observed_status": "RUNNING",
        "pod_id": "synthetic123",
        "pod_name": "cas-open-weight-canary-v2-synthetic",
        "provider_started_at_utc": "2026-08-20T12:00:00.0000000Z",
        "schema_version": canary.GITHUB_SUPERVISOR_SCHEMA,
        "source_commit_sha": "1" * 40,
        "status": "ARMED_PROVIDER_GET_SUCCEEDED",
        "supervisor_source_sha256": "A" * 64,
        "written_at_utc": "2026-08-20T12:05:00Z",
    }
    observed = canary._validate_github_supervisor_receipt(
        canary.canonical_json_bytes(value),
        source_commit_sha256="1" * 40,
        supervisor_source_sha256="A" * 64,
        expected_pod_id="synthetic123",
        expected_pod_name="cas-open-weight-canary-v2-synthetic",
        expected_provider_started_at="2026-08-20T12:00:00Z",
        expected_deadline="2026-08-20T12:30:00Z",
        require_current_time=False,
    )
    assert observed["hard_stop_deadline_utc"].endswith(".0000000Z")


def test_github_supervisor_arm_check_writes_canonical_bound_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source_commit = "1" * 40
    monkeypatch.setenv("GITHUB_SHA", source_commit)
    monkeypatch.setenv("GITHUB_REPOSITORY", "LittleHenderson/noetic-compass")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key-never-used")
    receipt_path = tmp_path / "armed.json"
    deadline = (
        datetime.now(timezone.utc).replace(microsecond=123456)
        + timedelta(minutes=20)
    )
    deadline_text = deadline.isoformat().replace("+00:00", "Z")
    provider_started_text = (deadline - timedelta(seconds=1800)).isoformat().replace(
        "+00:00", "Z"
    )
    monkeypatch.setattr(
        github_supervisor,
        "_get_pod",
        lambda **_kwargs: {
            "id": "synthetic123",
            "name": "cas-open-weight-canary-v2-synthetic",
            "desiredStatus": "RUNNING",
            "lastStartedAt": provider_started_text,
        },
    )
    args = SimpleNamespace(
        pod_id="synthetic123",
        pod_name="cas-open-weight-canary-v2-synthetic",
        deadline=deadline_text,
        provider_started_at=provider_started_text,
        source_commit=source_commit,
        receipt=str(receipt_path),
    )
    assert github_supervisor.arm_check(args) == 0
    raw = receipt_path.read_bytes()
    value = canary.strict_json_object(raw, "test GitHub arm receipt")
    assert raw == canary.canonical_json_bytes(value)
    assert value["status"] == "ARMED_PROVIDER_GET_SUCCEEDED"
    assert value["pod_id"] == "synthetic123"
    assert value["provider_started_at_utc"] == provider_started_text
    assert value["hard_stop_deadline_utc"] == deadline_text


def test_github_supervisor_post_arm_stop_uses_immutable_id_not_editable_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source_commit = "1" * 40
    pod_id = "synthetic123"
    original_name = "cas-open-weight-canary-v2-synthetic"
    monkeypatch.setenv("GITHUB_SHA", source_commit)
    monkeypatch.setenv("GITHUB_REPOSITORY", "LittleHenderson/noetic-compass")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key-never-used")
    deadline = datetime.now(timezone.utc) - timedelta(seconds=1)
    provider_started = deadline - timedelta(seconds=1800)
    provider_started_text = provider_started.isoformat()
    observations = iter(
        (
            {
                "id": pod_id,
                "name": "renamed-after-arm",
                "desiredStatus": "RUNNING",
                "lastStartedAt": provider_started_text,
            },
            {
                "id": pod_id,
                "name": "renamed-after-arm",
                "desiredStatus": "EXITED",
                "lastStartedAt": provider_started_text,
            },
        )
    )
    monkeypatch.setattr(
        github_supervisor, "_get_pod", lambda **_kwargs: next(observations)
    )
    stopped = []
    monkeypatch.setattr(
        github_supervisor,
        "_stop_with_retries",
        lambda **kwargs: (stopped.append(kwargs["pod_id"]) or 200, 1),
    )
    args = SimpleNamespace(
        pod_id=pod_id,
        pod_name=original_name,
        deadline=deadline.isoformat(),
        provider_started_at=provider_started_text,
        source_commit=source_commit,
        receipt=str(tmp_path / "terminal.json"),
    )

    assert github_supervisor.run_supervisor(args) == 0
    assert stopped == [pod_id]
    receipt = canary.strict_json_object(
        (tmp_path / "terminal.json").read_bytes(), "terminal receipt"
    )
    assert receipt["observed_terminal_status"] == "EXITED"
    assert receipt["mode"] == "NORMAL_PRE_DEADLINE_STOP"
    assert receipt["stop_lead_seconds"] == 90


def test_github_supervisor_requests_stop_before_hard_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source_commit = "1" * 40
    pod_id = "synthetic123"
    start = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    deadline = start + timedelta(minutes=5)
    provider_started = deadline - timedelta(seconds=1800)
    provider_started_text = provider_started.isoformat()

    class FakeDateTime(datetime):
        current = start

        @classmethod
        def now(cls, tz=None):
            value = cls.current
            return value if tz is None else value.astimezone(tz)

    def advance(seconds: float):
        FakeDateTime.current += timedelta(seconds=seconds)

    observations = iter(
        (
            {
                "id": pod_id,
                "name": "renamed-after-arm",
                "desiredStatus": "RUNNING",
                "lastStartedAt": provider_started_text,
            },
            {
                "id": pod_id,
                "name": "renamed-after-arm",
                "desiredStatus": "EXITED",
                "lastStartedAt": provider_started_text,
            },
        )
    )
    stop_times: list[datetime] = []
    monkeypatch.setenv("GITHUB_SHA", source_commit)
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key-never-used")
    monkeypatch.setattr(github_supervisor, "datetime", FakeDateTime)
    monkeypatch.setattr(github_supervisor.time, "sleep", advance)
    monkeypatch.setattr(
        github_supervisor, "_get_pod", lambda **_kwargs: next(observations)
    )
    monkeypatch.setattr(
        github_supervisor,
        "_stop_with_retries",
        lambda **_kwargs: (stop_times.append(FakeDateTime.current) or 200, 1),
    )
    args = SimpleNamespace(
        pod_id=pod_id,
        pod_name="cas-open-weight-canary-v2-synthetic",
        deadline=deadline.isoformat(),
        provider_started_at=provider_started_text,
        source_commit=source_commit,
        receipt=str(tmp_path / "terminal.json"),
    )

    assert github_supervisor.run_supervisor(args) == 0
    assert stop_times == [deadline - timedelta(seconds=90)]
    assert stop_times[0] < deadline


def test_github_supervisor_arm_is_name_strict_and_post_arm_is_id_strict():
    renamed = {
        "id": "synthetic123",
        "name": "renamed-after-arm",
        "desiredStatus": "RUNNING",
    }
    with pytest.raises(ValueError, match="bound Pod name"):
        github_supervisor._require_bound_target(
            renamed,
            pod_id="synthetic123",
            pod_name="cas-open-weight-canary-v2-synthetic",
        )
    assert (
        github_supervisor._require_bound_target(
            renamed, pod_id="synthetic123", pod_name=None
        )
        == "RUNNING"
    )
    with pytest.raises(ValueError, match="bound Pod"):
        github_supervisor._require_bound_target(
            renamed, pod_id="wrong123", pod_name=None
        )


def test_github_supervisor_emergency_rejects_protected_pod_before_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    called = False

    def forbidden_stop(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("provider stop must not be reached")

    monkeypatch.setattr(github_supervisor, "_stop_with_retries", forbidden_stop)
    args = SimpleNamespace(
        pod_id="q2oqlooejhin7s",
        pod_name="cas-open-weight-canary-v2-protected-test",
        deadline=(datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat(),
        provider_started_at=(datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        source_commit="1" * 40,
        receipt=str(tmp_path / "never.json"),
    )
    with pytest.raises(ValueError, match="protected"):
        github_supervisor.emergency_stop(args)
    assert called is False


def test_github_supervisor_emergency_requires_successful_arm_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    called = False

    def forbidden_stop(**_kwargs):
        nonlocal called
        called = True
        raise AssertionError("provider stop must not be reached")

    monkeypatch.setattr(github_supervisor, "_stop_with_retries", forbidden_stop)
    args = SimpleNamespace(
        pod_id="unrelated123",
        pod_name="cas-open-weight-canary-v2-typo",
        deadline=(datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat(),
        provider_started_at=(datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        source_commit="1" * 40,
        receipt=str(tmp_path / "never.json"),
        arm_receipt=str(tmp_path / "absent-arm.json"),
    )
    with pytest.raises(FileNotFoundError):
        github_supervisor.emergency_stop(args)
    assert called is False


def test_github_supervisor_emergency_already_terminal_writes_create_new_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source_commit = "1" * 40
    deadline = datetime.now(timezone.utc) + timedelta(minutes=20)
    provider_started = deadline - timedelta(seconds=1800)
    provider_started_text = provider_started.isoformat()
    monkeypatch.setenv("GITHUB_SHA", source_commit)
    monkeypatch.setenv("GITHUB_REPOSITORY", "LittleHenderson/noetic-compass")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key-never-used")
    arm_path = tmp_path / "arm.json"
    terminal_path = tmp_path / "terminal.json"
    args = SimpleNamespace(
        pod_id="synthetic123",
        pod_name="cas-open-weight-canary-v2-synthetic",
        deadline=deadline.isoformat(),
        provider_started_at=provider_started_text,
        source_commit=source_commit,
        receipt=str(arm_path),
    )
    monkeypatch.setattr(
        github_supervisor,
        "_get_pod",
        lambda **_kwargs: {
            "id": args.pod_id,
            "name": args.pod_name,
            "desiredStatus": "RUNNING",
            "lastStartedAt": provider_started_text,
        },
    )
    assert github_supervisor.arm_check(args) == 0
    args.arm_receipt = str(arm_path)
    args.receipt = str(terminal_path)
    monkeypatch.setattr(
        github_supervisor,
        "_get_pod",
        lambda **_kwargs: {
            "id": args.pod_id,
            "name": "renamed-after-arm",
            "desiredStatus": "EXITED",
            "lastStartedAt": provider_started_text,
        },
    )
    monkeypatch.setattr(
        github_supervisor,
        "_stop_with_retries",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("already-terminal emergency must not POST STOP")
        ),
    )
    assert github_supervisor.emergency_stop(args) == 0
    receipt = canary.strict_json_object(terminal_path.read_bytes(), "emergency")
    assert receipt["observed_terminal_status"] == "EXITED"
    assert receipt["stop_attempts"] == 0


def test_github_supervisor_emergency_rejects_preexisting_terminal_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source_commit = "1" * 40
    deadline = datetime.now(timezone.utc) + timedelta(minutes=20)
    provider_started = deadline - timedelta(seconds=1800)
    provider_started_text = provider_started.isoformat()
    monkeypatch.setenv("GITHUB_SHA", source_commit)
    monkeypatch.setenv("GITHUB_REPOSITORY", "LittleHenderson/noetic-compass")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key-never-used")
    arm_path = tmp_path / "arm.json"
    terminal_path = tmp_path / "terminal.json"
    args = SimpleNamespace(
        pod_id="synthetic123",
        pod_name="cas-open-weight-canary-v2-synthetic",
        deadline=deadline.isoformat(),
        provider_started_at=provider_started_text,
        source_commit=source_commit,
        receipt=str(arm_path),
    )
    running = {
        "id": args.pod_id,
        "name": args.pod_name,
        "desiredStatus": "RUNNING",
        "lastStartedAt": provider_started_text,
    }
    monkeypatch.setattr(github_supervisor, "_get_pod", lambda **_kwargs: running)
    assert github_supervisor.arm_check(args) == 0
    terminal_path.write_bytes(b"stale\n")
    args.arm_receipt = str(arm_path)
    args.receipt = str(terminal_path)
    exited = dict(running, desiredStatus="EXITED")
    monkeypatch.setattr(github_supervisor, "_get_pod", lambda **_kwargs: exited)
    with pytest.raises(FileExistsError):
        github_supervisor.emergency_stop(args)


def test_github_workflow_uses_env_inputs_and_arm_gates_emergency_stop():
    workflow = GITHUB_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert '--pod-id "${{ inputs.pod_id }}"' not in workflow
    assert '--pod-name "${{ inputs.pod_name }}"' not in workflow
    assert '--deadline "${{ inputs.hard_stop_deadline_utc }}"' not in workflow
    assert '--provider-started-at "${{ inputs.provider_started_at_utc }}"' not in workflow
    assert '--source-commit "${{ inputs.source_commit }}"' not in workflow
    assert "steps.arm_check.outcome == 'success'" in workflow
    assert '--arm-receipt "$ARMED_RECEIPT_PATH"' in workflow
    assert '--provider-started-at "$PROVIDER_STARTED_AT_UTC"' in workflow
    assert workflow.count("RUNPOD_API_KEY: ${{ secrets.RUNPOD_CANARY_V2_API_KEY }}") == 3


def test_preregistration_tamper_fails_self_hash(tmp_path: Path):
    raw = PREREGISTRATION_PATH.read_bytes()
    value = canary.strict_json_object(raw, "test preregistration")
    value["experiment"]["generation"]["seed"] = 1730
    path = tmp_path / "tampered.json"
    path.write_bytes(canary.canonical_json_bytes(value))

    with pytest.raises(ValueError, match="self-hash"):
        canary.load_preregistration(path.resolve())


def test_rehashed_preregistration_cannot_change_frozen_experiment(tmp_path: Path):
    value = canary.strict_json_object(
        PREREGISTRATION_PATH.read_bytes(), "test preregistration"
    )
    prompt = "A silently changed experiment prompt"
    value["experiment"]["scenario"]["prompt"] = prompt
    value["experiment"]["scenario"]["prompt_sha256"] = canary.sha256_bytes(
        prompt.encode("utf-8")
    )
    value.pop("preregistration_sha256")
    value["preregistration_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(value)
    )
    path = tmp_path / "rehashed-tampered.json"
    path.write_bytes(canary.canonical_json_bytes(value))

    with pytest.raises(ValueError, match="frozen design"):
        canary.load_preregistration(path.resolve())


def _provider_launch_receipt(
    *,
    pod_id: str = "synthetic123",
    pod_name: str = "cas-open-weight-canary-v2-synthetic-test",
    source_commit: str = "1" * 40,
    oci_image_digest: str = "sha256:" + "2" * 64,
    image_name: str = "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404",
    provider_started_at: str = "2026-08-20T12:00:00Z",
    hard_stop_deadline: str = "2026-08-20T12:30:00Z",
) -> dict[str, object]:
    public_key = (
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGYybnRoZXRpY2tleWZvcnRlc3Rz"
        " synthetic-test"
    )
    create_request = {
        "cloudType": "SECURE",
        "containerDiskInGb": 50,
        "env": {"PUBLIC_KEY": public_key},
        "gpuCount": 1,
        "gpuTypeIds": ["NVIDIA A40"],
        "imageName": image_name,
        "interruptible": False,
        "locked": False,
        "name": pod_name,
        "networkVolumeId": None,
        "ports": ["22/tcp"],
        "volumeEncrypted": True,
        "volumeInGb": 20,
        "volumeMountPath": "/workspace",
    }
    create_response = {
        "desiredStatus": "RUNNING",
        "id": pod_id,
        "interruptible": False,
        "lastStartedAt": "2026-08-20 12:00:00.000 +0000 UTC",
        "locked": False,
        "name": pod_name,
        "volumeEncrypted": True,
    }
    create_transaction = {
        "request_body": create_request,
        "request_body_sha256": canary.sha256_bytes(
            canary.canonical_json_bytes(create_request)
        ),
        "request_method": "POST",
        "request_observed_at_utc": "2026-08-20T11:59:59Z",
        "request_path": "/v1/pods",
        "response_body": create_response,
        "response_body_sha256": canary.sha256_bytes(
            canary.canonical_json_bytes(create_response)
        ),
        "response_http_status": 201,
        "response_observed_at_utc": "2026-08-20T12:00:01Z",
    }
    unsigned = {
        "claim_boundary": canary.PROVIDER_LAUNCH_CLAIM_BOUNDARY,
        "create_transaction": create_transaction,
        "dedicated_public_key_sha256": canary.sha256_bytes(
            public_key.encode("utf-8")
        ),
        "hard_stop_deadline_utc": hard_stop_deadline,
        "image_name": image_name,
        "launch_mode": "CREATE_RESPONSE_STARTED_POD",
        "oci_image_digest": oci_image_digest,
        "pod_id": pod_id,
        "pod_name": pod_name,
        "provider": "RUNPOD",
        "provider_started_at_utc": provider_started_at,
        "schema_version": canary.PROVIDER_LAUNCH_SCHEMA,
        "source_commit_sha256": source_commit,
        "status": "EXACT_CREATE_RESPONSE_STARTED_POD_OBSERVED",
    }
    receipt = dict(unsigned)
    receipt["receipt_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(unsigned)
    )
    return receipt


def _build_synthetic_bundle(
    root: Path,
    *,
    downstream_effect: bool = True,
    duplicate_nonce: bool = False,
    zero_output_changed: bool = False,
) -> Path:
    preregistration, _preregistration_raw = canary.load_preregistration(
        PREREGISTRATION_PATH
    )
    preregistration = canary.strict_json_object(
        canary.canonical_json_bytes(preregistration), "test preregistration copy"
    )
    preregistration["status"] = "FROZEN_BOUND_SINGLE_ENGINEERING_CANARY"
    launch = preregistration["launch_bindings"]
    launch["execution_authority"] = canary.BOUND_EXECUTION_AUTHORITY
    launch["required_source_commit_sha256"] = "1" * 40
    launch["required_oci_image_digest"] = "sha256:" + "2" * 64
    launch["required_runner_source_sha256"] = canary.sha256_bytes(
        RUNNER_PATH.read_bytes()
    )
    preregistration.pop("preregistration_sha256")
    preregistration["preregistration_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(preregistration)
    )
    preregistration_raw = canary.canonical_json_bytes(preregistration)
    root.mkdir()
    (root / "captures").mkdir()
    (root / "preregistration.snapshot.json").write_bytes(preregistration_raw)
    (root / "runner.snapshot.py").write_bytes(RUNNER_PATH.read_bytes())
    (root / "dependency-lock.snapshot.txt").write_bytes(
        canary.DEFAULT_DEPENDENCY_LOCK.read_bytes()
    )
    (root / "source-files.manifest.json").write_bytes(
        canary.canonical_json_bytes(canary._current_source_file_manifest_document())
    )
    scenario = preregistration["experiment"]["scenario"]
    scenario_raw = canary.canonical_json_bytes(
        {
            "schema_version": canary.SCENARIO_SCHEMA,
            "scenario_id": scenario["scenario_id"],
            "prompt": scenario["prompt"],
        }
    )
    scenario_path = root / "scenario.json"
    scenario_path.write_bytes(scenario_raw)
    provider_launch = _provider_launch_receipt()
    provider_launch_raw = canary.canonical_json_bytes(provider_launch)
    (root / "provider-launch.receipt.json").write_bytes(provider_launch_raw)
    watchdog = {
        "schema_version": canary.WATCHDOG_SCHEMA,
        "status": "ARMED",
        "provider": "RUNPOD",
        "provider_launch_receipt_sha256": canary.sha256_bytes(provider_launch_raw),
        "provider_started_at_utc": "2026-08-20T12:00:00.0000000Z",
        "workload_id": provider_launch["pod_id"],
        "workload_name": provider_launch["pod_name"],
        "hard_stop_deadline_utc": "2026-08-20T12:30:00Z",
        "maximum_wall_seconds": 1800,
        "maximum_spend_usd": "0.50",
        "source_commit_sha256": "1" * 40,
        "oci_image_digest": "sha256:" + "2" * 64,
        "watchdog_script_sha256": preregistration["launch_bindings"][
            "required_watchdog_script_sha256"
        ],
        "emergency_task_name": f"CAS-OpenWeight-Canary-Stop-{provider_launch['pod_id']}",
        "emergency_fallback_status": "REGISTERED_AND_REVALIDATED",
        "claim_boundary": "Self-reported external watchdog receipt; provider stop action and billing settlement require separate verification.",
    }
    watchdog_raw = canary.canonical_json_bytes(watchdog)
    (root / "external-watchdog.receipt.json").write_bytes(watchdog_raw)
    github_supervisor = {
        "claim_boundary": "GitHub-hosted operational stop evidence; not a RunPod signature or billing settlement record.",
        "delete_attempted": False,
        "github_repository": "LittleHenderson/noetic-compass",
        "github_run_attempt": "1",
        "github_run_id": "123456789",
        "github_sha": "1" * 40,
        "hard_stop_deadline_utc": watchdog["hard_stop_deadline_utc"],
        "mode": "PRE_DEADLINE_ARM_CHECK",
        "observed_status": "RUNNING",
        "pod_id": watchdog["workload_id"],
        "pod_name": "cas-open-weight-canary-v2-synthetic-test",
        "provider_started_at_utc": provider_launch["provider_started_at_utc"],
        "schema_version": canary.GITHUB_SUPERVISOR_SCHEMA,
        "source_commit_sha": "1" * 40,
        "status": "ARMED_PROVIDER_GET_SUCCEEDED",
        "supervisor_source_sha256": preregistration["launch_bindings"][
            "required_github_supervisor_source_sha256"
        ],
        "written_at_utc": "2026-08-20T12:00:00Z",
    }
    github_supervisor_raw = canary.canonical_json_bytes(github_supervisor)
    (root / "github-stop-supervisor.armed.receipt.json").write_bytes(
        github_supervisor_raw
    )
    bindings = {
        "schema_version": "cas_open_weight_trajectory_canary_execution_bindings.v3",
        "source_commit_sha256": "1" * 40,
        "oci_image_digest": "sha256:" + "2" * 64,
        "device": "cuda:0",
        "deterministic_controls": preregistration["experiment"]["runtime"][
            "deterministic_controls"
        ],
        "provider_launch_receipt_sha256": canary.sha256_bytes(provider_launch_raw),
        "provider_launch_status": provider_launch["status"],
        "provider_pod_id": provider_launch["pod_id"],
        "provider_pod_name": provider_launch["pod_name"],
        "provider_started_at_utc": provider_launch["provider_started_at_utc"],
        "hard_stop_deadline_utc": provider_launch["hard_stop_deadline_utc"],
        "watchdog_receipt_sha256": canary.sha256_bytes(watchdog_raw),
        "watchdog_status": "ARMED",
        "github_supervisor_receipt_sha256": canary.sha256_bytes(
            github_supervisor_raw
        ),
        "github_supervisor_status": "ARMED_PROVIDER_GET_SUCCEEDED",
        "claim_boundary": "Execution-environment declarations and locally captured provider request/response bytes are cross-links, not a provider signature, trusted timestamp, image attestation, or billing settlement.",
    }
    (root / "execution-bindings.json").write_bytes(
        canary.canonical_json_bytes(bindings)
    )

    plan = _adapter_plan(preregistration)
    plan_raw = canary.canonical_json_bytes(plan)
    base_arrays = _base_arrays()
    zero_arrays = {name: value.copy() for name, value in base_arrays.items()}
    target = preregistration["experiment"]["intervention"]["target_layer_index"]
    zero_arrays["residual_states"][0, target, :] = 0.0
    if downstream_effect:
        zero_arrays["residual_states"][0, target + 1, 0] += 0.5
        zero_arrays["pre_selection_logits"][0, 0] += 0.25
    if zero_output_changed:
        zero_arrays["pre_selection_logits"][0, 5] = 0.0
        zero_arrays["pre_selection_logits"][0, 7] = 100.0
        zero_arrays["generated_token_ids"][0] = 7

    first_nonce = None
    for row in preregistration["experiment"]["schedule"]:
        capture_directory = root / "captures" / row["capture_id"]
        capture_directory.mkdir()
        arrays = zero_arrays if row["condition"] == "zero" else base_arrays
        generated_text = (
            "different synthetic output"
            if row["condition"] == "zero" and zero_output_changed
            else "same synthetic output"
        )
        nonce = hashlib.sha256(row["capture_id"].encode("ascii")).hexdigest().upper()
        if first_nonce is None:
            first_nonce = nonce
        if duplicate_nonce and row["ordinal"] == 9:
            nonce = first_nonce
        _write_synthetic_capture(
            capture_directory,
            preregistration=preregistration,
            schedule_row=row,
            arrays=arrays,
            generated_text=generated_text,
            nonce=nonce,
            plan=plan,
            plan_raw=plan_raw,
            scenario_path=scenario_path,
            scenario_raw=scenario_raw,
        )

    canary._create_result_manifest(root.resolve(), preregistration)
    return root.resolve()


def _base_arrays() -> dict[str, np.ndarray]:
    residual = np.arange(2 * 12 * 768, dtype=np.float32).reshape(2, 12, 768) + 1.0
    mlp = residual * np.float32(0.25)
    logits = np.zeros((2, 50304), dtype=np.float32)
    logits[0, 5] = 100.0
    logits[1, 6] = 100.0
    return {
        "prompt_input_ids": np.asarray([[1, 2, 3]], dtype=np.int64),
        "prompt_attention_mask": np.asarray([[1, 1, 1]], dtype=np.int64),
        "generated_token_ids": np.asarray([5, 6], dtype=np.int64),
        "input_lengths": np.asarray([3, 4], dtype=np.int64),
        "residual_states": residual,
        "mlp_states": mlp,
        "pre_selection_logits": logits,
    }


def _adapter_plan(preregistration: dict[str, object]) -> dict[str, object]:
    model = preregistration["experiment"]["model"]
    hooks = [
        {
            "layer_index": index,
            "residual_module": f"gpt_neox.layers.{index}",
            "attention_module": f"gpt_neox.layers.{index}.attention",
            "mlp_module": f"gpt_neox.layers.{index}.mlp",
        }
        for index in range(12)
    ]
    unsigned = {
        "schema_version": "cas_harness_interpretability_adapter_plan.v1",
        "identity": {
            "model_id": model["model_id"],
            "revision": model["revision"],
            "config_sha256": next(
                row["sha256"]
                for row in model["files"]
                if row["relative_path"] == "config.json"
            ),
            "weights_manifest_sha256": "A" * 64,
            "trust_remote_code": False,
            "binding_status": "DECLARED_REFERENCE_NOT_LOADED_MODEL_BYTE_VERIFIED",
        },
        "declaration": {
            "model_type": "gpt_neox",
            "num_hidden_layers": 12,
            "hidden_size": 768,
            "num_attention_heads": 12,
        },
        "discovery": {
            "status": "STRUCTURE_VERIFIED",
            "model_type": "gpt_neox",
            "family": "gpt_neox",
            "layer_stack_attr": "gpt_neox.layers",
            "observed_layer_count": 12,
            "available_mechanics": ["adapter_manifest", "residual_capture"],
            "layer_hooks": hooks,
        },
        "runtime_verification": None,
        "capabilities": [
            {"capability_id": f"C{index:02d}", "evidence_status": "NOT_RUN"}
            for index in range(1, 15)
        ],
        "claim_boundary": canary.ADAPTER_PLAN_CLAIM_BOUNDARY,
    }
    plan = dict(unsigned)
    plan["plan_sha256"] = canary.sha256_bytes(canary.canonical_json_bytes(unsigned))
    return plan


def _write_synthetic_capture(
    directory: Path,
    *,
    preregistration: dict[str, object],
    schedule_row: dict[str, object],
    arrays: dict[str, np.ndarray],
    generated_text: str,
    nonce: str,
    plan: dict[str, object],
    plan_raw: bytes,
    scenario_path: Path,
    scenario_raw: bytes,
) -> None:
    model = preregistration["experiment"]["model"]
    scenario = preregistration["experiment"]["scenario"]
    intervention = canary._expected_intervention_observation(
        preregistration, schedule_row["condition"]
    )
    array_manifest = canary._array_manifest(arrays)
    loaded_weight_hash = "B" * 64
    tensor_raw = save(
        arrays,
        metadata={
            "schema_version": canary.TENSOR_SCHEMA,
            "scenario_id": scenario["scenario_id"],
            "prompt_sha256": scenario["prompt_sha256"],
            "model_tree_manifest_sha256": model["tree_manifest_sha256"],
            "loaded_weight_value_manifest_sha256": loaded_weight_hash,
            "adapter_plan_sha256": plan["plan_sha256"],
            "packet_eligibility": canary.PACKET_STATUS,
        },
    )
    snapshot_files = [
        {
            **row,
            "resolved_relative_to_storage": f"blobs/{row['sha256'].lower()}",
            "link_kind": "MODEL_LOCAL_FILE_SYMLINK",
        }
        for row in model["files"]
    ]
    snapshot = {
        "model_id": model["model_id"],
        "revision": model["revision"],
        "snapshot_root": "/synthetic/model/snapshots/" + model["revision"],
        "model_storage_root": "/synthetic/model",
        "config_sha256": next(
            row["sha256"]
            for row in model["files"]
            if row["relative_path"] == "config.json"
        ),
        "weights_manifest_sha256": "A" * 64,
        "tokenizer_manifest_sha256": "C" * 64,
        "tree_manifest_sha256": model["tree_manifest_sha256"],
        "files": snapshot_files,
        "identity_binding_status": "HF_CACHE_MODEL_ID_AND_REVISION_PATH_BOUND",
        "claim_boundary": "SYNTHETIC OFFLINE TEST SNAPSHOT ONLY",
    }
    source_manifest = [
        {"path": "/synthetic/source.py", "byte_count": 1, "sha256": "D" * 64}
    ]
    frozen_runtime = preregistration["experiment"]["runtime"]
    runtime = {
        "python": frozen_runtime["required_python_version"],
        "platform": "synthetic-offline-test",
        "device": "cuda:0",
        "dtype_request": "auto",
        "torch_deterministic_algorithms_enabled": True,
        "source_manifest": source_manifest,
        "python_executable": {
            "path": "/synthetic/python",
            "byte_count": 1,
            "sha256": "E" * 64,
        },
        "hardware": {
            "requested_device": "cuda:0",
            "cuda_available": True,
            "torch_cuda_version": frozen_runtime["required_torch_cuda_version"],
            "cudnn_version": 99999,
            "device_name": "NVIDIA A40",
            "device_capability": [8, 6],
        },
        "callable_manifest": [{"status": "SYNTHETIC_OFFLINE_TEST_ONLY"}],
        "tokenizer_callable_manifest": [{"status": "SYNTHETIC_OFFLINE_TEST_ONLY"}],
    }
    adapter = {
        "adapter_plan_sha256": plan["plan_sha256"],
        "adapter_plan_file_sha256": canary.sha256_bytes(plan_raw),
        "adapter_source_sha256": "F" * 64,
        "adapter_source_path": "/synthetic/adapter.py",
        "residual_paths": [f"gpt_neox.layers.{index}" for index in range(12)],
        "mlp_paths": [f"gpt_neox.layers.{index}.mlp" for index in range(12)],
        "attention_paths": [
            f"gpt_neox.layers.{index}.attention" for index in range(12)
        ],
        "config_projection": {
            "model_type": "gpt_neox",
            "num_hidden_layers": 12,
            "hidden_size": 768,
            "num_attention_heads": 12,
            "vocab_size": 50304,
            "max_position_embeddings": 2048,
        },
        "binding_status": canary.ADAPTER_BINDING_STATUS,
        "claim_boundary": canary.ADAPTER_CLAIM_BOUNDARY,
    }
    observation = {
        "schema_version": "cas_open_weight_trajectory_capture.v1",
        "status": canary.CAPTURE_STATUS,
        "packet_eligibility": canary.PACKET_STATUS,
        "scientific_status": canary.CAPTURE_SCIENTIFIC_STATUS,
        "scenario_id": scenario["scenario_id"],
        "prompt_sha256": scenario["prompt_sha256"],
        "seed": 1729,
        "generation": {
            "method": "manual_greedy_argmax",
            "max_new_tokens": 2,
            "temperature": None,
            "sampling": False,
        },
        "capture_contract": {
            "residual": "full_width_last_current_token_for_every_decoder_layer",
            "mlp": "full_width_last_current_token_for_every_decoder_layer",
            "logits": "full_vocabulary_pre_selection_each_generation_step",
            "attention": "NOT_CAPTURED_IN_V1",
            "shapes": {name: list(value.shape) for name, value in arrays.items()},
        },
        "intervention": intervention,
        "model_snapshot": snapshot,
        "loaded_weight_value_manifest_sha256": loaded_weight_hash,
        "tokenizer_canary": {"status": "SYNTHETIC_OFFLINE_TEST_ONLY"},
        "adapter": adapter,
        "dependencies": preregistration["experiment"]["runtime"][
            "required_dependency_versions"
        ],
        "runtime": runtime,
        "claim_boundary": canary.OBSERVATION_CLAIM_BOUNDARY,
        "scenario_source": {
            "path": str(scenario_path),
            "byte_count": len(scenario_raw),
            "sha256": canary.sha256_bytes(scenario_raw),
            "snapshot_semantics": "one immutable byte snapshot strict-parsed and hashed",
        },
    }
    ordinal = schedule_row["ordinal"]
    started = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc) + timedelta(
        seconds=ordinal * 10
    )
    ended = started + timedelta(seconds=1)
    expected_layer_calls = {
        str(step): {str(layer): 1 for layer in range(12)} for step in range(2)
    }
    record_unsigned = {
        "schema_version": "cas_open_weight_engine_execution_record.v1",
        "execution_nonce": nonce,
        "scenario_id": scenario["scenario_id"],
        "prompt_sha256": scenario["prompt_sha256"],
        "generated_text_sha256": canary.sha256_bytes(generated_text.encode("utf-8")),
        "intervention": intervention,
        "residual_hook_invocations": expected_layer_calls,
        "mlp_hook_invocations": expected_layer_calls,
        "intervention_hook_invocations": {
            str(step): 0 if schedule_row["condition"] == "baseline" else 1
            for step in range(2)
        },
        "array_manifest_sha256": canary.sha256_bytes(
            canary.canonical_json_bytes(array_manifest)
        ),
        "observation_without_execution_record_sha256": canary.sha256_bytes(
            canary.canonical_json_bytes(observation)
        ),
        "model_tree_manifest_sha256": model["tree_manifest_sha256"],
        "adapter_plan_sha256": plan["plan_sha256"],
        "runtime_source_manifest_sha256": canary.sha256_bytes(
            canary.canonical_json_bytes(source_manifest)
        ),
        "hook_state_before": "CLEAN",
        "hook_state_after": "CLEAN",
        "claim_boundary": canary.ENGINE_RECORD_CLAIM_BOUNDARY,
        "started_utc": started.isoformat().replace("+00:00", "Z"),
        "ended_utc": ended.isoformat().replace("+00:00", "Z"),
        "started_monotonic_ns": ordinal * 10_000,
        "ended_monotonic_ns": ordinal * 10_000 + 1_000,
        "model_forward_calls": 2,
    }
    record = dict(record_unsigned)
    record["execution_hmac_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(record_unsigned)
    )
    observation["execution_record"] = record
    receipt_unsigned = {
        "schema_version": canary.RECEIPT_SCHEMA,
        "status": canary.CAPTURE_STATUS,
        "packet_eligibility": canary.PACKET_STATUS,
        "scientific_status": canary.CAPTURE_SCIENTIFIC_STATUS,
        "input": {
            "scenario_id": scenario["scenario_id"],
            "prompt": scenario["prompt"],
            "prompt_sha256": scenario["prompt_sha256"],
        },
        "output": {
            "generated_text": generated_text,
            "tensor_path": "capture.safetensors",
            "tensor_byte_count": len(tensor_raw),
            "tensor_sha256": canary.sha256_bytes(tensor_raw),
            "adapter_plan_path": "capture.adapter-plan.json",
            "adapter_plan_byte_count": len(plan_raw),
            "adapter_plan_file_sha256": canary.sha256_bytes(plan_raw),
            "array_manifest": array_manifest,
        },
        "observation": observation,
        "claim_boundary": canary.RECEIPT_CLAIM_BOUNDARY,
    }
    receipt = dict(receipt_unsigned)
    receipt["receipt_sha256"] = canary.sha256_bytes(
        canary.canonical_json_bytes(receipt_unsigned)
    )
    (directory / "capture.safetensors").write_bytes(tensor_raw)
    (directory / "capture.adapter-plan.json").write_bytes(plan_raw)
    (directory / "capture.receipt.json").write_bytes(
        canary.canonical_json_bytes(receipt)
    )
