"""Atomic Stage C activation-budget reservation contract.

This module closes one narrow trust-system gap: it joins a pre-existing
authorization nonce to a conservative spend reservation using transaction time
owned by the ledger backend.  It deliberately does **not** start a provider,
load a model, prove Object Lock, or grant execution authority.

The in-memory implementation is an executable reference model.  The Postgres
adapter is an intentionally small seam around one atomic SQL statement.  A
post-dispatch database error is always indeterminate: callers may only perform
the exact-operation read reconciliation and must never repeat the mutation.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import threading
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable, Iterable, Mapping, Protocol


RESERVATION_STATUS = "RESERVED_NO_PROVIDER_OR_MODEL_START_AUTHORITY"
CONTROL_BOUNDARY = "BUDGET_RESERVATION_ONLY_PROVIDER_MODEL_OBJECT_LOCK_DARK"

_MACHINE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
_NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_MAX_MICROUSD = 10**15
_MAX_DURATION_SECONDS = 366 * 24 * 60 * 60


class ActivationBudgetLedgerError(RuntimeError):
    """A fail-closed domain or ledger error with a stable machine code."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class ActivationBudgetOutcomeIndeterminate(ActivationBudgetLedgerError):
    """The one mutation may have committed; only exact read reconciliation is safe."""

    def __init__(self, *, operation_id: str, request_sha256: str) -> None:
        super().__init__(
            "RESERVATION_OUTCOME_INDETERMINATE_NO_MUTATION_RETRY",
            "reservation outcome is indeterminate; reconcile the exact operation id",
        )
        self.operation_id = operation_id
        self.request_sha256 = request_sha256


def _machine(value: Any, field: str) -> str:
    if type(value) is not str or _MACHINE_RE.fullmatch(value) is None:
        raise ActivationBudgetLedgerError("INVALID_REQUEST", f"{field} is invalid")
    return value


