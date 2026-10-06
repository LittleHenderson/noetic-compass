"""Durable, research-only per-attempt lifecycle for Diagnostic Stage C.

This additive module joins the strict diagnostic execution-v2 carriers to a
create-only, one-attempt state machine.  It deliberately does *not* modify or
widen any v1 carrier.  The registry can prove one winner only inside the atomic
scope of its selected backend: one locked Python process for the in-memory
backend, or one SQLite database file on one host for the SQLite backend.

Neither backend supplies trusted time, worker/model authentication, WORM
retention, replication, scientific validity, a product licence, or disclosure
authority.  Every public result therefore remains OPEN / NOT LICENSED / HELD.
"""

from __future__ import annotations

import base64
from collections.abc import Callable, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime
import hmac
import json
import os
import secrets
import sqlite3
import threading
from types import MappingProxyType
from typing import Any, Protocol

from . import diagnostic_execution_protocol as _execution
from . import diagnostic_study_protocol as _study

from ._strict_json import (
    canonical_json_bytes,
    canonical_sha256,
    freeze_json,
    load_json_object,
    sha256_bytes,
    thaw_json,
)
from ._validation import (
    ArtifactRef,
    SchemaValidationError,
    expect_enum,
    expect_int,
    expect_keys,
    expect_machine_id,
    expect_object,
    expect_sha256,
    expect_string,
    expect_timestamp,
    parse_artifact_ref,
)
from .diagnostic_execution_protocol import (
    DiagnosticChildExecutionBindingArtifact,
    DiagnosticChildTerminalReceiptV2Artifact,
    DiagnosticStageCExecutionContractArtifact,
    DiagnosticWorkerAuthorizationV2Artifact,
    build_diagnostic_child_execution_binding,
    build_diagnostic_child_terminal_receipt_v2,
    build_diagnostic_worker_authorization_v2,
    load_diagnostic_child_execution_binding,
    load_diagnostic_child_terminal_receipt_v2,
    load_diagnostic_worker_authorization_v2,
    replay_diagnostic_execution_family,
)
from .diagnostic_preregistration import DiagnosticPreregistrationChain
from .diagnostic_study_protocol import (
    DiagnosticStudyRequestArtifact,
    DiagnosticStudyPlanArtifact,
)


DIAGNOSTIC_ATTEMPT_LIFECYCLE_SCHEMA = (
    "cas_harness_v2.diagnostic_attempt_lifecycle.v1"
)
DIAGNOSTIC_ATTEMPT_EVENT_SCHEMA = "cas_harness_v2.diagnostic_attempt_event.v1"
DIAGNOSTIC_ATTEMPT_SUBJECT_DOMAIN = (
    "cas_harness_v2.diagnostic_child_attempt_subject.v2"
)

AUTHORIZED = "AUTHORIZED"
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
FAILED = "FAILED"
INDETERMINATE = "INDETERMINATE"
REJECTED = "REJECTED"
EXPIRED = "EXPIRED"

DIAGNOSTIC_TERMINAL_STATES = frozenset(
    {COMPLETED, FAILED, INDETERMINATE, REJECTED, EXPIRED}
)
DIAGNOSTIC_ATTEMPT_STATES = frozenset(
    {AUTHORIZED, RUNNING, *DIAGNOSTIC_TERMINAL_STATES}
)

_ALLOWED_TRANSITIONS = {
    AUTHORIZED: frozenset({RUNNING, REJECTED, EXPIRED}),
    RUNNING: frozenset({COMPLETED, FAILED, INDETERMINATE}),
}
_GENESIS_SHA256 = "0" * 64
_MAX_TEXT = 4096

_AUTHORITY = {
    "criteria_status": "OPEN",
    "product_claim_status": "NOT LICENSED",
    "disclosure_status": "HELD",
    "scope": "DIAGNOSTIC_RESEARCH_ONLY",
    "durable_one_use": "BACKEND_ATOMIC_SCOPE_ONLY",
    "trusted_time": "NOT_PROVIDED",
    "execution_authentication": "NOT_PROVIDED",
    "worm": "NOT_PROVIDED",
    "replication": "NOT_PROVIDED",
    "evidence_packet_v2": "FORBIDDEN",
    "scientific_conclusion": "NOT_ESTABLISHED",
    "product_route": "FORBIDDEN",
    "license": "NOT_GRANTED",
    "disclosure": "HELD",
}

_TIME_ASSURANCE = "CALLER_OR_PROCESS_TIME_NOT_TRUSTED"


class DiagnosticLifecycleError(RuntimeError):
    """Base error for the diagnostic per-attempt lifecycle."""


class DiagnosticLifecycleValidationError(DiagnosticLifecycleError):
    """A caller supplied malformed or mutually inconsistent exact facts."""


class DiagnosticLifecycleConflict(DiagnosticLifecycleError):
    """A create-only fact or monotone state conflicts with an operation."""


class DiagnosticLifecycleNotFound(DiagnosticLifecycleError):
    """No attempt exists in the requested tenant/subject scope."""


class DiagnosticLifecycleExpired(DiagnosticLifecycleConflict):
    """An authorization can no longer be consumed."""


class DiagnosticLifecycleVersionConflict(DiagnosticLifecycleConflict):
    """A compare-and-swap mutation lost to another writer."""


class DiagnosticLifecyclePersistenceError(DiagnosticLifecycleError):
    """The backing store failed or exposed internally inconsistent bytes."""


class DiagnosticLifecycleIntegrityError(DiagnosticLifecycleError):
    """Stored carriers, events, or state fail exact replay."""


@dataclass(frozen=True, slots=True, init=False, eq=False)
class DiagnosticSharedPlanReplayContext:
    """Prevalidated immutable kernel shared by every row in one 480-case plan.

    Construction performs the expensive canonical chain/plan/contract replay
    once.  Row loaders below recompute their exact canonical values against the
    indexed case/request/capture facts without replaying the full plan.
    """

    chain: DiagnosticPreregistrationChain
    plan: DiagnosticStudyPlanArtifact
    execution_contract: DiagnosticStageCExecutionContractArtifact
    kernel_sha256: str
    case_count: int
    planned_request_ids: Mapping[str, str]
    _case_by_id: Mapping[str, Any]
    _capture_by_case_id: Mapping[str, Any]
    _study_request_refs: tuple[ArtifactRef, ...]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError(
            "DiagnosticSharedPlanReplayContext is factory-only; use "
            "build_diagnostic_shared_plan_replay_context"
        )

    def build_study_request(
        self, *, case_id: str, created_at: str
    ) -> DiagnosticStudyRequestArtifact:
        return _shared_build_study_request(self, case_id=case_id, created_at=created_at)

    def replay_study_request(
        self, request: DiagnosticStudyRequestArtifact
    ) -> DiagnosticStudyRequestArtifact:
        return _shared_replay_study_request(self, request)


@dataclass(frozen=True, slots=True)
class _SharedRowSeal:
    case: Any
    capture: Any
    planned_request_id: str
    row_sha256: str
    binding_refs_template: tuple[Any, ...]
    predecessor_ids: frozenset[str]
    predecessor_content_identities: frozenset[tuple[str, int]]


@dataclass(slots=True)
class _SharedPlanSeal:
    context: DiagnosticSharedPlanReplayContext
    chain: DiagnosticPreregistrationChain
    plan: DiagnosticStudyPlanArtifact
    execution_contract: DiagnosticStageCExecutionContractArtifact
    chain_base: Any
    chain_amendments: tuple[Any, ...]
    chain_pre_outcome_sha256: str
    plan_raw_bytes: bytes
    plan_scalars: tuple[Any, ...]
    plan_inventory: Any
    plan_execution_identity_artifacts: tuple[ArtifactRef, ...]
    plan_payload: Mapping[str, Any]
    execution_contract_raw_bytes: bytes
    execution_contract_scalars: tuple[Any, ...]
    execution_contract_payload: Mapping[str, Any]
    execution_contract_artifact_refs: tuple[ArtifactRef, ...]
    kernel_sha256: str
    case_count: int
    planned_request_ids: Mapping[str, str]
    case_by_id: Mapping[str, Any]
    capture_by_case_id: Mapping[str, Any]
    study_request_refs: tuple[ArtifactRef, ...]
    plan_cases: tuple[Any, ...]
    plan_artifact_refs: tuple[ArtifactRef, ...]
    rows: Mapping[str, _SharedRowSeal]
    lock: threading.RLock
    binding_cache: dict[tuple[str, str], DiagnosticChildExecutionBindingArtifact]
    authorization_cache: dict[
        tuple[str, str, str], DiagnosticWorkerAuthorizationV2Artifact
    ]
    terminal_cache: dict[
        tuple[str, str, str | None, str, tuple[tuple[str, str], ...]],
        DiagnosticChildTerminalReceiptV2Artifact,
    ]


_SHARED_PLAN_SEALS_LOCK = threading.RLock()
_SHARED_PLAN_SEALS: dict[int, _SharedPlanSeal] = {}


@dataclass(frozen=True, slots=True)
class DiagnosticLifecycleReplayContext:
    """One exact row request bound to a prevalidated shared-plan kernel."""

    shared_plan: DiagnosticSharedPlanReplayContext
    study_request: DiagnosticStudyRequestArtifact

    @property
    def chain(self) -> DiagnosticPreregistrationChain:
        return self.shared_plan.chain

    @property
    def plan(self) -> DiagnosticStudyPlanArtifact:
        return self.shared_plan.plan

    @property
    def execution_contract(self) -> DiagnosticStageCExecutionContractArtifact:
        return self.shared_plan.execution_contract


@dataclass(frozen=True, slots=True)
class DiagnosticAttemptEventReceipt:
    raw_bytes: bytes
    sha256: str
    sequence: int
    event_type: str
    state_before: str | None
    state_after: str
    occurred_at: str
    operation_id: str
    operation_request_sha256: str
    payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class DiagnosticAttemptSnapshot:
    tenant_id: str
    attempt_subject_sha256: str
    attempt_ordinal: int
    study_id: str
    case_id: str
    case_execution_ordinal: int
    state: str
    record_version: int
    issuance_mode: str
    issuance_request_sha256: str
    run_nonce_sha256: str
    binding_ref: ArtifactRef
    authorization_ref: ArtifactRef | None
    terminal_receipt_ref: ArtifactRef | None
    worker_started_at: str | None
    created_at: str
    updated_at: str
    event_count: int
    head_event_sha256: str
    backend_durability_profile: Mapping[str, Any]
    authority: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class DiagnosticAttemptIssuance:
    snapshot: DiagnosticAttemptSnapshot
    binding: DiagnosticChildExecutionBindingArtifact
    authorization: DiagnosticWorkerAuthorizationV2Artifact
    run_nonce_b64url: str | None
    issued_now: bool


@dataclass(frozen=True, slots=True)
class DiagnosticAttemptMutation:
    snapshot: DiagnosticAttemptSnapshot
    binding: DiagnosticChildExecutionBindingArtifact
    authorization: DiagnosticWorkerAuthorizationV2Artifact | None
    terminal_receipt: DiagnosticChildTerminalReceiptV2Artifact | None
    event: DiagnosticAttemptEventReceipt
    transitioned_now: bool


@dataclass(frozen=True, slots=True)
class DiagnosticAttemptReplay:
    """Public, exact replay surface for the later aggregate coordinator."""

    snapshot: DiagnosticAttemptSnapshot
    binding: DiagnosticChildExecutionBindingArtifact
    authorization: DiagnosticWorkerAuthorizationV2Artifact | None
    terminal_receipt: DiagnosticChildTerminalReceiptV2Artifact | None
    produced_artifact_bodies: Mapping[str, bytes]
    events: tuple[DiagnosticAttemptEventReceipt, ...]


@dataclass(frozen=True, slots=True)
class DiagnosticAttemptReconciliationIssue:
    code: str
    attempt_subject_sha256: str
    detail: str


@dataclass(frozen=True, slots=True)
class DiagnosticAttemptReconciliation:
    tenant_id: str
    attempt_count: int
    event_count: int
    state_counts: Mapping[str, int]
    integrity_clean: bool
    all_terminal: bool
    issues: tuple[DiagnosticAttemptReconciliationIssue, ...]
    backend_durability_profile: Mapping[str, Any]
    authority: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class _StoredAttempt:
    tenant_id: str
    attempt_subject_sha256: str
    attempt_ordinal: int
    study_id: str
    case_id: str
    case_execution_ordinal: int
    issuance_mode: str
    issuance_request_sha256: str
    state: str
    version: int
    run_nonce_sha256: str
    binding_raw: bytes
    authorization_raw: bytes | None
    terminal_raw: bytes | None
    produced_artifact_bodies: tuple[tuple[str, bytes], ...]
    worker_started_at: str | None
    created_at: str
    updated_at: str
    event_count: int
    head_event_sha256: str


class DiagnosticLifecycleStore(Protocol):
    @property
    def durability_profile(self) -> Mapping[str, Any]: ...

    def create_attempt(
        self,
        attempt: _StoredAttempt,
        event: DiagnosticAttemptEventReceipt,
    ) -> _StoredAttempt: ...

    def compare_and_swap(
        self,
        attempt: _StoredAttempt,
        event: DiagnosticAttemptEventReceipt,
        *,
        expected_version: int,
    ) -> _StoredAttempt: ...

    def get_attempt(
        self, tenant_id: str, attempt_subject_sha256: str
    ) -> _StoredAttempt | None: ...

    def list_attempts(self, tenant_id: str) -> tuple[_StoredAttempt, ...]: ...

    def list_events(
        self, tenant_id: str, attempt_subject_sha256: str
    ) -> tuple[DiagnosticAttemptEventReceipt, ...]: ...


def _artifact_ref_value(reference: ArtifactRef) -> dict[str, Any]:
    return {
        "artifact_id": reference.artifact_id,
        "sha256": reference.sha256,
        "byte_length": reference.byte_length,
        "media_type": reference.media_type,
    }


def _required_text(value: Any, path: str, *, machine: bool = False) -> str:
    try:
        if machine:
            return expect_machine_id(value, path)
        return expect_string(value, path, maximum=_MAX_TEXT)
    except (SchemaValidationError, ValueError) as exc:
        raise DiagnosticLifecycleValidationError(str(exc)) from exc


def _required_sha256(value: Any, path: str) -> str:
    try:
        return expect_sha256(value, path)
    except (SchemaValidationError, ValueError) as exc:
        raise DiagnosticLifecycleValidationError(str(exc)) from exc


def _required_timestamp(value: Any, path: str) -> str:
    try:
        return expect_timestamp(value, path)
    except (SchemaValidationError, ValueError) as exc:
        raise DiagnosticLifecycleValidationError(str(exc)) from exc


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _b64(value: bytes) -> str:
    if type(value) is not bytes:
        raise DiagnosticLifecyclePersistenceError("stored body must be exact bytes")
    return base64.b64encode(value).decode("ascii")


def _unb64(value: Any, path: str) -> bytes:
    if type(value) is not str:
        raise DiagnosticLifecyclePersistenceError(f"{path} must be base64 text")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise DiagnosticLifecyclePersistenceError(f"{path} is invalid base64") from exc
    if _b64(raw) != value:
        raise DiagnosticLifecyclePersistenceError(f"{path} is noncanonical base64")
    return raw


def _frozen_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return freeze_json(thaw_json(value))


