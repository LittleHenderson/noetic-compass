"""HELM-REPAIR-CONTROLLED-1 study spend and admission gate. Label CLAUDE_BUILT_CLAUDE_CHECKED.

Answers Codex review `codex-0007` (defects 1-4), the builder review of bb942461 (MAJOR 1-4, MINOR 1-4), the round-2
verification of d89721b4 (MAJOR-A, MINOR-B; see REVIEW.md "Round 2"), the round-3 verification of 269d13c8
(MAJOR-E, NOTE-F; see REVIEW.md "Round 3") and the round-4 verification of d2098474 (MAJOR-H, MINOR N8; see REVIEW.md
"Round 4"). Pure Python; reads files and git objects only; no AWS call; never reads or writes the meta1 ledger. The
only network step is the `git fetch` that `--admit` and `--launch-check` run (round 4 N8); report mode never fetches.

V2 (Codex decisions Q1-Q9 and R3-F, POLICY_DECISIONS_20260924.md and SPEND_STATIC_REVIEW_20260924.md findings 1-2 at
c3a128ee; slots schema 0.4; see REVIEW.md "v2 (Codex Q1-Q9)"). Where the text below says otherwise, V2 governs:
  R1 one admission authorizes exactly ONE RunInstances attempt. A second attempt under one admission (a row listing
     more than one attempt) is a limit breach (R5). A retry is a new append-only ATTEMPT ROW (`attempt_rows`, id
     "<slot>.<n>", n >= 2) with the slot's frozen definition and its own cap reserved while PLANNED; it needs its own
     fresh `--admit`, which covers prior spend, confirmed cleanup of every earlier attempt, the replacement cap, the
     owner stop and every remaining mandatory reserve. An attempt row may be appended only after the previous
     attempt is settled (DONE, INVALID or CLOSED_NO_LAUNCH). A RUNNING admission never goes back to PLANNED: an
     unused one is closed as CLOSED_NO_LAUNCH with proof of no launch, and reissued through the next attempt row.
  R2 `--admit` recomputes everything under a single-writer lock (ADMISSION.lock beside the slots file). An ADMIT is
     valid for ADMISSION_VALIDITY_SECONDS (300 s) and single use. `--launch-check SLOT`, run immediately before
     RunInstances, re-checks the lock, the time, single use and the recomputed inventory hash of the pre-admission
     state; expiry, a second use, a changed input or a lost lock refuses (a fresh check is then needed). The admission
     record binds the inventory hash, gate version, cap, remaining mandatory reserve, cumulative upper bound, main
     start count and launch identity. The receipt's launch time must lie inside the 300-s validity (this replaces the
     reusable lifetime window for admission validity; the search for unlisted attempts still uses the lifetime).
  R3 the unlisted-attempt search matches training files by seed + window with ANY source prefix; a file counts as
     listed only by its own path AND sha256: the listed receipt itself, and (v2.1, see listed_files) in its folder at
     the listed commit only a provider_NNNN.json directly beside it carrying exactly its job id, or a copy of its
     own worker result whose sha256 the hash-verified receipt pins; a watched record is skipped only when its sha256 is
     a listed pin or its instance id is listed, never by path alone; HEAD, pinned commits and the working tree are all
     read.
  R4 the admission binds source, bundle, worker and checker hashes for watched AND training slots; the receipt must
     show the same values at IDENTITY_FIELDS. A mismatch makes the result INVALID-worthy (rejected at DONE) and
     blocks every new admission, but no longer stops the cleanup check: the actual instance is still inspected and
     its cost counted.
  R5 a job that exceeded an admitted money / time / resource limit (or a second attempt under one admission) blocks
     every new admission, latched, even after its cleanup is confirmed. A CLOSED_NO_LAUNCH row with proof of no
     instance (including a prelaunch tool failure) does not.
  R6 main starts = every main attempt whose hash-verified receipt, bound to its admission, shows a launched instance,
     accepted or not, failed or repeated; a proven capacity refusal or a proven CLOSED_NO_LAUNCH does not count; an
     uncertain start blocks every admission. The $30.00 stop is checked before every admission while fewer than 3
     main attempts have started; settled rows only move forward, so once triggered it stays triggered.
  R7 CANCELLED_NOT_LAUNCHED: a never-admitted PLANNED row with a written cancellation and evidence; counted $0. An
     optional row's cap leaves fallback B; a mandatory row's cap stays reserved and COMPARISON_INCOMPLETE blocks every
     main (training-stop) admission.
  R8 the S1 capacity-refusal rule is ACCEPTED (Codex Q1), conditional on the pinned provider evidence it names.
  R9 the earlier preparation spend $1.9180 is one conservative prior-spend row (PRIOR, frozen whole), pending the
     owner's scope decision. Plan C's bound is not final.

FROZEN IN THIS CODE (never taken from the slots file; the file must agree or exit 2):
  * the $60.00 ceiling, the owner's $30.00 stop before the 3rd training job, the $0.10 S3/transfer/retention allowance;
  * the SLOT DEFINITIONS: the slot set, every cap, cap basis, flag, seed, arm, precondition and note, and the WHOLE rows
    of the pre-gate DONE slots S1, S2, P1a. Their canonical digest must equal FROZEN_DEFINITIONS_SHA256. Changing any of
    them needs a reviewed code change that re-freezes the digest.

MUTABLE PER SLOT (not pre-gate): status, receipt, invalid_reason, admission, attempts. Moves only forward, checked
against EVERY committed version of STUDY_SLOTS.json (`git log --full-history`, round 4 N8; exit 2 on a violation):
  PLANNED -> RUNNING (only `--admit` sets it, with an admission record) -> DONE (receipt filled) -> INVALID.
  A committed RUNNING row keeps its admission; a committed DONE row keeps its receipt and admission and may only become
  INVALID; a committed INVALID row never changes; no committed RUNNING / DONE / INVALID row may disappear. A committed
  `attempts` list only grows at its end (no listed attempt is ever removed, changed or reordered); INVALID freezes it.

LAUNCH ATTEMPTS (round 4 MAJOR-H). One admission may cover more than one launch attempt (a manual retry after a
capacity refusal or a failed launch, inside the admission's window). The row then lists EVERY attempt, in launch order,
in `attempts` (receipt specs of the same form as `receipt`); at DONE, `receipt` is the last listed attempt. Without
`attempts` the row has one attempt, its `receipt` (the single-receipt form; the frozen S1, S2, P1a rows always use it).
  * every attempt is read, counted and checked on its own: its pins, its own admission binding (window, seed, source)
    and its cleanup (confirmed, or a proven capacity refusal); one attempt that fails makes the slot UNCONFIRMED;
  * the slot's count is the SUM over its attempts, each by the status rule below (a proven, accepted capacity refusal
    at its bound, like S1); a RUNNING row adds its full cap for the attempt in progress;
  * no receipt identity may be claimed by two attempts, of one slot or of two.
UNLISTED ATTEMPTS FAIL CLOSED (round 4 MAJOR-H b). For every DONE, INVALID or overdue RUNNING slot the program looks
for launch attempts the row does not list; one found makes the slot UNCONFIRMED:
  * training: every file named `result.json`, `*_result.json` or `provider_NNNN.json` under the study's receipt home
    (TRAINING_RECEIPT_HOME, `typed_pointer_001/`) and under the folder that holds each listed attempt's receipt folder,
    at HEAD, at every commit a listed attempt is pinned to, and in the working tree (untracked or modified files). A
    job id there (its `job`, `authority.job` or `request.job` field; no other field is used) that carries this slot's
    seed and admitted source prefix and a time inside the admission's window, and that no listed attempt of this slot
    and no other slot claims, is an unlisted attempt;
  * watched: every `*launch_record.json` and `*watch_record.json` anywhere under the design folder, on disk and at HEAD.
    One that no listed attempt of this slot and no other slot claims (by path or instance id) is an unlisted attempt if
    its `launched_utc` lies inside the window, or if it has no readable launch time and sits in this slot's job folder
    (the top folder of a listed record);
  * the pre-gate rows S1, S2, P1a have no admission window. They are checked without one: S1 and S2 against every job
    id with their own seed and their own source prefix, P1a against every watched record under its job folder.

ACCOUNTING (exact decimals, every bound rounded UP to the cent):
  * DONE, receipt passes validation      -> the bound computed from that receipt;
  * DONE, receipt fails validation       -> max(cap, every cost figure the receipt itself shows); admissions refused
                                            until the slot is marked INVALID (the pins of a committed DONE row are frozen);
  * INVALID                              -> max(cap, every cost figure its receipt shows, if it has one), forever;
  * RUNNING                              -> its full cap (or more, if a receipt it already names shows more);
  * PLANNED                              -> nothing spent; if mandatory, its cap is reserved.
  "Every cost figure": recorded cost + allowances, cost recomputed from the timestamps, the receipt's own deadline or
  instance-seconds limit, each at the highest price the receipt or the basis shows. So a job that broke its own cost
  basis is never counted below what it recorded (review MAJOR 4). The receipt is read for these figures FIRST, from
  whatever commit and path its spec gives, before any spec-completeness or pin check (round 2 MAJOR-A): an empty
  spec field or a stale pin can reject a receipt, never shrink its count.
  Every cap must be at least the worst case its own basis computes (else exit 2; the old P1a $1.66 < $1.6639 guard).

CLEANUP, FAIL CLOSED (round 2 MAJOR-A). A cleanup is CONFIRMED only when HASH-VERIFIED records positively show this
slot's own machine gone: training -- cleanup complete, identity certain, the one launched instance CONFIRMED_TERMINATED,
nothing pending, no failure, compute cleanup COMPLETE; watched -- terminated confirmed, final state terminated or gone,
no volume left, the same instance and launch time in both records. Ids the spec does give must agree. A slot whose
receipt identity another slot also claims never confirms. The only other way out is a PROVEN capacity refusal under
the S1 rule (the receipt verified and every refusal check passed). A DONE or INVALID slot, or a RUNNING slot past its
lifetime (admission time + its basis's instance seconds or client deadline), without one of those is CLEANUP
UNCONFIRMED: a receipt that is missing, unreadable, stale, incomplete or silent is never a confirmation. Every admission
is then refused: a machine or disk may still exist, so the runner stops and reports to the owner. Nothing clears it.

THIS SLOT'S LAUNCH (round 3 MAJOR-E). For every slot except the pre-gate S1, S2 and P1a, a confirmed cleanup or a
proven refusal counts only when the verified receipt is THIS slot's admitted launch, whatever the slot's status
(DONE, INVALID, or RUNNING past its lifetime):
  (1) the admission record is one `--admit` wrote (gate, program_sha256, slots_sha256_before present; the program
      sha256 is a committed study_spend.py; slots_sha256_before is the committed STUDY_SLOTS.json version just before
      the first committed version showing the slot RUNNING with this identical record) -- NOTE-F -- and a committed
      version shows the slot RUNNING with it (the round-2 MINOR-B check, now also for INVALID rows);
  (2) the launch time the verified receipt ITSELF shows (the time in its own job id; launched_utc in both watched
      records) is at or after admitted_utc and before admitted_utc + the slot's lifetime;
  (3) training: the receipt's own model seed is the slot's seed, and its own source is the admitted source (the arm
      is bound through the source: one source per arm, never shared across arms).
Otherwise the cleanup is UNCONFIRMED ("the verified receipt is not this slot's admitted launch"). At DONE, (1) and
the window of (2) are also rejection reasons. The job id's time is set when the job is PREPARED: admit first, then
prepare and launch, all inside the slot's lifetime.

A receipt is also rejected when any identity it claims (receipt sha256 or path, job id, instance id, launch or watch
record sha256 or path, provider record) is claimed by another RUNNING / DONE / INVALID slot; every admission is then
refused (review MAJOR 1). A slot admitted by this gate must, at DONE, show the admitted source commit (and bundle for
watched jobs), the slot's own model seed (training), and a launch time AFTER its admission time and before admission
time + the slot's lifetime (round 3); and a committed version of STUDY_SLOTS.json must show the slot RUNNING with the
IDENTICAL admission record (round 2 MINOR-B: a hand-written record that was never committed as RUNNING is refused),
a record that carries the fields `--admit` writes and agrees with the committed history (round 3 NOTE-F).

ADMISSION (`--admit SLOT --source <commit> [--bundle <sha256>]`): exit 0 only if ALL of these hold, else exit 1 with the
reasons; any input error exit 2. On exit 0 it WRITES the slot as RUNNING with an admission record, in the same step.
  * the slot is PLANNED; no slot is RUNNING (one machine at a time); no DONE receipt is rejected; no identity is shared;
    no slot's cleanup is UNCONFIRMED (see CLEANUP: a machine or disk that may still exist: stop and report to the owner);
  * STUDY_SLOTS.json and study_spend.py equal HEAD (every earlier DONE is committed before the next machine starts);
  * HEAD equals the tip of the current branch's upstream, fetched just now (`git fetch`); if the fetch fails, refuse
    (round 4 N8: a stale checkout or a second runner cannot admit from an old copy of the slots file);
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
SCHEMA = "claude.helm-repair-controlled-1.study-slots/0.4"          # V2: attempt rows, two closing statuses
STATUSES = ("PLANNED", "RUNNING", "DONE", "INVALID", "CANCELLED_NOT_LAUNCHED", "CLOSED_NO_LAUNCH")
MUTABLE = ("status", "receipt", "invalid_reason", "admission", "attempts",    # "attempts": round 4 MAJOR-H
           "cancellation", "closure")                                         # V2 R7 / R1
# Done before this gate existed, or declared prior spend (V2 R9): their whole rows are frozen, no admission.
PRE_GATE_DONE = ("S1", "S2", "P1a", "PRIOR")
ATTEMPT_ROW_KEYS = ("id", "slot", "attempt") + MUTABLE                        # V2 R1: an append-only attempt row
SETTLED = ("DONE", "INVALID", "CLOSED_NO_LAUNCH")
ADMISSION_VALIDITY_SECONDS = 300        # V2 R2 (Codex R3-F): an ADMIT is valid for at most five minutes, single use
GATE_VERSION = "study_spend.py v2.1 (Codex Q1-Q9 and R3-F; slots schema 0.4; R3 listed-file rule narrowed)"
LOCK_NAME = "ADMISSION.lock"            # V2 R2: the single-writer admission lock, beside the slots file; never committed
# V2 R4: where each receipt shows the identity the admission binds (dotted paths inside the verified record).
IDENTITY_FIELDS = {
    "training_pointer": {"source_sha": ("authority", "source_sha"), "bundle_sha256": ("authority", "archive_sha256"),
                         "worker_sha256": ("authority", "worker_sha256"),
                         "checker_sha256": ("authority", "checker_sha256")},
    "watched_machine": {"source_sha": ("identity", "source_commit"), "bundle_sha256": ("bundle", "sha256"),
                        "worker_sha256": ("identity", "worker_sha256"),
                        "checker_sha256": ("identity", "checker_sha256")}}
# V2 R5: receipt problems that mean a job went past an admitted time or resource limit (money: any figure over the cap).
BREACH_CODES = ("ELAPSED_OVER_BASIS", "INSTANCE_SECONDS_MAX_OVER_BASIS", "DISK_OVER_BASIS", "DEADLINE_OVER_BASIS",
                "MACHINE_NOT_IN_BASIS")
# V2 R2 / R4: the fields every admission record `--admit` writes must carry, beyond the NOTE-F ones.
BINDING_FIELDS = ("gate_version", "valid_until_utc", "inventory_sha256", "lock_nonce", "cap_usd",
                  "remaining_mandatory_reserve_usd", "cumulative_upper_bound_usd", "main_starts", "source_sha",
                  "bundle_sha256", "worker_sha256", "checker_sha256")
Q1_ACCEPTANCE = "Codex Q1, POLICY_DECISIONS_20260924.md at c3a128ee"
# Round 4 MAJOR-H (b): the typed-pointer launcher's receipt home. Scanned (with the folder holding each listed receipt
# folder) for training launch attempts a row does not list. Repository-relative.
TRAINING_RECEIPT_HOME = "cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001"
TPNTR_JOB = re.compile(r"-(\d{14})-([0-9a-f]{8})-m-(\d+)$")   # ...-<prepared UTC>-<source prefix>-m-<model seed>
PROVIDER_NAME = re.compile(r"^provider_\d{4}\.json$")
ARMS = ("UNCHANGED", "REPAIRED")
POINTER_SCHEMA = "cas-graph-training-candidate-launch/1"
CENT, SIX = Decimal("0.01"), Decimal("0.000001")
SHA = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
SAFE_REF = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._/-]*$")     # a lenient read's commit: never an option-like string
MONEY = re.compile(r"^\d+\.\d{2}$")
DECIMAL = re.compile(r"^\d+(\.\d+)?$")
JOB_TIME = re.compile(r"-(\d{14})-")

# The owner's fixed numbers and the coordinator's allowance (review MAJOR 3): hard-coded, never read from the file.
CEILING_USD = Decimal("60.00")
STOP_USD = Decimal("30.00")
STOP_BEFORE_TRAINING_JOB = 3
ALLOWANCE_USD = Decimal("0.10")
# Canonical digest of STUDY_SLOTS.json without the mutable fields of non-pre-gate slots (definitions_digest()).
# V2 (schema 0.4, Codex Q1-Q9): re-frozen for the PRIOR row, the Q5 precondition lists, the decided questions and
# the owner-stop texts. S1, S2 and P1a are unchanged byte for byte. Was 82e80950... (schema 0.3).
FROZEN_DEFINITIONS_SHA256 = "a9fed7896aab374c6c2ce994dfe697999e37c960366107a1532b7d66b1760ecb"
ADMIT_GATE = "study_spend.py --admit"      # the `gate` field `--admit` writes into every admission record (NOTE-F)
MONEY_BASIS = ("worst-case SPEND upper bound (machine + address + disk + launcher ancillary + allowances), NOT the "
               "training launcher's fixed $15.00 bookings. Codex Q2: the $60.00 caps study charges, bounded across all "
               "attempts and required remaining work; the bookings are bookkeeping reservations, not invoices")


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


def prior_items(basis):
    """V2 R9: the declared earlier jobs of a prior-spend row, [(label, Decimal)]."""
    items = basis.get("items")
    if not isinstance(items, list) or not items or not all(isinstance(i, dict) for i in items):
        raise InputError("prior_spend basis needs items: [{job, attempt, usd}]")
    out = []
    for item in items:
        if not isinstance(item.get("job"), str) or not positive_int(item.get("attempt"), "prior_spend attempt"):
            raise InputError("prior_spend item needs job and attempt")
        out.append(("%s attempt %d" % (item["job"], item["attempt"]), decimal_str(item.get("usd"), "prior_spend usd")))
    return out


def basis_worst_case(basis, allowance):
    """Exact worst case a cap must cover. Returns (Decimal, arithmetic text)."""
    kind = basis.get("kind")
    if kind == "prior_spend":          # V2 R9: declared figures of earlier jobs; no allowance is added (Codex arithmetic)
        items = prior_items(basis)
        worst = sum((usd for _label, usd in items), Decimal("0"))
        return worst, "declared %s = $%s" % (" + ".join("%s $%s" % (label, usd) for label, usd in items), worst)
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
    """Digest of everything except the mutable fields of non-pre-gate slots (review MAJOR 3) and the append-only
    attempt rows, which are state, not definitions (V2 R1)."""
    d = copy.deepcopy(doc)
    if isinstance(d, dict):
        d.pop("attempt_rows", None)
    for s in d.get("slots") if isinstance(d.get("slots"), list) else []:
        if isinstance(s, dict) and s.get("id") not in PRE_GATE_DONE:
            for key in MUTABLE:
                s.pop(key, None)
    return sha256(canonical(d))


def attempt_rows_of(doc):
    rows = obj(doc).get("attempt_rows", [])
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise InputError("attempt_rows must be a list of objects")
    return rows


def all_rows(doc):
    """The raw slot rows and attempt rows of a slots document (V2 R1)."""
    return [r for r in obj(doc).get("slots") or [] if isinstance(r, dict)] + attempt_rows_of(doc)


def expand_attempt_row(row, parent):
    """V2 R1: an attempt row is its slot's frozen definition with the row's own id, number and mutable fields."""
    s = copy.deepcopy(parent)
    for key in MUTABLE:
        s.pop(key, None)
    for key in MUTABLE:
        if key in row:
            s[key] = copy.deepcopy(row[key])
    s.update(id=row["id"], attempt_of=parent["id"], attempt=row["attempt"],
             what="attempt %d of %s (a retry or a reissue): %s" % (row["attempt"], parent["id"], parent.get("what")))
    return s


def expand_attempts(doc, slots):
    """V2 R1: check the append-only attempt rows and return them as slots. Attempts of one slot are numbered 2, 3, ...
    in list order, with id '<slot>.<n>'; each may be appended only after the previous attempt is settled."""
    by_id, previous, out = {s.get("id"): s for s in slots}, {}, []
    for row in attempt_rows_of(doc):
        unknown = sorted(set(row) - set(ATTEMPT_ROW_KEYS))
        if unknown:
            raise InputError("attempt row %r carries fields an attempt row cannot: %s" % (row.get("id"), unknown))
        parent = by_id.get(row.get("slot"))
        if parent is None or parent.get("id") in PRE_GATE_DONE:
            raise InputError("attempt row %r names no slot that can have another attempt: %r" % (row.get("id"), row.get("slot")))
        before = previous.get(parent["id"], parent)
        want = before.get("attempt", 1) + 1
        if row.get("attempt") != want or row.get("id") != "%s.%d" % (parent["id"], want) or not is_int(row.get("attempt")):
            raise InputError("attempt row %r: the next attempt of %s is number %d with id %s.%d" % (
                row.get("id"), parent["id"], want, parent["id"], want))
        if before.get("status") not in SETTLED:
            raise InputError("attempt row %s: the previous attempt %s is %s; a new attempt row needs it settled (%s)" % (
                row["id"], before.get("id"), before.get("status"), ", ".join(SETTLED)))
        if not isinstance(row.get("receipt"), dict):
            raise InputError("attempt row %s: receipt spec missing" % row["id"])
        expanded = expand_attempt_row(row, parent)
        previous[parent["id"]] = expanded
        out.append(expanded)
    return out


def load_slots(path, frozen=FROZEN_DEFINITIONS_SHA256):
    try:
        raw = pathlib.Path(path).read_bytes()
    except OSError as error:
        raise InputError("slots file unreadable: %s: %s" % (type(error).__name__, error))
    return parse_slots(raw, frozen)


def parse_slots(raw, frozen=FROZEN_DEFINITIONS_SHA256):
    try:
        doc = json.loads(raw)
    except ValueError as error:
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
    slots = slots + expand_attempts(doc, slots)          # V2 R1: attempt rows are judged exactly like slots
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
                   "watched_machine": ("watched_machine",), "prior_spend": ("prior_spend_declared",)}[basis["kind"]]
        if receipt.get("kind") not in allowed:
            raise InputError("%s: receipt kind %r does not fit basis %r" % (sid, receipt.get("kind"), basis["kind"]))
        if basis["kind"] == "prior_spend" and (sid not in PRE_GATE_DONE or status != "DONE"):
            raise InputError("%s: a prior-spend row is a frozen DONE row (V2 R9)" % sid)
        for key, only in (("cancellation", "CANCELLED_NOT_LAUNCHED"), ("closure", "CLOSED_NO_LAUNCH")):
            if (slot.get(key) is not None) != (status == only):
                raise InputError("%s: %s is required with status %s and only with it" % (sid, key, only))
            if status == only:
                note = slot[key]
                if not (isinstance(note, dict) and all(isinstance(note.get(f), str) and note[f].strip()
                                                       for f in ("reason", "evidence"))):
                    raise InputError("%s: %s needs a written reason and evidence" % (sid, key))
        if status == "CANCELLED_NOT_LAUNCHED" and (slot.get("admission") is not None or slot.get("attempts") is not None):
            raise InputError("%s: CANCELLED_NOT_LAUNCHED is only for a row never admitted; an admitted, unused row is "
                             "CLOSED_NO_LAUNCH (Codex Q7)" % sid)
        if status == "CLOSED_NO_LAUNCH":
            if not isinstance(slot.get("admission"), dict) or slot.get("attempts") is not None:
                raise InputError("%s: CLOSED_NO_LAUNCH closes an admission that created no instance" % sid)
            proof = slot["closure"].get("receipt")
            if proof is not None and not (isinstance(proof, dict) and proof.get("kind") == "pointer_prelaunch_failure"
                                          and basis["kind"] == "training_pointer"):
                raise InputError("%s: a closure receipt is a training pointer_prelaunch_failure spec" % sid)
        attempts = slot.get("attempts")             # round 4 MAJOR-H (a): every launch attempt under one admission
        if attempts is not None:
            if status == "PLANNED":
                raise InputError("%s: a PLANNED slot cannot list launch attempts" % sid)
            if not isinstance(attempts, list) or not attempts or not all(isinstance(a, dict) for a in attempts):
                raise InputError("%s: attempts must be a non-empty list of receipt specs" % sid)
            for number, attempt in enumerate(attempts, 1):
                if attempt.get("kind") not in allowed:
                    raise InputError("%s: attempt %d kind %r does not fit basis %r" % (
                        sid, number, attempt.get("kind"), basis["kind"]))
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
    """Forward-only moves against every committed version of the slots file (review MAJOR 3). V2: attempt rows are
    append-only (R1); a RUNNING admission is never rewritten as PLANNED, only closed (R1); CANCELLED_NOT_LAUNCHED and
    CLOSED_NO_LAUNCH are final (R7, R1)."""
    current = {r.get("id"): r for r in all_rows(doc)}
    current_attempts = [r.get("id") for r in attempt_rows_of(doc)]

    def same(a, b, keys):
        return all(canonical(a.get(k)) == canonical(b.get(k)) for k in keys)

    def grows(a, b):
        """Round 4 MAJOR-H: a committed attempts list only grows at its end."""
        old, new = a.get("attempts") or [], b.get("attempts") or []
        return (isinstance(old, list) and isinstance(new, list) and len(new) >= len(old)
                and all(canonical(x) == canonical(y) for x, y in zip(old, new)))
    for commit, raw in history:
        try:
            old = json.loads(raw)
        except ValueError:
            raise InputError("committed slots file at %s is not JSON" % commit[:8])
        if not isinstance(old, dict) or not isinstance(old.get("slots"), list):
            raise InputError("committed slots file at %s has no slot list" % commit[:8])
        if not all(isinstance(o, dict) for o in old["slots"]):
            raise InputError("committed slots file at %s has a slot that is not an object" % commit[:8])
        try:
            old_attempts = attempt_rows_of(old)
        except InputError:
            raise InputError("committed slots file at %s has malformed attempt rows" % commit[:8])
        ids = [o.get("id") for o in old_attempts]
        if current_attempts[:len(ids)] != ids:
            raise InputError("HISTORY_VIOLATION: the attempt rows committed at %s (%s) are not the start of the current "
                             "ones: attempt rows are append-only" % (commit[:8], ",".join(map(str, ids))))
        for o in old["slots"] + old_attempts:
            sid, was = o.get("id"), o.get("status")
            cur = current.get(sid)
            if o in old_attempts and (cur is None or cur.get("slot") != o.get("slot") or cur.get("attempt") != o.get("attempt")):
                raise InputError("HISTORY_VIOLATION: attempt row %s committed at %s was removed or renumbered" % (sid, commit[:8]))
            if was not in ("RUNNING", "DONE", "INVALID", "CANCELLED_NOT_LAUNCHED", "CLOSED_NO_LAUNCH"):
                continue
            if cur is None:
                raise InputError("HISTORY_VIOLATION: %s was %s at %s and has disappeared" % (sid, was, commit[:8]))
            now = cur.get("status")
            if was == "INVALID":
                ok = now == "INVALID" and same(o, cur, ("receipt", "invalid_reason", "admission", "attempts"))
            elif was == "DONE":
                ok = now in ("DONE", "INVALID") and same(o, cur, ("receipt", "admission")) and grows(o, cur)
            elif was == "CANCELLED_NOT_LAUNCHED":
                ok = now == was and same(o, cur, ("cancellation", "receipt", "admission"))
            elif was == "CLOSED_NO_LAUNCH":
                ok = now == was and same(o, cur, ("closure", "receipt", "admission", "attempts"))
            else:
                ok = (now in ("RUNNING", "DONE", "INVALID", "CLOSED_NO_LAUNCH") and same(o, cur, ("admission",))
                      and grows(o, cur))
            if not ok:
                raise InputError("HISTORY_VIOLATION: %s was %s at %s; now %s, or its committed receipt / admission / "
                                 "reason changed, or a committed launch attempt was removed or changed (a RUNNING "
                                 "admission is never rewritten as PLANNED: close it as CLOSED_NO_LAUNCH)" % (
                                     sid, was, commit[:8], now))


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
        """(commit, bytes) of every committed version of HERE/name. `--full-history` (round 4 N8): git's default
        history simplification drops a side branch's commits when a merge keeps the other side's file."""
        done = self._run(["log", "--full-history", "--format=%H", "--", name])
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

    def tree_files(self, commit, folder):
        """(repository-relative path, blob id) of every file under `folder` (repository-relative) at `commit`."""
        if not (commit == "HEAD" or COMMIT.match(str(commit))):
            raise FileNotFoundError("not a commit: %r" % commit)
        where = ["--", folder.rstrip("/") + "/"] if folder.strip("/") else []
        done = self._run(["ls-tree", "-r", "-z", "--full-tree", commit] + where)
        if done.returncode != 0:
            raise FileNotFoundError("git ls-tree %s %s failed" % (commit, folder))
        out = []
        for item in done.stdout.split(b"\0"):
            meta, _, path = item.partition(b"\t")
            parts = meta.split()
            if len(parts) == 3 and parts[1] == b"blob":
                out.append((path.decode("utf-8"), parts[2].decode("ascii")))
        return out

    def blob_items(self, oids):
        """(blob id, bytes) of each blob, from one `git cat-file --batch`; a missing object raises."""
        if not oids:
            return
        done = subprocess.run(["git", "-C", self.repo, "cat-file", "--batch"], capture_output=True,
                              input="".join(o + "\n" for o in oids).encode("ascii"))
        if done.returncode != 0:
            raise OSError("git cat-file failed")
        data, pos = done.stdout, 0
        while pos < len(data):
            end = data.index(b"\n", pos)
            header = data[pos:end].split()
            if len(header) != 3:
                raise OSError("git cat-file: object missing: %r" % data[pos:end][:80])
            start = end + 1
            size = int(header[2])
            yield header[0].decode("ascii"), bytes(data[start:start + size])
            pos = start + size + 1

    def worktree_changes(self, folder, name_ok):
        """(repository-relative path, bytes) of files under `folder` whose name passes `name_ok` and that git reports
        untracked or modified in the working tree (their bytes are not in HEAD)."""
        top = self._run(["rev-parse", "--show-toplevel"])
        if top.returncode != 0:
            raise OSError("git rev-parse --show-toplevel failed")
        top = pathlib.Path(top.stdout.decode("utf-8").strip())
        done = self._run(["status", "--porcelain", "-z", "--untracked-files=all", "--", ":(top)" + folder.rstrip("/") + "/"])
        if done.returncode != 0:
            raise OSError("git status of %s failed" % folder)
        items, out, i = done.stdout.split(b"\0"), [], 0
        while i < len(items):
            item, i = items[i], i + 1
            if len(item) < 4:
                continue
            if item[:1] in (b"R", b"C"):
                i += 1                      # the next item is the rename's original path
            path = item[3:].decode("utf-8")
            if name_ok(path.rsplit("/", 1)[-1]) and (top / path).is_file():
                out.append((path, (top / path).read_bytes()))
        return out

    def prefix(self, path):
        """The repository-relative path of a folder, without a trailing slash."""
        done = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-prefix"], capture_output=True)
        if done.returncode != 0:
            raise OSError("git rev-parse --show-prefix failed")
        return done.stdout.decode("utf-8").strip().rstrip("/")

    def at_remote_tip(self, timeout=120):
        """(True, text) when HEAD equals the tip of the current branch's upstream, fetched just now; else (False, why).
        Round 4 N8: `--admit` refuses unless this holds; a fetch that fails refuses too."""
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0")

        def run(args):
            return subprocess.run(["git", "-C", self.repo] + args, capture_output=True, env=env, timeout=timeout)
        try:
            branch = run(["symbolic-ref", "--short", "-q", "HEAD"])
            if branch.returncode != 0:
                return False, "DETACHED_HEAD: run --admit on the study's branch"
            name = branch.stdout.decode("utf-8").strip()
            remote = run(["config", "--get", "branch.%s.remote" % name]).stdout.decode("utf-8").strip()
            merge = run(["config", "--get", "branch.%s.merge" % name]).stdout.decode("utf-8").strip()
            if not remote or not merge:
                return False, "NO_UPSTREAM: branch %s tracks no remote branch" % name
            if run(["fetch", "--quiet", remote, merge]).returncode != 0:
                return False, "FETCH_FAILED: git fetch %s %s" % (remote, merge)
            tip = run(["rev-parse", "--verify", "-q", "FETCH_HEAD"]).stdout.decode("ascii").strip()
            head = run(["rev-parse", "--verify", "-q", "HEAD"]).stdout.decode("ascii").strip()
        except (OSError, subprocess.TimeoutExpired) as error:
            return False, "FETCH_FAILED: %s" % type(error).__name__
        if not COMMIT.match(tip) or tip != head:
            return False, "HEAD_IS_NOT_THE_REMOTE_TIP: HEAD %s, fetched %s %s = %s" % (head[:12], remote, merge, tip[:12])
        return True, "HEAD %s equals the fetched tip of %s %s" % (head[:12], remote, merge)


def new_result():
    """read: some copy of the receipt was read (leniently or verified). cleanup_confirmed: HASH-VERIFIED records
    positively show a machine gone. proven_refusal: a verified capacity refusal passing the S1 rule. not_this_launch:
    why the verified receipt is not this slot's admitted launch ([] when it is; None when nothing was verified)."""
    return {"bound": None, "text": "", "problems": [], "pins": {}, "keys": set(), "figures": [],
            "read": False, "cleanup_confirmed": False, "proven_refusal": False, "not_this_launch": None,
            # V2: verified = the hash-verified copy was read; instance_shown = it names a launched instance (R6);
            # identity_problems = the admitted source / bundle / worker / checker it does not show (R4).
            "verified": False, "instance_shown": False, "identity_problems": []}


