import json
ROOT=r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
g=json.load(open(ROOT+"/records/typed_pointer_001/admission_001/gate_reading.json",encoding="utf-8"))
v=g["seeds"]["20260917"]["G_LEARN_population"]
print({k:(val if not isinstance(val,list) or len(val)<6 else "list%d"%len(val)) for k,val in v.items()})
print(json.dumps(g["seeds"]["20260917"]["start_checkpoint"])[:300], json.dumps(g["seeds"]["20260917"]["final_checkpoint"])[:300])
print(json.dumps(g["seeds"]["20260917"]["population_questions_correct"])[:400])