def build_diagnostic_shared_plan_replay_context(
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
) -> DiagnosticSharedPlanReplayContext:
    """Pay the full-plan validation cost once and freeze its 480-row index."""

    try:
        base = _execution._require_chain(chain, require_pre_outcome=True)
        replayed_plan = _execution._replay_plan(plan, chain=chain)
        replayed_contract = _execution._replay_contract(
            execution_contract, chain=chain, plan=replayed_plan
        )
        if replayed_plan != plan or replayed_contract != execution_contract:
            raise SchemaValidationError("shared replay kernel exact artifacts drifted")
        if len(plan.cases) != _study.DIAGNOSTIC_CASE_COUNT:
            raise SchemaValidationError("shared replay kernel requires exactly 480 cases")
        captures = plan.inventory.capture_requests
        if len(captures) != len(plan.cases):
            raise SchemaValidationError("case/capture inventory cardinality drifted")
        case_by_id: dict[str, Any] = {}
        capture_by_case: dict[str, Any] = {}
        planned_request_ids: dict[str, str] = {}
        for case, capture in zip(plan.cases, captures, strict=True):
            fresh_capture = _study.load_stagec_capture_request(
                capture.artifact_ref, capture.raw_bytes
            )
            if not _study._same_capture_request(fresh_capture, capture):
                raise SchemaValidationError("indexed capture request exact replay drifted")
            if (
                case.case_id in case_by_id
                or case.case_id != capture.case_id
                or case.capture_request != capture.artifact_ref
            ):
                raise SchemaValidationError("shared case/capture index is not one-to-one")
            case_by_id[case.case_id] = case
            capture_by_case[case.case_id] = fresh_capture
            planned_request_ids[case.case_id] = case.study_request_id
        first_capture = next(iter(capture_by_case.values()))
        request_refs = _study._study_request_refs(
            chain=chain, plan=plan, capture_request=first_capture
        )
        rows: dict[str, _SharedRowSeal] = {}
        plan_refs = tuple(plan.artifact_refs)
        for case in plan.cases:
            capture = capture_by_case[case.case_id]
            ordered: list[ArtifactRef] = []
            by_id: dict[str, ArtifactRef] = {}
            by_content: dict[tuple[str, int], str] = {}
            for reference in (
                execution_contract.artifact_ref,
                plan.artifact_ref,
                capture.artifact_ref,
                *plan_refs,
            ):
                prior = by_id.get(reference.artifact_id)
                if prior is not None:
                    if prior != reference:
                        raise SchemaValidationError(
                            "shared binding template reuses an ID for different bytes"
                        )
                    continue
                identity = (reference.sha256, reference.byte_length)
                prior_id = by_content.get(identity)
                if prior_id is not None and prior_id != reference.artifact_id:
                    raise SchemaValidationError(
                        "shared binding template clones a content identity"
                    )
                by_id[reference.artifact_id] = reference
                by_content[identity] = reference.artifact_id
                ordered.append(reference)
            # Exact row order is contract, plan, request, capture, then the
            # remaining plan closure.  None is a process-private request slot.
            if ordered[:3] != [
                execution_contract.artifact_ref,
                plan.artifact_ref,
                capture.artifact_ref,
            ]:
                raise SchemaValidationError("shared binding template prefix drifted")
            template: tuple[Any, ...] = (
                ordered[0],
                ordered[1],
                None,
                *ordered[2:],
            )
            row_sha = canonical_sha256(
                {
                    "domain": "cas_harness_v2.diagnostic_shared_plan_row_seal.v1",
                    "case": {
                        "execution_ordinal": case.execution_ordinal,
                        "case_id": case.case_id,
                        "study_request_id": case.study_request_id,
                        "split_id": case.split_id,
                        "base_intent_group_id": case.base_intent_group_id,
                        "frozen_variant": case.frozen_variant,
                        "frozen_label": case.frozen_label,
                        "invocation_id": case.invocation_id,
                        "capture_request": _artifact_ref_value(case.capture_request),
                    },
                    "capture": _artifact_ref_value(capture.artifact_ref),
                    "capture_bytes_sha256": sha256_bytes(capture.raw_bytes),
                }
            )
            rows[case.case_id] = _SharedRowSeal(
                case=case,
                capture=capture,
                planned_request_id=case.study_request_id,
                row_sha256=row_sha,
                binding_refs_template=template,
                predecessor_ids=frozenset(by_id),
                predecessor_content_identities=frozenset(by_content),
            )
        kernel_sha = canonical_sha256(
            {
                "domain": "cas_harness_v2.diagnostic_shared_plan_replay_context.v1",
                "pre_outcome_chain_sha256": plan.pre_outcome_chain_sha256,
                "base": _artifact_ref_value(_execution._base_ref(base)),
                "plan": _artifact_ref_value(plan.artifact_ref),
                "execution_contract": _artifact_ref_value(execution_contract.artifact_ref),
                "rows": [
                    {
                        "execution_ordinal": case.execution_ordinal,
                        "case_id": case.case_id,
                        "study_request_id": case.study_request_id,
                        "row_sha256": rows[case.case_id].row_sha256,
                    }
                    for case in plan.cases
                ],
            }
        )
    except (SchemaValidationError, ValueError, TypeError, KeyError) as exc:
        raise DiagnosticLifecycleValidationError(
            f"shared plan replay context validation failed: {exc}"
        ) from exc
    planned_proxy = MappingProxyType(planned_request_ids)
    case_proxy = MappingProxyType(case_by_id)
    capture_proxy = MappingProxyType(capture_by_case)
    rows_proxy = MappingProxyType(rows)
    context = object.__new__(DiagnosticSharedPlanReplayContext)
    object.__setattr__(context, "chain", chain)
    object.__setattr__(context, "plan", plan)
    object.__setattr__(context, "execution_contract", execution_contract)
    object.__setattr__(context, "kernel_sha256", kernel_sha)
    object.__setattr__(context, "case_count", len(case_by_id))
    object.__setattr__(context, "planned_request_ids", planned_proxy)
    object.__setattr__(context, "_case_by_id", case_proxy)
    object.__setattr__(context, "_capture_by_case_id", capture_proxy)
    object.__setattr__(context, "_study_request_refs", request_refs)
    seal = _SharedPlanSeal(
        context=context,
        chain=chain,
        plan=plan,
        execution_contract=execution_contract,
        chain_base=getattr(
            chain, "_DiagnosticPreregistrationChain__base"
        ),
        chain_amendments=getattr(
            chain, "_DiagnosticPreregistrationChain__amendments"
        ),
        chain_pre_outcome_sha256=chain._pre_outcome_chain_sha256(),
        plan_raw_bytes=plan.raw_bytes,
        plan_scalars=(
            plan.sha256,
            plan.byte_length,
            plan.plan_id,
            plan.study_id,
            plan.created_at,
            plan.pre_outcome_chain_sha256,
            plan.protected_design_sha256,
            plan.execution_window_start,
            plan.execution_window_end,
        ),
        plan_inventory=plan.inventory,
        plan_execution_identity_artifacts=plan.execution_identity_artifacts,
        plan_payload=plan.payload,
        execution_contract_raw_bytes=execution_contract.raw_bytes,
        execution_contract_scalars=(
            execution_contract.sha256,
            execution_contract.byte_length,
            execution_contract.contract_id,
            execution_contract.created_at,
        ),
        execution_contract_payload=execution_contract.payload,
        execution_contract_artifact_refs=execution_contract.artifact_refs,
        kernel_sha256=kernel_sha,
        case_count=len(case_by_id),
        planned_request_ids=planned_proxy,
        case_by_id=case_proxy,
        capture_by_case_id=capture_proxy,
        study_request_refs=request_refs,
        plan_cases=plan.cases,
        plan_artifact_refs=plan.artifact_refs,
        rows=rows_proxy,
        lock=threading.RLock(),
        binding_cache={},
        authorization_cache={},
        terminal_cache={},
    )
    with _SHARED_PLAN_SEALS_LOCK:
        _SHARED_PLAN_SEALS[id(context)] = seal
    return context


def _verify_shared_scope(
    shared: DiagnosticSharedPlanReplayContext,
    *,
    chain: DiagnosticPreregistrationChain,
    plan: DiagnosticStudyPlanArtifact,
    execution_contract: DiagnosticStageCExecutionContractArtifact,
) -> None:
    seal = _require_shared_seal(shared)
    if (
        chain is not seal.chain
        or plan is not seal.plan
        or execution_contract is not seal.execution_contract
        or plan.artifact_ref != seal.plan.artifact_ref
        or execution_contract.artifact_ref != seal.execution_contract.artifact_ref
    ):
        raise DiagnosticLifecycleValidationError(
            "row inputs do not belong to the supplied shared-plan context"
        )


def _require_shared_seal(
    shared: DiagnosticSharedPlanReplayContext,
) -> _SharedPlanSeal:
    if type(shared) is not DiagnosticSharedPlanReplayContext:
        raise DiagnosticLifecycleValidationError(
            "shared plan context must have the exact factory-only type"
        )
    with _SHARED_PLAN_SEALS_LOCK:
        seal = _SHARED_PLAN_SEALS.get(id(shared))
    if (
        seal is None
        or seal.context is not shared
        or shared.chain is not seal.chain
        or shared.plan is not seal.plan
        or shared.execution_contract is not seal.execution_contract
        or getattr(shared.chain, "_DiagnosticPreregistrationChain__base", None)
        is not seal.chain_base
        or getattr(shared.chain, "_DiagnosticPreregistrationChain__amendments", None)
        is not seal.chain_amendments
        or getattr(shared.chain, "_DiagnosticPreregistrationChain__outcome_index", None)
        is not None
        or getattr(shared.chain, "_DiagnosticPreregistrationChain__outcome_access", None)
        is not None
        or shared.chain._pre_outcome_chain_sha256()
        != seal.chain_pre_outcome_sha256
        or shared.plan.raw_bytes is not seal.plan_raw_bytes
        or (
            shared.plan.sha256,
            shared.plan.byte_length,
            shared.plan.plan_id,
            shared.plan.study_id,
            shared.plan.created_at,
            shared.plan.pre_outcome_chain_sha256,
            shared.plan.protected_design_sha256,
            shared.plan.execution_window_start,
            shared.plan.execution_window_end,
        )
        != seal.plan_scalars
        or shared.plan.inventory is not seal.plan_inventory
        or shared.plan.execution_identity_artifacts
        is not seal.plan_execution_identity_artifacts
        or shared.plan.payload is not seal.plan_payload
        or shared.execution_contract.raw_bytes
        is not seal.execution_contract_raw_bytes
        or (
            shared.execution_contract.sha256,
            shared.execution_contract.byte_length,
            shared.execution_contract.contract_id,
            shared.execution_contract.created_at,
        )
        != seal.execution_contract_scalars
        or shared.execution_contract.payload
        is not seal.execution_contract_payload
        or shared.execution_contract.artifact_refs
        is not seal.execution_contract_artifact_refs
        or shared.kernel_sha256 != seal.kernel_sha256
        or shared.case_count != seal.case_count
        or shared.planned_request_ids is not seal.planned_request_ids
        or shared._case_by_id is not seal.case_by_id
        or shared._capture_by_case_id is not seal.capture_by_case_id
        or shared._study_request_refs is not seal.study_request_refs
        or shared.plan.cases is not seal.plan_cases
        or shared.plan.artifact_refs is not seal.plan_artifact_refs
    ):
        raise DiagnosticLifecycleValidationError(
            "shared plan context is not the unchanged process-sealed factory result"
        )
    return seal


def _shared_row_seal(
    shared: DiagnosticSharedPlanReplayContext,
    case_id: str,
) -> _SharedRowSeal:
    seal = _require_shared_seal(shared)
    row = seal.rows.get(case_id)
    if row is None:
        raise DiagnosticLifecycleValidationError(
            "case_id is absent from the sealed 480-case index"
        )
    case = shared._case_by_id.get(case_id)
    capture = shared._capture_by_case_id.get(case_id)
    request_id = shared.planned_request_ids.get(case_id)
    if case is not row.case or capture is not row.capture or request_id != row.planned_request_id:
        raise DiagnosticLifecycleValidationError("shared row index identity drifted")
    observed_sha = canonical_sha256(
        {
            "domain": "cas_harness_v2.diagnostic_shared_plan_row_seal.v1",
            "case": {
                "execution_ordinal": case.execution_ordinal,
                "case_id": case.case_id,
                "study_request_id": case.study_request_id,
                "split_id": case.split_id,
                "base_intent_group_id": case.base_intent_group_id,
                "frozen_variant": case.frozen_variant,
                "frozen_label": case.frozen_label,
                "invocation_id": case.invocation_id,
                "capture_request": _artifact_ref_value(case.capture_request),
            },
            "capture": _artifact_ref_value(capture.artifact_ref),
            "capture_bytes_sha256": sha256_bytes(capture.raw_bytes),
        }
    )
    if observed_sha != row.row_sha256:
        raise DiagnosticLifecycleValidationError("shared row index digest drifted")
    return row


def _shared_request_value(
    shared: DiagnosticSharedPlanReplayContext,
    *,
    case_id: str,
    created_at: str,
) -> tuple[dict[str, Any], Any, Any]:
    case_id = _required_text(case_id, "case_id", machine=True)
    row = _shared_row_seal(shared, case_id)
    case = row.case
    capture = row.capture
    created_at = _required_timestamp(created_at, "created_at")
    if _time(created_at) <= _time(shared.plan.created_at) or _time(
        created_at
    ) >= _time(shared.plan.execution_window_start):
        raise DiagnosticLifecycleValidationError(
            "Study request creation lies outside the frozen pre-window interval"
        )
    value = {
        "schema_version": _study.DIAGNOSTIC_STUDY_REQUEST_SCHEMA,
        "request_id": case.study_request_id,
        "created_at": created_at,
        "diagnostic_study_plan": _artifact_ref_value(shared.plan.artifact_ref),
        "diagnostic_preregistration_binding": {
            "base_artifact": _artifact_ref_value(
                _execution._base_ref(shared.chain.base)
            ),
            "pre_outcome_chain_sha256": shared.plan.pre_outcome_chain_sha256,
            "protected_design_sha256": shared.plan.protected_design_sha256,
        },
        "case_binding": {
            "study_id": shared.plan.study_id,
            "case_id": case.case_id,
            "execution_ordinal": case.execution_ordinal,
            "split_id": case.split_id,
            "base_intent_group_id": case.base_intent_group_id,
            "frozen_variant": case.frozen_variant,
            "frozen_label": case.frozen_label,
            "invocation_id": case.invocation_id,
        },
        "capture_request": _artifact_ref_value(capture.artifact_ref),
        "execution_window": thaw_json(shared.plan.payload["execution_window"]),
        "retry_policy": dict(_study._RETRY_POLICY),
        "boundary": dict(_study._REQUEST_BOUNDARY),
        "authority": dict(_study._AUTHORITY),
        "governance": thaw_json(shared.chain.base.payload["governance"]),
    }
    return value, case, capture


def _shared_build_study_request(
    shared: DiagnosticSharedPlanReplayContext,
    *,
    case_id: str,
    created_at: str,
) -> DiagnosticStudyRequestArtifact:
    value, case, capture = _shared_request_value(
        shared, case_id=case_id, created_at=created_at
    )
    raw = canonical_json_bytes(value)
    return DiagnosticStudyRequestArtifact(
        raw_bytes=raw,
        sha256=sha256_bytes(raw),
        byte_length=len(raw),
        request_id=case.study_request_id,
        created_at=value["created_at"],
        study_id=shared.plan.study_id,
        case_id=case.case_id,
        execution_ordinal=case.execution_ordinal,
        capture_request=capture.artifact_ref,
        payload=freeze_json(value),
        artifact_refs=shared._study_request_refs,
    )


def _shared_replay_study_request(
    shared: DiagnosticSharedPlanReplayContext,
    request: DiagnosticStudyRequestArtifact,
) -> DiagnosticStudyRequestArtifact:
    if type(request) is not DiagnosticStudyRequestArtifact:
        raise DiagnosticLifecycleValidationError(
            "study_request must be an exact DiagnosticStudyRequestArtifact"
        )
    try:
        snapshot, obj = load_json_object(request.raw_bytes)
        if snapshot != canonical_json_bytes(obj):
            raise SchemaValidationError("Study request bytes are not canonical")
        case_binding = expect_object(obj.get("case_binding"), "$.case_binding")
        case_id = expect_machine_id(case_binding.get("case_id"), "$.case_binding.case_id")
        created_at = expect_timestamp(obj.get("created_at"), "$.created_at")
        expected = _shared_build_study_request(
            shared, case_id=case_id, created_at=created_at
        )
        if request != expected or obj != thaw_json(expected.payload):
            raise SchemaValidationError(
                "Study request differs from shared-plan exact replay"
            )
    except DiagnosticLifecycleError:
        raise
    except (SchemaValidationError, ValueError, TypeError, KeyError) as exc:
        raise DiagnosticLifecycleIntegrityError(
            f"shared Study request replay failed: {exc}"
        ) from exc
    return expected


def _shared_binding_value(
    shared: DiagnosticSharedPlanReplayContext,
    request: DiagnosticStudyRequestArtifact,
    *,
    binding_id: str,
    created_at: str,
    run_nonce_b64url: str,
    run_nonce_sha256: str,
    assigned_worker_id: str,
    archive_root: str,
    artifact_ids: Mapping[str, str],
) -> tuple[dict[str, Any], str, int, tuple[ArtifactRef, ...], Any]:
    request = shared.replay_study_request(request)
    row_seal = _shared_row_seal(shared, request.case_id)
    case = row_seal.case
    capture = row_seal.capture
    binding_id = expect_machine_id(binding_id, "binding_id")
    created_at = expect_timestamp(created_at, "created_at")
    if _time(created_at) <= max(
        _time(request.created_at), _time(shared.execution_contract.created_at)
    ) or _time(created_at) >= _time(shared.plan.execution_window_start):
        raise SchemaValidationError("child binding time is outside its exact pre-window interval")
    assigned_worker_id = expect_machine_id(assigned_worker_id, "assigned_worker_id")
    archive_root = _execution._require_absolute_archive_root(archive_root)
    ids = _execution._artifact_ids(artifact_ids)
    _execution._validate_nonce_binding(
        {
            "value_b64url": run_nonce_b64url,
            "sha256": run_nonce_sha256,
            "profile": "CALLER_DECLARED_CSPRNG_256_BIT",
            "structural_assurance": "LENGTH_ENCODING_AND_DIGEST_ONLY",
        },
        "run_nonce",
    )
    request_ref = request.artifact_ref
    request_identity = (request_ref.sha256, request_ref.byte_length)
    if (
        request_ref.artifact_id != row_seal.planned_request_id
        or request_ref.artifact_id in row_seal.predecessor_ids
        or request_identity in row_seal.predecessor_content_identities
        or row_seal.binding_refs_template[2] is not None
    ):
        raise SchemaValidationError("Study request collides with sealed predecessors")
    refs = (
        *row_seal.binding_refs_template[:2],
        request_ref,
        *row_seal.binding_refs_template[3:],
    )
    reserved_ids = {binding_id, *ids.values()}
    if len(reserved_ids) != len(ids) + 1:
        raise SchemaValidationError("binding_id collides with a prospective child artifact")
    collisions = reserved_ids.intersection(
        {*row_seal.predecessor_ids, request_ref.artifact_id}
    )
    if collisions:
        raise SchemaValidationError("prospective child artifact ID collides with predecessor")
    auth_projection = _execution._authorization_projection_ref(
        artifact_id=ids["authorization_projection"],
        plan=shared.plan,
        capture_request=capture,
    )
    case_binding = {
        "study_id": shared.plan.study_id,
        "case_id": case.case_id,
        "case_execution_ordinal": case.execution_ordinal,
        "split_id": case.split_id,
        "base_intent_group_id": case.base_intent_group_id,
        "frozen_variant": case.frozen_variant,
        "frozen_label": case.frozen_label,
        "invocation_id": case.invocation_id,
    }
    subject = canonical_sha256(
        {
            "domain": DIAGNOSTIC_ATTEMPT_SUBJECT_DOMAIN,
            "pre_outcome_chain_sha256": shared.plan.pre_outcome_chain_sha256,
            "study_plan": _artifact_ref_value(shared.plan.artifact_ref),
            "study_request": _artifact_ref_value(request.artifact_ref),
            "case_execution_ordinal": case.execution_ordinal,
        }
    )
    expected_member_ids = {
        "request_artifact": capture.artifact_ref.artifact_id,
        "authorization_projection_artifact": ids["authorization_projection"],
        "capture_index_artifact": ids["capture_index"],
        "input_ids": ids["input_ids"],
        "attention_mask": ids["attention_mask"],
        "target_vector": ids["target_vector"],
        "wrong_layer_vector": ids["wrong_layer_vector"],
    }
    capture_contract = _execution._STAGEC_CAPTURE
    context = {
        "diagnostic_preregistration_binding": thaw_json(
            shared.plan.payload["diagnostic_preregistration_binding"]
        ),
        "study_binding": {
            "diagnostic_study_plan": _artifact_ref_value(shared.plan.artifact_ref),
            "diagnostic_study_request": _artifact_ref_value(request.artifact_ref),
            "stagec_capture_request": _artifact_ref_value(capture.artifact_ref),
        },
        "case_binding": case_binding,
        "execution_contract": _artifact_ref_value(shared.execution_contract.artifact_ref),
        "execution_identity_artifacts": [
            _artifact_ref_value(reference)
            for reference in shared.plan.execution_identity_artifacts
        ],
        "model_runtime_capture_contract": {
            "model_contract": thaw_json(shared.execution_contract.payload["model_contract"]),
            "runtime_contract": thaw_json(shared.execution_contract.payload["runtime_contract"]),
            "capture_contract": thaw_json(shared.execution_contract.payload["capture_contract"]),
        },
        "attempt_binding": {
            "attempt_subject_sha256": subject,
            "run_nonce": {
                "value_b64url": run_nonce_b64url,
                "sha256": run_nonce_sha256,
                "profile": "CALLER_DECLARED_CSPRNG_256_BIT",
                "structural_assurance": "LENGTH_ENCODING_AND_DIGEST_ONLY",
            },
            "retry_policy": dict(_execution._RETRY_POLICY),
        },
        "worker_assignment": {
            "assigned_worker_id": assigned_worker_id,
            "assignment_semantic": "PROSPECTIVE_STRUCTURAL_BINDING_ONLY",
        },
        "execution_window": thaw_json(shared.plan.payload["execution_window"]),
        "artifact_expectations": {
            "authorization": {
                "artifact_id": ids["authorization"],
                "schema_version": _execution.DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA,
                "media_type": _execution.DIAGNOSTIC_WORKER_AUTHORIZATION_V2_MEDIA_TYPE,
            },
            "capture": {
                "authorization_projection": _artifact_ref_value(auth_projection),
                "capture_index": {
                    "artifact_id": ids["capture_index"],
                    "schema_version": capture_contract["capture_index_schema"],
                    "media_type": capture_contract["capture_index_media_type"],
                },
                "raw_arrays": {
                    "input_ids": {"artifact_id": ids["input_ids"], "dtype": "<i8", "role": "input_ids"},
                    "attention_mask": {"artifact_id": ids["attention_mask"], "dtype": "<i8", "role": "attention_mask"},
                    "target_vector": {"artifact_id": ids["target_vector"], "dtype": "<f4", "role": "target_final_token_activation", "layer_index": 18, "module_path": capture_contract["target_module_path"]},
                    "wrong_layer_vector": {"artifact_id": ids["wrong_layer_vector"], "dtype": "<f4", "role": "wrong_layer_final_token_activation", "layer_index": 0, "module_path": capture_contract["wrong_layer_module_path"]},
                },
            },
            "archive": {
                "schema_version": "cas_harness.stagec.local_capture_archive.v1",
                "media_type": "application/vnd.cas-harness.stagec-local-capture-archive+json",
                "manifest_name": "stagec-local-capture-archive.v1.json",
                "manifest_id_derivation": "stagec-local-archive- + lowercase_sha256(canonical_capture_index_ref_payload)",
                "content_path_derivation": "objects/sha256/<first-2-lowercase-digest>/<remaining-62>",
                "absolute_root": archive_root,
                "ordered_member_roles": list(_execution._ARCHIVE_MEMBER_ROLES),
                "expected_member_artifact_ids": expected_member_ids,
                "admission": {
                    "artifact_id": ids["archive_admission"],
                    "schema_version": _execution.DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_SCHEMA,
                    "media_type": _execution.DIAGNOSTIC_STAGEC_ARCHIVE_ADMISSION_MEDIA_TYPE,
                    "admission_domain": "FACTORY_ONLY_FRESH_WORKER_LOCAL_ARCHIVE_REPLAY_V2",
                },
            },
            "output": {
                "artifact_id": ids["child_output"],
                "output_name": "diagnostic_stagec_child_output",
                "schema_version": _execution.DIAGNOSTIC_STAGEC_CHILD_OUTPUT_SCHEMA,
                "media_type": _execution.DIAGNOSTIC_STAGEC_CHILD_OUTPUT_MEDIA_TYPE,
            },
            "terminal_receipt": {
                "artifact_id": ids["terminal_receipt"],
                "schema_version": _execution.DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA,
                "media_type": _execution.DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_MEDIA_TYPE,
            },
        },
    }
    context_bytes = canonical_json_bytes(context)
    context_sha = sha256_bytes(context_bytes)
    value = {
        "schema_version": _execution.DIAGNOSTIC_CHILD_EXECUTION_BINDING_SCHEMA,
        "binding_id": binding_id,
        "created_at": created_at,
        "execution_context": context,
        "execution_context_sha256": context_sha,
        "execution_context_byte_length": len(context_bytes),
        "boundary": dict(_execution._BINDING_BOUNDARY),
        "authority": dict(_execution._AUTHORITY),
        "governance": thaw_json(shared.chain.base.payload["governance"]),
    }
    return value, context_sha, len(context_bytes), refs, case


