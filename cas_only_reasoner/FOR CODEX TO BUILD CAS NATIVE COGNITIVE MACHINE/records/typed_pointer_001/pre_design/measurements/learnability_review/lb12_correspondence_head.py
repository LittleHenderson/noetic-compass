"""LB12 — correspondence: how often would the edge-free per-node scoring head be WRONG?

The head is logit(v) = <W_p q_slot, h_v> with q_slot = q + h_source, and the declared
answer includes h_source's NODE STATE. Section 2.1 says node features are
"ONLY its own raw fields ... NO node alias index, NO degree counts, NO derived relation".
So the per-node score has no input that depends on the target world's EDGES; its only
question-relevant input is the source world's node state. The decision is the best
SYNTACTIC bijection under summed node scores.

A machine in that position can at best place the source node with source-degree class d
onto a target node with target-degree class d (degree class is the only structure-free
thing it can compare), and the argmax will prefer a permutation. This script counts the
records where that route is correct and where it is not.
"""
import sys
from collections import Counter
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c, checker, slots

frozen, tokenizer, devdoc = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
heldset, trainedset = set(held), set(trained)
packets = dict(c.public_packets(frozen))


def side(rid):
    return "held" if rid in heldset else "trained" if rid in trainedset else "excluded"


rows = []
for rid in sorted(packets):
    p = packets[rid]
    q = p["record"]["query"]
    if q["kind"] != "correspondence":
        continue
    worlds = {w["world_id"]: w for w in p["source"]["worlds"]}
    focus = worlds[q["focus_world_id"]]
    target = worlds[q["arguments"]["target_world_id"]]
    other = q["focus_world_id"] == q["arguments"]["target_world_id"]
    plan = slots.compile_slots(p)
    # the source-node-marked slots, in the declared candidate order
    by_ref = {s["coordinates"][0]: s for s in plan["slots"] if s["field"] == "mapping_target"}
    src_refs = sorted(by_ref)
    tgt_refs = sorted(n["ref"] for n in target["nodes"])
    adm = checker.derive_target(p["source"], q)
    pairs_list = [a["value"]["pairs"] for a in adm["admissible_answers"]]
    # the edge-blind head's only usable signal: source node state. Best it can do:
    # any permutation; check every permutation for membership in the admissible set.
    from itertools import permutations
    ok = 0
    total = 0
    for perm in permutations(tgt_refs):
        cand = {"status": "MAPPING",
                "pairs": [{"source": a, "target": b} for a, b in zip(src_refs, perm)]}
        total += 1
        ok += int(checker._canonical(cand) in {checker._canonical({"status": "MAPPING", "pairs": pl}) for pl in pairs_list})
    rows.append({"rid": rid, "side": side(rid), "same_world": other,
                 "n_valid": ok, "n_perms": total, "n_admissible": len(pairs_list)})

print("correspondence records: %d" % len(rows))
for s in ("held", "trained", "excluded"):
    sub = [r for r in rows if r["side"] == s]
    if not sub:
        continue
    print("  %-9s records %d ; admissible mappings among all permutations: %s"
          % (s, len(sub), sorted(Counter(r["n_admissible"] for r in sub).items())))
    print("           identity permutation is valid in %d of %d records"
          % (sum(1 for r in sub if r["same_world"]), len(sub)))
print()
print("how narrow is the correct set? (a permutation chosen at random from all syntactic")
print("bijections would be correct with probability n_admissible/n_perms)")
hist = Counter((r["n_admissible"], r["n_perms"]) for r in rows)
for key in sorted(hist):
    print("   %d valid of %d permutations : %d records" % (key[0], key[1], hist[key]))
print()
print("held detail:")
for r in rows:
    if r["side"] == "held":
        print("   %s same_world=%-5s valid %d/%d" % (r["rid"][-12:], r["same_world"], r["n_valid"], r["n_perms"]))

# Is the identity permutation ever WRONG (so a constant "point at my own node" answer fails)?
print()
print("identity mapping admissible? by side:",
      dict(Counter((r["side"], r["same_world"]) for r in rows)))
