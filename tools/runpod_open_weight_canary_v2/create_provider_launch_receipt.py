"""Create-once RunPod launch transaction protocol.

The command-line live path is deliberately NO_GO until an external guardian can
durably arm exact-name reconciliation before the create request is sent.  The
library is fully injectable so its journal, raw HTTP evidence, recovery, STOP,
and arm ordering can be tested without a network or provider call.

Local self-hashes and guardian identity strings are integrity links, not
signatures, trusted timestamps, human authorization, or RunPod attestations.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import ssl
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Protocol, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = (
    REPOSITORY_ROOT
    / "noetic-compass-scaffold"
    / "noetic-compass"
    / "live-trace-worker"
    / "scripts"
    / "run_open_weight_trajectory_canary_v2.py"
)
WATCHDOG_PATH = Path(__file__).with_name("watchdog_armed.ps1")

API_HOST = "rest.runpod.io"
API_PORT = 443
CREATE_PATH = "/v1/pods"
CREATE_URL = "https://rest.runpod.io/v1/pods"
LIST_PATH = "/v1/pods"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_ELAPSED_MILLISECONDS = 120_000
HTTPS_TRANSPORT_TIMEOUT_SECONDS = 20
CLOCK_SKEW_ALLOWANCE_SECONDS = 10
PRE_SEND_SAFETY_MARGIN_SECONDS = (
    MAX_ELAPSED_MILLISECONDS // 1_000 + CLOCK_SKEW_ALLOWANCE_SECONDS
)
PROTECTED_POD_IDS = frozenset({"q2oqlooejhin7s", "hilj2rzs54gi06"})
DEFINITIVE_CREATE_REJECTION_STATUSES = frozenset({400})

AUTHORIZATION_SCHEMA = "cas_runpod_create_authorization.v1"
INTENT_SCHEMA = "cas_runpod_create_intent.v1"
GUARDIAN_SCHEMA = "cas_runpod_precreate_guardian_receipt.v1"
CONSUMPTION_SCHEMA = "cas_runpod_create_authorization_consumption.v1"
SEND_MARKER_SCHEMA = "cas_runpod_create_send_marker.v1"
OBSERVATION_SCHEMA = "cas_runpod_create_http_observation.v1"
PROVIDER_RECEIPT_SCHEMA = "cas_runpod_provider_launch_receipt.v2"
FAILURE_SCHEMA = "cas_runpod_provider_launch_failure.v1"

AUTHORIZATION_CLAIM = (
    "One-use operator intent artifact only. Its self-hash is not an identity "
    "signature, provider receipt, legal attestation, or substitute for the "
    "pre-create guardian."
)
INTENT_CLAIM = (
    "Durable create intent written before any provider request. It reserves one "
    "exact request/name window and never authorizes a retry."
)
GUARDIAN_CLAIM = (
    "Pre-create atomic authorization-consumption and recovery-arm evidence "
    "returned by an injected guardian. The local self-hash and guardian_id are "
    "not a signature; production use needs an independently running guardian "
    "that globally consumes this authorization and can reconcile this exact name."
)
PROVIDER_CLAIM = (
    "Locally captured exact RunPod request bytes, exact HTTP 201 response bytes, "
    "selected response metadata, and client timestamps. The receipt is not a "
    "RunPod signature, trusted timestamp, or billing settlement; it proves "
    "on-demand/unlocked only when the retained raw response strictly parses to "
    "the full retained object containing those false values, RUNNING, and "
    "lastStartedAt."
)
FAILURE_CLAIM = (
    "Local fail-closed transaction evidence. Provider observations are hashed "
    "but not authenticated; terminal state is claimed only after an exact-ID "
    "GET observes EXITED or TERMINATED."
)

_POD_ID = re.compile(r"^[a-z0-9]{6,32}$")
_POD_NAME = re.compile(
    r"^cas-open-weight-canary-v2-[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?$"
)
_HIGH_ENTROPY_POD_NAME = re.compile(
    r"^cas-open-weight-canary-v2-[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{32}$"
)
_SOURCE_COMMIT = re.compile(r"^[0-9a-f]{40,64}$")
_OCI_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_UPPER_SHA256 = re.compile(r"^[0-9A-F]{64}$")
_AUTHORIZATION_ID = re.compile(r"^[a-z0-9][a-z0-9-]{15,63}$")
_GUARDIAN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


class ProtocolFailure(RuntimeError):
    """A fixed-code error safe for operational artifacts and logs."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class AmbiguousCreateFailure(ProtocolFailure):
    """The create may have reached RunPod but no complete response was retained."""

    def __init__(
        self,
        code: str,
        *,
        known_http_status: int | None = None,
        effective_url: str | None = None,
    ):
        super().__init__(code)
        self.known_http_status = known_http_status
        self.effective_url = effective_url


@dataclass(frozen=True)
class HttpObservation:
    status: int
    body: bytes
    request_observed_at_utc: str
    response_observed_at_utc: str
    elapsed_milliseconds: int
    effective_url: str
    content_type: str | None = "application/json"
    content_encoding: str | None = None
    request_id: str | None = None


@dataclass(frozen=True)
class LaunchConfiguration:
    pod_name: str
    source_commit_sha256: str
    oci_image_digest: str
    image_name: str
    public_key: str
    authorization_path: Path
    expected_authorization_sha256: str
    state_directory: Path
    provider_receipt_path: Path
    failure_evidence_path: Path
    public_key_path: Path
    observed_hourly_rate: str = "0.44"
    maximum_wall_seconds: int = 1800
    maximum_spend_usd: str = "0.50"


@dataclass(frozen=True)
class ArmContext:
    authorization_id: str
    pod_id: str
    pod_name: str
    provider_started_at_utc: str
    hard_stop_deadline_utc: str
    source_commit_sha256: str
    oci_image_digest: str
    image_name: str
    provider_receipt_path: Path
    provider_receipt_sha256: str


@dataclass(frozen=True)
class LaunchOutcome:
    status: str
    failure_code: str | None
    pod_id: str | None
    stop_status: str | None
    provider_receipt_path: str | None
    failure_evidence_path: str | None


class RunPodTransport(Protocol):
    def create_pod(self, request_body: bytes) -> HttpObservation: ...

    def list_pods(self) -> HttpObservation: ...

    def get_pod(self, pod_id: str) -> HttpObservation: ...

    def stop_pod(self, pod_id: str) -> HttpObservation: ...


class PrecreateGuardian(Protocol):
    def consume_authorization_and_arm_precreate(
        self, intent: Mapping[str, object]
    ) -> bytes: ...

    def bind_exact_pod(self, context: ArmContext) -> None: ...


class LocalArmAdapter(Protocol):
    def arm(self, context: ArmContext) -> None: ...


class ReceiptContractValidator(Protocol):
    def validate(
        self,
        receipt_path: Path,
        receipt_raw: bytes,
        configuration: LaunchConfiguration,
    ) -> None: ...


class ArtifactWriter(Protocol):
    def create_new(self, path: Path, raw: bytes) -> None: ...


class SecretGuard:
    """Checks artifact bytes without exposing secret values through repr/errors."""

    def __init__(self, values: Sequence[str | bytes] = ()):
        tokens: list[bytes] = []
        for value in values:
            raw = value if isinstance(value, bytes) else value.encode("utf-8")
            if raw:
                tokens.append(raw)
        self._tokens = tuple(tokens)

    def __repr__(self) -> str:
        return "SecretGuard(<redacted>)"

    def assert_safe(self, raw: bytes) -> None:
        if any(token in raw for token in self._tokens):
            raise ProtocolFailure("SECRET_TOKEN_DETECTED_IN_ARTIFACT")


class DurableCreateNewWriter:
    """Durably publish exact bytes without replacing an existing path."""

    def create_new(self, path: Path, raw: bytes) -> None:
        parent = path.parent.resolve(strict=True)
        if not parent.is_dir() or path.is_symlink():
            raise ProtocolFailure("ARTIFACT_PARENT_OR_TARGET_INVALID")
        temporary = parent / f".{path.name}.{secrets.token_hex(16)}.tmp"
        descriptor: int | None = None
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_BINARY", 0),
                0o600,
            )
            view = memoryview(raw)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("short write")
                view = view[written:]
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            os.link(temporary, path)
            with path.open("rb", buffering=0) as published:
                observed = published.read(len(raw) + 1)
            if observed != raw:
                raise ProtocolFailure("PUBLISHED_ARTIFACT_BYTE_MISMATCH")
            if hasattr(os, "O_DIRECTORY"):
                directory_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
        except FileExistsError as exc:
            raise ProtocolFailure("CREATE_NEW_ARTIFACT_ALREADY_EXISTS") from exc
        except ProtocolFailure:
            raise
        except Exception as exc:
            raise ProtocolFailure("CREATE_NEW_ARTIFACT_WRITE_FAILED") from exc
        finally:
            if descriptor is not None:
                os.close(descriptor)
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


