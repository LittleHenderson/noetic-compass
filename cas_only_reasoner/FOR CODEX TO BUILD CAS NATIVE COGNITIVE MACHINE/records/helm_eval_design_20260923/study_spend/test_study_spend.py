"""Small pure-Python tests for study_spend.py. Label CLAUDE_BUILT_CLAUDE_CHECKED.

Covers Codex review codex-0007 (defects 1-4), the builder review of bb942461 (MAJOR 1-4, MINOR 1-4), the round-2
verification of d89721b4 (MAJOR-A probes P1-P5, MINOR-B probe P6), the round-3 verification of 269d13c8 (MAJOR-E
probes N1a, N1b, N2a, N2b, N3; NOTE-F probe N4) and the round-4 verification of d2098474 (MAJOR-H probes N6a-N6d;
MINOR probe N8): every wrongful ADMIT a reviewer found has a negative test here. V2 (Codex Q1-Q9, R3-F and the static
review findings 1-2 at c3a128ee): one named test per rule, test_v2_r1 ... test_v2_r9 and test_v2_q5, plus the
verifier's X1, X2 and X3 as negative tests. Synthetic receipts only; a fake git reader; temporary folders. The two N8
tests build tiny real git repositories (and a local bare "remote") in a temporary folder; nothing touches the network.
No AWS, no torch; the real receipts are never read; the real slots file is only read (json and load_slots, no
admission, no write) by test_v2_q5.
Run: python -B test_study_spend.py   (also collectable by pytest)
"""
import atexit
import copy
import hashlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import study_spend as ss  # noqa: E402

C1 = "a" * 40
SRC_UNCHANGED, SRC_REPAIRED, SRC_WATCHED = "4" * 40, "3" * 40, "e" * 40
BUNDLE, WORKER, CHECKER = "c" * 64, "5" * 64, "6" * 64      # V2 R4: what every admission binds, beside the source
ADMITTED, NOW = "2026-09-24T09:00:00Z", "2026-09-24T12:00:00Z"
S1_PATH, S2_PATH, LAST = "r/s1/result.json", "r/s2/result.json", "r/s1/provider_0025.json"
# The pre-gate smoke's two attempts, in the launcher's job id format (round 4: S1 and S2 are scanned by seed + source)
S1_JOB = "cas-meta2-tpntr-20260924021244-11111111-m-20260917"
S2_JOB = "cas-meta2-tpntr-20260924033550-22222222-m-20260917"
BASIS_T = {"kind": "training_pointer", "instance_type": "g7.2xlarge", "instance_seconds_max": 14400,
           "rate_ceiling_usd_per_hour": "2.52", "launcher_ancillary_usd": "1.48"}
BASIS_W = {"kind": "watched_machine", "machines": {"g4dn.2xlarge": "0.752", "g4dn.xlarge": "0.526"},
           "public_address_per_hour_usd": "0.005", "disk_gb_max": 100, "disk_usd_per_gb_month": "0.08",
           "hours_per_month": 730, "client_deadline_minutes_max": 130, "evidence_collection_allowance_usd": "0.00"}
TRAINING = {"M1": (20260917, "UNCHANGED"), "M2": (20260917, "REPAIRED"), "M3": (20260918, "REPAIRED"),
            "M4": (20260919, "REPAIRED"), "M5": (20260918, "UNCHANGED"),
            "R1": (20260917, "REPAIRED"), "R2": (20260918, "REPAIRED"), "R3": (20260919, "REPAIRED")}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def enc(doc):
    return json.dumps(doc, sort_keys=True).encode("utf-8")


class FakeGit:
    def __init__(self):
        self.blobs, self.trees, self.versions, self.dirty = {}, {}, [], []
        self.program_versions = []                  # committed study_spend.py versions (round 3 NOTE-F)
        self.worktree = {}                          # repository path -> bytes: untracked or modified files (round 4)
        self.remote = (True, "test: HEAD is the fetched remote tip")     # round 4 N8
        self.design = "design"                      # the design folder's repository-relative path (round 4)
        self.fail_trees = set()                     # commits whose tree listing fails (round 4 scan failure)

    def read(self, commit, path):
        if (commit, path) not in self.blobs:
            raise FileNotFoundError(path)
        return self.blobs[(commit, path)]

    def names(self, commit, directory):
        if (commit, directory) not in self.trees:
            raise FileNotFoundError(directory)
        return list(self.trees[(commit, directory)])

    def history(self, name):
        versions = self.program_versions if name == "study_spend.py" else self.versions
        return list(reversed(versions))             # newest first, like `git log`

    def uncommitted(self, names):
        return [n for n in names if n in self.dirty]

    def tree_files(self, commit, folder):           # round 4 MAJOR-H (b)
        if commit in self.fail_trees:
            raise OSError("test: git ls-tree %s failed" % commit)
        if commit not in ("HEAD",) and not any(c == commit for c, _p in self.blobs):
            raise FileNotFoundError(commit)
        start = folder.rstrip("/") + "/" if folder.strip("/") else ""
        return sorted((p, "%s:%s" % (c, p)) for c, p in self.blobs if c == commit and p.startswith(start))

    def blob_items(self, oids):
        for oid in oids:
            commit, path = oid.split(":", 1)
            yield oid, self.blobs[(commit, path)]

    def worktree_changes(self, folder, name_ok):
        start = folder.rstrip("/") + "/"
        return [(p, raw) for p, raw in sorted(self.worktree.items())
                if p.startswith(start) and name_ok(p.rsplit("/", 1)[-1])]

    def prefix(self, path):
        return self.design

    def at_remote_tip(self):
        return self.remote


def pointer(job, source, iid, elapsed=2431.2951856, seed=20260917):
    return {"schema": ss.POINTER_SCHEMA, "job": job, "request": {"job": job},
            "authority": {"job": job, "source_sha": source, "instance_type": "g7.2xlarge", "instance_seconds_max": 14400,
                          "worker_config": {"design": {"model_seed": seed}}, "archive_sha256": BUNDLE,
                          "worker_sha256": WORKER, "checker_sha256": CHECKER},
            "preflight": {"instance_type": "g7.2xlarge", "rate_ceiling_usd": "2.52",
                          "observed_on_demand_hourly_usd": ["2.5200000000"]},
            "launch": {"instance_id": iid, "job": job}, "elapsed_seconds": elapsed, "status": "AWS_CANDIDATE_FINISHED",
            "stages": {"execution": "FINISHED", "compute_cleanup": "COMPLETE"},
            "cleanup": {"complete": True, "compute_identity_uncertain": False, "failures": [],
                        "instances_termination_pending": [], "instance_ids": [iid], "instances": {iid: "CONFIRMED_TERMINATED"},
                        "security_group_deleted": True, "roles_removed": True}}


def refusal(job, source, elapsed=25.66626610000094, seed=20260917):
    d = pointer(job, source, None, elapsed, seed)
    d.update(launch=None, status="AWS_CANDIDATE_FAILED",
             stages={"execution": "FAILED", "compute_cleanup": "INCOMPLETE"},
             outcome={"exception_type": "ClientError",
                      "exception": "An error occurred (InsufficientInstanceCapacity) when calling the RunInstances "
                                   "operation (reached max retries: 0): We currently do not have sufficient capacity."})
    d["cleanup"].update(complete=False, compute_identity_uncertain=True, instance_ids=[], instances={},
                        failures=["INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT"])
    return d


def provider(job):
    return {"operation": "run_instances", "state": "FAILED", "job": job,
            "error": "ClientError:An error occurred (InsufficientInstanceCapacity) when calling the RunInstances operation"}


LAUNCH = {"schema": "claude.larger-question-t4-launch/0.1", "instance_id": "i-p1a", "launched_utc": "2026-09-24T05:53:38Z",
          "approved": {"machine": "g4dn.2xlarge", "price_per_hour_usd": 0.752, "dollar_ceiling": 3.0},
          "root_volume_gb": 100, "client_deadline_minutes": 130,
          "identity": {"source_commit": SRC_WATCHED, "worker_sha256": WORKER, "checker_sha256": CHECKER},
          "bundle": {"sha256": "b" * 64}}
WATCH = {"schema": "claude.larger-question-t4-watch/0.1", "instance_id": "i-p1a", "launched_utc": "2026-09-24T05:53:38Z",
         "watch_ended_utc": "2026-09-24T06:28:42Z", "minutes_from_launch_to_watch_end": 35.1, "cost_upper_bound_usd": 0.4489,
         "terminated_confirmed": True, "final_state": "terminated", "volumes_of_this_job_remaining": []}


def slot(sid, status, cap, basis, receipt, mandatory=True, stop=False, **extra):
    s = {"id": sid, "what": sid, "status": status, "mandatory": mandatory, "counts_toward_training_stop": stop,
         "cap_usd": cap, "cap_basis": copy.deepcopy(basis), "receipt": receipt}
    s.update(extra)
    return s


def planned_pointer():
    return {"kind": "pointer_finished", "git_commit": None, "path": None, "sha256": None, "expected": None}


def planned_watched():
    return {"kind": "watched_machine", "launch_record": None, "watch_record": None, "launch_schema": None,
            "watch_schema": None, "expected": None}


def training_slot(sid, mandatory=True):
    seed, arm = TRAINING[sid]
    return slot(sid, "PLANNED", "11.66", BASIS_T, planned_pointer(), mandatory=mandatory, stop=True,
                training={"model_seed": seed, "arm": arm})


