"""Offline hostile tests for the AWS production guardian core.

Every adapter in this module is a memory-only fake.  These tests make no AWS,
RunPod, GitHub, network, subprocess, credential, GPU, or model call.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import ast
import base64
import hashlib
import hmac
import json
from pathlib import Path
import sys
import threading
from typing import Any, Mapping

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import aws_production_guardian_core as guardian


BASE = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
ACCOUNT = "runpod-account-001"
EXECUTION_1 = (
    "arn:aws:states:us-west-2:123456789012:execution:"
    "cas-runpod-guardian:execution-one"
)
EXECUTION_2 = (
    "arn:aws:states:us-west-2:123456789012:execution:"
    "cas-runpod-guardian:execution-two"
)
DEDICATED_PUBLIC_KEY = (
    "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestOnlyGuardianKeyMaterial0001 "
    "cas-runpod-guardian-test"
)
ECHOED_API_SECRET = "sk_live_CAS_GUARDIAN_DO_NOT_PERSIST_7Q9M2X"
UNICODE_ESCAPED_SECRET = "".join(
    f"\\u{ord(character):04x}" for character in ECHOED_API_SECRET
)
PERCENT_ENCODED_SECRET = "".join(
    f"%{byte:02X}" for byte in ECHOED_API_SECRET.encode("ascii")
)
BASE32_ENCODED_SECRET = base64.b32encode(ECHOED_API_SECRET.encode("ascii")).decode(
    "ascii"
)
FRAGMENTED_SECRET_PARTS = (
    "sk_live_CAS_GUARDIAN_",
    "DO_NOT_PERSIST_7Q9M2X",
)
MISSING = object()


class HardCrash(BaseException):
    pass


class MemoryDynamoStore:
    """Thread-safe fake for PutItem and version-conditioned TransactWrite."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[tuple[str, str], dict[str, Any]] = {}
        self._evidence: dict[str, dict[str, Any]] = {}
        self.put_calls = 0
        self.replace_calls = 0
        self.successful_versions: list[int] = []
        self.head_sizes: list[int] = []

    def get_consistent(self, pk: str, sk: str) -> dict[str, Any] | None:
        with self._lock:
            value = self._items.get((pk, sk))
            return deepcopy(value) if value is not None else None

    def put_if_absent(
        self, pk: str, sk: str, item: Mapping[str, Any]
    ) -> bool:
        with self._lock:
            self.put_calls += 1
            if (pk, sk) in self._items:
                return False
            self._items[(pk, sk)] = deepcopy(dict(item))
            self.successful_versions.append(int(item["version"]))
            self.head_sizes.append(len(guardian.canonical_json_bytes(item)))
            return True

    def put_head_and_evidence_if_absent(
        self,
        pk: str,
        sk: str,
        item: Mapping[str, Any],
        *,
        evidence_id: str,
        evidence: Mapping[str, Any],
    ) -> bool:
        with self._lock:
            self.put_calls += 1
            assert len(guardian.canonical_json_bytes(item)) <= (
                guardian.MAX_LEDGER_ITEM_BYTES
            )
            assert len(guardian.canonical_json_bytes(evidence)) <= (
                guardian.MAX_EVIDENCE_ITEM_BYTES
            )
            if (pk, sk) in self._items or evidence_id in self._evidence:
                return False
            self._items[(pk, sk)] = deepcopy(dict(item))
            self._evidence[evidence_id] = deepcopy(dict(evidence))
            self.successful_versions.append(int(item["version"]))
            self.head_sizes.append(len(guardian.canonical_json_bytes(item)))
            return True

    def replace_if_version(
        self,
        pk: str,
        sk: str,
        *,
        expected_version: int,
        replacement: Mapping[str, Any],
    ) -> bool:
        with self._lock:
            self.replace_calls += 1
            assert len(guardian.canonical_json_bytes(replacement)) <= (
                guardian.MAX_LEDGER_ITEM_BYTES
            )
            current = self._items.get((pk, sk))
            if current is None or current.get("version") != expected_version:
                return False
            assert replacement["version"] == expected_version + 1
            self._items[(pk, sk)] = deepcopy(dict(replacement))
            self.successful_versions.append(int(replacement["version"]))
            self.head_sizes.append(len(guardian.canonical_json_bytes(replacement)))
            return True

    def replace_head_and_put_evidence_if_version(
        self,
        pk: str,
        sk: str,
        *,
        expected_version: int,
        replacement: Mapping[str, Any],
        evidence_id: str,
        evidence: Mapping[str, Any],
    ) -> bool:
        with self._lock:
            self.replace_calls += 1
            assert len(guardian.canonical_json_bytes(replacement)) <= (
                guardian.MAX_LEDGER_ITEM_BYTES
            )
            assert len(guardian.canonical_json_bytes(evidence)) <= (
                guardian.MAX_EVIDENCE_ITEM_BYTES
            )
            current = self._items.get((pk, sk))
            if (
                current is None
                or current.get("version") != expected_version
                or evidence_id in self._evidence
            ):
                return False
            assert replacement["version"] == expected_version + 1
            self._items[(pk, sk)] = deepcopy(dict(replacement))
            self._evidence[evidence_id] = deepcopy(dict(evidence))
            self.successful_versions.append(int(replacement["version"]))
            self.head_sizes.append(len(guardian.canonical_json_bytes(replacement)))
            return True

    def get_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        with self._lock:
            value = self._evidence.get(evidence_id)
            return deepcopy(value) if value is not None else None


class FailingAtomicEvidenceStore(MemoryDynamoStore):
    def __init__(self) -> None:
        super().__init__()
        self.fail_next_evidence_replace = False

    def replace_head_and_put_evidence_if_version(self, *args, **kwargs) -> bool:
        if self.fail_next_evidence_replace:
            self.fail_next_evidence_replace = False
            raise OSError("simulated atomic evidence transaction outage")
        return super().replace_head_and_put_evidence_if_version(*args, **kwargs)


class VersionOneTransitionRaceStore(MemoryDynamoStore):
    def __init__(self) -> None:
        super().__init__()
        self.version_one_barrier = threading.Barrier(2)
        self.race_armed = False

    def _gate_version_one(self, expected_version: int) -> None:
        if self.race_armed and expected_version == 1:
            self.version_one_barrier.wait(timeout=10)

    def replace_if_version(self, *args, **kwargs) -> bool:
        self._gate_version_one(int(kwargs["expected_version"]))
        return super().replace_if_version(*args, **kwargs)

    def replace_head_and_put_evidence_if_version(self, *args, **kwargs) -> bool:
        self._gate_version_one(int(kwargs["expected_version"]))
        return super().replace_head_and_put_evidence_if_version(*args, **kwargs)


class ManualClock:
    def __init__(self, now: datetime = BASE) -> None:
        self._lock = threading.RLock()
        self._now = now

    def now(self) -> datetime:
        with self._lock:
            return self._now

    def set(self, value: datetime) -> None:
        with self._lock:
            self._now = value

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._now += timedelta(seconds=seconds)


class PerThreadClock(ManualClock):
    def __init__(self, default: datetime = BASE) -> None:
        super().__init__(default)
        self.thread_times: dict[str, datetime] = {}

    def now(self) -> datetime:
        with self._lock:
            return self.thread_times.get(threading.current_thread().name, self._now)


class FakeKmsSigner:
    """Deterministic test double; its bytes are not an AWS KMS signature."""

    key_arn = "arn:aws:kms:us-west-2:123456789012:key/fake-test-key-0001"
    algorithm = "ECDSA_SHA_256"
    message_type = "DIGEST"

    def __init__(self) -> None:
        self.secret = b"offline-test-only-not-a-kms-key"
        self.calls: list[bytes] = []
        self._lock = threading.RLock()

    def sign_digest(self, digest: bytes) -> guardian.KmsSignature:
        assert type(digest) is bytes and len(digest) == 32
        with self._lock:
            self.calls.append(bytes(digest))
        return guardian.KmsSignature(
            self.key_arn,
            self.algorithm,
            self.message_type,
            hmac.new(self.secret, digest, hashlib.sha256).digest(),
        )

    def assert_valid(self, receipt: Mapping[str, Any]) -> None:
        message = guardian.receipt_signing_message(receipt)
        digest = hashlib.sha256(message).digest()
        assert base64.b64decode(receipt["kms_digest_base64"], validate=True) == digest
        expected = hmac.new(self.secret, digest, hashlib.sha256).digest()
        actual = base64.b64decode(receipt["kms_signature_base64"], validate=True)
        assert hmac.compare_digest(actual, expected)


class BadSigner(FakeKmsSigner):
    def __init__(
        self,
        *,
        key_arn: str | None = None,
        algorithm: str | None = None,
        message_type: str | None = None,
    ):
        super().__init__()
        if key_arn is not None:
            self.key_arn = key_arn
        if algorithm is not None:
            self.algorithm = algorithm
        if message_type is not None:
            self.message_type = message_type


class FakeSecretGuard:
    def __init__(self, forbidden: tuple[bytes, ...] = ()) -> None:
        self.forbidden = forbidden
        self.calls: list[str] = []

    def assert_safe(self, raw: bytes) -> None:
        self.calls.append(hashlib.sha256(raw).hexdigest())
        if any(token and token in raw for token in self.forbidden):
            raise guardian.ValidationError("SECRET_GUARD_REJECTED_BYTES")


class MarkerDelayingSigner(FakeKmsSigner):
    def __init__(self, clock: ManualClock) -> None:
        super().__init__()
        self.clock = clock

    def sign_digest(self, digest: bytes) -> guardian.KmsSignature:
        result = super().sign_digest(digest)
        # The marker receipt is the fifth persisted receipt in this fixture.
        if len(self.calls) == 5:
            self.clock.set(BASE + timedelta(seconds=51))
        return result


class AdmissionDelayingSigner(FakeKmsSigner):
    def __init__(self, clock: ManualClock) -> None:
        super().__init__()
        self.clock = clock

    def sign_digest(self, digest: bytes) -> guardian.KmsSignature:
        result = super().sign_digest(digest)
        # Registration, consumption, arm, reservation, dispatch, and binding
        # consume calls one through six.  Move trusted time to STOP dispatch
        # immediately after the first otherwise-admitting receipt signature.
        if len(self.calls) == 7:
            self.clock.set(BASE + timedelta(seconds=100))
        return result


class FailingKmsSigner(FakeKmsSigner):
    def __init__(self, fail_from_call: int) -> None:
        super().__init__()
        self.fail_from_call: int | None = fail_from_call

    def sign_digest(self, digest: bytes) -> guardian.KmsSignature:
        if self.fail_from_call is not None and len(self.calls) + 1 >= self.fail_from_call:
            raise OSError("simulated KMS outage")
        return super().sign_digest(digest)


def response_201(pod_name: str, *, pod_id: str = "newpod1234", **changes: Any):
    value: dict[str, Any] = {
        "id": pod_id,
        "name": pod_name,
        "imageName": guardian.FROZEN_IMAGE_NAME,
        "gpuCount": 1,
        "machine": {"gpuTypeId": "NVIDIA A40", "secureCloud": True},
        "gpu": {"id": "NVIDIA A40", "displayName": "A40"},
        "interruptible": False,
        "locked": False,
        "networkVolume": None,
        "networkVolumeId": None,
        "volumeInGb": 20,
        "containerDiskInGb": 50,
        "volumeMountPath": "/workspace",
        "volumeEncrypted": True,
        "ports": ["22/tcp"],
        "portMappings": {"22": 22022},
        "env": {"PUBLIC_KEY": DEDICATED_PUBLIC_KEY},
        "costPerHr": 0.35,
        "adjustedCostPerHr": 0.35,
        "desiredStatus": "RUNNING",
        "createdAt": guardian.iso_utc(BASE + timedelta(seconds=10)),
        "lastStartedAt": guardian.iso_utc(BASE + timedelta(seconds=10)),
    }
    value.update(changes)
    return guardian.HttpResponse(
        201,
        guardian.canonical_json_bytes(value),
        guardian.CREATE_ENDPOINT,
    )


class FakeProvider:
    def __init__(self, pods: list[dict[str, Any]] | None = None) -> None:
        self._lock = threading.RLock()
        self.pods = {str(item["id"]): deepcopy(item) for item in pods or []}
        self.inventory_complete = True
        self.inventory_unfiltered = True
        self.inventory_account = ACCOUNT
        self.inventory_scope = guardian.INVENTORY_SCOPE
        self.raw_pages_override: tuple[bytes, ...] | None = None
        self.list_calls = 0
        self.post_entries = 0
        self.provider_create_commits = 0
        self.get_calls: list[str] = []
        self.get_response_override: guardian.HttpResponse | None = None
        self.stop_calls: list[str] = []
        self.post_response: guardian.HttpResponse | None = None
        self.created_pod: dict[str, Any] | None = None
        self.post_mode = "return"
        self.stop_mode = "return"
        self.post_entered = threading.Event()
        self.post_release: threading.Event | None = None

    def list_all_pods(self, provider_account_id: str) -> guardian.InventorySnapshot:
        with self._lock:
            self.list_calls += 1
            pages = self.raw_pages_override
            if pages is None:
                pages = (
                    guardian.canonical_json_bytes(
                        sorted(self.pods.values(), key=lambda item: str(item["id"]))
                    ),
                )
            return guardian.InventorySnapshot(
                self.inventory_account,
                self.inventory_scope,
                self.inventory_complete,
                self.inventory_unfiltered,
                pages,
            )

    def post_create(
        self,
        provider_account_id: str,
        endpoint: str,
        exact_body: bytes,
    ) -> guardian.HttpResponse:
        assert provider_account_id == ACCOUNT
        assert endpoint == guardian.CREATE_ENDPOINT
        with self._lock:
            self.post_entries += 1
            mode = self.post_mode
        self.post_entered.set()
        if self.post_release is not None:
            assert self.post_release.wait(timeout=10)
        if mode == "crash_before_provider":
            raise HardCrash("process died after marker, before provider send")
        with self._lock:
            self.provider_create_commits += 1
            if self.created_pod is not None:
                self.pods[str(self.created_pod["id"])] = deepcopy(self.created_pod)
        if mode == "crash_after_provider":
            raise HardCrash("process died after provider commit")
        if mode == "ambiguous_after_provider":
            raise OSError("connection lost after request bytes left the process")
        assert self.post_response is not None
        return self.post_response

    def get_pod(
        self, provider_account_id: str, pod_id: str
    ) -> guardian.HttpResponse:
        assert provider_account_id == ACCOUNT
        with self._lock:
            self.get_calls.append(pod_id)
            if self.get_response_override is not None:
                return deepcopy(self.get_response_override)
            return guardian.HttpResponse(
                200,
                guardian.canonical_json_bytes(self.pods[pod_id]),
                f"{guardian.CREATE_ENDPOINT}/{pod_id}",
            )

    def stop_pod(
        self, provider_account_id: str, pod_id: str
    ) -> guardian.HttpResponse:
        assert provider_account_id == ACCOUNT
        with self._lock:
            self.stop_calls.append(pod_id)
            mode = self.stop_mode
        if mode == "crash_before_provider":
            raise HardCrash("STOP caller died before provider action")
        with self._lock:
            self.pods[pod_id]["desiredStatus"] = "EXITED"
        if mode == "crash_after_provider":
            raise HardCrash("STOP caller died after provider action")
        if mode == "ambiguous_after_provider":
            raise OSError("STOP response lost")
        return guardian.HttpResponse(
            200,
            guardian.canonical_json_bytes({"id": pod_id, "desiredStatus": "EXITED"}),
            f"{guardian.CREATE_ENDPOINT}/{pod_id}/stop",
        )


def make_spec(
    *,
    key: guardian.AuthorizationKey | None = None,
    request_sha256: str | None = None,
) -> tuple[guardian.AuthorizationSpec, bytes]:
    key = key or guardian.AuthorizationKey(
        "owner.example", ACCOUNT, "authorization-0001"
    )
    pod_name = (
        "cas-open-weight-canary-v2-20260820t120010000000z-"
        "abababababababababababababababab"
    )
    request = guardian.canonical_json_bytes(
        {
            "cloudType": "SECURE",
            "containerDiskInGb": 50,
            "env": {"PUBLIC_KEY": DEDICATED_PUBLIC_KEY},
            "gpuCount": 1,
            "gpuTypeIds": ["NVIDIA A40"],
            "imageName": guardian.FROZEN_IMAGE_NAME,
            "interruptible": False,
            "locked": False,
            "name": pod_name,
            "networkVolumeId": None,
            "ports": ["22/tcp"],
            "volumeEncrypted": True,
            "volumeInGb": 20,
            "volumeMountPath": "/workspace",
        }
    )
    spec = guardian.AuthorizationSpec(
        key=key,
        authorization_document_sha256="a" * 64,
        exact_create_request_sha256=request_sha256 or guardian.sha256_hex(request),
        pod_name=pod_name,
        source_commit_sha="b" * 40,
        oci_image_digest="sha256:" + "c" * 64,
        image_name=guardian.FROZEN_IMAGE_NAME,
        dedicated_public_key_sha256=guardian.sha256_hex(
            DEDICATED_PUBLIC_KEY.encode("utf-8")
        ),
        max_cost_per_hour="0.50",
        not_before_utc=guardian.iso_utc(BASE),
        expires_at_utc=guardian.iso_utc(BASE + timedelta(seconds=50)),
        creation_window_start_utc=guardian.iso_utc(BASE + timedelta(seconds=10)),
        creation_window_end_utc=guardian.iso_utc(BASE + timedelta(seconds=50)),
        stop_dispatch_at_utc=guardian.iso_utc(BASE + timedelta(seconds=100)),
        hard_stop_deadline_utc=guardian.iso_utc(BASE + timedelta(seconds=200)),
        terminal_proof_deadline_utc=guardian.iso_utc(BASE + timedelta(seconds=290)),
        protected_pod_ids=tuple(sorted(guardian.REQUIRED_PROTECTED_POD_IDS)),
    )
    return spec, request