def spec_complete(receipt, keys):
    return all(receipt.get(k) not in (None, "", {}) for k in keys)


def spec_keys(receipt):
    """Identity claims of a receipt spec; two RUNNING / DONE / INVALID slots may never share one (review MAJOR 1)."""
    keys = set()

    def add(name, value):
        if isinstance(value, str) and value:
            keys.add((name, value))
    expected = obj(receipt.get("expected"))
    if receipt.get("kind") == "pointer_prelaunch_failure":           # V2: a CLOSED_NO_LAUNCH row's pinned proof
        add("receipt_sha256", receipt.get("sha256"))
        add("receipt_path", receipt.get("path"))
    elif receipt.get("kind") in ("pointer_finished", "pointer_capacity_refusal"):
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
    """The receipt at its place WITHOUT the hash check: used only to count MORE, never less, and never to confirm a
    cleanup. Whatever commit the spec gives is tried, except an option-like string (it would reach `git show`)."""
    if not (isinstance(commit, str) and SAFE_REF.match(commit) and isinstance(path, str) and path):
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


def fmt(when):
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def validity_end(admitted):
    """V2 R2 (Codex R3-F): an admission is valid from its time for ADMISSION_VALIDITY_SECONDS, single use."""
    return admitted + datetime.timedelta(seconds=ADMISSION_VALIDITY_SECONDS)


