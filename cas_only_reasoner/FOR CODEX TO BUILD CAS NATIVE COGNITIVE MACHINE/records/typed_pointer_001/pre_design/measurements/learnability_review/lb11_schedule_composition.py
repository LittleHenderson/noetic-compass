"""LB11 — per-batch kind composition of the frozen 1,470-update schedule, and what it
means for a shared-parameter pointer machine.

Two different gradient questions are measured, and they are not the same:
  (a) does the batch contain a record of kind K?  (does that kind's slot-loss even exist)
  (b) does the batch contain a record of a kind whose SLOT TABLE covers a given head?
Heads are shared across kinds, so the per-head fraction is larger than the per-kind one.
The worst case is a head fed by exactly one kind; the best case is the node scorer, which
almost every kind uses.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c

frozen, tokenizer, devdoc = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
batches, stats = c.practice_schedule(frozen)
interference = c.interference_batches(frozen)
by_id = {r["record_id"]: r for r in frozen["registry"]}
print("main updates %d, presentations %d, interference updates %d"
      % (len(batches), stats["presentations"], len(interference)))
print("batch size histogram:", dict(sorted(Counter(len(b["record_ids"]) for b in batches).items())))
print("main update budget: %d + %d interference + %d replay = %d"
      % (len(batches), len(interference), c.REPLAY_UPDATES, len(batches) + len(interference) + c.REPLAY_UPDATES))

kind_of = {rid: by_id[rid]["query"]["kind"] for rid in by_id}
per_kind = Counter()
updates_with = Counter()
kinds_per_batch = Counter()
for b in batches:
    ks = {kind_of[rid] for rid in b["record_ids"]}
    kinds_per_batch[len(ks)] += 1
    for k in ks:
        updates_with[k] += 1
    for k in ks:
        per_kind[k] += sum(1 for rid in b["record_ids"] if kind_of[rid] == k)

print()
print("main schedule, 1,470 updates:")
print("  kinds present per update:", dict(sorted(kinds_per_batch.items())))
print("  %-16s %-10s %-12s %s" % ("kind", "updates", "fraction", "presentations"))
for k in c.KINDS:
    print("  %-16s %-10d %d/%d    %d" % (k, updates_with[k], updates_with[k], len(batches), per_kind[k]))

# heads: which kinds feed each
HEADS = {
    "node YES/NO (parts, context participants)": ("parts", "context"),
    "edge YES/NO (edge_account pairs)": ("edge_account",),
    "role YES/NO (role_set)": ("role_set",),
    "node scorer <Wq, h_v> (definition whole, reach VIA, correspondence mapping)": ("definition", "reach", "correspondence"),
    "world scorer <W[q;g_F], g_w> (definition kind/function, context setting, analogy world)": ("definition", "context", "analogy"),
    "option vectors (reach ABSENT/DIRECT, correspondence mode, analogy NO_MATCH)": ("reach", "correspondence", "analogy"),
    "role embedding table": ("role_set",),
    "world encoder + ^6 block (everything)": tuple(c.KINDS),
}
print()
print("per-head exposure over the 1,470 main updates:")
for name, kinds in HEADS.items():
    n = sum(1 for b in batches if {kind_of[rid] for rid in b["record_ids"]} & set(kinds))
    print("  %-78s %4d/%d updates" % (name, n, len(batches)))

print()
print("per-head exposure over the 16 interference updates (definition/context only):")
for name, kinds in HEADS.items():
    n = sum(1 for b in interference if {kind_of[rid] for rid in b["record_ids"]} & set(kinds))
    print("  %-78s %4d/%d updates" % (name, n, len(interference)))

print()
print("the same table restricted to what the updated gradient rule (per-head) implies:")
print("AdamW's second moment is a running average with decay 0.999, so a head that sees")
print("gradient in a fraction f of updates needs roughly 1/f updates for its second moment")
print("to describe its own gradient scale rather than be dominated by a stale value.")
LR = 3e-3  # an order-of-magnitude typical AdamW lr for a 45K-parameter module
for name, kinds in HEADS.items():
    n = sum(1 for b in batches if {kind_of[rid] for rid in b["record_ids"]} & set(kinds))
    f = n / len(batches)
    if n == 0:
        continue
    print("  %-78s f=%s  updates needed for 1e-3 decay-equivalence: %d"
          % (name, "%d/%d" % (n, len(batches)), int(round(1 / max(f, 1e-9)))))

# how many DISTINCT training records per kind
print()
print("records of each kind in the trained set (the entire per-kind training population):")
for k in c.KINDS:
    print("  %-16s %d of 358 trained records" % (k, sum(1 for rid in trained if kind_of[rid] == k)))
print("held records per kind (the evaluation target population):")
for k in c.KINDS:
    print("  %-16s %d of 127 held records" % (k, sum(1 for rid in held if kind_of[rid] == k)))

# slot tables: how many learnable rows/columns each kind needs
print()
print("output rows and candidate counts per kind (from the slot plan), which bound the")
print("minimum update count for the head to see each candidate at least once:")
rows = Counter()
for rid in trained:
    pass
packets = dict(c.public_packets(frozen))
for rid in trained:
    from cas_meta2.typed_teaching import slots as slotmod
    plan = slotmod.compile_slots(packets[rid])
    for s in plan["slots"]:
        rows[(plan["kind"], s["field"])] = max(rows[(plan["kind"], s["field"])], len(s["symbols"]))
for key in sorted(rows):
    print("   %-16s %-14s max symbols %d" % (key[0], key[1], rows[key]))
print()
print("questions per held-back world:", dict(Counter(
    by_id[r]["source_world_id"][-10:] for r in held)))
print("eligible held questions by kind (the gate population, from the pipeline review):")
print("  correspondence 5, edge_account 5, reach 9, analogy 5, parts 5 = 29 relational")
print("  definition 5, context 5 = 10 direct-read")