def make_core(
    *,
    store: MemoryDynamoStore | None = None,
    provider: FakeProvider | None = None,
    signer: FakeKmsSigner | None = None,
    secret_guard: FakeSecretGuard | None = None,
    clock: ManualClock | None = None,
):
    store = store or MemoryDynamoStore()
    provider = provider or FakeProvider()
    signer = signer or FakeKmsSigner()
    secret_guard = secret_guard or FakeSecretGuard()
    clock = clock or ManualClock()
    core = guardian.AwsProductionGuardianCore(
        store=store,
        transport=provider,
        signer=signer,
        secret_guard=secret_guard,
        clock=clock,
    )
    return core, store, provider, signer, clock


def first_claim(
    core: guardian.AwsProductionGuardianCore,
    spec: guardian.AuthorizationSpec,
    request: bytes,
    *,
    execution_arn: str = EXECUTION_1,
    lease_seconds: int = 60,
) -> guardian.ExecutionToken:
    return core.claim_execution(
        spec.key,
        execution_arn=execution_arn,
        lease_seconds=lease_seconds,
        exact_create_request_bytes=request,
        expected_authorization_spec_sha256=guardian.authorization_spec_sha256(
            spec
        ),
    )


def setup_armed(
    *,
    store: MemoryDynamoStore | None = None,
    provider: FakeProvider | None = None,
    signer: FakeKmsSigner | None = None,
    secret_guard: FakeSecretGuard | None = None,
    clock: ManualClock | None = None,
    lease_seconds: int = 200,
):
    core, store, provider, signer, clock = make_core(
        store=store,
        provider=provider,
        signer=signer,
        secret_guard=secret_guard,
        clock=clock,
    )
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = core.claim_execution(
        spec.key,
        execution_arn=EXECUTION_1,
        lease_seconds=lease_seconds,
        exact_create_request_bytes=request,
        expected_authorization_spec_sha256=guardian.authorization_spec_sha256(
            spec
        ),
    )
    arm = core.arm_precreate(token, exact_create_request_bytes=request)
    clock.set(BASE + timedelta(seconds=10))
    return core, store, provider, signer, clock, spec, request, token, arm


def reserve_and_set_201(
    core: guardian.AwsProductionGuardianCore,
    provider: FakeProvider,
    spec: guardian.AuthorizationSpec,
    request: bytes,
    token: guardian.ExecutionToken,
    *,
    response: guardian.HttpResponse | None = None,
) -> guardian.CreateReservation:
    reservation = core.reserve_create(token, exact_create_request_bytes=request)
    provider.post_response = response or response_201(spec.pod_name)
    return reservation


def bind_pending_fixture():
    values = setup_armed()
    core, _store, provider, _signer, _clock, spec, request, token, _arm = values
    pod = json.loads(response_201(spec.pod_name).body)
    provider.created_pod = pod
    reservation = reserve_and_set_201(core, provider, spec, request, token)
    outcome = core.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.target_bound
    assert outcome.launch_admitted is False
    assert provider.get_calls == []
    return (*values, reservation, pod)


def bind_success_fixture():
    values = bind_pending_fixture()
    core, _store, _provider, _signer, _clock, _spec, _request, token, _arm, _reservation, _pod = values
    admission = core.verify_post_bind_launch_admission(token)
    assert admission["payload"]["launch_admitted"] is True
    return values


def durable_storage_layers(store: MemoryDynamoStore) -> list[bytes]:
    """Return plaintext and explicitly reversible Base64 layers in the fake store."""

    layers: list[bytes] = []

    def visit(value: Any, *, depth: int = 0) -> None:
        if depth > 5:
            return
        if isinstance(value, Mapping):
            layers.append(guardian.canonical_json_bytes(dict(value)))
            for key, nested in value.items():
                visit(nested, depth=depth + 1)
                if isinstance(key, str) and key.lower().endswith("base64") and isinstance(
                    nested, str
                ):
                    try:
                        decoded = base64.b64decode(nested, validate=True)
                    except (TypeError, ValueError):
                        continue
                    layers.append(decoded)
                    try:
                        parsed = json.loads(decoded)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    visit(parsed, depth=depth + 1)
        elif isinstance(value, list):
            for nested in value:
                visit(nested, depth=depth + 1)

    with store._lock:
        for value in (*store._items.values(), *store._evidence.values()):
            visit(deepcopy(value))
    return layers


def assert_not_durably_reversible(
    store: MemoryDynamoStore, *forbidden_values: bytes
) -> None:
    layers = durable_storage_layers(store)
    for forbidden in forbidden_values:
        assert forbidden
        assert all(forbidden not in layer for layer in layers)


def test_strict_json_rejects_duplicate_nonfinite_and_invalid_utf8():
    with pytest.raises(guardian.ValidationError, match="duplicate"):
        guardian.strict_json(b'{"x":1,"x":2}', "hostile")
    with pytest.raises(guardian.ValidationError, match="strict finite"):
        guardian.strict_json(b'{"x":NaN}', "hostile")
    with pytest.raises(guardian.ValidationError, match="strict finite"):
        guardian.strict_json(b'{"x":"\xff"}', "hostile")


def test_authorization_key_is_primary_and_duplicate_request_cannot_reregister():
    core, store, _provider, _signer, _clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    with pytest.raises(guardian.AuthorizationAlreadyExists):
        core.register_authorization(spec, exact_create_request_bytes=request)
    assert store.put_calls == 2
    assert core.read_record(spec.key)["authorization_spec"][
        "exact_create_request_sha256"
    ] == spec.exact_create_request_sha256
    assert core.read_record(spec.key)["authorization_spec_sha256"] == (
        guardian.authorization_spec_sha256(spec)
    )


def test_first_claim_requires_exact_request_and_registered_spec_hash():
    core, store, provider, _signer, _clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)

    with pytest.raises(guardian.ValidationError, match="spec hash mismatch"):
        core.claim_execution(
            spec.key,
            execution_arn=EXECUTION_1,
            lease_seconds=60,
            exact_create_request_bytes=request,
            expected_authorization_spec_sha256="0" * 64,
        )
    with pytest.raises(guardian.ValidationError, match="SHA-256"):
        core.claim_execution(
            spec.key,
            execution_arn=EXECUTION_1,
            lease_seconds=60,
            exact_create_request_bytes=request + b" ",
            expected_authorization_spec_sha256=(
                guardian.authorization_spec_sha256(spec)
            ),
        )
    with pytest.raises(guardian.ValidationError, match="spec hash mismatch"):
        core.claim_execution(
            spec.key,
            execution_arn=EXECUTION_1,
            lease_seconds=60,
        )
    record = core.read_record(spec.key)
    assert record["state"] == "AUTHORIZED"
    assert record["authorization_consumed"] is False
    assert store.replace_calls == 0
    assert provider.list_calls == 0
    assert provider.post_entries == 0

    token = first_claim(core, spec, request)
    assert token.fence == 1


@pytest.mark.parametrize("bad_component", ["request", "spec_hash"])
def test_wrong_envelope_claimant_cannot_win_race_with_valid_claimant(
    bad_component
):
    core, _store, _provider, _signer, _clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    barrier = threading.Barrier(2)
    results: list[tuple[str, Any]] = []
    lock = threading.Lock()
    valid_arn = (
        "arn:aws:states:us-west-2:123456789012:execution:"
        "cas-runpod-guardian:valid-envelope"
    )
    bad_arn = (
        "arn:aws:states:us-west-2:123456789012:execution:"
        "cas-runpod-guardian:wrong-envelope"
    )

    def claimant(*, valid: bool) -> None:
        barrier.wait()
        try:
            body = request
            spec_hash = guardian.authorization_spec_sha256(spec)
            if not valid and bad_component == "request":
                body += b" "
            if not valid and bad_component == "spec_hash":
                spec_hash = "0" * 64
            token = core.claim_execution(
                spec.key,
                execution_arn=valid_arn if valid else bad_arn,
                lease_seconds=60,
                exact_create_request_bytes=body,
                expected_authorization_spec_sha256=spec_hash,
            )
            outcome: Any = token
        except BaseException as error:
            outcome = error
        with lock:
            results.append(("valid" if valid else "bad", outcome))

    threads = [
        threading.Thread(target=claimant, kwargs={"valid": False}),
        threading.Thread(target=claimant, kwargs={"valid": True}),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads)
    result_by_name = dict(results)
    assert isinstance(result_by_name["valid"], guardian.ExecutionToken)
    assert isinstance(
        result_by_name["bad"],
        (guardian.ValidationError, guardian.OwnershipBusy),
    )
    record = core.read_record(spec.key)
    assert record["owner_execution_arn"] == valid_arn
    assert record["owner_fence"] == 1
    assert record["authorization_consumed"] is True


def test_unclaimed_authorization_safe_loss_expiry_boundary_and_idempotency():
    core, store, provider, signer, clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    expires = guardian.parse_utc(spec.expires_at_utc)

    clock.set(expires - timedelta(microseconds=1))
    with pytest.raises(guardian.NotReady, match="has not expired"):
        core.finalize_unclaimed_authorization_safe_loss(spec.key)
    assert core.read_record(spec.key)["state"] == "AUTHORIZED"

    clock.set(expires)
    receipt = core.finalize_unclaimed_authorization_safe_loss(spec.key)
    signer.assert_valid(receipt)
    assert receipt["payload"]["authorization_consumed"] is False
    assert receipt["payload"]["provider_create_attempts"] == 0
    assert receipt["payload"]["create_dispatch_marker_present"] is False
    record = core.read_record(spec.key)
    assert record["state"] == "NO_CREATE_DISPATCHED_SAFE_LOSS"
    assert record["unclaimed_authorization_safe_loss"] is True
    assert record["authorization_consumed"] is False
    assert record.get("owner_execution_arn") is None
    assert provider.post_entries == 0
    evidence_count = len(store._evidence)
    signer_call_count = len(signer.calls)

    repeated = core.finalize_unclaimed_authorization_safe_loss(spec.key)
    assert repeated["receipt_sha256"] == receipt["receipt_sha256"]
    assert len(store._evidence) == evidence_count
    assert len(signer.calls) == signer_call_count


def test_concurrent_unclaimed_finalizers_converge_on_one_atomic_receipt():
    core, store, _provider, signer, clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    clock.set(guardian.parse_utc(spec.expires_at_utc))
    barrier = threading.Barrier(20)
    receipts: list[dict[str, Any]] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def finalize() -> None:
        barrier.wait()
        try:
            value = core.finalize_unclaimed_authorization_safe_loss(spec.key)
            with lock:
                receipts.append(value)
        except BaseException as error:
            with lock:
                errors.append(error)

    threads = [threading.Thread(target=finalize) for _index in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads)
    assert errors == []
    assert len(receipts) == 20
    assert len({receipt["receipt_sha256"] for receipt in receipts}) == 1
    assert core.read_record(spec.key)["version"] == 2
    assert len(store._evidence) == 2
    for receipt in receipts:
        signer.assert_valid(receipt)


def test_unclaimed_finalizer_kms_and_store_failures_leave_recoverable_head():
    store = FailingAtomicEvidenceStore()
    signer = FailingKmsSigner(fail_from_call=2)
    clock = ManualClock()
    core, _store, _provider, _signer, _clock = make_core(
        store=store, signer=signer, clock=clock
    )
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    clock.set(guardian.parse_utc(spec.expires_at_utc))

    with pytest.raises(OSError, match="KMS outage"):
        core.finalize_unclaimed_authorization_safe_loss(spec.key)
    assert core.read_record(spec.key)["state"] == "AUTHORIZED"
    assert len(store._evidence) == 1

    signer.fail_from_call = None
    store.fail_next_evidence_replace = True
    with pytest.raises(OSError, match="atomic evidence transaction outage"):
        core.finalize_unclaimed_authorization_safe_loss(spec.key)
    assert core.read_record(spec.key)["state"] == "AUTHORIZED"
    assert len(store._evidence) == 1

    recovered = core.finalize_unclaimed_authorization_safe_loss(spec.key)
    signer.assert_valid(recovered)
    assert core.read_record(spec.key)["state"] == (
        "NO_CREATE_DISPATCHED_SAFE_LOSS"
    )
    assert len(store._evidence) == 2


def test_unclaimed_finalizer_rejects_non_authorized_or_owner_tainted_state():
    core, store, _provider, _signer, clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request)
    clock.set(guardian.parse_utc(spec.expires_at_utc))
    with pytest.raises(guardian.NotReady, match="AUTHORIZED state"):
        core.finalize_unclaimed_authorization_safe_loss(spec.key)
    assert core.read_record(spec.key)["owner_fence"] == token.fence

    second_core, second_store, _provider, _signer, second_clock = make_core()
    second_spec, second_request = make_spec(
        key=guardian.AuthorizationKey(
            "owner.example", ACCOUNT, "authorization-owner-tainted"
        )
    )
    second_core.register_authorization(
        second_spec, exact_create_request_bytes=second_request
    )
    with second_store._lock:
        second_store._items[(second_spec.key.pk, second_spec.key.sk)][
            "owner_execution_arn"
        ] = EXECUTION_1
    second_clock.set(guardian.parse_utc(second_spec.expires_at_utc))
    with pytest.raises(guardian.ValidationError, match="conflicts with ownership"):
        second_core.finalize_unclaimed_authorization_safe_loss(second_spec.key)


def test_first_claim_and_unclaimed_expiry_finalizer_have_one_cas_winner():
    store = VersionOneTransitionRaceStore()
    clock = PerThreadClock()
    core, _store, _provider, _signer, _clock = make_core(store=store, clock=clock)
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    clock.thread_times["claim-before-expiry"] = guardian.parse_utc(
        spec.expires_at_utc
    ) - timedelta(microseconds=1)
    clock.thread_times["finalize-at-expiry"] = guardian.parse_utc(
        spec.expires_at_utc
    )
    store.race_armed = True
    outcomes: list[tuple[str, Any]] = []
    lock = threading.Lock()

    def claim() -> None:
        try:
            outcome: Any = first_claim(core, spec, request)
        except BaseException as error:
            outcome = error
        with lock:
            outcomes.append(("claim", outcome))

    def finalize() -> None:
        try:
            outcome: Any = core.finalize_unclaimed_authorization_safe_loss(
                spec.key
            )
        except BaseException as error:
            outcome = error
        with lock:
            outcomes.append(("finalize", outcome))

    threads = [
        threading.Thread(target=claim, name="claim-before-expiry"),
        threading.Thread(target=finalize, name="finalize-at-expiry"),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads)
    result = dict(outcomes)
    successes = sum(
        isinstance(result[name], expected)
        for name, expected in (
            ("claim", guardian.ExecutionToken),
            ("finalize", dict),
        )
    )
    assert successes == 1
    record = core.read_record(spec.key)
    if isinstance(result["claim"], guardian.ExecutionToken):
        assert isinstance(result["finalize"], guardian.NotReady)
        assert record["state"] == "CLAIMED"
        assert record["owner_execution_arn"] == EXECUTION_1
    else:
        assert isinstance(result["claim"], guardian.AuthorizationUnavailable)
        assert record["state"] == "NO_CREATE_DISPATCHED_SAFE_LOSS"
        assert record.get("owner_execution_arn") is None


def test_two_fresh_core_instances_share_one_global_consumption():
    store = MemoryDynamoStore()
    provider = FakeProvider()
    signer = FakeKmsSigner()
    clock = ManualClock()
    first = make_core(store=store, provider=provider, signer=signer, clock=clock)[0]
    second = make_core(store=store, provider=provider, signer=signer, clock=clock)[0]
    spec, request = make_spec()
    first.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(first, spec, request)
    assert token.fence == 1
    with pytest.raises(guardian.OwnershipBusy):
        second.claim_execution(
            spec.key, execution_arn=EXECUTION_2, lease_seconds=60
        )
    assert second.read_record(spec.key)["authorization_consumed"] is True


def test_concurrent_claim_has_exactly_one_owner_and_monotonic_versions():
    core, store, _provider, _signer, _clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    barrier = threading.Barrier(20)
    successes: list[guardian.ExecutionToken] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker(index: int) -> None:
        arn = (
            "arn:aws:states:us-west-2:123456789012:execution:"
            f"cas-runpod-guardian:race-{index}"
        )
        barrier.wait()
        try:
            value = first_claim(
                core, spec, request, execution_arn=arn, lease_seconds=60
            )
            with lock:
                successes.append(value)
        except BaseException as error:
            with lock:
                errors.append(error)

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads)
    assert len(successes) == 1
    assert len(errors) == 19
    assert all(isinstance(error, guardian.OwnershipBusy) for error in errors)
    assert store.successful_versions == sorted(set(store.successful_versions))
    record = core.read_record(spec.key)
    assert record["authorization_consumed"] is True
    assert record["owner_fence"] == 1


