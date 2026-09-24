"""HELM-REPAIR-CONTROLLED-1 study spend and admission gate. Label CLAUDE_BUILT_CLAUDE_CHECKED.

Answers Codex review `codex-0007` (defects 1-4). Pure Python; reads files and git objects only; no AWS call; never
reads or writes the meta1 ledger.

INPUT. `STUDY_SLOTS.json` is the ONE list of slots. Each slot has a status (PLANNED / RUNNING / DONE / INVALID), a
cap, the cap's basis (the arithmetic the cap must cover) and a receipt spec (where the receipt is, its pinned sha256
and the job / instance / source identity it must carry). The program reads it fresh on every run and never writes it.

ACCOUNTING (exact decimals, every bound rounded UP to the cent):
  * DONE with a receipt that passes validation -> the bound computed from that receipt;
  * DONE with a receipt that fails validation   -> its full cap, and every admission is refused until the runner fixes
                                                   the receipt pins or marks the slot INVALID;
  * RUNNING or INVALID                          -> its full cap;
  * PLANNED                                     -> nothing spent; if mandatory, its cap is reserved.
Every cap must be at least the worst case its own basis computes (a cap below its basis is an input error, exit 2;
this is the guard for the old P1a figure $1.66 < $1.6639).

ADMISSION (`--admit SLOT`): exit 0 only if ALL of these hold, else exit 1 with the reasons; any input error exit 2.
  * the slot exists and is PLANNED; no slot is RUNNING (one machine at a time); no DONE receipt is rejected;
  * spent upper bound + the slot's cap + the caps of every OTHER PLANNED mandatory slot (E1 included) <= $60.00;
  * the owner's stop is not triggered: spent upper bound > $30.00 while fewer than 3 training-stop slots are RUNNING
    or DONE stops the study (every admission refused).

Receipt kinds:
  pointer_finished          the typed-pointer launcher's result.json at a pinned git commit + sha256: job, source,
                            instance type and instance id equal the pins; cleanup complete; that one instance
                            CONFIRMED_TERMINATED; rate ceiling equal to the basis; elapsed seconds finite and > 0.
                            Bound = elapsed x rate ceiling + launcher ancillary + S3/transfer allowance.
  pointer_capacity_refusal  the same receipt for a launch AWS refused: status FAILED, no launch, no instance ids, the
                            only cleanup failure INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT, the exception AWS's
                            own InsufficientInstanceCapacity answer to RunInstances with zero client retries, and that
                            refusal the LAST provider call (pinned file, no later provider_NNNN.json). This overrides the
                            launcher's own compute_identity_uncertain flag; the override is printed. Same bound formula.
  watched_machine           launch_record.json + watch_record.json at pinned paths + sha256: instance id and launch time
                            equal the pins in BOTH files; source commit and bundle sha256 equal the pins; machine and
                            price equal the basis; disk and client deadline within the basis; ceiling equal to the cap;
                            terminated confirmed; no volume left; the watcher's cost finite, >= 0, <= the cap, and not
                            below the cost recomputed from the two timestamps. Bound = max(recorded, recomputed) +
                            evidence-collection allowance + S3/transfer allowance.
"""
import argparse
import datetime
import hashlib
import json
import math
import pathlib
import re
import subprocess
import sys
from decimal import ROUND_CEILING, Decimal, getcontext

getcontext().prec = 40
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                      # receipt paths of watched jobs are relative to the design folder
SLOTS_FILE = HERE / "STUDY_SLOTS.json"
STATE_FILE = HERE / "STUDY_SPEND_STATE.json"
SCHEMA = "claude.helm-repair-controlled-1.study-slots/0.2"
STATUSES = ("PLANNED", "RUNNING", "DONE", "INVALID")
POINTER_SCHEMA = "cas-graph-training-candidate-launch/1"
CENT, SIX = Decimal("0.01"), Decimal("0.000001")
SHA = re.compile(r"^[0-9a-f]{64}$")
MONEY = re.compile(r"^\d+\.\d{2}$")
DECIMAL = re.compile(r"^\d+(\.\d+)?$")


class InputError(Exception):
    """A malformed slots file or a cap below its own basis: the program cannot decide anything (exit 2)."""


def up(x):
    """Round an upper bound UP to the cent."""
    return x.quantize(CENT, rounding=ROUND_CEILING)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def money(value, what):
    if not isinstance(value, str) or not MONEY.match(value):
        raise InputError("%s must be a dollar string like '2.00', got %r" % (what, value))
    return Decimal(value)


def decimal_str(value, what):
    if not isinstance(value, str) or not DECIMAL.match(value):
        raise InputError("%s must be a non-negative decimal string, got %r" % (what, value))
    return Decimal(value)


