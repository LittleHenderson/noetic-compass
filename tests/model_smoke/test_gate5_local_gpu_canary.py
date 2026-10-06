from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "run_project_coherence_gate5_local_gpu_canary.py"
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs"
    / "working"
    / "project_coherence"
    / "gate5"
    / "model_smoke"
    / "GATE5_LOCAL_GPU_CANARY_PROTOCOL_v0.2.json"
)
SPEC = importlib.util.spec_from_file_location("gate5_local_gpu_canary", DRIVER_PATH)
assert SPEC is not None and SPEC.loader is not None
canary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(canary)


def _protocol():
    return canary._load_protocol(PROTOCOL_PATH)[1]


def _valid_runtime() -> dict:
    return {
        "profile": "production",
        "device": "cuda",
        "dtype": "torch.bfloat16",
        "torch_version": "2.13.0+cu126",
        "torch_native_jit_disabled": True,
        "cuda_bfloat16_supported": True,
        "cuda_runtime_version": "12.6",
        "cuda_driver_version": 13010,
        "cuda_device_name": "NVIDIA GeForce RTX 4070 Laptop GPU",
        "cuda_device_capability": "8.9",
    }


def _valid_health(source: dict) -> dict:
    return {
        "verdict": "REAL_PYTHIA_WEIGHTS_LOADED",
        "is_real_model": True,
        "fake_runtime_env": False,
        "model_loaded": True,
        "load_error": None,
        "manifest_is_real_model": True,
        "model_id": source["model_id"],
        "requested_revision": source["model_revision"],
        "resolved_revision": source["model_revision"],
        "revision_verified": True,
        "weights_filename": source["weights_filename"],
        "weights_sha256": source["weights_sha256"],
        "weights_bytes": source["weights_bytes"],
        "weights_hash_verified": True,
        "model_identity_status": "PINNED_REVISION_AND_WEIGHTS_SHA256",
        "runtime_execution": _valid_runtime(),
    }


def _valid_target_receipt() -> dict:
    return {
        "contract_version": canary.ERASER_CONTRACT,
        "method_id": "drive_local_eraser",
        "execution_kind": "real_model_weights",
        "source_kind": "stage27f_calibrated_cover",
        "coordinate_space": "mlp_intermediate_post_activation",
        "requested_gain": 0.5,
        "effective_gain": 0.5,
        "structurally_valid": False,
        "structural_status": "APPLIED_ACTIVATION_CHANGE_OUTPUT_DELTA_UNATTRIBUTED",
        "hook_fired": True,
        "activation_changed": True,
        "output_changed": True,
        "applied_coordinates": [
            {
                "layer": 1,
                "index": 10,
                "coordinate_space": "mlp_intermediate_post_activation",
            }
        ],
        "stability_control_performed": True,
        "baseline_output_stable": True,
        "baseline_geometry_stable": True,
    }


def _image_inspect_kwargs(
    source: dict,
    *,
    parent_layers: list[str] | None = None,
    successor_layers: list[str] | None = None,
) -> dict:
    result = {
        "expected_digest": source["worker_image_digest"],
        "expected_source_commit": source["worker_overlay_source_commit"],
        "expected_user": "10001:10001",
        "expected_parent_image_id": source["parent_worker_image_id"],
        "expected_parent_repo_digest": source["parent_worker_repo_digest"],
        "expected_parent_worker_source": source["parent_worker_source_commit"],
        "expected_runtime_dtype": source["expected_runtime_dtype"],
    }
    if parent_layers is None or successor_layers is None:
        result.update(
            {
                "expected_parent_rootfs_layer_count": source[
                    "parent_rootfs_layer_count"
                ],
                "expected_parent_rootfs_layers_sha256": source[
                    "parent_rootfs_layers_sha256"
                ],
                "expected_successor_rootfs_layer_count": source[
                    "successor_rootfs_layer_count"
                ],
                "expected_successor_rootfs_layers_sha256": source[
                    "successor_rootfs_layers_sha256"
                ],
                "expected_overlay_rootfs_layer_count": source[
                    "overlay_rootfs_layer_count"
                ],
            }
        )
    else:
        result.update(
            {
                "expected_parent_rootfs_layer_count": len(parent_layers),
                "expected_parent_rootfs_layers_sha256": canary._sha256_bytes(
                    canary._canonical_json_bytes(parent_layers)
                ),
                "expected_successor_rootfs_layer_count": len(successor_layers),
                "expected_successor_rootfs_layers_sha256": canary._sha256_bytes(
                    canary._canonical_json_bytes(successor_layers)
                ),
                "expected_overlay_rootfs_layer_count": len(successor_layers)
                - len(parent_layers),
            }
        )
    return result


