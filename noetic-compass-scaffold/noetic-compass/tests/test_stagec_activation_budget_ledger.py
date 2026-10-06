from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from api.services.production.stagec_activation_budget_ledger import (
    ActivationBudgetAuthority,
    ActivationBudgetLedgerError,
    ActivationBudgetOutcomeIndeterminate,
    ActivationBudgetReservationRequest,
    CONTROL_BOUNDARY,
    InMemoryActivationBudgetLedger,
    POSTGRES_RECONCILE_SQL,
    POSTGRES_RESERVE_SQL,
    POSTGRES_SCHEMA_SQL,
    PostgresActivationBudgetLedger,
    RESERVATION_STATUS,
)


T0 = datetime(2026, 8, 13, 20, 0, tzinfo=UTC)
SUBJECT = "A" * 64
NONCE = base64.urlsafe_b64encode(bytes(range(32))).rstrip(b"=").decode("ascii")


def authority(
    authorization_id: str = "auth-001",
    *,
    scope: str = "budget-window-001",
    start: datetime = T0 - timedelta(minutes=1),
    end: datetime = T0 + timedelta(hours=1),
    hard_cap: int = 100_000_000,
    nonce: str = NONCE,
) -> ActivationBudgetAuthority:
    return ActivationBudgetAuthority(
        tenant_id="tenant-a",
        authorization_id=authorization_id,
        budget_scope_id=scope,
        prospective_subject_sha256=SUBJECT,
        nonce_b64url=nonce,
        window_start=start,
        window_end=end,
        maximum_quoted_rate_microusd_per_hour=440_000,
        maximum_running_duration_seconds=86_400,
        hard_cap_microusd=hard_cap,
    )


def request(
    operation_id: str = "reserve-001",
    *,
    authorization_id: str = "auth-001",
    scope: str = "budget-window-001",
    nonce: str = NONCE,
    rate: int = 440_000,
    duration: int = 3_600,
    billed: int = 10_000_000,
    reservation: int = 1_000_000,
) -> ActivationBudgetReservationRequest:
    return ActivationBudgetReservationRequest(
        tenant_id="tenant-a",
        authorization_id=authorization_id,
        budget_scope_id=scope,
        prospective_subject_sha256=SUBJECT,
        operation_id=operation_id,
        nonce_b64url=nonce,
        quoted_rate_microusd_per_hour=rate,
        planned_running_duration_seconds=duration,
        observed_already_billed_microusd=billed,
        worst_case_reservation_microusd=reservation,
    )


def error_code(call) -> str:
    with pytest.raises(ActivationBudgetLedgerError) as caught:
        call()
    return caught.value.error_code


def test_reference_reservation_uses_backend_clock_and_has_no_start_authority() -> None:
    ledger = InMemoryActivationBudgetLedger([authority()], server_clock=lambda: T0)
    value = ledger.reserve_once(request())

    assert value.server_transaction_time == T0
    assert value.compute_floor_microusd == 440_000
    assert value.projected_total_microusd == 11_000_000
    assert value.observed_billed_high_water_before_microusd == 0
    assert value.observed_billed_high_water_after_microusd == 10_000_000
    assert value.nonce_state_before == "UNCONSUMED"
    assert value.nonce_state_after == "CONSUMED"
    assert value.ledger_generation == 1
    assert value.status == RESERVATION_STATUS
    assert value.control_boundary == CONTROL_BOUNDARY
    assert value.provider_start_authorized is False
    assert value.model_start_authorized is False
    assert value.object_lock_authority is False
    assert not any("time" in name for name in request().__dataclass_fields__)