def test_one_thousand_expired_owner_takeovers_keep_head_bounded_and_stop_capable():
    values = bind_success_fixture()
    core, store, provider, _signer, clock, spec, _request, _old, _arm, _res, pod = values
    clock.set(BASE + timedelta(seconds=201))
    latest = None
    for index in range(1_000):
        execution = (
            "arn:aws:states:us-west-2:123456789012:execution:"
            f"cas-runpod-guardian:takeover-{index:04d}"
        )
        latest = core.claim_execution(
            spec.key, execution_arn=execution, lease_seconds=5
        )
        if index != 999:
            clock.advance(6)
    assert latest is not None
    record = core.read_record(spec.key)
    assert record["takeover_receipt_count"] == 1_000
    assert record["owner_fence"] == 1_001
    assert record["ownership_receipt_status"] == "PENDING_KMS_EVIDENCE"
    assert not any(name.startswith("takeover_") for name in record["receipts"])
    assert max(store.head_sizes) < guardian.MAX_LEDGER_ITEM_BYTES
    receipt = core.request_stop(latest)
    assert receipt is not None
    assert provider.stop_calls == [pod["id"]]
    terminal_record = core.read_record(spec.key)
    assert terminal_record["state"] == "TERMINAL_PROVEN"
    assert "latest_takeover" in terminal_record["receipts"]


def test_kms_outage_cannot_block_expired_owner_takeover_or_exact_id_stop():
    signer = FailingKmsSigner(fail_from_call=10_000)
    values = setup_armed(signer=signer)
    core, _store, provider, _signer, clock, spec, request, old, _arm = values
    pod = json.loads(response_201(spec.pod_name).body)
    provider.created_pod = pod
    reservation = reserve_and_set_201(core, provider, spec, request, old)
    core.dispatch_create(old, reservation, exact_create_request_bytes=request)
    core.verify_post_bind_launch_admission(old)
    signer.fail_from_call = len(signer.calls) + 1
    clock.set(BASE + timedelta(seconds=201))
    new = core.claim_execution(
        spec.key, execution_arn=EXECUTION_2, lease_seconds=30
    )
    record = core.read_record(spec.key)
    assert record["owner_fence"] == 2
    assert record["ownership_receipt_status"] == "PENDING_KMS_EVIDENCE"
    with pytest.raises(OSError, match="KMS outage"):
        core.request_stop(new)
    assert provider.stop_calls == [pod["id"]]
    assert provider.pods[pod["id"]]["desiredStatus"] == "EXITED"


def test_same_execution_claim_is_idempotent():
    core, _store, _provider, _signer, _clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    first = first_claim(core, spec, request)
    second = core.claim_execution(spec.key, execution_arn=EXECUTION_1, lease_seconds=60)
    assert second == first
    assert core.read_record(spec.key)["owner_fence"] == 1


def test_expired_lease_takeover_increments_fence_and_rejects_old_owner():
    core, _store, _provider, _signer, clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    old = first_claim(core, spec, request, lease_seconds=5)
    clock.advance(5)
    with pytest.raises(guardian.ValidationError, match="derive.*ledger"):
        core.claim_execution(
            spec.key,
            execution_arn=EXECUTION_2,
            lease_seconds=60,
            exact_create_request_bytes=request,
            expected_authorization_spec_sha256=(
                guardian.authorization_spec_sha256(spec)
            ),
        )
    new = core.claim_execution(spec.key, execution_arn=EXECUTION_2, lease_seconds=60)
    assert new.fence == old.fence + 1
    with pytest.raises(guardian.StaleFence):
        core.heartbeat(old, expected_sequence=0, lease_seconds=30)


def test_heartbeat_is_durable_and_sequence_fenced():
    core, _store, _provider, _signer, clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request, lease_seconds=30)
    clock.advance(10)
    next_token = core.heartbeat(token, expected_sequence=0, lease_seconds=30)
    assert next_token.heartbeat_sequence == 1
    with pytest.raises(guardian.StaleFence, match="sequence"):
        core.heartbeat(next_token, expected_sequence=0, lease_seconds=30)


def test_bound_target_lease_budget_and_due_preemption_guarantee_stop_recovery():
    values = bind_success_fixture()
    core, _store, provider, _signer, clock, spec, _request, old, _arm, _res, pod = values
    bound = core.read_record(spec.key)
    assert guardian.parse_utc(bound["owner_lease_expires_at_utc"]) == (
        BASE + timedelta(seconds=10 + guardian.MAX_CONTAINMENT_OWNER_LEASE_SECONDS)
    )
    assert (
        guardian.MAX_CONTAINMENT_OWNER_LEASE_SECONDS
        + guardian.MAX_GUARDIAN_WAKE_INTERVAL_SECONDS
        + guardian.MAX_WORKER_STARTUP_SECONDS
        + guardian.MAX_PROVIDER_STOP_EXECUTION_SECONDS
        + guardian.MIN_STOP_SAFETY_MARGIN_SECONDS
        < guardian.MIN_STOP_LEAD_SECONDS
    )

    clock.set(BASE + timedelta(seconds=12))
    old = core.heartbeat(old, expected_sequence=0, lease_seconds=300)
    refreshed = core.read_record(spec.key)
    assert guardian.parse_utc(refreshed["owner_lease_expires_at_utc"]) == (
        guardian.parse_utc(spec.stop_dispatch_at_utc)
        + timedelta(seconds=guardian.MAX_CONTAINMENT_OWNER_LEASE_SECONDS)
    )

    clock.set(guardian.parse_utc(spec.stop_dispatch_at_utc))
    successor = core.claim_execution(
        spec.key, execution_arn=EXECUTION_2, lease_seconds=300
    )
    assert successor.fence == old.fence + 1
    with pytest.raises(guardian.StaleFence):
        core.request_stop(old)
    receipt = core.request_stop(successor)
    assert receipt is not None
    assert provider.stop_calls == [pod["id"]]


def test_create_dispatch_marker_shortens_lease_and_due_worker_can_preempt():
    values = setup_armed(lease_seconds=200)
    core, _store, provider, _signer, clock, spec, request, old, _arm = values
    reservation = core.reserve_create(old, exact_create_request_bytes=request)
    provider.post_mode = "crash_before_provider"
    with pytest.raises(HardCrash):
        core.dispatch_create(old, reservation, exact_create_request_bytes=request)
    record = core.read_record(spec.key)
    assert record["state"] == "CREATE_DISPATCHED_UNKNOWN"
    assert guardian.parse_utc(record["owner_lease_expires_at_utc"]) == (
        guardian.parse_utc(spec.stop_dispatch_at_utc)
        + timedelta(seconds=guardian.MAX_CONTAINMENT_OWNER_LEASE_SECONDS)
    )
    clock.set(guardian.parse_utc(spec.stop_dispatch_at_utc))
    successor = core.claim_execution(
        spec.key, execution_arn=EXECUTION_2, lease_seconds=300
    )
    assert successor.fence == old.fence + 1
    assert provider.post_entries == 1


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("inventory_complete", False, "complete"),
        ("inventory_unfiltered", False, "filter"),
        ("inventory_account", "another-account", "account"),
        ("inventory_scope", "FILTERED", "complete"),
    ],
)
def test_prearm_requires_complete_unfiltered_account_inventory(field, value, message):
    provider = FakeProvider()
    setattr(provider, field, value)
    core, _store, _provider, _signer, _clock = make_core(provider=provider)
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request)
    with pytest.raises(guardian.ValidationError, match=message):
        core.arm_precreate(token, exact_create_request_bytes=request)


def test_prearm_records_every_returned_id_and_kms_signed_exact_page_hashes():
    pods = [
        {"id": "oldpod0001", "name": "alpha", "desiredStatus": "EXITED"},
        {"id": "oldpod0002", "name": "beta", "desiredStatus": "RUNNING"},
    ]
    provider = FakeProvider(pods)
    core, _store, _provider, signer, _clock = make_core(provider=provider)
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request)
    receipt = core.arm_precreate(token, exact_create_request_bytes=request)
    signer.assert_valid(receipt)
    payload = receipt["payload"]
    assert payload["inventory_count"] == 2
    assert payload["inventory_ids_sha256"] == guardian.sha256_hex(
        guardian.canonical_json_bytes(["oldpod0001", "oldpod0002"])
    )
    assert payload["inventory_projection_sha256"] == guardian.sha256_hex(
        guardian.canonical_json_bytes(
            [
                {"id": "oldpod0001", "name": "alpha"},
                {"id": "oldpod0002", "name": "beta"},
            ]
        )
    )
    assert "inventory_projection" not in payload
    assert payload["inventory_complete"] is True
    assert payload["inventory_unfiltered"] is True


def test_large_arm_receipt_uses_one_32_byte_kms_digest_not_raw_message():
    provider = FakeProvider()
    provider.raw_pages_override = tuple(
        b"[]" for _index in range(guardian.MAX_INVENTORY_PAGES)
    )
    signer = FakeKmsSigner()
    core, _store, _provider, _signer, _clock = make_core(
        provider=provider, signer=signer
    )
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request)
    receipt = core.arm_precreate(token, exact_create_request_bytes=request)
    assert receipt["kms_message_type"] == "DIGEST"
    assert receipt["kms_signing_algorithm"] == "ECDSA_SHA_256"
    assert receipt["signed_payload_byte_count"] > 4_096
    assert len(guardian.canonical_json_bytes(receipt)) < (
        guardian.MAX_EVIDENCE_ITEM_BYTES
    )
    assert all(len(call) == 32 for call in signer.calls)
    signer.assert_valid(receipt)


def test_prearm_uses_inventory_completion_time_not_request_start_time():
    provider = FakeProvider()
    clock = ManualClock()
    real_list = provider.list_all_pods

    def slow_list(account: str):
        result = real_list(account)
        clock.set(BASE + timedelta(seconds=11))
        return result

    provider.list_all_pods = slow_list  # type: ignore[method-assign]
    core, _store, _provider, _signer, _clock = make_core(
        provider=provider, clock=clock
    )
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request)
    with pytest.raises(guardian.AuthorizationUnavailable, match="finished"):
        core.arm_precreate(token, exact_create_request_bytes=request)


def test_large_inventory_is_externalized_and_compact_head_preserves_post_headroom():
    pods = [
        {
            "id": f"p{index:07d}",
            "name": f"unrelated-inventory-entry-{index:07d}-" + "x" * 160,
            "desiredStatus": "EXITED",
        }
        for index in range(2_000)
    ]
    provider = FakeProvider(pods)
    core, _store, _provider, _signer, _clock = make_core(provider=provider)
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request)
    core.arm_precreate(token, exact_create_request_bytes=request)
    record = core.read_record(spec.key)
    assert len(guardian.canonical_json_bytes(record)) <= guardian.MAX_PRECREATE_HEAD_BYTES
    assert "prearm_inventory_projection" not in record
    assert "prearm_inventory_page_sha256" not in record
    assert provider.post_entries == 0


def test_max_inventory_headroom_survives_post_binding_stop_and_terminal_proof():
    pods = [
        {
            "id": f"p{index:07d}",
            "name": f"unrelated-{index:07d}-" + "x" * 500,
            "desiredStatus": "EXITED",
        }
        for index in range(guardian.MAX_INVENTORY_ITEMS)
    ]
    provider = FakeProvider(pods)
    core, store, _provider, _signer, clock = make_core(provider=provider)
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request, lease_seconds=200)
    arm_receipt = core.arm_precreate(token, exact_create_request_bytes=request)
    assert max(store.head_sizes) <= guardian.MAX_PRECREATE_HEAD_BYTES
    assert len(guardian.canonical_json_bytes(arm_receipt)) < (
        guardian.MAX_EVIDENCE_ITEM_BYTES
    )
    clock.set(BASE + timedelta(seconds=10))
    pod = json.loads(response_201(spec.pod_name).body)
    provider.created_pod = pod
    reservation = reserve_and_set_201(core, provider, spec, request, token)
    outcome = core.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.target_bound is True
    assert core.read_record(spec.key)["target_pod_id"] == pod["id"]
    receipt = core.request_stop(token)
    assert receipt is not None
    assert core.read_record(spec.key)["state"] == "TERMINAL_PROVEN"
    assert max(store.head_sizes) < guardian.MAX_LEDGER_ITEM_BYTES
    assert provider.post_entries == 1


def test_cumulative_inventory_raw_bytes_exact_boundary_and_plus_one():
    boundary_page = b"[]" + b" " * (guardian.MAX_INVENTORY_TOTAL_BYTES - 2)
    snapshot = guardian.InventorySnapshot(
        ACCOUNT,
        guardian.INVENTORY_SCOPE,
        True,
        True,
        (boundary_page,),
    )
    evidence = guardian._validate_inventory(  # type: ignore[attr-defined]
        snapshot, provider_account_id=ACCOUNT
    )
    assert evidence.projection == ()

    hostile = replace(snapshot, raw_pages=(boundary_page + b" ",))
    with pytest.raises(guardian.ValidationError, match="cumulative raw byte"):
        guardian._validate_inventory(  # type: ignore[attr-defined]
            hostile, provider_account_id=ACCOUNT
        )


def test_inventory_item_count_exact_boundary_and_plus_one():
    def snapshot(count: int) -> guardian.InventorySnapshot:
        return guardian.InventorySnapshot(
            ACCOUNT,
            guardian.INVENTORY_SCOPE,
            True,
            True,
            (
                guardian.canonical_json_bytes(
                    [
                        {"id": f"p{index:07d}", "name": f"pod-{index}"}
                        for index in range(count)
                    ]
                ),
            ),
        )

    admitted = guardian._validate_inventory(  # type: ignore[attr-defined]
        snapshot(guardian.MAX_INVENTORY_ITEMS), provider_account_id=ACCOUNT
    )
    assert len(admitted.projection) == guardian.MAX_INVENTORY_ITEMS
    with pytest.raises(guardian.ValidationError, match="total Pod item"):
        guardian._validate_inventory(  # type: ignore[attr-defined]
            snapshot(guardian.MAX_INVENTORY_ITEMS + 1),
            provider_account_id=ACCOUNT,
        )


def test_prearm_rejects_existing_exact_name_and_duplicate_ids():
    spec, request = make_spec()
    provider = FakeProvider([{"id": "oldpod0001", "name": spec.pod_name}])
    core, _store, _provider, _signer, _clock = make_core(provider=provider)
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request)
    with pytest.raises(guardian.ValidationError, match="existed"):
        core.arm_precreate(token, exact_create_request_bytes=request)

    provider = FakeProvider()
    provider.raw_pages_override = (
        guardian.canonical_json_bytes(
            [
                {"id": "oldpod0001", "name": "alpha"},
                {"id": "oldpod0001", "name": "beta"},
            ]
        ),
    )
    core, _store, _provider, _signer, _clock = make_core(provider=provider)
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request)
    with pytest.raises(guardian.ValidationError, match="duplicate"):
        core.arm_precreate(token, exact_create_request_bytes=request)


def test_request_hash_and_name_checked_before_inventory_or_reservation():
    core, _store, provider, _signer, _clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request)
    with pytest.raises(guardian.ValidationError, match="SHA-256"):
        core.arm_precreate(token, exact_create_request_bytes=request + b" ")
    assert provider.list_calls == 0


@pytest.mark.parametrize(
    ("field", "hostile_value"),
    [
        ("cloudType", "COMMUNITY"),
        ("containerDiskInGb", 49),
        ("containerDiskInGb", True),
        ("gpuCount", 2),
        ("gpuTypeIds", ["NVIDIA RTX A6000"]),
        ("imageName", "attacker/image:latest"),
        ("interruptible", True),
        ("locked", True),
        ("networkVolumeId", "hfelwlp1va"),
        ("ports", ["22/tcp", "8888/http"]),
        ("volumeEncrypted", False),
        ("volumeInGb", 19),
        ("volumeMountPath", "/root"),
    ],
)
def test_hostile_create_body_drift_rejected_before_store_inventory_or_post(
    field, hostile_value
):
    core, store, provider, _signer, _clock = make_core()
    spec, request = make_spec()
    value = json.loads(request)
    value[field] = hostile_value
    hostile = guardian.canonical_json_bytes(value)
    hostile_spec = replace(
        spec, exact_create_request_sha256=guardian.sha256_hex(hostile)
    )
    with pytest.raises(guardian.ValidationError, match=f"field {field} mismatch"):
        core.register_authorization(
            hostile_spec, exact_create_request_bytes=hostile
        )
    assert store.put_calls == 0
    assert provider.list_calls == 0
    assert provider.post_entries == 0


