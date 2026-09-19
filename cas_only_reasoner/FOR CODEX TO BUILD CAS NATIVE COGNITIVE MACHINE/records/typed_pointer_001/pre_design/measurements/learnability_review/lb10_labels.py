"""LB10 — do node LABEL words only enable memorisation? plus the exact tokenizer and
world-encoding cost of reading them.

Counting rules, stated so they can be checked:
  * "occurs in the training material" is counted the way the packet is built, not the way
    the machine reads it: a label occurs if its text appears in any record a TRAINED
    presentation carries.
  * "the focus of a trained question" means the packet's focus world is that label's world.
"""
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path[:0] = [str(CNCM), str(CNCM / "research/CAS_META_2_COMPOSITION")]
assert "torch" not in sys.modules
from cas_meta2.typed_teaching import practice_contract as c, slots, tokenization

frozen, tokenizer, devdoc = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
heldset, trainedset = set(held), set(trained)
packets = dict(c.public_packets(frozen))
worlds = {w["world_id"]: w for w in frozen["bank"]["worlds"]}
heldworlds = list(c.held_worlds(frozen))
by_id = {r["record_id"]: r for r in frozen["registry"]}

label_world = {}
for wid, w in worlds.items():
    for n in w["nodes"]:
        label_world.setdefault(n["label"], set()).add(wid)
all_labels = sorted(label_world)
print("distinct node labels in the whole 64-world bank: %d ; nodes: %d"
      % (len(all_labels), sum(len(w["nodes"]) for w in worlds.values())))
shared = {l: sorted(v) for l, v in label_world.items() if len(v) > 1}
print("labels used by more than one world: %d" % len(shared))
heldlabels = {n["label"]: wid for wid in heldworlds for n in worlds[wid]["nodes"]}
print("held-world node labels: %d over %d worlds" % (len(heldlabels), len(heldworlds)))

# --- 1. textual occurrence anywhere in the training material ---
trained_text = {rid: json.dumps(packets[rid], sort_keys=True) for rid in trained if rid in packets}
occurs_anywhere = {}
for label, wid in heldlabels.items():
    hits = [rid for rid, txt in trained_text.items() if label in txt]
    occurs_anywhere[label] = hits
print()
print("held-world node labels whose TEXT occurs in at least one trained record: %d/%d"
      % (sum(1 for v in occurs_anywhere.values() if v), len(heldlabels)))
print("total (label, trained record) textual occurrences: %d"
      % sum(len(v) for v in occurs_anywhere.values()))

# --- 2. the focus of a trained question ---
focused_labels = set()
focus_counts = Counter()
for rid in trained:
    p = packets.get(rid)
    if p is None:
        continue
    fw = p["source"]["focus_world_id"]
    for n in worlds[fw]["nodes"]:
        focused_labels.add(n["label"])
        focus_counts[n["label"]] += 1
print()
print("held-world node labels that are the FOCUS of a trained question: %d/%d"
      % (sum(1 for l in heldlabels if l in focused_labels), len(heldlabels)))
print("distinct labels appearing as a trained question's focus (any world): %d" % len(focused_labels))

# --- 3. read by the pointer reader, which encodes every world a slot lists ---
read_counts = Counter()
presentations = 0
world_choice_records = 0
for rid in trained:
    p = packets.get(rid)
    if p is None:
        continue
    plan = slots.compile_slots(p)
    fields = {s["field"] for s in plan["slots"]}
    listy = bool({"kind_ref", "function_ref", "setting_ref", "world_id"} & fields)
    ids = [x["world_id"] for x in p["source"]["worlds"]] if listy else [p["source"]["focus_world_id"]]
    if plan["kind"] == "correspondence":
        ids = ids + [p["record"]["query"]["arguments"]["target_world_id"]]
    seen = set(ids)
    for wid in seen:
        for n in worlds[wid]["nodes"]:
            read_counts[n["label"]] += 1
    presentations += len(seen)
    world_choice_records += int(listy)

# the practice schedule: 10 passes over the trained records
batches, stats = c.practice_schedule(frozen)
presentations_by_record = Counter()
for b in batches:
    for rid in b["record_ids"]:
        presentations_by_record[rid] += 1
