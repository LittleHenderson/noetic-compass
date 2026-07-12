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
            code=invite.code, email_or_username="recover@example.com"
        )

    recovered_store = AccountStore(backend, credential_pepper=PEPPER)
    recovered = recovered_store.redeem_invite(
        code=invite.code, email_or_username="recover@example.com"
    )
    repeated = recovered_store.redeem_invite(
        code=invite.code, email_or_username="recover@example.com"
    )

    assert recovered.account_id == repeated.account_id
    assert recovered.api_credential == repeated.api_credential
    assert recovered.api_credential
    assert recovered_store.authenticate_account(
        "recover@example.com", recovered.api_credential
    ) == recovered_store.get_account_by_id(recovered.account_id)
    assert recovered_store.get_invite(invite.code).uses == 1
    assert len(backend.list("accounts", ACCOUNT_KIND)) == 1
    assert len(backend.list("accounts", ACCOUNT_EMAIL_INDEX_KIND)) == 1


def test_persistence_contains_hash_and_nonce_but_never_bearer_credential() -> None:
    backend = InMemoryStateStore()
    store = AccountStore(backend, credential_pepper=PEPPER)
    invite = store.create_invite(code="hash-only")
    account = store.redeem_invite(
        code=invite.code, email_or_username="hash-only@example.com"
    )

    account_record = backend.get("accounts", ACCOUNT_KIND, account.account_id)
    invite_record = backend.list("accounts", INVITE_KIND)[0]
    assert account_record.payload["credential_hash"]
    assert "api_credential" not in account_record.payload
    assert account.api_credential not in repr(account_record.payload)
    assert account.api_credential not in repr(invite_record.payload)


def test_single_use_invite_never_materializes_two_accounts_under_race() -> None:
    backend = InMemoryStateStore()
    store = AccountStore(backend, credential_pepper=PEPPER)
    invite = store.create_invite(code="race-one-use", max_uses=1)

    def redeem(identity: str):
        try:
            return store.redeem_invite(
                code=invite.code, email_or_username=identity
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
