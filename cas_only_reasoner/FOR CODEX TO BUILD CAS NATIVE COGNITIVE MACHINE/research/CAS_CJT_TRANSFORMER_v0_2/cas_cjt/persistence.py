"""Crash-atomic SQLite persistence for Neural CJT state and traces."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Mapping

from .artifacts import ArtifactError, StoredArtifact
from .contracts import (
    ContractSchemaError,
    canonical_digest,
    canonical_json,
    validate_contract,
    verify_declared_digest,
)
from .repair import RepairError, repair_frame_from_dict, repair_outcome_from_dict
from .state import StateContractError, bias_from_dict
from .types import ContractTypeError
from .trace import (
    SealedTrace,
    seal_rejection_audit,
    verify_public_rejection_audit,
    verify_public_trace,
    verify_rejection_audit_chain,
    verify_trace,
    verify_trace_chain,
)


STORE_SCHEMA_VERSION = "cas.neural-cjt.sqlite-store/0.2"


class PersistenceError(RuntimeError):
    """The durable store rejected an operation or failed integrity checks."""


class StaleHeadError(PersistenceError):
    """A transaction was not bound to the currently active state."""


class IdempotencyConflict(PersistenceError):
    """One batch ID was reused with different request content."""


class InjectedFailure(PersistenceError):
    """A test-only failure interrupted an uncommitted transaction."""


def _payload_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        mapped = to_dict()
        if isinstance(mapped, Mapping):
            return dict(mapped)
    raise PersistenceError(f"{label} must be a mapping or expose to_dict()")


def _payload_json(value: Any, *, label: str) -> str:
    return canonical_json(_payload_mapping(value, label=label))


def _sha256_text(value: str) -> str:
    return sha256(value.encode("ascii")).hexdigest()


def _valid_digest(value: str | None, *, nullable: bool = False) -> bool:
    if value is None:
        return nullable
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _artifact_references(value: Any):
    if isinstance(value, Mapping):
        artifact_id = value.get("artifact_id")
        digest = value.get("sha256")
        if isinstance(artifact_id, str) and isinstance(digest, str):
            yield artifact_id, digest
        for item in value.values():
            yield from _artifact_references(item)
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _artifact_references(item)


def _valid_tick_sequence(events: Iterable[Mapping[str, Any]]) -> bool:
    expected = 1
    for event in events:
        tick = event.get("tick")
        if not isinstance(tick, int) or isinstance(tick, bool) or tick != expected:
            return False
        expected += 1
    return True


def _validated_receipt_payload(value: Any) -> dict[str, Any]:
    """Validate the full authoritative CommitReceipt wire contract."""

    payload = _payload_mapping(value, label="commit receipt")
    try:
        validate_contract(payload)
    except (ContractSchemaError, ContractTypeError) as error:
        raise PersistenceError("commit receipt schema validation failed") from error
    if not verify_declared_digest(payload, "receipt_digest"):
        raise PersistenceError("commit receipt digest is invalid")
    tick = payload.get("tick")
    if not isinstance(tick, int) or isinstance(tick, bool) or tick < 1:
        raise PersistenceError("commit receipt tick must be one-based")
    post_state_digest = payload.get("post_state_digest")
    if payload.get("persisted_snapshot_id") != (
        f"snapshot-{str(post_state_digest)[:24]}"
    ):
        raise PersistenceError("commit receipt snapshot alias is invalid")
    disposition = payload.get("disposition")
    rollback_id = payload.get("rollback_of_receipt_id")
    if (
        disposition not in {"COMMITTED", "ROLLED_BACK"}
        or payload.get("authorized") is not True
        or (disposition == "ROLLED_BACK") != (rollback_id is not None)
    ):
        raise PersistenceError("commit receipt authority/disposition is invalid")
    return payload


def _validated_state_biases(value: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild every retained Bias and enforce a network envelope's shared head."""

    is_network = value.get("contract_type") == "NETWORK_STATE_ENVELOPE"
    if is_network:
        expected_fields = {
            "contract_type",
            "schema_version",
            "state_version",
            "previous_state_digest",
            "model_id",
            "model_version",
            "model_digest",
            "model_artifact_ref",
            "biases",
            "state_digest",
        }
        nested = value.get("biases")
        model_artifact = value.get("model_artifact_ref")
        if (
            set(value) != expected_fields
            or value.get("schema_version")
            != "cas.neural-cjt.network-state-envelope/0.2"
            or not isinstance(nested, list)
            or len(nested) < 3
            or not isinstance(value.get("model_id"), str)
            or not value.get("model_id")
            or not isinstance(value.get("model_version"), int)
            or isinstance(value.get("model_version"), bool)
            or int(value["model_version"]) < 0
            or not _valid_digest(value.get("model_digest"))
            or not isinstance(model_artifact, Mapping)
            or model_artifact.get("sha256") != value.get("model_digest")
        ):
            raise PersistenceError("network state envelope is malformed")
        items = nested
    else:
        items = [value]

    rebuilt: list[Any] = []
    try:
        for item in items:
            if not isinstance(item, Mapping):
                raise PersistenceError("state contains a non-object Bias")
            bias = bias_from_dict(item)
            if bias.to_dict() != dict(item):
                raise PersistenceError("Bias wire fields are not exact")
            rebuilt.append(bias)
    except (KeyError, TypeError, ValueError, StateContractError) as error:
        raise PersistenceError("retained Bias state is malformed") from error

    identities = [(item.bias_id, item.cjt_id) for item in rebuilt]
    if (
        len({item.bias_id for item in rebuilt}) != len(rebuilt)
        or len({item.cjt_id for item in rebuilt}) != len(rebuilt)
        or (is_network and identities != sorted(identities))
    ):
        raise PersistenceError("state Bias identities are duplicate or noncanonical")
    if sum(len(item.rpm.open_repair_ids) for item in rebuilt) > 1:
        raise PersistenceError("v0.2 state retains multiple global OPEN repairs")

    if is_network:
        model_ref = dict(value["model_artifact_ref"])
        for bias in rebuilt:
            if (
                bias.theta.model_id != value.get("model_id")
                or bias.theta.model_version != value.get("model_version")
                or bias.theta.model_digest != value.get("model_digest")
                or model_ref not in [
                    artifact.to_dict() for artifact in bias.theta.parameter_artifacts
                ]
            ):
                raise PersistenceError(
                    "nested Bias is not bound to the network model head"
                )
    return {item.bias_id: item for item in rebuilt}


@dataclass(frozen=True, slots=True)
class ActiveHead:
    state_digest: str
    state_version: int
    trace_digest: str | None
    model_digest: str | None
    commit_receipt_id: str | None


@dataclass(frozen=True, slots=True)
class StoredDocument:
    record_id: str
    payload: Mapping[str, Any] | Any


@dataclass(frozen=True, slots=True)
class ModelVersionWrite:
    model_digest: str
    parent_model_digest: str | None
    artifact_id: str
    payload: Mapping[str, Any] | Any


@dataclass(frozen=True, slots=True)
class AtomicWriteSet:
    """Everything that becomes visible together in one SQLite COMMIT."""

    batch_id: str
    request_digest: str
    expected_state_digest: str
    expected_state_version: int
    expected_trace_digest: str | None
    expected_model_digest: str | None
    post_state_digest: str
    post_state_version: int
    post_state: Mapping[str, Any] | Any
    post_model_digest: str | None
    trace: SealedTrace
    receipt_id: str
    receipt: Mapping[str, Any] | Any
    transition_batch: StoredDocument | None = None
    causes: tuple[StoredDocument, ...] = ()
    candidate_effects: tuple[StoredDocument, ...] = ()
    verifier_receipts: tuple[StoredDocument, ...] = ()
    qualification_receipts: tuple[StoredDocument, ...] = ()
    state_intents: tuple[StoredDocument, ...] = ()
    model_intents: tuple[StoredDocument, ...] = ()
    memory_intents: tuple[StoredDocument, ...] = ()
    artifacts: tuple[StoredArtifact, ...] = ()
    published_effects: tuple[StoredDocument, ...] = ()
    memory_records: tuple[StoredDocument, ...] = ()
    repair_frames: tuple[StoredDocument, ...] = ()
    repair_outcomes: tuple[StoredDocument, ...] = ()
    model_version: ModelVersionWrite | None = None
    rollback_of_receipt_id: str | None = None