def identity_problems(slot, d):
    """V2 R4 (Codex Q8): the verified receipt `d` must show the admitted source, bundle, worker and checker hashes at
    IDENTITY_FIELDS. [] when it does, or when the row has no admission (reported elsewhere)."""
    a = slot.get("admission")
    if slot["id"] in PRE_GATE_DONE or not isinstance(a, dict):
        return []
    out = []
    for name, (outer, inner) in sorted(IDENTITY_FIELDS[slot["cap_basis"]["kind"]].items()):
        shown = obj(d.get(outer)).get(inner)
        if not (isinstance(shown, str) and shown and shown == a.get(name)):
            out.append("IDENTITY_NOT_THE_ADMITTED:%s: receipt %s.%s=%r, admitted %r" % (name, outer, inner, shown, a.get(name)))
    return out


def bind_admission(slot, res, launched_at, seed=None):
    """A slot admitted by this gate must show what it was admitted with (review MAJOR 1). V2 R2: the launch lies inside
    the admission's 300-s validity. V2 R4: source, bundle, worker and checker are checked by identity_problems."""
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
    if launched_at is None or launched_at < admitted:
        res["problems"].append("LAUNCH_NOT_AFTER_ADMISSION:%s vs admitted %s" % (launched_at, a.get("admitted_utc")))
    elif launched_at >= validity_end(admitted):                                          # V2 R2 (was the lifetime)
        res["problems"].append("LAUNCH_AFTER_THE_ADMISSION_VALIDITY:%s vs admitted %s + %d s" % (
            launched_at, a.get("admitted_utc"), ADMISSION_VALIDITY_SECONDS))
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


def job_time(job):
    """The UTC time inside a typed-pointer job id (`cas-meta2-tpntr-<YYYYmmddHHMMSS>-...`), or None. The launcher's
    prepare scripts stamp it with datetime.now(timezone.utc) when the job is PREPARED."""
    m = JOB_TIME.search(job) if isinstance(job, str) else None
    if not m:
        return None
    try:
        return datetime.datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def receipt_seed(d):
    return obj(obj(obj(d.get("authority")).get("worker_config")).get("design")).get("model_seed")


def pointer_admission(slot, d, expected, res):
    bind_admission(slot, res, job_time(expected.get("job")), seed=receipt_seed(d))


def not_this_launch(slot, launched_at, seed=None):
    """Why a HASH-VERIFIED receipt is NOT this slot's admitted launch; [] when it is (round 3 MAJOR-E). Only facts the
    receipt itself shows are used (never the spec's expected ids): its launch time must lie in [admitted_utc,
    admitted_utc + 300 s) (V2 R2: the admission's validity, was the lifetime); for a training slot its own model seed
    must be the slot's seed. V2 R4: a wrong source, bundle, worker or checker no longer makes the receipt "not this
    launch" (its machine is still inspected and its cost counted); it blocks the study through identity_problems.
    The pre-gate rows are exempt."""
    if slot["id"] in PRE_GATE_DONE:
        return []
    a = slot.get("admission")
    if not isinstance(a, dict):
        return ["NO_ADMISSION_RECORD"]
    admitted = utc(a.get("admitted_utc"))
    if admitted is None or a.get("slot") != slot["id"]:
        return ["ADMISSION_RECORD_MALFORMED_OR_OF_ANOTHER_SLOT"]
    out = []
    end = validity_end(admitted)
    shown = fmt(launched_at) if launched_at is not None else None
    if launched_at is None:
        out.append("RECEIPT_SHOWS_NO_LAUNCH_TIME")
    elif launched_at < admitted:
        out.append("LAUNCHED_BEFORE_ADMISSION:%s < admitted %s" % (shown, a["admitted_utc"]))
    elif launched_at >= end:
        out.append("LAUNCHED_AFTER_THE_ADMISSION_VALIDITY:%s >= %s" % (shown, fmt(end)))
    training = obj(slot.get("training"))
    if training:
        if not is_int(seed) or seed != training.get("model_seed"):
            out.append("SEED_NOT_THE_SLOT_SEED:receipt %r, slot %r" % (seed, training.get("model_seed")))
        if a.get("model_seed") != training.get("model_seed") or a.get("arm") != training.get("arm"):
            out.append("ADMISSION_SEED_OR_ARM_NOT_THE_SLOTS:%r %r" % (a.get("model_seed"), a.get("arm")))
    return out


def admission_provenance(slot, history, program_hashes):
    """Why a slot's admission record is not one `--admit` wrote and a committed version showed RUNNING; [] when it is
    (round 2 MINOR-B; round 3 NOTE-F; MAJOR-E condition 1 applies it to INVALID rows too). history: (commit, bytes) of
    every committed STUDY_SLOTS.json, newest first like `git log`. A careful hand edit that is committed can still pass;
    a careless one fails."""
    if slot["id"] in PRE_GATE_DONE:
        return []
    a = slot.get("admission")
    if not isinstance(a, dict):
        return ["NO_ADMISSION_RECORD"]
    want, first = canonical(a), None
    for index, (_commit, raw) in enumerate(history):
        try:
            rows = all_rows(json.loads(raw))           # V2 R1: attempt rows too
        except (ValueError, InputError):
            continue
        for row in rows:
            if (isinstance(row, dict) and row.get("id") == slot["id"] and row.get("status") == "RUNNING"
                    and isinstance(row.get("admission"), dict) and canonical(row["admission"]) == want):
                first = index           # newest first: the last match is the OLDEST version showing it RUNNING
    problems = []
    if first is None:
        problems.append("ADMISSION_NOT_IN_A_COMMITTED_RUNNING_ROW: no committed version of STUDY_SLOTS.json shows %s "
                        "RUNNING with this identical admission record (was --admit run and its RUNNING row committed?)"
                        % slot["id"])
    if a.get("gate") != ADMIT_GATE:
        problems.append("ADMISSION_NOT_WRITTEN_BY_THE_GATE:gate=%r" % a.get("gate"))
    program = a.get("program_sha256")
    if not (isinstance(program, str) and SHA.match(program) and program in program_hashes):
        problems.append("ADMISSION_PROGRAM_NOT_A_COMMITTED_STUDY_SPEND:%r" % program)
    missing = [f for f in BINDING_FIELDS if a.get(f) in (None, "")]        # V2 R2 / R4: what --admit binds
    if missing:
        problems.append("ADMISSION_RECORD_MISSING_BINDING:%s" % ",".join(missing))
    admitted = utc(a.get("admitted_utc"))
    if admitted is None or a.get("valid_until_utc") != fmt(validity_end(admitted)):
        problems.append("ADMISSION_VALIDITY_NOT_%d_S:%r" % (ADMISSION_VALIDITY_SECONDS, a.get("valid_until_utc")))
    before = a.get("slots_sha256_before")
    if not (isinstance(before, str) and SHA.match(before)):
        problems.append("ADMISSION_SLOTS_SHA256_BEFORE_MISSING:%r" % before)
    elif first is not None:
        older = history[first + 1][1] if first + 1 < len(history) else None
        if older is None or sha256(older) != before:
            problems.append("ADMISSION_SLOTS_BEFORE_NOT_THE_COMMITTED_VERSION_BEFORE_RUNNING:%s vs %s" % (
                before, sha256(older) if older is not None else "no earlier committed version"))
    return problems


