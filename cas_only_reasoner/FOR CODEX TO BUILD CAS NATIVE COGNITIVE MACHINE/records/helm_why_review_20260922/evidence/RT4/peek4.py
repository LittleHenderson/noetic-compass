import json
ROOT=r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
pc=json.load(open(ROOT+"/records/typed_course_001/checks_002/public_course.json"))
reg=pc["registry"]
print(json.dumps(reg[0])[:1500])
for r in reg:
    s=json.dumps(r)
    if '"reach"' in s:
        print(s[:5000]); break
