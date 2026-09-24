"""HELM-REPAIR-CONTROLLED-1 study spend and admission gate. Label CLAUDE_BUILT_CLAUDE_CHECKED.

Answers Codex review `codex-0007` (defects 1-4) and the builder review of bb942461 (MAJOR 1-4, MINOR 1-4; see
REVIEW.md). Pure Python; reads files and git objects only; no AWS call; never reads or writes the meta1 ledger.

FROZEN IN THIS CODE (never taken from the slots file; the file must agree or exit 2):
  * the $60.00 ceiling, the owner's $30.00 stop before the 3rd training job, the $0.10 S3/transfer/retention allowance;
  * the SLOT DEFINITIONS: the slot set, every cap, cap basis, flag, seed, arm, precondition and note, and the WHOLE rows
    of the pre-gate DONE slots S1, S2, P1a. Their canonical digest must equal FROZEN_DEFINITIONS_SHA256. Changing any of
    them needs a reviewed code change that re-freezes the digest.

MUTABLE PER SLOT (not pre-gate): status, receipt, invalid_reason, admission. Moves only forward, checked against EVERY
committed version of STUDY_SLOTS.json (exit 2 on a violation):
  PLANNED -> RUNNING (only `--admit` sets it, with an admission record) -> DONE (receipt filled) -> INVALID.
  A committed RUNNING row keeps its admission; a committed DONE row keeps its receipt and admission and may only become
  INVALID; a committed INVALID row never changes; no committed RUNNING / DONE / INVALID row may disappear.

ACCOUNTING (exact decimals, every bound rounded UP to the cent):
  * DONE, receipt passes validation      -> the bound computed from that receipt;
  * DONE, receipt fails validation       -> max(cap, every cost figure the receipt itself shows); admissions refused
                                            until the slot is marked INVALID (the pins of a committed DONE row are frozen);
  * INVALID                              -> max(cap, every cost figure its receipt shows, if it has one), forever;
  * RUNNING                              -> its full cap;
  * PLANNED                              -> nothing spent; if mandatory, its cap is reserved.
  "Every cost figure": recorded cost + allowances, cost recomputed from the timestamps, the receipt's own deadline or
  instance-seconds limit, each at the highest price the receipt or the basis shows. So a job that broke its own cost
  basis is never counted below what it recorded (review MAJOR 4).
  Every cap must be at least the worst case its own basis computes (else exit 2; the old P1a $1.66 < $1.6639 guard).

A receipt is also rejected when any identity it claims (receipt sha256 or path, job id, instance id, launch or watch
record sha256 or path, provider record) is claimed by another RUNNING / DONE / INVALID slot; every admission is then
refused (review MAJOR 1). A slot admitted by this gate must, at DONE, show the admitted source commit (and bundle for
watched jobs), the slot's own model seed (training), and a launch time AFTER its admission time.

ADMISSION (`--admit SLOT --source <commit> [--bundle <sha256>]`): exit 0 only if ALL of these hold, else exit 1 with the
reasons; any input error exit 2. On exit 0 it WRITES the slot as RUNNING with an admission record, in the same step.
  * the slot is PLANNED; no slot is RUNNING (one machine at a time); no DONE receipt is rejected; no identity is shared;
    no receipt shows an unconfirmed cleanup (a machine or disk that may still exist: stop and report to the owner);
  * STUDY_SLOTS.json and study_spend.py equal HEAD (every earlier DONE is committed before the next machine starts);
  * spent upper bound + the slot's cap + the caps of every OTHER PLANNED mandatory slot (E1 included) <= $60.00;
  * the owner's stop is not triggered: spent upper bound > $30.00 while fewer than 3 training jobs have STARTED stops
    the study. Started = RUNNING, or DONE with an ACCEPTED pointer_finished receipt. An AWS capacity refusal, a rejected
    receipt or an INVALID slot never counts as started (review MAJOR 2);
  * training slots: all admissions of one arm use one source commit, and the two arms never share one.

Receipt kinds:
  pointer_finished          the typed-pointer launcher's result.json at a pinned git commit + sha256.
                            Bound = elapsed x rate ceiling + launcher ancillary + S3/transfer allowance.
  pointer_capacity_refusal  the same receipt for a launch AWS refused (InsufficientInstanceCapacity to RunInstances,
                            zero client retries, the LAST provider call). Overrides the launcher's own
                            compute_identity_uncertain flag; the override is printed; the rule itself is CLAUDE_PROPOSED
                            and awaits Codex or owner acceptance (see the slots file's open questions). Same formula.
  watched_machine           launch_record.json + watch_record.json at pinned paths + sha256. The machine must be one the
                            basis lists, at that machine's listed price. Bound = max(watcher cost, recomputed cost) +
                            evidence-collection allowance + S3/transfer allowance.
"""
import argparse
import copy
import datetime
import hashlib
import json
import math
import os
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
PROGRAM_FILE = pathlib.Path(__file__).resolve()
SCHEMA = "claude.helm-repair-controlled-1.study-slots/0.3"
STATUSES = ("PLANNED", "RUNNING", "DONE", "INVALID")
MUTABLE = ("status", "receipt", "invalid_reason", "admission")
PRE_GATE_DONE = ("S1", "S2", "P1a")     # done before this gate existed: their whole rows are frozen
ARMS = ("UNCHANGED", "REPAIRED")
POINTER_SCHEMA = "cas-graph-training-candidate-launch/1"
CENT, SIX = Decimal("0.01"), Decimal("0.000001")
SHA = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
MONEY = re.compile(r"^\d+\.\d{2}$")
DECIMAL = re.compile(r"^\d+(\.\d+)?$")
JOB_TIME = re.compile(r"-(\d{14})-")

# The owner's fixed numbers and the coordinator's allowance (review MAJOR 3): hard-coded, never read from the file.
CEILING_USD = Decimal("60.00")
STOP_USD = Decimal("30.00")
STOP_BEFORE_TRAINING_JOB = 3
ALLOWANCE_USD = Decimal("0.10")
# Canonical digest of STUDY_SLOTS.json without the mutable fields of non-pre-gate slots (definitions_digest()).
FROZEN_DEFINITIONS_SHA256 = "82e809500f14ad8988b3b45ad6a7265f0601a5791f13cb8ea5a4608771456764"
MONEY_BASIS = ("worst-case SPEND upper bound (machine + address + disk + launcher ancillary + allowances), NOT the "
               "training launcher's fixed $15.00 bookings; which count the owner's $60.00 applies to is an OPEN "
               "question (FLAG_FOR_HUMAN_REVIEW, see open_questions)")


class InputError(Exception):
    """A malformed or changed slots file, a cap below its basis, a history violation: exit 2."""


def up(x):
    """Round an upper bound UP to the cent."""
    return x.quantize(CENT, rounding=ROUND_CEILING)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


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


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


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
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def obj(value):
    return value if isinstance(value, dict) else {}


