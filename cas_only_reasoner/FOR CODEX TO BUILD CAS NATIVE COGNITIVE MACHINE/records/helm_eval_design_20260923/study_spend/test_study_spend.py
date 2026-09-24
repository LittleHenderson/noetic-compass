"""Small pure-Python tests for study_spend.py. Label CLAUDE_BUILT_CLAUDE_CHECKED.

Covers Codex review codex-0007 (defects 1-4) and the builder review of bb942461 (MAJOR 1-4, MINOR 1-4): every
wrongful ADMIT the reviewer found has a negative test here. Synthetic receipts only; a fake git reader; temporary
folders. No AWS, no torch; the real slots file and receipts are never read or changed.
Run: python -B test_study_spend.py   (also collectable by pytest)
"""
import atexit
import copy
import hashlib
import io
import json
import pathlib
import shutil
import sys
import tempfile
from contextlib import redirect_stdout
from decimal import Decimal

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import study_spend as ss  # noqa: E402

C1 = "a" * 40
SRC_UNCHANGED, SRC_REPAIRED, SRC_WATCHED = "4" * 40, "3" * 40, "e" * 40
ADMITTED, NOW = "2026-09-24T09:00:00Z", "2026-09-24T12:00:00Z"
S1_PATH, S2_PATH, LAST = "r/s1/result.json", "r/s2/result.json", "r/s1/provider_0025.json"
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

    def read(self, commit, path):
        if (commit, path) not in self.blobs:
            raise FileNotFoundError(path)
        return self.blobs[(commit, path)]

    def names(self, commit, directory):
        if (commit, directory) not in self.trees:
            raise FileNotFoundError(directory)
        return list(self.trees[(commit, directory)])

    def history(self, name):
        return list(self.versions)

    def uncommitted(self, names):
        return [n for n in names if n in self.dirty]


