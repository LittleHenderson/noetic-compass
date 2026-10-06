"""History — the organism's accepted event stream, saved, restored, and verified before it answers.

This is the smallest canonical path the reuse audit recommends and the memory
contract v1 specifies (`docs/working/helm_reuse_audit_2026_10_06.md` §7,
`docs/working/helm_memory_contract_v1_draft_2026_10_06.md` M1, M2, M4, M9,
M10.3): keep `Organism.consume` as the single writer; write one history
document per stream following the CNCM native recovery's write discipline by
reference (temp file beside the target, flush, fsync, atomic replace, fsync the
directory, read back and verify); restore by replaying the rows through a
fresh organism and refusing to serve until the rebuilt state's digest, the
heartbeat audit and the identity all check. Nothing here is a framework. A
`Stream` is a thin owner around one `Organism`, and a history document with no
reader is inert data.

What this module is allowed to claim (contract M0.1, owner decision 1):

    survival level (a)   the accepted state survives a clean process exit and a
                         restart on the same machine. This is what the tests
                         demonstrate, in a fresh operating-system process.
    survival level (b)   survival of machine termination and replacement. NOT
                         demonstrated here; it needs the authorized storage
                         arrangement identified and an actual replacement run.

Everything the organism holds is a deterministic function of the identity
record (constructor arguments and world mode) and the ordered events (audit
§3), beat count included, so the document stores exactly those plus a
reference digest of the rebuilt state. The digest covers propositions,
standing conclusions, the clock and the counters; it deliberately excludes
the memory board's charge and the motivation levels, which are path-dependent
diagnostics (contract M12a item 5).

Refusal codes:
    E-MEM-001  identity mismatch on restore (a record from one context must
               never answer for another)
    E-MEM-002  stale expected version on a mutation
    E-MEM-003  same event id, different payload
    E-MEM-010  schema or engine version the running code cannot read
    E-MEM-040  the document read back after writing does not match
    E-MEM-041  a row out of sequence (quarantined; restore stops)
    E-MEM-042  replaying a row produced a different outcome than recorded
    E-MEM-043  the rebuilt state's reference digest differs from the footer's
    E-MEM-044  the heartbeat audit faulted at restore
    E-MEM-045  no document verifies; nothing can be served
    E-MEM-050  a retention limit was reached; the stream stops safely, state unchanged
    E-MEM-051  too little free space to save safely
    E-MEM-052  the dedicated remote location refused the document (the local one stands;
               the commit is NOT acknowledged at level (b))
    E-MEM-053  the remote location holds no verifying document for the stream

Survival level (b) is reached through `mirror`: an object store (an `S3Prefix`
on the owner's dedicated AWS location, or a `DirectoryStore` standing in for it
offline) that receives every sealed document after the local write, and from
which `Stream.restore_from` rebuilds the stream on a machine that has none of
the local state. The claim each test makes is written in its name.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ccb_r1"))

import ablations  # noqa: E402
from events import Event, EventKind  # noqa: E402
from foundations import Drive, FoundationProfile, Register  # noqa: E402
from organism import Heartbeat, Organism, Response  # noqa: E402
from workspace import ASSERTIVE, Workspace  # noqa: E402

SCHEMA_VERSION = "helm.memory/1.0"
SEMANTICS_VERSION = "revision-streams-2026-10-06+memory-v1"
PROJECT_ID = "noetic-compass"
TRUNK = "trunk"

#: Bounded initial limits, set before the first run (owner decision 3). When one
#: is reached the stream stops safely and reports it; nothing is discarded.
MAX_HISTORY_EVENTS = 4096
MAX_HISTORY_BYTES = 8 * 1024 * 1024
MAX_RETAINED_DOCUMENTS = 8
MIN_RETAINED_DOCUMENTS = 2
MIN_FREE_BYTES = 64 * 1024 * 1024
ROW_HEADROOM_BYTES = 8 * 1024

CURRENT = "history.current.json"
ARCHIVE = "archive"

_SEGMENT_OK = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.:-")


class MemoryError_(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# ---------------------------------------------------------------------------
# canonical bytes and digests
# ---------------------------------------------------------------------------

def canonical_json(obj) -> bytes:
    """Sorted keys, compact separators, no non-finite numbers. The one helper."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(obj) -> str:
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def engine_version() -> str:
    """Digest of the package sources the organism's behaviour depends on.

    A source digest subsumes both the commit and the explicit constants the
    contract lists (M1.1): any change to either changes it. Two processes
    agree on it iff they run the same code.
    """
    root = Path(__file__).resolve().parents[1]
    parts = []
    for folder in ("cas_rpu", "ccb_r1"):
        for path in sorted((root / folder).glob("*.py")):
            parts.append({"file": f"{folder}/{path.name}", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return digest(parts)


def _check_segment(name: str, value: str) -> str:
    if not value or len(value) > 128 or value[0] not in _SEGMENT_OK - set(".:-") or any(c not in _SEGMENT_OK for c in value):
        raise MemoryError_("E-MEM-001", f"{name} {value!r} is not a valid identifier segment")
    return value


def profile_to_dict(profile: FoundationProfile) -> dict:
    return {
        "g": {d.value: profile.g[d] for d in Drive},
        "q": {d.value: {r.value: profile.q[d][r] for r in Register} for d in Drive},
    }


def profile_from_dict(data: dict) -> FoundationProfile:
    return FoundationProfile(
        g={Drive(k): float(v) for k, v in data["g"].items()},
        q={Drive(k): {Register(r): float(v) for r, v in regs.items()} for k, regs in data["q"].items()},
    )


def _factory_name(factory: type) -> str:
    return factory.__name__


def _factory_from_name(name: str) -> type:
    if name == "Workspace":
        return Workspace
    candidate = getattr(ablations, name, None)
    if isinstance(candidate, type) and issubclass(candidate, Workspace):
        return candidate
    raise MemoryError_("E-MEM-010", f"unknown workspace factory {name!r}")


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Identity:
    """The stream identity record (contract M1.1). Written once; compared on every restore."""

    organism_id: str
    context_id: str
    world_mode: str
    constructor_args: dict
    project_id: str = PROJECT_ID
    branch_id: str = TRUNK
    schema_version: str = SCHEMA_VERSION
    semantics_version: str = SEMANTICS_VERSION
    engine_version: str = field(default_factory=engine_version)

    def __post_init__(self) -> None:
        for name in ("project_id", "organism_id", "context_id", "branch_id"):
            _check_segment(name, getattr(self, name))
        if self.world_mode not in ("open", "closed"):
            raise MemoryError_("E-MEM-001", f"world_mode must be open or closed, not {self.world_mode!r}")

    @property
    def stream_id(self) -> str:
        return ".".join((self.project_id, self.organism_id, self.context_id, self.branch_id))

    @property
    def closed_world(self) -> bool:
        return self.world_mode == "closed"

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "organism_id": self.organism_id,
            "context_id": self.context_id,
            "branch_id": self.branch_id,
            "stream_id": self.stream_id,
            "world_mode": self.world_mode,
            "constructor_args": self.constructor_args,
            "schema_version": self.schema_version,
            "semantics_version": self.semantics_version,
            "engine_version": self.engine_version,
        }

    @property
    def genesis_digest(self) -> str:
        return digest(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "Identity":
        return cls(
            organism_id=data["organism_id"],
            context_id=data["context_id"],
            world_mode=data["world_mode"],
            constructor_args=data["constructor_args"],
            project_id=data["project_id"],
            branch_id=data["branch_id"],
            schema_version=data["schema_version"],
            semantics_version=data["semantics_version"],
            engine_version=data["engine_version"],
        )

    def same_stream(self, other: "Identity") -> list[str]:
        """Field names that differ. Compared one by one; a hash alone does not authenticate."""
        fields = ("project_id", "organism_id", "context_id", "branch_id", "world_mode", "constructor_args")
        return [f for f in fields if getattr(self, f) != getattr(other, f)]


def build_organism(identity: Identity) -> Organism:
    args = identity.constructor_args
    return Organism(
        profile=profile_from_dict(args["profile"]) if args.get("profile") else None,
        closed_world=identity.closed_world,
        processor_kwargs=args.get("processor_kwargs") or None,
        motivation_kwargs=args.get("motivation_kwargs") or None,
        workspace_factory=_factory_from_name(args.get("workspace_factory", "Workspace")),
        record_first=bool(args.get("record_first", False)),
        record_invalidation=args.get("record_invalidation", "context"),
    )


# ---------------------------------------------------------------------------
# what is digested, what is recorded
# ---------------------------------------------------------------------------

def reference_digest(organism: Organism) -> str:
    """Digest of the rebuilt state (contract M4.4, M12a item 5).

    Propositions with status, support, stage and polarity; standing
    conclusions; clock; counters; beats; world. Not the memory board's charge
    and not the motivation levels: a fast-path hit would not LEARN, so those
    are path-dependent by design and are reported as diagnostics instead.
    """
    props = [
        {
            "pid": p.pid, "status": p.status.value, "support": list(p.support),
            "stage": p.stage, "negated": p.negated, "cas": p.cas,
        }
        for p in sorted(organism.ws.props.values(), key=lambda p: p.pid)
    ]
    return digest({
        "props": props,
        "standing": dict(sorted(organism.standing.items())),
        "clock": organism.clock,
        "asks_made": organism.asks_made,
        "reasks_made": organism.reasks_made,
        "beats": organism.heartbeat.beats,
        "closed_world": organism.ws.closed_world,
    })


def outcome_projection(response: Response) -> dict:
    """The part of a Response that a replay must reproduce exactly (contract M2.2)."""
    return {
        "accepted": response.accepted,
        "code": response.code,
        "verdict": response.verdict,
        "lacunae": list(response.lacunae),
        "contested": list(response.contested),
        "withdrawn": list(response.withdrawn),
        "satisfied": list(response.satisfied),
        "resolved": len(response.resolved),
        "beat_no": response.beat.beat_no,
        "faults": len(response.beat.faults),
        "route": response.route,
    }


def event_id(stream_id: str, seq: int, event: Event) -> str:
    return digest({"stream_id": stream_id, "seq": seq, "event": event.canonical()})


def _event_from_canonical(data: dict) -> Event:
    return Event(EventKind(data["kind"]), data["subject"], data["obj"], data["relation"])


# ---------------------------------------------------------------------------
# the stream: one organism, one writer, one document
# ---------------------------------------------------------------------------

class Stream:
    """One authoritative stream: an `Organism`, its identity, its history document.

    `commit(event)` is the only way an event reaches the organism through this
    module; it is the single writer the contract requires (M6.1). Every commit
    ends with a complete, digest-sealed document on disk, read back and
    verified, before it is acknowledged (M9.1).
    """

    def __init__(
        self,
        identity: Identity,
        organism: Organism,
        directory: Path | str,
        *,
        rows: list[dict] | None = None,
        max_events: int = MAX_HISTORY_EVENTS,
        max_bytes: int = MAX_HISTORY_BYTES,
        max_retained: int = MAX_RETAINED_DOCUMENTS,
        min_free_bytes: int = MIN_FREE_BYTES,
        mirror=None,
    ) -> None:
        self.mirror = mirror
        self.identity = identity
        self.organism = organism
        self.directory = Path(directory)
        self.rows: list[dict] = list(rows or [])
        self.max_events = max_events
        self.max_bytes = max_bytes
        self.max_retained = max_retained
        self.min_free_bytes = min_free_bytes
        self._responses: dict[str, Response] = {}
        self.stopped: str | None = None

    # ---- genesis ------------------------------------------------------------

    @classmethod
    def genesis(
        cls,
        directory: Path | str,
        *,
        organism_id: str,
        context_id: str,
        closed_world: bool = False,
        profile: FoundationProfile | None = None,
        processor_kwargs: dict | None = None,
        motivation_kwargs: dict | None = None,
        workspace_factory: type = Workspace,
        record_first: bool = False,
        record_invalidation: str = "context",
        project_id: str = PROJECT_ID,
        branch_id: str = TRUNK,
        **limits,
    ) -> "Stream":
        identity = Identity(
            organism_id=organism_id,
            context_id=context_id,
            world_mode="closed" if closed_world else "open",
            constructor_args={
                "profile": profile_to_dict(profile) if profile is not None else None,
                "processor_kwargs": processor_kwargs or {},
                "motivation_kwargs": motivation_kwargs or {},
                "workspace_factory": _factory_name(workspace_factory),
                "record_first": record_first,
                "record_invalidation": record_invalidation,
            },
            project_id=project_id,
            branch_id=branch_id,
        )
        stream = cls(identity, build_organism(identity), directory, **limits)
        stream.directory.mkdir(parents=True, exist_ok=True)
        stream.save()
        return stream

    @property
    def last_committed_seq(self) -> int:
        return self.rows[-1]["seq"] if self.rows else -1

    # ---- commit -------------------------------------------------------------

    def commit(self, event: Event, *, source: str = "host", expected_version: int | None = None) -> Response:
        """Apply one event through the single writer and seal the document.

        Order (contract M9.1): version check; assign seq and id; retry
        detection; limit check (before anything changes); consume; record the
        row; save and verify; acknowledge. A failure before `consume` leaves
        the organism untouched; a failure in `save` leaves the previous
        document standing and the in-memory organism discarded by the caller
        (the stream marks itself stopped).
        """
        if self.stopped:
            raise MemoryError_("E-MEM-050", f"stream stopped: {self.stopped}")
        if expected_version is not None and expected_version != self.last_committed_seq and event.kind is not EventKind.ASK:
            raise MemoryError_(
                "E-MEM-002",
                f"expected version {expected_version} but the stream is at {self.last_committed_seq}",
            )
        seq = self.organism.clock
        eid = event_id(self.identity.stream_id, seq, event)
        for row in self.rows:
            if row["event_id"] == eid:
                if row["payload"] != event.canonical():
                    raise MemoryError_("E-MEM-003", f"event id {eid[:12]} already recorded with a different payload")
                return self._responses[eid]           # lost-ack retry: exactly once
        if len(self.rows) + 1 > self.max_events:
            self.stopped = f"MAX_HISTORY_EVENTS={self.max_events} reached at seq {seq}"
            raise MemoryError_("E-MEM-050", self.stopped)
        if self._current_bytes() + ROW_HEADROOM_BYTES > self.max_bytes:
            self.stopped = f"MAX_HISTORY_BYTES={self.max_bytes} would be exceeded at seq {seq}"
            raise MemoryError_("E-MEM-050", self.stopped)

        response = self.organism.consume(event)
        self.rows.append({
            "seq": seq,
            "event_id": eid,
            "type": event.kind.value.upper(),
            "payload": event.canonical(),
            "polarity": "-" if event.kind is EventKind.NEGATION else "+",
            "source": source,
            "expected_version": expected_version if expected_version is not None else seq - 1,
            "commit_status": "ACCEPTED" if response.accepted else "REFUSED",
            "refusal_code": response.code,
            "outcome": outcome_projection(response),
        })
        self._responses[eid] = response
        self.save()
        return response

    def run(self, events) -> list[Response]:
        return [self.commit(e) for e in events]

    # ---- the document -------------------------------------------------------

    def document(self) -> dict:
        header = dict(self.identity.to_dict())
        header["last_committed_seq"] = self.last_committed_seq
        header["genesis_digest"] = self.identity.genesis_digest
        header["writer"] = "cas_rpu.history.Stream"
        body = {"header": header, "rows": self.rows, "reference_digest": reference_digest(self.organism)}
        return {**body, "document_digest": digest(body)}

    def _current_bytes(self) -> int:
        current = self.directory / CURRENT
        return current.stat().st_size if current.exists() else 0

    def save(self) -> Path:
        """Write the whole document atomically, read it back, verify, retain the previous.

        By reference to the CNCM native recovery's write path, with the two
        steps the audit found missing added: fsync of the directory and a
        read-back of what was written. The previous document is kept as
        `history.<seq>.json`; copies beyond the retention bound are moved to
        `archive/`, never deleted by code.
        """
        self.directory.mkdir(parents=True, exist_ok=True)
        doc = self.document()
        data = canonical_json(doc)
        if len(data) > self.max_bytes:
            self.stopped = f"MAX_HISTORY_BYTES={self.max_bytes} exceeded by the document ({len(data)} bytes)"
            raise MemoryError_("E-MEM-050", self.stopped)
        free = shutil.disk_usage(self.directory).free
        need = max(self.min_free_bytes, 10 * len(data))
        if free < need:
            raise MemoryError_("E-MEM-051", f"{free} bytes free; {need} needed to save safely")

        target = self.directory / CURRENT
        retained = self.directory / f"history.{len(self.rows):08d}.json"   # numbered by rows committed
        tmp = self.directory / f".{CURRENT}.tmp"
        with open(tmp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
        self._fsync_dir()
        read_back = target.read_bytes()
        if hashlib.sha256(read_back).hexdigest() != hashlib.sha256(data).hexdigest():
            raise MemoryError_("E-MEM-040", "the document read back differs from what was written")
        shutil.copyfile(target, retained)
        self._fsync_dir()
        self._prune_retained()
        if self.mirror is not None:
            self._mirror(data, retained.name)
        return target

    def _remote_name(self, name: str) -> str:
        return f"{self.identity.stream_id}/{name}"

    def _mirror(self, data: bytes, retained_name: str) -> None:
        """Put the sealed document in the dedicated remote location, current and retained.

        The remote put happens after the local write succeeds, and the store's
        own read-back verifies it. A refusal leaves the local document standing
        and raises E-MEM-052: the commit is acknowledged at level (a) only, and
        the next commit rewrites the whole document, so a transient refusal is
        healed by the next successful save.
        """
        try:
            self.mirror.put(self._remote_name(retained_name), data)
            self.mirror.put(self._remote_name(CURRENT), data)
        except Exception as exc:  # the store raises its own typed error; name it, never swallow it
            raise MemoryError_("E-MEM-052", f"{getattr(self.mirror, 'describe', lambda: 'remote')()} refused: {exc}") from exc

    def _fsync_dir(self) -> None:
        fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _retained(self) -> list[Path]:
        return sorted(p for p in self.directory.glob("history.*.json") if p.name != CURRENT)

    def _prune_retained(self) -> None:
        retained = self._retained()
        excess = len(retained) - self.max_retained
        if excess <= 0:
            return
        archive = self.directory / ARCHIVE
        archive.mkdir(exist_ok=True)
        for path in retained[:excess]:
            os.replace(path, archive / path.name)

    # ---- restore ------------------------------------------------------------

    @classmethod
    def restore(
        cls,
        directory: Path | str,
        *,
        expected: Identity | None = None,
        reference=None,
        **limits,
    ) -> "Stream":
        """Rebuild the organism from the newest verifying document and check it before serving.

        Contract M9.3: open and verify the document digest (falling back to
        retained copies); verify identity field by field; construct; replay in
        order, refusing out-of-sequence rows and comparing every outcome to the
        recorded one; verify the reference digest; run the heartbeat audit now,
        not at the next beat; confirm every standing conclusion is assertive.
        Only then is the stream returned. `reference`, if given, is a callable
        `(events, closed_world) -> run` with `.answers` (a control), compared on
        every ASK row.
        """
        directory = Path(directory)
        doc = cls._open_verified(directory)
        header = doc["header"]
        if header["schema_version"] != SCHEMA_VERSION:
            raise MemoryError_("E-MEM-010", f"schema {header['schema_version']!r} is not {SCHEMA_VERSION}")
        identity = Identity.from_dict(header)
        if identity.engine_version != engine_version():
            raise MemoryError_("E-MEM-010", "the document was written by different engine code")
        if expected is not None:
            differing = expected.same_stream(identity)
            if differing:
                raise MemoryError_("E-MEM-001", f"identity differs on {', '.join(differing)}")

        organism = build_organism(identity)
        rows = doc["rows"]
        seen: set[str] = set()
        responses: dict[str, Response] = {}
        for row in rows:
            if row["event_id"] in seen:
                continue                                  # duplicate delivery is harmless
            if row["seq"] != organism.clock:
                raise MemoryError_("E-MEM-041", f"row seq {row['seq']} out of order at clock {organism.clock}; quarantined")
            event = _event_from_canonical(row["payload"])
            if event_id(identity.stream_id, row["seq"], event) != row["event_id"]:
                raise MemoryError_("E-MEM-003", f"row {row['seq']}: event id does not match its payload")
            response = organism.consume(event)
            if outcome_projection(response) != row["outcome"]:
                raise MemoryError_(
                    "E-MEM-042",
                    f"row {row['seq']} ({event}) replayed to {outcome_projection(response)} but was recorded as {row['outcome']}",
                )
            seen.add(row["event_id"])
            responses[row["event_id"]] = response

        if reference_digest(organism) != doc["reference_digest"]:
            raise MemoryError_("E-MEM-043", "the rebuilt state does not match the document's reference digest")
        faults = Heartbeat.audit(organism)
        if faults:
            raise MemoryError_("E-MEM-044", "; ".join(faults))
        for pid in organism.standing:
            if organism.ws.props[pid].status not in ASSERTIVE:
                raise MemoryError_("E-MEM-044", f"standing conclusion {pid} is not assertive after restore")
        if reference is not None:
            events = [_event_from_canonical(r["payload"]) for r in rows]
            run = reference(events, identity.closed_world)
            asks = [r for r in rows if r["type"] == "ASK"]
            for row, answer in zip(asks, run.answers):
                if row["outcome"]["verdict"] != answer.verdict:
                    raise MemoryError_(
                        "E-MEM-042",
                        f"row {row['seq']}: recorded {row['outcome']['verdict']} but the reference says {answer.verdict}",
                    )

        stream = cls(identity, organism, directory, rows=rows, **limits)
        stream._responses = responses
        return stream

    @classmethod
    def restore_from(cls, store, stream_id: str, directory: Path | str, *, expected: Identity | None = None, reference=None, **limits) -> "Stream":
        """Rebuild a stream on a machine that has none of its local state.

        Every document the remote holds for `stream_id` is fetched into a fresh
        local directory, then the ordinary `restore` runs with all its checks
        (digest, identity, replay, audit). The restored stream keeps `store` as
        its mirror, so its next commit goes to the same location.
        """
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        names = [n for n in store.list() if n.startswith(stream_id + "/")]
        if not names:
            raise MemoryError_("E-MEM-053", f"{store.describe()} holds nothing for stream {stream_id}")
        for name in names:
            local = directory / name.split("/", 1)[1]
            local.write_bytes(store.get(name))
        stream = cls.restore(directory, expected=expected, reference=reference, **limits)
        stream.mirror = store
        return stream

    @classmethod
    def _open_verified(cls, directory: Path) -> dict:
        candidates = [directory / CURRENT] + sorted(
            (p for p in directory.glob("history.*.json") if p.name != CURRENT), reverse=True
        )
        failures: list[str] = []
        for path in candidates:
            if not path.exists():
                continue
            try:
                doc = json.loads(path.read_bytes(), parse_constant=_refuse_constant)
                body = {k: v for k, v in doc.items() if k != "document_digest"}
                if digest(body) != doc.get("document_digest"):
                    failures.append(f"{path.name}: document digest mismatch")
                    continue
                return doc
            except (ValueError, KeyError, TypeError) as exc:
                failures.append(f"{path.name}: {exc}")
        raise MemoryError_("E-MEM-045", "no document verifies: " + ("; ".join(failures) or "none found"))

    # ---- inspection ---------------------------------------------------------

    def report(self) -> str:
        lines = [
            f"stream     {self.identity.stream_id} ({self.identity.world_mode} world)",
            f"committed  {self.last_committed_seq + 1} row(s); last seq {self.last_committed_seq}",
            f"document   {self.directory / CURRENT}",
            f"digest     {reference_digest(self.organism)[:16]}…",
            (f"survival   level (a) locally; mirrored to {self.mirror.describe()}"
             if self.mirror is not None else
             "survival   level (a) only: clean process exit and restart on the same machine"),
        ]
        if self.stopped:
            lines.append(f"stopped    {self.stopped}")
        return "\n".join(lines) + "\n" + self.organism.report()


def _refuse_constant(name: str):
    raise ValueError(f"non-finite number {name!r} refused")