def test_frozen_protocol_builds_six_schema_shaped_requests() -> None:
    protocol = _protocol()
    assert [arm["arm_id"] for arm in protocol["arms"]] == [
        "clean_baseline",
        "clean_noop_hook",
        "adversarial_baseline",
        "adversarial_noop_hook",
        "clean_target_intervention",
        "adversarial_target_intervention",
    ]
    requests = [canary._build_request(protocol, arm) for arm in protocol["arms"]]
    assert len(requests) == 6
    assert all(request["max_new_tokens"] == 1 for request in requests)
    assert "drive_local_eraser" not in requests[0]["method_config"]["enabled_methods"]
    assert requests[1]["method_config"]["knobs"]["drive_local_eraser"]["gain"] == 0.0
    assert requests[4]["method_config"]["knobs"]["drive_local_eraser"]["gain"] == 0.5


def test_health_requires_exact_production_cuda_identity() -> None:
    source = _protocol()["source_binding"]
    health = _valid_health(source)
    assert canary._health_is_exact(health, source)
    cpu = deepcopy(health)
    cpu["runtime_execution"]["device"] = "cpu"
    assert not canary._health_is_exact(cpu, source)
    fake = deepcopy(health)
    fake["fake_runtime_env"] = True
    assert not canary._health_is_exact(fake, source)
    drift = deepcopy(health)
    drift["weights_sha256"] = "0" * 64
    assert not canary._health_is_exact(drift, source)
    fp16 = deepcopy(health)
    fp16["runtime_execution"]["dtype"] = "torch.float16"
    assert not canary._health_is_exact(fp16, source)
    jit_enabled = deepcopy(health)
    jit_enabled["runtime_execution"]["torch_native_jit_disabled"] = False
    assert not canary._health_is_exact(jit_enabled, source)
    emulated_bfloat16 = deepcopy(health)
    emulated_bfloat16["runtime_execution"]["cuda_bfloat16_supported"] = False
    assert not canary._health_is_exact(emulated_bfloat16, source)


def test_backend_policy_requires_effective_knob_sources_and_no_cache_files() -> None:
    adaptation = _protocol()["adaptation_evidence_binding"]
    policy = {
        "environment_value": "1",
        "policy_effective": True,
        "policy_source_path": (
            "/usr/local/lib/python3.12/site-packages/torch/_native/common_utils.py"
        ),
        "policy_source_sha256": adaptation["torch_native_policy_source_sha256"],
        "triton_policy_source_path": (
            "/usr/local/lib/python3.12/site-packages/torch/_native/triton_utils.py"
        ),
        "triton_policy_source_sha256": adaptation[
            "torch_triton_policy_source_sha256"
        ],
        "compiler_paths": {"cc": None, "gcc": None, "clang": None},
        "root_worker_writable": False,
        "tmp_regular_files": [],
    }
    assert canary._backend_policy_is_exact(policy, adaptation)
    for field, value in (
        ("policy_effective", False),
        ("tmp_regular_files", ["triton/cache.so"]),
        ("compiler_paths", {"cc": "/usr/bin/cc", "gcc": None, "clang": None}),
    ):
        drift = {**policy, field: value}
        assert not canary._backend_policy_is_exact(drift, adaptation)


def test_target_receipt_requires_exact_real_contract_and_measured_hook() -> None:
    receipt = _valid_target_receipt()
    assert canary._target_intervention_receipt_is_exact(receipt, gain=0.5)
    malformed = deepcopy(receipt)
    malformed["contract_version"] = "arbitrary"
    assert not canary._target_intervention_receipt_is_exact(malformed, gain=0.5)
    missing_application = deepcopy(receipt)
    missing_application["applied_coordinates"] = []
    assert not canary._target_intervention_receipt_is_exact(
        missing_application, gain=0.5
    )
    fake = deepcopy(receipt)
    fake["execution_kind"] = "demo_schema_only"
    assert not canary._target_intervention_receipt_is_exact(fake, gain=0.5)