def test_exact_integer_compute_ceiling_and_strict_hard_cap() -> None:
    one_second = InMemoryActivationBudgetLedger(
        [authority(hard_cap=12)], server_clock=lambda: T0
    )
    receipt = one_second.reserve_once(
        request(rate=1, duration=1, billed=9, reservation=1)
    )
    assert receipt.compute_floor_microusd == 1
    assert receipt.projected_total_microusd == 10

    exact_cap = InMemoryActivationBudgetLedger(
        [authority(hard_cap=11)], server_clock=lambda: T0
    )
    assert error_code(
        lambda: exact_cap.reserve_once(
            request(rate=1, duration=1, billed=10, reservation=1)
        )
    ) == "HARD_CAP_REQUIRES_STRICT_REMAINDER"


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"rate": 440_001}, "QUOTED_RATE_ABOVE_BOUND"),
        ({"duration": 86_401, "reservation": 11_000_000}, "RUNNING_DURATION_ABOVE_BOUND"),
        ({"reservation": 439_999}, "WORST_CASE_RESERVATION_UNDERSTATES_COMPUTE"),
    ],
)
def test_rate_duration_and_compute_undercount_fail_closed(overrides, expected) -> None:
    ledger = InMemoryActivationBudgetLedger([authority()], server_clock=lambda: T0)
    assert error_code(lambda: ledger.reserve_once(request(**overrides))) == expected


def test_server_window_is_half_open_and_caller_cannot_supply_time() -> None:
    at_start = InMemoryActivationBudgetLedger(
        [authority(start=T0, end=T0 + timedelta(seconds=1))], server_clock=lambda: T0
    )
    assert at_start.reserve_once(request()).ledger_generation == 1

    at_end = InMemoryActivationBudgetLedger(
        [authority(start=T0 - timedelta(seconds=1), end=T0)], server_clock=lambda: T0
    )
    assert error_code(lambda: at_end.reserve_once(request())) == (
        "SERVER_TIME_OUTSIDE_AUTHORIZATION_WINDOW"
    )


def test_nonce_is_one_use_and_duplicate_operation_is_reconcile_only() -> None:
    ledger = InMemoryActivationBudgetLedger([authority()], server_clock=lambda: T0)
    original = request()
    first = ledger.reserve_once(original)

    assert error_code(lambda: ledger.reserve_once(original)) == (
        "OPERATION_ALREADY_RECORDED_RECONCILE_ONLY"
    )
    assert error_code(lambda: ledger.reserve_once(request("reserve-002"))) == (
        "NONCE_ALREADY_CONSUMED"
    )
    assert ledger.reconcile_exact_operation(original) == first

    changed = replace(original, worst_case_reservation_microusd=1_000_001)
    assert error_code(lambda: ledger.reconcile_exact_operation(changed)) == (
        "OPERATION_REQUEST_DIGEST_MISMATCH"
    )


def test_absent_reconciliation_never_turns_into_mutation_permission() -> None:
    ledger = InMemoryActivationBudgetLedger([authority()], server_clock=lambda: T0)
    assert error_code(lambda: ledger.reconcile_exact_operation(request())) == (
        "OPERATION_NOT_FOUND_NO_MUTATION_RETRY"
    )


def test_concurrent_nonce_consumption_has_one_winner() -> None:
    ledger = InMemoryActivationBudgetLedger([authority()], server_clock=lambda: T0)

    def attempt(index: int):
        try:
            return ledger.reserve_once(request(f"reserve-{index:03d}"))
        except ActivationBudgetLedgerError as exc:
            return exc.error_code

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(attempt, range(32)))
    winners = [item for item in results if not isinstance(item, str)]
    losers = [item for item in results if isinstance(item, str)]
    assert len(winners) == 1
    assert set(losers) == {"NONCE_ALREADY_CONSUMED"}


def test_scope_reservations_accumulate_and_generations_are_monotonic() -> None:
    second_nonce = base64.urlsafe_b64encode(bytes(range(31, -1, -1))).rstrip(b"=").decode("ascii")
    ledger = InMemoryActivationBudgetLedger(
        [authority(), authority("auth-002", nonce=second_nonce)],
        server_clock=lambda: T0,
    )
    first = ledger.reserve_once(request(reservation=1_000_000))
    second = ledger.reserve_once(
        request(
            "reserve-002",
            authorization_id="auth-002",
            nonce=second_nonce,
            reservation=2_000_000,
        )
    )
    assert first.reserved_before_microusd == 0
    assert second.reserved_before_microusd == 1_000_000
    assert (first.ledger_generation, second.ledger_generation) == (1, 2)


