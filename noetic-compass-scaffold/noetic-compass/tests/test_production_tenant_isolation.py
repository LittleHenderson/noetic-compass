"""Tests for the workstream-06 tenant-isolation scaffold.

The centerpiece is ``test_cross_tenant_get_is_denied_fail_closed``: tenant B,
holding a perfectly valid context, MUST NOT be able to read tenant A's value ---
the kill-gate the blueprint (section 3, Phase B) requires to fail closed.

These tests assert the stub's HONEST scope only: logical (in-process) isolation
and the fail-closed contract. They do NOT assert at-rest encryption or
durability --- the stub neither provides nor claims those.
"""

from __future__ import annotations

import pytest

from api.services.production.tenant_isolation import (
    CrossTenantAccessError,
    InMemoryTenantKeyProvider,
    InMemoryTenantScopedStore,
    IsolationGuard,
    QuotaError,
    QuotaPolicy,
    TenantContext,
    TenantResolutionError,
    TenantScopedStore,
)


# --- TenantContext fails closed on ambiguity --------------------------------- #
def test_tenant_context_rejects_empty_tenant_id():
    with pytest.raises(TenantResolutionError):
        TenantContext(tenant_id="", principal="alice")
    with pytest.raises(TenantResolutionError):
        TenantContext(tenant_id="   ", principal="alice")


def test_tenant_context_rejects_empty_principal():
    with pytest.raises(TenantResolutionError):
        TenantContext(tenant_id="acme", principal="")


# --- The store satisfies the Protocol (drop-in seam) ------------------------- #
def test_in_memory_store_satisfies_protocol():
    store: TenantScopedStore = InMemoryTenantScopedStore()
    assert isinstance(store, TenantScopedStore)


# --- Same-tenant round-trip works ------------------------------------------- #
def test_same_tenant_round_trip():
    store: InMemoryTenantScopedStore[str] = InMemoryTenantScopedStore()
    acme = TenantContext(tenant_id="acme", principal="alice")
    store.put(acme, "audit-1", "acme-secret-verdict")
    assert store.get(acme, "audit-1") == "acme-secret-verdict"
    assert store.list_for_tenant(acme) == ["acme-secret-verdict"]


# --- THE LOAD-BEARING TEST: cross-tenant read denied, fail closed ------------ #
def test_cross_tenant_get_is_denied_fail_closed():
    """Tenant B, with a valid context and tenant A's real key, gets None ---
    never A's value, and never a signal that the id exists elsewhere."""
    store: InMemoryTenantScopedStore[str] = InMemoryTenantScopedStore()
    acme = TenantContext(tenant_id="acme", principal="alice")
    globex = TenantContext(tenant_id="globex", principal="mallory")

    store.put(acme, "audit-1", "acme-secret-verdict")

    # Globex knows the exact key "audit-1" but is a different tenant.
    assert store.get(globex, "audit-1") is None, "cross-tenant read MUST NOT return another tenant's value"

    # And Globex's tenant-scoped listing never contains Acme's record.
    assert store.list_for_tenant(globex) == []

    # The data really is there (under Acme) --- proving the None above is isolation,
    # not absence. The global view (test-only) sees one entry; the per-tenant view does not.
    assert store._total_entries_all_tenants() == 1
    assert store.get(acme, "audit-1") == "acme-secret-verdict"


def test_cross_tenant_delete_does_not_touch_other_tenant():
    store: InMemoryTenantScopedStore[str] = InMemoryTenantScopedStore()
    acme = TenantContext(tenant_id="acme", principal="alice")
    globex = TenantContext(tenant_id="globex", principal="mallory")
    store.put(acme, "audit-1", "acme-secret-verdict")

    # Globex deleting "audit-1" must be a no-op against Acme's data.
    assert store.delete(globex, "audit-1") is False
    assert store.get(acme, "audit-1") == "acme-secret-verdict"


# --- IsolationGuard fail-closed contract ------------------------------------- #
def test_guard_allows_same_tenant():
    acme = TenantContext(tenant_id="acme", principal="alice")
    IsolationGuard.assert_same_tenant(acme, "acme")  # no raise


def test_guard_denies_different_tenant():
    acme = TenantContext(tenant_id="acme", principal="alice")
    with pytest.raises(CrossTenantAccessError):
        IsolationGuard.assert_same_tenant(acme, "globex")


def test_guard_denies_when_owner_tenant_is_none_or_blank():
    """Ambiguous ownership (None/blank owning tenant) is a DENIAL, not a pass.
    This is the fail-closed behavior the legacy un-tenanted ``_DISTRIBUTED_AUDITS``
    records must hit until migrated (blueprint section 7, Q5)."""
    acme = TenantContext(tenant_id="acme", principal="alice")
    with pytest.raises(CrossTenantAccessError):
        IsolationGuard.assert_same_tenant(acme, None)
    with pytest.raises(CrossTenantAccessError):
        IsolationGuard.assert_same_tenant(acme, "  ")


# --- TenantKeyProvider: per-tenant key boundary, honest about NOT being crypto - #
def test_key_provider_round_trips_for_owning_tenant():
    kp = InMemoryTenantKeyProvider()
    acme = TenantContext(tenant_id="acme", principal="alice")
    plaintext = b"pooled_hidden_state_activations bytes"
    ciphertext = kp.wrap(acme, plaintext)
    assert ciphertext != plaintext
    assert kp.unwrap(acme, ciphertext) == plaintext


def test_key_provider_foreign_tenant_cannot_recover_plaintext():
    kp = InMemoryTenantKeyProvider()
    acme = TenantContext(tenant_id="acme", principal="alice")
    globex = TenantContext(tenant_id="globex", principal="mallory")
    plaintext = b"pooled_hidden_state_activations bytes"
    ciphertext = kp.wrap(acme, plaintext)
    # Different tenant key -> cannot recover Acme's plaintext.
    assert kp.unwrap(globex, ciphertext) != plaintext
    assert kp.data_key(acme) != kp.data_key(globex)


def test_key_provider_is_honest_about_not_being_kms_backed():
    """The stub must NEVER imply cryptographic isolation it does not have ---
    supports_kms() is the gate that blocks any *_KEY_KMS_BACKED status."""
    kp = InMemoryTenantKeyProvider()
    assert kp.supports_kms() is False


# --- QuotaPolicy: per-tenant, attributable, fail-closed at the cap ----------- #
def test_quota_concurrent_audits_blocks_at_cap_and_is_attributable():
    policy = QuotaPolicy(tenant_id="acme", max_concurrent_audits=2)
    policy.check_concurrent_audits(1)  # under cap, no raise
    with pytest.raises(QuotaError) as exc:
        policy.check_concurrent_audits(2)  # at cap -> refuse
    assert exc.value.tenant_id == "acme"
    assert exc.value.limit_name == "max_concurrent_audits"


def test_quota_zero_means_unlimited():
    policy = QuotaPolicy(tenant_id="acme")  # all limits default 0 == unlimited
    policy.check_concurrent_audits(10_000)  # no raise
    policy.check_worker_fanout(512)  # no raise


def test_quota_worker_fanout_blocks_over_cap():
    policy = QuotaPolicy(tenant_id="acme", max_worker_fanout=64)
    policy.check_worker_fanout(64)  # exactly at cap is allowed
    with pytest.raises(QuotaError):
        policy.check_worker_fanout(65)  # one tenant cannot starve the 512-worker fleet
