"""R7 meeting: final frozen-18 score vs the zero-learning floor, counted both ways. Pure JSON."""
import json, sys
sys.path.insert(0, r"%s" % __file__.rsplit("/", 1)[0].rsplit("\\", 1)[0])
exec(open(__file__.replace("floor_net.py", "start_swap.py"), encoding="utf-8").read().split('runs = {')[0])
g = json.load(open(T + "/admission_001/gate_reading.json", encoding="utf-8"))
oc = g["oracle_ceilings"]
floor = (set(oc["population_ids_the_rule_solves"]) | set(oc.get("rank_last_ids_the_rule_solves") or [])) & set(label18)
print("floor size", len(floor))
for v in VERS:
    for s in SEEDS:
        fi = outcomes(v, s, "p10")
        right = sum(fi.values()); non_floor = sum(1 for k in label18 if fi[k] and k not in floor)
        missed = [(k[12:20], kind_of[k]) for k in sorted(floor) if not fi[k]]
        print(v, s, "final", right, "| floor questions right", right - non_floor, "of", len(floor), "| non-floor right", non_floor,
              "| net vs floor total 11:", right - len(floor), "| floor questions missed", missed)