def _shared_load_binding(
    shared: DiagnosticSharedPlanReplayContext,
    request: DiagnosticStudyRequestArtifact,
    raw: bytes,
) -> DiagnosticChildExecutionBindingArtifact:
    request = shared.replay_study_request(request)
    seal = _require_shared_seal(shared)
    raw_sha = sha256_bytes(raw)
    cache_key = (request.sha256, raw_sha)
    with seal.lock:
        cached = seal.binding_cache.get(cache_key)
    if cached is not None:
        if cached.raw_bytes != raw:
            raise DiagnosticLifecycleIntegrityError("binding cache digest collision")
        return cached
    snapshot, obj = _execution._canonical_object(raw, "diagnostic child execution binding")
    context = expect_object(obj.get("execution_context"), "$.execution_context")
    attempt = expect_object(context.get("attempt_binding"), "$.execution_context.attempt_binding")
    nonce, nonce_sha = _execution._validate_nonce_binding(
        attempt.get("run_nonce"), "$.execution_context.attempt_binding.run_nonce"
    )
    worker = expect_object(context.get("worker_assignment"), "$.execution_context.worker_assignment")
    expectations = expect_object(context.get("artifact_expectations"), "$.execution_context.artifact_expectations")
    archive = expect_object(expectations.get("archive"), "$.execution_context.artifact_expectations.archive")
    capture = expect_object(expectations.get("capture"), "$.execution_context.artifact_expectations.capture")
    arrays = expect_object(capture.get("raw_arrays"), "$.execution_context.artifact_expectations.capture.raw_arrays")
    ids = {
        "authorization": expect_object(expectations.get("authorization"), "$.authorization")["artifact_id"],
        "authorization_projection": expect_object(capture.get("authorization_projection"), "$.authorization_projection")["artifact_id"],
        "capture_index": expect_object(capture.get("capture_index"), "$.capture_index")["artifact_id"],
        "input_ids": expect_object(arrays.get("input_ids"), "$.input_ids")["artifact_id"],
        "attention_mask": expect_object(arrays.get("attention_mask"), "$.attention_mask")["artifact_id"],
        "target_vector": expect_object(arrays.get("target_vector"), "$.target_vector")["artifact_id"],
        "wrong_layer_vector": expect_object(arrays.get("wrong_layer_vector"), "$.wrong_layer_vector")["artifact_id"],
        "archive_admission": expect_object(archive.get("admission"), "$.archive.admission")["artifact_id"],
        "child_output": expect_object(expectations.get("output"), "$.output")["artifact_id"],
        "terminal_receipt": expect_object(expectations.get("terminal_receipt"), "$.terminal_receipt")["artifact_id"],
    }
    value, context_sha, context_length, refs, case = _shared_binding_value(
        shared,
        request,
        binding_id=expect_machine_id(obj.get("binding_id"), "$.binding_id"),
        created_at=expect_timestamp(obj.get("created_at"), "$.created_at"),
        run_nonce_b64url=nonce,
        run_nonce_sha256=nonce_sha,
        assigned_worker_id=worker.get("assigned_worker_id"),
        archive_root=archive.get("absolute_root"),
        artifact_ids=ids,
    )
    if obj != value:
        raise SchemaValidationError("child binding differs from shared-plan exact replay")
    result = DiagnosticChildExecutionBindingArtifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        binding_id=value["binding_id"],
        created_at=value["created_at"],
        study_id=request.study_id,
        case_id=request.case_id,
        case_execution_ordinal=case.execution_ordinal,
        attempt_ordinal=1,
        run_nonce_b64url=nonce,
        execution_context_sha256=context_sha,
        execution_context_byte_length=context_length,
        payload=freeze_json(obj),
        artifact_refs=refs,
    )
    with seal.lock:
        prior = seal.binding_cache.setdefault(cache_key, result)
    if prior != result or prior.raw_bytes != result.raw_bytes:
        raise DiagnosticLifecycleIntegrityError("binding cache exact replay drifted")
    return prior


def _shared_build_binding(
    shared: DiagnosticSharedPlanReplayContext,
    request: DiagnosticStudyRequestArtifact,
    *,
    binding_id: str,
    created_at: str,
    run_nonce: bytes,
    assigned_worker_id: str,
    archive_root: str,
    artifact_ids: Mapping[str, str],
) -> DiagnosticChildExecutionBindingArtifact:
    nonce, nonce_sha = _execution._nonce_value(run_nonce)
    value, _sha, _length, _refs, _case = _shared_binding_value(
        shared,
        request,
        binding_id=binding_id,
        created_at=created_at,
        run_nonce_b64url=nonce,
        run_nonce_sha256=nonce_sha,
        assigned_worker_id=assigned_worker_id,
        archive_root=archive_root,
        artifact_ids=artifact_ids,
    )
    return _shared_load_binding(shared, request, canonical_json_bytes(value))


def _shared_authorization_value(
    shared: DiagnosticSharedPlanReplayContext,
    request: DiagnosticStudyRequestArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    *,
    issued_at: str,
    expires_at: str,
) -> tuple[dict[str, Any], str, tuple[ArtifactRef, ...]]:
    binding = _shared_load_binding(shared, request, binding.raw_bytes)
    expectations = binding.payload["execution_context"]["artifact_expectations"]
    authorization_id = expect_machine_id(
        expectations["authorization"]["artifact_id"], "authorization_id"
    )
    issued_at = expect_timestamp(issued_at, "issued_at")
    expires_at = expect_timestamp(expires_at, "expires_at")
    not_before = shared.plan.execution_window_start
    if (
        _time(issued_at) <= _time(binding.created_at)
        or _time(issued_at) >= _time(expires_at)
        or _time(expires_at) > _time(shared.plan.execution_window_end)
        or _time(expires_at) <= _time(not_before)
    ):
        raise SchemaValidationError("authorization interval is outside its exact Study window")
    context = binding.payload["execution_context"]
    value = {
        "schema_version": _execution.DIAGNOSTIC_WORKER_AUTHORIZATION_V2_SCHEMA,
        "authorization_id": authorization_id,
        "issued_at": issued_at,
        "not_before": not_before,
        "expires_at": expires_at,
        "child_execution_binding": _artifact_ref_value(binding.artifact_ref),
        "execution_context": thaw_json(context),
        "execution_context_sha256": binding.execution_context_sha256,
        "execution_context_byte_length": binding.execution_context_byte_length,
        "boundary": dict(_execution._AUTHORIZATION_BOUNDARY),
        "authority": dict(_execution._AUTHORITY),
        "governance": thaw_json(shared.chain.base.payload["governance"]),
    }
    row_seal = _shared_row_seal(shared, request.case_id)
    binding_ref = binding.artifact_ref
    if (
        binding_ref.artifact_id in {
            *row_seal.predecessor_ids,
            request.artifact_ref.artifact_id,
        }
        or (binding_ref.sha256, binding_ref.byte_length)
        in {
            *row_seal.predecessor_content_identities,
            (request.artifact_ref.sha256, request.artifact_ref.byte_length),
        }
    ):
        raise SchemaValidationError("binding collides with a sealed predecessor")
    refs = (binding_ref, *binding.artifact_refs)
    if authorization_id in {
        *row_seal.predecessor_ids,
        request.artifact_ref.artifact_id,
        binding_ref.artifact_id,
    }:
        raise SchemaValidationError("authorization_id collides with a predecessor")
    return value, authorization_id, refs


def _shared_load_authorization(
    shared: DiagnosticSharedPlanReplayContext,
    request: DiagnosticStudyRequestArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    raw: bytes,
) -> DiagnosticWorkerAuthorizationV2Artifact:
    request = shared.replay_study_request(request)
    binding = _shared_load_binding(shared, request, binding.raw_bytes)
    seal = _require_shared_seal(shared)
    raw_sha = sha256_bytes(raw)
    cache_key = (request.sha256, binding.sha256, raw_sha)
    with seal.lock:
        cached = seal.authorization_cache.get(cache_key)
    if cached is not None:
        if cached.raw_bytes != raw:
            raise DiagnosticLifecycleIntegrityError("authorization cache digest collision")
        return cached
    snapshot, obj = _execution._canonical_object(raw, "diagnostic worker authorization v2")
    issued_at = expect_timestamp(obj.get("issued_at"), "$.issued_at")
    expires_at = expect_timestamp(obj.get("expires_at"), "$.expires_at")
    value, authorization_id, refs = _shared_authorization_value(
        shared, request, binding, issued_at=issued_at, expires_at=expires_at
    )
    if obj != value:
        raise SchemaValidationError("authorization differs from shared-plan exact replay")
    context_sha = expect_sha256(obj.get("execution_context_sha256"), "$.execution_context_sha256")
    context_length = expect_int(
        obj.get("execution_context_byte_length"),
        "$.execution_context_byte_length",
        minimum=1,
    )
    _execution._require_context_copy(
        obj.get("execution_context"),
        expected=binding.payload["execution_context"],
        expected_sha256=context_sha,
        expected_byte_length=context_length,
        path="$.execution_context",
    )
    nonce, _ = _execution._validate_nonce_binding(
        obj["execution_context"]["attempt_binding"]["run_nonce"],
        "$.execution_context.attempt_binding.run_nonce",
    )
    result = DiagnosticWorkerAuthorizationV2Artifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        authorization_id=authorization_id,
        issued_at=issued_at,
        not_before=shared.plan.execution_window_start,
        expires_at=expires_at,
        study_id=binding.study_id,
        case_id=binding.case_id,
        case_execution_ordinal=binding.case_execution_ordinal,
        attempt_ordinal=1,
        run_nonce_b64url=nonce,
        execution_context_sha256=context_sha,
        execution_context_byte_length=context_length,
        payload=freeze_json(obj),
        artifact_refs=refs,
    )
    with seal.lock:
        prior = seal.authorization_cache.setdefault(cache_key, result)
    if prior != result or prior.raw_bytes != result.raw_bytes:
        raise DiagnosticLifecycleIntegrityError("authorization cache exact replay drifted")
    return prior


def _shared_build_authorization(
    shared: DiagnosticSharedPlanReplayContext,
    request: DiagnosticStudyRequestArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    *,
    issued_at: str,
    expires_at: str,
) -> DiagnosticWorkerAuthorizationV2Artifact:
    value, _id, _refs = _shared_authorization_value(
        shared, request, binding, issued_at=issued_at, expires_at=expires_at
    )
    return _shared_load_authorization(
        shared, request, binding, canonical_json_bytes(value)
    )


def _shared_terminal_value(
    shared: DiagnosticSharedPlanReplayContext,
    request: DiagnosticStudyRequestArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    authorization: DiagnosticWorkerAuthorizationV2Artifact | None,
    *,
    terminal_at: str,
    terminal_status: str,
    terminal_phase: str,
    invocation_certainty: str,
    worker_started_at: str | None,
    produced_artifacts: Mapping[str, tuple[ArtifactRef, bytes]] | None,
    error: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], tuple[ArtifactRef, ...], tuple[ArtifactRef, ...]]:
    binding = _shared_load_binding(shared, request, binding.raw_bytes)
    authorization = (
        None
        if authorization is None
        else _shared_load_authorization(
            shared, request, binding, authorization.raw_bytes
        )
    )
    terminal_at = expect_timestamp(terminal_at, "terminal_at")
    if worker_started_at is not None:
        worker_started_at = expect_timestamp(worker_started_at, "worker_started_at")
    if authorization is None:
        if produced_artifacts not in (None, {}):
            raise SchemaValidationError("preauthorization rejection cannot bind outputs")
        rows: tuple[tuple[str, ArtifactRef, bytes], ...] = ()
        dependencies: tuple[ArtifactRef, ...] = ()
        context = binding.payload["execution_context"]
        context_sha = binding.execution_context_sha256
        context_length = binding.execution_context_byte_length
    else:
        rows, dependencies = _execution._produced_artifacts(
            produced_artifacts, authorization=authorization
        )
        context = authorization.payload["execution_context"]
        context_sha = authorization.execution_context_sha256
        context_length = authorization.execution_context_byte_length
    roles = tuple(row[0] for row in rows)
    _execution._validate_terminal_branch(
        status=terminal_status,
        phase=terminal_phase,
        certainty=invocation_certainty,
        worker_started_at=worker_started_at,
        terminal_at=terminal_at,
        authorization=authorization,
        binding=binding,
        plan=shared.plan,
        produced_roles=roles,
    )
    validated_error = _execution._terminal_error(
        error,
        required=terminal_status != COMPLETED,
        status=terminal_status,
        phase=terminal_phase,
    )
    receipt_id = expect_machine_id(
        context["artifact_expectations"]["terminal_receipt"]["artifact_id"],
        "terminal_receipt.artifact_id",
    )
    missing = tuple(
        role for role in ("archive_admission", "child_output") if role not in roles
    )
    quarantined = () if terminal_status == COMPLETED else roles
    auth_disposition = (
        "NOT_CREATED_PREAUTHORIZATION_REJECTION"
        if authorization is None
        else (
            "CREATED_NOT_CONSUMED_TERMINAL"
            if terminal_status in {REJECTED, EXPIRED}
            else "CREATED_CONSUMED_TERMINAL"
        )
    )
    nonce_disposition = (
        "RESERVED_UNCONSUMED_TERMINALLY_RETIRED"
        if authorization is None
        else (
            "ISSUED_UNCONSUMED_TERMINALLY_RETIRED"
            if terminal_status in {REJECTED, EXPIRED}
            else "CONSUMED_SINGLE_ATTEMPT_TERMINAL"
        )
    )
    invocation_count: int | str = {
        "EXACTLY_ZERO": 0,
        "EXACTLY_ONE": 1,
        "INDETERMINATE_ZERO_OR_ONE": "INDETERMINATE_ZERO_OR_ONE",
    }[invocation_certainty]
    value = {
        "schema_version": _execution.DIAGNOSTIC_CHILD_TERMINAL_RECEIPT_V2_SCHEMA,
        "receipt_id": receipt_id,
        "terminal_at": terminal_at,
        "authorization": (
            None if authorization is None else _artifact_ref_value(authorization.artifact_ref)
        ),
        "child_execution_binding": _artifact_ref_value(binding.artifact_ref),
        "execution_context": thaw_json(context),
        "execution_context_sha256": context_sha,
        "execution_context_byte_length": context_length,
        "terminal": {
            "status": terminal_status,
            "lifecycle_terminal_state": terminal_status,
            "phase": terminal_phase,
            "invocation_certainty": invocation_certainty,
            "model_invocation_request_count": invocation_count,
            "authorization_disposition": auth_disposition,
            "nonce_disposition": nonce_disposition,
            "worker_started_at": worker_started_at,
            "produced_artifacts": [
                {"role": role, "artifact": _artifact_ref_value(reference)}
                for role, reference, _raw in rows
            ],
            "archive_manifest": (
                None if not dependencies else _artifact_ref_value(dependencies[0])
            ),
            "missing_artifact_roles": list(missing),
            "quarantined_artifact_roles": list(quarantined),
            "error": validated_error,
            "retry_count": 0,
            "retryable": False,
            "replacement": "FORBIDDEN",
            "row_disposition": (
                "DIAGNOSTIC_CHILD_COMPLETE_AGGREGATE_ONLY"
                if terminal_status == COMPLETED
                else "DIAGNOSTIC_CHILD_NEGATIVE_EVIDENCE_QUARANTINED_NO_REPLACEMENT"
            ),
            "packet_v2": "FORBIDDEN",
        },
        "boundary": dict(_execution._TERMINAL_BOUNDARY),
        "authority": dict(_execution._AUTHORITY),
        "governance": thaw_json(shared.chain.base.payload["governance"]),
    }
    row_seal = _shared_row_seal(shared, request.case_id)
    base_ids = {
        *row_seal.predecessor_ids,
        request.artifact_ref.artifact_id,
        binding.artifact_ref.artifact_id,
        *(() if authorization is None else (authorization.artifact_ref.artifact_id,)),
    }
    base_contents = {
        *row_seal.predecessor_content_identities,
        (request.artifact_ref.sha256, request.artifact_ref.byte_length),
        (binding.artifact_ref.sha256, binding.artifact_ref.byte_length),
        *(
            ()
            if authorization is None
            else ((authorization.artifact_ref.sha256, authorization.artifact_ref.byte_length),)
        ),
    }
    refs_list = [
        *((authorization.artifact_ref,) if authorization else ()),
        binding.artifact_ref,
        *binding.artifact_refs,
    ]
    for reference in (*(row[1] for row in rows), *dependencies):
        identity = (reference.sha256, reference.byte_length)
        if reference.artifact_id in base_ids or identity in base_contents:
            raise SchemaValidationError(
                "terminal observation collides with a sealed predecessor"
            )
        base_ids.add(reference.artifact_id)
        base_contents.add(identity)
        refs_list.append(reference)
    refs = tuple(refs_list)
    if receipt_id in base_ids:
        raise SchemaValidationError("terminal receipt_id collides with predecessor")
    return value, tuple(row[1] for row in rows), refs


