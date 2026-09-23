# JUDGE: the frozen-18 learning curve and the per-seed gate numbers, read from both gate readings. Pure JSON.
import json, os, hashlib
BASE = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_pointer_001"
for ver, adm in (("2.0", "admission_001"), ("1.0", "admission_helm1_certified")):
    path = os.path.join(BASE, adm, "gate_reading.json")
    raw = open(path, "rb").read()
    g = json.loads(raw.decode("utf-8"))
    print("==", ver, adm, "sha256", hashlib.sha256(raw).hexdigest(), "label", g["label"],
          "main_updates", g["main_updates"], "updates_per_pass", g["updates_per_pass"], "passes", g["passes"])
    for seed, s in sorted(g["seeds"].items()):
        curve = s["population_questions_correct"]
        order = sorted(curve, key=int)
        pr = s["G_LEARN_population"]; mp = s["MORE_PRACTICE_population"]
        print("  ", seed, "frozen-18 by pass", [(p, curve[p]) for p in order],
              "| primary b/c", pr["wrong_to_right"], pr["right_to_wrong"], "p", pr["p_one_sided"], "passed", pr["passed"],
              "| more-practice b/c", mp["wrong_to_right"], mp["right_to_wrong"], "p", mp["p_one_sided"], "passed", mp["passed"],
              "| retention", s["retention"]["before"]["correct"], "->", s["retention"]["after"]["correct"], "of", s["retention"]["after"]["total"])
