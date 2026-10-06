from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from api.services.cas_harness_evidence_object_store import EvidencePacketIndexEntry
from api.services.cas_harness_v2_identity import prospective_run_id, route_context_trace_id
from api.services.cas_harness_v2_lifecycle_service import (
    AUTHORIZATION_NAMESPACE,
    CONSUMPTION_NAMESPACE,
    NONREPORTING_NAMESPACE,
    OUTCOME_ACCESS_NAMESPACE,
    OUTPUT_NAMESPACE,
    TERMINAL_DISPOSITION_NAMESPACE,
    TERMINAL_NAMESPACE,
)
from api.services.cas_harness_v2_reconciliation_report import (
    AVAILABLE,
    AVAILABLE_WITH_ISSUES,
    RECONCILIATION_NAMESPACE,
    UNAVAILABLE,
    HarnessV2ReconciliationReportService,
)
from api.services.cas_harness_v2_run_context import (
    RUN_CONTEXT_NAMESPACE,
    RunContextNotFound,
)
from api.services.cas_harness_v2_run_lifecycle import (
    AUTHORIZED,
    FAILURE,
    INDETERMINATE,
    NONREPORTING_RECORDED,
    OUTCOME_ACCESSED,
    RUNNING,
)
from api.services.cas_harness_v2_worker_bridge import (
    PERSISTING,
    RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND,
    RESEARCH_WORKER_ACCEPTANCE_NAMESPACE,
)
from api.services.cas_harness_v2_worker_bridge import FleetJobSnapshot
from api.services.cas_harness_fleet_executor import HarnessV2ConfiguredFleetInventory


TENANT = "tenant-reconcile-001"
ACCOUNT = "account-reconcile-001"
AUDIT = "audit-reconcile-001"
JOB = "job-reconcile-001"
WORKER = "worker-reconcile-001"


def _snapshot(job_id: str = JOB, worker_id: str = WORKER) -> FleetJobSnapshot:
    return FleetJobSnapshot(
        fleet_id=AUDIT,
        job_id=job_id,
        audit_id=AUDIT,
        assigned_worker_id=worker_id,
        layer_start=0,
        layer_end=1,
        shard_id=f"shard-{job_id}",
        assigned_methods=("activation-patching",),
        expected_outputs=("raw-outcomes",),
        model_id="model-reconcile-001",
        model_revision="a" * 40,
        model_artifact_manifest_path="/models/reconcile/manifest.json",
        model_artifact_manifest_sha256="b" * 64,
        execution_mode="external_probe_command",
    )


def _inventory(*jobs: FleetJobSnapshot):
    return HarnessV2ConfiguredFleetInventory(
        tenant_id=TENANT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
        jobs=tuple(jobs or (_snapshot(),)),
    )


def _context(job: FleetJobSnapshot):
    return SimpleNamespace(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
        worker_id=job.assigned_worker_id,
        job_id=job.job_id,
        run_id=prospective_run_id(job.job_id),
        subject_id=job.job_id,
        authorization_id=job.job_id,
        execution_mapping=job.execution_mapping(),
        criteria_status="OPEN",
        trusted_time="NOT_ESTABLISHED",
        license_status="NOT LICENSED",
        disclosure_status="HELD",
    )


class _Contexts:
    def __init__(self, values: dict[str, object], *, fail: bool = False) -> None:
        self.values = values
        self.fail = fail

    def load(self, **kwargs):
        if self.fail:
            raise RuntimeError("synthetic context enumeration failure")
        try:
            return self.values[kwargs["job_id"]]
        except KeyError as exc:
            raise RunContextNotFound("missing") from exc


def _artifact(artifact_id: str) -> dict[str, object]:
    return {
        "artifact_id": artifact_id,
        "media_type": "application/test",
        "sha256": "c" * 64,
        "byte_length": 1,
    }


def _event(event_type: str, artifact_field: str, artifact_id: str, **details):
    return {
        "event_type": event_type,
        "details": {artifact_field: _artifact(artifact_id), **details},
    }


