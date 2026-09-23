import json
ROOT=r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
g=json.load(open(ROOT+"/records/typed_pointer_001/admission_001/gate_reading.json",encoding="utf-8"))
print(g["label_key_test"])
v=g["seeds"]["20260917"]
print(list(v.keys()))
print(json.dumps(v[g["label_key_test"]])[:1500])