def test_scope_billed_high_water_cannot_decrease_and_drives_cap_projection() -> None:
    second_nonce = base64.urlsafe_b64encode(b"\x21" * 32).rstrip(b"=").decode("ascii")
    third_nonce = base64.urlsafe_b64encode(b"\x22" * 32).rstrip(b"=").decode("ascii")
    ledger = InMemoryActivationBudgetLedger(
        [
            authority(hard_cap=100),
            authority("auth-002", hard_cap=100, nonce=second_nonce),
            authority("auth-003", hard_cap=100, nonce=third_nonce),
        ],
        server_clock=lambda: T0,
    )

    first = ledger.reserve_once(
        request(rate=1, duration=1, billed=80, reservation=5)
    )
    assert first.observed_billed_high_water_before_microusd == 0
    assert first.observed_billed_high_water_after_microusd == 80
    assert first.projected_total_microusd == 85

    assert error_code(
        lambda: ledger.reserve_once(
            request(
                "reserve-lower",
                authorization_id="auth-002",
                nonce=second_nonce,
                rate=1,
                duration=1,
                billed=79,
                reservation=1,
            )
        )
    ) == "OBSERVED_BILLED_BELOW_SCOPE_HIGH_WATER"
    assert error_code(
        lambda: ledger.reserve_once(
            request(
                "reserve-exact-cap",
                authorization_id="auth-003",
                nonce=third_nonce,
                rate=1,
                duration=1,
                billed=80,
                reservation=15,
            )
        )
    ) == "HARD_CAP_REQUIRES_STRICT_REMAINDER"

    second = ledger.reserve_once(
        request(
            "reserve-002",
            authorization_id="auth-002",
            nonce=second_nonce,
            rate=1,
            duration=1,
            billed=80,
            reservation=14,
        )
    )
    assert second.observed_billed_high_water_before_microusd == 80
    assert second.observed_billed_high_water_after_microusd == 80
    assert second.reserved_before_microusd == 5
    assert second.projected_total_microusd == 99


def test_concurrent_multi_authorization_high_water_updates_are_atomic() -> None:
    authorization_indexes = list(range(1, 17))
    nonces = {
        index: base64.urlsafe_b64encode(bytes([index]) * 32)
        .rstrip(b"=")
        .decode("ascii")
        for index in authorization_indexes
    }
    authorities = [
        authority(
            f"auth-{index:03d}",
            hard_cap=1_000,
            nonce=nonces[index],
        )
        for index in authorization_indexes
    ]
    ledger = InMemoryActivationBudgetLedger(authorities, server_clock=lambda: T0)

    def attempt(index: int):
        try:
            return ledger.reserve_once(
                request(
                    f"reserve-{index:03d}",
                    authorization_id=f"auth-{index:03d}",
                    nonce=nonces[index],
                    rate=1,
                    duration=1,
                    billed=100,
                    reservation=1,
                )
            )
        except ActivationBudgetLedgerError as exc:
            return exc.error_code

    with ThreadPoolExecutor(max_workers=len(authorization_indexes)) as pool:
        outcomes = list(pool.map(attempt, reversed(authorization_indexes)))

    receipts = sorted(
        (item for item in outcomes if not isinstance(item, str)),
        key=lambda item: item.ledger_generation,
    )
    assert len(receipts) == len(authorization_indexes)
    assert not any(isinstance(item, str) for item in outcomes)

    prior_high_water = 0
    prior_reserved = 0
    for receipt in receipts:
        assert receipt.observed_billed_high_water_before_microusd == prior_high_water
        assert receipt.observed_billed_high_water_after_microusd >= prior_high_water
        assert (
            receipt.observed_billed_high_water_after_microusd
            == receipt.observed_already_billed_microusd
        )
        assert receipt.reserved_before_microusd == prior_reserved
        assert receipt.projected_total_microusd == (
            receipt.observed_billed_high_water_after_microusd
            + receipt.reserved_before_microusd
            + receipt.worst_case_reservation_microusd
        )
        prior_high_water = receipt.observed_billed_high_water_after_microusd
        prior_reserved += receipt.worst_case_reservation_microusd
    assert prior_high_water == 100
    assert prior_reserved == len(authorization_indexes)


