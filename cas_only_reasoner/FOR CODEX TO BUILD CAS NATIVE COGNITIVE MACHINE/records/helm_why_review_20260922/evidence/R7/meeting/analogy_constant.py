"""R7 meeting: the two constant analogy worlds -- how often each is a worked answer in the packets, and on which
records each is scored correct. Pure JSON. No model is loaded."""
import collections, json
B = (r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
     r"/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records")
T = B + "/typed_pointer_001"
reg = {x["record_id"]: x for x in json.load(open(B + "/typed_course_001/checks_002/public_course.json", encoding="utf-8"))["registry"]
       if x["query"]["kind"] == "analogy"}
worked = collections.Counter(s["worked_answer"]["value"].get("world_id") for x in reg.values() for s in x["supports"])
print("distinct worked-answer worlds", len(worked), "top", [(str(w)[6:14], n) for w, n in worked.most_common(4)])
for ver, pat, seed in (("helm1", "receipt_helm1_certified_%s", "20260917"), ("helm2", "receipt_%s", "20260918")):
    A = "%s/%s/collected/results/artifacts" % (T, pat % seed)
    preds = {p["decisions"]["record_id"]: p["answer"]["value"]["world_id"] for p in
             json.load(open(A + "/course_p10_predictions.json", encoding="utf-8"))["predictions"] if p["answer"]["kind"] == "analogy"}
    rows = [r for r in json.load(open(A + "/course_p10_scoring.json", encoding="utf-8"))["rows"] if r["kind"] == "analogy"]
    ok = [r["record_id"] for r in rows if r["correct"]]
    w = set(preds.values()).pop()
    print(ver, seed, "constant", w[6:14], "| worked-answer count", worked[w], "| correct records", len(ok),
          "| distinct focus worlds among correct", len({reg[r]["query"]["focus_world_id"] for r in ok}),
          "| focus==constant among all", sum(reg[r]["query"]["focus_world_id"] == w for r in preds))
