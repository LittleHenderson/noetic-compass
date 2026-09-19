"""Exact structural classes of the 64 bank worlds. No refinement assumption; partitions checked."""
import sys
from collections import Counter, defaultdict
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c

frozen, tokenizer, devdoc = c.load_material(CNCM)
worlds = {w["world_id"]: w for w in frozen["bank"]["worlds"]}
heldworlds = set(c.held_worlds(frozen))

groups = defaultdict(list)
for wid, w in sorted(worlds.items()):
    ind, outd = Counter(), Counter()
    for e in w["contains"]:
        outd[e["source"]] += 1
        ind[e["target"]] += 1
    sig = tuple(sorted((ind.get(n["ref"], 0), outd.get(n["ref"], 0)) for n in w["nodes"]))
    groups[sig].append(wid)

print("grouping the 64 bank worlds by the SORTED multiset of (in-degree, out-degree) pairs")
print("(this is the strongest structural invariant obtainable from the draft's per-node reading")
print(" after one message-passing round: in-degree and out-degree are the two messages).")
print()
for sig, keys in sorted(groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))):
    print("degrees %s  worlds %d  held-in-group %d" % (sig, len(keys), sum(1 for k in keys if k in heldworlds)))
print("total worlds %d in %d degree groups" % (sum(len(v) for v in groups.values()), len(groups)))
print()
print("NOTE: two worlds can carry the SAME sorted degree multiset and still be non-isomorphic;")
print("the degree multiset is exactly the 1-WL signature only for graphs the refinement separates.")
print("The following counts are over the degree groups, computed exactly and without any")
print("partition-through-validation shortcut:")
tot = 0
for sig, keys in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    if len(keys) < 2:
        continue
    n = len(keys) * (len(keys) - 1) // 2
    tot += n
    print("   degrees %s: %d pairs, %d worlds" % (sig, n, len(keys)))
print("pairs sharing a degree multiset, total %d of %d bank pairs"
      % (tot, 64 * 63 // 2))

print()
print("per-world: does the number of distinct degree classes equal the number of nodes?")
part = Counter()
for wid, w in sorted(worlds.items()):
    ind, outd = Counter(), Counter()
    for e in w["contains"]:
        outd[e["source"]] += 1
        ind[e["target"]] += 1
    pairs = [(ind.get(n["ref"], 0), outd.get(n["ref"], 0)) for n in w["nodes"]]
    part[(len(pairs), len(set(pairs)))] += 1
for k in sorted(part):
    print("   nodes %d, distinct (in,out) classes %d : %d worlds" % (k[0], k[1], part[k]))

print()
print("the exact edge structure of one representative per degree group:")
for sig, keys in sorted(groups.items(), key=lambda kv: (-len(kv[1]), str(kv[0]))):
    w = worlds[keys[0]]
    refs = sorted(n["ref"] for n in w["nodes"])
    idx = {r: i for i, r in enumerate(refs)}
    edges = sorted((idx[e["source"]], idx[e["target"]]) for e in w["contains"])
    print("   degrees %s -> edges %s (over sorted refs), example %s" % (sig, edges, keys[0][-12:]))