def test_request_unknown_field_or_extra_environment_key_rejected_before_store():
    for mutate in (
        lambda value: value.update({"apiKey": "must-not-be-admitted"}),
        lambda value: value["env"].update({"RUNPOD_API_KEY": "secret"}),
    ):
        core, store, provider, _signer, _clock = make_core()
        spec, request = make_spec()
        value = json.loads(request)
        mutate(value)
        hostile = guardian.canonical_json_bytes(value)
        hostile_spec = replace(
            spec, exact_create_request_sha256=guardian.sha256_hex(hostile)
        )
        with pytest.raises(guardian.ValidationError, match="keyset"):
            core.register_authorization(
                hostile_spec, exact_create_request_bytes=hostile
            )
        assert store.put_calls == 0
        assert provider.list_calls == 0
        assert provider.post_entries == 0


def test_injected_secret_guard_rejects_exact_authorized_bytes_before_store():
    sentinel = b"DO_NOT_PERSIST_RUNTIME_SECRET"
    guard = FakeSecretGuard((sentinel,))
    core, store, provider, _signer, _clock = make_core(secret_guard=guard)
    spec, request = make_spec()
    value = json.loads(request)
    public_key = value["env"]["PUBLIC_KEY"] + " " + sentinel.decode("ascii")
    value["env"]["PUBLIC_KEY"] = public_key
    hostile = guardian.canonical_json_bytes(value)
    hostile_spec = replace(
        spec,
        exact_create_request_sha256=guardian.sha256_hex(hostile),
        dedicated_public_key_sha256=guardian.sha256_hex(public_key.encode("utf-8")),
    )
    with pytest.raises(guardian.ValidationError, match="SECRET_GUARD"):
        core.register_authorization(
            hostile_spec, exact_create_request_bytes=hostile
        )
    assert guard.calls == [guardian.sha256_hex(hostile)]
    assert store.put_calls == 0
    assert provider.list_calls == 0
    assert provider.post_entries == 0


def test_source_image_digest_and_public_key_hash_are_bound_in_arm_and_binding_receipts():
    values = bind_success_fixture()
    core, _store, _provider, signer, _clock, spec, _request, _token, _arm, _res, _pod = values
    record = core.read_record(spec.key)
    for name in ("arm", "binding"):
        receipt = core.read_receipt(spec.key, name)
        payload = receipt["payload"]
        assert payload["source_commit_sha"] == spec.source_commit_sha
        assert payload["oci_image_digest"] == spec.oci_image_digest
        assert payload["image_name"] == spec.image_name
        assert (
            payload["dedicated_public_key_sha256"]
            == spec.dedicated_public_key_sha256
        )
        signer.assert_valid(receipt)


def test_reservation_is_idempotent_and_exists_before_dispatch():
    core, _store, provider, signer, _clock, spec, request, token, _arm = setup_armed()
    first = core.reserve_create(token, exact_create_request_bytes=request)
    second = core.reserve_create(token, exact_create_request_bytes=request)
    assert second == first
    assert provider.post_entries == 0
    record = core.read_record(spec.key)
    assert record["create_dispatch_count"] == 0
    signer.assert_valid(core.read_receipt(spec.key, "create_reservation"))


def test_create_reservation_and_dispatch_are_forbidden_outside_window():
    values = setup_armed()
    core, _store, provider, _signer, clock, spec, request, token, _arm = values
    clock.set(BASE + timedelta(seconds=51))
    with pytest.raises(guardian.AuthorizationUnavailable, match="window"):
        core.reserve_create(token, exact_create_request_bytes=request)
    assert provider.post_entries == 0


def test_concurrent_dispatch_commits_one_marker_and_calls_transport_once():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    reservation = reserve_and_set_201(core, provider, spec, request, token)
    provider.created_pod = json.loads(provider.post_response.body)
    barrier = threading.Barrier(16)
    outcomes: list[guardian.CreateOutcome] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        try:
            result = core.dispatch_create(
                token, reservation, exact_create_request_bytes=request
            )
            with lock:
                outcomes.append(result)
        except BaseException as error:
            with lock:
                errors.append(error)

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert len(outcomes) == 1
    assert len(errors) == 15
    assert all(isinstance(error, guardian.CreateAlreadyDispatched) for error in errors)
    assert provider.post_entries == 1
    assert provider.provider_create_commits == 1
    assert core.read_record(spec.key)["create_dispatch_count"] == 1


def test_crash_after_dispatch_marker_before_provider_send_is_safe_loss_no_retry():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    reservation = core.reserve_create(token, exact_create_request_bytes=request)
    provider.post_mode = "crash_before_provider"
    with pytest.raises(HardCrash):
        core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert provider.post_entries == 1
    assert provider.provider_create_commits == 0
    assert core.read_record(spec.key)["state"] == "CREATE_DISPATCHED_UNKNOWN"
    with pytest.raises(guardian.CreateAlreadyDispatched):
        core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert provider.post_entries == 1
    result = core.reconcile_ambiguous_create(token)
    assert result.status == "AMBIGUOUS_NO_TARGET_YET"
    assert provider.post_entries == 1


def test_dispatch_marker_crossing_window_end_is_safe_loss_without_transport_call():
    clock = ManualClock()
    signer = MarkerDelayingSigner(clock)
    values = setup_armed(clock=clock, signer=signer)
    core, _store, provider, _signer, _clock, spec, request, token, _arm = values
    reservation = core.reserve_create(token, exact_create_request_bytes=request)
    provider.post_response = response_201(spec.pod_name)
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.status == "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED"
    assert provider.post_entries == 0
    assert core.read_record(spec.key)["create_dispatch_count"] == 1
    assert provider.provider_create_commits == 0
    assert core.read_record(spec.key)["state"] == "CREATE_AMBIGUOUS"
    with pytest.raises(guardian.CreateAlreadyDispatched):
        core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert provider.post_entries == 0
    result = core.reconcile_ambiguous_create(token)
    assert result.status == "AMBIGUOUS_NO_TARGET_YET"
    assert provider.post_entries == 0


def test_transport_loss_after_provider_commit_reconciles_without_post_retry():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    candidate = json.loads(response_201(spec.pod_name).body)
    provider.created_pod = candidate
    provider.post_mode = "ambiguous_after_provider"
    reservation = core.reserve_create(token, exact_create_request_bytes=request)
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.status == "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED"
    recovered = core.reconcile_ambiguous_create(token)
    assert recovered.target_bound is True
    assert recovered.launch_admitted is False
    assert recovered.pod_id == candidate["id"]
    assert provider.post_entries == 1


def test_crash_reconciliation_binds_unique_new_exact_name_without_birth_fields():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    candidate = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "desiredStatus": "RUNNING",
    }
    provider.created_pod = candidate
    provider.post_mode = "ambiguous_after_provider"
    reservation = core.reserve_create(token, exact_create_request_bytes=request)
    outcome = core.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.status == "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED"
    recovered = core.reconcile_ambiguous_create(token)
    assert recovered.target_bound is True
    assert recovered.pod_id == candidate["id"]
    record = core.read_record(spec.key)
    assert record["provider_birth_times_utc"] == {}
    assert record["target_binding_provenance"].endswith("NO_BIRTH")
    receipt = core.supervise_once(token)
    assert receipt is not None
    assert provider.stop_calls == [candidate["id"]]
    assert core.read_record(spec.key)["state"] == "TERMINAL_PROVEN"
    assert provider.post_entries == 1


