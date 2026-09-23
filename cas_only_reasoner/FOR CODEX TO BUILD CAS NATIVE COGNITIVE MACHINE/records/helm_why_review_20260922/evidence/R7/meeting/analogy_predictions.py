"""R7 meeting: are Helm's analogy answers a function of the focus world, or one near-constant world?

Pure JSON over saved course_p10 predictions/scoring and the public course registry. No model is loaded.
Tests R2-F5 (analogy scorer cannot see the focus world's shape or domain) against behaviour.
"""
import collections, json

B = (r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
     r"/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records")
T = B + "/typed_pointer_001"
reg = {x["record_id"]: x for x in json.load(open(B + "/typed_course_001/checks_002/public_course.json", encoding="utf-8"))["registry"]
       if x["query"]["kind"] == "analogy"}
print("analogy records in registry", len(reg), "distinct focus worlds", len({x["query"]["focus_world_id"] for x in reg.values()}))
RUNS = [("helm1", "receipt_helm1_certified_%s"), ("helm2", "receipt_%s")]
for ver, pat in RUNS:
    for seed in ("20260917", "20260918", "20260919"):
        for phase in ("p00", "p10"):
            A = "%s/%s/collected/results/artifacts" % (T, pat % seed)
            preds = [p for p in json.load(open(A + "/course_%s_predictions.json" % phase, encoding="utf-8"))["predictions"]
                     if p["answer"]["kind"] == "analogy"]
            score = {r["record_id"]: r["correct"] for r in json.load(open(A + "/course_%s_scoring.json" % phase, encoding="utf-8"))["rows"]
                     if r["kind"] == "analogy"}
            worlds = collections.Counter()
            focus_pred = collections.defaultdict(set)
            is_support_answer = 0
            for p in preds:
                rid = p["decisions"]["record_id"]
                w = (p["answer"]["value"] or {}).get("world_id")
                worlds[w] += 1
                focus_pred[reg[rid]["query"]["focus_world_id"]].add(w)
                sup = {s["worked_answer"]["value"].get("world_id") for s in reg[rid]["supports"]}
                is_support_answer += w in sup
            top = worlds.most_common(3)
            print("%s %s %s: n %d correct %d | distinct predicted worlds %d | top %s | pred == a support's worked answer %d"
                  % (ver, seed, phase, len(preds), sum(score.values()), len(worlds),
                     [(str(w)[6:14], n) for w, n in top], is_support_answer))
