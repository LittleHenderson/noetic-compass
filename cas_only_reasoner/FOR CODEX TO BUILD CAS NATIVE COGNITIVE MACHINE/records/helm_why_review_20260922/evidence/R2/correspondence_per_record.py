import json, collections, importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("cb", str(Path(__file__).with_name("correspondence_baseline.py")))
# re-use functions without re-printing: exec only the defs
src = Path(__file__).with_name("correspondence_baseline.py").read_text(encoding="utf-8")
ns = {}
exec(compile(src.split("score = collections.Counter()")[0], "cb", "exec"), ns)
R, W = ns["R"], ns["W"]
for s in (7, 8, 9):
    d = R / ("receipt_2026091%d" % s) / "checkpoints"
    preds = json.loads((d / "ablation_baseline_predictions.json").read_text(encoding="utf-8"))["predictions"]
    sc = {r["record_id"]: r for r in json.loads((d / "ablation_baseline_scoring.json").read_text(encoding="utf-8"))["rows"]}
    n = hit_p = hit_i = 0; q = collections.Counter(); worlds = collections.Counter()
    for p in preds:
        row = sc[p["record_id"]]
        if row["kind"] != "correspondence": continue
        pairs = tuple(sorted((x["source"], x["target"]) for x in p["answer"]["value"]["pairs"]))
        a, b = W[ns["world_of"](pairs[0][0])], W[ns["world_of"](pairs[0][1])]
        n += 1; q[row["query_id"]] += 1; worlds[(a["world_id"][:14], b["world_id"][:14])] += 1
        hit_p += ns["participant_order"](a, b) == pairs
        hit_i += ns["iso_lexical_first"](a, b) == pairs
    print("seed 2026091%d: correspondence rows %d, distinct query_ids %d, distinct (source,target) world pairs %d; participant_order matches Helm's correct answer on %d/%d; brute-force isomorphism on %d/%d"
          % (s, n, len(q), len(worlds), hit_p, n, hit_i, n))
# how participants relate to structure in the whole bank
agree = 0; tot = 0
for w in W.values():
    tot += 1
print("bank worlds:", tot, "example participants_basis:", next(iter(W.values()))["declarations"]["participants_basis"])
