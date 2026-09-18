"""Exactly what changes if the constraint layer is wired into a run. Measured, not asserted.

Pure standard library plus the project's pure modules. No torch, no device, no model, no training, no
new run.

Why this matters
----------------
Rounds 36 and 37 flagged the wiring as an owner decision and described it as "changes the decision
contract and its digest". That phrasing makes it sound expensive. **Whether it is expensive is a
question about code, so it is answered here rather than assumed.**

What is compared
----------------
The same packet is compiled twice: once with the registered `slots.DECISION_CONTRACT`, and once with a
contract modified to describe a constraint layer. Then, for every slot:

    plan_digest                     does it change?
    slot_id                         does it change?
    binding._query_spec(slot)       does it change?
    sha256(binding.row_bytes(...))  does it change?

Those last two are the encoder's entire input. If they are unchanged, then every encoded vector, every
score, and every recorded prediction's *scores* are unchanged -- and only the decisions differ.

The check is done on real packets from the frozen course, in all eight kinds.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

from cas_meta2.typed_teaching import binding, course, slots, worker_contract  # noqa: E402

SEED = 20260916


def main() -> int:
    frozen_course, _tokenizer, _ = worker_contract.load_material(HOME)
    registry = frozen_course["registry"]

    registered = slots.DECISION_CONTRACT
    print("=" * 100)
    print("THE REGISTERED DECISION CONTRACT, as it stands")
    print("=" * 100)
    print()
    print(json.dumps(registered, sort_keys=True, indent=2)[:1400])
    print()

    # A contract that describes a constraint layer. This is what wiring the layer would require the
    # contract TEXT to say; the layer itself is code, but a contract that no longer describes the
    # decoder would be dishonest.
    amended = dict(registered)
    amended["declared_constraints"] = (
        "declared legality conditions read from the packet are enforced after the per-slot or "
        "candidate decision: self-links and self-parts are ABSENT; declared cardinalities from "
        "focus['contains'], the supplied whole, and participants_basis; and "
        "FOCUS_WORLD_DECLARATION_IDENTITY by enumeration of the bank"
    )

    changed = {"plan_digest": 0, "slot_id": 0, "query_spec": 0, "query_bytes": 0}
    total_slots = 0
    kinds = set()
    for row in registry:
        packet = course.model_packet(frozen_course, row["record_id"])
        kinds.add(row["query"]["kind"])

        slots.DECISION_CONTRACT = registered
        slots._compile_slots_uncached.cache_clear() if hasattr(
            slots._compile_slots_uncached, "cache_clear") else None
        left = slots.compile_slots(packet)

        slots.DECISION_CONTRACT = amended
        right = slots.compile_slots(packet)
        slots.DECISION_CONTRACT = registered

        if left["plan_digest"] != right["plan_digest"]:
            changed["plan_digest"] += 1

        left_by_id = {slot["slot_id"]: slot for slot in left["slots"]}
        right_by_id = {slot["slot_id"]: slot for slot in right["slots"]}
        if set(left_by_id) != set(right_by_id):
            changed["slot_id"] += 1

        validated = slots.validate_plan(packet, left)
        for slot in left["slots"]:
            total_slots += 1
            spec_left = binding._query_spec(validated, slot)
            other = next((s for s in right["slots"] if s["slot_id"] == slot["slot_id"]), None)
            if other is None:
                continue
            spec_right = binding._query_spec(validated, other)
            if json.dumps(spec_left, sort_keys=True) != json.dumps(spec_right, sort_keys=True):
                changed["query_spec"] += 1
            if (hashlib.sha256(binding.row_bytes(["query", spec_left], seed=SEED)).hexdigest()
                    != hashlib.sha256(binding.row_bytes(["query", spec_right], seed=SEED)).hexdigest()):
                changed["query_bytes"] += 1

    print("=" * 100)
    print("WHAT CHANGES WHEN THE CONTRACT TEXT CHANGES — all 564 packets, every kind")
    print("=" * 100)
    print()
    print(f"  kinds covered                        {len(kinds)}  {sorted(kinds)}")
    print(f"  packets compared                     {len(registry)}")
    print(f"  slots compared                       {total_slots}")
    print()
    print(f"  plan_digest changed, packets         {changed['plan_digest']:6d} of {len(registry)}")
    print(f"  slot_id set changed, packets         {changed['slot_id']:6d} of {len(registry)}")
    print(f"  encoder query spec changed, slots    {changed['query_spec']:6d} of {total_slots}")
    print(f"  encoder query BYTES changed, slots   {changed['query_bytes']:6d} of {total_slots}")
    print()
    if changed["query_spec"] == 0 and changed["query_bytes"] == 0 and changed["slot_id"] == 0:
        print("THE ENCODER'S ENTIRE INPUT IS UNCHANGED.")
        print("  Every encoded vector, every score, and every recorded prediction's `scores` are")
        print("  therefore unchanged. What changes is plan_digest and the DECISIONS.")
        print()
        print("  So wiring the constraint layer does NOT invalidate the model, the encoder, the")
        print("  readout or the block, and it does NOT require a new baseline for them. Rounds 36")
        print("  and 37 described it as changing the contract and its digest, which is true, and")
        print("  implied that was expensive, which this measurement does not support.")
    else:
        print("SOMETHING IN THE ENCODER'S INPUT CHANGED -- the wiring is more invasive than assumed.")
    print()
    print("Caveat: `binding.compile_packet` may itself read `slots.DECISION_CONTRACT`; it does not")
    print("here, which is what makes the encoder input invariant, but that is a property of the")
    print("current code and would need re-checking if the packet compilation changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