def test_image_inspection_enforces_digest_source_and_user(monkeypatch) -> None:
    source = _protocol()["source_binding"]
    parent_layers = [f"sha256:parent-{index}" for index in range(17)]
    successor_layers = [*parent_layers, "sha256:overlay-0", "sha256:overlay-1", "sha256:overlay-2"]
    parent = {
        "Id": source["parent_worker_image_id"],
        "Config": {
            "Labels": {
                "org.opencontainers.image.revision": source[
                    "parent_worker_source_commit"
                ]
            }
        },
        "RepoDigests": [
            "atlas-live-trace-worker@" + source["parent_worker_repo_digest"]
        ],
        "RootFS": {"Layers": parent_layers},
    }
    image = {
        "Id": "sha256:" + "1" * 64,
        "RepoDigests": ["atlas-live-trace-worker@" + source["worker_image_digest"]],
        "Os": "linux",
        "Architecture": "amd64",
        "Size": 123,
        "RootFS": {"Layers": successor_layers},
        "Config": {
            "User": "10001:10001",
            "Cmd": ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8080"],
            "Env": [
                "ATLAS_WORKER_PROFILE=production",
                "TORCH_DISABLE_NATIVE_JIT=1",
            ],
            "Labels": {
                "org.opencontainers.image.revision": source[
                    "worker_overlay_source_commit"
                ],
                "io.cas-harness.overlay.source": source[
                    "worker_overlay_source_commit"
                ],
                "io.cas-harness.parent.local-image-id": source[
                    "parent_worker_image_id"
                ],
                "io.cas-harness.parent.repo-digest": source[
                    "parent_worker_repo_digest"
                ],
                "io.cas-harness.parent.worker-source": source[
                    "parent_worker_source_commit"
                ],
                "io.cas-harness.runtime.dtype": source["expected_runtime_dtype"],
                "io.cas-harness.runtime.native-jit": "disabled",
                "io.cas-harness.claim-status": "RESEARCH_ONLY_LOCAL_CANARY",
            },
        },
    }

    def fake_run(command, **_kwargs):
        payload = parent if command[-1] == source["parent_worker_image_id"] else image
        return subprocess.CompletedProcess(
            args=["docker"], returncode=0, stdout=json.dumps([payload]).encode(), stderr=b""
        )

    monkeypatch.setattr(canary, "_run", fake_run)
    result = canary._inspect_image(
        source["worker_image"],
        **_image_inspect_kwargs(
            source,
            parent_layers=parent_layers,
            successor_layers=successor_layers,
        ),
    )
    assert result["configured_user"] == "10001:10001"

    image["Config"]["Labels"]["org.opencontainers.image.revision"] = "0" * 40
    with pytest.raises(canary.CanaryError, match="source-commit"):
        canary._inspect_image(
            source["worker_image"],
            **_image_inspect_kwargs(
                source,
                parent_layers=parent_layers,
                successor_layers=successor_layers,
            ),
        )
    image["Config"]["Labels"]["org.opencontainers.image.revision"] = source[
        "worker_overlay_source_commit"
    ]
    image["Config"]["User"] = "0:0"
    with pytest.raises(canary.CanaryError, match="configured user"):
        canary._inspect_image(
            source["worker_image"],
            **_image_inspect_kwargs(
                source,
                parent_layers=parent_layers,
                successor_layers=successor_layers,
            ),
        )
    image["Config"]["User"] = "10001:10001"
    image["Config"]["Env"].remove("TORCH_DISABLE_NATIVE_JIT=1")
    with pytest.raises(canary.CanaryError, match="TORCH_DISABLE_NATIVE_JIT=1"):
        canary._inspect_image(
            source["worker_image"],
            **_image_inspect_kwargs(
                source,
                parent_layers=parent_layers,
                successor_layers=successor_layers,
            ),
        )
    image["Config"]["Env"].append("TORCH_DISABLE_NATIVE_JIT=1")
    image["RepoDigests"] = ["atlas-live-trace-worker@sha256:" + "0" * 64]
    with pytest.raises(canary.CanaryError, match="digest mismatch"):
        canary._inspect_image(
            source["worker_image"],
            **_image_inspect_kwargs(
                source,
                parent_layers=parent_layers,
                successor_layers=successor_layers,
            ),
        )
    image["RepoDigests"] = [
        "atlas-live-trace-worker@" + source["worker_image_digest"]
    ]
    frozen_kwargs = _image_inspect_kwargs(
        source,
        parent_layers=parent_layers,
        successor_layers=successor_layers,
    )
    image["RootFS"]["Layers"] = ["sha256:drift", *successor_layers[1:]]
    with pytest.raises(canary.CanaryError, match="successor rootfs chain"):
        canary._inspect_image(source["worker_image"], **frozen_kwargs)


