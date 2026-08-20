"""Model-free, network-free tests for the create-once RunPod transaction."""

from __future__ import annotations

import base64
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
LAUNCHER_PATH = (
    REPOSITORY_ROOT
    / "tools"
    / "runpod_open_weight_canary_v2"
    / "create_provider_launch_receipt.py"
)
RUNNER_PATH = (
    REPOSITORY_ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "live-trace-worker"
    / "scripts"
    / "run_open_weight_trajectory_canary_v2.py"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


launcher = _load_module("runpod_create_provider_launch_receipt_test", LAUNCHER_PATH)
runner = _load_module("runpod_create_provider_launch_runner_test", RUNNER_PATH)

NOW = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
POD_ID = "newpod123abc"
POD_NAME = (
    "cas-open-weight-canary-v2-attempt-0123456789abcdef0123456789abcdef"
)
IMAGE_NAME = "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404"
PUBLIC_KEY = (
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGYybnRoZXRpY2tleWZvcnRlc3Rz"
    " launcher-test"
)


def _utc(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _response(
    *,
    pod_id: str = POD_ID,
    pod_name: str = POD_NAME,
    interruptible: object = False,
    locked: object = False,
    encrypted: object = True,
    desired_status: str = "RUNNING",
    started: str = "2026-08-20 12:00:00.000 +0000 UTC",
) -> dict[str, object]:
    return {
        "desiredStatus": desired_status,
        "id": pod_id,
        "interruptible": interruptible,
        "lastStartedAt": started,
        "locked": locked,
        "name": pod_name,
        "volumeEncrypted": encrypted,
    }


def _raw_response(value: dict[str, object]) -> bytes:
    # Deliberately preserve whitespace and non-sorted insertion order. The
    # receipt must retain these exact entity-body bytes, not a reconstruction.
    return json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")


def _observation(
    body: bytes,
    *,
    status: int = 201,
    url: str = launcher.CREATE_URL,
    content_encoding: str | None = None,
) -> launcher.HttpObservation:
    return launcher.HttpObservation(
        status=status,
        body=body,
        request_observed_at_utc=_utc(NOW),
        response_observed_at_utc=_utc(NOW + timedelta(seconds=1)),
        elapsed_milliseconds=1000,
        effective_url=url,
        content_type="application/json; charset=utf-8",
        content_encoding=content_encoding,
        request_id="fake-request-123",
    )


class FakeTransport:
    def __init__(
        self,
        create_observation: launcher.HttpObservation | None = None,
        *,
        create_exception: Exception | None = None,
        inventory: list[dict[str, object]] | None = None,
        get_identity_id: str = POD_ID,
        get_identity_name: str = POD_NAME,
        stop_http_status: int = 200,
        terminal_after_stop: bool = True,
        actions: list[str] | None = None,
    ):
        self.create_observation = create_observation or _observation(
            _raw_response(_response())
        )
        self.create_exception = create_exception
        self.inventory = inventory or []
        self.get_identity_id = get_identity_id
        self.get_identity_name = get_identity_name
        self.stop_http_status = stop_http_status
        self.terminal_after_stop = terminal_after_stop
        self.actions = actions if actions is not None else []
        self.create_calls = 0
        self.list_calls = 0
        self.get_calls = 0
        self.stop_calls = 0
        self.request_bytes: bytes | None = None
        self.state = "RUNNING"
        self._lock = threading.Lock()

    def create_pod(self, request_body: bytes) -> launcher.HttpObservation:
        with self._lock:
            self.create_calls += 1
        self.actions.append("POST_CREATE")
        self.request_bytes = request_body
        if self.create_exception is not None:
            raise self.create_exception
        return self.create_observation

    def list_pods(self) -> launcher.HttpObservation:
        self.list_calls += 1
        self.actions.append("GET_INVENTORY")
        return _observation(
            json.dumps(self.inventory, separators=(",", ":")).encode("utf-8"),
            status=200,
        )

    def get_pod(self, pod_id: str) -> launcher.HttpObservation:
        self.get_calls += 1
        self.actions.append("GET_EXACT")
        body = {
            "desiredStatus": self.state,
            "id": self.get_identity_id,
            "lastStartedAt": "2026-08-20 12:00:00.000 +0000 UTC",
            "name": self.get_identity_name,
        }
        return _observation(
            json.dumps(body, separators=(",", ":")).encode("utf-8"),
            status=200,
            url=f"https://rest.runpod.io/v1/pods/{pod_id}",
        )

    def stop_pod(self, pod_id: str) -> launcher.HttpObservation:
        self.stop_calls += 1
        self.actions.append("POST_STOP")
        if self.stop_http_status == 200 and self.terminal_after_stop:
            self.state = "EXITED"
        return _observation(
            b"{}",
            status=self.stop_http_status,
            url=f"https://rest.runpod.io/v1/pods/{pod_id}/stop",
        )


class FakeGuardian:
    def __init__(
        self,
        actions: list[str],
        *,
        prearm_failure: bool = False,
        bind_failure: bool = False,
        malformed_receipt: bool = False,
        consumed_keys: set[str] | None = None,
        consume_lock: threading.Lock | None = None,
        pre_arm_inventory: list[dict[str, str]] | None = None,
    ):
        self.actions = actions
        self.prearm_failure = prearm_failure
        self.bind_failure = bind_failure
        self.malformed_receipt = malformed_receipt
        self.consumed_keys = consumed_keys if consumed_keys is not None else set()
        self.consume_lock = consume_lock or threading.Lock()
        self.pre_arm_inventory = pre_arm_inventory or []

    def consume_authorization_and_arm_precreate(
        self, intent: dict[str, object]
    ) -> bytes:
        self.actions.append("GUARDIAN_PREARM")
        if self.prearm_failure:
            raise launcher.ProtocolFailure("FAKE_GUARDIAN_PREARM_FAILED")
        if self.malformed_receipt:
            return b'{"status":"not-bound"}\n'
        consumption_key = launcher.sha256_bytes(
            (
                str(intent["authorization_id"])
                + "\n"
                + str(intent["request_body_sha256"])
            ).encode("utf-8")
        )
        with self.consume_lock:
            if consumption_key in self.consumed_keys:
                raise launcher.ProtocolFailure(
                    "FAKE_GUARDIAN_AUTHORIZATION_ALREADY_CONSUMED"
                )
            self.consumed_keys.add(consumption_key)
        return launcher.build_guardian_receipt(
            intent,
            guardian_id="fake-guardian:test-v1",
            pre_arm_inventory=self.pre_arm_inventory,
        )

    def bind_exact_pod(self, _context: launcher.ArmContext) -> None:
        self.actions.append("GITHUB_BIND_EXACT")
        if self.bind_failure:
            raise launcher.ProtocolFailure("FAKE_GITHUB_BIND_FAILED")


class FakeLocalArm:
    def __init__(self, actions: list[str], *, fail: bool = False):
        self.actions = actions
        self.fail = fail

    def arm(self, _context: launcher.ArmContext) -> None:
        self.actions.append("LOCAL_ARM")
        if self.fail:
            raise launcher.ProtocolFailure("FAKE_LOCAL_ARM_FAILED")


class AdvancingGuardian(FakeGuardian):
    def __init__(self, actions: list[str], clock_state: dict[str, datetime], advance: timedelta):
        super().__init__(actions)
        self.clock_state = clock_state
        self.advance = advance

    def consume_authorization_and_arm_precreate(
        self, intent: dict[str, object]
    ) -> bytes:
        raw = super().consume_authorization_and_arm_precreate(intent)
        self.clock_state["now"] += self.advance
        return raw


class TypeTamperingGuardian(FakeGuardian):
    def __init__(self, actions: list[str], field: str, replacement: object):
        super().__init__(actions)
        self.field = field
        self.replacement = replacement

    def consume_authorization_and_arm_precreate(
        self, intent: dict[str, object]
    ) -> bytes:
        raw = super().consume_authorization_and_arm_precreate(intent)
        value = launcher.strict_json_object(raw, "guardian")
        value[self.field] = self.replacement
        value.pop("guardian_receipt_sha256")
        value["guardian_receipt_sha256"] = launcher.sha256_bytes(
            launcher.canonical_json_bytes(value)
        )
        return launcher.canonical_json_bytes(value)


class RunnerValidator:
    def __init__(self, actions: list[str], *, fail: bool = False):
        self.actions = actions
        self.fail = fail

    def validate(
        self,
        _receipt_path: Path,
        receipt_raw: bytes,
        configuration: launcher.LaunchConfiguration,
    ) -> None:
        self.actions.append("VALIDATE_RECEIPT")
        if self.fail:
            raise launcher.ProtocolFailure("FAKE_RECEIPT_VALIDATION_FAILED")
        runner._validate_provider_launch_receipt(
            receipt_raw,
            source_commit_sha256=configuration.source_commit_sha256,
            oci_image_digest=configuration.oci_image_digest,
            expected_image_name=configuration.image_name,
            require_current_time=False,
        )


class FailingWriter:
    def __init__(self, fail_name: str):
        self.fail_name = fail_name
        self.delegate = launcher.DurableCreateNewWriter()

    def create_new(self, path: Path, raw: bytes) -> None:
        if path.name == self.fail_name:
            raise launcher.ProtocolFailure("INJECTED_WRITE_FAILURE")
        self.delegate.create_new(path, raw)


class BarrierWriter:
    def __init__(self, barrier: threading.Barrier):
        self.barrier = barrier
        self.delegate = launcher.DurableCreateNewWriter()

    def create_new(self, path: Path, raw: bytes) -> None:
        if path.name.endswith(".authorization-consumed.json"):
            self.barrier.wait(timeout=5)
        self.delegate.create_new(path, raw)


def _authorization(
    configuration: launcher.LaunchConfiguration,
    *,
    authorization_id: str = "authorization-0123456789abcdef",
) -> dict[str, object]:
    request_sha = launcher.sha256_bytes(
        launcher.canonical_json_bytes(launcher.build_create_request(configuration))
    )
    return launcher._self_hashed(
        {
            "authorization_id": authorization_id,
            "claim_boundary": launcher.AUTHORIZATION_CLAIM,
            "expires_at_utc": _utc(NOW + timedelta(minutes=10)),
            "issued_at_utc": _utc(NOW - timedelta(minutes=1)),
            "maximum_spend_usd": "0.50",
            "maximum_wall_seconds": 1800,
            "oci_image_digest": configuration.oci_image_digest,
            "one_use": True,
            "operation": "CREATE_EXACTLY_ONE_NEW_RUNPOD_POD",
            "pod_name": configuration.pod_name,
            "provider": "RUNPOD",
            "request_body_sha256": request_sha,
            "schema_version": launcher.AUTHORIZATION_SCHEMA,
            "source_commit_sha256": configuration.source_commit_sha256,
            "status": "AUTHORIZED_FOR_ONE_NEW_RUNPOD_CANARY",
        },
        "authorization_sha256",
    )


def _configuration(tmp_path: Path) -> launcher.LaunchConfiguration:
    tmp_path.mkdir(parents=True, exist_ok=True)
    state = tmp_path / "state"
    state.mkdir()
    public_key_path = tmp_path / "runpod_cas.pub"
    public_key_path.write_text(PUBLIC_KEY + "\n", encoding="utf-8", newline="\n")
    placeholder = launcher.LaunchConfiguration(
        pod_name=POD_NAME,
        source_commit_sha256="1" * 40,
        oci_image_digest="sha256:" + "2" * 64,
        image_name=IMAGE_NAME,
        public_key=PUBLIC_KEY,
        authorization_path=tmp_path / "authorization.json",
        expected_authorization_sha256="0" * 64,
        state_directory=state,
        provider_receipt_path=tmp_path / "provider-launch.receipt.json",
        failure_evidence_path=tmp_path / "provider-launch.failure.json",
        public_key_path=public_key_path,
    )
    raw = launcher.canonical_json_bytes(_authorization(placeholder))
    placeholder.authorization_path.write_bytes(raw)
    return replace(
        placeholder, expected_authorization_sha256=launcher.sha256_bytes(raw)
    )


def _execute(
    configuration: launcher.LaunchConfiguration,
    transport: FakeTransport,
    *,
    guardian: FakeGuardian | None = None,
    local: FakeLocalArm | None = None,
    validator: RunnerValidator | None = None,
    writer=None,
    secret_guard: launcher.SecretGuard | None = None,
    clock=None,
):
    actions = transport.actions
    return launcher.execute_create_once(
        configuration,
        transport=transport,
        guardian=guardian or FakeGuardian(actions),
        local_arm=local or FakeLocalArm(actions),
        validator=validator or RunnerValidator(actions),
        writer=writer,
        secret_guard=secret_guard or launcher.SecretGuard(),
        clock=clock or (lambda: NOW),
        sleeper=lambda _seconds: None,
        terminal_poll_limit=2,
        stop_attempt_limit=2,
    )


def test_success_binds_exact_raw_bytes_and_arm_order(tmp_path: Path):
    configuration = _configuration(tmp_path)
    actions: list[str] = []
    response_raw = b'{\n  "locked": false, "id": "newpod123abc",\n' + (
        b'  "name": "' + POD_NAME.encode("ascii") + b'",\n'
    ) + (
        b'  "interruptible": false, "volumeEncrypted": true,\n'
        b'  "desiredStatus": "RUNNING",\n'
        b'  "lastStartedAt": "2026-08-20 12:00:00.000 +0000 UTC"\n}'
    )
    transport = FakeTransport(_observation(response_raw), actions=actions)

    outcome = _execute(configuration, transport)

    assert outcome.status == "CREATE_RECEIPT_VALIDATED_AND_BOTH_GUARDIANS_ARMED"
    assert transport.create_calls == 1
    assert actions == [
        "GUARDIAN_PREARM",
        "POST_CREATE",
        "VALIDATE_RECEIPT",
        "GITHUB_BIND_EXACT",
        "LOCAL_ARM",
    ]
    receipt = launcher.strict_json_object(
        configuration.provider_receipt_path.read_bytes(), "receipt"
    )
    disk_raw = configuration.provider_receipt_path.read_bytes()
    assert disk_raw.endswith(b"\n") and not disk_raw.endswith(b"\r\n")
    assert disk_raw == launcher.canonical_json_bytes(receipt)
    for path in tmp_path.rglob("*.json"):
        value = launcher.strict_json_object(path.read_bytes(), path.name)
        assert path.read_bytes() == launcher.canonical_json_bytes(value)
    transaction = receipt["create_transaction"]
    assert base64.b64decode(transaction["response_body_base64"]) == response_raw
    assert transaction["response_body_sha256"] == launcher.sha256_bytes(response_raw)
    assert base64.b64decode(transaction["request_body_base64"]) == (
        transport.request_bytes
    )
    assert transaction["response_http_status"] == 201
    assert transaction["effective_url"] == launcher.CREATE_URL


def test_launcher_disk_receipt_passes_pwsh7_and_windows_powershell5(
    tmp_path: Path,
):
    executables: list[str] = []
    pwsh = shutil.which("pwsh")
    if pwsh:
        executables.append(pwsh)
    if sys.platform == "win32":
        powershell5 = Path(
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        )
        if powershell5.is_file():
            executables.append(str(powershell5))
    executables = list(dict.fromkeys(executables))
    if not executables:
        pytest.skip("PowerShell is unavailable")

    configuration = _configuration(tmp_path)
    response = _response()
    response.update({"costPerHr": 0.44, "gpuCount": 1, "volumeInGb": 20})
    outcome = _execute(
        configuration,
        FakeTransport(_observation(_raw_response(response))),
    )
    assert outcome.status == "CREATE_RECEIPT_VALIDATED_AND_BOTH_GUARDIANS_ARMED"
    receipt = launcher.strict_json_object(
        configuration.provider_receipt_path.read_bytes(), "launcher receipt"
    )

    for index, executable in enumerate(executables):
        completed = subprocess.run(
            [
                executable,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(launcher.WATCHDOG_PATH),
                "-ValidateProviderLaunchReceiptOnly",
                "-PodId",
                str(receipt["pod_id"]),
                "-PodName",
                str(receipt["pod_name"]),
                "-RunStartedAtUtc",
                str(receipt["provider_started_at_utc"]),
                "-HardStopDeadlineUtc",
                str(receipt["hard_stop_deadline_utc"]),
                "-SourceCommitSha256",
                configuration.source_commit_sha256,
                "-OciImageDigest",
                configuration.oci_image_digest,
                "-ExpectedImageName",
                configuration.image_name,
                "-ObservedHourlyRate",
                configuration.observed_hourly_rate,
                "-ReceiptDirectory",
                str(tmp_path / f"unused-watchdog-{index}"),
                "-ProviderLaunchReceiptPath",
                str(configuration.provider_receipt_path),
                "-ExpectedPublicKeyPath",
                str(configuration.public_key_path),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=45,
        )
        assert completed.returncode == 0, (
            executable + "\n" + completed.stdout + completed.stderr
        )
        assert "PROVIDER_LAUNCH_RECEIPT_VALIDATION_PASS_NO_PROVIDER_CALL" in (
            completed.stdout
        )


def test_cli_live_is_structural_no_go_before_any_transport(monkeypatch, capsys):
    constructed = {"value": False}

    def forbidden_transport(*_args, **_kwargs):
        constructed["value"] = True
        raise AssertionError("transport must remain unreachable")

    monkeypatch.setattr(launcher, "RunPodHttpsTransport", forbidden_transport)
    assert launcher.main(["--mode", "live"]) == 4
    assert constructed["value"] is False
    assert capsys.readouterr().out.strip() == (
        "LIVE_NO_GO_PRECREATE_GUARDIAN_UNAVAILABLE"
    )


@pytest.mark.parametrize("malformed", (False, True))
def test_create_never_runs_until_precreate_guardian_receipt_validates(
    tmp_path: Path, malformed: bool
):
    configuration = _configuration(tmp_path)
    actions: list[str] = []
    transport = FakeTransport(actions=actions)
    guardian = FakeGuardian(
        actions,
        prearm_failure=not malformed,
        malformed_receipt=malformed,
    )

    outcome = _execute(configuration, transport, guardian=guardian)

    assert outcome.status == "FAILED_BEFORE_CREATE_NO_PROVIDER_MUTATION"
    assert transport.create_calls == 0
    assert actions == ["GUARDIAN_PREARM"]


@pytest.mark.parametrize(
    ("field", "replacement"),
    (("one_use", 1), ("maximum_wall_seconds", 1800.0)),
)
def test_authorization_rejects_bool_integer_type_confusion_before_post(
    tmp_path: Path, field: str, replacement: object
):
    configuration = _configuration(tmp_path)
    value = launcher.strict_json_object(
        configuration.authorization_path.read_bytes(), "authorization"
    )
    value[field] = replacement
    value.pop("authorization_sha256")
    value["authorization_sha256"] = launcher.sha256_bytes(
        launcher.canonical_json_bytes(value)
    )
    raw = launcher.canonical_json_bytes(value)
    configuration.authorization_path.write_bytes(raw)
    configuration = replace(
        configuration, expected_authorization_sha256=launcher.sha256_bytes(raw)
    )
    transport = FakeTransport()

    outcome = _execute(configuration, transport)

    assert outcome.status == "FAILED_BEFORE_CREATE_NO_PROVIDER_MUTATION"
    assert transport.create_calls == 0


def test_pod_name_requires_exact_128_bit_lowercase_hex_suffix_before_post(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    configuration = replace(
        configuration,
        pod_name="cas-open-weight-canary-v2-attempt-0123456789abcdef0123",
    )
    transport = FakeTransport()

    outcome = _execute(configuration, transport)

    assert outcome.failure_code == "POD_NAME_HIGH_ENTROPY_SUFFIX_REQUIRED"
    assert outcome.status == "FAILED_BEFORE_CREATE_NO_PROVIDER_MUTATION"
    assert transport.create_calls == 0


@pytest.mark.parametrize(
    ("field", "replacement"),
    (("guardian_consumption_generation", True), ("pre_arm_inventory_count", False)),
)
def test_guardian_rejects_bool_integer_type_confusion_before_post(
    tmp_path: Path, field: str, replacement: object
):
    configuration = _configuration(tmp_path)
    actions: list[str] = []
    transport = FakeTransport(actions=actions)
    guardian = TypeTamperingGuardian(actions, field, replacement)

    outcome = _execute(configuration, transport, guardian=guardian)

    assert outcome.status == "FAILED_BEFORE_CREATE_NO_PROVIDER_MUTATION"
    assert transport.create_calls == 0


def test_slow_guardian_cannot_post_after_authorization_or_window_expires(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    actions: list[str] = []
    transport = FakeTransport(actions=actions)
    clock_state = {"now": NOW}
    guardian = AdvancingGuardian(actions, clock_state, timedelta(minutes=11))

    outcome = _execute(
        configuration,
        transport,
        guardian=guardian,
        clock=lambda: clock_state["now"],
    )

    assert outcome.failure_code == "PRE_SEND_AUTHORIZATION_OR_GUARDIAN_WINDOW_STALE"
    assert outcome.status == "FAILED_BEFORE_CREATE_NO_PROVIDER_MUTATION"
    assert transport.create_calls == 0


@pytest.mark.parametrize(
    ("advance_seconds", "expected_create_calls"),
    ((169, 1), (171, 0)),
)
def test_pre_send_margin_reserves_full_exchange_ceiling_plus_clock_skew(
    tmp_path: Path, advance_seconds: int, expected_create_calls: int
):
    configuration = _configuration(tmp_path)
    actions: list[str] = []
    clock_state = {"now": NOW}
    requested = NOW + timedelta(seconds=advance_seconds)
    response = _response(
        started=requested.strftime("%Y-%m-%d %H:%M:%S.000 +0000 UTC")
    )
    observation = launcher.HttpObservation(
        status=201,
        body=_raw_response(response),
        request_observed_at_utc=_utc(requested),
        response_observed_at_utc=_utc(requested + timedelta(seconds=1)),
        elapsed_milliseconds=1000,
        effective_url=launcher.CREATE_URL,
        content_type="application/json",
        request_id="freshness-boundary",
    )
    transport = FakeTransport(observation, actions=actions)
    guardian = AdvancingGuardian(
        actions, clock_state, timedelta(seconds=advance_seconds)
    )

    outcome = _execute(
        configuration,
        transport,
        guardian=guardian,
        clock=lambda: clock_state["now"],
    )

    assert transport.create_calls == expected_create_calls
    if expected_create_calls:
        assert outcome.status == "CREATE_RECEIPT_VALIDATED_AND_BOTH_GUARDIANS_ARMED"
    else:
        assert outcome.failure_code == "PRE_SEND_AUTHORIZATION_OR_GUARDIAN_WINDOW_STALE"
        assert outcome.status == "FAILED_BEFORE_CREATE_NO_PROVIDER_MUTATION"


def test_precreate_deadline_caps_runtime_from_window_start(tmp_path: Path):
    configuration = _configuration(tmp_path)
    actions: list[str] = []
    clock_state = {"now": NOW}
    started = NOW + timedelta(minutes=2, seconds=30)
    response = _response(
        started="2026-08-20 12:02:30.000 +0000 UTC"
    )
    observation = launcher.HttpObservation(
        status=201,
        body=_raw_response(response),
        request_observed_at_utc=_utc(started),
        response_observed_at_utc=_utc(started + timedelta(seconds=1)),
        elapsed_milliseconds=1000,
        effective_url=launcher.CREATE_URL,
        content_type="application/json",
        request_id="delayed-create",
    )
    transport = FakeTransport(observation, actions=actions)
    guardian = AdvancingGuardian(
        actions, clock_state, timedelta(minutes=2, seconds=30)
    )

    outcome = _execute(
        configuration,
        transport,
        guardian=guardian,
        clock=lambda: clock_state["now"],
    )

    assert outcome.status == "CREATE_RECEIPT_VALIDATED_AND_BOTH_GUARDIANS_ARMED"
    receipt = launcher.strict_json_object(
        configuration.provider_receipt_path.read_bytes(), "receipt"
    )
    assert launcher.parse_utc(receipt["hard_stop_deadline_utc"]) == (
        NOW + timedelta(seconds=1800)
    )
    assert launcher.parse_utc(receipt["hard_stop_deadline_utc"]) - started == (
        timedelta(minutes=27, seconds=30)
    )


@pytest.mark.parametrize(
    "body",
    (
        (
            b'{"id":"newpod123abc","name":"'
            + POD_NAME.encode("ascii")
            + b'","interruptible":false,"interruptible":true,'
            b'"locked":false,"volumeEncrypted":true,"desiredStatus":"RUNNING",'
            b'"lastStartedAt":"2026-08-20T12:00:00Z"}'
        ),
        (
            b'{"id":"newpod123abc","name":"'
            + POD_NAME.encode("ascii")
            + b'","interruptible":false,"locked":false,"volumeEncrypted":true,'
            b'"desiredStatus":"RUNNING","lastStartedAt":"2026-08-20T12:00:00Z",'
            b'"hostile":NaN}'
        ),
    ),
)
def test_duplicate_or_nonfinite_create_json_stops_salvaged_exact_id(
    tmp_path: Path, body: bytes
):
    configuration = _configuration(tmp_path)
    transport = FakeTransport(_observation(body))

    outcome = _execute(configuration, transport)

    assert outcome.status == "FAILED_CLOSED_TERMINAL_CONFIRMED"
    assert outcome.failure_code == "CREATE_RESPONSE_STRICT_JSON_INVALID"
    assert transport.create_calls == 1
    assert transport.stop_calls == 1


def test_documented_schema_400_is_one_attempt_with_no_fallback_or_retry(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    transport = FakeTransport(
        _observation(b'{"error":"unknown field volumeEncrypted"}', status=400),
        inventory=[
            {
                "id": "existing123",
                "lastStartedAt": "2026-08-20T12:00:01Z",
                "name": POD_NAME,
            }
        ],
    )

    outcome = _execute(configuration, transport)

    assert outcome.status == "FAILED_DEFINITIVE_CREATE_REJECTED_NO_POD_MUTATION"
    assert outcome.failure_code == "CREATE_HTTP_STATUS_NOT_201"
    assert transport.create_calls == 1
    assert transport.list_calls == 0
    assert transport.stop_calls == 0
    assert transport.request_bytes is not None
    assert b'"volumeEncrypted":true' in transport.request_bytes


def test_documented_400_error_body_id_is_not_treated_as_created_identity(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    transport = FakeTransport(
        _observation(
            _raw_response(_response()),
            status=400,
        )
    )

    outcome = _execute(configuration, transport)

    assert outcome.failure_code == "CREATE_HTTP_STATUS_NOT_201"
    assert outcome.status == "FAILED_DEFINITIVE_CREATE_REJECTED_NO_POD_MUTATION"
    assert transport.create_calls == 1
    assert transport.list_calls == 0
    assert transport.stop_calls == 0


@pytest.mark.parametrize("capture_failure", ("oversized", "read-error"))
def test_known_exact_origin_400_remains_definitive_when_body_capture_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capture_failure: str
):
    class FakeHttpResponse:
        status = 400

        def read(self, _limit: int) -> bytes:
            if capture_failure == "read-error":
                raise OSError("synthetic body read failure")
            return b"x" * (launcher.MAX_RESPONSE_BYTES + 1)

        def getheader(self, _name: str) -> None:
            return None

    class FakeHttpsConnection:
        def request(self, *_args, **_kwargs) -> None:
            return None

        def getresponse(self) -> FakeHttpResponse:
            return FakeHttpResponse()

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        launcher.http.client,
        "HTTPSConnection",
        lambda *_args, **_kwargs: FakeHttpsConnection(),
    )
    real_transport = launcher.RunPodHttpsTransport("synthetic-api-key-never-logged")
    with pytest.raises(launcher.AmbiguousCreateFailure) as captured:
        real_transport.create_pod(b"{}\n")
    assert captured.value.known_http_status == 400
    assert captured.value.effective_url == launcher.CREATE_URL

    configuration = _configuration(tmp_path)
    transport = FakeTransport(
        create_exception=captured.value,
        inventory=[
            {
                "createdAt": "2026-08-20T12:00:01Z",
                "id": "existing123",
                "lastStartedAt": "2026-08-20T12:00:01Z",
                "name": POD_NAME,
            }
        ],
    )

    outcome = _execute(configuration, transport)

    assert outcome.status == "FAILED_DEFINITIVE_CREATE_REJECTED_NO_POD_MUTATION"
    assert transport.create_calls == 1
    assert transport.list_calls == 0
    assert transport.get_calls == 0
    assert transport.stop_calls == 0
    failure = launcher.strict_json_object(
        configuration.failure_evidence_path.read_bytes(), "failure"
    )
    assert failure["create_http_status_observed"] == 400
    assert failure["create_response_capture_status"] == (
        "HTTP_STATUS_ONLY_BODY_CAPTURE_INCOMPLETE"
    )
    assert failure["create_observation_sha256"] is None


@pytest.mark.parametrize("status", (200, 202, 500))
def test_unexpected_or_server_status_with_unique_identity_is_contained(
    tmp_path: Path, status: int
):
    configuration = _configuration(tmp_path)
    transport = FakeTransport(
        _observation(_raw_response(_response()), status=status)
    )

    outcome = _execute(configuration, transport)

    assert outcome.failure_code == "CREATE_HTTP_STATUS_NOT_201"
    assert outcome.status == "FAILED_CLOSED_TERMINAL_CONFIRMED"
    assert transport.create_calls == 1
    assert transport.stop_calls == 1


@pytest.mark.parametrize(("status", "encrypted"), ((201, True), (201, False), (202, True), (500, True)))
def test_prearm_id_collision_is_non_actionable_for_every_response_provenance(
    tmp_path: Path, status: int, encrypted: bool
):
    configuration = _configuration(tmp_path)
    actions: list[str] = []
    guardian = FakeGuardian(
        actions,
        pre_arm_inventory=[{"id": POD_ID, "name": "some-old-unrelated-pod"}],
    )
    transport = FakeTransport(
        _observation(_raw_response(_response(encrypted=encrypted)), status=status),
        inventory=[
            {
                "createdAt": "2026-08-20T12:00:01Z",
                "id": POD_ID,
                "lastStartedAt": "2026-08-20T12:00:01Z",
                "name": POD_NAME,
            }
        ],
        actions=actions,
    )

    outcome = _execute(configuration, transport, guardian=guardian)

    if status == 201:
        assert outcome.failure_code == "STRICT_201_ID_PREEXISTED_PREARM"
    else:
        assert outcome.failure_code == "CREATE_HTTP_STATUS_NOT_201"
    assert outcome.status == "FAILED_OPERATOR_INTERVENTION_REQUIRED"
    assert outcome.pod_id is None
    assert transport.create_calls == 1
    assert transport.list_calls == 1
    assert transport.get_calls == 0
    assert transport.stop_calls == 0
    assert "GITHUB_BIND_EXACT" not in actions
    assert "LOCAL_ARM" not in actions
    failure = launcher.strict_json_object(
        configuration.failure_evidence_path.read_bytes(), "failure"
    )
    assert failure["non_actionable_observed_pod_id_sha256"] == (
        launcher.sha256_bytes(POD_ID.encode("utf-8"))
    )


@pytest.mark.parametrize(
    ("change", "expected_code"),
    (
        ({"name": POD_NAME + "-mismatch"}, "CREATE_RESPONSE_POD_NAME_MISMATCH"),
        ({"lastStartedAt": "2026-08-20T13:00:00Z"}, "CREATE_RESPONSE_START_OUTSIDE_EXCHANGE"),
        ({"volumeEncrypted": False}, "CREATE_RESPONSE_VOLUME_ENCRYPTED_NOT_TRUE"),
        ({"volumeEncrypted": None}, "CREATE_RESPONSE_VOLUME_ENCRYPTED_NOT_TRUE"),
        ({"interruptible": True}, "CREATE_RESPONSE_INTERRUPTIBLE_NOT_FALSE"),
        ({"locked": True}, "CREATE_RESPONSE_LOCKED_NOT_FALSE"),
    ),
)
def test_semantic_create_mismatch_stops_exact_returned_id(
    tmp_path: Path, change: dict[str, object], expected_code: str
):
    configuration = _configuration(tmp_path)
    response = _response()
    response.update(change)
    transport = FakeTransport(_observation(_raw_response(response)))

    outcome = _execute(configuration, transport)

    assert outcome.failure_code == expected_code
    assert outcome.status == "FAILED_CLOSED_TERMINAL_CONFIRMED"
    assert transport.stop_calls == 1


def test_strict_201_id_containment_is_id_only_after_provider_name_drift(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    normalized_name = POD_NAME + "-provider-normalized"
    transport = FakeTransport(
        _observation(
            _raw_response(_response(pod_name=normalized_name, encrypted=False))
        ),
        get_identity_name=normalized_name,
    )

    outcome = _execute(configuration, transport)

    assert outcome.failure_code == "CREATE_RESPONSE_POD_NAME_MISMATCH"
    assert outcome.status == "FAILED_CLOSED_TERMINAL_CONFIRMED"
    assert transport.stop_calls == 1


def test_response_write_failure_stops_exact_id(tmp_path: Path):
    configuration = _configuration(tmp_path)
    transport = FakeTransport()
    writer = FailingWriter(configuration.provider_receipt_path.name)

    outcome = _execute(configuration, transport, writer=writer)

    assert outcome.failure_code == "INJECTED_WRITE_FAILURE"
    assert outcome.status == "FAILED_CLOSED_TERMINAL_CONFIRMED"
    assert transport.stop_calls == 1
    assert not configuration.provider_receipt_path.exists()


@pytest.mark.parametrize(("github_fail", "local_fail"), ((True, False), (False, True)))
def test_github_or_local_arm_failure_stops_exact_id(
    tmp_path: Path, github_fail: bool, local_fail: bool
):
    configuration = _configuration(tmp_path)
    actions: list[str] = []
    transport = FakeTransport(actions=actions)

    outcome = _execute(
        configuration,
        transport,
        guardian=FakeGuardian(actions, bind_failure=github_fail),
        local=FakeLocalArm(actions, fail=local_fail),
    )

    assert outcome.status == "FAILED_CLOSED_TERMINAL_CONFIRMED"
    assert transport.stop_calls == 1
    if github_fail:
        assert "LOCAL_ARM" not in actions
    else:
        assert actions.index("GITHUB_BIND_EXACT") < actions.index("LOCAL_ARM")


def test_stop_failure_is_explicit_and_never_claims_terminal(tmp_path: Path):
    configuration = _configuration(tmp_path)
    response = _response(encrypted=False)
    transport = FakeTransport(
        _observation(_raw_response(response)),
        stop_http_status=500,
        terminal_after_stop=False,
    )

    outcome = _execute(configuration, transport)

    assert outcome.status == "FAILED_OPERATOR_INTERVENTION_REQUIRED"
    assert outcome.stop_status == "STOP_FAILED_OPERATOR_INTERVENTION_REQUIRED"
    failure = launcher.strict_json_object(
        configuration.failure_evidence_path.read_bytes(), "failure"
    )
    assert failure["status"] == "FAILED_OPERATOR_INTERVENTION_REQUIRED"
    assert failure["stop_status"] == "STOP_FAILED_OPERATOR_INTERVENTION_REQUIRED"
    assert all("body_base64" not in event for event in failure["events"])


def test_protected_id_is_never_mutated(tmp_path: Path):
    configuration = _configuration(tmp_path)
    protected = "q2oqlooejhin7s"
    transport = FakeTransport(
        _observation(_raw_response(_response(pod_id=protected))),
        get_identity_id=protected,
    )

    outcome = _execute(configuration, transport)

    assert outcome.failure_code == "PROTECTED_POD_ID_RETURNED_BY_CREATE"
    assert outcome.status == "FAILED_OPERATOR_INTERVENTION_REQUIRED"
    assert transport.stop_calls == 0


def test_replay_or_preexisting_output_never_creates_again(tmp_path: Path):
    configuration = _configuration(tmp_path)
    first = FakeTransport()
    assert _execute(configuration, first).status == (
        "CREATE_RECEIPT_VALIDATED_AND_BOTH_GUARDIANS_ARMED"
    )
    second = FakeTransport()

    outcome = _execute(configuration, second)

    assert outcome.status == "FAILED_BEFORE_CREATE_NO_PROVIDER_MUTATION"
    assert second.create_calls == 0
    assert outcome.provider_receipt_path is None


def test_two_concurrent_invocations_share_one_exclusive_create_attempt(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    actions: list[str] = []
    transport = FakeTransport(actions=actions)
    writer = BarrierWriter(threading.Barrier(2))
    outcomes: list[launcher.LaunchOutcome] = []

    def invoke() -> None:
        outcomes.append(
            _execute(configuration, transport, writer=writer)
        )

    threads = [threading.Thread(target=invoke), threading.Thread(target=invoke)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)
    assert transport.create_calls == 1
    assert len(outcomes) == 2
    assert sum(
        outcome.status == "CREATE_RECEIPT_VALIDATED_AND_BOTH_GUARDIANS_ARMED"
        for outcome in outcomes
    ) == 1


def test_shared_fake_guardian_consumption_blocks_auth_across_output_roots(
    tmp_path: Path,
):
    first_configuration = _configuration(tmp_path / "first")
    second_root = tmp_path / "second"
    second_root.mkdir()
    second_state = second_root / "state"
    second_state.mkdir()
    second_configuration = replace(
        first_configuration,
        state_directory=second_state,
        provider_receipt_path=second_root / "provider-launch.receipt.json",
        failure_evidence_path=second_root / "provider-launch.failure.json",
    )
    consumed_keys: set[str] = set()
    consume_lock = threading.Lock()
    actions: list[str] = []
    guardian = FakeGuardian(
        actions, consumed_keys=consumed_keys, consume_lock=consume_lock
    )
    first_transport = FakeTransport(actions=actions)
    second_transport = FakeTransport(actions=actions)

    first = _execute(first_configuration, first_transport, guardian=guardian)
    second = _execute(second_configuration, second_transport, guardian=guardian)

    assert first.status == "CREATE_RECEIPT_VALIDATED_AND_BOTH_GUARDIANS_ARMED"
    assert second.status == "FAILED_BEFORE_CREATE_NO_PROVIDER_MUTATION"
    assert first_transport.create_calls + second_transport.create_calls == 1


def test_timeout_after_create_inventory_reconciles_unique_name_and_stops(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    inventory = [
        {
            "id": POD_ID,
            "lastStartedAt": "2026-08-20T12:00:01Z",
            "name": POD_NAME,
        }
    ]
    transport = FakeTransport(
        create_exception=launcher.AmbiguousCreateFailure(
            "RUNPOD_CREATE_EXCHANGE_AMBIGUOUS"
        ),
        inventory=inventory,
    )

    outcome = _execute(configuration, transport)

    assert transport.create_calls == 1
    assert transport.list_calls == 1
    assert transport.stop_calls == 1
    assert outcome.pod_id == POD_ID
    assert outcome.status == "FAILED_CLOSED_TERMINAL_CONFIRMED"


def test_guardian_inventory_binding_remains_id_authoritative_after_name_drift(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    inventory = [
        {
            "createdAt": "2026-08-20T12:00:01Z",
            "id": POD_ID,
            "lastStartedAt": "2026-08-20T12:00:01Z",
            "name": POD_NAME,
        }
    ]
    transport = FakeTransport(
        create_exception=launcher.AmbiguousCreateFailure(
            "RUNPOD_CREATE_EXCHANGE_AMBIGUOUS"
        ),
        inventory=inventory,
        get_identity_name=POD_NAME + "-drifted-after-binding",
    )

    outcome = _execute(configuration, transport)

    assert outcome.pod_id == POD_ID
    assert outcome.status == "FAILED_CLOSED_TERMINAL_CONFIRMED"
    assert transport.stop_calls == 1


def test_ambiguous_multiple_inventory_matches_never_mutates(tmp_path: Path):
    configuration = _configuration(tmp_path)
    inventory = [
        {
            "id": pod_id,
            "lastStartedAt": "2026-08-20T12:00:01Z",
            "name": POD_NAME,
        }
        for pod_id in (POD_ID, "newpod456def")
    ]
    transport = FakeTransport(
        create_exception=launcher.AmbiguousCreateFailure(
            "RUNPOD_CREATE_EXCHANGE_AMBIGUOUS"
        ),
        inventory=inventory,
    )

    outcome = _execute(configuration, transport)

    assert outcome.status == "FAILED_OPERATOR_INTERVENTION_REQUIRED"
    assert transport.stop_calls == 0


def test_ambiguous_reconciliation_rejects_old_pod_restarted_in_window(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    inventory = [
        {
            "createdAt": "2026-08-01T00:00:00Z",
            "id": "stale12345",
            "lastStartedAt": "2026-08-20T12:00:01Z",
            "name": POD_NAME,
        }
    ]
    transport = FakeTransport(
        create_exception=launcher.AmbiguousCreateFailure(
            "RUNPOD_CREATE_EXCHANGE_AMBIGUOUS"
        ),
        inventory=inventory,
    )

    outcome = _execute(configuration, transport)

    assert outcome.status == "FAILED_OPERATOR_INTERVENTION_REQUIRED"
    assert transport.list_calls == 1
    assert transport.stop_calls == 0


def test_prearm_inventory_exact_name_presence_blocks_post(tmp_path: Path):
    configuration = _configuration(tmp_path)
    actions: list[str] = []
    transport = FakeTransport(actions=actions)
    guardian = FakeGuardian(
        actions,
        pre_arm_inventory=[{"id": "stale12345", "name": POD_NAME}],
    )

    outcome = _execute(configuration, transport, guardian=guardian)

    assert outcome.status == "FAILED_BEFORE_CREATE_NO_PROVIDER_MUTATION"
    assert outcome.failure_code == "PRECREATE_GUARDIAN_NAME_ALREADY_PRESENT"
    assert transport.create_calls == 0


def test_secret_sentinel_never_enters_receipts_failures_or_outcome(tmp_path: Path):
    configuration = _configuration(tmp_path)
    sentinel = "RUNPOD-SECRET-SENTINEL-DO-NOT-PERSIST"
    transport = FakeTransport()
    transport.secret = sentinel

    outcome = _execute(
        configuration,
        transport,
        secret_guard=launcher.SecretGuard([sentinel]),
    )

    assert outcome.status == "CREATE_RECEIPT_VALIDATED_AND_BOTH_GUARDIANS_ARMED"
    observed = b"".join(
        path.read_bytes() for path in tmp_path.rglob("*.json") if path.is_file()
    )
    assert sentinel.encode("utf-8") not in observed
    assert sentinel not in repr(outcome)


def test_secret_in_raw_response_is_rejected_before_base64_observation_write(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    sentinel = "RUNPOD-SECRET-SENTINEL-DO-NOT-PERSIST"
    transport = FakeTransport(
        _observation(
            json.dumps({"error": sentinel}, separators=(",", ":")).encode(
                "utf-8"
            ),
            status=400,
        )
    )

    outcome = _execute(
        configuration,
        transport,
        secret_guard=launcher.SecretGuard([sentinel]),
    )

    assert outcome.failure_code == "SECRET_TOKEN_DETECTED_IN_ARTIFACT"
    assert transport.create_calls == 1
    assert transport.list_calls == 0
    assert transport.stop_calls == 0
    observed = b"".join(
        path.read_bytes() for path in tmp_path.rglob("*.json") if path.is_file()
    )
    assert sentinel.encode("utf-8") not in observed
    assert not any(
        path.name.endswith(".create-observation.json")
        for path in tmp_path.rglob("*.json")
    )


def test_secret_bearing_201_is_contained_without_persisting_raw_body(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    sentinel = "RUNPOD-SECRET-SENTINEL-DO-NOT-PERSIST"
    response = _response()
    response["unexpectedSecretEcho"] = sentinel
    transport = FakeTransport(_observation(_raw_response(response)))

    outcome = _execute(
        configuration,
        transport,
        secret_guard=launcher.SecretGuard([sentinel]),
    )

    assert outcome.failure_code == "SECRET_TOKEN_DETECTED_IN_ARTIFACT"
    assert outcome.status == "FAILED_CLOSED_TERMINAL_CONFIRMED"
    assert transport.stop_calls == 1
    observed = b"".join(
        path.read_bytes() for path in tmp_path.rglob("*.json") if path.is_file()
    )
    assert sentinel.encode("utf-8") not in observed
    assert not any(
        path.name.endswith(".create-observation.json")
        for path in tmp_path.rglob("*.json")
    )


def test_raw_whitespace_change_changes_bound_response_hash(tmp_path: Path):
    first_config = _configuration(tmp_path / "first")
    second_config = _configuration(tmp_path / "second")
    value = _response()
    compact = json.dumps(value, separators=(",", ":")).encode("utf-8")
    spaced = json.dumps(value, indent=2).encode("utf-8")

    assert _execute(first_config, FakeTransport(_observation(compact))).status.endswith(
        "BOTH_GUARDIANS_ARMED"
    )
    assert _execute(second_config, FakeTransport(_observation(spaced))).status.endswith(
        "BOTH_GUARDIANS_ARMED"
    )
    first = launcher.strict_json_object(
        first_config.provider_receipt_path.read_bytes(), "first receipt"
    )
    second = launcher.strict_json_object(
        second_config.provider_receipt_path.read_bytes(), "second receipt"
    )
    assert first["create_transaction"]["response_body"] == second[
        "create_transaction"
    ]["response_body"]
    assert first["create_transaction"]["response_body_sha256"] != second[
        "create_transaction"
    ]["response_body_sha256"]


def test_cross_host_effective_url_and_nonidentity_encoding_fail_stop(
    tmp_path: Path,
):
    configuration = _configuration(tmp_path)
    transport = FakeTransport(
        _observation(
            _raw_response(_response()),
            url="https://attacker.invalid/v1/pods",
            content_encoding="gzip",
        )
    )

    outcome = _execute(configuration, transport)

    assert outcome.failure_code == "CREATE_EFFECTIVE_URL_MISMATCH"
    assert outcome.status == "FAILED_CLOSED_TERMINAL_CONFIRMED"
    assert transport.stop_calls == 1
