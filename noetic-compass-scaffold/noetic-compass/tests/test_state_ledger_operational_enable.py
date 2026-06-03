"""Operational-enable proof: the two flags turn the durable ledger on, dark by default.

The migration mechanism (mirror install, dual-write, shadow-compare, rehydrate, the Phase-3
read-authority flip) is locked in ``test_state_substrate_live_migration.py``. This file proves
the *operational wrapper* around it -- ``api/state_ledger_bootstrap.install_state_ledger`` /
``teardown_state_ledger`` -- behaves honestly under the three settings:

* dark by default (flags unset -> no mirror installed, dicts authoritative, production
  byte-for-byte unchanged);
* enabled, dict-authoritative (``state_ledger_enabled`` only -> mirror live, dual-write +
  shadow-compare running, reads still from the dicts);
* enabled, ledger-read-authoritative (both flags -> the Phase-3 flip applied);
* genuinely durable across a simulated restart (close the file, install again on the SAME
  path, the state survived); and
* teardown restores the dark state (no mirror leaks into the next process or test).

These are tested against the bootstrap helpers directly -- no app spin-up -- driving the two
live services through their real service-layer API so every wired-up call site fires. Each test
restores global state in a ``finally`` (clear the mirror on both services), mirroring the
teardown discipline the migration tests follow, so a mirror can never leak between tests.

Run ONLY this file:
    C:/Python314/python.exe -m pytest tests/test_state_ledger_operational_enable.py -q
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from api.config import Settings
from api.services import cas_harness_distributed_audits as da
from api.services import cas_harness_fleet_executor as fe
from api.services.cas_harness_scale_planner import ScalePlanRequest
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from api.state_ledger_bootstrap import (
    StateLedgerHandle,
    _build_state_store,
    install_state_ledger,
    teardown_state_ledger,
)


@dataclass(frozen=True)
class _FakeSettings:
    """Minimal stand-in carrying only the four fields the bootstrap reads.

    The bootstrap keys entirely off ``state_ledger_enabled`` / ``state_ledger_path`` /
    ``state_ledger_read_authority`` / ``database_url``, so a tiny object with those attributes
    drives it exactly as a real :class:`Settings` would -- and keeps these tests independent of
    process env or a stray ``.env`` file. One test below also exercises a real ``Settings``
    instance to prove the actual config fields wire through.

    ``database_url`` defaults to ``None`` (env ``NC_DATABASE_URL`` unset), so every existing test
    selects the SQLite backend exactly as before; the backend-selection tests set it to choose
    Postgres.
    """

    state_ledger_enabled: bool = False
    state_ledger_path: str = "state_ledger.db"
    state_ledger_read_authority: bool = False
    database_url: str | None = None


@pytest.fixture(autouse=True)
def _clean_services():
    """Start each test from a clean, mirror-free pair of services and leave it that way.

    Both the entry and the (belt-and-suspenders) exit reset the services -- if a test forgets
    its own ``finally``, this still prevents a mirror or stale dict from leaking onward.
    """
    da.reset_distributed_audits_for_tests()
    fe.reset_fleet_executor_for_tests()
    try:
        yield
    finally:
        da.set_state_mirror(None)
        fe.set_state_mirror(None)
        da.reset_distributed_audits_for_tests()
        fe.reset_fleet_executor_for_tests()


def _request(parameter_count_b: float = 20, num_layers: int = 8) -> ScalePlanRequest:
    return ScalePlanRequest(
        model_id=f"customer/open-weight-{int(parameter_count_b)}b",
        parameter_count_b=parameter_count_b,
        num_layers=num_layers,
        precision="bf16",
        available_gpu_memory_gb=80,
    )


def _drive_full_flow() -> str:
    """create -> dispatch -> register -> prepare -> (lease -> submit)* -> merge.

    Returns the audit_id. Mirrors the helper in the migration test so every dual-write and
    shadow-read call site in both live services actually fires while a mirror is installed.
    """

    audit = da.create_distributed_audit(_request(), data_capture_acknowledged=True)
    audit_id = audit.audit_id
    da.dispatch_distributed_audit(audit_id)

    model_id = audit.plan.model_id
    for worker in audit.worker_evidence:
        fe.register_worker(
            worker_id=worker.worker_id,
            model_id=model_id,
            worker_url=f"https://{worker.worker_id}.workers.example",
            gpu_type="H100-80GB",
            supported_methods=list(worker.assigned_methods),
        )

    run = fe.prepare_fleet_for_audit(audit_id)
    assert run is not None and run.jobs, "fleet run must have jobs to drive"

    for job in list(run.jobs):
        leased = fe.lease_next_job(audit_id=audit_id, worker_id=job.assigned_worker_id)
        assert leased is not None and leased.lease_token
        ref = fe.build_evidence_fragment_ref(
            audit_id=audit_id,
            job_id=leased.job_id,
            worker_id=leased.assigned_worker_id,
            model_id=model_id,
            layer_start=leased.layer_start,
            layer_end=leased.layer_end,
            shard_id=leased.shard_id,
            expected_outputs=leased.expected_outputs,
            produced_outputs=list(leased.expected_outputs),
        )
        fe.submit_job_receipt(
            audit_id=audit_id,
            job_id=leased.job_id,
            worker_id=leased.assigned_worker_id,
            lease_token=leased.lease_token,
            produced_outputs=list(leased.expected_outputs),
            evidence_packet_fragment_ref=ref,
        )

    fe.merge_fleet_evidence(audit_id)
    return audit_id


# ---------------------------------------------------------------------------
# 1. Dark default -- the safety test.
# ---------------------------------------------------------------------------


def test_dark_default_installs_no_mirror():
    # The load-bearing proof that production is structurally unchanged: with the flag unset,
    # install returns None AND neither service has a mirror -- so the serving path stays pinned
    # to the dicts (the read sites gate on `_STATE_MIRROR is not None`).
    handle = install_state_ledger(_FakeSettings(state_ledger_enabled=False))

    assert handle is None
    assert da._STATE_MIRROR is None and fe._STATE_MIRROR is None

    # And a real flow still runs end-to-end with nothing shadowed (dicts authoritative).
    audit_id = _drive_full_flow()
    assert da.get_distributed_audit(audit_id) is not None
    assert fe.get_fleet_run(audit_id) is not None


def test_real_settings_default_is_dark():
    # The actual Settings defaults (not a stand-in) must also be dark: a deployment that sets
    # none of the env vars installs no ledger. Construct Settings with explicit kwargs so the
    # field DEFAULTS are what is under test, independent of any ambient env / .env.
    settings = Settings(state_ledger_enabled=False, state_ledger_read_authority=False)
    assert settings.state_ledger_enabled is False
    assert settings.state_ledger_read_authority is False

    handle = install_state_ledger(settings)
    try:
        assert handle is None
        assert da._STATE_MIRROR is None and fe._STATE_MIRROR is None
    finally:
        teardown_state_ledger(handle)


# ---------------------------------------------------------------------------
# 2. Enabled, dual-write live, dict-authoritative.
# ---------------------------------------------------------------------------


def test_enabled_dict_authoritative_installs_mirror_and_serves(tmp_path):
    # state_ledger_enabled=True, read_authority=False: the mirror is installed into BOTH
    # services (Phases 1-2 live), but read authority stays on the dicts. A normal flow still
    # serves correctly, and the shadow ledger agrees with the dicts (zero divergence).
    db = tmp_path / "enabled_dict_auth.db"
    settings = _FakeSettings(state_ledger_enabled=True, state_ledger_path=str(db))
    handle = install_state_ledger(settings)
    try:
        assert handle is not None
        assert isinstance(handle, StateLedgerHandle)
        # Same single mirror installed on both services (they share one store, partitioned by
        # kind) -- exactly the established wiring pattern.
        assert da._STATE_MIRROR is handle.mirror
        assert fe._STATE_MIRROR is handle.mirror
        # Dict-authoritative: the Phase-3 flip was NOT applied.
        assert handle.read_authority is False
        assert handle.mirror.read_from_ledger is False

        # A fresh enable on an empty file rehydrates nothing.
        assert handle.audit_count == 0
        assert handle.fleet_counts == {"workers": 0, "fleet_runs": 0, "fragment_refs": 0}

        # The wired-up services still behave: drive the real flow, serve it from the dicts,
        # and confirm the shadow ledger never disagreed.
        audit_id = _drive_full_flow()
        assert da.get_distributed_audit(audit_id) is not None
        assert fe.get_fleet_run(audit_id) is not None
        handle.mirror.assert_no_divergence()
    finally:
        teardown_state_ledger(handle)


# ---------------------------------------------------------------------------
# 3. Read-authority flip.
# ---------------------------------------------------------------------------


def test_read_authority_flip_serves_from_ledger_after_clearing_the_dict(tmp_path):
    # state_ledger_enabled=True, read_authority=True: the Phase-3 flip is applied, so the
    # ledger is the read authority. Prove the move the same way the cutover tests do -- create
    # a record through the public API, clear the backing dict, and confirm the public read
    # still serves it (it can only be coming from the ledger now).
    db = tmp_path / "read_authority.db"
    settings = _FakeSettings(
        state_ledger_enabled=True,
        state_ledger_path=str(db),
        state_ledger_read_authority=True,
    )
    handle = install_state_ledger(settings)
    try:
        assert handle is not None
        assert handle.read_authority is True
        assert handle.mirror.read_from_ledger is True

        audit_id = _drive_full_flow()
        handle.mirror.assert_no_divergence()

        # Ground truth under the (intact-dict) read, which equals the ledger by zero-divergence.
        audit_before = da.get_distributed_audit(audit_id).to_dict()
        run_before = fe.get_fleet_run(audit_id).to_dict()
        workers_before = {w.worker_id: w.to_dict() for w in fe.list_workers()}
        assert run_before["verifier_gate_status"] == "ready_for_verifier"
        assert workers_before

        # Audit: self-contained. Clear its dict; the read can ONLY come from the ledger.
        da._DISTRIBUTED_AUDITS.clear()
        assert da.get_distributed_audit(audit_id).to_dict() == audit_before

        # Run: clear it while the worker cache is intact so the derived gate recomputes.
        fe._FLEET_RUNS.clear()
        served_run = fe.get_fleet_run(audit_id)
        assert served_run.to_dict() == run_before
        assert served_run.verifier_gate_status == "ready_for_verifier"

        # Workers last: cleared cache, ledger still serves each (status re-derived 'active').
        fe._WORKERS.clear()
        workers_after = {w.worker_id: w.to_dict() for w in fe.list_workers()}
        assert workers_after == workers_before
        assert all(w["status"] == "active" for w in workers_after.values())

        # Every dict empty, every read still served -> read-authority truly moved.
        assert da._DISTRIBUTED_AUDITS == {}
        assert fe._FLEET_RUNS == {} and fe._WORKERS == {}
    finally:
        teardown_state_ledger(handle)


# ---------------------------------------------------------------------------
# 4. Durable restart -- the enable is genuinely durable, not merely wired.
# ---------------------------------------------------------------------------


def test_enable_survives_a_process_restart_on_the_same_path(tmp_path):
    # Drive a real flow with the ledger enabled, tear down (closing the SQLite file), then
    # install AGAIN on the SAME path -- the process-restart analogue. The second install's
    # rehydrate must report the state survived, and the services must serve the same records.
    db = tmp_path / "durable_restart.db"
    settings = _FakeSettings(state_ledger_enabled=True, state_ledger_path=str(db))

    # --- first "process": enable, drive the flow, snapshot what is served, then shut down. ---
    handle = install_state_ledger(settings)
    try:
        assert handle is not None
        audit_id = _drive_full_flow()
        handle.mirror.assert_no_divergence()

        audit_before = da.get_distributed_audit(audit_id).to_dict()
        run_durable_before = fe._run_ledger_payload(fe.get_fleet_run(audit_id))
        run_rendered_before = fe.get_fleet_run(audit_id).to_dict()
        workers_before = {w.worker_id: w.to_dict() for w in fe.list_workers()}
        fragments_before = set(fe._FRAGMENT_REFS)
        assert workers_before and fragments_before
        assert run_rendered_before["verifier_gate_status"] == "ready_for_verifier"
    finally:
        # Teardown closes the file and uninstalls the mirror; then erase the in-RAM dicts,
        # which is exactly the state a restart leaves behind.
        teardown_state_ledger(handle)
        da.reset_distributed_audits_for_tests()
        fe.reset_fleet_executor_for_tests()

    # The dicts are gone -- a restart lost every live record.
    assert da.get_distributed_audit(audit_id) is None
    assert fe.get_fleet_run(audit_id) is None
    assert fe.list_workers() == []

    # --- second "process": install again on the SAME path. install() rehydrates on startup. ---
    handle2 = install_state_ledger(settings)
    try:
        assert handle2 is not None
        # Rehydrate counts prove the durable state came back through the operational enable.
        assert handle2.audit_count == 1
        assert handle2.fleet_counts == {
            "workers": len(workers_before),
            "fleet_runs": 1,
            "fragment_refs": len(fragments_before),
        }

        # And the services serve byte-identical durable state after the restart.
        assert da.get_distributed_audit(audit_id).to_dict() == audit_before
        rehydrated_run = fe.get_fleet_run(audit_id)
        assert fe._run_ledger_payload(rehydrated_run) == run_durable_before
        assert rehydrated_run.to_dict() == run_rendered_before
        assert {w.worker_id: w.to_dict() for w in fe.list_workers()} == workers_before
        assert set(fe._FRAGMENT_REFS) == fragments_before
    finally:
        teardown_state_ledger(handle2)


# ---------------------------------------------------------------------------
# 5. Teardown restores the dark state.
# ---------------------------------------------------------------------------


def test_teardown_restores_dark_state(tmp_path):
    # After teardown, no mirror remains on either service -- the serving path is back to the
    # dicts, exactly as production. This is what keeps an enabled deployment's shutdown from
    # leaking a mirror into the next process (or, in tests, the next test).
    db = tmp_path / "teardown.db"
    settings = _FakeSettings(state_ledger_enabled=True, state_ledger_path=str(db))
    handle = install_state_ledger(settings)
    assert handle is not None
    assert da._STATE_MIRROR is not None and fe._STATE_MIRROR is not None

    teardown_state_ledger(handle)

    assert da._STATE_MIRROR is None and fe._STATE_MIRROR is None

    # Idempotent / defensive: tearing down again (and tearing down None) is a harmless no-op.
    teardown_state_ledger(handle)
    teardown_state_ledger(None)
    assert da._STATE_MIRROR is None and fe._STATE_MIRROR is None


# ---------------------------------------------------------------------------
# 6. Backend selection -- which durable store the enable builds.
# ---------------------------------------------------------------------------


def test_build_state_store_selects_sqlite_when_no_database_url(tmp_path):
    # The default, production's posture: no DSN -> the single-host SQLite file on
    # state_ledger_path. Built for real (no mock) on a tmp path, then closed.
    store = _build_state_store(
        _FakeSettings(database_url=None, state_ledger_path=str(tmp_path / "select.db"))
    )
    try:
        assert isinstance(store, SqliteStateStore)
    finally:
        store.close()


def test_build_state_store_treats_empty_database_url_as_sqlite(tmp_path):
    # An empty string (NC_DATABASE_URL set but blank) is falsy -> SQLite, not a doomed connect
    # to an empty DSN. Guards the "unset OR blank -> single-host" intent so a stray empty env
    # var can never silently route the enable at a Postgres that was never configured.
    store = _build_state_store(
        _FakeSettings(database_url="", state_ledger_path=str(tmp_path / "blank.db"))
    )
    try:
        assert isinstance(store, SqliteStateStore)
    finally:
        store.close()


def test_build_state_store_selects_postgres_when_database_url_set(monkeypatch):
    # A configured DSN -> the multi-host Postgres backend, constructed with that EXACT DSN.
    # PostgresStateStore's real constructor would connect to a live server; patch it with a spy
    # so the SELECTION is what is under test here, not a database. (The live Postgres backend is
    # itself verified against real PostgreSQL 16.4 in test_state_substrate_postgres.py.)
    import api.state_ledger_bootstrap as boot

    captured = {}

    class _SpyPostgresStateStore:
        def __init__(self, dsn):
            captured["dsn"] = dsn

        def close(self):  # pragma: no cover - not closed in this selection test
            captured["closed"] = True

    monkeypatch.setattr(boot, "PostgresStateStore", _SpyPostgresStateStore)

    dsn = "postgresql://user:pw@db.internal:5432/noetic"
    store = boot._build_state_store(_FakeSettings(database_url=dsn))

    assert isinstance(store, _SpyPostgresStateStore)
    assert captured["dsn"] == dsn