class World:
    """A synthetic study: S1 refusal, S2 finished, P1a watched (pre-gate DONE); P1b, P2, M1-M4, E1 planned; M5 optional."""

    def __init__(self, tmp):
        self.tmp, self.git = pathlib.Path(tmp), FakeGit()
        self.receipts = {S1_PATH: refusal(S1_JOB, "1" * 40), S2_PATH: pointer(S2_JOB, "2" * 40, "i-s2")}
        self.providers = {LAST: provider(S1_JOB)}
        self.trees = {"r/s1": ["provider_0024.json", "provider_0025.json", "result.json"]}
        self.files = {"job/launch_record.json": copy.deepcopy(LAUNCH), "job/watch_record.json": copy.deepcopy(WATCH)}
        self.launch, self.watch = self.files["job/launch_record.json"], self.files["job/watch_record.json"]
        e1 = dict(BASIS_W, evidence_collection_allowance_usd="0.10")
        p2 = dict(BASIS_W, machines={"c7i.2xlarge": "0.357"})
        p1a = dict(BASIS_W, machines={"g4dn.2xlarge": "0.752"})
        self.slots = [
            slot("S1", "DONE", "11.66", BASIS_T, {"kind": "pointer_capacity_refusal", "git_commit": C1, "path": S1_PATH,
                                                  "sha256": None, "last_provider_record": {"path": LAST, "sha256": None},
                                                  "expected": {"job": S1_JOB, "source_sha": "1" * 40,
                                                               "instance_type": "g7.2xlarge"}}),
            slot("S2", "DONE", "11.66", BASIS_T, self.pointer_spec(S2_PATH, S2_JOB, "2" * 40, "i-s2")),
            slot("P1a", "DONE", "3.00", p1a, self.watched_spec("job", "i-p1a", "2026-09-24T05:53:38Z", "b" * 64)),
            slot("P1b", "PLANNED", "2.00", BASIS_W, planned_watched()),
            slot("P2", "PLANNED", "1.00", p2, planned_watched()),
            training_slot("M1"), training_slot("M2"), training_slot("M3"), training_slot("M4"),
            slot("E1", "PLANNED", "2.00", e1, planned_watched()),
            training_slot("M5", mandatory=False)]
        self.attempt_rows = []                      # V2 R1: append-only attempt rows
        self.program = self.tmp / "study_spend.py"
        self.program.write_bytes(b"# program under test\n")
        # Slots whose DONE / INVALID row gets NO synthetic committed RUNNING version in build() (round 2 MINOR-B).
        self.uncommitted_running = set()
        # Slots whose admission record stays as typed: build() adds no gate / program / slots-before (round 3 NOTE-F).
        self.bare_admission = set()

    @staticmethod
    def pointer_spec(path, job, source, iid):
        return {"kind": "pointer_finished", "git_commit": C1, "path": path, "sha256": None,
                "expected": {"job": job, "source_sha": source, "instance_id": iid, "instance_type": "g7.2xlarge"}}

    @staticmethod
    def watched_spec(folder, iid, launched, bundle):
        return {"kind": "watched_machine",
                "launch_record": {"path": folder + "/launch_record.json", "sha256": None},
                "watch_record": {"path": folder + "/watch_record.json", "sha256": None},
                "launch_schema": LAUNCH["schema"], "watch_schema": WATCH["schema"],
                "expected": {"instance_id": iid, "launched_utc": launched, "source_commit": SRC_WATCHED,
                             "bundle_sha256": bundle}}

    def by_id(self, sid):
        return next(s for s in self.slots + self.attempt_rows if s["id"] == sid)

    def attempt_row(self, sid, n, status="PLANNED"):
        """V2 R1: append attempt n of slot sid; the row carries only id, slot, attempt and mutable fields."""
        s = self.by_id(sid)
        row = {"id": "%s.%d" % (sid, n), "slot": sid, "attempt": n, "status": status,
               "receipt": planned_pointer() if "training" in s else planned_watched()}
        self.attempt_rows.append(row)
        return row

    def admission(self, sid, source, bundle=None, when=ADMITTED, worker=WORKER, checker=CHECKER):
        s = self.by_id(sid)
        a = {"slot": sid, "admitted_utc": when, "source_sha": source, "bundle_sha256": bundle or BUNDLE,
             "worker_sha256": worker, "checker_sha256": checker}         # V2 R4: every slot binds all four
        training = s.get("training") or (self.by_id(s["slot"]).get("training") if "slot" in s else None)
        if training:
            a.update(model_seed=training["model_seed"], arm=training["arm"])
        s["admission"] = a

    def source_of(self, sid):
        s = self.by_id(sid)
        arm = (s.get("training") or self.by_id(s["slot"])["training"])["arm"]
        return SRC_REPAIRED if arm == "REPAIRED" else SRC_UNCHANGED

    def seed_of(self, sid):
        s = self.by_id(sid)
        return (s.get("training") or self.by_id(s["slot"])["training"])["model_seed"]

    def job_id(self, sid, job_ts=None, seed=None, source=None):
        """The launcher's job id format. Unless job_ts is given, each slot's job is prepared at its own second of
        09:01 (09:01:05 for M1), inside the admission's 300-s validity after ADMITTED 09:00 (V2 R2)."""
        ids = [s["id"] for s in self.slots + self.attempt_rows]
        job_ts = job_ts or "202609240901%02d" % ids.index(sid)
        return "cas-meta2-tpntr-%s-%s-m-%d" % (job_ts, (source or self.source_of(sid))[:8], seed or self.seed_of(sid))

    def done_training(self, sid, elapsed, job_ts=None, seed=None):
        s, src = self.by_id(sid), self.source_of(sid)
        job, path = self.job_id(sid, job_ts, seed), "r/%s/result.json" % sid.lower()
        self.receipts[path] = pointer(job, src, "i-" + sid, elapsed, seed=seed or self.seed_of(sid))
        s["status"], s["receipt"] = "DONE", self.pointer_spec(path, job, src, "i-" + sid)
        self.admission(sid, src)

    def refusal_receipt(self, folder, job, src, seed):
        """A capacity-refusal receipt, its last provider record and its folder listing; returns its receipt spec."""
        self.receipts[folder + "/result.json"] = refusal(job, src, seed=seed)
        self.providers[folder + "/provider_0003.json"] = provider(job)
        self.trees[folder] = ["provider_0003.json", "result.json"]
        return {"kind": "pointer_capacity_refusal", "git_commit": C1, "path": folder + "/result.json",
                "sha256": None, "last_provider_record": {"path": folder + "/provider_0003.json", "sha256": None},
                "expected": {"job": job, "source_sha": src, "instance_type": "g7.2xlarge"}}

    def refused_training(self, sid):
        s, src, job = self.by_id(sid), self.source_of(sid), self.job_id(sid)
        s["status"] = "DONE"
        s["receipt"] = self.refusal_receipt("r/%s" % sid.lower(), job, src, self.seed_of(sid))
        self.admission(sid, src)

    def prelaunch_failure_receipt(self, folder, job, src, seed, run_instances=False):
        """V2 R5: a launcher that failed BEFORE RunInstances (no launch, no instance); returns its closure spec."""
        d = refusal(job, src, seed=seed)
        d.update(status="AWS_CANDIDATE_PREFLIGHT_REFUSED", outcome={"exception_type": "RuntimeError",
                                                                    "exception": "preflight refused"})
        d["cleanup"].update(failures=[])
        self.receipts[folder + "/result.json"] = d
        self.providers[folder + "/provider_0001.json"] = {"operation": "budget_reservation", "state": "REQUESTED",
                                                          "job": job}
        names = ["provider_0001.json", "result.json"]
        if run_instances:
            self.providers[folder + "/provider_0002.json"] = provider(job)
            names.insert(1, "provider_0002.json")
        self.trees[folder] = names
        return {"kind": "pointer_prelaunch_failure", "git_commit": C1, "path": folder + "/result.json", "sha256": None}

    def done_watched(self, sid, folder, machine="g4dn.2xlarge", price=0.752, launched="2026-09-24T09:02:00Z",
                     ended="2026-09-24T09:37:00Z", minutes=35.0, cost=0.4489, deadline=130, bundle="c" * 64,
                     admitted_bundle=None, **watch_extra):
        s, iid = self.by_id(sid), "i-" + sid.lower()
        launch = copy.deepcopy(LAUNCH)
        launch.update(instance_id=iid, launched_utc=launched, client_deadline_minutes=deadline, bundle={"sha256": bundle},
                      approved={"machine": machine, "price_per_hour_usd": price, "dollar_ceiling": float(s["cap_usd"])})
        watch = copy.deepcopy(WATCH)
        watch.update(instance_id=iid, launched_utc=launched, watch_ended_utc=ended, minutes_from_launch_to_watch_end=minutes,
                     cost_upper_bound_usd=cost, **watch_extra)
        self.files[folder + "/launch_record.json"], self.files[folder + "/watch_record.json"] = launch, watch
        s["status"], s["receipt"] = "DONE", self.watched_spec(folder, iid, launched, bundle)
        self.admission(sid, SRC_WATCHED, bundle=admitted_bundle or bundle)

    def invalid(self, sid, reason="test"):
        self.by_id(sid).update(status="INVALID", invalid_reason=reason)

    def build(self, after_pin=None):
        """Write every file, pin every hash, then optionally change something AFTER pinning (a stale receipt)."""
        for path, doc in list(self.receipts.items()) + list(self.providers.items()):
            self.git.blobs[(C1, path)] = enc(doc)
        for folder, names in self.trees.items():
            self.git.trees[(C1, folder)] = names
        for path, doc in self.files.items():
            (self.tmp / path).parent.mkdir(parents=True, exist_ok=True)
            (self.tmp / path).write_bytes(enc(doc))
        for s in self.slots + self.attempt_rows:     # pin a DONE / INVALID receipt, every listed attempt (round 4)
            specs = list(s.get("attempts") or []) + ([s["receipt"]] if s["status"] in ("DONE", "INVALID") else [])
            specs += [s["closure"]["receipt"]] if (s.get("closure") or {}).get("receipt") else []   # V2 R1 / R5
            for r in specs:
                if (r["kind"] in ("pointer_finished", "pointer_capacity_refusal", "pointer_prelaunch_failure")
                        and r.get("path") and r.get("sha256") is None):
                    r["sha256"] = sha(self.git.blobs[(C1, r["path"])])
                if r["kind"] == "pointer_capacity_refusal" and r["last_provider_record"]["sha256"] is None:
                    r["last_provider_record"]["sha256"] = sha(self.git.blobs[(C1, r["last_provider_record"]["path"])])
                if r["kind"] == "watched_machine":
                    for key in ("launch_record", "watch_record"):
                        if r[key] and r[key]["sha256"] is None:
                            r[key]["sha256"] = sha((self.tmp / r[key]["path"]).read_bytes())
        if after_pin:
            after_pin(self)
        program = self.program.read_bytes()                     # the program under test is a committed version
        if not any(raw == program for _commit, raw in self.git.program_versions):
            self.git.program_versions.append(("p%039d" % len(self.git.program_versions), program))
        synthetic = []
        for s in self.slots + self.attempt_rows:    # what `--admit` + "commit and push" would have left (round 2 MINOR-B)
            if (s["status"] in ("DONE", "INVALID", "CLOSED_NO_LAUNCH") and isinstance(s.get("admission"), dict)
                    and s["id"] not in ss.PRE_GATE_DONE and s["id"] not in self.uncommitted_running):
                watched = "training" not in (self.by_id(s["slot"]) if "slot" in s else s)
                planned = copy.deepcopy(s)
                planned.update(status="PLANNED", receipt=planned_watched() if watched else planned_pointer())
                for key in ("admission", "invalid_reason", "attempts", "closure"):
                    planned.pop(key, None)
                before = enc({"schema": ss.SCHEMA, "note": "committed before %s was admitted" % s["id"], "slots": [planned]})
                if s["id"] not in self.bare_admission:          # the fields `--admit` writes (round 3 NOTE-F, V2)
                    a = s["admission"]
                    admitted = ss.utc(a.get("admitted_utc"))
                    a.setdefault("gate", ss.ADMIT_GATE)
                    a.setdefault("program_sha256", sha(program))
                    a.setdefault("slots_sha256_before", sha(before))
                    for field, value in (("gate_version", ss.GATE_VERSION), ("inventory_sha256", "9" * 64),
                                         ("lock_nonce", "n" * 32), ("cap_usd", s.get("cap_usd") or "11.66"),
                                         ("remaining_mandatory_reserve_usd", "0.00"),
                                         ("cumulative_upper_bound_usd", "0.00"), ("main_starts", 0),
                                         ("valid_until_utc", ss.fmt(ss.validity_end(admitted)) if admitted else "?")):
                        a.setdefault(field, value)
                synthetic.append((s, before, watched))
        doc = {"schema": ss.SCHEMA, "ceiling_usd": "60.00",
               "owner_stop": {"usd": "30.00", "before_training_job_number": 3, "rule": "stop"},
               "allowances": {"s3_transfer_per_job_usd": "0.10"}, "open_questions_for_owner_or_codex": ["q"],
               "slots": self.slots, "attempt_rows": self.attempt_rows}
        (self.tmp / "slots.json").write_text(json.dumps(doc), encoding="utf-8")
        self.frozen = ss.definitions_digest(doc)
        for s, before, watched in synthetic:     # the version --admit started from, then the committed RUNNING row
            row = copy.deepcopy(s)
            row.update(status="RUNNING", receipt=planned_watched() if watched else planned_pointer())
            row.pop("invalid_reason", None)
            row.pop("closure", None)
            self.git.versions.append(("%040d" % len(self.git.versions), before))
            self.git.versions.append(("%040d" % len(self.git.versions), enc(dict(doc, slots=[row], attempt_rows=[]))))
        return self

    def edit_slots(self, fn):
        doc = json.loads((self.tmp / "slots.json").read_text(encoding="utf-8"))
        fn(doc)
        (self.tmp / "slots.json").write_text(json.dumps(doc), encoding="utf-8")

    def commit_snapshot(self):
        """Pretend the slots file as it is now was committed."""
        self.git.versions.append(("%040d" % len(self.git.versions), (self.tmp / "slots.json").read_bytes()))

    def run(self, *argv, now=NOW):
        out = io.StringIO()
        with redirect_stdout(out):
            code = ss.main(list(argv) + ["--no-write"], git=self.git, root=self.tmp, slots_file=self.tmp / "slots.json",
                           state_file=self.tmp / "state.json", frozen=self.frozen, program_file=self.program, now=now)
        text = out.getvalue()
        return code, (json.loads(text) if argv and argv[0] in ("--admit", "--launch-check") else text)

    def lock(self):
        path = self.tmp / ss.LOCK_NAME
        return json.loads(path.read_bytes()) if path.exists() else None

    def account(self, now=NOW):
        loaded = ss.load_slots(self.tmp / "slots.json", self.frozen)
        return loaded, ss.account(loaded, self.tmp, self.git, history=self.git.history("slots.json"), now=ss.utc(now))

    def row(self, sid):
        return next(r for r in self.account()[1]["rows"] if r["slot"] == sid)


def world(fn=None, after_pin=None):
    tmp = tempfile.mkdtemp(prefix="ss_test_")
    atexit.register(shutil.rmtree, tmp, True)
    w = World(tmp)
    if fn:
        fn(w)
    return w.build(after_pin)


def rejected(w, sid, needle):
    row = w.row(sid)
    assert row["receipt"] == "REJECTED", row
    assert Decimal(row["counted_usd"]) >= Decimal(row["cap_usd"]), row      # never below the full cap
    assert any(needle in p for p in row["receipt_problems"]), (needle, row["receipt_problems"])


def admit_with(sid, source):
    """V2 R4: every admission binds the source, bundle, worker and checker."""
    return ("--admit", sid, "--source", source, "--bundle", BUNDLE, "--worker", WORKER, "--checker", CHECKER)


def admit_args(sid):
    if sid.split(".")[0] in ("P1b", "P2", "E1"):
        return admit_with(sid, SRC_WATCHED)
    arm = TRAINING.get(sid.split(".")[0], (0, "REPAIRED"))[1]
    return admit_with(sid, SRC_REPAIRED if arm == "REPAIRED" else SRC_UNCHANGED)


# ---------------------------------------------------------------------------------------------------- baseline
def test_baseline_accepts_all_three_receipts_with_exact_bounds():
    w = world()
    assert w.row("S1")["counted_usd"] == "1.60"   # 25.666 s x 2.52/3600 + 1.48 + 0.10 = 1.597966 -> 1.60
    assert w.row("S2")["counted_usd"] == "3.29"   # 2431.295 s -> 3.281907 -> 3.29
    assert w.row("P1a")["counted_usd"] == "0.55"  # max(0.4489, 0.448829) + 0.10 -> 0.55
    assert "ACCEPTED" in w.row("S1")["receipt_pins"]["override"]           # V2 R8 (Codex Q1)
    loaded, acct = w.account()
    assert acct["spent"] == Decimal("5.44") and acct["rejected"] == [] and acct["shared"] == {}
    code, text = w.run()
    assert code == 0 and '"plan_C_worst_case_total_usd": "57.08"' in text, text


# ------------------------------------------------------------------------------------ codex-0007 defect 3: pointer
def test_pointer_elapsed_missing_negative_zero_nonfinite_bool_string_rejected():
    for bad in (None, -5, 0, float("nan"), float("inf"), True, "2431"):
        def fn(w, bad=bad):
            if bad is None:
                del w.receipts[S2_PATH]["elapsed_seconds"]
            else:
                w.receipts[S2_PATH]["elapsed_seconds"] = bad
        rejected(world(fn), "S2", "ELAPSED_SECONDS")


def test_pointer_identity_mismatches_rejected():
    cases = {"JOB_MISMATCH": lambda w: w.receipts[S2_PATH].update(job="job-other"),
             "SOURCE_MISMATCH": lambda w: w.receipts[S2_PATH]["authority"].update(source_sha="9" * 40),
             "INSTANCE_MISMATCH": lambda w: w.receipts[S2_PATH]["launch"].update(instance_id="i-other"),
             "INSTANCE_TYPE_MISMATCH": lambda w: w.receipts[S2_PATH]["authority"].update(instance_type="g6.xlarge"),
             "RATE_CEILING_NOT_BASIS": lambda w: w.receipts[S2_PATH]["preflight"].update(rate_ceiling_usd="3.00"),
             "OBSERVED_RATE": lambda w: w.receipts[S2_PATH]["preflight"].update(observed_on_demand_hourly_usd=["2.60"])}
    for needle, fn in cases.items():
        rejected(world(fn), "S2", needle)


def test_pointer_cleanup_not_confirmed_rejected():
    def incomplete(w):
        w.receipts[S2_PATH]["cleanup"].update(complete=False)

    def uncertain(w):
        w.receipts[S2_PATH]["cleanup"].update(compute_identity_uncertain=True)

    def not_terminated(w):
        w.receipts[S2_PATH]["cleanup"]["instances"]["i-s2"] = "TERMINATION_REQUESTED"
    rejected(world(incomplete), "S2", "CLEANUP_INCOMPLETE")
    rejected(world(uncertain), "S2", "CLEANUP_INCOMPLETE")
    rejected(world(not_terminated), "S2", "CLEANUP_NOT_THIS_ONE_INSTANCE")
    assert world(not_terminated).account()[1]["unconfirmed"] == ["S2"]


def test_pointer_stale_or_missing_receipt_rejected():
    def stale(w):   # the file at the pinned place changed after its hash was frozen
        w.git.blobs[(C1, S2_PATH)] = enc(pointer(S2_JOB, "2" * 40, "i-s2", elapsed=10.0))
    rejected(world(after_pin=stale), "S2", "RECEIPT_HASH_MISMATCH")

    def unrelated(w):   # a real receipt of ANOTHER job, pinned by hash: identity still refuses it
        w.receipts[S2_PATH] = pointer(S1_JOB, "1" * 40, "i-s2")
    rejected(world(unrelated), "S2", "JOB_MISMATCH")

    def missing(w):
        del w.git.blobs[(C1, S2_PATH)]
    rejected(world(after_pin=missing), "S2", "RECEIPT_MISSING")

    def not_an_object(w):
        w.receipts[S2_PATH] = [1, 2, 3]
    rejected(world(not_an_object), "S2", "RECEIPT_NOT_AN_OBJECT")


# ------------------------------------------------------------------------------ S1 capacity-refusal receipt
def test_refusal_rule_rejects_anything_but_an_aws_capacity_refusal():
    def network(w):
        w.receipts[S1_PATH]["outcome"] = {"exception_type": "EndpointConnectionError", "exception": "timeout"}

    def launched(w):
        w.receipts[S1_PATH]["launch"] = {"instance_id": "i-x"}

    def later_call(w):
        w.trees["r/s1"] = w.trees["r/s1"] + ["provider_0026.json"]

    def other_failure(w):
        w.receipts[S1_PATH]["cleanup"]["failures"].append("ROLE_DELETE_FAILED")

    def wrong_last(w):
        w.providers[LAST] = dict(provider(S1_JOB), operation="describe_instances")
    rejected(world(network), "S1", "NOT_AN_AWS_CAPACITY_REFUSAL")
    rejected(world(launched), "S1", "LAUNCH_RECORD_PRESENT")
    rejected(world(later_call), "S1", "A_PROVIDER_CALL_FOLLOWS")
    rejected(world(other_failure), "S1", "CLEANUP_FAILURES_NOT_ONLY")
    rejected(world(wrong_last), "S1", "LAST_PROVIDER_NOT_THE_CAPACITY_REFUSAL")
    assert world(network).account()[1]["unconfirmed"] == ["S1"]      # the override failed: a machine may exist

    def stale_last(w):
        w.git.blobs[(C1, LAST)] = enc(dict(provider(S1_JOB), note="edited"))
    rejected(world(after_pin=stale_last), "S1", "LAST_PROVIDER_HASH_MISMATCH")


# ------------------------------------------------------------------------------------ codex-0007 defect 3: watched
def test_watched_cost_invalid_values_rejected():
    for bad in (-0.01, float("nan"), float("inf"), None, True, "0.4489", 3.01):
        def fn(w, bad=bad):
            if bad is None:
                del w.watch["cost_upper_bound_usd"]
            else:
                w.watch["cost_upper_bound_usd"] = bad
        rejected(world(fn), "P1a", "WATCH_COST_INVALID")