def _sha256(value: Any, field: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise ActivationBudgetLedgerError("INVALID_REQUEST", f"{field} is invalid")
    return value


def _nonce(value: Any) -> str:
    if type(value) is not str or _NONCE_RE.fullmatch(value) is None:
        raise ActivationBudgetLedgerError("INVALID_REQUEST", "nonce_b64url is invalid")
    try:
        raw = base64.urlsafe_b64decode(value + "=")
    except (TypeError, ValueError) as exc:
        raise ActivationBudgetLedgerError("INVALID_REQUEST", "nonce_b64url is invalid") from exc
    if (
        len(raw) != 32
        or not any(raw)
        or base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii") != value
    ):
        raise ActivationBudgetLedgerError("INVALID_REQUEST", "nonce_b64url is invalid")
    return value


def _integer(
    value: Any,
    field: str,
    *,
    minimum: int = 0,
    maximum: int = _MAX_MICROUSD,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ActivationBudgetLedgerError("INVALID_REQUEST", f"{field} is invalid")
    return value


def _utc(value: Any, field: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise ActivationBudgetLedgerError("INVALID_REQUEST", f"{field} must be timezone-aware")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class ActivationBudgetAuthority:
    """A pre-existing authorization row; constructing it grants no execution authority."""

    tenant_id: str
    authorization_id: str
    budget_scope_id: str
    prospective_subject_sha256: str
    nonce_b64url: str
    window_start: datetime
    window_end: datetime
    maximum_quoted_rate_microusd_per_hour: int
    maximum_running_duration_seconds: int
    hard_cap_microusd: int

    def __post_init__(self) -> None:
        _machine(self.tenant_id, "tenant_id")
        _machine(self.authorization_id, "authorization_id")
        _machine(self.budget_scope_id, "budget_scope_id")
        _sha256(self.prospective_subject_sha256, "prospective_subject_sha256")
        _nonce(self.nonce_b64url)
        start = _utc(self.window_start, "window_start")
        end = _utc(self.window_end, "window_end")
        if not start < end:
            raise ActivationBudgetLedgerError("INVALID_REQUEST", "authorization window is empty")
        _integer(
            self.maximum_quoted_rate_microusd_per_hour,
            "maximum_quoted_rate_microusd_per_hour",
            minimum=1,
        )
        _integer(
            self.maximum_running_duration_seconds,
            "maximum_running_duration_seconds",
            minimum=1,
            maximum=_MAX_DURATION_SECONDS,
        )
        _integer(self.hard_cap_microusd, "hard_cap_microusd", minimum=1)


@dataclass(frozen=True, slots=True)
class ActivationBudgetReservationRequest:
    """Exact one-shot mutation input.  It intentionally carries no caller time."""

    tenant_id: str
    authorization_id: str
    budget_scope_id: str
    prospective_subject_sha256: str
    operation_id: str
    nonce_b64url: str
    quoted_rate_microusd_per_hour: int
    planned_running_duration_seconds: int
    observed_already_billed_microusd: int
    worst_case_reservation_microusd: int

    def __post_init__(self) -> None:
        _machine(self.tenant_id, "tenant_id")
        _machine(self.authorization_id, "authorization_id")
        _machine(self.budget_scope_id, "budget_scope_id")
        _sha256(self.prospective_subject_sha256, "prospective_subject_sha256")
        _machine(self.operation_id, "operation_id")
        _nonce(self.nonce_b64url)
        _integer(
            self.quoted_rate_microusd_per_hour,
            "quoted_rate_microusd_per_hour",
            minimum=1,
        )
        _integer(
            self.planned_running_duration_seconds,
            "planned_running_duration_seconds",
            minimum=1,
            maximum=_MAX_DURATION_SECONDS,
        )
        _integer(
            self.observed_already_billed_microusd,
            "observed_already_billed_microusd",
        )
        _integer(
            self.worst_case_reservation_microusd,
            "worst_case_reservation_microusd",
            minimum=1,
        )

    @property
    def request_sha256(self) -> str:
        raw = json.dumps(
            {
                "authorization_id": self.authorization_id,
                "budget_scope_id": self.budget_scope_id,
                "nonce_b64url": self.nonce_b64url,
                "observed_already_billed_microusd": self.observed_already_billed_microusd,
                "operation_id": self.operation_id,
                "planned_running_duration_seconds": self.planned_running_duration_seconds,
                "prospective_subject_sha256": self.prospective_subject_sha256,
                "quoted_rate_microusd_per_hour": self.quoted_rate_microusd_per_hour,
                "tenant_id": self.tenant_id,
                "worst_case_reservation_microusd": self.worst_case_reservation_microusd,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
        return hashlib.sha256(raw).hexdigest().upper()


@dataclass(frozen=True, slots=True)
class ActivationBudgetReservationReceipt:
    tenant_id: str
    authorization_id: str
    budget_scope_id: str
    prospective_subject_sha256: str
    operation_id: str
    request_sha256: str
    server_transaction_time: datetime
    nonce_state_before: str
    nonce_state_after: str
    quoted_rate_microusd_per_hour: int
    planned_running_duration_seconds: int
    compute_floor_microusd: int
    observed_already_billed_microusd: int
    observed_billed_high_water_before_microusd: int
    observed_billed_high_water_after_microusd: int
    reserved_before_microusd: int
    worst_case_reservation_microusd: int
    projected_total_microusd: int
    hard_cap_microusd: int
    ledger_generation: int
    status: str = RESERVATION_STATUS
    control_boundary: str = CONTROL_BOUNDARY
    provider_start_authorized: bool = False
    model_start_authorized: bool = False
    object_lock_authority: bool = False


def _fresh_request(value: Any) -> ActivationBudgetReservationRequest:
    if type(value) is not ActivationBudgetReservationRequest:
        raise ActivationBudgetLedgerError("INVALID_REQUEST", "request has wrong exact type")
    return ActivationBudgetReservationRequest(
        tenant_id=value.tenant_id,
        authorization_id=value.authorization_id,
        budget_scope_id=value.budget_scope_id,
        prospective_subject_sha256=value.prospective_subject_sha256,
        operation_id=value.operation_id,
        nonce_b64url=value.nonce_b64url,
        quoted_rate_microusd_per_hour=value.quoted_rate_microusd_per_hour,
        planned_running_duration_seconds=value.planned_running_duration_seconds,
        observed_already_billed_microusd=value.observed_already_billed_microusd,
        worst_case_reservation_microusd=value.worst_case_reservation_microusd,
    )


def _fresh_authority(value: Any) -> ActivationBudgetAuthority:
    if type(value) is not ActivationBudgetAuthority:
        raise ActivationBudgetLedgerError("INVALID_BACKEND", "authority has wrong type")
    return ActivationBudgetAuthority(
        tenant_id=value.tenant_id,
        authorization_id=value.authorization_id,
        budget_scope_id=value.budget_scope_id,
        prospective_subject_sha256=value.prospective_subject_sha256,
        nonce_b64url=value.nonce_b64url,
        window_start=value.window_start,
        window_end=value.window_end,
        maximum_quoted_rate_microusd_per_hour=value.maximum_quoted_rate_microusd_per_hour,
        maximum_running_duration_seconds=value.maximum_running_duration_seconds,
        hard_cap_microusd=value.hard_cap_microusd,
    )


def _copy_receipt(
    value: ActivationBudgetReservationReceipt,
) -> ActivationBudgetReservationReceipt:
    return ActivationBudgetReservationReceipt(
        tenant_id=value.tenant_id,
        authorization_id=value.authorization_id,
        budget_scope_id=value.budget_scope_id,
        prospective_subject_sha256=value.prospective_subject_sha256,
        operation_id=value.operation_id,
        request_sha256=value.request_sha256,
        server_transaction_time=value.server_transaction_time,
        nonce_state_before=value.nonce_state_before,
        nonce_state_after=value.nonce_state_after,
        quoted_rate_microusd_per_hour=value.quoted_rate_microusd_per_hour,
        planned_running_duration_seconds=value.planned_running_duration_seconds,
        compute_floor_microusd=value.compute_floor_microusd,
        observed_already_billed_microusd=value.observed_already_billed_microusd,
        observed_billed_high_water_before_microusd=(
            value.observed_billed_high_water_before_microusd
        ),
        observed_billed_high_water_after_microusd=(
            value.observed_billed_high_water_after_microusd
        ),
        reserved_before_microusd=value.reserved_before_microusd,
        worst_case_reservation_microusd=value.worst_case_reservation_microusd,
        projected_total_microusd=value.projected_total_microusd,
        hard_cap_microusd=value.hard_cap_microusd,
        ledger_generation=value.ledger_generation,
        status=value.status,
        control_boundary=value.control_boundary,
        provider_start_authorized=value.provider_start_authorized,
        model_start_authorized=value.model_start_authorized,
        object_lock_authority=value.object_lock_authority,
    )


def _compute_floor(rate_microusd_per_hour: int, duration_seconds: int) -> int:
    return (rate_microusd_per_hour * duration_seconds + 3_599) // 3_600


def _check_and_project(
    authority: ActivationBudgetAuthority,
    request: ActivationBudgetReservationRequest,
    *,
    server_time: datetime,
    reserved_before_microusd: int,
    observed_billed_high_water_before_microusd: int,
) -> tuple[int, int, int]:
    if (
        request.tenant_id != authority.tenant_id
        or request.authorization_id != authority.authorization_id
        or request.budget_scope_id != authority.budget_scope_id
        or request.prospective_subject_sha256 != authority.prospective_subject_sha256
        or request.nonce_b64url != authority.nonce_b64url
    ):
        raise ActivationBudgetLedgerError("AUTHORIZATION_BINDING_MISMATCH", "request differs from authority")
    now = _utc(server_time, "server_transaction_time")
    if not (_utc(authority.window_start, "window_start") <= now < _utc(authority.window_end, "window_end")):
        raise ActivationBudgetLedgerError("SERVER_TIME_OUTSIDE_AUTHORIZATION_WINDOW", "server time is outside window")
    if request.quoted_rate_microusd_per_hour > authority.maximum_quoted_rate_microusd_per_hour:
        raise ActivationBudgetLedgerError("QUOTED_RATE_ABOVE_BOUND", "quoted rate exceeds bound")
    if request.planned_running_duration_seconds > authority.maximum_running_duration_seconds:
        raise ActivationBudgetLedgerError("RUNNING_DURATION_ABOVE_BOUND", "duration exceeds bound")
    compute_floor = _compute_floor(
        request.quoted_rate_microusd_per_hour,
        request.planned_running_duration_seconds,
    )
    if request.worst_case_reservation_microusd < compute_floor:
        raise ActivationBudgetLedgerError(
            "WORST_CASE_RESERVATION_UNDERSTATES_COMPUTE",
            "worst-case reservation is below exact compute floor",
        )
    if (
        request.observed_already_billed_microusd
        < observed_billed_high_water_before_microusd
    ):
        raise ActivationBudgetLedgerError(
            "OBSERVED_BILLED_BELOW_SCOPE_HIGH_WATER",
            "observed billed amount cannot decrease within a budget scope",
        )
    observed_billed_high_water_after_microusd = max(
        observed_billed_high_water_before_microusd,
        request.observed_already_billed_microusd,
    )
    projected = (
        observed_billed_high_water_after_microusd
        + reserved_before_microusd
        + request.worst_case_reservation_microusd
    )
    if projected >= authority.hard_cap_microusd:
        raise ActivationBudgetLedgerError(
            "HARD_CAP_REQUIRES_STRICT_REMAINDER",
            "projected aggregate must remain strictly below hard cap",
        )
    return compute_floor, projected, observed_billed_high_water_after_microusd


class InMemoryActivationBudgetLedger:
    """Thread-safe reference semantics using an injected backend-owned clock."""

    def __init__(
        self,
        authorities: Iterable[ActivationBudgetAuthority],
        *,
        server_clock: Callable[[], datetime],
    ) -> None:
        if not callable(server_clock):
            raise ActivationBudgetLedgerError("INVALID_BACKEND", "server clock is unavailable")
        self._clock = server_clock
        self._lock = threading.Lock()
        self._authorities: dict[tuple[str, str], ActivationBudgetAuthority] = {}
        self._consumed: dict[tuple[str, str], str] = {}
        self._operations: dict[tuple[str, str], ActivationBudgetReservationReceipt] = {}
        self._scope_reserved: dict[tuple[str, str], int] = {}
        self._scope_observed_billed_high_water: dict[tuple[str, str], int] = {}
        self._scope_caps: dict[tuple[str, str], int] = {}
        self._nonce_keys: set[tuple[str, str]] = set()
        self._generation = 0
        for supplied_authority in authorities:
            authority = _fresh_authority(supplied_authority)
            key = (authority.tenant_id, authority.authorization_id)
            scope = (authority.tenant_id, authority.budget_scope_id)
            if key in self._authorities:
                raise ActivationBudgetLedgerError("INVALID_BACKEND", "duplicate authorization")
            nonce_key = (authority.tenant_id, authority.nonce_b64url)
            if nonce_key in self._nonce_keys:
                raise ActivationBudgetLedgerError("INVALID_BACKEND", "duplicate authorization nonce")
            if scope in self._scope_caps and self._scope_caps[scope] != authority.hard_cap_microusd:
                raise ActivationBudgetLedgerError("INVALID_BACKEND", "budget scope hard caps differ")
            self._authorities[key] = authority
            self._nonce_keys.add(nonce_key)
            self._scope_caps[scope] = authority.hard_cap_microusd
            self._scope_reserved.setdefault(scope, 0)
            self._scope_observed_billed_high_water.setdefault(scope, 0)

    def reserve_once(
        self, request: ActivationBudgetReservationRequest
    ) -> ActivationBudgetReservationReceipt:
        request = _fresh_request(request)
        operation_key = (request.tenant_id, request.operation_id)
        authority_key = (request.tenant_id, request.authorization_id)
        scope_key = (request.tenant_id, request.budget_scope_id)
        with self._lock:
            if operation_key in self._operations:
                raise ActivationBudgetLedgerError(
                    "OPERATION_ALREADY_RECORDED_RECONCILE_ONLY",
                    "mutation retry is forbidden; reconcile the exact operation",
                )
            authority = self._authorities.get(authority_key)
            if authority is None:
                raise ActivationBudgetLedgerError("AUTHORIZATION_NOT_FOUND", "authorization is unavailable")
            if authority_key in self._consumed:
                raise ActivationBudgetLedgerError("NONCE_ALREADY_CONSUMED", "authorization nonce is consumed")
            server_time = _utc(self._clock(), "server_transaction_time")
            if scope_key not in self._scope_reserved:
                raise ActivationBudgetLedgerError(
                    "AUTHORIZATION_BINDING_MISMATCH",
                    "request budget scope differs from authority",
                )
            reserved_before = self._scope_reserved[scope_key]
            observed_billed_high_water_before = (
                self._scope_observed_billed_high_water[scope_key]
            )
            compute_floor, projected, observed_billed_high_water_after = _check_and_project(
                authority,
                request,
                server_time=server_time,
                reserved_before_microusd=reserved_before,
                observed_billed_high_water_before_microusd=(
                    observed_billed_high_water_before
                ),
            )
            self._generation += 1
            receipt = ActivationBudgetReservationReceipt(
                tenant_id=request.tenant_id,
                authorization_id=request.authorization_id,
                budget_scope_id=request.budget_scope_id,
                prospective_subject_sha256=request.prospective_subject_sha256,
                operation_id=request.operation_id,
                request_sha256=request.request_sha256,
                server_transaction_time=server_time,
                nonce_state_before="UNCONSUMED",
                nonce_state_after="CONSUMED",
                quoted_rate_microusd_per_hour=request.quoted_rate_microusd_per_hour,
                planned_running_duration_seconds=request.planned_running_duration_seconds,
                compute_floor_microusd=compute_floor,
                observed_already_billed_microusd=request.observed_already_billed_microusd,
                observed_billed_high_water_before_microusd=(
                    observed_billed_high_water_before
                ),
                observed_billed_high_water_after_microusd=(
                    observed_billed_high_water_after
                ),
                reserved_before_microusd=reserved_before,
                worst_case_reservation_microusd=request.worst_case_reservation_microusd,
                projected_total_microusd=projected,
                hard_cap_microusd=authority.hard_cap_microusd,
                ledger_generation=self._generation,
            )
            self._scope_reserved[scope_key] = (
                reserved_before + request.worst_case_reservation_microusd
            )
            self._scope_observed_billed_high_water[scope_key] = (
                observed_billed_high_water_after
            )
            self._consumed[authority_key] = request.operation_id
            self._operations[operation_key] = receipt
            return _copy_receipt(receipt)

    def reconcile_exact_operation(
        self, request: ActivationBudgetReservationRequest
    ) -> ActivationBudgetReservationReceipt:
        """Read only.  Absence never licenses a mutation retry."""

        request = _fresh_request(request)
        with self._lock:
            receipt = self._operations.get((request.tenant_id, request.operation_id))
            if receipt is None:
                raise ActivationBudgetLedgerError(
                    "OPERATION_NOT_FOUND_NO_MUTATION_RETRY",
                    "exact operation is absent; mutation retry remains forbidden",
                )
            if receipt.request_sha256 != request.request_sha256:
                raise ActivationBudgetLedgerError(
                    "OPERATION_REQUEST_DIGEST_MISMATCH",
                    "operation id is bound to different request bytes",
                )
            return _copy_receipt(receipt)


POSTGRES_SCHEMA_SQL = """
CREATE SEQUENCE IF NOT EXISTS stagec_activation_budget_generation_seq AS bigint;
CREATE TABLE IF NOT EXISTS stagec_activation_budget_scopes (
    tenant_id text NOT NULL,
    budget_scope_id text NOT NULL,
    hard_cap_microusd bigint NOT NULL,
    reserved_microusd bigint NOT NULL DEFAULT 0,
    observed_billed_high_water_microusd bigint NOT NULL DEFAULT 0,
    CHECK (hard_cap_microusd BETWEEN 1 AND 1000000000000000),
    CHECK (reserved_microusd BETWEEN 0 AND 1000000000000000),
    CHECK (observed_billed_high_water_microusd BETWEEN 0 AND 1000000000000000),
    PRIMARY KEY (tenant_id, budget_scope_id)
);
CREATE TABLE IF NOT EXISTS stagec_activation_budget_authorizations (
    tenant_id text NOT NULL,
    authorization_id text NOT NULL,
    budget_scope_id text NOT NULL,
    prospective_subject_sha256 text NOT NULL,
    nonce_b64url text NOT NULL,
    window_start timestamptz NOT NULL,
    window_end timestamptz NOT NULL,
    maximum_quoted_rate_microusd_per_hour bigint NOT NULL,
    maximum_running_duration_seconds bigint NOT NULL,
    hard_cap_microusd bigint NOT NULL,
    nonce_state text NOT NULL DEFAULT 'UNCONSUMED',
    consumed_at timestamptz,
    consumed_operation_id text,
    CHECK (maximum_quoted_rate_microusd_per_hour BETWEEN 1 AND 1000000000000000),
    CHECK (maximum_running_duration_seconds BETWEEN 1 AND 31622400),
    CHECK (hard_cap_microusd BETWEEN 1 AND 1000000000000000),
    CHECK (nonce_state IN ('UNCONSUMED', 'CONSUMED')),
    UNIQUE (tenant_id, nonce_b64url),
    PRIMARY KEY (tenant_id, authorization_id)
);
CREATE TABLE IF NOT EXISTS stagec_activation_budget_operations (
    tenant_id text NOT NULL,
    operation_id text NOT NULL,
    authorization_id text NOT NULL,
    request_sha256 text NOT NULL,
    receipt jsonb NOT NULL,
    ledger_generation bigint NOT NULL UNIQUE,
    server_transaction_time timestamptz NOT NULL,
    PRIMARY KEY (tenant_id, operation_id)
);
"""


# One statement owns the transaction timestamp and locks both mutable rows before
# deciding.  ``numeric`` multiplication prevents bigint overflow in the compute
# floor.  Exact-cap equality is rejected by the explicit ``>=`` branch.
POSTGRES_RESERVE_SQL = """
WITH
i AS MATERIALIZED (
    SELECT
        %(tenant_id)s::text AS tenant_id,
        %(authorization_id)s::text AS authorization_id,
        %(budget_scope_id)s::text AS budget_scope_id,
        %(prospective_subject_sha256)s::text AS prospective_subject_sha256,
        %(operation_id)s::text AS operation_id,
        %(nonce_b64url)s::text AS nonce_b64url,
        %(request_sha256)s::text AS request_sha256,
        %(quoted_rate)s::bigint AS quoted_rate,
        %(duration_seconds)s::bigint AS duration_seconds,
        %(already_billed)s::bigint AS already_billed,
        %(reservation)s::bigint AS reservation
),
existing AS MATERIALIZED (
    SELECT o.request_sha256
      FROM stagec_activation_budget_operations o, i
     WHERE o.tenant_id = i.tenant_id AND o.operation_id = i.operation_id
     FOR UPDATE OF o
),
a AS MATERIALIZED (
    SELECT a.*
      FROM stagec_activation_budget_authorizations a, i
     WHERE a.tenant_id = i.tenant_id AND a.authorization_id = i.authorization_id
     FOR UPDATE OF a
),
s AS MATERIALIZED (
    SELECT s.*
      FROM stagec_activation_budget_scopes s, i
     WHERE s.tenant_id = i.tenant_id AND s.budget_scope_id = i.budget_scope_id
     FOR UPDATE OF s
),
t AS MATERIALIZED (
    SELECT clock_timestamp() AS server_time
      FROM (SELECT count(*) FROM existing) operation_lock,
           (SELECT count(*) FROM a) authorization_lock,
           (SELECT count(*) FROM s) budget_scope_lock
),
d AS MATERIALIZED (
    SELECT CASE
      WHEN EXISTS (SELECT 1 FROM existing) THEN 'OPERATION_ALREADY_RECORDED_RECONCILE_ONLY'
      WHEN NOT EXISTS (SELECT 1 FROM a) THEN 'AUTHORIZATION_NOT_FOUND'
      WHEN NOT EXISTS (SELECT 1 FROM s) THEN 'BUDGET_SCOPE_NOT_FOUND'
      WHEN (SELECT budget_scope_id FROM a) <> i.budget_scope_id
        OR (SELECT prospective_subject_sha256 FROM a) <> i.prospective_subject_sha256
        OR (SELECT nonce_b64url FROM a) <> i.nonce_b64url
        OR (SELECT hard_cap_microusd FROM a) <> (SELECT hard_cap_microusd FROM s)
        THEN 'AUTHORIZATION_BINDING_MISMATCH'
      WHEN (SELECT nonce_state FROM a) <> 'UNCONSUMED' THEN 'NONCE_ALREADY_CONSUMED'
      WHEN NOT ((SELECT window_start FROM a) <= t.server_time
            AND t.server_time < (SELECT window_end FROM a))
        THEN 'SERVER_TIME_OUTSIDE_AUTHORIZATION_WINDOW'
      WHEN i.quoted_rate > (SELECT maximum_quoted_rate_microusd_per_hour FROM a)
        THEN 'QUOTED_RATE_ABOVE_BOUND'
      WHEN i.duration_seconds > (SELECT maximum_running_duration_seconds FROM a)
        THEN 'RUNNING_DURATION_ABOVE_BOUND'
      WHEN i.reservation < CEIL((i.quoted_rate::numeric * i.duration_seconds::numeric) / 3600)
        THEN 'WORST_CASE_RESERVATION_UNDERSTATES_COMPUTE'
      WHEN i.already_billed < (SELECT observed_billed_high_water_microusd FROM s)
        THEN 'OBSERVED_BILLED_BELOW_SCOPE_HIGH_WATER'
      WHEN GREATEST(
             i.already_billed,
             (SELECT observed_billed_high_water_microusd FROM s)
           ) + (SELECT reserved_microusd FROM s) + i.reservation
            >= (SELECT hard_cap_microusd FROM a)
        THEN 'HARD_CAP_REQUIRES_STRICT_REMAINDER'
      ELSE 'RESERVED'
    END AS decision,
    i.*,
    t.server_time,
    COALESCE((SELECT reserved_microusd FROM s), 0) AS reserved_before,
    COALESCE(
      (SELECT observed_billed_high_water_microusd FROM s), 0
    ) AS observed_billed_high_water_before,
    GREATEST(
      i.already_billed,
      COALESCE((SELECT observed_billed_high_water_microusd FROM s), 0)
    ) AS observed_billed_high_water_after,
    CEIL((i.quoted_rate::numeric * i.duration_seconds::numeric) / 3600)::bigint AS compute_floor
    FROM i, t
),
consume AS (
    UPDATE stagec_activation_budget_authorizations a
       SET nonce_state = 'CONSUMED',
           consumed_at = d.server_time,
           consumed_operation_id = d.operation_id
      FROM d
     WHERE d.decision = 'RESERVED'
       AND a.tenant_id = d.tenant_id AND a.authorization_id = d.authorization_id
       AND a.nonce_state = 'UNCONSUMED'
    RETURNING a.hard_cap_microusd
),
scope_update AS (
    UPDATE stagec_activation_budget_scopes s
       SET reserved_microusd = s.reserved_microusd + d.reservation,
           observed_billed_high_water_microusd = GREATEST(
             s.observed_billed_high_water_microusd,
             d.already_billed
           )
      FROM d, consume
     WHERE d.decision = 'RESERVED'
       AND s.tenant_id = d.tenant_id AND s.budget_scope_id = d.budget_scope_id
    RETURNING s.reserved_microusd
),
written AS (
    INSERT INTO stagec_activation_budget_operations
        (tenant_id, operation_id, authorization_id, request_sha256, receipt,
         ledger_generation, server_transaction_time)
    SELECT d.tenant_id, d.operation_id, d.authorization_id, d.request_sha256,
           jsonb_build_object(
             'budget_scope_id', d.budget_scope_id,
             'prospective_subject_sha256', d.prospective_subject_sha256,
             'nonce_state_before', 'UNCONSUMED', 'nonce_state_after', 'CONSUMED',
             'quoted_rate_microusd_per_hour', d.quoted_rate,
             'planned_running_duration_seconds', d.duration_seconds,
             'compute_floor_microusd', d.compute_floor,
             'observed_already_billed_microusd', d.already_billed,
             'observed_billed_high_water_before_microusd',
               d.observed_billed_high_water_before,
             'observed_billed_high_water_after_microusd',
               d.observed_billed_high_water_after,
             'reserved_before_microusd', d.reserved_before,
             'worst_case_reservation_microusd', d.reservation,
             'projected_total_microusd',
               d.observed_billed_high_water_after + d.reserved_before + d.reservation,
             'hard_cap_microusd', consume.hard_cap_microusd,
             'status', 'RESERVED_NO_PROVIDER_OR_MODEL_START_AUTHORITY',
             'control_boundary',
               'BUDGET_RESERVATION_ONLY_PROVIDER_MODEL_OBJECT_LOCK_DARK',
             'provider_start_authorized', false,
             'model_start_authorized', false,
             'object_lock_authority', false
           ),
           nextval('stagec_activation_budget_generation_seq'), d.server_time
      FROM d, consume, scope_update
    RETURNING *
)
SELECT 'RESERVED'::text AS decision, w.* FROM written w
UNION ALL
SELECT d.decision, NULL::text, NULL::text, NULL::text, NULL::text, NULL::jsonb,
       NULL::bigint, NULL::timestamptz
  FROM d WHERE d.decision <> 'RESERVED';
"""


POSTGRES_RECONCILE_SQL = """
SELECT tenant_id, operation_id, authorization_id, request_sha256, receipt,
       ledger_generation, server_transaction_time
  FROM stagec_activation_budget_operations
 WHERE tenant_id = %(tenant_id)s AND operation_id = %(operation_id)s;
"""


class _PostgresConnection(Protocol):
    def transaction(self) -> Any: ...
    def execute(self, query: str, params: Mapping[str, Any]) -> Any: ...


def _mapping(cursor: Any, row: Any) -> dict[str, Any]:
    if isinstance(row, Mapping):
        return dict(row)
    description = getattr(cursor, "description", None)
    if description is None:
        raise TypeError("database row has no description")
    names = [item.name if hasattr(item, "name") else item[0] for item in description]
    return dict(zip(names, row, strict=True))


_POSTGRES_REJECTION_CODES = frozenset(
    {
        "OPERATION_ALREADY_RECORDED_RECONCILE_ONLY",
        "AUTHORIZATION_NOT_FOUND",
        "BUDGET_SCOPE_NOT_FOUND",
        "AUTHORIZATION_BINDING_MISMATCH",
        "NONCE_ALREADY_CONSUMED",
        "SERVER_TIME_OUTSIDE_AUTHORIZATION_WINDOW",
        "QUOTED_RATE_ABOVE_BOUND",
        "RUNNING_DURATION_ABOVE_BOUND",
        "WORST_CASE_RESERVATION_UNDERSTATES_COMPUTE",
        "OBSERVED_BILLED_BELOW_SCOPE_HIGH_WATER",
        "HARD_CAP_REQUIRES_STRICT_REMAINDER",
    }
)

_DATABASE_ROW_KEYS = frozenset(
    {
        "decision",
        "tenant_id",
        "operation_id",
        "authorization_id",
        "request_sha256",
        "receipt",
        "ledger_generation",
        "server_transaction_time",
    }
)

_DATABASE_RECEIPT_KEYS = frozenset(
    {
        "budget_scope_id",
        "prospective_subject_sha256",
        "nonce_state_before",
        "nonce_state_after",
        "quoted_rate_microusd_per_hour",
        "planned_running_duration_seconds",
        "compute_floor_microusd",
        "observed_already_billed_microusd",
        "observed_billed_high_water_before_microusd",
        "observed_billed_high_water_after_microusd",
        "reserved_before_microusd",
        "worst_case_reservation_microusd",
        "projected_total_microusd",
        "hard_cap_microusd",
        "status",
        "control_boundary",
        "provider_start_authorized",
        "model_start_authorized",
        "object_lock_authority",
    }
)


def _database_invalid(message: str) -> ActivationBudgetLedgerError:
    return ActivationBudgetLedgerError("DATABASE_RECEIPT_INVALID", message)


def _database_text(value: Any, field: str) -> str:
    if type(value) is not str:
        raise _database_invalid(f"{field} has wrong exact type")
    return value


def _database_machine(value: Any, field: str) -> str:
    value = _database_text(value, field)
    if _MACHINE_RE.fullmatch(value) is None:
        raise _database_invalid(f"{field} is malformed")
    return value


def _database_sha256(value: Any, field: str) -> str:
    value = _database_text(value, field)
    if _SHA256_RE.fullmatch(value) is None:
        raise _database_invalid(f"{field} is malformed")
    return value


def _database_integer(
    value: Any,
    field: str,
    *,
    minimum: int = 0,
    maximum: int = _MAX_MICROUSD,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise _database_invalid(f"{field} has wrong exact type or range")
    return value


def _database_utc(value: Any, field: str) -> datetime:
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
        raise _database_invalid(f"{field} has wrong exact type or timezone")
    return value.astimezone(UTC)


def _database_false(value: Any, field: str) -> bool:
    if type(value) is not bool or value is not False:
        raise _database_invalid(f"{field} must be exact false")
    return value


class PostgresActivationBudgetLedger:
    """Thin Postgres seam; schema installation and authority insertion are external."""

    def __init__(self, connection: _PostgresConnection) -> None:
        self._connection = connection

    @staticmethod
    def _params(request: ActivationBudgetReservationRequest) -> dict[str, Any]:
        return {
            "tenant_id": request.tenant_id,
            "authorization_id": request.authorization_id,
            "budget_scope_id": request.budget_scope_id,
            "prospective_subject_sha256": request.prospective_subject_sha256,
            "operation_id": request.operation_id,
            "nonce_b64url": request.nonce_b64url,
            "request_sha256": request.request_sha256,
            "quoted_rate": request.quoted_rate_microusd_per_hour,
            "duration_seconds": request.planned_running_duration_seconds,
            "already_billed": request.observed_already_billed_microusd,
            "reservation": request.worst_case_reservation_microusd,
        }

    def reserve_once(
        self, request: ActivationBudgetReservationRequest
    ) -> ActivationBudgetReservationReceipt:
        request = _fresh_request(request)
        try:
            transaction = self._connection.transaction()
            with transaction if transaction is not None else nullcontext():
                cursor = self._connection.execute(POSTGRES_RESERVE_SQL, self._params(request))
                row = cursor.fetchone()
        except Exception as exc:
            raise ActivationBudgetOutcomeIndeterminate(
                operation_id=request.operation_id,
                request_sha256=request.request_sha256,
            ) from exc
        if row is None:
            raise ActivationBudgetOutcomeIndeterminate(
                operation_id=request.operation_id,
                request_sha256=request.request_sha256,
            )
        try:
            value = _mapping(cursor, row)
        except Exception as exc:
            raise ActivationBudgetOutcomeIndeterminate(
                operation_id=request.operation_id,
                request_sha256=request.request_sha256,
            ) from exc
        try:
            decision = _database_text(value.get("decision"), "decision")
        except ActivationBudgetLedgerError as exc:
            raise ActivationBudgetOutcomeIndeterminate(
                operation_id=request.operation_id,
                request_sha256=request.request_sha256,
            ) from exc
        if decision != "RESERVED":
            if decision not in _POSTGRES_REJECTION_CODES:
                raise ActivationBudgetOutcomeIndeterminate(
                    operation_id=request.operation_id,
                    request_sha256=request.request_sha256,
                )
            code = decision
            raise ActivationBudgetLedgerError(code, "atomic reservation rejected")
        try:
            return self._receipt(request, value)
        except ActivationBudgetLedgerError as exc:
            raise ActivationBudgetOutcomeIndeterminate(
                operation_id=request.operation_id,
                request_sha256=request.request_sha256,
            ) from exc

    def reconcile_exact_operation(
        self, request: ActivationBudgetReservationRequest
    ) -> ActivationBudgetReservationReceipt:
        """Perform only the exact read; this method contains no mutation fallback."""

        request = _fresh_request(request)
        try:
            cursor = self._connection.execute(
                POSTGRES_RECONCILE_SQL,
                {"tenant_id": request.tenant_id, "operation_id": request.operation_id},
            )
            row = cursor.fetchone()
        except Exception as exc:
            raise ActivationBudgetLedgerError(
                "RECONCILIATION_READ_UNAVAILABLE_NO_MUTATION_RETRY",
                "exact-operation reconciliation failed",
            ) from exc
        if row is None:
            raise ActivationBudgetLedgerError(
                "OPERATION_NOT_FOUND_NO_MUTATION_RETRY",
                "exact operation is absent; mutation retry remains forbidden",
            )
        try:
            value = _mapping(cursor, row)
        except Exception as exc:
            raise _database_invalid("database row cannot be mapped") from exc
        stored_request_sha256 = _database_sha256(
            value.get("request_sha256"), "request_sha256"
        )
        if stored_request_sha256 != request.request_sha256:
            raise ActivationBudgetLedgerError(
                "OPERATION_REQUEST_DIGEST_MISMATCH",
                "operation id is bound to different request bytes",
            )
        value["decision"] = "RESERVED"
        return self._receipt(request, value)

    @staticmethod
    def _receipt(
        request: ActivationBudgetReservationRequest, row: Mapping[str, Any]
    ) -> ActivationBudgetReservationReceipt:
        if type(row) is not dict or frozenset(row) != _DATABASE_ROW_KEYS:
            raise _database_invalid("database row shape differs from the frozen contract")
        payload = row["receipt"]
        if type(payload) is not dict or frozenset(payload) != _DATABASE_RECEIPT_KEYS:
            raise _database_invalid("receipt shape differs from the frozen contract")

        decision = _database_text(row["decision"], "decision")
        tenant_id = _database_machine(row["tenant_id"], "tenant_id")
        authorization_id = _database_machine(
            row["authorization_id"], "authorization_id"
        )
        operation_id = _database_machine(row["operation_id"], "operation_id")
        request_sha256 = _database_sha256(row["request_sha256"], "request_sha256")
        server_time = _database_utc(
            row["server_transaction_time"], "server_transaction_time"
        )
        generation = _database_integer(
            row["ledger_generation"],
            "ledger_generation",
            minimum=1,
            maximum=2**63 - 1,
        )

        budget_scope_id = _database_machine(
            payload["budget_scope_id"], "budget_scope_id"
        )
        prospective_subject_sha256 = _database_sha256(
            payload["prospective_subject_sha256"], "prospective_subject_sha256"
        )
        nonce_state_before = _database_text(
            payload["nonce_state_before"], "nonce_state_before"
        )
        nonce_state_after = _database_text(
            payload["nonce_state_after"], "nonce_state_after"
        )
        quoted_rate = _database_integer(
            payload["quoted_rate_microusd_per_hour"],
            "quoted_rate_microusd_per_hour",
            minimum=1,
        )
        planned_duration = _database_integer(
            payload["planned_running_duration_seconds"],
            "planned_running_duration_seconds",
            minimum=1,
            maximum=_MAX_DURATION_SECONDS,
        )
        compute_floor = _database_integer(
            payload["compute_floor_microusd"], "compute_floor_microusd", minimum=1
        )
        observed_billed = _database_integer(
            payload["observed_already_billed_microusd"],
            "observed_already_billed_microusd",
        )
        observed_billed_high_water_before = _database_integer(
            payload["observed_billed_high_water_before_microusd"],
            "observed_billed_high_water_before_microusd",
        )
        observed_billed_high_water_after = _database_integer(
            payload["observed_billed_high_water_after_microusd"],
            "observed_billed_high_water_after_microusd",
        )
        reserved_before = _database_integer(
            payload["reserved_before_microusd"], "reserved_before_microusd"
        )
        reservation = _database_integer(
            payload["worst_case_reservation_microusd"],
            "worst_case_reservation_microusd",
            minimum=1,
        )
        projected_total = _database_integer(
            payload["projected_total_microusd"], "projected_total_microusd"
        )
        hard_cap = _database_integer(
            payload["hard_cap_microusd"], "hard_cap_microusd", minimum=1
        )
        status = _database_text(payload["status"], "status")
        control_boundary = _database_text(
            payload["control_boundary"], "control_boundary"
        )
        provider_start_authorized = _database_false(
            payload["provider_start_authorized"], "provider_start_authorized"
        )
        model_start_authorized = _database_false(
            payload["model_start_authorized"], "model_start_authorized"
        )
        object_lock_authority = _database_false(
            payload["object_lock_authority"], "object_lock_authority"
        )

        if (
            decision != "RESERVED"
            or tenant_id != request.tenant_id
            or authorization_id != request.authorization_id
            or operation_id != request.operation_id
            or request_sha256 != request.request_sha256
            or budget_scope_id != request.budget_scope_id
            or prospective_subject_sha256 != request.prospective_subject_sha256
            or nonce_state_before != "UNCONSUMED"
            or nonce_state_after != "CONSUMED"
            or quoted_rate != request.quoted_rate_microusd_per_hour
            or planned_duration != request.planned_running_duration_seconds
            or observed_billed != request.observed_already_billed_microusd
            or reservation != request.worst_case_reservation_microusd
            or status != RESERVATION_STATUS
            or control_boundary != CONTROL_BOUNDARY
        ):
            raise _database_invalid("receipt bindings differ from exact request")
        expected_compute = _compute_floor(
            request.quoted_rate_microusd_per_hour,
            request.planned_running_duration_seconds,
        )
        expected_high_water_after = max(
            observed_billed_high_water_before,
            request.observed_already_billed_microusd,
        )
        expected_projected = (
            observed_billed_high_water_after
            + reserved_before
            + request.worst_case_reservation_microusd
        )
        if (
            compute_floor != expected_compute
            or request.observed_already_billed_microusd
            < observed_billed_high_water_before
            or observed_billed_high_water_after != expected_high_water_after
            or projected_total != expected_projected
            or projected_total >= hard_cap
        ):
            raise _database_invalid("receipt arithmetic does not replay")
        return ActivationBudgetReservationReceipt(
            tenant_id=tenant_id,
            authorization_id=authorization_id,
            budget_scope_id=budget_scope_id,
            prospective_subject_sha256=prospective_subject_sha256,
            operation_id=operation_id,
            request_sha256=request_sha256,
            server_transaction_time=server_time,
            nonce_state_before=nonce_state_before,
            nonce_state_after=nonce_state_after,
            quoted_rate_microusd_per_hour=quoted_rate,
            planned_running_duration_seconds=planned_duration,
            compute_floor_microusd=compute_floor,
            observed_already_billed_microusd=observed_billed,
            observed_billed_high_water_before_microusd=(
                observed_billed_high_water_before
            ),
            observed_billed_high_water_after_microusd=(
                observed_billed_high_water_after
            ),
            reserved_before_microusd=reserved_before,
            worst_case_reservation_microusd=reservation,
            projected_total_microusd=projected_total,
            hard_cap_microusd=hard_cap,
            ledger_generation=generation,
            status=status,
            control_boundary=control_boundary,
            provider_start_authorized=provider_start_authorized,
            model_start_authorized=model_start_authorized,
            object_lock_authority=object_lock_authority,
        )


__all__ = [
    "ActivationBudgetAuthority",
    "ActivationBudgetLedgerError",
    "ActivationBudgetOutcomeIndeterminate",
    "ActivationBudgetReservationReceipt",
    "ActivationBudgetReservationRequest",
    "CONTROL_BOUNDARY",
    "InMemoryActivationBudgetLedger",
    "POSTGRES_RECONCILE_SQL",
    "POSTGRES_RESERVE_SQL",
    "POSTGRES_SCHEMA_SQL",
    "PostgresActivationBudgetLedger",
    "RESERVATION_STATUS",
]
