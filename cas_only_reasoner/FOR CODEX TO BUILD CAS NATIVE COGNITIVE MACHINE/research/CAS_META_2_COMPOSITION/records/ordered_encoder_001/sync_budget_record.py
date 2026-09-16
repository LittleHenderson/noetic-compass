"""Publish a verified copy of the canonical ledger; never reserve or refund."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from aws import budget

SOURCE = Path("C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/meta1/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/CAS_META_2_COMPOSITION/records/budget/campaign_ledger.json")
DESTINATION = ROOT / "records/budget/campaign_ledger.json"
state = budget.read_ledger(SOURCE)
assert state["revision"] == 74
assert state["total_reserved_usd"] == "431.00"
assert state["remaining_unreserved_usd"] == "4569.00"
source_history = SOURCE.with_suffix(SOURCE.suffix + ".history")
destination_history = DESTINATION.with_suffix(DESTINATION.suffix + ".history")
for source in sorted(source_history.iterdir()):
    target = destination_history / source.name
    if target.exists():
        assert target.read_bytes() == source.read_bytes(), source.name
    else:
        assert source.name == "00000074.json"
        with target.open("xb") as handle:
            handle.write(source.read_bytes())
DESTINATION.write_bytes(SOURCE.read_bytes())
assert budget.read_ledger(DESTINATION) == state
receipt = {
    "schema": "cas-canonical-budget-publication-copy/1",
    "observed_utc": datetime.now(timezone.utc).isoformat(),
    "canonical_spending_ledger": str(SOURCE),
    "publication_copy": str(DESTINATION),
    "revision": state["revision"],
    "total_reserved_usd": state["total_reserved_usd"],
    "remaining_unreserved_usd": state["remaining_unreserved_usd"],
    "owner_task_cap_usd": state["owner_task_cap_usd"],
    "head_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    "all_75_history_revisions_verified": True,
    "new_reservations_by_this_script": 0,
    "refunds": 0,
    "boundary": "Conservative reservations, not invoiced charges; the publication copy is not a second spending authority."
}
output = Path(__file__).with_name("budget_terminal.json")
with output.open("x", encoding="utf-8", newline="\n") as handle:
    json.dump(receipt, handle, indent=2, sort_keys=True)
    handle.write("\n")
print(json.dumps(receipt))