def test_reconciliation_untrusted_surrogate_status_cannot_block_exact_id_stop():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    provider.post_response = guardian.HttpResponse(500, b"{}", guardian.CREATE_ENDPOINT)
    reservation = core.reserve_create(token, exact_create_request_bytes=request)
    core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    candidate = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "createdAt": guardian.iso_utc(BASE + timedelta(seconds=10)),
        "desiredStatus": "\ud800",
    }
    provider.pods[candidate["id"]] = candidate
    inventory_raw = (
        json.dumps([candidate], sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")
    provider.raw_pages_override = (inventory_raw,)
    recovered = core.reconcile_ambiguous_create(token)
    assert recovered.pod_id == candidate["id"]
    provider.raw_pages_override = None
    terminal = core.supervise_once(token)
    assert terminal is not None
    assert provider.stop_calls == [candidate["id"]]


def test_strict_201_binds_exact_id_but_never_admits_without_live_get():
    values = bind_pending_fixture()
    core, _store, provider, signer, _clock, spec, _request, token, _arm, _res, pod = values
    record = core.read_record(spec.key)
    assert record["target_pod_id"] == pod["id"]
    assert record["launch_admitted"] is False
    assert record["launch_admission_status"] == "PENDING_EXACT_GET"
    assert provider.post_entries == 1
    assert provider.get_calls == []
    signer.assert_valid(core.read_receipt(spec.key, "binding"))

    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is True
    assert provider.get_calls == [pod["id"]]
    record = core.read_record(spec.key)
    assert record["launch_admitted"] is True
    assert record["launch_admission_status"] == "ADMITTED"
    signer.assert_valid(receipt)


def test_strict_201_binds_exact_id_and_admits_launch_with_signed_receipt():
    values = bind_success_fixture()
    core, _store, provider, signer, _clock, spec, _request, _token, _arm, _res, pod = values
    record = core.read_record(spec.key)
    assert record["target_pod_id"] == pod["id"]
    assert record["launch_admitted"] is True
    assert provider.post_entries == 1
    signer.assert_valid(core.read_receipt(spec.key, "binding"))


def test_admission_signing_crossing_stop_dispatch_is_denied_and_stopped():
    clock = ManualClock()
    signer = AdmissionDelayingSigner(clock)
    values = setup_armed(clock=clock, signer=signer)
    core, _store, provider, _signer, _clock, spec, request, token, _arm = values
    pod = json.loads(response_201(spec.pod_name).body)
    provider.created_pod = pod
    reservation = reserve_and_set_201(core, provider, spec, request, token)
    outcome = core.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.target_bound is True

    clock.set(BASE + timedelta(seconds=12))
    token = core.heartbeat(token, expected_sequence=0, lease_seconds=300)
    denial = core.verify_post_bind_launch_admission(token)
    assert clock.now() == guardian.parse_utc(spec.stop_dispatch_at_utc)
    assert denial["payload"]["launch_admitted"] is False
    assert denial["payload"]["launch_admission_valid_until_utc"] == (
        spec.stop_dispatch_at_utc
    )
    assert "LAUNCH_ADMISSION_SIGNED_AT_OR_AFTER_STOP_DISPATCH" in denial[
        "payload"
    ]["validation_errors"]
    record = core.read_record(spec.key)
    assert record["launch_admission_status"] == "DENIED"
    assert record["launch_admitted"] is False
    signer.assert_valid(denial)

    stop_receipt = core.supervise_once(token)
    assert stop_receipt is not None
    assert provider.stop_calls == [pod["id"]]


def test_kms_outage_after_provider_commit_cannot_block_exact_id_binding_or_stop():
    signer = FailingKmsSigner(fail_from_call=6)
    values = setup_armed(signer=signer)
    core, _store, provider, _signer, _clock, spec, request, token, _arm = values
    pod = json.loads(response_201(spec.pod_name).body)
    provider.created_pod = pod
    reservation = reserve_and_set_201(core, provider, spec, request, token)
    outcome = core.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.target_bound is True
    record = core.read_record(spec.key)
    assert record["target_pod_id"] == pod["id"]
    assert record["binding_receipt_status"] == "PENDING_KMS_EVIDENCE"
    assert "binding" not in record["receipts"]
    with pytest.raises(OSError, match="KMS outage"):
        core.supervise_once(token)
    assert provider.stop_calls == [pod["id"]]
    assert provider.pods[pod["id"]]["desiredStatus"] == "EXITED"

    signer.fail_from_call = None
    receipt = core.observe_terminal(token)
    assert receipt is not None
    assert receipt["payload"]["terminal_provider_proof"] is True
    assert core.read_record(spec.key)["state"] == "TERMINAL_PROVEN"


def _mutate_path(value: dict[str, Any], path: tuple[str, ...], hostile: Any) -> None:
    target: dict[str, Any] = value
    for key in path[:-1]:
        target = target[key]
    if hostile is MISSING:
        target.pop(path[-1], None)
    else:
        target[path[-1]] = hostile


@pytest.mark.parametrize(
    ("path", "hostile", "error_fragment"),
    [
        (("id",), "attacker9999", "EXACT_IDENTITY"),
        (("name",), "wrong-name", "EXACT_IDENTITY"),
        (("desiredStatus",), "EXITED", "NOT_RUNNING"),
        (("imageName",), "attacker/image:latest", "IMAGE_MISMATCH"),
        (("gpuCount",), False, "GPU_COUNT_MISMATCH"),
        (("gpuCount",), 2, "GPU_COUNT_MISMATCH"),
        (("machine", "gpuTypeId"), "NVIDIA RTX A6000", "MACHINE_GPU_TYPE"),
        (("machine", "secureCloud"), False, "NOT_SECURE_CLOUD"),
        (("machine", "cloudType"), "COMMUNITY", "MACHINE_CLOUD_TYPE"),
        (("cloudType",), "COMMUNITY", "CONFLICTING_CLOUD_TYPE"),
        (("gpu", "id"), "NVIDIA RTX A6000", "CONFLICTING_GPU_ID"),
        (("gpu", "displayName"), "RTX A6000", "CONFLICTING_GPU_DISPLAY"),
        (("gpu", "cloudType"), "COMMUNITY", "GPU_CLOUD_TYPE"),
        (("gpu", "secureCloud"), False, "GPU_SECURE_CLOUD"),
        (("gpuTypeIds",), ["NVIDIA RTX A6000"], "CONFLICTING_GPU_TYPE_IDS"),
        (("volumeInGb",), 19, "volumeInGb_MISMATCH"),
        (("containerDiskInGb",), 49, "containerDiskInGb_MISMATCH"),
        (("volumeMountPath",), "/root", "VOLUME_MOUNT_PATH"),
        (("volumeEncrypted",), False, "VOLUME_NOT_ENCRYPTED"),
        (("networkVolume",), {"id": "forbidden"}, "FORBIDDEN_NETWORK_VOLUME"),
        (("networkVolumeId",), "forbidden", "FORBIDDEN_NETWORK_VOLUME"),
        (("interruptible",), True, "interruptible_MISMATCH"),
        (("interruptible",), MISSING, "interruptible_MISMATCH"),
        (("locked",), True, "locked_MISMATCH"),
        (("ports",), ["22/tcp", "8888/http"], "PORTS_MISMATCH"),
        (("portMappings",), {"22": 22022, "8888": 8888}, "PORT_MAPPING"),
        (("portMappings", "22"), False, "EXTERNAL_SSH_PORT_INVALID"),
        (("env",), {"PUBLIC_KEY": DEDICATED_PUBLIC_KEY, "SECRET": "x"}, "ENVIRONMENT_KEYSET"),
        (("env", "PUBLIC_KEY"), "ssh-ed25519 attacker attacker", "PUBLIC_KEY"),
        (("lastStartedAt",), MISSING, "START_TIME_MISSING"),
        (("lastStartedAt",), guardian.iso_utc(BASE - timedelta(seconds=1)), "BIRTH_OUTSIDE"),
        (("createdAt",), guardian.iso_utc(BASE - timedelta(seconds=1)), "BIRTH_OUTSIDE"),
    ],
)
def test_live_exact_get_requires_every_authoritative_invariant(
    path, hostile, error_fragment
):
    values = bind_pending_fixture()
    core, _store, provider, signer, _clock, spec, _request, token, _arm, _res, pod = values
    _mutate_path(provider.pods[pod["id"]], path, hostile)
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is False
    assert any(
        error_fragment in error
        for error in receipt["payload"]["validation_errors"]
    )
    record = core.read_record(spec.key)
    assert record["launch_admitted"] is False
    assert record["launch_admission_status"] == "DENIED"
    signer.assert_valid(receipt)


@pytest.mark.parametrize(
    ("cost", "adjusted", "admitted", "error_fragment"),
    [
        (0.50, None, True, None),
        (0, None, True, None),
        (True, None, False, "NOT_JSON_NUMBER"),
        (1, None, False, "EXCEEDS_AUTHORIZED_CEILING"),
        (0.500001, None, False, "EXCEEDS_AUTHORIZED_CEILING"),
        (0.10, 0.75, False, "adjustedCostPerHr_EXCEEDS"),
        (None, None, False, "AUTHORITATIVE_RATE_MISSING"),
    ],
)
def test_live_rate_fields_are_all_finite_numeric_and_at_or_below_ceiling(
    cost, adjusted, admitted, error_fragment
):
    values = bind_pending_fixture()
    core, _store, provider, _signer, _clock, spec, _request, token, _arm, _res, pod = values
    provider.pods[pod["id"]]["costPerHr"] = cost
    provider.pods[pod["id"]]["adjustedCostPerHr"] = adjusted
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is admitted
    assert core.read_record(spec.key)["launch_admitted"] is admitted
    if error_fragment is not None:
        assert any(
            error_fragment in error
            for error in receipt["payload"]["validation_errors"]
        )
    else:
        assert receipt["payload"]["live_get_semantic_projection"]["pod"][
            "observed_rates"
        ]["costPerHr"] in {"5e-1", "0"}


@pytest.mark.parametrize(
    ("path", "value", "error_fragment"),
    [
        (("machine", "adjustedCostPerHr"), 0.75, "EXCEEDS"),
        (("gpu", "costPerHour"), True, "NOT_JSON_NUMBER"),
        (("billing", "costPerHr"), 0.10, "UNRECOGNIZED_LOCATION"),
        (("machine", "hiddenAdjustedCostPerHr"), 0.10, "UNRECOGNIZED_RATE"),
    ],
)
def test_live_get_rejects_hidden_or_conflicting_rate_fields(
    path, value, error_fragment
):
    values = bind_pending_fixture()
    core, _store, provider, _signer, _clock, _spec, _request, token, _arm, _res, pod = values
    target = provider.pods[pod["id"]]
    for key in path[:-1]:
        target = target.setdefault(key, {})
    target[path[-1]] = value
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is False
    assert any(
        error_fragment in error
        for error in receipt["payload"]["validation_errors"]
    )


def test_live_nan_rate_is_rejected_from_exact_raw_json():
    values = bind_pending_fixture()
    core, _store, provider, _signer, _clock, spec, _request, token, _arm, _res, pod = values
    hostile = deepcopy(provider.pods[pod["id"]])
    hostile["costPerHr"] = float("nan")
    provider.get_response_override = guardian.HttpResponse(
        200,
        json.dumps(hostile, separators=(",", ":"), allow_nan=True).encode("utf-8"),
        f"{guardian.CREATE_ENDPOINT}/{pod['id']}",
    )
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is False
    assert receipt["payload"]["validation_errors"] == ["PROVIDER_JSON_INVALID"]


@pytest.mark.parametrize("field", guardian.PROVIDER_RATE_FIELDS)
@pytest.mark.parametrize(
    ("raw_token", "admitted", "error_fragment"),
    [
        ("0.5", True, None),
        ("0.50000000000000000", True, None),
        ("5e-1", True, None),
        ("0.50000000000000001", False, "EXCEEDS_AUTHORIZED_CEILING"),
        ("5.0000000000000001e-1", False, "EXCEEDS_AUTHORIZED_CEILING"),
        ("1e999999", False, "EXCEEDS_AUTHORIZED_CEILING"),
        ("1e-999999", False, "EXPONENT_OUT_OF_RANGE"),
        ("-0", False, "NEGATIVE_ZERO"),
        ("-0.0", False, "NEGATIVE_ZERO"),
        ("false", False, "NOT_JSON_NUMBER"),
        ("NaN", False, "PROVIDER_JSON_INVALID"),
    ],
)
def test_exact_raw_rate_tokens_never_round_across_the_ceiling(
    field, raw_token, admitted, error_fragment
):
    values = bind_pending_fixture()
    core, _store, provider, _signer, _clock, _spec, _request, token, _arm, _res, pod = values
    live = deepcopy(provider.pods[pod["id"]])
    live["costPerHr"] = None
    live["adjustedCostPerHr"] = None
    live[field] = 0.35
    raw = guardian.canonical_json_bytes(live).replace(
        f'"{field}":0.35'.encode("ascii"),
        f'"{field}":{raw_token}'.encode("ascii"),
        1,
    )
    provider.get_response_override = guardian.HttpResponse(
        200, raw, f"{guardian.CREATE_ENDPOINT}/{pod['id']}"
    )
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is admitted
    if error_fragment is None:
        assert receipt["payload"]["live_get_semantic_projection"]["pod"][
            "observed_rates"
        ][field] == "5e-1"
    else:
        assert any(
            error_fragment in error
            for error in receipt["payload"]["validation_errors"]
        )


def test_live_get_accepts_whitespace_and_key_order_but_persists_only_hash_and_projection():
    values = bind_pending_fixture()
    core, _store, provider, _signer, _clock, _spec, _request, token, _arm, _res, pod = values
    raw = json.dumps(provider.pods[pod["id"]], indent=2, sort_keys=False).encode("utf-8")
    provider.get_response_override = guardian.HttpResponse(
        200, raw, f"{guardian.CREATE_ENDPOINT}/{pod['id']}"
    )
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is True
    assert receipt["payload"]["live_get_exact_body_sha256"] == guardian.sha256_hex(raw)
    assert receipt["payload"]["live_get_exact_body_byte_count"] == len(raw)
    assert "live_get_exact_body_base64" not in receipt["payload"]
    projection = receipt["payload"]["live_get_semantic_projection"]
    assert projection["schema_version"] == (
        guardian.LIVE_GET_SEMANTIC_PROJECTION_SCHEMA
    )
    assert receipt["payload"]["live_get_semantic_projection_sha256"] == (
        guardian.sha256_hex(guardian.canonical_json_bytes(projection))
    )


@pytest.mark.parametrize(
    ("echo_fragment", "encoded_secret"),
    [
        (
            json.dumps(ECHOED_API_SECRET).encode("ascii"),
            ECHOED_API_SECRET.encode("ascii"),
        ),
        (
            f'"{UNICODE_ESCAPED_SECRET}"'.encode("ascii"),
            UNICODE_ESCAPED_SECRET.encode("ascii"),
        ),
        (
            json.dumps(PERCENT_ENCODED_SECRET).encode("ascii"),
            PERCENT_ENCODED_SECRET.encode("ascii"),
        ),
        (
            json.dumps(BASE32_ENCODED_SECRET).encode("ascii"),
            BASE32_ENCODED_SECRET.encode("ascii"),
        ),
        (
            json.dumps(f"Bearer {ECHOED_API_SECRET}").encode("ascii"),
            f"Bearer {ECHOED_API_SECRET}".encode("ascii"),
        ),
        (
            json.dumps(list(FRAGMENTED_SECRET_PARTS)).encode("ascii"),
            "".join(FRAGMENTED_SECRET_PARTS).encode("ascii"),
        ),
    ],
)
def test_live_raw_echo_encodings_are_hash_bound_but_never_durably_reversible(
    echo_fragment, encoded_secret
):
    values = bind_pending_fixture()
    core, store, provider, signer, _clock, _spec, _request, token, _arm, _res, pod = values
    baseline = guardian.canonical_json_bytes(provider.pods[pod["id"]]).rstrip(b"\n")
    raw = baseline[:-1] + b',"providerEcho":' + echo_fragment + b"}\n"
    provider.get_response_override = guardian.HttpResponse(
        200, raw, f"{guardian.CREATE_ENDPOINT}/{pod['id']}"
    )

    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is True
    assert receipt["payload"]["live_get_exact_body_sha256"] == guardian.sha256_hex(
        raw
    )
    assert receipt["payload"]["live_get_exact_body_byte_count"] == len(raw)
    assert "live_get_exact_body_base64" not in receipt["payload"]
    projection = receipt["payload"]["live_get_semantic_projection"]
    assert b"providerEcho" not in guardian.canonical_json_bytes(projection)
    signer.assert_valid(receipt)
    assert_not_durably_reversible(
        store,
        raw,
        base64.b64encode(raw),
        ECHOED_API_SECRET.encode("ascii"),
        encoded_secret,
        *(part.encode("ascii") for part in FRAGMENTED_SECRET_PARTS),
    )


@pytest.mark.parametrize(
    ("metadata_field", "metadata_value", "admitted", "fixed_error"),
    [
        (
            "content_type",
            f"application/json; authorization=Bearer {ECHOED_API_SECRET}",
            True,
            None,
        ),
        (
            "effective_url",
            f"{guardian.CREATE_ENDPOINT}/newpod1234#{ECHOED_API_SECRET}",
            False,
            "LIVE_GET_EFFECTIVE_URL_MISMATCH",
        ),
        (
            "content_encoding",
            f"identity,Bearer {ECHOED_API_SECRET}",
            False,
            "LIVE_GET_CONTENT_ENCODING_MISMATCH",
        ),
    ],
)
def test_provider_controlled_http_metadata_is_never_persisted_as_text(
    metadata_field, metadata_value, admitted, fixed_error
):
    values = bind_pending_fixture()
    core, store, provider, _signer, _clock, _spec, _request, token, _arm, _res, pod = values
    response_values = {
        "status_code": 200,
        "body": guardian.canonical_json_bytes(provider.pods[pod["id"]]),
        "effective_url": f"{guardian.CREATE_ENDPOINT}/{pod['id']}",
        "content_type": "application/json",
        "content_encoding": "identity",
    }
    response_values[metadata_field] = metadata_value
    provider.get_response_override = guardian.HttpResponse(**response_values)

    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is admitted
    assert receipt["payload"]["validation_errors"] == (
        [] if fixed_error is None else [fixed_error]
    )
    assert f"live_get_{metadata_field}" not in receipt["payload"]
    assert f"live_get_{metadata_field}_sha256" in receipt["payload"]
    assert_not_durably_reversible(
        store,
        metadata_value.encode("ascii"),
        ECHOED_API_SECRET.encode("ascii"),
    )


def test_live_get_duplicate_key_marker_is_rejected_without_durable_echo():
    values = bind_pending_fixture()
    core, store, provider, _signer, _clock, _spec, _request, token, _arm, _res, pod = values
    marker = b"PROVIDER_PRIVATE_DUPLICATE_FIELD_7Q9M2X"
    baseline = guardian.canonical_json_bytes(provider.pods[pod["id"]]).rstrip(b"\n")
    raw = baseline[:-1] + b',"' + marker + b'":1,"' + marker + b'":2}\n'
    provider.get_response_override = guardian.HttpResponse(
        200, raw, f"{guardian.CREATE_ENDPOINT}/{pod['id']}"
    )
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is False
    assert receipt["payload"]["validation_errors"] == [
        "PROVIDER_JSON_DUPLICATE_KEY"
    ]
    assert_not_durably_reversible(store, marker, raw, base64.b64encode(raw))


def test_live_get_invalid_timestamp_marker_is_rejected_without_durable_echo():
    values = bind_pending_fixture()
    core, store, provider, _signer, _clock, _spec, _request, token, _arm, _res, pod = values
    marker = "PROVIDER_PRIVATE_TIMESTAMP_MARKER_7Q9M2X"
    hostile = deepcopy(provider.pods[pod["id"]])
    hostile["lastStartedAt"] = marker
    raw = guardian.canonical_json_bytes(hostile)
    provider.get_response_override = guardian.HttpResponse(
        200, raw, f"{guardian.CREATE_ENDPOINT}/{pod['id']}"
    )

    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is False
    assert receipt["payload"]["validation_errors"] == [
        "PROVIDER_TIMESTAMP_INVALID"
    ]
    assert_not_durably_reversible(
        store,
        marker.encode("ascii"),
        raw,
        base64.b64encode(raw),
    )


@pytest.mark.parametrize(
    "raw",
    [
        b'{"PROVIDER_PRIVATE_UTF8_MARKER_7Q9M2X":"\xff"}',
        b'{"PROVIDER_PRIVATE_BODY_MARKER_7Q9M2X":',
    ],
)
def test_live_get_malformed_body_marker_is_rejected_without_durable_echo(raw):
    values = bind_pending_fixture()
    core, store, provider, _signer, _clock, _spec, _request, token, _arm, _res, pod = values
    provider.get_response_override = guardian.HttpResponse(
        200, raw, f"{guardian.CREATE_ENDPOINT}/{pod['id']}"
    )

    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is False
    assert receipt["payload"]["validation_errors"] == ["PROVIDER_JSON_INVALID"]
    marker = raw.split(b'"', 2)[1]
    assert_not_durably_reversible(store, marker, raw, base64.b64encode(raw))


def test_live_get_transport_exception_class_marker_is_never_persisted():
    values = bind_pending_fixture()
    core, store, provider, _signer, _clock, _spec, _request, token, _arm, _res, _pod = values
    marker = "PROVIDER_PRIVATE_EXCEPTION_CLASS_7Q9M2X"
    exception_type = type(marker, (Exception,), {})

    def hostile_get(_account: str, _pod_id: str):
        raise exception_type("provider-controlled exception body marker")

    provider.get_pod = hostile_get  # type: ignore[method-assign]
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is False
    assert receipt["payload"]["validation_errors"] == [
        "LIVE_GET_TRANSPORT_PROVIDER_TRANSPORT_EXCEPTION"
    ]
    assert_not_durably_reversible(
        store,
        marker.encode("ascii"),
        b"provider-controlled exception body marker",
    )


def test_create_transport_exception_marker_is_never_persisted():
    core, store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    marker = "PROVIDER_PRIVATE_CREATE_EXCEPTION_7Q9M2X"
    exception_type = type(marker, (Exception,), {})
    reservation = core.reserve_create(token, exact_create_request_bytes=request)

    def hostile_post(_account: str, _endpoint: str, _body: bytes):
        provider.post_entries += 1
        raise exception_type("provider-controlled CREATE exception body marker")

    provider.post_create = hostile_post  # type: ignore[method-assign]
    outcome = core.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.status == "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED"
    assert outcome.target_bound is False
    assert core.read_record(spec.key)["create_ambiguous_reason"] == (
        "TRANSPORT_PROVIDER_TRANSPORT_EXCEPTION"
    )
    assert_not_durably_reversible(
        store,
        marker.encode("ascii"),
        b"provider-controlled CREATE exception body marker",
    )


def test_stop_transport_exception_marker_is_never_persisted():
    values = bind_success_fixture()
    core, store, provider, _signer, _clock, spec, _request, token, _arm, _res, _pod = values
    marker = "PROVIDER_PRIVATE_STOP_EXCEPTION_7Q9M2X"
    exception_type = type(marker, (Exception,), {})

    def hostile_stop(_account: str, _pod_id: str):
        raise exception_type("provider-controlled STOP exception body marker")

    provider.stop_pod = hostile_stop  # type: ignore[method-assign]
    assert core.request_stop(token) is None
    result = core.read_record(spec.key)["stop_result_history"][-1]
    assert result["outcome"] == "AMBIGUOUS_EXCEPTION"
    assert result["error_class"] == "PROVIDER_TRANSPORT_EXCEPTION"
    assert_not_durably_reversible(
        store,
        marker.encode("ascii"),
        b"provider-controlled STOP exception body marker",
    )


@pytest.mark.parametrize(
    "response",
    [
        guardian.HttpResponse(201, b"{}", f"{guardian.CREATE_ENDPOINT}/newpod1234"),
        guardian.HttpResponse(200, b"{}", f"{guardian.CREATE_ENDPOINT}/wrongpod99"),
        guardian.HttpResponse(
            200,
            b"{}",
            f"{guardian.CREATE_ENDPOINT}/newpod1234",
            content_type="text/html",
        ),
        guardian.HttpResponse(
            200,
            b"{}",
            f"{guardian.CREATE_ENDPOINT}/newpod1234",
            content_encoding="gzip",
        ),
    ],
)
def test_live_get_requires_exact_http_envelope(response):
    values = bind_pending_fixture()
    core, _store, provider, _signer, _clock, spec, _request, token, _arm, _res, _pod = values
    provider.get_response_override = response
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is False
    assert core.read_record(spec.key)["launch_admission_status"] == "DENIED"


def test_oversized_live_get_metadata_is_hash_only_and_cannot_block_stop_recovery():
    values = bind_pending_fixture()
    core, _store, provider, signer, _clock, spec, _request, token, _arm, _res, pod = values
    raw = guardian.canonical_json_bytes(provider.pods[pod["id"]])
    provider.get_response_override = guardian.HttpResponse(
        200,
        raw,
        f"{guardian.CREATE_ENDPOINT}/{pod['id']}",
        content_type="application/json;" + "x" * 100_000,
    )
    denial = core.verify_post_bind_launch_admission(token)
    assert denial["payload"]["launch_admitted"] is False
    assert "live_get_content_type" not in denial["payload"]
    assert "live_get_content_type_retained" not in denial["payload"]
    assert denial["payload"]["live_get_content_type_byte_count"] > (
        guardian.MAX_HTTP_METADATA_BYTES
    )
    assert len(guardian.canonical_json_bytes(denial)) < guardian.MAX_EVIDENCE_ITEM_BYTES
    signer.assert_valid(denial)

    with pytest.raises(guardian.ValidationError, match="CONTENT_TYPE_TOO_LARGE"):
        core.supervise_once(token)
    assert provider.stop_calls == [pod["id"]]
    provider.get_response_override = None
    terminal = core.observe_terminal(token)
    assert terminal is not None
    assert core.read_record(spec.key)["state"] == "TERMINAL_PROVEN"


def test_live_get_secret_guard_scans_exact_raw_provider_bytes():
    guard = FakeSecretGuard((b"forbiddenRaw",))
    values = setup_armed(secret_guard=guard)
    core, _store, provider, _signer, _clock, spec, request, token, _arm = values
    pod = json.loads(response_201(spec.pod_name).body)
    provider.created_pod = pod
    reservation = reserve_and_set_201(core, provider, spec, request, token)
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.launch_admitted is False
    provider.pods[pod["id"]]["providerNote"] = "forbiddenRaw"
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is False
    assert "SECRET_GUARD" in receipt["payload"]["validation_errors"][0]
    assert "live_get_exact_body_retained" not in receipt["payload"]
    assert "live_get_exact_body_base64" not in receipt["payload"]


def test_failed_live_admission_is_containment_only_and_stops_exact_id():
    values = bind_pending_fixture()
    core, _store, provider, _signer, _clock, _spec, _request, token, _arm, _res, pod = values
    provider.pods[pod["id"]]["adjustedCostPerHr"] = 0.75
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is False
    terminal = core.supervise_once(token)
    assert terminal is not None
    assert provider.stop_calls == [pod["id"]]


def test_concurrent_live_admission_get_has_one_durable_read_marker():
    values = bind_pending_fixture()
    core, _store, provider, _signer, _clock, _spec, _request, token, _arm, _res, pod = values
    entered = threading.Event()
    release = threading.Event()
    real_get = provider.get_pod

    def blocking_get(account: str, pod_id: str):
        entered.set()
        assert release.wait(timeout=10)
        return real_get(account, pod_id)

    provider.get_pod = blocking_get  # type: ignore[method-assign]
    results: list[dict[str, Any]] = []
    thread = threading.Thread(
        target=lambda: results.append(core.verify_post_bind_launch_admission(token))
    )
    thread.start()
    assert entered.wait(timeout=5)
    with pytest.raises(guardian.NotReady, match="already in flight"):
        core.verify_post_bind_launch_admission(token)
    release.set()
    thread.join(timeout=10)
    assert results[0]["payload"]["launch_admitted"] is True
    assert provider.get_calls == [pod["id"]]


def test_crash_after_live_get_marker_never_admits_and_containment_still_runs():
    values = bind_pending_fixture()
    core, _store, provider, _signer, _clock, spec, _request, token, _arm, _res, pod = values

    def crash_get(_account: str, _pod_id: str):
        raise HardCrash("worker died after durable live-GET marker")

    provider.get_pod = crash_get  # type: ignore[method-assign]
    with pytest.raises(HardCrash):
        core.verify_post_bind_launch_admission(token)
    record = core.read_record(spec.key)
    assert record["launch_admission_status"] == "VERIFYING_EXACT_GET"
    assert record["launch_admitted"] is False
    with pytest.raises(HardCrash):
        core.supervise_once(token)
    assert provider.stop_calls == [pod["id"]]


@pytest.mark.parametrize(
    ("changes", "error_fragment"),
    [
        ({"name": "provider-normalized-name"}, "NAME_MISMATCH"),
        ({"interruptible": True}, "interruptible_MISMATCH"),
        ({"locked": True}, "locked_MISMATCH"),
        ({"volumeEncrypted": False}, "volumeEncrypted_MISMATCH"),
        ({"desiredStatus": "EXITED"}, "desiredStatus_MISMATCH"),
        ({"lastStartedAt": guardian.iso_utc(BASE - timedelta(days=1))}, "BIRTH_TIME"),
    ],
)
def test_semantic_201_mismatch_still_binds_exact_id_for_containment(
    changes, error_fragment
):
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = response_201(spec.pod_name, **changes)
    provider.created_pod = json.loads(response.body)
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.target_bound is True
    assert outcome.launch_admitted is False
    assert any(
        error_fragment in value
        for value in core.read_record(spec.key)["create_semantic_errors"]
    )


@pytest.mark.parametrize(
    ("field", "hostile_value"),
    [
        ("cloudType", "COMMUNITY"),
        ("containerDiskInGb", 49),
        ("gpuCount", 2),
        ("gpuTypeIds", ["NVIDIA RTX A6000"]),
        ("imageName", "attacker/image:latest"),
        ("networkVolumeId", "hfelwlp1va"),
        ("ports", ["22/tcp", "8888/http"]),
        ("volumeInGb", 19),
        ("volumeMountPath", "/root"),
    ],
)
def test_every_returned_optional_safety_field_is_cross_checked_for_containment(
    field, hostile_value
):
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = response_201(spec.pod_name, **{field: hostile_value})
    provider.created_pod = json.loads(response.body)
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.target_bound is True
    assert outcome.launch_admitted is False
    assert f"{field}_MISMATCH" in core.read_record(spec.key)[
        "create_semantic_errors"
    ]


def test_returned_environment_public_key_is_cross_checked():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = response_201(
        spec.pod_name,
        env={"PUBLIC_KEY": "ssh-ed25519 attacker attacker"},
    )
    provider.created_pod = json.loads(response.body)
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.target_bound is True
    assert outcome.launch_admitted is False
    assert "env_PUBLIC_KEY_MISMATCH" in core.read_record(spec.key)[
        "create_semantic_errors"
    ]


def test_exact_201_id_and_name_without_birth_time_still_bind_for_immediate_stop():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    body = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "interruptible": False,
        "locked": False,
        "volumeEncrypted": True,
        "desiredStatus": "RUNNING",
    }
    response = guardian.HttpResponse(
        201, guardian.canonical_json_bytes(body), guardian.CREATE_ENDPOINT
    )
    provider.created_pod = body
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.pod_id == "newpod1234"
    assert outcome.target_bound is True
    assert outcome.launch_admitted is False
    assert "BIRTH_TIME_ABSENT_OR_MALFORMED" in core.read_record(spec.key)[
        "create_semantic_errors"
    ]
    receipt = core.supervise_once(token)
    assert receipt is not None
    assert provider.stop_calls == ["newpod1234"]


@pytest.mark.parametrize(
    "unsafe_id", ["q2oqlooejhin7s", "hilj2rzs54gi06", "vernmyfb3ck9po"]
)
def test_201_protected_id_is_never_bound_or_stopped(unsafe_id):
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = response_201(spec.pod_name, pod_id=unsafe_id)
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.target_bound is False
    assert core.read_record(spec.key).get("target_pod_id") is None
    assert provider.stop_calls == []


def test_201_prearm_id_is_never_bound_or_stopped():
    old = {"id": "oldpod0001", "name": "unrelated", "desiredStatus": "EXITED"}
    provider = FakeProvider([old])
    values = setup_armed(provider=provider)
    core, _store, _provider, _signer, _clock, spec, request, token, _arm = values
    response = response_201(spec.pod_name, pod_id="oldpod0001")
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.target_bound is False
    assert provider.stop_calls == []


def test_http_400_is_terminal_no_inventory_reconciliation_even_with_huge_body():
    core, _store, provider, signer, _clock, spec, request, token, _arm = setup_armed()
    before = provider.list_calls
    response = guardian.HttpResponse(400, b"x" * 1_500_000, guardian.CREATE_ENDPOINT)
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.status == "CREATE_REJECTED_400"
    assert provider.list_calls == before
    assert provider.stop_calls == []
    record = core.read_record(spec.key)
    signer.assert_valid(core.read_receipt(spec.key, "create_rejected"))
    with pytest.raises(guardian.AuthorizationUnavailable):
        core.reconcile_ambiguous_create(token)


def test_400_from_wrong_effective_url_is_ambiguous_not_definitive():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = guardian.HttpResponse(400, b"{}", "https://example.invalid/not-runpod")
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.status == "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED"
    assert core.read_record(spec.key)["state"] == "CREATE_AMBIGUOUS"


def test_oversized_create_response_url_is_hash_only_and_reconciliation_can_stop():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    pod = json.loads(response_201(spec.pod_name).body)
    provider.created_pod = pod
    response = guardian.HttpResponse(
        201,
        guardian.canonical_json_bytes(pod),
        "https://rest.runpod.io/" + "x" * 400_000,
    )
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.status == "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED"
    record = core.read_record(spec.key)
    assert "create_response_effective_url" not in record
    assert "create_response_effective_url_retained" not in record
    assert len(guardian.canonical_json_bytes(record)) < guardian.MAX_LEDGER_ITEM_BYTES
    recovered = core.reconcile_ambiguous_create(token)
    assert recovered.pod_id == pod["id"]
    terminal = core.supervise_once(token)
    assert terminal is not None
    assert provider.stop_calls == [pod["id"]]


def test_malformed_http_response_envelope_fails_to_ambiguity_without_raw_storage():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    provider.post_response = guardian.HttpResponse(  # type: ignore[arg-type]
        201, "not-bytes", guardian.CREATE_ENDPOINT
    )
    reservation = core.reserve_create(token, exact_create_request_bytes=request)
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.status == "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED"
    record = core.read_record(spec.key)
    assert record["create_ambiguous_reason"] == "MALFORMED_HTTP_RESPONSE_ENVELOPE"
    assert "create_response_body_sha256" not in record


@pytest.mark.parametrize("status", [200, 202, 204, 408, 429, 500, 503])
def test_every_non_400_non_201_status_is_ambiguous_and_never_reposts(status):
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = guardian.HttpResponse(
        status,
        guardian.canonical_json_bytes({"message": "not authoritative"}),
        guardian.CREATE_ENDPOINT,
    )
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.status == "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED"
    with pytest.raises(guardian.CreateAlreadyDispatched):
        core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert provider.post_entries == 1


@pytest.mark.parametrize(
    "body",
    [
        b'{"id":"newpod1234","id":"another1234"}',
        b'{"id":"newpod1234","x":NaN}',
        b'{"id":"newpod1234","x":"\xff"}',
        b"{}",
    ],
)
def test_malformed_or_incomplete_201_requires_reconciliation(body):
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = guardian.HttpResponse(201, body, guardian.CREATE_ENDPOINT)
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.status == "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED"
    assert outcome.target_bound is False


def test_ambiguous_full_inventory_requires_one_unique_new_in_window_name():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = guardian.HttpResponse(500, b'{"error":"lost"}', guardian.CREATE_ENDPOINT)
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    provider.pods["newpod1234"] = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "createdAt": guardian.iso_utc(BASE + timedelta(seconds=10)),
        "desiredStatus": "RUNNING",
    }
    outcome = core.reconcile_ambiguous_create(token)
    assert outcome.pod_id == "newpod1234"
    assert outcome.launch_admitted is False
    record = core.read_record(spec.key)
    assert record["reconciliation_count"] == 1
    assert record["reconciliation_history_sha256"] != "0" * 64
    binding = core.read_receipt(spec.key, "binding")
    assert binding["payload"]["binding_reconciliation_inventory_sha256"] == (
        record["last_reconciliation_inventory_sha256"]
    )
    assert binding["payload"]["reconciliation_history_sha256"] == record[
        "reconciliation_history_sha256"
    ]


