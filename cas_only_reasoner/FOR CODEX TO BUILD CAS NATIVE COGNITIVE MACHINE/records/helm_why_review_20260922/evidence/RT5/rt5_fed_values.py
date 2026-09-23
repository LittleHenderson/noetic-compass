"""RT5 step 4 (descriptive, NOT rule-bearing; defined AFTER step 2 was seen):
 (a) exact values FED to the reach head that change with world size: the four world-level degree sums of
     _reach_options (pointer_learner.py:1270-1273 in the Helm 1.0 run copy), computed in float64 from RMS-normalised
     rows (_row_rms: sqrt(mean(x^2)) over the 18-wide row, eps 1e-6), trained reach+parts vs dev;
 (b) exact 18-wide raw node rows: does each dev focus row occur among trained FOCUS rows?
 (c) post-hoc parts shortcut: 'parts = every node with in-degree >= 1' vs the true children, on the four-node course
     (trained + held-back parts) and on the ten-node dev parts; and how often Helm's dev parts answer equals it.
Usage: python -B rt5_fed_values.py <ROOT>
"""
import json, math, os, sys
from collections import Counter, defaultdict

ROOT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(ROOT, "records", "typed_pointer_001")
RECEIPTS = ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")] + \
           ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]
data = json.load(open(os.path.join(HERE, "rt5_inputs.json"), encoding="utf-8"))
trained, dev = data["trained"], data["dev"]


def raw_row(x):
    inh = [0] * 5; inh[x["in"]] = 1
    outh = [0] * 5; outh[x["out"]] = 1
    return (x["is_declared_whole"], x["participant"], 0, x["is_whole_arg"], x["is_part_arg"], x["is_focus"],
            x["is_target"], 1) + tuple(inh) + tuple(outh)


def rms(v):
    return max(math.sqrt(sum(a * a for a in v) / len(v)), 1e-6)


def reach_degree_terms(r):
    w = r["worlds"][r["focus_world_id"]]
    rows = [raw_row(x) for x in w["rows"]]
    s_in = sum(row[8] / rms(row) for row in rows)
    s_out = sum(row[13] / rms(row) for row in rows)
    n = len(rows)
    return (s_in, s_out, s_in / n, s_out / n)


def rng(vals):
    return "min %r max %r" % (min(vals), max(vals))


print("(a) the four reach-head degree terms (focus world), trained reach+parts vs dev (all 59):")
T = [reach_degree_terms(r) for r in trained.values() if r["kind"] in ("reach", "parts")]
D = [reach_degree_terms(r) for r in dev.values()]
names = ("sum in-deg-0 col", "sum out-deg-0 col", "sum in-deg-0 / n", "sum out-deg-0 / n")
for i, nm in enumerate(names):
    tmax, tmin = max(t[i] for t in T), min(t[i] for t in T)
    outside = sum(1 for d in D if not (tmin - 1e-12 <= d[i] <= tmax + 1e-12))
    print("   %-20s trained %s | dev %s | dev questions outside trained [min,max]: %d / %d"
          % (nm, rng([t[i] for t in T]), rng([d[i] for d in D]), outside, len(D)))
print("   query whole-rank scalar: trained reach+parts %s | dev %s"
      % (rng([r["whole"] for r in trained.values() if r["kind"] in ("reach", "parts")]), rng([r["whole"] for r in dev.values()])))

print("\n(b) exact 18-wide raw node rows (before RMS): dev focus rows vs trained FOCUS rows (any kind)")
tfocus = set()
for r in trained.values():
    for x in r["worlds"][r["focus_world_id"]]["rows"]:
        tfocus.add(raw_row(x))
unseen = Counter(); total = 0
for rid, r in dev.items():
    for x in r["worlds"][r["focus_world_id"]]["rows"]:
        total += 1
        if raw_row(x) not in tfocus:
            unseen[(x["in"], x["out"], x["participant"], x["is_whole_arg"], x["is_part_arg"], x["is_declared_whole"])] += 1
print("   trained distinct focus rows %d; dev focus rows %d; dev rows never seen as a trained focus row %d"
      % (len(tfocus), total, sum(unseen.values())))
print("   unseen dev rows by (in,out,participant,whole_arg,part_arg,declared_whole):", dict(unseen))

print("\n(c) post-hoc parts shortcut 'every node with in-degree >= 1' vs true children")
course = json.load(open(os.path.join(ROOT, "records/typed_course_001/checks_002/public_course.json"), encoding="utf-8"))
pm = json.load(open(os.path.join(BASE, RECEIPTS[0], "checkpoints", "protocol_material.json"), encoding="utf-8"))
held = set(pm["held_back_record_ids"])
bank = {w["world_id"]: w for w in course["bank"]["worlds"]}


def parts_sets_from_course(row):
    w = bank[row["source_world_id"]]
    refs = sorted(n["ref"] for n in w["nodes"]); idx = {r: i for i, r in enumerate(refs)}
    kids = defaultdict(set); indeg = Counter()
    for e in w["contains"]:
        kids[idx[e["source"]]].add(idx[e["target"]]); indeg[idx[e["target"]]] += 1
    whole = idx[row["query"]["arguments"]["whole"]]
    return kids[whole], {i for i in range(len(refs)) if indeg[i] >= 1}


c_tr, c_he = Counter(), Counter()
for row in course["registry"]:
    if row["query"]["kind"] != "parts": continue
    true, nonroot = parts_sets_from_course(row)
    rid = row["record_id"]
    if rid in pm["trained_record_ids"]: c_tr[true == nonroot] += 1
    elif rid in held: c_he[true == nonroot] += 1
print("   four-node course parts: shortcut == truth  trained %s  held-back %s" % (dict(c_tr), dict(c_he)))
dv = Counter(); helm_eq = Counter()
for rid, r in dev.items():
    if r["kind"] != "parts": continue
    w = r["worlds"][r["focus_world_id"]]
    true = {t for s, t in w["edges"] if s == r["whole"]}
    nonroot = {x["rank"] for x in w["rows"] if x["in"] >= 1}
    dv[true == nonroot] += 1
    for rd in RECEIPTS:
        pred = {p["record_id"]: p["answer"]["value"] for p in json.load(open(os.path.join(BASE, rd, "checkpoints", "development_p10_predictions.json"), encoding="utf-8"))["predictions"]}
        got = {int(x.rpartition("/n")[2]) for x in pred[rid].get("nodes", [])}
        below_whole_nonroot = {n for n in nonroot if n < r["whole"]}
        helm_eq[("equals truth", got == true)] += 1
        helm_eq[("equals every in>=1 node", got == nonroot)] += 1
        helm_eq[("is a superset of truth", got >= true)] += 1
print("   ten-node dev parts: shortcut == truth %s" % dict(dv))
print("   Helm's 36 dev parts answers (6 receipts x 6):", dict(sorted(helm_eq.items())))
