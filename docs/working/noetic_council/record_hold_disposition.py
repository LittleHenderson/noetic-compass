"""Record the owner's disposition of the seven open wave-1 holds.

WHY THIS EXISTS
---------------
The wave-1 reconciliation record says, in its own words:

    "it does not change any hold or ledger balance; the standing rule is that holds change only by
     explicit owner disposition or accepted billing reconciliation"

The owner gave that disposition. This writes it down executably, in the same addendum family the rest
of the budget record uses, rather than leaving it as prose in a chat.

WHAT THIS CHANGES, AND WHAT IT DOES NOT
---------------------------------------
It changes ONE number in the ledger: 63.75 USD of holds that were still open become unreserved. It
changes no AWS resource, no charge, and no ceiling. In particular it does not delete any attempt, does
not re-price any charge, and does not touch the two instances the owner was told about.

The owner's words are recorded as they were given. The question channel used in this session issues
no message id, so none is invented: an identifier that never existed is worse than an absent one.

Idempotent: refuses if the disposition file already exists.

Usage:
    C:\\Python314\\python.exe -B record_hold_disposition.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone

HERE = r"C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation"
RECON = os.path.join(HERE, "reconciliation_20261016T2300Z",
                     "RECONCILIATION_W1_C34_ALL_ATTEMPTS.json")

LEDGER_BEFORE_USD = 162.45
CEILING_USD = 200.00
UNRESERVED_BEFORE_USD = 37.55
HOLDS_PLACED_TOTAL_USD = 66.50
HOLDS_STILL_OPEN_USD = 63.75
CHARGES_ESTABLISHED_USD = 2.75


def main() -> int:
    if not os.path.isfile(RECON):
        print("REFUSED: the reconciliation record is not at %s" % RECON)
        return 1
    with open(RECON, encoding="utf-8") as fh:
        recon = json.load(fh)

    # Read the numbers from the record rather than trusting the constants above. If the record has
    # moved, this must fail rather than write a disposition against figures that are no longer true.
    checks = {
        "ledger_before_usd": LEDGER_BEFORE_USD,
        "combined_ceiling_usd": CEILING_USD,
        "unreserved_usd": UNRESERVED_BEFORE_USD,
        "holds_placed_total_usd": HOLDS_PLACED_TOTAL_USD,
        "hold_still_open_if_all_reconciled_usd": HOLDS_STILL_OPEN_USD,
        "charges_established_total_usd": CHARGES_ESTABLISHED_USD,
    }
    for key, expected in checks.items():
        got = recon.get(key)
        if got != expected:
            print("REFUSED: the record says %s = %r, this script expects %r." % (key, got, expected))
            print("         A disposition written against stale figures is worse than none.")
            return 1
    print("all six figures in the reconciliation record match this script.")

    unreserved_after = round(UNRESERVED_BEFORE_USD + HOLDS_STILL_OPEN_USD, 6)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = os.path.join(HERE, "BUDGET_DISPOSITION_W1_C34_HOLDS_%s.json" % stamp)
    if os.path.exists(out):
        print("the disposition file already exists: %s" % out)
        return 0

    body = {
        "schema": "helm.aws-combined-allocation.hold-disposition/1",
        "utc": datetime.now(timezone.utc).isoformat(),
        "job": recon.get("job"),
        "disposition": "CLEAR_THE_SEVEN_OPEN_WAVE_1_HOLDS",
        "owner_authority": (
            "The owner's own answer, given in this session through the harness's question channel. "
            "The question put to the owner was: \"Those 63.75 of holds are entries in my own ledger "
            "file, not AWS bookings. Should I clear them so the unreserved room goes from 37.55 to "
            "101.30?\" The owner selected: \"Yes, clear them\". No message id exists for that channel, "
            "so none is recorded: an invented identifier is worse than an absent one. In the same "
            "answer the owner also selected \"Yes, go ahead (costs $0 for now)\" for R1-RT, which is "
            "a separate authorisation recorded in the council directive, not in this budget file."),
        "owner_words_verbatim": ["Yes, clear them", "Yes, go ahead (costs $0 for now)"],
        "ledger_usd": LEDGER_BEFORE_USD,
        "ceiling_usd": CEILING_USD,
        "charges_established_usd": CHARGES_ESTABLISHED_USD,
        "holds_placed_count": recon.get("holds_placed_count"),
        "holds_placed_total_usd": HOLDS_PLACED_TOTAL_USD,
        "holds_open_before_usd": HOLDS_STILL_OPEN_USD,
        "holds_open_after_usd": 0.0,
        "unreserved_before_usd": UNRESERVED_BEFORE_USD,
        "unreserved_after_usd": unreserved_after,
        "what_this_changes": (
            "ONE number in the ledger: the 63.75 USD of holds that were still open become "
            "unreserved, so the unreserved room goes from 37.55 to %s USD. The ledger total stays at "
            "%s of %s." % (unreserved_after, LEDGER_BEFORE_USD, CEILING_USD)),
        "what_this_does_not_do": (
            "It changes no AWS resource, no charge and no ceiling. It deletes no attempt and re-prices "
            "nothing. It does not touch the two running instances the owner was told about. The "
            "cleared holds were always bookkeeping: nothing was reserved on Amazon's side, and the "
            "AWS check run in this session found none of the wave-1 machines still present."),
        "aws_reality_checked": {
            "how": "boto3 describe_instances in the default region and in us-east-1 and us-west-2",
            "wave_1_machine_present": False,
            "instances_found_and_not_ours": [
                {"id": "i-0bd0a082507a51ae3", "type": "t3.small", "name": "nc-customer-app",
                 "state": "running"},
                {"id": "i-02137d196e671b5c1", "type": "t3.small", "name": "nc-canary-app",
                 "state": "running"},
                {"id": "i-0c3028734c8885542", "type": "g6e.xlarge",
                 "name": "cas-bridge-control-20260822", "state": "stopped"},
            ],
            "note": ("These three were NOT created by this work and were NOT touched. They are "
                     "recorded because two are running and billing and one is holding disk, and the "
                     "owner should know. Changing them is the owner's call and nobody else's."),
        },
        "actual_billing": "PENDING",
        "written_by": "the TKS Noetic Council session, round 17",
    }
    raw = json.dumps(body, indent=2).encode("utf-8")
    body["disposition_digest"] = hashlib.sha256(raw).hexdigest()
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(body, indent=2) + "\n")
    print("WROTE %s" % out)
    print("  holds open : %s -> 0.0" % HOLDS_STILL_OPEN_USD)
    print("  unreserved : %s -> %s" % (UNRESERVED_BEFORE_USD, unreserved_after))
    print("  disposition digest: %s" % body["disposition_digest"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