def _events(job_id: str, state: str) -> tuple[dict, ...]:
    rows = [_event(AUTHORIZED, "authorization_artifact", job_id)]
    if state == AUTHORIZED:
        return tuple(rows)
    rows.append(_event(RUNNING, "consumption_artifact", f"consume-{job_id}"))
    if state == RUNNING:
        return tuple(rows)
    if state == INDETERMINATE:
        rows.append(
            _event(
                "TERMINAL_RECORDED",
                "terminal_artifact",
                f"disposition-{job_id}",
                terminal_status=INDETERMINATE,
            )
        )
        return tuple(rows)
    if state in {FAILURE, OUTCOME_ACCESSED, NONREPORTING_RECORDED}:
        rows.append(
            _event(
                "TERMINAL_RECORDED",
                "terminal_artifact",
                f"terminal-{job_id}",
                terminal_status=FAILURE,
            )
        )
    if state in {OUTCOME_ACCESSED, NONREPORTING_RECORDED}:
        rows.append(
            _event(
                OUTCOME_ACCESSED,
                "outcome_access_artifact",
                f"outcome-{job_id}",
            )
        )
    if state == NONREPORTING_RECORDED:
        rows.append(
            _event(
                NONREPORTING_RECORDED,
                "nonreporting_artifact",
                f"nonreport-{job_id}",
            )
        )
    return tuple(rows)


class _Lifecycle:
    def __init__(
        self,
        states: dict[str, str],
        *,
        lifecycle_count: int | None = None,
        fail_reconcile: bool = False,
        fail_lookup: bool = False,
    ) -> None:
        self.states = states
        self.lifecycle_count = lifecycle_count if lifecycle_count is not None else len(states)
        self.fail_reconcile = fail_reconcile
        self.fail_lookup = fail_lookup

    def reconcile(self, *, tenant_id: str):
        if self.fail_reconcile:
            raise RuntimeError("synthetic registry enumeration failure")
        state_counts: dict[str, int] = {}
        for state in self.states.values():
            state_counts[state] = state_counts.get(state, 0) + 1
        return SimpleNamespace(
            lifecycle_count=self.lifecycle_count,
            subject_reservation_count=self.lifecycle_count,
            nonce_reservation_count=self.lifecycle_count,
            authorization_finalization_count=self.lifecycle_count,
            outcome_access_reservation_count=sum(
                state in {OUTCOME_ACCESSED, NONREPORTING_RECORDED}
                for state in self.states.values()
            ),
            event_count=sum(len(_events(job_id, state)) for job_id, state in self.states.items()),
            issue_count=0,
            state_counts=state_counts,
            registry_sha256="d" * 64,
            structurally_valid=True,
            all_runs_reporting_disposed=bool(self.states)
            and all(state == NONREPORTING_RECORDED for state in self.states.values()),
            issues=(),
        )

    def get_lifecycle(self, *, tenant_id: str, subject_id: str):
        if self.fail_lookup:
            raise RuntimeError("synthetic lifecycle lookup failure")
        state = self.states.get(subject_id)
        if state is None:
            return None
        return SimpleNamespace(run_id=prospective_run_id(subject_id), state=state)

    def list_events(self, *, tenant_id: str, subject_id: str):
        if self.fail_lookup:
            raise RuntimeError("synthetic event enumeration failure")
        return _events(subject_id, self.states[subject_id])


class _Repository:
    def __init__(
        self,
        rows: tuple[EvidencePacketIndexEntry, ...],
        *,
        fail_list: bool = False,
        fail_verify: bool = False,
    ) -> None:
        self.rows = rows
        self.fail_list = fail_list
        self.fail_verify = fail_verify

    def list_packet_indices(self, *, tenant_id: str):
        if self.fail_list:
            raise RuntimeError("synthetic index enumeration failure")
        return self.rows

    def verify_packet(self, **kwargs):
        if self.fail_verify:
            raise RuntimeError("synthetic wrapper verification failure")
        return {"match": True}


