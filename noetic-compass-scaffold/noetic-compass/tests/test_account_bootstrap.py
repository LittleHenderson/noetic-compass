from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from api.services.accounts.bootstrap import AccountBootstrapError
from api.services.accounts.models import ACCOUNT_KIND
from api.services.accounts.store import AccountStore
from api.services.production.state_substrate import InMemoryStateStore


PEPPER = "test-account-credential-pepper-0123456789"
CREDENTIAL = "casak_0123456789abcdefghijklmnopqrstuvwxyzABCDEFG"
BOUNDARIES = (
    "after_bootstrap_reservation_write",
    "after_bootstrap_email_write",
    "after_bootstrap_account_write",
    "after_bootstrap_completion_write",
)


class SimulatedCrash(RuntimeError):
    pass


@pytest.mark.parametrize("boundary", BOUNDARIES)
def test_bootstrap_retry_repairs_each_crash_boundary(boundary: str) -> None:
    backend = InMemoryStateStore()
    fired = False

    def crash_once(observed: str) -> None:
        nonlocal fired
        if not fired and observed == boundary:
            fired = True
            raise SimulatedCrash(boundary)

    crashing = AccountStore(backend, credential_pepper=PEPPER, failure_injector=crash_once)
    with pytest.raises(SimulatedCrash):
        crashing.bootstrap_owner(
            email_or_username="owner@example.com",
            tenant_id="primary",
            api_credential=CREDENTIAL,
        )

    recovered = AccountStore(backend, credential_pepper=PEPPER).bootstrap_owner(
        email_or_username="owner@example.com",
        tenant_id="primary",
        api_credential=CREDENTIAL,
    )
    assert recovered.role == "owner"
    assert len(backend.list("accounts", ACCOUNT_KIND)) == 1
    assert "api_credential" not in repr(backend.list("accounts", ACCOUNT_KIND)[0].payload)


def test_bootstrap_race_creates_exactly_one_owner() -> None:
    backend = InMemoryStateStore()
    store = AccountStore(backend, credential_pepper=PEPPER)

    def create(identity: str):
        try:
            return store.bootstrap_owner(
                email_or_username=identity,
                tenant_id="primary",
                api_credential=CREDENTIAL,
            )
        except AccountBootstrapError as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(create, ("owner-a@example.com", "owner-b@example.com")))
    owners = [result for result in results if not isinstance(result, str)]
    failures = [result for result in results if isinstance(result, str)]
    assert len(owners) == 1
    assert failures == ["already_bootstrapped"]
    assert len(backend.list("accounts", ACCOUNT_KIND)) == 1


def test_completed_bootstrap_requires_original_credential() -> None:
    backend = InMemoryStateStore()
    store = AccountStore(backend, credential_pepper=PEPPER)
    store.bootstrap_owner(
        email_or_username="owner@example.com",
        tenant_id="primary",
        api_credential=CREDENTIAL,
    )
    with pytest.raises(AccountBootstrapError, match="bootstrap_credential_mismatch"):
        store.bootstrap_owner(
            email_or_username="owner@example.com",
            tenant_id="primary",
            api_credential="casak_ZYXWVUTSRQPONMLKJIHGFEDCBA9876543210abcdefgh",
        )