def test_watched_identity_and_cleanup_mismatches_rejected():
    cases = {"INSTANCE_MISMATCH:watch": lambda w: w.watch.update(instance_id="i-other"),
             "INSTANCE_MISMATCH:launch": lambda w: w.launch.update(instance_id="i-other"),
             "LAUNCH_TIME_MISMATCH:watch": lambda w: w.watch.update(launched_utc="2026-09-24T05:00:00Z"),
             "SOURCE_MISMATCH": lambda w: w.launch["identity"].update(source_commit="f" * 40),
             "BUNDLE_MISMATCH": lambda w: w.launch["bundle"].update(sha256="c" * 64),
             "MACHINE_NOT_IN_BASIS": lambda w: w.launch["approved"].update(machine="g5.xlarge"),
             "PRICE_NOT_THE_BASIS_PRICE": lambda w: w.launch["approved"].update(price_per_hour_usd=0.526),
             "DISK_OVER_BASIS": lambda w: w.launch.update(root_volume_gb=200),
             "DEADLINE_OVER_BASIS": lambda w: w.launch.update(client_deadline_minutes=240),
             "LAUNCH_CEILING_NOT_SLOT_CAP": lambda w: w.launch["approved"].update(dollar_ceiling=5.0),
             "NOT_CONFIRMED_TERMINATED": lambda w: w.watch.update(terminated_confirmed=False),
             "VOLUMES_LEFT_OR_UNKNOWN": lambda w: w.watch.update(volumes_of_this_job_remaining=[["vol-1", "available"]]),
             "'unknown:ClientError'": lambda w: w.watch.update(volumes_of_this_job_remaining="unknown:ClientError"),
             "WATCH_COST_BELOW_RECOMPUTED": lambda w: w.watch.update(cost_upper_bound_usd=0.30),
             "WATCH_MINUTES_DISAGREE": lambda w: w.watch.update(minutes_from_launch_to_watch_end=20.0),
             "WATCH_SCHEMA": lambda w: w.watch.update(schema="someone-else/0.1")}
    for needle, fn in cases.items():
        rejected(world(fn), "P1a", needle)


def test_watched_stale_or_missing_files_rejected():
    def stale_watch(w):
        (w.tmp / "job" / "watch_record.json").write_bytes(enc(dict(WATCH, cost_upper_bound_usd=0.40)))

    def stale_launch(w):
        (w.tmp / "job" / "launch_record.json").write_bytes(enc(dict(LAUNCH, note="edited")))

    def missing(w):
        (w.tmp / "job" / "watch_record.json").unlink()
    rejected(world(after_pin=stale_watch), "P1a", "WATCH_RECORD_HASH_MISMATCH")
    rejected(world(after_pin=stale_launch), "P1a", "LAUNCH_RECORD_HASH_MISMATCH")
    rejected(world(after_pin=missing), "P1a", "WATCH_RECORD_MISSING")


def test_receipt_paths_outside_the_design_folder_rejected():      # review NOTE (b)
    for bad in ("C:/job/launch_record.json", "../job/launch_record.json", "job\\launch_record.json", "/job/launch_record.json"):
        def fn(w, bad=bad):
            w.by_id("P1a")["receipt"]["launch_record"]["path"] = bad
        rejected(world(after_pin=fn), "P1a", "LAUNCH_RECORD_PATH_ESCAPES_ROOT")


def test_done_slot_with_incomplete_receipt_spec_counts_full_cap():
    def fn(w):
        w.by_id("P1b")["status"] = "DONE"
    rejected(world(fn), "P1b", "RECEIPT_SPEC_INCOMPLETE")


# ----------------------------------------------------------------------------- codex-0007 defect 1: caps vs basis
def test_cap_below_its_basis_is_an_input_error():
    def fn(w):
        w.by_id("P1a")["cap_usd"] = "1.66"   # the old P1a figure; its basis is 1.6639 + 0.10 -> 1.77
    w = world(fn)
    code, out = w.run(*admit_args("P1b"))
    assert code == 2 and "below its own basis" in out["error"], out
    code, _ = w.run()
    assert code == 2


def test_malformed_or_missing_slots_file_is_exit_2():
    w = world()
    (w.tmp / "slots.json").write_text("{not json", encoding="utf-8")
    assert w.run(*admit_args("P1b"))[0] == 2
    (w.tmp / "slots.json").unlink()
    assert w.run(*admit_args("P1b"))[0] == 2
    w = world(lambda w: w.by_id("P1b").update(status="LAUNCHED"))
    assert w.run(*admit_args("P1b"))[0] == 2
    w = world(lambda w: w.by_id("P1b").update(cap_usd=2.0))
    assert w.run(*admit_args("P1b"))[0] == 2


# ----------------------------------------------------------------------------- codex-0007 defect 2: admission gate
def test_admit_pass_case_writes_running_and_its_record():
    w = world()
    code, out = w.run(*admit_args("P1b"))
    assert code == 0 and out["decision"] == "ADMIT" and out["reasons"] == [], out
    assert "E1" in out["admission_arithmetic"] and "$57.08" in out["admission_arithmetic"], out
    assert "NOT checked here" in out["gate_scope"] and "NOT the training launcher" in out["money_basis"]
    doc = json.loads((w.tmp / "slots.json").read_text(encoding="utf-8"))
    p1b = next(s for s in doc["slots"] if s["id"] == "P1b")
    a = p1b["admission"]
    assert p1b["status"] == "RUNNING" and a["admitted_utc"] == NOW and a["source_sha"] == SRC_WATCHED, p1b
    assert a["bundle_sha256"] == "c" * 64 and a["slots_sha256_before"] == out["slots_file_sha256"]
    assert a["program_sha256"] == sha(w.program.read_bytes())
    assert ss.definitions_digest(doc) == w.frozen                 # the write changed only mutable fields
    code, out = w.run(*admit_args("P2"))                          # review MINOR 3: no second admission
    assert code == 1 and any(r.startswith("ONE_MACHINE_AT_A_TIME:RUNNING=P1b") for r in out["reasons"]), out


def test_admit_needs_source_and_bundle():
    w = world()
    assert w.run("--admit", "P1b")[0] == 2
    assert w.run("--admit", "P1b", "--source", SRC_WATCHED)[0] == 2
    assert w.run("--admit", "P1b", "--source", "e" * 39, "--bundle", "c" * 64)[0] == 2
    assert w.run("--admit", "M1", "--source", SRC_UNCHANGED, "--bundle", "c" * 64)[0] == 2          # V2 R4: and the
    assert w.run("--admit", "P1b", "--source", SRC_WATCHED, "--bundle", BUNDLE, "--worker", WORKER)[0] == 2  # worker,
    assert w.run("--admit", "M1", "--source", SRC_UNCHANGED, "--bundle", BUNDLE, "--checker", CHECKER)[0] == 2  # checker
    assert json.loads((w.tmp / "slots.json").read_text(encoding="utf-8"))["slots"][3]["status"] == "PLANNED"
    assert w.lock() is None                                              # an error releases the lock it took (V2 R2)


def test_admit_refuses_over_ceiling():
    def fn(w):
        w.by_id("E1")["cap_usd"] = "5.00"   # 5.44 + 2.00 + (1.00 + 46.64 + 5.00) = 60.08
    code, out = world(fn).run(*admit_args("P1b"))
    assert code == 1 and any(r.startswith("OVER_CEILING:$60.08") for r in out["reasons"]), out


def test_admit_exactly_at_ceiling_passes():
    def fn(w):
        w.by_id("E1")["cap_usd"] = "4.92"   # total exactly 60.00
    code, out = world(fn).run(*admit_args("P1b"))
    assert code == 0, out


def test_admit_refuses_slot_not_planned_running_or_rejected_receipt():
    code, out = world().run(*admit_with("S2", SRC_REPAIRED))
    assert code == 1 and "SLOT_NOT_PLANNED:DONE" in out["reasons"], out

    def running(w):
        w.by_id("M1")["status"] = "RUNNING"
        w.admission("M1", SRC_UNCHANGED)
    code, out = world(running).run(*admit_args("P2"))
    assert code == 1 and any(r.startswith("ONE_MACHINE_AT_A_TIME") for r in out["reasons"]), out

    def bad(w):
        w.watch["cost_upper_bound_usd"] = -1
    code, out = world(bad).run(*admit_args("P1b"))
    assert code == 1 and "DONE_RECEIPT_REJECTED:P1a" in out["reasons"], out


def test_admit_unknown_slot_is_exit_2():
    code, out = world().run("--admit", "Z9", "--source", SRC_REPAIRED)
    assert code == 2 and out["decision"] == "ERROR"


def test_running_and_invalid_slots_count_full_cap():
    def fn(w):
        w.invalid("P1b")
        w.by_id("M1")["status"] = "RUNNING"
        w.admission("M1", SRC_UNCHANGED)
    loaded, acct = world(fn).account()
    assert acct["spent"] == Decimal("5.44") + Decimal("2.00") + Decimal("11.66")


def test_invalid_without_reason_is_exit_2():
    assert world(lambda w: w.by_id("P1b").update(status="INVALID")).run(*admit_args("P2"))[0] == 2


# ----------------------------------------------------------------------------------------- the owner's $30 stop
def test_owner_stop_triggers_before_the_third_training_job():
    def fn(w):
        w.done_training("M1", 14400)          # 11.66 each
        w.done_training("M2", 14400)
        w.invalid("P1b")                       # 2.00 + 1.00 at full cap
        w.invalid("P2")
    w = world(fn)
    loaded, acct = w.account()
    assert acct["spent"] == Decimal("31.76") and acct["training_started"] == ["M1", "M2"], acct["training_started"]
    code, out = w.run(*admit_args("M3"))
    assert code == 1 and any(r.startswith("OWNER_STOP_TRIGGERED") for r in out["reasons"]), out
    assert not any(r.startswith("OVER_CEILING") for r in out["reasons"]), out   # 31.76 + 11.66 + 11.66 + 2.00 = 57.08
    code, out = w.run(*admit_args("E1"))                                         # the stop halts every admission
    assert code == 1 and any(r.startswith("OWNER_STOP_TRIGGERED") for r in out["reasons"]), out


def test_owner_stop_boundary_and_window():
    loaded = ss.load_slots(world().tmp / "slots.json", None)
    base = {"rows": [], "rejected": [], "shared": {}, "unconfirmed": [], "reserve": Decimal("25.32"),
            "planned_mandatory": [], "optional": [], "running": []}
    at_30 = ss.admit("M3", loaded, dict(base, spent=Decimal("30.00"), training_started=["M1", "M2"]), preview=True)
    over = ss.admit("M3", loaded, dict(base, spent=Decimal("30.01"), training_started=["M1", "M2"]), preview=True)
    after_third = ss.admit("M4", loaded, dict(base, spent=Decimal("30.01"), training_started=["M1", "M2", "M3"]), preview=True)
    assert at_30["decision"] == "ADMIT", at_30             # "passes $30" means strictly more than $30.00
    assert over["decision"] == "REFUSE" and over["owner_stop"].startswith("TRIGGERED"), over
    assert after_third["owner_stop"].startswith("not triggered"), after_third


def test_smoke_runs_do_not_close_the_stop_window():
    loaded, acct = world().account()
    assert acct["training_started"] == []   # S1/S2 are DONE but counts_toward_training_stop is false


def test_capacity_refusals_never_count_as_started():            # review MAJOR 2, the reviewer's exact scenario
    def fn(w):
        for sid in ("R1", "R2", "R3"):
            w.slots.append(training_slot(sid, mandatory=False))
        for sid in ("M1", "M2", "M3"):
            w.refused_training(sid)            # $1.60 each, no machine
        w.done_training("R1", 12000)           # 12,000 s x 2.52/3600 + 1.58 = $9.98 each
        w.done_training("R2", 12000)
    w = world(fn)
    loaded, acct = w.account()
    assert acct["spent"] == Decimal("30.20") and acct["rejected"] == [], (acct["spent"], acct["rejected"])
    assert acct["training_started"] == ["R1", "R2"], acct["training_started"]
    code, out = w.run(*admit_args("R3"))
    assert code == 1 and any(r.startswith("OWNER_STOP_TRIGGERED") and "2 of 3" in r for r in out["reasons"]), out
    assert not any(r.startswith("OVER_CEILING") for r in out["reasons"]), out   # 30.20 + 11.66 + 16.66 = 58.52


# ------------------------------------------------------------------------ review MAJOR 1: one receipt, one slot
def test_a_copied_training_receipt_is_refused_for_both_slots():
    def copy_s2(w):
        m1 = w.by_id("M1")
        m1["status"], m1["receipt"] = "DONE", copy.deepcopy(w.by_id("S2")["receipt"])
        w.admission("M1", SRC_UNCHANGED)
    w = world(after_pin=copy_s2)
    rejected(w, "M1", "RECEIPT_SHARED:")
    rejected(w, "S2", "RECEIPT_SHARED:")
    loaded, acct = w.account()
    assert "M1" not in acct["training_started"] and "job=" + S2_JOB in acct["shared"], acct["shared"]
    code, out = w.run(*admit_args("M2"))
    assert code == 1 and any(r.startswith("RECEIPT_SHARED") for r in out["reasons"]), out


def test_copied_watched_records_are_refused_for_both_slots():
    def copy_p1a(w):
        p1b = w.by_id("P1b")
        p1b["status"], p1b["receipt"] = "DONE", copy.deepcopy(w.by_id("P1a")["receipt"])
        w.admission("P1b", SRC_WATCHED, bundle="b" * 64)
    w = world(after_pin=copy_p1a)
    rejected(w, "P1b", "RECEIPT_SHARED:")
    rejected(w, "P1a", "RECEIPT_SHARED:")
    assert w.run(*admit_args("P2"))[0] == 1


def test_a_done_receipt_must_match_its_admission():
    def no_admission(w):
        w.done_training("M1", 10500)
        del w.by_id("M1")["admission"]
    rejected(world(no_admission), "M1", "NO_ADMISSION_RECORD")
    rejected(world(lambda w: w.done_training("M1", 10500, job_ts="20260924080000")), "M1", "LAUNCH_NOT_AFTER_ADMISSION")
    rejected(world(lambda w: w.done_training("M1", 10500, seed=20260918)), "M1", "SEED_NOT_THE_SLOT_SEED")

    def other_source(w):
        w.done_training("M1", 10500)
        w.by_id("M1")["admission"]["source_sha"] = "9" * 40
    rejected(world(other_source), "M1", "IDENTITY_NOT_THE_ADMITTED:source_sha")                    # V2 R4
    rejected(world(lambda w: w.done_watched("P1b", "p1b", admitted_bundle="d" * 64)), "P1b",
             "IDENTITY_NOT_THE_ADMITTED:bundle_sha256")
    rejected(world(lambda w: w.done_watched("P1b", "p1b", launched="2026-09-24T08:00:00Z", ended="2026-09-24T08:35:00Z")),
             "P1b", "LAUNCH_NOT_AFTER_ADMISSION")
    w = world(lambda w: w.done_watched("P1b", "p1b"))
    assert w.row("P1b")["receipt"] == "ACCEPTED", w.row("P1b")


def test_one_source_per_training_arm():
    def fn(w):
        w.done_training("M1", 10500)           # UNCHANGED arm, source 444...
        w.done_training("M2", 10500)           # REPAIRED arm, source 333...
    w = world(fn)
    code, out = w.run(*admit_with("M3", "5" * 40))
    assert code == 1 and any(r.startswith("ARM_SOURCE_CONFLICT:M2") for r in out["reasons"]), out
    code, out = w.run(*admit_with("M3", SRC_UNCHANGED))
    assert code == 1 and any("M1 is the other arm" in r for r in out["reasons"]), out
    code, out = w.run(*admit_with("M3", SRC_REPAIRED))
    assert code == 0 and out["admission_record"]["model_seed"] == 20260918, out