# ----------------------------------------------------------------------------------------------------- cap basis
def watched_machines(basis):
    machines = basis.get("machines")
    if not isinstance(machines, dict) or not machines:
        raise InputError("watched_machine basis needs machines: {name: price per hour}")
    return {name: decimal_str(price, "machines.%s" % name) for name, price in machines.items()}


def watched_per_hour(basis, price=None, disk_gb=None):
    price = max(watched_machines(basis).values()) if price is None else price
    address = decimal_str(basis.get("public_address_per_hour_usd"), "public_address_per_hour_usd")
    disk_gb = positive_int(basis.get("disk_gb_max"), "disk_gb_max") if disk_gb is None else disk_gb
    disk_rate = decimal_str(basis.get("disk_usd_per_gb_month"), "disk_usd_per_gb_month")
    hours = positive_int(basis.get("hours_per_month"), "hours_per_month")
    return price + address + Decimal(disk_gb) * disk_rate / hours


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
        machines = watched_machines(basis)
        top = max(machines, key=lambda m: machines[m])
        per_hour = watched_per_hour(basis)
        minutes = positive_int(basis.get("client_deadline_minutes_max"), "client_deadline_minutes_max")
        collection = decimal_str(basis.get("evidence_collection_allowance_usd"), "evidence_collection_allowance_usd")
        worst = per_hour * minutes / 60 + collection + allowance
        return worst, ("(%s %s, the dearest listed + %s address + %d GB x %s / %d disk) = %s/h x %d/60 h + $%s collection"
                       " + $%s S3/transfer = $%s") % (
            top, machines[top], basis["public_address_per_hour_usd"], basis["disk_gb_max"],
            basis["disk_usd_per_gb_month"], basis["hours_per_month"], per_hour.quantize(SIX), minutes, collection,
            allowance, worst.quantize(SIX))
    raise InputError("unknown cap_basis kind %r" % kind)


# ------------------------------------------------------------------------------------------------------- slots
def definitions_digest(doc):
    """Digest of everything except the mutable fields of non-pre-gate slots (review MAJOR 3)."""
    d = copy.deepcopy(doc)
    for s in d.get("slots") if isinstance(d.get("slots"), list) else []:
        if isinstance(s, dict) and s.get("id") not in PRE_GATE_DONE:
            for key in MUTABLE:
                s.pop(key, None)
    return sha256(canonical(d))


def load_slots(path, frozen=FROZEN_DEFINITIONS_SHA256):
    try:
        raw = pathlib.Path(path).read_bytes()
        doc = json.loads(raw)
    except (OSError, ValueError) as error:
        raise InputError("slots file unreadable: %s: %s" % (type(error).__name__, error))
    if not isinstance(doc, dict):
        raise InputError("slots file is not a JSON object")
    if doc.get("schema") != SCHEMA:
        raise InputError("slots file schema %r is not %r" % (doc.get("schema"), SCHEMA))
    stop, allowances = obj(doc.get("owner_stop")), obj(doc.get("allowances"))
    for what, value, fixed in (("ceiling_usd", doc.get("ceiling_usd"), CEILING_USD),
                               ("owner_stop.usd", stop.get("usd"), STOP_USD),
                               ("allowances.s3_transfer_per_job_usd", allowances.get("s3_transfer_per_job_usd"),
                                ALLOWANCE_USD)):
        if money(value, what) != fixed:
            raise InputError("FROZEN_CONSTANT_CHANGED: %s is %s in the file; the frozen value is %s" % (what, value, fixed))
    if stop.get("before_training_job_number") != STOP_BEFORE_TRAINING_JOB:
        raise InputError("FROZEN_CONSTANT_CHANGED: owner_stop.before_training_job_number is %r; the frozen value is %d"
                         % (stop.get("before_training_job_number"), STOP_BEFORE_TRAINING_JOB))
    slots = doc.get("slots")
    if not isinstance(slots, list) or not slots or not all(isinstance(s, dict) for s in slots):
        raise InputError("slots must be a non-empty list of objects")
    digest = definitions_digest(doc)
    if frozen is not None and digest != frozen:
        raise InputError("SLOT_DEFINITIONS_CHANGED: definitions digest %s is not the frozen %s. The slot set, caps, "
                         "bases, flags, seeds, arms, notes and the pre-gate DONE rows change only in a reviewed code "
                         "change" % (digest, frozen))
    info, seen = {}, set()
    for slot in slots:
        sid = slot.get("id")
        if not isinstance(sid, str) or not sid or sid in seen:
            raise InputError("slot id missing or repeated: %r" % sid)
        seen.add(sid)
        status = slot.get("status")
        if status not in STATUSES:
            raise InputError("%s: status %r not in %s" % (sid, status, STATUSES))
        for flag in ("mandatory", "counts_toward_training_stop"):
            if not isinstance(slot.get(flag), bool):
                raise InputError("%s: %s must be true or false" % (sid, flag))
        cap = money(slot.get("cap_usd"), "%s.cap_usd" % sid)
        basis = slot.get("cap_basis")
        if not isinstance(basis, dict):
            raise InputError("%s: cap_basis missing" % sid)
        worst, arithmetic = basis_worst_case(basis, ALLOWANCE_USD)
        if cap < up(worst):
            raise InputError("%s: cap $%s is below its own basis worst case $%s (%s)" % (sid, cap, up(worst), arithmetic))
        receipt = slot.get("receipt")
        if not isinstance(receipt, dict):
            raise InputError("%s: receipt spec missing" % sid)
        allowed = {"training_pointer": ("pointer_finished", "pointer_capacity_refusal"),
                   "watched_machine": ("watched_machine",)}[basis["kind"]]
        if receipt.get("kind") not in allowed:
            raise InputError("%s: receipt kind %r does not fit basis %r" % (sid, receipt.get("kind"), basis["kind"]))
        if basis["kind"] == "training_pointer" and sid not in PRE_GATE_DONE:
            training = obj(slot.get("training"))
            if training.get("arm") not in ARMS or not is_int(training.get("model_seed")):
                raise InputError("%s: a training slot needs training: {model_seed: int, arm: one of %s}" % (sid, ARMS))
        if status == "INVALID" and not (isinstance(slot.get("invalid_reason"), str) and slot["invalid_reason"].strip()):
            raise InputError("%s: an INVALID slot needs invalid_reason" % sid)
        if slot.get("admission") is not None and not isinstance(slot.get("admission"), dict):
            raise InputError("%s: admission must be an object" % sid)
        if status == "PLANNED" and slot.get("admission") is not None:
            raise InputError("%s: a PLANNED slot cannot carry an admission record" % sid)
        info[sid] = {"cap": cap, "worst": worst, "text": arithmetic}
    return {"doc": doc, "raw": raw, "sha256": sha256(raw), "digest": digest, "slots": slots, "info": info}