def test_ambiguous_inventory_rejects_multiple_out_of_window_and_mixed_births():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    provider.post_response = guardian.HttpResponse(500, b"{}", guardian.CREATE_ENDPOINT)
    reservation = core.reserve_create(token, exact_create_request_bytes=request)
    core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    provider.pods = {
        "newpod1234": {
            "id": "newpod1234",
            "name": spec.pod_name,
            "createdAt": guardian.iso_utc(BASE + timedelta(seconds=10)),
            "desiredStatus": "RUNNING",
        },
        "newpod5678": {
            "id": "newpod5678",
            "name": spec.pod_name,
            "createdAt": guardian.iso_utc(BASE + timedelta(seconds=11)),
            "desiredStatus": "RUNNING",
        },
        "newpod9999": {
            "id": "newpod9999",
            "name": spec.pod_name,
            "createdAt": guardian.iso_utc(BASE - timedelta(days=1)),
            "desiredStatus": "RUNNING",
        },
        "newpod8888": {
            "id": "newpod8888",
            "name": spec.pod_name,
            "createdAt": guardian.iso_utc(BASE + timedelta(seconds=12)),
            "lastStartedAt": guardian.iso_utc(BASE - timedelta(days=1)),
            "desiredStatus": "RUNNING",
        },
    }
    outcome = core.reconcile_ambiguous_create(token)
    assert outcome.status == "AMBIGUOUS_MULTIPLE_TARGETS"
    assert set(core.read_record(spec.key)["last_reconciliation_candidate_ids"]) == {
        "newpod1234",
        "newpod5678",
    }


def test_weak_response_id_must_match_full_inventory_candidate():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = guardian.HttpResponse(
        202,
        guardian.canonical_json_bytes({"id": "newpod1234"}),
        guardian.CREATE_ENDPOINT,
    )
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    for pod_id in ("newpod1234", "newpod5678"):
        provider.pods[pod_id] = {
            "id": pod_id,
            "name": spec.pod_name,
            "createdAt": guardian.iso_utc(BASE + timedelta(seconds=10)),
            "desiredStatus": "RUNNING",
        }
    outcome = core.reconcile_ambiguous_create(token)
    assert outcome.pod_id == "newpod1234"


def test_uncorroborated_weak_id_cannot_veto_unique_exact_name_containment():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = guardian.HttpResponse(
        202,
        guardian.canonical_json_bytes({"id": "wrongpod99"}),
        guardian.CREATE_ENDPOINT,
    )
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    provider.pods["newpod1234"] = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "createdAt": guardian.iso_utc(BASE + timedelta(seconds=10)),
        "desiredStatus": "RUNNING",
    }
    outcome = core.reconcile_ambiguous_create(token)
    assert outcome.pod_id == "newpod1234"
    assert outcome.launch_admitted is False


def test_legacy_runpod_birth_timestamp_is_admitted_for_binding_and_recovery():
    legacy = (BASE + timedelta(seconds=10)).strftime(
        "%Y-%m-%d %H:%M:%S.000 +0000 UTC"
    )
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = response_201(spec.pod_name, lastStartedAt=legacy)
    provider.created_pod = json.loads(response.body)
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert outcome.launch_admitted is False
    admission = core.verify_post_bind_launch_admission(token)
    assert admission["payload"]["launch_admitted"] is True

    second_key = guardian.AuthorizationKey(
        "owner.example", ACCOUNT, "authorization-0002"
    )
    second_spec, second_request = make_spec(key=second_key)
    second_provider = FakeProvider()
    second_core, _s, _p, _sig, second_clock = make_core(provider=second_provider)
    second_core.register_authorization(
        second_spec, exact_create_request_bytes=second_request
    )
    second_token = first_claim(
        second_core,
        second_spec,
        second_request,
        lease_seconds=200,
    )
    second_core.arm_precreate(
        second_token, exact_create_request_bytes=second_request
    )
    second_clock.set(BASE + timedelta(seconds=10))
    second_provider.post_response = guardian.HttpResponse(
        500, b"{}", guardian.CREATE_ENDPOINT
    )
    second_reservation = second_core.reserve_create(
        second_token, exact_create_request_bytes=second_request
    )
    second_core.dispatch_create(
        second_token,
        second_reservation,
        exact_create_request_bytes=second_request,
    )
    second_provider.pods["newpod5678"] = {
        "id": "newpod5678",
        "name": second_spec.pod_name,
        "lastStartedAt": legacy,
        "desiredStatus": "RUNNING",
    }
    recovered = second_core.reconcile_ambiguous_create(second_token)
    assert recovered.pod_id == "newpod5678"


def test_provider_timestamp_fraction_boundary_is_six_digits_and_canonicalized():
    exact = "2026-08-20T12:00:10.123456Z"
    assert guardian.iso_utc(guardian.parse_provider_utc(exact)) == exact
    with pytest.raises(guardian.ValidationError, match="noncanonical"):
        guardian.parse_provider_utc("2026-08-20T12:00:10.1234567Z")


@pytest.mark.parametrize(
    "hostile",
    [
        "2026-08-20T12:00:10Z",
        "2026-08-20T12:00:10.000000+00:00",
        "2026-08-20T12:00:10.0000001Z",
    ],
)
def test_authorization_utc_rejects_noncanonical_or_overprecision_forms(hostile):
    with pytest.raises(guardian.ValidationError, match="canonical"):
        guardian.parse_utc(hostile)


def test_huge_fractional_201_cannot_prevent_minimal_exact_id_binding_and_stop():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    pod = json.loads(response_201(spec.pod_name).body)
    pod["createdAt"] = "2026-08-20T12:00:10." + "0" * 400_000 + "Z"
    response = guardian.HttpResponse(
        201, guardian.canonical_json_bytes(pod), guardian.CREATE_ENDPOINT
    )
    provider.created_pod = pod
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.target_bound is True
    record = core.read_record(spec.key)
    assert record["target_pod_id"] == pod["id"]
    assert record["provider_birth_times_utc"] == {}
    assert len(guardian.canonical_json_bytes(record)) < guardian.MAX_LEDGER_ITEM_BYTES
    with pytest.raises(guardian.ValidationError, match="BODY_SIZE_INVALID"):
        core.supervise_once(token)
    assert provider.stop_calls == [pod["id"]]


def test_huge_mismatched_201_name_cannot_amplify_head_or_block_exact_id_stop():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    pod = json.loads(response_201(spec.pod_name).body)
    pod["name"] = "attacker-" + "x" * 400_000
    response = guardian.HttpResponse(
        201, guardian.canonical_json_bytes(pod), guardian.CREATE_ENDPOINT
    )
    provider.created_pod = pod
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.target_bound is True
    record = core.read_record(spec.key)
    assert record["target_pod_id"] == pod["id"]
    assert record["target_pod_name_at_binding"] is None
    assert record["target_provider_name_sha256"] == guardian.sha256_hex(
        pod["name"].encode("utf-8")
    )
    assert len(guardian.canonical_json_bytes(record)) < guardian.MAX_LEDGER_ITEM_BYTES
    with pytest.raises(guardian.ValidationError, match="BODY_SIZE_INVALID"):
        core.supervise_once(token)
    assert provider.stop_calls == [pod["id"]]