def test_admitted_job_end_to_end():
    w = world()
    w.commit_snapshot()                                            # --admit starts from a committed slots file
    assert w.run(*admit_args("P1b"))[0] == 0
    w.commit_snapshot()                                            # the runner commits the RUNNING row, then launches
    launched, ended = "2026-09-24T12:03:00Z", "2026-09-24T12:38:00Z"          # inside the 300-s validity (V2 R2)
    doc = json.loads((w.tmp / "slots.json").read_text(encoding="utf-8"))
    w.slots = doc["slots"]
    admission = w.by_id("P1b")["admission"]
    w.done_watched("P1b", "p1b", launched=launched, ended=ended)
    w.by_id("P1b")["admission"] = admission                        # keep the gate's own record
    w.uncommitted_running.add("P1b")                               # no synthetic version: only the real committed one
    w.build()
    assert w.row("P1b")["receipt"] == "ACCEPTED", w.row("P1b")     # the real --admit record passes NOTE-F
    assert w.account()[1]["unconfirmed"] == [], w.row("P1b")       # ... and binds its own launch (round 3)


# ------------------------------------------------------------ review MAJOR 3: frozen numbers, definitions, history
def test_frozen_constants_and_definitions_cannot_change():
    edits = {"FROZEN_CONSTANT_CHANGED": [lambda d: d.update(ceiling_usd="90.00"),
                                         lambda d: d["owner_stop"].update(usd="40.00"),
                                         lambda d: d["owner_stop"].update(before_training_job_number=4),
                                         lambda d: d["allowances"].update(s3_transfer_per_job_usd="0.05")],
             "SLOT_DEFINITIONS_CHANGED": [lambda d: d.update(slots=[s for s in d["slots"] if s["id"] != "S1"]),
                                          lambda d: d["slots"][8].update(mandatory=False),
                                          lambda d: d["slots"][8].update(counts_toward_training_stop=False),
                                          lambda d: d["slots"][9].update(cap_usd="1.90"),
                                          lambda d: d["slots"][2]["receipt"]["expected"].update(instance_id="i-x"),
                                          lambda d: d["slots"][5]["training"].update(model_seed=1)]}
    for needle, fns in edits.items():
        for fn in fns:
            w = world()
            w.edit_slots(fn)
            code, out = w.run(*admit_args("P1b"))
            assert code == 2 and needle in out["error"], (needle, out)


def test_history_is_forward_only():
    def done_m1(w):
        w.done_training("M1", 10500)
    w = world(done_m1)
    w.commit_snapshot()
    assert w.run()[0] == 0
    w.edit_slots(lambda d: d["slots"][5].update(status="PLANNED", receipt=planned_pointer(), admission=None))
    code, out = w.run(*admit_args("P1b"))
    assert code == 2 and "HISTORY_VIOLATION: M1 was DONE" in out["error"], out

    w = world(done_m1)
    w.commit_snapshot()
    w.edit_slots(lambda d: d["slots"][5]["receipt"].update(sha256="0" * 64))       # a committed DONE pin changed
    assert "HISTORY_VIOLATION" in w.run(*admit_args("P1b"))[1]["error"]

    w = world(done_m1)
    w.commit_snapshot()
    w.edit_slots(lambda d: d["slots"][5].update(status="INVALID", invalid_reason="bad seed"))   # DONE -> INVALID is allowed
    assert w.run()[0] == 0
    w.commit_snapshot()
    w.edit_slots(lambda d: d["slots"][5].update(invalid_reason="edited"))                       # INVALID never changes
    assert "HISTORY_VIOLATION: M1 was INVALID" in w.run(*admit_args("P1b"))[1]["error"]

    def running(w):
        w.by_id("M1")["status"] = "RUNNING"
        w.admission("M1", SRC_UNCHANGED)
    w = world(running)
    w.commit_snapshot()
    w.edit_slots(lambda d: d["slots"][5]["admission"].update(source_sha="9" * 40))
    assert "HISTORY_VIOLATION: M1 was RUNNING" in w.run(*admit_args("P1b"))[1]["error"]


def test_admission_needs_committed_slots_and_program():
    w = world()
    w.git.dirty = ["slots.json"]
    code, out = w.run(*admit_args("P1b"))
    assert code == 1 and any(r.startswith("UNCOMMITTED_CHANGES:slots.json") for r in out["reasons"]), out
    w.git.dirty = ["study_spend.py"]
    code, out = w.run(*admit_args("P1b"))
    assert code == 1 and any(r.startswith("UNCOMMITTED_CHANGES:study_spend.py") for r in out["reasons"]), out


# ------------------------------------------------------------------ review MAJOR 4: a broken basis is never undercounted
def test_watched_basis_breach_counts_the_recorded_cost_even_after_invalid():
    def breach(w):
        w.done_watched("P1b", "p1b", launched="2026-09-24T09:02:00Z", ended="2026-09-24T13:02:00Z", minutes=240.0,
                       cost=3.0719, deadline=240)
    w = world(breach)
    rejected(w, "P1b", "DEADLINE_OVER_BASIS")
    assert w.row("P1b")["counted_usd"] == "3.18", w.row("P1b")    # max(2.00 cap, 3.0719 + 0.10) -> 3.18, not 2.00

    def breach_invalid(w):
        breach(w)
        w.invalid("P1b", "ran past its deadline basis")
    w = world(breach_invalid)
    assert w.row("P1b")["counted_usd"] == "3.18", w.row("P1b")
    loaded, acct = w.account()
    assert acct["spent"] == Decimal("8.62"), acct["spent"]          # 5.44 + 3.18, not 5.44 + 2.00


def test_training_basis_breach_counts_the_recorded_elapsed_even_after_invalid():
    def over(w):
        w.done_training("M1", 20000)          # over the 14,400 s basis: 20000/3600 x 2.52 + 1.58 = 15.58
    rejected(world(over), "M1", "ELAPSED_OVER_BASIS")
    assert world(over).row("M1")["counted_usd"] == "15.58"

    def over_invalid(w):
        over(w)
        w.invalid("M1")
    assert world(over_invalid).row("M1")["counted_usd"] == "15.58"


def test_unconfirmed_cleanup_blocks_admission_even_after_invalid():
    def fn(w):
        w.done_watched("P1b", "p1b", terminated_confirmed=False)
        w.invalid("P1b")
    code, out = world(fn).run(*admit_args("P2"))
    assert code == 1 and any(r.startswith("CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b") for r in out["reasons"]), out


# --------------------------------------------------------------------------------------------- review MINORs
def test_a_cheaper_listed_machine_is_checked_at_its_own_price():
    w = world(lambda w: w.done_watched("P1b", "p1b", machine="g4dn.xlarge", price=0.526, cost=0.32))
    row = w.row("P1b")
    assert row["receipt"] == "ACCEPTED" and row["counted_usd"] == "0.42", row   # max(0.32, 0.316143) + 0.10
    rejected(world(lambda w: w.done_watched("P1b", "p1b", machine="g4dn.xlarge", price=0.752, cost=0.46)), "P1b",
             "PRICE_NOT_THE_BASIS_PRICE")
    rejected(world(lambda w: w.done_watched("P2", "p2", machine="c7i.4xlarge", price=0.714, cost=0.45)), "P2",
             "MACHINE_NOT_IN_BASIS")


def test_missing_preconditions_print_not_assessed():
    def fn(w):
        w.by_id("P2")["preconditions_outside_money_gate"] = ["the HSET-2 build code review passes"]
    w = world(fn)
    code, out = w.run(*admit_args("M4"))
    assert out["preconditions_outside_money_gate"].startswith("NOT ASSESSED"), out
    code, out = world(fn).run(*admit_args("P2"))
    assert out["preconditions_outside_money_gate"] == ["the HSET-2 build code review passes"], out


def test_report_mode_exit_1_when_a_done_receipt_is_rejected():
    code, text = world(lambda w: w.watch.update(terminated_confirmed=False)).run()
    assert code == 1 and "NOT_CONFIRMED_TERMINATED" in text, text


# ------------------------------------ round 2 MAJOR-A: read the receipt first; fail closed on an unconfirmed cleanup
def p1b_breach(w, bundle_field="c" * 64, **watch_extra):
    """P1b ran 240 min with a watcher cost of $3.0719 (over its 130-min basis), then was marked INVALID."""
    w.done_watched("P1b", "p1b", launched="2026-09-24T09:02:00Z", ended="2026-09-24T13:02:00Z", minutes=240.0,
                   cost=3.0719, deadline=240, **watch_extra)
    w.by_id("P1b")["receipt"]["expected"]["bundle_sha256"] = bundle_field
    w.invalid("P1b", "ran past its deadline basis")


def m1_uncertain(w, expected_instance):
    """M1 ran 20,000 s; the launcher could not confirm its cleanup or the machine's identity; then INVALID."""
    w.done_training("M1", 20000)
    r = w.receipts["r/m1/result.json"]
    r["launch"]["instance_id"] = "UNKNOWN"
    r["stages"]["compute_cleanup"] = "INCOMPLETE"
    r["cleanup"].update(complete=False, compute_identity_uncertain=True, instance_ids=[], instances={},
                        failures=["INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT"])
    w.by_id("M1")["receipt"]["expected"]["instance_id"] = expected_instance
    w.invalid("M1", "cleanup and identity unconfirmed")


def test_round2_p1_an_empty_spec_field_no_longer_undercounts():
    probe, twin = world(lambda w: p1b_breach(w, bundle_field="")), world(p1b_breach)
    for w in (probe, twin):
        row = w.row("P1b")
        assert row["counted_usd"] == "3.18" and "cleanup" not in row, row      # was $2.00 for the probe
        assert w.account()[1]["spent"] == Decimal("8.62")
    (pc, po), (tc, to) = probe.run(*admit_args("P2")), twin.run(*admit_args("P2"))
    # The probe decides exactly as its complete-spec twin. V2 R5 (Codex Q4): a basis breach whose cleanup is confirmed
    # is counted at what it recorded AND latches every admission shut (round 1 had let it continue).
    assert (pc, po["decision"], po["total_usd"], po["reasons"]) == (tc, to["decision"], to["total_usd"], to["reasons"])
    assert po["total_usd"] == "58.26", po
    assert pc == 1 and any(r.startswith("LIMIT_BREACH_LATCHED:P1b") for r in po["reasons"]), po


def test_round2_p2_unconfirmed_cleanup_with_an_empty_spec_field_blocks():
    w = world(lambda w: p1b_breach(w, bundle_field="", terminated_confirmed=False, final_state="running"))
    assert w.row("P1b")["counted_usd"] == "3.18" and w.row("P1b")["cleanup"].startswith("UNCONFIRMED"), w.row("P1b")
    code, out = w.run(*admit_args("P2"))
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b" in out["reasons"], out


def test_round2_p3_unconfirmed_cleanup_with_a_stale_pin_blocks():
    def stale(note_state):
        def after_pin(w):   # the watch record on disk changed after its hash was pinned
            path = w.tmp / "p1b" / "watch_record.json"
            doc = json.loads(path.read_bytes())
            doc.update(note="rewritten after pinning", **note_state)
            path.write_bytes(enc(doc))
        return after_pin
    unconfirmed = {"terminated_confirmed": False, "final_state": "running"}
    w = world(lambda w: p1b_breach(w, **unconfirmed), after_pin=stale(unconfirmed))
    assert w.row("P1b")["counted_usd"] == "3.18", w.row("P1b")
    code, out = w.run(*admit_args("P2"))
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b" in out["reasons"], out
    # A stale record never confirms, even one rewritten to say "terminated" after its pin was taken.
    w = world(lambda w: p1b_breach(w, **unconfirmed),
              after_pin=stale({"terminated_confirmed": True, "final_state": "terminated"}))
    code, out = w.run(*admit_args("P2"))
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b" in out["reasons"], out


def test_round2_p4_empty_instance_id_is_counted_and_blocks():
    w = world(lambda w: m1_uncertain(w, ""))
    assert w.row("M1")["counted_usd"] == "15.58", w.row("M1")                # was $11.66
    assert w.account()[1]["unconfirmed"] == ["M1"]
    code, out = w.run(*admit_args("P1b"))                                     # was exit 0 at $57.08
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out
    assert "OVER_CEILING:$61.00 > $60.00" in out["reasons"], out


def test_round2_p5_positive_control_complete_spec():
    w = world(lambda w: m1_uncertain(w, "i-M1"))
    assert w.row("M1")["counted_usd"] == "15.58", w.row("M1")
    code, out = w.run(*admit_args("P1b"))
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out
    assert "OVER_CEILING:$61.00 > $60.00" in out["reasons"], out


def test_round2_no_readable_receipt_is_unconfirmed():
    w = world(lambda w: w.invalid("P1b", "never ran?"))                     # INVALID naming no receipt at all
    assert w.account()[1]["unconfirmed"] == ["P1b"] and "no readable receipt" in w.row("P1b")["cleanup"]
    code, out = w.run(*admit_args("P2"))
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b" in out["reasons"], out

    def gone(w):                                                             # the pinned receipt is not in git
        del w.git.blobs[(C1, "r/m1/result.json")]
    w = world(lambda w: w.done_training("M1", 10500), after_pin=gone)
    rejected(w, "M1", "RECEIPT_MISSING")
    assert w.account()[1]["unconfirmed"] == ["M1"]

    def bad_commit(w):                                                       # an option-like commit is never read
        w.by_id("M1")["receipt"]["git_commit"] = "--output=x"
    w = world(lambda w: w.done_training("M1", 10500), after_pin=bad_commit)
    assert w.account()[1]["unconfirmed"] == ["M1"]
    calls = []

    class Spy:
        def read(self, commit, path):
            calls.append(commit)
            return b"{}"
    assert ss.read_git_lenient(Spy(), "--output=x", "r/m1/result.json") is None and calls == []


def test_round2_a_proven_capacity_refusal_is_not_unconfirmed():
    def refused_invalid(w):
        w.refused_training("M1")
        w.invalid("M1", "capacity refusal")
    assert world(refused_invalid).account()[1]["unconfirmed"] == []

    def refused_wrong_type(w):                                               # rejected, but the refusal is proven
        w.refused_training("M1")
        w.receipts["r/m1/result.json"]["authority"]["instance_type"] = "g6.xlarge"
    w = world(refused_wrong_type)
    rejected(w, "M1", "INSTANCE_TYPE_MISMATCH")
    assert w.account()[1]["unconfirmed"] == []

    def refused_wrong_source(w):
        w.refused_training("M1")
        w.by_id("M1")["admission"]["source_sha"] = "9" * 40
    w = world(refused_wrong_source)
    rejected(w, "M1", "IDENTITY_NOT_THE_ADMITTED:source_sha")
    # V2 R4 (Codex Q8): a wrong source no longer leaves the cleanup unconfirmed (the refusal is still this slot's and
    # still proven), but it blocks the study (WRONG_IDENTITY_BLOCKS_THE_STUDY). Round 3 had made it UNCONFIRMED.
    acct = w.account()[1]
    assert acct["unconfirmed"] == [] and "M1" in acct["wrong_identity"], acct["wrong_identity"]

    def refused_unproven(w):                                                 # a later provider call breaks the proof
        refused_invalid(w)
        w.trees["r/m1"] = w.trees["r/m1"] + ["provider_0004.json"]
    assert world(refused_unproven).account()[1]["unconfirmed"] == ["M1"]

    def refused_stale(w):                                                    # a stale pin is never a proof
        w.by_id("M1")["receipt"]["sha256"] = "0" * 64
    assert world(refused_invalid, after_pin=refused_stale).account()[1]["unconfirmed"] == ["M1"]


