"""Do the draft's per-node FLAGS (declared_whole, participant rank, primary rank) answer the 'relational'
kinds without reading any edge? Mechanism-free flag rules, scored with the private checker (no torch)."""
import sys
from collections import Counter
from pathlib import Path

CNCM = Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
for p in (CNCM, CNCM / "research/CAS_META_2_COMPOSITION", CNCM / "records/typed_practice_001"):
    sys.path.insert(0, str(p))
from cas_meta2.typed_teaching import practice_contract as c, checker, answers
import evaluate_gates as eg
assert "torch" not in sys.modules

frozen, _, _ = c.load_material(CNCM)
held, trained, excluded = c.split(frozen)
packets = dict(c.public_packets(frozen))
worlds = {w["world_id"]: w for w in frozen["bank"]["worlds"]}

def flag_answer(row):
    q = row["query"]; w = worlds[q["focus_world_id"]]; d = w["declarations"]
    parts = list(d["participants"]); whole = w["declared_whole"]
    if q["kind"] == "parts":
        a = q["arguments"]["whole"]
        return {"nodes": sorted(p for p in parts if p != a)} if a == whole else {"nodes": []}
    if q["kind"] == "edge_account":
        return {"edges": [{"source": whole, "target": p} for p in sorted(p for p in parts if p != whole)]}
    if q["kind"] == "reach":
        a, b = q["arguments"]["whole"], q["arguments"]["part"]
        return {"state": "DIRECT", "via": None} if a == whole and b in parts else {"state": "ABSENT", "via": None}
    return None

def correct(row, value):
    p = packets[row["record_id"]]
    ans = answers.make_answer(p["source"], row["query"], value)
    return checker.check_answer(p["source"], row["query"], ans)["correct"]

by_id = {r["record_id"]: r for r in frozen["registry"]}
held_q = c.held_back_questions(frozen)
eligible, _, _ = eg.eligible_questions(frozen, set(trained), held_q)
kind_of = {r["query"]["query_id"]: r["query"]["kind"] for r in frozen["registry"]}
res = Counter(); tot = Counter()
for q in eligible:
    kind = kind_of[q]
    if kind not in ("parts", "edge_account", "reach"):
        continue
    ok = all(correct(by_id[r], flag_answer(by_id[r])) for r in held_q[q])
    tot[kind] += 1; res[kind] += ok
print("held eligible questions solved by edge-free flag rules", {k: "%d/%d" % (res[k], tot[k]) for k in tot})
rec = Counter(); rtot = Counter()
for r in frozen["registry"]:
    if r["query"]["kind"] in ("parts", "edge_account", "reach"):
        s = "held" if r["record_id"] in set(held) else "trained" if r["record_id"] in set(trained) else "excl"
        rtot[(s, r["query"]["kind"])] += 1; rec[(s, r["query"]["kind"])] += correct(r, flag_answer(r))
print("records solved by flag rules", {"%s/%s" % k: "%d/%d" % (rec[k], rtot[k]) for k in sorted(rtot)})
# how often is the declared whole the unique source-only node, and participants == its children?
same = sum(1 for w in worlds.values() if sorted(p for p in w["declarations"]["participants"] if p != w["declared_whole"])
           == sorted(e["target"] for e in w["contains"] if e["source"] == w["declared_whole"]))
print("worlds where participants minus whole == children of declared whole:", same, "of", len(worlds))
