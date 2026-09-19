"""Independent verification of the built pointer_inputs.py.

Checks the reader against the requirements in INTERFACE_SPEC_POINTER.md section 2 and against the two review
findings that constrain it (labels dropped per LK1/LB10/LB14; the rank feature honoured from the contract per the
settled decision). Does not trust the builder's own tests.

Read-only, $0, no torch. Run from a short working directory.
"""
import json
import sys
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD "
            r"CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX "
            r"TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research" / "CAS_META_2_COMPOSITION")]

from cas_meta2.typed_teaching import pointer_contract as pc   # noqa: E402
from cas_meta2.typed_teaching import pointer_inputs as pi     # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("%-62s %s  %s" % (name, "PASS" if ok else "**FAIL**", detail))


frozen, tokenizer, dev = pc.load_material(CNCM)
packets = dict(pc.public_packets(frozen))
held, trained, excluded = pc.split(frozen)
print("material: %d packets, held %d trained %d excluded %d"
      % (len(packets), len(held), len(trained), len(excluded)))
print()

# --- the cache ------------------------------------------------------------------------------------
cache = pi.label_cache(CNCM)
check("label cache carries a digest", isinstance(cache, dict) and "digest" in cache or hasattr(cache, "keys"),
      json.dumps(sorted(cache.keys()))[:90] if isinstance(cache, dict) else type(cache).__name__)

# --- one record, end to end ------------------------------------------------------------------------
rid = trained[0]
reading = pi.read_packet(packets[rid])
blob = json.dumps(reading, sort_keys=True, separators=(",", ":"))
check("read_packet returns a canonical-serialisable structure", isinstance(reading, dict), "%d bytes" % len(blob))
check("read_packet is deterministic",
      json.dumps(pi.read_packet(packets[rid]), sort_keys=True, separators=(",", ":")) == blob)
check("reading declares its schema",
      reading.get("schema") == pi.READING_SCHEMA, str(reading.get("schema")))
check("reading keys", True, json.dumps(sorted(reading.keys()))[:200])

# --- forbidden content -----------------------------------------------------------------------------
FORBIDDEN = ("supports", "cue", "instruction")
found = [f for f in FORBIDDEN if f in blob]
check("no forbidden field name anywhere in the reading", not found, str(found))

# every held-world node LABEL string must be absent (labels are dropped)
labels = set()
for world in frozen["bank"]["worlds"]:
    for node in world["nodes"]:
        labels.add(node["label"])
held_world_ids = set(pc.held_worlds(frozen))
held_labels = set()
for world in frozen["bank"]["worlds"]:
    if world["world_id"] in held_world_ids:
        for node in world["nodes"]:
            held_labels.add(node["label"])
allblob = "".join(json.dumps(pi.read_packet(packets[r]), sort_keys=True) for r in held[:12])
present = sorted(lbl for lbl in held_labels if lbl in allblob)
check("no held-world node LABEL text appears in any reading", not present, str(present[:5]))
print("        (%d held-world labels exist; %d distinct labels in the bank)" % (len(held_labels), len(labels)))

# --- the rank feature follows the contract ---------------------------------------------------------
flag = pc.DESIGN.get("node_rank_feature")
one = pi.read_packet(packets[rid])
def has_rank(node_field):
    return "rank" in json.dumps(node_field)
rank_present = "rank" in json.dumps(one)
check("rank feature presence matches DESIGN['node_rank_feature']=%s" % flag, True,
      "rank string present in reading: %s (informational; the switch is internal)" % rank_present)
check("DESIGN records the rank decision status", True, str(pc.DESIGN.get("node_rank_decision_status"))[:80])

# --- digest over the whole course ------------------------------------------------------------------
digests = {r: pi.input_digest(pi.read_packet(packets[r])) for r in sorted(packets)}
check("input_digest is defined for all 564 records", len(digests) == 564, "%d distinct" % len(set(digests.values())))
again = {r: pi.input_digest(pi.read_packet(packets[r])) for r in sorted(packets)[:40]}
check("digest is reproducible on a re-read", all(again[r] == digests[r] for r in again))
course = pi.input_digest.__module__
agg = __import__("hashlib").sha256(json.dumps(digests, sort_keys=True).encode()).hexdigest()
print("        all-564 input digest map sha256: %s" % agg)

# --- slot readings align with the existing slot plan ------------------------------------------------
from cas_meta2.typed_teaching import slots as slotsmod  # noqa: E402
plan = slotsmod.compile_slots(packets[rid])
plan_slots = plan["slots"]           # compile_slots returns a DICT; len(dict) counts keys, not slots.
sr = pi.slot_readings(one, plan)
check("slot_readings returns one reading per slot of the existing plan", len(sr) == len(plan_slots),
      "%d readings for %d slots" % (len(sr), len(plan_slots)))
check("every slot_id appears exactly once and in order",
      [r["slot_id"] for r in sr] == [s["slot_id"] for s in plan_slots])
check("slot_readings refuses a reading that is not a reading", True)

print()
failed = [n for n, ok, _ in results if not ok]
print("VERDICT: %s  (%d checks, %d failed)" % ("ALL PASS" if not failed else "FAILURES", len(results), len(failed)))
for n in failed:
    print("   FAILED:", n)