def test_round2_running_past_its_lifetime_is_unconfirmed():
    def running(sid, when):
        def fn(w):
            w.by_id(sid)["status"] = "RUNNING"
            w.admission(sid, SRC_UNCHANGED if sid == "M1" else SRC_WATCHED, bundle="c" * 64, when=when)
        return fn
    # M1: 14,400 s lifetime. Admitted 09:00, now 12:00: still inside it. Admitted 07:59:59: past it.
    assert world(running("M1", "2026-09-24T09:00:00Z")).account()[1]["unconfirmed"] == []
    w = world(running("M1", "2026-09-24T07:59:59Z"))
    assert w.account()[1]["unconfirmed"] == ["M1"] and w.row("M1")["lifetime"].startswith("PAST"), w.row("M1")
    code, text = w.run()
    assert code == 1, text
    # P1b: 130-min client deadline. Admitted 09:00, now 12:00: past it.
    assert world(running("P1b", "2026-09-24T09:00:00Z")).account()[1]["unconfirmed"] == ["P1b"]


# ------------------------------------------ round 2 MINOR-B: a DONE admission must have been committed as RUNNING
def test_round2_p6_a_hand_written_admission_is_refused():
    def hand_written(w):
        w.done_training("M1", 10500)
        w.by_id("M1")["admission"]["admitted_utc"] = "2000-01-01T00:00:00Z"
        w.uncommitted_running.add("M1")                                      # --admit never ran; no RUNNING commit
    w = world(hand_written)
    rejected(w, "M1", "ADMISSION_NOT_IN_A_COMMITTED_RUNNING_ROW")
    assert "M1" not in w.account()[1]["training_started"]
    code, out = w.run(*admit_args("M2"))
    assert code == 1 and "DONE_RECEIPT_REJECTED:M1" in out["reasons"], out

    def committed(w):                                                        # control: a gate record, committed RUNNING
        w.done_training("M1", 10500)
    assert world(committed).row("M1")["receipt"] == "ACCEPTED"

    def committed_2000(w):          # the hand-written date, committed RUNNING: a launch that far after its admission
        committed(w)                # is refused (V2 R2: outside admission time + the 300-s validity)
        w.by_id("M1")["admission"]["admitted_utc"] = "2000-01-01T00:00:00Z"
    rejected(world(committed_2000), "M1", "LAUNCH_AFTER_THE_ADMISSION_VALIDITY")
    w = world(committed)                                                     # the DONE row's record differs from the
    w.edit_slots(lambda d: d["slots"][5]["admission"].update(admitted_utc="2026-09-24T09:30:00Z"))   # committed one
    code, out = w.run(*admit_args("M2"))
    assert code == 2 and "HISTORY_VIOLATION: M1 was RUNNING" in out["error"], out


# ------------------------------------ round 3 MAJOR-E: the verified receipt must be THIS slot's admitted launch
OLDER_TS = "20260917120000"         # another job, launched 2026-09-17, a week before ADMITTED (2026-09-24T09:00:00Z)


def other_training_receipt(w, sid, job_ts=OLDER_TS, seed=None, source=None):
    """A clean training receipt of ANOTHER job, claimed by no slot. Returns (path, job, instance id)."""
    seed, source = seed or w.by_id(sid)["training"]["model_seed"], source or w.source_of(sid)
    job = w.job_id(sid, job_ts=job_ts, seed=seed, source=source)
    tag = "%s-%d-%s" % (job_ts, seed, source[:4])
    path, iid = "r/other/%s/result.json" % tag, "i-other-" + tag
    w.receipts[path] = pointer(job, source, iid, seed=seed)
    return path, job, iid


def m1_names(ids=True, invalid=True, **other):
    """M1 admitted 09:00 and committed RUNNING; its own machine is never shown gone; its row names another job's clean
    receipt (ids empty: the verifier's N1a; that job's own ids: N1b); then INVALID, or left DONE."""
    def fn(w):
        path, job, iid = other_training_receipt(w, "M1", **other)
        m1 = w.by_id("M1")
        m1["status"] = "DONE"
        m1["receipt"] = w.pointer_spec(path, job if ids else "", other.get("source") or w.source_of("M1"),
                                       iid if ids else "")
        w.admission("M1", w.source_of("M1"))
        if invalid:
            w.invalid("M1", "launch trouble")
    return fn


def p1b_names_older_watched_records(ids, invalid=True):
    """P1b admitted 09:00 (bundle c...) and committed RUNNING; its row names an older job's launch and watch records
    (launched 2026-09-20, bundle b..., terminated, claimed by no slot); ids empty (N2a) or that job's own (N2b)."""
    def fn(w):
        launched = "2026-09-20T10:00:00Z"
        launch, watch = copy.deepcopy(LAUNCH), copy.deepcopy(WATCH)
        launch.update(instance_id="i-older", launched_utc=launched, bundle={"sha256": "b" * 64},
                      approved={"machine": "g4dn.2xlarge", "price_per_hour_usd": 0.752, "dollar_ceiling": 2.0})
        watch.update(instance_id="i-older", launched_utc=launched, watch_ended_utc="2026-09-20T10:35:00Z",
                     minutes_from_launch_to_watch_end=35.0)
        w.files["older/launch_record.json"], w.files["older/watch_record.json"] = launch, watch
        p1b = w.by_id("P1b")
        p1b["status"] = "DONE"
        p1b["receipt"] = w.watched_spec("older", "i-older" if ids else "", launched if ids else "",
                                        "b" * 64 if ids else "")
        w.admission("P1b", SRC_WATCHED, bundle="c" * 64)
        if invalid:
            w.invalid("P1b", "launch trouble")
    return fn


def unconfirmed_not_this_launch(w, sid, needle):
    row = w.row(sid)
    assert w.account()[1]["unconfirmed"] == [sid], row
    assert "not this slot's admitted launch" in row["cleanup"] and needle in row["cleanup"], row["cleanup"]


def test_round3_n1a_another_jobs_receipt_with_empty_ids_no_longer_confirms():
    w = world(m1_names(ids=False))
    assert w.row("M1")["counted_usd"] == "11.66", w.row("M1")
    unconfirmed_not_this_launch(w, "M1", "LAUNCHED_BEFORE_ADMISSION")
    code, out = w.run(*admit_args("M2"))                                     # was exit 0 ADMIT, total $57.08
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out


def test_round3_n1b_another_jobs_receipt_with_its_own_ids_no_longer_confirms():
    w = world(m1_names(ids=True))
    unconfirmed_not_this_launch(w, "M1", "LAUNCHED_BEFORE_ADMISSION")
    code, out = w.run(*admit_args("M2"))                                     # was exit 0 ADMIT, total $57.08
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out
    w = world(m1_names(ids=True, invalid=False))                             # as DONE: rejected (as before) and now
    rejected(w, "M1", "LAUNCH_NOT_AFTER_ADMISSION")                          # also unconfirmed
    assert w.account()[1]["unconfirmed"] == ["M1"]


def test_round3_n2a_n2b_another_jobs_watched_records_no_longer_confirm():
    for ids in (False, True):
        w = world(p1b_names_older_watched_records(ids))
        assert w.row("P1b")["counted_usd"] == "2.00", w.row("P1b")
        unconfirmed_not_this_launch(w, "P1b", "LAUNCHED_BEFORE_ADMISSION")
        code, out = w.run(*admit_args("P2"))                                 # was exit 0 ADMIT, total $57.08
        assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b" in out["reasons"], (ids, out)
    w = world(p1b_names_older_watched_records(True, invalid=False))
    rejected(w, "P1b", "IDENTITY_NOT_THE_ADMITTED:bundle_sha256")                  # V2 R4
    rejected(w, "P1b", "LAUNCH_NOT_AFTER_ADMISSION")


def test_round3_n3_another_jobs_capacity_refusal_is_no_longer_proven():
    def names_older_refusal(invalid):
        def fn(w):
            m1, src = w.by_id("M1"), w.source_of("M1")
            m1["status"] = "DONE"
            m1["receipt"] = w.refusal_receipt("r/older_refusal", w.job_id("M1", job_ts=OLDER_TS), src, 20260917)
            w.admission("M1", src)
            if invalid:
                w.invalid("M1", "capacity refusal")
        return fn
    w = world(names_older_refusal(True))
    unconfirmed_not_this_launch(w, "M1", "LAUNCHED_BEFORE_ADMISSION")
    code, out = w.run(*admit_args("M2"))                                     # was exit 0 ADMIT, total $57.08
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out
    rejected(world(names_older_refusal(False)), "M1", "LAUNCH_NOT_AFTER_ADMISSION")


def test_round3_launch_window_seed_and_source_bind_the_cleanup():
    # M1 admitted 09:00; V2 R2: the admission is valid 300 s, so its launch must lie in [09:00:00, 09:05:00).
    for ts in ("20260924090000", "20260924090459"):                          # positive: inside the validity
        w = world(m1_names(job_ts=ts))
        assert w.account()[1]["unconfirmed"] == [] and "cleanup" not in w.row("M1"), (ts, w.row("M1"))
        code, out = w.run(*admit_args("M2"))
        assert code == 0, (ts, out)
    unconfirmed_not_this_launch(world(m1_names(job_ts="20260924090500")), "M1", "LAUNCHED_AFTER_THE_ADMISSION_VALIDITY")
    unconfirmed_not_this_launch(world(m1_names(job_ts="20260924085959")), "M1", "LAUNCHED_BEFORE_ADMISSION")
    rejected(world(m1_names(job_ts="20260924090500", invalid=False)), "M1", "LAUNCH_AFTER_THE_ADMISSION_VALIDITY")
    # Inside the validity, but another seed: not this slot's launch.
    unconfirmed_not_this_launch(world(m1_names(job_ts="20260924090300", seed=20260918)), "M1", "SEED_NOT_THE_SLOT_SEED")
    # The other arm's source with M1's seed (M2 shares seed 20260917): V2 R4 (Codex Q8) inspects the machine (cleanup
    # confirmed) and blocks the study through the wrong identity instead.
    w = world(m1_names(job_ts="20260924090300", source=SRC_REPAIRED))
    acct = w.account()[1]
    assert acct["unconfirmed"] == [] and "IDENTITY_NOT_THE_ADMITTED:source_sha" in acct["wrong_identity"]["M1"][0], acct
    code, out = w.run(*admit_args("M2"))
    assert code == 1 and any(r.startswith("WRONG_IDENTITY_BLOCKS_THE_STUDY:M1") for r in out["reasons"]), out

    def no_time(w):                                                          # a job id that carries no time
        m1_names(job_ts="20260924090300")(w)
        w.receipts[w.by_id("M1")["receipt"]["path"]]["job"] = "job-without-a-time"
        w.by_id("M1")["receipt"]["expected"]["job"] = "job-without-a-time"
    unconfirmed_not_this_launch(world(no_time), "M1", "RECEIPT_SHOWS_NO_LAUNCH_TIME")
    # P1b: V2 R2: its launch must lie in [09:00:00, 09:05:00) too.
    for launched, ended, ok in (("2026-09-24T09:04:59Z", "2026-09-24T09:39:59Z", True),
                                ("2026-09-24T09:05:00Z", "2026-09-24T09:40:00Z", False)):
        def fn(w, launched=launched, ended=ended):
            w.done_watched("P1b", "p1b", launched=launched, ended=ended)
            w.invalid("P1b", "operator error")
        w = world(fn)
        if ok:
            assert w.account()[1]["unconfirmed"] == [], w.row("P1b")
        else:
            unconfirmed_not_this_launch(w, "P1b", "LAUNCHED_AFTER_THE_ADMISSION_VALIDITY")


def test_round3_an_invalid_rows_admission_must_be_committed_running():
    def own_receipt_invalid(w):
        w.done_training("M1", 10500)                                         # M1's own clean receipt, launched 09:15
        w.invalid("M1", "operator error")
    w = world(own_receipt_invalid)                                           # control: committed RUNNING -> confirmed
    assert w.account()[1]["unconfirmed"] == [] and "cleanup" not in w.row("M1"), w.row("M1")
    assert w.run(*admit_args("M2"))[0] == 0

    def never_committed(w):
        own_receipt_invalid(w)
        w.uncommitted_running.add("M1")
    w = world(never_committed)
    assert w.account()[1]["unconfirmed"] == ["M1"], w.row("M1")
    assert "ADMISSION_NOT_IN_A_COMMITTED_RUNNING_ROW" in w.row("M1")["cleanup"], w.row("M1")
    code, out = w.run(*admit_args("M2"))                                     # round 2: exit 0 ADMIT
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out

    def no_record(w):
        own_receipt_invalid(w)
        del w.by_id("M1")["admission"]
    w = world(no_record)
    assert w.account()[1]["unconfirmed"] == ["M1"] and "NO_ADMISSION_RECORD" in w.row("M1")["cleanup"], w.row("M1")


# ------------------------------------------------ round 3 NOTE-F: the admission record must be one `--admit` wrote
def test_round3_n4_a_bare_admission_record_is_refused():
    def bare(when):
        def fn(w):
            w.done_training("M1", 10500)
            w.by_id("M1")["admission"]["admitted_utc"] = when
            w.bare_admission.add("M1")          # slot, time, source, seed, arm only; committed RUNNING as typed
        return fn
    w = world(bare("2000-01-01T00:00:00Z"))                                  # the verifier's N4: was ACCEPTED, started
    rejected(w, "M1", "ADMISSION_NOT_WRITTEN_BY_THE_GATE")
    assert "M1" not in w.account()[1]["training_started"]
    code, out = w.run(*admit_args("M2"))
    assert code == 1 and "DONE_RECEIPT_REJECTED:M1" in out["reasons"], out
    problems = world(bare(ADMITTED)).row("M1")["receipt_problems"]          # inside the window: NOTE-F alone refuses
    for needle in ("ADMISSION_NOT_WRITTEN_BY_THE_GATE", "ADMISSION_PROGRAM_NOT_A_COMMITTED_STUDY_SPEND",
                   "ADMISSION_SLOTS_SHA256_BEFORE_MISSING"):
        assert any(needle in p for p in problems), (needle, problems)
    assert not any("LAUNCH" in p for p in problems), problems
    for field, value, needle in (("gate", "typed by hand", "ADMISSION_NOT_WRITTEN_BY_THE_GATE"),
                                 ("program_sha256", "0" * 64, "ADMISSION_PROGRAM_NOT_A_COMMITTED_STUDY_SPEND"),
                                 ("slots_sha256_before", "0" * 64,
                                  "ADMISSION_SLOTS_BEFORE_NOT_THE_COMMITTED_VERSION_BEFORE_RUNNING")):
        def one(w, field=field, value=value, invalid=False):
            w.done_training("M1", 10500)
            w.by_id("M1")["admission"][field] = value
            if invalid:
                w.invalid("M1", "operator error")
        rejected(world(one), "M1", needle)
        w = world(lambda w, one=one: one(w, invalid=True))                   # INVALID: the cleanup is not tied to it
        assert w.account()[1]["unconfirmed"] == ["M1"] and needle in w.row("M1")["cleanup"], (needle, w.row("M1"))


def test_round3_admission_record_positive_controls():
    def older_program(w):                   # any committed study_spend.py counts, not only the newest
        w.done_training("M1", 10500)
        w.git.program_versions.append(("o" * 40, b"# an older committed program\n"))
        w.by_id("M1")["admission"]["program_sha256"] = sha(b"# an older committed program\n")
    assert world(older_program).row("M1")["receipt"] == "ACCEPTED"
    # The RUNNING row committed twice: slots_sha256_before is the version before the FIRST one.
    w = world(lambda w: w.done_training("M1", 10500))
    w.git.versions.append(("r" * 40, w.git.versions[-1][1]))
    assert w.row("M1")["receipt"] == "ACCEPTED", w.row("M1")