read_train = Counter()
for rid, times in presentations_by_record.items():
    p = packets.get(rid)
    if p is None:
        continue
    plan = slots.compile_slots(p)
    fields = {s["field"] for s in plan["slots"]}
    listy = bool({"kind_ref", "function_ref", "setting_ref", "world_id"} & fields)
    ids = [x["world_id"] for x in p["source"]["worlds"]] if listy else [p["source"]["focus_world_id"]]
    if plan["kind"] == "correspondence":
        ids = ids + [p["record"]["query"]["arguments"]["target_world_id"]]
    for wid in set(ids):
        for n in worlds[wid]["nodes"]:
            read_train[n["label"]] += times
print()
print("over the 1,470-update schedule (%d record presentations), how often the pointer reader"
      % stats["presentations"])
print("would embed a held-world node label:")
tot = 0
for label in sorted(heldlabels):
    n = read_train.get(label, 0)
    tot += n
    print("   %-14s world %s  read %d times" % (label, heldlabels[label][-10:], n))
print("   TOTAL held-world label reads during training: %d" % tot)
print("   distinct held-world labels ever read during training: %d/%d"
      % (sum(1 for l in heldlabels if read_train.get(l)), len(heldlabels)))
print()
print("over the 564 records (one pass), worlds the reader must encode: %d" % presentations)
print("   records whose slots list every world (kind_ref/function_ref/setting_ref/world_id): %d" % world_choice_records)

# --- 4. tokenizer cost ---
def tsize(text):
    return len(tokenizer.encode_text(text))


t0 = time.perf_counter()
for _ in range(20):
    tokenizer.encode_text("Determiner")
dt = (time.perf_counter() - t0) / 20
print()
print("FrameTokenizer.encode_text: %.4f s per call" % dt)
node_tokens = sum(tsize(n["label"]) for w in worlds.values() for n in w["nodes"])
print("node-label encodes for one pass over all 64 worlds: %d calls, %.1f s"
      % (sum(len(w["nodes"]) for w in worlds.values()), dt * sum(len(w["nodes"]) for w in worlds.values())))
palbe = 0
for rid in trained:
    p = packets.get(rid)
    if p is None:
        continue
    plan = slots.compile_slots(p)
    fields = {s["field"] for s in plan["slots"]}
    listy = bool({"kind_ref", "function_ref", "setting_ref", "world_id"} & fields)
    ids = [x["world_id"] for x in p["source"]["worlds"]] if listy else [p["source"]["focus_world_id"]]
    palbe += sum(len(worlds[i]["nodes"]) for i in ids)
print("node-label encodes for one pass over the 358 trained records: %d" % palbe)
print("node-label encodes for the full 10-pass run: %d  -> %.0f s at %.4f s/call"
      % (palbe * 10, palbe * 10 * dt, dt))
decl = sum(tsize(w["declarations"][k]) for w in worlds.values() for k in ("domain", "kind", "function", "setting"))
print("declaration text encodes for one pass over all 64 worlds: %d" % decl)
print("distinct node labels: %d -> a one-time cache of %d encodes (%.1f s)"
      % (len(all_labels), len(all_labels), len(all_labels) * dt))
print("distinct declaration strings: %d"
      % len({w["declarations"][k] for w in worlds.values() for k in ("domain", "kind", "function", "setting")}))

# --- 5. is any label needed by any answer rule? ---
print()
print("checker rules that mention a label or a ref text:")
src = Path(CNCM / "research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/checker.py").read_text(encoding="utf-8")
for token in ("label", "ref"):
    hits = [i + 1 for i, line in enumerate(src.splitlines()) if token in line]
    print("   token %-6s appears on checker.py lines %s" % (token, hits))

# --- 6. label duplicates ACROSS worlds: does a label ever pick out more than one world? ---
print()
print("labels shared by several worlds (so the text alone cannot identify the world):")
for label, wid in sorted(shared.items()):
    print("   %-16s worlds %d  (held among them: %d)" % (label, len(wid), sum(1 for w in wid if w in set(heldworlds))))
print("held-world labels that are also labels of a non-held world: %d"
      % sum(1 for l, wid in heldlabels.items() if len(label_world[l]) > 1))
