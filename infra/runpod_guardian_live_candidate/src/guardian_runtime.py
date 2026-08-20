"""Fail-closed AWS adapters and Lambda handlers for the RunPod guardian.

The provider CREATE boundary exists only in :func:`create_handler`.  The
remaining handlers use distinct method allowlists.  The module never logs an
event, a request body, a provider response, or a credential.

Deployment is inert unless all of the following independently match:

* ``ACTIVATION_MODE=LIVE``;
* ``EXPECTED_AWS_REGION=us-west-2`` and the Lambda runtime region matches;
* a non-zero ``DEPLOYMENT_BINDING_SHA256`` matches the execution input; and
* the existing Secrets Manager value binds the same deployment and provider
  account.

The deterministic state machine itself lives in ``state_machine.asl.json``.
This module is intentionally importable without boto3 so its safety boundary
can be tested with fakes before packaging.
"""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
import hmac
import http.client
import json
import os
import re
import ssl
import threading
import time
from typing import Any, Callable, Mapping, MutableMapping, Sequence
from urllib.parse import unquote_to_bytes
import uuid

import aws_production_guardian_core as guardian

try:
    from guardian_build_identity import (  # type: ignore
        CORE_LOCK_DOCUMENT_SHA256 as COMPILED_CORE_LOCK_SHA256,
        LOCKED_HASHES as COMPILED_LOCKED_HASHES,
    )
except ImportError:
    COMPILED_CORE_LOCK_SHA256 = None
    COMPILED_LOCKED_HASHES = {}