def check_history(doc, history):
    """Forward-only moves against every committed version of the slots file (review MAJOR 3)."""
    current = {s.get("id"): s for s in doc["slots"]}

    def same(a, b, keys):
        return all(canonical(a.get(k)) == canonical(b.get(k)) for k in keys)
    for commit, raw in history:
        try:
            old = json.loads(raw)
        except ValueError:
            raise InputError("committed slots file at %s is not JSON" % commit[:8])
        if not isinstance(old, dict) or not isinstance(old.get("slots"), list):
            raise InputError("committed slots file at %s has no slot list" % commit[:8])
        for o in old["slots"]:
            if not isinstance(o, dict):
                raise InputError("committed slots file at %s has a slot that is not an object" % commit[:8])
            sid, was = o.get("id"), o.get("status")
            if was not in ("RUNNING", "DONE", "INVALID"):
                continue
            cur = current.get(sid)
            if cur is None:
                raise InputError("HISTORY_VIOLATION: %s was %s at %s and has disappeared" % (sid, was, commit[:8]))
            now = cur.get("status")
            if was == "INVALID":
                ok = now == "INVALID" and same(o, cur, ("receipt", "invalid_reason", "admission"))
            elif was == "DONE":
                ok = now in ("DONE", "INVALID") and same(o, cur, ("receipt", "admission"))
            else:
                ok = now in ("RUNNING", "DONE", "INVALID") and same(o, cur, ("admission",))
            if not ok:
                raise InputError("HISTORY_VIOLATION: %s was %s at %s; now %s, or its committed receipt / admission / "
                                 "reason changed" % (sid, was, commit[:8], now))


# ---------------------------------------------------------------------------------------------------- receipts
class GitReader:
    """Reads blobs at a pinned commit of the repository that holds this folder."""

    def __init__(self, repo=HERE):
        self.repo = str(repo)

    def _run(self, args):
        return subprocess.run(["git", "-C", self.repo] + args, capture_output=True)

    def read(self, commit, path):
        done = self._run(["show", "%s:%s" % (commit, path)])
        if done.returncode != 0:
            raise FileNotFoundError("git show %s:%s failed" % (commit, path))
        return done.stdout

    def names(self, commit, directory):
        done = self._run(["ls-tree", "--full-tree", "--name-only", commit, directory.rstrip("/") + "/"])
        if done.returncode != 0:
            raise FileNotFoundError("git ls-tree %s %s failed" % (commit, directory))
        return [line.rsplit("/", 1)[-1] for line in done.stdout.decode("utf-8").splitlines() if line]

    def history(self, name):
        """(commit, bytes) of every committed version of HERE/name."""
        done = self._run(["log", "--format=%H", "--", name])
        if done.returncode != 0:
            raise OSError("git log of %s failed" % name)
        return [(c, self.read(c, "./" + name)) for c in done.stdout.decode("ascii").split()]

    def uncommitted(self, names):
        """Names (in HERE) whose working copy differs from HEAD, or that are untracked."""
        done = self._run(["status", "--porcelain", "--"] + list(names))
        if done.returncode != 0:
            raise OSError("git status failed")
        text = done.stdout.decode("utf-8")
        return [n for n in names if n in text]


def new_result():
    return {"bound": None, "text": "", "problems": [], "pins": {}, "keys": set(), "figures": [],
            "cleanup_unconfirmed": False}


def spec_complete(receipt, keys):
    return all(receipt.get(k) not in (None, "", {}) for k in keys)


def spec_keys(receipt):
    """Identity claims of a receipt spec; two RUNNING / DONE / INVALID slots may never share one (review MAJOR 1)."""
    keys = set()

    def add(name, value):
        if isinstance(value, str) and value:
            keys.add((name, value))
    expected = obj(receipt.get("expected"))
    if receipt.get("kind") in ("pointer_finished", "pointer_capacity_refusal"):
        add("receipt_sha256", receipt.get("sha256"))
        add("receipt_path", receipt.get("path"))
        add("job", expected.get("job"))
        add("instance_id", expected.get("instance_id"))
        last = obj(receipt.get("last_provider_record"))
        add("provider_record_sha256", last.get("sha256"))
        add("provider_record_path", last.get("path"))
    elif receipt.get("kind") == "watched_machine":
        for key in ("launch_record", "watch_record"):
            add(key + "_sha256", obj(receipt.get(key)).get("sha256"))
            add(key + "_path", obj(receipt.get(key)).get("path"))
        add("instance_id", expected.get("instance_id"))
    return keys


