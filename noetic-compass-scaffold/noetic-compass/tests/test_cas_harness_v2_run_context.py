from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

import pytest


TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from api.services.cas_harness_v2_identity import (
    HarnessV2IdentityError,
    prospective_run_id,
    require_joint_run_identity,
)
from api.services.cas_harness_evidence_object_store import PACKET_INDEX_KIND
from api.services.cas_harness_v2_run_context import (
    HarnessV2RunContextStore,
    RUN_CONTEXT_NAMESPACE,
    RunContextConflict,
    RunContextPersistenceError,
    RunContextValidationError,
)
from api.services.production.state_substrate.sqlite_store import SqliteStateStore
from test_cas_harness_v2_worker_bridge import _VerifiedObjectBackend, _repository


NOW = datetime(2026, 8, 6, 16, 0, tzinfo=UTC)
JOB_ID = "fleet-job-context-001"
RUN_ID = prospective_run_id(JOB_ID)
RAW = b'{\r\n  "schema_version": "cas_harness_v2.route_authorization_request.v1"\n}\x20'


def _mapping() -> dict[str, object]:
    return {
        "fleet_id": "audit-context-001",
        "job_id": JOB_ID,
        "audit_id": "audit-context-001",
        "assigned_worker_id": "worker-context-001",
        "layer_start": 0,
        "layer_end": 1,
        "shard_id": "shard-context-001",
        "assigned_methods": ["activation-patching"],
        "expected_outputs": ["raw-outcomes"],
        "lease_model": {
            "model_id": "model-context-001",
            "model_revision": "a" * 40,
            "model_artifact_manifest_path": "/models/context/manifest.json",
            "model_artifact_manifest_sha256": "b" * 64,
            "execution_mode": "external_probe_command",
        },
    }


def _kwargs(*, raw: bytes = RAW, mapping: dict[str, object] | None = None) -> dict:
    return {
        "tenant_id": "tenant-context-001",
        "account_id": "account-context-001",
        "audit_id": "audit-context-001",
        "fleet_id": "audit-context-001",
        "worker_id": "worker-context-001",
        "job_id": JOB_ID,
        "run_id": RUN_ID,
        "subject_id": JOB_ID,
        "authorization_id": JOB_ID,
        "authorized_at": NOW,
        "expires_at": NOW + timedelta(hours=1),
        "exact_request_raw": raw,
        "execution_mapping": mapping or _mapping(),
    }


def _loader_kwargs() -> dict[str, str]:
    return {
        "tenant_id": "tenant-context-001",
        "account_id": "account-context-001",
        "audit_id": "audit-context-001",
        "fleet_id": "audit-context-001",
        "worker_id": "worker-context-001",
        "job_id": JOB_ID,
    }


def _system(tmp_path: Path):
    store = SqliteStateStore(tmp_path / "run-context.sqlite3")
    backend = _VerifiedObjectBackend()
    repository = _repository(store, backend, replica_id="run-context-a")
    return store, backend, repository, HarnessV2RunContextStore(repository)


def test_joint_identity_derivation_is_exact_and_shared() -> None:
    assert prospective_run_id(JOB_ID) == (
        "h2run_18d88f059fe65e60345b387caa1cbb7f87134f09fc30f27f90c6ee5d514b8f96"
    )
    require_joint_run_identity(
        job_id=JOB_ID,
        subject_id=JOB_ID,
        authorization_id=JOB_ID,
        run_id=RUN_ID,
    )
    with pytest.raises(HarnessV2IdentityError, match="exactly equal"):
        require_joint_run_identity(
            job_id=JOB_ID,
            subject_id="different-subject",
            authorization_id=JOB_ID,
            run_id=RUN_ID,
        )


def test_exact_context_is_retained_reverified_and_replayed(tmp_path: Path) -> None:
    store, backend, _repository_value, contexts = _system(tmp_path)
    first = contexts.retain(**_kwargs())
    replay = contexts.retain(**_kwargs())
    loaded = contexts.load(**_loader_kwargs())

    assert backend.put_count == 1
    assert replay == first == loaded
    assert loaded.exact_request_raw == RAW
    assert loaded.exact_request_byte_length == len(RAW)
    assert loaded.execution_mapping == _mapping()
    assert loaded.criteria_status == "OPEN"
    assert loaded.execution_authentication == "NOT_ESTABLISHED"
    assert loaded.trusted_time == "NOT_ESTABLISHED"
    assert loaded.license_status == "NOT LICENSED"
    assert loaded.disclosure_status == "HELD"
    assert loaded.wrapper_version_id == "bridge-version-1"
    rows = store.list("tenant-context-001", PACKET_INDEX_KIND)
    assert len(rows) == 1
    assert rows[0].payload["namespace"] == RUN_CONTEXT_NAMESPACE
    store.close()


def test_byte_or_execution_mapping_drift_is_an_immutable_conflict(
    tmp_path: Path,
) -> None:
    store, backend, _repository_value, contexts = _system(tmp_path)
    contexts.retain(**_kwargs())
    with pytest.raises(RunContextConflict, match="different exact route context"):
        contexts.retain(**_kwargs(raw=RAW + b"\n"))
    changed = deepcopy(_mapping())
    changed["layer_end"] = 2
    with pytest.raises(RunContextConflict, match="different exact route context"):
        contexts.retain(**_kwargs(mapping=changed))
    assert backend.put_count == 1
    store.close()


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    (
        ("subject_id", "other-subject", "exactly equal"),
        ("authorization_id", "other-authorization", "exactly equal"),
        ("run_id", "h2run_" + "0" * 64, "deterministic"),
        ("fleet_id", "other-fleet", "fleet_id must equal"),
        ("worker_id", "other-worker", "assigned_worker_id differs"),
    ),
)
def test_scope_and_identity_mismatch_fail_before_storage(
    tmp_path: Path, field: str, replacement: str, message: str
) -> None:
    store, backend, _repository_value, contexts = _system(tmp_path)
    values = _kwargs()
    values[field] = replacement
    with pytest.raises(RunContextValidationError, match=message):
        contexts.retain(**values)
    assert backend.put_count == 0
    store.close()


def test_tampered_wrapper_fails_exact_reload(tmp_path: Path) -> None:
    store, backend, _repository_value, contexts = _system(tmp_path)
    contexts.retain(**_kwargs())
    item = next(iter(backend._objects.values()))
    item["body"] = bytes(item["body"]).replace(
        b"worker-context-001", b"worker-context-999", 1
    )
    with pytest.raises(RunContextPersistenceError, match="could not be reloaded"):
        contexts.load(**_loader_kwargs())
    store.close()


def test_sqlite_reopen_preserves_context_without_promoting_authority(
    tmp_path: Path,
) -> None:
    database = tmp_path / "run-context-reopen.sqlite3"
    backend = _VerifiedObjectBackend()
    first_store = SqliteStateStore(database)
    first_repository = _repository(
        first_store, backend, replica_id="run-context-reopen-a"
    )
    first = HarnessV2RunContextStore(first_repository).retain(**_kwargs())
    first_store.close()

    second_store = SqliteStateStore(database)
    second_repository = _repository(
        second_store, backend, replica_id="run-context-reopen-b"
    )
    replayed = HarnessV2RunContextStore(second_repository).load(**_loader_kwargs())
    assert replayed.exact_request_sha256 == first.exact_request_sha256
    assert replayed.wrapper_version_id == first.wrapper_version_id
    assert replayed.trusted_time == "NOT_ESTABLISHED"
    assert replayed.execution_authentication == "NOT_ESTABLISHED"
    second_store.close()