class RunPodHttpsTransport:
    """Hard-coded, non-redirecting RunPod REST transport.

    The CLI does not construct this class while the pre-create guardian is
    unavailable.  It exists for a future production adapter and for review of
    the exact origin/method/body boundary.
    """

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: int = HTTPS_TRANSPORT_TIMEOUT_SECONDS,
        clock: Callable[[], datetime] | None = None,
        monotonic_ns: Callable[[], int] | None = None,
    ):
        if not api_key or "\r" in api_key or "\n" in api_key:
            raise ProtocolFailure("RUNPOD_API_KEY_INVALID")
        if (
            type(timeout_seconds) is not int
            or timeout_seconds < 1
            or timeout_seconds > HTTPS_TRANSPORT_TIMEOUT_SECONDS
        ):
            raise ProtocolFailure("RUNPOD_HTTP_TIMEOUT_INVALID")
        self._authorization = f"Bearer {api_key}"
        self._timeout_seconds = timeout_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._monotonic_ns = monotonic_ns or time.monotonic_ns
        self._create_called = False
        self._tls_context = ssl.create_default_context()
        self._tls_context.check_hostname = True
        self._tls_context.verify_mode = ssl.CERT_REQUIRED

    def __repr__(self) -> str:
        return "RunPodHttpsTransport(<credentials redacted>)"

    def create_pod(self, request_body: bytes) -> HttpObservation:
        if self._create_called:
            raise ProtocolFailure("SECOND_CREATE_ATTEMPT_FORBIDDEN")
        self._create_called = True
        return self._request("POST", CREATE_PATH, request_body)

    def list_pods(self) -> HttpObservation:
        return self._request("GET", LIST_PATH, None)

    def get_pod(self, pod_id: str) -> HttpObservation:
        _require_pod_id(pod_id)
        return self._request("GET", f"/v1/pods/{pod_id}", None)

    def stop_pod(self, pod_id: str) -> HttpObservation:
        _require_pod_id(pod_id)
        return self._request("POST", f"/v1/pods/{pod_id}/stop", b"")

    def _request(
        self, method: str, path: str, body: bytes | None
    ) -> HttpObservation:
        if not path.startswith("/v1/pods") or "?" in path or "#" in path:
            raise ProtocolFailure("RUNPOD_REQUEST_TARGET_FORBIDDEN")
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Authorization": self._authorization,
            "Host": API_HOST,
            "User-Agent": "cas-runpod-create-once/2.0",
        }
        if method == "POST":
            headers["Content-Type"] = "application/json"
        requested = self._clock()
        started_ns = self._monotonic_ns()
        connection = http.client.HTTPSConnection(
            API_HOST,
            API_PORT,
            timeout=self._timeout_seconds,
            context=self._tls_context,
        )
        response_status: int | None = None
        effective_url = f"https://{API_HOST}{path}"
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            response_status = int(response.status)
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            responded = self._clock()
            ended_ns = self._monotonic_ns()
            if len(raw) > MAX_RESPONSE_BYTES:
                raise AmbiguousCreateFailure(
                    "RUNPOD_RESPONSE_BODY_TOO_LARGE",
                    known_http_status=response_status,
                    effective_url=effective_url,
                )
            return HttpObservation(
                status=response_status,
                body=raw,
                request_observed_at_utc=_format_utc(requested),
                response_observed_at_utc=_format_utc(responded),
                elapsed_milliseconds=max(0, (ended_ns - started_ns) // 1_000_000),
                effective_url=effective_url,
                content_type=_bounded_header(response.getheader("Content-Type")),
                content_encoding=_bounded_header(
                    response.getheader("Content-Encoding")
                ),
                request_id=_bounded_header(response.getheader("X-Request-Id")),
            )
        except ProtocolFailure:
            raise
        except Exception as exc:
            if method == "POST" and path == CREATE_PATH:
                raise AmbiguousCreateFailure(
                    "RUNPOD_CREATE_EXCHANGE_AMBIGUOUS",
                    known_http_status=response_status,
                    effective_url=effective_url if response_status is not None else None,
                ) from exc
            raise ProtocolFailure("RUNPOD_RECOVERY_EXCHANGE_FAILED") from exc
        finally:
            connection.close()


class RunnerAndWatchdogValidator:
    """Validate a written v2 receipt with both frozen consumer contracts."""

    def __init__(self, runner_path: Path = RUNNER_PATH, watchdog_path: Path = WATCHDOG_PATH):
        self._runner_path = runner_path
        self._watchdog_path = watchdog_path

    def validate(
        self,
        receipt_path: Path,
        receipt_raw: bytes,
        configuration: LaunchConfiguration,
    ) -> None:
        module_name = f"cas_provider_receipt_validator_{secrets.token_hex(8)}"
        spec = importlib.util.spec_from_file_location(module_name, self._runner_path)
        if spec is None or spec.loader is None:
            raise ProtocolFailure("RUNNER_RECEIPT_VALIDATOR_UNAVAILABLE")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
            module._validate_provider_launch_receipt(
                receipt_raw,
                source_commit_sha256=configuration.source_commit_sha256,
                oci_image_digest=configuration.oci_image_digest,
                expected_image_name=configuration.image_name,
                require_current_time=True,
            )
        except Exception as exc:
            raise ProtocolFailure("RUNNER_PROVIDER_RECEIPT_VALIDATION_FAILED") from exc
        finally:
            sys.modules.pop(module_name, None)

        executable = shutil.which("pwsh")
        if executable is None and os.name == "nt":
            candidate = Path(
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            )
            if candidate.is_file():
                executable = str(candidate)
        if executable is None:
            raise ProtocolFailure("POWERSHELL_RECEIPT_VALIDATOR_UNAVAILABLE")
        value = strict_json_object(receipt_raw, "provider receipt")
        completed = subprocess.run(
            [
                executable,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self._watchdog_path),
                "-ValidateProviderLaunchReceiptOnly",
                "-PodId",
                str(value["pod_id"]),
                "-PodName",
                str(value["pod_name"]),
                "-RunStartedAtUtc",
                str(value["provider_started_at_utc"]),
                "-HardStopDeadlineUtc",
                str(value["hard_stop_deadline_utc"]),
                "-SourceCommitSha256",
                configuration.source_commit_sha256,
                "-OciImageDigest",
                configuration.oci_image_digest,
                "-ExpectedImageName",
                configuration.image_name,
                "-ObservedHourlyRate",
                configuration.observed_hourly_rate,
                "-ReceiptDirectory",
                str(configuration.state_directory / "watchdog-validation-unused"),
                "-ProviderLaunchReceiptPath",
                str(receipt_path),
                "-ExpectedPublicKeyPath",
                str(configuration.public_key_path),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=45,
        )
        if completed.returncode != 0:
            raise ProtocolFailure("WATCHDOG_PROVIDER_RECEIPT_VALIDATION_FAILED")


def build_create_request(configuration: LaunchConfiguration) -> dict[str, object]:
    _validate_configuration_literals(configuration)
    return {
        "cloudType": "SECURE",
        "containerDiskInGb": 50,
        "env": {"PUBLIC_KEY": configuration.public_key},
        "gpuCount": 1,
        "gpuTypeIds": ["NVIDIA A40"],
        "imageName": configuration.image_name,
        "interruptible": False,
        "locked": False,
        "name": configuration.pod_name,
        "networkVolumeId": None,
        "ports": ["22/tcp"],
        # The current public create-body field list does not document this key.
        # It remains mandatory and is never omitted/retried; an unknown-field
        # 400 is a fail-closed schema-rollout result.
        "volumeEncrypted": True,
        "volumeInGb": 20,
        "volumeMountPath": "/workspace",
    }


def execute_create_once(
    configuration: LaunchConfiguration,
    *,
    transport: RunPodTransport,
    guardian: PrecreateGuardian,
    local_arm: LocalArmAdapter,
    validator: ReceiptContractValidator,
    secret_guard: SecretGuard,
    writer: ArtifactWriter | None = None,
    clock: Callable[[], datetime] | None = None,
    sleeper: Callable[[float], None] | None = None,
    terminal_poll_limit: int = 4,
    stop_attempt_limit: int = 2,
) -> LaunchOutcome:
    """Execute one authorized create transaction or fail-stop its exact Pod.

    All provider and arm collaborators are injected.  The function never
    retries CREATE.  A preexisting consumption/send marker is a replay failure,
    not permission to resume the create path.
    """

    artifact_writer = writer or DurableCreateNewWriter()
    guard = secret_guard
    now = clock or (lambda: datetime.now(timezone.utc))
    wait = sleeper or time.sleep
    events: list[dict[str, object]] = []
    pod_id: str | None = None
    pre_arm_pod_ids: set[str] = set()
    non_actionable_observed_pod_id_sha256: str | None = None
    create_sent = False
    ambiguous_create = False
    definitive_non_201 = False
    create_http_status_observed: int | None = None
    create_response_capture_status: str | None = None
    identity_provenance: str | None = None
    intent: dict[str, object] | None = None
    authorization_id: str | None = None
    intent_sha256: str | None = None
    guardian_receipt_sha256: str | None = None
    send_marker_sha256: str | None = None
    observation_sha256: str | None = None
    provider_receipt_written_this_invocation = False
    failure_code = "UNEXPECTED_INTERNAL_FAILURE"

    try:
        request = build_create_request(configuration)
        request_raw = canonical_json_bytes(request)
        guard.assert_safe(request_raw)
        request_sha = sha256_bytes(request_raw)
        authorization = _load_authorization(
            configuration, request_sha=request_sha, now=now()
        )
        authorization_id = str(authorization["authorization_id"])
        paths = _transaction_paths(configuration.state_directory, authorization_id)
        _assert_new_transaction_targets(configuration, paths)

        consumption = _self_hashed(
            {
                "authorization_id": authorization_id,
                "authorization_sha256": configuration.expected_authorization_sha256,
                "consumed_at_utc": _format_utc(now()),
                "schema_version": CONSUMPTION_SCHEMA,
                "status": "CONSUMED_FOR_EXACTLY_ONE_CREATE_ATTEMPT",
            },
            "consumption_sha256",
        )
        _write_artifact(artifact_writer, guard, paths["consumption"], consumption)

        window_start = now()
        window_end = window_start + timedelta(minutes=5)
        intent = _self_hashed(
            {
                "authorization_id": authorization_id,
                "authorization_sha256": configuration.expected_authorization_sha256,
                "claim_boundary": INTENT_CLAIM,
                "creation_window_end_utc": _format_utc(window_end),
                "creation_window_start_utc": _format_utc(window_start),
                "maximum_hard_stop_deadline_utc": _format_utc(
                    window_start
                    + timedelta(seconds=configuration.maximum_wall_seconds)
                ),
                "oci_image_digest": configuration.oci_image_digest,
                "pod_name": configuration.pod_name,
                "prepared_at_utc": _format_utc(now()),
                "request_body_base64": base64.b64encode(request_raw).decode("ascii"),
                "request_body_byte_count": len(request_raw),
                "request_body_sha256": request_sha,
                "schema_version": INTENT_SCHEMA,
                "source_commit_sha256": configuration.source_commit_sha256,
                "status": "PREPARED_CREATE_NOT_SENT",
            },
            "intent_sha256",
        )
        _write_artifact(artifact_writer, guard, paths["intent"], intent)
        intent_sha256 = str(intent["intent_sha256"])

        guardian_raw = guardian.consume_authorization_and_arm_precreate(intent)
        guardian_receipt = _validate_guardian_receipt(guardian_raw, intent)
        pre_arm_pod_ids = {
            str(row["id"])
            for row in guardian_receipt["pre_arm_inventory_projection"]
        }
        guard.assert_safe(guardian_raw)
        artifact_writer.create_new(paths["guardian"], guardian_raw)
        guardian_receipt_sha256 = sha256_bytes(guardian_raw)

        send_reserved_at = now()
        _validate_pre_send_freshness(
            authorization=authorization,
            intent=intent,
            guardian_receipt=guardian_receipt,
            observed_now=send_reserved_at,
        )
        send_marker = _self_hashed(
            {
                "authorization_id": authorization_id,
                "intent_sha256": intent["intent_sha256"],
                "request_body_sha256": request_sha,
                "schema_version": SEND_MARKER_SCHEMA,
                "status": "CREATE_SEND_ATTEMPT_RESERVED_NO_RETRY",
                "written_at_utc": _format_utc(send_reserved_at),
            },
            "send_marker_sha256",
        )
        _write_artifact(artifact_writer, guard, paths["send"], send_marker)
        send_marker_sha256 = str(send_marker["send_marker_sha256"])
        create_sent = True

        try:
            observation = transport.create_pod(request_raw)
        except AmbiguousCreateFailure as exc:
            create_http_status_observed = exc.known_http_status
            create_response_capture_status = (
                "HTTP_STATUS_ONLY_BODY_CAPTURE_INCOMPLETE"
                if exc.known_http_status is not None
                else "NO_HTTP_STATUS_BODY_CAPTURE_INCOMPLETE"
            )
            if (
                exc.known_http_status in DEFINITIVE_CREATE_REJECTION_STATUSES
                and exc.effective_url == CREATE_URL
            ):
                definitive_non_201 = True
                ambiguous_create = False
            else:
                ambiguous_create = True
            raise
        create_http_status_observed = observation.status
        create_response_capture_status = "COMPLETE_BODY_CAPTURED_NOT_RETAINED"
        if observation.status == 201:
            # Until a strict 201 object yields its exact ID, an incomplete 201
            # remains possibly committed and is eligible for guardian-bound
            # exact-name inventory reconciliation.
            ambiguous_create = True
            candidate_id = _salvage_unique_pod_id(observation.body)
            if candidate_id is not None and (
                candidate_id in pre_arm_pod_ids or candidate_id in PROTECTED_POD_IDS
            ):
                non_actionable_observed_pod_id_sha256 = sha256_bytes(
                    candidate_id.encode("utf-8")
                )
                identity_provenance = "PREEXISTING_OR_PROTECTED_ID_NON_ACTIONABLE"
            else:
                pod_id = candidate_id
            if pod_id is not None:
                identity_provenance = "WEAK_201_SALVAGE"
        elif observation.status in DEFINITIVE_CREATE_REJECTION_STATUSES:
            # A completed non-201 response is a definitive create rejection for
            # this explicit status whitelist. Never infer ownership from its
            # error body and never scan inventory/STOP an older exact-name row.
            definitive_non_201 = True
        else:
            # Unexpected success, redirect, timeout-like 408, and server errors
            # are possibly committed. CREATE is still never retried; use only
            # a unique weak ID plus exact-name GET or guardian name/window scan.
            ambiguous_create = True
            candidate_id = _salvage_unique_pod_id(observation.body)
            if candidate_id is not None and (
                candidate_id in pre_arm_pod_ids or candidate_id in PROTECTED_POD_IDS
            ):
                non_actionable_observed_pod_id_sha256 = sha256_bytes(
                    candidate_id.encode("utf-8")
                )
                identity_provenance = "PREEXISTING_OR_PROTECTED_ID_NON_ACTIONABLE"
            else:
                pod_id = candidate_id
            if pod_id is not None:
                identity_provenance = "WEAK_NON_201_SALVAGE"
        # Inspect identity/status in memory first so a secret-bearing 201 can
        # still be contained, but reject the raw bytes before any reversible
        # base64 observation or other artifact is written.
        guard.assert_safe(observation.body)
        observation_document = _build_observation_document(
            authorization_id=authorization_id,
            intent_sha256=str(intent["intent_sha256"]),
            request_raw=request_raw,
            observation=observation,
        )
        _write_artifact(
            artifact_writer, guard, paths["observation"], observation_document
        )
        create_response_capture_status = "COMPLETE_EXACT_BODY_RETAINED"
        observation_sha256 = str(observation_document["observation_sha256"])
        response = _validate_create_observation(observation)
        response_id = _required_text(response, "id")
        _require_pod_id(response_id)
        if response_id in pre_arm_pod_ids:
            pod_id = None
            non_actionable_observed_pod_id_sha256 = sha256_bytes(
                response_id.encode("utf-8")
            )
            identity_provenance = "STRICT_201_PREARM_ID_COLLISION_NON_ACTIONABLE"
            ambiguous_create = True
            raise ProtocolFailure("STRICT_201_ID_PREEXISTED_PREARM")
        if response_id in PROTECTED_POD_IDS:
            pod_id = None
            non_actionable_observed_pod_id_sha256 = sha256_bytes(
                response_id.encode("utf-8")
            )
            identity_provenance = "STRICT_201_PROTECTED_ID_NON_ACTIONABLE"
            ambiguous_create = True
            raise ProtocolFailure("PROTECTED_POD_ID_RETURNED_BY_CREATE")
        pod_id = response_id
        identity_provenance = "STRICT_HTTP_201"
        ambiguous_create = False
        if _required_text(response, "name") != configuration.pod_name:
            raise ProtocolFailure("CREATE_RESPONSE_POD_NAME_MISMATCH")

        receipt = _build_provider_receipt(
            configuration=configuration,
            authorization_id=authorization_id,
            authorization_sha256=configuration.expected_authorization_sha256,
            intent_sha256=str(intent["intent_sha256"]),
            precreate_guardian_receipt_sha256=guardian_receipt_sha256,
            send_marker_sha256=send_marker_sha256,
            send_reserved_at_utc=str(send_marker["written_at_utc"]),
            precreate_maximum_deadline_utc=str(
                intent["maximum_hard_stop_deadline_utc"]
            ),
            request=request,
            request_raw=request_raw,
            response=response,
            observation=observation,
        )
        receipt_raw = canonical_json_bytes(receipt)
        guard.assert_safe(receipt_raw)
        artifact_writer.create_new(configuration.provider_receipt_path, receipt_raw)
        provider_receipt_written_this_invocation = True
        validator.validate(
            configuration.provider_receipt_path, receipt_raw, configuration
        )

        context = ArmContext(
            authorization_id=authorization_id,
            pod_id=pod_id,
            pod_name=configuration.pod_name,
            provider_started_at_utc=str(receipt["provider_started_at_utc"]),
            hard_stop_deadline_utc=str(receipt["hard_stop_deadline_utc"]),
            source_commit_sha256=configuration.source_commit_sha256,
            oci_image_digest=configuration.oci_image_digest,
            image_name=configuration.image_name,
            provider_receipt_path=configuration.provider_receipt_path,
            provider_receipt_sha256=sha256_bytes(receipt_raw),
        )
        # The pre-create external guardian becomes the exact-ID GitHub authority
        # first.  Only after that succeeds may the local watchdog arm.
        guardian.bind_exact_pod(context)
        local_arm.arm(context)
        return LaunchOutcome(
            status="CREATE_RECEIPT_VALIDATED_AND_BOTH_GUARDIANS_ARMED",
            failure_code=None,
            pod_id=pod_id,
            stop_status=None,
            provider_receipt_path=str(configuration.provider_receipt_path),
            failure_evidence_path=None,
        )
    except ProtocolFailure as exc:
        failure_code = exc.code
    except Exception:
        failure_code = "UNEXPECTED_INTERNAL_FAILURE"

    stop_status: str | None = None
    if create_sent:
        if pod_id is None and ambiguous_create and intent is not None:
            pod_id = _reconcile_unique_created_pod(
                transport,
                intent=intent,
                pre_arm_pod_ids=pre_arm_pod_ids,
                events=events,
            )
            if pod_id is not None:
                identity_provenance = "GUARDIAN_NAME_WINDOW_INVENTORY"
        if pod_id is not None:
            stop_status = _stop_and_reconcile(
                transport,
                pod_id=pod_id,
                expected_name=(
                    None
                    if identity_provenance
                    in {"STRICT_HTTP_201", "GUARDIAN_NAME_WINDOW_INVENTORY"}
                    else configuration.pod_name
                ),
                events=events,
                sleeper=wait,
                terminal_poll_limit=terminal_poll_limit,
                stop_attempt_limit=stop_attempt_limit,
            )
        elif definitive_non_201:
            stop_status = "DEFINITIVE_NON_201_NO_STOP_REQUIRED"
        else:
            stop_status = "EXACT_ID_UNAVAILABLE_OPERATOR_INTERVENTION_REQUIRED"

    if not create_sent:
        status = "FAILED_BEFORE_CREATE_NO_PROVIDER_MUTATION"
    elif stop_status == "TERMINAL_CONFIRMED":
        status = "FAILED_CLOSED_TERMINAL_CONFIRMED"
    elif stop_status == "DEFINITIVE_NON_201_NO_STOP_REQUIRED":
        status = "FAILED_DEFINITIVE_CREATE_REJECTED_NO_POD_MUTATION"
    else:
        status = "FAILED_OPERATOR_INTERVENTION_REQUIRED"

    failure = _self_hashed(
        {
            "ambiguity_class": (
                "NO_CREATE_SENT"
                if not create_sent
                else "DEFINITIVE_HTTP_400"
                if definitive_non_201
                else "POSSIBLY_COMMITTED"
                if ambiguous_create
                else "EXACT_201_ID_OBSERVED"
            ),
            "authorization_id": authorization_id,
            "authorization_sha256": (
                configuration.expected_authorization_sha256
                if authorization_id is not None
                else None
            ),
            "claim_boundary": FAILURE_CLAIM,
            "create_intent_sha256": intent_sha256,
            "create_http_status_observed": create_http_status_observed,
            "create_observation_sha256": observation_sha256,
            "create_response_capture_status": create_response_capture_status,
            "create_send_marker_sha256": send_marker_sha256,
            "events": events,
            "failure_code": failure_code,
            "identity_provenance": identity_provenance,
            "non_actionable_observed_pod_id_sha256": (
                non_actionable_observed_pod_id_sha256
            ),
            "pod_id": pod_id,
            "pod_name": configuration.pod_name,
            "precreate_guardian_receipt_sha256": guardian_receipt_sha256,
            "provider": "RUNPOD",
            "provider_receipt_written_this_invocation": (
                provider_receipt_written_this_invocation
            ),
            "schema_version": FAILURE_SCHEMA,
            "status": status,
            "stop_status": stop_status,
            "written_at_utc": _format_utc(now()),
        },
        "failure_evidence_sha256",
    )
    try:
        _write_artifact(
            artifact_writer, guard, configuration.failure_evidence_path, failure
        )
        failure_path: str | None = str(configuration.failure_evidence_path)
    except Exception:
        failure_path = None
        if status != "FAILED_BEFORE_CREATE_NO_PROVIDER_MUTATION":
            status = "FAILED_OPERATOR_INTERVENTION_REQUIRED"
    return LaunchOutcome(
        status=status,
        failure_code=failure_code,
        pod_id=pod_id,
        stop_status=stop_status,
        provider_receipt_path=(
            str(configuration.provider_receipt_path)
            if provider_receipt_written_this_invocation
            else None
        ),
        failure_evidence_path=failure_path,
    )


def _validate_configuration_literals(configuration: LaunchConfiguration) -> None:
    if not _POD_NAME.fullmatch(configuration.pod_name):
        raise ProtocolFailure("POD_NAME_INVALID")
    if not _HIGH_ENTROPY_POD_NAME.fullmatch(configuration.pod_name):
        raise ProtocolFailure("POD_NAME_HIGH_ENTROPY_SUFFIX_REQUIRED")
    if not _SOURCE_COMMIT.fullmatch(configuration.source_commit_sha256):
        raise ProtocolFailure("SOURCE_COMMIT_INVALID")
    if not _OCI_DIGEST.fullmatch(configuration.oci_image_digest):
        raise ProtocolFailure("OCI_DIGEST_INVALID")
    if configuration.image_name != "runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404":
        raise ProtocolFailure("IMAGE_NAME_INVALID")
    if (
        type(configuration.maximum_wall_seconds) is not int
        or configuration.maximum_wall_seconds != 1800
    ):
        raise ProtocolFailure("MAXIMUM_WALL_SECONDS_INVALID")
    if configuration.maximum_spend_usd != "0.50":
        raise ProtocolFailure("MAXIMUM_SPEND_INVALID")
    if not configuration.public_key.startswith("ssh-ed25519 "):
        raise ProtocolFailure("DEDICATED_PUBLIC_KEY_INVALID")
    if "\r" in configuration.public_key or "\n" in configuration.public_key:
        raise ProtocolFailure("DEDICATED_PUBLIC_KEY_INVALID")


def _load_authorization(
    configuration: LaunchConfiguration,
    *,
    request_sha: str,
    now: datetime,
) -> dict[str, object]:
    raw = configuration.authorization_path.read_bytes()
    if sha256_bytes(raw) != configuration.expected_authorization_sha256:
        raise ProtocolFailure("AUTHORIZATION_EXTERNAL_HASH_MISMATCH")
    value = strict_json_object(raw, "authorization")
    if raw != canonical_json_bytes(value):
        raise ProtocolFailure("AUTHORIZATION_NOT_CANONICAL")
    required = {
        "authorization_id",
        "authorization_sha256",
        "claim_boundary",
        "expires_at_utc",
        "issued_at_utc",
        "maximum_spend_usd",
        "maximum_wall_seconds",
        "oci_image_digest",
        "one_use",
        "operation",
        "pod_name",
        "provider",
        "request_body_sha256",
        "schema_version",
        "source_commit_sha256",
        "status",
    }
    if set(value) != required:
        raise ProtocolFailure("AUTHORIZATION_KEYSET_MISMATCH")
    unsigned = dict(value)
    supplied_self_hash = unsigned.pop("authorization_sha256")
    if supplied_self_hash != sha256_bytes(canonical_json_bytes(unsigned)):
        raise ProtocolFailure("AUTHORIZATION_SELF_HASH_MISMATCH")
    authorization_id = value.get("authorization_id")
    if not isinstance(authorization_id, str) or not _AUTHORIZATION_ID.fullmatch(
        authorization_id
    ):
        raise ProtocolFailure("AUTHORIZATION_ID_INVALID")
    expected_literals = {
        "claim_boundary": AUTHORIZATION_CLAIM,
        "maximum_spend_usd": configuration.maximum_spend_usd,
        "maximum_wall_seconds": 1800,
        "oci_image_digest": configuration.oci_image_digest,
        "one_use": True,
        "operation": "CREATE_EXACTLY_ONE_NEW_RUNPOD_POD",
        "pod_name": configuration.pod_name,
        "provider": "RUNPOD",
        "request_body_sha256": request_sha,
        "schema_version": AUTHORIZATION_SCHEMA,
        "source_commit_sha256": configuration.source_commit_sha256,
        "status": "AUTHORIZED_FOR_ONE_NEW_RUNPOD_CANARY",
    }
    for key, expected in expected_literals.items():
        observed = value.get(key)
        if isinstance(expected, bool):
            matches = observed is expected
        elif isinstance(expected, int):
            matches = type(observed) is int and observed == expected
        else:
            matches = observed == expected
        if not matches:
            raise ProtocolFailure("AUTHORIZATION_BINDING_MISMATCH")
    issued = parse_utc(_required_text(value, "issued_at_utc"))
    expires = parse_utc(_required_text(value, "expires_at_utc"))
    if expires <= issued or expires - issued > timedelta(minutes=15):
        raise ProtocolFailure("AUTHORIZATION_WINDOW_INVALID")
    if now < issued or now > expires:
        raise ProtocolFailure("AUTHORIZATION_NOT_CURRENT")
    return value


def _transaction_paths(root: Path, authorization_id: str) -> dict[str, Path]:
    return {
        "consumption": root / f"{authorization_id}.authorization-consumed.json",
        "intent": root / f"{authorization_id}.prepared-intent.json",
        "guardian": root / f"{authorization_id}.precreate-guardian.json",
        "send": root / f"{authorization_id}.send-attempted.json",
        "observation": root / f"{authorization_id}.create-observation.json",
    }


def _assert_new_transaction_targets(
    configuration: LaunchConfiguration, paths: Mapping[str, Path]
) -> None:
    state = configuration.state_directory.resolve(strict=True)
    if not state.is_dir() or configuration.state_directory.is_symlink():
        raise ProtocolFailure("STATE_DIRECTORY_INVALID")
    targets = [
        *paths.values(),
        configuration.provider_receipt_path,
        configuration.failure_evidence_path,
    ]
    if any(path.exists() or path.is_symlink() for path in targets):
        raise ProtocolFailure("CREATE_TRANSACTION_OR_OUTPUT_ALREADY_EXISTS")


def _validate_guardian_receipt(
    raw: bytes, intent: Mapping[str, object]
) -> dict[str, object]:
    value = strict_json_object(raw, "precreate guardian receipt")
    if raw != canonical_json_bytes(value):
        raise ProtocolFailure("PRECREATE_GUARDIAN_RECEIPT_NOT_CANONICAL")
    required = {
        "authorization_id",
        "authorization_consumption_key",
        "claim_boundary",
        "consumed_at_utc",
        "creation_window_end_utc",
        "creation_window_start_utc",
        "guardian_id",
        "guardian_consumption_generation",
        "guardian_receipt_sha256",
        "intent_sha256",
        "maximum_hard_stop_deadline_utc",
        "oci_image_digest",
        "pod_name",
        "pre_arm_inventory_count",
        "pre_arm_inventory_observed_at_utc",
        "pre_arm_inventory_projection",
        "pre_arm_inventory_sha256",
        "provider_endpoint",
        "request_body_sha256",
        "schema_version",
        "source_commit_sha256",
        "status",
    }
    if set(value) != required:
        raise ProtocolFailure("PRECREATE_GUARDIAN_RECEIPT_KEYSET_MISMATCH")
    unsigned = dict(value)
    supplied = unsigned.pop("guardian_receipt_sha256")
    if supplied != sha256_bytes(canonical_json_bytes(unsigned)):
        raise ProtocolFailure("PRECREATE_GUARDIAN_RECEIPT_SELF_HASH_MISMATCH")
    guardian_id = value.get("guardian_id")
    if not isinstance(guardian_id, str) or not _GUARDIAN_ID.fullmatch(guardian_id):
        raise ProtocolFailure("PRECREATE_GUARDIAN_ID_INVALID")
    expected_consumption_key = sha256_bytes(
        (
            str(intent["authorization_id"])
            + "\n"
            + str(intent["request_body_sha256"])
        ).encode("utf-8")
    )
    consumed_at = parse_utc(_required_text(value, "consumed_at_utc"))
    if consumed_at < parse_utc(str(intent["creation_window_start_utc"])) or (
        consumed_at > parse_utc(str(intent["creation_window_end_utc"]))
    ):
        raise ProtocolFailure("PRECREATE_GUARDIAN_CONSUMPTION_TIME_INVALID")
    inventory_observed = parse_utc(
        _required_text(value, "pre_arm_inventory_observed_at_utc")
    )
    if inventory_observed < parse_utc(str(intent["creation_window_start_utc"])) or (
        inventory_observed > parse_utc(str(intent["creation_window_end_utc"]))
    ) or inventory_observed > consumed_at:
        raise ProtocolFailure("PRECREATE_GUARDIAN_INVENTORY_TIME_INVALID")
    projection = value.get("pre_arm_inventory_projection")
    if not isinstance(projection, list):
        raise ProtocolFailure("PRECREATE_GUARDIAN_INVENTORY_INVALID")
    seen_ids: set[str] = set()
    normalized_projection: list[dict[str, str]] = []
    for row in projection:
        if not isinstance(row, dict) or set(row) != {"id", "name"}:
            raise ProtocolFailure("PRECREATE_GUARDIAN_INVENTORY_INVALID")
        row_id = row.get("id")
        row_name = row.get("name")
        if (
            not isinstance(row_id, str)
            or not _POD_ID.fullmatch(row_id)
            or row_id in seen_ids
            or not isinstance(row_name, str)
            or not row_name
        ):
            raise ProtocolFailure("PRECREATE_GUARDIAN_INVENTORY_INVALID")
        if row_name == intent["pod_name"]:
            raise ProtocolFailure("PRECREATE_GUARDIAN_NAME_ALREADY_PRESENT")
        seen_ids.add(row_id)
        normalized_projection.append({"id": row_id, "name": row_name})
    if projection != sorted(normalized_projection, key=lambda row: (row["id"], row["name"])):
        raise ProtocolFailure("PRECREATE_GUARDIAN_INVENTORY_NOT_SORTED")
    inventory_count = value.get("pre_arm_inventory_count")
    if type(inventory_count) is not int or inventory_count != len(projection) or value.get(
        "pre_arm_inventory_sha256"
    ) != sha256_bytes(canonical_json_bytes(projection)):
        raise ProtocolFailure("PRECREATE_GUARDIAN_INVENTORY_HASH_MISMATCH")
    bindings = {
        "authorization_id": intent["authorization_id"],
        "authorization_consumption_key": expected_consumption_key,
        "claim_boundary": GUARDIAN_CLAIM,
        "creation_window_end_utc": intent["creation_window_end_utc"],
        "creation_window_start_utc": intent["creation_window_start_utc"],
        "intent_sha256": intent["intent_sha256"],
        "guardian_consumption_generation": 1,
        "maximum_hard_stop_deadline_utc": intent[
            "maximum_hard_stop_deadline_utc"
        ],
        "oci_image_digest": intent["oci_image_digest"],
        "pod_name": intent["pod_name"],
        "provider_endpoint": CREATE_URL,
        "request_body_sha256": intent["request_body_sha256"],
        "schema_version": GUARDIAN_SCHEMA,
        "source_commit_sha256": intent["source_commit_sha256"],
        "status": "ARMED_FOR_EXACT_NAME_RECONCILIATION",
    }
    if type(value.get("guardian_consumption_generation")) is not int:
        raise ProtocolFailure("PRECREATE_GUARDIAN_CONSUMPTION_GENERATION_INVALID")
    if any(value.get(key) != expected for key, expected in bindings.items()):
        raise ProtocolFailure("PRECREATE_GUARDIAN_RECEIPT_BINDING_MISMATCH")
    return value


def _validate_pre_send_freshness(
    *,
    authorization: Mapping[str, object],
    intent: Mapping[str, object],
    guardian_receipt: Mapping[str, object],
    observed_now: datetime,
) -> None:
    # Reserve the full receipt-contract exchange ceiling plus clock skew.  The
    # concrete HTTPS adapter times out sooner, but a future compliant adapter
    # may use the full 120-second maximum without crossing an authorization,
    # creation-window, or hard-stop boundary.
    safety_margin = timedelta(seconds=PRE_SEND_SAFETY_MARGIN_SECONDS)
    authorization_expires = parse_utc(
        _required_text(authorization, "expires_at_utc")
    )
    window_start = parse_utc(str(intent["creation_window_start_utc"]))
    window_end = parse_utc(str(intent["creation_window_end_utc"]))
    maximum_deadline = parse_utc(str(intent["maximum_hard_stop_deadline_utc"]))
    consumed_at = parse_utc(str(guardian_receipt["consumed_at_utc"]))
    inventory_at = parse_utc(
        str(guardian_receipt["pre_arm_inventory_observed_at_utc"])
    )
    if (
        observed_now < window_start
        or observed_now + safety_margin > window_end
        or observed_now + safety_margin > authorization_expires
        or maximum_deadline != window_start + timedelta(seconds=1800)
        or maximum_deadline <= observed_now + safety_margin
        or observed_now - consumed_at > timedelta(minutes=5)
        or observed_now - inventory_at > timedelta(minutes=5)
        or consumed_at > observed_now + timedelta(seconds=5)
        or inventory_at > observed_now + timedelta(seconds=5)
    ):
        raise ProtocolFailure("PRE_SEND_AUTHORIZATION_OR_GUARDIAN_WINDOW_STALE")


def build_guardian_receipt(
    intent: Mapping[str, object],
    *,
    guardian_id: str,
    pre_arm_inventory: Sequence[Mapping[str, str]] = (),
) -> bytes:
    """Test/adapter helper; the returned local self-hash is not authentication."""

    projection = sorted(
        ({"id": str(row["id"]), "name": str(row["name"])} for row in pre_arm_inventory),
        key=lambda row: (row["id"], row["name"]),
    )
    value = _self_hashed(
        {
            "authorization_id": intent["authorization_id"],
            "authorization_consumption_key": sha256_bytes(
                (
                    str(intent["authorization_id"])
                    + "\n"
                    + str(intent["request_body_sha256"])
                ).encode("utf-8")
            ),
            "claim_boundary": GUARDIAN_CLAIM,
            "consumed_at_utc": intent["prepared_at_utc"],
            "creation_window_end_utc": intent["creation_window_end_utc"],
            "creation_window_start_utc": intent["creation_window_start_utc"],
            "guardian_id": guardian_id,
            "guardian_consumption_generation": 1,
            "intent_sha256": intent["intent_sha256"],
            "maximum_hard_stop_deadline_utc": intent[
                "maximum_hard_stop_deadline_utc"
            ],
            "oci_image_digest": intent["oci_image_digest"],
            "pod_name": intent["pod_name"],
            "pre_arm_inventory_count": len(projection),
            "pre_arm_inventory_observed_at_utc": intent["prepared_at_utc"],
            "pre_arm_inventory_projection": projection,
            "pre_arm_inventory_sha256": sha256_bytes(
                canonical_json_bytes(projection)
            ),
            "provider_endpoint": CREATE_URL,
            "request_body_sha256": intent["request_body_sha256"],
            "schema_version": GUARDIAN_SCHEMA,
            "source_commit_sha256": intent["source_commit_sha256"],
            "status": "ARMED_FOR_EXACT_NAME_RECONCILIATION",
        },
        "guardian_receipt_sha256",
    )
    return canonical_json_bytes(value)


def _build_observation_document(
    *,
    authorization_id: str,
    intent_sha256: str,
    request_raw: bytes,
    observation: HttpObservation,
) -> dict[str, object]:
    return _self_hashed(
        {
            "authorization_id": authorization_id,
            "effective_url": observation.effective_url,
            "elapsed_milliseconds": observation.elapsed_milliseconds,
            "intent_sha256": intent_sha256,
            "request_body_sha256": sha256_bytes(request_raw),
            "request_observed_at_utc": observation.request_observed_at_utc,
            "response_body_base64": base64.b64encode(observation.body).decode(
                "ascii"
            ),
            "response_body_byte_count": len(observation.body),
            "response_body_sha256": sha256_bytes(observation.body),
            "response_content_encoding": observation.content_encoding,
            "response_content_type": observation.content_type,
            "response_http_status": observation.status,
            "response_observed_at_utc": observation.response_observed_at_utc,
            "response_request_id": observation.request_id,
            "schema_version": OBSERVATION_SCHEMA,
            "status": "EXACT_HTTP_ENTITY_BODY_RETAINED",
        },
        "observation_sha256",
    )


def _validate_create_observation(observation: HttpObservation) -> dict[str, object]:
    if observation.effective_url != CREATE_URL:
        raise ProtocolFailure("CREATE_EFFECTIVE_URL_MISMATCH")
    if type(observation.status) is not int or observation.status != 201:
        raise ProtocolFailure("CREATE_HTTP_STATUS_NOT_201")
    if len(observation.body) > MAX_RESPONSE_BYTES:
        raise ProtocolFailure("CREATE_RESPONSE_BODY_TOO_LARGE")
    if (
        type(observation.elapsed_milliseconds) is not int
        or
        observation.elapsed_milliseconds < 0
        or observation.elapsed_milliseconds > MAX_ELAPSED_MILLISECONDS
    ):
        raise ProtocolFailure("CREATE_ELAPSED_DURATION_INVALID")
    if observation.content_encoding is not None and (
        observation.content_encoding.strip().lower() != "identity"
    ):
        raise ProtocolFailure("CREATE_RESPONSE_CONTENT_ENCODING_FORBIDDEN")
    if (
        not isinstance(observation.content_type, str)
        or observation.content_type.split(";", 1)[0].strip().lower()
        != "application/json"
    ):
        raise ProtocolFailure("CREATE_RESPONSE_CONTENT_TYPE_INVALID")
    requested = parse_utc(observation.request_observed_at_utc)
    responded = parse_utc(observation.response_observed_at_utc)
    if responded < requested:
        raise ProtocolFailure("CREATE_RESPONSE_PREDATES_REQUEST")
    wall_elapsed = int((responded - requested).total_seconds() * 1000)
    if wall_elapsed > MAX_ELAPSED_MILLISECONDS or abs(
        wall_elapsed - observation.elapsed_milliseconds
    ) > 5_000:
        raise ProtocolFailure("CREATE_WALL_MONOTONIC_DURATION_MISMATCH")
    try:
        value = strict_json_object(observation.body, "RunPod create response")
    except Exception as exc:
        raise ProtocolFailure("CREATE_RESPONSE_STRICT_JSON_INVALID") from exc
    return value


def _build_provider_receipt(
    *,
    configuration: LaunchConfiguration,
    authorization_id: str,
    authorization_sha256: str,
    intent_sha256: str,
    precreate_guardian_receipt_sha256: str,
    send_marker_sha256: str,
    send_reserved_at_utc: str,
    precreate_maximum_deadline_utc: str,
    request: Mapping[str, object],
    request_raw: bytes,
    response: Mapping[str, object],
    observation: HttpObservation,
) -> dict[str, object]:
    pod_id = _required_text(response, "id")
    _require_pod_id(pod_id)
    if response.get("interruptible") is not False:
        raise ProtocolFailure("CREATE_RESPONSE_INTERRUPTIBLE_NOT_FALSE")
    if response.get("locked") is not False:
        raise ProtocolFailure("CREATE_RESPONSE_LOCKED_NOT_FALSE")
    if response.get("volumeEncrypted") is not True:
        raise ProtocolFailure("CREATE_RESPONSE_VOLUME_ENCRYPTED_NOT_TRUE")
    if response.get("desiredStatus") != "RUNNING":
        raise ProtocolFailure("CREATE_RESPONSE_NOT_RUNNING")
    started_text = _required_text(response, "lastStartedAt")
    started = parse_provider_utc(started_text)
    requested = parse_utc(observation.request_observed_at_utc)
    responded = parse_utc(observation.response_observed_at_utc)
    send_reserved = parse_utc(send_reserved_at_utc)
    if send_reserved > requested or requested - send_reserved > timedelta(seconds=30):
        raise ProtocolFailure("CREATE_SEND_RESERVATION_CHRONOLOGY_MISMATCH")
    if started < requested - timedelta(seconds=30) or started > responded + timedelta(
        seconds=30
    ):
        raise ProtocolFailure("CREATE_RESPONSE_START_OUTSIDE_EXCHANGE")
    provider_started = _format_utc(started)
    precreate_maximum_deadline = parse_utc(precreate_maximum_deadline_utc)
    deadline = _format_utc(
        min(started + timedelta(seconds=1800), precreate_maximum_deadline)
    )
    if parse_utc(deadline) <= started:
        raise ProtocolFailure("CREATE_HARD_STOP_DEADLINE_NOT_AFTER_START")
    transaction = {
        "effective_url": observation.effective_url,
        "elapsed_milliseconds": observation.elapsed_milliseconds,
        "request_accept_encoding": "identity",
        "request_body": dict(request),
        "request_body_base64": base64.b64encode(request_raw).decode("ascii"),
        "request_body_byte_count": len(request_raw),
        "request_body_sha256": sha256_bytes(request_raw),
        "request_content_type": "application/json",
        "request_method": "POST",
        "request_observed_at_utc": observation.request_observed_at_utc,
        "request_path": CREATE_PATH,
        "response_body": dict(response),
        "response_body_base64": base64.b64encode(observation.body).decode("ascii"),
        "response_body_byte_count": len(observation.body),
        "response_body_sha256": sha256_bytes(observation.body),
        "response_content_encoding": observation.content_encoding,
        "response_content_type": observation.content_type,
        "response_http_status": observation.status,
        "response_observed_at_utc": observation.response_observed_at_utc,
        "response_request_id": observation.request_id,
    }
    unsigned = {
        "authorization_id": authorization_id,
        "authorization_sha256": authorization_sha256,
        "claim_boundary": PROVIDER_CLAIM,
        "create_intent_sha256": intent_sha256,
        "create_send_marker_sha256": send_marker_sha256,
        "create_send_reserved_at_utc": send_reserved_at_utc,
        "create_transaction": transaction,
        "dedicated_public_key_sha256": sha256_bytes(
            configuration.public_key.encode("utf-8")
        ),
        "hard_stop_deadline_utc": deadline,
        "image_name": configuration.image_name,
        "launch_mode": "CREATE_RESPONSE_STARTED_POD",
        "oci_image_digest": configuration.oci_image_digest,
        "pod_id": pod_id,
        "pod_name": configuration.pod_name,
        "provider": "RUNPOD",
        "provider_started_at_utc": provider_started,
        "precreate_guardian_receipt_sha256": precreate_guardian_receipt_sha256,
        "precreate_maximum_hard_stop_deadline_utc": precreate_maximum_deadline_utc,
        "schema_version": PROVIDER_RECEIPT_SCHEMA,
        "source_commit_sha256": configuration.source_commit_sha256,
        "status": "EXACT_CREATE_RESPONSE_STARTED_POD_OBSERVED",
    }
    return _self_hashed(unsigned, "receipt_sha256")


def _reconcile_unique_created_pod(
    transport: RunPodTransport,
    *,
    intent: Mapping[str, object],
    pre_arm_pod_ids: set[str],
    events: list[dict[str, object]],
) -> str | None:
    try:
        observation = transport.list_pods()
        _record_event(events, "GET", LIST_PATH, observation)
        if observation.status != 200 or observation.effective_url != CREATE_URL:
            return None
        value = strict_json_value(observation.body, "RunPod Pod inventory")
        if isinstance(value, list):
            rows = value
        elif isinstance(value, dict) and set(value) == {"pods"} and isinstance(
            value["pods"], list
        ):
            rows = value["pods"]
        else:
            return None
        window_start = parse_utc(str(intent["creation_window_start_utc"]))
        window_end = parse_utc(str(intent["creation_window_end_utc"]))
        candidates: list[str] = []
        for row in rows:
            if not isinstance(row, dict) or row.get("name") != intent["pod_name"]:
                continue
            candidate_id = row.get("id")
            if not isinstance(candidate_id, str) or not _POD_ID.fullmatch(candidate_id):
                continue
            if candidate_id in PROTECTED_POD_IDS or candidate_id in pre_arm_pod_ids:
                continue
            timestamp_values = [
                item
                for item in (row.get("createdAt"), row.get("lastStartedAt"))
                if item is not None
            ]
            if not timestamp_values or any(
                not isinstance(item, str) for item in timestamp_values
            ):
                continue
            try:
                observed_times = [
                    parse_provider_utc(str(item)) for item in timestamp_values
                ]
            except Exception:
                continue
            if all(
                window_start - timedelta(seconds=30)
                <= observed
                <= window_end + timedelta(seconds=30)
                for observed in observed_times
            ):
                candidates.append(candidate_id)
        unique = sorted(set(candidates))
        return unique[0] if len(unique) == 1 else None
    except Exception:
        return None


def _stop_and_reconcile(
    transport: RunPodTransport,
    *,
    pod_id: str,
    expected_name: str | None,
    events: list[dict[str, object]],
    sleeper: Callable[[float], None],
    terminal_poll_limit: int,
    stop_attempt_limit: int,
) -> str:
    if pod_id in PROTECTED_POD_IDS or not _POD_ID.fullmatch(pod_id):
        return "PROTECTED_OR_INVALID_ID_NOT_MUTATED"
    exact_id_authority = expected_name is None
    for _attempt in range(max(1, stop_attempt_limit)):
        try:
            current = transport.get_pod(pod_id)
            _record_event(events, "GET", f"/v1/pods/{pod_id}", current)
            pod = _validated_recovery_get(
                current,
                pod_id,
                None if exact_id_authority else expected_name,
            )
            exact_id_authority = True
            if pod.get("desiredStatus") in {"EXITED", "TERMINATED"}:
                return "TERMINAL_CONFIRMED"
            stopped = transport.stop_pod(pod_id)
            _record_event(events, "POST", f"/v1/pods/{pod_id}/stop", stopped)
            if stopped.status != 200 or stopped.effective_url != (
                f"https://{API_HOST}/v1/pods/{pod_id}/stop"
            ):
                continue
            for _poll in range(max(1, terminal_poll_limit)):
                sleeper(0)
                observed = transport.get_pod(pod_id)
                _record_event(events, "GET", f"/v1/pods/{pod_id}", observed)
                terminal = _validated_recovery_get(observed, pod_id, None)
                if terminal.get("desiredStatus") in {"EXITED", "TERMINATED"}:
                    return "TERMINAL_CONFIRMED"
        except Exception:
            continue
    return "STOP_FAILED_OPERATOR_INTERVENTION_REQUIRED"


def _validated_recovery_get(
    observation: HttpObservation, pod_id: str, expected_name: str | None
) -> dict[str, object]:
    expected_url = f"https://{API_HOST}/v1/pods/{pod_id}"
    if observation.status != 200 or observation.effective_url != expected_url:
        raise ProtocolFailure("RECOVERY_GET_HTTP_BINDING_MISMATCH")
    value = strict_json_object(observation.body, "RunPod recovery GET")
    if value.get("id") != pod_id or (
        expected_name is not None and value.get("name") != expected_name
    ):
        raise ProtocolFailure("RECOVERY_GET_IDENTITY_MISMATCH")
    return value


def _record_event(
    events: list[dict[str, object]], method: str, path: str, value: HttpObservation
) -> None:
    events.append(
        {
            "body_byte_count": len(value.body),
            "body_sha256": sha256_bytes(value.body),
            "effective_url": value.effective_url,
            "method": method,
            "path": path,
            "response_http_status": value.status,
            "response_observed_at_utc": value.response_observed_at_utc,
        }
    )


def _salvage_unique_pod_id(raw: bytes) -> str | None:
    """Return one unambiguous top-level ID even if another field is hostile."""

    class Pairs(list[tuple[str, object]]):
        pass

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=Pairs,
            parse_constant=lambda item: ("NONFINITE", item),
            parse_float=lambda item: (
                float(item) if abs(float(item)) != float("inf") else ("NONFINITE", item)
            ),
        )
    except Exception:
        return None
    if not isinstance(value, Pairs):
        return None
    ids = [item for key, item in value if key == "id"]
    if len(ids) != 1 or not isinstance(ids[0], str) or not _POD_ID.fullmatch(ids[0]):
        return None
    return ids[0]


