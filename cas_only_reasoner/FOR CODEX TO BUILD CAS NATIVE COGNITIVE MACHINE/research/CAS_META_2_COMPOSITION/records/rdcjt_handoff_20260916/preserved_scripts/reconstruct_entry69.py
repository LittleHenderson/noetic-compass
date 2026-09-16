"""Reconstruct the AMENDED revision-69 ledger state exactly, by hash.

Context. The cap amendment was applied by editing the revision-69 state in place
(cap 400.00 -> 5000.00, free 4.00 -> 4604.00, plus the amendment binding) while
history/00000069.json kept the pre-raise bytes. The next reservation (revision 70)
recorded previous_state_sha256 = digest(encoded(amended rev 69)), which does not
equal digest(encoded(entry 69 as stored)) -> BROKEN_BUDGET_HISTORY_CHAIN.

reserve_budget's update is fully determined, so the amended rev-69 state is
recoverable from entry 70 by dropping the appended reservation and restoring the
derived fields. The one field not derivable is updated_utc; the amended head was
observed to have kept the previous value, so it is taken from entry 69.

This script only RECONSTRUCTS and CHECKS. It writes nothing unless --apply is
given, and it refuses unless the reconstruction reproduces the digest that
entry 70 already committed to.
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


def load(path):
    return json.loads(Path(path).read_bytes())


def main():
    apply = "--apply" in sys.argv

    head = load(LEDGER)
    e70 = load(HISTORY / "00000070.json")
    e69 = load(HISTORY / "00000069.json")
    e68 = load(HISTORY / "00000068.json")

    committed = e70["previous_state_sha256"]

    recon = dict(e70)
    recon["reservations"] = e70["reservations"][:-1]
    recon["revision"] = 69
    recon["owner_task_cap_usd"] = str(budget.CAP)
    totals = budget.reservations_total(recon["reservations"])
    recon["total_reserved_usd"] = str(totals)
    recon["remaining_unreserved_usd"] = str(budget.CAP - totals)
    recon["previous_state_sha256"] = budget.digest(budget.encoded(e68))
    recon["updated_utc"] = e69["updated_utc"]

    got = budget.digest(budget.encoded(recon))
    report = {
        "apply": apply,
        "committed_digest_from_entry70": committed,
        "reconstructed_digest": got,
        "reconstruction_exact": got == committed,
        "reconstructed_cap": recon["owner_task_cap_usd"],
        "reconstructed_free": recon["remaining_unreserved_usd"],
        "reconstructed_reservations": len(recon["reservations"]),
        "reconstructed_amendment": "amendment" in recon,
        "entry69_current_sha256": hashlib.sha256(
            (HISTORY / "00000069.json").read_bytes()).hexdigest(),
        "entry69_is_pre_raise": e69["owner_task_cap_usd"] == "400.00",
        "reservations_untouched": (e70["reservations"][:-1]
                                   == e69["reservations"]),
    }
    print(json.dumps(report, indent=2))

    if not report["reconstruction_exact"]:
        raise SystemExit("REFUSED: reconstruction does not reproduce the digest "
                         "entry 70 already committed to. Not writing.")
    if not report["reservations_untouched"]:
        raise SystemExit("REFUSED: this would alter the money record.")

    if not apply:
        print("dry run only; pass --apply to write the reconstructed entry")
        return 0

    preserve = LEDGER.parent / "PRESERVED_history_00000069_pre_cap_raise.json"
    if not preserve.exists():
        shutil.copyfile(HISTORY / "00000069.json", preserve)
    print("preserved original entry 69 bytes ->", preserve)

    (HISTORY / "00000069.json").write_bytes(budget.encoded(recon))
    print("wrote reconstructed entry 69")

    state = budget.read_locked(LEDGER, HISTORY)
    print("read_locked OK: revision", state["revision"], "cap",
          state["owner_task_cap_usd"], "reserved", state["total_reserved_usd"],
          "free", state["remaining_unreserved_usd"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
