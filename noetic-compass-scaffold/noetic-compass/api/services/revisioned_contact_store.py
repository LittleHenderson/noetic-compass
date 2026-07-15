"""Shared-StateStore persistence for revisioned customer-contact records.

CRM leads and support tickets both have a domain-level ``version``.  A plain
StateStore upsert would preserve only the latest payload and would therefore
discard the append-only history currently present in their JSONL stores.  This
adapter keeps two rows per domain object shape instead:

* one immutable row per domain revision; and
* one optimistic-concurrency-controlled head row pointing at the latest revision.

The StateStore's version is deliberately independent from the domain version.
Short, per-object leases serialize read/transition/write operations across API
replicas, while ``expected_version`` remains the final lost-update defence.  This
is shared-state plumbing, not an HA claim: replica count, rolling deploys, load,
and provider failover still require separate hosted proof.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import math
import time
from typing import Callable, Generic, Iterator, Mapping, TypeVar
from uuid import uuid4

from api.services.production.state_substrate import (
    LedgerRecord,
    LeaseHeld,
    StateStore,
    StateStoreError,
    VersionConflict,
)


CONTACT_STATE_TENANT = "__cas_customer_operations__"
CONTACT_MIGRATION_KIND = "contact_jsonl_migration"
CONTACT_MIGRATION_SCHEMA_VERSION = "cas_contact_jsonl_migration.v1"

_HEAD_FIELDS = frozenset(
    {
        "schema_version",
        "item_id",
        "domain_version",
        "revision_record_id",
        "content_sha256",
        "item",
    }
)
_MIGRATION_FIELDS = frozenset(
    {
        "schema_version",
        "domain",
        "source_present",
        "source_sha256",
        "line_count",
        "revision_count",
        "head_count",
        "records_sha256",
    }
)
_WRITE_RETRIES = 8
_LEASE_ATTEMPTS = 100
_LEASE_RETRY_SECONDS = 0.005
_LEASE_TTL_SECONDS = 30.0


class RevisionedContactStoreError(StateStoreError):
    """A contact-domain record or migration failed its integrity contract."""


class DomainRevisionConflict(RevisionedContactStoreError):
    """One immutable domain revision was presented with different content."""


T = TypeVar("T")


class _StrictJsonDecodeError(ValueError):
    """A JSON token is valid under Python extensions but invalid for migration."""


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise _StrictJsonDecodeError("a duplicate JSON key")
        value[key] = item
    return value


def _reject_nonfinite_json_constant(value: str) -> object:
    raise _StrictJsonDecodeError(f"a non-finite JSON constant {value}")


def _strict_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise _StrictJsonDecodeError("a non-finite JSON number")
    return parsed


def canonical_json(value: object) -> str:
    """Return the exact, type-preserving canonical JSON projection."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RevisionedContactStoreError(
            "contact record is not strict JSON"
        ) from exc