def test_request_digest_is_stable_and_binds_every_mutation_field() -> None:
    base = request()
    assert base.request_sha256 == request().request_sha256
    mutations = [
        replace(base, operation_id="reserve-x"),
        replace(base, quoted_rate_microusd_per_hour=439_999),
        replace(base, planned_running_duration_seconds=3_599),
        replace(base, observed_already_billed_microusd=9_999_999),
        replace(base, worst_case_reservation_microusd=1_000_001),
    ]
    assert len({base.request_sha256, *(item.request_sha256 for item in mutations)}) == 6


def test_exact_types_nonce_and_scope_cap_consistency_are_required() -> None:
    with pytest.raises(ActivationBudgetLedgerError):
        request(rate=True)
    with pytest.raises(ActivationBudgetLedgerError):
        request(nonce="A" * 43)
    with pytest.raises(ActivationBudgetLedgerError):
        InMemoryActivationBudgetLedger(
            [authority(), authority("auth-002", hard_cap=99_000_000)],
            server_clock=lambda: T0,
        )
    with pytest.raises(ActivationBudgetLedgerError):
        InMemoryActivationBudgetLedger(
            [authority(), authority("auth-002")], server_clock=lambda: T0
        )


def test_reference_detaches_authority_and_revalidates_mutated_request() -> None:
    supplied = authority()
    ledger = InMemoryActivationBudgetLedger([supplied], server_clock=lambda: T0)
    object.__setattr__(supplied, "hard_cap_microusd", 1)
    assert ledger.reserve_once(request()).hard_cap_microusd == 100_000_000

    corrupted = request("reserve-corrupt")
    object.__setattr__(corrupted, "quoted_rate_microusd_per_hour", True)
    assert error_code(lambda: ledger.reconcile_exact_operation(corrupted)) == "INVALID_REQUEST"


def test_reference_reconciliation_detaches_caller_visible_receipt() -> None:
    ledger = InMemoryActivationBudgetLedger([authority()], server_clock=lambda: T0)
    req = request()
    visible = ledger.reserve_once(req)
    object.__setattr__(visible, "projected_total_microusd", 1)
    reconciled = ledger.reconcile_exact_operation(req)
    assert reconciled.projected_total_microusd == 11_000_000
    assert reconciled is not visible


class FakeTransaction:
    def __init__(self, owner) -> None:
        self.owner = owner

    def __enter__(self):
        self.owner.transactions += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        self.owner.transaction_exits += 1
        return False


class FakeCursor:
    def __init__(self, row) -> None:
        self.row = row
        self.description = None

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, outcomes) -> None:
        self.outcomes = list(outcomes)
        self.calls = []
        self.transactions = 0
        self.transaction_exits = 0

    def transaction(self):
        return FakeTransaction(self)

    def execute(self, query, params):
        self.calls.append((query, dict(params)))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return FakeCursor(outcome)


def postgres_row(req: ActivationBudgetReservationRequest, *, decision="RESERVED"):
    payload = {
        "budget_scope_id": req.budget_scope_id,
        "prospective_subject_sha256": req.prospective_subject_sha256,
        "nonce_state_before": "UNCONSUMED",
        "nonce_state_after": "CONSUMED",
        "quoted_rate_microusd_per_hour": req.quoted_rate_microusd_per_hour,
        "planned_running_duration_seconds": req.planned_running_duration_seconds,
        "compute_floor_microusd": 440_000,
        "observed_already_billed_microusd": req.observed_already_billed_microusd,
        "observed_billed_high_water_before_microusd": 0,
        "observed_billed_high_water_after_microusd": (
            req.observed_already_billed_microusd
        ),
        "reserved_before_microusd": 0,
        "worst_case_reservation_microusd": req.worst_case_reservation_microusd,
        "projected_total_microusd": 11_000_000,
        "hard_cap_microusd": 100_000_000,
        "status": RESERVATION_STATUS,
        "control_boundary": CONTROL_BOUNDARY,
        "provider_start_authorized": False,
        "model_start_authorized": False,
        "object_lock_authority": False,
    }
    return {
        "decision": decision,
        "tenant_id": req.tenant_id,
        "operation_id": req.operation_id,
        "authorization_id": req.authorization_id,
        "request_sha256": req.request_sha256,
        "receipt": payload,
        "ledger_generation": 7,
        "server_transaction_time": T0,
    }


