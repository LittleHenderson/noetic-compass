"""Pure-Python facts about the course material (no torch)."""
import json, sys
from collections import Counter
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
for p in (CNCM, CNCM / "research/CAS_META_2_COMPOSITION"):
    sys.path.insert(0, str(p))
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c, slots

frozen, tok, dev = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
packets = dict(c.public_packets(frozen))
print("counts", len(held), len(trained), len(excluded), len(packets))
k = next(iter(packets))
p = packets[k]
print("packet keys", list(p), "source keys", list(p["source"]), "record keys", list(p["record"]))
w = p["source"]["worlds"][0]
print("world keys", list(w))
print(json.dumps(w)[:1500])
print("query", json.dumps(p["record"]["query"])[:800])
print("n worlds", len(p["source"]["worlds"]))
sizes = Counter(len(w["nodes"]) for w in frozen["bank"]["worlds"])
print("bank world node counts", sizes)
# depth distribution in practice schedule
batches, stats = c.practice_schedule(frozen)
print("stats", {k: v for k, v in stats.items() if k not in ("held_worlds",)})
print("depth per batch", Counter(b["depth"] for b in batches))
by_id = {r["record_id"]: r for r in frozen["registry"]}
pres_depth = Counter((by_id[r]["query"]["kind"], b["depth"]) for b in batches for r in b["record_ids"])
print("kind x depth presentations", sorted(pres_depth.items()))
# kinds per batch
kinds_per_batch = [set(by_id[r]["query"]["kind"] for r in b["record_ids"]) for b in batches]
print("batch size dist", Counter(len(b["record_ids"]) for b in batches))
for kind in c.KINDS:
    missing = sum(1 for s in kinds_per_batch if kind not in s)
    print("batches lacking", kind, missing, "of", len(batches))
print("distinct kinds per batch", Counter(len(s) for s in kinds_per_batch))
interf = c.interference_batches(frozen)
print("interference kinds", Counter(frozenset(by_id[r]["query"]["kind"] for r in b["record_ids"]) for b in interf))
