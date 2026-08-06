"""Fail-closed configured-scope reconciliation for the dark Harness-v2 lane.

The report joins only sources explicitly injected into this process: one
authenticated scope, the process-local configured fleet inventory, immutable
route-context lookups, the tenant lifecycle registry, the configured repository
index, and optionally the worker-bridge StateStore indexes.  It never treats an
empty configured store as proof that no other execution occurred.

No timestamp is minted.  Canonical bytes and their SHA-256 identity make the
result suitable for later immutable retention, but are not themselves WORM
storage, trusted time, execution authentication, scientific evidence, product
readiness, licensing, canon, or disclosure authority.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from typing import Any, Protocol

from api.services.cas_harness_evidence_object_store import (
    EvidencePacketIndexEntry,
    EvidencePacketRepository,
)
from api.services.cas_harness_v2_identity import (
    prospective_run_id,
    route_context_trace_id,
)
from api.services.cas_harness_v2_lifecycle_service import (
    AUTHORIZATION_NAMESPACE,
    CONSUMPTION_NAMESPACE,
    DEPENDENCY_NAMESPACE,
    EVIDENCE_PACKET_NAMESPACE,
    NONREPORTING_NAMESPACE,
    OUTCOME_ACCESS_NAMESPACE,
    OUTPUT_NAMESPACE,
    TERMINAL_DISPOSITION_NAMESPACE,
    TERMINAL_NAMESPACE,
)
from api.services.cas_harness_v2_run_context import (
    RUN_CONTEXT_NAMESPACE,
    RunContextNotFound,
)
from api.services.cas_harness_v2_run_lifecycle import (
    AUTHORIZED,
    EXPIRED,
    FAILURE,
    INDETERMINATE,
    NONREPORTING_RECORDED,
    OUTCOME_ACCESSED,
    PACKET_RECORDED,
    REJECTED,
    RUNNING,
    SUCCESS,
)
from api.services.cas_harness_v2_worker_bridge import (
    PERSISTING,
    RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND,
    RESEARCH_WORKER_ACCEPTANCE_NAMESPACE,
    RESEARCH_WORKER_BRIDGE_INDEX_KIND,
    RESEARCH_WORKER_BRIDGE_NAMESPACE,
    STORED_AND_REPLAYED,
)
from api.services.production.state_substrate import StateStore, StateStoreError


REPORT_SCHEMA = "cas_harness_v2.configured_scope_reconciliation.v1"
RECONCILIATION_NAMESPACE = "research-only/harness-v2/reconciliation-report"
AVAILABLE = "AVAILABLE_CONFIGURED_SCOPE_ONLY"
AVAILABLE_WITH_ISSUES = "AVAILABLE_WITH_ISSUES_CONFIGURED_SCOPE_ONLY"
UNAVAILABLE = "UNAVAILABLE_SOURCE_ENUMERATION_FAILED"

_HARNESS_NAMESPACES = frozenset(
    {
        AUTHORIZATION_NAMESPACE,
        CONSUMPTION_NAMESPACE,
        TERMINAL_NAMESPACE,
        TERMINAL_DISPOSITION_NAMESPACE,
        OUTPUT_NAMESPACE,
        OUTCOME_ACCESS_NAMESPACE,
        DEPENDENCY_NAMESPACE,
        EVIDENCE_PACKET_NAMESPACE,
        NONREPORTING_NAMESPACE,
        RUN_CONTEXT_NAMESPACE,
        RESEARCH_WORKER_BRIDGE_NAMESPACE,
        RESEARCH_WORKER_ACCEPTANCE_NAMESPACE,
        RECONCILIATION_NAMESPACE,
    }
)
_DIRECT_DISPOSITIONS = frozenset({INDETERMINATE, REJECTED, EXPIRED})
_STRICT_TERMINALS = frozenset({SUCCESS, FAILURE})
_TERMINALS = _STRICT_TERMINALS | _DIRECT_DISPOSITIONS
_REPORTING = frozenset({PACKET_RECORDED, NONREPORTING_RECORDED})


class ReconciliationReportError(RuntimeError):
    """Base error for malformed service configuration or request scope."""


class ReconciliationReportValidationError(ReconciliationReportError):
    """The injected seams or authenticated scope are malformed."""


class _SourceUnavailable(RuntimeError):
    def __init__(self, source: str) -> None:
        self.source = source
        super().__init__(source)


class ConfiguredFleetInventoryPort(Protocol):
    tenant_id: str
    audit_id: str
    fleet_id: str
    jobs: tuple[Any, ...]
    state_authority: str
    tenant_scope_authority: str


@dataclass(frozen=True, slots=True)
class ReconciliationIssue:
    code: str
    subject: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "subject": self.subject,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class HarnessV2ReconciliationReport:
    """Canonical report bytes and identity; no global absence claim is implied."""

    report_id: str
    availability: str
    canonical_bytes: bytes
    sha256: str
    issue_count: int
    configured_job_count: int | None
    criteria_status: str = "OPEN"
    trusted_time: str = "NOT_ESTABLISHED"
    off_registry_execution_absence: str = "NOT_ESTABLISHED"
    license_status: str = "NOT LICENSED"
    disclosure_status: str = "HELD"

    def to_dict(self) -> dict[str, Any]:
        value = json.loads(self.canonical_bytes.decode("ascii"))
        if not isinstance(value, dict):  # pragma: no cover - construction invariant
            raise ReconciliationReportError("Canonical report is not an object.")
        return value


@dataclass(frozen=True, slots=True)
class _ExpectedWrapper:
    job_id: str
    purpose: str
    required: bool


class HarnessV2ReconciliationReportService:
    """Join configured, tenant-visible sources without promoting their scope."""

    def __init__(
        self,
        *,
        context_loader: Callable[..., Any] | object,
        lifecycle: Any,
        repository: EvidencePacketRepository,
        enumerate_configured_fleet: Callable[..., ConfiguredFleetInventoryPort],
        bridge_store: StateStore | None = None,
    ) -> None:
        loader = (
            context_loader
            if callable(context_loader)
            else getattr(context_loader, "load", None)
        )
        if not callable(loader):
            raise ReconciliationReportValidationError(
                "context_loader must be callable or expose load()."
            )
        if (
            lifecycle is None
            or not callable(getattr(lifecycle, "reconcile", None))
            or not callable(getattr(lifecycle, "get_lifecycle", None))
            or not callable(getattr(lifecycle, "list_events", None))
            or repository is None
            or not callable(getattr(repository, "list_packet_indices", None))
            or not callable(getattr(repository, "verify_packet", None))
            or not callable(enumerate_configured_fleet)
        ):
            raise ReconciliationReportValidationError(
                "Every required reconciliation source must be injected."
            )
        if bridge_store is not None and not callable(
            getattr(bridge_store, "list", None)
        ):
            raise ReconciliationReportValidationError(
                "bridge_store must expose tenant-scoped list()."
            )
        self._load_context = loader
        self._lifecycle = lifecycle
        self._repository = repository
        self._enumerate_fleet = enumerate_configured_fleet
        self._bridge_store = bridge_store

    def reconcile(
        self,
        *,
        tenant_id: str,
        account_id: str,
        audit_id: str,
        fleet_id: str,
    ) -> HarnessV2ReconciliationReport:
        scope = _scope(
            tenant_id=tenant_id,
            account_id=account_id,
            audit_id=audit_id,
            fleet_id=fleet_id,
        )
        report_id = _report_id(scope)
        source_status = {
            "configured_fleet": "NOT_ATTEMPTED",
            "run_contexts": "NOT_ATTEMPTED",
            "lifecycle_registry": "NOT_ATTEMPTED",
            "artifact_indices": "NOT_ATTEMPTED",
            "bridge_indices": (
                "NOT_ATTEMPTED"
                if self._bridge_store is not None
                else "NOT_CONFIGURED_OPTIONAL_SOURCE"
            ),
        }

        try:
            inventory = self._enumerate_fleet(
                tenant_id=tenant_id,
                audit_id=audit_id,
                fleet_id=fleet_id,
            )
            jobs = _configured_jobs(inventory, scope)
            source_status["configured_fleet"] = (
                "AVAILABLE_PROCESS_LOCAL_CONFIGURATION_ONLY"
            )
        except Exception:
            return _unavailable_report(
                report_id=report_id,
                scope=scope,
                source="configured_fleet",
                source_status=source_status,
            )

        try:
            registry = self._lifecycle.reconcile(tenant_id=tenant_id)
            registry_summary = _registry_summary(registry)
            source_status["lifecycle_registry"] = "AVAILABLE_TENANT_REGISTRY_ONLY"
        except Exception:
            return _unavailable_report(
                report_id=report_id,
                scope=scope,
                source="lifecycle_registry",
                source_status=source_status,
            )

        try:
            all_indices = tuple(
                self._repository.list_packet_indices(tenant_id=tenant_id)
            )
            harness_indices = _verified_harness_indices(
                repository=self._repository,
                tenant_id=tenant_id,
                rows=all_indices,
            )
            source_status["artifact_indices"] = (
                "AVAILABLE_TENANT_INDEX_REVERIFIED"
            )
        except Exception:
            return _unavailable_report(
                report_id=report_id,
                scope=scope,
                source="artifact_indices",
                source_status=source_status,
            )

        bridge_rows: tuple[Any, ...] = ()
        if self._bridge_store is not None:
            try:
                bridge_rows = _bridge_rows(
                    store=self._bridge_store,
                    tenant_id=tenant_id,
                )
                source_status["bridge_indices"] = (
                    "AVAILABLE_TENANT_STATE_STORE_ONLY"
                )
            except Exception:
                return _unavailable_report(
                    report_id=report_id,
                    scope=scope,
                    source="bridge_indices",
                    source_status=source_status,
                )

        try:
            return self._build_available(
                report_id=report_id,
                scope=scope,
                jobs=jobs,
                registry=registry,
                registry_summary=registry_summary,
                harness_indices=harness_indices,
                bridge_rows=bridge_rows,
                source_status=source_status,
            )
        except _SourceUnavailable as exc:
            return _unavailable_report(
                report_id=report_id,
                scope=scope,
                source=exc.source,
                source_status=source_status,
            )

    def _build_available(
        self,
        *,
        report_id: str,
        scope: Mapping[str, str],
        jobs: tuple[Any, ...],
        registry: Any,
        registry_summary: Mapping[str, Any],
        harness_indices: tuple[EvidencePacketIndexEntry, ...],
        bridge_rows: tuple["_BridgeRow", ...],
        source_status: dict[str, str],
    ) -> HarnessV2ReconciliationReport:
        issues: list[ReconciliationIssue] = []
        expected: dict[tuple[str, str], _ExpectedWrapper] = {}
        job_rows: list[dict[str, Any]] = []
        configured_ids = {job.job_id for job in jobs}
        lifecycle_by_job: dict[str, Any] = {}
        terminal_status_by_job: dict[str, str | None] = {}

        owned_indices = tuple(
            row for row in harness_indices if row.account_id == scope["account_id"]
        )
        unowned_index_count = sum(row.account_id is None for row in harness_indices)
        other_account_index_count = len(harness_indices) - len(owned_indices) - unowned_index_count
        actual = {(row.namespace, row.trace_id): row for row in owned_indices}
        if unowned_index_count:
            issues.append(
                ReconciliationIssue(
                    "UNOWNED_TENANT_WRAPPER_INDEX_COUNT",
                    "tenant-repository",
                    "Tenant-visible Harness-v2 wrapper indexes without account ownership remain unattributed.",
                )
            )

        configured_inventory = []
        for job in jobs:
            mapping = _job_mapping(job, scope)
            configured_inventory.append(
                {
                    "job_id": job.job_id,
                    "worker_id": job.assigned_worker_id,
                    "execution_mapping_sha256": _sha256_json(mapping),
                }
            )
            _expect(
                expected,
                namespace=RUN_CONTEXT_NAMESPACE,
                trace_id=route_context_trace_id(job.job_id),
                job_id=job.job_id,
                purpose="route-context",
                required=True,
                issues=issues,
            )
            for output_name in job.expected_outputs:
                _expect(
                    expected,
                    namespace=OUTPUT_NAMESPACE,
                    trace_id=_lifecycle_trace_id(
                        job.job_id, "output", output_name
                    ),
                    job_id=job.job_id,
                    purpose=f"output:{output_name}",
                    required=False,
                    issues=issues,
                )

            try:
                context = self._load_context(
                    tenant_id=scope["tenant_id"],
                    account_id=scope["account_id"],
                    audit_id=scope["audit_id"],
                    fleet_id=scope["fleet_id"],
                    worker_id=job.assigned_worker_id,
                    job_id=job.job_id,
                )
            except RunContextNotFound:
                context = None
            except Exception as exc:
                raise _SourceUnavailable("run_contexts") from exc

            context_status = "MISSING"
            if context is None:
                issues.append(
                    ReconciliationIssue(
                        "CONFIGURED_JOB_CONTEXT_MISSING",
                        job.job_id,
                        "Configured job has no reverified immutable route context.",
                    )
                )
            else:
                try:
                    context_mapping = _context_mapping(context, scope, job.job_id)
                except Exception as exc:
                    raise _SourceUnavailable("run_contexts") from exc
                context_status = "PRESENT_REVERIFIED"
                if context_mapping != mapping:
                    issues.append(
                        ReconciliationIssue(
                            "CONTEXT_FLEET_MAPPING_MISMATCH",
                            job.job_id,
                            "Route context execution mapping differs from configured fleet mapping.",
                        )
                    )

            try:
                lifecycle = self._lifecycle.get_lifecycle(
                    tenant_id=scope["tenant_id"], subject_id=job.job_id
                )
            except Exception as exc:
                raise _SourceUnavailable("lifecycle_registry") from exc
            lifecycle_by_job[job.job_id] = lifecycle
            if lifecycle is None:
                issues.append(
                    ReconciliationIssue(
                        "CONFIGURED_FLEET_JOB_WITHOUT_LIFECYCLE",
                        job.job_id,
                        "Configured fleet job has no tenant-visible prospective lifecycle.",
                    )
                )
                state = "MISSING"
                classification = "CONFIGURED_WITHOUT_LIFECYCLE"
                events: tuple[Mapping[str, Any], ...] = ()
                terminal_status = None
            else:
                try:
                    if lifecycle.run_id != prospective_run_id(job.job_id):
                        raise ValueError("run identity mismatch")
                    state = _state(lifecycle.state)
                    events = tuple(
                        self._lifecycle.list_events(
                            tenant_id=scope["tenant_id"], subject_id=job.job_id
                        )
                    )
                    terminal_status = _expected_from_events(
                        expected=expected,
                        issues=issues,
                        job_id=job.job_id,
                        state=state,
                        events=events,
                    )
                except Exception as exc:
                    raise _SourceUnavailable("lifecycle_registry") from exc
                classification = _state_classification(state)
                if context is not None and context.run_id != lifecycle.run_id:
                    issues.append(
                        ReconciliationIssue(
                            "CONTEXT_LIFECYCLE_RUN_MISMATCH",
                            job.job_id,
                            "Route context run identity differs from lifecycle identity.",
                        )
                    )
            terminal_status_by_job[job.job_id] = terminal_status

            output_keys = [
                (
                    OUTPUT_NAMESPACE,
                    _lifecycle_trace_id(job.job_id, "output", output_name),
                )
                for output_name in job.expected_outputs
            ]
            present_outputs = [key for key in output_keys if key in actual]
            if state == AUTHORIZED and present_outputs:
                issues.append(
                    ReconciliationIssue(
                        "OUTPUT_PRESENT_BEFORE_CONSUMPTION",
                        job.job_id,
                        "Output wrapper exists while lifecycle remains AUTHORIZED.",
                    )
                )
            if state == SUCCESS:
                for key in output_keys:
                    expectation = expected[key]
                    expected[key] = _ExpectedWrapper(
                        expectation.job_id, expectation.purpose, True
                    )

            job_rows.append(
                {
                    "job_id": job.job_id,
                    "worker_id": job.assigned_worker_id,
                    "context_status": context_status,
                    "lifecycle_state": state,
                    "lifecycle_classification": classification,
                    "terminal_status": terminal_status,
                    "retained_output_index_count": len(present_outputs),
                    "configured_fleet_runtime_status": (
                        "NOT_EXPOSED_BY_CONFIGURED_FLEET_INVENTORY"
                    ),
                    "state_fleet_comparison": (
                        "CONFIGURATION_MEMBERSHIP_AND_MAPPING_ONLY"
                    ),
                }
            )

        source_status["run_contexts"] = "AVAILABLE_BY_CONFIGURED_JOB_LOOKUP_ONLY"

        current_bridge_rows = tuple(
            row
            for row in bridge_rows
            if row.account_id == scope["account_id"]
            and row.audit_id == scope["audit_id"]
            and row.fleet_id == scope["fleet_id"]
        )
        terminal_bridge_jobs: set[str] = set()
        acceptance_jobs: set[str] = set()
        for row in current_bridge_rows:
            if row.kind == RESEARCH_WORKER_BRIDGE_INDEX_KIND:
                terminal_bridge_jobs.add(row.job_id)
            else:
                acceptance_jobs.add(row.job_id)
            _expect(
                expected,
                namespace=row.namespace,
                trace_id=row.trace_id,
                job_id=row.job_id,
                purpose=(
                    "worker-bridge"
                    if row.kind == RESEARCH_WORKER_BRIDGE_INDEX_KIND
                    else "worker-acceptance"
                ),
                required=True,
                issues=issues,
            )
            if row.job_id not in configured_ids:
                issues.append(
                    ReconciliationIssue(
                        "BRIDGE_INDEX_OUTSIDE_CONFIGURED_FLEET",
                        row.record_id,
                        "Bridge index references no configured job in this report scope.",
                    )
                )
            if row.state == PERSISTING:
                issues.append(
                    ReconciliationIssue(
                        "BRIDGE_INDEX_PERSISTING",
                        row.record_id,
                        "Bridge reservation has no finalized immutable-storage binding.",
                    )
                )
            if row.kind == RESEARCH_WORKER_BRIDGE_INDEX_KIND:
                state = getattr(lifecycle_by_job.get(row.job_id), "state", None)
                if state in {None, AUTHORIZED, RUNNING}:
                    issues.append(
                        ReconciliationIssue(
                            "BRIDGE_TERMINAL_WITHOUT_TERMINAL_LIFECYCLE",
                            row.record_id,
                            "Bridge terminal index precedes a terminal lifecycle event.",
                        )
                    )
                if terminal_status_by_job.get(row.job_id) in _DIRECT_DISPOSITIONS:
                    issues.append(
                        ReconciliationIssue(
                            "BRIDGE_INDEX_FOR_SERVER_DISPOSITION",
                            row.record_id,
                            "Worker terminal bridge index conflicts with a server-built disposition.",
                        )
                    )

        if self._bridge_store is not None:
            for job_id in sorted(acceptance_jobs - terminal_bridge_jobs):
                issues.append(
                    ReconciliationIssue(
                        "ACCEPTANCE_WITHOUT_BRIDGE_TERMINAL_INDEX",
                        job_id,
                        "Callback acceptance index has no terminal bridge index.",
                    )
                )
            for job_id, terminal_status in terminal_status_by_job.items():
                if (
                    terminal_status in _STRICT_TERMINALS
                    and job_id not in terminal_bridge_jobs
                ):
                    issues.append(
                        ReconciliationIssue(
                            "STRICT_TERMINAL_WITHOUT_BRIDGE_INDEX",
                            job_id,
                            "Strict terminal lifecycle has no configured bridge index.",
                        )
                    )

        for key, expectation in sorted(expected.items()):
            if expectation.required and key not in actual:
                issues.append(
                    ReconciliationIssue(
                        "EXPECTED_WRAPPER_INDEX_MISSING",
                        expectation.job_id,
                        f"Required {expectation.purpose} wrapper index is unavailable.",
                    )
                )

        unresolved_wrappers: list[dict[str, str]] = []
        potential_orphans: list[dict[str, str]] = []
        for key, row in sorted(actual.items()):
            if key in expected:
                continue
            if row.namespace == DEPENDENCY_NAMESPACE or (
                self._bridge_store is None
                and row.namespace
                in {RESEARCH_WORKER_BRIDGE_NAMESPACE, RESEARCH_WORKER_ACCEPTANCE_NAMESPACE}
            ):
                unresolved_wrappers.append(_index_identity(row))
                continue
            potential_orphans.append(
                {
                    **_index_identity(row),
                    "orphan_scope": (
                        "UNREFERENCED_BY_AUTHENTICATED_CONFIGURED_FLEET_NOT_GLOBAL"
                    ),
                }
            )
            orphan_code = (
                "POTENTIAL_ORPHAN_CONTEXT_WRAPPER_INDEX"
                if row.namespace == RUN_CONTEXT_NAMESPACE
                else "POTENTIAL_ORPHAN_WRAPPER_INDEX"
            )
            issues.append(
                ReconciliationIssue(
                    orphan_code,
                    row.record_id,
                    "Account-owned wrapper is unreferenced by this configured fleet; other-audit ownership is not established.",
                )
            )

        known_lifecycle_count = sum(value is not None for value in lifecycle_by_job.values())
        tenant_lifecycle_count = int(registry_summary["lifecycle_count"])
        unmatched_lifecycle_count = tenant_lifecycle_count - known_lifecycle_count
        if unmatched_lifecycle_count != 0:
            issues.append(
                ReconciliationIssue(
                    "POTENTIAL_ORPHAN_TENANT_LIFECYCLE_COUNT",
                    "tenant-registry",
                    "Tenant lifecycle count differs from configured-fleet matches; audit ownership of the remainder is not established.",
                )
            )
        for item in getattr(registry, "issues", ()):
            code = getattr(item, "code", "UNKNOWN")
            record_id = getattr(item, "record_id", "tenant-registry")
            issues.append(
                ReconciliationIssue(
                    f"REGISTRY_{code}",
                    str(record_id),
                    "Tenant lifecycle registry reported a structural reconciliation issue.",
                )
            )

        issues = sorted(issues, key=lambda item: (item.code, item.subject, item.detail))
        state_counts: dict[str, int] = {}
        for row in job_rows:
            state = str(row["lifecycle_state"])
            state_counts[state] = state_counts.get(state, 0) + 1
        running_jobs = sorted(
            row["job_id"] for row in job_rows if row["lifecycle_state"] == RUNNING
        )
        terminal_pending = sorted(
            row["job_id"]
            for row in job_rows
            if row["lifecycle_state"] in (_TERMINALS | {OUTCOME_ACCESSED})
        )
        reporting_disposed = sorted(
            row["job_id"]
            for row in job_rows
            if row["lifecycle_state"] in _REPORTING
        )
        artifact_rows = [_index_identity(row) for row in owned_indices]
        bridge_inventory = [row.as_dict() for row in current_bridge_rows]
        payload = {
            "schema_version": REPORT_SCHEMA,
            "report_id": report_id,
            "availability": AVAILABLE_WITH_ISSUES if issues else AVAILABLE,
            "scope": dict(scope),
            "source_status": dict(sorted(source_status.items())),
            "coverage": _coverage(bridge_configured=self._bridge_store is not None),
            "configured_fleet": {
                "job_count": len(jobs),
                "inventory_sha256": _sha256_json(configured_inventory),
                "runtime_status_visibility": (
                    "NOT_EXPOSED_BY_CONFIGURED_FLEET_INVENTORY"
                ),
            },
            "registry": dict(registry_summary),
            "artifact_inventory": {
                "owned_harness_index_count": len(owned_indices),
                "unowned_tenant_index_count": unowned_index_count,
                "other_account_index_count_redacted": other_account_index_count,
                "inventory_sha256": _sha256_json(artifact_rows),
                "potential_orphans": potential_orphans,
                "scope_unresolved": unresolved_wrappers,
            },
            "bridge_inventory": {
                "configured": self._bridge_store is not None,
                "current_scope_index_count": len(current_bridge_rows),
                "other_scope_index_count_redacted": len(bridge_rows)
                - len(current_bridge_rows),
                "inventory_sha256": (
                    _sha256_json(bridge_inventory)
                    if self._bridge_store is not None
                    else None
                ),
            },
            "counts": {
                "configured_job_count": len(jobs),
                "matched_context_count": sum(
                    row["context_status"] == "PRESENT_REVERIFIED" for row in job_rows
                ),
                "matched_lifecycle_count": known_lifecycle_count,
                "tenant_lifecycle_count": tenant_lifecycle_count,
                "tenant_unmatched_lifecycle_count": unmatched_lifecycle_count,
                "issue_count": len(issues),
            },
            "state_counts": dict(sorted(state_counts.items())),
            "pending_inventory": {
                "running_jobs": running_jobs,
                "terminal_pending_reporting_jobs": terminal_pending,
                "reporting_disposed_jobs": reporting_disposed,
                "running_output_index_count": sum(
                    row["retained_output_index_count"]
                    for row in job_rows
                    if row["lifecycle_state"] == RUNNING
                ),
            },
            "jobs": sorted(job_rows, key=lambda row: row["job_id"]),
            "issues": [issue.as_dict() for issue in issues],
            "authority": _authority(),
        }
        return _report(payload)


@dataclass(frozen=True, slots=True)
class _BridgeRow:
    kind: str
    record_id: str
    account_id: str
    audit_id: str
    fleet_id: str
    job_id: str
    namespace: str
    trace_id: str
    state: str

    def as_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "record_id": self.record_id,
            "account_id": self.account_id,
            "audit_id": self.audit_id,
            "fleet_id": self.fleet_id,
            "job_id": self.job_id,
            "namespace": self.namespace,
            "trace_id": self.trace_id,
            "state": self.state,
        }


def _scope(
    *, tenant_id: str, account_id: str, audit_id: str, fleet_id: str
) -> dict[str, str]:
    result = {
        "tenant_id": _text(tenant_id, "tenant_id"),
        "account_id": _text(account_id, "account_id"),
        "audit_id": _text(audit_id, "audit_id"),
        "fleet_id": _text(fleet_id, "fleet_id"),
    }
    if result["audit_id"] != result["fleet_id"]:
        raise ReconciliationReportValidationError(
            "Authenticated fleet_id must exactly equal audit_id."
        )
    return result


def _report_id(scope: Mapping[str, str]) -> str:
    digest = hashlib.sha256(
        "\0".join(scope[field] for field in ("tenant_id", "account_id", "audit_id", "fleet_id")).encode(
            "utf-8"
        )
    ).hexdigest()
    return "h2reconcile_" + digest


def _configured_jobs(
    inventory: ConfiguredFleetInventoryPort, scope: Mapping[str, str]
) -> tuple[Any, ...]:
    if (
        getattr(inventory, "tenant_id", None) != scope["tenant_id"]
        or getattr(inventory, "audit_id", None) != scope["audit_id"]
        or getattr(inventory, "fleet_id", None) != scope["fleet_id"]
        or getattr(inventory, "state_authority", None)
        != "PROCESS_LOCAL_FLEET_STATE_NOT_DURABLE"
        or getattr(inventory, "tenant_scope_authority", None)
        != "AUTHENTICATED_SCOPE_REQUIRED_NOT_RETAINED_BY_FLEET_EXECUTOR"
    ):
        raise ReconciliationReportValidationError(
            "Configured fleet inventory scope or authority limitation changed."
        )
    jobs = getattr(inventory, "jobs", None)
    if type(jobs) is not tuple or not jobs:
        raise ReconciliationReportValidationError(
            "Configured fleet inventory must contain a non-empty exact tuple."
        )
    try:
        ordered = tuple(sorted(jobs, key=lambda job: job.job_id))
        job_ids = tuple(_text(job.job_id, "configured job_id") for job in ordered)
    except (AttributeError, TypeError) as exc:
        raise ReconciliationReportValidationError(
            "Configured fleet inventory contains a malformed job."
        ) from exc
    if len(set(job_ids)) != len(job_ids):
        raise ReconciliationReportValidationError(
            "Configured fleet inventory contains duplicate jobs."
        )
    return ordered


def _job_mapping(job: Any, scope: Mapping[str, str]) -> dict[str, Any]:
    try:
        value = job.execution_mapping()
    except (AttributeError, TypeError, ValueError) as exc:
        raise ReconciliationReportValidationError(
            "Configured job cannot provide its exact execution mapping."
        ) from exc
    mapping = _plain_mapping(value, "configured execution mapping")
    expected = {
        "job_id": job.job_id,
        "audit_id": scope["audit_id"],
        "fleet_id": scope["fleet_id"],
        "assigned_worker_id": job.assigned_worker_id,
    }
    if any(mapping.get(field) != required for field, required in expected.items()):
        raise ReconciliationReportValidationError(
            "Configured job execution mapping crossed the authenticated scope."
        )
    outputs = getattr(job, "expected_outputs", None)
    if type(outputs) is not tuple or not outputs or any(
        type(value) is not str or not value for value in outputs
    ):
        raise ReconciliationReportValidationError(
            "Configured job expected_outputs are malformed."
        )
    return mapping


def _context_mapping(
    context: Any, scope: Mapping[str, str], job_id: str
) -> dict[str, Any]:
    expected = {
        "tenant_id": scope["tenant_id"],
        "account_id": scope["account_id"],
        "audit_id": scope["audit_id"],
        "fleet_id": scope["fleet_id"],
        "job_id": job_id,
        "subject_id": job_id,
        "authorization_id": job_id,
        "run_id": prospective_run_id(job_id),
        "criteria_status": "OPEN",
        "trusted_time": "NOT_ESTABLISHED",
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
    }
    for field, required in expected.items():
        if getattr(context, field, None) != required:
            raise ReconciliationReportValidationError(
                f"Run context {field} differs from authenticated scope."
            )
    return _plain_mapping(
        getattr(context, "execution_mapping", None), "context execution mapping"
    )


def _registry_summary(value: Any) -> dict[str, Any]:
    integer_fields = (
        "lifecycle_count",
        "subject_reservation_count",
        "nonce_reservation_count",
        "authorization_finalization_count",
        "outcome_access_reservation_count",
        "event_count",
        "issue_count",
    )
    result: dict[str, Any] = {}
    for field in integer_fields:
        item = getattr(value, field, None)
        if type(item) is not int or item < 0:
            raise ReconciliationReportValidationError(
                f"Registry reconciliation {field} is malformed."
            )
        result[field] = item
    digest = getattr(value, "registry_sha256", None)
    if not _is_sha256(digest):
        raise ReconciliationReportValidationError(
            "Registry reconciliation digest is malformed."
        )
    state_counts = _plain_mapping(
        getattr(value, "state_counts", None), "registry state_counts"
    )
    if any(type(count) is not int or count < 0 for count in state_counts.values()):
        raise ReconciliationReportValidationError(
            "Registry reconciliation state counts are malformed."
        )
    structurally_valid = getattr(value, "structurally_valid", None)
    all_disposed = getattr(value, "all_runs_reporting_disposed", None)
    issues = getattr(value, "issues", None)
    if (
        type(structurally_valid) is not bool
        or type(all_disposed) is not bool
        or type(issues) is not tuple
        or len(issues) != result["issue_count"]
        or structurally_valid == bool(issues)
    ):
        raise ReconciliationReportValidationError(
            "Registry reconciliation verdict or issue inventory is malformed."
        )
    result.update(
        {
            "registry_sha256": digest,
            "structurally_valid": structurally_valid,
            "all_runs_reporting_disposed": all_disposed,
            "state_counts": dict(sorted(state_counts.items())),
            "source_scope": "TENANT_STATE_STORE_ONLY",
        }
    )
    return result


def _verified_harness_indices(
    *,
    repository: EvidencePacketRepository,
    tenant_id: str,
    rows: tuple[EvidencePacketIndexEntry, ...],
) -> tuple[EvidencePacketIndexEntry, ...]:
    result: list[EvidencePacketIndexEntry] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, EvidencePacketIndexEntry):
            raise ReconciliationReportValidationError(
                "Repository inventory returned an invalid index carrier."
            )
        if row.tenant_id != tenant_id:
            raise ReconciliationReportValidationError(
                "Repository inventory crossed tenant scope."
            )
        if row.namespace.startswith("research-only/harness-v2/") and row.namespace not in _HARNESS_NAMESPACES:
            raise ReconciliationReportValidationError(
                "Repository inventory contains an unknown Harness-v2 namespace."
            )
        if row.namespace not in _HARNESS_NAMESPACES:
            continue
        key = (row.namespace, row.trace_id)
        if key in seen:
            raise ReconciliationReportValidationError(
                "Repository inventory contains duplicate Harness-v2 identities."
            )
        seen.add(key)
        verification = repository.verify_packet(
            tenant_id=tenant_id,
            namespace=row.namespace,
            trace_id=row.trace_id,
        )
        if not isinstance(verification, Mapping) or verification.get("match") is not True:
            raise ReconciliationReportValidationError(
                "Repository index points to bytes that did not reverify."
            )
        # Prior reconciliation reports are reverified as known Harness-v2
        # storage, then deliberately omitted from the state being reconciled.
        # Otherwise retaining a report would make the next report recursively
        # describe itself and destroy exact replay stability.
        if row.namespace == RECONCILIATION_NAMESPACE:
            continue
        result.append(row)
    return tuple(sorted(result, key=lambda row: (row.namespace, row.trace_id)))


def _bridge_rows(*, store: StateStore, tenant_id: str) -> tuple[_BridgeRow, ...]:
    try:
        records = (
            *store.list(tenant_id, RESEARCH_WORKER_BRIDGE_INDEX_KIND),
            *store.list(tenant_id, RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND),
        )
    except StateStoreError:
        raise
    result: list[_BridgeRow] = []
    seen: set[tuple[str, str]] = set()
    for record in records:
        if record.tenant_id != tenant_id or record.kind not in {
            RESEARCH_WORKER_BRIDGE_INDEX_KIND,
            RESEARCH_WORKER_ACCEPTANCE_INDEX_KIND,
        }:
            raise ReconciliationReportValidationError(
                "Bridge index enumeration crossed tenant or kind scope."
            )
        payload = record.payload
        if payload.get("tenant_id") != tenant_id:
            raise ReconciliationReportValidationError(
                "Bridge index payload crossed tenant scope."
            )
        namespace = _text(payload.get("namespace"), "bridge namespace")
        expected_namespace = (
            RESEARCH_WORKER_BRIDGE_NAMESPACE
            if record.kind == RESEARCH_WORKER_BRIDGE_INDEX_KIND
            else RESEARCH_WORKER_ACCEPTANCE_NAMESPACE
        )
        state = _text(payload.get("state"), "bridge state")
        if namespace != expected_namespace or state not in {PERSISTING, STORED_AND_REPLAYED}:
            raise ReconciliationReportValidationError(
                "Bridge index namespace or state is malformed."
            )
        row = _BridgeRow(
            kind=record.kind,
            record_id=_text(record.record_id, "bridge record_id"),
            account_id=_text(payload.get("account_id"), "bridge account_id"),
            audit_id=_text(payload.get("audit_id"), "bridge audit_id"),
            fleet_id=_text(payload.get("fleet_id"), "bridge fleet_id"),
            job_id=_text(payload.get("job_id"), "bridge job_id"),
            namespace=namespace,
            trace_id=_text(payload.get("trace_id"), "bridge trace_id"),
            state=state,
        )
        if row.audit_id != row.fleet_id:
            raise ReconciliationReportValidationError(
                "Bridge index audit/fleet scope is inconsistent."
            )
        key = (row.kind, row.record_id)
        if key in seen:
            raise ReconciliationReportValidationError(
                "Bridge index enumeration contains duplicate records."
            )
        seen.add(key)
        result.append(row)
    return tuple(sorted(result, key=lambda row: (row.kind, row.record_id)))


def _expected_from_events(
    *,
    expected: dict[tuple[str, str], _ExpectedWrapper],
    issues: list[ReconciliationIssue],
    job_id: str,
    state: str,
    events: tuple[Mapping[str, Any], ...],
) -> str | None:
    seen: set[str] = set()
    terminal_status: str | None = None
    routes = {
        AUTHORIZED: (AUTHORIZATION_NAMESPACE, "authorization", "authorization_artifact"),
        RUNNING: (CONSUMPTION_NAMESPACE, "consumption", "consumption_artifact"),
        OUTCOME_ACCESSED: (
            OUTCOME_ACCESS_NAMESPACE,
            "outcome-access",
            "outcome_access_artifact",
        ),
        PACKET_RECORDED: (
            EVIDENCE_PACKET_NAMESPACE,
            "evidence-packet",
            "packet_artifact",
        ),
        NONREPORTING_RECORDED: (
            NONREPORTING_NAMESPACE,
            "nonreporting",
            "nonreporting_artifact",
        ),
    }
    for event in events:
        if not isinstance(event, Mapping):
            raise ReconciliationReportValidationError(
                "Lifecycle event inventory contains a malformed event."
            )
        event_type = _text(event.get("event_type"), "event_type")
        if event_type in seen:
            raise ReconciliationReportValidationError(
                "Lifecycle event inventory contains duplicate event types."
            )
        seen.add(event_type)
        details = event.get("details")
        if not isinstance(details, Mapping):
            raise ReconciliationReportValidationError(
                "Lifecycle event details are unavailable."
            )
        if event_type == "TERMINAL_RECORDED":
            terminal_status = _state(details.get("terminal_status"))
            if terminal_status not in _TERMINALS:
                raise ReconciliationReportValidationError(
                    "Terminal event contains an invalid state."
                )
            namespace, purpose = (
                (TERMINAL_DISPOSITION_NAMESPACE, "terminal-disposition")
                if terminal_status in _DIRECT_DISPOSITIONS
                else (TERMINAL_NAMESPACE, "terminal")
            )
            artifact_id = _artifact_id(details.get("terminal_artifact"))
        elif event_type in routes:
            namespace, purpose, field = routes[event_type]
            artifact_id = _artifact_id(details.get(field))
        else:
            raise ReconciliationReportValidationError(
                "Lifecycle event inventory contains an unknown event type."
            )
        _expect(
            expected,
            namespace=namespace,
            trace_id=_lifecycle_trace_id(job_id, purpose, artifact_id),
            job_id=job_id,
            purpose=purpose,
            required=True,
            issues=issues,
        )
    if state in _TERMINALS and terminal_status != state:
        raise ReconciliationReportValidationError(
            "Lifecycle terminal state differs from its terminal event."
        )
    if state in {OUTCOME_ACCESSED, PACKET_RECORDED, NONREPORTING_RECORDED} and terminal_status is None:
        raise ReconciliationReportValidationError(
            "Post-terminal lifecycle has no terminal event."
        )
    return terminal_status


def _expect(
    expected: dict[tuple[str, str], _ExpectedWrapper],
    *,
    namespace: str,
    trace_id: str,
    job_id: str,
    purpose: str,
    required: bool,
    issues: list[ReconciliationIssue],
) -> None:
    key = (namespace, trace_id)
    value = _ExpectedWrapper(job_id=job_id, purpose=purpose, required=required)
    prior = expected.get(key)
    if prior is not None and prior != value:
        issues.append(
            ReconciliationIssue(
                "EXPECTED_WRAPPER_IDENTITY_COLLISION",
                trace_id,
                "Two configured facts resolve to one wrapper identity.",
            )
        )
        return
    expected[key] = value


def _artifact_id(value: object) -> str:
    if not isinstance(value, Mapping):
        raise ReconciliationReportValidationError(
            "Lifecycle artifact binding is unavailable."
        )
    return _text(value.get("artifact_id"), "artifact_id")


def _state(value: object) -> str:
    state = _text(value, "lifecycle state")
    if state not in {
        AUTHORIZED,
        RUNNING,
        SUCCESS,
        FAILURE,
        INDETERMINATE,
        REJECTED,
        EXPIRED,
        OUTCOME_ACCESSED,
        PACKET_RECORDED,
        NONREPORTING_RECORDED,
    }:
        raise ReconciliationReportValidationError(
            "Lifecycle state is outside the closed state machine."
        )
    return state


def _state_classification(state: str) -> str:
    if state == AUTHORIZED:
        return "AUTHORIZED_PENDING_CONSUMPTION"
    if state == RUNNING:
        return "RUNNING_PENDING_TERMINAL"
    if state in _DIRECT_DISPOSITIONS:
        return "SERVER_TERMINAL_PENDING_NONREPORTING"
    if state in _STRICT_TERMINALS:
        return "STRICT_TERMINAL_PENDING_OUTCOME_ACCESS"
    if state == OUTCOME_ACCESSED:
        return "OUTCOME_ACCESSED_PENDING_REPORTING"
    if state in _REPORTING:
        return "REPORTING_DISPOSED"
    raise ReconciliationReportValidationError("Lifecycle classification is unavailable.")


def _lifecycle_trace_id(subject_id: str, purpose: str, identity: str) -> str:
    digest = hashlib.sha256(
        f"{subject_id}\0{purpose}\0{identity}".encode("utf-8")
    ).hexdigest()
    return "h2exact_" + digest


def _index_identity(row: EvidencePacketIndexEntry) -> dict[str, str]:
    return {
        "namespace": row.namespace,
        "trace_id": row.trace_id,
        "record_id": row.record_id,
        "content_sha256": row.content_sha256,
        "version_id": row.version_id,
    }


def _coverage(*, bridge_configured: bool) -> dict[str, str]:
    return {
        "source_completeness": (
            "AUTHENTICATED_CONFIGURED_FLEET_PLUS_TENANT_STATE_STORE_AND_REPOSITORY"
            + ("_PLUS_BRIDGE_INDEXES" if bridge_configured else "_BRIDGE_NOT_CONFIGURED")
        ),
        "fleet_state_scope": "PROCESS_LOCAL_CONFIGURED_SNAPSHOTS_NOT_DURABLE",
        "fleet_runtime_status_comparison": "NOT_EXPOSED_BY_INPUT_SEAM",
        "context_scope": "CONFIGURED_JOB_LOOKUP_AND_REPOSITORY_INDEX_ONLY",
        "registry_scope": "TENANT_STATE_STORE_ONLY",
        "artifact_scope": "CONFIGURED_TENANT_REPOSITORY_INDEX_ONLY",
        "tenant_ownership_limitation": (
            "FLEET_EXECUTOR_DOES_NOT_RETAIN_TENANT_OWNERSHIP_CALLER_SCOPE_REQUIRED"
        ),
        "other_audit_attribution": "NOT_ESTABLISHED_FOR_UNMATCHED_TENANT_ROWS",
        "off_registry_execution_absence": "NOT_ESTABLISHED",
        "trusted_time": "NOT_ESTABLISHED",
        "global_exhaustiveness": "NOT_ESTABLISHED",
    }


def _authority() -> dict[str, str]:
    return {
        "criteria_status": "OPEN",
        "execution_authentication": "NOT_ESTABLISHED",
        "trusted_time": "NOT_ESTABLISHED",
        "off_registry_execution_absence": "NOT_ESTABLISHED",
        "independent_authority": "NOT_ESTABLISHED",
        "scientific_status": "NOT_ESTABLISHED",
        "product_status": "NOT_ESTABLISHED",
        "license_status": "NOT LICENSED",
        "disclosure_status": "HELD",
    }


def _unavailable_report(
    *,
    report_id: str,
    scope: Mapping[str, str],
    source: str,
    source_status: Mapping[str, str],
) -> HarnessV2ReconciliationReport:
    statuses = dict(source_status)
    statuses[source] = "UNAVAILABLE_ENUMERATION_FAILED"
    issue = ReconciliationIssue(
        "SOURCE_ENUMERATION_UNAVAILABLE",
        source,
        "A required configured source could not be enumerated or reverified; no empty inventory conclusion was produced.",
    )
    payload = {
        "schema_version": REPORT_SCHEMA,
        "report_id": report_id,
        "availability": UNAVAILABLE,
        "scope": dict(scope),
        "source_status": dict(sorted(statuses.items())),
        "coverage": _coverage(
            bridge_configured=statuses.get("bridge_indices")
            != "NOT_CONFIGURED_OPTIONAL_SOURCE"
        ),
        "configured_fleet": None,
        "registry": None,
        "artifact_inventory": None,
        "bridge_inventory": None,
        "counts": {
            "configured_job_count": None,
            "matched_context_count": None,
            "matched_lifecycle_count": None,
            "tenant_lifecycle_count": None,
            "tenant_unmatched_lifecycle_count": None,
            "issue_count": 1,
        },
        "state_counts": None,
        "pending_inventory": None,
        "jobs": None,
        "issues": [issue.as_dict()],
        "authority": _authority(),
    }
    return _report(payload)


def _report(payload: Mapping[str, Any]) -> HarnessV2ReconciliationReport:
    material = _plain_mapping(payload, "reconciliation report")
    identity_body = dict(material)
    identity_body.pop("report_id", None)
    material["report_id"] = "h2reconcile_" + hashlib.sha256(
        _canonical_bytes(identity_body)
    ).hexdigest()
    raw = _canonical_bytes(material)
    counts = material.get("counts")
    if not isinstance(counts, Mapping):
        raise ReconciliationReportValidationError("Report counts are unavailable.")
    issue_count = counts.get("issue_count")
    configured_job_count = counts.get("configured_job_count")
    if type(issue_count) is not int or (
        configured_job_count is not None and type(configured_job_count) is not int
    ):
        raise ReconciliationReportValidationError("Report count types are invalid.")
    return HarnessV2ReconciliationReport(
        report_id=_text(material.get("report_id"), "report_id"),
        availability=_text(material.get("availability"), "availability"),
        canonical_bytes=raw,
        sha256=hashlib.sha256(raw).hexdigest().upper(),
        issue_count=issue_count,
        configured_job_count=configured_job_count,
    )


def _plain_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ReconciliationReportValidationError(f"{field} must be a mapping.")
    result = _plain_json(value, field)
    if type(result) is not dict:
        raise ReconciliationReportValidationError(f"{field} must be an object.")
    return result


def _plain_json(value: object, field: str) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str or key in result:
                raise ReconciliationReportValidationError(
                    f"{field} contains an invalid key."
                )
            result[key] = _plain_json(item, field)
        return result
    if type(value) in (tuple, list):
        return [_plain_json(item, field) for item in value]
    if type(value) in (str, int, bool) or value is None:
        return value
    raise ReconciliationReportValidationError(
        f"{field} contains non-JSON value {type(value).__name__}."
    )


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ReconciliationReportValidationError(
            "Reconciliation report is not canonical JSON."
        ) from exc


def _sha256_json(value: object) -> str:
    if isinstance(value, Mapping):
        body = _canonical_bytes(value)
    else:
        body = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    return hashlib.sha256(body).hexdigest().upper()


def _text(value: object, field: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > 2048
        or any(ord(character) < 32 for character in value)
    ):
        raise ReconciliationReportValidationError(
            f"{field} must be exact non-empty text."
        )
    return value


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdefABCDEF" for character in value)
    )


__all__ = [
    "AVAILABLE",
    "AVAILABLE_WITH_ISSUES",
    "HarnessV2ReconciliationReport",
    "HarnessV2ReconciliationReportService",
    "RECONCILIATION_NAMESPACE",
    "REPORT_SCHEMA",
    "ReconciliationIssue",
    "ReconciliationReportError",
    "ReconciliationReportValidationError",
    "UNAVAILABLE",
]
