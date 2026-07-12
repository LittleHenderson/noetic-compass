"""Accounts service -- the identity half of the PAID-user security spine.

Real, durable identity: an :class:`Account` (the entity a JWT is minted against) and an
:class:`InviteCode` (a cryptographically-random, fail-closed redemption credential), both
persisted through the durable ``StateStore`` Protocol. This is NOT the import-isolated billing
stub (``api/services/production/billing.py``); it is wired into the live app behind the
``accounts_enabled`` flag (default off).

Public surface kept small on purpose: the models, the store + its redemption error, and the
``build_account_store`` lifespan helper that selects the same durable backend as the state ledger
and FAILS LOUD when accounts are enabled but no durable backend can be obtained.
"""

from __future__ import annotations

from api.services.production.state_substrate import StateStore

from .invites import generate_invite_code, is_redeemable
from .models import (
    Account,
    AccountStatus,
    DEFAULT_INVITE_ROLE,
    InviteCode,
    Role,
    ROLE_VALUES,
)
from .store import AccountStore, InviteRedemptionError
from .tenant_provisioning import (
    TenantProvisioningError,
    TenantProvisioningResult,
    provision_tenant_owner,
)


def build_account_store(
    settings, *, store: StateStore | None
) -> AccountStore | None:
    """Wrap the lifespan-owned shared persistent store when account mode is enabled.

    This builder never opens or closes a backend. Ownership belongs to the app lifespan, which
    passes the exact same StateStore to accounts, sessions, quotas, and evidence ownership.
    """
    if not getattr(settings, "accounts_enabled", False):
        return None
    if store is None:
        raise RuntimeError("Account mode requires a shared persistent StateStore.")

    from api.services.production.state_substrate import InMemoryStateStore

    if isinstance(store, InMemoryStateStore):
        raise RuntimeError("Account mode refuses the transient in-memory StateStore.")
    return AccountStore(
        store, credential_pepper=settings.account_credential_pepper
    )


__all__ = [
    "Account",
    "AccountStatus",
    "Role",
    "ROLE_VALUES",
    "DEFAULT_INVITE_ROLE",
    "InviteCode",
    "AccountStore",
    "InviteRedemptionError",
    "TenantProvisioningError",
    "TenantProvisioningResult",
    "provision_tenant_owner",
    "build_account_store",
    "generate_invite_code",
    "is_redeemable",
]