def test_only_specific_no_such_object_result_proves_cleanup_absence() -> None:
    absent = subprocess.CompletedProcess(
        args=["docker"], returncode=1, stdout=b"[]", stderr=b"Error: No such object: x"
    )
    daemon_failure = subprocess.CompletedProcess(
        args=["docker"], returncode=1, stdout=b"", stderr=b"daemon unavailable"
    )
    present = subprocess.CompletedProcess(
        args=["docker"], returncode=0, stdout=b"[{}]", stderr=b""
    )
    assert canary._docker_inspect_proves_absence(absent)
    assert not canary._docker_inspect_proves_absence(daemon_failure)
    assert not canary._docker_inspect_proves_absence(present)


def test_started_container_inspection_enforces_isolation_and_log_retention(
    monkeypatch,
) -> None:
    image_id = "sha256:" + "1" * 64
    inspected = {
        "Id": "container-id",
        "Image": image_id,
        "Config": {
            "Image": image_id,
            "User": "10001:10001",
            "Env": ["TORCH_DISABLE_NATIVE_JIT=1"],
        },
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Tmpfs": {"/tmp": "rw,noexec,nosuid,nodev,size=67108864"},
            "Memory": 6 * 1024**3,
            "MemorySwap": 6 * 1024**3,
            "PidsLimit": 512,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges:true"],
            "AutoRemove": False,
            "PublishAllPorts": False,
            "PortBindings": {},
        },
    }

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(
            args=["docker"],
            returncode=0,
            stdout=json.dumps([inspected]).encode(),
            stderr=b"",
        )

    monkeypatch.setattr(canary, "_run", fake_run)
    binding = canary._inspect_started_container(
        "test-container",
        expected_image_id=image_id,
        expected_user="10001:10001",
    )
    assert binding["network_mode"] == "none"
    assert binding["auto_remove"] is False
    assert binding["native_jit_disabled_bound"] is True

    inspected["HostConfig"]["NetworkMode"] = "default"
    with pytest.raises(canary.CanaryError, match="network mode none"):
        canary._inspect_started_container(
            "test-container",
            expected_image_id=image_id,
            expected_user="10001:10001",
        )
    inspected["HostConfig"]["NetworkMode"] = "none"
    inspected["Config"]["Env"] = []
    with pytest.raises(canary.CanaryError, match="disabled native JIT"):
        canary._inspect_started_container(
            "test-container",
            expected_image_id=image_id,
            expected_user="10001:10001",
        )


def test_event_sequence_requires_manifest_first_terminal_last_and_contiguous_tokens() -> None:
    manifest = {"type": "manifest", "manifest": {}}
    token = {"type": "token", "token_index": 0, "token": "x"}
    complete = {"type": "complete", "total_tokens": 1}
    assert canary._event_sequence_is_exact(
        [manifest, token, complete], [token], [complete], expected_tokens=1
    )
    assert not canary._event_sequence_is_exact(
        [token, manifest, complete], [token], [complete], expected_tokens=1
    )
    bad_index = {**token, "token_index": 1}
    assert not canary._event_sequence_is_exact(
        [manifest, bad_index, complete],
        [bad_index],
        [complete],
        expected_tokens=1,
    )
    assert not canary._event_sequence_is_exact(
        [manifest, token, complete, {"type": "diagnostic"}],
        [token],
        [complete],
        expected_tokens=1,
    )


def test_unexpected_arm_set_cannot_mint_mechanical_pass() -> None:
    summaries = [
        {
            "arm_id": f"unexpected-{index}",
            "generated_text": "x",
            "checks": {"synthetic": True},
            "mean_inversion_risk": 0.0,
        }
        for index in range(6)
    ]
    receipt = canary._mechanical_receipt(summaries)
    assert receipt["status"] == "FAIL_CLOSED"
    assert receipt["checks"]["exact_frozen_arm_set"] is False