def _shared_load_terminal(
    shared: DiagnosticSharedPlanReplayContext,
    request: DiagnosticStudyRequestArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    authorization: DiagnosticWorkerAuthorizationV2Artifact | None,
    raw: bytes,
    produced_artifact_bodies: Mapping[str, bytes] | None,
) -> DiagnosticChildTerminalReceiptV2Artifact:
    snapshot, obj = _execution._canonical_object(raw, "diagnostic child terminal receipt v2")
    terminal = expect_object(obj.get("terminal"), "$.terminal")
    status = expect_enum(
        terminal.get("status"), set(_execution.DIAGNOSTIC_TERMINAL_STATUSES), "$.terminal.status"
    )
    certainty = expect_enum(
        terminal.get("invocation_certainty"),
        set(_execution.DIAGNOSTIC_INVOCATION_CERTAINTIES),
        "$.terminal.invocation_certainty",
    )
    phase = expect_string(terminal.get("phase"), "$.terminal.phase", maximum=64)
    started = terminal.get("worker_started_at")
    if started is not None:
        started = expect_timestamp(started, "$.terminal.worker_started_at")
    body_map = {} if produced_artifact_bodies is None else dict(produced_artifact_bodies)
    produced: dict[str, tuple[ArtifactRef, bytes]] = {}
    for index, row in enumerate(
        _execution.expect_list(
            terminal.get("produced_artifacts"),
            "$.terminal.produced_artifacts",
            nonempty=False,
        )
    ):
        item = expect_object(row, f"$.terminal.produced_artifacts[{index}]")
        role = expect_enum(
            item.get("role"), {"archive_admission", "child_output"}, f"$.produced[{index}].role"
        )
        if role in produced or type(body_map.get(role)) is not bytes:
            raise SchemaValidationError("terminal produced body is missing or duplicated")
        produced[role] = (
            parse_artifact_ref(item.get("artifact"), f"$.produced[{index}].artifact"),
            body_map[role],
        )
    if set(body_map) != set(produced):
        raise SchemaValidationError("terminal produced body inventory differs from roles")
    value, produced_refs, refs = _shared_terminal_value(
        shared,
        request,
        binding,
        authorization,
        terminal_at=expect_timestamp(obj.get("terminal_at"), "$.terminal_at"),
        terminal_status=status,
        terminal_phase=phase,
        invocation_certainty=certainty,
        worker_started_at=started,
        produced_artifacts=produced,
        error=terminal.get("error"),
    )
    if obj != value:
        raise SchemaValidationError("terminal differs from shared-plan exact replay")
    context_sha = expect_sha256(obj.get("execution_context_sha256"), "$.execution_context_sha256")
    context_length = expect_int(
        obj.get("execution_context_byte_length"),
        "$.execution_context_byte_length",
        minimum=1,
    )
    return DiagnosticChildTerminalReceiptV2Artifact(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        byte_length=len(snapshot),
        receipt_id=expect_machine_id(obj.get("receipt_id"), "$.receipt_id"),
        terminal_status=status,
        invocation_certainty=certainty,
        terminal_at=value["terminal_at"],
        worker_started_at=started,
        execution_context_sha256=context_sha,
        execution_context_byte_length=context_length,
        produced_artifact_refs=produced_refs,
        payload=freeze_json(obj),
        artifact_refs=refs,
    )


def _shared_build_terminal(
    shared: DiagnosticSharedPlanReplayContext,
    request: DiagnosticStudyRequestArtifact,
    binding: DiagnosticChildExecutionBindingArtifact,
    authorization: DiagnosticWorkerAuthorizationV2Artifact | None,
    *,
    terminal_at: str,
    terminal_status: str,
    terminal_phase: str,
    invocation_certainty: str,
    worker_started_at: str | None,
    produced_artifacts: Mapping[str, tuple[ArtifactRef, bytes]] | None,
    error: Mapping[str, Any] | None,
) -> DiagnosticChildTerminalReceiptV2Artifact:
    value, _produced, _refs = _shared_terminal_value(
        shared,
        request,
        binding,
        authorization,
        terminal_at=terminal_at,
        terminal_status=terminal_status,
        terminal_phase=terminal_phase,
        invocation_certainty=invocation_certainty,
        worker_started_at=worker_started_at,
        produced_artifacts=produced_artifacts,
        error=error,
    )
    bodies = {
        role: pair[1]
        for role, pair in ({} if produced_artifacts is None else produced_artifacts).items()
    }
    return _shared_load_terminal(
        shared,
        request,
        binding,
        authorization,
        canonical_json_bytes(value),
        bodies,
    )


def derive_diagnostic_attempt_subject_sha256(
    *,
    plan: DiagnosticStudyPlanArtifact,
    study_request: DiagnosticStudyRequestArtifact,
) -> str:
    """Derive the exact lifecycle subject used by the execution-v2 binding."""

    if type(plan) is not DiagnosticStudyPlanArtifact:
        raise DiagnosticLifecycleValidationError(
            "plan must be an exact DiagnosticStudyPlanArtifact"
        )
    if type(study_request) is not DiagnosticStudyRequestArtifact:
        raise DiagnosticLifecycleValidationError(
            "study_request must be an exact DiagnosticStudyRequestArtifact"
        )
    if study_request.study_id != plan.study_id:
        raise DiagnosticLifecycleValidationError("Study request belongs to another plan")
    return canonical_sha256(
        {
            "domain": DIAGNOSTIC_ATTEMPT_SUBJECT_DOMAIN,
            "pre_outcome_chain_sha256": plan.pre_outcome_chain_sha256,
            "study_plan": _artifact_ref_value(plan.artifact_ref),
            "study_request": _artifact_ref_value(study_request.artifact_ref),
            "case_execution_ordinal": study_request.execution_ordinal,
        }
    )


def _backend_profile(name: str) -> Mapping[str, Any]:
    if name == "memory":
        value = {
            "profile": "LOCKED_IN_MEMORY_PROCESS_LOCAL_NON_DURABLE",
            "atomic_scope": "ONE_PYTHON_PROCESS_AND_STORE_INSTANCE",
            "close_reopen_persistence": "NOT_AVAILABLE",
            "same_host_file_arbitration": "NOT_AVAILABLE",
            "multi_host": "NOT_AVAILABLE",
            "host_loss_survival": "NOT_AVAILABLE",
            "worm": "NOT_AVAILABLE",
        }
    else:
        value = {
            "profile": "SQLITE_SINGLE_HOST_DURABLE_NOT_REPLICATED",
            "atomic_scope": "ONE_SQLITE_DATABASE_FILE_ON_ONE_HOST",
            "close_reopen_persistence": "AVAILABLE",
            "same_host_file_arbitration": "AVAILABLE",
            "multi_host": "NOT_AVAILABLE",
            "host_loss_survival": "NOT_AVAILABLE",
            "worm": "NOT_AVAILABLE",
        }
    return _frozen_mapping(value)


def _attempt_value(attempt: _StoredAttempt) -> dict[str, Any]:
    return {
        "schema_version": DIAGNOSTIC_ATTEMPT_LIFECYCLE_SCHEMA,
        "tenant_id": attempt.tenant_id,
        "attempt_subject_sha256": attempt.attempt_subject_sha256,
        "attempt_ordinal": attempt.attempt_ordinal,
        "study_id": attempt.study_id,
        "case_id": attempt.case_id,
        "case_execution_ordinal": attempt.case_execution_ordinal,
        "issuance_mode": attempt.issuance_mode,
        "issuance_request_sha256": attempt.issuance_request_sha256,
        "state": attempt.state,
        "version": attempt.version,
        "run_nonce_sha256": attempt.run_nonce_sha256,
        "binding_raw_b64": _b64(attempt.binding_raw),
        "authorization_raw_b64": (
            None if attempt.authorization_raw is None else _b64(attempt.authorization_raw)
        ),
        "terminal_raw_b64": (
            None if attempt.terminal_raw is None else _b64(attempt.terminal_raw)
        ),
        "produced_artifact_bodies_b64": {
            role: _b64(raw) for role, raw in attempt.produced_artifact_bodies
        },
        "worker_started_at": attempt.worker_started_at,
        "created_at": attempt.created_at,
        "updated_at": attempt.updated_at,
        "event_count": attempt.event_count,
        "head_event_sha256": attempt.head_event_sha256,
        "time_assurance": _TIME_ASSURANCE,
        "authority": dict(_AUTHORITY),
    }


def _attempt_raw(attempt: _StoredAttempt) -> bytes:
    return canonical_json_bytes(_attempt_value(attempt))


def _load_attempt_raw(raw: bytes) -> _StoredAttempt:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise DiagnosticLifecyclePersistenceError(
                "stored attempt must use exact canonical JSON bytes"
            )
        expect_keys(
            value,
            required={
                "schema_version",
                "tenant_id",
                "attempt_subject_sha256",
                "attempt_ordinal",
                "study_id",
                "case_id",
                "case_execution_ordinal",
                "issuance_mode",
                "issuance_request_sha256",
                "state",
                "version",
                "run_nonce_sha256",
                "binding_raw_b64",
                "authorization_raw_b64",
                "terminal_raw_b64",
                "produced_artifact_bodies_b64",
                "worker_started_at",
                "created_at",
                "updated_at",
                "event_count",
                "head_event_sha256",
                "time_assurance",
                "authority",
            },
            path="$attempt",
        )
        if value["schema_version"] != DIAGNOSTIC_ATTEMPT_LIFECYCLE_SCHEMA:
            raise DiagnosticLifecyclePersistenceError("stored attempt schema drifted")
        if value["time_assurance"] != _TIME_ASSURANCE or value["authority"] != _AUTHORITY:
            raise DiagnosticLifecyclePersistenceError("stored attempt authority drifted")
        tenant_id = expect_string(value["tenant_id"], "$attempt.tenant_id", maximum=256)
        subject = expect_sha256(
            value["attempt_subject_sha256"], "$attempt.attempt_subject_sha256"
        )
        attempt_ordinal = expect_int(
            value["attempt_ordinal"], "$attempt.attempt_ordinal", minimum=1, maximum=1
        )
        study_id = expect_machine_id(value["study_id"], "$attempt.study_id")
        case_id = expect_machine_id(value["case_id"], "$attempt.case_id")
        ordinal = expect_int(
            value["case_execution_ordinal"],
            "$attempt.case_execution_ordinal",
            minimum=1,
        )
        mode = expect_enum(
            value["issuance_mode"],
            {"AUTHORIZED", "PREAUTHORIZATION_REJECTED"},
            "$attempt.issuance_mode",
        )
        request_sha = expect_sha256(
            value["issuance_request_sha256"], "$attempt.issuance_request_sha256"
        )
        state = expect_enum(value["state"], set(DIAGNOSTIC_ATTEMPT_STATES), "$attempt.state")
        version = expect_int(value["version"], "$attempt.version", minimum=1)
        nonce_sha = expect_sha256(
            value["run_nonce_sha256"], "$attempt.run_nonce_sha256"
        )
        binding_raw = _unb64(value["binding_raw_b64"], "$attempt.binding_raw_b64")
        auth_value = value["authorization_raw_b64"]
        auth_raw = (
            None
            if auth_value is None
            else _unb64(auth_value, "$attempt.authorization_raw_b64")
        )
        terminal_value = value["terminal_raw_b64"]
        terminal_raw = (
            None
            if terminal_value is None
            else _unb64(terminal_value, "$attempt.terminal_raw_b64")
        )
        bodies = expect_object(
            value["produced_artifact_bodies_b64"],
            "$attempt.produced_artifact_bodies_b64",
        )
        if set(bodies) - {"archive_admission", "child_output"}:
            raise DiagnosticLifecyclePersistenceError("stored produced body role drifted")
        produced_bodies = tuple(
            (role, _unb64(bodies[role], f"$attempt.produced_artifact_bodies_b64.{role}"))
            for role in ("archive_admission", "child_output")
            if role in bodies
        )
        worker_started_at = value["worker_started_at"]
        if worker_started_at is not None:
            worker_started_at = expect_timestamp(
                worker_started_at, "$attempt.worker_started_at"
            )
        created_at = expect_timestamp(value["created_at"], "$attempt.created_at")
        updated_at = expect_timestamp(value["updated_at"], "$attempt.updated_at")
        event_count = expect_int(value["event_count"], "$attempt.event_count", minimum=1)
        head = expect_sha256(
            value["head_event_sha256"], "$attempt.head_event_sha256"
        )
    except DiagnosticLifecycleError:
        raise
    except (SchemaValidationError, ValueError, KeyError, TypeError) as exc:
        raise DiagnosticLifecyclePersistenceError(
            f"stored attempt payload is invalid: {exc}"
        ) from exc
    return _StoredAttempt(
        tenant_id=tenant_id,
        attempt_subject_sha256=subject,
        attempt_ordinal=attempt_ordinal,
        study_id=study_id,
        case_id=case_id,
        case_execution_ordinal=ordinal,
        issuance_mode=mode,
        issuance_request_sha256=request_sha,
        state=state,
        version=version,
        run_nonce_sha256=nonce_sha,
        binding_raw=binding_raw,
        authorization_raw=auth_raw,
        terminal_raw=terminal_raw,
        produced_artifact_bodies=produced_bodies,
        worker_started_at=worker_started_at,
        created_at=created_at,
        updated_at=updated_at,
        event_count=event_count,
        head_event_sha256=head,
    )


def _build_event(
    *,
    tenant_id: str,
    attempt_subject_sha256: str,
    sequence: int,
    previous_event_sha256: str,
    event_type: str,
    state_before: str | None,
    state_after: str,
    occurred_at: str,
    operation_id: str,
    operation_request_sha256: str,
    details: Mapping[str, Any],
) -> DiagnosticAttemptEventReceipt:
    value = {
        "schema_version": DIAGNOSTIC_ATTEMPT_EVENT_SCHEMA,
        "tenant_id": tenant_id,
        "attempt_subject_sha256": attempt_subject_sha256,
        "attempt_ordinal": 1,
        "sequence": sequence,
        "previous_event_sha256": previous_event_sha256,
        "event_type": event_type,
        "state_before": state_before,
        "state_after": state_after,
        "occurred_at": occurred_at,
        "operation_id": operation_id,
        "operation_request_sha256": operation_request_sha256,
        "details": thaw_json(details),
        "time_assurance": _TIME_ASSURANCE,
        "authority": dict(_AUTHORITY),
    }
    return _load_event_raw(canonical_json_bytes(value))