def content_sha256(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_json(dict(payload)).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class JsonlSource(Generic[T]):
    present: bool
    raw_sha256: str
    line_count: int
    items: tuple[T, ...]


class RevisionedContactStateStore(Generic[T]):
    """Immutable-revision + OCC-head adapter over one shared ``StateStore``."""

    def __init__(
        self,
        store: StateStore,
        *,
        domain: str,
        encode: Callable[[T], Mapping[str, object]],
        decode: Callable[[Mapping[str, object]], T],
        item_id: Callable[[T], str],
        item_version: Callable[[T], int],
        sort_key: Callable[[T], object],
        transition_validator: Callable[[T | None, T], None] | None = None,
    ) -> None:
        if not domain or not domain.replace("_", "").isalnum():
            raise ValueError("contact domain must contain only letters, digits, and underscores")
        self.state_store = store
        self.domain = domain
        self.head_kind = f"{domain}_head"
        self.revision_kind = f"{domain}_revision"
        self._head_schema = f"cas_{domain}_head.v1"
        self._revision_schema = f"cas_{domain}_revision.v1"
        self._encode = encode
        self._decode = decode
        self._item_id = item_id
        self._item_version = item_version
        self._sort_key = sort_key
        self._transition_validator = transition_validator

    def save(self, item: T) -> T:
        item_id, _, _ = self._validated_item(item)
        with self._exclusive(item_id):
            return self._save_locked(item)

    def mutate(self, item_id: str, mutation: Callable[[T], T]) -> T | None:
        """Apply one domain transition against the fresh head under a lease."""

        with self._exclusive(item_id):
            current = self._get_head_item(item_id)
            if current is None:
                return None
            candidate = mutation(current)
            if self._item_id(candidate) != item_id:
                raise RevisionedContactStoreError(
                    f"{self.domain} mutation changed item identity"
                )
            return self._save_locked(candidate)

    def get(self, item_id: str) -> T | None:
        return self._get_head_item(item_id)

    def list_all(
        self, *, heartbeat: Callable[[bool], None] | None = None
    ) -> list[T]:
        if heartbeat is not None:
            heartbeat(True)
        records = self.state_store.list(CONTACT_STATE_TENANT, self.head_kind)
        if heartbeat is not None:
            heartbeat(True)
        items = [
            self._item_from_head_record_with_heartbeat(record, heartbeat)
            for record in records
        ]
        if heartbeat is not None:
            heartbeat(True)
        return sorted(items, key=self._sort_key, reverse=True)

    def list_revisions(self, item_id: str) -> list[T]:
        revisions: list[T] = []
        for record in self.state_store.list(
            CONTACT_STATE_TENANT, self.revision_kind
        ):
            item = self._item_from_revision_record(record)
            if self._item_id(item) == item_id:
                revisions.append(item)
        return sorted(revisions, key=self._item_version)

    def revision_map(
        self, *, heartbeat: Callable[[bool], None] | None = None
    ) -> dict[tuple[str, int], Mapping[str, object]]:
        result: dict[tuple[str, int], Mapping[str, object]] = {}
        if heartbeat is not None:
            heartbeat(True)
        records = self.state_store.list(CONTACT_STATE_TENANT, self.revision_kind)
        if heartbeat is not None:
            heartbeat(True)
        for record in records:
            if heartbeat is not None:
                heartbeat(False)
            item = self._item_from_revision_record(record)
            key = (self._item_id(item), self._item_version(item))
            payload = dict(self._encode(item))
            prior = result.get(key)
            if prior is not None and canonical_json(prior) != canonical_json(payload):
                raise DomainRevisionConflict(
                    f"{self.domain} destination contains conflicting revision {key!r}"
                )
            result[key] = payload
        if heartbeat is not None:
            heartbeat(True)
        return result

    def head_map(
        self, *, heartbeat: Callable[[bool], None] | None = None
    ) -> dict[str, Mapping[str, object]]:
        result: dict[str, Mapping[str, object]] = {}
        for item in self.list_all(heartbeat=heartbeat):
            if heartbeat is not None:
                heartbeat(False)
            result[self._item_id(item)] = dict(self._encode(item))
        return result

    def _save_locked(self, item: T) -> T:
        item_id, incoming_version, incoming_payload = self._validated_item(item)
        for _ in range(_WRITE_RETRIES):
            head_record = self.state_store.get(
                CONTACT_STATE_TENANT, self.head_kind, item_id
            )
            current = (
                None
                if head_record is None
                else self._item_from_head_record(head_record)
            )
            if current is not None:
                current_version = self._item_version(current)
                current_payload = dict(self._encode(current))
                if incoming_version < current_version:
                    return current
                if incoming_version == current_version:
                    if canonical_json(incoming_payload) == canonical_json(current_payload):
                        return current
                    raise DomainRevisionConflict(
                        f"{self.domain}/{item_id} revision {incoming_version} "
                        "already exists with different content"
                    )

            if self._transition_validator is not None:
                self._transition_validator(current, item)

            revision_id = self._revision_record_id(item_id, incoming_version)
            digest = content_sha256(incoming_payload)
            revision_payload = self._envelope(
                schema_version=self._revision_schema,
                item_id=item_id,
                domain_version=incoming_version,
                revision_record_id=revision_id,
                digest=digest,
                item_payload=incoming_payload,
            )
            self._ensure_revision(revision_id, revision_payload)

            head_payload = self._envelope(
                schema_version=self._head_schema,
                item_id=item_id,
                domain_version=incoming_version,
                revision_record_id=revision_id,
                digest=digest,
                item_payload=incoming_payload,
            )
            try:
                if head_record is None:
                    candidate = LedgerRecord.new(
                        tenant_id=CONTACT_STATE_TENANT,
                        kind=self.head_kind,
                        record_id=item_id,
                        payload=head_payload,
                        source=f"{self.domain}_state_store",
                    )
                    stored = self.state_store.put(candidate, expected_version=0)
                else:
                    stored = self.state_store.put(
                        head_record.with_payload(head_payload),
                        expected_version=head_record.version,
                    )
                return self._item_from_head_record(stored)
            except VersionConflict:
                # A non-cooperating writer raced the lease. Re-read and re-decide;
                # never blindly overwrite a head we did not observe.
                continue
        raise RevisionedContactStoreError(
            f"{self.domain}/{item_id} head remained contended after "
            f"{_WRITE_RETRIES} OCC attempts"
        )

    def _ensure_revision(
        self, revision_id: str, expected_payload: Mapping[str, object]
    ) -> None:
        existing = self.state_store.get(
            CONTACT_STATE_TENANT, self.revision_kind, revision_id
        )
        if existing is not None:
            if canonical_json(dict(existing.payload)) != canonical_json(
                dict(expected_payload)
            ):
                raise DomainRevisionConflict(
                    f"{self.domain} immutable revision {revision_id!r} conflicts"
                )
            self._item_from_revision_record(existing)
            return
        candidate = LedgerRecord.new(
            tenant_id=CONTACT_STATE_TENANT,
            kind=self.revision_kind,
            record_id=revision_id,
            payload=expected_payload,
            source=f"{self.domain}_state_store",
        )
        try:
            self.state_store.put(candidate, expected_version=0)
        except VersionConflict:
            raced = self.state_store.get(
                CONTACT_STATE_TENANT, self.revision_kind, revision_id
            )
            if raced is None or canonical_json(dict(raced.payload)) != canonical_json(
                dict(expected_payload)
            ):
                raise DomainRevisionConflict(
                    f"{self.domain} immutable revision {revision_id!r} raced "
                    "with different content"
                )

    def _get_head_item(self, item_id: str) -> T | None:
        record = self.state_store.get(
            CONTACT_STATE_TENANT, self.head_kind, item_id
        )
        return None if record is None else self._item_from_head_record(record)

    def _item_from_head_record(self, record: LedgerRecord) -> T:
        payload, item = self._validate_envelope(
            record, expected_schema=self._head_schema
        )
        revision_id = str(payload["revision_record_id"])
        revision = self.state_store.get(
            CONTACT_STATE_TENANT, self.revision_kind, revision_id
        )
        if revision is None:
            raise RevisionedContactStoreError(
                f"{self.domain} head {record.record_id!r} points to a missing revision"
            )
        revision_payload, revision_item = self._validate_envelope(
            revision, expected_schema=self._revision_schema
        )
        if (
            canonical_json(dict(revision_payload))
            != canonical_json(
                self._envelope(
                    schema_version=self._revision_schema,
                    item_id=str(payload["item_id"]),
                    domain_version=int(payload["domain_version"]),
                    revision_record_id=revision_id,
                    digest=str(payload["content_sha256"]),
                    item_payload=dict(payload["item"]),  # type: ignore[arg-type]
                )
            )
            or canonical_json(dict(self._encode(item)))
            != canonical_json(dict(self._encode(revision_item)))
        ):
            raise RevisionedContactStoreError(
                f"{self.domain} head {record.record_id!r} disagrees with its revision"
            )
        return item

    def _item_from_head_record_with_heartbeat(
        self,
        record: LedgerRecord,
        heartbeat: Callable[[bool], None] | None,
    ) -> T:
        if heartbeat is not None:
            heartbeat(False)
        item = self._item_from_head_record(record)
        if heartbeat is not None:
            heartbeat(False)
        return item

    def _item_from_revision_record(self, record: LedgerRecord) -> T:
        _, item = self._validate_envelope(
            record, expected_schema=self._revision_schema
        )
        return item

    def _validate_envelope(
        self, record: LedgerRecord, *, expected_schema: str
    ) -> tuple[Mapping[str, object], T]:
        payload = dict(record.payload)
        if set(payload) != _HEAD_FIELDS:
            raise RevisionedContactStoreError(
                f"{self.domain} persisted envelope fields drifted"
            )
        if payload.get("schema_version") != expected_schema:
            raise RevisionedContactStoreError(
                f"{self.domain} persisted envelope schema drifted"
            )
        item_payload = payload.get("item")
        if not isinstance(item_payload, Mapping):
            raise RevisionedContactStoreError(
                f"{self.domain} persisted item must be a JSON object"
            )
        item = self._decode(dict(item_payload))
        item_id, version, canonical_payload = self._validated_item(item)
        expected_revision_id = self._revision_record_id(item_id, version)
        if (
            payload.get("item_id") != item_id
            or type(payload.get("domain_version")) is not int
            or payload.get("domain_version") != version
            or payload.get("revision_record_id") != expected_revision_id
            or payload.get("content_sha256") != content_sha256(canonical_payload)
            or canonical_json(dict(item_payload)) != canonical_json(canonical_payload)
        ):
            raise RevisionedContactStoreError(
                f"{self.domain} persisted envelope does not match its item"
            )
        if expected_schema == self._head_schema:
            if record.kind != self.head_kind or record.record_id != item_id:
                raise RevisionedContactStoreError(
                    f"{self.domain} head record identity drifted"
                )
        else:
            if (
                record.kind != self.revision_kind
                or record.record_id != expected_revision_id
            ):
                raise RevisionedContactStoreError(
                    f"{self.domain} revision record identity drifted"
                )
        return payload, item

    def _validated_item(self, item: T) -> tuple[str, int, dict[str, object]]:
        item_id = self._item_id(item)
        version = self._item_version(item)
        if not isinstance(item_id, str) or not item_id:
            raise RevisionedContactStoreError(
                f"{self.domain} item id must be a non-empty string"
            )
        if type(version) is not int or version < 1:
            raise RevisionedContactStoreError(
                f"{self.domain} domain version must be a positive strict integer"
            )
        payload = dict(self._encode(item))
        canonical_json(payload)
        decoded = self._decode(payload)
        if canonical_json(dict(self._encode(decoded))) != canonical_json(payload):
            raise RevisionedContactStoreError(
                f"{self.domain} item does not round-trip canonically"
            )
        return item_id, version, payload

    def _revision_record_id(self, item_id: str, version: int) -> str:
        return f"{item_id}:v{version}"

    @staticmethod
    def _envelope(
        *,
        schema_version: str,
        item_id: str,
        domain_version: int,
        revision_record_id: str,
        digest: str,
        item_payload: Mapping[str, object],
    ) -> dict[str, object]:
        return {
            "schema_version": schema_version,
            "item_id": item_id,
            "domain_version": domain_version,
            "revision_record_id": revision_record_id,
            "content_sha256": digest,
            "item": dict(item_payload),
        }

    @contextmanager
    def _exclusive(self, item_id: str) -> Iterator[None]:
        resource_id = f"{self.domain}:{item_id}"
        holder = f"{self.domain}-{uuid4().hex}"
        lease = None
        for attempt in range(_LEASE_ATTEMPTS):
            try:
                lease = self.state_store.acquire_lease(
                    CONTACT_STATE_TENANT,
                    resource_id,
                    holder=holder,
                    ttl_seconds=_LEASE_TTL_SECONDS,
                )
                break
            except LeaseHeld as exc:
                if attempt + 1 == _LEASE_ATTEMPTS:
                    raise RevisionedContactStoreError(
                        f"{self.domain}/{item_id} is busy under another live lease"
                    ) from exc
                time.sleep(_LEASE_RETRY_SECONDS)
        if lease is None:  # pragma: no cover - loop invariant
            raise RevisionedContactStoreError(
                f"could not acquire {self.domain}/{item_id} lease"
            )
        try:
            yield
        finally:
            self.state_store.release_lease(lease.token)


def read_strict_jsonl(
    path: str,
    *,
    parser: Callable[[Mapping[str, object], int], T],
) -> JsonlSource[T]:
    """Read a JSONL source without the legacy stores' skip-corruption behavior."""

    from pathlib import Path

    source = Path(path)
    present = source.is_file()
    if source.exists() and not present:
        raise RevisionedContactStoreError(
            "configured contact JSONL migration source is not a regular file"
        )
    raw = source.read_bytes() if present else b""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RevisionedContactStoreError(
            "contact JSONL migration source is not UTF-8"
        ) from exc
    items: list[T] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise RevisionedContactStoreError(
                f"contact JSONL migration source has a blank line at {line_number}"
            )
        try:
            payload = json.loads(
                line,
                object_pairs_hook=_unique_json_object,
                parse_constant=_reject_nonfinite_json_constant,
                parse_float=_strict_json_float,
            )
        except json.JSONDecodeError as exc:
            raise RevisionedContactStoreError(
                f"contact JSONL migration source has invalid JSON at line {line_number}"
            ) from exc
        except _StrictJsonDecodeError as exc:
            raise RevisionedContactStoreError(
                f"contact JSONL migration source has {exc} at line {line_number}"
            ) from exc
        except ValueError as exc:
            raise RevisionedContactStoreError(
                f"contact JSONL migration source has invalid JSON at line {line_number}"
            ) from exc
        if not isinstance(payload, dict):
            raise RevisionedContactStoreError(
                f"contact JSONL migration line {line_number} is not an object"
            )
        try:
            items.append(parser(payload, line_number))
        except RevisionedContactStoreError:
            raise
        except Exception as exc:  # noqa: BLE001 - domain errors become migration errors
            raise RevisionedContactStoreError(
                f"contact JSONL migration line {line_number} is invalid"
            ) from exc
    return JsonlSource(
        present=present,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        line_count=len(items),
        items=tuple(items),
    )


class _MigrationLeaseHeartbeat:
    """Renew one migration lease during scans and long copy loops."""

    def __init__(self, store: StateStore, token: str) -> None:
        self._store = store
        self._token = token
        self._last_renewed = time.monotonic()
        self._interval_seconds = _LEASE_TTL_SECONDS / 3

    def renew(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_renewed < self._interval_seconds:
            return
        # LeaseExpired / UnknownLease / backend failure intentionally propagate.
        # Continuing after an unproved renewal would let a second replica own the
        # same cutover, so renewal failure is a fail-closed migration failure.
        self._store.renew_lease(
            self._token, ttl_seconds=_LEASE_TTL_SECONDS
        )
        self._last_renewed = time.monotonic()


def migrate_jsonl_once(
    source: JsonlSource[T],
    destination: RevisionedContactStateStore[T],
    *,
    migration_id: str,
) -> dict[str, object]:
    """Strict, idempotent one-time migration with exact destination parity."""

    source_revisions: dict[tuple[str, int], Mapping[str, object]] = {}
    source_heads: dict[str, Mapping[str, object]] = {}
    for item in source.items:
        item_id, version, payload = destination._validated_item(item)
        key = (item_id, version)
        prior = source_revisions.get(key)
        if prior is not None and canonical_json(prior) != canonical_json(payload):
            raise DomainRevisionConflict(
                f"{destination.domain} JSONL contains conflicting revision {key!r}"
            )
        source_revisions[key] = payload
        head = source_heads.get(item_id)
        if head is None or int(head["version"]) < version:
            source_heads[item_id] = payload

    records_digest = hashlib.sha256(
        canonical_json(
            [
                {
                    "item_id": key[0],
                    "domain_version": key[1],
                    "item": dict(source_revisions[key]),
                }
                for key in sorted(source_revisions)
            ]
        ).encode("utf-8")
    ).hexdigest()
    marker_payload: dict[str, object] = {
        "schema_version": CONTACT_MIGRATION_SCHEMA_VERSION,
        "domain": destination.domain,
        "source_present": source.present,
        "source_sha256": source.raw_sha256,
        "line_count": source.line_count,
        "revision_count": len(source_revisions),
        "head_count": len(source_heads),
        "records_sha256": records_digest,
    }
    if set(marker_payload) != _MIGRATION_FIELDS:  # pragma: no cover - constant invariant
        raise AssertionError("contact migration marker schema drifted")

    existing_marker = destination.state_store.get(
        CONTACT_STATE_TENANT, CONTACT_MIGRATION_KIND, migration_id
    )
    if existing_marker is not None:
        _verify_marker(existing_marker, marker_payload, migration_id)
        return {"already_completed": True, **marker_payload}

    holder = f"contact-migration-{uuid4().hex}"
    resource_id = f"contact-migration:{migration_id}"
    lease = None
    for attempt in range(_LEASE_ATTEMPTS):
        try:
            lease = destination.state_store.acquire_lease(
                CONTACT_STATE_TENANT,
                resource_id,
                holder=holder,
                ttl_seconds=_LEASE_TTL_SECONDS,
            )
            break
        except LeaseHeld as exc:
            if attempt + 1 == _LEASE_ATTEMPTS:
                raise RevisionedContactStoreError(
                    f"contact migration {migration_id!r} is already running"
                ) from exc
            time.sleep(_LEASE_RETRY_SECONDS)
    if lease is None:  # pragma: no cover - loop invariant
        raise RevisionedContactStoreError("could not acquire contact migration lease")

    heartbeat = _MigrationLeaseHeartbeat(destination.state_store, lease.token)
    primary_failed = False
    try:
        heartbeat.renew(True)
        raced_marker = destination.state_store.get(
            CONTACT_STATE_TENANT, CONTACT_MIGRATION_KIND, migration_id
        )
        heartbeat.renew(True)
        if raced_marker is not None:
            _verify_marker(raced_marker, marker_payload, migration_id)
            return {"already_completed": True, **marker_payload}

        destination_revisions = destination.revision_map(
            heartbeat=heartbeat.renew
        )
        for key, payload in destination_revisions.items():
            heartbeat.renew(False)
            expected = source_revisions.get(key)
            if expected is None or canonical_json(expected) != canonical_json(payload):
                raise RevisionedContactStoreError(
                    f"{destination.domain} destination contains a revision outside "
                    "the unmarked JSONL source"
                )
        destination_heads = destination.head_map(heartbeat=heartbeat.renew)
        for item_id, payload in destination_heads.items():
            heartbeat.renew(False)
            version = payload.get("version")
            key = (item_id, version) if type(version) is int else None
            expected = None if key is None else source_revisions.get(key)
            if expected is None or canonical_json(expected) != canonical_json(payload):
                raise RevisionedContactStoreError(
                    f"{destination.domain} destination head conflicts with the "
                    "unmarked JSONL source"
                )

        for item in source.items:
            # Give every revision copy a fresh full TTL. Migration is one-time;
            # the extra renewal round-trip is preferable to entering a write with
            # only the tail of a lease remaining.
            heartbeat.renew(True)
            destination.save(item)
            heartbeat.renew(False)

        heartbeat.renew(True)
        if (
            {
                key: canonical_json(value)
                for key, value in destination.revision_map(
                    heartbeat=heartbeat.renew
                ).items()
            }
            != {
                key: canonical_json(value) for key, value in source_revisions.items()
            }
            or {
                key: canonical_json(value)
                for key, value in destination.head_map(
                    heartbeat=heartbeat.renew
                ).items()
            }
            != {key: canonical_json(value) for key, value in source_heads.items()}
        ):
            raise RevisionedContactStoreError(
                f"{destination.domain} migration destination parity failed"
            )

        heartbeat.renew(True)
        marker = LedgerRecord.new(
            tenant_id=CONTACT_STATE_TENANT,
            kind=CONTACT_MIGRATION_KIND,
            record_id=migration_id,
            payload=marker_payload,
            source="contact_jsonl_migration",
        )
        try:
            destination.state_store.put(marker, expected_version=0)
        except VersionConflict:
            raced = destination.state_store.get(
                CONTACT_STATE_TENANT, CONTACT_MIGRATION_KIND, migration_id
            )
            if raced is None:
                raise RevisionedContactStoreError(
                    "contact migration marker raced but cannot be read"
                )
            _verify_marker(raced, marker_payload, migration_id)
        return {"already_completed": False, **marker_payload}
    except BaseException:
        primary_failed = True
        raise
    finally:
        try:
            destination.state_store.release_lease(lease.token)
        except StateStoreError:
            # An expired/superseded token is secondary if the migration already
            # failed. Preserve the renewal/parity error that explains why the
            # cutover stopped. With no primary error, cleanup failure is itself
            # surfaced rather than silently claiming a clean handoff.
            if not primary_failed:
                raise


def _verify_marker(
    marker: LedgerRecord,
    expected_payload: Mapping[str, object],
    migration_id: str,
) -> None:
    if (
        marker.tenant_id != CONTACT_STATE_TENANT
        or marker.kind != CONTACT_MIGRATION_KIND
        or marker.record_id != migration_id
        or set(marker.payload) != _MIGRATION_FIELDS
        or canonical_json(dict(marker.payload)) != canonical_json(dict(expected_payload))
    ):
        raise RevisionedContactStoreError(
            f"contact migration marker {migration_id!r} does not match the JSONL source"
        )