def pointer_cleanup_confirmed(d, expected):
    """True only when a HASH-VERIFIED training receipt positively shows its own launched machine gone (round 2 MAJOR-A).
    Ids the spec does give must agree; an id the spec leaves empty is not guessed. The launcher's receipt has no volume
    list: its "complete" cleanup and the terminated instance are the only evidence it carries."""
    cleanup, iid = obj(d.get("cleanup")), obj(d.get("launch")).get("instance_id")
    if not (isinstance(iid, str) and iid):
        return False
    for want, got in ((expected.get("instance_id"), iid), (expected.get("job"), d.get("job"))):
        if isinstance(want, str) and want and want != got:
            return False
    return (cleanup.get("complete") is True and cleanup.get("compute_identity_uncertain") is False
            and cleanup.get("instance_ids") == [iid] and cleanup.get("instances") == {iid: "CONFIRMED_TERMINATED"}
            and cleanup.get("instances_termination_pending") == [] and cleanup.get("failures") == []
            and obj(d.get("stages")).get("compute_cleanup") == "COMPLETE")


def validate_pointer(slot, git, allowance, refusal):
    receipt, basis, res = slot["receipt"], slot["cap_basis"], new_result()
    problems, expected = res["problems"], obj(receipt.get("expected"))
    need = ("git_commit", "path", "sha256", "expected") + (("last_provider_record",) if refusal else ())
    need_expected = ("job", "source_sha", "instance_type") + (() if refusal else ("instance_id",))
    complete = spec_complete(receipt, need) and spec_complete(expected, need_expected)
    if not complete:
        problems.append("RECEIPT_SPEC_INCOMPLETE")
    # Round 2 MAJOR-A: read FIRST, from whatever commit and path the spec gives, before any completeness or pin return.
    # The lenient copy only ever ADDS cost figures and ids; only the hash-verified copy can confirm a cleanup.
    d = read_pinned_git(git, receipt.get("git_commit"), receipt.get("path"), receipt.get("sha256"), problems, "RECEIPT")
    lenient = d if d is not None else read_git_lenient(git, receipt.get("git_commit"), receipt.get("path"))
    if lenient is not None:
        res["read"] = True
        res["figures"] = pointer_figures(lenient, basis, allowance)
        for name, value in (("job", lenient.get("job")), ("instance_id", obj(lenient.get("launch")).get("instance_id"))):
            if isinstance(value, str) and value:
                res["keys"].add((name, value))
    if d is None:
        return res
    res["verified"] = True
    iid = obj(d.get("launch")).get("instance_id")
    res["instance_shown"] = isinstance(iid, str) and bool(iid)                    # V2 R6: a machine was launched
    res["cleanup_confirmed"] = pointer_cleanup_confirmed(d, expected)
    # Round 3 MAJOR-E: from the verified receipt's OWN job id and seed, before any completeness return.
    res["not_this_launch"] = not_this_launch(slot, job_time(d.get("job")), seed=receipt_seed(d))
    res["identity_problems"] = identity_problems(slot, d)                          # V2 R4
    if not complete:
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
    else:
        proof = []
        validate_refusal_specifics(d, receipt, expected, git, proof)
        problems.extend(proof)
        # Proven only for THIS job: every S1-rule check passed and the verified receipt is the job the spec names.
        res["proven_refusal"] = not proof and not any(p.startswith("JOB_MISMATCH") for p in problems)
    pointer_admission(slot, d, expected, res)
    problems.extend(res["identity_problems"])                                     # V2 R4: rejected at DONE
    if problems:
        return res
    ancillary = Decimal(basis["launcher_ancillary_usd"])
    exact = elapsed / 3600 * rate + ancillary + allowance
    res["bound"] = up(exact)
    res["text"] = "elapsed %s s x $%s/h + $%s launcher ancillary + $%s S3/transfer = $%s%s" % (
        elapsed, rate, ancillary, allowance, exact.quantize(SIX), " (no machine ran)" if refusal else "")
    res["pins"] = {"receipt_sha256": receipt["sha256"]}
    if refusal:                 # V2 R8: the rule is accepted (Codex Q1); the evidence that resolves the flag is named
        last = receipt["last_provider_record"]
        res["pins"]["override"] = (
            "launcher flag compute_identity_uncertain=%r resolved by the capacity-refusal rule, ACCEPTED (%s) "
            "conditional on the pinned provider failure evidence in override_resolved_by: AWS refused RunInstances "
            "(InsufficientInstanceCapacity, zero client retries), no machine was created, the temporary resources were "
            "removed. Counted at the elapsed-time bound, not the cap; not proof that the invoice equals it" % (
                cleanup.get("compute_identity_uncertain"), Q1_ACCEPTANCE))
        res["pins"]["override_resolved_by"] = {
            "last_provider_record": {"path": last["path"], "sha256": last["sha256"], "operation": "run_instances",
                                     "state": "FAILED", "error": "(InsufficientInstanceCapacity)"},
            "no_later_provider_record": "the highest-numbered provider_NNNN.json in its folder at %s" % receipt["git_commit"],
            "receipt_sha256": receipt["sha256"],
            "receipt_outcome": "ClientError: (InsufficientInstanceCapacity) calling the RunInstances operation "
                               "(reached max retries: 0)",
            "receipt_cleanup": "no instance ids, no instances, none pending; security group deleted; roles removed; the "
                               "only failure is INSTANCE_IDENTITY_UNKNOWN_AFTER_LAUNCH_ATTEMPT"}
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


def watch_shows_terminated(watch):
    return (watch.get("terminated_confirmed") is True and watch.get("final_state") in ("terminated", "gone")
            and watch.get("volumes_of_this_job_remaining") == [])


def watched_cleanup_confirmed(launch, watch, expected):
    """True only when BOTH hash-verified records name the same machine and launch, and the watcher saw it gone with no
    volume left (round 2 MAJOR-A). Ids the spec does give must agree."""
    iid = launch.get("instance_id")
    if not (isinstance(iid, str) and iid) or watch.get("instance_id") != iid:
        return False
    if not isinstance(launch.get("launched_utc"), str) or watch.get("launched_utc") != launch.get("launched_utc"):
        return False
    for want, got in ((expected.get("instance_id"), iid), (expected.get("launched_utc"), launch.get("launched_utc"))):
        if isinstance(want, str) and want and want != got:
            return False
    return watch_shows_terminated(watch)


def validate_watched(slot, info, root, allowance):
    receipt, basis, res = slot["receipt"], slot["cap_basis"], new_result()
    problems, expected = res["problems"], obj(receipt.get("expected"))
    complete = (spec_complete(receipt, ("launch_record", "watch_record", "launch_schema", "watch_schema", "expected"))
                and spec_complete(expected, ("instance_id", "launched_utc", "source_commit", "bundle_sha256")))
    if not complete:
        problems.append("RECEIPT_SPEC_INCOMPLETE")
    # Round 2 MAJOR-A: read FIRST, from whatever paths the spec gives, before any completeness or pin return.
    launch = read_pinned_file(root, receipt.get("launch_record"), problems, "LAUNCH_RECORD")
    watch = read_pinned_file(root, receipt.get("watch_record"), problems, "WATCH_RECORD")
    lenient_launch = launch if launch is not None else read_file_lenient(root, receipt.get("launch_record"))
    lenient_watch = watch if watch is not None else read_file_lenient(root, receipt.get("watch_record"))
    res["read"] = lenient_launch is not None or lenient_watch is not None
    res["figures"] = watched_figures(lenient_launch or {}, lenient_watch or {}, basis, allowance)
    for doc in (lenient_launch or {}, lenient_watch or {}):
        if isinstance(doc.get("instance_id"), str) and doc["instance_id"]:
            res["keys"].add(("instance_id", doc["instance_id"]))
    if launch is None or watch is None:
        return res
    res["verified"] = True
    res["instance_shown"] = isinstance(launch.get("instance_id"), str) and bool(launch.get("instance_id"))
    res["cleanup_confirmed"] = watched_cleanup_confirmed(launch, watch, expected)
    # Round 3 MAJOR-E: the launch time BOTH verified records show, before any completeness return.
    same = isinstance(launch.get("launched_utc"), str) and watch.get("launched_utc") == launch.get("launched_utc")
    res["not_this_launch"] = not_this_launch(slot, utc(launch["launched_utc"]) if same else None)
    res["identity_problems"] = identity_problems(slot, launch)                     # V2 R4 (was NOTE K: time only)
    if not complete:
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
    if not watch_shows_terminated(watch):
        problems.append("NOT_CONFIRMED_TERMINATED_OR_VOLUMES_LEFT_OR_UNKNOWN:%r %r" % (
            watch.get("final_state"), watch.get("volumes_of_this_job_remaining")))
    cost = number(watch.get("cost_upper_bound_usd"))
    if cost is None or cost < 0 or cost > info["cap"]:
        problems.append("WATCH_COST_INVALID:%r" % watch.get("cost_upper_bound_usd"))
    minutes = number(watch.get("minutes_from_launch_to_watch_end"))
    start, end = utc(watch.get("launched_utc")), utc(watch.get("watch_ended_utc"))
    if minutes is None or minutes <= 0 or start is None or end is None or end <= start:
        problems.append("WATCH_TIMES_INVALID")
    bind_admission(slot, res, utc(expected["launched_utc"]))
    problems.extend(res["identity_problems"])                                     # V2 R4: rejected at DONE
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


def validate_prior(slot):
    """V2 R9: one conservative prior-spend row. Counted at its declared total, rounded up; there is no receipt to pin,
    and this program does not re-check those jobs' cleanup (their own watchers recorded it)."""
    res = new_result()
    worst, text = basis_worst_case(slot["cap_basis"], ALLOWANCE_USD)
    res.update(bound=up(worst), read=True, text=text + ", rounded up to $%s (declared watcher figures, not program-"
               "validated; included conservatively pending the owner's scope decision)" % up(worst),
               pins={"declared": "no receipt pins: the figures are the jobs' own watcher records, as listed"})
    return res


def validate_receipt(slot, info, root, git):
    kind = slot["receipt"]["kind"]
    if kind == "prior_spend_declared":
        return validate_prior(slot)
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


# -------------------------------------------------------------------------------- launch attempts (round 4 MAJOR-H)
def slot_attempts(slot):
    """[(label, receipt spec)] of every launch attempt a RUNNING / DONE / INVALID row carries. Without `attempts`: the
    single-receipt form, labelled with the slot id (a DONE row always; other rows only when the receipt has pins). With
    `attempts`: each listed spec, labelled "<slot>#<n>", plus the row's receipt ("<slot>#receipt") if it has pins and
    is not one of the listed specs."""
    sid, receipt, listed = slot["id"], slot["receipt"], slot.get("attempts")
    if listed is None:
        if slot["status"] == "DONE" or (slot["status"] in ("INVALID", "RUNNING") and receipt_has_pins(receipt)):
            return [(sid, receipt)]
        return []
    out = [("%s#%d" % (sid, n), spec) for n, spec in enumerate(listed, 1)]
    if receipt_has_pins(receipt) and not any(canonical(spec) == canonical(receipt) for spec in listed):
        out.append(("%s#receipt" % sid, receipt))
    return out


def label_slot(label):
    return label.split("#", 1)[0]


def attempt_name(label):
    tail = label.split("#", 1)[1] if "#" in label else ""
    return "attempt %s" % tail if tail.isdigit() else "the row's receipt (not in attempts)"


def attempt_where(spec):
    if spec.get("kind") == "watched_machine":
        return obj(spec.get("launch_record")).get("path")
    return spec.get("path")


def training_scan_name(name):
    return name == "result.json" or name.endswith("_result.json") or bool(PROVIDER_NAME.match(name))


def watched_scan_name(name):
    return name.endswith("launch_record.json") or name.endswith("watch_record.json")


def job_parts(job):
    """(prepared UTC, source prefix, model seed) of a typed-pointer job id, or None."""
    m = TPNTR_JOB.search(job) if isinstance(job, str) else None
    if not m:
        return None
    try:
        when = datetime.datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None
    return when, m.group(2), int(m.group(3))


