"""Phase 1/2 proof: the live fleet/distributed services dual-write + shadow-read clean.

The seam itself is locked in ``test_state_substrate_migration.py``. This file proves
the *wiring*: with a real :class:`LedgerMirror` installed into the two live services,
driving their genuine service-layer flows leaves the shadow ledger in exact agreement
with the authoritative dicts -- the zero-divergence precondition doc 10 requires before
any cutover. One shared store backs both services, partitioned by ``kind`` (a
``distributed_audit`` and a ``fleet_run`` legitimately share an ``audit_id``; the
(tenant, kind, record_id) triple keeps them distinct), which is the single unified
ledger the migration targets.

What is deliberately exercised beyond the happy path:

* the indirect, clock-triggered lease-expiry helpers (``_expire_worker_leases`` via
  worker staleness, ``_expire_stale_leases`` via an aged lease) -- the paths that mutate
  run state *outside* a run's own mutators and so must re-mirror to stay in sync; and
* the Phase-0 mapping decision that the ledger stores durable STATE, not the rendered
  view: a worker going stale must NOT register as a divergence, because ``status`` is a
  recomputed view excluded from the stored projection.

Run ONLY this file:
    C:/Python314/python.exe -m pytest tests/test_state_substrate_live_migration.py -q
"""

from __future__ import annotations

import pytest

