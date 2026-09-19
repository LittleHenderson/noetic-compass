"""LB11 economics: what would it cost to give every head a gradient in every update?

The learnability lens found the current schedule under-covers (finding LB11): the rarest per-kind head sees a
gradient in only 320 of 1,470 updates, and the 64-way text choice gets 550 update events across 113 records. Its
instruction is "rebalance so every kind appears in every pass (about 10 x 470 updates), or drop the untrainable
heads".

This script measures the two ways to obey that instruction and what each costs in presentations, which is the
quantity that drives instance time:

  A. AS-IS      the practice study's MIXED_SAME_ITEMS order, 147 updates per pass
  B. STRATIFIED the same 147 updates per pass, but each batch assembled to carry as many distinct kinds as it can
  C. WIDENED    the lens's literal suggestion, ~470 updates per pass

It measures only. It does NOT change the contract, and nothing here is applied. Pure Python, $0, no torch.

Run from a short working directory:  python -B lb11_economics.py
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD "
            r"CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX "
            r"TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research" / "CAS_META_2_COMPOSITION")]

from cas_meta2.typed_teaching import pointer_contract as pc  # noqa: E402

frozen, tokenizer, dev = pc.load_material(CNCM)
held, trained, excluded = pc.split(frozen)
kind_of = {row["record_id"]: row["query"]["kind"] for row in frozen["registry"]}
KINDS = sorted(set(kind_of.values()))
pools = {k: sorted(r for r in trained if kind_of[r] == k) for k in KINDS}

batches, stats = pc.pointer_schedule(frozen)          # branch A, the as-is schedule
one_pass = [b for b in batches if b["pass"] == 1]

print("A. AS-IS (the practice MIXED order, 147 updates per pass)")
print("   updates_per_pass %d   presentations_per_pass %d" % (stats["updates_per_pass"],
                                                              stats["presentations_per_pass"]))
absent = {k: 0 for k in KINDS}
for b in one_pass:
    present = {kind_of[r] for r in b["record_ids"]}
    for k in KINDS:
        if k not in present:
            absent[k] += 1
print("   updates in which each kind is ABSENT (of %d):" % len(one_pass))
for k in KINDS:
    print("      %-14s absent %4d  present %4d" % (k, absent[k], len(one_pass) - absent[k]))
print("   every head gets gradient in every update?  %s" % all(v == 0 for v in absent.values()))

print()
print("B. STRATIFIED at the same 147 updates per pass")
print("   one record per kind per batch where the pool allows; deterministic round-robin over each kind's pool")
cursor = {k: 0 for k in KINDS}
strat = []
for i in range(len(one_pass)):
    take = []
    for k in KINDS:
        pool = pools[k]
        if not pool:
            continue
        take.append(pool[cursor[k] % len(pool)])
        cursor[k] += 1
    strat.append(take)
strat_presentations = sum(len(t) for t in strat)
strat_absent = {k: sum(1 for t in strat if k not in {kind_of[r] for r in t}) for k in KINDS}
print("   updates %d   presentations_per_pass %d" % (len(strat), strat_presentations))
print("   kinds absent from any update: %s" % {k: v for k, v in strat_absent.items() if v})
print("   every head gets gradient in every update?  %s" % all(v == 0 for v in strat_absent.values()))
print("   presentation increase over A: %+d (%.1f%%)"
      % (strat_presentations - stats["presentations_per_pass"],
         100.0 * (strat_presentations - stats["presentations_per_pass"]) / stats["presentations_per_pass"]))

print()
print("C. WIDENED, the lens's literal ~470 updates per pass at 8 records each")
wide_presentations = 470 * 8
print("   updates_per_pass 470   presentations_per_pass %d" % wide_presentations)
print("   presentation increase over A: %+d (%.1f%%)"
      % (wide_presentations - stats["presentations_per_pass"],
         100.0 * (wide_presentations - stats["presentations_per_pass"]) / stats["presentations_per_pass"]))
print("   10 passes needs %d updates, against the raised ceiling of %d"
      % (470 * 10 + 16, pc.LEARNER_MAX_UPDATES_CEILING))

print()
print("COST CONTEXT (measured from the practice receipts, not modelled)")
print("   practice: 1470 updates, 8180 presentations, 5465.811116456 s of worker clock")
print("   so roughly %.4f s per presentation and %.4f s per update" % (5465.811116456 / 8180,
                                                                       5465.811116456 / 1470))
print("   a pointer machine's own per-update cost is UNMEASURED; the smoke job measures it")
print()
print("BRIEF CONCLUSION")
ratio_b = strat_presentations / stats["presentations_per_pass"]
print("   B fixes total kind coverage for a ~%.0f%% presentation increase at the SAME update count." % ((ratio_b - 1) * 100))
print("   C multiplies presentations by %.1fx and needs %d updates, above today's ceiling of %d."
      % (wide_presentations / stats["presentations_per_pass"], 470 * 10 + 16, pc.LEARNER_MAX_UPDATES_CEILING))
