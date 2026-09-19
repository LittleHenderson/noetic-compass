"""Probe: exact shapes of the public packets, world records and development panel."""
import sys
from collections import Counter
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c, slots, development

frozen, tokenizer, developmentdoc = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
packets = dict(c.public_packets(frozen))
print("split", len(held), len(trained), len(excluded), "packets", len(packets))
print("frozen keys", sorted(frozen))
print("bank keys", sorted(frozen["bank"]))
print("registry row keys", sorted(frozen["registry"][0]))

w = frozen["bank"]["worlds"][0]
print("world keys", sorted(w))
print("node", w["nodes"][0])
print("contains", w["contains"][:2])
print("declarations", w["declarations"])
print("inventory_scope" in w, w.get("inventory_scope"))
print("bank world node counts", Counter(len(x["nodes"]) for x in frozen["bank"]["worlds"]))
print("bank world edge counts", Counter(len(x["contains"]) for x in frozen["bank"]["worlds"]))

p = packets[held[0]]
print("packet keys", sorted(p))
print("source keys", sorted(p["source"]))
print("n worlds in packet source", len(p["source"]["worlds"]))
print("n world_ids in bank list", len(p["source"]["bank"]["world_ids"]))
print("bank world_ids == sorted world ids?", p["source"]["bank"]["world_ids"] == sorted(x["world_id"] for x in p["source"]["worlds"]))
print("record keys", sorted(p["record"]))
print("query", p["record"]["query"])
print("supports", p["record"]["supports"])
print("cue", p["record"]["cue"])
print("instruction", p["record"]["instruction"][:120])

# which worlds appear with full node data in a packet?
ids = {x["world_id"] for x in p["source"]["worlds"]}
print("node data present for all 64 bank worlds?", len(ids) == 64)
print("does packet source contain held node labels for non-focus worlds? (should: only data, no leak concept)")
heldset = set(c.held_worlds(frozen))
print("packets whose focus world is held", sum(1 for k, q in packets.items() if q["source"]["focus_world_id"] in heldset))

# development panel
dev = c.development_packets(developmentdoc)
print("development packets", len(dev))
k0 = sorted(dev)[0]
dp = dev[k0]
print("dev packet source keys", sorted(dp["source"]))
print("dev focus", dp["source"]["focus_world_id"])
print("dev n worlds", len(dp["source"]["worlds"]))
print("dev kind counts", Counter(x["record"]["query"]["kind"] for x in dev.values()))
print("dev rules", Counter(x["record"]["query"]["rule"] for x in dev.values()))
print("dev node counts of focus worlds", Counter(len(x) for x in {q["record"]["query"]["focus_world_id"]: next(w["nodes"] for w in q["source"]["worlds"] if w["world_id"] == q["record"]["query"]["focus_world_id"]) for q in dev.values()}.values()))
print("dev focus node counts", Counter(len(next(w["nodes"] for w in q["source"]["worlds"] if w["world_id"] == q["record"]["query"]["focus_world_id"])) for q in dev.values()))
fw = next(w for w in dp["source"]["worlds"] if w["world_id"] == dp["source"]["focus_world_id"])
print("dev focus world keys", sorted(fw))
print("dev focus node", fw["nodes"][0])
print("dev declarations", fw["declarations"])
print("dev edges", len(fw["contains"]))
print("dev declared_whole", fw["declared_whole"])
print("dev inventory_scope", fw.get("inventory_scope"))
n10 = [q for q in dev.values() if len(next(w["nodes"] for w in q["source"]["worlds"] if w["world_id"] == q["source"]["focus_world_id"])) == 10]
print("dev packets with 10-node focus", len(n10))
sizes = Counter(len(next(w["nodes"] for w in q["source"]["worlds"] if w["world_id"] == q["source"]["focus_world_id"])) for q in dev.values())
print("dev focus sizes", dict(sizes))
# MAX_ISOMORPHISM_NODES check
from cas_meta2.typed_teaching import checker
print("checker.MAX_ISOMORPHISM_NODES", checker.MAX_ISOMORPHISM_NODES)
print("any dev focus world above the checker bound?", any(len(next(w["nodes"] for w in q["source"]["worlds"] if w["world_id"] == q["source"]["focus_world_id"])) > checker.MAX_ISOMORPHISM_NODES for q in dev.values()))
# do dev packets work through derive_target?
q = n10[0]["record"]["query"]
try:
    t = checker.derive_target(n10[0]["source"], q)
    print("dev derive_target ok for 10-node reach", t["kind"], len(t["admissible_answers"]))
except Exception as e:
    print("dev derive_target FAILED", type(e).__name__, e)
q2 = [x for x in dev.values() if x["record"]["query"]["kind"] == "parts"][0]["record"]["query"]
try:
    t = checker.derive_target([x for x in dev.values() if x["record"]["query"]["kind"] == "parts"][0]["source"], q2)
    print("dev derive_target ok for parts", len(t["admissible_answers"]))
except Exception as e:
    print("dev derive_target FAILED parts", type(e).__name__, e)
# node alias width: slot symbols
plan = slots.compile_slots(dp)
print("dev plan kinds", plan["kind"], "slots", len(plan["slots"]))
print("max slot symbol count dev", max(len(s["symbols"]) for s in plan["slots"]))
