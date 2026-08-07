from __future__ import annotations

import asyncio
from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import httpx
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "run_project_coherence_gate5_joined_local_gpu_smoke.py"
SPEC = importlib.util.spec_from_file_location("gate5_joined_local_gpu_smoke", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)
REAL_REQUIRE_CLEAN_SOURCE = runner._require_clean_source


COMMIT = "a" * 40
IMAGE_ID = "sha256:" + "b" * 64


def _image(image_id: str = IMAGE_ID) -> dict:
    return {
        "Id": image_id,
        "Architecture": "amd64",
        "Os": "linux",
        "Size": 4_400_000_000,
        "Config": {
            "User": "10001:10001",
            "Labels": {
                "io.cas-harness.claim-status": "RESEARCH_ONLY_LOCAL_JOINED_MECHANICS",
                "io.cas-harness.joined-binding.authority": "WORKER_PROCESS_OBSERVATION_ONLY",
                "io.cas-harness.scientific-status": "NOT_ESTABLISHED",
                "io.cas-harness.gate5-status": "OPEN",
                "io.cas-harness.license-status": "NOT_LICENSED",
                "io.cas-harness.disclosure-status": "HELD",
                "org.opencontainers.image.revision": COMMIT,
            },
        },
    }


def _prepared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(runner, "_require_clean_source", lambda: COMMIT)
    monkeypatch.setattr(runner, "_inspect_image", lambda _reference: _image())
    result = runner._prepare(tmp_path / "prepared", image_reference="joined:test")
    monkeypatch.setattr(runner, "_require_clean_source", REAL_REQUIRE_CLEAN_SOURCE)
    return result