def assert_malformed_database_receipt_is_rejected_on_both_paths(
    req: ActivationBudgetReservationRequest, row
) -> None:
    mutation_connection = FakeConnection([row])
    with pytest.raises(ActivationBudgetOutcomeIndeterminate):
        PostgresActivationBudgetLedger(mutation_connection).reserve_once(req)
    assert len(mutation_connection.calls) == 1

    read_connection = FakeConnection([row])
    assert error_code(
        lambda: PostgresActivationBudgetLedger(
            read_connection
        ).reconcile_exact_operation(req)
    ) == "DATABASE_RECEIPT_INVALID"
    assert [query for query, _ in read_connection.calls] == [POSTGRES_RECONCILE_SQL]


def test_postgres_adapter_performs_one_mutation_and_maps_server_receipt() -> None:
    req = request()
    connection = FakeConnection([postgres_row(req)])
    ledger = PostgresActivationBudgetLedger(connection)
    receipt = ledger.reserve_once(req)

    assert receipt.ledger_generation == 7
    assert receipt.server_transaction_time == T0
    assert connection.transactions == connection.transaction_exits == 1
    assert len(connection.calls) == 1
    assert connection.calls[0][0] == POSTGRES_RESERVE_SQL
    assert connection.calls[0][1]["request_sha256"] == req.request_sha256
    assert "server_time" not in connection.calls[0][1]


def test_postgres_receipt_replays_scope_high_water_and_reserved_projection() -> None:
    req = request()
    row = postgres_row(req)
    row["receipt"] = dict(row["receipt"])
    row["receipt"].update(
        {
            "observed_billed_high_water_before_microusd": 8_000_000,
            "observed_billed_high_water_after_microusd": 10_000_000,
            "reserved_before_microusd": 2_000_000,
            "projected_total_microusd": 13_000_000,
        }
    )
    receipt = PostgresActivationBudgetLedger(FakeConnection([row])).reserve_once(req)

    assert receipt.observed_billed_high_water_before_microusd == 8_000_000
    assert receipt.observed_billed_high_water_after_microusd == 10_000_000
    assert receipt.reserved_before_microusd == 2_000_000
    assert receipt.projected_total_microusd == 13_000_000


@pytest.mark.parametrize(
    "field",
    [
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
    ],
)
@pytest.mark.parametrize("corrupt", [True, 1.0, "1"])
def test_database_receipt_integer_fields_require_exact_int_on_both_paths(
    field, corrupt
) -> None:
    req = request()
    row = postgres_row(req)
    row["receipt"] = dict(row["receipt"])
    row["receipt"][field] = corrupt
    assert_malformed_database_receipt_is_rejected_on_both_paths(req, row)


@pytest.mark.parametrize(
    "field",
    [
        "quoted_rate_microusd_per_hour",
        "planned_running_duration_seconds",
        "observed_already_billed_microusd",
        "worst_case_reservation_microusd",
    ],
)
@pytest.mark.parametrize("corrupt", [True, 1.0])
def test_database_echo_rejects_bool_and_float_that_compare_equal_to_integer_one(
    field, corrupt
) -> None:
    req = request(rate=1, duration=1, billed=1, reservation=1)
    row = postgres_row(req)
    row["receipt"] = dict(row["receipt"])
    row["receipt"].update(
        {
            "compute_floor_microusd": 1,
            "observed_billed_high_water_after_microusd": 1,
            "projected_total_microusd": 2,
        }
    )
    row["receipt"][field] = corrupt
    assert_malformed_database_receipt_is_rejected_on_both_paths(req, row)


@pytest.mark.parametrize(
    ("field", "corrupt"),
    [
        ("tenant_id", True),
        ("authorization_id", 7.0),
        ("operation_id", 7),
        ("request_sha256", False),
        ("ledger_generation", True),
        ("ledger_generation", 7.0),
        ("ledger_generation", "7"),
        ("server_transaction_time", "2026-08-13T20:00:00Z"),
    ],
)
def test_database_row_fields_require_exact_types_on_both_paths(field, corrupt) -> None:
    req = request()
    row = postgres_row(req)
    row[field] = corrupt
    assert_malformed_database_receipt_is_rejected_on_both_paths(req, row)


