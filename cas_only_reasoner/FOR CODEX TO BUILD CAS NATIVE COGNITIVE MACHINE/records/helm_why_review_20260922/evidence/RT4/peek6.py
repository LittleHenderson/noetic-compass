import json
from collections import Counter
ROOT=r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
pc=json.load(open(ROOT+"/records/typed_course_001/checks_002/public_course.json",encoding="utf-8"))
c=Counter()
for r in pc["registry"]:
    q=r["query"]
    c[(q["kind"],q["rule"],tuple(sorted(q["arguments"].keys())))]+=1
for k,v in sorted(c.items()): print(k,v)
g=json.load(open(ROOT+"/records/typed_pointer_001/admission_001/gate_reading.json",encoding="utf-8"))
print(list(g.keys()))
print(list(g["population"].keys()))
print(json.dumps(g["population"])[:1500])