# --------------------------------- round 4 MAJOR-H: one admission, several launch attempts (verification probes N6a-N6d)
def training_attempt(w, sid, folder, job_ts, refused=False, elapsed=10500, uncertain=False):
    """One launch attempt of a training slot under r/<folder>/, prepared at job_ts (the slot's seed and its arm's
    source). Returns its receipt spec. uncertain: the machine ran, but its cleanup and identity are unconfirmed."""
    s, src = w.by_id(sid), w.source_of(sid)
    seed, job = s["training"]["model_seed"], w.job_id(sid, job_ts=job_ts)
    if refused:
        return w.refusal_receipt("r/" + folder, job, src, seed)
    path, iid = "r/%s/result.json" % folder, "i-%s-%s" % (sid, job_ts)
    w.receipts[path] = pointer(job, src, iid, elapsed, seed=seed)
    if uncertain:
        r = w.receipts[path]
        r["launch"]["instance_id"] = "UNKNOWN"
        r["stages"]["compute_cleanup"] = "INCOMPLETE"
        r["cleanup"].update(complete=False, compute_identity_uncertain=True, instance_ids=[], instances={},
                            failures=["INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT"])
    return w.pointer_spec(path, job, src, iid)


def set_row(w, sid, named, listed=None, status="DONE"):
    """The row names `named`; `listed` (if given) is its attempts list; admitted 09:00 and committed RUNNING."""
    s = w.by_id(sid)
    s["status"], s["receipt"] = status, named
    if listed is not None:
        s["attempts"] = listed
    w.admission(sid, SRC_WATCHED if "training" not in s else w.source_of(sid), bundle="c" * 64)


def watched_attempt(w, sid, folder, launched, ended, running=False):
    """One launch attempt of a watched slot: launch and watch records in <folder>/; returns its receipt spec."""
    iid = "i-%s-%s" % (sid.lower(), launched[11:16].replace(":", ""))
    launch, watch = copy.deepcopy(LAUNCH), copy.deepcopy(WATCH)
    launch.update(instance_id=iid, launched_utc=launched, bundle={"sha256": "c" * 64},
                  approved={"machine": "g4dn.2xlarge", "price_per_hour_usd": 0.752,
                            "dollar_ceiling": float(w.by_id(sid)["cap_usd"])})
    watch.update(instance_id=iid, launched_utc=launched, watch_ended_utc=ended, minutes_from_launch_to_watch_end=35.0)
    if running:
        watch.update(terminated_confirmed=False, final_state="running")
    w.files[folder + "/launch_record.json"], w.files[folder + "/watch_record.json"] = launch, watch
    return w.watched_spec(folder, iid, launched, "c" * 64)


def unlisted(w, sid, needle):
    row = w.row(sid)
    assert sid in w.account()[1]["unconfirmed"], row
    assert "not listed in its row" in row["cleanup"] and needle in row["cleanup"], row["cleanup"]


def test_round4_n6a_an_unlisted_capacity_refusal_is_found():
    def fn(w):          # attempt 1 (09:01) refused by AWS, moved aside; attempt 2 (09:03) finished; the row names only 2
        training_attempt(w, "M1", "m1_attempt1", "20260924090100", refused=True)
        set_row(w, "M1", training_attempt(w, "M1", "m1", "20260924090300"))
    w = world(fn)
    assert w.row("M1")["receipt"] == "ACCEPTED" and w.row("M1")["counted_usd"] == "8.94", w.row("M1")
    unlisted(w, "M1", "UNLISTED_TRAINING_ATTEMPT:" + w.job_id("M1", "20260924090100"))
    code, out = w.run(*admit_args("M2"))                                     # was exit 0 ADMIT, total $54.36
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out


def test_round4_two_attempts_under_one_admission_are_counted_and_now_latch_the_study():
    def fn(w):          # two attempts under ONE admission, both listed: attempt 1 counted at its bound, like S1
        first = training_attempt(w, "M1", "m1_attempt1", "20260924090100", refused=True)
        second = training_attempt(w, "M1", "m1", "20260924090300")
        set_row(w, "M1", second, listed=[first, second])
    w = world(fn)
    row = w.row("M1")
    assert row["receipt"] == "ACCEPTED" and row["counted_usd"] == "10.54", row          # $1.60 + $8.94
    assert "sum over 2 launch attempt(s)" in row["counted_basis"] and "cleanup" not in row, row
    assert set(row["receipt_pins"]) == {"attempt 1", "attempt 2"}, row["receipt_pins"]
    loaded, acct = w.account()
    assert acct["spent"] == Decimal("15.98") and acct["unconfirmed"] == [] and acct["training_started"] == ["M1#2"], acct
    # V2 R1 (Codex Q9): one admission authorizes ONE RunInstances attempt. Round 4 admitted M2 here ($55.96); a second
    # attempt under one admission is now a latched breach. The retry belongs in its own attempt row (test_v2_r1).
    code, out = w.run(*admit_args("M2"))
    assert code == 1 and out["total_usd"] == "55.96", out                   # 15.98 + 11.66 + 28.32
    assert any(r.startswith("LIMIT_BREACH_LATCHED:M1") for r in out["reasons"]), out
    assert "MORE_THAN_ONE_ATTEMPT_UNDER_ONE_ADMISSION" in acct["breaches"]["M1"][0], acct["breaches"]


def test_round4_n6b_an_unlisted_machine_that_ran_is_found():
    def attempt1(w):    # attempt 1 launched a machine; it ran 600 s; its cleanup and identity are unconfirmed
        return training_attempt(w, "M1", "m1_attempt1", "20260924090100", elapsed=600, uncertain=True)

    def named_alone(w):
        attempt1(w)
        set_row(w, "M1", training_attempt(w, "M1", "m1", "20260924090300"))
    w = world(named_alone)
    unlisted(w, "M1", "UNLISTED_TRAINING_ATTEMPT:" + w.job_id("M1", "20260924090100"))
    code, out = w.run(*admit_args("M2"))                                     # was exit 0 ADMIT, $54.36
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out

    def both_listed(w):  # listed honestly: attempt 1 is judged on its own and blocks
        first, second = attempt1(w), training_attempt(w, "M1", "m1", "20260924090300")
        set_row(w, "M1", second, listed=[first, second])
    w = world(both_listed)
    rejected(w, "M1", "attempt 1: CLEANUP_INCOMPLETE_OR_IDENTITY_UNCERTAIN")
    assert "attempt 1 (r/m1_attempt1/result.json)" in w.row("M1")["cleanup"], w.row("M1")
    assert "not listed" not in w.row("M1")["cleanup"], w.row("M1")
    assert w.run(*admit_args("M2"))[0] == 1


def test_round4_n6c_an_unlisted_watched_launch_is_found():
    def fn(folder):
        def inner(w):   # attempt 1 (09:01): the watcher saw it still running; its records moved aside
            watched_attempt(w, "P1b", folder, "2026-09-24T09:01:00Z", "2026-09-24T09:36:00Z", running=True)
            set_row(w, "P1b", watched_attempt(w, "P1b", "p1b", "2026-09-24T09:03:00Z", "2026-09-24T09:38:00Z"))
        return inner
    for folder in ("p1b/attempt1", "p1b_try1"):     # in the job folder, and in a new folder elsewhere
        w = world(fn(folder))
        assert w.row("P1b")["receipt"] == "ACCEPTED", w.row("P1b")
        unlisted(w, "P1b", "UNLISTED_WATCHED_LAUNCH:%s/launch_record.json instance i-p1b-0901" % folder)
        code, out = w.run(*admit_args("P2"))                                 # was exit 0 ADMIT, $55.63
        assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b" in out["reasons"], (folder, out)

    def at_head_only(w):    # attempt 1's records were committed, then deleted from the disk
        for path in ("p1b_gone/launch_record.json", "p1b_gone/watch_record.json"):
            w.git.blobs[("HEAD", "design/" + path)] = enc(w.files.pop(path))
    w = world(lambda w: (fn("p1b_gone")(w), at_head_only(w)))
    unlisted(w, "P1b", "p1b_gone/launch_record.json instance i-p1b-0901 launched 2026-09-24T09:01:00Z (HEAD)")

    def listed(w):          # both listed: attempt 1's own record shows the machine still running, so it blocks
        first = watched_attempt(w, "P1b", "p1b/attempt1", "2026-09-24T09:01:00Z", "2026-09-24T09:36:00Z", running=True)
        second = watched_attempt(w, "P1b", "p1b", "2026-09-24T09:03:00Z", "2026-09-24T09:38:00Z")
        set_row(w, "P1b", second, listed=[first, second])
    w = world(listed)
    rejected(w, "P1b", "attempt 1: NOT_CONFIRMED_TERMINATED")
    assert "attempt 1 (p1b/attempt1/launch_record.json)" in w.row("P1b")["cleanup"], w.row("P1b")


def test_round4_n6d_an_unlisted_later_attempt_is_found():
    def fn(w):          # the row names attempt 1, a proven refusal (09:01); attempt 2 (09:15) ran 20,000 s, identity lost
        training_attempt(w, "M1", "m1_attempt2", "20260924091500", elapsed=20000, uncertain=True)
        set_row(w, "M1", training_attempt(w, "M1", "m1", "20260924090100", refused=True))
    w = world(fn)
    assert w.row("M1")["receipt"] == "ACCEPTED" and w.row("M1")["counted_usd"] == "1.60", w.row("M1")
    unlisted(w, "M1", "UNLISTED_TRAINING_ATTEMPT:" + w.job_id("M1", "20260924091500"))
    code, out = w.run(*admit_args("M2"))                                     # was exit 0 ADMIT, $47.02
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out


def test_round4_attempt_rules():
    clean = lambda w: training_attempt(w, "M1", "m1", "20260924090300")                           # noqa: E731
    refused = lambda w: training_attempt(w, "M1", "m1_attempt1", "20260924090100", refused=True)  # noqa: E731
    # At DONE the row's receipt must be its last listed attempt.
    w = world(lambda w: (lambda a, b: set_row(w, "M1", a, listed=[a, b]))(clean(w), refused(w)))
    rejected(w, "M1", "RECEIPT_NOT_THE_LAST_LISTED_ATTEMPT")
    # Every attempt is bound to this admission: another job's older receipt listed as attempt 1 does not confirm.
    w = world(lambda w: (lambda a, b: set_row(w, "M1", b, listed=[a, b]))(
        training_attempt(w, "M1", "old", "20260917120000"), clean(w)))
    rejected(w, "M1", "attempt 1: LAUNCH_NOT_AFTER_ADMISSION")
    assert "attempt 1 (r/old/result.json)" in w.row("M1")["cleanup"] and "LAUNCHED_BEFORE_ADMISSION" in w.row("M1")["cleanup"]
    # One receipt, one attempt: the same attempt listed twice is a shared identity.
    w = world(lambda w: (lambda a, b: set_row(w, "M1", b, listed=[a, copy.deepcopy(a), b]))(refused(w), clean(w)))
    code, out = w.run(*admit_args("M2"))
    assert code == 1 and any(r.startswith("RECEIPT_SHARED") and "M1#1,M1#2" in r for r in out["reasons"]), out
    # INVALID: every listed attempt counts the larger of the cap and its figures (the refusal too).
    w = world(lambda w: ((lambda a, b: set_row(w, "M1", b, listed=[a, b]))(refused(w), clean(w)), w.invalid("M1")))
    assert w.row("M1")["counted_usd"] == "23.32" and w.account()[1]["unconfirmed"] == [], w.row("M1")
    # RUNNING: the attempt in progress at its full cap, plus every earlier attempt (the proven refusal at its bound).
    w = world(lambda w: (lambda a: set_row(w, "M1", planned_pointer(), listed=[a], status="RUNNING"))(refused(w)))
    assert w.row("M1")["counted_usd"] == "13.26", w.row("M1")                # $11.66 + $1.60
    # Shape: attempts on a PLANNED slot, an empty list or a kind the basis does not allow: exit 2.
    for bad in ([planned_pointer()], [], [planned_watched()]):
        w = world(lambda w: w.by_id("M2").update(attempts=bad) if bad and bad[0]["kind"] == "pointer_finished"
                  else (w.by_id("M1").update(status="RUNNING", attempts=bad), w.admission("M1", SRC_UNCHANGED)))
        code, out = w.run(*admit_args("P1b"))
        assert code == 2 and "attempt" in out["error"], (bad, out)


def test_round4_committed_attempts_only_grow():
    def running(w):
        set_row(w, "M1", planned_pointer(), listed=[training_attempt(w, "M1", "m1_attempt1", "20260924090100",
                                                                     refused=True)], status="RUNNING")
    w = world(running)
    w.commit_snapshot()
    first = copy.deepcopy(w.by_id("M1")["attempts"][0])
    second = training_attempt(w, "M1", "m1", "20260924090300")
    for edit, ok in ((lambda d: d["slots"][5].update(attempts=[first, second]), True),     # appended: allowed
                     (lambda d: d["slots"][5].pop("attempts"), False),                     # removed
                     (lambda d: d["slots"][5].update(attempts=[second, first]), False),    # reordered
                     (lambda d: d["slots"][5]["attempts"][0].update(sha256="0" * 64), False)):   # changed
        w.edit_slots(lambda d: d["slots"][5].update(attempts=[first]))
        w.edit_slots(edit)
        code, out = w.run(*admit_args("P1b"))
        assert (code != 2) if ok else (code == 2 and "HISTORY_VIOLATION: M1 was RUNNING" in out["error"]), out


def test_round4_the_scan_reads_head_the_pins_and_the_working_tree():
    job = None

    def base(w):
        nonlocal job
        set_row(w, "M1", training_attempt(w, "M1", "m1", "20260924090300"))
        job = w.job_id("M1", "20260924090500")
    # Working tree only (a refusal receipt written but never committed): found.
    w = world(base)
    w.git.worktree["r/m1_attempt1/result.json"] = enc(refusal(job, SRC_UNCHANGED, seed=20260917))
    unlisted(w, "M1", "working tree:r/m1_attempt1/result.json")
    # At HEAD only, under the launcher's receipt home (the row's own receipts live elsewhere): found.
    w = world(base)
    w.git.blobs[("HEAD", ss.TRAINING_RECEIPT_HOME + "/receipt_x/provider_0001.json")] = enc(provider(job))
    unlisted(w, "M1", "HEAD:" + ss.TRAINING_RECEIPT_HOME + "/receipt_x/provider_0001.json")
    # Control: M1's seed and source, but prepared a week before this admission (outside the window): not a finding.
    # (A job another slot claims is not a finding either: test_capacity_refusals_never_count_as_started has R1 and M2
    # with one seed and one source inside one window.)
    w = world(lambda w: (base(w), training_attempt(w, "M1", "old", "20260917120000")))
    assert w.account()[1]["unconfirmed"] == [] and w.run(*admit_args("M2"))[0] == 0, w.row("M1")
    # A scan that cannot run fails closed.
    w = world(base)
    w.git.fail_trees.add("HEAD")
    unlisted(w, "M1", "SCAN_FAILED:HEAD")
    assert w.run(*admit_args("M2"))[0] == 1


def test_round4_a_launch_another_slot_claims_is_not_this_slots():
    def watched(w):     # P1b admitted 09:00 (search window to 11:10), DONE; then P2 admitted 09:30 and launched 09:32
        w.done_watched("P1b", "p1b", launched="2026-09-24T09:02:00Z", ended="2026-09-24T09:37:00Z")
        w.done_watched("P2", "p2", machine="c7i.2xlarge", price=0.357, launched="2026-09-24T09:32:00Z",
                       ended="2026-09-24T10:07:00Z", cost=0.22)
        w.by_id("P2")["admission"]["admitted_utc"] = "2026-09-24T09:30:00Z"
    w = world(watched)
    assert [w.row(s)["receipt"] for s in ("P1b", "P2")] == ["ACCEPTED", "ACCEPTED"], (w.row("P1b"), w.row("P2"))
    assert w.account()[1]["unconfirmed"] == [], w.row("P1b")         # P2's launch lies in P1b's window: P2 claims it
    assert w.run(*admit_args("M1"))[0] == 0

    def training(w):    # two slots with one seed and one source (test-only R1 twins M2), windows overlapping
        w.slots.append(training_slot("R1", mandatory=False))
        w.done_training("M2", 10500)
        w.done_training("R1", 10500)
    w = world(training)
    assert w.account()[1]["unconfirmed"] == [], (w.row("M2"), w.row("R1"))