RUNTIME_SCHEMA = "cas_aws_runpod_guardian_runtime.v1"
EXECUTION_SCHEMA = "cas_aws_runpod_guardian_execution.v1"
SECRET_SCHEMA = "cas_aws_runpod_guardian_secret.v1"
PROXY_SCHEMA = "cas_aws_runpod_guardian_provider_proxy.v1"
DEPLOYMENT_BINDING_SCHEMA = "cas_aws_runpod_guardian_deployment_binding.v1"
TIMING_EVIDENCE_SCHEMA = "cas_aws_runpod_guardian_timing_evidence.v1"
DEPLOYMENT_BINDING_DOMAIN = b"CAS-AWS-RUNPOD-GUARDIAN-DEPLOYMENT-V1\x00"
PROVIDER_HOST = "rest.runpod.io"
PROVIDER_PORT = 443
PROVIDER_ROOT = "/v1/pods"
EXPECTED_REGION = "us-west-2"
MAX_HTTP_BODY_BYTES = 2_000_000
MAX_EVENT_BYTES = 1_000_000
MAX_PROXY_PAYLOAD_BYTES = 3_000_000
MAX_ACTIVATION_DOCUMENT_BYTES = 65_536
LIVE_STOP_LEAD_SECONDS = 300
GLOBAL_LEDGER_TABLE_PREFIX = "cas-runpod-guardian-global-v1-"
GLOBAL_ACTIVE_PK = "CONTROL#GLOBAL_ACTIVE#v1"
GLOBAL_ACTIVE_SK = "SINGLETON#v1"
CREATE_CAPABILITY_PREFIX = "CONTROL#CREATE_CAPABILITY#SHA256#"
CREATE_CAPABILITY_SK = "ONE_USE#v1"
TERMINAL_STATES = frozenset(
    {
        "TERMINAL_PROVEN",
        "CREATE_REJECTED_400",
        "UNRESOLVED_TERMINAL_FAILURE",
        "NO_CREATE_DISPATCHED_SAFE_LOSS",
    }
)
POINTER_RELEASE_STATES = frozenset(
    {
        "TERMINAL_PROVEN",
        "NO_CREATE_DISPATCHED_SAFE_LOSS",
    }
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TABLE_NAME = re.compile(r"^[A-Za-z0-9_.-]{3,255}$")
_POD_ID = re.compile(r"^[a-z0-9]{6,32}$")
_EXECUTION_NAME = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_RECOVERY_EVENT_ID = re.compile(
    r"^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$"
)
_SECRET_ARN = re.compile(
    r"^arn:aws[a-zA-Z-]*:secretsmanager:[a-z0-9-]+:\d{12}:secret:[A-Za-z0-9/_+=.@-]+$"
)

_BINDING_SOURCE_FIELDS = frozenset(
    {
        "schema_version",
        "aws_account_id",
        "aws_partition",
        "aws_region",
        "stack_id",
        "stack_name",
        "ledger_table_arn",
        "kms_signing_key_arn",
        "state_machine_arn",
        "control_function_arn",
        "observe_function_arn",
        "create_function_arn",
        "stop_function_arn",
        "starter_function_arn",
        "recovery_function_arn",
        "observe_proxy_function_arn",
        "create_proxy_function_arn",
        "stop_proxy_function_arn",
        "provider_secret_arn",
        "provider_account_id",
        "runtime_artifact_bucket",
        "runtime_artifact_key",
        "runtime_artifact_version",
        "runtime_zip_sha256",
        "core_lock_sha256",
        "timing_validation_evidence_sha256",
        "timing_evidence_bucket",
        "timing_evidence_key",
        "timing_evidence_version",
        "core_sha256",
        "runtime_sha256",
        "state_machine_sha256",
        "template_sha256",
        "provider_transport",
        "activation_contract",
    }
)
_TIMING_EVIDENCE_FIELDS = frozenset(
    {
        "schema_version",
        "aws_account_id",
        "aws_region",
        "stack_id",
        "core_lock_sha256",
        "runtime_zip_sha256",
        "measured_at_utc",
        "measurement_count",
        "measurement_kind",
        "scheduled_recovery_cadence_seconds",
        "recovery_retry_maximum_attempts",
        "recovery_event_maximum_age_seconds",
        "tested_consecutive_missed_ticks",
        "observed_recovery_gap_milliseconds",
        "observed_worker_startup_milliseconds",
        "observed_provider_stop_execution_milliseconds",
        "required_stop_lead_seconds",
        "source_evidence_manifest_sha256",
    }
)


class AdapterError(guardian.GuardianError):
    """A production adapter failed closed."""


class ActivationError(AdapterError):
    """Runtime deployment bindings are absent or inconsistent."""


class TransportError(AdapterError):
    """A provider exchange is ambiguous or outside the frozen boundary."""


class SecretExposure(AdapterError):
    """Credential material appeared in bytes that could become evidence."""


class SafeLambdaFailure(RuntimeError):
    """Generic Lambda error whose text never includes caller/provider data."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: Any) -> bytes:
    return guardian.canonical_json_bytes(value)


def _strict_b64(value: Any, *, label: str, max_bytes: int = MAX_EVENT_BYTES) -> bytes:
    if not isinstance(value, str) or not value:
        raise AdapterError(f"{label}_ABSENT")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise AdapterError(f"{label}_INVALID_BASE64") from error
    if not raw or len(raw) > max_bytes:
        raise AdapterError(f"{label}_INVALID_SIZE")
    if base64.b64encode(raw).decode("ascii") != value:
        raise AdapterError(f"{label}_NONCANONICAL_BASE64")
    return raw


def _strict_b64_allow_empty(
    value: Any, *, label: str, max_bytes: int = MAX_EVENT_BYTES
) -> bytes:
    if not isinstance(value, str):
        raise AdapterError(f"{label}_ABSENT")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as error:
        raise AdapterError(f"{label}_INVALID_BASE64") from error
    if len(raw) > max_bytes or base64.b64encode(raw).decode("ascii") != value:
        raise AdapterError(f"{label}_NONCANONICAL_BASE64")
    return raw


def _conditional_failed(error: BaseException) -> bool:
    response = getattr(error, "response", None)
    if not isinstance(response, Mapping):
        return False
    detail = response.get("Error")
    return isinstance(detail, Mapping) and detail.get("Code") in {
        "ConditionalCheckFailedException",
        "TransactionCanceledException",
    }


def _execution_exists(error: BaseException) -> bool:
    response = getattr(error, "response", None)
    if not isinstance(response, Mapping):
        return False
    detail = response.get("Error")
    return isinstance(detail, Mapping) and detail.get("Code") == (
        "ExecutionAlreadyExists"
    )


def _recovery_event_nonce(
    event: Any, environment: Mapping[str, str]
) -> str:
    """Return an async-retry-stable, scheduled-tick-unique name token."""

    if not isinstance(event, Mapping):
        raise AdapterError("RECOVERY_EVENT_NOT_OBJECT")
    event_id = event.get("id")
    if not isinstance(event_id, str) or not _RECOVERY_EVENT_ID.fullmatch(event_id):
        raise AdapterError("RECOVERY_EVENT_ID_INVALID")
    if (
        event.get("source") != "aws.events"
        or event.get("detail-type") != "Scheduled Event"
        or event.get("account") != environment.get("AWS_ACCOUNT_ID")
        or event.get("region") != environment.get("AWS_REGION")
    ):
        raise AdapterError("RECOVERY_EVENT_SCOPE_INVALID")
    return _sha256(
        _canonical(
            {
                "event_id": event_id,
                "account": event.get("account"),
                "region": event.get("region"),
            }
        )
    )[:20]


def _state_machine_execution_arn(
    state_machine_arn: str, execution_name: str
) -> str:
    if (
        not isinstance(state_machine_arn, str)
        or state_machine_arn.count(":stateMachine:") != 1
        or not _EXECUTION_NAME.fullmatch(execution_name)
    ):
        raise AdapterError("RECOVERY_STATE_MACHINE_IDENTITY_INVALID")
    return (
        state_machine_arn.replace(":stateMachine:", ":execution:", 1)
        + ":"
        + execution_name
    )


def _sfn_stop_date_text(value: Any) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise AdapterError("RECOVERY_COLLISION_STOP_DATE_INVALID")
    return guardian.iso_utc(value.astimezone(timezone.utc))


def _start_recovery_execution(
    sfn: Any,
    *,
    state_machine_arn: str,
    base_name: str,
    input_text: str,
) -> str:
    """Start once per scheduled event and safely resolve name collisions.

    Lambda async retries retain the EventBridge event ID, so an ambiguous
    StartExecution retry uses the same base name.  Only a RUNNING collision is
    accepted as live.  A terminal pre-claim collision receives a deterministic
    derived name; the next scheduled event has an independent base name.
    """

    name = base_name
    terminal_statuses = {
        "SUCCEEDED",
        "FAILED",
        "TIMED_OUT",
        "ABORTED",
        "PENDING_REDRIVE",
    }
    for collision_ordinal in range(1, 9):
        expected_arn = _state_machine_execution_arn(state_machine_arn, name)
        try:
            response = sfn.start_execution(
                stateMachineArn=state_machine_arn,
                name=name,
                input=input_text,
            )
        except Exception as error:
            if not _execution_exists(error):
                raise AdapterError("RECOVERY_START_EXECUTION_FAILED") from None
            try:
                description = sfn.describe_execution(executionArn=expected_arn)
            except Exception:
                raise AdapterError(
                    "RECOVERY_COLLISION_DESCRIBE_FAILED"
                ) from None
            if not isinstance(description, Mapping):
                raise AdapterError("RECOVERY_COLLISION_DESCRIPTION_INVALID")
            described_arn = description.get("executionArn", expected_arn)
            status = description.get("status")
            if described_arn != expected_arn or not isinstance(status, str):
                raise AdapterError("RECOVERY_COLLISION_DESCRIPTION_INVALID")
            if status == "RUNNING":
                return "ALREADY_RUNNING"
            if status not in terminal_statuses:
                raise AdapterError("RECOVERY_COLLISION_STATUS_INVALID")
            collision_digest = _sha256(
                _canonical(
                    {
                        "execution_arn": expected_arn,
                        "status": status,
                        "stop_date_utc": _sfn_stop_date_text(
                            description.get("stopDate")
                        ),
                        "collision_ordinal": collision_ordinal,
                    }
                )
            )[:12]
            name = f"{base_name}-r{collision_ordinal}-{collision_digest}"
            if not _EXECUTION_NAME.fullmatch(name):
                raise AdapterError("RECOVERY_EXECUTION_NAME_INVALID")
            continue
        if (
            not isinstance(response, Mapping)
            or response.get("executionArn") != expected_arn
        ):
            raise AdapterError("RECOVERY_START_RESPONSE_INVALID")
        return "STARTED"
    raise AdapterError("RECOVERY_COLLISION_BUDGET_EXHAUSTED")


class DynamoDbConditionalStore:
    """Lossless logical-record adapter over a version-conditioned DDB item.

    The core's lowercase ``pk``/``sk`` and complete record are retained as
    canonical JSON in ``record_blob``.  Physical scalar projections are
    duplicated only for conditional CAS, recovery discovery, and operations
    visibility.  They are checked against the canonical record on every read.
    """

    def __init__(self, client: Any, table_name: str) -> None:
        if not isinstance(table_name, str) or not _TABLE_NAME.fullmatch(table_name):
            raise AdapterError("DDB_TABLE_NAME_INVALID")
        self._client = client
        self.table_name = table_name

    @staticmethod
    def _evidence_key(evidence_id: str) -> tuple[str, str]:
        if not isinstance(evidence_id, str) or not _SHA256.fullmatch(evidence_id):
            raise AdapterError("DDB_EVIDENCE_ID_INVALID")
        return f"EVIDENCE#SHA256#{evidence_id}", "IMMUTABLE#v1"

    @classmethod
    def _physical_evidence(
        cls, evidence_id: str, evidence: Mapping[str, Any]
    ) -> dict[str, dict[str, Any]]:
        evidence_pk, evidence_sk = cls._evidence_key(evidence_id)
        if not isinstance(evidence, Mapping):
            raise AdapterError("DDB_EVIDENCE_NOT_OBJECT")
        value = dict(evidence)
        if value.get("receipt_sha256") != evidence_id:
            raise AdapterError("DDB_EVIDENCE_CONTENT_ID_MISMATCH")
        # Validate self-hash, canonical payload, exact 32-byte digest and KMS
        # metadata before any AWS write.
        guardian.receipt_signing_message(value)
        raw = _canonical(value)
        if len(raw) > guardian.MAX_LEDGER_ITEM_BYTES:
            raise AdapterError("DDB_EVIDENCE_TOO_LARGE")
        return {
            "pk": {"S": evidence_pk},
            "sk": {"S": evidence_sk},
            "item_type": {"S": "IMMUTABLE_SIGNED_RECEIPT"},
            "evidence_id": {"S": evidence_id},
            "record_blob": {"B": raw},
        }

    @classmethod
    def _decode_evidence(
        cls, evidence_id: str, item: Mapping[str, Any]
    ) -> dict[str, Any]:
        evidence_pk, evidence_sk = cls._evidence_key(evidence_id)
        try:
            pk = item["pk"]["S"]
            sk = item["sk"]["S"]
            item_type = item["item_type"]["S"]
            retained_id = item["evidence_id"]["S"]
            raw_value = item["record_blob"]["B"]
        except (KeyError, TypeError) as error:
            raise AdapterError("DDB_EVIDENCE_ITEM_MALFORMED") from error
        raw = bytes(raw_value) if isinstance(raw_value, (bytes, bytearray)) else None
        if (
            pk != evidence_pk
            or sk != evidence_sk
            or item_type != "IMMUTABLE_SIGNED_RECEIPT"
            or retained_id != evidence_id
            or raw is None
        ):
            raise AdapterError("DDB_EVIDENCE_IDENTITY_MISMATCH")
        parsed = guardian.strict_json(
            raw,
            "DynamoDB immutable receipt evidence",
            max_bytes=guardian.MAX_LEDGER_ITEM_BYTES,
        )
        if not isinstance(parsed, dict) or raw != _canonical(parsed):
            raise AdapterError("DDB_EVIDENCE_NONCANONICAL")
        if parsed.get("receipt_sha256") != evidence_id:
            raise AdapterError("DDB_EVIDENCE_CONTENT_ID_MISMATCH")
        guardian.receipt_signing_message(parsed)
        return parsed

    @staticmethod
    def _transaction_token(value: Mapping[str, Any]) -> str:
        # DynamoDB idempotency tokens allow at most 36 ASCII characters.
        return _sha256(_canonical(dict(value)))[:36]

    def _head_changed_after_transaction_error(
        self, pk: str, sk: str, expected_version: int | None
    ) -> bool:
        current = self.get_consistent(pk, sk)
        if expected_version is None:
            return current is not None
        return current is None or current.get("version") != expected_version

    @staticmethod
    def _global_active_item(record: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        pk = record.get("pk")
        sk = record.get("sk")
        key_sha = record.get("authorization_key_sha256")
        spec_sha = record.get("authorization_spec_sha256")
        if (
            not isinstance(pk, str)
            or not isinstance(sk, str)
            or not isinstance(key_sha, str)
            or not _SHA256.fullmatch(key_sha)
            or not isinstance(spec_sha, str)
            or not _SHA256.fullmatch(spec_sha)
        ):
            raise AdapterError("GLOBAL_ACTIVE_RECORD_IDENTITY_INVALID")
        return {
            "pk": {"S": GLOBAL_ACTIVE_PK},
            "sk": {"S": GLOBAL_ACTIVE_SK},
            "item_type": {"S": "GLOBAL_SINGLE_ACTIVE_AUTHORIZATION"},
            "active_pk": {"S": pk},
            "active_sk": {"S": sk},
            "authorization_key_sha256": {"S": key_sha},
            "authorization_spec_sha256": {"S": spec_sha},
        }

    def _pointer_release_is_proven(self, record: Mapping[str, Any]) -> bool:
        """Require strong, signed proof before releasing the global singleton.

        An unresolved post-dispatch failure is deliberately not releasable: it
        may still represent a live, unbound Pod.  Exact-ID terminal proof or a
        signed zero-POST safe-loss proof are the only automatic release paths.
        """

        state = record.get("state")
        receipts = record.get("receipts")
        if state not in POINTER_RELEASE_STATES or not isinstance(receipts, Mapping):
            return False
        if state == "TERMINAL_PROVEN":
            reference = receipts.get("terminal")
            expected_type = "TERMINAL_PROVEN"
        else:
            reference = receipts.get("unclaimed_authorization_safe_loss")
            expected_type = "UNCLAIMED_AUTHORIZATION_SAFE_LOSS"
            if not isinstance(reference, Mapping):
                reference = receipts.get("no_create_safe_loss")
                expected_type = "NO_CREATE_DISPATCHED_SAFE_LOSS"
        if not isinstance(reference, Mapping):
            return False
        evidence_id = reference.get("receipt_sha256")
        if not isinstance(evidence_id, str) or not _SHA256.fullmatch(evidence_id):
            return False
        evidence = self.get_evidence(evidence_id)
        if evidence is None or evidence.get("receipt_type") != expected_type:
            return False
        payload = evidence.get("payload")
        if not isinstance(payload, Mapping):
            return False
        if state == "TERMINAL_PROVEN":
            return bool(
                payload.get("terminal_provider_proof") is True
                and payload.get("pod_id") == record.get("target_pod_id")
                and payload.get("observed_terminal_status")
                == record.get("terminal_status")
            )
        return bool(
            record.get("create_dispatch_count") == 0
            and record.get("create_dispatch_started_at_utc") is None
            and record.get("target_pod_id") is None
            and payload.get("provider_create_attempts") == 0
            and payload.get("create_dispatch_marker_present") is False
            and payload.get("target_bound") is False
            and payload.get("safe_loss_proven") is True
        )

    def release_global_active_if_terminal(self, pk: str, sk: str) -> bool:
        """Strong-read a proven terminal head, then conditionally release it."""

        record = self.get_consistent(pk, sk)
        if record is None or not self._pointer_release_is_proven(record):
            return False
        pointer = self._global_active_item(record)
        try:
            self._client.delete_item(
                TableName=self.table_name,
                Key={
                    "pk": {"S": GLOBAL_ACTIVE_PK},
                    "sk": {"S": GLOBAL_ACTIVE_SK},
                },
                ConditionExpression=(
                    "#active_pk = :pk AND #active_sk = :sk "
                    "AND #key_sha = :key_sha AND #spec_sha = :spec_sha"
                ),
                ExpressionAttributeNames={
                    "#active_pk": "active_pk",
                    "#active_sk": "active_sk",
                    "#key_sha": "authorization_key_sha256",
                    "#spec_sha": "authorization_spec_sha256",
                },
                ExpressionAttributeValues={
                    ":pk": pointer["active_pk"],
                    ":sk": pointer["active_sk"],
                    ":key_sha": pointer["authorization_key_sha256"],
                    ":spec_sha": pointer["authorization_spec_sha256"],
                },
            )
        except Exception as error:
            if not _conditional_failed(error):
                raise AdapterError("GLOBAL_ACTIVE_RELEASE_FAILED") from None
            response = self._client.get_item(
                TableName=self.table_name,
                Key={
                    "pk": {"S": GLOBAL_ACTIVE_PK},
                    "sk": {"S": GLOBAL_ACTIVE_SK},
                },
                ConsistentRead=True,
            )
            if isinstance(response, Mapping) and response.get("Item") is None:
                return True
            return False
        return True

    @staticmethod
    def _create_capability_item(
        record: Mapping[str, Any]
    ) -> dict[str, dict[str, Any]] | None:
        if (
            record.get("state") != "CREATE_DISPATCHED_UNKNOWN"
            or record.get("create_dispatch_count") != 1
        ):
            return None
        reservation_id = record.get("create_reservation_id")
        request_sha = record.get("create_reserved_request_sha256")
        fence = record.get("create_dispatch_owner_fence")
        started_at = record.get("create_dispatch_started_at_utc")
        owner_execution = record.get("owner_execution_arn")
        owner_lease = record.get("owner_lease_expires_at_utc")
        spec = record.get("authorization_spec")
        pk = record.get("pk")
        sk = record.get("sk")
        if (
            not isinstance(reservation_id, str)
            or not _SHA256.fullmatch(reservation_id)
            or not isinstance(request_sha, str)
            or not _SHA256.fullmatch(request_sha)
            or type(fence) is not int
            or fence < 1
            or not isinstance(started_at, str)
            or not isinstance(owner_execution, str)
            or not isinstance(owner_lease, str)
            or not isinstance(spec, Mapping)
            or not isinstance(spec.get("creation_window_end_utc"), str)
            or not isinstance(pk, str)
            or not isinstance(sk, str)
        ):
            raise AdapterError("CREATE_CAPABILITY_SOURCE_INVALID")
        return {
            "pk": {"S": CREATE_CAPABILITY_PREFIX + reservation_id},
            "sk": {"S": CREATE_CAPABILITY_SK},
            "item_type": {"S": "ONE_USE_CREATE_CAPABILITY"},
            "head_pk": {"S": pk},
            "head_sk": {"S": sk},
            "reservation_id": {"S": reservation_id},
            "request_sha256": {"S": request_sha},
            "owner_fence": {"N": str(fence)},
            "owner_execution_arn": {"S": owner_execution},
            "owner_lease_expires_at_utc": {"S": owner_lease},
            "not_after_utc": {"S": str(spec["creation_window_end_utc"])},
            "dispatch_started_at_utc": {"S": started_at},
            "consumed": {"BOOL": False},
        }

    @staticmethod
    def _physical(record: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        value = dict(record)
        pk = value.get("pk")
        sk = value.get("sk")
        version = value.get("version")
        state = value.get("state")
        if not isinstance(pk, str) or not isinstance(sk, str):
            raise AdapterError("DDB_LOGICAL_KEY_INVALID")
        if type(version) is not int or version < 1:
            raise AdapterError("DDB_LOGICAL_VERSION_INVALID")
        if not isinstance(state, str):
            raise AdapterError("DDB_LOGICAL_STATE_INVALID")
        raw = _canonical(value)
        if len(raw) > guardian.MAX_LEDGER_ITEM_BYTES:
            raise AdapterError("DDB_LOGICAL_RECORD_TOO_LARGE")
        item: dict[str, dict[str, Any]] = {
            "pk": {"S": pk},
            "sk": {"S": sk},
            "item_type": {"S": "GUARDIAN_HEAD"},
            "version": {"N": str(version)},
            "state": {"S": state},
            "record_blob": {"B": raw},
        }
        for logical, physical in (
            ("owner_execution_arn", "owner_execution_arn"),
            ("owner_lease_expires_at_utc", "owner_lease_expires_at_utc"),
            ("authorization_key_sha256", "authorization_key_sha256"),
            ("create_reservation_id", "create_reservation_id"),
            ("create_reserved_request_sha256", "create_reserved_request_sha256"),
            ("create_dispatch_started_at_utc", "create_dispatch_started_at_utc"),
        ):
            scalar = value.get(logical)
            if scalar is not None:
                if not isinstance(scalar, str):
                    raise AdapterError("DDB_LOGICAL_PROJECTION_INVALID")
                item[physical] = {"S": scalar}
        fence = value.get("owner_fence")
        if fence is not None:
            if type(fence) is not int or fence < 1:
                raise AdapterError("DDB_LOGICAL_FENCE_INVALID")
            item["owner_fence"] = {"N": str(fence)}
        for logical in ("create_dispatch_count", "create_dispatch_owner_fence"):
            number = value.get(logical)
            if number is not None:
                if type(number) is not int or number < 0:
                    raise AdapterError("DDB_LOGICAL_PROJECTION_INVALID")
                item[logical] = {"N": str(number)}
        return item

    @staticmethod
    def decode_physical(item: Mapping[str, Any]) -> dict[str, Any]:
        try:
            pk = item["pk"]["S"]
            sk = item["sk"]["S"]
            version_text = item["version"]["N"]
            state = item["state"]["S"]
            raw_value = item["record_blob"]["B"]
            item_type = item["item_type"]["S"]
        except (KeyError, TypeError) as error:
            raise AdapterError("DDB_PHYSICAL_ITEM_MALFORMED") from error
        if isinstance(raw_value, bytearray):
            raw = bytes(raw_value)
        elif isinstance(raw_value, bytes):
            raw = raw_value
        else:
            raise AdapterError("DDB_RECORD_BLOB_NOT_BYTES")
        parsed = guardian.strict_json(
            raw, "DynamoDB canonical guardian record", max_bytes=guardian.MAX_LEDGER_ITEM_BYTES
        )
        if not isinstance(parsed, dict) or raw != _canonical(parsed):
            raise AdapterError("DDB_RECORD_BLOB_NONCANONICAL")
        try:
            version = int(version_text)
        except (TypeError, ValueError) as error:
            raise AdapterError("DDB_PHYSICAL_VERSION_INVALID") from error
        if (
            item_type != "GUARDIAN_HEAD"
            or parsed.get("pk") != pk
            or parsed.get("sk") != sk
            or parsed.get("version") != version
            or parsed.get("state") != state
        ):
            raise AdapterError("DDB_PHYSICAL_LOGICAL_MISMATCH")
        projections = (
            ("owner_execution_arn", "S"),
            ("owner_lease_expires_at_utc", "S"),
            ("authorization_key_sha256", "S"),
            ("create_reservation_id", "S"),
            ("create_reserved_request_sha256", "S"),
            ("create_dispatch_started_at_utc", "S"),
            ("owner_fence", "N"),
            ("create_dispatch_count", "N"),
            ("create_dispatch_owner_fence", "N"),
        )
        for name, kind in projections:
            if name in item:
                physical = item[name].get(kind)
                logical = parsed.get(name)
                if kind == "N":
                    try:
                        physical = int(physical)
                    except (TypeError, ValueError) as error:
                        raise AdapterError("DDB_PROJECTION_INVALID") from error
                if physical != logical:
                    raise AdapterError("DDB_PROJECTION_MISMATCH")
        return parsed

    def get_consistent(self, pk: str, sk: str) -> dict[str, Any] | None:
        try:
            response = self._client.get_item(
                TableName=self.table_name,
                Key={"pk": {"S": pk}, "sk": {"S": sk}},
                ConsistentRead=True,
            )
        except Exception as error:
            raise AdapterError("DDB_CONSISTENT_READ_FAILED") from None
        item = response.get("Item") if isinstance(response, Mapping) else None
        if item is None:
            return None
        if not isinstance(item, Mapping):
            raise AdapterError("DDB_READ_ITEM_MALFORMED")
        record = self.decode_physical(item)
        if record.get("pk") != pk or record.get("sk") != sk:
            raise AdapterError("DDB_READ_KEY_MISMATCH")
        return record

    def put_if_absent(
        self, pk: str, sk: str, item: Mapping[str, Any]
    ) -> bool:
        physical = self._physical(item)
        if physical["pk"]["S"] != pk or physical["sk"]["S"] != sk:
            raise AdapterError("DDB_PUT_KEY_MISMATCH")
        try:
            self._client.put_item(
                TableName=self.table_name,
                Item=physical,
                ConditionExpression="attribute_not_exists(#pk) AND attribute_not_exists(#sk)",
                ExpressionAttributeNames={"#pk": "pk", "#sk": "sk"},
            )
        except Exception as error:
            if _conditional_failed(error):
                return False
            raise AdapterError("DDB_CONDITIONAL_PUT_FAILED") from None
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
        head = self._physical(item)
        immutable = self._physical_evidence(evidence_id, evidence)
        global_active = self._global_active_item(item)
        if head["pk"]["S"] != pk or head["sk"]["S"] != sk:
            raise AdapterError("DDB_TRANSACTION_HEAD_KEY_MISMATCH")
        token = self._transaction_token(
            {
                "operation": "PUT_HEAD_AND_EVIDENCE_IF_ABSENT",
                "pk": pk,
                "sk": sk,
                "version": item.get("version"),
                "evidence_id": evidence_id,
            }
        )
        try:
            self._client.transact_write_items(
                ClientRequestToken=token,
                TransactItems=[
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": head,
                            "ConditionExpression": (
                                "attribute_not_exists(#pk) AND attribute_not_exists(#sk)"
                            ),
                            "ExpressionAttributeNames": {"#pk": "pk", "#sk": "sk"},
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": immutable,
                            "ConditionExpression": (
                                "attribute_not_exists(#pk) AND attribute_not_exists(#sk)"
                            ),
                            "ExpressionAttributeNames": {"#pk": "pk", "#sk": "sk"},
                        }
                    },
                    {
                        "Put": {
                            "TableName": self.table_name,
                            "Item": global_active,
                            "ConditionExpression": (
                                "attribute_not_exists(#pk) AND attribute_not_exists(#sk)"
                            ),
                            "ExpressionAttributeNames": {"#pk": "pk", "#sk": "sk"},
                        }
                    },
                ],
            )
        except Exception as error:
            if _conditional_failed(error) or self._head_changed_after_transaction_error(
                pk, sk, None
            ):
                return False
            raise AdapterError("DDB_ATOMIC_INITIAL_WRITE_FAILED") from None
        return True

    def replace_if_version(
        self,
        pk: str,
        sk: str,
        *,
        expected_version: int,
        replacement: Mapping[str, Any],
    ) -> bool:
        if type(expected_version) is not int or expected_version < 1:
            raise AdapterError("DDB_EXPECTED_VERSION_INVALID")
        physical = self._physical(replacement)
        if physical["pk"]["S"] != pk or physical["sk"]["S"] != sk:
            raise AdapterError("DDB_REPLACE_KEY_MISMATCH")
        if int(physical["version"]["N"]) != expected_version + 1:
            raise AdapterError("DDB_REPLACE_VERSION_NOT_SUCCESSOR")
        head_put = {
            "Put": {
                "TableName": self.table_name,
                "Item": physical,
                "ConditionExpression": (
                    "#version = :expected AND #pk = :pk AND #sk = :sk"
                ),
                "ExpressionAttributeNames": {
                    "#version": "version",
                    "#pk": "pk",
                    "#sk": "sk",
                },
                "ExpressionAttributeValues": {
                    ":expected": {"N": str(expected_version)},
                    ":pk": {"S": pk},
                    ":sk": {"S": sk},
                },
            }
        }
        try:
            self._client.put_item(**head_put["Put"])
        except Exception as error:
            if _conditional_failed(error) or self._head_changed_after_transaction_error(
                pk, sk, expected_version
            ):
                return False
            raise AdapterError("DDB_CONDITIONAL_REPLACE_FAILED") from None
        if replacement.get("state") in POINTER_RELEASE_STATES:
            self.release_global_active_if_terminal(pk, sk)
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
        if type(expected_version) is not int or expected_version < 1:
            raise AdapterError("DDB_EXPECTED_VERSION_INVALID")
        head = self._physical(replacement)
        immutable = self._physical_evidence(evidence_id, evidence)
        if head["pk"]["S"] != pk or head["sk"]["S"] != sk:
            raise AdapterError("DDB_TRANSACTION_HEAD_KEY_MISMATCH")
        if int(head["version"]["N"]) != expected_version + 1:
            raise AdapterError("DDB_REPLACE_VERSION_NOT_SUCCESSOR")
        token = self._transaction_token(
            {
                "operation": "REPLACE_HEAD_AND_PUT_EVIDENCE_IF_VERSION",
                "pk": pk,
                "sk": sk,
                "expected_version": expected_version,
                "replacement_version": replacement.get("version"),
                "evidence_id": evidence_id,
            }
        )
        transact_items: list[dict[str, Any]] = [
            {
                "Put": {
                    "TableName": self.table_name,
                    "Item": head,
                    "ConditionExpression": (
                        "#version = :expected AND #pk = :pk AND #sk = :sk"
                    ),
                    "ExpressionAttributeNames": {
                        "#version": "version",
                        "#pk": "pk",
                        "#sk": "sk",
                    },
                    "ExpressionAttributeValues": {
                        ":expected": {"N": str(expected_version)},
                        ":pk": {"S": pk},
                        ":sk": {"S": sk},
                    },
                }
            },
            {
                "Put": {
                    "TableName": self.table_name,
                    "Item": immutable,
                    "ConditionExpression": (
                        "attribute_not_exists(#pk) AND attribute_not_exists(#sk)"
                    ),
                    "ExpressionAttributeNames": {"#pk": "pk", "#sk": "sk"},
                }
            },
        ]
        create_capability = self._create_capability_item(replacement)
        if create_capability is not None:
            transact_items.append(
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": create_capability,
                        "ConditionExpression": (
                            "attribute_not_exists(#pk) AND attribute_not_exists(#sk)"
                        ),
                        "ExpressionAttributeNames": {"#pk": "pk", "#sk": "sk"},
                    }
                }
            )
        try:
            self._client.transact_write_items(
                ClientRequestToken=token,
                TransactItems=transact_items,
            )
        except Exception:
            if self._head_changed_after_transaction_error(pk, sk, expected_version):
                return False
            raise AdapterError("DDB_ATOMIC_TRANSITION_WRITE_FAILED") from None
        if replacement.get("state") in POINTER_RELEASE_STATES:
            self.release_global_active_if_terminal(pk, sk)
        return True

    def get_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        pk, sk = self._evidence_key(evidence_id)
        try:
            response = self._client.get_item(
                TableName=self.table_name,
                Key={"pk": {"S": pk}, "sk": {"S": sk}},
                ConsistentRead=True,
            )
        except Exception:
            raise AdapterError("DDB_EVIDENCE_READ_FAILED") from None
        item = response.get("Item") if isinstance(response, Mapping) else None
        if item is None:
            return None
        if not isinstance(item, Mapping):
            raise AdapterError("DDB_EVIDENCE_READ_MALFORMED")
        return self._decode_evidence(evidence_id, item)

    def mark_containment_time_uncertain(self, pk: str, sk: str) -> None:
        """Persist that no positive deadline/SLA claim may use fallback time."""

        for _ in range(16):
            current = self.get_consistent(pk, sk)
            if current is None:
                raise AdapterError("TIME_UNCERTAIN_HEAD_ABSENT")
            replacement = dict(current)
            replacement.update(
                {
                    "version": int(current["version"]) + 1,
                    "trusted_time_unavailable": True,
                    "stop_attempt_before_deadline_observed": False,
                    "stop_before_deadline": False,
                    "containment_sla_met": False,
                }
            )
            if self.replace_if_version(
                pk,
                sk,
                expected_version=int(current["version"]),
                replacement=replacement,
            ):
                return
        raise AdapterError("TIME_UNCERTAIN_MARKER_CONTENTION")


class AwsKmsReceiptSigner:
    """Asymmetric AWS KMS ECDSA signer using MessageType=DIGEST only."""

    algorithm = "ECDSA_SHA_256"
    message_type = "DIGEST"

    def __init__(self, client: Any, key_arn: str) -> None:
        if not isinstance(key_arn, str) or not key_arn.startswith("arn:aws"):
            raise AdapterError("KMS_KEY_ARN_INVALID")
        self._client = client
        self.key_arn = key_arn

    def sign_digest(self, digest: bytes) -> guardian.KmsSignature:
        if type(digest) is not bytes or len(digest) != 32:
            raise AdapterError("KMS_DIGEST_MUST_BE_32_BYTES")
        try:
            response = self._client.sign(
                KeyId=self.key_arn,
                Message=digest,
                MessageType=self.message_type,
                SigningAlgorithm=self.algorithm,
            )
        except Exception:
            raise AdapterError("KMS_SIGN_FAILED") from None
        if not isinstance(response, Mapping):
            raise AdapterError("KMS_SIGN_RESPONSE_MALFORMED")
        signature = response.get("Signature")
        if isinstance(signature, bytearray):
            signature = bytes(signature)
        if (
            response.get("KeyId") != self.key_arn
            or response.get("SigningAlgorithm") != self.algorithm
            or type(signature) is not bytes
            or not (8 <= len(signature) <= 512)
        ):
            raise AdapterError("KMS_SIGN_RESPONSE_IDENTITY_MISMATCH")
        return guardian.KmsSignature(
            key_arn=self.key_arn,
            algorithm=self.algorithm,
            message_type=self.message_type,
            signature=signature,
        )


def verify_receipt_with_kms(
    receipt: Mapping[str, Any], *, kms_client: Any, expected_key_arn: str
) -> bool:
    """Validate every retained hash, then ask KMS to verify the exact digest."""

    if receipt.get("kms_key_arn") != expected_key_arn:
        raise AdapterError("RECEIPT_KMS_KEY_MISMATCH")
    if receipt.get("kms_signing_algorithm") != "ECDSA_SHA_256":
        raise AdapterError("RECEIPT_KMS_ALGORITHM_MISMATCH")
    if receipt.get("kms_message_type") != "DIGEST":
        raise AdapterError("RECEIPT_KMS_MESSAGE_TYPE_NOT_DIGEST")
    message = guardian.receipt_signing_message(receipt)
    digest = hashlib.sha256(message).digest()
    retained_digest = _strict_b64(
        receipt.get("kms_digest_base64"), label="RECEIPT_KMS_DIGEST", max_bytes=32
    )
    if not hmac.compare_digest(digest, retained_digest):
        raise AdapterError("RECEIPT_KMS_DIGEST_MISMATCH")
    signature = _strict_b64(
        receipt.get("kms_signature_base64"),
        label="RECEIPT_KMS_SIGNATURE",
        max_bytes=512,
    )
    try:
        response = kms_client.verify(
            KeyId=expected_key_arn,
            Message=digest,
            MessageType="DIGEST",
            Signature=signature,
            SigningAlgorithm="ECDSA_SHA_256",
        )
    except Exception:
        raise AdapterError("KMS_VERIFY_FAILED") from None
    return isinstance(response, Mapping) and response.get("SignatureValid") is True


class ExactSecretGuard:
    """Reject direct, normalized JSON, and reversible credential encodings."""

    def __init__(self, secrets: Sequence[bytes]) -> None:
        needles: set[bytes] = set()
        for value in secrets:
            if type(value) is not bytes or len(value) < 20:
                raise AdapterError("SECRET_VALUE_TOO_SHORT")
            for candidate in (value, b"Bearer " + value):
                needles.add(candidate)
                needles.add(base64.b64encode(candidate))
                needles.add(base64.b64encode(candidate).rstrip(b"="))
                needles.add(base64.urlsafe_b64encode(candidate))
                needles.add(base64.urlsafe_b64encode(candidate).rstrip(b"="))
                needles.add(base64.b32encode(candidate))
                needles.add(base64.b32encode(candidate).rstrip(b"="))
                needles.add(candidate.hex().encode("ascii"))
                needles.add(candidate.hex().upper().encode("ascii"))
                percent = b"".join(
                    f"%{byte:02X}".encode("ascii") for byte in candidate
                )
                needles.add(percent)
                needles.add(percent.lower())
                try:
                    text = candidate.decode("utf-8")
                except UnicodeDecodeError:
                    text = ""
                if text:
                    escaped = "".join(f"\\u{ord(character):04x}" for character in text)
                    needles.add(escaped.encode("ascii"))
                    needles.add(escaped.upper().encode("ascii"))
        self._needles = tuple(sorted(needles, key=lambda value: (len(value), value)))

    def _assert_views_safe(self, views: Sequence[bytes]) -> None:
        for needle in self._needles:
            for view in views:
                if needle and (
                    hmac.compare_digest(needle, view) or needle in view
                ):
                    raise SecretExposure("SECRET_EXPOSURE_REJECTED")

    def assert_safe(self, raw: bytes) -> None:
        if type(raw) is not bytes:
            raise SecretExposure("NON_BYTE_EVIDENCE_REJECTED")
        views = [raw]
        # Percent escapes are case-insensitive.  Decode the complete bounded
        # byte string so alternating-case encodings cannot evade literal
        # uppercase/lowercase needles.  The decoded view is never retained.
        try:
            percent_decoded = unquote_to_bytes(raw.decode("ascii"))
        except (UnicodeDecodeError, ValueError):
            percent_decoded = raw
        if percent_decoded != raw:
            views.append(percent_decoded)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, TypeError, RecursionError):
            parsed = None
        if parsed is not None:
            stack = [parsed]
            text_values: list[bytes] = []
            visited = 0
            while stack:
                visited += 1
                if visited > 100_000:
                    raise SecretExposure("SECRET_NORMALIZATION_LIMIT_EXCEEDED")
                value = stack.pop()
                if isinstance(value, str):
                    text_values.append(value.encode("utf-8"))
                elif isinstance(value, list):
                    stack.extend(reversed(value))
                elif isinstance(value, dict):
                    for key, child in reversed(list(value.items())):
                        text_values.append(str(key).encode("utf-8"))
                        stack.append(child)
            views.extend(text_values)
            if text_values:
                # Joining ordered scalar strings catches a credential split over
                # adjacent JSON fields/list elements without retaining the text.
                views.append(b"".join(text_values))
        self._assert_views_safe(views)


@dataclass(frozen=True)
class ProviderSecret:
    provider_account_id: str
    api_key: bytes
    deployment_binding_sha256: str


def load_provider_secret(client: Any, secret_arn: str) -> ProviderSecret:
    if not isinstance(secret_arn, str) or not _SECRET_ARN.fullmatch(secret_arn):
        raise ActivationError("PROVIDER_SECRET_ARN_UNBOUND")
    try:
        response = client.get_secret_value(SecretId=secret_arn)
    except Exception:
        raise ActivationError("PROVIDER_SECRET_UNAVAILABLE") from None
    if not isinstance(response, Mapping) or "SecretString" not in response:
        raise ActivationError("PROVIDER_SECRET_FORMAT_INVALID")
    raw_text = response.get("SecretString")
    if not isinstance(raw_text, str):
        raise ActivationError("PROVIDER_SECRET_FORMAT_INVALID")
    try:
        parsed = json.loads(raw_text)
    except (ValueError, TypeError):
        raise ActivationError("PROVIDER_SECRET_FORMAT_INVALID") from None
    if not isinstance(parsed, dict) or set(parsed) != {
        "schema_version",
        "provider_account_id",
        "api_key",
        "deployment_binding_sha256",
    }:
        raise ActivationError("PROVIDER_SECRET_SCHEMA_INVALID")
    if parsed.get("schema_version") != SECRET_SCHEMA:
        raise ActivationError("PROVIDER_SECRET_SCHEMA_INVALID")
    account = parsed.get("provider_account_id")
    api_key_text = parsed.get("api_key")
    binding = parsed.get("deployment_binding_sha256")
    if not isinstance(account, str) or not account or len(account) > 128:
        raise ActivationError("PROVIDER_ACCOUNT_BINDING_INVALID")
    if not isinstance(api_key_text, str) or not (20 <= len(api_key_text) <= 512):
        raise ActivationError("PROVIDER_SECRET_VALUE_INVALID")
    if not isinstance(binding, str) or not _SHA256.fullmatch(binding):
        raise ActivationError("PROVIDER_SECRET_BINDING_INVALID")
    return ProviderSecret(account, api_key_text.encode("utf-8"), binding)


class AwsTrustedClock:
    """UTC sourced from the signed-TLS AWS STS response Date header.

    Lambda wall time is used only as a coarse skew detector.  A missing,
    malformed, non-UTC, or implausibly skewed AWS service timestamp fails
    closed.
    """

    def __init__(
        self,
        sts_client: Any,
        *,
        wall_clock: Callable[[], datetime] | None = None,
        maximum_skew_seconds: int = 300,
    ) -> None:
        self._sts = sts_client
        self._wall_clock = wall_clock or (lambda: datetime.now(timezone.utc))
        self._maximum_skew = maximum_skew_seconds

    def now(self) -> datetime:
        try:
            response = self._sts.get_caller_identity()
        except Exception:
            raise AdapterError("TRUSTED_CLOCK_STS_UNAVAILABLE") from None
        try:
            headers = response["ResponseMetadata"]["HTTPHeaders"]
            date_text = headers.get("date") or headers.get("Date")
            value = parsedate_to_datetime(date_text).astimezone(timezone.utc)
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
            raise AdapterError("TRUSTED_CLOCK_DATE_INVALID") from None
        wall = self._wall_clock()
        if not isinstance(wall, datetime) or wall.tzinfo is None:
            raise AdapterError("RUNTIME_WALL_CLOCK_INVALID")
        if abs((value - wall.astimezone(timezone.utc)).total_seconds()) > self._maximum_skew:
            raise AdapterError("TRUSTED_CLOCK_SKEW_EXCEEDED")
        return value


class ContainmentClock:
    """UTC for STOP urgency that cannot be disabled by an STS outage.

    STS remains preferred chronology evidence.  If it is unavailable or
    rejects its Date header, Lambda's local UTC is used so uncertainty fails
    toward an immediate exact-ID STOP instead of suppressing containment.
    """

    def __init__(
        self,
        trusted_clock: AwsTrustedClock | None = None,
        *,
        wall_clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._trusted = trusted_clock
        self._wall = wall_clock or (lambda: datetime.now(timezone.utc))
        self._last: datetime | None = None
        self._lock = threading.Lock()
        self.time_uncertain = trusted_clock is None
        self._proof_requires_trusted_time = False
        self._uncertainty_callbacks: list[Callable[[], None]] = []

    def on_uncertainty(self, callback: Callable[[], None]) -> None:
        if not callable(callback):
            raise AdapterError("CONTAINMENT_CLOCK_CALLBACK_INVALID")
        self._uncertainty_callbacks.append(callback)
        if self.time_uncertain:
            callback()

    def require_trusted_time_for_proof(self) -> None:
        """Make any prior or later uncertainty abort terminal-proof signing."""

        self._proof_requires_trusted_time = True
        if self.time_uncertain:
            raise AdapterError("CONTAINMENT_PROOF_TRUSTED_TIME_UNAVAILABLE")

    def _mark_uncertain(self) -> None:
        first_observation = not self.time_uncertain
        self.time_uncertain = True
        if first_observation:
            for callback in tuple(self._uncertainty_callbacks):
                callback()

    def force_conservative_floor(self, floor: datetime) -> None:
        """Carry a prior trusted-time failure into a containment worker.

        Recovery may know from the ledger that the exact-ID STOP dispatch time
        is due even when Lambda's wall clock is behind and STS is unavailable.
        The floor is never accepted from an external starter request: the
        worker derives it again from the strongly read authorization record.
        """

        if not isinstance(floor, datetime) or floor.tzinfo is None:
            raise AdapterError("CONTAINMENT_CLOCK_FLOOR_INVALID")
        floor = floor.astimezone(timezone.utc)
        self._mark_uncertain()
        with self._lock:
            if self._last is None or floor > self._last:
                self._last = floor

    def now(self) -> datetime:
        if self._proof_requires_trusted_time and self.time_uncertain:
            raise AdapterError("CONTAINMENT_PROOF_TRUSTED_TIME_UNAVAILABLE")
        try:
            value = self._trusted.now() if self._trusted is not None else self._wall()
        except Exception:
            self._mark_uncertain()
            if self._proof_requires_trusted_time:
                raise AdapterError("CONTAINMENT_PROOF_TRUSTED_TIME_UNAVAILABLE") from None
            value = self._wall()
        if self._trusted is None:
            self._mark_uncertain()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise AdapterError("CONTAINMENT_CLOCK_INVALID")
        value = value.astimezone(timezone.utc)
        with self._lock:
            if self._last is not None and value < self._last:
                value = self._last
            self._last = value
        return value

    def trusted_now_available(self) -> bool:
        self.now()
        return not self.time_uncertain


class StrictRunPodTransport:
    """One-shot fixed-host HTTPS transport with an explicit method allowlist."""

    def __init__(
        self,
        *,
        provider_account_id: str,
        api_key: bytes,
        secret_guard: ExactSecretGuard,
        allowed_operations: frozenset[str],
        connection_factory: Callable[..., Any] | None = None,
        timeout_seconds: int = 10,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        if not isinstance(provider_account_id, str) or not provider_account_id:
            raise AdapterError("PROVIDER_ACCOUNT_ID_INVALID")
        if type(api_key) is not bytes or not (20 <= len(api_key) <= 512):
            raise AdapterError("PROVIDER_API_KEY_INVALID")
        permitted = frozenset({"LIST", "CREATE", "GET", "STOP"})
        if not isinstance(allowed_operations, frozenset) or not allowed_operations <= permitted:
            raise AdapterError("PROVIDER_METHOD_ALLOWLIST_INVALID")
        self._account = provider_account_id
        self._api_key = api_key
        self._guard = secret_guard
        self._allowed = allowed_operations
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 30:
            raise AdapterError("PROVIDER_TIMEOUT_INVALID")
        self._timeout = timeout_seconds
        self._connection_factory = connection_factory or http.client.HTTPSConnection
        self._monotonic = monotonic_clock or time.monotonic

    @staticmethod
    def _tls_context() -> ssl.SSLContext:
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context

    def _assert_account(self, provider_account_id: str) -> None:
        if provider_account_id != self._account:
            raise TransportError("PROVIDER_ACCOUNT_MISMATCH")

    def _request(self, method: str, path: str, body: bytes | None) -> guardian.HttpResponse:
        if not path.startswith(PROVIDER_ROOT) or "?" in path or "#" in path:
            raise TransportError("PROVIDER_PATH_NOT_ALLOWLISTED")
        if body is not None:
            self._guard.assert_safe(body)
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self._api_key.decode("utf-8"),
            "Connection": "close",
            "User-Agent": "cas-aws-runpod-guardian/1",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(body))
        deadline = self._monotonic() + self._timeout
        finished = threading.Event()
        cancelled = threading.Event()
        exchange: dict[str, Any] = {}

        def run_exchange() -> None:
            connection = None
            try:
                connection = self._connection_factory(
                    PROVIDER_HOST,
                    PROVIDER_PORT,
                    timeout=self._timeout,
                    context=self._tls_context(),
                )
                exchange["connection"] = connection
                if cancelled.is_set():
                    raise TransportError("PROVIDER_TOTAL_DEADLINE_EXCEEDED")
                # Exactly one request call.  There is deliberately no retry
                # loop.  The outer watchdog bounds connect/write/read as one
                # wall-clock operation and closes this connection on expiry.
                connection.request(method, path, body=body, headers=headers)
                remaining = deadline - self._monotonic()
                if remaining <= 0 or cancelled.is_set():
                    raise TransportError("PROVIDER_TOTAL_DEADLINE_EXCEEDED")
                connection_socket = getattr(connection, "sock", None)
                if connection_socket is not None and hasattr(
                    connection_socket, "settimeout"
                ):
                    connection_socket.settimeout(remaining)
                response = connection.getresponse()
                remaining = deadline - self._monotonic()
                if remaining <= 0 or cancelled.is_set():
                    raise TransportError("PROVIDER_TOTAL_DEADLINE_EXCEEDED")
                if connection_socket is not None and hasattr(
                    connection_socket, "settimeout"
                ):
                    connection_socket.settimeout(remaining)
                status = response.status
                content_type = response.getheader("Content-Type", "")
                content_encoding = response.getheader("Content-Encoding", "")
                location = response.getheader("Location")
                pagination = response.getheader("Link") or response.getheader(
                    "X-Next-Cursor"
                )
                content_length = response.getheader("Content-Length")
                if content_length is not None:
                    try:
                        if int(content_length) > MAX_HTTP_BODY_BYTES:
                            raise TransportError("PROVIDER_BODY_TOO_LARGE")
                    except ValueError:
                        raise TransportError(
                            "PROVIDER_CONTENT_LENGTH_INVALID"
                        ) from None
                raw = response.read(MAX_HTTP_BODY_BYTES + 1)
                if self._monotonic() > deadline or cancelled.is_set():
                    raise TransportError("PROVIDER_TOTAL_DEADLINE_EXCEEDED")
                exchange["result"] = (
                    status,
                    content_type,
                    content_encoding,
                    location,
                    pagination,
                    raw,
                )
            except BaseException as error:
                exchange["error"] = error
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:
                        pass
                finished.set()

        worker = threading.Thread(
            target=run_exchange,
            name="cas-runpod-one-shot-transport",
            daemon=True,
        )
        worker.start()
        if not finished.wait(timeout=self._timeout):
            cancelled.set()
            connection = exchange.get("connection")
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
            raise TransportError("PROVIDER_TOTAL_DEADLINE_EXCEEDED")
        error = exchange.get("error")
        if error is not None:
            if isinstance(error, TransportError):
                raise error
            # The caller treats this as ambiguous when a mutating request may
            # have crossed the wire.  Never include provider/credential text.
            raise TransportError("PROVIDER_EXCHANGE_AMBIGUOUS") from None
        result = exchange.get("result")
        if not isinstance(result, tuple) or len(result) != 6:
            raise TransportError("PROVIDER_RESPONSE_ENVELOPE_INVALID")
        status, content_type, content_encoding, location, pagination, raw = result
        if type(status) is not int or not isinstance(raw, bytes):
            raise TransportError("PROVIDER_RESPONSE_ENVELOPE_INVALID")
        if len(raw) > MAX_HTTP_BODY_BYTES:
            raise TransportError("PROVIDER_BODY_TOO_LARGE")
        if location:
            raise TransportError("PROVIDER_REDIRECT_REJECTED")
        if pagination:
            # The current official account-wide List Pods endpoint is a single
            # unfiltered JSON array.  A newly paginated contract must be
            # reviewed before it can be called complete.
            raise TransportError("PROVIDER_UNREVIEWED_PAGINATION_REJECTED")
        if content_encoding not in {None, "", "identity"}:
            raise TransportError("PROVIDER_CONTENT_ENCODING_REJECTED")
        self._guard.assert_safe(raw)
        return guardian.HttpResponse(
            status_code=status,
            body=raw,
            effective_url=f"https://{PROVIDER_HOST}{path}",
            content_type=content_type or "",
            content_encoding=content_encoding or "",
        )

    def list_all_pods(self, provider_account_id: str) -> guardian.InventorySnapshot:
        self._assert_account(provider_account_id)
        if "LIST" not in self._allowed:
            raise TransportError("PROVIDER_LIST_NOT_ALLOWED")
        response = self._request("GET", PROVIDER_ROOT, None)
        if response.status_code != 200:
            raise TransportError("PROVIDER_LIST_STATUS_NOT_200")
        if response.content_type.lower().split(";", 1)[0].strip() != "application/json":
            raise TransportError("PROVIDER_LIST_CONTENT_TYPE_INVALID")
        # Structural validation is repeated by the provider-neutral core.
        value = guardian.strict_json(
            response.body,
            "RunPod complete account inventory",
            max_bytes=guardian.MAX_INVENTORY_TOTAL_BYTES,
        )
        if not isinstance(value, list):
            raise TransportError("PROVIDER_LIST_BODY_NOT_ARRAY")
        return guardian.InventorySnapshot(
            provider_account_id=provider_account_id,
            scope=guardian.INVENTORY_SCOPE,
            complete=True,
            unfiltered=True,
            raw_pages=(response.body,),
        )

    def post_create(
        self, provider_account_id: str, endpoint: str, exact_body: bytes
    ) -> guardian.HttpResponse:
        self._assert_account(provider_account_id)
        if "CREATE" not in self._allowed:
            raise TransportError("PROVIDER_CREATE_NOT_ALLOWED")
        if endpoint != guardian.CREATE_ENDPOINT:
            raise TransportError("PROVIDER_CREATE_ENDPOINT_MISMATCH")
        return self._request("POST", PROVIDER_ROOT, exact_body)

    def get_pod(self, provider_account_id: str, pod_id: str) -> guardian.HttpResponse:
        self._assert_account(provider_account_id)
        if "GET" not in self._allowed:
            raise TransportError("PROVIDER_GET_NOT_ALLOWED")
        if not isinstance(pod_id, str) or not _POD_ID.fullmatch(pod_id):
            raise TransportError("PROVIDER_POD_ID_INVALID")
        return self._request("GET", f"{PROVIDER_ROOT}/{pod_id}", None)

    def stop_pod(self, provider_account_id: str, pod_id: str) -> guardian.HttpResponse:
        self._assert_account(provider_account_id)
        if "STOP" not in self._allowed:
            raise TransportError("PROVIDER_STOP_NOT_ALLOWED")
        if not isinstance(pod_id, str) or not _POD_ID.fullmatch(pod_id):
            raise TransportError("PROVIDER_POD_ID_INVALID")
        return self._request("POST", f"{PROVIDER_ROOT}/{pod_id}/stop", None)


class DenyProviderTransport:
    """Control-plane port that cannot make any provider request."""

    def _deny(self) -> None:
        raise TransportError("CONTROL_HANDLER_HAS_NO_PROVIDER_AUTHORITY")

    def assert_safe(self, raw: bytes) -> None:
        self._deny()

    def list_all_pods(self, provider_account_id: str) -> guardian.InventorySnapshot:
        self._deny()

    def post_create(
        self, provider_account_id: str, endpoint: str, exact_body: bytes
    ) -> guardian.HttpResponse:
        self._deny()

    def get_pod(self, provider_account_id: str, pod_id: str) -> guardian.HttpResponse:
        self._deny()

    def stop_pod(self, provider_account_id: str, pod_id: str) -> guardian.HttpResponse:
        self._deny()


class LambdaProviderBoundary:
    """Secretless core-side client for one IAM-scoped provider proxy Lambda."""

    def __init__(
        self,
        client: Any,
        *,
        function_arn: str,
        deployment_binding_sha256: str,
        provider_account_id: str,
        allowed_operations: frozenset[str],
    ) -> None:
        if not isinstance(function_arn, str) or ":lambda:" not in function_arn:
            raise ActivationError("PROVIDER_PROXY_ARN_INVALID")
        if not _SHA256.fullmatch(deployment_binding_sha256):
            raise ActivationError("PROVIDER_PROXY_BINDING_INVALID")
        if not isinstance(provider_account_id, str) or not provider_account_id:
            raise ActivationError("PROVIDER_PROXY_ACCOUNT_INVALID")
        permitted = frozenset({"GUARD", "LIST", "CREATE", "GET", "STOP"})
        if (
            not isinstance(allowed_operations, frozenset)
            or "GUARD" not in allowed_operations
            or not allowed_operations <= permitted
        ):
            raise ActivationError("PROVIDER_PROXY_METHODS_INVALID")
        self._client = client
        self._function_arn = function_arn
        self._binding = deployment_binding_sha256
        self._account = provider_account_id
        self._allowed = allowed_operations
        self._create_capability: dict[str, Any] | None = None

    def bind_create_capability(
        self,
        *,
        key: guardian.AuthorizationKey,
        token: guardian.ExecutionToken,
        reservation: guardian.CreateReservation,
        owner_lease_expires_at_utc: str,
        not_after_utc: str,
    ) -> None:
        if "CREATE" not in self._allowed or self._create_capability is not None:
            raise TransportError("CREATE_CAPABILITY_BINDING_REJECTED")
        if token.key != key or reservation.key != key:
            raise TransportError("CREATE_CAPABILITY_KEY_MISMATCH")
        guardian.parse_utc(owner_lease_expires_at_utc)
        guardian.parse_utc(not_after_utc)
        self._create_capability = {
            "head_pk": key.pk,
            "head_sk": key.sk,
            "reservation_id": reservation.reservation_id,
            "request_sha256": reservation.request_sha256,
            "owner_fence": token.fence,
            "owner_execution_arn": token.execution_arn,
            "owner_lease_expires_at_utc": owner_lease_expires_at_utc,
            "not_after_utc": not_after_utc,
        }

    def _invoke(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if operation not in self._allowed:
            raise TransportError("PROVIDER_PROXY_OPERATION_NOT_ALLOWED")
        request = {
            "schema_version": PROXY_SCHEMA,
            "deployment_binding_sha256": self._binding,
            "provider_account_id": self._account,
            "operation": operation,
            "payload": dict(payload),
        }
        try:
            response = self._client.invoke(
                FunctionName=self._function_arn,
                InvocationType="RequestResponse",
                Payload=_canonical(request),
            )
            if (
                not isinstance(response, Mapping)
                or response.get("StatusCode") != 200
                or response.get("FunctionError") is not None
            ):
                raise TransportError("PROVIDER_PROXY_FUNCTION_FAILED")
            stream = response.get("Payload")
            if not hasattr(stream, "read"):
                raise TransportError("PROVIDER_PROXY_PAYLOAD_ABSENT")
            raw = stream.read(MAX_PROXY_PAYLOAD_BYTES + 1)
        except TransportError:
            raise
        except Exception:
            # No SDK retries are configured for this client.  A lost CREATE
            # proxy response therefore remains one ambiguous provider attempt.
            raise TransportError("PROVIDER_PROXY_EXCHANGE_AMBIGUOUS") from None
        if not isinstance(raw, bytes) or len(raw) > MAX_PROXY_PAYLOAD_BYTES:
            raise TransportError("PROVIDER_PROXY_PAYLOAD_INVALID")
        parsed = guardian.strict_json(
            raw, "method-enforcing provider proxy response", max_bytes=MAX_PROXY_PAYLOAD_BYTES
        )
        if not isinstance(parsed, dict) or parsed.get("schema_version") != PROXY_SCHEMA:
            raise TransportError("PROVIDER_PROXY_RESPONSE_SCHEMA_INVALID")
        return parsed

    def assert_safe(self, raw: bytes) -> None:
        if type(raw) is not bytes:
            raise SecretExposure("NON_BYTE_EVIDENCE_REJECTED")
        response = self._invoke(
            "GUARD", {"raw_base64": base64.b64encode(raw).decode("ascii")}
        )
        if set(response) != {
            "schema_version",
            "safe",
            "compiled_core_lock_sha256",
        } or response.get("safe") is not True:
            raise SecretExposure("PROVIDER_PROXY_GUARD_REJECTED")
        if response.get("compiled_core_lock_sha256") != COMPILED_CORE_LOCK_SHA256:
            raise SecretExposure("PROVIDER_PROXY_BUILD_IDENTITY_MISMATCH")

    def _http_response(self, operation: str, payload: Mapping[str, Any]) -> guardian.HttpResponse:
        response = self._invoke(operation, payload)
        expected = {
            "schema_version",
            "status_code",
            "body_base64",
            "effective_url",
            "content_type",
            "content_encoding",
            "compiled_core_lock_sha256",
        }
        if set(response) != expected:
            raise TransportError("PROVIDER_PROXY_HTTP_SCHEMA_INVALID")
        if response.get("compiled_core_lock_sha256") != COMPILED_CORE_LOCK_SHA256:
            raise TransportError("PROVIDER_PROXY_BUILD_IDENTITY_MISMATCH")
        status = response.get("status_code")
        url = response.get("effective_url")
        content_type = response.get("content_type")
        content_encoding = response.get("content_encoding")
        if (
            type(status) is not int
            or not isinstance(url, str)
            or not isinstance(content_type, str)
            or not isinstance(content_encoding, str)
        ):
            raise TransportError("PROVIDER_PROXY_HTTP_ENVELOPE_INVALID")
        body = _strict_b64_allow_empty(
            response.get("body_base64"),
            label="PROVIDER_PROXY_HTTP_BODY",
            max_bytes=MAX_HTTP_BODY_BYTES,
        )
        return guardian.HttpResponse(status, body, url, content_type, content_encoding)

    def list_all_pods(self, provider_account_id: str) -> guardian.InventorySnapshot:
        if provider_account_id != self._account:
            raise TransportError("PROVIDER_ACCOUNT_MISMATCH")
        response = self._invoke("LIST", {})
        expected = {
            "schema_version",
            "provider_account_id",
            "scope",
            "complete",
            "unfiltered",
            "raw_pages_base64",
            "compiled_core_lock_sha256",
        }
        if set(response) != expected or response.get("provider_account_id") != self._account:
            raise TransportError("PROVIDER_PROXY_INVENTORY_SCHEMA_INVALID")
        if response.get("compiled_core_lock_sha256") != COMPILED_CORE_LOCK_SHA256:
            raise TransportError("PROVIDER_PROXY_BUILD_IDENTITY_MISMATCH")
        pages_value = response.get("raw_pages_base64")
        if not isinstance(pages_value, list) or not pages_value:
            raise TransportError("PROVIDER_PROXY_INVENTORY_PAGES_INVALID")
        pages = tuple(
            _strict_b64(value, label="PROVIDER_PROXY_INVENTORY_PAGE", max_bytes=guardian.MAX_INVENTORY_PAGE_BYTES)
            for value in pages_value
        )
        return guardian.InventorySnapshot(
            provider_account_id=self._account,
            scope=str(response.get("scope")),
            complete=response.get("complete") is True,
            unfiltered=response.get("unfiltered") is True,
            raw_pages=pages,
        )

    def post_create(
        self, provider_account_id: str, endpoint: str, exact_body: bytes
    ) -> guardian.HttpResponse:
        if provider_account_id != self._account:
            raise TransportError("PROVIDER_ACCOUNT_MISMATCH")
        capability = self._create_capability
        self._create_capability = None
        if capability is None:
            raise TransportError("CREATE_CAPABILITY_NOT_BOUND")
        if _sha256(exact_body) != capability["request_sha256"]:
            raise TransportError("CREATE_CAPABILITY_BODY_MISMATCH")
        return self._http_response(
            "CREATE",
            {
                "endpoint": endpoint,
                "body_base64": base64.b64encode(exact_body).decode("ascii"),
                **capability,
            },
        )

    def get_pod(self, provider_account_id: str, pod_id: str) -> guardian.HttpResponse:
        if provider_account_id != self._account:
            raise TransportError("PROVIDER_ACCOUNT_MISMATCH")
        return self._http_response("GET", {"pod_id": pod_id})

    def stop_pod(self, provider_account_id: str, pod_id: str) -> guardian.HttpResponse:
        if provider_account_id != self._account:
            raise TransportError("PROVIDER_ACCOUNT_MISMATCH")
        return self._http_response("STOP", {"pod_id": pod_id})


class SplitStopProviderBoundary:
    """STOP through the stop proxy; post-STOP exact GET through observe proxy."""

    def __init__(
        self,
        stop_boundary: LambdaProviderBoundary,
        observe_boundary: LambdaProviderBoundary,
        *,
        containment_clock: ContainmentClock | None = None,
    ) -> None:
        self._stop = stop_boundary
        self._observe = observe_boundary
        self._observation_allowed = True
        self._containment_clock = containment_clock

    def bind_containment_clock(self, clock: ContainmentClock) -> None:
        if not isinstance(clock, ContainmentClock):
            raise AdapterError("STOP_BOUNDARY_CLOCK_INVALID")
        self._containment_clock = clock

    def disable_post_stop_observation(self) -> None:
        self._observation_allowed = False

    def assert_safe(self, raw: bytes) -> None:
        self._observe.assert_safe(raw)

    def list_all_pods(self, provider_account_id: str) -> guardian.InventorySnapshot:
        raise TransportError("STOP_BOUNDARY_LIST_NOT_ALLOWED")

    def post_create(
        self, provider_account_id: str, endpoint: str, exact_body: bytes
    ) -> guardian.HttpResponse:
        raise TransportError("STOP_BOUNDARY_CREATE_NOT_ALLOWED")

    def get_pod(self, provider_account_id: str, pod_id: str) -> guardian.HttpResponse:
        if not self._observation_allowed:
            raise TransportError("UNTRUSTED_TIME_POST_STOP_GET_DEFERRED")
        return self._observe.get_pod(provider_account_id, pod_id)

    def stop_pod(self, provider_account_id: str, pod_id: str) -> guardian.HttpResponse:
        try:
            return self._stop.stop_pod(provider_account_id, pod_id)
        finally:
            # Exact-ID STOP has already been sent.  Every subsequent clock
            # sample used for GET/KMS proof must remain trusted; otherwise the
            # core is forced out before it can sign a positive SLA receipt.
            if self._containment_clock is not None:
                self._containment_clock.require_trusted_time_for_proof()


_PROXY_TRANSPORT_FACTORY: Callable[
    [str, Mapping[str, str]], tuple[StrictRunPodTransport, ExactSecretGuard]
] | None = None
_CREATE_CAPABILITY_CONSUMER: Callable[
    [Mapping[str, str], Mapping[str, Any], bytes], None
] | None = None
_CREATE_CAPABILITY_CLOCK: Callable[[], datetime] | None = None
_CREATE_CAPABILITY_DDB_FACTORY: Callable[[Mapping[str, str]], Any] | None = None


def _trusted_create_capability_now(environment: Mapping[str, str]) -> datetime:
    try:
        import boto3  # type: ignore
        from botocore.config import Config  # type: ignore

        sts = boto3.client(
            "sts",
            region_name=environment["AWS_REGION"],
            config=Config(
                connect_timeout=2,
                read_timeout=3,
                retries={"mode": "standard", "total_max_attempts": 1},
                user_agent_extra="cas-runpod-create-capability-clock/1",
            ),
        )
        return AwsTrustedClock(sts, maximum_skew_seconds=60).now()
    except Exception:
        raise AdapterError("CREATE_CAPABILITY_TRUSTED_TIME_UNAVAILABLE") from None


def _consume_create_capability(
    environment: Mapping[str, str], payload: Mapping[str, Any], exact_body: bytes
) -> None:
    required = {
        "endpoint",
        "body_base64",
        "head_pk",
        "head_sk",
        "reservation_id",
        "request_sha256",
        "owner_fence",
        "owner_execution_arn",
        "owner_lease_expires_at_utc",
        "not_after_utc",
    }
    if set(payload) != required:
        raise AdapterError("CREATE_CAPABILITY_SCHEMA_INVALID")
    head_pk = payload.get("head_pk")
    head_sk = payload.get("head_sk")
    reservation_id = payload.get("reservation_id")
    request_sha = payload.get("request_sha256")
    fence = payload.get("owner_fence")
    owner_execution = payload.get("owner_execution_arn")
    owner_lease = payload.get("owner_lease_expires_at_utc")
    not_after = payload.get("not_after_utc")
    try:
        owner_lease_time = guardian.parse_utc(str(owner_lease))
        not_after_time = guardian.parse_utc(str(not_after))
    except Exception:
        raise AdapterError("CREATE_CAPABILITY_TIME_INVALID") from None
    local_now = (
        _CREATE_CAPABILITY_CLOCK()
        if _CREATE_CAPABILITY_CLOCK is not None
        else _trusted_create_capability_now(environment)
    )
    if not isinstance(local_now, datetime) or local_now.tzinfo is None:
        raise AdapterError("CREATE_CAPABILITY_LOCAL_CLOCK_INVALID")
    local_now = local_now.astimezone(timezone.utc)
    if (
        not isinstance(head_pk, str)
        or not head_pk.startswith("CAS#RUNPOD#AUTH#")
        or not isinstance(head_sk, str)
        or head_sk != "STATE#v1"
        or not isinstance(reservation_id, str)
        or not _SHA256.fullmatch(reservation_id)
        or not isinstance(request_sha, str)
        or not _SHA256.fullmatch(request_sha)
        or type(fence) is not int
        or fence < 1
        or not isinstance(owner_execution, str)
        or not owner_execution
        or local_now >= owner_lease_time
        or local_now > not_after_time
        or payload.get("endpoint") != guardian.CREATE_ENDPOINT
        or _sha256(exact_body) != request_sha
    ):
        raise AdapterError("CREATE_CAPABILITY_IDENTITY_INVALID")
    if _CREATE_CAPABILITY_CONSUMER is not None:
        _CREATE_CAPABILITY_CONSUMER(environment, payload, exact_body)
        return
    try:
        if _CREATE_CAPABILITY_DDB_FACTORY is not None:
            client = _CREATE_CAPABILITY_DDB_FACTORY(environment)
        else:
            import boto3  # type: ignore
            from botocore.config import Config  # type: ignore

            client = boto3.client(
                "dynamodb",
                region_name=environment["AWS_REGION"],
                config=Config(
                    connect_timeout=3,
                    read_timeout=8,
                    retries={"mode": "standard", "total_max_attempts": 1},
                    user_agent_extra="cas-runpod-create-capability/1",
                ),
            )
        client.transact_write_items(
            # Unique per invocation: reusing a token would let a duplicate
            # replay DynamoDB's cached idempotent success and issue a 2nd POST.
            ClientRequestToken=uuid.uuid4().hex,
            TransactItems=[
                {
                    "Update": {
                        "TableName": environment["LEDGER_TABLE_NAME"],
                        "Key": {
                            "pk": {"S": CREATE_CAPABILITY_PREFIX + reservation_id},
                            "sk": {"S": CREATE_CAPABILITY_SK},
                        },
                        "UpdateExpression": "SET #consumed = :true",
                        "ConditionExpression": (
                            "#item_type = :item_type AND #consumed = :false "
                            "AND #head_pk = :head_pk AND #head_sk = :head_sk "
                            "AND #reservation = :reservation "
                            "AND #request = :request AND #fence = :fence "
                            "AND #owner = :owner AND #lease = :lease "
                            "AND #not_after = :not_after"
                        ),
                        "ExpressionAttributeNames": {
                            "#item_type": "item_type",
                            "#consumed": "consumed",
                            "#head_pk": "head_pk",
                            "#head_sk": "head_sk",
                            "#reservation": "reservation_id",
                            "#request": "request_sha256",
                            "#fence": "owner_fence",
                            "#owner": "owner_execution_arn",
                            "#lease": "owner_lease_expires_at_utc",
                            "#not_after": "not_after_utc",
                        },
                        "ExpressionAttributeValues": {
                            ":item_type": {"S": "ONE_USE_CREATE_CAPABILITY"},
                            ":true": {"BOOL": True},
                            ":false": {"BOOL": False},
                            ":head_pk": {"S": head_pk},
                            ":head_sk": {"S": head_sk},
                            ":reservation": {"S": reservation_id},
                            ":request": {"S": request_sha},
                            ":fence": {"N": str(fence)},
                            ":owner": {"S": owner_execution},
                            ":lease": {"S": str(owner_lease)},
                            ":not_after": {"S": str(not_after)},
                        },
                    }
                },
                {
                    "ConditionCheck": {
                        "TableName": environment["LEDGER_TABLE_NAME"],
                        "Key": {"pk": {"S": head_pk}, "sk": {"S": head_sk}},
                        "ConditionExpression": (
                            "#item_type = :head_type AND #state = :state "
                            "AND #count = :one AND #reservation = :reservation "
                            "AND #request = :request AND #dispatch_fence = :fence "
                            "AND #current_fence = :fence AND #owner = :owner "
                            "AND #lease = :lease"
                        ),
                        "ExpressionAttributeNames": {
                            "#item_type": "item_type",
                            "#state": "state",
                            "#count": "create_dispatch_count",
                            "#reservation": "create_reservation_id",
                            "#request": "create_reserved_request_sha256",
                            "#dispatch_fence": "create_dispatch_owner_fence",
                            "#current_fence": "owner_fence",
                            "#owner": "owner_execution_arn",
                            "#lease": "owner_lease_expires_at_utc",
                        },
                        "ExpressionAttributeValues": {
                            ":head_type": {"S": "GUARDIAN_HEAD"},
                            ":state": {"S": "CREATE_DISPATCHED_UNKNOWN"},
                            ":one": {"N": "1"},
                            ":reservation": {"S": reservation_id},
                            ":request": {"S": request_sha},
                            ":fence": {"N": str(fence)},
                            ":owner": {"S": owner_execution},
                            ":lease": {"S": str(owner_lease)},
                        },
                    }
                },
            ],
        )
    except Exception:
        raise AdapterError("CREATE_CAPABILITY_CONSUME_FAILED") from None


def _real_proxy_transport(
    capability: str, environment: Mapping[str, str]
) -> tuple[StrictRunPodTransport, ExactSecretGuard]:
    try:
        import boto3  # type: ignore
        from botocore.config import Config  # type: ignore
    except ImportError:
        raise ActivationError("AWS_SDK_UNAVAILABLE") from None
    methods = {
        "observe_proxy": frozenset({"LIST", "GET"}),
        "create_proxy": frozenset({"CREATE"}),
        "stop_proxy": frozenset({"STOP"}),
    }
    if capability not in methods:
        raise ActivationError("PROVIDER_PROXY_CAPABILITY_INVALID")
    config = Config(
        connect_timeout=3,
        read_timeout=8,
        retries={"mode": "standard", "total_max_attempts": 3},
        user_agent_extra="cas-runpod-provider-proxy/1",
    )
    session = boto3.session.Session(region_name=environment["AWS_REGION"])
    secret = load_provider_secret(
        session.client("secretsmanager", config=config),
        environment.get("PROVIDER_SECRET_ARN", ""),
    )
    if secret.provider_account_id != environment.get("PROVIDER_ACCOUNT_ID"):
        raise ActivationError("PROVIDER_ACCOUNT_SECRET_MISMATCH")
    if secret.deployment_binding_sha256 != environment.get(
        "DEPLOYMENT_BINDING_SHA256"
    ):
        raise ActivationError("PROVIDER_SECRET_DEPLOYMENT_MISMATCH")
    guard = ExactSecretGuard((secret.api_key,))
    return (
        StrictRunPodTransport(
            provider_account_id=environment.get("PROVIDER_ACCOUNT_ID", ""),
            api_key=secret.api_key,
            secret_guard=guard,
            allowed_operations=methods[capability],
            timeout_seconds=7 if capability == "stop_proxy" else 8,
        ),
        guard,
    )


def _provider_proxy_handler(
    event: Any,
    context: Any,
    *,
    capability: str,
    allowed_operations: frozenset[str],
) -> dict[str, Any]:
    try:
        if not isinstance(event, Mapping) or set(event) != {
            "schema_version",
            "deployment_binding_sha256",
            "provider_account_id",
            "operation",
            "payload",
        }:
            raise AdapterError("PROVIDER_PROXY_REQUEST_SCHEMA_INVALID")
        if event.get("schema_version") != PROXY_SCHEMA:
            raise AdapterError("PROVIDER_PROXY_REQUEST_SCHEMA_INVALID")
        binding = event.get("deployment_binding_sha256")
        if not isinstance(binding, str):
            raise AdapterError("PROVIDER_PROXY_REQUEST_BINDING_INVALID")
        environment = dict(os.environ)
        _activation_gate(
            environment, binding, capability=capability, context=context
        )
        if event.get("provider_account_id") != environment.get("PROVIDER_ACCOUNT_ID"):
            raise AdapterError("PROVIDER_PROXY_REQUEST_ACCOUNT_MISMATCH")
        operation = event.get("operation")
        if operation not in allowed_operations:
            raise AdapterError("PROVIDER_PROXY_REQUEST_METHOD_NOT_ALLOWED")
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            raise AdapterError("PROVIDER_PROXY_REQUEST_PAYLOAD_INVALID")
        factory = _PROXY_TRANSPORT_FACTORY or _real_proxy_transport
        transport, guard = factory(capability, environment)
        if operation == "GUARD":
            if set(payload) != {"raw_base64"}:
                raise AdapterError("PROVIDER_PROXY_GUARD_PAYLOAD_INVALID")
            guard.assert_safe(
                _strict_b64_allow_empty(
                    payload.get("raw_base64"),
                    label="PROVIDER_PROXY_GUARD_BYTES",
                    max_bytes=MAX_HTTP_BODY_BYTES,
                )
            )
            return {
                "schema_version": PROXY_SCHEMA,
                "safe": True,
                "compiled_core_lock_sha256": COMPILED_CORE_LOCK_SHA256,
            }
        if operation == "LIST":
            if payload:
                raise AdapterError("PROVIDER_PROXY_LIST_PAYLOAD_INVALID")
            inventory = transport.list_all_pods(str(event["provider_account_id"]))
            return {
                "schema_version": PROXY_SCHEMA,
                "provider_account_id": inventory.provider_account_id,
                "scope": inventory.scope,
                "complete": inventory.complete,
                "unfiltered": inventory.unfiltered,
                "raw_pages_base64": [
                    base64.b64encode(page).decode("ascii")
                    for page in inventory.raw_pages
                ],
                "compiled_core_lock_sha256": COMPILED_CORE_LOCK_SHA256,
            }
        if operation == "CREATE":
            exact_body = _strict_b64(
                payload.get("body_base64"), label="PROVIDER_PROXY_CREATE_BODY"
            )
            _consume_create_capability(environment, payload, exact_body)
            response = transport.post_create(
                str(event["provider_account_id"]),
                str(payload.get("endpoint")),
                exact_body,
            )
        elif operation in {"GET", "STOP"}:
            if set(payload) != {"pod_id"} or not isinstance(
                payload.get("pod_id"), str
            ):
                raise AdapterError("PROVIDER_PROXY_POD_PAYLOAD_INVALID")
            if operation == "GET":
                response = transport.get_pod(
                    str(event["provider_account_id"]), str(payload["pod_id"])
                )
            else:
                response = transport.stop_pod(
                    str(event["provider_account_id"]), str(payload["pod_id"])
                )
        else:
            raise AdapterError("PROVIDER_PROXY_REQUEST_METHOD_NOT_ALLOWED")
        return {
            "schema_version": PROXY_SCHEMA,
            "status_code": response.status_code,
            "body_base64": base64.b64encode(response.body).decode("ascii"),
            "effective_url": response.effective_url,
            "content_type": response.content_type,
            "content_encoding": response.content_encoding,
            "compiled_core_lock_sha256": COMPILED_CORE_LOCK_SHA256,
        }
    except Exception as error:
        code = type(error).__name__.upper()
        raise SafeLambdaFailure(
            f"GUARDIAN_PROVIDER_PROXY_FAIL_CLOSED:{code}"
        ) from None


def observe_proxy_handler(event: Any, context: Any) -> dict[str, Any]:
    return _provider_proxy_handler(
        event,
        context,
        capability="observe_proxy",
        allowed_operations=frozenset({"GUARD", "LIST", "GET"}),
    )


def create_proxy_handler(event: Any, context: Any) -> dict[str, Any]:
    return _provider_proxy_handler(
        event,
        context,
        capability="create_proxy",
        allowed_operations=frozenset({"GUARD", "CREATE"}),
    )


def stop_proxy_handler(event: Any, context: Any) -> dict[str, Any]:
    return _provider_proxy_handler(
        event,
        context,
        capability="stop_proxy",
        allowed_operations=frozenset({"GUARD", "STOP"}),
    )


@dataclass
class RuntimePorts:
    store: guardian.ConditionalStore
    signer: guardian.ReceiptSigner
    clock: guardian.Clock
    secret_guard: guardian.SecretGuard
    transport: guardian.ProviderTransport

    def core(self) -> guardian.AwsProductionGuardianCore:
        return guardian.AwsProductionGuardianCore(
            store=self.store,
            signer=self.signer,
            clock=self.clock,
            secret_guard=self.secret_guard,
            transport=self.transport,
        )


def _key_from(value: Any) -> guardian.AuthorizationKey:
    if not isinstance(value, Mapping) or set(value) != {
        "issuer",
        "provider_account_id",
        "authorization_id",
    }:
        raise AdapterError("AUTHORIZATION_KEY_SCHEMA_INVALID")
    try:
        return guardian.AuthorizationKey(
            issuer=value["issuer"],
            provider_account_id=value["provider_account_id"],
            authorization_id=value["authorization_id"],
        )
    except (TypeError, KeyError) as error:
        raise AdapterError("AUTHORIZATION_KEY_INVALID") from error


def _spec_from(value: Any) -> guardian.AuthorizationSpec:
    if not isinstance(value, Mapping):
        raise AdapterError("AUTHORIZATION_SPEC_NOT_OBJECT")
    expected = {field.name for field in fields(guardian.AuthorizationSpec)}
    if set(value) != expected:
        raise AdapterError("AUTHORIZATION_SPEC_SCHEMA_INVALID")
    admitted = dict(value)
    admitted["key"] = _key_from(admitted["key"])
    protected = admitted.get("protected_pod_ids")
    if not isinstance(protected, list):
        raise AdapterError("AUTHORIZATION_PROTECTED_IDS_INVALID")
    admitted["protected_pod_ids"] = tuple(protected)
    try:
        spec = guardian.AuthorizationSpec(**admitted)
    except (TypeError, ValueError) as error:
        raise AdapterError("AUTHORIZATION_SPEC_INVALID") from error
    stop_at = guardian.parse_utc(spec.stop_dispatch_at_utc)
    hard_deadline = guardian.parse_utc(spec.hard_stop_deadline_utc)
    if (hard_deadline - stop_at).total_seconds() < LIVE_STOP_LEAD_SECONDS:
        raise AdapterError("AUTHORIZATION_STOP_LEAD_BELOW_LIVE_MINIMUM")
    return spec


def _token_from(value: Any, key: guardian.AuthorizationKey) -> guardian.ExecutionToken:
    if not isinstance(value, Mapping) or set(value) != {
        "execution_arn",
        "fence",
        "heartbeat_sequence",
    }:
        raise AdapterError("EXECUTION_TOKEN_SCHEMA_INVALID")
    try:
        return guardian.ExecutionToken(
            key=key,
            execution_arn=value["execution_arn"],
            fence=value["fence"],
            heartbeat_sequence=value["heartbeat_sequence"],
        )
    except (TypeError, KeyError) as error:
        raise AdapterError("EXECUTION_TOKEN_INVALID") from error


def _reservation_from(
    value: Any, key: guardian.AuthorizationKey
) -> guardian.CreateReservation:
    if not isinstance(value, Mapping) or set(value) != {
        "reservation_id",
        "request_sha256",
    }:
        raise AdapterError("CREATE_RESERVATION_SCHEMA_INVALID")
    try:
        return guardian.CreateReservation(
            key=key,
            reservation_id=value["reservation_id"],
            request_sha256=value["request_sha256"],
        )
    except (TypeError, KeyError) as error:
        raise AdapterError("CREATE_RESERVATION_INVALID") from error


def _event_envelope(event: Any) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        raise AdapterError("EVENT_NOT_OBJECT")
    candidate = event.get("envelope", event)
    if not isinstance(candidate, Mapping):
        raise AdapterError("ENVELOPE_NOT_OBJECT")
    if candidate.get("schema_version") != EXECUTION_SCHEMA:
        raise AdapterError("EXECUTION_SCHEMA_MISMATCH")
    allowed = {
        "schema_version",
        "deployment_binding_sha256",
        "authorization_key",
        "exact_create_request_base64",
        "token",
        "reservation",
        "next_action",
        "wait_seconds",
        "last_result",
        "compiled_core_lock_sha256",
        "last_provider_operation",
        "post_deadline_stop_attempted",
        "trusted_time_unavailable",
    }
    if not set(candidate) <= allowed:
        raise AdapterError("EXECUTION_ENVELOPE_HAS_UNKNOWN_FIELDS")
    value = {key: candidate[key] for key in allowed if key in candidate}
    binding = value.get("deployment_binding_sha256")
    if not isinstance(binding, str) or not _SHA256.fullmatch(binding):
        raise AdapterError("EXECUTION_BINDING_INVALID")
    _key_from(value.get("authorization_key"))
    _strict_b64(
        value.get("exact_create_request_base64"), label="EXACT_CREATE_REQUEST"
    )
    return value


def _with_token(envelope: MutableMapping[str, Any], token: guardian.ExecutionToken) -> None:
    envelope["token"] = {
        "execution_arn": token.execution_arn,
        "fence": token.fence,
        "heartbeat_sequence": token.heartbeat_sequence,
    }


def _sanitize_result(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, guardian.CreateOutcome):
        return asdict(value)
    if isinstance(value, Mapping):
        # Signed receipts and provider hashes contain no credential by contract.
        return json.loads(_canonical(dict(value)))
    raise AdapterError("ACTION_RESULT_TYPE_INVALID")


def _inspect_next(
    record: Mapping[str, Any],
    token: guardian.ExecutionToken,
    now: datetime,
    *,
    post_deadline_stop_attempted: bool = False,
) -> tuple[str, int]:
    if (
        record.get("owner_execution_arn") != token.execution_arn
        or record.get("owner_fence") != token.fence
    ):
        raise guardian.StaleFence("inspection ownership fence is stale")
    lease = guardian.parse_utc(str(record.get("owner_lease_expires_at_utc")))
    if now >= lease:
        raise guardian.StaleFence("inspection ownership lease expired")
    state = record.get("state")
    if state in TERMINAL_STATES:
        return "DONE", 0
    spec = record.get("authorization_spec")
    if not isinstance(spec, Mapping):
        raise AdapterError("LEDGER_AUTHORIZATION_SPEC_INVALID")
    stop_at = guardian.parse_utc(str(spec.get("stop_dispatch_at_utc")))
    window_end = guardian.parse_utc(str(spec.get("creation_window_end_utc")))
    proof_deadline = guardian.parse_utc(str(spec.get("terminal_proof_deadline_utc")))
    if (
        state in {"CLAIMED", "ARMED", "CREATE_RESERVED"}
        and record.get("create_dispatch_count") == 0
        and now > window_end
    ):
        return "FINALIZE_NO_CREATE_SAFE_LOSS", 0
    if state == "CLAIMED":
        return "ARM", 0
    if state == "ARMED":
        start = guardian.parse_utc(str(spec.get("creation_window_start_utc")))
        return ("RESERVE", 0) if now >= start else ("WAIT", 1)
    if state == "CREATE_RESERVED":
        return "DISPATCH", 0
    if state in {"CREATE_DISPATCHED_UNKNOWN", "CREATE_AMBIGUOUS"}:
        return (
            ("FINALIZE_UNRESOLVED", 0)
            if now >= proof_deadline
            else ("RECONCILE", 1)
        )
    if state == "TARGET_BOUND":
        admission = record.get("launch_admission_status")
        if now >= stop_at or admission == "INELIGIBLE_CREATE_EVIDENCE":
            return "STOP", 0
        if admission == "PENDING_EXACT_GET":
            return "ADMIT", 0
        if admission != "ADMITTED" or record.get("launch_admitted") is not True:
            return "STOP", 0
        return "OBSERVE", 1
    if state == "STOPPING":
        if now >= proof_deadline:
            return (
                ("FINALIZE_CONTAINMENT_FAILURE", 0)
                if post_deadline_stop_attempted
                else ("STOP", 0)
            )
        attempts = int(record.get("stop_attempt_count", 0))
        if record.get("last_exact_id_get_after_stop_attempt_count") != attempts:
            return "OBSERVE", 1
        return "STOP", 0
    if state == "EMERGENCY_CONTAINMENT_REQUIRED":
        return "STOP", 0
    raise AdapterError("LEDGER_STATE_HAS_NO_ORCHESTRATION_ROUTE")


def _apply_recovered_time_uncertainty(
    envelope: Mapping[str, Any],
    record: Mapping[str, Any],
    clock: guardian.Clock,
) -> None:
    """Fail a recovered possible-CREATE execution toward containment.

    The recovery supervisor is the only producer of
    ``trusted_time_unavailable`` because the public starter schema rejects the
    field.  Each Lambda task re-derives the conservative floor from the ledger
    so the flag cannot smuggle caller-controlled time into the core.
    """

    if envelope.get("trusted_time_unavailable") is not True:
        return
    if not isinstance(clock, ContainmentClock):
        raise AdapterError("RECOVERED_CONTAINMENT_CLOCK_REQUIRED")
    state = record.get("state")
    possible_create = (
        state in guardian.CONTAINMENT_RECOVERY_STATES
        or state in {"TERMINAL_PROVEN", "UNRESOLVED_TERMINAL_FAILURE"}
    )
    if not possible_create or record.get("create_dispatch_count") != 1:
        raise AdapterError("RECOVERED_TIME_UNCERTAINTY_STATE_INVALID")
    spec = record.get("authorization_spec")
    if not isinstance(spec, Mapping):
        raise AdapterError("LEDGER_AUTHORIZATION_SPEC_INVALID")
    clock.force_conservative_floor(
        guardian.parse_utc(str(spec.get("stop_dispatch_at_utc")))
    )


def execute_operation(
    operation: str,
    event: Mapping[str, Any],
    ports: RuntimePorts,
) -> dict[str, Any]:
    """Execute one bounded core transition and return a sanitized envelope."""

    envelope = _event_envelope(event)
    key = _key_from(envelope["authorization_key"])
    request = _strict_b64(
        envelope["exact_create_request_base64"], label="EXACT_CREATE_REQUEST"
    )
    engine = ports.core()
    result: Any = None
    if operation == "register":
        spec = _spec_from(event.get("authorization_spec"))
        if spec.key != key:
            raise AdapterError("REGISTRATION_KEY_MISMATCH")
        result = engine.register_authorization(
            spec, exact_create_request_bytes=request
        )
    elif operation == "claim":
        execution_arn = event.get("execution_arn")
        registered = engine.read_record(key)
        _apply_recovered_time_uncertainty(envelope, registered, ports.clock)
        spec_value = registered.get("authorization_spec")
        expected_request_sha = (
            spec_value.get("exact_create_request_sha256")
            if isinstance(spec_value, Mapping)
            else None
        )
        actual_request_sha = _sha256(request)
        if (
            not isinstance(expected_request_sha, str)
            or not _SHA256.fullmatch(expected_request_sha)
            or not hmac.compare_digest(expected_request_sha, actual_request_sha)
        ):
            raise AdapterError("CLAIM_EXACT_REQUEST_HASH_MISMATCH")
        claim_kwargs: dict[str, Any] = {
            "execution_arn": execution_arn,
            "lease_seconds": 180,
        }
        if (
            registered.get("state") == "AUTHORIZED"
            and registered.get("authorization_consumed") is False
        ):
            claim_kwargs.update(
                {
                    "exact_create_request_bytes": request,
                    "expected_authorization_spec_sha256": str(
                        registered.get("authorization_spec_sha256")
                    ),
                }
            )
        token = engine.claim_execution(key, **claim_kwargs)
        _with_token(envelope, token)
    else:
        token = _token_from(envelope.get("token"), key)
        if envelope.get("trusted_time_unavailable") is True:
            _apply_recovered_time_uncertainty(
                envelope, engine.read_record(key), ports.clock
            )
        if operation == "heartbeat":
            token = engine.heartbeat(
                token,
                expected_sequence=token.heartbeat_sequence,
                lease_seconds=180,
            )
            _with_token(envelope, token)
        elif operation == "inspect":
            record = engine.read_record(key)
            inspected_now = ports.clock.now()
            action, wait_seconds = _inspect_next(
                record,
                token,
                inspected_now,
                post_deadline_stop_attempted=(
                    envelope.get("post_deadline_stop_attempted") is True
                ),
            )
            if (
                isinstance(ports.clock, ContainmentClock)
                and ports.clock.time_uncertain
                and record.get("state")
                in {"TARGET_BOUND", "STOPPING", "EMERGENCY_CONTAINMENT_REQUIRED"}
            ):
                action, wait_seconds = "STOP", 0
                envelope["trusted_time_unavailable"] = True
            previous_provider_operation = envelope.pop(
                "last_provider_operation", None
            )
            if (
                (previous_provider_operation == "admit" and action == "OBSERVE")
                or previous_provider_operation == action.lower()
                and action in {"RECONCILE", "OBSERVE", "STOP"}
                or previous_provider_operation == "stop"
                and action in {"OBSERVE", "STOP"}
            ):
                action, wait_seconds = "WAIT", 1
            envelope["next_action"] = action
            envelope["wait_seconds"] = wait_seconds
            if record.get("state") == "CREATE_RESERVED":
                envelope["reservation"] = {
                    "reservation_id": record.get("create_reservation_id"),
                    "request_sha256": record.get("create_reserved_request_sha256"),
                }
        elif operation == "arm":
            result = engine.arm_precreate(
                token, exact_create_request_bytes=request
            )
        elif operation == "reserve":
            reservation = engine.reserve_create(
                token, exact_create_request_bytes=request
            )
            envelope["reservation"] = {
                "reservation_id": reservation.reservation_id,
                "request_sha256": reservation.request_sha256,
            }
        elif operation == "dispatch":
            reservation = _reservation_from(envelope.get("reservation"), key)
            pre_dispatch = engine.read_record(key)
            spec_value = pre_dispatch.get("authorization_spec")
            if not isinstance(spec_value, Mapping):
                raise AdapterError("CREATE_CAPABILITY_SPEC_ABSENT")
            existing_lease = guardian.parse_utc(
                str(pre_dispatch.get("owner_lease_expires_at_utc"))
            )
            containment_cap = guardian.parse_utc(
                str(spec_value.get("stop_dispatch_at_utc"))
            ) + timedelta(seconds=guardian.MAX_CONTAINMENT_OWNER_LEASE_SECONDS)
            marker_lease = guardian.iso_utc(min(existing_lease, containment_cap))
            not_after = str(spec_value.get("creation_window_end_utc"))
            capability_binder = getattr(
                ports.transport, "bind_create_capability", None
            )
            if isinstance(ports.transport, LambdaProviderBoundary):
                if not callable(capability_binder):
                    raise AdapterError("CREATE_CAPABILITY_BINDER_ABSENT")
                capability_binder(
                    key=key,
                    token=token,
                    reservation=reservation,
                    owner_lease_expires_at_utc=marker_lease,
                    not_after_utc=not_after,
                )
            result = engine.dispatch_create(
                token,
                reservation,
                exact_create_request_bytes=request,
            )
        elif operation == "admit":
            result = engine.verify_post_bind_launch_admission(token)
        elif operation == "reconcile":
            result = engine.reconcile_ambiguous_create(token)
        elif operation == "observe":
            result = engine.observe_terminal(token)
        elif operation == "stop":
            before_stop = engine.read_record(key)
            time_uncertain = False
            if isinstance(ports.clock, ContainmentClock):
                disable_observation = getattr(
                    ports.transport, "disable_post_stop_observation", None
                )
                if callable(disable_observation):
                    ports.clock.on_uncertainty(disable_observation)
                bind_clock = getattr(ports.transport, "bind_containment_clock", None)
                if callable(bind_clock):
                    bind_clock(ports.clock)
                time_uncertain = not ports.clock.trusted_now_available()
            if time_uncertain:
                disable_observation = getattr(
                    ports.transport, "disable_post_stop_observation", None
                )
                if callable(disable_observation):
                    disable_observation()
                envelope["trusted_time_unavailable"] = True
            try:
                result = engine.request_stop(token)
            finally:
                final_time_uncertain = time_uncertain or bool(
                    isinstance(ports.clock, ContainmentClock)
                    and ports.clock.time_uncertain
                )
                if final_time_uncertain:
                    marker = getattr(
                        ports.store, "mark_containment_time_uncertain", None
                    )
                    if not callable(marker):
                        raise AdapterError("TIME_UNCERTAIN_MARKER_UNAVAILABLE")
                    marker(key.pk, key.sk)
            spec_value = before_stop.get("authorization_spec")
            if isinstance(spec_value, Mapping) and ports.clock.now() >= guardian.parse_utc(
                str(spec_value.get("terminal_proof_deadline_utc"))
            ):
                envelope["post_deadline_stop_attempted"] = True
        elif operation == "finalize_no_create_safe_loss":
            result = engine.finalize_no_create_safe_loss(token)
        elif operation == "finalize_unresolved":
            result = engine.finalize_unresolved(token)
        elif operation == "finalize_containment_failure":
            result = engine.finalize_containment_failure(token)
        else:
            raise AdapterError("OPERATION_NOT_ALLOWLISTED")
    envelope["last_result"] = _sanitize_result(result)
    if operation in {"admit", "reconcile", "observe", "stop"}:
        envelope["last_provider_operation"] = operation
    envelope["compiled_core_lock_sha256"] = COMPILED_CORE_LOCK_SHA256
    return envelope


_PORTS_FACTORY: Callable[[str, Mapping[str, str]], RuntimePorts] | None = None

_ACTIVATION_DOCUMENTS_FACTORY: Callable[
    [Mapping[str, str]], tuple[bytes, bytes]
] | None = None
_ACTIVATION_DOCUMENT_VERIFIER: Callable[
    [Mapping[str, str], str, str, Any], None
] | None = None


def _binding_canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _read_s3_version(
    client: Any,
    *,
    bucket: str,
    key: str,
    version: str,
    expected_sha256: str,
    label: str,
) -> bytes:
    if not all(isinstance(value, str) and value for value in (bucket, key, version)):
        raise ActivationError(f"{label}_IDENTITY_ABSENT")
    if not _SHA256.fullmatch(expected_sha256):
        raise ActivationError(f"{label}_HASH_INVALID")
    try:
        response = client.get_object(
            Bucket=bucket,
            Key=key,
            VersionId=version,
            ChecksumMode="ENABLED",
        )
        if response.get("VersionId") != version:
            raise ActivationError(f"{label}_VERSION_MISMATCH")
        stream = response.get("Body")
        if not hasattr(stream, "read"):
            raise ActivationError(f"{label}_BODY_ABSENT")
        raw = stream.read(MAX_ACTIVATION_DOCUMENT_BYTES + 1)
    except ActivationError:
        raise
    except Exception:
        raise ActivationError(f"{label}_READ_FAILED") from None
    if not isinstance(raw, bytes) or len(raw) > MAX_ACTIVATION_DOCUMENT_BYTES:
        raise ActivationError(f"{label}_SIZE_INVALID")
    if not hmac.compare_digest(_sha256(raw), expected_sha256):
        raise ActivationError(f"{label}_HASH_MISMATCH")
    return raw


def _load_activation_documents(environment: Mapping[str, str]) -> tuple[bytes, bytes]:
    if _ACTIVATION_DOCUMENTS_FACTORY is not None:
        binding, timing = _ACTIVATION_DOCUMENTS_FACTORY(environment)
        if (
            not isinstance(binding, bytes)
            or not isinstance(timing, bytes)
            or _sha256(binding) != environment.get("BINDING_OBJECT_SHA256")
            or _sha256(timing)
            != environment.get("TIMING_VALIDATION_EVIDENCE_SHA256")
        ):
            raise ActivationError("ACTIVATION_DOCUMENT_FACTORY_HASH_MISMATCH")
        return binding, timing
    try:
        import boto3  # type: ignore
        from botocore.config import Config  # type: ignore
    except ImportError:
        raise ActivationError("AWS_SDK_UNAVAILABLE") from None
    config = Config(
        connect_timeout=3,
        read_timeout=8,
        retries={"mode": "standard", "total_max_attempts": 3},
        user_agent_extra="cas-runpod-activation-documents/1",
    )
    client = boto3.client("s3", region_name=environment["AWS_REGION"], config=config)
    binding = _read_s3_version(
        client,
        bucket=environment.get("BINDING_OBJECT_BUCKET", ""),
        key=environment.get("BINDING_OBJECT_KEY", ""),
        version=environment.get("BINDING_OBJECT_VERSION", ""),
        expected_sha256=environment.get("BINDING_OBJECT_SHA256", ""),
        label="DEPLOYMENT_BINDING_OBJECT",
    )
    timing = _read_s3_version(
        client,
        bucket=environment.get("TIMING_EVIDENCE_BUCKET", ""),
        key=environment.get("TIMING_EVIDENCE_KEY", ""),
        version=environment.get("TIMING_EVIDENCE_VERSION", ""),
        expected_sha256=environment.get("TIMING_VALIDATION_EVIDENCE_SHA256", ""),
        label="TIMING_EVIDENCE_OBJECT",
    )
    return binding, timing


def _verify_timing_evidence(
    raw: bytes, binding: Mapping[str, Any], environment: Mapping[str, str]
) -> None:
    parsed = guardian.strict_json(
        raw, "guardian timing evidence", max_bytes=MAX_ACTIVATION_DOCUMENT_BYTES
    )
    if (
        not isinstance(parsed, dict)
        or set(parsed) != _TIMING_EVIDENCE_FIELDS
        or parsed.get("schema_version") != TIMING_EVIDENCE_SCHEMA
        or raw != _binding_canonical(parsed)
    ):
        raise ActivationError("TIMING_EVIDENCE_SCHEMA_INVALID")
    for field, binding_field in (
        ("aws_account_id", "aws_account_id"),
        ("aws_region", "aws_region"),
        ("stack_id", "stack_id"),
        ("core_lock_sha256", "core_lock_sha256"),
        ("runtime_zip_sha256", "runtime_zip_sha256"),
    ):
        if parsed.get(field) != binding.get(binding_field):
            raise ActivationError("TIMING_EVIDENCE_BINDING_MISMATCH")
    observed_acceptance_bounds = (
        ("observed_recovery_gap_milliseconds", 180_000),
        ("observed_worker_startup_milliseconds", 8_000),
        ("observed_provider_stop_execution_milliseconds", 8_000),
    )
    if type(parsed.get("measurement_count")) is not int or parsed["measurement_count"] < 1:
        raise ActivationError("TIMING_EVIDENCE_COUNT_INVALID")
    if (
        parsed.get("measurement_kind") != "EMPIRICAL_NON_GUARANTEE"
        or parsed.get("scheduled_recovery_cadence_seconds") != 60
        or parsed.get("recovery_retry_maximum_attempts") != 2
        or parsed.get("recovery_event_maximum_age_seconds") != 60
        or type(parsed.get("tested_consecutive_missed_ticks")) is not int
        or parsed["tested_consecutive_missed_ticks"] < 1
    ):
        raise ActivationError("TIMING_EVIDENCE_RECOVERY_MODEL_MISMATCH")
    for name, maximum in observed_acceptance_bounds:
        value = parsed.get(name)
        if type(value) is not int or not 0 <= value <= maximum:
            raise ActivationError("TIMING_EVIDENCE_BOUND_EXCEEDED")
    if parsed.get("required_stop_lead_seconds") != LIVE_STOP_LEAD_SECONDS:
        raise ActivationError("TIMING_EVIDENCE_STOP_LEAD_MISMATCH")
    guardian.parse_utc(str(parsed.get("measured_at_utc")))
    manifest_hash = parsed.get("source_evidence_manifest_sha256")
    if not isinstance(manifest_hash, str) or not _SHA256.fullmatch(manifest_hash):
        raise ActivationError("TIMING_EVIDENCE_SOURCE_HASH_INVALID")
    if _sha256(raw) != environment.get("TIMING_VALIDATION_EVIDENCE_SHA256"):
        raise ActivationError("TIMING_EVIDENCE_OBJECT_HASH_MISMATCH")


def _expected_provider_transport_binding() -> dict[str, Any]:
    return {
        "host": PROVIDER_HOST,
        "create_endpoint": guardian.CREATE_ENDPOINT,
        "tls_port": PROVIDER_PORT,
        "allowed_provider_operations_by_proxy": {
            "observe_proxy": ["GET", "GUARD", "LIST"],
            "create_proxy": ["CREATE", "GUARD"],
            "stop_proxy": ["GUARD", "STOP"],
        },
        "allowed_proxy_invocation_by_core_lambda": {
            "control": [],
            "observe": ["observe_proxy"],
            "create": ["create_proxy"],
            "stop": ["observe_proxy", "stop_proxy"],
        },
    }


def _expected_activation_contract() -> dict[str, Any]:
    return {
        "activation_mode": "LIVE",
        "recovery_enabled": True,
        "recovery_schedule_state": "ENABLED",
        "local_launcher_provider_post_allowed": False,
        "provider_create_post_limit": 1,
        "timing_evidence_kind": "EMPIRICAL_NON_GUARANTEE",
        "scheduled_recovery_cadence_seconds": 60,
        "recovery_retry_maximum_attempts": 2,
        "recovery_event_maximum_age_seconds": 60,
        "provider_native_hard_ttl_available": False,
        "required_stop_lead_seconds": LIVE_STOP_LEAD_SECONDS,
    }


def _local_binding_source(environment: Mapping[str, str]) -> dict[str, Any]:
    """Rebuild the canonical binding without a containment-path S3 read."""

    account = environment.get("AWS_ACCOUNT_ID", "")
    partition = environment.get("AWS_PARTITION", "")
    region = environment.get("AWS_REGION", "")
    stack = environment.get("STACK_NAME", "")
    if (
        not re.fullmatch(r"\d{12}", account)
        or partition != "aws"
        or region != EXPECTED_REGION
        or not isinstance(stack, str)
        or not stack
    ):
        raise ActivationError("LOCAL_BINDING_STACK_SCOPE_INVALID")
    ledger_name = GLOBAL_LEDGER_TABLE_PREFIX + account
    ledger_arn = (
        f"arn:{partition}:dynamodb:{region}:{account}:table/{ledger_name}"
    )
    if environment.get("LEDGER_TABLE_ARN") != ledger_arn:
        raise ActivationError("LOCAL_BINDING_GLOBAL_LEDGER_MISMATCH")
    kms_arn = environment.get("BOUND_KMS_SIGNING_KEY_ARN", "")
    state_machine_arn = environment.get("BOUND_STATE_MACHINE_ARN", "")
    if (
        not kms_arn.startswith(f"arn:{partition}:kms:{region}:{account}:key/")
        or state_machine_arn
        != f"arn:{partition}:states:{region}:{account}:stateMachine:{stack}-guardian"
    ):
        raise ActivationError("LOCAL_BINDING_MANAGED_RESOURCE_MISMATCH")
    lambda_prefix = f"arn:{partition}:lambda:{region}:{account}:function:{stack}-"
    function_arns = {
        "control_function_arn": lambda_prefix + "control",
        "observe_function_arn": lambda_prefix + "observe",
        "create_function_arn": lambda_prefix + "create",
        "stop_function_arn": lambda_prefix + "stop",
        "starter_function_arn": lambda_prefix + "starter",
        "recovery_function_arn": lambda_prefix + "recovery",
        "observe_proxy_function_arn": lambda_prefix + "observe-proxy",
        "create_proxy_function_arn": lambda_prefix + "create-proxy",
        "stop_proxy_function_arn": lambda_prefix + "stop-proxy",
    }
    source = {
        "schema_version": DEPLOYMENT_BINDING_SCHEMA,
        "aws_account_id": account,
        "aws_partition": partition,
        "aws_region": region,
        "stack_id": environment.get("STACK_ID", ""),
        "stack_name": stack,
        "ledger_table_arn": ledger_arn,
        "kms_signing_key_arn": kms_arn,
        "state_machine_arn": state_machine_arn,
        **function_arns,
        "provider_secret_arn": environment.get("PROVIDER_SECRET_ARN", ""),
        "provider_account_id": environment.get("PROVIDER_ACCOUNT_ID", ""),
        "runtime_artifact_bucket": environment.get(
            "RUNTIME_ARTIFACT_BUCKET", ""
        ),
        "runtime_artifact_key": environment.get("RUNTIME_ARTIFACT_KEY", ""),
        "runtime_artifact_version": environment.get(
            "RUNTIME_ARTIFACT_VERSION", ""
        ),
        "runtime_zip_sha256": environment.get("RUNTIME_ZIP_SHA256", ""),
        "core_lock_sha256": environment.get("CORE_LOCK_SHA256", ""),
        "timing_validation_evidence_sha256": environment.get(
            "TIMING_VALIDATION_EVIDENCE_SHA256", ""
        ),
        "timing_evidence_bucket": environment.get("TIMING_EVIDENCE_BUCKET", ""),
        "timing_evidence_key": environment.get("TIMING_EVIDENCE_KEY", ""),
        "timing_evidence_version": environment.get(
            "TIMING_EVIDENCE_VERSION", ""
        ),
        "core_sha256": COMPILED_LOCKED_HASHES.get("core_sha256"),
        "runtime_sha256": COMPILED_LOCKED_HASHES.get("runtime_sha256"),
        "state_machine_sha256": COMPILED_LOCKED_HASHES.get(
            "state_machine_sha256"
        ),
        "template_sha256": COMPILED_LOCKED_HASHES.get("template_sha256"),
        "provider_transport": _expected_provider_transport_binding(),
        "activation_contract": _expected_activation_contract(),
    }
    if set(source) != _BINDING_SOURCE_FIELDS:
        raise ActivationError("LOCAL_BINDING_SOURCE_SCHEMA_INVALID")
    return source


def _verify_local_material_binding(
    environment: Mapping[str, str],
    expected_binding: str,
    capability: str,
    context: Any,
) -> None:
    source = _local_binding_source(environment)
    computed = _sha256(
        DEPLOYMENT_BINDING_DOMAIN + _binding_canonical(source)
    )
    if not hmac.compare_digest(computed, expected_binding):
        raise ActivationError("LOCAL_MATERIAL_BINDING_DIGEST_MISMATCH")
    capability_fields = {
        "control": "control_function_arn",
        "observe": "observe_function_arn",
        "create": "create_function_arn",
        "stop": "stop_function_arn",
        "starter": "starter_function_arn",
        "recovery": "recovery_function_arn",
        "containment_observe": "observe_function_arn",
        "observe_proxy": "observe_proxy_function_arn",
        "create_proxy": "create_proxy_function_arn",
        "stop_proxy": "stop_proxy_function_arn",
    }
    field = capability_fields.get(capability)
    if (
        field is None
        or getattr(context, "invoked_function_arn", None) != source[field]
    ):
        raise ActivationError("LOCAL_BINDING_FUNCTION_IDENTITY_MISMATCH")
    ledger_name = source["ledger_table_arn"].rsplit("/", 1)[-1]
    if (
        "LEDGER_TABLE_NAME" in environment
        and environment.get("LEDGER_TABLE_NAME") != ledger_name
    ):
        raise ActivationError("LOCAL_BINDING_LEDGER_TARGET_MISMATCH")
    for operational, bound in (
        ("KMS_SIGNING_KEY_ARN", "kms_signing_key_arn"),
        ("STATE_MACHINE_ARN", "state_machine_arn"),
    ):
        if operational in environment and environment.get(operational) != source[bound]:
            raise ActivationError("LOCAL_BINDING_OPERATIONAL_TARGET_MISMATCH")
    expected_proxy = {
        "observe": source["observe_proxy_function_arn"],
        "containment_observe": source["observe_proxy_function_arn"],
        "create": source["create_proxy_function_arn"],
    }.get(capability)
    if expected_proxy is not None and environment.get(
        "PROVIDER_PROXY_FUNCTION_ARN"
    ) != expected_proxy:
        raise ActivationError("LOCAL_BINDING_PROXY_TARGET_MISMATCH")
    if capability == "stop" and (
        environment.get("STOP_PROXY_FUNCTION_ARN")
        != source["stop_proxy_function_arn"]
        or environment.get("OBSERVE_PROXY_FUNCTION_ARN")
        != source["observe_proxy_function_arn"]
    ):
        raise ActivationError("LOCAL_BINDING_PROXY_TARGET_MISMATCH")


def _verify_activation_documents(
    environment: Mapping[str, str],
    expected_binding: str,
    capability: str,
    context: Any,
) -> None:
    binding_raw, timing_raw = _load_activation_documents(environment)
    parsed = guardian.strict_json(
        binding_raw,
        "guardian deployment binding",
        max_bytes=MAX_ACTIVATION_DOCUMENT_BYTES,
    )
    if not isinstance(parsed, dict) or set(parsed) != (
        _BINDING_SOURCE_FIELDS
        | {"deployment_binding_sha256", "binding_document_sha256"}
    ):
        raise ActivationError("DEPLOYMENT_BINDING_DOCUMENT_SCHEMA_INVALID")
    if parsed.get("schema_version") != DEPLOYMENT_BINDING_SCHEMA:
        raise ActivationError("DEPLOYMENT_BINDING_DOCUMENT_SCHEMA_INVALID")
    if binding_raw != _binding_canonical(parsed):
        raise ActivationError("DEPLOYMENT_BINDING_DOCUMENT_NONCANONICAL")
    without_document_hash = dict(parsed)
    document_hash = without_document_hash.pop("binding_document_sha256", None)
    if (
        not isinstance(document_hash, str)
        or not hmac.compare_digest(
            _sha256(_binding_canonical(without_document_hash)), document_hash
        )
    ):
        raise ActivationError("DEPLOYMENT_BINDING_DOCUMENT_HASH_MISMATCH")
    source = dict(without_document_hash)
    claimed_binding = source.pop("deployment_binding_sha256", None)
    recomputed_binding = _sha256(
        DEPLOYMENT_BINDING_DOMAIN + _binding_canonical(source)
    )
    if (
        not isinstance(claimed_binding, str)
        or not hmac.compare_digest(recomputed_binding, claimed_binding)
        or not hmac.compare_digest(claimed_binding, expected_binding)
    ):
        raise ActivationError("DEPLOYMENT_BINDING_DIGEST_MISMATCH")
    if source != _local_binding_source(environment):
        raise ActivationError("DEPLOYMENT_BINDING_ENVIRONMENT_MISMATCH")
    capability_fields = {
        "control": "control_function_arn",
        "observe": "observe_function_arn",
        "create": "create_function_arn",
        "stop": "stop_function_arn",
        "starter": "starter_function_arn",
        "recovery": "recovery_function_arn",
        "observe_proxy": "observe_proxy_function_arn",
        "create_proxy": "create_proxy_function_arn",
        "stop_proxy": "stop_proxy_function_arn",
    }
    arn_field = capability_fields.get(capability)
    invoked_arn = getattr(context, "invoked_function_arn", None)
    if arn_field is None or not isinstance(invoked_arn, str) or parsed.get(arn_field) != invoked_arn:
        raise ActivationError("DEPLOYMENT_BINDING_FUNCTION_IDENTITY_MISMATCH")
    arn_fields = [name for name in parsed if name.endswith("_arn")] + ["stack_id"]
    for name in arn_fields:
        value = parsed.get(name)
        if (
            not isinstance(value, str)
            or f":{environment['AWS_REGION']}:" not in value
            or f":{environment['AWS_ACCOUNT_ID']}:" not in value
        ):
            raise ActivationError("DEPLOYMENT_BINDING_ARN_SCOPE_MISMATCH")
    expected_transport = _expected_provider_transport_binding()
    if parsed.get("provider_transport") != expected_transport:
        raise ActivationError("DEPLOYMENT_BINDING_TRANSPORT_MISMATCH")
    contract = parsed.get("activation_contract")
    if not isinstance(contract, dict) or contract != _expected_activation_contract():
        raise ActivationError("DEPLOYMENT_BINDING_ACTIVATION_CONTRACT_MISMATCH")
    _verify_timing_evidence(timing_raw, parsed, environment)


def _activation_gate(
    environment: Mapping[str, str],
    binding: str,
    *,
    capability: str,
    context: Any,
) -> None:
    if environment.get("ACTIVATION_MODE") != "LIVE":
        raise ActivationError("DEPLOYMENT_IS_INERT")
    expected_region = environment.get("EXPECTED_AWS_REGION")
    if expected_region != EXPECTED_REGION or environment.get("AWS_REGION") != expected_region:
        raise ActivationError("AWS_REGION_BINDING_MISMATCH")
    frozen = environment.get("DEPLOYMENT_BINDING_SHA256", "")
    if not _SHA256.fullmatch(frozen) or frozen == "0" * 64:
        raise ActivationError("DEPLOYMENT_BINDING_UNBOUND")
    if not hmac.compare_digest(frozen, binding):
        raise ActivationError("DEPLOYMENT_BINDING_MISMATCH")
    provider_account = environment.get("PROVIDER_ACCOUNT_ID", "")
    if (
        not provider_account
        or provider_account == "UNBOUND"
        or len(provider_account) > 128
    ):
        raise ActivationError("PROVIDER_ACCOUNT_UNBOUND")
    environment_lock = environment.get("CORE_LOCK_SHA256", "")
    if (
        not _SHA256.fullmatch(environment_lock)
        or environment_lock == "0" * 64
        or not isinstance(COMPILED_CORE_LOCK_SHA256, str)
        or not hmac.compare_digest(environment_lock, COMPILED_CORE_LOCK_SHA256)
    ):
        raise ActivationError("COMPILED_CORE_LOCK_MISMATCH")
    timing_evidence = environment.get("TIMING_VALIDATION_EVIDENCE_SHA256", "")
    if not _SHA256.fullmatch(timing_evidence) or timing_evidence == "0" * 64:
        raise ActivationError("TIMING_VALIDATION_EVIDENCE_ABSENT")
    local_containment_capabilities = {
        "control",
        "stop",
        "recovery",
        "containment_observe",
        "observe_proxy",
        "stop_proxy",
    }
    if _ACTIVATION_DOCUMENT_VERIFIER is not None:
        _ACTIVATION_DOCUMENT_VERIFIER(environment, binding, capability, context)
    else:
        _verify_local_material_binding(
            environment, binding, capability, context
        )
        if capability not in local_containment_capabilities:
            _verify_activation_documents(environment, binding, capability, context)


def _boto3_ports(capability: str, environment: Mapping[str, str]) -> RuntimePorts:
    try:
        import boto3  # type: ignore
        from botocore.config import Config  # type: ignore
    except ImportError:
        raise ActivationError("AWS_SDK_UNAVAILABLE") from None
    aws_config = Config(
        connect_timeout=3,
        read_timeout=10,
        retries={"mode": "standard", "total_max_attempts": 3},
        user_agent_extra="cas-runpod-guardian/1",
    )
    region = environment["AWS_REGION"]
    session = boto3.session.Session(region_name=region)
    store = DynamoDbConditionalStore(
        session.client("dynamodb", config=aws_config),
        environment.get("LEDGER_TABLE_NAME", ""),
    )
    signer = AwsKmsReceiptSigner(
        session.client("kms", config=aws_config),
        environment.get("KMS_SIGNING_KEY_ARN", ""),
    )
    trusted_clock = AwsTrustedClock(session.client("sts", config=aws_config))
    clock: guardian.Clock = (
        ContainmentClock(trusted_clock)
        if capability in {"control", "stop", "containment_observe"}
        else trusted_clock
    )
    methods = {
        "control": frozenset(),
        "observe": frozenset({"GUARD", "LIST", "GET"}),
        "containment_observe": frozenset({"GUARD", "LIST", "GET"}),
        "create": frozenset({"GUARD", "CREATE"}),
        "stop": frozenset({"GUARD", "STOP"}),
    }
    if capability not in methods:
        raise ActivationError("LAMBDA_CAPABILITY_INVALID")
    if capability == "control":
        boundary: Any = DenyProviderTransport()
    elif capability == "stop":
        proxy_config = Config(
            connect_timeout=3,
            read_timeout=10,
            retries={"mode": "standard", "total_max_attempts": 1},
            user_agent_extra="cas-runpod-core-to-split-stop-proxy/1",
        )
        lambda_client = session.client("lambda", config=proxy_config)
        stop_boundary = LambdaProviderBoundary(
            lambda_client,
            function_arn=environment.get("STOP_PROXY_FUNCTION_ARN", ""),
            deployment_binding_sha256=environment.get(
                "DEPLOYMENT_BINDING_SHA256", ""
            ),
            provider_account_id=environment.get("PROVIDER_ACCOUNT_ID", ""),
            allowed_operations=frozenset({"GUARD", "STOP"}),
        )
        observe_boundary = LambdaProviderBoundary(
            lambda_client,
            function_arn=environment.get("OBSERVE_PROXY_FUNCTION_ARN", ""),
            deployment_binding_sha256=environment.get(
                "DEPLOYMENT_BINDING_SHA256", ""
            ),
            provider_account_id=environment.get("PROVIDER_ACCOUNT_ID", ""),
            allowed_operations=frozenset({"GUARD", "GET"}),
        )
        boundary = SplitStopProviderBoundary(
            stop_boundary,
            observe_boundary,
            containment_clock=(clock if isinstance(clock, ContainmentClock) else None),
        )
    else:
        proxy_config = Config(
            connect_timeout=3,
            read_timeout=15,
            retries={"mode": "standard", "total_max_attempts": 1},
            user_agent_extra="cas-runpod-core-to-proxy/1",
        )
        boundary = LambdaProviderBoundary(
            session.client("lambda", config=proxy_config),
            function_arn=environment.get("PROVIDER_PROXY_FUNCTION_ARN", ""),
            deployment_binding_sha256=environment.get(
                "DEPLOYMENT_BINDING_SHA256", ""
            ),
            provider_account_id=environment.get("PROVIDER_ACCOUNT_ID", ""),
            allowed_operations=methods[capability],
        )
    return RuntimePorts(store, signer, clock, boundary, boundary)


def _handler(
    event: Any,
    context: Any,
    *,
    capability: str,
    allowed_operations: frozenset[str],
) -> dict[str, Any]:
    try:
        if not isinstance(event, Mapping):
            raise AdapterError("EVENT_NOT_OBJECT")
        operation = event.get("operation")
        if operation not in allowed_operations:
            raise AdapterError("HANDLER_OPERATION_NOT_ALLOWED")
        envelope = _event_envelope(event)
        environment = dict(os.environ)
        _activation_gate(
            environment,
            envelope["deployment_binding_sha256"],
            capability=capability,
            context=context,
        )
        factory = _PORTS_FACTORY or _boto3_ports
        ports = factory(capability, environment)
        return execute_operation(str(operation), event, ports)
    except Exception as error:
        # Only the class is surfaced.  Provider, event, and secret text are
        # never copied to logs or Step Functions execution output.
        code = type(error).__name__.upper()
        raise SafeLambdaFailure(f"GUARDIAN_FAIL_CLOSED:{code}") from None


def control_handler(event: Any, context: Any) -> dict[str, Any]:
    return _handler(
        event,
        context,
        capability="control",
        allowed_operations=frozenset(
            {
                "claim",
                "heartbeat",
                "inspect",
                "finalize_unresolved",
                "finalize_containment_failure",
                "finalize_no_create_safe_loss",
            }
        ),
    )


def observe_handler(event: Any, context: Any) -> dict[str, Any]:
    operation = event.get("operation") if isinstance(event, Mapping) else None
    if operation in {"reconcile", "observe"}:
        return _handler(
            event,
            context,
            capability="containment_observe",
            allowed_operations=frozenset({"reconcile", "observe"}),
        )
    return _handler(
        event,
        context,
        capability="observe",
        allowed_operations=frozenset(
            {"register", "arm", "admit"}
        ),
    )


def create_handler(event: Any, context: Any) -> dict[str, Any]:
    return _handler(
        event,
        context,
        capability="create",
        allowed_operations=frozenset({"reserve", "dispatch"}),
    )


def stop_handler(event: Any, context: Any) -> dict[str, Any]:
    return _handler(
        event,
        context,
        capability="stop",
        allowed_operations=frozenset({"stop"}),
    )


def _starter_input(body: Mapping[str, Any], binding: str) -> dict[str, Any]:
    if set(body) != {
        "schema_version",
        "deployment_binding_sha256",
        "authorization_key",
        "exact_create_request_base64",
    } or body.get("schema_version") != EXECUTION_SCHEMA:
        raise AdapterError("START_REQUEST_SCHEMA_INVALID")
    envelope = _event_envelope(body)
    if envelope["deployment_binding_sha256"] != binding:
        raise AdapterError("START_REQUEST_BINDING_MISMATCH")
    return envelope


_STARTER_CLIENT_FACTORY: Callable[[], Any] | None = None


def starter_handler(event: Any, context: Any) -> dict[str, Any]:
    """IAM-authenticated HTTP API entry point for a registered authorization."""

    try:
        environment = dict(os.environ)
        if not isinstance(event, Mapping) or not isinstance(event.get("body"), str):
            raise AdapterError("HTTP_START_EVENT_INVALID")
        raw = event["body"].encode("utf-8")
        body = guardian.strict_json(raw, "guardian start request", max_bytes=MAX_EVENT_BYTES)
        if not isinstance(body, dict):
            raise AdapterError("HTTP_START_BODY_NOT_OBJECT")
        binding = body.get("deployment_binding_sha256", "")
        _activation_gate(
            environment, binding, capability="starter", context=context
        )
        execution_input = _starter_input(body, binding)
        key = _key_from(execution_input["authorization_key"])
        name = "primary-" + key.digest[:48]
        if not _EXECUTION_NAME.fullmatch(name):
            raise AdapterError("STEP_FUNCTIONS_EXECUTION_NAME_INVALID")
        if _STARTER_CLIENT_FACTORY is not None:
            client = _STARTER_CLIENT_FACTORY()
        else:
            import boto3  # type: ignore

            client = boto3.client("stepfunctions", region_name=environment["AWS_REGION"])
        response = client.start_execution(
            stateMachineArn=environment["STATE_MACHINE_ARN"],
            name=name,
            input=_canonical(execution_input).decode("utf-8"),
        )
        execution_arn = response.get("executionArn")
        if not isinstance(execution_arn, str):
            raise AdapterError("STEP_FUNCTIONS_START_RESPONSE_INVALID")
        return {
            "statusCode": 202,
            "headers": {"content-type": "application/json"},
            "body": json.dumps(
                {
                    "status": "ACCEPTED",
                    "execution_arn": execution_arn,
                    "compiled_core_lock_sha256": COMPILED_CORE_LOCK_SHA256,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
        }
    except Exception as error:
        code = type(error).__name__.upper()
        return {
            "statusCode": 503,
            "headers": {"content-type": "application/json"},
            "body": json.dumps(
                {"status": "FAIL_CLOSED", "code": code},
                sort_keys=True,
                separators=(",", ":"),
            ),
        }


_RECOVERY_CLIENTS_FACTORY: Callable[[], tuple[Any, Any, Any, Any]] | None = None


def recovery_handler(event: Any, context: Any) -> dict[str, Any]:
    """O(1) stale-lease successor launcher for the single active canary.

    Registration atomically owns one global pointer.  A separately conditioned
    delete releases it only after a strong read resolves signed terminal/safe-
    loss proof.  Recovery uses two strongly consistent reads and never depends
    on a scan, GSI visibility, or backlog.
    """

    try:
        environment = dict(os.environ)
        binding = environment.get("DEPLOYMENT_BINDING_SHA256", "")
        _activation_gate(
            environment, binding, capability="recovery", context=context
        )
        if environment.get("RECOVERY_ENABLED") != "TRUE":
            raise ActivationError("RECOVERY_SUPERVISOR_DISABLED")
        event_nonce = _recovery_event_nonce(event, environment)
        if _RECOVERY_CLIENTS_FACTORY is not None:
            ddb, sfn, clock, signer = _RECOVERY_CLIENTS_FACTORY()
        else:
            import boto3  # type: ignore
            from botocore.config import Config  # type: ignore

            config = Config(
                connect_timeout=3,
                read_timeout=8,
                retries={"mode": "standard", "total_max_attempts": 2},
                user_agent_extra="cas-runpod-recovery/1",
            )
            region = environment["AWS_REGION"]
            ddb = boto3.client("dynamodb", region_name=region, config=config)
            sfn = boto3.client("stepfunctions", region_name=region, config=config)
            clock = ContainmentClock(
                AwsTrustedClock(boto3.client("sts", region_name=region, config=config))
            )
            signer = AwsKmsReceiptSigner(
                boto3.client("kms", region_name=region, config=config),
                environment.get("KMS_SIGNING_KEY_ARN", ""),
            )
        started = 0
        already_exists = 0
        failed = 0
        unclaimed_finalized = 0
        pointer_released = 0
        table_name = environment["LEDGER_TABLE_NAME"]
        store = DynamoDbConditionalStore(ddb, table_name)
        pointer_response = ddb.get_item(
            TableName=table_name,
            Key={
                "pk": {"S": GLOBAL_ACTIVE_PK},
                "sk": {"S": GLOBAL_ACTIVE_SK},
            },
            ConsistentRead=True,
        )
        pointer = pointer_response.get("Item") if isinstance(
            pointer_response, Mapping
        ) else None
        if pointer is not None:
            try:
                if (
                    pointer["pk"]["S"] != GLOBAL_ACTIVE_PK
                    or pointer["sk"]["S"] != GLOBAL_ACTIVE_SK
                    or pointer["item_type"]["S"]
                    != "GLOBAL_SINGLE_ACTIVE_AUTHORIZATION"
                ):
                    raise AdapterError("GLOBAL_ACTIVE_POINTER_IDENTITY_INVALID")
                head_pk = pointer["active_pk"]["S"]
                head_sk = pointer["active_sk"]["S"]
                pointer_key_sha = pointer["authorization_key_sha256"]["S"]
                pointer_spec_sha = pointer["authorization_spec_sha256"]["S"]
            except (KeyError, TypeError):
                raise AdapterError("GLOBAL_ACTIVE_POINTER_MALFORMED") from None
            head_response = ddb.get_item(
                TableName=table_name,
                Key={"pk": {"S": head_pk}, "sk": {"S": head_sk}},
                ConsistentRead=True,
            )
            item = head_response.get("Item") if isinstance(
                head_response, Mapping
            ) else None
            if not isinstance(item, Mapping):
                raise AdapterError("GLOBAL_ACTIVE_HEAD_ABSENT")
            record = DynamoDbConditionalStore.decode_physical(item)
            if record.get("pk") != head_pk or record.get("sk") != head_sk:
                raise AdapterError("GLOBAL_ACTIVE_HEAD_KEY_MISMATCH")
            if (
                record.get("authorization_key_sha256") != pointer_key_sha
                or record.get("authorization_spec_sha256") != pointer_spec_sha
            ):
                raise AdapterError("GLOBAL_ACTIVE_POINTER_GENERATION_MISMATCH")
            if record.get("state") in POINTER_RELEASE_STATES:
                pointer_released = int(
                    store.release_global_active_if_terminal(head_pk, head_sk)
                )
            elif record.get("state") not in TERMINAL_STATES:
                now = clock.now()
                clock_uncertain = bool(
                    isinstance(clock, ContainmentClock)
                    and clock.time_uncertain
                )
                owner = record.get("owner_execution_arn")
                lease_text = record.get("owner_lease_expires_at_utc")
                fence = record.get("owner_fence")
                spec_value = record.get("authorization_spec")
                if (
                    record.get("state") == "AUTHORIZED"
                    and owner is None
                    and isinstance(spec_value, Mapping)
                    and now >= guardian.parse_utc(str(spec_value.get("expires_at_utc")))
                ):
                    # Expiry/release is a safety proof, not an urgency clock.
                    # It therefore requires trusted time and KMS; an outage
                    # leaves the singleton closed and never permits CREATE.
                    if isinstance(clock, ContainmentClock):
                        clock.require_trusted_time_for_proof()
                        now = clock.now()
                    key = _key_from(
                        {
                            "issuer": spec_value.get("key", {}).get("issuer")
                            if isinstance(spec_value.get("key"), Mapping)
                            else None,
                            "provider_account_id": spec_value.get("key", {}).get(
                                "provider_account_id"
                            )
                            if isinstance(spec_value.get("key"), Mapping)
                            else None,
                            "authorization_id": spec_value.get("key", {}).get(
                                "authorization_id"
                            )
                            if isinstance(spec_value.get("key"), Mapping)
                            else None,
                        }
                    )
                    if key.pk != head_pk or key.sk != head_sk:
                        raise AdapterError("UNCLAIMED_RECOVERY_KEY_MISMATCH")
                    deny = DenyProviderTransport()
                    recovery_core = guardian.AwsProductionGuardianCore(
                        store=store,
                        signer=signer,
                        clock=clock,
                        secret_guard=deny,
                        transport=deny,
                    )
                    recovery_core.finalize_unclaimed_authorization_safe_loss(key)
                    terminal = store.get_consistent(head_pk, head_sk)
                    if (
                        terminal is None
                        or terminal.get("state")
                        != "NO_CREATE_DISPATCHED_SAFE_LOSS"
                        or terminal.get("unclaimed_authorization_safe_loss") is not True
                    ):
                        raise AdapterError(
                            "UNCLAIMED_RECOVERY_TERMINAL_STRONG_READ_FAILED"
                        )
                    if not store.release_global_active_if_terminal(head_pk, head_sk):
                        raise AdapterError("UNCLAIMED_RECOVERY_POINTER_RELEASE_FAILED")
                    unclaimed_finalized = 1
                    pointer_released = 1
                stop_due = False
                if (
                    record.get("state") in guardian.CONTAINMENT_RECOVERY_STATES
                    and isinstance(spec_value, Mapping)
                ):
                    stop_at = guardian.parse_utc(
                        str(spec_value.get("stop_dispatch_at_utc"))
                    )
                    if clock_uncertain:
                        # An unavailable trusted clock must never suppress
                        # recovery merely because Lambda's wall clock is slow.
                        # The successor receives only a boolean marker and
                        # derives this same floor from the strong ledger read.
                        clock.force_conservative_floor(stop_at)
                        now = clock.now()
                    stop_due = clock_uncertain or now >= stop_at
                if (
                    isinstance(owner, str)
                    and type(fence) is int
                    and isinstance(lease_text, str)
                    and (stop_due or now >= guardian.parse_utc(lease_text))
                ):
                    description = sfn.describe_execution(executionArn=owner)
                    input_text = description.get("input")
                    if not isinstance(input_text, str):
                        raise AdapterError("RECOVERY_SOURCE_INPUT_ABSENT")
                    parsed = guardian.strict_json(
                        input_text.encode("utf-8"),
                        "recovery source input",
                        max_bytes=MAX_EVENT_BYTES,
                    )
                    source_envelope = _event_envelope(parsed)
                    if source_envelope["deployment_binding_sha256"] != binding:
                        raise AdapterError("RECOVERY_SOURCE_BINDING_MISMATCH")
                    key = _key_from(source_envelope["authorization_key"])
                    if key.pk != head_pk or key.sk != head_sk:
                        raise AdapterError("RECOVERY_SOURCE_LEDGER_KEY_MISMATCH")
                    exact_request = _strict_b64(
                        source_envelope.get("exact_create_request_base64"),
                        label="RECOVERY_EXACT_CREATE_REQUEST",
                    )
                    spec_value = record.get("authorization_spec")
                    expected_request_sha = (
                        spec_value.get("exact_create_request_sha256")
                        if isinstance(spec_value, Mapping)
                        else None
                    )
                    if (
                        not isinstance(expected_request_sha, str)
                        or not hmac.compare_digest(
                            _sha256(exact_request), expected_request_sha
                        )
                    ):
                        raise AdapterError("RECOVERY_SOURCE_REQUEST_HASH_MISMATCH")
                    # Reconstruct a clean input from ledger identity plus only
                    # the hash-verified exact body.  Never replay stale token or
                    # action fields from a failed execution.
                    envelope = {
                        "schema_version": EXECUTION_SCHEMA,
                        "deployment_binding_sha256": binding,
                        "authorization_key": {
                            "issuer": key.issuer,
                            "provider_account_id": key.provider_account_id,
                            "authorization_id": key.authorization_id,
                        },
                        "exact_create_request_base64": base64.b64encode(
                            exact_request
                        ).decode("ascii"),
                    }
                    if clock_uncertain:
                        envelope["trusted_time_unavailable"] = True
                    name_token = _sha256(
                        _canonical(
                            {
                                "authorization_key_sha256": key.digest,
                                "next_fence": fence + 1,
                                "event_nonce": event_nonce,
                            }
                        )
                    )[:20]
                    name = (
                        f"recovery-f{fence + 1}-e{name_token}"
                    )
                    if not _EXECUTION_NAME.fullmatch(name):
                        raise AdapterError("RECOVERY_EXECUTION_NAME_INVALID")
                    start_result = _start_recovery_execution(
                        sfn,
                        state_machine_arn=environment["STATE_MACHINE_ARN"],
                        base_name=name,
                        input_text=_canonical(envelope).decode("utf-8"),
                    )
                    if start_result == "STARTED":
                        started = 1
                    elif start_result == "ALREADY_RUNNING":
                        already_exists = 1
                    else:
                        failed = 1
                        raise AdapterError("RECOVERY_START_RESULT_INVALID")
        return {
            "schema_version": RUNTIME_SCHEMA,
            "stale_successors_started": started,
            "stale_successors_already_exist": already_exists,
            "recovery_records_failed_closed": failed,
            "global_active_authorization_present": pointer is not None,
            "unclaimed_authorizations_finalized": unclaimed_finalized,
            "global_active_pointer_released": pointer_released,
            "compiled_core_lock_sha256": COMPILED_CORE_LOCK_SHA256,
        }
    except Exception as error:
        code = type(error).__name__.upper()
        raise SafeLambdaFailure(f"GUARDIAN_RECOVERY_FAIL_CLOSED:{code}") from None


__all__ = [
    "ActivationError",
    "AdapterError",
    "AwsKmsReceiptSigner",
    "AwsTrustedClock",
    "DynamoDbConditionalStore",
    "ExactSecretGuard",
    "ProviderSecret",
    "RuntimePorts",
    "StrictRunPodTransport",
    "control_handler",
    "create_handler",
    "execute_operation",
    "load_provider_secret",
    "observe_handler",
    "recovery_handler",
    "starter_handler",
    "stop_handler",
    "verify_receipt_with_kms",
]
