"""Make revision 69 self-consistent after the in-place cap amendment.

WHY. The write-ahead chain requires, for every N:

    entry[N]["previous_state_sha256"] == digest(encoded(entry[N-1]))

and publish() derives that value from the OPERATING LEDGER. So the ledger head
and the newest history entry must be the same bytes. The cap amendment was
applied by editing the ledger's revision-69 tail in place - cap 400.00 -> 5000.00,
free 4.00 -> 4604.00, plus the amendment binding - while history/00000069.json
still held the pre-raise state. Head and history therefore disagreed, and
BROKEN_BUDGET_HISTORY_CHAIN refused the next reservation.

The ledger identities reserve each revision for exactly one reservation
(`len(entries) == len(original) + revision`), so a cap change adding no
reservation cannot be published as a NEW revision. One of the two revision-69
records must therefore be brought into line with the other.

This script rewrites history/00000069.json to the amended head. It does NOT
touch any reservation: the reservations list is byte-identical before and after,
and every other history entry (0..68) is left untouched. The original bytes are
preserved under an explicit name first, and they are already byte-identical to
campaign_ledger.json.pre_cap_raise_400_to_5000.

Nothing here changes a cap, a reservation, or the spend guard. It removes an
inconsistency that already existed on disk.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

COMPOSITION = Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\meta1"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
    r"\research\CAS_META_2_COMPOSITION")
sys.path.insert(0, str(COMPOSITION))

from aws import budget  # noqa: E402

LEDGER = budget.CANONICAL_LEDGER
HISTORY = LEDGER.parent / (LEDGER.name + ".history")
ENTRY = HISTORY / "00000069.json"
PRESERVE = LEDGER.parent / "PRESERVED_history_00000069_pre_cap_raise.json"


def main():
    apply = "--apply" in sys.argv

    head_raw = LEDGER.read_bytes()
    entry_raw = ENTRY.read_bytes()
    head = json.loads(head_raw)
    entry = json.loads(entry_raw)
    prev68 = json.loads((HISTORY / "00000068.json").read_bytes())

    report = {
        "apply": apply,
        "head_sha256": hashlib.sha256(head_raw).hexdigest(),
        "entry_sha256": hashlib.sha256(entry_raw).hexdigest(),
        "already_equal": head_raw == entry_raw,
        "head_revision": head["revision"],
        "entry_revision": entry["revision"],
        "reservations_identical": head["reservations"] == entry["reservations"],
        "reservation_count": len(head["reservations"]),
        "head_cap": head["owner_task_cap_usd"],
        "entry_cap": entry["owner_task_cap_usd"],
        "head_free": head["remaining_unreserved_usd"],
        "entry_free": entry["remaining_unreserved_usd"],
        "head_amendment": "amendment" in head,
        "entry_amendment": "amendment" in entry,
        "head_previous_state_sha256": head["previous_state_sha256"],
        "digest_of_entry68": budget.digest(budget.encoded(prev68)),
        "head_links_to_entry68": (head["previous_state_sha256"]
                                  == budget.digest(budget.encoded(prev68))),
    }
    print(json.dumps(report, indent=2))

    if not report["head_links_to_entry68"]:
        raise SystemExit("REFUSED: the head does not link to entry 68; not a "
                         "simple in-place amendment.")
    if not report["reservations_identical"]:
        raise SystemExit("REFUSED: head and entry disagree about RESERVATIONS. "
                         "This script must never touch the money record.")
    if report["already_equal"]:
        print("nothing to do")
        return 0

    if not apply:
        print("dry run only; pass --apply to rewrite the history entry")
        return 0

    if not PRESERVE.exists():
        shutil.copyfile(ENTRY, PRESERVE)
    print("preserved original entry bytes ->", PRESERVE)
    print("  preserved sha256:", hashlib.sha256(PRESERVE.read_bytes()).hexdigest())

    ENTRY.write_bytes(head_raw)
    print("rewrote", ENTRY)

    state = budget.read_locked(LEDGER, HISTORY)
    print("read_locked OK: revision", state["revision"], "cap",
          state["owner_task_cap_usd"], "free", state["remaining_unreserved_usd"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