class _TrackingRepository(_Repository):
    def __init__(self, rows, *, unverified=()) -> None:
        super().__init__(rows)
        self.unverified = frozenset(unverified)
        self.verifications: list[tuple[str, str]] = []

    def verify_packet(self, **kwargs):
        identity = (kwargs["namespace"], kwargs["trace_id"])
        self.verifications.append(identity)
        if identity in self.unverified:
            return {"match": False}
        return super().verify_packet(**kwargs)


class _BridgeStore:
    def __init__(self, rows=(), *, fail: bool = False) -> None:
        self.rows = tuple(rows)
        self.fail = fail

    def list(self, tenant_id: str, kind: str):
        if self.fail:
            raise RuntimeError("synthetic bridge enumeration failure")
        return tuple(row for row in self.rows if row.kind == kind)


def _trace(job_id: str, purpose: str, identity: str) -> str:
    digest = hashlib.sha256(
        f"{job_id}\0{purpose}\0{identity}".encode("utf-8")
    ).hexdigest()
    return "h2exact_" + digest


def _index(namespace: str, trace_id: str, *, account_id=ACCOUNT):
    return EvidencePacketIndexEntry(
        tenant_id=TENANT,
        namespace=namespace,
        trace_id=trace_id,
        account_id=account_id,
        record_id=f"idx-{hashlib.sha256((namespace + trace_id).encode()).hexdigest()}",
        content_sha256="e" * 64,
        byte_length=10,
        version_id="version-1",
    )


def _indices_for(job_id: str, state: str, *, output: bool = False):
    rows = [
        _index(RUN_CONTEXT_NAMESPACE, route_context_trace_id(job_id)),
        _index(AUTHORIZATION_NAMESPACE, _trace(job_id, "authorization", job_id)),
    ]
    if state != AUTHORIZED:
        rows.append(
            _index(
                CONSUMPTION_NAMESPACE,
                _trace(job_id, "consumption", f"consume-{job_id}"),
            )
        )
    if output:
        rows.append(
            _index(OUTPUT_NAMESPACE, _trace(job_id, "output", "raw-outcomes"))
        )
    if state == INDETERMINATE:
        rows.append(
            _index(
                TERMINAL_DISPOSITION_NAMESPACE,
                _trace(job_id, "terminal-disposition", f"disposition-{job_id}"),
            )
        )
    if state in {FAILURE, OUTCOME_ACCESSED, NONREPORTING_RECORDED}:
        rows.append(
            _index(
                TERMINAL_NAMESPACE,
                _trace(job_id, "terminal", f"terminal-{job_id}"),
            )
        )
    if state in {OUTCOME_ACCESSED, NONREPORTING_RECORDED}:
        rows.append(
            _index(
                OUTCOME_ACCESS_NAMESPACE,
                _trace(job_id, "outcome-access", f"outcome-{job_id}"),
            )
        )
    if state == NONREPORTING_RECORDED:
        rows.append(
            _index(
                NONREPORTING_NAMESPACE,
                _trace(job_id, "nonreporting", f"nonreport-{job_id}"),
            )
        )
    return tuple(rows)


def _service(
    *,
    jobs=(_snapshot(),),
    contexts=None,
    states=None,
    rows=None,
    lifecycle_count=None,
    repository=None,
    lifecycle=None,
    fleet=None,
    bridge_store=None,
):
    contexts = contexts if contexts is not None else {job.job_id: _context(job) for job in jobs}
    states = states if states is not None else {job.job_id: RUNNING for job in jobs}
    rows = rows if rows is not None else tuple(
        row
        for job in jobs
        for row in _indices_for(job.job_id, states[job.job_id], output=True)
    )
    return HarnessV2ReconciliationReportService(
        context_loader=_Contexts(contexts),
        lifecycle=lifecycle or _Lifecycle(states, lifecycle_count=lifecycle_count),
        repository=repository or _Repository(rows),
        enumerate_configured_fleet=fleet or (lambda **_kwargs: _inventory(*jobs)),
        bridge_store=bridge_store,
    )


def _reconcile(service):
    return service.reconcile(
        tenant_id=TENANT,
        account_id=ACCOUNT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
    )