@pytest.mark.parametrize(
    ("field", "corrupt"),
    [
        ("budget_scope_id", True),
        ("prospective_subject_sha256", 7.0),
        ("nonce_state_before", 0),
        ("nonce_state_after", False),
        ("status", 1.0),
    ],
)
def test_database_receipt_text_fields_require_exact_str_on_both_paths(
    field, corrupt
) -> None:
    req = request()
    row = postgres_row(req)
    row["receipt"] = dict(row["receipt"])
    row["receipt"][field] = corrupt
    assert_malformed_database_receipt_is_rejected_on_both_paths(req, row)


@pytest.mark.parametrize(
    ("field", "corrupt"),
    [
        ("provider_start_authorized", True),
        ("provider_start_authorized", 0),
        ("provider_start_authorized", 0.0),
        ("provider_start_authorized", "false"),
        ("model_start_authorized", True),
        ("model_start_authorized", 0),
        ("model_start_authorized", 0.0),
        ("model_start_authorized", "false"),
        ("object_lock_authority", True),
        ("object_lock_authority", 0),
        ("object_lock_authority", 0.0),
        ("object_lock_authority", "false"),
    ],
)
def test_database_receipt_dark_controls_require_exact_false_on_both_paths(
    field, corrupt
) -> None:
    req = request()
    row = postgres_row(req)
    row["receipt"] = dict(row["receipt"])
    row["receipt"][field] = corrupt
    assert_malformed_database_receipt_is_rejected_on_both_paths(req, row)


@pytest.mark.parametrize(
    ("field", "corrupt"),
    [
        ("control_boundary", "CORRUPTED_BOUNDARY"),
        ("control_boundary", False),
        ("status", "CORRUPTED_STATUS"),
    ],
)
def test_database_receipt_boundary_corruption_fails_closed_on_both_paths(
    field, corrupt
) -> None:
    req = request()
    row = postgres_row(req)
    row["receipt"] = dict(row["receipt"])
    row["receipt"][field] = corrupt
    assert_malformed_database_receipt_is_rejected_on_both_paths(req, row)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("observed_billed_high_water_before_microusd", 10_000_001),
        ("observed_billed_high_water_after_microusd", 9_999_999),
    ],
)
def test_database_receipt_high_water_arithmetic_replays_on_both_paths(
    field, value
) -> None:
    req = request()
    row = postgres_row(req)
    row["receipt"] = dict(row["receipt"])
    row["receipt"][field] = value
    assert_malformed_database_receipt_is_rejected_on_both_paths(req, row)


def test_database_success_decision_requires_exact_known_text() -> None:
    req = request()
    for corrupt in (True, 1.0, "UNEXPECTED_DATABASE_DECISION"):
        row = postgres_row(req)
        row["decision"] = corrupt
        connection = FakeConnection([row])
        with pytest.raises(ActivationBudgetOutcomeIndeterminate):
            PostgresActivationBudgetLedger(connection).reserve_once(req)
        assert len(connection.calls) == 1


def test_postgres_rejection_is_definitive_and_not_retried() -> None:
    req = request()
    connection = FakeConnection([{"decision": "NONCE_ALREADY_CONSUMED"}])
    ledger = PostgresActivationBudgetLedger(connection)
    assert error_code(lambda: ledger.reserve_once(req)) == "NONCE_ALREADY_CONSUMED"
    assert len(connection.calls) == 1


def test_committed_but_malformed_database_receipt_is_indeterminate_not_retryable() -> None:
    req = request()
    malformed = postgres_row(req)
    malformed["receipt"] = dict(malformed["receipt"])
    malformed["receipt"]["projected_total_microusd"] = 10_999_999
    connection = FakeConnection([malformed])
    ledger = PostgresActivationBudgetLedger(connection)

    with pytest.raises(ActivationBudgetOutcomeIndeterminate) as caught:
        ledger.reserve_once(req)
    assert caught.value.operation_id == req.operation_id
    assert len(connection.calls) == 1