def read_pinned_git(git, commit, path, pinned, problems, label):
    if not (isinstance(commit, str) and COMMIT.match(commit) and isinstance(path, str)
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


def read_git_lenient(git, commit, path):
    """The receipt at its place WITHOUT the hash check: used only to count MORE, never less."""
    if not (isinstance(commit, str) and isinstance(path, str)):
        return None
    try:
        doc = json.loads(git.read(commit, path))
    except Exception:           # noqa: BLE001 -- lenient by design; the strict read already reported the problem
        return None
    return doc if isinstance(doc, dict) else None


def safe_path(root, text):
    """A receipt path inside ROOT, or None (review NOTE b: no drive letters, backslashes, '..' or absolute paths)."""
    if not isinstance(text, str) or not text or "\\" in text or ":" in text:
        return None
    rel = pathlib.PurePosixPath(text)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    base = pathlib.Path(root).resolve()
    path = (base / rel).resolve()
    return path if base == path or base in path.parents else None


def read_pinned_file(root, spec, problems, label):
    if not isinstance(spec, dict) or not isinstance(spec.get("path"), str) or not SHA.match(str(spec.get("sha256"))):
        problems.append("%s_PIN_MALFORMED" % label)
        return None
    path = safe_path(root, spec["path"])
    if path is None:
        problems.append("%s_PATH_ESCAPES_ROOT" % label)
        return None
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


def read_file_lenient(root, spec):
    path = safe_path(root, obj(spec).get("path"))
    if path is None or not path.is_file():
        return None
    try:
        doc = json.loads(path.read_bytes())
    except (OSError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def bind_admission(slot, res, source, launched_at, seed=None, bundle=None, bundle_required=False):
    """A slot admitted by this gate must show what it was admitted with (review MAJOR 1)."""
    if slot["id"] in PRE_GATE_DONE:
        return
    a = slot.get("admission")
    if not isinstance(a, dict):
        res["problems"].append("NO_ADMISSION_RECORD")
        return
    admitted = utc(a.get("admitted_utc"))
    if admitted is None or a.get("slot") != slot["id"]:
        res["problems"].append("ADMISSION_RECORD_MALFORMED_OR_OF_ANOTHER_SLOT")
        return
    if source != a.get("source_sha"):
        res["problems"].append("SOURCE_NOT_THE_ADMITTED_SOURCE:%r vs admitted %r" % (source, a.get("source_sha")))
    if bundle_required and bundle != a.get("bundle_sha256"):
        res["problems"].append("BUNDLE_NOT_THE_ADMITTED_BUNDLE:%r vs admitted %r" % (bundle, a.get("bundle_sha256")))
    if launched_at is None or launched_at < admitted:
        res["problems"].append("LAUNCH_NOT_AFTER_ADMISSION:%s vs admitted %s" % (launched_at, a.get("admitted_utc")))
    training = obj(slot.get("training"))
    if training:
        if seed != training.get("model_seed") or a.get("model_seed") != training.get("model_seed"):
            res["problems"].append("SEED_NOT_THE_SLOT_SEED:receipt %r, admitted %r, slot %r" % (
                seed, a.get("model_seed"), training.get("model_seed")))
        if a.get("arm") != training.get("arm"):
            res["problems"].append("ARM_NOT_THE_SLOT_ARM:%r" % a.get("arm"))


def pointer_figures(d, basis, allowance):
    """Every cost figure a training receipt shows, at the highest rate it or the basis shows (review MAJOR 4)."""
    pre = obj(d.get("preflight"))
    observed = pre.get("observed_on_demand_hourly_usd") if isinstance(pre.get("observed_on_demand_hourly_usd"), list) else []
    rates = [Decimal(basis["rate_ceiling_usd_per_hour"])] + [
        Decimal(x) for x in [pre.get("rate_ceiling_usd")] + observed if isinstance(x, str) and DECIMAL.match(x)]
    rate, ancillary, out = max(rates), Decimal(basis["launcher_ancillary_usd"]), []
    elapsed = number(d.get("elapsed_seconds"))
    if elapsed is not None and elapsed > 0:
        out.append((elapsed / 3600 * rate + ancillary + allowance,
                    "receipt elapsed %s s x $%s/h + $%s + $%s" % (elapsed, rate, ancillary, allowance)))
    seconds_max = obj(d.get("authority")).get("instance_seconds_max")
    if is_int(seconds_max) and seconds_max > 0:
        out.append((Decimal(seconds_max) / 3600 * rate + ancillary + allowance,
                    "receipt's own instance_seconds_max %d s x $%s/h + $%s + $%s" % (seconds_max, rate, ancillary, allowance)))
    return out


def pointer_common(d, expected, basis, problems):
    """Identity and rate checks shared by both pointer kinds. Returns (elapsed, rate)."""
    authority, preflight = obj(d.get("authority")), obj(d.get("preflight"))
    if d.get("schema") != POINTER_SCHEMA:
        problems.append("SCHEMA:%r" % d.get("schema"))
    for where, value in (("job", d.get("job")), ("authority.job", authority.get("job")),
                         ("request.job", obj(d.get("request")).get("job"))):
        if value != expected.get("job"):
            problems.append("JOB_MISMATCH:%s=%r" % (where, value))
    if authority.get("source_sha") != expected.get("source_sha"):
        problems.append("SOURCE_MISMATCH:%r" % authority.get("source_sha"))
    for where, value in (("authority.instance_type", authority.get("instance_type")),
                         ("preflight.instance_type", preflight.get("instance_type"))):
        if value != expected.get("instance_type") or value != basis.get("instance_type"):
            problems.append("INSTANCE_TYPE_MISMATCH:%s=%r" % (where, value))
    seconds_max = authority.get("instance_seconds_max")
    if not is_int(seconds_max) or seconds_max > basis["instance_seconds_max"]:
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
    elif elapsed > basis["instance_seconds_max"]:
        problems.append("ELAPSED_OVER_BASIS:%s" % elapsed)
    return elapsed, Decimal(rate)


def pointer_admission(slot, d, expected, res):
    job = expected.get("job") if isinstance(expected.get("job"), str) else ""
    m = JOB_TIME.search(job)
    launched = None
    if m:
        try:
            launched = datetime.datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            launched = None
    seed = obj(obj(obj(d.get("authority")).get("worker_config")).get("design")).get("model_seed")
    bind_admission(slot, res, expected.get("source_sha"), launched, seed=seed)


def validate_pointer(slot, git, allowance, refusal):
    receipt, basis, res = slot["receipt"], slot["cap_basis"], new_result()
    need = ("git_commit", "path", "sha256", "expected") + (("last_provider_record",) if refusal else ())
    need_expected = ("job", "source_sha", "instance_type") + (() if refusal else ("instance_id",))
    if not spec_complete(receipt, need) or not spec_complete(obj(receipt["expected"]), need_expected):
        res["problems"].append("RECEIPT_SPEC_INCOMPLETE")
        return res
    expected, problems = receipt["expected"], res["problems"]
    d = read_pinned_git(git, receipt["git_commit"], receipt["path"], receipt["sha256"], problems, "RECEIPT")
    lenient = d if d is not None else read_git_lenient(git, receipt["git_commit"], receipt["path"])
    if lenient is not None:
        res["figures"] = pointer_figures(lenient, basis, allowance)
        for name, value in (("job", lenient.get("job")), ("instance_id", obj(lenient.get("launch")).get("instance_id"))):
            if isinstance(value, str) and value:
                res["keys"].add((name, value))
    if d is None:
        return res
    elapsed, rate = pointer_common(d, expected, basis, problems)
    cleanup = obj(d.get("cleanup"))
    if not refusal:
        iid = expected["instance_id"]
        if obj(d.get("launch")).get("instance_id") != iid:
            problems.append("INSTANCE_MISMATCH:launch.instance_id=%r" % obj(d.get("launch")).get("instance_id"))
        if cleanup.get("instance_ids") != [iid] or cleanup.get("instances") != {iid: "CONFIRMED_TERMINATED"}:
            problems.append("CLEANUP_NOT_THIS_ONE_INSTANCE_TERMINATED:%r" % cleanup.get("instances"))
        if cleanup.get("complete") is not True or cleanup.get("compute_identity_uncertain") is not False:
            problems.append("CLEANUP_INCOMPLETE_OR_IDENTITY_UNCERTAIN")
        if cleanup.get("failures") != [] or cleanup.get("instances_termination_pending") != []:
            problems.append("CLEANUP_FAILURES_OR_PENDING:%r" % cleanup.get("failures"))
        if obj(d.get("stages")).get("compute_cleanup") != "COMPLETE":
            problems.append("STAGE_COMPUTE_CLEANUP:%r" % obj(d.get("stages")).get("compute_cleanup"))
        instances = cleanup.get("instances") if isinstance(cleanup.get("instances"), dict) else {}
        res["cleanup_unconfirmed"] = (cleanup.get("complete") is not True or not instances
                                      or any(v != "CONFIRMED_TERMINATED" for v in instances.values())
                                      or cleanup.get("instances_termination_pending") != [])
    else:
        validate_refusal_specifics(d, receipt, expected, git, problems)
        named = (d.get("launch") is not None or cleanup.get("instance_ids") not in ([],)
                 or cleanup.get("instances") not in ({},) or cleanup.get("instances_termination_pending") not in ([],))
        proof_failed = any(p.startswith(x) for p in problems for x in (
            "NOT_A_FAILED_LAUNCH", "NOT_AN_AWS_CAPACITY_REFUSAL", "A_PROVIDER_CALL_FOLLOWS", "LAST_PROVIDER"))
        res["cleanup_unconfirmed"] = named or (cleanup.get("compute_identity_uncertain") is not False and proof_failed)
    pointer_admission(slot, d, expected, res)
    if problems:
        return res
    ancillary = Decimal(basis["launcher_ancillary_usd"])
    exact = elapsed / 3600 * rate + ancillary + allowance
    res["bound"] = up(exact)
    res["text"] = "elapsed %s s x $%s/h + $%s launcher ancillary + $%s S3/transfer = $%s%s" % (
        elapsed, rate, ancillary, allowance, exact.quantize(SIX), " (no machine ran)" if refusal else "")
    res["pins"] = {"receipt_sha256": receipt["sha256"]}
    if refusal:
        res["pins"]["override"] = (
            "launcher flag compute_identity_uncertain=%r overridden by the capacity-refusal rule: the last provider call "
            "is RunInstances refused by AWS (InsufficientInstanceCapacity, zero client retries); no machine was created. "
            "Rule status: CLAUDE_PROPOSED, awaiting Codex or owner acceptance" % cleanup.get("compute_identity_uncertain"))
    return res


def validate_refusal_specifics(d, receipt, expected, git, problems):
    cleanup, outcome, last = obj(d.get("cleanup")), obj(d.get("outcome")), obj(receipt.get("last_provider_record"))
    if d.get("status") != "AWS_CANDIDATE_FAILED" or obj(d.get("stages")).get("execution") != "FAILED":
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
    if p is None:
        return
    err = p.get("error")
    if not (p.get("operation") == "run_instances" and p.get("state") == "FAILED" and p.get("job") == expected["job"]
            and isinstance(err, str) and "(InsufficientInstanceCapacity)" in err):
        problems.append("LAST_PROVIDER_NOT_THE_CAPACITY_REFUSAL")
    directory, name = last["path"].rsplit("/", 1) if "/" in last["path"] else ("", last["path"])
    try:
        numbers = [int(n[9:13]) for n in git.names(receipt["git_commit"], directory)
                   if re.match(r"^provider_\d{4}\.json$", n)]
    except (OSError, FileNotFoundError):
        numbers = []
    if not re.match(r"^provider_\d{4}\.json$", name) or not numbers or max(numbers) != int(name[9:13]):
        problems.append("A_PROVIDER_CALL_FOLLOWS_THE_REFUSAL_OR_LIST_UNREADABLE")


def watched_figures(launch, watch, basis, allowance):
    """Every cost figure a watched job's records show, at the highest price and disk they or the basis show."""
    price = max(watched_machines(basis).values())
    recorded = number(obj(launch.get("approved")).get("price_per_hour_usd"))
    if recorded is not None and recorded > price:
        price = recorded
    disk = basis["disk_gb_max"]
    if is_int(launch.get("root_volume_gb")) and launch["root_volume_gb"] > disk:
        disk = launch["root_volume_gb"]
    per_hour = watched_per_hour(basis, price=price, disk_gb=disk)
    extra = Decimal(basis["evidence_collection_allowance_usd"]) + allowance
    out = []
    cost = number(watch.get("cost_upper_bound_usd"))
    if cost is not None and cost >= 0:
        out.append((cost + extra, "watcher's recorded $%s + $%s allowances" % (cost, extra)))
    start, end = utc(watch.get("launched_utc")) or utc(launch.get("launched_utc")), utc(watch.get("watch_ended_utc"))
    if start is not None and end is not None and end > start:
        seconds = Decimal(int((end - start).total_seconds()))
        out.append((seconds / 3600 * per_hour + extra, "recomputed %s s x $%s/h + $%s" % (seconds, per_hour.quantize(SIX), extra)))
    minutes = number(watch.get("minutes_from_launch_to_watch_end"))
    if minutes is not None and minutes > 0:
        out.append((minutes / 60 * per_hour + extra, "watcher's %s min x $%s/h + $%s" % (minutes, per_hour.quantize(SIX), extra)))
    deadline = launch.get("client_deadline_minutes")
    if is_int(deadline) and deadline > 0:
        out.append((per_hour * deadline / 60 + extra, "the job's own %d-min deadline x $%s/h + $%s" % (
            deadline, per_hour.quantize(SIX), extra)))
    return out


def validate_watched(slot, info, root, allowance):
    receipt, basis, res = slot["receipt"], slot["cap_basis"], new_result()
    if not spec_complete(receipt, ("launch_record", "watch_record", "launch_schema", "watch_schema", "expected")) or \
            not spec_complete(obj(receipt["expected"]), ("instance_id", "launched_utc", "source_commit", "bundle_sha256")):
        res["problems"].append("RECEIPT_SPEC_INCOMPLETE")
        return res
    expected, problems = receipt["expected"], res["problems"]
    launch = read_pinned_file(root, receipt["launch_record"], problems, "LAUNCH_RECORD")
    watch = read_pinned_file(root, receipt["watch_record"], problems, "WATCH_RECORD")
    lenient_launch = launch if launch is not None else read_file_lenient(root, receipt["launch_record"])
    lenient_watch = watch if watch is not None else read_file_lenient(root, receipt["watch_record"])
    res["figures"] = watched_figures(lenient_launch or {}, lenient_watch or {}, basis, allowance)
    for doc in (lenient_launch or {}, lenient_watch or {}):
        if isinstance(doc.get("instance_id"), str) and doc["instance_id"]:
            res["keys"].add(("instance_id", doc["instance_id"]))
    if watch is not None:
        res["cleanup_unconfirmed"] = (watch.get("terminated_confirmed") is not True
                                      or watch.get("final_state") not in ("terminated", "gone")
                                      or watch.get("volumes_of_this_job_remaining") != [])
    if launch is None or watch is None:
        return res
    approved, machines = obj(launch.get("approved")), watched_machines(basis)
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
    if obj(launch.get("identity")).get("source_commit") != expected["source_commit"]:
        problems.append("SOURCE_MISMATCH:%r" % obj(launch.get("identity")).get("source_commit"))
    if obj(launch.get("bundle")).get("sha256") != expected["bundle_sha256"]:
        problems.append("BUNDLE_MISMATCH:%r" % obj(launch.get("bundle")).get("sha256"))
    machine = approved.get("machine")
    if machine not in machines:
        problems.append("MACHINE_NOT_IN_BASIS:%r not in %s" % (machine, sorted(machines)))
    price = number(approved.get("price_per_hour_usd"))
    if price is None or machine not in machines or price != machines[machine]:
        problems.append("PRICE_NOT_THE_BASIS_PRICE_OF_THIS_MACHINE:%r" % approved.get("price_per_hour_usd"))
    disk, deadline = launch.get("root_volume_gb"), launch.get("client_deadline_minutes")
    if not is_int(disk) or not 0 < disk <= basis["disk_gb_max"]:
        problems.append("DISK_OVER_BASIS:%r" % disk)
    if not is_int(deadline) or not 0 < deadline <= basis["client_deadline_minutes_max"]:
        problems.append("DEADLINE_OVER_BASIS:%r" % deadline)
    ceiling = number(approved.get("dollar_ceiling"))
    if ceiling is None or ceiling != info["cap"]:
        problems.append("LAUNCH_CEILING_NOT_SLOT_CAP:%r" % approved.get("dollar_ceiling"))
    if res["cleanup_unconfirmed"]:
        problems.append("NOT_CONFIRMED_TERMINATED_OR_VOLUMES_LEFT_OR_UNKNOWN:%r %r" % (
            watch.get("final_state"), watch.get("volumes_of_this_job_remaining")))
    cost = number(watch.get("cost_upper_bound_usd"))
    if cost is None or cost < 0 or cost > info["cap"]:
        problems.append("WATCH_COST_INVALID:%r" % watch.get("cost_upper_bound_usd"))
    minutes = number(watch.get("minutes_from_launch_to_watch_end"))
    start, end = utc(watch.get("launched_utc")), utc(watch.get("watch_ended_utc"))
    if minutes is None or minutes <= 0 or start is None or end is None or end <= start:
        problems.append("WATCH_TIMES_INVALID")
    bind_admission(slot, res, expected["source_commit"], utc(expected["launched_utc"]),
                   bundle=expected["bundle_sha256"], bundle_required=True)
    if problems:
        return res
    seconds = Decimal(int((end - start).total_seconds()))
    if abs(minutes - seconds / 60) > Decimal("0.1"):
        problems.append("WATCH_MINUTES_DISAGREE_WITH_TIMESTAMPS:%s vs %s s" % (minutes, seconds))
    per_hour = watched_per_hour(basis, price=price, disk_gb=disk)
    recomputed = seconds / 3600 * per_hour
    if cost < recomputed - Decimal("0.0001"):
        problems.append("WATCH_COST_BELOW_RECOMPUTED:%s < %s" % (cost, recomputed))
    if problems:
        return res
    collection = Decimal(basis["evidence_collection_allowance_usd"])
    exact = max(cost, recomputed) + collection + allowance
    res["bound"] = up(exact)
    res["text"] = ("max(watcher $%s, recomputed %s s x $%s/h on %s = $%s) + $%s collection + $%s S3/transfer = $%s" % (
        cost, seconds, per_hour.quantize(SIX), machine, recomputed.quantize(SIX), collection, allowance, exact))
    res["pins"] = {"launch_record_sha256": receipt["launch_record"]["sha256"],
                   "watch_record_sha256": receipt["watch_record"]["sha256"]}
    return res


def validate_receipt(slot, info, root, git):
    kind = slot["receipt"]["kind"]
    if kind == "pointer_finished":
        return validate_pointer(slot, git, ALLOWANCE_USD, refusal=False)
    if kind == "pointer_capacity_refusal":
        return validate_pointer(slot, git, ALLOWANCE_USD, refusal=True)
    return validate_watched(slot, info, root, ALLOWANCE_USD)


def receipt_has_pins(receipt):
    if receipt.get("kind") == "watched_machine":
        return isinstance(receipt.get("launch_record"), dict) or isinstance(receipt.get("watch_record"), dict)
    return isinstance(receipt.get("path"), str) and bool(receipt.get("path"))


def counted_at_least_cap(cap, res):
    """max(cap, every cost figure the receipt shows), rounded up (review MAJOR 4)."""
    best, text = cap, "cap $%s" % cap
    for value, what in (res or {}).get("figures", []):
        if up(value) > best:
            best, text = up(value), "%s = $%s" % (what, value.quantize(SIX))
    return best, text


# ------------------------------------------------------------------------------------------ accounting + admission
def account(loaded, root, git):
    slots, info = loaded["slots"], loaded["info"]
    results = {}
    for s in slots:
        if s["status"] == "DONE" or (s["status"] == "INVALID" and receipt_has_pins(s["receipt"])):
            results[s["id"]] = validate_receipt(s, info[s["id"]], root, git)
    owners = {}
    for s in slots:
        if s["status"] in ("RUNNING", "DONE", "INVALID"):
            for key in spec_keys(s["receipt"]) | results.get(s["id"], {}).get("keys", set()):
                owners.setdefault(key, set()).add(s["id"])
    shared = {"%s=%s" % key: sorted(ids) for key, ids in sorted(owners.items()) if len(ids) > 1}
    for label, ids in shared.items():
        for sid in ids:
            if sid in results:
                results[sid]["problems"].append("RECEIPT_SHARED:%s:with=%s" % (label, ",".join(i for i in ids if i != sid)))
    rows, spent, rejected, unconfirmed = [], Decimal("0"), [], []
    for slot in slots:
        sid, status, cap = slot["id"], slot["status"], info[slot["id"]]["cap"]
        res = results.get(sid)
        row = {"slot": sid, "what": slot.get("what"), "status": status, "mandatory": slot["mandatory"],
               "cap_usd": str(cap), "basis_worst_case_usd": str(up(info[sid]["worst"])),
               "basis_arithmetic": info[sid]["text"]}
        if status == "DONE" and not res["problems"]:
            row.update(receipt="ACCEPTED", counted_usd=str(res["bound"]), counted_basis=res["text"], receipt_pins=res["pins"])
        elif status == "DONE":
            rejected.append(sid)
            counted, why = counted_at_least_cap(cap, res)
            row.update(receipt="REJECTED", receipt_problems=res["problems"], counted_usd=str(counted),
                       counted_basis="receipt rejected: the larger of the cap and every cost figure it shows: " + why)
        elif status == "INVALID":
            counted, why = counted_at_least_cap(cap, res)
            row.update(receipt="INVALID", counted_usd=str(counted),
                       counted_basis="INVALID (%s): the larger of the cap and every cost figure its receipt shows: %s" % (
                           slot["invalid_reason"], why))
            if res and res["problems"]:
                row["receipt_problems"] = res["problems"]
        elif status == "RUNNING":
            row.update(receipt="NOT_FINAL", counted_usd=str(cap), counted_basis="RUNNING: full cap",
                       admission=slot.get("admission") or "MISSING: set RUNNING by hand, not by --admit")
        else:
            row.update(receipt="NOT_APPLICABLE", counted_usd="0.00",
                       counted_basis="PLANNED: nothing spent; cap %s" % ("reserved" if slot["mandatory"] else "not reserved (optional)"))
        if res and res["cleanup_unconfirmed"]:
            unconfirmed.append(sid)
            row["cleanup"] = "UNCONFIRMED: a machine or disk of this slot may still exist; stop and report to the owner"
        for key in ("scope", "runtime_bound", "cleanup_bound", "timing_feasibility", "training"):
            if key in slot:
                row[key] = slot[key]
        row["preconditions_outside_money_gate"] = preconditions(slot)
        spent += Decimal(row["counted_usd"])
        rows.append(row)
    planned_mandatory = [s for s in slots if s["status"] == "PLANNED" and s["mandatory"]]
    reserve = sum((info[s["id"]]["cap"] for s in planned_mandatory), Decimal("0"))
    started = [s["id"] for s in slots if s["counts_toward_training_stop"] and (
        s["status"] == "RUNNING" or (s["status"] == "DONE" and s["receipt"]["kind"] == "pointer_finished"
                                     and s["id"] not in rejected))]
    return {"rows": rows, "spent": spent, "rejected": rejected, "shared": shared, "unconfirmed": unconfirmed,
            "reserve": reserve, "planned_mandatory": [s["id"] for s in planned_mandatory],
            "optional": [s for s in slots if s["status"] == "PLANNED" and not s["mandatory"]],
            "running": [s["id"] for s in slots if s["status"] == "RUNNING"], "training_started": started}


def preconditions(slot):
    listed = slot.get("preconditions_outside_money_gate")
    return listed if listed else "NOT ASSESSED: no precondition list for this slot; do not read ADMIT as ready"


def admit(slot_id, loaded, acct, source=None, bundle=None, preview=False, uncommitted=()):
    slots, info = {s["id"]: s for s in loaded["slots"]}, loaded["info"]
    if slot_id not in slots:
        raise InputError("no slot named %r" % slot_id)
    slot, reasons = slots[slot_id], []
    cap, kind = info[slot_id]["cap"], slot["cap_basis"]["kind"]
    if not preview:
        if not (isinstance(source, str) and COMMIT.match(source)):
            raise InputError("--source <the 40-hex source commit this slot will launch> is required")
        if kind == "watched_machine" and not (isinstance(bundle, str) and SHA.match(bundle)):
            raise InputError("--bundle <the 64-hex sha256 of the reviewed bundle> is required for a watched slot")
        if kind != "watched_machine" and bundle is not None:
            raise InputError("--bundle applies to watched slots only")
    if acct["rejected"]:
        reasons.append("DONE_RECEIPT_REJECTED:%s" % ",".join(acct["rejected"]))
    if acct["shared"]:
        reasons.append("RECEIPT_SHARED:%s" % "; ".join("%s by %s" % (k, ",".join(v)) for k, v in acct["shared"].items()))
    if acct["unconfirmed"]:
        reasons.append("CLEANUP_UNCONFIRMED_STOP_AND_REPORT:%s" % ",".join(acct["unconfirmed"]))
    if slot["status"] != "PLANNED":
        reasons.append("SLOT_NOT_PLANNED:%s" % slot["status"])
    if acct["running"]:
        reasons.append("ONE_MACHINE_AT_A_TIME:RUNNING=%s" % ",".join(acct["running"]))
    if uncommitted:
        reasons.append("UNCOMMITTED_CHANGES:%s: commit them first, so every DONE receipt is in git history before the "
                       "next machine starts" % ",".join(uncommitted))
    if not preview and kind == "training_pointer" and obj(slot.get("training")).get("arm"):
        arm = slot["training"]["arm"]
        for other in loaded["slots"]:
            a = obj(other.get("admission"))
            if other["id"] == slot_id or not a.get("source_sha") or "training" not in other:
                continue
            if other["training"]["arm"] == arm and a["source_sha"] != source:
                reasons.append("ARM_SOURCE_CONFLICT:%s (%s) was admitted with %s" % (other["id"], arm, a["source_sha"]))
            if other["training"]["arm"] != arm and a["source_sha"] == source:
                reasons.append("ARM_SOURCE_CONFLICT:%s is the other arm and was admitted with this source" % other["id"])
    others = acct["reserve"] - (cap if slot["status"] == "PLANNED" and slot["mandatory"] else 0)
    total = acct["spent"] + cap + others
    arithmetic = "spent upper bound $%s + %s cap $%s + other mandatory caps $%s (%s) = $%s vs ceiling $%s" % (
        acct["spent"], slot_id, cap, others,
        ",".join(i for i in acct["planned_mandatory"] if i != slot_id) or "none", total, CEILING_USD)
    if total > CEILING_USD:
        reasons.append("OVER_CEILING:$%s > $%s" % (total, CEILING_USD))
    stop = len(acct["training_started"]) < STOP_BEFORE_TRAINING_JOB and acct["spent"] > STOP_USD
    stop_text = "spent upper bound $%s %s $%s with %d of %d training jobs started (%s)" % (
        acct["spent"], ">" if acct["spent"] > STOP_USD else "<=", STOP_USD,
        len(acct["training_started"]), STOP_BEFORE_TRAINING_JOB, ",".join(acct["training_started"]) or "none")
    if stop:
        reasons.append("OWNER_STOP_TRIGGERED:stop and report:%s" % stop_text)
    return {"slot": slot_id, "decision": "REFUSE" if reasons else "ADMIT", "reasons": reasons,
            "admission_arithmetic": arithmetic, "total_usd": str(total),
            "owner_stop": ("TRIGGERED: " if stop else "not triggered: ") + stop_text,
            "started_counts": "RUNNING, or DONE with an ACCEPTED pointer_finished receipt; never a capacity refusal, a "
                              "rejected receipt or an INVALID slot",
            "money_basis": MONEY_BASIS,
            "gate_scope": "money ceiling, owner stop, one machine at a time, committed state and receipt validity ONLY; "
                          "technical readiness (reviews, builds) is a separate admission and is NOT checked here",
            "preconditions_outside_money_gate": preconditions(slot)}


def write_admission(slots_file, loaded, slot_id, record, frozen):
    """Set the slot RUNNING with its admission record, in one atomic write (review MINOR: --admit leaves a record)."""
    path = pathlib.Path(slots_file)
    if sha256(path.read_bytes()) != loaded["sha256"]:
        raise InputError("the slots file changed while the decision was made; nothing was written")
    doc = json.loads(loaded["raw"])
    for s in doc["slots"]:
        if s["id"] == slot_id:
            s["status"], s["admission"] = "RUNNING", record
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    os.replace(partial, path)
    again = load_slots(path, frozen)
    if again["digest"] != loaded["digest"]:
        raise InputError("definitions changed while writing the admission")
    return again["sha256"]


def state_document(loaded, acct):
    spent, doc = acct["spent"], loaded["doc"]
    plan_total = spent + acct["reserve"]
    fallback = sum((loaded["info"][s["id"]]["cap"] for s in acct["optional"]), Decimal("0"))
    sensitivity = {r["slot"]: str(plan_total - Decimal(r["counted_usd"]) + max(Decimal(r["cap_usd"]), Decimal(r["counted_usd"])))
                   for r in acct["rows"] if r["status"] == "DONE"}
    previews = {s["id"]: admit(s["id"], loaded, acct, preview=True) for s in loaded["slots"] if s["status"] == "PLANNED"}
    return {"schema": "claude.helm-repair-controlled-1.study-spend/0.3", "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
            "inputs": {"slots_file": "STUDY_SLOTS.json", "slots_file_sha256": loaded["sha256"],
                       "definitions_sha256": loaded["digest"]},
            "frozen_in_code": {"ceiling_usd": str(CEILING_USD), "owner_stop_usd": str(STOP_USD),
                               "owner_stop_before_training_job": STOP_BEFORE_TRAINING_JOB,
                               "s3_transfer_allowance_per_job_usd": str(ALLOWANCE_USD),
                               "definitions_sha256": FROZEN_DEFINITIONS_SHA256, "pre_gate_done_rows": list(PRE_GATE_DONE)},
            "money_basis": MONEY_BASIS,
            "spent_upper_bound_usd": str(spent), "rejected_done_receipts": acct["rejected"],
            "shared_receipt_identities": acct["shared"], "cleanup_unconfirmed": acct["unconfirmed"],
            "training_jobs_started": acct["training_started"],
            "slots": acct["rows"],
            "remaining_mandatory_slots": acct["planned_mandatory"],
            "remaining_mandatory_caps_usd": str(acct["reserve"]),
            "plan_C_worst_case_total_usd": str(plan_total), "plan_C_fits_ceiling_at_worst_case": plan_total <= CEILING_USD,
            "headroom_usd": str(CEILING_USD - plan_total),
            "fallback_B_slots": [s["id"] for s in acct["optional"]], "fallback_B_extra_caps_usd": str(fallback),
            "fallback_B_fits_at_worst_case": plan_total + fallback <= CEILING_USD,
            "plan_C_total_if_this_DONE_slot_were_counted_at_its_full_cap_usd": sensitivity,
            "money_gate_preview_not_an_admission": previews,
            "open_questions": doc.get("open_questions_for_owner_or_codex"),
            "rules": {"admission": "slot PLANNED; nothing RUNNING; no DONE receipt rejected; no receipt identity shared; "
                                   "no unconfirmed cleanup; slots file and program committed; spent upper bound + next "
                                   "cap + every other PLANNED mandatory cap (E1 included) <= ceiling; owner stop not "
                                   "triggered; one source per training arm. ADMIT writes the slot RUNNING with its "
                                   "admission record",
                      "owner_stop": doc["owner_stop"]["rule"],
                      "rounding": "every bound rounded UP to the cent; exact decimals, no floats"},
            "meta1_ledger": "not read or written by this program"}


def main(argv=None, git=None, root=ROOT, slots_file=SLOTS_FILE, state_file=STATE_FILE,
         frozen=FROZEN_DEFINITIONS_SHA256, program_file=PROGRAM_FILE, now=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--admit", metavar="SLOT", help="decide one admission; exit 0 ADMIT (slot written RUNNING), "
                                                        "1 REFUSE, 2 error")
    parser.add_argument("--source", metavar="COMMIT", help="with --admit: the 40-hex source commit the slot launches")
    parser.add_argument("--bundle", metavar="SHA256", help="with --admit of a watched slot: the reviewed bundle sha256")
    parser.add_argument("--no-write", action="store_true", help="report mode: do not write STUDY_SPEND_STATE.json")
    args = parser.parse_args(argv)
    git = git or GitReader()
    try:
        loaded = load_slots(slots_file, frozen)
        check_history(loaded["doc"], git.history(pathlib.Path(slots_file).name))
        acct = account(loaded, root, git)
        if args.admit:
            names = [pathlib.Path(slots_file).name, pathlib.Path(program_file).name]
            decision = admit(args.admit, loaded, acct, source=args.source, bundle=args.bundle,
                             uncommitted=git.uncommitted(names))
            decision.update(spent_upper_bound_usd=str(acct["spent"]), slots_file_sha256=loaded["sha256"],
                            definitions_sha256=loaded["digest"],
                            receipts={r["slot"]: r.get("receipt_pins") or r.get("receipt_problems")
                                      for r in acct["rows"] if r["status"] == "DONE"},
                            open_questions=loaded["doc"].get("open_questions_for_owner_or_codex"))
            if decision["decision"] == "ADMIT":
                slot = next(s for s in loaded["slots"] if s["id"] == args.admit)
                record = {"slot": args.admit, "gate": "study_spend.py --admit",
                          "admitted_utc": now or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                          "slots_sha256_before": loaded["sha256"], "definitions_sha256": loaded["digest"],
                          "program_sha256": sha256(pathlib.Path(program_file).read_bytes()),
                          "source_sha": args.source, "spent_upper_bound_usd": str(acct["spent"]),
                          "admission_arithmetic": decision["admission_arithmetic"]}
                if slot["cap_basis"]["kind"] == "watched_machine":
                    record["bundle_sha256"] = args.bundle
                else:
                    record.update(model_seed=slot["training"]["model_seed"], arm=slot["training"]["arm"])
                decision["slots_file_sha256_after"] = write_admission(slots_file, loaded, args.admit, record, frozen)
                decision["admission_record"] = record
                decision["recorded"] = ("slot set RUNNING in STUDY_SLOTS.json with this admission record; commit and "
                                        "push it before the launch")
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
                                            "rejected_done_receipts", "shared_receipt_identities", "cleanup_unconfirmed",
                                            "training_jobs_started")}, indent=1))
    for row in state["slots"]:
        print("%-4s %-8s counted $%-6s cap $%-6s %s" % (row["slot"], row["status"], row["counted_usd"], row["cap_usd"],
                                                        row.get("receipt_problems") or row["counted_basis"]))
    for sid, d in state["money_gate_preview_not_an_admission"].items():
        print("money gate preview for %-4s -> %s %s" % (sid, d["decision"], "; ".join(d["reasons"])))
    return 1 if (acct["rejected"] or acct["shared"] or acct["unconfirmed"]) else 0


if __name__ == "__main__":
    sys.exit(main())