class AttemptScanner:
    """Round 4 MAJOR-H (b), V2 R3: what the study's receipt folders and the design folder hold, read at most once per
    run. From a training file only its job ids and its sha256 are taken (`job`, `authority.job`, `request.job`), plus
    the worker-result pin a launcher receipt carries (`collected.result_sha256`), used only for a listed receipt whose
    sha256 equals its pin; from a watched record only its instance id, its launch time and its sha256. No other field
    of a scanned file is used or printed."""

    def __init__(self, git, root):
        self.git, self.root = git, pathlib.Path(root)
        self.blob_info, self.trees, self.worktrees, self.watched = {}, {}, {}, None

    @staticmethod
    def job_ids(raw):
        try:
            d = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return set()
        if not isinstance(d, dict):
            return set()
        return {j for j in (d.get("job"), obj(d.get("authority")).get("job"), obj(d.get("request")).get("job"))
                if isinstance(j, str) and j}

    @staticmethod
    def result_pin(raw):
        """The sha256 a launcher receipt pins for its own attempt's worker result (`collected.result_sha256`), or None."""
        try:
            d = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return None
        pin = obj(obj(d).get("collected")).get("result_sha256")
        return pin if isinstance(pin, str) and SHA.match(pin) else None

    def _tree(self, commit, folder):
        """([(path, blob id)] of the training-scan-named files under `folder` at `commit`, failure or None); cached.
        Each blob's job ids, sha256 and worker-result pin are kept in blob_info."""
        key = (commit, folder)
        if key not in self.trees:
            try:
                files = [(p, oid) for p, oid in self.git.tree_files(commit, folder)
                         if training_scan_name(p.rsplit("/", 1)[-1])]
                need = sorted({oid for _p, oid in files if oid not in self.blob_info})
                for oid, raw in self.git.blob_items(need):
                    self.blob_info[oid] = (self.job_ids(raw), sha256(raw), self.result_pin(raw))
                self.trees[key] = (files, None)
            except (OSError, KeyError, ValueError) as error:
                self.trees[key] = ([], "SCAN_FAILED:%s:%s:%s" % (str(commit)[:8], folder, type(error).__name__))
        return self.trees[key]

    def training_hits(self, commits, folders):
        """({job id: [(place, path, sha256)]}, [scan failures]) over the folders at each commit and in the working
        tree (files git reports untracked or modified)."""
        found, failures = {}, []
        for folder in folders:
            for commit in commits:
                files, failure = self._tree(commit, folder)
                if failure:
                    failures.append(failure)
                for p, oid in files:
                    jobs, digest, _pin = self.blob_info[oid]
                    for job in jobs:
                        found.setdefault(job, []).append(("%s:%s" % (commit[:8], p), p, digest))
            if folder not in self.worktrees:
                try:
                    self.worktrees[folder] = ([(p, sha256(raw), self.job_ids(raw)) for p, raw in
                                               self.git.worktree_changes(folder, training_scan_name)], None)
                except (OSError, ValueError) as error:
                    self.worktrees[folder] = ([], "SCAN_FAILED:working tree:%s:%s" % (folder, type(error).__name__))
            items, failure = self.worktrees[folder]
            if failure:
                failures.append(failure)
            for p, digest, jobs in items:
                for job in jobs:
                    found.setdefault(job, []).append(("working tree:%s" % p, p, digest))
        return found, failures

    def folder_files(self, commit, folder):
        """V2 R3: ([(path, sha256, job ids, worker-result pin)] of the training-scan-named files under a listed
        receipt's folder at its commit, failure or None)."""
        files, failure = self._tree(commit, folder)
        return [(p, self.blob_info[oid][1], frozenset(self.blob_info[oid][0]), self.blob_info[oid][2])
                for p, oid in files], failure

    def watched_records(self):
        """([(design-folder-relative path, instance id, launched_utc, place, sha256)], [scan failures]) of every launch
        and watch record under the design folder, on disk and at HEAD."""
        if self.watched is None:
            records, failures = [], []

            def add(rel, raw, place):
                try:
                    d = json.loads(raw)
                except (ValueError, UnicodeDecodeError):
                    d = None
                d = d if isinstance(d, dict) else {}
                iid = d.get("instance_id") if isinstance(d.get("instance_id"), str) and d.get("instance_id") else None
                records.append((rel, iid, d.get("launched_utc"), place, sha256(raw)))
            try:
                for dirpath, _dirs, names in os.walk(self.root):
                    for name in sorted(names):
                        if watched_scan_name(name):
                            path = pathlib.Path(dirpath) / name
                            add(path.relative_to(self.root).as_posix(), path.read_bytes(), "disk")
                prefix = self.git.prefix(self.root)
                files = [(p, oid) for p, oid in self.git.tree_files("HEAD", prefix)
                         if watched_scan_name(p.rsplit("/", 1)[-1])]
                blobs = dict(self.git.blob_items(sorted({oid for _p, oid in files})))
                for p, oid in files:
                    add(p[len(prefix) + 1:] if prefix else p, blobs[oid], "HEAD")
            except (OSError, KeyError, ValueError) as error:
                failures.append("SCAN_FAILED:design folder:%s" % type(error).__name__)
            self.watched = (records, failures)
        return self.watched


def listed_files(scanner, specs):
    """V2 R3 (Codex finding L; conformance check of d5c8184a): the (path, sha256) pairs a row's listed training
    receipts account for. Each listed receipt counts by its own pinned path AND sha256. Its copy at the listed commit
    whose sha256 equals the pin is the only source of anything else; beside it, in its folder at that commit, only:
      (a) a provider_NNNN.json DIRECTLY in the folder (no subfolder) whose job ids are exactly the receipt's one job id;
      (b) a file whose sha256 equals the worker-result pin the receipt itself carries (`collected.result_sha256`): the
          byte-identical copies of this attempt's own worker result the launcher collects into every receipt folder
          (curriculum_result.json, collected/results/result.json).
    Any other result.json or *_result.json never counts, and a job id alone never makes a file listed. Returns (set,
    [scan failures])."""
    out, failures = set(), []
    for spec in specs:
        path, pin, commit = spec.get("path"), spec.get("sha256"), spec.get("git_commit")
        if not (isinstance(path, str) and path and isinstance(pin, str) and SHA.match(pin)):
            continue
        out.add((path, pin))
        if "/" in path and isinstance(commit, str) and COMMIT.match(commit):
            folder = path.rsplit("/", 1)[0]
            files, failure = scanner.folder_files(commit, folder)
            if failure:
                failures.append(failure)
            own = [(jobs, result) for p, digest, jobs, result in files if p == path and digest == pin]
            if len(own) != 1 or len(own[0][0]) != 1:
                continue                    # no hash-verified receipt with one job id: nothing else counts (fail closed)
            job, result = own[0]
            out |= {(p, digest) for p, digest, jobs, _r in files if p != path and (
                (p.rsplit("/", 1)[0] == folder and PROVIDER_NAME.match(p.rsplit("/", 1)[-1]) and jobs == job)
                or (result is not None and digest == result))}
    return out, failures


def unlisted_attempts(slot, specs, own_ids, scanner, claims):
    """Round 4 MAJOR-H (b), V2 R3: launch attempts that belong to this row but that it does not list; [] when none.
    Fail closed: any finding, including a scan that could not run, makes the row's cleanup UNCONFIRMED.
      training: a job id with this row's seed, prepared inside its search window (admission time + the lifetime), with
        ANY source prefix (V2 R3; the pre-gate S1 and S2 keep their own source prefix, at any time), found in a file
        whose (path, sha256) neither this row lists nor another row lists;
      watched: a launch or watch record whose sha256 is not a listed pin and whose instance id is not listed (never
        skipped by its path alone), that no other row claims by sha256 or instance id, launched inside the window (or,
        with no readable launch time, inside the row's job folder).
    specs: the receipt specs the row lists; own_ids: the instance ids its listed records show; claims: {"files":
    {(path, sha256): row ids}, "keys": {identity key: attempt labels}} over every row."""
    sid, basis = slot["id"], slot["cap_basis"]
    if basis["kind"] == "prior_spend":
        return []

    def other(key, table):
        return any(label_slot(label) != sid for label in table.get(key, ()))
    if sid in PRE_GATE_DONE:
        window = None               # no admission: S1 and S2 by seed and source, P1a by its job folder, at any time
    else:
        admitted = utc(obj(slot.get("admission")).get("admitted_utc"))
        if admitted is None:
            return []               # nothing to scan against; the missing admission already leaves it UNCONFIRMED
        window = (admitted, admitted + datetime.timedelta(seconds=lifetime_seconds(basis)))
    out = []
    if basis["kind"] == "training_pointer":
        if window is None:
            parts = job_parts(obj(slot["receipt"].get("expected")).get("job"))
            if parts is None:
                return ["PRE_GATE_JOB_ID_UNREADABLE: its launch attempts cannot be scanned"]
            _when, prefix, seed = parts
        else:
            prefix, seed = None, obj(slot.get("training")).get("model_seed")       # V2 R3: any source prefix
            if not is_int(seed):
                return ["SLOT_SEED_UNREADABLE: its launch attempts cannot be scanned"]
        pointer_specs = [spec for spec in specs if spec.get("kind") != "watched_machine"]
        own, failures = listed_files(scanner, pointer_specs)
        out.extend(failures)
        commits = ["HEAD"] + sorted({spec.get("git_commit") for spec in pointer_specs
                                     if COMMIT.match(str(spec.get("git_commit")))})
        folders = {TRAINING_RECEIPT_HOME}
        for spec in pointer_specs:
            path = spec.get("path")
            if isinstance(path, str) and "/" in path:       # the folder that holds this attempt's receipt folder
                folders.add(path.rsplit("/", 2)[0] if path.count("/") >= 2 else path.rsplit("/", 1)[0])
        found, failures = scanner.training_hits(commits, sorted(folders))
        out.extend(failures)
        for job in sorted(found):
            parts = job_parts(job)
            if parts is None:
                continue
            when, source_prefix, job_seed = parts
            if job_seed != seed or (prefix is not None and source_prefix != prefix) or (
                    window and not window[0] <= when < window[1]):
                continue
            places = sorted({place for place, path, digest in found[job]
                             if (path, digest) not in own and not other((path, digest), claims["files"])})
            if places:
                out.append("UNLISTED_TRAINING_ATTEMPT:%s (%s)" % (job, "; ".join(places[:3])))
        return out
    listed_paths = {obj(spec.get(k)).get("path") for spec in specs for k in ("launch_record", "watch_record")}
    listed_shas = {obj(spec.get(k)).get("sha256") for spec in specs for k in ("launch_record", "watch_record")}
    listed_ids = {obj(spec.get("expected")).get("instance_id") for spec in specs} | set(own_ids)
    job_folders = {p.split("/", 1)[0] for p in listed_paths if isinstance(p, str) and "/" in p}
    records, failures = scanner.watched_records()
    out.extend(failures)
    seen = set()
    for rel, iid, launched, place, digest in records:
        if digest in listed_shas or (iid and iid in listed_ids):          # V2 R3: never by path alone
            continue
        if (other(("launch_record_sha256", digest), claims["keys"]) or other(("watch_record_sha256", digest), claims["keys"])
                or (iid and other(("instance_id", iid), claims["keys"]))):
            continue
        in_job_folder = "/" in rel and rel.split("/", 1)[0] in job_folders
        when = utc(launched)
        if window is None:
            hit = in_job_folder
        else:
            hit = (when is not None and window[0] <= when < window[1]) or (when is None and in_job_folder)
        if hit and (rel, iid, launched, digest) not in seen:
            seen.add((rel, iid, launched, digest))
            out.append("UNLISTED_WATCHED_LAUNCH:%s instance %s launched %s (%s)" % (rel, iid, launched, place))
    return out


def closure_proof(slot, git):
    """V2 R1 / R5: why a CLOSED_NO_LAUNCH row's pinned prelaunch-failure receipt does NOT prove that no instance was
    created; [] when it does, or when there is none (the search of its admission window is then the whole proof). A
    pinned receipt must be this admission's job (its own time inside the 300-s validity, the slot's seed), show no
    launch record and no instance, and its folder at that commit must hold no RunInstances provider call at all."""
    rec = obj(obj(slot.get("closure")).get("receipt"))
    if not rec:
        return []
    problems = []
    d = read_pinned_git(git, rec.get("git_commit"), rec.get("path"), rec.get("sha256"), problems, "CLOSURE_RECEIPT")
    if d is None:
        return problems
    problems.extend("CLOSURE_RECEIPT_NOT_THIS_ADMISSION:" + g
                    for g in not_this_launch(slot, job_time(d.get("job")), seed=receipt_seed(d)))
    cleanup = obj(d.get("cleanup"))
    if d.get("launch") is not None:
        problems.append("CLOSURE_RECEIPT_SHOWS_A_LAUNCH")
    if cleanup.get("instance_ids") != [] or cleanup.get("instances") != {} or cleanup.get("instances_termination_pending") != []:
        problems.append("CLOSURE_RECEIPT_NAMES_AN_INSTANCE")
    directory = rec["path"].rsplit("/", 1)[0] if "/" in rec["path"] else ""
    try:
        names = [n for n in git.names(rec["git_commit"], directory) if PROVIDER_NAME.match(n)]
    except (OSError, FileNotFoundError):
        return problems + ["CLOSURE_PROVIDER_LIST_UNREADABLE"]
    for name in names:
        try:
            call = json.loads(git.read(rec["git_commit"], "%s/%s" % (directory, name) if directory else name))
        except (OSError, FileNotFoundError, ValueError):
            problems.append("CLOSURE_PROVIDER_RECORD_UNREADABLE:%s" % name)
            continue
        if obj(call).get("operation") == "run_instances":
            problems.append("CLOSURE_FOLDER_SHOWS_A_RUNINSTANCES_CALL:%s" % name)
    return problems


# ------------------------------------------------------------------------------------------ accounting + admission
def lifetime_seconds(basis):
    """The longest a slot's machine may live by its own basis: training instance seconds, or the watched client deadline."""
    if basis["kind"] == "training_pointer":
        return basis["instance_seconds_max"]
    return basis["client_deadline_minutes_max"] * 60


def past_lifetime(slot, now):
    """A RUNNING slot whose admission time + its basis lifetime has passed, or whose admission time is unreadable. A
    launch made later than the admission makes this flag early, never late (fail closed)."""
    admitted = utc(obj(slot.get("admission")).get("admitted_utc"))
    return admitted is None or now > admitted + datetime.timedelta(seconds=lifetime_seconds(slot["cap_basis"]))