def _joined_response(request: httpx.Request) -> bytes:
    retained = (
        REPO_ROOT / "docs" / "working" / "project_coherence" / "gate5"
        / "model_smoke" / "runs" / "gate5-pythia-canary-20260807T035947Z-9f81c34de1b6"
        / "adversarial_target_intervention.response.json"
    )
    response = json.loads(retained.read_bytes())
    events_raw = json.dumps(response["events"], sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False, allow_nan=False).encode("utf-8")
    request_raw = request.content
    invocation = request.headers["X-CAS-Joined-Invocation-ID"]
    response["joined_execution_binding"] = {
        "schema_version": "cas_harness_live_worker.joined_execution_binding.v1",
        "status": "OBSERVED_REQUEST_AND_EVENTS_BOUND",
        "authority": "WORKER_PROCESS_OBSERVATION_ONLY",
        "authorization_sha256": request.headers["X-CAS-Joined-Authorization-SHA256"],
        "prospective_run_id": request.headers["X-CAS-Joined-Run-ID"],
        "invocation_id_sha256": hashlib.sha256(invocation.encode("ascii")).hexdigest().upper(),
        "request_sha256": hashlib.sha256(request_raw).hexdigest().upper(),
        "request_byte_length": len(request_raw),
        "events_sha256": hashlib.sha256(events_raw).hexdigest().upper(),
        "events_byte_length": len(events_raw),
        "digest_profile": "UTF8_SORTED_KEYS_COMPACT_JSON_ENSURE_ASCII_FALSE_V1",
        "binding_scope": "EXACT_REQUEST_BYTES_AND_CANONICAL_EVENTS_MEMBER_ONLY",
        "nonclaim": "NOT_A_SIGNATURE_OR_TRUSTED_EXECUTION_ATTESTATION",
    }
    return json.dumps(response, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def test_script_imports_and_retains_nonpromoting_boundary():
    assert SCRIPT.is_file()
    assert runner.CLAIM_ID == "CLM-GATE5-JOINED-MECHANICS-OBSERVATION"
    assert "LOCAL SINGLE-HOST / NOT WORM / NON-PRODUCTION" in runner.BOUNDARY
    assert "NO PROMPT-INJECTION DETECTION CLAIM" in runner.BOUNDARY
    assert "NO STEERING EFFICACY CLAIM" in runner.BOUNDARY
    assert runner.DockerExecLoopbackLiveDump.transport_label == (
        "DOCKER_EXEC_LOOPBACK / NETWORK_NONE / LOCAL_ONLY"
    )
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"--network", "none"' in source
    assert '"--publish"' not in source
    assert "EvidencePacketRepository" not in source


def test_exact_byte_store_is_create_only_fsync_reread_and_rejects_collision(tmp_path):
    store = runner.LocalExactByteStore(tmp_path / "bytes")
    raw = b'{"exact":true}\n'
    receipt = store.put_exact("artifact.json", raw, artifact_id="artifact-001",
                              media_type="application/json")

    assert (tmp_path / "bytes" / "artifact.json").read_bytes() == raw
    assert receipt.sha256 == hashlib.sha256(raw).hexdigest()
    assert receipt.byte_length == len(raw)
    assert store.authority == "LOCAL SINGLE-HOST / NOT WORM / NON-PRODUCTION"
    with pytest.raises(FileExistsError):
        store.put_exact("artifact.json", raw, artifact_id="artifact-001",
                        media_type="application/json")


def test_prepare_emits_schema_loadable_noncanonical_claim_and_preregistration(
    tmp_path, monkeypatch
):
    protocol_path = _prepared(tmp_path, monkeypatch)
    prepared = runner._load_prepared(protocol_path)
    protocol = json.loads(protocol_path.read_bytes())

    assert prepared.chain.base.claim_id == runner.CLAIM_ID
    assert prepared.chain.base.payload["permitted_wording"]["claim_ceiling"] == "DIAGNOSTIC_ONLY"
    assert prepared.chain.base.payload["governance"] == {
        "admission_ring": 4,
        "product_claim_status": "NOT LICENSED",
        "disclosure_status": "HELD",
        "public_release": False,
        "product_route": False,
        "license_decision": "NONE",
    }
    assert protocol["limitations"] == {
        "worm": "NOT ESTABLISHED",
        "postgres": "NOT USED",
        "admitted_route": "NOT USED",
        "scientific_efficacy": "NOT ESTABLISHED",
        "gate5": "OPEN",
        "packet": "NOT CREATED",
    }
    assert protocol["predecessor_failure_binding"]["run_id"] == runner.PREDECESSOR_RUN_ID
    assert protocol["predecessor_failure_binding"]["status"] == (
        "FAIL_CLOSED / ZERO MODEL INVOCATIONS"
    )
    assert protocol["predecessor_failure_binding"]["failure_receipt"]["sha256"] == (
        runner.PREDECESSOR_RECEIPT_SHA256.upper()
    )
    adaptation = json.loads(
        (protocol_path.parent / "network_none_adaptation.json").read_bytes()
    )
    assert adaptation["diagnostic_kind"] == "NON_MODEL_ENTRYPOINT_CONTAINER"
    assert adaptation["model_invocations"] == 0
    assert adaptation["observed_network_mode"] == "none"
    assert prepared.request_raw == runner.REQUEST_SOURCE.read_bytes()
    manifest = json.loads(prepared.model_manifest_raw)
    assert manifest["artifacts"] == [{
        "path": runner.WEIGHTS_FILE,
        "sha256": runner.WEIGHTS_SHA256,
        "byte_count": runner.WEIGHTS_BYTES,
    }]


def test_load_prepared_rejects_an_incomplete_binding_inventory(tmp_path, monkeypatch):
    protocol_path = _prepared(tmp_path, monkeypatch)
    protocol = json.loads(protocol_path.read_bytes())
    protocol["artifact_bindings"] = []
    protocol_path.write_bytes(runner._json_bytes(protocol))

    with pytest.raises(runner.JoinedLocalSmokeError, match="inventory is incomplete"):
        runner._load_prepared(protocol_path)


@pytest.mark.parametrize("field", ["claim_text", "controls", "limitations"])
def test_load_prepared_rejects_protocol_invariant_drift(tmp_path, monkeypatch, field):
    protocol_path = _prepared(tmp_path, monkeypatch)
    protocol = json.loads(protocol_path.read_bytes())
    protocol[field] = "DRIFTED" if field == "claim_text" else {}
    protocol_path.write_bytes(runner._json_bytes(protocol))

    with pytest.raises(runner.JoinedLocalSmokeError, match="invariants differ"):
        runner._load_prepared(protocol_path)


def test_cleanup_absence_requires_specific_docker_error():
    daemon_error = subprocess.CompletedProcess(
        ["docker", "inspect"], 1, b"", b"daemon transport unavailable"
    )
    no_such_object = subprocess.CompletedProcess(
        ["docker", "inspect"], 1, b"", b"Error: No such object: worker"
    )

    assert not runner._docker_inspect_proves_absence(daemon_error)
    assert runner._docker_inspect_proves_absence(no_such_object)


def test_network_none_validation_rejects_an_attached_bridge():
    none = {
        "HostConfig": {"NetworkMode": "none"},
        "NetworkSettings": {
            "Ports": {},
            "Networks": {
                "none": {
                    "NetworkID": "a" * 64, "EndpointID": "b" * 64, "Gateway": "",
                    "IPAddress": "", "MacAddress": "", "IPPrefixLen": 0,
                    "IPv6Gateway": "", "GlobalIPv6Address": "",
                    "GlobalIPv6PrefixLen": 0,
                }
            },
        },
    }
    attached = json.loads(json.dumps(none))
    attached["NetworkSettings"]["Networks"]["bridge"] = {
        "NetworkID": "bridge-id", "IPAddress": "172.17.0.2"
    }

    assert runner._container_has_exact_none_network(none)
    assert not runner._container_has_exact_none_network(attached)
    missing_runtime_identity = json.loads(json.dumps(none))
    missing_runtime_identity["NetworkSettings"]["Networks"]["none"]["EndpointID"] = ""
    assert not runner._container_has_exact_none_network(missing_runtime_identity)


def test_docker_exec_port_prevalidates_without_entering_subprocess(monkeypatch):
    calls = 0

    async def forbidden(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("subprocess boundary must not be entered")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    port = runner.DockerExecLoopbackLiveDump("worker")
    with pytest.raises(runner.JoinedLiveDumpPreSendFailure):
        asyncio.run(port.invoke_once(
            request_raw=b"{}", authorization_sha256="bad",
            prospective_run_id="run-001", invocation_id="invocation-00000001",
        ))
    assert calls == 0
    assert port.calls == 0


def test_docker_exec_port_crosses_one_subprocess_boundary_with_exact_stdin(monkeypatch):
    calls: list[tuple[tuple[object, ...], bytes]] = []
    response_raw = b'{"events":[],"joined_execution_binding":{}}'

    class Process:
        returncode = 0

        async def communicate(self, carrier: bytes):
            calls.append((arguments, carrier))
            return response_raw, b""

        def kill(self):
            raise AssertionError("successful process must not be killed")

        async def wait(self):
            return 0

    async def create(*args, **kwargs):
        nonlocal arguments
        arguments = args
        assert kwargs["stdin"] is asyncio.subprocess.PIPE
        assert kwargs["stdout"] is asyncio.subprocess.PIPE
        return Process()

    arguments: tuple[object, ...] = ()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    request_raw = b'{"prompt":"exact"}\n'
    port = runner.DockerExecLoopbackLiveDump("worker-container")
    result = asyncio.run(port.invoke_once(
        request_raw=request_raw, authorization_sha256="A" * 64,
        prospective_run_id="h2run_0000000000000001",
        invocation_id="invocation-00000001",
    ))

    assert result == response_raw
    assert port.calls == 1
    assert len(calls) == 1
    args, carrier = calls[0]
    assert args[:4] == ("docker", "exec", "--interactive", "worker-container")
    assert "X-CAS-Joined-Request-SHA256" in args[-1]
    size = int.from_bytes(carrier[:4], "big")
    metadata = json.loads(carrier[4:4 + size])
    assert carrier[4 + size:] == request_raw
    assert metadata == {
        "authorization_sha256": "A" * 64,
        "prospective_run_id": "h2run_0000000000000001",
        "invocation_id": "invocation-00000001",
    }


def test_docker_exec_failure_is_post_send_indeterminate_and_never_retried(monkeypatch):
    boundaries = 0

    class Process:
        returncode = 73
        async def communicate(self, _carrier): return b"", b"private remote detail"
        def kill(self): raise AssertionError("completed process is not killed")
        async def wait(self): return 73

    async def create(*_args, **_kwargs):
        nonlocal boundaries
        boundaries += 1
        return Process()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", create)
    port = runner.DockerExecLoopbackLiveDump("worker")
    with pytest.raises(runner.JoinedLiveDumpPostSendIndeterminate) as caught:
        asyncio.run(port.invoke_once(
            request_raw=b"{}", authorization_sha256="A" * 64,
            prospective_run_id="h2run_0000000000000001",
            invocation_id="invocation-00000001",
        ))
    assert "private remote detail" not in str(caught.value)
    assert boundaries == 1
    assert port.calls == 1


def test_local_lifecycle_join_succeeds_once_with_mocked_strict_http_transport(
    tmp_path, monkeypatch
):
    protocol_path = _prepared(tmp_path, monkeypatch)
    prepared = runner._load_prepared(protocol_path)
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        body = _joined_response(request)
        return httpx.Response(200, stream=httpx.ByteStream(body), headers={
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })

    async def execute():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            live = runner.StrictLiveWorkerDumpClient(
                runner.StrictLiveWorkerDumpClientConfig(
                    worker_base_url="http://127.0.0.1:8080",
                    worker_token="ephemeral-test-token",
                    timeout_seconds=5,
                ), http_client=client,
            )
            store = runner.LocalExactByteStore(tmp_path / "run")
            return await runner._run_joined_kernel(
                prepared, store, store.root / "lifecycle.sqlite3", live
            )

    result, invocations = asyncio.run(execute())
    assert result.status == runner.SUCCESS_NO_PACKET_RECORDED
    assert result.packet_status == "NOT_CREATED"
    assert result.gate_status == "OPEN"
    assert invocations == 1
    assert len(seen) == 1
    assert (tmp_path / "run" / "authorization.json").is_file()
    assert (tmp_path / "run" / "consumption.json").is_file()
    assert (tmp_path / "run" / "output.json").is_file()
    assert (tmp_path / "run" / "terminal_receipt.json").is_file()
    assert (tmp_path / "run" / "outcome_access.json").is_file()
    assert (tmp_path / "run" / "nonreporting.json").is_file()
    assert (tmp_path / "run" / "reconciliation.json").is_file()
    assert (tmp_path / "run" / "lifecycle.sqlite3").is_file()
    assert runner._joined_result_is_exact_success(
        result,
        prepared=prepared,
        invocation_count=invocations,
        run_root=tmp_path / "run",
    )
    assert not runner._joined_result_is_exact_success(
        replace(result, model_invocation_count=2),
        prepared=prepared,
        invocation_count=invocations,
        run_root=tmp_path / "run",
    )
    assert not runner._joined_result_is_exact_success(
        object(),
        prepared=prepared,
        invocation_count=invocations,
        run_root=tmp_path / "run",
    )


def test_execute_preflight_refuses_dirty_tree_before_image_or_model(tmp_path, monkeypatch):
    protocol_path = _prepared(tmp_path, monkeypatch)
    image_calls = 0
    monkeypatch.setattr(runner, "_git_status_porcelain", lambda: " M source.py")

    def image(_reference):
        nonlocal image_calls
        image_calls += 1
        return _image()

    monkeypatch.setattr(runner, "_inspect_image", image)
    with pytest.raises(runner.JoinedLocalSmokeError, match="clean"):
        runner._execute_preflight(protocol_path)
    assert image_calls == 0


def test_execute_preflight_refuses_source_commit_drift_before_image(tmp_path, monkeypatch):
    protocol_path = _prepared(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(runner, "_git_head", lambda: "c" * 40)
    monkeypatch.setattr(runner, "_git_is_ancestor", lambda _source, _head: False)
    monkeypatch.setattr(runner, "_inspect_image",
                        lambda _reference: (_ for _ in ()).throw(AssertionError("no image call")))
    with pytest.raises(runner.JoinedLocalSmokeError, match="does not descend"):
        runner._execute_preflight(protocol_path)


def test_execute_preflight_refuses_untracked_protocol_before_image(tmp_path, monkeypatch):
    protocol_path = _prepared(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(runner, "_git_head", lambda: COMMIT)
    monkeypatch.setattr(runner, "_git_is_ancestor", lambda _source, _head: True)
    monkeypatch.setattr(runner, "_inspect_image",
                        lambda _reference: (_ for _ in ()).throw(AssertionError("no image call")))
    with pytest.raises(runner.JoinedLocalSmokeError, match="outside the repository"):
        runner._execute_preflight(protocol_path)


def test_execute_preflight_refuses_image_drift_without_model_invocation(tmp_path, monkeypatch):
    protocol_path = _prepared(tmp_path, monkeypatch)
    monkeypatch.setattr(runner, "_git_status_porcelain", lambda: "")
    monkeypatch.setattr(runner, "_git_head", lambda: COMMIT)
    monkeypatch.setattr(runner, "_git_is_ancestor", lambda _source, _head: True)
    monkeypatch.setattr(runner, "_require_frozen_commit_boundary",
                        lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runner, "_validate_frozen_source_manifest",
                        lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runner, "_inspect_image", lambda _reference: _image("sha256:" + "d" * 64))
    with pytest.raises(runner.JoinedLocalSmokeError, match="image identity drifted"):
        runner._execute_preflight(protocol_path)


def test_execute_mocked_success_retains_true_cleanup_and_success_receipt(
    tmp_path, monkeypatch
):
    protocol_path = _prepared(tmp_path, monkeypatch)
    prepared = replace(
        runner._load_prepared(protocol_path),
        validated_execution_commit=COMMIT,
        validated_source_to_execution_paths=(
            "docs/working/project_coherence/gate5/joined_model_smoke_v0.2/protocol.json",
        ),
    )
    monkeypatch.setattr(runner, "_execute_preflight", lambda _path: prepared)

    none_network = {
        "HostConfig": {"NetworkMode": "none"},
        "NetworkSettings": {
            "Ports": {},
            "Networks": {
                "none": {
                    "NetworkID": "a" * 64, "EndpointID": "b" * 64, "Gateway": "",
                    "IPAddress": "", "MacAddress": "", "IPPrefixLen": 0,
                    "IPv6Gateway": "", "GlobalIPv6Address": "",
                    "GlobalIPv6PrefixLen": 0,
                }
            },
        },
    }

    def command(command, *, timeout=60.0):
        del timeout
        if command[1] == "run":
            return subprocess.CompletedProcess(command, 0, b"container-id\n", b"")
        if command[1] == "inspect":
            return subprocess.CompletedProcess(
                command, 0, runner._json_bytes([none_network]), b""
            )
        if command[1] == "logs":
            return subprocess.CompletedProcess(command, 0, b"safe worker log\n", b"")
        raise AssertionError(command)

    post_inspects = 0

    def best_effort(command, *, timeout):
        nonlocal post_inspects
        del timeout
        if command[1] == "rm":
            return subprocess.CompletedProcess(command, 0, b"worker\n", b""), None
        if command[1] == "inspect":
            post_inspects += 1
            if post_inspects == 1:
                return subprocess.CompletedProcess(
                    command, 0, runner._json_bytes([none_network]), b""
                ), None
            return subprocess.CompletedProcess(
                command, 1, b"", b"Error: No such object: worker"
            ), None
        raise AssertionError(command)

    class LiveDump:
        transport_label = "DOCKER_EXEC_LOOPBACK / NETWORK_NONE / LOCAL_ONLY"

        def __init__(self, _container):
            self.calls = 0

        async def invoke_once(
            self, *, request_raw, authorization_sha256,
            prospective_run_id, invocation_id,
        ):
            self.calls += 1
            request = httpx.Request(
                "POST", "http://127.0.0.1:8080/sessions/dump",
                content=request_raw,
                headers={
                    "X-CAS-Joined-Authorization-SHA256": authorization_sha256,
                    "X-CAS-Joined-Run-ID": prospective_run_id,
                    "X-CAS-Joined-Invocation-ID": invocation_id,
                },
            )
            return _joined_response(request)

    monkeypatch.setattr(runner, "_command", command)
    monkeypatch.setattr(runner, "_run_best_effort", best_effort)
    monkeypatch.setattr(runner, "_health", lambda _container: b'{"health":"exact"}\n')
    monkeypatch.setattr(runner, "DockerExecLoopbackLiveDump", LiveDump)

    receipt_path = runner._execute(protocol_path, tmp_path / "runs")
    receipt = json.loads(receipt_path.read_bytes())
    cleanup = json.loads((receipt_path.parent / "cleanup_proof.json").read_bytes())

    assert receipt["status"] == runner.SUCCESS_NO_PACKET_RECORDED
    assert receipt["model_invocation_count"] == 1
    assert receipt["error"] is None
    assert cleanup == {
        "network_none_reverified_before_removal": True,
        "container_remove_command_succeeded": True,
        "container_absence_specifically_verified": True,
        "ephemeral_env_file_removed_after_context": True,
    }