def test_running_report_is_canonical_hashed_and_keeps_scope_limitations() -> None:
    service = _service()
    first = _reconcile(service)
    second = _reconcile(service)

    assert first.availability == AVAILABLE
    assert first.issue_count == 0
    assert first.canonical_bytes == second.canonical_bytes
    assert first.sha256 == hashlib.sha256(first.canonical_bytes).hexdigest().upper()
    assert b"\n" not in first.canonical_bytes
    payload = first.to_dict()
    assert payload["pending_inventory"] == {
        "reporting_disposed_jobs": [],
        "running_jobs": [JOB],
        "running_output_index_count": 1,
        "terminal_pending_reporting_jobs": [],
    }
    assert payload["jobs"][0]["configured_fleet_runtime_status"] == (
        "NOT_EXPOSED_BY_CONFIGURED_FLEET_INVENTORY"
    )
    assert payload["coverage"]["off_registry_execution_absence"] == "NOT_ESTABLISHED"
    assert payload["coverage"]["trusted_time"] == "NOT_ESTABLISHED"
    assert payload["authority"]["criteria_status"] == "OPEN"
    assert payload["authority"]["license_status"] == "NOT LICENSED"
    assert payload["authority"]["disclosure_status"] == "HELD"


def test_retained_reverified_self_report_is_omitted_and_replay_stable() -> None:
    base_rows = _indices_for(JOB, RUNNING, output=True)
    repository = _TrackingRepository(base_rows)
    service = _service(repository=repository)

    first = _reconcile(service)
    first_payload = first.to_dict()
    self_report_identity = (RECONCILIATION_NAMESPACE, first.report_id)
    repository.rows = (
        *base_rows,
        _index(*self_report_identity),
    )
    repository.verifications.clear()

    second = _reconcile(service)
    second_payload = second.to_dict()

    assert self_report_identity in repository.verifications
    assert second.availability == AVAILABLE
    assert second_payload["source_status"]["artifact_indices"] == (
        "AVAILABLE_TENANT_INDEX_REVERIFIED"
    )
    assert second_payload["artifact_inventory"] == (
        first_payload["artifact_inventory"]
    )
    assert RECONCILIATION_NAMESPACE.encode("ascii") not in second.canonical_bytes
    assert second.canonical_bytes == first.canonical_bytes
    assert second.sha256 == first.sha256


@pytest.mark.parametrize("failure", ["malformed", "unverified"])
def test_malformed_or_unverified_self_report_index_fails_closed(failure: str) -> None:
    base_rows = _indices_for(JOB, RUNNING, output=True)
    self_report_identity = (
        RECONCILIATION_NAMESPACE,
        "h2reconcile_" + "f" * 64,
    )
    self_report = _index(*self_report_identity)
    rows = (
        *base_rows,
        (
            SimpleNamespace(
                tenant_id=TENANT,
                namespace=RECONCILIATION_NAMESPACE,
                trace_id=self_report_identity[1],
            )
            if failure == "malformed"
            else self_report
        ),
    )
    repository = _TrackingRepository(
        rows,
        unverified=(self_report_identity,) if failure == "unverified" else (),
    )

    report = _reconcile(_service(repository=repository))
    payload = report.to_dict()

    assert report.availability == UNAVAILABLE
    assert payload["source_status"]["artifact_indices"] == (
        "UNAVAILABLE_ENUMERATION_FAILED"
    )
    assert payload["jobs"] is None
    assert payload["artifact_inventory"] is None
    assert payload["issues"] == [
        {
            "code": "SOURCE_ENUMERATION_UNAVAILABLE",
            "detail": (
                "A required configured source could not be enumerated or reverified; "
                "no empty inventory conclusion was produced."
            ),
            "subject": "artifact_indices",
        }
    ]
    if failure == "unverified":
        assert self_report_identity in repository.verifications


