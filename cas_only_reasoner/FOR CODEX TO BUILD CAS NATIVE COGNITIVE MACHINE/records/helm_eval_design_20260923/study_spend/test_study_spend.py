"""Small pure-Python tests for study_spend.py (Codex review codex-0007, defects 1-4). Label CLAUDE_BUILT_CLAUDE_CHECKED.

Synthetic receipts only; a fake git reader; temporary folders. No AWS, no torch, no real receipt is changed.
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
S1_PATH, S2_PATH, M1_PATH, M2_PATH, M3_PATH = ("r/s1/result.json", "r/s2/result.json", "r/m1/result.json",
                                                "r/m2/result.json", "r/m3/result.json")
LAST = "r/s1/provider_0025.json"
BASIS_T = {"kind": "training_pointer", "instance_type": "g7.2xlarge", "instance_seconds_max": 14400,
           "rate_ceiling_usd_per_hour": "2.52", "launcher_ancillary_usd": "1.48"}
BASIS_W = {"kind": "watched_machine", "machine": "g4dn.2xlarge", "price_per_hour_usd": "0.752",
           "public_address_per_hour_usd": "0.005", "disk_gb_max": 100, "disk_usd_per_gb_month": "0.08",
           "hours_per_month": 730, "client_deadline_minutes_max": 130, "evidence_collection_allowance_usd": "0.00"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def enc(doc):
    return json.dumps(doc, sort_keys=True).encode("utf-8")


class FakeGit:
    def __init__(self):
        self.blobs, self.trees = {}, {}

    def read(self, commit, path):
        if (commit, path) not in self.blobs:
            raise FileNotFoundError(path)
        return self.blobs[(commit, path)]

    def names(self, commit, directory):
        if (commit, directory) not in self.trees:
            raise FileNotFoundError(directory)
        return list(self.trees[(commit, directory)])


def pointer(job, source, iid, elapsed=2431.2951856):
    return {"schema": ss.POINTER_SCHEMA, "job": job, "request": {"job": job},
            "authority": {"job": job, "source_sha": source, "instance_type": "g7.2xlarge", "instance_seconds_max": 14400},
            "preflight": {"instance_type": "g7.2xlarge", "rate_ceiling_usd": "2.52",
                          "observed_on_demand_hourly_usd": ["2.5200000000"]},
            "launch": {"instance_id": iid, "job": job}, "elapsed_seconds": elapsed, "status": "AWS_CANDIDATE_FINISHED",
            "stages": {"execution": "FINISHED", "compute_cleanup": "COMPLETE"},
            "cleanup": {"complete": True, "compute_identity_uncertain": False, "failures": [],
                        "instances_termination_pending": [], "instance_ids": [iid], "instances": {iid: "CONFIRMED_TERMINATED"},
                        "security_group_deleted": True, "roles_removed": True}}


def refusal(job, source, elapsed=25.66626610000094):
    d = pointer(job, source, None, elapsed)
    d.update(launch=None, status="AWS_CANDIDATE_FAILED",
             stages={"execution": "FAILED", "compute_cleanup": "INCOMPLETE"},
             outcome={"exception_type": "ClientError",
                      "exception": "An error occurred (InsufficientInstanceCapacity) when calling the RunInstances "
                                   "operation (reached max retries: 0): We currently do not have sufficient capacity."})
    d["cleanup"].update(complete=False, compute_identity_uncertain=True, instance_ids=[], instances={},
                        failures=["INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT"])
    return d


LAST_PROVIDER = {"operation": "run_instances", "state": "FAILED", "job": "job-s1",
                 "error": "ClientError:An error occurred (InsufficientInstanceCapacity) when calling the RunInstances operation"}
LAUNCH = {"schema": "claude.larger-question-t4-launch/0.1", "instance_id": "i-p1a", "launched_utc": "2026-09-24T05:53:38Z",
          "approved": {"machine": "g4dn.2xlarge", "price_per_hour_usd": 0.752, "dollar_ceiling": 3.0},
          "root_volume_gb": 100, "client_deadline_minutes": 130,
          "identity": {"source_commit": "e" * 40}, "bundle": {"sha256": "b" * 64}}
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


class World:
    """A synthetic study: S1 refusal, S2 finished, P1a watched (all DONE); P1b, P2, M1-M4, E1 planned; M5 optional."""

    def __init__(self, tmp):
        self.tmp, self.git = pathlib.Path(tmp), FakeGit()
        self.receipts = {S1_PATH: refusal("job-s1", "1" * 40), S2_PATH: pointer("job-s2", "2" * 40, "i-s2")}
        self.last_provider, self.tree = dict(LAST_PROVIDER), ["provider_0024.json", "provider_0025.json", "result.json"]
        self.launch, self.watch = copy.deepcopy(LAUNCH), copy.deepcopy(WATCH)
        e1 = dict(BASIS_W, evidence_collection_allowance_usd="0.10")
        p2 = dict(BASIS_W, machine="c7i.2xlarge", price_per_hour_usd="0.357")
        self.slots = [
            slot("S1", "DONE", "11.66", BASIS_T, {"kind": "pointer_capacity_refusal", "git_commit": C1, "path": S1_PATH,
                                                  "sha256": None, "last_provider_record": {"path": LAST, "sha256": None},
                                                  "expected": {"job": "job-s1", "source_sha": "1" * 40,
                                                               "instance_type": "g7.2xlarge"}}),
            slot("S2", "DONE", "11.66", BASIS_T, self.pointer_spec(S2_PATH, "job-s2", "2" * 40, "i-s2")),
            slot("P1a", "DONE", "3.00", BASIS_W, {"kind": "watched_machine",
                                                  "launch_record": {"path": "job/launch_record.json", "sha256": None},
                                                  "watch_record": {"path": "job/watch_record.json", "sha256": None},
                                                  "launch_schema": "claude.larger-question-t4-launch/0.1",
                                                  "watch_schema": "claude.larger-question-t4-watch/0.1",
                                                  "expected": {"instance_id": "i-p1a", "launched_utc": "2026-09-24T05:53:38Z",
                                                               "source_commit": "e" * 40, "bundle_sha256": "b" * 64}}),
            slot("P1b", "PLANNED", "2.00", BASIS_W, planned_watched()),
            slot("P2", "PLANNED", "1.00", p2, planned_watched()),
            slot("M1", "PLANNED", "11.66", BASIS_T, planned_pointer(), stop=True),
            slot("M2", "PLANNED", "11.66", BASIS_T, planned_pointer(), stop=True),
            slot("M3", "PLANNED", "11.66", BASIS_T, planned_pointer(), stop=True),
            slot("M4", "PLANNED", "11.66", BASIS_T, planned_pointer(), stop=True),
            slot("E1", "PLANNED", "2.00", e1, planned_watched()),
            slot("M5", "PLANNED", "11.66", BASIS_T, planned_pointer(), mandatory=False, stop=True)]
        self.pin_hashes = True

    @staticmethod
    def pointer_spec(path, job, source, iid):
        return {"kind": "pointer_finished", "git_commit": C1, "path": path, "sha256": None,
                "expected": {"job": job, "source_sha": source, "instance_id": iid, "instance_type": "g7.2xlarge"}}

    def by_id(self, sid):
        return next(s for s in self.slots if s["id"] == sid)

    def done_training(self, sid, path, elapsed):
        self.receipts[path] = pointer("job-" + sid, "3" * 40, "i-" + sid, elapsed)
        s = self.by_id(sid)
        s["status"], s["receipt"] = "DONE", self.pointer_spec(path, "job-" + sid, "3" * 40, "i-" + sid)

    def build(self, mutate_after_pin=None):
        """Write every file, pin every hash, then optionally change something AFTER pinning (a stale receipt)."""
        for path, doc in self.receipts.items():
            self.git.blobs[(C1, path)] = enc(doc)
        self.git.blobs[(C1, LAST)] = enc(self.last_provider)
        self.git.trees[(C1, "r/s1")] = self.tree
        (self.tmp / "job").mkdir(exist_ok=True)
        (self.tmp / "job" / "launch_record.json").write_bytes(enc(self.launch))
        (self.tmp / "job" / "watch_record.json").write_bytes(enc(self.watch))
        if self.pin_hashes:
            for s in self.slots:
                r = s["receipt"]
                if s["status"] != "DONE":
                    continue
                if r["kind"] in ("pointer_finished", "pointer_capacity_refusal") and r.get("path") and r.get("sha256") is None:
                    r["sha256"] = sha(self.git.blobs[(C1, r["path"])])
                if r["kind"] == "pointer_capacity_refusal" and r["last_provider_record"]["sha256"] is None:
                    r["last_provider_record"]["sha256"] = sha(self.git.blobs[(C1, LAST)])
                if r["kind"] == "watched_machine":
                    for key in ("launch_record", "watch_record"):
                        if r[key] and r[key]["sha256"] is None:
                            r[key]["sha256"] = sha((self.tmp / r[key]["path"]).read_bytes())
        if mutate_after_pin:
            mutate_after_pin(self)
        doc = {"schema": ss.SCHEMA, "ceiling_usd": "60.00",
               "owner_stop": {"usd": "30.00", "before_training_job_number": 3, "rule": "stop"},
               "allowances": {"s3_transfer_per_job_usd": "0.10"}, "slots": self.slots}
        (self.tmp / "slots.json").write_text(json.dumps(doc), encoding="utf-8")
        return self

    def run(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = ss.main(list(argv) + ["--no-write"], git=self.git, root=self.tmp, slots_file=self.tmp / "slots.json",
                           state_file=self.tmp / "state.json")
        text = out.getvalue()
        return code, (json.loads(text) if argv and argv[0] == "--admit" else text)

    def account(self):
        loaded = ss.load_slots(self.tmp / "slots.json")
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
    assert row["counted_usd"] == row["cap_usd"], row                     # an unvalidated receipt counts at full cap
    assert any(needle in p for p in row["receipt_problems"]), (needle, row["receipt_problems"])


# ---------------------------------------------------------------------------------------------------- baseline
def test_baseline_accepts_all_three_receipts_with_exact_bounds():
    w = world()
    assert w.row("S1")["counted_usd"] == "1.60"   # 25.666 s x 2.52/3600 + 1.48 + 0.10 = 1.597966 -> 1.60
    assert w.row("S2")["counted_usd"] == "3.29"   # 2431.295 s -> 3.281907 -> 3.29
    assert w.row("P1a")["counted_usd"] == "0.55"  # max(0.4489, 0.448829) + 0.10 -> 0.55
    assert "override" in w.row("S1")["receipt_pins"]
    loaded, acct = w.account()
    assert acct["spent"] == Decimal("5.44") and acct["rejected"] == []
    code, text = w.run()
    assert code == 0 and '"plan_C_worst_case_total_usd": "57.08"' in text, text


# ------------------------------------------------------------------------------------------ defect 3: pointer
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
        w.tree = w.tree + ["provider_0026.json"]

    def other_failure(w):
        w.receipts[S1_PATH]["cleanup"]["failures"].append("ROLE_DELETE_FAILED")

    def wrong_last(w):
        w.last_provider = dict(LAST_PROVIDER, operation="describe_instances")
    rejected(world(network), "S1", "NOT_AN_AWS_CAPACITY_REFUSAL")
    rejected(world(launched), "S1", "LAUNCH_RECORD_PRESENT")
    rejected(world(later_call), "S1", "A_PROVIDER_CALL_FOLLOWS")
    rejected(world(other_failure), "S1", "CLEANUP_FAILURES_NOT_ONLY")
    rejected(world(wrong_last), "S1", "LAST_PROVIDER_NOT_THE_CAPACITY_REFUSAL")

    def stale_last(w):
        w.git.blobs[(C1, LAST)] = enc(dict(LAST_PROVIDER, note="edited"))
    rejected(world(after_pin=stale_last), "S1", "LAST_PROVIDER_HASH_MISMATCH")


# ------------------------------------------------------------------------------------------ defect 3: watched
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
             "MACHINE_NOT_BASIS": lambda w: w.launch["approved"].update(machine="g5.xlarge"),
             "PRICE_NOT_BASIS": lambda w: w.launch["approved"].update(price_per_hour_usd=0.526),
             "DISK_OVER_BASIS": lambda w: w.launch.update(root_volume_gb=200),
             "DEADLINE_OVER_BASIS": lambda w: w.launch.update(client_deadline_minutes=240),
             "LAUNCH_CEILING_NOT_SLOT_CAP": lambda w: w.launch["approved"].update(dollar_ceiling=5.0),
             "NOT_CONFIRMED_TERMINATED": lambda w: w.watch.update(terminated_confirmed=False),
             "VOLUMES_LEFT_OR_UNKNOWN": lambda w: w.watch.update(volumes_of_this_job_remaining=[["vol-1", "available"]]),
             "VOLUMES_LEFT_OR_UNKNOWN:'unknown": lambda w: w.watch.update(volumes_of_this_job_remaining="unknown:ClientError"),
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


def test_done_slot_with_incomplete_receipt_spec_counts_full_cap():
    def fn(w):
        w.by_id("P1b")["status"] = "DONE"
    rejected(world(fn), "P1b", "RECEIPT_SPEC_INCOMPLETE")


# ----------------------------------------------------------------------------------- defect 1: caps vs basis
def test_cap_below_its_basis_is_an_input_error():
    def fn(w):
        w.by_id("P1a")["cap_usd"] = "1.66"   # the old P1a figure; its basis is 1.6639 + 0.10 -> 1.77
    w = world(fn)
    code, out = w.run("--admit", "P1b")
    assert code == 2 and "below its own basis" in out["error"], out
    code, _ = w.run()
    assert code == 2


def test_malformed_or_missing_slots_file_is_exit_2():
    w = world()
    (w.tmp / "slots.json").write_text("{not json", encoding="utf-8")
    assert w.run("--admit", "P1b")[0] == 2
    (w.tmp / "slots.json").unlink()
    assert w.run("--admit", "P1b")[0] == 2
    w = world(lambda w: w.by_id("P1b").update(status="LAUNCHED"))
    assert w.run("--admit", "P1b")[0] == 2
    w = world(lambda w: w.by_id("P1b").update(cap_usd=2.0))
    assert w.run("--admit", "P1b")[0] == 2


# ---------------------------------------------------------------------------------- defect 2: admission gate
def test_admit_pass_case():
    code, out = world().run("--admit", "P1b")
    assert code == 0 and out["decision"] == "ADMIT" and out["reasons"] == [], out
    assert "E1" in out["admission_arithmetic"] and "$57.08" in out["admission_arithmetic"], out
    assert "NOT checked here" in out["gate_scope"]


def test_admit_refuses_over_ceiling():
    def fn(w):
        w.by_id("E1")["cap_usd"] = "5.00"   # 5.44 + 2.00 + (1.00 + 46.64 + 5.00) = 60.08
    code, out = world(fn).run("--admit", "P1b")
    assert code == 1 and any(r.startswith("OVER_CEILING:$60.08") for r in out["reasons"]), out


def test_admit_exactly_at_ceiling_passes():
    def fn(w):
        w.by_id("E1")["cap_usd"] = "4.92"   # total exactly 60.00
    code, out = world(fn).run("--admit", "P1b")
    assert code == 0, out


def test_admit_refuses_slot_not_planned_running_or_rejected_receipt():
    code, out = world().run("--admit", "S2")
    assert code == 1 and "SLOT_NOT_PLANNED:DONE" in out["reasons"], out
    code, out = world(lambda w: w.by_id("M1").update(status="RUNNING")).run("--admit", "P2")
    assert code == 1 and any(r.startswith("ONE_MACHINE_AT_A_TIME") for r in out["reasons"]), out

    def bad(w):
        w.watch["cost_upper_bound_usd"] = -1
    code, out = world(bad).run("--admit", "P1b")
    assert code == 1 and "DONE_RECEIPT_REJECTED:P1a" in out["reasons"], out


def test_admit_unknown_slot_is_exit_2():
    code, out = world().run("--admit", "Z9")
    assert code == 2 and out["decision"] == "ERROR"


def test_running_and_invalid_slots_count_full_cap():
    def fn(w):
        w.by_id("P1b")["status"] = "INVALID"
        w.by_id("P1b")["invalid_reason"] = "test"
        w.by_id("M1")["status"] = "RUNNING"
    loaded, acct = world(fn).account()
    assert acct["spent"] == Decimal("5.44") + Decimal("2.00") + Decimal("11.66")


def test_invalid_without_reason_is_exit_2():
    assert world(lambda w: w.by_id("P1b").update(status="INVALID")).run("--admit", "P2")[0] == 2


# ----------------------------------------------------------------------------------------- the owner's $30 stop
def test_owner_stop_triggers_before_the_third_training_job():
    def fn(w):
        w.done_training("M1", M1_PATH, 14400)          # 11.66 each
        w.done_training("M2", M2_PATH, 14400)
        for sid in ("P1b", "P2"):                        # 2.00 + 1.00 at full cap
            w.by_id(sid).update(status="INVALID", invalid_reason="test")
    w = world(fn)
    loaded, acct = w.account()
    assert acct["spent"] == Decimal("31.76") and acct["training_started"] == ["M1", "M2"]
    code, out = w.run("--admit", "M3")
    assert code == 1 and any(r.startswith("OWNER_STOP_TRIGGERED") for r in out["reasons"]), out
    assert not any(r.startswith("OVER_CEILING") for r in out["reasons"]), out   # 31.76 + 11.66 + 11.66 + 2.00 = 57.08
    code, out = w.run("--admit", "E1")                                          # the stop halts every admission
    assert code == 1 and any(r.startswith("OWNER_STOP_TRIGGERED") for r in out["reasons"]), out


def test_owner_stop_boundary_and_window():
    loaded = ss.load_slots(world().tmp / "slots.json")
    base = {"rows": [], "rejected": [], "reserve": Decimal("25.32"), "planned_mandatory": [], "optional": [], "running": []}
    at_30 = ss.admit("M3", loaded, dict(base, spent=Decimal("30.00"), training_started=["M1", "M2"]))
    over = ss.admit("M3", loaded, dict(base, spent=Decimal("30.01"), training_started=["M1", "M2"]))
    after_third = ss.admit("M4", loaded, dict(base, spent=Decimal("30.01"), training_started=["M1", "M2", "M3"]))
    assert at_30["decision"] == "ADMIT", at_30             # "passes $30" means strictly more than $30.00
    assert over["decision"] == "REFUSE" and over["owner_stop"].startswith("TRIGGERED"), over
    assert after_third["owner_stop"].startswith("not triggered"), after_third


def test_smoke_runs_do_not_close_the_stop_window():
    loaded, acct = world().account()
    assert acct["training_started"] == []   # S1/S2 are DONE but counts_toward_training_stop is false


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
            print("FAIL", name, type(error).__name__, str(error)[:600])
    print("%d passed, %d failed" % (len(tests) - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run_all())