def _load_event_raw(raw: bytes) -> DiagnosticAttemptEventReceipt:
    try:
        snapshot, value = load_json_object(raw)
        if snapshot != canonical_json_bytes(value):
            raise DiagnosticLifecyclePersistenceError(
                "stored event must use exact canonical JSON bytes"
            )
        expect_keys(
            value,
            required={
                "schema_version",
                "tenant_id",
                "attempt_subject_sha256",
                "attempt_ordinal",
                "sequence",
                "previous_event_sha256",
                "event_type",
                "state_before",
                "state_after",
                "occurred_at",
                "operation_id",
                "operation_request_sha256",
                "details",
                "time_assurance",
                "authority",
            },
            path="$event",
        )
        if value["schema_version"] != DIAGNOSTIC_ATTEMPT_EVENT_SCHEMA:
            raise DiagnosticLifecyclePersistenceError("stored event schema drifted")
        if value["time_assurance"] != _TIME_ASSURANCE or value["authority"] != _AUTHORITY:
            raise DiagnosticLifecyclePersistenceError("stored event authority drifted")
        expect_string(value["tenant_id"], "$event.tenant_id", maximum=256)
        expect_sha256(
            value["attempt_subject_sha256"], "$event.attempt_subject_sha256"
        )
        expect_int(value["attempt_ordinal"], "$event.attempt_ordinal", minimum=1, maximum=1)
        sequence = expect_int(value["sequence"], "$event.sequence", minimum=1)
        expect_sha256(
            value["previous_event_sha256"], "$event.previous_event_sha256"
        )
        event_type = expect_enum(
            value["event_type"], set(DIAGNOSTIC_ATTEMPT_STATES), "$event.event_type"
        )
        before = value["state_before"]
        if before is not None:
            before = expect_enum(before, set(DIAGNOSTIC_ATTEMPT_STATES), "$event.state_before")
        after = expect_enum(
            value["state_after"], set(DIAGNOSTIC_ATTEMPT_STATES), "$event.state_after"
        )
        occurred_at = expect_timestamp(value["occurred_at"], "$event.occurred_at")
        operation_id = expect_machine_id(value["operation_id"], "$event.operation_id")
        request_sha = expect_sha256(
            value["operation_request_sha256"], "$event.operation_request_sha256"
        )
        expect_object(value["details"], "$event.details")
    except DiagnosticLifecycleError:
        raise
    except (SchemaValidationError, ValueError, KeyError, TypeError) as exc:
        raise DiagnosticLifecyclePersistenceError(
            f"stored event payload is invalid: {exc}"
        ) from exc
    return DiagnosticAttemptEventReceipt(
        raw_bytes=snapshot,
        sha256=sha256_bytes(snapshot),
        sequence=sequence,
        event_type=event_type,
        state_before=before,
        state_after=after,
        occurred_at=occurred_at,
        operation_id=operation_id,
        operation_request_sha256=request_sha,
        payload=freeze_json(value),
    )


def _validate_initial_pair(
    attempt: _StoredAttempt,
    event: DiagnosticAttemptEventReceipt,
) -> None:
    if attempt.version != 1 or attempt.event_count != 1:
        raise DiagnosticLifecyclePersistenceError("initial attempt version/count must equal one")
    if event.sequence != 1 or event.payload["previous_event_sha256"] != _GENESIS_SHA256:
        raise DiagnosticLifecyclePersistenceError("initial event does not follow genesis")
    if event.state_before is not None or event.state_after != attempt.state:
        raise DiagnosticLifecyclePersistenceError("initial event state differs from attempt")
    if event.event_type != attempt.state:
        raise DiagnosticLifecyclePersistenceError("initial event type differs from attempt state")
    if event.operation_request_sha256 != attempt.issuance_request_sha256:
        raise DiagnosticLifecyclePersistenceError(
            "initial event request digest differs from issuance request"
        )
    if attempt.state not in {AUTHORIZED, REJECTED}:
        raise DiagnosticLifecyclePersistenceError("attempt can initialize only AUTHORIZED or REJECTED")
    if attempt.state == AUTHORIZED:
        if attempt.issuance_mode != "AUTHORIZED" or attempt.authorization_raw is None:
            raise DiagnosticLifecyclePersistenceError("AUTHORIZED initialization lacks authorization")
    else:
        if attempt.issuance_mode != "PREAUTHORIZATION_REJECTED" or attempt.authorization_raw is not None:
            raise DiagnosticLifecyclePersistenceError("preauthorization rejection fabricated authorization")
    if attempt.terminal_raw is None and attempt.state in DIAGNOSTIC_TERMINAL_STATES:
        raise DiagnosticLifecyclePersistenceError("terminal initialization lacks terminal bytes")
    if attempt.terminal_raw is not None and attempt.state not in DIAGNOSTIC_TERMINAL_STATES:
        raise DiagnosticLifecyclePersistenceError("nonterminal initialization carries terminal bytes")
    if attempt.head_event_sha256 != event.sha256:
        raise DiagnosticLifecyclePersistenceError("initial head does not bind event")
    if attempt.created_at != event.occurred_at or attempt.updated_at != event.occurred_at:
        raise DiagnosticLifecyclePersistenceError("initial event time differs from attempt")
    if event.payload["tenant_id"] != attempt.tenant_id or event.payload[
        "attempt_subject_sha256"
    ] != attempt.attempt_subject_sha256:
        raise DiagnosticLifecyclePersistenceError("initial event scope differs from attempt")


def _validate_transition_pair(
    previous: _StoredAttempt,
    updated: _StoredAttempt,
    event: DiagnosticAttemptEventReceipt,
    *,
    expected_version: int,
) -> None:
    if previous.version != expected_version:
        raise DiagnosticLifecycleVersionConflict(
            f"expected version {expected_version}, store holds {previous.version}"
        )
    if updated.version != previous.version + 1:
        raise DiagnosticLifecyclePersistenceError("CAS update must increment version once")
    immutable_fields = (
        "tenant_id",
        "attempt_subject_sha256",
        "attempt_ordinal",
        "study_id",
        "case_id",
        "case_execution_ordinal",
        "issuance_mode",
        "issuance_request_sha256",
        "run_nonce_sha256",
        "binding_raw",
        "authorization_raw",
        "created_at",
    )
    for field in immutable_fields:
        if getattr(previous, field) != getattr(updated, field):
            raise DiagnosticLifecyclePersistenceError(f"CAS rewrote immutable {field}")
    if updated.state not in _ALLOWED_TRANSITIONS.get(previous.state, frozenset()):
        raise DiagnosticLifecycleConflict(
            f"invalid diagnostic transition {previous.state}->{updated.state}"
        )
    if event.sequence != previous.event_count + 1:
        raise DiagnosticLifecyclePersistenceError("CAS event sequence is not contiguous")
    if event.payload["previous_event_sha256"] != previous.head_event_sha256:
        raise DiagnosticLifecyclePersistenceError("CAS event predecessor differs from head")
    if event.state_before != previous.state or event.state_after != updated.state:
        raise DiagnosticLifecyclePersistenceError("CAS event states differ from update")
    if event.event_type != updated.state:
        raise DiagnosticLifecyclePersistenceError("CAS event type differs from new state")
    if updated.event_count != event.sequence or updated.head_event_sha256 != event.sha256:
        raise DiagnosticLifecyclePersistenceError("CAS update head/count differs from event")
    if updated.updated_at != event.occurred_at:
        raise DiagnosticLifecyclePersistenceError("CAS update time differs from event")
    if _time(event.occurred_at) < _time(previous.updated_at):
        raise DiagnosticLifecycleConflict("lifecycle event time regressed")
    if event.payload["tenant_id"] != previous.tenant_id or event.payload[
        "attempt_subject_sha256"
    ] != previous.attempt_subject_sha256:
        raise DiagnosticLifecyclePersistenceError("CAS event scope differs from attempt")
    if updated.state in DIAGNOSTIC_TERMINAL_STATES and updated.terminal_raw is None:
        raise DiagnosticLifecyclePersistenceError("terminal transition lacks terminal bytes")
    if updated.state == RUNNING and updated.worker_started_at is None:
        raise DiagnosticLifecyclePersistenceError("RUNNING transition lacks worker start")


class InMemoryDiagnosticLifecycleStore:
    """Locked process-local reference backend; intentionally non-durable."""

    def __init__(self, *, fault_hook: Callable[[str], None] | None = None) -> None:
        if fault_hook is not None and not callable(fault_hook):
            raise DiagnosticLifecycleValidationError("fault_hook must be callable")
        self._lock = threading.RLock()
        self._attempts: dict[tuple[str, str], _StoredAttempt] = {}
        self._events: dict[
            tuple[str, str], tuple[DiagnosticAttemptEventReceipt, ...]
        ] = {}
        self._nonce_index: dict[tuple[str, str], str] = {}
        self._closed = False
        self._fault_hook = fault_hook
        self._profile = _backend_profile("memory")

    @property
    def durability_profile(self) -> Mapping[str, Any]:
        return self._profile

    def _ensure_open(self) -> None:
        if self._closed:
            raise DiagnosticLifecyclePersistenceError("in-memory lifecycle store is closed")

    def _fault(self, stage: str) -> None:
        if self._fault_hook is None:
            return
        try:
            self._fault_hook(stage)
        except Exception as exc:
            raise DiagnosticLifecyclePersistenceError(
                f"injected lifecycle persistence failure at {stage}"
            ) from exc

    def create_attempt(
        self,
        attempt: _StoredAttempt,
        event: DiagnosticAttemptEventReceipt,
    ) -> _StoredAttempt:
        self._ensure_open()
        _validate_initial_pair(attempt, event)
        if _load_event_raw(event.raw_bytes) != event:
            raise DiagnosticLifecyclePersistenceError(
                "lifecycle create event projection differs from exact bytes"
            )
        key = (attempt.tenant_id, attempt.attempt_subject_sha256)
        nonce_key = (attempt.tenant_id, attempt.run_nonce_sha256)
        with self._lock:
            if key in self._attempts:
                raise DiagnosticLifecycleConflict("attempt subject is already reserved")
            if nonce_key in self._nonce_index:
                raise DiagnosticLifecycleConflict("attempt nonce is already reserved")
            self._fault("memory.create.before")
            self._attempts[key] = attempt
            self._nonce_index[nonce_key] = attempt.attempt_subject_sha256
            try:
                self._fault("memory.create.after_attempt")
                self._events[key] = (event,)
                self._fault("memory.create.after_event")
            except Exception:
                self._events.pop(key, None)
                self._attempts.pop(key, None)
                self._nonce_index.pop(nonce_key, None)
                raise
            return attempt

    def compare_and_swap(
        self,
        attempt: _StoredAttempt,
        event: DiagnosticAttemptEventReceipt,
        *,
        expected_version: int,
    ) -> _StoredAttempt:
        self._ensure_open()
        key = (attempt.tenant_id, attempt.attempt_subject_sha256)
        with self._lock:
            previous = self._attempts.get(key)
            if previous is None:
                raise DiagnosticLifecycleNotFound("attempt not found")
            _validate_transition_pair(
                previous, attempt, event, expected_version=expected_version
            )
            events = self._events.get(key, ())
            if any(item.operation_id == event.operation_id for item in events):
                raise DiagnosticLifecycleConflict("operation_id is already create-only")
            self._fault("memory.cas.before")
            self._attempts[key] = attempt
            try:
                self._fault("memory.cas.after_attempt")
                self._events[key] = (*events, event)
                self._fault("memory.cas.after_event")
            except Exception:
                self._attempts[key] = previous
                self._events[key] = events
                raise
            return attempt

    def get_attempt(
        self, tenant_id: str, attempt_subject_sha256: str
    ) -> _StoredAttempt | None:
        self._ensure_open()
        with self._lock:
            return self._attempts.get((tenant_id, attempt_subject_sha256))

    def list_attempts(self, tenant_id: str) -> tuple[_StoredAttempt, ...]:
        self._ensure_open()
        with self._lock:
            rows = [
                row
                for (scope, _subject), row in self._attempts.items()
                if scope == tenant_id
            ]
        rows.sort(key=lambda row: (row.case_execution_ordinal, row.attempt_subject_sha256))
        return tuple(rows)

    def list_events(
        self, tenant_id: str, attempt_subject_sha256: str
    ) -> tuple[DiagnosticAttemptEventReceipt, ...]:
        self._ensure_open()
        with self._lock:
            return self._events.get((tenant_id, attempt_subject_sha256), ())

    def close(self) -> None:
        with self._lock:
            self._closed = True


_CREATE_ATTEMPTS_TABLE = """
CREATE TABLE IF NOT EXISTS diagnostic_attempts (
    tenant_id TEXT NOT NULL,
    attempt_subject_sha256 TEXT NOT NULL,
    state TEXT NOT NULL,
    version INTEGER NOT NULL,
    run_nonce_sha256 TEXT NOT NULL,
    authorization_sha256 TEXT,
    terminal_sha256 TEXT,
    head_event_sha256 TEXT NOT NULL,
    payload BLOB NOT NULL,
    PRIMARY KEY (tenant_id, attempt_subject_sha256),
    UNIQUE (tenant_id, run_nonce_sha256)
)
"""