def strict_json_value(raw: bytes, label: str) -> object:
    def pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ProtocolFailure(f"DUPLICATE_JSON_KEY_{label.upper().replace(' ', '_')}")
            value[key] = item
        return value

    def reject_constant(_value: str) -> None:
        raise ProtocolFailure(f"NONFINITE_JSON_NUMBER_{label.upper().replace(' ', '_')}")

    def parse_finite_float(value: str) -> float:
        parsed = float(value)
        if parsed != parsed or abs(parsed) == float("inf"):
            raise ProtocolFailure(
                f"NONFINITE_JSON_NUMBER_{label.upper().replace(' ', '_')}"
            )
        return parsed

    try:
        return json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs_hook,
            parse_constant=reject_constant,
            parse_float=parse_finite_float,
        )
    except ProtocolFailure:
        raise
    except Exception as exc:
        raise ProtocolFailure("STRICT_JSON_INVALID") from exc


def strict_json_object(raw: bytes, label: str) -> dict[str, object]:
    value = strict_json_value(raw, label)
    if not isinstance(value, dict):
        raise ProtocolFailure("STRICT_JSON_TOP_LEVEL_NOT_OBJECT")
    return value


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def parse_utc(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProtocolFailure("UTC_TIMESTAMP_INVALID") from exc
    if parsed.tzinfo != timezone.utc:
        raise ProtocolFailure("UTC_TIMESTAMP_MUST_USE_UTC")
    return parsed


def parse_provider_utc(value: str) -> datetime:
    legacy = re.fullmatch(
        r"(?P<date>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) "
        r"(?P<offset>[+-]\d{4}) UTC",
        value,
    )
    if legacy:
        try:
            return datetime.strptime(
                f"{legacy.group('date')} {legacy.group('offset')}",
                "%Y-%m-%d %H:%M:%S.%f %z",
            ).astimezone(timezone.utc)
        except ValueError as exc:
            raise ProtocolFailure("PROVIDER_TIMESTAMP_INVALID") from exc
    return parse_utc(value)


def _format_utc(value: datetime) -> str:
    if value.tzinfo != timezone.utc:
        value = value.astimezone(timezone.utc)
    # Seven fractional digits matches .NET's round-trip ``o`` representation,
    # so PowerShell 7 DateTime parsing/serialization preserves canonical bytes.
    return value.strftime("%Y-%m-%dT%H:%M:%S.%f") + "0Z"


def _required_text(value: Mapping[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ProtocolFailure("REQUIRED_TEXT_FIELD_MISSING")
    return item


def _require_pod_id(pod_id: str) -> None:
    if not _POD_ID.fullmatch(pod_id):
        raise ProtocolFailure("POD_ID_INVALID")


def _self_hashed(value: Mapping[str, object], field: str) -> dict[str, object]:
    result = dict(value)
    result[field] = sha256_bytes(canonical_json_bytes(result))
    return result


def _write_artifact(
    writer: ArtifactWriter,
    guard: SecretGuard,
    path: Path,
    value: Mapping[str, object],
) -> None:
    raw = canonical_json_bytes(value)
    guard.assert_safe(raw)
    writer.create_new(path, raw)


def _bounded_header(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) > 256 or "\r" in value or "\n" in value:
        raise ProtocolFailure("RUNPOD_RESPONSE_HEADER_INVALID")
    return value


def _read_public_key(path: Path) -> str:
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    if len(lines) != 1 or not lines[0]:
        raise ProtocolFailure("DEDICATED_PUBLIC_KEY_FILE_INVALID")
    return lines[0]


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("plan", "live"), default="plan")
    parser.add_argument("--pod-name")
    parser.add_argument("--source-commit-sha256")
    parser.add_argument("--oci-image-digest")
    parser.add_argument(
        "--image-name",
        default="runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404",
    )
    parser.add_argument("--public-key-path", type=Path)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--authorization-sha256")
    parser.add_argument("--state-directory", type=Path)
    parser.add_argument("--provider-receipt", type=Path)
    parser.add_argument("--failure-evidence", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_cli_parser().parse_args(argv)
    if args.mode == "live":
        # This check intentionally precedes credential reads, authorization
        # consumption, transport construction, filesystem writes, and network.
        print("LIVE_NO_GO_PRECREATE_GUARDIAN_UNAVAILABLE")
        return 4
    if not all(
        (
            args.pod_name,
            args.source_commit_sha256,
            args.oci_image_digest,
            args.public_key_path,
        )
    ):
        print("INERT_PLAN_REQUIRES_POD_SOURCE_OCI_AND_PUBLIC_KEY_PATH")
        return 2
    try:
        dummy_root = Path.cwd()
        configuration = LaunchConfiguration(
            pod_name=args.pod_name,
            source_commit_sha256=args.source_commit_sha256,
            oci_image_digest=args.oci_image_digest,
            image_name=args.image_name,
            public_key=_read_public_key(args.public_key_path),
            authorization_path=args.authorization or dummy_root / "not-read.json",
            expected_authorization_sha256=args.authorization_sha256 or "",
            state_directory=args.state_directory or dummy_root,
            provider_receipt_path=args.provider_receipt or dummy_root / "not-written.json",
            failure_evidence_path=args.failure_evidence or dummy_root / "not-written.failure.json",
            public_key_path=args.public_key_path,
        )
        request_raw = canonical_json_bytes(build_create_request(configuration))
        result = {
            "create_attempts": 0,
            "live_status": "NO_GO_PRECREATE_GUARDIAN_UNAVAILABLE",
            "provider_calls": 0,
            "request_body_base64": base64.b64encode(request_raw).decode("ascii"),
            "request_body_byte_count": len(request_raw),
            "request_body_sha256": sha256_bytes(request_raw),
            "schema_version": "cas_runpod_create_once_inert_plan.v1",
            "status": "INERT_PLAN_NO_PROVIDER_OR_ARM_CALLS",
        }
        print(canonical_json_bytes(result).decode("utf-8"), end="")
        return 0
    except Exception:
        print("INERT_PLAN_VALIDATION_FAILED")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