def positive_int(value, what):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InputError("%s must be a positive integer, got %r" % (what, value))
    return value


def number(value):
    """A receipt number: int or float, not bool, finite. Returns a Decimal or None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return Decimal(str(value))


def utc(text):
    if not isinstance(text, str) or not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", text):
        return None
    return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


# ----------------------------------------------------------------------------------------------------- cap basis
def basis_worst_case(basis, allowance):
    """Exact worst case a cap must cover. Returns (Decimal, arithmetic text)."""
    kind = basis.get("kind")
    if kind == "training_pointer":
        seconds = positive_int(basis.get("instance_seconds_max"), "instance_seconds_max")
        rate = decimal_str(basis.get("rate_ceiling_usd_per_hour"), "rate_ceiling_usd_per_hour")
        ancillary = decimal_str(basis.get("launcher_ancillary_usd"), "launcher_ancillary_usd")
        if not isinstance(basis.get("instance_type"), str):
            raise InputError("training_pointer basis needs instance_type")
        worst = Decimal(seconds) / 3600 * rate + ancillary + allowance
        return worst, "%d s x $%s/h + $%s launcher ancillary + $%s S3/transfer = $%s" % (
            seconds, rate, ancillary, allowance, worst.quantize(SIX))
    if kind == "watched_machine":
        per_hour = watched_per_hour(basis)
        minutes = positive_int(basis.get("client_deadline_minutes_max"), "client_deadline_minutes_max")
        collection = decimal_str(basis.get("evidence_collection_allowance_usd"), "evidence_collection_allowance_usd")
        if not isinstance(basis.get("machine"), str):
            raise InputError("watched_machine basis needs machine")
        worst = per_hour * minutes / 60 + collection + allowance
        return worst, "(%s + %s address + %d GB x %s / %d disk) = %s/h x %d/60 h + $%s collection + $%s S3/transfer = $%s" % (
            basis["price_per_hour_usd"], basis["public_address_per_hour_usd"], basis["disk_gb_max"],
            basis["disk_usd_per_gb_month"], basis["hours_per_month"], per_hour.quantize(SIX), minutes, collection, allowance,
            worst.quantize(SIX))
    raise InputError("unknown cap_basis kind %r" % kind)


def watched_per_hour(basis, price=None, disk_gb=None):
    price = decimal_str(basis.get("price_per_hour_usd"), "price_per_hour_usd") if price is None else price
    address = decimal_str(basis.get("public_address_per_hour_usd"), "public_address_per_hour_usd")
    disk_gb = positive_int(basis.get("disk_gb_max"), "disk_gb_max") if disk_gb is None else disk_gb
    disk_rate = decimal_str(basis.get("disk_usd_per_gb_month"), "disk_usd_per_gb_month")
    hours = positive_int(basis.get("hours_per_month"), "hours_per_month")
    return price + address + Decimal(disk_gb) * disk_rate / hours


# ------------------------------------------------------------------------------------------------------- slots
def load_slots(path):
    try:
        raw = pathlib.Path(path).read_bytes()
        doc = json.loads(raw)
    except (OSError, ValueError) as error:
        raise InputError("slots file unreadable: %s: %s" % (type(error).__name__, error))
    if doc.get("schema") != SCHEMA:
        raise InputError("slots file schema %r is not %r" % (doc.get("schema"), SCHEMA))
    ceiling = money(doc.get("ceiling_usd"), "ceiling_usd")
    stop = doc.get("owner_stop") or {}
    stop_usd = money(stop.get("usd"), "owner_stop.usd")
    stop_n = positive_int(stop.get("before_training_job_number"), "owner_stop.before_training_job_number")
    allowance = money((doc.get("allowances") or {}).get("s3_transfer_per_job_usd"), "allowances.s3_transfer_per_job_usd")
    slots, seen = doc.get("slots"), set()
    if not isinstance(slots, list) or not slots:
        raise InputError("slots must be a non-empty list")
    for slot in slots:
        sid = slot.get("id")
        if not isinstance(sid, str) or not sid or sid in seen:
            raise InputError("slot id missing or repeated: %r" % sid)
        seen.add(sid)
        if slot.get("status") not in STATUSES:
            raise InputError("%s: status %r not in %s" % (sid, slot.get("status"), STATUSES))
        for flag in ("mandatory", "counts_toward_training_stop"):
            if not isinstance(slot.get(flag), bool):
                raise InputError("%s: %s must be true or false" % (sid, flag))
        cap = money(slot.get("cap_usd"), "%s.cap_usd" % sid)
        basis = slot.get("cap_basis")
        if not isinstance(basis, dict):
            raise InputError("%s: cap_basis missing" % sid)
        worst, arithmetic = basis_worst_case(basis, allowance)
        if cap < up(worst):
            raise InputError("%s: cap $%s is below its own basis worst case $%s (%s)" % (sid, cap, up(worst), arithmetic))
        receipt = slot.get("receipt")
        if not isinstance(receipt, dict):
            raise InputError("%s: receipt spec missing" % sid)
        allowed = {"training_pointer": ("pointer_finished", "pointer_capacity_refusal"),
                   "watched_machine": ("watched_machine",)}[basis["kind"]]
        if receipt.get("kind") not in allowed:
            raise InputError("%s: receipt kind %r does not fit basis %r" % (sid, receipt.get("kind"), basis["kind"]))
        if slot["status"] == "INVALID" and not isinstance(slot.get("invalid_reason"), str):
            raise InputError("%s: an INVALID slot needs invalid_reason" % sid)
        slot["_cap"], slot["_worst"], slot["_worst_text"] = cap, worst, arithmetic
    return {"doc": doc, "sha256": sha256(raw), "ceiling": ceiling, "stop_usd": stop_usd, "stop_n": stop_n,
            "allowance": allowance, "slots": slots}


# ---------------------------------------------------------------------------------------------------- receipts
class GitReader:
    """Reads blobs at a pinned commit of the repository that holds this folder."""

    def __init__(self, repo=HERE):
        self.repo = str(repo)

    def read(self, commit, path):
        done = subprocess.run(["git", "-C", self.repo, "show", "%s:%s" % (commit, path)], capture_output=True)
        if done.returncode != 0:
            raise FileNotFoundError("git show %s:%s failed" % (commit, path))
        return done.stdout

    def names(self, commit, directory):
        done = subprocess.run(["git", "-C", self.repo, "ls-tree", "--full-tree", "--name-only", commit,
                               directory.rstrip("/") + "/"],
                              capture_output=True, text=True)
        if done.returncode != 0:
            raise FileNotFoundError("git ls-tree %s %s failed" % (commit, directory))
        return [line.rsplit("/", 1)[-1] for line in done.stdout.splitlines() if line]


def spec_complete(receipt, keys):
    return all(receipt.get(k) not in (None, "", {}) for k in keys)


def read_pinned_git(git, commit, path, pinned, problems, label):
    if not (isinstance(commit, str) and re.match(r"^[0-9a-f]{40}$", commit) and isinstance(path, str)
            and isinstance(pinned, str) and SHA.match(pinned)):
        problems.append("%s_PIN_MALFORMED" % label)
        return None
    try:
        raw = git.read(commit, path)
    except (OSError, FileNotFoundError):
        problems.append("%s_MISSING:%s:%s" % (label, commit[:8], path))
        return None
    if sha256(raw) != pinned:
        problems.append("%s_HASH_MISMATCH(stale or replaced):%s" % (label, sha256(raw)))
        return None
    try:
        doc = json.loads(raw)
    except ValueError:
        problems.append("%s_NOT_JSON" % label)
        return None
    if not isinstance(doc, dict):
        problems.append("%s_NOT_AN_OBJECT" % label)
        return None
    return doc


def pointer_common(d, expected, basis, problems):
    """Identity and rate checks shared by both pointer kinds. Returns (elapsed, rate) or (None, None)."""
    if not isinstance(d, dict):
        problems.append("RECEIPT_NOT_AN_OBJECT")
        return None, None
    authority, preflight = d.get("authority") or {}, d.get("preflight") or {}
    if d.get("schema") != POINTER_SCHEMA:
        problems.append("SCHEMA:%r" % d.get("schema"))
    for where, value in (("job", d.get("job")), ("authority.job", authority.get("job")),
                         ("request.job", (d.get("request") or {}).get("job"))):
        if value != expected.get("job"):
            problems.append("JOB_MISMATCH:%s=%r" % (where, value))
    if authority.get("source_sha") != expected.get("source_sha"):
        problems.append("SOURCE_MISMATCH:%r" % authority.get("source_sha"))
    for where, value in (("authority.instance_type", authority.get("instance_type")),
                         ("preflight.instance_type", preflight.get("instance_type"))):
        if value != expected.get("instance_type") or value != basis.get("instance_type"):
            problems.append("INSTANCE_TYPE_MISMATCH:%s=%r" % (where, value))
    seconds_max = authority.get("instance_seconds_max")
    if isinstance(seconds_max, bool) or not isinstance(seconds_max, int) or seconds_max > basis["instance_seconds_max"]:
        problems.append("INSTANCE_SECONDS_MAX_OVER_BASIS:%r" % seconds_max)
    rate = basis["rate_ceiling_usd_per_hour"]
    if preflight.get("rate_ceiling_usd") != rate:
        problems.append("RATE_CEILING_NOT_BASIS:%r" % preflight.get("rate_ceiling_usd"))
    observed = preflight.get("observed_on_demand_hourly_usd")
    if not isinstance(observed, list) or not observed or not all(
            isinstance(x, str) and DECIMAL.match(x) and Decimal(x) <= Decimal(rate) for x in observed):
        problems.append("OBSERVED_RATE_MISSING_OR_OVER_CEILING:%r" % observed)
    elapsed = number(d.get("elapsed_seconds"))
    if elapsed is None or elapsed <= 0:
        problems.append("ELAPSED_SECONDS_MISSING_NONFINITE_OR_NOT_POSITIVE:%r" % d.get("elapsed_seconds"))
        elapsed = None
    return elapsed, Decimal(rate)


def validate_pointer_finished(slot, git, allowance):
    receipt, basis, problems = slot["receipt"], slot["cap_basis"], []
    if not spec_complete(receipt, ("git_commit", "path", "sha256", "expected")) or not spec_complete(
            receipt["expected"], ("job", "source_sha", "instance_id", "instance_type")):
        return None, "", ["RECEIPT_SPEC_INCOMPLETE"], {}
    expected = receipt["expected"]
    d = read_pinned_git(git, receipt["git_commit"], receipt["path"], receipt["sha256"], problems, "RECEIPT")
    if d is None:
        return None, "", problems, {}
    elapsed, rate = pointer_common(d, expected, basis, problems)
    iid, cleanup = expected["instance_id"], d.get("cleanup") or {}
    if (d.get("launch") or {}).get("instance_id") != iid:
        problems.append("INSTANCE_MISMATCH:launch.instance_id=%r" % (d.get("launch") or {}).get("instance_id"))
    if cleanup.get("instance_ids") != [iid] or cleanup.get("instances") != {iid: "CONFIRMED_TERMINATED"}:
        problems.append("CLEANUP_NOT_THIS_ONE_INSTANCE_TERMINATED:%r" % cleanup.get("instances"))
    if cleanup.get("complete") is not True or cleanup.get("compute_identity_uncertain") is not False:
        problems.append("CLEANUP_INCOMPLETE_OR_IDENTITY_UNCERTAIN")
    if cleanup.get("failures") != [] or cleanup.get("instances_termination_pending") != []:
        problems.append("CLEANUP_FAILURES_OR_PENDING:%r" % cleanup.get("failures"))
    if (d.get("stages") or {}).get("compute_cleanup") != "COMPLETE":
        problems.append("STAGE_COMPUTE_CLEANUP:%r" % (d.get("stages") or {}).get("compute_cleanup"))
    if problems:
        return None, "", problems, {}
    ancillary = Decimal(basis["launcher_ancillary_usd"])
    exact = elapsed / 3600 * rate + ancillary + allowance
    return up(exact), "elapsed %s s x $%s/h + $%s launcher ancillary + $%s S3/transfer = $%s" % (
        elapsed, rate, ancillary, allowance, exact.quantize(SIX)), [], {"receipt_sha256": receipt["sha256"]}


def validate_pointer_capacity_refusal(slot, git, allowance):
    receipt, basis, problems = slot["receipt"], slot["cap_basis"], []
    if not spec_complete(receipt, ("git_commit", "path", "sha256", "expected", "last_provider_record")) or not \
            spec_complete(receipt["expected"], ("job", "source_sha", "instance_type")):
        return None, "", ["RECEIPT_SPEC_INCOMPLETE"], {}
    expected, last = receipt["expected"], receipt["last_provider_record"]
    d = read_pinned_git(git, receipt["git_commit"], receipt["path"], receipt["sha256"], problems, "RECEIPT")
    if d is None:
        return None, "", problems, {}
    elapsed, rate = pointer_common(d, expected, basis, problems)
    cleanup, outcome = d.get("cleanup") or {}, d.get("outcome") or {}
    if d.get("status") != "AWS_CANDIDATE_FAILED" or (d.get("stages") or {}).get("execution") != "FAILED":
        problems.append("NOT_A_FAILED_LAUNCH:%r" % d.get("status"))
    if d.get("launch") is not None:
        problems.append("LAUNCH_RECORD_PRESENT")
    if cleanup.get("instance_ids") != [] or cleanup.get("instances") != {} or cleanup.get("instances_termination_pending") != []:
        problems.append("CLEANUP_NAMES_AN_INSTANCE")
    if cleanup.get("failures") != ["INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT"]:
        problems.append("CLEANUP_FAILURES_NOT_ONLY_IDENTITY_UNKNOWN:%r" % cleanup.get("failures"))
    if cleanup.get("security_group_deleted") is not True or cleanup.get("roles_removed") is not True:
        problems.append("SIDE_RESOURCES_NOT_REMOVED")
    text = outcome.get("exception")
    if outcome.get("exception_type") != "ClientError" or not isinstance(text, str) or not all(
            s in text for s in ("(InsufficientInstanceCapacity)", "RunInstances operation", "reached max retries: 0")):
        problems.append("NOT_AN_AWS_CAPACITY_REFUSAL_OF_RUNINSTANCES")
    p = read_pinned_git(git, receipt["git_commit"], last.get("path"), last.get("sha256"), problems, "LAST_PROVIDER")
    if p is not None:
        err = p.get("error") if isinstance(p, dict) else None
        if not (isinstance(p, dict) and p.get("operation") == "run_instances" and p.get("state") == "FAILED"
                and p.get("job") == expected["job"] and isinstance(err, str) and "(InsufficientInstanceCapacity)" in err):
            problems.append("LAST_PROVIDER_NOT_THE_CAPACITY_REFUSAL")
        directory, name = last["path"].rsplit("/", 1)
        try:
            numbers = [int(n[9:13]) for n in git.names(receipt["git_commit"], directory)
                       if re.match(r"^provider_\d{4}\.json$", n)]
        except (OSError, FileNotFoundError):
            numbers = []
        if not re.match(r"^provider_\d{4}\.json$", name) or not numbers or max(numbers) != int(name[9:13]):
            problems.append("A_PROVIDER_CALL_FOLLOWS_THE_REFUSAL_OR_LIST_UNREADABLE")
    if problems:
        return None, "", problems, {}
    ancillary = Decimal(basis["launcher_ancillary_usd"])
    exact = elapsed / 3600 * rate + ancillary + allowance
    note = ("launcher flag compute_identity_uncertain=%r overridden by the capacity-refusal rule: the last provider "
            "call is RunInstances refused by AWS (InsufficientInstanceCapacity, zero client retries); no machine was "
            "created" % cleanup.get("compute_identity_uncertain"))
    return up(exact), "elapsed %s s x $%s/h + $%s launcher ancillary + $%s S3/transfer = $%s (no machine ran)" % (
        elapsed, rate, ancillary, allowance, exact.quantize(SIX)), [], {"receipt_sha256": receipt["sha256"], "override": note}


def read_pinned_file(root, spec, problems, label):
    if not isinstance(spec, dict) or not isinstance(spec.get("path"), str) or not SHA.match(str(spec.get("sha256"))):
        problems.append("%s_PIN_MALFORMED" % label)
        return None
    rel = pathlib.PurePosixPath(spec["path"])
    if rel.is_absolute() or ".." in rel.parts:
        problems.append("%s_PATH_ESCAPES_ROOT" % label)
        return None
    path = pathlib.Path(root) / rel
    if not path.is_file():
        problems.append("%s_MISSING:%s" % (label, spec["path"]))
        return None
    raw = path.read_bytes()
    if sha256(raw) != spec["sha256"]:
        problems.append("%s_HASH_MISMATCH(stale or replaced):%s" % (label, sha256(raw)))
        return None
    try:
        doc = json.loads(raw)
    except ValueError:
        problems.append("%s_NOT_JSON" % label)
        return None
    if not isinstance(doc, dict):
        problems.append("%s_NOT_AN_OBJECT" % label)
        return None
    return doc


def validate_watched(slot, root, allowance):
    receipt, basis, problems = slot["receipt"], slot["cap_basis"], []
    if not spec_complete(receipt, ("launch_record", "watch_record", "launch_schema", "watch_schema", "expected")) or \
            not spec_complete(receipt["expected"], ("instance_id", "launched_utc", "source_commit", "bundle_sha256")):
        return None, "", ["RECEIPT_SPEC_INCOMPLETE"], {}
    expected = receipt["expected"]
    launch = read_pinned_file(root, receipt["launch_record"], problems, "LAUNCH_RECORD")
    watch = read_pinned_file(root, receipt["watch_record"], problems, "WATCH_RECORD")
    if launch is None or watch is None:
        return None, "", problems, {}
    approved = launch.get("approved") or {}
    if launch.get("schema") != receipt["launch_schema"]:
        problems.append("LAUNCH_SCHEMA:%r" % launch.get("schema"))
    if watch.get("schema") != receipt["watch_schema"]:
        problems.append("WATCH_SCHEMA:%r" % watch.get("schema"))
    for where, value in (("launch", launch.get("instance_id")), ("watch", watch.get("instance_id"))):
        if value != expected["instance_id"]:
            problems.append("INSTANCE_MISMATCH:%s=%r" % (where, value))
    for where, value in (("launch", launch.get("launched_utc")), ("watch", watch.get("launched_utc"))):
        if value != expected["launched_utc"]:
            problems.append("LAUNCH_TIME_MISMATCH:%s=%r" % (where, value))
    if (launch.get("identity") or {}).get("source_commit") != expected["source_commit"]:
        problems.append("SOURCE_MISMATCH:%r" % (launch.get("identity") or {}).get("source_commit"))
    if (launch.get("bundle") or {}).get("sha256") != expected["bundle_sha256"]:
        problems.append("BUNDLE_MISMATCH:%r" % (launch.get("bundle") or {}).get("sha256"))
    if approved.get("machine") != basis["machine"]:
        problems.append("MACHINE_NOT_BASIS:%r" % approved.get("machine"))
    price = number(approved.get("price_per_hour_usd"))
    if price is None or price != Decimal(basis["price_per_hour_usd"]):
        problems.append("PRICE_NOT_BASIS:%r" % approved.get("price_per_hour_usd"))
    disk, deadline = launch.get("root_volume_gb"), launch.get("client_deadline_minutes")
    if isinstance(disk, bool) or not isinstance(disk, int) or not 0 < disk <= basis["disk_gb_max"]:
        problems.append("DISK_OVER_BASIS:%r" % disk)
    if isinstance(deadline, bool) or not isinstance(deadline, int) or not 0 < deadline <= basis["client_deadline_minutes_max"]:
        problems.append("DEADLINE_OVER_BASIS:%r" % deadline)
    ceiling = number(approved.get("dollar_ceiling"))
    if ceiling is None or ceiling != slot["_cap"]:
        problems.append("LAUNCH_CEILING_NOT_SLOT_CAP:%r" % approved.get("dollar_ceiling"))
    if watch.get("terminated_confirmed") is not True or watch.get("final_state") not in ("terminated", "gone"):
        problems.append("NOT_CONFIRMED_TERMINATED:%r" % watch.get("final_state"))
    if watch.get("volumes_of_this_job_remaining") != []:
        problems.append("VOLUMES_LEFT_OR_UNKNOWN:%r" % watch.get("volumes_of_this_job_remaining"))
    cost = number(watch.get("cost_upper_bound_usd"))
    if cost is None or cost < 0 or cost > slot["_cap"]:
        problems.append("WATCH_COST_INVALID:%r" % watch.get("cost_upper_bound_usd"))
    minutes = number(watch.get("minutes_from_launch_to_watch_end"))
    start, end = utc(watch.get("launched_utc")), utc(watch.get("watch_ended_utc"))
    if minutes is None or minutes <= 0 or start is None or end is None or end <= start:
        problems.append("WATCH_TIMES_INVALID")
    if problems:
        return None, "", problems, {}
    seconds = Decimal(int((end - start).total_seconds()))
    if abs(minutes - seconds / 60) > Decimal("0.1"):
        problems.append("WATCH_MINUTES_DISAGREE_WITH_TIMESTAMPS:%s vs %s s" % (minutes, seconds))
    recomputed = seconds / 3600 * watched_per_hour(basis, price=price, disk_gb=disk)
    if cost < recomputed - Decimal("0.0001"):
        problems.append("WATCH_COST_BELOW_RECOMPUTED:%s < %s" % (cost, recomputed))
    if problems:
        return None, "", problems, {}
    collection = Decimal(basis["evidence_collection_allowance_usd"])
    machine = max(cost, recomputed)
    exact = machine + collection + allowance
    return up(exact), ("max(watcher $%s, recomputed %s s x $%s/h = $%s) + $%s collection + $%s S3/transfer = $%s" % (
        cost, seconds, watched_per_hour(basis, price=price, disk_gb=disk).quantize(Decimal("0.000001")),
        recomputed.quantize(Decimal("0.000001")), collection, allowance, exact)), [], {
        "launch_record_sha256": receipt["launch_record"]["sha256"], "watch_record_sha256": receipt["watch_record"]["sha256"]}


def validate_receipt(slot, root, git, allowance):
    kind = slot["receipt"]["kind"]
    if kind == "pointer_finished":
        return validate_pointer_finished(slot, git, allowance)
    if kind == "pointer_capacity_refusal":
        return validate_pointer_capacity_refusal(slot, git, allowance)
    return validate_watched(slot, root, allowance)


# ------------------------------------------------------------------------------------------ accounting + admission
def account(loaded, root, git):
    rows, spent, rejected = [], Decimal("0"), []
    for slot in loaded["slots"]:
        row = {"slot": slot["id"], "what": slot.get("what"), "status": slot["status"], "mandatory": slot["mandatory"],
               "cap_usd": str(slot["_cap"]), "basis_worst_case_usd": str(up(slot["_worst"])),
               "basis_arithmetic": slot["_worst_text"]}
        if slot["status"] == "DONE":
            bound, text, problems, pins = validate_receipt(slot, root, git, loaded["allowance"])
            if problems:
                rejected.append(slot["id"])
                row.update(receipt="REJECTED", receipt_problems=problems, counted_usd=str(slot["_cap"]),
                           counted_basis="receipt rejected: full cap")
            else:
                row.update(receipt="ACCEPTED", counted_usd=str(bound), counted_basis=text, receipt_pins=pins)
        elif slot["status"] in ("RUNNING", "INVALID"):
            row.update(receipt="NOT_FINAL", counted_usd=str(slot["_cap"]),
                       counted_basis="%s: full cap%s" % (slot["status"], (": " + slot["invalid_reason"])
                                                          if slot["status"] == "INVALID" else ""))
        else:
            row.update(receipt="NOT_APPLICABLE", counted_usd="0.00",
                       counted_basis="PLANNED: nothing spent; cap %s" % ("reserved" if slot["mandatory"] else "not reserved (optional)"))
        for key in ("scope", "runtime_bound", "cleanup_bound", "timing_feasibility", "preconditions_outside_money_gate"):
            if key in slot:
                row[key] = slot[key]
        spent += Decimal(row["counted_usd"])
        rows.append(row)
    planned_mandatory = [s for s in loaded["slots"] if s["status"] == "PLANNED" and s["mandatory"]]
    reserve = sum((s["_cap"] for s in planned_mandatory), Decimal("0"))
    optional = [s for s in loaded["slots"] if s["status"] == "PLANNED" and not s["mandatory"]]
    started = [s["id"] for s in loaded["slots"] if s["counts_toward_training_stop"] and s["status"] in ("RUNNING", "DONE")]
    return {"rows": rows, "spent": spent, "rejected": rejected, "reserve": reserve,
            "planned_mandatory": [s["id"] for s in planned_mandatory], "optional": optional,
            "running": [s["id"] for s in loaded["slots"] if s["status"] == "RUNNING"], "training_started": started}


def admit(slot_id, loaded, acct):
    slots = {s["id"]: s for s in loaded["slots"]}
    if slot_id not in slots:
        raise InputError("no slot named %r" % slot_id)
    slot, reasons = slots[slot_id], []
    if acct["rejected"]:
        reasons.append("DONE_RECEIPT_REJECTED:%s" % ",".join(acct["rejected"]))
    if slot["status"] != "PLANNED":
        reasons.append("SLOT_NOT_PLANNED:%s" % slot["status"])
    if acct["running"]:
        reasons.append("ONE_MACHINE_AT_A_TIME:RUNNING=%s" % ",".join(acct["running"]))
    others = acct["reserve"] - (slot["_cap"] if slot["status"] == "PLANNED" and slot["mandatory"] else 0)
    total = acct["spent"] + slot["_cap"] + others
    arithmetic = "spent upper bound $%s + %s cap $%s + other mandatory caps $%s (%s) = $%s vs ceiling $%s" % (
        acct["spent"], slot_id, slot["_cap"], others,
        ",".join(i for i in acct["planned_mandatory"] if i != slot_id) or "none", total, loaded["ceiling"])
    if total > loaded["ceiling"]:
        reasons.append("OVER_CEILING:$%s > $%s" % (total, loaded["ceiling"]))
    stop = len(acct["training_started"]) < loaded["stop_n"] and acct["spent"] > loaded["stop_usd"]
    stop_text = "spent upper bound $%s %s $%s with %d of %d training jobs started (%s)" % (
        acct["spent"], ">" if acct["spent"] > loaded["stop_usd"] else "<=", loaded["stop_usd"],
        len(acct["training_started"]), loaded["stop_n"], ",".join(acct["training_started"]) or "none")
    if stop:
        reasons.append("OWNER_STOP_TRIGGERED:stop and report:%s" % stop_text)
    return {"slot": slot_id, "decision": "REFUSE" if reasons else "ADMIT", "reasons": reasons,
            "admission_arithmetic": arithmetic, "owner_stop": ("TRIGGERED: " if stop else "not triggered: ") + stop_text,
            "gate_scope": "money ceiling, owner stop, one machine at a time and receipt validity ONLY; technical "
                          "readiness (reviews, builds) is a separate admission and is NOT checked here",
            "preconditions_outside_money_gate": slot.get("preconditions_outside_money_gate", [])}


def state_document(loaded, acct):
    spent, ceiling = acct["spent"], loaded["ceiling"]
    plan_total = spent + acct["reserve"]
    fallback = sum((s["_cap"] for s in acct["optional"]), Decimal("0"))
    sensitivity = {r["slot"]: str(plan_total - Decimal(r["counted_usd"]) + Decimal(r["cap_usd"]))
                   for r in acct["rows"] if r["status"] == "DONE"}
    previews = {s["id"]: admit(s["id"], loaded, acct) for s in loaded["slots"] if s["status"] == "PLANNED"}
    return {"schema": "claude.helm-repair-controlled-1.study-spend/0.2", "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
            "inputs": {"slots_file": "STUDY_SLOTS.json", "slots_file_sha256": loaded["sha256"]},
            "ceiling_usd": str(ceiling), "s3_transfer_allowance_per_job_usd": str(loaded["allowance"]),
            "spent_upper_bound_usd": str(spent), "rejected_done_receipts": acct["rejected"],
            "slots": acct["rows"],
            "remaining_mandatory_slots": acct["planned_mandatory"],
            "remaining_mandatory_caps_usd": str(acct["reserve"]),
            "plan_C_worst_case_total_usd": str(plan_total), "plan_C_fits_ceiling_at_worst_case": plan_total <= ceiling,
            "headroom_usd": str(ceiling - plan_total),
            "fallback_B_slots": [s["id"] for s in acct["optional"]], "fallback_B_extra_caps_usd": str(fallback),
            "fallback_B_fits_at_worst_case": plan_total + fallback <= ceiling,
            "plan_C_total_if_this_DONE_slot_were_counted_at_its_full_cap_usd": sensitivity,
            "admission_preview": previews,
            "rules": {"admission": "spent upper bound + next cap + every other PLANNED mandatory cap (E1 included) <= "
                                   "ceiling; slot PLANNED; nothing RUNNING; no DONE receipt rejected; owner stop not triggered",
                      "owner_stop": loaded["doc"]["owner_stop"]["rule"],
                      "rounding": "every bound rounded UP to the cent; exact decimals, no floats"},
            "meta1_ledger": "not read or written by this program; training bookings are the launcher's own bookkeeping"}


def main(argv=None, git=None, root=ROOT, slots_file=SLOTS_FILE, state_file=STATE_FILE):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--admit", metavar="SLOT", help="decide one admission; exit 0 ADMIT, 1 REFUSE, 2 error")
    parser.add_argument("--no-write", action="store_true", help="do not write STUDY_SPEND_STATE.json")
    args = parser.parse_args(argv)
    git = git or GitReader()
    try:
        loaded = load_slots(slots_file)
        acct = account(loaded, root, git)
        if args.admit:
            decision = admit(args.admit, loaded, acct)
            decision.update(spent_upper_bound_usd=str(acct["spent"]), slots_file_sha256=loaded["sha256"],
                            receipts={r["slot"]: r.get("receipt_pins") or r.get("receipt_problems")
                                      for r in acct["rows"] if r["status"] == "DONE"})
            print(json.dumps(decision, indent=1))
            return 0 if decision["decision"] == "ADMIT" else 1
        state = state_document(loaded, acct)
    except Exception as error:                  # fail closed: any error is exit 2, never a silent admit or refuse
        print(json.dumps({"decision": "ERROR", "error": "%s: %s" % (type(error).__name__, error)}))
        return 2
    if not args.no_write:
        pathlib.Path(state_file).write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: state[k] for k in ("spent_upper_bound_usd", "remaining_mandatory_caps_usd",
                                            "plan_C_worst_case_total_usd", "plan_C_fits_ceiling_at_worst_case",
                                            "headroom_usd", "fallback_B_extra_caps_usd", "fallback_B_fits_at_worst_case",
                                            "rejected_done_receipts")}, indent=1))
    for row in state["slots"]:
        print("%-4s %-8s counted $%-6s cap $%-6s %s" % (row["slot"], row["status"], row["counted_usd"], row["cap_usd"],
                                                        row.get("receipt_problems") or row["counted_basis"]))
    for sid, d in state["admission_preview"].items():
        print("money gate for %-4s -> %s %s" % (sid, d["decision"], "; ".join(d["reasons"])))
    return 1 if acct["rejected"] else 0


if __name__ == "__main__":
    sys.exit(main())
