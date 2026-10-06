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

Phase-3 prerequisites proved here too: the ledger does not just AGREE with and SURVIVE a
restart -- a restarted process can REBUILD the live dicts from it. Three tests drive the
real flow through the durable SqliteStateStore, drop the in-RAM dicts (all a restart
loses), and call ``rehydrate_from_ledger`` on both services, then assert the services serve
the same records -- with two honest restart consequences made explicit: an in-flight lease
is dropped (``leased`` -> ``expired``; the token is never persisted) and the non-durable
fragment-payload digest is dropped (the content-addressed ref survives).

The cutover itself -- the read-authority flip -- is proved in the final block. With
``enable_ledger_reads`` the public ``get_*`` / ``list_*`` reconstruct each record's stored
state from the ledger instead of the dict, demonstrated by clearing the dict and still
serving byte-identical state; the flip is reversible (``disable_ledger_reads`` returns to
dict-authority), dark by default (the switch is the only thing that serves the ledger, and
it starts off), and rollback-safe (the dual-write writes the dict back, so it stays a
faithful cache the instant we revert). This is the MECHANISM, shipped dark: production
installs no mirror, so the ``_STATE_MIRROR is not None and read_from_ledger`` guard can
never engage there -- the serving path stays structurally pinned to the dicts. Turning it
on in a durable deployment, and Phase 4 (deleting the dicts), remain separate human-gated
steps; multi-host durability is still workstream 11.

Run ONLY this file:
    C:/Python314/python.exe -m pytest tests/test_state_substrate_live_migration.py -q