def cleanup_gap(res, shared, provenance=()):
    """None when the cleanup is confirmed (or the slot is a proven capacity refusal) AND the verified receipt is this
    slot's admitted launch; else why not (round 2 MAJOR-A; round 3 MAJOR-E)."""
    if res is None or not res["read"]:
        return "no readable receipt"
    if shared:
        return "its receipt identity is also claimed by another slot"
    if not (res["cleanup_confirmed"] or res["proven_refusal"]):
        return ("the receipt does not positively show this slot's own machine terminated with no volume left, from "
                "hash-verified records (a stale, incomplete or silent record never confirms)")
    if provenance:
        return ("the admission record is not one `--admit` wrote and a committed version showed RUNNING, so nothing "
                "ties the receipt to this slot's launch: %s" % "; ".join(provenance))
    binding = res.get("not_this_launch")
    if binding is None or binding:
        return "the verified receipt is not this slot's admitted launch: %s" % "; ".join(binding or ["NOT_EVALUATED"])
    return None


def attempt_count(cap, res, trusted):
    """One attempt's count: its computed bound when trusted and accepted; else the larger of the cap and every cost
    figure its receipt shows (review MAJOR 4)."""
    if trusted and res is not None and not res["problems"] and res["bound"] is not None:
        return res["bound"], res["text"]
    return counted_at_least_cap(cap, res)


def summed(cap, items, multi, trusted):
    """(sum, text) over a row's attempts (round 4 MAJOR-H); the single-receipt form keeps its old text exactly."""
    if not multi:
        return attempt_count(cap, items[0][2] if items else None, trusted)
    total, texts = Decimal("0"), []
    for label, spec, res in items:
        value, text = attempt_count(cap, res, trusted)
        total += value
        texts.append("%s (%s): $%s = %s" % (attempt_name(label), attempt_where(spec), value, text))
    if not items:
        total, texts = cap, ["no attempt listed: cap $%s" % cap]
    return total, "sum over %d launch attempt(s) = $%s: %s" % (len(items), total, "; ".join(texts))


def account(loaded, root, git, history=None, now=None, program_name=None):
    slots, info = loaded["slots"], loaded["info"]
    history = git.history(SLOTS_FILE.name) if history is None else history
    now = now or datetime.datetime.now(datetime.timezone.utc)
    overdue = {s["id"] for s in slots if s["status"] == "RUNNING" and past_lifetime(s, now)}
    # Round 4 MAJOR-H (a): every launch attempt a row carries is read and judged on its own.
    entries = {s["id"]: [(label, spec, validate_receipt(dict(s, receipt=spec), info[s["id"]], root, git))
                         for label, spec in slot_attempts(s)]
               for s in slots if s["status"] in ("RUNNING", "DONE", "INVALID")}
    # V2 R1 / R5: a CLOSED_NO_LAUNCH row may pin the prelaunch-failure receipt that proves no instance was created.
    closure_specs = {s["id"]: s["closure"]["receipt"] for s in slots
                     if s["status"] == "CLOSED_NO_LAUNCH" and isinstance(s["closure"].get("receipt"), dict)}
    by_label = {label: res for items in entries.values() for label, _spec, res in items}
    owners = {}             # identity -> the attempts claiming it (a label is the row id, or "<row>#<n>")
    for s in slots:
        if s["status"] in ("RUNNING", "DONE", "INVALID"):
            receipt_label = next((label for label, spec, _res in entries[s["id"]]
                                  if canonical(spec) == canonical(s["receipt"])), s["id"])
            for key in spec_keys(s["receipt"]):
                owners.setdefault(key, set()).add(receipt_label)
            for label, spec, res in entries[s["id"]]:
                for key in spec_keys(spec) | res["keys"]:
                    owners.setdefault(key, set()).add(label)
        if s["id"] in closure_specs:
            for key in spec_keys(closure_specs[s["id"]]):
                owners.setdefault(key, set()).add(s["id"])
    shared = {"%s=%s" % key: sorted(ids) for key, ids in sorted(owners.items()) if len(ids) > 1}
    shared_labels = {label for ids in shared.values() for label in ids}
    for label, ids in shared.items():
        for owner in ids:
            if owner in by_label:
                by_label[owner]["problems"].append("RECEIPT_SHARED:%s:with=%s" % (label, ",".join(i for i in ids if i != owner)))
    # Round 2 MINOR-B, round 3 NOTE-F and MAJOR-E (1): the admission must be one `--admit` wrote and a committed version
    # showed RUNNING. Judged for every non-pre-gate row whose receipt or cleanup is judged (DONE, INVALID, overdue
    # RUNNING, and V2 CLOSED_NO_LAUNCH). The committed programs are read only when such a row carries an admission.
    judged = [s for s in slots if s["id"] not in PRE_GATE_DONE
              and (s["status"] in ("DONE", "INVALID", "CLOSED_NO_LAUNCH") or s["id"] in overdue)]
    programs = set()
    if any(isinstance(s.get("admission"), dict) for s in judged):
        programs = {sha256(raw) for _commit, raw in git.history(program_name or PROGRAM_FILE.name)}
    provenance = {s["id"]: admission_provenance(s, history, programs) for s in judged}
    # Round 4 MAJOR-H (b), V2 R3: look for launch attempts a judged row does not list (pre-gate rows by their criteria).
    scanner = AttemptScanner(git, root)

    def listed_specs(s):
        return [spec for _label, spec, _res in entries.get(s["id"], [])] + (
            [closure_specs[s["id"]]] if s["id"] in closure_specs else [])
    claimed = {}            # V2 R3: (path, sha256) -> the rows whose listed training receipts account for that file
    for s in slots:
        files, _failures = listed_files(scanner, [x for x in listed_specs(s) if x.get("kind") != "watched_machine"])
        for key in files:
            claimed.setdefault(key, set()).add(s["id"])
    claims = {"files": claimed, "keys": owners}
    unlisted = {s["id"]: unlisted_attempts(
        s, listed_specs(s), {v for _l, _sp, res in entries.get(s["id"], []) for n, v in res["keys"] if n == "instance_id"},
        scanner, claims) for s in slots if s["status"] in ("DONE", "INVALID", "CLOSED_NO_LAUNCH") or s["id"] in overdue}
    closures = {s["id"]: closure_proof(s, git) for s in slots if s["status"] == "CLOSED_NO_LAUNCH"}
    rows, spent, rejected, unconfirmed = [], Decimal("0"), [], []
    for slot in slots:
        sid, status, cap = slot["id"], slot["status"], info[slot["id"]]["cap"]
        items, multi = entries.get(sid, []), slot.get("attempts") is not None
        prior = slot["cap_basis"]["kind"] == "prior_spend"
        problems = [("%s: %s" % (attempt_name(label), p)) if multi else p
                    for label, _spec, res in items for p in res["problems"]]
        if status == "DONE" and multi and canonical(slot["receipt"]) != canonical(slot["attempts"][-1]):
            problems.append("RECEIPT_NOT_THE_LAST_LISTED_ATTEMPT: at DONE the row's receipt is its last launch attempt")
        if status == "DONE" and isinstance(slot.get("admission"), dict):
            problems.extend(provenance.get(sid, ()))    # at DONE a record that fails is a rejection reason
        row = {"slot": sid, "what": slot.get("what"), "status": status, "mandatory": slot["mandatory"],
               "cap_usd": str(cap), "basis_worst_case_usd": str(up(info[sid]["worst"])),
               "basis_arithmetic": info[sid]["text"]}
        if slot.get("attempt_of"):                      # V2 R1: an attempt row
            row.update(attempt_of=slot["attempt_of"], attempt=slot["attempt"])
        closing_gap = []
        if status == "DONE" and not problems:
            counted, why = summed(cap, items, multi, trusted=True)
            pins = ({attempt_name(label): res["pins"] for label, _spec, res in items} if multi else items[0][2]["pins"])
            row.update(receipt="DECLARED_PRIOR_SPEND" if prior else "ACCEPTED", counted_usd=str(counted),
                       counted_basis=why, receipt_pins=pins)
        elif status == "DONE":
            rejected.append(sid)
            counted, why = summed(cap, items, multi, trusted=False)
            row.update(receipt="REJECTED", receipt_problems=problems, counted_usd=str(counted),
                       counted_basis="receipt rejected: the larger of the cap and every cost figure it shows: " + why)
        elif status == "INVALID":
            counted, why = summed(cap, items, multi, trusted=False)
            row.update(receipt="INVALID", counted_usd=str(counted),
                       counted_basis="INVALID (%s): the larger of the cap and every cost figure its receipt shows: %s" % (
                           slot["invalid_reason"], why))
            if problems:
                row["receipt_problems"] = problems
        elif status == "RUNNING":
            pinned = receipt_has_pins(slot["receipt"])
            current = next((res for _label, spec, res in items if pinned and canonical(spec) == canonical(slot["receipt"])),
                           None)
            counted, why = counted_at_least_cap(cap, current)
            earlier = [item for item in items if item[2] is not current]
            text = "RUNNING: full cap" if current is None else ("RUNNING: the larger of the full cap and every cost "
                                                               "figure its receipt shows: " + why)
            if earlier:     # round 4 MAJOR-H: the attempt in progress at its cap, plus every earlier attempt
                value, earlier_text = summed(cap, earlier, True, trusted=True)
                counted += value
                text = "%s (the attempt in progress); earlier attempts: %s; total $%s" % (text, earlier_text, counted)
            row.update(receipt="NOT_FINAL", counted_usd=str(counted), counted_basis=text,
                       admission=slot.get("admission") or "MISSING: set RUNNING by hand, not by --admit")
            if sid in overdue:
                row["lifetime"] = ("PAST: admission time + %d s of its basis has passed (or the admission time is "
                                   "unreadable)" % lifetime_seconds(slot["cap_basis"]))
        elif status == "CANCELLED_NOT_LAUNCHED":        # V2 R7 (Codex Q7)
            row.update(receipt="NOT_APPLICABLE", counted_usd="0.00", cancellation=slot["cancellation"],
                       counted_basis="CANCELLED_NOT_LAUNCHED: never admitted, never launched; $0.00; %s" % (
                           "mandatory: its cap stays reserved, the registered comparison is COMPARISON_INCOMPLETE and "
                           "every main admission is refused" if slot["mandatory"] else
                           "optional: its cap leaves fallback B"))
        elif status == "CLOSED_NO_LAUNCH":              # V2 R1 / R5
            closing_gap = list(provenance.get(sid, ())) + closures.get(sid, [])
            if closing_gap or unlisted.get(sid):
                row.update(receipt="CLOSED_NO_LAUNCH_UNPROVEN", counted_usd=str(cap),
                           counted_basis="CLOSED_NO_LAUNCH without proof that no instance was created: the full cap")
            else:
                row.update(receipt="CLOSED_NO_LAUNCH", counted_usd="0.00",
                           counted_basis="CLOSED_NO_LAUNCH (%s): admitted, no instance created: the search of its "
                                         "admission window found no launch%s; $0.00" % (
                                             slot["closure"]["reason"],
                                             "; its pinned prelaunch-failure receipt shows no launch, no instance and "
                                             "no RunInstances call" if sid in closure_specs else ""))
            row.update(closure=slot["closure"], admission=slot["admission"])
        else:
            row.update(receipt="NOT_APPLICABLE", counted_usd="0.00",
                       counted_basis="PLANNED: nothing spent; cap %s" % ("reserved" if slot["mandatory"] else "not reserved (optional)"))
        if multi:
            row["attempts"] = [dict({"attempt": attempt_name(label), "receipt": attempt_where(spec)},
                                    **({"problems": res["problems"]} if res["problems"] else {})) for label, spec, res in items]
        gaps = []
        if prior:
            row["cleanup_note"] = ("NOT CHECKED BY THIS PROGRAM: a declared prior-spend row (V2 R9); those jobs' own "
                                   "watchers recorded their cleanup")
        elif status in ("DONE", "INVALID") or sid in overdue:     # round 2 MAJOR-A, round 3 MAJOR-E: fail closed
            if not items:
                gaps.append("no readable receipt")
            for label, spec, res in items:      # round 4 MAJOR-H (a): every attempt on its own
                gap = cleanup_gap(res, label in shared_labels or sid in shared_labels, provenance.get(sid, ()))
                if gap:
                    gaps.append("%s (%s): %s" % (attempt_name(label), attempt_where(spec), gap) if multi else gap)
            if status == "RUNNING" and items and not receipt_has_pins(slot["receipt"]):
                gaps.append("the attempt in progress names no receipt")
        elif status == "CLOSED_NO_LAUNCH" and closing_gap:
            gaps.append("the closure does not prove that no instance was created: " + "; ".join(closing_gap))
        if unlisted.get(sid):                   # round 4 MAJOR-H (b), V2 R3
            gaps.append("the search for launch attempts not listed in its row (every attempt belongs in its own row) "
                        "found: " + "; ".join(unlisted[sid]))
        if gaps:
            unconfirmed.append(sid)
            row["cleanup"] = ("UNCONFIRMED (%s): a machine or disk of this slot may still exist; stop and report to the "
                              "owner" % "; ".join(gaps))
        for key in ("scope", "runtime_bound", "cleanup_bound", "timing_feasibility", "training"):
            if key in slot:
                row[key] = slot[key]
        row["preconditions_outside_money_gate"] = preconditions(slot)
        spent += Decimal(row["counted_usd"])
        rows.append(row)
    # V2 R7: a cancelled mandatory row's cap stays reserved (only an optional row's cap is released).
    reserved = [s for s in slots if s["mandatory"] and s["status"] in ("PLANNED", "CANCELLED_NOT_LAUNCHED")]
    reserve = sum((info[s["id"]]["cap"] for s in reserved), Decimal("0"))
    # V2 R6 (Codex Q3/Q6): every main attempt whose verified receipt, bound to its admission, shows a launched instance
    # counts, accepted or not; a proven capacity refusal or a proven CLOSED_NO_LAUNCH does not; anything else is an
    # uncertain start, which blocks.
    started, uncertain = [], []
    for s in slots:
        if not s["counts_toward_training_stop"]:
            continue
        if s["status"] in ("DONE", "INVALID"):
            for label, _spec, res in entries[s["id"]]:
                if res["not_this_launch"] == [] and res["proven_refusal"]:
                    continue
                if res["verified"] and res["not_this_launch"] == [] and res["instance_shown"]:
                    started.append(label)
                else:
                    uncertain.append(label)
        elif s["status"] == "CLOSED_NO_LAUNCH" and s["id"] in unconfirmed:
            uncertain.append(s["id"])
    # V2 R5 (Codex Q4) and R1 (Q9): a limit breach, or a second attempt under one admission, latches the study shut.
    breaches, wrong_identity = {}, {}
    for s in slots:
        if s["status"] not in ("RUNNING", "DONE", "INVALID") or s["cap_basis"]["kind"] == "prior_spend":
            continue
        cap, found, extra = info[s["id"]]["cap"], [], s.get("attempts") or []
        if len(extra) > (0 if s["status"] == "RUNNING" else 1):
            found.append("MORE_THAN_ONE_ATTEMPT_UNDER_ONE_ADMISSION:%d listed%s (one admission authorizes one "
                         "RunInstances attempt)" % (len(extra), " plus the one in progress" if s["status"] == "RUNNING" else ""))
        for label, _spec, res in entries[s["id"]]:
            over = [up(value) for value, _what in res["figures"] if up(value) > cap]
            if over:
                found.append("%s: MONEY_OVER_CAP:$%s > cap $%s" % (label, max(over), cap))
            found.extend("%s: %s" % (label, p) for p in res["problems"] if p.startswith(BREACH_CODES))
            if res["identity_problems"]:
                wrong_identity.setdefault(s["id"], []).extend("%s: %s" % (label, p) for p in res["identity_problems"])
        if found:
            breaches[s["id"]] = found
    return {"rows": rows, "spent": spent, "rejected": rejected, "shared": shared, "unconfirmed": unconfirmed,
            "reserve": reserve, "planned_mandatory": [s["id"] for s in reserved],
            "optional": [s for s in slots if s["status"] == "PLANNED" and not s["mandatory"]],
            "running": [s["id"] for s in slots if s["status"] == "RUNNING"], "training_started": started,
            "uncertain": uncertain, "breaches": breaches, "wrong_identity": wrong_identity,
            "comparison_incomplete": [s["id"] for s in slots if s["status"] == "CANCELLED_NOT_LAUNCHED" and s["mandatory"]]}


