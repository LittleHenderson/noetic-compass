"""RT5 step 3 (descriptive, NOT rule-bearing):
 (1) cross-check my pure reconstruction against the project's own reader (pointer_inputs.read_packet, byte-identical
     to the run copy) on all 59 dev packets and all 358 trained packets;
 (2) Helm's answer-state mix on all 59 dev questions, per receipt;
 (3) Helm's DIRECT and parts accuracy on the FOUR-node course at p10 (in-range ranks), trained vs held-back records;
 (4) world-level count features (nodes at in-degree 0 / out-degree 0) trained vs dev;
 (5) parts misses: which nodes Helm returned, with their (in, out, participant) profile.
No torch. Usage: python -B rt5_context.py <ROOT>
"""
import json, os, sys
from collections import Counter, defaultdict

ROOT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(ROOT, "records", "typed_pointer_001")
sys.path.insert(0, os.path.join(ROOT, "research", "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import pointer_inputs, worker_contract  # noqa: E402

RECEIPTS = ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")] + \
           ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]
data = json.load(open(os.path.join(HERE, "rt5_inputs.json"), encoding="utf-8"))
mine_trained, mine_dev = data["trained"], data["dev"]

# ---------- (1) cross-check against the real reader ----------
pointer_inputs.label_cache(ROOT)
frozen = json.load(open(os.path.join(ROOT, "records/typed_course_001/checks_002/public_course.json"), encoding="utf-8"))
pm = json.load(open(os.path.join(BASE, RECEIPTS[0], "checkpoints", "protocol_material.json"), encoding="utf-8"))
trained_ids = set(pm["trained_record_ids"]); held_ids = set(pm["held_back_record_ids"])
course_packets = dict(worker_contract.public_packets(frozen))


def compare(mine, real):
    bad = []
    if mine["whole"] != real["query"]["whole"]: bad.append("whole")
    if mine["part"] != real["query"]["part"]: bad.append("part")
    if mine["world_count"] != real["query"]["world_count"]: bad.append("world_count")
    if sorted(mine["worlds"]) != sorted(real["worlds"]): bad.append("world_set")
    for wid, g in real["worlds"].items():
        m = mine["worlds"][wid]
        if [list(e) for e in m["edges"]] != g["contains"]: bad.append("edges:" + wid[:14])
        for row, node in zip(m["rows"], g["nodes"]):
            if (row["is_declared_whole"], row["participant"], row["is_whole_arg"], row["is_part_arg"]) != \
               (node["is_declared_whole"], node["is_participant"], node["is_whole_argument"], node["is_part_argument"]):
                bad.append("node:" + wid[:14]); break
        if g["is_focus"] != m["rows"][0]["is_focus"] or g["is_target"] != m["rows"][0]["is_target"]:
            bad.append("focus/target:" + wid[:14])
    return bad


mism = Counter()
for rid in trained_ids:
    real = pointer_inputs.read_packet(course_packets[rid])
    for b in compare(mine_trained[rid], real): mism["trained:" + b.split(":")[0]] += 1
for p in pm["development"]["packets"]:
    real = pointer_inputs.read_packet(p)
    for b in compare(mine_dev[p["record"]["record_id"]], real): mism["dev:" + b.split(":")[0]] += 1
print("(1) reconstruction vs pointer_inputs.read_packet: trained %d packets, dev %d packets, mismatches %s"
      % (len(trained_ids), len(pm["development"]["packets"]), dict(mism) or "NONE"))


# ---------- truth (checker reconstruction; R2 validated it 42/312 on dev) ----------
def kids_of(r):
    k = defaultdict(list)
    for s, t in r["worlds"][r["focus_world_id"]]["edges"]: k[s].append(t)
    return k


def truth_state(r):
    k = kids_of(r)
    if r["kind"] == "parts": return "PARTS"
    if r["kind"] != "reach": return None
    if r["part"] in k.get(r["whole"], []): return "DIRECT"
    seen, stack = set(), list(k.get(r["whole"], []))
    while stack:
        u = stack.pop()
        if u == r["part"]: return "VIA"
        if u in seen: continue
        seen.add(u); stack.extend(k.get(u, []))
    return "ABSENT"


# ---------- (2) answer mix on all 59 dev ----------
print("\n(2) Helm's answer state on all 59 dev questions at p10 (reach answers only; parts separately):")
dev_truth = {rid: truth_state(r) for rid, r in mine_dev.items()}
print("    truth mix:", dict(Counter(dev_truth.values())))
for rd in RECEIPTS:
    pred = {p["record_id"]: p["answer"]["value"] for p in json.load(open(os.path.join(BASE, rd, "checkpoints", "development_p10_predictions.json"), encoding="utf-8"))["predictions"]}
    c = Counter(pred[rid].get("state") for rid in mine_dev if dev_truth[rid] != "PARTS")
    print("    %-34s reach answers %s" % (rd, dict(c)))

# ---------- (3) four-node course at p10 ----------
print("\n(3) FOUR-node course at p10 (ranks 0-3, in range): DIRECT and parts accuracy, trained vs held-back records")
course_read = {}
for rid in list(trained_ids) + list(held_ids):
    r = mine_trained.get(rid)
    if r is None:
        row = next(x for x in frozen["registry"] if x["record_id"] == rid)
        # rebuild with step-1 logic via the real reader fields we need
        real = pointer_inputs.read_packet(course_packets[rid])
        g = real["worlds"][real["focus_world_id"]]
        r = {"kind": real["query"]["kind_name"], "whole": real["query"]["whole"], "part": real["query"]["part"],
             "focus_world_id": real["focus_world_id"],
             "worlds": {real["focus_world_id"]: {"edges": [tuple(e) for e in g["contains"]]}}}
    course_read[rid] = r
agree = Counter()
for rd in RECEIPTS:
    ck = os.path.join(BASE, rd, "checkpoints")
    rows = {x["record_id"]: x for x in json.load(open(os.path.join(ck, "course_p10_scoring.json"), encoding="utf-8"))["rows"]}
    pred = {p["record_id"]: p["answer"]["value"] for p in json.load(open(os.path.join(ck, "course_p10_predictions.json"), encoding="utf-8"))["predictions"]}
    tab = defaultdict(lambda: [0, 0])
    for rid, r in course_read.items():
        st = truth_state(r)
        if st not in ("DIRECT", "PARTS"):
            if st in ("VIA", "ABSENT"):
                tab[("held" if rid in held_ids else "trained", st)][0] += int(rows[rid]["correct"])
                tab[("held" if rid in held_ids else "trained", st)][1] += 1
            continue
        split = "held" if rid in held_ids else "trained"
        tab[(split, st)][0] += int(rows[rid]["correct"]); tab[(split, st)][1] += 1
        # validate truth reconstruction against the saved checker bit
        v = pred[rid]
        if st == "DIRECT":
            same = v.get("state") == "DIRECT"
        else:
            same = sorted(int(x.rpartition("/n")[2]) for x in v.get("nodes", [])) == sorted(kids_of(r).get(r["whole"], []))
        agree[(bool(rows[rid]["correct"]), same)] += 1
    print("    %-34s %s" % (rd, "; ".join("%s %s %d/%d" % (k[0], k[1], v[0], v[1]) for k, v in sorted(tab.items()))))
print("    truth-reconstruction check on course DIRECT/parts (saved correct, my equality):", dict(agree))

# ---------- (4) world-level count features ----------
def counts(readings, kinds=("reach", "parts")):
    c0in, c0out, n = Counter(), Counter(), Counter()
    for r in readings.values():
        if r["kind"] not in kinds: continue
        w = r["worlds"][r["focus_world_id"]]
        c0in[sum(1 for x in w["rows"] if x["in"] == 0)] += 1
        c0out[sum(1 for x in w["rows"] if x["out"] == 0)] += 1
    return dict(sorted(c0in.items())), dict(sorted(c0out.items()))
print("\n(4) per-question focus-world count of nodes at in-degree 0 / out-degree 0 (reach+parts):")
print("    trained:", counts(mine_trained))
print("    dev    :", counts(mine_dev))

# ---------- (5) parts misses ----------
print("\n(5) dev parts questions: true children vs Helm's returned nodes, each node as (rank, in, out, participant)")
for rid, r in sorted(mine_dev.items()):
    if r["kind"] != "parts": continue
    rows = r["worlds"][r["focus_world_id"]]["rows"]
    prof = lambda n: (n, rows[n]["in"], rows[n]["out"], rows[n]["participant"])
    true = sorted(kids_of(r).get(r["whole"], []))
    leaves_in1 = sorted(x["rank"] for x in rows if x["in"] >= 1 and x["out"] == 0)
    print("   %s whole %s true %s | leaves(in>=1,out=0) %s" % (rid[:20], prof(r["whole"]), [prof(n) for n in true], leaves_in1))
    for rd in RECEIPTS:
        pred = {p["record_id"]: p["answer"]["value"] for p in json.load(open(os.path.join(BASE, rd, "checkpoints", "development_p10_predictions.json"), encoding="utf-8"))["predictions"]}
        got = sorted(int(x.rpartition("/n")[2]) for x in pred[rid].get("nodes", []))
        print("       %-34s returned %s" % (rd, [prof(n) for n in got]))