_CREATE_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS diagnostic_attempt_events (
    tenant_id TEXT NOT NULL,
    attempt_subject_sha256 TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    operation_id TEXT NOT NULL,
    event_sha256 TEXT NOT NULL,
    payload BLOB NOT NULL,
    PRIMARY KEY (tenant_id, attempt_subject_sha256, sequence),
    UNIQUE (tenant_id, attempt_subject_sha256, operation_id),
    UNIQUE (tenant_id, event_sha256),
    FOREIGN KEY (tenant_id, attempt_subject_sha256)
        REFERENCES diagnostic_attempts (tenant_id, attempt_subject_sha256)
)
"""


def _optional_raw_sha256(raw: bytes | None) -> str | None:
    return None if raw is None else sha256_bytes(raw)


def _attempt_sql_values(attempt: _StoredAttempt) -> tuple[Any, ...]:
    return (
        attempt.tenant_id,
        attempt.attempt_subject_sha256,
        attempt.state,
        attempt.version,
        attempt.run_nonce_sha256,
        _optional_raw_sha256(attempt.authorization_raw),
        _optional_raw_sha256(attempt.terminal_raw),
        attempt.head_event_sha256,
        _attempt_raw(attempt),
    )


def _load_attempt_sql_row(
    row: Sequence[Any],
    *,
    requested_tenant_id: str,
    requested_subject_sha256: str | None,
) -> _StoredAttempt:
    if len(row) != 9:
        raise DiagnosticLifecyclePersistenceError("SQLite attempt projection width drifted")
    (
        sql_tenant,
        sql_subject,
        sql_state,
        sql_version,
        sql_nonce,
        sql_authorization_sha,
        sql_terminal_sha,
        sql_head,
        payload,
    ) = row
    if type(payload) not in (bytes, bytearray, memoryview):
        raise DiagnosticLifecyclePersistenceError("SQLite attempt payload is not bytes")
    attempt = _load_attempt_raw(bytes(payload))
    expected = (
        attempt.tenant_id,
        attempt.attempt_subject_sha256,
        attempt.state,
        attempt.version,
        attempt.run_nonce_sha256,
        _optional_raw_sha256(attempt.authorization_raw),
        _optional_raw_sha256(attempt.terminal_raw),
        attempt.head_event_sha256,
    )
    observed = (
        sql_tenant,
        sql_subject,
        sql_state,
        sql_version,
        sql_nonce,
        sql_authorization_sha,
        sql_terminal_sha,
        sql_head,
    )
    if observed != expected:
        raise DiagnosticLifecyclePersistenceError(
            "SQLite redundant attempt columns differ from strict payload"
        )
    if sql_tenant != requested_tenant_id or (
        requested_subject_sha256 is not None
        and sql_subject != requested_subject_sha256
    ):
        raise DiagnosticLifecyclePersistenceError(
            "SQLite attempt row differs from requested tenant/subject scope"
        )
    return attempt


def _load_event_sql_row(
    row: Sequence[Any],
    *,
    requested_tenant_id: str,
    requested_subject_sha256: str,
) -> DiagnosticAttemptEventReceipt:
    if len(row) != 6:
        raise DiagnosticLifecyclePersistenceError("SQLite event projection width drifted")
    sql_tenant, sql_subject, sql_sequence, sql_operation, sql_sha, payload = row
    if type(payload) not in (bytes, bytearray, memoryview):
        raise DiagnosticLifecyclePersistenceError("SQLite event payload is not bytes")
    event = _load_event_raw(bytes(payload))
    if (
        sql_tenant != requested_tenant_id
        or sql_subject != requested_subject_sha256
        or sql_tenant != event.payload["tenant_id"]
        or sql_subject != event.payload["attempt_subject_sha256"]
        or sql_sequence != event.sequence
        or sql_operation != event.operation_id
        or sql_sha != event.sha256
    ):
        raise DiagnosticLifecyclePersistenceError(
            "SQLite redundant event columns differ from payload/request scope"
        )
    return event


class SqliteDiagnosticLifecycleStore:
    """One-file, same-host SQLite backend with atomic create/CAS transactions."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        fault_hook: Callable[[str], None] | None = None,
    ) -> None:
        if fault_hook is not None and not callable(fault_hook):
            raise DiagnosticLifecycleValidationError("fault_hook must be callable")
        self._path = os.fspath(path)
        if not self._path:
            raise DiagnosticLifecycleValidationError("SQLite path must not be empty")
        lowered_path = self._path.lower()
        if self._path == ":memory:" or (
            lowered_path.startswith("file:")
            and "mode=memory" in lowered_path.partition("?")[2].split("&")
        ):
            raise DiagnosticLifecycleValidationError(
                "SQLite memory mode cannot satisfy the advertised durable-file profile"
            )
        self._lock = threading.RLock()
        self._closed = False
        self._fault_hook = fault_hook
        self._profile = _backend_profile("sqlite")
        try:
            self._conn = sqlite3.connect(
                self._path,
                check_same_thread=False,
                isolation_level=None,
                timeout=30.0,
            )
            with self._lock:
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA synchronous=FULL")
                self._conn.execute("PRAGMA foreign_keys=ON")
                self._conn.execute("PRAGMA busy_timeout=30000")
                self._conn.execute(_CREATE_ATTEMPTS_TABLE)
                self._conn.execute(_CREATE_EVENTS_TABLE)
        except sqlite3.Error as exc:
            raise DiagnosticLifecyclePersistenceError(
                f"could not initialize SQLite lifecycle store: {exc}"
            ) from exc

    @property
    def durability_profile(self) -> Mapping[str, Any]:
        return self._profile

    def _ensure_open(self) -> None:
        if self._closed:
            raise DiagnosticLifecyclePersistenceError("SQLite lifecycle store is closed")

    def _fault(self, stage: str) -> None:
        if self._fault_hook is None:
            return
        try:
            self._fault_hook(stage)
        except Exception as exc:
            raise DiagnosticLifecyclePersistenceError(
                f"injected lifecycle persistence failure at {stage}"
            ) from exc

    @contextmanager
    def _write_transaction(self):
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except Exception:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    def _read_attempt(
        self, tenant_id: str, attempt_subject_sha256: str
    ) -> _StoredAttempt | None:
        row = self._conn.execute(
            "SELECT tenant_id, attempt_subject_sha256, state, version, "
            "run_nonce_sha256, authorization_sha256, terminal_sha256, "
            "head_event_sha256, payload FROM diagnostic_attempts "
            "WHERE tenant_id = ? AND attempt_subject_sha256 = ?",
            (tenant_id, attempt_subject_sha256),
        ).fetchone()
        if row is None:
            return None
        return _load_attempt_sql_row(
            row,
            requested_tenant_id=tenant_id,
            requested_subject_sha256=attempt_subject_sha256,
        )

    def create_attempt(
        self,
        attempt: _StoredAttempt,
        event: DiagnosticAttemptEventReceipt,
    ) -> _StoredAttempt:
        self._ensure_open()
        _validate_initial_pair(attempt, event)
        if _load_event_raw(event.raw_bytes) != event:
            raise DiagnosticLifecyclePersistenceError(
                "SQLite create event projection differs from exact bytes"
            )
        try:
            with self._lock, self._write_transaction():
                self._fault("sqlite.create.before")
                self._conn.execute(
                    "INSERT INTO diagnostic_attempts "
                    "(tenant_id, attempt_subject_sha256, state, version, "
                    "run_nonce_sha256, authorization_sha256, terminal_sha256, "
                    "head_event_sha256, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    _attempt_sql_values(attempt),
                )
                self._fault("sqlite.create.after_attempt")
                self._conn.execute(
                    "INSERT INTO diagnostic_attempt_events "
                    "(tenant_id, attempt_subject_sha256, sequence, operation_id, event_sha256, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        attempt.tenant_id,
                        attempt.attempt_subject_sha256,
                        event.sequence,
                        event.operation_id,
                        event.sha256,
                        event.raw_bytes,
                    ),
                )
                self._fault("sqlite.create.after_event")
        except sqlite3.IntegrityError as exc:
            raise DiagnosticLifecycleConflict(
                "attempt subject, nonce, operation, or event is already create-only"
            ) from exc
        except sqlite3.Error as exc:
            raise DiagnosticLifecyclePersistenceError(
                f"SQLite create failed: {exc}"
            ) from exc
        return attempt

    def compare_and_swap(
        self,
        attempt: _StoredAttempt,
        event: DiagnosticAttemptEventReceipt,
        *,
        expected_version: int,
    ) -> _StoredAttempt:
        self._ensure_open()
        if _load_event_raw(event.raw_bytes) != event:
            raise DiagnosticLifecyclePersistenceError(
                "SQLite CAS event projection differs from exact bytes"
            )
        try:
            with self._lock, self._write_transaction():
                previous = self._read_attempt(
                    attempt.tenant_id, attempt.attempt_subject_sha256
                )
                if previous is None:
                    raise DiagnosticLifecycleNotFound("attempt not found")
                _validate_transition_pair(
                    previous, attempt, event, expected_version=expected_version
                )
                self._fault("sqlite.cas.before")
                self._conn.execute(
                    "INSERT INTO diagnostic_attempt_events "
                    "(tenant_id, attempt_subject_sha256, sequence, operation_id, event_sha256, payload) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        attempt.tenant_id,
                        attempt.attempt_subject_sha256,
                        event.sequence,
                        event.operation_id,
                        event.sha256,
                        event.raw_bytes,
                    ),
                )
                self._fault("sqlite.cas.after_event")
                cursor = self._conn.execute(
                    "UPDATE diagnostic_attempts SET state = ?, version = ?, "
                    "run_nonce_sha256 = ?, authorization_sha256 = ?, "
                    "terminal_sha256 = ?, head_event_sha256 = ?, payload = ? "
                    "WHERE tenant_id = ? AND attempt_subject_sha256 = ? AND version = ?",
                    (
                        attempt.state,
                        attempt.version,
                        attempt.run_nonce_sha256,
                        _optional_raw_sha256(attempt.authorization_raw),
                        _optional_raw_sha256(attempt.terminal_raw),
                        attempt.head_event_sha256,
                        _attempt_raw(attempt),
                        attempt.tenant_id,
                        attempt.attempt_subject_sha256,
                        expected_version,
                    ),
                )
                if cursor.rowcount != 1:
                    actual = self._read_attempt(
                        attempt.tenant_id, attempt.attempt_subject_sha256
                    )
                    raise DiagnosticLifecycleVersionConflict(
                        f"expected version {expected_version}, store holds "
                        f"{None if actual is None else actual.version}"
                    )
                self._fault("sqlite.cas.after_attempt")
        except sqlite3.IntegrityError as exc:
            raise DiagnosticLifecycleConflict(
                "operation or event is already create-only"
            ) from exc
        except sqlite3.Error as exc:
            raise DiagnosticLifecyclePersistenceError(
                f"SQLite compare-and-swap failed: {exc}"
            ) from exc
        return attempt

    def get_attempt(
        self, tenant_id: str, attempt_subject_sha256: str
    ) -> _StoredAttempt | None:
        self._ensure_open()
        try:
            with self._lock:
                return self._read_attempt(tenant_id, attempt_subject_sha256)
        except sqlite3.Error as exc:
            raise DiagnosticLifecyclePersistenceError(
                f"SQLite read failed: {exc}"
            ) from exc

    def list_attempts(self, tenant_id: str) -> tuple[_StoredAttempt, ...]:
        self._ensure_open()
        try:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT tenant_id, attempt_subject_sha256, state, version, "
                    "run_nonce_sha256, authorization_sha256, terminal_sha256, "
                    "head_event_sha256, payload FROM diagnostic_attempts "
                    "WHERE tenant_id = ?",
                    (tenant_id,),
                ).fetchall()
            attempts = [
                _load_attempt_sql_row(
                    row,
                    requested_tenant_id=tenant_id,
                    requested_subject_sha256=None,
                )
                for row in rows
            ]
        except sqlite3.Error as exc:
            raise DiagnosticLifecyclePersistenceError(
                f"SQLite list failed: {exc}"
            ) from exc
        attempts.sort(
            key=lambda row: (row.case_execution_ordinal, row.attempt_subject_sha256)
        )
        return tuple(attempts)

    def list_events(
        self, tenant_id: str, attempt_subject_sha256: str
    ) -> tuple[DiagnosticAttemptEventReceipt, ...]:
        self._ensure_open()
        try:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT tenant_id, attempt_subject_sha256, sequence, "
                    "operation_id, event_sha256, payload "
                    "FROM diagnostic_attempt_events "
                    "WHERE tenant_id = ? AND attempt_subject_sha256 = ? "
                    "ORDER BY sequence ASC",
                    (tenant_id, attempt_subject_sha256),
                ).fetchall()
            return tuple(
                _load_event_sql_row(
                    row,
                    requested_tenant_id=tenant_id,
                    requested_subject_sha256=attempt_subject_sha256,
                )
                for row in rows
            )
        except sqlite3.Error as exc:
            raise DiagnosticLifecyclePersistenceError(
                f"SQLite event read failed: {exc}"
            ) from exc

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._conn.close()
                self._closed = True

    def __enter__(self) -> "SqliteDiagnosticLifecycleStore":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


def _event_details(event: DiagnosticAttemptEventReceipt) -> Mapping[str, Any]:
    value = event.payload["details"]
    if not isinstance(value, Mapping):
        raise DiagnosticLifecycleIntegrityError("event details are not an exact mapping")
    return value


def _verify_event_chain(
    attempt: _StoredAttempt,
    events: tuple[DiagnosticAttemptEventReceipt, ...],
    *,
    binding: DiagnosticChildExecutionBindingArtifact,
    authorization: DiagnosticWorkerAuthorizationV2Artifact | None,
    terminal: DiagnosticChildTerminalReceiptV2Artifact | None,
) -> None:
    if len(events) != attempt.event_count or attempt.version != attempt.event_count:
        raise DiagnosticLifecycleIntegrityError(
            "attempt version/event count differs from retained event inventory"
        )
    if not events:
        raise DiagnosticLifecycleIntegrityError("attempt has no genesis event")
    previous_hash = _GENESIS_SHA256
    previous_state: str | None = None
    previous_time: datetime | None = None
    operation_ids: set[str] = set()
    for expected_sequence, event in enumerate(events, start=1):
        try:
            exact_event = _load_event_raw(event.raw_bytes)
        except DiagnosticLifecycleError as exc:
            raise DiagnosticLifecycleIntegrityError(
                f"event receipt bytes fail strict replay: {exc}"
            ) from exc
        if exact_event != event:
            raise DiagnosticLifecycleIntegrityError(
                "event dataclass projection differs from exact receipt bytes"
            )
        if event.sequence != expected_sequence:
            raise DiagnosticLifecycleIntegrityError("event sequence has a gap or reorder")
        if event.payload["tenant_id"] != attempt.tenant_id or event.payload[
            "attempt_subject_sha256"
        ] != attempt.attempt_subject_sha256:
            raise DiagnosticLifecycleIntegrityError("event tenant/subject scope drifted")
        if event.payload["previous_event_sha256"] != previous_hash:
            raise DiagnosticLifecycleIntegrityError("event hash-chain predecessor drifted")
        if event.operation_id in operation_ids:
            raise DiagnosticLifecycleIntegrityError("event operation_id was reused")
        operation_ids.add(event.operation_id)
        if expected_sequence == 1:
            if event.state_before is not None or event.state_after not in {
                AUTHORIZED,
                REJECTED,
            }:
                raise DiagnosticLifecycleIntegrityError("invalid diagnostic genesis state")
            if event.state_after == REJECTED and attempt.issuance_mode != "PREAUTHORIZATION_REJECTED":
                raise DiagnosticLifecycleIntegrityError("genesis rejection mode drifted")
            if event.operation_request_sha256 != attempt.issuance_request_sha256:
                raise DiagnosticLifecycleIntegrityError(
                    "genesis event request digest differs from issuance request"
                )
        else:
            if event.state_before != previous_state:
                raise DiagnosticLifecycleIntegrityError("event state predecessor drifted")
            if event.state_after not in _ALLOWED_TRANSITIONS.get(
                previous_state, frozenset()
            ):
                raise DiagnosticLifecycleIntegrityError("event contains an invalid transition")
        if event.event_type != event.state_after:
            raise DiagnosticLifecycleIntegrityError("event type/state drifted")
        event_time = _time(event.occurred_at)
        if previous_time is not None and event_time < previous_time:
            raise DiagnosticLifecycleIntegrityError("event time regressed")
        details = _event_details(event)
        if details.get("binding") != _artifact_ref_value(binding.artifact_ref):
            raise DiagnosticLifecycleIntegrityError("event does not bind exact child binding")
        expected_auth = (
            None
            if authorization is None
            else _artifact_ref_value(authorization.artifact_ref)
        )
        if details.get("authorization") != expected_auth:
            raise DiagnosticLifecycleIntegrityError("event authorization binding drifted")
        if event.state_after in DIAGNOSTIC_TERMINAL_STATES:
            if terminal is None or details.get("terminal_receipt") != _artifact_ref_value(
                terminal.artifact_ref
            ):
                raise DiagnosticLifecycleIntegrityError(
                    "terminal event does not bind exact terminal receipt"
                )
        elif "terminal_receipt" in details:
            raise DiagnosticLifecycleIntegrityError("nonterminal event fabricated terminal receipt")
        previous_hash = event.sha256
        previous_state = event.state_after
        previous_time = event_time
    if previous_hash != attempt.head_event_sha256 or previous_state != attempt.state:
        raise DiagnosticLifecycleIntegrityError("attempt head/state differs from event chain")
    if attempt.created_at != events[0].occurred_at or attempt.updated_at != events[-1].occurred_at:
        raise DiagnosticLifecycleIntegrityError("attempt time projection differs from event chain")


def _load_stored_family(
    attempt: _StoredAttempt,
    context: DiagnosticLifecycleReplayContext,
    events: tuple[DiagnosticAttemptEventReceipt, ...],
    profile: Mapping[str, Any],
) -> DiagnosticAttemptReplay:
    if type(context) is not DiagnosticLifecycleReplayContext:
        raise DiagnosticLifecycleValidationError(
            "context must be an exact DiagnosticLifecycleReplayContext"
        )
    try:
        shared = context.shared_plan
        request = shared.replay_study_request(context.study_request)
        binding = _shared_load_binding(shared, request, attempt.binding_raw)
        if binding.attempt_ordinal != 1 or attempt.attempt_ordinal != 1:
            raise DiagnosticLifecycleIntegrityError("attempt ordinal is not exactly one")
        subject = derive_diagnostic_attempt_subject_sha256(
            plan=context.plan,
            study_request=context.study_request,
        )
        bound_subject = binding.payload["execution_context"]["attempt_binding"][
            "attempt_subject_sha256"
        ]
        if subject != bound_subject or subject != attempt.attempt_subject_sha256:
            raise DiagnosticLifecycleIntegrityError("attempt subject digest drifted")
        nonce_sha = binding.payload["execution_context"]["attempt_binding"][
            "run_nonce"
        ]["sha256"]
        if nonce_sha != attempt.run_nonce_sha256:
            raise DiagnosticLifecycleIntegrityError("attempt nonce digest drifted")
        if (
            binding.study_id != attempt.study_id
            or binding.case_id != attempt.case_id
            or binding.case_execution_ordinal != attempt.case_execution_ordinal
        ):
            raise DiagnosticLifecycleIntegrityError("stored case projection drifted")
        authorization = None
        if attempt.authorization_raw is not None:
            authorization = _shared_load_authorization(
                shared,
                request,
                binding,
                attempt.authorization_raw,
            )
            if (
                authorization.attempt_ordinal != 1
                or authorization.run_nonce_b64url != binding.run_nonce_b64url
            ):
                raise DiagnosticLifecycleIntegrityError(
                    "authorization attempt/nonce differs from binding"
                )
        bodies = {role: raw for role, raw in attempt.produced_artifact_bodies}
        terminal = None
        if attempt.terminal_raw is not None:
            terminal = _shared_load_terminal(
                shared,
                request,
                binding,
                authorization,
                attempt.terminal_raw,
                bodies,
            )
        elif bodies:
            raise DiagnosticLifecycleIntegrityError(
                "produced bodies exist without a terminal receipt"
            )
    except DiagnosticLifecycleError:
        raise
    except (SchemaValidationError, ValueError, KeyError, TypeError) as exc:
        raise DiagnosticLifecycleIntegrityError(
            f"stored execution carrier replay failed: {exc}"
        ) from exc

    if attempt.issuance_mode == "PREAUTHORIZATION_REJECTED":
        if authorization is not None or attempt.state != REJECTED:
            raise DiagnosticLifecycleIntegrityError(
                "preauthorization rejection fabricated authorization/state"
            )
    elif authorization is None:
        raise DiagnosticLifecycleIntegrityError("authorized attempt lacks authorization")

    if attempt.state in {AUTHORIZED, RUNNING}:
        if terminal is not None:
            raise DiagnosticLifecycleIntegrityError("nonterminal state carries terminal receipt")
    else:
        if terminal is None or terminal.terminal_status != attempt.state:
            raise DiagnosticLifecycleIntegrityError("terminal state/receipt drifted")
    if attempt.state == AUTHORIZED and attempt.worker_started_at is not None:
        raise DiagnosticLifecycleIntegrityError("AUTHORIZED attempt has worker start")
    if attempt.state == RUNNING and attempt.worker_started_at is None:
        raise DiagnosticLifecycleIntegrityError("RUNNING attempt lacks worker start")
    if terminal is not None and terminal.worker_started_at != attempt.worker_started_at:
        raise DiagnosticLifecycleIntegrityError("terminal worker-start projection drifted")

    _verify_event_chain(
        attempt,
        events,
        binding=binding,
        authorization=authorization,
        terminal=terminal,
    )
    snapshot = DiagnosticAttemptSnapshot(
        tenant_id=attempt.tenant_id,
        attempt_subject_sha256=attempt.attempt_subject_sha256,
        attempt_ordinal=attempt.attempt_ordinal,
        study_id=attempt.study_id,
        case_id=attempt.case_id,
        case_execution_ordinal=attempt.case_execution_ordinal,
        state=attempt.state,
        record_version=attempt.version,
        issuance_mode=attempt.issuance_mode,
        issuance_request_sha256=attempt.issuance_request_sha256,
        run_nonce_sha256=attempt.run_nonce_sha256,
        binding_ref=binding.artifact_ref,
        authorization_ref=(None if authorization is None else authorization.artifact_ref),
        terminal_receipt_ref=(None if terminal is None else terminal.artifact_ref),
        worker_started_at=attempt.worker_started_at,
        created_at=attempt.created_at,
        updated_at=attempt.updated_at,
        event_count=attempt.event_count,
        head_event_sha256=attempt.head_event_sha256,
        backend_durability_profile=_frozen_mapping(profile),
        authority=_frozen_mapping(_AUTHORITY),
    )
    return DiagnosticAttemptReplay(
        snapshot=snapshot,
        binding=binding,
        authorization=authorization,
        terminal_receipt=terminal,
        produced_artifact_bodies=MappingProxyType(dict(bodies)),
        events=events,
    )


