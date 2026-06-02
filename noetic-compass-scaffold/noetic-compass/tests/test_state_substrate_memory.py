"""Contract tests for the in-memory reference ``StateStore``.

The bulk of the behavioural assertions live in the backend-agnostic
``run_state_store_contract`` suite -- this file proves the *reference* backend
passes it, plus a couple of properties specific to an in-memory store (instance
isolation, and that ``close`` really does drop state).

Run ONLY this file:
    C:/Python314/python.exe -m pytest tests/test_state_substrate_memory.py -q
"""

from __future__ import annotations

import pytest

from api.services.production.state_substrate import (
    InMemoryStateStore,
    LedgerRecord,
    StateStoreError,
    run_state_store_contract,
)


def test_inmemory_passes_state_store_contract():
    # The headline assertion: the reference backend satisfies every behaviour the
    # Protocol promises. A durable backend earns the right to be substituted by
    # passing this same call.
    run_state_store_contract(InMemoryStateStore)


def test_instances_are_isolated():
    # Two stores share no state -- there is no hidden process-global behind them.
    # (This is exactly the property the live `_DISTRIBUTED_AUDITS` global lacks.)
    a = InMemoryStateStore()
    b = InMemoryStateStore()
    a.put(
        LedgerRecord.new(tenant_id="t", kind="run", record_id="r-1", payload={"n": 1}),
        expected_version=0,
    )
    assert a.get("t", "run", "r-1") is not None
    assert b.get("t", "run", "r-1") is None


def test_close_is_idempotent_and_blocks_use():
    store = InMemoryStateStore()
    store.put(
        LedgerRecord.new(tenant_id="t", kind="run", record_id="r-1", payload={}),
        expected_version=0,
    )
    store.close()
    store.close()  # idempotent: no raise
    # Use-after-close is a loud error, not a silent operation on dropped state.
    with pytest.raises(StateStoreError):
        store.get("t", "run", "r-1")


def test_non_durability_is_explicit():
    # A new store does not somehow recover a prior store's records. In-memory has no
    # persistence; this test documents that as an intended, asserted property rather
    # than an accident -- the durable backends are the ones that must NOT pass an
    # analogous "fresh instance sees nothing" test against the same storage.
    first = InMemoryStateStore()
    first.put(
        LedgerRecord.new(tenant_id="t", kind="run", record_id="r-1", payload={"persisted": False}),
        expected_version=0,
    )
    second = InMemoryStateStore()
    assert second.get("t", "run", "r-1") is None