def test_unpaired_surrogate_201_fields_cannot_block_minimal_id_binding_or_stop():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    pod = json.loads(response_201(spec.pod_name).body)
    pod["name"] = "\ud800"
    pod["env"] = {"PUBLIC_KEY": "\ud800"}
    raw = (
        json.dumps(pod, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")
    response = guardian.HttpResponse(201, raw, guardian.CREATE_ENDPOINT)
    provider.created_pod = pod
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    outcome = core.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.target_bound is True
    assert outcome.pod_id == pod["id"]
    record = core.read_record(spec.key)
    assert record["target_pod_name_at_binding"] is None
    assert "env_PUBLIC_KEY_MISMATCH" in record["create_semantic_errors"]
    provider.get_response_override = guardian.HttpResponse(
        200,
        guardian.canonical_json_bytes(
            {"id": pod["id"], "desiredStatus": "EXITED"}
        ),
        f"{guardian.CREATE_ENDPOINT}/{pod['id']}",
    )
    terminal = core.supervise_once(token)
    assert terminal is not None
    assert provider.stop_calls == [pod["id"]]


def test_huge_fractional_live_get_is_denied_without_head_amplification():
    values = bind_pending_fixture()
    core, _store, provider, _signer, _clock, spec, _request, token, _arm, _res, pod = values
    live = deepcopy(provider.pods[pod["id"]])
    live["lastStartedAt"] = "2026-08-20T12:00:10." + "0" * 40_000 + "Z"
    raw = guardian.canonical_json_bytes(live)
    provider.get_response_override = guardian.HttpResponse(
        200, raw, f"{guardian.CREATE_ENDPOINT}/{pod['id']}"
    )
    receipt = core.verify_post_bind_launch_admission(token)
    assert receipt["payload"]["launch_admitted"] is False
    assert any(
        "BODY_SIZE_INVALID" in error
        for error in receipt["payload"]["validation_errors"]
    )
    assert len(guardian.canonical_json_bytes(core.read_record(spec.key))) < (
        guardian.MAX_LEDGER_ITEM_BYTES
    )


def test_huge_fractional_inventory_timestamp_fails_before_create():
    huge = "2026-08-20T12:00:10." + "0" * 100_000 + "Z"
    provider = FakeProvider(
        [
            {
                "id": "otherpod99",
                "name": "unrelated-pod",
                "createdAt": huge,
                "desiredStatus": "EXITED",
            }
        ]
    )
    core, _store, _provider, _signer, _clock = make_core(provider=provider)
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request)
    with pytest.raises(guardian.ValidationError, match="provider UTC"):
        core.arm_precreate(token, exact_create_request_bytes=request)
    assert provider.post_entries == 0


def test_null_created_at_does_not_hide_valid_last_started_ambiguous_target():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    provider.post_response = guardian.HttpResponse(500, b"{}", guardian.CREATE_ENDPOINT)
    reservation = core.reserve_create(token, exact_create_request_bytes=request)
    core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    provider.pods["newpod1234"] = {
        "id": "newpod1234",
        "name": spec.pod_name,
        "createdAt": None,
        "lastStartedAt": guardian.iso_utc(BASE + timedelta(seconds=10)),
        "desiredStatus": "RUNNING",
    }
    recovered = core.reconcile_ambiguous_create(token)
    assert recovered.pod_id == "newpod1234"


def test_reserved_create_can_transfer_to_new_fence_but_stale_owner_cannot_send():
    values = setup_armed(lease_seconds=20)
    core, _store, provider, _signer, clock, spec, request, old, _arm = values
    reservation = core.reserve_create(old, exact_create_request_bytes=request)
    clock.set(BASE + timedelta(seconds=21))
    new = core.claim_execution(spec.key, execution_arn=EXECUTION_2, lease_seconds=60)
    provider.post_response = response_201(spec.pod_name)
    provider.created_pod = json.loads(provider.post_response.body)
    with pytest.raises(guardian.StaleFence):
        core.dispatch_create(old, reservation, exact_create_request_bytes=request)
    outcome = core.dispatch_create(new, reservation, exact_create_request_bytes=request)
    assert outcome.target_bound is True
    assert provider.post_entries == 1


def test_old_owner_response_after_takeover_cannot_mutate_new_fence():
    values = setup_armed(lease_seconds=20)
    core, _store, provider, _signer, clock, spec, request, old, _arm = values
    reservation = core.reserve_create(old, exact_create_request_bytes=request)
    provider.post_response = response_201(spec.pod_name)
    candidate = json.loads(provider.post_response.body)
    provider.created_pod = candidate
    provider.post_release = threading.Event()
    errors: list[BaseException] = []

    def dispatch_old() -> None:
        try:
            core.dispatch_create(old, reservation, exact_create_request_bytes=request)
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=dispatch_old)
    thread.start()
    assert provider.post_entered.wait(timeout=5)
    clock.set(BASE + timedelta(seconds=21))
    new = core.claim_execution(spec.key, execution_arn=EXECUTION_2, lease_seconds=60)
    provider.post_release.set()
    thread.join(timeout=10)
    assert errors and isinstance(errors[0], guardian.StaleFence)
    assert core.read_record(spec.key).get("target_pod_id") is None
    recovered = core.reconcile_ambiguous_create(new)
    assert recovered.pod_id == candidate["id"]
    assert provider.post_entries == 1


def test_exact_id_stop_and_terminal_get_produce_signed_terminal_proof():
    values = bind_success_fixture()
    core, _store, provider, signer, _clock, spec, _request, token, _arm, _res, pod = values
    receipt = core.request_stop(token)
    assert receipt is not None
    assert provider.stop_calls == [pod["id"]]
    assert provider.get_calls[-1] == pod["id"]
    assert receipt["payload"]["terminal_provider_proof"] is True
    assert receipt["payload"]["stop_before_deadline"] is True
    assert receipt["payload"]["containment_sla_met"] is True
    assert receipt["payload"]["stop_attempt_count"] == 1
    assert receipt["payload"]["stop_result_count"] == 1
    assert receipt["payload"]["stop_result_history"][-1]["outcome"] == (
        "HTTP_RESPONSE"
    )
    assert receipt["payload"]["stop_result_history_sha256"] != "0" * 64
    assert "terminal_exact_body_base64" not in receipt["payload"]
    projection = receipt["payload"]["terminal_semantic_projection"]
    assert projection == {
        "schema_version": guardian.TERMINAL_SEMANTIC_PROJECTION_SCHEMA,
        "http_envelope": {
            "http_status": 200,
            "effective_url_exact_id": True,
            "media_type": "application/json",
            "content_encoding_identity": True,
        },
        "pod": {"id": pod["id"], "desired_status": "EXITED"},
    }
    assert receipt["payload"]["terminal_semantic_projection_sha256"] == (
        guardian.sha256_hex(guardian.canonical_json_bytes(projection))
    )
    signed_payload = base64.b64decode(
        receipt["signed_payload_base64"], validate=True
    )
    assert len(signed_payload) == receipt["signed_payload_byte_count"]
    assert guardian.sha256_hex(signed_payload) == receipt["signed_payload_sha256"]
    signer.assert_valid(receipt)
    assert core.read_record(spec.key)["state"] == "TERMINAL_PROVEN"


def test_terminal_raw_echo_and_header_are_hash_bound_but_never_reversible():
    values = bind_success_fixture()
    core, store, provider, signer, _clock, spec, _request, token, _arm, _res, pod = values
    terminal_pod = deepcopy(provider.pods[pod["id"]])
    terminal_pod["desiredStatus"] = "EXITED"
    terminal_pod["providerEcho"] = {
        "literal": ECHOED_API_SECRET,
        "percent": PERCENT_ENCODED_SECRET,
        "base32": BASE32_ENCODED_SECRET,
        "bearer": f"Bearer {ECHOED_API_SECRET}",
        "fragments": list(FRAGMENTED_SECRET_PARTS),
    }
    raw = guardian.canonical_json_bytes(terminal_pod)
    hostile_content_type = (
        f"application/json; authorization=Bearer {ECHOED_API_SECRET}"
    )
    provider.get_response_override = guardian.HttpResponse(
        200,
        raw,
        f"{guardian.CREATE_ENDPOINT}/{pod['id']}",
        content_type=hostile_content_type,
    )

    receipt = core.request_stop(token)
    assert receipt is not None
    assert receipt["payload"]["terminal_exact_body_sha256"] == guardian.sha256_hex(
        raw
    )
    assert receipt["payload"]["terminal_exact_body_byte_count"] == len(raw)
    assert "terminal_exact_body_base64" not in receipt["payload"]
    projection = receipt["payload"]["terminal_semantic_projection"]
    assert projection["pod"] == {"id": pod["id"], "desired_status": "EXITED"}
    assert receipt["payload"]["terminal_semantic_projection_sha256"] == (
        guardian.sha256_hex(guardian.canonical_json_bytes(projection))
    )
    signer.assert_valid(receipt)
    record = core.read_record(spec.key)
    assert record["terminal_semantic_projection"] == projection
    assert_not_durably_reversible(
        store,
        raw,
        base64.b64encode(raw),
        hostile_content_type.encode("ascii"),
        ECHOED_API_SECRET.encode("ascii"),
        PERCENT_ENCODED_SECRET.encode("ascii"),
        BASE32_ENCODED_SECRET.encode("ascii"),
        *(part.encode("ascii") for part in FRAGMENTED_SECRET_PARTS),
    )


def test_post_binding_name_drift_cannot_defeat_exact_id_stop():
    values = bind_success_fixture()
    core, _store, provider, _signer, _clock, _spec, _request, token, _arm, _res, pod = values
    provider.pods[pod["id"]]["name"] = "renamed-after-binding"
    core.request_stop(token)
    assert provider.stop_calls == [pod["id"]]


def test_containment_only_binding_stops_immediately_before_planned_stop_time():
    core, _store, provider, _signer, _clock, spec, request, token, _arm = setup_armed()
    response = response_201(spec.pod_name, interruptible=True)
    provider.created_pod = json.loads(response.body)
    reservation = reserve_and_set_201(
        core, provider, spec, request, token, response=response
    )
    core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    result = core.supervise_once(token)
    assert result is not None
    assert provider.stop_calls == ["newpod1234"]


def test_admitted_target_waits_until_planned_stop_then_stops():
    values = bind_success_fixture()
    core, _store, provider, _signer, clock, _spec, _request, token, _arm, _res, pod = values
    assert core.supervise_once(token) is None
    assert provider.stop_calls == []
    clock.set(BASE + timedelta(seconds=100))
    successor = core.claim_execution(
        token.key, execution_arn=EXECUTION_2, lease_seconds=60
    )
    result = core.supervise_once(successor)
    assert result is not None
    assert provider.stop_calls == [pod["id"]]


def test_due_stop_occurs_before_get_and_get_outage_cannot_block_containment():
    values = bind_success_fixture()
    core, _store, provider, _signer, clock, _spec, _request, token, _arm, _res, pod = values
    clock.set(BASE + timedelta(seconds=100))

    def get_outage(_account: str, _pod_id: str):
        raise OSError("read path unavailable")

    provider.get_pod = get_outage  # type: ignore[method-assign]
    successor = core.claim_execution(
        token.key, execution_arn=EXECUTION_2, lease_seconds=60
    )
    with pytest.raises(OSError, match="unavailable"):
        core.supervise_once(successor)
    assert provider.stop_calls == [pod["id"]]
    assert core.read_record(token.key)["state"] == "STOPPING"


def test_late_stop_is_still_attempted_but_sla_is_truthfully_false():
    values = bind_success_fixture()
    core, _store, provider, _signer, clock, _spec, _request, token, _arm, _res, pod = values
    clock.set(BASE + timedelta(seconds=201))
    successor = core.claim_execution(
        token.key, execution_arn=EXECUTION_2, lease_seconds=60
    )
    receipt = core.request_stop(successor)
    assert provider.stop_calls == [pod["id"]]
    assert receipt is not None
    assert receipt["payload"]["stop_before_deadline"] is False
    assert receipt["payload"]["containment_sla_met"] is False


def test_predeadline_ambiguous_stop_terminal_after_hard_deadline_fails_sla():
    values = bind_success_fixture()
    core, _store, provider, _signer, clock, _spec, _request, token, _arm, _res, pod = values
    provider.stop_mode = "ambiguous_after_provider"
    assert core.request_stop(token) is None
    assert provider.pods[pod["id"]]["desiredStatus"] == "EXITED"
    clock.set(BASE + timedelta(seconds=201))
    successor = core.claim_execution(
        token.key, execution_arn=EXECUTION_2, lease_seconds=60
    )
    receipt = core.observe_terminal(successor)
    assert receipt is not None
    assert receipt["payload"]["stop_before_deadline"] is True
    assert receipt["payload"]["terminal_before_hard_stop_deadline"] is False
    assert receipt["payload"]["terminal_by_proof_deadline"] is True
    assert receipt["payload"]["containment_sla_met"] is False


def test_crash_after_stop_effect_is_recovered_by_terminal_get_without_second_stop():
    values = bind_success_fixture()
    core, _store, provider, _signer, clock, spec, _request, old, _arm, _res, pod = values
    provider.stop_mode = "crash_after_provider"
    with pytest.raises(HardCrash):
        core.request_stop(old)
    assert provider.pods[pod["id"]]["desiredStatus"] == "EXITED"
    clock.set(BASE + timedelta(seconds=201))
    new = core.claim_execution(spec.key, execution_arn=EXECUTION_2, lease_seconds=30)
    receipt = core.observe_terminal(new)
    assert receipt is not None
    assert provider.stop_calls == [pod["id"]]


def test_crash_before_stop_effect_is_retried_only_after_new_fence():
    values = bind_success_fixture()
    core, _store, provider, _signer, clock, spec, _request, old, _arm, _res, pod = values
    provider.stop_mode = "crash_before_provider"
    with pytest.raises(HardCrash):
        core.request_stop(old)
    assert provider.pods[pod["id"]]["desiredStatus"] == "RUNNING"
    clock.set(BASE + timedelta(seconds=201))
    new = core.claim_execution(spec.key, execution_arn=EXECUTION_2, lease_seconds=30)
    provider.stop_mode = "return"
    receipt = core.request_stop(new)
    assert receipt is not None
    assert provider.stop_calls == [pod["id"], pod["id"]]


def test_same_execution_can_retry_crashed_stop_only_after_fresh_exact_id_get():
    values = bind_success_fixture()
    core, _store, provider, _signer, _clock, _spec, _request, token, _arm, _res, pod = values
    provider.stop_mode = "crash_before_provider"
    with pytest.raises(HardCrash):
        core.request_stop(token)
    with pytest.raises(guardian.NotReady, match="re-observe"):
        core.request_stop(token)
    assert core.observe_terminal(token) is None
    provider.stop_mode = "return"
    receipt = core.request_stop(token)
    assert receipt is not None
    assert provider.stop_calls == [pod["id"], pod["id"]]


def test_terminal_proof_uses_get_completion_time_for_deadline_truth():
    values = bind_success_fixture()
    core, _store, provider, _signer, clock, _spec, _request, token, _arm, _res, pod = values
    provider.pods[pod["id"]]["desiredStatus"] = "EXITED"
    real_get = provider.get_pod

    def slow_get(account: str, pod_id: str):
        result = real_get(account, pod_id)
        clock.set(BASE + timedelta(seconds=291))
        return result

    provider.get_pod = slow_get  # type: ignore[method-assign]
    with pytest.raises(guardian.StaleFence, match="expired"):
        core.observe_terminal(token)
    assert core.read_record(token.key)["state"] == "TARGET_BOUND"


def test_malformed_stop_response_is_ambiguous_and_never_terminal_proof():
    values = bind_success_fixture()
    core, _store, provider, _signer, _clock, spec, _request, token, _arm, _res, pod = values

    def malformed_stop(account: str, pod_id: str):
        provider.stop_calls.append(pod_id)
        return guardian.HttpResponse(200, "not-bytes", "bad")  # type: ignore[arg-type]

    provider.stop_pod = malformed_stop  # type: ignore[method-assign]
    assert core.request_stop(token) is None
    record = core.read_record(spec.key)
    assert record["state"] == "STOPPING"
    assert record["stop_result_history"][-1]["error_class"] == (
        "MALFORMED_HTTP_RESPONSE_ENVELOPE"
    )
    assert "terminal" not in record["receipts"]


def test_oversized_stop_metadata_is_compact_and_terminal_get_recovers():
    values = bind_success_fixture()
    core, _store, provider, signer, _clock, spec, _request, token, _arm, _res, pod = values

    def oversized_stop(account: str, pod_id: str):
        assert account == ACCOUNT
        provider.stop_calls.append(pod_id)
        provider.pods[pod_id]["desiredStatus"] = "EXITED"
        return guardian.HttpResponse(
            200,
            b"{}",
            f"{guardian.CREATE_ENDPOINT}/{pod_id}/stop/" + "x" * 100_000,
        )

    provider.stop_pod = oversized_stop  # type: ignore[method-assign]
    assert core.request_stop(token) is None
    record = core.read_record(spec.key)
    assert record["state"] == "STOPPING"
    assert record["stop_result_history"][-1]["error_class"] == (
        "MALFORMED_HTTP_RESPONSE_METADATA"
    )
    assert len(guardian.canonical_json_bytes(record)) < guardian.MAX_LEDGER_ITEM_BYTES
    terminal = core.observe_terminal(token)
    assert terminal is not None
    assert terminal["payload"]["stop_result_count"] == 1
    assert terminal["payload"]["stop_result_history"][-1]["outcome"] == (
        "AMBIGUOUS_EXCEPTION"
    )
    signer.assert_valid(terminal)


