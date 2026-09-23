"""R7: per-kind whole-course and held-back counts, Helm 1.0 certified vs Helm 2.0-experimental.

Reads the saved course_p00/p10 scoring files (whose correct flags trusted_rescore re-derived with
0 disagreements) and the two gate readings. Pure JSON. No model is loaded.
"""
import collections
import json

T = (r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
     r"/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001")
SEEDS = ("20260917", "20260918", "20260919")
VERS = {"helm1": ("receipt_helm1_certified_%s", "admission_helm1_certified"),
        "helm2": ("receipt_%s", "admission_001")}


def rows(ver, seed, phase):
    path = "%s/%s/collected/results/artifacts/course_%s_scoring.json" % (T, VERS[ver][0] % seed, phase)
    d = json.load(open(path, encoding="utf-8"))
    q = collections.defaultdict(list)
    for r in d["rows"]:
        q[r["query_id"]].append(r)
    return q, d["correct"], d["total"], d["rows"]


gr = {v: json.load(open("%s/%s/gate_reading.json" % (T, VERS[v][1]), encoding="utf-8")) for v in VERS}
held = set(gr["helm2"]["held_questions"]) if isinstance(gr["helm2"]["held_questions"], list) else None
print("held_questions value", gr["helm2"]["held_questions"], "held_records", gr["helm2"]["held_records"])
print("held sets identical across versions:", gr["helm1"]["held_questions"] == gr["helm2"]["held_questions"])
label18 = gr["helm2"]["label_key_population"]
print("label populations identical:", gr["helm1"]["label_key_population"] == label18, len(label18))
oc = gr["helm2"]["oracle_ceilings"]
floor_ids = set(oc["population_ids_the_rule_solves"]) | set(oc.get("rank_last_ids_the_rule_solves") or [])
print("floor ids (adjacency or rank-last) in label population:", len(floor_ids & set(label18)))

for seed in SEEDS:
    print("=== seed", seed)
    for ver in ("helm1", "helm2"):
        r10, c10, tot, raw10 = rows(ver, seed, "p10")
        r00, c00, _, _ = rows(ver, seed, "p00")
        kinds = collections.Counter(r["kind"] for r in raw10 if r["correct"])
        kinds_held = collections.Counter(r10[q]["kind"] for q in held if q in r10 and r10[q]["correct"]) if held else None
        print(" ", ver, "course p00", c00, "p10", c10, "/", tot, "| p10 by kind", dict(sorted(kinds.items())))
        if held:
            print("     held p10 total", sum(kinds_held.values()), "by kind", dict(sorted(kinds_held.items())),
                  "held minus correspondence", sum(kinds_held.values()) - kinds_held.get("correspondence", 0))
        print("     course p10 minus correspondence", c10 - kinds.get("correspondence", 0))
        before = {q: all(x["correct"] for x in r00[q]) for q in label18}
        after = {q: all(x["correct"] for x in r10[q]) for q in label18}
        lost = [q for q in label18 if before[q] and not after[q]]
        gained = [q for q in label18 if after[q] and not before[q]]
        print("     frozen18 before", sum(before.values()), "after", sum(after.values()), "gained", len(gained),
              "lost", len(lost), [(q[:24], r10[q][0]["kind"], q in floor_ids,
                                   q in set(oc.get("rank_last_ids_the_rule_solves") or [])) for q in lost])
        above = sum(1 for q in label18 if after[q] and q not in floor_ids)
        print("     after-correct NOT in floor set", above)