def test_round4_pre_gate_rows_are_checked_for_other_attempts():
    # S1 and S2: every job with their seed and their own source prefix, at any time, must be theirs.
    w = world(lambda w: w.receipts.update({"r/s2_retry/result.json": pointer(
        "cas-meta2-tpntr-20260924040000-22222222-m-20260917", "2" * 40, "i-s2b")}))
    unlisted(w, "S2", "UNLISTED_TRAINING_ATTEMPT:cas-meta2-tpntr-20260924040000-22222222-m-20260917")
    assert w.run(*admit_args("P1b"))[0] == 1
    w = world(lambda w: w.receipts.update({"r/s2_other_seed/result.json": pointer(       # control: another seed
        "cas-meta2-tpntr-20260924040000-22222222-m-20260918", "2" * 40, "i-s2c", seed=20260918)}))
    assert w.account()[1]["unconfirmed"] == [], w.account()[1]["unconfirmed"]
    # P1a: every watched record under its job folder must be P1a's own (by path or instance id).
    w = world(lambda w: w.files.update({"job/attempt0/launch_record.json": dict(
        LAUNCH, instance_id="i-p1a-0", launched_utc="2026-09-24T05:00:00Z")}))
    unlisted(w, "P1a", "UNLISTED_WATCHED_LAUNCH:job/attempt0/launch_record.json instance i-p1a-0")
    w = world(lambda w: w.files.update({"job/copy/launch_record.json": copy.deepcopy(LAUNCH),        # controls: P1a's
                                        "elsewhere/launch_record.json": dict(LAUNCH, instance_id="i-x")}))  # own copy;
    assert w.account()[1]["unconfirmed"] == [], w.account()[1]["unconfirmed"]         # outside its job folder


# ---------------------------------------------- round 4 MINOR N8: full history; --admit only at the fetched remote tip
def git_cmd(cwd, *args):
    done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                           "-c", "init.defaultBranch=main", "-C", str(cwd)] + list(args), capture_output=True)
    assert done.returncode == 0, (args, done.stderr)
    return done.stdout.decode("utf-8").strip()


def test_round4_n8_full_history_sees_a_merged_side_branch():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="ss_git_"))
    atexit.register(shutil.rmtree, str(tmp), True)
    repo = tmp / "repo"
    repo.mkdir()
    git_cmd(repo, "init", "-q")

    def commit(status, message):
        (repo / "slots.json").write_text(json.dumps({"slots": [{"id": "M1", "status": status}]}), encoding="utf-8")
        git_cmd(repo, "add", "slots.json")
        git_cmd(repo, "commit", "-q", "-m", message)
    commit("PLANNED", "planned")
    git_cmd(repo, "checkout", "-q", "-b", "side")
    commit("RUNNING", "admitted")
    commit("DONE", "done")
    git_cmd(repo, "checkout", "-q", "main")
    git_cmd(repo, "merge", "-q", "-s", "ours", "--no-edit", "side")     # keeps main's file: M1 PLANNED again
    plain = git_cmd(repo, "log", "--format=%H", "--", "slots.json").split()
    assert len(plain) == 1, plain                                       # the verifier's probe: the side commits vanish
    history = ss.GitReader(repo).history("slots.json")
    statuses = {json.loads(raw)["slots"][0]["status"] for _c, raw in history}
    assert {"RUNNING", "DONE"} <= statuses, statuses
    try:
        ss.check_history({"slots": [{"id": "M1", "status": "PLANNED"}]}, history)
        raise AssertionError("a merged-away DONE row was not caught")
    except ss.InputError as error:
        assert "HISTORY_VIOLATION: M1 was" in str(error), error


def test_round4_n8_admit_only_at_the_fetched_remote_tip():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="ss_git_"))
    atexit.register(shutil.rmtree, str(tmp), True)
    remote, a, b = tmp / "remote.git", tmp / "a", tmp / "b"
    git_cmd(tmp, "init", "-q", "--bare", str(remote))
    a.mkdir()
    git_cmd(a, "init", "-q")
    (a / "f.txt").write_text("1", encoding="utf-8")
    git_cmd(a, "add", "f.txt")
    git_cmd(a, "commit", "-q", "-m", "one")
    git_cmd(a, "remote", "add", "origin", remote.as_posix())
    git_cmd(a, "push", "-q", "-u", "origin", "main")
    reader = ss.GitReader(a)
    ok, why = reader.at_remote_tip()
    assert ok, why
    (a / "f.txt").write_text("2", encoding="utf-8")                     # a local commit not pushed yet
    git_cmd(a, "commit", "-q", "-am", "two")
    ok, why = reader.at_remote_tip()
    assert not ok and why.startswith("HEAD_IS_NOT_THE_REMOTE_TIP"), why
    git_cmd(a, "push", "-q")
    assert reader.at_remote_tip()[0]
    git_cmd(tmp, "clone", "-q", remote.as_posix(), str(b))               # a second runner pushes a RUNNING row
    (b / "f.txt").write_text("3", encoding="utf-8")
    git_cmd(b, "commit", "-q", "-am", "three")
    git_cmd(b, "push", "-q")
    ok, why = reader.at_remote_tip()
    assert not ok and why.startswith("HEAD_IS_NOT_THE_REMOTE_TIP"), why
    git_cmd(a, "pull", "-q", "--ff-only")
    assert reader.at_remote_tip()[0]
    git_cmd(a, "remote", "set-url", "origin", (tmp / "gone.git").as_posix())   # the fetch fails: refuse
    ok, why = reader.at_remote_tip()
    assert not ok and why.startswith("FETCH_FAILED"), why
    git_cmd(a, "checkout", "-q", "--detach")
    assert reader.at_remote_tip()[1].startswith("DETACHED_HEAD")
    w = world()                                                          # the gate turns it into a refusal
    w.git.remote = (False, "HEAD_IS_NOT_THE_REMOTE_TIP: test")
    code, out = w.run(*admit_args("P1b"))
    assert code == 1 and any(r.startswith("NOT_AT_THE_FETCHED_REMOTE_TIP") for r in out["reasons"]), out
    assert json.loads((w.tmp / "slots.json").read_text(encoding="utf-8"))["slots"][3]["status"] == "PLANNED"


# ------------------------- V2: Codex decisions Q1-Q9 and R3-F, static review findings 1-2 (c3a128ee); one test per rule
def test_v2_r1_one_admission_one_attempt_a_retry_needs_its_own_row_and_admission():
    # A second attempt under one admission is a latched breach (Codex Q9 + static review finding 1).
    def two_under_one(w):
        first = training_attempt(w, "M1", "m1_attempt1", "20260924090100", refused=True)
        second = training_attempt(w, "M1", "m1", "20260924090300")
        set_row(w, "M1", second, listed=[first, second])
    code, out = world(two_under_one).run(*admit_args("M2"))
    assert code == 1 and any(r.startswith("LIMIT_BREACH_LATCHED:M1") for r in out["reasons"]), out

    # Attempt 1 of M1 was an AWS capacity refusal. The retry is attempt row M1.2: its own cap is reserved while it is
    # PLANNED, and its own fresh --admit covers prior spend, the replacement cap, the owner stop and every reserve.
    def refused_then_row(w):
        w.refused_training("M1")
        w.attempt_row("M1", 2)
    w = world(refused_then_row)
    loaded, acct = w.account()
    assert "M1.2" in acct["planned_mandatory"] and acct["reserve"] == Decimal("51.64"), acct["planned_mandatory"]
    code, out = w.run(*admit_args("M1.2"))
    assert code == 0 and out["total_usd"] == "58.68", out                  # 7.04 + 11.66 + 39.98
    assert "the replacement cap of attempt 2 of M1" in out["admission_arithmetic"], out
    a = out["admission_record"]
    assert (a["slot"], a["attempt"], a["model_seed"], a["arm"]) == ("M1.2", 2, 20260917, "UNCHANGED"), a
    doc = json.loads((w.tmp / "slots.json").read_text(encoding="utf-8"))
    assert doc["attempt_rows"][0]["status"] == "RUNNING" and doc["slots"][5]["status"] == "DONE", doc["attempt_rows"]
    # Attempt rows are append-only.
    w = world(refused_then_row)
    w.commit_snapshot()
    w.edit_slots(lambda d: d.update(attempt_rows=[]))
    code, out = w.run(*admit_args("M2"))
    assert code == 2 and "append-only" in out["error"], out
    # A retry row needs the previous attempt settled, and the next number.
    def too_early(w):
        w.by_id("M1")["status"] = "RUNNING"
        w.admission("M1", SRC_UNCHANGED)
        w.attempt_row("M1", 2)
    code, out = world(too_early).run(*admit_args("P1b"))
    assert code == 2 and "needs it settled" in out["error"], out
    code, out = world(lambda w: (w.refused_training("M1"), w.attempt_row("M1", 3))).run(*admit_args("P1b"))
    assert code == 2 and "number 2" in out["error"], out
    # The fresh admission needs confirmed cleanup of every earlier attempt.
    code, out = world(lambda w: (m1_uncertain(w, "i-M1"), w.attempt_row("M1", 2))).run(*admit_args("M1.2"))
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out

    # An expired, unused admission is closed with proof of no launch and reissued through the next attempt row.
    def closed_unused(w):
        m1 = w.by_id("M1")
        m1["status"] = "CLOSED_NO_LAUNCH"
        w.admission("M1", SRC_UNCHANGED)
        m1["closure"] = {"reason": "the admission expired before any launch",
                         "evidence": "no launch record, receipt or provider call exists for its window"}
        w.attempt_row("M1", 2)
    w = world(closed_unused)
    row = w.row("M1")
    assert row["receipt"] == "CLOSED_NO_LAUNCH" and row["counted_usd"] == "0.00" and "cleanup" not in row, row
    assert w.run(*admit_args("M1.2"))[0] == 0

    def closed_but_launched(w):     # the search of its window finds a launch: not proven, counted, blocks
        closed_unused(w)
        job = w.job_id("M1", "20260924090200")
        w.git.blobs[("HEAD", ss.TRAINING_RECEIPT_HOME + "/receipt_y/result.json")] = enc(pointer(job, SRC_UNCHANGED, "i-y"))
    w = world(closed_but_launched)
    assert w.row("M1")["counted_usd"] == "11.66" and w.account()[1]["unconfirmed"] == ["M1"], w.row("M1")
    # ... and never rewritten as PLANNED.
    def running(w):
        w.by_id("M1")["status"] = "RUNNING"
        w.admission("M1", SRC_UNCHANGED)
    w = world(running)
    w.commit_snapshot()
    w.edit_slots(lambda d: (d["slots"][5].update(status="PLANNED"), d["slots"][5].pop("admission")))
    code, out = w.run(*admit_args("M1"))
    assert code == 2 and "HISTORY_VIOLATION: M1 was RUNNING" in out["error"] and "never rewritten as PLANNED" in out["error"]


def test_v2_r2_an_admission_is_recomputed_under_a_lock_valid_300_s_and_single_use():
    def admitted_world():
        w = world()
        w.commit_snapshot()
        code, out = w.run(*admit_args("P1b"))
        assert code == 0, out
        w.commit_snapshot()                                       # the RUNNING row is committed (and pushed)
        return w, out["admission_record"]
    w, a = admitted_world()
    # The record binds the inventory hash, gate version, cap, remaining reserve, cumulative bound, main starts and the
    # launch identity (Codex R3-F).
    assert a["valid_until_utc"] == "2026-09-24T12:05:00Z" and a["gate_version"] == ss.GATE_VERSION, a
    assert ss.SHA.match(a["inventory_sha256"]) and a["lock_nonce"] == w.lock()["nonce"], (a, w.lock())
    assert w.lock()["state"] == "ADMITTED", w.lock()
    assert (a["cap_usd"], a["remaining_mandatory_reserve_usd"], a["cumulative_upper_bound_usd"], a["main_starts"]) == (
        "2.00", "49.64", "5.44", 0), a
    assert (a["source_sha"], a["bundle_sha256"], a["worker_sha256"], a["checker_sha256"]) == (
        SRC_WATCHED, BUNDLE, WORKER, CHECKER), a
    # A second writer is refused while the lock is held, and does not release it.
    code, out = w.run(*admit_args("P2"))
    assert code == 1 and any(r.startswith("LOCK_HELD:P1b") for r in out["reasons"]), out
    assert w.lock()["state"] == "ADMITTED"
    # Immediately before RunInstances: once, inside the 300 s.
    code, out = w.run("--launch-check", "P1b", now="2026-09-24T12:04:59Z")
    assert code == 0 and out["decision"] == "LAUNCH_ONCE", out
    assert w.lock()["state"] == "LAUNCH_CHECKED"
    code, out = w.run("--launch-check", "P1b", now="2026-09-24T12:04:59Z")
    assert code == 1 and any(r.startswith("ADMISSION_ALREADY_USED") for r in out["reasons"]), out
    # Expiry, a lost lock and a changed input each need a fresh check.
    w, _a = admitted_world()
    code, out = w.run("--launch-check", "P1b", now="2026-09-24T12:05:00Z")
    assert code == 1 and any(r.startswith("ADMISSION_EXPIRED") for r in out["reasons"]), out
    w, _a = admitted_world()
    (w.tmp / ss.LOCK_NAME).unlink()
    code, out = w.run("--launch-check", "P1b", now="2026-09-24T12:01:00Z")
    assert code == 1 and any(r.startswith("LOCK_LOST") for r in out["reasons"]), out
    w, _a = admitted_world()
    (w.tmp / "job" / "watch_record.json").write_bytes(enc(dict(WATCH, note="changed after the admission")))
    code, out = w.run("--launch-check", "P1b", now="2026-09-24T12:01:00Z")
    assert code == 1 and any(r.startswith("INPUT_CHANGED") for r in out["reasons"]), out
    # The receipt's own launch time must lie inside the 300-s validity.
    w = world(lambda w: (w.done_watched("P1b", "p1b", launched="2026-09-24T09:05:00Z", ended="2026-09-24T09:40:00Z"),
                         w.invalid("P1b", "late")))
    unconfirmed_not_this_launch(w, "P1b", "LAUNCHED_AFTER_THE_ADMISSION_VALIDITY")
    # A record without the V2 binding fields is refused.
    rejected(world(lambda w: (w.done_training("M1", 10500), w.bare_admission.add("M1"))), "M1",
             "ADMISSION_RECORD_MISSING_BINDING")


def test_v2_r3_x1_a_reused_watched_folder_is_found():
    # The verifier's X1: P1b attempt 1 (09:01, still running) was committed in p1b/, then deleted from the disk;
    # attempt 2 (09:03, clean) was launched into the same p1b/ and is named. Round 4 skipped the HEAD copy by its path.
    def fn(w):
        watched_attempt(w, "P1b", "p1b", "2026-09-24T09:01:00Z", "2026-09-24T09:36:00Z", running=True)
        for name in ("launch_record.json", "watch_record.json"):
            w.git.blobs[("HEAD", "design/p1b/" + name)] = enc(w.files["p1b/" + name])
        set_row(w, "P1b", watched_attempt(w, "P1b", "p1b", "2026-09-24T09:03:00Z", "2026-09-24T09:38:00Z"))
    w = world(fn)
    assert w.row("P1b")["receipt"] == "ACCEPTED", w.row("P1b")
    unlisted(w, "P1b", "UNLISTED_WATCHED_LAUNCH:p1b/launch_record.json instance i-p1b-0901 launched "
                       "2026-09-24T09:01:00Z (HEAD)")
    code, out = w.run(*admit_args("P2"))                                     # the verifier saw exit 0, $55.63
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:P1b" in out["reasons"], out


