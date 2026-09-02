"""Prove the CI clearance check catches every way a run receipt can be wrong.

Closes GLM's recommendation on `69695680` risk point (b): make the last check MECHANICAL, so
"an auditor must check it" becomes a grep rather than a human promise.

Each case takes a GENUINE clearance produced by the real gate, damages the receipt in one
specific way, and asserts the CI check fails the build. The first case is the undamaged receipt,
which must PASS -- a checker that fails everything is not a checker.

    python validate_receipt_check.py
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from replay_training_gate import bind_into_receipt, require_clearance  # noqa: E402

OWNER, COMMIT, TS = "test-owner", "0" * 40, "2026-09-02T00:00:00Z"
WORK = tempfile.mkdtemp(prefix="receipt_check_")


def healthy_corpus():
    mems = []
    for i in range(60):
        mems.append({"id": f"m{i}", "trajectory": [(i * 3 + k * 2) % 10 for k in range(6)],
                     "links": ["x"] * 7, "is_forgery": False, "legitimate_group": i // 2})
    for j in range(20):
        mems.append({"id": f"f{j}", "trajectory": [9] * 6, "links": ["x"] * 4,
                     "is_forgery": True})
    p = os.path.join(WORK, "corpus.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"memories": mems, "writes_per_day": 0}, f)
    return p


clearance = require_clearance(
    job_id="DEMO-RP", pipeline_config={"memory_feeds_training": True},
    declared_owner=OWNER, source_commit=COMMIT, timestamp=TS,
    corpus_path=healthy_corpus(), artifact_dir=WORK)
GOOD = bind_into_receipt({"project": "demo", "result": "..."}, clearance)
K = "structural_forgery_clearance"


def write(name, obj):
    p = os.path.join(WORK, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
    return p


def damaged(mutate):
    r = copy.deepcopy(GOOD)
    mutate(r[K])
    return r


def _state(c):
    c["trigger_state"] = "CLEAR"
    c["trigger_receipt"]["state"] = "NECESSARY"


CASES = [
    ("genuine receipt from the gate", GOOD, 0),
    ("NO clearance at all -- the run never called the gate",
     {"project": "demo", "result": "..."}, 1),
    ("clearance state edited away from the trigger receipt", damaged(_state), 1),
    ("manifest digest edited -- does not re-verify",
     damaged(lambda c: c.update(manifest_digest="deadbeef")), 1),
    ("a BLOCKING result bound into a receipt anyway",
     damaged(lambda c: (c.update(trigger_exit_code=20),
                        c["trigger_receipt"].update(exit_code=20))), 1),
    ("clearance stripped of its embedded trigger receipt",
     damaged(lambda c: c.pop("trigger_receipt")), 1),
    ("clearance from a different, unknown gate",
     damaged(lambda c: c.update(gate="SOMETHING_ELSE")), 1),
    ("trigger receipt recorded a refusal but was bound anyway",
     damaged(lambda c: c["trigger_receipt"].update(refusals=["mis-scoped manifest"])), 1),
    ("trigger receipt recorded an authority problem but was bound anyway",
     damaged(lambda c: c["trigger_receipt"].update(authority_problems=["bad digest"])), 1),
    ("job id edited away from the trigger receipt",
     damaged(lambda c: c.update(job_id="OTHER-JOB")), 1),
]

print("CI CLEARANCE CHECK -- does it catch every way a receipt can be wrong?")
print()
print(f"{'scenario':<64}{'want':>6}{'got':>6}")
print("-" * 78)
bad = 0
for i, (label, obj, want) in enumerate(CASES):
    p = write(f"r{i:02d}.json", obj)
    rc = subprocess.run([sys.executable, os.path.join(HERE, "verify_receipt_clearance.py"), p],
                        capture_output=True, text=True).returncode
    ok = rc == want
    bad += not ok
    print(f"{label:<64}{want:>6}{rc:>6}  {'ok' if ok else '<-- FAIL'}")
print()
print("CI-CHECK VALIDATION:", "PASS" if not bad else f"FAIL ({bad})")
sys.exit(1 if bad else 0)