def preconditions(slot):
    listed = slot.get("preconditions_outside_money_gate")
    return listed if listed else "NOT ASSESSED: no precondition list for this slot; do not read ADMIT as ready"


def inventory_sha256(loaded, acct, program_sha):
    """V2 R2 (Codex R3-F): one hash of everything an admission decision rests on: the gate version and program, the
    slots document (canonical, as it was before the admission is written) and the recomputed account (every row's
    count, pins, problems, cleanup and search findings; the totals; every stop)."""
    summary = {"gate_version": GATE_VERSION, "program_sha256": program_sha,
               "slots_canonical_sha256": sha256(canonical(loaded["doc"])), "rows": acct["rows"],
               "spent": str(acct["spent"]), "reserve": str(acct["reserve"])}
    for key in ("rejected", "shared", "unconfirmed", "training_started", "uncertain", "breaches", "wrong_identity",
                "comparison_incomplete", "running"):
        summary[key] = acct.get(key)
    return sha256(canonical(summary))


def admit(slot_id, loaded, acct, source=None, bundle=None, worker=None, checker=None, preview=False, uncommitted=(),
          remote=None, lock_problem=None):
    slots, info = {s["id"]: s for s in loaded["slots"]}, loaded["info"]
    if slot_id not in slots:
        raise InputError("no slot named %r" % slot_id)
    slot, reasons = slots[slot_id], []
    cap, kind = info[slot_id]["cap"], slot["cap_basis"]["kind"]
    if not preview:
        if not (isinstance(source, str) and COMMIT.match(source)):
            raise InputError("--source <the 40-hex source commit this slot will launch> is required")
        for flag, value in (("--bundle", bundle), ("--worker", worker), ("--checker", checker)):
            if not (isinstance(value, str) and SHA.match(value)):
                raise InputError("%s <64-hex sha256> is required for every slot (V2 R4, Codex Q8: the admission binds the "
                                 "source, bundle, worker and checker)" % flag)
    if lock_problem:                                     # V2 R2
        reasons.append(lock_problem)
    if acct["rejected"]:
        reasons.append("DONE_RECEIPT_REJECTED:%s" % ",".join(acct["rejected"]))
    if acct["shared"]:
        reasons.append("RECEIPT_SHARED:%s" % "; ".join("%s by %s" % (k, ",".join(v)) for k, v in acct["shared"].items()))
    if acct["unconfirmed"]:
        reasons.append("CLEANUP_UNCONFIRMED_STOP_AND_REPORT:%s" % ",".join(acct["unconfirmed"]))
    if acct.get("breaches"):                             # V2 R5 (Codex Q4), R1 (Q9)
        reasons.append("LIMIT_BREACH_LATCHED:%s: a job went past an admitted limit (or a second attempt ran under one "
                       "admission); every admission stays refused, even after its cleanup: stop and report (Codex Q4)"
                       % ",".join(sorted(acct["breaches"])))
    if acct.get("wrong_identity"):                       # V2 R4 (Codex Q8)
        reasons.append("WRONG_IDENTITY_BLOCKS_THE_STUDY:%s: a receipt does not show the admitted source, bundle, worker "
                       "or checker; its result is INVALID and new study admissions are blocked (Codex Q8)"
                       % ",".join(sorted(acct["wrong_identity"])))
    if acct.get("uncertain"):                            # V2 R6 (Codex Q3/Q6)
        reasons.append("MAIN_START_UNCERTAIN:%s: whether a main attempt started an instance is not proven; an uncertain "
                       "start blocks (Codex Q3/Q6)" % ",".join(acct["uncertain"]))
    if acct.get("comparison_incomplete") and slot["counts_toward_training_stop"]:   # V2 R7 (Codex Q7)
        reasons.append("COMPARISON_INCOMPLETE:%s cancelled: every main admission is refused (Codex Q7)"
                       % ",".join(acct["comparison_incomplete"]))
    if slot["status"] != "PLANNED":
        reasons.append("SLOT_NOT_PLANNED:%s" % slot["status"])
    if acct["running"]:
        reasons.append("ONE_MACHINE_AT_A_TIME:RUNNING=%s" % ",".join(acct["running"]))
    if uncommitted:
        reasons.append("UNCOMMITTED_CHANGES:%s: commit them first, so every DONE receipt is in git history before the "
                       "next machine starts" % ",".join(uncommitted))
    if remote is not None and not remote[0]:        # round 4 N8
        reasons.append("NOT_AT_THE_FETCHED_REMOTE_TIP:%s: git pull --ff-only (and push), then run --admit again" % remote[1])
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
    arithmetic = "spent upper bound $%s + %s cap $%s%s + other mandatory caps $%s (%s) = $%s vs ceiling $%s" % (
        acct["spent"], slot_id, cap, " (the replacement cap of attempt %d of %s)" % (slot["attempt"], slot["attempt_of"])
        if slot.get("attempt_of") else "", others,
        ",".join(i for i in acct["planned_mandatory"] if i != slot_id) or "none", total, CEILING_USD)
    if total > CEILING_USD:
        reasons.append("OVER_CEILING:$%s > $%s" % (total, CEILING_USD))
    starts = acct["training_started"]
    stop = len(starts) < STOP_BEFORE_TRAINING_JOB and acct["spent"] > STOP_USD
    stop_text = "spent upper bound $%s %s $%s with %d of %d main training attempts started (%s)" % (
        acct["spent"], ">" if acct["spent"] > STOP_USD else "<=", STOP_USD,
        len(starts), STOP_BEFORE_TRAINING_JOB, ",".join(starts) or "none")
    if stop:
        reasons.append("OWNER_STOP_TRIGGERED:stop and report:%s" % stop_text)
    return {"slot": slot_id, "decision": "REFUSE" if reasons else "ADMIT", "reasons": reasons,
            "admission_arithmetic": arithmetic, "total_usd": str(total), "cap_usd": str(cap),
            "remaining_mandatory_reserve_usd": str(others), "cumulative_upper_bound_usd": str(acct["spent"]),
            "main_starts": len(starts),
            "owner_stop": ("TRIGGERED: " if stop else "not triggered: ") + stop_text,
            "started_counts": "every main attempt whose hash-verified receipt, bound to its admission, shows a launched "
                              "instance, accepted or not, failed or repeated; never a proven capacity refusal or a proven "
                              "CLOSED_NO_LAUNCH; an uncertain start blocks (Codex Q3/Q6)",
            "money_basis": MONEY_BASIS,
            "gate_scope": "money ceiling, owner stop, limit and identity latches, one machine at a time, committed state "
                          "and receipt validity ONLY; technical readiness (reviews, builds) is a separate admission and "
                          "is NOT checked here",
            "preconditions_outside_money_gate": preconditions(slot)}


def write_admission(slots_file, loaded, slot_id, record, frozen):
    """Set the row RUNNING with its admission record, in one atomic write (review MINOR: --admit leaves a record)."""
    path = pathlib.Path(slots_file)
    if sha256(path.read_bytes()) != loaded["sha256"]:
        raise InputError("the slots file changed while the decision was made; nothing was written")
    doc = json.loads(loaded["raw"])
    hits = [r for r in all_rows(doc) if r.get("id") == slot_id]         # V2 R1: a slot row or an attempt row
    if len(hits) != 1:
        raise InputError("no single row named %r to admit" % slot_id)
    hits[0]["status"], hits[0]["admission"] = "RUNNING", record
    partial = path.with_name(path.name + ".partial")
    partial.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    os.replace(partial, path)
    again = load_slots(path, frozen)
    if again["digest"] != loaded["digest"]:
        raise InputError("definitions changed while writing the admission")
    return again["sha256"]


# -------------------------------------------------------------------------------- V2 R2: the single-writer lock
def read_lock(lock_path):
    """The lock's content, None when there is no lock, or {"state": "UNREADABLE"}."""
    try:
        held = json.loads(pathlib.Path(lock_path).read_bytes())
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {"state": "UNREADABLE"}
    return held if isinstance(held, dict) else {"state": "UNREADABLE"}


def write_lock(lock_path, content):
    partial = pathlib.Path(str(lock_path) + ".partial")
    partial.write_bytes(canonical(content))
    os.replace(partial, lock_path)


def acquire_lock(lock_path, loaded, slot_id, now_text):
    """Take the single-writer admission lock: (True, nonce) or (False, why). A lock left by an admission whose row is
    settled (no longer RUNNING, same nonce) is released first; any other lock refuses. A lock no gate owns (a crash)
    is removed by hand, only after checking that no gate process runs."""
    held = read_lock(lock_path)
    if held is not None:
        holder = {s["id"]: s for s in loaded["slots"]}.get(held.get("slot"))
        settled = (held.get("state") in ("ADMITTED", "LAUNCH_CHECKED") and holder is not None
                   and holder["status"] != "RUNNING"
                   and obj(holder.get("admission")).get("lock_nonce") == held.get("nonce"))
        if not settled:
            return False, ("LOCK_HELD:%s holds %s (state %s): another admission is open or another gate process is "
                           "deciding" % (held.get("slot"), LOCK_NAME, held.get("state")))
        pathlib.Path(lock_path).unlink()
    nonce = os.urandom(16).hex()
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False, "LOCK_HELD: another gate process took %s just now" % LOCK_NAME
    with os.fdopen(fd, "wb") as handle:
        handle.write(canonical({"slot": slot_id, "nonce": nonce, "state": "DECIDING", "since_utc": now_text}))
    return True, nonce


