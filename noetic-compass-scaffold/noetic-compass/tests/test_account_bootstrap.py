from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

from api.services.accounts.bootstrap import AccountBootstrapError
from api.services.accounts.models import ACCOUNT_KIND, Account
from api.services.accounts.store import AccountStore
from api.services.accounts.tenant_provisioning import provision_tenant_owner
from api.services.production.state_substrate import InMemoryStateStore


PEPPER = "test-account-credential-pepper-0123456789"
CREDENTIAL = "casak_0123456789abcdefghijklmnopqrstuvwxyzABCDEFG"
SECOND_CREDENTIAL = "casak_ZYXWVUTSRQPONMLKJIHGFEDCBA9876543210abcdefgh"
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
            api_credential=SECOND_CREDENTIAL,
        )


def test_platform_owner_created_first_does_not_block_primary_bootstrap() -> None:
    backend = InMemoryStateStore()
    store = AccountStore(backend, credential_pepper=PEPPER)

    synthetic = provision_tenant_owner(
        store,
        tenant_id="journey-probe",
        email_or_username="owner@journey-probe.example",
        api_credential=SECOND_CREDENTIAL,
    ).account

    assert store.has_active_owner(tenant_id="journey-probe") is True
    assert store.has_active_owner(tenant_id="primary") is False

    primary = store.bootstrap_owner(
        email_or_username="owner@primary.example",
        tenant_id="primary",
        api_credential=CREDENTIAL,
    )

    assert primary.role == synthetic.role == "owner"
    assert primary.tenant_id == "primary"
    assert synthetic.tenant_id == "journey-probe"
    assert store.has_active_owner(tenant_id="primary") is True
    assert sorted(
        Account.from_payload(record.payload).tenant_id
        for record in backend.list("accounts", ACCOUNT_KIND)
    ) == ["journey-probe", "primary"]


def test_primary_bootstrap_still_rejects_a_second_primary_owner() -> None:
    backend = InMemoryStateStore()
    store = AccountStore(backend, credential_pepper=PEPPER)
    store.bootstrap_owner(
        email_or_username="first@primary.example",
        tenant_id="primary",
        api_credential=CREDENTIAL,
    )

    with pytest.raises(AccountBootstrapError, match="already_bootstrapped"):
        store.bootstrap_owner(
            email_or_username="second@primary.example",
            tenant_id="primary",
            api_credential=SECOND_CREDENTIAL,
        )

    primary_owners = [
        Account.from_payload(record.payload)
        for record in backend.list("accounts", ACCOUNT_KIND)
        if record.payload.get("tenant_id") == "primary"
    ]
    assert len(primary_owners) == 1
    assert primary_owners[0].email_or_username == "first@primary.example"
