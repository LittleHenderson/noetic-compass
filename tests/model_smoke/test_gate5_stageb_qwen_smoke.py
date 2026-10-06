from __future__ import annotations

import asyncio
import hashlib
import io
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import tarfile
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run_project_coherence_gate5_stageb_qwen_smoke.py"
SPEC = importlib.util.spec_from_file_location("gate5_stageb_qwen_smoke", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)

from cas_harness_v2 import build_worker_terminal_receipt  # noqa: E402


def _single_file_tar(name: str, body: bytes, *, kind: bytes | None = None) -> bytes:
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        member = tarfile.TarInfo(name)
        member.size = len(body)
        if kind is not None:
            member.type = kind
            member.linkname = "elsewhere"
        archive.addfile(member, io.BytesIO(body))
    return stream.getvalue()


def _packet_plan() -> dict:
    return json.loads(
        (runner.PACKAGE_ROOT / "evidence_packet_plan.json").read_bytes()
    )


def _planned_packet_ids() -> list[str]:
    plan = _packet_plan()["packet_artifact_role_plan"]
    return [
        plan["outcome_artifact"],
        plan["execution_manifest"],
        *(row["evidence_artifact_id"] for row in plan["metrics"]),
        *(row["evidence_artifact_id"] for row in plan["controls"]),
        plan["falsifier"]["evidence_artifact_id"],
        *(row["evidence_artifact_id"] for row in plan["split_results"]),
        plan["uncertainty_artifact"],
        plan["result_summary"],
    ]


def _runner_packet_ids() -> list[str]:
    return [
        runner.OUTPUT_ARTIFACT_ID,
        "stageb-qwen-execution-manifest-001",
        *runner.METRIC_EVIDENCE_IDS.values(),
        *runner.CONTROL_EVIDENCE_IDS.values(),
        "stageb-qwen-falsifier-report-001",
        *runner.SPLIT_EVIDENCE_IDS.values(),
        "stageb-qwen-uncertainty-report-001",
        "stageb-qwen-result-summary-001",
    ]


def test_frozen_stageb_package_loads_with_exact_final_identity() -> None:
    protocol, chain = runner._validate_base_package()

    assert protocol["experimental_execution_status"] == "NOT_STARTED"
    assert protocol["product_route_authorized"] is False
    assert chain.base.sha256 == (
        "4F7D32A9364FC5A470B0FEE575D53C15D027D52CB013AB3EDBBD059A3CCED57D"
    )
    assert chain.base.protected_design_sha256 == (
        "41ECD9E07637F457ED4A4832ED436A8A425675DD2B24C6A15EC1033B5E90D59F"
    )
    assert chain.chain_sha256 == (
        "ADAA0B04AC07CF5DB35A225F93FD5A7E9D2D1C8E7C1730986978F766B28F3343"
    )
    assert chain.amendments == ()
    assert chain.outcome_access is None


def test_runner_packet_inventory_exactly_matches_the_frozen_17_ref_plan() -> None:
    plan = _packet_plan()
    planned = _planned_packet_ids()
    observed = _runner_packet_ids()

    assert set(planned) == set(plan["required_future_packet_artifacts"])
    assert set(observed) == set(planned)
    assert len(planned) == len(set(planned)) == 17
    assert not set(planned).intersection(plan["supporting_nonpacket_or_chain_artifacts"])


def test_runner_threshold_control_and_split_maps_preserve_preregistration_order() -> None:
    preregistration = json.loads(runner.PREREG_PATH.read_bytes())

    assert list(runner.METRIC_EVIDENCE_IDS) == [
        row["threshold_id"] for row in preregistration["thresholds"]
    ]
    assert list(runner.CONTROL_EVIDENCE_IDS) == [
        row["control_id"] for row in preregistration["controls"]
    ]
    assert list(runner.SPLIT_EVIDENCE_IDS) == [
        row["split_id"] for row in preregistration["splits"]
    ]
    assert preregistration["falsifiers"][0]["condition"].endswith(
        "observable by Packet-construction time"
    )