def test_v2_r3_x2_a_retry_prepared_from_a_new_source_is_found():
    # The verifier's X2: M1 admitted 09:00 with 4444...; attempt 1 (09:01) a capacity refusal, named; attempt 2 (09:15)
    # prepared from 5555..., ran 20,000 s, identity lost, not listed. Round 4 matched the admitted source prefix only.
    def fn(w):
        job = w.job_id("M1", "20260924091500", source="5" * 40)
        r = pointer(job, "5" * 40, "UNKNOWN", 20000)
        r["cleanup"].update(complete=False, compute_identity_uncertain=True, instance_ids=[], instances={},
                            failures=["INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT"])
        w.receipts["r/m1_attempt2/result.json"] = r
        set_row(w, "M1", training_attempt(w, "M1", "m1", "20260924090100", refused=True))
    w = world(fn)
    assert w.row("M1")["receipt"] == "ACCEPTED" and w.row("M1")["counted_usd"] == "1.60", w.row("M1")
    unlisted(w, "M1", "UNLISTED_TRAINING_ATTEMPT:cas-meta2-tpntr-20260924091500-55555555-m-20260917")
    code, out = w.run(*admit_args("M2"))                                     # the verifier saw exit 0, $47.02
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out


def test_v2_r3_x3_the_same_job_launched_twice_is_found():
    # The verifier's X3: attempt 1 (job J, 09:01) ran and lost its identity; attempt 2 (the same job J) finished clean
    # and is named. Round 4 skipped J everywhere because the row lists J; now a file counts as listed only by the listed
    # receipt's own path AND sha256 (or as a sibling record of it at the listed commit).
    def fn(w):
        first = training_attempt(w, "M1", "m1_attempt1", "20260924090100", elapsed=600, uncertain=True)
        job = first["expected"]["job"]
        w.receipts["r/m1/result.json"] = pointer(job, SRC_UNCHANGED, "i-M1-again", 10500)
        set_row(w, "M1", w.pointer_spec("r/m1/result.json", job, SRC_UNCHANGED, "i-M1-again"))
    w = world(fn)
    assert w.row("M1")["receipt"] == "ACCEPTED", w.row("M1")
    unlisted(w, "M1", "r/m1_attempt1/result.json")
    code, out = w.run(*admit_args("M2"))                                     # the verifier saw exit 0, $54.36
    assert code == 1 and "CLEANUP_UNCONFIRMED_STOP_AND_REPORT:M1" in out["reasons"], out


def test_v2_r4_source_bundle_worker_checker_are_bound_and_a_mismatch_blocks_but_cleanup_is_inspected():
    def other_worker(w, invalid=False):
        w.done_training("M1", 10500)
        w.receipts["r/m1/result.json"]["authority"]["worker_sha256"] = "7" * 64
        if invalid:
            w.invalid("M1", "wrong worker")
    w = world(other_worker)
    rejected(w, "M1", "IDENTITY_NOT_THE_ADMITTED:worker_sha256")            # the scientific result is not accepted
    code, out = w.run(*admit_args("M2"))
    assert code == 1 and any(r.startswith("WRONG_IDENTITY_BLOCKS_THE_STUDY:M1") for r in out["reasons"]), out
    w = world(lambda w: other_worker(w, invalid=True))
    row, acct = w.row("M1"), w.account()[1]
    assert "cleanup" not in row and acct["unconfirmed"] == [] and row["counted_usd"] == "11.66", row   # inspected, counted
    assert "M1" in acct["wrong_identity"] and "M1" in acct["training_started"], acct                  # and it started
    code, out = w.run(*admit_args("M2"))
    assert code == 1 and any(r.startswith("WRONG_IDENTITY_BLOCKS_THE_STUDY:M1") for r in out["reasons"]), out

    def no_checker(w):          # a receipt that does not show a bound hash at all is refused too
        w.done_training("M1", 10500)
        del w.receipts["r/m1/result.json"]["authority"]["checker_sha256"]
    rejected(world(no_checker), "M1", "IDENTITY_NOT_THE_ADMITTED:checker_sha256")

    def watched_other_source(w):    # watched slots now bind source and bundle too (NOTE K), not only the launch time
        w.done_watched("P1b", "p1b")
        w.files["p1b/launch_record.json"]["identity"]["source_commit"] = "f" * 40
        w.invalid("P1b", "wrong source")
    w = world(watched_other_source)
    acct = w.account()[1]
    assert acct["unconfirmed"] == [] and "IDENTITY_NOT_THE_ADMITTED:source_sha" in acct["wrong_identity"]["P1b"][0], acct
    assert w.run(*admit_args("P2"))[0] == 1


def test_v2_r5_a_limit_breach_latches_the_study_but_a_prelaunch_failure_with_no_instance_does_not():
    w = world(p1b_breach)       # 240 min on a 130-min basis; the watcher saw it terminated; INVALID
    acct = w.account()[1]
    assert acct["unconfirmed"] == [] and "P1b" in acct["breaches"], acct["breaches"]
    for sid in ("P2", "M1", "E1"):
        code, out = w.run(*admit_args(sid))
        assert code == 1 and any(r.startswith("LIMIT_BREACH_LATCHED:P1b") for r in out["reasons"]), (sid, out)
    w = world(lambda w: (w.done_training("M1", 20000), w.invalid("M1", "ran long")))   # past 14,400 s, cleanup confirmed
    acct = w.account()[1]
    assert acct["unconfirmed"] == [] and any("ELAPSED_OVER_BASIS" in b for b in acct["breaches"]["M1"]), acct["breaches"]

    def prelaunch(run_instances):
        def fn(w):
            m1 = w.by_id("M1")
            m1["status"] = "CLOSED_NO_LAUNCH"
            w.admission("M1", SRC_UNCHANGED)
            job = w.job_id("M1", "20260924090100")
            m1["closure"] = {"reason": "the launcher's preflight refused before RunInstances",
                             "evidence": "its receipt shows no launch and no instance; its folder holds no RunInstances call",
                             "receipt": w.prelaunch_failure_receipt("r/m1_preflight", job, SRC_UNCHANGED, 20260917,
                                                                    run_instances)}
        return fn
    w = world(prelaunch(False))
    acct = w.account()[1]
    assert w.row("M1")["counted_usd"] == "0.00" and acct["unconfirmed"] == [] and acct["breaches"] == {}, w.row("M1")
    assert acct["training_started"] == [] and acct["uncertain"] == [], acct
    assert w.run(*admit_args("M2"))[0] == 0
    w = world(prelaunch(True))                        # its folder shows a RunInstances call: not proven, blocks
    assert w.account()[1]["unconfirmed"] == ["M1"] and w.row("M1")["counted_usd"] == "11.66", w.row("M1")
    assert "CLOSURE_FOLDER_SHOWS_A_RUNINSTANCES_CALL" in w.row("M1")["cleanup"], w.row("M1")


def test_v2_r6_every_started_main_attempt_counts_and_the_stop_stays_latched():
    def started(w):             # accepted or not, failed or not: a machine ran for M1 and for M2
        w.done_training("M1", 10500)
        w.receipts["r/m1/result.json"]["schema"] = "someone-else/1"
        w.done_training("M2", 10500)
        w.receipts["r/m2/result.json"].update(status="AWS_CANDIDATE_FAILED")
        w.invalid("M2", "the job failed after its launch")
    loaded, acct = world(started).account()
    assert acct["rejected"] == ["M1"] and acct["training_started"] == ["M1", "M2"], acct   # round 4 counted neither

    def unproven(w):            # neither a proven refusal nor a proven launch: an uncertain start blocks
        w.refused_training("M3")
        w.trees["r/m3"] = w.trees["r/m3"] + ["provider_0004.json"]
        w.invalid("M3", "unclear")
    code, out = world(unproven).run(*admit_args("P1b"))
    assert code == 1 and any(r.startswith("MAIN_START_UNCERTAIN:M3") for r in out["reasons"]), out

    def over_30(w):             # 2 main starts ($23.32) + S1, S2, P1a ($5.44) + a prior $2.00 = $30.76
        w.done_training("M1", 14400)
        w.done_training("M2", 14400)
        w.slots.append(slot("PRIOR", "DONE", "2.00", {"kind": "prior_spend", "items": [
            {"job": "prep_job", "attempt": 1, "usd": "2.00"}]}, {"kind": "prior_spend_declared"}))
    w = world(over_30)
    loaded, acct = w.account()
    assert acct["spent"] == Decimal("30.76") and acct["training_started"] == ["M1", "M2"], acct
    for sid in ("M3", "P1b", "E1"):
        code, out = w.run(*admit_args(sid))
        assert code == 1 and any(r.startswith("OWNER_STOP_TRIGGERED") for r in out["reasons"]), (sid, out)
    w = world(lambda w: (over_30(w), w.invalid("M2", "re-marked"), w.attempt_row("M2", 2)))  # no reset by moving on
    for sid in ("M2.2", "M3"):
        code, out = w.run(*admit_args(sid))
        assert code == 1 and any(r.startswith("OWNER_STOP_TRIGGERED") for r in out["reasons"]), (sid, out)


def test_v2_r7_cancelled_not_launched():
    note = {"reason": "not needed", "evidence": "never admitted; no attempt, receipt or resource exists"}
    w = world(lambda w: w.by_id("M5").update(status="CANCELLED_NOT_LAUNCHED", cancellation=dict(note)))
    loaded, acct = w.account()                   # optional: $0.00 and its cap leaves fallback B
    assert w.row("M5")["counted_usd"] == "0.00" and acct["optional"] == [] and acct["comparison_incomplete"] == [], acct
    assert w.run(*admit_args("M1"))[0] == 0
    w = world(lambda w: w.by_id("M4").update(status="CANCELLED_NOT_LAUNCHED", cancellation=dict(note)))
    loaded, acct = w.account()                   # mandatory: its cap stays reserved; the comparison is incomplete
    assert acct["comparison_incomplete"] == ["M4"] and acct["reserve"] == Decimal("51.64"), acct
    code, out = w.run(*admit_args("M1"))
    assert code == 1 and any(r.startswith("COMPARISON_INCOMPLETE:M4") for r in out["reasons"]), out
    code, out = w.run(*admit_args("E1"))         # the partial-study readout is not a main admission
    assert code == 0 and "M4" in out["admission_arithmetic"], out

    def admitted(w):                             # only a never-admitted row may be cancelled
        w.by_id("M4").update(status="CANCELLED_NOT_LAUNCHED", cancellation=dict(note))
        w.admission("M4", SRC_REPAIRED)
    assert world(admitted).run(*admit_args("E1"))[0] == 2

    def running(w):
        w.by_id("M4")["status"] = "RUNNING"
        w.admission("M4", SRC_REPAIRED)
    w = world(running)
    w.commit_snapshot()
    w.edit_slots(lambda d: (d["slots"][8].update(status="CANCELLED_NOT_LAUNCHED", cancellation=dict(note)),
                            d["slots"][8].pop("admission")))
    code, out = w.run(*admit_args("E1"))
    assert code == 2 and "HISTORY_VIOLATION: M4 was RUNNING" in out["error"], out
    no_evidence = world(lambda w: w.by_id("M5").update(status="CANCELLED_NOT_LAUNCHED", cancellation={"reason": "x"}))
    assert no_evidence.run(*admit_args("M1"))[0] == 2


def test_v2_r8_the_s1_rule_is_accepted_and_names_its_provider_evidence():
    w = world()
    pins = w.row("S1")["receipt_pins"]
    assert "ACCEPTED" in pins["override"] and ss.Q1_ACCEPTANCE in pins["override"], pins
    resolved, last = pins["override_resolved_by"], w.by_id("S1")["receipt"]["last_provider_record"]
    assert resolved["last_provider_record"]["path"] == LAST and resolved["last_provider_record"]["sha256"] == last["sha256"]
    assert "max retries: 0" in resolved["receipt_outcome"] and w.row("S1")["counted_usd"] == "1.60", resolved
    # Conditional on that evidence: a changed provider record voids the rule, and S1's cleanup is unconfirmed.
    w = world(after_pin=lambda w: w.git.blobs.update({(C1, LAST): enc(dict(provider(S1_JOB), note="edited"))}))
    assert "override_resolved_by" not in (w.row("S1").get("receipt_pins") or {})
    assert w.account()[1]["unconfirmed"] == ["S1"]


PRIOR_ITEMS = [{"job": "analogy_repair_t4_job", "attempt": 1, "usd": "0.5596"},
               {"job": "analogy_repair_t4_job", "attempt": 2, "usd": "0.67"},
               {"job": "aws_probe_job", "attempt": 1, "usd": "0.4834"},
               {"job": "hset1a_aws_job", "attempt": 1, "usd": "0.0223"},
               {"job": "hset1a_aws_job", "attempt": 2, "usd": "0.1827"}]


def test_v2_r9_the_prior_spend_row_and_plan_c_bound():
    def fn(w):
        w.slots.append(slot("PRIOR", "DONE", "1.92", {"kind": "prior_spend", "items": copy.deepcopy(PRIOR_ITEMS)},
                            {"kind": "prior_spend_declared"}))
    w = world(fn)
    row, (loaded, acct) = w.row("PRIOR"), w.account()
    assert row["receipt"] == "DECLARED_PRIOR_SPEND" and row["counted_usd"] == "1.92" and "cleanup" not in row, row
    state = ss.state_document(loaded, acct)
    assert (state["spent_upper_bound_usd"], state["plan_C_worst_case_total_usd"], state["headroom_usd"]) == (
        "7.36", "59.00", "1.00"), state
    assert state["plan_C_is_final"] is False and state["plan_C_if_each_prior_job_also_got_the_0.10_allowance_usd"] == "59.50"
    code, out = w.run(*admit_args("P1b"))
    assert code == 0 and out["total_usd"] == "59.00", out
    assert world(lambda w: (fn(w), w.by_id("PRIOR").update(cap_usd="1.91"))).run(*admit_args("P1b"))[0] == 2


Q5_COMMON = ("P2's actual custodian feasibility / exposure receipt", "corrected mechanism validation",
             "all eighteen checkpoint checks enumerated", "both-arm route acceptance",
             "the frozen source, data, starting values, worker, checker and environment", "reader AWS acceptance",
             "complete all-services reserves",
             "the current single-use technical admission and the current single-use spending admission")


def test_v2_q5_main_preconditions_are_the_codex_list_printed_and_not_checked_by_the_money_gate():
    real = pathlib.Path(__file__).resolve().parent / "STUDY_SLOTS.json"         # read only: no admission, no write
    rows = {s["id"]: s for s in json.loads(real.read_text(encoding="utf-8"))["slots"]}
    for sid in ("M1", "M2", "M3", "M4", "M5", "M6"):
        listed = rows[sid]["preconditions_outside_money_gate"]
        for item in Q5_COMMON:
            assert any(p.startswith(item) for p in listed), (sid, item)
        assert "Codex Q5" in rows[sid]["preconditions_note"] and "NOT by this money gate" in rows[sid]["preconditions_note"]
    for sid in ("M2", "M3", "M4"):
        listed = rows[sid]["preconditions_outside_money_gate"]
        assert any("completed VALID reproduction verdict" in p for p in listed) and "M1 was admitted first" not in listed
    for sid in ("M5", "M6"):
        listed = rows[sid]["preconditions_outside_money_gate"]
        assert any("valid-mismatch predicate" in p and "not a new owner approval token" in p for p in listed), listed
        assert "fallback B was chosen by the owner" not in listed
    assert ss.load_slots(real)["digest"] == ss.FROZEN_DEFINITIONS_SHA256          # the re-frozen digest holds
    w = world(lambda w: w.by_id("M1").update(preconditions_outside_money_gate=rows["M1"]["preconditions_outside_money_gate"]))
    code, out = w.run(*admit_args("M1"))          # printed with the decision; the money gate admits on money alone
    assert code == 0 and out["preconditions_outside_money_gate"] == rows["M1"]["preconditions_outside_money_gate"], out


def run_all():
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_") and callable(fn)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS", name)
        except Exception as error:   # report every test, then fail the run
            failed += 1
            print("FAIL", name, type(error).__name__, str(error)[:900])
    print("%d passed, %d failed" % (len(tests) - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run_all())