def test_stop_attempt_and_result_history_remain_bounded_during_long_outage():
    values = bind_success_fixture()
    core, _store, provider, _signer, _clock, spec, _request, token, _arm, _res, pod = values
    real_stop = provider.stop_pod

    def unavailable_stop(account: str, pod_id: str):
        assert account == ACCOUNT
        provider.stop_calls.append(pod_id)
        raise OSError("simulated prolonged STOP response outage")

    provider.stop_pod = unavailable_stop  # type: ignore[method-assign]
    for _index in range(40):
        assert core.request_stop(token) is None
    record = core.read_record(spec.key)
    assert record["stop_attempt_count"] == 40
    assert len(record["stop_attempt_started_at_utc"]) == (
        guardian.MAX_STOP_HISTORY_ENTRIES
    )
    assert len(record["stop_result_history"]) == guardian.MAX_STOP_HISTORY_ENTRIES
    assert record["stop_attempt_history_sha256"] != "0" * 64
    assert record["stop_result_history_sha256"] != "0" * 64
    assert len(guardian.canonical_json_bytes(record)) < guardian.MAX_LEDGER_ITEM_BYTES

    provider.stop_pod = real_stop  # type: ignore[method-assign]
    receipt = core.request_stop(token)
    assert receipt is not None
    assert receipt["payload"]["stop_attempt_count"] == 41
    assert receipt["payload"]["stop_result_count"] == 41
    assert len(receipt["payload"]["stop_result_history"]) == (
        guardian.MAX_STOP_HISTORY_ENTRIES
    )
    assert core.read_record(spec.key)["state"] == "TERMINAL_PROVEN"
    assert provider.stop_calls == [pod["id"]] * 41


def test_exact_id_get_mismatch_never_becomes_terminal_proof():
    values = bind_success_fixture()
    core, _store, provider, _signer, _clock, spec, _request, token, _arm, _res, pod = values
    real_get = provider.get_pod

    def wrong_get(account: str, pod_id: str):
        response = real_get(account, pod_id)
        value = json.loads(response.body)
        value["id"] = "another1234"
        return guardian.HttpResponse(
            200,
            guardian.canonical_json_bytes(value),
            response.effective_url,
        )

    provider.get_pod = wrong_get  # type: ignore[method-assign]
    with pytest.raises(guardian.ValidationError, match="different"):
        core.observe_terminal(token)
    assert core.read_record(spec.key)["state"] == "TARGET_BOUND"


def test_unresolved_failure_cannot_finalize_before_terminal_proof_deadline():
    core, _store, provider, signer, clock, spec, request, token, _arm = setup_armed()
    provider.post_mode = "ambiguous_after_provider"
    reservation = core.reserve_create(token, exact_create_request_bytes=request)
    core.dispatch_create(token, reservation, exact_create_request_bytes=request)
    core.reconcile_ambiguous_create(token)
    with pytest.raises(guardian.NotReady, match="proof deadline"):
        core.finalize_unresolved(token)
    clock.set(BASE + timedelta(seconds=290))
    receipt = core.finalize_unresolved(token)
    signer.assert_valid(receipt)
    assert receipt["payload"]["terminal_provider_proof"] is False
    assert receipt["payload"]["containment_proven"] is False


def test_unknown_dispatch_crash_can_finalize_truthfully_at_proof_deadline():
    core, _store, provider, signer, clock, spec, request, old, _arm = setup_armed()
    reservation = core.reserve_create(old, exact_create_request_bytes=request)
    provider.post_mode = "crash_before_provider"
    with pytest.raises(HardCrash):
        core.dispatch_create(old, reservation, exact_create_request_bytes=request)
    assert core.read_record(spec.key)["state"] == "CREATE_DISPATCHED_UNKNOWN"
    clock.set(BASE + timedelta(seconds=290))
    new = core.claim_execution(spec.key, execution_arn=EXECUTION_2, lease_seconds=30)
    receipt = core.finalize_unresolved(new)
    signer.assert_valid(receipt)
    assert receipt["payload"]["terminal_provider_proof"] is False
    assert core.read_record(spec.key)["state"] == "UNRESOLVED_TERMINAL_FAILURE"
    assert provider.post_entries == 1


@pytest.mark.parametrize("predispatch_state", ["CLAIMED", "ARMED", "CREATE_RESERVED"])
def test_expired_predispatch_states_finalize_signed_zero_post_safe_loss(
    predispatch_state
):
    core, _store, provider, signer, clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    token = first_claim(core, spec, request, lease_seconds=200)
    if predispatch_state in {"ARMED", "CREATE_RESERVED"}:
        core.arm_precreate(token, exact_create_request_bytes=request)
    if predispatch_state == "CREATE_RESERVED":
        clock.set(BASE + timedelta(seconds=10))
        core.reserve_create(token, exact_create_request_bytes=request)
    clock.set(BASE + timedelta(seconds=50))
    with pytest.raises(guardian.NotReady, match="window"):
        core.finalize_no_create_safe_loss(token)
    clock.advance(0.000001)
    receipt = core.finalize_no_create_safe_loss(token)
    assert receipt["receipt_type"] == "NO_CREATE_DISPATCHED_SAFE_LOSS"
    assert receipt["payload"]["provider_create_attempts"] == 0
    assert receipt["payload"]["create_dispatch_marker_present"] is False
    assert provider.post_entries == 0
    assert provider.provider_create_commits == 0
    assert core.read_record(spec.key)["state"] == "NO_CREATE_DISPATCHED_SAFE_LOSS"
    signer.assert_valid(receipt)


def test_post_deadline_successor_gets_live_lease_and_finalizes_reserved_safe_loss():
    values = setup_armed(lease_seconds=20)
    core, _store, provider, _signer, clock, spec, request, _old, _arm = values
    clock.set(BASE + timedelta(seconds=10))
    core.reserve_create(_old, exact_create_request_bytes=request)
    clock.set(BASE + timedelta(seconds=291))
    successor = core.claim_execution(
        spec.key, execution_arn=EXECUTION_2, lease_seconds=5
    )
    assert guardian.parse_utc(
        core.read_record(spec.key)["owner_lease_expires_at_utc"]
    ) > clock.now()
    receipt = core.supervise_once(successor)
    assert receipt is not None
    assert receipt["payload"]["safe_loss_proven"] is True
    assert provider.post_entries == 0
    assert provider.provider_create_commits == 0


def test_bound_target_missed_proof_deadline_signs_failure_but_retains_emergency_stop():
    values = bind_success_fixture()
    core, _store, provider, signer, clock, spec, _request, old, _arm, _res, pod = values
    clock.set(BASE + timedelta(seconds=290))
    failure = core.finalize_containment_failure(old)
    signer.assert_valid(failure)
    assert failure["payload"]["terminal_provider_proof"] is False
    assert failure["payload"]["emergency_exact_id_stop_still_required"] is True
    assert core.read_record(spec.key)["state"] == "EMERGENCY_CONTAINMENT_REQUIRED"

    new = core.claim_execution(spec.key, execution_arn=EXECUTION_2, lease_seconds=30)
    terminal = core.request_stop(new)
    assert terminal is not None
    assert provider.stop_calls == [pod["id"]]
    assert terminal["payload"]["containment_sla_met"] is False
    record = core.read_record(spec.key)
    assert record["state"] == "TERMINAL_PROVEN"
    assert "containment_failure" in record["receipts"]


def test_receipt_tamper_is_rejected_and_every_transition_receipt_is_kms_bound():
    values = bind_success_fixture()
    core, _store, _provider, signer, _clock, spec, _request, _token, _arm, _res, _pod = values
    receipts = core.read_record(spec.key)["receipts"]
    assert {"registration", "consumption", "arm", "create_reservation", "create_dispatch", "binding"}.issubset(receipts)
    for reference in receipts.values():
        receipt = core.resolve_receipt_reference(reference)
        signer.assert_valid(receipt)
    tampered = core.read_receipt(spec.key, "binding")
    tampered["payload"]["pod_id"] = "attacker9999"
    with pytest.raises(guardian.ValidationError, match="self-hash"):
        guardian.receipt_signing_message(tampered)


def test_live_semantic_projection_is_strict_allowlisted_and_hash_bound():
    values = bind_success_fixture()
    core, store, _provider, _signer, _clock, spec, _request, _token, _arm, _res, _pod = values
    receipt = core.read_receipt(spec.key, "launch_admission")
    projection = receipt["payload"]["live_get_semantic_projection"]
    assert receipt["payload"]["live_get_semantic_projection_sha256"] == (
        guardian.sha256_hex(guardian.canonical_json_bytes(projection))
    )

    hash_tampered = deepcopy(receipt)
    hash_tampered["payload"]["live_get_semantic_projection"]["pod"][
        "external_ssh_port"
    ] += 1
    with pytest.raises(guardian.ValidationError, match="projection SHA-256 mismatch"):
        guardian.receipt_signing_message(hash_tampered)

    extra_field = deepcopy(receipt)
    extra_field["payload"]["live_get_semantic_projection"]["pod"][
        "providerEcho"
    ] = ECHOED_API_SECRET
    extra_field["payload"]["live_get_semantic_projection_sha256"] = guardian.sha256_hex(
        guardian.canonical_json_bytes(
            extra_field["payload"]["live_get_semantic_projection"]
        )
    )
    with pytest.raises(guardian.ValidationError, match="projection keyset"):
        guardian.receipt_signing_message(extra_field)

    with store._lock:
        head = store._items[(spec.key.pk, spec.key.sk)]
        head["launch_admission_semantic_projection"]["pod"][
            "external_ssh_port"
        ] += 1
    with pytest.raises(guardian.ValidationError, match="projection SHA-256 mismatch"):
        core.read_record(spec.key)


def test_legacy_reversible_provider_fields_are_rejected_on_receipt_and_head_read():
    values = bind_success_fixture()
    core, store, _provider, _signer, _clock, spec, _request, _token, _arm, _res, _pod = values
    receipt = core.read_receipt(spec.key, "launch_admission")
    hostile_raw = b'{"providerEcho":"' + ECHOED_API_SECRET.encode("ascii") + b'"}'
    legacy_receipt = deepcopy(receipt)
    legacy_receipt["payload"]["live_get_exact_body_base64"] = base64.b64encode(
        hostile_raw
    ).decode("ascii")
    with pytest.raises(guardian.ValidationError, match="reversible legacy field"):
        guardian.receipt_signing_message(legacy_receipt)

    with store._lock:
        head = store._items[(spec.key.pk, spec.key.sk)]
        head["live_get_content_type"] = (
            f"application/json; authorization=Bearer {ECHOED_API_SECRET}"
        )
    with pytest.raises(guardian.ValidationError, match="reversible legacy field"):
        core.read_record(spec.key)


def test_terminal_semantic_projection_tamper_is_rejected_by_its_signed_hash():
    values = bind_success_fixture()
    core, _store, _provider, _signer, _clock, spec, _request, token, _arm, _res, _pod = values
    terminal = core.request_stop(token)
    assert terminal is not None
    projection = terminal["payload"]["terminal_semantic_projection"]
    assert terminal["payload"]["terminal_semantic_projection_sha256"] == (
        guardian.sha256_hex(guardian.canonical_json_bytes(projection))
    )
    tampered = deepcopy(terminal)
    tampered["payload"]["terminal_semantic_projection"]["pod"][
        "desired_status"
    ] = "TERMINATED"
    with pytest.raises(guardian.ValidationError, match="projection SHA-256 mismatch"):
        guardian.receipt_signing_message(tampered)


@pytest.mark.parametrize(
    "signer",
    [
        BadSigner(key_arn="not-a-kms-arn"),
        BadSigner(algorithm="HMAC_SHA_256"),
        BadSigner(message_type="RAW"),
    ],
)
def test_non_kms_signer_identity_or_algorithm_fails_before_store_write(signer):
    core, store, _provider, _signer, _clock = make_core(signer=signer)
    spec, request = make_spec()
    with pytest.raises(guardian.ValidationError, match="signer"):
        core.register_authorization(spec, exact_create_request_bytes=request)
    assert store.put_calls == 0


def test_spec_rejects_boolean_or_extended_deadline_and_missing_protected_ids():
    core, store, _provider, _signer, _clock = make_core()
    spec, request = make_spec()
    hostile = replace(
        spec,
        hard_stop_deadline_utc=guardian.iso_utc(BASE + timedelta(hours=1)),
        terminal_proof_deadline_utc=guardian.iso_utc(BASE + timedelta(hours=1, minutes=1)),
    )
    with pytest.raises(guardian.ValidationError, match="35 minutes"):
        core.register_authorization(hostile, exact_create_request_bytes=request)
    hostile = replace(spec, protected_pod_ids=())
    with pytest.raises(guardian.ValidationError, match="required protected"):
        core.register_authorization(hostile, exact_create_request_bytes=request)
    assert store.put_calls == 0


@pytest.mark.parametrize(
    "hostile_ceiling",
    [0.50, True, "NaN", "Infinity", "0.500", "0.51", "1", "0", "-0.01"],
)
def test_authorization_cost_ceiling_is_canonical_positive_and_never_over_050(
    hostile_ceiling
):
    core, store, _provider, _signer, _clock = make_core()
    spec, request = make_spec()
    with pytest.raises(guardian.ValidationError, match="maximum hourly cost"):
        core.register_authorization(
            replace(spec, max_cost_per_hour=hostile_ceiling),  # type: ignore[arg-type]
            exact_create_request_bytes=request,
        )
    assert store.put_calls == 0


def test_exact_cost_ceiling_is_bound_in_authorization_arm_binding_and_admission_receipts():
    values = bind_success_fixture()
    core, _store, _provider, _signer, _clock, spec, _request, _token, _arm, _res, _pod = values
    record = core.read_record(spec.key)
    assert record["authorization_spec"]["max_cost_per_hour"] == "0.50"
    assert core.read_receipt(spec.key, "registration")["payload"]["authorization_spec"][
        "max_cost_per_hour"
    ] == "0.50"
    for receipt_name in ("consumption", "arm", "create_reservation", "create_dispatch", "binding", "launch_admission"):
        assert core.read_receipt(spec.key, receipt_name)["payload"][
            "max_cost_per_hour"
        ] == "0.50"


def test_exact_1800_second_wall_and_90_second_stop_lead_boundaries():
    spec, request = make_spec()
    hard_boundary = BASE + timedelta(seconds=10 + guardian.MAX_POD_RUN_SECONDS)
    boundary = replace(
        spec,
        stop_dispatch_at_utc=guardian.iso_utc(
            hard_boundary - timedelta(seconds=guardian.MIN_STOP_LEAD_SECONDS)
        ),
        hard_stop_deadline_utc=guardian.iso_utc(hard_boundary),
        terminal_proof_deadline_utc=guardian.iso_utc(
            hard_boundary + timedelta(seconds=90)
        ),
    )
    core, _store, _provider, _signer, _clock = make_core()
    core.register_authorization(boundary, exact_create_request_bytes=request)

    wall_epsilon = replace(
        boundary,
        hard_stop_deadline_utc=guardian.iso_utc(
            hard_boundary + timedelta(microseconds=1)
        ),
        terminal_proof_deadline_utc=guardian.iso_utc(
            hard_boundary + timedelta(seconds=90, microseconds=1)
        ),
    )
    core, store, _provider, _signer, _clock = make_core()
    with pytest.raises(guardian.ValidationError, match="1800 seconds"):
        core.register_authorization(
            wall_epsilon, exact_create_request_bytes=request
        )
    assert store.put_calls == 0

    lead_epsilon = replace(
        boundary,
        stop_dispatch_at_utc=guardian.iso_utc(
            hard_boundary
            - timedelta(seconds=guardian.MIN_STOP_LEAD_SECONDS)
            + timedelta(microseconds=1)
        ),
    )
    core, store, _provider, _signer, _clock = make_core()
    with pytest.raises(guardian.ValidationError, match="90-second lead"):
        core.register_authorization(
            lead_epsilon, exact_create_request_bytes=request
        )
    assert store.put_calls == 0


def test_core_has_no_sdk_network_subprocess_delete_start_or_model_surface():
    source = Path(guardian.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported_roots.isdisjoint(
        {"boto3", "botocore", "urllib", "requests", "httpx", "subprocess", "socket"}
    )
    assert "def delete_pod" not in source
    assert "def start_pod" not in source
    assert "load_model" not in source
    assert set(guardian.ProviderTransport.__dict__) >= {
        "list_all_pods",
        "post_create",
        "get_pod",
        "stop_pod",
    }


def test_no_provider_call_occurs_during_import_registration_or_claim():
    core, _store, provider, _signer, _clock = make_core()
    spec, request = make_spec()
    core.register_authorization(spec, exact_create_request_bytes=request)
    first_claim(core, spec, request)
    assert provider.list_calls == 0
    assert provider.post_entries == 0
    assert provider.get_calls == []
    assert provider.stop_calls == []