def test_stageb_request_is_plain_single_carrier_with_no_intervention() -> None:
    request = json.loads((runner.PACKAGE_ROOT / "request.json").read_bytes())
    output_contract = json.loads(
        (runner.PACKAGE_ROOT / "output_contract.json").read_bytes()
    )

    assert request["model_id"] == runner.MODEL_ID
    assert request["max_new_tokens"] == 2
    assert request["temperature"] == 0.0
    assert request["probes"] == ["active_trace", "confidence_margin"]
    assert request["method_config"]["enabled_methods"] == ["foundation_probe"]
    assert request["method_config"]["knobs"] == {
        "foundation_probe": {"layer_range": [0, 23], "top_k": 8}
    }
    assert "ablation_target" not in request
    assert "<|im_" not in request["prompt"]
    assert runner.OUTPUT_NAME == output_contract["output_name"]


def test_output_observation_accepts_activation_capture_without_intervention() -> None:
    raw = runner._json_bytes(
        {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": runner.MODEL_ID,
                        "resolved_revision": runner.MODEL_REVISION,
                        "weights_sha256": runner.WEIGHTS_SHA256,
                        "weights_bytes": runner.WEIGHTS_BYTES,
                        "is_real_model": True,
                    },
                },
                {
                    "type": "token",
                    "token": "ok",
                    "top_activated_neurons": [{"layer": 0, "index": 1}],
                },
                {"type": "complete"},
            ]
        }
    )

    observed = runner._output_observation(raw)

    assert observed["token_event_count"] == 1
    assert observed["generated_text"] == "ok"
    assert observed["activation_summary_present"] is True
    assert observed["intervention_event_count"] == 0


def test_output_observation_rejects_an_intervention_event() -> None:
    raw = runner._json_bytes(
        {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": runner.MODEL_ID,
                        "resolved_revision": runner.MODEL_REVISION,
                        "weights_sha256": runner.WEIGHTS_SHA256,
                        "weights_bytes": runner.WEIGHTS_BYTES,
                        "is_real_model": True,
                    },
                },
                {
                    "type": "token",
                    "token": "x",
                    "top_activated_neurons": [{"layer": 0, "index": 1}],
                },
                {"type": "ablation_effect"},
                {"type": "complete"},
            ]
        }
    )

    with pytest.raises(runner.StageBSmokeError, match="non-intervention"):
        runner._output_observation(raw)


def test_runtime_image_identity_requires_an_additive_parent_prefix(monkeypatch) -> None:
    parent_id = "sha256:" + "1" * 64
    child_id = "sha256:" + "2" * 64
    parent = {
        "Id": parent_id,
        "Size": 10,
        "Config": {"Labels": {}},
        "RootFS": {"Layers": ["sha256:base"]},
    }
    child = {
        "Id": child_id,
        "Size": 11,
        "Config": {"Labels": {"bound": "yes"}},
        "RootFS": {"Layers": ["sha256:base", "sha256:additive"]},
    }
    images = {"child:test": child, "parent:test": parent}
    monkeypatch.setattr(runner, "_inspect_image", images.__getitem__)

    identity = runner._image_identity("child:test", parent_reference="parent:test")
    assert identity["image_id"] == child_id
    assert identity["parent_image_id"] == parent_id
    assert identity["parent_rootfs_is_exact_prefix"] is True
    assert identity["added_layer_count"] == 1

    child["RootFS"]["Layers"] = ["sha256:other", "sha256:additive"]
    with pytest.raises(runner.StageBSmokeError, match="additive parent-layer prefix"):
        runner._image_identity("child:test", parent_reference="parent:test")


def test_runtime_image_build_defers_model_invocation_until_authorized_execution() -> None:
    source = inspect.getsource(runner._build_runtime_image)

    assert '"build",' in source
    assert '"run",' not in source
    assert "warm_load" not in source
    assert not hasattr(runner, "_runtime_image_warm_load_canary")
    assert '"model_invocations": 0' in source
    assert '"runtime_validation": "DEFERRED TO THE AUTHORIZED JOINED EXECUTION"' in source