def launch_check(slot_id, loaded, history, git, root, lock_path, now, program_file, uncommitted, remote):
    """V2 R2 (Codex R3-F): the recomputation immediately before the ONE RunInstances call an admission authorizes.
    LAUNCH_ONCE only if the admission's lock is still held, unused, inside its 300-s validity, committed and pushed as
    written, and the recomputed pre-admission inventory hash equals the admitted one. It then marks the lock used."""
    rows = {s["id"]: s for s in loaded["slots"]}
    if slot_id not in rows:
        raise InputError("no slot named %r" % slot_id)
    slot, reasons = rows[slot_id], []
    a = slot.get("admission") if isinstance(slot.get("admission"), dict) else None
    if slot["status"] != "RUNNING" or a is None:
        return {"slot": slot_id, "decision": "REFUSE", "reasons": ["NOT_AN_OPEN_ADMISSION:%s is %s" % (slot_id, slot["status"])]}
    held = read_lock(lock_path)
    if held is None:
        reasons.append("LOCK_LOST:%s is gone: a fresh check is needed (close this admission as CLOSED_NO_LAUNCH, then "
                       "admit the next attempt row)" % LOCK_NAME)
    elif held.get("slot") != slot_id or held.get("nonce") != a.get("lock_nonce"):
        reasons.append("LOCK_LOST:%s is held by another admission (%s)" % (LOCK_NAME, held.get("slot")))
    elif held.get("state") == "LAUNCH_CHECKED":
        reasons.append("ADMISSION_ALREADY_USED:its one launch check passed at %s; one admission authorizes one "
                       "RunInstances attempt (Codex Q9)" % held.get("checked_utc"))
    elif held.get("state") != "ADMITTED":
        reasons.append("LOCK_LOST:%s is in state %r" % (LOCK_NAME, held.get("state")))
    admitted = utc(a.get("admitted_utc"))
    if admitted is None or now >= validity_end(admitted):
        reasons.append("ADMISSION_EXPIRED:now %s, valid until %s (%d s, Codex R3-F): close it as CLOSED_NO_LAUNCH with "
                       "proof of no launch, then admit the next attempt row" % (
                           fmt(now), a.get("valid_until_utc"), ADMISSION_VALIDITY_SECONDS))
    program_sha = sha256(pathlib.Path(program_file).read_bytes())
    if program_sha != a.get("program_sha256"):
        reasons.append("PROGRAM_CHANGED:%s is not the admitting program %s" % (program_sha, a.get("program_sha256")))
    programs = {sha256(raw) for _commit, raw in git.history(pathlib.Path(program_file).name)}
    provenance = admission_provenance(slot, history, programs)
    if provenance:
        reasons.append("ADMISSION_NOT_COMMITTED_AS_WRITTEN:%s" % "; ".join(provenance))
    if uncommitted:
        reasons.append("UNCOMMITTED_CHANGES:%s" % ",".join(uncommitted))
    if remote is not None and not remote[0]:
        reasons.append("NOT_AT_THE_FETCHED_REMOTE_TIP:%s: push the RUNNING row before the launch" % remote[1])
    doc = json.loads(loaded["raw"])          # the pre-admission state: this row as it was before --admit wrote it
    for row in all_rows(doc):
        if row.get("id") == slot_id:
            row["status"] = "PLANNED"
            row.pop("admission", None)
    before = parse_slots(json.dumps(doc).encode("utf-8"), frozen=None)
    recomputed = inventory_sha256(before, account(before, root, git, history=history, now=now,
                                                  program_name=pathlib.Path(program_file).name), a.get("program_sha256"))
    if recomputed != a.get("inventory_sha256"):
        reasons.append("INPUT_CHANGED:the recomputed inventory %s is not the admitted %s: a source, receipt or state "
                       "hash changed since the admission; a fresh check is needed" % (recomputed, a.get("inventory_sha256")))
    decision = {"slot": slot_id, "decision": "REFUSE" if reasons else "LAUNCH_ONCE", "reasons": reasons,
                "admitted_utc": a.get("admitted_utc"), "valid_until_utc": a.get("valid_until_utc"), "now_utc": fmt(now),
                "inventory_sha256": recomputed,
                "rule": "exit 0 authorizes exactly ONE RunInstances attempt, now; any retry needs its own attempt row "
                        "and its own --admit (Codex Q9)"}
    if not reasons:
        write_lock(lock_path, dict(held, state="LAUNCH_CHECKED", checked_utc=fmt(now)))
    return decision


def state_document(loaded, acct):
    spent, doc = acct["spent"], loaded["doc"]
    plan_total = spent + acct["reserve"]
    fallback = sum((loaded["info"][s["id"]]["cap"] for s in acct["optional"]), Decimal("0"))
    sensitivity = {r["slot"]: str(plan_total - Decimal(r["counted_usd"]) + max(
        Decimal(r["cap_usd"]) * len(r.get("attempts") or [None]), Decimal(r["counted_usd"])))     # a full cap per attempt
                   for r in acct["rows"] if r["status"] == "DONE"}
    previews = {s["id"]: admit(s["id"], loaded, acct, preview=True) for s in loaded["slots"] if s["status"] == "PLANNED"}
    prior = [s for s in loaded["slots"] if s["cap_basis"]["kind"] == "prior_spend"]
    prior_counted = sum((Decimal(r["counted_usd"]) for r in acct["rows"] if r["slot"] in {s["id"] for s in prior}),
                        Decimal("0"))
    prior_jobs = sum(len(s["cap_basis"]["items"]) for s in prior)
    return {"schema": "claude.helm-repair-controlled-1.study-spend/0.4", "label": "CLAUDE_BUILT_CLAUDE_CHECKED",
            "gate_version": GATE_VERSION,
            "inputs": {"slots_file": "STUDY_SLOTS.json", "slots_file_sha256": loaded["sha256"],
                       "definitions_sha256": loaded["digest"]},
            "frozen_in_code": {"ceiling_usd": str(CEILING_USD), "owner_stop_usd": str(STOP_USD),
                               "owner_stop_before_training_job": STOP_BEFORE_TRAINING_JOB,
                               "s3_transfer_allowance_per_job_usd": str(ALLOWANCE_USD),
                               "admission_validity_seconds": ADMISSION_VALIDITY_SECONDS,
                               "definitions_sha256": FROZEN_DEFINITIONS_SHA256, "pre_gate_done_rows": list(PRE_GATE_DONE)},
            "money_basis": MONEY_BASIS,
            "spent_upper_bound_usd": str(spent), "prior_spend_counted_usd": str(prior_counted),
            "rejected_done_receipts": acct["rejected"], "shared_receipt_identities": acct["shared"],
            "cleanup_unconfirmed": acct["unconfirmed"], "limit_breaches_latched": acct["breaches"],
            "wrong_identity_blocks": acct["wrong_identity"], "main_starts_uncertain": acct["uncertain"],
            "comparison_incomplete": acct["comparison_incomplete"],
            "training_jobs_started": acct["training_started"], "main_starts": len(acct["training_started"]),
            "slots": acct["rows"],
            "remaining_mandatory_slots": acct["planned_mandatory"],
            "remaining_mandatory_caps_usd": str(acct["reserve"]),
            "plan_C_worst_case_total_usd": str(plan_total), "plan_C_fits_ceiling_at_worst_case": plan_total <= CEILING_USD,
            "headroom_usd": str(CEILING_USD - plan_total),
            "plan_C_is_final": False,
            "plan_C_not_final_because": ("Codex 'Envelope consequences' (c3a128ee): this is program output, not an invoice "
                                         "or an accepted final envelope. P1b is still priced as a T4 job (Codex: it runs "
                                         "on the historical g7 environment and needs its own priced launcher); E1's real "
                                         "scope, retention past 12 months and request / transfer charges are not yet "
                                         "reconciled; the prior-spend row is included pending the owner's scope decision"),
            "plan_C_if_each_prior_job_also_got_the_0.10_allowance_usd": str(plan_total + ALLOWANCE_USD * prior_jobs),
            "fallback_B_slots": [s["id"] for s in acct["optional"]], "fallback_B_extra_caps_usd": str(fallback),
            "fallback_B_fits_at_worst_case": plan_total + fallback <= CEILING_USD,
            "plan_C_total_if_this_DONE_slot_were_counted_at_its_full_cap_usd": sensitivity,
            "money_gate_preview_not_an_admission": previews,
            "open_questions": doc.get("open_questions_for_owner_or_codex"),
            "rules": {"admission": "row PLANNED (a slot row, or an appended attempt row); nothing RUNNING; the single-"
                                   "writer lock taken; no DONE receipt rejected; no receipt identity shared; no "
                                   "unconfirmed cleanup; no limit breach, wrong identity or uncertain main start; no "
                                   "cancelled mandatory row for a main admission; slots file and program committed and "
                                   "at the fetched remote tip; spent upper bound + this cap + every other reserved "
                                   "mandatory cap (E1 included) <= ceiling; owner stop not triggered; one source per "
                                   "training arm. ADMIT writes the row RUNNING with its admission record, valid 300 s, "
                                   "single use; run --launch-check immediately before the one RunInstances attempt",
                      "owner_stop": doc["owner_stop"]["rule"],
                      "rounding": "every bound rounded UP to the cent; exact decimals, no floats"},
            "meta1_ledger": "not read or written by this program"}


def main(argv=None, git=None, root=ROOT, slots_file=SLOTS_FILE, state_file=STATE_FILE,
         frozen=FROZEN_DEFINITIONS_SHA256, program_file=PROGRAM_FILE, now=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--admit", metavar="SLOT", help="decide one admission; exit 0 ADMIT (row written RUNNING), "
                                                        "1 REFUSE, 2 error")
    parser.add_argument("--launch-check", metavar="SLOT", help="V2 R2: run immediately before RunInstances; exit 0 "
                                                               "LAUNCH_ONCE, 1 REFUSE, 2 error")
    parser.add_argument("--source", metavar="COMMIT", help="with --admit: the 40-hex source commit the slot launches")
    parser.add_argument("--bundle", metavar="SHA256", help="with --admit: the reviewed bundle sha256 (every slot, V2 R4)")
    parser.add_argument("--worker", metavar="SHA256", help="with --admit: the reviewed worker sha256 (V2 R4)")
    parser.add_argument("--checker", metavar="SHA256", help="with --admit: the reviewed checker sha256 (V2 R4)")
    parser.add_argument("--no-write", action="store_true", help="report mode: do not write STUDY_SPEND_STATE.json")
    args = parser.parse_args(argv)
    git = git or GitReader()
    lock_path = pathlib.Path(slots_file).with_name(LOCK_NAME)
    names = [pathlib.Path(slots_file).name, pathlib.Path(program_file).name]
    program_name = pathlib.Path(program_file).name
    acquired = False
    try:
        when = utc(now) if now else datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        if when is None:
            raise InputError("now must look like 2026-09-24T12:00:00Z")
        loaded = load_slots(slots_file, frozen)
        history = git.history(pathlib.Path(slots_file).name)
        check_history(loaded["doc"], history)
        if args.launch_check:
            decision = launch_check(args.launch_check, loaded, history, git, root, lock_path, when, program_file,
                                    git.uncommitted(names), git.at_remote_tip())
            print(json.dumps(decision, indent=1))
            return 0 if decision["decision"] == "LAUNCH_ONCE" else 1
        lock = None
        if args.admit:              # V2 R2: the decision is recomputed under the single-writer lock
            lock = acquire_lock(lock_path, loaded, args.admit, fmt(when))
            acquired = lock[0]
        acct = account(loaded, root, git, history=history, now=when, program_name=program_name)
        if args.admit:
            remote = git.at_remote_tip()        # round 4 N8: fetch first; HEAD must be the remote tip
            decision = admit(args.admit, loaded, acct, source=args.source, bundle=args.bundle, worker=args.worker,
                             checker=args.checker, uncommitted=git.uncommitted(names), remote=remote,
                             lock_problem=None if acquired else lock[1])
            decision.update(remote_tip=remote[1], spent_upper_bound_usd=str(acct["spent"]), slots_file_sha256=loaded["sha256"],
                            definitions_sha256=loaded["digest"],
                            receipts={r["slot"]: r.get("receipt_pins") or r.get("receipt_problems")
                                      for r in acct["rows"] if r["status"] == "DONE"},
                            open_questions=loaded["doc"].get("open_questions_for_owner_or_codex"))
            if decision["decision"] == "ADMIT":
                slot = next(s for s in loaded["slots"] if s["id"] == args.admit)
                program_sha = sha256(pathlib.Path(program_file).read_bytes())
                record = {"slot": args.admit, "attempt": slot.get("attempt", 1), "gate": ADMIT_GATE,
                          "gate_version": GATE_VERSION, "admitted_utc": fmt(when),
                          "valid_until_utc": fmt(validity_end(when)),
                          "single_use": "one RunInstances attempt; run --launch-check immediately before it",
                          "slots_sha256_before": loaded["sha256"], "definitions_sha256": loaded["digest"],
                          "program_sha256": program_sha, "inventory_sha256": inventory_sha256(loaded, acct, program_sha),
                          "lock_nonce": lock[1], "source_sha": args.source, "bundle_sha256": args.bundle,
                          "worker_sha256": args.worker, "checker_sha256": args.checker, "cap_usd": decision["cap_usd"],
                          "remaining_mandatory_reserve_usd": decision["remaining_mandatory_reserve_usd"],
                          "cumulative_upper_bound_usd": str(acct["spent"]),
                          "main_starts": len(acct["training_started"]),
                          "admission_arithmetic": decision["admission_arithmetic"]}
                if slot["cap_basis"]["kind"] == "training_pointer":
                    record.update(model_seed=slot["training"]["model_seed"], arm=slot["training"]["arm"])
                decision["slots_file_sha256_after"] = write_admission(slots_file, loaded, args.admit, record, frozen)
                write_lock(lock_path, {"slot": args.admit, "nonce": lock[1], "state": "ADMITTED",
                                       "admitted_utc": record["admitted_utc"], "valid_until_utc": record["valid_until_utc"]})
                acquired = False            # the lock stays with the open admission until its row is settled
                decision["admission_record"] = record
                decision["recorded"] = ("row set RUNNING in STUDY_SLOTS.json with this admission record; commit and "
                                        "push it, run --launch-check, and launch once, all before valid_until_utc")
            print(json.dumps(decision, indent=1))
            return 0 if decision["decision"] == "ADMIT" else 1
        state = state_document(loaded, acct)
    except Exception as error:                  # fail closed: any error is exit 2, never a silent admit or refuse
        print(json.dumps({"decision": "ERROR", "error": "%s: %s" % (type(error).__name__, error)}))
        return 2
    finally:
        if acquired:                            # a refusal or an error releases the lock it took
            try:
                lock_path.unlink()
            except OSError:
                pass
    if not args.no_write:
        pathlib.Path(state_file).write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: state[k] for k in ("spent_upper_bound_usd", "prior_spend_counted_usd",
                                            "remaining_mandatory_caps_usd", "plan_C_worst_case_total_usd",
                                            "plan_C_fits_ceiling_at_worst_case", "headroom_usd", "plan_C_is_final",
                                            "fallback_B_extra_caps_usd", "fallback_B_fits_at_worst_case",
                                            "rejected_done_receipts", "shared_receipt_identities", "cleanup_unconfirmed",
                                            "limit_breaches_latched", "wrong_identity_blocks", "main_starts_uncertain",
                                            "comparison_incomplete", "training_jobs_started")}, indent=1))
    for row in state["slots"]:
        print("%-5s %-8s counted $%-6s cap $%-6s %s" % (row["slot"], row["status"], row["counted_usd"], row["cap_usd"],
                                                        row.get("receipt_problems") or row["counted_basis"]))
    for sid, d in state["money_gate_preview_not_an_admission"].items():
        print("money gate preview for %-5s -> %s %s" % (sid, d["decision"], "; ".join(d["reasons"])))
    return 1 if (acct["rejected"] or acct["shared"] or acct["unconfirmed"] or acct["breaches"] or acct["wrong_identity"]
                 or acct["uncertain"]) else 0


if __name__ == "__main__":
    sys.exit(main())
