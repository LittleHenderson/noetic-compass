"""Crash-boundary and concurrency tests for durable invite redemption reservations."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from api.services.accounts.models import ACCOUNT_EMAIL_INDEX_KIND, ACCOUNT_KIND, INVITE_KIND
from api.services.accounts.store import AccountStore, InviteRedemptionError
from api.services.production.state_substrate import InMemoryStateStore

PEPPER = "test-account-credential-pepper-0123456789"
BOUNDARIES = (
    "after_invite_reservation_write",
    "after_email_index_write",
    "after_account_write",
    "after_invite_completion_write",
)
TEST_API_CREDENTIAL = "casak_0123456789abcdefghijklmnopqrstuvwxyzABCDEFG"
WRONG_API_CREDENTIAL = "casak_ZYXWVUTSRQPONMLKJIHGFEDCBA9876543210abcdefgh"



class SimulatedCrash(RuntimeError):
    pass


@pytest.mark.parametrize("boundary", BOUNDARIES)
def test_retry_repairs_each_crash_boundary_without_double_spend(boundary: str) -> None:
    backend = InMemoryStateStore()
    fired = False

    def crash_once(observed: str) -> None:
        nonlocal fired
        if not fired and observed == boundary:
            fired = True
            raise SimulatedCrash(boundary)

    crashing = AccountStore(
        backend, credential_pepper=PEPPER, failure_injector=crash_once
    )
    invite = crashing.create_invite(code=f"crash-{boundary}", max_uses=1)
    with pytest.raises(SimulatedCrash):
        crashing.redeem_invite(
            code=invite.code, email_or_username="recover@example.com", api_credential=TEST_API_CREDENTIAL
        )

    recovered_store = AccountStore(backend, credential_pepper=PEPPER)
    recovered = recovered_store.redeem_invite(
        code=invite.code, email_or_username="recover@example.com", api_credential=TEST_API_CREDENTIAL
    )
    repeated = recovered_store.redeem_invite(
        code=invite.code, email_or_username="recover@example.com", api_credential=TEST_API_CREDENTIAL
    )

    assert recovered.account_id == repeated.account_id
    assert repeated.api_credential is None
    if boundary == "after_invite_completion_write":
        assert recovered.api_credential is None
    else:
        assert recovered.api_credential == TEST_API_CREDENTIAL
    # The client-held credential survives every response-crash boundary without reissue.
    assert recovered_store.authenticate_account(
        "recover@example.com", TEST_API_CREDENTIAL
    ) == recovered_store.get_account_by_id(recovered.account_id)
    assert recovered_store.get_invite(invite.code).uses == 1
    assert len(backend.list("accounts", ACCOUNT_KIND)) == 1
    assert len(backend.list("accounts", ACCOUNT_EMAIL_INDEX_KIND)) == 1


def test_completed_persistence_contains_hash_but_no_nonce_or_bearer() -> None:
    backend = InMemoryStateStore()
    store = AccountStore(backend, credential_pepper=PEPPER)
    invite = store.create_invite(code="hash-only")
    account = store.redeem_invite(
        code=invite.code, email_or_username="hash-only@example.com", api_credential=TEST_API_CREDENTIAL
    )

    account_record = backend.get("accounts", ACCOUNT_KIND, account.account_id)
    invite_record = backend.list("accounts", INVITE_KIND)[0]
    assert account_record.payload["credential_hash"]
    assert "api_credential" not in account_record.payload
    assert account.api_credential not in repr(account_record.payload)
    assert account.api_credential not in repr(invite_record.payload)
    assert "credential_nonce" not in repr(invite_record.payload)


def test_completed_retry_requires_the_original_client_credential() -> None:
    backend = InMemoryStateStore()
    store = AccountStore(backend, credential_pepper=PEPPER)
    invite = store.create_invite(code="completed-key-check")
    store.redeem_invite(
        code=invite.code,
        email_or_username="completed@example.com",
        api_credential=TEST_API_CREDENTIAL,
    )

    with pytest.raises(InviteRedemptionError) as exc:
        store.redeem_invite(
            code=invite.code,
            email_or_username="completed@example.com",
            api_credential=WRONG_API_CREDENTIAL,
        )
    assert exc.value.reason == "credential_mismatch"


def test_single_use_invite_never_materializes_two_accounts_under_race() -> None:
    backend = InMemoryStateStore()
    store = AccountStore(backend, credential_pepper=PEPPER)
    invite = store.create_invite(code="race-one-use", max_uses=1)

    def redeem(identity: str):
        try:
            return store.redeem_invite(
                code=invite.code, email_or_username=identity, api_credential=TEST_API_CREDENTIAL
            )
        except InviteRedemptionError as exc:
            return exc.reason

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = tuple(
            pool.map(redeem, ("winner-a@example.com", "winner-b@example.com"))
        )

    accounts = [result for result in results if not isinstance(result, str)]
    failures = [result for result in results if isinstance(result, str)]
    assert len(accounts) == 1
    assert failures == ["not_redeemable"]
    assert store.get_invite(invite.code).uses == 1
    assert len(backend.list("accounts", ACCOUNT_KIND)) == 1
