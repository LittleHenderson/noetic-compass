import json
ROOT=r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
pc=json.load(open(ROOT+"/records/typed_course_001/checks_002/public_course.json"))
print(list(pc.keys()))
for k,v in pc.items():
    print(k, type(v).__name__, len(v) if hasattr(v,'__len__') else v)
