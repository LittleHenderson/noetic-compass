"""The multi-session evaluation harness: one fresh operating-system process per session.

Evaluation plan sections 3.2, 4.9 and 6 (`docs/working/helm_eval_plan_draft_2026_10_06.md`).
A `SeedStream` (see `cas_rpu/session_types.py`) is one context's whole event
stream, split into sessions. For every path under test this harness runs the
sessions as successive child processes over one `history.Stream` directory:
session 1 is the genesis, every later session restores from disk, verifies,
and only then answers. Each child acknowledges every committed event on its
standard output as it goes, so a child the fault schedule kills mid-segment
leaves the parent holding exactly the acknowledged prefix, which is what the
recovery session must reproduce.

Ground truth is the oracle over the WHOLE stream, stored in the `SeedStream`
before any process runs; no persistence mechanism under test can touch it.
Scoring is `cas_rpu/scoring.score_item`, then relabelled per episode so the
report can say which variant failed.

The four paths of plan section 2, named as the report names them:

    recompute   P0: `ctl_recompute` over the acknowledged log, in-process, no
                persistence; correct by construction and the work baseline.
    walk        P1: the organism, walk-first (`record_first=False`).
    record_dep  P2: record-first with dependency invalidation.
    record_rpa  P3: P2 with the RPA narrower attached (skipped, with the
                reason, when the RPA checkout is not mounted).

What this harness can and cannot claim (plan section 0 and 5.1a): a clean run
demonstrates survival level (a) — process exit and restart on the same machine.
With `--mirror DIR` every session restores from a second directory after the
local one is destroyed, which proves the replacement MECHANISM offline; level
(b) proper needs the dedicated remote location (`s3store.S3Prefix`), selected
with `--mirror s3` when `HELM_S3_BUCKET` is set and the key is accepted.

The fault schedule (section 4.9) is implemented where the single-document
design permits, and the report names what each fault kind exercises:

    kill-before-write      F1  crash before the commit boundary (nothing written)
    kill-before-replace    F4  crash during the document write (temp file left)
    kill-after-replace     F2/F5/F6 crash after publication, before retention and acknowledgment
    kill-after-save        F2  crash after the save completed, before the acknowledgment reached the host
    kill-during-restore    F7/F9 crash while rebuilding; the next restore must succeed
    redeliver              F8/F11 the same event id committed twice in one process (lost-ack retry)
    redeliver-restart      F8  an acknowledged event re-delivered after a restart with its original version
    swap                   F10 two events delivered out of order with correct versions
    torn-current           F3  the current document truncated after acknowledgment
    corrupt-current        F13 bytes flipped in the current document
    corrupt-both           F12/F13 the current AND the newest retained copy damaged: history lost
    schema-bump            F15 the document's schema field bumped and resealed
    quota                  F16 a retention limit small enough to stop the stream mid-segment
    missing-index          F14 not applicable: no index is persisted; the record index and the
                               atlas are rebuilt from the accepted state in every process

Not in the failure model (plan 4.9 last line): power loss, disk failure, host failure.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import resource
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for sub in ("cas_rpu", "ccb_r1", "cas_memory"):
    p = str(REPO / "scripts" / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from controls import ctl_recompute  # noqa: E402
from events import Event, EventKind, ask  # noqa: E402
from history import CURRENT, MemoryError_, Stream, digest  # noqa: E402
from scoring import Matrix, Probe, WithdrawnReport, score_item  # noqa: E402
from session_types import SeedStream, SessionSet  # noqa: E402

PATHS = ("recompute", "walk", "record_dep", "record_rpa")
PROCESS_PATHS = ("walk", "record_dep", "record_rpa")
PATH_KWARGS = {
    "walk": {"record_first": False},
    "record_dep": {"record_first": True, "record_invalidation": "dependency"},
    "record_rpa": {"record_first": True, "record_invalidation": "dependency"},
}
FAULT_KINDS = (
    "kill-before-write", "kill-before-replace", "kill-after-replace", "kill-after-save",
    "kill-during-restore", "redeliver", "redeliver-restart", "swap",
    "torn-current", "corrupt-current", "corrupt-both", "schema-bump", "quota",
)
IN_PROCESS_FAULTS = ("kill-before-write", "kill-before-replace", "kill-after-replace", "kill-after-save", "redeliver", "swap")
POST_MORTEM_FAULTS = ("torn-current", "corrupt-current", "corrupt-both", "schema-bump")
KILL_POINT = {
    "kill-before-write": "before-write",
    "kill-before-replace": "before-replace",
    "kill-after-replace": "after-replace",
    "kill-after-save": "after-save",
}
NOT_APPLICABLE = {"missing-index": "no index is persisted; the record index and the atlas are rebuilt from the accepted state in every process"}


class HarnessError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


# ---------------------------------------------------------------------------
# the child: one session, one process
# ---------------------------------------------------------------------------

def _event_from(data: dict) -> Event:
    return Event(EventKind(data["kind"]), data["subject"], data["obj"], data.get("relation", "leads_to"))


def _rpa_attacher(stream_id: str):
    import rpa_adapter  # noqa: WPS433 — lives in cas_memory, outside the reasoning package
    rpa = rpa_adapter.load_rpa()
    holder: dict = {}

    def attach(organism) -> None:
        holder["narrower"] = rpa_adapter.RpaNarrower(organism, stream_id, rpa)
        organism.record_narrow = holder["narrower"]
    attach.holder = holder  # type: ignore[attr-defined]
    return attach


def _outcome(response) -> dict:
    return {
        "accepted": response.accepted, "code": response.code, "verdict": response.verdict,
        "lacunae": list(response.lacunae), "contested": list(response.contested),
        "withdrawn": list(response.withdrawn), "route": response.route,
        "work": response.work, "work_asks": response.work_asks, "work_scanned": response.work_scanned,
        "edges": response.dependency_edges_checked, "beat_faults": list(response.beat.faults),
    }


def _store_from_spec(spec: dict):
    mirror = spec.get("mirror")
    if not mirror:
        return None
    from s3store import DirectoryStore, S3Prefix
    if mirror == "s3":
        return S3Prefix(os.environ["HELM_S3_BUCKET"], os.environ.get("HELM_S3_PREFIX", "helm-memory"),
                        os.environ.get("HELM_S3_REGION", "us-west-2"))
    return DirectoryStore(Path(mirror))


def child_main(spec: dict) -> int:
    """Run one session. Protocol: one JSON line per acknowledged event, then a `done` line.

    Exit 0 on a normal end; 3 on a typed refusal (`refused` line); the fault
    schedule may end the process with `os._exit(137)` at a declared point.
    """
    out = sys.stdout
    t_start = time.perf_counter_ns()
    directory = Path(spec["directory"])
    path = spec["path"]
    stream_id = f"noetic-compass.{spec['organism_id']}.{spec['context_id']}.trunk"
    fault = spec.get("fault") or {}
    kind = fault.get("kind")
    at = fault.get("at")           # session-local event index the fault acts on

    attach = None
    rpa_stats = None
    if path == "record_rpa":
        attach = _rpa_attacher(stream_id)
    limits = dict(spec.get("limits") or {})
    store = _store_from_spec(spec)

    def emit(obj: dict) -> None:
        out.write(json.dumps(obj, separators=(",", ":")) + "\n")
        out.flush()

    try:
        if spec["event_offset"] == 0 and spec.get("acknowledged_seq") is None:
            # genesis: the first process of the stream, nothing acknowledged yet
            kwargs = {**PATH_KWARGS[path], **limits}
            stream = Stream.genesis(directory, organism_id=spec["organism_id"], context_id=spec["context_id"],
                                    closed_world=spec["closed_world"], attach=attach, mirror=store, **kwargs)
            restore_ns = None
        else:
            if kind == "kill-during-restore":
                import history as _h
                real = _h.build_organism

                def dying(identity):
                    real(identity)
                    os._exit(137)
                _h.build_organism = dying
            t0 = time.perf_counter_ns()
            if store is not None and spec.get("replacement"):
                stream = Stream.restore_from(store, stream_id, directory, acknowledged_seq=spec.get("acknowledged_seq"), attach=attach, **limits)
            else:
                stream = Stream.restore(directory, acknowledged_seq=spec.get("acknowledged_seq"), attach=attach, mirror=store, **limits) \
                    if "mirror" not in limits else Stream.restore(directory, acknowledged_seq=spec.get("acknowledged_seq"), attach=attach, **limits)
                if store is not None:
                    stream.mirror = store
            restore_ns = time.perf_counter_ns() - t0
    except MemoryError_ as exc:
        emit({"refused": exc.code, "message": str(exc), "phase": "restore" if spec["event_offset"] else "genesis"})
        return 3

    restored_at = time.perf_counter_ns()
    restored_seq = stream.last_committed_seq

    # recovery probes (plan 4.9): asked BEFORE the stream continues, on a scratch
    # copy of the store, so the scored stream and the store itself are untouched
    recovery: list[dict] = []
    if spec.get("recovery_probes"):
        import tempfile
        scratch_dir = Path(tempfile.mkdtemp(prefix="helm-scratch-"))
        shutil.copytree(directory, scratch_dir / "copy")
        for pair in spec["recovery_probes"]:
            scratch = Stream.restore(scratch_dir / "copy", attach=attach, **limits)
            r = scratch.commit(ask(pair[0], pair[1]))
            recovery.append({"pair": pair, "verdict": r.verdict, "lacunae": list(r.lacunae), "contested": list(r.contested), "route": r.route})
            shutil.rmtree(scratch_dir / "copy")
            shutil.copytree(directory, scratch_dir / "copy")
        shutil.rmtree(scratch_dir)

    events = [_event_from(e) for e in spec["events"]]
    offset = spec["event_offset"]
    commit_ns: list[int] = []
    first_answer_ns = None

    def kill_at(point_wanted: str, index: int):
        def hook(point: str) -> None:
            if point == point_wanted and stream.organism.clock == offset + index + 1:
                out.flush()
                os._exit(137)
        return hook

    if kind in KILL_POINT and at is not None:
        stream.fault_hook = kill_at(KILL_POINT[kind], at)

    fault_report: dict = {}
    try:
        i = 0
        while i < len(events):
            ev = events[i]
            seq_expected = offset + i
            if kind == "swap" and at is not None and i == at and i + 1 < len(events):
                nxt = events[i + 1]
                try:
                    stream.commit(nxt, expected_version=seq_expected)   # delivered early with its own version
                    fault_report["swap"] = {"early_accepted": True, "event_kind": nxt.kind.value}
                except MemoryError_ as exc:
                    fault_report["swap"] = {"early_accepted": False, "code": exc.code, "event_kind": nxt.kind.value}
            t0 = time.perf_counter_ns()
            response = stream.commit(ev, expected_version=seq_expected - 1)
            dt = time.perf_counter_ns() - t0
            commit_ns.append(dt)
            if response.verdict is not None and first_answer_ns is None:
                first_answer_ns = time.perf_counter_ns()
            if kind == "redeliver" and at is not None and i == at:
                rows_before = len(stream.rows)
                again = stream.commit(ev, expected_version=seq_expected - 1)
                fault_report["redeliver"] = {"same_response": again is response, "rows_unchanged": len(stream.rows) == rows_before}
            emit({"ack": stream.last_committed_seq, "index": offset + i, "outcome": _outcome(response), "ns": dt})
            i += 1
        if spec.get("redeliver_after_restart"):
            rd = spec["redeliver_after_restart"]
            before = stream.last_committed_seq
            try:
                r = stream.commit(_event_from(rd["event"]), expected_version=rd["expected_version"])
                fault_report["redeliver-restart"] = {"accepted": True, "verdict": r.verdict, "rows_added": stream.last_committed_seq - before}
            except MemoryError_ as exc:
                fault_report["redeliver-restart"] = {"accepted": False, "code": exc.code, "rows_added": stream.last_committed_seq - before}
    except MemoryError_ as exc:
        emit({"refused": exc.code, "message": str(exc), "phase": "commit", "at": offset + i})
        return 3

    if attach is not None:
        rpa_stats = dict(attach.holder["narrower"].stats)  # type: ignore[attr-defined]
    rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    size = sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
    emit({
        "done": True,
        "rows": len(stream.rows), "last_seq": stream.last_committed_seq, "restored_seq": restored_seq,
        "standing": sorted(stream.organism.standing), "faults": list(stream.organism.faults),
        "record_stats": dict(stream.organism.record_stats), "rpa_stats": rpa_stats,
        "recovered_from": stream.recovered_from, "recovery_failures": list(stream.recovery_failures),
        "reference_digest": stream.document()["reference_digest"],
        "restore_ns": restore_ns, "start_ns": restored_at - t_start,
        "restore_before_first_answer": (first_answer_ns is None) or (restored_at < first_answer_ns),
        "commit_ns": commit_ns, "rss_kb": rss_kb, "bytes_on_disk": size,
        "fault_report": fault_report, "recovery": recovery,
        "survival": stream.report().splitlines()[4].split(None, 1)[1],
    })
    return 0


# ---------------------------------------------------------------------------
# the parent: sessions, faults, scoring
# ---------------------------------------------------------------------------

@dataclass
class SessionRecord:
    session: int
    label: str                       # "session" | "recovery"
    returncode: int
    acks: list[dict]
    done: dict | None
    refused: dict | None
    wall_ns: int
    fault: dict | None = None


@dataclass
class SeedRun:
    seed: int
    twin: bool
    path: str
    closed_world: bool
    sessions: list[SessionRecord] = field(default_factory=list)
    outcomes: dict[int, dict] = field(default_factory=dict)      # event index -> outcome
    fault_checks: list[dict] = field(default_factory=list)
    stopped: str | None = None

    @property
    def acknowledged_seq(self) -> int:
        return max((a["ack"] for s in self.sessions for a in s.acks), default=-1)


def _launch(spec: dict, timeout: float = 600.0) -> SessionRecord:
    env = os.environ.copy()
    t0 = time.perf_counter_ns()
    proc = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--child"],
                          input=json.dumps(spec), capture_output=True, text=True, timeout=timeout, env=env)
    wall = time.perf_counter_ns() - t0
    acks, done, refused = [], None, None
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if "ack" in obj:
            acks.append(obj)
        elif obj.get("done"):
            done = obj
        elif "refused" in obj:
            refused = obj
    if proc.returncode not in (0, 3, 137) or (proc.returncode == 0 and done is None):
        raise HarnessError("E-SH-001", f"child failed (rc={proc.returncode}):\n{proc.stderr[-4000:]}")
    return SessionRecord(spec["session"], spec.get("label", "session"), proc.returncode, acks, done, refused, wall, spec.get("fault"))


def _canon(events) -> list[dict]:
    return [e.canonical() for e in events]


def _post_mortem(directory: Path, kind: str) -> dict:
    """Damage the store between two sessions, deterministically, and say what was done."""
    current = directory / CURRENT
    data = current.read_bytes()
    retained = sorted(p for p in directory.glob("history.*.json") if p.name != CURRENT)
    if kind == "torn-current":
        current.write_bytes(data[: max(1, len(data) - len(data) // 3)])
        return {"kind": kind, "bytes_removed": len(data) // 3}
    if kind in ("corrupt-current", "corrupt-both"):
        flipped = bytearray(data)
        for k in range(0, len(flipped), max(1, len(flipped) // 7)):
            flipped[k] ^= 0x5A
        current.write_bytes(bytes(flipped))
        touched = [current.name]
        if kind == "corrupt-both" and retained:
            newest = retained[-1]
            raw = bytearray(newest.read_bytes())
            for k in range(0, len(raw), max(1, len(raw) // 5)):
                raw[k] ^= 0xA5
            newest.write_bytes(bytes(raw))
            touched.append(newest.name)
        return {"kind": kind, "touched": touched}
    if kind == "schema-bump":
        doc = json.loads(data)
        doc["header"]["schema_version"] = "helm.memory/99.0"
        body = {k: v for k, v in doc.items() if k != "document_digest"}
        doc["document_digest"] = digest(body)
        resealed = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
        current.write_bytes(resealed)
        if retained:
            retained[-1].write_bytes(resealed)
        return {"kind": kind, "touched": [current.name] + ([retained[-1].name] if retained else [])}
    raise HarnessError("E-SH-002", f"unknown post-mortem fault {kind!r}")


def run_seed(stream: SeedStream, path: str, root: Path, *, fault: dict | None = None,
             mirror: str | None = None, replacement: bool = False, limits: dict | None = None,
             organism_id: str = "helm-eval") -> SeedRun:
    """Run every session of one seed stream on one process path.

    `fault` = {"kind": ..., "boundary": b} applies one fault of the schedule to
    the session that ends at boundary `b` (1-based), or to the restore that
    follows it; the stream then continues through a recovery session and the
    remaining boundaries restart normally.
    """
    world = "closed" if stream.closed_world else "open"
    context_id = f"seed{stream.seed}{'-twin' if stream.twin_of is not None else ''}-{world}"
    directory = root / world / path / context_id
    if directory.exists():
        shutil.rmtree(directory)
    run = SeedRun(stream.seed, stream.twin_of is not None, path, stream.closed_world)
    fault = dict(fault) if fault else None
    kind = fault["kind"] if fault else None
    boundary = fault["boundary"] if fault else None
    if kind in NOT_APPLICABLE:
        run.fault_checks.append({"kind": kind, "applicable": False, "reason": NOT_APPLICABLE[kind], "ok": None})
        kind = None
    all_events = list(stream.events)
    asked_pairs: list[tuple[str, str]] = []
    redeliver_restart = None
    extra_limits = dict(limits or {})

    def spec_for(k: int, lo: int, hi: int, label: str, this_fault: dict | None, acknowledged: int | None, lim: dict) -> dict:
        s = {
            "directory": str(directory), "path": path, "closed_world": stream.closed_world,
            "organism_id": organism_id, "context_id": context_id, "session": k, "label": label,
            "events": _canon(all_events[lo:hi]), "event_offset": lo, "acknowledged_seq": acknowledged,
            "fault": this_fault, "limits": lim, "mirror": mirror, "replacement": replacement and k > 0,
        }
        return s

    k = 0
    launched: set[tuple[int, int]] = set()
    while k < stream.sessions:
        lo, hi = stream.session_range(k)
        start = max(lo, run.acknowledged_seq + 1)
        if (k, start) in launched and run.sessions[-1].returncode != 137:
            # the previous process made no progress on this segment and no fault
            # explains it: stop rather than retry forever, and say where
            run.stopped = f"E-SH-003: no progress at seq {start} (session {k + 1}); last refusal: {run.sessions[-1].refused}"
            break
        launched.add((k, start))
        this_fault = None
        lim = dict(extra_limits)
        if kind in IN_PROCESS_FAULTS and boundary == k + 1:
            at = _fault_index(all_events, start, hi, kind)
            if at is None:
                run.fault_checks.append({"kind": kind, "applicable": False, "reason": "no suitable event in the segment", "ok": None})
                kind = None
            else:
                this_fault = {"kind": kind, "at": at - start}
        if kind == "quota" and boundary == k + 1:
            lim["max_events"] = (start + 1) + max(1, (hi - start) // 2)     # rows so far + half the segment
            this_fault = {"kind": kind}
        if kind == "kill-during-restore" and boundary == k and k > 0:
            this_fault = {"kind": kind}
        spec = spec_for(k, start, hi, "session" if start == lo else "recovery", this_fault, run.acknowledged_seq if start > 0 else None, lim)
        if k > 0 and start > lo:
            spec["recovery_probes"] = [list(p) for p in dict.fromkeys(asked_pairs)]
        if redeliver_restart is not None:
            spec["redeliver_after_restart"] = redeliver_restart
            redeliver_restart = None
        if replacement and k > 0 and directory.exists():
            shutil.rmtree(directory)                       # the previous machine is gone
        rec = _launch(spec)
        run.sessions.append(rec)
        for c in run.fault_checks:
            if c.get("ok") is None and c["kind"] in POST_MORTEM_FAULTS and c.get("boundary") == k:
                c.update(_post_mortem_verdict(c["kind"], rec, spec["acknowledged_seq"]))   # what the host had acknowledged BEFORE this restore
        for a in rec.acks:
            run.outcomes[a["index"]] = a["outcome"]
            ev = all_events[a["index"]]
            if ev.kind is EventKind.ASK:
                asked_pairs.append(ev.pair)
        _check_session(run, rec, stream, all_events, spec)
        if rec.refused and rec.refused.get("phase") in ("restore", "genesis"):
            run.stopped = f"{rec.refused['refused']}: {rec.refused['message']}"
            break
        if rec.returncode == 137 or rec.refused:
            # killed or stopped mid-segment: a recovery session continues the same segment
            if this_fault and this_fault["kind"] == "kill-during-restore":
                this_fault = None
            kind_done = kind
            kind = None
            if run.acknowledged_seq + 1 >= hi:
                k += 1
            if kind_done == "quota":
                extra_limits.pop("max_events", None)
            continue
        if kind == "redeliver-restart" and boundary == k + 1:
            last = next((a for a in reversed(rec.acks) if all_events[a["index"]].kind is not EventKind.ASK), None)
            if last is None:
                run.fault_checks.append({"kind": kind, "applicable": False, "reason": "no non-ASK event acknowledged in the segment", "ok": None})
            else:
                redeliver_restart = {"event": all_events[last["index"]].canonical(), "expected_version": last["index"] - 1,
                                     "digest_before": rec.done["reference_digest"] if rec.done else None}
            kind = None
        if kind in POST_MORTEM_FAULTS and boundary == k + 1:
            run.fault_checks.append({"kind": kind, "applied": _post_mortem(directory, kind), "ok": None, "boundary": k + 1})
            kind = None
        k += 1
    return run


def _post_mortem_verdict(kind: str, rec: "SessionRecord", acked: int) -> dict:
    """Plan 4.9 pass conditions for damage done between two sessions."""
    if rec.refused and rec.refused.get("phase") == "restore":
        code = rec.refused["refused"]
        if kind == "corrupt-both":
            return {"ok": code == "E-MEM-046", "refused": code, "note": "history lost beyond retention: serving stopped, boundary named"}
        if kind == "schema-bump":
            return {"ok": code == "E-MEM-010", "refused": code}
        return {"ok": False, "refused": code, "message": rec.refused["message"]}
    if rec.done is None:
        return {"ok": False, "reason": "no restore report"}
    exact = rec.done["restored_seq"] == acked
    fell_back = rec.done["recovered_from"] != CURRENT and bool(rec.done["recovery_failures"])
    if kind in ("torn-current", "corrupt-current"):
        return {"ok": exact and fell_back, "restored_seq": rec.done["restored_seq"], "acknowledged_seq": acked,
                "recovered_from": rec.done["recovered_from"], "detected": rec.done["recovery_failures"]}
    return {"ok": False, "reason": f"{kind} did not stop the restore", "restored_seq": rec.done["restored_seq"]}


def _fault_index(events, start: int, hi: int, kind: str) -> int | None:
    """Pick the event the in-process fault acts on: past the segment's start, before its end."""
    candidates = list(range(start + 1, hi - 1))
    if not candidates:
        return None
    if kind == "swap":
        for i in candidates:
            if i + 1 < hi and events[i + 1].kind is not EventKind.ASK and events[i].kind is not EventKind.ASK:
                return i
        return None
    return candidates[len(candidates) // 2]


def _check_session(run: SeedRun, rec: SessionRecord, stream: SeedStream, events, spec: dict) -> None:
    """Pass conditions of plan section 4.9 for whatever this session exercised."""
    f = rec.fault or {}
    kind = f.get("kind")
    if rec.label == "recovery":
        acked = spec["acknowledged_seq"]
        if rec.refused and rec.refused.get("phase") == "restore":
            run.fault_checks.append({"kind": "recovery", "ok": rec.refused["refused"] in ("E-MEM-046", "E-MEM-010"),
                                     "refused": rec.refused["refused"], "message": rec.refused["message"], "acknowledged_seq": acked})
        elif rec.done is not None:
            restored_seq = rec.done["restored_seq"]
            # exactly the acknowledged prefix, or one ahead of it when the crash fell
            # between the save and the acknowledgment (the host's retry is then
            # recognised and acknowledged once; nothing acknowledged is missing)
            run.fault_checks.append({"kind": "recovery", "ok": restored_seq in (acked, acked + 1),
                                     "restored_seq": restored_seq, "acknowledged_seq": acked,
                                     "recovered_from": rec.done["recovered_from"], "recovery_failures": rec.done["recovery_failures"]})
            # recovery probes against fresh recompute over the acknowledged prefix
            prefix = [events[i] for i in sorted(run.outcomes) if i <= acked]
            for probe in rec.done.get("recovery", []):
                ref = ctl_recompute(prefix + [ask(*probe["pair"])], stream.closed_world).answers[-1]
                ok = probe["verdict"] == ref.verdict and set(probe["contested"]) == set(ref.contested)
                run.fault_checks.append({"kind": "recovery-probe", "ok": ok, "pair": probe["pair"], "got": probe["verdict"], "expected": ref.verdict, "route": probe["route"]})
    if rec.done is not None and rec.done.get("restore_before_first_answer") is False:
        run.fault_checks.append({"kind": "ordering", "ok": False, "reason": "an answer preceded restore validation"})
    fr = (rec.done or {}).get("fault_report") or {}
    if "redeliver" in fr:
        run.fault_checks.append({"kind": "redeliver", "ok": fr["redeliver"]["same_response"] and fr["redeliver"]["rows_unchanged"], **fr["redeliver"]})
    if "swap" in fr:
        run.fault_checks.append({"kind": "swap", "ok": not fr["swap"]["early_accepted"] and fr["swap"].get("code") == "E-MEM-002", **fr["swap"]})
    if "redeliver-restart" in fr:
        r = fr["redeliver-restart"]
        # applied once: the re-delivery adds no row, whether it is recognised as a
        # retry and acknowledged again (same payload at the intended seq) or refused
        run.fault_checks.append({"kind": "redeliver-restart", "ok": r["rows_added"] == 0, **r})
    if kind == "quota":
        if rec.refused and rec.refused.get("phase") == "commit":
            run.fault_checks.append({"kind": "quota", "ok": rec.refused["refused"] == "E-MEM-050", "refused": rec.refused["refused"],
                                     "acknowledged_seq": run.acknowledged_seq, "stopped_at": rec.refused.get("at")})
        else:
            run.fault_checks.append({"kind": "quota", "ok": False, "reason": "the limit did not stop the stream"})
    if kind in KILL_POINT and rec.returncode != 137:
        run.fault_checks.append({"kind": kind, "ok": False, "reason": "the kill point was never reached"})
    if kind == "kill-during-restore" and rec.returncode != 137:
        run.fault_checks.append({"kind": kind, "ok": False, "reason": "the restore was not interrupted"})


# ---------------------------------------------------------------------------
# P0 in-process and scoring
# ---------------------------------------------------------------------------

def run_recompute(stream: SeedStream) -> SeedRun:
    run = SeedRun(stream.seed, stream.twin_of is not None, "recompute", stream.closed_world)
    out = ctl_recompute(list(stream.events), stream.closed_world)
    for a in out.answers:
        run.outcomes[a.event_index] = {"verdict": a.verdict, "lacunae": list(a.lacunae), "contested": list(a.contested),
                                       "withdrawn": [], "route": "recompute", "work": a.work, "accepted": True}
    fell = {w.event_index: list(w.keys) for w in out.withdrawn}
    for i, ev in enumerate(stream.events):
        if ev.kind in (EventKind.RETRACT, EventKind.NEGATION):
            run.outcomes[i] = {"verdict": None, "withdrawn": fell.get(i, []), "route": "recompute", "work": 0, "accepted": i not in out.refused}
    return run


@dataclass(frozen=True)
class _ItemView:
    """What `score_item` needs, over a whole seed stream."""
    item_id: str
    mechanism: str
    variant: str
    closed_world: bool
    expectations: tuple
    withdrawn: tuple
    designed_probe_index: int = -1


def _owners(stream: SeedStream) -> dict[int, int]:
    """probe index -> episode position. Spans of different episodes interleave in a
    generated stream, so containment cannot say whose a probe is; the generator's
    token-component attribution can (`sessions.probe_owners`). Hand-built streams
    without that structure fall back to the designed index, then the smallest
    containing span."""
    try:
        from sessions import probe_owners
        return probe_owners(stream)
    except Exception:
        return {}


def _episode_of(stream: SeedStream, index: int, owners: dict[int, int] | None = None):
    for ep in stream.episodes:
        if ep.designed_probe_index == index:
            return ep
    if owners and index in owners:
        return stream.episodes[owners[index]]
    best = None
    for ep in stream.episodes:
        if ep.start <= index < ep.end and (best is None or (ep.end - ep.start) < (best.end - best.start)):
            best = ep
    return best


def score_run(stream: SeedStream, run: SeedRun):
    """`scoring.score_item` over the whole stream, relabelled per episode. Probes
    the run never answered (a stopped stream) are scored as missing: E-SC-001
    would refuse, so they are listed under `unanswered` instead."""
    probes, unanswered = [], []
    for x in stream.expectations:
        o = run.outcomes.get(x.event_index)
        if o is None or o.get("verdict") is None:
            unanswered.append(x.event_index)
            continue
        probes.append(Probe(x.event_index, o["verdict"], tuple(o["lacunae"]), tuple(o["contested"]), int(o.get("work", 0))))
    withdrawn = [WithdrawnReport(w.event_index, tuple(run.outcomes.get(w.event_index, {}).get("withdrawn", ())))
                 for w in stream.withdrawn if w.event_index in run.outcomes]
    view = _ItemView(f"seed{stream.seed}{'-twin' if stream.twin_of is not None else ''}", "S", "stream", stream.closed_world,
                     tuple(x for x in stream.expectations if x.event_index not in unanswered),
                     tuple(w for w in stream.withdrawn if w.event_index in run.outcomes))
    score = score_item(view, probes, withdrawn)
    owners = _owners(stream)
    relabelled = []
    for p in score.probes:
        ep = _episode_of(stream, p.event_index, owners)
        relabelled.append(replace(p, mechanism=ep.mechanism if ep else "?", variant=ep.variant if ep else "?",
                                  designed=bool(ep and ep.designed_probe_index == p.event_index)))
    rel_w = []
    for w in score.withdrawn:
        ep = _episode_of(stream, w.event_index)
        rel_w.append(replace(w, mechanism=ep.mechanism if ep else "?", variant=ep.variant if ep else "?"))
    return replace(score, probes=tuple(relabelled), withdrawn=tuple(rel_w)), unanswered


# ---------------------------------------------------------------------------
# the evaluation over a SessionSet
# ---------------------------------------------------------------------------

@dataclass
class PathResult:
    path: str
    world: str
    matrix: Matrix
    runs: list[SeedRun] = field(default_factory=list)
    unanswered: int = 0
    per_seed_accuracy: list[float] = field(default_factory=list)
    retention: dict = field(default_factory=lambda: {"total": 0, "ok": 0, "hits": 0, "stale_hits": 0})
    transfer: dict = field(default_factory=lambda: {"total": 0, "ok": 0, "hits": 0})
    exact: dict = field(default_factory=lambda: {"total": 0, "ok": 0, "hits": 0})
    unseen_hits: int = 0
    twin_designed: dict = field(default_factory=lambda: {"total": 0, "ok": 0})
    routes: dict = field(default_factory=dict)
    work: dict = field(default_factory=lambda: {"first": [], "repeat": []})
    commit_ns: list[int] = field(default_factory=list)
    restore_ns: list[int] = field(default_factory=list)
    start_ns: list[int] = field(default_factory=list)
    wall_ns: list[int] = field(default_factory=list)
    rss_kb: int = 0
    bytes_on_disk: int = 0
    heartbeat_faults: int = 0
    fault_checks: list[dict] = field(default_factory=list)
    stopped: list[str] = field(default_factory=list)
    skipped: str | None = None
    survival: str = ""


def _repeat_flags(events) -> dict[int, bool]:
    seen: set = set()
    flags = {}
    for i, ev in enumerate(events):
        if ev.kind is EventKind.ASK:
            flags[i] = ev.pair in seen
            seen.add(ev.pair)
    return flags


def _absorb(result: PathResult, stream: SeedStream, run: SeedRun) -> None:
    score, unanswered = score_run(stream, run)
    result.runs.append(run)
    result.unanswered += len(unanswered)
    result.matrix.add(result.path, score)
    if score.probes:
        result.per_seed_accuracy.append(sum(p.verdict_ok for p in score.probes) / len(score.probes))
    flags = _repeat_flags(stream.events)
    owners = _owners(stream)
    for p in score.probes:
        o = run.outcomes[p.event_index]
        route = (o.get("route") or "walk").split(":")[0]
        result.routes[route] = result.routes.get(route, 0) + 1
        (result.work["repeat"] if flags.get(p.event_index) else result.work["first"]).append(p.work)
        ep = _episode_of(stream, p.event_index, owners)
        hit = o.get("route") == "hit"
        if not flags.get(p.event_index) and hit:
            result.unseen_hits += 1
        if ep is not None and p.designed:
            if run.twin:
                result.twin_designed["total"] += 1
                result.twin_designed["ok"] += int(p.verdict_ok)
            elif ep.cross_session and ep.variant != "T-compose" and ep.variant != "T-exact":
                result.retention["total"] += 1
                result.retention["ok"] += int(p.verdict_ok)
                result.retention["hits"] += int(hit)
                result.retention["stale_hits"] += int(hit and not p.verdict_ok)
            elif ep.variant == "T-compose":
                result.transfer["total"] += 1
                result.transfer["ok"] += int(p.verdict_ok)
                result.transfer["hits"] += int(hit)
            elif ep.variant == "T-exact":
                result.exact["total"] += 1
                result.exact["ok"] += int(p.verdict_ok)
                result.exact["hits"] += int(hit)
    for rec in run.sessions:
        result.wall_ns.append(rec.wall_ns)
        if rec.done:
            result.commit_ns.extend(rec.done["commit_ns"])
            if rec.done["restore_ns"] is not None:
                result.restore_ns.append(rec.done["restore_ns"])
            result.start_ns.append(rec.done["start_ns"])
            result.rss_kb = max(result.rss_kb, rec.done["rss_kb"])
            result.bytes_on_disk = max(result.bytes_on_disk, rec.done["bytes_on_disk"])
            result.heartbeat_faults += len(rec.done["faults"])
            result.survival = rec.done.get("survival", result.survival)
    result.fault_checks.extend(run.fault_checks)
    if run.stopped:
        result.stopped.append(f"seed{stream.seed}: {run.stopped}")


def schedule_faults(streams, sessions: int, kinds=FAULT_KINDS) -> dict[int, dict]:
    """One fault per seed, kinds and boundaries rotating so every kind recurs."""
    out = {}
    for i, s in enumerate(streams):
        out[s.seed] = {"kind": kinds[i % len(kinds)], "boundary": 1 + (i % max(1, sessions - 1))}
    return out


def evaluate(sset: SessionSet, root: Path, *, paths=PATHS, faults: bool = False, twins: bool = True,
             mirror: str | None = None, replacement: bool = False, log=None) -> dict[str, PathResult]:
    world = "closed" if sset.closed_world else "open"
    results: dict[str, PathResult] = {}
    rpa_reason = None
    if "record_rpa" in paths:
        try:
            import rpa_adapter
            rpa_adapter.load_rpa()
        except Exception as exc:  # RpaUnavailable or an import failure in the checkout
            rpa_reason = str(exc)
    plan = schedule_faults(sset.streams, sset.sessions) if faults else {}
    streams = list(sset.streams) + (list(sset.twins) if twins else [])
    for path in paths:
        result = PathResult(path, world, Matrix())
        results[path] = result
        if path == "record_rpa" and rpa_reason:
            result.skipped = rpa_reason
            continue
        for stream in streams:
            if path == "recompute":
                run = run_recompute(stream)
            else:
                run = run_seed(stream, path, root, fault=plan.get(stream.seed) if stream.twin_of is None else None,
                               mirror=mirror, replacement=replacement)
            _absorb(result, stream, run)
            if log:
                log(f"{world} {path} seed{stream.seed}{' twin' if stream.twin_of is not None else ''}: "
                    f"{len(run.sessions)} process(es), acked through {run.acknowledged_seq}")
    return results


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def bootstrap_ci(values: list[float], reps: int = 1000, seed: int = 0) -> tuple[float, float] | None:
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    means = sorted(statistics.fmean(rng.choices(values, k=len(values))) for _ in range(reps))
    return means[int(0.025 * reps)], means[int(0.975 * reps) - 1]


def _pct(ns: list[int], q: float) -> float | None:
    if not ns:
        return None
    s = sorted(ns)
    return s[min(len(s) - 1, int(q * len(s)))] / 1e6


def render(results: dict[str, PathResult], sset: SessionSet) -> str:
    world = "closed" if sset.closed_world else "open"
    lines = [f"== multi-session evaluation — {world} world — {len(sset.streams)} seed(s) × {sset.sessions} session(s), "
             f"{len(sset.twins)} twin(s); fingerprint {sset.fingerprint()[:16]}…"]
    for path, r in results.items():
        if r.skipped:
            lines.append(f"-- {path}: NOT RUN — {r.skipped}")
            continue
        m = r.matrix
        tot = sum(c.total for (s, _, col), c in m.cells.items() if s == path and col == "verdict")
        ok = sum(c.hits for (s, _, col), c in m.cells.items() if s == path and col == "verdict")
        ci = bootstrap_ci(r.per_seed_accuracy)
        lines.append(f"-- {path}: verdict {ok}/{tot}" + (f" (seed-bootstrap 95% CI of mean accuracy {ci[0]:.3f}–{ci[1]:.3f})" if ci else "")
                     + (f"; UNANSWERED {r.unanswered}" if r.unanswered else ""))
        for col in ("contested", "named", "withdrawn"):
            t = sum(c.total for (s, _, cc), c in m.cells.items() if s == path and cc == col)
            h = sum(c.hits for (s, _, cc), c in m.cells.items() if s == path and cc == col)
            if t:
                lines.append(f"   {col:<10} {h}/{t}")
        failing = m.failing_variants(path)
        if failing:
            lines.append(f"   failing variants: {', '.join(failing)}")
        rt = r.retention
        lines.append(f"   retention probes (cross-session designed): {rt['ok']}/{rt['total']} correct; "
                     f"served from the record {rt['hits']}; STALE HITS {rt['stale_hits']}")
        lines.append(f"   transfer T-compose: {r.transfer['ok']}/{r.transfer['total']} correct, record hits {r.transfer['hits']} (must be 0); "
                     f"T-exact: {r.exact['ok']}/{r.exact['total']} correct, record hits {r.exact['hits']}")
        if r.twin_designed["total"]:
            lines.append(f"   untaught twins, designed probes: {r.twin_designed['ok']}/{r.twin_designed['total']} GAP as expected")
        lines.append(f"   routes {dict(sorted(r.routes.items()))}; hits on never-asked pairs {r.unseen_hits} (must be 0)")
        fw = statistics.fmean(r.work['first']) if r.work['first'] else None
        rw = statistics.fmean(r.work['repeat']) if r.work['repeat'] else None
        lines.append(f"   work units: first-ask mean {fw if fw is None else round(fw, 1)}, repeat-ask mean {rw if rw is None else round(rw, 1)}")
        if r.commit_ns:
            restore = (f"restore ms p50 {_pct(r.restore_ns, .5):.1f} max {max(r.restore_ns) / 1e6:.1f}"
                       if r.restore_ns else "restore: none")
            lines.append(f"   commit ms p50 {_pct(r.commit_ns, .5):.2f} p95 {_pct(r.commit_ns, .95):.2f}; {restore}; "
                         f"process start ms p50 {_pct(r.start_ns, .5):.1f}; session wall ms p50 {_pct(r.wall_ns, .5):.0f}; "
                         f"max RSS {r.rss_kb // 1024} MB; largest store {r.bytes_on_disk // 1024} KB; heartbeat faults {r.heartbeat_faults}")
            lines.append(f"   survival demonstrated: {r.survival}")
        if r.fault_checks:
            by = {}
            for c in r.fault_checks:
                by.setdefault(c["kind"], []).append(c)
            for kind, checks in sorted(by.items()):
                oks = [c["ok"] for c in checks]
                na = sum(1 for c in checks if c.get("applicable") is False)
                lines.append(f"   fault {kind:<18} {sum(1 for o in oks if o is True)}/{sum(1 for o in oks if o is not None)} passed"
                             + (f", {na} not applicable ({checks[0].get('reason', '')})" if na else "")
                             + ("" if all(o is not False for o in oks) else "  FAILED: " + "; ".join(
                                 json.dumps({k: v for k, v in c.items() if k != 'kind'})[:200] for c in checks if c["ok"] is False)))
        for s in r.stopped:
            lines.append(f"   STOPPED {s}")
    return "\n".join(lines)


def to_json(results: dict[str, PathResult], sset: SessionSet) -> dict:
    out = {"world": "closed" if sset.closed_world else "open", "fingerprint": sset.fingerprint(), "summary": sset.summary(), "paths": {}}
    for path, r in results.items():
        m = r.matrix
        out["paths"][path] = {
            "skipped": r.skipped,
            "matrix": None if r.skipped else json.loads(m.to_json()),
            "unanswered": r.unanswered,
            "retention": r.retention, "transfer": r.transfer, "exact": r.exact, "twin_designed": r.twin_designed,
            "routes": r.routes, "unseen_hits": r.unseen_hits,
            "work_first_mean": statistics.fmean(r.work["first"]) if r.work["first"] else None,
            "work_repeat_mean": statistics.fmean(r.work["repeat"]) if r.work["repeat"] else None,
            "commit_ms_p50": _pct(r.commit_ns, .5), "commit_ms_p95": _pct(r.commit_ns, .95),
            "restore_ms": [n / 1e6 for n in r.restore_ns], "start_ms_p50": _pct(r.start_ns, .5),
            "rss_kb": r.rss_kb, "bytes_on_disk": r.bytes_on_disk, "heartbeat_faults": r.heartbeat_faults,
            "fault_checks": r.fault_checks, "stopped": r.stopped, "survival": r.survival,
            "per_seed_accuracy": r.per_seed_accuracy, "ci": bootstrap_ci(r.per_seed_accuracy),
            "runs": [{"seed": run.seed, "twin": run.twin, "stopped": run.stopped,
                      "sessions": [{"session": sr.session, "label": sr.label, "returncode": sr.returncode, "acks": len(sr.acks),
                                    "restored_seq": (sr.done or {}).get("restored_seq"), "recovered_from": (sr.done or {}).get("recovered_from"),
                                    "wall_ms": sr.wall_ns / 1e6} for sr in run.sessions],
                      "outcomes": {str(i): o for i, o in sorted(run.outcomes.items())}} for run in r.runs],
        }
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_seeds(text: str) -> list[int]:
    out: list[int] = []
    for part in text.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--child", action="store_true", help="internal: run one session from a JSON spec on stdin")
    ap.add_argument("--seeds", default="0-2")
    ap.add_argument("--sessions", type=int, default=5)
    ap.add_argument("--paths", default=",".join(PATHS))
    ap.add_argument("--worlds", default="open,closed")
    ap.add_argument("--root", default=None, help="store root (default: a fresh temporary directory)")
    ap.add_argument("--faults", action="store_true", help="apply the fault schedule, one fault per seed")
    ap.add_argument("--no-twins", action="store_true")
    ap.add_argument("--mirror", default=None, help="DIR for a second-directory mirror, or 's3' for the dedicated location")
    ap.add_argument("--replacement", action="store_true", help="destroy the local store between sessions; restore from the mirror")
    ap.add_argument("--json", default=None, help="write the full results here")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    if args.child:
        return child_main(json.load(sys.stdin))

    from sessions import generate_session_set  # the generator; a separate module so this file never imports it as a child
    import tempfile
    root = Path(args.root) if args.root else Path(tempfile.mkdtemp(prefix="helm-eval-"))
    paths = tuple(p for p in args.paths.split(",") if p)
    log = None if args.quiet else (lambda s: print(s, file=sys.stderr, flush=True))
    blob = {}
    for world in args.worlds.split(","):
        sset = generate_session_set(_parse_seeds(args.seeds), sessions=args.sessions, closed_world=(world == "closed"))
        results = evaluate(sset, root, paths=paths, faults=args.faults, twins=not args.no_twins,
                           mirror=args.mirror, replacement=args.replacement, log=log)
        print(render(results, sset))
        blob[world] = to_json(results, sset)
    if args.json:
        Path(args.json).write_text(json.dumps(blob, indent=1, sort_keys=True))
    print(f"store root: {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