def test_create_only_artifact_writer_never_replaces_existing_bytes(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    original = b'{"status":"original"}\n'
    runner._write_create_only(path, original)

    assert path.read_bytes() == original
    assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(original).digest()
    with pytest.raises(FileExistsError):
        runner._write_create_only(path, b'{"status":"replacement"}\n')
    assert path.read_bytes() == original


def test_weight_tar_stream_is_regular_create_only_and_exact(tmp_path: Path) -> None:
    payload = (b"stageb-file-backed-weight-test\n" * 257) + b"end"
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    destination = tmp_path / "weight.safetensors"

    observation = runner._extract_exact_weight_tar_stream(
        io.BytesIO(_single_file_tar(runner.WEIGHTS_FILENAME, payload)),
        destination,
        expected_sha256=expected_sha256,
        expected_bytes=len(payload),
    )

    assert destination.read_bytes() == payload
    assert observation == {
        "sha256": expected_sha256,
        "byte_length": len(payload),
        "source_member": runner.WEIGHTS_FILENAME,
        "regular_file": True,
        "symlink_or_reparse": False,
    }
    with pytest.raises(FileExistsError):
        runner._extract_exact_weight_tar_stream(
            io.BytesIO(_single_file_tar(runner.WEIGHTS_FILENAME, payload)),
            destination,
            expected_sha256=expected_sha256,
            expected_bytes=len(payload),
        )


@pytest.mark.parametrize(
    ("archive_name", "kind"),
    [
        ("../model.safetensors", None),
        ("model.safetensors", tarfile.SYMTYPE),
    ],
)
def test_weight_tar_stream_rejects_unsafe_members(
    tmp_path: Path,
    archive_name: str,
    kind: bytes | None,
) -> None:
    payload = b"unsafe"
    destination = tmp_path / "weight.safetensors"

    with pytest.raises(runner.StageBSmokeError, match="safe regular-file"):
        runner._extract_exact_weight_tar_stream(
            io.BytesIO(_single_file_tar(archive_name, payload, kind=kind)),
            destination,
            expected_sha256=hashlib.sha256(payload).hexdigest(),
            expected_bytes=len(payload),
        )
    assert not destination.exists()


def test_streamed_secret_scan_finds_a_chunk_boundary_match(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"abcdeSECRETtail")
    monkeypatch.setattr(runner, "WEIGHTS_STREAM_CHUNK_BYTES", 8)

    sha256, byte_length, found = runner._stream_file_observation(
        path,
        secret=b"eSECRET",
    )

    assert sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert byte_length == path.stat().st_size
    assert found is True


def test_weight_materialization_uses_never_started_pinned_container_and_external_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    payload = b"small materialization seam"
    expected_sha256 = hashlib.sha256(payload).hexdigest()
    archive_root = tmp_path / "external-archive"
    archive_path = archive_root / f"sha256-{expected_sha256}.model.safetensors"
    helper_id = "a" * 64
    commands: list[list[str]] = []

    monkeypatch.setattr(runner, "WEIGHTS_SHA256", expected_sha256)
    monkeypatch.setattr(runner, "WEIGHTS_BYTES", len(payload))
    monkeypatch.setattr(runner, "WEIGHTS_ARCHIVE_ROOT", archive_root)
    monkeypatch.setattr(runner, "WEIGHTS_ARCHIVE_PATH", archive_path)

    def fake_run(command, **_kwargs):
        command = list(command)
        commands.append(command)
        if command[:2] == ["docker", "create"]:
            return SimpleNamespace(stdout=(helper_id + "\n").encode("ascii"))
        if command[:2] == ["docker", "inspect"]:
            return SimpleNamespace(
                stdout=runner._json_bytes(
                    [
                        {
                            "Id": helper_id,
                            "Image": runner.PARENT_IMAGE_ID,
                            "HostConfig": {"NetworkMode": "none"},
                            "State": {"Running": False, "Status": "created"},
                        }
                    ]
                )
            )
        raise AssertionError(command)

    def fake_copy(container: str, destination: Path):
        assert container.startswith("cas-g5-stageb-weight-copy-")
        return runner._extract_exact_weight_tar_stream(
            io.BytesIO(_single_file_tar(runner.WEIGHTS_FILENAME, payload)),
            destination,
            expected_sha256=expected_sha256,
            expected_bytes=len(payload),
        )

    def fake_best_effort(command, **_kwargs):
        command = list(command)
        if command[:2] == ["docker", "rm"]:
            return SimpleNamespace(returncode=0), None
        if command[:2] == ["docker", "inspect"]:
            return SimpleNamespace(returncode=1), None
        raise AssertionError(command)

    monkeypatch.setattr(runner, "_run", fake_run)
    monkeypatch.setattr(runner, "_copy_weight_tar_from_created_container", fake_copy)
    monkeypatch.setattr(runner.joined, "_run_best_effort", fake_best_effort)
    monkeypatch.setattr(runner.joined, "_docker_inspect_proves_absence", lambda _value: True)

    path, receipt = runner._materialize_weight_artifact_from_image()

    assert path == archive_path.resolve()
    assert path.read_bytes() == payload
    assert receipt["source_container_path"] == (
        "/worker/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct/"
        "snapshots/7ae557604adf67be50417f59c2c2f167def9a775/model.safetensors"
    )
    assert receipt["storage_scope"] == (
        "EXTERNAL CONTENT-ADDRESSED ARCHIVE / OUTSIDE PACKAGE_ROOT"
    )
    assert receipt["helper_container_started"] is False
    assert receipt["st_nlink"] == 1
    assert receipt["mode_read_only"] or receipt["file_attribute_read_only"] is True
    assert commands[0][0:2] == ["docker", "create"]
    assert "--network" in commands[0] and "none" in commands[0]
    assert commands[0][-1] == runner.PARENT_IMAGE_ID
    assert all(command[1] not in {"run", "start"} for command in commands)

    commands.clear()
    reused_path, reused_receipt = runner._materialize_weight_artifact_from_image()
    assert reused_path == path
    assert reused_receipt["reused_existing"] is True
    assert reused_receipt["sha256"] == expected_sha256
    assert reused_receipt["byte_length"] == len(payload)
    assert reused_receipt["mode_read_only"] or (
        reused_receipt["file_attribute_read_only"] is True
    )
    assert commands == []
    path.chmod(runner.stat.S_IREAD | runner.stat.S_IWRITE)


def test_final_source_surface_binds_every_new_execution_seam() -> None:
    required = {
        "src/cas_harness_v2/__init__.py",
        "src/cas_harness_v2/artifacts.py",
        "src/cas_harness_v2/evidence_packet_builder.py",
        "noetic-compass-scaffold/noetic-compass/api/services/cas_harness_v2_joined_executor.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/routes/health.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/schemas/__init__.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/schemas/manifest.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/event_stream.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/ablation_probe.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/knob_resolution.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/model_loader.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/probe_runner.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/app/runtime/pythia_runner.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/Dockerfile.qwen-instruct-overlay",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/Dockerfile.qwen-stageb-runtime-overlay",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/test_container_preflight.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/test_qwen_probe_adapter.py",
        "noetic-compass-scaffold/noetic-compass/live-trace-worker/tests/test_ablation_probe.py",
        "tests/cas_harness_v2/test_evidence_packet_builder.py",
        "noetic-compass-scaffold/noetic-compass/tests/test_cas_harness_v2_joined_executor.py",
        "noetic-compass-scaffold/noetic-compass/tests/test_cas_harness_v2_live_worker_join.py",
        "scripts/run_project_coherence_gate5_stageb_qwen_smoke.py",
        "tests/model_smoke/test_gate5_stageb_qwen_smoke.py",
    }

    assert required <= set(runner.SOURCE_PATHS)
    assert "Gate 5 remains OPEN / KEEP_OPEN" in SCRIPT.read_text(encoding="utf-8")
    assert "REPORTED_CRITERIA_NOT_MET / INELIGIBLE" in runner.BOUNDARY


@pytest.mark.parametrize(
    "mutate_after_packet_persistence",
    [False, True],
    ids=("stable-retention", "post-build-mutation"),
)
def test_packet_port_reserves_before_persisting_reporting_artifacts(
    tmp_path: Path,
    monkeypatch,
    mutate_after_packet_persistence: bool,
) -> None:
    weight_body = b"file-backed Stage B weight seam\n"
    weight_sha256 = hashlib.sha256(weight_body).hexdigest()
    preregistration_value = json.loads(runner.PREREG_PATH.read_bytes())
    weights = preregistration_value["identities"]["model"]["weights"]
    weights["sha256"] = weight_sha256.upper()
    weights["byte_length"] = len(weight_body)
    chain = runner.PreregistrationChain(
        runner.load_preregistration(
            runner._json_bytes(preregistration_value),
            claim_ledger_bytes=runner.LEDGER_PATH.read_bytes(),
        )
    )
    archive_root = tmp_path / "external-weight-archive"
    archive_root.mkdir()
    archive_path = archive_root / f"sha256-{weight_sha256}.model.safetensors"
    runner._write_create_only(archive_path, weight_body)
    runner._freeze_file_read_only(archive_path)
    monkeypatch.setattr(runner, "WEIGHTS_SHA256", weight_sha256)
    monkeypatch.setattr(runner, "WEIGHTS_BYTES", len(weight_body))
    monkeypatch.setattr(runner, "WEIGHTS_ARCHIVE_ROOT", archive_root)
    monkeypatch.setattr(runner, "WEIGHTS_ARCHIVE_PATH", archive_path)
    chain_artifact_bytes = runner._resolve_chain_artifact_bytes(chain)
    job = runner.FleetJobSnapshot(
        fleet_id="fleet-stageb-local",
        job_id=runner.JOB_ID,
        audit_id="audit-stageb-qwen-joined-001",
        assigned_worker_id="worker-stageb-local-gpu-001",
        layer_start=0,
        layer_end=23,
        shard_id="shard-stageb-qwen-all-layers",
        assigned_methods=("foundation_probe",),
        expected_outputs=(runner.OUTPUT_NAME,),
        model_id=runner.MODEL_ID,
        model_revision=runner.MODEL_REVISION,
        model_artifact_manifest_path="C:/stageb/model_artifact_manifest.json",
        model_artifact_manifest_sha256="d" * 64,
        execution_mode="external_probe_command",
    )
    authorization = runner.build_worker_authorization(
        chain=chain,
        authorization_id=runner.JOB_ID,
        issued_at="2026-08-08T20:55:00.000000Z",
        expires_at="2026-08-08T21:55:00.000000Z",
        execution_mapping=job.execution_mapping(),
        run_nonce=bytes(range(32)),
    )
    output_raw = runner._json_bytes(
        {
            "events": [
                {
                    "type": "manifest",
                    "manifest": {
                        "model_id": runner.MODEL_ID,
                        "resolved_revision": runner.MODEL_REVISION,
                        "weights_sha256": runner.WEIGHTS_SHA256,
                        "weights_bytes": runner.WEIGHTS_BYTES,
                        "is_real_model": True,
                    },
                },
                {
                    "type": "token",
                    "token": "Blue",
                    "top_activated_neurons": [{"layer": 0, "index": 1}],
                },
                {"type": "complete"},
            ]
        }
    )
    output_ref = runner.ArtifactRef(
        artifact_id=runner.OUTPUT_ARTIFACT_ID,
        sha256=runner._sha_upper(output_raw),
        byte_length=len(output_raw),
        media_type="application/json",
    )
    terminal = build_worker_terminal_receipt(
        chain=chain,
        authorization=authorization,
        receipt_id=runner.TERMINAL_RECEIPT_ID,
        worker_started_at="2026-08-08T21:00:00.000000Z",
        terminal_at="2026-08-08T21:01:00.000000Z",
        terminal_status="COMPLETED",
        produced_outputs=(
            {
                "output_name": runner.OUTPUT_NAME,
                "artifact": {
                    "artifact_id": output_ref.artifact_id,
                    "sha256": output_ref.sha256,
                    "byte_length": output_ref.byte_length,
                    "media_type": output_ref.media_type,
                },
            },
        ),
        missing_outputs=(),
        error=None,
    )
    chain.record_outcome_access(
        accessed_at="2026-08-08T21:02:00.000000Z",
        execution_completed_at=terminal.terminal_at,
        receipt=terminal.outcome_access_receipt_ref,
    )

    store = runner.joined.LocalExactByteStore(tmp_path / "run")
    reference_by_id = {ref.artifact_id: ref for ref in chain.artifact_refs}
    for artifact_id, raw in chain_artifact_bytes.items():
        reference = reference_by_id[artifact_id]
        store.put_exact(
            f"chain_artifacts/{artifact_id}.bin",
            raw,
            artifact_id=artifact_id,
            media_type=reference.media_type,
        )
    store.put_exact(
        "authorization.json",
        authorization.raw_bytes,
        artifact_id=authorization.authorization_id,
        media_type="application/vnd.cas-harness.worker-authorization+json",
    )
    store.put_exact(
        "terminal_receipt.json",
        terminal.raw_bytes,
        artifact_id=terminal.receipt_id,
        media_type="application/vnd.cas-harness.worker-terminal-receipt+json",
    )
    store.put_exact(
        "output.json",
        output_raw,
        artifact_id=output_ref.artifact_id,
        media_type=output_ref.media_type,
    )

    class Lifecycle:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def get_reporting_disposition_reservation(self, **_kwargs):
            return None

        def reserve_reporting_disposition(self, **_kwargs):
            self.calls.append("reserve")
            assert not (store.root / "packet_evidence").exists()
            assert not (store.root / "evidence_packet.v2.json").exists()
            return SimpleNamespace(reservation_id="reservation-stageb-001")

        def record_packet(self, **_kwargs):
            self.calls.append("record")
            assert (store.root / "packet_evidence").is_dir()
            assert (store.root / "evidence_packet_execution_manifest.json").is_file()
            assert (store.root / "evidence_packet_assessment.json").is_file()
            assert (store.root / "evidence_packet.v2.json").is_file()
            return SimpleNamespace(idempotent_replay=False)

    lifecycle = Lifecycle()
    ports = runner.StageBPacketPorts(
        lifecycle,
        store,
        chain,
        "tenant-local-stageb",
        runner.JOB_ID,
        chain_artifact_bytes=chain_artifact_bytes,
        chain_artifact_files={runner.WEIGHTS_ARTIFACT_ID: archive_path},
        ephemeral_secret=b"stageb-test-secret-that-is-not-retained-0001",
    )

    if mutate_after_packet_persistence:
        original_put_exact = type(store).put_exact

        def put_exact_then_mutate_weight(
            target_store,
            relative_path,
            raw,
            *,
            artifact_id,
            media_type,
        ):
            binding = original_put_exact(
                target_store,
                relative_path,
                raw,
                artifact_id=artifact_id,
                media_type=media_type,
            )
            if target_store is store and relative_path == "evidence_packet.v2.json":
                archive_path.chmod(runner.stat.S_IREAD | runner.stat.S_IWRITE)
                archive_path.write_bytes(b"X" * len(weight_body))
                runner._freeze_file_read_only(archive_path)
            return binding

        monkeypatch.setattr(type(store), "put_exact", put_exact_then_mutate_weight)

    if mutate_after_packet_persistence:
        with pytest.raises(
            runner.StageBSmokeError,
            match="final retained packet artifact verification failed",
        ):
            asyncio.run(
                ports.record_packet(
                    authorization=authorization,
                    job_snapshot=job,
                    terminal_receipt=terminal,
                    output_name=runner.OUTPUT_NAME,
                    output_artifact=output_ref,
                    output_body=output_raw,
                )
            )
        assert lifecycle.calls == ["reserve"]
        assert ports.packet_build_result is None
        assert ports.packet_binding is None
        archive_path.chmod(runner.stat.S_IREAD | runner.stat.S_IWRITE)
        return

    acceptance = asyncio.run(
        ports.record_packet(
            authorization=authorization,
            job_snapshot=job,
            terminal_receipt=terminal,
            output_name=runner.OUTPUT_NAME,
            output_artifact=output_ref,
            output_body=output_raw,
        )
    )

    assert lifecycle.calls == ["reserve", "record"]
    assert acceptance.packet_id == runner.PACKET_ID
    assert acceptance.packet_artifact_id == runner.PACKET_ARTIFACT_ID
    assert ports.packet_build_result.assessment.preregistered_criteria == (
        "REPORTED_CRITERIA_NOT_MET"
    )
    assert ports.packet_build_result.assessment.scientific_eligibility == "INELIGIBLE"
    registry_index = json.loads(
        (store.root / "evidence_packet_registry_index.json").read_bytes()
    )
    assert len(registry_index) == len(ports.packet_build_result.artifact_registry.artifact_ids)
    weight_entry = next(
        row
        for row in registry_index
        if row["artifact_id"] == runner.WEIGHTS_ARTIFACT_ID
    )
    assert weight_entry["storage_scope"] == "EXTERNAL_CONTENT_ADDRESSED_ARCHIVE"
    assert Path(weight_entry["path"]) == archive_path.resolve()
    assert not any(
        path.name.endswith(".safetensors")
        for path in store.root.rglob("*")
        if path.is_file()
    )
    archive_path.chmod(runner.stat.S_IREAD | runner.stat.S_IWRITE)
