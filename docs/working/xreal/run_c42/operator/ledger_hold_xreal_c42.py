"""Place a SOURCE_BOUND_SINGLE_ATTEMPT_RESERVATION of 1.00 USD for job helm-claude-xreal-20261019-c42, bound to the
sealed X-REAL zip (a9b4c954). Authority: the owner's pre-approval line (APPROVAL_RECORD_XREAL.md; line sha256 2a8a6f86,
121 bytes, "...X-REAL at 1 USD...") under the owner's 200 USD ceiling ruling. Derived from ledger_hold_r1w5_c40.py by
substitution (derive_ledger_hold_c42.py). Placed only when the last HISTORY line is the c41 (Scribe L4) closeout; the
before value is read from the pointer at that moment (sha-checked twice). No other hold touched; ceiling unchanged.
Read-modify-write with checks; atomic writes; one history line.

Usage: python -B ledger_hold_xreal_c42.py <expected pointer sha256 as just read by the operator>"""
import datetime, hashlib, json, os, sys, uuid
from pathlib import Path

CODEX = Path(r"C:\Users\wakil\Documents\Codex")
CURRENT = CODEX / "AWS_COMBINED_ALLOCATION_CURRENT.json"
HISTORY = CODEX / "AWS_COMBINED_ALLOCATION_HISTORY.jsonl"
PREP = CODEX / "2026-10-01" / "task-2" / "helm_operator_preparation"
RULING = PREP / "budget_ceiling_review_20261014_r1" / "OWNER_CEILING_RULING_20261014.md"
RULING_SHA = "701e6832ba5a248e2ee9b7c8e526b48e95fc8da0c58278de2e6ccad1ed68e8e2"
XR = CODEX / "2026-10-19" / "x_real"
APPROVAL = XR / "APPROVAL_RECORD_XREAL.md"
APPROVAL_SHA = "8592702c5389e6fa88b5e5005ba99d63460c1133a3965337e622341ae61b185c"
OPERATOR_RECORD = PREP / "OWNER_APPROVAL_XREAL_20261020T000138Z.json"
OPERATOR_RECORD_SHA = "6b4799b22750ca1c0c3050588f2364a66fc743c9ba0cd2245e9dc627399c4d6e"
CURRENT_SHA_EXPECTED = sys.argv[1]
ZIP = XR / "HELM_XREAL_20261019_SOURCE_XREAL.zip"
ZIP_SHA = "a9b4c9547e7276412a95141d24eb38d7d44ca3d539e8ff095abe727cf4e1c249"
FREEZE_SHA = "67b485415078ca11c5c3d984cd3f82a6a1ab1f111efc9ce2a619d3c136c8006d"
JOB = "helm-claude-xreal-20261019-c42"
PARALLEL_JOB = "helm-claude-scribe-l4-score-20261019-c41"
HOLD = 1.0
OPERATOR = "claude-code-subagent-launch-operator-c42-20261019"
LINE_SHA = "2a8a6f864a9e6d5349a048232813506c8efd51c50fdfde0f70af1e396fe56e00"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    partial = path.with_name(path.name + ".partial")
    with open(partial, "xb") as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    os.replace(partial, path)


def dump(obj) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=True) + "\n").encode("ascii")


utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
assert sha(CURRENT) == CURRENT_SHA_EXPECTED, "ledger changed since the operator read it; stop"
assert sha(ZIP) == ZIP_SHA and sha(RULING) == RULING_SHA and sha(APPROVAL) == APPROVAL_SHA and sha(OPERATOR_RECORD) == OPERATOR_RECORD_SHA
op = json.loads(OPERATOR_RECORD.read_text(encoding="ascii"))
owner_line = op["owner_line_verbatim"]
assert hashlib.sha256(owner_line.encode("utf-8")).hexdigest() == LINE_SHA
assert op["package_zip_sha256"] == ZIP_SHA and op["package_freeze_sha256"] == FREEZE_SHA and op["cap_usd"] == HOLD
history = HISTORY.read_text(encoding="utf-8")
assert JOB not in history and '-c42"' not in history and "-c42-" not in history and "-c42a" not in history and "-c42#" not in history, "c42 already used"
assert history.endswith("\n")
last = json.loads(history.rstrip("\n").rsplit("\n", 1)[-1])
assert last.get("job") == PARALLEL_JOB and last.get("action") == "CLOSEOUT_CONSERVATIVE_CHARGE", ("C41_NOT_CLOSED_OUT_YET", last.get("job"), last.get("action"))
cur = json.loads(CURRENT.read_bytes())
BEFORE = cur["combined_allocation_usd"]
AFTER = round(BEFORE + HOLD, 2)
assert BEFORE == last["after_usd"] and cur["latest_record_sha256"] == last["addendum_sha256"] and cur["last_jobs"] == [PARALLEL_JOB]
assert cur["ceiling_usd"] == 200.0 and cur["unreserved_usd"] == round(200.0 - BEFORE, 2)
assert cur["active_inquiry_unreserved_usd"] == round(200.0 - BEFORE, 2)
assert AFTER <= cur["ceiling_usd"]
before_sha = sha(CURRENT)