from api.services import cas_harness_distributed_audits as da
from api.services import cas_harness_fleet_executor as fe
from api.services.cas_harness_scale_planner import ScalePlanRequest
from api.services.production.state_substrate import (
    INTERIM_TENANT,
    InMemoryStateStore,
    LedgerMirror,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore


@pytest.fixture
def mirror():
    # A single unified ledger behind both services, exactly as the cutover envisions.
    da.reset_distributed_audits_for_tests()
    fe.reset_fleet_executor_for_tests()
    store = InMemoryStateStore()
    m = LedgerMirror(store)
    da.set_state_mirror(m)
    fe.set_state_mirror(m)
    try:
        yield store, m
    finally:
        da.set_state_mirror(None)
        fe.set_state_mirror(None)
        store.close()


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

    Returns the audit_id. Drives both live services through their real service-layer
    API so every dual-write and shadow-read call site actually fires.
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


def test_full_flow_leaves_zero_divergence(mirror):
    store, m = mirror
    audit_id = _drive_full_flow()

    # Touch every public read path once more so the shadow-read sites all fire.
    da.get_distributed_audit(audit_id)
    da.list_distributed_audits()
    fe.get_fleet_run(audit_id)
    fe.list_fleet_runs()
    fe.list_workers()

    # The Phase-2 gate: the shadow ledger and the live dicts never disagreed.
    m.assert_no_divergence()


def test_full_flow_populates_the_unified_ledger(mirror):
    store, m = mirror
    audit_id = _drive_full_flow()

    # Distinct rows under the shared audit_id, kept apart by `kind`.
    audit_row = store.get(INTERIM_TENANT, "distributed_audit", audit_id)
    run_row = store.get(INTERIM_TENANT, "fleet_run", audit_id)
    assert audit_row is not None and run_row is not None
    assert audit_row.payload != run_row.payload, "shared id, different kinds, different state"

    # Traceability envelope landed on the mirrored records (project-load-bearing).
    assert audit_row.source == "cas_harness_distributed_audits"
    assert audit_row.trace_id == audit_id
    assert run_row.source == "cas_harness_fleet_executor"
    assert run_row.parent_ids == (audit_id,)

    # Every worker and every fragment ref is mirrored too.
    workers = fe.list_workers()
    assert workers, "flow must register workers"
    for w in workers:
        assert store.get(INTERIM_TENANT, "worker", w.worker_id) is not None
    fragments = store.list(INTERIM_TENANT, "fragment_ref")
    assert len(fragments) == len(run_row.payload["jobs"]), "one fragment ref per completed job"

    m.assert_no_divergence()


def test_worker_going_stale_is_not_a_divergence(mirror):
    # The Phase-0 mapping decision under test: `status` is a derived view of
    # (last_heartbeat_at, now), excluded from the stored projection. So a worker aging
    # into 'stale' must NOT perturb its ledger payload, and must NOT register as drift.
    from datetime import UTC, datetime, timedelta

    store, m = mirror
    _drive_full_flow()
    m.assert_no_divergence()

    # Faithfully simulate real clock advance. Unlike `status`, `last_heartbeat_at` is
    # durable STATE and IS mirrored -- so to model "time passed, the last heartbeat is now
    # old" without manufacturing a *false* divergence, age the heartbeat AND re-mirror,
    # leaving live and ledger in agreement on every stored field. (Re-mirroring after the
    # aged heartbeat is exactly what a real heartbeat-at-time-T would have durably written;
    # only the derived `status` view is now left free to flip.)
    aged = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    for w in fe.list_workers():
        w.last_heartbeat_at = aged
        fe._mirror_worker(w)
    m.assert_no_divergence()

    # Now the derived view genuinely flips to 'stale'. This actually fires
    # _expire_worker_leases across every run (all jobs are already completed, so no lease
    # is cleared -- the point is that flipping `status` must not perturb the projection).
    stale = fe.mark_stale_workers(max_heartbeat_age_seconds=60)
    assert stale, "aged workers must really flip to stale, else the rule is tested vacuously"
    assert all(w.status == "stale" for w in fe.list_workers()), "the derived view did flip"

    fe.list_workers()  # shadow-compare every (now-stale) worker against the ledger
    fe.list_fleet_runs()
    m.assert_no_divergence()  # ...yet the status-flip caused zero drift: status isn't stored


def test_lease_expiry_re_mirrors_the_run(mirror):
    # Exercise the _expire_stale_leases path: lease a job, force its lease into the past,
    # then drive a lease attempt so the clock-triggered expiry fires. The run is mutated
    # outside its own mutators, so the seam must re-mirror it -- proven by zero divergence.
    store, m = mirror
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
    job = run.jobs[0]
    leased = fe.lease_next_job(audit_id=audit_id, worker_id=job.assigned_worker_id)
    assert leased is not None
    m.assert_no_divergence()

    # Age the lease into the past directly on the live record, then re-drive a lease for
    # the same worker: lease_next_job calls _expire_stale_leases first.
    from datetime import UTC, datetime, timedelta

    live_job = next(j for j in fe.get_fleet_run(audit_id).jobs if j.job_id == leased.job_id)
    live_job.lease_expires_at = (datetime.now(UTC) - timedelta(seconds=5)).isoformat()
    fe.lease_next_job(audit_id=audit_id, worker_id=job.assigned_worker_id)

    fe.get_fleet_run(audit_id)
    fe.list_fleet_runs()
    m.assert_no_divergence()


def test_mirror_is_dark_when_uninstalled():
    # With no mirror installed (production + every pre-existing test), the wiring is a
    # no-op: the flow runs and nothing is shadowed. This is the zero-behaviour-change
    # guarantee that lets the seam ship before cutover.
    da.reset_distributed_audits_for_tests()
    fe.reset_fleet_executor_for_tests()
    assert da._STATE_MIRROR is None and fe._STATE_MIRROR is None
    audit_id = _drive_full_flow()  # must complete with no mirror installed
    assert da.get_distributed_audit(audit_id) is not None
    assert fe.get_fleet_run(audit_id) is not None


def test_mirrored_ledger_survives_a_single_host_restart(tmp_path):
    # Phase 2 (the tests above) proved the shadow ledger AGREES with the live dicts --
    # on the deliberately non-durable InMemoryStateStore. This is the next honest
    # question, and the single-host half of doc 10's Phase-3 gate: does the mirrored
    # ledger SURVIVE what a process restart destroys? Drive the real flow through the
    # durable SqliteStateStore, then simulate a restart -- drop the in-RAM dicts (the
    # ONLY thing a restart loses) and reopen a brand-new store on the same DB file --
    # and confirm every mirrored record is still there.
    #
    # Honesty boundary: this is single-host durability only (one SQLite file on one
    # disk; multi-host survival is workstream 11), and it is NOT the cutover -- the
    # dicts are still authoritative on the serving path. It is the durability evidence
    # the cutover will require, demonstrated on the one backend whose tests earn the
    # word "durable on a single host".
    db = tmp_path / "live_ledger.db"

    da.reset_distributed_audits_for_tests()
    fe.reset_fleet_executor_for_tests()
    store = SqliteStateStore(db)
    m = LedgerMirror(store)
    da.set_state_mirror(m)
    fe.set_state_mirror(m)
    try:
        audit_id = _drive_full_flow()
        m.assert_no_divergence()  # the real payloads also serialise + round-trip through SQLite
        worker_ids = [w.worker_id for w in fe.list_workers()]
        fragment_ids = {r.record_id for r in store.list(INTERIM_TENANT, "fragment_ref")}
        run_row_live = store.get(INTERIM_TENANT, "fleet_run", audit_id)
        assert worker_ids and fragment_ids and run_row_live is not None
        job_count = len(run_row_live.payload["jobs"])
    finally:
        # --- process-restart analogue: detach the mirror, close the file, and erase
        # the in-RAM dicts, which is exactly the state a restart leaves behind. ---
        da.set_state_mirror(None)
        fe.set_state_mirror(None)
        store.close()
        da.reset_distributed_audits_for_tests()
        fe.reset_fleet_executor_for_tests()

    # The dicts are gone: a restart lost every live record (this is what makes the
    # current single-process design fatal for a public product) ...
    assert da.get_distributed_audit(audit_id) is None
    assert fe.get_fleet_run(audit_id) is None
    assert fe.list_workers() == []

    # ... but the durable ledger kept all of it. Reopen on the same file and read back
    # the audit, its fleet run (with every job), every worker, and every fragment ref.
    reopened = SqliteStateStore(db)
    try:
        audit_row = reopened.get(INTERIM_TENANT, "distributed_audit", audit_id)
        assert audit_row is not None, "the audit must survive the restart in the ledger"
        assert audit_row.source == "cas_harness_distributed_audits"
        assert audit_row.trace_id == audit_id

        run_row = reopened.get(INTERIM_TENANT, "fleet_run", audit_id)
        assert run_row is not None and run_row.parent_ids == (audit_id,)
        assert len(run_row.payload["jobs"]) == job_count, "every job survived the restart"

        for worker_id in worker_ids:
            assert reopened.get(INTERIM_TENANT, "worker", worker_id) is not None, worker_id

        survived = {r.record_id for r in reopened.list(INTERIM_TENANT, "fragment_ref")}
        assert survived == fragment_ids, "every content-addressed fragment ref is durable"
        assert len(survived) == job_count, "one fragment ref per completed job, all recovered"
    finally:
        reopened.close()

    # Leave no mirror installed for sibling tests.
    da.reset_distributed_audits_for_tests()
    fe.reset_fleet_executor_for_tests()