def pointer(job, source, iid, elapsed=2431.2951856, seed=20260917):
    return {"schema": ss.POINTER_SCHEMA, "job": job, "request": {"job": job},
            "authority": {"job": job, "source_sha": source, "instance_type": "g7.2xlarge", "instance_seconds_max": 14400,
                          "worker_config": {"design": {"model_seed": seed}}},
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
          "identity": {"source_commit": SRC_WATCHED}, "bundle": {"sha256": "b" * 64}}
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
        self.receipts = {S1_PATH: refusal("job-s1", "1" * 40), S2_PATH: pointer("job-s2", "2" * 40, "i-s2")}
        self.providers = {LAST: provider("job-s1")}
        self.trees = {"r/s1": ["provider_0024.json", "provider_0025.json", "result.json"]}
        self.files = {"job/launch_record.json": copy.deepcopy(LAUNCH), "job/watch_record.json": copy.deepcopy(WATCH)}
        self.launch, self.watch = self.files["job/launch_record.json"], self.files["job/watch_record.json"]
        e1 = dict(BASIS_W, evidence_collection_allowance_usd="0.10")
        p2 = dict(BASIS_W, machines={"c7i.2xlarge": "0.357"})
        p1a = dict(BASIS_W, machines={"g4dn.2xlarge": "0.752"})
        self.slots = [
            slot("S1", "DONE", "11.66", BASIS_T, {"kind": "pointer_capacity_refusal", "git_commit": C1, "path": S1_PATH,
                                                  "sha256": None, "last_provider_record": {"path": LAST, "sha256": None},
                                                  "expected": {"job": "job-s1", "source_sha": "1" * 40,
                                                               "instance_type": "g7.2xlarge"}}),
            slot("S2", "DONE", "11.66", BASIS_T, self.pointer_spec(S2_PATH, "job-s2", "2" * 40, "i-s2")),
            slot("P1a", "DONE", "3.00", p1a, self.watched_spec("job", "i-p1a", "2026-09-24T05:53:38Z", "b" * 64)),
            slot("P1b", "PLANNED", "2.00", BASIS_W, planned_watched()),
            slot("P2", "PLANNED", "1.00", p2, planned_watched()),
            training_slot("M1"), training_slot("M2"), training_slot("M3"), training_slot("M4"),
            slot("E1", "PLANNED", "2.00", e1, planned_watched()),
            training_slot("M5", mandatory=False)]
        self.program = self.tmp / "study_spend.py"
        self.program.write_bytes(b"# program under test\n")

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
        return next(s for s in self.slots if s["id"] == sid)

    def admission(self, sid, source, bundle=None, when=ADMITTED):
        s = self.by_id(sid)
        a = {"slot": sid, "admitted_utc": when, "source_sha": source}
        if "training" in s:
            a.update(model_seed=s["training"]["model_seed"], arm=s["training"]["arm"])
        else:
            a["bundle_sha256"] = bundle
        s["admission"] = a

    def source_of(self, sid):
        return SRC_REPAIRED if self.by_id(sid)["training"]["arm"] == "REPAIRED" else SRC_UNCHANGED

    def job_id(self, sid, job_ts=None, seed=None):
        """The launcher's job id format; each slot launches at its own hour after ADMITTED unless job_ts is given."""
        job_ts = job_ts or "20260924%02d0000" % (10 + [s["id"] for s in self.slots].index(sid))
        return "cas-meta2-tpntr-%s-%s-m-%d" % (job_ts, self.source_of(sid)[:8], seed or self.by_id(sid)["training"]["model_seed"])

    def done_training(self, sid, elapsed, job_ts=None, seed=None):
        s, src = self.by_id(sid), self.source_of(sid)
        job, path = self.job_id(sid, job_ts, seed), "r/%s/result.json" % sid.lower()
        self.receipts[path] = pointer(job, src, "i-" + sid, elapsed, seed=seed or s["training"]["model_seed"])
        s["status"], s["receipt"] = "DONE", self.pointer_spec(path, job, src, "i-" + sid)
        self.admission(sid, src)

    def refused_training(self, sid):
        s, src, job = self.by_id(sid), self.source_of(sid), self.job_id(sid)
        folder = "r/%s" % sid.lower()
        self.receipts[folder + "/result.json"] = refusal(job, src, seed=s["training"]["model_seed"])
        self.providers[folder + "/provider_0003.json"] = provider(job)
        self.trees[folder] = ["provider_0003.json", "result.json"]
        s["status"] = "DONE"
        s["receipt"] = {"kind": "pointer_capacity_refusal", "git_commit": C1, "path": folder + "/result.json",
                        "sha256": None, "last_provider_record": {"path": folder + "/provider_0003.json", "sha256": None},
                        "expected": {"job": job, "source_sha": src, "instance_type": "g7.2xlarge"}}
        self.admission(sid, src)

    def done_watched(self, sid, folder, machine="g4dn.2xlarge", price=0.752, launched="2026-09-24T10:00:00Z",
                     ended="2026-09-24T10:35:00Z", minutes=35.0, cost=0.4489, deadline=130, bundle="c" * 64,
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
        for s in self.slots:
            r = s["receipt"]
            if s["status"] not in ("DONE", "INVALID"):
                continue
            if r["kind"] in ("pointer_finished", "pointer_capacity_refusal") and r.get("path") and r.get("sha256") is None:
                r["sha256"] = sha(self.git.blobs[(C1, r["path"])])
            if r["kind"] == "pointer_capacity_refusal" and r["last_provider_record"]["sha256"] is None:
                r["last_provider_record"]["sha256"] = sha(self.git.blobs[(C1, r["last_provider_record"]["path"])])
            if r["kind"] == "watched_machine":
                for key in ("launch_record", "watch_record"):
                    if r[key] and r[key]["sha256"] is None:
                        r[key]["sha256"] = sha((self.tmp / r[key]["path"]).read_bytes())
        if after_pin:
            after_pin(self)
        doc = {"schema": ss.SCHEMA, "ceiling_usd": "60.00",
               "owner_stop": {"usd": "30.00", "before_training_job_number": 3, "rule": "stop"},
               "allowances": {"s3_transfer_per_job_usd": "0.10"}, "open_questions_for_owner_or_codex": ["q"],
               "slots": self.slots}
        (self.tmp / "slots.json").write_text(json.dumps(doc), encoding="utf-8")
        self.frozen = ss.definitions_digest(doc)
        return self

    def edit_slots(self, fn):
        doc = json.loads((self.tmp / "slots.json").read_text(encoding="utf-8"))
        fn(doc)
        (self.tmp / "slots.json").write_text(json.dumps(doc), encoding="utf-8")

    def commit_snapshot(self):
        """Pretend the slots file as it is now was committed."""
        self.git.versions.append(("%040d" % len(self.git.versions), (self.tmp / "slots.json").read_bytes()))

    def run(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = ss.main(list(argv) + ["--no-write"], git=self.git, root=self.tmp, slots_file=self.tmp / "slots.json",
                           state_file=self.tmp / "state.json", frozen=self.frozen, program_file=self.program, now=NOW)
        text = out.getvalue()
        return code, (json.loads(text) if argv and argv[0] == "--admit" else text)

    def account(self):
        loaded = ss.load_slots(self.tmp / "slots.json", self.frozen)
        return loaded, ss.account(loaded, self.tmp, self.git)

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


def admit_args(sid):
    if sid in ("P1b", "P2", "E1"):
        return ("--admit", sid, "--source", SRC_WATCHED, "--bundle", "c" * 64)
    return ("--admit", sid, "--source", SRC_REPAIRED if TRAINING.get(sid, (0, "REPAIRED"))[1] == "REPAIRED" else SRC_UNCHANGED)


# ---------------------------------------------------------------------------------------------------- baseline
def test_baseline_accepts_all_three_receipts_with_exact_bounds():
    w = world()
    assert w.row("S1")["counted_usd"] == "1.60"   # 25.666 s x 2.52/3600 + 1.48 + 0.10 = 1.597966 -> 1.60
    assert w.row("S2")["counted_usd"] == "3.29"   # 2431.295 s -> 3.281907 -> 3.29
    assert w.row("P1a")["counted_usd"] == "0.55"  # max(0.4489, 0.448829) + 0.10 -> 0.55
    assert "CLAUDE_PROPOSED" in w.row("S1")["receipt_pins"]["override"]
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
        w.git.blobs[(C1, S2_PATH)] = enc(pointer("job-s2", "2" * 40, "i-s2", elapsed=10.0))
    rejected(world(after_pin=stale), "S2", "RECEIPT_HASH_MISMATCH")

    def unrelated(w):   # a real receipt of ANOTHER job, pinned by hash: identity still refuses it
        w.receipts[S2_PATH] = pointer("job-s1", "1" * 40, "i-s2")
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
        w.providers[LAST] = dict(provider("job-s1"), operation="describe_instances")
    rejected(world(network), "S1", "NOT_AN_AWS_CAPACITY_REFUSAL")
    rejected(world(launched), "S1", "LAUNCH_RECORD_PRESENT")
    rejected(world(later_call), "S1", "A_PROVIDER_CALL_FOLLOWS")
    rejected(world(other_failure), "S1", "CLEANUP_FAILURES_NOT_ONLY")
    rejected(world(wrong_last), "S1", "LAST_PROVIDER_NOT_THE_CAPACITY_REFUSAL")
    assert world(network).account()[1]["unconfirmed"] == ["S1"]      # the override failed: a machine may exist

    def stale_last(w):
        w.git.blobs[(C1, LAST)] = enc(dict(provider("job-s1"), note="edited"))
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
    assert w.run("--admit", "M1", "--source", SRC_UNCHANGED, "--bundle", "c" * 64)[0] == 2
    assert json.loads((w.tmp / "slots.json").read_text(encoding="utf-8"))["slots"][3]["status"] == "PLANNED"


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
    code, out = world().run("--admit", "S2", "--source", SRC_REPAIRED)
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


def test_rejected_or_invalid_training_never_counts_as_started():
    def fn(w):
        w.done_training("M1", 10500)
        w.receipts["r/m1/result.json"]["job"] = "job-other"
        w.done_training("M2", 10500)
        w.invalid("M2")
    loaded, acct = world(fn).account()
    assert acct["training_started"] == [] and acct["rejected"] == ["M1"], acct


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
    assert "M1" not in acct["training_started"] and "job=job-s2" in acct["shared"], acct["shared"]
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
    rejected(world(other_source), "M1", "SOURCE_NOT_THE_ADMITTED_SOURCE")
    rejected(world(lambda w: w.done_watched("P1b", "p1b", admitted_bundle="d" * 64)), "P1b", "BUNDLE_NOT_THE_ADMITTED_BUNDLE")
    rejected(world(lambda w: w.done_watched("P1b", "p1b", launched="2026-09-24T08:00:00Z", ended="2026-09-24T08:35:00Z")),
             "P1b", "LAUNCH_NOT_AFTER_ADMISSION")
    w = world(lambda w: w.done_watched("P1b", "p1b"))
    assert w.row("P1b")["receipt"] == "ACCEPTED", w.row("P1b")


def test_one_source_per_training_arm():
    def fn(w):
        w.done_training("M1", 10500)           # UNCHANGED arm, source 444...
        w.done_training("M2", 10500)           # REPAIRED arm, source 333...
    w = world(fn)
    code, out = w.run("--admit", "M3", "--source", "5" * 40)
    assert code == 1 and any(r.startswith("ARM_SOURCE_CONFLICT:M2") for r in out["reasons"]), out
    code, out = w.run("--admit", "M3", "--source", SRC_UNCHANGED)
    assert code == 1 and any("M1 is the other arm" in r for r in out["reasons"]), out
    code, out = w.run("--admit", "M3", "--source", SRC_REPAIRED)
    assert code == 0 and out["admission_record"]["model_seed"] == 20260918, out


def test_admitted_job_end_to_end():
    w = world()
    assert w.run(*admit_args("P1b"))[0] == 0
    launched, ended = "2026-09-24T12:05:00Z", "2026-09-24T12:40:00Z"
    doc = json.loads((w.tmp / "slots.json").read_text(encoding="utf-8"))
    w.slots = doc["slots"]
    admission = w.by_id("P1b")["admission"]
    w.done_watched("P1b", "p1b", launched=launched, ended=ended)
    w.by_id("P1b")["admission"] = admission                        # keep the gate's own record
    w.build()
    assert w.row("P1b")["receipt"] == "ACCEPTED", w.row("P1b")


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
        w.done_watched("P1b", "p1b", launched="2026-09-24T10:00:00Z", ended="2026-09-24T14:00:00Z", minutes=240.0,
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
