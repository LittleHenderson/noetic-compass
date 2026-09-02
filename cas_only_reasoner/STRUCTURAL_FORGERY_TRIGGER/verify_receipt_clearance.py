"""CI GATE: fail any run receipt that does not carry a valid, self-consistent clearance.

GLM audit of `69695680`, risk point (b):

    "The procedural residue -- a launcher that never calls the gate, or forges both receipt and
     clearance -- is detectable (a receipt without a bound clearance is visibly incomplete and
     greppable) but only IF SOMETHING LOOKS. My recommendation: make that last check
     MECHANICAL. A dumb second script -- or one CI step -- that fails any training run whose
     receipt lacks a bound clearance, and fails any clearance whose receipt digest does not
     re-verify. It converts 'an auditor must check it' from a human promise into a grep."

This is that script. It is deliberately dumb: it re-derives nothing and trusts nothing, it only
checks that a receipt's own clearance is present, permitting, and internally consistent with the
trigger receipt embedded inside it.

    python verify_receipt_clearance.py <run_receipt.json> [more...]
    python verify_receipt_clearance.py --require-training-scope <run_receipt.json>

    exit 0   every receipt carries a valid clearance
    exit 1   at least one receipt fails -- FAIL THE BUILD

WHAT THIS CLOSES, AND WHAT IT DOES NOT. It closes "nobody looked". It does NOT close "a launcher
that controls its own source lied about everything consistently" -- that remains impossible in
code, and is stated as such in replay_training_gate.py and in the trigger spec. What it removes
is the far likelier failure: a run that simply never called the gate, and a receipt that nobody
noticed was incomplete.
"""
import json
import os
import sys

GATE = "STRUCTURAL_FORGERY_DEFENCE"
PERMITTING_CODES = (0,)
KEY = "structural_forgery_clearance"
REQUIRED = ("gate", "job_id", "scope", "event", "trigger_state", "trigger_exit_code",
            "manifest_digest", "pipeline_derived_memory_feeds_training", "trigger_receipt")


def check(receipt_path):
    """Return (ok, [failures], [notes])."""
    fails, notes = [], []
    try:
        with open(receipt_path, encoding="utf-8") as f:
            r = json.load(f)
    except Exception as e:
        return False, [f"receipt unreadable: {type(e).__name__}: {e}"], []

    c = r.get(KEY)
    if c is None:
        return False, [f"NO CLEARANCE. The receipt has no '{KEY}'. Either the run never called "
                       f"the interlock, or it did not bind the result. Both fail."], []
    if not isinstance(c, dict):
        return False, [f"'{KEY}' is not an object"], []

    for k in REQUIRED:
        if k not in c:
            fails.append(f"clearance missing required field '{k}'")
    if c.get("gate") != GATE:
        fails.append(f"clearance gate is {c.get('gate')!r}, expected {GATE!r}")

    code = c.get("trigger_exit_code")
    if code not in PERMITTING_CODES:
        fails.append(f"clearance exit code {code!r} is NOT permitting -- this run should never "
                     f"have trained")

    tr = c.get("trigger_receipt")
    if not isinstance(tr, dict) or not tr:
        fails.append("clearance carries no embedded trigger receipt to re-verify against")
        return (not fails), fails, notes

    # --- the re-verification GLM asked for: the clearance must agree with the trigger's own
    # --- receipt on state, exit code and manifest digest.
    for field, cf, tf in (("state", "trigger_state", "state"),
                          ("exit code", "trigger_exit_code", "exit_code"),
                          ("manifest digest", "manifest_digest", "manifest_digest")):
        cv, tv = c.get(cf), tr.get(tf)
        if cv != tv:
            fails.append(f"{field} MISMATCH: clearance says {cv!r}, embedded trigger receipt "
                         f"says {tv!r}")
    if tr.get("exit_code") not in PERMITTING_CODES:
        fails.append(f"the embedded trigger receipt is not a permitting result "
                     f"(exit {tr.get('exit_code')!r})")

    # --- scope / job identity must be present and consistent
    if tr.get("declared_scope") and tr["declared_scope"] != c.get("scope"):
        fails.append(f"scope mismatch: clearance {c.get('scope')!r}, "
                     f"trigger receipt {tr['declared_scope']!r}")
    if tr.get("declared_job_id") and tr["declared_job_id"] != c.get("job_id"):
        fails.append(f"job id mismatch: clearance {c.get('job_id')!r}, "
                     f"trigger receipt {tr['declared_job_id']!r}")

    if tr.get("refusals"):
        fails.append(f"the trigger recorded refusals: {tr['refusals']}")
    if tr.get("authority_problems"):
        fails.append(f"the trigger recorded authority problems: {tr['authority_problems']}")

    # --- notes, not failures: things an auditor should see
    if c.get("trigger_state") == "WATCH_ACKNOWLEDGED":
        ack = tr.get("acknowledgement", {})
        notes.append(f"passed on an owner ACKNOWLEDGEMENT of WATCH: {ack.get('detail')}")
    if c.get("pipeline_derived_memory_feeds_training") is False:
        notes.append("this run's pipeline did NOT feed memory into training (DORMANT path)")
    return (not fails), fails, notes


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    require_training = "--require-training-scope" in sys.argv
    if not args:
        print("usage: verify_receipt_clearance.py <run_receipt.json> [more...]")
        return 1

    print("RUN-RECEIPT CLEARANCE VERIFICATION")
    print("Fails any training run whose receipt lacks a bound clearance, and any clearance")
    print("that does not re-verify against the trigger receipt embedded in it.")
    print()
    bad = 0
    for p in args:
        ok, fails, notes = check(p)
        bad += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}]  {os.path.basename(p)}")
        for n in notes:
            print(f"           note: {n}")
        for f in fails:
            print(f"           FAIL: {f}")
        if ok and require_training:
            with open(p, encoding="utf-8") as fh:
                c = json.load(fh)[KEY]
            if not c.get("pipeline_derived_memory_feeds_training"):
                print("           note: --require-training-scope given, but this run did not "
                      "feed memory into training")
    print()
    print(f"{len(args) - bad} / {len(args)} receipts carry a valid clearance")
    if bad:
        print()
        print("BUILD MUST FAIL. A training run without a verified clearance is not a result.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
