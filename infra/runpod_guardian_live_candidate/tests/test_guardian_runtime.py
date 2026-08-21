"""Offline service-contract tests for the deployable guardian candidate.

No test imports boto3, opens a socket, contacts AWS/RunPod, or creates a paid
resource.  Provider and AWS SDK surfaces below are byte-capturing fakes.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import io
import json
from pathlib import Path
import sys
import threading
import time
from typing import Any, Mapping

import pytest


HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
TOOLS = REPO / "tools" / "runpod_open_weight_canary_v2"
SRC = HERE.parents[1] / "src"
for path in (TOOLS, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import aws_production_guardian_core as guardian
import guardian_runtime as runtime
import test_aws_production_guardian_core as core_fakes

if str(HERE.parents[1]) not in sys.path:
    sys.path.insert(0, str(HERE.parents[1]))
import create_deployment_binding as binding_tool


BASE = core_fakes.BASE
ACCOUNT = core_fakes.ACCOUNT
KEY_ARN = "arn:aws:kms:us-west-2:123456789012:key/test-key-00000001"
BINDING = "d" * 64
API_KEY = b"test-only-runpod-api-key-abcdefghijklmnopqrstuvwxyz"
CORE_LOCK = "c" * 64


@pytest.fixture(autouse=True)
def compiled_build_identity(monkeypatch):
    monkeypatch.setattr(runtime, "COMPILED_CORE_LOCK_SHA256", CORE_LOCK)
    monkeypatch.setattr(
        runtime,
        "COMPILED_LOCKED_HASHES",
        {
            "core_sha256": "2" * 64,
            "runtime_sha256": "3" * 64,
            "state_machine_sha256": "4" * 64,
            "template_sha256": "5" * 64,
        },
    )
    monkeypatch.setattr(
        runtime,
        "_ACTIVATION_DOCUMENT_VERIFIER",
        lambda environment, binding, capability, context: None,
    )
    monkeypatch.setenv("CORE_LOCK_SHA256", CORE_LOCK)
    monkeypatch.setenv("TIMING_VALIDATION_EVIDENCE_SHA256", "e" * 64)
    monkeypatch.setattr(
        runtime,
        "_CREATE_CAPABILITY_CLOCK",
        lambda: BASE + timedelta(seconds=10),
    )
    monkeypatch.setattr(runtime, "_CREATE_CAPABILITY_CONSUMER", None)
    monkeypatch.setattr(runtime, "_CREATE_CAPABILITY_DDB_FACTORY", None)


class FakeClientError(Exception):
    def __init__(self, code: str):
        super().__init__("opaque fake AWS error")
        self.response = {"Error": {"Code": code}}


class FakeDynamoClient:
    """Thread-safe low-level DDB fake implementing the exact adapter calls."""

    def __init__(self):
        self.lock = threading.RLock()
        self.items: dict[tuple[str, str], dict[str, Any]] = {}
        self.get_calls: list[dict[str, Any]] = []
        self.put_calls: list[dict[str, Any]] = []
        self.delete_calls: list[dict[str, Any]] = []
        self.transaction_calls: list[dict[str, Any]] = []
        self.query_calls: list[dict[str, Any]] = []
        self.scan_calls: list[dict[str, Any]] = []
        self.crash_before_transaction = False
        self.crash_after_transaction = False
        self.fail_next_delete = False

    @staticmethod
    def _key(item: Mapping[str, Any]) -> tuple[str, str]:
        return item["pk"]["S"], item["sk"]["S"]

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        with self.lock:
            self.get_calls.append(deepcopy(kwargs))
            key = self._key(kwargs["Key"])
            item = self.items.get(key)
            return {"Item": deepcopy(item)} if item is not None else {}

    def put_item(self, **kwargs: Any) -> dict[str, Any]:
        with self.lock:
            self.put_calls.append(deepcopy(kwargs))
            item = deepcopy(kwargs["Item"])
            key = self._key(item)
            condition = kwargs["ConditionExpression"]
            current = self.items.get(key)
            if condition.startswith("attribute_not_exists"):
                if current is not None:
                    raise FakeClientError("ConditionalCheckFailedException")
            else:
                expected = int(kwargs["ExpressionAttributeValues"][":expected"]["N"])
                if current is None or int(current["version"]["N"]) != expected:
                    raise FakeClientError("ConditionalCheckFailedException")
            self.items[key] = item
            return {}

    def delete_item(self, **kwargs: Any) -> dict[str, Any]:
        with self.lock:
            self.delete_calls.append(deepcopy(kwargs))
            if self.fail_next_delete:
                self.fail_next_delete = False
                raise FakeClientError("InternalServerError")
            key = self._key(kwargs["Key"])
            current = self.items.get(key)
            values = kwargs["ExpressionAttributeValues"]
            if (
                current is None
                or current.get("active_pk") != values[":pk"]
                or current.get("active_sk") != values[":sk"]
                or current.get("authorization_key_sha256") != values[":key_sha"]
                or current.get("authorization_spec_sha256") != values[":spec_sha"]
            ):
                raise FakeClientError("ConditionalCheckFailedException")
            self.items.pop(key, None)
            return {}

    def transact_write_items(self, **kwargs: Any) -> dict[str, Any]:
        with self.lock:
            self.transaction_calls.append(deepcopy(kwargs))
            if self.crash_before_transaction:
                self.crash_before_transaction = False
                raise FakeClientError("InternalServerError")
            staged: list[tuple[str, tuple[str, str], dict[str, Any] | None]] = []
            for operation in kwargs["TransactItems"]:
                if "Put" in operation:
                    put = operation["Put"]
                    item = deepcopy(put["Item"])
                    key = self._key(item)
                    current = self.items.get(key)
                    condition = put["ConditionExpression"]
                    if condition.startswith("attribute_not_exists"):
                        if current is not None:
                            raise FakeClientError("TransactionCanceledException")
                    else:
                        expected = int(
                            put["ExpressionAttributeValues"][":expected"]["N"]
                        )
                        if current is None or int(current["version"]["N"]) != expected:
                            raise FakeClientError("TransactionCanceledException")
                    staged.append(("put", key, item))
                elif "Delete" in operation:
                    delete = operation["Delete"]
                    key = self._key(delete["Key"])
                    current = self.items.get(key)
                    values = delete["ExpressionAttributeValues"]
                    if (
                        current is None
                        or current.get("active_pk") != values[":pk"]
                        or current.get("active_sk") != values[":sk"]
                    ):
                        raise FakeClientError("TransactionCanceledException")
                    staged.append(("delete", key, None))
                else:
                    raise AssertionError(f"unsupported fake transaction: {operation}")
            for action, key, item in staged:
                if action == "put":
                    assert item is not None
                    self.items[key] = item
                else:
                    self.items.pop(key, None)
            if self.crash_after_transaction:
                self.crash_after_transaction = False
                raise FakeClientError("InternalServerError")
            return {}

    def scan(self, **kwargs: Any) -> dict[str, Any]:
        with self.lock:
            self.scan_calls.append(deepcopy(kwargs))
            return {
                "Items": [
                    deepcopy(item)
                    for item in self.items.values()
                    if item["pk"]["S"].startswith("CAS#RUNPOD#AUTH#")
                ]
            }

    def query(self, **kwargs: Any) -> dict[str, Any]:
        with self.lock:
            self.query_calls.append(deepcopy(kwargs))
            assert kwargs["IndexName"] == runtime.RECOVERY_INDEX_NAME
            cutoff = kwargs["ExpressionAttributeValues"][":cutoff"]["S"]
            partition = kwargs["ExpressionAttributeValues"][":partition"]["S"]
            eligible = [
                deepcopy(item)
                for item in self.items.values()
                if item.get("recovery_partition", {}).get("S") == partition
                and item.get("owner_lease_expires_at_utc", {}).get("S", "")
                <= cutoff
            ]
            eligible.sort(
                key=lambda item: (
                    item["owner_lease_expires_at_utc"]["S"],
                    item["pk"]["S"],
                    item["sk"]["S"],
                )
            )
            start = kwargs.get("ExclusiveStartKey")
            if start:
                marker = (
                    start["owner_lease_expires_at_utc"]["S"],
                    start["pk"]["S"],
                    start["sk"]["S"],
                )
                eligible = [
                    item
                    for item in eligible
                    if (
                        item["owner_lease_expires_at_utc"]["S"],
                        item["pk"]["S"],
                        item["sk"]["S"],
                    )
                    > marker
                ]
            limit = kwargs["Limit"]
            page = eligible[:limit]
            response: dict[str, Any] = {"Items": page}
            if len(eligible) > limit:
                final = page[-1]
                response["LastEvaluatedKey"] = {
                    "pk": deepcopy(final["pk"]),
                    "sk": deepcopy(final["sk"]),
                    "recovery_partition": deepcopy(final["recovery_partition"]),
                    "owner_lease_expires_at_utc": deepcopy(
                        final["owner_lease_expires_at_utc"]
                    ),
                }
            return response


class FakeKmsClient:
    def __init__(self):
        self.sign_calls: list[dict[str, Any]] = []
        self.verify_calls: list[dict[str, Any]] = []

    def sign(self, **kwargs: Any) -> dict[str, Any]:
        self.sign_calls.append(deepcopy(kwargs))
        digest = kwargs["Message"]
        return {
            "KeyId": KEY_ARN,
            "SigningAlgorithm": "ECDSA_SHA_256",
            "Signature": b"DER-test-signature-" + digest,
        }

    def verify(self, **kwargs: Any) -> dict[str, Any]:
        self.verify_calls.append(deepcopy(kwargs))
        return {"SignatureValid": True}


class FakeSts:
    def __init__(self, date_text: str = "Thu, 20 Aug 2026 12:00:00 GMT"):
        self.date_text = date_text
        self.calls = 0

    def get_caller_identity(self) -> dict[str, Any]:
        self.calls += 1
        return {"ResponseMetadata": {"HTTPHeaders": {"date": self.date_text}}}


class FakeHttpResponse:
    def __init__(
        self,
        status: int,
        body: bytes,
        *,
        content_type: str = "application/json",
        content_encoding: str = "",
        location: str | None = None,
        link: str | None = None,
    ):
        self.status = status
        self._body = body
        self._headers = {
            "Content-Type": content_type,
            "Content-Encoding": content_encoding,
            "Content-Length": str(len(body)),
            "Location": location,
            "Link": link,
            "X-Next-Cursor": None,
        }

    def getheader(self, name: str, default: Any = None) -> Any:
        value = self._headers.get(name)
        return default if value is None else value

    def read(self, count: int) -> bytes:
        return self._body[:count]


class FakeHttpConnection:
    def __init__(self, response: FakeHttpResponse):
        self.response = response
        self.calls: list[tuple[str, str, bytes | None, dict[str, str]]] = []
        self.closed = 0

    def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None,
        headers: dict[str, str],
    ) -> None:
        self.calls.append((method, path, body, deepcopy(headers)))

    def getresponse(self) -> FakeHttpResponse:
        return self.response

    def close(self) -> None:
        self.closed += 1


class ConnectionFactory:
    def __init__(self, connection: FakeHttpConnection):
        self.connection = connection
        self.calls: list[tuple[Any, ...]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> FakeHttpConnection:
        self.calls.append((args, kwargs))
        return self.connection


def exact_request_envelope(
    spec: guardian.AuthorizationSpec, request: bytes
) -> dict[str, Any]:
    return {
        "schema_version": runtime.EXECUTION_SCHEMA,
        "deployment_binding_sha256": BINDING,
        "authorization_key": {
            "issuer": spec.key.issuer,
            "provider_account_id": spec.key.provider_account_id,
            "authorization_id": spec.key.authorization_id,
        },
        "exact_create_request_base64": base64.b64encode(request).decode("ascii"),
    }


def enable_recovery_environment(monkeypatch) -> None:
    for name, value in {
        "ACTIVATION_MODE": "LIVE",
        "EXPECTED_AWS_REGION": "us-west-2",
        "AWS_REGION": "us-west-2",
        "AWS_ACCOUNT_ID": "123456789012",
        "DEPLOYMENT_BINDING_SHA256": BINDING,
        "PROVIDER_ACCOUNT_ID": ACCOUNT,
        "RECOVERY_ENABLED": "TRUE",
        "LEDGER_TABLE_NAME": "guardian-test-table",
        "STATE_MACHINE_ARN": (
            "arn:aws:states:us-west-2:123456789012:stateMachine:guardian"
        ),
        "KMS_SIGNING_KEY_ARN": KEY_ARN,
    }.items():
        monkeypatch.setenv(name, value)


def recovery_event(index: int = 1) -> dict[str, Any]:
    return {
        "version": "0",
        "id": f"00000000-0000-4000-8000-{index:012x}",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "123456789012",
        "time": guardian.iso_utc(BASE),
        "region": "us-west-2",
        "resources": [],
        "detail": {},
    }


def adapter_core(
    *, provider: core_fakes.FakeProvider | None = None, lease: int = 200
):
    client = FakeDynamoClient()
    store = runtime.DynamoDbConditionalStore(client, "guardian-test-table")
    provider = provider or core_fakes.FakeProvider()
    signer = core_fakes.FakeKmsSigner()
    clock = core_fakes.ManualClock()
    guard = core_fakes.FakeSecretGuard()
    engine = guardian.AwsProductionGuardianCore(
        store=store,
        transport=provider,
        signer=signer,
        clock=clock,
        secret_guard=guard,
    )
    spec, request = core_fakes.make_spec()
    engine.register_authorization(spec, exact_create_request_bytes=request)
    token = engine.claim_execution(
        spec.key,
        execution_arn=core_fakes.EXECUTION_1,
        lease_seconds=lease,
        exact_create_request_bytes=request,
        expected_authorization_spec_sha256=guardian.authorization_spec_sha256(spec),
    )
    return engine, client, provider, signer, clock, spec, request, token


def arm_and_reserve(values: tuple[Any, ...]):
    engine, _client, _provider, _signer, clock, spec, request, token = values
    engine.arm_precreate(token, exact_create_request_bytes=request)
    clock.set(BASE + timedelta(seconds=10))
    reservation = engine.reserve_create(token, exact_create_request_bytes=request)
    return reservation


def test_dynamodb_adapter_round_trips_core_lowercase_schema_losslessly():
    engine, client, _provider, _signer, _clock, spec, _request, _token = adapter_core()
    record = engine.read_record(spec.key)
    assert record["pk"] == spec.key.pk
    assert record["sk"] == "STATE#v1"
    physical = client.items[(spec.key.pk, spec.key.sk)]
    assert set(physical) >= {
        "pk",
        "sk",
        "version",
        "state",
        "record_blob",
        "owner_fence",
        "owner_execution_arn",
    }
    decoded = runtime.DynamoDbConditionalStore.decode_physical(physical)
    assert decoded == record
    assert "image_name" in decoded["authorization_spec"]
    assert "dedicated_public_key_sha256" in decoded["authorization_spec"]
    assert "max_cost_per_hour" in decoded["authorization_spec"]
    assert client.transaction_calls
    registration_ref = decoded["receipts"]["registration"]
    evidence = engine.resolve_receipt_reference(registration_ref)
    assert evidence["receipt_sha256"] == registration_ref["receipt_sha256"]
    evidence_key = runtime.DynamoDbConditionalStore._evidence_key(
        registration_ref["receipt_sha256"]
    )
    assert evidence_key in client.items


def test_dynamodb_physical_projection_tamper_fails_closed():
    values = adapter_core()
    _engine, client, _provider, _signer, _clock, spec, _request, _token = values
    item = client.items[(spec.key.pk, spec.key.sk)]
    item["state"] = {"S": "ATTACKER_STATE"}
    with pytest.raises(runtime.AdapterError, match="PHYSICAL_LOGICAL_MISMATCH"):
        runtime.DynamoDbConditionalStore.decode_physical(item)


def test_global_single_active_registration_has_one_winner_under_100_way_race():
    client = FakeDynamoClient()
    store = runtime.DynamoDbConditionalStore(client, "guardian-test-table")
    signer = core_fakes.FakeKmsSigner()
    clock = core_fakes.ManualClock()
    provider = core_fakes.FakeProvider()
    guard = core_fakes.FakeSecretGuard()
    base_spec, request = core_fakes.make_spec()
    barrier = threading.Barrier(100)
    successes: list[guardian.AuthorizationKey] = []
    failures: list[type[BaseException]] = []
    result_lock = threading.Lock()

    def register(index: int) -> None:
        key = guardian.AuthorizationKey(
            base_spec.key.issuer,
            base_spec.key.provider_account_id,
            f"singleton-race-{index:03d}",
        )
        engine = guardian.AwsProductionGuardianCore(
            store=store,
            transport=provider,
            signer=signer,
            clock=clock,
            secret_guard=guard,
        )
        barrier.wait()
        try:
            engine.register_authorization(
                replace(base_spec, key=key), exact_create_request_bytes=request
            )
        except BaseException as error:
            with result_lock:
                failures.append(type(error))
        else:
            with result_lock:
                successes.append(key)

    threads = [threading.Thread(target=register, args=(index,)) for index in range(100)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(successes) == 1
    assert len(failures) == 99
    pointer = client.items[(runtime.GLOBAL_ACTIVE_PK, runtime.GLOBAL_ACTIVE_SK)]
    assert pointer["active_pk"]["S"] == successes[0].pk
    assert pointer["active_sk"]["S"] == successes[0].sk
    heads = [
        item
        for item in client.items.values()
        if item.get("item_type", {}).get("S") == "GUARDIAN_HEAD"
    ]
    assert len(heads) == 1


def test_transaction_response_loss_after_create_marker_causes_safe_lost_attempt():
    provider = core_fakes.FakeProvider()
    values = adapter_core(provider=provider)
    engine, client, provider, _signer, _clock, _spec, request, token = values
    reservation = arm_and_reserve(values)
    client.crash_after_transaction = True
    with pytest.raises(guardian.CreateAlreadyDispatched):
        engine.dispatch_create(token, reservation, exact_create_request_bytes=request)
    record = engine.read_record(token.key)
    assert record["state"] == "CREATE_DISPATCHED_UNKNOWN"
    assert record["create_dispatch_count"] == 1
    assert provider.post_entries == 0
    with pytest.raises(guardian.CreateAlreadyDispatched):
        engine.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert provider.post_entries == 0


def test_transaction_failure_before_create_marker_is_retryable_without_provider_effect():
    provider = core_fakes.FakeProvider()
    values = adapter_core(provider=provider)
    engine, client, provider, _signer, _clock, spec, request, token = values
    reservation = arm_and_reserve(values)
    client.crash_before_transaction = True
    with pytest.raises(runtime.AdapterError, match="ATOMIC_TRANSITION_WRITE_FAILED"):
        engine.dispatch_create(token, reservation, exact_create_request_bytes=request)
    assert engine.read_record(spec.key)["state"] == "CREATE_RESERVED"
    assert provider.post_entries == 0
    response = core_fakes.response_201(spec.pod_name)
    provider.post_response = response
    provider.created_pod = json.loads(response.body)
    outcome = engine.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.target_bound is True
    assert provider.post_entries == 1


def test_one_hundred_concurrent_claims_have_one_winner_and_one_consumption():
    client = FakeDynamoClient()
    store = runtime.DynamoDbConditionalStore(client, "guardian-test-table")
    provider = core_fakes.FakeProvider()
    signer = core_fakes.FakeKmsSigner()
    clock = core_fakes.ManualClock()
    engine = guardian.AwsProductionGuardianCore(
        store=store,
        transport=provider,
        signer=signer,
        clock=clock,
        secret_guard=core_fakes.FakeSecretGuard(),
    )
    spec, request = core_fakes.make_spec()
    engine.register_authorization(spec, exact_create_request_bytes=request)
    barrier = threading.Barrier(100)
    winners: list[guardian.ExecutionToken] = []
    failures: list[BaseException] = []
    lock = threading.Lock()

    def claim(index: int) -> None:
        try:
            barrier.wait(timeout=10)
            token = engine.claim_execution(
                spec.key,
                execution_arn=(
                    "arn:aws:states:us-west-2:123456789012:execution:"
                    f"cas-runpod-guardian:contender-{index:03d}"
                ),
                lease_seconds=180,
                exact_create_request_bytes=request,
                expected_authorization_spec_sha256=(
                    guardian.authorization_spec_sha256(spec)
                ),
            )
            with lock:
                winners.append(token)
        except BaseException as error:
            with lock:
                failures.append(error)

    threads = [threading.Thread(target=claim, args=(index,)) for index in range(100)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    assert all(not thread.is_alive() for thread in threads)
    assert len(winners) == 1
    assert len(failures) == 99
    record = engine.read_record(spec.key)
    assert record["authorization_consumed"] is True


def test_wrong_exact_request_cannot_consume_claim_then_valid_claim_succeeds():
    client = FakeDynamoClient()
    store = runtime.DynamoDbConditionalStore(client, "guardian-test-table")
    signer = core_fakes.FakeKmsSigner()
    clock = core_fakes.ManualClock()
    provider = core_fakes.FakeProvider()
    guard = core_fakes.FakeSecretGuard()
    ports = runtime.RuntimePorts(store, signer, clock, guard, provider)
    engine = ports.core()
    spec, request = core_fakes.make_spec()
    engine.register_authorization(spec, exact_create_request_bytes=request)
    wrong = bytearray(request)
    wrong[-2] = ord(" ") if wrong[-2] != ord(" ") else ord("x")
    envelope = exact_request_envelope(spec, bytes(wrong))
    with pytest.raises(runtime.AdapterError, match="CLAIM_EXACT_REQUEST_HASH_MISMATCH"):
        runtime.execute_operation(
            "claim",
            {"execution_arn": core_fakes.EXECUTION_1, "envelope": envelope},
            ports,
        )
    record = engine.read_record(spec.key)
    assert record["state"] == "AUTHORIZED"
    assert record["authorization_consumed"] is False
    valid = runtime.execute_operation(
        "claim",
        {
            "execution_arn": core_fakes.EXECUTION_1,
            "envelope": exact_request_envelope(spec, request),
        },
        ports,
    )
    assert valid["token"]["fence"] == 1
    record = engine.read_record(spec.key)
    assert record["owner_fence"] == 1
    assert record["create_dispatch_count"] == 0
    assert provider.post_entries == 0


def test_one_hundred_concurrent_dispatches_cross_provider_boundary_once():
    provider = core_fakes.FakeProvider()
    values = adapter_core(provider=provider)
    engine, _client, provider, _signer, _clock, spec, request, token = values
    reservation = arm_and_reserve(values)
    response = core_fakes.response_201(spec.pod_name)
    provider.post_response = response
    provider.created_pod = json.loads(response.body)
    barrier = threading.Barrier(100)
    outcomes: list[Any] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def dispatch() -> None:
        try:
            barrier.wait(timeout=10)
            result = engine.dispatch_create(
                token, reservation, exact_create_request_bytes=request
            )
            with lock:
                outcomes.append(result)
        except BaseException as error:
            with lock:
                errors.append(error)

    threads = [threading.Thread(target=dispatch) for _ in range(100)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    assert all(not thread.is_alive() for thread in threads)
    assert provider.post_entries == 1
    assert provider.provider_create_commits == 1
    assert len(outcomes) == 1
    assert len(errors) == 99
    record = engine.read_record(spec.key)
    assert record["create_dispatch_count"] == 1
    assert record["state"] == "TARGET_BOUND"


@pytest.mark.parametrize("mode", ["crash_before_provider", "crash_after_provider"])
def test_crash_after_durable_marker_never_allows_second_create(mode: str):
    provider = core_fakes.FakeProvider()
    values = adapter_core(provider=provider, lease=20)
    engine, _client, provider, _signer, clock, spec, request, old = values
    reservation = arm_and_reserve(values)
    response = core_fakes.response_201(spec.pod_name)
    provider.post_response = response
    provider.created_pod = json.loads(response.body)
    provider.post_mode = mode
    with pytest.raises(core_fakes.HardCrash):
        engine.dispatch_create(old, reservation, exact_create_request_bytes=request)
    assert provider.post_entries == 1
    clock.set(BASE + timedelta(seconds=31))
    new = engine.claim_execution(
        spec.key, execution_arn=core_fakes.EXECUTION_2, lease_seconds=180
    )
    outcome = engine.reconcile_ambiguous_create(new)
    assert provider.post_entries == 1
    if mode == "crash_after_provider":
        assert outcome.target_bound is True
    else:
        assert outcome.target_bound is False
    with pytest.raises(guardian.CreateAlreadyDispatched):
        engine.dispatch_create(new, reservation, exact_create_request_bytes=request)
    assert provider.post_entries == 1


def test_exact_201_then_exact_get_admission_deadline_stop_and_terminal_proof():
    provider = core_fakes.FakeProvider()
    values = adapter_core(provider=provider)
    engine, _client, provider, signer, clock, spec, request, token = values
    reservation = arm_and_reserve(values)
    response = core_fakes.response_201(spec.pod_name)
    provider.post_response = response
    provider.created_pod = json.loads(response.body)
    outcome = engine.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.target_bound is True and outcome.launch_admitted is False
    admission = engine.verify_post_bind_launch_admission(token)
    signer.assert_valid(admission)
    assert admission["payload"]["launch_admitted"] is True
    assert provider.get_calls == ["newpod1234"]
    clock.set(BASE + timedelta(seconds=14))
    token = engine.heartbeat(token, expected_sequence=0, lease_seconds=200)
    clock.set(BASE + timedelta(seconds=14))
    terminal = engine.request_stop(token)
    assert terminal is not None
    signer.assert_valid(terminal)
    assert provider.stop_calls == ["newpod1234"]
    assert terminal["payload"]["terminal_provider_proof"] is True
    assert terminal["payload"]["containment_sla_met"] is True
    serialized = json.dumps(terminal, sort_keys=True)
    assert "terminal_exact_body_base64" not in serialized
    assert "live_get_exact_body_base64" not in serialized
    assert terminal["payload"]["terminal_semantic_projection"]["pod"] == {
        "id": "newpod1234",
        "desired_status": "EXITED",
    }


def test_orchestration_routes_exact_id_stop_before_admission_or_kms_finalize():
    provider = core_fakes.FakeProvider()
    values = adapter_core(provider=provider)
    engine, _client, provider, _signer, _clock, spec, request, token = values
    reservation = arm_and_reserve(values)
    response = core_fakes.response_201(spec.pod_name)
    provider.post_response = response
    provider.created_pod = json.loads(response.body)
    engine.dispatch_create(token, reservation, exact_create_request_bytes=request)
    record = engine.read_record(spec.key)
    assert record["launch_admission_status"] == "PENDING_EXACT_GET"
    due = guardian.parse_utc(spec.stop_dispatch_at_utc)
    record["owner_lease_expires_at_utc"] = guardian.iso_utc(
        due + timedelta(seconds=30)
    )
    assert runtime._inspect_next(record, token, due) == ("STOP", 0)
    record["launch_admission_status"] = "INELIGIBLE_CREATE_EVIDENCE"
    assert runtime._inspect_next(record, token, due - timedelta(seconds=1)) == (
        "STOP",
        0,
    )
    record["state"] = "STOPPING"
    proof = guardian.parse_utc(spec.terminal_proof_deadline_utc)
    record["owner_lease_expires_at_utc"] = guardian.iso_utc(
        proof + timedelta(seconds=30)
    )
    assert runtime._inspect_next(
        record, token, proof, post_deadline_stop_attempted=False
    ) == ("STOP", 0)
    assert runtime._inspect_next(
        record, token, proof, post_deadline_stop_attempted=True
    ) == ("FINALIZE_CONTAINMENT_FAILURE", 0)


def test_expired_predispatch_routes_signed_zero_post_safe_loss():
    values = adapter_core()
    engine, _client, _provider, _signer, _clock, spec, request, token = values
    arm_and_reserve(values)
    record = engine.read_record(spec.key)
    after_window = guardian.parse_utc(spec.creation_window_end_utc) + timedelta(
        seconds=1
    )
    record["owner_lease_expires_at_utc"] = guardian.iso_utc(
        after_window + timedelta(seconds=30)
    )
    assert runtime._inspect_next(record, token, after_window) == (
        "FINALIZE_NO_CREATE_SAFE_LOSS",
        0,
    )


def test_maximum_2048_item_prearm_still_leaves_create_and_containment_headroom():
    pods = [
        {
            "id": f"oldpod{index:08d}",
            "name": f"preexisting-{index:08d}",
            "desiredStatus": "EXITED",
        }
        for index in range(guardian.MAX_INVENTORY_ITEMS)
    ]
    provider = core_fakes.FakeProvider(pods)
    values = adapter_core(provider=provider)
    engine, client, provider, _signer, clock, spec, request, token = values
    arm_receipt = engine.arm_precreate(token, exact_create_request_bytes=request)
    assert arm_receipt["payload"]["inventory_count"] == guardian.MAX_INVENTORY_ITEMS
    head = engine.read_record(spec.key)
    assert len(_canonical_for_test(head)) <= guardian.MAX_PRECREATE_HEAD_BYTES
    assert len(head["prearm_inventory_ids"]) == guardian.MAX_INVENTORY_ITEMS
    clock.set(BASE + timedelta(seconds=10))
    reservation = engine.reserve_create(token, exact_create_request_bytes=request)
    response = core_fakes.response_201(spec.pod_name)
    provider.post_response = response
    provider.created_pod = json.loads(response.body)
    engine.dispatch_create(token, reservation, exact_create_request_bytes=request)
    admission = engine.verify_post_bind_launch_admission(token)
    assert admission["payload"]["launch_admitted"] is True
    clock.set(BASE + timedelta(seconds=14))
    token = engine.heartbeat(token, expected_sequence=0, lease_seconds=200)
    clock.set(BASE + timedelta(seconds=100))
    terminal = engine.request_stop(token)
    assert terminal is not None
    assert terminal["payload"]["terminal_provider_proof"] is True
    assert len(_canonical_for_test(engine.read_record(spec.key))) < guardian.MAX_LEDGER_ITEM_BYTES
    evidence_items = [
        item
        for item in client.items.values()
        if item["pk"]["S"].startswith("EVIDENCE#SHA256#")
    ]
    assert len(evidence_items) >= 7


def _canonical_for_test(value: Any) -> bytes:
    return guardian.canonical_json_bytes(value)


def test_one_thousand_takeovers_keep_head_compact_and_late_exact_id_stop_works():
    provider = core_fakes.FakeProvider()
    values = adapter_core(provider=provider)
    engine, client, provider, _signer, clock, spec, request, token = values
    reservation = arm_and_reserve(values)
    response = core_fakes.response_201(spec.pod_name)
    provider.post_response = response
    provider.created_pod = json.loads(response.body)
    engine.dispatch_create(token, reservation, exact_create_request_bytes=request)
    engine.verify_post_bind_launch_admission(token)
    clock.set(BASE + timedelta(seconds=291))
    latest = token
    for index in range(1001):
        latest = engine.claim_execution(
            spec.key,
            execution_arn=(
                "arn:aws:states:us-west-2:123456789012:execution:"
                f"cas-runpod-guardian:takeover-{index:04d}"
            ),
            lease_seconds=5,
        )
        clock.advance(5)
    head = engine.read_record(spec.key)
    assert head["takeover_receipt_count"] == 1001
    assert set(head["receipts"]) >= {"create_dispatch", "binding"}
    assert not any(name.startswith("takeover_") for name in head["receipts"])
    assert len(_canonical_for_test(head)) < guardian.MAX_LEDGER_ITEM_BYTES
    # The last token expires at the exact +5 boundary; use a fresh successor
    # and prove that late containment remains available indefinitely.
    latest = engine.claim_execution(
        spec.key,
        execution_arn=(
            "arn:aws:states:us-west-2:123456789012:execution:"
            "cas-runpod-guardian:takeover-final"
        ),
        lease_seconds=5,
    )
    terminal = engine.request_stop(latest)
    assert terminal is not None
    assert provider.stop_calls == ["newpod1234"]
    assert terminal["payload"]["terminal_provider_proof"] is True
    sealed = engine.read_record(spec.key)
    assert "latest_takeover" in sealed["receipts"]
    assert terminal["payload"]["containment_sla_met"] is False
    evidence_count = sum(
        item["pk"]["S"].startswith("EVIDENCE#SHA256#")
        for item in client.items.values()
    )
    assert 8 <= evidence_count < 50


def test_kms_adapter_uses_exact_32_byte_digest_not_raw_message_and_verifies():
    kms = FakeKmsClient()
    signer = runtime.AwsKmsReceiptSigner(kms, KEY_ARN)
    store = core_fakes.MemoryDynamoStore()
    engine = guardian.AwsProductionGuardianCore(
        store=store,
        transport=core_fakes.FakeProvider(),
        signer=signer,
        clock=core_fakes.ManualClock(),
        secret_guard=core_fakes.FakeSecretGuard(),
    )
    spec, request = core_fakes.make_spec()
    receipt = engine.register_authorization(spec, exact_create_request_bytes=request)
    assert len(kms.sign_calls) == 1
    call = kms.sign_calls[0]
    assert call["MessageType"] == "DIGEST"
    assert call["SigningAlgorithm"] == "ECDSA_SHA_256"
    assert len(call["Message"]) == 32
    assert base64.b64decode(receipt["kms_digest_base64"], validate=True) == call["Message"]
    assert runtime.verify_receipt_with_kms(
        receipt, kms_client=kms, expected_key_arn=KEY_ARN
    )
    verify_call = kms.verify_calls[0]
    assert verify_call["MessageType"] == "DIGEST"
    assert verify_call["Message"] == call["Message"]


def test_kms_receipt_tamper_rejected_before_verify_call():
    kms = FakeKmsClient()
    signer = runtime.AwsKmsReceiptSigner(kms, KEY_ARN)
    engine = guardian.AwsProductionGuardianCore(
        store=core_fakes.MemoryDynamoStore(),
        transport=core_fakes.FakeProvider(),
        signer=signer,
        clock=core_fakes.ManualClock(),
        secret_guard=core_fakes.FakeSecretGuard(),
    )
    spec, request = core_fakes.make_spec()
    receipt = engine.register_authorization(spec, exact_create_request_bytes=request)
    tampered = deepcopy(receipt)
    tampered["payload"]["transition"] = "ATTACKER"
    with pytest.raises(guardian.ValidationError, match="self-hash"):
        runtime.verify_receipt_with_kms(
            tampered, kms_client=kms, expected_key_arn=KEY_ARN
        )
    assert kms.verify_calls == []


def test_secret_guard_rejects_direct_encoded_escaped_and_fragmented_credentials():
    guard = runtime.ExactSecretGuard((API_KEY,))
    escaped = "".join(f"\\u{ord(character):04x}" for character in API_KEY.decode())
    midpoint = len(API_KEY) // 2
    samples = (
        API_KEY,
        b"prefix" + API_KEY + b"suffix",
        base64.b64encode(API_KEY),
        base64.urlsafe_b64encode(API_KEY).rstrip(b"="),
        base64.b32encode(API_KEY),
        base64.b32encode(b"Bearer " + API_KEY).rstrip(b"="),
        API_KEY.hex().encode("ascii"),
        b"".join(f"%{byte:02x}".encode("ascii") for byte in API_KEY),
        b"".join(
            f"%{byte:02X}".encode("ascii")
            if index % 2
            else f"%{byte:02x}".encode("ascii")
            for index, byte in enumerate(API_KEY)
        ),
        base64.b64encode(b"Bearer " + API_KEY),
        ('{"credential":"' + escaped + '"}').encode("ascii"),
        json.dumps(
            {
                "first": API_KEY[:midpoint].decode("ascii"),
                "second": API_KEY[midpoint:].decode("ascii"),
            },
            separators=(",", ":"),
        ).encode("ascii"),
    )
    for raw in samples:
        with pytest.raises(runtime.SecretExposure, match="SECRET_EXPOSURE_REJECTED"):
            guard.assert_safe(raw)
    guard.assert_safe(b'{"safe":"provider evidence"}')


def test_provider_secret_schema_and_binding_are_exact():
    class Secrets:
        def get_secret_value(self, **kwargs: Any) -> dict[str, Any]:
            return {
                "SecretString": json.dumps(
                    {
                        "schema_version": runtime.SECRET_SCHEMA,
                        "provider_account_id": ACCOUNT,
                        "api_key": API_KEY.decode("ascii"),
                        "deployment_binding_sha256": BINDING,
                    }
                )
            }

    result = runtime.load_provider_secret(
        Secrets(),
        "arn:aws:secretsmanager:us-west-2:123456789012:secret:test-secret",
    )
    assert result.provider_account_id == ACCOUNT
    assert result.api_key == API_KEY
    assert result.deployment_binding_sha256 == BINDING


def test_trusted_clock_uses_aws_date_and_rejects_skew():
    clock = runtime.AwsTrustedClock(
        FakeSts(), wall_clock=lambda: BASE, maximum_skew_seconds=1
    )
    assert clock.now() == BASE
    skewed = runtime.AwsTrustedClock(
        FakeSts("Thu, 20 Aug 2026 12:10:00 GMT"),
        wall_clock=lambda: BASE,
        maximum_skew_seconds=1,
    )
    with pytest.raises(runtime.AdapterError, match="SKEW_EXCEEDED"):
        skewed.now()


def test_containment_clock_uncertainty_is_sticky_across_success_failure_success():
    class AlternatingTrustedClock:
        def __init__(self):
            self.calls = 0

        def now(self) -> datetime:
            self.calls += 1
            if self.calls == 1:
                return BASE
            if self.calls == 2:
                raise runtime.AdapterError("TRUSTED_CLOCK_STS_UNAVAILABLE")
            return BASE + timedelta(seconds=2)

    callbacks: list[str] = []
    clock = runtime.ContainmentClock(
        AlternatingTrustedClock(),
        wall_clock=lambda: BASE + timedelta(seconds=1),
    )
    clock.on_uncertainty(lambda: callbacks.append("uncertain"))
    assert clock.now() == BASE
    assert clock.now() == BASE + timedelta(seconds=1)
    assert clock.time_uncertain is True
    assert clock.now() == BASE + timedelta(seconds=2)
    assert clock.time_uncertain is True
    assert callbacks == ["uncertain"]
    with pytest.raises(
        runtime.AdapterError, match="CONTAINMENT_PROOF_TRUSTED_TIME_UNAVAILABLE"
    ):
        clock.require_trusted_time_for_proof()


def make_transport(
    response: FakeHttpResponse, allowed: frozenset[str]
) -> tuple[runtime.StrictRunPodTransport, FakeHttpConnection, ConnectionFactory]:
    connection = FakeHttpConnection(response)
    factory = ConnectionFactory(connection)
    guard = runtime.ExactSecretGuard((API_KEY,))
    transport = runtime.StrictRunPodTransport(
        provider_account_id=ACCOUNT,
        api_key=API_KEY,
        secret_guard=guard,
        allowed_operations=allowed,
        connection_factory=factory,
    )
    return transport, connection, factory


def test_raw_create_is_one_exact_post_and_preserves_201_bytes():
    body = guardian.canonical_json_bytes({"id": "newpod1234", "name": "test"})
    response = FakeHttpResponse(201, body)
    transport, connection, factory = make_transport(response, frozenset({"CREATE"}))
    exact_request = guardian.canonical_json_bytes({"safe": "request"})
    result = transport.post_create(ACCOUNT, guardian.CREATE_ENDPOINT, exact_request)
    assert result.status_code == 201
    assert result.body == body
    assert result.effective_url == guardian.CREATE_ENDPOINT
    assert len(factory.calls) == 1
    assert len(connection.calls) == 1
    method, path, sent, headers = connection.calls[0]
    assert (method, path, sent) == ("POST", "/v1/pods", exact_request)
    assert headers["Authorization"] == "Bearer " + API_KEY.decode("ascii")
    assert connection.closed == 1


def test_transport_enforces_one_monotonic_total_deadline_across_all_phases():
    body = guardian.canonical_json_bytes({"id": "newpod1234"})
    connection = FakeHttpConnection(FakeHttpResponse(200, body))
    values = iter((0.0, 3.0, 7.0, 8.01))
    transport = runtime.StrictRunPodTransport(
        provider_account_id=ACCOUNT,
        api_key=API_KEY,
        secret_guard=runtime.ExactSecretGuard((API_KEY,)),
        allowed_operations=frozenset({"GET"}),
        connection_factory=ConnectionFactory(connection),
        timeout_seconds=8,
        monotonic_clock=lambda: next(values),
    )
    with pytest.raises(runtime.TransportError, match="TOTAL_DEADLINE_EXCEEDED"):
        transport.get_pod(ACCOUNT, "newpod1234")
    assert len(connection.calls) == 1
    assert connection.closed == 1


def test_transport_watchdog_bounds_a_blocked_request_phase_without_retry():
    class BlockingConnection(FakeHttpConnection):
        def __init__(self):
            super().__init__(FakeHttpResponse(200, b"{}\n"))
            self.request_entered = threading.Event()
            self.release = threading.Event()

        def request(
            self,
            method: str,
            path: str,
            *,
            body: bytes | None,
            headers: dict[str, str],
        ) -> None:
            self.calls.append((method, path, body, deepcopy(headers)))
            self.request_entered.set()
            self.release.wait(timeout=5)

        def close(self) -> None:
            self.closed += 1
            self.release.set()

    connection = BlockingConnection()
    transport = runtime.StrictRunPodTransport(
        provider_account_id=ACCOUNT,
        api_key=API_KEY,
        secret_guard=runtime.ExactSecretGuard((API_KEY,)),
        allowed_operations=frozenset({"GET"}),
        connection_factory=ConnectionFactory(connection),
        timeout_seconds=1,
    )
    started = time.monotonic()
    with pytest.raises(runtime.TransportError, match="TOTAL_DEADLINE_EXCEEDED"):
        transport.get_pod(ACCOUNT, "newpod1234")
    elapsed = time.monotonic() - started
    assert connection.request_entered.is_set()
    assert len(connection.calls) == 1
    assert connection.closed >= 1
    assert elapsed < 1.5


def test_secretless_core_boundary_invokes_only_its_exact_proxy_method():
    response_body = guardian.canonical_json_bytes(
        {"id": "newpod1234", "name": "test"}
    )

    class InvokeClient:
        def __init__(self):
            self.calls: list[dict[str, Any]] = []

        def invoke(self, **kwargs: Any) -> dict[str, Any]:
            self.calls.append(deepcopy(kwargs))
            event = json.loads(kwargs["Payload"])
            assert event["operation"] == "CREATE"
            reply = {
                "schema_version": runtime.PROXY_SCHEMA,
                "status_code": 201,
                "body_base64": base64.b64encode(response_body).decode("ascii"),
                "effective_url": guardian.CREATE_ENDPOINT,
                "content_type": "application/json",
                "content_encoding": "",
                "compiled_core_lock_sha256": CORE_LOCK,
            }
            return {
                "StatusCode": 200,
                "Payload": io.BytesIO(guardian.canonical_json_bytes(reply)),
            }

    client = InvokeClient()
    boundary = runtime.LambdaProviderBoundary(
        client,
        function_arn=(
            "arn:aws:lambda:us-west-2:123456789012:function:create-proxy"
        ),
        deployment_binding_sha256=BINDING,
        provider_account_id=ACCOUNT,
        allowed_operations=frozenset({"GUARD", "CREATE"}),
    )
    request = guardian.canonical_json_bytes({"safe": "request"})
    key = guardian.AuthorizationKey("owner.example", ACCOUNT, "proxy-test")
    token = guardian.ExecutionToken(key, core_fakes.EXECUTION_1, 1, 0)
    reservation = guardian.CreateReservation(key, "a" * 64, hashlib.sha256(request).hexdigest())
    boundary.bind_create_capability(
        key=key,
        token=token,
        reservation=reservation,
        owner_lease_expires_at_utc=guardian.iso_utc(BASE + timedelta(seconds=100)),
        not_after_utc=guardian.iso_utc(BASE + timedelta(seconds=20)),
    )
    response = boundary.post_create(ACCOUNT, guardian.CREATE_ENDPOINT, request)
    assert response.status_code == 201 and response.body == response_body
    assert len(client.calls) == 1


def test_split_stop_boundary_sends_stop_then_exact_get_terminal_proof():
    provider = core_fakes.FakeProvider()
    values = adapter_core(provider=provider)
    engine, client, provider, signer, clock, spec, request, token = values
    reservation = arm_and_reserve(values)
    response = core_fakes.response_201(spec.pod_name)
    provider.post_response = response
    provider.created_pod = json.loads(response.body)
    engine.dispatch_create(token, reservation, exact_create_request_bytes=request)
    provider.pods["newpod1234"]["desiredStatus"] = "EXITED"
    clock.set(BASE + timedelta(seconds=14))

    class InvokeClient:
        def __init__(self):
            self.operations: list[str] = []
            self.calls: list[dict[str, Any]] = []

        def invoke(self, **kwargs: Any) -> dict[str, Any]:
            self.calls.append(deepcopy(kwargs))
            event = json.loads(kwargs["Payload"])
            operation = event["operation"]
            self.operations.append(operation)
            if operation == "GUARD":
                reply = {
                    "schema_version": runtime.PROXY_SCHEMA,
                    "safe": True,
                    "compiled_core_lock_sha256": CORE_LOCK,
                }
            elif operation == "STOP":
                reply = {
                    "schema_version": runtime.PROXY_SCHEMA,
                    "status_code": 200,
                    "body_base64": base64.b64encode(b'{"ok":true}\n').decode(),
                    "effective_url": f"{guardian.CREATE_ENDPOINT}/newpod1234/stop",
                    "content_type": "application/json",
                    "content_encoding": "",
                    "compiled_core_lock_sha256": CORE_LOCK,
                }
            elif operation == "GET":
                terminal_body = guardian.canonical_json_bytes(
                    provider.pods["newpod1234"]
                )
                reply = {
                    "schema_version": runtime.PROXY_SCHEMA,
                    "status_code": 200,
                    "body_base64": base64.b64encode(terminal_body).decode(),
                    "effective_url": f"{guardian.CREATE_ENDPOINT}/newpod1234",
                    "content_type": "application/json",
                    "content_encoding": "",
                    "compiled_core_lock_sha256": CORE_LOCK,
                }
            else:
                raise AssertionError(operation)
            return {
                "StatusCode": 200,
                "Payload": io.BytesIO(guardian.canonical_json_bytes(reply)),
            }

    invoke = InvokeClient()
    stop_boundary = runtime.LambdaProviderBoundary(
        invoke,
        function_arn="arn:aws:lambda:us-west-2:123456789012:function:stop-proxy",
        deployment_binding_sha256=BINDING,
        provider_account_id=ACCOUNT,
        allowed_operations=frozenset({"GUARD", "STOP"}),
    )
    observe_boundary = runtime.LambdaProviderBoundary(
        invoke,
        function_arn="arn:aws:lambda:us-west-2:123456789012:function:observe-proxy",
        deployment_binding_sha256=BINDING,
        provider_account_id=ACCOUNT,
        allowed_operations=frozenset({"GUARD", "GET"}),
    )
    split = runtime.SplitStopProviderBoundary(stop_boundary, observe_boundary)
    stop_engine = guardian.AwsProductionGuardianCore(
        store=runtime.DynamoDbConditionalStore(client, "guardian-test-table"),
        signer=signer,
        clock=clock,
        secret_guard=split,
        transport=split,
    )
    terminal = stop_engine.request_stop(token)
    assert terminal is not None
    assert terminal["payload"]["terminal_provider_proof"] is True
    assert invoke.operations == ["STOP", "GET", "GUARD"]
    assert all(call["InvocationType"] == "RequestResponse" for call in invoke.calls)


def test_provider_proxy_handler_enforces_method_and_normalized_secret_guard(
    monkeypatch,
):
    monkeypatch.setenv("ACTIVATION_MODE", "LIVE")
    monkeypatch.setenv("EXPECTED_AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_ACCOUNT_ID", "123456789012")
    monkeypatch.setenv("DEPLOYMENT_BINDING_SHA256", BINDING)
    monkeypatch.setenv("PROVIDER_ACCOUNT_ID", ACCOUNT)
    guard = runtime.ExactSecretGuard((API_KEY,))
    transport = runtime.DenyProviderTransport()
    monkeypatch.setattr(
        runtime,
        "_PROXY_TRANSPORT_FACTORY",
        lambda capability, environment: (transport, guard),
    )
    escaped = "".join(f"\\u{ord(character):04x}" for character in API_KEY.decode())
    leaked = ('{"value":"' + escaped + '"}').encode("ascii")
    event = {
        "schema_version": runtime.PROXY_SCHEMA,
        "deployment_binding_sha256": BINDING,
        "provider_account_id": ACCOUNT,
        "operation": "GUARD",
        "payload": {"raw_base64": base64.b64encode(leaked).decode("ascii")},
    }
    with pytest.raises(runtime.SafeLambdaFailure) as caught:
        runtime.create_proxy_handler(event, None)
    assert API_KEY.decode("ascii") not in str(caught.value)
    forbidden = deepcopy(event)
    forbidden["operation"] = "CREATE"
    forbidden["payload"] = {
        "endpoint": guardian.CREATE_ENDPOINT,
        "body_base64": base64.b64encode(b"{}").decode("ascii"),
    }
    with pytest.raises(runtime.SafeLambdaFailure, match="ADAPTERERROR"):
        runtime.observe_proxy_handler(forbidden, None)


@pytest.mark.parametrize("lose_consume_ack", [False, True])
def test_create_proxy_atomically_consumes_unique_one_use_capability_before_post(
    monkeypatch, lose_consume_ack: bool
):
    monkeypatch.setenv("ACTIVATION_MODE", "LIVE")
    monkeypatch.setenv("EXPECTED_AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("DEPLOYMENT_BINDING_SHA256", BINDING)
    monkeypatch.setenv("PROVIDER_ACCOUNT_ID", ACCOUNT)
    monkeypatch.setenv("LEDGER_TABLE_NAME", "guardian-test-table")
    spec, request = core_fakes.make_spec()
    provider = core_fakes.FakeProvider()
    provider.post_response = core_fakes.response_201(spec.pod_name)
    guard = runtime.ExactSecretGuard((API_KEY,))
    monkeypatch.setattr(
        runtime,
        "_PROXY_TRANSPORT_FACTORY",
        lambda capability, environment: (provider, guard),
    )

    class CapabilityDdb:
        def __init__(self):
            self.consumed = False
            self.tokens: list[str] = []
            self.cached: set[str] = set()
            self.lose_once = lose_consume_ack

        def transact_write_items(self, **kwargs: Any) -> dict[str, Any]:
            token = kwargs["ClientRequestToken"]
            self.tokens.append(token)
            if token in self.cached:
                return {}
            if self.consumed:
                raise FakeClientError("TransactionCanceledException")
            self.consumed = True
            self.cached.add(token)
            if self.lose_once:
                self.lose_once = False
                raise FakeClientError("InternalServerError")
            return {}

    ddb = CapabilityDdb()
    monkeypatch.setattr(runtime, "_CREATE_CAPABILITY_DDB_FACTORY", lambda env: ddb)
    payload = {
        "endpoint": guardian.CREATE_ENDPOINT,
        "body_base64": base64.b64encode(request).decode("ascii"),
        "head_pk": spec.key.pk,
        "head_sk": spec.key.sk,
        "reservation_id": "a" * 64,
        "request_sha256": hashlib.sha256(request).hexdigest(),
        "owner_fence": 1,
        "owner_execution_arn": core_fakes.EXECUTION_1,
        "owner_lease_expires_at_utc": guardian.iso_utc(BASE + timedelta(seconds=100)),
        "not_after_utc": guardian.iso_utc(BASE + timedelta(seconds=20)),
    }
    event = {
        "schema_version": runtime.PROXY_SCHEMA,
        "deployment_binding_sha256": BINDING,
        "provider_account_id": ACCOUNT,
        "operation": "CREATE",
        "payload": payload,
    }
    if lose_consume_ack:
        with pytest.raises(runtime.SafeLambdaFailure):
            runtime.create_proxy_handler(event, None)
        assert provider.post_entries == 0
    else:
        response = runtime.create_proxy_handler(event, None)
        assert response["status_code"] == 201
        assert provider.post_entries == 1
    with pytest.raises(runtime.SafeLambdaFailure):
        runtime.create_proxy_handler(event, None)
    assert provider.post_entries == (0 if lose_consume_ack else 1)
    assert len(ddb.tokens) == 2
    assert ddb.tokens[0] != ddb.tokens[1]


def test_create_capability_rejects_expired_or_successor_fence_before_ddb(monkeypatch):
    spec, request = core_fakes.make_spec()
    calls: list[Any] = []
    monkeypatch.setattr(runtime, "_CREATE_CAPABILITY_DDB_FACTORY", lambda env: calls)
    payload = {
        "endpoint": guardian.CREATE_ENDPOINT,
        "body_base64": base64.b64encode(request).decode("ascii"),
        "head_pk": spec.key.pk,
        "head_sk": spec.key.sk,
        "reservation_id": "b" * 64,
        "request_sha256": hashlib.sha256(request).hexdigest(),
        "owner_fence": 1,
        "owner_execution_arn": core_fakes.EXECUTION_1,
        "owner_lease_expires_at_utc": guardian.iso_utc(BASE + timedelta(seconds=9)),
        "not_after_utc": guardian.iso_utc(BASE + timedelta(seconds=9)),
    }
    with pytest.raises(runtime.AdapterError, match="CREATE_CAPABILITY_IDENTITY_INVALID"):
        runtime._consume_create_capability(
            {"AWS_REGION": "us-west-2", "LEDGER_TABLE_NAME": "table"},
            payload,
            request,
        )
    assert calls == []
    # The real transaction binds both dispatch and current owner fences, so a
    # successor claim makes the ConditionCheck fail before POST.
    source = (SRC / "guardian_runtime.py").read_text("utf-8")
    assert '"#current_fence": "owner_fence"' in source
    assert '"#dispatch_fence": "create_dispatch_owner_fence"' in source


def test_exact_id_get_and_stop_paths_are_fixed_and_no_redirect_is_followed():
    body = guardian.canonical_json_bytes({"id": "newpod1234"})
    get_transport, get_connection, _ = make_transport(
        FakeHttpResponse(200, body), frozenset({"GET"})
    )
    result = get_transport.get_pod(ACCOUNT, "newpod1234")
    assert result.effective_url == guardian.CREATE_ENDPOINT + "/newpod1234"
    assert get_connection.calls[0][0:2] == ("GET", "/v1/pods/newpod1234")

    stop_transport, stop_connection, _ = make_transport(
        FakeHttpResponse(
            302,
            b"{}\n",
            location="https://attacker.invalid/steal",
        ),
        frozenset({"STOP"}),
    )
    with pytest.raises(runtime.TransportError, match="REDIRECT_REJECTED"):
        stop_transport.stop_pod(ACCOUNT, "newpod1234")
    assert len(stop_connection.calls) == 1
    assert stop_connection.calls[0][0:2] == (
        "POST",
        "/v1/pods/newpod1234/stop",
    )


def test_current_single_page_inventory_rejects_unreviewed_pagination_signal():
    response = FakeHttpResponse(200, b"[]\n", link='</v1/pods?cursor=x>; rel="next"')
    transport, connection, _ = make_transport(response, frozenset({"LIST"}))
    with pytest.raises(runtime.TransportError, match="PAGINATION_REJECTED"):
        transport.list_all_pods(ACCOUNT)
    assert len(connection.calls) == 1


def test_split_provider_method_allowlists_deny_cross_boundary_calls():
    transport, connection, _ = make_transport(
        FakeHttpResponse(200, b"[]\n"), frozenset({"GET"})
    )
    with pytest.raises(runtime.TransportError, match="CREATE_NOT_ALLOWED"):
        transport.post_create(ACCOUNT, guardian.CREATE_ENDPOINT, b"{}\n")
    with pytest.raises(runtime.TransportError, match="STOP_NOT_ALLOWED"):
        transport.stop_pod(ACCOUNT, "newpod1234")
    with pytest.raises(runtime.TransportError, match="LIST_NOT_ALLOWED"):
        transport.list_all_pods(ACCOUNT)
    assert connection.calls == []


def test_handler_error_never_echoes_secret_event_or_provider_text(monkeypatch):
    spec, request = core_fakes.make_spec()
    envelope = exact_request_envelope(spec, request)
    monkeypatch.setenv("ACTIVATION_MODE", "LIVE")
    monkeypatch.setenv("EXPECTED_AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("DEPLOYMENT_BINDING_SHA256", BINDING)
    monkeypatch.setenv("PROVIDER_ACCOUNT_ID", ACCOUNT)

    def fail_factory(capability: str, environment: Mapping[str, str]):
        raise RuntimeError("provider said " + API_KEY.decode("ascii"))

    monkeypatch.setattr(runtime, "_PORTS_FACTORY", fail_factory)
    with pytest.raises(runtime.SafeLambdaFailure) as caught:
        runtime.create_handler(
            {"operation": "dispatch", "envelope": envelope}, None
        )
    text = str(caught.value)
    assert API_KEY.decode("ascii") not in text
    assert "provider said" not in text
    assert text == "GUARDIAN_FAIL_CLOSED:RUNTIMEERROR"


def test_inert_activation_fails_before_ports_or_provider(monkeypatch):
    spec, request = core_fakes.make_spec()
    envelope = exact_request_envelope(spec, request)
    calls: list[str] = []
    monkeypatch.setenv("ACTIVATION_MODE", "INERT")
    monkeypatch.setenv("EXPECTED_AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("DEPLOYMENT_BINDING_SHA256", BINDING)
    monkeypatch.setenv("PROVIDER_ACCOUNT_ID", ACCOUNT)
    monkeypatch.setattr(
        runtime,
        "_PORTS_FACTORY",
        lambda capability, environment: calls.append(capability),
    )
    with pytest.raises(runtime.SafeLambdaFailure, match="ACTIVATIONERROR"):
        runtime.create_handler(
            {"operation": "dispatch", "envelope": envelope}, None
        )
    assert calls == []


def test_s3_and_sts_outage_after_bind_still_sends_stop_and_cannot_claim_sla(
    monkeypatch,
):
    class ContainmentProvider(core_fakes.FakeProvider):
        def __init__(self):
            super().__init__()
            self.observation_allowed = True

        def disable_post_stop_observation(self) -> None:
            self.observation_allowed = False

        def get_pod(self, provider_account_id: str, pod_id: str):
            if not self.observation_allowed:
                raise runtime.TransportError("UNTRUSTED_TIME_POST_STOP_GET_DEFERRED")
            return super().get_pod(provider_account_id, pod_id)

    provider = ContainmentProvider()
    values = adapter_core(provider=provider)
    engine, client, provider, signer, manual, spec, request, token = values
    reservation = arm_and_reserve(values)
    response = core_fakes.response_201(spec.pod_name)
    provider.post_response = response
    provider.created_pod = json.loads(response.body)
    engine.dispatch_create(token, reservation, exact_create_request_bytes=request)
    manual.set(BASE + timedelta(seconds=14))
    token = engine.heartbeat(token, expected_sequence=0, lease_seconds=180)

    class FailingSts:
        def get_caller_identity(self):
            raise RuntimeError("offline")

    clock = runtime.ContainmentClock(
        runtime.AwsTrustedClock(FailingSts()),
        wall_clock=lambda: BASE + timedelta(seconds=100),
    )
    ports = runtime.RuntimePorts(
        runtime.DynamoDbConditionalStore(client, "guardian-test-table"),
        signer,
        clock,
        core_fakes.FakeSecretGuard(),
        provider,
    )
    monkeypatch.setattr(runtime, "_PORTS_FACTORY", lambda capability, env: ports)
    monkeypatch.setattr(runtime, "_ACTIVATION_DOCUMENT_VERIFIER", None)
    monkeypatch.setattr(
        runtime,
        "_ACTIVATION_DOCUMENTS_FACTORY",
        lambda env: (_ for _ in ()).throw(RuntimeError("S3 unavailable")),
    )
    binding_value, binding_document = install_local_binding_environment(monkeypatch)

    class Context:
        invoked_function_arn = (
            binding_value["stop_function_arn"]
        )

    envelope = exact_request_envelope(spec, request)
    envelope["deployment_binding_sha256"] = binding_document[
        "deployment_binding_sha256"
    ]
    envelope["token"] = {
        "execution_arn": token.execution_arn,
        "fence": token.fence,
        "heartbeat_sequence": token.heartbeat_sequence,
    }
    with pytest.raises(runtime.SafeLambdaFailure):
        runtime.stop_handler({"operation": "stop", "envelope": envelope}, Context())
    assert provider.stop_calls == ["newpod1234"]
    record = engine.read_record(spec.key)
    assert record["state"] == "STOPPING"
    assert record["trusted_time_unavailable"] is True
    assert record["stop_attempt_before_deadline_observed"] is False
    assert record["containment_sla_met"] is False


def test_lost_create_response_reconciles_and_contains_during_s3_sts_outage(
    monkeypatch,
):
    provider = core_fakes.FakeProvider()
    values = adapter_core(provider=provider)
    engine, client, provider, signer, manual, spec, request, token = values
    reservation = arm_and_reserve(values)
    response = core_fakes.response_201(spec.pod_name)
    provider.created_pod = json.loads(response.body)
    provider.post_mode = "ambiguous_after_provider"
    outcome = engine.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.status == "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED"
    assert provider.provider_create_commits == 1

    class FailingSts:
        def get_caller_identity(self):
            raise RuntimeError("STS unavailable")

    reconcile_clock = runtime.ContainmentClock(
        runtime.AwsTrustedClock(FailingSts()),
        wall_clock=lambda: BASE + timedelta(seconds=15),
    )
    store = runtime.DynamoDbConditionalStore(client, "guardian-test-table")
    reconcile_ports = runtime.RuntimePorts(
        store,
        signer,
        reconcile_clock,
        core_fakes.FakeSecretGuard(),
        provider,
    )
    manual.set(BASE + timedelta(seconds=15))
    stop_ports = runtime.RuntimePorts(
        store,
        signer,
        manual,
        core_fakes.FakeSecretGuard(),
        provider,
    )
    monkeypatch.setattr(
        runtime,
        "_PORTS_FACTORY",
        lambda capability, env: (
            reconcile_ports if capability == "containment_observe" else stop_ports
        ),
    )
    monkeypatch.setattr(runtime, "_ACTIVATION_DOCUMENT_VERIFIER", None)
    monkeypatch.setattr(
        runtime,
        "_ACTIVATION_DOCUMENTS_FACTORY",
        lambda env: (_ for _ in ()).throw(RuntimeError("S3 unavailable")),
    )
    binding_value, binding_document = install_local_binding_environment(monkeypatch)

    class ObserveContext:
        invoked_function_arn = (
            binding_value["observe_function_arn"]
        )

    class StopContext:
        invoked_function_arn = (
            binding_value["stop_function_arn"]
        )

    envelope = exact_request_envelope(spec, request)
    envelope["deployment_binding_sha256"] = binding_document[
        "deployment_binding_sha256"
    ]
    envelope["token"] = {
        "execution_arn": token.execution_arn,
        "fence": token.fence,
        "heartbeat_sequence": token.heartbeat_sequence,
    }
    reconciled = runtime.observe_handler(
        {"operation": "reconcile", "envelope": envelope}, ObserveContext()
    )
    record = engine.read_record(spec.key)
    assert record["target_pod_id"] == "newpod1234"
    assert record["launch_admission_status"] == "INELIGIBLE_CREATE_EVIDENCE"
    terminal = runtime.stop_handler(
        {"operation": "stop", "envelope": reconciled}, StopContext()
    )
    assert terminal["last_result"]["payload"]["terminal_provider_proof"] is True
    assert provider.stop_calls == ["newpod1234"]


def test_recovery_retries_preclaim_failure_with_new_event_id_then_takes_over(
    monkeypatch,
):
    values = adapter_core(lease=20)
    engine, client, _provider, signer, clock, spec, request, old_token = values
    source_input = exact_request_envelope(spec, request)
    for index in range(4096):
        evidence_pk = f"EVIDENCE#SHA256#{index:064x}"
        client.items[(evidence_pk, "IMMUTABLE#v1")] = {
            "pk": {"S": evidence_pk},
            "sk": {"S": "IMMUTABLE#v1"},
            "item_type": {"S": "IMMUTABLE_SIGNED_RECEIPT"},
        }
    clock.set(BASE + timedelta(seconds=21))

    class FakeSfn:
        def __init__(self):
            self.starts: list[dict[str, Any]] = []

        def describe_execution(self, **kwargs: Any) -> dict[str, Any]:
            if kwargs["executionArn"] == core_fakes.EXECUTION_1:
                return {"input": _canonical_for_test(source_input).decode("utf-8")}
            for call in self.starts:
                expected = (
                    "arn:aws:states:us-west-2:123456789012:execution:guardian:"
                    + call["name"]
                )
                if kwargs["executionArn"] == expected:
                    return {"executionArn": expected, "status": "RUNNING"}
            raise AssertionError(kwargs["executionArn"])

        def start_execution(self, **kwargs: Any) -> dict[str, Any]:
            if any(call["name"] == kwargs["name"] for call in self.starts):
                raise FakeClientError("ExecutionAlreadyExists")
            self.starts.append(deepcopy(kwargs))
            return {
                "executionArn": (
                    "arn:aws:states:us-west-2:123456789012:execution:guardian:"
                    + kwargs["name"]
                )
            }

    sfn = FakeSfn()
    monkeypatch.setenv("ACTIVATION_MODE", "LIVE")
    monkeypatch.setenv("EXPECTED_AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_ACCOUNT_ID", "123456789012")
    monkeypatch.setenv("DEPLOYMENT_BINDING_SHA256", BINDING)
    monkeypatch.setenv("PROVIDER_ACCOUNT_ID", ACCOUNT)
    monkeypatch.setenv("RECOVERY_ENABLED", "TRUE")
    monkeypatch.setenv("LEDGER_TABLE_NAME", "guardian-test-table")
    monkeypatch.setenv(
        "STATE_MACHINE_ARN",
        "arn:aws:states:us-west-2:123456789012:stateMachine:guardian",
    )
    monkeypatch.setattr(
        runtime, "_RECOVERY_CLIENTS_FACTORY", lambda: (client, sfn, clock, signer)
    )
    tick = recovery_event(1)
    result = runtime.recovery_handler(tick, None)
    assert result["stale_successors_started"] == 1
    assert result["global_active_authorization_present"] is True
    assert client.query_calls == []
    assert client.scan_calls == []
    assert len(sfn.starts) == 1
    started = sfn.starts[0]
    assert started["name"].startswith("recovery-f2-e")
    assert json.loads(started["input"]) == source_input
    second = runtime.recovery_handler(tick, None)
    assert second["stale_successors_started"] == 0
    assert second["stale_successors_already_exist"] == 1
    assert len(sfn.starts) == 1
    clock.advance(60)
    third = runtime.recovery_handler(recovery_event(2), None)
    assert third["stale_successors_started"] == 1
    assert len(sfn.starts) == 2
    assert sfn.starts[1]["name"] != sfn.starts[0]["name"]
    successor_arn = (
        "arn:aws:states:us-west-2:123456789012:execution:guardian:successor"
    )
    takeover = engine.claim_execution(
        spec.key, execution_arn=successor_arn, lease_seconds=20
    )
    assert takeover.fence == 2
    with pytest.raises(guardian.StaleFence):
        engine.heartbeat(
            old_token,
            expected_sequence=old_token.heartbeat_sequence,
            lease_seconds=20,
        )


def test_recovery_sts_failure_and_wall_clock_ten_minutes_behind_forces_stop_path(
    monkeypatch,
):
    class ContainmentProvider(core_fakes.FakeProvider):
        def __init__(self):
            super().__init__()
            self.observation_allowed = True

        def disable_post_stop_observation(self) -> None:
            self.observation_allowed = False

        def get_pod(self, provider_account_id: str, pod_id: str):
            if not self.observation_allowed:
                raise runtime.TransportError(
                    "UNTRUSTED_TIME_POST_STOP_GET_DEFERRED"
                )
            return super().get_pod(provider_account_id, pod_id)

    provider = ContainmentProvider()
    values = adapter_core(provider=provider, lease=180)
    engine, client, provider, signer, _manual, spec, request, old_token = values
    reservation = arm_and_reserve(values)
    response = core_fakes.response_201(spec.pod_name)
    provider.post_response = response
    provider.created_pod = json.loads(response.body)
    engine.dispatch_create(
        old_token, reservation, exact_create_request_bytes=request
    )
    before = engine.read_record(spec.key)
    assert before["state"] == "TARGET_BOUND"
    assert before["owner_fence"] == 1

    class FailingTrustedClock:
        def now(self) -> datetime:
            raise runtime.AdapterError("TRUSTED_CLOCK_STS_UNAVAILABLE")

    slow_wall = BASE - timedelta(minutes=10)
    recovery_clock = runtime.ContainmentClock(
        FailingTrustedClock(), wall_clock=lambda: slow_wall
    )
    source_input = exact_request_envelope(spec, request)

    class FakeSfn:
        def __init__(self):
            self.starts: list[dict[str, Any]] = []

        def describe_execution(self, **kwargs: Any) -> dict[str, Any]:
            assert kwargs["executionArn"] == old_token.execution_arn
            return {"input": _canonical_for_test(source_input).decode("utf-8")}

        def start_execution(self, **kwargs: Any) -> dict[str, Any]:
            self.starts.append(deepcopy(kwargs))
            return {
                "executionArn": (
                    "arn:aws:states:us-west-2:123456789012:execution:guardian:"
                    + kwargs["name"]
                )
            }

    sfn = FakeSfn()
    enable_recovery_environment(monkeypatch)
    monkeypatch.setattr(
        runtime,
        "_RECOVERY_CLIENTS_FACTORY",
        lambda: (client, sfn, recovery_clock, signer),
    )
    # Seven accepted executions die before ClaimAuthorization.  Each later
    # scheduled event must still obtain a distinct name while the slow wall
    # remains fixed; the eighth execution is the eventual claimant.
    for tick_index in range(3, 11):
        recovered = runtime.recovery_handler(recovery_event(tick_index), None)
        assert recovered["stale_successors_started"] == 1
    assert len(sfn.starts) == 8
    assert len({call["name"] for call in sfn.starts}) == 8
    successor_input = json.loads(sfn.starts[-1]["input"])
    assert successor_input["trusted_time_unavailable"] is True

    successor_arn = (
        "arn:aws:states:us-west-2:123456789012:execution:guardian:"
        + sfn.starts[-1]["name"]
    )
    worker_clock = runtime.ContainmentClock(
        FailingTrustedClock(), wall_clock=lambda: slow_wall
    )
    worker_ports = runtime.RuntimePorts(
        runtime.DynamoDbConditionalStore(client, "guardian-test-table"),
        signer,
        worker_clock,
        core_fakes.FakeSecretGuard(),
        provider,
    )
    claimed = runtime.execute_operation(
        "claim",
        {"execution_arn": successor_arn, "envelope": successor_input},
        worker_ports,
    )
    assert claimed["token"]["fence"] == 2
    inspected = runtime.execute_operation(
        "inspect", {"envelope": claimed}, worker_ports
    )
    assert inspected["next_action"] == "STOP"
    assert inspected["wait_seconds"] == 0
    assert inspected["trusted_time_unavailable"] is True
    with pytest.raises(
        runtime.TransportError, match="UNTRUSTED_TIME_POST_STOP_GET_DEFERRED"
    ):
        runtime.execute_operation(
            "stop", {"envelope": inspected}, worker_ports
        )
    assert provider.stop_calls == ["newpod1234"]
    assert provider.post_entries == 1
    after = engine.read_record(spec.key)
    assert after["state"] == "STOPPING"
    assert after["trusted_time_unavailable"] is True
    assert after.get("terminal_provider_proof") is not True
    assert after.get("containment_sla_met") is not True


def test_recovery_start_failure_raises_for_async_retry_then_same_name_succeeds(
    monkeypatch,
):
    values = adapter_core(lease=20)
    _engine, client, _provider, signer, clock, spec, request, _old_token = values
    source_input = exact_request_envelope(spec, request)
    clock.set(BASE + timedelta(seconds=21))

    class FlakySfn:
        def __init__(self):
            self.starts: list[dict[str, Any]] = []

        def describe_execution(self, **kwargs: Any) -> dict[str, Any]:
            assert kwargs["executionArn"] == core_fakes.EXECUTION_1
            return {"input": _canonical_for_test(source_input).decode("utf-8")}

        def start_execution(self, **kwargs: Any) -> dict[str, Any]:
            self.starts.append(deepcopy(kwargs))
            if len(self.starts) == 1:
                raise FakeClientError("InternalServerError")
            return {
                "executionArn": (
                    "arn:aws:states:us-west-2:123456789012:execution:guardian:"
                    + kwargs["name"]
                )
            }

    sfn = FlakySfn()
    enable_recovery_environment(monkeypatch)
    monkeypatch.setattr(
        runtime,
        "_RECOVERY_CLIENTS_FACTORY",
        lambda: (client, sfn, clock, signer),
    )
    with pytest.raises(
        runtime.SafeLambdaFailure,
        match="GUARDIAN_RECOVERY_FAIL_CLOSED:ADAPTERERROR",
    ):
        runtime.recovery_handler(recovery_event(4), None)
    retried = runtime.recovery_handler(recovery_event(4), None)
    assert retried["stale_successors_started"] == 1
    assert retried["recovery_records_failed_closed"] == 0
    assert len(sfn.starts) == 2
    assert sfn.starts[0]["name"] == sfn.starts[1]["name"]


def test_terminal_recovery_name_collision_derives_a_new_bounded_attempt():
    state_machine_arn = (
        "arn:aws:states:us-west-2:123456789012:stateMachine:guardian"
    )
    base_name = "recovery-f2-e" + "a" * 20

    class TerminalCollisionSfn:
        def __init__(self):
            self.names: list[str] = []

        def start_execution(self, **kwargs: Any) -> dict[str, Any]:
            self.names.append(kwargs["name"])
            if kwargs["name"] == base_name:
                raise FakeClientError("ExecutionAlreadyExists")
            return {
                "executionArn": runtime._state_machine_execution_arn(
                    state_machine_arn, kwargs["name"]
                )
            }

        def describe_execution(self, **kwargs: Any) -> dict[str, Any]:
            expected = runtime._state_machine_execution_arn(
                state_machine_arn, base_name
            )
            assert kwargs["executionArn"] == expected
            return {
                "executionArn": expected,
                "status": "FAILED",
                "stopDate": BASE + timedelta(seconds=1),
            }

    sfn = TerminalCollisionSfn()
    result = runtime._start_recovery_execution(
        sfn,
        state_machine_arn=state_machine_arn,
        base_name=base_name,
        input_text="{}\n",
    )
    assert result == "STARTED"
    assert len(sfn.names) == 2
    assert sfn.names[1] != base_name
    assert sfn.names[1].startswith(base_name + "-r1-")
    assert len(sfn.names[1]) <= 80


def test_recovery_start_ack_loss_retry_observes_one_running_execution():
    state_machine_arn = (
        "arn:aws:states:us-west-2:123456789012:stateMachine:guardian"
    )
    base_name = "recovery-f2-e" + "b" * 20

    class AckLossSfn:
        def __init__(self):
            self.accepted: set[str] = set()
            self.calls = 0

        def start_execution(self, **kwargs: Any) -> dict[str, Any]:
            self.calls += 1
            if kwargs["name"] in self.accepted:
                raise FakeClientError("ExecutionAlreadyExists")
            self.accepted.add(kwargs["name"])
            raise FakeClientError("InternalServerError")

        def describe_execution(self, **kwargs: Any) -> dict[str, Any]:
            return {"executionArn": kwargs["executionArn"], "status": "RUNNING"}

    sfn = AckLossSfn()
    with pytest.raises(runtime.AdapterError, match="RECOVERY_START_EXECUTION_FAILED"):
        runtime._start_recovery_execution(
            sfn,
            state_machine_arn=state_machine_arn,
            base_name=base_name,
            input_text="{}\n",
        )
    result = runtime._start_recovery_execution(
        sfn,
        state_machine_arn=state_machine_arn,
        base_name=base_name,
        input_text="{}\n",
    )
    assert result == "ALREADY_RUNNING"
    assert sfn.accepted == {base_name}
    assert sfn.calls == 2


def test_recovery_finalizes_expired_ownerless_authorization_and_releases_pointer(
    monkeypatch,
):
    client = FakeDynamoClient()
    store = runtime.DynamoDbConditionalStore(client, "guardian-test-table")
    signer = core_fakes.FakeKmsSigner()
    clock = core_fakes.ManualClock()
    deny = runtime.DenyProviderTransport()
    guard = core_fakes.FakeSecretGuard()
    engine = guardian.AwsProductionGuardianCore(
        store=store,
        signer=signer,
        clock=clock,
        secret_guard=guard,
        transport=deny,
    )
    spec, request = core_fakes.make_spec()
    engine.register_authorization(spec, exact_create_request_bytes=request)
    assert (runtime.GLOBAL_ACTIVE_PK, runtime.GLOBAL_ACTIVE_SK) in client.items
    clock.set(BASE + timedelta(seconds=51))

    class NoStartSfn:
        def describe_execution(self, **kwargs: Any) -> dict[str, Any]:
            raise AssertionError("ownerless cleanup must not inspect an execution")

        def start_execution(self, **kwargs: Any) -> dict[str, Any]:
            raise AssertionError("ownerless cleanup must not start an execution")

    enable_recovery_environment(monkeypatch)
    monkeypatch.setattr(
        runtime,
        "_RECOVERY_CLIENTS_FACTORY",
        lambda: (client, NoStartSfn(), clock, signer),
    )
    result = runtime.recovery_handler(recovery_event(5), None)
    assert result["unclaimed_authorizations_finalized"] == 1
    assert result["global_active_pointer_released"] == 1
    record = engine.read_record(spec.key)
    assert record["state"] == "NO_CREATE_DISPATCHED_SAFE_LOSS"
    assert record["unclaimed_authorization_safe_loss"] is True
    assert record["create_dispatch_count"] == 0
    assert (runtime.GLOBAL_ACTIVE_PK, runtime.GLOBAL_ACTIVE_SK) not in client.items

    # A later authorization is admitted only after the signed zero-POST proof.
    clock.set(BASE)
    next_key = guardian.AuthorizationKey(
        "owner.example", ACCOUNT, "authorization-after-ownerless-cleanup"
    )
    next_spec, next_request = core_fakes.make_spec(key=next_key)
    engine.register_authorization(next_spec, exact_create_request_bytes=next_request)
    assert engine.read_record(next_key)["state"] == "AUTHORIZED"


def test_first_claim_vs_ownerless_finalizer_has_one_durable_cas_outcome():
    client = FakeDynamoClient()
    store = runtime.DynamoDbConditionalStore(client, "guardian-test-table")
    signer = core_fakes.FakeKmsSigner()
    provider = core_fakes.FakeProvider()
    guard = core_fakes.FakeSecretGuard()
    registration_clock = core_fakes.ManualClock(BASE)
    registration_core = guardian.AwsProductionGuardianCore(
        store=store,
        signer=signer,
        clock=registration_clock,
        secret_guard=guard,
        transport=provider,
    )
    spec, request = core_fakes.make_spec()
    registration_core.register_authorization(
        spec, exact_create_request_bytes=request
    )
    claim_core = guardian.AwsProductionGuardianCore(
        store=store,
        signer=signer,
        clock=core_fakes.ManualClock(BASE + timedelta(seconds=49)),
        secret_guard=guard,
        transport=provider,
    )
    finalizer_core = guardian.AwsProductionGuardianCore(
        store=store,
        signer=signer,
        clock=core_fakes.ManualClock(BASE + timedelta(seconds=51)),
        secret_guard=guard,
        transport=provider,
    )
    barrier = threading.Barrier(100)
    errors: list[BaseException] = []
    lock = threading.Lock()

    def race(index: int) -> None:
        try:
            barrier.wait(timeout=20)
            if index % 2:
                claim_core.claim_execution(
                    spec.key,
                    execution_arn=(
                        "arn:aws:states:us-west-2:123456789012:execution:"
                        f"cas-runpod-guardian:claim-finalize-race-{index:03d}"
                    ),
                    lease_seconds=180,
                    exact_create_request_bytes=request,
                    expected_authorization_spec_sha256=(
                        guardian.authorization_spec_sha256(spec)
                    ),
                )
            else:
                finalizer_core.finalize_unclaimed_authorization_safe_loss(spec.key)
        except BaseException as error:
            with lock:
                errors.append(error)

    threads = [threading.Thread(target=race, args=(index,)) for index in range(100)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)
    assert all(not thread.is_alive() for thread in threads)
    record = registration_core.read_record(spec.key)
    assert record["version"] in {2, 3}
    assert record["state"] in {"CLAIMED", "NO_CREATE_DISPATCHED_SAFE_LOSS"}
    pointer_present = (
        runtime.GLOBAL_ACTIVE_PK,
        runtime.GLOBAL_ACTIVE_SK,
    ) in client.items
    assert pointer_present is (record["state"] == "CLAIMED")
    assert provider.post_entries == 0
    assert errors


def test_unresolved_possible_create_never_releases_global_singleton():
    provider = core_fakes.FakeProvider()
    values = adapter_core(provider=provider)
    engine, client, provider, _signer, clock, spec, request, token = values
    reservation = arm_and_reserve(values)
    provider.created_pod = json.loads(core_fakes.response_201(spec.pod_name).body)
    provider.post_mode = "ambiguous_after_provider"
    outcome = engine.dispatch_create(
        token, reservation, exact_create_request_bytes=request
    )
    assert outcome.status == "CREATE_AMBIGUOUS_RECONCILIATION_REQUIRED"
    clock.set(BASE + timedelta(seconds=291))
    receipt = engine.finalize_unresolved(token)
    assert receipt["payload"]["terminal_provider_proof"] is False
    record = engine.read_record(spec.key)
    assert record["state"] == "UNRESOLVED_TERMINAL_FAILURE"
    assert (runtime.GLOBAL_ACTIVE_PK, runtime.GLOBAL_ACTIVE_SK) in client.items

    clock.set(BASE)
    second_key = guardian.AuthorizationKey(
        "owner.example", ACCOUNT, "authorization-blocked-by-unresolved"
    )
    second_spec, second_request = core_fakes.make_spec(key=second_key)
    with pytest.raises(guardian.AuthorizationAlreadyExists):
        engine.register_authorization(
            second_spec, exact_create_request_bytes=second_request
        )
    assert provider.provider_create_commits == 1


def test_recovery_repairs_pointer_after_terminal_commit_delete_outage(monkeypatch):
    provider = core_fakes.FakeProvider()
    values = adapter_core(provider=provider)
    engine, client, provider, signer, clock, spec, request, token = values
    reservation = arm_and_reserve(values)
    response = core_fakes.response_201(spec.pod_name)
    provider.post_response = response
    provider.created_pod = json.loads(response.body)
    engine.dispatch_create(token, reservation, exact_create_request_bytes=request)
    clock.set(BASE + timedelta(seconds=14))
    client.fail_next_delete = True
    with pytest.raises(runtime.AdapterError, match="GLOBAL_ACTIVE_RELEASE_FAILED"):
        engine.request_stop(token)
    record = engine.read_record(spec.key)
    assert record["state"] == "TERMINAL_PROVEN"
    assert (runtime.GLOBAL_ACTIVE_PK, runtime.GLOBAL_ACTIVE_SK) in client.items

    class NoStartSfn:
        def describe_execution(self, **kwargs: Any) -> dict[str, Any]:
            raise AssertionError("terminal pointer repair must not inspect execution")

        def start_execution(self, **kwargs: Any) -> dict[str, Any]:
            raise AssertionError("terminal pointer repair must not start execution")

    enable_recovery_environment(monkeypatch)
    monkeypatch.setattr(
        runtime,
        "_RECOVERY_CLIENTS_FACTORY",
        lambda: (client, NoStartSfn(), clock, signer),
    )
    result = runtime.recovery_handler(recovery_event(6), None)
    assert result["global_active_pointer_released"] == 1
    assert (runtime.GLOBAL_ACTIVE_PK, runtime.GLOBAL_ACTIVE_SK) not in client.items


def test_starter_is_idempotently_named_and_never_accepts_unknown_body_fields(
    monkeypatch,
):
    spec, request = core_fakes.make_spec()
    body = exact_request_envelope(spec, request)

    class FakeSfn:
        def __init__(self):
            self.calls: list[dict[str, Any]] = []

        def start_execution(self, **kwargs: Any) -> dict[str, Any]:
            self.calls.append(deepcopy(kwargs))
            return {
                "executionArn": (
                    "arn:aws:states:us-west-2:123456789012:execution:guardian:primary"
                )
            }

    sfn = FakeSfn()
    monkeypatch.setenv("ACTIVATION_MODE", "LIVE")
    monkeypatch.setenv("EXPECTED_AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("DEPLOYMENT_BINDING_SHA256", BINDING)
    monkeypatch.setenv("PROVIDER_ACCOUNT_ID", ACCOUNT)
    monkeypatch.setenv(
        "STATE_MACHINE_ARN",
        "arn:aws:states:us-west-2:123456789012:stateMachine:guardian",
    )
    monkeypatch.setattr(runtime, "_STARTER_CLIENT_FACTORY", lambda: sfn)
    response = runtime.starter_handler(
        {"body": _canonical_for_test(body).decode("utf-8")}, None
    )
    assert response["statusCode"] == 202
    response_2 = runtime.starter_handler(
        {"body": _canonical_for_test(body).decode("utf-8")}, None
    )
    assert response_2["statusCode"] == 202
    assert sfn.calls[0]["name"] == sfn.calls[1]["name"]
    hostile = {**body, "api_key": API_KEY.decode("ascii")}
    rejected = runtime.starter_handler(
        {"body": _canonical_for_test(hostile).decode("utf-8")}, None
    )
    assert rejected["statusCode"] == 503
    assert API_KEY.decode("ascii") not in rejected["body"]
    assert len(sfn.calls) == 2


def test_step_functions_retries_only_preprovider_claim_and_create_is_sole_dispatcher():
    definition = json.loads((HERE.parents[1] / "state_machine.asl.json").read_text("utf-8"))
    assert definition["StartAt"] == "ClaimAuthorization"
    states = definition["States"]
    retry_states = [name for name, state in states.items() if "Retry" in state]
    assert retry_states == ["ClaimAuthorization"]
    claim_retry = states["ClaimAuthorization"]["Retry"][0]
    assert claim_retry["MaxAttempts"] == 3
    assert "Lambda.TooManyRequestsException" in claim_retry["ErrorEquals"]
    assert states["DispatchCreate"]["Parameters"]["FunctionName"] == (
        "${CreateFunctionArn}"
    )
    assert states["DispatchStop"]["Parameters"]["FunctionName"] == (
        "${StopFunctionArn}"
    )
    create_references = [
        name
        for name, state in states.items()
        if isinstance(state, dict)
        and "${CreateFunctionArn}" in json.dumps(state, sort_keys=True)
    ]
    assert create_references == ["ReserveCreate", "DispatchCreate"]
    assert states["DispatchCreate"]["Parameters"]["Payload"]["operation"] == (
        "dispatch"
    )
    wait_choice = next(
        choice
        for choice in states["ChooseNextAction"]["Choices"]
        if choice.get("StringEquals") == "WAIT"
    )
    assert wait_choice["Next"] == "Heartbeat"
    assert states["Heartbeat"]["Next"] == "BoundedWait"
    assert states["BoundedWait"]["SecondsPath"] == "$.wait_seconds"
    assert states["BoundedWait"]["Next"] == "InspectLedger"
    assert states["FinalizeNoCreateSafeLoss"]["Next"] == "InspectLedger"
    assert states["ReconcileAmbiguousCreate"]["Next"] == "InspectLedger"
    assert states["ObserveTerminal"]["Next"] == "InspectLedger"
    assert states["DispatchStop"]["Next"] == "InspectLedger"


def test_template_is_inert_standard_low_idle_and_has_no_vpc_nat_or_endpoint():
    raw = (HERE.parents[1] / "template.yaml").read_text("utf-8")
    assert "Default: INERT" in raw
    assert "Type: STANDARD" in raw
    assert "BillingMode: PAY_PER_REQUEST" in raw
    assert "DeletionProtectionEnabled: true" in raw
    assert "PointInTimeRecoveryEnabled: true" in raw
    assert "KeySpec: ECC_NIST_P256" in raw
    assert "KeyUsage: SIGN_VERIFY" in raw
    assert "IncludeExecutionData: false" in raw
    assert "AuthorizationType: AWS_IAM" in raw
    assert raw.count("MaximumRetryAttempts: 2") == 2
    assert raw.count("MaximumEventAgeInSeconds: 60") == 2
    assert "AWS::EC2::NatGateway" not in raw
    assert "AWS::EC2::VPCEndpoint" not in raw
    assert "VpcConfig" not in raw
    canonical_table = (
        "TableName: !Sub cas-runpod-guardian-global-v1-${AWS::AccountId}"
    )
    assert raw.count(canonical_table) == 1
    parameters = raw.split("Parameters:", 1)[1].split("Rules:", 1)[0]
    assert "LedgerTableName" not in parameters
    assert "LEDGER_TABLE_ARN:" in raw
    assert "BOUND_KMS_SIGNING_KEY_ARN:" in raw
    assert "BOUND_STATE_MACHINE_ARN:" in raw
    for role in (
        "ControlRole",
        "ObserveRole",
        "CreateRole",
        "StopRole",
        "ObserveProxyRole",
        "CreateProxyRole",
        "StopProxyRole",
    ):
        assert f"  {role}:" in raw
    assert "Handler: guardian_runtime.create_handler" in raw
    assert "Handler: guardian_runtime.create_proxy_handler" in raw
    assert "IndexName: RecoveryByLease" not in raw
    runtime_source = (SRC / "guardian_runtime.py").read_text("utf-8")
    assert "GLOBAL_SINGLE_ACTIVE_AUTHORIZATION" in runtime_source
    assert "RECOVERY_INDEX_NAME" not in runtime_source
    assert ".query(" not in runtime_source
    assert ".scan(" not in runtime_source
    assert "DeadLetterConfig:" in raw
    assert "Type: AWS::Lambda::EventInvokeConfig" in raw
    assert "DestinationConfig:" in raw
    assert "Action: sqs:SendMessage" in raw
    assert "Type: AWS::CloudWatch::Alarm" in raw
    assert "MetricName: Throttles" in raw
    assert "MetricName: FailedInvocations" in raw
    assert "LiveMode: !Equals [!Ref ActivationMode, LIVE]" in raw
    assert "ReservedConcurrentExecutions: !If [LiveMode, 1, !Ref AWS::NoValue]" in raw
    assert raw.count("ReservedConcurrentExecutions: !If [LiveMode, 1, !Ref AWS::NoValue]") >= 7
    resource_block = raw.split("Resources:", 1)[1].split("Outputs:", 1)[0]
    resource_names = [
        line[2:-1]
        for line in resource_block.splitlines()
        if line.startswith("  ")
        and not line.startswith("    ")
        and line.endswith(":")
    ]
    assert len(resource_names) == 48
    control_role = raw.split("  ControlRole:", 1)[1].split("  ObserveRole:", 1)[0]
    assert "secretsmanager:GetSecretValue" not in control_role
    for role, following in (
        ("ObserveRole", "CreateRole"),
        ("CreateRole", "StopRole"),
        ("StopRole", "ObserveProxyRole"),
    ):
        section = raw.split(f"  {role}:", 1)[1].split(f"  {following}:", 1)[0]
        assert "secretsmanager:GetSecretValue" not in section
        assert "lambda:InvokeFunction" in section
    stop_function = raw.split("  StopFunction:", 1)[1].split(
        "  ObserveProxyFunction:", 1
    )[0]
    assert "STOP_PROXY_FUNCTION_ARN:" in stop_function
    assert "OBSERVE_PROXY_FUNCTION_ARN:" in stop_function
    activation_policy = raw.split(
        "  DeploymentActivationDocumentReadPolicy:", 1
    )[1].split("  ControlFunction:", 1)[0]
    for role in (
        "ControlRole",
        "StopRole",
        "RecoveryRole",
        "ObserveProxyRole",
        "StopProxyRole",
    ):
        assert f"!Ref {role}" not in activation_policy
    for role in ("ObserveRole", "CreateRole", "StarterRole", "CreateProxyRole"):
        assert f"!Ref {role}" in activation_policy


def test_containment_recovery_timing_budget_has_strict_positive_margin():
    components = (
        guardian.MAX_CONTAINMENT_OWNER_LEASE_SECONDS,
        guardian.MAX_GUARDIAN_WAKE_INTERVAL_SECONDS,
        guardian.MAX_WORKER_STARTUP_SECONDS,
        guardian.MAX_PROVIDER_STOP_EXECUTION_SECONDS,
        guardian.MIN_STOP_SAFETY_MARGIN_SECONDS,
    )
    assert components == (5, 60, 8, 8, 5)
    assert sum(components) == 86
    assert sum(components) < guardian.MIN_STOP_LEAD_SECONDS
    raw_template = (HERE.parents[1] / "template.yaml").read_text("utf-8")
    raw_runtime = (SRC / "guardian_runtime.py").read_text("utf-8")
    assert "ScheduleExpression: rate(1 minute)" in raw_template
    assert 'timeout_seconds=7 if capability == "stop_proxy" else 8' in raw_runtime
    assert runtime.LIVE_STOP_LEAD_SECONDS == 300
    assert '"required_stop_lead_seconds": LIVE_STOP_LEAD_SECONDS' in raw_runtime
    assert "TIMING_VALIDATION_EVIDENCE_SHA256" in raw_template


def test_live_authorization_adapter_requires_300_second_stop_lead():
    spec, _request = core_fakes.make_spec()
    short = asdict(spec)
    short["protected_pod_ids"] = list(short["protected_pod_ids"])
    with pytest.raises(
        runtime.AdapterError, match="AUTHORIZATION_STOP_LEAD_BELOW_LIVE_MINIMUM"
    ):
        runtime._spec_from(short)
    valid_spec = replace(
        spec,
        hard_stop_deadline_utc=guardian.iso_utc(BASE + timedelta(seconds=400)),
        terminal_proof_deadline_utc=guardian.iso_utc(BASE + timedelta(seconds=460)),
    )
    valid = asdict(valid_spec)
    valid["protected_pod_ids"] = list(valid["protected_pod_ids"])
    assert runtime._spec_from(valid).hard_stop_deadline_utc == valid_spec.hard_stop_deadline_utc


def test_runtime_source_has_no_logging_or_delete_start_update_provider_surface():
    source = (SRC / "guardian_runtime.py").read_text("utf-8")
    assert "import logging" not in source
    assert "print(" not in source
    assert "str(error)" not in source
    assert "repr(error)" not in source
    assert "delete_pod" not in source
    assert "start_pod" not in source
    assert "update_pod" not in source
    assert "/start" not in source
    assert "DELETE" not in source


def test_candidate_tree_contains_no_python_or_pytest_cache_artifacts():
    candidate = HERE.parents[1]
    assert not list(candidate.rglob("__pycache__"))
    assert not list(candidate.rglob("*.pyc"))
    assert not list(candidate.rglob(".pytest_cache"))


def deployment_binding_input(timing_sha256: str = "e" * 64) -> dict[str, Any]:
    account = "123456789012"
    region = "us-west-2"
    prefix = f"arn:aws"
    stack = "guardian"
    return {
        "aws_account_id": account,
        "aws_partition": "aws",
        "aws_region": region,
        "stack_id": f"{prefix}:cloudformation:{region}:{account}:stack/guardian/uuid",
        "stack_name": stack,
        "ledger_table_arn": (
            f"{prefix}:dynamodb:{region}:{account}:table/"
            f"{runtime.GLOBAL_LEDGER_TABLE_PREFIX}{account}"
        ),
        "kms_signing_key_arn": f"{prefix}:kms:{region}:{account}:key/key-00000001",
        "state_machine_arn": (
            f"{prefix}:states:{region}:{account}:stateMachine:{stack}-guardian"
        ),
        "control_function_arn": f"{prefix}:lambda:{region}:{account}:function:{stack}-control",
        "observe_function_arn": f"{prefix}:lambda:{region}:{account}:function:{stack}-observe",
        "create_function_arn": f"{prefix}:lambda:{region}:{account}:function:{stack}-create",
        "stop_function_arn": f"{prefix}:lambda:{region}:{account}:function:{stack}-stop",
        "starter_function_arn": f"{prefix}:lambda:{region}:{account}:function:{stack}-starter",
        "recovery_function_arn": f"{prefix}:lambda:{region}:{account}:function:{stack}-recovery",
        "observe_proxy_function_arn": f"{prefix}:lambda:{region}:{account}:function:{stack}-observe-proxy",
        "create_proxy_function_arn": f"{prefix}:lambda:{region}:{account}:function:{stack}-create-proxy",
        "stop_proxy_function_arn": f"{prefix}:lambda:{region}:{account}:function:{stack}-stop-proxy",
        "provider_secret_arn": f"{prefix}:secretsmanager:{region}:{account}:secret:runpod",
        "provider_account_id": ACCOUNT,
        "runtime_artifact_bucket": "private-versioned-bucket",
        "runtime_artifact_key": "guardian/guardian-runtime.zip",
        "runtime_artifact_version": "version-0001",
        "runtime_zip_sha256": "1" * 64,
        "core_lock_sha256": CORE_LOCK,
        "timing_validation_evidence_sha256": timing_sha256,
        "timing_evidence_bucket": "private-versioned-bucket",
        "timing_evidence_key": "guardian/timing-evidence.json",
        "timing_evidence_version": "timing-version-0001",
        "core_sha256": "2" * 64,
        "runtime_sha256": "3" * 64,
        "state_machine_sha256": "4" * 64,
        "template_sha256": "5" * 64,
    }


def deployment_binding_environment(
    value: Mapping[str, Any], timing_sha256: str
) -> dict[str, str]:
    return {
        "ACTIVATION_MODE": "LIVE",
        "EXPECTED_AWS_REGION": "us-west-2",
        "AWS_REGION": str(value["aws_region"]),
        "AWS_ACCOUNT_ID": str(value["aws_account_id"]),
        "AWS_PARTITION": str(value["aws_partition"]),
        "STACK_ID": str(value["stack_id"]),
        "STACK_NAME": str(value["stack_name"]),
        "PROVIDER_ACCOUNT_ID": str(value["provider_account_id"]),
        "PROVIDER_SECRET_ARN": str(value["provider_secret_arn"]),
        "RUNTIME_ARTIFACT_BUCKET": str(value["runtime_artifact_bucket"]),
        "RUNTIME_ARTIFACT_KEY": str(value["runtime_artifact_key"]),
        "RUNTIME_ARTIFACT_VERSION": str(value["runtime_artifact_version"]),
        "RUNTIME_ZIP_SHA256": str(value["runtime_zip_sha256"]),
        "CORE_LOCK_SHA256": str(value["core_lock_sha256"]),
        "TIMING_VALIDATION_EVIDENCE_SHA256": timing_sha256,
        "TIMING_EVIDENCE_BUCKET": str(value["timing_evidence_bucket"]),
        "TIMING_EVIDENCE_KEY": str(value["timing_evidence_key"]),
        "TIMING_EVIDENCE_VERSION": str(value["timing_evidence_version"]),
        "LEDGER_TABLE_ARN": str(value["ledger_table_arn"]),
        "LEDGER_TABLE_NAME": str(value["ledger_table_arn"]).rsplit("/", 1)[-1],
        "BOUND_KMS_SIGNING_KEY_ARN": str(value["kms_signing_key_arn"]),
        "KMS_SIGNING_KEY_ARN": str(value["kms_signing_key_arn"]),
        "BOUND_STATE_MACHINE_ARN": str(value["state_machine_arn"]),
        "STATE_MACHINE_ARN": str(value["state_machine_arn"]),
        "PROVIDER_PROXY_FUNCTION_ARN": str(value["observe_proxy_function_arn"]),
        "OBSERVE_PROXY_FUNCTION_ARN": str(value["observe_proxy_function_arn"]),
        "STOP_PROXY_FUNCTION_ARN": str(value["stop_proxy_function_arn"]),
    }


def install_local_binding_environment(monkeypatch) -> tuple[dict[str, Any], dict[str, Any]]:
    value = deployment_binding_input()
    document = binding_tool.create_binding(value)
    environment = deployment_binding_environment(value, "e" * 64)
    environment["DEPLOYMENT_BINDING_SHA256"] = document[
        "deployment_binding_sha256"
    ]
    for name, text_value in environment.items():
        monkeypatch.setenv(name, text_value)
    return value, document


def test_deployment_binding_is_canonical_account_region_and_artifact_bound():
    value = deployment_binding_input()
    account = value["aws_account_id"]
    first = binding_tool.create_binding(value)
    second = binding_tool.create_binding(deepcopy(value))
    assert first == second
    assert first["deployment_binding_sha256"] == second["deployment_binding_sha256"]
    assert first["activation_contract"]["local_launcher_provider_post_allowed"] is False
    assert first["provider_transport"]["allowed_provider_operations_by_proxy"][
        "create_proxy"
    ] == ["CREATE", "GUARD"]
    assert first["provider_transport"]["allowed_proxy_invocation_by_core_lambda"][
        "stop"
    ] == ["observe_proxy", "stop_proxy"]
    assert first["activation_contract"]["required_stop_lead_seconds"] == 300
    assert first["activation_contract"]["timing_evidence_kind"] == (
        "EMPIRICAL_NON_GUARANTEE"
    )
    assert "maximum_guardian_wake_interval_seconds" not in first["activation_contract"]
    hostile = deepcopy(value)
    hostile["create_function_arn"] = hostile["create_function_arn"].replace(
        account, "999999999999"
    )
    with pytest.raises(
        binding_tool.BindingError, match="CANONICAL_RESOURCE_IDENTITY_MISMATCH"
    ):
        binding_tool.create_binding(hostile)


def test_global_ledger_and_every_operational_target_are_materially_bound():
    value = deployment_binding_input()
    document = binding_tool.create_binding(value)
    binding = document["deployment_binding_sha256"]

    def context_for(field: str):
        return type("Context", (), {"invoked_function_arn": value[field]})()

    baseline = deployment_binding_environment(value, "e" * 64)
    runtime._verify_local_material_binding(
        baseline, binding, "control", context_for("control_function_arn")
    )

    # A second stack or modified template can create a binding for an
    # alternate table, but the reviewed runtime accepts only the one physical
    # account/region-global ledger name.
    alternate = deepcopy(value)
    alternate["ledger_table_arn"] = (
        "arn:aws:dynamodb:us-west-2:123456789012:table/hostile-stack-ledger"
    )
    with pytest.raises(
        binding_tool.BindingError, match="CANONICAL_RESOURCE_IDENTITY_MISMATCH"
    ):
        binding_tool.create_binding(alternate)
    hostile_source = runtime._local_binding_source(baseline)
    hostile_source["ledger_table_arn"] = alternate["ledger_table_arn"]
    hostile_binding = hashlib.sha256(
        runtime.DEPLOYMENT_BINDING_DOMAIN
        + binding_tool.canonical(hostile_source)
    ).hexdigest()
    with pytest.raises(
        runtime.ActivationError, match="LOCAL_MATERIAL_BINDING_DIGEST_MISMATCH"
    ):
        runtime._verify_local_material_binding(
            baseline,
            hostile_binding,
            "control",
            context_for("control_function_arn"),
        )

    cases = [
        ("LEDGER_TABLE_ARN", value["ledger_table_arn"] + "-other", "control", "control_function_arn"),
        ("LEDGER_TABLE_NAME", "other-ledger", "control", "control_function_arn"),
        ("BOUND_KMS_SIGNING_KEY_ARN", value["kms_signing_key_arn"] + "-other", "control", "control_function_arn"),
        ("KMS_SIGNING_KEY_ARN", value["kms_signing_key_arn"] + "-other", "control", "control_function_arn"),
        ("BOUND_STATE_MACHINE_ARN", value["state_machine_arn"] + "-other", "starter", "starter_function_arn"),
        ("STATE_MACHINE_ARN", value["state_machine_arn"] + "-other", "starter", "starter_function_arn"),
        ("PROVIDER_PROXY_FUNCTION_ARN", value["observe_proxy_function_arn"] + "-other", "observe", "observe_function_arn"),
        ("PROVIDER_PROXY_FUNCTION_ARN", value["create_proxy_function_arn"] + "-other", "create", "create_function_arn"),
        ("STOP_PROXY_FUNCTION_ARN", value["stop_proxy_function_arn"] + "-other", "stop", "stop_function_arn"),
        ("OBSERVE_PROXY_FUNCTION_ARN", value["observe_proxy_function_arn"] + "-other", "stop", "stop_function_arn"),
    ]
    for field, hostile_value, capability, invoked_field in cases:
        environment = deployment_binding_environment(value, "e" * 64)
        if capability == "create":
            environment["PROVIDER_PROXY_FUNCTION_ARN"] = value[
                "create_proxy_function_arn"
            ]
        environment[field] = hostile_value
        with pytest.raises(runtime.ActivationError):
            runtime._verify_local_material_binding(
                environment, binding, capability, context_for(invoked_field)
            )

    wrong_context = type(
        "Context",
        (),
        {"invoked_function_arn": value["control_function_arn"] + "-other"},
    )()
    with pytest.raises(runtime.ActivationError, match="FUNCTION_IDENTITY_MISMATCH"):
        runtime._verify_local_material_binding(
            baseline, binding, "control", wrong_context
        )


def test_runtime_verifies_canonical_binding_timing_object_and_compiled_hashes(
    monkeypatch,
):
    timing = {
        "schema_version": runtime.TIMING_EVIDENCE_SCHEMA,
        "aws_account_id": "123456789012",
        "aws_region": "us-west-2",
        "stack_id": (
            "arn:aws:cloudformation:us-west-2:123456789012:"
            "stack/guardian/uuid"
        ),
        "core_lock_sha256": CORE_LOCK,
        "runtime_zip_sha256": "1" * 64,
        "measured_at_utc": guardian.iso_utc(BASE),
        "measurement_count": 25,
        "measurement_kind": "EMPIRICAL_NON_GUARANTEE",
        "scheduled_recovery_cadence_seconds": 60,
        "recovery_retry_maximum_attempts": 2,
        "recovery_event_maximum_age_seconds": 60,
        "tested_consecutive_missed_ticks": 1,
        "observed_recovery_gap_milliseconds": 119_000,
        "observed_worker_startup_milliseconds": 7_000,
        "observed_provider_stop_execution_milliseconds": 7_500,
        "required_stop_lead_seconds": 300,
        "source_evidence_manifest_sha256": "a" * 64,
    }
    timing_raw = binding_tool.canonical(timing)
    timing_sha = hashlib.sha256(timing_raw).hexdigest()
    value = deployment_binding_input(timing_sha)
    document = binding_tool.create_binding(value)
    binding_raw = binding_tool.canonical(document)
    environment = deployment_binding_environment(value, timing_sha)
    environment["BINDING_OBJECT_SHA256"] = hashlib.sha256(binding_raw).hexdigest()

    class Context:
        invoked_function_arn = value["control_function_arn"]

    monkeypatch.setattr(
        runtime,
        "_ACTIVATION_DOCUMENTS_FACTORY",
        lambda supplied: (binding_raw, timing_raw),
    )
    runtime._verify_activation_documents(
        environment,
        document["deployment_binding_sha256"],
        "control",
        Context(),
    )
    forged_value = deepcopy(value)
    forged_value["runtime_sha256"] = "9" * 64
    forged_document = binding_tool.create_binding(forged_value)
    forged_raw = binding_tool.canonical(forged_document)
    environment["BINDING_OBJECT_SHA256"] = hashlib.sha256(forged_raw).hexdigest()
    monkeypatch.setattr(
        runtime,
        "_ACTIVATION_DOCUMENTS_FACTORY",
        lambda supplied: (forged_raw, timing_raw),
    )
    with pytest.raises(runtime.ActivationError, match="ENVIRONMENT_MISMATCH"):
        runtime._verify_activation_documents(
            environment,
            forged_document["deployment_binding_sha256"],
            "control",
            Context(),
        )


def test_starter_rejects_fabricated_matching_binding_hex_before_start(monkeypatch):
    timing = {
        "schema_version": runtime.TIMING_EVIDENCE_SCHEMA,
        "aws_account_id": "123456789012",
        "aws_region": "us-west-2",
        "stack_id": "arn:aws:cloudformation:us-west-2:123456789012:stack/guardian/uuid",
        "core_lock_sha256": CORE_LOCK,
        "runtime_zip_sha256": "1" * 64,
        "measured_at_utc": guardian.iso_utc(BASE),
        "measurement_count": 1,
        "measurement_kind": "EMPIRICAL_NON_GUARANTEE",
        "scheduled_recovery_cadence_seconds": 60,
        "recovery_retry_maximum_attempts": 2,
        "recovery_event_maximum_age_seconds": 60,
        "tested_consecutive_missed_ticks": 1,
        "observed_recovery_gap_milliseconds": 1,
        "observed_worker_startup_milliseconds": 1,
        "observed_provider_stop_execution_milliseconds": 1,
        "required_stop_lead_seconds": 300,
        "source_evidence_manifest_sha256": "a" * 64,
    }
    timing_raw = binding_tool.canonical(timing)
    timing_sha = hashlib.sha256(timing_raw).hexdigest()
    value = deployment_binding_input(timing_sha)
    value["runtime_sha256"] = "9" * 64
    forged = binding_tool.create_binding(value)
    forged_raw = binding_tool.canonical(forged)
    environment = deployment_binding_environment(value, timing_sha)
    environment.update(
        {
            "BINDING_OBJECT_SHA256": hashlib.sha256(forged_raw).hexdigest(),
            "DEPLOYMENT_BINDING_SHA256": forged["deployment_binding_sha256"],
        }
    )
    for name, value_text in environment.items():
        monkeypatch.setenv(name, value_text)
    monkeypatch.setattr(runtime, "_ACTIVATION_DOCUMENT_VERIFIER", None)
    monkeypatch.setattr(
        runtime,
        "_ACTIVATION_DOCUMENTS_FACTORY",
        lambda supplied: (forged_raw, timing_raw),
    )
    starts: list[dict[str, Any]] = []
    monkeypatch.setattr(
        runtime,
        "_STARTER_CLIENT_FACTORY",
        lambda: type(
            "Client",
            (),
            {"start_execution": lambda self, **kwargs: starts.append(kwargs)},
        )(),
    )
    spec, request = core_fakes.make_spec()
    body = exact_request_envelope(spec, request)
    body["deployment_binding_sha256"] = forged["deployment_binding_sha256"]

    class Context:
        invoked_function_arn = value["starter_function_arn"]

    response = runtime.starter_handler(
        {"body": _canonical_for_test(body).decode("utf-8")}, Context()
    )
    assert response["statusCode"] == 503
    assert starts == []


# Added 2026-08-21 after a pre-flight audit found that CreateProxyRole was granted
# dynamodb:TransactWriteItems alone while its transaction carries "Update" and
# "ConditionCheck" items. DynamoDB authorises TransactWriteItems PER ITEM, by the
# item's own action, so the call returns AccessDeniedException. The defect could not
# surface until the single paid CREATE attempt, after the non-retryable dispatch
# marker was durably committed and before the provider POST was issued.
#
# 426 tests passed over that defect because every transaction test installs a fake
# DynamoDB client with no policy engine. These two tests read the TEMPLATE, not a
# fake, which is the only place the grant actually exists.
_ITEM_ACTION_FOR_VERB = {
    "Update": "dynamodb:UpdateItem",
    "ConditionCheck": "dynamodb:ConditionCheckItem",
    "Put": "dynamodb:PutItem",
    "Delete": "dynamodb:DeleteItem",
}


def test_create_proxy_role_grants_every_item_level_action_its_transaction_uses():
    runtime_source = (HERE.parents[1] / "src" / "guardian_runtime.py").read_text("utf-8")
    consume = runtime_source.split("def _consume_create_capability", 1)[1].split(
        "\ndef ", 1
    )[0]
    verbs = {
        verb for verb in _ITEM_ACTION_FOR_VERB if f'"{verb}": {{' in consume
    }
    # The transaction is expected to carry both an Update and a ConditionCheck item.
    # If the runtime ever stops using one, this assertion fails loudly rather than
    # letting the test silently check nothing.
    assert verbs == {"Update", "ConditionCheck"}, verbs

    raw = (HERE.parents[1] / "template.yaml").read_text("utf-8")
    section = raw.split("  CreateProxyRole:", 1)[1].split("  StopProxyRole:", 1)[0]
    assert "dynamodb:TransactWriteItems" in section
    for verb in sorted(verbs):
        required = _ITEM_ACTION_FOR_VERB[verb]
        assert required in section, (
            f'CreateProxyRole issues a "{verb}" item inside TransactWriteItems but '
            f"the template does not grant {required}. DynamoDB authorises "
            "TransactWriteItems per item, so this fails with AccessDeniedException "
            "at the single paid CREATE attempt."
        )


def test_live_rules_forbid_the_two_binding_hashes_from_being_equal():
    # DeploymentBindingSha256 hashes the document source EXCLUDING its two hash
    # fields (domain-prefixed); DeploymentBindingObjectSha256 hashes the raw object
    # bytes INCLUDING them. They can never be equal for any binding document, so
    # equality proves one slot holds the wrong value. DeploymentBindingSha256 is
    # NoEcho -- masked in the console, in describe-change-set, and redacted in
    # CloudTrail -- so this rule is the ONLY gate that can catch the mistake.
    raw = (HERE.parents[1] / "template.yaml").read_text("utf-8")
    rules = raw.split("Rules:", 1)[1].split("\nConditions:", 1)[0]
    assert "!Ref DeploymentBindingSha256" in rules
    assert "!Ref DeploymentBindingObjectSha256" in rules
    normalised = " ".join(rules.split())
    assert (
        "- !Ref DeploymentBindingSha256 - !Ref DeploymentBindingObjectSha256"
        in normalised
    ), "LIVE rules must assert the two binding hashes are not equal"