class DiagnosticAttemptLifecycle:
    """One-use per-case lifecycle over exact diagnostic execution-v2 carriers."""

    def __init__(
        self,
        store: DiagnosticLifecycleStore,
        *,
        nonce_factory: Callable[[int], bytes] = secrets.token_bytes,
    ) -> None:
        if store is None:
            raise DiagnosticLifecycleValidationError("a lifecycle store is required")
        if not callable(nonce_factory):
            raise DiagnosticLifecycleValidationError("nonce_factory must be callable")
        required = {
            "create_attempt",
            "compare_and_swap",
            "get_attempt",
            "list_attempts",
            "list_events",
            "durability_profile",
        }
        if any(not hasattr(store, name) for name in required):
            raise DiagnosticLifecycleValidationError(
                "store does not implement the DiagnosticLifecycleStore contract"
            )
        self._store = store
        self._nonce_factory = nonce_factory
        self._profile = _frozen_mapping(store.durability_profile)

    @property
    def backend_durability_profile(self) -> Mapping[str, Any]:
        return self._profile

    def _scope(self, tenant_id: str, subject: str) -> tuple[str, str]:
        tenant = _required_text(tenant_id, "tenant_id")
        return tenant, _required_sha256(subject, "attempt_subject_sha256")

    def _record(self, tenant_id: str, subject: str) -> _StoredAttempt:
        tenant, subject = self._scope(tenant_id, subject)
        record = self._store.get_attempt(tenant, subject)
        if record is None:
            raise DiagnosticLifecycleNotFound("diagnostic attempt not found")
        return record

    def read_attempt(
        self,
        *,
        tenant_id: str,
        attempt_subject_sha256: str,
        context: DiagnosticLifecycleReplayContext,
    ) -> DiagnosticAttemptReplay:
        record = self._record(tenant_id, attempt_subject_sha256)
        events = self._store.list_events(
            record.tenant_id, record.attempt_subject_sha256
        )
        return _load_stored_family(record, context, events, self._profile)

    def list_subjects(self, *, tenant_id: str) -> tuple[str, ...]:
        tenant = _required_text(tenant_id, "tenant_id")
        return tuple(
            row.attempt_subject_sha256 for row in self._store.list_attempts(tenant)
        )

    def list_snapshots(
        self,
        *,
        tenant_id: str,
        contexts: Mapping[str, DiagnosticLifecycleReplayContext],
    ) -> tuple[DiagnosticAttemptSnapshot, ...]:
        tenant = _required_text(tenant_id, "tenant_id")
        if not isinstance(contexts, Mapping):
            raise DiagnosticLifecycleValidationError("contexts must be a mapping")
        rows: list[DiagnosticAttemptSnapshot] = []
        for record in self._store.list_attempts(tenant):
            context = contexts.get(record.attempt_subject_sha256)
            if context is None:
                raise DiagnosticLifecycleIntegrityError(
                    f"no replay context for subject {record.attempt_subject_sha256}"
                )
            events = self._store.list_events(tenant, record.attempt_subject_sha256)
            rows.append(
                _load_stored_family(record, context, events, self._profile).snapshot
            )
        return tuple(rows)

    def list_events(
        self,
        *,
        tenant_id: str,
        attempt_subject_sha256: str,
        context: DiagnosticLifecycleReplayContext,
    ) -> tuple[DiagnosticAttemptEventReceipt, ...]:
        return self.read_attempt(
            tenant_id=tenant_id,
            attempt_subject_sha256=attempt_subject_sha256,
            context=context,
        ).events

    def _fresh_nonce(self) -> bytes:
        try:
            value = self._nonce_factory(32)
        except Exception as exc:
            raise DiagnosticLifecycleValidationError("nonce factory failed") from exc
        if type(value) is not bytes or len(value) != 32:
            raise DiagnosticLifecycleValidationError(
                "nonce factory must return exactly 32 immutable bytes"
            )
        return value

    def _issuance_request_sha256(
        self,
        *,
        mode: str,
        tenant_id: str,
        subject: str,
        operation_id: str,
        execution_contract: DiagnosticStageCExecutionContractArtifact,
        binding_id: str,
        binding_created_at: str,
        assigned_worker_id: str,
        archive_root: str,
        artifact_ids: Mapping[str, str],
        issued_at: str | None,
        expires_at: str | None,
        terminal_at: str | None,
        error: Mapping[str, Any] | None,
    ) -> str:
        try:
            value = {
                "domain": "cas_harness_v2.diagnostic_attempt_issuance_request.v1",
                "mode": mode,
                "tenant_id": tenant_id,
                "attempt_subject_sha256": subject,
                "operation_id": operation_id,
                "attempt_ordinal": 1,
                "execution_contract": _artifact_ref_value(
                    execution_contract.artifact_ref
                ),
                "binding_id": binding_id,
                "binding_created_at": binding_created_at,
                "assigned_worker_id": assigned_worker_id,
                "archive_root": archive_root,
                "artifact_ids": dict(artifact_ids),
                "issued_at": issued_at,
                "expires_at": expires_at,
                "terminal_at": terminal_at,
                "error": None if error is None else thaw_json(error),
                "retry_policy": {
                    "maximum_attempts": 1,
                    "attempt_ordinal": 1,
                    "retry_count": 0,
                    "retry": "FORBIDDEN",
                    "replacement": "FORBIDDEN",
                },
            }
            return canonical_sha256(value)
        except (SchemaValidationError, ValueError, TypeError, KeyError) as exc:
            raise DiagnosticLifecycleValidationError(
                f"issuance request is not canonical: {exc}"
            ) from exc

    def _existing_for_request(
        self,
        *,
        tenant_id: str,
        subject: str,
        mode: str,
        request_sha256: str,
        context: DiagnosticLifecycleReplayContext,
    ) -> DiagnosticAttemptReplay | None:
        record = self._store.get_attempt(tenant_id, subject)
        if record is None:
            return None
        if (
            record.issuance_mode != mode
            or record.issuance_request_sha256 != request_sha256
        ):
            raise DiagnosticLifecycleConflict(
                "attempt subject is already reserved for different exact issuance facts"
            )
        events = self._store.list_events(tenant_id, subject)
        return _load_stored_family(record, context, events, self._profile)

    def _create_or_observe_race(
        self,
        *,
        attempt: _StoredAttempt,
        event: DiagnosticAttemptEventReceipt,
        mode: str,
        request_sha256: str,
        context: DiagnosticLifecycleReplayContext,
    ) -> tuple[DiagnosticAttemptReplay, bool]:
        try:
            self._store.create_attempt(attempt, event)
        except DiagnosticLifecycleConflict:
            existing = self._existing_for_request(
                tenant_id=attempt.tenant_id,
                subject=attempt.attempt_subject_sha256,
                mode=mode,
                request_sha256=request_sha256,
                context=context,
            )
            if existing is None:
                raise DiagnosticLifecyclePersistenceError(
                    "create conflict has no tenant-visible winner"
                )
            return existing, False
        replay = self.read_attempt(
            tenant_id=attempt.tenant_id,
            attempt_subject_sha256=attempt.attempt_subject_sha256,
            context=context,
        )
        return replay, True

    def issue_attempt(
        self,
        *,
        tenant_id: str,
        chain: DiagnosticPreregistrationChain,
        plan: DiagnosticStudyPlanArtifact,
        study_request: DiagnosticStudyRequestArtifact,
        execution_contract: DiagnosticStageCExecutionContractArtifact,
        shared_plan_context: DiagnosticSharedPlanReplayContext,
        binding_id: str,
        binding_created_at: str,
        assigned_worker_id: str,
        archive_root: str,
        artifact_ids: Mapping[str, str],
        issued_at: str,
        expires_at: str,
        operation_id: str,
    ) -> DiagnosticAttemptIssuance:
        """Atomically issue one exact binding/auth pair and release its nonce once."""

        tenant = _required_text(tenant_id, "tenant_id")
        operation = _required_text(operation_id, "operation_id", machine=True)
        if type(execution_contract) is not DiagnosticStageCExecutionContractArtifact:
            raise DiagnosticLifecycleValidationError(
                "execution_contract must be an exact carrier"
            )
        _verify_shared_scope(
            shared_plan_context,
            chain=chain,
            plan=plan,
            execution_contract=execution_contract,
        )
        study_request = shared_plan_context.replay_study_request(study_request)
        subject = derive_diagnostic_attempt_subject_sha256(
            plan=plan, study_request=study_request
        )
        context = DiagnosticLifecycleReplayContext(
            shared_plan=shared_plan_context,
            study_request=study_request,
        )
        request_sha = self._issuance_request_sha256(
            mode="AUTHORIZED",
            tenant_id=tenant,
            subject=subject,
            operation_id=operation,
            execution_contract=execution_contract,
            binding_id=binding_id,
            binding_created_at=binding_created_at,
            assigned_worker_id=assigned_worker_id,
            archive_root=archive_root,
            artifact_ids=artifact_ids,
            issued_at=issued_at,
            expires_at=expires_at,
            terminal_at=None,
            error=None,
        )
        existing = self._existing_for_request(
            tenant_id=tenant,
            subject=subject,
            mode="AUTHORIZED",
            request_sha256=request_sha,
            context=context,
        )
        if existing is not None:
            if existing.authorization is None:
                raise DiagnosticLifecycleIntegrityError(
                    "authorized issuance replay has no authorization"
                )
            return DiagnosticAttemptIssuance(
                snapshot=existing.snapshot,
                binding=existing.binding,
                authorization=existing.authorization,
                run_nonce_b64url=None,
                issued_now=False,
            )

        nonce = self._fresh_nonce()
        try:
            binding = _shared_build_binding(
                shared_plan_context,
                study_request,
                binding_id=binding_id,
                created_at=binding_created_at,
                run_nonce=nonce,
                assigned_worker_id=assigned_worker_id,
                archive_root=archive_root,
                artifact_ids=artifact_ids,
            )
            authorization = _shared_build_authorization(
                shared_plan_context,
                study_request,
                binding,
                issued_at=issued_at,
                expires_at=expires_at,
            )
        except (SchemaValidationError, ValueError, TypeError, KeyError) as exc:
            raise DiagnosticLifecycleValidationError(
                f"exact diagnostic issuance carrier build failed: {exc}"
            ) from exc
        bound_subject = binding.payload["execution_context"]["attempt_binding"][
            "attempt_subject_sha256"
        ]
        nonce_sha = binding.payload["execution_context"]["attempt_binding"][
            "run_nonce"
        ]["sha256"]
        if bound_subject != subject or binding.attempt_ordinal != 1:
            raise DiagnosticLifecycleIntegrityError("new binding subject/attempt drifted")
        event = _build_event(
            tenant_id=tenant,
            attempt_subject_sha256=subject,
            sequence=1,
            previous_event_sha256=_GENESIS_SHA256,
            event_type=AUTHORIZED,
            state_before=None,
            state_after=AUTHORIZED,
            occurred_at=authorization.issued_at,
            operation_id=operation,
            operation_request_sha256=request_sha,
            details={
                "binding": _artifact_ref_value(binding.artifact_ref),
                "authorization": _artifact_ref_value(authorization.artifact_ref),
                "run_nonce_sha256": nonce_sha,
                "attempt_ordinal": 1,
                "retry": "FORBIDDEN",
                "replacement": "FORBIDDEN",
            },
        )
        attempt = _StoredAttempt(
            tenant_id=tenant,
            attempt_subject_sha256=subject,
            attempt_ordinal=1,
            study_id=binding.study_id,
            case_id=binding.case_id,
            case_execution_ordinal=binding.case_execution_ordinal,
            issuance_mode="AUTHORIZED",
            issuance_request_sha256=request_sha,
            state=AUTHORIZED,
            version=1,
            run_nonce_sha256=nonce_sha,
            binding_raw=binding.raw_bytes,
            authorization_raw=authorization.raw_bytes,
            terminal_raw=None,
            produced_artifact_bodies=(),
            worker_started_at=None,
            created_at=event.occurred_at,
            updated_at=event.occurred_at,
            event_count=1,
            head_event_sha256=event.sha256,
        )
        replay, created = self._create_or_observe_race(
            attempt=attempt,
            event=event,
            mode="AUTHORIZED",
            request_sha256=request_sha,
            context=context,
        )
        if replay.authorization is None:
            raise DiagnosticLifecycleIntegrityError("issued attempt has no authorization")
        return DiagnosticAttemptIssuance(
            snapshot=replay.snapshot,
            binding=replay.binding,
            authorization=replay.authorization,
            run_nonce_b64url=(replay.binding.run_nonce_b64url if created else None),
            issued_now=created,
        )

    def reject_preauthorization(
        self,
        *,
        tenant_id: str,
        chain: DiagnosticPreregistrationChain,
        plan: DiagnosticStudyPlanArtifact,
        study_request: DiagnosticStudyRequestArtifact,
        execution_contract: DiagnosticStageCExecutionContractArtifact,
        shared_plan_context: DiagnosticSharedPlanReplayContext,
        binding_id: str,
        binding_created_at: str,
        assigned_worker_id: str,
        archive_root: str,
        artifact_ids: Mapping[str, str],
        terminal_at: str,
        error: Mapping[str, Any],
        operation_id: str,
    ) -> DiagnosticAttemptMutation:
        """Create one terminal preauthorization rejection without false auth."""

        tenant = _required_text(tenant_id, "tenant_id")
        operation = _required_text(operation_id, "operation_id", machine=True)
        _verify_shared_scope(
            shared_plan_context,
            chain=chain,
            plan=plan,
            execution_contract=execution_contract,
        )
        study_request = shared_plan_context.replay_study_request(study_request)
        subject = derive_diagnostic_attempt_subject_sha256(
            plan=plan, study_request=study_request
        )
        context = DiagnosticLifecycleReplayContext(
            shared_plan=shared_plan_context,
            study_request=study_request,
        )
        request_sha = self._issuance_request_sha256(
            mode="PREAUTHORIZATION_REJECTED",
            tenant_id=tenant,
            subject=subject,
            operation_id=operation,
            execution_contract=execution_contract,
            binding_id=binding_id,
            binding_created_at=binding_created_at,
            assigned_worker_id=assigned_worker_id,
            archive_root=archive_root,
            artifact_ids=artifact_ids,
            issued_at=None,
            expires_at=None,
            terminal_at=terminal_at,
            error=error,
        )
        existing = self._existing_for_request(
            tenant_id=tenant,
            subject=subject,
            mode="PREAUTHORIZATION_REJECTED",
            request_sha256=request_sha,
            context=context,
        )
        if existing is not None:
            if existing.terminal_receipt is None:
                raise DiagnosticLifecycleIntegrityError(
                    "preauthorization rejection replay lacks terminal"
                )
            return DiagnosticAttemptMutation(
                snapshot=existing.snapshot,
                binding=existing.binding,
                authorization=None,
                terminal_receipt=existing.terminal_receipt,
                event=existing.events[0],
                transitioned_now=False,
            )

        nonce = self._fresh_nonce()
        try:
            binding = _shared_build_binding(
                shared_plan_context,
                study_request,
                binding_id=binding_id,
                created_at=binding_created_at,
                run_nonce=nonce,
                assigned_worker_id=assigned_worker_id,
                archive_root=archive_root,
                artifact_ids=artifact_ids,
            )
            terminal = _shared_build_terminal(
                shared_plan_context,
                study_request,
                binding,
                None,
                terminal_at=terminal_at,
                terminal_status=REJECTED,
                terminal_phase="PRE_AUTHORIZATION",
                invocation_certainty="EXACTLY_ZERO",
                worker_started_at=None,
                produced_artifacts=None,
                error=error,
            )
        except (SchemaValidationError, ValueError, TypeError, KeyError) as exc:
            raise DiagnosticLifecycleValidationError(
                f"exact preauthorization rejection build failed: {exc}"
            ) from exc
        nonce_sha = binding.payload["execution_context"]["attempt_binding"][
            "run_nonce"
        ]["sha256"]
        event = _build_event(
            tenant_id=tenant,
            attempt_subject_sha256=subject,
            sequence=1,
            previous_event_sha256=_GENESIS_SHA256,
            event_type=REJECTED,
            state_before=None,
            state_after=REJECTED,
            occurred_at=terminal.terminal_at,
            operation_id=operation,
            operation_request_sha256=request_sha,
            details={
                "binding": _artifact_ref_value(binding.artifact_ref),
                "authorization": None,
                "terminal_receipt": _artifact_ref_value(terminal.artifact_ref),
                "run_nonce_sha256": nonce_sha,
                "nonce_disposition": "RESERVED_UNCONSUMED_TERMINALLY_RETIRED",
                "model_invocation_request_count": 0,
                "retry": "FORBIDDEN",
                "replacement": "FORBIDDEN",
            },
        )
        attempt = _StoredAttempt(
            tenant_id=tenant,
            attempt_subject_sha256=subject,
            attempt_ordinal=1,
            study_id=binding.study_id,
            case_id=binding.case_id,
            case_execution_ordinal=binding.case_execution_ordinal,
            issuance_mode="PREAUTHORIZATION_REJECTED",
            issuance_request_sha256=request_sha,
            state=REJECTED,
            version=1,
            run_nonce_sha256=nonce_sha,
            binding_raw=binding.raw_bytes,
            authorization_raw=None,
            terminal_raw=terminal.raw_bytes,
            produced_artifact_bodies=(),
            worker_started_at=None,
            created_at=event.occurred_at,
            updated_at=event.occurred_at,
            event_count=1,
            head_event_sha256=event.sha256,
        )
        replay, created = self._create_or_observe_race(
            attempt=attempt,
            event=event,
            mode="PREAUTHORIZATION_REJECTED",
            request_sha256=request_sha,
            context=context,
        )
        if replay.terminal_receipt is None:
            raise DiagnosticLifecycleIntegrityError("preauthorization rejection lost terminal")
        return DiagnosticAttemptMutation(
            snapshot=replay.snapshot,
            binding=replay.binding,
            authorization=None,
            terminal_receipt=replay.terminal_receipt,
            event=replay.events[0],
            transitioned_now=created,
        )

    def _find_operation(
        self,
        replay: DiagnosticAttemptReplay,
        operation_id: str,
        request_sha256: str,
    ) -> DiagnosticAttemptEventReceipt | None:
        matches = tuple(
            event for event in replay.events if event.operation_id == operation_id
        )
        if not matches:
            return None
        if len(matches) != 1 or matches[0].operation_request_sha256 != request_sha256:
            raise DiagnosticLifecycleConflict(
                "operation_id is already bound to different exact facts"
            )
        return matches[0]

    def consume_attempt(
        self,
        *,
        tenant_id: str,
        attempt_subject_sha256: str,
        context: DiagnosticLifecycleReplayContext,
        run_nonce_b64url: str,
        worker_started_at: str,
        operation_id: str,
    ) -> DiagnosticAttemptMutation:
        """CAS AUTHORIZED->RUNNING; only transitioned_now may invoke a model."""

        tenant, subject = self._scope(tenant_id, attempt_subject_sha256)
        operation = _required_text(operation_id, "operation_id", machine=True)
        started_at = _required_timestamp(worker_started_at, "worker_started_at")
        supplied_nonce = _required_text(run_nonce_b64url, "run_nonce_b64url")
        try:
            supplied_nonce_bytes = supplied_nonce.encode("ascii")
        except UnicodeEncodeError as exc:
            raise DiagnosticLifecycleValidationError(
                "run_nonce_b64url must be ASCII base64url text"
            ) from exc
        request_sha = canonical_sha256(
            {
                "domain": "cas_harness_v2.diagnostic_attempt_consumption.v1",
                "tenant_id": tenant,
                "attempt_subject_sha256": subject,
                "operation_id": operation,
                "run_nonce_sha256": sha256_bytes(supplied_nonce_bytes),
                "worker_started_at": started_at,
            }
        )
        replay = self.read_attempt(
            tenant_id=tenant,
            attempt_subject_sha256=subject,
            context=context,
        )
        prior = self._find_operation(replay, operation, request_sha)
        if prior is not None:
            return DiagnosticAttemptMutation(
                snapshot=replay.snapshot,
                binding=replay.binding,
                authorization=replay.authorization,
                terminal_receipt=replay.terminal_receipt,
                event=prior,
                transitioned_now=False,
            )
        if replay.snapshot.state != AUTHORIZED or replay.authorization is None:
            raise DiagnosticLifecycleConflict(
                f"cannot consume attempt from {replay.snapshot.state}"
            )
        if not hmac.compare_digest(
            supplied_nonce_bytes,
            replay.authorization.run_nonce_b64url.encode("ascii"),
        ):
            raise DiagnosticLifecycleConflict("attempt nonce does not match authorization")
        if _time(started_at) < max(
            _time(replay.authorization.issued_at),
            _time(replay.authorization.not_before),
        ):
            raise DiagnosticLifecycleConflict("worker start precedes authorization window")
        if _time(started_at) >= _time(replay.authorization.expires_at):
            raise DiagnosticLifecycleExpired("authorization expired before consumption")
        previous = self._record(tenant, subject)
        event = _build_event(
            tenant_id=tenant,
            attempt_subject_sha256=subject,
            sequence=previous.event_count + 1,
            previous_event_sha256=previous.head_event_sha256,
            event_type=RUNNING,
            state_before=AUTHORIZED,
            state_after=RUNNING,
            occurred_at=started_at,
            operation_id=operation,
            operation_request_sha256=request_sha,
            details={
                "binding": _artifact_ref_value(replay.binding.artifact_ref),
                "authorization": _artifact_ref_value(
                    replay.authorization.artifact_ref
                ),
                "worker_started_at": started_at,
                "model_invocation_permission": "ONE_WINNER_ONLY_IF_TRANSITIONED_NOW",
                "retry": "FORBIDDEN",
                "replacement": "FORBIDDEN",
            },
        )
        updated = replace(
            previous,
            state=RUNNING,
            version=previous.version + 1,
            worker_started_at=started_at,
            updated_at=event.occurred_at,
            event_count=event.sequence,
            head_event_sha256=event.sha256,
        )
        try:
            self._store.compare_and_swap(
                updated, event, expected_version=previous.version
            )
            changed = True
        except (DiagnosticLifecycleVersionConflict, DiagnosticLifecycleConflict):
            concurrent = self.read_attempt(
                tenant_id=tenant,
                attempt_subject_sha256=subject,
                context=context,
            )
            prior = self._find_operation(concurrent, operation, request_sha)
            if prior is None:
                raise DiagnosticLifecycleConflict(
                    "another operation consumed or terminalized the attempt"
                )
            replay = concurrent
            event = prior
            changed = False
        else:
            replay = self.read_attempt(
                tenant_id=tenant,
                attempt_subject_sha256=subject,
                context=context,
            )
        return DiagnosticAttemptMutation(
            snapshot=replay.snapshot,
            binding=replay.binding,
            authorization=replay.authorization,
            terminal_receipt=replay.terminal_receipt,
            event=event,
            transitioned_now=changed,
        )

    def record_terminal(
        self,
        *,
        tenant_id: str,
        attempt_subject_sha256: str,
        context: DiagnosticLifecycleReplayContext,
        terminal_receipt: DiagnosticChildTerminalReceiptV2Artifact,
        produced_artifact_bodies: Mapping[str, bytes] | None,
        operation_id: str,
    ) -> DiagnosticAttemptMutation:
        """Atomically bind the one exact terminal receipt to an attempt."""

        tenant, subject = self._scope(tenant_id, attempt_subject_sha256)
        operation = _required_text(operation_id, "operation_id", machine=True)
        if type(terminal_receipt) is not DiagnosticChildTerminalReceiptV2Artifact:
            raise DiagnosticLifecycleValidationError(
                "terminal_receipt must have the exact v2 artifact type"
            )
        if produced_artifact_bodies is None:
            body_map: dict[str, bytes] = {}
        elif not isinstance(produced_artifact_bodies, Mapping):
            raise DiagnosticLifecycleValidationError(
                "produced_artifact_bodies must be a mapping"
            )
        else:
            body_map = {}
            for role, raw in produced_artifact_bodies.items():
                role = _required_text(role, "produced_artifact_bodies.role", machine=True)
                if type(raw) is not bytes:
                    raise DiagnosticLifecycleValidationError(
                        f"produced_artifact_bodies.{role} must be exact bytes"
                    )
                body_map[role] = raw
        request_sha = canonical_sha256(
            {
                "domain": "cas_harness_v2.diagnostic_attempt_terminal.v1",
                "tenant_id": tenant,
                "attempt_subject_sha256": subject,
                "operation_id": operation,
                "terminal_receipt": _artifact_ref_value(terminal_receipt.artifact_ref),
                "produced_artifact_bodies": [
                    {
                        "role": role,
                        "sha256": sha256_bytes(raw),
                        "byte_length": len(raw),
                    }
                    for role, raw in sorted(body_map.items())
                ],
            }
        )
        replay = self.read_attempt(
            tenant_id=tenant,
            attempt_subject_sha256=subject,
            context=context,
        )
        prior = self._find_operation(replay, operation, request_sha)
        if prior is not None:
            if replay.terminal_receipt is None:
                raise DiagnosticLifecycleIntegrityError(
                    "terminal operation exists without terminal receipt"
                )
            return DiagnosticAttemptMutation(
                snapshot=replay.snapshot,
                binding=replay.binding,
                authorization=replay.authorization,
                terminal_receipt=replay.terminal_receipt,
                event=prior,
                transitioned_now=False,
            )
        if replay.authorization is None:
            raise DiagnosticLifecycleConflict(
                "preauthorization rejection is terminal at creation"
            )
        status = terminal_receipt.terminal_status
        if status not in _ALLOWED_TRANSITIONS.get(replay.snapshot.state, frozenset()):
            raise DiagnosticLifecycleConflict(
                f"cannot terminalize {replay.snapshot.state} as {status}"
            )
        try:
            loaded = _shared_load_terminal(
                context.shared_plan,
                context.study_request,
                replay.binding,
                replay.authorization,
                terminal_receipt.raw_bytes,
                body_map,
            )
        except (SchemaValidationError, ValueError, KeyError, TypeError) as exc:
            raise DiagnosticLifecycleValidationError(
                f"exact terminal carrier replay failed: {exc}"
            ) from exc
        if loaded.raw_bytes != terminal_receipt.raw_bytes:
            raise DiagnosticLifecycleValidationError("terminal carrier is not its exact replay")
        if status in {COMPLETED, FAILED, INDETERMINATE}:
            if (
                replay.snapshot.state != RUNNING
                or loaded.worker_started_at != replay.snapshot.worker_started_at
            ):
                raise DiagnosticLifecycleConflict(
                    "post-dispatch terminal does not bind the consumed worker start"
                )
        elif (
            replay.snapshot.state != AUTHORIZED
            or loaded.worker_started_at is not None
            or body_map
        ):
            raise DiagnosticLifecycleConflict(
                "unconsumed terminal must be output-free and lack worker start"
            )
        previous = self._record(tenant, subject)
        if previous.version != replay.snapshot.record_version:
            raise DiagnosticLifecycleVersionConflict("attempt changed before terminal CAS")
        event = _build_event(
            tenant_id=tenant,
            attempt_subject_sha256=subject,
            sequence=previous.event_count + 1,
            previous_event_sha256=previous.head_event_sha256,
            event_type=status,
            state_before=previous.state,
            state_after=status,
            occurred_at=loaded.terminal_at,
            operation_id=operation,
            operation_request_sha256=request_sha,
            details={
                "binding": _artifact_ref_value(replay.binding.artifact_ref),
                "authorization": _artifact_ref_value(replay.authorization.artifact_ref),
                "terminal_receipt": _artifact_ref_value(loaded.artifact_ref),
                "produced_artifacts": [
                    {
                        "role": role,
                        "sha256": sha256_bytes(raw),
                        "byte_length": len(raw),
                    }
                    for role, raw in sorted(body_map.items())
                ],
                "nonce_disposition": (
                    "ISSUED_UNCONSUMED_TERMINALLY_RETIRED"
                    if previous.state == AUTHORIZED
                    else "CONSUMED_SINGLE_ATTEMPT_TERMINAL"
                ),
                "retry": "FORBIDDEN",
                "replacement": "FORBIDDEN",
            },
        )
        updated = replace(
            previous,
            state=status,
            version=previous.version + 1,
            terminal_raw=loaded.raw_bytes,
            produced_artifact_bodies=tuple(sorted(body_map.items())),
            updated_at=event.occurred_at,
            event_count=event.sequence,
            head_event_sha256=event.sha256,
        )
        try:
            self._store.compare_and_swap(
                updated, event, expected_version=previous.version
            )
            transitioned = True
        except (DiagnosticLifecycleVersionConflict, DiagnosticLifecycleConflict):
            concurrent = self.read_attempt(
                tenant_id=tenant,
                attempt_subject_sha256=subject,
                context=context,
            )
            prior = self._find_operation(concurrent, operation, request_sha)
            if prior is None:
                raise DiagnosticLifecycleConflict(
                    "another operation terminalized the attempt"
                )
            replay = concurrent
            event = prior
            transitioned = False
        else:
            replay = self.read_attempt(
                tenant_id=tenant,
                attempt_subject_sha256=subject,
                context=context,
            )
        return DiagnosticAttemptMutation(
            snapshot=replay.snapshot,
            binding=replay.binding,
            authorization=replay.authorization,
            terminal_receipt=replay.terminal_receipt,
            event=event,
            transitioned_now=transitioned,
        )

    def build_and_record_terminal(
        self,
        *,
        tenant_id: str,
        attempt_subject_sha256: str,
        context: DiagnosticLifecycleReplayContext,
        terminal_at: str,
        terminal_status: str,
        terminal_phase: str,
        invocation_certainty: str,
        produced_artifacts: Mapping[str, tuple[ArtifactRef, bytes]] | None,
        error: Mapping[str, Any] | None,
        operation_id: str,
    ) -> DiagnosticAttemptMutation:
        """Build through the frozen carrier API, then atomically retain it."""

        replay = self.read_attempt(
            tenant_id=tenant_id,
            attempt_subject_sha256=attempt_subject_sha256,
            context=context,
        )
        if replay.authorization is None:
            raise DiagnosticLifecycleConflict(
                "preauthorization rejection cannot build another terminal"
            )
        bodies = {
            role: pair[1]
            for role, pair in ({} if produced_artifacts is None else produced_artifacts).items()
        }
        try:
            terminal = _shared_build_terminal(
                context.shared_plan,
                context.study_request,
                replay.binding,
                replay.authorization,
                terminal_at=_required_timestamp(terminal_at, "terminal_at"),
                terminal_status=terminal_status,
                terminal_phase=terminal_phase,
                invocation_certainty=invocation_certainty,
                worker_started_at=replay.snapshot.worker_started_at,
                produced_artifacts=produced_artifacts,
                error=error,
            )
        except (SchemaValidationError, ValueError, KeyError, TypeError) as exc:
            raise DiagnosticLifecycleValidationError(
                f"exact terminal build failed: {exc}"
            ) from exc
        return self.record_terminal(
            tenant_id=tenant_id,
            attempt_subject_sha256=attempt_subject_sha256,
            context=context,
            terminal_receipt=terminal,
            produced_artifact_bodies=bodies,
            operation_id=operation_id,
        )

    def reject_authorized_attempt(
        self,
        *,
        tenant_id: str,
        attempt_subject_sha256: str,
        context: DiagnosticLifecycleReplayContext,
        terminal_at: str,
        error: Mapping[str, Any],
        operation_id: str,
    ) -> DiagnosticAttemptMutation:
        return self.build_and_record_terminal(
            tenant_id=tenant_id,
            attempt_subject_sha256=attempt_subject_sha256,
            context=context,
            terminal_at=terminal_at,
            terminal_status=REJECTED,
            terminal_phase="PRE_ADMISSION",
            invocation_certainty="EXACTLY_ZERO",
            produced_artifacts=None,
            error=error,
            operation_id=operation_id,
        )

    def expire_authorized_attempt(
        self,
        *,
        tenant_id: str,
        attempt_subject_sha256: str,
        context: DiagnosticLifecycleReplayContext,
        terminal_at: str,
        error: Mapping[str, Any],
        operation_id: str,
    ) -> DiagnosticAttemptMutation:
        return self.build_and_record_terminal(
            tenant_id=tenant_id,
            attempt_subject_sha256=attempt_subject_sha256,
            context=context,
            terminal_at=terminal_at,
            terminal_status=EXPIRED,
            terminal_phase="AUTHORIZATION_EXPIRED",
            invocation_certainty="EXACTLY_ZERO",
            produced_artifacts=None,
            error=error,
            operation_id=operation_id,
        )

    def terminalize_stranded_running(
        self,
        *,
        tenant_id: str,
        attempt_subject_sha256: str,
        context: DiagnosticLifecycleReplayContext,
        observed_at: str,
        operation_id: str,
        error: Mapping[str, Any] | None = None,
    ) -> DiagnosticAttemptMutation:
        adverse = (
            {
                "code": "diagnostic_running_stranded",
                "category": "EXECUTION_INDETERMINATE",
                "message": "RUNNING attempt lacked an authoritative terminal after recovery",
                "retryable": False,
            }
            if error is None
            else error
        )
        return self.build_and_record_terminal(
            tenant_id=tenant_id,
            attempt_subject_sha256=attempt_subject_sha256,
            context=context,
            terminal_at=observed_at,
            terminal_status=INDETERMINATE,
            terminal_phase="DISPATCH_OR_EXECUTION",
            invocation_certainty="INDETERMINATE_ZERO_OR_ONE",
            produced_artifacts=None,
            error=adverse,
            operation_id=operation_id,
        )

    def reconcile(
        self,
        *,
        tenant_id: str,
        contexts: Mapping[str, DiagnosticLifecycleReplayContext],
    ) -> DiagnosticAttemptReconciliation:
        """Read-only structural reconciliation; it is not a phase seal."""

        tenant = _required_text(tenant_id, "tenant_id")
        if not isinstance(contexts, Mapping):
            raise DiagnosticLifecycleValidationError("contexts must be a mapping")
        attempts = self._store.list_attempts(tenant)
        subjects = {attempt.attempt_subject_sha256 for attempt in attempts}
        issues: list[DiagnosticAttemptReconciliationIssue] = []
        counts = {state: 0 for state in sorted(DIAGNOSTIC_ATTEMPT_STATES)}
        event_count = 0
        integrity_clean = True
        all_terminal = True
        for attempt in attempts:
            counts[attempt.state] = counts.get(attempt.state, 0) + 1
            context = contexts.get(attempt.attempt_subject_sha256)
            if context is None:
                integrity_clean = False
                all_terminal = False
                issues.append(
                    DiagnosticAttemptReconciliationIssue(
                        code="MISSING_REPLAY_CONTEXT",
                        attempt_subject_sha256=attempt.attempt_subject_sha256,
                        detail="exact carrier replay context was not supplied",
                    )
                )
                continue
            try:
                replay = _load_stored_family(
                    attempt,
                    context,
                    self._store.list_events(tenant, attempt.attempt_subject_sha256),
                    self._profile,
                )
            except DiagnosticLifecycleError as exc:
                integrity_clean = False
                all_terminal = False
                issues.append(
                    DiagnosticAttemptReconciliationIssue(
                        code="LIFECYCLE_INTEGRITY_FAILURE",
                        attempt_subject_sha256=attempt.attempt_subject_sha256,
                        detail=str(exc),
                    )
                )
                continue
            event_count += len(replay.events)
            if replay.snapshot.state not in DIAGNOSTIC_TERMINAL_STATES:
                all_terminal = False
                issues.append(
                    DiagnosticAttemptReconciliationIssue(
                        code=(
                            "STRANDED_RUNNING"
                            if replay.snapshot.state == RUNNING
                            else "AUTHORIZED_NOT_TERMINAL"
                        ),
                        attempt_subject_sha256=attempt.attempt_subject_sha256,
                        detail=f"attempt remains {replay.snapshot.state}",
                    )
                )
        for extra in sorted(set(contexts) - subjects):
            integrity_clean = False
            all_terminal = False
            issues.append(
                DiagnosticAttemptReconciliationIssue(
                    code="UNREGISTERED_CONTEXT",
                    attempt_subject_sha256=str(extra),
                    detail="context has no retained attempt in this tenant",
                )
            )
        return DiagnosticAttemptReconciliation(
            tenant_id=tenant,
            attempt_count=len(attempts),
            event_count=event_count,
            state_counts=_frozen_mapping(counts),
            integrity_clean=integrity_clean,
            all_terminal=all_terminal,
            issues=tuple(issues),
            backend_durability_profile=self._profile,
            authority=_frozen_mapping(_AUTHORITY),
        )