@pytest.mark.parametrize(
    "source",
    [
        "configured_fleet",
        "lifecycle_registry",
        "artifact_indices",
        "artifact_verification",
        "run_contexts",
        "bridge_indices",
    ],
)
def test_every_source_failure_returns_unavailable_never_empty(source: str) -> None:
    job = _snapshot()
    fleet = lambda **_kwargs: _inventory(job)
    lifecycle = _Lifecycle({JOB: RUNNING})
    repository = _Repository(_indices_for(JOB, RUNNING, output=True))
    contexts = _Contexts({JOB: _context(job)})
    bridge_store = None
    if source == "configured_fleet":
        fleet = lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("fleet"))
    elif source == "lifecycle_registry":
        lifecycle = _Lifecycle({JOB: RUNNING}, fail_reconcile=True)
    elif source == "artifact_indices":
        repository = _Repository((), fail_list=True)
    elif source == "artifact_verification":
        repository = _Repository(
            _indices_for(JOB, RUNNING, output=True), fail_verify=True
        )
    elif source == "run_contexts":
        contexts = _Contexts({JOB: _context(job)}, fail=True)
    elif source == "bridge_indices":
        bridge_store = _BridgeStore(fail=True)
    service = HarnessV2ReconciliationReportService(
        context_loader=contexts,
        lifecycle=lifecycle,
        repository=repository,
        enumerate_configured_fleet=fleet,
        bridge_store=bridge_store,
    )

    report = _reconcile(service)
    payload = report.to_dict()
    assert report.availability == UNAVAILABLE
    assert report.issue_count == 1
    assert payload["jobs"] is None
    assert payload["counts"]["configured_job_count"] is None
    assert payload["issues"] == [
        {
            "code": "SOURCE_ENUMERATION_UNAVAILABLE",
            "detail": (
                "A required configured source could not be enumerated or reverified; "
                "no empty inventory conclusion was produced."
            ),
            "subject": (
                "artifact_indices" if source == "artifact_verification" else source
            ),
        }
    ]
    assert payload["authority"]["off_registry_execution_absence"] == "NOT_ESTABLISHED"


def test_empty_configured_inventory_is_unavailable_not_a_zero_job_pass() -> None:
    malformed_inventory = SimpleNamespace(
        tenant_id=TENANT,
        audit_id=AUDIT,
        fleet_id=AUDIT,
        jobs=(),
        state_authority="PROCESS_LOCAL_FLEET_STATE_NOT_DURABLE",
        tenant_scope_authority=(
            "AUTHENTICATED_SCOPE_REQUIRED_NOT_RETAINED_BY_FLEET_EXECUTOR"
        ),
    )
    service = HarnessV2ReconciliationReportService(
        context_loader=_Contexts({}),
        lifecycle=_Lifecycle({}),
        repository=_Repository(()),
        enumerate_configured_fleet=lambda **_kwargs: malformed_inventory,
    )
    report = _reconcile(service)
    assert report.availability == UNAVAILABLE
    assert report.configured_job_count is None
    assert report.issue_count == 1