rdir = PREP / "x_real_c42_reservation_20261019"
rdir.mkdir(exist_ok=False)
rpath = rdir / "BUDGET_RESERVATION_XREAL_C42.json"
reservation = {
    "schema": "helm.aws-combined-allocation.reservation/1",
    "utc": utc,
    "job": JOB,
    "hold_placed_usd": HOLD,
    "combined_ceiling_usd": 200.0,
    "historical_pointer_ceiling_usd": 200.0,
    "ceiling_changed": False,
    "previous_pointer_sha256": before_sha,
    "source_manifest_sha256": ZIP_SHA,
    "source_archive": str(ZIP),
    "package_freeze_sha256": FREEZE_SHA,
    "controller_freeze_sha256": None,
    "controller_freeze_note": "controller not built yet (X-REAL exam sealed 2026-10-19T23:56:39Z by the separate custodian); the controller is bound at launch time",
    "authority_record": str(RULING),
    "authority_sha256": RULING_SHA,
    "owner_quote": owner_line,
    "related_approval_record": str(APPROVAL),
    "related_approval_sha256": APPROVAL_SHA,
    "operator_authority_record": str(OPERATOR_RECORD),
    "operator_authority_sha256": OPERATOR_RECORD_SHA,
    "authority_scope": "owner pre-approval line 'I PRE-APPROVE BOTH OF THE FOLLOWING:   Two sign lines are coming: X-REAL at 1 USD, and the transformer training at 8 USD.' (sha256 2a8a6f86, 121 bytes) bound to package a9b4c954 by APPROVAL_RECORD_XREAL.md, under the owner's 200 USD ceiling ruling; this hold covers ONLY the X-REAL line (1.00 USD TOTAL cap: the scored attempt and at most one plumbing retry; no torch); the 8 USD transformer line is not touched here; the launch brief orders the coordinator to place this hold before launch",
    "parallel_job_note": "the previous ledger line is the c41 (Scribe L4) closeout; this hold is a separate line placed after it, so no hold is double-counted or released by another job",
    "combined_allocation_before_usd": BEFORE,
    "combined_allocation_after_usd": AFTER,
    "operator_id": OPERATOR,
    "reservation_id": f"xreal-c42-{uuid.uuid4().hex}",
    "client_token": f"xreal-c42-{uuid.uuid4().hex}",
    "hold_release": "No automatic release; actual billing remains pending. Any release requires explicit owner disposition or accepted billing reconciliation.",
    "job_scope": "One source-bound scored attempt (plus at most one plumbing retry under this same hold) of HELM_XREAL_20261019 (zip sha256 a9b4c954..., freeze 67b48541...): m6i.xlarge, c21 image ami-0dddfa1ffa6b87af7, 2-CPU slice with 14 GiB, stage limit 3000 s, command deadline 2400 s, total cap 1.00 USD, cleanup with proof. No automatic retry; no fallback host; no torch work.",
    "execution_status_at_reservation": "NOT_LAUNCHED; owner pre-approval given; X-REAL exam sealed (manifest 1e535511, pins 4cb97a82)",
}
atomic_write(rpath, dump(reservation))
rsha = sha(rpath)
assert sha(CURRENT) == CURRENT_SHA_EXPECTED, "ledger changed while the reservation was written; stop"
cur["utc"] = utc
cur["combined_allocation_usd"] = AFTER
cur["unreserved_usd"] = round(200.0 - AFTER, 2)
cur["active_inquiry_unreserved_usd"] = round(200.0 - AFTER, 2)
cur["reconciliation_records"].append(str(rpath))
cur["latest_record_sha256"] = rsha
cur["last_jobs"] = [JOB]
atomic_write(CURRENT, dump(cur))
after_sha = sha(CURRENT)
line = {"schema": "helm.aws-combined-allocation.reservation/1", "utc": utc,
        "action": "SOURCE_BOUND_SINGLE_ATTEMPT_RESERVATION", "job": JOB, "before_usd": BEFORE, "hold_placed_usd": HOLD,
        "after_usd": AFTER, "reservation_record_path": str(rpath), "reservation_record_sha256": rsha,
        "ledger_after_sha256": after_sha, "operator_id": OPERATOR, "reservation_id": reservation["reservation_id"],
        "client_token": reservation["client_token"]}
with open(HISTORY, "ab") as stream:
    stream.write(json.dumps(line, separators=(",", ":"), ensure_ascii=True).encode("ascii") + b"\n")
    stream.flush(); os.fsync(stream.fileno())
result = {"reservation": str(rpath), "reservation_sha256": rsha, "ledger_before_sha256": before_sha,
          "ledger_after_sha256": after_sha, "ceiling_usd": cur["ceiling_usd"], "combined_allocation_before_usd": BEFORE,
          "combined_allocation_usd": cur["combined_allocation_usd"], "unreserved_usd": cur["unreserved_usd"]}
with open(PREP / "x_real_c42_operator_notes" / "LEDGER_HOLD_RESULT_XREAL_C42.json", "x", encoding="utf-8", newline="\n") as stream:
    json.dump(result, stream, indent=1); stream.write("\n")
print(json.dumps(result, indent=1))
