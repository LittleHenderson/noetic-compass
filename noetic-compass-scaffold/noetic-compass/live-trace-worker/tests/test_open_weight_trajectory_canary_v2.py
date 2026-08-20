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
        "C3BE44564B705F994B348EC6445A15E69C175ADCA7EF32D2CAF5873F2E31491A"
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


def test_local_watchdog_binds_live_runpod_schema_and_exact_boundary():
    helper_text = LOCAL_WATCHDOG_PATH.read_text(encoding="utf-8")
    assert "[datetime]$RunStartedAtUtc" in helper_text
    assert "Get-OptionalProperty $machine 'gpuTypeId'" in helper_text
    assert "WATCHDOG_PROVIDER_START_TIME_MISMATCH" in helper_text
    assert "WATCHDOG_TARGET_VOLUME_NOT_ENCRYPTED" in helper_text
    assert "WATCHDOG_TARGET_PORTS_MISMATCH" in helper_text
    assert "[int]$podVolumeInGb -ne 20" in helper_text
    assert "[int]$containerDiskInGb -ne 50" in helper_text


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


def test_portable_verifier_rejects_capture_outside_watchdog_window(tmp_path: Path):
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

    with pytest.raises(ValueError, match="watchdog window"):
        canary.verify_bundle(bundle_root=root)


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
    with pytest.raises(ValueError, match="not canonical JSON"):
        canary._load_watchdog_receipt(
            watchdog_path,
            source_commit_sha256=launch["required_source_commit_sha256"],
            oci_image_digest=launch["required_oci_image_digest"],
            watchdog_script_sha256=launch["required_watchdog_script_sha256"],
        )


def test_github_supervisor_self_test_makes_no_provider_call():
    assert github_supervisor.self_test() == 0


def test_github_supervisor_arm_check_writes_canonical_bound_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    source_commit = "1" * 40
    monkeypatch.setenv("GITHUB_SHA", source_commit)
    monkeypatch.setenv("GITHUB_REPOSITORY", "LittleHenderson/noetic-compass")
    monkeypatch.setenv("GITHUB_RUN_ID", "123")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("RUNPOD_API_KEY", "test-key-never-used")
    monkeypatch.setattr(
        github_supervisor,
        "_get_pod",
        lambda **_kwargs: {
            "id": "synthetic123",
            "name": "cas-open-weight-canary-v2-synthetic",
            "desiredStatus": "RUNNING",
        },
    )
    receipt_path = tmp_path / "armed.json"
    deadline_text = (
        datetime.now(timezone.utc).replace(microsecond=123456)
        + timedelta(minutes=20)
    ).isoformat().replace("+00:00", "Z")
    args = SimpleNamespace(
        pod_id="synthetic123",
        pod_name="cas-open-weight-canary-v2-synthetic",
        deadline=deadline_text,
        source_commit=source_commit,
        receipt=str(receipt_path),
    )
    assert github_supervisor.arm_check(args) == 0
    raw = receipt_path.read_bytes()
    value = canary.strict_json_object(raw, "test GitHub arm receipt")
    assert raw == canary.canonical_json_bytes(value)
    assert value["status"] == "ARMED_PROVIDER_GET_SUCCEEDED"
    assert value["pod_id"] == "synthetic123"
    assert value["hard_stop_deadline_utc"] == deadline_text


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
        source_commit="1" * 40,
        receipt=str(tmp_path / "never.json"),
        arm_receipt=str(tmp_path / "absent-arm.json"),
    )
    with pytest.raises(FileNotFoundError):
        github_supervisor.emergency_stop(args)
    assert called is False


def test_github_workflow_uses_env_inputs_and_arm_gates_emergency_stop():
    workflow = GITHUB_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert '--pod-id "${{ inputs.pod_id }}"' not in workflow
    assert '--pod-name "${{ inputs.pod_name }}"' not in workflow
    assert '--deadline "${{ inputs.hard_stop_deadline_utc }}"' not in workflow
    assert '--source-commit "${{ inputs.source_commit }}"' not in workflow
    assert "steps.arm_check.outcome == 'success'" in workflow
    assert '--arm-receipt "$ARMED_RECEIPT_PATH"' in workflow
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
    watchdog = {
        "schema_version": canary.WATCHDOG_SCHEMA,
        "status": "ARMED",
        "provider": "RUNPOD",
        "workload_id": "synthetic-offline-test",
        "hard_stop_deadline_utc": "2026-08-20T12:30:00Z",
        "maximum_wall_seconds": 1800,
        "maximum_spend_usd": "0.50",
        "source_commit_sha256": "1" * 40,
        "oci_image_digest": "sha256:" + "2" * 64,
        "watchdog_script_sha256": preregistration["launch_bindings"][
            "required_watchdog_script_sha256"
        ],
        "emergency_task_name": "CAS-OpenWeight-Canary-Stop-synthetic-offline-test",
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
        "schema_version": "cas_open_weight_trajectory_canary_execution_bindings.v2",
        "source_commit_sha256": "1" * 40,
        "oci_image_digest": "sha256:" + "2" * 64,
        "device": "cuda:0",
        "deterministic_controls": preregistration["experiment"]["runtime"][
            "deterministic_controls"
        ],
        "watchdog_receipt_sha256": canary.sha256_bytes(watchdog_raw),
        "watchdog_status": "ARMED",
        "github_supervisor_receipt_sha256": canary.sha256_bytes(
            github_supervisor_raw
        ),
        "github_supervisor_status": "ARMED_PROVIDER_GET_SUCCEEDED",
        "claim_boundary": "Execution-environment declarations are cross-links, not an independent image attestation or provider receipt.",
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