def test_missing_jobs_and_unmatched_tenant_rows_are_visible_without_global_orphan_claim() -> None:
    job_a = _snapshot()
    job_b = _snapshot("job-reconcile-002", "worker-reconcile-002")
    other_account_trace = "private-other-account-trace"
    rows = (
        *_indices_for(job_a.job_id, AUTHORIZED, output=True),
        _index(RUN_CONTEXT_NAMESPACE, "unattributed-context-trace"),
        _index(AUTHORIZATION_NAMESPACE, other_account_trace, account_id="other-account"),
        _index(AUTHORIZATION_NAMESPACE, "unowned-tenant-trace", account_id=None),
    )
    service = _service(
        jobs=(job_a, job_b),
        contexts={job_a.job_id: _context(job_a)},
        states={job_a.job_id: AUTHORIZED},
        lifecycle_count=2,
        rows=rows,
    )
    report = _reconcile(service)
    payload = report.to_dict()
    codes = {issue["code"] for issue in payload["issues"]}

    assert report.availability == AVAILABLE_WITH_ISSUES
    assert "CONFIGURED_JOB_CONTEXT_MISSING" in codes
    assert "CONFIGURED_FLEET_JOB_WITHOUT_LIFECYCLE" in codes
    assert "POTENTIAL_ORPHAN_TENANT_LIFECYCLE_COUNT" in codes
    assert "POTENTIAL_ORPHAN_CONTEXT_WRAPPER_INDEX" in codes
    assert "UNOWNED_TENANT_WRAPPER_INDEX_COUNT" in codes
    assert "OUTPUT_PRESENT_BEFORE_CONSUMPTION" in codes
    assert payload["counts"]["tenant_unmatched_lifecycle_count"] == 1
    assert payload["artifact_inventory"]["unowned_tenant_index_count"] == 1
    assert payload["artifact_inventory"]["other_account_index_count_redacted"] == 1
    assert payload["artifact_inventory"]["potential_orphans"][0]["orphan_scope"] == (
        "UNREFERENCED_BY_AUTHENTICATED_CONFIGURED_FLEET_NOT_GLOBAL"
    )
    assert other_account_trace.encode() not in report.canonical_bytes
    assert payload["coverage"]["other_audit_attribution"] == (
        "NOT_ESTABLISHED_FOR_UNMATCHED_TENANT_ROWS"
    )


def test_running_terminal_and_reporting_states_remain_separate_in_inventory() -> None:
    running = _snapshot("job-running", "worker-running")
    terminal = _snapshot("job-terminal", "worker-terminal")
    reported = _snapshot("job-reported", "worker-reported")
    jobs = (running, terminal, reported)
    states = {
        running.job_id: RUNNING,
        terminal.job_id: INDETERMINATE,
        reported.job_id: NONREPORTING_RECORDED,
    }
    rows = tuple(
        row
        for job in jobs
        for row in _indices_for(
            job.job_id,
            states[job.job_id],
            output=job.job_id == running.job_id,
        )
    )
    service = _service(jobs=jobs, states=states, rows=rows)
    report = _reconcile(service)
    payload = report.to_dict()

    assert report.availability == AVAILABLE
    assert payload["pending_inventory"] == {
        "running_jobs": [running.job_id],
        "running_output_index_count": 1,
        "terminal_pending_reporting_jobs": [terminal.job_id],
        "reporting_disposed_jobs": [reported.job_id],
    }
    by_job = {row["job_id"]: row for row in payload["jobs"]}
    assert by_job[running.job_id]["lifecycle_classification"] == (
        "RUNNING_PENDING_TERMINAL"
    )
    assert by_job[terminal.job_id]["lifecycle_classification"] == (
        "SERVER_TERMINAL_PENDING_NONREPORTING"
    )
    assert by_job[reported.job_id]["lifecycle_classification"] == (
        "REPORTING_DISPOSED"
    )


def test_optional_bridge_persisting_acceptance_is_reported_and_wrapper_required() -> None:
    bridge_record = SimpleNamespace(
        tenant_id=TENANT,
        kind=RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND,
        record_id="bridge-acceptance-pending",
        payload={
            "tenant_id": TENANT,
            "account_id": ACCOUNT,
            "audit_id": AUDIT,
            "fleet_id": AUDIT,
            "job_id": JOB,
            "namespace": RESEARCH_WORKER_ACCEPTANCE_NAMESPACE,
            "trace_id": "acceptance-trace-pending",
            "state": PERSISTING,
        },
    )
    service = _service(bridge_store=_BridgeStore((bridge_record,)))
    report = _reconcile(service)
    payload = report.to_dict()
    codes = {issue["code"] for issue in payload["issues"]}

    assert report.availability == AVAILABLE_WITH_ISSUES
    assert "BRIDGE_INDEX_PERSISTING" in codes
    assert "ACCEPTANCE_WITHOUT_BRIDGE_TERMINAL_INDEX" in codes
    assert "EXPECTED_WRAPPER_INDEX_MISSING" in codes
    assert payload["source_status"]["bridge_indices"] == (
        "AVAILABLE_TENANT_STATE_STORE_ONLY"
    )