__all__ = [
    "AUTHORIZED",
    "COMPLETED",
    "DIAGNOSTIC_ATTEMPT_EVENT_SCHEMA",
    "DIAGNOSTIC_ATTEMPT_LIFECYCLE_SCHEMA",
    "DIAGNOSTIC_ATTEMPT_STATES",
    "DIAGNOSTIC_ATTEMPT_SUBJECT_DOMAIN",
    "DIAGNOSTIC_TERMINAL_STATES",
    "EXPIRED",
    "FAILED",
    "INDETERMINATE",
    "REJECTED",
    "RUNNING",
    "DiagnosticAttemptEventReceipt",
    "DiagnosticAttemptIssuance",
    "DiagnosticAttemptLifecycle",
    "DiagnosticAttemptMutation",
    "DiagnosticAttemptReconciliation",
    "DiagnosticAttemptReconciliationIssue",
    "DiagnosticAttemptReplay",
    "DiagnosticAttemptSnapshot",
    "DiagnosticLifecycleConflict",
    "DiagnosticLifecycleError",
    "DiagnosticLifecycleExpired",
    "DiagnosticLifecycleIntegrityError",
    "DiagnosticLifecycleNotFound",
    "DiagnosticLifecyclePersistenceError",
    "DiagnosticLifecycleReplayContext",
    "DiagnosticSharedPlanReplayContext",
    "DiagnosticLifecycleStore",
    "DiagnosticLifecycleValidationError",
    "DiagnosticLifecycleVersionConflict",
    "InMemoryDiagnosticLifecycleStore",
    "SqliteDiagnosticLifecycleStore",
    "build_diagnostic_shared_plan_replay_context",
    "derive_diagnostic_attempt_subject_sha256",
]
