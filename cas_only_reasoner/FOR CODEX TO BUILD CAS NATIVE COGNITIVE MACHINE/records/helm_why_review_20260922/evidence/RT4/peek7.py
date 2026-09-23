import json
ROOT=r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
for adm in ["admission_001","admission_helm1_certified"]:
    g=json.load(open(ROOT+"/records/typed_pointer_001/"+adm+"/gate_reading.json",encoding="utf-8"))
    print(adm, type(g["held_questions"]).__name__, (len(g["held_questions"]) if hasattr(g["held_questions"],"__len__") else g["held_questions"]))
    print(" held_questions sample:", json.dumps(g["held_questions"])[:300])
    print(" population_questions:", json.dumps(g["population_questions"])[:300])
    oc=g["oracle_ceilings"]; print(" oracle keys", list(oc.keys()))
    print(" pop solved", [q[12:20] for q in oc["population_ids_the_rule_solves"]], " rank", [q[12:20] for q in oc["rank_last_ids_the_rule_solves"]])
    for s,v in g["seeds"].items():
        print(" seed",s, {k:v[k] for k in v if k in ("primary","label_key")} if False else list(v.keys())[:12])
        break