def test_ambiguous_mutation_requires_read_only_exact_operation_reconciliation() -> None:
    req = request()
    connection = FakeConnection([TimeoutError("after dispatch"), postgres_row(req)])
    ledger = PostgresActivationBudgetLedger(connection)

    with pytest.raises(ActivationBudgetOutcomeIndeterminate) as caught:
        ledger.reserve_once(req)
    assert caught.value.operation_id == req.operation_id
    assert caught.value.request_sha256 == req.request_sha256
    assert len(connection.calls) == 1

    reconciled = ledger.reconcile_exact_operation(req)
    assert reconciled.operation_id == req.operation_id
    assert len(connection.calls) == 2
    assert connection.calls[1][0] == POSTGRES_RECONCILE_SQL
    assert sum(query == POSTGRES_RESERVE_SQL for query, _ in connection.calls) == 1


def test_reconciliation_absence_or_digest_conflict_never_retries_mutation() -> None:
    req = request()
    wrong = postgres_row(req)
    wrong["request_sha256"] = "B" * 64
    for outcome, expected in [
        (None, "OPERATION_NOT_FOUND_NO_MUTATION_RETRY"),
        (wrong, "OPERATION_REQUEST_DIGEST_MISMATCH"),
    ]:
        connection = FakeConnection([outcome])
        ledger = PostgresActivationBudgetLedger(connection)
        assert error_code(lambda: ledger.reconcile_exact_operation(req)) == expected
        assert [query for query, _ in connection.calls] == [POSTGRES_RECONCILE_SQL]


def test_postgres_sql_contract_owns_time_locks_rows_and_rejects_exact_cap() -> None:
    sql = " ".join(POSTGRES_RESERVE_SQL.lower().split())
    assert sql.count("clock_timestamp()") == 1
    assert "%(server_time)" not in sql and "%(now)" not in sql
    assert "for update of a" in sql
    assert "for update of s" in sql
    assert "for update of o" in sql
    assert "from (select count(*) from existing) operation_lock" in sql
    assert "(select count(*) from a) authorization_lock" in sql
    assert "(select count(*) from s) budget_scope_lock" in sql
    assert "nextval('stagec_activation_budget_generation_seq')" in sql
    high_water_projection = (
        "greatest( i.already_billed, "
        "(select observed_billed_high_water_microusd from s) ) "
        "+ (select reserved_microusd from s) + i.reservation"
    )
    assert high_water_projection in sql
    assert ">= (select hard_cap_microusd from a)" in sql
    assert "i.quoted_rate::numeric * i.duration_seconds::numeric" in sql
    assert "operation_already_recorded_reconcile_only" in sql
    assert "observed_billed_below_scope_high_water" in sql
    assert "observed_billed_high_water_microusd = greatest(" in sql
    assert "'observed_billed_high_water_before_microusd'" in sql
    assert "'observed_billed_high_water_after_microusd'" in sql


def test_postgres_schema_and_reconciliation_are_exact_operation_scoped() -> None:
    schema = " ".join(POSTGRES_SCHEMA_SQL.lower().split())
    read = " ".join(POSTGRES_RECONCILE_SQL.lower().split())
    assert "primary key (tenant_id, operation_id)" in schema
    assert "ledger_generation bigint not null unique" in schema
    assert "nonce_state text not null default 'unconsumed'" in schema
    assert "unique (tenant_id, nonce_b64url)" in schema
    assert "observed_billed_high_water_microusd bigint not null default 0" in schema
    assert "where tenant_id = %(tenant_id)s and operation_id = %(operation_id)s" in read
    assert all(
        word not in POSTGRES_RESERVE_SQL.lower()
        for word in ("runpod", "start_pod", "model_call", "put_object")
    )
    assert "'provider_start_authorized', false" in POSTGRES_RESERVE_SQL.lower()
    assert "'model_start_authorized', false" in POSTGRES_RESERVE_SQL.lower()
    assert "'object_lock_authority', false" in POSTGRES_RESERVE_SQL.lower()