"""

from __future__ import annotations

import hashlib
import json
import pytest

from api.services import cas_harness_distributed_audits as da
from api.services import cas_harness_fleet_executor as fe
from api.services.cas_harness_scale_planner import ScalePlanRequest
from api.services.cas_harness_model_provenance import ModelProvenanceManifest, WeightFileRef
from api.services.production.state_substrate import (
    INTERIM_TENANT,
    InMemoryStateStore,
    LedgerMirror,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore


MODEL_REVISION = "a" * 40
MANIFEST_PATH = "/workspace/model-artifacts.json"
MANIFEST_SHA256 = "b" * 64


def _model_attestation(audit_id: str, job, model_id: str) -> dict:
    artifacts = [{"path": "config.json", "sha256": "c" * 64, "byte_count": 1}]
    artifact_set_sha256 = hashlib.sha256(
        json.dumps(artifacts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "status": "real_model_forward_completed",
        "audit_id": audit_id,
        "job_id": job.job_id,
        "worker_id": job.assigned_worker_id,
        "model_id": model_id,
        "model_revision": MODEL_REVISION,
        "shard_id": job.shard_id,
        "layer_start": job.layer_start,
        "layer_end": job.layer_end,
        "model_info": {
            "artifact_identity": {
                "manifest_path": MANIFEST_PATH,
                "manifest_sha256": MANIFEST_SHA256,
                "artifact_count": 1,
                "artifact_set_sha256": artifact_set_sha256,
                "artifacts": artifacts,
                "all_artifacts_hash_verified": True,
                "post_load_reverified": True,
                "local_files_only": True,
                "trust_remote_code": False,
                "use_safetensors": True,
            }
        },
    }


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

    request = _request()
    audit = da.create_distributed_audit(
        request,
        data_capture_acknowledged=True,
        provenance=ModelProvenanceManifest(
            model_id=request.model_id,
            source_uri="https://models.example.test/open-weight",
            license_id="apache-2.0",
            revision=MODEL_REVISION,
            weight_files=(
                WeightFileRef(path="model.safetensors", sha256="d" * 64, size_bytes=1),
            ),
        ),
    )
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

    run = fe.prepare_fleet_for_audit(
        audit_id,
        model_revision=MODEL_REVISION,
        model_artifact_manifest_path=MANIFEST_PATH,
        model_artifact_manifest_sha256=MANIFEST_SHA256,
    )
    assert run is not None and run.jobs, "fleet run must have jobs to drive"

    for job in list(run.jobs):
        leased = fe.lease_next_job(audit_id=audit_id, worker_id=job.assigned_worker_id)
        assert leased is not None and leased.lease_token
        evidence_payload = _model_attestation(audit_id, leased, model_id)
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
            evidence_packet_fragment_payload=evidence_payload,
            execution_mode="external_probe_command",
        )
        fe.submit_job_receipt(
            audit_id=audit_id,
            job_id=leased.job_id,
            worker_id=leased.assigned_worker_id,
            lease_token=leased.lease_token,
            produced_outputs=list(leased.expected_outputs),
            evidence_packet_fragment_ref=ref,
            evidence_packet_fragment_payload=evidence_payload,
            execution_mode="external_probe_command",
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


def test_rehydrate_rebuilds_every_dict_from_the_ledger(tmp_path):
    # docs 10 Phase-3 cutover PREREQUISITE. The sibling test proved the ledger SURVIVES a
    # restart; this proves the read inverse -- rehydrate_from_ledger reads that surviving
    # ledger back into _DISTRIBUTED_AUDITS / _WORKERS / _FLEET_RUNS / _FRAGMENT_REFS so the
    # two live services serve byte-identical durable state afterwards. This is exactly the
    # gate named: "when the service restarts, it reads the ledger and rebuilds [the four
    # dicts]. Only after that passes should we move read-authority off the dicts." It is the
    # prerequisite, NOT the cutover -- the dicts are still authoritative on the serving path.
    db = tmp_path / "rehydrate_ledger.db"

    da.reset_distributed_audits_for_tests()
    fe.reset_fleet_executor_for_tests()
    store = SqliteStateStore(db)
    m = LedgerMirror(store)
    da.set_state_mirror(m)
    fe.set_state_mirror(m)
    try:
        audit_id = _drive_full_flow()
        m.assert_no_divergence()

        # Snapshot exactly what the services SERVE before the restart.
        #  * the audit's rendered view is fully clock-independent durable state, so it must
        #    round-trip byte-for-byte (reconstructed via ScalePlan.from_dict + faithful
        #    summary re-servers);
        #  * the run is captured two ways -- its durable projection (the contract the ledger
        #    stores) and its full rendered view (durable state PLUS the gate / readiness views
        #    recomputed on read), which must also reproduce because every input to those views
        #    (jobs, active workers) round-trips;
        #  * worker `status` is a derived staleness view, re-derived from the durable heartbeat
        #    (fresh here -> 'active').
        audit_before = da.get_distributed_audit(audit_id).to_dict()
        audit_list_before = [a.audit_id for a in da.list_distributed_audits()]
        run_durable_before = fe._run_ledger_payload(fe.get_fleet_run(audit_id))
        run_rendered_before = fe.get_fleet_run(audit_id).to_dict()
        workers_before = {w.worker_id: w.to_dict() for w in fe.list_workers()}
        fragments_before = set(fe._FRAGMENT_REFS)
        assert workers_before and fragments_before
        assert run_rendered_before["verifier_gate_status"] == "ready_for_verifier"
    finally:
        # Process-restart analogue: detach the mirror, close the file, erase the dicts.
        da.set_state_mirror(None)
        fe.set_state_mirror(None)
        store.close()
        da.reset_distributed_audits_for_tests()
        fe.reset_fleet_executor_for_tests()

    # The dicts are gone -- a restart lost every live record ...
    assert da.get_distributed_audit(audit_id) is None
    assert fe.get_fleet_run(audit_id) is None
    assert fe.list_workers() == []

    # ... so rehydrate from the durable ledger exactly as startup would, then drop the store
    # handle. Closing it BEFORE the assertions proves rehydrate fully copied into RAM and does
    # not lazily depend on the store still being open.
    reopened = SqliteStateStore(db)
    try:
        audit_count = da.rehydrate_from_ledger(reopened)
        fleet_counts = fe.rehydrate_from_ledger(reopened)
    finally:
        reopened.close()

    assert audit_count == 1
    assert fleet_counts == {
        "workers": len(workers_before),
        "fleet_runs": 1,
        "fragment_refs": len(fragments_before),
    }

    # The audit serves byte-identically: its to_dict() is clock-independent durable state.
    assert da.get_distributed_audit(audit_id).to_dict() == audit_before
    assert [a.audit_id for a in da.list_distributed_audits()] == audit_list_before

    # Durable state round-trips exactly. The rendered gate deliberately tightens after
    # restart because the run ledger does not retain the raw model attestation payload;
    # a content-addressed ref alone is not replay evidence.
    rehydrated_run = fe.get_fleet_run(audit_id)
    assert fe._run_ledger_payload(rehydrated_run) == run_durable_before
    rehydrated_view = rehydrated_run.to_dict()
    assert rehydrated_view["verifier_gate_status"] == "blocked_unattested_model"
    assert rehydrated_view["readiness"]["status"] == "blocked"
    assert all(
        job["evidence_packet_fragment_payload_sha256"] is None
        for job in rehydrated_view["jobs"]
    )

    # Workers serve identically, including the re-derived 'active' status (fresh heartbeat).
    workers_after = {w.worker_id: w.to_dict() for w in fe.list_workers()}
    assert workers_after == workers_before
    assert all(w["status"] == "active" for w in workers_after.values())

    # Every content-addressed fragment ref is back.
    assert set(fe._FRAGMENT_REFS) == fragments_before

    # Leave no mirror installed for sibling tests.
    da.reset_distributed_audits_for_tests()
    fe.reset_fleet_executor_for_tests()


def test_rehydrate_drops_in_flight_leases_honestly(tmp_path):
    # Honest restart consequence #1: an in-flight lease cannot survive a restart. The lease
    # token is a secret capability redacted from the durable projection (never written to the
    # ledger), so a process that crashes mid-lease must NOT come back believing a job is held
    # by a token no one has. rehydrate maps a stored 'leased' job to 'expired' -- and because
    # lease_next_job re-leases 'expired' jobs, the work is recoverable, not stranded.
    db = tmp_path / "rehydrate_lease.db"

    da.reset_distributed_audits_for_tests()
    fe.reset_fleet_executor_for_tests()
    store = SqliteStateStore(db)
    m = LedgerMirror(store)
    da.set_state_mirror(m)
    fe.set_state_mirror(m)
    try:
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
        target = run.jobs[0]
        leased = fe.lease_next_job(audit_id=audit_id, worker_id=target.assigned_worker_id)
        assert leased is not None and leased.lease_token, "precondition: a live, held lease"
        assert leased.status == "leased"
        leased_worker_id = leased.assigned_worker_id
        leased_job_id = leased.job_id
        m.assert_no_divergence()
    finally:
        da.set_state_mirror(None)
        fe.set_state_mirror(None)
        store.close()
        da.reset_distributed_audits_for_tests()
        fe.reset_fleet_executor_for_tests()

    reopened = SqliteStateStore(db)
    try:
        da.rehydrate_from_ledger(reopened)
        fe.rehydrate_from_ledger(reopened)
    finally:
        reopened.close()

    # The lease did not survive: the job is back as 'expired', with no token left behind.
    rehydrated = fe.get_fleet_run(audit_id)
    job = next(j for j in rehydrated.jobs if j.job_id == leased_job_id)
    assert job.status == "expired", "a stored 'leased' job must rehydrate as 'expired'"
    assert job.lease_token is None and job.lease_token_hash is None, "the token is never persisted"
    # the redacted token is absent from the rendered view too (it always is, but assert it).
    job_view = next(j for j in rehydrated.to_dict()["jobs"] if j["job_id"] == leased_job_id)
    assert job_view["lease_token"] is None

    # ... and the work is recoverable: the same worker can re-lease the expired job.
    re_leased = fe.lease_next_job(audit_id=audit_id, worker_id=leased_worker_id)
    assert re_leased is not None and re_leased.job_id == leased_job_id
    assert re_leased.status == "leased" and re_leased.lease_token

    da.reset_distributed_audits_for_tests()
    fe.reset_fleet_executor_for_tests()


def test_rehydrate_drops_the_non_durable_fragment_payload_digest(tmp_path):
    # Honest restart consequence #2: the raw fragment-payload digest is not durable run-ledger
    # state, so it does not survive a restart -- but the content-addressed ref that locates the
    # payload in the WORM evidence store DOES. A completed receipt may carry a raw
    # evidence_packet_fragment_payload whose sha256 the job view renders; that digest is a view
    # of bytes the run ledger does not own. So the projection keeps the ref and drops the digest:
    # after a restart the job serves the same ref with a null payload digest, and its durable
    # projection is byte-identical to before.
    db = tmp_path / "rehydrate_payload.db"
    payload = {"probe": "hidden_state_l12", "norm": 1.5, "tokens": [7, 8, 9]}

    da.reset_distributed_audits_for_tests()
    fe.reset_fleet_executor_for_tests()
    store = SqliteStateStore(db)
    m = LedgerMirror(store)
    da.set_state_mirror(m)
    fe.set_state_mirror(m)
    try:
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
        target = run.jobs[0]
        leased = fe.lease_next_job(audit_id=audit_id, worker_id=target.assigned_worker_id)
        assert leased is not None
        # Bind the raw payload into the ref's digest AND submit it, so the live job actually
        # holds the payload and renders a real sha256.
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
            evidence_packet_fragment_payload=payload,
        )
        fe.submit_job_receipt(
            audit_id=audit_id,
            job_id=leased.job_id,
            worker_id=leased.assigned_worker_id,
            lease_token=leased.lease_token,
            produced_outputs=list(leased.expected_outputs),
            evidence_packet_fragment_ref=ref,
            evidence_packet_fragment_payload=payload,
        )
        target_job_id = leased.job_id

        live_job = next(j for j in fe.get_fleet_run(audit_id).jobs if j.job_id == target_job_id)
        assert live_job.evidence_packet_fragment_payload == payload
        live_view = next(
            j for j in fe.get_fleet_run(audit_id).to_dict()["jobs"] if j["job_id"] == target_job_id
        )
        assert live_view["evidence_packet_fragment_payload_sha256"] is not None
        assert live_view["evidence_packet_fragment_ref"] == ref
        job_durable_before = fe._job_ledger_payload(live_job)
        m.assert_no_divergence()
    finally:
        da.set_state_mirror(None)
        fe.set_state_mirror(None)
        store.close()
        da.reset_distributed_audits_for_tests()
        fe.reset_fleet_executor_for_tests()

    reopened = SqliteStateStore(db)
    try:
        da.rehydrate_from_ledger(reopened)
        fe.rehydrate_from_ledger(reopened)
    finally:
        reopened.close()

    rehydrated = fe.get_fleet_run(audit_id)
    job = next(j for j in rehydrated.jobs if j.job_id == target_job_id)
    # The durable ref survives; the raw payload (WORM-owned) does not, so its digest is null.
    assert job.evidence_packet_fragment_ref == ref, "the content-addressed ref is durable state"
    assert job.evidence_packet_fragment_payload is None, "the raw payload is not run-ledger state"
    view = next(j for j in rehydrated.to_dict()["jobs"] if j["job_id"] == target_job_id)
    assert view["evidence_packet_fragment_payload_sha256"] is None
    assert view["evidence_packet_fragment_ref"] == ref
    # The job's durable projection is byte-identical: the dropped digest was never in it.
    assert fe._job_ledger_payload(job) == job_durable_before
    # And the fragment ref itself rehydrated into the dedupe set.
    assert ref in fe._FRAGMENT_REFS

    da.reset_distributed_audits_for_tests()
    fe.reset_fleet_executor_for_tests()


# ---------------------------------------------------------------------------
# Phase 3: the read-authority cutover (the flip itself), shipped DARK.
#
# The tests above prove the prerequisites -- the ledger AGREES with the dicts
# (Phase 2) and SURVIVES + can REBUILD them across a restart. These three prove
# the cutover MECHANISM: with read_from_ledger enabled the public get_*/list_*
# reconstruct each record's stored state from the ledger instead of the dict
# (shown by clearing the dict and still serving correctly), and the flip is
# reversible, dark by default, and rollback-safe via the write-through.
#
# Still DARK, still NOT the operational cutover: production installs no mirror,
# so `_STATE_MIRROR is not None and read_from_ledger` can never be true there --
# the serving path is structurally pinned to the dicts. Enabling this in a durable
# deployment (and Phase 4, deleting the dicts) remain separate, human-gated steps;
# multi-host durability is still workstream 11.
# ---------------------------------------------------------------------------


def test_ledger_reads_serve_stored_state_after_clearing_the_backing_dicts(mirror):
    # The headline cutover proof. Under dict-authority the dicts ARE the answer, so the
    # honest test that read-authority has truly MOVED is to make the ledger serve a read
    # whose dict is empty. Drive the real flow (the dual-write populates the ledger), flip
    # enable_ledger_reads(), then clear each backing dict and assert the public read still
    # returns byte-identical state -- it can only be coming from the ledger now.
    #
    # Order is the honest scope boundary. A run's verifier gate is a DERIVED view recomputed
    # from the worker cache in BOTH modes (the flip moves authority for STORED state, not the
    # ACCEPT-gating logic). So clear the run dict while the worker cache is still intact --
    # proving the run's stored state comes from the ledger with the gate reproducing exactly
    # -- and only then clear the workers.
    store, m = mirror
    audit_id = _drive_full_flow()
    m.assert_no_divergence()

    # Ground truth: exactly what the services serve under dict-authority.
    audit_before = da.get_distributed_audit(audit_id).to_dict()
    audit_list_before = sorted(a.audit_id for a in da.list_distributed_audits())
    run_rendered_before = fe.get_fleet_run(audit_id).to_dict()
    run_list_before = sorted(r.audit_id for r in fe.list_fleet_runs())
    workers_before = {w.worker_id: w.to_dict() for w in fe.list_workers()}
    assert run_rendered_before["verifier_gate_status"] == "ready_for_verifier"
    assert workers_before

    m.enable_ledger_reads()

    # The ledger serves the same durable state, but completed jobs are quarantined because
    # their raw model attestation payloads are intentionally not in the run ledger.
    assert da.get_distributed_audit(audit_id).to_dict() == audit_before
    run_ledger_view = fe.get_fleet_run(audit_id).to_dict()
    assert run_ledger_view["verifier_gate_status"] == "blocked_unattested_model"
    assert run_ledger_view["readiness"]["status"] == "blocked"
    assert {w.worker_id: w.to_dict() for w in fe.list_workers()} == workers_before

    # Now the pointed proof, one kind at a time. Audit first: self-contained, no cross-dict
    # derivation. Clear its dict; the read can ONLY come from the ledger.
    da._DISTRIBUTED_AUDITS.clear()
    assert da.get_distributed_audit(audit_id).to_dict() == audit_before
    assert sorted(a.audit_id for a in da.list_distributed_audits()) == audit_list_before

    # Run next, workers still intact so the derived gate recomputes identically.
    fe._FLEET_RUNS.clear()
    served_run = fe.get_fleet_run(audit_id)
    assert served_run.to_dict() == run_ledger_view
    assert served_run.verifier_gate_status == "blocked_unattested_model"
    assert sorted(r.audit_id for r in fe.list_fleet_runs()) == run_list_before

    # Workers last: clear the worker cache and the ledger still serves every worker, with
    # 'active' re-derived from the durable fresh heartbeat (status is a view, never stored).
    fe._WORKERS.clear()
    workers_after = {w.worker_id: w.to_dict() for w in fe.list_workers()}
    assert workers_after == workers_before
    assert all(w["status"] == "active" for w in workers_after.values())

    # Every dict is now empty, yet every public read served correctly: read-authority has
    # moved onto the ledger -- the reads consult it, never the emptied dicts.
    assert da._DISTRIBUTED_AUDITS == {}
    assert fe._FLEET_RUNS == {} and fe._WORKERS == {}


def test_ledger_read_switch_is_reversible_and_dark_by_default(mirror):
    # The switch -- not merely the mirror's presence -- decides the read source, and it
    # defaults OFF. An installed-but-not-enabled mirror is still Phase 2 (shadow only): reads
    # come from the dict. enable_ledger_reads() moves authority to the ledger;
    # disable_ledger_reads() moves it straight back. Proven by toggling the switch with the
    # dict deliberately emptied, so the two sources give visibly different answers.
    store, m = mirror
    audit_id = _drive_full_flow()
    m.assert_no_divergence()
    served = da.get_distributed_audit(audit_id).to_dict()

    # Default: a mirror IS installed but read_from_ledger is False -> dict-authority.
    assert m.read_from_ledger is False

    # Empty the dict. Under dict-authority the read must now MISS -- it did NOT fall through
    # to the ledger, which still holds the record. This is what "dark by default" means even
    # with a mirror present: Phase 2 shadows, it does not serve.
    da._DISTRIBUTED_AUDITS.clear()
    assert da.get_distributed_audit(audit_id) is None

    # Flip to ledger-authority: the very same emptied-dict read now serves from the ledger.
    m.enable_ledger_reads()
    assert m.read_from_ledger is True
    assert da.get_distributed_audit(audit_id).to_dict() == served

    # Flip back: dict-authority again, dict still empty -> the read misses once more. The
    # switch is the only thing that changed, and it fully controls the read source.
    m.disable_ledger_reads()
    assert da.get_distributed_audit(audit_id) is None


def test_write_through_keeps_the_dict_current_for_instant_rollback(mirror):
    # The rollback-safety invariant. Under read-authority get_distributed_audit returns a
    # FRESH reconstruction from the ledger, not the dict's instance -- so a mutator that read
    # the ledger, mutated that fresh object, and mirrored it would leave the dict STALE unless
    # the dual-write also writes the dict back. _mirror_audit does exactly that write-through.
    # Here we mutate through the real service API while ledger reads are live, then
    # disable_ledger_reads() and confirm the dict-authority read sees the same mutation -- i.e.
    # reverting to the dicts loses nothing, which is what makes the flip instantly reversible.
    store, m = mirror
    audit = da.create_distributed_audit(_request(), data_capture_acknowledged=True)
    audit_id = audit.audit_id
    assert da._DISTRIBUTED_AUDITS[audit_id].status == "PLANNED"

    m.enable_ledger_reads()
    # Under ledger-reads the served object is a fresh reconstruction, not the dict's instance.
    assert da.get_distributed_audit(audit_id) is not da._DISTRIBUTED_AUDITS.get(audit_id)

    # Mutate through the real mutator: it get()s from the ledger (fresh PLANNED), flips the
    # status to DISPATCHED, and dual-writes -- mirror_put to the ledger AND write-through to
    # the dict.
    da.dispatch_distributed_audit(audit_id)

    # The ledger (the live read source) reflects the mutation ...
    assert da.get_distributed_audit(audit_id).status == "DISPATCHED"
    # ... and so does the dict, because the write-through kept it current.
    assert da._DISTRIBUTED_AUDITS[audit_id].status == "DISPATCHED"

    # Instant rollback: flip read-authority back to the dicts. The mutation made under
    # ledger-reads is already there -- nothing lost, no rehydrate needed.
    m.disable_ledger_reads()
    assert da.get_distributed_audit(audit_id).status == "DISPATCHED"

    # And the two views never disagreed throughout (the post-rollback read shadow-compares).
    m.assert_no_divergence()