class SQLiteAtomicStore:
    """One durable, single-writer store with immutable history tables.

    SQLite supplies the disk transaction.  Application-level compare-and-swap
    on ``active_head`` prevents a stale snapshot from winning that transaction.
    """

    _FAULT_POINTS = frozenset(
        {
            "after_artifacts",
            "after_state",
            "after_trace",
            "after_receipt",
            "after_head_update",
            "before_commit",
        }
    )

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            str(self.path),
            timeout=30.0,
            isolation_level=None,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = FULL")
        self._connection.execute("PRAGMA busy_timeout = 30000")
        self._receipt_validation_cache: dict[str, tuple[tuple[Any, ...], str]] = {}
        self._create_schema()

    def __enter__(self) -> "SQLiteAtomicStore":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS store_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_id TEXT PRIMARY KEY,
                sha256 TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL,
                media_type TEXT NOT NULL,
                encoding TEXT NOT NULL,
                byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
                metadata_json TEXT NOT NULL,
                payload BLOB NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS state_versions (
                state_digest TEXT PRIMARY KEY,
                state_version INTEGER NOT NULL CHECK (state_version >= 0),
                parent_state_digest TEXT,
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS model_versions (
                model_digest TEXT PRIMARY KEY,
                parent_model_digest TEXT,
                artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS trace_events (
                sequence INTEGER PRIMARY KEY,
                trace_id TEXT NOT NULL UNIQUE,
                trace_digest TEXT NOT NULL UNIQUE,
                previous_trace_digest TEXT,
                pre_state_digest TEXT NOT NULL,
                post_state_digest TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                public_payload_sha256 TEXT NOT NULL,
                public_payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS commit_receipts (
                receipt_id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL UNIQUE,
                request_digest TEXT NOT NULL,
                pre_state_digest TEXT NOT NULL,
                post_state_digest TEXT NOT NULL,
                trace_digest TEXT NOT NULL REFERENCES trace_events(trace_digest),
                rollback_of_receipt_id TEXT,
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS published_effects (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS memory_records (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS repair_frames (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS repair_outcomes (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS transition_batches (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS causes (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS candidate_effects (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS verifier_receipts (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS qualification_receipts (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS state_intents (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS model_intents (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS memory_intents (
                record_id TEXT PRIMARY KEY,
                commit_receipt_id TEXT NOT NULL REFERENCES commit_receipts(receipt_id),
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS rejection_audits (
                sequence INTEGER PRIMARY KEY,
                audit_id TEXT NOT NULL UNIQUE,
                audit_digest TEXT NOT NULL UNIQUE,
                previous_audit_digest TEXT,
                batch_id TEXT NOT NULL UNIQUE,
                request_digest TEXT NOT NULL,
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                public_payload_sha256 TEXT NOT NULL,
                public_payload_json TEXT NOT NULL
            ) STRICT;

            CREATE TABLE IF NOT EXISTS active_head (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                state_digest TEXT NOT NULL REFERENCES state_versions(state_digest),
                state_version INTEGER NOT NULL CHECK (state_version >= 0),
                trace_digest TEXT,
                model_digest TEXT,
                commit_receipt_id TEXT
            ) STRICT;
            """
        )
        row = self._connection.execute(
            "SELECT value FROM store_metadata WHERE key = 'schema_version'"
        ).fetchone()
        if row is None:
            self._connection.execute(
                "INSERT INTO store_metadata(key, value) VALUES('schema_version', ?)",
                (STORE_SCHEMA_VERSION,),
            )
        elif row["value"] != STORE_SCHEMA_VERSION:
            raise PersistenceError("SQLite store schema version mismatch")
        for table in (
            "artifacts",
            "state_versions",
            "model_versions",
            "trace_events",
            "commit_receipts",
            "published_effects",
            "memory_records",
            "repair_frames",
            "repair_outcomes",
            "transition_batches",
            "causes",
            "candidate_effects",
            "verifier_receipts",
            "qualification_receipts",
            "state_intents",
            "model_intents",
            "memory_intents",
            "rejection_audits",
        ):
            self._connection.executescript(
                f"""
                CREATE TRIGGER IF NOT EXISTS {table}_immutable_update
                BEFORE UPDATE ON {table}
                BEGIN SELECT RAISE(ABORT, '{table} is immutable'); END;
                CREATE TRIGGER IF NOT EXISTS {table}_immutable_delete
                BEFORE DELETE ON {table}
                BEGIN SELECT RAISE(ABORT, '{table} is immutable'); END;
                """
            )

    @property
    def head(self) -> ActiveHead:
        row = self._connection.execute(
            "SELECT state_digest, state_version, trace_digest, model_digest, "
            "commit_receipt_id FROM active_head WHERE singleton = 1"
        ).fetchone()
        if row is None:
            raise PersistenceError("store has not been initialized")
        return ActiveHead(
            state_digest=row["state_digest"],
            state_version=row["state_version"],
            trace_digest=row["trace_digest"],
            model_digest=row["model_digest"],
            commit_receipt_id=row["commit_receipt_id"],
        )

    def initialize(
        self,
        *,
        state_digest: str,
        state_version: int,
        state_payload: Mapping[str, Any] | Any,
        model_digest: str | None = None,
        initial_artifacts: tuple[StoredArtifact, ...] = (),
        initial_model_version: ModelVersionWrite | None = None,
    ) -> ActiveHead:
        if not _valid_digest(state_digest):
            raise PersistenceError("initial state_digest must be lowercase SHA-256")
        if not isinstance(state_version, int) or isinstance(state_version, bool) or state_version < 0:
            raise PersistenceError("initial state_version must be a nonnegative integer")
        if initial_model_version is not None:
            if model_digest is None:
                model_digest = initial_model_version.model_digest
            elif model_digest != initial_model_version.model_digest:
                raise PersistenceError("initial model version does not match model_digest")
            if initial_model_version.parent_model_digest is not None:
                raise PersistenceError("the initial model version cannot have a parent")
        if model_digest is not None and not _valid_digest(model_digest):
            raise PersistenceError("initial model_digest must be lowercase SHA-256 or null")
        if model_digest is not None and initial_model_version is None:
            raise PersistenceError(
                "initial_model_version is required when model_digest is supplied"
            )
        payload_json = _payload_json(state_payload, label="initial state")
        payload_sha = _sha256_text(payload_json)
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            existing = self._connection.execute(
                "SELECT state_digest, state_version, trace_digest, model_digest, "
                "commit_receipt_id FROM active_head WHERE singleton = 1"
            ).fetchone()
            if existing is not None:
                existing_head = ActiveHead(
                    existing["state_digest"],
                    existing["state_version"],
                    existing["trace_digest"],
                    existing["model_digest"],
                    existing["commit_receipt_id"],
                )
                if existing_head != ActiveHead(
                    state_digest, state_version, None, model_digest, None
                ):
                    raise PersistenceError("store is already initialized with a different head")
                row = self._connection.execute(
                    "SELECT payload_sha256 FROM state_versions WHERE state_digest = ?",
                    (state_digest,),
                ).fetchone()
                if row is None or not hmac.compare_digest(row["payload_sha256"], payload_sha):
                    raise PersistenceError("existing initial state payload differs")
                if initial_model_version is not None:
                    model_row = self._connection.execute(
                        "SELECT artifact_id, parent_model_digest FROM model_versions "
                        "WHERE model_digest = ?",
                        (initial_model_version.model_digest,),
                    ).fetchone()
                    if model_row is None or (
                        model_row["artifact_id"] != initial_model_version.artifact_id
                        or model_row["parent_model_digest"] is not None
                    ):
                        raise PersistenceError("existing initial model version differs")
                self._connection.execute("COMMIT")
                return existing_head
            for artifact in initial_artifacts:
                self._put_artifact(artifact)
            self._assert_artifact_references((state_payload,))
            if initial_model_version is not None:
                self._put_model_version(initial_model_version)
            self._connection.execute(
                "INSERT INTO state_versions(state_digest, state_version, parent_state_digest, "
                "payload_sha256, payload_json) VALUES(?, ?, NULL, ?, ?)",
                (state_digest, state_version, payload_sha, payload_json),
            )
            self._connection.execute(
                "INSERT INTO active_head(singleton, state_digest, state_version, trace_digest, "
                "model_digest, commit_receipt_id) VALUES(1, ?, ?, NULL, ?, NULL)",
                (state_digest, state_version, model_digest),
            )
            self._connection.execute("COMMIT")
        except BaseException:
            if self._connection.in_transaction:
                self._connection.execute("ROLLBACK")
            raise
        return self.head

    def batch_record(self, batch_id: str) -> tuple[str, dict[str, Any]] | None:
        """Return the immutable request digest and receipt for an idempotency check."""

        row = self._connection.execute(
            "SELECT receipt_id, request_digest FROM commit_receipts WHERE batch_id = ?",
            (batch_id,),
        ).fetchone()
        if row is None:
            return None
        return row["request_digest"], self.receipt_by_id(str(row["receipt_id"]))

    def receipt_by_id(self, receipt_id: str) -> dict[str, Any]:
        row = self._connection.execute(
            "SELECT receipt_id, batch_id, request_digest, pre_state_digest, "
            "post_state_digest, trace_digest, rollback_of_receipt_id, "
            "payload_sha256, payload_json FROM commit_receipts WHERE receipt_id = ?",
            (receipt_id,),
        ).fetchone()
        if row is None or not hmac.compare_digest(
            row["payload_sha256"], _sha256_text(row["payload_json"])
        ):
            raise PersistenceError("commit receipt was not found or is corrupt")
        trace_row = self._connection.execute(
            "SELECT trace_id, trace_digest, pre_state_digest, post_state_digest, "
            "payload_sha256, payload_json FROM trace_events "
            "WHERE trace_digest = ?",
            (row["trace_digest"],),
        ).fetchone()
        if trace_row is None or not hmac.compare_digest(
            trace_row["payload_sha256"], _sha256_text(trace_row["payload_json"])
        ):
            raise PersistenceError("commit receipt trace is missing or corrupt")
        signature = (
            row["batch_id"],
            row["request_digest"],
            row["pre_state_digest"],
            row["post_state_digest"],
            row["trace_digest"],
            row["rollback_of_receipt_id"],
            row["payload_sha256"],
            trace_row["trace_id"],
            trace_row["trace_digest"],
            trace_row["pre_state_digest"],
            trace_row["post_state_digest"],
            trace_row["payload_sha256"],
        )
        cached = self._receipt_validation_cache.get(receipt_id)
        if cached == (signature, row["payload_json"]):
            return json.loads(row["payload_json"])
        payload = _validated_receipt_payload(json.loads(row["payload_json"]))
        trace = json.loads(trace_row["payload_json"])
        try:
            validate_contract(trace)
        except (ContractSchemaError, ContractTypeError) as error:
            raise PersistenceError("commit receipt trace schema is invalid") from error
        if (
            not verify_trace(trace)
            or payload.get("receipt_id") != row["receipt_id"]
            or payload.get("batch_id") != row["batch_id"]
            or payload.get("receipt_id")
            != f"commit-{str(row['request_digest'])[:24]}"
            or payload.get("pre_state_digest") != row["pre_state_digest"]
            or payload.get("post_state_digest") != row["post_state_digest"]
            or payload.get("rollback_of_receipt_id")
            != row["rollback_of_receipt_id"]
            or payload.get("trace_id") != trace_row["trace_id"]
            or trace.get("trace_id") != trace_row["trace_id"]
            or trace.get("trace_digest") != trace_row["trace_digest"]
            or trace_row["trace_digest"] != row["trace_digest"]
            or trace.get("commit_receipt_id") != row["receipt_id"]
            or payload.get("tick") != trace.get("tick")
            or payload.get("pre_state_digest") != trace.get("pre_state_digest")
            or payload.get("post_state_digest") != trace.get("post_state_digest")
            or payload.get("pre_model_digest") != trace.get("pre_model_digest")
            or payload.get("post_model_digest") != trace.get("post_model_digest")
        ):
            raise PersistenceError("commit receipt row/trace binding is invalid")
        rollback_id = row["rollback_of_receipt_id"]
        if rollback_id is not None:
            original = self._connection.execute(
                "SELECT payload_sha256, payload_json FROM commit_receipts "
                "WHERE receipt_id = ?",
                (rollback_id,),
            ).fetchone()
            if original is None or not hmac.compare_digest(
                original["payload_sha256"], _sha256_text(original["payload_json"])
            ):
                raise PersistenceError("rollback target receipt is missing or corrupt")
            original_payload = _validated_receipt_payload(
                json.loads(original["payload_json"])
            )
            if int(original_payload["tick"]) >= int(payload["tick"]):
                raise PersistenceError("rollback target receipt is not earlier")
        self._receipt_validation_cache[receipt_id] = (signature, row["payload_json"])
        return payload

    def has_artifact(self, artifact_id: str, sha256_digest: str | None = None) -> bool:
        row = self._connection.execute(
            "SELECT sha256 FROM artifacts WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        return row is not None and (
            sha256_digest is None or hmac.compare_digest(row["sha256"], sha256_digest)
        )

    def state_record(self, state_digest: str) -> tuple[int, str | None, dict[str, Any]]:
        row = self._connection.execute(
            "SELECT state_version, parent_state_digest, payload_sha256, payload_json "
            "FROM state_versions WHERE state_digest = ?",
            (state_digest,),
        ).fetchone()
        if row is None or not hmac.compare_digest(
            row["payload_sha256"], _sha256_text(row["payload_json"])
        ):
            raise PersistenceError("state version was not found or is corrupt")
        payload = json.loads(row["payload_json"])
        parent_field = (
            "previous_state_digest"
            if "previous_state_digest" in payload
            else "previous_digest"
        )
        if payload.get(parent_field) != row["parent_state_digest"]:
            raise PersistenceError("state parent row/payload binding is invalid")
        _validated_state_biases(payload)
        return (int(row["state_version"]), row["parent_state_digest"], payload)

    def model_version_record(self, model_digest: str) -> dict[str, Any]:
        """Load one immutable model manifest and verify its row bindings."""

        row = self._connection.execute(
            "SELECT parent_model_digest, artifact_id, payload_sha256, payload_json "
            "FROM model_versions WHERE model_digest = ?",
            (model_digest,),
        ).fetchone()
        if row is None or not hmac.compare_digest(
            row["payload_sha256"], _sha256_text(row["payload_json"])
        ):
            raise PersistenceError("model version was not found or is corrupt")
        payload = json.loads(row["payload_json"])
        if (
            payload.get("model_digest") != model_digest
            or payload.get("parent_model_digest") != row["parent_model_digest"]
            or payload.get("model_artifact_ref", {}).get("artifact_id")
            != row["artifact_id"]
            or not self.has_artifact(row["artifact_id"], model_digest)
        ):
            raise PersistenceError("model manifest does not bind its durable row")
        model_version = payload.get("model_version")
        if (
            not isinstance(model_version, int)
            or isinstance(model_version, bool)
            or model_version < 0
        ):
            raise PersistenceError("model manifest version is invalid")
        parent_digest = row["parent_model_digest"]
        if parent_digest is not None:
            parent_row = self._connection.execute(
                "SELECT payload_sha256, payload_json FROM model_versions "
                "WHERE model_digest = ?",
                (parent_digest,),
            ).fetchone()
            if parent_row is None or not hmac.compare_digest(
                parent_row["payload_sha256"],
                _sha256_text(parent_row["payload_json"]),
            ):
                raise PersistenceError("model lineage parent is missing or corrupt")
            parent_payload = json.loads(parent_row["payload_json"])
            parent_version = parent_payload.get("model_version")
            if (
                parent_payload.get("model_digest") != parent_digest
                or not isinstance(parent_version, int)
                or isinstance(parent_version, bool)
                or model_version != parent_version + 1
            ):
                raise PersistenceError("model versions are not contiguous")
        return payload

    def _validate_state_lineage(self, descendant_digest: str) -> None:
        """Validate the complete state row/payload and nested Bias chain."""

        seen: set[str] = set()
        child_payload: dict[str, Any] | None = None
        child_version: int | None = None
        child_digest: str | None = None
        current: str | None = descendant_digest

        def biases(value: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
            nested = value.get("biases")
            items = nested if isinstance(nested, list) else [value]
            result = {
                str(item.get("bias_id")): item
                for item in items
                if isinstance(item, Mapping) and isinstance(item.get("bias_id"), str)
            }
            if len(result) != len(items):
                raise PersistenceError("state contains duplicate or invalid Bias identities")
            return result

        def history(
            value: Mapping[str, Any], field: str, *, label: str
        ) -> list[str]:
            items = value.get(field, [])
            if (
                not isinstance(items, list)
                or len(items) > 16
                or any(not isinstance(item, str) or not item for item in items)
                or len(set(items)) != len(items)
            ):
                raise PersistenceError(f"{label} is not a valid bounded history")
            return list(items)

        def appended(
            before: list[str], after: list[str], *, maximum_new: int | None
        ) -> list[str]:
            additions = [item for item in after if item not in before]
            if maximum_new is not None and len(additions) > maximum_new:
                raise PersistenceError("Bias history added too many records in one revision")
            expected = list(before)
            for item in additions:
                if item not in expected:
                    expected.append(item)
            if after != expected[-16:]:
                raise PersistenceError("Bias bounded history is not a predecessor append")
            return additions

        def validate_bias_history_successor(
            parent: Mapping[str, Any], child: Mapping[str, Any]
        ) -> None:
            parent_memory = parent.get("memory")
            child_memory = child.get("memory")
            parent_rpm = parent.get("rpm")
            child_rpm = child.get("rpm")
            if not all(
                isinstance(item, Mapping)
                for item in (parent_memory, child_memory, parent_rpm, child_rpm)
            ):
                raise PersistenceError("Bias state lacks typed memory/RPM records")

            triple_fields = (
                "recent_cause_ids",
                "recent_candidate_effect_ids",
                "verifier_receipt_ids",
            )
            triple_additions = [
                appended(
                    history(parent_memory, field, label=field),
                    history(child_memory, field, label=field),
                    maximum_new=1,
                )
                for field in triple_fields
            ]
            if len({len(items) for items in triple_additions}) != 1:
                raise PersistenceError(
                    "Bias accepted-memory histories do not advance as one triple"
                )

            for field in ("retrieved_memory_refs", "provenance_refs"):
                appended(
                    history(parent_memory, field, label=field),
                    history(child_memory, field, label=field),
                    maximum_new=None,
                )

            parent_open = history(
                parent_rpm, "open_repair_ids", label="RPM open repairs"
            )
            child_open = history(
                child_rpm, "open_repair_ids", label="RPM open repairs"
            )
            parent_closed = history(
                parent_rpm, "repair_history", label="RPM repair history"
            )
            child_closed = history(
                child_rpm, "repair_history", label="RPM repair history"
            )
            if len(parent_open) > 1 or len(child_open) > 1:
                raise PersistenceError("v0.2 state retains multiple OPEN repairs")
            opened = [item for item in child_open if item not in parent_open]
            closed = [item for item in parent_open if item not in child_open]
            if len(opened) + len(closed) > 1:
                raise PersistenceError("Bias revision performs multiple repair transitions")
            expected_open = [
                item for item in parent_open if item not in closed
            ]
            expected_open.extend(opened)
            if child_open != expected_open:
                raise PersistenceError("Bias OPEN repair state is not a predecessor transition")
            expected_closed = list(parent_closed)
            for repair_id in closed:
                if repair_id not in expected_closed:
                    expected_closed.append(repair_id)
            if child_closed != expected_closed[-16:]:
                raise PersistenceError("Bias repair history is not a predecessor transition")

            parent_memory_repairs = history(
                parent_memory, "repair_frame_ids", label="memory repair frames"
            )
            child_memory_repairs = history(
                child_memory, "repair_frame_ids", label="memory repair frames"
            )
            expected_memory_repairs = list(parent_memory_repairs)
            for repair_id in opened:
                if repair_id not in expected_memory_repairs:
                    expected_memory_repairs.append(repair_id)
            if child_memory_repairs != expected_memory_repairs[-16:]:
                raise PersistenceError(
                    "Bias repair memory is not the bounded predecessor append"
                )

        def is_valid_rollback_successor(
            *,
            state_digest: str,
            predecessor_digest: str,
            state_payload: Mapping[str, Any],
        ) -> bool:
            rows = self._connection.execute(
                "SELECT cr.receipt_id FROM trace_events te "
                "JOIN commit_receipts cr ON cr.trace_digest = te.trace_digest "
                "WHERE te.post_state_digest = ?",
                (state_digest,),
            ).fetchall()
            if len(rows) != 1:
                return False
            receipt = self.receipt_by_id(str(rows[0]["receipt_id"]))
            if receipt.get("disposition") != "ROLLED_BACK":
                return False
            rollback_id = receipt.get("rollback_of_receipt_id")
            if not isinstance(rollback_id, str):
                raise PersistenceError("rollback successor lacks its target receipt")
            original = self.receipt_by_id(rollback_id)
            target = self.load_state(str(original["pre_state_digest"]))

            def semantic(value: Mapping[str, Any]) -> dict[str, Any]:
                normalized = dict(value)
                for field in (
                    "state_digest",
                    "version",
                    "state_version",
                    "previous_digest",
                    "previous_state_digest",
                ):
                    normalized.pop(field, None)
                return normalized

            if (
                receipt.get("pre_state_digest") != predecessor_digest
                or receipt.get("post_state_digest") != state_digest
                or receipt.get("post_model_digest")
                != original.get("pre_model_digest")
                or semantic(state_payload) != semantic(target)
            ):
                raise PersistenceError("rollback successor does not restore its exact target")
            return True

        while current is not None:
            if current in seen:
                raise PersistenceError("state lineage contains a cycle")
            seen.add(current)
            version, parent_digest, payload = self.state_record(current)
            payload_version = payload.get(
                "state_version", payload.get("version")
            )
            if (
                payload.get("state_digest") != current
                or payload_version != version
                or not verify_declared_digest(payload, "state_digest")
            ):
                raise PersistenceError("state row/payload identity is invalid")
            if child_payload is not None:
                if child_version != version + 1:
                    raise PersistenceError("state versions are not contiguous")
                parent_biases = biases(payload)
                child_biases = biases(child_payload)
                if set(parent_biases) != set(child_biases):
                    raise PersistenceError("state lineage changes the Bias identity set")
                for bias_id, child_bias in child_biases.items():
                    parent_bias = parent_biases[bias_id]
                    if child_bias == parent_bias:
                        continue
                    if (
                        child_bias.get("cjt_id") != parent_bias.get("cjt_id")
                        or child_bias.get("version")
                        != int(parent_bias.get("version", -1)) + 1
                        or child_bias.get("previous_digest")
                        != parent_bias.get("state_digest")
                        or child_bias.get("stable") != parent_bias.get("stable")
                        or child_bias.get("governance")
                        != parent_bias.get("governance")
                    ):
                        raise PersistenceError(
                            "nested Bias predecessor binding is invalid"
                        )
                    if child_digest is None:
                        raise PersistenceError("state lineage lost its child identity")
                    if not is_valid_rollback_successor(
                        state_digest=child_digest,
                        predecessor_digest=current,
                        state_payload=child_payload,
                    ):
                        validate_bias_history_successor(parent_bias, child_bias)
            elif parent_digest is not None:
                # The first selected node is checked against its parent on the
                # next loop iteration.
                pass
            if parent_digest is None and version != 0:
                raise PersistenceError("non-genesis state lacks a parent")
            if parent_digest is None:
                for bias in biases(payload).values():
                    memory = bias.get("memory", {})
                    rpm = bias.get("rpm", {})
                    for field in (
                        "recent_cause_ids",
                        "recent_candidate_effect_ids",
                        "verifier_receipt_ids",
                        "repair_frame_ids",
                        "retrieved_memory_refs",
                    ):
                        if history(memory, field, label=field):
                            raise PersistenceError(
                                "genesis Bias contains non-genesis evidence history"
                            )
                    for field in ("open_repair_ids", "repair_history"):
                        if history(rpm, field, label=field):
                            raise PersistenceError(
                                "genesis Bias contains non-genesis repair history"
                            )
            child_payload = payload
            child_version = version
            child_digest = current
            current = parent_digest

    def is_state_ancestor(self, ancestor_digest: str, descendant_digest: str) -> bool:
        """Return true only when the retained parent chain reaches ancestor_digest."""

        seen: set[str] = set()
        current: str | None = descendant_digest
        while current is not None:
            if current == ancestor_digest:
                return True
            if current in seen:
                raise PersistenceError("state ancestry contains a cycle")
            seen.add(current)
            row = self._connection.execute(
                "SELECT parent_state_digest FROM state_versions WHERE state_digest = ?",
                (current,),
            ).fetchone()
            if row is None:
                raise PersistenceError("state ancestry references a missing version")
            current = row["parent_state_digest"]
        return False

    def _fault(self, requested: str | None, location: str) -> None:
        if requested == location:
            raise InjectedFailure(f"fault injected at {location}")

    def _put_artifact(self, artifact: StoredArtifact) -> None:
        try:
            artifact.verify()
        except ArtifactError as exc:
            raise PersistenceError(str(exc)) from exc
        self._connection.execute(
            "INSERT OR IGNORE INTO artifacts(artifact_id, sha256, kind, media_type, "
            "encoding, byte_length, metadata_json, payload) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (
                artifact.artifact_id,
                artifact.sha256,
                artifact.kind,
                artifact.media_type,
                artifact.encoding,
                artifact.byte_length,
                artifact.metadata_json,
                sqlite3.Binary(artifact.payload),
            ),
        )
        row = self._connection.execute(
            "SELECT sha256, kind, media_type, encoding, byte_length, metadata_json, payload "
            "FROM artifacts WHERE artifact_id = ?",
            (artifact.artifact_id,),
        ).fetchone()
        if row is None or any(
            (
                row["sha256"] != artifact.sha256,
                row["kind"] != artifact.kind,
                row["media_type"] != artifact.media_type,
                row["encoding"] != artifact.encoding,
                row["byte_length"] != artifact.byte_length,
                row["metadata_json"] != artifact.metadata_json,
                bytes(row["payload"]) != artifact.payload,
            )
        ):
            raise PersistenceError("artifact identity collision or stored payload mismatch")

    def _put_state(self, write: AtomicWriteSet) -> None:
        state_json = _payload_json(write.post_state, label="post state")
        state_sha = _sha256_text(state_json)
        self._connection.execute(
            "INSERT OR IGNORE INTO state_versions(state_digest, state_version, "
            "parent_state_digest, payload_sha256, payload_json) VALUES(?, ?, ?, ?, ?)",
            (
                write.post_state_digest,
                write.post_state_version,
                write.expected_state_digest,
                state_sha,
                state_json,
            ),
        )
        row = self._connection.execute(
            "SELECT state_version, parent_state_digest, payload_sha256, payload_json "
            "FROM state_versions WHERE state_digest = ?",
            (write.post_state_digest,),
        ).fetchone()
        if row is None or (
            row["state_version"] != write.post_state_version
            or row["parent_state_digest"] != write.expected_state_digest
            or row["payload_sha256"] != state_sha
            or row["payload_json"] != state_json
        ):
            raise PersistenceError("state digest collision or immutable state mismatch")

    def _put_model_version(self, model: ModelVersionWrite) -> None:
        payload_json = _payload_json(model.payload, label="model version")
        payload_sha = _sha256_text(payload_json)
        self._connection.execute(
            "INSERT OR IGNORE INTO model_versions(model_digest, parent_model_digest, "
            "artifact_id, payload_sha256, payload_json) VALUES(?, ?, ?, ?, ?)",
            (
                model.model_digest,
                model.parent_model_digest,
                model.artifact_id,
                payload_sha,
                payload_json,
            ),
        )
        row = self._connection.execute(
            "SELECT parent_model_digest, artifact_id, payload_sha256, payload_json "
            "FROM model_versions WHERE model_digest = ?",
            (model.model_digest,),
        ).fetchone()
        if row is None or (
            row["parent_model_digest"] != model.parent_model_digest
            or row["artifact_id"] != model.artifact_id
            or row["payload_sha256"] != payload_sha
            or row["payload_json"] != payload_json
        ):
            raise PersistenceError("model digest collision or immutable model mismatch")

    def _assert_artifact_references(self, values: Iterable[Any]) -> None:
        for value in values:
            mapped = _payload_mapping(value, label="artifact-bearing payload")
            for artifact_id, digest in _artifact_references(mapped):
                row = self._connection.execute(
                    "SELECT sha256 FROM artifacts WHERE artifact_id = ?",
                    (artifact_id,),
                ).fetchone()
                if row is None or not hmac.compare_digest(row["sha256"], digest):
                    raise PersistenceError(
                        "authoritative payload references a missing or mismatched artifact"
                    )

    def _put_document(
        self,
        table: str,
        document: StoredDocument,
        receipt_id: str,
    ) -> None:
        if table not in {
            "published_effects",
            "memory_records",
            "repair_frames",
            "repair_outcomes",
            "transition_batches",
            "causes",
            "candidate_effects",
            "verifier_receipts",
            "qualification_receipts",
            "state_intents",
            "model_intents",
            "memory_intents",
        }:
            raise PersistenceError("unknown immutable document table")
        payload_json = _payload_json(document.payload, label=table)
        payload_sha = _sha256_text(payload_json)
        self._connection.execute(
            f"INSERT OR IGNORE INTO {table}(record_id, commit_receipt_id, payload_sha256, "
            "payload_json) VALUES(?, ?, ?, ?)",
            (document.record_id, receipt_id, payload_sha, payload_json),
        )
        row = self._connection.execute(
            f"SELECT commit_receipt_id, payload_sha256, payload_json FROM {table} "
            "WHERE record_id = ?",
            (document.record_id,),
        ).fetchone()
        if row is None or (
            row["commit_receipt_id"] != receipt_id
            or row["payload_sha256"] != payload_sha
            or row["payload_json"] != payload_json
        ):
            raise PersistenceError(f"{table} identity collision or immutable payload mismatch")

    def receipt_for_batch(self, batch_id: str) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT receipt_id FROM commit_receipts WHERE batch_id = ?", (batch_id,)
        ).fetchone()
        return None if row is None else self.receipt_by_id(str(row["receipt_id"]))

    def record_rejection(
        self,
        *,
        batch_id: str,
        request_digest: str,
        payload: Mapping[str, Any],
        sensitive_fields: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Append a non-authoritative rejection audit without moving active_head.

        This ledger is intentionally separate from the authoritative transition
        chain.  It records invalid/stale proposals while preserving the exact
        cognitive state, model, memory, Effect set, and active trace pointer.
        """

        if not isinstance(batch_id, str) or not batch_id or not _valid_digest(request_digest):
            raise PersistenceError("rejection audit identity is invalid")
        audit_payload = dict(payload)
        audit_payload["batch_id"] = batch_id
        audit_payload["request_digest"] = request_digest
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            committed = self._connection.execute(
                "SELECT request_digest FROM commit_receipts WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
            if committed is not None:
                raise IdempotencyConflict("a committed batch cannot also be rejected")
            existing = self._connection.execute(
                "SELECT request_digest, payload_json FROM rejection_audits WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
            if existing is not None:
                if not hmac.compare_digest(existing["request_digest"], request_digest):
                    raise IdempotencyConflict(
                        "rejected batch_id was reused for a different request"
                    )
                self._connection.execute("COMMIT")
                return json.loads(existing["payload_json"])
            previous_row = self._connection.execute(
                "SELECT audit_digest FROM rejection_audits ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous = None if previous_row is None else previous_row["audit_digest"]
            sealed = seal_rejection_audit(
                audit_payload,
                previous_audit_digest=previous,
                sensitive_fields=sensitive_fields,
            )
            sequence_row = self._connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM rejection_audits"
            ).fetchone()
            private_json = canonical_json(sealed.payload)
            public_json = canonical_json(sealed.public_payload)
            self._connection.execute(
                "INSERT INTO rejection_audits(sequence, audit_id, audit_digest, "
                "previous_audit_digest, batch_id, request_digest, payload_sha256, payload_json, "
                "public_payload_sha256, public_payload_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    int(sequence_row["next_sequence"]),
                    sealed.audit_id,
                    sealed.audit_digest,
                    previous,
                    batch_id,
                    request_digest,
                    _sha256_text(private_json),
                    private_json,
                    _sha256_text(public_json),
                    public_json,
                ),
            )
            self._connection.execute("COMMIT")
            return dict(sealed.payload)
        except BaseException:
            if self._connection.in_transaction:
                self._connection.execute("ROLLBACK")
            raise

    def rejection_audits(self, *, public: bool = False) -> tuple[dict[str, Any], ...]:
        column = "public_payload_json" if public else "payload_json"
        rows = self._connection.execute(
            f"SELECT {column} AS payload FROM rejection_audits ORDER BY sequence"
        ).fetchall()
        return tuple(json.loads(row["payload"]) for row in rows)

    def commit(self, write: AtomicWriteSet, *, fault_at: str | None = None) -> dict[str, Any]:
        """Install a complete write set or expose none of it."""

        try:
            validate_contract(write.trace.payload)
        except (ContractSchemaError, ContractTypeError) as error:
            raise PersistenceError("tick trace schema validation failed") from error
        if fault_at is not None and fault_at not in self._FAULT_POINTS:
            raise PersistenceError(f"unknown fault injection point: {fault_at}")
        for name, value in (
            ("request_digest", write.request_digest),
            ("expected_state_digest", write.expected_state_digest),
            ("post_state_digest", write.post_state_digest),
        ):
            if not _valid_digest(value):
                raise PersistenceError(f"{name} must be lowercase SHA-256")
        if not isinstance(write.expected_state_version, int) or isinstance(
            write.expected_state_version, bool
        ) or write.expected_state_version < 0:
            raise PersistenceError("expected_state_version must be nonnegative")
        if not isinstance(write.post_state_version, int) or isinstance(
            write.post_state_version, bool
        ) or write.post_state_version != write.expected_state_version + 1:
            raise PersistenceError("post_state_version must increment exactly once")
        for value, label in (
            (write.expected_trace_digest, "expected_trace_digest"),
            (write.expected_model_digest, "expected_model_digest"),
            (write.post_model_digest, "post_model_digest"),
        ):
            if value is not None and not _valid_digest(value):
                raise PersistenceError(f"{label} must be lowercase SHA-256 or null")
        if not verify_trace(write.trace.payload) or not verify_public_trace(
            write.trace.public_payload
        ):
            raise PersistenceError("write set contains an invalid trace")
        if (
            write.trace.public_payload.get("private_trace_id") != write.trace.trace_id
            or write.trace.public_payload.get("private_trace_digest") != write.trace.trace_digest
        ):
            raise PersistenceError("public trace is not bound to its private trace")
        if write.trace.previous_trace_digest != write.expected_trace_digest:
            raise PersistenceError("trace is not bound to the expected prior trace")
        if (
            write.trace.payload.get("pre_state_digest") != write.expected_state_digest
            or write.trace.payload.get("post_state_digest") != write.post_state_digest
        ):
            raise PersistenceError("trace state binding does not match the write set")

        receipt_payload = _validated_receipt_payload(write.receipt)
        receipt_json = canonical_json(receipt_payload)
        receipt_sha = _sha256_text(receipt_json)
        expected_intent_ids = {
            document.record_id
            for collection in (
                write.state_intents,
                write.model_intents,
                write.memory_intents,
            )
            for document in collection
        }
        if write.rollback_of_receipt_id is not None:
            expected_intent_ids.add(f"rollback:{write.rollback_of_receipt_id}")
        expected_receipt_fields = {
            "receipt_id": write.receipt_id,
            "tick": write.trace.payload.get("tick"),
            "batch_id": write.batch_id,
            "pre_state_digest": write.expected_state_digest,
            "post_state_digest": write.post_state_digest,
            "pre_model_digest": write.expected_model_digest,
            "post_model_digest": write.post_model_digest,
            "trace_id": write.trace.trace_id,
            "rollback_of_receipt_id": write.rollback_of_receipt_id,
            "persisted_snapshot_id": f"snapshot-{write.post_state_digest[:24]}",
        }
        if any(receipt_payload.get(key) != value for key, value in expected_receipt_fields.items()):
            raise PersistenceError("commit receipt binding does not match the write set")
        if (
            write.receipt_id != f"commit-{write.request_digest[:24]}"
            or set(receipt_payload.get("accepted_intent_ids", ()))
            != expected_intent_ids
            or set(receipt_payload.get("published_effect_ids", ()))
            != {document.record_id for document in write.published_effects}
            or set(receipt_payload.get("opened_repair_ids", ()))
            != {document.record_id for document in write.repair_frames}
        ):
            raise PersistenceError("commit receipt outputs do not match the write set")
        if write.trace.payload.get("commit_receipt_id") != write.receipt_id:
            raise PersistenceError("trace does not bind the commit receipt")
        if (
            write.trace.payload.get("pre_model_digest") != write.expected_model_digest
            or write.trace.payload.get("post_model_digest") != write.post_model_digest
        ):
            raise PersistenceError("trace model binding does not match the write set")
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            existing = self._connection.execute(
                "SELECT receipt_id, request_digest FROM commit_receipts WHERE batch_id = ?",
                (write.batch_id,),
            ).fetchone()
            if existing is not None:
                if not hmac.compare_digest(existing["request_digest"], write.request_digest):
                    raise IdempotencyConflict(
                        "batch_id was already used for a different request"
                    )
                retained_receipt = self.receipt_by_id(str(existing["receipt_id"]))
                self._connection.execute("COMMIT")
                return retained_receipt
            rejected = self._connection.execute(
                "SELECT request_digest FROM rejection_audits WHERE batch_id = ?",
                (write.batch_id,),
            ).fetchone()
            if rejected is not None:
                raise IdempotencyConflict(
                    "a rejected batch_id cannot later identify an authoritative commit"
                )

            head = self.head
            if head != ActiveHead(
                write.expected_state_digest,
                write.expected_state_version,
                write.expected_trace_digest,
                write.expected_model_digest,
                head.commit_receipt_id,
            ):
                raise StaleHeadError("write set is stale relative to the active head")
            latest_tick_row = self._connection.execute(
                "SELECT payload_json FROM trace_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            expected_tick = 1
            if latest_tick_row is not None:
                try:
                    latest_tick = json.loads(latest_tick_row["payload_json"])["tick"]
                except (KeyError, TypeError, json.JSONDecodeError) as error:
                    raise PersistenceError("latest durable trace tick is invalid") from error
                if not isinstance(latest_tick, int) or isinstance(latest_tick, bool):
                    raise PersistenceError("latest durable trace tick is invalid")
                expected_tick = latest_tick + 1
            if write.trace.payload.get("tick") != expected_tick:
                raise PersistenceError("commit tick is not one-based and contiguous")
            if write.rollback_of_receipt_id is not None:
                original_row = self._connection.execute(
                    "SELECT payload_sha256, payload_json FROM commit_receipts "
                    "WHERE receipt_id = ?",
                    (write.rollback_of_receipt_id,),
                ).fetchone()
                if original_row is None or not hmac.compare_digest(
                    original_row["payload_sha256"],
                    _sha256_text(original_row["payload_json"]),
                ):
                    raise PersistenceError("rollback target receipt is missing or corrupt")

            for artifact in write.artifacts:
                self._put_artifact(artifact)
            reference_values: list[Any] = [
                write.post_state,
                write.receipt,
                write.trace.payload,
                write.trace.public_payload,
            ]
            if write.model_version is not None:
                reference_values.append(write.model_version.payload)
            if write.transition_batch is not None:
                reference_values.append(write.transition_batch.payload)
            for collection in (
                write.causes,
                write.candidate_effects,
                write.verifier_receipts,
                write.qualification_receipts,
                write.state_intents,
                write.model_intents,
                write.memory_intents,
                write.published_effects,
                write.memory_records,
                write.repair_frames,
                write.repair_outcomes,
            ):
                reference_values.extend(document.payload for document in collection)
            self._assert_artifact_references(reference_values)
            self._fault(fault_at, "after_artifacts")

            if write.model_version is not None:
                if write.model_version.model_digest != write.post_model_digest:
                    raise PersistenceError("model version does not match post_model_digest")
                self._put_model_version(write.model_version)
            elif write.post_model_digest != write.expected_model_digest:
                # A rollback may point to an already retained model version.
                retained = self._connection.execute(
                    "SELECT 1 FROM model_versions WHERE model_digest = ?",
                    (write.post_model_digest,),
                ).fetchone()
                if retained is None:
                    raise PersistenceError("post model digest has no retained model version")

            self._put_state(write)
            self._fault(fault_at, "after_state")

            sequence_row = self._connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM trace_events"
            ).fetchone()
            sequence = int(sequence_row["next_sequence"])
            trace_json = canonical_json(write.trace.payload)
            public_json = canonical_json(write.trace.public_payload)
            self._connection.execute(
                "INSERT INTO trace_events(sequence, trace_id, trace_digest, previous_trace_digest, "
                "pre_state_digest, post_state_digest, payload_sha256, payload_json, "
                "public_payload_sha256, public_payload_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    sequence,
                    write.trace.trace_id,
                    write.trace.trace_digest,
                    write.trace.previous_trace_digest,
                    write.expected_state_digest,
                    write.post_state_digest,
                    _sha256_text(trace_json),
                    trace_json,
                    _sha256_text(public_json),
                    public_json,
                ),
            )
            self._fault(fault_at, "after_trace")

            self._connection.execute(
                "INSERT INTO commit_receipts(receipt_id, batch_id, request_digest, "
                "pre_state_digest, post_state_digest, trace_digest, rollback_of_receipt_id, "
                "payload_sha256, payload_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    write.receipt_id,
                    write.batch_id,
                    write.request_digest,
                    write.expected_state_digest,
                    write.post_state_digest,
                    write.trace.trace_digest,
                    write.rollback_of_receipt_id,
                    receipt_sha,
                    receipt_json,
                ),
            )
            if write.transition_batch is not None:
                self._put_document("transition_batches", write.transition_batch, write.receipt_id)
            for document in write.causes:
                self._put_document("causes", document, write.receipt_id)
            for document in write.candidate_effects:
                self._put_document("candidate_effects", document, write.receipt_id)
            for document in write.verifier_receipts:
                self._put_document("verifier_receipts", document, write.receipt_id)
            for document in write.qualification_receipts:
                self._put_document("qualification_receipts", document, write.receipt_id)
            for document in write.state_intents:
                self._put_document("state_intents", document, write.receipt_id)
            for document in write.model_intents:
                self._put_document("model_intents", document, write.receipt_id)
            for document in write.memory_intents:
                self._put_document("memory_intents", document, write.receipt_id)
            for document in write.published_effects:
                self._put_document("published_effects", document, write.receipt_id)
            for document in write.memory_records:
                self._put_document("memory_records", document, write.receipt_id)
            for document in write.repair_frames:
                self._put_document("repair_frames", document, write.receipt_id)
            for document in write.repair_outcomes:
                self._put_document("repair_outcomes", document, write.receipt_id)
            self._fault(fault_at, "after_receipt")

            cursor = self._connection.execute(
                "UPDATE active_head SET state_digest = ?, state_version = ?, trace_digest = ?, "
                "model_digest = ?, commit_receipt_id = ? WHERE singleton = 1 "
                "AND state_digest = ? AND state_version = ? "
                "AND trace_digest IS ? AND model_digest IS ?",
                (
                    write.post_state_digest,
                    write.post_state_version,
                    write.trace.trace_digest,
                    write.post_model_digest,
                    write.receipt_id,
                    write.expected_state_digest,
                    write.expected_state_version,
                    write.expected_trace_digest,
                    write.expected_model_digest,
                ),
            )
            if cursor.rowcount != 1:
                raise StaleHeadError("active-head compare-and-swap failed")
            self._fault(fault_at, "after_head_update")
            self._fault(fault_at, "before_commit")
            self._connection.execute("COMMIT")
        except BaseException:
            if self._connection.in_transaction:
                self._connection.execute("ROLLBACK")
            raise
        return json.loads(receipt_json)

    def load_state(self, state_digest: str | None = None) -> dict[str, Any]:
        selected = self.head.state_digest if state_digest is None else state_digest
        _, _, value = self.state_record(selected)
        return value

    def load_artifact(self, artifact_id: str) -> StoredArtifact:
        row = self._connection.execute(
            "SELECT artifact_id, sha256, kind, media_type, encoding, metadata_json, payload "
            "FROM artifacts WHERE artifact_id = ?",
            (artifact_id,),
        ).fetchone()
        if row is None:
            raise PersistenceError("artifact was not found")
        artifact = StoredArtifact(
            artifact_id=row["artifact_id"],
            sha256=row["sha256"],
            kind=row["kind"],
            media_type=row["media_type"],
            encoding=row["encoding"],
            metadata_json=row["metadata_json"],
            payload=bytes(row["payload"]),
        )
        try:
            artifact.verify()
        except ArtifactError as exc:
            raise PersistenceError(str(exc)) from exc
        return artifact

    def trace_events(self, *, public: bool = False) -> tuple[dict[str, Any], ...]:
        column = "public_payload_json" if public else "payload_json"
        rows = self._connection.execute(
            f"SELECT {column} AS payload FROM trace_events ORDER BY sequence"
        ).fetchall()
        return tuple(json.loads(row["payload"]) for row in rows)

    def immutable_document(self, table: str, record_id: str) -> dict[str, Any]:
        if table not in {
            "published_effects",
            "memory_records",
            "repair_frames",
            "repair_outcomes",
            "transition_batches",
            "causes",
            "candidate_effects",
            "verifier_receipts",
            "qualification_receipts",
            "state_intents",
            "model_intents",
            "memory_intents",
        }:
            raise PersistenceError("unknown immutable document table")
        row = self._connection.execute(
            f"SELECT payload_sha256, payload_json FROM {table} WHERE record_id = ?",
            (record_id,),
        ).fetchone()
        if row is None or row["payload_sha256"] != _sha256_text(row["payload_json"]):
            raise PersistenceError(f"{table} record missing or corrupt")
        return json.loads(row["payload_json"])

    def next_tick(self) -> int:
        """Return the only global logical tick a new commit may use."""

        row = self._connection.execute(
            "SELECT payload_json FROM trace_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return 1
        try:
            tick = json.loads(row["payload_json"])["tick"]
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise PersistenceError("latest trace does not declare a valid tick") from error
        if not isinstance(tick, int) or isinstance(tick, bool) or tick < 1:
            raise PersistenceError("latest trace does not declare a valid tick")
        return tick + 1

    def documents_for_receipt(
        self, table: str, receipt_id: str
    ) -> tuple[dict[str, Any], ...]:
        """Load one evidence class in stable record-ID order."""

        if table not in {
            "published_effects",
            "memory_records",
            "repair_frames",
            "repair_outcomes",
            "transition_batches",
            "causes",
            "candidate_effects",
            "verifier_receipts",
            "qualification_receipts",
            "state_intents",
            "model_intents",
            "memory_intents",
        }:
            raise PersistenceError("unknown immutable document table")
        rows = self._connection.execute(
            f"SELECT payload_sha256, payload_json FROM {table} "
            "WHERE commit_receipt_id = ? ORDER BY record_id",
            (receipt_id,),
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            if not hmac.compare_digest(
                row["payload_sha256"], _sha256_text(row["payload_json"])
            ):
                raise PersistenceError(f"{table} contains a corrupt record")
            result.append(json.loads(row["payload_json"]))
        return tuple(result)

    def reconstruct_transition(self, trace_id: str | None = None) -> dict[str, Any]:
        """Resolve data for inspection/audit or a separate replay implementation."""

        if trace_id is None:
            row = self._connection.execute(
                "SELECT payload_sha256, payload_json, trace_digest, pre_state_digest, post_state_digest "
                "FROM trace_events ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
        else:
            row = self._connection.execute(
                "SELECT payload_sha256, payload_json, trace_digest, pre_state_digest, post_state_digest "
                "FROM trace_events WHERE trace_id = ?",
                (trace_id,),
            ).fetchone()
        if row is None:
            raise PersistenceError("trace event was not found")
        if not hmac.compare_digest(
            row["payload_sha256"], _sha256_text(row["payload_json"])
        ):
            raise PersistenceError("trace event payload is corrupt")
        trace = json.loads(row["payload_json"])
        if (
            trace.get("trace_digest") != row["trace_digest"]
            or trace.get("pre_state_digest") != row["pre_state_digest"]
            or trace.get("post_state_digest") != row["post_state_digest"]
            or not verify_trace(trace)
        ):
            raise PersistenceError("trace event failed verification")
        try:
            validate_contract(trace)
        except (ContractSchemaError, ContractTypeError) as error:
            raise PersistenceError("trace event failed schema validation") from error
        all_traces = self.trace_events()
        if not _valid_tick_sequence(all_traces):
            raise PersistenceError("trace ticks are not one-based and contiguous")
        receipt_row = self._connection.execute(
            "SELECT receipt_id, request_digest, payload_sha256, payload_json FROM commit_receipts "
            "WHERE trace_digest = ?",
            (row["trace_digest"],),
        ).fetchone()
        if receipt_row is None or not hmac.compare_digest(
            receipt_row["payload_sha256"], _sha256_text(receipt_row["payload_json"])
        ):
            raise PersistenceError("trace commit receipt was not found or is corrupt")
        receipt_id = receipt_row["receipt_id"]
        evidence_tables = (
            "transition_batches",
            "causes",
            "candidate_effects",
            "verifier_receipts",
            "qualification_receipts",
            "state_intents",
            "model_intents",
            "memory_intents",
            "published_effects",
            "memory_records",
            "repair_frames",
            "repair_outcomes",
        )
        evidence = {
            table: list(self.documents_for_receipt(table, receipt_id))
            for table in evidence_tables
        }
        receipt_payload = self.receipt_by_id(str(receipt_id))

        identity_fields = {
            "transition_batches": "batch_id",
            "causes": "cause_id",
            "candidate_effects": "candidate_effect_id",
            "verifier_receipts": "receipt_id",
            "qualification_receipts": "qualification_receipt_id",
            "state_intents": "intent_id",
            "model_intents": "intent_id",
            "memory_intents": "intent_id",
            "published_effects": "published_effect_id",
            "memory_records": "memory_record_id",
            "repair_frames": "repair_id",
            "repair_outcomes": "outcome_id",
        }
        digest_fields = {
            "candidate_effects": "candidate_digest",
            "verifier_receipts": "receipt_digest",
            "qualification_receipts": "receipt_digest",
            "state_intents": "intent_digest",
            "model_intents": "intent_digest",
            "memory_intents": "intent_digest",
            "published_effects": "publication_digest",
            "memory_records": "record_digest",
            "repair_frames": "frame_digest",
            "repair_outcomes": "outcome_digest",
        }
        prior: dict[str, dict[str, dict[str, Any]]] = {
            name: {}
            for name in (
                "causes",
                "candidate_effects",
                "verifier_receipts",
                "qualification_receipts",
                "state_intents",
                "model_intents",
                "memory_intents",
                "published_effects",
                "memory_records",
                "repair_frames",
                "repair_outcomes",
                "model_versions",
                "commit_receipts",
                "traces",
            )
        }
        owner_cache: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
        resolving_origins: set[str] = set()
        resolved_origins: set[str] = set()

        def owner_evidence(
            source_receipt_id: str,
        ) -> tuple[dict[str, Any], dict[str, Any]]:
            cached = owner_cache.get(source_receipt_id)
            if cached is not None:
                return cached
            owner_receipt = self.receipt_by_id(source_receipt_id)
            owner_row = self._connection.execute(
                "SELECT payload_sha256, payload_json FROM trace_events "
                "WHERE trace_id = ?",
                (owner_receipt["trace_id"],),
            ).fetchone()
            if owner_row is None or not hmac.compare_digest(
                owner_row["payload_sha256"], _sha256_text(owner_row["payload_json"])
            ):
                raise PersistenceError("evidence owner trace is missing or corrupt")
            owner_trace = json.loads(owner_row["payload_json"])
            cached = (owner_receipt, owner_trace)
            owner_cache[source_receipt_id] = cached
            return cached

        def add_origin(source_receipt_id: str) -> None:
            if source_receipt_id == receipt_id:
                return
            if source_receipt_id in resolved_origins:
                return
            if source_receipt_id in resolving_origins:
                raise PersistenceError("rollback/dependency origin contains a cycle")
            resolving_origins.add(source_receipt_id)
            try:
                source_receipt = self.receipt_by_id(source_receipt_id)
                if source_receipt.get("receipt_id") != source_receipt_id:
                    raise PersistenceError("dependency commit receipt identity mismatch")
                source_trace_id = source_receipt.get("trace_id")
                source_row = self._connection.execute(
                    "SELECT trace_digest, payload_sha256, payload_json FROM trace_events "
                    "WHERE trace_id = ?",
                    (source_trace_id,),
                ).fetchone()
                if source_row is None or not hmac.compare_digest(
                    source_row["payload_sha256"],
                    _sha256_text(source_row["payload_json"]),
                ):
                    raise PersistenceError("dependency trace is missing or corrupt")
                source_trace = json.loads(source_row["payload_json"])
                try:
                    schema_valid = validate_contract(source_trace)
                except (ContractSchemaError, ContractTypeError) as error:
                    raise PersistenceError("dependency trace schema is invalid") from error
                if (
                    not verify_trace(source_trace)
                    or schema_valid.get("commit_receipt_id") != source_receipt_id
                    or source_receipt.get("trace_id") != source_trace.get("trace_id")
                    or source_row["trace_digest"] != source_trace.get("trace_digest")
                    or int(source_trace.get("tick", -1)) >= int(trace["tick"])
                ):
                    raise PersistenceError("dependency receipt/trace link is invalid")
                prior["commit_receipts"][source_receipt_id] = source_receipt
                prior["traces"][str(source_trace_id)] = source_trace
                rollback_parent = source_receipt.get("rollback_of_receipt_id")
                if rollback_parent is not None:
                    add_origin(str(rollback_parent))
                resolved_origins.add(source_receipt_id)
            finally:
                resolving_origins.discard(source_receipt_id)

        def add_document(table: str, record_id: str) -> dict[str, Any]:
            source_row = self._connection.execute(
                f"SELECT commit_receipt_id FROM {table} WHERE record_id = ?",
                (record_id,),
            ).fetchone()
            if source_row is None:
                raise PersistenceError(f"dependency {table} record was not found")
            payload = self.immutable_document(table, record_id)
            identity_field = identity_fields[table]
            if payload.get(identity_field) != record_id:
                raise PersistenceError(f"dependency {table} identity mismatch")
            digest_field = digest_fields.get(table)
            if digest_field is not None and not verify_declared_digest(
                payload, digest_field
            ):
                raise PersistenceError(f"dependency {table} digest mismatch")
            source_receipt_id = str(source_row["commit_receipt_id"])
            _, owner_trace = owner_evidence(source_receipt_id)
            tick_field = (
                "opened_tick"
                if table == "repair_frames"
                else (
                    "learning_tick"
                    if table == "qualification_receipts"
                    and "learning_tick" in payload
                    else "tick"
                )
            )
            if table != "memory_records" and tick_field in payload and (
                payload[tick_field] != owner_trace.get("tick")
            ):
                raise PersistenceError(
                    f"dependency {table} tick does not match its owning trace"
                )
            if source_receipt_id != receipt_id:
                prior[table][record_id] = payload
                add_origin(source_receipt_id)
            return payload

        resolving_causes: set[str] = set()
        resolved_causes: set[str] = set()
        resolving_candidates: set[str] = set()
        resolved_candidates: set[str] = set()
        resolving_effects: set[str] = set()
        resolved_effects: set[str] = set()

        def add_cause(cause_id: str) -> dict[str, Any]:
            if cause_id in resolving_causes:
                raise PersistenceError("dependency Cause ancestry contains a cycle")
            cause = add_document("causes", cause_id)
            if cause_id in resolved_causes:
                return cause
            resolving_causes.add(cause_id)
            try:
                try:
                    validate_contract(cause)
                except (ContractSchemaError, ContractTypeError) as error:
                    raise PersistenceError("dependency Cause schema is invalid") from error
                identity = {
                    "tick": cause.get("tick"),
                    "cause_kind": cause.get("cause_kind"),
                    "content": cause.get("content"),
                    "goal_context": cause.get("goal_context"),
                    "source": cause.get("source"),
                    "provenance": cause.get("provenance"),
                    "uncertainty_ppm": cause.get("uncertainty_ppm"),
                    "entity_bindings": cause.get("entity_bindings"),
                    "relation_bindings": cause.get("relation_bindings"),
                    "candidate_operation_ids": cause.get(
                        "candidate_operation_ids"
                    ),
                    "memory_refs": cause.get("memory_refs"),
                    "content_ref": cause.get("content_ref"),
                    "parent_effect_id": cause.get("parent_effect_id"),
                    "originating_cjt_id": cause.get("originating_cjt_id"),
                    "originating_modality": cause.get("originating_modality"),
                }
                if (
                    cause.get("cause_id")
                    != f"cause-{canonical_digest(identity)[:24]}"
                    or cause.get("time_label")
                    != f"logical-tick:{cause.get('tick')}"
                ):
                    raise PersistenceError("dependency Cause identity is invalid")
                parent_effect_id = cause.get("parent_effect_id")
                if parent_effect_id is not None:
                    if not isinstance(parent_effect_id, str) or not parent_effect_id:
                        raise PersistenceError("dependency Cause parent is invalid")
                    parent_effect = add_published(parent_effect_id)
                    if int(parent_effect.get("tick", -1)) >= int(cause["tick"]):
                        raise PersistenceError(
                            "dependency Cause parent Effect is not earlier"
                        )
                for memory_record_id in cause.get("memory_refs", []):
                    add_memory(str(memory_record_id))
                resolved_causes.add(cause_id)
                return cause
            finally:
                resolving_causes.discard(cause_id)

        def add_candidate(candidate_id: str) -> dict[str, Any]:
            if candidate_id in resolving_candidates:
                raise PersistenceError("dependency candidate ancestry contains a cycle")
            candidate = add_document("candidate_effects", candidate_id)
            if candidate_id in resolved_candidates:
                return candidate
            resolving_candidates.add(candidate_id)
            try:
                try:
                    validate_contract(candidate)
                except (ContractSchemaError, ContractTypeError) as error:
                    raise PersistenceError(
                        "dependency candidate schema is invalid"
                    ) from error
                parent_cause_id = candidate.get("parent_cause_id")
                if not isinstance(parent_cause_id, str) or not parent_cause_id:
                    raise PersistenceError("dependency candidate lacks a parent Cause")
                parent_cause = add_cause(parent_cause_id)
                identity = {
                    "tick": candidate.get("tick"),
                    "parent_cause_id": parent_cause_id,
                    "producer_cjt_id": candidate.get("producer_cjt_id"),
                    "operation_contract_digest": candidate.get(
                        "operation_contract_digest"
                    ),
                    "bias_digest": candidate.get("bias_digest"),
                    "model_digest": candidate.get("model_digest"),
                    "content": candidate.get("content"),
                    "content_ref": candidate.get("content_ref"),
                }
                if (
                    candidate.get("tick") != parent_cause.get("tick")
                    or candidate_id
                    != f"candidate-effect-{canonical_digest(identity)[:24]}"
                ):
                    raise PersistenceError(
                        "dependency candidate identity/Cause binding is invalid"
                    )
                source = self._connection.execute(
                    "SELECT commit_receipt_id FROM candidate_effects WHERE record_id = ?",
                    (candidate_id,),
                ).fetchone()
                if source is None:
                    raise PersistenceError("dependency candidate owner is missing")
                _, owner_trace = owner_evidence(str(source["commit_receipt_id"]))
                if "network_request_digest" in owner_trace:
                    observe = next(
                        (
                            phase
                            for phase in owner_trace.get("phases", [])
                            if isinstance(phase, Mapping)
                            and phase.get("phase") == "OBSERVE"
                        ),
                        None,
                    )
                    decoder = owner_trace.get("decoder_contract")
                    control_digest = (
                        None
                        if not isinstance(observe, Mapping)
                        else observe.get("diagnostics", {}).get(
                            "control_binding_digest"
                        )
                    )
                    decoder_digest = (
                        None
                        if not isinstance(decoder, Mapping)
                        else decoder.get("decoder_digest")
                    )
                    expected_provenance = [
                        f"cause:{parent_cause_id}",
                        f"bias:{candidate.get('bias_digest')}",
                        f"model:{candidate.get('model_digest')}",
                        f"decoder:{decoder_digest}",
                        f"control-binding:{control_digest}",
                    ]
                    if (
                        not isinstance(control_digest, str)
                        or not isinstance(decoder_digest, str)
                        or candidate.get("provenance") != expected_provenance
                        or candidate.get("uncertainty_ppm") != 0
                    ):
                        raise PersistenceError(
                            "dependency candidate provenance is invalid"
                        )
                resolved_candidates.add(candidate_id)
                return candidate
            finally:
                resolving_candidates.discard(candidate_id)

        def add_verifier(verifier_receipt_id: str) -> dict[str, Any]:
            verifier = add_document("verifier_receipts", verifier_receipt_id)
            try:
                validate_contract(verifier)
            except (ContractSchemaError, ContractTypeError) as error:
                raise PersistenceError("dependency verifier schema is invalid") from error
            candidate_id = verifier.get("candidate_effect_id")
            if not isinstance(candidate_id, str) or not candidate_id:
                raise PersistenceError("dependency verifier lacks a candidate")
            candidate = add_candidate(candidate_id)
            identity_digest = canonical_digest(
                {
                    "tick": verifier.get("tick"),
                    "verifier_id": verifier.get("verifier_id"),
                    "verifier_version": verifier.get("verifier_version"),
                    "verifier_digest": verifier.get("verifier_digest"),
                    "cause_id": verifier.get("cause_id"),
                    "candidate_effect_id": verifier.get("candidate_effect_id"),
                    "candidate_effect_digest": verifier.get(
                        "candidate_effect_digest"
                    ),
                    "bias_digest": verifier.get("bias_digest"),
                    "contract_digest": verifier.get(
                        "operation_contract_digest"
                    ),
                    "outcome": verifier.get("semantic_outcome"),
                    "disposition": verifier.get("disposition"),
                    "reason_codes": verifier.get("reason_codes"),
                    "evidence_refs": verifier.get("evidence_refs"),
                }
            )
            if (
                verifier.get("candidate_effect_digest")
                != candidate.get("candidate_digest")
                or verifier.get("cause_id") != candidate.get("parent_cause_id")
                or verifier.get("tick") != candidate.get("tick")
                or verifier.get("bias_id") != candidate.get("bias_id")
                or verifier.get("bias_version") != candidate.get("bias_version")
                or verifier.get("bias_digest") != candidate.get("bias_digest")
                or verifier.get("operation_contract_id")
                != candidate.get("operation_contract_id")
                or verifier.get("operation_contract_digest")
                != candidate.get("operation_contract_digest")
                or verifier.get("model_digest") != candidate.get("model_digest")
                or verifier.get("independent") is not True
                or verifier_receipt_id
                != f"verifier-receipt-{identity_digest}"
            ):
                raise PersistenceError("dependency verifier/candidate digest mismatch")
            return verifier

        def add_published(effect_id: str) -> dict[str, Any]:
            if effect_id in resolving_effects:
                raise PersistenceError("dependency Effect ancestry contains a cycle")
            source_row = self._connection.execute(
                "SELECT commit_receipt_id FROM published_effects WHERE record_id = ?",
                (effect_id,),
            ).fetchone()
            if source_row is None:
                raise PersistenceError("dependency published Effect was not found")
            effect = add_document("published_effects", effect_id)
            if effect_id in resolved_effects:
                return effect
            resolving_effects.add(effect_id)
            try:
                validate_contract(effect)
            except (ContractSchemaError, ContractTypeError) as error:
                resolving_effects.discard(effect_id)
                raise PersistenceError("dependency Effect schema is invalid") from error
            candidate_id = effect.get("candidate_effect_id")
            verifier_id = effect.get("verifier_receipt_id")
            if not isinstance(candidate_id, str) or not isinstance(verifier_id, str):
                raise PersistenceError("dependency Effect links are invalid")
            try:
                candidate = add_candidate(candidate_id)
                verifier = add_verifier(verifier_id)
                owner_receipt, _ = owner_evidence(
                    str(source_row["commit_receipt_id"])
                )
                identity_payload = dict(effect)
                identity_payload.pop("publication_digest", None)
                identity_payload["published_effect_id"] = "pending"
                expected_effect_id = f"effect-{canonical_digest(identity_payload)[:24]}"
                if (
                    verifier.get("candidate_effect_id") != candidate_id
                    or verifier.get("candidate_effect_digest")
                    != candidate.get("candidate_digest")
                    or effect.get("content") != candidate.get("content")
                    or effect.get("content_ref") != candidate.get("content_ref")
                    or effect.get("producer_cjt_id")
                    != candidate.get("producer_cjt_id")
                    or effect.get("tick") != candidate.get("tick")
                    or effect.get("verifier_receipt_id")
                    != verifier.get("receipt_id")
                    or effect.get("commit_receipt_id")
                    != str(source_row["commit_receipt_id"])
                    or effect.get("published_effect_id") != expected_effect_id
                    or effect.get("authoritative") is not True
                    or verifier.get("disposition") != "ACCEPT"
                    or verifier.get("semantic_outcome") != "INTENDED"
                    or verifier.get("repair_required") is not False
                    or owner_receipt.get("disposition") != "COMMITTED"
                    or effect_id
                    not in owner_receipt.get("published_effect_ids", [])
                ):
                    raise PersistenceError(
                        "dependency Effect evidence is inconsistent"
                    )
                resolved_effects.add(effect_id)
                return effect
            finally:
                resolving_effects.discard(effect_id)

        def add_memory(record_id: str) -> dict[str, Any]:
            record = add_document("memory_records", record_id)
            source_intent_id = record.get("source_intent_id")
            verifier_id = record.get("verifier_receipt_id")
            if not isinstance(source_intent_id, str) or not isinstance(verifier_id, str):
                raise PersistenceError("dependency memory links are invalid")
            intent = add_document("memory_intents", source_intent_id)
            try:
                validate_contract(intent)
            except (ContractSchemaError, ContractTypeError) as error:
                raise PersistenceError("dependency memory schema is invalid") from error
            verifier = add_verifier(verifier_id)
            record_owner = self._connection.execute(
                "SELECT commit_receipt_id FROM memory_records WHERE record_id = ?",
                (record_id,),
            ).fetchone()
            intent_owner = self._connection.execute(
                "SELECT commit_receipt_id FROM memory_intents WHERE record_id = ?",
                (source_intent_id,),
            ).fetchone()
            if record_owner is None or intent_owner is None:
                raise PersistenceError("dependency memory owner is missing")
            _, memory_owner_trace = owner_evidence(
                str(record_owner["commit_receipt_id"])
            )
            if (
                record_owner["commit_receipt_id"]
                != intent_owner["commit_receipt_id"]
                or record.get("schema_version")
                != "cas.neural-cjt.memory-record/0.2"
                or intent.get("tick") != memory_owner_trace.get("tick")
                or intent.get("memory_record_id") != record_id
                or intent.get("verifier_receipt_id") != verifier_id
                or record.get("memory_kind") != intent.get("memory_kind")
                or record.get("content") != intent.get("content")
                or record.get("content_ref") != intent.get("content_ref")
                or record.get("confidence_ppm") != intent.get("confidence_ppm")
                or record.get("provenance") != intent.get("provenance")
                or record.get("evidence_refs") != intent.get("evidence_refs")
                or record.get("evidence_refs") != verifier.get("evidence_refs")
            ):
                raise PersistenceError("dependency memory provenance is inconsistent")
            return record

        def add_repair_frame(repair_id: str) -> dict[str, Any]:
            frame = add_document("repair_frames", repair_id)
            try:
                validate_contract(frame)
                repair_frame_from_dict(frame)
            except (ContractSchemaError, ContractTypeError, RepairError, KeyError) as error:
                raise PersistenceError("repair frame contract is invalid") from error
            candidate = add_candidate(str(frame["rejected_candidate_effect_id"]))
            verifier = add_verifier(str(frame["verifier_receipt_id"]))
            parent = add_cause(str(frame["parent_cause_id"]))
            expected_cycle = canonical_digest(
                {
                    "parent_cause_id": parent.get("cause_id"),
                    "producer_cjt_id": candidate.get("producer_cjt_id"),
                    "operation_id": candidate.get("operation_id"),
                    "axis": frame.get("prerequisite_axis"),
                }
            )
            expected_repair_id = (
                "repair-"
                + canonical_digest(
                    {
                        "parent_cause_id": parent.get("cause_id"),
                        "candidate_effect_id": candidate.get(
                            "candidate_effect_id"
                        ),
                        "receipt_id": verifier.get("receipt_id"),
                        "axis": frame.get("prerequisite_axis"),
                        "eligible_tick": frame.get("eligible_tick"),
                        "cycle_key": expected_cycle,
                    }
                )[:24]
            )
            expected_return = (
                f"cjt:{candidate.get('producer_cjt_id')}:"
                f"cause:{parent.get('cause_id')}"
            )
            if (
                candidate.get("parent_cause_id") != parent.get("cause_id")
                or candidate.get("bias_id") != frame.get("suspended_bias_id")
                or candidate.get("bias_version")
                != frame.get("suspended_bias_version")
                or candidate.get("tick") != parent.get("tick")
                or verifier.get("candidate_effect_id")
                != candidate.get("candidate_effect_id")
                or verifier.get("candidate_effect_digest")
                != candidate.get("candidate_digest")
                or verifier.get("cause_id") != parent.get("cause_id")
                or verifier.get("bias_id") != candidate.get("bias_id")
                or verifier.get("bias_version") != candidate.get("bias_version")
                or verifier.get("bias_digest") != candidate.get("bias_digest")
                or verifier.get("tick") != parent.get("tick")
                or verifier.get("disposition") != "REPAIR"
                or verifier.get("repair_required") is not True
                or frame.get("opened_tick") != parent.get("tick")
                or frame.get("cycle_key") != expected_cycle
                or frame.get("repair_id") != expected_repair_id
                or repair_id != expected_repair_id
                or frame.get("return_address") != expected_return
            ):
                raise PersistenceError("repair frame evidence is inconsistent")
            return frame

        def emitted_subgoal_for_frame(frame: Mapping[str, Any]) -> dict[str, Any]:
            """Derive the opening output without importing future t+1 evidence."""

            candidate = add_candidate(str(frame["rejected_candidate_effect_id"]))
            verifier = add_verifier(str(frame["verifier_receipt_id"]))
            if (
                verifier.get("candidate_effect_id")
                != candidate.get("candidate_effect_id")
                or verifier.get("cause_id") != frame.get("parent_cause_id")
                or verifier.get("disposition") != "REPAIR"
                or verifier.get("repair_required") is not True
                or candidate.get("bias_id") != frame.get("suspended_bias_id")
            ):
                raise PersistenceError("repair subgoal evidence is inconsistent")
            body: dict[str, Any] = {
                "contract_type": "CAUSE",
                "schema_version": "cas.neural-cjt.cause/0.2",
                "cause_id": "pending",
                "tick": frame["eligible_tick"],
                "cause_kind": "RPM_SUBGOAL",
                "content": {
                    "repair_id": frame["repair_id"],
                    "blocked_axis": frame["prerequisite_axis"],
                    "parent_cause_id": frame["parent_cause_id"],
                    "rejected_candidate_effect_id": frame[
                        "rejected_candidate_effect_id"
                    ],
                    "reason_codes": verifier["reason_codes"],
                },
                "source": "prototype:rpm-controller",
                "provenance": [
                    f"verifier-receipt:{frame['verifier_receipt_id']}",
                    f"suspended-bias:{candidate['bias_digest']}",
                ],
                "time_label": f"logical-tick:{frame['eligible_tick']}",
                "uncertainty_ppm": 0,
                "goal_context": {
                    "kind": "PREREQUISITE_REPAIR",
                    "return_address": frame["return_address"],
                },
                "entity_bindings": [],
                "relation_bindings": [],
                "candidate_operation_ids": ["^6"],
                "memory_refs": [],
                "originating_cjt_id": candidate["producer_cjt_id"],
                "originating_modality": None,
                "parent_effect_id": None,
                "content_ref": candidate.get("content_ref"),
            }
            identity = {
                key: body[key]
                for key in (
                    "tick",
                    "cause_kind",
                    "content",
                    "goal_context",
                    "source",
                    "provenance",
                    "uncertainty_ppm",
                    "entity_bindings",
                    "relation_bindings",
                    "candidate_operation_ids",
                    "memory_refs",
                    "content_ref",
                    "parent_effect_id",
                    "originating_cjt_id",
                    "originating_modality",
                )
            }
            body["cause_id"] = f"cause-{canonical_digest(identity)[:24]}"
            if body["cause_id"] != frame.get("subgoal_cause_id"):
                raise PersistenceError("derived repair subgoal identity is invalid")
            try:
                validate_contract(body)
            except (ContractSchemaError, ContractTypeError) as error:
                raise PersistenceError("derived repair subgoal schema is invalid") from error
            future_row = self._connection.execute(
                "SELECT payload_sha256, payload_json FROM causes WHERE record_id = ?",
                (body["cause_id"],),
            ).fetchone()
            if future_row is not None:
                if (
                    not hmac.compare_digest(
                        future_row["payload_sha256"],
                        _sha256_text(future_row["payload_json"]),
                    )
                    or json.loads(future_row["payload_json"]) != body
                ):
                    raise PersistenceError("stored repair subgoal differs from opening output")
            return body

        rollback_origin = receipt_payload.get("rollback_of_receipt_id")
        if rollback_origin is not None:
            add_origin(str(rollback_origin))

        memory_read_records = [
            add_memory(str(record_id))
            for record_id in trace.get("memory_read_refs", [])
        ]
        pre_version, _, pre_state = self.state_record(str(row["pre_state_digest"]))
        post_version, post_parent, post_state = self.state_record(
            str(row["post_state_digest"])
        )
        if (
            not verify_declared_digest(pre_state, "state_digest")
            or not verify_declared_digest(post_state, "state_digest")
            or post_parent != row["pre_state_digest"]
            or post_version != pre_version + 1
        ):
            raise PersistenceError("transition state digest is invalid")
        self._validate_state_lineage(str(row["post_state_digest"]))
        if len(evidence["transition_batches"]) != 1:
            raise PersistenceError("transition must retain exactly one request batch")
        request_payload = evidence["transition_batches"][0]
        if (
            request_payload.get("batch_id") != receipt_payload.get("batch_id")
            or canonical_digest(request_payload) != receipt_row["request_digest"]
        ):
            raise PersistenceError("transition request digest/batch binding is invalid")
        # Validate the independently retained frame before comparing it with
        # redundant in-band request/trace copies.  This proves its own
        # content-derived identity and cycle key, not only copy equality.
        current_frames = [
            add_repair_frame(str(frame["repair_id"]))
            for frame in evidence["repair_frames"]
        ]
        durable_intent_ids = {
            str(item["intent_id"])
            for table in ("state_intents", "model_intents", "memory_intents")
            for item in evidence[table]
        }
        if rollback_origin is not None:
            durable_intent_ids.add(f"rollback:{rollback_origin}")
        memory_record_ids = {
            str(item["memory_record_id"]) for item in evidence["memory_records"]
        }
        memory_intent_record_ids = {
            str(item["memory_record_id"]) for item in evidence["memory_intents"]
        }
        if (
            {str(item["cause_id"]) for item in evidence["causes"]}
            != {str(trace["cause_id"])}
            or set(trace.get("candidate_effect_ids", []))
            != {
                str(item["candidate_effect_id"])
                for item in evidence["candidate_effects"]
            }
            or set(trace.get("verifier_receipt_ids", []))
            != {str(item["receipt_id"]) for item in evidence["verifier_receipts"]}
            or set(trace.get("published_effect_ids", []))
            != {
                str(item["published_effect_id"])
                for item in evidence["published_effects"]
            }
            or set(trace.get("memory_write_refs", [])) != memory_record_ids
            or memory_record_ids != memory_intent_record_ids
            or set(trace.get("accepted_intent_ids", [])) != durable_intent_ids
            or set(receipt_payload.get("accepted_intent_ids", []))
            != durable_intent_ids
            or set(receipt_payload.get("published_effect_ids", []))
            != set(trace.get("published_effect_ids", []))
            or set(receipt_payload.get("opened_repair_ids", []))
            != {str(item["repair_id"]) for item in evidence["repair_frames"]}
        ):
            raise PersistenceError("trace/receipt durable evidence sets are inexact")
        if "network_request_digest" in trace and (
            set(trace.get("repair_frame_ids", []))
            != {str(item["repair_id"]) for item in evidence["repair_frames"]}
            or set(trace.get("repair_outcome_ids", []))
            != {str(item["outcome_id"]) for item in evidence["repair_outcomes"]}
        ):
            raise PersistenceError("network repair evidence sets are inexact")
        if rollback_origin is not None:
            original_receipt = self.receipt_by_id(str(rollback_origin))
            target_state = self.load_state(
                str(original_receipt["pre_state_digest"])
            )
            normalized_target = dict(target_state)
            normalized_post = dict(post_state)
            for normalized in (normalized_target, normalized_post):
                for field in (
                    "state_digest",
                    "version",
                    "state_version",
                    "previous_digest",
                    "previous_state_digest",
                ):
                    normalized.pop(field, None)
            if (
                normalized_post != normalized_target
                or trace.get("post_model_digest")
                != original_receipt.get("pre_model_digest")
                or request_payload.get("rollback_of_receipt_id")
                != rollback_origin
            ):
                raise PersistenceError("rollback target restoration is inexact")

        def same_records(
            left: Any, right: Any, *, identity_field: str
        ) -> bool:
            if not isinstance(left, list) or not isinstance(right, list):
                return False
            try:
                left_map = {str(item[identity_field]): item for item in left}
                right_map = {str(item[identity_field]): item for item in right}
            except (KeyError, TypeError):
                return False
            return (
                len(left_map) == len(left)
                and len(right_map) == len(right)
                and canonical_json(left_map) == canonical_json(right_map)
            )

        if "network_request_digest" in trace:
            collection_bindings = (
                ("candidate_effects", "candidate_effect_id"),
                ("verifier_receipts", "receipt_id"),
                ("model_intents", "intent_id"),
                ("memory_intents", "intent_id"),
                ("repair_frames", "repair_id"),
                ("repair_outcomes", "outcome_id"),
                ("qualification_receipts", "qualification_receipt_id"),
            )
            expected_audit = None
            expected_state_intents = list(request_payload.get("state_intents", []))
            if request_payload.get("audit_only") is True:
                audit_body = {
                    "contract_type": "AUDIT_TRANSITION_INTENT",
                    "schema_version": "cas.neural-cjt.audit-transition-intent/0.2",
                    "intent_id": f"audit-transition-{receipt_row['request_digest'][:24]}",
                    "tick": request_payload.get("tick"),
                    "issuer_id": receipt_payload.get("coordinator_id"),
                    "authority_capability": "PROPOSE_STATE_UPDATE",
                    "expected_state_version": pre_version,
                    "expected_state_digest": row["pre_state_digest"],
                    "proposed_state_version": post_version,
                    "proposed_state_digest": row["post_state_digest"],
                    "reason_codes": request_payload.get("audit_reason_codes"),
                    "bias_and_model_bytes_unchanged": True,
                }
                expected_state_intents.append(
                    {**audit_body, "intent_digest": canonical_digest(audit_body)}
                )
                expected_audit = {
                    "contract_type": "AUDIT_TRANSITION_INTENT",
                    "schema_version": "cas.neural-cjt.audit-transition/0.2",
                    "audit_id": f"audit-{receipt_row['request_digest'][:24]}",
                    "reason_codes": request_payload.get("audit_reason_codes"),
                    "bias_and_model_bytes_unchanged": True,
                }
            if (
                trace.get("network_request_digest")
                != receipt_row["request_digest"]
                or trace.get("tick") != request_payload.get("tick")
                or trace.get("runtime_id") != request_payload.get("runtime_id")
                or trace.get("software_digest")
                != request_payload.get("software_digest")
                or trace.get("cjt_ids") != request_payload.get("cjt_ids")
                or trace.get("memory_read_refs")
                != request_payload.get("memory_read_refs")
                or trace.get("previous_trace_digest")
                != request_payload.get("base_trace_digest")
                or trace.get("state_before") != pre_state
                or trace.get("state_after") != post_state
                or trace.get("cause") != request_payload.get("cause")
                or trace.get("state_before") != request_payload.get("state_before")
                or trace.get("state_after") != request_payload.get("state_after")
                or trace.get("semantic_evidence")
                != request_payload.get("semantic_evidence")
                or trace.get("decoder_contract")
                != request_payload.get("decoder_contract")
                or trace.get("compute_plan") != request_payload.get("compute_plan")
                or trace.get("compute_observations")
                != request_payload.get("compute_observations")
                or trace.get("artifacts") != request_payload.get("artifacts")
                or trace.get("phases") != request_payload.get("phase_records")
                or trace.get("audit_transition") != expected_audit
                or not same_records(
                    trace.get("state_intents"),
                    expected_state_intents,
                    identity_field="intent_id",
                )
                or not same_records(
                    trace.get("state_intents"),
                    evidence["state_intents"],
                    identity_field="intent_id",
                )
                or any(
                    not same_records(
                        trace.get(name),
                        request_payload.get(name),
                        identity_field=identity,
                    )
                    or not same_records(
                        trace.get(name), evidence[name], identity_field=identity
                    )
                    for name, identity in collection_bindings
                )
            ):
                raise PersistenceError(
                    "network trace/request/durable evidence binding is invalid"
                )
            trace_model = trace.get("model_version")
            request_model = request_payload.get("model_version")
            if trace_model != request_model:
                raise PersistenceError("network model-version trace binding is invalid")
            if trace_model is not None:
                retained_model = self.model_version_record(
                    str(trace_model.get("model_digest"))
                )
                if (
                    trace_model.get("payload") != retained_model
                    or trace_model.get("parent_model_digest")
                    != retained_model.get("parent_model_digest")
                    or trace_model.get("artifact_id")
                    != retained_model.get("model_artifact_ref", {}).get(
                        "artifact_id"
                    )
                ):
                    raise PersistenceError(
                        "network model-version durable binding is invalid"
                    )
            for descriptor in trace.get("artifacts", []):
                if not isinstance(descriptor, Mapping):
                    raise PersistenceError("network trace artifact is invalid")
                artifact = self.load_artifact(str(descriptor.get("artifact_id")))
                if artifact.public_descriptor() != dict(descriptor):
                    raise PersistenceError(
                        "network trace artifact differs from durable bytes"
                    )

        def state_bias_map(
            state_payload: Mapping[str, Any],
        ) -> dict[str, Mapping[str, Any]]:
            values = state_payload.get("biases")
            items = values if isinstance(values, list) else [state_payload]
            result = {
                str(item.get("bias_id")): item
                for item in items
                if isinstance(item, Mapping)
                and isinstance(item.get("bias_id"), str)
            }
            if len(result) != len(items):
                raise PersistenceError("state Bias index is malformed")
            return result

        def open_repair_entries(
            state_payload: Mapping[str, Any],
        ) -> list[tuple[Mapping[str, Any], str]]:
            entries: list[tuple[Mapping[str, Any], str]] = []
            for bias in state_bias_map(state_payload).values():
                rpm = bias.get("rpm")
                if not isinstance(rpm, Mapping):
                    raise PersistenceError("state Bias RPM is malformed")
                open_ids = rpm.get("open_repair_ids")
                if not isinstance(open_ids, list):
                    raise PersistenceError("state Bias OPEN repairs are malformed")
                entries.extend((bias, str(item)) for item in open_ids)
            if len(entries) > 1:
                raise PersistenceError("v0.2 state retains multiple global OPEN repairs")
            return entries

        def viable_repair_cjts(
            state_payload: Mapping[str, Any], suspended_cjt_id: str
        ) -> tuple[str, ...]:
            """Replay the durable portion of the v0.2 repair preflight."""

            manifest = self.model_version_record(str(state_payload.get("model_digest")))
            network = manifest.get("network")
            if not isinstance(network, Mapping):
                raise PersistenceError("model manifest lacks repair topology")
            nodes = network.get("nodes")
            edges = network.get("edges")
            if not isinstance(nodes, list) or not isinstance(edges, list):
                raise PersistenceError("model repair topology is malformed")
            operation_by_cjt: dict[str, str] = {}
            for node in nodes:
                if not isinstance(node, Mapping):
                    raise PersistenceError("model topology node is malformed")
                cjt_id = node.get("cjt_id")
                operation_id = node.get("operation_id")
                if (
                    not isinstance(cjt_id, str)
                    or not cjt_id
                    or not isinstance(operation_id, str)
                    or not operation_id
                    or cjt_id in operation_by_cjt
                ):
                    raise PersistenceError("model topology node identity is invalid")
                operation_by_cjt[cjt_id] = operation_id
            permitted: set[tuple[str, str]] = set()
            for edge in edges:
                if not isinstance(edge, Mapping):
                    raise PersistenceError("model topology edge is malformed")
                source = edge.get("source_cjt_id")
                target = edge.get("target_cjt_id")
                allowed = edge.get("permitted")
                if (
                    not isinstance(source, str)
                    or not isinstance(target, str)
                    or not isinstance(allowed, bool)
                ):
                    raise PersistenceError("model topology edge is invalid")
                if allowed:
                    permitted.add((source, target))
            typed = _validated_state_biases(state_payload)
            by_cjt = {item.cjt_id: item for item in typed.values()}
            source_bias = by_cjt.get(suspended_cjt_id)
            if (
                source_bias is None
                or "cascade" not in source_bias.governance.topology_permissions
            ):
                return ()
            coordinator_id = receipt_payload.get("coordinator_id")
            nonconducting = {"BREAKDOWN", "NON_OHMIC", "UNSTABLE"}
            viable: list[str] = []
            for candidate in by_cjt.values():
                if (
                    candidate.cjt_id == suspended_cjt_id
                    or operation_by_cjt.get(candidate.cjt_id) != "^6"
                    or (suspended_cjt_id, candidate.cjt_id) not in permitted
                    or (candidate.cjt_id, suspended_cjt_id) not in permitted
                    or "cascade" not in candidate.governance.topology_permissions
                    or "execute" not in candidate.governance.hard_permissions
                    or "publish_effect" not in candidate.governance.hard_permissions
                    or coordinator_id
                    not in candidate.governance.effect_publication_authorities
                    or candidate.governance.quarantined
                    or not candidate.rpm.readiness.hard_open
                    or candidate.operating.region.value in nonconducting
                ):
                    continue
                viable.append(candidate.cjt_id)
            return tuple(sorted(viable))

        pre_biases = state_bias_map(pre_state)
        post_biases = state_bias_map(post_state)
        pre_open = open_repair_entries(pre_state)
        post_open = open_repair_entries(post_state)
        for frame in current_frames:
            before_bias = pre_biases.get(str(frame.get("suspended_bias_id")))
            after_bias = post_biases.get(str(frame.get("suspended_bias_id")))
            if before_bias is None or after_bias is None:
                raise PersistenceError("repair opening target Bias is missing")
            after_rpm = after_bias.get("rpm", {})
            after_memory = after_bias.get("memory", {})
            if (
                pre_open
                or before_bias.get("version") != frame.get("suspended_bias_version")
                or before_bias.get("state_digest")
                != add_candidate(
                    str(frame["rejected_candidate_effect_id"])
                ).get("bias_digest")
                or post_open != [(after_bias, str(frame["repair_id"]))]
                or after_rpm.get("open_repair_ids") != [frame.get("repair_id")]
                or after_rpm.get("suspended_parent_cause_id")
                != frame.get("parent_cause_id")
                or after_rpm.get("return_addresses")
                != [frame.get("return_address")]
                or frame.get("repair_id")
                not in after_memory.get("repair_frame_ids", [])
            ):
                raise PersistenceError("repair opening state transition is inexact")
            if "network_request_digest" in trace and not viable_repair_cjts(
                pre_state, str(before_bias.get("cjt_id"))
            ):
                raise PersistenceError("repair opening has no viable round trip")

        retained_cause = add_cause(str(trace["cause_id"]))
        if rollback_origin is not None and (
            retained_cause.get("content")
            != {
                "mode": "COMPENSATING_ROLLBACK",
                "rollback_of_receipt_id": rollback_origin,
                "reason_codes": list(receipt_payload.get("reason_codes", ()))[1:],
            }
            or retained_cause.get("provenance")
            != [f"commit-receipt:{rollback_origin}"]
        ):
            raise PersistenceError("rollback Cause/origin binding is invalid")
        # Network-extended traces carry the complete Cause in-band.  The
        # original/core TickTrace carries only its immutable Cause ID.
        if "cause" in trace:
            cause = trace["cause"]
            if not isinstance(cause, Mapping):
                raise PersistenceError("trace Cause is invalid")
            if retained_cause != dict(cause):
                raise PersistenceError("trace Cause differs from its immutable record")
        evidence["published_effects"] = [
            add_published(str(effect["published_effect_id"]))
            for effect in evidence["published_effects"]
        ]
        emitted_repair_subgoals = [
            emitted_subgoal_for_frame(frame) for frame in current_frames
        ]

        reserved_viable: tuple[str, ...] = ()
        if "network_request_digest" in trace and pre_open:
            suspended_bias, reserved_repair_id = pre_open[0]
            reserved_frame = add_repair_frame(reserved_repair_id)
            reserved_viable = viable_repair_cjts(
                pre_state, str(suspended_bias.get("cjt_id"))
            )
            route_phase = next(
                (
                    phase
                    for phase in trace.get("phases", [])
                    if isinstance(phase, Mapping) and phase.get("phase") == "ROUTE"
                ),
                None,
            )
            control_cjt_id = (
                None
                if route_phase is None
                else route_phase.get("inputs", {}).get("control_cjt_id")
            )
            if int(trace["tick"]) == int(reserved_frame["eligible_tick"]):
                expected_subgoal = emitted_subgoal_for_frame(reserved_frame)
                current_candidates = evidence["candidate_effects"]
                if (
                    retained_cause != expected_subgoal
                    or control_cjt_id not in reserved_viable
                    or len(current_candidates) != 1
                    or current_candidates[0].get("producer_cjt_id")
                    != control_cjt_id
                    or len(evidence["published_effects"]) != 1
                    or evidence["repair_outcomes"]
                    or post_open
                    != [(post_biases[str(suspended_bias["bias_id"])], reserved_repair_id)]
                    or post_biases[str(suspended_bias["bias_id"])] != suspended_bias
                    or trace.get("post_model_digest")
                    != trace.get("pre_model_digest")
                ):
                    raise PersistenceError(
                        "repair subgoal reserved transition is inexact"
                    )
            elif int(trace["tick"]) == int(reserved_frame["eligible_tick"]) + 1:
                if (
                    control_cjt_id != suspended_bias.get("cjt_id")
                    or len(evidence["repair_outcomes"]) != 1
                    or evidence["repair_outcomes"][0].get("repair_id")
                    != reserved_repair_id
                    or post_open
                ):
                    raise PersistenceError("repair resume reserved transition is inexact")
            else:
                raise PersistenceError("OPEN repair missed its reserved global tick")

        for outcome in evidence["repair_outcomes"]:
            try:
                validate_contract(outcome)
                repair_outcome_from_dict(outcome)
            except (ContractSchemaError, ContractTypeError, RepairError, KeyError) as error:
                raise PersistenceError("repair outcome contract is invalid") from error
            frame = add_repair_frame(str(outcome["repair_id"]))
            result_effect = add_published(str(outcome["result_effect_id"]))
            resumed_cause = add_cause(str(outcome["resumed_cause_id"]))
            resumed_candidate = add_candidate(
                str(outcome["resumed_candidate_effect_id"])
            )
            resumed_verifier = add_verifier(str(outcome["verifier_receipt_id"]))
            parent_cause = add_cause(str(frame["parent_cause_id"]))
            result_candidate = add_candidate(
                str(result_effect["candidate_effect_id"])
            )
            state_biases = pre_state.get("biases")
            if not isinstance(state_biases, list):
                state_biases = [pre_state]
            target = next(
                (
                    item
                    for item in state_biases
                    if isinstance(item, Mapping)
                    and item.get("bias_id") == outcome.get("target_bias_id")
                ),
                None,
            )
            target_map: Mapping[str, Any] = {} if target is None else target
            target_rpm = target_map.get("rpm", {})
            post_target = post_biases.get(str(outcome.get("target_bias_id")))
            post_target_map: Mapping[str, Any] = (
                {} if post_target is None else post_target
            )
            post_rpm = post_target_map.get("rpm", {})
            post_memory = post_target_map.get("memory", {})
            expected_return = (
                f"cjt:{target_map.get('cjt_id')}:cause:{frame['parent_cause_id']}"
                if target is not None
                else None
            )
            if (
                outcome.get("frame_digest") != frame.get("frame_digest")
                or outcome.get("tick") != frame.get("eligible_tick", -1) + 1
                or result_effect.get("tick") != frame.get("eligible_tick")
                or result_effect.get("publication_digest")
                != outcome.get("result_effect_digest")
                or result_effect.get("commit_receipt_id")
                != outcome.get("result_effect_commit_receipt_id")
                or result_candidate.get("parent_cause_id")
                != frame.get("subgoal_cause_id")
                or resumed_cause.get("tick") != outcome.get("tick")
                or resumed_cause.get("parent_effect_id")
                != result_effect.get("published_effect_id")
                or resumed_cause.get("originating_cjt_id")
                != result_effect.get("producer_cjt_id")
                or resumed_cause.get("candidate_operation_ids")
                != parent_cause.get("candidate_operation_ids")
                or resumed_cause.get("goal_context")
                != parent_cause.get("goal_context")
                or resumed_candidate.get("parent_cause_id")
                != resumed_cause.get("cause_id")
                or resumed_candidate.get("bias_id") != target_map.get("bias_id")
                or resumed_candidate.get("bias_version")
                != target_map.get("version")
                or resumed_candidate.get("bias_digest")
                != target_map.get("state_digest")
                or resumed_candidate.get("model_digest")
                != target_map.get("theta", {}).get("model_digest")
                or resumed_verifier.get("cause_id")
                != resumed_cause.get("cause_id")
                or resumed_verifier.get("candidate_effect_id")
                != resumed_candidate.get("candidate_effect_id")
                or resumed_verifier.get("candidate_effect_digest")
                != resumed_candidate.get("candidate_digest")
                or resumed_verifier.get("disposition") != "ACCEPT"
                or target is None
                or target_map.get("state_digest") != outcome.get("target_bias_digest")
                or target_map.get("version") != outcome.get("target_bias_version")
                or target_map.get("bias_id") != frame.get("suspended_bias_id")
                or target_map.get("version", -1) <= frame.get("suspended_bias_version", -1)
                or target_rpm.get("open_repair_ids") != [frame.get("repair_id")]
                or target_rpm.get("suspended_parent_cause_id")
                != frame.get("parent_cause_id")
                or target_rpm.get("return_addresses") != [expected_return]
                or frame.get("return_address") != expected_return
                or (
                    "network_request_digest" in trace
                    and result_candidate.get("producer_cjt_id")
                    not in reserved_viable
                )
                or post_target is None
                or post_rpm.get("open_repair_ids") != []
                or post_rpm.get("suspended_parent_cause_id") is not None
                or post_rpm.get("return_addresses") != []
                or frame.get("repair_id")
                not in post_rpm.get("repair_history", [])
                or frame.get("repair_id")
                not in post_memory.get("repair_frame_ids", [])
                or post_open
            ):
                raise PersistenceError("repair outcome evidence is inconsistent")
        for transition_batch in evidence["transition_batches"]:
            add_document("transition_batches", str(transition_batch["batch_id"]))
        for candidate in evidence["candidate_effects"]:
            add_candidate(str(candidate["candidate_effect_id"]))
        for verifier in evidence["verifier_receipts"]:
            add_verifier(str(verifier["receipt_id"]))
        for table in ("qualification_receipts", "state_intents", "model_intents"):
            for document in evidence[table]:
                retained = add_document(
                    table, str(document[identity_fields[table]])
                )
                if table == "qualification_receipts":
                    if (
                        retained.get("schema_version")
                        != "cas.neural-cjt.qualification-receipt/0.2"
                        or not verify_declared_digest(retained, "receipt_digest")
                    ):
                        raise PersistenceError(
                            "qualification_receipts schema is invalid"
                        )
                    continue
                if (
                    table == "state_intents"
                    and retained.get("contract_type") == "AUDIT_TRANSITION_INTENT"
                ):
                    if (
                        retained.get("schema_version")
                        != "cas.neural-cjt.audit-transition-intent/0.2"
                        or not verify_declared_digest(retained, "intent_digest")
                    ):
                        raise PersistenceError("state_intents schema is invalid")
                    continue
                try:
                    validate_contract(retained)
                except (ContractSchemaError, ContractTypeError) as error:
                    raise PersistenceError(f"{table} schema is invalid") from error
                if table == "model_intents" and "network_request_digest" in trace:
                    qualification = add_document(
                        "qualification_receipts",
                        str(retained.get("qualification_receipt_id")),
                    )
                    candidate_artifact = retained.get("candidate_artifact")
                    gradient_artifact = retained.get("gradient_artifact")
                    changed_names = qualification.get("changed_parameter_names")
                    if (
                        retained.get("update_kind") != "GRADIENT_DELTA"
                        or not isinstance(candidate_artifact, Mapping)
                        or not isinstance(gradient_artifact, Mapping)
                        or not isinstance(changed_names, list)
                    ):
                        raise PersistenceError("model intent authority label is invalid")
                    identity = {
                        "tick": retained.get("tick"),
                        "model_id": retained.get("model_id"),
                        "expected_model_digest": retained.get(
                            "expected_model_digest"
                        ),
                        "update_kind": retained.get("update_kind"),
                        "candidate_model_digest": candidate_artifact.get("sha256"),
                        "gradient_digest": gradient_artifact.get("sha256"),
                        "parameter_names": changed_names,
                        "parameter_group_ids": retained.get("parameter_group_ids"),
                        "plasticity_ppm": retained.get("plasticity_ppm"),
                        "verifier_receipt_id": retained.get(
                            "verifier_receipt_id"
                        ),
                        "qualification_receipt_id": retained.get(
                            "qualification_receipt_id"
                        ),
                    }
                    if retained.get("intent_id") != (
                        f"intent-model-{canonical_digest(identity)[:24]}"
                    ):
                        raise PersistenceError("model intent identity is invalid")
        for memory_record in evidence["memory_records"]:
            add_memory(str(memory_record["memory_record_id"]))

        def record_owner(table: str, record_id: str) -> str:
            owner = self._connection.execute(
                f"SELECT commit_receipt_id FROM {table} WHERE record_id = ?",
                (record_id,),
            ).fetchone()
            if owner is None:
                raise PersistenceError(f"state link to missing {table} record")
            return str(owner["commit_receipt_id"])

        def state_biases(state_payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
            values = state_payload.get("biases")
            if isinstance(values, list):
                return [item for item in values if isinstance(item, Mapping)]
            return [state_payload]

        def validate_state_links(
            state_payload: Mapping[str, Any], *, require_prior: bool
        ) -> None:
            for bias in state_biases(state_payload):
                memory = bias.get("memory", {})
                rpm = bias.get("rpm", {})
                operating = bias.get("operating", {})
                linked_records: list[dict[str, Any]] = []
                typed_links = (
                    ("causes", "recent_cause_ids", add_cause),
                    (
                        "candidate_effects",
                        "recent_candidate_effect_ids",
                        add_candidate,
                    ),
                    (
                        "verifier_receipts",
                        "verifier_receipt_ids",
                        add_verifier,
                    ),
                    ("repair_frames", "repair_frame_ids", add_repair_frame),
                    ("memory_records", "retrieved_memory_refs", add_memory),
                )
                for table, field, resolver in typed_links:
                    values = memory.get(field, [])
                    if not isinstance(values, list):
                        raise PersistenceError(f"Bias memory {field} is not a list")
                    for value in values:
                        record_id = str(value)
                        resolved = resolver(record_id)
                        if table == "memory_records":
                            linked_records.append(resolved)
                        if require_prior and record_owner(table, record_id) == receipt_id:
                            raise PersistenceError(
                                "pre-state refers to evidence created by its transition"
                            )
                recent_causes = memory.get("recent_cause_ids", [])
                recent_candidates = memory.get(
                    "recent_candidate_effect_ids", []
                )
                recent_verifiers = memory.get("verifier_receipt_ids", [])
                if not (
                    len(recent_causes)
                    == len(recent_candidates)
                    == len(recent_verifiers)
                ):
                    raise PersistenceError(
                        "Bias accepted-memory histories are not aligned"
                    )
                prior_tick = -1
                for cause_id, candidate_id, verifier_id in zip(
                    recent_causes,
                    recent_candidates,
                    recent_verifiers,
                    strict=True,
                ):
                    history_cause = add_cause(str(cause_id))
                    history_candidate = add_candidate(str(candidate_id))
                    history_verifier = add_verifier(str(verifier_id))
                    tick = int(history_cause.get("tick", -1))
                    if (
                        tick <= prior_tick
                        or history_candidate.get("parent_cause_id")
                        != history_cause.get("cause_id")
                        or history_candidate.get("bias_id") != bias.get("bias_id")
                        or history_candidate.get("producer_cjt_id")
                        != bias.get("cjt_id")
                        or history_verifier.get("candidate_effect_id")
                        != history_candidate.get("candidate_effect_id")
                        or history_verifier.get("cause_id")
                        != history_cause.get("cause_id")
                        or history_verifier.get("bias_id") != bias.get("bias_id")
                        or history_verifier.get("disposition") != "ACCEPT"
                        or history_verifier.get("semantic_outcome") != "INTENDED"
                        or history_verifier.get("repair_required") is not False
                    ):
                        raise PersistenceError(
                            "Bias accepted-memory history triple is invalid"
                        )
                    prior_tick = tick
                for field in ("open_repair_ids", "repair_history"):
                    values = rpm.get(field, [])
                    if not isinstance(values, list):
                        raise PersistenceError(f"Bias RPM {field} is not a list")
                    for value in values:
                        repair_id = str(value)
                        add_repair_frame(repair_id)
                        if require_prior and record_owner(
                            "repair_frames", repair_id
                        ) == receipt_id:
                            raise PersistenceError(
                                "pre-state refers to a current repair frame"
                            )
                expected_repair_memory = list(
                    dict.fromkeys(
                        [*rpm.get("repair_history", []), *rpm.get("open_repair_ids", [])]
                    )
                )[-16:]
                if memory.get("repair_frame_ids", []) != expected_repair_memory:
                    raise PersistenceError(
                        "Bias repair memory does not match bounded RPM history"
                    )
                suspended_parent = rpm.get("suspended_parent_cause_id")
                open_ids = rpm.get("open_repair_ids", [])
                return_addresses = rpm.get("return_addresses", [])
                if suspended_parent is not None:
                    parent = add_cause(str(suspended_parent))
                    if require_prior and record_owner(
                        "causes", str(suspended_parent)
                    ) == receipt_id:
                        raise PersistenceError(
                            "pre-state suspended parent is not prior evidence"
                        )
                    if len(open_ids) != 1:
                        raise PersistenceError(
                            "suspended Bias does not name exactly one OPEN frame"
                        )
                    frame = add_repair_frame(str(open_ids[0]))
                    if (
                        frame.get("parent_cause_id") != parent.get("cause_id")
                        or frame.get("suspended_bias_id") != bias.get("bias_id")
                        or return_addresses != [frame.get("return_address")]
                    ):
                        raise PersistenceError(
                            "suspended Bias/frame cross-link is invalid"
                        )
                elif open_ids or return_addresses:
                    raise PersistenceError(
                        "unsuspended Bias retains an open repair address"
                    )
                previous_verifier = operating.get(
                    "previous_committed_verifier_receipt_id"
                )
                if previous_verifier is not None:
                    add_verifier(str(previous_verifier))
                    if require_prior and record_owner(
                        "verifier_receipts", str(previous_verifier)
                    ) == receipt_id:
                        raise PersistenceError(
                            "pre-state refers to a current verifier receipt"
                        )
                provenance = memory.get("provenance_refs", [])
                if not isinstance(provenance, list):
                    raise PersistenceError("Bias memory provenance is not a list")
                required_provenance = {
                    str(item)
                    for record in linked_records
                    for item in record.get("provenance", [])
                }
                if not required_provenance.issubset(set(provenance)):
                    raise PersistenceError(
                        "Bias memory provenance omits a consumed record source"
                    )

        validate_state_links(pre_state, require_prior=True)
        validate_state_links(post_state, require_prior=False)

        resolving_models: set[str] = set()
        model_records: dict[str, dict[str, Any]] = {}
        selected_tick = int(trace["tick"])

        def add_model(model_digest: str) -> dict[str, Any]:
            if model_digest in resolving_models:
                raise PersistenceError("model lineage contains a cycle")
            if model_digest in model_records:
                return model_records[model_digest]
            resolving_models.add(model_digest)
            try:
                manifest = self.model_version_record(model_digest)
                parent_digest = manifest.get("parent_model_digest")
                origin_traces: list[dict[str, Any]] = []
                for item in all_traces:
                    if (
                        item.get("post_model_digest") != model_digest
                        or item.get("pre_model_digest") == model_digest
                    ):
                        continue
                    origin_receipt = self.receipt_by_id(
                        str(item.get("commit_receipt_id"))
                    )
                    if origin_receipt.get("disposition") == "COMMITTED":
                        origin_traces.append(item)
                if len(origin_traces) > 1:
                    raise PersistenceError("model version has multiple origin traces")
                origin = origin_traces[0] if origin_traces else None
                if parent_digest is None:
                    if origin is not None:
                        raise PersistenceError("root model has a learning origin")
                else:
                    if not isinstance(parent_digest, str) or not _valid_digest(
                        parent_digest
                    ):
                        raise PersistenceError("model parent digest is invalid")
                    parent = add_model(parent_digest)
                    if origin is None:
                        raise PersistenceError("learned model lacks an origin trace")
                    origin_tick = int(origin.get("tick", -1))
                    if (
                        origin_tick > selected_tick
                        or origin.get("pre_model_digest") != parent_digest
                        or (
                            "learning_tick" in manifest
                            and manifest.get("learning_tick") != origin_tick
                        )
                        or int(manifest.get("model_version", -1))
                        != int(parent.get("model_version", -1)) + 1
                    ):
                        raise PersistenceError("model lineage is not causal")
                    qualification_id = manifest.get("qualification_receipt_id")
                    if not isinstance(qualification_id, str) or not qualification_id:
                        raise PersistenceError(
                            "learned model lacks qualification evidence"
                        )
                    qualification = add_document(
                        "qualification_receipts", qualification_id
                    )
                    qualification_owner = record_owner(
                        "qualification_receipts", qualification_id
                    )
                    if (
                        qualification_owner != origin.get("commit_receipt_id")
                        or qualification.get("candidate_model_digest")
                        != model_digest
                        or qualification.get("qualified") is not True
                    ):
                        raise PersistenceError(
                            "model qualification/origin binding is invalid"
                        )
                model_records[model_digest] = manifest
                if origin is not None and origin.get("trace_id") != trace.get("trace_id"):
                    prior["model_versions"][model_digest] = manifest
                    add_origin(str(origin["commit_receipt_id"]))
                return manifest
            finally:
                resolving_models.discard(model_digest)

        for model_digest in dict.fromkeys(
            (trace["pre_model_digest"], trace["post_model_digest"])
        ):
            add_model(str(model_digest))
        model_versions = list(model_records.values())

        artifact_refs: set[tuple[str, str]] = set()
        for value in (
            trace,
            receipt_payload,
            *[item for records in evidence.values() for item in records],
            *memory_read_records,
            *model_versions,
            *[
                item
                for records in prior.values()
                for item in records.values()
            ],
        ):
            artifact_refs.update(_artifact_references(value))
        artifacts = []
        for artifact_id, digest in sorted(artifact_refs):
            artifact = self.load_artifact(artifact_id)
            if artifact.sha256 != digest:
                raise PersistenceError("transition artifact reference digest mismatch")
            artifacts.append(artifact.public_descriptor())
        return {
            "trace": trace,
            "commit_receipt": receipt_payload,
            "pre_state": pre_state,
            "post_state": post_state,
            **evidence,
            "memory_read_records": memory_read_records,
            "emitted_repair_subgoals": emitted_repair_subgoals,
            "model_versions": model_versions,
            "prior_dependencies": {
                name: [records[key] for key in sorted(records)]
                for name, records in prior.items()
            },
            "artifacts": artifacts,
        }

    def verify_integrity(self) -> bool:
        """Verify SQLite, immutable payload checksums, references, and trace chain."""

        try:
            integrity = self._connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                return False
            if self._connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                return False
            metadata = self._connection.execute(
                "SELECT value FROM store_metadata WHERE key = 'schema_version'"
            ).fetchone()
            if metadata is None or metadata["value"] != STORE_SCHEMA_VERSION:
                return False

            for table in (
                "state_versions",
                "model_versions",
                "trace_events",
                "commit_receipts",
                "published_effects",
                "memory_records",
                "repair_frames",
                "repair_outcomes",
                "transition_batches",
                "causes",
                "candidate_effects",
                "verifier_receipts",
                "qualification_receipts",
                "state_intents",
                "model_intents",
                "memory_intents",
                "rejection_audits",
            ):
                rows = self._connection.execute(
                    f"SELECT payload_sha256, payload_json FROM {table}"
                ).fetchall()
                if any(
                    not hmac.compare_digest(row["payload_sha256"], _sha256_text(row["payload_json"]))
                    for row in rows
                ):
                    return False
            public_rows = self._connection.execute(
                "SELECT trace_id, trace_digest, public_payload_sha256, public_payload_json "
                "FROM trace_events"
            ).fetchall()
            if any(
                row["public_payload_sha256"] != _sha256_text(row["public_payload_json"])
                or not verify_public_trace(json.loads(row["public_payload_json"]))
                or json.loads(row["public_payload_json"]).get("private_trace_id") != row["trace_id"]
                or json.loads(row["public_payload_json"]).get("private_trace_digest")
                != row["trace_digest"]
                for row in public_rows
            ):
                return False
            rejection_public_rows = self._connection.execute(
                "SELECT audit_id, audit_digest, public_payload_sha256, public_payload_json "
                "FROM rejection_audits"
            ).fetchall()
            if any(
                row["public_payload_sha256"] != _sha256_text(row["public_payload_json"])
                or not verify_public_rejection_audit(json.loads(row["public_payload_json"]))
                or json.loads(row["public_payload_json"]).get("private_audit_id") != row["audit_id"]
                or json.loads(row["public_payload_json"]).get("private_audit_digest")
                != row["audit_digest"]
                for row in rejection_public_rows
            ):
                return False
            artifacts = self._connection.execute(
                "SELECT artifact_id FROM artifacts"
            ).fetchall()
            for row in artifacts:
                self.load_artifact(row["artifact_id"])
            events = self.trace_events()
            if events and (
                not verify_trace_chain(events)
                or not _valid_tick_sequence(events)
            ):
                return False
            audits = self.rejection_audits()
            if audits and not verify_rejection_audit_chain(audits):
                return False
            trace_rows = self._connection.execute(
                "SELECT trace_id, trace_digest, previous_trace_digest, pre_state_digest, "
                "post_state_digest, payload_json FROM trace_events ORDER BY sequence"
            ).fetchall()
            for row in trace_rows:
                trace = json.loads(row["payload_json"])
                try:
                    validate_contract(trace)
                except (ContractSchemaError, ContractTypeError):
                    return False
                if (
                    trace.get("trace_id") != row["trace_id"]
                    or trace.get("trace_digest") != row["trace_digest"]
                    or trace.get("previous_trace_digest") != row["previous_trace_digest"]
                    or trace.get("pre_state_digest") != row["pre_state_digest"]
                    or trace.get("post_state_digest") != row["post_state_digest"]
                ):
                    return False
                receipt_row = self._connection.execute(
                    "SELECT receipt_id, batch_id FROM commit_receipts WHERE trace_digest = ?",
                    (row["trace_digest"],),
                ).fetchone()
                if receipt_row is None:
                    return False
                receipt = self.receipt_by_id(str(receipt_row["receipt_id"]))
                if (
                    receipt.get("receipt_id") != receipt_row["receipt_id"]
                    or receipt.get("batch_id") != receipt_row["batch_id"]
                    or receipt.get("trace_id") != row["trace_id"]
                    or trace.get("commit_receipt_id") != receipt_row["receipt_id"]
                ):
                    return False
                evidence_ids: dict[str, set[str]] = {}
                for table in (
                    "transition_batches",
                    "causes",
                    "candidate_effects",
                    "verifier_receipts",
                    "qualification_receipts",
                    "state_intents",
                    "model_intents",
                    "memory_intents",
                    "published_effects",
                    "memory_records",
                    "repair_frames",
                    "repair_outcomes",
                ):
                    ids = self._connection.execute(
                        f"SELECT record_id FROM {table} WHERE commit_receipt_id = ?",
                        (receipt_row["receipt_id"],),
                    ).fetchall()
                    evidence_ids[table] = {item["record_id"] for item in ids}
                if (
                    evidence_ids["transition_batches"] != {receipt_row["batch_id"]}
                    or trace.get("cause_id") not in evidence_ids["causes"]
                    or set(trace.get("candidate_effect_ids", []))
                    != evidence_ids["candidate_effects"]
                    or set(trace.get("verifier_receipt_ids", []))
                    != evidence_ids["verifier_receipts"]
                    or set(trace.get("published_effect_ids", []))
                    != evidence_ids["published_effects"]
                    or set(receipt.get("published_effect_ids", []))
                    != evidence_ids["published_effects"]
                    or set(receipt.get("opened_repair_ids", []))
                    != evidence_ids["repair_frames"]
                    or set(trace.get("repair_outcome_ids", []))
                    != evidence_ids["repair_outcomes"]
                ):
                    return False
                if "network_request_digest" in trace:
                    request_documents = self.documents_for_receipt(
                        "transition_batches", receipt_row["receipt_id"]
                    )
                    if len(request_documents) != 1:
                        return False
                    request_payload = request_documents[0]
                    request_row = self._connection.execute(
                        "SELECT request_digest FROM commit_receipts WHERE receipt_id = ?",
                        (receipt_row["receipt_id"],),
                    ).fetchone()
                    if request_row is None:
                        return False
                    request_digest = str(request_row["request_digest"])
                    pre_version, _, pre_state = self.state_record(
                        str(row["pre_state_digest"])
                    )
                    post_version, _, post_state = self.state_record(
                        str(row["post_state_digest"])
                    )
                    expected_audit = None
                    expected_state_intents = list(
                        request_payload.get("state_intents", [])
                    )
                    if request_payload.get("audit_only") is True:
                        audit_body = {
                            "contract_type": "AUDIT_TRANSITION_INTENT",
                            "schema_version": (
                                "cas.neural-cjt.audit-transition-intent/0.2"
                            ),
                            "intent_id": f"audit-transition-{request_digest[:24]}",
                            "tick": request_payload.get("tick"),
                            "issuer_id": receipt.get("coordinator_id"),
                            "authority_capability": "PROPOSE_STATE_UPDATE",
                            "expected_state_version": pre_version,
                            "expected_state_digest": row["pre_state_digest"],
                            "proposed_state_version": post_version,
                            "proposed_state_digest": row["post_state_digest"],
                            "reason_codes": request_payload.get(
                                "audit_reason_codes"
                            ),
                            "bias_and_model_bytes_unchanged": True,
                        }
                        expected_state_intents.append(
                            {
                                **audit_body,
                                "intent_digest": canonical_digest(audit_body),
                            }
                        )
                        expected_audit = {
                            "contract_type": "AUDIT_TRANSITION_INTENT",
                            "schema_version": "cas.neural-cjt.audit-transition/0.2",
                            "audit_id": f"audit-{request_digest[:24]}",
                            "reason_codes": request_payload.get(
                                "audit_reason_codes"
                            ),
                            "bias_and_model_bytes_unchanged": True,
                        }
                    cause_documents = list(
                        self.documents_for_receipt(
                            "causes", receipt_row["receipt_id"]
                        )
                    )
                    if (
                        canonical_digest(request_payload) != request_digest
                        or trace.get("network_request_digest") != request_digest
                        or trace.get("tick") != request_payload.get("tick")
                        or trace.get("runtime_id")
                        != request_payload.get("runtime_id")
                        or trace.get("software_digest")
                        != request_payload.get("software_digest")
                        or trace.get("cjt_ids") != request_payload.get("cjt_ids")
                        or trace.get("previous_trace_digest")
                        != request_payload.get("base_trace_digest")
                        or trace.get("memory_read_refs")
                        != request_payload.get("memory_read_refs")
                        or trace.get("state_before") != pre_state
                        or trace.get("state_after") != post_state
                        or trace.get("state_before")
                        != request_payload.get("state_before")
                        or trace.get("state_after")
                        != request_payload.get("state_after")
                        or trace.get("cause") != request_payload.get("cause")
                        or cause_documents != [request_payload.get("cause")]
                        or trace.get("phases")
                        != request_payload.get("phase_records")
                        or trace.get("semantic_evidence")
                        != request_payload.get("semantic_evidence")
                        or trace.get("decoder_contract")
                        != request_payload.get("decoder_contract")
                        or trace.get("compute_plan")
                        != request_payload.get("compute_plan")
                        or trace.get("compute_observations")
                        != request_payload.get("compute_observations")
                        or trace.get("artifacts")
                        != request_payload.get("artifacts")
                        or trace.get("model_version")
                        != request_payload.get("model_version")
                        or trace.get("audit_transition") != expected_audit
                    ):
                        return False
                    for table, identity in (
                        ("candidate_effects", "candidate_effect_id"),
                        ("verifier_receipts", "receipt_id"),
                        ("state_intents", "intent_id"),
                        ("model_intents", "intent_id"),
                        ("memory_intents", "intent_id"),
                        ("repair_frames", "repair_id"),
                        ("repair_outcomes", "outcome_id"),
                        ("qualification_receipts", "qualification_receipt_id"),
                    ):
                        embedded = trace.get(table)
                        durable = list(
                            self.documents_for_receipt(
                                table, receipt_row["receipt_id"]
                            )
                        )
                        expected = (
                            expected_state_intents
                            if table == "state_intents"
                            else request_payload.get(table)
                        )
                        if not isinstance(embedded, list) or not isinstance(
                            expected, list
                        ):
                            return False
                        try:
                            embedded_map = {
                                str(item[identity]): item for item in embedded
                            }
                            durable_map = {
                                str(item[identity]): item for item in durable
                            }
                            expected_map = {
                                str(item[identity]): item for item in expected
                            }
                        except (KeyError, TypeError):
                            return False
                        if (
                            len(embedded_map) != len(embedded)
                            or len(durable_map) != len(durable)
                            or len(expected_map) != len(expected)
                            or canonical_json(embedded_map)
                            != canonical_json(durable_map)
                            or canonical_json(embedded_map)
                            != canonical_json(expected_map)
                        ):
                            return False
                    trace_model = trace.get("model_version")
                    if trace_model is not None:
                        if not isinstance(trace_model, Mapping):
                            return False
                        retained_model = self.model_version_record(
                            str(trace_model.get("model_digest"))
                        )
                        if (
                            trace_model.get("payload") != retained_model
                            or trace_model.get("parent_model_digest")
                            != retained_model.get("parent_model_digest")
                            or trace_model.get("artifact_id")
                            != retained_model.get("model_artifact_ref", {}).get(
                                "artifact_id"
                            )
                        ):
                            return False
                    for descriptor in trace.get("artifacts", []):
                        if not isinstance(descriptor, Mapping):
                            return False
                        artifact = self.load_artifact(
                            str(descriptor.get("artifact_id"))
                        )
                        if artifact.public_descriptor() != dict(descriptor):
                            return False
                stored_intents = (
                    evidence_ids["state_intents"]
                    | evidence_ids["model_intents"]
                    | evidence_ids["memory_intents"]
                )
                accepted = set(trace.get("accepted_intent_ids", []))
                if receipt.get("rollback_of_receipt_id") is not None:
                    stored_intents.add(
                        f"rollback:{receipt['rollback_of_receipt_id']}"
                    )
                if (
                    accepted != stored_intents
                    or set(receipt.get("accepted_intent_ids", []))
                    != stored_intents
                    or set(trace.get("memory_write_refs", []))
                    != evidence_ids["memory_records"]
                    or evidence_ids["memory_records"]
                    != {
                        str(item["memory_record_id"])
                        for item in self.documents_for_receipt(
                            "memory_intents", receipt_row["receipt_id"]
                        )
                    }
                    or (
                        "network_request_digest" in trace
                        and (
                            set(trace.get("repair_frame_ids", []))
                            != evidence_ids["repair_frames"]
                            or set(trace.get("repair_outcome_ids", []))
                            != evidence_ids["repair_outcomes"]
                        )
                    )
                ):
                    return False
                model_intents = self.documents_for_receipt(
                    "model_intents", receipt_row["receipt_id"]
                )
                for intent in model_intents:
                    if intent.get("qualification_receipt_id") not in evidence_ids[
                        "qualification_receipts"
                    ]:
                        return False

            if trace_rows:
                # Every transition must independently close its semantic
                # request/evidence graph.  A valid hash chain alone cannot
                # detect a resealed mutation in an older request batch.
                for trace_row in trace_rows:
                    self.reconstruct_transition(str(trace_row["trace_id"]))

            identity_fields = {
                "transition_batches": "batch_id",
                "causes": "cause_id",
                "candidate_effects": "candidate_effect_id",
                "verifier_receipts": "receipt_id",
                "qualification_receipts": "qualification_receipt_id",
                "state_intents": "intent_id",
                "model_intents": "intent_id",
                "memory_intents": "intent_id",
                "published_effects": "published_effect_id",
                "memory_records": "memory_record_id",
                "repair_frames": "repair_id",
                "repair_outcomes": "outcome_id",
            }
            digest_fields = {
                "candidate_effects": "candidate_digest",
                "verifier_receipts": "receipt_digest",
                "qualification_receipts": "receipt_digest",
                "state_intents": "intent_digest",
                "model_intents": "intent_digest",
                "memory_intents": "intent_digest",
                "published_effects": "publication_digest",
                "memory_records": "record_digest",
                "repair_frames": "frame_digest",
                "repair_outcomes": "outcome_digest",
            }
            for table, identity_field in identity_fields.items():
                rows = self._connection.execute(
                    f"SELECT record_id, payload_json FROM {table}"
                ).fetchall()
                for row in rows:
                    payload = json.loads(row["payload_json"])
                    if payload.get(identity_field) != row["record_id"]:
                        return False
                    digest_field = digest_fields.get(table)
                    if digest_field is not None and not verify_declared_digest(
                        payload, digest_field
                    ):
                        return False

            # Validate semantic links for every retained document, including
            # records no longer reachable from the latest Bias snapshot.
            semantic_tables = tuple(identity_fields)
            retained: dict[str, dict[str, dict[str, Any]]] = {}
            owners: dict[str, dict[str, str]] = {}
            for table in semantic_tables:
                retained[table] = {}
                owners[table] = {}
                rows = self._connection.execute(
                    f"SELECT record_id, commit_receipt_id, payload_json FROM {table}"
                ).fetchall()
                for document_row in rows:
                    record_id = str(document_row["record_id"])
                    retained[table][record_id] = json.loads(
                        document_row["payload_json"]
                    )
                    owners[table][record_id] = str(
                        document_row["commit_receipt_id"]
                    )

            receipt_ticks = {
                str(row["receipt_id"]): int(
                    self.receipt_by_id(str(row["receipt_id"]))["tick"]
                )
                for row in self._connection.execute(
                    "SELECT receipt_id FROM commit_receipts"
                ).fetchall()
            }
            event_by_receipt = {
                str(event.get("commit_receipt_id")): event for event in events
            }
            for table, documents in retained.items():
                if table == "transition_batches":
                    continue
                for record_id, payload in documents.items():
                    if (
                        table == "state_intents"
                        and payload.get("contract_type")
                        == "AUDIT_TRANSITION_INTENT"
                    ):
                        if payload.get("schema_version") != (
                            "cas.neural-cjt.audit-transition-intent/0.2"
                        ):
                            return False
                    elif table not in {"qualification_receipts", "memory_records"}:
                        validate_contract(payload)
                    elif table == "qualification_receipts" and (
                        payload.get("schema_version")
                        != "cas.neural-cjt.qualification-receipt/0.2"
                    ):
                        return False
                    elif table == "memory_records" and (
                        payload.get("schema_version")
                        != "cas.neural-cjt.memory-record/0.2"
                    ):
                        return False
                    tick_field = (
                        "opened_tick"
                        if table == "repair_frames"
                        else (
                            "learning_tick"
                            if table == "qualification_receipts"
                            and "learning_tick" in payload
                            else "tick"
                        )
                    )
                    if table != "memory_records" and tick_field in payload and (
                        payload[tick_field]
                        != receipt_ticks[owners[table][record_id]]
                    ):
                        return False

            for cause_id, cause in retained["causes"].items():
                identity = {
                    "tick": cause.get("tick"),
                    "cause_kind": cause.get("cause_kind"),
                    "content": cause.get("content"),
                    "goal_context": cause.get("goal_context"),
                    "source": cause.get("source"),
                    "provenance": cause.get("provenance"),
                    "uncertainty_ppm": cause.get("uncertainty_ppm"),
                    "entity_bindings": cause.get("entity_bindings"),
                    "relation_bindings": cause.get("relation_bindings"),
                    "candidate_operation_ids": cause.get(
                        "candidate_operation_ids"
                    ),
                    "memory_refs": cause.get("memory_refs"),
                    "content_ref": cause.get("content_ref"),
                    "parent_effect_id": cause.get("parent_effect_id"),
                    "originating_cjt_id": cause.get("originating_cjt_id"),
                    "originating_modality": cause.get("originating_modality"),
                }
                if (
                    cause_id != f"cause-{canonical_digest(identity)[:24]}"
                    or cause.get("time_label")
                    != f"logical-tick:{cause.get('tick')}"
                    or any(
                        str(memory_id) not in retained["memory_records"]
                        for memory_id in cause.get("memory_refs", [])
                    )
                ):
                    return False
                parent_effect_id = cause.get("parent_effect_id")
                if parent_effect_id is not None:
                    parent_effect = retained["published_effects"].get(
                        str(parent_effect_id)
                    )
                    if (
                        parent_effect is None
                        or int(parent_effect.get("tick", -1))
                        >= int(cause.get("tick", -1))
                    ):
                        return False

            for candidate_id, candidate in retained["candidate_effects"].items():
                parent = retained["causes"].get(
                    str(candidate.get("parent_cause_id"))
                )
                identity = {
                    "tick": candidate.get("tick"),
                    "parent_cause_id": candidate.get("parent_cause_id"),
                    "producer_cjt_id": candidate.get("producer_cjt_id"),
                    "operation_contract_digest": candidate.get(
                        "operation_contract_digest"
                    ),
                    "bias_digest": candidate.get("bias_digest"),
                    "model_digest": candidate.get("model_digest"),
                    "content": candidate.get("content"),
                    "content_ref": candidate.get("content_ref"),
                }
                if (
                    parent is None
                    or candidate.get("tick") != parent.get("tick")
                    or candidate_id
                    != f"candidate-effect-{canonical_digest(identity)[:24]}"
                ):
                    return False
                owner_trace = event_by_receipt.get(
                    owners["candidate_effects"][candidate_id]
                )
                if owner_trace is None:
                    return False
                if "network_request_digest" in owner_trace:
                    observe = next(
                        (
                            phase
                            for phase in owner_trace.get("phases", [])
                            if isinstance(phase, Mapping)
                            and phase.get("phase") == "OBSERVE"
                        ),
                        None,
                    )
                    decoder = owner_trace.get("decoder_contract")
                    control_digest = (
                        None
                        if not isinstance(observe, Mapping)
                        else observe.get("diagnostics", {}).get(
                            "control_binding_digest"
                        )
                    )
                    decoder_digest = (
                        None
                        if not isinstance(decoder, Mapping)
                        else decoder.get("decoder_digest")
                    )
                    if (
                        not isinstance(control_digest, str)
                        or not isinstance(decoder_digest, str)
                        or candidate.get("provenance")
                        != [
                            f"cause:{candidate.get('parent_cause_id')}",
                            f"bias:{candidate.get('bias_digest')}",
                            f"model:{candidate.get('model_digest')}",
                            f"decoder:{decoder_digest}",
                            f"control-binding:{control_digest}",
                        ]
                        or candidate.get("uncertainty_ppm") != 0
                    ):
                        return False

            for verifier_id, verifier in retained["verifier_receipts"].items():
                candidate = retained["candidate_effects"].get(
                    str(verifier.get("candidate_effect_id"))
                )
                identity_digest = canonical_digest(
                    {
                        "tick": verifier.get("tick"),
                        "verifier_id": verifier.get("verifier_id"),
                        "verifier_version": verifier.get("verifier_version"),
                        "verifier_digest": verifier.get("verifier_digest"),
                        "cause_id": verifier.get("cause_id"),
                        "candidate_effect_id": verifier.get(
                            "candidate_effect_id"
                        ),
                        "candidate_effect_digest": verifier.get(
                            "candidate_effect_digest"
                        ),
                        "bias_digest": verifier.get("bias_digest"),
                        "contract_digest": verifier.get(
                            "operation_contract_digest"
                        ),
                        "outcome": verifier.get("semantic_outcome"),
                        "disposition": verifier.get("disposition"),
                        "reason_codes": verifier.get("reason_codes"),
                        "evidence_refs": verifier.get("evidence_refs"),
                    }
                )
                if candidate is None or any(
                    verifier.get(left) != candidate.get(right)
                    for left, right in (
                        ("tick", "tick"),
                        ("cause_id", "parent_cause_id"),
                        ("candidate_effect_digest", "candidate_digest"),
                        ("bias_id", "bias_id"),
                        ("bias_version", "bias_version"),
                        ("bias_digest", "bias_digest"),
                        ("operation_contract_id", "operation_contract_id"),
                        (
                            "operation_contract_digest",
                            "operation_contract_digest",
                        ),
                        ("model_digest", "model_digest"),
                    )
                ) or verifier_id != f"verifier-receipt-{identity_digest}":
                    return False

            for intent_id, intent in retained["model_intents"].items():
                intent_owner_trace = event_by_receipt.get(
                    owners["model_intents"][intent_id]
                )
                if (
                    intent_owner_trace is None
                    or "network_request_digest" not in intent_owner_trace
                ):
                    continue
                qualification = retained["qualification_receipts"].get(
                    str(intent.get("qualification_receipt_id"))
                )
                candidate_artifact = intent.get("candidate_artifact")
                gradient_artifact = intent.get("gradient_artifact")
                changed_names = (
                    None
                    if qualification is None
                    else qualification.get("changed_parameter_names")
                )
                if (
                    qualification is None
                    or intent.get("update_kind") != "GRADIENT_DELTA"
                    or not isinstance(candidate_artifact, Mapping)
                    or not isinstance(gradient_artifact, Mapping)
                    or not isinstance(changed_names, list)
                ):
                    return False
                identity = {
                    "tick": intent.get("tick"),
                    "model_id": intent.get("model_id"),
                    "expected_model_digest": intent.get(
                        "expected_model_digest"
                    ),
                    "update_kind": intent.get("update_kind"),
                    "candidate_model_digest": candidate_artifact.get("sha256"),
                    "gradient_digest": gradient_artifact.get("sha256"),
                    "parameter_names": changed_names,
                    "parameter_group_ids": intent.get("parameter_group_ids"),
                    "plasticity_ppm": intent.get("plasticity_ppm"),
                    "verifier_receipt_id": intent.get("verifier_receipt_id"),
                    "qualification_receipt_id": intent.get(
                        "qualification_receipt_id"
                    ),
                }
                if intent_id != f"intent-model-{canonical_digest(identity)[:24]}":
                    return False

            for effect_id, effect in retained["published_effects"].items():
                candidate = retained["candidate_effects"].get(
                    str(effect.get("candidate_effect_id"))
                )
                verifier = retained["verifier_receipts"].get(
                    str(effect.get("verifier_receipt_id"))
                )
                owner_receipt = self.receipt_by_id(
                    owners["published_effects"][effect_id]
                )
                identity_payload = dict(effect)
                identity_payload.pop("publication_digest", None)
                identity_payload["published_effect_id"] = "pending"
                if (
                    candidate is None
                    or verifier is None
                    or effect_id
                    != f"effect-{canonical_digest(identity_payload)[:24]}"
                    or effect.get("authoritative") is not True
                    or effect.get("content") != candidate.get("content")
                    or effect.get("content_ref") != candidate.get("content_ref")
                    or effect.get("producer_cjt_id")
                    != candidate.get("producer_cjt_id")
                    or verifier.get("candidate_effect_id")
                    != candidate.get("candidate_effect_id")
                    or verifier.get("disposition") != "ACCEPT"
                    or verifier.get("semantic_outcome") != "INTENDED"
                    or verifier.get("repair_required") is not False
                    or owner_receipt.get("disposition") != "COMMITTED"
                    or effect_id
                    not in owner_receipt.get("published_effect_ids", [])
                    or effect.get("commit_receipt_id")
                    != owners["published_effects"][effect_id]
                ):
                    return False

            for memory_id, memory in retained["memory_records"].items():
                intent_id = str(memory.get("source_intent_id"))
                intent = retained["memory_intents"].get(intent_id)
                verifier = retained["verifier_receipts"].get(
                    str(memory.get("verifier_receipt_id"))
                )
                if (
                    intent is None
                    or verifier is None
                    or owners["memory_records"][memory_id]
                    != owners["memory_intents"].get(intent_id)
                    or intent.get("tick")
                    != receipt_ticks[owners["memory_records"][memory_id]]
                    or intent.get("memory_record_id") != memory_id
                    or any(
                        memory.get(field) != intent.get(field)
                        for field in (
                            "memory_kind",
                            "content",
                            "content_ref",
                            "confidence_ppm",
                            "provenance",
                            "evidence_refs",
                            "verifier_receipt_id",
                        )
                    )
                    or memory.get("evidence_refs")
                    != verifier.get("evidence_refs")
                ):
                    return False

            for frame_id, frame in retained["repair_frames"].items():
                repair_frame_from_dict(frame)
                candidate = retained["candidate_effects"].get(
                    str(frame.get("rejected_candidate_effect_id"))
                )
                verifier = retained["verifier_receipts"].get(
                    str(frame.get("verifier_receipt_id"))
                )
                if (
                    candidate is None
                    or verifier is None
                    or candidate.get("parent_cause_id")
                    != frame.get("parent_cause_id")
                    or candidate.get("bias_id")
                    != frame.get("suspended_bias_id")
                    or candidate.get("bias_version")
                    != frame.get("suspended_bias_version")
                    or verifier.get("disposition") != "REPAIR"
                    or verifier.get("repair_required") is not True
                ):
                    return False

            for outcome_id, outcome in retained["repair_outcomes"].items():
                repair_outcome_from_dict(outcome)
                frame = retained["repair_frames"].get(str(outcome.get("repair_id")))
                effect = retained["published_effects"].get(
                    str(outcome.get("result_effect_id"))
                )
                resumed_cause = retained["causes"].get(
                    str(outcome.get("resumed_cause_id"))
                )
                resumed_candidate = retained["candidate_effects"].get(
                    str(outcome.get("resumed_candidate_effect_id"))
                )
                resumed_verifier = retained["verifier_receipts"].get(
                    str(outcome.get("verifier_receipt_id"))
                )
                if None in (
                    frame,
                    effect,
                    resumed_cause,
                    resumed_candidate,
                    resumed_verifier,
                ):
                    return False
                assert frame is not None and effect is not None
                assert resumed_cause is not None and resumed_candidate is not None
                assert resumed_verifier is not None
                owner_receipt = self.receipt_by_id(
                    owners["repair_outcomes"][outcome_id]
                )
                owner_trace = next(
                    (
                        item
                        for item in events
                        if item.get("trace_id") == owner_receipt.get("trace_id")
                    ),
                    None,
                )
                if owner_trace is None:
                    return False
                target_state = self.load_state(str(owner_trace["pre_state_digest"]))
                target_values = target_state.get("biases")
                target_items = (
                    target_values if isinstance(target_values, list) else [target_state]
                )
                target = next(
                    (
                        item
                        for item in target_items
                        if isinstance(item, Mapping)
                        and item.get("bias_id") == outcome.get("target_bias_id")
                    ),
                    None,
                )
                target_map: Mapping[str, Any] = {} if target is None else target
                expected_return = (
                    f"cjt:{target_map.get('cjt_id')}:cause:{frame.get('parent_cause_id')}"
                )
                if (
                    target is None
                    or outcome.get("frame_digest") != frame.get("frame_digest")
                    or outcome.get("tick") != frame.get("eligible_tick", -1) + 1
                    or effect.get("tick") != frame.get("eligible_tick")
                    or outcome.get("result_effect_digest")
                    != effect.get("publication_digest")
                    or outcome.get("result_effect_commit_receipt_id")
                    != effect.get("commit_receipt_id")
                    or resumed_cause.get("parent_effect_id")
                    != effect.get("published_effect_id")
                    or resumed_cause.get("tick") != outcome.get("tick")
                    or resumed_candidate.get("parent_cause_id")
                    != resumed_cause.get("cause_id")
                    or resumed_candidate.get("bias_id") != target_map.get("bias_id")
                    or resumed_candidate.get("bias_version")
                    != target_map.get("version")
                    or resumed_candidate.get("bias_digest")
                    != target_map.get("state_digest")
                    or resumed_candidate.get("model_digest")
                    != target_map.get("theta", {}).get("model_digest")
                    or resumed_verifier.get("candidate_effect_id")
                    != resumed_candidate.get("candidate_effect_id")
                    or resumed_verifier.get("cause_id")
                    != resumed_cause.get("cause_id")
                    or resumed_verifier.get("disposition") != "ACCEPT"
                    or target_map.get("state_digest")
                    != outcome.get("target_bias_digest")
                    or target_map.get("version")
                    != outcome.get("target_bias_version")
                    or frame.get("return_address") != expected_return
                    or target_map.get("rpm", {}).get("return_addresses")
                    != [expected_return]
                ):
                    return False

            for state_document_row in self._connection.execute(
                "SELECT payload_json FROM state_versions"
            ).fetchall():
                state_payload = json.loads(state_document_row["payload_json"])
                nested = state_payload.get("biases")
                bias_values = nested if isinstance(nested, list) else [state_payload]
                for bias in bias_values:
                    if not isinstance(bias, Mapping):
                        return False
                    memory = bias.get("memory", {})
                    rpm = bias.get("rpm", {})
                    cause_ids = memory.get("recent_cause_ids", [])
                    candidate_ids = memory.get(
                        "recent_candidate_effect_ids", []
                    )
                    verifier_ids = memory.get("verifier_receipt_ids", [])
                    if not (
                        isinstance(cause_ids, list)
                        and isinstance(candidate_ids, list)
                        and isinstance(verifier_ids, list)
                        and len(cause_ids)
                        == len(candidate_ids)
                        == len(verifier_ids)
                    ):
                        return False
                    previous_tick = -1
                    for cause_id, candidate_id, verifier_id in zip(
                        cause_ids, candidate_ids, verifier_ids, strict=True
                    ):
                        cause = retained["causes"].get(str(cause_id))
                        candidate = retained["candidate_effects"].get(
                            str(candidate_id)
                        )
                        verifier = retained["verifier_receipts"].get(
                            str(verifier_id)
                        )
                        if cause is None or candidate is None or verifier is None:
                            return False
                        candidate_tick = int(candidate.get("tick", -1))
                        if (
                            candidate_tick <= previous_tick
                            or candidate.get("parent_cause_id")
                            != cause.get("cause_id")
                            or candidate.get("bias_id") != bias.get("bias_id")
                            or candidate.get("producer_cjt_id")
                            != bias.get("cjt_id")
                            or verifier.get("candidate_effect_id")
                            != candidate.get("candidate_effect_id")
                            or verifier.get("cause_id") != cause.get("cause_id")
                            or verifier.get("bias_id") != bias.get("bias_id")
                            or verifier.get("disposition") != "ACCEPT"
                            or verifier.get("semantic_outcome") != "INTENDED"
                            or verifier.get("repair_required") is not False
                        ):
                            return False
                        previous_tick = candidate_tick
                    expected_repairs = list(
                        dict.fromkeys(
                            [
                                *rpm.get("repair_history", []),
                                *rpm.get("open_repair_ids", []),
                            ]
                        )
                    )[-16:]
                    if memory.get("repair_frame_ids", []) != expected_repairs:
                        return False
                    retrieved_ids = memory.get("retrieved_memory_refs", [])
                    if any(
                        str(memory_id) not in retained["memory_records"]
                        for memory_id in retrieved_ids
                    ):
                        return False
                    required_provenance = {
                        str(item)
                        for memory_id in retrieved_ids
                        for item in retained["memory_records"][
                            str(memory_id)
                        ].get("provenance", [])
                    }
                    if not required_provenance.issubset(
                        set(memory.get("provenance_refs", []))
                    ):
                        return False

            # Every retained state row participates in one valid lineage; this
            # catches row-only parent rewires as well as nested Bias rewires.
            for state_row in self._connection.execute(
                "SELECT state_digest FROM state_versions"
            ).fetchall():
                self._validate_state_lineage(str(state_row["state_digest"]))

            model_manifests = {
                str(model_row["model_digest"]): self.model_version_record(
                    str(model_row["model_digest"])
                )
                for model_row in self._connection.execute(
                    "SELECT model_digest FROM model_versions"
                ).fetchall()
            }
            model_origins: dict[str, dict[str, Any]] = {}
            for event in events:
                if event.get("post_model_digest") == event.get("pre_model_digest"):
                    continue
                event_receipt = self.receipt_by_id(
                    str(event.get("commit_receipt_id"))
                )
                if event_receipt.get("disposition") != "COMMITTED":
                    continue
                digest = str(event.get("post_model_digest"))
                if digest in model_origins:
                    return False
                model_origins[digest] = event
            visiting_models: set[str] = set()
            validated_models: set[str] = set()

            def validate_model(model_digest: str) -> int:
                if model_digest in visiting_models:
                    raise PersistenceError("model lineage contains a cycle")
                if model_digest in validated_models:
                    origin = model_origins.get(model_digest)
                    return 0 if origin is None else int(origin["tick"])
                manifest = model_manifests.get(model_digest)
                if manifest is None:
                    raise PersistenceError("model lineage parent is missing")
                visiting_models.add(model_digest)
                parent_digest = manifest.get("parent_model_digest")
                origin = model_origins.get(model_digest)
                if parent_digest is None:
                    if origin is not None:
                        raise PersistenceError("root model has a creation trace")
                    origin_tick = 0
                else:
                    if not isinstance(parent_digest, str):
                        raise PersistenceError("model parent digest is invalid")
                    parent_tick = validate_model(parent_digest)
                    if origin is None:
                        raise PersistenceError("learned model has no creation trace")
                    origin_tick = int(origin["tick"])
                    qualification_id = manifest.get("qualification_receipt_id")
                    qualification = retained["qualification_receipts"].get(
                        str(qualification_id)
                    )
                    if (
                        origin.get("pre_model_digest") != parent_digest
                        or origin_tick <= parent_tick
                        or (
                            "learning_tick" in manifest
                            and manifest.get("learning_tick") != origin_tick
                        )
                        or qualification is None
                        or qualification.get("candidate_model_digest")
                        != model_digest
                        or qualification.get("qualified") is not True
                        or owners["qualification_receipts"].get(
                            str(qualification_id)
                        )
                        != origin.get("commit_receipt_id")
                    ):
                        raise PersistenceError("model creation lineage is invalid")
                visiting_models.remove(model_digest)
                validated_models.add(model_digest)
                return origin_tick

            for model_digest in model_manifests:
                validate_model(model_digest)

            state_rows = self._connection.execute(
                "SELECT state_digest, state_version, parent_state_digest, payload_json "
                "FROM state_versions ORDER BY state_version"
            ).fetchall()
            for row in state_rows:
                payload = json.loads(row["payload_json"])
                declared = payload.get("state_digest")
                if declared is not None and declared != row["state_digest"]:
                    return False
                if "version" in payload and payload["version"] != row["state_version"]:
                    return False
                if "state_version" in payload and payload["state_version"] != row["state_version"]:
                    return False
                if row["parent_state_digest"] is not None:
                    parent = self._connection.execute(
                        "SELECT state_version FROM state_versions WHERE state_digest = ?",
                        (row["parent_state_digest"],),
                    ).fetchone()
                    if parent is None or parent["state_version"] >= row["state_version"]:
                        return False

            artifact_payload_rows: list[sqlite3.Row] = []
            for table in (
                "state_versions",
                "model_versions",
                "trace_events",
                "commit_receipts",
                *identity_fields.keys(),
            ):
                artifact_payload_rows.extend(
                    self._connection.execute(f"SELECT payload_json FROM {table}").fetchall()
                )
            for row in artifact_payload_rows:
                for artifact_id, digest in _artifact_references(json.loads(row["payload_json"])):
                    if not self.has_artifact(artifact_id, digest):
                        return False
            head = self.head
            if events:
                if head.trace_digest != events[-1]["trace_digest"]:
                    return False
                if head.commit_receipt_id != events[-1].get("commit_receipt_id"):
                    return False
                if head.state_digest != events[-1]["post_state_digest"]:
                    return False
            elif head.trace_digest is not None:
                return False
            state_row = self._connection.execute(
                "SELECT state_version FROM state_versions WHERE state_digest = ?",
                (head.state_digest,),
            ).fetchone()
            if state_row is None or state_row["state_version"] != head.state_version:
                return False
            if head.model_digest is not None:
                model_row = self._connection.execute(
                    "SELECT 1 FROM model_versions WHERE model_digest = ?",
                    (head.model_digest,),
                ).fetchone()
                if model_row is None:
                    return False
            return True
        except (
            ArtifactError,
            json.JSONDecodeError,
            PersistenceError,
            sqlite3.DatabaseError,
            TypeError,
            ValueError,
        ):
            return False


__all__ = [
    "STORE_SCHEMA_VERSION",
    "ActiveHead",
    "AtomicWriteSet",
    "IdempotencyConflict",
    "InjectedFailure",
    "ModelVersionWrite",
    "PersistenceError",
    "SQLiteAtomicStore",
    "StaleHeadError",
    "StoredDocument",
]
